"""Contract tests for the clause 5.2.6.4.1 essential-load disable authority.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: essentiality asserted with
no rationale, a population with no essential limiter in it, an onboard path
holding retrigger-disable authority over an essential load, and the reach of
the widest such path.
"""

import unittest

from e2020_essential_load_retrigger_disabling_logic import (
    DEFAULT_AUTHORITY_POLICY,
    DISABLE_AUTHORITY_GROUND_ONLY,
    ESSENTIALITY_NOT_ESTABLISHED,
    NON_GROUND_DISABLE_AUTHORITY,
    assess_essential_load_retrigger_disabling,
    authority_advisories,
    blast_radius,
    command_source_index,
    essential_exposure,
    exposed_essential_fraction,
    group_by_essentiality,
    limiter_records,
    non_ground_authorities,
    unsupported_essentiality,
    validate_authority_policy,
    validate_command_source,
    validate_limiter_record,
    widest_non_ground_path,
)

GROUND = "ground-telecommand"
TIME_TAGGED = "ground-time-tagged-sequence"
FAULT_MANAGEMENT = "onboard-fault-management"
TIMELINE = "onboard-mission-timeline"


def _policy(**overrides):
    policy = dict(DEFAULT_AUTHORITY_POLICY)
    policy.update(overrides)
    return policy


def _sources():
    return [
        {"name": GROUND, "ground_originated": True, "executed_onboard": False},
        {"name": TIME_TAGGED, "ground_originated": True, "executed_onboard": True},
        {
            "name": FAULT_MANAGEMENT,
            "ground_originated": False,
            "executed_onboard": True,
        },
        {"name": TIMELINE, "ground_originated": False, "executed_onboard": True},
    ]


def _limiter(identifier, **overrides):
    limiter = {
        "id": identifier,
        "load_id": "load-for-%s" % identifier,
        "essential": True,
        "essentiality_rationale": "criticality list entry %s" % identifier,
        "disable_authority": (GROUND,),
    }
    limiter.update(overrides)
    return limiter


def _limiters():
    return [
        _limiter("rcl-1"),
        _limiter("rcl-2"),
        _limiter("rcl-3", essential=False, essentiality_rationale=""),
    ]


def _case(**overrides):
    case = {"command_sources": _sources(), "limiters": _limiters()}
    case.update(overrides)
    return case


def _index():
    return command_source_index(_sources())


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_authority_policy(DEFAULT_AUTHORITY_POLICY),
            DEFAULT_AUTHORITY_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_authority_policy("max_exposed_essential_limiters")

    def test_non_boolean_rationale_requirement_rejected(self):
        with self.assertRaises(ValueError):
            validate_authority_policy(_policy(require_essentiality_rationale="yes"))

    def test_fractional_exposure_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_authority_policy(_policy(max_exposed_essential_limiters=0.5))

    def test_zero_blast_radius_advisory_rejected(self):
        with self.assertRaises(ValueError):
            validate_authority_policy(_policy(blast_radius_advisory_count=0))


class SourceTests(unittest.TestCase):
    def test_good_source_validates(self):
        record = validate_command_source(_sources()[0])
        self.assertEqual(record["name"], GROUND)
        self.assertTrue(record["ground_originated"])

    def test_non_mapping_source_rejected(self):
        with self.assertRaises(ValueError):
            validate_command_source([GROUND])

    def test_blank_source_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_command_source(
                {"name": "  ", "ground_originated": True, "executed_onboard": False}
            )

    def test_non_boolean_origin_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_command_source(
                {"name": GROUND, "ground_originated": 1, "executed_onboard": False}
            )

    def test_empty_source_list_rejected(self):
        with self.assertRaises(ValueError):
            command_source_index([])

    def test_duplicate_source_rejected(self):
        with self.assertRaises(ValueError):
            command_source_index([_sources()[0], _sources()[0]])

    def test_a_time_tagged_uplink_is_ground_originated(self):
        index = _index()
        self.assertTrue(index[TIME_TAGGED]["ground_originated"])
        self.assertTrue(index[TIME_TAGGED]["executed_onboard"])


class LimiterValidationTests(unittest.TestCase):
    def test_good_limiter_validates(self):
        record = validate_limiter_record(_limiter("rcl-9"))
        self.assertEqual(record["id"], "rcl-9")
        self.assertEqual(record["disable_authority"], (GROUND,))

    def test_non_mapping_limiter_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_record(["rcl-9"])

    def test_blank_load_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_record(_limiter("rcl-9", load_id=" "))

    def test_non_boolean_essential_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_record(_limiter("rcl-9", essential="yes"))

    def test_repeated_authority_entry_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_record(
                _limiter("rcl-9", disable_authority=(GROUND, GROUND))
            )

    def test_empty_limiter_population_rejected(self):
        with self.assertRaises(ValueError):
            limiter_records([])

    def test_duplicate_limiter_id_rejected(self):
        with self.assertRaises(ValueError):
            limiter_records([_limiter("rcl-1"), _limiter("rcl-1")])


class GroupingTests(unittest.TestCase):
    def test_population_splits_by_essentiality(self):
        essential, other = group_by_essentiality(limiter_records(_limiters()))
        self.assertEqual(len(essential), 2)
        self.assertEqual(len(other), 1)

    def test_essentiality_without_rationale_is_named(self):
        limiters = _limiters()
        limiters[0]["essentiality_rationale"] = ""
        self.assertEqual(
            unsupported_essentiality(limiter_records(limiters)), ("rcl-1",)
        )

    def test_a_non_essential_limiter_needs_no_rationale(self):
        self.assertEqual(unsupported_essentiality(limiter_records(_limiters())), ())

    def test_the_rationale_requirement_can_be_waived(self):
        limiters = _limiters()
        limiters[0]["essentiality_rationale"] = ""
        self.assertEqual(
            unsupported_essentiality(
                limiter_records(limiters),
                _policy(require_essentiality_rationale=False),
            ),
            (),
        )


class AuthorityTests(unittest.TestCase):
    def test_ground_only_authority_has_no_offending_path(self):
        self.assertEqual(non_ground_authorities(_limiter("rcl-1"), _index()), ())

    def test_a_time_tagged_uplink_is_not_an_offending_path(self):
        limiter = _limiter("rcl-1", disable_authority=(TIME_TAGGED,))
        self.assertEqual(non_ground_authorities(limiter, _index()), ())

    def test_onboard_fault_management_is_an_offending_path(self):
        limiter = _limiter("rcl-1", disable_authority=(GROUND, FAULT_MANAGEMENT))
        self.assertEqual(
            non_ground_authorities(limiter, _index()), (FAULT_MANAGEMENT,)
        )

    def test_an_undeclared_authority_is_rejected(self):
        limiter = _limiter("rcl-1", disable_authority=("bench-test-jig",))
        with self.assertRaises(ValueError):
            non_ground_authorities(limiter, _index())

    def test_only_essential_limiters_are_counted_as_exposed(self):
        limiters = _limiters()
        limiters[2]["disable_authority"] = (GROUND, FAULT_MANAGEMENT)
        exposure = essential_exposure(limiter_records(limiters), _index())
        self.assertEqual(exposure, ())

    def test_an_exposed_essential_limiter_is_named_with_its_path(self):
        limiters = _limiters()
        limiters[1]["disable_authority"] = (GROUND, TIMELINE)
        exposure = essential_exposure(limiter_records(limiters), _index())
        self.assertEqual(exposure, (("rcl-2", (TIMELINE,)),))

    def test_exposed_fraction_of_the_essential_population(self):
        limiters = _limiters()
        limiters[1]["disable_authority"] = (GROUND, TIMELINE)
        self.assertAlmostEqual(
            exposed_essential_fraction(limiter_records(limiters), _index()),
            0.5,
            places=9,
        )

    def test_exposed_fraction_is_zero_on_the_base_population(self):
        self.assertAlmostEqual(
            exposed_essential_fraction(limiter_records(_limiters()), _index()),
            0.0,
            places=9,
        )

    def test_fraction_refuses_a_population_with_no_essential_limiter(self):
        limiters = [_limiter("rcl-3", essential=False, essentiality_rationale="")]
        with self.assertRaises(ValueError):
            exposed_essential_fraction(limiter_records(limiters), _index())


class ReachTests(unittest.TestCase):
    def test_no_reach_on_a_compliant_population(self):
        self.assertEqual(blast_radius(limiter_records(_limiters()), _index()), {})
        self.assertIsNone(widest_non_ground_path(limiter_records(_limiters()), _index()))

    def test_one_path_reaching_two_essential_limiters(self):
        limiters = _limiters()
        limiters[0]["disable_authority"] = (GROUND, FAULT_MANAGEMENT)
        limiters[1]["disable_authority"] = (GROUND, FAULT_MANAGEMENT)
        records = limiter_records(limiters)
        self.assertEqual(blast_radius(records, _index()), {FAULT_MANAGEMENT: 2})
        self.assertEqual(
            widest_non_ground_path(records, _index()), (FAULT_MANAGEMENT, 2)
        )

    def test_the_widest_path_wins_over_a_narrower_one(self):
        limiters = _limiters()
        limiters[0]["disable_authority"] = (GROUND, FAULT_MANAGEMENT)
        limiters[1]["disable_authority"] = (GROUND, FAULT_MANAGEMENT, TIMELINE)
        records = limiter_records(limiters)
        self.assertEqual(
            widest_non_ground_path(records, _index()), (FAULT_MANAGEMENT, 2)
        )


class AdvisoryTests(unittest.TestCase):
    def test_compliant_population_raises_no_advisory(self):
        self.assertEqual(authority_advisories(limiter_records(_limiters()), _index()), ())

    def test_an_essential_limiter_nobody_can_disable_is_named(self):
        limiters = _limiters()
        limiters[0]["disable_authority"] = ()
        advisories = authority_advisories(limiter_records(limiters), _index())
        self.assertEqual(len(advisories), 1)
        self.assertIn("nobody at all", advisories[0])

    def test_an_onboard_executed_ground_path_is_named(self):
        limiters = _limiters()
        limiters[1]["disable_authority"] = (TIME_TAGGED,)
        advisories = authority_advisories(limiter_records(limiters), _index())
        self.assertEqual(len(advisories), 1)
        self.assertIn("uplink record", advisories[0])

    def test_an_all_essential_population_is_named(self):
        limiters = [_limiter("rcl-1"), _limiter("rcl-2")]
        advisories = authority_advisories(limiter_records(limiters), _index())
        self.assertEqual(len(advisories), 1)
        self.assertIn("marked essential", advisories[0])


class AssessmentTests(unittest.TestCase):
    def test_ground_only_population_passes(self):
        result = assess_essential_load_retrigger_disabling(_case())
        self.assertEqual(result["verdict"], DISABLE_AUTHORITY_GROUND_ONLY)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["advisories"], [])

    def test_a_time_tagged_uplink_still_passes(self):
        limiters = _limiters()
        limiters[1]["disable_authority"] = (TIME_TAGGED,)
        result = assess_essential_load_retrigger_disabling(_case(limiters=limiters))
        self.assertEqual(result["verdict"], DISABLE_AUTHORITY_GROUND_ONLY)
        self.assertEqual(len(result["advisories"]), 1)

    def test_unsupported_essentiality_closes_the_assessment(self):
        limiters = _limiters()
        limiters[0]["essentiality_rationale"] = "  "
        result = assess_essential_load_retrigger_disabling(_case(limiters=limiters))
        self.assertEqual(result["verdict"], ESSENTIALITY_NOT_ESTABLISHED)
        self.assertEqual(result["unsupported_essentiality"], ("rcl-1",))

    def test_a_population_with_no_essential_limiter_closes_too(self):
        limiters = [_limiter("rcl-3", essential=False, essentiality_rationale="")]
        result = assess_essential_load_retrigger_disabling(_case(limiters=limiters))
        self.assertEqual(result["verdict"], ESSENTIALITY_NOT_ESTABLISHED)

    def test_onboard_authority_on_an_essential_load_fails(self):
        limiters = _limiters()
        limiters[1]["disable_authority"] = (GROUND, FAULT_MANAGEMENT)
        result = assess_essential_load_retrigger_disabling(_case(limiters=limiters))
        self.assertEqual(result["verdict"], NON_GROUND_DISABLE_AUTHORITY)
        self.assertEqual(result["exposed_essential_count"], 1)
        self.assertAlmostEqual(result["exposed_essential_fraction"], 0.5, places=9)

    def test_every_exposed_limiter_is_named_not_only_the_first(self):
        limiters = _limiters()
        limiters[0]["disable_authority"] = (GROUND, TIMELINE)
        limiters[1]["disable_authority"] = (GROUND, FAULT_MANAGEMENT)
        result = assess_essential_load_retrigger_disabling(_case(limiters=limiters))
        self.assertEqual(len(result["findings"]), 2)

    def test_a_wide_onboard_path_adds_its_own_finding(self):
        limiters = [
            _limiter("rcl-1", disable_authority=(GROUND, FAULT_MANAGEMENT)),
            _limiter("rcl-2", disable_authority=(GROUND, FAULT_MANAGEMENT)),
            _limiter("rcl-4", disable_authority=(GROUND, FAULT_MANAGEMENT)),
            _limiter("rcl-3", essential=False, essentiality_rationale=""),
        ]
        result = assess_essential_load_retrigger_disabling(_case(limiters=limiters))
        self.assertEqual(result["verdict"], NON_GROUND_DISABLE_AUTHORITY)
        self.assertEqual(result["widest_non_ground_reach"], 3)
        self.assertEqual(len(result["findings"]), 4)

    def test_the_non_essential_population_is_reported_separately(self):
        result = assess_essential_load_retrigger_disabling(_case())
        self.assertEqual(result["essential_limiters"], ("rcl-1", "rcl-2"))
        self.assertEqual(result["non_essential_limiters"], ("rcl-3",))

    def test_a_declared_allowance_can_admit_one_exposure(self):
        limiters = _limiters()
        limiters[1]["disable_authority"] = (GROUND, FAULT_MANAGEMENT)
        result = assess_essential_load_retrigger_disabling(
            _case(limiters=limiters), _policy(max_exposed_essential_limiters=1)
        )
        self.assertEqual(result["verdict"], DISABLE_AUTHORITY_GROUND_ONLY)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_essential_load_retrigger_disabling(["limiters"])

    def test_missing_command_sources_rejected(self):
        case = _case()
        del case["command_sources"]
        with self.assertRaises(ValueError):
            assess_essential_load_retrigger_disabling(case)


if __name__ == "__main__":
    unittest.main()
