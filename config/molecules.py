"""
Tracked molecules for MedScope.

Each entry contains:
    generic:  generic (INN) name — ALWAYS used as the PubMed search term
    brands:   commercial brand names (for fuzzy matching on user input)
    synonyms: additional aliases, research codes, common misspellings
    drug_class: high-level therapeutic class (for dashboard grouping)
    indication_hint: short description of primary indication(s)

The generic name is the canonical identifier. User input
("Herceptin", "trastuzomab" typo, etc.) is resolved to the generic
before hitting PubMed.

To add a molecule, copy one of the entries below and edit it.
"""

MOLECULES = [
    {
        "generic": "Guselkumab",
        "brands": ["Tremfya"],
        "synonyms": ["CNTO 1959", "anti-IL-23"],
        "drug_class": "Monoclonal antibody (IL-23 inhibitor)",
        "indication_hint": "Plaque psoriasis, psoriatic arthritis",
    },
    {
        "generic": "Dupilumab",
        "brands": ["Dupixent"],
        "synonyms": ["REGN668", "SAR231893", "anti-IL-4Ra"],
        "drug_class": "Monoclonal antibody (IL-4Rα antagonist)",
        "indication_hint": "Atopic dermatitis, asthma, eosinophilic esophagitis",
    },
    {
        "generic": "Pembrolizumab",
        "brands": ["Keytruda"],
        "synonyms": ["MK-3475", "lambrolizumab", "anti-PD-1"],
        "drug_class": "Immune checkpoint inhibitor (PD-1)",
        "indication_hint": "Multiple oncology indications",
    },
    {
        "generic": "Trastuzumab",
        "brands": ["Herceptin", "Ogivri", "Kanjinti", "Trazimera", "Ontruzant"],
        "synonyms": ["anti-HER2", "rhuMAb HER2"],
        "drug_class": "Monoclonal antibody (HER2 inhibitor)",
        "indication_hint": "HER2-positive breast cancer, gastric cancer",
    },
    {
        "generic": "Mavacamten",
        "brands": ["Camzyos"],
        "synonyms": ["MYK-461"],
        "drug_class": "Cardiac myosin inhibitor",
        "indication_hint": "Obstructive hypertrophic cardiomyopathy",
    },
    {
        "generic": "Ribociclib",
        "brands": ["Kisqali"],
        "synonyms": ["LEE011"],
        "drug_class": "CDK4/6 inhibitor",
        "indication_hint": "HR+/HER2- breast cancer",
    },
    {
        "generic": "Nivolumab",
        "brands": ["Opdivo"],
        "synonyms": ["BMS-936558", "MDX-1106", "ONO-4538", "anti-PD-1"],
        "drug_class": "Immune checkpoint inhibitor (PD-1)",
        "indication_hint": "Multiple oncology indications",
    },
    {
        "generic": "Lorlatinib",
        "brands": ["Lorbrena", "Lorviqua"],
        "synonyms": ["PF-06463922"],
        "drug_class": "ALK/ROS1 tyrosine kinase inhibitor",
        "indication_hint": "ALK-positive non-small cell lung cancer",
    },
    {
        "generic": "Semaglutide",
        "brands": ["Ozempic", "Wegovy", "Rybelsus"],
        "synonyms": ["NN9535"],
        "drug_class": "GLP-1 receptor agonist",
        "indication_hint": "Type 2 diabetes, obesity/weight management",
    },
    {
        "generic": "Lenalidomide",
        "brands": ["Revlimid"],
        "synonyms": ["CC-5013"],
        "drug_class": "Immunomodulatory drug (IMiD)",
        "indication_hint": "Multiple myeloma, MDS, certain lymphomas",
    },
]


def get_all_generics() -> list[str]:
    """Return list of all generic names (canonical identifiers)."""
    return [m["generic"] for m in MOLECULES]


def get_all_search_terms() -> list[tuple[str, str]]:
    """
    Return (display_term, canonical_generic) pairs used for fuzzy matching.
    Includes generics, brands, and synonyms.
    """
    terms = []
    for m in MOLECULES:
        generic = m["generic"]
        terms.append((generic, generic))
        for brand in m.get("brands", []):
            terms.append((brand, generic))
        for syn in m.get("synonyms", []):
            terms.append((syn, generic))
    return terms


def get_molecule(generic: str) -> dict | None:
    """Lookup a molecule entry by its generic name (case-insensitive)."""
    for m in MOLECULES:
        if m["generic"].lower() == generic.lower():
            return m
    return None
