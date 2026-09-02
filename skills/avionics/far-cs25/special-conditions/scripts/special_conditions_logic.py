#!/usr/bin/env python3
"""FAR-25.17 / CS-25.17 special conditions determination logic (paraphrase).

Common-knowledge summary (standards-map.yaml, far-25/cs-25: gated false,
quotable with citation): 14 CFR Part 25.17 and CS-25.17 let the
certification authority issue special conditions when a novel or unusual
design feature is not covered by the existing airworthiness standards.
The special condition states the additional requirements for that feature
and the means of compliance that demonstrate them. Classification here
uses a deterministic rule table over categorical inputs.

Units: none. This module reasons over categorical inputs (booleans and
short text identifiers), not physical quantities, so no unit convention
applies; the scope text it drafts carries no numeric values.
"""

REQUIRED_KEYS = ("feature", "novel", "existing_standard", "safety_significant")

# Rule table: (novel, existing_standard, safety_significant) ->
# (verdict, category). A feature covered by an existing standard is
# always "covered-by-existing"; anything else needs a special condition.
RULE_TABLE = {
    (True, True, True): ("covered-by-existing", "covered-by-existing-standard"),
    (True, True, False): ("covered-by-existing", "covered-by-existing-standard"),
    (False, True, True): ("covered-by-existing", "covered-by-existing-standard"),
    (False, True, False): ("covered-by-existing", "covered-by-existing-standard"),
    (True, False, True): ("special-condition-required", "novel-safety-behavior"),
    (True, False, False): ("special-condition-required", "novel-uncovered-technology"),
    (False, False, True): ("special-condition-required", "uncovered-safety-significant"),
    (False, False, False): ("special-condition-required", "outside-existing-standards"),
}

# Means of compliance proposed per special-condition category.
MOC_BY_CATEGORY = {
    "novel-safety-behavior": "analysis + test",
    "novel-uncovered-technology": "analysis + test + simulation",
    "uncovered-safety-significant": "analysis + test",
    "outside-existing-standards": "analysis only",
    "equivalent-safety-finding": "analysis + test",
}


def _validate(feature):
    """Validate the feature mapping; returns (feature name, esf flag)."""
    if not isinstance(feature, dict):
        raise ValueError("feature must be a dict, got %r" % (feature,))
    for key in REQUIRED_KEYS:
        if key not in feature:
            raise ValueError("missing required key %r in feature" % (key,))
    name = feature["feature"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("feature['feature'] must be a non-empty string")
    for key in ("novel", "existing_standard", "safety_significant"):
        if not isinstance(feature[key], bool):
            raise ValueError(
                "feature[%r] must be a bool, got %r" % (key, feature[key])
            )
    esf = feature.get("esf_needed", False)
    if not isinstance(esf, bool):
        raise ValueError("feature['esf_needed'] must be a bool, got %r" % (esf,))
    return name.strip(), esf


def classify_feature(feature):
    """FAR 25.17 / CS-25.17 special-conditions verdict for a design feature.

    Accepts a dict with keys feature (str), novel (bool),
    existing_standard (bool, whether an existing standard covers the
    feature), safety_significant (bool), and optionally esf_needed
    (bool, equivalent safety finding required). Returns (verdict,
    category): verdict is 'special-condition-required' or
    'covered-by-existing'. Invalid inputs raise ValueError.
    """
    _, esf = _validate(feature)
    if esf:
        return ("special-condition-required", "equivalent-safety-finding")
    return RULE_TABLE[
        (feature["novel"], feature["existing_standard"], feature["safety_significant"])
    ]


def draft_scopes(feature):
    """Scope content of the special condition for a required feature.

    Returns a dict with subject_area (the affected subject), issue (what
    the special condition addresses), and means_of_compliance (proposed
    demonstration, e.g. 'analysis + test'). Raises ValueError when the
    feature is covered by existing standards: there is no special
    condition to scope.
    """
    name, _ = _validate(feature)
    verdict, category = classify_feature(feature)
    if verdict != "special-condition-required":
        raise ValueError(
            "no special condition to scope: feature %r is covered by "
            "existing standards" % (name,)
        )
    return {
        "subject_area": name,
        "issue": (
            "the feature is not covered by the existing FAR-25 / CS-25 "
            "requirements, so additional requirements are needed for "
            "certification"
        ),
        "means_of_compliance": MOC_BY_CATEGORY[category],
    }
