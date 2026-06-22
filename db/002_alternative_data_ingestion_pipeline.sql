-- =============================================================================
-- Contrarian Radar — Step 2: Alternative Data Ingestion Pipeline
-- Sources: SEC EDGAR, Earnings Call NLP, Satellite/Alt-Data Connectors
-- Horizon: 2026–2031
-- =============================================================================

-- ── Enumerations ─────────────────────────────────────────────────────────────

CREATE TYPE data_source_category AS ENUM (
    'SEC_EDGAR',
    'Earnings_Call_Transcript',
    'Satellite_AIS',
    'Satellite_Nightlight',
    'Credit_Card_Flow',
    'Job_Posting_Feed',
    'Patent_Filing',
    'Supply_Chain_Manifest',
    'Social_Sentiment',
    'Central_Bank_Filing'
);

CREATE TYPE ingestion_status AS ENUM (
    'Pending',
    'Running',
    'Completed',
    'Failed',
    'Partial'
);

CREATE TYPE filing_form_type AS ENUM (
    '10-K',
    '10-Q',
    '8-K',
    'SC-13G',
    'SC-13D',
    'Form-4',
    'S-1',
    'DEF-14A',
    '13-F',
    'NT-10K'
);

CREATE TYPE nlp_signal_type AS ENUM (
    'Supplier_Named',
    'Customer_Concentration_Risk',
    'Capex_Commitment',
    'Guidance_Raise',
    'Guidance_Cut',
    'Executive_Departure_Risk',
    'Litigation_Mentioned',
    'Regulatory_Headwind',
    'Geopolitical_Exposure',
    'Partnership_Announced',
    'Custom_Silicon_Referenced',
    'Kingmaker_Trigger'
);

-- =============================================================================
-- TABLE 5: DATA_SOURCE_REGISTRY
-- Catalogue of every external feed / connector the pipeline consumes.
-- Supports both push (webhook) and pull (scheduled poll) patterns.
-- =============================================================================

CREATE TABLE IF NOT EXISTS Data_Source_Registry (
    Source_ID           SERIAL                  PRIMARY KEY,
    Source_Name         TEXT                    NOT NULL UNIQUE,
    Source_Category     data_source_category    NOT NULL,
    Provider_Name       TEXT                    NOT NULL,
    Base_Endpoint_URL   TEXT,
    Auth_Mechanism      TEXT,
    Poll_Frequency_Min  INTEGER                 CHECK (Poll_Frequency_Min > 0),
    Is_Webhook          BOOLEAN                 NOT NULL DEFAULT FALSE,
    Rate_Limit_Per_Min  INTEGER,
    Geo_Coverage        TEXT[],
    Asset_Coverage      TEXT[],
    Data_Lag_Hours      NUMERIC(6,2),
    Licensing_Notes     TEXT,
    Is_Active           BOOLEAN                 NOT NULL DEFAULT TRUE,
    Created_At          TIMESTAMPTZ             NOT NULL DEFAULT NOW(),
    Updated_At          TIMESTAMPTZ             NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  Data_Source_Registry IS 'Catalogue of all external alternative data feeds consumed by the ingestion pipeline.';
COMMENT ON COLUMN Data_Source_Registry.Data_Lag_Hours IS 'Typical delay between real-world event and data availability. Used to timestamp-adjust signals.';
COMMENT ON COLUMN Data_Source_Registry.Geo_Coverage IS 'Array of ISO 3166-1 alpha-2 country codes covered by this feed.';

-- =============================================================================
-- TABLE 6: INGESTION_JOBS
-- Execution log for every scheduled or on-demand data pull.
-- Tracks row counts, latency, and failure reasons for pipeline observability.
-- =============================================================================

CREATE TABLE IF NOT EXISTS Ingestion_Jobs (
    Job_ID              BIGSERIAL               PRIMARY KEY,
    Source_ID           INTEGER                 NOT NULL REFERENCES Data_Source_Registry (Source_ID) ON DELETE RESTRICT,
    Job_Status          ingestion_status        NOT NULL DEFAULT 'Pending',
    Triggered_By        TEXT                    NOT NULL DEFAULT 'scheduler',
    Started_At          TIMESTAMPTZ,
    Completed_At        TIMESTAMPTZ,
    Duration_Seconds    NUMERIC(10, 3)
        GENERATED ALWAYS AS (
            EXTRACT(EPOCH FROM (Completed_At - Started_At))
        ) STORED,
    Records_Fetched     INTEGER                 DEFAULT 0,
    Records_Inserted    INTEGER                 DEFAULT 0,
    Records_Updated     INTEGER                 DEFAULT 0,
    Records_Rejected    INTEGER                 DEFAULT 0,
    Error_Message       TEXT,
    Retry_Count         SMALLINT                NOT NULL DEFAULT 0,
    Checkpoint_Cursor   TEXT,
    Created_At          TIMESTAMPTZ             NOT NULL DEFAULT NOW(),
    Updated_At          TIMESTAMPTZ             NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  Ingestion_Jobs IS 'Execution log for all ingestion runs. Duration_Seconds is auto-computed. Checkpoint_Cursor holds the last-seen ID or timestamp for resumable pulls.';
COMMENT ON COLUMN Ingestion_Jobs.Checkpoint_Cursor IS 'Opaque resumption token (e.g. last EDGAR accession number or Unix timestamp) enabling idempotent re-runs after failure.';

CREATE INDEX idx_jobs_source_status  ON Ingestion_Jobs (Source_ID, Job_Status);
CREATE INDEX idx_jobs_started        ON Ingestion_Jobs (Started_At DESC);
CREATE INDEX idx_jobs_failed         ON Ingestion_Jobs (Job_Status) WHERE Job_Status = 'Failed';

-- =============================================================================
-- TABLE 7: SEC_EDGAR_FILINGS
-- Normalised store for parsed EDGAR submissions.
-- Links back to Asset_Registry and flags Kingmaker-relevant disclosures.
-- =============================================================================

CREATE TABLE IF NOT EXISTS SEC_Edgar_Filings (
    Filing_ID               BIGSERIAL           PRIMARY KEY,
    Job_ID                  BIGINT              REFERENCES Ingestion_Jobs (Job_ID) ON DELETE SET NULL,
    Asset_ID                INTEGER             REFERENCES Asset_Registry (Asset_ID) ON DELETE SET NULL,
    CIK                     VARCHAR(10)         NOT NULL,
    Accession_Number        VARCHAR(25)         NOT NULL UNIQUE,
    Form_Type               filing_form_type    NOT NULL,
    Filing_Date             DATE                NOT NULL,
    Period_Of_Report        DATE,
    Filed_By_Name           TEXT,
    Filer_CIK               VARCHAR(10),

    -- Parsed financial fields (populated by NLP extraction layer)
    Revenue_USD             NUMERIC(20, 2),
    Net_Income_USD          NUMERIC(20, 2),
    Total_Assets_USD        NUMERIC(20, 2),
    Long_Term_Debt_USD      NUMERIC(20, 2),
    Capex_USD               NUMERIC(20, 2),

    -- Key entity mentions extracted by NLP
    Named_Suppliers         TEXT[],
    Named_Customers         TEXT[],
    Named_Partners          TEXT[],

    -- Kingmaker-specific extraction flags
    Kingmaker_Keywords_Hit  TEXT[],
    Kingmaker_Flag          BOOLEAN             NOT NULL DEFAULT FALSE,

    -- Raw text sections retained for downstream NLP re-processing
    Item1_Business_Text     TEXT,
    Item1A_Risk_Text        TEXT,
    Item7_MDA_Text          TEXT,

    EDGAR_URL               TEXT,
    Raw_Filing_Path         TEXT,
    Created_At              TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    Updated_At              TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  SEC_Edgar_Filings IS 'Normalised EDGAR filing store. Named_Suppliers/Customers/Partners are NLP-extracted arrays. Kingmaker_Flag triggers a connection review workflow.';
COMMENT ON COLUMN SEC_Edgar_Filings.Kingmaker_Keywords_Hit IS 'Array of keyword matches (e.g. custom silicon, sole-source supplier, strategic dependency) that triggered Kingmaker_Flag.';
COMMENT ON COLUMN SEC_Edgar_Filings.Item7_MDA_Text IS 'Raw MD&A text retained for re-processing as NLP models improve without re-fetching from EDGAR.';

CREATE INDEX idx_edgar_asset          ON SEC_Edgar_Filings (Asset_ID);
CREATE INDEX idx_edgar_cik            ON SEC_Edgar_Filings (CIK);
CREATE INDEX idx_edgar_form_date      ON SEC_Edgar_Filings (Form_Type, Filing_Date DESC);
CREATE INDEX idx_edgar_kingmaker      ON SEC_Edgar_Filings (Kingmaker_Flag) WHERE Kingmaker_Flag = TRUE;

-- =============================================================================
-- TABLE 8: EARNINGS_CALL_TRANSCRIPTS
-- Raw and structured store for quarterly earnings call transcripts.
-- Feeds directly into the NLP signal extraction engine.
-- =============================================================================

CREATE TABLE IF NOT EXISTS Earnings_Call_Transcripts (
    Transcript_ID       BIGSERIAL               PRIMARY KEY,
    Job_ID              BIGINT                  REFERENCES Ingestion_Jobs (Job_ID) ON DELETE SET NULL,
    Asset_ID            INTEGER                 NOT NULL REFERENCES Asset_Registry (Asset_ID) ON DELETE RESTRICT,
    Fiscal_Quarter      CHAR(6)                 NOT NULL,     -- Format: YYYYQN e.g. 2025Q3
    Call_Date           DATE                    NOT NULL,
    Call_Year           SMALLINT
        GENERATED ALWAYS AS (EXTRACT(YEAR FROM Call_Date)::SMALLINT) STORED,

    -- Structured sections
    Prepared_Remarks    TEXT,
    QA_Session          TEXT,
    Full_Transcript     TEXT                    NOT NULL,

    -- Speaker metadata [{name, role, employer}]
    Speakers            JSONB,

    -- NLP outputs (populated by extraction job after ingestion)
    Sentiment_Score     NUMERIC(4, 3)           CHECK (Sentiment_Score BETWEEN -1 AND 1),
    Confidence_Delta    NUMERIC(4, 3),
    Word_Count          INTEGER,
    NLP_Processed       BOOLEAN                 NOT NULL DEFAULT FALSE,
    NLP_Processed_At    TIMESTAMPTZ,

    Source_Provider     TEXT,
    Source_URL          TEXT,
    Created_At          TIMESTAMPTZ             NOT NULL DEFAULT NOW(),
    Updated_At          TIMESTAMPTZ             NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_transcript UNIQUE (Asset_ID, Fiscal_Quarter)
);

COMMENT ON TABLE  Earnings_Call_Transcripts IS 'Raw and NLP-enriched earnings call transcripts. Full_Transcript retained for re-processing. Speakers JSONB enables per-executive sentiment isolation.';
COMMENT ON COLUMN Earnings_Call_Transcripts.Confidence_Delta IS 'Change in Sentiment_Score vs prior quarter. Negative delta on a Kingmaker asset is a Cassandra_Signal trigger candidate.';
COMMENT ON COLUMN Earnings_Call_Transcripts.Fiscal_Quarter IS 'Format: YYYYQN e.g. 2025Q3. Used for cross-asset temporal alignment.';

CREATE INDEX idx_transcript_asset       ON Earnings_Call_Transcripts (Asset_ID);
CREATE INDEX idx_transcript_date        ON Earnings_Call_Transcripts (Call_Date DESC);
CREATE INDEX idx_transcript_unprocessed ON Earnings_Call_Transcripts (NLP_Processed) WHERE NLP_Processed = FALSE;
CREATE INDEX idx_transcript_sentiment   ON Earnings_Call_Transcripts (Sentiment_Score);

-- =============================================================================
-- TABLE 9: NLP_SIGNAL_EXTRACTIONS
-- Atomic NLP findings extracted from any text corpus (EDGAR, transcripts,
-- news, social). Each row = one signal event with position and confidence.
-- Links back to source document and, when matched, to Asset_Registry.
-- =============================================================================

CREATE TABLE IF NOT EXISTS NLP_Signal_Extractions (
    Extraction_ID           BIGSERIAL               PRIMARY KEY,

    -- Source document (exactly one of these will be non-NULL)
    Source_Filing_ID        BIGINT                  REFERENCES SEC_Edgar_Filings (Filing_ID) ON DELETE CASCADE,
    Source_Transcript_ID    BIGINT                  REFERENCES Earnings_Call_Transcripts (Transcript_ID) ON DELETE CASCADE,

    Signal_Type             nlp_signal_type         NOT NULL,

    -- The verbatim text fragment that triggered the signal
    Extracted_Text          TEXT                    NOT NULL,
    Char_Offset_Start       INTEGER,
    Char_Offset_End         INTEGER,

    -- Entity resolution
    Subject_Asset_ID        INTEGER                 REFERENCES Asset_Registry (Asset_ID) ON DELETE SET NULL,
    Object_Entity_Name      TEXT,
    Object_Asset_ID         INTEGER                 REFERENCES Asset_Registry (Asset_ID) ON DELETE SET NULL,

    -- Scoring
    Confidence              NUMERIC(4, 3)           NOT NULL CHECK (Confidence BETWEEN 0 AND 1),
    Sentiment               NUMERIC(4, 3)           CHECK (Sentiment BETWEEN -1 AND 1),

    -- Kingmaker promotion: did this extraction trigger a new/updated connection?
    Promoted_To_Connection  BOOLEAN                 NOT NULL DEFAULT FALSE,
    Connection_ID           INTEGER                 REFERENCES Corporate_Ecosystem_Connections (Connection_ID) ON DELETE SET NULL,

    -- Cassandra promotion: did this extraction trigger a risk signal?
    Promoted_To_Signal      BOOLEAN                 NOT NULL DEFAULT FALSE,
    Cassandra_Signal_ID     INTEGER                 REFERENCES Cassandra_Signals (Signal_ID) ON DELETE SET NULL,

    NLP_Model_Version       TEXT,
    Created_At              TIMESTAMPTZ             NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_single_source CHECK (
        (Source_Filing_ID IS NOT NULL)::INT +
        (Source_Transcript_ID IS NOT NULL)::INT = 1
    )
);

COMMENT ON TABLE  NLP_Signal_Extractions IS 'Atomic NLP extraction events from any text corpus. Confidence >= 0.75 triggers auto-promotion review to Corporate_Ecosystem_Connections or Cassandra_Signals.';
COMMENT ON COLUMN NLP_Signal_Extractions.Promoted_To_Connection IS 'TRUE when this extraction was auto-escalated to create or update a Corporate_Ecosystem_Connections row.';
COMMENT ON COLUMN NLP_Signal_Extractions.Confidence IS '0.0-1.0 model confidence. Auto-promotion threshold: >= 0.75. Human review required for 0.50-0.74.';

CREATE INDEX idx_nlp_signal_type        ON NLP_Signal_Extractions (Signal_Type);
CREATE INDEX idx_nlp_subject_asset      ON NLP_Signal_Extractions (Subject_Asset_ID) WHERE Subject_Asset_ID IS NOT NULL;
CREATE INDEX idx_nlp_object_asset       ON NLP_Signal_Extractions (Object_Asset_ID) WHERE Object_Asset_ID IS NOT NULL;
CREATE INDEX idx_nlp_kingmaker_promoted ON NLP_Signal_Extractions (Promoted_To_Connection) WHERE Promoted_To_Connection = TRUE;
CREATE INDEX idx_nlp_filing             ON NLP_Signal_Extractions (Source_Filing_ID) WHERE Source_Filing_ID IS NOT NULL;
CREATE INDEX idx_nlp_transcript         ON NLP_Signal_Extractions (Source_Transcript_ID) WHERE Source_Transcript_ID IS NOT NULL;

-- =============================================================================
-- TABLE 10: ALT_DATA_OBSERVATIONS
-- Generic store for non-textual alternative data:
-- satellite imagery metrics, AIS vessel tracking, credit card panel flows,
-- job posting velocity, patent filing counts, nightlight intensity indices.
-- =============================================================================

CREATE TABLE IF NOT EXISTS Alt_Data_Observations (
    Observation_ID      BIGSERIAL               PRIMARY KEY,
    Job_ID              BIGINT                  REFERENCES Ingestion_Jobs (Job_ID) ON DELETE SET NULL,
    Source_ID           INTEGER                 NOT NULL REFERENCES Data_Source_Registry (Source_ID) ON DELETE RESTRICT,
    Asset_ID            INTEGER                 REFERENCES Asset_Registry (Asset_ID) ON DELETE SET NULL,

    Observation_Date    DATE                    NOT NULL,
    Metric_Name         TEXT                    NOT NULL,
    Metric_Value        NUMERIC(20, 6)          NOT NULL,
    Metric_Unit         TEXT,

    -- Period-over-period deltas (populated by transformation job)
    Delta_YoY           NUMERIC(10, 4),
    Delta_MoM           NUMERIC(10, 4),
    Delta_QoQ           NUMERIC(10, 4),

    -- Z-score vs rolling 52-week window (anomaly detection trigger)
    Z_Score_52W         NUMERIC(8, 4),

    -- Geo tag for satellite / AIS data
    Geo_Lat             NUMERIC(9, 6),
    Geo_Lon             NUMERIC(9, 6),
    Geo_Label           TEXT,

    Alert_Triggered     BOOLEAN                 NOT NULL DEFAULT FALSE,
    Alert_Threshold     NUMERIC(20, 6),

    Raw_Payload         JSONB,
    Created_At          TIMESTAMPTZ             NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_alt_obs UNIQUE (Source_ID, Asset_ID, Observation_Date, Metric_Name)
);

COMMENT ON TABLE  Alt_Data_Observations IS 'Generic time-series store for non-textual alt data: satellite imagery, AIS vessel tracking, credit card flows, job postings, patent counts. Z_Score_52W drives anomaly alerts.';
COMMENT ON COLUMN Alt_Data_Observations.Z_Score_52W IS 'Standard deviations from 52-week rolling mean. |Z| > 2.0 triggers Alert_Triggered = TRUE and candidate Cassandra_Signal creation.';
COMMENT ON COLUMN Alt_Data_Observations.Raw_Payload IS 'Original provider JSON retained for auditability and re-transformation without re-fetching.';

CREATE INDEX idx_alt_asset_date     ON Alt_Data_Observations (Asset_ID, Observation_Date DESC);
CREATE INDEX idx_alt_source_metric  ON Alt_Data_Observations (Source_ID, Metric_Name);
CREATE INDEX idx_alt_alert          ON Alt_Data_Observations (Alert_Triggered) WHERE Alert_Triggered = TRUE;
CREATE INDEX idx_alt_zscore         ON Alt_Data_Observations (Z_Score_52W) WHERE Z_Score_52W IS NOT NULL;
CREATE INDEX idx_alt_geo            ON Alt_Data_Observations USING GIST (
    point(Geo_Lon, Geo_Lat)
) WHERE Geo_Lat IS NOT NULL AND Geo_Lon IS NOT NULL;

-- =============================================================================
-- UPDATED_AT TRIGGERS for Step 2 tables
-- =============================================================================

CREATE TRIGGER trg_datasource_updated_at
    BEFORE UPDATE ON Data_Source_Registry FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_jobs_updated_at
    BEFORE UPDATE ON Ingestion_Jobs FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_edgar_updated_at
    BEFORE UPDATE ON SEC_Edgar_Filings FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_transcript_updated_at
    BEFORE UPDATE ON Earnings_Call_Transcripts FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =============================================================================
-- SEED DATA — Data_Source_Registry (canonical connectors)
-- =============================================================================

INSERT INTO Data_Source_Registry (
    Source_Name, Source_Category, Provider_Name, Base_Endpoint_URL,
    Auth_Mechanism, Poll_Frequency_Min, Is_Webhook, Rate_Limit_Per_Min,
    Geo_Coverage, Data_Lag_Hours, Licensing_Notes
) VALUES
    ('SEC EDGAR Full-Text Search',
     'SEC_EDGAR', 'US SEC', 'https://efts.sec.gov/LATEST/search-index',
     'None (public)', 5, FALSE, 10,
     ARRAY['US'], 0.5,
     'Public domain. Rate-limit: 10 req/s per SEC Fair Access Policy.'),

    ('SEC EDGAR Submissions Feed',
     'SEC_EDGAR', 'US SEC', 'https://data.sec.gov/submissions',
     'None (public)', 15, FALSE, 10,
     ARRAY['US'], 0.25,
     'Public domain. CIK-based lookup. Includes Form-4 insider transactions.'),

    ('Earnings Whispers Transcript Feed',
     'Earnings_Call_Transcript', 'Earnings Whispers', NULL,
     'API Key', 60, FALSE, 30,
     ARRAY['US','GB','DE','JP','IN'], 2.0,
     'Commercial licence required.'),

    ('Spire Maritime AIS Feed',
     'Satellite_AIS', 'Spire Global', NULL,
     'OAuth2 Bearer Token', 60, TRUE, 100,
     ARRAY['GLOBAL'], 0.1,
     'Commercial. Tracks vessel movements for supply chain disruption signals.'),

    ('RS Metrics Satellite Parking/Footfall',
     'Satellite_Nightlight', 'RS Metrics', NULL,
     'API Key', 1440, FALSE, 5,
     ARRAY['US','CN','DE','JP'], 24.0,
     'Commercial. Parking lot occupancy as retail/industrial demand proxy.'),

    ('Earnest Research Credit Panel',
     'Credit_Card_Flow', 'Earnest Research', NULL,
     'API Key', 1440, FALSE, 10,
     ARRAY['US'], 3.0,
     'Commercial. Anonymised credit/debit transaction panel — 5M+ US consumers.'),

    ('Revelio Labs Job Posting Feed',
     'Job_Posting_Feed', 'Revelio Labs', NULL,
     'API Key', 720, FALSE, 20,
     ARRAY['US','GB','IN','DE','SG'], 6.0,
     'Commercial. Real-time job posting velocity by company, role, and region.'),

    ('USPTO Patent Full-Text Bulk Data',
     'Patent_Filing', 'USPTO', 'https://bulkdata.uspto.gov',
     'None (public)', 10080, FALSE, 5,
     ARRAY['US'], 72.0,
     'Public domain. Weekly XML bulk download. R&D intensity signal.');

-- =============================================================================
-- END OF STEP 2
-- =============================================================================
