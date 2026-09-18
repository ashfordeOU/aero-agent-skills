#!/usr/bin/env python3
"""Bias condition under which output impedance is measured and reported.

Anchor: ECSS-E-ST-20-20C clause 5.2.17.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An output impedance figure is meaningless without the operating point it
was taken at. The series element of a protection device is a controlled
semiconductor, not a resistor: its small-signal behaviour, and therefore
the impedance the load behind it sees, depends on how hard that element
is being driven. The clause pins that operating point down by naming the
voltage the device drops between its input and its output at the moment
the data is taken, so two curves from two suppliers can be compared at
all.

A bias record is therefore reviewable only when it is:

    referenced   its declared drop agrees with the reference bias point
                 the project fixed for the whole characterisation
    consistent   that declared drop agrees with the drop the reported
                 load current and series resistance actually imply, so
                 the number was measured and not copied from the header
    in window    inside the drop range the device is meant to be
                 operated over -- too small and the element is barely
                 conducting, too large and it is closer to limitation
                 than to its normal operating point
    common       the same reference drop across every reported class,
                 since a family curve compared at different bias points
                 is not a family curve
    survivable   the dissipation the drop implies at that current is
                 inside what the device can shed

The reference tolerance, the consistency tolerance, the operating
window, the dissipation limit and the bus-share advisory ceiling are a
declared project policy, not physical constants; a project substitutes
its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

RECORD_FIELDS = (
    "class_name",
    "declared_drop_v",
    "load_current_a",
    "series_resistance_ohm",
    "bus_voltage_v",
)

VERDICT_COMPLIANT = "bias-condition-compliant"
VERDICT_NONCOMPLIANT = "bias-condition-noncompliant"

FINDING_REFERENCE = "declared-drop-away-from-the-reference-bias-point"
FINDING_CONSISTENCY = "declared-drop-inconsistent-with-current-and-series-resistance"
FINDING_WINDOW = "declared-drop-outside-the-device-operating-window"
FINDING_DISSIPATION = "implied-dissipation-above-the-device-limit"
FINDING_COMMONALITY = "reported-classes-do-not-share-one-bias-point"

ADVISORY_BUS_SHARE = "drop-share-of-the-bus-voltage-above-the-advisory-ceiling"

DEFAULT_BIAS_POLICY = {
    "reference_drop_rel_tol": 0.02,
    "drop_consistency_rel_tol": 0.05,
    "min_operating_drop_v": 0.05,
    "max_operating_drop_v": 1.00,
    "device_dissipation_limit_w": 5.00,
    "bus_drop_share_advisory_ceiling": 0.02,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_fraction(name, value, allow_zero=True):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0 or (value == 0.0 and not allow_zero):
        raise ValueError("%s must be a non-negative fraction, got %r" % (name, value))
    if value >= 1.0:
        raise ValueError("%s must sit below one, got %r" % (name, value))
    return float(value)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A voltage drop reconstructed as current times resistance, and a
    dissipation reconstructed as current times that drop, both pass
    through multiplication, so a case meant to sit exactly on a limit can
    land a few units in the last place above it. The limit is never
    widened; only the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, bound):
    """value >= bound, absorbing the same representation error."""
    return value >= bound or math.isclose(
        value, bound, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_bias_policy(policy):
    """Check the tolerances, the window and the limits are usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction(
        "reference_drop_rel_tol", policy.get("reference_drop_rel_tol"), allow_zero=False
    )
    _require_fraction(
        "drop_consistency_rel_tol",
        policy.get("drop_consistency_rel_tol"),
        allow_zero=False,
    )
    low = _require_positive("min_operating_drop_v", policy.get("min_operating_drop_v"))
    high = _require_positive("max_operating_drop_v", policy.get("max_operating_drop_v"))
    if high <= low:
        raise ValueError(
            "operating drop window must ascend, got %g V .. %g V" % (low, high)
        )
    _require_positive(
        "device_dissipation_limit_w", policy.get("device_dissipation_limit_w")
    )
    _require_fraction(
        "bus_drop_share_advisory_ceiling",
        policy.get("bus_drop_share_advisory_ceiling"),
        allow_zero=False,
    )
    return policy


def validate_bias_record(record):
    """Check one reported bias record carries a complete operating point."""
    if not isinstance(record, dict):
        raise ValueError("bias record must be a mapping, got %r" % (record,))
    missing = [f for f in RECORD_FIELDS if f not in record]
    if missing:
        raise ValueError(
            "bias record is missing fields: %s" % ", ".join(sorted(missing))
        )
    name = record["class_name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("class_name must be a non-empty string, got %r" % (name,))
    row = {
        "class_name": name,
        "declared_drop_v": _require_positive(
            "declared_drop_v", record["declared_drop_v"]
        ),
        "load_current_a": _require_positive(
            "load_current_a", record["load_current_a"]
        ),
        "series_resistance_ohm": _require_positive(
            "series_resistance_ohm", record["series_resistance_ohm"]
        ),
        "bus_voltage_v": _require_positive("bus_voltage_v", record["bus_voltage_v"]),
    }
    if not _at_most(row["declared_drop_v"], row["bus_voltage_v"]):
        raise ValueError(
            "class %s declares a drop of %g V across a %g V bus; a device "
            "cannot drop more than it is fed"
            % (name, row["declared_drop_v"], row["bus_voltage_v"])
        )
    return row


def validate_bias_records(records):
    """Normalise a reported record set and refuse a repeated class name."""
    if isinstance(records, dict) or not hasattr(records, "__iter__"):
        raise ValueError("records must be a sequence of bias records")
    rows = [validate_bias_record(r) for r in records]
    if not rows:
        raise ValueError("no bias record was reported; there is nothing to check")
    seen = set()
    for row in rows:
        if row["class_name"] in seen:
            raise ValueError(
                "record set repeats the class %r" % (row["class_name"],)
            )
        seen.add(row["class_name"])
    return tuple(rows)


def implied_drop_v(load_current_a, series_resistance_ohm):
    """Drop the reported current and series resistance actually imply."""
    current = _require_positive("load_current_a", load_current_a)
    resistance = _require_positive("series_resistance_ohm", series_resistance_ohm)
    return current * resistance


def dissipation_w(load_current_a, drop_v):
    """Power the series element sheds at this current and this drop."""
    current = _require_positive("load_current_a", load_current_a)
    drop = _require_positive("drop_v", drop_v)
    return current * drop


def relative_deviation(value, reference):
    """Size of the gap between a value and its reference, as a fraction."""
    ref = _require_positive("reference", reference)
    val = _require_positive("value", value)
    return abs(val - ref) / ref


def drop_share_of_bus(drop_v, bus_voltage_v):
    """Share of the bus voltage the device is holding across itself."""
    drop = _require_positive("drop_v", drop_v)
    bus = _require_positive("bus_voltage_v", bus_voltage_v)
    return drop / bus


def assess_bias_record(record, reference_drop_v, policy=DEFAULT_BIAS_POLICY):
    """Assess one reported bias record against the reference bias point."""
    validate_bias_policy(policy)
    row = validate_bias_record(record)
    reference = _require_positive("reference_drop_v", reference_drop_v)
    window_low = float(policy["min_operating_drop_v"])
    window_high = float(policy["max_operating_drop_v"])
    if not (_at_least(reference, window_low) and _at_most(reference, window_high)):
        raise ValueError(
            "reference_drop_v %g V sits outside the operating window "
            "%g V .. %g V" % (reference, window_low, window_high)
        )

    declared = row["declared_drop_v"]
    implied = implied_drop_v(row["load_current_a"], row["series_resistance_ohm"])
    reference_gap = relative_deviation(declared, reference)
    consistency_gap = relative_deviation(declared, implied)
    dissipation = dissipation_w(row["load_current_a"], declared)
    share = drop_share_of_bus(declared, row["bus_voltage_v"])

    on_reference = _at_most(
        reference_gap, float(policy["reference_drop_rel_tol"])
    )
    consistent = _at_most(
        consistency_gap, float(policy["drop_consistency_rel_tol"])
    )
    in_window = _at_least(declared, window_low) and _at_most(declared, window_high)
    within_dissipation = _at_most(
        dissipation, float(policy["device_dissipation_limit_w"])
    )

    findings = []
    if not on_reference:
        findings.append(
            "%s: %s declares %.4f V against a reference bias point of %.4f V "
            "(%.3f%% away, tolerance %.3f%%)"
            % (
                FINDING_REFERENCE,
                row["class_name"],
                declared,
                reference,
                100.0 * reference_gap,
                100.0 * float(policy["reference_drop_rel_tol"]),
            )
        )
    if not consistent:
        findings.append(
            "%s: %s declares %.4f V while %.4f A through %.5f ohm implies "
            "%.4f V" % (
                FINDING_CONSISTENCY,
                row["class_name"],
                declared,
                row["load_current_a"],
                row["series_resistance_ohm"],
                implied,
            )
        )
    if not in_window:
        findings.append(
            "%s: %s declares %.4f V, outside the operating window %.4f V .. "
            "%.4f V"
            % (FINDING_WINDOW, row["class_name"], declared, window_low, window_high)
        )
    if not within_dissipation:
        findings.append(
            "%s: %s sheds %.4f W at %.4f A and %.4f V, above the device limit "
            "of %.4f W"
            % (
                FINDING_DISSIPATION,
                row["class_name"],
                dissipation,
                row["load_current_a"],
                declared,
                float(policy["device_dissipation_limit_w"]),
            )
        )

    advisories = []
    ceiling = float(policy["bus_drop_share_advisory_ceiling"])
    if not _at_most(share, ceiling):
        advisories.append(
            "%s: %s holds %.4f of the %.3f V bus across itself, above the "
            "advisory ceiling of %.4f"
            % (ADVISORY_BUS_SHARE, row["class_name"], share, row["bus_voltage_v"], ceiling)
        )

    return {
        "class_name": row["class_name"],
        "declared_drop_v": declared,
        "implied_drop_v": implied,
        "reference_drop_v": reference,
        "reference_deviation": reference_gap,
        "consistency_deviation": consistency_gap,
        "dissipation_w": dissipation,
        "bus_share": share,
        "on_reference": on_reference,
        "consistent": consistent,
        "within_operating_window": in_window,
        "within_dissipation_limit": within_dissipation,
        "acceptable": on_reference and consistent and in_window and within_dissipation,
        "findings": findings,
        "advisories": advisories,
    }


def declared_drop_spread(records):
    """Spread of the declared drops across the set, against their mean."""
    rows = validate_bias_records(records)
    drops = [r["declared_drop_v"] for r in rows]
    mean = sum(drops) / len(drops)
    return (max(drops) - min(drops)) / mean


def assess_bias_reporting(records, reference_drop_v, policy=DEFAULT_BIAS_POLICY):
    """Full clause 5.2.17.2.1 bias reporting check with a verdict.

    Each record is taken against the reference bias point, and the set is
    then taken against itself: records that each sit inside the tolerance
    can still straddle it as a group, and a family compared at two bias
    points is not a family.
    """
    validate_bias_policy(policy)
    rows = validate_bias_records(records)
    assessments = [assess_bias_record(r, reference_drop_v, policy) for r in rows]

    findings = []
    advisories = []
    for a in assessments:
        findings.extend(a["findings"])
        advisories.extend(a["advisories"])

    spread = declared_drop_spread(rows)
    common = _at_most(spread, float(policy["reference_drop_rel_tol"]))
    if not common:
        findings.append(
            "%s: declared drops spread by %.3f%% across the reported classes, "
            "against a tolerance of %.3f%%"
            % (
                FINDING_COMMONALITY,
                100.0 * spread,
                100.0 * float(policy["reference_drop_rel_tol"]),
            )
        )

    return {
        "verdict": VERDICT_COMPLIANT if not findings else VERDICT_NONCOMPLIANT,
        "assessments": assessments,
        "acceptable_classes": [a["class_name"] for a in assessments if a["acceptable"]],
        "declared_drop_spread": spread,
        "shares_one_bias_point": common,
        "findings": findings,
        "advisories": advisories,
    }
