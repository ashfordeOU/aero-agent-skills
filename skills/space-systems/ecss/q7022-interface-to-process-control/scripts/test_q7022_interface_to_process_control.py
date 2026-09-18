"""Contract tests for the shelf-life to process-control interface gate."""

import datetime
import unittest

from q7022_interface_to_process_control_logic import (
    RECOGNISED_PROCESS_STANDARDS,
    RELEASABLE_STATUSES,
    evaluate_material_release,
    operation_window,
    parse_date,
    parse_timestamp,
    pot_life_reason_codes,
    process_reason_codes,
    shelf_life_deadline,
    shelf_life_reason_codes,
    status_reason_codes,
)


def base_operation(**overrides):
    """A four-hour bonding operation cited against a recognised process standard."""
    operation = {
        "process_id": "BOND-114",
        "process_standard": "ecss-q-st-70-31c",
        "start": "2026-05-04T08:00",
        "duration_hours": 4.0,
    }
    operation.update(overrides)
    return operation


def base_lot(**overrides):
    """A released adhesive lot in date until the end of 2026-07-01."""
    lot = {
        "lot_id": "SL-2026-0031",
        "expiry_date": "2026-07-01",
        "status": "released",
        "approved_processes": ["BOND-114", "BOND-115"],
        "open_deviation": False,
    }
    lot.update(overrides)
    return lot


class TimestampTests(unittest.TestCase):
    def test_iso_timestamp_parsed(self):
        self.assertEqual(
            parse_timestamp("2026-05-04T08:00"), datetime.datetime(2026, 5, 4, 8, 0)
        )

    def test_space_separator_accepted(self):
        self.assertEqual(
            parse_timestamp("2026-05-04 08:30"), datetime.datetime(2026, 5, 4, 8, 30)
        )

    def test_seconds_accepted(self):
        self.assertEqual(
            parse_timestamp("2026-05-04T08:30:15"), datetime.datetime(2026, 5, 4, 8, 30, 15)
        )

    def test_date_without_a_time_rejected(self):
        with self.assertRaises(ValueError):
            parse_timestamp("2026-05-04")

    def test_malformed_time_rejected(self):
        with self.assertRaises(ValueError):
            parse_timestamp("2026-05-04T08")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_timestamp(20260504)

    def test_plain_date_parser_still_available(self):
        self.assertEqual(parse_date("2026-07-01"), datetime.date(2026, 7, 1))


class WindowTests(unittest.TestCase):
    def test_window_end_follows_the_duration(self):
        begin, end = operation_window("2026-05-04T08:00", 4.0)
        self.assertEqual(end - begin, datetime.timedelta(hours=4))

    def test_fractional_hours_accepted(self):
        _, end = operation_window("2026-05-04T08:00", 1.5)
        self.assertEqual(end, datetime.datetime(2026, 5, 4, 9, 30))

    def test_zero_duration_rejected(self):
        with self.assertRaises(ValueError):
            operation_window("2026-05-04T08:00", 0.0)

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            operation_window("2026-05-04T08:00", -2.0)

    def test_deadline_runs_to_the_end_of_the_expiry_day(self):
        self.assertEqual(shelf_life_deadline("2026-07-01"), datetime.datetime(2026, 7, 2, 0, 0))


class ShelfLifeGateTests(unittest.TestCase):
    def test_operation_well_inside_the_shelf_life_is_clean(self):
        window = operation_window("2026-05-04T08:00", 4.0)
        self.assertEqual(shelf_life_reason_codes(base_lot(), window), [])

    def test_operation_starting_after_expiry_is_blocked(self):
        window = operation_window("2026-08-04T08:00", 4.0)
        self.assertEqual(shelf_life_reason_codes(base_lot(), window), ["expired-before-use"])

    def test_operation_crossing_the_deadline_is_blocked(self):
        window = operation_window("2026-07-01T22:00", 4.0)
        self.assertEqual(
            shelf_life_reason_codes(base_lot(), window), ["expires-during-operation"]
        )

    def test_operation_ending_exactly_on_the_deadline_is_clean(self):
        window = operation_window("2026-07-01T20:00", 4.0)
        self.assertEqual(window[1], shelf_life_deadline("2026-07-01"))
        self.assertEqual(shelf_life_reason_codes(base_lot(), window), [])

    def test_lot_without_an_expiry_date_rejected(self):
        lot = base_lot()
        del lot["expiry_date"]
        with self.assertRaises(ValueError):
            shelf_life_reason_codes(lot, operation_window("2026-05-04T08:00", 4.0))


class StatusGateTests(unittest.TestCase):
    def test_released_lot_is_clean(self):
        self.assertEqual(status_reason_codes(base_lot()), [])

    def test_every_releasable_status_passes(self):
        for status in RELEASABLE_STATUSES:
            self.assertEqual(status_reason_codes(base_lot(status=status)), [])

    def test_quarantined_lot_is_blocked(self):
        self.assertIn("status-not-released", status_reason_codes(base_lot(status="quarantine")))

    def test_open_deviation_blocks_a_released_lot(self):
        self.assertIn("open-deviation", status_reason_codes(base_lot(open_deviation=True)))

    def test_blank_status_rejected(self):
        with self.assertRaises(ValueError):
            status_reason_codes(base_lot(status="  "))


class ProcessGateTests(unittest.TestCase):
    def test_approved_process_on_a_recognised_standard_is_clean(self):
        self.assertEqual(process_reason_codes(base_operation(), base_lot()), [])

    def test_every_recognised_standard_passes(self):
        for standard in RECOGNISED_PROCESS_STANDARDS:
            self.assertEqual(
                process_reason_codes(base_operation(process_standard=standard), base_lot()), []
            )

    def test_unapproved_process_is_blocked(self):
        codes = process_reason_codes(base_operation(process_id="WELD-9"), base_lot())
        self.assertIn("process-not-approved", codes)

    def test_process_match_ignores_case(self):
        codes = process_reason_codes(base_operation(process_id="bond-114"), base_lot())
        self.assertEqual(codes, [])

    def test_unrecognised_standard_is_blocked(self):
        codes = process_reason_codes(base_operation(process_standard="in-house-wi-7"), base_lot())
        self.assertIn("unrecognised-process-standard", codes)

    def test_lot_without_an_approved_process_list_rejected(self):
        lot = base_lot()
        del lot["approved_processes"]
        with self.assertRaises(ValueError):
            process_reason_codes(base_operation(), lot)

    def test_blank_process_id_rejected(self):
        with self.assertRaises(ValueError):
            process_reason_codes(base_operation(process_id=""), base_lot())


class PotLifeGateTests(unittest.TestCase):
    def test_unmixed_lot_has_no_pot_life_codes(self):
        window = operation_window("2026-05-04T08:00", 4.0)
        self.assertEqual(pot_life_reason_codes(base_operation(), base_lot(), window), [])

    def test_operation_inside_the_pot_life_is_clean(self):
        window = operation_window("2026-05-04T08:00", 1.0)
        lot = base_lot(mixed_at="2026-05-04T07:50", pot_life_min=120.0)
        self.assertEqual(pot_life_reason_codes(base_operation(), lot, window), [])

    def test_operation_past_the_pot_life_is_blocked(self):
        window = operation_window("2026-05-04T08:00", 4.0)
        lot = base_lot(mixed_at="2026-05-04T07:50", pot_life_min=60.0)
        self.assertEqual(
            pot_life_reason_codes(base_operation(), lot, window), ["pot-life-exceeded"]
        )

    def test_pot_life_already_spent_at_the_start_is_blocked(self):
        window = operation_window("2026-05-04T08:00", 1.0)
        lot = base_lot(mixed_at="2026-05-04T05:00", pot_life_min=60.0)
        self.assertEqual(
            pot_life_reason_codes(base_operation(), lot, window), ["pot-life-already-spent"]
        )

    def test_operation_ending_exactly_on_the_pot_life_is_clean(self):
        window = operation_window("2026-05-04T08:00", 1.0)
        lot = base_lot(mixed_at="2026-05-04T08:00", pot_life_min=60.0)
        self.assertEqual(pot_life_reason_codes(base_operation(), lot, window), [])

    def test_pot_life_without_a_mix_time_rejected(self):
        window = operation_window("2026-05-04T08:00", 1.0)
        with self.assertRaises(ValueError):
            pot_life_reason_codes(base_operation(), base_lot(pot_life_min=60.0), window)

    def test_negative_pot_life_rejected(self):
        window = operation_window("2026-05-04T08:00", 1.0)
        lot = base_lot(mixed_at="2026-05-04T07:50", pot_life_min=-60.0)
        with self.assertRaises(ValueError):
            pot_life_reason_codes(base_operation(), lot, window)


class ReleaseDecisionTests(unittest.TestCase):
    def test_compliant_issue_is_released(self):
        result = evaluate_material_release(base_operation(), base_lot())
        self.assertEqual(result["decision"], "release")
        self.assertEqual(result["reason_codes"], [])

    def test_released_record_carries_the_window(self):
        result = evaluate_material_release(base_operation(), base_lot())
        self.assertEqual(result["window_start"], "2026-05-04T08:00:00")
        self.assertEqual(result["window_end"], "2026-05-04T12:00:00")

    def test_expired_lot_is_blocked_with_a_reason_code(self):
        result = evaluate_material_release(
            base_operation(start="2026-09-04T08:00"), base_lot()
        )
        self.assertEqual(result["decision"], "block")
        self.assertIn("expired-before-use", result["reason_codes"])

    def test_quarantined_lot_is_blocked(self):
        result = evaluate_material_release(base_operation(), base_lot(status="quarantine"))
        self.assertEqual(result["decision"], "block")

    def test_several_failures_all_appear(self):
        result = evaluate_material_release(
            base_operation(start="2026-09-04T08:00", process_id="WELD-9"),
            base_lot(status="quarantine", open_deviation=True),
        )
        self.assertEqual(
            sorted(result["reason_codes"]),
            sorted(
                [
                    "expired-before-use",
                    "status-not-released",
                    "open-deviation",
                    "process-not-approved",
                ]
            ),
        )

    def test_every_reason_code_has_a_finding(self):
        result = evaluate_material_release(
            base_operation(start="2026-09-04T08:00", process_standard="in-house-wi-7"),
            base_lot(status="quarantine", open_deviation=True),
        )
        self.assertEqual(len(result["findings"]), len(result["reason_codes"]))
        self.assertTrue(all(isinstance(f, str) and f for f in result["findings"]))

    def test_mixed_lot_past_its_pot_life_is_blocked(self):
        result = evaluate_material_release(
            base_operation(duration_hours=4.0),
            base_lot(mixed_at="2026-05-04T07:50", pot_life_min=60.0),
        )
        self.assertIn("pot-life-exceeded", result["reason_codes"])

    def test_non_mapping_operation_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_material_release("BOND-114", base_lot())

    def test_non_mapping_lot_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_material_release(base_operation(), "SL-2026-0031")

    def test_missing_duration_rejected(self):
        operation = base_operation()
        del operation["duration_hours"]
        with self.assertRaises(ValueError):
            evaluate_material_release(operation, base_lot())


if __name__ == "__main__":
    unittest.main()
