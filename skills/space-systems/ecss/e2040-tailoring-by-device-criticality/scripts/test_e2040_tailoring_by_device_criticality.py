"""Contract tests for the clause 5.1.2 device criticality tailoring logic."""

import unittest

from e2040_tailoring_by_device_criticality_logic import (
    CRITICALITY_ORDER,
    DEVICE_TYPES,
    applies_to_device,
    apply_project_delta,
    assess_tailoring,
    build_baseline,
    check_criticality_monotonic,
    criticality_rank,
    normalize_criticality,
    normalize_device_type,
    tailor_requirement_set,
    validate_requirement,
)


def base_baseline():
    return [
        {"id": "REQ-001", "applies_to_types": "all", "minimum_criticality": "minor",
         "removable": False, "title": "device requirements specification exists"},
        {"id": "REQ-002", "applies_to_types": "all", "minimum_criticality": "major"},
        {"id": "REQ-003", "applies_to_types": ["asic", "fpga"],
         "minimum_criticality": "major"},
        {"id": "REQ-004", "applies_to_types": ["asic"], "minimum_criticality": "critical",
         "removable": False},
        {"id": "REQ-005", "applies_to_types": ["hybrid", "multi-chip-module"],
         "minimum_criticality": "critical"},
        {"id": "REQ-006", "applies_to_types": "all",
         "minimum_criticality": "catastrophic"},
    ]


class CriticalityTests(unittest.TestCase):
    def test_canonical_category_passes_through(self):
        self.assertEqual(normalize_criticality("critical"), "critical")

    def test_numeral_one_is_the_most_severe(self):
        self.assertEqual(normalize_criticality("1"), "catastrophic")

    def test_roman_numeral_is_folded(self):
        self.assertEqual(normalize_criticality("III"), "major")

    def test_rank_increases_with_severity(self):
        self.assertLess(criticality_rank("minor"), criticality_rank("catastrophic"))

    def test_order_has_no_repeats(self):
        self.assertEqual(len(set(CRITICALITY_ORDER)), len(CRITICALITY_ORDER))

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_criticality("severe-ish")

    def test_blank_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_criticality("   ")


class DeviceTypeTests(unittest.TestCase):
    def test_canonical_type_passes_through(self):
        self.assertEqual(normalize_device_type("asic"), "asic")

    def test_mcm_is_folded(self):
        self.assertEqual(normalize_device_type("MCM"), "multi-chip-module")

    def test_spelled_out_type_is_folded(self):
        self.assertEqual(normalize_device_type("Field Programmable Gate Array"), "fpga")

    def test_unknown_type_rejected(self):
        with self.assertRaises(ValueError):
            normalize_device_type("breadboard")

    def test_every_canonical_type_round_trips(self):
        for device_type in DEVICE_TYPES:
            self.assertEqual(normalize_device_type(device_type), device_type)


class BaselineValidationTests(unittest.TestCase):
    def test_all_types_is_accepted(self):
        record = validate_requirement(base_baseline()[0])
        self.assertEqual(record["applies_to_types"], "all")

    def test_type_list_is_folded_and_sorted(self):
        record = validate_requirement(
            {"id": "R", "applies_to_types": ["MCM", "hybrid"],
             "minimum_criticality": "minor"}
        )
        self.assertEqual(record["applies_to_types"], ("hybrid", "multi-chip-module"))

    def test_removable_defaults_to_true(self):
        self.assertTrue(validate_requirement(base_baseline()[1])["removable"])

    def test_empty_type_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(
                {"id": "R", "applies_to_types": [], "minimum_criticality": "minor"}
            )

    def test_free_text_type_scope_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(
                {"id": "R", "applies_to_types": "everything",
                 "minimum_criticality": "minor"}
            )

    def test_repeated_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(
                {"id": "R", "applies_to_types": ["asic", "ASIC"],
                 "minimum_criticality": "minor"}
            )

    def test_non_boolean_removable_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(
                {"id": "R", "applies_to_types": "all",
                 "minimum_criticality": "minor", "removable": "no"}
            )

    def test_duplicate_baseline_id_rejected(self):
        baseline = base_baseline()
        baseline.append(dict(baseline[0]))
        with self.assertRaises(ValueError):
            build_baseline(baseline)

    def test_empty_baseline_rejected(self):
        with self.assertRaises(ValueError):
            build_baseline([])

    def test_non_mapping_requirement_rejected(self):
        with self.assertRaises(ValueError):
            applies_to_device(["REQ-001"], "asic", "major")


class TailoringTests(unittest.TestCase):
    def test_minor_asic_keeps_only_the_floor_requirement(self):
        baseline = build_baseline(base_baseline())
        self.assertEqual(tailor_requirement_set(baseline, "asic", "minor"), ["REQ-001"])

    def test_major_asic_adds_the_type_scoped_requirement(self):
        baseline = build_baseline(base_baseline())
        self.assertEqual(
            tailor_requirement_set(baseline, "asic", "major"),
            ["REQ-001", "REQ-002", "REQ-003"],
        )

    def test_critical_asic_adds_the_asic_only_requirement(self):
        baseline = build_baseline(base_baseline())
        self.assertIn("REQ-004", tailor_requirement_set(baseline, "asic", "critical"))

    def test_hybrid_never_picks_up_the_asic_requirement(self):
        baseline = build_baseline(base_baseline())
        for category in CRITICALITY_ORDER:
            self.assertNotIn(
                "REQ-004", tailor_requirement_set(baseline, "hybrid", category)
            )

    def test_catastrophic_reaches_the_widest_set(self):
        baseline = build_baseline(base_baseline())
        self.assertEqual(len(tailor_requirement_set(baseline, "asic", "catastrophic")), 5)

    def test_type_scope_excludes_a_board_level_device(self):
        baseline = build_baseline(base_baseline())
        self.assertNotIn(
            "REQ-003", tailor_requirement_set(baseline, "board-level-device", "critical")
        )

    def test_applies_to_device_is_false_below_the_floor(self):
        record = validate_requirement(base_baseline()[5])
        self.assertFalse(applies_to_device(record, "asic", "critical"))
        self.assertTrue(applies_to_device(record, "asic", "catastrophic"))


class MonotonicityTests(unittest.TestCase):
    def test_sane_baseline_is_monotonic(self):
        baseline = build_baseline(base_baseline())
        self.assertTrue(check_criticality_monotonic(baseline, "asic")["monotonic"])

    def test_every_category_gets_a_set(self):
        baseline = build_baseline(base_baseline())
        result = check_criticality_monotonic(baseline, "asic")
        self.assertEqual(set(result["sets"]), set(CRITICALITY_ORDER))

    def test_sets_grow_with_severity(self):
        baseline = build_baseline(base_baseline())
        sets = check_criticality_monotonic(baseline, "asic")["sets"]
        self.assertTrue(set(sets["minor"]) <= set(sets["catastrophic"]))


class DeltaTests(unittest.TestCase):
    def setUp(self):
        self.baseline = build_baseline(base_baseline())
        self.tailored = tailor_requirement_set(self.baseline, "asic", "critical")

    def test_no_delta_leaves_the_set_alone(self):
        result = apply_project_delta(self.baseline, self.tailored, None)
        self.assertEqual(result["final"], self.tailored)
        self.assertEqual(result["reduction"], 0)

    def test_justified_removal_is_recorded(self):
        delta = {"removed": [{"id": "REQ-003", "justification": "no programmable logic"}]}
        result = apply_project_delta(self.baseline, self.tailored, delta)
        self.assertNotIn("REQ-003", result["final"])
        self.assertEqual(result["removed_without_justification"], [])

    def test_bare_id_removal_has_no_justification(self):
        result = apply_project_delta(self.baseline, self.tailored, {"removed": ["REQ-003"]})
        self.assertEqual(result["removed_without_justification"], ["REQ-003"])

    def test_protected_removal_is_named(self):
        delta = {"removed": [{"id": "REQ-004", "justification": "cost"}]}
        result = apply_project_delta(self.baseline, self.tailored, delta)
        self.assertEqual(result["removed_though_protected"], ["REQ-004"])

    def test_addition_outside_the_baseline_is_named(self):
        delta = {"added": [{"id": "REQ-999", "justification": "project specific"}]}
        result = apply_project_delta(self.baseline, self.tailored, delta)
        self.assertEqual(result["added_outside_the_baseline"], ["REQ-999"])

    def test_removing_an_absent_requirement_rejected(self):
        with self.assertRaises(ValueError):
            apply_project_delta(self.baseline, self.tailored, {"removed": ["REQ-006"]})

    def test_adding_a_held_requirement_rejected(self):
        with self.assertRaises(ValueError):
            apply_project_delta(self.baseline, self.tailored, {"added": ["REQ-001"]})

    def test_malformed_delta_entry_rejected(self):
        with self.assertRaises(ValueError):
            apply_project_delta(self.baseline, self.tailored, {"removed": [42]})

    def test_non_mapping_delta_rejected(self):
        with self.assertRaises(ValueError):
            apply_project_delta(self.baseline, self.tailored, ["REQ-003"])

    def test_reduction_counts_removals_less_additions(self):
        delta = {
            "removed": [{"id": "REQ-003", "justification": "no programmable logic"}],
            "added": [{"id": "REQ-005", "justification": "hybrid substrate reused"}],
        }
        result = apply_project_delta(self.baseline, self.tailored, delta)
        self.assertEqual(result["reduction"], 0)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "baseline": base_baseline(),
            "device_type": "asic",
            "criticality": "critical",
        }
        spec.update(overrides)
        return spec

    def test_clean_tailoring_is_compliant(self):
        result = assess_tailoring(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_tailored_set_is_reported(self):
        result = assess_tailoring(self._spec())
        self.assertEqual(result["tailored"], ["REQ-001", "REQ-002", "REQ-003", "REQ-004"])

    def test_criticality_rank_is_reported(self):
        result = assess_tailoring(self._spec())
        self.assertEqual(result["criticality_rank"], criticality_rank("critical"))

    def test_unjustified_removal_is_flagged(self):
        result = assess_tailoring(self._spec(delta={"removed": ["REQ-002"]}))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("no justification" in f for f in result["findings"]))

    def test_protected_removal_is_flagged(self):
        result = assess_tailoring(
            self._spec(delta={"removed": [{"id": "REQ-001", "justification": "scope"}]})
        )
        self.assertTrue(any("non-removable" in f for f in result["findings"]))

    def test_device_the_baseline_does_not_reach_is_flagged(self):
        baseline = [
            {"id": "REQ-010", "applies_to_types": ["asic"],
             "minimum_criticality": "catastrophic"}
        ]
        result = assess_tailoring(
            self._spec(baseline=baseline, device_type="hybrid", criticality="minor")
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("no baseline requirement" in f for f in result["findings"]))

    def test_non_monotonic_baseline_is_flagged(self):
        result = assess_tailoring(self._spec())
        self.assertTrue(result["monotonic"]["monotonic"])

    def test_missing_device_type_rejected(self):
        spec = self._spec()
        del spec["device_type"]
        with self.assertRaises(ValueError):
            assess_tailoring(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_tailoring(["baseline"])

    def test_unknown_criticality_rejected(self):
        with self.assertRaises(ValueError):
            assess_tailoring(self._spec(criticality="quite-bad"))


if __name__ == "__main__":
    unittest.main()
