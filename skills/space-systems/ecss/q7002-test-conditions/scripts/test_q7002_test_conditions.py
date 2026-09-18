"""Contract tests for the outgassing test-condition set logic.

The cases work across a run sheet: the three set points graded against their
own bands, the pressure ceiling that is satisfied by being low enough, the
per-parameter justification a departure owes, and the chamber time the whole
sequence needs before the soak can be held for its full length.
"""

import unittest

from q7002_test_conditions_logic import (
    JUSTIFIABLE_PARAMETERS,
    REFERENCE_COLLECTOR_TEMPERATURE_C,
    REFERENCE_DURATION_H,
    REFERENCE_PRESSURE_CEILING_PA,
    REFERENCE_SPECIMEN_TEMPERATURE_C,
    REFERENCE_SPECIMEN_TOLERANCE_C,
    assess_test_conditions,
    deviation,
    justification_findings,
    pressure_finding,
    required_window_h,
    setpoint_finding,
    window_findings,
    within_tolerance,
)


def _justification(**overrides):
    entry = {"rationale": "application temperature is lower", "approval_reference": "NCR-114"}
    entry.update(overrides)
    return entry


class DeviationTests(unittest.TestCase):
    def test_deviation_is_signed(self):
        self.assertAlmostEqual(deviation(130.0, 125.0), 5.0)
        self.assertAlmostEqual(deviation(120.0, 125.0), -5.0)

    def test_zero_deviation_at_the_reference(self):
        self.assertAlmostEqual(deviation(125.0, 125.0), 0.0)

    def test_non_numeric_declared_rejected(self):
        with self.assertRaises(ValueError):
            deviation("125", 125.0)

    def test_boolean_declared_rejected(self):
        with self.assertRaises(ValueError):
            deviation(True, 125.0)


class ToleranceTests(unittest.TestCase):
    def test_value_inside_the_band(self):
        self.assertTrue(within_tolerance(125.4, 125.0, 1.0))

    def test_band_edge_is_inclusive(self):
        edge = REFERENCE_SPECIMEN_TEMPERATURE_C + REFERENCE_SPECIMEN_TOLERANCE_C
        self.assertAlmostEqual(
            deviation(edge, REFERENCE_SPECIMEN_TEMPERATURE_C),
            REFERENCE_SPECIMEN_TOLERANCE_C,
            places=9,
        )
        self.assertTrue(
            within_tolerance(edge, REFERENCE_SPECIMEN_TEMPERATURE_C,
                             REFERENCE_SPECIMEN_TOLERANCE_C)
        )

    def test_value_outside_the_band(self):
        self.assertFalse(within_tolerance(127.0, 125.0, 1.0))

    def test_zero_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            within_tolerance(125.0, 125.0, 0.0)


class SetpointFindingTests(unittest.TestCase):
    def test_in_band_setpoint_is_silent(self):
        self.assertIsNone(setpoint_finding("specimen temperature", 125.0, 125.0, 1.0, "C"))

    def test_departed_setpoint_names_the_deviation(self):
        note = setpoint_finding("specimen temperature", 100.0, 125.0, 1.0, "C")
        self.assertIn("-25", note)

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            setpoint_finding("  ", 125.0, 125.0, 1.0, "C")

    def test_blank_unit_rejected(self):
        with self.assertRaises(ValueError):
            setpoint_finding("specimen temperature", 125.0, 125.0, 1.0, " ")


class PressureTests(unittest.TestCase):
    def test_deep_vacuum_satisfies_the_ceiling(self):
        self.assertIsNone(pressure_finding(1.0e-6))

    def test_exactly_the_ceiling_is_accepted(self):
        self.assertIsNone(pressure_finding(REFERENCE_PRESSURE_CEILING_PA))

    def test_above_the_ceiling_is_flagged(self):
        note = pressure_finding(1.0e-2)
        self.assertIn("above", note)

    def test_zero_pressure_rejected(self):
        with self.assertRaises(ValueError):
            pressure_finding(0.0)

    def test_ceiling_can_be_overridden(self):
        self.assertIsNone(pressure_finding(1.0e-3, 1.0e-2))


class JustificationTests(unittest.TestCase):
    def test_no_departure_needs_no_justification(self):
        self.assertEqual(justification_findings([], None), [])

    def test_departure_without_justification_is_flagged(self):
        notes = justification_findings(["specimen_temperature_c"], None)
        self.assertEqual(len(notes), 1)
        self.assertIn("no justification", notes[0])

    def test_complete_justification_clears_the_departure(self):
        notes = justification_findings(
            ["specimen_temperature_c"], {"specimen_temperature_c": _justification()}
        )
        self.assertEqual(notes, [])

    def test_missing_approval_reference_is_flagged(self):
        notes = justification_findings(
            ["duration_h"], {"duration_h": _justification(approval_reference="  ")}
        )
        self.assertEqual(len(notes), 1)
        self.assertIn("approval reference", notes[0])

    def test_blank_rationale_is_flagged(self):
        notes = justification_findings(
            ["duration_h"], {"duration_h": _justification(rationale="")}
        )
        self.assertIn("rationale", notes[0])

    def test_justification_for_another_parameter_does_not_cover_this_one(self):
        notes = justification_findings(
            ["specimen_temperature_c"], {"duration_h": _justification()}
        )
        self.assertEqual(len(notes), 1)

    def test_unknown_parameter_rejected(self):
        with self.assertRaises(ValueError):
            justification_findings(["chamber_colour"], None)

    def test_non_mapping_justification_rejected(self):
        with self.assertRaises(ValueError):
            justification_findings(["duration_h"], {"duration_h": "approved"})

    def test_every_condition_parameter_is_justifiable(self):
        self.assertEqual(len(JUSTIFIABLE_PARAMETERS), 4)


class WindowTests(unittest.TestCase):
    def test_required_window_is_the_sum_of_the_phases(self):
        self.assertAlmostEqual(required_window_h(3.0, 1.0, 24.0, 2.0), 30.0)

    def test_zero_cooldown_is_allowed(self):
        self.assertAlmostEqual(required_window_h(3.0, 1.0, 24.0, 0.0), 28.0)

    def test_zero_duration_rejected(self):
        with self.assertRaises(ValueError):
            required_window_h(3.0, 1.0, 0.0, 2.0)

    def test_negative_pumpdown_rejected(self):
        with self.assertRaises(ValueError):
            required_window_h(-3.0, 1.0, 24.0, 2.0)

    def test_generous_booking_is_silent(self):
        self.assertEqual(window_findings(36.0, 30.0), [])

    def test_exact_booking_is_accepted(self):
        self.assertEqual(window_findings(30.0, 30.0), [])

    def test_short_booking_is_flagged(self):
        notes = window_findings(26.0, 30.0)
        self.assertEqual(len(notes), 1)
        self.assertIn("short of", notes[0])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "specimen_temperature_c": REFERENCE_SPECIMEN_TEMPERATURE_C,
            "collector_temperature_c": REFERENCE_COLLECTOR_TEMPERATURE_C,
            "duration_h": REFERENCE_DURATION_H,
            "pressure_pa": 1.0e-5,
        }
        spec.update(overrides)
        return spec

    def test_screening_point_is_accepted(self):
        result = assess_test_conditions(self._spec())
        self.assertTrue(result["at_screening_point"])
        self.assertTrue(result["conditions_accepted"])
        self.assertEqual(result["findings"], [])

    def test_deviations_are_reported_for_every_setpoint(self):
        result = assess_test_conditions(self._spec())
        self.assertEqual(
            sorted(result["deviations"]),
            ["collector_temperature_c", "duration_h", "specimen_temperature_c"],
        )

    def test_lower_temperature_departs_and_is_unjustified(self):
        result = assess_test_conditions(self._spec(specimen_temperature_c=80.0))
        self.assertFalse(result["at_screening_point"])
        self.assertFalse(result["conditions_accepted"])
        self.assertEqual(result["departed_parameters"], ["specimen_temperature_c"])

    def test_justified_departure_is_accepted(self):
        result = assess_test_conditions(
            self._spec(
                specimen_temperature_c=80.0,
                justifications={"specimen_temperature_c": _justification()},
            )
        )
        self.assertFalse(result["at_screening_point"])
        self.assertTrue(result["conditions_accepted"])

    def test_short_soak_is_a_departure(self):
        result = assess_test_conditions(self._spec(duration_h=6.0))
        self.assertIn("duration_h", result["departed_parameters"])

    def test_soft_vacuum_is_a_departure(self):
        result = assess_test_conditions(self._spec(pressure_pa=1.0e-2))
        self.assertIn("pressure_pa", result["departed_parameters"])

    def test_headroom_is_reported_when_a_window_is_booked(self):
        result = assess_test_conditions(
            self._spec(booked_window_h=32.0, pumpdown_h=3.0, stabilisation_h=1.0,
                       cooldown_h=2.0)
        )
        self.assertAlmostEqual(result["required_window_h"], 30.0)
        self.assertAlmostEqual(result["window_headroom_h"], 2.0)

    def test_short_booking_makes_the_conditions_unacceptable(self):
        result = assess_test_conditions(
            self._spec(booked_window_h=25.0, pumpdown_h=3.0, stabilisation_h=1.0,
                       cooldown_h=2.0)
        )
        self.assertFalse(result["conditions_accepted"])

    def test_window_is_absent_when_nothing_is_booked(self):
        result = assess_test_conditions(self._spec())
        self.assertIsNone(result["required_window_h"])
        self.assertIsNone(result["window_headroom_h"])

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["pressure_pa"]
        with self.assertRaises(ValueError):
            assess_test_conditions(spec)

    def test_non_positive_duration_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_conditions(self._spec(duration_h=0.0))

    def test_departure_note_describes_the_setpoint(self):
        result = assess_test_conditions(self._spec(specimen_temperature_c=80.0))
        self.assertEqual(len(result["departure_notes"]), 1)
        self.assertIn("specimen temperature", result["departure_notes"][0])

    def test_a_justified_departure_keeps_its_note(self):
        result = assess_test_conditions(
            self._spec(
                specimen_temperature_c=80.0,
                justifications={"specimen_temperature_c": _justification()},
            )
        )
        self.assertEqual(len(result["departure_notes"]), 1)
        self.assertEqual(result["findings"], [])

    def test_screening_point_run_has_no_departure_notes(self):
        result = assess_test_conditions(self._spec())
        self.assertEqual(result["departure_notes"], [])

    def test_reference_point_can_be_overridden_for_an_alternative_method(self):
        result = assess_test_conditions(
            self._spec(specimen_temperature_c=80.0, reference_specimen_temperature_c=80.0)
        )
        self.assertTrue(result["at_screening_point"])


if __name__ == "__main__":
    unittest.main()
