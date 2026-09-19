"""Contract tests for the sterilization compatibility specimen selection logic."""

import unittest

from q7053_specimen_selection_logic import (
    CAPABILITY_TOLERANCE,
    DEFAULT_MIN_REPLICATES,
    assess_specimen_set,
    group_by_family,
    is_representative,
    select_family_set,
    validate_pool,
    validate_specimen,
    validate_thickness_range,
    worst_case_specimen,
)


def coupon(identifier, family, thickness, capability, control=False, lot="L1"):
    return {
        "id": identifier,
        "family": family,
        "thickness_mm": thickness,
        "capability": capability,
        "is_control": control,
        "lot": lot,
    }


POOL = [
    coupon("AL-1", "aluminium", 2.0, 200.0),
    coupon("AL-2", "aluminium", 2.5, 210.0),
    coupon("AL-3", "aluminium", 3.0, 220.0),
    coupon("AL-C", "aluminium", 2.0, 200.0, control=True),
    coupon("PA-1", "polyamide", 1.5, 130.0),
    coupon("PA-2", "polyamide", 1.8, 140.0),
    coupon("PA-3", "polyamide", 2.0, 150.0),
    coupon("PA-C", "polyamide", 1.5, 130.0, control=True),
]


class ValidationTests(unittest.TestCase):
    def test_range_is_returned_as_floats(self):
        self.assertEqual(validate_thickness_range(1, 5), (1.0, 5.0))

    def test_inverted_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_thickness_range(5.0, 1.0)

    def test_zero_thickness_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_thickness_range(0.0, 5.0)

    def test_family_is_lowercased(self):
        record = validate_specimen(coupon("X", "Aluminium", 2.0, 100.0))
        self.assertEqual(record["family"], "aluminium")

    def test_specimen_missing_a_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_specimen({"id": "X", "family": "f", "thickness_mm": 1.0})

    def test_non_boolean_control_flag_rejected(self):
        bad = coupon("X", "f", 1.0, 100.0)
        bad["is_control"] = "yes"
        with self.assertRaises(ValueError):
            validate_specimen(bad)

    def test_negative_capability_rejected(self):
        with self.assertRaises(ValueError):
            validate_specimen(coupon("X", "f", 1.0, -1.0))

    def test_duplicate_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_pool([coupon("X", "f", 1.0, 10.0), coupon("X", "f", 2.0, 20.0)])

    def test_empty_pool_rejected(self):
        with self.assertRaises(ValueError):
            validate_pool([])


class RepresentativenessTests(unittest.TestCase):
    def test_thickness_inside_the_range(self):
        self.assertTrue(is_representative(2.0, (1.0, 3.0)))

    def test_thickness_at_the_lower_bound_is_inside(self):
        self.assertTrue(is_representative(1.0, (1.0, 3.0)))

    def test_thickness_at_the_upper_bound_is_inside(self):
        self.assertTrue(is_representative(3.0, (1.0, 3.0)))

    def test_thinner_than_flight_is_outside(self):
        self.assertFalse(is_representative(0.2, (1.0, 3.0)))

    def test_thicker_than_flight_is_outside(self):
        self.assertFalse(is_representative(9.0, (1.0, 3.0)))

    def test_zero_thickness_rejected(self):
        with self.assertRaises(ValueError):
            is_representative(0.0, (1.0, 3.0))


class GroupingTests(unittest.TestCase):
    def test_families_are_separated(self):
        grouped = group_by_family(validate_pool(POOL))
        self.assertEqual(sorted(grouped), ["aluminium", "polyamide"])

    def test_controls_are_kept_apart(self):
        grouped = group_by_family(validate_pool(POOL))
        self.assertEqual(len(grouped["aluminium"]["exposed"]), 3)
        self.assertEqual(len(grouped["aluminium"]["controls"]), 1)

    def test_worst_case_is_the_least_capable(self):
        grouped = group_by_family(validate_pool(POOL))
        worst = worst_case_specimen(grouped["polyamide"]["exposed"])
        self.assertEqual(worst["id"], "PA-1")

    def test_tie_is_broken_on_the_identifier(self):
        candidates = [
            {"id": "B", "capability": 100.0},
            {"id": "A", "capability": 100.0},
        ]
        self.assertEqual(worst_case_specimen(candidates)["id"], "A")

    def test_empty_candidate_list_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_specimen([])

    def test_malformed_candidate_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_specimen([{"id": "A"}])


class FamilySelectionTests(unittest.TestCase):
    def test_least_capable_specimens_are_taken_first(self):
        grouped = group_by_family(validate_pool(POOL))
        chosen = select_family_set(
            grouped["aluminium"]["exposed"], grouped["aluminium"]["controls"], 2
        )
        self.assertEqual([r["id"] for r in chosen["exposed"]], ["AL-1", "AL-2"])

    def test_control_is_attached(self):
        grouped = group_by_family(validate_pool(POOL))
        chosen = select_family_set(
            grouped["polyamide"]["exposed"], grouped["polyamide"]["controls"], 3
        )
        self.assertEqual(chosen["control"]["id"], "PA-C")

    def test_missing_control_is_reported_as_none(self):
        grouped = group_by_family(validate_pool(POOL))
        chosen = select_family_set(grouped["aluminium"]["exposed"], [], 2)
        self.assertIsNone(chosen["control"])

    def test_replicate_count_below_one_rejected(self):
        with self.assertRaises(ValueError):
            select_family_set([], [], 0)

    def test_non_integer_replicate_count_rejected(self):
        with self.assertRaises(ValueError):
            select_family_set([], [], 2.5)


class SpecimenSetTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "families": ["aluminium", "polyamide"],
            "pool": POOL,
            "flight_min_mm": 1.0,
            "flight_max_mm": 4.0,
            "applied_stressor": 125.0,
        }
        spec.update(overrides)
        return spec

    def test_complete_set_has_no_findings(self):
        result = assess_specimen_set(self._spec())
        self.assertTrue(result["complete"])
        self.assertEqual(result["findings"], [])

    def test_worst_case_is_selected_per_family(self):
        result = assess_specimen_set(self._spec())
        self.assertEqual(result["selection"]["polyamide"]["worst_case"]["id"], "PA-1")

    def test_default_replicate_count_is_used(self):
        result = assess_specimen_set(self._spec())
        self.assertEqual(result["min_replicates"], DEFAULT_MIN_REPLICATES)
        self.assertEqual(len(result["selection"]["aluminium"]["exposed"]), 3)

    def test_uncovered_family_is_a_finding(self):
        result = assess_specimen_set(self._spec(families=["aluminium", "titanium"]))
        self.assertFalse(result["complete"])
        self.assertTrue(any("titanium" in f for f in result["findings"]))

    def test_out_of_range_coupon_is_set_aside(self):
        pool = list(POOL) + [coupon("PA-THIN", "polyamide", 0.05, 100.0)]
        result = assess_specimen_set(self._spec(pool=pool))
        self.assertEqual([r["id"] for r in result["set_aside"]], ["PA-THIN"])
        self.assertFalse(result["complete"])

    def test_set_aside_coupon_does_not_count_toward_replicates(self):
        pool = [
            coupon("PA-1", "polyamide", 1.5, 130.0),
            coupon("PA-2", "polyamide", 1.8, 140.0),
            coupon("PA-FAT", "polyamide", 40.0, 120.0),
            coupon("PA-C", "polyamide", 1.5, 130.0, control=True),
        ]
        result = assess_specimen_set(self._spec(families=["polyamide"], pool=pool))
        self.assertEqual(len(result["selection"]["polyamide"]["exposed"]), 2)
        self.assertTrue(any("replicates required" in f for f in result["findings"]))

    def test_missing_control_is_a_finding(self):
        pool = [r for r in POOL if r["id"] != "PA-C"]
        result = assess_specimen_set(self._spec(pool=pool))
        self.assertTrue(any("no unexposed control" in f for f in result["findings"]))

    def test_control_from_another_lot_is_a_finding(self):
        pool = [r for r in POOL if r["id"] != "PA-C"]
        pool.append(coupon("PA-C2", "polyamide", 1.5, 130.0, control=True, lot="L9"))
        result = assess_specimen_set(self._spec(pool=pool))
        self.assertTrue(any("worst-case lot" in f for f in result["findings"]))

    def test_worst_case_below_the_applied_stressor_is_a_finding(self):
        result = assess_specimen_set(self._spec(applied_stressor=135.0))
        self.assertTrue(any("at or below the applied" in f for f in result["findings"]))

    def test_worst_case_exactly_at_the_stressor_is_a_finding(self):
        result = assess_specimen_set(self._spec(applied_stressor=130.0))
        worst = result["selection"]["polyamide"]["worst_case"]
        self.assertAlmostEqual(worst["capability"], 130.0, places=9)
        self.assertTrue(any("at or below the applied" in f for f in result["findings"]))

    def test_tolerance_is_a_representation_allowance_only(self):
        self.assertAlmostEqual(CAPABILITY_TOLERANCE, 1e-9, places=12)

    def test_empty_family_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_specimen_set(self._spec(families=[]))

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["applied_stressor"]
        with self.assertRaises(ValueError):
            assess_specimen_set(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_specimen_set(["families"])

    def test_covered_families_are_listed(self):
        result = assess_specimen_set(self._spec())
        self.assertEqual(sorted(result["covered_families"]), ["aluminium", "polyamide"])


if __name__ == "__main__":
    unittest.main()
