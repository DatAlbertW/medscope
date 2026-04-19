"""
All LLM prompts used by MedScope.

Every prompt the app sends to the LLM lives here. Edit these to change
behavior without touching engine code.

Design principles:
    - Every prompt demands STRICT JSON output
    - System message enforces JSON-only responses
    - Prompts are parametrised via .format() with named placeholders
"""

# ════════════════════════════════════════════════════════════════════════════
#  SYSTEM MESSAGES
# ════════════════════════════════════════════════════════════════════════════

SYSTEM_CLASSIFIER = (
    "You are a systematic review expert and medical affairs specialist. "
    "You ALWAYS respond with a single valid JSON object and nothing else. "
    "No markdown fences, no prose, no text outside the JSON."
)

SYSTEM_EXTRACTOR = (
    "You are a clinical research data extractor. "
    "You ALWAYS respond with a single valid JSON object and nothing else. "
    "If a field cannot be determined from the text, return null for that field. "
    "Do NOT invent data."
)


# ════════════════════════════════════════════════════════════════════════════
#  CLASSIFICATION PROMPT
# ════════════════════════════════════════════════════════════════════════════
# Classifies a paper into ONE of the 4 categories (or excludes it).
# Placeholders: {molecule}, {title}, {abstract}, {categories_block}

CLASSIFY_PROMPT = """Classify the following paper for a medical affairs literature review on the molecule: {molecule}.

Title: {title}

Abstract: {abstract}

Pick the SINGLE best category from this list, or EXCLUDE the paper if it is
animal-only, in-vitro only, irrelevant to {molecule}, or not about human use:

{categories_block}

Return ONLY valid JSON:
{{
  "decision": "INCLUDE" | "EXCLUDE",
  "category": "clinically_relevant" | "safety_efficacy" | "trial_results" | "real_world_evidence" | null,
  "confidence": 0.0-1.0,
  "study_type": "RCT | Observational | Review | Meta-analysis | Case report | Preclinical | Other",
  "key_finding": "one-sentence finding in 15 words max",
  "reasoning": "one short sentence justifying the decision"
}}"""


# ════════════════════════════════════════════════════════════════════════════
#  GEOGRAPHY EXTRACTION PROMPT (for RWE tab)
# ════════════════════════════════════════════════════════════════════════════
# Extracts country AND state/region from author affiliations and abstract.
# Placeholders: {title}, {abstract}, {affiliations}

EXTRACT_GEOGRAPHY_PROMPT = """Extract the geographic origin of this real-world evidence study.

Title: {title}
Abstract: {abstract}
Author affiliations: {affiliations}

Identify:
- The primary country where the study was conducted
- The state, region, province, or city (when clearly stated)
- The approximate patient cohort size (if mentioned)

Return ONLY valid JSON:
{{
  "country": "country name in English, or null",
  "country_iso2": "ISO 3166-1 alpha-2 code, or null",
  "region": "state/province/region name, or null",
  "city": "city name if clearly stated, or null",
  "cohort_size": integer or null,
  "is_multicentric": true or false
}}"""


# ════════════════════════════════════════════════════════════════════════════
#  STUDY TYPE EXTRACTION PROMPT (for Trial Results tab)
# ════════════════════════════════════════════════════════════════════════════
# Extracts structured trial metadata for the Trial Results view.
# Placeholders: {title}, {abstract}

EXTRACT_TRIAL_METADATA_PROMPT = """Extract structured clinical trial metadata from this paper.

Title: {title}
Abstract: {abstract}

Return ONLY valid JSON:
{{
  "phase": "Phase 1" | "Phase 2" | "Phase 3" | "Phase 4" | "Not specified",
  "nct_id": "NCT id if present, or null",
  "primary_endpoint": "primary endpoint in <12 words, or null",
  "primary_result": "primary result in <20 words, or null",
  "n_enrolled": integer or null,
  "comparator": "comparator arm in <8 words, or null"
}}"""


# ════════════════════════════════════════════════════════════════════════════
#  SAFETY SIGNAL EXTRACTION PROMPT (for Safety & Efficacy tab)
# ════════════════════════════════════════════════════════════════════════════
# Pulls key safety signals from papers classified as Safety & Efficacy.
# Placeholders: {title}, {abstract}

EXTRACT_SAFETY_PROMPT = """Extract key safety and efficacy signals from this paper.

Title: {title}
Abstract: {abstract}

Return ONLY valid JSON:
{{
  "most_common_aes": ["up to 3 most common adverse events, each <5 words"],
  "serious_aes_mentioned": true or false,
  "discontinuation_rate": "percent as string like '7.5%' or null",
  "efficacy_signal": "one-sentence efficacy takeaway <20 words, or null"
}}"""
