#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C clause 4.2 gravity
environment model selection and magnitude/gradient logic.

Exercises scripts/e1004_gravity_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the gravity model is
selected from the orbit regime; MEO/GEO/HEO always require third-body
perturbation terms in addition to the geopotential term; a mission
duration beyond the tide-accumulation threshold also requires the
solid-Earth-tide term (and, for LEO, the third-body term); a case's
perturbation coverage is adequate only when its included terms are a
superset of what is required; a case's altitude must fall inside the
selected model's validity range; gravitational acceleration magnitude
and gravity gradient magnitude are computed from the point-mass
relations and decrease with increasing radius; the assessment record
covers every case with no duplicates and is reported all-compliant
only when every case is compliant.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_gravity_logic as gl  # noqa: E402


class SelectGravityModelTest(unittest.TestCase):
    def test_leo_model(self):
        self.assertEqual(
            gl.select_gravity_model("leo"), gl.MODEL_BY_ORBIT_REGIME["leo"]
        )

    def test_geo_model(self):
        self.assertEqual(
            gl.select_gravity_model("geo"), gl.MODEL_BY_ORBIT_REGIME["geo"]
        )

    def test_unknown_regime_raises(self):
        with self.assertRaises(ValueError):
            gl.select_gravity_model("cislunar")


class RequiredPerturbationTermsTest(unittest.TestCase):
    def test_short_leo_requires_only_geopotential(self):
        self.assertEqual(
            gl.required_perturbation_terms("leo", 30.0),
            frozenset({"earth_geopotential_high_degree"}),
        )

    def test_long_leo_requires_third_body_and_tide(self):
        self.assertEqual(
            gl.required_perturbation_terms("leo", 400.0),
            frozenset(
                {
                    "earth_geopotential_high_degree",
                    "third_body",
                    "solid_earth_tide",
                }
            ),
        )

    def test_short_geo_requires_third_body_but_not_tide(self):
        self.assertEqual(
            gl.required_perturbation_terms("geo", 90.0),
            frozenset({"earth_geopotential_low_degree", "third_body"}),
        )

    def test_long_geo_also_requires_tide(self):
        self.assertEqual(
            gl.required_perturbation_terms("geo", 1000.0),
            frozenset(
                {
                    "earth_geopotential_low_degree",
                    "third_body",
                    "solid_earth_tide",
                }
            ),
        )

    def test_unknown_regime_raises(self):
        with self.assertRaises(ValueError):
            gl.required_perturbation_terms("cislunar", 30.0)

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            gl.required_perturbation_terms("leo", -1.0)


class PerturbationTermsAdequateTest(unittest.TestCase):
    def test_exact_coverage_is_adequate(self):
        self.assertTrue(
            gl.perturbation_terms_adequate(
                "meo", 30.0, {"earth_geopotential_low_degree", "third_body"}
            )
        )

    def test_missing_term_is_not_adequate(self):
        self.assertFalse(
            gl.perturbation_terms_adequate(
                "meo", 30.0, {"earth_geopotential_low_degree"}
            )
        )

    def test_extra_terms_still_adequate(self):
        self.assertTrue(
            gl.perturbation_terms_adequate(
                "leo",
                30.0,
                {"earth_geopotential_high_degree", "third_body", "solid_earth_tide"},
            )
        )


class ValidityAltitudeRangeTest(unittest.TestCase):
    def test_leo_range(self):
        self.assertEqual(gl.validity_altitude_range("leo"), (160000.0, 2000000.0))

    def test_unknown_regime_raises(self):
        with self.assertRaises(ValueError):
            gl.validity_altitude_range("cislunar")


class AltitudeInValidityRangeTest(unittest.TestCase):
    def test_inside_range(self):
        self.assertTrue(gl.altitude_in_validity_range("leo", 500000.0))

    def test_outside_range(self):
        self.assertFalse(gl.altitude_in_validity_range("leo", 36000000.0))

    def test_boundary_inclusive(self):
        self.assertTrue(gl.altitude_in_validity_range("leo", 160000.0))
        self.assertTrue(gl.altitude_in_validity_range("leo", 2000000.0))


class OrbitalRadiusMTest(unittest.TestCase):
    def test_adds_earth_radius(self):
        self.assertEqual(
            gl.orbital_radius_m(500000.0), gl.EARTH_RADIUS_M + 500000.0
        )

    def test_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            gl.orbital_radius_m(-1.0)


class GravityMagnitudeTest(unittest.TestCase):
    def test_matches_point_mass_relation(self):
        radius = gl.EARTH_RADIUS_M
        expected = gl.EARTH_GM_M3_S2 / (radius ** 2)
        self.assertAlmostEqual(gl.gravity_magnitude(radius), expected)

    def test_decreases_with_radius(self):
        low = gl.gravity_magnitude(gl.EARTH_RADIUS_M + 500000.0)
        high = gl.gravity_magnitude(gl.EARTH_RADIUS_M + 35786000.0)
        self.assertGreater(low, high)

    def test_non_positive_radius_raises(self):
        with self.assertRaises(ValueError):
            gl.gravity_magnitude(0.0)
        with self.assertRaises(ValueError):
            gl.gravity_magnitude(-10.0)


class GravityGradientMagnitudeTest(unittest.TestCase):
    def test_matches_point_mass_relation(self):
        radius = gl.EARTH_RADIUS_M
        expected = 2.0 * gl.EARTH_GM_M3_S2 / (radius ** 3)
        self.assertAlmostEqual(gl.gravity_gradient_magnitude(radius), expected)

    def test_decreases_with_radius(self):
        low = gl.gravity_gradient_magnitude(gl.EARTH_RADIUS_M + 500000.0)
        high = gl.gravity_gradient_magnitude(gl.EARTH_RADIUS_M + 35786000.0)
        self.assertGreater(low, high)

    def test_non_positive_radius_raises(self):
        with self.assertRaises(ValueError):
            gl.gravity_gradient_magnitude(0.0)


class AssessGravityCaseTest(unittest.TestCase):
    def test_compliant_leo_case(self):
        case = {
            "id": "GRAV-001",
            "orbit_regime": "leo",
            "altitude_m": 500000.0,
            "mission_duration_days": 30.0,
            "included_terms": {"earth_geopotential_high_degree"},
        }
        result = gl.assess_gravity_case(case)
        self.assertEqual(result["model"], gl.MODEL_BY_ORBIT_REGIME["leo"])
        self.assertTrue(result["terms_adequate"])
        self.assertTrue(result["altitude_valid"])
        self.assertTrue(result["compliant"])
        self.assertGreater(result["gravity_magnitude_m_s2"], 0.0)
        self.assertGreater(result["gravity_gradient_1_s2"], 0.0)

    def test_noncompliant_geo_case_missing_third_body(self):
        case = {
            "id": "GRAV-002",
            "orbit_regime": "geo",
            "altitude_m": 35786000.0,
            "mission_duration_days": 90.0,
            "included_terms": {"earth_geopotential_low_degree"},
        }
        result = gl.assess_gravity_case(case)
        self.assertFalse(result["terms_adequate"])
        self.assertFalse(result["compliant"])

    def test_noncompliant_case_wrong_altitude_for_regime(self):
        case = {
            "id": "GRAV-003",
            "orbit_regime": "leo",
            "altitude_m": 35786000.0,
            "mission_duration_days": 30.0,
            "included_terms": {"earth_geopotential_high_degree"},
        }
        result = gl.assess_gravity_case(case)
        self.assertFalse(result["altitude_valid"])
        self.assertFalse(result["compliant"])

    def test_compliant_long_duration_leo_case(self):
        case = {
            "id": "GRAV-004",
            "orbit_regime": "leo",
            "altitude_m": 700000.0,
            "mission_duration_days": 3650.0,
            "included_terms": {
                "earth_geopotential_high_degree",
                "third_body",
                "solid_earth_tide",
            },
        }
        result = gl.assess_gravity_case(case)
        self.assertTrue(result["compliant"])

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            gl.assess_gravity_case(
                {
                    "orbit_regime": "leo",
                    "altitude_m": 500000.0,
                    "mission_duration_days": 30.0,
                    "included_terms": {"earth_geopotential_high_degree"},
                }
            )

    def test_unknown_orbit_regime_raises(self):
        with self.assertRaises(ValueError):
            gl.assess_gravity_case(
                {
                    "id": "GRAV-005",
                    "orbit_regime": "cislunar",
                    "altitude_m": 500000.0,
                    "mission_duration_days": 30.0,
                    "included_terms": set(),
                }
            )


class BuildGravityAssessmentTest(unittest.TestCase):
    CASES = [
        {
            "id": "GRAV-001",
            "orbit_regime": "leo",
            "altitude_m": 500000.0,
            "mission_duration_days": 30.0,
            "included_terms": {"earth_geopotential_high_degree"},
        },
        {
            "id": "GRAV-002",
            "orbit_regime": "geo",
            "altitude_m": 35786000.0,
            "mission_duration_days": 90.0,
            "included_terms": {"earth_geopotential_low_degree"},
        },
    ]

    def test_record_order_and_status(self):
        record = gl.build_gravity_assessment(self.CASES)
        self.assertEqual(record[0]["id"], "GRAV-001")
        self.assertTrue(record[0]["compliant"])
        self.assertEqual(record[1]["id"], "GRAV-002")
        self.assertFalse(record[1]["compliant"])

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            gl.build_gravity_assessment(self.CASES + [self.CASES[0]])

    def test_does_not_mutate_input(self):
        before = [dict(c) for c in self.CASES]
        gl.build_gravity_assessment(self.CASES)
        self.assertEqual(self.CASES, before)


class RecordSummaryTest(unittest.TestCase):
    def test_noncompliant_items(self):
        record = gl.build_gravity_assessment(BuildGravityAssessmentTest.CASES)
        self.assertEqual(gl.noncompliant_items(record), ["GRAV-002"])

    def test_all_compliant_true_when_all_pass(self):
        record = gl.build_gravity_assessment(
            [BuildGravityAssessmentTest.CASES[0]]
        )
        self.assertTrue(gl.all_compliant(record))

    def test_all_compliant_false_when_any_fail(self):
        record = gl.build_gravity_assessment(BuildGravityAssessmentTest.CASES)
        self.assertFalse(gl.all_compliant(record))


if __name__ == "__main__":
    unittest.main(verbosity=2)
