#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-03C clause 4.4.3 measurement
uncertainty vs. test margin.

Exercises scripts/e1003_uncertainties_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - uncertainty
resolution prefers a project-specific measured value over the Table
4-2 typical for its parameter type; the effective margin is the
demonstrated margin minus the applicable uncertainty; a margin is
adequate only when the effective margin is strictly positive; a
project-specific uncertainty worse than its Table 4-2 typical is
flagged; the assessment record covers every test point with no
duplicates and is reported all-adequate only when every point is
adequate.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1003_uncertainties_logic as ul  # noqa: E402


class TypicalUncertaintyTest(unittest.TestCase):
    def test_known_parameter_type(self):
        self.assertEqual(ul.typical_uncertainty("temperature"), 2.0)

    def test_unknown_parameter_type_raises(self):
        with self.assertRaises(ValueError):
            ul.typical_uncertainty("humidity")

    def test_table_override_extends_defaults(self):
        self.assertEqual(
            ul.typical_uncertainty("humidity", table={"humidity": 3.0}), 3.0
        )

    def test_table_override_replaces_default(self):
        self.assertEqual(
            ul.typical_uncertainty("temperature", table={"temperature": 1.5}), 1.5
        )


class ResolveUncertaintyTest(unittest.TestCase):
    def test_measured_value_takes_precedence(self):
        self.assertEqual(
            ul.resolve_uncertainty("temperature", measured_uncertainty=4.0), 4.0
        )

    def test_falls_back_to_typical_when_measured_absent(self):
        self.assertEqual(ul.resolve_uncertainty("mass"), 1.0)

    def test_falls_back_to_typical_when_measured_none(self):
        self.assertEqual(
            ul.resolve_uncertainty("mass", measured_uncertainty=None), 1.0
        )


class EffectiveMarginTest(unittest.TestCase):
    def test_subtracts_uncertainty_from_margin(self):
        self.assertEqual(ul.effective_margin(6.0, 2.0), 4.0)

    def test_can_go_negative(self):
        self.assertEqual(ul.effective_margin(1.0, 2.0), -1.0)


class MarginIsAdequateTest(unittest.TestCase):
    def test_positive_effective_margin_is_adequate(self):
        self.assertTrue(ul.margin_is_adequate(6.0, 2.0))

    def test_zero_effective_margin_is_not_adequate(self):
        self.assertFalse(ul.margin_is_adequate(2.0, 2.0))

    def test_negative_effective_margin_is_not_adequate(self):
        self.assertFalse(ul.margin_is_adequate(1.0, 2.0))


class ExceedsTypicalTest(unittest.TestCase):
    def test_larger_uncertainty_exceeds_typical(self):
        self.assertTrue(ul.exceeds_typical(3.0, "temperature"))

    def test_equal_uncertainty_does_not_exceed_typical(self):
        self.assertFalse(ul.exceeds_typical(2.0, "temperature"))

    def test_smaller_uncertainty_does_not_exceed_typical(self):
        self.assertFalse(ul.exceeds_typical(1.0, "temperature"))


class AssessTestPointTest(unittest.TestCase):
    def test_adequate_margin_with_table_typical(self):
        point = {
            "id": "TP-001",
            "parameter_type": "acoustic",
            "demonstrated_margin": 3.0,
        }
        result = ul.assess_test_point(point)
        self.assertEqual(result["uncertainty_used"], 1.0)
        self.assertEqual(result["uncertainty_source"], "table_typical")
        self.assertEqual(result["effective_margin"], 2.0)
        self.assertTrue(result["margin_adequate"])
        self.assertFalse(result["uncertainty_flagged"])

    def test_inadequate_margin_with_measured_uncertainty(self):
        point = {
            "id": "TP-002",
            "parameter_type": "vibration",
            "demonstrated_margin": 8.0,
            "measured_uncertainty": 12.0,
        }
        result = ul.assess_test_point(point)
        self.assertEqual(result["uncertainty_source"], "measured")
        self.assertEqual(result["effective_margin"], -4.0)
        self.assertFalse(result["margin_adequate"])
        self.assertTrue(result["uncertainty_flagged"])

    def test_measured_uncertainty_within_typical_not_flagged(self):
        point = {
            "id": "TP-003",
            "parameter_type": "vibration",
            "demonstrated_margin": 15.0,
            "measured_uncertainty": 8.0,
        }
        result = ul.assess_test_point(point)
        self.assertFalse(result["uncertainty_flagged"])
        self.assertTrue(result["margin_adequate"])

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            ul.assess_test_point({
                "parameter_type": "mass",
                "demonstrated_margin": 5.0,
            })

    def test_unknown_parameter_type_raises(self):
        with self.assertRaises(ValueError):
            ul.assess_test_point({
                "id": "TP-004",
                "parameter_type": "humidity",
                "demonstrated_margin": 5.0,
            })


class BuildUncertaintyAssessmentTest(unittest.TestCase):
    POINTS = [
        {
            "id": "TP-001",
            "parameter_type": "temperature",
            "demonstrated_margin": 5.0,
        },
        {
            "id": "TP-002",
            "parameter_type": "pressure",
            "demonstrated_margin": 3.0,
            "measured_uncertainty": 6.0,
        },
    ]

    def test_record_order_and_status(self):
        record = ul.build_uncertainty_assessment(self.POINTS)
        self.assertEqual(record[0]["id"], "TP-001")
        self.assertTrue(record[0]["margin_adequate"])
        self.assertEqual(record[1]["id"], "TP-002")
        self.assertFalse(record[1]["margin_adequate"])
        self.assertTrue(record[1]["uncertainty_flagged"])

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            ul.build_uncertainty_assessment(self.POINTS + [self.POINTS[0]])

    def test_does_not_mutate_input(self):
        before = [dict(p) for p in self.POINTS]
        ul.build_uncertainty_assessment(self.POINTS)
        self.assertEqual(self.POINTS, before)


class RecordSummaryTest(unittest.TestCase):
    def test_inadequate_and_flagged_items(self):
        record = ul.build_uncertainty_assessment([
            {"id": "TP-001", "parameter_type": "temperature", "demonstrated_margin": 5.0},
            {
                "id": "TP-002",
                "parameter_type": "mass",
                "demonstrated_margin": 0.5,
                "measured_uncertainty": 2.0,
            },
        ])
        self.assertEqual(ul.inadequate_items(record), ["TP-002"])
        self.assertEqual(ul.flagged_items(record), ["TP-002"])

    def test_all_margins_adequate_true_when_all_pass(self):
        record = ul.build_uncertainty_assessment([
            {"id": "TP-001", "parameter_type": "temperature", "demonstrated_margin": 5.0},
        ])
        self.assertTrue(ul.all_margins_adequate(record))

    def test_all_margins_adequate_false_when_any_fail(self):
        record = ul.build_uncertainty_assessment([
            {"id": "TP-001", "parameter_type": "temperature", "demonstrated_margin": 5.0},
            {"id": "TP-002", "parameter_type": "mass", "demonstrated_margin": 0.2},
        ])
        self.assertFalse(ul.all_margins_adequate(record))


if __name__ == "__main__":
    unittest.main(verbosity=2)
