"""Contract test for the fuel jettison sizing logic (FAR 25.1001 context).

Offline, deterministic, stdlib unittest only. Run:

    python3 test_fuel_jettison_sizing.py

Worked-example reference transport: MTOW 79,000 kg, MLW 66,500 kg, two
dump masts, 10 percent design margin (module defaults). Expected:
dumpable 12,500 kg, required rate 13.8889 kg/s, design rate 15.2778
kg/s, per-mast flow 7.6389 kg/s, time to landing weight 818.18 s
(<= 900 s, PASS).
"""

import unittest

import fuel_jettison_sizing_logic as fjs

MTOW = 79000.0
MLW = 66500.0
DUMPABLE = 12500.0
LIMIT = fjs.JETTISON_LIMIT_S


class TestDumpableFuelMass(unittest.TestCase):
    def test_worked_case_excess(self):
        self.assertEqual(fjs.dumpable_fuel_mass(MTOW, MLW), DUMPABLE)

    def test_zero_excess_at_equal_weights(self):
        self.assertEqual(fjs.dumpable_fuel_mass(50000, 50000), 0.0)

    def test_mtow_nonpositive_raises(self):
        with self.assertRaises(ValueError):
            fjs.dumpable_fuel_mass(0, MLW)
        with self.assertRaises(ValueError):
            fjs.dumpable_fuel_mass(-1000, MLW)

    def test_mlw_nonpositive_raises(self):
        with self.assertRaises(ValueError):
            fjs.dumpable_fuel_mass(MTOW, 0)
        with self.assertRaises(ValueError):
            fjs.dumpable_fuel_mass(MTOW, -500)

    def test_mlw_exceeds_mtow_raises(self):
        with self.assertRaises(ValueError):
            fjs.dumpable_fuel_mass(60000, 60001)


class TestRequiredJettisonRate(unittest.TestCase):
    def test_worked_case_rate(self):
        self.assertAlmostEqual(
            fjs.required_jettison_rate(MTOW, MLW), 13.88888888888889, places=6
        )

    def test_rate_identity_exact(self):
        # Required rate is exactly (MTOW - MLW) / 900 s.
        self.assertEqual(
            fjs.required_jettison_rate(MTOW, MLW), (MTOW - MLW) / LIMIT
        )

    def test_rate_custom_limit(self):
        self.assertAlmostEqual(
            fjs.required_jettison_rate(MTOW, MLW, limit_s=950.0),
            DUMPABLE / 950.0,
            places=9,
        )

    def test_rate_nonpositive_limit_raises(self):
        with self.assertRaises(ValueError):
            fjs.required_jettison_rate(MTOW, MLW, limit_s=0)
        with self.assertRaises(ValueError):
            fjs.required_jettison_rate(MTOW, MLW, limit_s=-100)

    def test_rate_bad_masses_raise(self):
        with self.assertRaises(ValueError):
            fjs.required_jettison_rate(0, MLW)
        with self.assertRaises(ValueError):
            fjs.required_jettison_rate(MTOW, 0)
        with self.assertRaises(ValueError):
            fjs.required_jettison_rate(60000, 60001)


class TestDesignJettisonRate(unittest.TestCase):
    def test_default_margin_ten_percent(self):
        self.assertAlmostEqual(
            fjs.design_jettison_rate(13.88888888888889),
            15.277777777777779,
            places=6,
        )

    def test_worked_case_design_rate(self):
        req = fjs.required_jettison_rate(MTOW, MLW)
        self.assertAlmostEqual(fjs.design_jettison_rate(req), 15.278, places=2)

    def test_margin_one_unchanged(self):
        req = fjs.required_jettison_rate(MTOW, MLW)
        self.assertEqual(fjs.design_jettison_rate(req, margin=1.0), req)

    def test_margin_12_scales_exactly(self):
        req = fjs.required_jettison_rate(MTOW, MLW)
        self.assertEqual(fjs.design_jettison_rate(req, margin=1.2), req * 1.2)

    def test_margin_below_one_raises(self):
        req = fjs.required_jettison_rate(MTOW, MLW)
        with self.assertRaises(ValueError):
            fjs.design_jettison_rate(req, margin=0.9)
        with self.assertRaises(ValueError):
            fjs.design_jettison_rate(req, margin=0.0)

    def test_nonpositive_required_rate_raises(self):
        with self.assertRaises(ValueError):
            fjs.design_jettison_rate(0)
        with self.assertRaises(ValueError):
            fjs.design_jettison_rate(-5.0)


class TestPerMastFlow(unittest.TestCase):
    def test_two_masts_halve_flow(self):
        design = fjs.design_jettison_rate(fjs.required_jettison_rate(MTOW, MLW))
        self.assertEqual(fjs.per_mast_flow(design, 2), design / 2)
        self.assertAlmostEqual(fjs.per_mast_flow(design, 2), 7.639, places=2)

    def test_single_mast_equals_design_rate(self):
        design = fjs.design_jettison_rate(fjs.required_jettison_rate(MTOW, MLW))
        self.assertEqual(fjs.per_mast_flow(design, 1), design)

    def test_zero_masts_raises(self):
        with self.assertRaises(ValueError):
            fjs.per_mast_flow(15.0, 0)
        with self.assertRaises(ValueError):
            fjs.per_mast_flow(15.0, -2)

    def test_nonpositive_rate_raises(self):
        with self.assertRaises(ValueError):
            fjs.per_mast_flow(0.0, 2)
        with self.assertRaises(ValueError):
            fjs.per_mast_flow(-3.0, 2)


class TestTimeToLandingWeight(unittest.TestCase):
    def test_worked_case_time_within_one_second(self):
        design = fjs.design_jettison_rate(fjs.required_jettison_rate(MTOW, MLW))
        result = fjs.time_to_landing_weight(DUMPABLE, design)
        self.assertAlmostEqual(result["time_s"], 818.1818181818181, places=3)
        self.assertAlmostEqual(result["time_s"], 818, delta=1.0)
        self.assertEqual(result["verdict"], "PASS")

    def test_margin_one_boundary_exactly_900(self):
        # With margin 1.0 the design rate equals the required rate, so
        # the time to landing weight is exactly the 900 s limit.
        req = fjs.required_jettison_rate(MTOW, MLW)
        result = fjs.time_to_landing_weight(DUMPABLE, req)
        self.assertEqual(result["time_s"], LIMIT)
        self.assertEqual(result["verdict"], "PASS")

    def test_identity_time_equals_mass_over_rate(self):
        design = fjs.design_jettison_rate(fjs.required_jettison_rate(MTOW, MLW))
        result = fjs.time_to_landing_weight(DUMPABLE, design)
        self.assertEqual(result["time_s"], DUMPABLE / design)

    def test_identity_time_equals_900_over_margin(self):
        # Time = excess / (required * margin) = 900 / margin exactly.
        result = fjs.time_to_landing_weight(
            DUMPABLE, fjs.design_jettison_rate(fjs.required_jettison_rate(MTOW, MLW))
        )
        self.assertAlmostEqual(result["time_s"], LIMIT / 1.1, places=9)

    def test_undersized_design_fails_verdict(self):
        # Margin 0.9 is rejected; an undersized design instead follows
        # from a 950 s requirement at margin 1.0: dumping over 950 s
        # cannot meet the 900 s limit.
        req_950 = fjs.required_jettison_rate(MTOW, MLW, limit_s=950.0)
        result = fjs.time_to_landing_weight(DUMPABLE, req_950)
        self.assertGreater(result["time_s"], LIMIT)
        self.assertAlmostEqual(result["time_s"], 950.0, places=9)
        self.assertEqual(result["verdict"], "FAIL")

    def test_negative_dumpable_raises(self):
        with self.assertRaises(ValueError):
            fjs.time_to_landing_weight(-1.0, 15.0)

    def test_nonpositive_rate_raises(self):
        with self.assertRaises(ValueError):
            fjs.time_to_landing_weight(DUMPABLE, 0.0)
        with self.assertRaises(ValueError):
            fjs.time_to_landing_weight(DUMPABLE, -2.0)


class TestJettisonSummary(unittest.TestCase):
    def test_summary_keys_exact(self):
        expected_keys = {
            "mtow_kg",
            "mlw_kg",
            "dumpable_mass_kg",
            "required_rate_kg_s",
            "design_rate_kg_s",
            "margin",
            "n_masts",
            "per_mast_flow_kg_s",
            "limit_s",
            "time_s",
            "verdict",
        }
        self.assertEqual(set(fjs.jettison_summary(MTOW, MLW, 2).keys()), expected_keys)

    def test_summary_worked_case_values(self):
        s = fjs.jettison_summary(MTOW, MLW, 2)
        self.assertEqual(s["dumpable_mass_kg"], DUMPABLE)
        self.assertAlmostEqual(s["required_rate_kg_s"], 13.889, places=2)
        self.assertAlmostEqual(s["design_rate_kg_s"], 15.278, places=2)
        self.assertAlmostEqual(s["per_mast_flow_kg_s"], 7.639, places=2)
        self.assertEqual(s["n_masts"], 2)
        self.assertEqual(s["margin"], fjs.DESIGN_MARGIN_DEFAULT)
        self.assertEqual(s["limit_s"], 900.0)

    def test_summary_time_recheck_pass(self):
        s = fjs.jettison_summary(MTOW, MLW, 2)
        self.assertAlmostEqual(s["time_s"], 818, delta=1.0)
        self.assertEqual(s["verdict"], "PASS")
        # The summary re-check matches the direct function output.
        direct = fjs.time_to_landing_weight(s["dumpable_mass_kg"], s["design_rate_kg_s"])
        self.assertEqual(s["time_s"], direct["time_s"])
        self.assertEqual(s["verdict"], direct["verdict"])

    def test_summary_single_mast_verdict(self):
        # Single mast carries the full design rate, so the time check is
        # unchanged by the mast count.
        s = fjs.jettison_summary(MTOW, MLW, 1)
        self.assertEqual(s["per_mast_flow_kg_s"], s["design_rate_kg_s"])
        self.assertEqual(s["verdict"], "PASS")

    def test_summary_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fjs.jettison_summary(0, MLW, 2)
        with self.assertRaises(ValueError):
            fjs.jettison_summary(MTOW, 0, 2)
        with self.assertRaises(ValueError):
            fjs.jettison_summary(MTOW, MTOW + 1, 2)
        with self.assertRaises(ValueError):
            fjs.jettison_summary(MTOW, MLW, 0)
        with self.assertRaises(ValueError):
            fjs.jettison_summary(MTOW, MLW, 2, margin=0.95)


class TestDeterminism(unittest.TestCase):
    def test_summary_deterministic(self):
        a = fjs.jettison_summary(MTOW, MLW, 2)
        b = fjs.jettison_summary(MTOW, MLW, 2)
        self.assertEqual(a, b)

    def test_rate_deterministic(self):
        self.assertEqual(
            fjs.required_jettison_rate(MTOW, MLW),
            fjs.required_jettison_rate(MTOW, MLW),
        )

    def test_time_deterministic(self):
        design = fjs.design_jettison_rate(fjs.required_jettison_rate(MTOW, MLW))
        self.assertEqual(
            fjs.time_to_landing_weight(DUMPABLE, design),
            fjs.time_to_landing_weight(DUMPABLE, design),
        )


if __name__ == "__main__":
    unittest.main()
