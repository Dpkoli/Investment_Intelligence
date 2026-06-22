"""
Sovereign Crypto Networks — 70+ asset registry.
Tiers: Store-of-Value, Smart Contract, Layer-2, DeFi, Exchange Tokens,
       Payments, AI/Data, Gaming/NFT, Privacy, Storage,
       Stablecoins, Wrapped/Liquid-Staking, Meme,
       LSE ETPs, Global Trusts.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

log = logging.getLogger(__name__)


class CryptoTier(str, Enum):
    STORE_OF_VALUE  = "Store of Value"
    SMART_CONTRACT  = "Smart Contract Platform"
    LAYER_2         = "Layer 2 / Scaling"
    DEFI            = "DeFi Protocol"
    EXCHANGE_TOKEN  = "Exchange Token"
    PAYMENTS        = "Payments & Cross-Border"
    AI_DATA         = "AI & Data Infrastructure"
    GAMING_NFT      = "Gaming & NFT"
    PRIVACY         = "Privacy"
    STORAGE         = "Decentralized Storage"
    STABLECOIN      = "Stablecoin"
    WRAPPED         = "Wrapped / Liquid Staking"
    MEME            = "Meme / Community"
    LSE_ETP         = "LSE Exchange-Traded Product"
    GLOBAL_TRUST    = "Global Crypto Trust"


class FCAStatus(str, Enum):
    REGISTERED      = "FCA Registered"
    UNREGISTERED    = "Unregistered"
    PENDING         = "Application Pending"
    REGULATED_ETP   = "Regulated ETP (LSE)"
    GRANDFATHERED   = "Grandfathered"
    NOT_APPLICABLE  = "N/A (Non-UK)"


@dataclass
class CryptoAsset:
    ticker: str
    name: str
    tier: CryptoTier
    fca_status: FCAStatus
    exchange: str
    currency: str
    blockchain: Optional[str] = None
    issuer: Optional[str] = None
    isin: Optional[str] = None
    coingecko_id: Optional[str] = None
    yf_ticker: Optional[str] = None
    aum_mn: Optional[float] = None
    ter: Optional[float] = None
    notes: Optional[str] = None


CRYPTO_REGISTRY: list[CryptoAsset] = [
    # ── Store of Value ────────────────────────────────────────────────────────
    CryptoAsset("BTC",    "Bitcoin",              CryptoTier.STORE_OF_VALUE, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Bitcoin",         coingecko_id="bitcoin",             yf_ticker="BTC-USD"),
    CryptoAsset("ETH",    "Ethereum",             CryptoTier.STORE_OF_VALUE, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum",        coingecko_id="ethereum",            yf_ticker="ETH-USD"),

    # ── Smart Contract Platforms ──────────────────────────────────────────────
    CryptoAsset("SOL",    "Solana",               CryptoTier.SMART_CONTRACT, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Solana",          coingecko_id="solana",              yf_ticker="SOL-USD"),
    CryptoAsset("ADA",    "Cardano",              CryptoTier.SMART_CONTRACT, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Cardano",         coingecko_id="cardano",             yf_ticker="ADA-USD"),
    CryptoAsset("AVAX",   "Avalanche",            CryptoTier.SMART_CONTRACT, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Avalanche C-Chain",coingecko_id="avalanche-2",        yf_ticker="AVAX-USD"),
    CryptoAsset("DOT",    "Polkadot",             CryptoTier.SMART_CONTRACT, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Polkadot",        coingecko_id="polkadot",            yf_ticker="DOT-USD"),
    CryptoAsset("NEAR",   "NEAR Protocol",        CryptoTier.SMART_CONTRACT, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="NEAR",            coingecko_id="near",                yf_ticker="NEAR-USD"),
    CryptoAsset("APT",    "Aptos",                CryptoTier.SMART_CONTRACT, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Aptos",           coingecko_id="aptos",               yf_ticker="APT-USD"),
    CryptoAsset("SUI",    "Sui",                  CryptoTier.SMART_CONTRACT, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Sui",             coingecko_id="sui",                 yf_ticker="SUI20947-USD"),
    CryptoAsset("TON",    "Toncoin",              CryptoTier.SMART_CONTRACT, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="TON Blockchain",  coingecko_id="the-open-network",    yf_ticker="TON11419-USD"),
    CryptoAsset("TRX",    "TRON",                 CryptoTier.SMART_CONTRACT, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="TRON",            coingecko_id="tron",                yf_ticker="TRX-USD"),
    CryptoAsset("ICP",    "Internet Computer",    CryptoTier.SMART_CONTRACT, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Internet Computer",coingecko_id="internet-computer",  yf_ticker="ICP-USD"),
    CryptoAsset("VET",    "VeChain",              CryptoTier.SMART_CONTRACT, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="VeChainThor",     coingecko_id="vechain",             yf_ticker="VET-USD"),
    CryptoAsset("EOS",    "EOS",                  CryptoTier.SMART_CONTRACT, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="EOSIO",           coingecko_id="eos",                 yf_ticker="EOS-USD"),

    # ── Layer 2 / Scaling ─────────────────────────────────────────────────────
    CryptoAsset("ARB",    "Arbitrum",             CryptoTier.LAYER_2, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Arbitrum One",    coingecko_id="arbitrum",            yf_ticker="ARB11841-USD"),
    CryptoAsset("OP",     "Optimism",             CryptoTier.LAYER_2, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="OP Mainnet",      coingecko_id="optimism",            yf_ticker="OP-USD"),
    CryptoAsset("MATIC",  "Polygon",              CryptoTier.LAYER_2, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Polygon",         coingecko_id="matic-network",       yf_ticker="MATIC-USD"),
    CryptoAsset("STRK",   "Starknet",             CryptoTier.LAYER_2, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="StarkNet",        coingecko_id="starknet",            yf_ticker="STRK-USD"),
    CryptoAsset("IMX",    "Immutable X",          CryptoTier.LAYER_2, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Immutable X",     coingecko_id="immutable-x",         yf_ticker="IMX-USD"),
    CryptoAsset("ZK",     "ZKsync Era",           CryptoTier.LAYER_2, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="zkSync Era",      coingecko_id="zksync",              yf_ticker="ZK29110-USD"),
    CryptoAsset("BLAST",  "Blast",                CryptoTier.LAYER_2, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Blast L2",        coingecko_id="blast",               yf_ticker="BLAST-USD"),
    CryptoAsset("MANTA",  "Manta Network",        CryptoTier.LAYER_2, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Manta Pacific",   coingecko_id="manta-network",       yf_ticker="MANTA-USD"),

    # ── DeFi Protocols ───────────────────────────────────────────────────────
    CryptoAsset("UNI",    "Uniswap",              CryptoTier.DEFI, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum/Multi",  coingecko_id="uniswap",             yf_ticker="UNI7083-USD"),
    CryptoAsset("AAVE",   "Aave",                 CryptoTier.DEFI, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum/Multi",  coingecko_id="aave",                yf_ticker="AAVE-USD"),
    CryptoAsset("MKR",    "Maker",                CryptoTier.DEFI, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum",        coingecko_id="maker",               yf_ticker="MKR-USD"),
    CryptoAsset("CRV",    "Curve DAO",            CryptoTier.DEFI, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum/Multi",  coingecko_id="curve-dao-token",     yf_ticker="CRV-USD"),
    CryptoAsset("COMP",   "Compound",             CryptoTier.DEFI, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum",        coingecko_id="compound-governance-token", yf_ticker="COMP-USD"),
    CryptoAsset("SNX",    "Synthetix",            CryptoTier.DEFI, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum/Optimism",coingecko_id="havven",             yf_ticker="SNX-USD"),
    CryptoAsset("GMX",    "GMX",                  CryptoTier.DEFI, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Arbitrum/Avalanche",coingecko_id="gmx",               yf_ticker="GMX-USD"),
    CryptoAsset("PENDLE", "Pendle",               CryptoTier.DEFI, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum/Multi",  coingecko_id="pendle",              yf_ticker="PENDLE-USD"),
    CryptoAsset("LDO",    "Lido DAO",             CryptoTier.DEFI, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum",        coingecko_id="lido-dao",            yf_ticker="LDO-USD"),
    CryptoAsset("1INCH",  "1inch",                CryptoTier.DEFI, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum/BSC",    coingecko_id="1inch",               yf_ticker="1INCH-USD"),

    # ── Exchange Tokens ───────────────────────────────────────────────────────
    CryptoAsset("BNB",    "BNB",                  CryptoTier.EXCHANGE_TOKEN, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="BNB Chain",       coingecko_id="binancecoin",         yf_ticker="BNB-USD"),
    CryptoAsset("OKB",    "OKB",                  CryptoTier.EXCHANGE_TOKEN, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="OKChain",         coingecko_id="okb",                 yf_ticker="OKB-USD"),
    CryptoAsset("CRO",    "Cronos",               CryptoTier.EXCHANGE_TOKEN, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Cronos",          coingecko_id="crypto-com-chain",    yf_ticker="CRO-USD"),
    CryptoAsset("KCS",    "KuCoin Token",         CryptoTier.EXCHANGE_TOKEN, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="KCC",             coingecko_id="kucoin-shares",       yf_ticker="KCS-USD"),

    # ── Payments & Cross-Border ───────────────────────────────────────────────
    CryptoAsset("XRP",    "XRP",                  CryptoTier.PAYMENTS, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="XRP Ledger",      coingecko_id="ripple",              yf_ticker="XRP-USD",
                notes="9th Circuit appeal — elevated legal uncertainty"),
    CryptoAsset("XLM",    "Stellar Lumens",       CryptoTier.PAYMENTS, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Stellar",         coingecko_id="stellar",             yf_ticker="XLM-USD"),
    CryptoAsset("ALGO",   "Algorand",             CryptoTier.PAYMENTS, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Algorand",        coingecko_id="algorand",            yf_ticker="ALGO-USD"),
    CryptoAsset("HBAR",   "Hedera",               CryptoTier.PAYMENTS, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Hedera",          coingecko_id="hedera-hashgraph",    yf_ticker="HBAR-USD"),
    CryptoAsset("ATOM",   "Cosmos Hub",           CryptoTier.PAYMENTS, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Cosmos Hub",      coingecko_id="cosmos",              yf_ticker="ATOM-USD"),
    CryptoAsset("LTC",    "Litecoin",             CryptoTier.PAYMENTS, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Litecoin",        coingecko_id="litecoin",            yf_ticker="LTC-USD"),
    CryptoAsset("BCH",    "Bitcoin Cash",         CryptoTier.PAYMENTS, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Bitcoin Cash",    coingecko_id="bitcoin-cash",        yf_ticker="BCH-USD"),

    # ── AI & Data Infrastructure ──────────────────────────────────────────────
    CryptoAsset("TAO",    "Bittensor",            CryptoTier.AI_DATA, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Bittensor",       coingecko_id="bittensor",           yf_ticker="TAO22974-USD"),
    CryptoAsset("FET",    "Fetch.ai (ASI Alliance)",CryptoTier.AI_DATA, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Fetch.ai",        coingecko_id="fetch-ai",            yf_ticker="FET-USD"),
    CryptoAsset("RENDER", "Render",               CryptoTier.AI_DATA, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Solana/Ethereum", coingecko_id="render-token",        yf_ticker="RENDER-USD"),
    CryptoAsset("GRT",    "The Graph",            CryptoTier.AI_DATA, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum/Multi",  coingecko_id="the-graph",           yf_ticker="GRT-USD"),
    CryptoAsset("LINK",   "Chainlink",            CryptoTier.AI_DATA, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum/Multi",  coingecko_id="chainlink",           yf_ticker="LINK-USD"),
    CryptoAsset("OCEAN",  "Ocean Protocol",       CryptoTier.AI_DATA, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum",        coingecko_id="ocean-protocol",      yf_ticker="OCEAN-USD"),
    CryptoAsset("RNDR",   "Render Network",       CryptoTier.AI_DATA, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum",        coingecko_id="render-token",        yf_ticker="RNDR-USD"),

    # ── Gaming & NFT ──────────────────────────────────────────────────────────
    CryptoAsset("AXS",    "Axie Infinity",        CryptoTier.GAMING_NFT, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ronin",           coingecko_id="axie-infinity",       yf_ticker="AXS-USD"),
    CryptoAsset("SAND",   "The Sandbox",          CryptoTier.GAMING_NFT, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum",        coingecko_id="the-sandbox",         yf_ticker="SAND-USD"),
    CryptoAsset("MANA",   "Decentraland",         CryptoTier.GAMING_NFT, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum",        coingecko_id="decentraland",        yf_ticker="MANA-USD"),
    CryptoAsset("FLOW",   "Flow",                 CryptoTier.GAMING_NFT, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Flow",            coingecko_id="flow",                yf_ticker="FLOW-USD"),
    CryptoAsset("GALA",   "Gala",                 CryptoTier.GAMING_NFT, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum/BSC",    coingecko_id="gala",                yf_ticker="GALA-USD"),
    CryptoAsset("APE",    "ApeCoin",              CryptoTier.GAMING_NFT, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum",        coingecko_id="apecoin",             yf_ticker="APE-USD"),

    # ── Privacy ───────────────────────────────────────────────────────────────
    CryptoAsset("XMR",    "Monero",               CryptoTier.PRIVACY, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Monero",          coingecko_id="monero",              yf_ticker="XMR-USD"),
    CryptoAsset("ZEC",    "Zcash",                CryptoTier.PRIVACY, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Zcash",           coingecko_id="zcash",               yf_ticker="ZEC-USD"),
    CryptoAsset("SCRT",   "Secret Network",       CryptoTier.PRIVACY, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Secret",          coingecko_id="secret",              yf_ticker="SCRT-USD"),

    # ── Decentralized Storage ─────────────────────────────────────────────────
    CryptoAsset("FIL",    "Filecoin",             CryptoTier.STORAGE, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Filecoin",        coingecko_id="filecoin",            yf_ticker="FIL-USD"),
    CryptoAsset("AR",     "Arweave",              CryptoTier.STORAGE, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Arweave",         coingecko_id="arweave",             yf_ticker="AR-USD"),
    CryptoAsset("STORJ",  "Storj",                CryptoTier.STORAGE, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum",        coingecko_id="storj",               yf_ticker="STORJ-USD"),

    # ── Stablecoins ───────────────────────────────────────────────────────────
    CryptoAsset("USDT",   "Tether USD",           CryptoTier.STABLECOIN, FCAStatus.PENDING, "Global", "USD",
                blockchain="Multi-chain",     coingecko_id="tether",              yf_ticker="USDT-USD",
                notes="UK EMI licence application under review; MiCA compliance required by Jun 2025"),
    CryptoAsset("USDC",   "USD Coin",             CryptoTier.STABLECOIN, FCAStatus.PENDING, "Global", "USD",
                blockchain="Multi-chain",     coingecko_id="usd-coin",            yf_ticker="USDC-USD",
                notes="Circle: FCA EMI registration filed Q1 2026"),
    CryptoAsset("DAI",    "Dai",                  CryptoTier.STABLECOIN, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum/Multi",  coingecko_id="dai",                 yf_ticker="DAI-USD"),
    CryptoAsset("GBPT",   "Pound Token",          CryptoTier.STABLECOIN, FCAStatus.PENDING, "UK", "GBP",
                blockchain="Ethereum",        coingecko_id="gbpt",
                notes="GBP-pegged; FCA registration pathway contested under FSMA s.234"),
    CryptoAsset("EURS",   "STASIS EURO",          CryptoTier.STABLECOIN, FCAStatus.UNREGISTERED, "Europe", "EUR",
                blockchain="Ethereum",        coingecko_id="stasis-eurs"),
    CryptoAsset("PYUSD",  "PayPal USD",           CryptoTier.STABLECOIN, FCAStatus.UNREGISTERED, "US", "USD",
                blockchain="Ethereum/Solana", coingecko_id="paypal-usd"),
    CryptoAsset("FRAX",   "Frax",                 CryptoTier.STABLECOIN, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum/Multi",  coingecko_id="frax"),
    CryptoAsset("LUSD",   "Liquity USD",          CryptoTier.STABLECOIN, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum",        coingecko_id="liquity-usd"),

    # ── Wrapped / Liquid Staking ──────────────────────────────────────────────
    CryptoAsset("WBTC",   "Wrapped Bitcoin (ERC-20)",CryptoTier.WRAPPED, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum",        coingecko_id="wrapped-bitcoin",     yf_ticker="WBTC-USD"),
    CryptoAsset("stETH",  "Lido Staked ETH",      CryptoTier.WRAPPED, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum",        coingecko_id="staked-ether",        yf_ticker="STETH-USD"),
    CryptoAsset("rETH",   "Rocket Pool ETH",      CryptoTier.WRAPPED, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum",        coingecko_id="rocket-pool-eth"),
    CryptoAsset("cbETH",  "Coinbase Wrapped Staked ETH",CryptoTier.WRAPPED, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum",        coingecko_id="coinbase-wrapped-staked-eth"),

    # ── Meme / Community ──────────────────────────────────────────────────────
    CryptoAsset("DOGE",   "Dogecoin",             CryptoTier.MEME, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Dogecoin",        coingecko_id="dogecoin",            yf_ticker="DOGE-USD"),
    CryptoAsset("SHIB",   "Shiba Inu",            CryptoTier.MEME, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum",        coingecko_id="shiba-inu",           yf_ticker="SHIB-USD"),
    CryptoAsset("PEPE",   "Pepe",                 CryptoTier.MEME, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Ethereum",        coingecko_id="pepe",                yf_ticker="PEPE24478-USD"),
    CryptoAsset("FLOKI",  "Floki",                CryptoTier.MEME, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="ETH / BNB Chain", coingecko_id="floki",               yf_ticker="FLOKI24093-USD"),
    CryptoAsset("WIF",    "dogwifhat",            CryptoTier.MEME, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Solana",          coingecko_id="dogwifcoin",          yf_ticker="WIF-USD"),
    CryptoAsset("BONK",   "Bonk",                 CryptoTier.MEME, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Solana",          coingecko_id="bonk",                yf_ticker="BONK-USD"),
    CryptoAsset("BOME",   "Book of Meme",         CryptoTier.MEME, FCAStatus.UNREGISTERED, "Global", "USD",
                blockchain="Solana",          coingecko_id="book-of-meme",        yf_ticker="BOME-USD"),

    # ── LSE Exchange-Traded Products ──────────────────────────────────────────
    CryptoAsset("IB1T.L",  "iShares Bitcoin ETP",             CryptoTier.LSE_ETP, FCAStatus.REGULATED_ETP, "LSE", "USD",
                issuer="BlackRock",  aum_mn=3_200, ter=0.15, isin="IE000MDACAP6",
                notes="Physically backed; FCA-approved; largest LSE BTC ETP"),
    CryptoAsset("BITB.L",  "CoinShares Physical Bitcoin",     CryptoTier.LSE_ETP, FCAStatus.REGULATED_ETP, "LSE", "USD",
                issuer="CoinShares", aum_mn=890,   ter=0.25, isin="XS1975316903"),
    CryptoAsset("WBTC.L",  "WisdomTree Physical Bitcoin",     CryptoTier.LSE_ETP, FCAStatus.REGULATED_ETP, "LSE", "USD",
                issuer="WisdomTree", aum_mn=680,   ter=0.35, isin="GB00BJYDH986"),
    CryptoAsset("WETH.L",  "WisdomTree Physical Ethereum",    CryptoTier.LSE_ETP, FCAStatus.REGULATED_ETP, "LSE", "USD",
                issuer="WisdomTree", aum_mn=240,   ter=0.35, isin="GB00BJYDH879"),
    CryptoAsset("ETHE.L",  "CoinShares Physical Ethereum",    CryptoTier.LSE_ETP, FCAStatus.REGULATED_ETP, "LSE", "USD",
                issuer="CoinShares", aum_mn=310,   ter=0.25, isin="XS2075781644"),
    CryptoAsset("SOLW.L",  "WisdomTree Physical Solana",      CryptoTier.LSE_ETP, FCAStatus.REGULATED_ETP, "LSE", "USD",
                issuer="WisdomTree", aum_mn=95,    ter=0.50, notes="SOL physical ETP; FCA-approved"),
    CryptoAsset("XRPL.L",  "WisdomTree Physical XRP",         CryptoTier.LSE_ETP, FCAStatus.REGULATED_ETP, "LSE", "USD",
                issuer="WisdomTree", aum_mn=42,    ter=0.50,
                notes="Elevated regulatory risk; XRP securities status contested"),
    CryptoAsset("MBTC.L",  "VanEck Bitcoin ETP",              CryptoTier.LSE_ETP, FCAStatus.REGULATED_ETP, "LSE", "USD",
                issuer="VanEck",     aum_mn=120,   ter=0.20, notes="Physically settled; CME custody"),
    CryptoAsset("21BTC.L", "21Shares Bitcoin ETP",            CryptoTier.LSE_ETP, FCAStatus.REGULATED_ETP, "LSE", "USD",
                issuer="21Shares",   aum_mn=580,   ter=0.21, notes="Largest LSE BTC ETP by volume"),
    CryptoAsset("HODL.L",  "VanEck Crypto & Blockchain Eq.",  CryptoTier.LSE_ETP, FCAStatus.REGULATED_ETP, "LSE", "USD",
                issuer="VanEck",     aum_mn=85,    ter=0.65, notes="Equity basket: Coinbase/MicroStrategy/Marathon"),
    CryptoAsset("DAPP.L",  "VanEck Dapp Leaders ETF",         CryptoTier.LSE_ETP, FCAStatus.REGULATED_ETP, "LSE", "USD",
                issuer="VanEck",     aum_mn=28,    ter=0.65, notes="dApp equity exposure: Coinbase/Uniswap/OpenSea"),
    CryptoAsset("KOIN.L",  "Fidelity Physical Bitcoin",       CryptoTier.LSE_ETP, FCAStatus.REGULATED_ETP, "LSE", "USD",
                issuer="Fidelity",   aum_mn=180,   ter=0.35, notes="Fidelity Digital Assets custody"),

    # ── Global Crypto Trusts / US-Listed ─────────────────────────────────────
    CryptoAsset("GBTC",   "Grayscale Bitcoin Trust ETF",      CryptoTier.GLOBAL_TRUST, FCAStatus.NOT_APPLICABLE, "US", "USD",
                issuer="Grayscale",  yf_ticker="GBTC", ter=1.50,
                notes="Converted to SEC-registered ETF Jan 2024; historically traded at large discount"),
    CryptoAsset("ETHE",   "Grayscale Ethereum Trust ETF",     CryptoTier.GLOBAL_TRUST, FCAStatus.NOT_APPLICABLE, "US", "USD",
                issuer="Grayscale",  yf_ticker="ETHE", ter=2.50,
                notes="ETF conversion completed May 2024"),
    CryptoAsset("BITO",   "ProShares Bitcoin Strategy ETF",   CryptoTier.GLOBAL_TRUST, FCAStatus.NOT_APPLICABLE, "US", "USD",
                issuer="ProShares",  yf_ticker="BITO", ter=0.95,
                notes="Futures-based; first US BTC ETF (Oct 2021)"),
    CryptoAsset("BITX",   "2× Bitcoin Strategy ETF",          CryptoTier.GLOBAL_TRUST, FCAStatus.NOT_APPLICABLE, "US", "USD",
                issuer="Volatility Shares", yf_ticker="BITX", ter=1.85,
                notes="2× leveraged BTC futures"),
    CryptoAsset("IBIT",   "iShares Bitcoin Trust ETF",        CryptoTier.GLOBAL_TRUST, FCAStatus.NOT_APPLICABLE, "US", "USD",
                issuer="BlackRock",  yf_ticker="IBIT", aum_mn=52_400, ter=0.25,
                notes="Largest US spot BTC ETF by AUM; launched Jan 2024"),
    CryptoAsset("FBTC",   "Fidelity Wise Origin Bitcoin",     CryptoTier.GLOBAL_TRUST, FCAStatus.NOT_APPLICABLE, "US", "USD",
                issuer="Fidelity",   yf_ticker="FBTC", aum_mn=22_800, ter=0.25,
                notes="Second largest US spot BTC ETF"),
]

ALL_TIERS = sorted(set(a.tier.value for a in CRYPTO_REGISTRY))
ALL_FCA_STATUSES = sorted(set(a.fca_status.value for a in CRYPTO_REGISTRY))
