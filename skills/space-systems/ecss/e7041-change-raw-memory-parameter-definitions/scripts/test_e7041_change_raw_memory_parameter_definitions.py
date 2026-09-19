"""Contract test for the e7041 raw memory parameter definition change leaf."""

import unittest

from e7041_change_raw_memory_parameter_definitions_logic import (
    REFUSAL_MISALIGNED,
    REFUSAL_OUT_OF_BOUNDS,
    REFUSAL_UNKNOWN_AREA,
    REFUSAL_UNKNOWN_PARAMETER,
    REFUSAL_WRONG_LENGTH,
    VERDICT_APPLIED,
    VERDICT_FAILED_START,
    VERDICT_PARTIAL,
    apply_changes,
    assess_change_request,
    outcome_accounts_for_request,
    overlap_hazards,
    region_end,
    regions_overlap,
    screen_changes,
    validate_change,
    validate_changes,
    validate_definition_store,
    validate_memory_area,
    validate_memory_map,
    validate_raw_memory_parameter,
)


def area(area_id="MEM-SRAM", size_bytes=1024, alignment_bytes=4):
    return {"id": area_id, "size_bytes": size_bytes, "alignment_bytes": alignment_bytes}


def areas():
    return [area("MEM-SRAM", 1024, 4), area("MEM-EEPROM", 256, 1)]


def parameter(parameter_id="RMP-MODE-WORD", width_bytes=4,
              memory_area_id="MEM-SRAM", base_address=0, length_bytes=4):
    return {
        "parameter_id": parameter_id,
        "width_bytes": width_bytes,
        "memory_area_id": memory_area_id,
        "base_address": base_address,
        "length_bytes": length_bytes,
    }


def store():
    return [
        parameter("RMP-MODE-WORD", 4, "MEM-SRAM", 0, 4),
        parameter("RMP-FAULT-COUNT", 2, "MEM-SRAM", 64, 2),
        parameter("RMP-SERIAL", 4, "MEM-EEPROM", 8, 4),
    ]


def change(parameter_id="RMP-MODE-WORD", memory_area_id="MEM-SRAM",
           base_address=128, length_bytes=4):
    return {
        "parameter_id": parameter_id,
        "memory_area_id": memory_area_id,
        "base_address": base_address,
        "length_bytes": length_bytes,
    }


class TestMemoryMap(unittest.TestCase):
    def test_a_valid_area_normalizes(self):
        record = validate_memory_area(area())
        self.assertEqual(record["size_bytes"], 1024)
        self.assertEqual(record["alignment_bytes"], 4)

    def test_alignment_defaults_to_one_byte(self):
        record = validate_memory_area({"id": "MEM-X", "size_bytes": 16})
        self.assertEqual(record["alignment_bytes"], 1)

    def test_a_zero_sized_area_raises(self):
        with self.assertRaises(ValueError):
            validate_memory_area(area(size_bytes=0))

    def test_a_zero_alignment_raises(self):
        with self.assertRaises(ValueError):
            validate_memory_area(area(alignment_bytes=0))

    def test_a_non_mapping_area_raises(self):
        with self.assertRaises(ValueError):
            validate_memory_area("MEM-SRAM")

    def test_a_duplicate_area_raises(self):
        with self.assertRaises(ValueError):
            validate_memory_map([area("MEM-SRAM"), area("MEM-SRAM")])

    def test_a_non_list_memory_map_raises(self):
        with self.assertRaises(ValueError):
            validate_memory_map(area())


class TestDefinitionStore(unittest.TestCase):
    def test_a_valid_definition_normalizes(self):
        record = validate_raw_memory_parameter(parameter())
        self.assertEqual(record["parameter_id"], "RMP-MODE-WORD")
        self.assertEqual(record["length_bytes"], 4)

    def test_a_non_mapping_definition_raises(self):
        with self.assertRaises(ValueError):
            validate_raw_memory_parameter("RMP-MODE-WORD")

    def test_a_negative_base_raises(self):
        with self.assertRaises(ValueError):
            validate_raw_memory_parameter(parameter(base_address=-4))

    def test_a_zero_length_raises(self):
        with self.assertRaises(ValueError):
            validate_raw_memory_parameter(parameter(length_bytes=0))

    def test_a_zero_base_is_a_valid_window(self):
        self.assertEqual(
            validate_raw_memory_parameter(parameter(base_address=0))["base_address"], 0
        )

    def test_a_duplicate_parameter_raises(self):
        with self.assertRaises(ValueError):
            validate_definition_store([parameter("RMP-A"), parameter("RMP-A")])

    def test_a_non_list_store_raises(self):
        with self.assertRaises(ValueError):
            validate_definition_store(parameter())


class TestGeometryHelpers(unittest.TestCase):
    def test_the_region_end_is_one_past_the_last_byte(self):
        self.assertEqual(region_end(64, 4), 68)

    def test_a_region_end_uses_exact_integer_arithmetic(self):
        self.assertIsInstance(region_end(1 << 20, 4), int)
        self.assertEqual(region_end(1 << 20, 4), (1 << 20) + 4)

    def test_two_disjoint_windows_do_not_overlap(self):
        self.assertFalse(
            regions_overlap(parameter(base_address=0, length_bytes=4),
                            parameter(base_address=4, length_bytes=4))
        )

    def test_two_windows_sharing_a_byte_overlap(self):
        self.assertTrue(
            regions_overlap(parameter(base_address=0, length_bytes=4),
                            parameter(base_address=3, length_bytes=4))
        )

    def test_windows_in_different_areas_never_overlap(self):
        self.assertFalse(
            regions_overlap(
                parameter(memory_area_id="MEM-SRAM", base_address=0),
                parameter(memory_area_id="MEM-EEPROM", base_address=0),
            )
        )

    def test_a_disjoint_store_carries_no_hazards(self):
        self.assertEqual(overlap_hazards(store()), [])

    def test_an_overlapping_store_names_the_pair(self):
        records = store()
        records[1]["base_address"] = 2
        self.assertEqual(overlap_hazards(records), [("RMP-MODE-WORD", "RMP-FAULT-COUNT")])


class TestChangeNormalization(unittest.TestCase):
    def test_a_valid_change_normalizes(self):
        item = validate_change(change(), 0)
        self.assertEqual(item["base_address"], 128)

    def test_a_change_without_an_area_raises(self):
        record = change()
        del record["memory_area_id"]
        with self.assertRaises(ValueError):
            validate_change(record, 0)

    def test_a_change_without_a_length_raises(self):
        record = change()
        del record["length_bytes"]
        with self.assertRaises(ValueError):
            validate_change(record, 0)

    def test_a_non_mapping_change_raises(self):
        with self.assertRaises(ValueError):
            validate_change("RMP-MODE-WORD", 0)

    def test_an_empty_request_is_refused_rather_than_a_no_op_success(self):
        with self.assertRaises(ValueError):
            validate_changes([])

    def test_a_non_list_request_raises(self):
        with self.assertRaises(ValueError):
            validate_changes(change())

    def test_request_order_is_preserved(self):
        request = validate_changes([change("RMP-B"), change("RMP-A")])
        self.assertEqual(
            [item["parameter_id"] for item in request["changes"]], ["RMP-B", "RMP-A"]
        )

    def test_a_parameter_changed_twice_collapses_to_the_last_change(self):
        request = validate_changes(
            [change("RMP-A", base_address=16), change("RMP-A", base_address=32)]
        )
        self.assertEqual(request["distinct_count"], 1)
        self.assertEqual(request["changes"][0]["base_address"], 32)
        self.assertEqual(request["repeated"], ["RMP-A"])
        self.assertEqual(request["submitted_count"], 2)


class TestScreening(unittest.TestCase):
    def test_a_sound_change_is_acceptable(self):
        screening = screen_changes(store(), areas(), [change()])
        self.assertEqual(len(screening["acceptable"]), 1)
        self.assertEqual(screening["refused"], [])

    def test_an_unknown_parameter_is_refused(self):
        screening = screen_changes(store(), areas(), [change("RMP-GHOST")])
        self.assertEqual(screening["refused"][0]["refusal"], REFUSAL_UNKNOWN_PARAMETER)

    def test_an_unknown_memory_area_is_refused(self):
        screening = screen_changes(
            store(), areas(), [change(memory_area_id="MEM-FLASH")]
        )
        self.assertEqual(screening["refused"][0]["refusal"], REFUSAL_UNKNOWN_AREA)

    def test_a_region_running_past_the_area_end_is_refused(self):
        screening = screen_changes(store(), areas(), [change(base_address=1022)])
        self.assertEqual(screening["refused"][0]["refusal"], REFUSAL_OUT_OF_BOUNDS)

    def test_a_region_ending_exactly_at_the_area_end_is_accepted(self):
        screening = screen_changes(store(), areas(), [change(base_address=1020)])
        self.assertEqual(screening["refused"], [])
        self.assertEqual(len(screening["acceptable"]), 1)

    def test_a_base_breaking_the_area_alignment_is_refused(self):
        screening = screen_changes(store(), areas(), [change(base_address=130)])
        self.assertEqual(screening["refused"][0]["refusal"], REFUSAL_MISALIGNED)

    def test_the_same_base_is_accepted_in_a_byte_aligned_area(self):
        screening = screen_changes(
            store(),
            areas(),
            [change("RMP-SERIAL", memory_area_id="MEM-EEPROM", base_address=13)],
        )
        self.assertEqual(screening["refused"], [])

    def test_a_length_disagreeing_with_the_representation_is_refused(self):
        screening = screen_changes(store(), areas(), [change(length_bytes=8)])
        self.assertEqual(screening["refused"][0]["refusal"], REFUSAL_WRONG_LENGTH)

    def test_a_short_length_is_refused_even_though_it_is_in_bounds(self):
        screening = screen_changes(store(), areas(), [change(length_bytes=2)])
        self.assertEqual(screening["refused"][0]["refusal"], REFUSAL_WRONG_LENGTH)

    def test_bounds_are_reported_before_alignment_when_both_are_wrong(self):
        screening = screen_changes(store(), areas(), [change(base_address=1023)])
        self.assertEqual(screening["refused"][0]["refusal"], REFUSAL_OUT_OF_BOUNDS)

    def test_alignment_is_reported_before_length_when_both_are_wrong(self):
        screening = screen_changes(
            store(), areas(), [change(base_address=130, length_bytes=8)]
        )
        self.assertEqual(screening["refused"][0]["refusal"], REFUSAL_MISALIGNED)

    def test_a_refused_sibling_does_not_remove_an_acceptable_change(self):
        screening = screen_changes(
            store(), areas(), [change("RMP-GHOST"), change()]
        )
        self.assertEqual(len(screening["acceptable"]), 1)
        self.assertEqual(len(screening["refused"]), 1)


class TestApplication(unittest.TestCase):
    def test_an_acceptable_change_moves_the_window(self):
        outcome = apply_changes(store(), areas(), [change()])
        self.assertTrue(outcome["applied"])
        moved = [p for p in outcome["store"] if p["parameter_id"] == "RMP-MODE-WORD"]
        self.assertEqual(moved[0]["base_address"], 128)

    def test_the_original_store_is_not_mutated(self):
        records = store()
        apply_changes(records, areas(), [change()])
        self.assertEqual(records[0]["base_address"], 0)

    def test_a_change_records_the_previous_window(self):
        outcome = apply_changes(store(), areas(), [change()])
        previous = outcome["changed"][0]["previous_window"]
        self.assertEqual(previous["base_address"], 0)
        self.assertEqual(previous["memory_area_id"], "MEM-SRAM")

    def test_an_untouched_definition_keeps_its_window(self):
        outcome = apply_changes(store(), areas(), [change()])
        untouched = [p for p in outcome["store"] if p["parameter_id"] == "RMP-SERIAL"]
        self.assertEqual(untouched[0]["base_address"], 8)

    def test_a_refused_change_leaves_that_definition_on_its_old_window(self):
        outcome = apply_changes(
            store(), areas(), [change(), change("RMP-FAULT-COUNT", length_bytes=8)]
        )
        self.assertTrue(outcome["applied"])
        kept = [p for p in outcome["store"] if p["parameter_id"] == "RMP-FAULT-COUNT"]
        self.assertEqual(kept[0]["base_address"], 64)
        self.assertEqual(len(outcome["changed"]), 1)

    def test_a_request_with_nothing_acceptable_alters_nothing(self):
        outcome = apply_changes(store(), areas(), [change("RMP-GHOST")])
        self.assertFalse(outcome["applied"])
        self.assertEqual(outcome["changed"], [])
        self.assertEqual(outcome["store"][0]["base_address"], 0)

    def test_the_last_change_wins_on_a_repeated_parameter(self):
        outcome = apply_changes(
            store(),
            areas(),
            [change(base_address=128), change(base_address=256)],
        )
        self.assertEqual(len(outcome["changed"]), 1)
        self.assertEqual(outcome["changed"][0]["window"]["base_address"], 256)

    def test_the_changes_follow_request_order(self):
        outcome = apply_changes(
            store(),
            areas(),
            [
                change("RMP-FAULT-COUNT", base_address=200, length_bytes=2),
                change("RMP-MODE-WORD", base_address=128),
            ],
        )
        self.assertEqual(
            [item["parameter_id"] for item in outcome["changed"]],
            ["RMP-FAULT-COUNT", "RMP-MODE-WORD"],
        )

    def test_a_change_can_move_a_parameter_to_another_area(self):
        outcome = apply_changes(
            store(),
            areas(),
            [change("RMP-MODE-WORD", memory_area_id="MEM-EEPROM", base_address=16)],
        )
        moved = [p for p in outcome["store"] if p["parameter_id"] == "RMP-MODE-WORD"]
        self.assertEqual(moved[0]["memory_area_id"], "MEM-EEPROM")


class TestAccounting(unittest.TestCase):
    def test_a_clean_outcome_accounts_for_every_change(self):
        outcome = apply_changes(store(), areas(), [change()])
        self.assertTrue(outcome_accounts_for_request(outcome)["accounted"])

    def test_a_mixed_outcome_accounts_for_every_change(self):
        outcome = apply_changes(store(), areas(), [change(), change("RMP-GHOST")])
        self.assertTrue(outcome_accounts_for_request(outcome)["accounted"])

    def test_a_dropped_change_is_detected(self):
        outcome = apply_changes(
            store(),
            areas(),
            [
                change("RMP-FAULT-COUNT", base_address=200, length_bytes=2),
                change("RMP-MODE-WORD", base_address=128),
            ],
        )
        outcome["changed"] = outcome["changed"][:1]
        self.assertFalse(outcome_accounts_for_request(outcome)["accounted"])

    def test_a_refusal_reason_outside_the_declared_set_is_detected(self):
        outcome = apply_changes(store(), areas(), [change(), change("RMP-GHOST")])
        outcome["refused"][0]["refusal"] = "because-i-said-so"
        self.assertFalse(outcome_accounts_for_request(outcome)["accounted"])

    def test_a_non_mapping_outcome_raises(self):
        with self.assertRaises(ValueError):
            outcome_accounts_for_request(["changed"])

    def test_an_outcome_without_a_screening_record_raises(self):
        with self.assertRaises(ValueError):
            outcome_accounts_for_request({"changed": [], "refused": []})


class TestFullAssessment(unittest.TestCase):
    def test_a_clean_request_is_applied(self):
        result = assess_change_request(store(), areas(), [change()])
        self.assertEqual(result["verdict"], VERDICT_APPLIED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["changed_ids"], ["RMP-MODE-WORD"])

    def test_a_mixed_request_is_partially_applied(self):
        result = assess_change_request(
            store(), areas(), [change(), change("RMP-GHOST")]
        )
        self.assertEqual(result["verdict"], VERDICT_PARTIAL)
        self.assertEqual(result["applied_count"], 1)
        self.assertEqual(result["refused_count"], 1)

    def test_a_request_with_nothing_acceptable_fails_at_start(self):
        result = assess_change_request(store(), areas(), [change("RMP-GHOST")])
        self.assertEqual(result["verdict"], VERDICT_FAILED_START)
        self.assertFalse(result["applied"])

    def test_each_refusal_is_named_with_its_own_reason(self):
        result = assess_change_request(
            store(),
            areas(),
            [
                change("RMP-GHOST"),
                change("RMP-FAULT-COUNT", base_address=130, length_bytes=2),
                change(),
            ],
        )
        self.assertEqual(
            [item["refusal"] for item in result["refused"]],
            [REFUSAL_UNKNOWN_PARAMETER, REFUSAL_MISALIGNED],
        )

    def test_a_new_overlap_is_applied_and_raised_as_a_hazard(self):
        result = assess_change_request(
            store(), areas(), [change("RMP-FAULT-COUNT", base_address=0, length_bytes=2)]
        )
        self.assertEqual(result["verdict"], VERDICT_APPLIED)
        self.assertEqual(result["new_overlaps"], [("RMP-MODE-WORD", "RMP-FAULT-COUNT")])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_pre_existing_overlap_is_not_raised_again(self):
        records = store()
        records[1]["base_address"] = 2
        result = assess_change_request(
            records, areas(), [change("RMP-SERIAL", "MEM-EEPROM", 16, 4)]
        )
        self.assertEqual(result["new_overlaps"], [])
        self.assertEqual(len(result["overlaps_before"]), 1)

    def test_a_repeated_parameter_is_raised_as_a_finding(self):
        result = assess_change_request(
            store(), areas(), [change(base_address=128), change(base_address=256)]
        )
        self.assertEqual(result["verdict"], VERDICT_APPLIED)
        self.assertEqual(len(result["findings"]), 1)

    def test_an_invalid_store_entry_raises_before_anything_is_applied(self):
        broken = store()
        broken[0]["length_bytes"] = 0
        with self.assertRaises(ValueError):
            assess_change_request(broken, areas(), [change()])

    def test_an_empty_request_raises_before_anything_is_applied(self):
        with self.assertRaises(ValueError):
            assess_change_request(store(), areas(), [])


if __name__ == "__main__":
    unittest.main()
