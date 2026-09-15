"""Contract test for the ECSS-Q-ST-60C clause 4.2.3.3 construction leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q60_class_1_constructional_analysis.py
"""

import unittest

from q60_class_1_constructional_analysis_logic import (
    ACCEPTANCE_INDEX,
    ANALYSIS_TOLERANCE,
    FAMILY_MINIMUM_SAMPLES,
    INSPECTION_STEP_WEIGHTS,
    LOT_WIDE_SAMPLE_FRACTION,
    MANDATORY_STEPS,
    SEVERITY_CATEGORIES,
    STEP_OUTCOME_CREDIT,
    VERDICTS,
    assess_constructional_analysis,
    assess_step,
    categorize_anomaly,
    conformance_index,
    family_minimum,
    normalize_samples,
    normalize_step,
    outcome_credit,
    required_sample_count,
    sample_coverage,
    step_weight,
)

FAMILY = "monolithic-integrated-circuit"
TOTAL_WEIGHT = sum(INSPECTION_STEP_WEIGHTS.values())
SPARE_STEP = "die-topology-and-marking-review"

DECLARED = {
    "diffusion_lots": ["D-1", "D-2"],
    "assembly_lots": ["A-1"],
    "date_codes": ["2431"],
}


def sample(sample_id, diffusion="D-1", assembly="A-1", date_code="2431"):
    """One cross-sectioned sample and the lots it speaks for."""
    return {
        "sample_id": sample_id,
        "diffusion_lot": diffusion,
        "assembly_lot": assembly,
        "date_code": date_code,
    }


def representative_samples():
    """A sample set that spans every declared lot and date code."""
    return [sample("S-1", diffusion="D-1"), sample("S-2", diffusion="D-2")]


def performed_steps(**outcomes):
    """Every inspection step conforming, with named exceptions."""
    steps = []
    for name in sorted(INSPECTION_STEP_WEIGHTS):
        entry = {"step": name, "outcome": "conforming"}
        if name in outcomes:
            entry.update(outcomes[name])
        steps.append(entry)
    return steps


def anomaly(**overrides):
    """A workmanship observation on a single sample."""
    item = {
        "anomaly_id": "AN-1",
        "outside_declared_construction": False,
        "affects_interconnect_integrity": False,
        "workmanship_only": True,
        "observed_on_samples": 1,
    }
    item.update(overrides)
    return item


class SampleSizeTests(unittest.TestCase):
    def test_every_family_needs_more_than_one_sample(self):
        for family in FAMILY_MINIMUM_SAMPLES:
            self.assertGreaterEqual(family_minimum(family), 2)

    def test_a_hybrid_needs_the_largest_minimum(self):
        self.assertEqual(
            family_minimum("hybrid-microcircuit"), max(FAMILY_MINIMUM_SAMPLES.values())
        )

    def test_the_family_minimum_holds_when_there_is_one_lot_of_each(self):
        self.assertEqual(required_sample_count(FAMILY, 1, 1), FAMILY_MINIMUM_SAMPLES[FAMILY])

    def test_many_diffusion_lots_raise_the_sample_count_above_the_minimum(self):
        self.assertEqual(required_sample_count(FAMILY, 5, 1), 5)

    def test_many_assembly_lots_raise_the_sample_count_too(self):
        self.assertEqual(required_sample_count(FAMILY, 1, 4), 4)

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            family_minimum("space-magic")

    def test_zero_lots_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_count(FAMILY, 0, 1)

    def test_non_integer_lot_count_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_count(FAMILY, 2.5, 1)


class SampleSetTests(unittest.TestCase):
    def test_a_spanning_set_leaves_nothing_uncovered(self):
        self.assertEqual(sample_coverage(representative_samples(), DECLARED), [])

    def test_a_missing_diffusion_lot_is_named(self):
        uncovered = sample_coverage([sample("S-1", diffusion="D-1")], DECLARED)
        self.assertEqual(uncovered, ["diffusion-lot:D-2"])

    def test_a_missing_date_code_is_named_separately(self):
        declared = dict(DECLARED)
        declared["date_codes"] = ["2431", "2502"]
        uncovered = sample_coverage(representative_samples(), declared)
        self.assertEqual(uncovered, ["date-code:2502"])

    def test_duplicate_sample_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalize_samples([sample("S-1"), sample("S-1", diffusion="D-2")])

    def test_a_sample_without_a_lot_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_samples([{"sample_id": "S-1", "assembly_lot": "A-1", "date_code": "2431"}])

    def test_non_sequence_sample_set_rejected(self):
        with self.assertRaises(ValueError):
            normalize_samples(sample("S-1"))

    def test_empty_declared_lot_list_rejected(self):
        declared = dict(DECLARED)
        declared["assembly_lots"] = []
        with self.assertRaises(ValueError):
            sample_coverage(representative_samples(), declared)


class InspectionStepTests(unittest.TestCase):
    def test_every_mandatory_step_is_a_known_step(self):
        for name in MANDATORY_STEPS:
            self.assertIn(name, INSPECTION_STEP_WEIGHTS)

    def test_the_cross_section_carries_the_heaviest_weight(self):
        heaviest = max(INSPECTION_STEP_WEIGHTS.values())
        self.assertAlmostEqual(
            step_weight("metallographic-cross-section-preparation"), heaviest, places=9
        )

    def test_a_conforming_outcome_earns_the_whole_credit(self):
        self.assertAlmostEqual(outcome_credit("conforming"), 1.0, places=9)

    def test_a_major_deviation_earns_nothing(self):
        self.assertAlmostEqual(outcome_credit("major-deviation"), 0.0, places=9)

    def test_a_minor_deviation_earns_part_of_the_credit(self):
        credit = outcome_credit("minor-deviation")
        self.assertGreater(credit, 0.1)
        self.assertLess(credit, 0.9)

    def test_outcome_defaults_to_not_performed(self):
        record = normalize_step({"step": SPARE_STEP})
        self.assertEqual(record["outcome"], "step-not-performed")

    def test_unknown_step_rejected(self):
        with self.assertRaises(ValueError):
            step_weight("hold-it-up-to-the-light")

    def test_unknown_outcome_rejected(self):
        with self.assertRaises(ValueError):
            outcome_credit("looked-fine")

    def test_a_skipped_mandatory_step_is_flagged(self):
        record = assess_step(
            {"step": "internal-visual-inspection", "outcome": "step-not-performed"}
        )
        self.assertTrue(record["mandatory_missing"])
        self.assertIn("mandatory-step-not-performed", record["findings"])

    def test_a_skipped_spare_step_is_not_a_missing_mandatory_step(self):
        record = assess_step({"step": SPARE_STEP, "outcome": "step-not-performed"})
        self.assertFalse(record["mandatory_missing"])
        self.assertIn("step-not-performed", record["findings"])

    def test_index_rejects_an_empty_record_set(self):
        with self.assertRaises(ValueError):
            conformance_index([])

    def test_index_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            conformance_index({"weight": 1.0, "weighted_credit": 1.0})

    def test_the_index_reads_the_acceptance_bound_exactly(self):
        records = [{"weight": 1.0, "weighted_credit": ACCEPTANCE_INDEX}]
        self.assertAlmostEqual(conformance_index(records), ACCEPTANCE_INDEX, places=9)


class AnomalySeverityTests(unittest.TestCase):
    def test_construction_outside_the_declaration_is_critical_on_one_sample(self):
        severity = categorize_anomaly(anomaly(outside_declared_construction=True), 4)
        self.assertEqual(severity, "critical-construction-anomaly")

    def test_an_interconnect_anomaly_across_the_set_is_critical(self):
        severity = categorize_anomaly(
            anomaly(
                affects_interconnect_integrity=True,
                workmanship_only=False,
                observed_on_samples=2,
            ),
            4,
        )
        self.assertAlmostEqual(2.0 / 4.0, LOT_WIDE_SAMPLE_FRACTION, places=9)
        self.assertEqual(severity, "critical-construction-anomaly")

    def test_an_interconnect_anomaly_on_a_minority_is_major(self):
        severity = categorize_anomaly(
            anomaly(
                affects_interconnect_integrity=True,
                workmanship_only=False,
                observed_on_samples=1,
            ),
            4,
        )
        self.assertEqual(severity, "major-construction-anomaly")

    def test_workmanship_on_a_minority_is_minor(self):
        self.assertEqual(
            categorize_anomaly(anomaly(observed_on_samples=1), 4),
            "minor-construction-anomaly",
        )

    def test_workmanship_across_the_set_stops_being_minor(self):
        severity = categorize_anomaly(anomaly(observed_on_samples=3), 4)
        self.assertEqual(severity, "major-construction-anomaly")

    def test_every_severity_name_is_one_the_module_publishes(self):
        seen = {
            categorize_anomaly(anomaly(outside_declared_construction=True), 4),
            categorize_anomaly(
                anomaly(affects_interconnect_integrity=True, workmanship_only=False), 4
            ),
            categorize_anomaly(anomaly(observed_on_samples=1), 4),
        }
        self.assertEqual(seen, set(SEVERITY_CATEGORIES))

    def test_an_anomaly_on_more_samples_than_exist_rejected(self):
        with self.assertRaises(ValueError):
            categorize_anomaly(anomaly(observed_on_samples=5), 4)

    def test_a_non_boolean_anomaly_flag_rejected(self):
        with self.assertRaises(ValueError):
            categorize_anomaly(anomaly(workmanship_only="mostly"), 4)

    def test_a_non_mapping_anomaly_rejected(self):
        with self.assertRaises(ValueError):
            categorize_anomaly("a scratch", 4)


class AnalysisVerdictTests(unittest.TestCase):
    def test_a_clean_analysis_accepts_the_construction(self):
        report = assess_constructional_analysis(
            "dev-01", FAMILY, DECLARED, representative_samples(), performed_steps()
        )
        self.assertEqual(report["verdict"], "construction-acceptable-for-class-1")
        self.assertTrue(report["acceptable_for_class_1"])
        self.assertAlmostEqual(report["conformance_index"], 1.0, places=9)
        self.assertEqual(report["findings"], [])

    def test_a_minor_anomaly_leaves_open_actions(self):
        report = assess_constructional_analysis(
            "dev-01",
            FAMILY,
            DECLARED,
            representative_samples(),
            performed_steps(),
            [anomaly(observed_on_samples=1)],
        )
        self.assertEqual(report["verdict"], "construction-acceptable-with-open-actions")
        self.assertTrue(report["acceptable_for_class_1"])

    def test_a_critical_anomaly_rejects_the_construction(self):
        report = assess_constructional_analysis(
            "dev-01",
            FAMILY,
            DECLARED,
            representative_samples(),
            performed_steps(),
            [anomaly(outside_declared_construction=True)],
        )
        self.assertEqual(report["verdict"], "construction-not-acceptable-for-class-1")
        self.assertFalse(report["acceptable_for_class_1"])

    def test_a_skipped_cross_section_makes_the_analysis_incomplete(self):
        report = assess_constructional_analysis(
            "dev-01",
            FAMILY,
            DECLARED,
            representative_samples(),
            performed_steps(
                **{"metallographic-cross-section-preparation": {"outcome": "step-not-performed"}}
            ),
        )
        self.assertEqual(report["verdict"], "constructional-analysis-incomplete")

    def test_a_sample_set_short_of_the_lots_is_incomplete(self):
        report = assess_constructional_analysis(
            "dev-01", FAMILY, DECLARED, [sample("S-1", diffusion="D-1")], performed_steps()
        )
        self.assertEqual(report["verdict"], "constructional-analysis-incomplete")
        self.assertIn("diffusion-lot:D-2", report["uncovered_declarations"])
        self.assertEqual(report["required_sample_count"], 2)

    def test_one_missing_spare_step_removes_exactly_its_weight(self):
        report = assess_constructional_analysis(
            "dev-01",
            FAMILY,
            DECLARED,
            representative_samples(),
            performed_steps(**{SPARE_STEP: {"outcome": "step-not-performed"}}),
        )
        self.assertAlmostEqual(
            report["conformance_index"] * TOTAL_WEIGHT,
            TOTAL_WEIGHT - INSPECTION_STEP_WEIGHTS[SPARE_STEP],
            places=9,
        )

    def test_an_undeclared_step_is_graded_as_not_performed(self):
        report = assess_constructional_analysis(
            "dev-01", FAMILY, DECLARED, representative_samples(), []
        )
        self.assertEqual(len(report["step_records"]), len(INSPECTION_STEP_WEIGHTS))
        self.assertEqual(report["verdict"], "constructional-analysis-incomplete")

    def test_every_verdict_name_is_one_the_module_publishes(self):
        seen = set()
        seen.add(
            assess_constructional_analysis(
                "p", FAMILY, DECLARED, representative_samples(), performed_steps()
            )["verdict"]
        )
        seen.add(
            assess_constructional_analysis(
                "p",
                FAMILY,
                DECLARED,
                representative_samples(),
                performed_steps(),
                [anomaly()],
            )["verdict"]
        )
        seen.add(
            assess_constructional_analysis(
                "p",
                FAMILY,
                DECLARED,
                representative_samples(),
                performed_steps(),
                [anomaly(outside_declared_construction=True)],
            )["verdict"]
        )
        seen.add(
            assess_constructional_analysis(
                "p", FAMILY, DECLARED, representative_samples(), []
            )["verdict"]
        )
        self.assertEqual(seen, set(VERDICTS))

    def test_duplicate_inspection_step_rejected(self):
        with self.assertRaises(ValueError):
            assess_constructional_analysis(
                "dev-01",
                FAMILY,
                DECLARED,
                representative_samples(),
                [
                    {"step": SPARE_STEP, "outcome": "conforming"},
                    {"step": SPARE_STEP, "outcome": "conforming"},
                ],
            )

    def test_empty_part_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_constructional_analysis(
                "  ", FAMILY, DECLARED, representative_samples(), performed_steps()
            )

    def test_an_empty_sample_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_constructional_analysis(
                "dev-01", FAMILY, DECLARED, [], performed_steps()
            )

    def test_non_sequence_steps_rejected(self):
        with self.assertRaises(ValueError):
            assess_constructional_analysis(
                "dev-01", FAMILY, DECLARED, representative_samples(), {"step": SPARE_STEP}
            )

    def test_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(ANALYSIS_TOLERANCE, 1e-6)

    def test_every_outcome_credit_is_on_the_published_scale(self):
        self.assertAlmostEqual(max(STEP_OUTCOME_CREDIT.values()), 1.0, places=9)
        self.assertAlmostEqual(min(STEP_OUTCOME_CREDIT.values()), 0.0, places=9)


if __name__ == "__main__":
    unittest.main()
