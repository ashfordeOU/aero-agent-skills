"""
e1006_wording_logic.py
ECSS-E-ST-10C §8.3 — requirement wording audit helpers.
stdlib only; offline; deterministic.
"""
import re

# Standard verbal forms and their requirement category.
VERBAL_FORMS = {
    "shall": "mandatory",
    "should": "recommendation",
    "may": "permission",
}

# Non-standard verbal forms that must be replaced with 'shall'.
NON_STANDARD_FORMS = {
    "is required to": "replace with 'shall'",
    "are required to": "replace with 'shall'",
    "will": "replace with 'shall' for obligations",
    "must": "replace with 'shall' for obligations",
}

# Ambiguous / unverifiable terms forbidden in requirement text per §8.3.
FORBIDDEN_TERMS = [
    "adequate",
    "and/or",
    "appropriate",
    "as required",
    "easy",
    "effective",
    "efficient",
    "etc.",
    "fast",
    "flexible",
    "friendly",
    "general",
    "generally",
    "good",
    "ideally",
    "if possible",
    "large",
    "maximize",
    "minimize",
    "minimum necessary",
    "nominal",
    "normal",
    "optimum",
    "practical",
    "reasonable",
    "robust",
    "simple",
    "small",
    "state of the art",
    "sufficient",
    "timely",
    "user-friendly",
    "when necessary",
    "where applicable",
]

# Phrases indicating embedded rationale that must be moved to a NOTE.
RATIONALE_MARKERS = [
    "in order to",
    "so that",
    "because",
    "due to",
    "to enable",
    "to ensure that",
    "to allow",
    "to prevent",
    "to avoid",
]


def detect_verbal_form(text: str) -> dict:
    """
    Identify the verbal form in a requirement string.

    Returns a dict with keys:
      form       – the matched token, or None
      category   – 'mandatory' | 'recommendation' | 'permission'
                   | 'non-standard' | 'missing'
      compliant  – True when the form is one of shall / should / may
      message    – human-readable diagnosis
    """
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    lower = text.lower()

    # Multi-word non-standard forms take priority over single-word checks.
    for phrase in ("is required to", "are required to"):
        if phrase in lower:
            return {
                "form": phrase,
                "category": "non-standard",
                "compliant": False,
                "message": (
                    f"Non-standard verbal form '{phrase}': "
                    f"{NON_STANDARD_FORMS[phrase]}"
                ),
            }

    # Single-word non-standard forms — matched as whole words to avoid
    # hitting "will" inside "willingness" etc.
    for word in ("must", "will"):
        if re.search(rf"\b{word}\b", lower):
            return {
                "form": word,
                "category": "non-standard",
                "compliant": False,
                "message": (
                    f"Non-standard verbal form '{word}': "
                    f"{NON_STANDARD_FORMS[word]}"
                ),
            }

    # Standard verbal forms — whole-word match.
    for verb, category in VERBAL_FORMS.items():
        if re.search(rf"\b{verb}\b", lower):
            return {
                "form": verb,
                "category": category,
                "compliant": True,
                "message": f"Verbal form '{verb}' is acceptable ({category})",
            }

    return {
        "form": None,
        "category": "missing",
        "compliant": False,
        "message": (
            "No recognizable verbal form found; "
            "every requirement must use shall, should, or may"
        ),
    }


def count_obligations(text: str) -> int:
    """
    Return the number of whole-word 'shall' occurrences.
    A compliant mandatory requirement has exactly one.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    return len(re.findall(r"\bshall\b", text, re.IGNORECASE))


def check_forbidden_terms(text: str) -> list:
    """
    Return the list of forbidden (ambiguous/unverifiable) terms present.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    lower = text.lower()
    return [term for term in FORBIDDEN_TERMS if term in lower]


def check_embedded_rationale(text: str) -> list:
    """
    Return the list of rationale-marker phrases present in the text.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    lower = text.lower()
    return [marker for marker in RATIONALE_MARKERS if marker in lower]


def audit_requirement(text: str) -> dict:
    """
    Full §8.3 wording audit of a single requirement string.

    Returns:
      verbal_form       – output of detect_verbal_form
      obligation_count  – int (number of 'shall' clauses)
      forbidden_terms   – list of forbidden terms found
      rationale_markers – list of rationale phrases found
      compliant         – True only when findings list is empty
      findings          – list of human-readable violation strings
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Requirement text must be a non-empty string")

    verbal = detect_verbal_form(text)
    obligation_count = count_obligations(text)
    forbidden = check_forbidden_terms(text)
    rationale = check_embedded_rationale(text)

    findings = []

    if not verbal["compliant"]:
        findings.append(verbal["message"])

    if verbal["form"] == "shall" and obligation_count > 1:
        findings.append(
            f"Compound requirement: {obligation_count} 'shall' clauses found; "
            f"split into {obligation_count} separate requirements"
        )

    for term in forbidden:
        findings.append(
            f"Ambiguous term '{term}': replace with a measurable criterion"
        )

    for marker in rationale:
        findings.append(
            f"Embedded rationale marker '{marker}': move justification to a NOTE"
        )

    return {
        "verbal_form": verbal,
        "obligation_count": obligation_count,
        "forbidden_terms": forbidden,
        "rationale_markers": rationale,
        "compliant": len(findings) == 0,
        "findings": findings,
    }
