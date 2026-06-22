-- =============================================================================
-- Contrarian Radar — Step 4: Personalization Schema + Full RLS Policy Suite
-- Tables 13–18: Analyst Profiles, Portfolios, Positions, Watchlists, Audit Log
-- Row Level Security for all 18 tables
-- Horizon: 2026–2031
-- =============================================================================

-- =============================================================================
-- TABLE 13: ANALYST_PROFILES
-- Extends Supabase auth.users with role, preferences, and alert config.
-- Profile_ID mirrors auth.users.id so RLS uses auth.uid() directly.
-- =============================================================================

CREATE TABLE IF NOT EXISTS Analyst_Profiles (
    Profile_ID              UUID            PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
    Display_Name            TEXT            NOT NULL,
    Role                    TEXT            NOT NULL DEFAULT 'analyst'
                                            CHECK (Role IN ('admin', 'analyst', 'viewer')),
    Organisation            TEXT,
    Default_Horizon_Years   SMALLINT        NOT NULL DEFAULT 5 CHECK (Default_Horizon_Years BETWEEN 1 AND 10),
    Risk_Tolerance          TEXT            NOT NULL DEFAULT 'moderate'
                                            CHECK (Risk_Tolerance IN ('conservative', 'moderate', 'aggressive')),
    Preferred_Clusters      cluster_label[],
    Min_KA_Score_Filter     NUMERIC(6,3)    DEFAULT 40,
    Email_Alerts_Enabled    BOOLEAN         NOT NULL DEFAULT TRUE,
    Min_Alert_Severity      alert_severity  NOT NULL DEFAULT 'WATCH',
    Webhook_URL             TEXT,
    Created_At              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    Updated_At              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  Analyst_Profiles IS 'Extends auth.users with role, personalization settings, and alert preferences. Profile_ID = auth.uid().';
COMMENT ON COLUMN Analyst_Profiles.Min_Alert_Severity IS 'Minimum Cassandra alert severity level this analyst receives notifications for.';

CREATE TRIGGER trg_analyst_profiles_updated_at
    BEFORE UPDATE ON Analyst_Profiles FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =============================================================================
-- TABLE 14: PORTFOLIOS
-- =============================================================================

CREATE TABLE IF NOT EXISTS Portfolios (
    Portfolio_ID            SERIAL          PRIMARY KEY,
    Analyst_ID              UUID            NOT NULL REFERENCES Analyst_Profiles (Profile_ID) ON DELETE CASCADE,
    Portfolio_Name          TEXT            NOT NULL,
    Description             TEXT,
    Base_Currency           CHAR(3)         NOT NULL DEFAULT 'USD',
    Total_AUM_USD           NUMERIC(20, 2),
    Benchmark_Ticker        VARCHAR(20),
    Is_Active               BOOLEAN         NOT NULL DEFAULT TRUE,
    Created_At              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    Updated_At              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_portfolio_name UNIQUE (Analyst_ID, Portfolio_Name)
);

COMMENT ON TABLE Portfolios IS 'Named model portfolios belonging to an analyst.';

CREATE INDEX idx_portfolio_analyst ON Portfolios (Analyst_ID);

CREATE TRIGGER trg_portfolios_updated_at
    BEFORE UPDATE ON Portfolios FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =============================================================================
-- TABLE 15: PORTFOLIO_POSITIONS
-- =============================================================================

CREATE TABLE IF NOT EXISTS Portfolio_Positions (
    Position_ID             SERIAL          PRIMARY KEY,
    Portfolio_ID            INTEGER         NOT NULL REFERENCES Portfolios (Portfolio_ID) ON DELETE CASCADE,
    Asset_ID                INTEGER         NOT NULL REFERENCES Asset_Registry (Asset_ID) ON DELETE RESTRICT,
    Target_Weight           NUMERIC(5, 4)   NOT NULL CHECK (Target_Weight BETWEEN 0 AND 1),
    Current_Weight          NUMERIC(5, 4)   CHECK (Current_Weight BETWEEN 0 AND 1),
    Entry_Price             NUMERIC(18, 6),
    Entry_Date              DATE,
    Position_Size_USD       NUMERIC(20, 2),
    Stop_Loss_Pct           NUMERIC(5, 4)   CHECK (Stop_Loss_Pct BETWEEN 0 AND 1),
    Take_Profit_Pct         NUMERIC(5, 4)   CHECK (Take_Profit_Pct BETWEEN 0 AND 1),
    Conviction_Override     SMALLINT        CHECK (Conviction_Override BETWEEN 1 AND 5),
    Notes                   TEXT,
    Is_Active               BOOLEAN         NOT NULL DEFAULT TRUE,
    Created_At              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    Updated_At              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_portfolio_asset UNIQUE (Portfolio_ID, Asset_ID)
);

COMMENT ON TABLE  Portfolio_Positions IS 'Individual asset allocations within a model portfolio.';
COMMENT ON COLUMN Portfolio_Positions.Conviction_Override IS 'Analyst manual conviction override (1-5). Overrides the KA_Score conviction label in position sizing.';

CREATE INDEX idx_position_portfolio ON Portfolio_Positions (Portfolio_ID);
CREATE INDEX idx_position_asset     ON Portfolio_Positions (Asset_ID);

CREATE TRIGGER trg_positions_updated_at
    BEFORE UPDATE ON Portfolio_Positions FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =============================================================================
-- TABLE 16: WATCHLISTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS Watchlists (
    Watchlist_ID            SERIAL          PRIMARY KEY,
    Analyst_ID              UUID            NOT NULL REFERENCES Analyst_Profiles (Profile_ID) ON DELETE CASCADE,
    Watchlist_Name          TEXT            NOT NULL,
    Description             TEXT,
    Min_KA_Score            NUMERIC(6, 3)   DEFAULT 0,
    Max_Cassandra_Risk      SMALLINT        DEFAULT 10 CHECK (Max_Cassandra_Risk BETWEEN 1 AND 10),
    Alert_On_Score_Change   BOOLEAN         NOT NULL DEFAULT FALSE,
    Score_Change_Threshold  NUMERIC(5, 2)   DEFAULT 5.0,
    Is_Active               BOOLEAN         NOT NULL DEFAULT TRUE,
    Created_At              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    Updated_At              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_watchlist_name UNIQUE (Analyst_ID, Watchlist_Name)
);

COMMENT ON TABLE  Watchlists IS 'Custom asset collections per analyst with independent alert thresholds.';
COMMENT ON COLUMN Watchlists.Score_Change_Threshold IS 'Alert fires if KA_Score moves by this many points between consecutive computations.';

CREATE INDEX idx_watchlist_analyst ON Watchlists (Analyst_ID);

CREATE TRIGGER trg_watchlists_updated_at
    BEFORE UPDATE ON Watchlists FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =============================================================================
-- TABLE 17: WATCHLIST_ITEMS
-- =============================================================================

CREATE TABLE IF NOT EXISTS Watchlist_Items (
    Item_ID                 SERIAL          PRIMARY KEY,
    Watchlist_ID            INTEGER         NOT NULL REFERENCES Watchlists (Watchlist_ID) ON DELETE CASCADE,
    Asset_ID                INTEGER         NOT NULL REFERENCES Asset_Registry (Asset_ID) ON DELETE CASCADE,
    Notes                   TEXT,
    Added_At                TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_watchlist_item UNIQUE (Watchlist_ID, Asset_ID)
);

COMMENT ON TABLE Watchlist_Items IS 'Bridge table between Watchlists and Asset_Registry.';

CREATE INDEX idx_watchlist_items_wl    ON Watchlist_Items (Watchlist_ID);
CREATE INDEX idx_watchlist_items_asset ON Watchlist_Items (Asset_ID);

-- =============================================================================
-- TABLE 18: AUDIT_LOG
-- Append-only compliance trail. No UPDATE or DELETE ever permitted.
-- =============================================================================

CREATE TABLE IF NOT EXISTS Audit_Log (
    Audit_ID                BIGSERIAL       PRIMARY KEY,
    Analyst_ID              UUID            REFERENCES Analyst_Profiles (Profile_ID) ON DELETE SET NULL,
    Action                  TEXT            NOT NULL,
    Table_Name              TEXT            NOT NULL,
    Record_ID               TEXT,
    Old_Values              JSONB,
    New_Values              JSONB,
    IP_Address              INET,
    User_Agent              TEXT,
    Created_At              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE Audit_Log IS 'Append-only compliance audit trail. No UPDATE or DELETE permitted. Admin SELECT only.';

CREATE INDEX idx_audit_analyst ON Audit_Log (Analyst_ID);
CREATE INDEX idx_audit_table   ON Audit_Log (Table_Name, Created_At DESC);
CREATE INDEX idx_audit_time    ON Audit_Log (Created_At DESC);

-- =============================================================================
-- HELPER: fn_is_admin()
-- SECURITY DEFINER prevents RLS recursion when policies query Analyst_Profiles.
-- =============================================================================

CREATE OR REPLACE FUNCTION fn_is_admin()
RETURNS BOOLEAN LANGUAGE sql STABLE SECURITY DEFINER AS $$
    SELECT EXISTS (
        SELECT 1 FROM Analyst_Profiles
        WHERE Profile_ID = auth.uid() AND Role = 'admin'
    );
$$;

COMMENT ON FUNCTION fn_is_admin() IS 'Returns TRUE when auth.uid() maps to an admin-role Analyst_Profile. SECURITY DEFINER prevents infinite recursion in RLS policies.';

-- =============================================================================
-- ROW LEVEL SECURITY — Full Policy Suite (18 tables)
-- Reference tables       → authenticated read; admin write
-- Operational tables     → authenticated read; analyst insert; admin all
-- Pipeline/scoring tables → authenticated read; service_role insert; admin all
-- Personalisation tables → owner-scoped CRUD via auth.uid()
-- Audit_Log              → admin read; append-only via service_role
-- =============================================================================

-- Exposure_Clusters
ALTER TABLE Exposure_Clusters ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ec_read_authenticated" ON Exposure_Clusters FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY "ec_write_admin"        ON Exposure_Clusters FOR ALL   TO authenticated USING (fn_is_admin()) WITH CHECK (fn_is_admin());

-- Asset_Registry
ALTER TABLE Asset_Registry ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ar_read_authenticated" ON Asset_Registry FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY "ar_write_admin"        ON Asset_Registry FOR ALL   TO authenticated USING (fn_is_admin()) WITH CHECK (fn_is_admin());

-- Corporate_Ecosystem_Connections
ALTER TABLE Corporate_Ecosystem_Connections ENABLE ROW LEVEL SECURITY;
CREATE POLICY "cec_read_authenticated" ON Corporate_Ecosystem_Connections FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY "cec_write_admin"        ON Corporate_Ecosystem_Connections FOR ALL   TO authenticated USING (fn_is_admin()) WITH CHECK (fn_is_admin());

-- Cassandra_Signals
ALTER TABLE Cassandra_Signals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "cs_read_authenticated" ON Cassandra_Signals FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY "cs_insert_analyst"     ON Cassandra_Signals FOR INSERT TO authenticated WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "cs_update_admin"       ON Cassandra_Signals FOR UPDATE TO authenticated USING (fn_is_admin()) WITH CHECK (fn_is_admin());
CREATE POLICY "cs_delete_admin"       ON Cassandra_Signals FOR DELETE TO authenticated USING (fn_is_admin());

-- Data_Source_Registry
ALTER TABLE Data_Source_Registry ENABLE ROW LEVEL SECURITY;
CREATE POLICY "dsr_read_authenticated" ON Data_Source_Registry FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY "dsr_write_admin"        ON Data_Source_Registry FOR ALL   TO authenticated USING (fn_is_admin()) WITH CHECK (fn_is_admin());

-- Ingestion_Jobs
ALTER TABLE Ingestion_Jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ij_read_authenticated" ON Ingestion_Jobs FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY "ij_write_admin"        ON Ingestion_Jobs FOR ALL   TO authenticated USING (fn_is_admin()) WITH CHECK (fn_is_admin());

-- SEC_Edgar_Filings
ALTER TABLE SEC_Edgar_Filings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "sef_read_authenticated" ON SEC_Edgar_Filings FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY "sef_write_admin"        ON SEC_Edgar_Filings FOR ALL   TO authenticated USING (fn_is_admin()) WITH CHECK (fn_is_admin());

-- Earnings_Call_Transcripts
ALTER TABLE Earnings_Call_Transcripts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ect_read_authenticated" ON Earnings_Call_Transcripts FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY "ect_write_admin"        ON Earnings_Call_Transcripts FOR ALL   TO authenticated USING (fn_is_admin()) WITH CHECK (fn_is_admin());

-- NLP_Signal_Extractions
ALTER TABLE NLP_Signal_Extractions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "nlp_read_authenticated" ON NLP_Signal_Extractions FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY "nlp_write_admin"        ON NLP_Signal_Extractions FOR ALL   TO authenticated USING (fn_is_admin()) WITH CHECK (fn_is_admin());

-- Alt_Data_Observations
ALTER TABLE Alt_Data_Observations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ado_read_authenticated" ON Alt_Data_Observations FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY "ado_write_admin"        ON Alt_Data_Observations FOR ALL   TO authenticated USING (fn_is_admin()) WITH CHECK (fn_is_admin());

-- Asset_Alpha_Scores
ALTER TABLE Asset_Alpha_Scores ENABLE ROW LEVEL SECURITY;
CREATE POLICY "aas_read_authenticated" ON Asset_Alpha_Scores FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY "aas_write_admin"        ON Asset_Alpha_Scores FOR ALL   TO authenticated USING (fn_is_admin()) WITH CHECK (fn_is_admin());

-- Cassandra_Dispatch_Log (append-only: no UPDATE/DELETE policies)
ALTER TABLE Cassandra_Dispatch_Log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "cdl_read_admin" ON Cassandra_Dispatch_Log FOR SELECT TO authenticated USING (fn_is_admin());

-- Analyst_Profiles
ALTER TABLE Analyst_Profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ap_read_own_or_admin" ON Analyst_Profiles FOR SELECT TO authenticated USING (Profile_ID = auth.uid() OR fn_is_admin());
CREATE POLICY "ap_insert_own"        ON Analyst_Profiles FOR INSERT TO authenticated WITH CHECK (Profile_ID = auth.uid());
CREATE POLICY "ap_update_own"        ON Analyst_Profiles FOR UPDATE TO authenticated USING (Profile_ID = auth.uid()) WITH CHECK (Profile_ID = auth.uid());
CREATE POLICY "ap_delete_admin"      ON Analyst_Profiles FOR DELETE TO authenticated USING (fn_is_admin());

-- Portfolios
ALTER TABLE Portfolios ENABLE ROW LEVEL SECURITY;
CREATE POLICY "port_read_own_or_admin"   ON Portfolios FOR SELECT TO authenticated USING (Analyst_ID = auth.uid() OR fn_is_admin());
CREATE POLICY "port_insert_own"          ON Portfolios FOR INSERT TO authenticated WITH CHECK (Analyst_ID = auth.uid());
CREATE POLICY "port_update_own"          ON Portfolios FOR UPDATE TO authenticated USING (Analyst_ID = auth.uid()) WITH CHECK (Analyst_ID = auth.uid());
CREATE POLICY "port_delete_own_or_admin" ON Portfolios FOR DELETE TO authenticated USING (Analyst_ID = auth.uid() OR fn_is_admin());

-- Portfolio_Positions (inherits from parent portfolio ownership)
ALTER TABLE Portfolio_Positions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "pp_read_owner" ON Portfolio_Positions FOR SELECT TO authenticated USING (
    EXISTS (SELECT 1 FROM Portfolios p WHERE p.Portfolio_ID = Portfolio_Positions.Portfolio_ID AND (p.Analyst_ID = auth.uid() OR fn_is_admin()))
);
CREATE POLICY "pp_insert_owner" ON Portfolio_Positions FOR INSERT TO authenticated WITH CHECK (
    EXISTS (SELECT 1 FROM Portfolios p WHERE p.Portfolio_ID = Portfolio_Positions.Portfolio_ID AND p.Analyst_ID = auth.uid())
);
CREATE POLICY "pp_update_owner" ON Portfolio_Positions FOR UPDATE TO authenticated USING (
    EXISTS (SELECT 1 FROM Portfolios p WHERE p.Portfolio_ID = Portfolio_Positions.Portfolio_ID AND p.Analyst_ID = auth.uid())
);
CREATE POLICY "pp_delete_owner" ON Portfolio_Positions FOR DELETE TO authenticated USING (
    EXISTS (SELECT 1 FROM Portfolios p WHERE p.Portfolio_ID = Portfolio_Positions.Portfolio_ID AND (p.Analyst_ID = auth.uid() OR fn_is_admin()))
);

-- Watchlists
ALTER TABLE Watchlists ENABLE ROW LEVEL SECURITY;
CREATE POLICY "wl_read_own_or_admin"   ON Watchlists FOR SELECT TO authenticated USING (Analyst_ID = auth.uid() OR fn_is_admin());
CREATE POLICY "wl_insert_own"          ON Watchlists FOR INSERT TO authenticated WITH CHECK (Analyst_ID = auth.uid());
CREATE POLICY "wl_update_own"          ON Watchlists FOR UPDATE TO authenticated USING (Analyst_ID = auth.uid()) WITH CHECK (Analyst_ID = auth.uid());
CREATE POLICY "wl_delete_own_or_admin" ON Watchlists FOR DELETE TO authenticated USING (Analyst_ID = auth.uid() OR fn_is_admin());

-- Watchlist_Items
ALTER TABLE Watchlist_Items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "wli_read_owner" ON Watchlist_Items FOR SELECT TO authenticated USING (
    EXISTS (SELECT 1 FROM Watchlists w WHERE w.Watchlist_ID = Watchlist_Items.Watchlist_ID AND (w.Analyst_ID = auth.uid() OR fn_is_admin()))
);
CREATE POLICY "wli_insert_owner" ON Watchlist_Items FOR INSERT TO authenticated WITH CHECK (
    EXISTS (SELECT 1 FROM Watchlists w WHERE w.Watchlist_ID = Watchlist_Items.Watchlist_ID AND w.Analyst_ID = auth.uid())
);
CREATE POLICY "wli_delete_owner" ON Watchlist_Items FOR DELETE TO authenticated USING (
    EXISTS (SELECT 1 FROM Watchlists w WHERE w.Watchlist_ID = Watchlist_Items.Watchlist_ID AND (w.Analyst_ID = auth.uid() OR fn_is_admin()))
);

-- Audit_Log
ALTER TABLE Audit_Log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "al_read_admin" ON Audit_Log FOR SELECT TO authenticated USING (fn_is_admin());

-- =============================================================================
-- AUTO-AUDIT TRIGGER (attached to high-value write targets)
-- =============================================================================

CREATE OR REPLACE FUNCTION fn_audit_trigger()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    INSERT INTO Audit_Log (Analyst_ID, Action, Table_Name, Record_ID, Old_Values, New_Values)
    VALUES (
        auth.uid(), TG_OP, TG_TABLE_NAME,
        CASE TG_OP WHEN 'DELETE' THEN OLD.ctid::TEXT ELSE NEW.ctid::TEXT END,
        CASE TG_OP WHEN 'INSERT' THEN NULL ELSE to_jsonb(OLD) END,
        CASE TG_OP WHEN 'DELETE' THEN NULL ELSE to_jsonb(NEW) END
    );
    RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE TRIGGER trg_audit_cassandra_signals
    AFTER INSERT OR UPDATE OR DELETE ON Cassandra_Signals
    FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();

CREATE TRIGGER trg_audit_cec
    AFTER INSERT OR UPDATE OR DELETE ON Corporate_Ecosystem_Connections
    FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();

CREATE TRIGGER trg_audit_portfolio_positions
    AFTER INSERT OR UPDATE OR DELETE ON Portfolio_Positions
    FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();

-- =============================================================================
-- PERSONALISED VIEWS (scoped via RLS on underlying tables)
-- =============================================================================

-- V6: My Watchlist Scores
CREATE OR REPLACE VIEW v_my_watchlist_scores AS
SELECT
    w.Watchlist_ID, w.Watchlist_Name,
    wi.Asset_ID, ar.Ticker, ar.Asset_Name, ar.Kingmaker_Tier,
    ar.Live_Spot_Price, ar.Price_Currency,
    s.KA_Score, s.Computed_At AS Score_As_Of,
    CASE WHEN s.KA_Score >= 80 THEN 'Tier-1 Conviction'
         WHEN s.KA_Score >= 60 THEN 'High Watch'
         WHEN s.KA_Score >= 40 THEN 'Speculative'
         ELSE 'Monitoring' END AS Conviction_Label,
    s.Cassandra_Discount,
    COALESCE(risk.Open_Risk, 0) AS Open_Cassandra_Signals,
    COALESCE(risk.Max_Risk, 0)  AS Max_Risk_Score,
    wi.Notes AS Watchlist_Notes, wi.Added_At
FROM Watchlist_Items wi
JOIN Watchlists w        ON w.Watchlist_ID = wi.Watchlist_ID
JOIN Asset_Registry ar   ON ar.Asset_ID    = wi.Asset_ID
LEFT JOIN LATERAL (
    SELECT KA_Score, Computed_At, Cassandra_Discount FROM Asset_Alpha_Scores
    WHERE Asset_ID = wi.Asset_ID ORDER BY Computed_At DESC LIMIT 1
) s ON TRUE
LEFT JOIN LATERAL (
    SELECT COUNT(*) AS Open_Risk, MAX(Systemic_Risk_Score) AS Max_Risk
    FROM Cassandra_Signals WHERE Target_Asset_ID = wi.Asset_ID AND Is_Resolved = FALSE
) risk ON TRUE
WHERE w.Is_Active = TRUE AND ar.Is_Active = TRUE
ORDER BY w.Watchlist_Name, s.KA_Score DESC NULLS LAST;

COMMENT ON VIEW v_my_watchlist_scores IS 'Personalised watchlist view scoped by RLS to the calling analyst. Returns latest KA_Score and Cassandra risk overlay.';

-- V7: My Portfolio Summary
CREATE OR REPLACE VIEW v_my_portfolio_summary AS
SELECT
    p.Portfolio_ID, p.Portfolio_Name, p.Base_Currency,
    pp.Position_ID, pp.Asset_ID, ar.Ticker, ar.Asset_Name, ar.Kingmaker_Tier,
    ar.Live_Spot_Price, pp.Target_Weight, pp.Current_Weight,
    pp.Entry_Price, pp.Entry_Date, pp.Position_Size_USD,
    pp.Stop_Loss_Pct, pp.Take_Profit_Pct, pp.Conviction_Override,
    s.KA_Score, s.Computed_At AS Score_As_Of, s.Rank_Delta,
    CASE WHEN pp.Entry_Price IS NOT NULL AND ar.Live_Spot_Price IS NOT NULL
        THEN ROUND(((ar.Live_Spot_Price - pp.Entry_Price) / pp.Entry_Price) * 100, 2)
    END AS Unrealised_PnL_Pct,
    COALESCE(risk.Open_Risk, 0) AS Open_Cassandra_Signals,
    COALESCE(risk.Max_Risk, 0)  AS Max_Risk_Score,
    ec.Cluster_Label AS Asset_Cluster, pp.Notes
FROM Portfolios p
JOIN Portfolio_Positions pp ON pp.Portfolio_ID = p.Portfolio_ID AND pp.Is_Active = TRUE
JOIN Asset_Registry ar      ON ar.Asset_ID     = pp.Asset_ID
JOIN Exposure_Clusters ec   ON ec.Cluster_ID   = ar.Cluster_ID
LEFT JOIN LATERAL (
    SELECT KA_Score, Computed_At, Rank_Delta FROM Asset_Alpha_Scores
    WHERE Asset_ID = pp.Asset_ID ORDER BY Computed_At DESC LIMIT 1
) s ON TRUE
LEFT JOIN LATERAL (
    SELECT COUNT(*) AS Open_Risk, MAX(Systemic_Risk_Score) AS Max_Risk
    FROM Cassandra_Signals WHERE Target_Asset_ID = pp.Asset_ID AND Is_Resolved = FALSE
) risk ON TRUE
WHERE p.Is_Active = TRUE AND ar.Is_Active = TRUE
ORDER BY p.Portfolio_Name, pp.Target_Weight DESC;

COMMENT ON VIEW v_my_portfolio_summary IS 'Personalised portfolio view scoped by RLS. Enriches positions with live KA_Score, unrealised PnL%, and Cassandra risk overlay.';

-- =============================================================================
-- END OF STEP 4 — MIGRATION
-- =============================================================================
