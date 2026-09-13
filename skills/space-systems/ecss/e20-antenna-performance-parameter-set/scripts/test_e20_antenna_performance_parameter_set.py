#!/usr/bin/env python3
"""Gate 3 contract test for e20-antenna-performance-parameter-set.

Offline, deterministic, stdlib unittest only.
Run: python3 test_e20_antenna_performance_parameter_set.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_antenna_performance_parameter_set_logic as logic


class TestNameNormalisation(unittest.TestCase):
    def test_canonical_name_passes_through(self):
        self.assertEqual(logic.normalise_parameter("axial-ratio"), "axial-ratio")

    def test_alias_resolves_to_canonical(self):
        self.assertEqual(logic.normalise_parameter("hpbw"), "half-power-beamwidth")
        self.assertEqual(logic.normalise_parameter("xpd"), "cross-polar-discrimination")
        self.assertEqual(logic.normalise_parameter("sll"), "side-lobe-level")

    def test_case_underscore_and_whitespace_are_tolerated(self):
        self.assertEqual(logic.normalise_parameter("  Peak_Antenna_Gain "), "peak-antenna-gain")
        self.assertEqual(logic.normalise_parameter("Half Power Beamwidth"), "half-power-beamwidth")

    def test_unknown_name_raises(self):
        with self.assertRaises(ValueError):
            logic.normalise_parameter("wing-loading")

    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            logic.normalise_parameter("   ")

    def test_non_string_name_raises(self):
        with self.assertRaises(ValueError):
            logic.normalise_parameter(17)


class TestFamilySorting(unittest.TestCase):
    def test_every_canonical_parameter_has_exactly_one_family(self):
        families = set()
        for name in logic._PARAMETER_FAMILY:
            families.add(logic.parameter_family(name))
        self.assertEqual(len(families), 5)

    def test_coverage_family(self):
        self.assertEqual(logic.parameter_family("eoc"), "beam-coverage")

    def test_boresight_family(self):
        self.assertEqual(logic.parameter_family("pointing-error"), "boresight-pointing")

    def test_port_family(self):
        self.assertEqual(logic.parameter_family("vswr"), "port-matching")

    def test_unknown_family_lookup_raises(self):
        with self.assertRaises(ValueError):
            logic.parameter_family("thermal-conductance")


class TestFunctionRequirements(unittest.TestCase):
    def test_payload_downlink_requires_side_lobe_level(self):
        self.assertIn("side-lobe-level", logic.required_parameters("payload-downlink"))

    def test_navigation_signal_requires_polarisation_purity(self):
        required = logic.required_parameters("navigation-signal")
        self.assertIn("axial-ratio", required)
        self.assertIn("cross-polar-discrimination", required)

    def test_telecommand_reception_does_not_require_side_lobe_level(self):
        self.assertNotIn("side-lobe-level", logic.required_parameters("telecommand-reception"))

    def test_inter_satellite_link_requires_scan_range(self):
        self.assertIn("scan-range", logic.required_parameters("inter-satellite-link"))

    def test_unknown_function_raises(self):
        with self.assertRaises(ValueError):
            logic.required_parameters("radar-altimeter")

    def test_non_string_function_raises(self):
        with self.assertRaises(ValueError):
            logic.required_parameters(None)


class TestParameterSetCompleteness(unittest.TestCase):
    def test_complete_set_reports_no_missing_entry(self):
        report = logic.check_parameter_set(
            logic.required_parameters("telecommand-reception"), "telecommand-reception"
        )
        self.assertTrue(report["complete"])
        self.assertEqual(report["missing"], [])
        self.assertEqual(report["families-uncovered"], [])

    def test_missing_mandatory_entry_is_reported(self):
        declared = [p for p in logic.required_parameters("payload-downlink")
                    if p != "boresight-pointing-error"]
        report = logic.check_parameter_set(declared, "payload-downlink")
        self.assertFalse(report["complete"])
        self.assertEqual(report["missing"], ["boresight-pointing-error"])

    def test_duplicate_aliases_collapse_to_one_entry(self):
        report = logic.check_parameter_set(
            ["gain", "peak-antenna-gain", "vswr"], "telecommand-reception"
        )
        self.assertEqual(report["declared"].count("peak-antenna-gain"), 1)

    def test_extra_declared_entry_does_not_break_completeness(self):
        declared = list(logic.required_parameters("telecommand-reception")) + ["side-lobe-level"]
        report = logic.check_parameter_set(declared, "telecommand-reception")
        self.assertTrue(report["complete"])
        self.assertIn("directivity-and-antenna-gain", report["families-covered"])

    def test_uncovered_family_is_reported(self):
        report = logic.check_parameter_set(["coverage-area"], "navigation-signal")
        self.assertIn("polarisation-purity", report["families-uncovered"])

    def test_empty_declared_set_raises(self):
        with self.assertRaises(ValueError):
            logic.check_parameter_set([], "payload-downlink")

    def test_non_sequence_declared_raises(self):
        with self.assertRaises(ValueError):
            logic.check_parameter_set("axial-ratio", "payload-downlink")


class TestDirectivityAndAntennaGain(unittest.TestCase):
    def test_pencil_beam_directivity(self):
        self.assertAlmostEqual(
            logic.directivity_dbi_from_beamwidths(2.0, 2.0), 40.13395545, places=6
        )

    def test_elliptical_beam_directivity(self):
        self.assertAlmostEqual(
            logic.directivity_dbi_from_beamwidths(1.5, 3.0), 39.62243023, places=6
        )

    def test_wide_beam_directivity(self):
        self.assertAlmostEqual(
            logic.directivity_dbi_from_beamwidths(65.0, 65.0), 9.89628824, places=6
        )

    def test_zero_beamwidth_raises(self):
        with self.assertRaises(ValueError):
            logic.directivity_dbi_from_beamwidths(0.0, 2.0)

    def test_negative_beamwidth_raises(self):
        with self.assertRaises(ValueError):
            logic.directivity_dbi_from_beamwidths(2.0, -1.0)

    def test_beamwidth_at_or_above_full_circle_raises(self):
        with self.assertRaises(ValueError):
            logic.directivity_dbi_from_beamwidths(360.0, 10.0)

    def test_non_numeric_beamwidth_raises(self):
        with self.assertRaises(ValueError):
            logic.directivity_dbi_from_beamwidths("2.0", 2.0)

    def test_unit_efficiency_leaves_directivity_unchanged(self):
        self.assertAlmostEqual(logic.antenna_gain_dbi(40.0, 1.0), 40.0, places=9)

    def test_partial_efficiency_reduces_antenna_gain(self):
        self.assertAlmostEqual(logic.antenna_gain_dbi(40.0, 0.6), 37.78151250, places=6)

    def test_zero_efficiency_raises(self):
        with self.assertRaises(ValueError):
            logic.antenna_gain_dbi(40.0, 0.0)

    def test_efficiency_above_unity_raises(self):
        with self.assertRaises(ValueError):
            logic.antenna_gain_dbi(40.0, 1.2)


class TestPolarisationPurity(unittest.TestCase):
    def test_one_decibel_axial_ratio(self):
        self.assertAlmostEqual(
            logic.cross_polar_discrimination_db(1.0), 24.80647275, places=6
        )

    def test_three_decibel_axial_ratio(self):
        self.assertAlmostEqual(
            logic.cross_polar_discrimination_db(3.0), 15.34021203, places=6
        )

    def test_discrimination_collapses_as_axial_ratio_grows(self):
        self.assertGreater(
            logic.cross_polar_discrimination_db(0.5),
            logic.cross_polar_discrimination_db(1.0),
        )

    def test_ideal_circular_polarisation_is_unbounded(self):
        self.assertEqual(logic.cross_polar_discrimination_db(0.0), float("inf"))

    def test_negative_axial_ratio_raises(self):
        with self.assertRaises(ValueError):
            logic.cross_polar_discrimination_db(-0.1)

    def test_non_finite_axial_ratio_raises(self):
        with self.assertRaises(ValueError):
            logic.cross_polar_discrimination_db(float("nan"))


class TestPointingErrorBudget(unittest.TestCase):
    def test_root_sum_square_total(self):
        report = logic.boresight_pointing_error_budget(
            {"thermal-distortion": 0.1, "alignment-residual": 0.2, "deployment": 0.05}, 0.5
        )
        self.assertAlmostEqual(report["total-deg"], 0.22912878, places=6)
        self.assertTrue(report["compliant"])

    def test_budget_exactly_on_the_allowable_is_compliant(self):
        report = logic.boresight_pointing_error_budget(
            {"a": 0.3, "b": 0.4}, 0.5
        )
        self.assertAlmostEqual(report["total-deg"], 0.5, places=12)
        self.assertTrue(report["compliant"])

    def test_exceeding_budget_is_not_compliant(self):
        report = logic.boresight_pointing_error_budget({"a": 0.6}, 0.5)
        self.assertFalse(report["compliant"])
        self.assertLess(report["remaining-deg"], 0.0)

    def test_arithmetic_sum_would_have_failed_where_rss_passes(self):
        report = logic.boresight_pointing_error_budget({"a": 0.3, "b": 0.3}, 0.5)
        self.assertTrue(report["compliant"])

    def test_empty_contributor_map_raises(self):
        with self.assertRaises(ValueError):
            logic.boresight_pointing_error_budget({}, 0.5)

    def test_negative_contributor_raises(self):
        with self.assertRaises(ValueError):
            logic.boresight_pointing_error_budget({"a": -0.1}, 0.5)

    def test_non_positive_allowable_raises(self):
        with self.assertRaises(ValueError):
            logic.boresight_pointing_error_budget({"a": 0.1}, 0.0)


class TestRecordEvaluation(unittest.TestCase):
    def test_upper_bound_parameter_within_limit(self):
        result = logic.evaluate_parameter_record(
            {"name": "side-lobe-level", "value": -22.0, "bound": -20.0}
        )
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin"], 2.0, places=9)

    def test_upper_bound_parameter_violated(self):
        result = logic.evaluate_parameter_record(
            {"name": "axial-ratio", "value": 3.5, "bound": 3.0}
        )
        self.assertFalse(result["compliant"])

    def test_lower_bound_parameter_within_limit(self):
        result = logic.evaluate_parameter_record(
            {"name": "edge-of-coverage-level", "value": -2.0, "bound": -3.0}
        )
        self.assertTrue(result["compliant"])

    def test_lower_bound_parameter_violated(self):
        result = logic.evaluate_parameter_record(
            {"name": "peak-antenna-gain", "value": 28.0, "bound": 30.0}
        )
        self.assertFalse(result["compliant"])

    def test_value_exactly_on_a_bound_built_from_a_difference_is_compliant(self):
        value = 0.1 + 0.2
        result = logic.evaluate_parameter_record(
            {"name": "boresight-pointing-error", "value": value, "bound": 0.3}
        )
        self.assertTrue(result["compliant"])

    def test_explicit_direction_override(self):
        result = logic.evaluate_parameter_record(
            {"name": "operating-bandwidth", "value": 40.0, "bound": 50.0, "direction": "max"}
        )
        self.assertTrue(result["compliant"])

    def test_bad_direction_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_parameter_record(
                {"name": "axial-ratio", "value": 1.0, "bound": 3.0, "direction": "below"}
            )

    def test_non_numeric_parameter_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_parameter_record(
                {"name": "polarisation-sense", "value": 1.0, "bound": 1.0}
            )

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_parameter_record(["axial-ratio", 1.0, 3.0])

    def test_missing_value_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_parameter_record({"name": "axial-ratio", "bound": 3.0})


class TestDerivedConsistency(unittest.TestCase):
    def test_agreeing_values_are_consistent(self):
        result = logic.check_derived_consistency(37.8, 37.78151250, 0.5)
        self.assertTrue(result["consistent"])

    def test_disagreement_beyond_tolerance_is_flagged(self):
        result = logic.check_derived_consistency(40.0, 37.78151250, 0.5)
        self.assertFalse(result["consistent"])

    def test_delta_exactly_on_the_tolerance_is_consistent(self):
        result = logic.check_derived_consistency(0.1 + 0.2, 0.0, 0.3)
        self.assertTrue(result["consistent"])

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            logic.check_derived_consistency(1.0, 1.0, -0.1)


class TestFullAssessment(unittest.TestCase):
    def _good_records(self):
        return [
            {"name": "half-power-beamwidth", "value": 2.0, "bound": 1.0},
            {"name": "peak-antenna-gain", "value": 37.8, "bound": 36.0},
            {"name": "radiation-efficiency", "value": 0.6, "bound": 0.5},
            {"name": "side-lobe-level", "value": -22.0, "bound": -20.0},
            "boresight-direction",
            {"name": "boresight-pointing-error", "value": 0.2, "bound": 0.25},
            {"name": "input-vswr", "value": 1.3, "bound": 1.5},
            {"name": "operating-bandwidth", "value": 60.0, "bound": 50.0},
        ]

    def test_complete_compliant_set_passes(self):
        report = logic.assess_parameter_set("payload-downlink", self._good_records())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["findings"], [])

    def test_missing_entry_produces_a_finding(self):
        records = [r for r in self._good_records() if r != "boresight-direction"]
        report = logic.assess_parameter_set("payload-downlink", records)
        self.assertFalse(report["compliant"])
        self.assertTrue(any("missing mandatory" in f for f in report["findings"]))

    def test_violated_bound_produces_a_finding(self):
        records = self._good_records()
        records[3] = {"name": "side-lobe-level", "value": -18.0, "bound": -20.0}
        report = logic.assess_parameter_set("payload-downlink", records)
        self.assertFalse(report["compliant"])
        self.assertTrue(any("side-lobe-level" in f for f in report["findings"]))

    def test_pointing_budget_exceedance_produces_a_finding(self):
        report = logic.assess_parameter_set(
            "payload-downlink",
            self._good_records(),
            pointing_budget={
                "contributors": {"thermal-distortion": 0.3, "alignment-residual": 0.3},
                "allowable_deg": 0.25,
            },
        )
        self.assertFalse(report["compliant"])
        self.assertTrue(any("boresight-pointing-error budget" in f for f in report["findings"]))

    def test_compliant_pointing_budget_is_attached(self):
        report = logic.assess_parameter_set(
            "payload-downlink",
            self._good_records(),
            pointing_budget={
                "contributors": {"thermal-distortion": 0.1, "alignment-residual": 0.1},
                "allowable_deg": 0.25,
            },
        )
        self.assertTrue(report["compliant"])
        self.assertIsNotNone(report["pointing-budget"])

    def test_empty_records_raise(self):
        with self.assertRaises(ValueError):
            logic.assess_parameter_set("payload-downlink", [])

    def test_non_sequence_records_raise(self):
        with self.assertRaises(ValueError):
            logic.assess_parameter_set("payload-downlink", {"name": "axial-ratio"})

    def test_bad_pointing_budget_type_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_parameter_set(
                "payload-downlink", self._good_records(), pointing_budget=[0.1, 0.2]
            )


if __name__ == "__main__":
    unittest.main()
