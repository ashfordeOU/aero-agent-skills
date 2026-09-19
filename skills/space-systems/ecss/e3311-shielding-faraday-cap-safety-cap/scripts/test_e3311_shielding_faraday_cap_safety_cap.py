"""Contract tests for the clause 4.10.3-4.10.5 shielding and cap logic."""

import math
import unittest

from e3311_shielding_faraday_cap_safety_cap_logic import (
    CAP_DEFECT,
    FARADAY_REQUIREMENTS,
    MARGIN_SHORT,
    PROTECTED,
    UNPROTECTED,
    assess_initiator_protection,
    faraday_cap_findings,
    field_attenuation_factor,
    no_fire_margin_db,
    power_attenuation_factor,
    required_shield_db,
    safety_cap_findings,
    shielded_power_w,
    validate_db,
    validate_non_negative,
    validate_positive,
)

INCIDENT_W = 1.0
NO_FIRE_W = 0.001
SHIELD_DB = 60.0
MARGIN_DB = 20.0


def faraday(**overrides):
    declared = {name: True for name in FARADAY_REQUIREMENTS}
    declared.update(overrides)
    return declared


def sequence(**overrides):
    steps = [
        {"name": "receipt inspection", "cap_fitted": True},
        {"name": "mechanical integration", "cap_fitted": True},
        {"name": "harness mate", "cap_fitted": True},
        {"name": "arm authorisation", "cap_fitted": True},
        {"name": "launch", "cap_fitted": False},
    ]
    for index, patch in overrides.items():
        steps[int(index)].update(patch)
    return steps


REMOVAL = "arm authorisation"


class ValidationTests(unittest.TestCase):
    def test_zero_rejected_where_positive_required(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0)

    def test_zero_accepted_where_non_negative_required(self):
        self.assertAlmostEqual(validate_non_negative(0), 0.0, places=9)

    def test_negative_shield_rejected(self):
        with self.assertRaises(ValueError):
            validate_db(-1.0)

    def test_zero_shield_accepted(self):
        self.assertAlmostEqual(validate_db(0), 0.0, places=9)

    def test_boolean_rejected_as_a_number(self):
        with self.assertRaises(ValueError):
            validate_db(True)

    def test_text_rejected_as_a_number(self):
        with self.assertRaises(ValueError):
            validate_db("60")

    def test_infinite_rejected(self):
        with self.assertRaises(ValueError):
            validate_non_negative(float("inf"))

    def test_nan_rejected(self):
        with self.assertRaises(ValueError):
            validate_non_negative(float("nan"))


class AttenuationTests(unittest.TestCase):
    def test_no_shield_attenuates_nothing(self):
        self.assertAlmostEqual(power_attenuation_factor(0.0), 1.0, places=9)

    def test_ten_decibels_is_a_factor_of_ten_in_power(self):
        self.assertAlmostEqual(power_attenuation_factor(10.0), 10.0, places=9)

    def test_twenty_decibels_is_a_factor_of_ten_in_field(self):
        self.assertAlmostEqual(field_attenuation_factor(20.0), 10.0, places=9)

    def test_field_and_power_factors_are_consistent(self):
        self.assertAlmostEqual(
            field_attenuation_factor(40.0) ** 2,
            power_attenuation_factor(40.0),
            places=6,
        )

    def test_shield_divides_the_incident_power(self):
        self.assertAlmostEqual(shielded_power_w(1.0, 30.0), 1e-3, places=9)

    def test_no_incident_power_gets_through_nothing(self):
        self.assertAlmostEqual(shielded_power_w(0.0, SHIELD_DB), 0.0, places=9)


class MarginTests(unittest.TestCase):
    def test_a_shield_exactly_at_the_no_fire_power_has_no_margin(self):
        self.assertAlmostEqual(
            no_fire_margin_db(1.0, 30.0, 1e-3), 0.0, places=9
        )

    def test_more_shielding_buys_margin_one_for_one(self):
        self.assertAlmostEqual(
            no_fire_margin_db(1.0, 50.0, 1e-3), 20.0, places=9
        )

    def test_a_field_free_environment_has_unbounded_margin(self):
        self.assertIsNone(no_fire_margin_db(0.0, SHIELD_DB, NO_FIRE_W))

    def test_zero_no_fire_power_rejected(self):
        with self.assertRaises(ValueError):
            no_fire_margin_db(1.0, SHIELD_DB, 0.0)

    def test_required_shield_reaches_the_margin(self):
        needed = required_shield_db(INCIDENT_W, NO_FIRE_W, MARGIN_DB)
        self.assertAlmostEqual(
            no_fire_margin_db(INCIDENT_W, needed, NO_FIRE_W), MARGIN_DB, places=9
        )

    def test_required_shield_is_the_ratio_plus_the_margin(self):
        expected = 10.0 * math.log10(INCIDENT_W / NO_FIRE_W) + MARGIN_DB
        self.assertAlmostEqual(
            required_shield_db(INCIDENT_W, NO_FIRE_W, MARGIN_DB), expected, places=9
        )

    def test_an_already_clear_field_needs_no_shield_for_this(self):
        self.assertAlmostEqual(
            required_shield_db(1e-9, NO_FIRE_W, 10.0), 0.0, places=9
        )

    def test_no_field_needs_no_shield_for_this(self):
        self.assertAlmostEqual(required_shield_db(0.0, NO_FIRE_W, 20.0), 0.0, places=9)


class FaradayTests(unittest.TestCase):
    def test_a_full_cap_declaration_is_clean(self):
        self.assertEqual(faraday_cap_findings(faraday()), [])

    def test_each_requirement_is_detected_when_dropped(self):
        for name in FARADAY_REQUIREMENTS:
            findings = faraday_cap_findings(faraday(**{name: False}))
            self.assertTrue(any(name in f for f in findings))

    def test_an_undeclared_requirement_counts_as_absent(self):
        declared = faraday()
        del declared["shorts_pin_to_case"]
        self.assertTrue(faraday_cap_findings(declared))

    def test_a_non_boolean_declaration_rejected(self):
        with self.assertRaises(ValueError):
            faraday_cap_findings(faraday(shorts_pin_to_pin="yes"))

    def test_a_non_mapping_declaration_rejected(self):
        with self.assertRaises(ValueError):
            faraday_cap_findings(["shorts_pin_to_pin"])


class SafetyCapTests(unittest.TestCase):
    def test_a_correct_sequence_is_clean(self):
        self.assertEqual(safety_cap_findings(sequence(), REMOVAL), [])

    def test_an_early_removal_is_reported(self):
        steps = sequence(**{"1": {"cap_fitted": False}})
        findings = safety_cap_findings(steps, REMOVAL)
        self.assertTrue(any("mechanical integration" in f for f in findings))

    def test_a_removal_at_harness_mate_is_reported(self):
        steps = sequence(**{"2": {"cap_fitted": False}})
        self.assertTrue(
            any("before the authorised removal" in f for f in safety_cap_findings(steps, REMOVAL))
        )

    def test_an_interruption_after_removal_needs_the_cap_back(self):
        steps = sequence(**{"4": {"interrupted": True}})
        findings = safety_cap_findings(steps, REMOVAL)
        self.assertTrue(any("goes back on for an interruption" in f for f in findings))

    def test_an_interruption_with_the_cap_refitted_is_clean(self):
        steps = sequence(**{"4": {"interrupted": True, "cap_fitted": True}})
        self.assertEqual(safety_cap_findings(steps, REMOVAL), [])

    def test_an_unknown_removal_step_rejected(self):
        with self.assertRaises(ValueError):
            safety_cap_findings(sequence(), "coffee break")

    def test_an_empty_sequence_rejected(self):
        with self.assertRaises(ValueError):
            safety_cap_findings([], REMOVAL)

    def test_a_step_without_a_name_rejected(self):
        with self.assertRaises(ValueError):
            safety_cap_findings([{"cap_fitted": True}], REMOVAL)

    def test_a_non_boolean_cap_state_rejected(self):
        with self.assertRaises(ValueError):
            safety_cap_findings([{"name": "receipt", "cap_fitted": "on"}], "receipt")

    def test_a_single_mapping_is_not_a_sequence(self):
        with self.assertRaises(ValueError):
            safety_cap_findings({"name": "receipt", "cap_fitted": True}, "receipt")


class AssessTests(unittest.TestCase):
    def test_a_sound_circuit_is_protected(self):
        result = assess_initiator_protection(
            INCIDENT_W, 60.0, NO_FIRE_W, MARGIN_DB, faraday(), sequence(), REMOVAL
        )
        self.assertEqual(result["verdict"], PROTECTED)
        self.assertEqual(result["findings"], [])

    def test_a_circuit_exactly_on_its_margin_is_protected(self):
        needed = required_shield_db(INCIDENT_W, NO_FIRE_W, MARGIN_DB)
        result = assess_initiator_protection(
            INCIDENT_W, needed, NO_FIRE_W, MARGIN_DB, faraday(), sequence(), REMOVAL
        )
        self.assertAlmostEqual(result["no_fire_margin_db"], MARGIN_DB, places=9)
        self.assertEqual(result["verdict"], PROTECTED)

    def test_a_thin_shield_is_margin_short(self):
        result = assess_initiator_protection(
            INCIDENT_W, 35.0, NO_FIRE_W, MARGIN_DB, faraday(), sequence(), REMOVAL
        )
        self.assertEqual(result["verdict"], MARGIN_SHORT)
        self.assertTrue(any("required margin of" in f for f in result["findings"]))

    def test_a_margin_short_circuit_is_told_the_shield_it_needs(self):
        result = assess_initiator_protection(
            INCIDENT_W, 35.0, NO_FIRE_W, MARGIN_DB, faraday(), sequence(), REMOVAL
        )
        self.assertTrue(any("shield effectiveness of at least" in f for f in result["findings"]))

    def test_the_named_shield_actually_reaches_the_margin(self):
        result = assess_initiator_protection(
            INCIDENT_W, 35.0, NO_FIRE_W, MARGIN_DB, faraday(), sequence(), REMOVAL
        )
        fixed = assess_initiator_protection(
            INCIDENT_W,
            result["required_shield_db"],
            NO_FIRE_W,
            MARGIN_DB,
            faraday(),
            sequence(),
            REMOVAL,
        )
        self.assertEqual(fixed["verdict"], PROTECTED)

    def test_a_pickup_above_the_no_fire_power_is_unprotected(self):
        result = assess_initiator_protection(
            INCIDENT_W, 10.0, NO_FIRE_W, MARGIN_DB, faraday(), sequence(), REMOVAL
        )
        self.assertEqual(result["verdict"], UNPROTECTED)
        self.assertTrue(any("can be set off by the field" in f for f in result["findings"]))

    def test_a_cap_defect_outranks_a_met_margin(self):
        result = assess_initiator_protection(
            INCIDENT_W,
            60.0,
            NO_FIRE_W,
            MARGIN_DB,
            faraday(shorts_pin_to_case=False),
            sequence(),
            REMOVAL,
        )
        self.assertEqual(result["verdict"], CAP_DEFECT)

    def test_a_bare_initiator_in_the_sequence_is_a_cap_defect(self):
        result = assess_initiator_protection(
            INCIDENT_W,
            60.0,
            NO_FIRE_W,
            MARGIN_DB,
            faraday(),
            sequence(**{"0": {"cap_fitted": False}}),
            REMOVAL,
        )
        self.assertEqual(result["verdict"], CAP_DEFECT)
        self.assertTrue(result["safety_cap_findings"])

    def test_an_energised_circuit_outranks_a_cap_defect(self):
        result = assess_initiator_protection(
            INCIDENT_W,
            10.0,
            NO_FIRE_W,
            MARGIN_DB,
            faraday(shorts_pin_to_pin=False),
            sequence(),
            REMOVAL,
        )
        self.assertEqual(result["verdict"], UNPROTECTED)

    def test_the_two_cap_findings_are_reported_separately(self):
        result = assess_initiator_protection(
            INCIDENT_W,
            60.0,
            NO_FIRE_W,
            MARGIN_DB,
            faraday(fitted_when_demated=False),
            sequence(**{"1": {"cap_fitted": False}}),
            REMOVAL,
        )
        self.assertTrue(result["faraday_findings"])
        self.assertTrue(result["safety_cap_findings"])

    def test_a_field_free_circuit_is_protected(self):
        result = assess_initiator_protection(
            0.0, 0.0, NO_FIRE_W, MARGIN_DB, faraday(), sequence(), REMOVAL
        )
        self.assertIsNone(result["no_fire_margin_db"])
        self.assertEqual(result["verdict"], PROTECTED)

    def test_bad_no_fire_power_rejected(self):
        with self.assertRaises(ValueError):
            assess_initiator_protection(
                INCIDENT_W, 60.0, 0.0, MARGIN_DB, faraday(), sequence(), REMOVAL
            )

    def test_bad_shield_rejected(self):
        with self.assertRaises(ValueError):
            assess_initiator_protection(
                INCIDENT_W, -5.0, NO_FIRE_W, MARGIN_DB, faraday(), sequence(), REMOVAL
            )


if __name__ == "__main__":
    unittest.main()
