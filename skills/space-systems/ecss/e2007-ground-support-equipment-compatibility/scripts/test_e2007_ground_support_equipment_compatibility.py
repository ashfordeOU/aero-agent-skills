#!/usr/bin/env python3
"""Gate 3 contract test for e2007-ground-support-equipment-compatibility.

Offline, deterministic, standard library only. Run:
    python3 test_e2007_ground_support_equipment_compatibility.py
"""

import unittest

from e2007_ground_support_equipment_compatibility_logic import (
    BLEED_PATH_WINDOW_OHM_PER_SQUARE,
    DEFAULT_BOND_CEILING_OHM,
    assess_ground_support_equipment_compatibility,
    bleed_path_state,
    bond_path_resistance_ohm,
    bond_resistance_finding,
    categorize_gse_item,
    emission_margin_db,
    evaluate_gse_item,
    meets_required_margin,
    reference_potential_difference_v,
    scale_emission_to_distance_db,
    verification_findings,
)

VEHICLE = {
    "radiated_susceptibility_db": 80.0,
    "conducted_susceptibility_db": 60.0,
    "bond_ceiling_ohm": 0.010,
    "safe_potential_v": 0.050,
}


def rack(**overrides):
    item = {
        "item_id": "EGSE-STIM-01",
        "item_type": "stimulus-rack",
        "bond_segments_ohm": [0.0020, 0.0030, 0.0025],
        "return_current_a": 2.0,
        "stand_off_m": 3.0,
        "radiated_levels_db": [{"level_db": 50.0, "reference_distance_m": 3.0}],
        "conducted_levels_db": [40.0],
        "verification_status": "verified",
        "powered_in_activity": True,
    }
    item.update(overrides)
    return item


def fixture(**overrides):
    item = {
        "item_id": "MGSE-FIX-01",
        "item_type": "handling-fixture",
        "contacts_flight_hardware": True,
        "surface_resistivity": 1.0e7,
        "verification_status": "verified",
        "powered_in_activity": False,
    }
    item.update(overrides)
    return item


class TestCategorization(unittest.TestCase):
    def test_stimulus_rack_is_electrical(self):
        self.assertEqual(categorize_gse_item("stimulus-rack"), "electrical")

    def test_umbilical_is_electrical(self):
        self.assertEqual(categorize_gse_item("umbilical"), "electrical")

    def test_handling_fixture_is_mechanical(self):
        self.assertEqual(categorize_gse_item("handling-fixture"), "mechanical")

    def test_lifting_device_is_mechanical(self):
        self.assertEqual(categorize_gse_item("lifting-device"), "mechanical")

    def test_lookup_ignores_case_and_padding(self):
        self.assertEqual(categorize_gse_item("  Trolley "), "mechanical")

    def test_unknown_item_type_raises(self):
        with self.assertRaises(ValueError):
            categorize_gse_item("clean-room-chair")

    def test_non_string_item_type_raises(self):
        with self.assertRaises(ValueError):
            categorize_gse_item(42)


class TestBondPath(unittest.TestCase):
    def test_chain_total_is_the_sum_of_segments(self):
        self.assertAlmostEqual(
            bond_path_resistance_ohm([0.001, 0.002, 0.003]), 0.006, places=9
        )

    def test_single_segment_chain(self):
        self.assertAlmostEqual(bond_path_resistance_ohm([0.004]), 0.004, places=9)

    def test_empty_chain_raises(self):
        with self.assertRaises(ValueError):
            bond_path_resistance_ohm([])

    def test_none_chain_raises(self):
        with self.assertRaises(ValueError):
            bond_path_resistance_ohm(None)

    def test_non_positive_segment_raises(self):
        with self.assertRaises(ValueError):
            bond_path_resistance_ohm([0.001, 0.0, 0.002])

    def test_non_numeric_segment_raises(self):
        with self.assertRaises(ValueError):
            bond_path_resistance_ohm([0.001, "2 mohm"])

    def test_compliant_chain_has_no_finding(self):
        self.assertIsNone(bond_resistance_finding(0.006, 0.010))

    def test_chain_over_the_ceiling_is_a_finding(self):
        finding = bond_resistance_finding(0.014, 0.010)
        self.assertIsNotNone(finding)
        self.assertIn("ceiling", finding)

    def test_compliant_joints_can_still_break_the_chain(self):
        # Each joint is well under the ceiling; the chain is not.
        total = bond_path_resistance_ohm([0.005, 0.005, 0.005])
        self.assertIsNotNone(bond_resistance_finding(total, 0.010))

    def test_chain_exactly_on_the_ceiling_passes_despite_float_error(self):
        # 0.0005 + 0.0016 + 0.0079 sums to 0.010000000000000002 in binary
        # floating point; the physical chain is exactly on the ceiling.
        total = bond_path_resistance_ohm([0.0005, 0.0016, 0.0079])
        self.assertAlmostEqual(total, 0.010, places=12)
        self.assertIsNone(bond_resistance_finding(total, 0.010))

    def test_default_ceiling_is_ten_milliohm(self):
        self.assertAlmostEqual(DEFAULT_BOND_CEILING_OHM, 0.010, places=9)

    def test_negative_total_raises(self):
        with self.assertRaises(ValueError):
            bond_resistance_finding(-0.001, 0.010)

    def test_non_positive_ceiling_raises(self):
        with self.assertRaises(ValueError):
            bond_resistance_finding(0.005, 0.0)


class TestReferencePotential(unittest.TestCase):
    def test_potential_is_current_times_resistance(self):
        self.assertAlmostEqual(
            reference_potential_difference_v(2.0, 0.010), 0.020, places=9
        )

    def test_zero_current_raises_no_potential(self):
        self.assertAlmostEqual(
            reference_potential_difference_v(0.0, 0.010), 0.0, places=12
        )

    def test_negative_current_raises(self):
        with self.assertRaises(ValueError):
            reference_potential_difference_v(-1.0, 0.010)

    def test_negative_resistance_raises(self):
        with self.assertRaises(ValueError):
            reference_potential_difference_v(1.0, -0.010)


class TestEmissionScaling(unittest.TestCase):
    def test_halving_the_distance_adds_six_decibels(self):
        self.assertAlmostEqual(
            scale_emission_to_distance_db(50.0, 3.0, 1.5), 56.020599913279625, places=9
        )

    def test_doubling_the_distance_removes_six_decibels(self):
        self.assertAlmostEqual(
            scale_emission_to_distance_db(50.0, 3.0, 6.0), 43.979400086720375, places=9
        )

    def test_same_distance_leaves_the_level_unchanged(self):
        self.assertAlmostEqual(
            scale_emission_to_distance_db(50.0, 3.0, 3.0), 50.0, places=12
        )

    def test_tenfold_distance_removes_twenty_decibels(self):
        self.assertAlmostEqual(
            scale_emission_to_distance_db(50.0, 1.0, 10.0), 30.0, places=9
        )

    def test_non_positive_reference_distance_raises(self):
        with self.assertRaises(ValueError):
            scale_emission_to_distance_db(50.0, 0.0, 3.0)

    def test_non_positive_stand_off_raises(self):
        with self.assertRaises(ValueError):
            scale_emission_to_distance_db(50.0, 3.0, -1.0)


class TestMargins(unittest.TestCase):
    def test_margin_is_limit_less_emission(self):
        self.assertAlmostEqual(emission_margin_db(80.0, 50.0), 30.0, places=9)

    def test_generous_margin_meets_the_requirement(self):
        self.assertTrue(meets_required_margin(30.0, 6.0))

    def test_short_margin_fails_the_requirement(self):
        self.assertFalse(meets_required_margin(4.0, 6.0))

    def test_negative_margin_fails_the_requirement(self):
        self.assertFalse(meets_required_margin(-2.0, 6.0))

    def test_exact_margin_passes_despite_float_error(self):
        # 8.2 - 2.2 evaluates to 5.999999999999999 in binary floating point;
        # the physical margin is exactly the required six decibels.
        margin = emission_margin_db(8.2, 2.2)
        self.assertAlmostEqual(margin, 6.0, places=9)
        self.assertTrue(meets_required_margin(margin, 6.0))

    def test_negative_requirement_raises(self):
        with self.assertRaises(ValueError):
            meets_required_margin(10.0, -1.0)

    def test_non_numeric_margin_raises(self):
        with self.assertRaises(ValueError):
            meets_required_margin("10 dB", 6.0)


class TestBleedPath(unittest.TestCase):
    def test_mid_window_surface_is_dissipative(self):
        self.assertEqual(bleed_path_state(1.0e7), "dissipative")

    def test_low_resistivity_surface_is_conductive(self):
        self.assertEqual(bleed_path_state(1.0e3), "conductive")

    def test_high_resistivity_surface_is_insulating(self):
        self.assertEqual(bleed_path_state(1.0e12), "insulating")

    def test_lower_window_edge_is_dissipative(self):
        self.assertEqual(
            bleed_path_state(BLEED_PATH_WINDOW_OHM_PER_SQUARE[0]), "dissipative"
        )

    def test_upper_window_edge_is_dissipative(self):
        self.assertEqual(
            bleed_path_state(BLEED_PATH_WINDOW_OHM_PER_SQUARE[1]), "dissipative"
        )

    def test_custom_window_is_honoured(self):
        self.assertEqual(bleed_path_state(1.0e7, (1.0e8, 1.0e11)), "conductive")

    def test_non_positive_resistivity_raises(self):
        with self.assertRaises(ValueError):
            bleed_path_state(0.0)

    def test_inverted_window_raises(self):
        with self.assertRaises(ValueError):
            bleed_path_state(1.0e7, (1.0e9, 1.0e5))


class TestVerificationRecord(unittest.TestCase):
    def test_verified_item_has_no_finding(self):
        self.assertEqual(verification_findings(rack()), [])

    def test_unverified_powered_item_is_a_finding(self):
        findings = verification_findings(rack(verification_status="unverified"))
        self.assertEqual(len(findings), 1)
        self.assertIn("verification", findings[0])

    def test_unverified_unpowered_item_is_tolerated(self):
        self.assertEqual(
            verification_findings(
                rack(verification_status="unverified", powered_in_activity=False)
            ),
            [],
        )

    def test_waiver_without_rationale_is_a_finding(self):
        findings = verification_findings(rack(verification_status="waived"))
        self.assertEqual(len(findings), 1)
        self.assertIn("rationale", findings[0])

    def test_waiver_with_rationale_is_accepted(self):
        self.assertEqual(
            verification_findings(
                rack(verification_status="waived", waiver_rationale="NCR-88 closed")
            ),
            [],
        )

    def test_absent_status_defaults_to_unverified(self):
        item = rack()
        del item["verification_status"]
        self.assertEqual(len(verification_findings(item)), 1)

    def test_unrecognised_status_raises(self):
        with self.assertRaises(ValueError):
            verification_findings(rack(verification_status="probably-fine"))

    def test_non_string_status_raises(self):
        with self.assertRaises(ValueError):
            verification_findings(rack(verification_status=1))


class TestEvaluateElectricalItem(unittest.TestCase):
    def test_compliant_rack(self):
        result = evaluate_gse_item(rack(), VEHICLE, 6.0)
        self.assertTrue(result["compatible"])
        self.assertEqual(result["family"], "electrical")
        self.assertAlmostEqual(result["bond_resistance_ohm"], 0.0075, places=9)
        self.assertAlmostEqual(result["reference_potential_v"], 0.015, places=9)
        self.assertAlmostEqual(result["radiated_margins_db"][0], 30.0, places=9)
        self.assertAlmostEqual(result["conducted_margins_db"][0], 20.0, places=9)

    def test_excessive_bond_chain_is_reported(self):
        result = evaluate_gse_item(
            rack(bond_segments_ohm=[0.006, 0.006, 0.006]), VEHICLE, 6.0
        )
        self.assertFalse(result["compatible"])
        self.assertTrue(any("bond path" in f for f in result["findings"]))

    def test_large_return_current_lifts_the_reference_beyond_the_allowance(self):
        result = evaluate_gse_item(rack(return_current_a=40.0), VEHICLE, 6.0)
        self.assertFalse(result["compatible"])
        self.assertAlmostEqual(result["reference_potential_v"], 0.30, places=9)
        self.assertTrue(any("reference" in f for f in result["findings"]))

    def test_rack_moved_closer_loses_its_radiated_margin(self):
        result = evaluate_gse_item(rack(stand_off_m=0.05), VEHICLE, 6.0)
        self.assertFalse(result["compatible"])
        self.assertLess(result["radiated_margins_db"][0], 6.0)
        self.assertTrue(any("radiated level" in f for f in result["findings"]))

    def test_umbilical_conducted_level_without_margin_is_reported(self):
        result = evaluate_gse_item(rack(conducted_levels_db=[58.0]), VEHICLE, 6.0)
        self.assertFalse(result["compatible"])
        self.assertAlmostEqual(result["conducted_margins_db"][0], 2.0, places=9)
        self.assertTrue(any("conducted level" in f for f in result["findings"]))

    def test_electrical_item_without_bond_chain_raises(self):
        item = rack()
        del item["bond_segments_ohm"]
        with self.assertRaises(ValueError):
            evaluate_gse_item(item, VEHICLE, 6.0)

    def test_radiated_levels_without_stand_off_raise(self):
        item = rack()
        del item["stand_off_m"]
        with self.assertRaises(ValueError):
            evaluate_gse_item(item, VEHICLE, 6.0)

    def test_radiated_level_missing_reference_distance_raises(self):
        item = rack(radiated_levels_db=[{"level_db": 50.0}])
        with self.assertRaises(ValueError):
            evaluate_gse_item(item, VEHICLE, 6.0)

    def test_missing_item_identifier_raises(self):
        item = rack()
        del item["item_id"]
        with self.assertRaises(ValueError):
            evaluate_gse_item(item, VEHICLE, 6.0)

    def test_unknown_item_type_raises(self):
        with self.assertRaises(ValueError):
            evaluate_gse_item(rack(item_type="coffee-machine"), VEHICLE, 6.0)


class TestEvaluateMechanicalItem(unittest.TestCase):
    def test_compliant_handling_fixture(self):
        result = evaluate_gse_item(fixture(), VEHICLE, 6.0)
        self.assertTrue(result["compatible"])
        self.assertEqual(result["family"], "mechanical")
        self.assertEqual(result["bleed_path_state"], "dissipative")
        self.assertIsNone(result["bond_resistance_ohm"])

    def test_insulating_fixture_is_reported(self):
        result = evaluate_gse_item(fixture(surface_resistivity=1.0e13), VEHICLE, 6.0)
        self.assertFalse(result["compatible"])
        self.assertEqual(result["bleed_path_state"], "insulating")

    def test_over_conductive_fixture_is_reported(self):
        result = evaluate_gse_item(fixture(surface_resistivity=1.0e2), VEHICLE, 6.0)
        self.assertFalse(result["compatible"])
        self.assertEqual(result["bleed_path_state"], "conductive")

    def test_non_contacting_fixture_skips_the_bleed_path_check(self):
        result = evaluate_gse_item(
            fixture(contacts_flight_hardware=False, surface_resistivity=1.0e13),
            VEHICLE,
            6.0,
        )
        self.assertTrue(result["compatible"])
        self.assertIsNone(result["bleed_path_state"])

    def test_contacting_fixture_without_resistivity_raises(self):
        item = fixture()
        del item["surface_resistivity"]
        with self.assertRaises(ValueError):
            evaluate_gse_item(item, VEHICLE, 6.0)

    def test_unverified_powered_fixture_is_reported(self):
        result = evaluate_gse_item(
            fixture(verification_status="unverified", powered_in_activity=True),
            VEHICLE,
            6.0,
        )
        self.assertFalse(result["compatible"])


class TestActivityAssessment(unittest.TestCase):
    def test_clean_activity(self):
        out = assess_ground_support_equipment_compatibility(
            [rack(), fixture()], VEHICLE, 6.0
        )
        self.assertTrue(out["activity_compatible"])
        self.assertEqual(out["electrical_count"], 1)
        self.assertEqual(out["mechanical_count"], 1)
        self.assertEqual(out["non_compliant_items"], [])
        self.assertAlmostEqual(out["required_margin_db"], 6.0, places=9)

    def test_one_bad_item_breaks_the_activity(self):
        out = assess_ground_support_equipment_compatibility(
            [rack(), fixture(surface_resistivity=1.0e13)], VEHICLE, 6.0
        )
        self.assertFalse(out["activity_compatible"])
        self.assertEqual(len(out["non_compliant_items"]), 1)
        self.assertEqual(out["non_compliant_items"][0]["item_id"], "MGSE-FIX-01")

    def test_verification_gap_alone_breaks_the_activity(self):
        out = assess_ground_support_equipment_compatibility(
            [rack(verification_status="unverified"), fixture()], VEHICLE, 6.0
        )
        self.assertFalse(out["activity_compatible"])
        self.assertEqual(len(out["non_compliant_items"]), 1)

    def test_tighter_required_margin_can_fail_a_passing_activity(self):
        out = assess_ground_support_equipment_compatibility(
            [rack()], VEHICLE, 25.0
        )
        self.assertFalse(out["activity_compatible"])

    def test_empty_activity_raises(self):
        with self.assertRaises(ValueError):
            assess_ground_support_equipment_compatibility([], VEHICLE, 6.0)

    def test_duplicate_item_identifier_raises(self):
        with self.assertRaises(ValueError):
            assess_ground_support_equipment_compatibility(
                [rack(), rack(stand_off_m=5.0)], VEHICLE, 6.0
            )

    def test_non_mapping_item_raises(self):
        with self.assertRaises(ValueError):
            assess_ground_support_equipment_compatibility(
                ["EGSE-STIM-01"], VEHICLE, 6.0
            )

    def test_vehicle_without_radiated_limit_raises(self):
        with self.assertRaises(ValueError):
            assess_ground_support_equipment_compatibility(
                [rack()], {"conducted_susceptibility_db": 60.0}, 6.0
            )

    def test_vehicle_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_ground_support_equipment_compatibility([rack()], [80.0], 6.0)


if __name__ == "__main__":
    unittest.main()
