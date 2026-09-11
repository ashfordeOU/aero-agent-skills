"""
test_e1009_planet_coords.py

Gate-3 contract tests for e1009_planet_coords_logic.py.
Run: python3 test_e1009_planet_coords.py
Offline; deterministic; stdlib unittest only.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1009_planet_coords_logic import (
    angular_separation_deg,
    compute_body_frame,
    list_bodies,
    pole_unit_vector,
    validate_pole_range,
)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestInputValidation(unittest.TestCase):
    def test_unknown_body_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_body_frame("pluto", 0.0)

    def test_non_string_body_raises_type_error(self):
        with self.assertRaises(TypeError):
            compute_body_frame(42, 0.0)

    def test_non_numeric_epoch_raises_type_error(self):
        with self.assertRaises(TypeError):
            compute_body_frame("earth", "now")

    def test_epoch_too_large_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_body_frame("earth", 1e8)

    def test_epoch_too_negative_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_body_frame("earth", -1e8)

    def test_body_lookup_is_case_insensitive(self):
        r = compute_body_frame("EARTH", 0.0)
        self.assertEqual(r.body, "earth")

    def test_body_lookup_strips_whitespace(self):
        r = compute_body_frame("  mars  ", 0.0)
        self.assertEqual(r.body, "mars")


# ---------------------------------------------------------------------------
# Earth frame at J2000
# ---------------------------------------------------------------------------

class TestEarthAtJ2000(unittest.TestCase):
    def setUp(self):
        self.r = compute_body_frame("earth", 0.0)

    def test_pole_ra_at_j2000(self):
        self.assertAlmostEqual(self.r.pole.alpha_deg, 0.00, places=3)

    def test_pole_dec_at_j2000(self):
        self.assertAlmostEqual(self.r.pole.delta_deg, 90.00, places=3)

    def test_prime_meridian_W0(self):
        self.assertAlmostEqual(self.r.prime_meridian.W_deg, 190.147, places=2)

    def test_T_is_zero_at_j2000(self):
        self.assertAlmostEqual(self.r.T, 0.0, places=12)

    def test_ra_rad_consistent_with_degrees(self):
        self.assertAlmostEqual(
            self.r.pole_ra_rad, math.radians(self.r.pole.alpha_deg), places=12
        )

    def test_dec_rad_consistent_with_degrees(self):
        self.assertAlmostEqual(
            self.r.pole_dec_rad, math.radians(self.r.pole.delta_deg), places=12
        )

    def test_W_rad_consistent_with_degrees(self):
        self.assertAlmostEqual(
            self.r.W_rad, math.radians(self.r.prime_meridian.W_deg), places=12
        )

    def test_no_range_findings(self):
        self.assertEqual(validate_pole_range(self.r), [])


# ---------------------------------------------------------------------------
# Mars frame at J2000
# ---------------------------------------------------------------------------

class TestMarsAtJ2000(unittest.TestCase):
    def setUp(self):
        self.r = compute_body_frame("mars", 0.0)

    def test_pole_ra(self):
        self.assertAlmostEqual(self.r.pole.alpha_deg, 317.68143, places=4)

    def test_pole_dec(self):
        self.assertAlmostEqual(self.r.pole.delta_deg, 52.88650, places=4)

    def test_prime_meridian_W0(self):
        self.assertAlmostEqual(self.r.prime_meridian.W_deg, 176.630, places=2)

    def test_no_range_findings(self):
        self.assertEqual(validate_pole_range(self.r), [])


# ---------------------------------------------------------------------------
# Venus — retrograde rotator (negative W1)
# ---------------------------------------------------------------------------

class TestVenusRetrograde(unittest.TestCase):
    def test_prime_meridian_decreases_over_time(self):
        r0 = compute_body_frame("venus", 0.0)
        r1 = compute_body_frame("venus", 100.0)
        # W is reduced mod 360, so compare total advance via W1
        # W1 for Venus is negative; after 100 days the raw angle is smaller
        from e1009_planet_coords_logic import _BODY_PARAMS
        _, _, _, _, W0, W1 = _BODY_PARAMS["venus"]
        expected_W = (W0 + W1 * 100.0) % 360.0
        self.assertAlmostEqual(r1.prime_meridian.W_deg, expected_W, places=6)

    def test_no_range_findings(self):
        r = compute_body_frame("venus", 0.0)
        self.assertEqual(validate_pole_range(r), [])


# ---------------------------------------------------------------------------
# Prime-meridian wrapping across all bodies and epochs
# ---------------------------------------------------------------------------

class TestPrimeMeridianWrapping(unittest.TestCase):
    def test_W_stays_in_0_to_360_for_all_bodies_and_epochs(self):
        for body in list_bodies():
            for d in (1.0, 365.0, 3650.0, 36500.0, -365.0, -3650.0):
                r = compute_body_frame(body, d)
                self.assertGreaterEqual(
                    r.prime_meridian.W_deg, 0.0,
                    msg=f"body={body}, d={d}: W={r.prime_meridian.W_deg}"
                )
                self.assertLess(
                    r.prime_meridian.W_deg, 360.0,
                    msg=f"body={body}, d={d}: W={r.prime_meridian.W_deg}"
                )


# ---------------------------------------------------------------------------
# Pole unit vector
# ---------------------------------------------------------------------------

class TestPoleUnitVector(unittest.TestCase):
    def test_earth_pole_points_near_north_icrf(self):
        r = compute_body_frame("earth", 0.0)
        v = pole_unit_vector(r)
        # Earth pole dec≈90° → z component ≈ 1
        self.assertAlmostEqual(v[2], 1.0, places=3)

    def test_unit_length_for_all_bodies(self):
        for body in list_bodies():
            r = compute_body_frame(body, 0.0)
            v = pole_unit_vector(r)
            length = math.sqrt(sum(x**2 for x in v))
            self.assertAlmostEqual(
                length, 1.0, places=10, msg=f"body={body}"
            )

    def test_pole_vector_z_matches_sin_dec(self):
        r = compute_body_frame("mars", 0.0)
        v = pole_unit_vector(r)
        self.assertAlmostEqual(v[2], math.sin(r.pole_dec_rad), places=12)


# ---------------------------------------------------------------------------
# Angular separation
# ---------------------------------------------------------------------------

class TestAngularSeparation(unittest.TestCase):
    def test_identical_vectors_yield_zero(self):
        v = (1.0, 0.0, 0.0)
        self.assertAlmostEqual(angular_separation_deg(v, v), 0.0, places=10)

    def test_orthogonal_vectors_yield_90(self):
        self.assertAlmostEqual(
            angular_separation_deg((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
            90.0,
            places=10,
        )

    def test_opposite_vectors_yield_180(self):
        self.assertAlmostEqual(
            angular_separation_deg((0.0, 0.0, 1.0), (0.0, 0.0, -1.0)),
            180.0,
            places=10,
        )

    def test_known_angle_45_degrees(self):
        c = math.cos(math.radians(45))
        s = math.sin(math.radians(45))
        self.assertAlmostEqual(
            angular_separation_deg((1.0, 0.0, 0.0), (c, s, 0.0)),
            45.0,
            places=10,
        )


# ---------------------------------------------------------------------------
# list_bodies utility
# ---------------------------------------------------------------------------

class TestListBodies(unittest.TestCase):
    def test_known_bodies_present(self):
        bodies = list_bodies()
        for name in ("earth", "mars", "moon", "venus", "jupiter", "saturn", "mercury"):
            self.assertIn(name, bodies)

    def test_result_is_sorted(self):
        bodies = list_bodies()
        self.assertEqual(bodies, sorted(bodies))

    def test_returns_list(self):
        self.assertIsInstance(list_bodies(), list)


# ---------------------------------------------------------------------------
# Time parameterisation
# ---------------------------------------------------------------------------

class TestTimeParameterisation(unittest.TestCase):
    def test_T_is_one_century_after_36525_days(self):
        r = compute_body_frame("earth", 36525.0)
        self.assertAlmostEqual(r.T, 1.0, places=10)

    def test_T_is_negative_before_j2000(self):
        r = compute_body_frame("earth", -36525.0)
        self.assertAlmostEqual(r.T, -1.0, places=10)

    def test_epoch_stored_on_result(self):
        r = compute_body_frame("moon", 1000.0)
        self.assertEqual(r.epoch_d, 1000.0)


if __name__ == "__main__":
    unittest.main()
