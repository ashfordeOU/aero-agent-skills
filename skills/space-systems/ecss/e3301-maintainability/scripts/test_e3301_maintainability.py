"""Contract tests for the ECSS-E-ST-33-01 clause 4.2.4.4 maintainability logic."""

import unittest

from e3301_maintainability_logic import (
    APPROVAL_ABSENT,
    APPROVAL_APPROVED,
    APPROVAL_PENDING,
    DAYS_PER_MONTH,
    DEFAULT_LIFE_FACTOR,
    MAINTENANCE_PHASES,
    VERDICT_APPROVED,
    VERDICT_FREE,
    VERDICT_NON_COMPLIANT,
    access_is_provisioned,
    approval_state,
    assess_action,
    assess_life_items,
    assess_maintainability,
    life_margin_ratio,
    occurrences_in_mission,
    required_cycles,
    validate_life_item,
    validate_maintenance_action,
)

# A twelve-month mission at 100 cycles a day accumulates 36 525 cycles, so a
# 73 050-cycle qualification is exactly the factor of two the default demands.
MISSION_MONTHS = 12.0
DUTY_PER_DAY = 100.0
MISSION_CYCLES = 36525.0


def action(**overrides):
    """Return an approved ground-storage inspection action."""
    record = {
        "id": "MNT-01",
        "phase": "ground-storage",
        "requires_disassembly": False,
        "interval_months": 6.0,
        "customer_approval": {
            "status": "approved",
            "reference": "CUST-MNT-07",
            "date": "2026-04-02",
        },
    }
    record.update(overrides)
    return record


def in_orbit_action(**overrides):
    """Return an approved in-orbit action with declared access."""
    record = action(
        id="MNT-ORB-01",
        phase="in-orbit",
        interval_months=None,
        access_provision={"route": "hatch on the +Y panel", "tooling": "captive driver"},
    )
    record.update(overrides)
    return record


def life_item(**overrides):
    """Return a limited-life item exactly on the required factor."""
    record = {
        "id": "LUB-BEARING-01",
        "qualified_cycles": 73050.0,
        "duty_cycles_per_day": DUTY_PER_DAY,
    }
    record.update(overrides)
    return record


class ActionValidationTests(unittest.TestCase):
    def test_action_is_normalised(self):
        record = validate_maintenance_action(action(id=" MNT-01 "))
        self.assertEqual(record["id"], "MNT-01")
        self.assertAlmostEqual(record["interval_months"], 6.0)

    def test_every_listed_phase_is_accepted(self):
        for phase in MAINTENANCE_PHASES:
            record = validate_maintenance_action(action(phase=phase))
            self.assertEqual(record["phase"], phase)

    def test_unknown_phase_rejected(self):
        with self.assertRaises(ValueError):
            validate_maintenance_action(action(phase="on-console"))

    def test_zero_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_maintenance_action(action(interval_months=0.0))

    def test_non_boolean_disassembly_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_maintenance_action(action(requires_disassembly="no"))

    def test_missing_key_rejected(self):
        record = action()
        del record["phase"]
        with self.assertRaises(ValueError):
            validate_maintenance_action(record)

    def test_non_mapping_action_rejected(self):
        with self.assertRaises(ValueError):
            validate_maintenance_action(["MNT-01"])

    def test_non_mapping_approval_rejected(self):
        with self.assertRaises(ValueError):
            validate_maintenance_action(action(customer_approval="approved"))


class OccurrenceTests(unittest.TestCase):
    def test_six_monthly_action_falls_four_times_in_two_years(self):
        self.assertEqual(occurrences_in_mission(action(), 24.0), 4)

    def test_one_off_action_falls_once(self):
        self.assertEqual(occurrences_in_mission(action(interval_months=None), 24.0), 1)

    def test_interval_longer_than_the_mission_never_falls(self):
        self.assertEqual(occurrences_in_mission(action(interval_months=36.0), 24.0), 0)

    def test_interval_equal_to_the_mission_falls_once(self):
        self.assertEqual(occurrences_in_mission(action(interval_months=24.0), 24.0), 1)

    def test_zero_mission_duration_rejected(self):
        with self.assertRaises(ValueError):
            occurrences_in_mission(action(), 0.0)


class ApprovalTests(unittest.TestCase):
    def test_recorded_approval_is_approved(self):
        self.assertEqual(approval_state(action()), APPROVAL_APPROVED)

    def test_absent_approval_is_not_submitted(self):
        self.assertEqual(
            approval_state(action(customer_approval=None)), APPROVAL_ABSENT)

    def test_other_status_is_pending(self):
        self.assertEqual(
            approval_state(action(customer_approval={"status": "in review"})),
            APPROVAL_PENDING,
        )

    def test_approval_without_a_reference_rejected(self):
        with self.assertRaises(ValueError):
            approval_state(action(customer_approval={
                "status": "approved", "date": "2026-04-02"}))

    def test_approval_without_a_date_rejected(self):
        with self.assertRaises(ValueError):
            approval_state(action(customer_approval={
                "status": "approved", "reference": "CUST-MNT-07"}))

    def test_declared_access_is_recognised(self):
        self.assertTrue(access_is_provisioned(in_orbit_action()))

    def test_access_without_tooling_is_not_provisioned(self):
        record = in_orbit_action(access_provision={"route": "hatch on the +Y panel"})
        self.assertFalse(access_is_provisioned(record))

    def test_no_access_block_is_not_provisioned(self):
        self.assertFalse(access_is_provisioned(action()))


class LifeMarginTests(unittest.TestCase):
    def test_mission_cycles_match_the_hand_computed_value(self):
        self.assertAlmostEqual(
            required_cycles(DUTY_PER_DAY, MISSION_MONTHS), MISSION_CYCLES, places=6)

    def test_days_per_month_is_the_mean_calendar_month(self):
        self.assertAlmostEqual(DAYS_PER_MONTH, 30.4375, places=12)

    def test_margin_exactly_on_the_required_factor(self):
        ratio = life_margin_ratio(life_item(), MISSION_MONTHS)
        self.assertAlmostEqual(ratio, DEFAULT_LIFE_FACTOR, places=9)

    def test_doubling_the_qualified_life_doubles_the_margin(self):
        one = life_margin_ratio(life_item(), MISSION_MONTHS)
        two = life_margin_ratio(life_item(qualified_cycles=146100.0), MISSION_MONTHS)
        self.assertAlmostEqual(two, 2.0 * one, places=9)

    def test_longer_mission_shrinks_the_margin(self):
        short = life_margin_ratio(life_item(), MISSION_MONTHS)
        long_mission = life_margin_ratio(life_item(), 2.0 * MISSION_MONTHS)
        self.assertAlmostEqual(long_mission, short / 2.0, places=9)

    def test_zero_duty_rejected(self):
        with self.assertRaises(ValueError):
            validate_life_item(life_item(duty_cycles_per_day=0.0))

    def test_missing_life_key_rejected(self):
        record = life_item()
        del record["qualified_cycles"]
        with self.assertRaises(ValueError):
            validate_life_item(record)

    def test_item_on_the_factor_is_sufficient(self):
        result = assess_life_items([life_item()], MISSION_MONTHS)
        self.assertTrue(result["records"][0]["sufficient"])
        self.assertEqual(result["findings"], [])

    def test_item_below_the_factor_is_a_finding(self):
        result = assess_life_items([life_item(qualified_cycles=60000.0)], MISSION_MONTHS)
        self.assertFalse(result["records"][0]["sufficient"])
        self.assertTrue(any("unstated maintenance demand" in f
                            for f in result["findings"]))

    def test_life_factor_can_be_raised(self):
        result = assess_life_items([life_item()], MISSION_MONTHS, life_factor=4.0)
        self.assertFalse(result["records"][0]["sufficient"])

    def test_record_carries_the_required_cycles(self):
        result = assess_life_items([life_item()], MISSION_MONTHS)
        self.assertAlmostEqual(
            result["records"][0]["required_cycles"], MISSION_CYCLES, places=6)


class ActionAssessmentTests(unittest.TestCase):
    def test_approved_ground_action_is_permitted(self):
        record = assess_action(action(), 24.0)
        self.assertTrue(record["permitted"])
        self.assertEqual(record["findings"], [])

    def test_unapproved_action_is_not_permitted(self):
        record = assess_action(action(customer_approval=None), 24.0)
        self.assertFalse(record["permitted"])
        self.assertTrue(any("not approved" in f for f in record["findings"]))

    def test_in_orbit_action_with_access_is_permitted(self):
        record = assess_action(in_orbit_action(), 24.0)
        self.assertTrue(record["permitted"])

    def test_in_orbit_action_without_access_is_a_finding(self):
        record = assess_action(in_orbit_action(access_provision=None), 24.0)
        self.assertFalse(record["permitted"])
        self.assertTrue(any("no access route" in f for f in record["findings"]))

    def test_in_orbit_disassembly_is_a_finding(self):
        record = assess_action(in_orbit_action(requires_disassembly=True), 24.0)
        self.assertFalse(record["permitted"])
        self.assertTrue(any("opens the mechanism" in f for f in record["findings"]))

    def test_interval_beyond_the_mission_is_reported(self):
        record = assess_action(action(interval_months=36.0), 24.0)
        self.assertEqual(record["occurrences"], 0)
        self.assertTrue(any("not a maintenance demand" in f for f in record["findings"]))


class MaintainabilityVerdictTests(unittest.TestCase):
    def test_design_with_no_actions_is_maintenance_free(self):
        result = assess_maintainability({
            "mission_duration_months": MISSION_MONTHS,
            "life_items": [life_item()],
        })
        self.assertEqual(result["verdict"], VERDICT_FREE)
        self.assertTrue(result["maintenance_free"])
        self.assertTrue(result["compliant"])

    def test_approved_action_gives_approved_maintenance(self):
        result = assess_maintainability({
            "mission_duration_months": 24.0,
            "maintenance_actions": [action()],
            "life_items": [life_item(qualified_cycles=146100.0)],
        })
        self.assertEqual(result["verdict"], VERDICT_APPROVED)
        self.assertFalse(result["maintenance_free"])
        self.assertTrue(result["compliant"])

    def test_unapproved_action_is_non_compliant(self):
        result = assess_maintainability({
            "mission_duration_months": 24.0,
            "maintenance_actions": [action(customer_approval=None)],
        })
        self.assertEqual(result["verdict"], VERDICT_NON_COMPLIANT)
        self.assertFalse(result["compliant"])

    def test_life_shortfall_alone_is_non_compliant(self):
        result = assess_maintainability({
            "mission_duration_months": MISSION_MONTHS,
            "life_items": [life_item(qualified_cycles=60000.0)],
        })
        self.assertEqual(result["verdict"], VERDICT_NON_COMPLIANT)

    def test_permitted_actions_are_counted(self):
        result = assess_maintainability({
            "mission_duration_months": 24.0,
            "maintenance_actions": [action(), in_orbit_action()],
        })
        self.assertEqual(result["declared_action_count"], 2)
        self.assertEqual(result["permitted_action_count"], 2)

    def test_repeated_action_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_maintainability({
                "mission_duration_months": 24.0,
                "maintenance_actions": [action(), action()],
            })

    def test_missing_mission_duration_rejected(self):
        with self.assertRaises(ValueError):
            assess_maintainability({"maintenance_actions": [action()]})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_maintainability(["mission_duration_months"])

    def test_non_sequence_action_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_maintainability({
                "mission_duration_months": 24.0,
                "maintenance_actions": action(),
            })


if __name__ == "__main__":
    unittest.main()
