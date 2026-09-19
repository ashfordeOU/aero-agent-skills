"""Equipment specification for an off-the-shelf candidate, and the match against it.

Anchor: ECSS-Q-ST-20-10C clause 5.1.2 (establish the equipment specification each
off-the-shelf candidate is to be matched against). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every requirement of the equipment specification: a category
   (functional, performance, interface), an obligation (mandatory, desirable)
   and a criterion that can actually be matched against a candidate datum.
2. Report the categories the specification never populated. An off-the-shelf
   unit is bought on its interfaces as much as on its function, so a
   specification carrying no interface requirement cannot decide anything.
3. Grade each candidate characteristic against its requirement as met, not met
   or undeclared. An undeclared datum is a hole in the candidate's data pack,
   not a zero, and it is kept out of the compliance ratio rather than scored.
4. Block acceptance on an unmet mandatory requirement, carry an unmet desirable
   requirement as a gap, and refuse to call a candidate assessable while a
   mandatory requirement has no declared datum behind it.
"""

import math

__all__ = [
    "CATEGORIES",
    "OBLIGATIONS",
    "CRITERION_KINDS",
    "COMPARISON_TOLERANCE",
    "validate_requirement",
    "build_specification",
    "specification_gaps",
    "evaluate_requirement",
    "compliance_ratio",
    "match_candidate",
    "assess_equipment_spec",
]

CATEGORIES = ("functional", "performance", "interface")
OBLIGATIONS = ("mandatory", "desirable")
CRITERION_KINDS = ("capability", "min", "max", "range", "target")

# A performance bound and the datum offered against it are both decimal figures
# transcribed from data sheets. Equality at the bound is a representation
# question, absorbed here, never by relaxing the bound itself.
COMPARISON_TOLERANCE = 1e-9


def _real(value, label):
    """Return value as a float, refusing anything that is not a real number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _at_least(value, bound):
    """True when value clears bound, counting an on-the-bound value as clearing."""
    return value > bound or math.isclose(value, bound, rel_tol=0.0, abs_tol=COMPARISON_TOLERANCE)


def _at_most(value, bound):
    """True when value stays under bound, counting an on-the-bound value as under."""
    return value < bound or math.isclose(value, bound, rel_tol=0.0, abs_tol=COMPARISON_TOLERANCE)


def validate_requirement(requirement):
    """Return one normalised requirement of the equipment specification."""
    if not isinstance(requirement, dict):
        raise ValueError("a requirement must be a mapping")
    ident = requirement.get("id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("requirement id must be a non-empty string")
    category = requirement.get("category")
    if category not in CATEGORIES:
        raise ValueError("requirement %s has category %r, expected one of %s"
                         % (ident, category, ", ".join(CATEGORIES)))
    obligation = requirement.get("obligation", "mandatory")
    if obligation not in OBLIGATIONS:
        raise ValueError("requirement %s has obligation %r, expected one of %s"
                         % (ident, obligation, ", ".join(OBLIGATIONS)))
    kind = requirement.get("kind")
    if kind not in CRITERION_KINDS:
        raise ValueError("requirement %s has kind %r, expected one of %s"
                         % (ident, kind, ", ".join(CRITERION_KINDS)))
    normalised = {
        "id": ident.strip(),
        "category": category,
        "obligation": obligation,
        "kind": kind,
        "unit": requirement.get("unit"),
    }
    if kind == "capability":
        required = requirement.get("required", True)
        if not isinstance(required, bool):
            raise ValueError("requirement %s capability flag must be boolean" % ident)
        normalised["required"] = required
    elif kind in ("min", "max"):
        normalised["limit"] = _real(requirement.get("limit"), "requirement %s limit" % ident)
    elif kind == "range":
        lower = _real(requirement.get("lower"), "requirement %s lower" % ident)
        upper = _real(requirement.get("upper"), "requirement %s upper" % ident)
        if lower > upper:
            raise ValueError("requirement %s has lower %g above upper %g" % (ident, lower, upper))
        normalised["lower"] = lower
        normalised["upper"] = upper
    else:
        normalised["target"] = _real(requirement.get("target"), "requirement %s target" % ident)
        tolerance = _real(requirement.get("tolerance", 0.0), "requirement %s tolerance" % ident)
        if tolerance < 0.0:
            raise ValueError("requirement %s tolerance must not be negative" % ident)
        normalised["tolerance"] = tolerance
    return normalised


def build_specification(requirements):
    """Return the validated equipment specification as an ordered requirement list."""
    if not isinstance(requirements, (list, tuple)) or not requirements:
        raise ValueError("the equipment specification needs at least one requirement")
    built = []
    seen = set()
    for item in requirements:
        entry = validate_requirement(item)
        if entry["id"] in seen:
            raise ValueError("duplicate requirement id %r in the specification" % entry["id"])
        seen.add(entry["id"])
        built.append(entry)
    return built


def specification_gaps(specification):
    """Return the categories the specification never populated."""
    present = {entry["category"] for entry in specification}
    return [category for category in CATEGORIES if category not in present]


def evaluate_requirement(requirement, declared_value):
    """Grade one declared candidate datum against one requirement."""
    entry = validate_requirement(requirement)
    record = {
        "id": entry["id"],
        "category": entry["category"],
        "obligation": entry["obligation"],
        "status": "undeclared",
        "margin": None,
        "detail": "no candidate datum declared for this requirement",
    }
    if declared_value is None:
        return record
    kind = entry["kind"]
    if kind == "capability":
        if not isinstance(declared_value, bool):
            raise ValueError("requirement %s expects a boolean candidate datum" % entry["id"])
        met = declared_value or not entry["required"]
        record["status"] = "met" if met else "not-met"
        record["detail"] = ("capability offered" if declared_value
                            else "capability absent from the candidate")
        return record
    value = _real(declared_value, "candidate datum for %s" % entry["id"])
    if kind == "min":
        met = _at_least(value, entry["limit"])
        record["margin"] = value - entry["limit"]
        record["detail"] = "%g against a floor of %g" % (value, entry["limit"])
    elif kind == "max":
        met = _at_most(value, entry["limit"])
        record["margin"] = entry["limit"] - value
        record["detail"] = "%g against a ceiling of %g" % (value, entry["limit"])
    elif kind == "range":
        met = _at_least(value, entry["lower"]) and _at_most(value, entry["upper"])
        record["margin"] = min(value - entry["lower"], entry["upper"] - value)
        record["detail"] = "%g against the band %g to %g" % (value, entry["lower"], entry["upper"])
    else:
        deviation = abs(value - entry["target"])
        met = _at_most(deviation, entry["tolerance"])
        record["margin"] = entry["tolerance"] - deviation
        record["detail"] = ("%g against a target of %g within %g"
                            % (value, entry["target"], entry["tolerance"]))
    record["status"] = "met" if met else "not-met"
    return record


def compliance_ratio(records):
    """Return met / assessed, counting only requirements with a declared datum."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of requirement records")
    assessed = [r for r in records if r.get("status") in ("met", "not-met")]
    if not assessed:
        return None
    met = sum(1 for r in assessed if r["status"] == "met")
    return met / float(len(assessed))


def match_candidate(specification, declared):
    """Match one off-the-shelf candidate's declared data against the specification."""
    spec = build_specification(specification)
    if not isinstance(declared, dict):
        raise ValueError("declared candidate data must be a mapping of requirement id to datum")
    unknown = sorted(set(declared) - {entry["id"] for entry in spec})
    if unknown:
        raise ValueError("declared data cite requirements absent from the specification: %s"
                         % ", ".join(unknown))
    records = [evaluate_requirement(entry, declared.get(entry["id"])) for entry in spec]
    blocking = [r["id"] for r in records
                if r["obligation"] == "mandatory" and r["status"] == "not-met"]
    undeclared_mandatory = [r["id"] for r in records
                            if r["obligation"] == "mandatory" and r["status"] == "undeclared"]
    gaps = [r["id"] for r in records
            if r["obligation"] == "desirable" and r["status"] != "met"]
    if blocking:
        verdict = "rejected"
    elif undeclared_mandatory:
        verdict = "not-assessable"
    elif gaps:
        verdict = "acceptable-with-gaps"
    else:
        verdict = "compliant"
    return {
        "records": records,
        "blocking": blocking,
        "undeclared_mandatory": undeclared_mandatory,
        "gaps": gaps,
        "compliance_ratio": compliance_ratio(records),
        "verdict": verdict,
    }


def assess_equipment_spec(spec):
    """Run the full clause 5.1.2 specification-and-match assessment.

    spec keys: requirements (list), candidates (mapping of candidate name to a
    mapping of requirement id to declared datum).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("requirements", "candidates"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    requirements = build_specification(spec["requirements"])
    candidates = spec["candidates"]
    if not isinstance(candidates, dict) or not candidates:
        raise ValueError("spec['candidates'] must be a non-empty mapping")
    missing_categories = specification_gaps(requirements)
    findings = []
    if missing_categories:
        findings.append("the specification populates no %s requirement"
                        % ", ".join(missing_categories))
    results = {}
    for name in sorted(candidates):
        results[name] = match_candidate(requirements, candidates[name])
    shortlist = sorted(
        (name for name, r in results.items()
         if r["verdict"] in ("compliant", "acceptable-with-gaps")),
        key=lambda n: (-(results[n]["compliance_ratio"] or 0.0), n),
    )
    return {
        "requirements": requirements,
        "missing_categories": missing_categories,
        "candidates": results,
        "shortlist": shortlist,
        "findings": findings,
        "specification_usable": not missing_categories,
    }
