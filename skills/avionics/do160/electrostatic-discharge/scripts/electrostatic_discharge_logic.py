#!/usr/bin/env python3
"""DO-160 Section 25 electrostatic discharge (ESD) logic (summary only).

Common-knowledge summary (standards-map.yaml, do-160: proprietary RTCA,
summary-only): DO-160G / ED-14G section 25 tests equipment immunity to
personnel-borne electrostatic discharge. There is a single equipment
category (A) tested at 15 kV air discharge on the equipment bonded to
the ground plane, with 10 positive and 10 negative discharges per test
point. Test points are surfaces accessible to personnel during normal
operation or maintenance; connector pins are not applicable test
points (DO-160G). The discharge generator follows the IEC 61000-4-2
human-body model: 150 pF storage capacitance and 330 ohm discharge
resistance, rise time 0.7 to 1.0 ns, first peak current 3.75 A/kV,
current at 30 ns of 2 A/kV, and current at 60 ns of 1 A/kV. Exact
level, waveform, and count tables are standard data and must be read
from the current revision; this module validates inputs and classifies
the verdict only. No standard tables are reproduced here.
"""

CATEGORY_A = "A"
TEST_LEVEL_KV = 15.0
CAPACITANCE_PF = 150.0
RESISTANCE_OHM = 330.0
PEAK_A_PER_KV = 3.75
CURRENT_30NS_A_PER_KV = 2.0
CURRENT_60NS_A_PER_KV = 1.0
RISE_TIME_MIN_NS = 0.7
RISE_TIME_MAX_NS = 1.0
MIN_DISCHARGES_PER_POLARITY = 10


def _require_number(value, name):
    """Return value if it is an int or float, else raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    return float(value)


def _require_bool(value, name):
    """Return value if it is a bool, else raise ValueError."""
    if not isinstance(value, bool):
        raise ValueError("%s must be a bool, got %r" % (name, value))
    return value


def category_test_level_kv(category):
    """Test level for a DO-160 Section 25 equipment category.

    DO-160 Section 25 defines a single equipment category, A, tested
    at 15 kV air discharge. Worked anchor: category "A" (or "a")
    returns 15.0 kV; any other category is undefined and raises
    ValueError. Raises ValueError when category is not a str.
    """
    if not isinstance(category, str):
        raise ValueError("category must be a str, got %r" % (category,))
    c = category.strip().upper()
    if c != CATEGORY_A:
        raise ValueError(
            "DO-160 Section 25 defines only category A, got %r" % (category,)
        )
    return TEST_LEVEL_KV


def stored_energy_joules(capacitance_pf, voltage_kv):
    """Stored energy of the discharge capacitor, E = 0.5 * C * V^2.

    Worked anchor: 150 pF at 15 kV gives 0.5 * 150e-12 * (15e3)^2 =
    0.016875 J (16.875 mJ). Worked anchor: 150 pF at 8 kV gives
    0.5 * 150e-12 * (8e3)^2 = 0.0048 J (4.8 mJ). Raises ValueError
    when capacitance is not positive or voltage is negative.
    """
    c = _require_number(capacitance_pf, "capacitance_pf")
    v = _require_number(voltage_kv, "voltage_kv")
    if c <= 0:
        raise ValueError("capacitance_pf must be positive, got %r" % (capacitance_pf,))
    if v < 0:
        raise ValueError("voltage_kv must be >= 0, got %r" % (voltage_kv,))
    return 0.5 * (c * 1e-12) * (v * 1e3) ** 2


def peak_current_amps(voltage_kv):
    """First peak current of the discharge waveform, 3.75 A/kV.

    Worked anchor: 15 kV gives 3.75 * 15 = 56.25 A. Worked anchor:
    2 kV gives 7.5 A. Raises ValueError when voltage is not positive.
    """
    v = _require_number(voltage_kv, "voltage_kv")
    if v <= 0:
        raise ValueError("voltage_kv must be positive, got %r" % (voltage_kv,))
    return PEAK_A_PER_KV * v


def current_at_30ns_amps(voltage_kv):
    """Discharge current 30 ns after trigger, 2 A/kV.

    Worked anchor: 15 kV gives 2.0 * 15 = 30.0 A. Raises ValueError
    when voltage is not positive.
    """
    v = _require_number(voltage_kv, "voltage_kv")
    if v <= 0:
        raise ValueError("voltage_kv must be positive, got %r" % (voltage_kv,))
    return CURRENT_30NS_A_PER_KV * v


def current_at_60ns_amps(voltage_kv):
    """Discharge current 60 ns after trigger, 1 A/kV.

    Worked anchor: 15 kV gives 1.0 * 15 = 15.0 A. Raises ValueError
    when voltage is not positive.
    """
    v = _require_number(voltage_kv, "voltage_kv")
    if v <= 0:
        raise ValueError("voltage_kv must be positive, got %r" % (voltage_kv,))
    return CURRENT_60NS_A_PER_KV * v


def rise_time_valid_ns(ns):
    """True when the measured rise time is within 0.7 to 1.0 ns.

    Worked anchor: 0.8 ns is valid (True); 0.5 ns and 1.2 ns are not
    (False). Raises ValueError when ns is not a number.
    """
    t = _require_number(ns, "ns")
    return RISE_TIME_MIN_NS <= t <= RISE_TIME_MAX_NS


def rc_time_constant_ns(resistance_ohm, capacitance_pf):
    """Discharge network time constant, tau = R * C.

    Worked anchor: 330 ohm and 150 pF give 330 * 150e-12 = 49.5e-9 s
    = 49.5 ns. Raises ValueError when either value is not positive.
    """
    r = _require_number(resistance_ohm, "resistance_ohm")
    c = _require_number(capacitance_pf, "capacitance_pf")
    if r <= 0:
        raise ValueError("resistance_ohm must be positive, got %r" % (resistance_ohm,))
    if c <= 0:
        raise ValueError("capacitance_pf must be positive, got %r" % (capacitance_pf,))
    return r * c * 1e-3  # ohm * pF = 1e-12 s; *1e9 gives ns; net factor 1e-3


def discharge_count_valid(positive_count, negative_count):
    """True when at least 10 discharges of each polarity are planned.

    DO-160 Section 25 applies 10 positive and 10 negative discharges
    per test point. Worked anchor: (10, 10) is valid (True); (9, 10)
    and (10, 9) are not (False). Raises ValueError when a count is
    not a non-negative int.
    """
    for val, name in ((positive_count, "positive_count"), (negative_count, "negative_count")):
        if isinstance(val, bool) or not isinstance(val, int) or val < 0:
            raise ValueError("%s must be a non-negative int, got %r" % (name, val))
    return (
        positive_count >= MIN_DISCHARGES_PER_POLARITY
        and negative_count >= MIN_DISCHARGES_PER_POLARITY
    )


def test_point_applicable(accessible_normal_operation, accessible_maintenance, connector_pin):
    """True when a surface is a valid ESD test point.

    Test points must be accessible to personnel during normal
    operation or during maintenance, and must not be connector pins
    (DO-160G excludes connector pins). Worked anchor:
    (True, False, False) is applicable; (True, False, True) is not
    because the point is a connector pin. Raises ValueError when any
    argument is not a bool.
    """
    for val, name in (
        (accessible_normal_operation, "accessible_normal_operation"),
        (accessible_maintenance, "accessible_maintenance"),
        (connector_pin, "connector_pin"),
    ):
        _require_bool(val, name)
    return (accessible_normal_operation or accessible_maintenance) and not connector_pin


def pass_verdict(operates_as_specified, no_permanent_degradation):
    """True (pass) only when both criteria hold.

    DO-160 Section 25 pass criteria: the equipment operates as
    specified during and after the discharges, with no permanent
    degradation of performance. Worked anchor: (True, True) passes;
    (False, True) and (True, False) fail. Raises ValueError when any
    argument is not a bool.
    """
    for val, name in (
        (operates_as_specified, "operates_as_specified"),
        (no_permanent_degradation, "no_permanent_degradation"),
    ):
        _require_bool(val, name)
    return operates_as_specified and no_permanent_degradation
