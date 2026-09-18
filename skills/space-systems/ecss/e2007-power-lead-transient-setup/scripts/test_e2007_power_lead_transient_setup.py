#!/usr/bin/env python3
"""Gate 3 contract test for e2007-power-lead-transient-setup.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_power_lead_transient_setup.py
"""

import unittest

from e2007_power_lead_transient_setup_logic import (
    CATEGORY_CONFORMING,
    CATEGORY_DEVIATION,
    CATEGORY_MARGINAL,
    DEFAULT_BOND_RESISTANCE_LIMIT_MOHM,
    DEFAULT_INJECTION_OFFSET_WINDOW_MM,
    DEFAULT_PROBE_SEPARATION_MIN_MM,
    MODE_DIFFERENTIAL,
    VERDICT_CONFORMING,
    VERDICT_REJECTED,
    assess_transient_setup,
    at_least,
    at_most,
    bond_headroom_mohm,
    categorize_minimum,
    categorize_window,
    delivered_pulse_amplitude_v,
    governing_path,
    grade_injection_path,
    normalize_injection_device,
    normalize_injection_mode,
    normalize_lead,
    paired_return,
    validate_transient_bench,
)


def good_bench(**over):
    record = {
        "injection_mode": MODE_DIFFERENTIAL,
        "ground_plane_bonded": True,
        "support_equipment_powered": True,
        "bond_resistance_mohm": 1.5,
        "source_isolation_uh": 50.0,
    }
    record.update(over)
    return record


def good_path(**over):
    record = {
        "supply_lead": "primary-positive",
        "return_lead": "primary-return",
        "injection_device": "series-injection-transformer",
        "monitor_probe_fitted": True,
        "injection_offset_mm": 50.0,
        "harness_height_mm": 50.0,
        "probe_separation_mm": 80.0,
        "source_isolation_uh": 50.0,
    }
    record.update(over)
    return record


class TestNormalization(unittest.TestCase):
    def test_differential_mode_normalizes(self):
        self.assertEqual(normalize_injection_mode("  Differential-Mode "), MODE_DIFFERENTIAL)

    def test_common_mode_is_not_this_clause(self):
        with self.assertRaises(ValueError):
            normalize_injection_mode("common-mode")

    def test_non_string_mode_rejected(self):
        with self.assertRaises(ValueError):
            normalize_injection_mode(3)

    def test_every_recognized_lead_normalizes(self):
        self.assertEqual(normalize_lead("PRIMARY-RETURN"), "primary-return")

    def test_unrecognized_lead_rejected(self):
        with self.assertRaises(ValueError):
            normalize_lead("chassis")

    def test_non_string_lead_rejected(self):
        with self.assertRaises(ValueError):
            normalize_lead(None)

    def test_injection_device_normalizes(self):
        self.assertEqual(
            normalize_injection_device(" Clamp-Injection-Probe"),
            "clamp-injection-probe",
        )

    def test_unrecognized_injection_device_rejected(self):
        with self.assertRaises(ValueError):
            normalize_injection_device("bench-power-supply")


class TestDifferentialPairing(unittest.TestCase):
    def test_primary_supply_closes_through_the_primary_return(self):
        self.assertEqual(paired_return("primary-positive"), "primary-return")

    def test_secondary_supply_closes_through_the_secondary_return(self):
        self.assertEqual(paired_return("secondary-positive"), "secondary-return")

    def test_a_return_lead_is_not_an_injection_lead(self):
        with self.assertRaises(ValueError):
            paired_return("primary-return")

    def test_path_with_the_wrong_return_rejected(self):
        with self.assertRaises(ValueError):
            grade_injection_path(good_path(return_lead="secondary-return"))


class TestBond(unittest.TestCase):
    def test_headroom_is_limit_minus_measured(self):
        self.assertAlmostEqual(bond_headroom_mohm(1.5, 2.5), 1.0, places=9)

    def test_bond_at_the_ceiling_leaves_no_headroom(self):
        self.assertAlmostEqual(
            bond_headroom_mohm(DEFAULT_BOND_RESISTANCE_LIMIT_MOHM), 0.0, places=9
        )

    def test_bond_over_the_ceiling_is_negative(self):
        self.assertAlmostEqual(bond_headroom_mohm(4.0, 2.5), -1.5, places=9)

    def test_negative_bond_resistance_rejected(self):
        with self.assertRaises(ValueError):
            bond_headroom_mohm(-0.1)

    def test_zero_bond_limit_rejected(self):
        with self.assertRaises(ValueError):
            bond_headroom_mohm(1.0, 0.0)


class TestWindowCategorization(unittest.TestCase):
    def test_mid_window_dimension_conforms(self):
        self.assertEqual(
            categorize_window(50.0, DEFAULT_INJECTION_OFFSET_WINDOW_MM),
            CATEGORY_CONFORMING,
        )

    def test_dimension_at_the_low_edge_is_marginal(self):
        self.assertEqual(
            categorize_window(40.0, DEFAULT_INJECTION_OFFSET_WINDOW_MM),
            CATEGORY_MARGINAL,
        )

    def test_dimension_at_the_high_edge_is_marginal(self):
        self.assertEqual(
            categorize_window(60.0, DEFAULT_INJECTION_OFFSET_WINDOW_MM),
            CATEGORY_MARGINAL,
        )

    def test_dimension_outside_the_window_is_a_deviation(self):
        self.assertEqual(
            categorize_window(90.0, DEFAULT_INJECTION_OFFSET_WINDOW_MM),
            CATEGORY_DEVIATION,
        )

    def test_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            categorize_window(50.0, (60.0, 40.0))

    def test_marginal_fraction_of_a_half_rejected(self):
        with self.assertRaises(ValueError):
            categorize_window(50.0, DEFAULT_INJECTION_OFFSET_WINDOW_MM, 0.5)

    def test_zero_marginal_fraction_keeps_the_edge_marginal_only(self):
        self.assertEqual(
            categorize_window(40.0, DEFAULT_INJECTION_OFFSET_WINDOW_MM, 0.0),
            CATEGORY_MARGINAL,
        )
        self.assertEqual(
            categorize_window(41.0, DEFAULT_INJECTION_OFFSET_WINDOW_MM, 0.0),
            CATEGORY_CONFORMING,
        )


class TestMinimumCategorization(unittest.TestCase):
    def test_generous_separation_conforms(self):
        self.assertEqual(
            categorize_minimum(80.0, DEFAULT_PROBE_SEPARATION_MIN_MM),
            CATEGORY_CONFORMING,
        )

    def test_separation_at_the_floor_is_marginal(self):
        self.assertEqual(
            categorize_minimum(
                DEFAULT_PROBE_SEPARATION_MIN_MM, DEFAULT_PROBE_SEPARATION_MIN_MM
            ),
            CATEGORY_MARGINAL,
        )

    def test_separation_under_the_floor_is_a_deviation(self):
        self.assertEqual(
            categorize_minimum(10.0, DEFAULT_PROBE_SEPARATION_MIN_MM),
            CATEGORY_DEVIATION,
        )

    def test_zero_minimum_rejected(self):
        with self.assertRaises(ValueError):
            categorize_minimum(10.0, 0.0)


class TestTolerantComparison(unittest.TestCase):
    def test_at_least_absorbs_float_error_only(self):
        self.assertTrue(at_least(3.0, 3.0))
        self.assertFalse(at_least(2.0, 3.0))

    def test_at_most_absorbs_float_error_only(self):
        self.assertTrue(at_most(3.0, 3.0))
        self.assertFalse(at_most(4.0, 3.0))


class TestDeliveredAmplitude(unittest.TestCase):
    def test_matched_load_halves_the_open_circuit_amplitude(self):
        self.assertAlmostEqual(
            delivered_pulse_amplitude_v(100.0, 2.0, 2.0), 50.0, places=9
        )

    def test_a_light_load_keeps_most_of_the_amplitude(self):
        self.assertAlmostEqual(
            delivered_pulse_amplitude_v(100.0, 1.0, 9.0), 90.0, places=9
        )

    def test_a_heavy_load_collapses_the_amplitude(self):
        self.assertAlmostEqual(
            delivered_pulse_amplitude_v(100.0, 9.0, 1.0), 10.0, places=9
        )

    def test_zero_source_impedance_rejected(self):
        with self.assertRaises(ValueError):
            delivered_pulse_amplitude_v(100.0, 0.0, 2.0)

    def test_zero_load_impedance_rejected(self):
        with self.assertRaises(ValueError):
            delivered_pulse_amplitude_v(100.0, 2.0, 0.0)

    def test_non_numeric_open_circuit_rejected(self):
        with self.assertRaises(ValueError):
            delivered_pulse_amplitude_v("one hundred", 2.0, 2.0)


class TestBenchValidation(unittest.TestCase):
    def test_good_bench_normalizes(self):
        report = validate_transient_bench(good_bench())
        self.assertEqual(report["injection_mode"], MODE_DIFFERENTIAL)
        self.assertAlmostEqual(report["bond_headroom_mohm"], 1.0, places=9)

    def test_unbonded_unit_rejected(self):
        with self.assertRaises(ValueError):
            validate_transient_bench(good_bench(ground_plane_bonded=False))

    def test_unpowered_support_equipment_rejected(self):
        with self.assertRaises(ValueError):
            validate_transient_bench(good_bench(support_equipment_powered=False))

    def test_bond_over_the_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_transient_bench(good_bench(bond_resistance_mohm=9.0))

    def test_missing_source_isolation_rejected(self):
        bench = good_bench()
        del bench["source_isolation_uh"]
        with self.assertRaises(ValueError):
            validate_transient_bench(bench)

    def test_non_mapping_bench_rejected(self):
        with self.assertRaises(ValueError):
            validate_transient_bench(["primary-positive"])

    def test_boolean_bond_resistance_rejected(self):
        with self.assertRaises(ValueError):
            validate_transient_bench(good_bench(bond_resistance_mohm=True))


class TestPathGrading(unittest.TestCase):
    def test_a_nominal_path_conforms_on_every_dimension(self):
        report = grade_injection_path(good_path())
        self.assertTrue(report["conforming"])
        self.assertEqual(report["counts"][CATEGORY_DEVIATION], 0)

    def test_a_short_probe_separation_is_a_deviation(self):
        report = grade_injection_path(good_path(probe_separation_mm=5.0))
        self.assertEqual(
            report["dimensions"]["probe_separation_mm"], CATEGORY_DEVIATION
        )
        self.assertFalse(report["conforming"])

    def test_an_offset_beyond_the_window_is_a_deviation(self):
        report = grade_injection_path(good_path(injection_offset_mm=150.0))
        self.assertEqual(
            report["dimensions"]["injection_offset_mm"], CATEGORY_DEVIATION
        )

    def test_a_missing_monitor_probe_rejects_the_path(self):
        with self.assertRaises(ValueError):
            grade_injection_path(good_path(monitor_probe_fitted=False))

    def test_a_non_positive_harness_height_rejected(self):
        with self.assertRaises(ValueError):
            grade_injection_path(good_path(harness_height_mm=0.0))

    def test_counts_cover_every_graded_dimension(self):
        report = grade_injection_path(good_path())
        self.assertEqual(sum(report["counts"].values()), len(report["dimensions"]))


class TestGoverningPath(unittest.TestCase):
    def test_the_path_with_the_most_deviations_governs(self):
        clean = grade_injection_path(good_path())
        broken = grade_injection_path(
            good_path(
                supply_lead="secondary-positive",
                return_lead="secondary-return",
                probe_separation_mm=5.0,
                injection_offset_mm=200.0,
            )
        )
        self.assertEqual(
            governing_path([clean, broken])["supply_lead"], "secondary-positive"
        )

    def test_an_empty_report_set_rejected(self):
        with self.assertRaises(ValueError):
            governing_path([])


class TestAssessment(unittest.TestCase):
    def test_a_good_bench_is_conforming(self):
        report = assess_transient_setup(good_bench(), [good_path()])
        self.assertEqual(report["verdict"], VERDICT_CONFORMING)
        self.assertEqual(report["findings"], [])

    def test_a_deviation_rejects_the_bench(self):
        report = assess_transient_setup(
            good_bench(), [good_path(probe_separation_mm=5.0)]
        )
        self.assertEqual(report["verdict"], VERDICT_REJECTED)
        self.assertEqual(len(report["findings"]), 1)

    def test_an_edge_dimension_is_a_limitation_not_a_finding(self):
        report = assess_transient_setup(
            good_bench(), [good_path(injection_offset_mm=40.0)]
        )
        self.assertEqual(report["verdict"], VERDICT_CONFORMING)
        self.assertEqual(len(report["limitations"]), 1)

    def test_a_repeated_supply_lead_rejected(self):
        with self.assertRaises(ValueError):
            assess_transient_setup(good_bench(), [good_path(), good_path()])

    def test_an_empty_path_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_transient_setup(good_bench(), [])

    def test_the_generator_amplitude_is_carried_when_supplied(self):
        report = assess_transient_setup(
            good_bench(),
            [good_path()],
            generator={
                "open_circuit_v": 100.0,
                "source_impedance_ohm": 2.0,
                "load_impedance_ohm": 2.0,
            },
        )
        self.assertAlmostEqual(report["delivered_amplitude_v"], 50.0, places=9)

    def test_no_generator_leaves_the_amplitude_unreported(self):
        report = assess_transient_setup(good_bench(), [good_path()])
        self.assertIsNone(report["delivered_amplitude_v"])

    def test_both_supply_leads_can_be_graded_together(self):
        report = assess_transient_setup(
            good_bench(),
            [
                good_path(),
                good_path(
                    supply_lead="secondary-positive", return_lead="secondary-return"
                ),
            ],
        )
        self.assertEqual(len(report["paths"]), 2)
        self.assertEqual(report["verdict"], VERDICT_CONFORMING)


if __name__ == "__main__":
    unittest.main(verbosity=1)
