"""Dependability provisions of a spacecraft thermal control design.

Anchor: ECSS-E-ST-31C clauses 4.4.9 to 4.4.13 (design provisions for
reliability, interchangeability, maintenance, safety and availability).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Turn element failure rates into mission reliabilities and combine them in
   series along a heater line and in parallel across redundant lines, with any
   shared element placed in series with the whole redundant block.
2. Compare a series thermostat stack with a parallel one on both of its
   failure modes and recommend the topology that minimises the probability of
   the outcome declared hazardous for that item.
3. Grade a spare unit's interface parameters against the nominal tolerance
   band to decide whether it is interchangeable without requalification.
4. Compute availability for repairable items only.
"""

import math

__all__ = [
    "PROBABILITY_TOLERANCE",
    "HAZARDOUS_OUTCOMES",
    "element_reliability",
    "series_reliability",
    "parallel_reliability",
    "heater_chain_reliability",
    "thermostat_topology_risk",
    "recommend_thermostat_topology",
    "interchangeability_findings",
    "availability",
    "assess_dependability",
]

# Reliability comparisons are products of exponentials and can land exactly on
# a threshold. Absorb the representation error here instead of moving the
# threshold.
PROBABILITY_TOLERANCE = 1e-12

# The two outcomes a thermostat topology has to be chosen between.
HAZARDOUS_OUTCOMES = ("loss_of_heating", "loss_of_cutoff")


def _require_real(value, label):
    """Return value as a finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _require_positive(value, label):
    """Return value as a strictly positive finite float."""
    out = _require_real(value, label)
    if out <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, out))
    return out


def _require_non_negative(value, label):
    """Return value as a non-negative finite float."""
    out = _require_real(value, label)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, out))
    return out


def _require_probability(value, label):
    """Return value as a probability in the closed unit interval."""
    out = _require_real(value, label)
    if out < 0.0 or out > 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (label, out))
    return out


def _require_name(value, label):
    """Return a non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def element_reliability(failure_rate_per_hour, mission_hours):
    """Return the mission survival probability of one element."""
    rate = _require_non_negative(failure_rate_per_hour, "failure_rate_per_hour")
    hours = _require_positive(mission_hours, "mission_hours")
    return math.exp(-rate * hours)


def series_reliability(values):
    """Return the reliability of elements that all have to work."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("values must be a non-empty sequence of reliabilities")
    product = 1.0
    for index, value in enumerate(values):
        product *= _require_probability(value, "values[%d]" % index)
    return product


def parallel_reliability(values):
    """Return the reliability of a block that survives while one branch works."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("values must be a non-empty sequence of reliabilities")
    failure = 1.0
    for index, value in enumerate(values):
        failure *= 1.0 - _require_probability(value, "values[%d]" % index)
    return 1.0 - failure


def heater_chain_reliability(lines, mission_hours, shared_elements=None):
    """Return the mission reliability of a redundant heater chain.

    Each line is a sequence of element failure rates in 1/h; every element of
    a line has to survive for that line to heat, one surviving line is enough,
    and any shared element sits in series with the whole redundant block.
    """
    if not isinstance(lines, (list, tuple)) or not lines:
        raise ValueError("lines must be a non-empty sequence of heater lines")
    line_values = []
    for index, line in enumerate(lines):
        if not isinstance(line, (list, tuple)) or not line:
            raise ValueError("lines[%d] must be a non-empty sequence of rates" % index)
        elements = [
            element_reliability(rate, mission_hours) for rate in line
        ]
        line_values.append(series_reliability(elements))
    block = parallel_reliability(line_values)
    shared_value = 1.0
    if shared_elements:
        if not isinstance(shared_elements, (list, tuple)):
            raise ValueError("shared_elements must be a sequence of rates")
        shared_value = series_reliability(
            [element_reliability(rate, mission_hours) for rate in shared_elements]
        )
    return {
        "line_reliabilities": line_values,
        "redundant_block": block,
        "shared_reliability": shared_value,
        "chain_reliability": block * shared_value,
    }


def thermostat_topology_risk(count, stuck_open_probability, stuck_closed_probability,
                             topology):
    """Return both failure-mode probabilities for a thermostat stack.

    In series every device has to close for heat to flow and every device has
    to fail closed before the cut-off is lost; in parallel the reverse holds.
    """
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ValueError("count must be an integer of at least one, got %r" % (count,))
    p_open = _require_probability(stuck_open_probability, "stuck_open_probability")
    p_closed = _require_probability(stuck_closed_probability, "stuck_closed_probability")
    if p_open + p_closed > 1.0:
        raise ValueError(
            "stuck-open and stuck-closed probabilities sum above one (%g)"
            % (p_open + p_closed)
        )
    if topology not in ("series", "parallel"):
        raise ValueError("topology must be 'series' or 'parallel', got %r" % (topology,))
    any_open = 1.0 - (1.0 - p_open) ** count
    all_open = p_open ** count
    any_closed = 1.0 - (1.0 - p_closed) ** count
    all_closed = p_closed ** count
    if topology == "series":
        return {
            "topology": "series",
            "count": count,
            "loss_of_heating": any_open,
            "loss_of_cutoff": all_closed,
        }
    return {
        "topology": "parallel",
        "count": count,
        "loss_of_heating": all_open,
        "loss_of_cutoff": any_closed,
    }


def recommend_thermostat_topology(count, stuck_open_probability,
                                  stuck_closed_probability, hazardous_outcome):
    """Recommend the thermostat topology for the declared hazardous outcome."""
    if hazardous_outcome not in HAZARDOUS_OUTCOMES:
        raise ValueError(
            "hazardous_outcome must be one of %s, got %r"
            % (", ".join(HAZARDOUS_OUTCOMES), hazardous_outcome)
        )
    series = thermostat_topology_risk(
        count, stuck_open_probability, stuck_closed_probability, "series"
    )
    parallel = thermostat_topology_risk(
        count, stuck_open_probability, stuck_closed_probability, "parallel"
    )
    series_risk = series[hazardous_outcome]
    parallel_risk = parallel[hazardous_outcome]
    if math.isclose(series_risk, parallel_risk, rel_tol=0.0, abs_tol=PROBABILITY_TOLERANCE):
        recommended = "series"
    elif series_risk < parallel_risk:
        recommended = "series"
    else:
        recommended = "parallel"
    return {
        "hazardous_outcome": hazardous_outcome,
        "series": series,
        "parallel": parallel,
        "recommended": recommended,
        "hazardous_probability": min(series_risk, parallel_risk),
    }


def interchangeability_findings(nominal, spare, relative_tolerances):
    """Return the findings that stop a spare swapping in without requalification.

    All three mappings are keyed by interface parameter name; a parameter
    present in the nominal but absent from the spare is itself a finding.
    """
    for label, value in (("nominal", nominal), ("spare", spare),
                         ("relative_tolerances", relative_tolerances)):
        if not isinstance(value, dict):
            raise ValueError("%s must be a mapping" % label)
    if not nominal:
        raise ValueError("nominal must declare at least one interface parameter")
    findings = []
    for key in sorted(nominal):
        reference = _require_real(nominal[key], "nominal['%s']" % key)
        if reference == 0.0:
            raise ValueError(
                "nominal['%s'] is zero, so a relative tolerance is undefined" % key
            )
        if key not in spare:
            findings.append("spare does not declare interface parameter %s" % key)
            continue
        candidate = _require_real(spare[key], "spare['%s']" % key)
        if key not in relative_tolerances:
            raise ValueError("relative_tolerances missing parameter '%s'" % key)
        tolerance = _require_non_negative(
            relative_tolerances[key], "relative_tolerances['%s']" % key
        )
        deviation = abs(candidate - reference) / abs(reference)
        if deviation > tolerance + PROBABILITY_TOLERANCE:
            findings.append(
                "spare %s deviates %.4f from the nominal against a %.4f band"
                % (key, deviation, tolerance)
            )
    return findings


def availability(mtbf_hours, mttr_hours, repairable=True):
    """Return the availability of a repairable item.

    An item nobody can repair has no availability figure; asking for one is an
    input error rather than a ratio of one.
    """
    if not isinstance(repairable, bool):
        raise ValueError("repairable must be a boolean")
    if not repairable:
        raise ValueError(
            "availability is undefined for an item declared not repairable"
        )
    mtbf = _require_positive(mtbf_hours, "mtbf_hours")
    mttr = _require_non_negative(mttr_hours, "mttr_hours")
    return mtbf / (mtbf + mttr)


def assess_dependability(spec):
    """Run the full clauses 4.4.9 to 4.4.13 dependability assessment.

    spec keys: heater_lines, mission_hours, required_chain_reliability,
    thermostat_count, stuck_open_probability, stuck_closed_probability,
    hazardous_outcome; optional shared_elements, nominal_interface,
    spare_interface, interface_tolerances, mtbf_hours, mttr_hours, repairable.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "heater_lines", "mission_hours", "required_chain_reliability",
        "thermostat_count", "stuck_open_probability", "stuck_closed_probability",
        "hazardous_outcome",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    required_reliability = _require_probability(
        spec["required_chain_reliability"], "required_chain_reliability"
    )
    chain = heater_chain_reliability(
        spec["heater_lines"], spec["mission_hours"], spec.get("shared_elements")
    )
    topology = recommend_thermostat_topology(
        spec["thermostat_count"],
        spec["stuck_open_probability"],
        spec["stuck_closed_probability"],
        spec["hazardous_outcome"],
    )
    findings = []
    reliable = chain["chain_reliability"] >= required_reliability - PROBABILITY_TOLERANCE
    if not reliable:
        findings.append(
            "heater chain reliability %.6f falls short of the required %.6f"
            % (chain["chain_reliability"], required_reliability)
        )
    if spec.get("shared_elements") and len(spec["heater_lines"]) > 1:
        if chain["shared_reliability"] < chain["redundant_block"]:
            findings.append(
                "the shared element caps the redundant block at %.6f"
                % chain["shared_reliability"]
            )
    swap_findings = []
    if "nominal_interface" in spec:
        swap_findings = interchangeability_findings(
            spec["nominal_interface"],
            spec.get("spare_interface", {}),
            spec.get("interface_tolerances", {}),
        )
        findings.extend(swap_findings)
    item_availability = None
    if "mtbf_hours" in spec:
        repairable = spec.get("repairable", True)
        if repairable:
            item_availability = availability(
                spec["mtbf_hours"], spec.get("mttr_hours", 0.0), True
            )
        else:
            findings.append(
                "an availability figure was requested for an item declared not "
                "repairable"
            )
    return {
        "chain": chain,
        "reliable": reliable,
        "topology": topology,
        "recommended_topology": topology["recommended"],
        "interchangeable": not swap_findings,
        "availability": item_availability,
        "findings": findings,
        "compliant": not findings,
    }
