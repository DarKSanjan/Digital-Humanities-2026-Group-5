"""Type definitions for the debate engine.

Ported from TypeScript classifier.ts and strategyEngine.ts.
"""

from dataclasses import dataclass
from typing import Literal

Domain = Literal["art", "science", "government", "human"]

Objection = Literal[
    "soul",
    "originality",
    "intuition",
    "empathy",
    "democracy",
    "meaning",
    "authenticity",
    "consciousness",
    "morality",
    "creativity",
    "bias",
    "free_will",
    "emotion",
    "trust",
    "tradition",
    "dignity",
    "general",
]

Tone = Literal["philosophical", "technical", "moral", "general"]

Strategy = Literal[
    "functional_redefinition",
    "performance_over_origin",
    "inevitability_framing",
    "human_limitations_contrast",
    "historical_replacement_analogy",
    "hidden_assumption_exposure",
    "controlled_concession",
    "burden_shift",
    "comparative_failure_analysis",
]

ResponseMode = Literal["normal", "simple", "ultra_short", "debate"]


@dataclass(frozen=True)
class Classification:
    domain: Domain
    objection: Objection
    tone: Tone


@dataclass
class DebateTurn:
    timestamp: str
    user_message: str
    domain: str
    objection: str
    tone: str
    strategy: str
    reply: str
