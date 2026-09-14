"""Contract tests for the clause 8.7.12 coverglass ultraviolet exposure test."""

import copy
import unittest

from e2008_coverglass_ultraviolet_exposure_test_logic import (
    BANDS,
    MAX_ACCELERATION_FACTOR,
    MAX_CHAMBER_PRESSURE_PA,
    MAX_CONTROL_DRIFT,
    MAX_MEASUREMENT_DELAY_H,
    MAX_TRANSMITTANCE_LOSS,
    TEMPERATURE_TOLERANCE_C,
    TOLERANCE,
    acceleration_findings,
    assess_coverglass_uv_exposure,
    band_loss,
    band_retention,
    chamber_findings,
    control_findings,
    dose_findings,
    equivalent_sun_hours,
    measurement_delay_findings,
    retention_factor,
    solar_weighted_transmittance,
    solarisation_findings,
)

BEFORE = {"ultraviolet": 0.90, "visible": 0.95, "near-infrared": 0.93}
AFTER = {"ultraviolet": 0.89, "visible": 0.945, "near-infrared": 0.928}
CONTROL_BEFORE = dict(BEFORE)
CONTROL_AFTER = {
    "ultraviolet": 0.8995,
    "visible": 0.9495,
    "near-infrared": 0.9295,
}
WEIGHTS = {"ultraviolet": 0.1, "visible": 0.5, "near-infrared": 0.4}


def exposure():
    return {
        "uv_suns": 3.0,
        "hours": 500.0,
        "pressure_pa": 1.0e-5,
        "temperature_c": 60.0,
        "reference_temperature_c": 60.0,
    }


def spec(**overrides):
    base = {
        "specimen": {
            "label": "coverglass-uv-01",
            "before": dict(BEFORE),
            "after": dict(AFTER),
        },
        "control": {
            "label": "coverglass-uv-dark-control",
            "before": dict(CONTROL_BEFORE),
            "after": dict(CONTROL_AFTER),
        },
        "exposure": exposure(),
        "required_esh": 1200.0,
        "measurement_delay_h": 6.0,
    }
    base.update(overrides)
    return base


class DoseTests(unittest.TestCase):
    def test_equivalent_sun_hours_multiply(self):
        self.assertAlmostEqual(
            equivalent_sun_hours(3.0, 500.0), 1500.0, places=9
        )

    def test_one_sun_is_an_hour_per_hour(self):
        self.assertAlmostEqual(equivalent_sun_hours(1.0, 250.0), 250.0, places=9)

    def test_zero_hours_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_sun_hours(3.0, 0.0)

    def test_negative_suns_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_sun_hours(-3.0, 500.0)

    def test_boolean_suns_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_sun_hours(True, 500.0)

    def test_dose_meeting_the_mission_gives_no_finding(self):
        self.assertEqual(dose_findings(1500.0, 1200.0), [])

    def test_dose_exactly_on_the_requirement_is_accepted(self):
        self.assertEqual(dose_findings(1200.0, 1200.0), [])

    def test_short_dose_is_a_finding(self):
        findings = dose_findings(800.0, 1200.0)
        self.assertEqual(len(findings), 1)
        self.assertIn("incomplete", findings[0])


class AccelerationTests(unittest.TestCase):
    def test_moderate_lamp_gives_no_finding(self):
        self.assertEqual(acceleration_findings(3.0), [])

    def test_lamp_exactly_on_the_cap_is_accepted(self):
        self.assertEqual(acceleration_findings(MAX_ACCELERATION_FACTOR), [])

    def test_lamp_past_the_cap_is_a_finding(self):
        findings = acceleration_findings(12.0)
        self.assertEqual(len(findings), 1)
        self.assertIn("reciprocity", findings[0])

    def test_default_reciprocity_cap(self):
        self.assertAlmostEqual(MAX_ACCELERATION_FACTOR, 5.0, places=9)

    def test_zero_cap_rejected(self):
        with self.assertRaises(ValueError):
            acceleration_findings(3.0, max_factor=0.0)


class ChamberTests(unittest.TestCase):
    def test_held_chamber_gives_no_finding(self):
        self.assertEqual(chamber_findings(exposure()), [])

    def test_pressure_exactly_on_the_cap_is_accepted(self):
        state = exposure()
        state["pressure_pa"] = MAX_CHAMBER_PRESSURE_PA
        self.assertEqual(chamber_findings(state), [])

    def test_residual_gas_is_a_finding(self):
        state = exposure()
        state["pressure_pa"] = 1.0
        findings = chamber_findings(state)
        self.assertEqual(len(findings), 1)
        self.assertIn("residual gas", findings[0])

    def test_temperature_exactly_on_the_tolerance_is_accepted(self):
        state = exposure()
        state["temperature_c"] = 60.0 + TEMPERATURE_TOLERANCE_C
        self.assertEqual(chamber_findings(state), [])

    def test_hot_specimen_is_a_finding(self):
        state = exposure()
        state["temperature_c"] = 110.0
        findings = chamber_findings(state)
        self.assertEqual(len(findings), 1)
        self.assertIn("C", findings[0])

    def test_both_conditions_off_give_two_findings(self):
        state = exposure()
        state["pressure_pa"] = 5.0
        state["temperature_c"] = 140.0
        self.assertEqual(len(chamber_findings(state)), 2)

    def test_exposure_without_a_pressure_rejected(self):
        state = exposure()
        del state["pressure_pa"]
        with self.assertRaises(ValueError):
            chamber_findings(state)

    def test_non_mapping_exposure_rejected(self):
        with self.assertRaises(ValueError):
            chamber_findings(["pressure_pa"])


class RetentionTests(unittest.TestCase):
    def test_three_bands_are_named(self):
        self.assertEqual(len(BANDS), 3)
        self.assertIn("ultraviolet", BANDS)

    def test_retention_is_after_over_before(self):
        self.assertAlmostEqual(retention_factor(0.45, 0.90), 0.5, places=9)

    def test_unchanged_reading_gives_unity(self):
        self.assertAlmostEqual(retention_factor(0.90, 0.90), 1.0, places=9)

    def test_transmittance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            retention_factor(1.4, 0.90)

    def test_zero_before_reading_rejected(self):
        with self.assertRaises(ValueError):
            retention_factor(0.45, 0.0)

    def test_band_retention_covers_every_band(self):
        retention = band_retention(BEFORE, AFTER)
        self.assertEqual(sorted(retention), sorted(BANDS))

    def test_band_loss_is_the_absolute_drop(self):
        losses = band_loss(BEFORE, AFTER)
        self.assertAlmostEqual(losses["ultraviolet"], 0.01, places=9)
        self.assertAlmostEqual(losses["visible"], 0.005, places=9)
        self.assertAlmostEqual(losses["near-infrared"], 0.002, places=9)

    def test_scan_missing_a_band_rejected(self):
        with self.assertRaises(ValueError):
            band_loss({"ultraviolet": 0.9}, AFTER)

    def test_scan_with_an_unknown_band_rejected(self):
        scan = dict(BEFORE)
        scan["gamma"] = 0.5
        with self.assertRaises(ValueError):
            band_retention(scan, AFTER)


class SolarisationTests(unittest.TestCase):
    def test_small_losses_give_no_finding(self):
        self.assertEqual(solarisation_findings(band_loss(BEFORE, AFTER)), [])

    def test_loss_exactly_on_the_limit_is_accepted(self):
        losses = {key: MAX_TRANSMITTANCE_LOSS for key in BANDS}
        self.assertEqual(solarisation_findings(losses), [])

    def test_darkened_band_is_a_finding(self):
        losses = dict(band_loss(BEFORE, AFTER))
        losses["ultraviolet"] = 0.11
        findings = solarisation_findings(losses)
        self.assertEqual(len(findings), 1)
        self.assertIn("ultraviolet", findings[0])

    def test_default_allowed_loss(self):
        self.assertAlmostEqual(MAX_TRANSMITTANCE_LOSS, 0.02, places=9)

    def test_losses_missing_a_band_rejected(self):
        with self.assertRaises(ValueError):
            solarisation_findings({"ultraviolet": 0.01})


class ControlTests(unittest.TestCase):
    def test_steady_control_gives_no_finding(self):
        self.assertEqual(control_findings(CONTROL_BEFORE, CONTROL_AFTER), [])

    def test_drifting_control_is_a_finding(self):
        drifted = dict(CONTROL_AFTER)
        drifted["visible"] = 0.90
        findings = control_findings(CONTROL_BEFORE, drifted)
        self.assertEqual(len(findings), 1)
        self.assertIn("dark control", findings[0])

    def test_control_that_brightened_is_also_a_finding(self):
        drifted = dict(CONTROL_AFTER)
        drifted["visible"] = 0.99
        self.assertEqual(len(control_findings(CONTROL_BEFORE, drifted)), 1)

    def test_default_control_drift_allowance(self):
        self.assertAlmostEqual(MAX_CONTROL_DRIFT, 0.002, places=9)

    def test_zero_drift_allowance_rejected(self):
        with self.assertRaises(ValueError):
            control_findings(CONTROL_BEFORE, CONTROL_AFTER, max_drift=0.0)


class DelayTests(unittest.TestCase):
    def test_prompt_scan_gives_no_finding(self):
        self.assertEqual(measurement_delay_findings(6.0), [])

    def test_delay_exactly_on_the_window_is_accepted(self):
        self.assertEqual(
            measurement_delay_findings(MAX_MEASUREMENT_DELAY_H), []
        )

    def test_late_scan_is_a_finding(self):
        findings = measurement_delay_findings(200.0)
        self.assertEqual(len(findings), 1)
        self.assertIn("bleaching", findings[0])

    def test_negative_delay_rejected(self):
        with self.assertRaises(ValueError):
            measurement_delay_findings(-1.0)

    def test_default_measurement_window(self):
        self.assertAlmostEqual(MAX_MEASUREMENT_DELAY_H, 24.0, places=9)


class WeightingTests(unittest.TestCase):
    def test_weighted_figure_sits_between_the_bands(self):
        weighted = solar_weighted_transmittance(BEFORE, WEIGHTS)
        self.assertAlmostEqual(weighted, 0.9370, places=9)

    def test_weights_that_do_not_add_to_one_rejected(self):
        with self.assertRaises(ValueError):
            solar_weighted_transmittance(
                BEFORE,
                {"ultraviolet": 0.1, "visible": 0.5, "near-infrared": 0.1},
            )

    def test_weights_missing_a_band_rejected(self):
        with self.assertRaises(ValueError):
            solar_weighted_transmittance(BEFORE, {"visible": 1.0})

    def test_zero_weight_rejected(self):
        with self.assertRaises(ValueError):
            solar_weighted_transmittance(
                BEFORE,
                {"ultraviolet": 0.0, "visible": 0.6, "near-infrared": 0.4},
            )

    def test_tolerance_is_small(self):
        self.assertAlmostEqual(TOLERANCE, 1e-9, places=12)


class AssessmentTests(unittest.TestCase):
    def test_conformant_run_has_no_finding(self):
        result = assess_coverglass_uv_exposure(spec())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["run_conformant"])

    def test_dose_and_specimen_are_reported(self):
        result = assess_coverglass_uv_exposure(spec())
        self.assertAlmostEqual(
            result["equivalent_sun_hours"], 1500.0, places=9
        )
        self.assertEqual(result["specimen"], "coverglass-uv-01")

    def test_band_retention_is_reported(self):
        result = assess_coverglass_uv_exposure(spec())
        self.assertAlmostEqual(
            result["band_retention"]["visible"], 0.945 / 0.95, places=9
        )

    def test_weighted_figures_are_none_without_weights(self):
        result = assess_coverglass_uv_exposure(spec())
        self.assertIsNone(result["solar_weighted_before"])
        self.assertIsNone(result["solar_weighted_loss"])

    def test_weighted_loss_is_reported_when_weights_are_given(self):
        result = assess_coverglass_uv_exposure(spec(band_weights=WEIGHTS))
        self.assertAlmostEqual(
            result["solar_weighted_loss"], 0.0043, places=9
        )

    def test_short_run_fails_the_assessment(self):
        state = spec()
        state["exposure"]["hours"] = 100.0
        result = assess_coverglass_uv_exposure(state)
        self.assertFalse(result["run_conformant"])

    def test_overdriven_lamp_fails_the_assessment(self):
        state = spec()
        state["exposure"]["uv_suns"] = 20.0
        result = assess_coverglass_uv_exposure(state)
        self.assertFalse(result["run_conformant"])

    def test_darkened_specimen_fails_the_assessment(self):
        state = spec()
        state["specimen"]["after"]["ultraviolet"] = 0.60
        result = assess_coverglass_uv_exposure(state)
        self.assertFalse(result["run_conformant"])
        self.assertTrue(
            any("darken" in item for item in result["findings"])
        )

    def test_drifting_control_fails_the_assessment(self):
        state = spec()
        state["control"]["after"]["visible"] = 0.80
        result = assess_coverglass_uv_exposure(state)
        self.assertFalse(result["run_conformant"])

    def test_late_scan_fails_the_assessment(self):
        result = assess_coverglass_uv_exposure(spec(measurement_delay_h=400.0))
        self.assertFalse(result["run_conformant"])

    def test_missing_spec_key_rejected(self):
        state = spec()
        del state["required_esh"]
        with self.assertRaises(ValueError):
            assess_coverglass_uv_exposure(state)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_uv_exposure(["specimen"])

    def test_specimen_without_a_label_rejected(self):
        state = copy.deepcopy(spec())
        del state["specimen"]["label"]
        with self.assertRaises(ValueError):
            assess_coverglass_uv_exposure(state)

    def test_exposure_without_hours_rejected(self):
        state = spec()
        del state["exposure"]["hours"]
        with self.assertRaises(ValueError):
            assess_coverglass_uv_exposure(state)


if __name__ == "__main__":
    unittest.main()
