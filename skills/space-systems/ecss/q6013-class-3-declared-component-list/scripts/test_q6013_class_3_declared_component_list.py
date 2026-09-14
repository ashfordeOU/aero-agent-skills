"""Contract tests for the clause 6.1.4 list issue and upkeep decision.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused upkeep
policy, an absent or unidentified list, a first issue later than the
milestone it was meant to inform, a list past its re-issue interval, a
retired line still carrying an installed quantity, a stale line dragging
the quantity-weighted currency share under its floor, and an alert left
open on an installed part.
"""

import unittest

from q6013_class_3_declared_component_list_logic import (
    ACCEPTANCE_REVIEW,
    ACTIVE_LINE_STATUSES,
    CRITICAL_DESIGN_REVIEW,
    DEFAULT_UPKEEP_POLICY,
    ISSUE_MILESTONE_MISSED,
    ISSUE_STALE,
    LINE_APPROVED,
    LINE_APPROVED_WITH_WAIVER,
    LINE_PROPOSED,
    LINE_SUPERSEDED,
    LINE_UPKEEP_SHORT,
    LINE_WITHDRAWN,
    LIST_MAINTAINED,
    LIST_NOT_ISSUED,
    MILESTONE_ORDER,
    OPEN_ALERT_NOT_DISPOSITIONED,
    PRELIMINARY_DESIGN_REVIEW,
    QUALIFICATION_REVIEW,
    RETIRED_LINE_STILL_INSTALLED,
    assess_declared_component_list,
    current_quantity_share,
    installed_active_quantity,
    issue_age_days,
    line_age_days,
    marginal_age_advisories,
    milestone_rank,
    open_alert_lines,
    retired_lines_still_installed,
    stale_lines,
    validate_line_record,
    validate_lines,
    validate_list_identity,
    validate_upkeep_policy,
)

AS_OF = 2000


def _policy(**overrides):
    policy = dict(DEFAULT_UPKEEP_POLICY)
    policy.update(overrides)
    return policy


def _line(part, **overrides):
    line = {
        "part_reference": part,
        "line_status": LINE_APPROVED,
        "last_confirmed_day": AS_OF - 100,
        "installed_quantity": 10,
        "open_alert": False,
    }
    line.update(overrides)
    return line


def _lines():
    return [
        _line("RES-0402-10K", installed_quantity=400),
        _line("CAP-0603-1U", installed_quantity=200),
        _line("CONN-D38-15P", installed_quantity=8, line_status=LINE_APPROVED_WITH_WAIVER),
        _line("REG-LDO-3V3", installed_quantity=4, line_status=LINE_PROPOSED),
    ]


def _declared_list(**overrides):
    declared = {
        "list_reference": "DCL3-0042",
        "issue": "issue 2",
        "first_issue_milestone": CRITICAL_DESIGN_REVIEW,
        "last_issue_day": AS_OF - 60,
        "lines": _lines(),
    }
    declared.update(overrides)
    return declared


def _case(**overrides):
    case = {"declared_list": _declared_list(), "as_of_day": AS_OF}
    case.update(overrides)
    return case


class UpkeepPolicyValidation(unittest.TestCase):
    def test_default_policy_accepted(self):
        self.assertIs(
            validate_upkeep_policy(DEFAULT_UPKEEP_POLICY), DEFAULT_UPKEEP_POLICY
        )

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_upkeep_policy("max_line_age_days")

    def test_unrecognised_required_milestone_refused(self):
        with self.assertRaises(ValueError):
            validate_upkeep_policy(_policy(required_issue_milestone="kickoff"))

    def test_zero_issue_interval_refused(self):
        with self.assertRaises(ValueError):
            validate_upkeep_policy(_policy(max_issue_age_days=0))

    def test_zero_line_interval_refused(self):
        with self.assertRaises(ValueError):
            validate_upkeep_policy(_policy(max_line_age_days=0))

    def test_marginal_band_wider_than_line_interval_refused(self):
        with self.assertRaises(ValueError):
            validate_upkeep_policy(
                _policy(max_line_age_days=90, marginal_age_band_days=120)
            )

    def test_currency_floor_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_upkeep_policy(_policy(min_current_quantity_share=1.2))


class IdentityAndMilestones(unittest.TestCase):
    def test_milestone_rank_follows_the_sequence(self):
        self.assertEqual(milestone_rank(PRELIMINARY_DESIGN_REVIEW), 0)
        self.assertEqual(milestone_rank(ACCEPTANCE_REVIEW), len(MILESTONE_ORDER) - 1)

    def test_unrecognised_milestone_rank_refused(self):
        with self.assertRaises(ValueError):
            milestone_rank("tea-break")

    def test_identity_reads_reference_and_issue(self):
        identity = validate_list_identity(_declared_list())
        self.assertEqual(identity["list_reference"], "DCL3-0042")
        self.assertEqual(identity["first_issue_milestone"], CRITICAL_DESIGN_REVIEW)

    def test_unrecognised_first_issue_milestone_refused(self):
        with self.assertRaises(ValueError):
            validate_list_identity(_declared_list(first_issue_milestone="somewhere"))

    def test_issue_age_is_the_day_difference(self):
        self.assertEqual(issue_age_days(_declared_list(), AS_OF), 60)

    def test_issue_after_the_assessment_day_refused(self):
        with self.assertRaises(ValueError):
            issue_age_days(_declared_list(last_issue_day=AS_OF + 5), AS_OF)


class LineValidation(unittest.TestCase):
    def test_blank_part_reference_refused(self):
        with self.assertRaises(ValueError):
            validate_line_record(_line("  "))

    def test_unrecognised_line_status_refused(self):
        with self.assertRaises(ValueError):
            validate_line_record(_line("RES-1", line_status="maybe"))

    def test_negative_installed_quantity_refused(self):
        with self.assertRaises(ValueError):
            validate_line_record(_line("RES-1", installed_quantity=-2))

    def test_duplicate_part_reference_refused(self):
        with self.assertRaises(ValueError):
            validate_lines([_line("RES-1"), _line("RES-1")])

    def test_empty_line_sequence_refused(self):
        with self.assertRaises(ValueError):
            validate_lines([])

    def test_line_confirmed_after_the_assessment_day_refused(self):
        with self.assertRaises(ValueError):
            line_age_days(_line("RES-1", last_confirmed_day=AS_OF + 1), AS_OF)

    def test_line_age_is_the_day_difference(self):
        self.assertEqual(line_age_days(_line("RES-1"), AS_OF), 100)


class UpkeepArithmetic(unittest.TestCase):
    def test_installed_active_quantity_ignores_retired_lines(self):
        lines = _lines() + [
            _line("OLD-PART", line_status=LINE_SUPERSEDED, installed_quantity=0)
        ]
        self.assertEqual(installed_active_quantity(lines), 612)

    def test_a_fresh_list_is_fully_current(self):
        self.assertAlmostEqual(
            current_quantity_share(_lines(), AS_OF, _policy()), 1.0, places=9
        )
        self.assertEqual(stale_lines(_lines(), AS_OF, _policy()), ())

    def test_currency_is_weighted_by_installed_quantity(self):
        lines = _lines()
        lines[0]["last_confirmed_day"] = AS_OF - 500
        share = current_quantity_share(lines, AS_OF, _policy(max_line_age_days=365))
        self.assertAlmostEqual(share, 212.0 / 612.0, places=9)
        self.assertEqual(
            stale_lines(lines, AS_OF, _policy(max_line_age_days=365)),
            ("RES-0402-10K",),
        )

    def test_a_line_exactly_on_the_interval_is_current(self):
        lines = _lines()
        lines[1]["last_confirmed_day"] = AS_OF - 365
        self.assertEqual(stale_lines(lines, AS_OF, _policy(max_line_age_days=365)), ())

    def test_currency_share_refused_when_nothing_is_installed(self):
        lines = [_line("SPARE-1", installed_quantity=0)]
        with self.assertRaises(ValueError):
            current_quantity_share(lines, AS_OF, _policy())

    def test_retired_line_with_quantity_is_named(self):
        lines = _lines() + [
            _line("OBS-PART", line_status=LINE_WITHDRAWN, installed_quantity=3)
        ]
        self.assertEqual(retired_lines_still_installed(lines), ("OBS-PART",))

    def test_retired_line_with_no_quantity_is_not_named(self):
        lines = _lines() + [
            _line("OBS-PART", line_status=LINE_SUPERSEDED, installed_quantity=0)
        ]
        self.assertEqual(retired_lines_still_installed(lines), ())

    def test_open_alert_lines_are_named(self):
        lines = _lines()
        lines[2]["open_alert"] = True
        self.assertEqual(open_alert_lines(lines), ("CONN-D38-15P",))

    def test_active_statuses_cover_the_live_line_states(self):
        self.assertIn(LINE_PROPOSED, ACTIVE_LINE_STATUSES)
        self.assertIn(LINE_APPROVED_WITH_WAIVER, ACTIVE_LINE_STATUSES)
        self.assertNotIn(LINE_SUPERSEDED, ACTIVE_LINE_STATUSES)


class MarginalAdvisories(unittest.TestCase):
    def test_a_comfortable_list_raises_nothing(self):
        self.assertEqual(
            marginal_age_advisories(_declared_list(), _lines(), AS_OF, _policy()), ()
        )

    def test_issue_falling_due_is_advised_on(self):
        advisories = marginal_age_advisories(
            _declared_list(last_issue_day=AS_OF - 160),
            _lines(),
            AS_OF,
            _policy(max_issue_age_days=180, marginal_age_band_days=30),
        )
        self.assertEqual(len(advisories), 1)

    def test_line_falling_due_is_advised_on(self):
        lines = _lines()
        lines[3]["last_confirmed_day"] = AS_OF - 350
        advisories = marginal_age_advisories(
            _declared_list(), lines, AS_OF, _policy(max_line_age_days=365)
        )
        self.assertEqual(len(advisories), 1)
        self.assertIn("REG-LDO-3V3", advisories[0])


class ListVerdicts(unittest.TestCase):
    def test_absent_list_is_not_issued(self):
        result = assess_declared_component_list(_case(declared_list=None))
        self.assertEqual(result["verdict"], LIST_NOT_ISSUED)

    def test_list_without_a_first_issue_milestone_is_not_issued(self):
        result = assess_declared_component_list(
            _case(declared_list=_declared_list(first_issue_milestone=""))
        )
        self.assertEqual(result["verdict"], LIST_NOT_ISSUED)

    def test_first_issue_after_the_required_milestone_is_missed(self):
        result = assess_declared_component_list(
            _case(declared_list=_declared_list(first_issue_milestone=QUALIFICATION_REVIEW)),
            _policy(required_issue_milestone=CRITICAL_DESIGN_REVIEW),
        )
        self.assertEqual(result["verdict"], ISSUE_MILESTONE_MISSED)

    def test_first_issue_before_the_required_milestone_passes(self):
        result = assess_declared_component_list(
            _case(
                declared_list=_declared_list(
                    first_issue_milestone=PRELIMINARY_DESIGN_REVIEW
                )
            ),
            _policy(),
        )
        self.assertEqual(result["verdict"], LIST_MAINTAINED)

    def test_list_past_its_reissue_interval_is_stale(self):
        result = assess_declared_component_list(
            _case(declared_list=_declared_list(last_issue_day=AS_OF - 400)),
            _policy(max_issue_age_days=180),
        )
        self.assertEqual(result["verdict"], ISSUE_STALE)
        self.assertEqual(result["issue_age_days"], 400)

    def test_retired_line_still_installed_is_caught_before_upkeep(self):
        lines = _lines() + [
            _line("OBS-PART", line_status=LINE_SUPERSEDED, installed_quantity=6)
        ]
        result = assess_declared_component_list(
            _case(declared_list=_declared_list(lines=lines)), _policy()
        )
        self.assertEqual(result["verdict"], RETIRED_LINE_STILL_INSTALLED)
        self.assertEqual(result["retired_lines_still_installed"], ("OBS-PART",))

    def test_stale_bulk_line_shortens_upkeep(self):
        lines = _lines()
        lines[0]["last_confirmed_day"] = AS_OF - 500
        result = assess_declared_component_list(
            _case(declared_list=_declared_list(lines=lines)),
            _policy(max_line_age_days=365, min_current_quantity_share=0.95),
        )
        self.assertEqual(result["verdict"], LINE_UPKEEP_SHORT)
        self.assertIn("RES-0402-10K", result["stale_lines"])

    def test_stale_spare_line_inside_the_floor_still_passes(self):
        lines = _lines()
        lines[3]["last_confirmed_day"] = AS_OF - 500
        result = assess_declared_component_list(
            _case(declared_list=_declared_list(lines=lines)),
            _policy(max_line_age_days=365, min_current_quantity_share=0.99),
        )
        self.assertEqual(result["verdict"], LIST_MAINTAINED)
        self.assertIn("REG-LDO-3V3", result["stale_lines"])

    def test_open_alert_is_caught_last(self):
        lines = _lines()
        lines[1]["open_alert"] = True
        result = assess_declared_component_list(
            _case(declared_list=_declared_list(lines=lines)), _policy()
        )
        self.assertEqual(result["verdict"], OPEN_ALERT_NOT_DISPOSITIONED)
        self.assertEqual(result["open_alert_lines"], ("CAP-0603-1U",))

    def test_open_alert_allowed_by_policy_does_not_move_the_verdict(self):
        lines = _lines()
        lines[1]["open_alert"] = True
        result = assess_declared_component_list(
            _case(declared_list=_declared_list(lines=lines)),
            _policy(allow_open_alert_lines=True),
        )
        self.assertEqual(result["verdict"], LIST_MAINTAINED)

    def test_maintained_list_reports_its_numbers(self):
        result = assess_declared_component_list(_case(), _policy())
        self.assertEqual(result["verdict"], LIST_MAINTAINED)
        self.assertAlmostEqual(result["current_quantity_share"], 1.0, places=9)
        self.assertEqual(result["issue_age_days"], 60)

    def test_list_without_a_lines_sequence_refused(self):
        declared = _declared_list()
        del declared["lines"]
        with self.assertRaises(ValueError):
            assess_declared_component_list(_case(declared_list=declared))

    def test_advisories_travel_with_a_passing_verdict(self):
        result = assess_declared_component_list(
            _case(declared_list=_declared_list(last_issue_day=AS_OF - 170)),
            _policy(max_issue_age_days=180, marginal_age_band_days=30),
        )
        self.assertEqual(result["verdict"], LIST_MAINTAINED)
        self.assertEqual(len(result["advisories"]), 1)

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_declared_component_list(["declared_list"])


if __name__ == "__main__":
    unittest.main()
