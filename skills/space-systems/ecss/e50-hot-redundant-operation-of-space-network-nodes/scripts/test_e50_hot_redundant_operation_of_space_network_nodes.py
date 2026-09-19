"""Contract tests for the clause 5.7.1.6 hot redundant network node logic."""

import copy
import unittest

from e50_hot_redundant_operation_of_space_network_nodes_logic import (
    HOT_REDUNDANT,
    NETWORK_CONFLICT,
    NOT_HOT_REDUNDANT,
    OUTAGE_EXCEEDED,
    SINGLE_POINT_OF_FAILURE,
    assess_hot_redundancy,
    failover_outage_s,
    is_hot_redundant,
    network_conflicts,
    required_detection_s,
    single_point_segment,
    validate_nonnegative,
    validate_unit,
)

NOMINAL = {
    "powered": True,
    "attached": True,
    "segments": ["bus-a", "bus-b"],
    "address": 17,
    "drives_medium": True,
}
REDUNDANT = {
    "powered": True,
    "attached": True,
    "segments": ["bus-a", "bus-b"],
    "address": 18,
    "drives_medium": False,
}
DETECTION = 0.5
SWITCHOVER = 0.2
REINIT = 1.3


def variant(base, **changes):
    unit = copy.deepcopy(base)
    unit.update(changes)
    return unit


class ValidationTests(unittest.TestCase):
    def test_non_mapping_unit_rejected(self):
        with self.assertRaises(ValueError):
            validate_unit("nominal")

    def test_missing_field_rejected(self):
        broken = copy.deepcopy(NOMINAL)
        del broken["attached"]
        with self.assertRaises(ValueError):
            validate_unit(broken)

    def test_non_boolean_power_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_unit(variant(NOMINAL, powered="yes"))

    def test_segment_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_unit(variant(NOMINAL, segments="bus-a"))

    def test_empty_segment_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_unit(variant(NOMINAL, segments=[]))

    def test_blank_segment_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_unit(variant(NOMINAL, segments=["  "]))

    def test_boolean_address_rejected(self):
        with self.assertRaises(ValueError):
            validate_unit(variant(NOMINAL, address=True))

    def test_blank_address_rejected(self):
        with self.assertRaises(ValueError):
            validate_unit(variant(NOMINAL, address="  "))

    def test_segments_are_normalised_to_a_set(self):
        unit = validate_unit(variant(NOMINAL, segments=[" bus-a ", "bus-a"]))
        self.assertEqual(sorted(unit["segments"]), ["bus-a"])

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_nonnegative(-0.1, "detection_s")


class HotRedundancyTests(unittest.TestCase):
    def test_both_powered_and_attached_is_hot(self):
        self.assertTrue(is_hot_redundant(NOMINAL, REDUNDANT))

    def test_an_unpowered_standby_is_not_hot(self):
        self.assertFalse(is_hot_redundant(NOMINAL, variant(REDUNDANT, powered=False)))

    def test_a_detached_standby_is_not_hot(self):
        self.assertFalse(is_hot_redundant(NOMINAL, variant(REDUNDANT, attached=False)))


class ConflictTests(unittest.TestCase):
    def test_an_inhibited_standby_raises_no_conflict(self):
        self.assertEqual(network_conflicts(NOMINAL, REDUNDANT), [])

    def test_two_live_transmitters_conflict(self):
        conflicts = network_conflicts(NOMINAL, variant(REDUNDANT, drives_medium=True))
        self.assertTrue(any("two transmitters" in c for c in conflicts))

    def test_a_shared_address_blocks_standby_monitoring(self):
        conflicts = network_conflicts(NOMINAL, variant(REDUNDANT, address=17))
        self.assertTrue(any("answer to address" in c for c in conflicts))

    def test_both_faults_are_reported_together(self):
        conflicts = network_conflicts(
            NOMINAL, variant(REDUNDANT, address=17, drives_medium=True)
        )
        self.assertEqual(len(conflicts), 2)

    def test_a_detached_standby_cannot_conflict(self):
        conflicts = network_conflicts(
            NOMINAL, variant(REDUNDANT, attached=False, address=17, drives_medium=True)
        )
        self.assertEqual(conflicts, [])


class SegmentTests(unittest.TestCase):
    def test_a_cross_strapped_pair_has_no_single_point(self):
        self.assertIsNone(single_point_segment(NOMINAL, REDUNDANT))

    def test_one_shared_segment_is_a_single_point(self):
        self.assertEqual(
            single_point_segment(
                variant(NOMINAL, segments=["bus-a"]),
                variant(REDUNDANT, segments=["bus-a"]),
            ),
            "bus-a",
        )

    def test_one_unit_on_two_segments_removes_the_single_point(self):
        self.assertIsNone(
            single_point_segment(NOMINAL, variant(REDUNDANT, segments=["bus-a"]))
        )

    def test_units_on_different_single_segments_are_safe(self):
        self.assertIsNone(
            single_point_segment(
                variant(NOMINAL, segments=["bus-a"]),
                variant(REDUNDANT, segments=["bus-b"]),
            )
        )


class OutageTests(unittest.TestCase):
    def test_outage_is_the_sum_of_the_chain(self):
        self.assertAlmostEqual(
            failover_outage_s(DETECTION, SWITCHOVER, REINIT), 2.0, places=9
        )

    def test_required_detection_is_the_budget_headroom(self):
        self.assertAlmostEqual(
            required_detection_s(2.0, SWITCHOVER, REINIT), DETECTION, places=9
        )

    def test_a_budget_spent_by_the_takeover_admits_no_detection(self):
        self.assertIsNone(required_detection_s(1.0, SWITCHOVER, REINIT))

    def test_required_detection_actually_fits_the_budget(self):
        headroom = required_detection_s(2.0, SWITCHOVER, REINIT)
        self.assertAlmostEqual(
            failover_outage_s(headroom, SWITCHOVER, REINIT), 2.0, places=9
        )


class AssessTests(unittest.TestCase):
    def test_a_sound_pair_is_hot_redundant(self):
        result = assess_hot_redundancy(
            NOMINAL, REDUNDANT, DETECTION, SWITCHOVER, REINIT, 2.0
        )
        self.assertEqual(result["verdict"], HOT_REDUNDANT)
        self.assertTrue(result["cross_strapped"])

    def test_an_outage_exactly_at_budget_passes(self):
        result = assess_hot_redundancy(
            NOMINAL, REDUNDANT, DETECTION, SWITCHOVER, REINIT, 2.0
        )
        self.assertTrue(result["within_outage_budget"])

    def test_a_cold_spare_fails_the_first_item(self):
        result = assess_hot_redundancy(
            NOMINAL, variant(REDUNDANT, powered=False), DETECTION, SWITCHOVER,
            REINIT, 2.0,
        )
        self.assertEqual(result["verdict"], NOT_HOT_REDUNDANT)
        self.assertTrue(any("cold spare" in f for f in result["findings"]))

    def test_a_warm_spare_is_named_as_such(self):
        result = assess_hot_redundancy(
            NOMINAL, variant(REDUNDANT, attached=False), DETECTION, SWITCHOVER,
            REINIT, 2.0,
        )
        self.assertTrue(any("warm spare" in f for f in result["findings"]))

    def test_a_live_standby_transmitter_is_a_network_conflict(self):
        result = assess_hot_redundancy(
            NOMINAL, variant(REDUNDANT, drives_medium=True), DETECTION,
            SWITCHOVER, REINIT, 2.0,
        )
        self.assertEqual(result["verdict"], NETWORK_CONFLICT)

    def test_a_conflict_outranks_the_outage_budget(self):
        result = assess_hot_redundancy(
            NOMINAL, variant(REDUNDANT, drives_medium=True), DETECTION,
            SWITCHOVER, REINIT, 0.1,
        )
        self.assertEqual(result["verdict"], NETWORK_CONFLICT)

    def test_a_shared_single_segment_is_reported(self):
        result = assess_hot_redundancy(
            variant(NOMINAL, segments=["bus-a"]),
            variant(REDUNDANT, segments=["bus-a"]),
            DETECTION, SWITCHOVER, REINIT, 2.0,
        )
        self.assertEqual(result["verdict"], SINGLE_POINT_OF_FAILURE)
        self.assertFalse(result["cross_strapped"])

    def test_a_slow_failover_is_reported_with_its_remedy(self):
        result = assess_hot_redundancy(
            NOMINAL, REDUNDANT, DETECTION, SWITCHOVER, REINIT, 1.8
        )
        self.assertEqual(result["verdict"], OUTAGE_EXCEEDED)
        self.assertTrue(any("detection has to come down" in f for f in result["findings"]))

    def test_a_takeover_that_alone_busts_the_budget_says_so(self):
        result = assess_hot_redundancy(
            NOMINAL, REDUNDANT, DETECTION, SWITCHOVER, REINIT, 1.0
        )
        self.assertEqual(result["verdict"], OUTAGE_EXCEEDED)
        self.assertTrue(any("no detection time fits" in f for f in result["findings"]))

    def test_an_undeclared_budget_is_flagged_not_assumed(self):
        result = assess_hot_redundancy(
            NOMINAL, REDUNDANT, DETECTION, SWITCHOVER, REINIT
        )
        self.assertEqual(result["verdict"], HOT_REDUNDANT)
        self.assertTrue(any("no outage budget" in f for f in result["findings"]))

    def test_a_malformed_unit_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_hot_redundancy(NOMINAL, {"powered": True})

    def test_a_negative_switchover_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_hot_redundancy(NOMINAL, REDUNDANT, DETECTION, -0.1, REINIT, 2.0)


if __name__ == "__main__":
    unittest.main()
