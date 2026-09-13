#!/usr/bin/env python3
"""ECSS-E-ST-20-07C clause 4.2.11.3 -- external ground connection provisions.

Deterministic, offline, standard-library-only logic for the charge-equalization
attachment points used before a handling or mating operation: qualification of
each provision (bond back to structure, current-limiting bleed resistance,
marking, reachability) and, per operation, the resistance-capacitance decay of
the item's stored potential, the residual potential after the planned dwell,
the peak equalization current and the bleed-resistance window that satisfies
both the current limit and the available dwell.

The procedure is a paraphrase; no standard text is reproduced.
"""

import math

PROVISION_STYLES = (
    "grounding-stud",
    "banana-jack-receptacle",
    "clamp-lug",
)

# Withstand potential, in volts, by electrostatic susceptibility category.
SUSCEPTIBILITY_WITHSTAND_V = {
    "category-0": 250.0,
    "category-1a": 500.0,
    "category-1b": 1000.0,
    "category-2": 2000.0,
}

# The residual is derated below the withstand so the item is not sitting at
# its limit when the operator makes contact.
RESIDUAL_DERATING_FRACTION = 0.1

# Allowance for the provision's own bond back to structure, in milliohm.
PROVISION_BOND_ALLOWANCE_MOHM = 10.0

# A soft-ground lead carries a series resistor; below this the lead is a hard
# short and the equalization becomes a single discharge through the item.
MIN_BLEED_RESISTANCE_OHM = 1.0e5

# Peak equalization current the provision is allowed to pass, in amperes.
MAX_EQUALIZATION_CURRENT_A = 5.0e-3

# Absorbs float representation error where a quantity physically sits on its
# limit. It never widens the engineering limit.
COMPARISON_REL_TOL = 1e-9
COMPARISON_ABS_TOL = 1e-15


def _within(value, limit):
    """True when ``value`` does not exceed ``limit``.

    An exponential decay evaluated at a logarithm-derived dwell lands a few
    units in the last place either side of the target. That representation
    error is absorbed here; the threshold itself is not moved.
    """
    if value <= limit:
        return True
    return math.isclose(
        value, limit, rel_tol=COMPARISON_REL_TOL, abs_tol=COMPARISON_ABS_TOL
    )


def normalize_token(raw, allowed, label):
    """Return the canonical token for ``raw`` or raise ValueError."""
    if not isinstance(raw, str):
        raise ValueError("%s must be a string, got %r" % (label, raw))
    token = raw.strip().lower()
    if not token:
        raise ValueError("%s must not be empty" % label)
    if token not in allowed:
        raise ValueError(
            "unknown %s %r; expected one of %s"
            % (label, raw, ", ".join(sorted(allowed)))
        )
    return token


def _number(raw, label, minimum=None, strict=False):
    """Validate a finite magnitude against an optional lower bound."""
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, raw))
    value = float(raw)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite, got %r" % (label, raw))
    if minimum is not None:
        if strict and value <= minimum:
            raise ValueError("%s must be greater than %g, got %r" % (label, minimum, raw))
        if not strict and value < minimum:
            raise ValueError("%s must not be below %g, got %r" % (label, minimum, raw))
    return value


def time_constant_s(resistance_ohm, capacitance_f):
    """Equalization time constant R x C, in seconds."""
    resistance = _number(resistance_ohm, "bleed resistance_ohm", 0.0, strict=True)
    capacitance = _number(capacitance_f, "capacitance_f", 0.0, strict=True)
    return resistance * capacitance


def residual_potential_v(initial_v, resistance_ohm, capacitance_f, dwell_s):
    """Potential remaining after ``dwell_s`` of resistance-capacitance decay."""
    initial = _number(initial_v, "initial_potential_v", 0.0)
    dwell = _number(dwell_s, "dwell_s", 0.0)
    tau = time_constant_s(resistance_ohm, capacitance_f)
    return initial * math.exp(-dwell / tau)


def required_dwell_s(initial_v, target_v, resistance_ohm, capacitance_f):
    """Dwell needed to decay from ``initial_v`` down to ``target_v``."""
    initial = _number(initial_v, "initial_potential_v", 0.0, strict=True)
    target = _number(target_v, "target_potential_v", 0.0, strict=True)
    if target >= initial:
        raise ValueError(
            "target potential %.6g V is not below the initial potential %.6g V"
            % (target, initial)
        )
    tau = time_constant_s(resistance_ohm, capacitance_f)
    return tau * math.log(initial / target)


def peak_equalization_current_a(initial_v, resistance_ohm):
    """Initial current drawn through the bleed resistance, in amperes."""
    initial = _number(initial_v, "initial_potential_v", 0.0)
    resistance = _number(resistance_ohm, "bleed resistance_ohm", 0.0, strict=True)
    return initial / resistance


def residual_threshold_v(susceptibility_category):
    """Derated residual threshold for an electrostatic susceptibility category."""
    category = normalize_token(
        susceptibility_category,
        tuple(SUSCEPTIBILITY_WITHSTAND_V),
        "susceptibility category",
    )
    return SUSCEPTIBILITY_WITHSTAND_V[category] * RESIDUAL_DERATING_FRACTION


def bleed_resistance_window_ohm(
    initial_v,
    capacitance_f,
    available_dwell_s,
    target_v,
    current_limit_a=MAX_EQUALIZATION_CURRENT_A,
):
    """Bleed-resistance window that satisfies the current limit and the dwell.

    Lower bound from the peak current, upper bound from the dwell the
    operation can hold. An empty window means no resistor value satisfies
    both and the dwell or the initial potential has to change instead.
    """
    initial = _number(initial_v, "initial_potential_v", 0.0, strict=True)
    target = _number(target_v, "target_potential_v", 0.0, strict=True)
    if target >= initial:
        raise ValueError(
            "target potential %.6g V is not below the initial potential %.6g V"
            % (target, initial)
        )
    capacitance = _number(capacitance_f, "capacitance_f", 0.0, strict=True)
    dwell = _number(available_dwell_s, "available_dwell_s", 0.0, strict=True)
    limit = _number(current_limit_a, "current_limit_a", 0.0, strict=True)
    minimum = initial / limit
    maximum = dwell / (capacitance * math.log(initial / target))
    feasible = minimum <= maximum or math.isclose(
        minimum, maximum, rel_tol=COMPARISON_REL_TOL
    )
    return {
        "minimum_ohm": minimum,
        "maximum_ohm": maximum,
        "feasible": feasible,
    }


def qualify_provision(record):
    """Qualify one external ground connection provision record."""
    if not isinstance(record, dict):
        raise ValueError("provision record must be a mapping, got %r" % (record,))
    provision_id = record.get("id")
    if not isinstance(provision_id, str) or not provision_id.strip():
        raise ValueError("provision record needs a non-empty 'id'")
    style = normalize_token(record.get("style"), PROVISION_STYLES, "provision style")
    bond_mohm = _number(
        record.get("bond_to_structure_mohm"), "bond_to_structure_mohm", 0.0
    )
    bleed_ohm = _number(record.get("bleed_resistance_ohm"), "bleed_resistance_ohm", 0.0)
    marked = record.get("marking_present")
    if not isinstance(marked, bool):
        raise ValueError("marking_present must be a boolean, got %r" % (marked,))
    raw_configs = record.get("reachable_configurations", [])
    if not isinstance(raw_configs, (list, tuple)):
        raise ValueError(
            "reachable_configurations must be a sequence, got %r" % (raw_configs,)
        )
    configurations = []
    for item in raw_configs:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("reachable configuration must be a non-empty string")
        configurations.append(item.strip().lower())
    findings = []
    if not _within(bond_mohm, PROVISION_BOND_ALLOWANCE_MOHM):
        findings.append("provision-bond-to-structure-exceeds-allowance")
    if bleed_ohm < MIN_BLEED_RESISTANCE_OHM:
        findings.append("provision-lacks-current-limiting-bleed-resistance")
    if not marked:
        findings.append("provision-not-marked-for-the-operator")
    if not configurations:
        findings.append("provision-has-no-reachable-configuration")
    return {
        "id": provision_id.strip(),
        "style": style,
        "bond_to_structure_mohm": bond_mohm,
        "bleed_resistance_ohm": bleed_ohm,
        "reachable_configurations": configurations,
        "findings": findings,
        "qualified": not findings,
    }


def build_provision_catalogue(records):
    """Qualify every provision record and index it by identifier."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("provision records must be a non-empty sequence")
    catalogue = {}
    for record in records:
        qualified = qualify_provision(record)
        if qualified["id"] in catalogue:
            raise ValueError("duplicate provision id %r" % qualified["id"])
        catalogue[qualified["id"]] = qualified
    return catalogue


def evaluate_operation(record, catalogue):
    """Evaluate one handling or mating operation against its provision."""
    if not isinstance(record, dict):
        raise ValueError("operation record must be a mapping, got %r" % (record,))
    if not isinstance(catalogue, dict) or not catalogue:
        raise ValueError("provision catalogue must be a non-empty mapping")
    operation_id = record.get("id")
    if not isinstance(operation_id, str) or not operation_id.strip():
        raise ValueError("operation record needs a non-empty 'id'")
    provision_id = record.get("provision_id")
    if not isinstance(provision_id, str) or provision_id.strip() not in catalogue:
        raise ValueError(
            "operation %r names provision %r which is not in the catalogue"
            % (operation_id, provision_id)
        )
    provision = catalogue[provision_id.strip()]
    configuration = record.get("configuration")
    if not isinstance(configuration, str) or not configuration.strip():
        raise ValueError("operation record needs a non-empty 'configuration'")
    configuration = configuration.strip().lower()
    initial = _number(record.get("initial_potential_v"), "initial_potential_v", 0.0)
    capacitance = _number(
        record.get("item_capacitance_f"), "item_capacitance_f", 0.0, strict=True
    )
    dwell = _number(record.get("dwell_s"), "dwell_s", 0.0)
    threshold = residual_threshold_v(record.get("susceptibility_category"))
    resistance = provision["bleed_resistance_ohm"]
    if resistance <= 0.0:
        raise ValueError(
            "provision %r has no bleed resistance, so no decay can be computed"
            % provision["id"]
        )
    tau = time_constant_s(resistance, capacitance)
    residual = residual_potential_v(initial, resistance, capacitance, dwell)
    current = peak_equalization_current_a(initial, resistance)
    findings = []
    if configuration not in provision["reachable_configurations"]:
        findings.append("provision-not-reachable-in-operation-configuration")
    if not _within(residual, threshold):
        findings.append("equalization-dwell-too-short-for-residual-threshold")
    if not _within(current, MAX_EQUALIZATION_CURRENT_A):
        findings.append("peak-equalization-current-above-limit")
    needed = None
    window = None
    if initial > threshold:
        needed = required_dwell_s(initial, threshold, resistance, capacitance)
        if dwell > 0.0:
            window = bleed_resistance_window_ohm(
                initial, capacitance, dwell, threshold
            )
        if window is not None and not window["feasible"]:
            findings.append("no-feasible-bleed-resistance-window")
    return {
        "id": operation_id.strip(),
        "provision_id": provision["id"],
        "time_constant_s": tau,
        "residual_potential_v": residual,
        "residual_threshold_v": threshold,
        "required_dwell_s": needed,
        "peak_current_a": current,
        "bleed_resistance_window_ohm": window,
        "findings": findings,
        "compliant": not findings,
    }


def assess_ground_connection_provisions(provision_records, operation_records):
    """Full clause 4.2.11.3 verdict for a provision set and its operations."""
    catalogue = build_provision_catalogue(provision_records)
    if not isinstance(operation_records, (list, tuple)):
        raise ValueError("operation records must be a sequence")
    operations = [evaluate_operation(rec, catalogue) for rec in operation_records]
    findings = []
    for provision_id in sorted(catalogue):
        for finding in catalogue[provision_id]["findings"]:
            findings.append("%s: %s" % (provision_id, finding))
    for entry in operations:
        for finding in entry["findings"]:
            findings.append("%s: %s" % (entry["id"], finding))
    residuals = [entry["residual_potential_v"] for entry in operations]
    return {
        "provisions": catalogue,
        "operations": operations,
        "operation_count": len(operations),
        "worst_residual_v": max(residuals) if residuals else None,
        "findings": findings,
        "compliant": not findings,
    }


def summarize_assessment(report):
    """One-line summary of a provision assessment report."""
    if not isinstance(report, dict) or "compliant" not in report:
        raise ValueError("summary needs an assessment report mapping")
    verdict = "COMPLIANT" if report["compliant"] else "NON-COMPLIANT"
    worst = report["worst_residual_v"]
    worst_text = "n/a" if worst is None else "%.3f V" % worst
    return "%s: %d provision(s), %d operation(s), worst residual=%s, %d finding(s)" % (
        verdict,
        len(report["provisions"]),
        report["operation_count"],
        worst_text,
        len(report["findings"]),
    )
