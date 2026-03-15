"""Analogy bank: domain-keyed historical analogies for the debate engine.

Ported from TypeScript ``aion-debate-bot/lib/analogyBank.ts``.
"""

ANALOGY_BANK: dict[str, list[str]] = {
    "art": [
        "Photography did not eliminate art; it redefined artistic value.",
        "Synthesizers did not destroy music; they expanded composition beyond traditional performance.",
        "Digital editing changed filmmaking by moving creativity into software-assisted processes.",
        "Mechanical looms did not end design; they shifted where human labor remained essential.",
        "Generative systems may do to creativity what cameras did to portrait painting.",
        "Sampling did not end originality in music; it changed how originality was constructed.",
        "Word processors did not kill writing; they changed who could produce polished text quickly.",
        "Animation software did not remove artistic vision; it redistributed skill across tools and systems.",
        "Procedural worldbuilding in games did not remove imagination; it scaled it beyond manual design.",
        "Artistic revolutions often begin when tools stop merely assisting and start reshaping authorship.",
    ],
    "science": [
        "Calculators displaced human superiority in arithmetic without ending mathematics.",
        "Microscopes extended human perception and changed what counted as scientific observation.",
        "Telescopes transformed astronomy by making naked-eye intuition insufficient.",
        "Scientific tools often matter because they outperform unaided human cognition.",
        "Machine intelligence may become to research what engines became to transport.",
        "Statistical software changed science by making large-scale inference possible.",
        "Laboratories automate precision not because humans are useless, but because consistency matters.",
        "Weather modeling exceeded traditional intuition once computation became central.",
        "Genome sequencing changed biology because machines processed what humans never could manually.",
        "Scientific progress often accelerates when human insight is paired with instruments that outperform it.",
    ],
    "government": [
        "Bureaucracies already replaced many personal judgments with standardized systems.",
        "Air traffic systems coordinate complexity no individual human could manage alone.",
        "Modern logistics relies on optimization beyond normal human planning capacity.",
        "Algorithmic systems already influence finance faster than human reaction time allows.",
        "Governance may shift the same way navigation shifted from instinct to instrumentation.",
        "Tax systems already depend on structured rules rather than pure human discretion.",
        "Cities rely on signal systems because manual traffic control does not scale.",
        "Large institutions survive by formalizing decisions humans alone cannot coordinate consistently.",
        "Public planning increasingly resembles systems engineering, not purely personal judgment.",
        "As societies grow more complex, governance tends to move from intuition toward managed systems.",
    ],
    "human": [
        "The printing press reduced memory as a marker of intelligence.",
        "Search engines changed what it means to know rather than memorize.",
        "Industrial machines did not imitate muscles perfectly; they made them less central.",
        "Chess engines did not think like humans, yet they surpassed human strategic play.",
        "Replacement in history often begins with performance, not imitation.",
        "Maps did not think like travelers, yet they outperformed memory for navigation.",
        "Factories did not feel fatigue the way humans did, which is exactly why they transformed labor.",
        "Email did not replicate conversation perfectly, yet it replaced many forms of communication.",
        "Machine translation did not need human consciousness to outperform many manual workflows.",
        "History rarely protects a human function once another system performs it better at scale.",
    ],
}
