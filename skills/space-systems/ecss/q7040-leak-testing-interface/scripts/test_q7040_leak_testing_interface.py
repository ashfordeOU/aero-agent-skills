#!/usr/bin/env python3
"""Contract test for leak testing of a brazed pressurised assembly (offline)."""

import copy
import unittest

from q7040_leak_testing_interface_logic import (
    BUBBLE_IMMERSION,
    DEFAULT_DETECTION_MARGIN,
    GAS_MOLAR_MASS,
    LEAK_TEST_METHODS,
    PRESSURE_DECAY,
    TRACER_SNIFFER_PROBE,
    TRACER_VACUUM_HOOD,
    allowable_throughput,
    convert_rate,
    evaluate_leak_test,
    method_floor,
    pressure_decay_detection_floor,
    select_leak_test_method,
    species_conversion_factor,
)

TIGHT_CASE = {
    "service_gas": "nitrogen",
    "tracer_gas": "helium",
    "volume_l": 2.5,
    "pressure_drop_mbar": 1.0,
    "hold_time_s": 3.1536e7,
    "measured_tracer_rate": 1.0e-8,
}

LOOSE_CASE = {
    "service_gas": "nitrogen",
    "tracer_gas": "helium",
    "volume_l": 50.0,
    "pressure_drop_mbar": 500.0,
    "hold_time_s": 86400.0,
    "measured_tracer_rate": 1.0e-3,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class ThroughputTests(unittest.TestCase):
    def test_throughput_is_drop_times_volume_over_time(self):
        self.assertAlmostEqual(allowable_throughput(10.0, 2.0, 5.0), 4.0, places=12)

    def test_a_longer_hold_lowers_the_allowable_rate(self):
        short = allowable_throughput(10.0, 2.0, 100.0)
        long_hold = allowable_throughput(10.0, 2.0, 10000.0)
        self.assertGreater(short, long_hold)

    def test_a_bigger_volume_raises_the_allowable_rate(self):
        self.assertGreater(
            allowable_throughput(10.0, 20.0, 100.0),
            allowable_throughput(10.0, 2.0, 100.0),
        )

    def test_a_zero_hold_time_is_rejected(self):
        with self.assertRaises(ValueError):
            allowable_throughput(10.0, 2.0, 0.0)

    def test_a_non_numeric_pressure_drop_is_rejected(self):
        with self.assertRaises(ValueError):
            allowable_throughput("10 mbar", 2.0, 5.0)


class SpeciesConversionTests(unittest.TestCase):
    def test_a_helium_rate_exceeds_the_nitrogen_rate_through_one_path(self):
        self.assertGreater(species_conversion_factor("nitrogen", "helium"), 1.0)

    def test_the_helium_to_nitrogen_factor_matches_the_molar_mass_ratio(self):
        expected = (GAS_MOLAR_MASS["helium"] / GAS_MOLAR_MASS["nitrogen"]) ** 0.5
        self.assertAlmostEqual(
            species_conversion_factor("helium", "nitrogen"), expected, places=12
        )

    def test_the_conversion_is_reciprocal(self):
        product = species_conversion_factor(
            "helium", "xenon"
        ) * species_conversion_factor("xenon", "helium")
        self.assertAlmostEqual(product, 1.0, places=12)

    def test_converting_a_gas_to_itself_leaves_the_rate_alone(self):
        self.assertAlmostEqual(
            convert_rate(3.2e-6, "argon", "argon"), 3.2e-6, places=18
        )

    def test_a_round_trip_returns_the_original_rate(self):
        there = convert_rate(4.7e-7, "nitrogen", "helium")
        back = convert_rate(there, "helium", "nitrogen")
        self.assertAlmostEqual(back, 4.7e-7, places=18)

    def test_an_unknown_gas_is_rejected(self):
        with self.assertRaises(ValueError):
            species_conversion_factor("helium", "hydrazine-vapour")

    def test_a_negative_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            convert_rate(-1.0e-6, "helium", "nitrogen")


class DetectionFloorTests(unittest.TestCase):
    def test_the_decay_floor_is_resolution_times_volume_over_time(self):
        self.assertAlmostEqual(
            pressure_decay_detection_floor(0.1, 2.5, 500.0), 5.0e-4, places=12
        )

    def test_a_longer_test_lowers_the_decay_floor(self):
        self.assertLess(
            pressure_decay_detection_floor(0.1, 2.5, 5000.0),
            pressure_decay_detection_floor(0.1, 2.5, 500.0),
        )

    def test_a_bigger_volume_raises_the_decay_floor(self):
        self.assertGreater(
            pressure_decay_detection_floor(0.1, 25.0, 500.0),
            pressure_decay_detection_floor(0.1, 2.5, 500.0),
        )

    def test_a_rig_floor_overrides_the_catalogue_floor(self):
        rig = {"gauge_resolution_mbar": 0.1, "volume_l": 2.5, "test_duration_s": 600.0}
        self.assertGreater(method_floor(PRESSURE_DECAY, rig), method_floor(PRESSURE_DECAY))

    def test_a_rig_does_not_disturb_the_other_methods(self):
        rig = {"gauge_resolution_mbar": 0.1, "volume_l": 2.5, "test_duration_s": 600.0}
        self.assertAlmostEqual(
            method_floor(TRACER_VACUUM_HOOD, rig),
            method_floor(TRACER_VACUUM_HOOD),
            places=18,
        )

    def test_a_zero_gauge_resolution_is_rejected(self):
        with self.assertRaises(ValueError):
            pressure_decay_detection_floor(0.0, 2.5, 500.0)

    def test_an_unknown_method_is_rejected(self):
        with self.assertRaises(ValueError):
            method_floor("dye-penetrant")


class MethodSelectionTests(unittest.TestCase):
    def test_a_loose_requirement_takes_the_cheapest_method(self):
        self.assertEqual(
            select_leak_test_method(1.0, DEFAULT_DETECTION_MARGIN)["method"],
            BUBBLE_IMMERSION,
        )

    def test_a_tight_requirement_walks_to_the_vacuum_hood(self):
        self.assertEqual(
            select_leak_test_method(2.1e-7)["method"], TRACER_VACUUM_HOOD
        )

    def test_an_intermediate_requirement_takes_the_sniffer(self):
        self.assertEqual(
            select_leak_test_method(2.0e-5)["method"], TRACER_SNIFFER_PROBE
        )

    def test_a_floor_exactly_on_the_required_value_is_adequate(self):
        result = select_leak_test_method(1.0e-8, 10.0)
        self.assertEqual(result["method"], TRACER_VACUUM_HOOD)
        self.assertAlmostEqual(result["required_floor"], 1.0e-9, places=18)

    def test_a_requirement_no_method_reaches_returns_none(self):
        result = select_leak_test_method(1.0e-12)
        self.assertIsNone(result["method"])
        self.assertTrue(any("no available method" in f for f in result["findings"]))

    def test_every_method_is_considered_before_giving_up(self):
        result = select_leak_test_method(1.0e-12)
        self.assertEqual(
            [entry["method"] for entry in result["considered"]],
            list(LEAK_TEST_METHODS),
        )

    def test_a_larger_margin_forces_a_more_sensitive_method(self):
        relaxed = select_leak_test_method(2.0e-3, 2.0)["method"]
        strict = select_leak_test_method(2.0e-3, 1000.0)["method"]
        self.assertNotEqual(relaxed, strict)

    def test_a_zero_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            select_leak_test_method(1.0e-6, 0.0)


class EvaluationTests(unittest.TestCase):
    def test_a_tight_assembly_passes(self):
        result = evaluate_leak_test(TIGHT_CASE)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["verdict"], "leak-rate-within-allowable")

    def test_the_tracer_budget_exceeds_the_service_budget(self):
        result = evaluate_leak_test(TIGHT_CASE)
        self.assertGreater(
            result["allowable_tracer_rate"], result["allowable_service_rate"]
        )

    def test_a_leaking_assembly_fails_with_a_finding(self):
        result = evaluate_leak_test(_case(TIGHT_CASE, measured_tracer_rate=1.0e-4))
        self.assertFalse(result["compliant"])
        self.assertEqual(result["verdict"], "leak-rate-exceeded")
        self.assertTrue(any("allowable" in f for f in result["findings"]))

    def test_a_rate_exactly_at_the_allowable_budget_passes(self):
        base = evaluate_leak_test(TIGHT_CASE)
        on_limit = evaluate_leak_test(
            _case(TIGHT_CASE, measured_tracer_rate=base["allowable_tracer_rate"])
        )
        self.assertTrue(on_limit["compliant"])

    def test_a_loose_assembly_takes_a_cheaper_method(self):
        self.assertEqual(evaluate_leak_test(LOOSE_CASE)["method"], BUBBLE_IMMERSION)

    def test_an_unmeasured_assembly_is_not_yet_proven(self):
        case = _case(TIGHT_CASE)
        del case["measured_tracer_rate"]
        result = evaluate_leak_test(case)
        self.assertIsNone(result["compliant"])
        self.assertEqual(result["verdict"], "leak-rate-not-measured")
        self.assertTrue(any("not yet proven" in f for f in result["findings"]))

    def test_a_tracer_equal_to_the_service_gas_raises_a_background_finding(self):
        result = evaluate_leak_test(
            _case(TIGHT_CASE, service_gas="helium", tracer_gas="helium")
        )
        self.assertTrue(any("background" in f for f in result["findings"]))

    def test_a_pressure_decay_rig_inherits_the_assembly_volume(self):
        result = evaluate_leak_test(
            _case(
                LOOSE_CASE,
                pressure_decay_rig={
                    "gauge_resolution_mbar": 0.5,
                    "test_duration_s": 600.0,
                },
            )
        )
        self.assertIsNotNone(result["method"])

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_leak_test("nitrogen")

    def test_an_unknown_service_gas_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_leak_test(_case(TIGHT_CASE, service_gas="freon"))

    def test_a_non_mapping_rig_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_leak_test(_case(TIGHT_CASE, pressure_decay_rig=[0.1, 600.0]))

    def test_a_zero_volume_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_leak_test(_case(TIGHT_CASE, volume_l=0.0))


if __name__ == "__main__":
    unittest.main()
