#!/usr/bin/env python3
"""Contract test for SCA acceptance electrical performance (offline)."""

import copy
import unittest

from e2008_sca_electrical_performance_acceptance_logic import (
    ASSEMBLY_ACCEPTED,
    ASSEMBLY_BELOW_DECLARED_MINIMUM,
    ASSEMBLY_CONDITIONS_OUT_OF_WINDOW,
    ASSEMBLY_POINT_INCONSISTENT,
    DEFAULT_SCA_ACCEPTANCE_POLICY,
    LOT_ACCEPTED,
    LOT_REJECTED,
    REFERENCE_IRRADIANCE_W_PER_M2,
    REFERENCE_TEMPERATURE_C,
    assess_acceptance_lot,
    assess_assembly,
    condition_window_status,
    correct_to_reference,
    margin_status,
    point_consistency,
    required_sample_count,
    validate_acceptance_policy,
    validate_coefficients,
    validate_reading,
)

NOMINAL_COEFFICIENTS = {
    "isc_a_per_c": 0.0003,
    "voc_v_per_c": -0.006,
    "pmax_w_per_c": -0.0035,
}

DECLARED_MINIMUM_W = 1.10


def _reading(**overrides):
    reading = {
        "irradiance_w_per_m2": REFERENCE_IRRADIANCE_W_PER_M2,
        "temperature_c": REFERENCE_TEMPERATURE_C,
        "isc_a": 0.50,
        "voc_v": 2.70,
        "pmax_w": 1.15,
    }
    reading.update(overrides)
    return reading


def _assembly(identifier="sca-0001", **overrides):
    entry = {
        "identifier": identifier,
        "reading": _reading(),
        "coefficients": dict(NOMINAL_COEFFICIENTS),
        "declared_minimum_pmax_w": DECLARED_MINIMUM_W,
    }
    entry.update(overrides)
    return entry


def _lot(measured=5, lot_size=50, weak=0):
    entries = []
    for index in range(measured):
        identifier = "sca-%04d" % (index + 1)
        if index < weak:
            entries.append(
                _assembly(identifier, reading=_reading(pmax_w=1.02))
            )
        else:
            entries.append(_assembly(identifier))
    return {"lot_size": lot_size, "assemblies": entries}


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_acceptance_policy(DEFAULT_SCA_ACCEPTANCE_POLICY),
            DEFAULT_SCA_ACCEPTANCE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceptance_policy("flash the lot")

    def test_inverted_fill_factor_band_rejected(self):
        broken = copy.deepcopy(DEFAULT_SCA_ACCEPTANCE_POLICY)
        broken["min_fill_factor"] = 0.95
        with self.assertRaises(ValueError):
            validate_acceptance_policy(broken)

    def test_out_of_range_reject_share_rejected(self):
        broken = copy.deepcopy(DEFAULT_SCA_ACCEPTANCE_POLICY)
        broken["max_reject_fraction"] = 1.8
        with self.assertRaises(ValueError):
            validate_acceptance_policy(broken)

    def test_zero_sample_floor_rejected(self):
        broken = copy.deepcopy(DEFAULT_SCA_ACCEPTANCE_POLICY)
        broken["min_sample_count"] = 0
        with self.assertRaises(ValueError):
            validate_acceptance_policy(broken)


class ReadingTests(unittest.TestCase):
    def test_nominal_reading_validates(self):
        values = validate_reading(_reading())
        self.assertAlmostEqual(values["pmax_w"], 1.15, places=9)

    def test_reading_missing_a_quantity_rejected(self):
        reading = _reading()
        del reading["voc_v"]
        with self.assertRaises(ValueError):
            validate_reading(reading)

    def test_zero_irradiance_rejected(self):
        with self.assertRaises(ValueError):
            validate_reading(_reading(irradiance_w_per_m2=0.0))

    def test_negative_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_reading(_reading(isc_a=-0.5))

    def test_boolean_power_rejected(self):
        with self.assertRaises(ValueError):
            validate_reading(_reading(pmax_w=True))

    def test_coefficients_missing_a_key_rejected(self):
        drift = dict(NOMINAL_COEFFICIENTS)
        del drift["pmax_w_per_c"]
        with self.assertRaises(ValueError):
            validate_coefficients(drift)

    def test_coefficients_may_be_negative(self):
        drift = validate_coefficients(NOMINAL_COEFFICIENTS)
        self.assertAlmostEqual(drift["pmax_w_per_c"], -0.0035, places=9)


class ConditionWindowTests(unittest.TestCase):
    def test_reference_conditions_sit_in_the_window(self):
        status = condition_window_status(_reading())
        self.assertTrue(status["in_window"])
        self.assertEqual(status["findings"], [])

    def test_irradiance_exactly_on_the_window_edge_is_still_inside(self):
        edge = REFERENCE_IRRADIANCE_W_PER_M2 * (
            1.0 - DEFAULT_SCA_ACCEPTANCE_POLICY["irradiance_window_fraction"]
        )
        status = condition_window_status(_reading(irradiance_w_per_m2=edge))
        self.assertAlmostEqual(
            status["irradiance_offset_w_per_m2"],
            status["allowed_irradiance_offset_w_per_m2"],
            places=9,
        )
        self.assertTrue(status["in_window"])

    def test_temperature_exactly_on_the_window_edge_is_still_inside(self):
        edge = REFERENCE_TEMPERATURE_C + DEFAULT_SCA_ACCEPTANCE_POLICY[
            "temperature_window_c"
        ]
        status = condition_window_status(_reading(temperature_c=edge))
        self.assertAlmostEqual(status["temperature_offset_c"], 15.0, places=9)
        self.assertTrue(status["in_window"])

    def test_far_irradiance_falls_out_of_the_window(self):
        status = condition_window_status(_reading(irradiance_w_per_m2=1100.0))
        self.assertFalse(status["irradiance_in_window"])
        self.assertFalse(status["in_window"])
        self.assertTrue(any("irradiance" in f for f in status["findings"]))

    def test_far_temperature_falls_out_of_the_window(self):
        status = condition_window_status(_reading(temperature_c=60.0))
        self.assertFalse(status["temperature_in_window"])
        self.assertTrue(any("temperature" in f for f in status["findings"]))


class CorrectionTests(unittest.TestCase):
    def test_a_reading_at_reference_is_its_own_correction(self):
        corrected = correct_to_reference(_reading(), NOMINAL_COEFFICIENTS)
        self.assertAlmostEqual(corrected["irradiance_ratio"], 1.0, places=9)
        self.assertAlmostEqual(corrected["pmax_w"], 1.15, places=9)
        self.assertAlmostEqual(corrected["voc_v"], 2.70, places=9)

    def test_low_irradiance_scales_current_and_power_up(self):
        corrected = correct_to_reference(
            _reading(irradiance_w_per_m2=1300.0), NOMINAL_COEFFICIENTS
        )
        self.assertGreater(corrected["isc_a"], 0.50)
        self.assertGreater(corrected["pmax_w"], 1.15)

    def test_hot_reading_corrects_the_voltage_upward(self):
        corrected = correct_to_reference(
            _reading(temperature_c=45.0), NOMINAL_COEFFICIENTS
        )
        self.assertAlmostEqual(corrected["temperature_offset_c"], 20.0, places=9)
        self.assertAlmostEqual(corrected["voc_v"], 2.70 + 0.12, places=9)

    def test_correction_is_reversible_within_representation_error(self):
        hot = correct_to_reference(
            _reading(irradiance_w_per_m2=1300.0, temperature_c=35.0),
            NOMINAL_COEFFICIENTS,
        )
        expected = 1.15 * (REFERENCE_IRRADIANCE_W_PER_M2 / 1300.0) + 0.035
        self.assertAlmostEqual(hot["pmax_w"], expected, places=9)


class ConsistencyTests(unittest.TestCase):
    def test_nominal_point_is_consistent(self):
        corrected = correct_to_reference(_reading(), NOMINAL_COEFFICIENTS)
        result = point_consistency(corrected)
        self.assertTrue(result["consistent"])
        self.assertAlmostEqual(result["fill_factor"], 1.15 / (0.50 * 2.70), places=9)

    def test_power_above_its_own_envelope_is_inconsistent(self):
        corrected = correct_to_reference(
            _reading(pmax_w=1.45), NOMINAL_COEFFICIENTS
        )
        result = point_consistency(corrected)
        self.assertFalse(result["consistent"])
        self.assertTrue(any("envelope" in f for f in result["findings"]))

    def test_power_far_under_its_envelope_is_inconsistent(self):
        corrected = correct_to_reference(
            _reading(pmax_w=0.60), NOMINAL_COEFFICIENTS
        )
        self.assertFalse(point_consistency(corrected)["consistent"])

    def test_correction_driving_a_quantity_negative_is_inconsistent(self):
        drift = dict(NOMINAL_COEFFICIENTS)
        drift["voc_v_per_c"] = 0.30
        corrected = correct_to_reference(_reading(temperature_c=35.0), drift)
        result = point_consistency(corrected)
        self.assertFalse(result["consistent"])
        self.assertIsNone(result["fill_factor"])

    def test_corrected_point_missing_a_quantity_rejected(self):
        with self.assertRaises(ValueError):
            point_consistency({"isc_a": 0.5, "voc_v": 2.7})


class MarginTests(unittest.TestCase):
    def test_power_above_the_minimum_clears_it(self):
        result = margin_status(1.15, DECLARED_MINIMUM_W)
        self.assertTrue(result["clears_minimum"])
        self.assertAlmostEqual(result["margin_w"], 0.05, places=9)

    def test_power_exactly_on_the_minimum_clears_it(self):
        result = margin_status(DECLARED_MINIMUM_W, DECLARED_MINIMUM_W)
        self.assertAlmostEqual(result["margin_w"], 0.0, places=9)
        self.assertTrue(result["clears_minimum"])

    def test_power_under_the_minimum_does_not_clear_it(self):
        result = margin_status(1.02, DECLARED_MINIMUM_W)
        self.assertFalse(result["clears_minimum"])
        self.assertTrue(any("falls under" in f for f in result["findings"]))

    def test_zero_declared_minimum_rejected(self):
        with self.assertRaises(ValueError):
            margin_status(1.15, 0.0)


class AssemblyTests(unittest.TestCase):
    def test_nominal_assembly_is_accepted(self):
        record = assess_assembly(_assembly())
        self.assertEqual(record["verdict"], ASSEMBLY_ACCEPTED)
        self.assertTrue(record["accepted"])
        self.assertEqual(record["findings"], [])

    def test_weak_assembly_falls_under_the_declared_minimum(self):
        record = assess_assembly(_assembly(reading=_reading(pmax_w=1.02)))
        self.assertEqual(record["verdict"], ASSEMBLY_BELOW_DECLARED_MINIMUM)
        self.assertFalse(record["accepted"])

    def test_out_of_window_conditions_outrank_a_weak_reading(self):
        record = assess_assembly(
            _assembly(reading=_reading(irradiance_w_per_m2=1100.0, pmax_w=0.80))
        )
        self.assertEqual(record["verdict"], ASSEMBLY_CONDITIONS_OUT_OF_WINDOW)

    def test_inconsistent_point_outranks_a_weak_reading(self):
        record = assess_assembly(_assembly(reading=_reading(pmax_w=1.45)))
        self.assertEqual(record["verdict"], ASSEMBLY_POINT_INCONSISTENT)

    def test_findings_carry_the_assembly_identifier(self):
        record = assess_assembly(
            _assembly("sca-0042", reading=_reading(pmax_w=1.02))
        )
        self.assertTrue(all(f.startswith("sca-0042: ") for f in record["findings"]))

    def test_assembly_without_an_identifier_rejected(self):
        entry = _assembly()
        entry["identifier"] = "   "
        with self.assertRaises(ValueError):
            assess_assembly(entry)

    def test_non_mapping_assembly_rejected(self):
        with self.assertRaises(ValueError):
            assess_assembly("sca-0001")


class SampleSizeTests(unittest.TestCase):
    def test_small_lot_uses_the_policy_floor(self):
        self.assertEqual(required_sample_count(30), 5)

    def test_large_lot_uses_the_policy_share(self):
        self.assertEqual(required_sample_count(200), 20)

    def test_sample_never_exceeds_the_lot(self):
        self.assertEqual(required_sample_count(3), 3)

    def test_zero_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_count(0)


class LotTests(unittest.TestCase):
    def test_clean_lot_is_accepted(self):
        result = assess_acceptance_lot(_lot())
        self.assertEqual(result["verdict"], LOT_ACCEPTED)
        self.assertAlmostEqual(result["reject_fraction"], 0.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_thin_sample_rejects_the_lot(self):
        result = assess_acceptance_lot(_lot(measured=4))
        self.assertEqual(result["verdict"], LOT_REJECTED)
        self.assertFalse(result["sample_sufficient"])
        self.assertTrue(any("required" in f for f in result["findings"]))

    def test_one_weak_assembly_in_five_exceeds_the_reject_share(self):
        result = assess_acceptance_lot(_lot(measured=5, weak=1))
        self.assertEqual(result["verdict"], LOT_REJECTED)
        self.assertAlmostEqual(result["reject_fraction"], 0.20, places=9)
        self.assertFalse(result["reject_share_within_limit"])

    def test_reject_share_exactly_on_the_limit_is_still_within_it(self):
        result = assess_acceptance_lot(_lot(measured=20, lot_size=200, weak=1))
        self.assertAlmostEqual(result["reject_fraction"], 0.05, places=9)
        self.assertAlmostEqual(result["max_reject_fraction"], 0.05, places=9)
        self.assertTrue(result["reject_share_within_limit"])
        self.assertEqual(result["verdict"], LOT_ACCEPTED)

    def test_lot_groups_assemblies_by_verdict(self):
        grouped = assess_acceptance_lot(_lot(measured=5, weak=2))[
            "grouped_by_verdict"
        ]
        self.assertEqual(len(grouped[ASSEMBLY_BELOW_DECLARED_MINIMUM]), 2)
        self.assertEqual(len(grouped[ASSEMBLY_ACCEPTED]), 3)

    def test_lot_reports_the_mean_corrected_power(self):
        result = assess_acceptance_lot(_lot())
        self.assertAlmostEqual(result["mean_corrected_pmax_w"], 1.15, places=9)

    def test_lot_level_coefficients_and_minimum_are_inherited(self):
        case = _lot()
        for entry in case["assemblies"]:
            del entry["coefficients"]
            del entry["declared_minimum_pmax_w"]
        case["coefficients"] = dict(NOMINAL_COEFFICIENTS)
        case["declared_minimum_pmax_w"] = DECLARED_MINIMUM_W
        self.assertEqual(assess_acceptance_lot(case)["verdict"], LOT_ACCEPTED)

    def test_repeated_assembly_identifier_rejected(self):
        case = _lot()
        case["assemblies"][1]["identifier"] = case["assemblies"][0]["identifier"]
        with self.assertRaises(ValueError):
            assess_acceptance_lot(case)

    def test_measuring_more_assemblies_than_the_lot_holds_rejected(self):
        with self.assertRaises(ValueError):
            assess_acceptance_lot(_lot(measured=5, lot_size=4))

    def test_empty_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_acceptance_lot({"lot_size": 50, "assemblies": []})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_acceptance_lot([_assembly()])

    def test_non_mapping_assembly_entry_rejected(self):
        case = _lot()
        case["assemblies"][2] = "sca-0003"
        with self.assertRaises(ValueError):
            assess_acceptance_lot(case)


if __name__ == "__main__":
    unittest.main()
