"""Contract tests for the Annex B reference test-process-sequence logic."""

import unittest

from q2007_test_sequence_logic import (
    MANDATORY_PHASES,
    OPTIONAL_PHASES,
    REFERENCE_SEQUENCE,
    assess_test_sequence,
    coverage_findings,
    critical_reference_path,
    is_mandatory,
    normalise_identifier,
    order_findings,
    phase_windows,
    reference_index,
    validate_plan,
    validate_tailoring,
)


def full_plan(duration=3, omit=(), order=None):
    names = order if order is not None else [n for n, _ in REFERENCE_SEQUENCE]
    return [
        {"phase": name, "duration_days": duration}
        for name in names
        if name not in omit
    ]


def mandatory_plan(duration=2):
    return [{"phase": name, "duration_days": duration} for name in MANDATORY_PHASES]


class NormaliseTests(unittest.TestCase):
    def test_trims_and_lowercases(self):
        self.assertEqual(normalise_identifier(" Pre-Test-Review ", "x"), "pre-test-review")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier(3, "x")


class ReferenceFlowTests(unittest.TestCase):
    def test_reference_indices_are_strictly_increasing(self):
        indices = [reference_index(name) for name, _ in REFERENCE_SEQUENCE]
        self.assertEqual(indices, sorted(indices))
        self.assertEqual(len(set(indices)), len(indices))

    def test_request_precedes_execution(self):
        self.assertLess(reference_index("test-request"), reference_index("test-execution"))

    def test_execution_precedes_close_out(self):
        self.assertLess(
            reference_index("test-execution"), reference_index("test-report-and-close-out")
        )

    def test_unknown_phase_rejected(self):
        with self.assertRaises(ValueError):
            reference_index("coffee-break")

    def test_mandatory_and_optional_partition_the_flow(self):
        self.assertEqual(
            sorted(MANDATORY_PHASES + OPTIONAL_PHASES),
            sorted(name for name, _ in REFERENCE_SEQUENCE),
        )

    def test_incoming_inspection_is_optional(self):
        self.assertFalse(is_mandatory("test-item-incoming-inspection"))

    def test_critical_path_is_the_mandatory_set_in_order(self):
        self.assertEqual(critical_reference_path(), MANDATORY_PHASES)


class PlanValidationTests(unittest.TestCase):
    def test_plan_keeps_the_planner_order(self):
        entries = validate_plan(full_plan())
        self.assertEqual(entries[0]["phase"], "test-request")
        self.assertEqual(entries[0]["position"], 0)

    def test_duplicate_phase_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan([
                {"phase": "test-request", "duration_days": 1},
                {"phase": "Test-Request", "duration_days": 1},
            ])

    def test_unknown_phase_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan([{"phase": "site-visit", "duration_days": 1}])

    def test_zero_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan([{"phase": "test-request", "duration_days": 0}])

    def test_float_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan([{"phase": "test-request", "duration_days": 1.5}])

    def test_empty_plan_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan([])

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan(["test-request"])


class TailoringValidationTests(unittest.TestCase):
    def test_rationale_is_trimmed(self):
        out = validate_tailoring({"post-test-inspection": "  covered by the customer  "})
        self.assertEqual(out["post-test-inspection"], "covered by the customer")

    def test_unknown_phase_rejected(self):
        with self.assertRaises(ValueError):
            validate_tailoring({"site-visit": "none"})

    def test_empty_rationale_rejected(self):
        with self.assertRaises(ValueError):
            validate_tailoring({"post-test-inspection": "   "})

    def test_absent_tailoring_is_empty(self):
        self.assertEqual(validate_tailoring(None), {})


class CoverageTests(unittest.TestCase):
    def test_full_plan_has_no_coverage_finding(self):
        self.assertEqual(coverage_findings(validate_plan(full_plan()), {}), [])

    def test_omitted_mandatory_phase_without_rationale_blocks(self):
        entries = validate_plan(full_plan(omit=("pre-test-review",)))
        findings = coverage_findings(entries, {})
        self.assertEqual(findings[0]["code"], "mandatory-phase-omitted")
        self.assertEqual(findings[0]["severity"], "blocking")

    def test_omitted_mandatory_phase_with_rationale_is_advisory(self):
        entries = validate_plan(full_plan(omit=("pre-test-review",)))
        findings = coverage_findings(entries, {"pre-test-review": "merged into the trr"})
        self.assertEqual(findings[0]["code"], "mandatory-phase-tailored")
        self.assertEqual(findings[0]["severity"], "advisory")

    def test_rationale_for_a_planned_phase_is_reported_as_stale(self):
        entries = validate_plan(full_plan())
        findings = coverage_findings(entries, {"pre-test-review": "not needed"})
        self.assertEqual(findings[0]["code"], "tailoring-rationale-unused")

    def test_omitted_optional_phase_is_not_a_finding(self):
        entries = validate_plan(full_plan(omit=("test-item-return",)))
        self.assertEqual(coverage_findings(entries, {}), [])


class OrderTests(unittest.TestCase):
    def test_reference_order_is_clean(self):
        self.assertEqual(order_findings(validate_plan(full_plan())), [])

    def test_inversion_is_named_as_a_pair(self):
        entries = validate_plan([
            {"phase": "test-execution", "duration_days": 5},
            {"phase": "pre-test-review", "duration_days": 1},
        ])
        findings = order_findings(entries)
        self.assertEqual(findings[0]["code"], "phase-out-of-reference-order")
        self.assertEqual(findings[0]["phase"], "pre-test-review")

    def test_two_inversions_produce_two_findings(self):
        entries = validate_plan([
            {"phase": "test-execution", "duration_days": 5},
            {"phase": "pre-test-review", "duration_days": 1},
            {"phase": "test-request", "duration_days": 1},
        ])
        self.assertEqual(len(order_findings(entries)), 2)

    def test_skipping_optional_phases_is_not_an_inversion(self):
        entries = validate_plan(mandatory_plan())
        self.assertEqual(order_findings(entries), [])


class WindowTests(unittest.TestCase):
    def test_windows_are_contiguous(self):
        windows = phase_windows(validate_plan(mandatory_plan(duration=4)))
        for position in range(1, len(windows)):
            self.assertEqual(windows[position]["start_day"], windows[position - 1]["end_day"])

    def test_campaign_start_day_offsets_every_window(self):
        windows = phase_windows(validate_plan(mandatory_plan(duration=4)), 10)
        self.assertEqual(windows[0]["start_day"], 10)

    def test_negative_start_day_rejected(self):
        with self.assertRaises(ValueError):
            phase_windows(validate_plan(mandatory_plan()), -1)

    def test_non_integer_start_day_rejected(self):
        with self.assertRaises(ValueError):
            phase_windows(validate_plan(mandatory_plan()), 2.5)


class AssessmentTests(unittest.TestCase):
    def test_full_plan_conforms(self):
        result = assess_test_sequence({"plan": full_plan()})
        self.assertEqual(result["decision"], "conforms")
        self.assertAlmostEqual(result["mandatory_coverage"], 1.0, places=9)
        self.assertTrue(result["ordered"])

    def test_total_duration_is_the_sum_of_the_durations(self):
        result = assess_test_sequence({"plan": mandatory_plan(duration=3)})
        self.assertEqual(result["total_duration_days"], 3 * len(MANDATORY_PHASES))

    def test_tailored_plan_conforms_with_tailoring(self):
        result = assess_test_sequence({
            "plan": full_plan(omit=("post-test-inspection", "test-item-incoming-inspection",
                                    "pre-test-review")),
            "tailoring": {"pre-test-review": "covered by the customer readiness review"},
        })
        self.assertEqual(result["decision"], "conforms-with-tailoring")

    def test_untailored_omission_is_non_conforming(self):
        result = assess_test_sequence({"plan": full_plan(omit=("test-data-package",))})
        self.assertEqual(result["decision"], "non-conforming")
        self.assertAlmostEqual(
            result["mandatory_coverage"],
            (len(MANDATORY_PHASES) - 1) / float(len(MANDATORY_PHASES)),
            places=9,
        )

    def test_inverted_plan_is_non_conforming_and_not_ordered(self):
        order = [n for n, _ in REFERENCE_SEQUENCE]
        order[6], order[7] = order[7], order[6]
        result = assess_test_sequence({"plan": full_plan(order=order)})
        self.assertEqual(result["decision"], "non-conforming")
        self.assertFalse(result["ordered"])

    def test_unplanned_optional_phases_are_listed(self):
        result = assess_test_sequence({"plan": mandatory_plan()})
        self.assertEqual(sorted(result["optional_phases_not_planned"]), sorted(OPTIONAL_PHASES))

    def test_missing_plan_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_sequence({"tailoring": {}})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_sequence(["plan"])


if __name__ == "__main__":
    unittest.main(verbosity=0)
