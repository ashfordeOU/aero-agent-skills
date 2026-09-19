"""Contract tests for the clause 5.7.1.3 synchronous command and control logic."""

import unittest

from e50_synchronous_command_and_control_logic import (
    NON_HARMONIC,
    OVERSUBSCRIBED,
    PHASE_ERROR_EXCEEDED,
    SCHEDULABLE,
    assess_synchronous_schedule,
    delivery_phase_error_s,
    is_harmonic,
    required_link_rate_bps,
    reserved_time_s,
    slot_duration_s,
    slots_in_worst_cycle,
    spare_time_s,
    synchronous_utilisation,
    validate_exchanges,
    validate_nonnegative,
    validate_positive,
)

CYCLE = 0.125
RATE = 1.0e6
OVERHEAD = 96.0
GUARD = 1.0e-5
NOMINAL = [
    {"name": "attitude-control", "bits": 1000.0, "period_s": 0.125},
    {"name": "thruster-command", "bits": 500.0, "period_s": 0.03125},
]


class ValidationTests(unittest.TestCase):
    def test_exchanges_none_rejected(self):
        with self.assertRaises(ValueError):
            validate_exchanges(None)

    def test_exchanges_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_exchanges({"name": "a", "bits": 1.0, "period_s": 1.0})

    def test_empty_exchange_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_exchanges([])

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            validate_exchanges(["attitude-control"])

    def test_missing_period_rejected(self):
        with self.assertRaises(ValueError):
            validate_exchanges([{"name": "a", "bits": 100.0}])

    def test_duplicate_exchange_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_exchanges([
                {"name": "a", "bits": 100.0, "period_s": 0.1},
                {"name": "a", "bits": 200.0, "period_s": 0.1},
            ])

    def test_blank_exchange_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_exchanges([{"name": "  ", "bits": 100.0, "period_s": 0.1}])

    def test_zero_bits_rejected(self):
        with self.assertRaises(ValueError):
            validate_exchanges([{"name": "a", "bits": 0.0, "period_s": 0.1}])

    def test_zero_period_rejected(self):
        with self.assertRaises(ValueError):
            validate_exchanges([{"name": "a", "bits": 100.0, "period_s": 0.0}])

    def test_zero_cycle_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "cycle_s")

    def test_negative_guard_rejected(self):
        with self.assertRaises(ValueError):
            validate_nonnegative(-1.0e-9, "guard_s")


class SlotTests(unittest.TestCase):
    def test_slot_carries_overhead_and_guard(self):
        self.assertAlmostEqual(
            slot_duration_s(1000.0, OVERHEAD, RATE, GUARD), 0.001106, places=12
        )

    def test_bare_slot_is_payload_over_rate(self):
        self.assertAlmostEqual(slot_duration_s(1000.0, 0.0, RATE), 0.001, places=12)

    def test_slot_rejects_a_dead_link(self):
        with self.assertRaises(ValueError):
            slot_duration_s(1000.0, OVERHEAD, 0.0, GUARD)


class HarmonicTests(unittest.TestCase):
    def test_period_equal_to_the_cycle_is_harmonic(self):
        self.assertTrue(is_harmonic(CYCLE, CYCLE))

    def test_cycle_a_whole_multiple_of_the_period_is_harmonic(self):
        self.assertTrue(is_harmonic(0.03125, CYCLE))

    def test_period_a_whole_multiple_of_the_cycle_is_harmonic(self):
        self.assertTrue(is_harmonic(0.5, CYCLE))

    def test_period_that_fits_neither_way_is_not_harmonic(self):
        self.assertFalse(is_harmonic(0.03, CYCLE))


class SlotCountTests(unittest.TestCase):
    def test_four_activations_in_a_cycle(self):
        self.assertEqual(slots_in_worst_cycle(0.03125, CYCLE), 4)

    def test_one_activation_at_the_cycle_rate(self):
        self.assertEqual(slots_in_worst_cycle(CYCLE, CYCLE), 1)

    def test_slower_exchange_still_needs_a_whole_slot(self):
        self.assertEqual(slots_in_worst_cycle(0.5, CYCLE), 1)


class ReservationTests(unittest.TestCase):
    def test_reserved_time_is_the_sum_of_the_slots(self):
        self.assertAlmostEqual(
            reserved_time_s(NOMINAL, CYCLE, RATE, OVERHEAD, GUARD), 0.00353, places=12
        )

    def test_utilisation_is_the_reserved_fraction(self):
        self.assertAlmostEqual(synchronous_utilisation(0.00353, CYCLE), 0.02824, places=12)

    def test_spare_is_what_the_cycle_has_left(self):
        self.assertAlmostEqual(spare_time_s(0.00353, CYCLE), 0.12147, places=12)

    def test_spare_never_goes_negative(self):
        self.assertAlmostEqual(spare_time_s(0.2, CYCLE), 0.0, places=12)


class PhaseErrorTests(unittest.TestCase):
    def test_phase_error_adds_its_three_terms(self):
        self.assertAlmostEqual(
            delivery_phase_error_s(1.0e-5, 2.0e-5, 3.0e-5), 6.0e-5, places=12
        )

    def test_phase_error_rejects_a_negative_reference_error(self):
        with self.assertRaises(ValueError):
            delivery_phase_error_s(1.0e-5, 0.0, -1.0e-6)


class RequiredRateTests(unittest.TestCase):
    def test_single_exchange_needs_its_bits_in_the_cycle(self):
        single = [{"name": "housekeeping-poll", "bits": 1000.0, "period_s": 0.1}]
        self.assertAlmostEqual(required_link_rate_bps(single, 0.1), 10000.0, places=9)

    def test_required_rate_actually_makes_the_schedule_fit(self):
        heavy = [{"name": "payload-command", "bits": 200000.0, "period_s": CYCLE}]
        needed = required_link_rate_bps(heavy, CYCLE, OVERHEAD, GUARD)
        fixed = assess_synchronous_schedule(heavy, CYCLE, needed, OVERHEAD, GUARD)
        self.assertTrue(fixed["fits"])

    def test_guard_time_filling_the_cycle_admits_no_rate(self):
        tight = [{"name": "fine-pointing", "bits": 100.0, "period_s": 0.001}]
        self.assertIsNone(required_link_rate_bps(tight, 0.001, 0.0, 0.002))


class AssessTests(unittest.TestCase):
    def test_nominal_cycle_is_schedulable(self):
        result = assess_synchronous_schedule(NOMINAL, CYCLE, RATE, OVERHEAD, GUARD)
        self.assertEqual(result["verdict"], SCHEDULABLE)
        self.assertTrue(result["fits"])

    def test_nominal_cycle_reports_its_spare_time(self):
        result = assess_synchronous_schedule(NOMINAL, CYCLE, RATE, OVERHEAD, GUARD)
        self.assertAlmostEqual(result["spare_s"], 0.12147, places=12)

    def test_schedule_exactly_filling_the_cycle_is_accepted(self):
        exact = [{"name": "bulk-control-frame", "bits": 125000.0, "period_s": CYCLE}]
        result = assess_synchronous_schedule(exact, CYCLE, RATE)
        self.assertAlmostEqual(result["reserved_s"], result["cycle_s"], places=12)
        self.assertEqual(result["verdict"], SCHEDULABLE)

    def test_oversubscribed_cycle_is_reported(self):
        heavy = [{"name": "payload-command", "bits": 200000.0, "period_s": CYCLE}]
        result = assess_synchronous_schedule(heavy, CYCLE, RATE)
        self.assertEqual(result["verdict"], OVERSUBSCRIBED)
        self.assertFalse(result["fits"])

    def test_oversubscribed_cycle_names_both_ways_out(self):
        heavy = [{"name": "payload-command", "bits": 200000.0, "period_s": CYCLE}]
        result = assess_synchronous_schedule(heavy, CYCLE, RATE)
        self.assertTrue(any("or a cycle of at least" in f for f in result["findings"]))

    def test_non_harmonic_period_outranks_oversubscription(self):
        odd = [{"name": "payload-command", "bits": 200000.0, "period_s": 0.03}]
        result = assess_synchronous_schedule(odd, CYCLE, RATE)
        self.assertEqual(result["verdict"], NON_HARMONIC)

    def test_phase_error_exactly_at_budget_passes(self):
        result = assess_synchronous_schedule(
            NOMINAL, CYCLE, RATE, OVERHEAD, GUARD, 2.0e-5, 3.0e-5, 6.0e-5
        )
        self.assertEqual(result["verdict"], SCHEDULABLE)

    def test_phase_error_beyond_budget_is_reported(self):
        result = assess_synchronous_schedule(
            NOMINAL, CYCLE, RATE, OVERHEAD, GUARD, 2.0e-5, 3.0e-5, 5.0e-5
        )
        self.assertEqual(result["verdict"], PHASE_ERROR_EXCEEDED)
        self.assertAlmostEqual(result["phase_error_s"], 6.0e-5, places=12)

    def test_breakdown_carries_the_slot_count_per_exchange(self):
        result = assess_synchronous_schedule(NOMINAL, CYCLE, RATE, OVERHEAD, GUARD)
        self.assertEqual([e["slots_per_cycle"] for e in result["exchanges"]], [1, 4])

    def test_bad_link_rate_rejected(self):
        with self.assertRaises(ValueError):
            assess_synchronous_schedule(NOMINAL, CYCLE, 0.0, OVERHEAD, GUARD)


if __name__ == "__main__":
    unittest.main()
