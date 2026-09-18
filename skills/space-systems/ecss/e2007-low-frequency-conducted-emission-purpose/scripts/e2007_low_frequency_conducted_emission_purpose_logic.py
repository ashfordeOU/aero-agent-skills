"""Aim of the low-frequency conducted-emission measurement.

Anchor: ECSS-E-ST-20-07C clause 5.4.2.1 (paraphrased into an
implementable procedure; no standard text is reproduced).

The clause states an aim rather than a limit: the low-frequency
conducted-emission measurement exists to bound the interference a unit
injects back onto the leads that feed it, on both the supply leads and
their returns, across the low part of the spectrum where the power
distribution is the coupling path. A test plan either serves that aim
or it does not, and a plan that runs cleanly while missing the aim
produces evidence about nothing.

Procedure implemented here:

1. Validate a proposed measurement plan: its frequency band, the
   supply and return leads of the unit, the leads it actually
   instruments, its sensing method, and whether a limit line is on
   record to compare against.
2. Decide, objective by objective, whether the plan serves the aim:
   every supply lead instrumented, every return lead instrumented, the
   band spanning the low-frequency range of interest, a limit line
   declared, and a sensing method that measures the lead current
   rather than a terminal voltage.
3. Quantify the band the plan covers as a share of the band the aim
   asks for, worked in the logarithmic domain because the range spans
   decades and a linear share would be dominated by its top end.
4. Report the leads left uninstrumented by name, so a plan that misses
   the returns is distinguishable from one that misses everything.

Stdlib only, offline, deterministic.
"""

import math

# Low part of the spectrum the aim covers, in hertz.
BAND_FLOOR_HZ = 30.0
BAND_CEILING_HZ = 100.0e3

METHOD_CURRENT_PROBE = "current-probe"
VALID_METHODS = (
    METHOD_CURRENT_PROBE,
    "voltage-probe",
    "line-impedance-stabilisation-network",
)

OBJECTIVE_SUPPLY_LEADS = "bound-emission-on-every-supply-lead"
OBJECTIVE_RETURN_LEADS = "bound-emission-on-every-return-lead"
OBJECTIVE_BAND = "span-the-low-frequency-band"
OBJECTIVE_LIMIT_LINE = "compare-against-a-declared-limit-line"
OBJECTIVE_SENSING = "sense-the-lead-current-not-a-terminal-voltage"
AIM_OBJECTIVES = (
    OBJECTIVE_SUPPLY_LEADS,
    OBJECTIVE_RETURN_LEADS,
    OBJECTIVE_BAND,
    OBJECTIVE_LIMIT_LINE,
    OBJECTIVE_SENSING,
)

# Band edges are compared after a logarithm, and a plan written to the
# exact band edge can land a few units in the last place inside or
# outside it. A relative tolerance far below any generator setting
# resolution absorbs that without moving the band.
FREQUENCY_RELATIVE_TOLERANCE = 1.0e-12
FRACTION_TOLERANCE = 1.0e-12


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def _lead_list(label, value):
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a sequence of lead identifiers" % label)
    leads = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("%s contains a non-string lead identifier %r" % (label, item))
        if item in leads:
            raise ValueError("%s lists lead %r twice" % (label, item))
        leads.append(item)
    return leads


def validate_plan(plan):
    """Validate one measurement plan and return a normalized copy."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping")
    plan_id = plan.get("id")
    if not isinstance(plan_id, str) or not plan_id.strip():
        raise ValueError("plan needs a non-empty string id")
    start = _numeric("plan %s band_start_hz" % plan_id, plan.get("band_start_hz"))
    stop = _numeric("plan %s band_stop_hz" % plan_id, plan.get("band_stop_hz"))
    if start <= 0:
        raise ValueError("plan %s band_start_hz must be positive" % plan_id)
    if stop <= start:
        raise ValueError("plan %s band_stop_hz must exceed band_start_hz" % plan_id)
    method = plan.get("method")
    if method not in VALID_METHODS:
        raise ValueError(
            "plan %s has unknown method %r (expected one of %s)"
            % (plan_id, method, ", ".join(VALID_METHODS))
        )
    supply = _lead_list("plan %s supply_leads" % plan_id, plan.get("supply_leads", []))
    returns = _lead_list("plan %s return_leads" % plan_id, plan.get("return_leads", []))
    if not supply:
        raise ValueError("plan %s lists no supply leads" % plan_id)
    if not returns:
        raise ValueError("plan %s lists no return leads" % plan_id)
    overlap = [lead for lead in supply if lead in returns]
    if overlap:
        raise ValueError(
            "plan %s lists %s as both a supply and a return lead"
            % (plan_id, ", ".join(overlap))
        )
    instrumented = _lead_list(
        "plan %s instrumented_leads" % plan_id, plan.get("instrumented_leads", [])
    )
    known = set(supply) | set(returns)
    unknown = [lead for lead in instrumented if lead not in known]
    if unknown:
        raise ValueError(
            "plan %s instruments unknown lead(s) %s" % (plan_id, ", ".join(unknown))
        )
    return {
        "id": plan_id,
        "band_start_hz": start,
        "band_stop_hz": stop,
        "method": method,
        "supply_leads": supply,
        "return_leads": returns,
        "instrumented_leads": instrumented,
        "limit_line_declared": _boolean(
            "plan %s limit_line_declared" % plan_id,
            plan.get("limit_line_declared", False),
        ),
    }


def required_band_decades():
    """Width of the band the aim covers, in decades."""
    return math.log10(BAND_CEILING_HZ / BAND_FLOOR_HZ)


def band_decades(start_hz, stop_hz):
    """Width of an arbitrary band, in decades."""
    start = _numeric("start_hz", start_hz)
    stop = _numeric("stop_hz", stop_hz)
    if start <= 0 or stop <= 0:
        raise ValueError("band edges must be positive")
    if stop <= start:
        raise ValueError("stop_hz must exceed start_hz")
    return math.log10(stop / start)


def band_coverage_fraction(plan):
    """Share of the aim's band the plan sweeps, in the log domain."""
    norm = validate_plan(plan)
    low = max(norm["band_start_hz"], BAND_FLOOR_HZ)
    high = min(norm["band_stop_hz"], BAND_CEILING_HZ)
    if high <= low:
        return 0.0
    return band_decades(low, high) / required_band_decades()


def band_spans_the_aim(plan):
    """True when the plan's sweep reaches both edges of the aim's band."""
    norm = validate_plan(plan)
    start_ok = norm["band_start_hz"] <= BAND_FLOOR_HZ * (
        1.0 + FREQUENCY_RELATIVE_TOLERANCE
    )
    stop_ok = norm["band_stop_hz"] >= BAND_CEILING_HZ * (
        1.0 - FREQUENCY_RELATIVE_TOLERANCE
    )
    return start_ok and stop_ok


def uninstrumented_leads(plan):
    """Supply and return leads the plan leaves without a sensor."""
    norm = validate_plan(plan)
    instrumented = set(norm["instrumented_leads"])
    missing_supply = [lead for lead in norm["supply_leads"] if lead not in instrumented]
    missing_return = [lead for lead in norm["return_leads"] if lead not in instrumented]
    return missing_supply, missing_return


def objectives_served(plan):
    """Which of the clause aim's objectives the plan serves."""
    norm = validate_plan(plan)
    missing_supply, missing_return = uninstrumented_leads(norm)
    return {
        OBJECTIVE_SUPPLY_LEADS: not missing_supply,
        OBJECTIVE_RETURN_LEADS: not missing_return,
        OBJECTIVE_BAND: band_spans_the_aim(norm),
        OBJECTIVE_LIMIT_LINE: norm["limit_line_declared"],
        OBJECTIVE_SENSING: norm["method"] == METHOD_CURRENT_PROBE,
    }


def unserved_objectives(plan):
    """Objectives of the aim the plan does not serve, in a fixed order."""
    served = objectives_served(plan)
    return [name for name in AIM_OBJECTIVES if not served[name]]


def assess_plan(plan):
    """Assess one measurement plan against the aim of clause 5.4.2.1."""
    norm = validate_plan(plan)
    missing_supply, missing_return = uninstrumented_leads(norm)
    unserved = unserved_objectives(norm)
    coverage = band_coverage_fraction(norm)
    findings = []
    if missing_supply:
        findings.append("supply-leads-without-a-sensor")
    if missing_return:
        findings.append("return-leads-without-a-sensor")
    if not band_spans_the_aim(norm):
        findings.append("sweep-does-not-span-the-low-frequency-band")
    if not norm["limit_line_declared"]:
        findings.append("no-limit-line-to-compare-against")
    if norm["method"] != METHOD_CURRENT_PROBE:
        findings.append("method-does-not-sense-the-lead-current")
    return {
        "id": norm["id"],
        "band_coverage_fraction": coverage,
        "missing_supply_leads": missing_supply,
        "missing_return_leads": missing_return,
        "unserved_objectives": unserved,
        "findings": findings,
        "serves_the_aim": not findings,
    }


def assess_low_frequency_conducted_emission_purpose(plans):
    """Run the clause 5.4.2.1 aim check over a list of measurement plans."""
    if not isinstance(plans, list) or not plans:
        raise ValueError("plans must be a non-empty list")
    results = []
    seen = set()
    for plan in plans:
        result = assess_plan(plan)
        if result["id"] in seen:
            raise ValueError("duplicate plan id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    failing = [r["id"] for r in results if not r["serves_the_aim"]]
    total = 0.0
    for result in results:
        total += result["band_coverage_fraction"]
    return {
        "plans": results,
        "mean_band_coverage_fraction": total / len(results),
        "plans_missing_the_aim": failing,
        "serves_the_aim": not failing,
    }
