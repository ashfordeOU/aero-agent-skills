#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 4.2.3 electrical
connector design rules.

Exercises scripts/e20_electrical_connector_design_rules_logic.py
(stdlib unittest, offline). Contract: a connection type categorizes
into exactly one family and an unrecognized type raises; the half that
stays energized after separation must carry socket contacts and a
declared pin there is an exposed-energized-contact finding, while an
unreadable style raises; the scoop-proof decision fires at the voltage
or contact-count threshold and rejects a negative voltage or a
non-integer contact count; the demanded safety-feature set follows the
family, the live side and the shroud decision, and the gap against the
implemented set is reported per feature; the mating sequence must be
non-decreasing in contact rank, with an empty sequence or an unknown
role raising; zone keying uniqueness is a pairwise property that only
fires across connectors and rejects an incomplete entry; and the
aggregated review is compliant only when it carries no findings.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_electrical_connector_design_rules_logic as cd  # noqa: E402


class CategorizeConnectionTest(unittest.TestCase):
    def test_power_source_is_power(self):
        self.assertEqual(cd.categorize_connection("power_source"), "power")

    def test_test_umbilical_is_test(self):
        self.assertEqual(cd.categorize_connection("test_umbilical"), "test")

    def test_telemetry_is_signal(self):
        self.assertEqual(cd.categorize_connection("telemetry"), "signal")

    def test_pyrotechnic_firing_is_ordnance(self):
        self.assertEqual(cd.categorize_connection("pyrotechnic_firing"), "ordnance")

    def test_every_known_connection_type_resolves_to_its_family(self):
        for family, members in cd.CONNECTION_FAMILIES.items():
            for connection_type in members:
                self.assertEqual(cd.categorize_connection(connection_type), family)

    def test_unrecognized_connection_type_raises(self):
        with self.assertRaises(ValueError):
            cd.categorize_connection("fibre_optic_patch")


class ContactStyleTest(unittest.TestCase):
    def test_energized_half_takes_socket_contacts(self):
        self.assertEqual(cd.required_contact_style(True), "socket")

    def test_de_energized_half_takes_pin_contacts(self):
        self.assertEqual(cd.required_contact_style(False), "pin")

    def test_socket_on_the_live_half_is_compliant(self):
        self.assertEqual(cd.contact_style_violations("J1", "socket", True), [])

    def test_pin_on_the_de_energized_half_is_compliant(self):
        self.assertEqual(cd.contact_style_violations("J1", "pin", False), [])

    def test_pin_on_the_live_half_is_an_exposed_contact_finding(self):
        found = cd.contact_style_violations("J1", "pin", True)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["issue"], "exposed_energized_contact")
        self.assertEqual(found[0]["required_style"], "socket")

    def test_socket_on_the_de_energized_half_is_flagged_as_inverted(self):
        found = cd.contact_style_violations("J1", "socket", False)
        self.assertEqual(found[0]["issue"], "contact_style_inverted")

    def test_unreadable_contact_style_raises(self):
        with self.assertRaises(ValueError):
            cd.contact_style_violations("J1", "blade", True)


class ScoopProofThresholdTest(unittest.TestCase):
    def test_low_voltage_low_density_needs_no_shroud(self):
        self.assertFalse(cd.scoop_proof_required(28.0, 9))

    def test_voltage_at_the_threshold_demands_a_shroud(self):
        self.assertTrue(
            cd.scoop_proof_required(cd.SCOOP_PROOF_VOLTAGE_THRESHOLD_V, 9)
        )

    def test_voltage_just_below_the_threshold_does_not(self):
        self.assertFalse(
            cd.scoop_proof_required(cd.SCOOP_PROOF_VOLTAGE_THRESHOLD_V - 0.1, 9)
        )

    def test_contact_count_at_the_threshold_demands_a_shroud(self):
        self.assertTrue(
            cd.scoop_proof_required(28.0, cd.SCOOP_PROOF_CONTACT_THRESHOLD)
        )

    def test_contact_count_just_below_the_threshold_does_not(self):
        self.assertFalse(
            cd.scoop_proof_required(28.0, cd.SCOOP_PROOF_CONTACT_THRESHOLD - 1)
        )

    def test_negative_voltage_raises(self):
        with self.assertRaises(ValueError):
            cd.scoop_proof_required(-1.0, 9)

    def test_non_integer_contact_count_raises(self):
        with self.assertRaises(ValueError):
            cd.scoop_proof_required(28.0, 9.5)

    def test_boolean_contact_count_raises(self):
        with self.assertRaises(ValueError):
            cd.scoop_proof_required(28.0, True)

    def test_negative_contact_count_raises(self):
        with self.assertRaises(ValueError):
            cd.scoop_proof_required(28.0, -3)


class SafetyFeatureDerivationTest(unittest.TestCase):
    def test_live_power_connection_demands_the_core_feature_set(self):
        features = cd.required_safety_features("power_source", 28.0, 9, True)
        self.assertEqual(
            features,
            (
                "de_energized_demate_inhibit",
                "keying",
                "protective_cover",
                "socket_contacts_on_energized_half",
            ),
        )

    def test_de_energized_power_connection_drops_the_live_side_features(self):
        features = cd.required_safety_features("power_source", 28.0, 9, False)
        self.assertEqual(features, ("de_energized_demate_inhibit", "keying"))

    def test_signal_connection_demands_only_keying(self):
        features = cd.required_safety_features("telemetry", 5.0, 9, False)
        self.assertEqual(features, ("keying",))

    def test_test_connection_adds_isolation_and_demate_verification(self):
        features = cd.required_safety_features("test_umbilical", 28.0, 9, False)
        self.assertIn("isolation_element", features)
        self.assertIn("demate_verification", features)

    def test_ordnance_connection_adds_a_shorting_feature(self):
        features = cd.required_safety_features("pyrotechnic_firing", 28.0, 9, False)
        self.assertIn("initiator_shorting_feature", features)

    def test_high_voltage_connection_adds_the_shroud(self):
        features = cd.required_safety_features("power_source", 120.0, 9, False)
        self.assertIn("scoop_proof_shroud", features)

    def test_missing_features_report_only_the_gap(self):
        gap = cd.missing_safety_features(
            "power_source", 28.0, 9, True, ["keying", "protective_cover"]
        )
        self.assertEqual(
            gap, ("de_energized_demate_inhibit", "socket_contacts_on_energized_half")
        )

    def test_extra_implemented_features_are_ignored(self):
        gap = cd.missing_safety_features(
            "telemetry", 5.0, 9, False, ["keying", "gold_plating", "lanyard"]
        )
        self.assertEqual(gap, ())

    def test_unrecognized_connection_type_in_derivation_raises(self):
        with self.assertRaises(ValueError):
            cd.required_safety_features("fibre_optic_patch", 28.0, 9, True)


class MateSequenceTest(unittest.TestCase):
    def test_canonical_order_is_compliant(self):
        sequence = ["chassis_ground", "power_return", "power_positive", "signal"]
        self.assertEqual(cd.mate_sequence_violations("J1", sequence), [])

    def test_repeated_role_at_equal_rank_is_compliant(self):
        sequence = ["chassis_ground", "chassis_ground", "power_return"]
        self.assertEqual(cd.mate_sequence_violations("J1", sequence), [])

    def test_partial_sequence_missing_roles_is_compliant(self):
        self.assertEqual(
            cd.mate_sequence_violations("J1", ["chassis_ground", "signal"]), []
        )

    def test_power_ahead_of_chassis_is_flagged_at_its_position(self):
        found = cd.mate_sequence_violations("J1", ["power_positive", "chassis_ground"])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["issue"], "mate_sequence_out_of_order")
        self.assertEqual(found[0]["position"], 1)
        self.assertEqual(found[0]["role"], "chassis_ground")

    def test_only_the_first_break_in_order_is_reported(self):
        found = cd.mate_sequence_violations(
            "J1", ["signal", "power_positive", "chassis_ground"]
        )
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["position"], 1)

    def test_empty_sequence_raises(self):
        with self.assertRaises(ValueError):
            cd.mate_sequence_violations("J1", [])

    def test_unrecognized_contact_role_raises(self):
        with self.assertRaises(ValueError):
            cd.mate_sequence_violations("J1", ["chassis_ground", "coolant_line"])


class ZoneKeyingTest(unittest.TestCase):
    def _connector(self, connector_id, keying, zone="bay-1"):
        return {
            "connector_id": connector_id,
            "zone": zone,
            "shell_size": 15,
            "insert_arrangement": "15-35",
            "keying": keying,
        }

    def test_distinct_keying_in_a_zone_is_compliant(self):
        connectors = [self._connector("J1", "A"), self._connector("J2", "B")]
        self.assertEqual(cd.keying_violations(connectors), [])

    def test_shared_keying_in_a_zone_is_flagged_as_a_pair(self):
        connectors = [self._connector("J1", "A"), self._connector("J2", "A")]
        found = cd.keying_violations(connectors)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["issue"], "cross_mateable_keying_not_unique")
        self.assertEqual(found[0]["connectors"], ["J1", "J2"])

    def test_same_keying_in_different_zones_is_compliant(self):
        connectors = [
            self._connector("J1", "A", zone="bay-1"),
            self._connector("J2", "A", zone="bay-2"),
        ]
        self.assertEqual(cd.keying_violations(connectors), [])

    def test_same_keying_with_a_different_insert_is_compliant(self):
        first = self._connector("J1", "A")
        second = self._connector("J2", "A")
        second["insert_arrangement"] = "15-18"
        self.assertEqual(cd.keying_violations([first, second]), [])

    def test_a_single_connector_can_never_fail_the_keying_check(self):
        self.assertEqual(cd.keying_violations([self._connector("J1", "A")]), [])

    def test_empty_zone_is_compliant(self):
        self.assertEqual(cd.keying_violations([]), [])

    def test_connector_missing_a_keying_field_raises(self):
        incomplete = self._connector("J1", "A")
        del incomplete["keying"]
        with self.assertRaises(ValueError):
            cd.keying_violations([incomplete])


class ConnectorDesignReviewTest(unittest.TestCase):
    def _connector(self):
        return {
            "connector_id": "J12",
            "connection_type": "power_source",
            "voltage_v": 28.0,
            "contact_count": 9,
            "energized_when_demated": True,
            "contact_style": "socket",
            "implemented_features": [
                "keying",
                "socket_contacts_on_energized_half",
                "protective_cover",
                "de_energized_demate_inhibit",
            ],
            "contact_sequence": ["chassis_ground", "power_return", "power_positive"],
        }

    def test_fully_featured_connector_is_compliant(self):
        review = cd.connector_design_review(self._connector())
        self.assertEqual(review["findings"], [])
        self.assertTrue(cd.is_connector_compliant(review))

    def test_review_reports_family_and_shroud_decision(self):
        review = cd.connector_design_review(self._connector())
        self.assertEqual(review["family"], "power")
        self.assertFalse(review["scoop_proof_required"])

    def test_review_does_not_mutate_the_input_connector(self):
        connector = self._connector()
        before = repr(connector)
        cd.connector_design_review(connector)
        self.assertEqual(repr(connector), before)

    def test_pins_on_a_live_half_surface_as_a_finding(self):
        connector = self._connector()
        connector["contact_style"] = "pin"
        review = cd.connector_design_review(connector)
        self.assertIn(
            "exposed_energized_contact", [f["issue"] for f in review["findings"]]
        )
        self.assertFalse(cd.is_connector_compliant(review))

    def test_bare_test_umbilical_collects_every_missing_feature(self):
        connector = {
            "connector_id": "J-GSE",
            "connection_type": "test_umbilical",
            "voltage_v": 120.0,
            "contact_count": 37,
            "energized_when_demated": True,
            "contact_style": "socket",
            "implemented_features": ["keying"],
        }
        review = cd.connector_design_review(connector)
        missing = sorted(
            f["feature"]
            for f in review["findings"]
            if f["issue"] == "safety_feature_not_implemented"
        )
        self.assertEqual(
            missing,
            [
                "de_energized_demate_inhibit",
                "demate_verification",
                "isolation_element",
                "protective_cover",
                "scoop_proof_shroud",
                "socket_contacts_on_energized_half",
            ],
        )
        self.assertTrue(review["scoop_proof_required"])

    def test_out_of_order_sequence_surfaces_in_the_review(self):
        connector = self._connector()
        connector["contact_sequence"] = ["power_positive", "chassis_ground"]
        review = cd.connector_design_review(connector)
        self.assertIn(
            "mate_sequence_out_of_order", [f["issue"] for f in review["findings"]]
        )

    def test_review_without_a_declared_sequence_skips_that_check(self):
        connector = self._connector()
        del connector["contact_sequence"]
        review = cd.connector_design_review(connector)
        self.assertEqual(review["findings"], [])

    def test_unrecognized_connection_type_in_review_raises(self):
        connector = self._connector()
        connector["connection_type"] = "fibre_optic_patch"
        with self.assertRaises(ValueError):
            cd.connector_design_review(connector)

    def test_bad_contact_count_in_review_raises(self):
        connector = self._connector()
        connector["contact_count"] = -1
        with self.assertRaises(ValueError):
            cd.connector_design_review(connector)


if __name__ == "__main__":
    unittest.main()
