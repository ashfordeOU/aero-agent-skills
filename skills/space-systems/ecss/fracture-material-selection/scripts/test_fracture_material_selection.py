"""
Unit tests for fracture_material_selection_logic.py
Run: python3 test_fracture_material_selection.py
stdlib unittest only — offline, deterministic.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from fracture_material_selection_logic import (
    MaterialCandidate,
    ScreeningResult,
    screen_material,
    screen_material_list,
    summarize_screening,
    MIN_KIC_FRACTURE_CRITICAL_MPAsqrtm,
    SCC_RATIO_LIMIT_CONDITIONAL,
    SCC_RATIO_LIMIT_REJECT,
)


def _mc(**kwargs) -> MaterialCandidate:
    defaults = dict(
        name="TestAlloy",
        scc_code="A",
        kic_mpa_sqrtm=55.0,
        kiscc_mpa_sqrtm=None,
        is_fracture_critical=False,
        environment="dry",
        on_prohibited_list=False,
    )
    defaults.update(kwargs)
    return MaterialCandidate(**defaults)


class TestScreenMaterial(unittest.TestCase):

    # --- basic acceptance ---

    def test_accept_scc_code_a_dry(self):
        result = screen_material(_mc(scc_code="A", environment="dry"))
        self.assertEqual(result.verdict, "ACCEPT")
        self.assertEqual(result.findings, [])
        self.assertIsNone(result.scc_ratio)

    def test_accept_scc_code_a_propellant(self):
        """SCC code A (not susceptible) is acceptable in any environment."""
        result = screen_material(_mc(scc_code="A", environment="propellant"))
        self.assertEqual(result.verdict, "ACCEPT")
        self.assertEqual(result.findings, [])

    # --- prohibited list ---

    def test_reject_prohibited_list(self):
        result = screen_material(_mc(on_prohibited_list=True))
        self.assertEqual(result.verdict, "REJECT")
        self.assertTrue(any("prohibited list" in f for f in result.findings))

    def test_prohibited_list_short_circuits_all_other_checks(self):
        """Prohibited-list rejection returns immediately — no other findings."""
        result = screen_material(_mc(
            on_prohibited_list=True,
            kic_mpa_sqrtm=5.0,
            is_fracture_critical=True,
        ))
        self.assertEqual(result.verdict, "REJECT")
        self.assertEqual(len(result.findings), 1)

    # --- fracture-critical KIc floor ---

    def test_reject_kic_below_minimum_fracture_critical(self):
        result = screen_material(_mc(
            kic_mpa_sqrtm=15.0,
            is_fracture_critical=True,
        ))
        self.assertEqual(result.verdict, "REJECT")
        self.assertTrue(any("KIc" in f and "minimum" in f for f in result.findings))

    def test_accept_kic_at_exact_minimum_fracture_critical(self):
        result = screen_material(_mc(
            kic_mpa_sqrtm=MIN_KIC_FRACTURE_CRITICAL_MPAsqrtm,
            is_fracture_critical=True,
        ))
        self.assertEqual(result.verdict, "ACCEPT")

    def test_accept_non_fracture_critical_low_kic(self):
        """KIc floor does not apply to non-fracture-critical parts."""
        result = screen_material(_mc(kic_mpa_sqrtm=8.0, is_fracture_critical=False))
        self.assertEqual(result.verdict, "ACCEPT")

    # --- KIscc/KIc ratio ---

    def test_reject_scc_ratio_below_reject_limit(self):
        kic = 50.0
        kiscc = kic * (SCC_RATIO_LIMIT_REJECT - 0.01)  # ratio = 0.09
        result = screen_material(_mc(
            scc_code="B",
            kic_mpa_sqrtm=kic,
            kiscc_mpa_sqrtm=kiscc,
            environment="dry",
        ))
        self.assertEqual(result.verdict, "REJECT")
        self.assertAlmostEqual(result.scc_ratio, kiscc / kic, places=5)

    def test_conditional_scc_ratio_between_limits(self):
        kic = 50.0
        kiscc = kic * (SCC_RATIO_LIMIT_REJECT + 0.05)  # ratio = 0.15
        result = screen_material(_mc(
            scc_code="B",
            kic_mpa_sqrtm=kic,
            kiscc_mpa_sqrtm=kiscc,
            environment="dry",
        ))
        self.assertEqual(result.verdict, "CONDITIONAL")

    def test_accept_scc_ratio_at_conditional_limit(self):
        kic = 50.0
        kiscc = kic * SCC_RATIO_LIMIT_CONDITIONAL  # ratio = 0.25 exactly → accept
        result = screen_material(_mc(
            scc_code="B",
            kic_mpa_sqrtm=kic,
            kiscc_mpa_sqrtm=kiscc,
            environment="dry",
        ))
        self.assertEqual(result.verdict, "ACCEPT")

    def test_scc_ratio_computed_correctly(self):
        kic, kiscc = 60.0, 18.0
        result = screen_material(_mc(
            scc_code="B",
            kic_mpa_sqrtm=kic,
            kiscc_mpa_sqrtm=kiscc,
            environment="dry",
        ))
        self.assertAlmostEqual(result.scc_ratio, 18.0 / 60.0, places=6)

    # --- SCC code vs environment ---

    def test_reject_scc_code_d_moist_environment(self):
        result = screen_material(_mc(
            scc_code="D",
            kic_mpa_sqrtm=40.0,
            kiscc_mpa_sqrtm=10.0,
            environment="moist",
        ))
        self.assertEqual(result.verdict, "REJECT")
        self.assertTrue(any("code D" in f for f in result.findings))

    def test_conditional_scc_code_c_propellant_environment(self):
        result = screen_material(_mc(
            scc_code="C",
            kic_mpa_sqrtm=40.0,
            kiscc_mpa_sqrtm=15.0,
            environment="propellant",
        ))
        self.assertEqual(result.verdict, "CONDITIONAL")
        self.assertTrue(any("code C" in f for f in result.findings))

    def test_conditional_scc_code_b_aqueous_environment(self):
        kic, kiscc = 45.0, 20.0  # ratio = 0.444 (above conditional limit)
        result = screen_material(_mc(
            scc_code="B",
            kic_mpa_sqrtm=kic,
            kiscc_mpa_sqrtm=kiscc,
            environment="aqueous",
        ))
        self.assertEqual(result.verdict, "CONDITIONAL")
        self.assertTrue(any("code B" in f for f in result.findings))

    def test_accept_scc_code_b_dry_environment(self):
        kic, kiscc = 45.0, 25.0  # ratio = 0.556 (above conditional limit)
        result = screen_material(_mc(
            scc_code="B",
            kic_mpa_sqrtm=kic,
            kiscc_mpa_sqrtm=kiscc,
            environment="dry",
        ))
        self.assertEqual(result.verdict, "ACCEPT")

    def test_accept_scc_code_b_moist_environment(self):
        """Code B in moist (not severe) environment — SCC code alone does not trigger conditional."""
        kic, kiscc = 45.0, 25.0  # ratio = 0.556
        result = screen_material(_mc(
            scc_code="B",
            kic_mpa_sqrtm=kic,
            kiscc_mpa_sqrtm=kiscc,
            environment="moist",
        ))
        self.assertEqual(result.verdict, "ACCEPT")

    # --- missing KIscc in corrosive environment ---

    def test_reject_missing_kiscc_corrosive_environment(self):
        result = screen_material(_mc(
            scc_code="C",
            kic_mpa_sqrtm=40.0,
            kiscc_mpa_sqrtm=None,
            environment="moist",
        ))
        self.assertEqual(result.verdict, "REJECT")
        self.assertTrue(any("KIscc not provided" in f for f in result.findings))

    # --- input validation ---

    def test_invalid_scc_code_raises_value_error(self):
        with self.assertRaises(ValueError):
            screen_material(_mc(scc_code="X"))

    def test_invalid_environment_raises_value_error(self):
        with self.assertRaises(ValueError):
            screen_material(_mc(environment="vacuum"))

    def test_negative_kic_raises_value_error(self):
        with self.assertRaises(ValueError):
            screen_material(_mc(kic_mpa_sqrtm=-5.0))

    def test_zero_kic_raises_value_error(self):
        with self.assertRaises(ValueError):
            screen_material(_mc(kic_mpa_sqrtm=0.0))

    def test_empty_name_raises_value_error(self):
        with self.assertRaises(ValueError):
            screen_material(_mc(name=""))

    # --- batch and summary ---

    def test_batch_screening_returns_one_result_per_candidate(self):
        candidates = [
            _mc(name="M1", scc_code="A"),
            _mc(name="M2", on_prohibited_list=True),
        ]
        results = screen_material_list(candidates)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].verdict, "ACCEPT")
        self.assertEqual(results[1].verdict, "REJECT")

    def test_summary_counts_all_verdicts(self):
        candidates = [
            _mc(name="M1", scc_code="A"),
            _mc(name="M2", on_prohibited_list=True),
            _mc(name="M3", scc_code="C", kic_mpa_sqrtm=40.0,
                kiscc_mpa_sqrtm=15.0, environment="propellant"),
        ]
        results = screen_material_list(candidates)
        summary = summarize_screening(results)
        self.assertEqual(summary["ACCEPT"], 1)
        self.assertEqual(summary["REJECT"], 1)
        self.assertEqual(summary["CONDITIONAL"], 1)

    def test_result_name_matches_input_name(self):
        result = screen_material(_mc(name="Alloy-7075-T73"))
        self.assertEqual(result.name, "Alloy-7075-T73")


if __name__ == "__main__":
    unittest.main()
