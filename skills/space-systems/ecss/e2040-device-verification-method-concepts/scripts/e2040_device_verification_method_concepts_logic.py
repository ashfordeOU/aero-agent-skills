"""Verification method concepts for a device specification.

Anchor: ECSS-E-ST-20-40C clause 4.2 (the evidence gathering methods that show
a device matches its specification and is free of defects). Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Fold the method spellings a supplier writes onto the canonical set: test,
   analysis, similarity, review of design, inspection.
2. Decide, per requirement, which methods are admissible evidence for it. The
   deciding properties are the kind of requirement, whether it carries a
   numeric limit, and whether the property is a built-in one that only a
   physical examination can confirm.
3. Rule on similarity separately, because it is the only method whose
   admissibility depends on something outside the requirement: a named
   heritage item whose qualified environment is at least as severe as the one
   now being claimed.
4. Compare the allocated method with the admissible set and report a
   requirement whose evidence would not actually demonstrate it.
5. Summarise the allocation across the specification: how many requirements
   each method carries, which ones have no method at all, and whether the
   defect-freedom requirements are answered by a method that can see defects.
"""

import math

__all__ = [
    "CANONICAL_METHODS",
    "METHOD_ALIASES",
    "REQUIREMENT_KINDS",
    "KIND_ALIASES",
    "EVIDENCE_RANK",
    "SEVERITY_TOLERANCE",
    "normalize_method",
    "normalize_kind",
    "evidence_rank",
    "validate_requirement",
    "admissible_methods",
    "similarity_admissible",
    "assess_allocation",
    "coverage_by_method",
    "assess_verification_methods",
]

# The evidence gathering methods available to a device supplier.
CANONICAL_METHODS = (
    "test",
    "analysis",
    "similarity",
    "review-of-design",
    "inspection",
)

METHOD_ALIASES = {
    "testing": "test",
    "t": "test",
    "analyse": "analysis",
    "analyze": "analysis",
    "analysing": "analysis",
    "a": "analysis",
    "simulation": "analysis",
    "heritage": "similarity",
    "similar": "similarity",
    "s": "similarity",
    "rod": "review-of-design",
    "review of design": "review-of-design",
    "design-review": "review-of-design",
    "r": "review-of-design",
    "inspect": "inspection",
    "visual-examination": "inspection",
    "i": "inspection",
}

# What a requirement is about. The kind, not the wording, decides which
# evidence can settle it.
REQUIREMENT_KINDS = (
    "functional",
    "performance",
    "environmental",
    "interface",
    "workmanship",
    "construction",
)

KIND_ALIASES = {
    "function": "functional",
    "perf": "performance",
    "performances": "performance",
    "environment": "environmental",
    "environmental-load": "environmental",
    "interfaces": "interface",
    "defect-freedom": "workmanship",
    "cleanliness": "workmanship",
    "build-standard": "construction",
    "materials": "construction",
}

# How directly a method observes the device itself. Used to report the
# strongest evidence a requirement was given, never to override the
# admissibility rules.
EVIDENCE_RANK = {
    "test": 4,
    "analysis": 3,
    "similarity": 2,
    "inspection": 2,
    "review-of-design": 1,
}

# A heritage environment equal to the claimed one is admissible; this absorbs
# the representation error of a severity expressed as a float.
SEVERITY_TOLERANCE = 1e-9


def _clean_token(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip().lower().replace("_", "-")


def normalize_method(value):
    """Fold a method spelling onto one of the canonical methods."""
    token = _clean_token(value, "verification method")
    spaced = token.replace("-", " ")
    if token in CANONICAL_METHODS:
        return token
    if token in METHOD_ALIASES:
        return METHOD_ALIASES[token]
    if spaced in METHOD_ALIASES:
        return METHOD_ALIASES[spaced]
    raise ValueError("unrecognised verification method %r" % (value,))


def normalize_kind(value):
    """Fold a requirement kind spelling onto the canonical set."""
    token = _clean_token(value, "requirement kind")
    if token in REQUIREMENT_KINDS:
        return token
    if token in KIND_ALIASES:
        return KIND_ALIASES[token]
    raise ValueError("unrecognised requirement kind %r" % (value,))


def evidence_rank(method):
    """Return how directly a method observes the device."""
    return EVIDENCE_RANK[normalize_method(method)]


def validate_requirement(requirement):
    """Return one requirement folded onto canonical tokens."""
    if not isinstance(requirement, dict):
        raise ValueError("each requirement must be a mapping")
    for key in ("id", "kind"):
        if key not in requirement:
            raise ValueError("requirement missing required key '%s'" % key)
    identifier = requirement["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("requirement id must be a non-empty string, got %r" % (identifier,))
    numeric = requirement.get("numeric_limit", False)
    if not isinstance(numeric, bool):
        raise ValueError("numeric_limit of %s must be a boolean" % identifier)
    method = requirement.get("method")
    if method is not None:
        method = normalize_method(method)
    heritage = requirement.get("heritage")
    if heritage is not None and not isinstance(heritage, dict):
        raise ValueError("heritage of %s must be a mapping or None" % identifier)
    return {
        "id": identifier.strip(),
        "kind": normalize_kind(requirement["kind"]),
        "numeric_limit": numeric,
        "method": method,
        "heritage": heritage,
    }


def admissible_methods(requirement):
    """Return the sorted methods that could actually settle this requirement."""
    record = validate_requirement(requirement)
    kind = record["kind"]
    numeric = record["numeric_limit"]

    if kind == "workmanship":
        # A built-in defect is seen, not computed.
        allowed = {"inspection", "test"}
    elif kind == "construction":
        allowed = {"inspection", "review-of-design", "similarity"}
    elif kind == "environmental":
        # What the device survives is demonstrated on hardware, or argued
        # from hardware already qualified to at least the same severity.
        allowed = {"test", "analysis", "similarity"}
    elif kind in ("functional", "interface"):
        allowed = {"test", "analysis", "similarity", "review-of-design"}
    else:  # performance
        allowed = {"test", "analysis", "similarity"}

    if numeric:
        # A number is demonstrated by producing a number.
        allowed = allowed - {"review-of-design", "inspection"}
    return sorted(allowed)


def similarity_admissible(heritage, claimed_severity):
    """Decide whether a similarity claim is usable evidence."""
    if heritage is None:
        return {
            "admissible": False,
            "reason": "similarity claimed with no heritage item named",
        }
    if not isinstance(heritage, dict):
        raise ValueError("heritage must be a mapping or None")
    item = heritage.get("item")
    if not isinstance(item, str) or not item.strip():
        return {
            "admissible": False,
            "reason": "heritage names no item",
        }
    qualified = heritage.get("qualified_severity")
    for label, value in (
        ("qualified_severity", qualified),
        ("claimed_severity", claimed_severity),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a real number, got %r" % (label, value))
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite" % label)
        if float(value) <= 0.0:
            raise ValueError("%s must be positive, got %r" % (label, value))
    qualified = float(qualified)
    claimed = float(claimed_severity)
    equal = math.isclose(qualified, claimed, rel_tol=SEVERITY_TOLERANCE, abs_tol=0.0)
    if qualified < claimed and not equal:
        return {
            "admissible": False,
            "reason": "heritage item %s was qualified to a less severe "
                      "environment than the one claimed" % item.strip(),
        }
    if not heritage.get("design_unchanged", False):
        return {
            "admissible": False,
            "reason": "heritage item %s is not declared unchanged in the "
                      "respect being claimed" % item.strip(),
        }
    return {
        "admissible": True,
        "reason": "heritage item %s covers the claimed severity" % item.strip(),
    }


def assess_allocation(requirement, claimed_severity=None):
    """Decide whether the allocated method is admissible for one requirement."""
    record = validate_requirement(requirement)
    allowed = admissible_methods(requirement)
    if record["method"] is None:
        return {
            "id": record["id"],
            "kind": record["kind"],
            "method": None,
            "admissible_methods": allowed,
            "adequate": False,
            "reason": "no verification method allocated",
        }
    if record["method"] not in allowed:
        return {
            "id": record["id"],
            "kind": record["kind"],
            "method": record["method"],
            "admissible_methods": allowed,
            "adequate": False,
            "reason": "%s cannot settle a %s requirement%s"
                      % (record["method"], record["kind"],
                         " carrying a numeric limit" if record["numeric_limit"] else ""),
        }
    if record["method"] == "similarity":
        severity = claimed_severity
        if severity is None:
            severity = record["heritage"].get("claimed_severity") if record["heritage"] else None
        if severity is None:
            return {
                "id": record["id"],
                "kind": record["kind"],
                "method": "similarity",
                "admissible_methods": allowed,
                "adequate": False,
                "reason": "similarity claimed with no severity to compare against",
            }
        verdict = similarity_admissible(record["heritage"], severity)
        return {
            "id": record["id"],
            "kind": record["kind"],
            "method": "similarity",
            "admissible_methods": allowed,
            "adequate": verdict["admissible"],
            "reason": verdict["reason"],
        }
    return {
        "id": record["id"],
        "kind": record["kind"],
        "method": record["method"],
        "admissible_methods": allowed,
        "adequate": True,
        "reason": "%s is admissible evidence for a %s requirement"
                  % (record["method"], record["kind"]),
    }


def coverage_by_method(requirements):
    """Count how many requirements each method carries."""
    if isinstance(requirements, dict) or not isinstance(requirements, (list, tuple)):
        raise ValueError("requirements must be a sequence of mappings")
    counts = {method: 0 for method in CANONICAL_METHODS}
    unallocated = []
    for raw in requirements:
        record = validate_requirement(raw)
        if record["method"] is None:
            unallocated.append(record["id"])
        else:
            counts[record["method"]] += 1
    unallocated.sort()
    return {"counts": counts, "unallocated": unallocated}


def assess_verification_methods(spec):
    """Run the full clause 4.2 method allocation assessment.

    spec keys: requirements (sequence of requirement mappings), optional
    claimed_severity applied to every similarity claim that carries none.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "requirements" not in spec:
        raise ValueError("spec missing required key 'requirements'")
    requirements = spec["requirements"]
    if isinstance(requirements, dict) or not isinstance(requirements, (list, tuple)):
        raise ValueError("spec['requirements'] must be a sequence of mappings")
    if not requirements:
        raise ValueError("at least one requirement is needed to assess an allocation")

    seen = set()
    verdicts = []
    for raw in requirements:
        record = validate_requirement(raw)
        if record["id"] in seen:
            raise ValueError("requirement identifier %r declared twice" % record["id"])
        seen.add(record["id"])
        verdicts.append(assess_allocation(raw, spec.get("claimed_severity")))

    coverage = coverage_by_method(requirements)
    inadequate = [v for v in verdicts if not v["adequate"]]
    findings = ["%s: %s" % (v["id"], v["reason"]) for v in inadequate]

    workmanship = [v for v in verdicts if v["kind"] == "workmanship"]
    if not workmanship:
        findings.append(
            "no workmanship requirement is stated, so nothing in the "
            "specification asks the device to be free of built-in defects"
        )

    strongest = {}
    for verdict in verdicts:
        if verdict["method"] is not None:
            strongest[verdict["id"]] = evidence_rank(verdict["method"])

    return {
        "verdicts": verdicts,
        "coverage": coverage,
        "inadequate": [v["id"] for v in inadequate],
        "evidence_rank": strongest,
        "findings": findings,
        "compliant": not findings,
    }
