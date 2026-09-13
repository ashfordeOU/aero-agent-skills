#!/usr/bin/env python3
"""Contract test for the clause 6.8.1 grounding-verification logic."""

import unittest

from e2006_grounding_verification_by_inspection_logic import (
    PROVISION_BOUNDS_OHM,
    bond_resistance_margin,
    categorize_provision,
    evaluate_continuity_measurement,
    evaluate_inspection_record,
    resistance_bounds,
    verify_grounding_network,
    verify_provision,
)


def good_inspection(**overrides):
    record = {
        "surface_preparation": "verified",
        "fastener_installation": "verified",
        "corrosion_protection": "verified",
        "conductor_routing": "verified",
        "open_nonconformances": 0,
    }
    record.update(overrides)
    return record


def good_provision(**overrides):
    provision = {
        "id": "BOND-001",
        "kind": "equipment-chassis-bond",
        "inspection": good_inspection(),
        "measurement": {
            "measured_ohm": 3.0e-3,
            "resolution_ohm": 1.0e-4,
            "method": "four-wire-dc",
        },
    }
    provision.update(overrides)
    return provision


class TestCategorizeProvision(unittest.TestCase):
    def test_canonical_name_round_trips(self):
        self.assertEqual(categorize_provision("structure-bond"), "structure-bond")

    def test_alias_maps_to_canonical_category(self):
        self.assertEqual(categorize_provision("backshell-termination"), "shield-termination")

    def test_case_and_underscore_normalized(self):
        self.assertEqual(categorize_provision("  Chassis_Bond "), "equipment-chassis-bond")

    def test_bleed_path_alias(self):
        self.assertEqual(categorize_provision("bleed-path-bond"), "static-dissipative-bond")

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            categorize_provision("paint-stripe")

    def test_blank_kind_raises(self):
        with self.assertRaises(ValueError):
            categorize_provision("   ")

    def test_non_string_kind_raises(self):
        with self.assertRaises(ValueError):
            categorize_provision(7)


class TestResistanceBounds(unittest.TestCase):
    def test_structure_bond_is_the_tightest_upper_bound(self):
        tightest = min(upper for _, upper in PROVISION_BOUNDS_OHM.values())
        self.assertAlmostEqual(resistance_bounds("structure-bond")[1], tightest)

    def test_dissipative_bond_has_a_lower_bound(self):
        lower, upper = resistance_bounds("static-dissipative-bond")
        self.assertGreater(lower, 0.0)
        self.assertGreater(upper, lower)

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            resistance_bounds("antenna-bond")


class TestInspectionRecord(unittest.TestCase):
    def test_complete_record_has_no_findings(self):
        result = evaluate_inspection_record("equipment-chassis-bond", good_inspection())
        self.assertTrue(result["complete"])
        self.assertEqual(result["findings"], [])

    def test_unverified_attribute_blocks_completion(self):
        result = evaluate_inspection_record(
            "equipment-chassis-bond", good_inspection(corrosion_protection="not-verified")
        )
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["findings"]), 1)

    def test_routing_not_applicable_is_accepted_on_a_face_to_face_bond(self):
        result = evaluate_inspection_record(
            "structure-bond", good_inspection(conductor_routing="not-applicable")
        )
        self.assertTrue(result["complete"])

    def test_routing_not_applicable_is_a_finding_on_a_strap_bond(self):
        result = evaluate_inspection_record(
            "shield-termination", good_inspection(conductor_routing="not-applicable")
        )
        self.assertFalse(result["complete"])

    def test_surface_preparation_never_waivable(self):
        result = evaluate_inspection_record(
            "structure-bond", good_inspection(surface_preparation="not-applicable")
        )
        self.assertFalse(result["complete"])

    def test_open_nonconformance_blocks_completion(self):
        result = evaluate_inspection_record(
            "equipment-chassis-bond", good_inspection(open_nonconformances=2)
        )
        self.assertFalse(result["complete"])
        self.assertIn("2 open nonconformance(s) against the provision", result["findings"])

    def test_missing_nonconformance_count_defaults_to_zero(self):
        record = good_inspection()
        del record["open_nonconformances"]
        self.assertTrue(evaluate_inspection_record("structure-bond", record)["complete"])

    def test_missing_attribute_raises(self):
        record = good_inspection()
        del record["fastener_installation"]
        with self.assertRaises(ValueError):
            evaluate_inspection_record("structure-bond", record)

    def test_illegal_attribute_state_raises(self):
        with self.assertRaises(ValueError):
            evaluate_inspection_record("structure-bond", good_inspection(surface_preparation="ok"))

    def test_negative_nonconformance_count_raises(self):
        with self.assertRaises(ValueError):
            evaluate_inspection_record("structure-bond", good_inspection(open_nonconformances=-1))

    def test_boolean_nonconformance_count_raises(self):
        with self.assertRaises(ValueError):
            evaluate_inspection_record("structure-bond", good_inspection(open_nonconformances=True))

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            evaluate_inspection_record("structure-bond", ["surface_preparation"])


class TestContinuityMeasurement(unittest.TestCase):
    def test_compliant_reading_passes(self):
        result = evaluate_continuity_measurement("structure-bond", 1.0e-3, 1.0e-5, "four-wire-dc")
        self.assertTrue(result["compliant"])
        self.assertTrue(result["within_bounds"])

    def test_reading_above_bound_is_flagged(self):
        result = evaluate_continuity_measurement("structure-bond", 4.0e-3, 1.0e-5, "four-wire-dc")
        self.assertFalse(result["compliant"])
        self.assertFalse(result["within_bounds"])

    def test_exact_bound_value_is_compliant(self):
        _, upper = resistance_bounds("structure-bond")
        result = evaluate_continuity_measurement("structure-bond", upper, 1.0e-5, "four-wire-dc")
        self.assertTrue(result["compliant"])

    def test_accumulated_sum_at_the_bound_is_compliant(self):
        # 10 joint drops of 0.25 mohm sum to the 2.5 mohm bound but land a
        # few ULPs above it in binary floating point.
        measured = 0.0
        for _ in range(10):
            measured += 2.5e-4
        _, upper = resistance_bounds("structure-bond")
        self.assertGreaterEqual(measured, upper)
        result = evaluate_continuity_measurement("structure-bond", measured, 1.0e-5, "four-wire-dc")
        self.assertTrue(result["compliant"], result["findings"])

    def test_two_wire_method_rejected_for_a_milliohm_bound(self):
        result = evaluate_continuity_measurement("structure-bond", 1.0e-3, 1.0e-5, "two-wire-dc")
        self.assertFalse(result["compliant"])
        self.assertTrue(any("four-wire-dc required" in f for f in result["findings"]))

    def test_two_wire_method_accepted_on_a_bleed_path(self):
        result = evaluate_continuity_measurement("static-dissipative-bond", 1.0e6, 1.0e3, "two-wire-dc")
        self.assertTrue(result["compliant"], result["findings"])

    def test_dissipative_reading_below_lower_bound_is_flagged(self):
        result = evaluate_continuity_measurement("static-dissipative-bond", 1.0e2, 1.0e3, "two-wire-dc")
        self.assertFalse(result["within_bounds"])

    def test_coarse_instrument_resolution_is_flagged(self):
        result = evaluate_continuity_measurement("structure-bond", 1.0e-3, 1.0e-3, "four-wire-dc")
        self.assertFalse(result["compliant"])
        self.assertTrue(any("coarser" in f for f in result["findings"]))

    def test_resolution_exactly_one_tenth_of_the_bound_is_accepted(self):
        _, upper = resistance_bounds("equipment-chassis-bond")
        result = evaluate_continuity_measurement(
            "equipment-chassis-bond", 1.0e-3, upper / 10.0, "four-wire-dc"
        )
        self.assertTrue(result["compliant"], result["findings"])

    def test_negative_reading_raises(self):
        with self.assertRaises(ValueError):
            evaluate_continuity_measurement("structure-bond", -1.0e-3, 1.0e-5, "four-wire-dc")

    def test_non_finite_reading_raises(self):
        with self.assertRaises(ValueError):
            evaluate_continuity_measurement("structure-bond", float("inf"), 1.0e-5, "four-wire-dc")

    def test_non_numeric_reading_raises(self):
        with self.assertRaises(ValueError):
            evaluate_continuity_measurement("structure-bond", "1m", 1.0e-5, "four-wire-dc")

    def test_zero_resolution_raises(self):
        with self.assertRaises(ValueError):
            evaluate_continuity_measurement("structure-bond", 1.0e-3, 0.0, "four-wire-dc")

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            evaluate_continuity_measurement("structure-bond", 1.0e-3, 1.0e-5, "ac-bridge")


class TestBondResistanceMargin(unittest.TestCase):
    def test_half_the_bound_gives_half_margin(self):
        self.assertAlmostEqual(bond_resistance_margin("structure-bond", 1.25e-3), 0.5)

    def test_reading_at_the_bound_gives_zero_margin(self):
        self.assertAlmostEqual(bond_resistance_margin("equipment-chassis-bond", 1.0e-2), 0.0)

    def test_exceedance_gives_negative_margin(self):
        self.assertLess(bond_resistance_margin("equipment-chassis-bond", 2.0e-2), 0.0)

    def test_negative_reading_raises(self):
        with self.assertRaises(ValueError):
            bond_resistance_margin("structure-bond", -1.0)


class TestVerifyProvision(unittest.TestCase):
    def test_complete_provision_is_verified(self):
        result = verify_provision(good_provision())
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["margin"], 0.7)

    def test_inspection_gap_keeps_the_provision_open(self):
        result = verify_provision(
            good_provision(inspection=good_inspection(corrosion_protection="not-verified"))
        )
        self.assertEqual(result["status"], "open")
        self.assertTrue(result["continuity_compliant"])
        self.assertFalse(result["inspection_complete"])

    def test_continuity_gap_keeps_the_provision_open(self):
        result = verify_provision(
            good_provision(
                measurement={
                    "measured_ohm": 5.0e-2,
                    "resolution_ohm": 1.0e-4,
                    "method": "four-wire-dc",
                }
            )
        )
        self.assertEqual(result["status"], "open")
        self.assertTrue(result["inspection_complete"])
        self.assertFalse(result["continuity_compliant"])

    def test_blank_id_raises(self):
        with self.assertRaises(ValueError):
            verify_provision(good_provision(id="  "))

    def test_missing_measurement_raises(self):
        provision = good_provision()
        del provision["measurement"]
        with self.assertRaises(ValueError):
            verify_provision(provision)

    def test_measurement_missing_method_raises(self):
        with self.assertRaises(ValueError):
            verify_provision(
                good_provision(measurement={"measured_ohm": 1.0e-3, "resolution_ohm": 1.0e-5})
            )

    def test_non_mapping_provision_raises(self):
        with self.assertRaises(ValueError):
            verify_provision("BOND-001")


class TestVerifyGroundingNetwork(unittest.TestCase):
    def _network(self):
        return [
            good_provision(
                id="BOND-000",
                kind="structure-bond",
                inspection=good_inspection(conductor_routing="not-applicable"),
                measurement={
                    "measured_ohm": 1.0e-3,
                    "resolution_ohm": 1.0e-5,
                    "method": "four-wire-dc",
                },
            ),
            good_provision(),
        ]

    def test_complete_network_closes(self):
        summary = verify_grounding_network(self._network())
        self.assertTrue(summary["closed"])
        self.assertEqual(summary["verified_count"], 2)
        self.assertEqual(summary["open_ids"], [])

    def test_network_without_a_structure_reference_stays_open(self):
        summary = verify_grounding_network([good_provision()])
        self.assertFalse(summary["closed"])
        self.assertIn("no structure-bond reference point in the network", summary["network_findings"])

    def test_duplicate_provision_ids_are_reported(self):
        network = self._network()
        network.append(good_provision())
        summary = verify_grounding_network(network)
        self.assertFalse(summary["closed"])
        self.assertTrue(any("duplicate" in f for f in summary["network_findings"]))

    def test_one_open_provision_opens_the_network(self):
        network = self._network()
        network[1]["inspection"] = good_inspection(fastener_installation="not-verified")
        summary = verify_grounding_network(network)
        self.assertFalse(summary["closed"])
        self.assertEqual(summary["open_ids"], ["BOND-001"])

    def test_categories_present_are_reported_sorted(self):
        summary = verify_grounding_network(self._network())
        self.assertEqual(summary["categories_present"], ["equipment-chassis-bond", "structure-bond"])

    def test_empty_network_raises(self):
        with self.assertRaises(ValueError):
            verify_grounding_network([])

    def test_non_list_network_raises(self):
        with self.assertRaises(ValueError):
            verify_grounding_network({"id": "BOND-001"})


if __name__ == "__main__":
    unittest.main()
