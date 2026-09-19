"""Contract test for the e7041 parameter setting leaf."""

import unittest

from e7041_set_parameter_values_logic import (
    REFUSAL_OUT_OF_DOMAIN,
    REFUSAL_READ_ONLY,
    REFUSAL_UNKNOWN,
    VERDICT_APPLIED,
    VERDICT_FAILED_START,
    VERDICT_PARTIAL,
    apply_settings,
    assess_set_request,
    outcome_accounts_for_request,
    representable_domain,
    screen_instructions,
    validate_instruction,
    validate_instructions,
    validate_parameter,
    validate_store,
    value_suits_parameter,
)


def parameter(parameter_id="PAR-HEATER-SETPOINT", apid="AP-THM",
              representation="unsigned-integer", value=20, **kw):
    record = {
        "application_process_id": apid,
        "parameter_id": parameter_id,
        "representation": representation,
        "value": value,
    }
    if representation in ("unsigned-integer", "signed-integer"):
        record.setdefault("bits", 8)
    record.update(kw)
    return record


def store():
    return [
        parameter("PAR-HEATER-SETPOINT", "AP-THM", value=20, upper_limit=100),
        parameter("PAR-DUTY-CYCLE", "AP-THM", value=50),
        parameter("PAR-SERIAL-NUMBER", "AP-THM", value=7, access="read-only"),
        parameter("PAR-HEATER-SETPOINT", "AP-PWR", value=90),
    ]


def instruction(parameter_id="PAR-HEATER-SETPOINT", value=30):
    return {"parameter_id": parameter_id, "value": value}


class TestStoreValidation(unittest.TestCase):
    def test_a_valid_parameter_normalizes(self):
        record = validate_parameter(parameter())
        self.assertEqual(record["access"], "read-write")
        self.assertEqual(record["domain"], {"lower": 0, "upper": 255})

    def test_a_non_mapping_parameter_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter("PAR-HEATER-SETPOINT")

    def test_a_parameter_with_no_current_value_raises(self):
        record = parameter()
        del record["value"]
        with self.assertRaises(ValueError):
            validate_parameter(record)

    def test_an_unknown_access_mode_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter(parameter(access="write-only"))

    def test_declared_limits_narrow_the_domain(self):
        record = validate_parameter(parameter(upper_limit=100))
        self.assertEqual(record["domain"], {"lower": 0, "upper": 100})

    def test_a_repeated_identifier_in_one_process_raises(self):
        with self.assertRaises(ValueError):
            validate_store([parameter("PAR-A"), parameter("PAR-A")])

    def test_the_same_name_under_another_process_is_another_parameter(self):
        self.assertEqual(len(validate_store(store())), 4)

    def test_a_non_list_store_raises(self):
        with self.assertRaises(ValueError):
            validate_store(parameter())

    def test_an_integer_domain_is_derived_with_exact_arithmetic(self):
        self.assertEqual(
            representable_domain("signed-integer", 32)["lower"], -(1 << 31)
        )


class TestInstructionNormalization(unittest.TestCase):
    def test_a_valid_instruction_normalizes(self):
        item = validate_instruction(instruction(), 0)
        self.assertEqual(item["parameter_id"], "PAR-HEATER-SETPOINT")
        self.assertEqual(item["value"], 30)

    def test_an_instruction_without_a_value_raises(self):
        with self.assertRaises(ValueError):
            validate_instruction({"parameter_id": "PAR-A"}, 0)

    def test_an_instruction_without_an_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_instruction({"value": 3}, 0)

    def test_a_non_mapping_instruction_raises(self):
        with self.assertRaises(ValueError):
            validate_instruction("PAR-A", 0)

    def test_an_empty_request_is_refused_rather_than_a_no_op_success(self):
        with self.assertRaises(ValueError):
            validate_instructions([])

    def test_a_non_list_request_raises(self):
        with self.assertRaises(ValueError):
            validate_instructions(instruction())

    def test_request_order_is_preserved(self):
        request = validate_instructions(
            [instruction("PAR-B", 1), instruction("PAR-A", 2)]
        )
        self.assertEqual(
            [item["parameter_id"] for item in request["instructions"]],
            ["PAR-B", "PAR-A"],
        )

    def test_a_parameter_named_twice_collapses_to_the_last_instruction(self):
        request = validate_instructions(
            [instruction("PAR-A", 1), instruction("PAR-A", 9)]
        )
        self.assertEqual(request["distinct_count"], 1)
        self.assertEqual(request["instructions"][0]["value"], 9)
        self.assertEqual(request["repeated"], ["PAR-A"])

    def test_the_submitted_count_still_records_what_arrived(self):
        request = validate_instructions(
            [instruction("PAR-A", 1), instruction("PAR-A", 9)]
        )
        self.assertEqual(request["submitted_count"], 2)


class TestValueSuitability(unittest.TestCase):
    def test_a_value_inside_the_domain_suits(self):
        self.assertTrue(value_suits_parameter(parameter(), 30)["suits"])

    def test_a_value_on_the_upper_bound_suits(self):
        self.assertTrue(value_suits_parameter(parameter(upper_limit=100), 100)["suits"])

    def test_a_value_past_the_engineering_limit_does_not_suit(self):
        result = value_suits_parameter(parameter(upper_limit=100), 101)
        self.assertFalse(result["suits"])
        self.assertIn("upper", result["reason"])

    def test_a_value_past_the_representation_does_not_suit(self):
        self.assertFalse(value_suits_parameter(parameter(), 256)["suits"])

    def test_a_negative_value_does_not_suit_an_unsigned_parameter(self):
        self.assertFalse(value_suits_parameter(parameter(), -1)["suits"])

    def test_a_fractional_value_does_not_suit_an_integer_parameter(self):
        self.assertFalse(value_suits_parameter(parameter(), 30.5)["suits"])

    def test_a_boolean_parameter_takes_only_booleans(self):
        record = parameter(representation="boolean", value=False)
        self.assertTrue(value_suits_parameter(record, True)["suits"])
        self.assertFalse(value_suits_parameter(record, 1)["suits"])

    def test_normalizing_a_normalized_parameter_keeps_its_limits(self):
        once = validate_parameter(parameter(upper_limit=100))
        self.assertEqual(validate_parameter(once)["domain"], {"lower": 0, "upper": 100})

    def test_a_normalized_parameter_still_refuses_a_value_past_its_limit(self):
        once = validate_parameter(parameter(upper_limit=100))
        self.assertFalse(value_suits_parameter(once, 200)["suits"])

    def test_a_real_value_on_its_declared_bound_suits(self):
        record = parameter(
            representation="real", value=0.0, lower_limit=0.0, upper_limit=1.0
        )
        self.assertTrue(value_suits_parameter(record, 1.0)["suits"])
        self.assertAlmostEqual(validate_parameter(record)["domain"]["upper"], 1.0, places=9)


class TestScreening(unittest.TestCase):
    def test_a_sound_instruction_is_applicable(self):
        screening = screen_instructions(store(), "AP-THM", [instruction()])
        self.assertEqual(len(screening["applicable"]), 1)
        self.assertEqual(screening["refused"], [])

    def test_an_unknown_parameter_is_refused_as_unknown(self):
        screening = screen_instructions(store(), "AP-THM", [instruction("PAR-GHOST")])
        self.assertEqual(screening["refused"][0]["refusal"], REFUSAL_UNKNOWN)

    def test_a_read_only_parameter_is_refused_as_read_only(self):
        screening = screen_instructions(
            store(), "AP-THM", [instruction("PAR-SERIAL-NUMBER", 9)]
        )
        self.assertEqual(screening["refused"][0]["refusal"], REFUSAL_READ_ONLY)

    def test_an_out_of_domain_value_is_refused_as_out_of_domain(self):
        screening = screen_instructions(
            store(), "AP-THM", [instruction("PAR-HEATER-SETPOINT", 200)]
        )
        self.assertEqual(screening["refused"][0]["refusal"], REFUSAL_OUT_OF_DOMAIN)

    def test_the_three_refusals_stay_distinct_in_one_request(self):
        screening = screen_instructions(
            store(),
            "AP-THM",
            [
                instruction("PAR-GHOST", 1),
                instruction("PAR-SERIAL-NUMBER", 9),
                instruction("PAR-HEATER-SETPOINT", 200),
            ],
        )
        self.assertEqual(
            [item["refusal"] for item in screening["refused"]],
            [REFUSAL_UNKNOWN, REFUSAL_READ_ONLY, REFUSAL_OUT_OF_DOMAIN],
        )

    def test_screening_is_scoped_to_the_named_application_process(self):
        screening = screen_instructions(store(), "AP-PWR", [instruction("PAR-DUTY-CYCLE")])
        self.assertEqual(screening["refused"][0]["refusal"], REFUSAL_UNKNOWN)

    def test_a_refused_sibling_does_not_remove_an_applicable_instruction(self):
        screening = screen_instructions(
            store(), "AP-THM", [instruction("PAR-GHOST", 1), instruction()]
        )
        self.assertEqual(len(screening["applicable"]), 1)
        self.assertEqual(len(screening["refused"]), 1)


class TestApplication(unittest.TestCase):
    def test_an_applicable_instruction_is_written(self):
        outcome = apply_settings(store(), "AP-THM", [instruction()])
        self.assertTrue(outcome["applied"])
        written = {p["parameter_id"]: p["value"] for p in outcome["store"]
                   if p["application_process_id"] == "AP-THM"}
        self.assertEqual(written["PAR-HEATER-SETPOINT"], 30)

    def test_the_original_store_is_not_mutated(self):
        records = store()
        apply_settings(records, "AP-THM", [instruction()])
        self.assertEqual(records[0]["value"], 20)

    def test_a_write_records_the_previous_value(self):
        outcome = apply_settings(store(), "AP-THM", [instruction()])
        self.assertEqual(outcome["writes"][0]["previous_value"], 20)
        self.assertEqual(outcome["writes"][0]["value"], 30)

    def test_a_parameter_of_another_process_is_left_alone(self):
        outcome = apply_settings(store(), "AP-THM", [instruction()])
        other = [p for p in outcome["store"] if p["application_process_id"] == "AP-PWR"]
        self.assertEqual(other[0]["value"], 90)

    def test_a_refused_instruction_does_not_withdraw_an_applied_one(self):
        outcome = apply_settings(
            store(), "AP-THM", [instruction(), instruction("PAR-GHOST", 1)]
        )
        self.assertTrue(outcome["applied"])
        self.assertEqual(len(outcome["writes"]), 1)
        self.assertEqual(len(outcome["refused"]), 1)

    def test_a_request_with_nothing_applicable_writes_nothing(self):
        outcome = apply_settings(store(), "AP-THM", [instruction("PAR-GHOST", 1)])
        self.assertFalse(outcome["applied"])
        self.assertEqual(outcome["writes"], [])
        self.assertEqual(outcome["store"][0]["value"], 20)

    def test_the_last_instruction_wins_on_a_repeated_parameter(self):
        outcome = apply_settings(
            store(),
            "AP-THM",
            [instruction("PAR-HEATER-SETPOINT", 31), instruction("PAR-HEATER-SETPOINT", 32)],
        )
        self.assertEqual(outcome["writes"][0]["value"], 32)
        self.assertEqual(len(outcome["writes"]), 1)

    def test_the_writes_follow_request_order(self):
        outcome = apply_settings(
            store(),
            "AP-THM",
            [instruction("PAR-DUTY-CYCLE", 60), instruction("PAR-HEATER-SETPOINT", 30)],
        )
        self.assertEqual(
            [write["parameter_id"] for write in outcome["writes"]],
            ["PAR-DUTY-CYCLE", "PAR-HEATER-SETPOINT"],
        )


class TestAccounting(unittest.TestCase):
    def test_a_clean_outcome_accounts_for_every_instruction(self):
        outcome = apply_settings(store(), "AP-THM", [instruction()])
        self.assertTrue(outcome_accounts_for_request(outcome)["accounted"])

    def test_a_mixed_outcome_accounts_for_every_instruction(self):
        outcome = apply_settings(
            store(), "AP-THM", [instruction(), instruction("PAR-GHOST", 1)]
        )
        self.assertTrue(outcome_accounts_for_request(outcome)["accounted"])

    def test_a_dropped_write_is_detected(self):
        outcome = apply_settings(
            store(),
            "AP-THM",
            [instruction("PAR-DUTY-CYCLE", 60), instruction("PAR-HEATER-SETPOINT", 30)],
        )
        outcome["writes"] = outcome["writes"][:1]
        self.assertFalse(outcome_accounts_for_request(outcome)["accounted"])

    def test_a_refusal_reason_outside_the_declared_set_is_detected(self):
        outcome = apply_settings(
            store(), "AP-THM", [instruction(), instruction("PAR-GHOST", 1)]
        )
        outcome["refused"][0]["refusal"] = "because-i-said-so"
        result = outcome_accounts_for_request(outcome)
        self.assertFalse(result["accounted"])

    def test_a_non_mapping_outcome_raises(self):
        with self.assertRaises(ValueError):
            outcome_accounts_for_request(["writes"])

    def test_an_outcome_without_a_screening_record_raises(self):
        with self.assertRaises(ValueError):
            outcome_accounts_for_request({"writes": [], "refused": []})


class TestFullAssessment(unittest.TestCase):
    def test_a_clean_request_is_applied(self):
        result = assess_set_request(store(), "AP-THM", [instruction()])
        self.assertEqual(result["verdict"], VERDICT_APPLIED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["written_ids"], ["PAR-HEATER-SETPOINT"])

    def test_a_mixed_request_is_partially_applied(self):
        result = assess_set_request(
            store(), "AP-THM", [instruction(), instruction("PAR-SERIAL-NUMBER", 9)]
        )
        self.assertEqual(result["verdict"], VERDICT_PARTIAL)
        self.assertEqual(result["applied_count"], 1)
        self.assertEqual(result["refused_count"], 1)

    def test_a_request_with_nothing_applicable_fails_at_start(self):
        result = assess_set_request(store(), "AP-THM", [instruction("PAR-GHOST", 1)])
        self.assertEqual(result["verdict"], VERDICT_FAILED_START)
        self.assertFalse(result["applied"])

    def test_each_refusal_is_named_with_its_own_reason(self):
        result = assess_set_request(
            store(),
            "AP-THM",
            [instruction(), instruction("PAR-SERIAL-NUMBER", 9), instruction("PAR-GHOST", 1)],
        )
        self.assertEqual(result["refused_ids"], ["PAR-SERIAL-NUMBER", "PAR-GHOST"])
        self.assertEqual(len(result["findings"]), 2)

    def test_a_repeated_parameter_is_raised_as_a_finding(self):
        result = assess_set_request(
            store(),
            "AP-THM",
            [instruction("PAR-HEATER-SETPOINT", 31), instruction("PAR-HEATER-SETPOINT", 32)],
        )
        self.assertEqual(result["verdict"], VERDICT_APPLIED)
        self.assertEqual(len(result["findings"]), 1)

    def test_the_returned_store_carries_the_new_value(self):
        result = assess_set_request(store(), "AP-THM", [instruction()])
        updated = [
            p for p in result["store"]
            if p["application_process_id"] == "AP-THM"
            and p["parameter_id"] == "PAR-HEATER-SETPOINT"
        ]
        self.assertEqual(updated[0]["value"], 30)

    def test_an_invalid_store_entry_raises_before_anything_is_written(self):
        broken = store()
        del broken[1]["value"]
        with self.assertRaises(ValueError):
            assess_set_request(broken, "AP-THM", [instruction()])

    def test_an_empty_request_raises_before_anything_is_written(self):
        with self.assertRaises(ValueError):
            assess_set_request(store(), "AP-THM", [])


if __name__ == "__main__":
    unittest.main()
