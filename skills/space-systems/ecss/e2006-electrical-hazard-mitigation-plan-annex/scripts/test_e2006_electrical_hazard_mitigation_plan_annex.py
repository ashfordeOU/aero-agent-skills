#!/usr/bin/env python3
"""Gate 3 contract test for e2006-electrical-hazard-mitigation-plan-annex.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2006_electrical_hazard_mitigation_plan_annex.py
"""

from __future__ import annotations

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e2006_electrical_hazard_mitigation_plan_annex_logic as logic  # noqa: E402


def hazard_one(**over):
    rec = {
        "hazard_id": "HZ-001",
        "hazard_type": "surface-charging-differential",
        "severity": "critical",
        "likelihood": "occasional",
        "exposure_weight": 0.1,
    }
    rec.update(over)
    return rec


def hazard_two(**over):
    rec = {
        "hazard_id": "HZ-002",
        "hazard_type": "arc-tracking-in-harness",
        "severity": "marginal",
        "likelihood": "remote",
        "exposure_weight": 0.2,
    }
    rec.update(over)
    return rec


def mitigation_one(**over):
    rec = {
        "mitigation_id": "MIT-001",
        "hazard_id": "HZ-001",
        "mitigation_class": "conductive-surface-treatment",
        "verification_method": "analysis",
        "verification_status": "closed",
    }
    rec.update(over)
    return rec


def mitigation_two(**over):
    rec = {
        "mitigation_id": "MIT-002",
        "hazard_id": "HZ-002",
        "mitigation_class": "grounding-bond",
        "verification_method": "inspection",
        "verification_status": "closed",
    }
    rec.update(over)
    return rec


def clean_annex(**over):
    rec = {
        "sections": list(logic.REQUIRED_SECTIONS),
        "hazards": [hazard_one(), hazard_two()],
        "mitigations": [mitigation_one(), mitigation_two()],
    }
    rec.update(over)
    return rec


class TestHazardCategorization(unittest.TestCase):
    def test_surface_hazard_is_electrostatic(self):
        self.assertEqual(
            logic.categorize_hazard("surface-charging-differential"), "electrostatic"
        )

    def test_plume_hazard_is_a_propulsion_interaction(self):
        self.assertEqual(
            logic.categorize_hazard("plume-induced-erosion"), "propulsion-interaction"
        )

    def test_bonding_hazard_is_grounding_and_bonding(self):
        self.assertEqual(
            logic.categorize_hazard("bonding-discontinuity"), "grounding-and-bonding"
        )

    def test_every_declared_type_resolves_to_a_family(self):
        families = {logic.categorize_hazard(t) for t in logic.HAZARD_TYPES}
        self.assertIn("electrostatic", families)
        self.assertIn("power-distribution", families)

    def test_unknown_hazard_type_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_hazard("micrometeoroid-impact")

    def test_missing_hazard_type_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_hazard(None)


class TestRiskGrid(unittest.TestCase):
    def test_index_is_the_product_of_the_two_ranks(self):
        self.assertEqual(logic.risk_index("critical", "occasional"), 9)

    def test_lowest_grid_cell_is_one(self):
        self.assertEqual(logic.risk_index("negligible", "improbable"), 1)

    def test_highest_grid_cell_is_sixteen(self):
        self.assertEqual(logic.risk_index("catastrophic", "probable"), 16)

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            logic.risk_index("severe", "occasional")

    def test_unknown_likelihood_rejected(self):
        with self.assertRaises(ValueError):
            logic.risk_index("critical", "frequent")

    def test_low_index_is_acceptable(self):
        self.assertEqual(logic.categorize_risk(4), "acceptable")

    def test_mid_index_is_tolerable_with_review(self):
        self.assertEqual(logic.categorize_risk(9), "tolerable-with-review")

    def test_high_index_is_unacceptable(self):
        self.assertEqual(logic.categorize_risk(16), "unacceptable")

    def test_unacceptable_boundary_is_inclusive(self):
        self.assertEqual(
            logic.categorize_risk(logic.UNACCEPTABLE_INDEX), "unacceptable"
        )
        self.assertEqual(
            logic.categorize_risk(logic.UNACCEPTABLE_INDEX - 1),
            "tolerable-with-review",
        )

    def test_tolerable_boundary_is_inclusive(self):
        self.assertEqual(
            logic.categorize_risk(logic.TOLERABLE_INDEX), "tolerable-with-review"
        )
        self.assertEqual(logic.categorize_risk(logic.TOLERABLE_INDEX - 1), "acceptable")

    def test_every_band_is_a_declared_band(self):
        for index in range(1, 17):
            self.assertIn(logic.categorize_risk(index), logic.RISK_BANDS)

    def test_index_below_range_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_risk(0)

    def test_index_above_range_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_risk(17)

    def test_fractional_index_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_risk(6.5)

    def test_non_numeric_index_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_risk("nine")


class TestHazardValidation(unittest.TestCase):
    def test_valid_hazard_is_normalized(self):
        haz = logic.validate_hazard(hazard_one())
        self.assertEqual(haz["family"], "electrostatic")
        self.assertEqual(haz["initial_index"], 9)
        self.assertEqual(haz["initial_band"], "tolerable-with-review")

    def test_default_exposure_weight_is_unity(self):
        rec = hazard_one()
        del rec["exposure_weight"]
        self.assertAlmostEqual(
            logic.validate_hazard(rec)["exposure_weight"], 1.0, places=12
        )

    def test_non_mapping_hazard_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_hazard("HZ-001")

    def test_missing_hazard_identifier_rejected(self):
        rec = hazard_one()
        del rec["hazard_id"]
        with self.assertRaises(ValueError):
            logic.validate_hazard(rec)

    def test_zero_exposure_weight_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_hazard(hazard_one(exposure_weight=0.0))

    def test_negative_exposure_weight_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_hazard(hazard_one(exposure_weight=-0.5))


class TestMitigationValidation(unittest.TestCase):
    def test_valid_mitigation_is_normalized(self):
        entry = logic.validate_mitigation(mitigation_one())
        self.assertEqual(entry["hazard_id"], "HZ-001")
        self.assertEqual(entry["verification_status"], "closed")

    def test_non_mapping_mitigation_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_mitigation(["MIT-001"])

    def test_missing_mitigation_identifier_rejected(self):
        rec = mitigation_one()
        del rec["mitigation_id"]
        with self.assertRaises(ValueError):
            logic.validate_mitigation(rec)

    def test_missing_hazard_link_rejected(self):
        rec = mitigation_one()
        del rec["hazard_id"]
        with self.assertRaises(ValueError):
            logic.validate_mitigation(rec)

    def test_unknown_mitigation_class_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_mitigation(mitigation_one(mitigation_class="paint-it"))

    def test_unknown_verification_method_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_mitigation(mitigation_one(verification_method="hunch"))

    def test_unknown_verification_status_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_mitigation(mitigation_one(verification_status="maybe"))


class TestMitigationCredit(unittest.TestCase):
    def test_closed_verification_earns_the_full_credit(self):
        credit, axis = logic.mitigation_credit(mitigation_one())
        self.assertEqual(credit, 2)
        self.assertEqual(axis, "likelihood")

    def test_running_verification_earns_a_capped_credit(self):
        credit, _ = logic.mitigation_credit(
            mitigation_one(verification_status="in-progress")
        )
        self.assertEqual(credit, logic.PROVISIONAL_CREDIT_CAP)

    def test_open_verification_earns_nothing(self):
        credit, _ = logic.mitigation_credit(mitigation_one(verification_status="open"))
        self.assertEqual(credit, 0)

    def test_severity_reducing_class_is_reported_on_that_axis(self):
        credit, axis = logic.mitigation_credit(
            mitigation_one(mitigation_class="redundant-return-path")
        )
        self.assertEqual(axis, "severity")
        self.assertEqual(credit, 2)

    def test_provisional_credit_never_exceeds_the_class_credit(self):
        credit, _ = logic.mitigation_credit(
            mitigation_one(
                mitigation_class="grounding-bond", verification_status="in-progress"
            )
        )
        self.assertEqual(credit, 1)


class TestSectionCompleteness(unittest.TestCase):
    def test_complete_annex_has_no_missing_sections(self):
        self.assertEqual(logic.check_sections(list(logic.REQUIRED_SECTIONS)), [])

    def test_missing_section_is_reported(self):
        sections = [s for s in logic.REQUIRED_SECTIONS if s != "verification-status"]
        self.assertEqual(logic.check_sections(sections), ["verification-status"])

    def test_missing_sections_keep_reading_order(self):
        sections = ["hazard-inventory"]
        missing = logic.check_sections(sections)
        expected = [s for s in logic.REQUIRED_SECTIONS if s != "hazard-inventory"]
        self.assertEqual(missing, expected)

    def test_optional_sections_do_not_affect_completeness(self):
        sections = list(logic.REQUIRED_SECTIONS) + ["configuration-baseline"]
        self.assertEqual(logic.check_sections(sections), [])

    def test_unknown_section_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_sections(list(logic.REQUIRED_SECTIONS) + ["executive-summary"])

    def test_non_sequence_sections_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_sections("hazard-inventory")


class TestResidualRisk(unittest.TestCase):
    def test_closed_mitigation_lowers_the_likelihood_rank(self):
        result = logic.residual_risk(hazard_one(), [mitigation_one()])
        self.assertEqual(result["residual_likelihood_rank"], 1)
        self.assertEqual(result["residual_severity_rank"], 3)
        self.assertEqual(result["residual_index"], 3)
        self.assertEqual(result["residual_band"], "acceptable")

    def test_severity_class_lowers_the_severity_rank(self):
        result = logic.residual_risk(
            hazard_one(), [mitigation_one(mitigation_class="redundant-return-path")]
        )
        self.assertEqual(result["residual_severity_rank"], 1)
        self.assertEqual(result["residual_likelihood_rank"], 3)

    def test_open_verification_earns_no_reduction_and_raises_a_finding(self):
        result = logic.residual_risk(
            hazard_one(), [mitigation_one(verification_status="open")]
        )
        self.assertEqual(result["residual_index"], result["initial_index"])
        self.assertTrue(any("open verification" in f for f in result["findings"]))

    def test_unmitigated_hazard_raises_a_finding(self):
        result = logic.residual_risk(hazard_one(), [])
        self.assertTrue(any("no mitigation is recorded" in f for f in result["findings"]))
        self.assertEqual(result["residual_index"], result["initial_index"])

    def test_mitigation_for_another_hazard_is_ignored(self):
        result = logic.residual_risk(hazard_one(), [mitigation_two()])
        self.assertEqual(result["mitigations"], [])
        self.assertEqual(result["residual_index"], result["initial_index"])

    def test_ranks_never_fall_below_one(self):
        result = logic.residual_risk(
            hazard_two(),
            [
                mitigation_two(mitigation_class="conductive-surface-treatment"),
                mitigation_two(
                    mitigation_id="MIT-003", mitigation_class="shielding-augmentation"
                ),
            ],
        )
        self.assertEqual(result["residual_likelihood_rank"], 1)
        self.assertEqual(result["residual_index"], 2)

    def test_credits_from_several_mitigations_accumulate(self):
        worst = hazard_one(severity="catastrophic", likelihood="probable")
        result = logic.residual_risk(
            worst,
            [
                mitigation_one(mitigation_class="grounding-bond"),
                mitigation_one(
                    mitigation_id="MIT-004", mitigation_class="operational-constraint"
                ),
            ],
        )
        self.assertEqual(result["residual_likelihood_rank"], 2)
        self.assertEqual(result["residual_index"], 8)

    def test_residual_still_unacceptable_raises_a_finding(self):
        worst = hazard_one(severity="catastrophic", likelihood="probable")
        result = logic.residual_risk(
            worst, [mitigation_one(mitigation_class="grounding-bond")]
        )
        self.assertEqual(result["residual_index"], 12)
        self.assertTrue(
            any("remains unacceptable" in f for f in result["findings"])
        )

    def test_invalid_hazard_rejected(self):
        with self.assertRaises(ValueError):
            logic.residual_risk(hazard_one(hazard_type="solar-flare"), [])

    def test_invalid_mitigation_rejected(self):
        with self.assertRaises(ValueError):
            logic.residual_risk(hazard_one(), [mitigation_one(verification_status="wip")])


class TestWeightedScore(unittest.TestCase):
    def test_score_is_the_exposure_weighted_mean(self):
        results = [
            logic.residual_risk(hazard_one(), [mitigation_one()]),
            logic.residual_risk(hazard_two(), [mitigation_two()]),
        ]
        expected = (3 * 0.1 + 2 * 0.2) / (0.1 + 0.2)
        self.assertAlmostEqual(logic.weighted_residual_score(results), expected, places=12)

    def test_equal_weights_give_the_plain_mean(self):
        results = [
            logic.residual_risk(hazard_one(exposure_weight=1.0), [mitigation_one()]),
            logic.residual_risk(hazard_two(exposure_weight=1.0), [mitigation_two()]),
        ]
        self.assertAlmostEqual(logic.weighted_residual_score(results), 2.5, places=12)

    def test_heavier_hazard_dominates_the_score(self):
        heavy = logic.residual_risk(hazard_one(exposure_weight=100.0), [mitigation_one()])
        light = logic.residual_risk(hazard_two(exposure_weight=0.01), [mitigation_two()])
        self.assertAlmostEqual(
            logic.weighted_residual_score([heavy, light]), 3.0, places=3
        )

    def test_empty_result_list_rejected(self):
        with self.assertRaises(ValueError):
            logic.weighted_residual_score([])


class TestPlanAnnexAssessment(unittest.TestCase):
    def test_complete_annex_is_ready_for_release(self):
        result = logic.assess_plan_annex(clean_annex())
        self.assertTrue(result["ready_for_release"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["missing_sections"], [])

    def test_worst_hazard_is_reported(self):
        result = logic.assess_plan_annex(clean_annex())
        self.assertEqual(result["worst_hazard_id"], "HZ-001")
        self.assertEqual(result["worst_residual_index"], 3)

    def test_missing_section_blocks_release(self):
        annex = clean_annex(
            sections=[s for s in logic.REQUIRED_SECTIONS if s != "residual-risk-statement"]
        )
        result = logic.assess_plan_annex(annex)
        self.assertFalse(result["ready_for_release"])
        self.assertEqual(result["missing_sections"], ["residual-risk-statement"])
        self.assertTrue(any("is missing" in f for f in result["findings"]))

    def test_open_verification_blocks_release(self):
        annex = clean_annex(
            mitigations=[mitigation_one(verification_status="open"), mitigation_two()]
        )
        result = logic.assess_plan_annex(annex)
        self.assertFalse(result["ready_for_release"])
        self.assertTrue(any("open verification" in f for f in result["findings"]))

    def test_unmitigated_hazard_blocks_release(self):
        annex = clean_annex(mitigations=[mitigation_two()])
        result = logic.assess_plan_annex(annex)
        self.assertFalse(result["ready_for_release"])
        self.assertTrue(any("HZ-001" in f for f in result["findings"]))

    def test_dangling_mitigation_is_reported(self):
        annex = clean_annex(
            mitigations=[
                mitigation_one(),
                mitigation_two(),
                mitigation_two(mitigation_id="MIT-009", hazard_id="HZ-404"),
            ]
        )
        result = logic.assess_plan_annex(annex)
        self.assertFalse(result["ready_for_release"])
        self.assertTrue(
            any("the inventory does not declare" in f for f in result["findings"])
        )

    def test_unacceptable_residual_blocks_release(self):
        annex = clean_annex(
            hazards=[
                hazard_one(severity="catastrophic", likelihood="probable"),
                hazard_two(),
            ],
            mitigations=[
                mitigation_one(mitigation_class="grounding-bond"),
                mitigation_two(),
            ],
        )
        result = logic.assess_plan_annex(annex, acceptance_score=16.0)
        self.assertFalse(result["ready_for_release"])
        self.assertTrue(any("remains unacceptable" in f for f in result["findings"]))

    def test_score_above_the_threshold_is_reported(self):
        annex = clean_annex()
        result = logic.assess_plan_annex(annex, acceptance_score=1.0)
        self.assertFalse(result["ready_for_release"])
        self.assertTrue(
            any("exceeds the acceptance threshold" in f for f in result["findings"])
        )

    def test_score_exactly_on_the_threshold_is_accepted(self):
        probe = logic.assess_plan_annex(clean_annex())
        exact = logic.assess_plan_annex(
            clean_annex(), acceptance_score=probe["weighted_residual_score"]
        )
        self.assertTrue(exact["ready_for_release"])

    def test_representation_error_on_the_threshold_is_absorbed(self):
        probe = logic.assess_plan_annex(clean_annex())
        score = probe["weighted_residual_score"]
        threshold = math.nextafter(score, 0.0)
        self.assertLess(threshold, score)
        edge = logic.assess_plan_annex(clean_annex(), acceptance_score=threshold)
        self.assertTrue(edge["ready_for_release"])

    def test_duplicate_hazard_identifier_rejected(self):
        annex = clean_annex(hazards=[hazard_one(), hazard_one()])
        with self.assertRaises(ValueError):
            logic.assess_plan_annex(annex)

    def test_non_mapping_annex_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_plan_annex(["hazard-inventory"])

    def test_annex_without_hazards_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_plan_annex(clean_annex(hazards=[]))

    def test_non_positive_acceptance_score_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_plan_annex(clean_annex(), acceptance_score=0.0)

    def test_unknown_section_in_annex_rejected(self):
        annex = clean_annex(sections=list(logic.REQUIRED_SECTIONS) + ["appendix-z"])
        with self.assertRaises(ValueError):
            logic.assess_plan_annex(annex)


if __name__ == "__main__":
    unittest.main()
