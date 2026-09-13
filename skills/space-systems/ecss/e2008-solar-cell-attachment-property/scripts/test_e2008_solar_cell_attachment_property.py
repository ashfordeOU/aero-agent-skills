#!/usr/bin/env python3
"""Contract test for the cell-assembly attachment property (offline).

Walks the clause workflow step by step: the as-bonded reference anchor,
the per-stage retention and drop checks, the detachment count that has
to stop the sequence outright, the mission-cycle coverage and the
end-of-life extrapolation, and the retention gate that sentences the
record. This is the gate 3 review evidence for the leaf.
"""

import copy
import unittest

from e2008_solar_cell_attachment_property_logic import (
    ATTACHMENT_NOT_EVALUATED,
    ATTACHMENT_NOT_RETAINED,
    ATTACHMENT_RETAINED,
    DEFAULT_ATTACHMENT_POLICY,
    RECOGNIZED_STAGES,
    REFERENCE_STAGE,
    cycle_coverage,
    evaluate_attachment_property,
    evaluate_stage,
    life_extrapolated_strength_mpa,
    retention_fraction,
    validate_attachment_policy,
)

SOUND_RECORD = {
    "stages": [
        {"stage": REFERENCE_STAGE, "strength_mpa": 0.80, "detached_cell_count": 0},
        {"stage": "humidity-storage", "strength_mpa": 0.76, "detached_cell_count": 0},
        {
            "stage": "solar-array-thermal-cycling",
            "strength_mpa": 0.70,
            "detached_cell_count": 0,
        },
        {
            "stage": "sine-and-random-vibration",
            "strength_mpa": 0.68,
            "detached_cell_count": 0,
        },
        {"stage": "thermal-vacuum-soak", "strength_mpa": 0.66, "detached_cell_count": 0},
    ],
    "tested_thermal_cycles": 8000,
    "mission_thermal_cycles": 6000,
}


def _record(**overrides):
    record = copy.deepcopy(SOUND_RECORD)
    record.update(overrides)
    return record


def _stage(name, strength, detached=0):
    return {
        "stage": name,
        "strength_mpa": strength,
        "detached_cell_count": detached,
    }


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_attachment_policy(DEFAULT_ATTACHMENT_POLICY),
            DEFAULT_ATTACHMENT_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_attachment_policy("default")

    def test_retention_floor_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_ATTACHMENT_POLICY)
        broken["min_retention_fraction"] = 1.4
        with self.assertRaises(ValueError):
            validate_attachment_policy(broken)

    def test_test_factor_below_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_ATTACHMENT_POLICY)
        broken["cycle_test_factor"] = 0.8
        with self.assertRaises(ValueError):
            validate_attachment_policy(broken)

    def test_total_per_decade_loss_rejected(self):
        broken = copy.deepcopy(DEFAULT_ATTACHMENT_POLICY)
        broken["per_decade_loss_fraction"] = 1.0
        with self.assertRaises(ValueError):
            validate_attachment_policy(broken)

    def test_fractional_detached_cell_allowance_rejected(self):
        broken = copy.deepcopy(DEFAULT_ATTACHMENT_POLICY)
        broken["max_detached_cells"] = 0.5
        with self.assertRaises(ValueError):
            validate_attachment_policy(broken)


class RetentionTests(unittest.TestCase):
    def test_unchanged_strength_retains_everything(self):
        self.assertAlmostEqual(retention_fraction(0.8, 0.8), 1.0, places=12)

    def test_halved_strength_retains_half(self):
        self.assertAlmostEqual(retention_fraction(0.4, 0.8), 0.5, places=12)

    def test_zero_reference_strength_rejected(self):
        with self.assertRaises(ValueError):
            retention_fraction(0.4, 0.0)

    def test_non_numeric_stage_strength_rejected(self):
        with self.assertRaises(ValueError):
            retention_fraction("0.4 MPa", 0.8)


class CycleCoverageTests(unittest.TestCase):
    def test_cycles_beyond_the_factored_mission_are_covered(self):
        result = cycle_coverage(8000, 6000, 1.25)
        self.assertAlmostEqual(result["required_cycles"], 7500.0, places=9)
        self.assertTrue(result["covered"])

    def test_coverage_exactly_on_the_requirement_is_covered(self):
        result = cycle_coverage(7500, 6000, 1.25)
        self.assertAlmostEqual(result["coverage_ratio"], 1.0, places=9)
        self.assertTrue(result["covered"])

    def test_short_test_is_not_covered(self):
        result = cycle_coverage(3000, 6000, 1.25)
        self.assertAlmostEqual(result["coverage_ratio"], 0.4, places=9)
        self.assertFalse(result["covered"])

    def test_zero_tested_cycles_rejected(self):
        with self.assertRaises(ValueError):
            cycle_coverage(0, 6000, 1.25)

    def test_fractional_mission_cycles_rejected(self):
        with self.assertRaises(ValueError):
            cycle_coverage(8000, 6000.5, 1.25)

    def test_test_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            cycle_coverage(8000, 6000, 0.9)


class LifeExtrapolationTests(unittest.TestCase):
    def test_a_test_that_reached_the_mission_keeps_its_strength(self):
        self.assertAlmostEqual(
            life_extrapolated_strength_mpa(0.66, 6000, 6000, 0.10), 0.66, places=12
        )

    def test_a_test_beyond_the_mission_never_credits_recovery(self):
        self.assertAlmostEqual(
            life_extrapolated_strength_mpa(0.66, 9000, 6000, 0.10), 0.66, places=12
        )

    def test_one_decade_short_costs_one_decade_of_loss(self):
        self.assertAlmostEqual(
            life_extrapolated_strength_mpa(0.50, 1000, 10000, 0.10),
            0.45,
            places=9,
        )

    def test_two_decades_short_compound_the_loss(self):
        self.assertAlmostEqual(
            life_extrapolated_strength_mpa(0.50, 100, 10000, 0.10),
            0.405,
            places=9,
        )

    def test_zero_loss_leaves_the_strength_alone(self):
        self.assertAlmostEqual(
            life_extrapolated_strength_mpa(0.50, 100, 10000, 0.0), 0.50, places=9
        )

    def test_total_loss_fraction_rejected(self):
        with self.assertRaises(ValueError):
            life_extrapolated_strength_mpa(0.50, 100, 10000, 1.0)


class StageTests(unittest.TestCase):
    def test_gentle_stage_is_retained(self):
        result = evaluate_stage(
            _stage("humidity-storage", 0.76), 0.80, 0.80, DEFAULT_ATTACHMENT_POLICY
        )
        self.assertTrue(result["retained"])
        self.assertAlmostEqual(result["retention_fraction"], 0.95, places=9)

    def test_retention_exactly_on_the_floor_is_retained(self):
        floor = DEFAULT_ATTACHMENT_POLICY["min_retention_fraction"]
        result = evaluate_stage(
            _stage("thermal-vacuum-soak", 0.80 * floor),
            0.80,
            0.80 * floor,
            DEFAULT_ATTACHMENT_POLICY,
        )
        self.assertAlmostEqual(result["retention_fraction"], floor, places=9)
        self.assertTrue(result["retained"])

    def test_stage_drop_exactly_on_the_allowance_is_retained(self):
        allowance = DEFAULT_ATTACHMENT_POLICY["max_stage_drop_fraction"]
        previous = 1.0
        result = evaluate_stage(
            _stage("acoustic-noise", previous * (1.0 - allowance)),
            1.0,
            previous,
            DEFAULT_ATTACHMENT_POLICY,
        )
        self.assertAlmostEqual(result["stage_drop_fraction"], allowance, places=9)
        self.assertTrue(result["retained"])

    def test_a_detached_cell_assembly_fails_the_stage(self):
        result = evaluate_stage(
            _stage("solar-array-thermal-cycling", 0.76, detached=1),
            0.80,
            0.80,
            DEFAULT_ATTACHMENT_POLICY,
        )
        self.assertFalse(result["retained"])
        self.assertTrue(any("came off" in note for note in result["findings"]))

    def test_a_strength_gain_gives_no_negative_drop(self):
        result = evaluate_stage(
            _stage("humidity-storage", 0.85), 0.80, 0.80, DEFAULT_ATTACHMENT_POLICY
        )
        self.assertAlmostEqual(result["stage_drop_fraction"], 0.0, places=12)

    def test_every_recognized_stage_is_accepted(self):
        for name in RECOGNIZED_STAGES:
            result = evaluate_stage(
                _stage(name, 0.76), 0.80, 0.80, DEFAULT_ATTACHMENT_POLICY
            )
            self.assertEqual(result["stage"], name)

    def test_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_stage(
                _stage("shaken-about", 0.76), 0.80, 0.80, DEFAULT_ATTACHMENT_POLICY
            )

    def test_negative_detached_count_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_stage(
                _stage("humidity-storage", 0.76, detached=-1),
                0.80,
                0.80,
                DEFAULT_ATTACHMENT_POLICY,
            )


class AttachmentPropertyTests(unittest.TestCase):
    def test_sound_sequence_retains_the_attachment(self):
        result = evaluate_attachment_property(SOUND_RECORD)
        self.assertEqual(result["verdict"], ATTACHMENT_RETAINED)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["total_detached_cells"], 0)
        self.assertAlmostEqual(result["final_strength_mpa"], 0.66, places=12)

    def test_life_strength_equals_the_final_measurement_when_cycles_are_covered(self):
        result = evaluate_attachment_property(SOUND_RECORD)
        self.assertAlmostEqual(result["life_strength_mpa"], 0.66, places=12)
        self.assertTrue(result["cycle_coverage"]["covered"])

    def test_one_detachment_anywhere_breaks_the_property(self):
        record = _record()
        record["stages"][2]["detached_cell_count"] = 1
        result = evaluate_attachment_property(record)
        self.assertEqual(result["verdict"], ATTACHMENT_NOT_RETAINED)
        self.assertEqual(result["total_detached_cells"], 1)
        self.assertFalse(result["compliant"])

    def test_a_detachment_at_the_reference_is_reported(self):
        record = _record()
        record["stages"][0]["detached_cell_count"] = 2
        result = evaluate_attachment_property(record)
        self.assertEqual(result["total_detached_cells"], 2)
        self.assertTrue(any("already off" in note for note in result["findings"]))

    def test_overall_retention_below_the_floor_fails(self):
        record = _record()
        record["stages"][-1]["strength_mpa"] = 0.50
        result = evaluate_attachment_property(record)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["worst_retention_fraction"], 0.625, places=9)

    def test_a_single_punishing_stage_fails_the_per_stage_allowance(self):
        record = _record()
        record["stages"][2]["strength_mpa"] = 0.58
        record["stages"][3]["strength_mpa"] = 0.575
        record["stages"][4]["strength_mpa"] = 0.57
        result = evaluate_attachment_property(record)
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("per-stage allowance" in note for note in result["findings"])
        )

    def test_short_cycling_fails_the_life_coverage(self):
        record = _record(tested_thermal_cycles=3000)
        result = evaluate_attachment_property(record)
        self.assertFalse(result["compliant"])
        self.assertFalse(result["cycle_coverage"]["covered"])
        self.assertTrue(
            any("cover only" in note for note in result["findings"])
        )

    def test_extrapolation_can_take_the_end_of_life_below_the_minimum(self):
        policy = copy.deepcopy(DEFAULT_ATTACHMENT_POLICY)
        policy["per_decade_loss_fraction"] = 0.30
        record = _record(tested_thermal_cycles=100, mission_thermal_cycles=100000)
        result = evaluate_attachment_property(record, policy)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["life_strength_mpa"], 0.66 * 0.343, places=9)
        self.assertTrue(
            any("end-of-life strength" in note for note in result["findings"])
        )

    def test_missing_cycle_counts_leave_life_undemonstrated(self):
        record = _record()
        del record["tested_thermal_cycles"]
        result = evaluate_attachment_property(record)
        self.assertIsNone(result["cycle_coverage"])
        self.assertIsNone(result["life_strength_mpa"])
        self.assertFalse(result["compliant"])

    def test_reference_only_record_is_not_evaluated(self):
        record = {"stages": [_stage(REFERENCE_STAGE, 0.80)]}
        result = evaluate_attachment_property(record)
        self.assertEqual(result["verdict"], ATTACHMENT_NOT_EVALUATED)
        self.assertIsNone(result["compliant"])
        self.assertTrue(
            any("not demonstrated" in note for note in result["findings"])
        )

    def test_sequence_not_starting_at_the_reference_rejected(self):
        record = {"stages": [_stage("humidity-storage", 0.76)]}
        with self.assertRaises(ValueError):
            evaluate_attachment_property(record)

    def test_a_second_reference_stage_rejected(self):
        record = _record()
        record["stages"].append(_stage(REFERENCE_STAGE, 0.66))
        with self.assertRaises(ValueError):
            evaluate_attachment_property(record)

    def test_empty_stage_sequence_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_attachment_property({"stages": []})

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_attachment_property("all cells still on")


if __name__ == "__main__":
    unittest.main()
