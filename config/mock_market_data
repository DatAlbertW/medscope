"""
Illustrative market and sales data for the Market tab.

IMPORTANT: The values below are ILLUSTRATIVE mock data, clearly labeled
as such in the UI. They exist to demonstrate what a production integration
with IQVIA / Evaluate Pharma / Citeline would look like.

Real data sources wired up elsewhere in the app:
    - ClinicalTrials.gov (sponsors, phases, countries) — core/pubmed_client-like module
    - DrugBank open data (marketing company, approved indications)
    - FDA Orange Book / EMA (approval status)

The mock data here ONLY covers what paid sources would provide:
annual sales estimates, market share, and HCP specialty targeting mix.

To edit: update the DICT below. Each molecule key matches the `generic`
field in config/molecules.py (case-sensitive).
"""

# Clearly flagged so UI can show a "mock — illustrative only" banner
IS_ILLUSTRATIVE = True


MARKET_DATA = {
    "Guselkumab": {
        "marketing_company": "Janssen (Johnson & Johnson)",
        "est_annual_sales_usd_m": 3400,
        "growth_yoy_pct": 18,
        "hcp_targeting_mix": {
            "Dermatologist": 65,
            "Rheumatologist": 30,
            "Primary Care": 5,
        },
        "key_competitor_molecules": ["Risankizumab", "Ustekinumab", "Secukinumab"],
    },
    "Dupilumab": {
        "marketing_company": "Sanofi / Regeneron",
        "est_annual_sales_usd_m": 11900,
        "growth_yoy_pct": 22,
        "hcp_targeting_mix": {
            "Dermatologist": 45,
            "Allergist/Immunologist": 25,
            "Pulmonologist": 20,
            "Gastroenterologist": 10,
        },
        "key_competitor_molecules": ["Tralokinumab", "Lebrikizumab", "Omalizumab"],
    },
    "Pembrolizumab": {
        "marketing_company": "Merck & Co. (MSD)",
        "est_annual_sales_usd_m": 27000,
        "growth_yoy_pct": 16,
        "hcp_targeting_mix": {
            "Medical Oncologist": 80,
            "Thoracic Oncologist": 10,
            "Urologist": 5,
            "Gynecologic Oncologist": 5,
        },
        "key_competitor_molecules": ["Nivolumab", "Atezolizumab", "Cemiplimab"],
    },
    "Trastuzumab": {
        "marketing_company": "Roche (originator); multiple biosimilars",
        "est_annual_sales_usd_m": 4200,
        "growth_yoy_pct": -6,   # biosimilar erosion
        "hcp_targeting_mix": {
            "Medical Oncologist": 85,
            "Breast Surgeon": 10,
            "Gastroenterologist": 5,
        },
        "key_competitor_molecules": ["Pertuzumab", "T-DM1", "T-DXd"],
    },
    "Mavacamten": {
        "marketing_company": "Bristol Myers Squibb",
        "est_annual_sales_usd_m": 480,
        "growth_yoy_pct": 140,
        "hcp_targeting_mix": {
            "Cardiologist": 70,
            "HCM specialist centre": 25,
            "Primary Care": 5,
        },
        "key_competitor_molecules": ["Aficamten (investigational)"],
    },
    "Ribociclib": {
        "marketing_company": "Novartis",
        "est_annual_sales_usd_m": 2400,
        "growth_yoy_pct": 14,
        "hcp_targeting_mix": {
            "Medical Oncologist": 90,
            "Breast Surgeon": 10,
        },
        "key_competitor_molecules": ["Palbociclib", "Abemaciclib"],
    },
    "Nivolumab": {
        "marketing_company": "Bristol Myers Squibb",
        "est_annual_sales_usd_m": 9100,
        "growth_yoy_pct": 4,
        "hcp_targeting_mix": {
            "Medical Oncologist": 80,
            "Thoracic Oncologist": 10,
            "Urologist": 5,
            "Dermatologist (Melanoma)": 5,
        },
        "key_competitor_molecules": ["Pembrolizumab", "Atezolizumab", "Cemiplimab"],
    },
    "Lorlatinib": {
        "marketing_company": "Pfizer",
        "est_annual_sales_usd_m": 680,
        "growth_yoy_pct": 28,
        "hcp_targeting_mix": {
            "Thoracic Oncologist": 70,
            "Medical Oncologist": 25,
            "Pulmonologist": 5,
        },
        "key_competitor_molecules": ["Alectinib", "Brigatinib", "Ceritinib"],
    },
    "Semaglutide": {
        "marketing_company": "Novo Nordisk",
        "est_annual_sales_usd_m": 25600,
        "growth_yoy_pct": 55,
        "hcp_targeting_mix": {
            "Endocrinologist": 35,
            "Primary Care": 40,
            "Cardiologist": 15,
            "Obesity Medicine": 10,
        },
        "key_competitor_molecules": ["Tirzepatide", "Liraglutide", "Dulaglutide"],
    },
    "Lenalidomide": {
        "marketing_company": "Bristol Myers Squibb (post-Celgene)",
        "est_annual_sales_usd_m": 6100,
        "growth_yoy_pct": -18,   # generic erosion
        "hcp_targeting_mix": {
            "Hematologist/Oncologist": 90,
            "Transplant Specialist": 10,
        },
        "key_competitor_molecules": ["Pomalidomide", "Daratumumab", "Bortezomib"],
    },
}


def get_market_data(generic: str) -> dict | None:
    """Return the market data entry for a given molecule (case-insensitive)."""
    for key, value in MARKET_DATA.items():
        if key.lower() == generic.lower():
            return value
    return None
