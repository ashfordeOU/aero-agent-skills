"""Contract tests for the clause 4.7.7.6 / 4.7.7.7 protection and strain logic."""

import math
import unittest

from e3301_over_current_protection_wire_strain_logic import (
    CURRENT_TOLERANCE_A,
    DEFAULT_OPERATING_FACTOR,
    DEFAULT_WIRE_FACTOR,
    assess_overcurrent_and_strain,
    bend_radius_m,
    conductor_bending_strain,
    grade_crossing,
    grade_protection_rating,
    protection_window_a,
    service_loop_length_m,
    stall_findings,
    validate_circuit,
    validate_crossing,
    wire_capacity_a,
)


def good_circuit(**overrides):
    circuit = {
        "id": "SADM-MOTOR",
        "operating_current_a": 1.0,
        "stall_current_a": 4.0,
        "wire_rating_a": 5.0,
        "protection_rating_a": 2.5,
        "protection_trip_time_s": 0.5,
        "wire_withstand_time_s": 5.0,
        "bundle_derating": 0.8,
    }
    circuit.update(overrides)
    return circuit


def good_crossing(**overrides):
    crossing = {
        "id": "SADM-CROSSING",
        "travel_m": 0.100,
        "free_length_m": 0.200,
        "cable_diameter_m": 0.004,
        "min_bend_radius_m": 0.020,
        "wrap_angle_rad": math.pi,
        "allowable_strain": 0.05,
        "cycles_required": 20000,
        "cycles_qualified": 60000,
    }
    crossing.update(overrides)
    return crossing


class ValidateCircuitTests(unittest.TestCase):
    def test_defaults_are_applied(self):
        record = validate_circuit(good_circuit())
        self.assertAlmostEqual(record["altitude_derating"], 1.0, places=9)
        self.assertFalse(record["wire_carries_stall"])

    def test_missing_key_rejected(self):
        circuit = good_circuit()
        del circuit["wire_rating_a"]
        with self.assertRaises(ValueError):
            validate_circuit(circuit)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_circuit("SADM-MOTOR")

    def test_stall_below_operating_rejected(self):
        with self.assertRaises(ValueError):
            validate_circuit(good_circuit(stall_current_a=0.5))

    def test_zero_operating_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_circuit(good_circuit(operating_current_a=0.0))

    def test_derating_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_circuit(good_circuit(bundle_derating=1.3))

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_circuit(good_circuit(id="  "))

    def test_boolean_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_circuit(good_circuit(operating_current_a=True))


class WireCapacityTests(unittest.TestCase):
    def test_no_derating_returns_the_rating(self):
        self.assertAlmostEqual(wire_capacity_a(5.0), 5.0, places=9)

    def test_deratings_multiply(self):
        self.assertAlmostEqual(wire_capacity_a(5.0, 0.8, 0.5), 2.0, places=9)

    def test_zero_rating_rejected(self):
        with self.assertRaises(ValueError):
            wire_capacity_a(0.0)

    def test_zero_derating_rejected(self):
        with self.assertRaises(ValueError):
            wire_capacity_a(5.0, 0.0)


class ProtectionWindowTests(unittest.TestCase):
    def test_default_factors_are_the_documented_ones(self):
        self.assertAlmostEqual(DEFAULT_OPERATING_FACTOR, 1.5, places=9)
        self.assertAlmostEqual(DEFAULT_WIRE_FACTOR, 0.8, places=9)

    def test_window_bounds_follow_the_factors(self):
        low, high = protection_window_a(good_circuit())
        self.assertAlmostEqual(low, 1.5, places=9)
        self.assertAlmostEqual(high, 3.2, places=9)

    def test_operating_factor_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            protection_window_a(good_circuit(), operating_factor=0.9)

    def test_wire_factor_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            protection_window_a(good_circuit(), wire_factor=1.1)

    def test_rating_inside_the_window_is_compliant(self):
        graded = grade_protection_rating(good_circuit())
        self.assertTrue(graded["compliant"])
        self.assertEqual(graded["findings"], [])

    def test_rating_below_the_lower_bound_is_flagged(self):
        graded = grade_protection_rating(good_circuit(protection_rating_a=1.2))
        self.assertFalse(graded["compliant"])
        self.assertIn("lower bound", graded["findings"][0])

    def test_rating_above_the_wire_bound_is_flagged(self):
        graded = grade_protection_rating(good_circuit(protection_rating_a=4.0))
        self.assertFalse(graded["compliant"])
        self.assertIn("derated wire supports", graded["findings"][0])

    def test_rating_exactly_on_the_lower_bound_is_accepted(self):
        graded = grade_protection_rating(good_circuit(protection_rating_a=1.5))
        self.assertAlmostEqual(graded["rating_a"], graded["lower_bound_a"], places=9)
        self.assertTrue(graded["compliant"])

    def test_rating_exactly_on_the_upper_bound_is_accepted(self):
        graded = grade_protection_rating(good_circuit(protection_rating_a=3.2))
        self.assertAlmostEqual(graded["rating_a"], graded["upper_bound_a"], places=9)
        self.assertTrue(graded["compliant"])

    def test_crossed_bounds_report_that_no_rating_exists(self):
        circuit = good_circuit(operating_current_a=4.0, stall_current_a=8.0,
                               wire_rating_a=5.0, protection_rating_a=6.0)
        graded = grade_protection_rating(circuit)
        self.assertFalse(graded["window_exists"])
        self.assertTrue(any("no rating satisfies" in f for f in graded["findings"]))

    def test_tolerance_is_tight(self):
        self.assertLess(CURRENT_TOLERANCE_A, 1e-6)


class StallTests(unittest.TestCase):
    def test_fast_protection_is_clean(self):
        self.assertEqual(stall_findings(good_circuit()), [])

    def test_slow_protection_is_flagged(self):
        findings = stall_findings(good_circuit(protection_trip_time_s=20.0))
        self.assertEqual(len(findings), 1)
        self.assertIn("withstand time", findings[0])

    def test_stall_below_the_rating_is_never_interrupted(self):
        findings = stall_findings(good_circuit(stall_current_a=2.0, protection_rating_a=2.5))
        self.assertTrue(any("never reaches" in f for f in findings))

    def test_trip_time_exactly_at_the_withstand_time_is_accepted(self):
        self.assertEqual(
            stall_findings(good_circuit(protection_trip_time_s=5.0, wire_withstand_time_s=5.0)),
            [],
        )

    def test_wire_declared_to_carry_stall_is_graded_on_capacity(self):
        circuit = good_circuit(wire_carries_stall=True, stall_current_a=4.0,
                               wire_rating_a=5.0, bundle_derating=0.8)
        self.assertEqual(stall_findings(circuit), [])

    def test_wire_that_cannot_carry_stall_is_flagged(self):
        circuit = good_circuit(wire_carries_stall=True, stall_current_a=6.0,
                               wire_rating_a=5.0, bundle_derating=0.8)
        findings = stall_findings(circuit)
        self.assertEqual(len(findings), 1)
        self.assertIn("carry stall indefinitely", findings[0])


class StrainGeometryTests(unittest.TestCase):
    def test_service_loop_adds_the_slack(self):
        self.assertAlmostEqual(service_loop_length_m(0.100, 1.25), 0.125, places=9)

    def test_slack_factor_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            service_loop_length_m(0.100, 0.9)

    def test_zero_travel_rejected(self):
        with self.assertRaises(ValueError):
            service_loop_length_m(0.0)

    def test_bend_radius_is_length_over_angle(self):
        self.assertAlmostEqual(bend_radius_m(math.pi, math.pi), 1.0, places=9)

    def test_wrap_beyond_a_full_turn_rejected(self):
        with self.assertRaises(ValueError):
            bend_radius_m(0.2, 7.0)

    def test_strain_falls_with_radius(self):
        tight = conductor_bending_strain(0.004, 0.010)
        loose = conductor_bending_strain(0.004, 0.100)
        self.assertLess(loose, tight / 5.0)

    def test_strain_matches_the_closed_form(self):
        self.assertAlmostEqual(
            conductor_bending_strain(0.004, 0.020), 0.004 / (0.044), places=12
        )

    def test_zero_radius_rejected(self):
        with self.assertRaises(ValueError):
            conductor_bending_strain(0.004, 0.0)


class CrossingTests(unittest.TestCase):
    def test_healthy_crossing_is_compliant(self):
        graded = grade_crossing(good_crossing())
        self.assertTrue(graded["compliant"])
        self.assertEqual(graded["findings"], [])

    def test_short_free_length_is_flagged(self):
        graded = grade_crossing(good_crossing(free_length_m=0.110))
        self.assertFalse(graded["length_ok"])
        self.assertTrue(any("goes taut" in f for f in graded["findings"]))

    def test_free_length_exactly_at_the_requirement_is_accepted(self):
        graded = grade_crossing(good_crossing(travel_m=0.160, free_length_m=0.200))
        self.assertAlmostEqual(graded["required_length_m"], 0.200, places=9)
        self.assertTrue(graded["length_ok"])

    def test_tight_bend_is_flagged(self):
        graded = grade_crossing(good_crossing(min_bend_radius_m=0.200))
        self.assertFalse(graded["radius_ok"])

    def test_excess_strain_is_flagged(self):
        graded = grade_crossing(good_crossing(allowable_strain=0.01))
        self.assertFalse(graded["strain_ok"])

    def test_insufficient_flexure_qualification_is_flagged(self):
        graded = grade_crossing(good_crossing(cycles_qualified=5000))
        self.assertFalse(graded["cycles_ok"])
        self.assertTrue(any("flexure cycles" in f for f in graded["findings"]))

    def test_equal_cycles_are_accepted(self):
        graded = grade_crossing(good_crossing(cycles_qualified=20000))
        self.assertTrue(graded["cycles_ok"])

    def test_missing_crossing_key_rejected(self):
        crossing = good_crossing()
        del crossing["wrap_angle_rad"]
        with self.assertRaises(ValueError):
            validate_crossing(crossing)

    def test_fractional_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_crossing(good_crossing(cycles_required=1.5))

    def test_zero_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_crossing(good_crossing(cycles_required=0))

    def test_non_mapping_crossing_rejected(self):
        with self.assertRaises(ValueError):
            validate_crossing(["SADM-CROSSING"])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {"circuits": [good_circuit()], "crossings": [good_crossing()]}
        spec.update(overrides)
        return spec

    def test_healthy_design_reports_no_findings(self):
        result = assess_overcurrent_and_strain(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_one_record_per_circuit_and_crossing(self):
        result = assess_overcurrent_and_strain(self._spec())
        self.assertEqual(len(result["circuits"]), 1)
        self.assertEqual(len(result["crossings"]), 1)

    def test_stall_findings_reach_the_circuit_record(self):
        result = assess_overcurrent_and_strain(
            self._spec(circuits=[good_circuit(protection_trip_time_s=20.0)])
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["circuits"][0]["stall_findings"]), 1)

    def test_duplicate_circuit_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_overcurrent_and_strain(self._spec(circuits=[good_circuit(), good_circuit()]))

    def test_empty_circuit_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_overcurrent_and_strain(self._spec(circuits=[]))

    def test_no_crossings_is_allowed(self):
        result = assess_overcurrent_and_strain(self._spec(crossings=[]))
        self.assertTrue(result["compliant"])
        self.assertEqual(result["crossings"], [])

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["crossings"]
        with self.assertRaises(ValueError):
            assess_overcurrent_and_strain(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_overcurrent_and_strain(["circuits"])

    def test_factor_overrides_move_the_window(self):
        result = assess_overcurrent_and_strain(self._spec(operating_factor=3.0))
        self.assertAlmostEqual(result["circuits"][0]["lower_bound_a"], 3.0, places=9)
        self.assertFalse(result["compliant"])


if __name__ == "__main__":
    unittest.main()
