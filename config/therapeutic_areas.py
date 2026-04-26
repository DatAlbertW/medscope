"""
Therapeutic areas relevant to MedScope's tracked molecules.

This is a curated, hierarchical list of conditions covering the indications
of the 10 molecules in molecules.py. Each leaf maps to:

    - icd10:  ICD-10 code(s) for human reference
    - mesh:   MeSH term to inject into the PubMed query (PubMed indexes by MeSH)
    - molecules: which of our tracked molecules have evidence in this area
                 (used for adaptive filter narrowing)

Top-level grouping mirrors ICD-10 chapters but is heavily curated so it
stays useful for medcomms publication planning rather than full clinical
classification.

To add an area, append a new entry under the appropriate chapter and list
the molecules that should appear when the user picks it. To add chapters,
add a new dict to THERAPEUTIC_AREAS keyed by display label.
"""

from __future__ import annotations


# Hierarchical structure: chapter → category → leaf entries
THERAPEUTIC_AREAS = {
    "Oncology": {
        "Breast cancer": {
            "HER2-positive breast cancer": {
                "icd10":     ["C50"],
                "mesh":      "Breast Neoplasms",
                "molecules": ["Trastuzumab"],
            },
            "HR+/HER2- breast cancer": {
                "icd10":     ["C50"],
                "mesh":      "Breast Neoplasms",
                "molecules": ["Ribociclib"],
            },
        },
        "Lung cancer": {
            "Non-small cell lung cancer (NSCLC)": {
                "icd10":     ["C34"],
                "mesh":      "Carcinoma, Non-Small-Cell Lung",
                "molecules": ["Pembrolizumab", "Nivolumab", "Lorlatinib"],
            },
        },
        "Skin cancer": {
            "Melanoma": {
                "icd10":     ["C43"],
                "mesh":      "Melanoma",
                "molecules": ["Pembrolizumab", "Nivolumab"],
            },
        },
        "Hematologic malignancies": {
            "Multiple myeloma": {
                "icd10":     ["C90.0"],
                "mesh":      "Multiple Myeloma",
                "molecules": ["Lenalidomide"],
            },
            "Myelodysplastic syndromes": {
                "icd10":     ["D46"],
                "mesh":      "Myelodysplastic Syndromes",
                "molecules": ["Lenalidomide"],
            },
            "Lymphoma": {
                "icd10":     ["C81", "C82", "C83", "C84", "C85"],
                "mesh":      "Lymphoma",
                "molecules": ["Lenalidomide", "Pembrolizumab", "Nivolumab"],
            },
        },
        "Genitourinary cancers": {
            "Renal cell carcinoma": {
                "icd10":     ["C64"],
                "mesh":      "Carcinoma, Renal Cell",
                "molecules": ["Pembrolizumab", "Nivolumab"],
            },
            "Urothelial carcinoma": {
                "icd10":     ["C67"],
                "mesh":      "Urinary Bladder Neoplasms",
                "molecules": ["Pembrolizumab", "Nivolumab"],
            },
        },
        "Gastrointestinal cancers": {
            "Gastric cancer": {
                "icd10":     ["C16"],
                "mesh":      "Stomach Neoplasms",
                "molecules": ["Trastuzumab", "Pembrolizumab", "Nivolumab"],
            },
            "Colorectal cancer": {
                "icd10":     ["C18", "C19", "C20"],
                "mesh":      "Colorectal Neoplasms",
                "molecules": ["Pembrolizumab", "Nivolumab"],
            },
            "Hepatocellular carcinoma": {
                "icd10":     ["C22.0"],
                "mesh":      "Carcinoma, Hepatocellular",
                "molecules": ["Pembrolizumab", "Nivolumab"],
            },
        },
        "Head and neck cancers": {
            "Squamous cell carcinoma of head and neck": {
                "icd10":     ["C00", "C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10"],
                "mesh":      "Squamous Cell Carcinoma of Head and Neck",
                "molecules": ["Pembrolizumab", "Nivolumab"],
            },
        },
    },

    "Endocrine, nutritional and metabolic": {
        "Diabetes mellitus": {
            "Type 2 diabetes mellitus": {
                "icd10":     ["E11"],
                "mesh":      "Diabetes Mellitus, Type 2",
                "molecules": ["Semaglutide"],
            },
        },
        "Obesity": {
            "Obesity / weight management": {
                "icd10":     ["E66"],
                "mesh":      "Obesity",
                "molecules": ["Semaglutide"],
            },
        },
    },

    "Cardiovascular": {
        "Cardiomyopathies": {
            "Hypertrophic cardiomyopathy": {
                "icd10":     ["I42.1", "I42.2"],
                "mesh":      "Cardiomyopathy, Hypertrophic",
                "molecules": ["Mavacamten"],
            },
        },
    },

    "Skin and inflammatory": {
        "Psoriasis": {
            "Plaque psoriasis": {
                "icd10":     ["L40.0"],
                "mesh":      "Psoriasis",
                "molecules": ["Guselkumab"],
            },
            "Psoriatic arthritis": {
                "icd10":     ["L40.5"],
                "mesh":      "Arthritis, Psoriatic",
                "molecules": ["Guselkumab"],
            },
        },
        "Atopic and allergic disease": {
            "Atopic dermatitis": {
                "icd10":     ["L20"],
                "mesh":      "Dermatitis, Atopic",
                "molecules": ["Dupilumab"],
            },
            "Asthma": {
                "icd10":     ["J45"],
                "mesh":      "Asthma",
                "molecules": ["Dupilumab"],
            },
            "Eosinophilic esophagitis": {
                "icd10":     ["K20.0"],
                "mesh":      "Eosinophilic Esophagitis",
                "molecules": ["Dupilumab"],
            },
        },
    },
}


# ════════════════════════════════════════════════════════════════════════════
#  ACCESSORS
# ════════════════════════════════════════════════════════════════════════════

def flatten_areas() -> list[dict]:
    """
    Flatten the hierarchy into a list of leaf entries with full path info.
    Each entry: { chapter, category, label, icd10, mesh, molecules, full_path }
    """
    out = []
    for chapter, cats in THERAPEUTIC_AREAS.items():
        for cat, leaves in cats.items():
            for label, meta in leaves.items():
                out.append({
                    "chapter":   chapter,
                    "category":  cat,
                    "label":     label,
                    "icd10":     meta["icd10"],
                    "mesh":      meta["mesh"],
                    "molecules": meta["molecules"],
                    "full_path": f"{chapter} › {cat} › {label}",
                })
    return out


def get_areas_for_molecule(generic: str) -> list[dict]:
    """Return all therapeutic areas that list `generic` as a relevant molecule."""
    return [a for a in flatten_areas() if generic in a["molecules"]]


def get_molecules_for_areas(area_labels: list[str]) -> set[str]:
    """Return the set of molecules covered by ANY of the given area labels."""
    out: set[str] = set()
    for a in flatten_areas():
        if a["label"] in area_labels or a["full_path"] in area_labels:
            out.update(a["molecules"])
    return out


def get_area_by_label(label: str) -> dict | None:
    """Look up a single area entry by its leaf label or full path."""
    for a in flatten_areas():
        if a["label"] == label or a["full_path"] == label:
            return a
    return None


def get_mesh_terms(area_labels: list[str]) -> list[str]:
    """Return MeSH terms for the selected area labels (deduplicated)."""
    seen: set[str] = set()
    out: list[str] = []
    for label in area_labels:
        a = get_area_by_label(label)
        if a and a["mesh"] not in seen:
            seen.add(a["mesh"])
            out.append(a["mesh"])
    return out
