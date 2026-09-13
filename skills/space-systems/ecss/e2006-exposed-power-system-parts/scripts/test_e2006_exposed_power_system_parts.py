#!/usr/bin/env python3
"""Contract test for the exposed power-chain arcing-provision leaf (stdlib)."""

import unittest

from e2006_exposed_power_system_parts_logic import (
    BONDING_RESISTANCE_LIMIT_OHM,
    PRIMARY_ARC_INCEPTION_V,
    SUSTAINED_ARC_DIFFERENTIAL_V,
    assess_exposed_power_chain,
    categorize_arcing_regime,
    categorize_power_chain_element,
    check_bonding_resistance,
    evaluate_element,
    largest_conductor_differential,
    most_negative_plasma_relative_potential,
    required_provisions,
)


def drive_element(**overrides):
    element = {
        "id": "sadm-1",
        "kind": "solar-array-drive-mechanism",
        "plasma_exposed": True,
        "exposed_conductor_potentials_v": [0.0, 100.0],
        "ground_potential_v": -120.0,
        "provisions": [
            "bonding-to-structure",
            "insulation-barrier",
            "primary-arc-mitigation",
            "secondary-arc-evidence",
            "gap-integrity-inspection",
        ],
        "bonding_resistance_ohm": 0.004,
    }
    element.update(overrides)
    return element


def shielded_element(**overrides):
    element = {
        "id": "box-1",
        "kind": "junction-box",
        "plasma_exposed": False,
        "exposed_conductor_potentials_v": [0.0, 100.0],
        "ground_potential_v": -120.0,
        "provisions": ["bonding-to-structure", "insulation-barrier"],
        "bonding_resistance_ohm": 0.002,
    }
    element.update(overrides)
    return element


class ElementFamilyTests(unittest.TestCase):
    def test_drive_mechanism_family(self):
        self.assertEqual(
            categorize_power_chain_element("solar-array-drive-mechanism"), "drive-mechanism"
        )

    def test_deployment_hinge_is_a_drive_mechanism(self):
        self.assertEqual(categorize_power_chain_element("deployment-hinge"), "drive-mechanism")

    def test_slip_ring_is_a_rotary_transfer_element(self):
        self.assertEqual(categorize_power_chain_element("slip-ring-assembly"), "rotary-transfer")

    def test_exposed_harness_is_a_conductor_run(self):
        self.assertEqual(categorize_power_chain_element("exposed-harness-run"), "conductor-run")

    def test_junction_box_is_a_conditioning_unit(self):
        self.assertEqual(categorize_power_chain_element("junction-box"), "conditioning-unit")

    def test_uncategorized_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_power_chain_element("mystery-bracket")

    def test_non_string_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_power_chain_element(7)


class DifferentialTests(unittest.TestCase):
    def test_differential_is_the_span_of_the_exposed_potentials(self):
        self.assertAlmostEqual(
            largest_conductor_differential([-20.0, 0.0, 35.0]), 55.0, places=9
        )

    def test_single_conductor_is_rejected(self):
        with self.assertRaises(ValueError):
            largest_conductor_differential([100.0])

    def test_non_list_potentials_are_rejected(self):
        with self.assertRaises(ValueError):
            largest_conductor_differential(100.0)

    def test_non_numeric_potential_is_rejected(self):
        with self.assertRaises(ValueError):
            largest_conductor_differential([0.0, "100"])

    def test_boolean_potential_is_rejected(self):
        with self.assertRaises(ValueError):
            largest_conductor_differential([0.0, True])

    def test_plasma_relative_potential_adds_the_floating_ground_offset(self):
        value = most_negative_plasma_relative_potential([0.0, 100.0], -120.0)
        self.assertAlmostEqual(value, -120.0, places=9)

    def test_plasma_relative_potential_tracks_the_most_negative_conductor(self):
        value = most_negative_plasma_relative_potential([-40.0, 100.0], -20.0)
        self.assertAlmostEqual(value, -60.0, places=9)

    def test_empty_potentials_are_rejected_for_the_plasma_reference(self):
        with self.assertRaises(ValueError):
            most_negative_plasma_relative_potential([], -20.0)

    def test_non_numeric_ground_potential_is_rejected(self):
        with self.assertRaises(ValueError):
            most_negative_plasma_relative_potential([0.0, 100.0], None)


class RegimeTests(unittest.TestCase):
    def test_shielded_element_stays_below_the_arcing_thresholds(self):
        self.assertEqual(
            categorize_arcing_regime(200.0, -400.0, False), "below-arcing-thresholds"
        )

    def test_shallow_negative_potential_stays_below_the_thresholds(self):
        self.assertEqual(
            categorize_arcing_regime(80.0, -40.0, True), "below-arcing-thresholds"
        )

    def test_positive_exposed_potential_stays_below_the_thresholds(self):
        self.assertEqual(categorize_arcing_regime(80.0, 25.0, True), "below-arcing-thresholds")

    def test_deep_potential_with_small_differential_is_primary_arc_risk(self):
        self.assertEqual(categorize_arcing_regime(20.0, -150.0, True), "primary-arc-risk")

    def test_deep_potential_with_large_differential_is_sustained_arc_risk(self):
        self.assertEqual(categorize_arcing_regime(90.0, -150.0, True), "sustained-arc-risk")

    def test_inception_magnitude_reached_by_a_sum_of_offsets_still_counts(self):
        # -33.4 - 33.3 - 33.3 is exactly -100 V physically but lands a few ULPs
        # short of it in binary; the compliant-looking shortfall must not
        # downgrade the regime.
        relative = -33.4 + -33.3 + -33.3
        self.assertGreater(relative, -PRIMARY_ARC_INCEPTION_V)
        self.assertEqual(categorize_arcing_regime(10.0, relative, True), "primary-arc-risk")

    def test_differential_at_the_sustaining_threshold_by_subtraction_still_counts(self):
        # 64.1 V - 9.1 V is exactly 55 V physically, a few ULPs short in binary.
        differential = largest_conductor_differential([9.1, 64.1])
        self.assertLess(differential, SUSTAINED_ARC_DIFFERENTIAL_V)
        self.assertEqual(
            categorize_arcing_regime(differential, -150.0, True), "sustained-arc-risk"
        )

    def test_non_boolean_exposure_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_arcing_regime(90.0, -150.0, "yes")

    def test_negative_differential_magnitude_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_arcing_regime(-5.0, -150.0, True)

    def test_non_positive_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_arcing_regime(90.0, -150.0, True, primary_threshold_v=0.0)


class ProvisionTests(unittest.TestCase):
    def test_conductor_run_baseline(self):
        self.assertEqual(
            required_provisions("conductor-run", "below-arcing-thresholds"),
            ("bonding-to-structure", "insulation-barrier"),
        )

    def test_rotary_transfer_baseline_adds_track_separation(self):
        self.assertIn(
            "track-separation", required_provisions("rotary-transfer", "below-arcing-thresholds")
        )

    def test_primary_arc_risk_adds_mitigation(self):
        provisions = required_provisions("drive-mechanism", "primary-arc-risk")
        self.assertIn("primary-arc-mitigation", provisions)
        self.assertNotIn("secondary-arc-evidence", provisions)

    def test_sustained_arc_risk_adds_evidence_and_gap_inspection(self):
        provisions = required_provisions("drive-mechanism", "sustained-arc-risk")
        self.assertIn("secondary-arc-evidence", provisions)
        self.assertIn("gap-integrity-inspection", provisions)
        self.assertIn("primary-arc-mitigation", provisions)

    def test_provision_set_is_sorted_and_unique(self):
        provisions = required_provisions("rotary-transfer", "sustained-arc-risk")
        self.assertEqual(list(provisions), sorted(set(provisions)))

    def test_unknown_family_is_rejected(self):
        with self.assertRaises(ValueError):
            required_provisions("thermal-blanket", "primary-arc-risk")

    def test_unknown_regime_is_rejected(self):
        with self.assertRaises(ValueError):
            required_provisions("conductor-run", "maybe-arcing")


class BondingTests(unittest.TestCase):
    def test_bond_within_the_limit_has_no_findings(self):
        self.assertEqual(check_bonding_resistance({"bonding_resistance_ohm": 0.004}), [])

    def test_bond_above_the_limit_is_a_finding(self):
        findings = check_bonding_resistance({"bonding_resistance_ohm": 0.05})
        self.assertEqual(len(findings), 1)
        self.assertIn("exceeds", findings[0])

    def test_series_bond_path_exactly_at_the_limit_passes(self):
        # Strap + interface + fastener segments summing to exactly 10 mohm;
        # the binary sum lands one ULP above the limit.
        measured = 0.0002 + 0.0079 + 0.0019
        self.assertGreater(measured, BONDING_RESISTANCE_LIMIT_OHM)
        self.assertEqual(check_bonding_resistance({"bonding_resistance_ohm": measured}), [])

    def test_missing_bond_reading_is_a_finding(self):
        findings = check_bonding_resistance({})
        self.assertEqual(findings, ["bonding-resistance not on record"])

    def test_negative_bond_reading_is_rejected(self):
        with self.assertRaises(ValueError):
            check_bonding_resistance({"bonding_resistance_ohm": -0.001})

    def test_non_positive_bond_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            check_bonding_resistance({"bonding_resistance_ohm": 0.004}, limit_ohm=0.0)

    def test_non_mapping_element_is_rejected(self):
        with self.assertRaises(ValueError):
            check_bonding_resistance(0.004)


class EvaluateElementTests(unittest.TestCase):
    def test_fully_provisioned_drive_mechanism_is_compliant(self):
        result = evaluate_element(drive_element())
        self.assertEqual(result["regime"], "sustained-arc-risk")
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["differential_v"], 100.0, places=9)
        self.assertAlmostEqual(result["plasma_relative_potential_v"], -120.0, places=9)

    def test_missing_provision_is_reported(self):
        element = drive_element(provisions=["bonding-to-structure", "insulation-barrier"])
        result = evaluate_element(element)
        self.assertFalse(result["compliant"])
        self.assertIn("secondary-arc-evidence", result["missing_provisions"])
        self.assertTrue(any("primary-arc-mitigation" in f for f in result["findings"]))

    def test_shielded_element_only_needs_the_family_baseline(self):
        result = evaluate_element(shielded_element())
        self.assertEqual(result["regime"], "below-arcing-thresholds")
        self.assertTrue(result["compliant"])

    def test_bond_finding_reaches_the_element_verdict(self):
        result = evaluate_element(shielded_element(bonding_resistance_ohm=0.2))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("bonding-resistance" in f for f in result["findings"]))

    def test_uncategorized_provision_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_element(drive_element(provisions=["magic-paint"]))

    def test_provisions_must_be_a_list(self):
        with self.assertRaises(ValueError):
            evaluate_element(drive_element(provisions="bonding-to-structure"))

    def test_missing_identifier_is_rejected(self):
        element = drive_element()
        del element["id"]
        with self.assertRaises(ValueError):
            evaluate_element(element)

    def test_blank_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_element(drive_element(id="   "))

    def test_missing_kind_is_rejected(self):
        element = drive_element()
        del element["kind"]
        with self.assertRaises(ValueError):
            evaluate_element(element)

    def test_missing_exposure_flag_is_rejected(self):
        element = drive_element()
        del element["plasma_exposed"]
        with self.assertRaises(ValueError):
            evaluate_element(element)

    def test_non_boolean_exposure_flag_is_rejected_on_the_element(self):
        with self.assertRaises(ValueError):
            evaluate_element(drive_element(plasma_exposed=1))

    def test_missing_potentials_are_rejected(self):
        element = drive_element()
        del element["exposed_conductor_potentials_v"]
        with self.assertRaises(ValueError):
            evaluate_element(element)

    def test_missing_ground_potential_is_rejected(self):
        element = drive_element()
        del element["ground_potential_v"]
        with self.assertRaises(ValueError):
            evaluate_element(element)

    def test_element_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            evaluate_element(["sadm-1"])


class ChainAssessmentTests(unittest.TestCase):
    def test_compliant_chain_passes(self):
        result = assess_exposed_power_chain([drive_element(), shielded_element()])
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["finding_count"], 0)
        self.assertEqual(result["regime_counts"]["sustained-arc-risk"], 1)
        self.assertEqual(result["regime_counts"]["below-arcing-thresholds"], 1)

    def test_one_gap_fails_the_whole_chain(self):
        bad = drive_element(id="sadm-2", provisions=["bonding-to-structure"])
        result = assess_exposed_power_chain([shielded_element(), bad])
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(result["non_compliant_ids"], ["sadm-2"])
        self.assertGreaterEqual(result["finding_count"], 3)

    def test_slip_ring_without_track_separation_is_reported(self):
        ring = {
            "id": "slip-ring-1",
            "kind": "slip-ring-assembly",
            "plasma_exposed": True,
            "exposed_conductor_potentials_v": [0.0, 70.0],
            "ground_potential_v": -140.0,
            "provisions": [
                "bonding-to-structure",
                "insulation-barrier",
                "primary-arc-mitigation",
                "secondary-arc-evidence",
                "gap-integrity-inspection",
            ],
            "bonding_resistance_ohm": 0.003,
        }
        result = assess_exposed_power_chain([ring])
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(result["elements"][0]["missing_provisions"], ("track-separation",))

    def test_duplicate_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_exposed_power_chain([drive_element(), drive_element()])

    def test_empty_inventory_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_exposed_power_chain([])

    def test_non_list_inventory_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_exposed_power_chain(drive_element())


if __name__ == "__main__":
    unittest.main()
