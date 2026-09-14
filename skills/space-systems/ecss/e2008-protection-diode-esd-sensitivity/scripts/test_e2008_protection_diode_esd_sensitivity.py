#!/usr/bin/env python3
"""Contract test for the ESD-sensitive diode handling regime, clause 9.10.2."""

import unittest

from e2008_protection_diode_esd_sensitivity_logic import (
    BAND_TOLERANCE,
    CONTROL_ABSENT,
    CONTROL_COMPLIANT,
    CONTROL_OUT_OF_BAND,
    CONTROL_REQUIREMENTS,
    CONTROL_VERIFICATION_STALE,
    DEFAULT_SENSITIVITY_THRESHOLDS,
    DISCHARGE_MODELS,
    ESD_BANDS,
    ESD_NOT_SENSITIVE,
    MINIMUM_PACKAGING,
    PACKAGING_LADDER,
    REGIME_COMPLIANT,
    REGIME_DEFICIENT,
    band_rank,
    evaluate_handling_regime,
    grade_control,
    grade_controls,
    grade_packaging,
    grade_residual_charge,
    grade_storage,
    normalize_discharge_model,
    normalize_packaging,
    obliged_controls,
    packaging_rank,
    residual_voltage_from_charge,
    sensitivity_band,
    validate_thresholds,
)

MID = {
    "wrist-strap-ground-path": 1.0e7,
    "worksurface-ground-path": 1.0e7,
    "floor-footwear-ground-path": 1.0e7,
    "ionizer-offset": 5.0,
    "terminal-shorting-bar": 1.0,
}


def _control(control_id, value=None, age=0.0, present=True):
    if value is None:
        value = MID[control_id]
    return {
        "control_id": control_id,
        "present": present,
        "measured_value": value,
        "days_since_verification": age,
    }


def _controls(band="esd-band-1", **overrides):
    out = []
    for control_id in obliged_controls(band):
        entry = _control(control_id)
        entry.update(overrides.get(control_id, {}))
        out.append(entry)
    return out


def _envelope(**overrides):
    base = {
        "temperature_c": (15.0, 30.0),
        "relative_humidity_pct": (30.0, 60.0),
        "shelf_life_days": 365.0,
    }
    base.update(overrides)
    return base


def _observed(**overrides):
    base = {
        "temperature_c": 22.0,
        "relative_humidity_pct": 45.0,
        "days_in_storage": 100.0,
    }
    base.update(overrides)
    return base


def _spec(**overrides):
    spec = {
        "item_id": "dio-7741",
        "withstand_voltage_v": 200.0,
        "discharge_model": "human-body-model",
        "controls": _controls("esd-band-1"),
        "packaging_category": "shielding",
        "storage_envelope": _envelope(),
        "storage_observed": _observed(),
        "residual_charge_nc": 1.0,
        "package_capacitance_pf": 100.0,
        "margin_factor": 2.0,
    }
    spec.update(overrides)
    return spec


class SensitivityBandTests(unittest.TestCase):
    def test_bands_run_most_sensitive_first(self):
        self.assertEqual(ESD_BANDS[0], "esd-band-1")
        self.assertEqual(ESD_BANDS[-1], ESD_NOT_SENSITIVE)

    def test_rank_orders_the_band_ladder(self):
        self.assertLess(band_rank("esd-band-1"), band_rank("esd-band-3"))

    def test_a_low_withstand_voltage_lands_in_the_most_sensitive_band(self):
        self.assertEqual(sensitivity_band(120.0, "human-body-model"), "esd-band-1")

    def test_the_same_voltage_lands_differently_under_a_different_model(self):
        self.assertEqual(sensitivity_band(150.0, "human-body-model"), "esd-band-1")
        self.assertEqual(sensitivity_band(150.0, "machine-model"), "esd-band-2")

    def test_a_voltage_exactly_on_a_limit_falls_into_the_less_sensitive_band(self):
        self.assertEqual(sensitivity_band(250.0, "human-body-model"), "esd-band-2")

    def test_a_high_withstand_voltage_is_not_sensitive(self):
        self.assertEqual(
            sensitivity_band(8000.0, "human-body-model"), ESD_NOT_SENSITIVE
        )

    def test_unknown_discharge_model_rejected(self):
        with self.assertRaises(ValueError):
            sensitivity_band(200.0, "field-induced-guesswork")

    def test_model_name_is_trimmed_and_lowercased(self):
        self.assertEqual(
            normalize_discharge_model("  Human-Body-Model "), "human-body-model"
        )

    def test_three_discharge_models_are_recognized(self):
        self.assertEqual(len(DISCHARGE_MODELS), 3)

    def test_zero_withstand_voltage_rejected(self):
        with self.assertRaises(ValueError):
            sensitivity_band(0.0, "human-body-model")

    def test_boolean_withstand_voltage_rejected(self):
        with self.assertRaises(ValueError):
            sensitivity_band(True, "human-body-model")

    def test_a_threshold_table_that_does_not_rise_is_rejected(self):
        table = dict(DEFAULT_SENSITIVITY_THRESHOLDS)
        table["human-body-model"] = (
            ("esd-band-1", 1000.0),
            ("esd-band-2", 250.0),
        )
        with self.assertRaises(ValueError):
            validate_thresholds(table)

    def test_a_threshold_table_missing_a_model_is_rejected(self):
        table = dict(DEFAULT_SENSITIVITY_THRESHOLDS)
        del table["machine-model"]
        with self.assertRaises(ValueError):
            validate_thresholds(table)

    def test_a_project_threshold_table_overrides_the_default(self):
        table = {
            "human-body-model": (("esd-band-1", 50.0), ("esd-band-2", 80.0)),
            "machine-model": (("esd-band-1", 10.0),),
            "charged-device-model": (("esd-band-1", 10.0),),
        }
        self.assertEqual(
            sensitivity_band(120.0, "human-body-model", table), ESD_NOT_SENSITIVE
        )


class ObligedControlSetTests(unittest.TestCase):
    def test_the_most_sensitive_band_obliges_every_control(self):
        self.assertEqual(
            set(obliged_controls("esd-band-1")), set(CONTROL_REQUIREMENTS)
        )

    def test_a_less_sensitive_band_obliges_fewer_controls(self):
        self.assertLess(
            len(obliged_controls("esd-band-3")), len(obliged_controls("esd-band-1"))
        )

    def test_terminal_shorting_is_obliged_on_the_two_sensitive_bands(self):
        self.assertIn("terminal-shorting-bar", obliged_controls("esd-band-2"))
        self.assertNotIn("terminal-shorting-bar", obliged_controls("esd-band-3"))

    def test_a_part_that_is_not_sensitive_owes_no_control(self):
        self.assertEqual(obliged_controls(ESD_NOT_SENSITIVE), ())

    def test_unknown_band_rejected(self):
        with self.assertRaises(ValueError):
            obliged_controls("esd-band-9")


class ControlGradingTests(unittest.TestCase):
    def test_a_control_inside_its_band_and_freshly_verified_is_compliant(self):
        graded = grade_control(_control("worksurface-ground-path"))
        self.assertEqual(graded["state"], CONTROL_COMPLIANT)
        self.assertTrue(graded["compliant"])

    def test_a_control_below_its_band_is_not_compliant(self):
        graded = grade_control(_control("wrist-strap-ground-path", value=1.0e3))
        self.assertEqual(graded["state"], CONTROL_OUT_OF_BAND)
        self.assertFalse(graded["in_band"])

    def test_a_control_above_its_band_is_not_compliant(self):
        graded = grade_control(_control("wrist-strap-ground-path", value=1.0e9))
        self.assertEqual(graded["state"], CONTROL_OUT_OF_BAND)

    def test_a_control_exactly_on_its_lower_limit_is_inside_its_band(self):
        low = CONTROL_REQUIREMENTS["wrist-strap-ground-path"][0]
        graded = grade_control(_control("wrist-strap-ground-path", value=low))
        self.assertTrue(graded["in_band"])
        self.assertAlmostEqual(graded["measured_value"], low, places=9)

    def test_a_control_exactly_on_its_upper_limit_is_inside_its_band(self):
        high = CONTROL_REQUIREMENTS["wrist-strap-ground-path"][1]
        graded = grade_control(_control("wrist-strap-ground-path", value=high))
        self.assertTrue(graded["in_band"])

    def test_a_control_in_band_but_verified_too_long_ago_is_stale(self):
        graded = grade_control(_control("wrist-strap-ground-path", age=30.0))
        self.assertEqual(graded["state"], CONTROL_VERIFICATION_STALE)
        self.assertFalse(graded["compliant"])
        self.assertTrue(graded["in_band"])

    def test_a_control_verified_exactly_on_its_interval_is_still_current(self):
        age = CONTROL_REQUIREMENTS["floor-footwear-ground-path"][3]
        graded = grade_control(_control("floor-footwear-ground-path", age=age))
        self.assertTrue(graded["verification_current"])
        self.assertEqual(graded["state"], CONTROL_COMPLIANT)

    def test_an_absent_control_is_graded_absent_not_skipped(self):
        graded = grade_control(
            {"control_id": "ionizer-offset", "present": False}
        )
        self.assertEqual(graded["state"], CONTROL_ABSENT)
        self.assertFalse(graded["compliant"])

    def test_an_ionizer_offset_of_either_sign_is_graded(self):
        self.assertTrue(grade_control(_control("ionizer-offset", value=-40.0))["in_band"])
        self.assertFalse(
            grade_control(_control("ionizer-offset", value=-80.0))["in_band"]
        )

    def test_a_shorting_bar_must_actually_be_a_short(self):
        self.assertFalse(
            grade_control(_control("terminal-shorting-bar", value=5.0e3))["in_band"]
        )

    def test_a_present_control_without_a_measurement_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_control(
                {
                    "control_id": "wrist-strap-ground-path",
                    "present": True,
                    "days_since_verification": 0.0,
                }
            )

    def test_a_negative_verification_age_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_control(_control("wrist-strap-ground-path", age=-1.0))

    def test_a_non_boolean_presence_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_control(
                {"control_id": "wrist-strap-ground-path", "present": "yes"}
            )

    def test_an_unrecognized_control_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_control({"control_id": "lucky-charm", "present": False})

    def test_a_missing_obliged_control_is_graded_absent_by_the_set(self):
        controls = [c for c in _controls("esd-band-1") if c["control_id"] != "ionizer-offset"]
        graded = grade_controls(controls, "esd-band-1")
        self.assertIn("ionizer-offset", graded["deficient_control_ids"])
        self.assertFalse(graded["all_compliant"])

    def test_four_of_five_controls_passing_does_not_pass_the_set(self):
        graded = grade_controls(
            _controls("esd-band-1", **{"ionizer-offset": {"measured_value": 400.0}}),
            "esd-band-1",
        )
        self.assertEqual(len(graded["controls"]), 5)
        self.assertEqual(graded["deficient_control_ids"], ("ionizer-offset",))
        self.assertFalse(graded["all_compliant"])

    def test_a_control_the_band_does_not_oblige_is_reported_not_graded(self):
        controls = _controls("esd-band-3")
        controls.append(_control("ionizer-offset"))
        graded = grade_controls(controls, "esd-band-3")
        self.assertEqual(graded["not_obliged_control_ids"], ("ionizer-offset",))
        self.assertTrue(graded["all_compliant"])

    def test_a_repeated_control_entry_is_rejected(self):
        controls = _controls("esd-band-3")
        controls.append(_control("worksurface-ground-path"))
        with self.assertRaises(ValueError):
            grade_controls(controls, "esd-band-3")


class PackagingTests(unittest.TestCase):
    def test_ladder_runs_weakest_first(self):
        self.assertEqual(PACKAGING_LADDER[0], "unprotected")
        self.assertEqual(PACKAGING_LADDER[-1], "shielding")

    def test_rank_orders_the_packaging_ladder(self):
        self.assertLess(packaging_rank("dissipative"), packaging_rank("shielding"))

    def test_a_dissipative_bag_does_not_answer_a_band_one_part(self):
        graded = grade_packaging("dissipative", "esd-band-1")
        self.assertFalse(graded["adequate"])
        self.assertEqual(graded["minimum_category"], "shielding")

    def test_a_dissipative_bag_does_answer_a_band_three_part(self):
        self.assertTrue(grade_packaging("dissipative", "esd-band-3")["adequate"])

    def test_shielding_answers_every_band(self):
        for band in ESD_BANDS:
            self.assertTrue(grade_packaging("shielding", band)["adequate"])

    def test_the_minimum_table_covers_every_band(self):
        self.assertEqual(set(MINIMUM_PACKAGING), set(ESD_BANDS))

    def test_unknown_packaging_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_packaging("brown paper")


class StorageEnvelopeTests(unittest.TestCase):
    def test_a_store_inside_both_bands_is_compliant(self):
        graded = grade_storage(_envelope(), _observed())
        self.assertTrue(graded["compliant"])

    def test_a_store_drier_than_its_humidity_floor_is_a_finding(self):
        graded = grade_storage(_envelope(), _observed(relative_humidity_pct=12.0))
        self.assertFalse(graded["compliant"])
        self.assertTrue(any("floor" in r for r in graded["reasons"]))

    def test_a_store_wetter_than_its_humidity_ceiling_is_a_finding(self):
        graded = grade_storage(_envelope(), _observed(relative_humidity_pct=85.0))
        self.assertFalse(graded["compliant"])
        self.assertTrue(any("ceiling" in r for r in graded["reasons"]))

    def test_a_store_exactly_on_its_humidity_floor_is_inside(self):
        graded = grade_storage(_envelope(), _observed(relative_humidity_pct=30.0))
        self.assertTrue(graded["relative_humidity"]["inside"])
        self.assertTrue(graded["compliant"])

    def test_a_store_outside_its_temperature_band_is_a_finding(self):
        graded = grade_storage(_envelope(), _observed(temperature_c=45.0))
        self.assertFalse(graded["temperature"]["inside"])

    def test_shelf_life_spent_is_graded_with_the_envelope(self):
        graded = grade_storage(_envelope(), _observed(days_in_storage=400.0))
        self.assertFalse(graded["within_shelf_life"])
        self.assertAlmostEqual(graded["shelf_life_days_remaining"], -35.0, places=9)

    def test_a_part_exactly_on_its_shelf_life_is_still_within_it(self):
        graded = grade_storage(_envelope(), _observed(days_in_storage=365.0))
        self.assertTrue(graded["within_shelf_life"])
        self.assertAlmostEqual(graded["shelf_life_days_remaining"], 0.0, places=9)

    def test_an_inverted_humidity_band_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_storage(_envelope(relative_humidity_pct=(60.0, 30.0)), _observed())

    def test_a_humidity_band_beyond_one_hundred_percent_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_storage(_envelope(relative_humidity_pct=(30.0, 140.0)), _observed())

    def test_a_one_sided_humidity_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_storage(_envelope(relative_humidity_pct=60.0), _observed())

    def test_a_negative_storage_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_storage(_envelope(), _observed(days_in_storage=-4.0))


class ResidualChargeTests(unittest.TestCase):
    def test_charge_over_capacitance_gives_volts(self):
        self.assertAlmostEqual(
            residual_voltage_from_charge(1.0, 100.0), 10.0, places=9
        )

    def test_a_smaller_package_capacitance_delivers_more_volts(self):
        self.assertAlmostEqual(
            residual_voltage_from_charge(1.0, 10.0), 100.0, places=9
        )

    def test_zero_charge_delivers_no_volts(self):
        self.assertAlmostEqual(residual_voltage_from_charge(0.0, 50.0), 0.0, places=9)

    def test_zero_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            residual_voltage_from_charge(1.0, 0.0)

    def test_negative_charge_rejected(self):
        with self.assertRaises(ValueError):
            residual_voltage_from_charge(-1.0, 50.0)

    def test_a_charge_that_clears_only_without_the_margin_is_a_finding(self):
        graded = grade_residual_charge(1.0, 10.0, 150.0, 2.0)
        self.assertAlmostEqual(graded["residual_voltage_v"], 100.0, places=9)
        self.assertAlmostEqual(graded["demanded_voltage_v"], 200.0, places=9)
        self.assertFalse(graded["clears"])

    def test_a_charge_that_clears_with_the_margin_passes(self):
        graded = grade_residual_charge(1.0, 100.0, 150.0, 2.0)
        self.assertTrue(graded["clears"])
        self.assertAlmostEqual(graded["utilisation"], 20.0 / 150.0, places=9)

    def test_a_demand_exactly_on_the_withstand_voltage_clears(self):
        graded = grade_residual_charge(1.0, 10.0, 200.0, 2.0)
        self.assertAlmostEqual(graded["demanded_voltage_v"], 200.0, places=9)
        self.assertTrue(graded["clears"])

    def test_a_margin_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_residual_charge(1.0, 100.0, 150.0, 0.5)

    def test_band_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(BAND_TOLERANCE, 1e-6)


class RegimeTests(unittest.TestCase):
    def test_a_complete_regime_is_compliant(self):
        result = evaluate_handling_regime(_spec())
        self.assertEqual(result["verdict"], REGIME_COMPLIANT)
        self.assertEqual(result["sensitivity_band"], "esd-band-1")
        self.assertTrue(result["esd_sensitive"])

    def test_the_band_drives_which_controls_are_obliged(self):
        result = evaluate_handling_regime(
            _spec(withstand_voltage_v=3000.0, controls=_controls("esd-band-3"))
        )
        self.assertEqual(result["sensitivity_band"], "esd-band-3")
        self.assertEqual(len(result["controls"]["controls"]), 3)
        self.assertEqual(result["verdict"], REGIME_COMPLIANT)

    def test_one_stale_control_alone_leaves_the_regime_deficient(self):
        controls = _controls(
            "esd-band-1", **{"wrist-strap-ground-path": {"days_since_verification": 9.0}}
        )
        result = evaluate_handling_regime(_spec(controls=controls))
        self.assertEqual(result["verdict"], REGIME_DEFICIENT)
        self.assertEqual(
            result["controls"]["deficient_control_ids"], ("wrist-strap-ground-path",)
        )

    def test_a_merely_dissipative_bag_alone_leaves_the_regime_deficient(self):
        result = evaluate_handling_regime(_spec(packaging_category="dissipative"))
        self.assertEqual(result["verdict"], REGIME_DEFICIENT)
        self.assertFalse(result["packaging"]["adequate"])

    def test_a_dry_store_alone_leaves_the_regime_deficient(self):
        result = evaluate_handling_regime(
            _spec(storage_observed=_observed(relative_humidity_pct=8.0))
        )
        self.assertEqual(result["verdict"], REGIME_DEFICIENT)
        self.assertFalse(result["storage"]["compliant"])

    def test_a_residual_charge_alone_leaves_the_regime_deficient(self):
        result = evaluate_handling_regime(
            _spec(residual_charge_nc=40.0, package_capacitance_pf=100.0)
        )
        self.assertEqual(result["verdict"], REGIME_DEFICIENT)
        self.assertFalse(result["residual_charge"]["clears"])

    def test_a_part_that_is_not_sensitive_owes_no_control_but_is_still_stored(self):
        result = evaluate_handling_regime(
            _spec(
                withstand_voltage_v=9000.0,
                controls=[],
                packaging_category="antistatic-only",
            )
        )
        self.assertEqual(result["sensitivity_band"], ESD_NOT_SENSITIVE)
        self.assertFalse(result["esd_sensitive"])
        self.assertEqual(result["verdict"], REGIME_COMPLIANT)

    def test_every_deficient_arm_contributes_its_own_finding(self):
        result = evaluate_handling_regime(
            _spec(
                packaging_category="unprotected",
                storage_observed=_observed(relative_humidity_pct=5.0),
                residual_charge_nc=40.0,
            )
        )
        self.assertGreaterEqual(len(result["findings"]), 3)
        self.assertEqual(result["verdict"], REGIME_DEFICIENT)

    def test_spec_missing_a_key_rejected(self):
        spec = _spec()
        del spec["storage_envelope"]
        with self.assertRaises(ValueError):
            evaluate_handling_regime(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_handling_regime("bag it and tag it")


if __name__ == "__main__":
    unittest.main()
