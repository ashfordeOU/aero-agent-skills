#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-Q-ST-60-13C Table 8-7 resistor chip test matrix.

Exercises scripts/q6013_resistor_chip_test_table_logic.py (stdlib
unittest, offline). Contract: lot validation, sampling-rule resolution,
resistance tolerance band, temperature coefficient, directional limit
comparison, matrix coverage, per-row verdict, the accept-or-hold
disposition, and ValueError on invalid input.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import q6013_resistor_chip_test_table_logic as rchip  # noqa: E402


def row(group, **overrides):
    entry = {
        "group": group,
        "method": "method-ref-%s" % group,
        "sampling": {"mode": "fixed", "size": 10},
        "failures": 0,
        "accept_number": 1,
    }
    entry.update(overrides)
    return entry


FULL_MATRIX = [row(group) for group in rchip.REQUIRED_TEST_GROUPS]


def full_spec(**overrides):
    spec = {"lot_size": 500, "entries": [dict(e) for e in FULL_MATRIX]}
    spec.update(overrides)
    return spec


class LotValidationTest(unittest.TestCase):
    def test_positive_lot_accepted(self):
        self.assertEqual(rchip.validate_lot_size(500), 500)

    def test_zero_lot_raises(self):
        with self.assertRaises(ValueError):
            rchip.validate_lot_size(0)

    def test_negative_lot_raises(self):
        with self.assertRaises(ValueError):
            rchip.validate_lot_size(-5)

    def test_non_integer_lot_raises(self):
        with self.assertRaises(ValueError):
            rchip.validate_lot_size(500.0)

    def test_boolean_lot_raises(self):
        with self.assertRaises(ValueError):
            rchip.validate_lot_size(True)


class SampleResolutionTest(unittest.TestCase):
    def test_whole_lot_rule_returns_the_lot(self):
        self.assertEqual(rchip.resolve_sample_size({"mode": "all"}, 250), 250)

    def test_fixed_rule_returns_its_size(self):
        self.assertEqual(
            rchip.resolve_sample_size({"mode": "fixed", "size": 22}, 250), 22
        )

    def test_percent_rule_rounds_up_to_whole_devices(self):
        self.assertEqual(
            rchip.resolve_sample_size({"mode": "percent", "percent": 2.0}, 101), 3
        )

    def test_percent_landing_on_a_whole_device_gains_nothing(self):
        # 10 percent of 500 is exactly 50 devices; a float product that
        # lands a few units in the last place high must not become 51.
        self.assertEqual(
            rchip.resolve_sample_size({"mode": "percent", "percent": 10.0}, 500), 50
        )

    def test_percent_floor_raises_a_small_lot_sample(self):
        self.assertEqual(
            rchip.resolve_sample_size(
                {"mode": "percent", "percent": 1.0, "minimum": 5}, 100
            ),
            5,
        )

    def test_percent_sample_never_exceeds_the_lot(self):
        self.assertEqual(
            rchip.resolve_sample_size({"mode": "percent", "percent": 100.0}, 7), 7
        )

    def test_fixed_sample_larger_than_the_lot_raises(self):
        with self.assertRaises(ValueError):
            rchip.resolve_sample_size({"mode": "fixed", "size": 40}, 30)

    def test_unknown_sampling_mode_raises(self):
        with self.assertRaises(ValueError):
            rchip.resolve_sample_size({"mode": "every-other-one"}, 100)

    def test_percent_outside_its_range_raises(self):
        with self.assertRaises(ValueError):
            rchip.resolve_sample_size({"mode": "percent", "percent": 0.0}, 100)
        with self.assertRaises(ValueError):
            rchip.resolve_sample_size({"mode": "percent", "percent": 140.0}, 100)

    def test_floor_larger_than_the_lot_raises(self):
        with self.assertRaises(ValueError):
            rchip.resolve_sample_size(
                {"mode": "percent", "percent": 1.0, "minimum": 200}, 100
            )


class ResistanceBandTest(unittest.TestCase):
    def test_band_is_symmetric_about_the_nominal(self):
        low, high = rchip.resistance_tolerance_band(1000.0, 1.0)
        self.assertAlmostEqual(low, 990.0, places=9)
        self.assertAlmostEqual(high, 1010.0, places=9)

    def test_value_inside_the_band_passes(self):
        self.assertTrue(rchip.within_tolerance_band(1005.0, 1000.0, 1.0))

    def test_value_exactly_on_the_upper_edge_is_inside(self):
        self.assertTrue(rchip.within_tolerance_band(1010.0, 1000.0, 1.0))

    def test_value_exactly_on_the_lower_edge_is_inside(self):
        self.assertTrue(rchip.within_tolerance_band(990.0, 1000.0, 1.0))

    def test_value_outside_the_band_fails(self):
        self.assertFalse(rchip.within_tolerance_band(1011.0, 1000.0, 1.0))

    def test_non_positive_nominal_raises(self):
        with self.assertRaises(ValueError):
            rchip.resistance_tolerance_band(0.0, 1.0)

    def test_tolerance_outside_its_range_raises(self):
        with self.assertRaises(ValueError):
            rchip.resistance_tolerance_band(1000.0, 0.0)
        with self.assertRaises(ValueError):
            rchip.resistance_tolerance_band(1000.0, 100.0)


class TemperatureCoefficientTest(unittest.TestCase):
    def test_rising_resistance_gives_a_positive_coefficient(self):
        ppm = rchip.temperature_coefficient_ppm(1000.0, 1001.0, 25.0, 125.0)
        self.assertAlmostEqual(ppm, 10.0, places=9)

    def test_falling_resistance_gives_a_negative_coefficient(self):
        ppm = rchip.temperature_coefficient_ppm(1000.0, 999.0, 25.0, 125.0)
        self.assertAlmostEqual(ppm, -10.0, places=9)

    def test_unchanged_resistance_gives_a_zero_coefficient(self):
        ppm = rchip.temperature_coefficient_ppm(1000.0, 1000.0, 25.0, 125.0)
        self.assertAlmostEqual(ppm, 0.0, places=9)

    def test_cooling_leg_gives_the_same_sign_convention(self):
        ppm = rchip.temperature_coefficient_ppm(1000.0, 999.0, 25.0, -55.0)
        self.assertAlmostEqual(ppm, 12.5, places=9)

    def test_same_temperature_raises(self):
        with self.assertRaises(ValueError):
            rchip.temperature_coefficient_ppm(1000.0, 1001.0, 25.0, 25.0)

    def test_non_positive_reference_resistance_raises(self):
        with self.assertRaises(ValueError):
            rchip.temperature_coefficient_ppm(0.0, 1001.0, 25.0, 125.0)


class LimitDirectionTest(unittest.TestCase):
    def test_upper_bound_accepts_below_and_at_the_limit(self):
        self.assertTrue(rchip.within_limit(45.0, 50.0, "max"))
        self.assertTrue(rchip.within_limit(50.0, 50.0, "max"))
        self.assertFalse(rchip.within_limit(50.5, 50.0, "max"))

    def test_lower_bound_accepts_above_and_at_the_limit(self):
        self.assertTrue(rchip.within_limit(1.2e9, 1.0e9, "min"))
        self.assertTrue(rchip.within_limit(1.0e9, 1.0e9, "min"))
        self.assertFalse(rchip.within_limit(9.0e8, 1.0e9, "min"))

    def test_magnitude_bound_applies_either_way(self):
        self.assertTrue(rchip.within_limit(-0.5, 0.5, "abs-delta"))
        self.assertTrue(rchip.within_limit(0.5, 0.5, "abs-delta"))
        self.assertFalse(rchip.within_limit(-0.9, 0.5, "abs-delta"))

    def test_unknown_direction_raises(self):
        with self.assertRaises(ValueError):
            rchip.within_limit(1.0, 2.0, "sideways")

    def test_negative_magnitude_bound_raises(self):
        with self.assertRaises(ValueError):
            rchip.within_limit(1.0, -2.0, "abs-delta")

    def test_non_real_measurement_raises(self):
        with self.assertRaises(ValueError):
            rchip.within_limit("high", 2.0, "max")


class MeasurementRecordTest(unittest.TestCase):
    def test_record_carries_the_verdict(self):
        record = rchip.evaluate_measurement(
            {
                "parameter": "insulation-resistance",
                "measured": 2.0e9,
                "limit": 1.0e9,
                "direction": "min",
            }
        )
        self.assertTrue(record["within_limit"])
        self.assertEqual(record["parameter"], "insulation-resistance")

    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            rchip.evaluate_measurement({"parameter": "noise", "measured": 1.0})

    def test_blank_parameter_name_raises(self):
        with self.assertRaises(ValueError):
            rchip.evaluate_measurement(
                {"parameter": "  ", "measured": 1.0, "limit": 2.0, "direction": "max"}
            )


class MatrixCoverageTest(unittest.TestCase):
    def test_full_matrix_is_complete(self):
        coverage = rchip.matrix_coverage(FULL_MATRIX)
        self.assertTrue(coverage["complete"])
        self.assertEqual(coverage["missing"], [])
        self.assertEqual(coverage["duplicated"], [])

    def test_missing_group_reported(self):
        coverage = rchip.matrix_coverage(FULL_MATRIX[:-1])
        self.assertEqual(coverage["missing"], [rchip.REQUIRED_TEST_GROUPS[-1]])
        self.assertFalse(coverage["complete"])

    def test_duplicated_group_reported_once(self):
        coverage = rchip.matrix_coverage(FULL_MATRIX + [row("life-test")])
        self.assertEqual(coverage["duplicated"], ["life-test"])
        self.assertFalse(coverage["complete"])

    def test_extra_group_reported_as_unrecognized(self):
        coverage = rchip.matrix_coverage(FULL_MATRIX + [row("solderability")])
        self.assertEqual(coverage["unrecognized"], ["solderability"])

    def test_empty_matrix_raises(self):
        with self.assertRaises(ValueError):
            rchip.matrix_coverage([])


class RowVerdictTest(unittest.TestCase):
    def test_clean_row_accepts(self):
        verdict = rchip.row_verdict(row("life-test"), 500)
        self.assertTrue(verdict["accepted"])
        self.assertEqual(verdict["findings"], [])
        self.assertFalse(verdict["marginal"])

    def test_failures_over_the_accept_number_reject(self):
        verdict = rchip.row_verdict(row("life-test", failures=3, accept_number=1), 500)
        self.assertFalse(verdict["accepted"])
        self.assertEqual(len(verdict["findings"]), 1)

    def test_accept_number_consumed_exactly_is_marginal_not_a_reject(self):
        verdict = rchip.row_verdict(row("life-test", failures=1, accept_number=1), 500)
        self.assertTrue(verdict["accepted"])
        self.assertTrue(verdict["marginal"])

    def test_clean_count_with_an_out_of_limit_parameter_rejects(self):
        entry = row(
            "insulation-resistance",
            measurements=[
                {
                    "parameter": "insulation-resistance",
                    "measured": 5.0e8,
                    "limit": 1.0e9,
                    "direction": "min",
                }
            ],
        )
        verdict = rchip.row_verdict(entry, 500)
        self.assertFalse(verdict["accepted"])
        self.assertEqual(verdict["failures"], 0)

    def test_resistance_outside_its_band_rejects_the_row(self):
        entry = row(
            "resistance-measurement",
            resistance={
                "measured_ohms": 1015.0,
                "nominal_ohms": 1000.0,
                "tolerance_percent": 1.0,
            },
        )
        verdict = rchip.row_verdict(entry, 500)
        self.assertFalse(verdict["accepted"])
        self.assertFalse(verdict["resistance_in_band"])

    def test_resistance_on_the_band_edge_accepts_the_row(self):
        entry = row(
            "resistance-measurement",
            resistance={
                "measured_ohms": 1010.0,
                "nominal_ohms": 1000.0,
                "tolerance_percent": 1.0,
            },
        )
        verdict = rchip.row_verdict(entry, 500)
        self.assertTrue(verdict["accepted"])
        self.assertTrue(verdict["resistance_in_band"])

    def test_more_failures_than_the_sample_raises(self):
        entry = row("life-test", failures=40, sampling={"mode": "fixed", "size": 10})
        with self.assertRaises(ValueError):
            rchip.row_verdict(entry, 500)

    def test_accept_number_over_the_sample_raises(self):
        entry = row("life-test", accept_number=40, sampling={"mode": "fixed", "size": 10})
        with self.assertRaises(ValueError):
            rchip.row_verdict(entry, 500)

    def test_row_without_a_method_reference_raises(self):
        entry = row("life-test", method="   ")
        with self.assertRaises(ValueError):
            rchip.row_verdict(entry, 500)

    def test_incomplete_resistance_record_raises(self):
        entry = row("resistance-measurement", resistance={"measured_ohms": 1000.0})
        with self.assertRaises(ValueError):
            rchip.row_verdict(entry, 500)


class AssessmentTest(unittest.TestCase):
    def test_complete_clean_matrix_accepts_the_lot(self):
        verdict = rchip.assess_resistor_chip_test_table(full_spec())
        self.assertEqual(verdict["disposition"], "accept")
        self.assertTrue(verdict["accepted"])
        self.assertEqual(verdict["findings"], [])
        self.assertEqual(
            verdict["total_devices_tested"], 10 * len(rchip.REQUIRED_TEST_GROUPS)
        )

    def test_known_textbook_case_names_every_rejecting_group(self):
        entries = [dict(e) for e in FULL_MATRIX]
        entries[0] = row("visual-inspection", failures=4, accept_number=1)
        entries[2] = row(
            "resistance-measurement",
            resistance={
                "measured_ohms": 1100.0,
                "nominal_ohms": 1000.0,
                "tolerance_percent": 1.0,
            },
        )
        verdict = rchip.assess_resistor_chip_test_table(
            full_spec(entries=entries[:-1])
        )
        self.assertEqual(verdict["disposition"], "hold")
        self.assertIn("visual-inspection", verdict["rejecting_groups"])
        self.assertIn("resistance-measurement", verdict["rejecting_groups"])
        self.assertIn(
            rchip.REQUIRED_TEST_GROUPS[-1], verdict["coverage"]["missing"]
        )
        self.assertGreater(len(verdict["findings"]), 2)

    def test_marginal_row_is_an_advisory_not_a_hold(self):
        entries = [dict(e) for e in FULL_MATRIX]
        entries[5] = row("insulation-resistance", failures=1, accept_number=1)
        verdict = rchip.assess_resistor_chip_test_table(full_spec(entries=entries))
        self.assertEqual(verdict["disposition"], "accept")
        self.assertEqual(len(verdict["advisories"]), 1)

    def test_spec_missing_key_raises(self):
        with self.assertRaises(ValueError):
            rchip.assess_resistor_chip_test_table({"lot_size": 500})

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            rchip.assess_resistor_chip_test_table(["lot"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
