"""Contract test for the q40-applicability-guidelines leaf (stdlib unittest)."""

import unittest

from q40_applicability_guidelines_logic import (
    APPLICABILITY_STATES,
    PHASES,
    REQUIREMENT_GROUPS,
    applicability,
    applicable_groups,
    assess_tailoring_proposal,
    assess_tailoring_set,
    guideline_for,
    validate_context,
    validate_proposal,
)


def proposal(group="hazard-analysis", action="retain",
             product_type="unmanned-orbital-system", phase="phase-c", **kw):
    record = {
        "product_type": product_type,
        "phase": phase,
        "group": group,
        "action": action,
    }
    record.update(kw)
    return record


class TestValidateContext(unittest.TestCase):
    def test_a_known_context_normalises(self):
        self.assertEqual(validate_context("LAUNCH-VEHICLE", "Phase-C"),
                         ("launch-vehicle", "phase-c"))

    def test_an_unknown_product_type_raises(self):
        with self.assertRaises(ValueError):
            validate_context("space-hotel", "phase-c")

    def test_an_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            validate_context("launch-vehicle", "phase-z")

    def test_a_non_string_product_type_raises(self):
        with self.assertRaises(ValueError):
            validate_context(None, "phase-c")

    def test_every_product_type_has_a_guideline_for_every_group(self):
        for product in ("launch-vehicle", "payload-instrument",
                        "ground-segment-equipment"):
            entry = guideline_for(product)
            self.assertEqual(set(entry["from"]), set(REQUIREMENT_GROUPS))


class TestApplicability(unittest.TestCase):
    def test_a_group_before_its_phase_is_not_yet_applicable(self):
        self.assertEqual(
            applicability("launch-vehicle", "phase-0", "safety-verification"),
            "not-yet-applicable")

    def test_a_group_on_its_starting_phase_is_applicable(self):
        self.assertEqual(
            applicability("launch-vehicle", "phase-b", "safety-verification"),
            "applicable")

    def test_a_group_after_its_starting_phase_stays_applicable(self):
        self.assertEqual(
            applicability("launch-vehicle", "phase-e", "safety-verification"),
            "applicable")

    def test_a_group_out_of_scope_stays_out_of_scope_at_every_phase(self):
        states = set(applicability("payload-instrument", phase, "disposal-safety")
                     for phase in PHASES)
        self.assertEqual(states, {"out-of-scope"})

    def test_a_reduced_group_reports_as_reduced_not_as_applicable(self):
        self.assertEqual(
            applicability("ground-segment-equipment", "phase-d",
                          "safety-risk-assessment"),
            "applicable-reduced")

    def test_the_same_group_differs_by_product_type(self):
        self.assertEqual(
            applicability("manned-orbital-system", "phase-0", "hazard-analysis"),
            "applicable")
        self.assertEqual(
            applicability("payload-instrument", "phase-0", "hazard-analysis"),
            "not-yet-applicable")

    def test_an_unknown_group_raises(self):
        with self.assertRaises(ValueError):
            applicability("launch-vehicle", "phase-c", "paperwork-reduction")

    def test_every_state_returned_is_in_the_vocabulary(self):
        for group in REQUIREMENT_GROUPS:
            state = applicability("payload-instrument", "phase-c", group)
            self.assertIn(state, APPLICABILITY_STATES)


class TestApplicableGroups(unittest.TestCase):
    def test_the_grouping_covers_every_requirement_group(self):
        grouped = applicable_groups("launch-vehicle", "phase-c")
        total = sum(len(v) for v in grouped.values())
        self.assertEqual(total, len(REQUIREMENT_GROUPS))

    def test_an_early_phase_leaves_most_groups_not_yet_applicable(self):
        grouped = applicable_groups("payload-instrument", "phase-0")
        self.assertEqual(grouped["applicable"], [])
        self.assertIn("disposal-safety", grouped["out-of-scope"])

    def test_a_late_phase_has_everything_in_scope_biting(self):
        grouped = applicable_groups("launch-vehicle", "phase-e")
        self.assertEqual(grouped["not-yet-applicable"], [])
        self.assertEqual(len(grouped["applicable"]), len(REQUIREMENT_GROUPS))

    def test_the_grouping_keys_are_the_state_vocabulary(self):
        grouped = applicable_groups("reentry-vehicle", "phase-b")
        self.assertEqual(set(grouped), set(APPLICABILITY_STATES))


class TestValidateProposal(unittest.TestCase):
    def test_a_complete_proposal_normalises(self):
        norm = validate_proposal(proposal())
        self.assertEqual(norm["action"], "retain")
        self.assertIsNone(norm["justification"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_proposal("retain everything")

    def test_an_unknown_action_raises(self):
        with self.assertRaises(ValueError):
            validate_proposal(proposal(action="ignore"))

    def test_a_non_boolean_agreement_raises(self):
        with self.assertRaises(ValueError):
            validate_proposal(proposal(customer_agreed="probably"))

    def test_an_empty_justification_raises(self):
        with self.assertRaises(ValueError):
            validate_proposal(proposal(justification="   "))


class TestAssessProposal(unittest.TestCase):
    def test_retaining_an_applicable_group_is_consistent(self):
        report = assess_tailoring_proposal(proposal())
        self.assertTrue(report["consistent_with_guideline"])
        self.assertEqual(report["findings"], [])

    def test_deleting_an_applicable_group_with_no_justification_is_a_finding(self):
        report = assess_tailoring_proposal(proposal(action="delete"))
        self.assertFalse(report["consistent_with_guideline"])
        self.assertTrue(any("no justification recorded" in f for f in report["findings"]))

    def test_an_unagreed_justified_deletion_still_needs_agreement(self):
        report = assess_tailoring_proposal(
            proposal(action="delete", justification="covered by the launcher authority"))
        self.assertTrue(report["needs_customer_agreement"])
        self.assertTrue(any("not agreed" in f for f in report["findings"]))

    def test_an_agreed_justified_deletion_is_carried_in_the_record(self):
        report = assess_tailoring_proposal(
            proposal(action="delete", justification="covered by the launcher authority",
                     customer_agreed=True))
        self.assertTrue(any("carry it in the tailoring record" in f
                            for f in report["findings"]))

    def test_deleting_a_group_that_has_not_started_suggests_deferral(self):
        report = assess_tailoring_proposal(
            proposal(group="operational-safety", phase="phase-a", action="delete"))
        self.assertTrue(report["consistent_with_guideline"])
        self.assertTrue(any("defer would keep it in view" in f for f in report["findings"]))

    def test_retaining_an_out_of_scope_group_is_reported_as_cost(self):
        report = assess_tailoring_proposal(
            proposal(product_type="payload-instrument", group="disposal-safety"))
        self.assertTrue(report["consistent_with_guideline"])
        self.assertTrue(any("cost, not safety" in f for f in report["findings"]))

    def test_tailoring_a_fully_applicable_group_needs_a_justification(self):
        report = assess_tailoring_proposal(proposal(action="tailor"))
        self.assertFalse(report["consistent_with_guideline"])

    def test_tailoring_a_reduced_group_is_consistent(self):
        report = assess_tailoring_proposal(
            proposal(product_type="ground-segment-equipment",
                     group="safety-risk-assessment", phase="phase-d", action="tailor"))
        self.assertTrue(report["consistent_with_guideline"])

    def test_tailoring_an_out_of_scope_group_has_nothing_to_tailor(self):
        report = assess_tailoring_proposal(
            proposal(product_type="payload-instrument", group="disposal-safety",
                     action="tailor"))
        self.assertTrue(any("nothing to" in f for f in report["findings"]))

    def test_deferring_a_biting_group_is_a_finding(self):
        report = assess_tailoring_proposal(proposal(action="defer"))
        self.assertFalse(report["consistent_with_guideline"])

    def test_deferring_a_group_that_has_not_started_is_consistent(self):
        report = assess_tailoring_proposal(
            proposal(group="operational-safety", phase="phase-a", action="defer"))
        self.assertTrue(report["consistent_with_guideline"])
        self.assertEqual(report["findings"], [])


class TestAssessSet(unittest.TestCase):
    def test_a_consistent_set_reports_as_consistent(self):
        rollup = assess_tailoring_set([proposal("hazard-analysis"),
                                       proposal("safety-verification")])
        self.assertEqual(rollup["position"], "tailoring-consistent")
        self.assertAlmostEqual(rollup["consistent_ratio"], 1.0, places=9)

    def test_an_unjustified_deletion_makes_the_set_unsupported(self):
        rollup = assess_tailoring_set([proposal("hazard-analysis"),
                                       proposal("safety-verification", action="delete")])
        self.assertEqual(rollup["position"], "tailoring-unsupported")
        self.assertEqual(rollup["unjustified_groups"], ["safety-verification"])

    def test_a_justified_deletion_only_needs_agreement(self):
        rollup = assess_tailoring_set([
            proposal("hazard-analysis"),
            proposal("safety-verification", action="delete",
                     justification="carried by the hosting programme")])
        self.assertEqual(rollup["position"], "tailoring-needs-agreement")
        self.assertEqual(rollup["arguable_groups"], ["safety-verification"])

    def test_advisory_findings_do_not_change_the_position(self):
        rollup = assess_tailoring_set([
            proposal("hazard-analysis"),
            proposal(product_type="payload-instrument", group="disposal-safety")])
        self.assertEqual(rollup["position"], "tailoring-consistent")
        self.assertEqual(rollup["advisory_groups"], ["disposal-safety"])

    def test_the_consistent_ratio_counts_the_proposals(self):
        rollup = assess_tailoring_set([proposal("hazard-analysis"),
                                       proposal("safety-verification", action="delete")])
        self.assertAlmostEqual(rollup["consistent_ratio"], 0.5, places=9)

    def test_the_same_group_proposed_twice_raises(self):
        with self.assertRaises(ValueError):
            assess_tailoring_set([proposal("hazard-analysis"),
                                  proposal("hazard-analysis", action="delete")])

    def test_an_empty_set_raises(self):
        with self.assertRaises(ValueError):
            assess_tailoring_set([])


if __name__ == "__main__":
    unittest.main()
