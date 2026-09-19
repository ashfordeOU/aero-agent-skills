"""Contract tests for the clause 4.7.2 general design requirement logic."""

import unittest

from e3301_general_design_requirements_logic import (
    AMBIENT_PRESSURE_PA,
    MARGIN_TOLERANCE,
    REQUIRED_OPERATING_MODES,
    REQUIRED_PHASES,
    assess_general_design,
    cumulative_duty,
    encloses,
    environment_envelope,
    grade_phase,
    missing_phases,
    normalise_phase,
    operating_modes_gap,
    validate_number,
    validate_range,
)

PHASES = {
    "handling": {
        "temperature_c": (15.0, 30.0),
        "pressure_pa": (AMBIENT_PRESSURE_PA, AMBIENT_PRESSURE_PA),
        "humidity_pct": 60.0,
        "duration_hours": 50.0,
        "cycles": 20.0,
    },
    "transport": {
        "temperature_c": (-10.0, 45.0),
        "pressure_pa": (70000.0, AMBIENT_PRESSURE_PA),
        "humidity_pct": 75.0,
        "random_vibration_grms": 1.5,
        "shock_g": 5.0,
        "duration_hours": 200.0,
    },
    "test": {
        "temperature_c": (-40.0, 70.0),
        "pressure_pa": (1.0e-4, AMBIENT_PRESSURE_PA),
        "humidity_pct": 60.0,
        "random_vibration_grms": 10.0,
        "shock_g": 100.0,
        "duration_hours": 300.0,
        "cycles": 2000.0,
    },
    "storage": {
        "temperature_c": (5.0, 35.0),
        "pressure_pa": (AMBIENT_PRESSURE_PA, AMBIENT_PRESSURE_PA),
        "humidity_pct": 50.0,
        "duration_hours": 8760.0,
    },
    "launch": {
        "temperature_c": (-20.0, 60.0),
        "pressure_pa": (1.0e-3, AMBIENT_PRESSURE_PA),
        "random_vibration_grms": 14.0,
        "shock_g": 1500.0,
        "duration_hours": 1.0,
    },
    "orbit": {
        "temperature_c": (-60.0, 90.0),
        "pressure_pa": (1.0e-7, 1.0e-5),
        "duration_hours": 43800.0,
        "cycles": 30000.0,
    },
}

CAPABILITY = {
    "temperature_c": (-70.0, 100.0),
    "pressure_pa": (1.0e-9, 110000.0),
    "humidity_max_pct": 80.0,
    "random_vibration_grms": 16.0,
    "shock_g": 2000.0,
}


def _spec(**overrides):
    spec = {
        "phases": {name: dict(env) for name, env in PHASES.items()},
        "capability": dict(CAPABILITY),
        "operating_modes": ["ground-ambient", "thermal-vacuum"],
        "qualified_life_hours": 60000.0,
        "qualified_life_cycles": 40000.0,
    }
    spec.update(overrides)
    return spec


class ValidationTests(unittest.TestCase):
    def test_number_returns_float(self):
        self.assertAlmostEqual(validate_number("x", 4), 4.0)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_number("x", False)

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_number("x", float("inf"))

    def test_negative_rejected_when_disallowed(self):
        with self.assertRaises(ValueError):
            validate_number("x", -1.0, allow_negative=False)

    def test_range_orders_a_valid_pair(self):
        self.assertEqual(validate_range("t", -40, 70), (-40.0, 70.0))

    def test_inverted_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_range("t", 70, -40)

    def test_enclosure_accepts_a_contained_range(self):
        self.assertTrue(encloses((-70.0, 100.0), (-40.0, 70.0)))

    def test_enclosure_accepts_exact_coincidence(self):
        self.assertTrue(encloses((-70.0, 100.0), (-70.0, 100.0)))

    def test_enclosure_rejects_an_overhang(self):
        self.assertFalse(encloses((-70.0, 100.0), (-80.0, 70.0)))


class PhaseNormalisationTests(unittest.TestCase):
    def test_defaults_fill_the_optional_loads(self):
        record = normalise_phase("orbit", PHASES["orbit"])
        self.assertAlmostEqual(record["random_vibration_grms"], 0.0)
        self.assertIsNone(record["humidity_pct"])

    def test_declared_humidity_is_kept_at_ambient_pressure(self):
        record = normalise_phase("storage", PHASES["storage"])
        self.assertAlmostEqual(record["humidity_pct"], 50.0)

    def test_humidity_in_vacuum_is_rejected(self):
        env = dict(PHASES["orbit"])
        env["humidity_pct"] = 40.0
        with self.assertRaises(ValueError):
            normalise_phase("orbit", env)

    def test_humidity_above_one_hundred_rejected(self):
        env = dict(PHASES["storage"])
        env["humidity_pct"] = 120.0
        with self.assertRaises(ValueError):
            normalise_phase("storage", env)

    def test_negative_pressure_rejected(self):
        env = dict(PHASES["orbit"])
        env["pressure_pa"] = (-1.0, 1.0e-5)
        with self.assertRaises(ValueError):
            normalise_phase("orbit", env)

    def test_missing_temperature_rejected(self):
        with self.assertRaises(ValueError):
            normalise_phase("handling", {"pressure_pa": (1.0, 2.0)})

    def test_scalar_temperature_rejected(self):
        with self.assertRaises(ValueError):
            normalise_phase("handling", {"temperature_c": 20.0, "pressure_pa": (1.0, 2.0)})

    def test_empty_phase_name_rejected(self):
        with self.assertRaises(ValueError):
            normalise_phase("  ", PHASES["orbit"])


class CoverageTests(unittest.TestCase):
    def test_full_declaration_has_no_missing_phase(self):
        self.assertEqual(missing_phases(list(PHASES)), ())

    def test_absent_storage_is_reported(self):
        names = [name for name in PHASES if name != "storage"]
        self.assertEqual(missing_phases(names), ("storage",))

    def test_phase_names_are_matched_case_insensitively(self):
        self.assertEqual(missing_phases([name.upper() for name in PHASES]), ())

    def test_non_string_phase_name_rejected(self):
        with self.assertRaises(ValueError):
            missing_phases([1])

    def test_required_phase_list_is_the_full_life_cycle(self):
        self.assertEqual(len(REQUIRED_PHASES), 6)

    def test_both_operating_modes_required(self):
        self.assertEqual(operating_modes_gap(["ground-ambient"]), ("thermal-vacuum",))

    def test_no_gap_when_both_modes_declared(self):
        self.assertEqual(operating_modes_gap(list(REQUIRED_OPERATING_MODES)), ())

    def test_non_sequence_mode_list_rejected(self):
        with self.assertRaises(ValueError):
            operating_modes_gap("ground-ambient")


class EnvelopeAndDutyTests(unittest.TestCase):
    def _records(self):
        return [normalise_phase(name, env) for name, env in sorted(PHASES.items())]

    def test_envelope_bounds_the_temperature(self):
        envelope = environment_envelope(self._records())
        self.assertAlmostEqual(envelope["temperature_c"][0], -60.0)
        self.assertAlmostEqual(envelope["temperature_c"][1], 90.0)

    def test_envelope_takes_the_worst_dynamic_levels(self):
        envelope = environment_envelope(self._records())
        self.assertAlmostEqual(envelope["random_vibration_grms"], 14.0)
        self.assertAlmostEqual(envelope["shock_g"], 1500.0)

    def test_envelope_spans_ambient_to_orbital_pressure(self):
        envelope = environment_envelope(self._records())
        self.assertAlmostEqual(envelope["pressure_pa"][1], AMBIENT_PRESSURE_PA)

    def test_empty_phase_list_rejected_by_envelope(self):
        with self.assertRaises(ValueError):
            environment_envelope([])

    def test_duty_sums_hours_and_cycles(self):
        duty = cumulative_duty(self._records())
        self.assertAlmostEqual(duty["duration_hours"], 53111.0)
        self.assertAlmostEqual(duty["cycles"], 32020.0)

    def test_duty_rejects_a_record_without_a_duration(self):
        with self.assertRaises(ValueError):
            cumulative_duty([{"name": "orbit", "cycles": 10.0}])


class PhaseGradingTests(unittest.TestCase):
    def test_enclosed_phase_is_clean(self):
        record = normalise_phase("orbit", PHASES["orbit"])
        self.assertTrue(grade_phase(record, CAPABILITY)["compliant"])

    def test_cold_overhang_is_flagged(self):
        env = dict(PHASES["orbit"])
        env["temperature_c"] = (-90.0, 90.0)
        record = normalise_phase("orbit", env)
        result = grade_phase(record, CAPABILITY)
        self.assertFalse(result["compliant"])
        self.assertIn("temperature range", result["findings"][0])

    def test_launch_vibration_over_capability_is_flagged(self):
        env = dict(PHASES["launch"])
        env["random_vibration_grms"] = 20.0
        record = normalise_phase("launch", env)
        result = grade_phase(record, CAPABILITY)
        self.assertFalse(result["compliant"])

    def test_level_exactly_on_the_capability_passes(self):
        env = dict(PHASES["launch"])
        env["random_vibration_grms"] = 16.0
        record = normalise_phase("launch", env)
        self.assertTrue(grade_phase(record, CAPABILITY)["compliant"])

    def test_humidity_without_a_rated_capability_is_flagged(self):
        capability = dict(CAPABILITY)
        del capability["humidity_max_pct"]
        record = normalise_phase("storage", PHASES["storage"])
        result = grade_phase(record, capability)
        self.assertFalse(result["compliant"])
        self.assertIn("no humidity rating", result["findings"][0])

    def test_missing_capability_key_rejected(self):
        capability = dict(CAPABILITY)
        del capability["shock_g"]
        record = normalise_phase("orbit", PHASES["orbit"])
        with self.assertRaises(ValueError):
            grade_phase(record, capability)


class AssessmentTests(unittest.TestCase):
    def test_complete_design_is_compliant(self):
        result = assess_general_design(_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_absent_phase_is_a_coverage_finding(self):
        spec = _spec()
        del spec["phases"]["storage"]
        result = assess_general_design(spec)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["missing_phases"], ("storage",))

    def test_thermal_vacuum_demonstration_missing_is_flagged(self):
        result = assess_general_design(_spec(operating_modes=["ground-ambient"]))
        self.assertFalse(result["compliant"])
        self.assertEqual(result["missing_operating_modes"], ("thermal-vacuum",))

    def test_ground_test_cycles_can_exhaust_the_qualified_life(self):
        result = assess_general_design(_spec(qualified_life_cycles=31000.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("actuation count" in text for text in result["findings"]))

    def test_life_exactly_equal_to_the_duty_is_compliant(self):
        result = assess_general_design(
            _spec(qualified_life_hours=53111.0, qualified_life_cycles=32020.0)
        )
        self.assertTrue(result["compliant"])

    def test_envelope_is_reported_alongside_the_findings(self):
        result = assess_general_design(_spec())
        self.assertAlmostEqual(result["envelope"]["temperature_c"][1], 90.0)

    def test_empty_phase_mapping_rejected(self):
        with self.assertRaises(ValueError):
            assess_general_design(_spec(phases={}))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["capability"]
        with self.assertRaises(ValueError):
            assess_general_design(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_general_design(["phases"])

    def test_margin_tolerance_is_representation_sized(self):
        self.assertLess(MARGIN_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
