"""Contract tests for the clause 5.2.1 Class 2 selection duty framing logic."""

import unittest

from q6013_class_2_selection_overview_logic import (
    CONDITION_SOURCE,
    COVERAGE_TOLERANCE,
    DEFAULT_MINIMUM_COVERAGE,
    DISPOSITIONS,
    DUTY_CATALOGUE,
    EVIDENCE_STATUSES,
    OWNER_ROLES,
    PROGRAMME_SUBJECT,
    assess_class2_selection_duties,
    coverage_share,
    disposition_of,
    duty_instances,
    validate_evidence,
    validate_part,
    validate_programme_context,
)

FULL_CONTEXT = {
    "radiation-environment-declared": True,
    "mission-beyond-short-duration": True,
    "multi-batch-production": True,
}

BARE_CONTEXT = {
    "radiation-environment-declared": False,
    "mission-beyond-short-duration": False,
    "multi-batch-production": False,
}


def part(reference="P1", heritage=False):
    """Return a candidate part with its part-sourced conditions declared."""
    return {
        "reference": reference,
        "conditions": {"no-qualification-heritage": not heritage},
    }


def evidence(duty, subject, owner=None, status="recorded", **overrides):
    """Return an evidence record for one duty instance."""
    record = {
        "duty": duty,
        "subject": subject,
        "owner": owner or DUTY_CATALOGUE[duty]["owner"],
        "status": status,
    }
    if status == "recorded":
        record["reference"] = "PA-REC-001"
    if status == "waived":
        record["waiver_authority"] = "parts control board"
    record.update(overrides)
    return record


def cover_all(instances):
    """Return recorded evidence for every in-scope duty instance."""
    return [evidence(entry["duty"], entry["subject"]) for entry in instances]


class CatalogueTests(unittest.TestCase):
    def test_every_duty_declares_scope_owner_and_waivability(self):
        for duty, spec in DUTY_CATALOGUE.items():
            self.assertIn(spec["scope"], ("per-part", "per-programme"), duty)
            self.assertIn(spec["owner"], OWNER_ROLES, duty)
            self.assertIsInstance(spec["waivable"], bool)

    def test_every_declared_condition_has_a_source(self):
        for spec in DUTY_CATALOGUE.values():
            if spec["condition"] is not None:
                self.assertIn(spec["condition"], CONDITION_SOURCE)

    def test_condition_sources_are_programme_or_part(self):
        for source in CONDITION_SOURCE.values():
            self.assertIn(source, ("programme", "part"))

    def test_both_scopes_are_actually_used(self):
        scopes = {spec["scope"] for spec in DUTY_CATALOGUE.values()}
        self.assertEqual(scopes, {"per-part", "per-programme"})

    def test_disposition_and_status_vocabularies_are_disjointly_declared(self):
        self.assertIn("covered", DISPOSITIONS)
        self.assertIn("recorded", EVIDENCE_STATUSES)
        self.assertNotIn("recorded", DISPOSITIONS)

    def test_tolerance_is_representation_sized(self):
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)


class ContextValidationTests(unittest.TestCase):
    def test_full_context_is_accepted(self):
        self.assertEqual(validate_programme_context(dict(FULL_CONTEXT)), FULL_CONTEXT)

    def test_undeclared_condition_is_unknown_not_false(self):
        short = dict(FULL_CONTEXT)
        del short["multi-batch-production"]
        with self.assertRaises(ValueError):
            validate_programme_context(short)

    def test_non_boolean_condition_rejected(self):
        bad = dict(FULL_CONTEXT)
        bad["multi-batch-production"] = "yes"
        with self.assertRaises(ValueError):
            validate_programme_context(bad)

    def test_unknown_programme_condition_rejected(self):
        bad = dict(FULL_CONTEXT)
        bad["no-qualification-heritage"] = True
        with self.assertRaises(ValueError):
            validate_programme_context(bad)

    def test_part_without_conditions_rejected(self):
        with self.assertRaises(ValueError):
            validate_part({"reference": "P1"})

    def test_part_named_as_the_programme_rejected(self):
        with self.assertRaises(ValueError):
            validate_part(part(reference=PROGRAMME_SUBJECT))

    def test_blank_part_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_part(part(reference="   "))


class DutyScopingTests(unittest.TestCase):
    def test_conditional_duties_drop_out_when_the_condition_is_false(self):
        instances = duty_instances([part()], dict(BARE_CONTEXT))
        duties = {entry["duty"] for entry in instances}
        self.assertNotIn("radiation-suitability", duties)
        self.assertNotIn("lifetime-assessment", duties)
        self.assertNotIn("obsolescence-continuity", duties)

    def test_unconditional_duties_are_always_in_scope(self):
        instances = duty_instances([part()], dict(BARE_CONTEXT))
        duties = {entry["duty"] for entry in instances}
        self.assertIn("usage-justification", duties)
        self.assertIn("customer-agreement", duties)

    def test_part_sourced_condition_scopes_only_the_part_it_holds_for(self):
        instances = duty_instances(
            [part("P1", heritage=True), part("P2", heritage=False)], dict(BARE_CONTEXT)
        )
        subjects = {
            entry["subject"] for entry in instances if entry["duty"] == "evaluation-plan"
        }
        self.assertEqual(subjects, {"P2"})

    def test_programme_duty_is_instantiated_once_whatever_the_part_count(self):
        instances = duty_instances(
            [part("P1"), part("P2"), part("P3")], dict(FULL_CONTEXT)
        )
        agreements = [
            entry for entry in instances if entry["duty"] == "customer-agreement"
        ]
        self.assertEqual(len(agreements), 1)
        self.assertEqual(agreements[0]["subject"], PROGRAMME_SUBJECT)

    def test_per_part_duties_scale_with_the_part_count(self):
        one = duty_instances([part("P1")], dict(FULL_CONTEXT))
        two = duty_instances([part("P1"), part("P2")], dict(FULL_CONTEXT))
        self.assertEqual(len(one), 8)
        self.assertEqual(len(two), 14)

    def test_duplicate_part_reference_rejected(self):
        with self.assertRaises(ValueError):
            duty_instances([part("P1"), part("P1")], dict(FULL_CONTEXT))

    def test_empty_part_list_rejected(self):
        with self.assertRaises(ValueError):
            duty_instances([], dict(FULL_CONTEXT))


class EvidenceValidationTests(unittest.TestCase):
    def test_well_formed_record_is_normalised(self):
        record = validate_evidence(evidence("usage-justification", "P1"))
        self.assertEqual(record["status"], "recorded")
        self.assertEqual(record["reference"], "PA-REC-001")

    def test_programme_duty_recorded_against_a_part_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(evidence("customer-agreement", "P1"))

    def test_part_duty_recorded_once_for_the_programme_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(evidence("usage-justification", PROGRAMME_SUBJECT))

    def test_recorded_status_without_a_reference_rejected(self):
        bad = evidence("usage-justification", "P1")
        del bad["reference"]
        with self.assertRaises(ValueError):
            validate_evidence(bad)

    def test_waived_status_without_an_authority_rejected(self):
        bad = evidence("derating-declaration", "P1", status="waived")
        del bad["waiver_authority"]
        with self.assertRaises(ValueError):
            validate_evidence(bad)

    def test_unknown_owner_role_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(evidence("usage-justification", "P1", owner="the intern"))

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(evidence("usage-justification", "P1", status="fine"))

    def test_unknown_duty_rejected(self):
        record = evidence("usage-justification", "P1")
        record["duty"] = "colour-preference"
        with self.assertRaises(ValueError):
            validate_evidence(record)


class DispositionTests(unittest.TestCase):
    def setUp(self):
        self.instances = duty_instances([part("P1")], dict(BARE_CONTEXT))
        self.usage = [
            entry for entry in self.instances if entry["duty"] == "usage-justification"
        ][0]
        self.derating = [
            entry for entry in self.instances if entry["duty"] == "derating-declaration"
        ][0]

    def test_absent_evidence_is_absent_not_covered(self):
        self.assertEqual(disposition_of(self.usage, []), "absent")

    def test_recorded_evidence_covers_the_duty(self):
        records = [validate_evidence(evidence("usage-justification", "P1"))]
        self.assertEqual(disposition_of(self.usage, records), "covered")

    def test_wrong_owner_is_mis_owned_not_covered(self):
        records = [
            validate_evidence(
                evidence("usage-justification", "P1", owner="procurement")
            )
        ]
        self.assertEqual(disposition_of(self.usage, records), "mis-owned")

    def test_waiver_on_a_waivable_duty_settles_it(self):
        records = [
            validate_evidence(evidence("derating-declaration", "P1", status="waived"))
        ]
        self.assertEqual(disposition_of(self.derating, records), "waived")

    def test_waiver_on_a_non_waivable_duty_is_invalid(self):
        records = [
            validate_evidence(evidence("usage-justification", "P1", status="waived"))
        ]
        self.assertEqual(disposition_of(self.usage, records), "waiver-invalid")

    def test_open_and_rejected_pass_straight_through(self):
        for status in ("open", "rejected"):
            records = [
                validate_evidence(evidence("usage-justification", "P1", status=status))
            ]
            self.assertEqual(disposition_of(self.usage, records), status)

    def test_duty_recorded_twice_rejected(self):
        records = [
            validate_evidence(evidence("usage-justification", "P1")),
            validate_evidence(evidence("usage-justification", "P1", status="open")),
        ]
        with self.assertRaises(ValueError):
            disposition_of(self.usage, records)


class CoverageShareTests(unittest.TestCase):
    def test_all_settled_is_unity(self):
        self.assertAlmostEqual(coverage_share(["covered", "waived"]), 1.0, places=9)

    def test_none_settled_is_zero(self):
        self.assertAlmostEqual(coverage_share(["absent", "open"]), 0.0, places=9)

    def test_mis_owned_does_not_count_as_settled(self):
        self.assertAlmostEqual(
            coverage_share(["covered", "mis-owned"]), 0.5, places=9
        )

    def test_empty_disposition_list_rejected(self):
        with self.assertRaises(ValueError):
            coverage_share([])

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            coverage_share(["covered", "probably-fine"])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        parts = [part("P1")]
        instances = duty_instances(parts, dict(FULL_CONTEXT))
        spec = {
            "parts": parts,
            "context": dict(FULL_CONTEXT),
            "evidence": cover_all(instances),
        }
        spec.update(overrides)
        return spec

    def test_fully_evidenced_programme_is_selection_ready(self):
        result = assess_class2_selection_duties(self._spec())
        self.assertEqual(result["verdict"], "selection-ready")
        self.assertAlmostEqual(result["coverage_share"], 1.0, places=9)
        self.assertEqual(result["outstanding"], ())

    def test_one_missing_mandatory_duty_blocks_readiness(self):
        spec = self._spec()
        spec["evidence"] = [
            record for record in spec["evidence"] if record["duty"] != "usage-justification"
        ]
        result = assess_class2_selection_duties(spec)
        self.assertEqual(result["verdict"], "not-selection-ready")
        self.assertEqual(result["findings"][0]["severity"], 0)

    def test_one_missing_waivable_duty_leaves_actions_not_a_block(self):
        spec = self._spec()
        spec["evidence"] = [
            record
            for record in spec["evidence"]
            if record["duty"] != "obsolescence-continuity"
        ]
        spec["minimum_coverage"] = 0.5
        result = assess_class2_selection_duties(spec)
        self.assertEqual(result["verdict"], "selection-ready-with-actions")

    def test_coverage_exactly_at_the_minimum_counts_as_met(self):
        spec = self._spec()
        spec["evidence"] = [
            record
            for record in spec["evidence"]
            if record["duty"] != "obsolescence-continuity"
        ]
        spec["minimum_coverage"] = 7.0 / 8.0
        result = assess_class2_selection_duties(spec)
        self.assertAlmostEqual(result["coverage_share"], 7.0 / 8.0, places=9)
        self.assertEqual(result["verdict"], "selection-ready-with-actions")

    def test_evidence_outside_the_scoped_set_is_reported_not_credited(self):
        parts = [part("P1", heritage=True)]
        spec = {
            "parts": parts,
            "context": dict(BARE_CONTEXT),
            "evidence": cover_all(duty_instances(parts, dict(BARE_CONTEXT)))
            + [evidence("evaluation-plan", "P1")],
        }
        result = assess_class2_selection_duties(spec)
        self.assertEqual(result["unmatched_evidence"], ("evaluation-plan/P1",))
        self.assertAlmostEqual(result["coverage_share"], 1.0, places=9)

    def test_instance_count_matches_the_scoped_duties(self):
        result = assess_class2_selection_duties(self._spec())
        self.assertEqual(result["instance_count"], 8)

    def test_bare_context_reduces_the_owed_set(self):
        parts = [part("P1", heritage=True)]
        result = assess_class2_selection_duties(
            {
                "parts": parts,
                "context": dict(BARE_CONTEXT),
                "evidence": cover_all(duty_instances(parts, dict(BARE_CONTEXT))),
            }
        )
        self.assertEqual(result["instance_count"], 4)

    def test_missing_context_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_class2_selection_duties({"parts": [part()]})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_class2_selection_duties(["parts"])

    def test_minimum_coverage_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            assess_class2_selection_duties(self._spec(minimum_coverage=1.5))

    def test_default_minimum_is_the_declared_one(self):
        self.assertAlmostEqual(DEFAULT_MINIMUM_COVERAGE, 0.8, places=9)

    def test_evidence_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            assess_class2_selection_duties(self._spec(evidence={"duty": "x"}))


if __name__ == "__main__":
    unittest.main()
