#!/usr/bin/env python3
"""Review of customer requirements, ECSS-Q-ST-20-07C clause 5.7.2.

Paraphrased clause intent, no verbatim standard text. Before a test
centre commits to a test request it reviews that request: is the content
complete enough to quote and run, can this facility deliver the
parameters asked for inside the window asked for, and did the safety
input the specimen needs arrive with it. This module turns that into a
deterministic decision:

  mandatory content items -> what the request is still missing
  requested parameters    -> inside / outside / unknown vs the envelope
  window vs free capacity -> can the centre fit it at all
  hazard + safety data    -> what the customer still owes

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerance. Envelope bounds and week counts are floats, so a
# request that exactly meets a bound can land a few units in the last
# place the wrong side of it. The tolerance absorbs that representation
# error only; it never widens a facility limit.
REL_TOL = 1e-12
ABS_TOL = 1e-12

# Content a test request carries before the centre can review it at all.
REQUIRED_CONTENT = (
    "acceptance_criteria",
    "deliverables",
    "specimen_identification",
    "test_objective",
)

FEASIBLE = "parameter-within-envelope"
INFEASIBLE = "parameter-outside-envelope"
UNCHARACTERISED = "parameter-envelope-unknown"

DECISION_ACCEPTED = "request-accepted"
DECISION_ACCEPTED_WITH_ACTIONS = "request-accepted-with-actions"
DECISION_REFUSED = "request-refused"


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _scalar(value, name):
    return _number({"v": value}, "v", name)


def _flag(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, bool):
        raise ValueError("%s: field %r must be a boolean, got %r" % (where, key, value))
    return value


def at_least(value, bound):
    """True when a value reaches a lower bound, absorbing float error."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def at_most(value, bound):
    """True when a value stays under an upper bound, absorbing float error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def validate_request(request):
    """Validate an incoming test request and return it normalized."""
    where = "request"
    if not isinstance(request, dict):
        raise ValueError("%s: record must be a mapping" % where)

    out = {}
    for key in ("request_id", "customer"):
        value = request.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("%s: field %r must be a non-empty string" % (where, key))
        out[key] = value.strip()

    params = request.get("requested_parameters")
    if not isinstance(params, dict) or not params:
        raise ValueError("%s: requested_parameters must be a non-empty mapping" % where)
    normalized = {}
    for name, value in params.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("%s: parameter names must be non-empty strings" % where)
        normalized[name.strip()] = _number(params, name, "%s.requested_parameters" % where)
    out["requested_parameters"] = normalized

    for key in ("requested_weeks", "window_weeks"):
        value = _number(request, key, where)
        if value <= 0.0:
            raise ValueError("%s: %s must be > 0, got %g" % (where, key, value))
        out[key] = value
    if out["requested_weeks"] > out["window_weeks"] and not math.isclose(
        out["requested_weeks"], out["window_weeks"], rel_tol=REL_TOL, abs_tol=ABS_TOL
    ):
        raise ValueError(
            "%s: requested_weeks (%g) cannot exceed the customer window (%g)"
            % (where, out["requested_weeks"], out["window_weeks"])
        )

    out["hazardous_specimen"] = _flag(request, "hazardous_specimen", where)
    out["safety_data_supplied"] = _flag(request, "safety_data_supplied", where)

    measures = request.get("safety_measures", [])
    if not isinstance(measures, (list, tuple)):
        raise ValueError("%s: safety_measures must be a sequence" % where)
    out["safety_measures"] = [str(m).strip() for m in measures if str(m).strip()]

    hazards = request.get("declared_hazards", [])
    if not isinstance(hazards, (list, tuple)):
        raise ValueError("%s: declared_hazards must be a sequence" % where)
    out["declared_hazards"] = [str(h).strip() for h in hazards if str(h).strip()]

    for key in REQUIRED_CONTENT:
        value = request.get(key, "")
        out[key] = value.strip() if isinstance(value, str) else value
    return out


def missing_content(request, required=REQUIRED_CONTENT):
    """List the mandatory content items the request does not actually carry."""
    if not isinstance(request, dict):
        raise ValueError("request: record must be a mapping")
    if not isinstance(required, (list, tuple)) or not required:
        raise ValueError("required: must be a non-empty sequence of item names")
    gaps = []
    for key in required:
        value = request.get(key)
        if value is None:
            gaps.append(key)
        elif isinstance(value, str) and not value.strip():
            gaps.append(key)
        elif isinstance(value, (list, tuple, dict)) and not value:
            gaps.append(key)
    return sorted(gaps)


def validate_envelope(envelope):
    """Validate the facility envelope: parameter name -> (lower, upper)."""
    if not isinstance(envelope, dict) or not envelope:
        raise ValueError("envelope: must be a non-empty mapping")
    out = {}
    for name, bounds in envelope.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("envelope: parameter names must be non-empty strings")
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
            raise ValueError("envelope[%r]: bounds must be a (lower, upper) pair" % name)
        lower = _scalar(bounds[0], "envelope[%r].lower" % name)
        upper = _scalar(bounds[1], "envelope[%r].upper" % name)
        if not upper > lower:
            raise ValueError(
                "envelope[%r]: upper (%g) must exceed lower (%g)" % (name, upper, lower)
            )
        out[name.strip()] = (lower, upper)
    return out


def parameter_feasibility(requested, envelope):
    """Score each requested parameter against the facility envelope."""
    if not isinstance(requested, dict) or not requested:
        raise ValueError("requested: must be a non-empty mapping")
    bounds = validate_envelope(envelope)
    out = {}
    for name in sorted(requested):
        value = _number(requested, name, "requested")
        if name not in bounds:
            out[name] = {
                "value": value,
                "status": UNCHARACTERISED,
                "lower": None,
                "upper": None,
                "margin_fraction": None,
            }
            continue
        lower, upper = bounds[name]
        inside = at_least(value, lower) and at_most(value, upper)
        span = upper - lower
        headroom = min(value - lower, upper - value)
        out[name] = {
            "value": value,
            "status": FEASIBLE if inside else INFEASIBLE,
            "lower": lower,
            "upper": upper,
            "margin_fraction": headroom / span,
        }
    return out


def capacity_is_available(requested_weeks, free_weeks):
    """True when the centre has enough free weeks inside the window."""
    requested = _scalar(requested_weeks, "requested_weeks")
    free = _scalar(free_weeks, "free_weeks")
    if requested <= 0.0:
        raise ValueError("requested_weeks must be > 0, got %g" % requested)
    if free < 0.0:
        raise ValueError("free_weeks must be >= 0, got %g" % free)
    return at_least(free, requested)


def safety_input_findings(request):
    """Report what the customer still owes on the safety side of the request."""
    if not isinstance(request, dict):
        raise ValueError("request: record must be a mapping")
    hazardous = _flag(request, "hazardous_specimen", "request")
    supplied = _flag(request, "safety_data_supplied", "request")
    measures = request.get("safety_measures", [])
    hazards = request.get("declared_hazards", [])
    if not isinstance(measures, (list, tuple)) or not isinstance(hazards, (list, tuple)):
        raise ValueError("request: safety_measures and declared_hazards must be sequences")

    out = []
    if hazardous and not supplied:
        out.append(
            "the specimen is declared hazardous and no safety data came with the "
            "request, so the hazard cannot be carried into the facility calendar"
        )
    if hazardous and not [m for m in measures if str(m).strip()]:
        out.append(
            "the specimen is declared hazardous and no protective measure is named "
            "against it, so the centre cannot size its own precautions"
        )
    if not hazardous and [h for h in hazards if str(h).strip()]:
        out.append(
            "%d hazard(s) are listed against a specimen declared non-hazardous; the "
            "customer resolves the contradiction before a slot is held"
            % len([h for h in hazards if str(h).strip()])
        )
    return out


def commitment_decision(gaps, infeasible, capacity_ok, safety):
    """Grade the review into accept, accept against actions, or refuse."""
    for name, value in (("gaps", gaps), ("infeasible", infeasible), ("safety", safety)):
        if not isinstance(value, (list, tuple)):
            raise ValueError("%s: must be a sequence" % name)
    if not isinstance(capacity_ok, bool):
        raise ValueError("capacity_ok must be a boolean, got %r" % (capacity_ok,))
    if infeasible or not capacity_ok:
        return DECISION_REFUSED
    if gaps or safety:
        return DECISION_ACCEPTED_WITH_ACTIONS
    return DECISION_ACCEPTED


def evaluate_customer_requirements(request, envelope, free_weeks):
    """Full clause 5.7.2 review of one incoming test request."""
    normalized = validate_request(request)
    gaps = missing_content(normalized)
    feasibility = parameter_feasibility(normalized["requested_parameters"], envelope)
    infeasible = sorted(
        name for name, entry in feasibility.items() if entry["status"] == INFEASIBLE
    )
    unknown = sorted(
        name for name, entry in feasibility.items() if entry["status"] == UNCHARACTERISED
    )
    capacity_ok = capacity_is_available(normalized["requested_weeks"], free_weeks)
    safety = safety_input_findings(normalized)

    actions = []
    for item in gaps:
        actions.append("customer supplies the missing %s" % item.replace("_", " "))
    for name in unknown:
        actions.append(
            "centre characterises its envelope for %s before the level is agreed" % name
        )
    actions.extend(safety)

    refusals = []
    for name in infeasible:
        entry = feasibility[name]
        refusals.append(
            "%s requested at %g sits outside the facility envelope %g to %g"
            % (name, entry["value"], entry["lower"], entry["upper"])
        )
    if not capacity_ok:
        refusals.append(
            "the request needs %g week(s) and %g week(s) are free inside the "
            "customer window" % (normalized["requested_weeks"], float(free_weeks))
        )

    if unknown and not (infeasible or not capacity_ok):
        decision = DECISION_ACCEPTED_WITH_ACTIONS
    else:
        decision = commitment_decision(gaps, infeasible, capacity_ok, safety)

    return {
        "request": normalized,
        "missing_content": gaps,
        "parameter_feasibility": feasibility,
        "infeasible_parameters": infeasible,
        "uncharacterised_parameters": unknown,
        "capacity_is_available": capacity_ok,
        "safety_findings": safety,
        "actions": actions,
        "refusal_reasons": refusals,
        "decision": decision,
    }
