"""Contract test for the ECSS-Q-ST-60-13C clause 5.2.3.3 Class 2 analysis leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6013_class_2_constructional_analysis.py
"""

import unittest

from q6013_class_2_constructional_analysis_logic import (
    CLASS_2_ACCEPT_INDEX,
    CLASS_2_MITIGATION_INDEX,
    DISQUALIFYING_SEVERITY,
    HERMETIC_ONLY_STEPS,
    INDEX_TOLERANCE,
    OBSERVATION_SEVERITY_SCORE,
    PACKAGE_TYPES,
    STEP_MIN_SAMPLE,
    STEP_WEIGHTS,
    STRUCTURAL_STEPS,
    VERDICTS,
    WEAKNESS_SEVERITIES,
    assess_analysis,
    assess_step,
    construction_risk_index,
    index_disposition,
    normalize_step,
    required_sample,
    sample_representative,
    severity_score,
    step_applicable,
    step_weight,
)

LOT = "2617"


def clean_steps(package_type="hermetic", **overrides):
    """Every applicable step performed on a sufficient sample, nothing found."""
    steps = []
    for name in sorted(STEP_WEIGHTS):
        if not step_applicable(name, package_type):
            continue
        entry = {
            "step": name,
            "performed": True,
            "sample_size": STEP_MIN_SAMPLE[name],
            "severity": "no-anomaly",
        }
        if name in overrides:
            entry.update(overrides[name])
        steps.append(entry)
    return steps


def applicable_weight(package_type="hermetic"):
    return sum(
        weight
        for name, weight in STEP_WEIGHTS.items()
        if step_applicable(name, package_type)
    )


class StepWeightTests(unittest.TestCase):
    def test_every_step_carries_a_positive_weight(self):
        for name in STEP_WEIGHTS:
            self.assertGreater(step_weight(name), 0.0)

    def test_the_structural_steps_carry_the_heaviest_weight(self):
        heaviest = max(STEP_WEIGHTS.values())
        for name in STRUCTURAL_STEPS:
            self.assertAlmostEqual(step_weight(name), heaviest, places=9)

    def test_every_step_owes_at_least_one_part(self):
        for name in STEP_WEIGHTS:
            self.assertGreaterEqual(required_sample(name), 1)

    def test_unknown_step_rejected(self):
        with self.assertRaises(ValueError):
            step_weight("shake-it-and-listen")


class SeverityTests(unittest.TestCase):
    def test_a_clean_step_scores_nothing(self):
        self.assertAlmostEqual(severity_score("no-anomaly"), 0.0, places=9)

    def test_a_disqualifying_defect_scores_the_maximum(self):
        self.assertAlmostEqual(severity_score(DISQUALIFYING_SEVERITY), 1.0, places=9)

    def test_severity_scores_rise_with_severity(self):
        ordered = [
            "no-anomaly",
            "cosmetic-anomaly",
            "workmanship-deviation",
            "construction-weakness",
            "disqualifying-defect",
        ]
        scores = [severity_score(name) for name in ordered]
        self.assertEqual(scores, sorted(scores))
        self.assertEqual(len(set(scores)), len(scores))

    def test_every_score_sits_between_zero_and_one(self):
        # The scores are declared constants, so both ends of the scale are
        # exact literals. The extremes pin the closed interval for every
        # entry at once, without a comparison whose two sides are the same
        # bit pattern at the top of the scale.
        scores = list(OBSERVATION_SEVERITY_SCORE.values())
        self.assertEqual(min(scores), 0.0)
        self.assertEqual(max(scores), 1.0)

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            severity_score("looked-a-bit-odd")


class PackageApplicabilityTests(unittest.TestCase):
    def test_a_hermetic_only_step_has_nothing_to_measure_on_plastic(self):
        for name in HERMETIC_ONLY_STEPS:
            self.assertTrue(step_applicable(name, "hermetic"))
            self.assertFalse(step_applicable(name, "plastic-encapsulated"))

    def test_a_structural_step_applies_to_every_package(self):
        for name in STRUCTURAL_STEPS:
            for package in PACKAGE_TYPES:
                self.assertTrue(step_applicable(name, package))

    def test_unknown_package_rejected(self):
        with self.assertRaises(ValueError):
            step_applicable("x-ray-radiography", "shrink-wrapped")


class SampleProvenanceTests(unittest.TestCase):
    def test_the_same_date_code_represents_the_lot(self):
        self.assertTrue(sample_representative(LOT, LOT))

    def test_surrounding_space_does_not_change_the_date_code(self):
        self.assertTrue(sample_representative(" 2617 ", "2617"))

    def test_another_date_code_does_not_represent_the_lot(self):
        self.assertFalse(sample_representative("2540", LOT))

    def test_an_empty_date_code_rejected(self):
        with self.assertRaises(ValueError):
            sample_representative("   ", LOT)


class NormaliseStepTests(unittest.TestCase):
    def test_a_step_defaults_to_performed_with_no_sample(self):
        record = normalize_step({"step": "x-ray-radiography"})
        self.assertTrue(record["performed"])
        self.assertEqual(record["sample_size"], 0)
        self.assertEqual(record["severity"], "no-anomaly")

    def test_a_step_not_performed_cannot_carry_a_sample(self):
        with self.assertRaises(ValueError):
            normalize_step(
                {"step": "die-shear-test", "performed": False, "sample_size": 2}
            )

    def test_a_step_not_performed_cannot_report_an_observation(self):
        with self.assertRaises(ValueError):
            normalize_step(
                {
                    "step": "die-shear-test",
                    "performed": False,
                    "severity": "construction-weakness",
                }
            )

    def test_a_fractional_sample_size_rejected(self):
        with self.assertRaises(ValueError):
            normalize_step({"step": "die-shear-test", "sample_size": 2.5})

    def test_a_boolean_sample_size_rejected(self):
        with self.assertRaises(ValueError):
            normalize_step({"step": "die-shear-test", "sample_size": True})

    def test_a_negative_sample_size_rejected(self):
        with self.assertRaises(ValueError):
            normalize_step({"step": "die-shear-test", "sample_size": -1})

    def test_non_mapping_step_rejected(self):
        with self.assertRaises(ValueError):
            normalize_step("die-shear-test")


class AssessStepTests(unittest.TestCase):
    def test_a_clean_sufficient_step_leaves_no_finding(self):
        record = assess_step(
            {
                "step": "die-shear-test",
                "performed": True,
                "sample_size": STEP_MIN_SAMPLE["die-shear-test"],
            }
        )
        self.assertEqual(record["findings"], [])
        self.assertAlmostEqual(record["weighted_score"], 0.0, places=9)

    def test_an_under_sampled_step_is_reported_not_credited(self):
        record = assess_step(
            {
                "step": "external-visual-inspection",
                "performed": True,
                "sample_size": STEP_MIN_SAMPLE["external-visual-inspection"] - 1,
            }
        )
        self.assertIn("step-under-sampled", record["findings"])

    def test_an_under_sampled_structural_step_is_also_unrepresentative(self):
        record = assess_step(
            {
                "step": "wire-bond-integrity-test",
                "performed": True,
                "sample_size": STEP_MIN_SAMPLE["wire-bond-integrity-test"] - 1,
            }
        )
        self.assertIn("structural-step-not-representative", record["findings"])

    def test_a_skipped_structural_step_is_named_as_such(self):
        record = assess_step({"step": "internal-visual-inspection", "performed": False})
        self.assertIn("structural-step-not-performed", record["findings"])

    def test_an_inapplicable_step_carries_no_weight_and_no_finding(self):
        record = assess_step(
            {"step": "hermeticity-and-seal-test", "performed": False}, applicable=False
        )
        self.assertFalse(record["applicable"])
        self.assertAlmostEqual(record["weight"], 0.0, places=9)
        self.assertEqual(record["findings"], [])

    def test_a_weakness_is_carried_forward_by_name(self):
        for severity in WEAKNESS_SEVERITIES:
            record = assess_step(
                {
                    "step": "die-metallisation-inspection",
                    "performed": True,
                    "sample_size": STEP_MIN_SAMPLE["die-metallisation-inspection"],
                    "severity": severity,
                }
            )
            self.assertIn(severity, record["findings"])

    def test_non_boolean_applicability_rejected(self):
        with self.assertRaises(ValueError):
            assess_step({"step": "die-shear-test"}, applicable="sort-of")


class RiskIndexTests(unittest.TestCase):
    def test_a_clean_analysis_scores_zero(self):
        report = assess_analysis("cots-mux-01", "hermetic", clean_steps(), LOT, LOT)
        self.assertAlmostEqual(report["construction_risk_index"], 0.0, places=9)

    def test_one_deviation_weighs_its_own_step_only(self):
        report = assess_analysis(
            "cots-mux-01",
            "hermetic",
            clean_steps(**{"x-ray-radiography": {"severity": "workmanship-deviation"}}),
            LOT,
            LOT,
        )
        expected = (
            STEP_WEIGHTS["x-ray-radiography"]
            * OBSERVATION_SEVERITY_SCORE["workmanship-deviation"]
            / applicable_weight("hermetic")
        )
        self.assertAlmostEqual(report["construction_risk_index"], expected, places=9)

    def test_the_index_never_leaves_the_unit_interval(self):
        report = assess_analysis(
            "cots-mux-01",
            "hermetic",
            clean_steps(
                **{
                    name: {"severity": DISQUALIFYING_SEVERITY}
                    for name in STEP_WEIGHTS
                    if step_applicable(name, "hermetic")
                }
            ),
            LOT,
            LOT,
        )
        self.assertAlmostEqual(report["construction_risk_index"], 1.0, places=9)

    def test_an_index_exactly_on_the_accept_bound_is_acceptable(self):
        self.assertEqual(index_disposition(CLASS_2_ACCEPT_INDEX), "construction-acceptable")

    def test_an_index_exactly_on_the_mitigation_bound_is_mitigable(self):
        self.assertEqual(
            index_disposition(CLASS_2_MITIGATION_INDEX),
            "construction-acceptable-with-mitigation",
        )

    def test_an_index_a_hair_over_a_bound_stays_inside_it(self):
        self.assertEqual(
            index_disposition(CLASS_2_ACCEPT_INDEX + INDEX_TOLERANCE / 2.0),
            "construction-acceptable",
        )

    def test_an_index_materially_past_the_mitigation_bound_is_rejected(self):
        self.assertEqual(
            index_disposition(CLASS_2_MITIGATION_INDEX + 0.05), "construction-rejected"
        )

    def test_a_negative_index_rejected(self):
        with self.assertRaises(ValueError):
            index_disposition(-0.01)

    def test_the_index_rejects_an_empty_record_set(self):
        with self.assertRaises(ValueError):
            construction_risk_index([])

    def test_the_index_rejects_a_set_with_no_applicable_weight(self):
        with self.assertRaises(ValueError):
            construction_risk_index(
                [{"applicable": False, "weight": 0.0, "weighted_score": 0.0}]
            )

    def test_the_index_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            construction_risk_index({"weight": 1.0, "weighted_score": 0.0})


class AnalysisVerdictTests(unittest.TestCase):
    def test_a_clean_hermetic_analysis_is_usable(self):
        report = assess_analysis("cots-mux-01", "hermetic", clean_steps(), LOT, LOT)
        self.assertEqual(report["verdict"], "construction-acceptable")
        self.assertTrue(report["usable_at_class_2"])
        self.assertEqual(report["findings"], [])

    def test_a_plastic_part_drops_the_hermetic_steps_from_the_set(self):
        report = assess_analysis(
            "cots-mux-02", "plastic-encapsulated", clean_steps("plastic-encapsulated"), LOT, LOT
        )
        self.assertEqual(sorted(report["inapplicable_steps"]), sorted(HERMETIC_ONLY_STEPS))
        self.assertEqual(report["verdict"], "construction-acceptable")
        self.assertEqual(report["findings"], [])

    def test_a_skipped_structural_step_makes_the_analysis_incomplete(self):
        steps = [
            step
            for step in clean_steps()
            if step["step"] != "wire-bond-integrity-test"
        ]
        report = assess_analysis("cots-mux-01", "hermetic", steps, LOT, LOT)
        self.assertEqual(report["verdict"], "constructional-analysis-incomplete")
        self.assertEqual(report["incomplete_structural_steps"], ["wire-bond-integrity-test"])

    def test_a_sample_from_another_lot_makes_the_analysis_incomplete(self):
        report = assess_analysis("cots-mux-01", "hermetic", clean_steps(), "2540", LOT)
        self.assertEqual(report["verdict"], "constructional-analysis-incomplete")
        self.assertFalse(report["sample_representative"])
        self.assertIn(
            {"step": "sample-provenance", "finding": "sample-not-drawn-from-procurement-lot"},
            report["findings"],
        )

    def test_a_disqualifying_defect_rejects_the_part_type_outright(self):
        report = assess_analysis(
            "cots-mux-01",
            "hermetic",
            clean_steps(
                **{"cross-section-and-materials-review": {"severity": DISQUALIFYING_SEVERITY}}
            ),
            LOT,
            LOT,
        )
        self.assertEqual(report["verdict"], "construction-rejected")
        self.assertEqual(
            report["disqualifying_steps"], ["cross-section-and-materials-review"]
        )

    def test_one_weakness_on_a_light_step_still_owes_a_mitigation(self):
        report = assess_analysis(
            "cots-mux-01",
            "hermetic",
            clean_steps(**{"die-shear-test": {"severity": "construction-weakness"}}),
            LOT,
            LOT,
        )
        self.assertLessEqual(
            report["construction_risk_index"], CLASS_2_ACCEPT_INDEX + INDEX_TOLERANCE
        )
        self.assertEqual(report["verdict"], "construction-acceptable-with-mitigation")
        self.assertFalse(report["usable_at_class_2"])

    def test_weaknesses_come_back_heaviest_first(self):
        report = assess_analysis(
            "cots-mux-01",
            "hermetic",
            clean_steps(
                **{
                    "die-shear-test": {"severity": "construction-weakness"},
                    "internal-visual-inspection": {"severity": "construction-weakness"},
                }
            ),
            LOT,
            LOT,
        )
        self.assertEqual(
            report["weaknesses"], ["internal-visual-inspection", "die-shear-test"]
        )

    def test_widespread_weakness_rejects_the_part_type(self):
        report = assess_analysis(
            "cots-mux-01",
            "hermetic",
            clean_steps(
                **{
                    name: {"severity": "construction-weakness"}
                    for name in STRUCTURAL_STEPS
                }
            ),
            LOT,
            LOT,
        )
        self.assertGreater(report["construction_risk_index"], CLASS_2_MITIGATION_INDEX)
        self.assertEqual(report["verdict"], "construction-rejected")

    def test_an_undeclared_step_counts_as_not_performed(self):
        report = assess_analysis("cots-mux-01", "hermetic", [], LOT, LOT)
        self.assertEqual(report["verdict"], "constructional-analysis-incomplete")
        self.assertEqual(len(report["records"]), len(STEP_WEIGHTS))
        self.assertEqual(
            sorted(report["incomplete_structural_steps"]), sorted(STRUCTURAL_STEPS)
        )

    def test_every_verdict_name_is_one_the_module_publishes(self):
        seen = {
            assess_analysis("p", "hermetic", clean_steps(), LOT, LOT)["verdict"],
            assess_analysis("p", "hermetic", [], LOT, LOT)["verdict"],
            assess_analysis(
                "p",
                "hermetic",
                clean_steps(**{"die-shear-test": {"severity": "construction-weakness"}}),
                LOT,
                LOT,
            )["verdict"],
            assess_analysis(
                "p",
                "hermetic",
                clean_steps(
                    **{"internal-visual-inspection": {"severity": DISQUALIFYING_SEVERITY}}
                ),
                LOT,
                LOT,
            )["verdict"],
        }
        self.assertEqual(seen, set(VERDICTS))

    def test_duplicate_step_declaration_rejected(self):
        with self.assertRaises(ValueError):
            assess_analysis(
                "cots-mux-01",
                "hermetic",
                [
                    {"step": "die-shear-test", "performed": False},
                    {"step": "die-shear-test", "performed": False},
                ],
                LOT,
                LOT,
            )

    def test_empty_part_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_analysis("  ", "hermetic", clean_steps(), LOT, LOT)

    def test_unknown_package_type_rejected(self):
        with self.assertRaises(ValueError):
            assess_analysis("cots-mux-01", "sealed-in-hope", clean_steps(), LOT, LOT)

    def test_non_sequence_step_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_analysis("cots-mux-01", "hermetic", {"step": "die-shear-test"}, LOT, LOT)


if __name__ == "__main__":
    unittest.main()
