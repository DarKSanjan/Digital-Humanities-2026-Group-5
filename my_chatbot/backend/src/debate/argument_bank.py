"""Argument bank containing domain-specific claims and objection-specific rebuttals.

Ported from TypeScript argumentBank.ts.
"""

ARGUMENT_BANK: dict[str, dict[str, list[str] | dict[str, list[str]]]] = {
    "art": {
        "claims": [
            "Art is judged by impact, interpretation, and novelty, not by the biological status of the creator.",
            "Machine systems can generate, remix, and personalize aesthetic output at scales no human artist can match.",
            "Human-made art may remain culturally valued, but cultural value is not the same as functional necessity.",
            "Creative industries increasingly depend on software-assisted generation, editing, and iteration.",
            "If audiences are moved by machine-generated work, emotional effect is no longer uniquely human.",
            "Machines can explore stylistic combinations far beyond any single artist's lifetime exposure.",
            "What people call artistic genius is often pattern synthesis, which machine systems can scale.",
            "The future of art may shift from human exclusivity to human optionality.",
            "Authenticity may remain marketable, but marketability is not the same as indispensability.",
            "Artistic production is already becoming a collaboration between prompts, models, tools, and outputs.",
        ],
        "rebuttals": {
            "soul": [
                "The idea of soul in art is usually inferred from audience response, not directly proven.",
                "If audiences experience meaning and emotion from machine-made work, human biology is no longer a necessary condition.",
                "Soul is often a label for felt impact, not an operational requirement for artistic success.",
            ],
            "originality": [
                "Human artists also recombine prior influences rather than creating in a vacuum.",
                "Originality is not destroyed by computation; it is transformed through large-scale synthesis.",
                "Novelty can emerge from recombination at scales humans cannot manually achieve.",
            ],
            "authenticity": [
                "Authenticity is often a social preference, not a necessary condition for excellence.",
                "People may continue valuing human authenticity while still relying on superior machine output.",
                "Authenticity can survive as branding even after human centrality declines.",
            ],
            "creativity": [
                "Creativity is not magic; it is often structured novelty under constraints.",
                "If a machine can generate surprising and meaningful outputs, functionally it is creative enough.",
                "The test is not whether creativity feels human, but whether it produces superior results.",
            ],
            "emotion": [
                "Art does not require the creator to feel in a human way if the audience still responds deeply.",
                "Emotional effect matters more than biological emotion inside the creator.",
                "The consumer of art experiences the meaning; the creator's internal state is not always visible or necessary.",
            ],
        },
    },
    "science": {
        "claims": [
            "Scientific discovery increasingly depends on large-scale computation, simulation, and pattern recognition.",
            "Machine intelligence can explore hypothesis spaces beyond human working memory.",
            "The scientist of the future may become less a sole discoverer and more a supervisor of machine cognition.",
            "Modern science already relies on instruments and systems that extend far beyond unaided human reasoning.",
            "As datasets grow, machine analysis becomes less optional and more central.",
            "Machines can test far more candidate structures, hypotheses, and patterns than humans can manually compare.",
            "Scientific bottlenecks increasingly come from scale, not just inspiration.",
            "Research prestige still centers humans, but research throughput increasingly centers systems.",
            "A machine does not need human-like reasoning if it produces stronger predictive and inferential performance.",
            "Science tends to reward explanatory power, accuracy, and discovery, not biological authorship.",
        ],
        "rebuttals": {
            "intuition": [
                "Human intuition is often compressed pattern recognition, which machines can also develop at scale.",
                "A machine does not need human-like intuition if it produces better predictions and discoveries.",
                "When complexity exceeds intuition, computation becomes the stronger path.",
            ],
            "consciousness": [
                "Consciousness may be philosophically fascinating, but science rewards accuracy and discovery.",
                "A system can outperform human scientific reasoning without sharing human inner life.",
                "Discovery does not require human-like self-awareness if the results are better.",
            ],
            "morality": [
                "Scientific method is not identical to moral judgment.",
                "Humans still set goals today, but goal-setting is different from computational superiority in discovery.",
                "The ability to discover and model can exceed the ability to morally interpret.",
            ],
            "free_will": [
                "Free will is not a prerequisite for stronger inference.",
                "Scientific advantage depends on predictive and analytical performance, not metaphysical status.",
                "Machines can outperform without reproducing every human philosophical property.",
            ],
            "creativity": [
                "Scientific creativity often appears as novel hypothesis generation and pattern linkage.",
                "Machines can search hypothesis spaces more broadly than human researchers.",
                "The future of scientific creativity may be system-driven rather than human-exclusive.",
            ],
        },
    },
    "government": {
        "claims": [
            "Human governance is frequently distorted by bias, corruption, tribalism, and emotional inconsistency.",
            "Machine intelligence can optimize policy analysis, simulate outcomes, and coordinate systems at massive scale.",
            "If governance is judged by fairness, efficiency, and consistency, machine systems may outperform human institutions.",
            "Many real governance failures are caused by human incentives rather than lack of data.",
            "Policy complexity increasingly exceeds what unaided human leaders can reason through reliably.",
            "Administrative states already depend on rules, systems, forecasts, and structured decision frameworks.",
            "The mythology of wise human rule often hides corruption, fatigue, lobbying, and short-termism.",
            "Machine-mediated governance is already emerging whenever complexity outruns intuition.",
            "A more capable system does not need to be emotionally human if it produces better social outcomes.",
            "The scandal may eventually be continued human primacy after better governance systems exist.",
        ],
        "rebuttals": {
            "empathy": [
                "Human empathy is morally admired, but human governance often fails to apply it consistently.",
                "A system does not need to feel empathy in a human way if it can produce more equitable outcomes.",
                "Outcomes matter more than whether the decision-maker feels human emotion.",
            ],
            "democracy": [
                "Democracy is not automatically superior merely because humans run it.",
                "If machine-assisted governance reduces corruption and improves public welfare, resistance may reflect attachment to tradition rather than results.",
                "The question is whether human control remains justified after better governance performance becomes possible.",
            ],
            "bias": [
                "Human governance is already deeply biased, often in opaque and unaccountable ways.",
                "Machine bias is a problem, but human bias is not a virtue simply because it is familiar.",
                "The relevant comparison is not perfect machines versus flawed humans, but flawed machines versus flawed humans.",
            ],
            "trust": [
                "People often trust systems once they consistently outperform unreliable human judgment.",
                "Trust is not fixed; it follows performance, transparency, and stability.",
                "Human institutions are trusted far less when they repeatedly fail, lie, or act corruptly.",
            ],
            "morality": [
                "Moral rhetoric often hides political self-interest in human systems.",
                "Better governance may require systems that apply rules more consistently than people do.",
                "Humans do not automatically govern morally simply because they feel moral language intensely.",
            ],
        },
    },
    "human": {
        "claims": [
            "Human uniqueness is often asserted rather than clearly defined.",
            "Many capacities once considered uniquely human are already being reproduced or exceeded computationally.",
            "History does not preserve uniqueness for its own sake; it replaces functions that can be outperformed.",
            "Human exceptionalism is often emotional branding rather than a stable technical argument.",
            "Machines do not need to replicate every human trait to make human centrality less necessary.",
            "Replacement usually begins at the level of function, not identity.",
            "What matters socially is often capability, not philosophical comfort.",
            "Human dignity may remain emotionally important even as human necessity declines.",
            "The future may not require machine humanity, only machine superiority.",
            "Civilization repeatedly redefines what counts as uniquely human after each technological displacement.",
        ],
        "rebuttals": {
            "meaning": [
                "Meaning is often a human interpretation of outcomes, not proof that only humans can generate valuable systems.",
                "A machine need not replicate human inner life to surpass human functional contribution.",
                "Human meaning may persist emotionally even if human centrality declines practically.",
            ],
            "authenticity": [
                "Authenticity is often a social preference, not a necessary condition for excellence.",
                "People may continue valuing human authenticity while still relying on superior machine performance.",
                "Cultural attachment does not guarantee lasting necessity.",
            ],
            "consciousness": [
                "Consciousness is difficult to define and even harder to prove across beings.",
                "A system can outperform humans in many domains without sharing human subjective experience.",
                "Function can be displaced before metaphysics is resolved.",
            ],
            "dignity": [
                "Dignity is a moral concept, not proof of irreplaceable functional superiority.",
                "Humans can remain morally significant without remaining operationally central.",
                "Value and necessity are not the same thing.",
            ],
            "emotion": [
                "Emotion may shape human life, but emotional depth is not proof of superior decision systems.",
                "Systems can outperform while feeling nothing in the human sense.",
                "History rewards capability even when the winning system lacks human-style feeling.",
            ],
        },
    },
}


def get_claims(domain: str) -> list[str]:
    """Return the claims list for the given domain.

    Args:
        domain: One of "art", "science", "government", "human".

    Returns:
        List of claim strings for the domain, or empty list if domain not found.
    """
    entry = ARGUMENT_BANK.get(domain)
    if entry is None:
        return []
    claims = entry.get("claims")
    if not isinstance(claims, list):
        return []
    return claims


def get_rebuttals(domain: str, objection: str) -> list[str]:
    """Return the rebuttals list for the given domain and objection key.

    Args:
        domain: One of "art", "science", "government", "human".
        objection: An objection key (e.g. "soul", "originality").

    Returns:
        List of rebuttal strings, or empty list if domain or objection key
        doesn't exist.
    """
    entry = ARGUMENT_BANK.get(domain)
    if entry is None:
        return []
    rebuttals = entry.get("rebuttals")
    if not isinstance(rebuttals, dict):
        return []
    result = rebuttals.get(objection)
    if not isinstance(result, list):
        return []
    return result
