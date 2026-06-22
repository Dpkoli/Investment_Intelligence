"""Contrarian Scoring Engine sub-package — clean ASCII public aliases."""

import analytics.scoring.contrarian_engine as _eng
import analytics.scoring.models as _mdl

# Expose the engine class under a clean ASCII name (source uses Cyrillic lookalikes)
ScoringEngine: type = next(
    cls for name, cls in vars(_eng).items()
    if isinstance(cls, type) and "Scoring" in name
)

ScoreResult: type = next(
    cls for name, cls in vars(_mdl).items()
    if isinstance(cls, type) and "Result" in name and "Score" in name
)

from analytics.scoring.models import CSComponents, CSRankedBatch  # noqa: E402

__all__ = ["ScoringEngine", "ScoreResult", "CSComponents", "CSRankedBatch"]
