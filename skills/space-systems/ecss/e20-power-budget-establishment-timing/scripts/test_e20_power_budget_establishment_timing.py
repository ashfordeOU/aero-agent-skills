#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 5.2.1 power budget
establishment and phase review.

Exercises scripts/e20_power_budget_establishment_timing_logic.py
(stdlib unittest, offline). Contract: docs/harness-contract.md gate 3 -
an equipment line carries the margin fraction of its maturity category
and an uncategorized maturity raises; lines roll up into a subsystem
budget and a duplicated equipment identifier raises; the system margin
required at a phase gate tightens with maturity and a phase before
establishment has no requirement; a budget established after phase B is
flagged, a phase gate passed without a review is flagged, and a margin
below the phase requirement is flagged; the aggregated review is
compliant only when every finding list is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_power_budget_establishment_timing_logic as pb  # noqa: E402


def _equipment(*items):
    return [
        {"equipment_id": eid, "predicted_power_w": power, "maturity_category": cat}
        for eid, power, cat in items
    ]


class PhaseIndexTest(unittest.TestCase):
    def test_phases_are_ordered(self):
        self.assertLess(pb.phase_index("phase_b"), pb.phase_index("phase_c"))
        self.assertLess(pb.phase_index("phase_0"), pb.phase_index("phase_a"))

    def test_uncategorized_phase_raises(self):
        with self.assertRaises(ValueError):
            pb.phase_index("phase_z")


class MaturityMarginTest(unittest.TestCase):
    def test_flight_proven_carries_least_margin(self):
        self.assertAlmostEqual(pb.maturity_margin_fraction("flight_proven"), 0.05)

    def test_modified_existing_sits_between(self):
        self.assertAlmostEqual(pb.maturity_margin_fraction("modified_existing"), 0.10)

    def test_new_development_carries_most_margin(self):
        self.assertAlmostEqual(pb.maturity_margin_fraction("new_development"), 0.20)

    def test_uncategorized_maturity_raises(self):
        with self.assertRaises(ValueError):
            pb.maturity_margin_fraction("probably_fine")


class EquipmentBudgetLineTest(unittest.TestCase):
    def test_margin_is_added_to_prediction(self):
        line = pb.equipment_budget_line("rw_1", 100.0, "new_development")
        self.assertAlmostEqual(line["margin_power_w"], 20.0)
        self.assertAlmostEqual(line["budgeted_power_w"], 120.0)

    def test_zero_power_line_is_allowed(self):
        line = pb.equipment_budget_line("dummy", 0.0, "flight_proven")
        self.assertAlmostEqual(line["budgeted_power_w"], 0.0)

    def test_blank_identifier_raises(self):
        with self.assertRaises(ValueError):
            pb.equipment_budget_line("", 10.0, "flight_proven")

    def test_negative_power_raises(self):
        with self.assertRaises(ValueError):
            pb.equipment_budget_line("rw_1", -1.0, "flight_proven")


class RollUpBudgetTest(unittest.TestCase):
    def test_totals_sum_every_line(self):
        lines = [
            pb.equipment_budget_line("a", 100.0, "flight_proven"),
            pb.equipment_budget_line("b", 200.0, "new_development"),
        ]
        rollup = pb.roll_up_budget(lines)
        self.assertAlmostEqual(rollup["predicted_power_w"], 300.0)
        self.assertAlmostEqual(rollup["margin_power_w"], 45.0)
        self.assertAlmostEqual(rollup["budgeted_power_w"], 345.0)
        self.assertEqual(rollup["line_count"], 2)

    def test_empty_budget_raises(self):
        with self.assertRaises(ValueError):
            pb.roll_up_budget([])

    def test_duplicate_equipment_id_raises(self):
        lines = [
            pb.equipment_budget_line("a", 10.0, "flight_proven"),
            pb.equipment_budget_line("a", 20.0, "flight_proven"),
        ]
        with self.assertRaises(ValueError):
            pb.roll_up_budget(lines)


class SystemMarginTest(unittest.TestCase):
    def test_requirement_tightens_with_maturity(self):
        self.assertGreater(
            pb.required_system_margin("phase_b"), pb.required_system_margin("phase_c")
        )
        self.assertGreater(
            pb.required_system_margin("phase_d"), pb.required_system_margin("phase_e")
        )

    def test_phase_before_establishment_has_no_requirement(self):
        with self.assertRaises(ValueError):
            pb.required_system_margin("phase_a")

    def test_uncategorized_phase_requirement_raises(self):
        with self.assertRaises(ValueError):
            pb.required_system_margin("phase_q")

    def test_achieved_margin_is_unspent_fraction(self):
        self.assertAlmostEqual(pb.achieved_system_margin(1000.0, 800.0), 0.2)

    def test_overrun_gives_negative_margin(self):
        self.assertAlmostEqual(pb.achieved_system_margin(1000.0, 1100.0), -0.1)

    def test_zero_availability_raises(self):
        with self.assertRaises(ValueError):
            pb.achieved_system_margin(0.0, 10.0)

    def test_negative_budgeted_demand_raises(self):
        with self.assertRaises(ValueError):
            pb.achieved_system_margin(100.0, -1.0)


class EstablishmentFindingsTest(unittest.TestCase):
    def test_phase_b_establishment_is_clean(self):
        self.assertEqual(pb.establishment_findings("phase_b"), [])

    def test_earlier_establishment_is_clean(self):
        self.assertEqual(pb.establishment_findings("phase_a"), [])

    def test_late_establishment_is_flagged(self):
        findings = pb.establishment_findings("phase_c")
        self.assertEqual(findings[0]["issue"], "power_budget_established_late")

    def test_missing_establishment_is_flagged(self):
        findings = pb.establishment_findings(None)
        self.assertEqual(findings[0]["issue"], "power_budget_not_established")


class ReviewCadenceTest(unittest.TestCase):
    def test_expected_phases_follow_establishment(self):
        self.assertEqual(
            pb.expected_review_phases("phase_b", "phase_d"), ("phase_c", "phase_d")
        )

    def test_no_review_owed_at_establishment_phase(self):
        self.assertEqual(pb.expected_review_phases("phase_b", "phase_b"), ())

    def test_skipped_gate_is_flagged(self):
        findings = pb.review_cadence_findings("phase_b", "phase_d", ["phase_c"])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["phase"], "phase_d")

    def test_full_cadence_is_clean(self):
        self.assertEqual(
            pb.review_cadence_findings("phase_b", "phase_d", ["phase_c", "phase_d"]), []
        )

    def test_current_phase_before_establishment_raises(self):
        with self.assertRaises(ValueError):
            pb.review_cadence_findings("phase_d", "phase_c", [])

    def test_uncategorized_reviewed_phase_raises(self):
        with self.assertRaises(ValueError):
            pb.review_cadence_findings("phase_b", "phase_c", ["phase_x"])


class MarginFindingsTest(unittest.TestCase):
    def test_margin_at_requirement_is_clean(self):
        self.assertEqual(pb.margin_findings("phase_c", 1000.0, 900.0), [])

    def test_margin_below_requirement_is_flagged(self):
        findings = pb.margin_findings("phase_b", 1000.0, 900.0)
        self.assertEqual(
            findings[0]["issue"], "system_margin_below_phase_requirement"
        )
        self.assertAlmostEqual(findings[0]["achieved_margin"], 0.1)
        self.assertAlmostEqual(findings[0]["required_margin"], 0.2)


class BudgetReviewTest(unittest.TestCase):
    def test_compliant_record_has_no_findings(self):
        record = {
            "established_phase": "phase_b",
            "current_phase": "phase_c",
            "reviewed_phases": ["phase_c"],
            "equipment": _equipment(
                ("obc", 100.0, "flight_proven"), ("payload", 200.0, "modified_existing")
            ),
            "available_power_w": 1000.0,
        }
        review = pb.budget_review(record)
        self.assertAlmostEqual(review["rollup"]["budgeted_power_w"], 325.0)
        self.assertTrue(pb.is_budget_compliant(review))

    def test_late_and_thin_record_is_not_compliant(self):
        record = {
            "established_phase": "phase_d",
            "current_phase": "phase_d",
            "reviewed_phases": [],
            "equipment": _equipment(("payload", 900.0, "new_development")),
            "available_power_w": 1000.0,
        }
        review = pb.budget_review(record)
        self.assertEqual(len(review["establishment"]), 1)
        self.assertEqual(review["review_cadence"], [])
        self.assertEqual(len(review["margin"]), 1)
        self.assertFalse(pb.is_budget_compliant(review))

    def test_unestablished_record_skips_cadence_but_fails(self):
        record = {
            "established_phase": None,
            "current_phase": "phase_c",
            "reviewed_phases": [],
            "equipment": _equipment(("obc", 50.0, "flight_proven")),
            "available_power_w": 1000.0,
        }
        review = pb.budget_review(record)
        self.assertEqual(review["review_cadence"], [])
        self.assertEqual(
            review["establishment"][0]["issue"], "power_budget_not_established"
        )
        self.assertFalse(pb.is_budget_compliant(review))


if __name__ == "__main__":
    unittest.main()
