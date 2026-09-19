"""Contract test for the e3311 harness-connector/test-substitute leaf (stdlib unittest)."""

import unittest

from e3311_initiator_harness_connector_test_substitute_logic import (
    CONNECTOR_CONTROLS,
    DEFAULT_HARNESS_POLICY,
    SUBSTITUTE_CONTROLS,
    VERDICT_MET,
    VERDICT_NOT_MET,
    assess_connector_controls,
    assess_contact_rating,
    assess_harness_connector_and_substitute,
    assess_keying_uniqueness,
    assess_test_substitute,
    required_contact_rating_a,
    resistance_deviation,
    validate_harness_policy,
)


def connector_controls(**kw):
    controls = {name: True for name in CONNECTOR_CONTROLS}
    controls.update(kw)
    return controls


def substitute_controls(**kw):
    controls = {name: True for name in SUBSTITUTE_CONTROLS}
    controls.update(kw)
    return controls


def contacts(**kw):
    case = {"all_fire_current_a": 5.0, "contact_rated_current_a": 15.0}
    case.update(kw)
    return case


def keying(**kw):
    codes = {"circuit-a": "K-1", "circuit-b": "K-2", "circuit-c": "K-3"}
    codes.update(kw)
    return codes


def substitute(**kw):
    case = {
        "flight_bridge_resistance_ohm": 1.0,
        "substitute_bridge_resistance_ohm": 1.02,
        "insulation_resistance_ohm": 5.0e6,
        "insulation_test_voltage_v": 500.0,
        "flight_identification_colour": "red",
        "substitute_identification_colour": "blue",
        "controls": substitute_controls(),
    }
    case.update(kw)
    return case


def full_case(**kw):
    case = {
        "contacts": contacts(),
        "circuit_keying": keying(),
        "connector_controls": connector_controls(),
        "test_substitute": substitute(),
    }
    case.update(kw)
    return case


class TestPolicyValidation(unittest.TestCase):
    def test_default_policy_is_valid(self):
        self.assertIs(
            validate_harness_policy(DEFAULT_HARNESS_POLICY), DEFAULT_HARNESS_POLICY
        )

    def test_non_mapping_policy_raises(self):
        with self.assertRaises(ValueError):
            validate_harness_policy(["contact_current_derating", 0.5])

    def test_derating_above_unity_raises(self):
        policy = dict(DEFAULT_HARNESS_POLICY, contact_current_derating=1.2)
        with self.assertRaises(ValueError):
            validate_harness_policy(policy)

    def test_tolerance_at_unity_raises(self):
        policy = dict(DEFAULT_HARNESS_POLICY, bridge_resistance_tolerance=1.0)
        with self.assertRaises(ValueError):
            validate_harness_policy(policy)

    def test_unknown_connector_control_in_policy_raises(self):
        policy = dict(DEFAULT_HARNESS_POLICY, required_connector_controls=("gold-shell",))
        with self.assertRaises(ValueError):
            validate_harness_policy(policy)

    def test_empty_substitute_control_list_raises(self):
        policy = dict(DEFAULT_HARNESS_POLICY, required_substitute_controls=())
        with self.assertRaises(ValueError):
            validate_harness_policy(policy)


class TestRatingArithmetic(unittest.TestCase):
    def test_a_half_derating_doubles_the_required_rating(self):
        self.assertAlmostEqual(required_contact_rating_a(5.0, 0.5), 10.0, places=12)

    def test_unity_derating_leaves_the_rating_alone(self):
        self.assertAlmostEqual(required_contact_rating_a(5.0, 1.0), 5.0, places=12)

    def test_a_derating_above_unity_raises(self):
        with self.assertRaises(ValueError):
            required_contact_rating_a(5.0, 1.5)

    def test_a_zero_all_fire_current_raises(self):
        with self.assertRaises(ValueError):
            required_contact_rating_a(0.0, 0.5)

    def test_a_boolean_current_raises(self):
        with self.assertRaises(ValueError):
            required_contact_rating_a(True, 0.5)

    def test_resistance_deviation_is_symmetric_in_sign(self):
        self.assertAlmostEqual(resistance_deviation(1.0, 1.2), 0.2, places=12)
        self.assertAlmostEqual(resistance_deviation(1.0, 0.8), 0.2, places=12)

    def test_resistance_deviation_is_zero_on_a_match(self):
        self.assertAlmostEqual(resistance_deviation(1.05, 1.05), 0.0, places=12)

    def test_resistance_deviation_rejects_a_zero_reference(self):
        with self.assertRaises(ValueError):
            resistance_deviation(0.0, 1.0)


class TestContactRating(unittest.TestCase):
    def test_a_generous_contact_passes(self):
        result = assess_contact_rating(contacts())
        self.assertTrue(result["compliant"])

    def test_a_contact_exactly_on_the_required_rating_passes(self):
        result = assess_contact_rating(contacts(contact_rated_current_a=10.0))
        self.assertAlmostEqual(result["required_rating_a"], 10.0, places=9)
        self.assertTrue(result["compliant"])

    def test_an_underrated_contact_fails(self):
        result = assess_contact_rating(contacts(contact_rated_current_a=6.0))
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_tighter_derating_raises_the_bar(self):
        policy = dict(DEFAULT_HARNESS_POLICY, contact_current_derating=0.25)
        result = assess_contact_rating(contacts(), policy)
        self.assertAlmostEqual(result["required_rating_a"], 20.0, places=9)
        self.assertFalse(result["compliant"])

    def test_a_missing_rated_current_raises(self):
        case = contacts()
        del case["contact_rated_current_a"]
        with self.assertRaises(ValueError):
            assess_contact_rating(case)


class TestKeyingUniqueness(unittest.TestCase):
    def test_three_distinct_codes_pass(self):
        result = assess_keying_uniqueness(keying())
        self.assertTrue(result["compliant"])

    def test_a_shared_code_names_both_circuits(self):
        result = assess_keying_uniqueness(keying(**{"circuit-c": "K-1"}))
        self.assertFalse(result["compliant"])
        finding = result["findings"][0]
        self.assertIn("circuit-a", finding)
        self.assertIn("circuit-c", finding)

    def test_an_empty_keying_map_raises(self):
        with self.assertRaises(ValueError):
            assess_keying_uniqueness({})

    def test_a_blank_keying_code_raises(self):
        with self.assertRaises(ValueError):
            assess_keying_uniqueness(keying(**{"circuit-b": "  "}))


class TestConnectorControls(unittest.TestCase):
    def test_a_complete_control_set_passes(self):
        result = assess_connector_controls(connector_controls())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["controls_absent"], [])

    def test_a_missing_shorting_control_is_named(self):
        result = assess_connector_controls(
            connector_controls(**{"contacts-shorted-and-grounded-when-unmated": False})
        )
        self.assertFalse(result["compliant"])
        self.assertIn(
            "contacts-shorted-and-grounded-when-unmated", result["controls_absent"]
        )

    def test_an_undeclared_control_raises(self):
        controls = connector_controls()
        del controls["scoop-proof-sockets-on-live-side"]
        with self.assertRaises(ValueError):
            assess_connector_controls(controls)

    def test_an_unknown_control_key_raises(self):
        with self.assertRaises(ValueError):
            assess_connector_controls(connector_controls(**{"gold-shell": True}))

    def test_a_non_boolean_control_state_raises(self):
        controls = connector_controls()
        controls["unique-keying-per-firing-circuit"] = 1
        with self.assertRaises(ValueError):
            assess_connector_controls(controls)


class TestTestSubstitute(unittest.TestCase):
    def test_a_faithful_substitute_passes(self):
        result = assess_test_substitute(substitute())
        self.assertTrue(result["compliant"])

    def test_a_deviation_exactly_on_the_tolerance_passes(self):
        result = assess_test_substitute(
            substitute(substitute_bridge_resistance_ohm=1.1)
        )
        self.assertAlmostEqual(result["resistance_deviation"], 0.10, places=9)
        self.assertTrue(result["compliant"])

    def test_a_far_off_resistance_fails(self):
        result = assess_test_substitute(
            substitute(substitute_bridge_resistance_ohm=2.0)
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("bridge resistance" in f for f in result["findings"]))

    def test_a_low_insulation_resistance_fails(self):
        result = assess_test_substitute(substitute(insulation_resistance_ohm=1.0e5))
        self.assertFalse(result["compliant"])

    def test_an_insulation_measurement_at_too_low_a_voltage_fails(self):
        result = assess_test_substitute(substitute(insulation_test_voltage_v=50.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("does not demonstrate" in f for f in result["findings"]))

    def test_a_substitute_in_the_flight_colour_fails(self):
        result = assess_test_substitute(
            substitute(substitute_identification_colour="red")
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("flight hardware" in f for f in result["findings"]))

    def test_a_missing_substitute_control_is_named(self):
        result = assess_test_substitute(
            substitute(controls=substitute_controls(**{"serialised-and-logged": False}))
        )
        self.assertFalse(result["compliant"])
        self.assertIn("serialised-and-logged", result["controls_absent"])

    def test_an_undeclared_substitute_control_raises(self):
        controls = substitute_controls()
        del controls["inert-no-energetic-material"]
        with self.assertRaises(ValueError):
            assess_test_substitute(substitute(controls=controls))

    def test_a_non_mapping_control_block_raises(self):
        with self.assertRaises(ValueError):
            assess_test_substitute(substitute(controls=["inert"]))


class TestFullAssessment(unittest.TestCase):
    def test_a_sound_interface_is_met(self):
        report = assess_harness_connector_and_substitute(full_case())
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["failed_parts"], [])
        self.assertEqual(report["findings"], [])

    def test_one_broken_part_names_only_itself(self):
        case = full_case(contacts=contacts(contact_rated_current_a=6.0))
        report = assess_harness_connector_and_substitute(case)
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)
        self.assertEqual(report["failed_parts"], ["contact-rating"])

    def test_two_broken_parts_are_both_named(self):
        case = full_case(
            circuit_keying=keying(**{"circuit-b": "K-1"}),
            test_substitute=substitute(substitute_identification_colour="red"),
        )
        report = assess_harness_connector_and_substitute(case)
        self.assertEqual(
            report["failed_parts"], ["keying-uniqueness", "test-substitute"]
        )
        self.assertGreaterEqual(len(report["findings"]), 2)

    def test_every_part_appears_in_the_report(self):
        report = assess_harness_connector_and_substitute(full_case())
        for name in (
            "contact-rating",
            "keying-uniqueness",
            "connector-controls",
            "test-substitute",
        ):
            self.assertIn(name, report["parts"])

    def test_a_non_mapping_case_raises(self):
        with self.assertRaises(ValueError):
            assess_harness_connector_and_substitute("one connector")

    def test_a_case_without_keying_raises(self):
        case = full_case()
        del case["circuit_keying"]
        with self.assertRaises(ValueError):
            assess_harness_connector_and_substitute(case)


if __name__ == "__main__":
    unittest.main()
