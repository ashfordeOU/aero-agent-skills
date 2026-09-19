"""Contract test for the e3311 expanding tube devices leaf (unittest)."""

import unittest

from e3311_expanding_tube_devices_logic import (
    DEFAULT_EXPANDING_TUBE_POLICY,
    VERDICT_MET,
    VERDICT_NOT_MET,
    assess_expanding_tube_device,
    assess_expanding_tube_devices,
    containment_verdict,
    core_load_verdict,
    core_load_window_g_per_m,
    debris_verdict,
    delivered_force_kn,
    expansion_stroke_mm,
    internal_pressure_mpa,
    ligament_verdict,
    ligament_window_mm,
    meeting_point_m,
    severance_time_s,
    severance_timing_verdict,
    validate_device,
    validate_expanding_tube_policy,
)


def device(did="ETD-1", **kw):
    record = {
        "id": did,
        "core_load_g_per_m": 5.00,
        "expansion_coefficient_mm_per_g_per_m": 0.40,
        "required_stroke_mm": 1.20,
        "pressure_coefficient_mpa_per_g_per_m": 40.0,
        "tube_burst_pressure_mpa": 500.0,
        "force_coefficient_kn_per_g_per_m": 3.00,
        "severance_coefficient_kn_per_mm": 8.00,
        "ligament_thickness_mm": 1.00,
        "ligament_strength_kn_per_mm": 20.0,
        "limit_load_kn": 12.0,
        "joint_length_m": 2.00,
        "detonation_velocity_m_s": 7000.0,
        "end_a_delay_s": 0.0,
        "end_b_delay_s": 0.0,
        "max_severance_time_s": 3.0e-4,
        "debris_contained": True,
    }
    record.update(kw)
    return record


class TestPolicyValidation(unittest.TestCase):
    def test_default_policy_is_valid(self):
        self.assertIs(
            validate_expanding_tube_policy(DEFAULT_EXPANDING_TUBE_POLICY),
            DEFAULT_EXPANDING_TUBE_POLICY,
        )

    def test_a_non_mapping_policy_raises(self):
        with self.assertRaises(ValueError):
            validate_expanding_tube_policy(2.0)

    def test_a_containment_margin_below_unity_raises(self):
        with self.assertRaises(ValueError):
            validate_expanding_tube_policy(
                dict(DEFAULT_EXPANDING_TUBE_POLICY, min_containment_margin=0.5)
            )

    def test_a_missing_structural_margin_raises(self):
        bad = dict(DEFAULT_EXPANDING_TUBE_POLICY)
        del bad["min_structural_margin"]
        with self.assertRaises(ValueError):
            validate_expanding_tube_policy(bad)


class TestRecordValidation(unittest.TestCase):
    def test_a_valid_device_normalizes(self):
        record = validate_device(device())
        self.assertAlmostEqual(record["core_load_g_per_m"], 5.0, places=9)

    def test_a_zero_core_load_raises(self):
        with self.assertRaises(ValueError):
            validate_device(device(core_load_g_per_m=0.0))

    def test_a_negative_end_delay_raises(self):
        with self.assertRaises(ValueError):
            validate_device(device(end_b_delay_s=-1.0e-4))

    def test_a_non_boolean_debris_declaration_raises(self):
        with self.assertRaises(ValueError):
            validate_device(device(debris_contained="contained"))

    def test_an_empty_device_id_raises(self):
        with self.assertRaises(ValueError):
            validate_device(device(id="  "))

    def test_a_zero_detonation_velocity_raises(self):
        with self.assertRaises(ValueError):
            validate_device(device(detonation_velocity_m_s=0.0))


class TestResponseModel(unittest.TestCase):
    def test_stroke_is_core_load_times_the_expansion_coefficient(self):
        self.assertAlmostEqual(expansion_stroke_mm(device()), 2.00, places=9)

    def test_internal_pressure_is_core_load_times_its_coefficient(self):
        self.assertAlmostEqual(internal_pressure_mpa(device()), 200.0, places=9)

    def test_delivered_force_is_core_load_times_its_coefficient(self):
        self.assertAlmostEqual(delivered_force_kn(device()), 15.0, places=9)


class TestCoreLoadWindow(unittest.TestCase):
    def test_the_window_is_bounded_by_stroke_and_containment(self):
        window = core_load_window_g_per_m(device())
        self.assertAlmostEqual(window["low_g_per_m"], 3.75, places=9)
        self.assertAlmostEqual(window["high_g_per_m"], 6.25, places=9)
        self.assertFalse(window["empty"])

    def test_a_load_inside_the_window_passes(self):
        self.assertTrue(core_load_verdict(device())["compliant"])

    def test_a_load_exactly_on_the_lower_bound_passes(self):
        self.assertTrue(core_load_verdict(device(core_load_g_per_m=3.75))["compliant"])

    def test_a_load_exactly_on_the_upper_bound_passes(self):
        self.assertTrue(core_load_verdict(device(core_load_g_per_m=6.25))["compliant"])

    def test_too_little_core_load_fails_to_fracture(self):
        verdict = core_load_verdict(device(core_load_g_per_m=2.00))
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("fracture the ligament" in f for f in verdict["findings"]))

    def test_too_much_core_load_fails_containment(self):
        verdict = core_load_verdict(device(core_load_g_per_m=9.00))
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("can contain" in f for f in verdict["findings"]))

    def test_an_empty_core_load_window_is_reported_as_such(self):
        verdict = core_load_verdict(device(tube_burst_pressure_mpa=120.0))
        self.assertTrue(verdict["window"]["empty"])
        self.assertFalse(verdict["compliant"])
        self.assertTrue(
            any("no admissible core load" in f for f in verdict["findings"])
        )


class TestLigamentWindow(unittest.TestCase):
    def test_the_window_is_bounded_by_flight_load_and_severance(self):
        window = ligament_window_mm(device())
        self.assertAlmostEqual(window["low_mm"], 0.84, places=9)
        self.assertAlmostEqual(window["high_mm"], 1.25, places=9)
        self.assertFalse(window["empty"])

    def test_a_thickness_inside_the_window_passes(self):
        self.assertTrue(ligament_verdict(device())["compliant"])

    def test_a_thickness_exactly_on_the_severance_bound_passes(self):
        self.assertTrue(
            ligament_verdict(device(ligament_thickness_mm=1.25))["compliant"]
        )

    def test_too_thin_a_ligament_fails_the_flight_load(self):
        verdict = ligament_verdict(device(ligament_thickness_mm=0.50))
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("flight load" in f for f in verdict["findings"]))

    def test_too_thick_a_ligament_will_not_sever(self):
        verdict = ligament_verdict(device(ligament_thickness_mm=2.00))
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("will sever" in f for f in verdict["findings"]))

    def test_an_empty_ligament_window_is_reported_as_such(self):
        verdict = ligament_verdict(device(limit_load_kn=30.0))
        self.assertTrue(verdict["window"]["empty"])
        self.assertTrue(
            any("no admissible ligament" in f for f in verdict["findings"])
        )


class TestContainmentAndDebris(unittest.TestCase):
    def test_a_strong_tube_clears_the_containment_margin(self):
        verdict = containment_verdict(device())
        self.assertTrue(verdict["compliant"])
        self.assertAlmostEqual(verdict["containment_margin"], 2.5, places=9)

    def test_a_margin_landing_exactly_on_the_requirement_passes(self):
        verdict = containment_verdict(device(tube_burst_pressure_mpa=400.0))
        self.assertAlmostEqual(verdict["containment_margin"], 2.0, places=9)
        self.assertTrue(verdict["compliant"])

    def test_a_thin_tube_fails_containment(self):
        verdict = containment_verdict(device(tube_burst_pressure_mpa=260.0))
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("bursts at" in f for f in verdict["findings"]))

    def test_a_missing_debris_verification_fails(self):
        self.assertFalse(debris_verdict(device(debris_contained=False))["compliant"])

    def test_a_recorded_debris_verification_passes(self):
        self.assertTrue(debris_verdict(device())["compliant"])


class TestSeveranceTiming(unittest.TestCase):
    def test_simultaneous_ends_meet_at_the_centre(self):
        self.assertAlmostEqual(meeting_point_m(device()), 1.00, places=12)

    def test_severance_time_is_the_run_to_the_meeting_point(self):
        self.assertAlmostEqual(
            severance_time_s(device()), 1.00 / 7000.0, places=12
        )

    def test_a_delayed_end_moves_the_meeting_point_toward_it(self):
        moved = meeting_point_m(device(end_b_delay_s=1.0e-4))
        self.assertGreater(moved, 1.00)
        self.assertAlmostEqual(moved, 0.5 * (2.0 + 7000.0 * 1.0e-4), places=12)

    def test_a_badly_delayed_end_clamps_to_the_far_end(self):
        self.assertAlmostEqual(
            meeting_point_m(device(end_b_delay_s=1.0)), 2.00, places=12
        )

    def test_a_single_end_run_takes_the_whole_joint_length(self):
        self.assertAlmostEqual(
            severance_time_s(device(end_b_delay_s=1.0)), 2.00 / 7000.0, places=12
        )

    def test_a_timely_joint_passes(self):
        self.assertTrue(severance_timing_verdict(device())["compliant"])

    def test_a_slow_joint_fails(self):
        verdict = severance_timing_verdict(
            device(detonation_velocity_m_s=200.0)
        )
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("last point" in f for f in verdict["findings"]))


class TestAssessment(unittest.TestCase):
    def test_a_sound_device_meets_the_clause(self):
        report = assess_expanding_tube_device(device())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["findings"], [])

    def test_a_failing_device_names_every_failed_gate(self):
        report = assess_expanding_tube_device(
            device(core_load_g_per_m=9.00, debris_contained=False)
        )
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)
        self.assertIn("core-load", report["failed_gates"])
        self.assertIn("containment", report["failed_gates"])
        self.assertIn("debris", report["failed_gates"])

    def test_a_set_of_sound_devices_is_accepted(self):
        report = assess_expanding_tube_devices([device("ETD-1"), device("ETD-2")])
        self.assertTrue(report["compliant"])
        self.assertEqual(sorted(report["accepted"]), ["ETD-1", "ETD-2"])

    def test_duplicate_device_ids_raise_from_the_set(self):
        with self.assertRaises(ValueError):
            assess_expanding_tube_devices([device("ETD-1"), device("ETD-1")])

    def test_one_bad_device_fails_the_set(self):
        report = assess_expanding_tube_devices(
            [device("ETD-1"), device("ETD-2", ligament_thickness_mm=3.0)]
        )
        self.assertEqual(report["rejected"], ["ETD-2"])
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)

    def test_an_empty_device_set_raises(self):
        with self.assertRaises(ValueError):
            assess_expanding_tube_devices([])


if __name__ == "__main__":
    unittest.main()
