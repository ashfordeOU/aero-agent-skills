"""Contract tests for the clause 5.2.13.5.1 both-switches undervoltage logic."""

import unittest

from e2020_undervoltage_action_on_both_switches_logic import (
    ELEMENT_KINDS,
    REQUIRED_SWITCH_ROLES,
    SHAREABLE_KINDS,
    assess_undervoltage_both_switches,
    holds_open_state,
    memory_cells,
    path_ids,
    shared_elements,
    single_failure_points,
    switch_opens,
    validate_protection,
)


def switch(role, name, elements):
    return {"role": role, "name": name, "path": list(elements)}


# Shared detection, one memory cell and one driver per switch: the arrangement
# the clause asks for.
INDEPENDENT = {
    "unit": "LCL-7",
    "switches": [
        switch(
            "main",
            "MS-7",
            [
                {"id": "UVD", "kind": "sense"},
                {"id": "CELL-M", "kind": "memory"},
                {"id": "DRV-M", "kind": "drive"},
            ],
        ),
        switch(
            "extra",
            "XS-7",
            [
                {"id": "UVD", "kind": "sense"},
                {"id": "CELL-X", "kind": "memory"},
                {"id": "DRV-X", "kind": "drive"},
            ],
        ),
    ],
}

# One cell latches both switches: the defect the clause is written against.
SHARED_CELL = {
    "unit": "LCL-8",
    "switches": [
        switch(
            "main",
            "MS-8",
            [
                {"id": "UVD", "kind": "sense"},
                {"id": "CELL-1", "kind": "memory"},
                {"id": "DRV-M", "kind": "drive"},
            ],
        ),
        switch(
            "extra",
            "XS-8",
            [
                {"id": "UVD", "kind": "sense"},
                {"id": "CELL-1", "kind": "memory"},
                {"id": "DRV-X", "kind": "drive"},
            ],
        ),
    ],
}

# Separate cells, one driver: independence bought and then given back.
SHARED_DRIVE = {
    "unit": "LCL-9",
    "switches": [
        switch(
            "main",
            "MS-9",
            [
                {"id": "CELL-M", "kind": "memory"},
                {"id": "DRV-1", "kind": "drive"},
            ],
        ),
        switch(
            "extra",
            "XS-9",
            [
                {"id": "CELL-X", "kind": "memory"},
                {"id": "DRV-1", "kind": "drive"},
            ],
        ),
    ],
}


def spec_with(main_path, extra_path, unit="LCL-0"):
    return {
        "unit": unit,
        "switches": [
            switch("main", "MS", main_path),
            switch("extra", "XS", extra_path),
        ],
    }


class ValidationTests(unittest.TestCase):
    def test_valid_spec_returns_unit_and_both_roles_in_order(self):
        unit, switches = validate_protection(INDEPENDENT)
        self.assertEqual(unit, "LCL-7")
        self.assertEqual([s["role"] for s in switches], list(REQUIRED_SWITCH_ROLES))

    def test_memory_elements_default_to_holding_state(self):
        _, switches = validate_protection(INDEPENDENT)
        self.assertTrue(memory_cells(switches[0])[0]["holds_state"])

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            validate_protection(["main", "extra"])

    def test_missing_switches_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_protection({"unit": "LCL-1"})

    def test_blank_unit_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_protection({"unit": "   ", "switches": INDEPENDENT["switches"]})

    def test_missing_extra_switch_rejected(self):
        with self.assertRaises(ValueError):
            validate_protection(
                {
                    "unit": "LCL-1",
                    "switches": [switch("main", "MS", [{"id": "C", "kind": "memory"}])],
                }
            )

    def test_unknown_switch_role_rejected(self):
        with self.assertRaises(ValueError):
            validate_protection(
                {
                    "unit": "LCL-1",
                    "switches": [
                        switch("spare", "SS", [{"id": "C", "kind": "memory"}]),
                        switch("extra", "XS", [{"id": "D", "kind": "memory"}]),
                    ],
                }
            )

    def test_duplicate_switch_role_rejected(self):
        with self.assertRaises(ValueError):
            validate_protection(
                {
                    "unit": "LCL-1",
                    "switches": [
                        switch("main", "MS-A", [{"id": "C", "kind": "memory"}]),
                        switch("main", "MS-B", [{"id": "D", "kind": "memory"}]),
                    ],
                }
            )

    def test_empty_command_path_rejected(self):
        with self.assertRaises(ValueError):
            validate_protection(spec_with([], [{"id": "D", "kind": "memory"}]))

    def test_repeated_element_inside_one_path_rejected(self):
        with self.assertRaises(ValueError):
            validate_protection(
                spec_with(
                    [{"id": "C", "kind": "memory"}, {"id": "C", "kind": "memory"}],
                    [{"id": "D", "kind": "memory"}],
                )
            )

    def test_unknown_element_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_protection(
                spec_with([{"id": "C", "kind": "relay"}], [{"id": "D", "kind": "memory"}])
            )

    def test_element_declared_with_two_kinds_rejected(self):
        with self.assertRaises(ValueError):
            validate_protection(
                spec_with([{"id": "C", "kind": "memory"}], [{"id": "C", "kind": "drive"}])
            )

    def test_non_boolean_holds_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_protection(
                spec_with(
                    [{"id": "C", "kind": "memory", "holds_state": "yes"}],
                    [{"id": "D", "kind": "memory"}],
                )
            )

    def test_holds_state_on_a_drive_element_rejected(self):
        with self.assertRaises(ValueError):
            validate_protection(
                spec_with(
                    [{"id": "C", "kind": "memory"}, {"id": "E", "kind": "drive", "holds_state": True}],
                    [{"id": "D", "kind": "memory"}],
                )
            )

    def test_kind_and_role_vocabularies_are_the_documented_ones(self):
        self.assertEqual(ELEMENT_KINDS, ("sense", "memory", "drive"))
        self.assertEqual(SHAREABLE_KINDS, ("sense",))
        self.assertEqual(REQUIRED_SWITCH_ROLES, ("main", "extra"))


class PathTests(unittest.TestCase):
    def test_path_ids_keep_the_declared_order(self):
        _, switches = validate_protection(INDEPENDENT)
        self.assertEqual(path_ids(switches[0]), ["UVD", "CELL-M", "DRV-M"])

    def test_switch_opens_with_no_failure_injected(self):
        _, switches = validate_protection(INDEPENDENT)
        self.assertTrue(switch_opens(switches[0]))

    def test_switch_stays_closed_when_a_path_element_fails(self):
        _, switches = validate_protection(INDEPENDENT)
        self.assertFalse(switch_opens(switches[0], {"DRV-M"}))
        self.assertTrue(switch_opens(switches[1], {"DRV-M"}))

    def test_a_path_without_a_memory_element_does_not_hold_the_open_state(self):
        _, switches = validate_protection(
            spec_with([{"id": "DRV-M", "kind": "drive"}], [{"id": "CELL-X", "kind": "memory"}])
        )
        self.assertFalse(holds_open_state(switches[0]))
        self.assertTrue(holds_open_state(switches[1]))

    def test_a_cell_declared_not_to_hold_state_releases_the_switch(self):
        _, switches = validate_protection(
            spec_with(
                [{"id": "CELL-M", "kind": "memory", "holds_state": False}],
                [{"id": "CELL-X", "kind": "memory"}],
            )
        )
        self.assertFalse(holds_open_state(switches[0]))


class SharingTests(unittest.TestCase):
    def test_independent_paths_share_only_the_detection(self):
        _, switches = validate_protection(INDEPENDENT)
        shared = shared_elements(switches)
        self.assertEqual([entry["id"] for entry in shared], ["UVD"])
        self.assertEqual(shared[0]["kind"], "sense")

    def test_a_shared_cell_is_reported_against_both_roles(self):
        _, switches = validate_protection(SHARED_CELL)
        shared = {entry["id"]: entry for entry in shared_elements(switches)}
        self.assertEqual(shared["CELL-1"]["roles"], ["main", "extra"])

    def test_single_failure_walk_blocks_one_role_on_an_independent_element(self):
        _, switches = validate_protection(INDEPENDENT)
        points = {p["element"]: p for p in single_failure_points(switches)}
        self.assertEqual(points["CELL-M"]["roles_blocked"], ["main"])
        self.assertEqual(points["CELL-X"]["roles_blocked"], ["extra"])

    def test_single_failure_walk_blocks_both_roles_on_a_shared_element(self):
        _, switches = validate_protection(SHARED_CELL)
        points = {p["element"]: p for p in single_failure_points(switches)}
        self.assertEqual(points["CELL-1"]["roles_blocked"], ["main", "extra"])


class AssessmentTests(unittest.TestCase):
    def test_independent_cells_and_drivers_are_compliant(self):
        result = assess_undervoltage_both_switches(INDEPENDENT)
        self.assertEqual(result["verdict"], "compliant")
        self.assertTrue(result["acts_on_both_switches"])
        self.assertTrue(result["memory_independent"])
        self.assertEqual(result["findings"], [])

    def test_a_shared_detection_is_a_note_and_not_a_finding(self):
        result = assess_undervoltage_both_switches(INDEPENDENT)
        self.assertEqual(len(result["notes"]), 1)
        self.assertIn("UVD", result["notes"][0])

    def test_shared_memory_cell_is_not_compliant(self):
        result = assess_undervoltage_both_switches(SHARED_CELL)
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertFalse(result["memory_independent"])
        self.assertIn("CELL-1", " | ".join(result["findings"]))

    def test_shared_drive_stage_is_not_compliant(self):
        result = assess_undervoltage_both_switches(SHARED_DRIVE)
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertFalse(result["memory_independent"])
        self.assertIn("DRV-1", " | ".join(result["findings"]))

    def test_common_mode_points_name_every_element_that_blocks_both(self):
        result = assess_undervoltage_both_switches(SHARED_CELL)
        self.assertEqual(result["common_mode_points"], ["UVD", "CELL-1"])

    def test_independent_design_still_reports_the_shared_detection_as_common_mode(self):
        result = assess_undervoltage_both_switches(INDEPENDENT)
        self.assertEqual(result["common_mode_points"], ["UVD"])
        self.assertEqual(result["verdict"], "compliant")

    def test_a_switch_with_no_memory_cell_is_not_compliant(self):
        result = assess_undervoltage_both_switches(
            spec_with([{"id": "DRV-M", "kind": "drive"}], [{"id": "CELL-X", "kind": "memory"}])
        )
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertEqual(result["memory_cells"]["main"], [])
        self.assertFalse(result["open_state_held"]["main"])

    def test_a_volatile_cell_is_reported_by_identifier(self):
        result = assess_undervoltage_both_switches(
            spec_with(
                [{"id": "CELL-M", "kind": "memory", "holds_state": False}],
                [{"id": "CELL-X", "kind": "memory"}],
            )
        )
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertIn("CELL-M", " | ".join(result["findings"]))

    def test_result_reports_the_unit_and_the_switch_names(self):
        result = assess_undervoltage_both_switches(INDEPENDENT)
        self.assertEqual(result["unit"], "LCL-7")
        self.assertEqual(result["switch_names"], {"main": "MS-7", "extra": "XS-7"})

    def test_memory_cells_are_reported_per_role(self):
        result = assess_undervoltage_both_switches(INDEPENDENT)
        self.assertEqual(result["memory_cells"], {"main": ["CELL-M"], "extra": ["CELL-X"]})


if __name__ == "__main__":
    unittest.main()
