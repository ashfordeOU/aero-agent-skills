"""Contract tests for the clause 5.1.1 off-the-shelf plan logic."""

import unittest
from datetime import date

from q2010_plan_logic import (
    DEFAULT_DECISION_LEAD_DAYS,
    DRD_SECTIONS,
    EXCHANGE_KINDS,
    RESPONSIBLE_ROLES,
    assess_ots_plan,
    evaluation_findings,
    interface_findings,
    need_day,
    normalise_identifier,
    parse_day,
    section_findings,
    validate_candidates,
    validate_evaluations,
    validate_interfaces,
    validate_sections,
)


def sections(omit=(), empty=()):
    return [
        {"section": s, "content": "" if s in empty else "drafted text for %s" % s}
        for s in DRD_SECTIONS
        if s not in omit
    ]


def candidates(day="2026-06-01"):
    return [{"candidate": "cand-1", "node": "pcdu", "commitment_day": day}]


def evaluations(day="2026-04-01", responsible="product-assurance-manager",
                candidate="cand-1"):
    return [{
        "evaluation": "eval-1",
        "candidate": candidate,
        "completion_day": day,
        "responsible": responsible,
    }]


def interfaces(parties=("project", "supplier"), candidate="cand-1"):
    return [{
        "interface": "if-1",
        "candidate": candidate,
        "parties": list(parties),
        "exchange": "data",
    }]


def plan(**overrides):
    spec = {
        "sections": sections(),
        "candidates": candidates(),
        "evaluations": evaluations(),
        "interfaces": interfaces(),
    }
    spec.update(overrides)
    return spec


class NormaliseTests(unittest.TestCase):
    def test_trims_and_lowercases(self):
        self.assertEqual(normalise_identifier(" Cand-1 ", "x"), "cand-1")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier(1, "x")

    def test_iso_day_parsed(self):
        self.assertEqual(parse_day("2026-06-01", "x"), date(2026, 6, 1))

    def test_malformed_day_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("2026-13-01", "x")


class NeedDayTests(unittest.TestCase):
    def test_default_lead_is_thirty_days(self):
        self.assertEqual(DEFAULT_DECISION_LEAD_DAYS, 30)

    def test_need_day_steps_back_the_lead(self):
        self.assertEqual(need_day(date(2026, 6, 1), 30), date(2026, 5, 2))

    def test_zero_lead_is_the_commitment_day(self):
        self.assertEqual(need_day(date(2026, 6, 1), 0), date(2026, 6, 1))

    def test_negative_lead_rejected(self):
        with self.assertRaises(ValueError):
            need_day(date(2026, 6, 1), -1)

    def test_non_date_rejected(self):
        with self.assertRaises(ValueError):
            need_day("2026-06-01", 30)


class SectionTests(unittest.TestCase):
    def test_full_draft_has_no_section_finding(self):
        self.assertEqual(section_findings(validate_sections(sections())), [])

    def test_missing_section_is_reported(self):
        drafted = validate_sections(sections(omit=("interfaces",)))
        self.assertEqual(section_findings(drafted)[0]["code"], "drd-section-missing")

    def test_empty_section_is_reported_apart(self):
        drafted = validate_sections(sections(empty=("responsibilities",)))
        self.assertEqual(section_findings(drafted)[0]["code"], "drd-section-empty")

    def test_unknown_section_rejected(self):
        with self.assertRaises(ValueError):
            validate_sections([{"section": "budget", "content": "x"}])

    def test_duplicate_section_rejected(self):
        with self.assertRaises(ValueError):
            validate_sections(sections() + [{"section": "interfaces", "content": "again"}])

    def test_non_string_content_rejected(self):
        with self.assertRaises(ValueError):
            validate_sections([{"section": "interfaces", "content": 7}])


class CandidateTests(unittest.TestCase):
    def test_candidate_is_keyed_with_its_commitment_day(self):
        listed = validate_candidates(candidates())
        self.assertEqual(listed["cand-1"]["commitment_day"], date(2026, 6, 1))

    def test_duplicate_candidate_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidates(candidates() + candidates())

    def test_missing_commitment_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidates([{"candidate": "cand-1", "node": "pcdu"}])


class EvaluationValidationTests(unittest.TestCase):
    def test_every_recognised_role_is_accepted(self):
        for role in RESPONSIBLE_ROLES:
            scheduled = validate_evaluations(evaluations(responsible=role))
            self.assertEqual(scheduled["eval-1"]["responsible"], role)

    def test_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            validate_evaluations(evaluations(responsible="somebody"))

    def test_absent_responsible_is_kept_as_none(self):
        scheduled = validate_evaluations(evaluations(responsible=None))
        self.assertIsNone(scheduled["eval-1"]["responsible"])

    def test_duplicate_evaluation_rejected(self):
        with self.assertRaises(ValueError):
            validate_evaluations(evaluations() + evaluations())

    def test_absent_schedule_is_empty(self):
        self.assertEqual(validate_evaluations(None), {})


class EvaluationGradingTests(unittest.TestCase):
    def test_evaluation_before_the_need_day_is_clean(self):
        listed = validate_candidates(candidates())
        scheduled = validate_evaluations(evaluations("2026-04-01"))
        self.assertEqual(evaluation_findings(listed, scheduled), [])

    def test_evaluation_exactly_on_the_need_day_is_clean(self):
        listed = validate_candidates(candidates())
        scheduled = validate_evaluations(evaluations("2026-05-02"))
        self.assertEqual(evaluation_findings(listed, scheduled), [])

    def test_evaluation_one_day_late_is_reported(self):
        listed = validate_candidates(candidates())
        scheduled = validate_evaluations(evaluations("2026-05-03"))
        codes = [f["code"] for f in evaluation_findings(listed, scheduled)]
        self.assertIn("evaluation-completes-too-late", codes)

    def test_unattributed_evaluation_is_reported(self):
        listed = validate_candidates(candidates())
        scheduled = validate_evaluations(evaluations(responsible=None))
        codes = [f["code"] for f in evaluation_findings(listed, scheduled)]
        self.assertIn("evaluation-without-responsible", codes)

    def test_candidate_with_no_evaluation_is_reported(self):
        listed = validate_candidates(candidates())
        codes = [f["code"] for f in evaluation_findings(listed, {})]
        self.assertIn("candidate-without-evaluation", codes)

    def test_evaluation_of_an_unlisted_candidate_is_reported(self):
        listed = validate_candidates(candidates())
        scheduled = validate_evaluations(evaluations(candidate="cand-9"))
        codes = [f["code"] for f in evaluation_findings(listed, scheduled)]
        self.assertIn("evaluation-for-unlisted-candidate", codes)

    def test_shorter_lead_can_rescue_a_late_evaluation(self):
        listed = validate_candidates(candidates())
        scheduled = validate_evaluations(evaluations("2026-05-20"))
        self.assertEqual(evaluation_findings(listed, scheduled, 5), [])

    def test_non_mapping_schedule_rejected(self):
        with self.assertRaises(ValueError):
            evaluation_findings(validate_candidates(candidates()), [])


class InterfaceTests(unittest.TestCase):
    def test_two_party_interface_is_clean(self):
        listed = validate_candidates(candidates())
        declared = validate_interfaces(interfaces())
        self.assertEqual(interface_findings(listed, declared), [])

    def test_one_sided_interface_is_reported(self):
        listed = validate_candidates(candidates())
        declared = validate_interfaces(interfaces(parties=("project",)))
        codes = [f["code"] for f in interface_findings(listed, declared)]
        self.assertIn("interface-not-two-sided", codes)

    def test_repeated_party_does_not_make_two_sides(self):
        listed = validate_candidates(candidates())
        declared = validate_interfaces(interfaces(parties=("project", "Project")))
        codes = [f["code"] for f in interface_findings(listed, declared)]
        self.assertIn("interface-not-two-sided", codes)

    def test_candidate_without_an_interface_is_advisory(self):
        listed = validate_candidates(candidates())
        findings = interface_findings(listed, {})
        self.assertEqual(findings[0]["code"], "candidate-without-declared-interface")
        self.assertEqual(findings[0]["severity"], "advisory")

    def test_interface_for_an_unlisted_candidate_is_reported(self):
        listed = validate_candidates(candidates())
        declared = validate_interfaces(interfaces(candidate="cand-9"))
        codes = [f["code"] for f in interface_findings(listed, declared)]
        self.assertIn("interface-for-unlisted-candidate", codes)

    def test_unknown_exchange_rejected(self):
        with self.assertRaises(ValueError):
            validate_interfaces([{
                "interface": "if-1", "candidate": "cand-1",
                "parties": ["a", "b"], "exchange": "telepathy",
            }])

    def test_every_declared_exchange_is_accepted(self):
        for kind in EXCHANGE_KINDS:
            declared = validate_interfaces([{
                "interface": "if-1", "candidate": "cand-1",
                "parties": ["a", "b"], "exchange": kind,
            }])
            self.assertEqual(declared["if-1"]["exchange"], kind)

    def test_duplicate_interface_rejected(self):
        with self.assertRaises(ValueError):
            validate_interfaces(interfaces() + interfaces())


class AssessmentTests(unittest.TestCase):
    def test_complete_plan_is_issuable(self):
        result = assess_ots_plan(plan())
        self.assertEqual(result["decision"], "issuable")
        self.assertAlmostEqual(result["section_completeness"], 1.0, places=9)
        self.assertAlmostEqual(result["evaluation_coverage"], 1.0, places=9)

    def test_advisory_only_plan_is_issuable_with_actions(self):
        result = assess_ots_plan(plan(interfaces=[]))
        self.assertEqual(result["decision"], "issuable-with-actions")

    def test_missing_section_makes_the_plan_not_issuable(self):
        result = assess_ots_plan(plan(sections=sections(omit=("responsibilities",))))
        self.assertEqual(result["decision"], "not-issuable")
        self.assertAlmostEqual(
            result["section_completeness"],
            (len(DRD_SECTIONS) - 1) / float(len(DRD_SECTIONS)),
            places=9,
        )

    def test_uncovered_candidate_lowers_the_evaluation_coverage(self):
        spec = plan(candidates=candidates() + [
            {"candidate": "cand-2", "node": "gps-rx", "commitment_day": "2026-06-01"}
        ])
        result = assess_ots_plan(spec)
        self.assertAlmostEqual(result["evaluation_coverage"], 0.5, places=9)
        self.assertEqual(result["decision"], "not-issuable")

    def test_lead_is_carried_into_the_result(self):
        result = assess_ots_plan(plan(lead_days=10))
        self.assertEqual(result["decision_lead_days"], 10)

    def test_negative_lead_rejected(self):
        with self.assertRaises(ValueError):
            assess_ots_plan(plan(lead_days=-1))

    def test_missing_candidates_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_ots_plan({"sections": sections()})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_ots_plan(["sections"])


if __name__ == "__main__":
    unittest.main(verbosity=0)
