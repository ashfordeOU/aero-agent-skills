"""
Tests for aeroelastic_analysis_logic — ECSS E-ST-32C clause 4.6.2.17
stdlib unittest only; offline; deterministic. Run: python3 test_aeroelastic_analysis.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aeroelastic_analysis_logic import (
    AeroelasticError,
    AeroelasticFinding,
    DIVERGENCE_SPEED_MARGIN,
    FLUTTER_SPEED_MARGIN,
    MIN_FREQUENCY_SEPARATION,
    REGIME_COUPLED_RISK,
    REGIME_DIVERGENCE_RISK,
    REGIME_FLUTTER_RISK,
    REGIME_STABLE,
    SurfaceDefinition,
    assess_surface,
    categorize_aeroelastic_regime,
    compute_divergence_margin,
    compute_dynamic_pressure,
    compute_flutter_margin,
    compute_frequency_separation,
    is_assessment_compliant,
    run_aeroelastic_assessment,
)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _stable_surface(name: str = "fin-A") -> SurfaceDefinition:
    """Surface where all three margins comfortably exceed thresholds."""
    return SurfaceDefinition(
        name=name,
        design_speed=100.0,
        flutter_speed=130.0,      # 30 % margin
        divergence_speed=135.0,   # 35 % margin
        structural_freq_hz=15.0,
        aerodynamic_freq_hz=5.0,  # separation = 10/5 = 2.0 (200 %)
    )


def _flutter_risk_surface(name: str = "fin-B") -> SurfaceDefinition:
    return SurfaceDefinition(
        name=name,
        design_speed=100.0,
        flutter_speed=107.0,      # 7 % margin — below 15 %
        divergence_speed=135.0,
        structural_freq_hz=15.0,
        aerodynamic_freq_hz=5.0,
    )


def _divergence_risk_surface(name: str = "fin-C") -> SurfaceDefinition:
    return SurfaceDefinition(
        name=name,
        design_speed=100.0,
        flutter_speed=130.0,
        divergence_speed=108.0,   # 8 % margin — below 15 %
        structural_freq_hz=15.0,
        aerodynamic_freq_hz=5.0,
    )


def _coupled_risk_surface(name: str = "fin-D") -> SurfaceDefinition:
    return SurfaceDefinition(
        name=name,
        design_speed=100.0,
        flutter_speed=107.0,      # flutter margin violated
        divergence_speed=108.0,   # divergence margin violated
        structural_freq_hz=15.0,
        aerodynamic_freq_hz=5.0,
    )


def _freq_coupled_surface(name: str = "fin-E") -> SurfaceDefinition:
    """Speed margins adequate but frequency separation too close."""
    return SurfaceDefinition(
        name=name,
        design_speed=100.0,
        flutter_speed=130.0,
        divergence_speed=135.0,
        structural_freq_hz=10.0,
        aerodynamic_freq_hz=9.5,  # separation = 0.5/9.5 ≈ 0.053 — below 0.10
    )


# ---------------------------------------------------------------------------
# Dynamic pressure
# ---------------------------------------------------------------------------

class TestComputeDynamicPressure(unittest.TestCase):
    def test_sea_level_standard_atmosphere(self):
        q = compute_dynamic_pressure(1.225, 100.0)
        self.assertAlmostEqual(q, 0.5 * 1.225 * 10000.0, places=6)

    def test_zero_velocity_gives_zero(self):
        self.assertEqual(compute_dynamic_pressure(1.225, 0.0), 0.0)

    def test_zero_density_gives_zero(self):
        self.assertEqual(compute_dynamic_pressure(0.0, 100.0), 0.0)

    def test_negative_density_raises(self):
        with self.assertRaises(AeroelasticError):
            compute_dynamic_pressure(-0.5, 100.0)

    def test_negative_velocity_raises(self):
        with self.assertRaises(AeroelasticError):
            compute_dynamic_pressure(1.225, -1.0)


# ---------------------------------------------------------------------------
# Flutter margin
# ---------------------------------------------------------------------------

class TestComputeFlutterMargin(unittest.TestCase):
    def test_15_percent_margin(self):
        margin = compute_flutter_margin(115.0, 100.0)
        self.assertAlmostEqual(margin, 0.15, places=10)

    def test_negative_margin_when_flutter_speed_below_design(self):
        margin = compute_flutter_margin(90.0, 100.0)
        self.assertAlmostEqual(margin, -0.10, places=10)

    def test_zero_design_speed_raises(self):
        with self.assertRaises(AeroelasticError):
            compute_flutter_margin(100.0, 0.0)

    def test_zero_flutter_speed_raises(self):
        with self.assertRaises(AeroelasticError):
            compute_flutter_margin(0.0, 100.0)

    def test_equal_speeds_gives_zero_margin(self):
        self.assertAlmostEqual(compute_flutter_margin(100.0, 100.0), 0.0, places=10)


# ---------------------------------------------------------------------------
# Divergence margin
# ---------------------------------------------------------------------------

class TestComputeDivergenceMargin(unittest.TestCase):
    def test_20_percent_margin(self):
        margin = compute_divergence_margin(120.0, 100.0)
        self.assertAlmostEqual(margin, 0.20, places=10)

    def test_insufficient_margin(self):
        margin = compute_divergence_margin(108.0, 100.0)
        self.assertAlmostEqual(margin, 0.08, places=10)

    def test_zero_design_speed_raises(self):
        with self.assertRaises(AeroelasticError):
            compute_divergence_margin(120.0, 0.0)


# ---------------------------------------------------------------------------
# Frequency separation
# ---------------------------------------------------------------------------

class TestComputeFrequencySeparation(unittest.TestCase):
    def test_double_frequency_gives_separation_one(self):
        sep = compute_frequency_separation(10.0, 5.0)
        self.assertAlmostEqual(sep, 1.0, places=10)

    def test_identical_frequencies_give_zero(self):
        self.assertAlmostEqual(compute_frequency_separation(8.0, 8.0), 0.0, places=10)

    def test_separation_symmetric(self):
        sep_ab = compute_frequency_separation(10.0, 9.0)
        sep_ba = compute_frequency_separation(9.0, 10.0)
        self.assertAlmostEqual(sep_ab, sep_ba, places=10)

    def test_zero_structural_freq_raises(self):
        with self.assertRaises(AeroelasticError):
            compute_frequency_separation(0.0, 5.0)

    def test_zero_aerodynamic_freq_raises(self):
        with self.assertRaises(AeroelasticError):
            compute_frequency_separation(5.0, 0.0)


# ---------------------------------------------------------------------------
# Regime categorization
# ---------------------------------------------------------------------------

class TestCategorizeAeroelasticRegime(unittest.TestCase):
    def test_all_margins_adequate_is_stable(self):
        regime = categorize_aeroelastic_regime(0.20, 0.20, 0.20)
        self.assertEqual(regime, REGIME_STABLE)

    def test_flutter_margin_violated_only(self):
        regime = categorize_aeroelastic_regime(0.05, 0.20, 0.20)
        self.assertEqual(regime, REGIME_FLUTTER_RISK)

    def test_divergence_margin_violated_only(self):
        regime = categorize_aeroelastic_regime(0.20, 0.05, 0.20)
        self.assertEqual(regime, REGIME_DIVERGENCE_RISK)

    def test_both_speed_margins_violated(self):
        regime = categorize_aeroelastic_regime(0.05, 0.05, 0.20)
        self.assertEqual(regime, REGIME_COUPLED_RISK)

    def test_freq_separation_violated_with_adequate_speed_margins(self):
        regime = categorize_aeroelastic_regime(0.20, 0.20, 0.02)
        self.assertEqual(regime, REGIME_COUPLED_RISK)

    def test_exact_threshold_is_adequate(self):
        regime = categorize_aeroelastic_regime(
            FLUTTER_SPEED_MARGIN,
            DIVERGENCE_SPEED_MARGIN,
            MIN_FREQUENCY_SEPARATION,
        )
        self.assertEqual(regime, REGIME_STABLE)


# ---------------------------------------------------------------------------
# Surface assessment
# ---------------------------------------------------------------------------

class TestAssessSurface(unittest.TestCase):
    def test_stable_surface_has_no_findings(self):
        result = assess_surface(_stable_surface())
        self.assertEqual(result.regime, REGIME_STABLE)
        self.assertEqual(result.findings, [])
        self.assertTrue(result.flutter_adequate)
        self.assertTrue(result.divergence_adequate)
        self.assertTrue(result.frequency_separation_adequate)

    def test_flutter_risk_flagged(self):
        result = assess_surface(_flutter_risk_surface())
        self.assertEqual(result.regime, REGIME_FLUTTER_RISK)
        self.assertFalse(result.flutter_adequate)
        self.assertTrue(any("Flutter" in f for f in result.findings))

    def test_divergence_risk_flagged(self):
        result = assess_surface(_divergence_risk_surface())
        self.assertEqual(result.regime, REGIME_DIVERGENCE_RISK)
        self.assertFalse(result.divergence_adequate)
        self.assertTrue(any("Divergence" in f for f in result.findings))

    def test_coupled_risk_produces_two_findings(self):
        result = assess_surface(_coupled_risk_surface())
        self.assertEqual(result.regime, REGIME_COUPLED_RISK)
        self.assertEqual(len(result.findings), 2)

    def test_frequency_coupling_flagged(self):
        result = assess_surface(_freq_coupled_surface())
        self.assertEqual(result.regime, REGIME_COUPLED_RISK)
        self.assertFalse(result.frequency_separation_adequate)
        self.assertTrue(any("Frequency" in f for f in result.findings))

    def test_surface_name_preserved_in_finding(self):
        result = assess_surface(_stable_surface("nozzle-fairing"))
        self.assertEqual(result.surface, "nozzle-fairing")

    def test_margins_stored_correctly(self):
        result = assess_surface(_stable_surface())
        self.assertAlmostEqual(result.flutter_margin, 0.30, places=10)
        self.assertAlmostEqual(result.divergence_margin, 0.35, places=10)

    def test_finding_is_aeroelastic_finding_type(self):
        result = assess_surface(_stable_surface())
        self.assertIsInstance(result, AeroelasticFinding)


# ---------------------------------------------------------------------------
# Full assessment run
# ---------------------------------------------------------------------------

class TestRunAeroelasticAssessment(unittest.TestCase):
    def test_all_stable_surfaces_pass_compliance(self):
        surfaces = [_stable_surface(f"fin-{i}") for i in range(3)]
        findings = run_aeroelastic_assessment(surfaces)
        self.assertTrue(is_assessment_compliant(findings))

    def test_one_noncompliant_surface_fails_overall(self):
        surfaces = [_stable_surface("fin-A"), _flutter_risk_surface("fin-B")]
        findings = run_aeroelastic_assessment(surfaces)
        self.assertFalse(is_assessment_compliant(findings))

    def test_result_count_equals_input_count(self):
        surfaces = [_stable_surface(f"fin-{i}") for i in range(5)]
        findings = run_aeroelastic_assessment(surfaces)
        self.assertEqual(len(findings), 5)

    def test_empty_surface_list_raises(self):
        with self.assertRaises(AeroelasticError):
            run_aeroelastic_assessment([])

    def test_all_risk_regimes_detectable_in_single_run(self):
        surfaces = [
            _flutter_risk_surface("s1"),
            _divergence_risk_surface("s2"),
            _coupled_risk_surface("s3"),
            _freq_coupled_surface("s4"),
        ]
        findings = run_aeroelastic_assessment(surfaces)
        regimes = {f.regime for f in findings}
        self.assertIn(REGIME_FLUTTER_RISK, regimes)
        self.assertIn(REGIME_DIVERGENCE_RISK, regimes)
        self.assertIn(REGIME_COUPLED_RISK, regimes)

    def test_single_stable_surface_is_compliant(self):
        findings = run_aeroelastic_assessment([_stable_surface()])
        self.assertTrue(is_assessment_compliant(findings))


if __name__ == "__main__":
    unittest.main()
