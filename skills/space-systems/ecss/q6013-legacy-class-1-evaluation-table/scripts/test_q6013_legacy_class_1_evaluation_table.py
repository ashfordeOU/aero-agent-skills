"""Contract tests for the Table 8-9 legacy evaluation list logic.

The cases follow the workflow one step at a time: context validation, the
soundness of each offered legacy credit, list coverage, the residual
programme that survives the credits, the device allocation it consumes, the
accept-on-zero verdict of each residual group, and the release-or-repeat
disposition. Every credit rule is exercised on both sides, so the record
shows which evidence was taken and which was refused.
"""

import unittest

from q6013_legacy_class_1_evaluation_table_logic import (
    ASSURANCE_CLASSES,
    DEFAULT_VALIDITY_MONTHS,
    HIGHEST_ASSURANCE_CLASS,
    NEVER_CREDITABLE_GROUPS,
    REQUIRED_EVALUATION_GROUPS,
    allocate_devices,
    assess_legacy_evaluation_table,
    credit_decision,
    evaluation_coverage,
    group_verdict,
    residual_programme,
    validate_context,
    validate_evidence,
)

CREDITABLE = "operating-life-evaluation"


def _context(**overrides):
    record = {
        "manufacturer": "reference-maker",
        "site": "fab-site-a",
        "technology": "bipolar-linear",
        "assurance_class": HIGHEST_ASSURANCE_CLASS,
        "devices_available": 120,
    }
    record.update(overrides)
    return record


def _evidence(group=CREDITABLE, **overrides):
    record = {
        "group": group,
        "manufacturer": "reference-maker",
        "site": "fab-site-a",
        "technology": "bipolar-linear",
        "assurance_class": HIGHEST_ASSURANCE_CLASS,
        "age_months": 18,
        "report": "legacy-report-001",
    }
    record.update(overrides)
    return record


def _entry(group, devices=8, failures=0, **extra):
    record = {"group": group, "devices": devices, "failures": failures}
    record.update(extra)
    return record


def _full_list(**per_group):
    return [_entry(group, **per_group.get(group, {})) for group in REQUIRED_EVALUATION_GROUPS]


def _spec(**overrides):
    spec = {"context": _context(), "entries": _full_list(), "evidence": []}
    spec.update(overrides)
    return spec


class ContextValidationTests(unittest.TestCase):
    def test_valid_context_is_returned_with_a_default_window(self):
        ctx = validate_context(_context())
        self.assertEqual(ctx["validity_months"], DEFAULT_VALIDITY_MONTHS)
        self.assertEqual(ctx["assurance_class"], HIGHEST_ASSURANCE_CLASS)

    def test_declared_window_overrides_the_default(self):
        ctx = validate_context(_context(validity_months=24))
        self.assertEqual(ctx["validity_months"], 24)

    def test_missing_context_key_rejected(self):
        broken = _context()
        del broken["site"]
        with self.assertRaises(ValueError):
            validate_context(broken)

    def test_blank_manufacturer_rejected(self):
        with self.assertRaises(ValueError):
            validate_context(_context(manufacturer="   "))

    def test_zero_devices_available_rejected(self):
        with self.assertRaises(ValueError):
            validate_context(_context(devices_available=0))

    def test_unknown_assurance_class_rejected(self):
        with self.assertRaises(ValueError):
            validate_context(_context(assurance_class=9))

    def test_every_known_assurance_class_is_accepted(self):
        for value in ASSURANCE_CLASSES:
            self.assertEqual(
                validate_context(_context(assurance_class=value))["assurance_class"], value
            )


class EvidenceValidationTests(unittest.TestCase):
    def test_valid_evidence_is_returned(self):
        record = validate_evidence(_evidence())
        self.assertEqual(record["report"], "legacy-report-001")

    def test_missing_report_reference_rejected(self):
        broken = _evidence()
        del broken["report"]
        with self.assertRaises(ValueError):
            validate_evidence(broken)

    def test_negative_age_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(_evidence(age_months=-2))

    def test_non_mapping_evidence_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence("legacy-report-001")


class CreditDecisionTests(unittest.TestCase):
    def test_matching_recent_evidence_is_credited(self):
        decision = credit_decision(_evidence(), _context())
        self.assertTrue(decision["credited"])
        self.assertEqual(decision["reasons"], [])

    def test_evidence_at_the_window_edge_is_still_credited(self):
        decision = credit_decision(
            _evidence(age_months=DEFAULT_VALIDITY_MONTHS), _context()
        )
        self.assertTrue(decision["credited"])

    def test_evidence_past_the_window_is_refused(self):
        decision = credit_decision(
            _evidence(age_months=DEFAULT_VALIDITY_MONTHS + 1), _context()
        )
        self.assertFalse(decision["credited"])

    def test_evidence_from_another_site_is_refused(self):
        decision = credit_decision(_evidence(site="fab-site-b"), _context())
        self.assertFalse(decision["credited"])

    def test_evidence_from_another_manufacturer_is_refused(self):
        decision = credit_decision(_evidence(manufacturer="other-maker"), _context())
        self.assertFalse(decision["credited"])

    def test_evidence_from_another_technology_is_refused(self):
        decision = credit_decision(_evidence(technology="cmos-digital"), _context())
        self.assertFalse(decision["credited"])

    def test_evidence_from_a_lower_class_cannot_be_credited_upwards(self):
        decision = credit_decision(_evidence(assurance_class=3), _context())
        self.assertFalse(decision["credited"])

    def test_evidence_from_a_higher_class_is_credited_downwards(self):
        decision = credit_decision(
            _evidence(assurance_class=1), _context(assurance_class=2)
        )
        self.assertTrue(decision["credited"])

    def test_a_never_creditable_group_is_refused_however_recent(self):
        for group in NEVER_CREDITABLE_GROUPS:
            decision = credit_decision(_evidence(group=group, age_months=1), _context())
            self.assertFalse(decision["credited"])

    def test_every_failing_rule_is_named_not_just_the_first(self):
        decision = credit_decision(
            _evidence(site="fab-site-b", technology="cmos-digital", age_months=200),
            _context(),
        )
        self.assertGreaterEqual(len(decision["reasons"]), 3)


class CoverageTests(unittest.TestCase):
    def test_full_list_is_complete(self):
        coverage = evaluation_coverage(_full_list())
        self.assertTrue(coverage["complete"])

    def test_missing_group_is_named(self):
        entries = [e for e in _full_list() if e["group"] != "radiation-capability"]
        coverage = evaluation_coverage(entries)
        self.assertIn("radiation-capability", coverage["missing"])

    def test_duplicated_group_is_named(self):
        entries = _full_list() + [_entry("mechanical-sequence")]
        coverage = evaluation_coverage(entries)
        self.assertEqual(coverage["duplicated"], ["mechanical-sequence"])

    def test_unrecognized_group_does_not_block_coverage(self):
        entries = _full_list() + [_entry("acoustic-noise-survey")]
        coverage = evaluation_coverage(entries)
        self.assertEqual(coverage["unrecognized"], ["acoustic-noise-survey"])
        self.assertTrue(coverage["complete"])

    def test_empty_list_rejected(self):
        with self.assertRaises(ValueError):
            evaluation_coverage([])


class ResidualProgrammeTests(unittest.TestCase):
    def test_without_evidence_every_declared_group_is_residual(self):
        programme = residual_programme(_full_list(), [], _context())
        self.assertEqual(len(programme["residual"]), len(REQUIRED_EVALUATION_GROUPS))

    def test_a_sound_credit_removes_its_group_from_the_residual(self):
        programme = residual_programme(_full_list(), [_evidence()], _context())
        self.assertIn(CREDITABLE, programme["credited"])
        self.assertNotIn(CREDITABLE, programme["residual"])

    def test_a_refused_credit_leaves_its_group_residual(self):
        programme = residual_programme(
            _full_list(), [_evidence(site="fab-site-b")], _context()
        )
        self.assertIn(CREDITABLE, programme["residual"])
        self.assertIn(CREDITABLE, programme["credit_refused"])

    def test_evidence_for_an_undeclared_group_is_reported_as_orphan(self):
        programme = residual_programme(
            _full_list(), [_evidence(group="acoustic-noise-survey")], _context()
        )
        self.assertEqual(programme["orphan_evidence"], ["acoustic-noise-survey"])

    def test_non_sequence_evidence_rejected(self):
        with self.assertRaises(ValueError):
            residual_programme(_full_list(), "legacy-report-001", _context())


class AllocationTests(unittest.TestCase):
    def test_residual_groups_consume_their_declared_devices(self):
        entries = _full_list()
        residual = [e["group"] for e in entries]
        record = allocate_devices(entries, residual, 120)
        self.assertEqual(record["devices_consumed"], 8 * len(REQUIRED_EVALUATION_GROUPS))
        self.assertEqual(record["devices_remaining"], 120 - record["devices_consumed"])

    def test_a_credited_group_frees_the_devices_it_would_have_taken(self):
        entries = _full_list()
        residual = [e["group"] for e in entries if e["group"] != CREDITABLE]
        record = allocate_devices(entries, residual, 120)
        self.assertEqual(record["devices_saved_by_credit"], 8)

    def test_an_allocation_larger_than_the_lot_is_refused(self):
        entries = _full_list()
        residual = [e["group"] for e in entries]
        with self.assertRaises(ValueError):
            allocate_devices(entries, residual, 20)

    def test_a_group_without_a_device_count_is_refused(self):
        entries = _full_list()
        del entries[0]["devices"]
        residual = [e["group"] for e in entries]
        with self.assertRaises(ValueError):
            allocate_devices(entries, residual, 120)

    def test_a_residual_group_taking_no_device_is_refused(self):
        entries = _full_list()
        entries[0]["devices"] = 0
        residual = [e["group"] for e in entries]
        with self.assertRaises(ValueError):
            allocate_devices(entries, residual, 120)


class GroupVerdictTests(unittest.TestCase):
    def test_a_clean_group_accepts_on_zero(self):
        record = group_verdict(_entry("extended-burn-in"))
        self.assertTrue(record["accepted"])
        self.assertTrue(record["accept_on_zero"])

    def test_one_failure_fails_an_accept_on_zero_group(self):
        record = group_verdict(_entry("extended-burn-in", failures=1))
        self.assertFalse(record["accepted"])
        self.assertEqual(len(record["findings"]), 1)

    def test_a_declared_accept_number_tolerates_its_failure(self):
        record = group_verdict(_entry("mechanical-sequence", failures=1, accept_number=1))
        self.assertTrue(record["accepted"])
        self.assertFalse(record["accept_on_zero"])

    def test_more_failures_than_devices_rejected(self):
        with self.assertRaises(ValueError):
            group_verdict(_entry("mechanical-sequence", devices=4, failures=6))

    def test_an_accept_number_over_the_device_count_rejected(self):
        with self.assertRaises(ValueError):
            group_verdict(_entry("mechanical-sequence", devices=4, accept_number=6))

    def test_a_group_consuming_no_device_rejected(self):
        with self.assertRaises(ValueError):
            group_verdict(_entry("mechanical-sequence", devices=0))


class AssessmentTests(unittest.TestCase):
    def test_a_complete_clean_list_releases_the_part_type(self):
        result = assess_legacy_evaluation_table(_spec())
        self.assertTrue(result["released"])
        self.assertEqual(result["disposition"], "release")

    def test_a_sound_credit_shortens_the_residual_programme(self):
        result = assess_legacy_evaluation_table(_spec(evidence=[_evidence()]))
        self.assertIn(CREDITABLE, result["credited_groups"])
        self.assertNotIn(CREDITABLE, result["residual_groups"])
        self.assertTrue(result["released"])

    def test_a_refused_credit_is_a_finding_not_a_silent_run(self):
        result = assess_legacy_evaluation_table(
            _spec(evidence=[_evidence(age_months=200)])
        )
        self.assertFalse(result["released"])
        self.assertEqual(result["disposition"], "repeat-evaluation")

    def test_a_failed_residual_group_repeats_the_evaluation(self):
        entries = _full_list(**{"operating-life-evaluation": {"failures": 1}})
        result = assess_legacy_evaluation_table(_spec(entries=entries))
        self.assertEqual(result["failing_groups"], ["operating-life-evaluation"])
        self.assertEqual(result["disposition"], "repeat-evaluation")

    def test_a_credited_group_is_not_judged_on_its_own_failures(self):
        entries = _full_list(**{CREDITABLE: {"failures": 3}})
        result = assess_legacy_evaluation_table(
            _spec(entries=entries, evidence=[_evidence()])
        )
        self.assertEqual(result["failing_groups"], [])
        self.assertTrue(result["released"])

    def test_a_missing_group_repeats_the_evaluation(self):
        entries = [e for e in _full_list() if e["group"] != "radiation-capability"]
        result = assess_legacy_evaluation_table(_spec(entries=entries))
        self.assertFalse(result["released"])

    def test_applying_the_list_below_the_highest_class_is_an_advisory(self):
        result = assess_legacy_evaluation_table(_spec(context=_context(assurance_class=2)))
        self.assertTrue(result["released"])
        self.assertEqual(len(result["advisories"]), 1)

    def test_an_allocation_over_the_lot_is_refused_rather_than_trimmed(self):
        with self.assertRaises(ValueError):
            assess_legacy_evaluation_table(_spec(context=_context(devices_available=10)))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["entries"]
        with self.assertRaises(ValueError):
            assess_legacy_evaluation_table(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_legacy_evaluation_table(["context"])

    def test_the_highest_assurance_class_is_the_lowest_number(self):
        self.assertEqual(HIGHEST_ASSURANCE_CLASS, min(ASSURANCE_CLASSES))


if __name__ == "__main__":
    unittest.main()
