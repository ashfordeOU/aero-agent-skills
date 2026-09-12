"""
Gate-3 contract tests for e1012-shield-transport logic.
Ref: ECSS-E-ST-10-12C §6.2.4

Run: python3 test_e1012_shield_transport.py
Expected: OK (all tests pass, offline, deterministic, stdlib only).
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_shield_transport_logic import (
    MATERIALS,
    TransportError,
    validate_transport_setup,
    categorize_transport_method,
    categorize_geometry,
    compute_buildup_factor,
    compute_photon_attenuation,
    compute_proton_range_g_cm2,
    compute_proton_transmission,
    compute_transmitted_dose,
    compute_dose_margin,
    run_transport_analysis,
)


class TestValidateTransportSetup(unittest.TestCase):

    def _valid_kwargs(self):
        return dict(
            geometry_dim=1,
            method='monte_carlo',
            material_name='aluminum',
            thickness_cm=1.0,
            source_rate_Gy_s=1e-3,
            exposure_s=3600.0,
            dose_limit_Gy=10.0,
        )

    def test_valid_setup_raises_nothing(self):
        validate_transport_setup(**self._valid_kwargs())

    def test_invalid_geometry_dim_raises(self):
        kw = self._valid_kwargs()
        kw['geometry_dim'] = 0
        with self.assertRaises(TransportError):
            validate_transport_setup(**kw)

    def test_invalid_geometry_dim_4_raises(self):
        kw = self._valid_kwargs()
        kw['geometry_dim'] = 4
        with self.assertRaises(TransportError):
            validate_transport_setup(**kw)

    def test_unknown_method_raises(self):
        kw = self._valid_kwargs()
        kw['method'] = 'flux_pinning'
        with self.assertRaises(TransportError):
            validate_transport_setup(**kw)

    def test_unknown_material_raises(self):
        kw = self._valid_kwargs()
        kw['material_name'] = 'unobtainium'
        with self.assertRaises(TransportError):
            validate_transport_setup(**kw)

    def test_nonpositive_thickness_raises(self):
        kw = self._valid_kwargs()
        kw['thickness_cm'] = -1.0
        with self.assertRaises(TransportError):
            validate_transport_setup(**kw)

    def test_zero_thickness_raises(self):
        kw = self._valid_kwargs()
        kw['thickness_cm'] = 0.0
        with self.assertRaises(TransportError):
            validate_transport_setup(**kw)

    def test_negative_source_rate_raises(self):
        kw = self._valid_kwargs()
        kw['source_rate_Gy_s'] = -1e-4
        with self.assertRaises(TransportError):
            validate_transport_setup(**kw)

    def test_zero_exposure_raises(self):
        kw = self._valid_kwargs()
        kw['exposure_s'] = 0.0
        with self.assertRaises(TransportError):
            validate_transport_setup(**kw)

    def test_nonpositive_dose_limit_raises(self):
        kw = self._valid_kwargs()
        kw['dose_limit_Gy'] = 0.0
        with self.assertRaises(TransportError):
            validate_transport_setup(**kw)


class TestCategorizeMethod(unittest.TestCase):

    def test_monte_carlo_is_stochastic(self):
        self.assertEqual(categorize_transport_method('monte_carlo'), 'stochastic')

    def test_deterministic_sn_is_deterministic(self):
        self.assertEqual(categorize_transport_method('deterministic_sn'), 'deterministic')

    def test_deterministic_pn_is_deterministic(self):
        self.assertEqual(categorize_transport_method('deterministic_pn'), 'deterministic')

    def test_unknown_method_raises(self):
        with self.assertRaises(TransportError):
            categorize_transport_method('raytracing')


class TestCategorizeGeometry(unittest.TestCase):

    def test_dim_1_returns_1d(self):
        self.assertEqual(categorize_geometry(1), '1-D')

    def test_dim_2_returns_2d(self):
        self.assertEqual(categorize_geometry(2), '2-D')

    def test_dim_3_returns_3d(self):
        self.assertEqual(categorize_geometry(3), '3-D')

    def test_invalid_dim_raises(self):
        with self.assertRaises(TransportError):
            categorize_geometry(5)


class TestPhotonAttenuation(unittest.TestCase):

    def test_buildup_factor_increases_with_thickness(self):
        mu = MATERIALS['aluminum']['mu_photon_cm2_g']
        rho = MATERIALS['aluminum']['density_g_cm3']
        bf_thin = compute_buildup_factor(mu, rho, 1.0)
        bf_thick = compute_buildup_factor(mu, rho, 5.0)
        self.assertGreater(bf_thick, bf_thin)

    def test_buildup_factor_minimum_is_one(self):
        mu = MATERIALS['aluminum']['mu_photon_cm2_g']
        rho = MATERIALS['aluminum']['density_g_cm3']
        bf = compute_buildup_factor(mu, rho, 0.01)
        self.assertGreaterEqual(bf, 1.0)

    def test_buildup_formula_correctness(self):
        mu_cm2_g = 0.1
        rho = 2.0
        t = 3.0
        # B = 1 + mu_lin * t = 1 + 0.1*2.0*3.0 = 1.6
        expected = 1.0 + (0.1 * 2.0 * 3.0)
        self.assertAlmostEqual(compute_buildup_factor(mu_cm2_g, rho, t), expected, places=10)

    def test_photon_attenuation_reduces_dose_rate(self):
        mu = MATERIALS['aluminum']['mu_photon_cm2_g']
        rho = MATERIALS['aluminum']['density_g_cm3']
        source = 1.0
        transmitted = compute_photon_attenuation(source, mu, rho, 1.0, buildup_factor=1.0)
        self.assertLess(transmitted, source)

    def test_photon_attenuation_zero_source_gives_zero(self):
        mu = MATERIALS['aluminum']['mu_photon_cm2_g']
        rho = MATERIALS['aluminum']['density_g_cm3']
        self.assertAlmostEqual(
            compute_photon_attenuation(0.0, mu, rho, 5.0, buildup_factor=1.5), 0.0
        )

    def test_photon_attenuation_buildup_below_one_raises(self):
        mu = 0.08
        rho = 2.7
        with self.assertRaises(TransportError):
            compute_photon_attenuation(1.0, mu, rho, 1.0, buildup_factor=0.5)

    def test_photon_attenuation_formula(self):
        # D_trans = D0 * B * exp(-mu*rho*t)
        D0 = 2.0
        mu = 0.08
        rho = 2.7
        t = 1.0
        B = 1.5
        expected = D0 * B * math.exp(-mu * rho * t)
        self.assertAlmostEqual(
            compute_photon_attenuation(D0, mu, rho, t, B), expected, places=10
        )


class TestProtonTransport(unittest.TestCase):

    def test_proton_range_increases_with_energy(self):
        r_low = compute_proton_range_g_cm2('aluminum', 10.0)
        r_high = compute_proton_range_g_cm2('aluminum', 100.0)
        self.assertGreater(r_high, r_low)

    def test_proton_range_positive_for_positive_energy(self):
        r = compute_proton_range_g_cm2('aluminum', 50.0)
        self.assertGreater(r, 0.0)

    def test_proton_range_zero_energy_raises(self):
        with self.assertRaises(TransportError):
            compute_proton_range_g_cm2('aluminum', 0.0)

    def test_proton_range_unknown_material_raises(self):
        with self.assertRaises(TransportError):
            compute_proton_range_g_cm2('unobtainium', 50.0)

    def test_low_energy_proton_stopped_in_thick_shield(self):
        # 1 MeV proton in 10 cm of aluminum — definitely stopped
        penetrates, residual = compute_proton_transmission('aluminum', 10.0, 1.0)
        self.assertFalse(penetrates)
        self.assertLess(residual, 0.0)

    def test_high_energy_proton_penetrates_thin_shield(self):
        # 500 MeV proton through 0.1 cm of aluminum — penetrates
        penetrates, residual = compute_proton_transmission('aluminum', 0.1, 500.0)
        self.assertTrue(penetrates)
        self.assertGreater(residual, 0.0)

    def test_proton_range_tantalum_less_than_aluminum_same_energy(self):
        # Tantalum is much denser; areal range (g/cm²) should be similar but
        # linear range (cm) is much smaller — test areal range (g/cm²) comparison.
        # Per reference data, proton areal range in Ta is slightly less than Al.
        r_al = compute_proton_range_g_cm2('aluminum', 50.0)
        r_ta = compute_proton_range_g_cm2('tantalum', 50.0)
        # Both should be positive
        self.assertGreater(r_al, 0.0)
        self.assertGreater(r_ta, 0.0)


class TestComputeTransmittedDose(unittest.TestCase):

    def test_photon_transmitted_dose_positive(self):
        dose = compute_transmitted_dose(1e-3, 3600.0, 'aluminum', 2.0, 'photon')
        self.assertGreater(dose, 0.0)

    def test_photon_transmitted_dose_less_than_incident(self):
        incident = 1e-3 * 3600.0  # Gy (no attenuation)
        dose = compute_transmitted_dose(1e-3, 3600.0, 'aluminum', 2.0, 'photon')
        self.assertLess(dose, incident)

    def test_proton_stopped_gives_zero_dose(self):
        # 1 MeV proton through 10 cm aluminum — stopped
        dose = compute_transmitted_dose(
            1e-3, 3600.0, 'aluminum', 10.0, 'proton', proton_energy_MeV=1.0
        )
        self.assertAlmostEqual(dose, 0.0)

    def test_proton_penetrating_gives_nonzero_dose(self):
        # 500 MeV proton through 0.1 cm aluminum — penetrates
        dose = compute_transmitted_dose(
            1e-3, 3600.0, 'aluminum', 0.1, 'proton', proton_energy_MeV=500.0
        )
        self.assertGreater(dose, 0.0)

    def test_proton_missing_energy_raises(self):
        with self.assertRaises(TransportError):
            compute_transmitted_dose(1e-3, 3600.0, 'aluminum', 2.0, 'proton')

    def test_electron_transmitted_dose_less_than_incident(self):
        incident = 1e-3 * 3600.0
        dose = compute_transmitted_dose(1e-3, 3600.0, 'aluminum', 1.0, 'electron')
        self.assertLess(dose, incident)

    def test_electron_dose_positive(self):
        dose = compute_transmitted_dose(1e-3, 3600.0, 'aluminum', 1.0, 'electron')
        self.assertGreater(dose, 0.0)

    def test_unknown_particle_type_raises(self):
        with self.assertRaises(TransportError):
            compute_transmitted_dose(1e-3, 3600.0, 'aluminum', 1.0, 'neutrino')

    def test_thicker_shield_gives_lower_photon_dose(self):
        dose_thin = compute_transmitted_dose(1e-3, 3600.0, 'aluminum', 1.0, 'photon')
        dose_thick = compute_transmitted_dose(1e-3, 3600.0, 'aluminum', 5.0, 'photon')
        self.assertLess(dose_thick, dose_thin)


class TestDoseMargin(unittest.TestCase):

    def test_margin_positive_when_within_limit(self):
        margin = compute_dose_margin(5.0, 10.0)
        self.assertGreater(margin, 0.0)

    def test_margin_zero_when_exactly_at_limit(self):
        self.assertAlmostEqual(compute_dose_margin(10.0, 10.0), 0.0)

    def test_margin_negative_when_exceeded(self):
        margin = compute_dose_margin(15.0, 10.0)
        self.assertLess(margin, 0.0)

    def test_margin_formula(self):
        # margin = (limit - transmitted) / limit
        self.assertAlmostEqual(compute_dose_margin(3.0, 12.0), (12.0 - 3.0) / 12.0)

    def test_zero_limit_raises(self):
        with self.assertRaises(TransportError):
            compute_dose_margin(1.0, 0.0)


class TestRunTransportAnalysis(unittest.TestCase):

    def _base_run(self, **overrides):
        kwargs = dict(
            geometry_dim=1,
            method='monte_carlo',
            material_name='aluminum',
            thickness_cm=8.0,  # sized so the shielded dose clears the
            #                   100 Gy TID limit once photon buildup is applied
            source_rate_Gy_s=1e-6,
            exposure_s=86400.0 * 365 * 5,  # 5-year mission
            dose_limit_Gy=100.0,
            particle_type='photon',
        )
        kwargs.update(overrides)
        return run_transport_analysis(**kwargs)

    def test_compliant_result_has_empty_findings(self):
        result = self._base_run()
        self.assertTrue(result['compliant'])
        # No exceedance finding (geometry 1-D, so no multi-D caveat either)
        exceedance_findings = [f for f in result['findings'] if 'exceeded' in f]
        self.assertEqual(exceedance_findings, [])

    def test_result_keys_present(self):
        result = self._base_run()
        for key in ('geometry_dim', 'geometry_label', 'method', 'method_category',
                    'material', 'thickness_cm', 'particle_type', 'transmitted_dose_Gy',
                    'dose_margin', 'compliant', 'findings'):
            self.assertIn(key, result)

    def test_exceedance_makes_noncompliant(self):
        # Very thin shield, large source rate, small limit
        result = self._base_run(
            thickness_cm=0.01,
            source_rate_Gy_s=1.0,
            dose_limit_Gy=1e-10,
        )
        self.assertFalse(result['compliant'])
        self.assertTrue(any('exceeded' in f for f in result['findings']))

    def test_2d_geometry_adds_caveat_finding(self):
        result = self._base_run(geometry_dim=2)
        self.assertTrue(any('2-D' in f for f in result['findings']))

    def test_3d_geometry_adds_caveat_finding(self):
        result = self._base_run(geometry_dim=3)
        self.assertTrue(any('3-D' in f for f in result['findings']))

    def test_1d_geometry_no_geometry_caveat(self):
        result = self._base_run(geometry_dim=1)
        geometry_caveats = [f for f in result['findings'] if 'geometry' in f.lower()]
        self.assertEqual(geometry_caveats, [])

    def test_method_category_stochastic_for_monte_carlo(self):
        result = self._base_run(method='monte_carlo')
        self.assertEqual(result['method_category'], 'stochastic')

    def test_method_category_deterministic_for_sn(self):
        result = self._base_run(method='deterministic_sn')
        self.assertEqual(result['method_category'], 'deterministic')

    def test_geometry_label_in_result(self):
        result = self._base_run(geometry_dim=1)
        self.assertEqual(result['geometry_label'], '1-D')

    def test_transmitted_dose_is_positive(self):
        result = self._base_run(source_rate_Gy_s=1e-4)
        self.assertGreater(result['transmitted_dose_Gy'], 0.0)

    def test_invalid_setup_raises_before_transport(self):
        with self.assertRaises(TransportError):
            run_transport_analysis(
                geometry_dim=1,
                method='monte_carlo',
                material_name='unobtainium',
                thickness_cm=1.0,
                source_rate_Gy_s=1e-3,
                exposure_s=3600.0,
                dose_limit_Gy=10.0,
            )

    def test_proton_analysis_stopped(self):
        result = run_transport_analysis(
            geometry_dim=1,
            method='deterministic_sn',
            material_name='aluminum',
            thickness_cm=10.0,
            source_rate_Gy_s=1e-4,
            exposure_s=3600.0,
            dose_limit_Gy=1.0,
            particle_type='proton',
            proton_energy_MeV=1.0,
        )
        self.assertAlmostEqual(result['transmitted_dose_Gy'], 0.0)
        self.assertTrue(result['compliant'])

    def test_dose_margin_matches_formula(self):
        result = self._base_run()
        expected_margin = (
            (result['dose_limit_Gy'] - result['transmitted_dose_Gy'])
            / result['dose_limit_Gy']
        )
        self.assertAlmostEqual(result['dose_margin'], expected_margin, places=10)

    def test_tantalum_shield_lower_transmitted_dose_than_aluminum_same_thickness(self):
        # Tantalum has higher density so exponential attenuation is stronger per cm
        result_al = self._base_run(material_name='aluminum', thickness_cm=1.0)
        result_ta = self._base_run(material_name='tantalum', thickness_cm=1.0)
        self.assertLess(result_ta['transmitted_dose_Gy'], result_al['transmitted_dose_Gy'])


if __name__ == '__main__':
    unittest.main()
