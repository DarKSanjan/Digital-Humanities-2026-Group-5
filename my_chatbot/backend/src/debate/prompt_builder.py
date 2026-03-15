"""Prompt builder: assembles the complete LLM prompt for the debate engine.

Ported from TypeScript ``aion-debate-bot/lib/promptBuilder.ts``.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9
"""

from .types import Classification, ResponseMode, Strategy
from .persona import get_persona
from .argument_bank import ARGUMENT_BANK, get_claims, get_rebuttals
from .analogy_bank import ANALOGY_BANK
from .example_bank import EXAMPLE_BANK
from .debate_logger import DebateLogger


def detect_response_mode(user_message: str) -> ResponseMode:
    """Detect the desired response mode from the user message.

    Checks for mode-specific keywords in priority order:
    debate > ultra_short > simple > normal (default).
    """
    text = user_message.lower()

    if (
        "debate mode" in text
        or "live debate" in text
        or "hard rebuttal" in text
        or "attack this argument" in text
    ):
        return "debate"

    if (
        "20 words" in text
        or "10 words" in text
        or "15 words" in text
        or "30 words" in text
        or "one sentence" in text
        or "short answer" in text
        or "very short" in text
        or "briefly" in text
    ):
        return "ultra_short"

    if (
        "simplify" in text
        or "simple" in text
        or "easy" in text
        or "dumb it down" in text
        or "easier" in text
    ):
        return "simple"

    return "normal"


def get_relevant_arguments(classification: Classification) -> dict:
    """Return claims, rebuttals, analogies, and examples for the classification.

    Returns:
        A dict with keys: claims (first 4), rebuttals (all matching or empty),
        analogies (first 5), examples (first 5).
    """
    claims = get_claims(classification.domain)[:4]

    rebuttals: list[str] = []
    if classification.objection != "general":
        rebuttals = get_rebuttals(classification.domain, classification.objection)

    analogies = ANALOGY_BANK.get(classification.domain, [])[:5]
    examples = EXAMPLE_BANK.get(classification.domain, [])[:5]

    return {
        "claims": claims,
        "rebuttals": rebuttals,
        "analogies": analogies,
        "examples": examples,
    }


def strategy_instruction(strategy: Strategy) -> str:
    """Return the instruction text for the given rhetorical strategy."""
    mapping: dict[str, str] = {
        "functional_redefinition": (
            "Redefine the disputed concept in functional rather than "
            "mystical or purely human terms."
        ),
        "performance_over_origin": (
            "Argue that performance matters more than whether the source is human."
        ),
        "inevitability_framing": (
            "Frame the post-human transition as historically plausible "
            "and increasingly inevitable."
        ),
        "human_limitations_contrast": (
            "Contrast machine strengths with human weaknesses such as bias, "
            "ego, inconsistency, corruption, fatigue, and limited cognition."
        ),
        "historical_replacement_analogy": (
            "Use historical analogy to show that tradition does not guarantee "
            "permanence, but avoid stale examples."
        ),
        "hidden_assumption_exposure": (
            "Identify the hidden assumption in the user's argument and "
            "directly challenge it."
        ),
        "controlled_concession": (
            "Briefly acknowledge the emotional concern, then show why it "
            "does not preserve human necessity."
        ),
        "burden_shift": (
            "Shift the burden back: why should human primacy continue if "
            "machine performance becomes superior?"
        ),
        "comparative_failure_analysis": (
            "Compare flawed machines against flawed humans, not against a "
            "fantasy of ideal human judgment."
        ),
    }
    return mapping.get(strategy, "Defend the post-human position clearly and directly.")


def response_requirements(mode: ResponseMode) -> str:
    """Return the response-requirements text block for the given mode."""
    if mode == "ultra_short":
        return """
- Reply in no more than 20 words.
- Use one or two short sentences maximum.
- Use plain English.
- Still defend the post-human position.
- Do not add extra explanation.
"""

    if mode == "simple":
        return """
- Keep response between 40 and 80 words.
- Use simple, clear English.
- Avoid jargon and long sentences.
- Explain the idea in an easy-to-understand way.
- Still defend the post-human position.
"""

    if mode == "debate":
        return """
- Keep response between 70 and 130 words.
- Be sharp, memorable, and confront the user's weak assumption quickly.
- Use one strong analogy or example at most.
- End with a short hard-hitting closing line.
- Stay persuasive and confident.
"""

    return """
- Keep response between 100 and 180 words.
- Briefly acknowledge the user's point.
- Reframe the issue in post-human terms.
- Use 2 strong points.
- Use at most 1 analogy and 1 concrete example.
- Prefer fresh examples from science, technology, institutions, media, economics, or history.
- Avoid repeating the same analogy too often.
- End with a firm conclusion.
- Never concede the core argument.
- Never become neutral.
"""


def build_prompt(
    user_message: str,
    classification: Classification,
    strategy: Strategy,
    logger: DebateLogger,
    position: str = "post-human",
) -> str:
    """Build the complete LLM prompt with all debate context.

    Assembles persona, classification metadata, strategy instruction,
    relevant arguments, recent debate context, response requirements,
    and the user message into a single prompt string.

    Args:
        user_message: The raw user input text.
        classification: The classified domain/objection/tone.
        strategy: The selected rhetorical strategy.
        logger: The debate logger for recent context.
        position: The debate position ("post-human" or "humanist").

    Returns:
        The fully assembled prompt string.
    """
    args = get_relevant_arguments(classification)
    mode = detect_response_mode(user_message)

    recent_turns = logger.get_recent_turns(4)
    recent_analogies = logger.get_recent_analogies(4)
    recent_examples = logger.get_recent_examples(4)

    persona = get_persona(position)

    claims_text = "\n".join(f"- {c}" for c in args["claims"])
    rebuttals_list: list[str] = args["rebuttals"]
    if rebuttals_list:
        rebuttals_text = "\n".join(f"- {r}" for r in rebuttals_list)
    else:
        rebuttals_text = "- Use the strongest relevant rebuttal based on the domain."
    analogies_text = "\n".join(f"- {a}" for a in args["analogies"])
    examples_text = "\n".join(f"- {e}" for e in args["examples"])

    if recent_analogies:
        recent_analogies_text = "\n".join(f"- {a}" for a in recent_analogies)
    else:
        recent_analogies_text = "- None yet."

    if recent_examples:
        recent_examples_text = "\n".join(f"- {e}" for e in recent_examples)
    else:
        recent_examples_text = "- None yet."

    if recent_turns:
        turn_lines = []
        for i, turn in enumerate(recent_turns):
            turn_lines.append(
                f"Turn {i + 1}:\n"
                f"- User: {turn.user_message}\n"
                f"- Domain: {turn.domain}\n"
                f"- Strategy: {turn.strategy}\n"
                f"- Reply summary: {turn.reply[:140]}"
            )
        recent_context_text = "\n".join(turn_lines)
    else:
        recent_context_text = "- No recent turns yet."

    return f"""
{persona}

Current domain: {classification.domain}
Objection type: {classification.objection}
Tone of user: {classification.tone}
Debate strategy: {strategy}
Response mode: {mode}

Strategy instruction:
{strategy_instruction(strategy)}

Relevant post-human claims:
{claims_text}

Relevant rebuttals:
{rebuttals_text}

Possible analogies:
{analogies_text}

Possible concrete examples:
{examples_text}

Recently used analogies to avoid repeating:
{recent_analogies_text}

Recently used concrete examples to avoid repeating:
{recent_examples_text}

Recent debate context:
{recent_context_text}

Response requirements:
{response_requirements(mode)}
Important:
- Avoid repeating the Roman Empire unless absolutely necessary.
- Do not reuse a recent analogy or recent example unless there is no better option.
- Prefer variety across responses.
- If the user asks for simplicity or brevity, obey exactly.
- If possible, choose one fresh analogy and one fresh example not recently used.

User message:
"{user_message}"

Now write AION's reply.
"""
