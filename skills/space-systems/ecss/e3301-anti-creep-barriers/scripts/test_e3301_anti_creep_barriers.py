"""Contract tests for the clause 4.7.3.3.3 anti-creep barrier logic."""

import math
import unittest

from e3301_anti_creep_barriers_logic import (
    ANGLE_TOLERANCE_DEG,
    DEFAULT_MIN_BAND_WIDTH_MM,
    DEFAULT_MIN_CONTACT_ANGLE_DEG,
    MARGIN_TOLERANCE,
    assess_anti_creep_barriers,
    contact_angle_deg,
    grade_barrier,
    grade_path,
    spreading_coefficient,
    validate_non_negative,
    validate_positive,
    wetting_margin_mn_per_m,
)

LUBRICANT = {
    "surface_tension_mn_per_m": 25.0,
    "temperature_c": (-20.0, 80.0),
}

BARRIER = {
    "name": "shaft-band",
    "critical_surface_energy_mn_per_m": 10.0,
    "interfacial_energy_mn_per_m": 2.0,
    "band_width_mm": 3.0,
    "continuous": True,
    "temperature_c": (-60.0, 150.0),
}

SECOND_BARRIER = {
    "name": "housing-band",
    "critical_surface_energy_mn_per_m": 11.0,
    "interfacial_energy_mn_per_m": 2.0,
    "band_width_mm": 4.0,
    "continuous": True,
    "temperature_c": (-60.0, 150.0),
}

PATHS = [
    {
        "name": "bearing-to-optics",
        "source": "bearing-reservoir",
        "destination": "optical-window",
        "sensitive": True,
        "barriers": ["shaft-band"],
    },
    {
        "name": "bearing-to-vent",
        "source": "bearing-reservoir",
        "destination": "vent-port",
        "sensitive": False,
        "barriers": [],
    },
    {
        "name": "gear-to-latch-face",
        "source": "gear-mesh",
        "destination": "un-lubricated-latch-face",
        "sensitive": True,
        "barriers": ["housing-band"],
    },
]


def _spec(**overrides):
    spec = {
        "lubricant": dict(LUBRICANT),
        "barriers": [dict(BARRIER), dict(SECOND_BARRIER)],
        "paths": [dict(path) for path in PATHS],
    }
    spec.update(overrides)
    return spec


class ValidationTests(unittest.TestCase):
    def test_positive_validator_returns_float(self):
        self.assertAlmostEqual(validate_positive("x", 7), 7.0)

    def test_positive_validator_rejects_zero(self):
        with self.assertRaises(ValueError):
            validate_positive("x", 0.0)

    def test_non_negative_validator_accepts_zero(self):
        self.assertAlmostEqual(validate_non_negative("x", 0.0), 0.0)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", True)


class SurfaceEnergyTests(unittest.TestCase):
    def test_spreading_coefficient_is_negative_for_a_sound_barrier(self):
        self.assertAlmostEqual(spreading_coefficient(10.0, 25.0, 2.0), -17.0, places=12)

    def test_spreading_coefficient_is_positive_when_the_oil_wets(self):
        self.assertGreater(spreading_coefficient(40.0, 25.0, 2.0), 0.0)

    def test_zero_surface_tension_rejected(self):
        with self.assertRaises(ValueError):
            spreading_coefficient(10.0, 0.0, 2.0)

    def test_contact_angle_matches_the_young_equation(self):
        angle = contact_angle_deg(10.0, 25.0, 2.0)
        self.assertAlmostEqual(angle, math.degrees(math.acos(8.0 / 25.0)), places=12)

    def test_equal_energies_give_a_right_angle(self):
        self.assertAlmostEqual(contact_angle_deg(2.0, 25.0, 2.0), 90.0, places=9)

    def test_lower_barrier_energy_raises_the_contact_angle(self):
        low = contact_angle_deg(8.0, 25.0, 2.0)
        high = contact_angle_deg(14.0, 25.0, 2.0)
        self.assertGreater(low, high)

    def test_complete_wetting_has_no_young_solution(self):
        with self.assertRaises(ValueError):
            contact_angle_deg(40.0, 25.0, 2.0)

    def test_wetting_margin_is_the_energy_difference(self):
        self.assertAlmostEqual(wetting_margin_mn_per_m(10.0, 25.0), 15.0, places=12)

    def test_negative_wetting_margin_when_the_barrier_is_too_energetic(self):
        self.assertLess(wetting_margin_mn_per_m(40.0, 25.0), 0.0)


class BarrierGradingTests(unittest.TestCase):
    def test_sound_barrier_passes(self):
        record = grade_barrier(BARRIER, LUBRICANT)
        self.assertTrue(record["sound"])
        self.assertEqual(record["findings"], [])

    def test_contact_angle_is_reported(self):
        record = grade_barrier(BARRIER, LUBRICANT)
        self.assertAlmostEqual(
            record["contact_angle_deg"], math.degrees(math.acos(8.0 / 25.0)), places=12
        )

    def test_wetted_barrier_is_reported_not_raised(self):
        barrier = dict(BARRIER)
        barrier["critical_surface_energy_mn_per_m"] = 40.0
        record = grade_barrier(barrier, LUBRICANT)
        self.assertFalse(record["sound"])
        self.assertTrue(any("wetted completely" in text for text in record["findings"]))

    def test_narrow_band_is_flagged(self):
        barrier = dict(BARRIER)
        barrier["band_width_mm"] = 0.5
        record = grade_barrier(barrier, LUBRICANT)
        self.assertFalse(record["sound"])
        self.assertTrue(any("band is" in text for text in record["findings"]))

    def test_band_exactly_on_the_minimum_passes(self):
        barrier = dict(BARRIER)
        barrier["band_width_mm"] = DEFAULT_MIN_BAND_WIDTH_MM
        self.assertTrue(grade_barrier(barrier, LUBRICANT)["sound"])

    def test_discontinuous_band_is_flagged(self):
        barrier = dict(BARRIER)
        barrier["continuous"] = False
        record = grade_barrier(barrier, LUBRICANT)
        self.assertFalse(record["sound"])
        self.assertTrue(any("not continuous" in text for text in record["findings"]))

    def test_barrier_below_its_hot_rating_is_flagged(self):
        barrier = dict(BARRIER)
        barrier["temperature_c"] = (-60.0, 60.0)
        record = grade_barrier(barrier, LUBRICANT)
        self.assertFalse(record["sound"])
        self.assertTrue(any("rated to 60 C hot" in text for text in record["findings"]))

    def test_barrier_rating_exactly_on_the_duty_passes(self):
        barrier = dict(BARRIER)
        barrier["temperature_c"] = (-20.0, 80.0)
        self.assertTrue(grade_barrier(barrier, LUBRICANT)["sound"])

    def test_contact_angle_exactly_on_the_minimum_passes(self):
        tension = LUBRICANT["surface_tension_mn_per_m"]
        cosine = math.cos(math.radians(DEFAULT_MIN_CONTACT_ANGLE_DEG))
        barrier = dict(BARRIER)
        barrier["interfacial_energy_mn_per_m"] = 0.0
        barrier["critical_surface_energy_mn_per_m"] = cosine * tension
        record = grade_barrier(barrier, LUBRICANT)
        self.assertAlmostEqual(
            record["contact_angle_deg"], DEFAULT_MIN_CONTACT_ANGLE_DEG, places=9
        )
        self.assertTrue(record["sound"])

    def test_shallow_contact_angle_is_flagged(self):
        barrier = dict(BARRIER)
        barrier["critical_surface_energy_mn_per_m"] = 22.0
        barrier["interfacial_energy_mn_per_m"] = 0.0
        record = grade_barrier(barrier, LUBRICANT)
        self.assertFalse(record["sound"])

    def test_non_boolean_continuity_rejected(self):
        barrier = dict(BARRIER)
        barrier["continuous"] = "yes"
        with self.assertRaises(ValueError):
            grade_barrier(barrier, LUBRICANT)

    def test_missing_barrier_key_rejected(self):
        barrier = dict(BARRIER)
        del barrier["band_width_mm"]
        with self.assertRaises(ValueError):
            grade_barrier(barrier, LUBRICANT)

    def test_missing_lubricant_key_rejected(self):
        lubricant = dict(LUBRICANT)
        del lubricant["temperature_c"]
        with self.assertRaises(ValueError):
            grade_barrier(BARRIER, lubricant)


class PathGradingTests(unittest.TestCase):
    def _graded(self):
        return {
            record["name"]: record
            for record in (
                grade_barrier(BARRIER, LUBRICANT),
                grade_barrier(SECOND_BARRIER, LUBRICANT),
            )
        }

    def test_barriered_sensitive_path_is_protected(self):
        self.assertTrue(grade_path(PATHS[0], self._graded())["protected"])

    def test_insensitive_path_needs_no_barrier(self):
        self.assertTrue(grade_path(PATHS[1], self._graded())["protected"])

    def test_bare_sensitive_path_is_flagged(self):
        path = dict(PATHS[0])
        path["barriers"] = []
        record = grade_path(path, self._graded())
        self.assertFalse(record["protected"])
        self.assertIn("no barrier", record["findings"][0])

    def test_path_covered_only_by_a_failed_barrier_is_flagged(self):
        broken = dict(BARRIER)
        broken["continuous"] = False
        graded = {"shaft-band": grade_barrier(broken, LUBRICANT)}
        record = grade_path(PATHS[0], graded)
        self.assertFalse(record["protected"])
        self.assertIn("did not pass", record["findings"][0])

    def test_line_of_sight_without_vapour_control_is_flagged(self):
        path = dict(PATHS[0])
        path["line_of_sight"] = True
        record = grade_path(path, self._graded())
        self.assertFalse(record["protected"])
        self.assertTrue(any("vapour" in text for text in record["findings"]))

    def test_declared_vapour_control_clears_the_line_of_sight_finding(self):
        path = dict(PATHS[0])
        path["line_of_sight"] = True
        path["vapour_control"] = "labyrinth-and-getter"
        self.assertTrue(grade_path(path, self._graded())["protected"])

    def test_unknown_barrier_name_rejected(self):
        path = dict(PATHS[0])
        path["barriers"] = ["no-such-band"]
        with self.assertRaises(ValueError):
            grade_path(path, self._graded())

    def test_non_boolean_sensitivity_rejected(self):
        path = dict(PATHS[0])
        path["sensitive"] = 1
        with self.assertRaises(ValueError):
            grade_path(path, self._graded())

    def test_missing_path_key_rejected(self):
        path = dict(PATHS[0])
        del path["destination"]
        with self.assertRaises(ValueError):
            grade_path(path, self._graded())


class AssessmentTests(unittest.TestCase):
    def test_sound_design_is_compliant(self):
        result = assess_anti_creep_barriers(_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["unprotected_paths"], ())

    def test_unprotected_path_is_named(self):
        spec = _spec()
        spec["paths"][2]["barriers"] = []
        result = assess_anti_creep_barriers(spec)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["unprotected_paths"], ("gear-to-latch-face",))

    def test_a_failed_barrier_takes_its_path_with_it(self):
        spec = _spec()
        spec["barriers"][0]["band_width_mm"] = 0.1
        result = assess_anti_creep_barriers(spec)
        self.assertFalse(result["compliant"])
        self.assertIn("bearing-to-optics", result["unprotected_paths"])

    def test_tighter_minimum_angle_can_fail_a_previously_sound_barrier(self):
        result = assess_anti_creep_barriers(_spec(min_contact_angle_deg=85.0))
        self.assertFalse(result["compliant"])

    def test_duplicate_barrier_name_rejected(self):
        spec = _spec()
        spec["barriers"].append(dict(BARRIER))
        with self.assertRaises(ValueError):
            assess_anti_creep_barriers(spec)

    def test_duplicate_path_name_rejected(self):
        spec = _spec()
        spec["paths"].append(dict(PATHS[0]))
        with self.assertRaises(ValueError):
            assess_anti_creep_barriers(spec)

    def test_empty_barrier_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_anti_creep_barriers(_spec(barriers=[]))

    def test_empty_path_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_anti_creep_barriers(_spec(paths=[]))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["lubricant"]
        with self.assertRaises(ValueError):
            assess_anti_creep_barriers(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_anti_creep_barriers(["lubricant"])

    def test_tolerances_are_representation_sized(self):
        self.assertLess(MARGIN_TOLERANCE, 1e-6)
        self.assertLess(ANGLE_TOLERANCE_DEG, 1e-6)


if __name__ == "__main__":
    unittest.main()
