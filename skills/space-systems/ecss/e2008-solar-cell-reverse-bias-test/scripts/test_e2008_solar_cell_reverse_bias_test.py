#!/usr/bin/env python3
"""Contract test for the solar cell reverse bias test, clause 7.5.16 (offline)."""

import copy
import unittest

from e2008_solar_cell_reverse_bias_test_logic import (
    DEFAULT_REVERSE_BIAS_POLICY,
    LOT_OPEN,
    LOT_PASSED,
    OUTPUT_OVER_ALLOWANCE,
    OUTPUT_UNCHANGED,
    OUTPUT_WITHIN_ALLOWANCE,
    SPECIMEN_FAILED,
    SPECIMEN_NOT_EVALUATED,
    SPECIMEN_PASSED,
    STRESS_AS_DECLARED,
    STRESS_OVER_TEMPERATURE,
    STRESS_SHORT,
    STRESS_SUPPLY_CLAMPED,
    assess_reverse_bias_test,
    assess_specimen,
    categorize_output_change,
    dissipated_power_w,
    parameter_losses,
    read_measurement,
    read_reverse_stress,
    reference_conditions_match,
    validate_reverse_bias_policy,
    worst_output_category,
)


def _measurement(pmax=1.200, isc=0.500, voc=2.700, **overrides):
    record = {
        "pmax_w": pmax,
        "isc_a": isc,
        "voc_v": voc,
        "irradiance_w_m2": 1367.0,
        "temperature_c": 28.0,
    }
    record.update(overrides)
    return record


def _stress(**overrides):
    record = {
        "reverse_current_a": 0.500,
        "reverse_voltage_v": 12.0,
        "supply_compliance_v": 20.0,
        "dwell_s": 60.0,
        "temperature_c": 60.0,
    }
    record.update(overrides)
    return record


def _specimen(specimen_id="cell-a", before=None, after=None, stress=None):
    return {
        "specimen_id": specimen_id,
        "before": before if before is not None else _measurement(),
        "after": after if after is not None else _measurement(),
        "stress": stress if stress is not None else _stress(),
    }


def _case(*specimens):
    return {
        "specimens": list(specimens)
        or [_specimen("cell-a"), _specimen("cell-b"), _specimen("cell-c")]
    }


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_reverse_bias_policy(DEFAULT_REVERSE_BIAS_POLICY),
            DEFAULT_REVERSE_BIAS_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_reverse_bias_policy("push it backwards")

    def test_zero_reverse_current_requirement_rejected(self):
        broken = copy.deepcopy(DEFAULT_REVERSE_BIAS_POLICY)
        broken["required_reverse_current_a"] = 0.0
        with self.assertRaises(ValueError):
            validate_reverse_bias_policy(broken)

    def test_unchanged_band_wider_than_an_allowance_rejected(self):
        broken = copy.deepcopy(DEFAULT_REVERSE_BIAS_POLICY)
        broken["unchanged_loss_fraction"] = 0.5
        with self.assertRaises(ValueError):
            validate_reverse_bias_policy(broken)

    def test_negative_condition_tolerance_rejected(self):
        broken = copy.deepcopy(DEFAULT_REVERSE_BIAS_POLICY)
        broken["max_temperature_delta_c"] = -1.0
        with self.assertRaises(ValueError):
            validate_reverse_bias_policy(broken)

    def test_non_integer_specimen_floor_rejected(self):
        broken = copy.deepcopy(DEFAULT_REVERSE_BIAS_POLICY)
        broken["min_specimens"] = "three"
        with self.assertRaises(ValueError):
            validate_reverse_bias_policy(broken)


class MeasurementTests(unittest.TestCase):
    def test_measurement_reads_back(self):
        read = read_measurement(_measurement(), "before")
        self.assertAlmostEqual(read["pmax_w"], 1.200, places=9)
        self.assertAlmostEqual(read["irradiance_w_m2"], 1367.0, places=9)

    def test_non_mapping_measurement_rejected(self):
        with self.assertRaises(ValueError):
            read_measurement("one point two watts", "before")

    def test_zero_maximum_power_rejected(self):
        with self.assertRaises(ValueError):
            read_measurement(_measurement(pmax=0.0), "before")

    def test_missing_irradiance_rejected(self):
        broken = _measurement()
        del broken["irradiance_w_m2"]
        with self.assertRaises(ValueError):
            read_measurement(broken, "after")

    def test_matched_conditions_are_comparable(self):
        match = reference_conditions_match(
            read_measurement(_measurement(), "before"),
            read_measurement(_measurement(), "after"),
        )
        self.assertTrue(match["comparable"])
        self.assertEqual(match["findings"], [])

    def test_a_warmer_post_measurement_is_refused(self):
        match = reference_conditions_match(
            read_measurement(_measurement(), "before"),
            read_measurement(_measurement(temperature_c=40.0), "after"),
        )
        self.assertFalse(match["comparable"])
        self.assertAlmostEqual(match["temperature_delta_c"], 12.0, places=9)

    def test_a_shifted_irradiance_is_refused(self):
        match = reference_conditions_match(
            read_measurement(_measurement(), "before"),
            read_measurement(_measurement(irradiance_w_m2=1300.0), "after"),
        )
        self.assertFalse(match["comparable"])

    def test_a_shift_inside_the_tolerance_is_still_comparable(self):
        match = reference_conditions_match(
            read_measurement(_measurement(), "before"),
            read_measurement(_measurement(temperature_c=28.5), "after"),
        )
        self.assertTrue(match["comparable"])


class StressTests(unittest.TestCase):
    def test_declared_stress_is_accepted(self):
        read = read_reverse_stress(_stress())
        self.assertEqual(read["status"], STRESS_AS_DECLARED)
        self.assertEqual(read["findings"], [])

    def test_dissipated_power_is_the_voltage_current_product(self):
        self.assertAlmostEqual(dissipated_power_w(12.0, 0.5), 6.0, places=9)

    def test_dissipation_is_reported_with_the_stress(self):
        read = read_reverse_stress(_stress())
        self.assertAlmostEqual(read["dissipated_power_w"], 6.0, places=9)
        self.assertTrue(read["dissipation_within_cap"])

    def test_a_run_held_at_supply_compliance_is_grouped_on_its_own(self):
        read = read_reverse_stress(
            _stress(reverse_current_a=0.200, reverse_voltage_v=20.0)
        )
        self.assertEqual(read["status"], STRESS_SUPPLY_CLAMPED)
        self.assertTrue(any("supply compliance" in t for t in read["findings"]))

    def test_a_short_current_below_compliance_is_only_short(self):
        read = read_reverse_stress(
            _stress(reverse_current_a=0.200, reverse_voltage_v=5.0)
        )
        self.assertEqual(read["status"], STRESS_SHORT)

    def test_a_short_dwell_is_reported(self):
        read = read_reverse_stress(_stress(dwell_s=10.0))
        self.assertEqual(read["status"], STRESS_SHORT)
        self.assertTrue(any("held the stress" in t for t in read["findings"]))

    def test_a_dwell_exactly_on_the_minimum_is_accepted(self):
        read = read_reverse_stress(
            _stress(dwell_s=DEFAULT_REVERSE_BIAS_POLICY["min_dwell_s"])
        )
        self.assertEqual(read["status"], STRESS_AS_DECLARED)

    def test_an_over_temperature_run_is_grouped_on_its_own(self):
        read = read_reverse_stress(_stress(temperature_c=120.0))
        self.assertEqual(read["status"], STRESS_OVER_TEMPERATURE)

    def test_dissipation_past_the_hot_spot_cap_is_reported(self):
        read = read_reverse_stress(
            _stress(reverse_voltage_v=25.0, supply_compliance_v=30.0)
        )
        self.assertEqual(read["status"], STRESS_AS_DECLARED)
        self.assertFalse(read["dissipation_within_cap"])
        self.assertAlmostEqual(read["dissipated_power_w"], 12.5, places=9)

    def test_a_voltage_above_its_own_compliance_rejected(self):
        with self.assertRaises(ValueError):
            read_reverse_stress(
                _stress(reverse_voltage_v=25.0, supply_compliance_v=20.0)
            )

    def test_negative_reverse_current_rejected(self):
        with self.assertRaises(ValueError):
            read_reverse_stress(_stress(reverse_current_a=-0.5))

    def test_non_mapping_stress_rejected(self):
        with self.assertRaises(ValueError):
            read_reverse_stress("half an amp backwards")


class LossTests(unittest.TestCase):
    def test_an_unchanged_cell_reports_no_loss(self):
        losses = parameter_losses(_measurement(), _measurement())
        for value in losses.values():
            self.assertAlmostEqual(value, 0.0, places=9)

    def test_a_power_loss_is_the_share_of_the_baseline(self):
        losses = parameter_losses(_measurement(), _measurement(pmax=1.140))
        self.assertAlmostEqual(losses["pmax_w"], 0.05, places=9)

    def test_a_zero_baseline_parameter_rejected(self):
        with self.assertRaises(ValueError):
            parameter_losses(_measurement(pmax=0.0), _measurement())

    def test_small_losses_are_grouped_as_unchanged(self):
        grouped = categorize_output_change(
            {"pmax_w": 0.0005, "isc_a": 0.0, "voc_v": 0.0}
        )
        self.assertEqual(grouped["pmax_w"], OUTPUT_UNCHANGED)

    def test_a_loss_inside_its_allowance_is_grouped_apart_from_unchanged(self):
        grouped = categorize_output_change(
            {"pmax_w": 0.015, "isc_a": 0.0, "voc_v": 0.0}
        )
        self.assertEqual(grouped["pmax_w"], OUTPUT_WITHIN_ALLOWANCE)

    def test_a_loss_exactly_on_its_allowance_stays_within_it(self):
        grouped = categorize_output_change(
            {
                "pmax_w": DEFAULT_REVERSE_BIAS_POLICY["max_pmax_loss_fraction"],
                "isc_a": 0.0,
                "voc_v": 0.0,
            }
        )
        self.assertEqual(grouped["pmax_w"], OUTPUT_WITHIN_ALLOWANCE)

    def test_each_parameter_carries_its_own_allowance(self):
        grouped = categorize_output_change(
            {"pmax_w": 0.015, "isc_a": 0.015, "voc_v": 0.0}
        )
        self.assertEqual(grouped["pmax_w"], OUTPUT_WITHIN_ALLOWANCE)
        self.assertEqual(grouped["isc_a"], OUTPUT_OVER_ALLOWANCE)

    def test_a_missing_parameter_rejected(self):
        with self.assertRaises(ValueError):
            categorize_output_change({"pmax_w": 0.0, "isc_a": 0.0})

    def test_the_worst_grouping_is_reported(self):
        grouped = {
            "pmax_w": OUTPUT_UNCHANGED,
            "isc_a": OUTPUT_WITHIN_ALLOWANCE,
            "voc_v": OUTPUT_OVER_ALLOWANCE,
        }
        self.assertEqual(worst_output_category(grouped), OUTPUT_OVER_ALLOWANCE)

    def test_an_empty_grouping_rejected(self):
        with self.assertRaises(ValueError):
            worst_output_category({})


class SpecimenTests(unittest.TestCase):
    def test_a_clean_specimen_passes(self):
        record = assess_specimen(_specimen())
        self.assertEqual(record["verdict"], SPECIMEN_PASSED)
        self.assertEqual(record["findings"], [])
        self.assertEqual(record["worst_category"], OUTPUT_UNCHANGED)

    def test_a_power_loss_past_the_allowance_fails_the_specimen(self):
        record = assess_specimen(_specimen(after=_measurement(pmax=1.140)))
        self.assertEqual(record["verdict"], SPECIMEN_FAILED)
        self.assertEqual(record["parameters_over_allowance"], ["pmax_w"])

    def test_a_shunted_junction_shows_up_on_the_current(self):
        record = assess_specimen(_specimen(after=_measurement(isc=0.480)))
        self.assertEqual(record["verdict"], SPECIMEN_FAILED)
        self.assertIn("isc_a", record["parameters_over_allowance"])

    def test_a_breakdown_path_shows_up_on_the_voltage(self):
        record = assess_specimen(_specimen(after=_measurement(voc=2.600)))
        self.assertEqual(record["verdict"], SPECIMEN_FAILED)
        self.assertIn("voc_v", record["parameters_over_allowance"])

    def test_a_clamped_supply_leaves_the_specimen_unsentenced(self):
        record = assess_specimen(
            _specimen(stress=_stress(reverse_current_a=0.200, reverse_voltage_v=20.0))
        )
        self.assertEqual(record["verdict"], SPECIMEN_NOT_EVALUATED)
        self.assertFalse(record["stress_delivered"])

    def test_mismatched_reference_conditions_leave_the_specimen_unsentenced(self):
        record = assess_specimen(_specimen(after=_measurement(temperature_c=45.0)))
        self.assertEqual(record["verdict"], SPECIMEN_NOT_EVALUATED)
        self.assertFalse(record["conditions"]["comparable"])

    def test_dissipation_past_the_cap_fails_an_otherwise_clean_specimen(self):
        record = assess_specimen(
            _specimen(stress=_stress(reverse_voltage_v=25.0, supply_compliance_v=30.0))
        )
        self.assertEqual(record["verdict"], SPECIMEN_FAILED)
        self.assertTrue(any("hot-spot cap" in t for t in record["findings"]))

    def test_specimen_without_an_identifier_rejected(self):
        broken = _specimen()
        del broken["specimen_id"]
        with self.assertRaises(ValueError):
            assess_specimen(broken)

    def test_specimen_missing_its_stress_record_rejected(self):
        broken = _specimen()
        del broken["stress"]
        with self.assertRaises(ValueError):
            assess_specimen(broken)


class RunTests(unittest.TestCase):
    def test_a_clean_run_passes_the_lot(self):
        result = assess_reverse_bias_test(_case())
        self.assertEqual(result["verdict"], LOT_PASSED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["specimen_count"], 3)

    def test_a_failed_specimen_opens_the_lot(self):
        case = _case(
            _specimen("cell-a"),
            _specimen("cell-b"),
            _specimen("cell-c", after=_measurement(pmax=1.100)),
        )
        result = assess_reverse_bias_test(case)
        self.assertEqual(result["verdict"], LOT_OPEN)
        self.assertEqual(result["specimens_by_verdict"][SPECIMEN_FAILED], ["cell-c"])

    def test_an_unsentenced_specimen_opens_the_lot(self):
        case = _case(
            _specimen("cell-a"),
            _specimen("cell-b"),
            _specimen("cell-c", stress=_stress(dwell_s=5.0)),
        )
        result = assess_reverse_bias_test(case)
        self.assertEqual(result["verdict"], LOT_OPEN)
        self.assertTrue(any("unsentenced" in t for t in result["findings"]))

    def test_a_run_short_of_specimens_opens_the_lot(self):
        result = assess_reverse_bias_test(_case(_specimen("cell-a")))
        self.assertEqual(result["verdict"], LOT_OPEN)
        self.assertFalse(result["population_met"])

    def test_records_come_back_in_identifier_order(self):
        case = _case(_specimen("cell-c"), _specimen("cell-a"), _specimen("cell-b"))
        result = assess_reverse_bias_test(case)
        self.assertEqual(
            [r["specimen_id"] for r in result["specimen_records"]],
            ["cell-a", "cell-b", "cell-c"],
        )

    def test_the_worst_loss_per_parameter_is_reported(self):
        case = _case(
            _specimen("cell-a"),
            _specimen("cell-b", after=_measurement(pmax=1.188)),
            _specimen("cell-c", after=_measurement(pmax=1.176)),
        )
        result = assess_reverse_bias_test(case)
        self.assertAlmostEqual(result["worst_losses"]["pmax_w"], 0.02, places=9)

    def test_the_peak_dissipation_is_reported(self):
        result = assess_reverse_bias_test(_case())
        self.assertAlmostEqual(result["peak_dissipated_power_w"], 6.0, places=9)

    def test_repeated_specimen_identifier_rejected(self):
        case = _case(_specimen("cell-a"), _specimen("cell-a"), _specimen("cell-b"))
        with self.assertRaises(ValueError):
            assess_reverse_bias_test(case)

    def test_empty_run_rejected(self):
        with self.assertRaises(ValueError):
            assess_reverse_bias_test({"specimens": []})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_reverse_bias_test([_specimen()])

    def test_the_lot_carries_every_specimen_finding(self):
        case = _case(
            _specimen("cell-a"),
            _specimen("cell-b"),
            _specimen("cell-c", after=_measurement(pmax=1.100)),
        )
        result = assess_reverse_bias_test(case)
        self.assertTrue(any("cell-c" in t for t in result["findings"]))


if __name__ == "__main__":
    unittest.main()
