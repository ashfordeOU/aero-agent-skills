"""Contract tests for the clause 5.2.5.3.1 shared-protection redundancy logic."""

import unittest

from e2020_centralised_undervoltage_protection_redundancy_logic import (
    MIN_SHARED_LIMITERS,
    architecture_units,
    assess_centralised_protection,
    loss_single_points,
    protected_limiters,
    spurious_single_points,
    stage_functional,
    stage_limiters,
    validate_architecture,
)

LIMITERS = ["LCL-1", "LCL-2", "LCL-3"]

# Two-of-three at every stage: one unit can be lost and one can fail active
# without either reaching the served limiters.
TOLERANT = {
    "served_limiters": list(LIMITERS),
    "stages": [
        {"name": "bus-sensing", "units": ["SENSE-A", "SENSE-B", "SENSE-C"], "vote": 2},
        {"name": "trip-distribution", "units": ["DIST-A", "DIST-B", "DIST-C"], "vote": 2},
    ],
}

# One-of-two: survives a lost unit, but either unit alone can command the trip.
OR_VOTED = {
    "served_limiters": list(LIMITERS),
    "stages": [
        {"name": "bus-sensing", "units": ["SENSE-A", "SENSE-B"], "vote": 1},
    ],
}

# Two-of-two: nothing trips spuriously, but either loss disables protection.
AND_VOTED = {
    "served_limiters": list(LIMITERS),
    "stages": [
        {"name": "bus-sensing", "units": ["SENSE-A", "SENSE-B"], "vote": 2},
    ],
}

SIMPLEX = {
    "served_limiters": list(LIMITERS),
    "stages": [
        {"name": "bus-sensing", "units": ["SENSE-A"], "vote": 1},
    ],
}


def tolerant_plus(extra_stage):
    spec = {
        "served_limiters": list(LIMITERS),
        "stages": [dict(s) for s in TOLERANT["stages"]],
    }
    spec["stages"].append(extra_stage)
    return spec


class ValidationTests(unittest.TestCase):
    def test_valid_architecture_returns_limiters_and_stages(self):
        limiters, stages = validate_architecture(TOLERANT)
        self.assertEqual(limiters, LIMITERS)
        self.assertEqual(len(stages), 2)

    def test_stage_without_serves_defaults_to_every_limiter(self):
        _, stages = validate_architecture(TOLERANT)
        self.assertEqual(stages[0]["serves"], LIMITERS)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            validate_architecture(["LCL-1"])

    def test_missing_stages_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_architecture({"served_limiters": list(LIMITERS)})

    def test_empty_limiter_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_architecture({"served_limiters": [], "stages": TOLERANT["stages"]})

    def test_duplicate_limiter_rejected(self):
        with self.assertRaises(ValueError):
            validate_architecture(
                {"served_limiters": ["LCL-1", "LCL-1"], "stages": TOLERANT["stages"]}
            )

    def test_blank_limiter_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_architecture(
                {"served_limiters": ["LCL-1", "  "], "stages": TOLERANT["stages"]}
            )

    def test_duplicate_stage_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_architecture(
                {
                    "served_limiters": list(LIMITERS),
                    "stages": [
                        {"name": "s", "units": ["A", "B", "C"], "vote": 2},
                        {"name": "s", "units": ["D", "E", "F"], "vote": 2},
                    ],
                }
            )

    def test_empty_unit_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_architecture(
                {
                    "served_limiters": list(LIMITERS),
                    "stages": [{"name": "s", "units": [], "vote": 1}],
                }
            )

    def test_duplicate_unit_inside_a_stage_rejected(self):
        with self.assertRaises(ValueError):
            validate_architecture(
                {
                    "served_limiters": list(LIMITERS),
                    "stages": [{"name": "s", "units": ["A", "A"], "vote": 1}],
                }
            )

    def test_vote_larger_than_the_unit_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_architecture(
                {
                    "served_limiters": list(LIMITERS),
                    "stages": [{"name": "s", "units": ["A", "B"], "vote": 3}],
                }
            )

    def test_zero_vote_rejected(self):
        with self.assertRaises(ValueError):
            validate_architecture(
                {
                    "served_limiters": list(LIMITERS),
                    "stages": [{"name": "s", "units": ["A", "B"], "vote": 0}],
                }
            )

    def test_boolean_vote_rejected(self):
        with self.assertRaises(ValueError):
            validate_architecture(
                {
                    "served_limiters": list(LIMITERS),
                    "stages": [{"name": "s", "units": ["A", "B"], "vote": True}],
                }
            )

    def test_serves_naming_an_unknown_limiter_rejected(self):
        with self.assertRaises(ValueError):
            validate_architecture(
                tolerant_plus(
                    {"name": "x", "units": ["A"], "vote": 1, "serves": ["LCL-9"]}
                )
            )


class TopologyTests(unittest.TestCase):
    def test_units_shared_between_stages_are_counted_once(self):
        _, stages = validate_architecture(
            {
                "served_limiters": list(LIMITERS),
                "stages": [
                    {"name": "a", "units": ["U1", "U2", "U3"], "vote": 2},
                    {"name": "b", "units": ["U1", "U4", "U5"], "vote": 2},
                ],
            }
        )
        self.assertEqual(architecture_units(stages), ["U1", "U2", "U3", "U4", "U5"])

    def test_stage_lookup_finds_only_the_serving_stages(self):
        _, stages = validate_architecture(
            tolerant_plus(
                {"name": "lcl3-driver", "units": ["DRV"], "vote": 1, "serves": ["LCL-3"]}
            )
        )
        self.assertEqual(len(stage_limiters(stages, "LCL-1")), 2)
        self.assertEqual(len(stage_limiters(stages, "LCL-3")), 3)

    def test_stage_survives_while_the_vote_is_met(self):
        _, stages = validate_architecture(TOLERANT)
        self.assertTrue(stage_functional(stages[0], {"SENSE-A"}))
        self.assertFalse(stage_functional(stages[0], {"SENSE-A", "SENSE-B"}))

    def test_every_limiter_is_protected_with_no_failure(self):
        limiters, stages = validate_architecture(TOLERANT)
        self.assertEqual(protected_limiters(limiters, stages), LIMITERS)


class SingleFailureWalkTests(unittest.TestCase):
    def test_two_of_three_has_no_loss_point(self):
        limiters, stages = validate_architecture(TOLERANT)
        self.assertEqual(loss_single_points(limiters, stages), [])

    def test_two_of_three_has_no_spurious_point(self):
        limiters, stages = validate_architecture(TOLERANT)
        self.assertEqual(spurious_single_points(limiters, stages), [])

    def test_or_voted_chain_survives_a_loss_but_trips_spuriously(self):
        limiters, stages = validate_architecture(OR_VOTED)
        self.assertEqual(loss_single_points(limiters, stages), [])
        spurious = spurious_single_points(limiters, stages)
        self.assertEqual(len(spurious), 2)
        self.assertEqual(spurious[0]["limiters_tripped"], LIMITERS)

    def test_and_voted_chain_loses_protection_but_never_trips_spuriously(self):
        limiters, stages = validate_architecture(AND_VOTED)
        self.assertEqual(spurious_single_points(limiters, stages), [])
        loss = loss_single_points(limiters, stages)
        self.assertEqual(len(loss), 2)
        self.assertEqual(loss[0]["limiters_lost"], LIMITERS)

    def test_simplex_chain_fails_in_both_directions(self):
        limiters, stages = validate_architecture(SIMPLEX)
        self.assertEqual(len(loss_single_points(limiters, stages)), 1)
        self.assertEqual(len(spurious_single_points(limiters, stages)), 1)

    def test_a_dedicated_stage_costs_only_the_limiter_it_serves(self):
        limiters, stages = validate_architecture(
            tolerant_plus(
                {"name": "lcl3-driver", "units": ["DRV"], "vote": 1, "serves": ["LCL-3"]}
            )
        )
        loss = loss_single_points(limiters, stages)
        self.assertEqual(len(loss), 1)
        self.assertEqual(loss[0]["unit"], "DRV")
        self.assertEqual(loss[0]["limiters_lost"], ["LCL-3"])

    def test_spurious_point_names_every_stage_it_can_trip_from(self):
        limiters, stages = validate_architecture(
            {
                "served_limiters": list(LIMITERS),
                "stages": [
                    {"name": "sense", "units": ["U1", "U2"], "vote": 1},
                    {"name": "drive", "units": ["U1", "U3"], "vote": 1},
                ],
            }
        )
        points = {p["unit"]: p for p in spurious_single_points(limiters, stages)}
        self.assertEqual(points["U1"]["stages"], ["sense", "drive"])
        self.assertEqual(points["U2"]["stages"], ["sense"])


class AssessmentTests(unittest.TestCase):
    def test_two_of_three_architecture_is_compliant(self):
        result = assess_centralised_protection(TOLERANT)
        self.assertTrue(result["single_failure_tolerant"])
        self.assertEqual(result["verdict"], "compliant")
        self.assertEqual(result["findings"], [])

    def test_or_voted_architecture_is_not_compliant(self):
        result = assess_centralised_protection(OR_VOTED)
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertEqual(result["loss_single_points"], [])
        self.assertEqual(len(result["spurious_single_points"]), 2)

    def test_and_voted_architecture_is_not_compliant(self):
        result = assess_centralised_protection(AND_VOTED)
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertEqual(result["spurious_single_points"], [])
        self.assertEqual(len(result["loss_single_points"]), 2)

    def test_counts_are_reported(self):
        result = assess_centralised_protection(TOLERANT)
        self.assertEqual(result["stage_count"], 2)
        self.assertEqual(result["unit_count"], 6)
        self.assertEqual(result["served_limiters"], LIMITERS)

    def test_single_limiter_is_flagged_as_outside_the_shared_case(self):
        result = assess_centralised_protection(
            {
                "served_limiters": ["LCL-1"],
                "stages": [
                    {"name": "sense", "units": ["A", "B", "C"], "vote": 2},
                ],
            }
        )
        self.assertFalse(result["centralised"])
        self.assertTrue(result["single_failure_tolerant"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_limiter_no_stage_serves_is_reported_and_fails(self):
        result = assess_centralised_protection(
            {
                "served_limiters": list(LIMITERS),
                "stages": [
                    {
                        "name": "sense",
                        "units": ["A", "B", "C"],
                        "vote": 2,
                        "serves": ["LCL-1", "LCL-2"],
                    }
                ],
            }
        )
        self.assertEqual(result["unserved_limiters"], ["LCL-3"])
        self.assertFalse(result["single_failure_tolerant"])

    def test_findings_name_the_unit_and_the_limiters_behind_each_point(self):
        result = assess_centralised_protection(SIMPLEX)
        joined = " | ".join(result["findings"])
        self.assertIn("SENSE-A", joined)
        self.assertIn("LCL-2", joined)

    def test_shared_threshold_for_the_centralised_case(self):
        self.assertEqual(MIN_SHARED_LIMITERS, 2)


if __name__ == "__main__":
    unittest.main()
