"""Contract test for turbine-blade-cooling logic.

Offline deterministic stdlib unittest. Run:
    cd ~/AeroSkills && python3 skills/propulsion/axial-compressor/turbine-blade-cooling/scripts/test_turbine_blade_cooling.py

Sensitivity boundary (t_gas 1500 K, t_coolant 800 K, no film): the
required coolant fraction falls below the 0.20 bleed limit when the
allowable metal temperature exceeds 1383.33 K, about 116.7 K below the
gas temperature.
"""

import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
    ),
)

import turbine_blade_cooling_logic as m


class TestEffectiveness(unittest.TestCase):
    def test_worked_case1_effectiveness(self):
        # phi = (1500 - 1200) / (1500 - 800) = 300 / 700 = 0.4286.
        self.assertAlmostEqual(m.effectiveness(1500, 1200, 800), 0.4286, places=4)

    def test_worked_case2_effectiveness(self):
        # phi = (1600 - 1250) / (1600 - 900) = 350 / 700 = 0.5.
        self.assertAlmostEqual(m.effectiveness(1600, 1250, 900), 0.5, places=4)

    def test_worked_case3_effectiveness(self):
        # phi = (1600 - 1350) / (1600 - 900) = 250 / 700 = 0.3571.
        self.assertAlmostEqual(m.effectiveness(1600, 1350, 900), 0.3571, places=4)

    def test_effectiveness_zero_when_metal_at_gas(self):
        # Metal near the gas temperature needs almost no cooling.
        self.assertAlmostEqual(m.effectiveness(1400, 1399.99, 700), 0.0, places=3)

    def test_effectiveness_in_unit_interval(self):
        for t_gas, t_metal, t_cool in ((1400, 1300, 700), (1800, 1600, 1000),
                                       (1250, 1100, 650), (2000, 1500, 600)):
            phi = m.effectiveness(t_gas, t_metal, t_cool)
            self.assertGreater(phi, 0.0)
            self.assertLess(phi, 1.0)


class TestCoolantFraction(unittest.TestCase):
    def test_worked_case1_fraction(self):
        # 0.4286 / 0.5714 = 0.75.
        self.assertAlmostEqual(
            m.coolant_fraction(m.effectiveness(1500, 1200, 800)), 0.75, places=3
        )

    def test_worked_case2_fraction(self):
        # 0.5 / 0.5 = 1.0.
        self.assertAlmostEqual(
            m.coolant_fraction(m.effectiveness(1600, 1250, 900)), 1.0, places=4
        )

    def test_worked_case3_fraction(self):
        # 0.3571 / 0.6429 = 0.5556.
        self.assertAlmostEqual(
            m.coolant_fraction(m.effectiveness(1600, 1350, 900)), 0.5556, places=3
        )

    def test_fraction_zero_at_zero_effectiveness(self):
        self.assertAlmostEqual(m.coolant_fraction(1e-12), 0.0, places=6)

    def test_fraction_monotonic_in_effectiveness(self):
        fracs = [m.coolant_fraction(phi) for phi in (0.1, 0.2, 0.3, 0.4, 0.5)]
        self.assertEqual(fracs, sorted(fracs))
        self.assertLess(fracs[0], fracs[-1])


class TestBleedVerdict(unittest.TestCase):
    def test_case1_verdict_exceeds(self):
        self.assertEqual(
            m.bleed_verdict(m.coolant_fraction(m.effectiveness(1500, 1200, 800))),
            "exceeds bleed limit",
        )

    def test_case2_verdict_exceeds(self):
        self.assertEqual(
            m.bleed_verdict(m.coolant_fraction(m.effectiveness(1600, 1250, 900))),
            "exceeds bleed limit",
        )

    def test_case3_verdict_exceeds(self):
        self.assertEqual(
            m.bleed_verdict(m.coolant_fraction(m.effectiveness(1600, 1350, 900))),
            "exceeds bleed limit",
        )

    def test_verdict_within_at_limit(self):
        self.assertEqual(m.bleed_verdict(m.BLEED_LIMIT), "within bleed limit")

    def test_verdict_within_below_limit(self):
        self.assertEqual(m.bleed_verdict(0.15), "within bleed limit")
        self.assertEqual(m.bleed_verdict(0.0), "within bleed limit")

    def test_sensitivity_boundary_crossing(self):
        # Boundary metal temperature 1383.33 K at gas 1500, coolant 800.
        below = m.coolant_fraction(m.effectiveness(1500, 1380, 800))
        above = m.coolant_fraction(m.effectiveness(1500, 1385, 800))
        self.assertEqual(m.bleed_verdict(below), "exceeds bleed limit")
        self.assertEqual(m.bleed_verdict(above), "within bleed limit")

    def test_sensitivity_monotonic_trend(self):
        # Rising allowable metal temperature lowers the required fraction.
        fracs = [
            m.coolant_fraction(m.effectiveness(1500, t, 800))
            for t in (1250, 1300, 1350, 1400)
        ]
        self.assertEqual(fracs, sorted(fracs, reverse=True))


class TestMetalTempWithFilm(unittest.TestCase):
    def test_case1_film_metal_temp(self):
        # phi_eff = 0.4286 + 0.15 = 0.5786; Tm = 1500 - 0.5786 * 700 = 1095.0 K.
        phi = m.effectiveness(1500, 1200, 800)
        self.assertAlmostEqual(m.metal_temp_with_film(1500, 800, phi, True), 1095.0, places=1)

    def test_case2_film_metal_temp(self):
        # phi_eff = 0.5 + 0.15 = 0.65; Tm = 1600 - 0.65 * 700 = 1145 K.
        phi = m.effectiveness(1600, 1250, 900)
        self.assertAlmostEqual(m.metal_temp_with_film(1600, 900, phi, True), 1145.0, places=1)

    def test_no_film_uses_baseline_effectiveness(self):
        phi = m.effectiveness(1600, 1350, 900)
        self.assertAlmostEqual(
            m.metal_temp_with_film(1600, 900, phi, False), 1350.0, places=4
        )

    def test_film_lowers_metal_temp(self):
        phi = m.effectiveness(1600, 1350, 900)
        base = m.metal_temp_with_film(1600, 900, phi, False)
        filmed = m.metal_temp_with_film(1600, 900, phi, True)
        self.assertLess(filmed, base)

    def test_film_effectiveness_capped_at_phicap(self):
        # A high base effectiveness plus film must not exceed PHI_CAP.
        phi = m.effectiveness(2000, 800, 600)  # 0.8571, near the cap.
        self.assertGreater(phi + m.FILM_IMPROVEMENT, m.PHI_CAP)
        temp = m.metal_temp_with_film(2000, 600, phi, True)
        self.assertAlmostEqual(
            temp, 2000 - m.PHI_CAP * (2000 - 600), places=4
        )


class TestAnalyze(unittest.TestCase):
    def test_analyze_case1_film(self):
        result = m.analyze(1500, 1200, 800, film_cooling=True)
        self.assertAlmostEqual(result["effectiveness"], 0.4286, places=4)
        self.assertAlmostEqual(result["coolant_fraction"], 0.75, places=3)
        self.assertEqual(result["verdict"], "exceeds bleed limit")
        self.assertAlmostEqual(result["metal_temp_k"], 1095.0, places=1)
        self.assertAlmostEqual(result["margin_k"], 105.0, places=1)

    def test_analyze_case2_film_margin(self):
        result = m.analyze(1600, 1250, 900, film_cooling=True)
        self.assertAlmostEqual(result["effectiveness"], 0.5, places=4)
        self.assertAlmostEqual(result["metal_temp_k"], 1145.0, places=1)
        self.assertAlmostEqual(result["margin_k"], 1250 - 1145, places=1)

    def test_analyze_defaults_to_no_film(self):
        result = m.analyze(1600, 1350, 900)
        self.assertAlmostEqual(result["metal_temp_k"], 1350.0, places=4)
        self.assertEqual(result["margin_k"], 0.0)

    def test_analyze_dict_keys(self):
        result = m.analyze(1500, 1200, 800)
        self.assertEqual(
            sorted(result.keys()),
            ["coolant_fraction", "effectiveness", "margin_k",
             "metal_temp_k", "verdict"],
        )

    def test_analyze_margin_positive_with_film(self):
        # Film cooling on case 1 leaves a +105 K margin.
        self.assertGreater(m.analyze(1500, 1200, 800, film_cooling=True)["margin_k"], 0)


class TestValueErrors(unittest.TestCase):
    def test_gas_at_or_below_coolant_rejected(self):
        with self.assertRaises(ValueError):
            m.effectiveness(1500, 1200, 1500)
        with self.assertRaises(ValueError):
            m.effectiveness(1500, 1200, 1600)
        with self.assertRaises(ValueError):
            m.analyze(900, 800, 900)

    def test_metal_at_or_above_gas_rejected(self):
        with self.assertRaises(ValueError):
            m.effectiveness(1500, 1500, 800)
        with self.assertRaises(ValueError):
            m.effectiveness(1500, 1600, 800)

    def test_metal_at_or_below_coolant_rejected(self):
        with self.assertRaises(ValueError):
            m.effectiveness(1500, 800, 800)
        with self.assertRaises(ValueError):
            m.effectiveness(1500, 700, 800)

    def test_non_positive_gas_rejected(self):
        with self.assertRaises(ValueError):
            m.effectiveness(0, 500, 300)
        with self.assertRaises(ValueError):
            m.effectiveness(-100, 500, 300)
        with self.assertRaises(ValueError):
            m.analyze(0, 1200, 800)

    def test_out_of_range_phi_rejected(self):
        with self.assertRaises(ValueError):
            m.coolant_fraction(0.0)
        with self.assertRaises(ValueError):
            m.coolant_fraction(1.0)
        with self.assertRaises(ValueError):
            m.coolant_fraction(1.5)

    def test_negative_fraction_rejected_in_verdict(self):
        with self.assertRaises(ValueError):
            m.bleed_verdict(-0.1)

    def test_bad_phi_base_rejected_in_film_temp(self):
        with self.assertRaises(ValueError):
            m.metal_temp_with_film(1500, 800, 1.0, True)
        with self.assertRaises(ValueError):
            m.metal_temp_with_film(1500, 800, 0.0, False)

    def test_bad_temperatures_rejected_in_film_temp(self):
        with self.assertRaises(ValueError):
            m.metal_temp_with_film(0, 800, 0.4, True)
        with self.assertRaises(ValueError):
            m.metal_temp_with_film(900, 900, 0.4, False)


if __name__ == "__main__":
    unittest.main()
