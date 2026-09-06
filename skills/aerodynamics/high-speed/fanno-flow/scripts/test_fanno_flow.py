"""Contract test for the fanno-flow leaf (aerodynamics/high-speed/fanno-flow).

Exercises the SKILL.md workflow end to end: step 2 (evaluate the
Fanno-line integral fL*/D from the inlet Mach), step 3 (compute the
friction-duct choking length), step 4 (form the segment friction
parameter fL/D and recover the downstream Mach number on the inlet
branch), step 5 (read the starred total-pressure and static ratios to
the sonic state), step 6 (assemble the duct state across the segment:
the p02/p01 total-pressure loss, the static p2/p1, T2/T1, rho2/rho1
quotients, the entropy rise and the adiabatic T02/T01 check), and step 7
(find the friction required to choke the duct). All numeric asserts are
tolerance-based (delta or isclose) so the test passes identically under
the pre-push pyenv 3.13.12 interpreter and the system python3. Offline,
deterministic, no imports beyond math and the leaf module.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fanno_flow_logic import (  # noqa: E402
    BISECT_TOL,
    GAMMA,
    MAX_ITER,
    choke_length,
    downstream_mach,
    duct_state,
    fanno_function,
    friction_to_choke,
    static_ratios,
    total_pressure_ratio,
)


class FannoFunctionTests(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: the Fanno-line integral fL*/D."""

    def test_fanno_function_subsonic_anchors(self):
        """Step 2 fL*/D evaluation: subsonic Fanno table anchors 0.3 to 0.95."""
        self.assertAlmostEqual(fanno_function(0.3), 5.299253105091, delta=1e-5)
        self.assertAlmostEqual(fanno_function(0.5), 1.069060312718, delta=1e-5)
        self.assertAlmostEqual(fanno_function(0.8), 0.072289972363, delta=1e-6)
        self.assertAlmostEqual(fanno_function(0.95), 0.003278221120, delta=1e-6)

    def test_fanno_function_sonic_zero(self):
        """Step 2 check: phi vanishes at the sonic state M = 1."""
        self.assertAlmostEqual(fanno_function(1.0), 0.0, delta=1e-12)

    def test_fanno_function_supersonic_anchors(self):
        """Step 2 fL*/D evaluation: supersonic Fanno table anchors 1.2 to 10."""
        self.assertAlmostEqual(fanno_function(1.2), 0.033638068346, delta=1e-6)
        self.assertAlmostEqual(fanno_function(2.0), 0.304996502581, delta=1e-5)
        self.assertAlmostEqual(fanno_function(3.0), 0.522159408179, delta=1e-5)
        self.assertAlmostEqual(fanno_function(5.0), 0.693803924944, delta=1e-5)
        self.assertAlmostEqual(fanno_function(10.0), 0.786830832907, delta=1e-5)

    def test_fanno_function_textbook_table_row(self):
        """Step 2 Fanno table cross-check: 1.0691 at 0.5, 0.3050 at 2.0."""
        self.assertAlmostEqual(fanno_function(0.5), 1.0691, delta=1e-4)
        self.assertAlmostEqual(fanno_function(2.0), 0.3050, delta=1e-4)
        self.assertAlmostEqual(fanno_function(3.0), 0.5222, delta=1e-4)

    def test_fanno_function_gamma_parameter_honored(self):
        """Step 2 gas parameter: gamma defaults to 1.4 but is honored."""
        self.assertAlmostEqual(fanno_function(2.0), 0.304996502581, delta=1e-5)
        self.assertAlmostEqual(fanno_function(2.0, 1.3), 0.357277365682, delta=1e-5)

    def test_fanno_function_branch_monotonicity(self):
        """Step 2 monotonicity: phi falls on (0, 1), rises on (1, inf)."""
        grid = [0.05, 0.1, 0.3, 0.5, 0.8, 0.95, 1.0, 1.2, 2.0, 3.0, 5.0, 10.0]
        vals = [fanno_function(m) for m in grid]
        subsonic = [vals[i] for i in range(len(grid)) if grid[i] < 1.0]
        supersonic = [vals[i] for i in range(len(grid)) if grid[i] > 1.0]
        for a, b in zip(subsonic, subsonic[1:]):
            self.assertGreater(a, b)
        for a, b in zip(supersonic, supersonic[1:]):
            self.assertLess(a, b)
        self.assertAlmostEqual(min(vals), 0.0, delta=1e-15)  # the zero sits at M = 1

    def test_fanno_function_valueerror_nonphysical(self):
        """Step 2 guard: non-positive Mach and gamma at one raise ValueError."""
        for mach in (0.0, -0.5):
            with self.assertRaises(ValueError):
                fanno_function(mach)
        with self.assertRaises(ValueError):
            fanno_function(0.5, 1.0)

    def test_module_constants_pinned(self):
        """Determinism setup: the gamma default and bisection bounds."""
        self.assertEqual(GAMMA, 1.4)
        self.assertEqual(BISECT_TOL, 1e-12)
        self.assertEqual(MAX_ITER, 200)


class TotalPressureRatioTests(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: p0/p0* to the sonic reference."""

    def test_total_pressure_ratio_anchors(self):
        """Step 5 starred total-pressure read: p0/p0* table anchors."""
        self.assertAlmostEqual(total_pressure_ratio(0.3), 2.035065262346, delta=1e-5)
        self.assertAlmostEqual(total_pressure_ratio(0.5), 1.339843750000, delta=1e-5)
        self.assertAlmostEqual(total_pressure_ratio(1.0), 1.000000000000, delta=1e-12)
        self.assertAlmostEqual(total_pressure_ratio(1.5), 1.176167052469, delta=1e-5)
        self.assertAlmostEqual(total_pressure_ratio(2.0), 1.687500000000, delta=1e-6)
        self.assertAlmostEqual(total_pressure_ratio(3.0), 4.234567901235, delta=1e-5)

    def test_total_pressure_ratio_minimal_at_sonic(self):
        """Step 5 loss bookkeeping: p0/p0* is minimal (1.0) at the sonic state."""
        self.assertGreater(total_pressure_ratio(0.9), 1.0)
        self.assertGreater(total_pressure_ratio(1.1), 1.0)
        self.assertGreater(total_pressure_ratio(0.3), total_pressure_ratio(0.9))
        self.assertGreater(total_pressure_ratio(3.0), total_pressure_ratio(1.1))

    def test_total_pressure_ratio_valueerror(self):
        """Step 5 guard: a negative Mach raises ValueError."""
        with self.assertRaises(ValueError):
            total_pressure_ratio(-2.0)


class StaticRatiosTests(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: T/T*, p/p*, rho/rho* at a station."""

    def test_static_ratios_subsonic_row(self):
        """Step 5 starred static read at M = 0.3, the subsonic table row."""
        r = static_ratios(0.3)
        self.assertAlmostEqual(r["T_Tstar"], 1.178781925344, delta=1e-5)
        self.assertAlmostEqual(r["p_pstar"], 3.619057466836, delta=1e-5)
        self.assertAlmostEqual(r["rho_rhostar"], 3.070167084366, delta=1e-5)

    def test_static_ratios_supersonic_row(self):
        """Step 5 starred static read at M = 2.0, the supersonic table row."""
        r = static_ratios(2.0)
        self.assertAlmostEqual(r["T_Tstar"], 0.666666666667, delta=1e-6)
        self.assertAlmostEqual(r["p_pstar"], 0.408248290464, delta=1e-6)
        self.assertAlmostEqual(r["rho_rhostar"], 0.612372435696, delta=1e-6)

    def test_static_ratios_consistent_identity(self):
        """Step 5 consistency: p/p* equals (rho/rho*)(T/T*) to 1e-12."""
        r = static_ratios(0.5)
        product = r["rho_rhostar"] * r["T_Tstar"]
        self.assertAlmostEqual(product, 2.138089935299, delta=1e-12)
        self.assertAlmostEqual(r["p_pstar"], product, delta=1e-12)
        for mach in (0.3, 0.9, 1.5, 2.0, 5.0):
            r = static_ratios(mach)
            self.assertAlmostEqual(
                r["p_pstar"], r["rho_rhostar"] * r["T_Tstar"], delta=1e-12
            )

    def test_static_ratios_sonic_unity(self):
        """Step 5 reference state: every starred static ratio is 1.0 at M = 1."""
        r = static_ratios(1.0)
        self.assertAlmostEqual(r["T_Tstar"], 1.0, delta=1e-12)
        self.assertAlmostEqual(r["p_pstar"], 1.0, delta=1e-12)
        self.assertAlmostEqual(r["rho_rhostar"], 1.0, delta=1e-12)

    def test_static_ratios_valueerror_gamma(self):
        """Step 5 guard: gamma at one raises ValueError."""
        with self.assertRaises(ValueError):
            static_ratios(2.0, 1.0)


class ChokeLengthTests(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: the friction-duct choking length."""

    def test_choke_length_subsonic_anchor(self):
        """Step 3 choke-length run: L* = 105.985 m for the M = 0.3 duct."""
        self.assertAlmostEqual(choke_length(0.3, 0.005, 0.1), 105.985062101823, delta=1e-3)

    def test_choke_length_supersonic_shorter(self):
        """Step 3 choke-length run: the M = 2.0 duct chokes seventeen times sooner."""
        l_sub = choke_length(0.3, 0.005, 0.1)
        l_sup = choke_length(2.0, 0.005, 0.1)
        self.assertAlmostEqual(l_sup, 6.099930051630, delta=1e-4)
        self.assertLess(l_sup, l_sub)
        self.assertAlmostEqual(l_sub / l_sup, 17.37, delta=0.02)

    def test_choke_length_sonic_already_choked(self):
        """Step 3 edge: a sonic inlet is already choked, L* is exactly 0.0."""
        self.assertAlmostEqual(choke_length(1.0, 0.005, 0.1), 0.0, delta=1e-12)

    def test_choke_length_closed_form_identity(self):
        """Step 3 consistency: L* equals D times phi(M) over the Fanning factor."""
        for mach, f, d in ((0.3, 0.005, 0.1), (2.0, 0.005, 0.1), (0.6, 0.002, 0.05)):
            self.assertAlmostEqual(
                choke_length(mach, f, d),
                d * fanno_function(mach) / f,
                delta=1e-9,
            )

    def test_choke_length_valueerror_nonphysical(self):
        """Step 3 guard: zero friction or diameter raises ValueError."""
        with self.assertRaises(ValueError):
            choke_length(0.3, 0.0, 0.1)
        with self.assertRaises(ValueError):
            choke_length(0.3, 0.005, 0.0)
        with self.assertRaises(ValueError):
            choke_length(0.3, -0.005, 0.1)


class DownstreamMachTests(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: recover the downstream Mach number."""

    def test_downstream_mach_subsonic_acceleration(self):
        """Step 4 subsonic branch: friction accelerates M = 0.3 to 0.375749."""
        m2 = downstream_mach(0.3, 2.5)
        self.assertAlmostEqual(m2, 0.375749134774, delta=1e-5)
        self.assertGreater(m2, 0.3)
        self.assertLess(m2, 1.0)

    def test_downstream_mach_supersonic_deceleration(self):
        """Step 4 supersonic branch: friction decelerates M = 2.0 to 1.552005."""
        m2 = downstream_mach(2.0, 0.15)
        self.assertAlmostEqual(m2, 1.552005392004, delta=1e-5)
        self.assertGreater(m2, 1.0)
        self.assertLess(m2, 2.0)

    def test_downstream_mach_round_trip_residual(self):
        """Step 4 margin bookkeeping: phi(M2) + fL/D - phi(M1) is below 1e-9."""
        m_sub = downstream_mach(0.3, 2.5)
        res_sub = fanno_function(m_sub) + 2.5 - fanno_function(0.3)
        self.assertLess(abs(res_sub), 1e-9)
        m_sup = downstream_mach(2.0, 0.15)
        res_sup = fanno_function(m_sup) + 0.15 - fanno_function(2.0)
        self.assertLess(abs(res_sup), 1e-9)

    def test_downstream_mach_margin_to_sonic(self):
        """Step 4 choke margin: phi(M2) equals phi(M1) minus the fL/D spent."""
        m_sub = downstream_mach(0.3, 2.5)
        self.assertAlmostEqual(
            fanno_function(m_sub), 5.299253105091 - 2.5, delta=1e-9
        )
        self.assertAlmostEqual(fanno_function(m_sub), 2.799253105091, delta=1e-9)
        m_sup = downstream_mach(2.0, 0.15)
        self.assertAlmostEqual(fanno_function(m_sup), 0.154996502581, delta=1e-9)

    def test_downstream_mach_zero_friction_limit(self):
        """Step 4 no-friction limit: a zero fL/D segment leaves the Mach intact."""
        self.assertAlmostEqual(downstream_mach(0.3, 0.0), 0.3, delta=1e-9)
        self.assertAlmostEqual(downstream_mach(2.0, 0.0), 2.0, delta=1e-9)

    def test_downstream_mach_deterministic_bits(self):
        """Step 4 determinism: identical inputs return identical bits."""
        self.assertEqual(downstream_mach(0.3, 2.5), downstream_mach(0.3, 2.5))
        self.assertEqual(downstream_mach(2.0, 0.15), downstream_mach(2.0, 0.15))

    def test_downstream_mach_valueerror_choking_fld(self):
        """Step 4 guard: fL/D at or above the choke value phi(M1) raises."""
        with self.assertRaises(ValueError):
            downstream_mach(0.3, -1.0)  # negative friction parameter
        with self.assertRaises(ValueError):
            downstream_mach(0.3, 5.3)  # at/above phi(0.3) = 5.299253105091
        with self.assertRaises(ValueError):
            downstream_mach(2.0, 0.3050)  # at/above phi(2.0) = 0.304996502581

    def test_downstream_mach_valueerror_sonic_inlet(self):
        """Step 4 guard: a sonic inlet (M1 = 1) has no duct inversion."""
        with self.assertRaises(ValueError):
            downstream_mach(1.0, 0.1)


class FrictionToChokeTests(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: the friction required to choke."""

    def test_friction_to_choke_anchors(self):
        """Step 7 f_req read: 0.010599 for the 50 m M = 0.3 duct, 0.010167 for 3 m M = 2."""
        self.assertAlmostEqual(friction_to_choke(0.3, 50, 0.1), 0.010598506210, delta=1e-6)
        self.assertAlmostEqual(friction_to_choke(2.0, 3, 0.1), 0.010166550086, delta=1e-6)

    def test_friction_to_choke_consistency(self):
        """Step 7 choke consistency: f_req times L/D reproduces phi(M1)."""
        for mach, length, d in ((0.3, 50, 0.1), (2.0, 3, 0.1), (0.5, 10, 0.2)):
            f_req = friction_to_choke(mach, length, d)
            self.assertAlmostEqual(f_req * length / d, fanno_function(mach), delta=1e-9)

    def test_friction_to_choke_valueerror(self):
        """Step 7 guard: zero duct length or diameter raises ValueError."""
        with self.assertRaises(ValueError):
            friction_to_choke(0.3, 0.0, 0.1)
        with self.assertRaises(ValueError):
            friction_to_choke(0.3, 50, 0.0)


class DuctStateTests(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: the duct state across a segment."""

    def test_duct_state_subsonic_50m_segment(self):
        """Step 6 subsonic duct state: the 50 m M = 0.3 run loses 17.7% of p0."""
        s = duct_state(0.3, 2.5)
        self.assertAlmostEqual(s["mach_out"], 0.375749134774, delta=1e-5)
        self.assertAlmostEqual(s["p02_over_p01"], 0.822735477531, delta=1e-5)
        self.assertAlmostEqual(s["p2_over_p1"], 0.794420493240, delta=1e-5)
        self.assertAlmostEqual(s["T2_over_T1"], 0.990043659533, delta=1e-5)
        self.assertAlmostEqual(s["rho2_over_rho1"], 0.802409555973, delta=1e-5)

    def test_duct_state_subsonic_station_references(self):
        """Step 6 subsonic read-off: exit p0/p0* 1.6743 and entropy rise 0.1951."""
        m2 = downstream_mach(0.3, 2.5)
        self.assertAlmostEqual(total_pressure_ratio(m2), 1.674320390423, delta=1e-5)
        self.assertAlmostEqual(
            total_pressure_ratio(m2) / total_pressure_ratio(0.3),
            0.822735477531,
            delta=1e-5,
        )
        self.assertAlmostEqual(
            -math.log(duct_state(0.3, 2.5)["p02_over_p01"]), 0.195120542447, delta=1e-5
        )

    def test_duct_state_supersonic_3m_segment(self):
        """Step 6 supersonic duct state: the 3 m M = 2.0 run loses 28.1% of p0."""
        s = duct_state(2.0, 0.15)
        self.assertAlmostEqual(s["mach_out"], 1.552005392004, delta=1e-5)
        self.assertAlmostEqual(s["p02_over_p01"], 0.718851057841, delta=1e-5)
        self.assertAlmostEqual(s["p2_over_p1"], 1.420320685669, delta=1e-5)
        self.assertAlmostEqual(s["T2_over_T1"], 1.214784619331, delta=1e-5)
        self.assertAlmostEqual(s["rho2_over_rho1"], 1.169195479649, delta=1e-5)

    def test_duct_state_supersonic_station_references(self):
        """Step 6 supersonic read-off: exit p0/p0* 1.2131 and entropy rise 0.3301."""
        m2 = downstream_mach(2.0, 0.15)
        self.assertAlmostEqual(total_pressure_ratio(m2), 1.213061160106, delta=1e-5)
        self.assertAlmostEqual(
            total_pressure_ratio(m2) / total_pressure_ratio(2.0),
            0.718851057841,
            delta=1e-5,
        )
        self.assertAlmostEqual(
            -math.log(duct_state(2.0, 0.15)["p02_over_p01"]), 0.330101094541, delta=1e-5
        )

    def test_duct_state_loss_signs_both_branches(self):
        """Step 6 loss direction: p02/p01 below 1 and entropy rise above 0."""
        for mach_in, fld in ((0.3, 2.5), (2.0, 0.15), (0.5, 0.5), (1.5, 0.05)):
            s = duct_state(mach_in, fld)
            self.assertLess(s["p02_over_p01"], 1.0)
            self.assertGreater(-math.log(s["p02_over_p01"]), 0.0)

    def test_duct_state_adiabatic_total_temperature(self):
        """Step 6 adiabatic check: T02/T01 equals 1.0 to within 1e-9."""
        for mach_in, fld in ((0.3, 2.5), (2.0, 0.15)):
            m2 = downstream_mach(mach_in, fld)
            t0_in = static_ratios(mach_in)["T_Tstar"] * (1.0 + 0.2 * mach_in * mach_in)
            t0_out = static_ratios(m2)["T_Tstar"] * (1.0 + 0.2 * m2 * m2)
            self.assertAlmostEqual(t0_out / t0_in, 1.0, delta=1e-9)

    def test_duct_state_supersonic_loses_more_total_pressure(self):
        """Step 6 comparison: the supersonic run loses more p0 from far less fL/D."""
        sub = duct_state(0.3, 2.5)["p02_over_p01"]
        sup = duct_state(2.0, 0.15)["p02_over_p01"]
        self.assertLess(sup, sub)
        self.assertAlmostEqual(sub, 0.8227, delta=1e-4)
        self.assertAlmostEqual(sup, 0.7189, delta=1e-4)

    def test_duct_state_quotient_construction(self):
        """Step 6 construction: each ratio is the starred-ratio quotient of the segment."""
        for mach_in, fld in ((0.3, 2.5), (2.0, 0.15)):
            m2 = downstream_mach(mach_in, fld)
            s = duct_state(mach_in, fld)
            self.assertAlmostEqual(
                s["p02_over_p01"],
                total_pressure_ratio(m2) / total_pressure_ratio(mach_in),
                delta=1e-12,
            )
            in_s = static_ratios(mach_in)
            out_s = static_ratios(m2)
            self.assertAlmostEqual(
                s["p2_over_p1"], out_s["p_pstar"] / in_s["p_pstar"], delta=1e-12
            )
            self.assertAlmostEqual(
                s["T2_over_T1"], out_s["T_Tstar"] / in_s["T_Tstar"], delta=1e-12
            )
            self.assertAlmostEqual(
                s["rho2_over_rho1"],
                out_s["rho_rhostar"] / in_s["rho_rhostar"],
                delta=1e-12,
            )

    def test_duct_state_valueerror_propagation(self):
        """Step 6 guard: duct_state inherits the downstream_mach ValueError set."""
        with self.assertRaises(ValueError):
            duct_state(0.3, 5.3)  # friction parameter at the choke value
        with self.assertRaises(ValueError):
            duct_state(1.0, 0.1)  # sonic inlet
        with self.assertRaises(ValueError):
            duct_state(2.0, -0.1)  # negative friction parameter


if __name__ == "__main__":
    unittest.main()
