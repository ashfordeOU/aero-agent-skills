"""
test_in_service_surveillance.py

Offline unittest for in_service_surveillance_logic.py.
Run: python3 test_in_service_surveillance.py
stdlib only — no third-party dependencies.
"""

import sys
import os
import unittest

# Allow running from any working directory
sys.path.insert(0, os.path.dirname(__file__))

from in_service_surveillance_logic import (
    Criticality,
    InspectionType,
    MaintenanceDecision,
    DamageType,
    InspectionItem,
    DamageReport,
    HIGH_FATIGUE_THRESHOLD,
    INTERVAL_REDUCTION_FACTOR,
    EXTENDED_DAMAGE_MULTIPLIER,
    assign_inspection_interval,
    evaluate_damage,
    surveillance_compliance_check,
)


def _item(
    item_id="I1",
    criticality=Criticality.STANDARD,
    inspection_type=InspectionType.VISUAL,
    fatigue_fraction=0.3,
    base_interval_hours=1000.0,
):
    return InspectionItem(
        item_id=item_id,
        criticality=criticality,
        inspection_type=inspection_type,
        fatigue_fraction=fatigue_fraction,
        base_interval_hours=base_interval_hours,
    )


def _report(
    item_id="I1",
    damage_type=DamageType.CRACK,
    damage_size=1.0,
    allowable_limit=5.0,
    has_residual_strength_analysis=False,
    can_be_repaired=True,
):
    return DamageReport(
        item_id=item_id,
        damage_type=damage_type,
        damage_size=damage_size,
        allowable_limit=allowable_limit,
        has_residual_strength_analysis=has_residual_strength_analysis,
        can_be_repaired=can_be_repaired,
    )


class TestAssignInspectionInterval(unittest.TestCase):

    def test_standard_criticality_full_interval(self):
        item = _item(criticality=Criticality.STANDARD, base_interval_hours=1000.0, fatigue_fraction=0.2)
        schedule = assign_inspection_interval(item)
        self.assertAlmostEqual(schedule.interval_hours, 1000.0)
        self.assertFalse(schedule.reduced_interval)

    def test_significant_criticality_applies_factor(self):
        item = _item(criticality=Criticality.SIGNIFICANT, base_interval_hours=1000.0, fatigue_fraction=0.2)
        schedule = assign_inspection_interval(item)
        self.assertAlmostEqual(schedule.interval_hours, 750.0)
        self.assertFalse(schedule.reduced_interval)

    def test_fracture_critical_halves_interval(self):
        item = _item(criticality=Criticality.FRACTURE_CRITICAL, base_interval_hours=1000.0, fatigue_fraction=0.2)
        schedule = assign_inspection_interval(item)
        self.assertAlmostEqual(schedule.interval_hours, 500.0)
        self.assertFalse(schedule.reduced_interval)

    def test_high_fatigue_triggers_reduction(self):
        item = _item(criticality=Criticality.STANDARD, base_interval_hours=1000.0, fatigue_fraction=0.9)
        schedule = assign_inspection_interval(item)
        # standard factor = 1.0, then * 0.5 for high fatigue
        self.assertAlmostEqual(schedule.interval_hours, 500.0)
        self.assertTrue(schedule.reduced_interval)

    def test_fatigue_at_threshold_triggers_reduction(self):
        # fatigue_fraction > HIGH_FATIGUE_THRESHOLD triggers reduction; equal does not
        item_above = _item(fatigue_fraction=HIGH_FATIGUE_THRESHOLD + 0.01)
        item_at = _item(fatigue_fraction=HIGH_FATIGUE_THRESHOLD)
        self.assertTrue(assign_inspection_interval(item_above).reduced_interval)
        self.assertFalse(assign_inspection_interval(item_at).reduced_interval)

    def test_fracture_critical_with_high_fatigue_both_factors(self):
        item = _item(criticality=Criticality.FRACTURE_CRITICAL, base_interval_hours=2000.0, fatigue_fraction=0.95)
        schedule = assign_inspection_interval(item)
        # 2000 * 0.5 (fracture-critical) * 0.5 (high fatigue) = 500
        self.assertAlmostEqual(schedule.interval_hours, 500.0)
        self.assertTrue(schedule.reduced_interval)

    def test_schedule_carries_correct_inspection_type(self):
        item = _item(inspection_type=InspectionType.NDT)
        schedule = assign_inspection_interval(item)
        self.assertEqual(schedule.inspection_type, InspectionType.NDT)

    def test_invalid_fatigue_fraction_below_zero(self):
        with self.assertRaises(ValueError):
            assign_inspection_interval(_item(fatigue_fraction=-0.1))

    def test_invalid_fatigue_fraction_above_one(self):
        with self.assertRaises(ValueError):
            assign_inspection_interval(_item(fatigue_fraction=1.01))

    def test_invalid_base_interval_zero(self):
        with self.assertRaises(ValueError):
            assign_inspection_interval(_item(base_interval_hours=0.0))

    def test_invalid_base_interval_negative(self):
        with self.assertRaises(ValueError):
            assign_inspection_interval(_item(base_interval_hours=-500.0))


class TestEvaluateDamage(unittest.TestCase):

    def test_damage_within_allowable_accepted(self):
        report = _report(damage_size=3.0, allowable_limit=5.0)
        disposition = evaluate_damage(report)
        self.assertEqual(disposition.decision, MaintenanceDecision.ACCEPT)

    def test_damage_exactly_at_allowable_accepted(self):
        report = _report(damage_size=5.0, allowable_limit=5.0)
        disposition = evaluate_damage(report)
        self.assertEqual(disposition.decision, MaintenanceDecision.ACCEPT)

    def test_damage_above_allowable_with_analysis_accepted_continue_fly(self):
        report = _report(
            damage_size=7.0, allowable_limit=5.0, has_residual_strength_analysis=True
        )
        disposition = evaluate_damage(report)
        self.assertEqual(disposition.decision, MaintenanceDecision.ACCEPT_CONTINUE_FLY)

    def test_damage_above_allowable_without_analysis_flagged(self):
        report = _report(
            damage_size=7.0, allowable_limit=5.0, has_residual_strength_analysis=False
        )
        disposition = evaluate_damage(report)
        self.assertEqual(disposition.decision, MaintenanceDecision.FLAG)

    def test_damage_at_extended_limit_with_analysis_accepted_continue_fly(self):
        # exactly at 2 * allowable is still within extended region (<=)
        report = _report(
            damage_size=10.0, allowable_limit=5.0, has_residual_strength_analysis=True
        )
        disposition = evaluate_damage(report)
        self.assertEqual(disposition.decision, MaintenanceDecision.ACCEPT_CONTINUE_FLY)

    def test_damage_beyond_extended_limit_repaired(self):
        report = _report(
            damage_size=11.0, allowable_limit=5.0, can_be_repaired=True
        )
        disposition = evaluate_damage(report)
        self.assertEqual(disposition.decision, MaintenanceDecision.REPAIR)

    def test_damage_beyond_extended_limit_replaced_when_not_repairable(self):
        report = _report(
            damage_size=11.0, allowable_limit=5.0, can_be_repaired=False
        )
        disposition = evaluate_damage(report)
        self.assertEqual(disposition.decision, MaintenanceDecision.REPLACE)

    def test_zero_damage_accepted(self):
        report = _report(damage_size=0.0, allowable_limit=5.0)
        disposition = evaluate_damage(report)
        self.assertEqual(disposition.decision, MaintenanceDecision.ACCEPT)

    def test_invalid_negative_damage_raises(self):
        with self.assertRaises(ValueError):
            evaluate_damage(_report(damage_size=-1.0))

    def test_invalid_zero_allowable_raises(self):
        with self.assertRaises(ValueError):
            evaluate_damage(_report(allowable_limit=0.0))

    def test_invalid_negative_allowable_raises(self):
        with self.assertRaises(ValueError):
            evaluate_damage(_report(allowable_limit=-5.0))

    def test_disposition_carries_item_id(self):
        report = _report(item_id="STRINGER-07", damage_size=1.0, allowable_limit=5.0)
        disposition = evaluate_damage(report)
        self.assertEqual(disposition.item_id, "STRINGER-07")


class TestSurveillanceComplianceCheck(unittest.TestCase):

    def test_all_compliant_no_damage(self):
        items = [_item("A1"), _item("A2", criticality=Criticality.SIGNIFICANT)]
        result = surveillance_compliance_check(items, [])
        self.assertTrue(result.compliant)
        self.assertEqual(len(result.inspection_schedules), 2)
        self.assertEqual(result.damage_dispositions, [])

    def test_compliant_with_accepted_damage(self):
        items = [_item("B1")]
        reports = [_report("B1", damage_size=2.0, allowable_limit=10.0)]
        result = surveillance_compliance_check(items, reports)
        self.assertTrue(result.compliant)
        self.assertEqual(result.damage_dispositions[0].decision, MaintenanceDecision.ACCEPT)

    def test_non_compliant_with_flagged_damage(self):
        items = [_item("C1")]
        reports = [_report("C1", damage_size=7.0, allowable_limit=5.0, has_residual_strength_analysis=False)]
        result = surveillance_compliance_check(items, reports)
        self.assertFalse(result.compliant)
        self.assertEqual(result.damage_dispositions[0].decision, MaintenanceDecision.FLAG)

    def test_non_compliant_with_repair_required(self):
        items = [_item("D1")]
        reports = [_report("D1", damage_size=20.0, allowable_limit=5.0, can_be_repaired=True)]
        result = surveillance_compliance_check(items, reports)
        self.assertFalse(result.compliant)

    def test_non_compliant_with_replace_required(self):
        items = [_item("E1")]
        reports = [_report("E1", damage_size=20.0, allowable_limit=5.0, can_be_repaired=False)]
        result = surveillance_compliance_check(items, reports)
        self.assertFalse(result.compliant)
        self.assertEqual(result.damage_dispositions[0].decision, MaintenanceDecision.REPLACE)

    def test_unknown_item_in_damage_report_causes_non_compliant(self):
        items = [_item("F1")]
        reports = [_report("UNKNOWN_ITEM", damage_size=1.0, allowable_limit=5.0)]
        result = surveillance_compliance_check(items, reports)
        self.assertFalse(result.compliant)
        self.assertTrue(any("UNKNOWN_ITEM" in f for f in result.findings))

    def test_high_fatigue_finding_recorded(self):
        items = [_item("G1", fatigue_fraction=0.95)]
        result = surveillance_compliance_check(items, [])
        self.assertTrue(result.compliant)
        self.assertTrue(any("G1" in f and "reduced" in f for f in result.findings))

    def test_continue_fly_with_analysis_is_compliant(self):
        items = [_item("H1")]
        reports = [_report("H1", damage_size=8.0, allowable_limit=5.0, has_residual_strength_analysis=True)]
        result = surveillance_compliance_check(items, reports)
        self.assertTrue(result.compliant)
        self.assertEqual(result.damage_dispositions[0].decision, MaintenanceDecision.ACCEPT_CONTINUE_FLY)

    def test_multiple_items_mixed_damage(self):
        items = [_item("J1"), _item("J2"), _item("J3")]
        reports = [
            _report("J1", damage_size=1.0, allowable_limit=5.0),               # ACCEPT
            _report("J2", damage_size=8.0, allowable_limit=5.0, has_residual_strength_analysis=True),  # ACCEPT_CONTINUE_FLY
            _report("J3", damage_size=8.0, allowable_limit=5.0, has_residual_strength_analysis=False), # FLAG
        ]
        result = surveillance_compliance_check(items, reports)
        self.assertFalse(result.compliant)
        decisions = {d.item_id: d.decision for d in result.damage_dispositions}
        self.assertEqual(decisions["J1"], MaintenanceDecision.ACCEPT)
        self.assertEqual(decisions["J2"], MaintenanceDecision.ACCEPT_CONTINUE_FLY)
        self.assertEqual(decisions["J3"], MaintenanceDecision.FLAG)


if __name__ == "__main__":
    unittest.main()
