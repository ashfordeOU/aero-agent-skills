"""Contract tests for the clause 4.3.5 and 4.3.6 telemetry and software logic."""

import math
import unittest

from e31_tm_tc_obdh_sw_interface_requirements_logic import (
    DEADBAND_KNOWLEDGE_FACTOR,
    KNOWLEDGE_TOLERANCE_K,
    MIN_SAMPLES_PER_TIME_CONSTANT,
    assess_tm_tc_interfaces,
    channel_bit_rate_bps,
    channel_knowledge_k,
    deadband_adequate,
    evaluate_channel,
    evaluate_control_line,
    predicted_cycle_period_s,
    quantisation_step_k,
    samples_per_time_constant,
    telemetry_bandwidth_bps,
    validate_limit_ordering,
    validate_positive,
)


def channel(**overrides):
    """Return a representative thermal telemetry channel record."""
    record = {
        "name": "tank-skin-thermistor-1",
        "span_k": 200.0,
        "converter_bits": 12,
        "sensor_tolerance_k": 0.5,
        "chain_error_k": 0.2,
        "sample_period_s": 8.0,
        "required_knowledge_k": 1.0,
        "time_constant_s": 900.0,
    }
    record.update(overrides)
    return record


def control_line(**overrides):
    """Return a representative software-owned heater control line record."""
    record = {
        "name": "tank-heater-loop",
        "channel": "tank-skin-thermistor-1",
        "command_id": "TC-THM-0041",
        "status_telemetry_id": "TM-THM-0041",
        "low_alarm_c": -20.0,
        "switch_on_c": 5.0,
        "switch_off_c": 11.0,
        "high_alarm_c": 45.0,
        "heating_rate_k_per_s": 0.01,
        "cooling_rate_k_per_s": 0.004,
    }
    record.update(overrides)
    return record


class ValidatePositiveTests(unittest.TestCase):
    def test_returns_float(self):
        self.assertEqual(validate_positive("x", 5), 5.0)

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", -1.0)

    def test_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", "5")


class QuantisationTests(unittest.TestCase):
    def test_step_is_span_over_full_scale_counts(self):
        self.assertAlmostEqual(quantisation_step_k(200.0, 12), 200.0 / 4095.0, places=12)

    def test_extra_bit_halves_the_step(self):
        coarse = quantisation_step_k(200.0, 8)
        fine = quantisation_step_k(200.0, 9)
        self.assertAlmostEqual(coarse / fine, 511.0 / 255.0, places=12)

    def test_float_bit_count_rejected(self):
        with self.assertRaises(ValueError):
            quantisation_step_k(200.0, 12.0)

    def test_one_bit_rejected(self):
        with self.assertRaises(ValueError):
            quantisation_step_k(200.0, 1)

    def test_absurd_bit_count_rejected(self):
        with self.assertRaises(ValueError):
            quantisation_step_k(200.0, 64)

    def test_zero_span_rejected(self):
        with self.assertRaises(ValueError):
            quantisation_step_k(0.0, 12)


class KnowledgeTests(unittest.TestCase):
    def test_knowledge_is_root_sum_square(self):
        value = channel_knowledge_k(0.4, 0.3, 0.4)
        self.assertAlmostEqual(value, math.sqrt(0.04 + 0.09 + 0.16), places=12)

    def test_quantisation_alone_is_half_the_step(self):
        self.assertAlmostEqual(channel_knowledge_k(1.0, 0.0, 0.0), 0.5, places=12)

    def test_knowledge_never_below_its_largest_term(self):
        value = channel_knowledge_k(0.2, 1.5, 0.1)
        self.assertGreater(value, 1.5)

    def test_negative_sensor_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            channel_knowledge_k(0.4, -0.3, 0.1)

    def test_zero_step_rejected(self):
        with self.assertRaises(ValueError):
            channel_knowledge_k(0.0, 0.3, 0.1)


class SamplingTests(unittest.TestCase):
    def test_samples_are_tau_over_period(self):
        self.assertAlmostEqual(samples_per_time_constant(900.0, 8.0), 112.5, places=12)

    def test_longer_period_gives_fewer_samples(self):
        self.assertLess(
            samples_per_time_constant(900.0, 300.0),
            samples_per_time_constant(900.0, 8.0),
        )

    def test_zero_period_rejected(self):
        with self.assertRaises(ValueError):
            samples_per_time_constant(900.0, 0.0)

    def test_bit_rate_is_bits_over_period(self):
        self.assertAlmostEqual(channel_bit_rate_bps(12, 8.0), 1.5, places=12)

    def test_bit_rate_rejects_float_bits(self):
        with self.assertRaises(ValueError):
            channel_bit_rate_bps(12.0, 8.0)


class EvaluateChannelTests(unittest.TestCase):
    def test_nominal_channel_is_compliant(self):
        record = evaluate_channel(channel())
        self.assertTrue(record["compliant"])
        self.assertEqual(record["findings"], [])

    def test_coarse_converter_fails_the_knowledge_requirement(self):
        record = evaluate_channel(channel(converter_bits=6))
        self.assertFalse(record["compliant"])
        self.assertTrue(any("knowledge" in f for f in record["findings"]))

    def test_slow_sampling_fails_the_transient_requirement(self):
        record = evaluate_channel(channel(sample_period_s=600.0))
        self.assertFalse(record["compliant"])
        self.assertTrue(any("samples per time constant" in f for f in record["findings"]))

    def test_sampling_exactly_at_the_floor_is_accepted(self):
        period = 900.0 / MIN_SAMPLES_PER_TIME_CONSTANT
        record = evaluate_channel(channel(sample_period_s=period))
        self.assertAlmostEqual(
            record["samples_per_time_constant"],
            MIN_SAMPLES_PER_TIME_CONSTANT,
            places=9,
        )
        self.assertTrue(record["compliant"])

    def test_knowledge_exactly_on_the_requirement_is_accepted(self):
        probe = evaluate_channel(channel())
        tuned = evaluate_channel(
            channel(required_knowledge_k=probe["knowledge_k"])
        )
        self.assertAlmostEqual(
            tuned["knowledge_k"], tuned["required_knowledge_k"], places=12
        )
        self.assertTrue(tuned["compliant"])

    def test_missing_key_rejected(self):
        bad = channel()
        del bad["time_constant_s"]
        with self.assertRaises(ValueError):
            evaluate_channel(bad)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_channel("thermistor")

    def test_tolerance_is_a_rounding_allowance(self):
        self.assertLess(KNOWLEDGE_TOLERANCE_K, 1e-6)


class BandwidthTests(unittest.TestCase):
    def test_bandwidth_sums_the_channels(self):
        records = [evaluate_channel(channel()),
                   evaluate_channel(channel(name="radiator-thermistor-1"))]
        self.assertAlmostEqual(telemetry_bandwidth_bps(records), 3.0, places=12)

    def test_empty_record_set_rejected(self):
        with self.assertRaises(ValueError):
            telemetry_bandwidth_bps([])

    def test_malformed_record_rejected(self):
        with self.assertRaises(ValueError):
            telemetry_bandwidth_bps([{"name": "x"}])


class LimitOrderingTests(unittest.TestCase):
    def test_ordered_limits_returned(self):
        self.assertEqual(
            validate_limit_ordering(-20.0, 5.0, 11.0, 45.0), (-20.0, 5.0, 11.0, 45.0)
        )

    def test_inverted_setpoints_rejected(self):
        with self.assertRaises(ValueError):
            validate_limit_ordering(-20.0, 11.0, 5.0, 45.0)

    def test_setpoint_outside_the_alarm_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_limit_ordering(-20.0, 5.0, 60.0, 45.0)

    def test_equal_setpoints_rejected(self):
        with self.assertRaises(ValueError):
            validate_limit_ordering(-20.0, 5.0, 5.0, 45.0)

    def test_non_numeric_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_limit_ordering(-20.0, "5", 11.0, 45.0)


class DeadbandTests(unittest.TestCase):
    def test_wide_deadband_is_adequate(self):
        self.assertTrue(deadband_adequate(6.0, 0.8))

    def test_deadband_exactly_at_the_floor_is_adequate(self):
        knowledge = 0.75
        self.assertTrue(
            deadband_adequate(DEADBAND_KNOWLEDGE_FACTOR * knowledge, knowledge)
        )

    def test_narrow_deadband_is_not_adequate(self):
        self.assertFalse(deadband_adequate(1.0, 0.8))

    def test_zero_deadband_rejected(self):
        with self.assertRaises(ValueError):
            deadband_adequate(0.0, 0.8)

    def test_cycle_period_adds_both_ramps(self):
        self.assertAlmostEqual(
            predicted_cycle_period_s(6.0, 0.01, 0.004), 600.0 + 1500.0, places=9
        )

    def test_wider_deadband_lengthens_the_cycle(self):
        short = predicted_cycle_period_s(3.0, 0.01, 0.004)
        long_cycle = predicted_cycle_period_s(6.0, 0.01, 0.004)
        self.assertAlmostEqual(long_cycle / short, 2.0, places=12)

    def test_zero_cooling_rate_rejected(self):
        with self.assertRaises(ValueError):
            predicted_cycle_period_s(6.0, 0.01, 0.0)


class ControlLineTests(unittest.TestCase):
    def test_nominal_line_is_compliant(self):
        record = evaluate_control_line(control_line(), 0.8)
        self.assertTrue(record["compliant"])
        self.assertAlmostEqual(record["deadband_k"], 6.0, places=12)

    def test_narrow_deadband_raises_a_chatter_finding(self):
        record = evaluate_control_line(control_line(switch_off_c=5.5), 0.8)
        self.assertFalse(record["compliant"])
        self.assertTrue(any("noise" in f for f in record["findings"]))

    def test_blank_command_identifier_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_control_line(control_line(command_id="   "), 0.8)

    def test_missing_status_telemetry_rejected(self):
        bad = control_line()
        del bad["status_telemetry_id"]
        with self.assertRaises(ValueError):
            evaluate_control_line(bad, 0.8)

    def test_unordered_limits_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_control_line(control_line(high_alarm_c=8.0), 0.8)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "channels": [channel(), channel(name="radiator-thermistor-1",
                                            required_knowledge_k=2.0)],
            "control_lines": [control_line()],
            "bandwidth_allocation_bps": 16.0,
        }
        spec.update(overrides)
        return spec

    def test_nominal_assessment_is_compliant(self):
        result = assess_tm_tc_interfaces(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_bandwidth_reported(self):
        result = assess_tm_tc_interfaces(self._spec())
        self.assertAlmostEqual(result["telemetry_bandwidth_bps"], 3.0, places=12)

    def test_bandwidth_overrun_raises_a_finding(self):
        result = assess_tm_tc_interfaces(self._spec(bandwidth_allocation_bps=1.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("bandwidth" in f for f in result["findings"]))

    def test_control_line_reading_an_undeclared_channel_rejected(self):
        spec = self._spec(control_lines=[control_line(channel="nowhere-thermistor")])
        with self.assertRaises(ValueError):
            assess_tm_tc_interfaces(spec)

    def test_duplicate_channel_names_rejected(self):
        spec = self._spec(channels=[channel(), channel()])
        with self.assertRaises(ValueError):
            assess_tm_tc_interfaces(spec)

    def test_empty_control_line_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_tm_tc_interfaces(self._spec(control_lines=[]))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["bandwidth_allocation_bps"]
        with self.assertRaises(ValueError):
            assess_tm_tc_interfaces(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_tm_tc_interfaces(None)

    def test_channel_findings_reach_the_aggregate(self):
        spec = self._spec()
        spec["channels"][0]["converter_bits"] = 6
        result = assess_tm_tc_interfaces(spec)
        self.assertFalse(result["compliant"])
        self.assertTrue(result["findings"])


if __name__ == "__main__":
    unittest.main()
