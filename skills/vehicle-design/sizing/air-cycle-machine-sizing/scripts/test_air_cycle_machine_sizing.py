"""Contract test for the air-cycle-machine-sizing leaf (wave-41).

Every method docstring names the SKILL.md Workflow step it exercises.
Workflow steps of the SKILL.md body: 1 fix the pack-inlet bleed
condition, 2 compute the compressor exit state, 3 cool the compressor
discharge through the ram-air heat exchanger, 4 expand through the
cooling turbine to cabin pressure, 5 close the ACM shaft balance, 6
resolve an open balance through the closure temperature, 7 quote the
delivered cooling and size the required bleed flow, 8 run the contract
test. Step 8 of the SKILL.md workflow, the deterministic contract test
run, is exercised by every method here through asserts on the real
module outputs at the Case A and Case B anchors of the spec, within
spec tolerances.

Run offline: python3 scripts/test_air_cycle_machine_sizing.py
"""

import unittest

from air_cycle_machine_sizing_logic import (
    compressor_exit,
    heat_exchanger_exit,
    turbine_exit,
    compressor_power,
    turbine_power,
    shaft_balance,
    t3_required_for_balance,
    hx_effectiveness_for_balance,
    cooling_capacity,
    required_bleed_flow,
)

P1 = 240000.0
T1_A = 460.0
T1_B = 340.0
PR_C = 3.0
ETA_C = 0.78
SINK = 320.0
ETA_T = 0.85
P_CABIN = 101325.0
M_DOT = 0.9
CABIN_T = 294.0
LOAD_W = 12000.0
T2_A = 677.460935
T2_B = 500.731995
T3_A = 391.492187
T3_B = 440.845194
T4_A = 248.754280
T4_B = 280.113199


class CompressorExitStateTests(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, the compressor exit state."""

    def test_compressor_exit_case_a_and_b_anchors(self):
        """Workflow step 2 compressor-exit-state traverse: Case A
        (unprecooled bleed, T1 460 K) gives T2 677.460935 K within 1e-6
        and p2 exactly 720000 Pa; Case B (precooled, T1 340 K) gives T2
        500.731995 K within 1e-6 at pr_c 3.0, eta_c 0.78."""
        a = compressor_exit(P1, T1_A, PR_C, ETA_C)
        b = compressor_exit(P1, T1_B, PR_C, ETA_C)
        self.assertAlmostEqual(a["t2"], T2_A, delta=1e-6)
        self.assertEqual(a["p2"], 720000.0)
        self.assertAlmostEqual(b["t2"], T2_B, delta=1e-6)
        self.assertEqual(b["p2"], 720000.0)

    def test_compressor_exit_temperature_rises_with_pressure_ratio(self):
        """Workflow step 2 compressor-exit-state traverse: T2 rises
        monotonically as pr_c rises at fixed inlet and efficiency."""
        lo = compressor_exit(P1, T1_B, 2.5, ETA_C)["t2"]
        hi = compressor_exit(P1, T1_B, 3.5, ETA_C)["t2"]
        self.assertGreater(hi, lo)

    def test_compressor_exit_rejects_pressure_ratio_at_or_below_one(self):
        """Workflow step 2 compressor-exit-state guard: pr_c 1.0 and
        0.5, both non-physical for compression, raise ValueError."""
        for bad in (1.0, 0.5):
            with self.assertRaises(ValueError):
                compressor_exit(P1, T1_A, bad, ETA_C)

    def test_compressor_exit_rejects_efficiency_and_bleed_state(self):
        """Workflow step 2 compressor-exit-state guard: eta_c 0 and 1,
        bleed pressure 0 and bleed temperature 0 each raise
        ValueError (efficiency must sit in (0, 1), state positive)."""
        for bad in (0.0, 1.0):
            with self.assertRaises(ValueError):
                compressor_exit(P1, T1_A, PR_C, bad)
        with self.assertRaises(ValueError):
            compressor_exit(0.0, T1_A, PR_C, ETA_C)
        with self.assertRaises(ValueError):
            compressor_exit(P1, 0.0, PR_C, ETA_C)


class HeatExchangerExitTests(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, the ram-air heat exchanger."""

    def test_heat_exchanger_exit_case_a_anchor(self):
        """Workflow step 3 heat-exchanger-exit traverse: effectiveness
        0.8 against the 320 K ram sink cools the 677.460935 K
        compressor discharge to T3 391.492187 K within 1e-6."""
        t3 = heat_exchanger_exit(T2_A, 0.8, SINK)
        self.assertAlmostEqual(t3, T3_A, delta=1e-6)

    def test_heat_exchanger_exit_monotone_and_effectiveness_bound(self):
        """Workflow step 3 heat-exchanger-exit traverse: T3 is monotone
        decreasing in effectiveness, and effectiveness 1.0 is legal and
        lands T3 exactly on the sink temperature."""
        low = heat_exchanger_exit(T2_A, 0.3, SINK)
        high = heat_exchanger_exit(T2_A, 0.9, SINK)
        self.assertGreater(low, high)
        self.assertAlmostEqual(heat_exchanger_exit(T2_A, 1.0, SINK), SINK)

    def test_heat_exchanger_exit_rejects_effectiveness_bounds(self):
        """Workflow step 3 heat-exchanger-exit guard: effectiveness 0
        and 1.01 both raise ValueError (allowed range (0, 1])."""
        for bad in (0.0, 1.01):
            with self.assertRaises(ValueError):
                heat_exchanger_exit(T2_A, bad, SINK)

    def test_heat_exchanger_exit_rejects_sink_geometry(self):
        """Workflow step 3 heat-exchanger-exit guard: a hot inlet 320 K
        against a 320 K sink and non-positive inlet or sink
        temperatures all raise ValueError (cooling needs the hot side
        above the sink)."""
        with self.assertRaises(ValueError):
            heat_exchanger_exit(320.0, 0.8, 320.0)
        with self.assertRaises(ValueError):
            heat_exchanger_exit(0.0, 0.8, SINK)
        with self.assertRaises(ValueError):
            heat_exchanger_exit(500.0, 0.8, 0.0)


class TurbineExitTests(unittest.TestCase):
    """Step 4 of the SKILL.md workflow, the cooling turbine expansion."""

    def test_turbine_exit_case_a_anchor(self):
        """Workflow step 4 cooling-turbine-exit traverse at Case A
        (T3 391.492187 K): T4 248.754280 K within 1e-6, p4 exactly the
        cabin pressure and pr_t 7.105848 within 1e-6 at eta_t 0.85."""
        r = turbine_exit(720000.0, T3_A, 720000.0 / P_CABIN, ETA_T, P_CABIN)
        self.assertAlmostEqual(r["t4"], T4_A, delta=1e-6)
        self.assertEqual(r["p4"], P_CABIN)
        self.assertAlmostEqual(r["pr_t"], 7.105848, delta=1e-6)

    def test_turbine_exit_case_b_anchor(self):
        """Workflow step 4 cooling-turbine-exit traverse at Case B
        (T3 440.845194 K): T4 280.113199 K within 1e-6 at cabin
        discharge pressure."""
        r = turbine_exit(720000.0, T3_B, 720000.0 / P_CABIN, ETA_T, P_CABIN)
        self.assertAlmostEqual(r["t4"], T4_B, delta=1e-6)
        self.assertEqual(r["p4"], P_CABIN)

    def test_turbine_exit_cools_more_with_ratio_and_efficiency(self):
        """Workflow step 4 cooling-turbine-exit traverse trends: at
        fixed T3 the exit temperature falls as pr_t rises and as eta_t
        rises, so a colder supply needs a deeper, more efficient
        expansion."""
        pr_lo = turbine_exit(720000.0, T3_B, 720000.0 / P_CABIN, ETA_T, P_CABIN)
        pr_hi = turbine_exit(900000.0, T3_B, 900000.0 / P_CABIN, ETA_T, P_CABIN)
        self.assertLess(pr_hi["t4"], pr_lo["t4"])
        eff_lo = turbine_exit(720000.0, T3_B, 720000.0 / P_CABIN, 0.6, P_CABIN)
        eff_hi = turbine_exit(720000.0, T3_B, 720000.0 / P_CABIN, 0.9, P_CABIN)
        self.assertLess(eff_hi["t4"], eff_lo["t4"])

    def test_turbine_exit_rejects_ratio_and_efficiency(self):
        """Workflow step 4 cooling-turbine-exit guard: pr_t 1.0 and
        eta_t 0 or 1 each raise ValueError (expansion ratio above one,
        efficiency in (0, 1))."""
        with self.assertRaises(ValueError):
            turbine_exit(720000.0, T3_B, 1.0, ETA_T, P_CABIN)
        for bad in (0.0, 1.0):
            with self.assertRaises(ValueError):
                turbine_exit(720000.0, T3_B, 720000.0 / P_CABIN, bad, P_CABIN)

    def test_turbine_exit_rejects_pressure_inconsistency(self):
        """Workflow step 4 cooling-turbine-exit guard: pr_t 7.0 against
        p_cabin 101325 Pa fails the REL_TOL consistency check (p3/pr_t
        is 102857 Pa) and raises ValueError."""
        with self.assertRaises(ValueError):
            turbine_exit(720000.0, T3_B, 7.0, ETA_T, P_CABIN)

    def test_turbine_exit_rejects_nonpositive_states(self):
        """Workflow step 4 cooling-turbine-exit guard: non-positive p3,
        t3 and p_cabin each raise ValueError."""
        for args in (
            (0.0, T3_B, 720000.0 / P_CABIN, ETA_T, P_CABIN),
            (720000.0, 0.0, 720000.0 / P_CABIN, ETA_T, P_CABIN),
            (720000.0, T3_B, 720000.0 / P_CABIN, ETA_T, 0.0),
        ):
            with self.assertRaises(ValueError):
                turbine_exit(*args)


class ShaftPowerTests(unittest.TestCase):
    """Step 5 of the SKILL.md workflow, the ACM shaft power terms."""

    def test_shaft_powers_case_a_anchors(self):
        """Workflow step 5 ACM shaft power traverse at Case A: W_c
        196693.4 W within 0.1 and W_t 129106.4 W within 0.1 at 0.9 kg/s,
        the open pack where the turbine cannot cover the compressor."""
        wc = compressor_power(M_DOT, T1_A, T2_A)
        wt = turbine_power(M_DOT, T3_A, T4_A)
        self.assertAlmostEqual(wc, 196693.4, delta=0.1)
        self.assertAlmostEqual(wt, 129106.4, delta=0.1)

    def test_case_b_shaft_powers_closed(self):
        """Workflow step 5 ACM shaft power traverse at Case B: W_c and
        W_t both 145382.1 W within 0.1, the closing point of the
        balanced pack at 0.9 kg/s."""
        wc = compressor_power(M_DOT, T1_B, T2_B)
        wt = turbine_power(M_DOT, T3_B, T4_B)
        self.assertAlmostEqual(wc, 145382.1, delta=0.1)
        self.assertAlmostEqual(wt, 145382.1, delta=0.1)
        self.assertAlmostEqual(wc, wt, delta=0.1)

    def test_power_functions_reject_nonphysical_inputs(self):
        """Workflow step 5 ACM shaft power guard: m_dot 0, a compressor
        exit below its inlet (t2 < t1) and a turbine exit above its
        inlet (t4 > t3) all raise ValueError."""
        with self.assertRaises(ValueError):
            compressor_power(0.0, T1_A, T2_A)
        with self.assertRaises(ValueError):
            turbine_power(0.0, T3_A, T4_A)
        with self.assertRaises(ValueError):
            compressor_power(M_DOT, 500.0, 400.0)
        with self.assertRaises(ValueError):
            turbine_power(M_DOT, 300.0, 400.0)


class ShaftBalanceTests(unittest.TestCase):
    """Step 5 of the SKILL.md workflow, the ACM shaft balance closure."""

    def test_shaft_balance_case_a_open(self):
        """Workflow step 5 ACM shaft balance verdict at Case A:
        balanced False with deficit 67587.0 W within 0.1 and power
        ratio 0.6564 within 1e-4, the turbine cannot drive the
        compressor."""
        r = shaft_balance(196693.4, 129106.4)
        self.assertFalse(r["balanced"])
        self.assertAlmostEqual(r["deficit_w"], 67587.0, delta=0.1)
        self.assertAlmostEqual(r["power_ratio"], 0.6564, delta=1e-4)

    def test_shaft_balance_case_b_closed(self):
        """Workflow step 5 ACM shaft balance verdict at Case B:
        balanced True with zero deficit and power ratio exactly 1.0."""
        r = shaft_balance(145382.1, 145382.1)
        self.assertTrue(r["balanced"])
        self.assertEqual(r["deficit_w"], 0.0)
        self.assertEqual(r["power_ratio"], 1.0)

    def test_shaft_balance_tolerance_band_and_guard(self):
        """Workflow step 5 ACM shaft balance verdict: a turbine short of
        up to the 1 W band still reports balanced, a real deficit
        beyond the band reports unbalanced, and non-positive compressor
        power or negative turbine power raise ValueError."""
        self.assertTrue(shaft_balance(1000.0, 999.5)["balanced"])
        self.assertFalse(shaft_balance(1000.0, 998.0)["balanced"])
        with self.assertRaises(ValueError):
            shaft_balance(0.0, 100.0)
        with self.assertRaises(ValueError):
            shaft_balance(100.0, -1.0)


class ClosureTemperatureTests(unittest.TestCase):
    """Step 6 of the SKILL.md workflow, the closure temperature."""

    def test_t3_required_for_balance_case_b_anchor(self):
        """Workflow step 6 closure-temperature resolve at Case B: T3
        440.845194 K within 1e-6 makes W_t = W_c on the shared shaft."""
        t3r = t3_required_for_balance(T1_B, T2_B, ETA_T, 720000.0, P_CABIN)
        self.assertAlmostEqual(t3r, T3_B, delta=1e-6)

    def test_t3_required_for_balance_case_a_anchor(self):
        """Workflow step 6 closure-temperature resolve at Case A: the
        open pack closes only at T3 596.437615 K within 1e-6, far above
        the nominal heat-exchanger exit 391.492187 K; the chain feeds
        the real compressor-exit state from workflow step 2."""
        t2 = compressor_exit(P1, T1_A, PR_C, ETA_C)["t2"]
        t3r = t3_required_for_balance(T1_A, t2, ETA_T, 720000.0, P_CABIN)
        self.assertAlmostEqual(t3r, 596.437615, delta=1e-6)

    def test_t3_required_for_balance_rejects_invalid_inputs(self):
        """Workflow step 6 closure-temperature guard: t1 0, t2 at or
        below t1, p3 at or below p_cabin and eta_t 0 or 1 all raise
        ValueError."""
        with self.assertRaises(ValueError):
            t3_required_for_balance(0.0, 500.0, ETA_T, 720000.0, P_CABIN)
        with self.assertRaises(ValueError):
            t3_required_for_balance(500.0, 500.0, ETA_T, 720000.0, P_CABIN)
        with self.assertRaises(ValueError):
            t3_required_for_balance(T1_B, 500.0, ETA_T, P_CABIN, P_CABIN)
        for bad in (0.0, 1.0):
            with self.assertRaises(ValueError):
                t3_required_for_balance(T1_B, 500.0, bad, 720000.0, P_CABIN)

    def test_hx_effectiveness_for_balance_anchor_and_round_trip(self):
        """Workflow step 6 closure-temperature resolve: effectiveness
        0.331357 within 1e-6 lands T3 on the Case B balance value, and
        heat_exchanger_exit at that effectiveness round-trips to
        440.845194 K within 1e-6."""
        eff = hx_effectiveness_for_balance(T2_B, SINK, T3_B)
        self.assertAlmostEqual(eff, 0.331357, delta=1e-6)
        t3 = heat_exchanger_exit(T2_B, eff, SINK)
        self.assertAlmostEqual(t3, T3_B, delta=1e-6)

    def test_case_a_closure_feasible_but_cannot_cool(self):
        """Workflow step 6 closure-temperature resolve at Case A: the
        closing effectiveness 0.226663 within 1e-6 is feasible, but the
        balanced turbine exit 378.976680 K within 1e-6 sits above the
        294 K cabin, so the two-wheel pack cannot both close and cool
        and the delivered cooling is negative."""
        eff = hx_effectiveness_for_balance(T2_A, SINK, 596.437615)
        self.assertAlmostEqual(eff, 0.226663, delta=1e-6)
        t3 = heat_exchanger_exit(T2_A, eff, SINK)
        t4 = turbine_exit(720000.0, t3, 720000.0 / P_CABIN, ETA_T, P_CABIN)["t4"]
        self.assertAlmostEqual(t4, 378.976680, delta=1e-6)
        self.assertGreaterEqual(t4, CABIN_T)
        self.assertLess(cooling_capacity(M_DOT, t4, CABIN_T), 0.0)

    def test_hx_effectiveness_for_balance_rejects_infeasible_pack(self):
        """Workflow step 6 closure-temperature guard: a required T3 at
        or below the sink, one above the exchanger hot inlet and a hot
        inlet at the sink all raise ValueError, the infeasible-pack
        path where no heat exchanger can close the balance."""
        with self.assertRaises(ValueError):
            hx_effectiveness_for_balance(500.0, SINK, SINK)
        with self.assertRaises(ValueError):
            hx_effectiveness_for_balance(500.0, SINK, 600.0)
        with self.assertRaises(ValueError):
            hx_effectiveness_for_balance(320.0, SINK, 400.0)


class DeliveredCoolingTests(unittest.TestCase):
    """Step 7 of the SKILL.md workflow, delivered cooling and bleed flow."""

    def test_cooling_capacity_case_b_anchor_and_margin(self):
        """Workflow step 7 delivered-cooling-power traverse at Case B:
        Q 12560.6 W within 0.1 against the 294 K cabin at 0.9 kg/s, a
        margin of 1.0467 within 1e-3 over the 12000 W ECS load."""
        q = cooling_capacity(M_DOT, T4_B, CABIN_T)
        self.assertAlmostEqual(q, 12560.6, delta=0.1)
        self.assertAlmostEqual(q / LOAD_W, 1.0467, delta=1e-3)

    def test_cooling_capacity_signed_and_zero_cases(self):
        """Workflow step 7 delivered-cooling-power traverse: a turbine
        exit at 310 K returns negative -14472.0 W within 0.1 (signed,
        no cooling) and an exit exactly at the cabin temperature
        returns zero."""
        q = cooling_capacity(M_DOT, 310.0, CABIN_T)
        self.assertAlmostEqual(q, -14472.0, delta=0.1)
        self.assertLess(q, 0.0)
        self.assertEqual(cooling_capacity(M_DOT, CABIN_T, CABIN_T), 0.0)

    def test_cooling_capacity_rejects_nonphysical_inputs(self):
        """Workflow step 7 delivered-cooling-power guard: m_dot 0 and
        non-positive turbine exit or target temperatures raise
        ValueError."""
        with self.assertRaises(ValueError):
            cooling_capacity(0.0, 280.0, CABIN_T)
        with self.assertRaises(ValueError):
            cooling_capacity(M_DOT, 0.0, CABIN_T)
        with self.assertRaises(ValueError):
            cooling_capacity(M_DOT, 280.0, 0.0)

    def test_required_bleed_flow_case_b_anchor(self):
        """Workflow step 7 required-bleed-flow traverse at Case B: the
        12000 W load needs m_dot 0.859831 kg/s within 1e-6 at the
        actual turbine exit 280.113199 K."""
        m = required_bleed_flow(LOAD_W, T4_B, CABIN_T)
        self.assertAlmostEqual(m, 0.859831, delta=1e-6)

    def test_required_bleed_flow_rejects_load_and_uncoolable_supply(self):
        """Workflow step 7 required-bleed-flow guard: loads of 0 and
        -5 W and a turbine exit 300 K at or above the 294 K target all
        raise ValueError (a positive demand is needed and raising the
        flow never helps when the air cannot cool)."""
        for bad in (0.0, -5.0):
            with self.assertRaises(ValueError):
                required_bleed_flow(bad, T4_B, CABIN_T)
        with self.assertRaises(ValueError):
            required_bleed_flow(LOAD_W, 300.0, CABIN_T)


class BalanceIdentityTests(unittest.TestCase):
    """Steps 5 and 7 of the SKILL.md workflow, the balance identities."""

    def test_balance_ratio_invariant_in_mass_flow(self):
        """Workflow step 5 ACM shaft balance identity: the power ratio
        W_t / W_c is independent of the bleed flow, 0.6564 at both
        0.45 and 0.9 kg/s in Case A and 1.0 at both flows in Case B."""
        a_hi = shaft_balance(196693.4, 129106.4)
        a_lo = shaft_balance(98346.7, 64553.2)
        b_hi = shaft_balance(145382.1, 145382.1)
        b_lo = shaft_balance(72691.0, 72691.0)
        self.assertAlmostEqual(a_hi["power_ratio"], a_lo["power_ratio"], delta=1e-9)
        self.assertAlmostEqual(b_hi["power_ratio"], b_lo["power_ratio"], delta=1e-9)

    def test_closing_pack_stays_closed_at_required_flow(self):
        """Workflow step 7 required-bleed-flow identity: the pack sized
        for the 12000 W load at 0.859831 kg/s stays balanced at that
        lower flow, because closure is a purely thermodynamic statement
        about temperatures and both shaft powers scale with m_dot."""
        wc = compressor_power(0.859831, T1_B, T2_B)
        wt = turbine_power(0.859831, T3_B, T4_B)
        r = shaft_balance(wc, wt)
        self.assertTrue(r["balanced"])
        self.assertAlmostEqual(r["deficit_w"], 0.0, delta=0.1)

    def test_case_b_delta_t_identity_and_determinism(self):
        """Workflow step 5 ACM shaft balance identity in Case B: the
        compressor delta-T 160.731995 K equals the turbine delta-T, the
        run is deterministic, and the result dicts carry exactly the
        documented keys (workflow step 8 contract test run)."""
        d_comp = T2_B - T1_B
        d_turb = T3_B - T4_B
        self.assertAlmostEqual(d_comp, 160.731995, delta=1e-6)
        self.assertAlmostEqual(d_turb, 160.731995, delta=1e-6)
        self.assertAlmostEqual(d_comp, d_turb, delta=1e-9)
        a1 = compressor_exit(P1, T1_A, PR_C, ETA_C)
        a2 = compressor_exit(P1, T1_A, PR_C, ETA_C)
        self.assertEqual(a1["t2"], a2["t2"])
        self.assertEqual(set(a1.keys()), {"t2", "p2"})
        t = turbine_exit(720000.0, T3_A, 720000.0 / P_CABIN, ETA_T, P_CABIN)
        self.assertEqual(set(t.keys()), {"t4", "p4", "pr_t"})
        s = shaft_balance(196693.4, 129106.4)
        self.assertEqual(
            set(s.keys()),
            {"balanced", "w_compressor", "w_turbine", "deficit_w", "power_ratio"},
        )


if __name__ == "__main__":
    unittest.main()
