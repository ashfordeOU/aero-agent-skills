#!/usr/bin/env python3
"""Contract test for the shunt diode forward-voltage test (offline).

Walks the clause workflow step by step: the adequacy of the reverse
drive against the string current the diode is there to carry, the
referral of each measured forward drop to the reference junction
temperature, the window that separates a conducting part from a shorted,
degraded or open one, the dissipation the drive imposes, the residual
string drop no diode explains, and the verdict that has to stop a
campaign whose drive never reached the protected case. This is the gate
3 review evidence for the leaf.
"""

import copy
import unittest

from e2008_shunt_diode_test_logic import (
    DEFAULT_SHUNT_DIODE_POLICY,
    SHUNT_CONDUCTING,
    SHUNT_DEGRADED,
    SHUNT_DIODE_CATEGORIES,
    SHUNT_DIODE_TEST_FAILED,
    SHUNT_DIODE_TEST_NOT_EVALUATED,
    SHUNT_DIODE_TEST_PASSED,
    SHUNT_OPEN,
    SHUNT_SHORTED,
    categorize_shunt_diode,
    diode_dissipation_w,
    evaluate_shunt_diode,
    evaluate_shunt_diode_test,
    normalize_forward_voltage_v,
    reverse_drive_adequacy,
    unexplained_string_drop_v,
    validate_shunt_diode_policy,
)

WORST_CASE_STRING_CURRENT_A = 0.52


def _diode(identifier, forward_v, junction_c=25.0):
    return {
        "id": identifier,
        "forward_voltage_v": forward_v,
        "junction_temperature_c": junction_c,
    }


def _campaign(diodes, drive_a=0.60, string_v=None):
    campaign = {
        "flight_case": {"worst_case_string_current_a": WORST_CASE_STRING_CURRENT_A},
        "applied_drive_current_a": drive_a,
        "diodes": list(diodes),
    }
    if string_v is not None:
        campaign["measured_string_reverse_voltage_v"] = string_v
    return campaign


SOUND_CAMPAIGN = _campaign(
    [
        _diode("s1", 0.62, 35.0),
        _diode("s2", 0.64, 35.0),
        _diode("s3", 0.61, 35.0),
    ]
)


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_shunt_diode_policy(DEFAULT_SHUNT_DIODE_POLICY),
            DEFAULT_SHUNT_DIODE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_shunt_diode_policy("default")

    def test_inverted_window_rejected(self):
        broken = copy.deepcopy(DEFAULT_SHUNT_DIODE_POLICY)
        broken["max_forward_voltage_v"] = 0.20
        with self.assertRaises(ValueError):
            validate_shunt_diode_policy(broken)

    def test_open_threshold_inside_the_window_rejected(self):
        broken = copy.deepcopy(DEFAULT_SHUNT_DIODE_POLICY)
        broken["open_circuit_threshold_v"] = 0.80
        with self.assertRaises(ValueError):
            validate_shunt_diode_policy(broken)

    def test_non_negative_tempco_rejected(self):
        broken = copy.deepcopy(DEFAULT_SHUNT_DIODE_POLICY)
        broken["forward_voltage_tempco_v_per_k"] = 0.002
        with self.assertRaises(ValueError):
            validate_shunt_diode_policy(broken)

    def test_zero_dissipation_budget_rejected(self):
        broken = copy.deepcopy(DEFAULT_SHUNT_DIODE_POLICY)
        broken["max_dissipation_w"] = 0.0
        with self.assertRaises(ValueError):
            validate_shunt_diode_policy(broken)

    def test_negative_unexplained_drop_allowance_rejected(self):
        broken = copy.deepcopy(DEFAULT_SHUNT_DIODE_POLICY)
        broken["max_unexplained_string_drop_v"] = -0.01
        with self.assertRaises(ValueError):
            validate_shunt_diode_policy(broken)


class NormalizationTests(unittest.TestCase):
    def test_reading_at_the_reference_is_unchanged(self):
        self.assertAlmostEqual(
            normalize_forward_voltage_v(0.62, 25.0, 25.0, -0.002), 0.62, places=12
        )

    def test_warm_reading_is_lifted_back_to_the_reference(self):
        self.assertAlmostEqual(
            normalize_forward_voltage_v(0.62, 35.0, 25.0, -0.002), 0.64, places=12
        )

    def test_cold_reading_is_brought_down_to_the_reference(self):
        self.assertAlmostEqual(
            normalize_forward_voltage_v(0.70, 5.0, 25.0, -0.002), 0.66, places=12
        )

    def test_non_negative_tempco_rejected(self):
        with self.assertRaises(ValueError):
            normalize_forward_voltage_v(0.62, 35.0, 25.0, 0.002)

    def test_zero_measured_voltage_rejected(self):
        with self.assertRaises(ValueError):
            normalize_forward_voltage_v(0.0, 35.0, 25.0, -0.002)

    def test_non_numeric_junction_temperature_rejected(self):
        with self.assertRaises(ValueError):
            normalize_forward_voltage_v(0.62, "warm", 25.0, -0.002)


class DriveAdequacyTests(unittest.TestCase):
    def test_drive_above_the_string_current_is_adequate(self):
        result = reverse_drive_adequacy(0.60, WORST_CASE_STRING_CURRENT_A)
        self.assertTrue(result["adequate"])
        self.assertAlmostEqual(result["shortfall_a"], 0.0, places=12)
        self.assertEqual(result["findings"], [])

    def test_drive_exactly_on_the_string_current_is_adequate(self):
        result = reverse_drive_adequacy(
            WORST_CASE_STRING_CURRENT_A, WORST_CASE_STRING_CURRENT_A
        )
        self.assertTrue(result["adequate"])
        self.assertAlmostEqual(result["coverage_ratio"], 1.0, places=9)

    def test_gentle_drive_is_inadequate_and_named(self):
        result = reverse_drive_adequacy(0.20, WORST_CASE_STRING_CURRENT_A)
        self.assertFalse(result["adequate"])
        self.assertAlmostEqual(
            result["shortfall_a"], WORST_CASE_STRING_CURRENT_A - 0.20, places=9
        )
        self.assertTrue(
            any("below the worst-case" in note for note in result["findings"])
        )

    def test_zero_drive_rejected(self):
        with self.assertRaises(ValueError):
            reverse_drive_adequacy(0.0, WORST_CASE_STRING_CURRENT_A)


class CategoryTests(unittest.TestCase):
    def test_nominal_drop_is_conducting(self):
        self.assertEqual(categorize_shunt_diode(0.64), SHUNT_CONDUCTING)

    def test_collapsed_drop_is_suspect_shorted(self):
        self.assertEqual(categorize_shunt_diode(0.07), SHUNT_SHORTED)

    def test_excess_drop_is_suspect_degraded(self):
        self.assertEqual(categorize_shunt_diode(1.50), SHUNT_DEGRADED)

    def test_drive_against_a_broken_path_is_open_circuit(self):
        self.assertEqual(categorize_shunt_diode(8.00), SHUNT_OPEN)

    def test_drop_referred_onto_the_lower_edge_is_conducting(self):
        # The referral is a difference of products, so a part meant to
        # sit on the window edge need not land on it bit for bit.
        edge = DEFAULT_SHUNT_DIODE_POLICY["min_forward_voltage_v"]
        referred = normalize_forward_voltage_v(0.41, 45.0, 25.0, -0.002)
        self.assertAlmostEqual(referred, edge, places=9)
        self.assertEqual(categorize_shunt_diode(referred), SHUNT_CONDUCTING)

    def test_drop_on_the_upper_edge_is_conducting(self):
        edge = DEFAULT_SHUNT_DIODE_POLICY["max_forward_voltage_v"]
        referred = normalize_forward_voltage_v(0.91, 45.0, 25.0, -0.002)
        self.assertAlmostEqual(referred, edge, places=9)
        self.assertEqual(categorize_shunt_diode(referred), SHUNT_CONDUCTING)

    def test_every_category_is_reachable(self):
        seen = {
            categorize_shunt_diode(value) for value in (0.07, 0.64, 1.50, 8.00)
        }
        self.assertEqual(seen, set(SHUNT_DIODE_CATEGORIES))

    def test_negative_referred_drop_rejected(self):
        with self.assertRaises(ValueError):
            categorize_shunt_diode(-0.10)


class DissipationTests(unittest.TestCase):
    def test_dissipation_is_drop_times_drive_current(self):
        self.assertAlmostEqual(diode_dissipation_w(0.62, 0.60), 0.372, places=12)

    def test_a_harder_drive_raises_the_load(self):
        self.assertAlmostEqual(diode_dissipation_w(0.62, 1.20), 0.744, places=12)

    def test_zero_drive_current_rejected(self):
        with self.assertRaises(ValueError):
            diode_dissipation_w(0.62, 0.0)

    def test_non_numeric_drop_rejected(self):
        with self.assertRaises(ValueError):
            diode_dissipation_w("0.62 V", 0.60)


class DiodeTests(unittest.TestCase):
    def test_warm_nominal_diode_is_acceptable(self):
        record = evaluate_shunt_diode(_diode("s1", 0.62, 35.0), 0.60)
        self.assertAlmostEqual(record["normalized_forward_voltage_v"], 0.64, places=12)
        self.assertEqual(record["category"], SHUNT_CONDUCTING)
        self.assertTrue(record["acceptable"])

    def test_shorted_diode_is_called_out(self):
        record = evaluate_shunt_diode(_diode("s4", 0.05), 0.60)
        self.assertEqual(record["category"], SHUNT_SHORTED)
        self.assertFalse(record["acceptable"])
        self.assertTrue(any("shunted while lit" in note for note in record["findings"]))

    def test_degraded_diode_is_called_out(self):
        record = evaluate_shunt_diode(_diode("s5", 1.50), 0.60)
        self.assertEqual(record["category"], SHUNT_DEGRADED)
        self.assertTrue(
            any("above the window" in note for note in record["findings"])
        )

    def test_open_path_is_called_out(self):
        record = evaluate_shunt_diode(_diode("s6", 8.00), 0.60)
        self.assertEqual(record["category"], SHUNT_OPEN)
        self.assertTrue(any("broken path" in note for note in record["findings"]))

    def test_dissipation_budget_can_reject_a_conducting_diode(self):
        policy = copy.deepcopy(DEFAULT_SHUNT_DIODE_POLICY)
        policy["max_dissipation_w"] = 0.10
        record = evaluate_shunt_diode(_diode("s1", 0.62, 35.0), 0.60, policy)
        self.assertEqual(record["category"], SHUNT_CONDUCTING)
        self.assertFalse(record["within_dissipation_budget"])
        self.assertFalse(record["acceptable"])

    def test_non_mapping_diode_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_shunt_diode("0.62 volts", 0.60)


class StringResidualTests(unittest.TestCase):
    def test_residual_is_the_string_drop_less_the_diode_drops(self):
        self.assertAlmostEqual(
            unexplained_string_drop_v(1.90, [0.62, 0.62, 0.62]), 0.04, places=9
        )

    def test_a_string_explained_by_its_diodes_has_no_residual(self):
        self.assertAlmostEqual(
            unexplained_string_drop_v(1.86, [0.62, 0.62, 0.62]), 0.0, places=9
        )

    def test_empty_diode_list_rejected(self):
        with self.assertRaises(ValueError):
            unexplained_string_drop_v(1.90, [])

    def test_zero_string_voltage_rejected(self):
        with self.assertRaises(ValueError):
            unexplained_string_drop_v(0.0, [0.62])


class CampaignTests(unittest.TestCase):
    def test_sound_campaign_passes(self):
        result = evaluate_shunt_diode_test(SOUND_CAMPAIGN)
        self.assertEqual(result["verdict"], SHUNT_DIODE_TEST_PASSED)
        self.assertTrue(result["compliant"])
        self.assertTrue(result["drive_adequate"])
        self.assertEqual(result["rejected_diode_ids"], [])

    def test_shorted_diode_fails_the_campaign_and_is_named(self):
        campaign = _campaign(
            [_diode("s1", 0.62, 35.0), _diode("s2", 0.05, 35.0)]
        )
        result = evaluate_shunt_diode_test(campaign)
        self.assertEqual(result["verdict"], SHUNT_DIODE_TEST_FAILED)
        self.assertEqual(result["rejected_diode_ids"], ["s2"])

    def test_gentle_drive_is_not_evaluated(self):
        campaign = _campaign([_diode("s1", 0.62, 35.0)], drive_a=0.20)
        result = evaluate_shunt_diode_test(campaign)
        self.assertEqual(result["verdict"], SHUNT_DIODE_TEST_NOT_EVALUATED)
        self.assertIsNone(result["compliant"])
        self.assertTrue(
            any("driven again" in note for note in result["findings"])
        )

    def test_drive_exactly_at_the_string_current_is_evaluated(self):
        campaign = _campaign(
            [_diode("s1", 0.62, 35.0)], drive_a=WORST_CASE_STRING_CURRENT_A
        )
        result = evaluate_shunt_diode_test(campaign)
        self.assertTrue(result["drive_adequate"])
        self.assertEqual(result["verdict"], SHUNT_DIODE_TEST_PASSED)

    def test_string_drop_within_the_allowance_passes(self):
        campaign = _campaign(
            [_diode("s1", 0.62, 35.0), _diode("s2", 0.62, 35.0)], string_v=1.27
        )
        result = evaluate_shunt_diode_test(campaign)
        self.assertAlmostEqual(result["unexplained_string_drop_v"], 0.03, places=9)
        self.assertTrue(result["compliant"])

    def test_unexplained_string_drop_fails_the_campaign(self):
        campaign = _campaign(
            [_diode("s1", 0.62, 35.0), _diode("s2", 0.62, 35.0)], string_v=1.90
        )
        result = evaluate_shunt_diode_test(campaign)
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("resisting joint" in note for note in result["findings"])
        )
        self.assertEqual(result["rejected_diode_ids"], [])

    def test_total_dissipation_is_the_sum_of_the_population(self):
        result = evaluate_shunt_diode_test(SOUND_CAMPAIGN)
        expected = sum(record["dissipation_w"] for record in result["diodes"])
        self.assertAlmostEqual(result["total_dissipation_w"], expected, places=12)

    def test_campaign_without_diodes_rejected(self):
        campaign = copy.deepcopy(SOUND_CAMPAIGN)
        campaign["diodes"] = []
        with self.assertRaises(ValueError):
            evaluate_shunt_diode_test(campaign)

    def test_campaign_without_a_flight_case_rejected(self):
        campaign = copy.deepcopy(SOUND_CAMPAIGN)
        del campaign["flight_case"]
        with self.assertRaises(ValueError):
            evaluate_shunt_diode_test(campaign)

    def test_non_mapping_campaign_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_shunt_diode_test("three diodes, all conducting")


if __name__ == "__main__":
    unittest.main()
