"""Contract test for the hybrid-burn-in-test leaf (stdlib unittest)."""

import math
import unittest

from q6005_hybrid_burn_in_test_logic import (
    ACTIVATION_ENERGY_EV,
    BOLTZMANN_EV_PER_K,
    DELTA_DRIFT_LIMIT,
    FAIL,
    MAX_JUNCTION_TEMP_C,
    MEASUREMENT_WINDOW_H,
    PASS,
    PERCENT_DEFECTIVE_ALLOWABLE,
    REFERENCE_DURATION_H,
    REFERENCE_STRESS_TEMP_C,
    activation_energy,
    arrhenius_acceleration_factor,
    assess_burn_in,
    assess_burn_in_lot,
    check_measurement,
    check_schedule,
    check_thermal,
    delta_drift_fraction,
    equivalence_factor,
    equivalent_reference_hours,
    junction_temperature_c,
    percent_defective_allowable,
    required_duration_h,
    schedule_options,
    to_kelvin,
    validate_burn_in,
)


def burn_in(unit_id="U-1", **kw):
    record = {
        "id": unit_id,
        "mechanism": "ionic-contamination",
        "flow_class": "class-2",
        "use_temp_c": 55.0,
        "ambient_temp_c": 125.0,
        "duration_h": 160.0,
        "dissipated_power_w": 0.8,
        "theta_ja_c_per_w": 20.0,
        "bias_applied": True,
        "measurement_delay_h": 12.0,
        "pre_reading": 100.0,
        "post_reading": 101.0,
        "reduced_duration_approved": False,
        "catastrophic_failure": False,
    }
    record.update(kw)
    return record


class TestTemperature(unittest.TestCase):
    def test_kelvin_offsets_the_celsius_reading(self):
        self.assertAlmostEqual(to_kelvin("t", 125.0), 398.15, places=9)

    def test_absolute_zero_raises(self):
        with self.assertRaises(ValueError):
            to_kelvin("t", -273.15)

    def test_boolean_temperature_raises(self):
        with self.assertRaises(ValueError):
            to_kelvin("t", True)

    def test_infinite_temperature_raises(self):
        with self.assertRaises(ValueError):
            to_kelvin("t", float("inf"))


class TestActivationEnergy(unittest.TestCase):
    def test_every_mechanism_is_tabulated(self):
        for name in ACTIVATION_ENERGY_EV:
            self.assertGreater(activation_energy(name), 0.0)

    def test_unknown_mechanism_raises(self):
        with self.assertRaises(ValueError):
            activation_energy("bad-vibes")

    def test_a_low_energy_mechanism_accelerates_less(self):
        low = arrhenius_acceleration_factor("oxide-defect", 55.0, 125.0)
        high = arrhenius_acceleration_factor("wire-bond-intermetallic", 55.0, 125.0)
        self.assertLess(low, high)


class TestArrhenius(unittest.TestCase):
    def test_factor_follows_the_arrhenius_relation(self):
        expected = math.exp(
            (0.70 / BOLTZMANN_EV_PER_K) * (1.0 / 328.15 - 1.0 / 398.15)
        )
        self.assertAlmostEqual(
            arrhenius_acceleration_factor("ionic-contamination", 55.0, 125.0),
            expected,
            places=9,
        )

    def test_equal_temperatures_accelerate_nothing(self):
        self.assertAlmostEqual(
            arrhenius_acceleration_factor("ionic-contamination", 125.0, 125.0),
            1.0,
            places=12,
        )

    def test_a_cooler_stress_decelerates(self):
        self.assertLess(
            arrhenius_acceleration_factor("ionic-contamination", 125.0, 85.0), 1.0
        )

    def test_the_reference_condition_is_its_own_equivalent(self):
        self.assertAlmostEqual(
            equivalence_factor("ionic-contamination", REFERENCE_STRESS_TEMP_C),
            1.0,
            places=12,
        )

    def test_a_hotter_exposure_buys_more_reference_hours(self):
        self.assertGreater(
            equivalent_reference_hours(48.0, "ionic-contamination", 150.0),
            equivalent_reference_hours(48.0, "ionic-contamination", 125.0),
        )

    def test_required_duration_at_the_reference_is_the_reference(self):
        self.assertAlmostEqual(
            required_duration_h("ionic-contamination", REFERENCE_STRESS_TEMP_C),
            REFERENCE_DURATION_H,
            places=9,
        )

    def test_required_duration_falls_with_temperature(self):
        self.assertLess(
            required_duration_h("ionic-contamination", 150.0),
            required_duration_h("ionic-contamination", 125.0),
        )

    def test_the_equivalence_round_trips(self):
        hours = required_duration_h("wire-bond-intermetallic", 150.0)
        self.assertAlmostEqual(
            equivalent_reference_hours(hours, "wire-bond-intermetallic", 150.0),
            REFERENCE_DURATION_H,
            places=9,
        )

    def test_schedule_options_pair_temperature_with_duration(self):
        options = schedule_options("ionic-contamination", [125.0, 150.0])
        self.assertEqual(len(options), 2)
        self.assertAlmostEqual(options[0][1], REFERENCE_DURATION_H, places=9)
        self.assertLess(options[1][1], options[0][1])

    def test_empty_schedule_request_raises(self):
        with self.assertRaises(ValueError):
            schedule_options("ionic-contamination", [])

    def test_zero_duration_raises(self):
        with self.assertRaises(ValueError):
            equivalent_reference_hours(0.0, "ionic-contamination", 125.0)


class TestJunctionTemperature(unittest.TestCase):
    def test_junction_sits_above_ambient_by_the_dissipation(self):
        self.assertAlmostEqual(
            junction_temperature_c(125.0, 0.8, 20.0), 141.0, places=9
        )

    def test_an_unpowered_part_sits_at_ambient(self):
        self.assertAlmostEqual(
            junction_temperature_c(125.0, 0.0, 20.0), 125.0, places=9
        )

    def test_negative_power_raises(self):
        with self.assertRaises(ValueError):
            junction_temperature_c(125.0, -1.0, 20.0)

    def test_negative_thermal_resistance_raises(self):
        with self.assertRaises(ValueError):
            junction_temperature_c(125.0, 0.8, -5.0)


class TestDrift(unittest.TestCase):
    def test_drift_is_the_fractional_movement(self):
        self.assertAlmostEqual(delta_drift_fraction(100.0, 105.0), 0.05, places=12)

    def test_drift_is_unsigned(self):
        self.assertAlmostEqual(
            delta_drift_fraction(100.0, 95.0),
            delta_drift_fraction(100.0, 105.0),
            places=12,
        )

    def test_a_zero_pre_reading_raises(self):
        with self.assertRaises(ValueError):
            delta_drift_fraction(0.0, 5.0)

    def test_a_non_numeric_reading_raises(self):
        with self.assertRaises(ValueError):
            delta_drift_fraction("100", 105.0)


class TestValidation(unittest.TestCase):
    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_burn_in(["U-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_burn_in(burn_in(""))

    def test_unknown_flow_class_raises(self):
        with self.assertRaises(ValueError):
            validate_burn_in(burn_in("U-1", flow_class="class-9"))

    def test_non_boolean_bias_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_burn_in(burn_in("U-1", bias_applied="on"))

    def test_negative_measurement_delay_raises(self):
        with self.assertRaises(ValueError):
            validate_burn_in(burn_in("U-1", measurement_delay_h=-1.0))

    def test_defaults_fill_the_optional_fields(self):
        norm = validate_burn_in(
            {
                "id": "U-9",
                "mechanism": "oxide-defect",
                "use_temp_c": 55.0,
                "ambient_temp_c": 125.0,
                "duration_h": 160.0,
                "theta_ja_c_per_w": 20.0,
                "pre_reading": 10.0,
                "post_reading": 10.1,
            }
        )
        self.assertEqual(norm["flow_class"], "class-2")
        self.assertTrue(norm["bias_applied"])
        self.assertFalse(norm["catastrophic_failure"])


class TestScheduleFindings(unittest.TestCase):
    def test_a_reference_schedule_carries_no_finding(self):
        self.assertEqual(check_schedule(burn_in()), [])

    def test_a_stress_at_the_use_temperature_accelerates_nothing(self):
        findings = check_schedule(burn_in("U-1", ambient_temp_c=55.0, duration_h=5000.0))
        self.assertIn(
            "stress-temperature-does-not-accelerate-the-mechanism", findings
        )

    def test_an_exposure_below_the_equivalent_duration_is_a_finding(self):
        self.assertIn(
            "exposure-below-the-reference-equivalent-duration",
            check_schedule(burn_in("U-1", duration_h=40.0)),
        )

    def test_a_shortened_hot_run_needs_an_approval(self):
        hours = required_duration_h("ionic-contamination", 150.0)
        findings = check_schedule(
            burn_in("U-1", ambient_temp_c=150.0, duration_h=hours,
                    theta_ja_c_per_w=5.0)
        )
        self.assertIn("reduced-duration-equivalence-without-an-approval", findings)

    def test_an_approved_shortened_hot_run_is_accepted(self):
        hours = required_duration_h("ionic-contamination", 150.0)
        findings = check_schedule(
            burn_in(
                "U-1",
                ambient_temp_c=150.0,
                duration_h=hours,
                reduced_duration_approved=True,
                theta_ja_c_per_w=5.0,
            )
        )
        self.assertEqual(findings, [])


class TestThermalFindings(unittest.TestCase):
    def test_a_sound_exposure_carries_no_finding(self):
        self.assertEqual(check_thermal(burn_in()), [])

    def test_an_unpowered_soak_is_a_finding(self):
        self.assertIn(
            "bias-not-applied-during-the-exposure",
            check_thermal(burn_in("U-1", bias_applied=False)),
        )

    def test_an_overheated_die_is_a_finding(self):
        self.assertIn(
            "junction-temperature-above-the-maximum-rating",
            check_thermal(burn_in("U-1", dissipated_power_w=3.0)),
        )

    def test_a_junction_exactly_on_the_rating_is_accepted(self):
        power = (MAX_JUNCTION_TEMP_C - 125.0) / 20.0
        findings = check_thermal(burn_in("U-1", dissipated_power_w=power))
        self.assertNotIn("junction-temperature-above-the-maximum-rating", findings)


class TestMeasurementFindings(unittest.TestCase):
    def test_a_prompt_reading_carries_no_finding(self):
        self.assertEqual(check_measurement(burn_in()), [])

    def test_a_late_reading_is_a_finding(self):
        self.assertIn(
            "post-exposure-measurement-outside-the-window",
            check_measurement(
                burn_in("U-1", measurement_delay_h=MEASUREMENT_WINDOW_H + 24.0)
            ),
        )

    def test_a_reading_exactly_on_the_window_is_accepted(self):
        findings = check_measurement(
            burn_in("U-1", measurement_delay_h=MEASUREMENT_WINDOW_H)
        )
        self.assertNotIn("post-exposure-measurement-outside-the-window", findings)

    def test_drift_above_the_limit_is_a_finding(self):
        self.assertIn(
            "delta-drift-above-the-limit",
            check_measurement(burn_in("U-1", post_reading=140.0)),
        )

    def test_drift_exactly_on_the_limit_is_absorbed(self):
        post = 100.0 * (1.0 + DELTA_DRIFT_LIMIT)
        findings = check_measurement(burn_in("U-1", post_reading=post))
        self.assertNotIn("delta-drift-above-the-limit", findings)

    def test_a_catastrophic_failure_is_a_finding(self):
        self.assertIn(
            "unit-failed-during-the-exposure",
            check_measurement(burn_in("U-1", catastrophic_failure=True)),
        )


class TestAssessBurnIn(unittest.TestCase):
    def test_a_sound_exposure_survives(self):
        result = assess_burn_in(burn_in())
        self.assertEqual(result["disposition"], PASS)
        self.assertEqual(result["findings"], [])

    def test_any_finding_fails_the_unit(self):
        self.assertEqual(
            assess_burn_in(burn_in("U-1", catastrophic_failure=True))["disposition"],
            FAIL,
        )

    def test_the_report_carries_the_equivalence_and_the_junction(self):
        result = assess_burn_in(burn_in())
        self.assertAlmostEqual(
            result["equivalent_reference_hours"], REFERENCE_DURATION_H, places=9
        )
        self.assertAlmostEqual(result["junction_temperature_c"], 141.0, places=9)
        self.assertAlmostEqual(result["activation_energy_ev"], 0.70, places=12)


class TestLot(unittest.TestCase):
    def test_a_clean_lot_is_accepted(self):
        report = assess_burn_in_lot([burn_in("U-%d" % i) for i in range(10)])
        self.assertTrue(report["lot_accepted"])
        self.assertEqual(report["failed_ids"], [])

    def test_a_reject_fraction_above_the_allowable_refuses_the_lot(self):
        units = [burn_in("U-%d" % i) for i in range(8)]
        units.append(burn_in("U-8", catastrophic_failure=True))
        units.append(burn_in("U-9", catastrophic_failure=True))
        report = assess_burn_in_lot(units)
        self.assertFalse(report["lot_accepted"])
        self.assertAlmostEqual(report["reject_fraction"], 0.2, places=12)

    def test_a_looser_flow_class_accepts_the_same_lot(self):
        units = [burn_in("U-%d" % i) for i in range(8)]
        units.append(burn_in("U-8", catastrophic_failure=True))
        units.append(burn_in("U-9", catastrophic_failure=True))
        report = assess_burn_in_lot(units, "class-3")
        self.assertTrue(report["lot_accepted"])
        self.assertAlmostEqual(
            report["percent_defective_allowable"],
            PERCENT_DEFECTIVE_ALLOWABLE["class-3"],
            places=12,
        )

    def test_a_fraction_exactly_on_the_allowable_is_accepted(self):
        units = [burn_in("U-%d" % i) for i in range(9)]
        units.append(burn_in("U-9", catastrophic_failure=True))
        report = assess_burn_in_lot(units)
        self.assertAlmostEqual(
            report["reject_fraction"],
            percent_defective_allowable("class-2"),
            places=12,
        )
        self.assertTrue(report["lot_accepted"])

    def test_duplicate_unit_id_raises(self):
        with self.assertRaises(ValueError):
            assess_burn_in_lot([burn_in("U-1"), burn_in("U-1")])

    def test_empty_lot_raises(self):
        with self.assertRaises(ValueError):
            assess_burn_in_lot([])

    def test_non_list_lot_raises(self):
        with self.assertRaises(ValueError):
            assess_burn_in_lot(burn_in())

    def test_unknown_flow_class_raises(self):
        with self.assertRaises(ValueError):
            assess_burn_in_lot([burn_in("U-1")], "class-0")


if __name__ == "__main__":
    unittest.main()
