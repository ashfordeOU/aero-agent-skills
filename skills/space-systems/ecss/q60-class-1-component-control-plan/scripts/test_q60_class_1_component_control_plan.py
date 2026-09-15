"""Contract tests for the clause 4.1.2.2 component control plan.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused maintenance
policy, a plan with no reference or issue, a required chapter absent, a
chapter drafted with no procedure behind it, an issue that has outlived
its revision interval, an event that never reached the plan, an event
that reached it late and a review milestone the plan was never taken
through.
"""

import unittest

from q60_class_1_component_control_plan_logic import (
    ALERT_NOTICE,
    CRITICAL_DESIGN_REVIEW,
    DEFAULT_PLAN_MAINTENANCE_POLICY,
    DERATING_AND_APPLICATION_RULES,
    NONCONFORMANCE_DISPOSITION_CHANGE,
    OBSOLESCENCE_AND_NONCONFORMANCE,
    OBSOLESCENCE_NOTICE,
    PART_SUBSTITUTION_REQUEST,
    PLAN_CHAPTER_COVERAGE_SHORT,
    PLAN_MAINTAINED_FOR_CLASS_ONE,
    PLAN_MILESTONE_OUTSTANDING,
    PLAN_NOT_APPROVED,
    PLAN_NOT_ESTABLISHED,
    PLAN_REVISION_OVERDUE,
    PLAN_TRIGGER_BACKLOG_OPEN,
    PRELIMINARY_DESIGN_REVIEW,
    PROCUREMENT_AND_SOURCE_APPROVAL,
    QUALIFICATION_AND_EVALUATION,
    QUALIFICATION_REVIEW,
    RADIATION_AND_DOSE_BUDGET,
    REQUIRED_PLAN_CHAPTERS,
    SCREENING_AND_LOT_ACCEPTANCE,
    SELECTION_AND_DECLARED_LISTS,
    SUPPLIER_OR_LINE_CHANGE,
    absent_chapters,
    assess_component_control_plan,
    chapter_coverage,
    chapter_is_prepared,
    late_trigger_events,
    marginal_currency_advisory,
    open_trigger_events,
    outstanding_milestones,
    revision_currency,
    revision_is_overdue,
    slowest_incorporated_event,
    trigger_response_days,
    unprepared_chapters,
    validate_chapter_record,
    validate_chapters,
    validate_plan_identity,
    validate_plan_maintenance_policy,
    validate_trigger_event,
    validate_trigger_events,
)


def _policy(**overrides):
    policy = dict(DEFAULT_PLAN_MAINTENANCE_POLICY)
    policy.update(overrides)
    return policy


def _chapters(drafted=None, procedures=None, drop=()):
    drafted_map = drafted or {}
    procedure_map = procedures or {}
    return [
        {
            "chapter": name,
            "drafted": drafted_map.get(name, True),
            "procedure_reference": procedure_map.get(
                name, "CCP-PROC-%02d" % (index + 1)
            ),
        }
        for index, name in enumerate(REQUIRED_PLAN_CHAPTERS)
        if name not in drop
    ]


def _events():
    return [
        {
            "trigger": OBSOLESCENCE_NOTICE,
            "event_reference": "OBS-2201",
            "raised_day": 40.0,
            "incorporated_day": 55.0,
        },
        {
            "trigger": ALERT_NOTICE,
            "event_reference": "ALR-3308",
            "raised_day": 90.0,
            "incorporated_day": 100.0,
        },
        {
            "trigger": PART_SUBSTITUTION_REQUEST,
            "event_reference": "SUB-4417",
            "raised_day": 170.0,
            "incorporated_day": 180.0,
        },
    ]


def _plan(**overrides):
    plan = {
        "plan_reference": "CCP-9021",
        "issue": "issue 4",
        "issue_age_days": 200.0,
        "approved_by_customer": True,
        "chapters": _chapters(),
        "trigger_events": _events(),
        "completed_milestones": [
            PRELIMINARY_DESIGN_REVIEW,
            CRITICAL_DESIGN_REVIEW,
            QUALIFICATION_REVIEW,
        ],
    }
    plan.update(overrides)
    return plan


def _case(**overrides):
    case = {"plan": _plan()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_plan_maintenance_policy(DEFAULT_PLAN_MAINTENANCE_POLICY),
            DEFAULT_PLAN_MAINTENANCE_POLICY,
        )

    def test_chapter_coverage_floor_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_maintenance_policy(_policy(min_chapter_coverage=1.3))

    def test_non_positive_revision_interval_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_maintenance_policy(_policy(max_revision_interval_days=0.0))

    def test_non_positive_response_time_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_maintenance_policy(_policy(max_trigger_response_days=-5.0))

    def test_full_width_currency_band_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_maintenance_policy(_policy(marginal_currency_band=1.0))

    def test_empty_milestone_list_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_maintenance_policy(_policy(required_milestones=()))

    def test_unrecognised_milestone_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_maintenance_policy(
                _policy(required_milestones=("launch-campaign-review",))
            )

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_maintenance_policy(("min_chapter_coverage", 1.0))


class IdentityTests(unittest.TestCase):
    def test_identity_reads_back(self):
        identity = validate_plan_identity(_plan())
        self.assertEqual(identity["plan_reference"], "CCP-9021")
        self.assertAlmostEqual(identity["issue_age_days"], 200.0, places=9)

    def test_negative_issue_age_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_identity(_plan(issue_age_days=-1.0))

    def test_non_boolean_approval_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_identity(_plan(approved_by_customer="pending"))

    def test_non_mapping_plan_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_identity("CCP-9021")


class ChapterTests(unittest.TestCase):
    def test_a_full_plan_covers_every_chapter(self):
        self.assertAlmostEqual(chapter_coverage(_chapters()), 1.0, places=9)

    def test_unrecognised_chapter_refused(self):
        with self.assertRaises(ValueError):
            validate_chapter_record(
                {
                    "chapter": "packaging-and-shipping",
                    "drafted": True,
                    "procedure_reference": "CCP-PROC-99",
                }
            )

    def test_duplicate_chapter_refused(self):
        chapters = _chapters()
        chapters.append(dict(chapters[0]))
        with self.assertRaises(ValueError):
            validate_chapters(chapters)

    def test_a_drafted_chapter_with_no_procedure_is_unprepared(self):
        record = {
            "chapter": RADIATION_AND_DOSE_BUDGET,
            "drafted": True,
            "procedure_reference": "   ",
        }
        self.assertFalse(chapter_is_prepared(record))

    def test_an_undrafted_chapter_is_unprepared(self):
        chapters = _chapters(drafted={SCREENING_AND_LOT_ACCEPTANCE: False})
        self.assertEqual(
            unprepared_chapters(chapters), (SCREENING_AND_LOT_ACCEPTANCE,)
        )

    def test_a_dropped_chapter_is_reported_absent(self):
        chapters = _chapters(drop=(DERATING_AND_APPLICATION_RULES,))
        self.assertEqual(
            absent_chapters(chapters), (DERATING_AND_APPLICATION_RULES,)
        )

    def test_a_contents_page_with_nothing_behind_it_covers_nothing(self):
        procedures = {name: "" for name in REQUIRED_PLAN_CHAPTERS}
        self.assertAlmostEqual(
            chapter_coverage(_chapters(procedures=procedures)), 0.0, places=9
        )

    def test_non_sequence_chapters_refused(self):
        with self.assertRaises(ValueError):
            validate_chapters({"chapter": SELECTION_AND_DECLARED_LISTS})


class CurrencyTests(unittest.TestCase):
    def test_a_fresh_issue_has_used_none_of_its_interval(self):
        self.assertAlmostEqual(revision_currency(0.0), 0.0, places=9)

    def test_currency_is_the_share_of_the_interval_used(self):
        expected = 200.0 / float(
            DEFAULT_PLAN_MAINTENANCE_POLICY["max_revision_interval_days"]
        )
        self.assertAlmostEqual(revision_currency(200.0), expected, places=9)

    def test_an_issue_exactly_on_its_interval_is_still_current(self):
        age = float(
            DEFAULT_PLAN_MAINTENANCE_POLICY["max_revision_interval_days"]
        )
        self.assertAlmostEqual(revision_currency(age), 1.0, places=9)
        self.assertFalse(revision_is_overdue(age))

    def test_an_issue_past_its_interval_is_overdue(self):
        age = (
            float(DEFAULT_PLAN_MAINTENANCE_POLICY["max_revision_interval_days"])
            + 30.0
        )
        self.assertTrue(revision_is_overdue(age))

    def test_negative_age_refused(self):
        with self.assertRaises(ValueError):
            revision_currency(-10.0)

    def test_an_issue_in_the_last_stretch_is_advised_on(self):
        advisory = marginal_currency_advisory(340.0)
        self.assertEqual(len(advisory), 1)

    def test_a_fresh_issue_raises_no_advisory(self):
        self.assertEqual(marginal_currency_advisory(10.0), ())

    def test_an_overdue_issue_raises_no_advisory_because_it_is_a_finding(self):
        self.assertEqual(marginal_currency_advisory(400.0), ())


class TriggerTests(unittest.TestCase):
    def test_an_incorporated_event_reports_the_days_it_took(self):
        days = trigger_response_days(_events()[0], 200.0)
        self.assertAlmostEqual(days, 15.0, places=9)

    def test_an_open_event_reports_the_days_it_has_waited(self):
        event = {
            "trigger": SUPPLIER_OR_LINE_CHANGE,
            "event_reference": "SUP-5501",
            "raised_day": 120.0,
            "incorporated_day": None,
        }
        self.assertAlmostEqual(trigger_response_days(event, 200.0), 80.0, places=9)

    def test_an_event_incorporated_before_it_was_raised_refused(self):
        with self.assertRaises(ValueError):
            validate_trigger_event(
                {
                    "trigger": ALERT_NOTICE,
                    "event_reference": "ALR-9999",
                    "raised_day": 100.0,
                    "incorporated_day": 90.0,
                }
            )

    def test_an_event_with_no_reference_refused(self):
        with self.assertRaises(ValueError):
            validate_trigger_event(
                {
                    "trigger": ALERT_NOTICE,
                    "event_reference": "  ",
                    "raised_day": 100.0,
                    "incorporated_day": 110.0,
                }
            )

    def test_unrecognised_trigger_refused(self):
        with self.assertRaises(ValueError):
            validate_trigger_event(
                {
                    "trigger": "office-move",
                    "event_reference": "MOV-1",
                    "raised_day": 1.0,
                    "incorporated_day": 2.0,
                }
            )

    def test_duplicate_event_reference_refused(self):
        events = _events()
        events.append(dict(events[0]))
        with self.assertRaises(ValueError):
            validate_trigger_events(events)

    def test_a_timely_event_set_leaves_nothing_open_or_late(self):
        self.assertEqual(open_trigger_events(_events(), 200.0), ())
        self.assertEqual(late_trigger_events(_events()), ())

    def test_an_event_landing_exactly_on_the_response_limit_is_not_late(self):
        events = [
            {
                "trigger": NONCONFORMANCE_DISPOSITION_CHANGE,
                "event_reference": "NCR-7702",
                "raised_day": 50.0,
                "incorporated_day": 80.0,
            }
        ]
        self.assertEqual(late_trigger_events(events), ())

    def test_an_event_landing_past_the_limit_is_late(self):
        events = [
            {
                "trigger": NONCONFORMANCE_DISPOSITION_CHANGE,
                "event_reference": "NCR-7703",
                "raised_day": 50.0,
                "incorporated_day": 95.0,
            }
        ]
        self.assertEqual(late_trigger_events(events), ("NCR-7703",))

    def test_an_event_never_incorporated_goes_open(self):
        events = _events() + [
            {
                "trigger": SUPPLIER_OR_LINE_CHANGE,
                "event_reference": "SUP-5502",
                "raised_day": 120.0,
                "incorporated_day": None,
            }
        ]
        self.assertEqual(open_trigger_events(events, 200.0), ("SUP-5502",))

    def test_an_open_event_still_inside_its_response_time_is_not_overdue(self):
        events = [
            {
                "trigger": SUPPLIER_OR_LINE_CHANGE,
                "event_reference": "SUP-5503",
                "raised_day": 190.0,
                "incorporated_day": None,
            }
        ]
        self.assertEqual(open_trigger_events(events, 200.0), ())

    def test_the_slowest_incorporated_event_is_named(self):
        slowest = slowest_incorporated_event(_events())
        self.assertEqual(slowest["event_reference"], "OBS-2201")

    def test_no_incorporated_event_gives_no_slowest(self):
        self.assertIsNone(slowest_incorporated_event([]))


class MilestoneTests(unittest.TestCase):
    def test_a_fully_reviewed_plan_leaves_nothing_outstanding(self):
        self.assertEqual(
            outstanding_milestones(
                [PRELIMINARY_DESIGN_REVIEW, CRITICAL_DESIGN_REVIEW, QUALIFICATION_REVIEW]
            ),
            (),
        )

    def test_a_skipped_milestone_is_reported(self):
        self.assertEqual(
            outstanding_milestones([PRELIMINARY_DESIGN_REVIEW, CRITICAL_DESIGN_REVIEW]),
            (QUALIFICATION_REVIEW,),
        )

    def test_unrecognised_completed_milestone_refused(self):
        with self.assertRaises(ValueError):
            outstanding_milestones(["tea-break-review"])

    def test_non_sequence_completed_milestones_refused(self):
        with self.assertRaises(ValueError):
            outstanding_milestones(PRELIMINARY_DESIGN_REVIEW)


class VerdictTests(unittest.TestCase):
    def test_a_prepared_and_maintained_plan_passes(self):
        result = assess_component_control_plan(_case())
        self.assertEqual(result["verdict"], PLAN_MAINTAINED_FOR_CLASS_ONE)
        self.assertAlmostEqual(result["chapter_coverage"], 1.0, places=9)

    def test_an_absent_plan_is_not_established(self):
        result = assess_component_control_plan({"plan": None})
        self.assertEqual(result["verdict"], PLAN_NOT_ESTABLISHED)

    def test_a_plan_with_no_issue_label_is_not_established(self):
        result = assess_component_control_plan(_case(plan=_plan(issue="   ")))
        self.assertEqual(result["verdict"], PLAN_NOT_ESTABLISHED)

    def test_a_missing_chapter_shortens_the_coverage(self):
        chapters = _chapters(drop=(QUALIFICATION_AND_EVALUATION,))
        result = assess_component_control_plan(_case(plan=_plan(chapters=chapters)))
        self.assertEqual(result["verdict"], PLAN_CHAPTER_COVERAGE_SHORT)
        self.assertEqual(
            result["absent_chapters"], (QUALIFICATION_AND_EVALUATION,)
        )

    def test_a_heading_with_nothing_behind_it_shortens_the_coverage(self):
        chapters = _chapters(procedures={PROCUREMENT_AND_SOURCE_APPROVAL: ""})
        result = assess_component_control_plan(_case(plan=_plan(chapters=chapters)))
        self.assertEqual(result["verdict"], PLAN_CHAPTER_COVERAGE_SHORT)
        self.assertEqual(
            result["unprepared_chapters"], (PROCUREMENT_AND_SOURCE_APPROVAL,)
        )

    def test_an_unapproved_plan_is_a_draft(self):
        result = assess_component_control_plan(
            _case(plan=_plan(approved_by_customer=False))
        )
        self.assertEqual(result["verdict"], PLAN_NOT_APPROVED)

    def test_an_issue_past_its_interval_stops_the_assessment(self):
        result = assess_component_control_plan(_case(plan=_plan(issue_age_days=500.0)))
        self.assertEqual(result["verdict"], PLAN_REVISION_OVERDUE)

    def test_an_open_trigger_backlog_stops_the_assessment(self):
        events = _events() + [
            {
                "trigger": OBSOLESCENCE_NOTICE,
                "event_reference": "OBS-2299",
                "raised_day": 60.0,
                "incorporated_day": None,
            }
        ]
        result = assess_component_control_plan(
            _case(plan=_plan(trigger_events=events))
        )
        self.assertEqual(result["verdict"], PLAN_TRIGGER_BACKLOG_OPEN)
        self.assertEqual(result["open_trigger_events"], ("OBS-2299",))

    def test_a_skipped_milestone_stops_the_assessment(self):
        result = assess_component_control_plan(
            _case(
                plan=_plan(
                    completed_milestones=[
                        PRELIMINARY_DESIGN_REVIEW,
                        CRITICAL_DESIGN_REVIEW,
                    ]
                )
            )
        )
        self.assertEqual(result["verdict"], PLAN_MILESTONE_OUTSTANDING)
        self.assertEqual(result["outstanding_milestones"], (QUALIFICATION_REVIEW,))

    def test_a_late_event_is_a_finding_that_travels_with_a_pass(self):
        events = [
            {
                "trigger": OBSOLESCENCE_NOTICE,
                "event_reference": "OBS-2250",
                "raised_day": 40.0,
                "incorporated_day": 130.0,
            }
        ]
        result = assess_component_control_plan(
            _case(plan=_plan(trigger_events=events))
        )
        self.assertEqual(result["verdict"], PLAN_MAINTAINED_FOR_CLASS_ONE)
        self.assertEqual(result["late_trigger_events"], ("OBS-2250",))
        self.assertTrue(result["findings"])

    def test_advisories_travel_with_a_passing_verdict(self):
        result = assess_component_control_plan(_case(plan=_plan(issue_age_days=340.0)))
        self.assertEqual(result["verdict"], PLAN_MAINTAINED_FOR_CLASS_ONE)
        self.assertEqual(len(result["advisories"]), 1)

    def test_the_slowest_incorporation_is_reported(self):
        result = assess_component_control_plan(_case())
        self.assertEqual(result["slowest_incorporated_event"], "OBS-2201")
        self.assertAlmostEqual(
            result["slowest_incorporation_days"], 15.0, places=9
        )

    def test_a_plan_with_no_chapters_sequence_refused(self):
        plan = _plan()
        del plan["chapters"]
        with self.assertRaises(ValueError):
            assess_component_control_plan(_case(plan=plan))

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_component_control_plan(["plan"])

    def test_a_plan_with_no_trigger_events_is_still_assessable(self):
        plan = _plan(trigger_events=[])
        result = assess_component_control_plan(_case(plan=plan))
        self.assertEqual(result["verdict"], PLAN_MAINTAINED_FOR_CLASS_ONE)
        self.assertIsNone(result["slowest_incorporated_event"])


if __name__ == "__main__":
    unittest.main()
