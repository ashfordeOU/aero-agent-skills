"""Contract test for the ECSS-Q-ST-60C clause 5.2.3.3 Class 2 construction leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q60_class_2_constructional_analysis.py
"""

import unittest

from q60_class_2_constructional_analysis_logic import (
    ANALYSIS_STEPS,
    ANOMALY_GRADES,
    ANOMALY_LOCATIONS,
    BASE_INCIDENCE_SHARE,
    FAMILY_SAMPLE_FLOOR,
    MAJOR_SEVERITY_THRESHOLD,
    MANDATORY_STEPS,
    MINOR_SEVERITY_THRESHOLD,
    OPTIONAL_STEPS,
    SEVERITY_TOLERANCE,
    VERDICTS,
    anomaly_severity,
    assess_anomaly,
    assess_constructional_analysis,
    family_sample_floor,
    grade_anomaly,
    missing_mandatory_steps,
    normalize_samples,
    normalize_steps,
    required_sample_count,
    sample_set_reach,
    step_conformance,
)


def sample(sample_id, lot, date_code, matches=True):
    return {
        "sample_id": sample_id,
        "lot": lot,
        "date_code": date_code,
        "construction_matches_declaration": matches,
    }


def clean_samples():
    """Three samples spanning three lots and three date codes."""
    return [
        sample("s1", "lot-a", "2421"),
        sample("s2", "lot-b", "2428"),
        sample("s3", "lot-c", "2435"),
    ]


def all_steps(**overrides):
    """Every step executed and conforming unless overridden."""
    steps = {
        name: {"executed": True, "conforms": True} for name in ANALYSIS_STEPS
    }
    steps.update(overrides)
    return steps


def clean_case(**overrides):
    case = {
        "part_id": "u17-lm124",
        "part_family": "monolithic-integrated-circuit",
        "declared_lots": ["lot-a", "lot-b", "lot-c"],
        "declared_date_codes": ["2421", "2428", "2435"],
        "samples": clean_samples(),
        "steps": all_steps(),
        "anomalies": [],
    }
    case.update(overrides)
    return case


def run_case(**overrides):
    return assess_constructional_analysis(**clean_case(**overrides))


class SampleSizingTests(unittest.TestCase):
    def test_every_family_has_a_floor_of_at_least_two(self):
        for family, floor in FAMILY_SAMPLE_FLOOR.items():
            self.assertGreaterEqual(floor, 2, family)

    def test_an_unknown_family_is_rejected(self):
        with self.assertRaises(ValueError):
            family_sample_floor("mystery-part")

    def test_the_lot_count_governs_when_it_beats_the_family_floor(self):
        required = required_sample_count(
            "discrete-semiconductor", ["lot-a", "lot-b", "lot-c", "lot-d"]
        )
        self.assertEqual(required, 4)

    def test_the_family_floor_governs_when_it_beats_the_lot_count(self):
        required = required_sample_count("monolithic-integrated-circuit", ["lot-a"])
        self.assertEqual(required, 3)

    def test_repeated_lot_names_do_not_inflate_the_requirement(self):
        required = required_sample_count(
            "discrete-semiconductor", ["lot-a", "lot-a", "lot-a"]
        )
        self.assertEqual(required, 2)

    def test_declaring_no_lot_at_all_is_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_count("passive-component", [])

    def test_a_bare_string_is_not_a_lot_list(self):
        with self.assertRaises(ValueError):
            required_sample_count("passive-component", "lot-a")


class SampleSetTests(unittest.TestCase):
    def test_a_complete_set_reaches_its_declared_population(self):
        reaches, gaps = sample_set_reach(
            clean_samples(), ["lot-a", "lot-b", "lot-c"], ["2421", "2428", "2435"]
        )
        self.assertTrue(reaches)
        self.assertEqual(gaps, [])

    def test_an_unsectioned_lot_is_named_as_a_gap(self):
        reaches, gaps = sample_set_reach(
            clean_samples(), ["lot-a", "lot-b", "lot-c", "lot-d"], ["2421"]
        )
        self.assertFalse(reaches)
        self.assertIn("declared-lot-not-sectioned:lot-d", gaps)

    def test_an_unsectioned_date_code_is_named_separately(self):
        reaches, gaps = sample_set_reach(
            clean_samples(), ["lot-a", "lot-b", "lot-c"], ["2421", "2440"]
        )
        self.assertFalse(reaches)
        self.assertIn("declared-date-code-not-sectioned:2440", gaps)

    def test_every_gap_is_reported_at_once(self):
        reaches, gaps = sample_set_reach(
            [sample("s1", "lot-a", "2421")],
            ["lot-a", "lot-b"],
            ["2421", "2428"],
        )
        self.assertFalse(reaches)
        self.assertEqual(len(gaps), 2)

    def test_duplicate_sample_identifiers_are_rejected(self):
        with self.assertRaises(ValueError):
            normalize_samples([sample("s1", "lot-a", "2421"), sample("s1", "lot-b", "2428")])

    def test_a_sample_without_a_declaration_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_samples([{"sample_id": "s1", "lot": "lot-a", "date_code": "2421"}])

    def test_a_non_mapping_sample_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_samples(["s1"])


class StepTests(unittest.TestCase):
    def test_mandatory_and_optional_steps_do_not_overlap(self):
        self.assertEqual(set(MANDATORY_STEPS) & set(OPTIONAL_STEPS), set())

    def test_a_complete_run_leaves_no_mandatory_step_missing(self):
        self.assertEqual(missing_mandatory_steps(all_steps()), ())

    def test_a_skipped_mandatory_step_is_named(self):
        steps = all_steps(
            **{"metallographic-cross-section": {"executed": False, "conforms": False}}
        )
        self.assertIn("metallographic-cross-section", missing_mandatory_steps(steps))

    def test_a_step_absent_from_the_record_counts_as_not_executed(self):
        steps = all_steps()
        del steps["internal-visual-inspection"]
        self.assertIn("internal-visual-inspection", missing_mandatory_steps(steps))

    def test_a_skipped_optional_step_is_not_a_gap(self):
        steps = all_steps(
            **{"residual-gas-analysis": {"executed": False, "conforms": False}}
        )
        self.assertEqual(missing_mandatory_steps(steps), ())

    def test_conformance_counts_only_the_steps_that_ran(self):
        steps = all_steps(
            **{
                "residual-gas-analysis": {"executed": False, "conforms": False},
                "wire-bond-strength-check": {"executed": True, "conforms": False},
            }
        )
        executed = len(ANALYSIS_STEPS) - 1
        self.assertAlmostEqual(
            step_conformance(steps), float(executed - 1) / float(executed), places=9
        )

    def test_an_analysis_that_never_ran_has_no_conformance(self):
        steps = {name: {"executed": False, "conforms": False} for name in ANALYSIS_STEPS}
        self.assertAlmostEqual(step_conformance(steps), 0.0, places=9)

    def test_a_step_cannot_conform_without_having_been_executed(self):
        with self.assertRaises(ValueError):
            normalize_steps({"external-visual-inspection": {"executed": False, "conforms": True}})

    def test_an_unknown_step_name_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_steps({"had-a-look-at-it": {"executed": True, "conforms": True}})

    def test_a_non_mapping_step_record_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_steps({"external-visual-inspection": True})


class AnomalySeverityTests(unittest.TestCase):
    def test_a_single_occurrence_carries_the_base_share_of_its_barrier(self):
        severity = anomaly_severity("package-hermetic-seal", 1, 1)
        self.assertAlmostEqual(severity, ANOMALY_LOCATIONS["package-hermetic-seal"], places=9)

    def test_a_barrier_found_throughout_the_set_carries_its_whole_weight(self):
        severity = anomaly_severity("die-attach", 4, 4)
        self.assertAlmostEqual(severity, ANOMALY_LOCATIONS["die-attach"], places=9)

    def test_the_base_share_sets_the_floor_for_a_sparse_anomaly(self):
        severity = anomaly_severity("die-metallisation", 1, 1000)
        floor = ANOMALY_LOCATIONS["die-metallisation"] * BASE_INCIDENCE_SHARE
        self.assertGreater(severity, floor)
        self.assertLess(severity, ANOMALY_LOCATIONS["die-metallisation"])

    def test_a_severity_landing_exactly_on_the_major_bound_is_major(self):
        severity = anomaly_severity("package-hermetic-seal", 2, 5)
        self.assertAlmostEqual(severity, MAJOR_SEVERITY_THRESHOLD, places=9)
        self.assertEqual(grade_anomaly(severity), "major")

    def test_a_light_barrier_never_reaches_major_even_across_the_whole_set(self):
        severity = anomaly_severity("internal-cavity-cleanliness", 3, 3)
        self.assertEqual(grade_anomaly(severity), "minor")

    def test_a_sparse_light_barrier_is_only_an_observation(self):
        severity = anomaly_severity("external-termination-finish", 1, 4)
        self.assertEqual(grade_anomaly(severity), "observation")

    def test_spreading_through_the_set_can_lift_a_grade(self):
        sparse = anomaly_severity("die-metallisation", 1, 3)
        wide = anomaly_severity("die-metallisation", 2, 3)
        self.assertEqual(grade_anomaly(sparse), "minor")
        self.assertEqual(grade_anomaly(wide), "major")

    def test_every_grade_name_is_one_the_module_publishes(self):
        self.assertIn(grade_anomaly(1.0), ANOMALY_GRADES)
        self.assertIn(grade_anomaly(0.4), ANOMALY_GRADES)
        self.assertIn(grade_anomaly(0.0), ANOMALY_GRADES)

    def test_the_minor_bound_sits_below_the_major_bound(self):
        self.assertLess(MINOR_SEVERITY_THRESHOLD, MAJOR_SEVERITY_THRESHOLD)

    def test_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(SEVERITY_TOLERANCE, 1e-6)

    def test_an_unknown_barrier_is_rejected(self):
        with self.assertRaises(ValueError):
            anomaly_severity("looked-a-bit-odd", 1, 3)

    def test_an_anomaly_affecting_more_samples_than_exist_is_rejected(self):
        with self.assertRaises(ValueError):
            anomaly_severity("die-attach", 4, 3)

    def test_an_anomaly_affecting_no_sample_is_rejected(self):
        with self.assertRaises(ValueError):
            anomaly_severity("die-attach", 0, 3)

    def test_a_negative_severity_is_rejected_by_the_grader(self):
        with self.assertRaises(ValueError):
            grade_anomaly(-0.1)

    def test_a_non_mapping_anomaly_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_anomaly(["die-attach"], 3)


class VerdictTests(unittest.TestCase):
    def test_a_clean_complete_analysis_is_accepted(self):
        report = run_case()
        self.assertEqual(report["verdict"], "class-2-construction-accepted")
        self.assertTrue(report["analysis_complete"])
        self.assertEqual(report["findings"], [])
        self.assertAlmostEqual(report["step_conformance"], 1.0, places=9)

    def test_a_minor_anomaly_accepts_with_a_limitation(self):
        report = run_case(
            anomalies=[{"location": "internal-cavity-cleanliness", "affected_samples": 3}]
        )
        self.assertEqual(report["verdict"], "class-2-construction-accepted-with-limitation")
        self.assertIn(
            "minor-construction-anomaly", [f["finding"] for f in report["findings"]]
        )

    def test_a_major_anomaly_rejects_the_construction(self):
        report = run_case(
            anomalies=[{"location": "package-hermetic-seal", "affected_samples": 2}]
        )
        self.assertEqual(report["verdict"], "class-2-construction-rejected")

    def test_construction_differing_from_the_declaration_rejects_on_its_own(self):
        samples = clean_samples()
        samples[1]["construction_matches_declaration"] = False
        report = run_case(samples=samples)
        self.assertEqual(report["verdict"], "class-2-construction-rejected")
        self.assertIn(
            "construction-differs-from-declaration",
            [f["finding"] for f in report["findings"]],
        )

    def test_a_declaration_mismatch_outranks_a_perfect_conformance_index(self):
        samples = clean_samples()
        samples[0]["construction_matches_declaration"] = False
        report = run_case(samples=samples)
        self.assertAlmostEqual(report["step_conformance"], 1.0, places=9)
        self.assertEqual(report["verdict"], "class-2-construction-rejected")

    def test_a_skipped_mandatory_step_leaves_the_analysis_incomplete(self):
        report = run_case(
            steps=all_steps(
                **{"metallographic-cross-section": {"executed": False, "conforms": False}}
            )
        )
        self.assertEqual(report["verdict"], "class-2-construction-analysis-incomplete")
        self.assertIn("metallographic-cross-section", report["missing_mandatory_steps"])

    def test_a_set_that_misses_a_declared_lot_leaves_the_analysis_incomplete(self):
        report = run_case(declared_lots=["lot-a", "lot-b", "lot-c", "lot-d"])
        self.assertEqual(report["verdict"], "class-2-construction-analysis-incomplete")
        self.assertFalse(report["sample_set_reaches_declared_population"])

    def test_a_short_sample_set_leaves_the_analysis_incomplete(self):
        report = run_case(
            samples=[sample("s1", "lot-a", "2421"), sample("s2", "lot-b", "2428")],
            declared_lots=["lot-a", "lot-b"],
            declared_date_codes=["2421", "2428"],
        )
        self.assertEqual(report["required_sample_count"], 3)
        self.assertEqual(report["sectioned_sample_count"], 2)
        self.assertEqual(report["verdict"], "class-2-construction-analysis-incomplete")

    def test_a_major_finding_is_conclusive_even_on_an_incomplete_analysis(self):
        report = run_case(
            steps=all_steps(
                **{"internal-visual-inspection": {"executed": False, "conforms": False}}
            ),
            anomalies=[{"location": "die-metallisation", "affected_samples": 3}],
        )
        self.assertFalse(report["analysis_complete"])
        self.assertEqual(report["verdict"], "class-2-construction-rejected")

    def test_every_verdict_name_is_one_the_module_publishes(self):
        self.assertIn(run_case()["verdict"], VERDICTS)
        self.assertIn(
            run_case(
                anomalies=[{"location": "package-hermetic-seal", "affected_samples": 3}]
            )["verdict"],
            VERDICTS,
        )
        self.assertIn(run_case(declared_lots=["lot-a", "lot-z"])["verdict"], VERDICTS)

    def test_an_empty_part_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run_case(part_id="  ")

    def test_an_analysis_with_no_sectioned_sample_is_rejected(self):
        with self.assertRaises(ValueError):
            run_case(samples=[])

    def test_a_non_sequence_anomaly_list_is_rejected(self):
        with self.assertRaises(ValueError):
            run_case(anomalies={"location": "die-attach"})


if __name__ == "__main__":
    unittest.main()
