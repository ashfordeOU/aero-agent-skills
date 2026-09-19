"""Contract tests for the sterilization process applicability scoping logic."""

import unittest

from q7053_applicability_and_processes_logic import (
    DEFAULT_ANALYSIS_MARGIN,
    MARGIN_TOLERANCE,
    STATUS_ADMISSIBLE,
    STATUS_EXCLUDED,
    STATUS_TEST_REQUIRED,
    admissible_processes,
    assess_applicability,
    axis_margin,
    screen_pairing,
    test_matrix,
    validate_material,
    validate_process,
)

DRY_HEAT = {
    "name": "dry-heat",
    "stressors": {"temperature_c": 125.0, "dwell_h": 30.0},
    "agents": [],
}
RADIATION = {
    "name": "gamma-radiation",
    "stressors": {"dose_kgy": 25.0},
    "agents": ["ionising-radiation"],
}
ETHYLENE_OXIDE = {
    "name": "ethylene-oxide",
    "stressors": {"temperature_c": 55.0, "humidity_pct": 60.0},
    "agents": ["ethylene-oxide"],
}

ALUMINIUM = {
    "name": "aluminium-7075",
    "capabilities": {"temperature_c": 200.0, "dwell_h": 1000.0, "dose_kgy": 1000.0,
                     "humidity_pct": 100.0},
}
PTFE_SEAL = {
    "name": "ptfe-seal",
    "capabilities": {"temperature_c": 200.0, "dwell_h": 1000.0, "dose_kgy": 5.0,
                     "humidity_pct": 100.0},
}
ELASTOMER = {
    "name": "nitrile-elastomer",
    "capabilities": {"temperature_c": 130.0, "dwell_h": 1000.0, "dose_kgy": 100.0,
                     "humidity_pct": 100.0},
    "sensitive_to": ["ethylene-oxide"],
}
UNDECLARED_POLYMER = {
    "name": "undeclared-polymer",
    "capabilities": {"temperature_c": 200.0, "humidity_pct": 100.0},
}


class ValidationTests(unittest.TestCase):
    def test_process_is_normalised(self):
        record = validate_process(DRY_HEAT)
        self.assertEqual(record["name"], "dry-heat")
        self.assertIn("temperature_c", record["stressors"])

    def test_process_without_stressors_rejected(self):
        with self.assertRaises(ValueError):
            validate_process({"name": "vacuum", "stressors": {}})

    def test_process_with_negative_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_process({"name": "x", "stressors": {"dose_kgy": -1.0}})

    def test_unnamed_process_rejected(self):
        with self.assertRaises(ValueError):
            validate_process({"stressors": {"dose_kgy": 1.0}})

    def test_material_agents_are_lowercased(self):
        record = validate_material({"name": "m", "sensitive_to": ["Ethylene-Oxide"]})
        self.assertIn("ethylene-oxide", record["sensitive_to"])

    def test_material_with_zero_capability_rejected(self):
        with self.assertRaises(ValueError):
            validate_material({"name": "m", "capabilities": {"dose_kgy": 0.0}})

    def test_material_agent_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_material({"name": "m", "sensitive_to": "ethylene-oxide"})

    def test_material_without_capabilities_is_allowed(self):
        record = validate_material({"name": "m"})
        self.assertEqual(record["capabilities"], {})


class AxisMarginTests(unittest.TestCase):
    def test_half_used_capability_is_half_margin(self):
        self.assertAlmostEqual(axis_margin(200.0, 100.0), 0.5, places=12)

    def test_exactly_at_capability_is_zero_margin(self):
        self.assertAlmostEqual(axis_margin(125.0, 125.0), 0.0, places=12)

    def test_breach_is_negative(self):
        self.assertAlmostEqual(axis_margin(100.0, 150.0), -0.5, places=12)

    def test_zero_capability_rejected(self):
        with self.assertRaises(ValueError):
            axis_margin(0.0, 10.0)

    def test_negative_applied_level_rejected(self):
        with self.assertRaises(ValueError):
            axis_margin(100.0, -1.0)


class PairingTests(unittest.TestCase):
    def test_ample_margin_is_settled_by_analysis(self):
        record = screen_pairing(ALUMINIUM, DRY_HEAT)
        self.assertEqual(record["status"], STATUS_ADMISSIBLE)

    def test_thin_margin_demands_a_test(self):
        record = screen_pairing(ELASTOMER, DRY_HEAT)
        self.assertEqual(record["status"], STATUS_TEST_REQUIRED)
        self.assertEqual(record["driving_axis"], "temperature_c")

    def test_breached_axis_excludes_the_pairing(self):
        record = screen_pairing(PTFE_SEAL, RADIATION)
        self.assertEqual(record["status"], STATUS_EXCLUDED)
        self.assertEqual(record["breached_axes"], ["dose_kgy"])

    def test_chemical_sensitivity_excludes_regardless_of_margin(self):
        record = screen_pairing(ELASTOMER, ETHYLENE_OXIDE)
        self.assertEqual(record["status"], STATUS_EXCLUDED)
        self.assertEqual(record["attacked_by"], ["ethylene-oxide"])

    def test_undeclared_axis_is_never_a_pass(self):
        record = screen_pairing(UNDECLARED_POLYMER, RADIATION)
        self.assertEqual(record["status"], STATUS_TEST_REQUIRED)
        self.assertEqual(record["undeclared_axes"], ["dose_kgy"])

    def test_exactly_at_capability_is_not_a_breach(self):
        material = {"name": "at-limit", "capabilities": {"temperature_c": 125.0,
                                                         "dwell_h": 1000.0}}
        record = screen_pairing(material, DRY_HEAT)
        self.assertEqual(record["breached_axes"], [])
        self.assertAlmostEqual(record["axes"]["temperature_c"]["margin"], 0.0, places=12)
        self.assertEqual(record["status"], STATUS_TEST_REQUIRED)

    def test_driving_axis_is_the_least_margin_one(self):
        record = screen_pairing(ELASTOMER, DRY_HEAT)
        self.assertAlmostEqual(record["least_margin"], axis_margin(130.0, 125.0), places=12)

    def test_lower_threshold_settles_a_thin_pairing_by_analysis(self):
        record = screen_pairing(ELASTOMER, DRY_HEAT, analysis_margin=0.01)
        self.assertEqual(record["status"], STATUS_ADMISSIBLE)

    def test_pairing_records_both_names(self):
        record = screen_pairing(ALUMINIUM, RADIATION)
        self.assertEqual(record["material"], "aluminium-7075")
        self.assertEqual(record["process"], "gamma-radiation")


class AggregationTests(unittest.TestCase):
    def test_excluded_pairing_removes_the_process(self):
        pairings = [
            {"material": "a", "process": "p1", "status": STATUS_ADMISSIBLE},
            {"material": "b", "process": "p1", "status": STATUS_EXCLUDED},
            {"material": "a", "process": "p2", "status": STATUS_TEST_REQUIRED},
        ]
        self.assertEqual(admissible_processes(pairings), ["p2"])

    def test_process_order_is_preserved(self):
        pairings = [
            {"material": "a", "process": "p2", "status": STATUS_ADMISSIBLE},
            {"material": "a", "process": "p1", "status": STATUS_ADMISSIBLE},
        ]
        self.assertEqual(admissible_processes(pairings), ["p2", "p1"])

    def test_malformed_pairing_rejected(self):
        with self.assertRaises(ValueError):
            admissible_processes([{"process": "p1"}])

    def test_test_matrix_keeps_only_test_required(self):
        pairings = [
            {"material": "a", "process": "p1", "status": STATUS_ADMISSIBLE},
            {"material": "b", "process": "p1", "status": STATUS_TEST_REQUIRED},
        ]
        self.assertEqual(test_matrix(pairings), [("b", "p1")])


class ApplicabilityTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "item": "propulsion-valve",
            "materials": [ALUMINIUM, ELASTOMER],
            "processes": [DRY_HEAT, RADIATION],
        }
        spec.update(overrides)
        return spec

    def test_scope_keeps_the_surviving_processes(self):
        result = assess_applicability(self._spec())
        self.assertTrue(result["scoped"])
        self.assertEqual(result["admissible_processes"], ["dry-heat", "gamma-radiation"])

    def test_test_matrix_names_the_thin_pairing(self):
        result = assess_applicability(self._spec())
        self.assertIn(("nitrile-elastomer", "dry-heat"), result["test_matrix"])

    def test_test_matrix_never_lists_an_inadmissible_process(self):
        result = assess_applicability(
            self._spec(materials=[ALUMINIUM, ELASTOMER, UNDECLARED_POLYMER],
                       processes=[ETHYLENE_OXIDE, RADIATION])
        )
        for _material, process in result["test_matrix"]:
            self.assertIn(process, result["admissible_processes"])

    def test_one_sensitive_material_removes_a_process_for_the_item(self):
        result = assess_applicability(self._spec(processes=[ETHYLENE_OXIDE, RADIATION]))
        self.assertNotIn("ethylene-oxide", result["admissible_processes"])

    def test_no_surviving_process_is_a_finding(self):
        result = assess_applicability(
            self._spec(materials=[ELASTOMER, PTFE_SEAL],
                       processes=[ETHYLENE_OXIDE, RADIATION])
        )
        self.assertFalse(result["scoped"])
        self.assertTrue(any("no candidate process" in f for f in result["findings"]))

    def test_every_pairing_is_screened(self):
        result = assess_applicability(self._spec())
        self.assertEqual(len(result["pairings"]), 4)

    def test_default_analysis_margin_is_reported(self):
        result = assess_applicability(self._spec())
        self.assertAlmostEqual(result["analysis_margin"], DEFAULT_ANALYSIS_MARGIN, places=12)

    def test_empty_material_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_applicability(self._spec(materials=[]))

    def test_empty_process_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_applicability(self._spec(processes=[]))

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["item"]
        with self.assertRaises(ValueError):
            assess_applicability(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_applicability(["item"])

    def test_tolerance_is_a_representation_allowance_only(self):
        self.assertAlmostEqual(MARGIN_TOLERANCE, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main()
