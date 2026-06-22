"""
Contrarian Radar — modular product hub.
Each sub-package is a self-contained analytical domain with its own
data registry, live-price collector, and Streamlit renderer.
"""
from __future__ import annotations

__version__ = "2.0.0"

MODULES = [
    "core_equity",
    "thematic_sectors",
    "sovereign_crypto",
    "precious_metals",
    "kingmaker_intelligence",
    "regulatory_sandbox",
]
