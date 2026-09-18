"""Contract tests for the clause 5.2.7.3.1 limiter failure containment logic."""

import unittest

from e2020_failure_propagation_containment_logic import (
    BACKUP_FUSE,
    BLOCKING_DIODE,
    CONTAINMENT_ACHIEVED,
    CONTAINMENT_BUS_PROPAGATION,
    CONTAINMENT_LATE_CLEARING,
    CONTAINMENT_NEIGHBOUR_PROPAGATION,
    CONTAINMENT_NOT_EVALUATED,
    DEDICATED_RETURN,
    DEFAULT_CONTAINMENT_POLICY,
    FAIL_CONDUCTING,
    FAIL_OPEN,
    FAIL_OSCILLATING,
    FAIL_TO_LIMIT,
    LIMITER_FAILURE_MODES,
    OUTPUT_FILTER,
    REACH_CONTAINED,
    REACH_DISTRIBUTION_BUS,
    REACH_NEIGHBOUR_LINE,
    SERIES_ISOLATION_SWITCH,
    UPSTREAM_LIMITER,
    assess_failure_containment,
    barriers_covering,
    bus_droop_fraction,
    categorize_barrier,
    categorize_failure_mode,
    trace_failure_mode,
    validate_containment_policy,
    worst_reach,
)


def _policy(**overrides):
    policy = dict(DEFAULT_CONTAINMENT_POLICY)
    policy.update(overrides)
    return policy


def _modes(**overrides):
    modes = {
        FAIL_CONDUCTING: {"fault_current_a": 12.0, "clearing_time_ms": 4.0},
        FAIL_OPEN: {"fault_current_a": 0.0},
        FAIL_TO_LIMIT: {"fault_current_a": 18.0, "clearing_time_ms": 6.0},
        FAIL_OSCILLATING: {"fault_current_a": 3.0, "clearing_time_ms": 2.0},
    }
    modes.update(overrides)
    return modes


def _channel(**overrides):
    channel = {
        "barriers": [SERIES_ISOLATION_SWITCH, BACKUP_FUSE, OUTPUT_FILTER],
        "source_impedance_ohm": 0.05,
        "bus_voltage_v": 28.0,
        "failure_modes": _modes(),
    }
    channel.update(overrides)
    return channel


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_containment_policy(DEFAULT_CONTAINMENT_POLICY),
            DEFAULT_CONTAINMENT_POLICY,
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_containment_policy("contained")

    def test_a_neighbour_limit_above_the_bus_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_containment_policy(
                _policy(
                    max_bus_droop_fraction=0.05,
                    max_neighbour_droop_fraction=0.10,
                )
            )

    def test_a_neighbour_limit_equal_to_the_bus_limit_accepted(self):
        policy = _policy(
            max_bus_droop_fraction=0.10, max_neighbour_droop_fraction=0.10
        )
        self.assertIs(validate_containment_policy(policy), policy)

    def test_a_clearing_budget_longer_than_ride_through_rejected(self):
        with self.assertRaises(ValueError):
            validate_containment_policy(
                _policy(max_clearing_time_ms=30.0, bus_ride_through_ms=12.0)
            )

    def test_a_droop_limit_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_containment_policy(_policy(max_bus_droop_fraction=1.0))


class VocabularyTests(unittest.TestCase):
    def test_every_known_failure_mode_round_trips(self):
        for mode in LIMITER_FAILURE_MODES:
            self.assertEqual(categorize_failure_mode(mode), mode)

    def test_an_unrecognised_failure_mode_rejected(self):
        with self.assertRaises(ValueError):
            categorize_failure_mode("fail-warm")

    def test_an_empty_failure_mode_rejected(self):
        with self.assertRaises(ValueError):
            categorize_failure_mode("  ")

    def test_a_known_barrier_round_trips(self):
        self.assertEqual(categorize_barrier(" backup-fuse "), BACKUP_FUSE)

    def test_an_unrecognised_barrier_rejected(self):
        with self.assertRaises(ValueError):
            categorize_barrier("kapton-tape")


class BarrierCoverageTests(unittest.TestCase):
    def test_a_blocking_diode_covers_only_a_conducting_failure(self):
        self.assertEqual(
            barriers_covering(FAIL_CONDUCTING, [BLOCKING_DIODE]),
            (BLOCKING_DIODE,),
        )

    def test_a_blocking_diode_does_nothing_about_an_oscillation(self):
        self.assertEqual(barriers_covering(FAIL_OSCILLATING, [BLOCKING_DIODE]), ())

    def test_a_filter_and_a_dedicated_return_both_cover_an_oscillation(self):
        self.assertEqual(
            barriers_covering(FAIL_OSCILLATING, [OUTPUT_FILTER, DEDICATED_RETURN]),
            (OUTPUT_FILTER, DEDICATED_RETURN),
        )

    def test_an_upstream_limiter_covers_a_loss_of_limiting(self):
        self.assertIn(
            UPSTREAM_LIMITER, barriers_covering(FAIL_TO_LIMIT, [UPSTREAM_LIMITER])
        )

    def test_no_barrier_covers_a_failed_open_line(self):
        self.assertEqual(
            barriers_covering(FAIL_OPEN, [SERIES_ISOLATION_SWITCH, BACKUP_FUSE]),
            (),
        )

    def test_a_barrier_declared_twice_rejected(self):
        with self.assertRaises(ValueError):
            barriers_covering(FAIL_CONDUCTING, [BACKUP_FUSE, BACKUP_FUSE])

    def test_a_non_sequence_barrier_set_rejected(self):
        with self.assertRaises(ValueError):
            barriers_covering(FAIL_CONDUCTING, BACKUP_FUSE)


class DroopTests(unittest.TestCase):
    def test_droop_is_the_ohmic_drop_over_the_bus_voltage(self):
        self.assertAlmostEqual(bus_droop_fraction(14.0, 0.1, 28.0), 0.05, places=9)

    def test_a_zero_fault_current_droops_nothing(self):
        self.assertAlmostEqual(bus_droop_fraction(0.0, 0.1, 28.0), 0.0, places=9)

    def test_a_zero_bus_voltage_rejected(self):
        with self.assertRaises(ValueError):
            bus_droop_fraction(14.0, 0.1, 0.0)

    def test_a_negative_impedance_rejected(self):
        with self.assertRaises(ValueError):
            bus_droop_fraction(14.0, -0.1, 28.0)


class TraceTests(unittest.TestCase):
    def test_a_covered_and_prompt_mode_is_contained(self):
        record = trace_failure_mode(FAIL_CONDUCTING, _channel())
        self.assertEqual(record["reach"], REACH_CONTAINED)
        self.assertIn(SERIES_ISOLATION_SWITCH, record["covering_barriers"])

    def test_a_failed_open_line_never_leaves_itself(self):
        record = trace_failure_mode(FAIL_OPEN, _channel())
        self.assertEqual(record["reach"], REACH_CONTAINED)
        self.assertEqual(record["covering_barriers"], ())

    def test_an_uncovered_hard_fault_reaches_the_bus(self):
        channel = _channel(barriers=[], source_impedance_ohm=0.3)
        record = trace_failure_mode(FAIL_CONDUCTING, channel)
        self.assertEqual(record["reach"], REACH_DISTRIBUTION_BUS)

    def test_an_uncovered_modest_fault_reaches_only_a_neighbour(self):
        channel = _channel(
            barriers=[],
            source_impedance_ohm=0.05,
            failure_modes=_modes(
                **{FAIL_CONDUCTING: {"fault_current_a": 40.0}}
            ),
        )
        record = trace_failure_mode(FAIL_CONDUCTING, channel)
        self.assertAlmostEqual(record["droop_fraction"], 2.0 / 28.0, places=9)
        self.assertEqual(record["reach"], REACH_NEIGHBOUR_LINE)

    def test_a_droop_exactly_on_the_neighbour_limit_stays_contained(self):
        channel = _channel(
            barriers=[],
            source_impedance_ohm=0.1,
            bus_voltage_v=28.0,
            failure_modes=_modes(
                **{FAIL_CONDUCTING: {"fault_current_a": 14.0}}
            ),
        )
        record = trace_failure_mode(FAIL_CONDUCTING, channel)
        self.assertAlmostEqual(
            record["droop_fraction"],
            float(DEFAULT_CONTAINMENT_POLICY["max_neighbour_droop_fraction"]),
            places=9,
        )
        self.assertEqual(record["reach"], REACH_CONTAINED)

    def test_a_barrier_that_acts_too_late_stops_containing(self):
        channel = _channel(
            source_impedance_ohm=0.3,
            failure_modes=_modes(
                **{
                    FAIL_CONDUCTING: {
                        "fault_current_a": 12.0,
                        "clearing_time_ms": 40.0,
                    }
                }
            ),
        )
        record = trace_failure_mode(FAIL_CONDUCTING, channel)
        self.assertEqual(record["reach"], REACH_DISTRIBUTION_BUS)

    def test_an_undeclared_mode_is_not_evaluated(self):
        modes = _modes()
        del modes[FAIL_OSCILLATING]
        record = trace_failure_mode(FAIL_OSCILLATING, _channel(failure_modes=modes))
        self.assertFalse(record["evaluated"])
        self.assertIsNone(record["reach"])

    def test_a_malformed_mode_detail_rejected(self):
        channel = _channel(failure_modes=_modes(**{FAIL_CONDUCTING: 12.0}))
        with self.assertRaises(ValueError):
            trace_failure_mode(FAIL_CONDUCTING, channel)

    def test_a_channel_with_no_failure_modes_mapping_rejected(self):
        with self.assertRaises(ValueError):
            trace_failure_mode(FAIL_CONDUCTING, {"barriers": []})


class WorstReachTests(unittest.TestCase):
    def test_the_furthest_reach_is_the_one_reported(self):
        records = [
            {"reach": REACH_CONTAINED},
            {"reach": REACH_NEIGHBOUR_LINE},
            {"reach": REACH_CONTAINED},
        ]
        self.assertEqual(worst_reach(records), REACH_NEIGHBOUR_LINE)

    def test_an_untraced_mode_does_not_lower_the_reach(self):
        records = [{"reach": None}, {"reach": REACH_DISTRIBUTION_BUS}]
        self.assertEqual(worst_reach(records), REACH_DISTRIBUTION_BUS)

    def test_an_unrecognised_reach_rejected(self):
        with self.assertRaises(ValueError):
            worst_reach([{"reach": "reaches-orbit"}])

    def test_an_empty_record_set_rejected(self):
        with self.assertRaises(ValueError):
            worst_reach([])


class ChannelAssessmentTests(unittest.TestCase):
    def test_a_fully_barriered_channel_is_contained(self):
        result = assess_failure_containment(_channel())
        self.assertEqual(result["verdict"], CONTAINMENT_ACHIEVED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["untraced_modes"], [])

    def test_an_untraced_mode_outranks_everything_else(self):
        modes = _modes()
        del modes[FAIL_TO_LIMIT]
        result = assess_failure_containment(
            _channel(failure_modes=modes, barriers=[], source_impedance_ohm=0.5)
        )
        self.assertEqual(result["verdict"], CONTAINMENT_NOT_EVALUATED)
        self.assertEqual(result["untraced_modes"], [FAIL_TO_LIMIT])

    def test_a_bus_reaching_fault_is_reported_as_bus_propagation(self):
        result = assess_failure_containment(
            _channel(barriers=[], source_impedance_ohm=0.5)
        )
        self.assertEqual(result["verdict"], CONTAINMENT_BUS_PROPAGATION)

    def test_a_neighbour_reaching_fault_is_reported_separately(self):
        result = assess_failure_containment(
            _channel(
                barriers=[],
                source_impedance_ohm=0.1,
                failure_modes=_modes(
                    **{
                        FAIL_CONDUCTING: {"fault_current_a": 20.0},
                        FAIL_TO_LIMIT: {"fault_current_a": 18.0},
                        FAIL_OSCILLATING: {"fault_current_a": 3.0},
                    }
                ),
            )
        )
        self.assertEqual(result["verdict"], CONTAINMENT_NEIGHBOUR_PROPAGATION)

    def test_a_late_barrier_on_an_otherwise_quiet_fault_is_reported(self):
        result = assess_failure_containment(
            _channel(
                source_impedance_ohm=0.001,
                failure_modes=_modes(
                    **{
                        FAIL_CONDUCTING: {
                            "fault_current_a": 12.0,
                            "clearing_time_ms": 40.0,
                        }
                    }
                ),
            )
        )
        self.assertEqual(result["verdict"], CONTAINMENT_LATE_CLEARING)
        self.assertEqual(result["late_modes"], [FAIL_CONDUCTING])

    def test_an_unrecognised_declared_mode_rejected(self):
        modes = _modes()
        modes["fail-smoky"] = {"fault_current_a": 1.0}
        with self.assertRaises(ValueError):
            assess_failure_containment(_channel(failure_modes=modes))

    def test_an_empty_failure_mode_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_failure_containment(_channel(failure_modes={}))

    def test_a_non_mapping_channel_rejected(self):
        with self.assertRaises(ValueError):
            assess_failure_containment(["limiter"])

    def test_every_mode_is_traced_exactly_once(self):
        result = assess_failure_containment(_channel())
        traced = [record["mode"] for record in result["modes"]]
        self.assertEqual(traced, list(LIMITER_FAILURE_MODES))

    def test_every_finding_is_a_readable_sentence(self):
        result = assess_failure_containment(
            _channel(barriers=[], source_impedance_ohm=0.5)
        )
        self.assertTrue(result["findings"])
        for note in result["findings"]:
            self.assertIsInstance(note, str)
            self.assertGreater(len(note), 20)


if __name__ == "__main__":
    unittest.main()
