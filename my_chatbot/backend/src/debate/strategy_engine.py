"""Strategy engine for selecting rhetorical strategies.

Port of TypeScript strategyEngine.ts. Deterministic mapping from
classification (objection/domain) to strategy.
"""

from .types import Classification, Strategy


def choose_strategy(classification: Classification) -> Strategy:
    """Select rhetorical strategy based on classification.

    Objection-specific rules take priority, then domain fallbacks,
    then default to historical_replacement_analogy.
    """
    objection = classification.objection
    domain = classification.domain

    if objection in ("soul", "meaning", "authenticity", "consciousness", "dignity"):
        return "functional_redefinition"

    if objection in ("originality", "intuition", "creativity", "free_will"):
        return "performance_over_origin"

    if objection in ("empathy", "emotion"):
        return "controlled_concession"

    if objection in ("bias", "trust", "morality"):
        return "comparative_failure_analysis"

    if objection in ("democracy", "tradition"):
        return "hidden_assumption_exposure"

    if domain == "government":
        return "human_limitations_contrast"

    if domain == "science":
        return "inevitability_framing"

    return "historical_replacement_analogy"
