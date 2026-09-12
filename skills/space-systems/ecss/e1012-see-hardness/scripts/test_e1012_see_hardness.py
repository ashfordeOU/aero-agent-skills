#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-12C §9.5 SEE hardness assurance.

Exercises scripts/e1012_see_hardness_logic.py (stdlib unittest, offline).
Contract: an SEE effect type is either destructive or non-destructive, and
an unrecognized type raises; the Weibull cross-section returns zero below
the onset threshold and the correct saturated-exponential value above it,
and invalid parameters raise; the ion SEE rate integrates σ(LET)×flux
over the heavy-ion spectrum, returning zero for an ion-immune device; the
proton/neutron SEE rate integrates σ(E)×flux over the energy spectrum,
returning zero for a proton-immune device; assign_hardness_assurance_category
returns HA1 for destructive effects, HA2 for non-destructive effects with
a rate violation, and HA3 otherwise; the full device review aggregates
findings correctly and is_see_hardness_compliant reflects the presence or
absence of findings.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1012_see_hardness_logic as sh  # noqa: E402


# ── SEE effect type categorization ────────────────────────────────────────

class CategorizeSeeEffectTest(unittest.TestCase):
    def test_sel_is_destructive(self):
        self.assertEqual(sh.categorize_see_effect("sel"), "destructive")

    def test_seb_is_destructive(self):
        self.assertEqual(sh.categorize_see_effect("seb"), "destructive")

    def test_segr_is_destructive(self):
        self.assertEqual(sh.categorize_see_effect("segr"), "destructive")

    def test_seu_is_non_destructive(self):
        self.assertEqual(sh.categorize_see_effect("seu"), "non_destructive")

    def test_sefi_is_non_destructive(self):
        self.assertEqual(sh.categorize_see_effect("sefi"), "non_destructive")

    def test_setr_is_non_destructive(self):
        self.assertEqual(sh.categorize_see_effect("setr"), "non_destructive")

    def test_sehe_is_non_destructive(self):
        self.assertEqual(sh.categorize_see_effect("sehe"), "non_destructive")

    def test_unknown_effect_type_raises(self):
        with self.assertRaises(ValueError):
            sh.categorize_see_effect("phantom_event")


# ── Weibull cross-section ──────────────────────────────────────────────────

class WeibullCrossSectionTest(unittest.TestCase):
    def test_at_threshold_returns_zero(self):
        self.assertEqual(sh.weibull_cross_section(10.0, 10.0, 1e-6, 5.0, 1.0), 0.0)

    def test_below_threshold_returns_zero(self):
        self.assertEqual(sh.weibull_cross_section(5.0, 10.0, 1e-6, 5.0, 1.0), 0.0)

    def test_far_above_threshold_approaches_sigma_sat(self):
        sigma_sat = 1e-6
        result = sh.weibull_cross_section(200.0, 1.0, sigma_sat, 5.0, 1.0)
        self.assertAlmostEqual(result, sigma_sat, places=10)

    def test_midpoint_value_matches_weibull_formula(self):
        threshold, sigma_sat, width, shape = 2.0, 1e-5, 4.0, 2.0
        x = 4.0
        expected = sigma_sat * (1.0 - math.exp(-((x - threshold) / width) ** shape))
        self.assertAlmostEqual(
            sh.weibull_cross_section(x, threshold, sigma_sat, width, shape),
            expected,
        )

    def test_zero_sigma_sat_raises(self):
        with self.assertRaises(ValueError):
            sh.weibull_cross_section(10.0, 1.0, 0.0, 5.0, 1.0)

    def test_negative_sigma_sat_raises(self):
        with self.assertRaises(ValueError):
            sh.weibull_cross_section(10.0, 1.0, -1e-6, 5.0, 1.0)

    def test_zero_width_raises(self):
        with self.assertRaises(ValueError):
            sh.weibull_cross_section(10.0, 1.0, 1e-6, 0.0, 1.0)

    def test_zero_shape_raises(self):
        with self.assertRaises(ValueError):
            sh.weibull_cross_section(10.0, 1.0, 1e-6, 5.0, 0.0)


# ── Ion immunity ───────────────────────────────────────────────────────────

class IonImmunityTest(unittest.TestCase):
    def test_at_immunity_threshold_is_immune(self):
        self.assertTrue(sh.is_ion_immune(37.0))

    def test_above_immunity_threshold_is_immune(self):
        self.assertTrue(sh.is_ion_immune(50.0))

    def test_below_immunity_threshold_not_immune(self):
        self.assertFalse(sh.is_ion_immune(10.0))


# ── Proton immunity ────────────────────────────────────────────────────────

class ProtonImmunityTest(unittest.TestCase):
    def test_at_immunity_threshold_is_immune(self):
        self.assertTrue(sh.is_proton_immune(200.0))

    def test_above_immunity_threshold_is_immune(self):
        self.assertTrue(sh.is_proton_immune(250.0))

    def test_below_immunity_threshold_not_immune(self):
        self.assertFalse(sh.is_proton_immune(50.0))


# ── Ion SEE rate ───────────────────────────────────────────────────────────

class IonSeeRateTest(unittest.TestCase):
    def test_ion_immune_device_returns_zero(self):
        spectrum = [{"let_mev_cm2_mg": 5.0, "flux_per_cm2_per_day": 1e4}]
        rate = sh.ion_see_rate(37.0, 1e-6, 5.0, 1.0, spectrum)
        self.assertEqual(rate, 0.0)

    def test_all_bins_below_threshold_returns_zero(self):
        spectrum = [
            {"let_mev_cm2_mg": 1.0, "flux_per_cm2_per_day": 1e4},
            {"let_mev_cm2_mg": 2.0, "flux_per_cm2_per_day": 1e4},
        ]
        rate = sh.ion_see_rate(5.0, 1e-6, 5.0, 1.0, spectrum)
        self.assertEqual(rate, 0.0)

    def test_single_bin_above_threshold(self):
        let_thresh, sigma_sat, width, shape = 1.0, 1e-5, 10.0, 1.0
        flux = 1e6
        let_val = 11.0
        expected_sigma = sh.weibull_cross_section(let_val, let_thresh, sigma_sat, width, shape)
        spectrum = [{"let_mev_cm2_mg": let_val, "flux_per_cm2_per_day": flux}]
        rate = sh.ion_see_rate(let_thresh, sigma_sat, width, shape, spectrum)
        self.assertAlmostEqual(rate, expected_sigma * flux)

    def test_empty_spectrum_returns_zero(self):
        self.assertEqual(sh.ion_see_rate(5.0, 1e-6, 5.0, 1.0, []), 0.0)

    def test_negative_let_threshold_raises(self):
        with self.assertRaises(ValueError):
            sh.ion_see_rate(-1.0, 1e-6, 5.0, 1.0, [])

    def test_negative_flux_raises(self):
        spectrum = [{"let_mev_cm2_mg": 10.0, "flux_per_cm2_per_day": -1.0}]
        with self.assertRaises(ValueError):
            sh.ion_see_rate(1.0, 1e-6, 5.0, 1.0, spectrum)


# ── Proton/neutron SEE rate ────────────────────────────────────────────────

class ProtonNeutronSeeRateTest(unittest.TestCase):
    def test_proton_immune_device_returns_zero(self):
        spectrum = [{"energy_mev": 100.0, "flux_per_cm2_per_day": 1e5}]
        rate = sh.proton_neutron_see_rate(200.0, 1e-7, 50.0, 1.0, spectrum)
        self.assertEqual(rate, 0.0)

    def test_all_bins_below_threshold_returns_zero(self):
        spectrum = [{"energy_mev": 5.0, "flux_per_cm2_per_day": 1e5}]
        rate = sh.proton_neutron_see_rate(10.0, 1e-7, 50.0, 1.0, spectrum)
        self.assertEqual(rate, 0.0)

    def test_single_bin_above_threshold(self):
        e_thresh, sigma_sat, width, shape = 10.0, 1e-6, 20.0, 1.0
        flux = 5e5
        energy = 30.0
        expected_sigma = sh.weibull_cross_section(energy, e_thresh, sigma_sat, width, shape)
        spectrum = [{"energy_mev": energy, "flux_per_cm2_per_day": flux}]
        rate = sh.proton_neutron_see_rate(e_thresh, sigma_sat, width, shape, spectrum)
        self.assertAlmostEqual(rate, expected_sigma * flux)

    def test_empty_spectrum_returns_zero(self):
        self.assertEqual(sh.proton_neutron_see_rate(10.0, 1e-6, 5.0, 1.0, []), 0.0)

    def test_negative_energy_threshold_raises(self):
        with self.assertRaises(ValueError):
            sh.proton_neutron_see_rate(-1.0, 1e-6, 5.0, 1.0, [])

    def test_negative_flux_raises(self):
        spectrum = [{"energy_mev": 50.0, "flux_per_cm2_per_day": -1.0}]
        with self.assertRaises(ValueError):
            sh.proton_neutron_see_rate(10.0, 1e-6, 5.0, 1.0, spectrum)


# ── Rate exceeds requirement ───────────────────────────────────────────────

class RateExceedsRequirementTest(unittest.TestCase):
    def test_rate_above_requirement_is_violation(self):
        self.assertTrue(sh.rate_exceeds_requirement(1.0, 0.5))

    def test_rate_equal_to_requirement_is_not_violation(self):
        self.assertFalse(sh.rate_exceeds_requirement(0.5, 0.5))

    def test_rate_below_requirement_is_not_violation(self):
        self.assertFalse(sh.rate_exceeds_requirement(0.1, 0.5))

    def test_negative_predicted_rate_raises(self):
        with self.assertRaises(ValueError):
            sh.rate_exceeds_requirement(-0.1, 0.5)

    def test_negative_requirement_rate_raises(self):
        with self.assertRaises(ValueError):
            sh.rate_exceeds_requirement(0.1, -0.5)


# ── Hardness assurance category ────────────────────────────────────────────

class AssignHardnessAssuranceCategoryTest(unittest.TestCase):
    def test_destructive_effect_always_ha1(self):
        self.assertEqual(
            sh.assign_hardness_assurance_category("sel", 0.0, 1.0), "HA1"
        )

    def test_destructive_effect_ha1_even_when_rate_within_requirement(self):
        self.assertEqual(
            sh.assign_hardness_assurance_category("seb", 0.001, 1.0), "HA1"
        )

    def test_non_destructive_rate_violation_gives_ha2(self):
        self.assertEqual(
            sh.assign_hardness_assurance_category("seu", 2.0, 1.0), "HA2"
        )

    def test_non_destructive_rate_within_requirement_gives_ha3(self):
        self.assertEqual(
            sh.assign_hardness_assurance_category("seu", 0.5, 1.0), "HA3"
        )

    def test_non_destructive_rate_exactly_at_requirement_gives_ha3(self):
        self.assertEqual(
            sh.assign_hardness_assurance_category("sefi", 1.0, 1.0), "HA3"
        )

    def test_unknown_effect_type_raises(self):
        with self.assertRaises(ValueError):
            sh.assign_hardness_assurance_category("unknown_event", 0.0, 1.0)


# ── Full device review ─────────────────────────────────────────────────────

def _make_device(device_id, effects, let_spectrum=None, energy_spectrum=None):
    return {
        "device_id": device_id,
        "effects": effects,
        "let_spectrum": let_spectrum or [],
        "energy_spectrum": energy_spectrum or [],
    }


class SeeHardnessReviewTest(unittest.TestCase):
    def _seu_effect(self, let_thresh=1.0, e_thresh=10.0, req=1.0):
        return {
            "effect_type": "seu",
            "let_threshold": let_thresh,
            "sigma_sat_ion": 1e-6,
            "weibull_width_ion": 5.0,
            "weibull_shape_ion": 1.0,
            "energy_threshold": e_thresh,
            "sigma_sat_proton": 1e-7,
            "weibull_width_proton": 20.0,
            "weibull_shape_proton": 1.0,
            "requirement_rate": req,
        }

    def test_fully_immune_device_has_no_findings(self):
        effect = self._seu_effect(let_thresh=37.0, e_thresh=200.0)
        device = _make_device("FPGA-1", [effect])
        review = sh.see_hardness_review(device)
        self.assertEqual(review["findings"], [])
        self.assertTrue(sh.is_see_hardness_compliant(review))

    def test_compliant_device_has_no_findings(self):
        # Both spectra have bins at threshold so σ = 0, rate = 0 < requirement
        effect = self._seu_effect(let_thresh=5.0, e_thresh=50.0, req=1.0)
        spectrum_at_thresh = [{"let_mev_cm2_mg": 5.0, "flux_per_cm2_per_day": 1e6}]
        e_spectrum_at_thresh = [{"energy_mev": 50.0, "flux_per_cm2_per_day": 1e6}]
        device = _make_device(
            "FPGA-2", [effect], spectrum_at_thresh, e_spectrum_at_thresh
        )
        review = sh.see_hardness_review(device)
        self.assertEqual(review["findings"], [])
        self.assertTrue(sh.is_see_hardness_compliant(review))

    def test_rate_violation_produces_finding(self):
        effect = self._seu_effect(let_thresh=1.0, e_thresh=50.0, req=1e-10)
        let_spectrum = [{"let_mev_cm2_mg": 20.0, "flux_per_cm2_per_day": 1e8}]
        device = _make_device("SRAM-1", [effect], let_spectrum)
        review = sh.see_hardness_review(device)
        self.assertTrue(review["findings"])
        self.assertFalse(sh.is_see_hardness_compliant(review))
        self.assertEqual(review["findings"][0]["issue"], "see_rate_requirement_exceeded")

    def test_destructive_effect_gets_ha1_in_assessment(self):
        effect = {
            "effect_type": "sel",
            "let_threshold": 37.0,  # ion-immune
            "sigma_sat_ion": 1e-6,
            "weibull_width_ion": 5.0,
            "weibull_shape_ion": 1.0,
            "energy_threshold": 200.0,  # proton-immune
            "sigma_sat_proton": 1e-7,
            "weibull_width_proton": 20.0,
            "weibull_shape_proton": 1.0,
            "requirement_rate": 1.0,
        }
        device = _make_device("CMOS-1", [effect])
        review = sh.see_hardness_review(device)
        self.assertEqual(review["effect_assessments"][0]["hardness_assurance_category"], "HA1")

    def test_multiple_effects_assessed_independently(self):
        seu = self._seu_effect(let_thresh=37.0, e_thresh=200.0, req=1.0)
        sel = {
            "effect_type": "sel",
            "let_threshold": 5.0,
            "sigma_sat_ion": 1e-6,
            "weibull_width_ion": 5.0,
            "weibull_shape_ion": 1.0,
            "energy_threshold": 200.0,
            "sigma_sat_proton": 1e-7,
            "weibull_width_proton": 20.0,
            "weibull_shape_proton": 1.0,
            "requirement_rate": 1.0,
        }
        device = _make_device("DRAM-1", [seu, sel])
        review = sh.see_hardness_review(device)
        self.assertEqual(len(review["effect_assessments"]), 2)

    def test_device_id_propagated_to_finding(self):
        effect = self._seu_effect(let_thresh=1.0, e_thresh=50.0, req=1e-20)
        let_spectrum = [{"let_mev_cm2_mg": 10.0, "flux_per_cm2_per_day": 1e9}]
        device = _make_device("CUSTOM-42", [effect], let_spectrum)
        review = sh.see_hardness_review(device)
        self.assertEqual(review["device_id"], "CUSTOM-42")
        if review["findings"]:
            self.assertEqual(review["findings"][0]["device"], "CUSTOM-42")

    def test_no_effects_produces_empty_review(self):
        device = _make_device("PASSIVE-1", [])
        review = sh.see_hardness_review(device)
        self.assertEqual(review["effect_assessments"], [])
        self.assertEqual(review["findings"], [])
        self.assertTrue(sh.is_see_hardness_compliant(review))


if __name__ == "__main__":
    unittest.main()
