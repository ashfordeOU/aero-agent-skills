#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.9 electrical subsystem safety conformance
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires payloads and electrical
subsystems to conform to the space product assurance safety standard,
so the electrical design has to be shown against a hazard-driven
safety argument rather than against its own performance requirements
alone. This module implements the checkable part of that linkage:
categorization of an electrical hazard into a hazard family, the
severity that follows from the credible consequence, the failure
tolerance and the number of independent monitored inhibits that
severity demands, the residual charge a stored-energy source still
holds after its bleed path has run, and the verification method and
closure record every hazard has to carry. It does not write the safety
data package, does not assign probabilities, and does not perform a
fault-tree cut-set search.
"""

import math

# Boundary comparisons absorb floating-point representation error only;
# the safety threshold itself is never widened.
COMPARISON_REL_TOL = 1e-9
COMPARISON_ABS_TOL = 1e-12

HAZARD_FAMILIES = {
    "exposed_live_conductor": "shock_and_touch",
    "insulation_breakdown_to_chassis": "shock_and_touch",
    "ground_fault_return_path": "shock_and_touch",
    "bulk_capacitor_residual_charge": "stored_energy",
    "inductive_flyback_energy": "stored_energy",
    "high_voltage_filter_bank": "stored_energy",
    "battery_cell_internal_short": "thermal_runaway",
    "battery_overcharge": "thermal_runaway",
    "battery_external_short": "thermal_runaway",
    "pyrotechnic_firing_circuit": "inadvertent_initiation",
    "deployment_actuator_command_path": "inadvertent_initiation",
    "rf_transmitter_field_exposure": "radiated_energy",
    "laser_source_emission": "radiated_energy",
}

CONSEQUENCE_SEVERITY = {
    "loss_of_life_or_vehicle": "catastrophic",
    "loss_of_launcher_or_facility": "catastrophic",
    "permanent_disabling_injury": "catastrophic",
    "loss_of_mission": "critical",
    "reversible_injury_to_personnel": "critical",
    "loss_of_a_redundant_string": "marginal",
    "degraded_performance": "marginal",
}

# Failure tolerance the severity demands, and the count of independent
# inhibits that tolerance translates into (tolerance plus one).
SEVERITY_FAILURE_TOLERANCE = {
    "catastrophic": 2,
    "critical": 1,
    "marginal": 0,
}

RECOGNIZED_VERIFICATION_METHODS = frozenset(
    {
        "safety_test",
        "safety_analysis",
        "design_inspection",
        "review_of_design",
        "similarity_to_flown_design",
    }
)

_HAZARD_REQUIRED_KEYS = ("hazard_id", "hazard_kind", "consequence")
_INHIBIT_REQUIRED_KEYS = ("inhibit_id", "independent", "monitored")
_STORED_ENERGY_REQUIRED_KEYS = (
    "capacitance_f",
    "operating_voltage_v",
    "bleed_resistance_ohm",
    "safe_touch_voltage_v",
    "safe_energy_j",
    "required_bleed_time_s",
)
_VERIFICATION_REQUIRED_KEYS = ("method", "closed", "closure_reference")


def _within(value, limit):
    """True when value does not exceed limit. An exact-boundary case is
    accepted even when the computed value sits a few units in the last
    place above the limit through the arithmetic that produced it."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=COMPARISON_REL_TOL, abs_tol=COMPARISON_ABS_TOL
    )


def _require_keys(record, keys, what):
    missing = [k for k in keys if k not in record]
    if missing:
        raise ValueError(
            "%s record is missing required key(s): %s"
            % (what, ", ".join(sorted(missing)))
        )


def categorize_electrical_hazard(hazard_kind):
    """Hazard family for an electrical hazard kind: shock_and_touch,
    stored_energy, thermal_runaway, inadvertent_initiation or
    radiated_energy. Raises ValueError for a kind that is not a
    clause 5.9 electrical hazard."""
    try:
        return HAZARD_FAMILIES[hazard_kind]
    except (KeyError, TypeError):
        raise ValueError(
            "unrecognized electrical hazard kind %r under "
            "E-ST-20C clause 5.9" % (hazard_kind,)
        )


def severity_from_consequence(consequence):
    """Severity band for a credible worst-case consequence:
    catastrophic, critical or marginal. Raises ValueError for a
    consequence outside the recognized set -- an unmapped consequence
    is an unfinished hazard record, not a marginal one."""
    try:
        return CONSEQUENCE_SEVERITY[consequence]
    except (KeyError, TypeError):
        raise ValueError(
            "unrecognized hazard consequence %r; map it to a severity "
            "band before the tolerance check" % (consequence,)
        )


def required_failure_tolerance(severity):
    """Number of independent failures the design must survive without
    the hazard occurring: two for catastrophic, one for critical, none
    for marginal (which is controlled by design instead). Raises
    ValueError for an unrecognized severity band."""
    try:
        return SEVERITY_FAILURE_TOLERANCE[severity]
    except (KeyError, TypeError):
        raise ValueError("unrecognized severity band %r" % (severity,))


def required_independent_inhibits(severity):
    """Count of independent inhibits the severity demands: one more
    than the failure tolerance, because the last inhibit still has to
    be standing after the tolerated failures. Marginal hazards need
    none. Raises ValueError through required_failure_tolerance."""
    tolerance = required_failure_tolerance(severity)
    if tolerance == 0:
        return 0
    return tolerance + 1


def inhibit_findings(hazard_id, severity, inhibits):
    """Findings (empty list when adequate) for the inhibit set guarding
    one hazard. inhibits: iterable of mappings with inhibit_id,
    independent and monitored. Raises ValueError for an unrecognized
    severity or an inhibit record missing a key."""
    required = required_independent_inhibits(severity)
    findings = []
    independent = []
    for inhibit in inhibits:
        _require_keys(inhibit, _INHIBIT_REQUIRED_KEYS, "inhibit")
        if inhibit["independent"]:
            independent.append(inhibit)
        else:
            findings.append(
                "hazard %s: inhibit %s shares a failure cause with another "
                "inhibit, so it does not add tolerance"
                % (hazard_id, inhibit["inhibit_id"])
            )
        if not inhibit["monitored"]:
            findings.append(
                "hazard %s: inhibit %s carries no monitoring, so its state "
                "cannot be verified before the hazardous operation"
                % (hazard_id, inhibit["inhibit_id"])
            )
    if len(independent) < required:
        findings.append(
            "hazard %s: %d independent inhibit(s) against the %d a %s hazard "
            "requires" % (hazard_id, len(independent), required, severity)
        )
    return findings


def capacitor_stored_energy(capacitance_f, voltage_v):
    """Energy in joules held by a capacitance at a given voltage: half
    the capacitance times the voltage squared. Raises ValueError for a
    non-positive capacitance or a negative voltage."""
    if capacitance_f <= 0:
        raise ValueError("capacitance_f must be > 0")
    if voltage_v < 0:
        raise ValueError("voltage_v must be >= 0")
    return 0.5 * capacitance_f * voltage_v * voltage_v


def residual_voltage_after_bleed(
    initial_voltage_v, capacitance_f, bleed_resistance_ohm, elapsed_s
):
    """Voltage remaining on a capacitance after its bleed resistor has
    drained it for elapsed_s seconds, following the exponential decay
    of the resistance-capacitance product. Raises ValueError for a
    negative initial voltage, a non-positive capacitance or bleed
    resistance, or a negative elapsed time."""
    if initial_voltage_v < 0:
        raise ValueError("initial_voltage_v must be >= 0")
    if capacitance_f <= 0:
        raise ValueError("capacitance_f must be > 0")
    if bleed_resistance_ohm <= 0:
        raise ValueError("bleed_resistance_ohm must be > 0")
    if elapsed_s < 0:
        raise ValueError("elapsed_s must be >= 0")
    tau = bleed_resistance_ohm * capacitance_f
    return initial_voltage_v * math.exp(-elapsed_s / tau)


def time_to_safe_voltage(
    initial_voltage_v, safe_voltage_v, capacitance_f, bleed_resistance_ohm
):
    """Seconds the bleed path needs to bring the stored charge down to
    the safe touch voltage. Returns zero when the source already sits
    at or below that voltage. Raises ValueError for a non-positive safe
    voltage or through residual_voltage_after_bleed's own checks."""
    if safe_voltage_v <= 0:
        raise ValueError("safe_voltage_v must be > 0")
    if initial_voltage_v < 0:
        raise ValueError("initial_voltage_v must be >= 0")
    if capacitance_f <= 0:
        raise ValueError("capacitance_f must be > 0")
    if bleed_resistance_ohm <= 0:
        raise ValueError("bleed_resistance_ohm must be > 0")
    if initial_voltage_v <= safe_voltage_v:
        return 0.0
    tau = bleed_resistance_ohm * capacitance_f
    return tau * math.log(initial_voltage_v / safe_voltage_v)


def stored_energy_findings(hazard_id, stored_energy):
    """Findings (empty list when safe) for a stored-energy source
    behind one hazard. Required keys: capacitance_f,
    operating_voltage_v, bleed_resistance_ohm, safe_touch_voltage_v,
    safe_energy_j, required_bleed_time_s. Raises ValueError for a
    missing key or an out-of-range value."""
    _require_keys(stored_energy, _STORED_ENERGY_REQUIRED_KEYS, "stored energy")
    findings = []
    if stored_energy["safe_energy_j"] < 0:
        raise ValueError("safe_energy_j must be >= 0")
    if stored_energy["required_bleed_time_s"] < 0:
        raise ValueError("required_bleed_time_s must be >= 0")
    residual_v = residual_voltage_after_bleed(
        stored_energy["operating_voltage_v"],
        stored_energy["capacitance_f"],
        stored_energy["bleed_resistance_ohm"],
        stored_energy["required_bleed_time_s"],
    )
    safe_v = stored_energy["safe_touch_voltage_v"]
    if safe_v <= 0:
        raise ValueError("safe_touch_voltage_v must be > 0")
    if not _within(residual_v, safe_v):
        findings.append(
            "hazard %s: %.3f V still on the source after the %.1f s bleed "
            "period, above the %.3f V safe touch limit"
            % (
                hazard_id,
                residual_v,
                stored_energy["required_bleed_time_s"],
                safe_v,
            )
        )
    residual_j = capacitor_stored_energy(
        stored_energy["capacitance_f"], residual_v
    )
    if not _within(residual_j, stored_energy["safe_energy_j"]):
        findings.append(
            "hazard %s: %.4f J of residual stored energy against the %.4f J "
            "safe limit" % (hazard_id, residual_j, stored_energy["safe_energy_j"])
        )
    needed_s = time_to_safe_voltage(
        stored_energy["operating_voltage_v"],
        safe_v,
        stored_energy["capacitance_f"],
        stored_energy["bleed_resistance_ohm"],
    )
    if not _within(needed_s, stored_energy["required_bleed_time_s"]):
        findings.append(
            "hazard %s: bleed path needs %.2f s to reach the safe touch "
            "voltage, longer than the %.2f s the procedure allows"
            % (hazard_id, needed_s, stored_energy["required_bleed_time_s"])
        )
    return findings


def verification_findings(hazard_id, verification):
    """Findings (empty list when complete) for the safety verification
    record of one hazard. Required keys: method, closed,
    closure_reference. Raises ValueError for a missing key or a method
    outside the recognized set."""
    _require_keys(verification, _VERIFICATION_REQUIRED_KEYS, "verification")
    method = verification["method"]
    if method not in RECOGNIZED_VERIFICATION_METHODS:
        raise ValueError(
            "unrecognized safety verification method %r for hazard %s"
            % (method, hazard_id)
        )
    findings = []
    if not verification["closed"]:
        findings.append(
            "hazard %s: safety verification by %s is still open"
            % (hazard_id, method)
        )
    reference = verification["closure_reference"]
    if not reference or not str(reference).strip():
        findings.append(
            "hazard %s: no closure reference on record, so the %s result "
            "cannot be traced" % (hazard_id, method)
        )
    return findings


def review_hazard(hazard):
    """Full clause 5.9 review of one hazard record. Required keys:
    hazard_id, hazard_kind, consequence. Optional keys: inhibits,
    stored_energy, verification. Returns a mapping carrying the family,
    severity, required tolerance and inhibit count, the three finding
    lists and a conformant flag. Raises ValueError for a missing key or
    an unrecognized kind, consequence or method."""
    _require_keys(hazard, _HAZARD_REQUIRED_KEYS, "hazard")
    hazard_id = hazard["hazard_id"]
    family = categorize_electrical_hazard(hazard["hazard_kind"])
    severity = severity_from_consequence(hazard["consequence"])
    inhibits = inhibit_findings(hazard_id, severity, hazard.get("inhibits", []))
    energy = []
    if "stored_energy" in hazard:
        energy = stored_energy_findings(hazard_id, hazard["stored_energy"])
    verification = []
    if "verification" in hazard:
        verification = verification_findings(hazard_id, hazard["verification"])
    else:
        verification = [
            "hazard %s: no safety verification record attached" % hazard_id
        ]
    return {
        "hazard_id": hazard_id,
        "family": family,
        "severity": severity,
        "required_failure_tolerance": required_failure_tolerance(severity),
        "required_independent_inhibits": required_independent_inhibits(severity),
        "inhibit_findings": inhibits,
        "stored_energy_findings": energy,
        "verification_findings": verification,
        "conformant": not (inhibits or energy or verification),
    }


def aggregate_safety_conformance_review(subsystem):
    """Clause 5.9 conformance review of a payload or electrical
    subsystem. subsystem keys: subsystem_id, plus an optional hazards
    list of hazard records. Returns a mapping of the per-hazard reviews,
    the flat finding list and a conformant flag that is true only when
    no hazard carries a finding. Raises ValueError for a missing
    subsystem_id or through the per-hazard checks."""
    if "subsystem_id" not in subsystem:
        raise ValueError(
            "subsystem record is missing required key: subsystem_id"
        )
    reviews = [review_hazard(h) for h in subsystem.get("hazards", [])]
    findings = []
    for review in reviews:
        findings.extend(review["inhibit_findings"])
        findings.extend(review["stored_energy_findings"])
        findings.extend(review["verification_findings"])
    return {
        "subsystem_id": subsystem["subsystem_id"],
        "hazard_reviews": reviews,
        "findings": findings,
        "conformant": not findings,
    }
