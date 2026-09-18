"""Contract tests for the clause 5.2.13.1.1 stuck-on switch budget logic."""

import unittest

from e2020_switch_failure_power_budget_logic import (
    BUDGET_COVERED,
    BUDGET_EXCEEDED,
    BUDGET_MARGIN_SHORTFALL,
    BUDGET_NOT_ASSESSED,
    DEFAULT_BUDGET_POLICY,
    DOWNSTREAM_LOAD_SWITCH,
    NO_ADDITIONAL_SWITCHING,
    REDUNDANT_LIMITER_BRANCH,
    SWITCHING_PROVISIONS,
    UPSTREAM_ISOLATION_SWITCH,
    assess_switch_failure_budget,
    budget_margin_fraction,
    categorize_switching_provision,
    channels_needing_budget,
    normalize_channel,
    normalize_channels,
    provision_sheds_load,
    stuck_on_increment_w,
    stuck_on_power_w,
    validate_budget_policy,
    worst_case_increment_w,
)


def _policy(**overrides):
    policy = dict(DEFAULT_BUDGET_POLICY)
    policy.update(overrides)
    return policy


def _channel(
    identifier,
    provision=NO_ADDITIONAL_SWITCHING,
    nominal=56.0,
    stuck_current=3.0,
):
    return {
        "id": identifier,
        "switching_provision": provision,
        "nominal_power_w": nominal,
        "stuck_on_current_a": stuck_current,
    }


def _system(**overrides):
    system = {
        "bus_voltage_v": 28.0,
        "available_power_w": 1000.0,
        "nominal_demand_w": 700.0,
        "channels": [
            _channel("ch-a", nominal=56.0, stuck_current=3.0),
            _channel(
                "ch-b",
                provision=DOWNSTREAM_LOAD_SWITCH,
                nominal=28.0,
                stuck_current=5.0,
            ),
            _channel("ch-c", nominal=28.0, stuck_current=1.5),
        ],
    }
    system.update(overrides)
    return system


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_budget_policy(DEFAULT_BUDGET_POLICY), DEFAULT_BUDGET_POLICY
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_budget_policy("covered")

    def test_a_zero_margin_requirement_is_allowed(self):
        policy = _policy(required_margin_fraction=0.0)
        self.assertIs(validate_budget_policy(policy), policy)

    def test_a_margin_requirement_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_budget_policy(_policy(required_margin_fraction=1.0))

    def test_a_negative_margin_requirement_rejected(self):
        with self.assertRaises(ValueError):
            validate_budget_policy(_policy(required_margin_fraction=-0.05))

    def test_zero_simultaneous_stuck_channels_rejected(self):
        with self.assertRaises(ValueError):
            validate_budget_policy(_policy(simultaneous_stuck_channels=0))


class ProvisionTests(unittest.TestCase):
    def test_every_known_provision_round_trips(self):
        for provision in SWITCHING_PROVISIONS:
            self.assertEqual(categorize_switching_provision(provision), provision)

    def test_an_unrecognised_provision_rejected(self):
        with self.assertRaises(ValueError):
            categorize_switching_provision("thermal-cutout")

    def test_an_empty_provision_rejected(self):
        with self.assertRaises(ValueError):
            categorize_switching_provision("   ")

    def test_an_isolation_switch_sheds_the_stuck_on_load(self):
        self.assertTrue(provision_sheds_load(UPSTREAM_ISOLATION_SWITCH))

    def test_a_load_switch_sheds_the_stuck_on_load(self):
        self.assertTrue(provision_sheds_load(DOWNSTREAM_LOAD_SWITCH))

    def test_no_additional_switching_sheds_nothing(self):
        self.assertFalse(provision_sheds_load(NO_ADDITIONAL_SWITCHING))

    def test_a_redundant_branch_is_a_second_path_not_a_way_out(self):
        self.assertFalse(provision_sheds_load(REDUNDANT_LIMITER_BRANCH))


class PowerTests(unittest.TestCase):
    def test_stuck_on_power_is_the_bus_voltage_times_the_current(self):
        self.assertAlmostEqual(stuck_on_power_w(28.0, 3.0), 84.0, places=9)

    def test_a_zero_stuck_on_current_draws_nothing(self):
        self.assertAlmostEqual(stuck_on_power_w(28.0, 0.0), 0.0, places=9)

    def test_a_zero_bus_voltage_rejected(self):
        with self.assertRaises(ValueError):
            stuck_on_power_w(0.0, 3.0)

    def test_a_negative_stuck_on_current_rejected(self):
        with self.assertRaises(ValueError):
            stuck_on_power_w(28.0, -3.0)

    def test_the_increment_is_what_the_failure_adds_over_the_nominal_draw(self):
        self.assertAlmostEqual(stuck_on_increment_w(84.0, 56.0), 28.0, places=9)

    def test_a_stuck_draw_below_nominal_adds_nothing_rather_than_a_credit(self):
        self.assertAlmostEqual(stuck_on_increment_w(28.0, 100.0), 0.0, places=9)

    def test_a_stuck_draw_equal_to_nominal_adds_nothing(self):
        self.assertAlmostEqual(stuck_on_increment_w(56.0, 56.0), 0.0, places=9)

    def test_a_negative_nominal_power_rejected(self):
        with self.assertRaises(ValueError):
            stuck_on_increment_w(84.0, -1.0)


class ChannelTests(unittest.TestCase):
    def test_a_channel_carries_its_provision_power_and_increment(self):
        channel = normalize_channel(_channel("ch-a"), 28.0)
        self.assertFalse(channel["sheds_load"])
        self.assertAlmostEqual(channel["stuck_on_power_w"], 84.0, places=9)
        self.assertAlmostEqual(channel["stuck_on_increment_w"], 28.0, places=9)
        self.assertTrue(channel["assessed"])

    def test_a_channel_without_a_stuck_on_current_is_not_assessed(self):
        channel = normalize_channel(_channel("ch-a", stuck_current=None), 28.0)
        self.assertFalse(channel["assessed"])
        self.assertIsNone(channel["stuck_on_increment_w"])

    def test_a_channel_without_an_id_rejected(self):
        with self.assertRaises(ValueError):
            normalize_channel({"switching_provision": NO_ADDITIONAL_SWITCHING}, 28.0)

    def test_a_channel_with_an_unrecognised_provision_rejected(self):
        with self.assertRaises(ValueError):
            normalize_channel(_channel("ch-a", provision="hope"), 28.0)

    def test_a_duplicate_channel_id_rejected(self):
        with self.assertRaises(ValueError):
            normalize_channels([_channel("ch-a"), _channel("ch-a")], 28.0)

    def test_an_empty_channel_set_rejected(self):
        with self.assertRaises(ValueError):
            normalize_channels([], 28.0)

    def test_only_the_unsheddable_channels_need_the_budget(self):
        channels = normalize_channels(_system()["channels"], 28.0)
        needing = [channel["id"] for channel in channels_needing_budget(channels)]
        self.assertEqual(needing, ["ch-a", "ch-c"])

    def test_a_raw_channel_that_was_never_normalized_rejected(self):
        with self.assertRaises(ValueError):
            channels_needing_budget([_channel("ch-a")])


class WorstCaseTests(unittest.TestCase):
    def test_a_single_failure_charges_only_the_largest_increment(self):
        channels = channels_needing_budget(
            normalize_channels(_system()["channels"], 28.0)
        )
        self.assertAlmostEqual(worst_case_increment_w(channels, 1), 28.0, places=9)

    def test_two_simultaneous_failures_charge_the_two_largest(self):
        channels = channels_needing_budget(
            normalize_channels(_system()["channels"], 28.0)
        )
        self.assertAlmostEqual(worst_case_increment_w(channels, 2), 42.0, places=9)

    def test_an_unassessed_channel_contributes_no_charge(self):
        channels = normalize_channels(
            [_channel("ch-a", stuck_current=None)], 28.0
        )
        self.assertAlmostEqual(worst_case_increment_w(channels, 1), 0.0, places=9)

    def test_a_zero_simultaneous_count_rejected(self):
        channels = normalize_channels(_system()["channels"], 28.0)
        with self.assertRaises(ValueError):
            worst_case_increment_w(channels, 0)

    def test_margin_is_the_unspent_share_of_the_available_power(self):
        self.assertAlmostEqual(budget_margin_fraction(1000.0, 900.0), 0.1, places=9)

    def test_a_demand_over_the_available_power_gives_a_negative_margin(self):
        self.assertLess(budget_margin_fraction(1000.0, 1200.0), 0.0)

    def test_a_zero_available_power_rejected(self):
        with self.assertRaises(ValueError):
            budget_margin_fraction(0.0, 900.0)


class SystemAssessmentTests(unittest.TestCase):
    def test_a_sized_spacecraft_covers_its_worst_stuck_on_channel(self):
        result = assess_switch_failure_budget(_system())
        self.assertEqual(result["verdict"], BUDGET_COVERED)
        self.assertAlmostEqual(result["worst_case_increment_w"], 28.0, places=9)
        self.assertAlmostEqual(result["demand_power_w"], 728.0, places=9)

    def test_a_sheddable_channel_is_never_charged(self):
        result = assess_switch_failure_budget(_system())
        self.assertEqual(result["sheddable_channels"], ["ch-b"])
        self.assertNotIn("ch-b", result["charged_channels"])

    def test_an_unsized_unsheddable_channel_outranks_everything_else(self):
        result = assess_switch_failure_budget(
            _system(
                nominal_demand_w=990.0,
                channels=[
                    _channel("ch-a", stuck_current=3.0),
                    _channel("ch-c", stuck_current=None),
                ],
            )
        )
        self.assertEqual(result["verdict"], BUDGET_NOT_ASSESSED)
        self.assertEqual(result["unassessed_channels"], ["ch-c"])

    def test_a_sheddable_channel_needs_no_stuck_on_current(self):
        result = assess_switch_failure_budget(
            _system(
                channels=[
                    _channel("ch-a", stuck_current=3.0),
                    _channel(
                        "ch-b",
                        provision=UPSTREAM_ISOLATION_SWITCH,
                        stuck_current=None,
                    ),
                ]
            )
        )
        self.assertEqual(result["unassessed_channels"], [])
        self.assertEqual(result["verdict"], BUDGET_COVERED)

    def test_a_demand_over_the_available_power_is_reported_as_exceeded(self):
        result = assess_switch_failure_budget(_system(nominal_demand_w=990.0))
        self.assertEqual(result["verdict"], BUDGET_EXCEEDED)

    def test_a_failure_paid_out_of_the_margin_is_reported_separately(self):
        result = assess_switch_failure_budget(_system(nominal_demand_w=920.0))
        self.assertEqual(result["verdict"], BUDGET_MARGIN_SHORTFALL)

    def test_a_margin_exactly_on_the_requirement_is_covered(self):
        result = assess_switch_failure_budget(_system(nominal_demand_w=872.0))
        self.assertAlmostEqual(
            result["margin_fraction"],
            float(DEFAULT_BUDGET_POLICY["required_margin_fraction"]),
            places=9,
        )
        self.assertEqual(result["verdict"], BUDGET_COVERED)

    def test_a_redundant_branch_does_not_excuse_the_channel_from_the_budget(self):
        result = assess_switch_failure_budget(
            _system(
                channels=[
                    _channel(
                        "ch-a",
                        provision=REDUNDANT_LIMITER_BRANCH,
                        stuck_current=3.0,
                    ),
                    _channel(
                        "ch-b",
                        provision=DOWNSTREAM_LOAD_SWITCH,
                        stuck_current=5.0,
                    ),
                ]
            )
        )
        self.assertEqual(result["channels_needing_budget"], ["ch-a"])
        self.assertEqual(result["charged_channels"], ["ch-a"])

    def test_a_two_failure_policy_charges_more_than_a_single_failure(self):
        single = assess_switch_failure_budget(_system())
        double = assess_switch_failure_budget(
            _system(), _policy(simultaneous_stuck_channels=2)
        )
        self.assertAlmostEqual(double["worst_case_increment_w"], 42.0, places=9)
        self.assertGreater(
            double["worst_case_increment_w"], single["worst_case_increment_w"]
        )

    def test_a_system_without_an_available_power_rejected(self):
        system = _system()
        del system["available_power_w"]
        with self.assertRaises(ValueError):
            assess_switch_failure_budget(system)

    def test_a_non_mapping_system_rejected(self):
        with self.assertRaises(ValueError):
            assess_switch_failure_budget(["ch-a"])

    def test_every_finding_is_a_readable_sentence(self):
        result = assess_switch_failure_budget(_system(nominal_demand_w=990.0))
        self.assertTrue(result["findings"])
        for note in result["findings"]:
            self.assertIsInstance(note, str)
            self.assertGreater(len(note), 20)


if __name__ == "__main__":
    unittest.main()
