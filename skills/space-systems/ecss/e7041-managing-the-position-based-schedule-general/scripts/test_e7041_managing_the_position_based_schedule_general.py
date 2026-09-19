"""Contract tests for the clause 6.22.6.2 position-based schedule management."""

import unittest

from e7041_managing_the_position_based_schedule_general_logic import (
    OPERATION_DELETE,
    OPERATION_INSERT,
    SUPPORTED_OPERATIONS,
    apply_schedule_operations,
    delete_entry,
    insert_entry,
    normalise_entry,
    order_schedule,
    schedule_key,
)


def entry(request_id, orbit, angle):
    return {"request_id": request_id, "orbit_number": orbit, "angle_degrees": angle}


class EntryValidationTests(unittest.TestCase):
    def test_valid_entry_is_normalised(self):
        result = normalise_entry(entry("burn", 12, 90))
        self.assertEqual(result["request_id"], "burn")
        self.assertEqual(result["orbit_number"], 12)
        self.assertAlmostEqual(result["angle_degrees"], 90.0, places=9)

    def test_ascending_node_is_a_valid_angle(self):
        self.assertAlmostEqual(
            normalise_entry(entry("burn", 12, 0))["angle_degrees"], 0.0, places=9
        )

    def test_a_whole_revolution_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_entry(entry("burn", 12, 360.0))

    def test_negative_orbit_number_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_entry(entry("burn", -1, 90.0))

    def test_blank_request_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_entry(entry("   ", 12, 90.0))

    def test_missing_key_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_entry({"request_id": "burn", "orbit_number": 12})

    def test_non_mapping_entry_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_entry(["burn", 12, 90.0])


class OrderingTests(unittest.TestCase):
    def test_schedule_is_ordered_by_orbit_then_angle(self):
        ordered = order_schedule(
            [entry("c", 13, 10.0), entry("b", 12, 300.0), entry("a", 12, 20.0)]
        )
        self.assertEqual([e["request_id"] for e in ordered], ["a", "b", "c"])

    def test_next_orbit_outranks_the_end_of_this_one(self):
        self.assertLess(
            schedule_key(normalise_entry(entry("a", 12, 359.0)))[0],
            schedule_key(normalise_entry(entry("b", 13, 0.0)))[0],
        )

    def test_duplicate_identifier_in_the_initial_schedule_is_refused(self):
        with self.assertRaises(ValueError):
            order_schedule([entry("a", 12, 10.0), entry("a", 13, 10.0)])

    def test_empty_schedule_orders_to_nothing(self):
        self.assertEqual(order_schedule([]), ())

    def test_non_sequence_schedule_is_refused(self):
        with self.assertRaises(ValueError):
            order_schedule({"a": 1})


class InsertDeleteTests(unittest.TestCase):
    def test_insertion_lands_in_position_order(self):
        schedule = order_schedule([entry("late", 14, 10.0)])
        schedule = insert_entry(schedule, entry("early", 12, 10.0), 4)
        self.assertEqual([e["request_id"] for e in schedule], ["early", "late"])

    def test_duplicate_identifier_insertion_is_refused(self):
        schedule = order_schedule([entry("burn", 14, 10.0)])
        with self.assertRaises(ValueError):
            insert_entry(schedule, entry("burn", 15, 10.0), 4)

    def test_insertion_past_capacity_is_refused(self):
        schedule = order_schedule([entry("a", 12, 10.0), entry("b", 13, 10.0)])
        with self.assertRaises(ValueError):
            insert_entry(schedule, entry("c", 14, 10.0), 2)

    def test_deletion_removes_the_named_entry(self):
        schedule = order_schedule([entry("a", 12, 10.0), entry("b", 13, 10.0)])
        remaining = delete_entry(schedule, "b")
        self.assertEqual([e["request_id"] for e in remaining], ["a"])

    def test_deleting_an_absent_identifier_is_refused(self):
        schedule = order_schedule([entry("a", 12, 10.0)])
        with self.assertRaises(ValueError):
            delete_entry(schedule, "zzz")

    def test_deleting_with_a_blank_identifier_is_refused(self):
        schedule = order_schedule([entry("a", 12, 10.0)])
        with self.assertRaises(ValueError):
            delete_entry(schedule, "  ")

    def test_zero_capacity_is_refused(self):
        with self.assertRaises(ValueError):
            insert_entry((), entry("a", 12, 10.0), 0)


class OperationRunTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "initial_entries": [entry("beacon", 12, 45.0), entry("burn", 13, 200.0)],
            "capacity": 4,
            "operations": [
                dict(entry("survey", 12, 300.0), operation=OPERATION_INSERT),
                {"operation": OPERATION_DELETE, "request_id": "burn"},
            ],
        }
        spec.update(overrides)
        return spec

    def test_a_clean_run_accepts_every_operation(self):
        result = apply_schedule_operations(self._spec())
        self.assertTrue(result["all_operations_accepted"])
        self.assertEqual(result["rejected_operations"], ())

    def test_the_resulting_schedule_is_in_position_order(self):
        result = apply_schedule_operations(self._spec())
        self.assertEqual(result["scheduled_request_ids"], ("beacon", "survey"))

    def test_occupancy_and_free_slots_are_reported(self):
        result = apply_schedule_operations(self._spec())
        self.assertEqual(result["occupancy"], 2)
        self.assertEqual(result["free_slots"], 2)

    def test_a_duplicate_insertion_is_rejected_without_stopping_the_run(self):
        spec = self._spec(
            operations=[
                dict(entry("beacon", 15, 10.0), operation=OPERATION_INSERT),
                {"operation": OPERATION_DELETE, "request_id": "burn"},
            ]
        )
        result = apply_schedule_operations(spec)
        self.assertEqual(len(result["rejected_operations"]), 1)
        self.assertEqual(len(result["accepted_operations"]), 1)
        self.assertEqual(result["scheduled_request_ids"], ("beacon",))

    def test_capacity_exhaustion_rejects_the_later_insertion(self):
        spec = self._spec(
            capacity=2,
            operations=[dict(entry("survey", 12, 300.0), operation=OPERATION_INSERT)],
        )
        result = apply_schedule_operations(spec)
        self.assertFalse(result["all_operations_accepted"])
        self.assertIn("capacity", result["rejected_operations"][0][2])

    def test_a_deletion_frees_a_slot_for_a_later_insertion(self):
        spec = self._spec(
            capacity=2,
            operations=[
                {"operation": OPERATION_DELETE, "request_id": "burn"},
                dict(entry("survey", 12, 300.0), operation=OPERATION_INSERT),
            ],
        )
        result = apply_schedule_operations(spec)
        self.assertTrue(result["all_operations_accepted"])
        self.assertEqual(result["scheduled_request_ids"], ("beacon", "survey"))

    def test_deleting_an_absent_entry_is_rejected(self):
        spec = self._spec(
            operations=[{"operation": OPERATION_DELETE, "request_id": "ghost"}]
        )
        result = apply_schedule_operations(spec)
        self.assertEqual(len(result["rejected_operations"]), 1)

    def test_an_initial_schedule_past_capacity_is_refused(self):
        with self.assertRaises(ValueError):
            apply_schedule_operations(self._spec(capacity=1))

    def test_an_unknown_operation_name_is_refused(self):
        with self.assertRaises(ValueError):
            apply_schedule_operations(
                self._spec(operations=[{"operation": "reschedule"}])
            )

    def test_missing_spec_key_is_refused(self):
        spec = self._spec()
        del spec["capacity"]
        with self.assertRaises(ValueError):
            apply_schedule_operations(spec)

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            apply_schedule_operations(["operations"])

    def test_only_insert_and_delete_are_supported(self):
        self.assertEqual(SUPPORTED_OPERATIONS, (OPERATION_INSERT, OPERATION_DELETE))


if __name__ == "__main__":
    unittest.main()
