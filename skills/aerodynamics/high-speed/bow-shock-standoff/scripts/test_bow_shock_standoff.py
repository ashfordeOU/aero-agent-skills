"""Contract test for the bow-shock-standoff leaf (wave-39).

Exercises the SKILL.md workflow end to end: step 1 fixes the flight
point and the nose geometry (Mach above 1, positive radius, sphere or
cylinder body), step 2 runs the ratio-evaluation step on the stagnation
streamline with the Billig-form correlation, step 3 converts the ratio
to the standoff distance with the linear radius scaling, step 4 checks
the trend flags, and step 5 respects the validity floor near Mach 1.
The fact anchors (sphere and cylinder ratios at Mach 4 and Mach 8, nose
radius 0.5 m) are the module outputs, bounded by the spec anchors within
1e-4. Deterministic, offline, stdlib unittest.
"""

import unittest

from bow_shock_standoff_logic import (
    SPHERE_COEF,
    CYL_COEF,
    standoff_ratio,
    standoff_distance,
    standoff_report,
)

TOL = 1e-4


class StandoffRatioAnchors(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, the ratio-evaluation step."""

    def test_sphere_ratio_mach8_spec_anchor(self):
        """Sphere ratio at Mach 8 falls inside the spec anchor 0.15043
        within 1e-4 (Billig-form correlation for the sphere nose, the
        step 2 ratio-evaluation output)."""
        self.assertAlmostEqual(standoff_ratio(8.0), 0.15043, delta=TOL)
        self.assertAlmostEqual(
            standoff_ratio(8.0), 0.1504257535038012, places=6
        )

    def test_sphere_ratio_mach4_spec_anchor(self):
        """Sphere ratio at Mach 4 falls inside the spec anchor 0.17510
        within 1e-4, matching the module output 0.1750977921724338."""
        self.assertAlmostEqual(standoff_ratio(4.0), 0.17510, delta=TOL)
        self.assertAlmostEqual(
            standoff_ratio(4.0), 0.1750977921724338, places=6
        )

    def test_cylinder_ratio_mach8_spec_anchor(self):
        """Cylinder ratio at Mach 8 falls inside the spec anchor 0.41522
        within 1e-4."""
        self.assertAlmostEqual(
            standoff_ratio(8.0, "cylinder"), 0.41522, delta=TOL
        )

    def test_cylinder_ratio_mach4_spec_anchor(self):
        """Cylinder ratio at Mach 4 falls inside the spec anchor 0.51682
        within 1e-4."""
        self.assertAlmostEqual(
            standoff_ratio(4.0, "cylinder"), 0.51682, delta=TOL
        )

    def test_sphere_ratio_mach4_module_output(self):
        """Sphere ratio at Mach 4 matches the module output
        0.1750977921724338."""
        self.assertAlmostEqual(
            standoff_ratio(4.0), 0.1750977921724338, places=9
        )

    def test_cylinder_ratio_mach8_module_output(self):
        """Cylinder ratio at Mach 8 matches the module output
        0.41521901145222184."""
        self.assertAlmostEqual(
            standoff_ratio(8.0, "cylinder"),
            0.41521901145222184,
            places=9,
        )

    def test_cylinder_ratio_mach4_module_output(self):
        """Cylinder ratio at Mach 4 matches the module output
        0.5168291571262306."""
        self.assertAlmostEqual(
            standoff_ratio(4.0, "cylinder"),
            0.5168291571262306,
            places=9,
        )

    def test_default_body_is_sphere(self):
        """The default body is the sphere: the plain call equals the
        explicit sphere call at Mach 8."""
        self.assertEqual(standoff_ratio(8.0), standoff_ratio(8.0, "sphere"))


class StandoffDistanceConversion(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, the distance-conversion step."""

    def test_sphere_distance_mach8_half_meter(self):
        """Standoff distance at sphere Mach 8 with nose radius 0.5 m is
        the module output 0.0752128767519006 m, inside the spec anchor
        0.0752 m within 1e-4."""
        self.assertAlmostEqual(
            standoff_distance(8.0, 0.5), 0.0752128767519006, places=9
        )
        self.assertAlmostEqual(standoff_distance(8.0, 0.5), 0.0752, delta=TOL)

    def test_cylinder_distance_mach8_half_meter(self):
        """Cylinder standoff distance at Mach 8 with nose radius 0.5 m
        matches the module output 0.20760950572611092 m."""
        self.assertAlmostEqual(
            standoff_distance(8.0, 0.5, "cylinder"),
            0.20760950572611092,
            places=9,
        )

    def test_distance_linear_scaling_identity(self):
        """Step 3 linear scaling: doubling the nose radius doubles the
        standoff distance for the sphere."""
        self.assertAlmostEqual(
            standoff_distance(8.0, 1.0),
            2.0 * standoff_distance(8.0, 0.5),
            places=12,
        )

    def test_distance_quarter_radius_scales(self):
        """A quarter radius gives a quarter standoff distance at fixed
        Mach for the cylinder body."""
        self.assertAlmostEqual(
            standoff_distance(8.0, 0.25, "cylinder"),
            0.25 * standoff_distance(8.0, 1.0, "cylinder"),
            places=12,
        )

    def test_distance_ratio_radius_round_trip(self):
        """Round-trip identity: distance over radius recovers the
        step 2 ratio for both bodies at Mach 8."""
        for body in ("sphere", "cylinder"):
            d = standoff_distance(8.0, 0.5, body)
            self.assertAlmostEqual(d / 0.5, standoff_ratio(8.0, body),
                                   places=12)


class TrendChecks(unittest.TestCase):
    """Step 4 of the SKILL.md workflow, the trend-check step."""

    def test_ratio_monotone_decreasing_sphere(self):
        """The sphere ratio is monotone decreasing in Mach: the ratio at
        Mach 6 sits below the ratio at Mach 4."""
        self.assertLess(standoff_ratio(6.0), standoff_ratio(4.0))

    def test_ratio_monotone_decreasing_cylinder(self):
        """The cylinder ratio is monotone decreasing in Mach: the ratio
        at Mach 6 sits below the ratio at Mach 4."""
        self.assertLess(
            standoff_ratio(6.0, "cylinder"), standoff_ratio(4.0, "cylinder")
        )

    def test_ratio_drops_from_mach4_to_mach8(self):
        """Both body ratios fall from Mach 4 to Mach 8, so the standoff
        shrinks as Mach rises."""
        for body in ("sphere", "cylinder"):
            self.assertLess(standoff_ratio(8.0, body),
                            standoff_ratio(4.0, body))

    def test_cylinder_exceeds_sphere_at_mach4(self):
        """The cylinder ratio exceeds the sphere ratio at Mach 4,
        matching the 0.51682 over 0.17510 worked example."""
        self.assertGreater(
            standoff_ratio(4.0, "cylinder"), standoff_ratio(4.0)
        )

    def test_cylinder_exceeds_sphere_at_mach8(self):
        """The cylinder ratio exceeds the sphere ratio at Mach 8,
        matching the 0.41522 over 0.15043 worked example."""
        self.assertGreater(
            standoff_ratio(8.0, "cylinder"), standoff_ratio(8.0)
        )

    def test_report_keys_exact(self):
        """The step 4 report dict carries exactly the keys ratio,
        distance, sphere_cylinder_order and decreasing_with_mach."""
        rep = standoff_report(4.0, 0.5)
        self.assertEqual(
            sorted(rep.keys()),
            ["decreasing_with_mach", "distance", "ratio",
             "sphere_cylinder_order"],
        )

    def test_report_sphere_mach4_values(self):
        """Sphere report at Mach 4 and nose radius 0.5 m carries the
        module ratio, the scaled distance and both True trend flags."""
        rep = standoff_report(4.0, 0.5)
        self.assertAlmostEqual(rep["ratio"], 0.1750977921724338, places=9)
        self.assertAlmostEqual(rep["distance"], 0.0875488960862169,
                               places=9)
        self.assertTrue(rep["sphere_cylinder_order"])
        self.assertTrue(rep["decreasing_with_mach"])

    def test_report_cylinder_mach4_values(self):
        """Cylinder report at Mach 4 and nose radius 0.5 m carries the
        module ratio 0.51683, the scaled distance 0.25841 m and both
        True trend flags."""
        rep = standoff_report(4.0, 0.5, "cylinder")
        self.assertAlmostEqual(rep["ratio"], 0.5168291571262306, places=9)
        self.assertAlmostEqual(rep["distance"], 0.2584145785631153,
                               places=9)
        self.assertTrue(rep["sphere_cylinder_order"])
        self.assertTrue(rep["decreasing_with_mach"])

    def test_report_mach8_sphere_distance(self):
        """Sphere report at Mach 8 and nose radius 0.5 m reports the
        0.07521 m standoff distance from the worked example."""
        rep = standoff_report(8.0, 0.5)
        self.assertAlmostEqual(rep["distance"], 0.0752128767519006,
                               places=9)

    def test_decreasing_flag_uses_mach_times_1_1(self):
        """decreasing_with_mach stays True when the ratio at 1.1 times
        the Mach is smaller, as in step 4 of the workflow."""
        self.assertTrue(standoff_report(4.0, 0.5)["decreasing_with_mach"])
        self.assertLess(
            standoff_ratio(4.0 * 1.1), standoff_ratio(4.0)
        )


class HighMachAsymptote(unittest.TestCase):
    """Step 5 of the SKILL.md workflow context, the high Mach side."""

    def test_sphere_asymptote_at_mach20(self):
        """At Mach 20 the sphere ratio approaches the leading
        coefficient SPHERE_COEF from above."""
        r = standoff_ratio(20.0)
        self.assertGreater(r, SPHERE_COEF)
        self.assertLess(r, SPHERE_COEF + 0.002)

    def test_cylinder_asymptote_at_mach20(self):
        """At Mach 20 the cylinder ratio approaches the leading
        coefficient CYL_COEF from above."""
        r = standoff_ratio(20.0, "cylinder")
        self.assertGreater(r, CYL_COEF)
        self.assertLess(r, CYL_COEF + 0.005)

    def test_ratio_finite_and_growing_near_floor(self):
        """Near the validity floor the ratio stays finite but already
        exceeds the Mach 4 ratio for both bodies, so the step 5 floor
        caveat applies below Mach 1.5."""
        for body in ("sphere", "cylinder"):
            self.assertGreater(standoff_ratio(1.05, body),
                               standoff_ratio(4.0, body))
            self.assertTrue(standoff_ratio(1.05, body) < 1e6)


class ValueErrorRejection(unittest.TestCase):
    """Step 1 of the SKILL.md workflow, the non-physical rejection."""

    def test_valueerror_mach_one_ratio(self):
        """Mach 1.0 raises ValueError on the ratio: no detached bow
        shock exists at Mach 1."""
        with self.assertRaises(ValueError):
            standoff_ratio(1.0)

    def test_valueerror_mach_below_one_ratio(self):
        """Mach 0.8 raises ValueError on the ratio."""
        with self.assertRaises(ValueError):
            standoff_ratio(0.8)

    def test_valueerror_mach_one_distance(self):
        """Mach 1.0 raises ValueError on the standoff distance."""
        with self.assertRaises(ValueError):
            standoff_distance(1.0, 0.5)

    def test_valueerror_mach_one_report(self):
        """Mach 1.0 raises ValueError on the report."""
        with self.assertRaises(ValueError):
            standoff_report(1.0, 0.5)

    def test_valueerror_radius_zero(self):
        """A zero nose radius raises ValueError on the distance."""
        with self.assertRaises(ValueError):
            standoff_distance(4.0, 0.0)

    def test_valueerror_radius_negative(self):
        """A negative nose radius raises ValueError on the distance."""
        with self.assertRaises(ValueError):
            standoff_distance(4.0, -0.5)

    def test_valueerror_unknown_body_ratio(self):
        """The body string wedge raises ValueError on the ratio."""
        with self.assertRaises(ValueError):
            standoff_ratio(4.0, "wedge")

    def test_valueerror_unknown_body_distance(self):
        """The body string wedge raises ValueError on the distance."""
        with self.assertRaises(ValueError):
            standoff_distance(4.0, 0.5, "wedge")


class Determinism(unittest.TestCase):
    """Step 6 of the SKILL.md workflow, the deterministic contract."""

    def test_deterministic_repeated_calls(self):
        """Repeated calls at the same flight point agree exactly for
        the sphere and the cylinder body."""
        for body in ("sphere", "cylinder"):
            self.assertEqual(standoff_ratio(7.5, body),
                             standoff_ratio(7.5, body))
            rep1 = standoff_report(7.5, 0.3, body)
            rep2 = standoff_report(7.5, 0.3, body)
            self.assertEqual(rep1, rep2)


if __name__ == "__main__":
    unittest.main()
