"""Contract test for the acceleration-and-shock-screening leaf (stdlib unittest)."""

import math
import unittest

from q6005_acceleration_and_shock_screening_logic import (
    ACCELERATION_CONDITIONS,
    ALL_AXES,
    DRIFT_LIMIT_FRACTION,
    DURATION_TOLERANCE,
    FAIL,
    G0,
    HEAVY_PACKAGE_CONDITION,
    LOT_PERCENT_DEFECTIVE_ALLOWABLE,
    PASS,
    acceleration_level_g,
    assess_screen,
    assess_screening_lot,
    attachment_capability_mpa,
    attachment_margin,
    attachment_stress_mpa,
    axes_shortfall,
    check_acceleration,
    check_attachment_capability,
    check_outcome,
    check_shock_pulse,
    inertial_force_newton,
    level_is_saturated,
    required_axes,
    required_condition_for_mass,
    shock_condition_bounds,
    shock_velocity_change,
    validate_screen,
    worst_attachment_margin,
)


def unit(unit_id="U-1", **kw):
    record = {
        "id": unit_id,
        "package_mass_g": 8.0,
        "element_mass_g": 0.02,
        "bond_area_mm2": 6.0,
        "attach_medium": "eutectic-gold-silicon",
        "mounting_style": "flat-die-attach",
        "acceleration_applied_g": 10000.0,
        "axes_applied": ["Y1"],
        "shock_condition": "B",
        "shock_peak_g": 1500.0,
        "shock_duration_ms": 0.5,
        "post_screen_measured": True,
        "parameter_drift_fraction": 0.01,
        "loose_element_detected": False,
    }
    record.update(kw)
    return record


class TestConditionSelection(unittest.TestCase):
    def test_light_package_takes_the_highest_condition(self):
        self.assertEqual(required_condition_for_mass(0.2), "E")
        self.assertAlmostEqual(acceleration_level_g("E"), 50000.0, places=9)

    def test_band_boundary_stays_in_the_lower_band(self):
        self.assertEqual(required_condition_for_mass(2.0), "D")
        self.assertEqual(required_condition_for_mass(2.0001), "C")

    def test_heavy_package_saturates_at_the_lowest_condition(self):
        self.assertEqual(required_condition_for_mass(40.0), HEAVY_PACKAGE_CONDITION)
        self.assertTrue(level_is_saturated(40.0))
        self.assertFalse(level_is_saturated(0.2))

    def test_every_condition_is_tabulated(self):
        for name in ACCELERATION_CONDITIONS:
            self.assertGreater(acceleration_level_g(name), 0.0)

    def test_zero_mass_raises(self):
        with self.assertRaises(ValueError):
            required_condition_for_mass(0.0)

    def test_boolean_mass_raises(self):
        with self.assertRaises(ValueError):
            required_condition_for_mass(True)

    def test_infinite_mass_raises(self):
        with self.assertRaises(ValueError):
            required_condition_for_mass(float("inf"))

    def test_unknown_condition_raises(self):
        with self.assertRaises(ValueError):
            acceleration_level_g("Z")


class TestAxes(unittest.TestCase):
    def test_flat_die_attach_owes_the_normal_axis_only(self):
        self.assertEqual(required_axes("flat-die-attach"), ("Y1",))

    def test_stacked_element_owes_both_senses_of_the_normal_axis(self):
        self.assertEqual(required_axes("stacked-element"), ("Y1", "Y2"))

    def test_cantilevered_element_owes_every_axis(self):
        self.assertEqual(set(required_axes("cantilevered-element")), set(ALL_AXES))

    def test_unknown_mounting_style_raises(self):
        with self.assertRaises(ValueError):
            required_axes("glued-on-somehow")

    def test_shortfall_names_the_axes_never_run(self):
        missing = axes_shortfall(
            unit("U-1", mounting_style="stacked-element", axes_applied=["Y1"])
        )
        self.assertEqual(missing, ["Y2"])


class TestInertialLoad(unittest.TestCase):
    def test_force_is_mass_times_level(self):
        self.assertAlmostEqual(
            inertial_force_newton(0.02, 10000.0),
            (0.02 / 1000.0) * G0 * 10000.0,
            places=12,
        )

    def test_stress_is_force_over_the_bonded_area(self):
        self.assertAlmostEqual(attachment_stress_mpa(12.0, 6.0), 2.0, places=12)

    def test_margin_is_capability_over_stress(self):
        capability = attachment_capability_mpa("eutectic-gold-silicon")
        self.assertAlmostEqual(
            attachment_margin(capability / 2.0, "eutectic-gold-silicon"),
            1.0,
            places=12,
        )

    def test_stress_exactly_on_the_capability_is_zero_margin(self):
        capability = attachment_capability_mpa("polyimide-adhesive")
        self.assertAlmostEqual(
            attachment_margin(capability, "polyimide-adhesive"), 0.0, places=12
        )

    def test_unknown_attach_medium_raises(self):
        with self.assertRaises(ValueError):
            attachment_capability_mpa("chewing-gum")

    def test_zero_bond_area_raises(self):
        with self.assertRaises(ValueError):
            attachment_stress_mpa(12.0, 0.0)

    def test_negative_element_mass_raises(self):
        with self.assertRaises(ValueError):
            inertial_force_newton(-0.02, 10000.0)


class TestShockPulse(unittest.TestCase):
    def test_bounds_wrap_the_nominal_duration(self):
        peak, low, high = shock_condition_bounds("B")
        self.assertAlmostEqual(peak, 1500.0, places=9)
        self.assertAlmostEqual(low, 0.5 * (1.0 - DURATION_TOLERANCE), places=12)
        self.assertAlmostEqual(high, 0.5 * (1.0 + DURATION_TOLERANCE), places=12)

    def test_velocity_change_follows_the_half_sine_integral(self):
        self.assertAlmostEqual(
            shock_velocity_change(1500.0, 0.5),
            (2.0 / math.pi) * 1500.0 * G0 * 0.0005,
            places=12,
        )

    def test_a_shorter_pulse_at_the_same_peak_buys_less_velocity(self):
        short = shock_velocity_change(1500.0, 0.2)
        long_pulse = shock_velocity_change(1500.0, 0.5)
        self.assertLess(short, long_pulse)

    def test_unknown_shock_condition_raises(self):
        with self.assertRaises(ValueError):
            shock_condition_bounds("Q")

    def test_low_peak_is_a_finding(self):
        self.assertIn(
            "shock-peak-below-the-required-condition",
            check_shock_pulse(unit("U-1", shock_peak_g=900.0)),
        )

    def test_duration_outside_the_window_is_a_finding(self):
        self.assertIn(
            "shock-duration-outside-the-waveform-tolerance",
            check_shock_pulse(unit("U-1", shock_duration_ms=0.9)),
        )

    def test_duration_exactly_on_the_window_edge_is_accepted(self):
        _, low, _ = shock_condition_bounds("B")
        self.assertEqual(check_shock_pulse(unit("U-1", shock_duration_ms=low)), [])


class TestValidation(unittest.TestCase):
    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_screen(["U-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_screen(unit(""))

    def test_unknown_axis_raises(self):
        with self.assertRaises(ValueError):
            validate_screen(unit("U-1", axes_applied=["Y9"]))

    def test_repeated_axis_raises(self):
        with self.assertRaises(ValueError):
            validate_screen(unit("U-1", axes_applied=["Y1", "Y1"]))

    def test_non_sequence_axes_raises(self):
        with self.assertRaises(ValueError):
            validate_screen(unit("U-1", axes_applied="Y1"))

    def test_non_boolean_loose_element_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_screen(unit("U-1", loose_element_detected="maybe"))

    def test_negative_drift_raises(self):
        with self.assertRaises(ValueError):
            validate_screen(unit("U-1", parameter_drift_fraction=-0.01))


class TestAccelerationFindings(unittest.TestCase):
    def test_level_below_the_condition_is_a_finding(self):
        self.assertIn(
            "acceleration-level-below-the-required-condition",
            check_acceleration(unit("U-1", acceleration_applied_g=5000.0)),
        )

    def test_level_exactly_on_the_condition_is_accepted(self):
        owed = acceleration_level_g(required_condition_for_mass(8.0))
        self.assertAlmostEqual(owed, 10000.0, places=9)
        self.assertEqual(
            check_acceleration(unit("U-1", acceleration_applied_g=owed)), []
        )

    def test_missing_axis_is_a_finding(self):
        findings = check_acceleration(
            unit("U-1", mounting_style="cantilevered-element", axes_applied=["Y1"])
        )
        self.assertIn("required-axis-not-exercised", findings)


class TestAttachmentCapability(unittest.TestCase):
    def test_screen_stronger_than_the_attachment_is_a_finding(self):
        findings = check_attachment_capability(
            unit(
                "U-1",
                attach_medium="polyimide-adhesive",
                element_mass_g=0.4,
                bond_area_mm2=1.0,
            )
        )
        self.assertIn("screen-load-exceeds-the-attachment-capability", findings)

    def test_a_sound_attachment_carries_no_finding(self):
        self.assertEqual(check_attachment_capability(unit()), [])


class TestOutcome(unittest.TestCase):
    def test_no_post_stress_measurement_is_a_finding(self):
        self.assertIn(
            "electrical-measurement-not-repeated-after-the-stress",
            check_outcome(unit("U-1", post_screen_measured=False)),
        )

    def test_drift_above_the_limit_is_a_finding(self):
        self.assertIn(
            "post-screen-drift-above-the-limit",
            check_outcome(unit("U-1", parameter_drift_fraction=0.5)),
        )

    def test_drift_exactly_on_the_limit_is_absorbed(self):
        findings = check_outcome(
            unit("U-1", parameter_drift_fraction=DRIFT_LIMIT_FRACTION)
        )
        self.assertNotIn("post-screen-drift-above-the-limit", findings)

    def test_loose_element_evidence_is_a_finding(self):
        self.assertIn(
            "loose-element-evidence-after-screening",
            check_outcome(unit("U-1", loose_element_detected=True)),
        )


class TestAssessScreen(unittest.TestCase):
    def test_a_sound_screen_passes(self):
        result = assess_screen(unit())
        self.assertEqual(result["disposition"], PASS)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["required_condition"], "B")

    def test_any_finding_fails_the_unit(self):
        result = assess_screen(unit("U-1", loose_element_detected=True))
        self.assertEqual(result["disposition"], FAIL)

    def test_report_carries_the_computed_load(self):
        result = assess_screen(unit())
        self.assertAlmostEqual(
            result["attachment_stress_mpa"],
            inertial_force_newton(0.02, 10000.0) / 6.0,
            places=12,
        )


class TestLot(unittest.TestCase):
    def test_a_clean_lot_is_accepted(self):
        report = assess_screening_lot([unit("U-1"), unit("U-2")])
        self.assertTrue(report["lot_accepted"])
        self.assertEqual(report["failed_ids"], [])
        self.assertAlmostEqual(report["reject_fraction"], 0.0, places=12)

    def test_reject_fraction_above_the_allowable_refuses_the_lot(self):
        report = assess_screening_lot(
            [unit("U-1"), unit("U-2", loose_element_detected=True)]
        )
        self.assertFalse(report["lot_accepted"])
        self.assertEqual(report["failed_ids"], ["U-2"])

    def test_reject_fraction_exactly_on_the_allowable_is_accepted(self):
        units = [unit("U-%d" % i) for i in range(9)]
        units.append(unit("U-9", loose_element_detected=True))
        report = assess_screening_lot(units)
        self.assertAlmostEqual(
            report["reject_fraction"], LOT_PERCENT_DEFECTIVE_ALLOWABLE, places=12
        )
        self.assertTrue(report["lot_accepted"])

    def test_duplicate_unit_id_raises(self):
        with self.assertRaises(ValueError):
            assess_screening_lot([unit("U-1"), unit("U-1")])

    def test_empty_lot_raises(self):
        with self.assertRaises(ValueError):
            assess_screening_lot([])

    def test_non_list_lot_raises(self):
        with self.assertRaises(ValueError):
            assess_screening_lot(unit())

    def test_worst_margin_names_the_weakest_attachment(self):
        unit_id, margin = worst_attachment_margin(
            [unit("U-1"), unit("U-2", attach_medium="polyimide-adhesive")]
        )
        self.assertEqual(unit_id, "U-2")
        self.assertLess(margin, attachment_margin(1.0, "eutectic-gold-silicon"))


if __name__ == "__main__":
    unittest.main()
