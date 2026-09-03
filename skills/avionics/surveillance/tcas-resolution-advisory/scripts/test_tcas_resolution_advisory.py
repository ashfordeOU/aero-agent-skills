"""Contract test for the TCAS II resolution advisory logic leaf.

Deterministic stdlib unittest for
tcas_resolution_advisory_logic.py. Covers the sensitivity level band
edges (999/1000/2350/5000/10000/20000 with neighbors), the worked
anchors, the five spec cases (modified tau of 33.75 / 95.16 / 20.63 /
95.16 / 5.25 s with threat verdicts and senses), the not-closing gate,
the tau-exceeded and altitude-exceeded reasons, sense selection both
directions with ties to climb, the evaluate_encounter chain and the
ValueError rejections. Runs offline.

    python3 scripts/test_tcas_resolution_advisory.py
"""

import unittest

from tcas_resolution_advisory_logic import (
    ALTITUDE_BANDS,
    SENSITIVITY_TABLE,
    evaluate_encounter,
    modified_tau,
    ra_sense,
    sensitivity_level,
    threat_verdict,
)

CLOSING_300KT = -0.08333  # 300 kt closing in nmi/s
CLOSING_180KT = -0.05  # 180 kt closing in nmi/s


class TestSensitivityLevel(unittest.TestCase):
    def test_sl_edges_around_1000_ft(self):
        self.assertEqual(sensitivity_level(999), 2)
        self.assertEqual(sensitivity_level(1000), 3)

    def test_sl_edges_around_2350_ft(self):
        self.assertEqual(sensitivity_level(2349), 3)
        self.assertEqual(sensitivity_level(2350), 4)

    def test_sl_edges_around_5000_ft(self):
        self.assertEqual(sensitivity_level(4999), 4)
        self.assertEqual(sensitivity_level(5000), 5)

    def test_sl_edges_around_10000_ft(self):
        self.assertEqual(sensitivity_level(9999), 5)
        self.assertEqual(sensitivity_level(10000), 6)

    def test_sl_edges_around_20000_ft(self):
        self.assertEqual(sensitivity_level(19999), 6)
        self.assertEqual(sensitivity_level(20000), 7)

    def test_sl_worked_anchors(self):
        self.assertEqual(sensitivity_level(500), 2)
        self.assertEqual(sensitivity_level(8000), 5)
        self.assertEqual(sensitivity_level(30000), 7)

    def test_sl_bands_cover_every_level_once(self):
        self.assertEqual([b[2] for b in ALTITUDE_BANDS], [2, 3, 4, 5, 6, 7])

    def test_sl_negative_altitude_raises_valueerror(self):
        with self.assertRaises(ValueError):
            sensitivity_level(-1)
        with self.assertRaises(ValueError):
            sensitivity_level(-10000)


class TestModifiedTau(unittest.TestCase):
    def test_modified_tau_case1_33_75_s(self):
        tau_mod = modified_tau(3.0, CLOSING_300KT, SENSITIVITY_TABLE[5]["dmod"])
        self.assertAlmostEqual(tau_mod, 33.75, delta=0.01)

    def test_modified_tau_case2_95_16_s(self):
        tau_mod = modified_tau(8.0, CLOSING_300KT, SENSITIVITY_TABLE[5]["dmod"])
        self.assertAlmostEqual(tau_mod, 95.16, delta=0.01)

    def test_modified_tau_case3_20_63_s(self):
        tau_mod = modified_tau(2.0, CLOSING_300KT, SENSITIVITY_TABLE[5]["dmod"])
        self.assertAlmostEqual(tau_mod, 20.63, delta=0.01)

    def test_modified_tau_case4_sl7_95_16_s(self):
        tau_mod = modified_tau(5.0, CLOSING_180KT, SENSITIVITY_TABLE[7]["dmod"])
        self.assertAlmostEqual(tau_mod, 95.16, delta=0.01)

    def test_modified_tau_case5_5_25_s(self):
        tau_mod = modified_tau(1.0, CLOSING_300KT, SENSITIVITY_TABLE[5]["dmod"])
        self.assertAlmostEqual(tau_mod, 5.25, delta=0.01)

    def test_modified_tau_zero_at_or_inside_dmod(self):
        self.assertEqual(modified_tau(0.75, CLOSING_300KT, 0.75), 0.0)
        self.assertEqual(modified_tau(0.5, CLOSING_300KT, 0.75), 0.0)

    def test_modified_tau_rejects_nonpositive_range_and_dmod(self):
        with self.assertRaises(ValueError):
            modified_tau(0.0, CLOSING_300KT, 0.75)
        with self.assertRaises(ValueError):
            modified_tau(-2.0, CLOSING_300KT, 0.75)
        with self.assertRaises(ValueError):
            modified_tau(3.0, CLOSING_300KT, 0.0)
        with self.assertRaises(ValueError):
            modified_tau(3.0, CLOSING_300KT, -0.5)

    def test_modified_tau_rejects_non_closing_range_rate(self):
        with self.assertRaises(ValueError):
            modified_tau(3.0, 0.0, 0.75)
        with self.assertRaises(ValueError):
            modified_tau(3.0, 0.1, 0.75)


class TestThreatVerdict(unittest.TestCase):
    def test_verdict_case1_threat_sense_descend(self):
        verdict = threat_verdict(3.0, CLOSING_300KT, 8000, 8200)
        self.assertEqual(verdict["sensitivity_level"], 5)
        self.assertAlmostEqual(verdict["modified_tau"], 33.75, delta=0.01)
        self.assertTrue(verdict["threat"])
        self.assertEqual(verdict["sense"], "descend")
        self.assertEqual(verdict["vertical_separation_ft"], 200)
        self.assertEqual(verdict["tau_threshold"], 40.0)
        self.assertEqual(verdict["dmod"], 0.75)
        self.assertEqual(verdict["alim"], 350.0)

    def test_verdict_case2_tau_exceeded_reason(self):
        verdict = threat_verdict(8.0, CLOSING_300KT, 8000, 8200)
        self.assertAlmostEqual(verdict["modified_tau"], 95.16, delta=0.01)
        self.assertFalse(verdict["threat"])
        self.assertEqual(verdict["reason"], "tau-exceeded")
        self.assertNotIn("sense", verdict)

    def test_verdict_case3_threat_sense_climb(self):
        verdict = threat_verdict(2.0, CLOSING_300KT, 8000, 7800)
        self.assertAlmostEqual(verdict["modified_tau"], 20.63, delta=0.01)
        self.assertTrue(verdict["threat"])
        self.assertEqual(verdict["sense"], "climb")
        self.assertEqual(verdict["vertical_separation_ft"], -200)

    def test_verdict_case4_sl7_tau_gate_holds_at_long_range(self):
        verdict = threat_verdict(5.0, CLOSING_180KT, 30000, 29500)
        self.assertEqual(verdict["sensitivity_level"], 7)
        self.assertAlmostEqual(verdict["modified_tau"], 95.16, delta=0.01)
        self.assertEqual(verdict["alim"], 600.0)
        self.assertLessEqual(abs(verdict["vertical_separation_ft"]), 600)
        self.assertFalse(verdict["threat"])
        self.assertEqual(verdict["reason"], "tau-exceeded")

    def test_verdict_case5_dmod_influence_threat_descend(self):
        verdict = threat_verdict(1.0, CLOSING_300KT, 5000, 5100)
        self.assertEqual(verdict["sensitivity_level"], 5)
        self.assertAlmostEqual(verdict["modified_tau"], 5.25, delta=0.01)
        self.assertTrue(verdict["threat"])
        self.assertEqual(verdict["sense"], "descend")

    def test_verdict_not_closing_gate_no_threat(self):
        for rate in (0.0, 0.08333):
            verdict = threat_verdict(3.0, rate, 8000, 8200)
            self.assertFalse(verdict["threat"])
            self.assertEqual(verdict["reason"], "not-closing")
            self.assertIsNone(verdict["modified_tau"])

    def test_verdict_altitude_exceeded_reason(self):
        verdict = threat_verdict(1.0, CLOSING_300KT, 8000, 9500)
        self.assertFalse(verdict["threat"])
        self.assertEqual(verdict["reason"], "altitude-exceeded")
        self.assertEqual(verdict["vertical_separation_ft"], 1500)


class TestRaSense(unittest.TestCase):
    def test_ra_sense_descend_when_intruder_above(self):
        self.assertEqual(ra_sense(8200, 8000), "descend")
        self.assertEqual(ra_sense(30000, 8000), "descend")

    def test_ra_sense_climb_below_or_tie(self):
        self.assertEqual(ra_sense(7800, 8000), "climb")
        self.assertEqual(ra_sense(5000, 30000), "climb")
        self.assertEqual(ra_sense(8000, 8000), "climb")


class TestEvaluateEncounter(unittest.TestCase):
    def test_evaluate_case1_full_chain_descend(self):
        result = evaluate_encounter(3.0, CLOSING_300KT, 8000, 8200)
        self.assertEqual(result["sensitivity_level"], 5)
        self.assertAlmostEqual(result["modified_tau"], 33.75, delta=0.01)
        self.assertTrue(result["threat"])
        self.assertEqual(result["sense"], "descend")
        self.assertEqual(result["resolution_advisory"], "descend")
        self.assertEqual(result["parameters"], {"tau": 40.0, "dmod": 0.75, "alim": 350.0})

    def test_evaluate_case3_climb_advisory(self):
        result = evaluate_encounter(2.0, CLOSING_300KT, 8000, 7800)
        self.assertTrue(result["threat"])
        self.assertEqual(result["sense"], "climb")
        self.assertEqual(result["resolution_advisory"], "climb")

    def test_evaluate_tau_exceeded_gives_none(self):
        result = evaluate_encounter(8.0, CLOSING_300KT, 8000, 8200)
        self.assertFalse(result["threat"])
        self.assertEqual(result["reason"], "tau-exceeded")
        self.assertEqual(result["resolution_advisory"], "none")

    def test_evaluate_sl7_long_range_gives_none(self):
        result = evaluate_encounter(5.0, CLOSING_180KT, 30000, 29500)
        self.assertEqual(result["sensitivity_level"], 7)
        self.assertFalse(result["threat"])
        self.assertEqual(result["reason"], "tau-exceeded")
        self.assertEqual(result["resolution_advisory"], "none")

    def test_evaluate_altitude_exceeded_and_not_closing_give_none(self):
        altitude_result = evaluate_encounter(1.0, CLOSING_300KT, 8000, 9500)
        self.assertEqual(altitude_result["reason"], "altitude-exceeded")
        self.assertEqual(altitude_result["resolution_advisory"], "none")
        closing_result = evaluate_encounter(3.0, 0.0, 8000, 8200)
        self.assertEqual(closing_result["reason"], "not-closing")
        self.assertIsNone(closing_result["modified_tau"])
        self.assertEqual(closing_result["resolution_advisory"], "none")

    def test_evaluate_valueerrors_propagate(self):
        with self.assertRaises(ValueError):
            evaluate_encounter(3.0, CLOSING_300KT, -100, 8200)
        with self.assertRaises(ValueError):
            evaluate_encounter(0.0, CLOSING_300KT, 8000, 8200)


if __name__ == "__main__":
    unittest.main()
