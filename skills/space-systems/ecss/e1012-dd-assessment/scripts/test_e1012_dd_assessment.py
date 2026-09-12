"""
test_e1012_dd_assessment.py

Stdlib unittest for e1012_dd_assessment_logic.py.
Run: python3 test_e1012_dd_assessment.py
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from e1012_dd_assessment_logic import (
    NIEL_10MEV_PROTON_SI,
    NIEL_1MEV_NEUTRON_SI,
    compute_tnid,
    compute_ddef,
    apply_rdm,
    check_ddef_compliance,
    assess_device_dd,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bin(species="proton", energy_mev=10.0, fluence_cm2=1e12, niel_mev_cm2_g=5.55e-4):
    return {
        "species": species,
        "energy_mev": energy_mev,
        "fluence_cm2": fluence_cm2,
        "niel_mev_cm2_g": niel_mev_cm2_g,
    }


# ---------------------------------------------------------------------------
# compute_tnid
# ---------------------------------------------------------------------------

class TestComputeTnid(unittest.TestCase):

    def test_single_bin_tnid_value(self):
        bins = [_bin(fluence_cm2=1e12, niel_mev_cm2_g=5.55e-4)]
        tnid, _ = compute_tnid(bins)
        self.assertAlmostEqual(tnid, 1e12 * 5.55e-4, places=10)

    def test_multiple_bins_sum(self):
        bins = [
            _bin(species="proton",   fluence_cm2=1e12, niel_mev_cm2_g=5.55e-4),
            _bin(species="electron", fluence_cm2=5e13, niel_mev_cm2_g=4.6e-6),
            _bin(species="neutron",  fluence_cm2=2e11, niel_mev_cm2_g=9.5e-3),
        ]
        tnid, _ = compute_tnid(bins)
        expected = 1e12 * 5.55e-4 + 5e13 * 4.6e-6 + 2e11 * 9.5e-3
        self.assertAlmostEqual(tnid, expected, places=6)

    def test_zero_fluence_bin_contributes_nothing(self):
        bins = [
            _bin(fluence_cm2=0.0, niel_mev_cm2_g=5.55e-4),
            _bin(fluence_cm2=1e12, niel_mev_cm2_g=1e-3),
        ]
        tnid, _ = compute_tnid(bins)
        self.assertAlmostEqual(tnid, 1e12 * 1e-3, places=10)

    def test_per_bin_contributions_recorded(self):
        bins = [
            _bin(species="proton",  fluence_cm2=2e12, niel_mev_cm2_g=5e-4),
            _bin(species="neutron", fluence_cm2=1e11, niel_mev_cm2_g=9e-3),
        ]
        _, per_bin = compute_tnid(bins)
        self.assertAlmostEqual(per_bin[0]["tnid_contribution_mev_g"], 2e12 * 5e-4)
        self.assertAlmostEqual(per_bin[1]["tnid_contribution_mev_g"], 1e11 * 9e-3)

    def test_empty_bins_raises(self):
        with self.assertRaises(ValueError):
            compute_tnid([])

    def test_negative_fluence_raises(self):
        with self.assertRaises(ValueError):
            compute_tnid([_bin(fluence_cm2=-1.0)])

    def test_zero_niel_raises(self):
        with self.assertRaises(ValueError):
            compute_tnid([_bin(niel_mev_cm2_g=0.0)])

    def test_negative_niel_raises(self):
        with self.assertRaises(ValueError):
            compute_tnid([_bin(niel_mev_cm2_g=-1e-4)])

    def test_unrecognised_species_raises(self):
        with self.assertRaises(ValueError):
            compute_tnid([_bin(species="cosmic_ray")])

    def test_missing_fluence_key_raises(self):
        bad_bin = {"species": "proton", "energy_mev": 10.0, "niel_mev_cm2_g": 5e-4}
        with self.assertRaises(KeyError):
            compute_tnid([bad_bin])

    def test_heavy_ion_species_accepted(self):
        bins = [_bin(species="heavy_ion", fluence_cm2=1e9, niel_mev_cm2_g=1e-2)]
        tnid, _ = compute_tnid(bins)
        self.assertAlmostEqual(tnid, 1e9 * 1e-2)


# ---------------------------------------------------------------------------
# compute_ddef
# ---------------------------------------------------------------------------

class TestComputeDdef(unittest.TestCase):

    def test_ddef_equals_tnid_over_reference_niel(self):
        tnid = 5.55e8   # MeV/g
        ddef = compute_ddef(tnid, NIEL_10MEV_PROTON_SI)
        self.assertAlmostEqual(ddef, tnid / NIEL_10MEV_PROTON_SI, places=6)

    def test_ddef_zero_tnid_gives_zero(self):
        self.assertEqual(compute_ddef(0.0, NIEL_10MEV_PROTON_SI), 0.0)

    def test_ddef_alternate_reference(self):
        tnid = 9.5e9   # MeV/g
        ddef = compute_ddef(tnid, NIEL_1MEV_NEUTRON_SI)
        self.assertAlmostEqual(ddef, tnid / NIEL_1MEV_NEUTRON_SI, places=4)

    def test_zero_reference_niel_raises(self):
        with self.assertRaises(ValueError):
            compute_ddef(1.0, 0.0)

    def test_negative_reference_niel_raises(self):
        with self.assertRaises(ValueError):
            compute_ddef(1.0, -1e-4)

    def test_negative_tnid_raises(self):
        with self.assertRaises(ValueError):
            compute_ddef(-1.0, NIEL_10MEV_PROTON_SI)


# ---------------------------------------------------------------------------
# apply_rdm
# ---------------------------------------------------------------------------

class TestApplyRdm(unittest.TestCase):

    def test_rdm_scales_ddef(self):
        self.assertAlmostEqual(apply_rdm(1e14, 2.0), 2e14)

    def test_rdm_one_leaves_ddef_unchanged(self):
        self.assertAlmostEqual(apply_rdm(3.5e13, 1.0), 3.5e13)

    def test_zero_ddef_with_rdm(self):
        self.assertEqual(apply_rdm(0.0, 2.0), 0.0)

    def test_rdm_below_one_raises(self):
        with self.assertRaises(ValueError):
            apply_rdm(1e12, 0.5)

    def test_rdm_zero_raises(self):
        with self.assertRaises(ValueError):
            apply_rdm(1e12, 0.0)


# ---------------------------------------------------------------------------
# check_ddef_compliance
# ---------------------------------------------------------------------------

class TestCheckDdefCompliance(unittest.TestCase):

    def test_pass_when_assessed_below_limit(self):
        result = check_ddef_compliance(1e13, 2e13)
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["compliant"])

    def test_fail_when_assessed_exceeds_limit(self):
        result = check_ddef_compliance(3e13, 2e13)
        self.assertEqual(result["status"], "fail")
        self.assertFalse(result["compliant"])

    def test_pass_at_exact_limit(self):
        result = check_ddef_compliance(2e13, 2e13)
        self.assertEqual(result["status"], "pass")

    def test_margin_ratio_computed_correctly(self):
        result = check_ddef_compliance(1e13, 4e13)
        self.assertAlmostEqual(result["margin_ratio"], 4.0)

    def test_zero_assessed_gives_inf_margin(self):
        result = check_ddef_compliance(0.0, 1e12)
        self.assertEqual(result["margin_ratio"], float("inf"))
        self.assertTrue(result["compliant"])

    def test_zero_limit_raises(self):
        with self.assertRaises(ValueError):
            check_ddef_compliance(1e12, 0.0)

    def test_result_keys_present(self):
        result = check_ddef_compliance(1e12, 1e13)
        for key in ("status", "ddef_assessed_cm2", "ddef_limit_cm2",
                    "margin_ratio", "compliant"):
            self.assertIn(key, result)


# ---------------------------------------------------------------------------
# assess_device_dd (integration)
# ---------------------------------------------------------------------------

class TestAssessDeviceDd(unittest.TestCase):

    def _make_bins(self):
        return [
            _bin(species="proton",   fluence_cm2=1e12, niel_mev_cm2_g=5.55e-4),
            _bin(species="electron", fluence_cm2=5e13, niel_mev_cm2_g=4.6e-6),
        ]

    def test_passing_assessment(self):
        result = assess_device_dd(
            device_name="sensor_A",
            particle_bins=self._make_bins(),
            reference_niel_mev_cm2_g=NIEL_10MEV_PROTON_SI,
            ddef_limit_cm2=1e16,
            rdm_factor=2.0,
        )
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["compliant"])

    def test_failing_assessment_tight_limit(self):
        result = assess_device_dd(
            device_name="sensor_B",
            particle_bins=self._make_bins(),
            reference_niel_mev_cm2_g=NIEL_10MEV_PROTON_SI,
            ddef_limit_cm2=1.0,   # unrealistically tight
            rdm_factor=2.0,
        )
        self.assertEqual(result["status"], "fail")
        self.assertFalse(result["compliant"])

    def test_result_contains_all_expected_keys(self):
        result = assess_device_dd(
            device_name="solar_cell",
            particle_bins=self._make_bins(),
            reference_niel_mev_cm2_g=NIEL_10MEV_PROTON_SI,
            ddef_limit_cm2=1e15,
            rdm_factor=2.0,
        )
        for key in ("device_name", "total_tnid_mev_g", "ddef_cm2",
                    "ddef_assessed_cm2", "ddef_limit_cm2", "rdm_factor",
                    "reference_niel_mev_cm2_g", "status", "margin_ratio",
                    "compliant", "per_bin"):
            self.assertIn(key, result)

    def test_ddef_assessed_is_ddef_times_rdm(self):
        result = assess_device_dd(
            device_name="detector",
            particle_bins=[_bin(fluence_cm2=1e12, niel_mev_cm2_g=5.55e-4)],
            reference_niel_mev_cm2_g=NIEL_10MEV_PROTON_SI,
            ddef_limit_cm2=1e15,
            rdm_factor=3.0,
        )
        self.assertAlmostEqual(
            result["ddef_assessed_cm2"],
            result["ddef_cm2"] * 3.0,
            places=6,
        )

    def test_empty_device_name_raises(self):
        with self.assertRaises(ValueError):
            assess_device_dd(
                device_name="",
                particle_bins=self._make_bins(),
                reference_niel_mev_cm2_g=NIEL_10MEV_PROTON_SI,
                ddef_limit_cm2=1e15,
                rdm_factor=2.0,
            )


if __name__ == "__main__":
    unittest.main()
