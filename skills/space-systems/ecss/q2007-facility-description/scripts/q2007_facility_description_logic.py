#!/usr/bin/env python3
"""The facility description a space test centre keeps and tests against.

Anchor: ECSS-Q-ST-20-07 clause 5.2.2, the requirement that a test centre
maintains a description of each of its facilities: what the facility can
do, the environmental envelope it can hold, and the reference documents
that govern it. The procedure below is a paraphrase into implementable
steps; no standard text is reproduced.

Four things follow from what the facility description is for.

The description is what a customer is sold against. A facility entry
with no capability list, no envelope, or no reference documents cannot
support a booking, so completeness is taken entry by entry and the
incomplete entries are named rather than averaged away.

An envelope is a pair of bounds, not a single number. A bound pair that
is inverted, or a parameter declared with only one side, cannot be
tested against and is refused at validation rather than half-applied at
assessment.

A requested test either sits inside the envelope or it does not, and the
interesting case is the request that lands exactly on a bound. The
margin is therefore reported as a signed distance from the nearer bound
and the inside/outside call is made with a tolerance, so a demand equal
to a limit is inside on every host rather than inside on one and outside
on another.

A demand on a parameter the facility never declared is not a pass. It is
an undeclared parameter, reported separately from an exceeded one,
because the two need different corrective actions: one extends the
description, the other refuses the booking.

The policy numbers below are declared centre values, not physical
constants: a centre substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

REQUIRED_FACILITY_FIELDS = (
    "facility_id",
    "capabilities",
    "envelope",
    "reference_documents",
    "described_on_day",
)

REGISTER_ABSENT = "facility-register-absent"
FACILITY_ENTRY_INCOMPLETE = "facility-entry-incomplete"
FACILITY_ENVELOPE_MISSING = "facility-envelope-parameter-missing"
REFERENCE_DOCUMENTS_MISSING = "facility-reference-documents-missing"
CAPABILITY_COVERAGE_SHORT = "facility-capability-coverage-short"
REGISTER_MAINTAINED = "facility-description-maintained"

DEMAND_INSIDE = "demand-inside-envelope"
DEMAND_EXCEEDS = "demand-exceeds-envelope"
DEMAND_UNDECLARED = "demand-parameter-undeclared"

DEFAULT_REGISTER_POLICY = {
    "required_envelope_parameters": ("temperature-degc", "pressure-mbar"),
    "min_reference_documents": 1,
    "description_review_interval_days": 1095,
    "min_capability_coverage": 1.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_day(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number != int(number):
        raise ValueError("%s must be a whole non-negative day, got %r" % (name, value))
    return int(number)


def _require_interval(name, value):
    number = _require_number(name, value)
    if number <= 0.0 or number != int(number):
        raise ValueError("%s must be a whole positive day count, got %r" % (name, value))
    return int(number)


def _require_count(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number != int(number):
        raise ValueError("%s must be a whole non-negative count, got %r" % (name, value))
    return int(number)


def _require_token(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty identifier, got %r" % (name, value))
    return value.strip()


def _require_token_list(name, value):
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a sequence of identifiers, got %r" % (name, value))
    return [_require_token("%s[%d]" % (name, i), item) for i, item in enumerate(value)]


def at_least(value, bound):
    """Return True when value reaches bound, absorbing representation error."""
    left = _require_number("value", value)
    right = _require_number("bound", bound)
    return left > right or math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def within_bounds(value, lower, upper):
    """Return True when value sits inside the closed interval, boundary included."""
    v = _require_number("value", value)
    lo = _require_number("lower", lower)
    hi = _require_number("upper", upper)
    if lo > hi:
        raise ValueError("lower bound %g is above upper bound %g" % (lo, hi))
    if v < lo and not math.isclose(v, lo, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        return False
    if v > hi and not math.isclose(v, hi, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        return False
    return True


def bound_margin(value, lower, upper):
    """Return the signed distance to the nearer bound; zero exactly on a bound."""
    v = _require_number("value", value)
    lo = _require_number("lower", lower)
    hi = _require_number("upper", upper)
    if lo > hi:
        raise ValueError("lower bound %g is above upper bound %g" % (lo, hi))
    if v < lo:
        return v - lo
    if v > hi:
        return hi - v
    return min(v - lo, hi - v)


def validate_register_policy(policy):
    """Return the validated facility-register policy."""
    if not isinstance(policy, dict):
        raise ValueError("register policy must be a mapping")
    for key in policy:
        if key not in DEFAULT_REGISTER_POLICY:
            raise ValueError("unrecognised register policy key '%s'" % key)
    merged = dict(DEFAULT_REGISTER_POLICY)
    merged.update(policy)
    parameters = _require_token_list(
        "required_envelope_parameters", list(merged["required_envelope_parameters"])
    )
    if len(set(parameters)) != len(parameters):
        raise ValueError("required_envelope_parameters names the same parameter twice")
    return {
        "required_envelope_parameters": tuple(parameters),
        "min_reference_documents": _require_count(
            "min_reference_documents", merged["min_reference_documents"]
        ),
        "description_review_interval_days": _require_interval(
            "description_review_interval_days", merged["description_review_interval_days"]
        ),
        "min_capability_coverage": _require_fraction(
            "min_capability_coverage", merged["min_capability_coverage"]
        ),
    }


def validate_envelope(envelope, facility_id="facility"):
    """Return one validated environmental envelope as parameter -> (lower, upper)."""
    if not isinstance(envelope, dict):
        raise ValueError("%s envelope must be a mapping" % facility_id)
    out = {}
    for parameter, bounds in envelope.items():
        name = _require_token("envelope parameter", parameter)
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
            raise ValueError(
                "%s envelope parameter '%s' must be a (lower, upper) pair" % (facility_id, name)
            )
        lower = _require_number("%s/%s lower bound" % (facility_id, name), bounds[0])
        upper = _require_number("%s/%s upper bound" % (facility_id, name), bounds[1])
        if lower > upper:
            raise ValueError(
                "%s envelope parameter '%s' is inverted: %g above %g"
                % (facility_id, name, lower, upper)
            )
        out[name] = (lower, upper)
    return out


def validate_facility(facility):
    """Return one validated facility description entry."""
    if not isinstance(facility, dict):
        raise ValueError("a facility entry must be a mapping, got %r" % (facility,))
    for field in REQUIRED_FACILITY_FIELDS:
        if field not in facility:
            raise ValueError("facility entry missing field '%s'" % field)
    facility_id = _require_token("facility_id", facility["facility_id"])
    capabilities = _require_token_list("capabilities", facility["capabilities"])
    if len(set(capabilities)) != len(capabilities):
        raise ValueError("facility '%s' lists the same capability twice" % facility_id)
    documents = _require_token_list("reference_documents", facility["reference_documents"])
    return {
        "validated_facility": True,
        "facility_id": facility_id,
        "capabilities": capabilities,
        "envelope": validate_envelope(facility["envelope"], facility_id),
        "reference_documents": documents,
        "described_on_day": _require_day("described_on_day", facility["described_on_day"]),
    }


def validate_register(register):
    """Return the validated facility register."""
    if not isinstance(register, dict):
        raise ValueError("facility register must be a mapping")
    for field in ("maintained", "facilities", "centre_capabilities", "as_of_day"):
        if field not in register:
            raise ValueError("facility register missing field '%s'" % field)
    maintained = register["maintained"]
    if not isinstance(maintained, bool):
        raise ValueError("maintained must be a boolean")
    as_of_day = _require_day("as_of_day", register["as_of_day"])
    if not isinstance(register["facilities"], (list, tuple)):
        raise ValueError("facilities must be a sequence")
    facilities = [validate_facility(item) for item in register["facilities"]]
    seen = set()
    for facility in facilities:
        if facility["facility_id"] in seen:
            raise ValueError("facility '%s' is registered twice" % facility["facility_id"])
        seen.add(facility["facility_id"])
        if facility["described_on_day"] > as_of_day:
            raise ValueError(
                "facility '%s' is described after the assessment day" % facility["facility_id"]
            )
    centre = _require_token_list("centre_capabilities", register["centre_capabilities"])
    if len(set(centre)) != len(centre):
        raise ValueError("centre_capabilities names the same capability twice")
    return {
        "validated_register": True,
        "maintained": maintained,
        "facilities": facilities,
        "centre_capabilities": centre,
        "as_of_day": as_of_day,
    }


def _as_register(register):
    """Return the record already validated, validating a raw one first."""
    if isinstance(register, dict) and register.get("validated_register"):
        return register
    return validate_register(register)


def _as_facility(facility):
    """Return the entry already validated, validating a raw one first."""
    if isinstance(facility, dict) and facility.get("validated_facility"):
        return facility
    return validate_facility(facility)


def facilities_without_capabilities(register):
    """Return the facility ids whose entry declares no capability."""
    record = _as_register(register)
    return [f["facility_id"] for f in record["facilities"] if not f["capabilities"]]


def envelope_parameter_gaps(register, policy=None):
    """Return (facility_id, missing parameters) for every incomplete envelope."""
    record = _as_register(register)
    rules = validate_register_policy(policy or {})
    out = []
    for facility in record["facilities"]:
        missing = [p for p in rules["required_envelope_parameters"] if p not in facility["envelope"]]
        if missing:
            out.append((facility["facility_id"], missing))
    return out


def reference_document_gaps(register, policy=None):
    """Return the facility ids holding fewer reference documents than required."""
    record = _as_register(register)
    rules = validate_register_policy(policy or {})
    floor = rules["min_reference_documents"]
    return [
        f["facility_id"]
        for f in record["facilities"]
        if len(f["reference_documents"]) < floor
    ]


def descriptions_past_review(register, policy=None):
    """Return the facility ids whose description is older than the interval."""
    record = _as_register(register)
    rules = validate_register_policy(policy or {})
    limit = rules["description_review_interval_days"]
    return [
        f["facility_id"]
        for f in record["facilities"]
        if record["as_of_day"] - f["described_on_day"] > limit
    ]


def capability_coverage(register):
    """Return the fraction of the centre's capabilities some facility carries."""
    record = _as_register(register)
    declared = record["centre_capabilities"]
    if not declared:
        return 0.0
    held = set()
    for facility in record["facilities"]:
        held.update(facility["capabilities"])
    covered = sum(1 for name in declared if name in held)
    return covered / float(len(declared))


def uncovered_capabilities(register):
    """Return the centre capabilities no facility entry carries."""
    record = _as_register(register)
    held = set()
    for facility in record["facilities"]:
        held.update(facility["capabilities"])
    return [name for name in record["centre_capabilities"] if name not in held]


def find_facility(register, facility_id):
    """Return one facility entry by identifier, or raise when it is not held."""
    record = _as_register(register)
    wanted = _require_token("facility_id", facility_id)
    for facility in record["facilities"]:
        if facility["facility_id"] == wanted:
            return facility
    raise ValueError("the register holds no facility '%s'" % wanted)


def screen_demand(facility, demands):
    """Assess one set of parameter demands against a facility envelope."""
    if not isinstance(demands, dict) or not demands:
        raise ValueError("demands must be a non-empty mapping of parameter to value")
    entry = _as_facility(facility)
    results = []
    verdict = DEMAND_INSIDE
    for parameter in sorted(demands):
        name = _require_token("demand parameter", parameter)
        value = _require_number("demand '%s'" % name, demands[parameter])
        if name not in entry["envelope"]:
            results.append(
                {"parameter": name, "value": value, "outcome": DEMAND_UNDECLARED, "margin": None}
            )
            verdict = DEMAND_UNDECLARED
            continue
        lower, upper = entry["envelope"][name]
        inside = within_bounds(value, lower, upper)
        margin = bound_margin(value, lower, upper)
        results.append(
            {
                "parameter": name,
                "value": value,
                "outcome": DEMAND_INSIDE if inside else DEMAND_EXCEEDS,
                "margin": margin,
            }
        )
        if not inside and verdict != DEMAND_UNDECLARED:
            verdict = DEMAND_EXCEEDS
    return {"facility_id": entry["facility_id"], "verdict": verdict, "parameters": results}


def assess_facility_description(case):
    """Run the full clause 5.2.2 facility-description assessment.

    case keys: register (the facility register), optional policy, and an
    optional booking of the form {facility_id, demands}.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    if "register" not in case:
        raise ValueError("case missing required key 'register'")
    rules = validate_register_policy(case.get("policy") or {})
    record = validate_register(case["register"])

    blank = facilities_without_capabilities(record)
    envelope_gaps = envelope_parameter_gaps(record, rules)
    document_gaps = reference_document_gaps(record, rules)
    stale = descriptions_past_review(record, rules)
    coverage = capability_coverage(record)
    uncovered = uncovered_capabilities(record)

    findings = []
    advisories = []

    if not record["maintained"] or not record["facilities"]:
        verdict = REGISTER_ABSENT
        findings.append("no facility description register is being maintained")
    elif blank:
        verdict = FACILITY_ENTRY_INCOMPLETE
        findings.append(
            "%d facility entry/entries declare no capability: %s" % (len(blank), ", ".join(blank))
        )
    elif envelope_gaps:
        verdict = FACILITY_ENVELOPE_MISSING
        findings.append(
            "%d facility entry/entries miss a required envelope parameter: %s"
            % (
                len(envelope_gaps),
                ", ".join("%s(%s)" % (name, "+".join(miss)) for name, miss in envelope_gaps),
            )
        )
    elif document_gaps:
        verdict = REFERENCE_DOCUMENTS_MISSING
        findings.append(
            "%d facility entry/entries hold fewer than %d reference document(s): %s"
            % (len(document_gaps), rules["min_reference_documents"], ", ".join(document_gaps))
        )
    elif not at_least(coverage, rules["min_capability_coverage"]):
        verdict = CAPABILITY_COVERAGE_SHORT
        findings.append(
            "facility capability coverage %.3f is under the required %.3f; uncovered: %s"
            % (coverage, rules["min_capability_coverage"], ", ".join(uncovered) or "none")
        )
    else:
        verdict = REGISTER_MAINTAINED

    if stale:
        advisories.append(
            "%d facility description(s) are past their review age: %s"
            % (len(stale), ", ".join(stale))
        )

    booking = case.get("booking")
    screening = None
    if booking is not None:
        if not isinstance(booking, dict):
            raise ValueError("booking must be a mapping of facility_id and demands")
        for field in ("facility_id", "demands"):
            if field not in booking:
                raise ValueError("booking missing field '%s'" % field)
        screening = screen_demand(
            find_facility(record, booking["facility_id"]), booking["demands"]
        )
        if screening["verdict"] != DEMAND_INSIDE:
            findings.append(
                "the booking on facility '%s' is %s"
                % (screening["facility_id"], screening["verdict"])
            )

    return {
        "verdict": verdict,
        "maintained": record["maintained"],
        "facilities_without_capabilities": blank,
        "envelope_parameter_gaps": envelope_gaps,
        "reference_document_gaps": document_gaps,
        "descriptions_past_review": stale,
        "capability_coverage": coverage,
        "uncovered_capabilities": uncovered,
        "booking_screening": screening,
        "findings": findings,
        "advisories": advisories,
        "policy": rules,
    }
