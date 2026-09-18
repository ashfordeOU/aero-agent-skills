"""Applicability and scope decision for stress-corrosion-cracking control.

Anchor: ECSS-Q-ST-70-36C, the framework clauses that fix which hardware the
stress-corrosion-cracking (SCC) control discipline applies to. Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalize the declared material of every part onto a known metallic family
   (aluminium, titanium, carbon and low-alloy steel, stainless steel, nickel,
   copper, magnesium, refractory) or onto a non-metallic family.
2. Decide scope from the family, not from the part name: metallic families are
   inside the SCC discipline, non-metallic families are outside it, and a
   surface layer takes the scope of the substrate it sits on.
3. Separate the in-scope families that carry a tabulated SCC resistance rating
   from the in-scope families that do not, because the second group owes test
   or literature evidence before an alloy choice can be defended.
4. Aggregate a parts list into a coverage figure -- how much of the metallic
   hardware can be dispositioned from tabulated ratings alone -- and raise a
   finding for every part that cannot.
"""

import math

__all__ = [
    "COVERAGE_TOLERANCE",
    "METALLIC_FAMILIES",
    "NON_METALLIC_FAMILIES",
    "PRODUCT_FORMS",
    "normalize_family",
    "normalize_form",
    "is_metallic",
    "family_in_scope",
    "has_tabulated_rating",
    "effective_family",
    "disposition_part",
    "assess_scope",
]

# Coverage is a ratio of small integer counts, but it is still a float
# division; absorb representation error at the reporting boundary instead of
# rounding the counts.
COVERAGE_TOLERANCE = 1e-9

# Metallic families inside the SCC discipline. "tabulated" marks the families
# whose alloys carry a published resistance rating that a selection can be
# defended against without new testing.
METALLIC_FAMILIES = {
    "aluminium": {"tabulated": True, "note": "wrought high-strength tempers span the full rating range"},
    "titanium": {"tabulated": True, "note": "generally resistant, sensitive to specific halogenated media"},
    "carbon-low-alloy-steel": {"tabulated": True, "note": "susceptibility tracks strength and tempering state"},
    "stainless-steel": {"tabulated": True, "note": "austenitic grades are chloride sensitive when stressed"},
    "nickel-alloy": {"tabulated": True, "note": "mostly resistant, precipitation-hardened tempers less so"},
    "copper-alloy": {"tabulated": True, "note": "ammonia-bearing media drive the known failures"},
    "magnesium": {"tabulated": True, "note": "treated as susceptible unless evidence says otherwise"},
    "refractory-metal": {"tabulated": False, "note": "sparse published ratings; evidence needed per application"},
    "beryllium": {"tabulated": False, "note": "sparse published ratings; evidence needed per application"},
}

NON_METALLIC_FAMILIES = (
    "polymer",
    "ceramic",
    "glass",
    "polymer-matrix-composite",
    "elastomer",
)

# Product forms recognised by the scope decision. A coating is not a family in
# its own right: its scope follows the substrate underneath it.
PRODUCT_FORMS = (
    "wrought",
    "cast",
    "forging",
    "extrusion",
    "weldment",
    "additive",
    "fastener",
    "coating",
)

_FAMILY_ALIASES = {
    "al": "aluminium",
    "aluminum": "aluminium",
    "aluminium-alloy": "aluminium",
    "ti": "titanium",
    "titanium-alloy": "titanium",
    "steel": "carbon-low-alloy-steel",
    "low-alloy-steel": "carbon-low-alloy-steel",
    "carbon-steel": "carbon-low-alloy-steel",
    "cres": "stainless-steel",
    "austenitic-stainless": "stainless-steel",
    "ni": "nickel-alloy",
    "nickel": "nickel-alloy",
    "cu": "copper-alloy",
    "copper": "copper-alloy",
    "brass": "copper-alloy",
    "mg": "magnesium",
    "magnesium-alloy": "magnesium",
    "refractory": "refractory-metal",
    "niobium": "refractory-metal",
    "tantalum": "refractory-metal",
    "molybdenum": "refractory-metal",
    "be": "beryllium",
    "cfrp": "polymer-matrix-composite",
    "composite": "polymer-matrix-composite",
    "plastic": "polymer",
    "rubber": "elastomer",
}


def _require_text(value, label):
    """Return a lower-cased, dash-normalized token, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    token = value.strip().lower().replace("_", "-").replace(" ", "-")
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def normalize_family(name):
    """Return the canonical family token for a declared material name."""
    token = _require_text(name, "material family")
    token = _FAMILY_ALIASES.get(token, token)
    if token in METALLIC_FAMILIES or token in NON_METALLIC_FAMILIES:
        return token
    raise ValueError(
        "material family %r is not recognised; declare one of %s"
        % (name, ", ".join(sorted(set(METALLIC_FAMILIES) | set(NON_METALLIC_FAMILIES))))
    )


def normalize_form(name):
    """Return the canonical product form token."""
    token = _require_text(name, "product form")
    if token not in PRODUCT_FORMS:
        raise ValueError(
            "product form %r is not recognised; use one of %s"
            % (name, ", ".join(PRODUCT_FORMS))
        )
    return token


def is_metallic(family):
    """Return True when the family is a metal."""
    return normalize_family(family) in METALLIC_FAMILIES


def family_in_scope(family):
    """Return True when the family falls inside the SCC control discipline."""
    return is_metallic(family)


def has_tabulated_rating(family):
    """Return True when the family carries a published SCC resistance rating."""
    token = normalize_family(family)
    if token not in METALLIC_FAMILIES:
        return False
    return bool(METALLIC_FAMILIES[token]["tabulated"])


def effective_family(part):
    """Return the family that governs scope for a part.

    A coating has no scope of its own: the substrate it is applied to decides,
    so a coating declared without a substrate family is an input error.
    """
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    for key in ("id", "family", "form"):
        if key not in part:
            raise ValueError("part missing required key %r" % key)
    form = normalize_form(part["form"])
    if form != "coating":
        return normalize_family(part["family"])
    substrate = part.get("substrate_family")
    if substrate is None:
        raise ValueError(
            "part %r is a coating; declare substrate_family so scope can follow the substrate"
            % (part["id"],)
        )
    return normalize_family(substrate)


def disposition_part(part):
    """Return the scope record for a single part."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    part_id = _require_text(part.get("id", ""), "part id")
    form = normalize_form(part["form"])
    declared = normalize_family(part["family"]) if form != "coating" else normalize_family(part["family"])
    governing = effective_family(part)
    in_scope = family_in_scope(governing)
    tabulated = has_tabulated_rating(governing) if in_scope else False
    if not in_scope:
        disposition = "out-of-scope-non-metallic"
        reason = "%s is not a metal, so no SCC resistance rating applies" % governing
    elif tabulated:
        disposition = "in-scope-rated"
        reason = METALLIC_FAMILIES[governing]["note"]
    else:
        disposition = "in-scope-evidence-required"
        reason = METALLIC_FAMILIES[governing]["note"]
    return {
        "id": part_id,
        "declared_family": declared,
        "governing_family": governing,
        "form": form,
        "in_scope": in_scope,
        "tabulated_rating": tabulated,
        "disposition": disposition,
        "reason": reason,
    }


def assess_scope(parts):
    """Disposition a parts list and report the tabulated-rating coverage.

    Returns the per-part records, the counts, the coverage ratio over the
    in-scope parts only, and a finding for every in-scope part that cannot be
    dispositioned from a published rating.
    """
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError("parts must be a non-empty sequence of part mappings")
    records = []
    seen = set()
    for part in parts:
        record = disposition_part(part)
        if record["id"] in seen:
            raise ValueError("duplicate part id %r in the parts list" % record["id"])
        seen.add(record["id"])
        records.append(record)
    in_scope = [r for r in records if r["in_scope"]]
    rated = [r for r in in_scope if r["tabulated_rating"]]
    unrated = [r for r in in_scope if not r["tabulated_rating"]]
    coverage = 1.0 if not in_scope else float(len(rated)) / float(len(in_scope))
    findings = [
        "part %s (%s) is in scope but has no published SCC resistance rating; "
        "test or literature evidence is owed" % (r["id"], r["governing_family"])
        for r in unrated
    ]
    complete = not findings
    return {
        "records": records,
        "total_parts": len(records),
        "in_scope_count": len(in_scope),
        "out_of_scope_count": len(records) - len(in_scope),
        "rated_count": len(rated),
        "coverage_ratio": coverage,
        "fully_covered": complete and math.isclose(
            coverage, 1.0, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
        ),
        "findings": findings,
    }
