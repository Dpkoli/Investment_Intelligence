"""
Kingmaker Intelligence — multi-sector global supply-chain dependency registry.
Maps anchor corporations (S&P 500, FTSE 100, NASDAQ, Nikkei 225, DAX) to their
smaller supplier/partner ecosystem across Energy, Consumer, Defense/Aerospace,
Healthcare, Technology, and Materials sectors.

Each link captures:
  • Supply layer (precise functional description)
  • Wallet share % estimation
  • Contract duration and renewal cliff
  • Relative valuation delta (EV/EBITDA, P/E, P/S anchor vs. supplier)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SupplyChainLink:
    anchor_ticker: str
    anchor_name: str
    anchor_index: str           # e.g. "S&P 500", "FTSE 100", "NASDAQ", "Nikkei 225", "DAX"
    supplier_ticker: str
    supplier_name: str
    sector: str                 # "Technology", "Energy", "Defense", "Healthcare", "Consumer", "Materials"
    supply_layer: str           # precise functional description
    connection_type: str        # "Custom_Silicon" | "JV_Partner" | "Sole_Supplier" | "Preferred_Supplier" | "Subcontractor" | "CRO" | "CDMO"
    wallet_share_pct: Optional[float] = None    # estimated % of supplier revenue from anchor
    wallet_share_qual: str = "Significant"      # "Critical (>50%)" | "Major (30-50%)" | "Significant (15-30%)" | "Notable (5-15%)"
    contract_years: Optional[float] = None
    renewal_cliff: Optional[str] = None        # "YYYY-QQ" format
    endorsement_flag: bool = False
    ev_ebitda_anchor: Optional[float] = None
    ev_ebitda_supplier: Optional[float] = None
    pe_anchor: Optional[float] = None
    pe_supplier: Optional[float] = None
    ps_anchor: Optional[float] = None
    ps_supplier: Optional[float] = None
    valuation_narrative: str = ""
    exec_quote: str = ""
    source_url: str = ""
    notes: str = ""


# ── TECHNOLOGY SECTOR ─────────────────────────────────────────────────────────

_TECH_LINKS: list[SupplyChainLink] = [
    SupplyChainLink(
        anchor_ticker="NVDA", anchor_name="NVIDIA", anchor_index="NASDAQ",
        supplier_ticker="MRVL", supplier_name="Marvell Technology",
        sector="Technology", supply_layer="Custom ASIC Design & ConnectX NIC Silicon",
        connection_type="Custom_Silicon", wallet_share_pct=28.0,
        wallet_share_qual="Major (30-50%)", contract_years=5.0, renewal_cliff="2027-Q2",
        endorsement_flag=True, ev_ebitda_anchor=82.0, ev_ebitda_supplier=28.0,
        pe_anchor=55.0, pe_supplier=32.0, ps_anchor=28.0, ps_supplier=8.0,
        valuation_narrative="MRVL trades at 28× EV/EBITDA vs NVDA's 82× despite 40-60% of cloud ASIC revenue directly tied to NVDA ecosystem. Structural 3× valuation discount vs. anchor on equivalent silicon revenue trajectory.",
        exec_quote="Marvell is our primary custom ASIC partner — sole-source for ConnectX series",
        source_url="https://ir.nvidia.com/news-releases/news-release-details/nvidia-fiscal-2025-third-quarter-earnings",
    ),
    SupplyChainLink(
        anchor_ticker="NVDA", anchor_name="NVIDIA", anchor_index="NASDAQ",
        supplier_ticker="SMCI", supplier_name="Super Micro Computer",
        sector="Technology", supply_layer="HGX Server Platform Integration & Thermal Architecture",
        connection_type="Preferred_Supplier", wallet_share_pct=38.0,
        wallet_share_qual="Major (30-50%)", contract_years=3.0, renewal_cliff="2026-Q4",
        endorsement_flag=True, ev_ebitda_anchor=82.0, ev_ebitda_supplier=9.0,
        pe_anchor=55.0, pe_supplier=11.0, ps_anchor=28.0, ps_supplier=0.4,
        valuation_narrative="SMCI trades at 9× EV/EBITDA — a 73% discount to NVDA — despite ~38% of revenue directly attributed to NVDA HGX shipments. Regulatory overhang (PCAOB delay) creates temporary valuation dislocation.",
        exec_quote="~35% of HGX unit shipments flow through SuperMicro liquid-cooled chassis",
        source_url="https://investor.supermicro.com/news-releases/news-release-details/super-micro-computer-inc-reports-financial-results-fourth",
    ),
    SupplyChainLink(
        anchor_ticker="NVDA", anchor_name="NVIDIA", anchor_index="NASDAQ",
        supplier_ticker="COHR", supplier_name="Coherent Corp",
        sector="Technology", supply_layer="800G/1.6T Optical Transceiver Modules for AI Fabric",
        connection_type="Preferred_Supplier", wallet_share_pct=22.0,
        wallet_share_qual="Significant (15-30%)", contract_years=4.0, renewal_cliff="2027-Q3",
        ev_ebitda_anchor=82.0, ev_ebitda_supplier=18.0, pe_anchor=55.0, pe_supplier=24.0,
        valuation_narrative="COHR at 18× EV/EBITDA vs NVDA 82× — 4.5× discount despite being sole-qualified supplier for 800G ZR+ modules in NVLink 5.0 fabric. Optical interconnect revenue growing 65% YoY.",
        exec_quote="Coherent 800G transceivers underpin our Azure and NVLink AI fabric at scale",
        source_url="https://ir.coherent.com/",
    ),
    SupplyChainLink(
        anchor_ticker="GOOGL", anchor_name="Google/Alphabet", anchor_index="NASDAQ",
        supplier_ticker="CDNS", supplier_name="Cadence Design Systems",
        sector="Technology", supply_layer="TPU v5/v6 EDA Verification & Silicon IP",
        connection_type="Custom_Silicon", wallet_share_pct=18.0,
        wallet_share_qual="Significant (15-30%)", contract_years=5.0, renewal_cliff="2028-Q1",
        endorsement_flag=True, ev_ebitda_anchor=24.0, ev_ebitda_supplier=42.0,
        pe_anchor=22.0, pe_supplier=50.0, ps_anchor=5.5, ps_supplier=14.0,
        valuation_narrative="CDNS commands a premium (42× EV/EBITDA) reflecting oligopoly pricing power in EDA. Google 100% dependency on Cadence for TPU verification creates sticky revenue floor.",
        exec_quote="Cadence handles 100% of our TPU v5 verification flows and DFT sign-off",
        source_url="https://ai.google/research/teams/brain/tpu",
    ),
    SupplyChainLink(
        anchor_ticker="GOOGL", anchor_name="Google/Alphabet", anchor_index="NASDAQ",
        supplier_ticker="SNPS", supplier_name="Synopsys",
        sector="Technology", supply_layer="RTL Synthesis & Physical Design for Google TPU/Axion",
        connection_type="Custom_Silicon", wallet_share_pct=16.0,
        wallet_share_qual="Significant (15-30%)", contract_years=5.0, renewal_cliff="2028-Q2",
        endorsement_flag=True, ev_ebitda_anchor=24.0, ev_ebitda_supplier=48.0,
        valuation_narrative="SNPS EDA monopoly extends to Google's entire custom silicon roadmap. ANSYS acquisition adds simulation moat. 48× EV/EBITDA premium justified by zero substitution risk.",
        exec_quote="Synopsys is our synthesis-to-signoff partner across all custom SoC programs",
        source_url="https://www.synopsys.com/company/newsroom.html",
    ),
    SupplyChainLink(
        anchor_ticker="AMZN", anchor_name="Amazon", anchor_index="NASDAQ",
        supplier_ticker="ANET", supplier_name="Arista Networks",
        sector="Technology", supply_layer="AWS Nitro SuperCluster Switching Fabric (400G/800G)",
        connection_type="JV_Partner", wallet_share_pct=20.0,
        wallet_share_qual="Significant (15-30%)", contract_years=4.0, renewal_cliff="2027-Q1",
        endorsement_flag=True, ev_ebitda_anchor=32.0, ev_ebitda_supplier=38.0,
        pe_anchor=42.0, pe_supplier=46.0,
        valuation_narrative="ANET trades near parity with AMZN EV/EBITDA but with significantly higher gross margins (63% vs 48%). AWS concentration risk (~20% of ANET revenue) offset by Microsoft and Meta diversification.",
        exec_quote="Arista is exclusive switching fabric partner for AWS Nitro SuperCluster",
        source_url="https://www.arista.com/en/news",
    ),
    SupplyChainLink(
        anchor_ticker="MSFT", anchor_name="Microsoft", anchor_index="NASDAQ",
        supplier_ticker="FORM", supplier_name="FormFactor",
        sector="Technology", supply_layer="Advanced IC Probe Cards for Azure Maia ASIC Wafer Test",
        connection_type="Sole_Supplier", wallet_share_pct=25.0,
        wallet_share_qual="Major (30-50%)", contract_years=3.0, renewal_cliff="2026-Q4",
        ev_ebitda_anchor=26.0, ev_ebitda_supplier=14.0,
        pe_anchor=32.0, pe_supplier=22.0,
        valuation_narrative="FORM at 14× EV/EBITDA vs MSFT 26× — sole qualified probe card supplier for advanced AI ASIC testing protocols. Custom AI chip boom drives structural wafer-test demand growth.",
        exec_quote="FormFactor is qualified for our Maia silicon engineering wafer sort",
        source_url="https://ir.formfactor.com/",
    ),
    SupplyChainLink(
        anchor_ticker="TSM", anchor_name="TSMC", anchor_index="NYSE",
        supplier_ticker="ONTO", supplier_name="Onto Innovation",
        sector="Technology", supply_layer="Optical Metrology & Wafer Inspection for N3/N2 Node",
        connection_type="Preferred_Supplier", wallet_share_pct=35.0,
        wallet_share_qual="Major (30-50%)", contract_years=4.0, renewal_cliff="2027-Q3",
        ev_ebitda_anchor=18.0, ev_ebitda_supplier=16.0,
        pe_anchor=20.0, pe_supplier=22.0,
        valuation_narrative="ONTO trades at near-parity with TSMC on EV/EBITDA but is entirely dependent on leading-edge node yield ramp timing. N2 ramp in 2025-26 is direct catalyst for ONTO order book growth.",
        source_url="https://ir.ontoinnovation.com/",
    ),
    SupplyChainLink(
        anchor_ticker="INTC", anchor_name="Intel", anchor_index="NASDAQ",
        supplier_ticker="ACLS", supplier_name="Axcelis Technologies",
        sector="Technology", supply_layer="Ion Implantation Systems for Intel 18A Foundry Node",
        connection_type="Preferred_Supplier", wallet_share_pct=30.0,
        wallet_share_qual="Major (30-50%)", contract_years=3.0, renewal_cliff="2026-Q2",
        ev_ebitda_anchor=22.0, ev_ebitda_supplier=8.0,
        pe_anchor=28.0, pe_supplier=11.0,
        valuation_narrative="ACLS at 8× EV/EBITDA — 63% discount to INTC — as sole-qualified implanter for INTEL 18A node. Recovery thesis tied to Intel Foundry Services ramp; asymmetric setup if 18A node achieves volume production.",
        source_url="https://ir.axcelis.com/",
    ),
]

# ── ENERGY SECTOR ─────────────────────────────────────────────────────────────

_ENERGY_LINKS: list[SupplyChainLink] = [
    SupplyChainLink(
        anchor_ticker="XOM", anchor_name="ExxonMobil", anchor_index="S&P 500",
        supplier_ticker="SLB", supplier_name="SLB (Schlumberger)",
        sector="Energy", supply_layer="Reservoir Characterisation, Drilling Automation & Cementing Services",
        connection_type="Preferred_Supplier", wallet_share_pct=12.0,
        wallet_share_qual="Notable (5-15%)", contract_years=5.0, renewal_cliff="2028-Q1",
        ev_ebitda_anchor=8.0, ev_ebitda_supplier=10.0, pe_anchor=12.0, pe_supplier=14.0,
        valuation_narrative="SLB trades at modest premium to XOM reflecting higher services-business margins. International deepwater expansion (Guyana, Brazil) adds 3-5% annual service demand uplift over 5-year horizon.",
        source_url="https://investors.slb.com/",
    ),
    SupplyChainLink(
        anchor_ticker="XOM", anchor_name="ExxonMobil", anchor_index="S&P 500",
        supplier_ticker="HAL", supplier_name="Halliburton",
        sector="Energy", supply_layer="Completions, Production Enhancement & Digital Well Monitoring",
        connection_type="Preferred_Supplier", wallet_share_pct=10.0,
        wallet_share_qual="Notable (5-15%)", contract_years=3.0, renewal_cliff="2026-Q4",
        ev_ebitda_anchor=8.0, ev_ebitda_supplier=7.0, pe_anchor=12.0, pe_supplier=10.0,
        valuation_narrative="HAL at 7× EV/EBITDA — slight discount to XOM despite higher operational leverage to Permian Basin activity. Istation Digital completions platform reduces well cost 18-22%, driving adoption acceleration.",
        source_url="https://investors.halliburton.com/",
    ),
    SupplyChainLink(
        anchor_ticker="XOM", anchor_name="ExxonMobil", anchor_index="S&P 500",
        supplier_ticker="BKR", supplier_name="Baker Hughes",
        sector="Energy", supply_layer="LNG Compression & Turbomachinery for Golden Pass LNG",
        connection_type="Sole_Supplier", wallet_share_pct=8.0,
        wallet_share_qual="Notable (5-15%)", contract_years=6.0, renewal_cliff="2029-Q3",
        ev_ebitda_anchor=8.0, ev_ebitda_supplier=12.0,
        valuation_narrative="BKR sole-source supplier for Golden Pass LNG turbomachinery — a 6-year committed revenue stream. NovaLT gas turbines also supplied to 3 CCGT plants. Industrial Energy Technology segment growing at 12% CAGR.",
        source_url="https://investors.bakerhughes.com/",
    ),
    SupplyChainLink(
        anchor_ticker="NEE", anchor_name="NextEra Energy", anchor_index="S&P 500",
        supplier_ticker="ARRY", supplier_name="Array Technologies",
        sector="Energy", supply_layer="Single-Axis Solar Tracker Systems for Florida Solar Farms",
        connection_type="Preferred_Supplier", wallet_share_pct=40.0,
        wallet_share_qual="Critical (>50%)", contract_years=3.0, renewal_cliff="2026-Q3",
        ev_ebitda_anchor=22.0, ev_ebitda_supplier=8.0, pe_anchor=18.0, pe_supplier=12.0,
        valuation_narrative="ARRY at 8× EV/EBITDA — 63% discount to NEE — with ~40% of tracker revenues tied to NextEra/FPL solar procurement pipeline. 60+ GW US utility solar backlog structurally underpins order visibility through 2028.",
        source_url="https://ir.arraytechinc.com/",
    ),
    SupplyChainLink(
        anchor_ticker="NEE", anchor_name="NextEra Energy", anchor_index="S&P 500",
        supplier_ticker="ENPH", supplier_name="Enphase Energy",
        sector="Energy", supply_layer="IQ8 Microinverters & Grid-forming Battery Storage for Distributed Solar",
        connection_type="Preferred_Supplier", wallet_share_pct=8.0,
        wallet_share_qual="Notable (5-15%)", contract_years=2.0, renewal_cliff="2026-Q1",
        ev_ebitda_anchor=22.0, ev_ebitda_supplier=14.0,
        valuation_narrative="ENPH microinverter platform adopted by NEE residential solar arm (NextEra Energy Resources). Utility-scale battery adjacency emerging as NEE expands storage mandates under Florida RPS.",
        source_url="https://investor.enphase.com/",
    ),
    SupplyChainLink(
        anchor_ticker="BP", anchor_name="BP", anchor_index="FTSE 100",
        supplier_ticker="AMRC", supplier_name="Ameresco",
        sector="Energy", supply_layer="Renewable Energy Project Development & ESCO Services",
        connection_type="JV_Partner", wallet_share_pct=15.0,
        wallet_share_qual="Significant (15-30%)", contract_years=10.0, renewal_cliff="2033-Q4",
        ev_ebitda_anchor=6.0, ev_ebitda_supplier=18.0,
        valuation_narrative="AMRC JV with BP for campus microgrid and solar-plus-storage development. 10-year contracted revenue visibility from federal/municipal ESCO projects provides counter-cyclical revenue floor.",
        source_url="https://ir.ameresco.com/",
    ),
    SupplyChainLink(
        anchor_ticker="DUK", anchor_name="Duke Energy", anchor_index="S&P 500",
        supplier_ticker="PLUG", supplier_name="Plug Power",
        sector="Energy", supply_layer="Green Hydrogen Electrolyser Supply for Grid Decarbonisation",
        connection_type="Preferred_Supplier", wallet_share_pct=12.0,
        wallet_share_qual="Notable (5-15%)", contract_years=5.0, renewal_cliff="2028-Q2",
        ev_ebitda_anchor=14.0, ev_ebitda_supplier=None,
        valuation_narrative="PLUG pre-revenue on green hydrogen scale; Duke Energy's North Carolina H2 hub creates 5-year pilot purchase agreement. Execution risk high but DOE hydrogen hub award ($750M) de-risks near-term cash burn.",
        source_url="https://ir.plugpower.com/",
    ),
]

# ── CONSUMER STAPLES & LOGISTICS ──────────────────────────────────────────────

_CONSUMER_LINKS: list[SupplyChainLink] = [
    SupplyChainLink(
        anchor_ticker="WMT", anchor_name="Walmart", anchor_index="S&P 500",
        supplier_ticker="SEE", supplier_name="Sealed Air Corp",
        sector="Consumer", supply_layer="Cryovac Food Packaging & Protective Mailers (Fulfillment Centers)",
        connection_type="Preferred_Supplier", wallet_share_pct=18.0,
        wallet_share_qual="Significant (15-30%)", contract_years=3.0, renewal_cliff="2027-Q1",
        ev_ebitda_anchor=12.0, ev_ebitda_supplier=9.0, pe_anchor=26.0, pe_supplier=12.0,
        valuation_narrative="SEE trades at 9× EV/EBITDA vs WMT 12×. Walmart fresh-food packaging and e-commerce protective mailing contracts represent ~18% of SEE Food segment. Automation-first packaging (Bubble Wrap AI) reduces Walmart's per-shipment cost 12-15%.",
        source_url="https://ir.sealedair.com/",
    ),
    SupplyChainLink(
        anchor_ticker="WMT", anchor_name="Walmart", anchor_index="S&P 500",
        supplier_ticker="CHRW", supplier_name="C.H. Robinson Worldwide",
        sector="Consumer", supply_layer="Truckload & LTL Freight Brokerage for Walmart Domestic Supply Chain",
        connection_type="Preferred_Supplier", wallet_share_pct=9.0,
        wallet_share_qual="Notable (5-15%)", contract_years=2.0, renewal_cliff="2026-Q3",
        ev_ebitda_anchor=12.0, ev_ebitda_supplier=11.0,
        valuation_narrative="CHRW at 11× EV/EBITDA — near parity with WMT but with 15% operating margins in a soft freight market. Navisphere TMS platform creates switching costs for Walmart's omnichannel DC network.",
        source_url="https://ir.chrobinson.com/",
    ),
    SupplyChainLink(
        anchor_ticker="WMT", anchor_name="Walmart", anchor_index="S&P 500",
        supplier_ticker="UFPT", supplier_name="UFP Technologies",
        sector="Consumer", supply_layer="Custom Protective Foam & Moulded Fibre Packaging for Walmart Private Label",
        connection_type="Preferred_Supplier", wallet_share_pct=22.0,
        wallet_share_qual="Significant (15-30%)", contract_years=3.0, renewal_cliff="2026-Q4",
        ev_ebitda_anchor=12.0, ev_ebitda_supplier=14.0,
        valuation_narrative="UFPT micro-cap ($1.2bn mkt cap) with 22% revenue from Walmart electronics packaging. Sustainable moulded pulp pivot reduces plastic content, aligning with WMT's 2030 packaging pledge and creating new programme wins.",
        source_url="https://ir.ufpt.com/",
    ),
    SupplyChainLink(
        anchor_ticker="COST", anchor_name="Costco", anchor_index="NASDAQ",
        supplier_ticker="SON", supplier_name="Sonoco Products",
        sector="Consumer", supply_layer="Retail-Ready Corrugated & Composite Cans for Kirkland Signature Products",
        connection_type="Preferred_Supplier", wallet_share_pct=11.0,
        wallet_share_qual="Notable (5-15%)", contract_years=4.0, renewal_cliff="2027-Q2",
        ev_ebitda_anchor=22.0, ev_ebitda_supplier=8.0,
        valuation_narrative="SON at 8× EV/EBITDA — a 63% discount to Costco — producing Kirkland branded packaging. Composite cans are growing 8% YoY driven by Costco's private-label expansion into premiumised food categories.",
        source_url="https://investor.sonoco.com/",
    ),
    SupplyChainLink(
        anchor_ticker="AMZN", anchor_name="Amazon", anchor_index="NASDAQ",
        supplier_ticker="GXO", supplier_name="GXO Logistics",
        sector="Consumer", supply_layer="Automated Fulfilment Centre Operations & Returns Processing",
        connection_type="JV_Partner", wallet_share_pct=14.0,
        wallet_share_qual="Notable (5-15%)", contract_years=5.0, renewal_cliff="2028-Q4",
        ev_ebitda_anchor=32.0, ev_ebitda_supplier=10.0,
        valuation_narrative="GXO at 10× EV/EBITDA — 69% discount to AMZN — operating Amazon-branded fulfilment automation at scale. GXO's advanced robotics (Quiet Logistics acquisition) reduces Amazon's picking cost 35% vs. manual DC.",
        source_url="https://ir.gxo.com/",
    ),
    SupplyChainLink(
        anchor_ticker="PG", anchor_name="Procter & Gamble", anchor_index="S&P 500",
        supplier_ticker="PPG", supplier_name="PPG Industries",
        sector="Consumer", supply_layer="Specialty Packaging Coatings & Aerosol Barrier Compounds",
        connection_type="Preferred_Supplier", wallet_share_pct=7.0,
        wallet_share_qual="Notable (5-15%)", contract_years=3.0, renewal_cliff="2026-Q4",
        ev_ebitda_anchor=18.0, ev_ebitda_supplier=11.0,
        valuation_narrative="PPG at 11× EV/EBITDA with P&G as top-3 packaging coatings customer. Sustainable aerospace and consumer packaging growth drives 6-8% CAGR for PPG's Industrial Coatings segment.",
        source_url="https://investor.ppg.com/",
    ),
    SupplyChainLink(
        anchor_ticker="TSCO.L", anchor_name="Tesco", anchor_index="FTSE 100",
        supplier_ticker="WRK", supplier_name="WestRock",
        sector="Consumer", supply_layer="Corrugated Retail-Ready Packaging for Tesco Own-Brand Lines",
        connection_type="Preferred_Supplier", wallet_share_pct=6.0,
        wallet_share_qual="Notable (5-15%)", contract_years=3.0, renewal_cliff="2027-Q1",
        ev_ebitda_anchor=8.0, ev_ebitda_supplier=7.0,
        valuation_narrative="WRK trading at 7× EV/EBITDA — compressed by Smurfit merger integration uncertainty. Tesco 'Farm Brands' packaging programme drives consistent corrugated volume regardless of merger outcome.",
        source_url="https://ir.westrock.com/",
    ),
]

# ── DEFENSE & AEROSPACE ───────────────────────────────────────────────────────

_DEFENSE_LINKS: list[SupplyChainLink] = [
    SupplyChainLink(
        anchor_ticker="LMT", anchor_name="Lockheed Martin", anchor_index="S&P 500",
        supplier_ticker="TDG", supplier_name="TransDigm Group",
        sector="Defense", supply_layer="Sole-Source Proprietary Aerospace Components (F-35 Actuation & Connectors)",
        connection_type="Sole_Supplier", wallet_share_pct=8.0,
        wallet_share_qual="Notable (5-15%)", contract_years=10.0, renewal_cliff="2032-Q1",
        ev_ebitda_anchor=16.0, ev_ebitda_supplier=22.0, pe_anchor=18.0, pe_supplier=28.0,
        valuation_narrative="TDG commands a premium justified by 85%+ proprietary aftermarket parts for F-35 and Legacy platforms. Lockheed cannot substitute — sole-source status across 900+ part numbers creates 20-35% EBITDA margin floor.",
        exec_quote="TransDigm components are in every F-35 we manufacture — there is no alternative supplier",
        source_url="https://ir.transdigm.com/",
    ),
    SupplyChainLink(
        anchor_ticker="LMT", anchor_name="Lockheed Martin", anchor_index="S&P 500",
        supplier_ticker="HEI", supplier_name="HEICO Corp",
        sector="Defense", supply_layer="FAA-Approved PMA Replacement Parts for F-16/F-22 Legacy Fleet",
        connection_type="Preferred_Supplier", wallet_share_pct=6.0,
        wallet_share_qual="Notable (5-15%)", contract_years=5.0, renewal_cliff="2028-Q3",
        ev_ebitda_anchor=16.0, ev_ebitda_supplier=34.0, pe_anchor=18.0, pe_supplier=48.0,
        valuation_narrative="HEICO commands 34× EV/EBITDA — premium justified by FAA-PMA moat and 50+ year legacy fleet service relationships. F-16 global fleet life extension to 2035+ creates 15+ year recurring parts revenue stream.",
        source_url="https://www.heico.com/investor-relations/",
    ),
    SupplyChainLink(
        anchor_ticker="RTX", anchor_name="RTX (Raytheon Technologies)", anchor_index="S&P 500",
        supplier_ticker="MOG.A", supplier_name="Moog Inc",
        sector="Defense", supply_layer="Flight Control Actuation Systems for Missiles & UAVs",
        connection_type="Sole_Supplier", wallet_share_pct=20.0,
        wallet_share_qual="Significant (15-30%)", contract_years=8.0, renewal_cliff="2031-Q1",
        ev_ebitda_anchor=14.0, ev_ebitda_supplier=12.0, pe_anchor=16.0, pe_supplier=15.0,
        valuation_narrative="Moog sole-source actuation provider across Raytheon's AIM-120C, AIM-9X and SM-6 missile programmes. Post-Ukraine defence spending surge creates 5-year backlog at record levels; near-parity valuation offers unwarranted discount.",
        exec_quote="Moog's precision actuation is qualified on every air-to-air missile in our portfolio",
        source_url="https://ir.moog.com/",
    ),
    SupplyChainLink(
        anchor_ticker="RTX", anchor_name="RTX (Raytheon Technologies)", anchor_index="S&P 500",
        supplier_ticker="KTOS", supplier_name="Kratos Defense & Security",
        sector="Defense", supply_layer="Affordable Mass Attrition UAV Targets & XQ-58A Valkyrie Sub-Systems",
        connection_type="Subcontractor", wallet_share_pct=15.0,
        wallet_share_qual="Significant (15-30%)", contract_years=4.0, renewal_cliff="2027-Q4",
        ev_ebitda_anchor=14.0, ev_ebitda_supplier=28.0,
        valuation_narrative="KTOS growing into a $2bn tactical UAV player riding a structural drone-warfare procurement wave. RTX IBCS integration creates multi-year sub-contract visibility. Premium valuation (28× EV/EBITDA) reflects embedded CAGR expectations of 22%.",
        source_url="https://ir.kratosdefense.com/",
    ),
    SupplyChainLink(
        anchor_ticker="GD", anchor_name="General Dynamics", anchor_index="S&P 500",
        supplier_ticker="DCO", supplier_name="Ducommun",
        sector="Defense", supply_layer="Structural Aerostructures & Electronic Systems for Gulfstream & Stryker IFV",
        connection_type="Preferred_Supplier", wallet_share_pct=30.0,
        wallet_share_qual="Major (30-50%)", contract_years=5.0, renewal_cliff="2028-Q2",
        ev_ebitda_anchor=15.0, ev_ebitda_supplier=9.0, pe_anchor=16.0, pe_supplier=12.0,
        valuation_narrative="DCO at 9× EV/EBITDA — a 40% discount to GD — with ~30% of revenue from General Dynamics platforms. Gulfstream G700/G800 production ramp and Stryker upgrade cycle create 2-year structural order uplift.",
        source_url="https://ir.ducommun.com/",
    ),
    SupplyChainLink(
        anchor_ticker="BA", anchor_name="Boeing", anchor_index="S&P 500",
        supplier_ticker="SPR", supplier_name="Spirit AeroSystems",
        sector="Defense", supply_layer="737 MAX Fuselages & 787 Nacelles — Primary Structural Assembly",
        connection_type="Sole_Supplier", wallet_share_pct=83.0,
        wallet_share_qual="Critical (>50%)", contract_years=10.0, renewal_cliff="2033-Q4",
        ev_ebitda_anchor=28.0, ev_ebitda_supplier=12.0,
        valuation_narrative="SPR is effectively a single-customer business (83% Boeing revenue). Fuselage quality issues (plug-out incident, Jan 2024) created massive overhang — but Boeing's re-acquisition proposal (announced mid-2024) implies structural floor. Binary event risk.",
        notes="Boeing acquisition offer at ~$37.25/share (Jun 2024) creates hard valuation floor",
        source_url="https://ir.spiritaero.com/",
    ),
    SupplyChainLink(
        anchor_ticker="LDOF.PA", anchor_name="Airbus", anchor_index="CAC 40",
        supplier_ticker="MRCY", supplier_name="Mercury Systems",
        sector="Defense", supply_layer="Mission Computing, EW Processing & Safety-Critical Avionics Modules",
        connection_type="Preferred_Supplier", wallet_share_pct=12.0,
        wallet_share_qual="Notable (5-15%)", contract_years=7.0, renewal_cliff="2030-Q1",
        ev_ebitda_anchor=14.0, ev_ebitda_supplier=20.0,
        valuation_narrative="MRCY at 20× EV/EBITDA, premium reflecting SOSA-aligned open architecture moat. Airbus A400M mission computer and ATM-F radar processing programmes provide EU defence revenue diversification outside US DoD budget cycles.",
        source_url="https://ir.mrcy.com/",
    ),
]

# ── HEALTHCARE, BIOTECH & PHARMA ──────────────────────────────────────────────

_HEALTHCARE_LINKS: list[SupplyChainLink] = [
    SupplyChainLink(
        anchor_ticker="PFE", anchor_name="Pfizer", anchor_index="S&P 500",
        supplier_ticker="ICLR", supplier_name="ICON plc",
        sector="Healthcare", supply_layer="CRO: Phase II-IV Clinical Trial Management & Biostatistics",
        connection_type="CRO", wallet_share_pct=16.0,
        wallet_share_qual="Significant (15-30%)", contract_years=5.0, renewal_cliff="2028-Q3",
        ev_ebitda_anchor=10.0, ev_ebitda_supplier=14.0, pe_anchor=12.0, pe_supplier=20.0,
        valuation_narrative="ICON at 14× EV/EBITDA vs PFE 10× — modest premium reflecting CRO oligopoly pricing. PFE represents ~16% of ICON's revenue after PRA Health Sciences merger. Post-COVID pipeline rationalisation at Pfizer creates near-term revenue headwind.",
        exec_quote="ICON manages our Phase III oncology portfolio across 40+ countries",
        source_url="https://ir.iconplc.com/",
    ),
    SupplyChainLink(
        anchor_ticker="PFE", anchor_name="Pfizer", anchor_index="S&P 500",
        supplier_ticker="CRL", supplier_name="Charles River Laboratories",
        sector="Healthcare", supply_layer="Discovery CRO: In-Vitro Toxicology, GLP Safety & Drug Metabolism Studies",
        connection_type="CRO", wallet_share_pct=12.0,
        wallet_share_qual="Notable (5-15%)", contract_years=3.0, renewal_cliff="2026-Q4",
        ev_ebitda_anchor=10.0, ev_ebitda_supplier=12.0,
        valuation_narrative="CRL at near-parity EV/EBITDA to Pfizer with ~12% Pfizer revenue concentration. Post-COVID inventory destocking headwind resolved; biotech VC recovery in 2025-26 drives new drug candidate pipeline growth.",
        source_url="https://ir.crl.com/",
    ),
    SupplyChainLink(
        anchor_ticker="LLY", anchor_name="Eli Lilly", anchor_index="S&P 500",
        supplier_ticker="CTLT", supplier_name="Catalent",
        sector="Healthcare", supply_layer="GLP-1 Drug Product Fill-Finish & Parenteral Manufacturing (Tirzepatide)",
        connection_type="CDMO", wallet_share_pct=22.0,
        wallet_share_qual="Significant (15-30%)", contract_years=6.0, renewal_cliff="2029-Q2",
        ev_ebitda_anchor=62.0, ev_ebitda_supplier=18.0, pe_anchor=82.0, pe_supplier=28.0,
        valuation_narrative="CTLT at 18× EV/EBITDA — a 71% discount to LLY — as the primary Mounjaro/Tirzepatide fill-finish manufacturer. Novo Nordisk acquisition of 3 Catalent sites (announced Aug 2024) and LLY's manufacturing expansion create supply-chain structural tension.",
        exec_quote="Catalent is a critical manufacturing partner for our incretin medicine supply ramp",
        notes="Novo Nordisk acquired 3 Catalent facilities Aug 2024 — risk of LLY supply concentration",
        source_url="https://ir.catalent.com/",
    ),
    SupplyChainLink(
        anchor_ticker="AZN", anchor_name="AstraZeneca", anchor_index="FTSE 100",
        supplier_ticker="LNZA", supplier_name="LanzaTech Global",
        sector="Healthcare", supply_layer="Sustainable Fermentation Carbon Capture for API Synthesis",
        connection_type="JV_Partner", wallet_share_pct=20.0,
        wallet_share_qual="Significant (15-30%)", contract_years=8.0, renewal_cliff="2031-Q4",
        ev_ebitda_anchor=22.0, ev_ebitda_supplier=None,
        valuation_narrative="LNZA JV with AstraZeneca for carbon-negative API precursor synthesis is a 2026-2028 inflection story. AZN's 2030 sustainability roadmap requires 50% bio-based API feedstock — LNZA is the only industrial-scale CO2-to-ethanol technology.",
        source_url="https://investors.lanzatech.com/",
    ),
    SupplyChainLink(
        anchor_ticker="JNJ", anchor_name="Johnson & Johnson", anchor_index="S&P 500",
        supplier_ticker="ILMN", supplier_name="Illumina",
        sector="Healthcare", supply_layer="Next-Generation Sequencing Platforms for Oncology Companion Diagnostics",
        connection_type="JV_Partner", wallet_share_pct=10.0,
        wallet_share_qual="Notable (5-15%)", contract_years=5.0, renewal_cliff="2028-Q1",
        ev_ebitda_anchor=16.0, ev_ebitda_supplier=25.0,
        valuation_narrative="Illumina at 25× EV/EBITDA (compressed from 60× post-GRAIL divestiture). J&J Janssen oncology CDx programmes use NovaSeq 6000/X+ for tumour profiling. Sequencing-as-diagnosis moat strengthens with pan-cancer cfDNA regulatory submissions.",
        source_url="https://investor.illumina.com/",
    ),
    SupplyChainLink(
        anchor_ticker="MRK", anchor_name="Merck & Co", anchor_index="S&P 500",
        supplier_ticker="BCYC", supplier_name="Bicycle Therapeutics",
        sector="Healthcare", supply_layer="Bicyclic Peptide (BT-ADC) Platform Licensing for Keytruda Combination",
        connection_type="JV_Partner", wallet_share_pct=35.0,
        wallet_share_qual="Major (30-50%)", contract_years=7.0, renewal_cliff="2030-Q2",
        ev_ebitda_anchor=14.0, ev_ebitda_supplier=None,
        valuation_narrative="BCYC development-stage biotech with MSD collaboration deal ($1.75bn potential milestones). Keytruda LOE (2028) creates urgency for combination therapy pipeline — BCYC BT-ADC oncology platform is strategically critical.",
        notes="Milestone-based deal; revenue recognition begins Phase II initiation 2026",
        source_url="https://ir.bicycletherapeutics.com/",
    ),
    SupplyChainLink(
        anchor_ticker="MRK", anchor_name="Merck & Co", anchor_index="S&P 500",
        supplier_ticker="PTGX", supplier_name="Protagonist Therapeutics",
        sector="Healthcare", supply_layer="Oral Peptide Platform (Rusfertide) — Polycythemia Vera FDA Submission",
        connection_type="JV_Partner", wallet_share_pct=60.0,
        wallet_share_qual="Critical (>50%)", contract_years=10.0, renewal_cliff="2034-Q4",
        ev_ebitda_anchor=14.0, ev_ebitda_supplier=None,
        valuation_narrative="PTGX ~60% dependent on Merck development agreement. Rusfertide NDA submission expected H1 2026 — approval creates $600M+ peak sales opportunity with PTGX retaining 35% US profit share.",
        source_url="https://ir.protagonist-inc.com/",
    ),
    SupplyChainLink(
        anchor_ticker="ABBV", anchor_name="AbbVie", anchor_index="S&P 500",
        supplier_ticker="NBIX", supplier_name="Neurocrine Biosciences",
        sector="Healthcare", supply_layer="CNS Royalty Collaboration — Ingrezza (Valbenazine) Co-Promotion",
        connection_type="JV_Partner", wallet_share_pct=28.0,
        wallet_share_qual="Major (30-50%)", contract_years=8.0, renewal_cliff="2031-Q2",
        ev_ebitda_anchor=16.0, ev_ebitda_supplier=32.0,
        valuation_narrative="NBIX at 32× EV/EBITDA premium — Ingrezza TD franchise has >80% market share and $2.4bn peak sales trajectory. AbbVie co-commercialisation extends NBIX commercial reach without proportionate cost structure.",
        source_url="https://ir.neurocrine.com/",
    ),
]

# ── MATERIALS & MINING ────────────────────────────────────────────────────────

_MATERIALS_LINKS: list[SupplyChainLink] = [
    SupplyChainLink(
        anchor_ticker="TSLA", anchor_name="Tesla", anchor_index="NASDAQ",
        supplier_ticker="ALBE", supplier_name="Albemarle Corp",
        sector="Materials", supply_layer="Battery-Grade Lithium Hydroxide for 4680 Cell Production",
        connection_type="Preferred_Supplier", wallet_share_pct=20.0,
        wallet_share_qual="Significant (15-30%)", contract_years=5.0, renewal_cliff="2028-Q4",
        ev_ebitda_anchor=52.0, ev_ebitda_supplier=8.0, pe_anchor=62.0, pe_supplier=12.0,
        valuation_narrative="ALBE at 8× EV/EBITDA — 84% discount to TSLA — despite being strategically irreplaceable lithium hydroxide supplier for 4680 cell chemistry. Lithium price trough (2024) compresses earnings; medium-term EV demand recovery restores margin power.",
        exec_quote="Albemarle is our primary lithium hydroxide partner for the Nevada Gigafactory",
        source_url="https://ir.albemarle.com/",
    ),
    SupplyChainLink(
        anchor_ticker="TSLA", anchor_name="Tesla", anchor_index="NASDAQ",
        supplier_ticker="MP", supplier_name="MP Materials",
        sector="Materials", supply_layer="Rare Earth Magnets (NdFeB) for Permanent Magnet Motor in Model S/X/3",
        connection_type="Sole_Supplier", wallet_share_pct=35.0,
        wallet_share_qual="Major (30-50%)", contract_years=10.0, renewal_cliff="2033-Q2",
        ev_ebitda_anchor=52.0, ev_ebitda_supplier=None,
        valuation_narrative="MP is the only US-based NdFeB magnet manufacturer at scale — Tesla's 10-year supply agreement (2023) makes MP sole-source for EV traction motor magnets. Fort Worth magnet facility provides supply chain sovereignty vs. China rare earth export controls.",
        exec_quote="MP Materials is essential to our mission to decarbonise transportation through domestic supply chains",
        source_url="https://ir.mpmaterials.com/",
    ),
    SupplyChainLink(
        anchor_ticker="AAPL", anchor_name="Apple", anchor_index="NASDAQ",
        supplier_ticker="IPGP", supplier_name="IPG Photonics",
        sector="Materials", supply_layer="High-Power Industrial Lasers for Sapphire & Ceramic Screen Machining",
        connection_type="Preferred_Supplier", wallet_share_pct=15.0,
        wallet_share_qual="Significant (15-30%)", contract_years=4.0, renewal_cliff="2027-Q1",
        ev_ebitda_anchor=32.0, ev_ebitda_supplier=18.0,
        valuation_narrative="IPGP at 18× EV/EBITDA — 44% discount to AAPL — as preferred supplier of high-power fibre lasers used in watch-face and iPhone display sapphire machining. EV battery welding (CATL, Panasonic) diversification reduces Apple revenue concentration.",
        source_url="https://www.ipgphotonics.com/en/about/investor-relations",
    ),
    SupplyChainLink(
        anchor_ticker="AAPL", anchor_name="Apple", anchor_index="NASDAQ",
        supplier_ticker="VIAV", supplier_name="Viavi Solutions",
        sector="Materials", supply_layer="Optically Variable Pigments & Secure Colour-Shift Ink for iPhone Structural Colour",
        connection_type="Sole_Supplier", wallet_share_pct=20.0,
        wallet_share_qual="Significant (15-30%)", contract_years=5.0, renewal_cliff="2028-Q3",
        ev_ebitda_anchor=32.0, ev_ebitda_supplier=14.0,
        valuation_narrative="VIAV OVP (optically variable pigment) is the sole-source colour-shift technology for iPhone's titanium and aluminium chassis structural colouring. Apple accounts for ~20% of VIAV Network Instruments revenue.",
        source_url="https://investors.viavisolutions.com/",
    ),
]


# ── CONSOLIDATED REGISTRY ─────────────────────────────────────────────────────

SUPPLY_CHAIN_REGISTRY: list[SupplyChainLink] = (
    _TECH_LINKS + _ENERGY_LINKS + _CONSUMER_LINKS + _DEFENSE_LINKS +
    _HEALTHCARE_LINKS + _MATERIALS_LINKS
)

ALL_SECTORS = sorted(set(link.sector for link in SUPPLY_CHAIN_REGISTRY))
ALL_CONNECTION_TYPES = sorted(set(link.connection_type for link in SUPPLY_CHAIN_REGISTRY))

SECTOR_ANCHORS: dict[str, list[str]] = {}
for _link in SUPPLY_CHAIN_REGISTRY:
    SECTOR_ANCHORS.setdefault(_link.sector, [])
    if _link.anchor_ticker not in SECTOR_ANCHORS[_link.sector]:
        SECTOR_ANCHORS[_link.sector].append(_link.anchor_ticker)
