"""Contract test for the gravity-gradient-stabilization leaf.

Exercises every step of the SKILL.md workflow: step 1, the mean-motion
traverse; step 2, the inertia-ratio criterion traverse; step 3, the pitch
libration frequency and period traverse; step 4, the restoring-torque
traverse; step 5, the boom-sizing traverse; step 6, the design-report
gather; step 7, the deterministic contract confirmation. Fact terms:
mean motion, inertia ratio, stability verdict, pitch libration frequency,
libration period, restoring torque, gravity boom tip mass, inertia
spread. Procedure terms: criterion check, traverse, report gather.
Run offline: python3 test_gravity_gradient_stabilization.py
"""

import math
import unittest

from gravity_gradient_stabilization_logic import (
    MU_EARTH,
    boom_tip_mass_for_stiffness,
    gg_report,
    libration_period,
    mean_motion,
    moment_ordering,
    pitch_libration_frequency,
    restoring_torque,
    stability_verdict,
)

MU = 3.986004418e14
R_500KM = 6.878e6


class GravityGradientStabilizationTest(unittest.TestCase):

    def test_mean_motion_at_500_km_anchor(self):
        """Step 1 of the SKILL.md workflow, the mean-motion traverse,
        gives n = 1.1068e-3 rad/s at the 500 km worked example."""
        n = mean_motion(MU, R_500KM)
        self.assertAlmostEqual(n, 1.1068e-3, delta=1e-6)

    def test_mean_motion_scales_as_radius_to_minus_15(self):
        """Step 1 of the SKILL.md workflow: doubling the orbital radius
        divides the mean motion by 2 ** 1.5."""
        n1 = mean_motion(MU, R_500KM)
        n2 = mean_motion(MU, 2.0 * R_500KM)
        self.assertAlmostEqual(n2, n1 / (2.0 ** 1.5), places=12)

    def test_mean_motion_rejects_nonpositive_mu_or_radius(self):
        """Step 1 of the SKILL.md workflow: mean_motion raises ValueError
        when mu or the orbital radius is at or below zero."""
        for bad_mu in (0.0, -1.0):
            with self.assertRaises(ValueError):
                mean_motion(bad_mu, R_500KM)
        for bad_radius in (0.0, -1000.0):
            with self.assertRaises(ValueError):
                mean_motion(MU, bad_radius)

    def test_stability_verdict_true_on_worked_example_moments(self):
        """Step 2 of the SKILL.md workflow, the inertia-ratio criterion
        check: (60, 80, 40) is stable because iy > ix > iz."""
        self.assertTrue(stability_verdict(60, 80, 40))

    def test_stability_verdict_false_when_ix_exceeds_iy(self):
        """Step 2 of the SKILL.md workflow: (80, 60, 40) fails the
        inertia-ratio criterion because ix exceeds iy."""
        self.assertFalse(stability_verdict(80, 60, 40))

    def test_stability_verdict_false_when_iz_not_smallest(self):
        """Step 2 of the SKILL.md workflow: (60, 40, 80) fails because iz
        is not the smallest principal moment."""
        self.assertFalse(stability_verdict(60, 40, 80))

    def test_stability_verdict_false_on_equal_boundary_moments(self):
        """Step 2 of the SKILL.md workflow: the inertia-ratio criterion is
        strict, so equal adjacent moments fail the verdict."""
        self.assertFalse(stability_verdict(60, 60, 40))
        self.assertFalse(stability_verdict(80, 80, 40))
        self.assertFalse(stability_verdict(60, 80, 80))

    def test_moment_ordering_matches_criterion_on_example(self):
        """Step 2 of the SKILL.md workflow: moment_ordering ranks the
        axes by descending moment, giving 'y > x > z' on the example."""
        self.assertEqual(moment_ordering(60, 80, 40), "y > x > z")

    def test_moment_ordering_other_configurations(self):
        """Step 2 of the SKILL.md workflow: the ordering string tracks the
        moments, so (80, 60, 40) reads 'x > y > z'."""
        self.assertEqual(moment_ordering(80, 60, 40), "x > y > z")

    def test_stability_verdict_rejects_nonpositive_inertia(self):
        """Step 2 of the SKILL.md workflow: the criterion check raises
        ValueError on any non-positive principal moment."""
        for bad in ((0, 80, 40), (60, 0, 40), (60, 80, 0), (-5, 80, 40)):
            with self.assertRaises(ValueError):
                stability_verdict(*bad)

    def test_pitch_libration_frequency_anchor(self):
        """Step 3 of the SKILL.md workflow, the libration traverse:
        omega_p = 9.586e-4 rad/s at the worked example, inside 1e-6."""
        w = pitch_libration_frequency(60, 80, 40, MU, R_500KM)
        self.assertAlmostEqual(w, 9.586e-4, delta=1e-6)

    def test_libration_period_anchor_seconds(self):
        """Step 3 of the SKILL.md workflow: the pitch libration period is
        6555 s at the worked example, inside 20 s."""
        p = libration_period(60, 80, 40, MU, R_500KM)
        self.assertAlmostEqual(p, 6555.0, delta=20.0)

    def test_libration_period_anchor_minutes(self):
        """Step 3 of the SKILL.md workflow: the same libration period is
        109.25 min, inside 0.5 min of the 109.2 min anchor."""
        p = libration_period(60, 80, 40, MU, R_500KM)
        self.assertAlmostEqual(p / 60.0, 109.2, delta=0.5)

    def test_libration_period_identity_against_orbital_period(self):
        """Step 3 of the SKILL.md workflow: the libration period identity
        holds, period equals the orbital period divided by
        sqrt(3 * (ix - iz) / iy), about 1.155 orbital periods."""
        p = libration_period(60, 80, 40, MU, R_500KM)
        orbit = 2.0 * math.pi / mean_motion(MU, R_500KM)
        expected = orbit / math.sqrt(3.0 * (60.0 - 40.0) / 80.0)
        self.assertAlmostEqual(p, expected, places=6)
        self.assertAlmostEqual(p / orbit, 1.1547005, places=6)

    def test_doubled_inertia_spread_raises_frequency_by_sqrt2(self):
        """Step 3 of the SKILL.md workflow: doubling the inertia spread
        (ix - iz) at fixed iy multiplies omega_p by sqrt(2), the closed
        form identity behind the libration traverse."""
        w1 = pitch_libration_frequency(60, 80, 40, MU, R_500KM)
        w2 = pitch_libration_frequency(75, 80, 35, MU, R_500KM)
        self.assertAlmostEqual(w2 / w1, math.sqrt(2.0), places=12)
        p1 = libration_period(60, 80, 40, MU, R_500KM)
        p2 = libration_period(75, 80, 35, MU, R_500KM)
        self.assertAlmostEqual(p1 / p2, math.sqrt(2.0), places=12)

    def test_libration_frequency_rejects_nonphysical_inputs(self):
        """Step 3 of the SKILL.md workflow: the libration traverse raises
        ValueError on a negative or zero inertia spread and on non-positive
        mu or orbital radius."""
        with self.assertRaises(ValueError):
            pitch_libration_frequency(60, 80, 80, MU, R_500KM)
        with self.assertRaises(ValueError):
            pitch_libration_frequency(60, 80, 60, MU, R_500KM)
        with self.assertRaises(ValueError):
            pitch_libration_frequency(60, 80, 40, 0.0, R_500KM)
        with self.assertRaises(ValueError):
            pitch_libration_frequency(60, 80, 40, MU, -R_500KM)

    def test_restoring_torque_anchor_at_45_degrees(self):
        """Step 4 of the SKILL.md workflow, the restoring-torque traverse:
        the torque is 3.675e-5 N m at a 45 degree pitch offset, inside
        1e-6 of the 3.68e-5 anchor."""
        t = restoring_torque(60, 80, 40, MU, R_500KM, 45.0)
        self.assertAlmostEqual(t, 3.68e-5, delta=1e-6)

    def test_restoring_torque_zero_at_zero_and_ninety_degrees(self):
        """Step 4 of the SKILL.md workflow: the restoring torque is zero
        at 0 degrees (nadir) and at 90 degrees (the unstable
        equilibrium), from the sin(2 * theta) factor."""
        self.assertEqual(restoring_torque(60, 80, 40, MU, R_500KM, 0.0), 0.0)
        self.assertAlmostEqual(
            restoring_torque(60, 80, 40, MU, R_500KM, 90.0), 0.0, delta=1e-15)

    def test_restoring_torque_symmetric_and_maximal_at_45(self):
        """Step 4 of the SKILL.md workflow: the torque flips sign with the
        offset and is largest in magnitude at 45 degrees."""
        t45 = restoring_torque(60, 80, 40, MU, R_500KM, 45.0)
        t_neg = restoring_torque(60, 80, 40, MU, R_500KM, -45.0)
        self.assertAlmostEqual(t_neg, -t45, places=12)
        t10 = restoring_torque(60, 80, 40, MU, R_500KM, 10.0)
        self.assertLess(abs(t10), abs(t45))

    def test_restoring_torque_rejects_out_of_range_offset(self):
        """Step 4 of the SKILL.md workflow: offsets beyond the -90 to
        90 degree range raise ValueError, as does a negative inertia
        spread."""
        for bad_offset in (91.0, -91.0, 180.0, -180.0):
            with self.assertRaises(ValueError):
                restoring_torque(60, 80, 40, MU, R_500KM, bad_offset)
        with self.assertRaises(ValueError):
            restoring_torque(60, 80, 80, MU, R_500KM, 45.0)

    def test_boom_tip_mass_anchor(self):
        """Step 5 of the SKILL.md workflow, the boom-sizing traverse: a
        20 kg m2 target inertia spread on a 10 m gravity boom needs a
        0.2 kg tip mass, inside 0.01."""
        m = boom_tip_mass_for_stiffness(60, 20.0, 10.0)
        self.assertAlmostEqual(m, 0.2, delta=0.01)

    def test_boom_tip_mass_inverse_square_scaling(self):
        """Step 5 of the SKILL.md workflow: halving the boom length
        quadruples the tip mass because m = spread / L^2."""
        m10 = boom_tip_mass_for_stiffness(60, 20.0, 10.0)
        m5 = boom_tip_mass_for_stiffness(60, 20.0, 5.0)
        self.assertAlmostEqual(m5, 4.0 * m10, places=12)

    def test_boom_tip_mass_rejects_nonpositive_inputs(self):
        """Step 5 of the SKILL.md workflow: the boom-sizing traverse
        raises ValueError on any non-positive input."""
        with self.assertRaises(ValueError):
            boom_tip_mass_for_stiffness(0.0, 20.0, 10.0)
        with self.assertRaises(ValueError):
            boom_tip_mass_for_stiffness(60, -20.0, 10.0)
        with self.assertRaises(ValueError):
            boom_tip_mass_for_stiffness(60, 20.0, 0.0)

    def test_gg_report_keys_and_worked_example_values(self):
        """Step 6 of the SKILL.md workflow, the report gather: gg_report
        returns exactly the documented keys stable, ordering, omega_p,
        period_s, period_min and torque, and the values match the direct
        function calls."""
        rep = gg_report(60, 80, 40, MU, R_500KM)
        self.assertEqual(
            set(rep.keys()),
            {"stable", "ordering", "omega_p", "period_s",
             "period_min", "torque"})
        self.assertTrue(rep["stable"])
        self.assertEqual(rep["ordering"], "y > x > z")
        self.assertAlmostEqual(
            rep["omega_p"],
            pitch_libration_frequency(60, 80, 40, MU, R_500KM),
            places=12)
        self.assertAlmostEqual(
            rep["period_s"],
            libration_period(60, 80, 40, MU, R_500KM),
            places=12)
        self.assertAlmostEqual(rep["period_min"], rep["period_s"] / 60.0)
        self.assertAlmostEqual(
            rep["torque"],
            restoring_torque(60, 80, 40, MU, R_500KM, 45.0),
            places=12)

    def test_gg_report_unstable_configuration_returns_none_quantities(self):
        """Step 6 of the SKILL.md workflow: on a configuration that fails
        the inertia-ratio criterion the report marks stable False, names
        the axis ordering, and leaves the quantity keys None."""
        rep = gg_report(80, 60, 40, MU, R_500KM)
        self.assertFalse(rep["stable"])
        self.assertEqual(rep["ordering"], "x > y > z")
        self.assertIsNone(rep["omega_p"])
        self.assertIsNone(rep["period_s"])
        self.assertIsNone(rep["period_min"])
        self.assertIsNone(rep["torque"])

    def test_gg_report_default_offset_is_45_degrees(self):
        """Step 6 of the SKILL.md workflow: the report gather defaults to
        the 45 degree pitch offset, the maximum restoring torque case."""
        rep = gg_report(60, 80, 40, MU, R_500KM)
        rep0 = gg_report(60, 80, 40, MU, R_500KM, pitch_offset_deg=0.0)
        self.assertAlmostEqual(rep["torque"], 3.675e-5, delta=1e-6)
        self.assertEqual(rep0["torque"], 0.0)

    def test_gg_report_rejects_out_of_range_offset(self):
        """Step 6 of the SKILL.md workflow: the report gather raises
        ValueError for a pitch offset magnitude above 90 degrees."""
        with self.assertRaises(ValueError):
            gg_report(60, 80, 40, MU, R_500KM, pitch_offset_deg=95.0)

    def test_determinism_of_repeated_calls(self):
        """Step 7 of the SKILL.md workflow: every function is
        deterministic, so repeated calls return identical values."""
        n1 = mean_motion(MU, R_500KM)
        n2 = mean_motion(MU, R_500KM)
        self.assertEqual(n1, n2)
        w1 = pitch_libration_frequency(60, 80, 40, MU, R_500KM)
        w2 = pitch_libration_frequency(60, 80, 40, MU, R_500KM)
        self.assertEqual(w1, w2)
        t1 = restoring_torque(60, 80, 40, MU, R_500KM, 45.0)
        t2 = restoring_torque(60, 80, 40, MU, R_500KM, 45.0)
        self.assertEqual(t1, t2)
        self.assertEqual(gg_report(60, 80, 40, MU, R_500KM),
                         gg_report(60, 80, 40, MU, R_500KM))

    def test_workflow_end_to_end_passive_design(self):
        """Steps 1 to 6 of the SKILL.md workflow as one passive design
        pass: mean-motion traverse, inertia-ratio criterion check,
        libration traverse, restoring-torque traverse and boom-sizing
        traverse, then the report gather confirms the design."""
        n = mean_motion(MU, R_500KM)
        self.assertAlmostEqual(n, 1.1068e-3, delta=1e-6)
        self.assertTrue(stability_verdict(60, 80, 40))
        rep = gg_report(60, 80, 40, MU, R_500KM)
        self.assertTrue(rep["stable"])
        self.assertAlmostEqual(rep["period_s"], 6555.0, delta=20.0)
        self.assertAlmostEqual(rep["torque"], 3.675e-5, delta=1e-6)
        m = boom_tip_mass_for_stiffness(60, 20.0, 10.0)
        self.assertAlmostEqual(m, 0.2, delta=0.01)
        self.assertAlmostEqual(m * 10.0 ** 2, 20.0, places=6)
        self.assertEqual(MU_EARTH, MU)


if __name__ == "__main__":
    unittest.main()
