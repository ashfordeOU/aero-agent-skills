import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from load_events_and_combined_loads_logic import (
    validate_load_event,
    categorize_load_event,
    get_required_load_types,
    check_load_type_coverage,
    compute_design_load,
    apply_ultimate_factor,
    check_event_coverage,
    find_governing_load_case,
    DEFAULT_ULTIMATE_FACTOR,
    VALID_PHASES,
    REQUIRED_LOAD_TYPES_BY_PHASE,
)

LAUNCH_EVENT = {
    "name": "launch_liftoff",
    "phase": "launch",
    "load_types": ["quasi_static", "acoustic", "random_vibration", "thermal"],
    "limit_load": 45000.0,
}

ORBIT_EVENT = {
    "name": "orbit_maneuver",
    "phase": "on_orbit",
    "load_types": ["quasi_static", "thermal"],
    "limit_load": 500.0,
}

ALL_PHASE_EVENTS = [
    {"name": "ev_ground_handling", "phase": "ground_handling",
     "load_types": ["quasi_static", "thermal"], "limit_load": 200.0},
    {"name": "ev_transportation", "phase": "transportation",
     "load_types": ["quasi_static", "dynamic", "shock"], "limit_load": 300.0},
    {"name": "ev_launch", "phase": "launch",
     "load_types": ["quasi_static", "acoustic", "random_vibration", "thermal"],
     "limit_load": 45000.0},
    {"name": "ev_ascent", "phase": "ascent",
     "load_types": ["quasi_static", "acoustic", "random_vibration", "thermal"],
     "limit_load": 30000.0},
    {"name": "ev_separation", "phase": "separation",
     "load_types": ["quasi_static", "shock"], "limit_load": 8000.0},
    {"name": "ev_on_orbit", "phase": "on_orbit",
     "load_types": ["quasi_static", "thermal"], "limit_load": 500.0},
    {"name": "ev_re_entry", "phase": "re_entry",
     "load_types": ["quasi_static", "thermal", "pressure"], "limit_load": 12000.0},
    {"name": "ev_landing", "phase": "landing",
     "load_types": ["quasi_static", "shock", "dynamic"], "limit_load": 5000.0},
]


class TestValidateLoadEvent(unittest.TestCase):

    def test_valid_event_returns_event(self):
        result = validate_load_event(LAUNCH_EVENT)
        self.assertEqual(result["name"], "launch_liftoff")

    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            validate_load_event({**LAUNCH_EVENT, "name": ""})

    def test_none_name_raises(self):
        with self.assertRaises(ValueError):
            validate_load_event({**LAUNCH_EVENT, "name": None})

    def test_invalid_phase_raises(self):
        with self.assertRaises(ValueError):
            validate_load_event({**LAUNCH_EVENT, "phase": "cruise"})

    def test_unknown_load_type_raises(self):
        with self.assertRaises(ValueError):
            validate_load_event({**LAUNCH_EVENT, "load_types": ["electromagnetic"]})

    def test_negative_limit_load_raises(self):
        with self.assertRaises(ValueError):
            validate_load_event({**LAUNCH_EVENT, "limit_load": -1.0})

    def test_zero_limit_load_passes(self):
        result = validate_load_event({**LAUNCH_EVENT, "limit_load": 0.0})
        self.assertEqual(result["limit_load"], 0.0)

    def test_missing_load_types_raises(self):
        bad = dict(LAUNCH_EVENT)
        bad["load_types"] = []
        with self.assertRaises(ValueError):
            validate_load_event(bad)


class TestCategorizeLoadEvent(unittest.TestCase):

    def test_returns_launch_phase(self):
        self.assertEqual(categorize_load_event(LAUNCH_EVENT), "launch")

    def test_returns_on_orbit_phase(self):
        self.assertEqual(categorize_load_event(ORBIT_EVENT), "on_orbit")

    def test_all_valid_phases_round_trip(self):
        for phase in VALID_PHASES:
            event = {
                "name": f"ev_{phase}",
                "phase": phase,
                "load_types": list(REQUIRED_LOAD_TYPES_BY_PHASE[phase]),
                "limit_load": 100.0,
            }
            self.assertEqual(categorize_load_event(event), phase)


class TestGetRequiredLoadTypes(unittest.TestCase):

    def test_launch_requires_acoustic(self):
        self.assertIn("acoustic", get_required_load_types("launch"))

    def test_launch_requires_random_vibration(self):
        self.assertIn("random_vibration", get_required_load_types("launch"))

    def test_on_orbit_requires_quasi_static_and_thermal(self):
        req = get_required_load_types("on_orbit")
        self.assertIn("quasi_static", req)
        self.assertIn("thermal", req)

    def test_separation_requires_shock(self):
        self.assertIn("shock", get_required_load_types("separation"))

    def test_re_entry_requires_pressure(self):
        self.assertIn("pressure", get_required_load_types("re_entry"))

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            get_required_load_types("deep_space")

    def test_returns_set(self):
        result = get_required_load_types("landing")
        self.assertIsInstance(result, set)


class TestCheckLoadTypeCoverage(unittest.TestCase):

    def test_compliant_launch_event_returns_empty(self):
        self.assertEqual(check_load_type_coverage(LAUNCH_EVENT), [])

    def test_missing_acoustic_reported(self):
        event = {
            "name": "launch_partial",
            "phase": "launch",
            "load_types": ["quasi_static", "thermal"],
            "limit_load": 40000.0,
        }
        missing = check_load_type_coverage(event)
        self.assertIn("acoustic", missing)
        self.assertIn("random_vibration", missing)

    def test_result_is_sorted(self):
        event = {
            "name": "ascent_bad",
            "phase": "ascent",
            "load_types": ["quasi_static"],
            "limit_load": 1000.0,
        }
        missing = check_load_type_coverage(event)
        self.assertEqual(missing, sorted(missing))


class TestComputeDesignLoad(unittest.TestCase):

    def test_single_full_factor(self):
        loads = [{"load_type": "quasi_static", "value": 1000.0}]
        result = compute_design_load(loads, {"quasi_static": 1.0})
        self.assertAlmostEqual(result, 1000.0)

    def test_two_loads_summed(self):
        loads = [
            {"load_type": "quasi_static", "value": 500.0},
            {"load_type": "dynamic", "value": 300.0},
        ]
        result = compute_design_load(loads, {"quasi_static": 1.0, "dynamic": 0.5})
        self.assertAlmostEqual(result, 650.0)

    def test_zero_factor_drops_contribution(self):
        loads = [
            {"load_type": "quasi_static", "value": 1000.0},
            {"load_type": "thermal", "value": 500.0},
        ]
        result = compute_design_load(loads, {"quasi_static": 1.0, "thermal": 0.0})
        self.assertAlmostEqual(result, 1000.0)

    def test_absent_factor_defaults_zero(self):
        loads = [{"load_type": "shock", "value": 200.0}]
        result = compute_design_load(loads, {})
        self.assertAlmostEqual(result, 0.0)

    def test_empty_loads_raises(self):
        with self.assertRaises(ValueError):
            compute_design_load([], {})

    def test_malformed_item_raises(self):
        with self.assertRaises(ValueError):
            compute_design_load([{"load_type": "quasi_static"}], {"quasi_static": 1.0})

    def test_three_loads_full_factors(self):
        loads = [
            {"load_type": "quasi_static", "value": 100.0},
            {"load_type": "acoustic", "value": 200.0},
            {"load_type": "thermal", "value": 50.0},
        ]
        factors = {"quasi_static": 1.0, "acoustic": 1.0, "thermal": 1.0}
        result = compute_design_load(loads, factors)
        self.assertAlmostEqual(result, 350.0)


class TestApplyUltimateFactor(unittest.TestCase):

    def test_default_factor_applied(self):
        result = apply_ultimate_factor(1000.0)
        self.assertAlmostEqual(result, 1000.0 * DEFAULT_ULTIMATE_FACTOR)

    def test_custom_factor_1_25(self):
        result = apply_ultimate_factor(2000.0, ultimate_factor=1.25)
        self.assertAlmostEqual(result, 2500.0)

    def test_zero_limit_load_gives_zero(self):
        self.assertAlmostEqual(apply_ultimate_factor(0.0), 0.0)

    def test_non_positive_factor_raises(self):
        with self.assertRaises(ValueError):
            apply_ultimate_factor(1000.0, ultimate_factor=0.0)

    def test_negative_factor_raises(self):
        with self.assertRaises(ValueError):
            apply_ultimate_factor(1000.0, ultimate_factor=-1.5)

    def test_negative_limit_load_raises(self):
        with self.assertRaises(ValueError):
            apply_ultimate_factor(-100.0)


class TestCheckEventCoverage(unittest.TestCase):

    def test_all_phases_covered_returns_true(self):
        covered, missing = check_event_coverage(ALL_PHASE_EVENTS)
        self.assertTrue(covered)
        self.assertEqual(missing, [])

    def test_missing_phase_returns_false(self):
        covered, missing = check_event_coverage([LAUNCH_EVENT, ORBIT_EVENT])
        self.assertFalse(covered)
        self.assertIn("ground_handling", missing)

    def test_custom_required_phases_single(self):
        covered, missing = check_event_coverage([LAUNCH_EVENT], required_phases={"launch"})
        self.assertTrue(covered)
        self.assertEqual(missing, [])

    def test_custom_required_phases_missing_one(self):
        covered, missing = check_event_coverage(
            [LAUNCH_EVENT], required_phases={"launch", "landing"}
        )
        self.assertFalse(covered)
        self.assertIn("landing", missing)

    def test_missing_phases_list_is_sorted(self):
        covered, missing = check_event_coverage([LAUNCH_EVENT, ORBIT_EVENT])
        self.assertFalse(covered)
        self.assertEqual(missing, sorted(missing))


class TestFindGoverningLoadCase(unittest.TestCase):

    def test_returns_highest_value(self):
        combos = [
            {"name": "lc1", "design_load": 1000.0},
            {"name": "lc2", "design_load": 5000.0},
            {"name": "lc3", "design_load": 2500.0},
        ]
        governing = find_governing_load_case(combos)
        self.assertEqual(governing["name"], "lc2")
        self.assertAlmostEqual(governing["design_load"], 5000.0)

    def test_single_entry_returns_itself(self):
        combos = [{"name": "lc_only", "design_load": 750.0}]
        governing = find_governing_load_case(combos)
        self.assertEqual(governing["name"], "lc_only")

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            find_governing_load_case([])

    def test_tied_values_returns_one_of_them(self):
        combos = [
            {"name": "lc_a", "design_load": 3000.0},
            {"name": "lc_b", "design_load": 3000.0},
        ]
        governing = find_governing_load_case(combos)
        self.assertAlmostEqual(governing["design_load"], 3000.0)


if __name__ == "__main__":
    unittest.main()
