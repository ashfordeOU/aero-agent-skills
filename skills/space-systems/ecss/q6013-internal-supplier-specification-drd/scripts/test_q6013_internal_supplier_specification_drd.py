#!/usr/bin/env python3
"""Contract tests for the Annex C supplier internal specification data item.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused data-item
policy, a specification never offered, one with no reference or issue, a
required clause absent, a clause stated with no text behind it, a clause
reserved to the supplier's discretion, a change-notification duty too
short to react to, and an application demand the declared limits do not
reach.
"""

import unittest

from q6013_internal_supplier_specification_drd_logic import (
    APPLICATION_LIMIT_NOT_COVERED,
    CHANGE_NOTIFICATION_DUTY,
    CHANGE_NOTIFICATION_NOT_BINDING,
    CLAUSE_COVERAGE_SHORT,
    CLAUSE_LEFT_TO_DISCRETION,
    DEFAULT_SPECIFICATION_DRD_POLICY,
    ELECTRICAL_LIMITS_AND_RATINGS,
    LOT_ACCEPTANCE_OPERATIONS,
    MANUFACTURING_SITE_AND_BASELINE,
    MARKING_AND_TRACEABILITY,
    NOT_ABOVE,
    NOT_BELOW,
    REQUIRED_SPECIFICATION_CLAUSES,
    SCREENING_OPERATIONS,
    SPECIFICATION_ACCEPTED,
    SPECIFICATION_NOT_PROVIDED,
    STORAGE_AND_HANDLING,
    absent_clauses,
    assess_internal_supplier_specification_drd,
    change_notice_is_binding,
    clause_coverage,
    clause_index,
    clause_is_controlled,
    discretionary_clauses,
    limit_is_covered,
    limit_margin,
    marginal_limits,
    uncontrolled_clauses,
    uncovered_limits,
    validate_clause_record,
    validate_clauses,
    validate_limit_record,
    validate_limits,
    validate_specification_drd_policy,
    validate_specification_identity,
)


def _policy(**overrides):
    policy = dict(DEFAULT_SPECIFICATION_DRD_POLICY)
    policy.update(overrides)
    return policy


def _clauses(stated=None, texts=None, discretion=None, drop=()):
    stated_map = stated or {}
    text_map = texts or {}
    discretion_map = discretion or {}
    return [
        {
            "clause": name,
            "stated": stated_map.get(name, True),
            "text_reference": text_map.get(name, "SPEC-CL-%02d" % (index + 1)),
            "at_supplier_discretion": discretion_map.get(name, False),
        }
        for index, name in enumerate(REQUIRED_SPECIFICATION_CLAUSES)
        if name not in drop
    ]


def _limits():
    return [
        {
            "parameter": "maximum-junction-temperature-c",
            "direction": NOT_ABOVE,
            "specification_limit": 125.0,
            "application_demand": 96.0,
        },
        {
            "parameter": "minimum-supply-voltage-v",
            "direction": NOT_BELOW,
            "specification_limit": 2.7,
            "application_demand": 3.3,
        },
        {
            "parameter": "maximum-total-ionising-dose-krad",
            "direction": NOT_ABOVE,
            "specification_limit": 30.0,
            "application_demand": 12.0,
        },
    ]


def _specification(**overrides):
    specification = {
        "specification_reference": "SUP-INT-SPEC-7712",
        "issue": "issue B",
        "supplier": "north-line-semiconductors",
        "change_notification_days": 120.0,
        "clauses": _clauses(),
        "declared_limits": _limits(),
    }
    specification.update(overrides)
    return specification


def _case(**overrides):
    case = {"policy": _policy(), "specification": _specification()}
    case.update(overrides)
    return case


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_is_usable(self):
        self.assertIs(
            validate_specification_drd_policy(DEFAULT_SPECIFICATION_DRD_POLICY),
            DEFAULT_SPECIFICATION_DRD_POLICY,
        )

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_specification_drd_policy(("min_clause_coverage",))

    def test_coverage_floor_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_specification_drd_policy(_policy(min_clause_coverage=2.0))

    def test_non_positive_notification_lead_refused(self):
        with self.assertRaises(ValueError):
            validate_specification_drd_policy(_policy(max_change_notification_days=0.0))

    def test_full_width_marginal_band_refused(self):
        with self.assertRaises(ValueError):
            validate_specification_drd_policy(
                _policy(marginal_limit_margin_fraction=1.0)
            )


class IdentityValidationTests(unittest.TestCase):
    def test_identity_is_read_back(self):
        identity = validate_specification_identity(_specification())
        self.assertEqual(identity["specification_reference"], "SUP-INT-SPEC-7712")
        self.assertAlmostEqual(identity["change_notification_days"], 120.0, places=9)

    def test_negative_notification_days_refused(self):
        with self.assertRaises(ValueError):
            validate_specification_identity(
                _specification(change_notification_days=-5.0)
            )

    def test_non_mapping_specification_refused(self):
        with self.assertRaises(ValueError):
            validate_specification_identity("SUP-INT-SPEC-7712")


class ClauseValidationTests(unittest.TestCase):
    def test_unrecognised_clause_refused(self):
        with self.assertRaises(ValueError):
            validate_clause_record({"clause": "colour-of-the-tape", "stated": True})

    def test_duplicate_clause_refused(self):
        clauses = _clauses()
        clauses.append(dict(clauses[0]))
        with self.assertRaises(ValueError):
            validate_clauses(clauses)

    def test_non_boolean_discretion_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_clause_record(
                {
                    "clause": STORAGE_AND_HANDLING,
                    "stated": True,
                    "text_reference": "SPEC-CL-08",
                    "at_supplier_discretion": "sometimes",
                }
            )

    def test_clause_with_no_text_is_uncontrolled(self):
        record = validate_clause_record(
            {
                "clause": MARKING_AND_TRACEABILITY,
                "stated": True,
                "text_reference": "  ",
            }
        )
        self.assertFalse(clause_is_controlled(record))

    def test_clause_index_maps_every_declared_clause(self):
        self.assertEqual(len(clause_index(_clauses())), len(REQUIRED_SPECIFICATION_CLAUSES))


class CoverageTests(unittest.TestCase):
    def test_full_specification_covers_every_clause(self):
        self.assertAlmostEqual(clause_coverage(_clauses()), 1.0, places=9)

    def test_absent_clause_is_named_and_lowers_coverage(self):
        clauses = _clauses(drop=(LOT_ACCEPTANCE_OPERATIONS,))
        self.assertEqual(absent_clauses(clauses), (LOT_ACCEPTANCE_OPERATIONS,))
        self.assertAlmostEqual(
            clause_coverage(clauses),
            (len(REQUIRED_SPECIFICATION_CLAUSES) - 1)
            / float(len(REQUIRED_SPECIFICATION_CLAUSES)),
            places=9,
        )

    def test_unstated_clause_is_named(self):
        clauses = _clauses(stated={SCREENING_OPERATIONS: False})
        self.assertEqual(uncontrolled_clauses(clauses), (SCREENING_OPERATIONS,))

    def test_discretionary_clause_is_named_and_lowers_coverage(self):
        clauses = _clauses(discretion={MANUFACTURING_SITE_AND_BASELINE: True})
        self.assertEqual(
            discretionary_clauses(clauses), (MANUFACTURING_SITE_AND_BASELINE,)
        )
        self.assertAlmostEqual(
            clause_coverage(clauses),
            (len(REQUIRED_SPECIFICATION_CLAUSES) - 1)
            / float(len(REQUIRED_SPECIFICATION_CLAUSES)),
            places=9,
        )


class LimitTests(unittest.TestCase):
    def test_unrecognised_direction_refused(self):
        with self.assertRaises(ValueError):
            validate_limit_record(
                {
                    "parameter": "maximum-current-a",
                    "direction": "around",
                    "specification_limit": 1.0,
                    "application_demand": 0.5,
                }
            )

    def test_unnamed_parameter_refused(self):
        with self.assertRaises(ValueError):
            validate_limit_record(
                {
                    "parameter": "   ",
                    "direction": NOT_ABOVE,
                    "specification_limit": 1.0,
                    "application_demand": 0.5,
                }
            )

    def test_duplicate_parameter_refused(self):
        limits = _limits()
        limits.append(dict(limits[0]))
        with self.assertRaises(ValueError):
            validate_limits(limits)

    def test_not_above_margin_is_the_room_left(self):
        self.assertAlmostEqual(limit_margin(_limits()[0]), 29.0, places=9)

    def test_not_below_margin_is_the_room_left(self):
        self.assertAlmostEqual(limit_margin(_limits()[1]), 0.6, places=9)

    def test_demand_landing_on_the_limit_is_covered(self):
        limit = dict(_limits()[0])
        limit["application_demand"] = 125.0
        self.assertTrue(limit_is_covered(limit))
        self.assertAlmostEqual(limit_margin(limit), 0.0, places=9)

    def test_demand_past_the_limit_is_uncovered(self):
        limit = dict(_limits()[0])
        limit["application_demand"] = 140.0
        self.assertFalse(limit_is_covered(limit))

    def test_uncovered_parameter_is_named(self):
        limits = _limits()
        limits[1]["application_demand"] = 1.8
        self.assertEqual(uncovered_limits(limits), ("minimum-supply-voltage-v",))

    def test_marginal_limit_is_advised_on(self):
        limits = _limits()
        limits[0]["application_demand"] = 122.0
        self.assertEqual(marginal_limits(limits, _policy()), ("maximum-junction-temperature-c",))

    def test_comfortable_limits_are_not_marginal(self):
        self.assertEqual(marginal_limits(_limits(), _policy()), ())


class ChangeNoticeTests(unittest.TestCase):
    def test_long_enough_notice_binds(self):
        identity = validate_specification_identity(_specification())
        self.assertTrue(change_notice_is_binding(identity, _clauses(), _policy()))

    def test_notice_landing_on_the_lead_time_still_binds(self):
        identity = validate_specification_identity(
            _specification(change_notification_days=90.0)
        )
        self.assertTrue(change_notice_is_binding(identity, _clauses(), _policy()))

    def test_short_notice_does_not_bind(self):
        identity = validate_specification_identity(
            _specification(change_notification_days=14.0)
        )
        self.assertFalse(change_notice_is_binding(identity, _clauses(), _policy()))

    def test_notice_clause_left_to_discretion_does_not_bind(self):
        identity = validate_specification_identity(_specification())
        clauses = _clauses(discretion={CHANGE_NOTIFICATION_DUTY: True})
        self.assertFalse(change_notice_is_binding(identity, clauses, _policy()))


class AssessmentTests(unittest.TestCase):
    def test_complete_specification_is_accepted(self):
        result = assess_internal_supplier_specification_drd(_case())
        self.assertEqual(result["verdict"], SPECIFICATION_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_absent_specification_stops_the_assessment(self):
        result = assess_internal_supplier_specification_drd(_case(specification=None))
        self.assertEqual(result["verdict"], SPECIFICATION_NOT_PROVIDED)

    def test_blank_reference_stops_the_assessment(self):
        result = assess_internal_supplier_specification_drd(
            _case(specification=_specification(specification_reference=" "))
        )
        self.assertEqual(result["verdict"], SPECIFICATION_NOT_PROVIDED)

    def test_short_coverage_outranks_the_later_checks(self):
        specification = _specification(clauses=_clauses(drop=(STORAGE_AND_HANDLING,)))
        result = assess_internal_supplier_specification_drd(
            _case(specification=specification)
        )
        self.assertEqual(result["verdict"], CLAUSE_COVERAGE_SHORT)

    def test_discretionary_clause_is_its_own_verdict(self):
        specification = _specification(
            clauses=_clauses(discretion={SCREENING_OPERATIONS: True})
        )
        result = assess_internal_supplier_specification_drd(
            _case(
                policy=_policy(min_clause_coverage=0.5),
                specification=specification,
            )
        )
        self.assertEqual(result["verdict"], CLAUSE_LEFT_TO_DISCRETION)

    def test_short_change_notice_is_reported(self):
        specification = _specification(change_notification_days=10.0)
        result = assess_internal_supplier_specification_drd(
            _case(specification=specification)
        )
        self.assertEqual(result["verdict"], CHANGE_NOTIFICATION_NOT_BINDING)

    def test_uncovered_application_limit_is_reported(self):
        limits = _limits()
        limits[0]["application_demand"] = 150.0
        specification = _specification(declared_limits=limits)
        result = assess_internal_supplier_specification_drd(
            _case(specification=specification)
        )
        self.assertEqual(result["verdict"], APPLICATION_LIMIT_NOT_COVERED)
        self.assertEqual(result["uncovered_limits"], ("maximum-junction-temperature-c",))

    def test_marginal_limit_passes_with_an_advisory(self):
        limits = _limits()
        limits[2]["application_demand"] = 29.0
        specification = _specification(declared_limits=limits)
        result = assess_internal_supplier_specification_drd(
            _case(specification=specification)
        )
        self.assertEqual(result["verdict"], SPECIFICATION_ACCEPTED)
        self.assertEqual(len(result["advisories"]), 1)

    def test_specification_with_no_clauses_sequence_refused(self):
        specification = _specification()
        del specification["clauses"]
        with self.assertRaises(ValueError):
            assess_internal_supplier_specification_drd(
                _case(specification=specification)
            )

    def test_specification_with_no_limits_is_still_assessable(self):
        specification = _specification(declared_limits=[])
        result = assess_internal_supplier_specification_drd(
            _case(specification=specification)
        )
        self.assertEqual(result["verdict"], SPECIFICATION_ACCEPTED)

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_internal_supplier_specification_drd("specification")


if __name__ == "__main__":
    unittest.main()
