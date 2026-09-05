#!/usr/bin/env python3
"""Gate 3 contract test: isentropic flow relations (aerodynamics).

Exercises scripts/isentropic_flow_relations_logic.py (stdlib unittest,
offline, deterministic). Contract: docs/harness-contract.md gate 3 -
the SKILL.md workflow converts a Mach number into the isentropic total
to static ratio set (step 2, total_static_ratios), rebuilds the total
conditions from a static state and confirms the round trip (step 3,
static_to_total), evaluates the area-Mach relation at a Mach number
(step 4, area_ratio), recovers the Mach number from a given area ratio
on the subsonic low branch or the supersonic high branch by
deterministic bisection (step 5, mach_from_area_ratio), computes the
choked mass flow a passage passes at its sonic throat through the mass
flow parameter (step 6, choked_mass_flow), and confirms the
deterministic checks and the ValueError rejection of non-physical
inputs (step 7). Air at gamma 1.4 and R 287.0; anchors from the
wave-41 spec (NACA-TR-824 methodology, paraphrased): at M = 2.0 the
ratios are T0/T = 1.8, p0/p = 7.8244490669, rho0/rho = 4.3469161483,
A/A* = 1.6875 exactly, and the choked mass flow through a 0.01 m2
sonic throat at p0 = 101325 Pa, T0 = 288.15 K is 2.4126072679 kg/s.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import isentropic_flow_relations_logic as iso

P0_WT = 101325.0  # Pa, stilling chamber total pressure
T0_WT = 288.15  # K, stilling chamber total temperature
A_STAR = 0.01  # m2, sonic throat area


class TestTotalStaticRatios(unittest.TestCase):
    """Workflow step 2, converting the Mach number into the isentropic
    total to static ratio set, is exercised by every method here."""

    def test_ratios_at_mach2_anchor_set(self):
        """Convert M = 2.0: t0_over_t 1.8 within 1e-9, p0_over_p
        7.8244490669 within 1e-9, rho0_over_rho 4.3469161483 within
        1e-9, the supersonic wind tunnel anchor set."""
        r = iso.total_static_ratios(2.0)
        self.assertAlmostEqual(r["t0_over_t"], 1.8, delta=1e-9)
        self.assertAlmostEqual(r["p0_over_p"], 7.8244490669, delta=1e-9)
        self.assertAlmostEqual(r["rho0_over_rho"], 4.3469161483, delta=1e-9)

    def test_ratios_at_mach085_cruise_point(self):
        """Convert the M = 0.85 subsonic cruise point: t0_over_t
        1.1445 within 1e-12, p0_over_p 1.6038187614 within 1e-9 and
        rho0_over_rho 1.4013270087 within 1e-9."""
        r = iso.total_static_ratios(0.85)
        self.assertAlmostEqual(r["t0_over_t"], 1.1445, delta=1e-12)
        self.assertAlmostEqual(r["p0_over_p"], 1.6038187614, delta=1e-9)
        self.assertAlmostEqual(r["rho0_over_rho"], 1.4013270087, delta=1e-9)

    def test_ratios_at_mach3_supersonic_point(self):
        """Convert M = 3.0: t0_over_t 2.8, p0_over_p 36.7327218050 and
        rho0_over_rho 13.1188292161 all within 1e-9, verifying the
        exponent growth of the total pressure and density ratios."""
        r = iso.total_static_ratios(3.0)
        self.assertAlmostEqual(r["t0_over_t"], 2.8, delta=1e-9)
        self.assertAlmostEqual(r["p0_over_p"], 36.7327218050, delta=1e-9)
        self.assertAlmostEqual(r["rho0_over_rho"], 13.1188292161, delta=1e-9)

    def test_ratios_at_mach_zero_identity(self):
        """Convert M = 0.0: every total to static ratio is exactly 1.0,
        the zero-Mach identity of the isentropic conversion."""
        r = iso.total_static_ratios(0.0)
        self.assertEqual(r["t0_over_t"], 1.0)
        self.assertEqual(r["p0_over_p"], 1.0)
        self.assertEqual(r["rho0_over_rho"], 1.0)

    def test_ratios_dict_keys_exact(self):
        """Convert M = 2.0 and check the returned dict keys are exactly
        t0_over_t, p0_over_p and rho0_over_rho, the schema of step 2."""
        r = iso.total_static_ratios(2.0)
        self.assertEqual(
            set(r.keys()), {"t0_over_t", "p0_over_p", "rho0_over_rho"})

    def test_ratios_reject_negative_mach(self):
        """Reject a negative Mach number: a negative Mach is not a
        physical compressible flow state, so conversion must raise
        ValueError (step 7 rejection check)."""
        with self.assertRaises(ValueError):
            iso.total_static_ratios(-0.5)


class TestStaticToTotal(unittest.TestCase):
    """Workflow step 3, rebuilding the total conditions from a static
    state and confirming the round trip through the ratios, is
    exercised by every method here."""

    def test_static_to_total_cruise_rebuild(self):
        """Rebuild totals at the M = 0.85 cruise static state of
        30000 Pa and 220 K: p0 48114.562843 within 1e-6 and t0 251.79
        within 1e-9, the step 3 rebuild contract."""
        tot = iso.static_to_total(30000.0, 220.0, 0.85)
        self.assertAlmostEqual(tot["p0"], 48114.562843, delta=1e-6)
        self.assertAlmostEqual(tot["t0"], 251.79, delta=1e-9)

    def test_static_to_total_round_trip_mach2_exact(self):
        """Rebuild totals from the M = 2.0 static state derived by
        dividing the stilling chamber conditions by the ratios, then
        check the round trip returns p0 = 101325.0 and t0 = 288.15
        exactly (step 3 inverts step 2 to machine precision)."""
        r = iso.total_static_ratios(2.0)
        p_static = P0_WT / r["p0_over_p"]
        t_static = T0_WT / r["t0_over_t"]
        tot = iso.static_to_total(p_static, t_static, 2.0)
        self.assertAlmostEqual(tot["p0"], P0_WT, delta=1e-6)
        self.assertAlmostEqual(tot["t0"], T0_WT, delta=1e-6)
        self.assertEqual(set(tot.keys()), {"p0", "t0"})

    def test_static_to_total_spec_literal_static_state(self):
        """Rebuild totals from the spec literal static state at M = 2.0,
        p = 12949.793543 Pa and T = 160.083333 K: p0 returns within
        1e-5 Pa of 101325.0 and t0 within 1e-6 K of 288.15, honoring
        the printed rounding of the worked example."""
        tot = iso.static_to_total(12949.793543, 160.083333, 2.0)
        self.assertAlmostEqual(tot["p0"], P0_WT, delta=1e-5)
        self.assertAlmostEqual(tot["t0"], T0_WT, delta=1e-6)

    def test_static_to_total_reject_nonpositive_pressure(self):
        """Reject a non-positive static pressure: p_static 0.0 and
        negative values are not physical and must raise ValueError
        (step 7 rejection check on the rebuild)."""
        with self.assertRaises(ValueError):
            iso.static_to_total(0.0, 220.0, 0.85)
        with self.assertRaises(ValueError):
            iso.static_to_total(-100.0, 220.0, 0.85)

    def test_static_to_total_reject_nonpositive_temperature(self):
        """Reject a non-positive static temperature: t_static 0.0 and
        negative values must raise ValueError on the rebuild (step 7
        rejection check)."""
        with self.assertRaises(ValueError):
            iso.static_to_total(30000.0, 0.0, 0.85)
        with self.assertRaises(ValueError):
            iso.static_to_total(30000.0, -220.0, 0.85)

    def test_static_to_total_reject_negative_mach(self):
        """Reject a negative Mach number in the rebuild call, matching
        the step 2 rejection of non-physical Mach inputs."""
        with self.assertRaises(ValueError):
            iso.static_to_total(30000.0, 220.0, -1.0)


class TestAreaRatio(unittest.TestCase):
    """Workflow step 4, evaluating the area-Mach relation at a Mach
    number, is exercised by every method here."""

    def test_area_ratio_closed_form_values(self):
        """Evaluate the area-Mach relation at the closed-form points:
        A/A* = 1.0 at M = 1.0 within 1e-15, 1.6875 at M = 2.0 within
        1e-12 and 1.33984375 at M = 0.5 within 1e-12."""
        self.assertAlmostEqual(iso.area_ratio(1.0), 1.0, delta=1e-15)
        self.assertAlmostEqual(iso.area_ratio(2.0), 1.6875, delta=1e-12)
        self.assertAlmostEqual(iso.area_ratio(0.5), 1.33984375, delta=1e-12)

    def test_area_ratio_cruise_point(self):
        """Evaluate A/A* at the M = 0.85 cruise point: 1.020668536305
        within 1e-9, the contraction-side value near the throat."""
        self.assertAlmostEqual(
            iso.area_ratio(0.85), 1.020668536305, delta=1e-9)

    def test_area_ratio_sonic_minimum_and_monotone_branches(self):
        """Verify the sonic minimum of the area-Mach relation: the
        ratio is monotone decreasing on the subsonic branch (0, 1] and
        monotone increasing on the supersonic branch [1, 20], with its
        minimum 1.0 exactly at M = 1.0."""
        sub_points = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
        sub_vals = [iso.area_ratio(m) for m in sub_points]
        for lower, upper in zip(sub_vals, sub_vals[1:]):
            self.assertGreater(lower, upper)
        sup_vals = [iso.area_ratio(m) for m in [1.0, 2.0, 3.0, 5.0, 10.0, 20.0]]
        for lower, upper in zip(sup_vals, sup_vals[1:]):
            self.assertLess(lower, upper)
        self.assertEqual(iso.area_ratio(1.0), 1.0)
        self.assertGreater(iso.area_ratio(0.99), 1.0)
        self.assertGreater(iso.area_ratio(1.01), 1.0)

    def test_area_ratio_reject_zero_and_negative_mach(self):
        """Reject mach 0.0 and negative mach in the area-Mach
        evaluation: both must raise ValueError (step 7 rejection
        check)."""
        with self.assertRaises(ValueError):
            iso.area_ratio(0.0)
        with self.assertRaises(ValueError):
            iso.area_ratio(-2.0)


class TestMachFromAreaRatio(unittest.TestCase):
    """Workflow step 5, recovering the Mach number from a given area
    ratio on the subsonic low branch or the supersonic high branch by
    deterministic bisection, is exercised by every method here."""

    def test_recover_supersonic_root_classic_16875(self):
        """Recover the supersonic root for A/A* = 1.6875: M = 2.0
        within 1e-10, the classic supersonic wind tunnel test section
        value from the worked example."""
        m = iso.mach_from_area_ratio(1.6875, subsonic=False)
        self.assertAlmostEqual(m, 2.0, delta=1e-10)

    def test_recover_subsonic_root_classic_16875(self):
        """Recover the subsonic root for the same A/A* = 1.6875: M =
        0.372244486203 within 1e-10, the contraction-side Mach at the
        same area station."""
        m = iso.mach_from_area_ratio(1.6875, subsonic=True)
        self.assertAlmostEqual(m, 0.372244486203, delta=1e-10)

    def test_recover_both_roots_contraction_ratio_2(self):
        """Recover both roots for the common contraction ratio A/A* =
        2.0: the supersonic root 2.197198121652 and the subsonic root
        0.305903834189, each within 1e-10."""
        hi = iso.mach_from_area_ratio(2.0, subsonic=False)
        lo = iso.mach_from_area_ratio(2.0, subsonic=True)
        self.assertAlmostEqual(hi, 2.197198121652, delta=1e-10)
        self.assertAlmostEqual(lo, 0.305903834189, delta=1e-10)

    def test_recover_round_trip_on_own_branch(self):
        """Recover M from area_ratio(M) on its own branch: the bisection
        round trip returns M within 1e-10 for M = 0.5, 2.0 and 3.0, the
        identity check of step 5 against step 4."""
        for mach, branch in ((0.5, True), (2.0, False), (3.0, False)):
            back = iso.mach_from_area_ratio(
                iso.area_ratio(mach), subsonic=branch)
            self.assertAlmostEqual(back, mach, delta=1e-10)

    def test_recover_sonic_area_ratio_returns_one(self):
        """Recover M for A/A* = 1.0: both branches return exactly 1.0,
        the sonic throat condition."""
        self.assertEqual(iso.mach_from_area_ratio(1.0, subsonic=True), 1.0)
        self.assertEqual(iso.mach_from_area_ratio(1.0, subsonic=False), 1.0)

    def test_recover_near_sonic_rebracket_roots(self):
        """Recover both roots for the near-sonic A/A* = 1.00005: the
        re-bracketed subsonic root 0.992270777840 and supersonic root
        1.007762554875, each within 1e-10."""
        lo = iso.mach_from_area_ratio(1.00005, subsonic=True)
        hi = iso.mach_from_area_ratio(1.00005, subsonic=False)
        self.assertAlmostEqual(lo, 0.992270777840, delta=1e-10)
        self.assertAlmostEqual(hi, 1.007762554875, delta=1e-10)

    def test_recover_reject_below_sonic_floor(self):
        """Reject an area ratio below the sonic-throat floor: A/A* =
        0.999 and 0.5 are not physical and must raise ValueError."""
        with self.assertRaises(ValueError):
            iso.mach_from_area_ratio(0.999)
        with self.assertRaises(ValueError):
            iso.mach_from_area_ratio(0.5, subsonic=False)

    def test_recover_reject_domain_limit_excess(self):
        """Reject area ratios beyond the documented bracket domain: the
        subsonic root for A/A* = 12.0 lies below the 0.05 bracket floor
        of 11.591443867187 and the supersonic root for A/A* = 16000.0
        above the 20.0 bracket ceiling of 15377.343750000022, so both
        must raise ValueError."""
        with self.assertRaises(ValueError):
            iso.mach_from_area_ratio(12.0, subsonic=True)
        with self.assertRaises(ValueError):
            iso.mach_from_area_ratio(16000.0, subsonic=False)

    def test_recover_deterministic_bits(self):
        """Run the bisection twice on identical inputs and require
        identical bits, the determinism contract of step 5 (no RNG,
        fixed bracket schedule)."""
        first = iso.mach_from_area_ratio(1.6875, subsonic=False)
        second = iso.mach_from_area_ratio(1.6875, subsonic=False)
        self.assertEqual(first, second)

    def test_recover_both_roots_bracket_sonic_and_approach(self):
        """Verify the two roots of one area ratio bracket 1.0: the
        subsonic root stays below 1.0 and the supersonic root above
        1.0, and both approach 1.0 as the ratio approaches 1.0."""
        lo = iso.mach_from_area_ratio(1.00005, subsonic=True)
        hi = iso.mach_from_area_ratio(1.00005, subsonic=False)
        self.assertLess(lo, 1.0)
        self.assertGreater(hi, 1.0)
        closer_lo = iso.mach_from_area_ratio(1.00001, subsonic=True)
        closer_hi = iso.mach_from_area_ratio(1.00001, subsonic=False)
        self.assertGreater(closer_lo, lo)
        self.assertLess(closer_hi, hi)

    def test_branch_monotonic_roots_in_area_ratio(self):
        """Verify the recovered roots move monotonically with the area
        ratio: on the subsonic low branch the root falls as A/A* grows
        (0.3059 at 2.0 below 0.3722 at 1.6875) and on the supersonic
        high branch the root rises (2.1972 at 2.0 above 2.0 at
        1.6875)."""
        self.assertLess(
            iso.mach_from_area_ratio(2.0, subsonic=True),
            iso.mach_from_area_ratio(1.6875, subsonic=True))
        self.assertGreater(
            iso.mach_from_area_ratio(2.0, subsonic=False),
            iso.mach_from_area_ratio(1.6875, subsonic=False))


class TestChokedMassFlow(unittest.TestCase):
    """Workflow step 6, computing the choked mass flow the passage
    passes at its sonic throat from total pressure, total temperature
    and throat area through the mass flow parameter, is exercised by
    every method here."""

    def test_choked_mass_flow_anchor_throat(self):
        """Compute the choked flow at p0 = 101325 Pa, T0 = 288.15 K
        and a 0.01 m2 sonic throat: mdot = 2.4126072679 kg/s within
        1e-8, the worked example anchor."""
        mdot = iso.choked_mass_flow(P0_WT, T0_WT, A_STAR)
        self.assertAlmostEqual(mdot, 2.4126072679, delta=1e-8)

    def test_choked_mass_flow_linear_in_p0(self):
        """Double the total pressure to 202650 Pa and verify the choked
        mass flow doubles to 4.8252145358 kg/s within 1e-8, the linear
        scaling of the choked flow with total pressure."""
        mdot = iso.choked_mass_flow(2.0 * P0_WT, T0_WT, A_STAR)
        self.assertAlmostEqual(mdot, 4.8252145358, delta=1e-8)
        self.assertAlmostEqual(
            mdot, 2.0 * iso.choked_mass_flow(P0_WT, T0_WT, A_STAR),
            delta=1e-8)

    def test_choked_mass_flow_linear_in_throat_area(self):
        """Double the sonic throat area to 0.02 m2 and verify the choked
        mass flow doubles to 4.8252145358 kg/s within 1e-8, the linear
        scaling with the throat area."""
        mdot = iso.choked_mass_flow(P0_WT, T0_WT, 2.0 * A_STAR)
        self.assertAlmostEqual(mdot, 4.8252145358, delta=1e-8)

    def test_choked_mass_flow_inverse_sqrt_total_temperature(self):
        """Quadruple the total temperature to 1152.6 K and verify the
        choked mass flow halves to 1.2063036339 kg/s within 1e-8, the
        1 / sqrt(t0) scaling of the choked flow."""
        mdot = iso.choked_mass_flow(P0_WT, 4.0 * T0_WT, A_STAR)
        self.assertAlmostEqual(mdot, 1.2063036339, delta=1e-8)

    def test_mass_flow_parameter_identity_all_points(self):
        """Check the mass flow parameter identity on every worked point:
        mdot * sqrt(t0) / (p0 * area_star) equals 0.0404184199 within
        1e-10, the MFP of the choked flow relation."""
        mfp_module = math.sqrt(iso.GAMMA / iso.R) * (
            2.0 / (iso.GAMMA + 1.0)) ** ((iso.GAMMA + 1.0) /
                                         (2.0 * (iso.GAMMA - 1.0)))
        self.assertAlmostEqual(mfp_module, 0.0404184199, delta=1e-10)
        points = [
            (P0_WT, T0_WT, A_STAR),
            (2.0 * P0_WT, T0_WT, A_STAR),
            (P0_WT, T0_WT, 2.0 * A_STAR),
            (P0_WT, 4.0 * T0_WT, A_STAR),
        ]
        for p0, t0, a_star in points:
            mdot = iso.choked_mass_flow(p0, t0, a_star)
            identity = mdot * math.sqrt(t0) / (p0 * a_star)
            self.assertAlmostEqual(identity, mfp_module, delta=1e-12)

    def test_choked_mass_flow_reject_nonpositive_inputs(self):
        """Reject non-positive p0, t0 and area_star: total pressure 0,
        total temperature 0 or negative, and a zero throat area are not
        physical choked flow inputs and must raise ValueError (step 7
        rejection check)."""
        with self.assertRaises(ValueError):
            iso.choked_mass_flow(0.0, T0_WT, A_STAR)
        with self.assertRaises(ValueError):
            iso.choked_mass_flow(P0_WT, 0.0, A_STAR)
        with self.assertRaises(ValueError):
            iso.choked_mass_flow(P0_WT, -288.15, A_STAR)
        with self.assertRaises(ValueError):
            iso.choked_mass_flow(P0_WT, T0_WT, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
