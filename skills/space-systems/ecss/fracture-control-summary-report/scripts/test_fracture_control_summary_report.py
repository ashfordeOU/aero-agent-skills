import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from fracture_control_summary_report_logic import (
    FlightItemRecord,
    assess_item,
    compile_summary,
    MIN_LIFE_RATIO_INSPECTABLE,
    MIN_LIFE_RATIO_SAFE_LIFE,
)


def _compliant_inspectable(**overrides) -> FlightItemRecord:
    """Return a fully compliant fracture-critical inspectable item."""
    defaults = dict(
        item_id="IT-001",
        name="Main strut lug",
        fracture_critical=True,
        basis_documented=True,
        analysis_complete=True,
        life_ratio=2.5,
        safety_factor_met=True,
        inspection_category="inspectable",
        inspection_method="NDE",
        inspection_interval_met=True,
        test_verified=True,
    )
    defaults.update(overrides)
    return FlightItemRecord(**defaults)


def _compliant_safe_life(**overrides) -> FlightItemRecord:
    """Return a fully compliant fracture-critical safe-life item."""
    defaults = dict(
        item_id="IT-002",
        name="Pressure vessel boss",
        fracture_critical=True,
        basis_documented=True,
        analysis_complete=True,
        life_ratio=4.5,
        safety_factor_met=True,
        inspection_category="safe_life",
        inspection_method="",
        inspection_interval_met=False,
        test_verified=True,
    )
    defaults.update(overrides)
    return FlightItemRecord(**defaults)


def _compliant_non_fc(**overrides) -> FlightItemRecord:
    """Return a compliant non-fracture-critical item."""
    defaults = dict(
        item_id="IT-003",
        name="Bracket gusset",
        fracture_critical=False,
        basis_documented=True,
    )
    defaults.update(overrides)
    return FlightItemRecord(**defaults)


class TestNonFractureCriticalItems(unittest.TestCase):

    def test_non_fc_with_basis_is_compliant(self):
        item = _compliant_non_fc()
        status = assess_item(item)
        self.assertTrue(status.compliant)
        self.assertEqual(status.findings, [])

    def test_non_fc_without_basis_is_non_compliant(self):
        item = _compliant_non_fc(basis_documented=False)
        status = assess_item(item)
        self.assertFalse(status.compliant)
        self.assertTrue(any("basis" in f for f in status.findings))

    def test_non_fc_item_does_not_check_analysis(self):
        # analysis_complete=False should not add a finding for non-FC items
        item = _compliant_non_fc(basis_documented=True)
        status = assess_item(item)
        self.assertTrue(status.compliant)
        self.assertFalse(any("analysis" in f for f in status.findings))


class TestFractureCriticalAnalysis(unittest.TestCase):

    def test_incomplete_analysis_adds_finding(self):
        item = _compliant_inspectable(analysis_complete=False)
        status = assess_item(item)
        self.assertFalse(status.compliant)
        self.assertTrue(any("analysis" in f for f in status.findings))

    def test_incomplete_analysis_skips_life_ratio_check(self):
        # life_ratio below threshold should NOT add a second finding when
        # analysis is already flagged as incomplete
        item = _compliant_inspectable(analysis_complete=False, life_ratio=0.1)
        status = assess_item(item)
        finding_texts = " ".join(status.findings)
        self.assertNotIn("life ratio", finding_texts)


class TestLifeRatioInspectable(unittest.TestCase):

    def test_life_ratio_at_minimum_passes(self):
        item = _compliant_inspectable(life_ratio=MIN_LIFE_RATIO_INSPECTABLE)
        status = assess_item(item)
        self.assertTrue(status.compliant)

    def test_life_ratio_below_minimum_fails(self):
        item = _compliant_inspectable(life_ratio=0.99)
        status = assess_item(item)
        self.assertFalse(status.compliant)
        self.assertTrue(any("life ratio" in f for f in status.findings))

    def test_life_ratio_well_above_minimum_passes(self):
        item = _compliant_inspectable(life_ratio=10.0)
        status = assess_item(item)
        self.assertTrue(status.compliant)


class TestLifeRatioSafeLife(unittest.TestCase):

    def test_safe_life_ratio_at_minimum_passes(self):
        item = _compliant_safe_life(life_ratio=MIN_LIFE_RATIO_SAFE_LIFE)
        status = assess_item(item)
        self.assertTrue(status.compliant)

    def test_safe_life_ratio_below_minimum_fails(self):
        item = _compliant_safe_life(life_ratio=3.99)
        status = assess_item(item)
        self.assertFalse(status.compliant)
        self.assertTrue(any("safe-life ratio" in f for f in status.findings))

    def test_inspectable_threshold_not_applied_to_safe_life(self):
        # life_ratio=1.5 passes inspectable threshold but fails safe-life threshold
        item = _compliant_safe_life(life_ratio=1.5)
        status = assess_item(item)
        self.assertFalse(status.compliant)
        self.assertTrue(any("safe-life ratio" in f for f in status.findings))


class TestSafetyFactor(unittest.TestCase):

    def test_safety_factor_not_met_adds_finding(self):
        item = _compliant_inspectable(safety_factor_met=False)
        status = assess_item(item)
        self.assertFalse(status.compliant)
        self.assertTrue(any("safety factor" in f for f in status.findings))


class TestInspectionCategory(unittest.TestCase):

    def test_missing_inspection_category_adds_finding(self):
        item = _compliant_inspectable(inspection_category="")
        status = assess_item(item)
        self.assertFalse(status.compliant)
        self.assertTrue(any("inspection category" in f for f in status.findings))

    def test_missing_inspection_method_adds_finding(self):
        item = _compliant_inspectable(inspection_method="")
        status = assess_item(item)
        self.assertFalse(status.compliant)
        self.assertTrue(any("inspection method" in f for f in status.findings))

    def test_inspection_interval_not_met_adds_finding(self):
        item = _compliant_inspectable(inspection_interval_met=False)
        status = assess_item(item)
        self.assertFalse(status.compliant)
        self.assertTrue(any("inspection interval" in f for f in status.findings))

    def test_safe_life_item_does_not_check_inspection_interval(self):
        # safe_life items have no inspection interval requirement
        item = _compliant_safe_life(inspection_interval_met=False)
        status = assess_item(item)
        self.assertTrue(status.compliant)


class TestTestVerification(unittest.TestCase):

    def test_test_not_verified_adds_finding(self):
        item = _compliant_inspectable(test_verified=False)
        status = assess_item(item)
        self.assertFalse(status.compliant)
        self.assertTrue(any("test verification" in f for f in status.findings))


class TestInputValidation(unittest.TestCase):

    def test_empty_item_id_raises(self):
        with self.assertRaises(ValueError):
            assess_item(_compliant_inspectable(item_id=""))

    def test_blank_name_raises(self):
        with self.assertRaises(ValueError):
            assess_item(_compliant_inspectable(name="   "))

    def test_invalid_inspection_category_raises(self):
        with self.assertRaises(ValueError):
            assess_item(_compliant_inspectable(inspection_category="periodic"))


class TestCompileSummary(unittest.TestCase):

    def test_empty_list_produces_empty_report(self):
        report = compile_summary([])
        self.assertEqual(report.total_items, 0)
        self.assertEqual(report.fracture_critical_count, 0)
        self.assertEqual(report.non_fracture_critical_count, 0)
        self.assertTrue(report.overall_compliant)

    def test_all_compliant_items_overall_compliant(self):
        records = [
            _compliant_inspectable(item_id="A"),
            _compliant_safe_life(item_id="B"),
            _compliant_non_fc(item_id="C"),
        ]
        report = compile_summary(records)
        self.assertTrue(report.overall_compliant)
        self.assertEqual(report.compliant_count, 3)
        self.assertEqual(report.non_compliant_count, 0)

    def test_one_failing_item_makes_overall_non_compliant(self):
        records = [
            _compliant_inspectable(item_id="A"),
            _compliant_inspectable(item_id="B", life_ratio=0.5),
        ]
        report = compile_summary(records)
        self.assertFalse(report.overall_compliant)
        self.assertEqual(report.non_compliant_count, 1)

    def test_counts_fracture_critical_vs_non_fc(self):
        records = [
            _compliant_inspectable(item_id="FC-1"),
            _compliant_safe_life(item_id="FC-2"),
            _compliant_non_fc(item_id="NFC-1"),
            _compliant_non_fc(item_id="NFC-2"),
        ]
        report = compile_summary(records)
        self.assertEqual(report.total_items, 4)
        self.assertEqual(report.fracture_critical_count, 2)
        self.assertEqual(report.non_fracture_critical_count, 2)

    def test_item_statuses_length_matches_input(self):
        records = [_compliant_inspectable(item_id=f"IT-{i:03d}") for i in range(5)]
        report = compile_summary(records)
        self.assertEqual(len(report.item_statuses), 5)

    def test_multiple_findings_per_item_all_recorded(self):
        item = _compliant_inspectable(
            life_ratio=0.5,
            safety_factor_met=False,
            test_verified=False,
        )
        status = assess_item(item)
        self.assertGreaterEqual(len(status.findings), 3)


if __name__ == "__main__":
    unittest.main()
