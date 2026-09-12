"""
Gate 3 contract tests for e1012-bio-env-limits.
Stdlib unittest only; deterministic; offline.  Run:
    python3 test_e1012_bio_env_limits.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_bio_env_limits_logic import (
    categorize_environment,
    assess_orbit_environments,
    age_bracket,
    career_bfo_limit_mSv,
    check_short_term_dose,
    check_career_bfo_dose,
    assess_crew_member,
    SHORT_TERM_ORGAN_LIMITS,
    ENVIRONMENT_TYPES,
    VALID_ORGANS,
    VALID_PERIODS,
)


# ---------------------------------------------------------------------------
# Environment categorization
# ---------------------------------------------------------------------------

class TestCategorizeEnvironment(unittest.TestCase):

    def test_gcr_keyword_returns_gcr(self):
        self.assertEqual(categorize_environment("gcr"), "GCR")

    def test_galactic_returns_gcr(self):
        self.assertEqual(categorize_environment("galactic"), "GCR")

    def test_solar_returns_spe(self):
        self.assertEqual(categorize_environment("solar"), "SPE")

    def test_spe_keyword_returns_spe(self):
        self.assertEqual(categorize_environment("spe"), "SPE")

    def test_saa_returns_trapped_proton(self):
        self.assertEqual(categorize_environment("saa"), "TRAPPED_PROTON")

    def test_inner_belt_returns_trapped_proton(self):
        self.assertEqual(categorize_environment("inner_belt"), "TRAPPED_PROTON")

    def test_outer_belt_returns_trapped_electron(self):
        self.assertEqual(categorize_environment("outer_belt"), "TRAPPED_ELECTRON")

    def test_electron_belt_returns_trapped_electron(self):
        self.assertEqual(categorize_environment("electron_belt"), "TRAPPED_ELECTRON")

    def test_neutron_returns_neutron(self):
        self.assertEqual(categorize_environment("neutron"), "NEUTRON")

    def test_albedo_returns_neutron(self):
        self.assertEqual(categorize_environment("albedo"), "NEUTRON")

    def test_leading_trailing_whitespace_stripped(self):
        self.assertEqual(categorize_environment("  gcr  "), "GCR")

    def test_unknown_source_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_environment("xray_background_unknown")

    def test_non_string_input_raises_type_error(self):
        with self.assertRaises(TypeError):
            categorize_environment(42)

    def test_none_input_raises_type_error(self):
        with self.assertRaises(TypeError):
            categorize_environment(None)


# ---------------------------------------------------------------------------
# Orbit environment assessment
# ---------------------------------------------------------------------------

class TestAssessOrbitEnvironments(unittest.TestCase):

    def test_iss_orbit_includes_gcr_neutron_trapped_proton_spe(self):
        # ISS: ~400 km, 51.6 deg inclination
        envs = assess_orbit_environments(400, 51.6)
        self.assertIn("GCR", envs)
        self.assertIn("NEUTRON", envs)
        self.assertIn("TRAPPED_PROTON", envs)
        self.assertIn("SPE", envs)

    def test_low_inclination_leo_no_spe(self):
        # Equatorial LEO, 28.5 deg — no polar-horn SPE access
        envs = assess_orbit_environments(400, 28.5)
        self.assertNotIn("SPE", envs)
        self.assertIn("GCR", envs)
        self.assertIn("TRAPPED_PROTON", envs)

    def test_meo_orbit_includes_trapped_electron(self):
        # 20 000 km MEO — in outer electron belt region
        envs = assess_orbit_environments(20000, 0)
        self.assertIn("TRAPPED_ELECTRON", envs)

    def test_low_altitude_equatorial_no_trapped_electron(self):
        # 300 km — below trapped-electron altitude threshold
        envs = assess_orbit_environments(300, 0)
        self.assertNotIn("TRAPPED_ELECTRON", envs)

    def test_polar_orbit_includes_spe(self):
        envs = assess_orbit_environments(800, 90)
        self.assertIn("SPE", envs)

    def test_exactly_50_deg_inclination_includes_spe(self):
        envs = assess_orbit_environments(600, 50.0)
        self.assertIn("SPE", envs)

    def test_49_deg_inclination_no_spe(self):
        envs = assess_orbit_environments(600, 49.0)
        self.assertNotIn("SPE", envs)

    def test_gcr_and_neutron_always_present_geo(self):
        envs = assess_orbit_environments(35786, 0)
        self.assertIn("GCR", envs)
        self.assertIn("NEUTRON", envs)

    def test_result_is_sorted_list(self):
        envs = assess_orbit_environments(400, 51.6)
        self.assertEqual(envs, sorted(envs))

    def test_zero_altitude_raises_value_error(self):
        with self.assertRaises(ValueError):
            assess_orbit_environments(0, 28.5)

    def test_negative_altitude_raises_value_error(self):
        with self.assertRaises(ValueError):
            assess_orbit_environments(-100, 28.5)

    def test_inclination_above_180_raises_value_error(self):
        with self.assertRaises(ValueError):
            assess_orbit_environments(400, 200)

    def test_inclination_below_zero_raises_value_error(self):
        with self.assertRaises(ValueError):
            assess_orbit_environments(400, -1)


# ---------------------------------------------------------------------------
# Age bracket
# ---------------------------------------------------------------------------

class TestAgeBracket(unittest.TestCase):

    def test_age_30_returns_25_35(self):
        self.assertEqual(age_bracket(30), "25-35")

    def test_age_35_returns_35_45(self):
        self.assertEqual(age_bracket(35), "35-45")

    def test_age_44_returns_35_45(self):
        self.assertEqual(age_bracket(44), "35-45")

    def test_age_45_returns_45_55(self):
        self.assertEqual(age_bracket(45), "45-55")

    def test_age_55_returns_55_plus(self):
        self.assertEqual(age_bracket(55), "55+")

    def test_age_70_returns_55_plus(self):
        self.assertEqual(age_bracket(70), "55+")

    def test_age_17_raises_value_error(self):
        with self.assertRaises(ValueError):
            age_bracket(17)

    def test_float_age_raises_value_error(self):
        with self.assertRaises(ValueError):
            age_bracket(35.5)


# ---------------------------------------------------------------------------
# Career BFO limit lookup
# ---------------------------------------------------------------------------

class TestCareerBfoLimitMSv(unittest.TestCase):

    def test_male_age_40_returns_2500(self):
        self.assertEqual(career_bfo_limit_mSv("M", 40), 2500.0)

    def test_female_age_30_returns_1000(self):
        self.assertEqual(career_bfo_limit_mSv("F", 30), 1000.0)

    def test_male_age_60_returns_4000(self):
        self.assertEqual(career_bfo_limit_mSv("M", 60), 4000.0)

    def test_female_age_50_returns_2500(self):
        self.assertEqual(career_bfo_limit_mSv("F", 50), 2500.0)

    def test_invalid_sex_raises_value_error(self):
        with self.assertRaises(ValueError):
            career_bfo_limit_mSv("X", 40)

    def test_unknown_sex_empty_string_raises(self):
        with self.assertRaises(ValueError):
            career_bfo_limit_mSv("", 40)


# ---------------------------------------------------------------------------
# Short-term organ dose checks
# ---------------------------------------------------------------------------

class TestCheckShortTermDose(unittest.TestCase):

    def test_bfo_30d_compliant(self):
        result = check_short_term_dose("BFO", 100.0, "30d")
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_mGy_Eq"], 150.0)

    def test_bfo_30d_exceedance(self):
        result = check_short_term_dose("BFO", 300.0, "30d")
        self.assertFalse(result["compliant"])
        self.assertLess(result["margin_mGy_Eq"], 0.0)

    def test_bfo_at_exact_30d_limit_is_compliant(self):
        limit = SHORT_TERM_ORGAN_LIMITS["30d"]["BFO"]
        result = check_short_term_dose("BFO", limit, "30d")
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_mGy_Eq"], 0.0)

    def test_eye_lens_annual_exceedance(self):
        result = check_short_term_dose("eye_lens", 2500.0, "annual")
        self.assertFalse(result["compliant"])

    def test_skin_30d_limit_value_is_1500(self):
        result = check_short_term_dose("skin", 0.0, "30d")
        self.assertEqual(result["limit_mGy_Eq"], 1500.0)

    def test_skin_annual_limit_value_is_6000(self):
        result = check_short_term_dose("skin", 0.0, "annual")
        self.assertEqual(result["limit_mGy_Eq"], 6000.0)

    def test_result_contains_all_expected_keys(self):
        result = check_short_term_dose("BFO", 50.0, "30d")
        for key in ("organ", "period", "dose_mGy_Eq", "limit_mGy_Eq",
                    "compliant", "margin_mGy_Eq"):
            self.assertIn(key, result)

    def test_unknown_organ_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_short_term_dose("liver", 50.0, "30d")

    def test_unknown_period_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_short_term_dose("BFO", 50.0, "weekly")

    def test_negative_dose_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_short_term_dose("BFO", -1.0, "30d")


# ---------------------------------------------------------------------------
# Career BFO dose check
# ---------------------------------------------------------------------------

class TestCheckCareerBfoDose(unittest.TestCase):

    def test_male_age_45_compliant(self):
        # limit for M, 45-55 is 3000 mSv
        result = check_career_bfo_dose(2000.0, "M", 45)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_mSv"], 1000.0)

    def test_female_age_30_exceedance(self):
        # limit for F, 25-35 is 1000 mSv
        result = check_career_bfo_dose(1200.0, "F", 30)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["margin_mSv"], -200.0)

    def test_at_exact_career_limit_is_compliant(self):
        limit = career_bfo_limit_mSv("M", 40)  # 2500
        result = check_career_bfo_dose(limit, "M", 40)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_mSv"], 0.0)

    def test_result_contains_sex_and_age(self):
        result = check_career_bfo_dose(500.0, "F", 42)
        self.assertEqual(result["sex"], "F")
        self.assertEqual(result["age"], 42)

    def test_negative_career_dose_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_career_bfo_dose(-10.0, "M", 40)


# ---------------------------------------------------------------------------
# Full crew member assessment
# ---------------------------------------------------------------------------

class TestAssessCrewMember(unittest.TestCase):

    def _nominal_profile(self, career_bfo=400.0, sex="M", age=38,
                         bfo_30d=50.0, eye_30d=100.0, skin_30d=200.0,
                         bfo_annual=200.0, eye_annual=400.0, skin_annual=800.0):
        return {
            "sex": sex,
            "age": age,
            "career_bfo_mSv": career_bfo,
            "doses": {
                "30d": {"BFO": bfo_30d, "eye_lens": eye_30d, "skin": skin_30d},
                "annual": {
                    "BFO": bfo_annual,
                    "eye_lens": eye_annual,
                    "skin": skin_annual,
                },
            },
        }

    def test_fully_compliant_crew_member_has_no_findings(self):
        result = assess_crew_member(self._nominal_profile())
        self.assertTrue(result["all_compliant"])
        self.assertEqual(result["findings"], [])

    def test_bfo_30d_exceedance_is_detected(self):
        # BFO 30d limit is 250 mGy-Eq; supply 300
        profile = self._nominal_profile(bfo_30d=300.0)
        result = assess_crew_member(profile)
        self.assertFalse(result["all_compliant"])
        organs_with_findings = [f.get("organ") for f in result["findings"]]
        self.assertIn("BFO", organs_with_findings)

    def test_eye_lens_annual_exceedance_is_detected(self):
        # eye_lens annual limit is 2000 mGy-Eq; supply 2500
        profile = self._nominal_profile(eye_annual=2500.0)
        result = assess_crew_member(profile)
        self.assertFalse(result["all_compliant"])

    def test_career_exceedance_is_detected(self):
        # F, age 30, career limit is 1000 mSv; supply 1200
        profile = self._nominal_profile(career_bfo=1200.0, sex="F", age=30)
        result = assess_crew_member(profile)
        self.assertFalse(result["all_compliant"])

    def test_short_term_results_count_is_six(self):
        # 2 periods × 3 organs = 6 short-term results
        result = assess_crew_member(self._nominal_profile())
        self.assertEqual(len(result["short_term"]), 6)

    def test_missing_profile_key_raises_value_error(self):
        with self.assertRaises(ValueError):
            assess_crew_member({"sex": "M", "age": 40})

    def test_career_result_present_in_return(self):
        result = assess_crew_member(self._nominal_profile())
        self.assertIn("career", result)
        self.assertIn("compliant", result["career"])

    def test_multiple_exceedances_all_appear_in_findings(self):
        # BFO 30d and skin 30d both exceed limits
        profile = self._nominal_profile(bfo_30d=300.0, skin_30d=1600.0)
        result = assess_crew_member(profile)
        self.assertFalse(result["all_compliant"])
        self.assertGreaterEqual(len(result["findings"]), 2)


# ---------------------------------------------------------------------------
# Environment type table completeness
# ---------------------------------------------------------------------------

class TestEnvironmentTypesTable(unittest.TestCase):

    def test_all_five_environment_types_defined(self):
        expected = {"GCR", "SPE", "TRAPPED_PROTON", "TRAPPED_ELECTRON", "NEUTRON"}
        self.assertEqual(set(ENVIRONMENT_TYPES.keys()), expected)

    def test_all_environment_descriptions_are_non_empty_strings(self):
        for key, desc in ENVIRONMENT_TYPES.items():
            self.assertIsInstance(desc, str, msg=key)
            self.assertGreater(len(desc.strip()), 0, msg=key)

    def test_valid_organs_matches_30d_limit_keys(self):
        self.assertEqual(VALID_ORGANS, frozenset(SHORT_TERM_ORGAN_LIMITS["30d"]))

    def test_valid_periods_contains_30d_and_annual(self):
        self.assertIn("30d", VALID_PERIODS)
        self.assertIn("annual", VALID_PERIODS)


if __name__ == "__main__":
    unittest.main()
