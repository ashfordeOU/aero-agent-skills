"""Contract tests for the clause 5.5.6 mixed-rate telemetry coexistence logic."""

import unittest

from e50_simultaneous_support_of_differing_source_rates_logic import (
    LATENCY_TOLERANCE_S,
    RATE_TOLERANCE_BPS,
    apportion_slots,
    assess_rate_coexistence,
    buffer_depth_bits,
    demand_spread,
    end_to_end_latency_s,
    fits_capacity,
    offered_load_bps,
    service_interval_s,
    source_demand_bps,
    validate_source,
    validate_source_set,
)


def _source(name, packet_bits, period_s, max_latency_s=60.0):
    return {
        "name": name,
        "packet_bits": packet_bits,
        "generation_period_s": period_s,
        "max_latency_s": max_latency_s,
    }


def _sources():
    return [
        _source("housekeeping", 2048, 1.0, 30.0),
        _source("attitude-history", 1024, 0.25, 10.0),
        _source("payload-science", 8192, 0.5, 20.0),
    ]


class ValidateSourceTests(unittest.TestCase):
    def test_returns_normalised_record(self):
        record = validate_source(_source("housekeeping", 2048, 1.0))
        self.assertEqual(record["packet_bits"], 2048)
        self.assertAlmostEqual(record["generation_period_s"], 1.0)

    def test_missing_key_rejected(self):
        source = _source("housekeeping", 2048, 1.0)
        del source["max_latency_s"]
        with self.assertRaises(ValueError):
            validate_source(source)

    def test_zero_packet_bits_rejected(self):
        with self.assertRaises(ValueError):
            validate_source(_source("housekeeping", 0, 1.0))

    def test_float_packet_bits_rejected(self):
        with self.assertRaises(ValueError):
            validate_source(_source("housekeeping", 2048.0, 1.0))

    def test_zero_period_rejected(self):
        with self.assertRaises(ValueError):
            validate_source(_source("housekeeping", 2048, 0.0))

    def test_negative_latency_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_source(_source("housekeeping", 2048, 1.0, -5.0))

    def test_non_mapping_source_rejected(self):
        with self.assertRaises(ValueError):
            validate_source(["housekeeping"])

    def test_empty_source_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_source_set([])

    def test_duplicate_source_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_source_set(_sources() + [_source("housekeeping", 512, 2.0)])


class DemandTests(unittest.TestCase):
    def test_demand_is_packet_bits_over_period(self):
        self.assertAlmostEqual(source_demand_bps(_source("x", 2048, 1.0)), 2048.0)

    def test_shorter_period_raises_demand(self):
        self.assertAlmostEqual(source_demand_bps(_source("x", 1024, 0.25)), 4096.0)

    def test_offered_load_sums_the_sources(self):
        # 2048 + 4096 + 16384 = 22528
        self.assertAlmostEqual(offered_load_bps(_sources()), 22528.0)

    def test_overhead_factor_scales_the_load(self):
        self.assertAlmostEqual(
            offered_load_bps(_sources(), 1.25), 22528.0 * 1.25, places=9
        )

    def test_overhead_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            offered_load_bps(_sources(), 0.8)

    def test_load_below_capacity_fits(self):
        self.assertTrue(fits_capacity(22528.0, 32768.0))

    def test_load_above_capacity_does_not_fit(self):
        self.assertFalse(fits_capacity(65536.0, 32768.0))

    def test_load_exactly_at_capacity_fits(self):
        self.assertTrue(fits_capacity(22528.0, 22528.0))

    def test_rate_tolerance_is_representation_sized(self):
        self.assertLess(RATE_TOLERANCE_BPS, 1e-6)

    def test_demand_spread_of_the_reference_set(self):
        # fastest 16384, slowest 2048
        self.assertAlmostEqual(demand_spread(_sources()), 8.0)

    def test_identical_sources_have_unit_spread(self):
        pair = [_source("a", 1024, 1.0), _source("b", 1024, 1.0)]
        self.assertAlmostEqual(demand_spread(pair), 1.0)


class ApportionmentTests(unittest.TestCase):
    def test_slots_sum_exactly_to_the_cycle(self):
        allocation = apportion_slots(_sources(), 11)
        self.assertEqual(sum(allocation.values()), 11)

    def test_shares_follow_demand_order(self):
        allocation = apportion_slots(_sources(), 11)
        self.assertGreater(allocation["payload-science"], allocation["attitude-history"])
        self.assertGreater(allocation["attitude-history"], allocation["housekeeping"])

    def test_equal_demands_split_evenly(self):
        pair = [_source("a", 1024, 1.0), _source("b", 1024, 1.0)]
        self.assertEqual(apportion_slots(pair, 10), {"a": 5, "b": 5})

    def test_largest_remainder_breaks_a_tie_on_the_name(self):
        pair = [_source("zulu", 1024, 1.0), _source("alpha", 1024, 1.0)]
        allocation = apportion_slots(pair, 5)
        self.assertEqual(allocation["alpha"], 3)
        self.assertEqual(allocation["zulu"], 2)

    def test_apportionment_is_reproducible(self):
        self.assertEqual(apportion_slots(_sources(), 11), apportion_slots(_sources(), 11))

    def test_a_tiny_source_can_be_apportioned_no_slot(self):
        mixed = [_source("firehose", 100000, 1.0), _source("trickle", 100, 1.0)]
        allocation = apportion_slots(mixed, 10)
        self.assertEqual(allocation["trickle"], 0)

    def test_cycle_shorter_than_the_source_count_rejected(self):
        with self.assertRaises(ValueError):
            apportion_slots(_sources(), 2)

    def test_non_integer_cycle_rejected(self):
        with self.assertRaises(ValueError):
            apportion_slots(_sources(), 11.0)


class IntervalAndBufferTests(unittest.TestCase):
    def test_interval_is_cycle_over_slots(self):
        self.assertAlmostEqual(service_interval_s(4, 16, 8.0), 2.0)

    def test_more_slots_shorten_the_interval(self):
        few = service_interval_s(2, 16, 8.0)
        many = service_interval_s(8, 16, 8.0)
        self.assertAlmostEqual(few, 4.0 * many)

    def test_zero_slots_rejected_as_never_served(self):
        with self.assertRaises(ValueError):
            service_interval_s(0, 16, 8.0)

    def test_more_slots_than_the_cycle_rejected(self):
        with self.assertRaises(ValueError):
            service_interval_s(20, 16, 8.0)

    def test_latency_adds_the_generation_period(self):
        self.assertAlmostEqual(end_to_end_latency_s(0.5, 2.0), 2.5)

    def test_latency_rejects_a_zero_interval(self):
        with self.assertRaises(ValueError):
            end_to_end_latency_s(0.5, 0.0)

    def test_buffer_holds_one_interval_of_production(self):
        # 2 s interval, 0.5 s period -> 4 packets of 8192 bits
        self.assertEqual(buffer_depth_bits(_source("x", 8192, 0.5), 2.0), 4 * 8192)

    def test_buffer_rounds_a_partial_packet_up(self):
        self.assertEqual(buffer_depth_bits(_source("x", 1024, 1.0), 2.5), 3 * 1024)

    def test_buffer_never_drops_below_one_packet(self):
        self.assertEqual(buffer_depth_bits(_source("x", 1024, 10.0), 0.1), 1024)

    def test_buffer_rejects_a_zero_interval(self):
        with self.assertRaises(ValueError):
            buffer_depth_bits(_source("x", 1024, 1.0), 0.0)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "sources": _sources(),
            "capacity_bps": 32768.0,
            "slots_per_cycle": 16,
            "cycle_duration_s": 8.0,
            "overhead_factor": 1.1,
        }
        spec.update(overrides)
        return spec

    def test_clean_plan_is_compliant(self):
        result = assess_rate_coexistence(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_offered_load_carries_the_overhead(self):
        result = assess_rate_coexistence(self._spec())
        self.assertAlmostEqual(result["offered_load_bps"], 22528.0 * 1.1, places=9)

    def test_every_source_gets_a_report(self):
        result = assess_rate_coexistence(self._spec())
        self.assertEqual(sorted(result["per_source"]), sorted(s["name"] for s in _sources()))

    def test_allocation_covers_the_whole_cycle(self):
        result = assess_rate_coexistence(self._spec())
        self.assertEqual(sum(result["allocation"].values()), 16)

    def test_buffer_is_sized_per_source(self):
        result = assess_rate_coexistence(self._spec())
        entry = result["per_source"]["payload-science"]
        self.assertGreaterEqual(entry["buffer_bits"], 8192)

    def test_overbooked_capacity_is_flagged(self):
        result = assess_rate_coexistence(self._spec(capacity_bps=8000.0))
        self.assertFalse(result["compliant"])
        self.assertFalse(result["within_capacity"])
        self.assertTrue(any("exceeds the downlink capacity" in f for f in result["findings"]))

    def test_capacity_exactly_at_the_offered_load_still_fits(self):
        offered = assess_rate_coexistence(self._spec())["offered_load_bps"]
        result = assess_rate_coexistence(self._spec(capacity_bps=offered))
        self.assertTrue(result["within_capacity"])

    def test_starved_source_is_flagged_as_carried_at_no_rate(self):
        mixed = [
            _source("firehose", 100000, 1.0, 60.0),
            _source("trickle", 100, 1.0, 60.0),
        ]
        result = assess_rate_coexistence(
            self._spec(sources=mixed, slots_per_cycle=10, capacity_bps=200000.0)
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(result["per_source"]["trickle"]["slots"], 0)
        self.assertTrue(any("no rate at all" in f for f in result["findings"]))

    def test_latency_breach_is_flagged(self):
        slow = _sources()
        slow[0] = _source("housekeeping", 2048, 1.0, 0.5)
        result = assess_rate_coexistence(self._spec(sources=slow))
        self.assertFalse(result["compliant"])
        self.assertFalse(result["per_source"]["housekeeping"]["meets_latency"])

    def test_latency_exactly_at_the_limit_is_met(self):
        base = assess_rate_coexistence(self._spec())
        latency = base["per_source"]["housekeeping"]["latency_s"]
        tuned = _sources()
        tuned[0] = _source("housekeeping", 2048, 1.0, latency)
        result = assess_rate_coexistence(self._spec(sources=tuned))
        self.assertTrue(result["per_source"]["housekeeping"]["meets_latency"])

    def test_latency_tolerance_is_representation_sized(self):
        self.assertLess(LATENCY_TOLERANCE_S, 1e-6)

    def test_demand_spread_is_reported(self):
        result = assess_rate_coexistence(self._spec())
        self.assertAlmostEqual(result["demand_spread"], 8.0)

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["cycle_duration_s"]
        with self.assertRaises(ValueError):
            assess_rate_coexistence(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_rate_coexistence(["sources"])

    def test_zero_cycle_duration_rejected(self):
        with self.assertRaises(ValueError):
            assess_rate_coexistence(self._spec(cycle_duration_s=0.0))


if __name__ == "__main__":
    unittest.main()
