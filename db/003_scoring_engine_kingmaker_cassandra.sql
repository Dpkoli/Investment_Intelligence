-- =============================================================================
-- Contrarian Radar — Step 3: Scoring Engine
-- Kingmaker Alpha Score + Cassandra Alert Dispatcher
-- Horizon: 2026–2031
-- =============================================================================

-- ── Enumerations ─────────────────────────────────────────────────────────────

CREATE TYPE score_driver AS ENUM (
    'Titan_Dependency',
    'Executive_Endorsement',
    'NLP_Signal_Strength',
    'Earnings_Sentiment',
    'AltData_Momentum',
    'Cassandra_Discount',
    'Tier_Proximity',
    'Flow_Momentum'
);

CREATE TYPE alert_severity AS ENUM (
    'INFO',       -- score 1–3
    'WATCH',      -- score 4–6
    'THREAT',     -- score 7–9
    'CRITICAL'    -- score 10
);

-- =============================================================================
-- TABLE 11: ASSET_ALPHA_SCORES
-- Point-in-time store for computed Kingmaker Alpha Scores.
-- One row per (Asset_ID, Computed_At) — full history retained for
-- regime-change attribution and backtesting.
-- =============================================================================

CREATE TABLE IF NOT EXISTS Asset_Alpha_Scores (
    Score_ID                BIGSERIAL           PRIMARY KEY,
    Asset_ID                INTEGER             NOT NULL REFERENCES Asset_Registry (Asset_ID) ON DELETE CASCADE,
    Computed_At             TIMESTAMPTZ         NOT NULL DEFAULT NOW(),

    -- Composite Kingmaker Alpha Score (0.00–100.00)
    KA_Score                NUMERIC(6, 3)       NOT NULL CHECK (KA_Score BETWEEN 0 AND 100),

    -- Component sub-scores (each 0.00–1.00 before weighting)
    Sub_Titan_Dependency    NUMERIC(5, 4),      -- Share_Of_Wallet_Est × tier multiplier
    Sub_Endorsement         NUMERIC(5, 4),      -- Endorsement_Flag + recency decay
    Sub_NLP_Strength        NUMERIC(5, 4),      -- avg confidence of recent Kingmaker_Trigger extractions
    Sub_Earnings_Sentiment  NUMERIC(5, 4),      -- normalised Sentiment_Score from latest transcript
    Sub_AltData_Momentum    NUMERIC(5, 4),      -- z-score composite across alt-data feeds
    Sub_Flow_Momentum       NUMERIC(5, 4),      -- Net_30D_Flows / AUM (ETF/ETP only)
    Cassandra_Discount      NUMERIC(5, 4),      -- penalty from active Cassandra signals

    -- Rank within KINGMAKER cluster at computation time
    Cluster_Rank            SMALLINT,
    Rank_Delta              SMALLINT,

    -- Signal counts feeding into this score
    NLP_Signal_Count        SMALLINT            DEFAULT 0,
    Cassandra_Signal_Count  SMALLINT            DEFAULT 0,
    AltData_Obs_Count       SMALLINT            DEFAULT 0,

    Score_Version           TEXT                NOT NULL DEFAULT '1.0',
    Created_At              TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  Asset_Alpha_Scores IS 'Point-in-time Kingmaker Alpha Scores (0-100). Full history retained for backtesting. KA_Score = weighted sum of 6 sub-scores minus Cassandra_Discount.';
COMMENT ON COLUMN Asset_Alpha_Scores.KA_Score IS 'Composite Kingmaker Alpha Score 0-100. >=80 = Tier-1 conviction, 60-79 = high watch, 40-59 = speculative, <40 = monitoring only.';
COMMENT ON COLUMN Asset_Alpha_Scores.Cassandra_Discount IS 'Active Cassandra penalty: sum(Systemic_Risk_Score) across open signals / 100, capped at 0.40 (max 40-point penalty).';

CREATE INDEX idx_scores_asset_time  ON Asset_Alpha_Scores (Asset_ID, Computed_At DESC);
CREATE INDEX idx_scores_ka_score    ON Asset_Alpha_Scores (KA_Score DESC);
CREATE INDEX idx_scores_rank        ON Asset_Alpha_Scores (Cluster_Rank) WHERE Cluster_Rank IS NOT NULL;

-- =============================================================================
-- TABLE 12: CASSANDRA_DISPATCH_LOG
-- Immutable audit log for every automated alert created by the dispatcher.
-- =============================================================================

CREATE TABLE IF NOT EXISTS Cassandra_Dispatch_Log (
    Dispatch_ID             BIGSERIAL           PRIMARY KEY,
    Cassandra_Signal_ID     INTEGER             NOT NULL REFERENCES Cassandra_Signals (Signal_ID) ON DELETE CASCADE,
    Trigger_Source          TEXT                NOT NULL,
    Trigger_Record_Type     TEXT                NOT NULL,
    Trigger_Record_ID       BIGINT              NOT NULL,
    Trigger_Condition       TEXT                NOT NULL,
    Observed_Value          NUMERIC(20, 6),
    Threshold_Value         NUMERIC(20, 6),
    Computed_Risk_Score     SMALLINT            NOT NULL,
    Alert_Severity          alert_severity      NOT NULL,
    Dispatched_At           TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  Cassandra_Dispatch_Log IS 'Immutable audit trail for every auto-dispatched Cassandra alert. Trigger_Record_ID references the PK of the row that fired the rule.';

CREATE INDEX idx_dispatch_signal    ON Cassandra_Dispatch_Log (Cassandra_Signal_ID);
CREATE INDEX idx_dispatch_severity  ON Cassandra_Dispatch_Log (Alert_Severity);
CREATE INDEX idx_dispatch_time      ON Cassandra_Dispatch_Log (Dispatched_At DESC);

-- =============================================================================
-- FUNCTION: fn_severity_from_score
-- =============================================================================

CREATE OR REPLACE FUNCTION fn_severity_from_score(p_score SMALLINT)
RETURNS alert_severity
LANGUAGE sql IMMUTABLE STRICT AS $$
    SELECT CASE
        WHEN p_score <= 3  THEN 'INFO'::alert_severity
        WHEN p_score <= 6  THEN 'WATCH'::alert_severity
        WHEN p_score <= 9  THEN 'THREAT'::alert_severity
        ELSE                    'CRITICAL'::alert_severity
    END;
$$;

-- =============================================================================
-- FUNCTION: fn_compute_kingmaker_alpha(p_asset_id)
-- ─────────────────────────────────────────────────────────────────────────────
-- KA_Score (0–100) formula v1.0:
--   Titan_Dependency   × 0.30
--   Endorsement        × 0.20   (with 365-day recency decay)
--   Tier_Proximity     × 0.10   (T1=1.0, T2=0.67, T3=0.33)
--   NLP_Strength       × 0.15   (avg confidence, Kingmaker_Trigger, 90-day)
--   Earnings_Sentiment × 0.10   (normalised latest transcript sentiment)
--   AltData_Momentum   × 0.10   (capped Z-score composite, 30-day)
--   Flow_Momentum      × 0.05   (Net_30D_Flows / AUM, ETF/ETP only)
--   − Cassandra_Discount × 0.40 (capped at 0.40)
-- =============================================================================

CREATE OR REPLACE FUNCTION fn_compute_kingmaker_alpha(p_asset_id INTEGER)
RETURNS NUMERIC(6,3)
LANGUAGE plpgsql AS $$
DECLARE
    v_asset             Asset_Registry%ROWTYPE;
    v_prev_rank         SMALLINT;
    v_titan_dep         NUMERIC(5,4) := 0;
    v_endorsement       NUMERIC(5,4) := 0;
    v_tier_prox         NUMERIC(5,4) := 0;
    v_nlp_strength      NUMERIC(5,4) := 0;
    v_earnings_sent     NUMERIC(5,4) := 0;
    v_altdata_mom       NUMERIC(5,4) := 0;
    v_flow_mom          NUMERIC(5,4) := 0;
    v_cassandra_disc    NUMERIC(5,4) := 0;
    v_best_connection   Corporate_Ecosystem_Connections%ROWTYPE;
    v_endorsement_days  INTEGER;
    v_latest_transcript Earnings_Call_Transcripts%ROWTYPE;
    v_nlp_avg_conf      NUMERIC(5,4);
    v_nlp_count         SMALLINT;
    v_z_avg             NUMERIC(8,4);
    v_alt_count         SMALLINT;
    v_cassandra_sum     INTEGER;
    v_cassandra_count   SMALLINT;
    v_raw_score         NUMERIC(8,4);
    v_final_score       NUMERIC(6,3);
    v_cluster_rank      SMALLINT;
    v_rank_delta        SMALLINT;
BEGIN
    SELECT * INTO v_asset FROM Asset_Registry WHERE Asset_ID = p_asset_id AND Is_Active = TRUE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Asset % not found or inactive', p_asset_id;
    END IF;

    -- Titan Dependency
    SELECT * INTO v_best_connection
    FROM Corporate_Ecosystem_Connections
    WHERE Counterparty_Asset_ID = p_asset_id AND Is_Active = TRUE
    ORDER BY COALESCE(Share_Of_Wallet_Est, 0) DESC LIMIT 1;
    IF FOUND THEN
        v_titan_dep := COALESCE(v_best_connection.Share_Of_Wallet_Est, 0.1);
    END IF;

    -- Tier Proximity
    v_tier_prox := CASE v_asset.Kingmaker_Tier
        WHEN 1 THEN 1.0 WHEN 2 THEN 0.67 WHEN 3 THEN 0.33 ELSE 0.0 END;

    -- Endorsement with 365-day linear recency decay
    IF v_best_connection.Endorsement_Flag IS TRUE THEN
        v_endorsement_days := EXTRACT(DAY FROM NOW() - v_best_connection.Endorsement_Date::TIMESTAMPTZ)::INTEGER;
        v_endorsement := GREATEST(0, 1.0 - (COALESCE(v_endorsement_days, 0)::NUMERIC / 365.0));
    END IF;

    -- NLP Signal Strength: avg confidence of Kingmaker_Trigger signals, 90-day window
    SELECT AVG(Confidence), COUNT(*) INTO v_nlp_avg_conf, v_nlp_count
    FROM NLP_Signal_Extractions
    WHERE Subject_Asset_ID = p_asset_id
      AND Signal_Type = 'Kingmaker_Trigger'
      AND Created_At >= NOW() - INTERVAL '90 days';
    v_nlp_strength := COALESCE(v_nlp_avg_conf, 0);
    v_nlp_count    := COALESCE(v_nlp_count, 0);

    -- Earnings Sentiment: normalise (-1..1) → (0..1)
    SELECT * INTO v_latest_transcript
    FROM Earnings_Call_Transcripts
    WHERE Asset_ID = p_asset_id AND NLP_Processed = TRUE
    ORDER BY Call_Date DESC LIMIT 1;
    v_earnings_sent := CASE WHEN FOUND AND v_latest_transcript.Sentiment_Score IS NOT NULL
        THEN (v_latest_transcript.Sentiment_Score + 1.0) / 2.0
        ELSE 0.5 END;

    -- Alt-Data Momentum: avg positive Z-score, capped at 3σ, 30-day window
    SELECT AVG(LEAST(Z_Score_52W, 3.0) / 3.0), COUNT(*) INTO v_z_avg, v_alt_count
    FROM Alt_Data_Observations
    WHERE Asset_ID = p_asset_id AND Z_Score_52W IS NOT NULL
      AND Observation_Date >= CURRENT_DATE - 30;
    v_altdata_mom := GREATEST(0, COALESCE(v_z_avg, 0));
    v_alt_count   := COALESCE(v_alt_count, 0);

    -- Flow Momentum: ETF/ETP only; 10% monthly inflow = 1.0
    IF v_asset.AUM IS NOT NULL AND v_asset.AUM > 0
       AND v_asset.Net_30D_Flows IS NOT NULL
       AND v_asset.Instrument_Type IN ('ETF','ETP') THEN
        v_flow_mom := GREATEST(0, LEAST(1.0, v_asset.Net_30D_Flows / (v_asset.AUM * 0.10)));
    ELSE
        v_flow_mom := 0.5;
    END IF;

    -- Cassandra Discount: sum of open risk scores / 100, capped at 0.40
    SELECT COALESCE(SUM(Systemic_Risk_Score), 0), COUNT(*) INTO v_cassandra_sum, v_cassandra_count
    FROM Cassandra_Signals WHERE Target_Asset_ID = p_asset_id AND Is_Resolved = FALSE;
    v_cassandra_disc  := LEAST(0.40, COALESCE(v_cassandra_sum, 0)::NUMERIC / 100.0);
    v_cassandra_count := COALESCE(v_cassandra_count, 0);

    -- Composite
    v_raw_score :=
          (v_titan_dep      * 0.30)
        + (v_endorsement    * 0.20)
        + (v_tier_prox      * 0.10)
        + (v_nlp_strength   * 0.15)
        + (v_earnings_sent  * 0.10)
        + (v_altdata_mom    * 0.10)
        + (v_flow_mom       * 0.05)
        - (v_cassandra_disc * 0.40);

    v_final_score := GREATEST(0, LEAST(100, ROUND(v_raw_score * 100, 3)));

    -- Cluster rank
    SELECT Cluster_Rank INTO v_prev_rank
    FROM Asset_Alpha_Scores WHERE Asset_ID = p_asset_id ORDER BY Computed_At DESC LIMIT 1;

    SELECT COUNT(*) + 1 INTO v_cluster_rank
    FROM (
        SELECT DISTINCT ON (aas.Asset_ID) aas.KA_Score
        FROM Asset_Alpha_Scores aas
        JOIN Asset_Registry ar ON ar.Asset_ID = aas.Asset_ID
        JOIN Exposure_Clusters ec ON ec.Cluster_ID = ar.Cluster_ID
        WHERE ec.Cluster_Label = 'KINGMAKER'
          AND ar.Is_Active = TRUE AND aas.Asset_ID <> p_asset_id
        ORDER BY aas.Asset_ID, aas.Computed_At DESC
    ) sub WHERE sub.KA_Score > v_final_score;

    v_rank_delta := CASE WHEN v_prev_rank IS NOT NULL THEN v_prev_rank - v_cluster_rank ELSE NULL END;

    INSERT INTO Asset_Alpha_Scores (
        Asset_ID, KA_Score,
        Sub_Titan_Dependency, Sub_Endorsement, Sub_NLP_Strength,
        Sub_Earnings_Sentiment, Sub_AltData_Momentum, Sub_Flow_Momentum,
        Cassandra_Discount, Cluster_Rank, Rank_Delta,
        NLP_Signal_Count, Cassandra_Signal_Count, AltData_Obs_Count
    ) VALUES (
        p_asset_id, v_final_score,
        v_titan_dep, v_endorsement, v_nlp_strength,
        v_earnings_sent, v_altdata_mom, v_flow_mom,
        v_cassandra_disc, v_cluster_rank, v_rank_delta,
        v_nlp_count, v_cassandra_count, v_alt_count
    );

    RETURN v_final_score;
END;
$$;

COMMENT ON FUNCTION fn_compute_kingmaker_alpha(INTEGER) IS
'Computes the Kingmaker Alpha Score (0-100) and persists it to Asset_Alpha_Scores. Weights: Titan_Dep 30%, Endorsement 20%, Tier 10%, NLP 15%, Sentiment 10%, AltData 10%, Flow 5%, minus Cassandra_Discount up to 40%.';

-- =============================================================================
-- FUNCTION: fn_dispatch_cassandra_alert
-- =============================================================================

CREATE OR REPLACE FUNCTION fn_dispatch_cassandra_alert(
    p_target_asset_id       INTEGER,
    p_target_cluster_id     INTEGER,
    p_signal_source         signal_source_type,
    p_source_handle         TEXT,
    p_signal_title          TEXT,
    p_raw_signal_text       TEXT,
    p_risk_score            SMALLINT,
    p_risk_vector           TEXT,
    p_related_connection_id INTEGER,
    p_trigger_source        TEXT,
    p_trigger_record_type   TEXT,
    p_trigger_record_id     BIGINT,
    p_trigger_condition     TEXT,
    p_observed_value        NUMERIC,
    p_threshold_value       NUMERIC
)
RETURNS INTEGER
LANGUAGE plpgsql AS $$
DECLARE
    v_signal_id  INTEGER;
    v_severity   alert_severity;
BEGIN
    v_severity := fn_severity_from_score(p_risk_score);

    INSERT INTO Cassandra_Signals (
        Target_Asset_ID, Target_Cluster_ID,
        Signal_Source, Source_Handle, Source_Credibility,
        Signal_Title, Raw_Signal_Text, Signal_Date,
        Systemic_Risk_Score, Risk_Vector,
        Related_Connection_ID, Analyst_Reviewed
    ) VALUES (
        p_target_asset_id, p_target_cluster_id,
        p_signal_source, p_source_handle, NULL,
        p_signal_title, p_raw_signal_text, CURRENT_DATE,
        p_risk_score, p_risk_vector,
        p_related_connection_id, FALSE
    ) RETURNING Signal_ID INTO v_signal_id;

    INSERT INTO Cassandra_Dispatch_Log (
        Cassandra_Signal_ID,
        Trigger_Source, Trigger_Record_Type, Trigger_Record_ID,
        Trigger_Condition, Observed_Value, Threshold_Value,
        Computed_Risk_Score, Alert_Severity
    ) VALUES (
        v_signal_id,
        p_trigger_source, p_trigger_record_type, p_trigger_record_id,
        p_trigger_condition, p_observed_value, p_threshold_value,
        p_risk_score, v_severity
    );

    RETURN v_signal_id;
END;
$$;

COMMENT ON FUNCTION fn_dispatch_cassandra_alert IS 'Atomically creates a Cassandra_Signals row and an immutable Cassandra_Dispatch_Log audit entry.';

-- =============================================================================
-- FUNCTION: fn_promote_nlp_to_connection
-- =============================================================================

CREATE OR REPLACE FUNCTION fn_promote_nlp_to_connection(p_extraction_id BIGINT)
RETURNS INTEGER
LANGUAGE plpgsql AS $$
DECLARE
    v_ext      NLP_Signal_Extractions%ROWTYPE;
    v_conn_id  INTEGER;
BEGIN
    SELECT * INTO v_ext FROM NLP_Signal_Extractions WHERE Extraction_ID = p_extraction_id;
    IF NOT FOUND THEN RAISE EXCEPTION 'Extraction % not found', p_extraction_id; END IF;
    IF v_ext.Confidence < 0.75 THEN RAISE EXCEPTION 'Confidence %.3f below threshold 0.75', v_ext.Confidence; END IF;
    IF v_ext.Subject_Asset_ID IS NULL OR v_ext.Object_Asset_ID IS NULL THEN
        RAISE EXCEPTION 'Both Subject_Asset_ID and Object_Asset_ID must be resolved before promotion';
    END IF;

    INSERT INTO Corporate_Ecosystem_Connections (
        Parent_Anchor_ID, Counterparty_Asset_ID, Connection_Type,
        Endorsement_Flag, Confidence_Score, Primary_Source_URL, Is_Active
    ) VALUES (
        v_ext.Subject_Asset_ID, v_ext.Object_Asset_ID,
        CASE v_ext.Signal_Type
            WHEN 'Custom_Silicon_Referenced' THEN 'Custom_Silicon'::connection_type
            WHEN 'Partnership_Announced'     THEN 'JV_Partner'::connection_type
            ELSE                                  'Supplier'::connection_type
        END,
        FALSE, ROUND(v_ext.Confidence * 10)::SMALLINT, NULL, TRUE
    )
    ON CONFLICT (Parent_Anchor_ID, Counterparty_Asset_ID, Connection_Type)
    DO UPDATE SET
        Confidence_Score = GREATEST(
            Corporate_Ecosystem_Connections.Confidence_Score,
            ROUND(v_ext.Confidence * 10)::SMALLINT
        ),
        Updated_At = NOW()
    RETURNING Connection_ID INTO v_conn_id;

    UPDATE NLP_Signal_Extractions
    SET Promoted_To_Connection = TRUE, Connection_ID = v_conn_id
    WHERE Extraction_ID = p_extraction_id;

    RETURN v_conn_id;
END;
$$;

COMMENT ON FUNCTION fn_promote_nlp_to_connection(BIGINT) IS 'Promotes a high-confidence (>=0.75) NLP extraction to Corporate_Ecosystem_Connections via UPSERT. Maps Signal_Type to Connection_Type.';

-- =============================================================================
-- TRIGGER: NLP → Cassandra auto-dispatch
-- =============================================================================

CREATE OR REPLACE FUNCTION trg_fn_nlp_cassandra_dispatch()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_risk_score SMALLINT;
    v_signal_id  INTEGER;
BEGIN
    IF NEW.Confidence < 0.75 THEN RETURN NEW; END IF;
    v_risk_score := CASE NEW.Signal_Type
        WHEN 'Customer_Concentration_Risk' THEN 7
        WHEN 'Regulatory_Headwind'         THEN 6
        WHEN 'Litigation_Mentioned'        THEN 5
        WHEN 'Geopolitical_Exposure'       THEN 6
        WHEN 'Guidance_Cut'                THEN 7
        WHEN 'Executive_Departure_Risk'    THEN 5
        ELSE NULL END;
    IF v_risk_score IS NULL THEN RETURN NEW; END IF;

    v_signal_id := fn_dispatch_cassandra_alert(
        NEW.Subject_Asset_ID, NULL,
        'Regulatory_Leak'::signal_source_type, 'nlp_pipeline',
        'Auto: ' || NEW.Signal_Type::TEXT || ' detected (conf ' || ROUND(NEW.Confidence * 100)::TEXT || '%)',
        COALESCE(NEW.Extracted_Text, '(see extraction ' || NEW.Extraction_ID || ')'),
        v_risk_score, NEW.Signal_Type::TEXT, NEW.Connection_ID,
        'nlp_extraction', 'NLP_Signal_Extractions', NEW.Extraction_ID,
        'Signal_Type=' || NEW.Signal_Type::TEXT || ' AND Confidence>=' || NEW.Confidence::TEXT,
        NEW.Confidence, 0.75
    );

    UPDATE NLP_Signal_Extractions
    SET Promoted_To_Signal = TRUE, Cassandra_Signal_ID = v_signal_id
    WHERE Extraction_ID = NEW.Extraction_ID;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_nlp_cassandra_dispatch
    AFTER INSERT ON NLP_Signal_Extractions
    FOR EACH ROW EXECUTE FUNCTION trg_fn_nlp_cassandra_dispatch();

-- =============================================================================
-- TRIGGER: Alt-Data anomaly → Cassandra auto-dispatch
-- =============================================================================

CREATE OR REPLACE FUNCTION trg_fn_altdata_cassandra_dispatch()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_risk_score SMALLINT;
    v_signal_id  INTEGER;
BEGIN
    IF NOT (NEW.Alert_Triggered = TRUE AND NEW.Z_Score_52W <= -2.0) THEN RETURN NEW; END IF;
    v_risk_score := CASE
        WHEN NEW.Z_Score_52W <= -4.0 THEN 9
        WHEN NEW.Z_Score_52W <= -3.0 THEN 7
        ELSE 5 END;

    v_signal_id := fn_dispatch_cassandra_alert(
        NEW.Asset_ID, NULL,
        'Anonymous_Filing'::signal_source_type, 'altdata_pipeline',
        'Auto: Alt-data anomaly — ' || NEW.Metric_Name || ' Z=' || ROUND(NEW.Z_Score_52W, 2)::TEXT || 'σ',
        'Metric: ' || NEW.Metric_Name || ' | Value: ' || NEW.Metric_Value::TEXT ||
        ' | Z-Score: ' || NEW.Z_Score_52W::TEXT || ' | Date: ' || NEW.Observation_Date::TEXT,
        v_risk_score, 'AltData_Anomaly_' || NEW.Metric_Name, NULL,
        'alt_data_anomaly', 'Alt_Data_Observations', NEW.Observation_ID,
        'Z_Score_52W <= -2.0 AND Alert_Triggered = TRUE',
        NEW.Z_Score_52W, -2.0
    );
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_altdata_cassandra_dispatch
    AFTER INSERT OR UPDATE OF Alert_Triggered, Z_Score_52W ON Alt_Data_Observations
    FOR EACH ROW EXECUTE FUNCTION trg_fn_altdata_cassandra_dispatch();

-- =============================================================================
-- TRIGGER: Earnings sentiment collapse → Cassandra auto-dispatch
-- =============================================================================

CREATE OR REPLACE FUNCTION trg_fn_sentiment_cassandra_dispatch()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_risk_score SMALLINT;
    v_signal_id  INTEGER;
BEGIN
    IF NOT (NEW.NLP_Processed = TRUE
            AND NEW.Confidence_Delta IS NOT NULL
            AND NEW.Confidence_Delta < -0.15) THEN RETURN NEW; END IF;
    v_risk_score := CASE
        WHEN NEW.Confidence_Delta < -0.40 THEN 8
        WHEN NEW.Confidence_Delta < -0.25 THEN 6
        ELSE 4 END;

    v_signal_id := fn_dispatch_cassandra_alert(
        NEW.Asset_ID, NULL,
        'Influencer'::signal_source_type, 'earnings_nlp_pipeline',
        'Auto: Earnings sentiment collapse — ' || NEW.Fiscal_Quarter ||
            ' delta=' || ROUND(NEW.Confidence_Delta, 3)::TEXT,
        'Quarter: ' || NEW.Fiscal_Quarter || ' | Sentiment: ' ||
        COALESCE(NEW.Sentiment_Score::TEXT, 'N/A') ||
        ' | Delta vs prior: ' || NEW.Confidence_Delta::TEXT,
        v_risk_score, 'Earnings_Sentiment_Collapse', NULL,
        'sentiment_delta', 'Earnings_Call_Transcripts', NEW.Transcript_ID,
        'Confidence_Delta < -0.15 on NLP_Processed transition',
        NEW.Confidence_Delta, -0.15
    );
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_sentiment_cassandra_dispatch
    AFTER UPDATE OF NLP_Processed ON Earnings_Call_Transcripts
    FOR EACH ROW EXECUTE FUNCTION trg_fn_sentiment_cassandra_dispatch();

-- =============================================================================
-- FUNCTION: fn_refresh_all_kingmaker_scores()
-- =============================================================================

CREATE OR REPLACE FUNCTION fn_refresh_all_kingmaker_scores()
RETURNS TABLE (Asset_ID INTEGER, Ticker VARCHAR(20), KA_Score NUMERIC(6,3))
LANGUAGE plpgsql AS $$
DECLARE v_rec RECORD;
BEGIN
    FOR v_rec IN
        SELECT ar.Asset_ID, ar.Ticker
        FROM Asset_Registry ar
        JOIN Exposure_Clusters ec ON ec.Cluster_ID = ar.Cluster_ID
        WHERE ec.Cluster_Label = 'KINGMAKER' AND ar.Is_Active = TRUE
        ORDER BY ar.Asset_ID
    LOOP
        Asset_ID := v_rec.Asset_ID;
        Ticker   := v_rec.Ticker;
        KA_Score := fn_compute_kingmaker_alpha(v_rec.Asset_ID);
        RETURN NEXT;
    END LOOP;
END;
$$;

COMMENT ON FUNCTION fn_refresh_all_kingmaker_scores() IS 'Batch recomputes KA_Score for all active KINGMAKER assets. Call nightly via pg_cron or equivalent scheduler.';

-- =============================================================================
-- VIEWS
-- =============================================================================

-- V1: Kingmaker Leaderboard
CREATE OR REPLACE VIEW v_kingmaker_leaderboard AS
SELECT
    ar.Asset_ID, ar.Ticker, ar.Asset_Name, ar.Kingmaker_Tier,
    ar.Live_Spot_Price, ar.Price_Currency,
    s.KA_Score, s.Cluster_Rank, s.Rank_Delta,
    s.Sub_Titan_Dependency, s.Sub_Endorsement, s.Sub_NLP_Strength,
    s.Sub_Earnings_Sentiment, s.Sub_AltData_Momentum, s.Sub_Flow_Momentum,
    s.Cassandra_Discount, s.NLP_Signal_Count, s.Cassandra_Signal_Count,
    s.Computed_At,
    CASE WHEN s.KA_Score >= 80 THEN 'Tier-1 Conviction'
         WHEN s.KA_Score >= 60 THEN 'High Watch'
         WHEN s.KA_Score >= 40 THEN 'Speculative'
         ELSE                        'Monitoring' END AS Conviction_Label,
    cec.Connection_Type     AS Primary_Connection_Type,
    cec.Share_Of_Wallet_Est AS Primary_Share_Of_Wallet,
    cec.Endorsement_Flag    AS Titan_Endorsed,
    cec.Endorsement_Source
FROM Asset_Registry ar
JOIN Exposure_Clusters ec ON ec.Cluster_ID = ar.Cluster_ID
JOIN LATERAL (
    SELECT * FROM Asset_Alpha_Scores
    WHERE Asset_ID = ar.Asset_ID ORDER BY Computed_At DESC LIMIT 1
) s ON TRUE
LEFT JOIN LATERAL (
    SELECT * FROM Corporate_Ecosystem_Connections
    WHERE Counterparty_Asset_ID = ar.Asset_ID AND Is_Active = TRUE
    ORDER BY COALESCE(Share_Of_Wallet_Est, 0) DESC LIMIT 1
) cec ON TRUE
WHERE ec.Cluster_Label = 'KINGMAKER' AND ar.Is_Active = TRUE
ORDER BY s.KA_Score DESC;

COMMENT ON VIEW v_kingmaker_leaderboard IS 'Live Kingmaker leaderboard: latest KA_Score per active KINGMAKER asset with full sub-score breakdown and conviction label.';

-- V2: Cassandra Triage Queue
CREATE OR REPLACE VIEW v_cassandra_triage AS
SELECT
    cs.Signal_ID, cs.Signal_Date,
    fn_severity_from_score(cs.Systemic_Risk_Score) AS Severity,
    cs.Systemic_Risk_Score, cs.Signal_Title,
    cs.Signal_Source, cs.Source_Handle, cs.Risk_Vector,
    ar.Ticker AS Target_Ticker, ar.Asset_Name AS Target_Asset_Name,
    ec.Cluster_Label AS Target_Cluster,
    cs.Analyst_Reviewed, cs.Related_Connection_ID,
    dl.Trigger_Source, dl.Trigger_Condition, dl.Dispatched_At,
    cs.Primary_Source_URL, cs.Created_At
FROM Cassandra_Signals cs
LEFT JOIN Asset_Registry ar    ON ar.Asset_ID   = cs.Target_Asset_ID
LEFT JOIN Exposure_Clusters ec ON ec.Cluster_ID = cs.Target_Cluster_ID
    OR (cs.Target_Asset_ID IS NOT NULL AND ec.Cluster_ID = ar.Cluster_ID)
LEFT JOIN LATERAL (
    SELECT * FROM Cassandra_Dispatch_Log
    WHERE Cassandra_Signal_ID = cs.Signal_ID ORDER BY Dispatched_At DESC LIMIT 1
) dl ON TRUE
WHERE cs.Is_Resolved = FALSE
ORDER BY cs.Systemic_Risk_Score DESC, cs.Signal_Date DESC;

COMMENT ON VIEW v_cassandra_triage IS 'Analyst triage queue: unresolved Cassandra signals ordered by risk severity with dispatch audit context.';

-- V3: Ecosystem Graph Summary
CREATE OR REPLACE VIEW v_ecosystem_graph AS
SELECT
    cec.Connection_ID, cec.Connection_Type,
    pa.Asset_ID AS Titan_Asset_ID, pa.Ticker AS Titan_Ticker, pa.Asset_Name AS Titan_Name,
    cp.Asset_ID AS Target_Asset_ID, cp.Ticker AS Target_Ticker,
    cp.Asset_Name AS Target_Name, cp.Kingmaker_Tier AS Target_Tier,
    cec.Share_Of_Wallet_Est, cec.Revenue_Impact_USD_Est,
    cec.Endorsement_Flag, cec.Endorsement_Source, cec.Endorsement_Date,
    cec.Confidence_Score AS Connection_Confidence,
    s.KA_Score, s.Computed_At AS Score_As_Of,
    COALESCE(risk.Open_Signal_Count, 0) AS Open_Cassandra_Signals,
    COALESCE(risk.Max_Risk_Score, 0)    AS Max_Cassandra_Risk_Score
FROM Corporate_Ecosystem_Connections cec
JOIN Asset_Registry pa ON pa.Asset_ID = cec.Parent_Anchor_ID
JOIN Asset_Registry cp ON cp.Asset_ID = cec.Counterparty_Asset_ID
LEFT JOIN LATERAL (
    SELECT KA_Score, Computed_At FROM Asset_Alpha_Scores
    WHERE Asset_ID = cp.Asset_ID ORDER BY Computed_At DESC LIMIT 1
) s ON TRUE
LEFT JOIN LATERAL (
    SELECT COUNT(*) AS Open_Signal_Count, MAX(Systemic_Risk_Score) AS Max_Risk_Score
    FROM Cassandra_Signals
    WHERE Target_Asset_ID = cp.Asset_ID AND Is_Resolved = FALSE
) risk ON TRUE
WHERE cec.Is_Active = TRUE
ORDER BY cec.Share_Of_Wallet_Est DESC NULLS LAST;

COMMENT ON VIEW v_ecosystem_graph IS 'Full titan → counterparty dependency graph with latest KA_Score and active Cassandra risk overlay.';

-- V4: Pipeline Health Dashboard
CREATE OR REPLACE VIEW v_pipeline_health AS
SELECT
    dsr.Source_ID, dsr.Source_Name, dsr.Source_Category,
    dsr.Is_Active AS Source_Active, dsr.Poll_Frequency_Min,
    COUNT(ij.Job_ID) AS Jobs_Last_24h,
    SUM(CASE WHEN ij.Job_Status = 'Completed' THEN 1 ELSE 0 END) AS Jobs_OK,
    SUM(CASE WHEN ij.Job_Status = 'Failed'    THEN 1 ELSE 0 END) AS Jobs_Failed,
    SUM(CASE WHEN ij.Job_Status = 'Running'   THEN 1 ELSE 0 END) AS Jobs_Running,
    ROUND(AVG(ij.Duration_Seconds), 2) AS Avg_Duration_Sec,
    MAX(ij.Started_At)                 AS Last_Run_At,
    SUM(ij.Records_Inserted)           AS Total_Inserted_24h,
    SUM(ij.Records_Rejected)           AS Total_Rejected_24h,
    MAX(ij.Error_Message)              AS Last_Error
FROM Data_Source_Registry dsr
LEFT JOIN Ingestion_Jobs ij ON ij.Source_ID = dsr.Source_ID
    AND ij.Started_At >= NOW() - INTERVAL '24 hours'
GROUP BY dsr.Source_ID, dsr.Source_Name, dsr.Source_Category,
         dsr.Is_Active, dsr.Poll_Frequency_Min
ORDER BY Jobs_Failed DESC, dsr.Source_Name;

COMMENT ON VIEW v_pipeline_health IS '24-hour ingestion health dashboard: job counts, avg latency, and throughput per data source.';

-- V5: Score Attribution Breakdown
CREATE OR REPLACE VIEW v_score_attribution AS
SELECT
    aas.Score_ID, aas.Asset_ID, ar.Ticker, aas.KA_Score, aas.Computed_At,
    driver.Driver_Name, driver.Raw_Value, driver.Weight,
    ROUND(driver.Raw_Value * driver.Weight * 100, 3) AS Weighted_Points
FROM Asset_Alpha_Scores aas
JOIN Asset_Registry ar ON ar.Asset_ID = aas.Asset_ID
JOIN LATERAL (
    VALUES
        ('Titan_Dependency'::TEXT,   aas.Sub_Titan_Dependency,    0.30::NUMERIC),
        ('Executive_Endorsement',    aas.Sub_Endorsement,         0.20),
        ('NLP_Signal_Strength',      aas.Sub_NLP_Strength,        0.15),
        ('Earnings_Sentiment',       aas.Sub_Earnings_Sentiment,  0.10),
        ('AltData_Momentum',         aas.Sub_AltData_Momentum,    0.10),
        ('Flow_Momentum',            aas.Sub_Flow_Momentum,       0.05),
        ('Cassandra_Discount',       -aas.Cassandra_Discount,     0.40)
) driver(Driver_Name, Raw_Value, Weight) ON TRUE
ORDER BY aas.Computed_At DESC, aas.Asset_ID, driver.Weight DESC;

COMMENT ON VIEW v_score_attribution IS 'Unpivoted score attribution: one row per driver per computation. Use for waterfall charts and attribution reports.';

-- =============================================================================
-- END OF STEP 3
-- =============================================================================
