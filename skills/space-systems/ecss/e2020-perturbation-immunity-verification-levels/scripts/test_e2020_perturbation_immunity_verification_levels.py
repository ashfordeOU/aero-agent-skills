#!/usr/bin/env python3
"""Contract test for the perturbation immunity verification split (offline)."""

import copy
import unittest

from e2020_perturbation_immunity_verification_levels_logic import (
    ADVISORY_SPACECRAFT_LOAD,
    ADVISORY_UNIT_SHARE,
    DEFAULT_ALLOCATION_POLICY,
    FINDING_BAND_GAP,
    FINDING_NO_LEVEL,
    LEVEL_NONE,
    LEVEL_SPACECRAFT,
    LEVEL_UNIT,
    REASON_AMPLITUDE,
    REASON_COUPLING,
    REASON_FREQUENCY,
    REASON_HARNESS,
    REASON_SOURCE_Z,
    VERDICT_COMPLETE,
    VERDICT_INCOMPLETE,
    allocate_immunity_verification,
    allocate_requirement,
    bench_representativeness_blockers,
    facility_can_reproduce,
    merge_frequency_intervals,
    uncovered_band_slices,
    validate_allocation_policy,
    validate_requirement,
    validate_requirement_set,
)

BAND_LOW_HZ = 10.0
BAND_HIGH_HZ = 1.0e7

CLEAN_LOW = {
    "id": "imm-01",
    "perturbation": "conducted bus ripple",
    "amplitude": 1.0,
    "frequency_low_hz": 10.0,
    "frequency_high_hz": 1.0e3,
    "needs_flight_harness": False,
    "needs_bus_source_impedance": False,
    "needs_cross_user_coupling": False,
}

CLEAN_MID = {
    "id": "imm-02",
    "perturbation": "conducted bus ripple",
    "amplitude": 2.0,
    "frequency_low_hz": 1.0e3,
    "frequency_high_hz": 1.0e5,
    "needs_flight_harness": False,
    "needs_bus_source_impedance": False,
    "needs_cross_user_coupling": False,
}

HARNESS_ITEM = {
    "id": "imm-03",
    "perturbation": "harness-borne switching transient",
    "amplitude": 4.0,
    "frequency_low_hz": 1.0e5,
    "frequency_high_hz": 1.0e6,
    "needs_flight_harness": True,
    "needs_bus_source_impedance": False,
    "needs_cross_user_coupling": False,
}

SOURCE_Z_ITEM = {
    "id": "imm-04",
    "perturbation": "bus notching from a neighbouring user",
    "amplitude": 6.0,
    "frequency_low_hz": 1.0e6,
    "frequency_high_hz": 1.0e7,
    "needs_flight_harness": False,
    "needs_bus_source_impedance": True,
    "needs_cross_user_coupling": False,
}

NOMINAL_SET = (CLEAN_LOW, CLEAN_MID, HARNESS_ITEM, SOURCE_Z_ITEM)


def _item(base=CLEAN_LOW, **overrides):
    row = copy.deepcopy(base)
    row.update(overrides)
    return row


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_allocation_policy(DEFAULT_ALLOCATION_POLICY),
            DEFAULT_ALLOCATION_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_allocation_policy("default")

    def test_zero_bench_amplitude_rejected(self):
        policy = dict(DEFAULT_ALLOCATION_POLICY, unit_bench_amplitude_limit=0.0)
        with self.assertRaises(ValueError):
            validate_allocation_policy(policy)

    def test_facility_weaker_than_the_bench_rejected(self):
        policy = dict(DEFAULT_ALLOCATION_POLICY, facility_amplitude_limit=1.0)
        with self.assertRaises(ValueError):
            validate_allocation_policy(policy)

    def test_facility_frequency_below_the_bench_ceiling_rejected(self):
        policy = dict(DEFAULT_ALLOCATION_POLICY, facility_frequency_high_hz=1.0e3)
        with self.assertRaises(ValueError):
            validate_allocation_policy(policy)

    def test_negative_advisory_ceiling_rejected(self):
        policy = dict(DEFAULT_ALLOCATION_POLICY, spacecraft_level_advisory_ceiling=-1)
        with self.assertRaises(ValueError):
            validate_allocation_policy(policy)

    def test_boolean_advisory_ceiling_rejected(self):
        policy = dict(DEFAULT_ALLOCATION_POLICY, spacecraft_level_advisory_ceiling=True)
        with self.assertRaises(ValueError):
            validate_allocation_policy(policy)

    def test_share_floor_above_one_rejected(self):
        policy = dict(DEFAULT_ALLOCATION_POLICY, unit_level_share_floor=1.4)
        with self.assertRaises(ValueError):
            validate_allocation_policy(policy)


class RequirementValidationTests(unittest.TestCase):
    def test_nominal_requirement_validates(self):
        row = validate_requirement(CLEAN_LOW)
        self.assertEqual(row["id"], "imm-01")
        self.assertAlmostEqual(row["frequency_high_hz"], 1.0e3, places=9)

    def test_missing_field_rejected(self):
        row = _item()
        del row["needs_cross_user_coupling"]
        with self.assertRaises(ValueError):
            validate_requirement(row)

    def test_inverted_frequency_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(_item(frequency_low_hz=1.0e6, frequency_high_hz=10.0))

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(_item(needs_flight_harness="yes"))

    def test_zero_amplitude_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(_item(amplitude=0.0))

    def test_blank_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(_item(id="   "))

    def test_blank_perturbation_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(_item(perturbation=""))

    def test_repeated_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement_set([_item(), _item()])

    def test_empty_requirement_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement_set([])

    def test_mapping_instead_of_a_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement_set(_item())


class BlockerTests(unittest.TestCase):
    def test_clean_requirement_has_no_blockers(self):
        self.assertEqual(bench_representativeness_blockers(CLEAN_LOW), ())

    def test_flight_harness_flag_blocks_the_bench(self):
        self.assertIn(REASON_HARNESS, bench_representativeness_blockers(HARNESS_ITEM))

    def test_source_impedance_and_coupling_are_both_reported(self):
        row = _item(needs_bus_source_impedance=True, needs_cross_user_coupling=True)
        reasons = bench_representativeness_blockers(row)
        self.assertIn(REASON_SOURCE_Z, reasons)
        self.assertIn(REASON_COUPLING, reasons)

    def test_amplitude_over_the_bench_limit_blocks(self):
        row = _item(amplitude=12.0)
        self.assertIn(REASON_AMPLITUDE, bench_representativeness_blockers(row))

    def test_amplitude_exactly_on_the_bench_limit_does_not_block(self):
        limit = float(DEFAULT_ALLOCATION_POLICY["unit_bench_amplitude_limit"])
        self.assertAlmostEqual(limit, 8.0, places=9)
        row = _item(amplitude=limit)
        self.assertEqual(bench_representativeness_blockers(row), ())

    def test_frequency_over_the_bench_ceiling_blocks(self):
        row = _item(frequency_low_hz=1.0e6, frequency_high_hz=2.0e7)
        self.assertIn(REASON_FREQUENCY, bench_representativeness_blockers(row))

    def test_facility_reproduces_at_its_exact_amplitude_limit(self):
        limit = float(DEFAULT_ALLOCATION_POLICY["facility_amplitude_limit"])
        self.assertAlmostEqual(limit, 40.0, places=9)
        self.assertTrue(facility_can_reproduce(_item(amplitude=limit)))

    def test_facility_refuses_an_amplitude_beyond_its_limit(self):
        self.assertFalse(facility_can_reproduce(_item(amplitude=60.0)))


class AllocationTests(unittest.TestCase):
    def test_clean_requirement_goes_to_unit_level(self):
        result = allocate_requirement(CLEAN_LOW)
        self.assertEqual(result["level"], LEVEL_UNIT)
        self.assertEqual(result["reasons"], ())
        self.assertTrue(result["verified"])

    def test_harness_dependent_requirement_goes_to_spacecraft_level(self):
        result = allocate_requirement(HARNESS_ITEM)
        self.assertEqual(result["level"], LEVEL_SPACECRAFT)
        self.assertIn(REASON_HARNESS, result["reasons"])
        self.assertTrue(result["verified"])

    def test_requirement_beyond_both_levels_is_unplaced(self):
        result = allocate_requirement(_item(amplitude=60.0))
        self.assertEqual(result["level"], LEVEL_NONE)
        self.assertFalse(result["verified"])

    def test_unplaced_requirement_carries_a_finding(self):
        result = allocate_requirement(_item(amplitude=60.0))
        self.assertTrue(any(FINDING_NO_LEVEL in f for f in result["findings"]))

    def test_a_placed_requirement_carries_no_finding(self):
        self.assertEqual(allocate_requirement(SOURCE_Z_ITEM)["findings"], [])

    def test_allocation_keeps_the_requirement_band(self):
        result = allocate_requirement(CLEAN_MID)
        self.assertAlmostEqual(result["frequency_low_hz"], 1.0e3, places=9)
        self.assertAlmostEqual(result["frequency_high_hz"], 1.0e5, places=9)


class IntervalTests(unittest.TestCase):
    def test_touching_intervals_merge(self):
        self.assertEqual(
            merge_frequency_intervals([(10.0, 1.0e3), (1.0e3, 1.0e5)]),
            ((10.0, 1.0e5),),
        )

    def test_overlapping_intervals_merge(self):
        self.assertEqual(
            merge_frequency_intervals([(10.0, 5.0e3), (1.0e3, 1.0e5)]),
            ((10.0, 1.0e5),),
        )

    def test_disjoint_intervals_stay_apart(self):
        self.assertEqual(
            merge_frequency_intervals([(1.0e4, 1.0e5), (10.0, 1.0e3)]),
            ((10.0, 1.0e3), (1.0e4, 1.0e5)),
        )

    def test_inverted_interval_rejected(self):
        with self.assertRaises(ValueError):
            merge_frequency_intervals([(1.0e5, 10.0)])

    def test_interval_of_the_wrong_arity_rejected(self):
        with self.assertRaises(ValueError):
            merge_frequency_intervals([(10.0, 100.0, 1000.0)])

    def test_gap_between_two_intervals_is_reported(self):
        gaps = uncovered_band_slices(
            [(10.0, 1.0e3), (1.0e5, 1.0e7)], BAND_LOW_HZ, BAND_HIGH_HZ
        )
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0][0], 1.0e3, places=9)
        self.assertAlmostEqual(gaps[0][1], 1.0e5, places=9)

    def test_full_coverage_reports_no_gap(self):
        self.assertEqual(
            uncovered_band_slices([(10.0, 1.0e7)], BAND_LOW_HZ, BAND_HIGH_HZ), ()
        )

    def test_coverage_ending_exactly_on_the_upper_edge_leaves_no_gap(self):
        gaps = uncovered_band_slices(
            [(BAND_LOW_HZ, BAND_HIGH_HZ)], BAND_LOW_HZ, BAND_HIGH_HZ
        )
        self.assertEqual(gaps, ())

    def test_gap_at_the_top_of_the_band_is_reported(self):
        gaps = uncovered_band_slices([(10.0, 1.0e5)], BAND_LOW_HZ, BAND_HIGH_HZ)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0][1], BAND_HIGH_HZ, places=9)

    def test_no_coverage_at_all_leaves_the_whole_band_open(self):
        gaps = uncovered_band_slices([], BAND_LOW_HZ, BAND_HIGH_HZ)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0][0], BAND_LOW_HZ, places=9)

    def test_band_that_does_not_ascend_rejected(self):
        with self.assertRaises(ValueError):
            uncovered_band_slices([(10.0, 100.0)], 1.0e6, 1.0e3)


class CampaignTests(unittest.TestCase):
    def test_nominal_set_is_complete(self):
        result = allocate_immunity_verification(
            NOMINAL_SET, BAND_LOW_HZ, BAND_HIGH_HZ
        )
        self.assertEqual(result["verdict"], VERDICT_COMPLETE)
        self.assertEqual(result["findings"], [])

    def test_split_follows_the_representativeness_flags(self):
        result = allocate_immunity_verification(
            NOMINAL_SET, BAND_LOW_HZ, BAND_HIGH_HZ
        )
        self.assertEqual(result["unit_level"], ["imm-01", "imm-02"])
        self.assertEqual(result["spacecraft_level"], ["imm-03", "imm-04"])
        self.assertEqual(result["unplaced"], [])

    def test_unit_share_exactly_on_the_floor_raises_no_advisory(self):
        result = allocate_immunity_verification(
            NOMINAL_SET, BAND_LOW_HZ, BAND_HIGH_HZ
        )
        self.assertAlmostEqual(result["unit_level_share"], 0.5, places=9)
        self.assertFalse(any(ADVISORY_UNIT_SHARE in a for a in result["advisories"]))

    def test_verified_intervals_are_merged_into_one_span(self):
        result = allocate_immunity_verification(
            NOMINAL_SET, BAND_LOW_HZ, BAND_HIGH_HZ
        )
        self.assertEqual(len(result["verified_intervals"]), 1)
        self.assertAlmostEqual(result["verified_intervals"][0][0], 10.0, places=9)
        self.assertAlmostEqual(result["verified_intervals"][0][1], 1.0e7, places=9)

    def test_a_missing_slice_turns_the_verdict_incomplete(self):
        result = allocate_immunity_verification(
            (CLEAN_LOW, HARNESS_ITEM, SOURCE_Z_ITEM), BAND_LOW_HZ, BAND_HIGH_HZ
        )
        self.assertEqual(result["verdict"], VERDICT_INCOMPLETE)
        self.assertTrue(any(FINDING_BAND_GAP in f for f in result["findings"]))

    def test_an_unplaced_requirement_turns_the_verdict_incomplete(self):
        heavy = _item(base=SOURCE_Z_ITEM, id="imm-09", amplitude=90.0)
        result = allocate_immunity_verification(
            (CLEAN_LOW, CLEAN_MID, HARNESS_ITEM, heavy), BAND_LOW_HZ, BAND_HIGH_HZ
        )
        self.assertEqual(result["verdict"], VERDICT_INCOMPLETE)
        self.assertEqual(result["unplaced"], ["imm-09"])
        self.assertTrue(any(FINDING_NO_LEVEL in f for f in result["findings"]))

    def test_a_crowded_spacecraft_slot_raises_an_advisory(self):
        crowd = [
            _item(base=HARNESS_ITEM, id="imm-1%d" % n, frequency_low_hz=1.0e5)
            for n in range(5)
        ]
        result = allocate_immunity_verification(
            [CLEAN_LOW, CLEAN_MID] + crowd, BAND_LOW_HZ, BAND_HIGH_HZ
        )
        self.assertEqual(len(result["spacecraft_level"]), 5)
        self.assertTrue(
            any(ADVISORY_SPACECRAFT_LOAD in a for a in result["advisories"])
        )

    def test_a_low_unit_share_raises_an_advisory(self):
        result = allocate_immunity_verification(
            (CLEAN_LOW, HARNESS_ITEM, SOURCE_Z_ITEM), BAND_LOW_HZ, BAND_HIGH_HZ
        )
        self.assertLess(result["unit_level_share"], 0.5)
        self.assertTrue(any(ADVISORY_UNIT_SHARE in a for a in result["advisories"]))

    def test_every_requirement_gets_an_allocation_row(self):
        result = allocate_immunity_verification(
            NOMINAL_SET, BAND_LOW_HZ, BAND_HIGH_HZ
        )
        self.assertEqual(len(result["allocations"]), len(NOMINAL_SET))

    def test_a_broken_requirement_set_is_refused(self):
        with self.assertRaises(ValueError):
            allocate_immunity_verification(
                (CLEAN_LOW, _item(amplitude=-1.0, id="imm-bad")),
                BAND_LOW_HZ,
                BAND_HIGH_HZ,
            )

    def test_a_broken_policy_is_refused(self):
        with self.assertRaises(ValueError):
            allocate_immunity_verification(
                NOMINAL_SET,
                BAND_LOW_HZ,
                BAND_HIGH_HZ,
                dict(DEFAULT_ALLOCATION_POLICY, unit_level_share_floor=-0.2),
            )


if __name__ == "__main__":
    unittest.main()
