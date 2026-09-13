"""Contract tests for the clause 5.5.1.4.2 humidity-test general-provisions logic."""

import unittest

from e2008_humidity_test_general_provisions_logic import (
    DEFAULT_OVER_TEST_FACTOR,
    MAX_RELATIVE_HUMIDITY_PCT,
    assess_general_provisions,
    capture_precedes_test,
    envelopes_requirement,
    mission_envelope,
    missing_parameters,
    parameter_comparison,
    required_declaration,
    validate_iso_date,
    validate_mission_phase,
    validate_positive,
)

# Representative ground phases of a photovoltaic assembly between panel
# integration and lift-off: warehouse storage, road transport, launch-site
# stand-by. The launch site drives both humidity and temperature.
PHASES = [
    {"phase": "warehouse-storage", "relative_humidity_pct": 60.0,
     "air_temperature_c": 25.0, "exposure_duration_h": 500.0},
    {"phase": "road-transport", "relative_humidity_pct": 75.0,
     "air_temperature_c": 30.0, "exposure_duration_h": 100.0},
    {"phase": "launch-site-standby", "relative_humidity_pct": 85.0,
     "air_temperature_c": 32.0, "exposure_duration_h": 200.0},
]


def _declaration(**overrides):
    values = {
        "relative_humidity_pct": 85.0,
        "air_temperature_c": 35.0,
        "exposure_duration_h": 1200.0,
    }
    values.update(overrides)
    return values


def _spec(**overrides):
    spec = {
        "drawing_revision": "PVA-1042 rev C",
        "revision_date": "2026-03-02",
        "test_start_date": "2026-04-15",
        "declaration": _declaration(),
        "mission_phases": PHASES,
    }
    spec.update(overrides)
    return spec


class ValidationHelperTests(unittest.TestCase):
    def test_iso_date_parses_a_calendar_date(self):
        self.assertEqual(validate_iso_date("2026-04-15", "d").month, 4)

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            validate_iso_date("15-04-2026", "d")

    def test_non_string_date_rejected(self):
        with self.assertRaises(ValueError):
            validate_iso_date(20260415, "d")

    def test_zero_rejected_by_default(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "duration")

    def test_zero_allowed_when_permitted(self):
        self.assertAlmostEqual(validate_positive(0.0, "gap", allow_zero=True), 0.0)

    def test_boolean_rejected_as_a_number(self):
        with self.assertRaises(ValueError):
            validate_positive(True, "duration")


class MissionPhaseTests(unittest.TestCase):
    def test_phase_name_is_trimmed(self):
        phase = validate_mission_phase(dict(PHASES[0], phase="  road-transport  "))
        self.assertEqual(phase["phase"], "road-transport")

    def test_phase_missing_a_parameter_rejected(self):
        broken = dict(PHASES[0])
        del broken["exposure_duration_h"]
        with self.assertRaises(ValueError):
            validate_mission_phase(broken)

    def test_humidity_above_saturation_rejected(self):
        with self.assertRaises(ValueError):
            validate_mission_phase(dict(PHASES[0], relative_humidity_pct=140.0))

    def test_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_mission_phase(dict(PHASES[0], air_temperature_c=-400.0))

    def test_sub_zero_storage_temperature_accepted(self):
        phase = validate_mission_phase(dict(PHASES[0], air_temperature_c=-20.0))
        self.assertAlmostEqual(phase["air_temperature_c"], -20.0)

    def test_non_mapping_phase_rejected(self):
        with self.assertRaises(ValueError):
            validate_mission_phase(["road-transport"])

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_mission_phase(dict(PHASES[0], exposure_duration_h=-5.0))


class MissionEnvelopeTests(unittest.TestCase):
    def test_envelope_keeps_the_worst_humidity(self):
        self.assertAlmostEqual(mission_envelope(PHASES)["relative_humidity_pct"], 85.0)

    def test_envelope_keeps_the_worst_temperature(self):
        self.assertAlmostEqual(mission_envelope(PHASES)["air_temperature_c"], 32.0)

    def test_envelope_accumulates_the_durations(self):
        self.assertAlmostEqual(mission_envelope(PHASES)["exposure_duration_h"], 800.0)

    def test_envelope_names_the_driving_phase(self):
        self.assertEqual(mission_envelope(PHASES)["driving_phase"], "launch-site-standby")

    def test_empty_phase_list_rejected(self):
        with self.assertRaises(ValueError):
            mission_envelope([])

    def test_duplicate_phase_names_rejected(self):
        with self.assertRaises(ValueError):
            mission_envelope([PHASES[0], dict(PHASES[1], phase="warehouse-storage")])


class RequiredDeclarationTests(unittest.TestCase):
    def test_duration_carries_the_default_schedule_margin(self):
        required = required_declaration(mission_envelope(PHASES))
        self.assertAlmostEqual(required["exposure_duration_h"], 1200.0)

    def test_humidity_is_capped_at_saturation(self):
        required = required_declaration(
            mission_envelope(PHASES), {"relative_humidity_pct": 1.4}
        )
        self.assertAlmostEqual(
            required["relative_humidity_pct"], MAX_RELATIVE_HUMIDITY_PCT, places=9
        )

    def test_custom_duration_margin_is_applied(self):
        required = required_declaration(
            mission_envelope(PHASES), {"exposure_duration_h": 2.0}
        )
        self.assertAlmostEqual(required["exposure_duration_h"], 1600.0)

    def test_margin_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            required_declaration(mission_envelope(PHASES), {"exposure_duration_h": 0.8})

    def test_unknown_margin_parameter_rejected(self):
        with self.assertRaises(ValueError):
            required_declaration(mission_envelope(PHASES), {"chamber_pressure_kpa": 1.1})

    def test_envelope_missing_a_parameter_rejected(self):
        with self.assertRaises(ValueError):
            required_declaration({"relative_humidity_pct": 85.0})


class EnvelopeComparisonTests(unittest.TestCase):
    def test_equal_value_envelopes_the_requirement(self):
        self.assertAlmostEqual(1200.0, 800.0 * 1.5, places=9)
        self.assertTrue(envelopes_requirement(1200.0, 800.0 * 1.5))

    def test_unrounded_product_is_still_enveloped(self):
        # 800 * 1.1 is not representable exactly; a drawing that declares the
        # round 880 h must still count as covering it.
        self.assertAlmostEqual(880.0, 800.0 * 1.1, places=9)
        self.assertTrue(envelopes_requirement(880.0, 800.0 * 1.1))

    def test_real_shortfall_is_not_enveloped(self):
        self.assertFalse(envelopes_requirement(900.0, 1200.0))

    def test_non_numeric_declared_value_rejected(self):
        with self.assertRaises(ValueError):
            envelopes_requirement("1200", 1200.0)


class ParameterComparisonTests(unittest.TestCase):
    def _required(self):
        return required_declaration(mission_envelope(PHASES))

    def test_every_declared_parameter_is_compared(self):
        rows = parameter_comparison(_declaration(), self._required())
        self.assertEqual(len(rows), 3)

    def test_absent_parameter_is_not_compared(self):
        declaration = _declaration()
        del declaration["air_temperature_c"]
        rows = parameter_comparison(declaration, self._required())
        self.assertEqual([r["parameter"] for r in rows],
                         ["relative_humidity_pct", "exposure_duration_h"])

    def test_shortfall_is_marked_uncovered(self):
        rows = parameter_comparison(
            _declaration(exposure_duration_h=600.0), self._required()
        )
        row = [r for r in rows if r["parameter"] == "exposure_duration_h"][0]
        self.assertFalse(row["covered"])

    def test_gross_over_declaration_is_flagged(self):
        rows = parameter_comparison(
            _declaration(exposure_duration_h=5000.0), self._required()
        )
        row = [r for r in rows if r["parameter"] == "exposure_duration_h"][0]
        self.assertTrue(row["covered"])
        self.assertTrue(row["over_declared"])

    def test_declaration_exactly_at_the_over_test_ceiling_is_accepted(self):
        required = self._required()
        ceiling = required["exposure_duration_h"] * DEFAULT_OVER_TEST_FACTOR
        rows = parameter_comparison(_declaration(exposure_duration_h=ceiling), required)
        row = [r for r in rows if r["parameter"] == "exposure_duration_h"][0]
        self.assertAlmostEqual(row["declared"], ceiling, places=9)
        self.assertFalse(row["over_declared"])

    def test_over_test_factor_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            parameter_comparison(_declaration(), self._required(), 0.5)

    def test_non_numeric_declared_parameter_rejected(self):
        with self.assertRaises(ValueError):
            parameter_comparison(
                _declaration(relative_humidity_pct="85"), self._required()
            )


class MissingParameterTests(unittest.TestCase):
    def test_complete_declaration_has_no_omissions(self):
        self.assertEqual(missing_parameters(_declaration()), [])

    def test_none_counts_as_an_omission(self):
        self.assertEqual(
            missing_parameters(_declaration(exposure_duration_h=None)),
            ["exposure_duration_h"],
        )

    def test_non_mapping_declaration_rejected(self):
        with self.assertRaises(ValueError):
            missing_parameters(["relative_humidity_pct"])


class CaptureOrderTests(unittest.TestCase):
    def test_revision_issued_before_the_test_precedes_it(self):
        self.assertTrue(capture_precedes_test("2026-03-02", "2026-04-15"))

    def test_same_day_capture_is_accepted(self):
        self.assertTrue(capture_precedes_test("2026-04-15", "2026-04-15"))

    def test_revision_issued_after_the_test_start_does_not(self):
        self.assertFalse(capture_precedes_test("2026-04-16", "2026-04-15"))


class AssessmentTests(unittest.TestCase):
    def test_complete_declaration_is_ready_to_test(self):
        result = assess_general_provisions(_spec())
        self.assertTrue(result["ready_to_test"])
        self.assertEqual(result["findings"], [])

    def test_envelope_is_reported_back(self):
        result = assess_general_provisions(_spec())
        self.assertAlmostEqual(result["mission_envelope"]["exposure_duration_h"], 800.0)

    def test_omitted_parameter_is_a_finding(self):
        declaration = _declaration()
        del declaration["relative_humidity_pct"]
        result = assess_general_provisions(_spec(declaration=declaration))
        self.assertFalse(result["ready_to_test"])
        self.assertIn("relative_humidity_pct", result["findings"][0])

    def test_short_duration_is_a_finding(self):
        result = assess_general_provisions(
            _spec(declaration=_declaration(exposure_duration_h=600.0))
        )
        self.assertFalse(result["ready_to_test"])
        self.assertEqual(len(result["findings"]), 1)

    def test_late_capture_is_a_finding(self):
        result = assess_general_provisions(_spec(revision_date="2026-05-01"))
        self.assertFalse(result["captured_before_test"])
        self.assertIn("before testing", result["findings"][-1])

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["mission_phases"]
        with self.assertRaises(ValueError):
            assess_general_provisions(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_general_provisions(["declaration"])

    def test_blank_drawing_revision_rejected(self):
        with self.assertRaises(ValueError):
            assess_general_provisions(_spec(drawing_revision="   "))

    def test_drawing_revision_is_trimmed_in_the_report(self):
        result = assess_general_provisions(_spec(drawing_revision=" PVA-1042 rev C "))
        self.assertEqual(result["drawing_revision"], "PVA-1042 rev C")


if __name__ == "__main__":
    unittest.main()
