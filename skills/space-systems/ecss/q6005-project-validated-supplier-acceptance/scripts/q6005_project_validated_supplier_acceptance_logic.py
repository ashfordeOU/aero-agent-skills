"""Acceptance testing for a hybrid maker validated for one programme only.

Anchor: ECSS-Q-ST-60-05C clause 12.3 (the acceptance testing that applies
when the manufacturer was validated for a single programme rather than
holding an approved line, and the production acceptance steps that go with
it). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the validation record and the build request it is being read
   against. Both carry a programme, a technology and a date; the record also
   carries the hybrid types it was granted for and the window it is good in.
2. Decide whether the validation reaches this build at all. A validation
   scoped to one programme does not travel to another, however similar the
   part, and a build outside the validity window is outside it whatever the
   scope says. Every failing condition is named, because a maker one
   condition short is in a different position from one that is out entirely.
3. Assemble the production acceptance steps this build owes. The base set
   applies to every project-validated build; a first production lot and an
   enhanced reliability level each add their own steps on top.
4. Compare the steps performed against the steps owed, matching names
   insensitively to case and separator, and name what is outstanding.
5. Return whether the build may be accepted, with the coverage finding and
   the outstanding steps kept separate: an out-of-scope validation is not
   repaired by running more tests.
"""

import datetime

__all__ = [
    "BASE_ACCEPTANCE_STEPS",
    "FIRST_LOT_ADDITIONAL_STEPS",
    "ENHANCED_RELIABILITY_ADDITIONAL_STEPS",
    "RELIABILITY_LEVELS",
    "parse_date",
    "validate_validation_record",
    "validate_build_request",
    "validation_covers",
    "required_acceptance_steps",
    "missing_acceptance_steps",
    "assess_project_validated_acceptance",
]

# Production acceptance steps every project-validated build owes.
BASE_ACCEPTANCE_STEPS = (
    "full-electrical-acceptance-on-every-unit",
    "environmental-acceptance-on-every-lot",
    "lot-construction-analysis",
    "internal-visual-inspection-record",
    "delivery-review-with-customer",
)

# Added when this is the first production lot off the validated process.
FIRST_LOT_ADDITIONAL_STEPS = (
    "customer-witnessed-key-operations",
    "extended-burn-in",
)

# Added when the build is at the enhanced reliability level.
ENHANCED_RELIABILITY_ADDITIONAL_STEPS = (
    "radiographic-inspection",
    "residual-gas-analysis",
)

RELIABILITY_LEVELS = ("standard", "enhanced")


def _clean_token(value, label):
    """Return a normalised lower-case token, raising on anything unusable."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip().lower().replace("_", "-").replace(" ", "-")


def parse_date(value, label):
    """Return an ISO date string as a date, raising on anything else."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not an ISO date: %r" % (label, value))


def validate_validation_record(record):
    """Return the maker's programme validation record, normalised."""
    if not isinstance(record, dict):
        raise ValueError("validation record must be a mapping")
    for key in ("programme", "technology", "valid_from", "valid_until"):
        if key not in record:
            raise ValueError("validation record missing required key '%s'" % key)
    types = record.get("hybrid_types", ())
    if isinstance(types, str) or not isinstance(types, (list, tuple, set, frozenset)):
        raise ValueError("hybrid_types must be a sequence of hybrid type names")
    if not types:
        raise ValueError("a validation record covering no hybrid type grants nothing")
    valid_from = parse_date(record["valid_from"], "valid_from")
    valid_until = parse_date(record["valid_until"], "valid_until")
    if valid_until < valid_from:
        raise ValueError("validation expires (%s) before it starts (%s)" % (valid_until, valid_from))
    return {
        "programme": _clean_token(record["programme"], "validation programme"),
        "technology": _clean_token(record["technology"], "validation technology"),
        "hybrid_types": {_clean_token(t, "hybrid_types entry") for t in types},
        "valid_from": valid_from,
        "valid_until": valid_until,
        "reference": record.get("reference"),
    }


def validate_build_request(request):
    """Return the build this validation is being read against, normalised."""
    if not isinstance(request, dict):
        raise ValueError("build request must be a mapping")
    for key in ("programme", "technology", "hybrid_type", "build_date"):
        if key not in request:
            raise ValueError("build request missing required key '%s'" % key)
    level = request.get("reliability_level", "standard")
    level_token = _clean_token(level, "reliability_level")
    if level_token not in RELIABILITY_LEVELS:
        raise ValueError(
            "reliability_level must be one of %s, got %r" % (", ".join(RELIABILITY_LEVELS), level)
        )
    first_lot = request.get("first_production_lot", False)
    if not isinstance(first_lot, bool):
        raise ValueError("first_production_lot must be a boolean")
    return {
        "programme": _clean_token(request["programme"], "build programme"),
        "technology": _clean_token(request["technology"], "build technology"),
        "hybrid_type": _clean_token(request["hybrid_type"], "hybrid_type"),
        "build_date": parse_date(request["build_date"], "build_date"),
        "reliability_level": level_token,
        "first_production_lot": first_lot,
    }


def validation_covers(record, request):
    """Return whether the programme validation reaches this build, and why not.

    The programme scope is the point of the clause: a maker validated for one
    programme has shown its process against that programme's requirements,
    and nothing about a second programme follows from it.
    """
    v = validate_validation_record(record)
    b = validate_build_request(request)
    reasons = []
    if v["programme"] != b["programme"]:
        reasons.append(
            "validation is scoped to programme %s and this build is for %s"
            % (v["programme"], b["programme"])
        )
    if v["technology"] != b["technology"]:
        reasons.append(
            "validation covers the %s technology and this build uses %s"
            % (v["technology"], b["technology"])
        )
    if b["hybrid_type"] not in v["hybrid_types"]:
        reasons.append("hybrid type %s is not among the validated types" % b["hybrid_type"])
    if b["build_date"] < v["valid_from"]:
        reasons.append(
            "build date %s precedes the validation start %s" % (b["build_date"], v["valid_from"])
        )
    if b["build_date"] > v["valid_until"]:
        reasons.append(
            "build date %s is past the validation expiry %s" % (b["build_date"], v["valid_until"])
        )
    return {
        "covered": not reasons,
        "reasons": reasons,
        "programme": v["programme"],
        "reference": v["reference"],
    }


def required_acceptance_steps(request):
    """Return the production acceptance steps this build owes, in order."""
    b = validate_build_request(request)
    steps = list(BASE_ACCEPTANCE_STEPS)
    if b["first_production_lot"]:
        steps.extend(FIRST_LOT_ADDITIONAL_STEPS)
    if b["reliability_level"] == "enhanced":
        steps.extend(ENHANCED_RELIABILITY_ADDITIONAL_STEPS)
    return steps


def missing_acceptance_steps(request, performed):
    """Return the owed production acceptance steps this build has not run."""
    if isinstance(performed, str) or not isinstance(performed, (list, tuple, set, frozenset)):
        raise ValueError("performed steps must be a sequence of step names")
    done = {_clean_token(step, "performed step") for step in performed}
    return [step for step in required_acceptance_steps(request) if step not in done]


def assess_project_validated_acceptance(spec):
    """Run the full clause 12.3 acceptance assessment for one build.

    spec keys: validation (the programme validation record), request (the
    build), optional performed_steps (default none performed).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("validation", "request"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    coverage = validation_covers(spec["validation"], spec["request"])
    required = required_acceptance_steps(spec["request"])
    outstanding = missing_acceptance_steps(spec["request"], spec.get("performed_steps", ()))
    b = validate_build_request(spec["request"])

    refusals = list(coverage["reasons"])
    if outstanding:
        refusals.append(
            "production acceptance incomplete: %s" % ", ".join(outstanding)
        )
    accepted = not refusals
    return {
        "programme": b["programme"],
        "hybrid_type": b["hybrid_type"],
        "reliability_level": b["reliability_level"],
        "first_production_lot": b["first_production_lot"],
        "validation_covers_build": coverage["covered"],
        "coverage_reasons": coverage["reasons"],
        "validation_reference": coverage["reference"],
        "required_steps": required,
        "outstanding_steps": outstanding,
        "steps_completed": len(required) - len(outstanding),
        "disposition": "accept" if accepted else "refuse",
        "accepted": accepted,
        "refusals": refusals,
        "out_of_scope": not coverage["covered"],
    }
