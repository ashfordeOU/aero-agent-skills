"""Contract tests for the clause 6.3.8 class 3 radiation verification logic.

The cases follow the verification one step at a time: the two routes into
radiation sensitivity, the penalty each evidence tier carries, the required
capability the mission dose scales into, the total dose comparison at and
around its limit, the destructive single-event check that no dose margin
waives, and the five verdicts a part can end in. Limits are exercised on both
sides and exactly on the boundary.
"""

import unittest

from q6013_class_3_radiation_verification_testing_logic import (
    DEFAULT_RADIATION_DESIGN_MARGIN,
    EVIDENCE_TIER_PENALTY,
    assess_class3_radiation_verification,
    destructive_see_status,
    evidence_tier_penalty,
    radiation_sensitivity,
    required_capability_krad,
    total_dose_verdict,
)


def _spec(**overrides):
    spec = {
        "technology_family": "sram-memory",
        "mission_dose_krad": 10.0,
        "evidence_tier": "flight-lot-irradiation",
        "capability_krad": 30.0,
        "see_data_available": True,
        "see_threshold_let": 60.0,
        "see_environment_let": 37.0,
    }
    spec.update(overrides)
    return spec


class SensitivityTriageTests(unittest.TestCase):
    def test_registered_family_is_sensitive_at_any_dose(self):
        result = radiation_sensitivity("optocoupler", 0.0)
        self.assertTrue(result["in_register"])
        self.assertTrue(result["sensitive"])

    def test_unregistered_family_below_the_threshold_is_not_sensitive(self):
        result = radiation_sensitivity("wirewound-resistor", 0.1)
        self.assertFalse(result["in_register"])
        self.assertFalse(result["sensitive"])

    def test_unregistered_family_above_the_threshold_is_sensitive(self):
        self.assertTrue(radiation_sensitivity("wirewound-resistor", 25.0)["sensitive"])

    def test_dose_exactly_on_the_threshold_is_sensitive(self):
        result = radiation_sensitivity("wirewound-resistor", 1.0, threshold_krad=1.0)
        self.assertTrue(result["dose_reaches_threshold"])
        self.assertTrue(result["sensitive"])

    def test_family_match_ignores_case_and_space(self):
        self.assertTrue(radiation_sensitivity("  SRAM-Memory ", 0.0)["in_register"])

    def test_negative_mission_dose_rejected(self):
        with self.assertRaises(ValueError):
            radiation_sensitivity("sram-memory", -1.0)

    def test_zero_threshold_rejected(self):
        with self.assertRaises(ValueError):
            radiation_sensitivity("sram-memory", 5.0, threshold_krad=0.0)


class EvidenceTierTests(unittest.TestCase):
    def test_flight_lot_evidence_carries_no_penalty(self):
        self.assertAlmostEqual(evidence_tier_penalty("flight-lot-irradiation"), 1.0, places=9)

    def test_similar_lot_evidence_carries_a_penalty(self):
        self.assertAlmostEqual(
            evidence_tier_penalty("similar-lot-irradiation"),
            EVIDENCE_TIER_PENALTY["similar-lot-irradiation"],
            places=9,
        )

    def test_declared_capability_carries_the_largest_penalty(self):
        self.assertGreater(
            evidence_tier_penalty("manufacturer-declared-capability"),
            evidence_tier_penalty("similar-lot-irradiation"),
        )

    def test_unknown_tier_rejected(self):
        with self.assertRaises(ValueError):
            evidence_tier_penalty("a-colleague-remembered-it-being-fine")

    def test_blank_tier_rejected(self):
        with self.assertRaises(ValueError):
            evidence_tier_penalty("   ")


class RequirementTests(unittest.TestCase):
    def test_requirement_is_the_dose_scaled_by_the_margin(self):
        result = required_capability_krad(10.0, 2.0, "flight-lot-irradiation")
        self.assertAlmostEqual(result["required_krad"], 20.0, places=9)

    def test_thinner_evidence_raises_the_requirement(self):
        flight = required_capability_krad(10.0, 2.0, "flight-lot-irradiation")
        declared = required_capability_krad(10.0, 2.0, "manufacturer-declared-capability")
        self.assertGreater(declared["required_krad"], flight["required_krad"])

    def test_similar_lot_requirement_sits_between_the_other_two(self):
        similar = required_capability_krad(10.0, 2.0, "similar-lot-irradiation")
        self.assertAlmostEqual(similar["required_krad"], 30.0, places=9)

    def test_default_margin_is_applied_when_none_is_declared(self):
        result = required_capability_krad(10.0)
        self.assertAlmostEqual(result["design_margin"], DEFAULT_RADIATION_DESIGN_MARGIN, places=9)

    def test_margin_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            required_capability_krad(10.0, 0.5, "flight-lot-irradiation")

    def test_non_numeric_dose_rejected(self):
        with self.assertRaises(ValueError):
            required_capability_krad("ten", 2.0, "flight-lot-irradiation")


class TotalDoseTests(unittest.TestCase):
    def test_capability_above_the_requirement_meets_it(self):
        self.assertTrue(total_dose_verdict(50.0, 20.0)["meets_requirement"])

    def test_capability_exactly_on_the_requirement_meets_it(self):
        result = total_dose_verdict(20.0, 20.0)
        self.assertAlmostEqual(result["shortfall_krad"], 0.0, places=9)
        self.assertTrue(result["meets_requirement"])

    def test_capability_below_the_requirement_falls_short(self):
        result = total_dose_verdict(15.0, 20.0)
        self.assertFalse(result["meets_requirement"])
        self.assertAlmostEqual(result["shortfall_krad"], 5.0, places=9)

    def test_negative_capability_rejected(self):
        with self.assertRaises(ValueError):
            total_dose_verdict(-1.0, 20.0)


class DestructiveSingleEventTests(unittest.TestCase):
    def test_family_outside_the_register_is_cleared_without_data(self):
        result = destructive_see_status("wirewound-resistor", False)
        self.assertFalse(result["susceptible"])
        self.assertTrue(result["cleared"])

    def test_susceptible_family_without_data_is_not_cleared(self):
        result = destructive_see_status("sram-memory", False)
        self.assertTrue(result["susceptible"])
        self.assertFalse(result["cleared"])

    def test_threshold_above_the_environment_clears(self):
        self.assertTrue(destructive_see_status("sram-memory", True, 60.0, 37.0)["cleared"])

    def test_threshold_exactly_on_the_environment_clears(self):
        result = destructive_see_status("sram-memory", True, 37.0, 37.0)
        self.assertAlmostEqual(result["margin_let"], 0.0, places=9)
        self.assertTrue(result["cleared"])

    def test_threshold_below_the_environment_does_not_clear(self):
        self.assertFalse(destructive_see_status("power-mosfet", True, 20.0, 37.0)["cleared"])

    def test_available_data_without_numbers_rejected(self):
        with self.assertRaises(ValueError):
            destructive_see_status("sram-memory", True)

    def test_negative_threshold_rejected(self):
        with self.assertRaises(ValueError):
            destructive_see_status("sram-memory", True, -1.0, 37.0)


class AssessmentTests(unittest.TestCase):
    def test_insensitive_part_owes_nothing(self):
        result = assess_class3_radiation_verification(
            _spec(technology_family="wirewound-resistor", mission_dose_krad=0.2)
        )
        self.assertEqual(result["verdict"], "not-radiation-sensitive")
        self.assertTrue(result["accepted"])

    def test_tested_lot_with_margin_is_verified(self):
        result = assess_class3_radiation_verification(_spec())
        self.assertEqual(result["verdict"], "verified")
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])

    def test_capability_exactly_on_the_requirement_is_verified(self):
        result = assess_class3_radiation_verification(_spec(capability_krad=20.0))
        self.assertAlmostEqual(result["requirement"]["required_krad"], 20.0, places=9)
        self.assertEqual(result["verdict"], "verified")

    def test_declared_capability_short_of_the_penalised_requirement_needs_a_lot_test(self):
        result = assess_class3_radiation_verification(
            _spec(evidence_tier="manufacturer-declared-capability", capability_krad=30.0)
        )
        self.assertEqual(result["verdict"], "lot-radiation-test-required")
        self.assertFalse(result["accepted"])

    def test_similar_lot_short_of_the_requirement_needs_a_lot_test(self):
        result = assess_class3_radiation_verification(
            _spec(evidence_tier="similar-lot-irradiation", capability_krad=25.0)
        )
        self.assertEqual(result["verdict"], "lot-radiation-test-required")

    def test_tested_flight_lot_falling_short_is_rejected(self):
        result = assess_class3_radiation_verification(_spec(capability_krad=5.0))
        self.assertEqual(result["verdict"], "rejected")

    def test_no_evidence_at_all_is_insufficient(self):
        result = assess_class3_radiation_verification(
            _spec(technology_family="linear-bipolar", evidence_tier="none", see_data_available=False)
        )
        self.assertEqual(result["verdict"], "evidence-insufficient")

    def test_destructive_single_event_gap_outranks_a_healthy_dose_margin(self):
        result = assess_class3_radiation_verification(
            _spec(capability_krad=500.0, see_data_available=False)
        )
        self.assertEqual(result["verdict"], "rejected")
        self.assertTrue(any("single-event" in item for item in result["findings"]))

    def test_destructive_single_event_shortfall_rejects(self):
        result = assess_class3_radiation_verification(
            _spec(see_threshold_let=10.0, see_environment_let=37.0)
        )
        self.assertEqual(result["verdict"], "rejected")

    def test_both_reasons_are_named_not_just_the_first(self):
        result = assess_class3_radiation_verification(
            _spec(capability_krad=1.0, see_threshold_let=10.0, see_environment_let=37.0)
        )
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["evidence_tier"]
        with self.assertRaises(ValueError):
            assess_class3_radiation_verification(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_class3_radiation_verification(["not", "a", "mapping"])

    def test_unknown_evidence_tier_rejected(self):
        with self.assertRaises(ValueError):
            assess_class3_radiation_verification(_spec(evidence_tier="vendor-said-so"))


if __name__ == "__main__":
    unittest.main()
