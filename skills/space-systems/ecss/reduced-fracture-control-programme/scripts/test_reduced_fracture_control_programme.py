"""
Gate 3 contract tests for reduced_fracture_control_programme_logic.
stdlib unittest only; deterministic; offline.
Run: python3 test_reduced_fracture_control_programme.py
"""

import sys
import os
import unittest

# Allow running directly from the scripts/ directory or from the repo root.
sys.path.insert(0, os.path.dirname(__file__))

from reduced_fracture_control_programme_logic import (
    assess_eligibility,
    assess_batch,
    summary_counts,
    InputError,
    WAIVABLE_STEPS,
    MANDATORY_REMAINING_ACTIONS,
    STRESS_RATIO_THRESHOLD_CREWED,
    STRESS_RATIO_THRESHOLD_UNCREWED,
    MIN_KIC_MPA_SQRTM,
)


def _make_component(**overrides):
    """Return a valid, eligible base component with optional field overrides."""
    base = {
        "id": "ITEM-001",
        "fracture_category": "non_fracture_critical",
        "consequence": "minor",
        "operating_stress_ratio": 0.30,
        "mission_type": "uncrewed",
        "kic_mpa_sqrtm": 50.0,
    }
    base.update(overrides)
    return base


class TestEligibleBaseline(unittest.TestCase):
    """Valid low-risk item must be eligible with all modifications granted."""

    def test_eligible_returns_true(self):
        result = assess_eligibility(_make_component())
        self.assertTrue(result["eligible"])

    def test_eligible_no_ineligibility_reason(self):
        result = assess_eligibility(_make_component())
        self.assertIsNone(result["ineligibility_reason"])

    def test_eligible_grants_all_waivable_steps(self):
        result = assess_eligibility(_make_component())
        self.assertEqual(sorted(result["modifications"]), sorted(WAIVABLE_STEPS))

    def test_eligible_includes_all_mandatory_actions(self):
        result = assess_eligibility(_make_component())
        self.assertEqual(
            sorted(result["mandatory_actions"]),
            sorted(MANDATORY_REMAINING_ACTIONS),
        )


class TestFractureCriticalExclusion(unittest.TestCase):
    """Fracture-critical items are never eligible."""

    def test_fracture_critical_not_eligible(self):
        result = assess_eligibility(_make_component(fracture_category="fracture_critical"))
        self.assertFalse(result["eligible"])

    def test_fracture_critical_reason_recorded(self):
        result = assess_eligibility(_make_component(fracture_category="fracture_critical"))
        self.assertIsNotNone(result["ineligibility_reason"])
        self.assertIn("fracture-critical", result["ineligibility_reason"])

    def test_fracture_critical_no_modifications(self):
        result = assess_eligibility(_make_component(fracture_category="fracture_critical"))
        self.assertEqual(result["modifications"], [])


class TestCatastrophicConsequenceExclusion(unittest.TestCase):
    """Catastrophic consequence of failure excludes the reduced programme."""

    def test_catastrophic_not_eligible(self):
        result = assess_eligibility(_make_component(consequence="catastrophic"))
        self.assertFalse(result["eligible"])

    def test_catastrophic_reason_recorded(self):
        result = assess_eligibility(_make_component(consequence="catastrophic"))
        self.assertIsNotNone(result["ineligibility_reason"])
        self.assertIn("catastrophic", result["ineligibility_reason"])

    def test_critical_consequence_can_be_eligible(self):
        """'critical' (not 'catastrophic') should not auto-exclude."""
        result = assess_eligibility(_make_component(consequence="critical"))
        self.assertTrue(result["eligible"])


class TestStressRatioThresholds(unittest.TestCase):
    """Operating stress ratio must be at or below the mission-type threshold."""

    def test_uncrewed_at_threshold_eligible(self):
        result = assess_eligibility(
            _make_component(
                mission_type="uncrewed",
                operating_stress_ratio=STRESS_RATIO_THRESHOLD_UNCREWED,
            )
        )
        self.assertTrue(result["eligible"])

    def test_uncrewed_above_threshold_not_eligible(self):
        result = assess_eligibility(
            _make_component(
                mission_type="uncrewed",
                operating_stress_ratio=STRESS_RATIO_THRESHOLD_UNCREWED + 0.01,
            )
        )
        self.assertFalse(result["eligible"])
        self.assertIn("stress ratio", result["ineligibility_reason"])

    def test_crewed_at_threshold_eligible(self):
        result = assess_eligibility(
            _make_component(
                mission_type="crewed",
                operating_stress_ratio=STRESS_RATIO_THRESHOLD_CREWED,
            )
        )
        self.assertTrue(result["eligible"])

    def test_crewed_above_threshold_not_eligible(self):
        result = assess_eligibility(
            _make_component(
                mission_type="crewed",
                operating_stress_ratio=STRESS_RATIO_THRESHOLD_CREWED + 0.01,
            )
        )
        self.assertFalse(result["eligible"])

    def test_crewed_threshold_stricter_than_uncrewed(self):
        """A ratio that passes uncrewed must fail crewed."""
        ratio_between = (STRESS_RATIO_THRESHOLD_CREWED + STRESS_RATIO_THRESHOLD_UNCREWED) / 2
        uncrewed_result = assess_eligibility(
            _make_component(mission_type="uncrewed", operating_stress_ratio=ratio_between)
        )
        crewed_result = assess_eligibility(
            _make_component(mission_type="crewed", operating_stress_ratio=ratio_between)
        )
        self.assertTrue(uncrewed_result["eligible"])
        self.assertFalse(crewed_result["eligible"])


class TestFractureToughnessCheck(unittest.TestCase):
    """K_IC must meet the minimum toughness threshold."""

    def test_kic_at_minimum_eligible(self):
        result = assess_eligibility(_make_component(kic_mpa_sqrtm=MIN_KIC_MPA_SQRTM))
        self.assertTrue(result["eligible"])

    def test_kic_below_minimum_not_eligible(self):
        result = assess_eligibility(_make_component(kic_mpa_sqrtm=MIN_KIC_MPA_SQRTM - 0.1))
        self.assertFalse(result["eligible"])
        self.assertIn("K_IC", result["ineligibility_reason"])

    def test_kic_well_above_minimum_eligible(self):
        result = assess_eligibility(_make_component(kic_mpa_sqrtm=100.0))
        self.assertTrue(result["eligible"])


class TestInputValidation(unittest.TestCase):
    """InputError must be raised for invalid or missing fields."""

    def test_missing_id_raises(self):
        c = _make_component()
        del c["id"]
        with self.assertRaises(InputError):
            assess_eligibility(c)

    def test_unknown_fracture_category_raises(self):
        with self.assertRaises(InputError):
            assess_eligibility(_make_component(fracture_category="unknown_category"))

    def test_unknown_consequence_raises(self):
        with self.assertRaises(InputError):
            assess_eligibility(_make_component(consequence="negligible"))

    def test_unknown_mission_type_raises(self):
        with self.assertRaises(InputError):
            assess_eligibility(_make_component(mission_type="robotic"))

    def test_stress_ratio_above_one_raises(self):
        with self.assertRaises(InputError):
            assess_eligibility(_make_component(operating_stress_ratio=1.01))

    def test_stress_ratio_negative_raises(self):
        with self.assertRaises(InputError):
            assess_eligibility(_make_component(operating_stress_ratio=-0.1))

    def test_kic_zero_raises(self):
        with self.assertRaises(InputError):
            assess_eligibility(_make_component(kic_mpa_sqrtm=0.0))

    def test_kic_negative_raises(self):
        with self.assertRaises(InputError):
            assess_eligibility(_make_component(kic_mpa_sqrtm=-5.0))


class TestBatchAndSummary(unittest.TestCase):
    """Batch assessment and summary counts work correctly."""

    def _batch_of_three(self):
        return [
            _make_component(id="ITEM-A"),
            _make_component(id="ITEM-B", fracture_category="fracture_critical"),
            _make_component(id="ITEM-C", consequence="catastrophic"),
        ]

    def test_batch_returns_one_result_per_input(self):
        results = assess_batch(self._batch_of_three())
        self.assertEqual(len(results), 3)

    def test_batch_preserves_ids(self):
        results = assess_batch(self._batch_of_three())
        ids = [r["id"] for r in results]
        self.assertEqual(ids, ["ITEM-A", "ITEM-B", "ITEM-C"])

    def test_summary_counts_match(self):
        results = assess_batch(self._batch_of_three())
        counts = summary_counts(results)
        self.assertEqual(counts["total"], 3)
        self.assertEqual(counts["eligible"], 1)
        self.assertEqual(counts["ineligible"], 2)

    def test_batch_raises_on_invalid_component(self):
        bad = [_make_component(id="OK"), _make_component(fracture_category="invalid")]
        with self.assertRaises(InputError):
            assess_batch(bad)


class TestMandatoryActionsAlwaysPresent(unittest.TestCase):
    """Mandatory remaining actions appear in every result, eligible or not."""

    def test_ineligible_item_still_has_mandatory_actions(self):
        result = assess_eligibility(_make_component(fracture_category="fracture_critical"))
        self.assertEqual(
            sorted(result["mandatory_actions"]),
            sorted(MANDATORY_REMAINING_ACTIONS),
        )

    def test_eligible_item_has_mandatory_actions(self):
        result = assess_eligibility(_make_component())
        self.assertEqual(
            sorted(result["mandatory_actions"]),
            sorted(MANDATORY_REMAINING_ACTIONS),
        )


if __name__ == "__main__":
    unittest.main()
