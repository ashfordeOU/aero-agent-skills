#!/usr/bin/env python3
"""Gate 3 contract test: classical shock-tube solver (shock-tube leaf).

Exercises scripts/shock_tube_logic.py (stdlib unittest, offline,
deterministic). Contract: docs/harness-contract.md gate 3 - from the
driver-to-driven diaphragm pressure ratio p4_p1, the driver sound-speed
ratio a4_a1 and the specific heat ratios gamma1 and gamma4, recover the
incident-shock Mach number Ms by the deterministic bisection of the
diaphragm-match residual (SKILL.md workflow step 2), then the post-shock
driven-gas ratios and region-2 absolute state (step 3), the
contact-surface velocity u2 = u3 and region-2 flow Mach number (step 4),
the driver expansion wave ratios and region-3 absolute state (step 5),
the fan head and tail wave speeds with the four-region state table
(step 6), the contact close-out identities (step 7), and the
determinism and ValueError rejection checks (step 8) that the SKILL.md
workflow closes with when it runs this contract test (step 9).

All numeric asserts are order-safe: assertAlmostEqual with an explicit
delta, or math.isclose; exact equality appears only for literal
constants and round trips exact by construction (u3 equals u2, the fan
tail speed equals u3 - a3, bit-identical determinism reruns). Air/air
workcase anchors (gamma1 = gamma4 = 1.4, R = 287.0, a4/a1 = 1, p1 =
101325 Pa, T1 = 288.15 K, p4/p1 = 40) come from the spec worked
example, prep-verified by the anchor script the spec cites; module
outputs agree with every anchor within the stated tolerance.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import shock_tube_logic as st  # noqa: E402


class ShockTubeWorkcase(unittest.TestCase):
    """Air/air worked example p4/p1 = 40 (steps 2 to 7 of the workflow)."""

    def test_workcase_incident_shock_mach(self):
        """Step 2 of the SKILL.md workflow, the deterministic bisection of
        the diaphragm-match residual, is exercised here: incident_shock_mach
        must return the incident-shock Mach number 2.057576505 for the
        driver overpressure 40 at sound-speed ratio 1, and the residual of
        the implicit shock-tube equation at that root must be below 1e-10."""
        ms = st.incident_shock_mach(40.0, 1.0)
        self.assertAlmostEqual(ms, 2.057576505, delta=1e-9)
        self.assertLess(abs(st.shock_tube_residual(ms, 40.0, 1.0)), 1e-10)

    def test_workcase_state_mach_bit_identical(self):
        """Step 2 hands Ms to step 6: the state-table incident-shock Mach
        number must equal the incident_shock_mach return value bit for bit."""
        ms = st.incident_shock_mach(40.0, 1.0)
        state = st.shock_tube_state(40.0, 1.0)
        self.assertEqual(state["Ms"], ms)

    def test_workcase_post_shock_ratios(self):
        """Step 3 of the SKILL.md workflow, the post-shock driven-gas ratios
        from normal_shock_ratios at Ms, is exercised here: p2_p1 4.772557918,
        rho2_rho1 2.751003776 and T2_T1 1.734842373, each within 1e-9."""
        s = st.shock_tube_state(40.0, 1.0)
        self.assertAlmostEqual(s["p2_p1"], 4.772557918, delta=1e-9)
        self.assertAlmostEqual(s["rho2_rho1"], 2.751003776, delta=1e-9)
        self.assertAlmostEqual(s["T2_T1"], 1.734842373, delta=1e-9)

    def test_workcase_region2_absolute_state(self):
        """Step 3 multiplies the ratios by the region-1 absolute state: p2
        483579.43 Pa, T2 499.89 K, rho2 3.370600480 kg/m3, a2 448.1716 m/s,
        and the shock speed Ws = Ms a1 = 700.1164 m/s."""
        s = st.shock_tube_state(40.0, 1.0)
        self.assertAlmostEqual(s["p2"], 483579.43, delta=1e-2)
        self.assertAlmostEqual(s["T2"], 499.89, delta=1e-2)
        self.assertAlmostEqual(s["rho2"], 3.370600480, delta=1e-6)
        self.assertAlmostEqual(s["a2"], 448.1716, delta=1e-3)
        self.assertAlmostEqual(s["a1"], 340.2626, delta=1e-3)
        self.assertAlmostEqual(s["Ms"] * s["a1"], 700.1164, delta=1e-3)
        self.assertAlmostEqual(s["rho1"], 1.225225683, delta=1e-6)

    def test_workcase_contact_velocity(self):
        """Step 4 of the SKILL.md workflow, the contact-surface velocity,
        is exercised here: u2 must be 445.6215 m/s within 1e-3, equal to
        induced_velocity at Ms and a1 within 1e-9, and equal to the closed
        form 2 a1 (Ms - 1 / Ms) / (gamma1 + 1) within 1e-9."""
        s = st.shock_tube_state(40.0, 1.0)
        self.assertAlmostEqual(s["u2"], 445.6215, delta=1e-3)
        ms = s["Ms"]
        self.assertAlmostEqual(s["u2"],
                               st.induced_velocity(ms, s["a1"]), delta=1e-9)
        closed = 2.0 * s["a1"] * (ms - 1.0 / ms) / (1.4 + 1.0)
        self.assertAlmostEqual(s["u2"], closed, delta=1e-9)

    def test_workcase_region2_flow_mach(self):
        """Step 4 closes with the region-2 lab-frame flow Mach number
        M2_lab = u2 / a2: 0.994310161 within 1e-9, exactly equal to the
        division it is built from, and subsonic as the shocked driven
        stream requires."""
        s = st.shock_tube_state(40.0, 1.0)
        self.assertAlmostEqual(s["M2_lab"], 0.994310161, delta=1e-9)
        self.assertEqual(s["M2_lab"], s["u2"] / s["a2"])
        self.assertLess(s["M2_lab"], 1.0)

    def test_workcase_driver_expansion_ratios(self):
        """Step 5 of the SKILL.md workflow, the driver expansion wave
        ratios, is exercised here: p3_p4 0.119313948, T3_T4 0.544750315
        and rho3_rho4 0.219025019, each within 1e-9, with T3_T4 equal to
        the square of the expansion bracket 1 - (gamma4 - 1) u3 / (2 a4)."""
        s = st.shock_tube_state(40.0, 1.0)
        self.assertAlmostEqual(s["p3_p4"], 0.119313948, delta=1e-9)
        self.assertAlmostEqual(s["T3_T4"], 0.544750315, delta=1e-9)
        self.assertAlmostEqual(s["rho3_rho4"], 0.219025019, delta=1e-9)
        bracket = 1.0 - 0.4 * s["u3"] / (2.0 * s["a4"])
        self.assertAlmostEqual(s["T3_T4"], bracket * bracket, delta=1e-15)

    def test_workcase_region3_absolute_state(self):
        """Step 5 multiplies the driver ratios by the region-4 state: p3
        483579.43 Pa, T3 156.97 K, rho3 10.734203118 kg/m3, a3 251.1383
        m/s, with the region-3 flow Mach number M3_lab 1.774406595 within
        1e-9 and exactly u3 / a3."""
        s = st.shock_tube_state(40.0, 1.0)
        self.assertAlmostEqual(s["p3"], 483579.43, delta=1e-2)
        self.assertAlmostEqual(s["T3"], 156.97, delta=1e-2)
        self.assertAlmostEqual(s["rho3"], 10.734203118, delta=1e-6)
        self.assertAlmostEqual(s["a3"], 251.1383, delta=1e-3)
        self.assertAlmostEqual(s["M3_lab"], 1.774406595, delta=1e-9)
        self.assertEqual(s["M3_lab"], s["u3"] / s["a3"])
        self.assertGreater(s["M3_lab"], 1.0)

    def test_workcase_region4_state(self):
        """Step 6 of the SKILL.md workflow assembles the four-region state
        table from shock_tube_state: region 4 holds p4 4053000.00 Pa, T4
        288.15 K (the a4/a1 = 1, equal-gamma driver runs at T1) and rho4
        49.009027310 kg/m3 at rest."""
        s = st.shock_tube_state(40.0, 1.0)
        self.assertEqual(s["p4"], 4053000.0)
        self.assertEqual(s["T4"], 288.15)
        self.assertAlmostEqual(s["rho4"], 49.009027310, delta=1e-6)
        self.assertEqual(s["u3"], s["u2"])

    def test_workcase_fan_wave_speeds(self):
        """Step 6 reads the expansion wave speeds from the state dict: the
        fan head speed fan_head_speed = a4 = 340.2626 m/s into the
        quiescent driver gas and the fan tail speed fan_tail_speed = u3 - a3
        = 194.4832 m/s, exact by construction and within 1e-3 of the
        worked example."""
        s = st.shock_tube_state(40.0, 1.0)
        self.assertEqual(s["fan_head_speed"], s["a4"])
        self.assertEqual(s["fan_tail_speed"], s["u3"] - s["a3"])
        self.assertAlmostEqual(s["fan_head_speed"], 340.2626, delta=1e-3)
        self.assertAlmostEqual(s["fan_tail_speed"], 194.4832, delta=1e-3)

    def test_state_dict_keys_exact(self):
        """Step 6 hands over the four-region state table: shock_tube_state
        must carry exactly the 29 documented keys, no more and no fewer."""
        s = st.shock_tube_state(40.0, 1.0)
        expected = {"Ms", "p2_p1", "rho2_rho1", "T2_T1", "u2", "p2", "T2",
                    "rho2", "a2", "M2_lab", "a1", "rho1", "p1", "p3_p4",
                    "T3_T4", "rho3_rho4", "p3", "T3", "rho3", "a3",
                    "M3_lab", "u3", "p4", "T4", "rho4", "a4",
                    "fan_head_speed", "fan_tail_speed", "residual"}
        self.assertEqual(set(s.keys()), expected)

    def test_contact_surface_close_out(self):
        """Step 7 of the SKILL.md workflow, the contact close-out, is
        exercised here: at the bisected root the contact-surface match is
        exact, p3 - p2 below 1e-6 Pa, u3 - u2 exactly 0.0 in the state
        dict, and p3_p4 times p4_p1 equals p2_p1 within 1e-9."""
        s = st.shock_tube_state(40.0, 1.0)
        self.assertLess(abs(s["p3"] - s["p2"]), 1e-6)
        self.assertEqual(s["u3"] - s["u2"], 0.0)
        self.assertLess(abs(s["p3_p4"] * 40.0 - s["p2_p1"]), 1e-9)
        self.assertLess(abs(s["residual"]), 1e-10)

    def test_ideal_gas_identity(self):
        """Step 7 checks the ideal-gas identity p / (rho R T) = 1.0 in the
        region-2 and region-3 absolute states within 1e-9."""
        s = st.shock_tube_state(40.0, 1.0)
        self.assertAlmostEqual(s["p2"] / (s["rho2"] * 287.0 * s["T2"]),
                               1.0, delta=1e-9)
        self.assertAlmostEqual(s["p3"] / (s["rho3"] * 287.0 * s["T3"]),
                               1.0, delta=1e-9)

    def test_shock_frame_mn2_recovery(self):
        """Step 7 cross-checks the shock frame: the shock-relative downstream
        Mach number Mn2 = sqrt((1 + (gamma1 - 1) Ms^2 / 2) / (gamma1 Ms^2 -
        (gamma1 - 1) / 2)) is 0.567851523 within 1e-9, and u2 recovered as
        Ms a1 - Mn2 a2 equals the state u2 within 1e-6."""
        s = st.shock_tube_state(40.0, 1.0)
        ms = s["Ms"]
        mn2 = math.sqrt((1.0 + 0.4 * ms * ms / 2.0) /
                        (1.4 * ms * ms - 0.4 / 2.0))
        self.assertAlmostEqual(mn2, 0.567851523, delta=1e-9)
        self.assertAlmostEqual(s["u2"], ms * s["a1"] - mn2 * s["a2"],
                               delta=1e-6)

    def test_p2_p1_closed_form(self):
        """Step 7 verifies p2_p1 from the state equals the closed form
        1 + 2 gamma1 (Ms^2 - 1) / (gamma1 + 1) within 1e-12."""
        s = st.shock_tube_state(40.0, 1.0)
        closed = 1.0 + 2.0 * 1.4 * (s["Ms"] * s["Ms"] - 1.0) / 2.4
        self.assertAlmostEqual(s["p2_p1"], closed, delta=1e-12)


class ShockTubeDriverFamily(unittest.TestCase):
    """Driver-strength family air/air at a4/a1 = 1 (steps 2 to 6)."""

    def test_driver_family_incident_mach(self):
        """Step 2, the incident_shock_mach bisection, is exercised across
        the driver-strength family: Ms anchors 1.039831292 (p4/p1 = 1.2),
        1.159478862 (2.0), 1.402408030 (5.0), 1.607525211 (10.0),
        2.371054059 (100.0) and 3.150486214 (1000.0), each within 1e-9,
        and strictly increasing with the driver overpressure."""
        anchors = {1.2: 1.039831292, 2.0: 1.159478862, 5.0: 1.402408030,
                   10.0: 1.607525211, 100.0: 2.371054059,
                   1000.0: 3.150486214}
        machs = []
        for ratio, anchor in sorted(anchors.items()):
            ms = st.incident_shock_mach(ratio, 1.0)
            self.assertAlmostEqual(ms, anchor, delta=1e-9)
            machs.append(ms)
        for higher, lower in zip(machs[1:], machs):
            self.assertGreater(higher, lower)

    def test_driver_family_contact_velocity(self):
        """Step 4, induced_velocity at each family Ms, is exercised here:
        u2 matches the worked-example rows 22.1559, 84.2214, 195.4664,
        279.4268, 552.7285 and 803.3246 m/s (printed to 1e-4, so relative
        tolerance 1e-5) and grows strictly with the driver overpressure."""
        anchors = {1.2: 22.1559, 2.0: 84.2214, 5.0: 195.4664,
                   10.0: 279.4268, 100.0: 552.7285, 1000.0: 803.3246}
        speeds = []
        for ratio, anchor in sorted(anchors.items()):
            u2 = st.shock_tube_state(ratio, 1.0)["u2"]
            self.assertTrue(math.isclose(u2, anchor, rel_tol=1e-5),
                            msg="u2 {} vs anchor {}".format(u2, anchor))
            speeds.append(u2)
        for higher, lower in zip(speeds[1:], speeds):
            self.assertGreater(higher, lower)

    def test_driver_family_states(self):
        """Steps 3 and 5 build the family states: p2_p1 anchors 1.094790636
        (p4/p1 = 1.2) and 1.401789770 (2.0) within 1e-9 (the 2.0 row is the
        standard chart value p2/p1 ~ 1.40 at Ms ~ 1.16), and the T2 rows
        295.71, 317.70, 361.99, 401.44, 580.01 and 824.23 K within
        relative tolerance 1e-5."""
        p21_anchors = {1.2: 1.094790636, 2.0: 1.401789770}
        t2_anchors = {1.2: 295.71, 2.0: 317.70, 5.0: 361.99, 10.0: 401.44,
                      100.0: 580.01, 1000.0: 824.23}
        for ratio, anchor in p21_anchors.items():
            self.assertAlmostEqual(st.shock_tube_state(ratio, 1.0)["p2_p1"],
                                   anchor, delta=1e-9)
        s2 = st.shock_tube_state(2.0, 1.0)
        self.assertTrue(math.isclose(s2["p2_p1"], 1.40, rel_tol=1e-2),
                        msg="chart cross-check p2_p1 ~ 1.40")
        for ratio, anchor in t2_anchors.items():
            t2 = st.shock_tube_state(ratio, 1.0)["T2"]
            self.assertTrue(math.isclose(t2, anchor, rel_tol=1e-5),
                            msg="T2 {} vs anchor {}".format(t2, anchor))

    def test_family_expansion_velocity_within_limit(self):
        """Step 2 keeps every family root under the ceiling: even p4/p1 =
        1000 gives Ms = 3.150486214, far inside the air/air ceiling
        Ms_lim = 6.162277660, approached only as p4_p1 grows without
        bound."""
        ceiling = (6.0 + math.sqrt(6.0 * 6.0 + 4.0)) / 2.0
        self.assertAlmostEqual(ceiling, 6.16227766016838, delta=1e-9)
        self.assertLess(st.incident_shock_mach(1000.0, 1.0), ceiling)
        self.assertLess(st.incident_shock_mach(1000.0, 1.0), 0.55 * ceiling)


class ShockTubeGeneralGamma(unittest.TestCase):
    """Helium driver over air, gamma4 = 5/3, a4/a1 = 2.4 (steps 2, 3, 5)."""

    def test_general_gamma_incident_mach(self):
        """Step 2 with a light fast driver: incident_shock_mach(40.0, 2.4,
        1.4, 5.0 / 3.0) returns Ms 2.698174185 within 1e-9, above the
        air/air value at the same diaphragm pressure ratio."""
        ms = st.incident_shock_mach(40.0, 2.4, 1.4, 5.0 / 3.0)
        self.assertAlmostEqual(ms, 2.698174185, delta=1e-9)
        self.assertGreater(ms, st.incident_shock_mach(40.0, 1.0))

    def test_general_gamma_state(self):
        """Steps 3 and 5 with differing heat ratios: p2_p1 8.326834585 and
        T2_T1 2.340950220 within 1e-9, u2 659.9828 m/s within 1e-3, p3_p4
        0.208170865 within 1e-9 and T3 744.20 K within relative 1e-5."""
        s = st.shock_tube_state(40.0, 2.4, 1.4, 5.0 / 3.0)
        self.assertAlmostEqual(s["p2_p1"], 8.326834585, delta=1e-9)
        self.assertAlmostEqual(s["T2_T1"], 2.340950220, delta=1e-9)
        self.assertAlmostEqual(s["u2"], 659.9828, delta=1e-3)
        self.assertAlmostEqual(s["p3_p4"], 0.208170865, delta=1e-9)
        self.assertTrue(math.isclose(s["T3"], 744.20, rel_tol=1e-5))
        self.assertLess(abs(s["p3"] - s["p2"]), 1e-6)


class ShockTubeValueErrors(unittest.TestCase):
    """ValueError rejection of non-physical inputs (workflow step 8)."""

    def test_p4_p1_must_exceed_one(self):
        """Step 8 rejection: a driver overpressure is required, so p4_p1 =
        1.0 and below raise ValueError in incident_shock_mach and
        shock_tube_state."""
        for bad in (1.0, 0.5, 0.0, -3.0):
            with self.assertRaises(ValueError):
                st.incident_shock_mach(bad, 1.0)
            with self.assertRaises(ValueError):
                st.shock_tube_state(bad, 1.0)

    def test_a4_a1_must_be_positive(self):
        """Step 8 rejection: a zero or negative driver sound-speed ratio
        raises ValueError in the bisection entry points."""
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                st.incident_shock_mach(40.0, bad)
            with self.assertRaises(ValueError):
                st.shock_tube_state(40.0, bad)
            with self.assertRaises(ValueError):
                st.shock_tube_residual(2.0, 40.0, bad)

    def test_gamma_ratios_must_exceed_one(self):
        """Step 8 rejection: gamma1 = 1.0 and gamma4 = 1.0 both raise, and
        so does normal_shock_ratios at gamma = 1.0."""
        with self.assertRaises(ValueError):
            st.incident_shock_mach(40.0, 1.0, gamma1=1.0)
        with self.assertRaises(ValueError):
            st.incident_shock_mach(40.0, 1.0, gamma4=1.0)
        with self.assertRaises(ValueError):
            st.shock_tube_state(40.0, 1.0, gamma4=1.0)
        with self.assertRaises(ValueError):
            st.normal_shock_ratios(2.0, gamma=1.0)

    def test_absolute_state_inputs_positive(self):
        """Step 8 rejection: p1 = 0, t1 = 0 and r_gas = 0 each raise
        ValueError in shock_tube_state before any bisection runs."""
        with self.assertRaises(ValueError):
            st.shock_tube_state(40.0, p1=0.0)
        with self.assertRaises(ValueError):
            st.shock_tube_state(40.0, t1=0.0)
        with self.assertRaises(ValueError):
            st.shock_tube_state(40.0, r_gas=0.0)
        with self.assertRaises(ValueError):
            st.shock_tube_state(40.0, p1=-101325.0)

    def test_component_value_errors(self):
        """Step 8 rejection in the component relations: the expansion
        pressure ratio raises past the full-expansion limit (u_over_a4 =
        5.0 at gamma4 = 1.4) and at gamma4 = 1.0, normal_shock_ratios
        raises at shock_mach = 1.0, and induced_velocity raises at
        shock_mach = 1.0 and at a1 = 0."""
        with self.assertRaises(ValueError):
            st.expansion_pressure_ratio(5.0, 1.4)
        with self.assertRaises(ValueError):
            st.expansion_pressure_ratio(0.5, 1.0)
        with self.assertRaises(ValueError):
            st.normal_shock_ratios(1.0)
        with self.assertRaises(ValueError):
            st.induced_velocity(1.0, 340.0)
        with self.assertRaises(ValueError):
            st.induced_velocity(2.0, 0.0)
        with self.assertRaises(ValueError):
            st.normal_shock_ratios(1.5, gamma=0.5)

    def test_expansion_ratio_literal_limits(self):
        """Step 5 boundary: the expansion pressure ratio is exactly 1.0 at
        u_over_a4 = 0 (still driver gas), stays positive just inside the
        full-expansion limit, and the near-limit value is below one."""
        self.assertEqual(st.expansion_pressure_ratio(0.0, 1.4), 1.0)
        near = st.expansion_pressure_ratio(4.9, 1.4)
        self.assertGreater(near, 0.0)
        self.assertLess(near, 1.0)


class ShockTubeDeterminism(unittest.TestCase):
    """Determinism and closed-form consistency (workflow step 8)."""

    def test_rerun_bit_identical(self):
        """Step 8 determinism: two calls of incident_shock_mach on the same
        input return identical bits, and two shock_tube_state calls return
        equal dicts (no RNG, pure math, fixed iteration count)."""
        m1 = st.incident_shock_mach(40.0, 1.0)
        m2 = st.incident_shock_mach(40.0, 1.0)
        self.assertEqual(m1, m2)
        s1 = st.shock_tube_state(40.0, 1.0)
        s2 = st.shock_tube_state(40.0, 1.0)
        self.assertEqual(s1, s2)
        self.assertEqual(st.incident_shock_mach(2.0, 1.0),
                         st.incident_shock_mach(2.0, 1.0))

    def test_normal_shock_ratios_consistency(self):
        """Step 3 consistency: inside normal_shock_ratios the temperature
        ratio is p2_p1 divided by rho2_rho1, and both ratios grow with the
        incident-shock Mach number."""
        r_weak = st.normal_shock_ratios(1.5)
        r_strong = st.normal_shock_ratios(3.0)
        self.assertEqual(r_weak["T2_T1"],
                         r_weak["p2_p1"] / r_weak["rho2_rho1"])
        self.assertGreater(r_strong["p2_p1"], r_weak["p2_p1"])
        self.assertGreater(r_strong["rho2_rho1"], r_weak["rho2_rho1"])
        self.assertGreater(r_strong["T2_T1"], r_weak["T2_T1"])
        self.assertGreater(r_strong["p2_p1"], 1.0)

    def test_region4_scales_with_overpressure(self):
        """Step 6 consistency for an equal-gamma driver at a4/a1 = 1: the
        region-4 density equals the overpressure times the region-1 density
        (same gas constant, T4 = T1) within 1e-9 relative."""
        s = st.shock_tube_state(40.0, 1.0)
        self.assertTrue(math.isclose(s["rho4"], 40.0 * s["rho1"],
                                     rel_tol=1e-9))
        self.assertEqual(s["a4"], s["a1"])

    def test_induced_velocity_positive_and_bounded(self):
        """Step 4 sanity: the contact-surface velocity is positive for any
        overpressure and always outrun by the shock itself, so u2 stays
        below the shock speed Ms a1 and the shock-frame downstream Mach
        number (Ms a1 - u2) / a2 stays below one even when the lab-frame
        flow turns supersonic behind a strong shock."""
        s = st.shock_tube_state(100.0, 1.0)
        self.assertGreater(s["u2"], 0.0)
        self.assertLess(s["u2"], s["Ms"] * s["a1"])
        self.assertLess((s["Ms"] * s["a1"] - s["u2"]) / s["a2"], 1.0)


if __name__ == "__main__":
    unittest.main()
