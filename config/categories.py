"""
Classification categories for MedScope.

Each paper retrieved from PubMed is classified by the LLM into ONE of these
four categories (David's request). Papers may also be excluded entirely if
they fail the exclusion criteria (e.g. animal-only studies).

To tune classification behavior, adjust:
    - `description`: the definition the LLM uses to decide the category
    - `include_keywords`: terms that bias classification toward this category
    - `exclude_keywords`: terms that disqualify a paper from this category

Changes here immediately affect how new searches are classified.
"""

CATEGORIES = {
    "clinically_relevant": {
        "label": "Clinically Relevant Articles",
        "icon": "📖",
        "description": (
            "Papers discussing the molecule in a clinical context: human patient use, "
            "clinical guidelines, mechanism of action in humans, indication reviews, "
            "or positioning within standard of care. Excludes purely preclinical, "
            "in vitro, or animal-only studies."
        ),
        "include_keywords": [
            "clinical", "patient", "treatment", "therapy", "indication",
            "guideline", "recommendation", "standard of care",
        ],
        "exclude_keywords": [
            "mouse", "mice", "rat", "zebrafish", "in vitro",
            "cell line", "animal model", "preclinical",
        ],
    },

    "safety_efficacy": {
        "label": "Safety & Efficacy",
        "icon": "⚖️",
        "description": (
            "Papers specifically reporting on safety profile, adverse events, "
            "tolerability, pharmacovigilance findings, or efficacy endpoints "
            "(ORR, PFS, OS, HbA1c change, etc.) in humans."
        ),
        "include_keywords": [
            "safety", "adverse event", "tolerability", "efficacy",
            "pharmacovigilance", "side effect", "endpoint",
            "overall survival", "progression-free", "response rate",
        ],
        "exclude_keywords": [
            "in vitro", "cell line", "animal model",
        ],
    },

    "trial_results": {
        "label": "Trial Results",
        "icon": "🧪",
        "description": (
            "Papers reporting results from interventional clinical trials "
            "(Phase 1, 2, 3, or 4) with primary or secondary outcome data "
            "on the molecule. Includes RCTs, single-arm trials, and follow-up analyses."
        ),
        "include_keywords": [
            "randomized", "randomised", "phase", "trial",
            "double-blind", "placebo-controlled", "results",
            "primary endpoint", "NCT",
        ],
        "exclude_keywords": [
            "protocol only", "design paper", "rationale",
        ],
    },

    "real_world_evidence": {
        "label": "Real-World Evidence",
        "icon": "🌍",
        "description": (
            "Observational studies, registry analyses, real-world data, "
            "retrospective cohorts, post-marketing surveillance, pharmacoepidemiology, "
            "or single-center/regional experience with the molecule in routine practice."
        ),
        "include_keywords": [
            "real-world", "real world", "observational", "registry",
            "retrospective", "cohort", "post-marketing", "post marketing",
            "pharmacoepidemiology", "routine practice", "claims data",
            "electronic health record",
        ],
        "exclude_keywords": [
            "randomized controlled trial only", "phase 1 trial only",
        ],
    },
}


# Exclusion rules applied BEFORE categorisation.
# If a paper matches any of these, it is dropped entirely.
GLOBAL_EXCLUSIONS = {
    "animal_only_markers": [
        "mouse model", "murine model", "rat model",
        "zebrafish", "xenograft only",
    ],
    "in_vitro_only_markers": [
        "in vitro study", "cell culture only",
    ],
}


def get_category_ids() -> list[str]:
    """Return list of category IDs (e.g. 'clinically_relevant')."""
    return list(CATEGORIES.keys())


def get_category_label(category_id: str) -> str:
    """Return the user-facing label for a category."""
    return CATEGORIES.get(category_id, {}).get("label", category_id)
