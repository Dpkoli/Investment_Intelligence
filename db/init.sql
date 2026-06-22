-- =============================================================================
-- Contrarian Radar — PostgreSQL Initialization Script
-- The Kingmaker Protocol: Relational Database Foundation
-- Horizon: 2026–2031 | Step 1 of 4
-- =============================================================================

-- Enforce strict type safety and referential integrity
SET client_min_messages = WARNING;

-- =============================================================================
-- ENUMERATIONS
-- =============================================================================

CREATE TYPE cluster_label AS ENUM (
    'SP500',
    'FTSE',
    'EM',
    'GOLD',
    'SILVER',
    'BTC',
    'ETH',
    'SOL',
    'XRP',
    'HORIZON',
    'KINGMAKER'
);

CREATE TYPE instrument_type AS ENUM (
    'Spot',
    'ETF',
    'ETP',
    'Corporate_Proxy',
    'Pipeline_Filing'
);

CREATE TYPE connection_type AS ENUM (
    'Supplier',
    'JV_Partner',
    'Custom_Silicon',
    'Equity_Stake'
);

CREATE TYPE signal_source_type AS ENUM (
    'Whistleblower',
    'Influencer',
    'Regulatory_Leak',
    'Short_Seller_Report',
    'Anonymous_Filing'
);

-- =============================================================================
-- TABLE 1: EXPOSURE_CLUSTERS
-- Taxonomy buckets that classify every tracked asset into a macro-theme.
-- KINGMAKER bucket isolates hidden titan-backed growth gems.
-- =============================================================================

CREATE TABLE IF NOT EXISTS Exposure_Clusters (
    Cluster_ID          SERIAL          PRIMARY KEY,
    Cluster_Label       cluster_label   NOT NULL UNIQUE,
    Description         TEXT            NOT NULL,
    Theme_Thesis        TEXT,
    -- Relative weight within a model portfolio (0.00 – 1.00, sum advisory only)
    Target_Weight       NUMERIC(5, 4)   CHECK (Target_Weight BETWEEN 0 AND 1),
    -- Volatility regime multiplier used by the risk engine
    Vol_Regime_Factor   NUMERIC(6, 4)   DEFAULT 1.0000,
    Is_Active           BOOLEAN         NOT NULL DEFAULT TRUE,
    Created_At          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    Updated_At          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  Exposure_Clusters IS 'Macro-theme taxonomy buckets. KINGMAKER isolates hidden titan-backed growth gems discovered by the Kingmaker Protocol engine.';
COMMENT ON COLUMN Exposure_Clusters.Vol_Regime_Factor IS 'Multiplier applied to position sizing during high-volatility regimes (e.g. 0.5 = half-size in stressed markets).';

-- =============================================================================
-- TABLE 2: ASSET_REGISTRY
-- Master instrument ledger — every tracked security, token, or proxy.
-- Cluster_ID FK links each asset to its macro-theme bucket.
-- =============================================================================

CREATE TABLE IF NOT EXISTS Asset_Registry (
    Asset_ID                SERIAL              PRIMARY KEY,
    Cluster_ID              INTEGER             NOT NULL REFERENCES Exposure_Clusters (Cluster_ID) ON DELETE RESTRICT,
    Ticker                  VARCHAR(20)         NOT NULL,
    ISIN                    CHAR(12),
    Asset_Name              TEXT                NOT NULL,
    Instrument_Type         instrument_type     NOT NULL,

    -- Pricing & liquidity
    Live_Spot_Price         NUMERIC(18, 6),
    Price_Currency          CHAR(3)             DEFAULT 'USD',
    Price_As_Of             TIMESTAMPTZ,

    -- Fund-level metrics (ETF / ETP only; NULL for spot / corporate)
    AUM                     NUMERIC(20, 2),
    Expense_Ratio           NUMERIC(6, 5)       CHECK (Expense_Ratio BETWEEN 0 AND 1),
    Net_30D_Flows           NUMERIC(20, 2),     -- positive = inflows, negative = outflows

    -- Regulatory metadata
    FCA_Authorized_Flag     BOOLEAN             NOT NULL DEFAULT FALSE,
    Regulatory_Filing_Date  DATE,
    Domicile_Country        CHAR(2),            -- ISO 3166-1 alpha-2
    Exchange_MIC            CHAR(4),            -- ISO 10383 Market Identifier Code

    -- Kingmaker tagging
    Kingmaker_Tier          SMALLINT            CHECK (Kingmaker_Tier BETWEEN 1 AND 3),
    -- Tier 1 = direct titan dependency, 2 = second-order, 3 = ecosystem play

    Is_Active               BOOLEAN             NOT NULL DEFAULT TRUE,
    Created_At              TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    Updated_At              TIMESTAMPTZ         NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_asset_ticker_exchange UNIQUE (Ticker, Exchange_MIC)
);

COMMENT ON TABLE  Asset_Registry IS 'Master instrument ledger covering Spot, ETF, ETP, Corporate_Proxy and Pipeline_Filing instrument types across all exposure clusters.';
COMMENT ON COLUMN Asset_Registry.Net_30D_Flows IS 'Rolling 30-day net fund flows in Price_Currency. Positive = net inflow. Used as a momentum signal in allocation engine.';
COMMENT ON COLUMN Asset_Registry.Kingmaker_Tier IS 'NULL unless asset is in the KINGMAKER cluster. Tier 1 = direct titan structural dependency, Tier 2 = second-order ecosystem, Tier 3 = thematic adjacency.';

-- =============================================================================
-- TABLE 3: CORPORATE_ECOSYSTEM_CONNECTIONS
-- The core Kingmaker Protocol table. Maps hidden B2B dependencies between
-- S&P 500 titans (Parent_Anchor) and smaller counterparties (Counterparty).
-- Classic example: Nvidia → Marvell (custom silicon / networking dependency).
-- =============================================================================

CREATE TABLE IF NOT EXISTS Corporate_Ecosystem_Connections (
    Connection_ID           SERIAL              PRIMARY KEY,

    -- The S&P 500 titan providing the structural tailwind
    Parent_Anchor_ID        INTEGER             NOT NULL REFERENCES Asset_Registry (Asset_ID) ON DELETE RESTRICT,

    -- The smaller vendor / supplier / acquisition target receiving the tailwind
    Counterparty_Asset_ID   INTEGER             NOT NULL REFERENCES Asset_Registry (Asset_ID) ON DELETE RESTRICT,

    Connection_Type         connection_type     NOT NULL,

    -- Estimated share of counterparty revenue derived from this relationship (0.00–1.00)
    Share_Of_Wallet_Est     NUMERIC(5, 4)       CHECK (Share_Of_Wallet_Est BETWEEN 0 AND 1),

    -- TRUE if a named executive or public filing explicitly endorses the counterparty
    Endorsement_Flag        BOOLEAN             NOT NULL DEFAULT FALSE,
    Endorsement_Source      TEXT,               -- e.g. "Jensen Huang, GTC 2024 Keynote"
    Endorsement_Date        DATE,

    -- Qualitative confidence in the connection estimate
    Confidence_Score        SMALLINT            CHECK (Confidence_Score BETWEEN 1 AND 10),

    -- Annualised revenue impact estimate in USD (for materiality ranking)
    Revenue_Impact_USD_Est  NUMERIC(20, 2),

    -- Public evidence trail
    Primary_Source_URL      TEXT,
    SEC_Filing_Reference    TEXT,               -- e.g. "10-K 2024, Item 1, p.14"

    Verified_At             TIMESTAMPTZ,
    Is_Active               BOOLEAN             NOT NULL DEFAULT TRUE,
    Created_At              TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    Updated_At              TIMESTAMPTZ         NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_connection UNIQUE (Parent_Anchor_ID, Counterparty_Asset_ID, Connection_Type),
    CONSTRAINT chk_no_self_loop CHECK (Parent_Anchor_ID <> Counterparty_Asset_ID)
);

COMMENT ON TABLE  Corporate_Ecosystem_Connections IS 'Kingmaker Protocol core table. Maps hidden B2B structural dependencies: supplier contracts, JV partnerships, custom silicon agreements, and equity stakes between S&P 500 titans and smaller counterparties.';
COMMENT ON COLUMN Corporate_Ecosystem_Connections.Share_Of_Wallet_Est IS 'Estimated fraction of counterparty annual revenue attributable to the parent titan relationship. High values signal binary dependency risk AND upside leverage.';
COMMENT ON COLUMN Corporate_Ecosystem_Connections.Endorsement_Flag IS 'TRUE when a named titan executive or official filing explicitly names the counterparty as a strategic partner or endorses its technology.';

-- =============================================================================
-- TABLE 4: CASSANDRA_SIGNALS
-- Unstructured early-warning log for systemic risks sourced from
-- whistleblowers, short-sellers, anonymous filings, and influencer alerts.
-- Named after the Trojan prophetess — signals believed but often ignored.
-- =============================================================================

CREATE TABLE IF NOT EXISTS Cassandra_Signals (
    Signal_ID               SERIAL              PRIMARY KEY,

    -- Asset this signal primarily targets (nullable if market-wide)
    Target_Asset_ID         INTEGER             REFERENCES Asset_Registry (Asset_ID) ON DELETE SET NULL,

    -- Cluster-level risk flag (e.g. entire KINGMAKER bucket under threat)
    Target_Cluster_ID       INTEGER             REFERENCES Exposure_Clusters (Cluster_ID) ON DELETE SET NULL,

    Signal_Source           signal_source_type  NOT NULL,
    Source_Handle           TEXT,               -- Twitter/X handle, pseudonym, filing entity name
    Source_Credibility      SMALLINT            CHECK (Source_Credibility BETWEEN 1 AND 10),

    -- Core signal payload
    Signal_Title            TEXT                NOT NULL,
    Raw_Signal_Text         TEXT                NOT NULL,
    Signal_Date             DATE                NOT NULL DEFAULT CURRENT_DATE,

    -- Internal risk scoring (1 = noise, 10 = imminent systemic event)
    Systemic_Risk_Score     SMALLINT            NOT NULL CHECK (Systemic_Risk_Score BETWEEN 1 AND 10),

    -- Categorised risk vector for downstream filtering
    Risk_Vector             TEXT,               -- e.g. 'Counterparty_Concentration', 'Regulatory_Overhang', 'Leverage_Unwind'

    -- Has a human analyst reviewed and adjudicated this signal?
    Analyst_Reviewed        BOOLEAN             NOT NULL DEFAULT FALSE,
    Analyst_Notes           TEXT,
    Analyst_ID              TEXT,               -- links to future User/Analyst table

    -- Cross-reference to any triggered Corporate_Ecosystem_Connections
    Related_Connection_ID   INTEGER             REFERENCES Corporate_Ecosystem_Connections (Connection_ID) ON DELETE SET NULL,

    -- Evidence trail
    Primary_Source_URL      TEXT,
    Attachment_Path         TEXT,               -- path to stored document / screenshot

    Is_Resolved             BOOLEAN             NOT NULL DEFAULT FALSE,
    Resolved_At             TIMESTAMPTZ,
    Created_At              TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    Updated_At              TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  Cassandra_Signals IS 'Early-warning log for unstructured systemic risk signals. Systemic_Risk_Score (1–10) drives alert prioritisation. Named for the Trojan prophetess — signals believed but routinely ignored until too late.';
COMMENT ON COLUMN Cassandra_Signals.Systemic_Risk_Score IS 'Internal composite risk score 1–10. 1–3 = background noise, 4–6 = elevated watch, 7–9 = active threat, 10 = imminent systemic event requiring immediate portfolio action.';
COMMENT ON COLUMN Cassandra_Signals.Risk_Vector IS 'Tagged risk category for downstream strategy filtering. Examples: Counterparty_Concentration, Regulatory_Overhang, Leverage_Unwind, Geopolitical_Friction, Liquidity_Crisis.';

-- =============================================================================
-- INDEXES — query-critical paths
-- =============================================================================

-- Asset_Registry: primary lookup patterns
CREATE INDEX idx_asset_cluster      ON Asset_Registry (Cluster_ID);
CREATE INDEX idx_asset_ticker       ON Asset_Registry (Ticker);
CREATE INDEX idx_asset_fca          ON Asset_Registry (FCA_Authorized_Flag) WHERE FCA_Authorized_Flag = TRUE;
CREATE INDEX idx_asset_kingmaker    ON Asset_Registry (Kingmaker_Tier)       WHERE Kingmaker_Tier IS NOT NULL;

-- Corporate_Ecosystem_Connections: graph traversal performance
CREATE INDEX idx_cec_parent         ON Corporate_Ecosystem_Connections (Parent_Anchor_ID);
CREATE INDEX idx_cec_counterparty   ON Corporate_Ecosystem_Connections (Counterparty_Asset_ID);
CREATE INDEX idx_cec_endorsed       ON Corporate_Ecosystem_Connections (Endorsement_Flag) WHERE Endorsement_Flag = TRUE;
CREATE INDEX idx_cec_type           ON Corporate_Ecosystem_Connections (Connection_Type);

-- Cassandra_Signals: risk triage performance
CREATE INDEX idx_cassandra_score    ON Cassandra_Signals (Systemic_Risk_Score DESC);
CREATE INDEX idx_cassandra_asset    ON Cassandra_Signals (Target_Asset_ID)   WHERE Target_Asset_ID IS NOT NULL;
CREATE INDEX idx_cassandra_unrev    ON Cassandra_Signals (Analyst_Reviewed)  WHERE Analyst_Reviewed = FALSE;
CREATE INDEX idx_cassandra_date     ON Cassandra_Signals (Signal_Date DESC);

-- =============================================================================
-- UPDATED_AT AUTO-MAINTENANCE TRIGGER
-- =============================================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.Updated_At = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_exposure_clusters_updated_at
    BEFORE UPDATE ON Exposure_Clusters
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_asset_registry_updated_at
    BEFORE UPDATE ON Asset_Registry
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_cec_updated_at
    BEFORE UPDATE ON Corporate_Ecosystem_Connections
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_cassandra_updated_at
    BEFORE UPDATE ON Cassandra_Signals
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =============================================================================
-- SEED DATA — Exposure_Clusters taxonomy
-- =============================================================================

INSERT INTO Exposure_Clusters (Cluster_Label, Description, Theme_Thesis, Target_Weight, Vol_Regime_Factor)
VALUES
    ('SP500',      'S&P 500 large-cap equities',
     'Core US equity beta. Baseline allocation for risk-on regime.',                   0.2000, 1.0000),

    ('FTSE',       'FTSE 100 large-cap equities',
     'UK/European developed market diversification with GBP FX overlay.',              0.0500, 1.0500),

    ('EM',         'Emerging market equities',
     'High-growth frontier and emerging exposure: India, Vietnam, Saudi Arabia.',       0.0800, 1.4000),

    ('GOLD',       'Physical gold and gold-backed instruments',
     'Monetary debasement hedge; crisis liquidity reserve.',                            0.0800, 0.8000),

    ('SILVER',     'Physical silver and silver-backed instruments',
     'Industrial demand + monetary hedge dual-driver thesis.',                          0.0400, 1.2000),

    ('BTC',        'Bitcoin spot and regulated exposure vehicles',
     'Sovereign-grade digital scarcity asset; institutional adoption curve.',           0.0800, 2.0000),

    ('ETH',        'Ethereum spot and staking derivatives',
     'Programmable settlement layer; DeFi and tokenisation infrastructure.',            0.0400, 2.2000),

    ('SOL',        'Solana ecosystem instruments',
     'High-throughput L1 challenger; consumer crypto and payments rail.',               0.0200, 2.5000),

    ('XRP',        'XRP and cross-border payment instruments',
     'Institutional cross-border settlement; post-SEC clarity optionality.',            0.0200, 2.0000),

    ('HORIZON',    'Frontier technology and deep-disruption plays',
     'Pre-revenue or early-revenue companies redefining category structure by 2031.',   0.1200, 1.8000),

    ('KINGMAKER',  'Hidden titan-backed growth gems — Kingmaker Protocol',
     'Small/mid-cap companies with structural B2B dependencies on S&P 500 titans. '
     'Asymmetric upside from hidden supplier contracts, custom silicon mandates, '
     'and direct executive endorsements. Core alpha engine of Contrarian Radar.',       0.1500, 1.3000);

-- =============================================================================
-- END OF INITIALIZATION
-- =============================================================================
