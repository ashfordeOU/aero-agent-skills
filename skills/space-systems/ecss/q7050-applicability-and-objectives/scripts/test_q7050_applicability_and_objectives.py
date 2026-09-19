"""Contract tests for the particle-monitoring applicability and objectives logic."""

import unittest

from q7050_applicability_and_objectives_logic import (
    DE_MINIMIS_AREA_M2,
    FALLOUT_EXPOSURE_THRESHOLD_H,
    MODE_OBJECTIVES,
    MONITORING_MODES,
    airborne_required,
    assess_applicability,
    fallout_required,
    objectives_for,
    tape_lift_required,
    validate_area_m2,
    validate_containment,
    validate_exposure_hours,
    validate_sensitivity,
    validate_zone_type,
)


class ValidationTests(unittest.TestCase):
    def test_sensitivity_is_normalised(self):
        self.assertEqual(validate_sensitivity(" Optical "), "optical")

    def test_unknown_sensitivity_rejected(self):
        with self.assertRaises(ValueError):
            validate_sensitivity("delicate")

    def test_non_string_sensitivity_rejected(self):
        with self.assertRaises(ValueError):
            validate_sensitivity(3)

    def test_zone_type_is_normalised(self):
        self.assertEqual(validate_zone_type("CLEANROOM"), "cleanroom")

    def test_unknown_zone_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_zone_type("lab")

    def test_containment_is_normalised(self):
        self.assertEqual(validate_containment("Bagged"), "bagged")

    def test_unknown_containment_rejected(self):
        with self.assertRaises(ValueError):
            validate_containment("wrapped")

    def test_negative_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_area_m2(-0.5)

    def test_boolean_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_area_m2(True)

    def test_non_finite_exposure_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure_hours(float("inf"))

    def test_negative_exposure_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure_hours(-1.0)

    def test_zero_area_is_accepted_as_a_real_usage(self):
        self.assertAlmostEqual(validate_area_m2(0.0), 0.0)


class AirborneObligationTests(unittest.TestCase):
    def test_cleanroom_always_owes_air_counting(self):
        self.assertTrue(airborne_required("cleanroom", False))

    def test_controlled_area_owes_it_only_with_sensitive_hardware(self):
        self.assertFalse(airborne_required("controlled-area", False))
        self.assertTrue(airborne_required("controlled-area", True))

    def test_uncontrolled_area_owes_nothing(self):
        self.assertFalse(airborne_required("uncontrolled-area", True))

    def test_non_boolean_presence_flag_rejected(self):
        with self.assertRaises(ValueError):
            airborne_required("cleanroom", "yes")


class FalloutObligationTests(unittest.TestCase):
    def test_bagged_hardware_collects_no_fallout(self):
        self.assertFalse(fallout_required("bagged", "optical", 100.0, 1.0))

    def test_sealed_enclosure_collects_no_fallout(self):
        self.assertFalse(fallout_required("sealed-enclosure", "precision", 100.0, 1.0))

    def test_optical_surface_ignores_the_de_minimis_area(self):
        self.assertTrue(fallout_required("open", "optical", 0.5, DE_MINIMIS_AREA_M2 / 10.0))

    def test_general_surface_below_de_minimis_is_covered_by_zone_plates(self):
        self.assertFalse(fallout_required("open", "general", 10.0, DE_MINIMIS_AREA_M2 / 10.0))

    def test_general_surface_below_the_exposure_threshold_is_exempt(self):
        self.assertFalse(
            fallout_required("open", "general", FALLOUT_EXPOSURE_THRESHOLD_H / 2.0, 1.0)
        )

    def test_general_surface_at_the_exposure_threshold_is_owed(self):
        self.assertTrue(fallout_required("open", "general", FALLOUT_EXPOSURE_THRESHOLD_H, 1.0))

    def test_precision_surface_is_owed_regardless_of_short_exposure(self):
        self.assertTrue(fallout_required("open", "precision", 0.1, 1.0))

    def test_insensitive_surface_is_never_owed(self):
        self.assertFalse(fallout_required("open", "insensitive", 500.0, 50.0))

    def test_zero_exposure_collects_nothing(self):
        self.assertFalse(fallout_required("open", "optical", 0.0, 1.0))


class TapeLiftObligationTests(unittest.TestCase):
    def test_stated_level_on_an_accessible_precision_surface_is_owed(self):
        self.assertTrue(tape_lift_required(True, True, "precision"))

    def test_no_stated_level_means_no_lift(self):
        self.assertFalse(tape_lift_required(False, True, "precision"))

    def test_inaccessible_surface_cannot_be_lifted(self):
        self.assertFalse(tape_lift_required(True, False, "general"))

    def test_bare_optic_is_sampled_through_a_coupon_instead(self):
        self.assertFalse(tape_lift_required(True, True, "optical"))

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            tape_lift_required("yes", True, "general")


class ObjectiveTests(unittest.TestCase):
    def test_every_mode_carries_an_objective(self):
        self.assertEqual(set(MODE_OBJECTIVES), set(MONITORING_MODES))

    def test_objectives_are_returned_in_canonical_order(self):
        result = objectives_for(["tape-lift", "airborne-count"])
        self.assertEqual(list(result), ["airborne-count", "tape-lift"])

    def test_duplicate_modes_collapse(self):
        result = objectives_for(["tape-lift", "tape-lift"])
        self.assertEqual(len(result), 1)

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            objectives_for(["swab"])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            objectives_for("tape-lift")


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "sensitivity": "precision",
            "zone_type": "cleanroom",
            "containment": "open",
            "exposed_area_m2": 0.8,
            "exposure_hours": 12.0,
            "cleanliness_level_specified": True,
            "accessible": True,
        }
        spec.update(overrides)
        return spec

    def test_open_precision_hardware_owes_all_three_modes(self):
        result = assess_applicability(self._spec())
        self.assertEqual(result["modes"], list(MONITORING_MODES))
        self.assertTrue(result["monitoring_required"])

    def test_sealed_unit_in_a_cleanroom_owes_air_counting_only(self):
        result = assess_applicability(
            self._spec(containment="sealed-enclosure", cleanliness_level_specified=False)
        )
        self.assertEqual(result["modes"], ["airborne-count"])

    def test_optic_with_a_stated_level_is_steered_to_a_coupon(self):
        result = assess_applicability(self._spec(sensitivity="optical"))
        self.assertNotIn("tape-lift", result["modes"])
        self.assertTrue(any("witness coupon" in f for f in result["findings"]))

    def test_open_sensitive_hardware_outside_a_controlled_zone_is_flagged(self):
        result = assess_applicability(self._spec(zone_type="uncontrolled-area"))
        self.assertTrue(any("uncontrolled area" in f for f in result["findings"]))

    def test_a_usage_owing_nothing_records_a_waiver_finding(self):
        result = assess_applicability(
            self._spec(
                sensitivity="insensitive",
                zone_type="uncontrolled-area",
                containment="bagged",
                cleanliness_level_specified=False,
            )
        )
        self.assertFalse(result["monitoring_required"])
        self.assertEqual(result["modes"], [])
        self.assertTrue(any("waiver" in f for f in result["findings"]))

    def test_rationale_is_reported_per_mode(self):
        result = assess_applicability(self._spec())
        self.assertEqual(len(result["rationale"]), len(result["modes"]))

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["zone_type"]
        with self.assertRaises(ValueError):
            assess_applicability(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_applicability(["cleanroom"])

    def test_controlled_area_with_open_precision_hardware_gains_air_counting(self):
        result = assess_applicability(self._spec(zone_type="controlled-area"))
        self.assertIn("airborne-count", result["modes"])

    def test_objectives_match_the_modes_returned(self):
        result = assess_applicability(self._spec())
        self.assertEqual(list(result["objectives"]), result["modes"])


if __name__ == "__main__":
    unittest.main()
