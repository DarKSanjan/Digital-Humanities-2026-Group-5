"""Example bank: domain-keyed concrete examples for the debate engine.

Ported from TypeScript ``aion-debate-bot/lib/exampleBank.ts``.
"""

EXAMPLE_BANK: dict[str, list[str]] = {
    "art": [
        "AI image generation systems can produce novel visual outputs in seconds.",
        "Algorithmic music tools can compose in multiple styles at scale.",
        "Interactive narrative systems can personalize storytelling for different audiences.",
        "Procedural content generation already shapes game design and digital worlds.",
        "Creative workflows increasingly combine human direction with machine generation.",
        "Design tools now generate logo and layout variations far faster than manual iteration alone.",
        "Recommendation-driven media systems increasingly shape what audiences encounter as culture.",
        "Text generation systems can draft scripts, poems, concepts, and dialogue at scale.",
        "Video generation tools increasingly compress production time for visual storytelling.",
        "Creative industries already use software not just to assist expression, but to shape it.",
    ],
    "science": [
        "Machine learning systems have accelerated protein structure prediction.",
        "AI-assisted drug discovery helps search huge molecular spaces faster than humans can.",
        "Scientific simulation can evaluate more scenarios than any individual researcher could track manually.",
        "Pattern discovery in large datasets increasingly depends on machine-scale computation.",
        "Automated theorem exploration suggests that machine reasoning may become central in research.",
        "Astronomy increasingly depends on software to detect patterns in massive streams of data.",
        "Climate modeling relies on computational systems beyond ordinary human reasoning capacity.",
        "Materials discovery increasingly uses machine search across candidate structures.",
        "Automated lab systems improve consistency and throughput in experimental workflows.",
        "Large-scale scientific progress is increasingly shaped by systems that process beyond human limits.",
    ],
    "government": [
        "Traffic optimization systems already improve routing better than ad hoc human control.",
        "Fraud detection systems analyze patterns at scales impossible for manual review.",
        "Resource allocation models can simulate trade-offs across large populations.",
        "Predictive maintenance systems help cities manage infrastructure more systematically.",
        "Administrative decisions are increasingly shaped by data systems rather than intuition alone.",
        "Hospitals use triage support systems because human judgment under pressure is inconsistent.",
        "Public transport scheduling increasingly depends on optimization software.",
        "Risk scoring systems already influence institutional decisions in finance and operations.",
        "Emergency planning uses simulation because unaided human foresight is too limited.",
        "Governance is already partly machine-mediated whenever complexity exceeds direct human coordination.",
    ],
    "human": [
        "Chess engines surpassed human champions without reproducing human thought exactly.",
        "Recommendation systems already shape culture at superhuman scale.",
        "Medical support models can flag patterns a tired human may miss.",
        "Industrial automation removed many tasks once thought inseparable from human skill.",
        "Machine systems do not need human-like consciousness to outperform human functions.",
        "Search engines changed daily cognition by externalizing memory and retrieval.",
        "Autocorrect and language tools already alter how people write and communicate.",
        "Autonomous systems increasingly perform monitoring tasks humans struggle to do continuously.",
        "Humans often trust instruments precisely because instruments reduce human inconsistency.",
        "Many human strengths become less central once systems scale accuracy, speed, and memory.",
    ],
}
