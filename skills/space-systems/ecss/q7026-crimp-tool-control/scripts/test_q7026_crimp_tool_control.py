"""Contract test for the crimp tool control leaf (stdlib unittest)."""

import datetime
import unittest

from q7026_crimp_tool_control_logic import (
    CALENDAR,
    CYCLES,
    NOT_CERTIFIED,
    OVERDUE,
    RECALL,
    RECALL_THRESHOLD,
    RELEASED,
    WITHDRAWN,
    assess_tool,
    assess_tool_pool,
    calibration_status,
    certification_covers,
    parse_date,
    validate_job,
    validate_tool,
)


def tool(**kw):
    t = {
        "tool_id": "CT-0114",
        "die_part_number": "DIE-M22520-1-02",
        "positioner_part_number": "POS-K13-1",
        "certified_contacts": ["M39029-58-360", "M39029-56-348"],
        "certified_csa_min_mm2": 0.20,
        "certified_csa_max_mm2": 0.60,
        "last_calibration_date": "2026-03-01",
        "calibration_interval_days": 180,
        "calibration_interval_cycles": 10000,
        "cycles_since_calibration": 1200,
        "withdrawn": False,
    }
    t.update(kw)
    return t


def job(**kw):
    j = {
        "contact_part_number": "M39029-58-360",
        "conductor_csa_mm2": 0.38,
        "required_positioner": "POS-K13-1",
    }
    j.update(kw)
    return j


AS_OF = "2026-04-01"


class TestValidation(unittest.TestCase):
    def test_a_non_mapping_tool_raises(self):
        with self.assertRaises(ValueError):
            validate_tool("CT-0114")

    def test_an_empty_certification_list_raises(self):
        with self.assertRaises(ValueError):
            validate_tool(tool(certified_contacts=[]))

    def test_an_inverted_certified_range_raises(self):
        with self.assertRaises(ValueError):
            validate_tool(
                tool(certified_csa_min_mm2=0.6, certified_csa_max_mm2=0.2)
            )

    def test_a_zero_calibration_interval_raises(self):
        with self.assertRaises(ValueError):
            validate_tool(tool(calibration_interval_days=0))

    def test_a_negative_cycle_count_raises(self):
        with self.assertRaises(ValueError):
            validate_tool(tool(cycles_since_calibration=-5))

    def test_a_non_integer_cycle_count_raises(self):
        with self.assertRaises(ValueError):
            validate_tool(tool(cycles_since_calibration=1200.0))

    def test_a_malformed_calibration_date_raises(self):
        with self.assertRaises(ValueError):
            validate_tool(tool(last_calibration_date="01/03/2026"))

    def test_a_date_object_passes_through(self):
        day = datetime.date(2026, 3, 1)
        self.assertEqual(parse_date("last_calibration_date", day), day)

    def test_a_zero_conductor_in_the_job_raises(self):
        with self.assertRaises(ValueError):
            validate_job(job(conductor_csa_mm2=0.0))

    def test_part_numbers_fold_case(self):
        self.assertEqual(
            validate_job(job(contact_part_number="m39029-58-360"))[
                "contact_part_number"
            ],
            "M39029-58-360",
        )


class TestCertification(unittest.TestCase):
    def test_a_matching_set_is_certified(self):
        self.assertTrue(certification_covers(tool(), job())["certified"])

    def test_an_uncertified_contact_is_refused(self):
        result = certification_covers(tool(), job(contact_part_number="M39029-99-000"))
        self.assertIn("contact-not-in-the-tool-certification", result["reasons"])

    def test_a_swapped_positioner_is_refused(self):
        result = certification_covers(tool(), job(required_positioner="POS-K13-9"))
        self.assertIn("positioner-does-not-match-the-job", result["reasons"])

    def test_a_conductor_below_the_range_is_refused(self):
        result = certification_covers(tool(), job(conductor_csa_mm2=0.10))
        self.assertIn("conductor-below-the-certified-range", result["reasons"])

    def test_a_conductor_above_the_range_is_refused(self):
        result = certification_covers(tool(), job(conductor_csa_mm2=1.50))
        self.assertIn("conductor-above-the-certified-range", result["reasons"])

    def test_a_conductor_exactly_on_the_low_bound_is_certified(self):
        self.assertTrue(
            certification_covers(tool(), job(conductor_csa_mm2=0.20))["certified"]
        )

    def test_a_conductor_exactly_on_the_high_bound_is_certified(self):
        self.assertTrue(
            certification_covers(tool(), job(conductor_csa_mm2=0.60))["certified"]
        )

    def test_several_faults_are_reported_together(self):
        result = certification_covers(
            tool(),
            job(
                contact_part_number="M39029-99-000",
                required_positioner="POS-K13-9",
                conductor_csa_mm2=1.50,
            ),
        )
        self.assertEqual(len(result["reasons"]), 3)


class TestCalibration(unittest.TestCase):
    def test_a_fresh_tool_is_released(self):
        self.assertEqual(calibration_status(tool(), AS_OF)["status"], RELEASED)

    def test_elapsed_days_are_counted_from_the_calibration_date(self):
        self.assertEqual(calibration_status(tool(), AS_OF)["elapsed_days"], 31)

    def test_the_calendar_governs_a_lightly_used_tool(self):
        self.assertEqual(
            calibration_status(tool(), AS_OF)["governing_allowance"], CALENDAR
        )

    def test_cycles_govern_a_heavily_used_tool(self):
        heavy = tool(cycles_since_calibration=9000)
        self.assertEqual(
            calibration_status(heavy, AS_OF)["governing_allowance"], CYCLES
        )

    def test_a_heavily_used_tool_in_date_is_still_booked_in(self):
        heavy = tool(cycles_since_calibration=9500)
        status = calibration_status(heavy, AS_OF)
        self.assertEqual(status["status"], RECALL)

    def test_the_allowance_exactly_consumed_is_a_recall_not_an_overdue(self):
        spent = tool(cycles_since_calibration=10000)
        status = calibration_status(spent, AS_OF)
        self.assertAlmostEqual(status["consumed_fraction"], 1.0, places=9)
        self.assertEqual(status["status"], RECALL)

    def test_exactly_at_the_recall_threshold_the_tool_is_booked_in(self):
        spent = tool(cycles_since_calibration=9000)
        status = calibration_status(spent, AS_OF)
        self.assertAlmostEqual(
            status["consumed_fraction"], RECALL_THRESHOLD, places=9
        )
        self.assertEqual(status["status"], RECALL)

    def test_past_the_allowance_the_tool_is_overdue(self):
        spent = tool(cycles_since_calibration=12000)
        self.assertEqual(calibration_status(spent, AS_OF)["status"], OVERDUE)

    def test_an_unused_tool_still_runs_out_of_calendar(self):
        old = tool(last_calibration_date="2025-01-01", cycles_since_calibration=0)
        self.assertEqual(calibration_status(old, AS_OF)["status"], OVERDUE)

    def test_a_date_before_the_calibration_raises(self):
        with self.assertRaises(ValueError):
            calibration_status(tool(), "2026-01-01")


class TestDisposition(unittest.TestCase):
    def test_a_good_tool_for_a_good_job_is_released(self):
        self.assertEqual(assess_tool(tool(), job(), AS_OF)["disposition"], RELEASED)

    def test_a_withdrawn_tool_is_out_whatever_the_arithmetic(self):
        result = assess_tool(tool(withdrawn=True), job(), AS_OF)
        self.assertEqual(result["disposition"], WITHDRAWN)
        self.assertFalse(result["usable"])

    def test_an_uncertified_set_outranks_a_live_calibration(self):
        result = assess_tool(tool(), job(required_positioner="POS-K13-9"), AS_OF)
        self.assertEqual(result["disposition"], NOT_CERTIFIED)
        self.assertFalse(result["usable"])

    def test_a_booked_in_tool_is_still_usable(self):
        result = assess_tool(tool(cycles_since_calibration=9500), job(), AS_OF)
        self.assertEqual(result["disposition"], RECALL)
        self.assertTrue(result["usable"])

    def test_an_overdue_tool_is_not_usable(self):
        result = assess_tool(tool(cycles_since_calibration=12000), job(), AS_OF)
        self.assertEqual(result["disposition"], OVERDUE)
        self.assertFalse(result["usable"])


class TestPool(unittest.TestCase):
    def test_a_pool_with_one_good_tool_can_proceed(self):
        report = assess_tool_pool(
            [tool(), tool(tool_id="CT-0115", cycles_since_calibration=12000)],
            job(),
            AS_OF,
        )
        self.assertTrue(report["job_can_proceed"])
        self.assertEqual(report["released"], ["CT-0114"])
        self.assertEqual(report["blocked"], ["CT-0115"])

    def test_a_pool_of_overdue_tools_cannot_proceed(self):
        report = assess_tool_pool(
            [tool(cycles_since_calibration=12000)], job(), AS_OF
        )
        self.assertFalse(report["job_can_proceed"])

    def test_a_booked_in_tool_shows_in_both_usable_and_to_book(self):
        report = assess_tool_pool(
            [tool(cycles_since_calibration=9500)], job(), AS_OF
        )
        self.assertEqual(report["to_book"], ["CT-0114"])
        self.assertEqual(report["usable"], ["CT-0114"])

    def test_an_empty_pool_raises(self):
        with self.assertRaises(ValueError):
            assess_tool_pool([], job(), AS_OF)

    def test_a_non_list_pool_raises(self):
        with self.assertRaises(ValueError):
            assess_tool_pool(tool(), job(), AS_OF)


if __name__ == "__main__":
    unittest.main()
