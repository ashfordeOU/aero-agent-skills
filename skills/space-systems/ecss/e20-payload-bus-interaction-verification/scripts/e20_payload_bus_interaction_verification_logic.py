#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.7.6 payload-to-primary-bus interaction
verification (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard asks the interaction between a payload
and the primary power bus to be verified by test, covering the inrush
drawn when the payload is switched on, the undervoltage transient the
payload causes or must survive, and the failure cases agreed with the
customer. This module implements the checkable part of that clause:
categorization of a campaign case, the mandatory field list that
follows from the category, the peak inrush current and the time it
spends above the upstream protection threshold, the transient bus sag
from a load step against the bus lower limit and the payload
undervoltage lockout, the fault current with the inverse-square
protection clearing time and the let-through energy against the
containment requirement, and the coverage of the three case families
across the campaign. It does not schedule the test, does not size the
limiting element, and does not model the payload beyond its input
capacitance and current draw.
"""

import math

INRUSH_CASE_KINDS = frozenset(
    {
        "cold_start_inrush",
        "hot_switchover_inrush",
        "capacitive_load_inrush",
        "heater_switch_on_inrush",
    }
)
UNDERVOLTAGE_CASE_KINDS = frozenset(
    {
        "load_step_undervoltage",
        "bus_undervoltage_ride_through",
        "eclipse_entry_undervoltage",
        "battery_discharge_undervoltage",
    }
)
FAILURE_CASE_KINDS = frozenset(
    {
        "payload_short_circuit",
        "payload_overcurrent",
        "payload_reverse_energy",
        "payload_internal_latch_up",
        "protection_switch_failure",
    }
)

REQUIRED_CASE_FIELDS = {
    "inrush": frozenset(
        {
            "bus_voltage_v",
            "limiter_resistance_ohm",
            "load_capacitance_f",
            "allowed_peak_inrush_a",
            "protection_trip_current_a",
            "protection_trip_delay_s",
        }
    ),
    "undervoltage": frozenset(
        {
            "bus_voltage_v",
            "step_current_a",
            "bus_capacitance_f",
            "control_bandwidth_hz",
            "harness_resistance_ohm",
            "bus_lower_limit_v",
            "payload_undervoltage_lockout_v",
        }
    ),
    "agreed_failure": frozenset(
        {
            "bus_voltage_v",
            "fault_resistance_ohm",
            "harness_resistance_ohm",
            "protection_rated_current_a",
            "protection_i2t_a2s",
            "protection_minimum_clearing_time_s",
            "containment_time_s",
            "containment_outcome",
        }
    ),
}

RECOGNISED_CONTAINMENT_OUTCOMES = frozenset(
    {
        "payload_isolated",
        "payload_latched_off",
        "bus_undisturbed",
        "redundant_side_unaffected",
    }
)

CASE_FAMILIES = ("inrush", "undervoltage", "agreed_failure")

# Interface limits are never widened. These absorb the representation
# error of a quantity that lands exactly on its limit.
_RELATIVE_TOLERANCE = 1.0e-12
_ABSOLUTE_TOLERANCE = 1.0e-12


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _finite(value, label):
    if not _is_number(value) or not math.isfinite(float(value)):
        raise ValueError("%s must be a finite number, got %r" % (label, value))
    return float(value)


def _positive(value, label):
    number = _finite(value, label)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return number


def _non_negative(value, label):
    number = _finite(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _within(value, limit):
    """True when a quantity stays at or under its limit, absorbing the
    representation error of an exactly-on-limit result."""
    if value <= limit:
        return True
    return math.isclose(
        value, limit, rel_tol=_RELATIVE_TOLERANCE, abs_tol=_ABSOLUTE_TOLERANCE
    )


def _at_least(value, floor):
    """True when a quantity stays at or above its floor, absorbing the
    representation error of an exactly-on-floor result."""
    if value >= floor:
        return True
    return math.isclose(
        value, floor, rel_tol=_RELATIVE_TOLERANCE, abs_tol=1.0e-9
    )


def categorize_test_case(case_kind):
    """Family of one campaign case: "inrush", "undervoltage" or
    "agreed_failure". Raises ValueError for a kind that is not a
    clause 5.7.6 payload-to-bus interaction case."""
    if case_kind in INRUSH_CASE_KINDS:
        return "inrush"
    if case_kind in UNDERVOLTAGE_CASE_KINDS:
        return "undervoltage"
    if case_kind in FAILURE_CASE_KINDS:
        return "agreed_failure"
    raise ValueError(
        "unrecognized payload-bus interaction case kind %r under "
        "E-ST-20C clause 5.7.6" % (case_kind,)
    )


def required_case_fields(category):
    """Mandatory field set for a case family. Raises ValueError for an
    uncategorized family name."""
    if category not in REQUIRED_CASE_FIELDS:
        raise ValueError("unknown campaign case family %r" % (category,))
    return REQUIRED_CASE_FIELDS[category]


def missing_case_fields(category, declared):
    """Sorted list of mandatory fields the case sheet does not carry or
    leaves empty. Raises ValueError if the sheet is not a mapping."""
    required = required_case_fields(category)
    if not isinstance(declared, dict):
        raise ValueError(
            "declared case fields must be a mapping, got %r"
            % (type(declared).__name__,)
        )
    return sorted(
        field
        for field in required
        if field not in declared or declared[field] is None
    )


def peak_inrush_current_a(bus_voltage_v, limiter_resistance_ohm):
    """Peak charging current into the payload input capacitance, set by
    the bus voltage across the limiting element."""
    voltage = _positive(bus_voltage_v, "bus_voltage_v")
    resistance = _positive(limiter_resistance_ohm, "limiter_resistance_ohm")
    return voltage / resistance


def inrush_time_constant_s(limiter_resistance_ohm, load_capacitance_f):
    """Decay time constant of the inrush: the limiting resistance times
    the payload input capacitance."""
    resistance = _positive(limiter_resistance_ohm, "limiter_resistance_ohm")
    capacitance = _positive(load_capacitance_f, "load_capacitance_f")
    return resistance * capacitance


def inrush_time_above_a(peak_current_a, threshold_a, time_constant_s):
    """Time the exponentially decaying inrush spends above a current
    threshold. Zero when the peak never reaches the threshold."""
    peak = _positive(peak_current_a, "peak_current_a")
    threshold = _positive(threshold_a, "threshold_a")
    tau = _positive(time_constant_s, "time_constant_s")
    if _within(peak, threshold):
        return 0.0
    return tau * math.log(peak / threshold)


def evaluate_inrush_case(case):
    """Findings for one inrush case: peak against the interface
    allowance, time above the protection threshold against the trip
    delay, and settling time against any declared limit."""
    fields = case.get("declared_fields")
    missing = missing_case_fields("inrush", fields)
    if missing:
        return {
            "case_id": case.get("case_id"),
            "category": "inrush",
            "findings": [
                "inrush case %s is missing mandatory field %s"
                % (case.get("case_id"), field)
                for field in missing
            ],
        }
    peak = peak_inrush_current_a(
        fields["bus_voltage_v"], fields["limiter_resistance_ohm"]
    )
    tau = inrush_time_constant_s(
        fields["limiter_resistance_ohm"], fields["load_capacitance_f"]
    )
    trip_current = _positive(
        fields["protection_trip_current_a"], "protection_trip_current_a"
    )
    trip_delay = _non_negative(
        fields["protection_trip_delay_s"], "protection_trip_delay_s"
    )
    allowed_peak = _positive(
        fields["allowed_peak_inrush_a"], "allowed_peak_inrush_a"
    )
    time_above = inrush_time_above_a(peak, trip_current, tau)
    findings = []
    if not _within(peak, allowed_peak):
        findings.append(
            "inrush case %s: peak current %.3f A exceeds the %.3f A allowed at "
            "the interface" % (case.get("case_id"), peak, allowed_peak)
        )
    if not _within(time_above, trip_delay):
        findings.append(
            "inrush case %s: current stays above the %.3f A protection "
            "threshold for %.6f s, longer than the %.6f s trip delay"
            % (case.get("case_id"), trip_current, time_above, trip_delay)
        )
    settling = 5.0 * tau
    limit = fields.get("max_settling_time_s")
    if limit is not None:
        limit = _positive(limit, "max_settling_time_s")
        if not _within(settling, limit):
            findings.append(
                "inrush case %s: settling time %.6f s exceeds the declared "
                "%.6f s limit" % (case.get("case_id"), settling, limit)
            )
    return {
        "case_id": case.get("case_id"),
        "category": "inrush",
        "peak_current_a": peak,
        "time_constant_s": tau,
        "time_above_threshold_s": time_above,
        "settling_time_s": settling,
        "findings": findings,
    }


def transient_bus_sag_v(step_current_a, bus_capacitance_f, control_bandwidth_hz):
    """Bus voltage sag caused by a load step before the regulator loop
    recovers it: the step current over the bus capacitance times the
    angular control bandwidth."""
    step = _positive(step_current_a, "step_current_a")
    capacitance = _positive(bus_capacitance_f, "bus_capacitance_f")
    bandwidth = _positive(control_bandwidth_hz, "control_bandwidth_hz")
    return step / (2.0 * math.pi * bandwidth * capacitance)


def minimum_transient_bus_voltage_v(
    bus_voltage_v,
    step_current_a,
    bus_capacitance_f,
    control_bandwidth_hz,
    harness_resistance_ohm,
):
    """Lowest voltage the payload sees during a load step: the bus
    voltage less the loop sag and less the harness resistive drop."""
    voltage = _positive(bus_voltage_v, "bus_voltage_v")
    step = _positive(step_current_a, "step_current_a")
    resistance = _non_negative(harness_resistance_ohm, "harness_resistance_ohm")
    sag = transient_bus_sag_v(step, bus_capacitance_f, control_bandwidth_hz)
    return voltage - sag - step * resistance


def evaluate_undervoltage_case(case):
    """Findings for one undervoltage case: the remaining bus voltage
    against the bus lower limit and the payload undervoltage lockout,
    and the recharge time against any declared ride-through."""
    fields = case.get("declared_fields")
    missing = missing_case_fields("undervoltage", fields)
    if missing:
        return {
            "case_id": case.get("case_id"),
            "category": "undervoltage",
            "findings": [
                "undervoltage case %s is missing mandatory field %s"
                % (case.get("case_id"), field)
                for field in missing
            ],
        }
    sag = transient_bus_sag_v(
        fields["step_current_a"],
        fields["bus_capacitance_f"],
        fields["control_bandwidth_hz"],
    )
    minimum = minimum_transient_bus_voltage_v(
        fields["bus_voltage_v"],
        fields["step_current_a"],
        fields["bus_capacitance_f"],
        fields["control_bandwidth_hz"],
        fields["harness_resistance_ohm"],
    )
    lower_limit = _positive(fields["bus_lower_limit_v"], "bus_lower_limit_v")
    lockout = _positive(
        fields["payload_undervoltage_lockout_v"], "payload_undervoltage_lockout_v"
    )
    findings = []
    if not _at_least(minimum, lower_limit):
        findings.append(
            "undervoltage case %s: transient minimum %.4f V is below the "
            "%.4f V bus lower limit" % (case.get("case_id"), minimum, lower_limit)
        )
    if not _at_least(minimum, lockout):
        findings.append(
            "undervoltage case %s: transient minimum %.4f V is below the "
            "%.4f V payload undervoltage lockout"
            % (case.get("case_id"), minimum, lockout)
        )
    recovery_current = fields.get("source_recovery_current_a")
    ride_through = fields.get("payload_ride_through_s")
    recharge = None
    if recovery_current is not None and ride_through is not None:
        recovery_current = _positive(
            recovery_current, "source_recovery_current_a"
        )
        ride_through = _positive(ride_through, "payload_ride_through_s")
        recharge = (
            _positive(fields["bus_capacitance_f"], "bus_capacitance_f")
            * sag
            / recovery_current
        )
        if not _within(recharge, ride_through):
            findings.append(
                "undervoltage case %s: recharge takes %.6f s, longer than the "
                "%.6f s payload ride-through"
                % (case.get("case_id"), recharge, ride_through)
            )
    return {
        "case_id": case.get("case_id"),
        "category": "undervoltage",
        "sag_v": sag,
        "minimum_bus_voltage_v": minimum,
        "recharge_time_s": recharge,
        "findings": findings,
    }


def fault_current_a(bus_voltage_v, fault_resistance_ohm, harness_resistance_ohm):
    """Steady fault current: the bus voltage over the sum of the fault
    and harness resistance. Raises ValueError for a zero total path."""
    voltage = _positive(bus_voltage_v, "bus_voltage_v")
    fault = _non_negative(fault_resistance_ohm, "fault_resistance_ohm")
    harness = _non_negative(harness_resistance_ohm, "harness_resistance_ohm")
    total = fault + harness
    if total <= 0.0:
        raise ValueError(
            "fault and harness resistance sum to zero; the fault path needs a "
            "finite resistance"
        )
    return voltage / total


def protection_clearing_time_s(
    current_a, rated_current_a, i2t_a2s, minimum_clearing_time_s
):
    """Clearing time of an inverse-square protection device, floored by
    its own minimum response time. Positive infinity when the current
    does not exceed the device rating, because the device never trips."""
    current = _positive(current_a, "current_a")
    rated = _positive(rated_current_a, "rated_current_a")
    energy_constant = _positive(i2t_a2s, "i2t_a2s")
    floor = _non_negative(minimum_clearing_time_s, "minimum_clearing_time_s")
    if _within(current, rated):
        return math.inf
    return max(energy_constant / (current * current), floor)


def let_through_energy_a2s(current_a, clearing_time_s):
    """Energy the protection lets through, as current squared times the
    clearing time. Raises ValueError for a non-clearing fault."""
    current = _positive(current_a, "current_a")
    if not math.isfinite(clearing_time_s):
        raise ValueError(
            "let-through energy is undefined for a fault the protection never "
            "clears"
        )
    duration = _non_negative(clearing_time_s, "clearing_time_s")
    return current * current * duration


def evaluate_failure_case(case, agreed_failure_cases):
    """Findings for one agreed failure case: membership of the agreed
    list, clearing time against containment, let-through energy against
    the allowance, and a recognised containment outcome."""
    if not isinstance(agreed_failure_cases, (list, tuple, set, frozenset)):
        raise ValueError("agreed_failure_cases must be a list of case kinds")
    case_id = case.get("case_id")
    findings = []
    kind = case.get("case_kind")
    if kind not in agreed_failure_cases:
        findings.append(
            "failure case %s exercises %r, which is not on the agreed failure "
            "case list" % (case_id, kind)
        )
    fields = case.get("declared_fields")
    missing = missing_case_fields("agreed_failure", fields)
    if missing:
        findings.extend(
            "failure case %s is missing mandatory field %s" % (case_id, field)
            for field in missing
        )
        return {"case_id": case_id, "category": "agreed_failure", "findings": findings}
    current = fault_current_a(
        fields["bus_voltage_v"],
        fields["fault_resistance_ohm"],
        fields["harness_resistance_ohm"],
    )
    clearing = protection_clearing_time_s(
        current,
        fields["protection_rated_current_a"],
        fields["protection_i2t_a2s"],
        fields["protection_minimum_clearing_time_s"],
    )
    containment = _positive(fields["containment_time_s"], "containment_time_s")
    energy = None
    if not math.isfinite(clearing):
        findings.append(
            "failure case %s: fault current %.3f A does not exceed the %.3f A "
            "protection rating, so the fault is never cleared"
            % (case_id, current, fields["protection_rated_current_a"])
        )
    else:
        if not _within(clearing, containment):
            findings.append(
                "failure case %s: clearing time %.6f s exceeds the %.6f s "
                "containment requirement" % (case_id, clearing, containment)
            )
        energy = let_through_energy_a2s(current, clearing)
        allowance = fields.get("allowed_let_through_a2s")
        if allowance is not None:
            allowance = _positive(allowance, "allowed_let_through_a2s")
            if not _within(energy, allowance):
                findings.append(
                    "failure case %s: let-through energy %.4f A2s exceeds the "
                    "%.4f A2s allowance" % (case_id, energy, allowance)
                )
    outcome = fields["containment_outcome"]
    if outcome not in RECOGNISED_CONTAINMENT_OUTCOMES:
        findings.append(
            "failure case %s: containment outcome %r is not one of the "
            "recognised results" % (case_id, outcome)
        )
    return {
        "case_id": case_id,
        "category": "agreed_failure",
        "fault_current_a": current,
        "clearing_time_s": clearing,
        "let_through_a2s": energy,
        "findings": findings,
    }


def verify_payload_bus_interaction(campaign):
    """Clause 5.7.6 verification review of one payload-to-bus campaign.
    Raises ValueError for a malformed campaign."""
    if not isinstance(campaign, dict):
        raise ValueError("campaign must be a mapping")
    payload_id = campaign.get("payload_id")
    if not isinstance(payload_id, str) or not payload_id.strip():
        raise ValueError("campaign needs a non-empty payload_id")
    cases = campaign.get("cases")
    if not isinstance(cases, (list, tuple)) or not cases:
        raise ValueError("campaign needs a non-empty cases list")
    agreed = campaign.get("agreed_failure_cases")
    if not isinstance(agreed, (list, tuple)) or not agreed:
        raise ValueError(
            "campaign needs a non-empty agreed_failure_cases list; clause 5.7.6 "
            "anchors the failure campaign to the agreed set"
        )
    for kind in agreed:
        if kind not in FAILURE_CASE_KINDS:
            raise ValueError(
                "agreed failure case %r is not a recognised failure kind" % (kind,)
            )
    results = []
    case_findings = []
    seen_ids = set()
    covered = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("every campaign case must be a mapping")
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("every campaign case needs a non-empty case_id")
        if case_id in seen_ids:
            raise ValueError("duplicate campaign case_id %r" % (case_id,))
        seen_ids.add(case_id)
        category = categorize_test_case(case.get("case_kind"))
        covered.add(category)
        if category == "inrush":
            result = evaluate_inrush_case(case)
        elif category == "undervoltage":
            result = evaluate_undervoltage_case(case)
        else:
            result = evaluate_failure_case(case, agreed)
        results.append(result)
        case_findings.extend(result["findings"])
    coverage_findings = [
        "campaign has no %s case on record" % family
        for family in CASE_FAMILIES
        if family not in covered
    ]
    return {
        "payload_id": payload_id,
        "case_count": len(results),
        "families_covered": sorted(covered),
        "case_results": results,
        "coverage_findings": coverage_findings,
        "case_findings": case_findings,
        "verified": not coverage_findings and not case_findings,
    }
