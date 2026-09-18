#!/usr/bin/env python3
"""Contract tests for the clause 5.3.4.1.1 representative-interface logic."""

import unittest

from e2020_representative_interface_for_load_testing_logic import (
    DEFAULT_TOLERANCES,
    FLAG_PARAMETERS,
    HARD_SOURCE_FACTOR,
    NUMERIC_PARAMETERS,
    VERDICT_NOT_REPRESENTATIVE,
    VERDICT_REPRESENTATIVE,
    assess_representativeness,
    assess_standalone_load_test,
    compare_flag,
    compare_parameter,
    is_hard_source,
    limitation_expected,
    relative_deviation,
    required_envelope,
    validate_interface,
    validate_tolerances,
)

# A representative branch: a 28 V regulated bus behind a 2 A latching
# current limiter with a 10 ms trip-off delay.
FLIGHT = {
    "nominal_voltage_v": 28.0,
    "current_limit_a": 2.0,
    "trip_off_delay_s": 0.010,
    "source_impedance_ohm": 0.05,
    "source_inductance_h": 2.0e-6,
    "undervoltage_trip_v": 22.0,
    "latching": True,
    "retrigger_inhibited": True,
}


def bench(**overrides):
    """Return a bench interface that matches flight except where overridden."""
    spec = dict(FLIGHT)
    spec.update(overrides)
    return spec


class ValidateInterfaceTests(unittest.TestCase):
    def test_returns_normalised_floats(self):
        out = validate_interface(FLIGHT)
        self.assertAlmostEqual(out["current_limit_a"], 2.0, places=9)
        self.assertIsInstance(out["current_limit_a"], float)

    def test_flags_survive_validation(self):
        out = validate_interface(FLIGHT)
        self.assertTrue(out["latching"])
        self.assertTrue(out["retrigger_inhibited"])

    def test_zero_series_terms_allowed(self):
        out = validate_interface(bench(source_impedance_ohm=0.0, source_inductance_h=0.0))
        self.assertAlmostEqual(out["source_impedance_ohm"], 0.0, places=12)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_interface(["nominal_voltage_v"])

    def test_missing_key_rejected(self):
        spec = dict(FLIGHT)
        del spec["trip_off_delay_s"]
        with self.assertRaises(ValueError):
            validate_interface(spec)

    def test_missing_flag_rejected(self):
        spec = dict(FLIGHT)
        del spec["latching"]
        with self.assertRaises(ValueError):
            validate_interface(spec)

    def test_boolean_masquerading_as_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_interface(bench(current_limit_a=True))

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_interface(bench(latching="yes"))

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_interface(bench(current_limit_a=0.0))

    def test_negative_series_impedance_rejected(self):
        with self.assertRaises(ValueError):
            validate_interface(bench(source_impedance_ohm=-0.01))

    def test_non_finite_delay_rejected(self):
        with self.assertRaises(ValueError):
            validate_interface(bench(trip_off_delay_s=float("inf")))

    def test_undervoltage_above_nominal_rejected(self):
        with self.assertRaises(ValueError):
            validate_interface(bench(undervoltage_trip_v=30.0))


class ToleranceTests(unittest.TestCase):
    def test_defaults_cover_every_numeric_parameter(self):
        self.assertEqual(set(DEFAULT_TOLERANCES), set(NUMERIC_PARAMETERS))

    def test_project_override_replaces_one_entry(self):
        out = validate_tolerances({"current_limit_a": 0.02})
        self.assertAlmostEqual(out["current_limit_a"], 0.02, places=9)
        self.assertAlmostEqual(
            out["trip_off_delay_s"], DEFAULT_TOLERANCES["trip_off_delay_s"], places=9
        )

    def test_unknown_parameter_rejected(self):
        with self.assertRaises(ValueError):
            validate_tolerances({"cable_length_m": 0.1})

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_tolerances({"current_limit_a": -0.1})

    def test_non_mapping_tolerances_rejected(self):
        with self.assertRaises(ValueError):
            validate_tolerances([0.1])


class RelativeDeviationTests(unittest.TestCase):
    def test_exact_match_is_zero(self):
        self.assertAlmostEqual(relative_deviation(2.0, 2.0), 0.0, places=12)

    def test_deviation_is_signless(self):
        self.assertAlmostEqual(
            relative_deviation(2.0, 2.4), relative_deviation(2.0, 1.6), places=9
        )

    def test_quarter_above_reference(self):
        self.assertAlmostEqual(relative_deviation(4.0, 5.0), 0.25, places=9)

    def test_zero_reference_matched_by_zero_candidate(self):
        self.assertAlmostEqual(relative_deviation(0.0, 0.0), 0.0, places=12)

    def test_zero_reference_with_finite_candidate_is_infinite(self):
        self.assertEqual(relative_deviation(0.0, 0.01), float("inf"))

    def test_negative_value_rejected(self):
        with self.assertRaises(ValueError):
            relative_deviation(2.0, -1.0)

    def test_non_numeric_rejected(self):
        with self.assertRaises(ValueError):
            relative_deviation("2.0", 2.0)


class CompareParameterTests(unittest.TestCase):
    def test_match_is_within_tolerance(self):
        record = compare_parameter("current_limit_a", 2.0, 2.0, 0.10)
        self.assertTrue(record["within_tolerance"])

    def test_value_exactly_on_the_tolerance_is_inside_it(self):
        record = compare_parameter("current_limit_a", 2.0, 2.2, 0.10)
        self.assertAlmostEqual(record["deviation"], 0.10, places=9)
        self.assertTrue(record["within_tolerance"])

    def test_value_beyond_the_tolerance_is_outside_it(self):
        record = compare_parameter("current_limit_a", 2.0, 2.5, 0.10)
        self.assertFalse(record["within_tolerance"])

    def test_unknown_parameter_rejected(self):
        with self.assertRaises(ValueError):
            compare_parameter("harness_mass_kg", 1.0, 1.0, 0.1)

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            compare_parameter("current_limit_a", 2.0, 2.0, -0.1)


class CompareFlagTests(unittest.TestCase):
    def test_matching_flags(self):
        self.assertTrue(compare_flag("latching", True, True)["matches"])

    def test_differing_flags(self):
        self.assertFalse(compare_flag("retrigger_inhibited", True, False)["matches"])

    def test_unknown_flag_rejected(self):
        with self.assertRaises(ValueError):
            compare_flag("fused", True, True)

    def test_non_boolean_rejected(self):
        with self.assertRaises(ValueError):
            compare_flag("latching", True, 1)


class HardSourceTests(unittest.TestCase):
    def test_matched_bench_is_not_hard(self):
        self.assertFalse(is_hard_source(FLIGHT, bench()))

    def test_non_latching_bench_is_hard(self):
        self.assertTrue(is_hard_source(FLIGHT, bench(latching=False)))

    def test_limit_exactly_at_the_hard_factor_is_not_hard(self):
        ceiling = FLIGHT["current_limit_a"] * HARD_SOURCE_FACTOR
        self.assertFalse(is_hard_source(FLIGHT, bench(current_limit_a=ceiling)))

    def test_limit_far_above_flight_is_hard(self):
        self.assertTrue(is_hard_source(FLIGHT, bench(current_limit_a=20.0)))

    def test_hard_factor_at_unity_rejected(self):
        with self.assertRaises(ValueError):
            is_hard_source(FLIGHT, bench(), hard_factor=1.0)


class EnvelopeTests(unittest.TestCase):
    def test_envelope_brackets_the_flight_value(self):
        envelope = required_envelope(FLIGHT)
        low, high = envelope["current_limit_a"]
        self.assertAlmostEqual(low, 1.8, places=9)
        self.assertAlmostEqual(high, 2.2, places=9)

    def test_envelope_covers_every_numeric_parameter(self):
        self.assertEqual(set(required_envelope(FLIGHT)), set(NUMERIC_PARAMETERS))

    def test_tighter_tolerance_narrows_the_envelope(self):
        tight = required_envelope(FLIGHT, {"current_limit_a": 0.01})
        low, high = tight["current_limit_a"]
        self.assertAlmostEqual(high - low, 0.04, places=9)


class LimitationExpectedTests(unittest.TestCase):
    def test_inrush_below_the_limit_never_provokes_limitation(self):
        self.assertFalse(limitation_expected(FLIGHT, 1.5))

    def test_inrush_exactly_at_the_limit_provokes_limitation(self):
        self.assertTrue(limitation_expected(FLIGHT, 2.0))

    def test_inrush_above_the_limit_provokes_limitation(self):
        self.assertTrue(limitation_expected(FLIGHT, 9.0))

    def test_negative_inrush_rejected(self):
        with self.assertRaises(ValueError):
            limitation_expected(FLIGHT, -1.0)


class AssessRepresentativenessTests(unittest.TestCase):
    def test_identical_interface_is_representative(self):
        report = assess_representativeness(FLIGHT, bench())
        self.assertTrue(report["representative"])
        self.assertEqual(report["verdict"], VERDICT_REPRESENTATIVE)
        self.assertEqual(report["findings"], [])

    def test_small_parasitic_difference_still_representative(self):
        report = assess_representativeness(FLIGHT, bench(source_impedance_ohm=0.06))
        self.assertTrue(report["representative"])

    def test_delay_far_off_is_a_finding(self):
        report = assess_representativeness(FLIGHT, bench(trip_off_delay_s=0.100))
        self.assertFalse(report["representative"])
        self.assertEqual(report["verdict"], VERDICT_NOT_REPRESENTATIVE)
        self.assertTrue(any("trip-off-delay-s" in f for f in report["findings"]))

    def test_flag_mismatch_is_a_finding_with_no_tolerance(self):
        report = assess_representativeness(FLIGHT, bench(retrigger_inhibited=False))
        self.assertFalse(report["representative"])
        self.assertTrue(any("retrigger-inhibited" in f for f in report["findings"]))

    def test_hard_bench_supply_is_reported_as_such(self):
        report = assess_representativeness(FLIGHT, bench(current_limit_a=25.0, latching=False))
        self.assertTrue(report["hard_source"])
        self.assertFalse(report["representative"])

    def test_every_numeric_parameter_is_compared(self):
        report = assess_representativeness(FLIGHT, bench())
        names = [record["parameter"] for record in report["comparisons"]]
        self.assertEqual(set(names), set(NUMERIC_PARAMETERS))

    def test_every_flag_is_compared(self):
        report = assess_representativeness(FLIGHT, bench())
        names = [record["parameter"] for record in report["flags"]]
        self.assertEqual(set(names), set(FLAG_PARAMETERS))

    def test_project_tolerance_can_tighten_a_pass_into_a_finding(self):
        loose = assess_representativeness(FLIGHT, bench(current_limit_a=2.15))
        tight = assess_representativeness(
            FLIGHT, bench(current_limit_a=2.15), {"current_limit_a": 0.01}
        )
        self.assertTrue(loose["representative"])
        self.assertFalse(tight["representative"])


class AssessStandaloneLoadTestTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "flight_interface": FLIGHT,
            "bench_interface": bench(),
            "load_inrush_current_a": 6.0,
            "load_steady_current_a": 1.2,
        }
        spec.update(overrides)
        return spec

    def test_matched_bench_transfers_its_evidence(self):
        report = assess_standalone_load_test(self._spec())
        self.assertTrue(report["evidence_transfers"])
        self.assertEqual(report["verdict"], VERDICT_REPRESENTATIVE)

    def test_inrush_above_the_limit_flags_the_reproduction_gap(self):
        report = assess_standalone_load_test(
            self._spec(bench_interface=bench(current_limit_a=25.0, latching=False))
        )
        self.assertFalse(report["evidence_transfers"])
        self.assertTrue(report["limitation_expected"])
        self.assertTrue(any("has to reproduce" in f for f in report["findings"]))

    def test_gentle_load_behind_a_hard_bench_still_fails_on_the_interface(self):
        report = assess_standalone_load_test(
            self._spec(
                load_inrush_current_a=1.0,
                load_steady_current_a=0.8,
                bench_interface=bench(latching=False),
            )
        )
        self.assertFalse(report["limitation_expected"])
        self.assertFalse(report["evidence_transfers"])

    def test_steady_demand_above_the_limit_is_its_own_finding(self):
        report = assess_standalone_load_test(
            self._spec(load_steady_current_a=3.0, load_inrush_current_a=6.0)
        )
        self.assertTrue(any("never reaches a stable state" in f for f in report["findings"]))

    def test_steady_above_inrush_rejected(self):
        with self.assertRaises(ValueError):
            assess_standalone_load_test(
                self._spec(load_steady_current_a=8.0, load_inrush_current_a=6.0)
            )

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["bench_interface"]
        with self.assertRaises(ValueError):
            assess_standalone_load_test(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_standalone_load_test(["flight_interface"])

    def test_negative_load_current_rejected(self):
        with self.assertRaises(ValueError):
            assess_standalone_load_test(self._spec(load_steady_current_a=-1.0))


if __name__ == "__main__":
    unittest.main()
