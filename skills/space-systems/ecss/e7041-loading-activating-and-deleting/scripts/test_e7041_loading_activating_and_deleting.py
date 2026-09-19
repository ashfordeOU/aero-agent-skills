"""Contract test for the OBCP load/activate/delete leaf (stdlib unittest)."""

import unittest

from e7041_loading_activating_and_deleting_logic import (
    OPERATION_ACTIVATE,
    OPERATION_DELETE,
    OPERATION_LOAD,
    OPERATION_STOP,
    OUTCOME_ACTIVATED,
    OUTCOME_DELETED,
    OUTCOME_LOADED,
    OUTCOME_REFUSED_ACTIVE,
    OUTCOME_REFUSED_ALREADY_ACTIVE,
    OUTCOME_REFUSED_ALREADY_LOADED,
    OUTCOME_REFUSED_CHECKSUM_MISMATCH,
    OUTCOME_REFUSED_NO_ENGINE_SLOT,
    OUTCOME_REFUSED_NOT_ACTIVE,
    OUTCOME_REFUSED_NOT_LOADED,
    OUTCOME_REFUSED_OVER_ENGINE_LIMIT,
    OUTCOME_REFUSED_PROTECTED,
    OUTCOME_REFUSED_STORE_FULL,
    OUTCOME_REFUSED_VERSION_CONFLICT,
    OUTCOME_STOPPED,
    activate_procedure,
    active_count,
    apply_operations,
    assess_command_sequence,
    code_checksum,
    code_octets,
    create_store,
    delete_procedure,
    free_engine_slots,
    free_octets,
    is_active,
    is_loaded,
    load_procedure,
    report_store,
    stop_procedure,
    upload_is_intact,
    used_octets,
    validate_store,
    validate_upload,
)

IMAGE = "step heater_on; wait 30; step heater_off"


def upload(proc_id="OBCP-1", code=IMAGE, **kw):
    record = {"id": proc_id, "version": 1, "code": code}
    record.update(kw)
    return record


def signed(proc_id="OBCP-1", code=IMAGE, **kw):
    return upload(proc_id, code, declared_checksum=code_checksum(code), **kw)


def store_with(*uploads, **kw):
    store = create_store(
        kw.get("capacity", 4096), kw.get("max_active", 2),
        kw.get("max_procedure_octets"),
    )
    for item in uploads:
        store, _ = load_procedure(store, item)
    return store


class TestImageValidation(unittest.TestCase):
    def test_upload_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_upload(["OBCP-1"])

    def test_an_empty_code_image_raises(self):
        with self.assertRaises(ValueError):
            validate_upload(upload(code=""))

    def test_version_zero_raises(self):
        with self.assertRaises(ValueError):
            validate_upload(upload(version=0))

    def test_a_non_boolean_permanent_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_upload(upload(permanent="yes"))

    def test_octets_follow_the_encoded_image(self):
        self.assertEqual(code_octets(IMAGE), len(IMAGE.encode("utf-8")))

    def test_a_matching_checksum_is_intact(self):
        self.assertTrue(upload_is_intact(signed()))

    def test_a_flipped_image_fails_its_declared_checksum(self):
        corrupted = signed()
        corrupted["code"] = IMAGE.replace("30", "90")
        self.assertFalse(upload_is_intact(corrupted))

    def test_no_declared_checksum_promises_nothing(self):
        self.assertTrue(upload_is_intact(upload()))


class TestStoreValidation(unittest.TestCase):
    def test_zero_capacity_raises(self):
        with self.assertRaises(ValueError):
            create_store(0, 2)

    def test_zero_engine_slots_raises(self):
        with self.assertRaises(ValueError):
            create_store(4096, 0)

    def test_a_procedure_limit_above_the_store_raises(self):
        with self.assertRaises(ValueError):
            create_store(1024, 2, 4096)

    def test_a_mismatched_load_order_raises(self):
        store = store_with(upload())
        store["load_order"] = []
        with self.assertRaises(ValueError):
            validate_store(store)

    def test_more_active_procedures_than_slots_raises(self):
        store = store_with(upload("A"), upload("B"), max_active=1)
        store["procedures"]["A"]["active"] = True
        store["procedures"]["B"]["active"] = True
        with self.assertRaises(ValueError):
            validate_store(store)


class TestLoading(unittest.TestCase):
    def test_a_clean_image_loads(self):
        store, outcome = load_procedure(create_store(4096, 2), signed())
        self.assertEqual(outcome, OUTCOME_LOADED)
        self.assertTrue(is_loaded(store, "OBCP-1"))

    def test_a_repeated_uplink_of_the_same_version_is_refused(self):
        store = store_with(upload())
        store, outcome = load_procedure(store, upload())
        self.assertEqual(outcome, OUTCOME_REFUSED_ALREADY_LOADED)

    def test_a_different_version_on_an_occupied_id_is_refused(self):
        store = store_with(upload())
        store, outcome = load_procedure(store, upload(version=2))
        self.assertEqual(outcome, OUTCOME_REFUSED_VERSION_CONFLICT)

    def test_a_corrupted_uplink_is_refused_on_its_checksum(self):
        corrupted = signed()
        corrupted["code"] = IMAGE.replace("30", "90")
        store, outcome = load_procedure(create_store(4096, 2), corrupted)
        self.assertEqual(outcome, OUTCOME_REFUSED_CHECKSUM_MISMATCH)
        self.assertFalse(is_loaded(store, "OBCP-1"))

    def test_a_full_store_refuses_the_next_image(self):
        store = create_store(code_octets(IMAGE), 2)
        store, first = load_procedure(store, upload("A"))
        store, second = load_procedure(store, upload("B"))
        self.assertEqual(first, OUTCOME_LOADED)
        self.assertEqual(second, OUTCOME_REFUSED_STORE_FULL)

    def test_an_image_exactly_filling_the_store_still_loads(self):
        store, outcome = load_procedure(
            create_store(code_octets(IMAGE), 2), upload()
        )
        self.assertEqual(outcome, OUTCOME_LOADED)
        self.assertEqual(free_octets(store), 0)

    def test_an_image_over_the_engine_limit_is_refused_before_the_store(self):
        store = create_store(4096, 2, 8)
        store, outcome = load_procedure(store, upload())
        self.assertEqual(outcome, OUTCOME_REFUSED_OVER_ENGINE_LIMIT)

    def test_a_refused_load_consumes_no_space(self):
        store = store_with(upload("A"))
        before = used_octets(store)
        store, _ = load_procedure(store, upload("A", version=3))
        self.assertEqual(used_octets(store), before)


class TestActivation(unittest.TestCase):
    def test_activating_an_absent_procedure_is_refused(self):
        store, outcome = activate_procedure(create_store(4096, 2), "OBCP-9")
        self.assertEqual(outcome, OUTCOME_REFUSED_NOT_LOADED)

    def test_a_loaded_procedure_activates(self):
        store, outcome = activate_procedure(store_with(upload()), "OBCP-1")
        self.assertEqual(outcome, OUTCOME_ACTIVATED)
        self.assertTrue(is_active(store, "OBCP-1"))

    def test_activating_twice_is_refused_not_ignored(self):
        store, _ = activate_procedure(store_with(upload()), "OBCP-1")
        store, outcome = activate_procedure(store, "OBCP-1")
        self.assertEqual(outcome, OUTCOME_REFUSED_ALREADY_ACTIVE)
        self.assertEqual(active_count(store), 1)

    def test_the_engine_refuses_a_run_past_its_slot_count(self):
        store = store_with(upload("A"), upload("B"), max_active=1)
        store, _ = activate_procedure(store, "A")
        store, outcome = activate_procedure(store, "B")
        self.assertEqual(outcome, OUTCOME_REFUSED_NO_ENGINE_SLOT)
        self.assertEqual(free_engine_slots(store), 0)

    def test_stopping_frees_the_slot_for_the_next_procedure(self):
        store = store_with(upload("A"), upload("B"), max_active=1)
        store, _ = activate_procedure(store, "A")
        store, stopped = stop_procedure(store, "A")
        store, outcome = activate_procedure(store, "B")
        self.assertEqual(stopped, OUTCOME_STOPPED)
        self.assertEqual(outcome, OUTCOME_ACTIVATED)

    def test_stopping_an_idle_procedure_is_refused(self):
        store, outcome = stop_procedure(store_with(upload()), "OBCP-1")
        self.assertEqual(outcome, OUTCOME_REFUSED_NOT_ACTIVE)

    def test_stopping_an_absent_procedure_is_refused_as_not_loaded(self):
        store, outcome = stop_procedure(create_store(4096, 2), "OBCP-9")
        self.assertEqual(outcome, OUTCOME_REFUSED_NOT_LOADED)


class TestDeletion(unittest.TestCase):
    def test_deleting_an_absent_procedure_is_refused(self):
        store, outcome = delete_procedure(create_store(4096, 2), "OBCP-9")
        self.assertEqual(outcome, OUTCOME_REFUSED_NOT_LOADED)

    def test_an_idle_procedure_deletes_and_returns_its_octets(self):
        store = store_with(upload())
        store, outcome = delete_procedure(store, "OBCP-1")
        self.assertEqual(outcome, OUTCOME_DELETED)
        self.assertEqual(used_octets(store), 0)

    def test_a_running_procedure_cannot_be_deleted(self):
        store, _ = activate_procedure(store_with(upload()), "OBCP-1")
        store, outcome = delete_procedure(store, "OBCP-1")
        self.assertEqual(outcome, OUTCOME_REFUSED_ACTIVE)
        self.assertTrue(is_loaded(store, "OBCP-1"))

    def test_a_permanent_procedure_cannot_be_deleted(self):
        store = store_with(upload(permanent=True))
        store, outcome = delete_procedure(store, "OBCP-1")
        self.assertEqual(outcome, OUTCOME_REFUSED_PROTECTED)

    def test_stopping_first_makes_deletion_possible(self):
        store, _ = activate_procedure(store_with(upload()), "OBCP-1")
        store, _ = stop_procedure(store, "OBCP-1")
        store, outcome = delete_procedure(store, "OBCP-1")
        self.assertEqual(outcome, OUTCOME_DELETED)

    def test_deleting_frees_the_id_for_a_new_version(self):
        store = store_with(upload())
        store, _ = delete_procedure(store, "OBCP-1")
        store, outcome = load_procedure(store, upload(version=2))
        self.assertEqual(outcome, OUTCOME_LOADED)


class TestSequences(unittest.TestCase):
    def test_operations_must_be_a_list(self):
        with self.assertRaises(ValueError):
            apply_operations(create_store(4096, 2), "load")

    def test_an_unknown_operation_raises(self):
        with self.assertRaises(ValueError):
            apply_operations(
                create_store(4096, 2), [{"operation": "reboot", "id": "A"}]
            )

    def test_a_clean_sequence_is_all_accepted(self):
        result = assess_command_sequence(
            {"capacity_octets": 4096, "max_active": 2},
            [
                {"operation": OPERATION_LOAD, "upload": signed("A")},
                {"operation": OPERATION_ACTIVATE, "id": "A"},
                {"operation": OPERATION_STOP, "id": "A"},
                {"operation": OPERATION_DELETE, "id": "A"},
            ],
        )
        self.assertTrue(result["all_accepted"])
        self.assertEqual(result["store"]["procedure_count"], 0)

    def test_the_first_refusal_is_named(self):
        result = assess_command_sequence(
            {"capacity_octets": 4096, "max_active": 2},
            [
                {"operation": OPERATION_LOAD, "upload": signed("A")},
                {"operation": OPERATION_DELETE, "id": "B"},
                {"operation": OPERATION_ACTIVATE, "id": "A"},
            ],
        )
        self.assertEqual(result["first_refusal"]["outcome"],
                         OUTCOME_REFUSED_NOT_LOADED)
        self.assertEqual(result["refused_count"], 1)

    def test_outcomes_are_grouped(self):
        result = assess_command_sequence(
            {"capacity_octets": 4096, "max_active": 1},
            [
                {"operation": OPERATION_LOAD, "upload": signed("A")},
                {"operation": OPERATION_LOAD, "upload": signed("B")},
                {"operation": OPERATION_ACTIVATE, "id": "A"},
                {"operation": OPERATION_ACTIVATE, "id": "B"},
            ],
        )
        self.assertEqual(result["grouped_by_outcome"][OUTCOME_LOADED],
                         ["A", "B"])
        self.assertEqual(
            result["grouped_by_outcome"][OUTCOME_REFUSED_NO_ENGINE_SLOT], ["B"]
        )

    def test_the_report_keeps_load_order(self):
        store = store_with(upload("B"), upload("A"))
        self.assertEqual(report_store(store)["loaded_ids"], ["B", "A"])

    def test_fill_fraction_is_exact_at_a_full_store(self):
        store = store_with(upload(), capacity=code_octets(IMAGE))
        self.assertAlmostEqual(report_store(store)["fill_fraction"], 1.0,
                               places=9)

    def test_permanent_procedures_are_listed_in_the_report(self):
        store = store_with(upload("A", permanent=True), upload("B"))
        self.assertEqual(report_store(store)["permanent_ids"], ["A"])


if __name__ == "__main__":
    unittest.main()
