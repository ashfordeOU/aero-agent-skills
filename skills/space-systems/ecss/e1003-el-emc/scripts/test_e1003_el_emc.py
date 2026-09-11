"""
Gate-3 contract tests for e1003_el_emc_logic.
ECSS-E-ST-10-03C §6.5.5 element EMC logic.
Stdlib unittest only. Offline, deterministic.
Run: python3 test_e1003_el_emc.py
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1003_el_emc_logic import (
    AutoCompatPair,
    EMCAssessmentResult,
    MagneticMeasurement,
    Outcome,
    PIMCarrierPair,
    TestFinding,
    TestMode,
    TestType,
    _odd_order_pim_products,
    assess_element_emc,
    check_auto_compatibility,
    check_magnetic_field,
    check_pim,
    select_test_modes,
)


class TestAutoCompatibility(unittest.TestCase):

    def test_emitter_outside_band_is_not_applicable(self):
        pair = AutoCompatPair(
            emitter_freq_hz=1.0e9,
            rx_band_low_hz=2.0e9,
            rx_band_high_hz=2.5e9,
            margin_db=20.0,
            required_margin_db=6.0,
        )
        finding = check_auto_compatibility(pair, TestMode.STANDALONE)
        self.assertEqual(finding.outcome, Outcome.NOT_APPLICABLE)

    def test_emitter_in_band_sufficient_margin_passes(self):
        pair = AutoCompatPair(
            emitter_freq_hz=2.2e9,
            rx_band_low_hz=2.0e9,
            rx_band_high_hz=2.5e9,
            margin_db=15.0,
            required_margin_db=6.0,
        )
        finding = check_auto_compatibility(pair, TestMode.STANDALONE)
        self.assertEqual(finding.outcome, Outcome.PASS)

    def test_emitter_in_band_insufficient_margin_fails(self):
        pair = AutoCompatPair(
            emitter_freq_hz=2.2e9,
            rx_band_low_hz=2.0e9,
            rx_band_high_hz=2.5e9,
            margin_db=3.0,
            required_margin_db=6.0,
        )
        finding = check_auto_compatibility(pair, TestMode.STANDALONE)
        self.assertEqual(finding.outcome, Outcome.FAIL)

    def test_emitter_at_band_edge_low_is_in_band(self):
        pair = AutoCompatPair(
            emitter_freq_hz=2.0e9,
            rx_band_low_hz=2.0e9,
            rx_band_high_hz=2.5e9,
            margin_db=10.0,
            required_margin_db=6.0,
        )
        finding = check_auto_compatibility(pair, TestMode.STANDALONE)
        self.assertEqual(finding.outcome, Outcome.PASS)

    def test_emitter_at_band_edge_high_is_in_band(self):
        pair = AutoCompatPair(
            emitter_freq_hz=2.5e9,
            rx_band_low_hz=2.0e9,
            rx_band_high_hz=2.5e9,
            margin_db=10.0,
            required_margin_db=6.0,
        )
        finding = check_auto_compatibility(pair, TestMode.STANDALONE)
        self.assertEqual(finding.outcome, Outcome.PASS)

    def test_bad_rx_band_raises(self):
        with self.assertRaises(ValueError):
            AutoCompatPair(
                emitter_freq_hz=1.0e9,
                rx_band_low_hz=3.0e9,
                rx_band_high_hz=2.0e9,  # inverted
                margin_db=10.0,
                required_margin_db=6.0,
            )

    def test_non_positive_emitter_freq_raises(self):
        with self.assertRaises(ValueError):
            AutoCompatPair(
                emitter_freq_hz=0.0,
                rx_band_low_hz=2.0e9,
                rx_band_high_hz=2.5e9,
                margin_db=10.0,
                required_margin_db=6.0,
            )

    def test_embedded_mode_recorded_in_finding(self):
        pair = AutoCompatPair(
            emitter_freq_hz=2.2e9,
            rx_band_low_hz=2.0e9,
            rx_band_high_hz=2.5e9,
            margin_db=3.0,
            required_margin_db=6.0,
        )
        finding = check_auto_compatibility(pair, TestMode.EMBEDDED)
        self.assertEqual(finding.test_mode, TestMode.EMBEDDED)
        self.assertEqual(finding.outcome, Outcome.FAIL)


class TestPIM(unittest.TestCase):

    def test_no_pim_products_in_band_passes(self):
        # Carriers at 1 GHz and 1.1 GHz produce order-3..9 products from
        # 0.6 GHz up to 7.8 GHz (8*f2-f1). A receive band above 7.8 GHz
        # therefore holds no product.
        pair = PIMCarrierPair(
            f1_hz=1.0e9,
            f2_hz=1.1e9,
            rx_low_hz=8.0e9,
            rx_high_hz=9.0e9,
        )
        finding = check_pim(pair)
        self.assertEqual(finding.outcome, Outcome.PASS)

    def test_high_order_product_in_band_fails(self):
        # 5-6 GHz is NOT clear for these carriers: 6*f2-f1 = 5.6 GHz
        # (order 7) and 7*f2-2*f1 = 5.7 GHz (order 9) sit inside it.
        pair = PIMCarrierPair(
            f1_hz=1.0e9,
            f2_hz=1.1e9,
            rx_low_hz=5.6e9,
            rx_high_hz=5.8e9,
        )
        finding = check_pim(pair)
        self.assertEqual(finding.outcome, Outcome.FAIL)

    def test_third_order_product_in_band_fails(self):
        # f1=900 MHz, f2=1000 MHz → 3rd-order product 2*900-1000 = 800 MHz
        pair = PIMCarrierPair(
            f1_hz=900e6,
            f2_hz=1000e6,
            rx_low_hz=790e6,
            rx_high_hz=810e6,
        )
        finding = check_pim(pair)
        self.assertEqual(finding.outcome, Outcome.FAIL)
        self.assertIn("800", finding.detail.replace("8.0000e+08", "800e6"))

    def test_third_order_product_detail_mentions_rx_band(self):
        pair = PIMCarrierPair(
            f1_hz=900e6,
            f2_hz=1000e6,
            rx_low_hz=790e6,
            rx_high_hz=810e6,
        )
        finding = check_pim(pair)
        self.assertIn("rx band", finding.detail)

    def test_pim_products_are_computed_for_both_orderings(self):
        # 2*f2 - f1 = 2*1000 - 900 = 1100 MHz
        pair = PIMCarrierPair(
            f1_hz=900e6,
            f2_hz=1000e6,
            rx_low_hz=1090e6,
            rx_high_hz=1110e6,
        )
        finding = check_pim(pair)
        self.assertEqual(finding.outcome, Outcome.FAIL)

    def test_bad_carrier_freq_raises(self):
        with self.assertRaises(ValueError):
            PIMCarrierPair(
                f1_hz=-100e6,
                f2_hz=1000e6,
                rx_low_hz=790e6,
                rx_high_hz=810e6,
            )

    def test_inverted_rx_band_raises(self):
        with self.assertRaises(ValueError):
            PIMCarrierPair(
                f1_hz=900e6,
                f2_hz=1000e6,
                rx_low_hz=900e6,
                rx_high_hz=800e6,
            )

    def test_odd_order_products_only(self):
        products = _odd_order_pim_products(900e6, 1000e6, max_order=7)
        orders = [m + n for m, n, _ in products]
        for order in orders:
            self.assertEqual(order % 2, 1, f"even order {order} found")

    def test_max_order_parameter_limits_products(self):
        products_3 = _odd_order_pim_products(900e6, 1000e6, max_order=3)
        products_9 = _odd_order_pim_products(900e6, 1000e6, max_order=9)
        self.assertLess(len(products_3), len(products_9))


class TestMagneticField(unittest.TestCase):

    def test_within_budget_passes(self):
        meas = MagneticMeasurement(measured_am2=0.05, budget_am2=0.1)
        finding = check_magnetic_field(meas, TestMode.STANDALONE)
        self.assertEqual(finding.outcome, Outcome.PASS)

    def test_exceeds_budget_fails(self):
        meas = MagneticMeasurement(measured_am2=0.15, budget_am2=0.1)
        finding = check_magnetic_field(meas, TestMode.STANDALONE)
        self.assertEqual(finding.outcome, Outcome.FAIL)

    def test_exactly_at_budget_passes(self):
        meas = MagneticMeasurement(measured_am2=0.1, budget_am2=0.1)
        finding = check_magnetic_field(meas, TestMode.STANDALONE)
        self.assertEqual(finding.outcome, Outcome.PASS)

    def test_non_positive_budget_raises(self):
        with self.assertRaises(ValueError):
            MagneticMeasurement(measured_am2=0.05, budget_am2=0.0)

    def test_negative_measured_raises(self):
        with self.assertRaises(ValueError):
            MagneticMeasurement(measured_am2=-0.01, budget_am2=0.1)


class TestSelectTestModes(unittest.TestCase):

    def test_rf_element_standalone_includes_pim(self):
        modes = select_test_modes(element_has_rf_paths=True, embedded_available=False)
        self.assertIn(TestType.PIM, modes)
        self.assertEqual(modes[TestType.PIM], TestMode.STANDALONE)

    def test_non_rf_element_excludes_pim(self):
        modes = select_test_modes(element_has_rf_paths=False, embedded_available=False)
        self.assertNotIn(TestType.PIM, modes)

    def test_embedded_available_adds_susceptibility(self):
        modes = select_test_modes(element_has_rf_paths=True, embedded_available=True)
        self.assertIn(TestType.CONDUCTED_SUSCEPTIBILITY, modes)
        self.assertIn(TestType.RADIATED_SUSCEPTIBILITY, modes)
        self.assertEqual(modes[TestType.CONDUCTED_SUSCEPTIBILITY], TestMode.EMBEDDED)

    def test_no_embedded_omits_susceptibility(self):
        modes = select_test_modes(element_has_rf_paths=True, embedded_available=False)
        self.assertNotIn(TestType.CONDUCTED_SUSCEPTIBILITY, modes)
        self.assertNotIn(TestType.RADIATED_SUSCEPTIBILITY, modes)

    def test_standalone_mandatory_types_always_present_rf(self):
        modes = select_test_modes(element_has_rf_paths=True, embedded_available=False)
        for tt in [
            TestType.AUTO_COMPATIBILITY,
            TestType.MAGNETIC_FIELD,
            TestType.CONDUCTED_EMISSION,
            TestType.RADIATED_EMISSION,
        ]:
            self.assertIn(tt, modes)


class TestAssessElementEMC(unittest.TestCase):

    def test_empty_element_id_raises(self):
        with self.assertRaises(ValueError):
            assess_element_emc("", TestMode.STANDALONE)

    def test_whitespace_element_id_raises(self):
        with self.assertRaises(ValueError):
            assess_element_emc("   ", TestMode.STANDALONE)

    def test_no_inputs_returns_data_missing(self):
        result = assess_element_emc("EL-001", TestMode.STANDALONE)
        self.assertFalse(result.compliant)
        self.assertTrue(any(f.outcome == Outcome.DATA_MISSING for f in result.findings))

    def test_all_pass_means_compliant(self):
        compat = AutoCompatPair(
            emitter_freq_hz=1.0e9,
            rx_band_low_hz=2.0e9,
            rx_band_high_hz=2.5e9,
            margin_db=20.0,
            required_margin_db=6.0,
        )
        mag = MagneticMeasurement(measured_am2=0.01, budget_am2=0.1)
        result = assess_element_emc(
            "EL-001",
            TestMode.STANDALONE,
            auto_compat_pairs=[compat],
            magnetic_meas=mag,
        )
        self.assertTrue(result.compliant)
        self.assertEqual(len(result.open_findings), 0)

    def test_one_fail_means_not_compliant(self):
        compat = AutoCompatPair(
            emitter_freq_hz=2.2e9,
            rx_band_low_hz=2.0e9,
            rx_band_high_hz=2.5e9,
            margin_db=2.0,
            required_margin_db=6.0,
        )
        result = assess_element_emc(
            "EL-002",
            TestMode.STANDALONE,
            auto_compat_pairs=[compat],
        )
        self.assertFalse(result.compliant)
        self.assertEqual(len(result.open_findings), 1)

    def test_element_id_preserved_in_result(self):
        result = assess_element_emc("EL-XYZ-99", TestMode.STANDALONE)
        self.assertEqual(result.element_id, "EL-XYZ-99")

    def test_pim_finding_included_in_aggregate(self):
        pim = PIMCarrierPair(
            f1_hz=900e6,
            f2_hz=1000e6,
            rx_low_hz=790e6,
            rx_high_hz=810e6,
        )
        result = assess_element_emc(
            "EL-003",
            TestMode.STANDALONE,
            pim_pairs=[pim],
        )
        types = [f.test_type for f in result.findings]
        self.assertIn(TestType.PIM, types)


if __name__ == "__main__":
    unittest.main()
