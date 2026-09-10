#!/usr/bin/env python3
"""ECSS-E-ST-10-03C clause 5.5.4 equipment thermal test logic
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
equipment-level thermal testing is either thermal vacuum (the unit is
exposed to vacuum in its operational environment) or thermal test at
mission pressure (the unit is sealed/pressurized and not
vacuum-exposed). The hot/cold temperature levels and the required
cycle count for a given test campaign (qualification, acceptance,
protoflight) are owned by the sibling baseline leaves (e1003-eq-qual,
e1003-eq-acceptance, e1003-eq-protoflight); this module implements the
per-test rules that consume those levels: cycle-plan construction,
plateau stabilization against a dwell window, the functional/
performance check requirement at the temperature extremes of the first
and last cycle, and the overall test-completion verdict.
"""

TEST_TYPES = ("thermal_vacuum", "thermal_at_mission_pressure")
CAMPAIGNS = ("qualification", "acceptance", "protoflight")


def select_test_type(vacuum_exposed):
    """Thermal test type for a unit: thermal_vacuum when the unit is
    exposed to vacuum in its operational environment, otherwise
    thermal_at_mission_pressure."""
    return "thermal_vacuum" if vacuum_exposed else "thermal_at_mission_pressure"


def build_cycle_plan(campaign, hot_temp, cold_temp, tolerance, dwell_hours, num_cycles):
    """Thermal cycle plan for a test campaign. Validates: campaign is
    known, hot_temp is strictly above cold_temp, tolerance and
    dwell_hours are positive, and num_cycles is at least 1. Returns a
    new dict; raises ValueError on any invalid input."""
    if campaign not in CAMPAIGNS:
        raise ValueError("unknown campaign: %r" % (campaign,))
    if not (hot_temp > cold_temp):
        raise ValueError("hot_temp must be strictly greater than cold_temp")
    if tolerance <= 0:
        raise ValueError("tolerance must be positive")
    if dwell_hours <= 0:
        raise ValueError("dwell_hours must be positive")
    if num_cycles < 1:
        raise ValueError("num_cycles must be at least 1")
    return {
        "campaign": campaign,
        "hot_temp": hot_temp,
        "cold_temp": cold_temp,
        "tolerance": tolerance,
        "dwell_hours": dwell_hours,
        "num_cycles": num_cycles,
    }


def find_stable_window(readings, target, tolerance, required_samples):
    """Index of the first contiguous run in readings, of length at
    least required_samples, where every reading is within tolerance of
    target; None if no such run exists. Raises ValueError if
    required_samples is less than 1."""
    if required_samples < 1:
        raise ValueError("required_samples must be at least 1")
    run_start = None
    run_len = 0
    for index, reading in enumerate(readings):
        if abs(reading - target) <= tolerance:
            if run_len == 0:
                run_start = index
            run_len += 1
            if run_len >= required_samples:
                return run_start
        else:
            run_len = 0
            run_start = None
    return None


def plateau_stable(readings, target, tolerance, required_samples):
    """True when readings contain a contiguous run of at least
    required_samples samples within tolerance of target -- touching
    the target once is not enough, the dwell window must hold."""
    return find_stable_window(readings, target, tolerance, required_samples) is not None


def functional_check_required(cycle_index, num_cycles):
    """True when cycle_index (0-based) is the first or last cycle of
    num_cycles -- functional/performance verification is mandatory at
    the temperature extremes of those cycles at minimum. Raises
    ValueError for an out-of-range cycle_index or num_cycles."""
    if num_cycles < 1:
        raise ValueError("num_cycles must be at least 1")
    if cycle_index < 0 or cycle_index >= num_cycles:
        raise ValueError("cycle_index out of range")
    return cycle_index == 0 or cycle_index == num_cycles - 1


def evaluate_cycle(plan, cycle_index, cold_readings, hot_readings,
                    required_samples, functional_hot_passed=None,
                    functional_cold_passed=None):
    """Assessment of one thermal cycle against plan. Checks both
    plateaus for dwell-window stabilization; when this cycle requires
    a functional/performance check (first or last cycle), both
    functional_hot_passed and functional_cold_passed must be True for
    the cycle to be complete. Returns a new dict; does not mutate
    plan."""
    cold_stable = plateau_stable(cold_readings, plan["cold_temp"], plan["tolerance"], required_samples)
    hot_stable = plateau_stable(hot_readings, plan["hot_temp"], plan["tolerance"], required_samples)
    functional_required = functional_check_required(cycle_index, plan["num_cycles"])
    if functional_required:
        functional_ok = bool(functional_hot_passed) and bool(functional_cold_passed)
    else:
        functional_ok = True
    return {
        "index": cycle_index,
        "cold_stable": cold_stable,
        "hot_stable": hot_stable,
        "functional_required": functional_required,
        "functional_ok": functional_ok,
        "complete": cold_stable and hot_stable and functional_ok,
    }


def evaluate_thermal_test(vacuum_exposed, required_test_type, plan, cycle_results):
    """Overall thermal-test verdict. Requires: the test type derived
    from vacuum_exposed matches required_test_type, the number of
    cycle_results matches plan['num_cycles'], and every cycle result is
    complete. Returns a new dict listing any incomplete cycle indices;
    does not mutate cycle_results."""
    actual_type = select_test_type(vacuum_exposed)
    type_ok = actual_type == required_test_type
    count_ok = len(cycle_results) == plan["num_cycles"]
    incomplete_cycles = [cycle["index"] for cycle in cycle_results if not cycle["complete"]]
    return {
        "test_type": actual_type,
        "type_ok": type_ok,
        "count_ok": count_ok,
        "incomplete_cycles": incomplete_cycles,
        "passed": type_ok and count_ok and len(incomplete_cycles) == 0,
    }
