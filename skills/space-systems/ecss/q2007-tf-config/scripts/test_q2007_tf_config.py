#!/usr/bin/env python3
"""Contract tests for test facility configuration control, clause 5.6.2.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused policy,
a facility never baselined, a duplicate item, a change that does not
advance its version, a change applied without approval, a change chain
that breaks, an as-run item the baseline never declared, drift in both
directions, incomplete identification and a pending change backlog.
"""

import unittest

from q2007_tf_config_logic import (
    CHANGES_PENDING_APPROVAL,
    CONFIGURATION_DRIFT,
    CONFIGURATION_UNDER_CONTROL,
    DEFAULT_CONFIG_POLICY,
    FACILITY_NOT_BASELINED,
    IDENTIFICATION_INCOMPLETE,
    UNAPPROVED_CHANGE_APPLIED,
    assess_test_facility_configuration,
    configuration_drift,
    expected_configuration,
    identification_coverage,
    pending_changes,
    replay_item_version,
    unapproved_applied_changes,
    unidentified_items,
    validate_as_run,
    validate_baseline,
    validate_change_record,
    validate_changes,
    validate_config_policy,
    validate_configuration_item,
)


def _policy(**overrides):
    policy = dict(DEFAULT_CONFIG_POLICY)
    policy.update(overrides)
    return policy


def _baseline():
    return [
        {
            "item_id": "thermal-vacuum-chamber-shroud",
            "version": 3,
            "identification": "TVC-SHR-003",
        },
        {
            "item_id": "vibration-slip-table-fixture",
            "version": 1,
            "identification": "VIB-SLP-001",
        },
        {
            "item_id": "facility-control-software",
            "version": 7,
            "identification": "FCS-R7",
        },
    ]


def _changes():
    return [
        {
            "change_id": "fcr-101",
            "item_id": "facility-control-software",
            "from_version": 7,
            "to_version": 8,
            "approved": True,
            "applied": True,
        },
        {
            "change_id": "fcr-102",
            "item_id": "facility-control-software",
            "from_version": 8,
            "to_version": 9,
            "approved": True,
            "applied": True,
        },
    ]


def _as_run(**overrides):
    as_run = {
        "thermal-vacuum-chamber-shroud": 3,
        "vibration-slip-table-fixture": 1,
        "facility-control-software": 9,
    }
    as_run.update(overrides)
    return as_run


def _facility(**overrides):
    facility = {
        "baseline": _baseline(),
        "changes": _changes(),
        "as_run": _as_run(),
    }
    facility.update(overrides)
    return facility


def _case(**overrides):
    case = {"policy": _policy(), "facility": _facility()}
    case.update(overrides)
    return case


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_is_usable(self):
        self.assertIs(
            validate_config_policy(DEFAULT_CONFIG_POLICY), DEFAULT_CONFIG_POLICY
        )

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_config_policy("full coverage")

    def test_coverage_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_config_policy(_policy(min_identification_coverage=1.4))

    def test_negative_pending_allowance_refused(self):
        with self.assertRaises(ValueError):
            validate_config_policy(_policy(max_pending_changes=-1))


class BaselineValidationTests(unittest.TestCase):
    def test_item_is_read_back(self):
        record = validate_configuration_item(_baseline()[0])
        self.assertEqual(record["item_id"], "thermal-vacuum-chamber-shroud")
        self.assertEqual(record["version"], 3)

    def test_a_missing_identification_is_carried_as_blank(self):
        record = validate_configuration_item(
            {"item_id": "lox-feed-line", "version": 2}
        )
        self.assertEqual(record["identification"], "")

    def test_a_non_integer_version_refused(self):
        with self.assertRaises(ValueError):
            validate_configuration_item(
                {"item_id": "lox-feed-line", "version": 2.5}
            )

    def test_a_blank_item_id_refused(self):
        with self.assertRaises(ValueError):
            validate_configuration_item({"item_id": "  ", "version": 1})

    def test_the_same_item_twice_refused(self):
        with self.assertRaises(ValueError):
            validate_baseline(_baseline() + [_baseline()[0]])

    def test_an_empty_baseline_refused(self):
        with self.assertRaises(ValueError):
            validate_baseline([])


class IdentificationTests(unittest.TestCase):
    def test_a_fully_identified_baseline_has_full_coverage(self):
        self.assertAlmostEqual(identification_coverage(_baseline()), 1.0, places=9)

    def test_unidentified_items_stay_in_the_denominator(self):
        baseline = _baseline()
        baseline[1]["identification"] = "   "
        self.assertAlmostEqual(
            identification_coverage(baseline), 2.0 / 3.0, places=9
        )

    def test_unidentified_items_are_named(self):
        baseline = _baseline()
        baseline[1]["identification"] = ""
        self.assertEqual(
            unidentified_items(baseline), ("vibration-slip-table-fixture",)
        )


class ChangeRecordTests(unittest.TestCase):
    def test_change_is_read_back(self):
        record = validate_change_record(_changes()[0])
        self.assertEqual(record["from_version"], 7)
        self.assertTrue(record["approved"])

    def test_a_change_that_does_not_advance_is_refused(self):
        change = _changes()[0]
        change["to_version"] = 7
        with self.assertRaises(ValueError):
            validate_change_record(change)

    def test_a_backwards_change_is_refused(self):
        change = _changes()[0]
        change["to_version"] = 6
        with self.assertRaises(ValueError):
            validate_change_record(change)

    def test_a_non_boolean_approval_is_refused(self):
        change = _changes()[0]
        change["approved"] = "yes"
        with self.assertRaises(ValueError):
            validate_change_record(change)

    def test_the_same_change_identifier_twice_refused(self):
        with self.assertRaises(ValueError):
            validate_changes(_changes() + [_changes()[0]])

    def test_applied_without_approval_is_separated(self):
        changes = _changes()
        changes[1]["approved"] = False
        self.assertEqual(unapproved_applied_changes(changes), ("fcr-102",))

    def test_approved_but_unapplied_is_pending_not_unapproved(self):
        changes = _changes()
        changes[1]["applied"] = False
        self.assertEqual(unapproved_applied_changes(changes), ())
        self.assertEqual(pending_changes(changes), ("fcr-102",))


class ReplayTests(unittest.TestCase):
    def test_the_chain_walks_forward_from_the_baseline(self):
        self.assertEqual(replay_item_version(7, _changes()), 9)

    def test_an_unapplied_change_does_not_move_the_version(self):
        changes = _changes()
        changes[1]["applied"] = False
        self.assertEqual(replay_item_version(7, changes), 8)

    def test_a_broken_chain_is_refused_not_shortened(self):
        changes = _changes()
        changes[1]["from_version"] = 12
        changes[1]["to_version"] = 13
        with self.assertRaises(ValueError):
            replay_item_version(7, changes)

    def test_expected_configuration_covers_every_baseline_item(self):
        expected = expected_configuration(_baseline(), _changes())
        self.assertEqual(expected["facility-control-software"], 9)
        self.assertEqual(expected["thermal-vacuum-chamber-shroud"], 3)

    def test_a_change_naming_an_undeclared_item_is_refused(self):
        changes = _changes() + [
            {
                "change_id": "fcr-900",
                "item_id": "shaker-amplifier",
                "from_version": 1,
                "to_version": 2,
                "approved": True,
                "applied": True,
            }
        ]
        with self.assertRaises(ValueError):
            expected_configuration(_baseline(), changes)


class DriftTests(unittest.TestCase):
    def test_a_matching_as_run_has_no_drift(self):
        self.assertEqual(
            configuration_drift(_baseline(), _changes(), _as_run()), ()
        )

    def test_an_as_run_behind_the_chain_is_drift(self):
        drift = configuration_drift(
            _baseline(), _changes(), _as_run(**{"facility-control-software": 8})
        )
        self.assertEqual(drift[0]["as_run_version"], 8)
        self.assertEqual(drift[0]["expected_version"], 9)

    def test_an_as_run_ahead_of_the_chain_is_also_drift(self):
        drift = configuration_drift(
            _baseline(), _changes(), _as_run(**{"facility-control-software": 11})
        )
        self.assertEqual(len(drift), 1)

    def test_an_undeclared_as_run_item_is_refused(self):
        with self.assertRaises(ValueError):
            configuration_drift(
                _baseline(), _changes(), _as_run(**{"spare-shaker": 1})
            )

    def test_a_baseline_item_absent_from_the_as_run_is_refused(self):
        as_run = _as_run()
        del as_run["vibration-slip-table-fixture"]
        with self.assertRaises(ValueError):
            configuration_drift(_baseline(), _changes(), as_run)

    def test_a_duplicate_as_run_label_is_refused(self):
        with self.assertRaises(ValueError):
            validate_as_run({"chamber": 1, " chamber ": 2})


class AssessmentTests(unittest.TestCase):
    def test_a_controlled_facility_passes(self):
        result = assess_test_facility_configuration(_case())
        self.assertEqual(result["verdict"], CONFIGURATION_UNDER_CONTROL)
        self.assertEqual(result["items_baselined"], 3)

    def test_no_facility_at_all_stops_the_assessment(self):
        result = assess_test_facility_configuration(_case(facility=None))
        self.assertEqual(result["verdict"], FACILITY_NOT_BASELINED)

    def test_an_empty_baseline_closes_on_not_baselined(self):
        result = assess_test_facility_configuration(
            _case(facility=_facility(baseline=[]))
        )
        self.assertEqual(result["verdict"], FACILITY_NOT_BASELINED)

    def test_an_unapproved_applied_change_outranks_the_drift_it_caused(self):
        changes = _changes()
        changes[1]["approved"] = False
        result = assess_test_facility_configuration(
            _case(facility=_facility(changes=changes))
        )
        self.assertEqual(result["verdict"], UNAPPROVED_CHANGE_APPLIED)
        self.assertEqual(result["unapproved_applied"], ("fcr-102",))

    def test_drift_outranks_incomplete_identification(self):
        baseline = _baseline()
        baseline[0]["identification"] = ""
        result = assess_test_facility_configuration(
            _case(
                facility=_facility(
                    baseline=baseline,
                    as_run=_as_run(**{"facility-control-software": 8}),
                )
            )
        )
        self.assertEqual(result["verdict"], CONFIGURATION_DRIFT)

    def test_incomplete_identification_is_reported_on_its_own(self):
        baseline = _baseline()
        baseline[0]["identification"] = ""
        result = assess_test_facility_configuration(
            _case(facility=_facility(baseline=baseline))
        )
        self.assertEqual(result["verdict"], IDENTIFICATION_INCOMPLETE)
        self.assertAlmostEqual(
            result["identification_coverage"], 2.0 / 3.0, places=9
        )

    def test_a_pending_change_backlog_is_reported_as_an_advisory(self):
        changes = _changes()
        changes[1]["applied"] = False
        result = assess_test_facility_configuration(
            _case(
                facility=_facility(
                    changes=changes, as_run=_as_run(**{"facility-control-software": 8})
                )
            )
        )
        self.assertEqual(result["verdict"], CHANGES_PENDING_APPROVAL)
        self.assertEqual(len(result["advisories"]), 1)

    def test_a_policy_allowing_a_pending_change_still_passes(self):
        changes = _changes()
        changes[1]["applied"] = False
        result = assess_test_facility_configuration(
            _case(
                policy=_policy(max_pending_changes=1),
                facility=_facility(
                    changes=changes, as_run=_as_run(**{"facility-control-software": 8})
                ),
            )
        )
        self.assertEqual(result["verdict"], CONFIGURATION_UNDER_CONTROL)

    def test_a_facility_with_no_as_run_record_is_refused(self):
        facility = _facility()
        del facility["as_run"]
        with self.assertRaises(ValueError):
            assess_test_facility_configuration(_case(facility=facility))

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_test_facility_configuration(["facility"])


if __name__ == "__main__":
    unittest.main()
