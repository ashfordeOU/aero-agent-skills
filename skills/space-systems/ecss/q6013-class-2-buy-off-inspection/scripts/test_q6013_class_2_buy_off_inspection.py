"""Contract tests for the clause 5.3.6 intermediate class buy-off logic.

The cases walk the release decision one gate at a time: the delegation record
behind the witness, the evidence set each attendance mode demands, the credit
given to an item carried by reference, the lot-scaled minor allowance, the
date sequence, and the three-way disposition that releases, holds or escalates
a lot. Each gate is exercised on both sides of its limit.
"""

import unittest

from q6013_class_2_buy_off_inspection_logic import (
    BASE_EVIDENCE,
    DOCUMENTARY_COVERAGE_FLOOR,
    MAX_MINOR_ALLOWANCE,
    REFERENCED_CREDIT,
    assess_class_2_buy_off,
    evidence_coverage,
    group_findings,
    minor_allowance,
    normalize_evidence,
    required_evidence,
    sequence_gap,
    validate_delegation,
)

ON_SITE_FULL = {item: "seen" for item in BASE_EVIDENCE}


def _delegation(**overrides):
    record = {
        "delegate": "R. Feld",
        "delegate_organisation": "Independent Survey Group",
        "delegating_organisation": "Prime Contractor",
        "producer_organisation": "Component Maker AG",
        "valid_from": "2026-01-01",
        "valid_to": "2026-12-31",
    }
    record.update(overrides)
    return record


def _spec(**overrides):
    spec = {
        "lot_id": "LOT-5536-A",
        "lot_size": 100,
        "buy_off_date": "2026-06-10",
        "review_completed": "2026-06-01",
        "attendance_mode": "on-site",
        "delegation": _delegation(),
        "evidence": dict(ON_SITE_FULL),
        "findings": [],
    }
    spec.update(overrides)
    return spec


class RequiredEvidenceTests(unittest.TestCase):
    def test_on_site_mode_needs_only_the_base_set(self):
        self.assertEqual(required_evidence("on-site"), tuple(BASE_EVIDENCE))

    def test_documentary_mode_adds_the_substitute_records(self):
        required = required_evidence("documentary")
        self.assertIn("photographic-record-set", required)
        self.assertIn("supplier-release-note", required)
        self.assertEqual(len(required), len(BASE_EVIDENCE) + 2)

    def test_remote_witnessed_mode_adds_the_recording(self):
        self.assertIn("live-witness-recording", required_evidence(" Remote-Witnessed "))

    def test_unknown_attendance_mode_rejected(self):
        with self.assertRaises(ValueError):
            required_evidence("posted-in")

    def test_blank_attendance_mode_rejected(self):
        with self.assertRaises(ValueError):
            required_evidence("   ")


class EvidenceCoverageTests(unittest.TestCase):
    def test_full_direct_pack_is_complete(self):
        result = evidence_coverage(ON_SITE_FULL, "on-site")
        self.assertTrue(result["complete"])
        self.assertAlmostEqual(result["coverage"], 1.0, places=9)

    def test_referenced_item_counts_below_a_seen_item(self):
        evidence = dict(ON_SITE_FULL)
        evidence["screening-report"] = "referenced"
        result = evidence_coverage(
            evidence, "on-site", {"screening-report": "DP-77 issue 3"}
        )
        expected = (len(BASE_EVIDENCE) - 1 + REFERENCED_CREDIT) / len(BASE_EVIDENCE)
        self.assertAlmostEqual(result["coverage"], expected, places=9)
        self.assertEqual(result["referenced"], ["screening-report"])
        self.assertTrue(result["complete"])

    def test_reference_without_a_named_document_counts_as_absent(self):
        evidence = dict(ON_SITE_FULL)
        evidence["screening-report"] = "referenced"
        result = evidence_coverage(evidence, "on-site")
        self.assertEqual(result["unsupported_references"], ["screening-report"])
        self.assertIn("screening-report", result["absent"])
        self.assertFalse(result["complete"])

    def test_item_omitted_entirely_is_absent(self):
        evidence = dict(ON_SITE_FULL)
        del evidence["certificate-of-conformity"]
        result = evidence_coverage(evidence, "on-site")
        self.assertEqual(result["absent"], ["certificate-of-conformity"])

    def test_sequence_of_names_reads_as_all_seen(self):
        result = evidence_coverage(list(BASE_EVIDENCE), "on-site")
        self.assertAlmostEqual(result["coverage"], 1.0, places=9)

    def test_boolean_evidence_values_are_accepted(self):
        record = normalize_evidence({"traceability-records": True, "screening-report": False})
        self.assertEqual(record["traceability-records"], "seen")
        self.assertEqual(record["screening-report"], "absent")

    def test_unknown_evidence_state_rejected(self):
        with self.assertRaises(ValueError):
            normalize_evidence({"screening-report": "promised"})

    def test_blank_evidence_key_rejected(self):
        with self.assertRaises(ValueError):
            normalize_evidence({"  ": "seen"})

    def test_blank_reference_value_rejected(self):
        with self.assertRaises(ValueError):
            evidence_coverage(ON_SITE_FULL, "on-site", {"screening-report": "  "})


class MinorAllowanceTests(unittest.TestCase):
    def test_small_lot_gets_the_base_allowance(self):
        self.assertEqual(minor_allowance(99), 1)

    def test_allowance_scales_with_the_lot(self):
        self.assertEqual(minor_allowance(100), 2)
        self.assertEqual(minor_allowance(400), 3)

    def test_allowance_is_capped(self):
        self.assertEqual(minor_allowance(1000000), MAX_MINOR_ALLOWANCE)

    def test_zero_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            minor_allowance(0)

    def test_boolean_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            minor_allowance(True)

    def test_negative_base_rejected(self):
        with self.assertRaises(ValueError):
            minor_allowance(100, base=-1)


class FindingGroupingTests(unittest.TestCase):
    def test_open_major_blocks(self):
        grouped = group_findings([{"id": "N1", "severity": "major", "state": "open"}], 2)
        self.assertEqual(grouped["open_major"], ["N1"])
        self.assertTrue(grouped["blocking"])

    def test_minors_within_allowance_do_not_block(self):
        items = [
            {"id": "N1", "severity": "minor", "state": "open"},
            {"id": "N2", "severity": "minor", "state": "open"},
        ]
        self.assertFalse(group_findings(items, 2)["blocking"])

    def test_minors_over_allowance_block(self):
        items = [
            {"id": "N1", "severity": "minor", "state": "open"},
            {"id": "N2", "severity": "minor", "state": "open"},
            {"id": "N3", "severity": "minor", "state": "open"},
        ]
        self.assertTrue(group_findings(items, 2)["blocking"])

    def test_waiver_without_a_reference_rejected(self):
        with self.assertRaises(ValueError):
            group_findings([{"id": "N1", "severity": "major", "state": "waived"}], 2)

    def test_waiver_with_a_reference_closes_the_major(self):
        grouped = group_findings(
            [{"id": "N1", "severity": "major", "state": "waived", "waiver_ref": "W-12"}], 2
        )
        self.assertEqual(grouped["waived"], ["N1"])
        self.assertFalse(grouped["blocking"])

    def test_repeated_finding_id_rejected(self):
        items = [
            {"id": "N1", "severity": "minor", "state": "open"},
            {"id": "N1", "severity": "minor", "state": "open"},
        ]
        with self.assertRaises(ValueError):
            group_findings(items, 2)

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            group_findings([{"id": "N1", "severity": "critical", "state": "open"}], 2)

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            group_findings([{"id": "N1", "severity": "minor", "state": "pending"}], 2)


class DelegationTests(unittest.TestCase):
    def test_delegation_in_force_is_credible(self):
        result = validate_delegation(_delegation(), "2026-06-10")
        self.assertTrue(result["in_force"])
        self.assertTrue(result["credible"])

    def test_delegation_expired_before_the_buy_off(self):
        result = validate_delegation(_delegation(valid_to="2026-05-31"), "2026-06-10")
        self.assertFalse(result["in_force"])
        self.assertFalse(result["credible"])

    def test_delegation_starting_on_the_buy_off_day_is_in_force(self):
        self.assertTrue(validate_delegation(_delegation(valid_from="2026-06-10"), "2026-06-10")["in_force"])

    def test_producer_witnessing_its_own_lot_is_self_delegated(self):
        record = _delegation(delegate_organisation="Component Maker AG")
        self.assertTrue(validate_delegation(record, "2026-06-10")["self_delegated"])

    def test_inverted_validity_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_delegation(_delegation(valid_from="2026-12-01", valid_to="2026-01-01"), "2026-06-10")

    def test_missing_delegate_name_rejected(self):
        record = _delegation()
        del record["delegate"]
        with self.assertRaises(ValueError):
            validate_delegation(record, "2026-06-10")

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            validate_delegation(_delegation(valid_to="31/12/2026"), "2026-06-10")


class SequenceTests(unittest.TestCase):
    def test_buy_off_after_the_review_gives_a_positive_gap(self):
        self.assertEqual(sequence_gap("2026-06-01", "2026-06-10"), 9)

    def test_buy_off_before_the_review_gives_a_negative_gap(self):
        self.assertEqual(sequence_gap("2026-06-10", "2026-06-01"), -9)


class DispositionTests(unittest.TestCase):
    def test_clean_on_site_buy_off_releases_the_lot(self):
        result = assess_class_2_buy_off(_spec())
        self.assertEqual(result["disposition"], "release-for-delivery")
        self.assertTrue(result["released"])
        self.assertEqual(result["hold_reasons"], [])

    def test_missing_evidence_holds_at_source(self):
        evidence = dict(ON_SITE_FULL)
        del evidence["screening-report"]
        result = assess_class_2_buy_off(_spec(evidence=evidence))
        self.assertEqual(result["disposition"], "hold-at-source")
        self.assertFalse(result["released"])

    def test_expired_delegation_escalates_rather_than_holds(self):
        spec = _spec(delegation=_delegation(valid_to="2026-05-01"))
        self.assertEqual(
            assess_class_2_buy_off(spec)["disposition"], "escalate-to-witnessed-buy-off"
        )

    def test_self_delegated_witness_escalates(self):
        spec = _spec(delegation=_delegation(delegate_organisation="component maker ag"))
        result = assess_class_2_buy_off(spec)
        self.assertEqual(result["disposition"], "escalate-to-witnessed-buy-off")
        self.assertEqual(len(result["escalation_reasons"]), 1)

    def test_documentary_coverage_at_the_floor_does_not_escalate(self):
        required = required_evidence("documentary")
        evidence = {item: "seen" for item in required[:5]}
        evidence[required[5]] = "referenced"
        result = assess_class_2_buy_off(
            _spec(
                attendance_mode="documentary",
                evidence=evidence,
                data_pack_references={required[5]: "DP-91"},
            )
        )
        self.assertAlmostEqual(
            result["coverage"]["coverage"], DOCUMENTARY_COVERAGE_FLOOR, places=9
        )
        self.assertEqual(result["escalation_reasons"], [])
        self.assertEqual(result["disposition"], "hold-at-source")

    def test_documentary_coverage_below_the_floor_escalates(self):
        required = required_evidence("documentary")
        evidence = {item: "seen" for item in required[:4]}
        result = assess_class_2_buy_off(
            _spec(attendance_mode="documentary", evidence=evidence)
        )
        self.assertEqual(result["disposition"], "escalate-to-witnessed-buy-off")

    def test_buy_off_before_the_review_holds(self):
        result = assess_class_2_buy_off(_spec(review_completed="2026-06-20"))
        self.assertEqual(result["gap_days"], -10)
        self.assertEqual(result["disposition"], "hold-at-source")

    def test_referenced_item_is_reported_as_an_advisory_not_a_hold(self):
        evidence = dict(ON_SITE_FULL)
        evidence["traceability-records"] = "referenced"
        result = assess_class_2_buy_off(
            _spec(evidence=evidence, data_pack_references={"traceability-records": "DP-4"})
        )
        self.assertEqual(result["disposition"], "release-for-delivery")
        self.assertEqual(len(result["advisories"]), 1)

    def test_minor_findings_within_the_lot_scaled_allowance_release(self):
        items = [
            {"id": "N1", "severity": "minor", "state": "open"},
            {"id": "N2", "severity": "minor", "state": "open"},
        ]
        result = assess_class_2_buy_off(_spec(lot_size=100, findings=items))
        self.assertEqual(result["minor_allowance"], 2)
        self.assertEqual(result["disposition"], "release-for-delivery")

    def test_same_minors_hold_a_smaller_lot(self):
        items = [
            {"id": "N1", "severity": "minor", "state": "open"},
            {"id": "N2", "severity": "minor", "state": "open"},
        ]
        result = assess_class_2_buy_off(_spec(lot_size=64, findings=items))
        self.assertEqual(result["minor_allowance"], 1)
        self.assertEqual(result["disposition"], "hold-at-source")

    def test_every_hold_reason_is_reported_together(self):
        evidence = dict(ON_SITE_FULL)
        del evidence["screening-report"]
        items = [{"id": "N1", "severity": "major", "state": "open"}]
        result = assess_class_2_buy_off(
            _spec(evidence=evidence, findings=items, review_completed="2026-07-01")
        )
        self.assertEqual(len(result["hold_reasons"]), 3)

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["delegation"]
        with self.assertRaises(ValueError):
            assess_class_2_buy_off(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_2_buy_off(["not", "a", "mapping"])

    def test_blank_lot_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_2_buy_off(_spec(lot_id="   "))


if __name__ == "__main__":
    unittest.main()
