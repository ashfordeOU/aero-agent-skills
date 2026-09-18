"""Contract test for the short-contact-periods leaf (stdlib unittest)."""

import unittest

from e50_short_contact_periods_logic import (
    SETUP_DOMINANCE_FRACTION,
    VOLUME_TOLERANCE_BITS,
    assess_contact_schedule,
    contact_findings,
    deliverable_volume_bits,
    effective_throughput_bps,
    required_channel_rate_bps,
    setup_overhead_fraction,
    usable_transfer_time_s,
    validate_contact,
)


def contact(cid="P-1", start=0.0, duration=400.0, setup=40.0, **kw):
    record = {
        "id": cid,
        "start_time_s": start,
        "duration_s": duration,
        "setup_time_s": setup,
        "channel_rate_bps": 1.0e6,
        "coding_rate": 0.5,
        "framing_efficiency": 0.8,
    }
    record.update(kw)
    return record


class TestValidateContact(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_contact(
            {"id": "P-1", "duration_s": 100.0, "channel_rate_bps": 1000.0}
        )
        self.assertEqual(norm["start_time_s"], 0.0)
        self.assertEqual(norm["setup_time_s"], 0.0)
        self.assertEqual(norm["coding_rate"], 1.0)
        self.assertEqual(norm["framing_efficiency"], 1.0)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_contact(["P-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_contact(contact(""))

    def test_zero_duration_raises(self):
        with self.assertRaises(ValueError):
            validate_contact(contact(duration=0.0))

    def test_negative_setup_raises(self):
        with self.assertRaises(ValueError):
            validate_contact(contact(setup=-1.0))

    def test_non_positive_rate_raises(self):
        with self.assertRaises(ValueError):
            validate_contact(contact(channel_rate_bps=0.0))

    def test_coding_rate_above_one_raises(self):
        with self.assertRaises(ValueError):
            validate_contact(contact(coding_rate=1.5))

    def test_zero_framing_efficiency_raises(self):
        with self.assertRaises(ValueError):
            validate_contact(contact(framing_efficiency=0.0))

    def test_boolean_duration_raises(self):
        with self.assertRaises(ValueError):
            validate_contact(contact(duration=True))


class TestUsableTime(unittest.TestCase):
    def test_setup_is_subtracted_from_the_pass(self):
        self.assertAlmostEqual(usable_transfer_time_s(400.0, 40.0), 360.0, places=9)

    def test_setup_equal_to_the_pass_leaves_nothing(self):
        self.assertAlmostEqual(usable_transfer_time_s(60.0, 60.0), 0.0, places=9)

    def test_setup_longer_than_the_pass_is_floored_at_zero(self):
        self.assertAlmostEqual(usable_transfer_time_s(30.0, 60.0), 0.0, places=9)

    def test_non_positive_duration_raises(self):
        with self.assertRaises(ValueError):
            usable_transfer_time_s(0.0, 10.0)

    def test_overhead_fraction_is_reported(self):
        self.assertAlmostEqual(setup_overhead_fraction(contact()), 0.1, places=9)

    def test_overhead_fraction_is_capped_at_one(self):
        self.assertAlmostEqual(
            setup_overhead_fraction(contact(duration=30.0, setup=60.0)), 1.0, places=9
        )


class TestThroughput(unittest.TestCase):
    def test_coding_and_framing_both_take_their_share(self):
        self.assertAlmostEqual(
            effective_throughput_bps(1.0e6, 0.5, 0.8), 400000.0, places=6
        )

    def test_unity_coding_and_framing_pass_the_rate_through(self):
        self.assertAlmostEqual(effective_throughput_bps(2048.0, 1.0, 1.0), 2048.0, places=9)

    def test_negative_coding_rate_raises(self):
        with self.assertRaises(ValueError):
            effective_throughput_bps(1.0e6, -0.5, 0.8)

    def test_deliverable_volume_uses_the_usable_time(self):
        self.assertAlmostEqual(
            deliverable_volume_bits(contact()), 360.0 * 400000.0, places=3
        )

    def test_a_pass_eaten_by_setup_delivers_nothing(self):
        self.assertAlmostEqual(
            deliverable_volume_bits(contact(duration=30.0, setup=60.0)), 0.0, places=9
        )


class TestRequiredRate(unittest.TestCase):
    def test_required_rate_inverts_the_deliverable_volume(self):
        pass_record = contact()
        volume = deliverable_volume_bits(pass_record)
        self.assertAlmostEqual(
            required_channel_rate_bps(volume, pass_record), 1.0e6, places=3
        )

    def test_required_rate_refuses_a_pass_with_no_usable_time(self):
        with self.assertRaises(ValueError):
            required_channel_rate_bps(1.0e6, contact(duration=30.0, setup=60.0))

    def test_negative_volume_raises(self):
        with self.assertRaises(ValueError):
            required_channel_rate_bps(-1.0, contact())


class TestContactFindings(unittest.TestCase):
    def test_healthy_pass_is_clean(self):
        self.assertEqual(contact_findings(contact()), [])

    def test_pass_shorter_than_its_setup_is_a_finding(self):
        self.assertIn(
            "contact-fully-consumed-by-link-setup",
            contact_findings(contact(duration=30.0, setup=60.0)),
        )

    def test_setup_dominated_pass_is_a_finding(self):
        dominated = contact(duration=100.0, setup=60.0)
        self.assertGreater(setup_overhead_fraction(dominated), SETUP_DOMINANCE_FRACTION)
        self.assertIn(
            "link-setup-consumes-most-of-a-short-contact", contact_findings(dominated)
        )

    def test_setup_at_exactly_half_the_pass_is_not_a_finding(self):
        boundary = contact(duration=100.0, setup=50.0)
        self.assertAlmostEqual(
            setup_overhead_fraction(boundary), SETUP_DOMINANCE_FRACTION, places=9
        )
        self.assertEqual(contact_findings(boundary), [])


class TestAssessContactSchedule(unittest.TestCase):
    def test_a_draining_plan_is_compliant(self):
        report = assess_contact_schedule(
            [contact("P-1", start=0.0), contact("P-2", start=5400.0)],
            generation_rate_bps=1000.0,
        )
        self.assertTrue(report["compliant"])
        self.assertTrue(report["store_cleared_at_least_once"])
        self.assertAlmostEqual(report["final_backlog_bits"], 0.0, places=6)

    def test_a_growing_backlog_is_a_finding(self):
        report = assess_contact_schedule(
            [contact("P-1", start=0.0, duration=100.0, setup=40.0)],
            generation_rate_bps=1.0e6,
            initial_backlog_bits=0.0,
        )
        self.assertIn("backlog-grows-across-the-contact-plan", report["findings"])
        self.assertFalse(report["backlog_stable"])

    def test_storage_overflow_counts_the_lost_volume(self):
        report = assess_contact_schedule(
            [contact("P-1", start=10000.0, duration=100.0, setup=40.0)],
            generation_rate_bps=1.0e6,
            storage_capacity_bits=1.0e6,
        )
        self.assertIn("onboard-storage-overflowed-before-a-contact", report["findings"])
        self.assertGreater(report["lost_bits"], 0.0)

    def test_contacts_are_walked_in_time_order(self):
        report = assess_contact_schedule(
            [contact("P-2", start=5400.0), contact("P-1", start=0.0)],
            generation_rate_bps=1000.0,
        )
        self.assertEqual([c["id"] for c in report["contacts"]], ["P-1", "P-2"])

    def test_peak_backlog_is_never_below_the_final_backlog(self):
        report = assess_contact_schedule(
            [contact("P-1", start=0.0, duration=100.0, setup=40.0)],
            generation_rate_bps=1.0e6,
        )
        self.assertGreaterEqual(report["peak_backlog_bits"], report["final_backlog_bits"])

    def test_tolerance_absorbs_a_sub_microbit_residue(self):
        report = assess_contact_schedule(
            [contact("P-1", start=0.0)],
            generation_rate_bps=0.0,
            initial_backlog_bits=VOLUME_TOLERANCE_BITS / 2.0,
        )
        self.assertTrue(report["store_cleared_at_least_once"])

    def test_overlapping_contacts_raise(self):
        with self.assertRaises(ValueError):
            assess_contact_schedule(
                [contact("P-1", start=0.0, duration=400.0), contact("P-2", start=100.0)],
                generation_rate_bps=1000.0,
            )

    def test_duplicate_contact_id_raises(self):
        with self.assertRaises(ValueError):
            assess_contact_schedule(
                [contact("P-1", start=0.0), contact("P-1", start=5400.0)],
                generation_rate_bps=1000.0,
            )

    def test_empty_schedule_raises(self):
        with self.assertRaises(ValueError):
            assess_contact_schedule([], generation_rate_bps=1000.0)

    def test_non_list_input_raises(self):
        with self.assertRaises(ValueError):
            assess_contact_schedule(contact(), generation_rate_bps=1000.0)

    def test_negative_generation_rate_raises(self):
        with self.assertRaises(ValueError):
            assess_contact_schedule([contact()], generation_rate_bps=-1.0)

    def test_initial_backlog_above_capacity_raises(self):
        with self.assertRaises(ValueError):
            assess_contact_schedule(
                [contact()],
                generation_rate_bps=0.0,
                initial_backlog_bits=2.0e6,
                storage_capacity_bits=1.0e6,
            )


if __name__ == "__main__":
    unittest.main()
