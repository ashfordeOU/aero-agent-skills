#!/usr/bin/env python3
"""Contract test for brazement records and furnace run data (offline)."""

import copy
import datetime
import unittest

from q7040_brazing_records_logic import (
    FIELD_ATMOSPHERE_LOG,
    FIELD_FLUX_BATCH,
    FIELD_FURNACE_RUN,
    FIELD_INSPECTION_RESULT,
    FIELD_QUALIFICATION_RECORD,
    FIELD_THERMAL_PROFILE,
    MINIMUM_LOAD_THERMOCOUPLES,
    OPERATOR_CURRENT,
    OPERATOR_EXPIRED,
    OPERATOR_LAPSED,
    PROCESS_FURNACE_VACUUM,
    PROCESS_TORCH,
    PROFILE_CHANNELS,
    PROFILE_COOLING_RATE,
    VERDICT_COMPLETE,
    VERDICT_INCOMPLETE,
    assess_brazement_record,
    furnace_data_gaps,
    missing_record_fields,
    operator_currency,
    required_record_fields,
)

DATE = datetime.date

GOOD_RUN = {
    "run_id": "FRN-2026-114",
    "channels_recorded": list(PROFILE_CHANNELS),
    "load_thermocouples": 3,
}

GOOD_CASE = {
    "brazement_id": "BRZ-7712",
    "process": PROCESS_FURNACE_VACUUM,
    "uses_flux": False,
    "braze_date": DATE(2026, 5, 12),
    "fields_present": required_record_fields(PROCESS_FURNACE_VACUUM, False),
    "operator_certificate_expiry": DATE(2027, 1, 31),
    "operator_last_process_run": DATE(2026, 4, 2),
    "furnace_run": GOOD_RUN,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class RequiredFieldTests(unittest.TestCase):
    def test_a_furnace_process_owes_the_run_trace_and_atmosphere_log(self):
        fields = required_record_fields(PROCESS_FURNACE_VACUUM, False)
        self.assertIn(FIELD_FURNACE_RUN, fields)
        self.assertIn(FIELD_THERMAL_PROFILE, fields)
        self.assertIn(FIELD_ATMOSPHERE_LOG, fields)

    def test_a_torch_process_owes_no_furnace_fields(self):
        fields = required_record_fields(PROCESS_TORCH, True)
        self.assertNotIn(FIELD_FURNACE_RUN, fields)
        self.assertNotIn(FIELD_ATMOSPHERE_LOG, fields)

    def test_only_a_fluxed_braze_owes_a_flux_batch_identity(self):
        self.assertIn(FIELD_FLUX_BATCH, required_record_fields(PROCESS_TORCH, True))
        self.assertNotIn(
            FIELD_FLUX_BATCH, required_record_fields(PROCESS_TORCH, False)
        )

    def test_every_process_owes_the_procedure_qualification_record(self):
        for process in (PROCESS_TORCH, PROCESS_FURNACE_VACUUM):
            self.assertIn(
                FIELD_QUALIFICATION_RECORD, required_record_fields(process, False)
            )

    def test_the_inspection_result_closes_every_required_set(self):
        self.assertEqual(
            required_record_fields(PROCESS_TORCH, False)[-1], FIELD_INSPECTION_RESULT
        )

    def test_a_non_boolean_flux_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            required_record_fields(PROCESS_TORCH, "yes")

    def test_gaps_come_back_in_the_order_the_set_requires_them(self):
        required = required_record_fields(PROCESS_TORCH, True)
        gaps = missing_record_fields(PROCESS_TORCH, True, [required[0]])
        self.assertEqual(gaps, required[1:])

    def test_an_unknown_field_name_on_the_record_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_record_fields(PROCESS_TORCH, False, ["the travellers folder"])


class OperatorCurrencyTests(unittest.TestCase):
    def test_a_recently_working_operator_inside_the_certificate_is_current(self):
        result = operator_currency(
            DATE(2027, 1, 31), DATE(2026, 4, 2), DATE(2026, 5, 12)
        )
        self.assertEqual(result["status"], OPERATOR_CURRENT)
        self.assertTrue(result["current"])

    def test_an_expired_certificate_outranks_good_continuity(self):
        result = operator_currency(
            DATE(2026, 5, 1), DATE(2026, 5, 10), DATE(2026, 5, 12)
        )
        self.assertEqual(result["status"], OPERATOR_EXPIRED)

    def test_a_long_gap_lapses_currency_even_inside_the_certificate(self):
        result = operator_currency(
            DATE(2027, 1, 31), DATE(2025, 9, 1), DATE(2026, 5, 12)
        )
        self.assertEqual(result["status"], OPERATOR_LAPSED)

    def test_a_gap_exactly_on_the_continuity_interval_is_still_current(self):
        result = operator_currency(
            DATE(2027, 1, 31),
            DATE(2026, 1, 1),
            DATE(2026, 1, 11),
            continuity_days=10,
        )
        self.assertEqual(result["days_since_last_run"], 10)
        self.assertEqual(result["status"], OPERATOR_CURRENT)

    def test_a_last_run_after_the_braze_is_an_inconsistent_record(self):
        with self.assertRaises(ValueError):
            operator_currency(
                DATE(2027, 1, 31), DATE(2026, 6, 1), DATE(2026, 5, 12)
            )

    def test_a_zero_continuity_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            operator_currency(
                DATE(2027, 1, 31),
                DATE(2026, 4, 2),
                DATE(2026, 5, 12),
                continuity_days=0,
            )

    def test_a_datetime_instead_of_a_date_is_rejected(self):
        with self.assertRaises(ValueError):
            operator_currency(
                datetime.datetime(2027, 1, 31), DATE(2026, 4, 2), DATE(2026, 5, 12)
            )


class FurnaceDataTests(unittest.TestCase):
    def test_a_fully_traced_run_is_complete(self):
        result = furnace_data_gaps(GOOD_RUN)
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing_channels"], [])

    def test_a_missing_cooling_rate_is_reported_as_a_gap(self):
        run = copy.deepcopy(GOOD_RUN)
        run["channels_recorded"].remove(PROFILE_COOLING_RATE)
        result = furnace_data_gaps(run)
        self.assertIn(PROFILE_COOLING_RATE, result["missing_channels"])
        self.assertFalse(result["complete"])

    def test_a_run_identity_with_no_channels_is_a_switched_on_furnace(self):
        run = {"run_id": "FRN-2026-115", "channels_recorded": [], "load_thermocouples": 3}
        result = furnace_data_gaps(run)
        self.assertEqual(len(result["missing_channels"]), len(PROFILE_CHANNELS))

    def test_a_single_load_thermocouple_is_under_instrumented(self):
        run = copy.deepcopy(GOOD_RUN)
        run["load_thermocouples"] = MINIMUM_LOAD_THERMOCOUPLES - 1
        result = furnace_data_gaps(run)
        self.assertFalse(result["instrumented"])

    def test_the_minimum_number_of_load_thermocouples_is_accepted(self):
        run = copy.deepcopy(GOOD_RUN)
        run["load_thermocouples"] = MINIMUM_LOAD_THERMOCOUPLES
        self.assertTrue(furnace_data_gaps(run)["instrumented"])

    def test_a_run_with_no_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            furnace_data_gaps({"run_id": "", "channels_recorded": []})

    def test_a_negative_thermocouple_count_is_rejected(self):
        run = copy.deepcopy(GOOD_RUN)
        run["load_thermocouples"] = -2
        with self.assertRaises(ValueError):
            furnace_data_gaps(run)


class AssessmentTests(unittest.TestCase):
    def test_a_complete_record_closes(self):
        result = assess_brazement_record(_case())
        self.assertEqual(result["verdict"], VERDICT_COMPLETE)
        self.assertTrue(result["record_closes"])

    def test_a_lapsed_operator_holds_an_otherwise_complete_record(self):
        result = assess_brazement_record(
            _case(operator_last_process_run=DATE(2025, 8, 1))
        )
        self.assertEqual(result["verdict"], VERDICT_INCOMPLETE)
        self.assertEqual(result["missing_fields"], [])

    def test_a_furnace_process_with_no_run_data_is_a_finding(self):
        case = _case()
        case["furnace_run"] = None
        result = assess_brazement_record(case)
        self.assertFalse(result["record_closes"])

    def test_a_torch_braze_is_not_asked_for_furnace_data(self):
        result = assess_brazement_record(
            _case(
                process=PROCESS_TORCH,
                uses_flux=True,
                fields_present=required_record_fields(PROCESS_TORCH, True),
                furnace_run=None,
            )
        )
        self.assertTrue(result["record_closes"])
        self.assertIsNone(result["furnace_run"])

    def test_every_finding_is_reported_not_only_the_first(self):
        run = copy.deepcopy(GOOD_RUN)
        run["load_thermocouples"] = 0
        run["channels_recorded"] = []
        result = assess_brazement_record(
            _case(
                fields_present=[],
                operator_certificate_expiry=DATE(2026, 1, 1),
                furnace_run=run,
            )
        )
        self.assertGreaterEqual(len(result["findings"]), 4)

    def test_a_record_without_a_brazement_id_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_brazement_record(_case(brazement_id="   "))

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_brazement_record("it is in the traveller")

    def test_an_unknown_process_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_brazement_record(_case(process="soldering"))


if __name__ == "__main__":
    unittest.main()
