"""Contract test for the intercooled-cycle logic module.

Deterministic, offline, stdlib only. Run with:
    python3 scripts/test_intercooled_cycle.py

Covers the wave-38 spec validation list: optimum intercooler pressure
ratio, stage and intercooler exit temperatures, worked-example anchors
within 1 percent, the eps_ic = 0 degeneration identity, efficiency
bounds, ValueError rejection of non-physical inputs, and determinism.
"""

import unittest

import intercooled_cycle_logic as ic

# Worked example (spec, prep-verified): T1 = 288 K, T3 = 1500 K,
# pi_total = 30, eps_ic = 0.8, eta_c = 0.85, eta_t = 0.9.
T1 = 288.0
T3 = 1500.0
PI_TOTAL = 30.0
EPS_IC = 0.8
ETA_C = 0.85
ETA_T = 0.9

# Module real outputs (kJ/kg where noted), within 1 percent of anchors:
# T_2a 499.97, T_ic_exit 330.39, T_2b 573.57, w_c_total 457.42,
# w_net 385.91, eta_th 0.4145, gain +35.9 percent, eta_delta -1.66 pp.
W_C_TOTAL_REF = 457.42
W_NET_REF = 385.91
ETA_TH_REF = 0.4145
WORK_GAIN_REF = 35.9
ETA_DELTA_REF = -1.66


class TestConstants(unittest.TestCase):
    def test_module_constants(self):
        self.assertEqual(ic.GAMMA, 1.4)
        self.assertEqual(ic.CP, 1005.0)


class TestOptimumPressureRatio(unittest.TestCase):
    def test_pi36_optimum_is_6(self):
        self.assertEqual(ic.optimum_intercooler_pressure_ratio(36.0), 6.0)

    def test_pi30_optimum_is_sqrt(self):
        self.assertAlmostEqual(
            ic.optimum_intercooler_pressure_ratio(PI_TOTAL), 5.4772, places=4
        )

    def test_valueerror_pi_not_above_one(self):
        for bad in (1.0, 0.5):
            with self.assertRaises(ValueError):
                ic.optimum_intercooler_pressure_ratio(bad)


class TestStageExitTemperature(unittest.TestCase):
    def test_worked_example_T2a(self):
        t2a = ic.stage_exit_temperature(T1, PI_TOTAL ** 0.5, ETA_C)
        self.assertAlmostEqual(t2a, 499.97, delta=0.2)

    def test_rises_with_pi_falls_with_eta(self):
        self.assertLess(
            ic.stage_exit_temperature(T1, 2.0, ETA_C),
            ic.stage_exit_temperature(T1, 5.0, ETA_C),
        )
        self.assertLess(
            ic.stage_exit_temperature(T1, 5.0, 0.95),
            ic.stage_exit_temperature(T1, 5.0, 0.7),
        )

    def test_ideal_limit_is_isentropic(self):
        ideal = ic.stage_exit_temperature(T1, 10.0, 1.0)
        isen = T1 * 10.0 ** ((ic.GAMMA - 1.0) / ic.GAMMA)
        self.assertAlmostEqual(ideal, isen, places=9)

    def test_valueerror_non_physical(self):
        for args in ((0.0, 5.0, ETA_C), (T1, 1.0, ETA_C),
                     (T1, 5.0, 0.0), (T1, 5.0, 1.2)):
            with self.assertRaises(ValueError):
                ic.stage_exit_temperature(*args)


class TestIntercoolerExitTemperature(unittest.TestCase):
    def test_eps_zero_and_one_limits(self):
        self.assertEqual(ic.intercooler_exit_temperature(500.0, 288.0, 0.0),
                         500.0)
        self.assertEqual(ic.intercooler_exit_temperature(500.0, 288.0, 1.0),
                         288.0)

    def test_worked_example_T_ic_exit(self):
        t_ic = ic.intercooler_exit_temperature(499.97, T1, EPS_IC)
        self.assertAlmostEqual(t_ic, 330.39, delta=0.2)

    def test_higher_effectiveness_cools_more(self):
        self.assertLess(
            ic.intercooler_exit_temperature(500.0, 288.0, 0.8),
            ic.intercooler_exit_temperature(500.0, 288.0, 0.3),
        )

    def test_valueerror_non_physical(self):
        for bad_eps in (-0.1, 1.1):
            with self.assertRaises(ValueError):
                ic.intercooler_exit_temperature(500.0, 288.0, bad_eps)
        for bad_coolant in (300.0, 350.0):  # no cooling or reversed sink
            with self.assertRaises(ValueError):
                ic.intercooler_exit_temperature(300.0, bad_coolant, EPS_IC)


class TestCompressorWorkTotal(unittest.TestCase):
    def test_worked_example_full(self):
        comp = ic.compressor_work_total(T1, PI_TOTAL, EPS_IC, ETA_C)
        self.assertAlmostEqual(comp["pi_1"], 5.4772, places=4)
        self.assertAlmostEqual(comp["pi_2"], 5.4772, places=4)
        self.assertAlmostEqual(comp["T_2a"], 499.97, delta=0.2)
        self.assertAlmostEqual(comp["T_ic_exit"], 330.39, delta=0.2)
        self.assertAlmostEqual(comp["T_2b"], 573.57, delta=0.2)
        self.assertAlmostEqual(comp["w_c1"] / 1000.0, 213.03, delta=2.2)
        self.assertAlmostEqual(comp["w_c2"] / 1000.0, 244.39, delta=2.5)
        self.assertAlmostEqual(comp["w_c_total"] / 1000.0, W_C_TOTAL_REF,
                               delta=0.01 * W_C_TOTAL_REF)
        self.assertEqual(
            set(comp),
            {"pi_1", "pi_2", "T_2a", "T_ic_exit", "T_2b",
             "w_c1", "w_c2", "w_c_total"},
        )

    def test_total_work_is_sum_of_stage_works(self):
        comp = ic.compressor_work_total(T1, PI_TOTAL, EPS_IC, ETA_C)
        self.assertAlmostEqual(
            comp["w_c_total"], comp["w_c1"] + comp["w_c2"], places=6
        )

    def test_effectiveness_reduces_total_work(self):
        self.assertLess(
            ic.compressor_work_total(T1, PI_TOTAL, 0.9, ETA_C)["w_c_total"],
            ic.compressor_work_total(T1, PI_TOTAL, 0.4, ETA_C)["w_c_total"],
        )

    def test_valueerror_non_physical(self):
        for kwargs in (
            dict(t_1=0.0, pi_total=PI_TOTAL, eps_ic=EPS_IC, eta_c=ETA_C),
            dict(t_1=T1, pi_total=1.0, eps_ic=EPS_IC, eta_c=ETA_C),
            dict(t_1=T1, pi_total=PI_TOTAL, eps_ic=1.5, eta_c=ETA_C),
            dict(t_1=T1, pi_total=PI_TOTAL, eps_ic=EPS_IC, eta_c=1.1),
        ):
            with self.assertRaises(ValueError):
                ic.compressor_work_total(**kwargs)


class TestTurbineWork(unittest.TestCase):
    def test_worked_example_wt(self):
        self.assertAlmostEqual(
            ic.turbine_work(T3, PI_TOTAL, ETA_T) / 1000.0, 843.34, delta=8.5
        )

    def test_rises_with_T3_and_pi(self):
        self.assertLess(
            ic.turbine_work(1400.0, PI_TOTAL, ETA_T),
            ic.turbine_work(1600.0, PI_TOTAL, ETA_T),
        )
        self.assertLess(  # more expansion across the larger total ratio
            ic.turbine_work(T3, 20.0, ETA_T),
            ic.turbine_work(T3, 40.0, ETA_T),
        )

    def test_valueerror_non_physical(self):
        for args in ((0.0, PI_TOTAL, ETA_T), (T3, 1.0, ETA_T),
                     (T3, PI_TOTAL, 0.0), (T3, PI_TOTAL, 1.2)):
            with self.assertRaises(ValueError):
                ic.turbine_work(*args)


class TestIntercooledCycle(unittest.TestCase):
    def test_worked_example_anchors(self):
        res = ic.intercooled_cycle(T1, T3, PI_TOTAL, EPS_IC, ETA_C, ETA_T)
        self.assertAlmostEqual(res["w_net"] / 1000.0, W_NET_REF,
                               delta=0.01 * W_NET_REF)
        self.assertAlmostEqual(res["q_in"] / 1000.0, 931.06, delta=9.4)
        self.assertAlmostEqual(res["eta_th"], ETA_TH_REF,
                               delta=0.01 * ETA_TH_REF)
        self.assertGreater(res["eta_th"], 0.0)
        self.assertLess(res["eta_th"], 1.0)
        self.assertEqual(
            set(res),
            {"pi_1", "pi_2", "T_2a", "T_ic_exit", "T_2b", "w_c1", "w_c2",
             "w_c_total", "w_t", "w_net", "q_in", "eta_th"},
        )

    def test_identities(self):
        res = ic.intercooled_cycle(T1, T3, PI_TOTAL, EPS_IC, ETA_C, ETA_T)
        self.assertAlmostEqual(res["w_net"],
                               res["w_t"] - res["w_c_total"], places=6)
        self.assertAlmostEqual(res["eta_th"], res["w_net"] / res["q_in"],
                               places=9)

    def test_deterministic(self):
        a = ic.intercooled_cycle(T1, T3, PI_TOTAL, EPS_IC, ETA_C, ETA_T)
        b = ic.intercooled_cycle(T1, T3, PI_TOTAL, EPS_IC, ETA_C, ETA_T)
        self.assertEqual(a, b)

    def test_valueerror_non_physical(self):
        base = dict(t_1=T1, t_3=T3, pi_total=PI_TOTAL, eps_ic=EPS_IC,
                    eta_c=ETA_C, eta_t=ETA_T)
        for bad in (
            dict(t_1=0.0),
            dict(t_3=200.0),
            dict(pi_total=0.9),
            dict(eps_ic=-0.01),
            dict(eta_c=0.0),
            dict(eta_t=0.0),
        ):
            kwargs = dict(base)
            kwargs.update(bad)
            with self.assertRaises(ValueError):
                ic.intercooled_cycle(**kwargs)


class TestSimpleCycle(unittest.TestCase):
    def test_worked_example_anchors(self):
        s = ic.simple_cycle(T1, T3, PI_TOTAL, ETA_C, ETA_T)
        self.assertAlmostEqual(s["w_net"] / 1000.0, 283.99, delta=2.9)
        self.assertAlmostEqual(s["eta_th"], 0.4311, delta=0.01 * 0.4311)
        self.assertEqual(set(s), {"w_c", "w_t", "w_net", "q_in", "eta_th"})

    def test_compressor_work_matches_stage_function(self):
        s = ic.simple_cycle(T1, T3, PI_TOTAL, ETA_C, ETA_T)
        t2 = ic.stage_exit_temperature(T1, PI_TOTAL, ETA_C)
        self.assertAlmostEqual(s["w_c"], ic.CP * (t2 - T1), places=6)

    def test_valueerror_t3_below_t1(self):
        with self.assertRaises(ValueError):
            ic.simple_cycle(T1, 250.0, PI_TOTAL, ETA_C, ETA_T)


class TestCycleComparison(unittest.TestCase):
    def setUp(self):
        self.intercooled = ic.intercooled_cycle(
            T1, T3, PI_TOTAL, EPS_IC, ETA_C, ETA_T
        )
        self.simple = ic.simple_cycle(T1, T3, PI_TOTAL, ETA_C, ETA_T)

    def test_worked_example_comparison(self):
        c = ic.cycle_comparison(self.intercooled, self.simple)
        self.assertAlmostEqual(c["work_gain_pct"], WORK_GAIN_REF, delta=0.2)
        self.assertAlmostEqual(c["eta_delta_pp"], ETA_DELTA_REF, delta=0.02)

    def test_gain_positive_eta_delta_negative(self):
        c = ic.cycle_comparison(self.intercooled, self.simple)
        self.assertGreater(c["work_gain_pct"], 0.0)
        self.assertLess(c["eta_delta_pp"], 0.0)

    def test_identical_cycles_zero_gain(self):
        c = ic.cycle_comparison(self.intercooled, self.intercooled)
        self.assertEqual(c["work_gain_pct"], 0.0)
        self.assertEqual(c["eta_delta_pp"], 0.0)

    def test_keys_and_closed_form(self):
        c = ic.cycle_comparison(self.intercooled, self.simple)
        self.assertEqual(set(c), {"work_gain_pct", "eta_delta_pp"})
        expected = (
            (self.intercooled["w_net"] - self.simple["w_net"])
            / self.simple["w_net"] * 100.0
        )
        self.assertAlmostEqual(c["work_gain_pct"], expected, places=9)


class TestEpsZeroIdentity(unittest.TestCase):
    def test_two_stage_no_cooling_approximates_single_stage(self):
        two_stage = ic.compressor_work_total(T1, PI_TOTAL, 0.0, ETA_C)
        single = ic.simple_cycle(T1, T3, PI_TOTAL, ETA_C, ETA_T)["w_c"]
        self.assertAlmostEqual(
            two_stage["w_c_total"], single,
            delta=0.05 * single,  # cascade nuance, vanishes as eta_c -> 1
        )

    def test_two_stage_no_cooling_closed_form(self):
        comp = ic.compressor_work_total(T1, PI_TOTAL, 0.0, ETA_C)
        r = PI_TOTAL ** ((ic.GAMMA - 1.0) / (2.0 * ic.GAMMA))
        chain = ic.CP * T1 * ((1.0 + (r - 1.0) / ETA_C) ** 2 - 1.0)
        self.assertAlmostEqual(comp["w_c_total"], chain, places=6)


class TestPerfectIntercoolingRoundTrip(unittest.TestCase):
    def test_eps_one_resets_stage_two(self):
        comp = ic.compressor_work_total(T1, PI_TOTAL, 1.0, ETA_C)
        t2a = ic.stage_exit_temperature(T1, PI_TOTAL ** 0.5, ETA_C)
        self.assertAlmostEqual(comp["T_ic_exit"], T1, places=9)
        self.assertAlmostEqual(comp["T_2b"], t2a, places=9)
        self.assertAlmostEqual(comp["w_c1"], comp["w_c2"], places=6)


if __name__ == "__main__":
    unittest.main()
