"""Contract test for the aerodynamics/high-speed/regular-shock-reflection leaf.

Exercises the numbered SKILL.md Workflow: fixing the freestream Mach
number and flow deflection (step 1), solving the incident shock on the
theta-beta-M weak branch with the deflection round trip back-check (step
2), marching the state behind the incident shock (step 3), evaluating the
reflected-shock detachment limit with the golden-section maximizer (step
4), judging the regular versus mach verdict by bisection and the
detachment criterion (step 5), solving the reflected shock and assembling
the post-reflection state from the product of the two stage ratio sets
(step 6), and reporting the two-shock interaction (step 7).  Every
expectation is a real module output from a local run, cross-checked
against the spec anchors.  Offline, deterministic, pure stdlib.

Run: python3 scripts/test_regular_shock_reflection.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import regular_shock_reflection_logic as r

GAMMA = 1.4


class ShockAngleWeakTests(unittest.TestCase):
    """Weak-branch incident shock angle solves (Workflow steps 2 and 5)."""

    def test_shock_angle_weak_M1_3_theta_15(self):
        """Step 2 of the SKILL.md workflow, the incident weak-branch
        solution: the shock angle at (3.0, 15.0) is 32.240400 deg within
        1e-6, the anchor of the regular reflection worked example."""
        self.assertAlmostEqual(r.shock_angle_weak(3.0, 15.0), 32.240400, places=6)

    def test_shock_angle_weak_reference_pairs(self):
        """Step 2 of the SKILL.md workflow, theta-beta-M weak branch at
        the reference Mach numbers: (2.0, 10.0) = 39.313932, (2.0, 20.0)
        = 53.422941, (5.0, 25.0) = 35.779435 and (1.5, 5.0) =
        47.889264 deg, each within 1e-6."""
        for m1, theta, want in [
            (2.0, 10.0, 39.313932),
            (2.0, 20.0, 53.422941),
            (5.0, 25.0, 35.779435),
            (1.5, 5.0, 47.889264),
        ]:
            self.assertAlmostEqual(
                r.shock_angle_weak(m1, theta), want, places=6,
                msg="shock_angle_weak(%s, %s)" % (m1, theta),
            )

    def test_zero_deflection_returns_mach_angle(self):
        """Step 2 of the SKILL.md workflow, the degenerate zero
        deflection: the weak-branch solver returns the Mach angle
        asin(1/M1), 19.471221 deg at M1 = 3.0 within 1e-6 and 30.0 deg
        at M1 = 2.0 to machine precision."""
        self.assertAlmostEqual(r.shock_angle_weak(3.0, 0.0), 19.471221, places=6)
        self.assertAlmostEqual(r.shock_angle_weak(2.0, 0.0), 30.0, places=9)

    def test_theta_beta_m_deflection_round_trip(self):
        """Steps 2 and 6 of the SKILL.md workflow, the theta-beta-M
        round trip identity: deflection_angle at the solved shock angle
        recovers the requested deflection within 1e-9 for the five
        reference pairs and the worked example, so both the incident and
        reflected solves close exactly (the degenerate zero deflection is
        covered by its Mach-angle test)."""
        for m1, theta in [
            (3.0, 15.0), (2.0, 10.0), (2.0, 20.0), (5.0, 25.0), (1.5, 5.0),
        ]:
            beta = r.shock_angle_weak(m1, theta)
            back = r.deflection_angle(m1, beta)
            self.assertAlmostEqual(
                back, theta, places=9,
                msg="round trip at (M1=%s, theta=%s)" % (m1, theta),
            )

    def test_negative_deflection_rejected(self):
        """Step 2 of the SKILL.md workflow, physical-input guard: a
        negative flow deflection has no oblique-shock solution and
        raises ValueError."""
        with self.assertRaises(ValueError):
            r.shock_angle_weak(3.0, -1.0)

    def test_detached_incident_deflection_rejected(self):
        """Step 2 of the SKILL.md workflow, attached-shock guard: a
        deflection at or above the detachment limit, shock_angle_weak(2.0,
        22.973532) and shock_angle_weak(3.0, 35.0), is a detached
        incident shock and raises ValueError."""
        with self.assertRaises(ValueError):
            r.shock_angle_weak(2.0, 22.973532)
        with self.assertRaises(ValueError):
            r.shock_angle_weak(3.0, 35.0)

    def test_sonic_and_subsonic_upstream_rejected(self):
        """Steps 2, 3 and 4 of the SKILL.md workflow, physical-input
        guard: every solver rejects M1 at or below 1 with ValueError."""
        for m1 in (1.0, 0.8):
            with self.assertRaises(ValueError):
                r.shock_angle_weak(m1, 5.0)
            with self.assertRaises(ValueError):
                r.deflection_angle(m1, 45.0)
            with self.assertRaises(ValueError):
                r.maximum_deflection_angle(m1)
            with self.assertRaises(ValueError):
                r.oblique_shock_state(m1, 5.0)


class DeflectionAngleTests(unittest.TestCase):
    """Deflection angle evaluations (Workflow steps 2 and 4)."""

    def test_deflection_angle_at_known_shock_angle(self):
        """Step 2 of the SKILL.md workflow: deflection_angle(3.0,
        32.240400) recovers the 15 deg worked-example deflection within
        1e-6, closing the theta-beta-M relation from the shock-angle
        side."""
        self.assertAlmostEqual(r.deflection_angle(3.0, 32.240400), 15.0, places=6)

    def test_deflection_angle_unimodal_over_shock_angles(self):
        """Steps 2 and 4 of the SKILL.md workflow, the deflection
        profile that the golden-section maximizer climbs: at M1 = 3.0 the
        deflection rises from zero at the Mach angle to the detachment
        peak and falls again toward 90 deg, so the values at 25 and 80
        deg both sit below the value at 45 deg and all stay below
        theta_max = 34.073440."""
        d25 = r.deflection_angle(3.0, 25.0)
        d45 = r.deflection_angle(3.0, 45.0)
        d80 = r.deflection_angle(3.0, 80.0)
        self.assertLess(d25, d45)
        self.assertLess(d80, d45)
        self.assertLess(d45, r.maximum_deflection_angle(3.0))
        self.assertGreater(d45, 0.0)

    def test_deflection_angle_rejects_beta_outside_open_interval(self):
        """Step 2 of the SKILL.md workflow, physical-input guard: the
        shock angle must lie strictly between the Mach angle and 90 deg;
        values at or outside the endpoints raise ValueError."""
        with self.assertRaises(ValueError):
            r.deflection_angle(3.0, 10.0)  # below the Mach angle 19.471221
        with self.assertRaises(ValueError):
            r.deflection_angle(3.0, 90.0)
        with self.assertRaises(ValueError):
            r.deflection_angle(3.0, 95.0)


class MaximumDeflectionAngleTests(unittest.TestCase):
    """Detachment limit evaluations (Workflow step 4)."""

    def test_detachment_limit_reference_values(self):
        """Step 4 of the SKILL.md workflow, the reflected-shock
        detachment limit from the golden-section maximizer: 3.944187 at
        M1 = 1.2, 12.112669 at 1.5, 22.973532 at 2.0, 34.073440 at 3.0
        and 41.117663 at 5.0 deg, each within 1e-6."""
        for m1, want in [
            (1.2, 3.944187), (1.5, 12.112669), (2.0, 22.973532),
            (3.0, 34.073440), (5.0, 41.117663),
        ]:
            self.assertAlmostEqual(
                r.maximum_deflection_angle(m1), want, places=6,
                msg="theta_max at M1=%s" % m1,
            )

    def test_detachment_limit_rises_with_mach_number(self):
        """Step 4 of the SKILL.md workflow: the detachment limit rises
        monotonically with the Mach number toward its asymptotic maximum,
        so theta_max(5.0) > theta_max(3.0) > theta_max(2.0) >
        theta_max(1.5) > theta_max(1.2)."""
        limits = [r.maximum_deflection_angle(m) for m in (1.2, 1.5, 2.0, 3.0, 5.0)]
        for higher, lower in zip(limits[1:], limits[:-1]):
            self.assertGreater(higher, lower)


class ObliqueShockStateTests(unittest.TestCase):
    """State march behind a single oblique shock (Workflow step 3)."""

    def test_incident_state_all_ratios_M1_3_theta_15(self):
        """Step 3 of the SKILL.md workflow, the march behind the
        incident shock at (3.0, 15.0): beta 32.240400, Mn1 1.600418, M2
        2.254902, p2_p1 2.821562, rho2_rho1 2.032449, T2_T1 1.388258 and
        p02_p01 0.895044, each within 1e-6 of the module output."""
        st = r.oblique_shock_state(3.0, 15.0)
        for key, want in [
            ("beta_deg", 32.240400), ("Mn1", 1.600418), ("M2", 2.254902),
            ("p2_p1", 2.821562), ("rho2_rho1", 2.032449), ("T2_T1", 1.388258),
            ("p02_p01", 0.895044),
        ]:
            self.assertAlmostEqual(
                st[key], want, places=6, msg="incident %s" % key,
            )

    def test_state_dict_keys_exact(self):
        """Step 3 of the SKILL.md workflow: oblique_shock_state returns
        exactly the documented keys beta_deg, Mn1, Mn2, M2, p2_p1,
        rho2_rho1, T2_T1 and p02_p01."""
        st = r.oblique_shock_state(3.0, 15.0)
        self.assertEqual(
            set(st.keys()),
            {"beta_deg", "Mn1", "Mn2", "M2", "p2_p1",
             "rho2_rho1", "T2_T1", "p02_p01"},
        )

    def test_temperature_ratio_equals_pressure_over_density(self):
        """Step 3 of the SKILL.md workflow, ratio identity: T2_T1 equals
        p2_p1 divided by rho2_rho1 within 1e-12 for the worked
        example."""
        st = r.oblique_shock_state(3.0, 15.0)
        self.assertAlmostEqual(st["T2_T1"], st["p2_p1"] / st["rho2_rho1"], places=12)

    def test_zero_deflection_state_unit_ratios(self):
        """Step 3 of the SKILL.md workflow, degenerate zero deflection:
        the state at (3.0, 0.0) leaves the flow untouched, M2 = M1 = 3.0
        with unit pressure, density, temperature and stagnation pressure
        ratios and Mn1 = 1 at the Mach angle."""
        st = r.oblique_shock_state(3.0, 0.0)
        self.assertAlmostEqual(st["M2"], 3.0, places=12)
        self.assertAlmostEqual(st["Mn1"], 1.0, places=9)
        for key in ("p2_p1", "rho2_rho1", "T2_T1", "p02_p01"):
            self.assertAlmostEqual(st[key], 1.0, places=9, msg=key)

    def test_detached_state_rejected(self):
        """Step 3 of the SKILL.md workflow, physical-input guard: a
        deflection beyond the attachment limit at M1 = 2.0 raises
        ValueError instead of returning a state."""
        with self.assertRaises(ValueError):
            r.oblique_shock_state(2.0, 23.0)


class ShockReflectionRegularTests(unittest.TestCase):
    """Regular reflection verdict and reflected state (Workflow steps 5, 6, 7)."""

    def test_regular_verdict_and_margin_M1_3_theta_15(self):
        """Step 5 of the SKILL.md workflow, the regular verdict: at
        (3.0, 15.0) the intermediate Mach number M2 = 2.254902 stays
        below the reflected-shock detachment limit 26.860810 deg, giving
        a margin of 11.860810 deg, verdict regular and reason None."""
        sr = r.shock_reflection(3.0, 15.0)
        self.assertEqual(sr["verdict"], "regular")
        self.assertAlmostEqual(sr["M2"], 2.254902, places=6)
        self.assertAlmostEqual(sr["theta_max_ref_deg"], 26.860810, places=6)
        self.assertAlmostEqual(sr["theta_max_ref_deg"] - 15.0, 11.860810, places=6)
        self.assertIsNone(sr["reason"])
        self.assertIsNotNone(sr["reflected"])

    def test_regular_reflected_shock_state(self):
        """Step 6 of the SKILL.md workflow, the reflected-shock solve at
        the intermediate Mach number: beta_ref 40.349015, Mn1 1.459918,
        M3 1.671849, p3_p2 2.319922, rho3_rho2 1.793230, T3_T2 1.293712
        and p03_p02 0.941981, each within 1e-6 of the module output."""
        rf = r.shock_reflection(3.0, 15.0)["reflected"]
        for key, want in [
            ("beta_deg", 40.349015), ("Mn1", 1.459918), ("M2", 1.671849),
            ("p2_p1", 2.319922), ("rho2_rho1", 1.793230), ("T2_T1", 1.293712),
            ("p02_p01", 0.941981),
        ]:
            self.assertAlmostEqual(
                rf[key], want, places=6, msg="reflected %s" % key,
            )

    def test_reflected_wave_steeper_than_incident(self):
        """Step 6 of the SKILL.md workflow, wave-angle ordering: the
        reflected-shock wave angle sits about 8.108615 deg steeper than
        the incident wave angle (40.349015 against 32.240400 deg)."""
        sr = r.shock_reflection(3.0, 15.0)
        beta_inc = sr["incident"]["beta_deg"]
        beta_ref = sr["reflected"]["beta_deg"]
        self.assertGreater(beta_ref, beta_inc)
        self.assertAlmostEqual(beta_ref - beta_inc, 8.108615, places=6)

    def test_post_reflection_state_products(self):
        """Step 6 of the SKILL.md workflow, assembling the post-reflection
        state: p3_p1 = 6.545805 and p03_p01 = 0.843115 equal the products
        of the stage pressure ratio sets within 1e-6, and the shock chain
        decelerates, M3 = 1.671849 below M2 = 2.254902."""
        sr = r.shock_reflection(3.0, 15.0)
        inc, ref = sr["incident"], sr["reflected"]
        p3_p1 = inc["p2_p1"] * ref["p2_p1"]
        p03_p01 = inc["p02_p01"] * ref["p02_p01"]
        self.assertAlmostEqual(p3_p1, 6.545805, places=6)
        self.assertAlmostEqual(p03_p01, 0.843115, places=6)
        self.assertAlmostEqual(sr["reflected"]["M2"], 1.671849, places=6)
        self.assertLess(sr["reflected"]["M2"], sr["M2"])
        self.assertGreater(inc["p2_p1"], 1.0)
        self.assertGreater(ref["p2_p1"], 1.0)

    def test_pressure_rises_total_pressure_falls(self):
        """Steps 6 and 7 of the SKILL.md workflow, monotonicity through
        the pair: static pressure climbs strictly across every shock
        (p2_p1 > 1 and p3_p2 > 1) while stagnation pressure falls, p03_p01
        < p02_p01 < 1 with p03_p02 below 1."""
        sr = r.shock_reflection(3.0, 15.0)
        inc, ref = sr["incident"], sr["reflected"]
        self.assertGreater(inc["p2_p1"], 1.0)
        self.assertGreater(ref["p2_p1"], 1.0)
        self.assertLess(inc["p02_p01"], 1.0)
        self.assertLess(ref["p02_p01"], 1.0)
        self.assertLess(inc["p02_p01"] * ref["p02_p01"], inc["p02_p01"])

    def test_net_zero_turning_parallel_to_wall(self):
        """Step 6 of the SKILL.md workflow, the straight-wall geometry:
        the deflection round trip at the reflected stage recovers the
        15 deg deflection exactly, so the two shocks turn the flow by
        equal and opposite angles and the stream leaves parallel to the
        wall (net zero turning)."""
        sr = r.shock_reflection(3.0, 15.0)
        m2 = sr["M2"]
        beta_ref = sr["reflected"]["beta_deg"]
        back = r.deflection_angle(m2, beta_ref)
        self.assertAlmostEqual(back, 15.0, places=9)
        back_inc = r.deflection_angle(3.0, sr["incident"]["beta_deg"])
        self.assertAlmostEqual(back_inc, 15.0, places=9)

    def test_zero_deflection_regular_verdict(self):
        """Steps 5, 6 and 7 of the SKILL.md workflow, degenerate zero
        deflection: shock_reflection(3.0, 0.0) returns verdict regular
        with unit ratios throughout and a post-reflection Mach number of
        3.0."""
        sr = r.shock_reflection(3.0, 0.0)
        self.assertEqual(sr["verdict"], "regular")
        self.assertAlmostEqual(sr["M2"], 3.0, places=9)
        for key in ("p2_p1", "rho2_rho1", "T2_T1", "p02_p01"):
            self.assertAlmostEqual(sr["incident"][key], 1.0, places=9)
            self.assertAlmostEqual(sr["reflected"][key], 1.0, places=9)
        self.assertAlmostEqual(sr["reflected"]["M2"], 3.0, places=9)

    def test_incident_key_matches_oblique_shock_state(self):
        """Step 5 of the SKILL.md workflow: the incident dict carried by
        shock_reflection equals the standalone oblique_shock_state solve
        at the same (M1, theta), bit for bit, because the module is
        deterministic."""
        sr = r.shock_reflection(3.0, 15.0)
        self.assertEqual(sr["incident"], r.oblique_shock_state(3.0, 15.0))


class ShockReflectionMachTests(unittest.TestCase):
    """Mach reflection verdict branch (Workflow step 5)."""

    def test_mach_verdict_M1_2_theta_20(self):
        """Step 5 of the SKILL.md workflow, the mach verdict: at (2.0,
        20.0) the intermediate M2 = 1.210218 leaves a reflected-shock
        detachment limit of only 4.214110 deg, far below the required
        20 deg, so the verdict is mach with reflected None and a reason
        string that reports the detachment limit."""
        sr = r.shock_reflection(2.0, 20.0)
        self.assertEqual(sr["verdict"], "mach")
        self.assertAlmostEqual(sr["M2"], 1.210218, places=6)
        self.assertAlmostEqual(sr["theta_max_ref_deg"], 4.214110, places=6)
        self.assertIsNone(sr["reflected"])
        self.assertTrue(sr["reason"])
        self.assertIn("detachment limit", sr["reason"])

    def test_verdict_flip_regular_to_mach_at_M1_3(self):
        """Step 5 of the SKILL.md workflow, the verdict flip as the
        required deflection crosses the reflected-shock detachment limit:
        at M1 = 3.0 theta 20 deg is regular with margin +2.872253 (limit
        22.872253) while theta 25 deg is mach with margin -7.599755
        (limit 17.400245)."""
        sr20 = r.shock_reflection(3.0, 20.0)
        self.assertEqual(sr20["verdict"], "regular")
        self.assertAlmostEqual(sr20["theta_max_ref_deg"], 22.872253, places=6)
        self.assertAlmostEqual(sr20["theta_max_ref_deg"] - 20.0, 2.872253, places=6)
        sr25 = r.shock_reflection(3.0, 25.0)
        self.assertEqual(sr25["verdict"], "mach")
        self.assertAlmostEqual(sr25["theta_max_ref_deg"], 17.400245, places=6)
        self.assertAlmostEqual(sr25["theta_max_ref_deg"] - 25.0, -7.599755, places=6)
        self.assertIsNone(sr25["reflected"])

    def test_mach_at_detachment_equality_reflected_branch_skipped(self):
        """Step 5 of the SKILL.md workflow, the equality case: bisecting
        on the verdict at M1 = 3.0 between theta 20 and 25 deg locates
        the transition deflection where the required deflection equals
        the reflected-shock detachment limit; just above it the verdict
        is mach and the reflected branch is not attempted (reflected
        None), just below it the verdict is regular."""
        lo, hi = 20.0, 25.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if r.shock_reflection(3.0, mid)["verdict"] == "mach":
                hi = mid
            else:
                lo = mid
        theta_eq = 0.5 * (lo + hi)
        sr_eq = r.shock_reflection(3.0, theta_eq)
        self.assertAlmostEqual(sr_eq["theta_max_ref_deg"], theta_eq, places=8)
        sr_above = r.shock_reflection(3.0, theta_eq + 1e-6)
        self.assertEqual(sr_above["verdict"], "mach")
        self.assertIsNone(sr_above["reflected"])
        self.assertLess(sr_above["theta_max_ref_deg"] - theta_eq, 0.0)
        sr_below = r.shock_reflection(3.0, theta_eq - 1e-6)
        self.assertEqual(sr_below["verdict"], "regular")
        self.assertGreater(sr_below["theta_max_ref_deg"] - theta_eq, 0.0)

    def test_subsonic_downstream_mach_verdict(self):
        """Step 5 of the SKILL.md workflow, the M2 <= 1 branch of the
        verdict: a near-detachment weak incident shock at M1 = 1.2,
        theta 3.74698, leaves M2 = 0.994678 below Mach 1, so no
        reflected-shock detachment limit exists (theta_max_ref_deg 0.0)
        and the verdict is mach with reflected None."""
        sr = r.shock_reflection(1.2, 3.74698)
        self.assertLess(sr["M2"], 1.0)
        self.assertAlmostEqual(sr["M2"], 0.994678, places=6)
        self.assertEqual(sr["theta_max_ref_deg"], 0.0)
        self.assertEqual(sr["verdict"], "mach")
        self.assertIsNone(sr["reflected"])

    def test_detached_incident_raises_no_verdict(self):
        """Step 5 of the SKILL.md workflow, physical-input guard: a
        detached incident shock raises ValueError instead of returning a
        verdict, at (2.0, 23.0) and at (3.0, 35.0)."""
        with self.assertRaises(ValueError):
            r.shock_reflection(2.0, 23.0)
        with self.assertRaises(ValueError):
            r.shock_reflection(3.0, 35.0)

    def test_fixed_verdict_and_reason_strings(self):
        """Steps 5 and 7 of the SKILL.md workflow, reporting contract:
        every verdict is exactly the string regular or mach, and every
        mach call carries the same fixed reason string, so the report is
        deterministic."""
        sr_reg = r.shock_reflection(3.0, 15.0)
        sr_mach_a = r.shock_reflection(2.0, 20.0)
        sr_mach_b = r.shock_reflection(3.0, 25.0)
        self.assertIn(sr_reg["verdict"], ("regular", "mach"))
        self.assertIn(sr_mach_a["verdict"], ("regular", "mach"))
        self.assertEqual(sr_mach_a["reason"], sr_mach_b["reason"])


class ModuleContractTests(unittest.TestCase):
    """Module constants and determinism (all workflow steps)."""

    def test_module_constants(self):
        """Workflow steps 1 to 7 use the module constants GAMMA = 1.4 and
        SHOCK_SOLVE_TOL_RAD = 1e-13, the bisection tolerance stated in
        the SKILL.md domain reference."""
        self.assertEqual(r.GAMMA, 1.4)
        self.assertEqual(r.SHOCK_SOLVE_TOL_RAD, 1e-13)

    def test_deterministic_no_randomness(self):
        """Workflow steps 2 to 7 are deterministic: two full
        shock_reflection solves at the worked example return identical
        dicts, and the reflected shock angle is reproducible to the last
        bit."""
        a = r.shock_reflection(3.0, 15.0)
        b = r.shock_reflection(3.0, 15.0)
        self.assertEqual(a, b)
        self.assertEqual(a["reflected"], b["reflected"])

    def test_shock_angle_solver_tolerance_converges(self):
        """Workflow step 2, bisection convergence: the weak-branch shock
        angle solved for the worked example agrees with the anchor to
        far tighter than the 1e-6 assert tolerance, confirming the 1e-13
        radian bisection tolerance is active."""
        beta = r.shock_angle_weak(3.0, 15.0)
        self.assertAlmostEqual(beta, 32.240400183, places=9)

    def test_gamma_argument_defaults_to_module_constant(self):
        """Workflow step 1, the thermodynamic model: every public
        function defaults gamma to the module constant GAMMA = 1.4, so
        the default solve matches the explicit gamma solve."""
        self.assertEqual(r.shock_angle_weak(3.0, 15.0),
                         r.shock_angle_weak(3.0, 15.0, GAMMA))
        self.assertEqual(r.maximum_deflection_angle(3.0),
                         r.maximum_deflection_angle(3.0, GAMMA))
        st_default = r.oblique_shock_state(3.0, 15.0)
        st_explicit = r.oblique_shock_state(3.0, 15.0, GAMMA)
        for key in st_default:
            self.assertEqual(st_default[key], st_explicit[key])


if __name__ == "__main__":
    unittest.main()
