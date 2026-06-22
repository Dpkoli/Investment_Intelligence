"""
Regex patterns, scoring tables, and NLP rule sets for the ETL parsers.

All patterns are compiled once at import time for performance.
Organised by pipeline stage: Kingmaker → Cassandra → Horizon.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Pattern


# ─────────────────────────────────────────────────────────────────────────────
# KINGMAKER PATTERNS
# ─────────────────────────────────────────────────────────────────────────────

# Connection type classifiers — ordered by specificity (most specific first)
CONNECTION_TYPE_RULES: list[tuple[str, list[str]]] = [
    ("Custom_Silicon", [
        r"custom\s+(?:silicon|asic|chip|accelerator|npu|dpu)",
        r"custom(?:ized|ised)?\s+(?:networking|connectivity)\s+chip",
        r"proprietary\s+(?:silicon|asic|chip)",
        r"bespoke\s+(?:silicon|asic|chip)",
        r"co-designed\s+(?:silicon|asic|chip)",
        r"custom\s+ai\s+(?:chip|accelerator|processor)",
        r"custom\s+ethernet\s+(?:chip|asic)",
    ]),
    ("Equity_Stake", [
        r"(?:strategic|minority|equity)\s+(?:investment|stake|interest)",
        r"(?:acquired|purchased)\s+(?:a\s+)?(?:\d+[\.\d]*\s*%|stake|interest)\s+in",
        r"equity\s+(?:financing|round|participation)",
    ]),
    ("JV_Partner", [
        r"joint\s+venture",
        r"strategic\s+(?:alliance|partnership|collaboration)",
        r"technology\s+(?:partnership|alliance|collaboration)",
        r"co-development\s+agreement",
        r"co-invest",
        r"joint\s+development\s+agreement",
    ]),
    ("Supplier", [
        r"(?:sole|primary|exclusive|strategic|preferred|key)\s+supplier",
        r"supply\s+(?:agreement|contract|arrangement|deal)",
        r"manufacturing\s+(?:agreement|partnership|contract)",
        r"vendor\s+(?:agreement|contract|relationship)",
        r"procurement\s+(?:agreement|contract)",
        r"component\s+(?:supplier|provider)",
        r"original\s+design\s+manufacturer",
        r"\bodm\b",
    ]),
]

# Compile all connection type patterns
COMPILED_CONNECTION_RULES: list[tuple[str, list[Pattern[str]]]] = [
    (ctype, [re.compile(p, re.IGNORECASE) for p in patterns])
    for ctype, patterns in CONNECTION_TYPE_RULES
]

# Wallet-share percentage extractors — captures numeric % near relationship text
WALLET_SHARE_PATTERNS: list[Pattern[str]] = [re.compile(p, re.IGNORECASE) for p in [
    r"(?:approximately\s+)?(\d{1,3}(?:\.\d+)?)\s*%\s+of\s+(?:our\s+)?(?:annual\s+)?revenue",
    r"(?:approximately\s+)?(\d{1,3}(?:\.\d+)?)\s*%\s+of\s+(?:total\s+)?(?:net\s+)?(?:sales|revenue)",
    r"represents?\s+(?:approximately\s+)?(\d{1,3}(?:\.\d+)?)\s*%",
    r"accounted?\s+for\s+(?:approximately\s+)?(\d{1,3}(?:\.\d+)?)\s*%",
    r"(\d{1,3}(?:\.\d+)?)\s*%\s+of\s+(?:our\s+)?(?:business|revenue|sales)",
    r"generated?\s+(?:approximately\s+)?(\d{1,3}(?:\.\d+)?)\s*%",
]]

# Qualitative wallet share mappings when no percentage is given
QUALITATIVE_WALLET_MAP: dict[str, float] = {
    "sole": 0.90,
    "exclusive": 0.85,
    "primary": 0.60,
    "main": 0.55,
    "principal": 0.55,
    "largest": 0.50,
    "significant": 0.35,
    "major": 0.40,
    "key": 0.30,
    "strategic": 0.25,
    "important": 0.20,
}

# Executive endorsement detection patterns
ENDORSEMENT_PATTERNS: list[Pattern[str]] = [re.compile(p, re.IGNORECASE) for p in [
    # Named executive + affirmative verb + company/product
    r"(?:ceo|cto|president|chairman|founder|chief\s+executive)\s+(?:\w+\s+){0,3}"
    r"(?:said|stated|announced|declared|highlighted|emphasised?|called out|named|identified)",
    r"(?:said|stated|declared|announced)\s+in\s+(?:an?\s+)?(?:interview|keynote|presentation|conference|earnings call)",
    r"(?:on stage|at\s+(?:computex|nvidia\s+gtc|ces|hot chips|sc\d{2}|flash\s+memory summit))",
    r"(?:our\s+partner|our\s+strategic\s+partner|endorsed\s+by|recommended\s+by)",
    r"(?:named|identified|called out|spotlighted|highlighted)\s+(?:by\s+)?(?:our\s+)?(?:ceo|cto|founder|chairman)",
]]

# Executive name extractor (captures speaker attribution)
SPEAKER_PATTERN: Pattern[str] = re.compile(
    r"""
    (?:
        (?P<first>[A-Z][a-z]+)\s+(?P<last>[A-Z][a-z]+)   # First Last
        \s*[,\-\(]?\s*
        (?:
            (?:chief\s+executive|ceo|cto|president|chairman|co-founder|founder|
               executive\s+vice\s+president|evp|svp|senior\s+vice\s+president)
            (?:\s+(?:and|&)\s+\w+)*
        )?
    )
    """,
    re.VERBOSE,
)

# Relationship trigger patterns — finds proximity between titan and vendor
# The captured text window is 500 chars and we search for entity pairs
RELATIONSHIP_TRIGGER_PATTERNS: list[Pattern[str]] = [re.compile(p, re.IGNORECASE) for p in [
    r"(?:partner|supplier|vendor|manufacturer|provider)\s+(?:for|to|of|with)\s+\w+",
    r"(?:custom|proprietary)\s+(?:silicon|chip|asic|accelerator)\s+(?:for|to|from)",
    r"supply(?:ing)?\s+(?:to|for)",
    r"manufactur(?:e|ing|ed)\s+(?:for|by)",
    r"design(?:ed|ing)?\s+(?:for|in\s+collaboration\s+with)",
    r"develop(?:ed|ing|ment)?\s+(?:jointly|together|in\s+partnership)\s+with",
    r"integrat(?:e|ed|ing)\s+(?:into|with)",
    r"licens(?:e|ed|ing)\s+(?:from|to)",
    r"exclusively\s+(?:supply|provide|manufacture)",
]]


# ─────────────────────────────────────────────────────────────────────────────
# CASSANDRA RISK PATTERNS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RiskTrigger:
    pattern: Pattern[str]
    base_weight: float     # contribution to raw severity score
    risk_vector: str       # category label for Risk_Vector field


def _rt(regex: str, weight: float, vector: str) -> RiskTrigger:
    return RiskTrigger(re.compile(regex, re.IGNORECASE), weight, vector)


# Energy grid / AI data center power constraints
ENERGY_RISK_TRIGGERS: list[RiskTrigger] = [
    _rt(r"grid\s+(?:constraint|failure|overload|capacity|instability)", 2.5, "Energy_Grid_Constraint"),
    _rt(r"power\s+(?:shortage|outage|crisis|deficit|rationing)", 2.8, "Energy_Grid_Constraint"),
    _rt(r"electricity\s+(?:shortage|deficit|constraint|crisis)", 2.5, "Energy_Grid_Constraint"),
    _rt(r"data\s+center\s+power\s+(?:demand|constraint|limit|crisis)", 2.0, "DC_Power_Demand"),
    _rt(r"(?:electrical|power)\s+transformer\s+(?:shortage|lead.?time|backlog|constraint)", 3.2, "Transformer_Lead_Time"),
    _rt(r"transformer\s+(?:lead.?time|delivery|backlog|delay|shortage)", 3.0, "Transformer_Lead_Time"),
    _rt(r"(?:\d+\s+to\s+\d+|\d+).?(?:month|year)\s+(?:lead.?time|wait|backlog)\s+(?:for\s+)?transformer", 3.5, "Transformer_Lead_Time"),
    _rt(r"utility.?scale\s+(?:power|energy)\s+(?:shortage|gap|constraint)", 2.8, "Energy_Grid_Constraint"),
    _rt(r"(?:nuclear|smr|small\s+modular\s+reactor)\s+(?:power|energy|plant)", 1.5, "Energy_Infrastructure"),
    _rt(r"ai\s+energy\s+(?:consumption|demand|footprint|cost)", 1.8, "DC_Power_Demand"),
    _rt(r"hyperscal(?:er|e)\s+(?:power|energy)\s+(?:demand|crisis|constraint)", 2.2, "DC_Power_Demand"),
    _rt(r"(?:cooling|thermal)\s+(?:constraint|crisis|shortage|limit)", 1.5, "DC_Power_Demand"),
]

# Crypto custody / counterparty centralisation risks
CRYPTO_RISK_TRIGGERS: list[RiskTrigger] = [
    _rt(r"crypto\s+(?:custody|custodian)\s+(?:risk|failure|collapse|crisis)", 3.0, "Crypto_Custody_Risk"),
    _rt(r"custodian\s+(?:failure|collapse|default|insolvency)", 3.5, "Crypto_Custody_Risk"),
    _rt(r"counterparty\s+(?:risk|exposure|concentration|default|collapse)", 2.8, "Crypto_Counterparty_Risk"),
    _rt(r"exchange\s+(?:collapse|failure|insolvency|hack|exploit)", 3.5, "Crypto_Exchange_Risk"),
    _rt(r"crypto\s+contagion", 3.2, "Crypto_Counterparty_Risk"),
    _rt(r"centrali(?:s|z)ation\s+(?:risk|concern|problem)\s+(?:in\s+)?(?:crypto|bitcoin|digital)", 2.5, "Crypto_Centralisation"),
    _rt(r"single\s+point\s+of\s+failure\s+(?:in\s+)?(?:crypto|custody|exchange)", 3.0, "Crypto_Centralisation"),
    _rt(r"(?:staking|validator)\s+(?:slashing|risk|concentration)", 2.0, "Crypto_Staking_Risk"),
    _rt(r"re-?hypothecation\s+(?:risk|concern)", 2.5, "Crypto_Custody_Risk"),
    _rt(r"proof.of.reserves\s+(?:fraud|manipulation|missing)", 3.8, "Crypto_Custody_Risk"),
    _rt(r"liquidity\s+(?:crisis|crunch|dry.?up)\s+(?:in\s+)?(?:crypto|defi|stablecoin)", 3.0, "Crypto_Liquidity_Risk"),
    _rt(r"stablecoin\s+(?:depeg|collapse|crisis|failure)", 3.5, "Crypto_Stablecoin_Risk"),
]

# Macro systemic risks
MACRO_RISK_TRIGGERS: list[RiskTrigger] = [
    _rt(r"(?:systemic|contagion|cascade)\s+(?:risk|failure|collapse)", 3.0, "Systemic_Risk"),
    _rt(r"leverage\s+(?:unwind|collapse|liquidation|crisis)", 3.2, "Leverage_Unwind"),
    _rt(r"margin\s+call(?:s)?", 2.5, "Leverage_Unwind"),
    _rt(r"(?:regulatory|government)\s+(?:crackdown|ban|restriction|enforcement)", 2.8, "Regulatory_Overhang"),
    _rt(r"geopolit(?:ical|ic)\s+(?:risk|tension|conflict|escalation)", 2.0, "Geopolitical_Friction"),
    _rt(r"supply\s+chain\s+(?:disruption|crisis|breakdown|collapse)", 2.5, "Supply_Chain_Disruption"),
    _rt(r"(?:export\s+)?(?:restriction|control|ban)\s+(?:on\s+)?(?:chip|semiconductor|ai)", 2.8, "Regulatory_Overhang"),
    _rt(r"concentration\s+risk", 2.0, "Counterparty_Concentration"),
    _rt(r"(?:credit|counterparty)\s+default\s+(?:swap|risk|event)", 3.0, "Credit_Risk"),
]

# Severity amplifiers — multiply the weighted score when present
SEVERITY_AMPLIFIERS: list[tuple[Pattern[str], float]] = [
    (re.compile(r"\bimminent\b", re.IGNORECASE), 1.5),
    (re.compile(r"\bcritical\b", re.IGNORECASE), 1.4),
    (re.compile(r"\bcatastrophic\b", re.IGNORECASE), 1.6),
    (re.compile(r"\bsevere\b", re.IGNORECASE), 1.3),
    (re.compile(r"\bcrisis\b", re.IGNORECASE), 1.3),
    (re.compile(r"\bextreme\b", re.IGNORECASE), 1.4),
    (re.compile(r"\bcollapse\b", re.IGNORECASE), 1.5),
    (re.compile(r"\baccelerating\b", re.IGNORECASE), 1.2),
    (re.compile(r"\bworsening\b", re.IGNORECASE), 1.2),
    (re.compile(r"\bunprecedented\b", re.IGNORECASE), 1.3),
]

ALL_RISK_TRIGGERS: list[RiskTrigger] = (
    ENERGY_RISK_TRIGGERS + CRYPTO_RISK_TRIGGERS + MACRO_RISK_TRIGGERS
)


# ─────────────────────────────────────────────────────────────────────────────
# HORIZON PATTERNS
# ─────────────────────────────────────────────────────────────────────────────

# Asset class classifiers for prospectus filings
ASSET_CLASS_PATTERNS: list[tuple[str, Pattern[str]]] = [
    ("Spot Bitcoin ETF",      re.compile(r"spot\s+bitcoin", re.IGNORECASE)),
    ("Spot Ethereum ETF",     re.compile(r"spot\s+ether(?:eum)?", re.IGNORECASE)),
    ("Spot Solana ETF",       re.compile(r"spot\s+sol(?:ana)?", re.IGNORECASE)),
    ("Spot XRP ETF",          re.compile(r"spot\s+xrp|ripple\s+etf", re.IGNORECASE)),
    ("AI Infrastructure ETF", re.compile(r"artificial\s+intelligence|ai\s+infra", re.IGNORECASE)),
    ("Data Center REIT ETF",  re.compile(r"data\s+cent(?:er|re)", re.IGNORECASE)),
    ("Nuclear Energy ETF",    re.compile(r"nuclear\s+(?:energy|power)", re.IGNORECASE)),
    ("Physical Gold ETP",     re.compile(r"physical\s+gold|gold\s+bullion", re.IGNORECASE)),
    ("Physical Silver ETP",   re.compile(r"physical\s+silver|silver\s+bullion", re.IGNORECASE)),
    ("Blockchain ETF",        re.compile(r"blockchain\s+(?:etf|technology)", re.IGNORECASE)),
    ("Semiconductor ETF",     re.compile(r"semiconductor\s+(?:etf|fund)", re.IGNORECASE)),
    ("Quantum Computing ETF", re.compile(r"quantum\s+computing", re.IGNORECASE)),
    ("Space Economy ETF",     re.compile(r"space\s+(?:economy|exploration|tech)", re.IGNORECASE)),
    ("Digital Assets ETF",    re.compile(r"digital\s+asset", re.IGNORECASE)),
    ("Emerging Markets ETF",  re.compile(r"emerging\s+market", re.IGNORECASE)),
]

# Listing timeline extractors
TIMELINE_PATTERNS: list[Pattern[str]] = [re.compile(p, re.IGNORECASE) for p in [
    r"expect(?:ed|s)?\s+(?:to\s+list|listing|to\s+launch|launch)\s+(?:in\s+)?([A-Z]?\d?[Qq][1-4]\s+\d{4})",
    r"(?:anticipated|planned|target(?:ed)?)\s+(?:listing|launch|trading)\s+(?:date\s+)?(?:in\s+)?(\w+\s+\d{4}|\d{4})",
    r"(?:by|before|during)\s+((?:Q[1-4]\s+)?\d{4})",
    r"(?:effective\s+date|commencement)\s*[:\-]\s*(\w+\s+\d{1,2},?\s+\d{4})",
    r"(?:first\s+half|second\s+half|H[12])\s+(\d{4})",
    r"(\d{4})\s+(?:listing|launch|initial\s+offering)",
]]

# Instrument type classifier from filing form
FILING_TO_INSTRUMENT: dict[str, str] = {
    "S-1":     "Pipeline_Filing",
    "S-1/A":   "Pipeline_Filing",
    "N-1A":    "ETF",
    "N-1A/A":  "ETF",
    "N-2":     "Corporate_Proxy",
    "N-2/A":   "Corporate_Proxy",
    "DEF-14A": "Pipeline_Filing",
    "424B3":   "ETF",
    "424B4":   "ETF",
    "13-F":    "Pipeline_Filing",
    "FCA-ETP": "ETP",
}

# Cleaner for raw HTML / filing text
HTML_STRIP: Pattern[str] = re.compile(r"<[^>]+>")
WHITESPACE_NORM: Pattern[str] = re.compile(r"\s{2,}")
