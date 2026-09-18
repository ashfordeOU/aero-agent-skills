"""Contract tests for the clause 5.5.2 essential-telemetry acquisition logic."""

import unittest

from e50_essential_telemetry_acquisition_logic import (
    DEFAULT_HEALTH_CATEGORIES,
    RATE_TOLERANCE_BPS,
    aggregate_bit_rate_bps,
    assess_essential_telemetry,
    capacity_headroom_bps,
    chain_dependent_parameters,
    fits_capacity,
    parameter_bit_rate_bps,
    phase_gaps,
    uncovered_categories,
    validate_parameter,
    validate_parameter_set,
)

PHASES = ("launch", "leop", "nominal", "safe", "contingency")


def _param(name, category, bits=8, rate=1.0, phases=PHASES, chain_dependent=False):
    return {
        "name": name,
        "category": category,
        "bits_per_sample": bits,
        "sample_rate_hz": rate,
        "phases": list(phases),
        "chain_dependent": chain_dependent,
    }


def _full_set():
    return [
        _param("bus-voltage", "power", 12, 1.0),
        _param("battery-temperature", "thermal", 12, 0.5),
        _param("body-rate-x", "attitude", 16, 2.0),
        _param("receiver-lock", "command-link", 8, 1.0),
        _param("processor-mode", "on-board-computer", 8, 1.0),
    ]


class ValidateParameterTests(unittest.TestCase):
    def test_returns_normalised_record(self):
        record = validate_parameter(_param("bus-voltage", "power", 12, 2.0))
        self.assertEqual(record["name"], "bus-voltage")
        self.assertEqual(record["bits_per_sample"], 12)
        self.assertAlmostEqual(record["sample_rate_hz"], 2.0)

    def test_phases_become_a_frozenset(self):
        record = validate_parameter(_param("bus-voltage", "power"))
        self.assertIsInstance(record["phases"], frozenset)
        self.assertIn("safe", record["phases"])

    def test_chain_dependent_defaults_to_false(self):
        param = _param("bus-voltage", "power")
        del param["chain_dependent"]
        self.assertFalse(validate_parameter(param)["chain_dependent"])

    def test_missing_key_rejected(self):
        param = _param("bus-voltage", "power")
        del param["category"]
        with self.assertRaises(ValueError):
            validate_parameter(param)

    def test_zero_bits_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(_param("bus-voltage", "power", bits=0))

    def test_float_bits_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(_param("bus-voltage", "power", bits=8.0))

    def test_negative_sample_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(_param("bus-voltage", "power", rate=-1.0))

    def test_empty_phase_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(_param("bus-voltage", "power", phases=()))

    def test_phase_string_rejected(self):
        param = _param("bus-voltage", "power")
        param["phases"] = "safe"
        with self.assertRaises(ValueError):
            validate_parameter(param)

    def test_non_boolean_chain_flag_rejected(self):
        param = _param("bus-voltage", "power")
        param["chain_dependent"] = "yes"
        with self.assertRaises(ValueError):
            validate_parameter(param)

    def test_non_mapping_parameter_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(["bus-voltage"])


class ParameterSetTests(unittest.TestCase):
    def test_full_set_validates(self):
        self.assertEqual(len(validate_parameter_set(_full_set())), 5)

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter_set([])

    def test_duplicate_name_rejected(self):
        params = _full_set()
        params.append(_param("bus-voltage", "power"))
        with self.assertRaises(ValueError):
            validate_parameter_set(params)

    def test_mapping_instead_of_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter_set({"name": "bus-voltage"})


class RateTests(unittest.TestCase):
    def test_parameter_rate_is_bits_times_rate(self):
        self.assertAlmostEqual(
            parameter_bit_rate_bps(_param("x", "power", 12, 2.0)), 24.0
        )

    def test_aggregate_without_overhead(self):
        # 12*1 + 12*0.5 + 16*2 + 8*1 + 8*1 = 12 + 6 + 32 + 8 + 8 = 66
        self.assertAlmostEqual(aggregate_bit_rate_bps(_full_set()), 66.0)

    def test_overhead_factor_scales_the_aggregate(self):
        plain = aggregate_bit_rate_bps(_full_set())
        grossed = aggregate_bit_rate_bps(_full_set(), 1.25)
        self.assertAlmostEqual(grossed, plain * 1.25)

    def test_overhead_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_bit_rate_bps(_full_set(), 0.9)

    def test_zero_overhead_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_bit_rate_bps(_full_set(), 0.0)

    def test_headroom_is_capacity_minus_aggregate(self):
        self.assertAlmostEqual(capacity_headroom_bps(66.0, 100.0), 34.0)

    def test_overrun_gives_negative_headroom(self):
        self.assertAlmostEqual(capacity_headroom_bps(150.0, 100.0), -50.0)

    def test_exact_equality_fits_within_tolerance(self):
        self.assertTrue(fits_capacity(66.0, 66.0))
        self.assertLessEqual(abs(capacity_headroom_bps(66.0, 66.0)), RATE_TOLERANCE_BPS)

    def test_clear_overrun_does_not_fit(self):
        self.assertFalse(fits_capacity(1000.0, 100.0))

    def test_non_positive_capacity_rejected(self):
        with self.assertRaises(ValueError):
            capacity_headroom_bps(66.0, 0.0)


class CoverageTests(unittest.TestCase):
    def test_full_set_covers_every_default_category(self):
        self.assertEqual(uncovered_categories(_full_set()), [])

    def test_missing_category_is_reported(self):
        params = [p for p in _full_set() if p["category"] != "thermal"]
        self.assertEqual(uncovered_categories(params), ["thermal"])

    def test_mission_specific_category_list_is_honoured(self):
        self.assertEqual(
            uncovered_categories(_full_set(), ["power", "propulsion"]), ["propulsion"]
        )

    def test_empty_category_list_rejected(self):
        with self.assertRaises(ValueError):
            uncovered_categories(_full_set(), [])

    def test_default_categories_include_the_command_link(self):
        self.assertIn("command-link", DEFAULT_HEALTH_CATEGORIES)

    def test_no_phase_gaps_when_every_phase_is_covered(self):
        self.assertEqual(phase_gaps(_full_set(), PHASES), {})

    def test_nominal_only_parameter_gaps_on_safe_and_contingency(self):
        params = _full_set()
        params[1] = _param("battery-temperature", "thermal", 12, 0.5, ("nominal",))
        gaps = phase_gaps(params, PHASES)
        self.assertEqual(
            gaps["battery-temperature"], ["contingency", "launch", "leop", "safe"]
        )

    def test_phase_gap_only_reports_incomplete_parameters(self):
        params = _full_set()
        params[0] = _param("bus-voltage", "power", 12, 1.0, ("nominal", "safe"))
        gaps = phase_gaps(params, PHASES)
        self.assertEqual(sorted(gaps), ["bus-voltage"])

    def test_chain_dependent_names_are_listed(self):
        params = _full_set()
        params[2]["chain_dependent"] = True
        self.assertEqual(chain_dependent_parameters(params), ["body-rate-x"])

    def test_no_chain_dependent_parameters_in_a_clean_set(self):
        self.assertEqual(chain_dependent_parameters(_full_set()), [])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "parameters": _full_set(),
            "mission_phases": PHASES,
            "emergency_capacity_bps": 128.0,
            "overhead_factor": 1.2,
        }
        spec.update(overrides)
        return spec

    def test_clean_set_is_compliant(self):
        result = assess_essential_telemetry(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_aggregate_carries_the_overhead_factor(self):
        result = assess_essential_telemetry(self._spec())
        self.assertAlmostEqual(result["aggregate_bps"], 66.0 * 1.2)

    def test_per_parameter_rates_are_reported(self):
        result = assess_essential_telemetry(self._spec())
        self.assertAlmostEqual(result["parameter_rates_bps"]["body-rate-x"], 32.0)

    def test_capacity_overrun_is_flagged(self):
        result = assess_essential_telemetry(self._spec(emergency_capacity_bps=32.0))
        self.assertFalse(result["compliant"])
        self.assertFalse(result["within_capacity"])
        self.assertTrue(any("exceeds" in f for f in result["findings"]))

    def test_exact_capacity_match_stays_compliant(self):
        result = assess_essential_telemetry(
            self._spec(emergency_capacity_bps=66.0 * 1.2)
        )
        self.assertTrue(result["within_capacity"])
        self.assertAlmostEqual(result["headroom_bps"], 0.0, places=9)

    def test_uncovered_category_is_flagged(self):
        params = [p for p in _full_set() if p["category"] != "attitude"]
        result = assess_essential_telemetry(self._spec(parameters=params))
        self.assertEqual(result["uncovered_categories"], ["attitude"])
        self.assertFalse(result["compliant"])

    def test_phase_gap_is_flagged(self):
        params = _full_set()
        params[4] = _param("processor-mode", "on-board-computer", 8, 1.0, ("nominal",))
        result = assess_essential_telemetry(self._spec(parameters=params))
        self.assertIn("processor-mode", result["phase_gaps"])
        self.assertFalse(result["compliant"])

    def test_chain_dependent_parameter_is_flagged(self):
        params = _full_set()
        params[0]["chain_dependent"] = True
        result = assess_essential_telemetry(self._spec(parameters=params))
        self.assertEqual(result["chain_dependent"], ["bus-voltage"])
        self.assertTrue(any("processor reset" in f for f in result["findings"]))

    def test_findings_accumulate_across_defect_kinds(self):
        params = [p for p in _full_set() if p["category"] != "thermal"]
        params[0]["chain_dependent"] = True
        result = assess_essential_telemetry(
            self._spec(parameters=params, emergency_capacity_bps=4.0)
        )
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["emergency_capacity_bps"]
        with self.assertRaises(ValueError):
            assess_essential_telemetry(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_essential_telemetry(["parameters"])

    def test_zero_capacity_rejected(self):
        with self.assertRaises(ValueError):
            assess_essential_telemetry(self._spec(emergency_capacity_bps=0.0))


if __name__ == "__main__":
    unittest.main()
