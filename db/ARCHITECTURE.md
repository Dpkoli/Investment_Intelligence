# Contrarian Radar — Relational Database Architecture
## Step 1 of 4 | The Kingmaker Protocol Foundation

---

## Entity-Relationship Map

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         EXPOSURE_CLUSTERS                                    │
│  PK: Cluster_ID                                                              │
│  ── Cluster_Label  (ENUM: SP500 | FTSE | EM | GOLD | SILVER | BTC | ETH |  │
│                           SOL | XRP | HORIZON | KINGMAKER)                   │
│  ── Target_Weight, Vol_Regime_Factor                                         │
│  ── Theme_Thesis, Is_Active                                                  │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │ 1
                               │
                               │ N  (every asset belongs to exactly one cluster)
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           ASSET_REGISTRY                                     │
│  PK: Asset_ID                                                                │
│  FK: Cluster_ID ──────────────────────────────► Exposure_Clusters           │
│  ── Ticker, ISIN, Asset_Name                                                 │
│  ── Instrument_Type  (Spot | ETF | ETP | Corporate_Proxy | Pipeline_Filing) │
│  ── Live_Spot_Price, Price_Currency, Price_As_Of                             │
│  ── AUM, Expense_Ratio, Net_30D_Flows          ← Fund-level metrics         │
│  ── FCA_Authorized_Flag, Regulatory_Filing_Date ← Regulatory layer          │
│  ── Kingmaker_Tier (1–3, NULL if not KINGMAKER cluster)                     │
└──────────┬────────────────────────────────┬─────────────────────────────────┘
           │                                │
           │                                │
           │ AS Parent_Anchor_ID (Titan)    │ AS Counterparty_Asset_ID (Target)
           │ N                              │ N
           └───────────────┬────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CORPORATE_ECOSYSTEM_CONNECTIONS                            │
│  PK: Connection_ID                                                           │
│  FK: Parent_Anchor_ID    ──────────────────────► Asset_Registry (Titan)     │
│  FK: Counterparty_Asset_ID ────────────────────► Asset_Registry (Target)    │
│  ── Connection_Type  (Supplier | JV_Partner | Custom_Silicon | Equity_Stake)│
│  ── Share_Of_Wallet_Est   ← % of counterparty revenue from this titan       │
│  ── Endorsement_Flag (BOOL) + Endorsement_Source + Endorsement_Date         │
│  ── Confidence_Score (1–10), Revenue_Impact_USD_Est                         │
│  ── Primary_Source_URL, SEC_Filing_Reference                                 │
│  CONSTRAINT: no self-loops (Parent ≠ Counterparty)                          │
│  CONSTRAINT: unique (Parent, Counterparty, Connection_Type)                  │
└──────────────────────────────────────────────────────────────────────────────┘
           ▲
           │ optional back-reference (Related_Connection_ID)
           │
┌──────────────────────────────────────────────────────────────────────────────┐
│                         CASSANDRA_SIGNALS                                    │
│  PK: Signal_ID                                                               │
│  FK: Target_Asset_ID   ────────────────────────► Asset_Registry (nullable)  │
│  FK: Target_Cluster_ID ────────────────────────► Exposure_Clusters (nullable│
│  FK: Related_Connection_ID ────────────────────► Corporate_Ecosystem_Conn.  │
│  ── Signal_Source  (Whistleblower | Influencer | Regulatory_Leak |          │
│                     Short_Seller_Report | Anonymous_Filing)                  │
│  ── Source_Handle, Source_Credibility (1–10)                                │
│  ── Signal_Title, Raw_Signal_Text, Signal_Date                               │
│  ── Systemic_Risk_Score (1–10)  ← CORE ALERT FIELD                         │
│      1–3 = Background noise                                                  │
│      4–6 = Elevated watch                                                    │
│      7–9 = Active threat                                                     │
│      10  = Imminent systemic event                                           │
│  ── Risk_Vector (free-tag: Counterparty_Concentration, Leverage_Unwind …)   │
│  ── Analyst_Reviewed, Analyst_Notes, Is_Resolved                            │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Cardinality Summary

| Relationship | Type | Notes |
|---|---|---|
| Exposure_Clusters → Asset_Registry | 1 : N | One cluster, many assets |
| Asset_Registry → Corporate_Ecosystem_Connections (as Parent) | 1 : N | One titan, many dependencies |
| Asset_Registry → Corporate_Ecosystem_Connections (as Counterparty) | 1 : N | One target, many titan relationships |
| Corporate_Ecosystem_Connections → Cassandra_Signals | 1 : N (optional) | A signal can reference a specific connection |
| Asset_Registry → Cassandra_Signals | 1 : N (optional) | A signal can target a specific asset |
| Exposure_Clusters → Cassandra_Signals | 1 : N (optional) | A signal can target an entire cluster bucket |

---

## Kingmaker Protocol Data Flow

```
Macro Research / Filings / Keynote Transcripts
            │
            ▼
  CORPORATE_ECOSYSTEM_CONNECTIONS
  (Parent_Anchor=Nvidia, Counterparty=Marvell,
   Connection_Type=Custom_Silicon,
   Share_Of_Wallet_Est=0.42,
   Endorsement_Flag=TRUE,
   Endorsement_Source="Jensen Huang, GTC 2024")
            │
            ▼
  ASSET_REGISTRY: Marvell tagged
  Cluster_ID → KINGMAKER
  Kingmaker_Tier = 1  (direct titan structural dependency)
            │
            ▼
  Allocation Engine reads:
  • Share_Of_Wallet_Est  → upside leverage multiple
  • Endorsement_Flag     → conviction multiplier
  • Cassandra_Signals    → risk discount if score ≥ 7
```

---

## Index Strategy

| Index | Purpose |
|---|---|
| `idx_asset_kingmaker` | Fast filter to all KINGMAKER-tier assets |
| `idx_cec_parent` | Graph traversal: all dependencies of one titan |
| `idx_cec_endorsed` | Instant pull of all formally endorsed counterparties |
| `idx_cassandra_score DESC` | Priority-ranked risk triage queue |
| `idx_cassandra_unrev` | Analyst inbox: unreviewed signals only |

---

## Next Steps (Steps 2–4)

- **Step 2** — Alternative data ingestion pipeline (SEC EDGAR, earnings call NLP, satellite data connectors)
- **Step 3** — Scoring engine: Kingmaker Alpha Score, Cassandra Alert Dispatcher
- **Step 4** — API layer and personalized portfolio interface
