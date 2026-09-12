#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C §11.2 dosimetric quantities.

Exercises scripts/e1012_bio_quantities_logic.py (stdlib unittest, offline).
Contract: wR is looked up by radiation type from Table 11-1 and raises for
unknown types; neutron wR is energy-dependent per the five-step schedule;
wT is looked up by tissue name from Table 11-2 and raises for unknown
tissues; Q(L) follows the three-region piecewise function (1 below 10,
linear in the middle band, 300/sqrt above 100); equivalent dose is
absorbed dose times wR; effective dose sums wT times HT across tissues;
dose equivalent applies Q to absorbed dose; all functions raise for
invalid (negative or zero) inputs.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1012_bio_quantities_logic as bq  # noqa: E402


class RadiationWrLookupTest(unittest.TestCase):
    def test_photon_wr_is_one(self):
        self.assertEqual(bq.lookup_radiation_wr("photon"), 1)

    def test_electron_wr_is_one(self):
        self.assertEqual(bq.lookup_radiation_wr("electron"), 1)

    def test_proton_wr_is_five(self):
        self.assertEqual(bq.lookup_radiation_wr("proton"), 5)

    def test_alpha_wr_is_twenty(self):
        self.assertEqual(bq.lookup_radiation_wr("alpha"), 20)

    def test_heavy_ion_wr_is_twenty(self):
        self.assertEqual(bq.lookup_radiation_wr("heavy_ion"), 20)

    def test_neutron_raises_with_helpful_message(self):
        with self.assertRaises(ValueError) as ctx:
            bq.lookup_radiation_wr("neutron")
        self.assertIn("energy-dependent", str(ctx.exception))

    def test_unknown_radiation_type_raises(self):
        with self.assertRaises(ValueError):
            bq.lookup_radiation_wr("cosmic_muon")


class NeutronWrEnergyDependenceTest(unittest.TestCase):
    def test_thermal_neutron_wr_is_five(self):
        self.assertEqual(bq.lookup_neutron_wr(0.000025), 5)  # 25 eV thermal

    def test_low_energy_neutron_below_10kev_wr_is_five(self):
        self.assertEqual(bq.lookup_neutron_wr(0.005), 5)  # 5 keV

    def test_neutron_10kev_to_100kev_wr_is_ten(self):
        self.assertEqual(bq.lookup_neutron_wr(0.05), 10)  # 50 keV

    def test_neutron_peak_band_0p1_to_2mev_wr_is_twenty(self):
        self.assertEqual(bq.lookup_neutron_wr(1.0), 20)  # 1 MeV

    def test_neutron_2mev_to_20mev_wr_is_ten(self):
        self.assertEqual(bq.lookup_neutron_wr(10.0), 10)  # 10 MeV

    def test_neutron_above_20mev_wr_is_five(self):
        self.assertEqual(bq.lookup_neutron_wr(50.0), 5)  # 50 MeV

    def test_negative_neutron_energy_raises(self):
        with self.assertRaises(ValueError):
            bq.lookup_neutron_wr(-1.0)


class TissueWtLookupTest(unittest.TestCase):
    def test_gonads_wt_is_point_twenty(self):
        self.assertAlmostEqual(bq.lookup_tissue_wt("gonads"), 0.20)

    def test_lung_wt_is_point_twelve(self):
        self.assertAlmostEqual(bq.lookup_tissue_wt("lung"), 0.12)

    def test_thyroid_wt_is_point_zero_five(self):
        self.assertAlmostEqual(bq.lookup_tissue_wt("thyroid"), 0.05)

    def test_skin_wt_is_point_zero_one(self):
        self.assertAlmostEqual(bq.lookup_tissue_wt("skin"), 0.01)

    def test_remainder_wt_is_point_zero_five(self):
        self.assertAlmostEqual(bq.lookup_tissue_wt("remainder"), 0.05)

    def test_unknown_tissue_raises(self):
        with self.assertRaises(ValueError):
            bq.lookup_tissue_wt("spleen")

    def test_table_wt_factors_sum_to_one(self):
        total = sum(bq.TISSUE_WT.values())
        self.assertAlmostEqual(total, 1.00, places=10)


class QualityFactorTest(unittest.TestCase):
    def test_let_below_10_q_is_one(self):
        self.assertAlmostEqual(bq.quality_factor_from_let(5.0), 1.0)

    def test_let_exactly_10_q_is_one(self):
        self.assertAlmostEqual(bq.quality_factor_from_let(10.0), 1.0)

    def test_let_in_linear_band_50(self):
        expected = 0.32 * 50.0 - 2.2  # 13.8
        self.assertAlmostEqual(bq.quality_factor_from_let(50.0), expected)

    def test_let_in_linear_band_100(self):
        expected = 0.32 * 100.0 - 2.2  # 29.8
        self.assertAlmostEqual(bq.quality_factor_from_let(100.0), expected)

    def test_let_above_100_uses_inverse_sqrt(self):
        expected = 300.0 / (400.0 ** 0.5)  # 300/20 = 15
        self.assertAlmostEqual(bq.quality_factor_from_let(400.0), expected)

    def test_zero_let_raises(self):
        with self.assertRaises(ValueError):
            bq.quality_factor_from_let(0.0)

    def test_negative_let_raises(self):
        with self.assertRaises(ValueError):
            bq.quality_factor_from_let(-5.0)


class EquivalentDoseTest(unittest.TestCase):
    def test_photon_dose_wr_one(self):
        self.assertAlmostEqual(bq.equivalent_dose_sv(0.5, 1), 0.5)

    def test_proton_dose_wr_five(self):
        self.assertAlmostEqual(bq.equivalent_dose_sv(0.1, 5), 0.5)

    def test_alpha_dose_wr_twenty(self):
        self.assertAlmostEqual(bq.equivalent_dose_sv(0.05, 20), 1.0)

    def test_zero_absorbed_dose(self):
        self.assertAlmostEqual(bq.equivalent_dose_sv(0.0, 20), 0.0)

    def test_negative_absorbed_dose_raises(self):
        with self.assertRaises(ValueError):
            bq.equivalent_dose_sv(-0.1, 1)

    def test_negative_wr_raises(self):
        with self.assertRaises(ValueError):
            bq.equivalent_dose_sv(1.0, -1)


class EquivalentDoseTissueSumTest(unittest.TestCase):
    def test_single_component(self):
        components = [{"absorbed_dose_gy": 0.1, "wr": 5}]
        self.assertAlmostEqual(bq.equivalent_dose_tissue_sv(components), 0.5)

    def test_multiple_components_summed(self):
        components = [
            {"absorbed_dose_gy": 0.1, "wr": 1},   # 0.1 Sv
            {"absorbed_dose_gy": 0.05, "wr": 20},  # 1.0 Sv
        ]
        self.assertAlmostEqual(bq.equivalent_dose_tissue_sv(components), 1.1)

    def test_empty_component_list_gives_zero(self):
        self.assertAlmostEqual(bq.equivalent_dose_tissue_sv([]), 0.0)


class EffectiveDoseTest(unittest.TestCase):
    def test_single_tissue_effective_dose(self):
        # gonads wT = 0.20
        e = bq.effective_dose_sv({"gonads": 1.0})
        self.assertAlmostEqual(e, 0.20)

    def test_two_tissues_effective_dose(self):
        # lung wT=0.12, thyroid wT=0.05 → 0.12*2 + 0.05*1 = 0.29
        e = bq.effective_dose_sv({"lung": 2.0, "thyroid": 1.0})
        self.assertAlmostEqual(e, 0.29)

    def test_unknown_tissue_raises(self):
        with self.assertRaises(ValueError):
            bq.effective_dose_sv({"spleen": 0.5})

    def test_zero_equivalent_doses_give_zero_effective_dose(self):
        e = bq.effective_dose_sv({"lung": 0.0, "stomach": 0.0})
        self.assertAlmostEqual(e, 0.0)


class DoseEquivalentTest(unittest.TestCase):
    def test_low_let_q_one(self):
        # Q=1 for LET=5
        self.assertAlmostEqual(bq.dose_equivalent_sv(2.0, 5.0), 2.0)

    def test_high_let_q_scales_dose(self):
        # LET=50 → Q = 0.32*50 - 2.2 = 13.8; D=0.1 → H=1.38
        self.assertAlmostEqual(bq.dose_equivalent_sv(0.1, 50.0), 1.38)

    def test_negative_absorbed_dose_raises(self):
        with self.assertRaises(ValueError):
            bq.dose_equivalent_sv(-1.0, 10.0)

    def test_zero_let_raises(self):
        with self.assertRaises(ValueError):
            bq.dose_equivalent_sv(1.0, 0.0)

    def test_zero_absorbed_dose_gives_zero(self):
        self.assertAlmostEqual(bq.dose_equivalent_sv(0.0, 5.0), 0.0)


if __name__ == "__main__":
    unittest.main()
