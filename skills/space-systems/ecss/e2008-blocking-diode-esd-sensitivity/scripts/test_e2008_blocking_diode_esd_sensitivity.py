#!/usr/bin/env python3
"""Contract test for the blocking diode ESD regime check, clause 12.10.2 (offline)."""

import copy
import unittest

from e2008_blocking_diode_esd_sensitivity_logic import (
    BAND_TOLERANCE,
    CONTROL_ABSENT,
    CONTROL_COMPLIANT,
    CONTROL_OUT_OF_BAND,
    CONTROL_REQUIREMENTS,
    CONTROL_VERIFICATION_STALE,
    DEFAULT_WITHSTAND_THRESHOLDS,
    DISCHARGE_MODELS,
    EPA_REQUIRED_BANDS,
    ESD_NOT_SENSITIVE,
    MINIMUM_TRANSFER_PACKAGING,
    OBLIGED_CONTROLS,
    REGIME_COMPLIANT,
    REGIME_DEFICIENT,
    SENSITIVITY_BANDS,
    STORAGE_HUMIDITY_BAND,
    STORAGE_TEMPERATURE_BAND,
    TRANSFER_PACKAGING_LADDER,
    band_rank,
    evaluate_handling_regime,
    grade_control,
    grade_residual_charge,
    grade_route,
    grade_station,
    grade_storage,
    normalize_discharge_model,
    normalize_transfer_packaging,
    obliged_controls,
    residual_voltage_from_charge,
    sensitivity_band,
    transfer_rank,
    validate_thresholds,
)

BAND_A = "esd-band-a"
CLIP = "lead-shorting-clip-resistance"
STRAP = "wrist-strap-ground-path"


def _mid(name):
    low, high, _unit, _age = CONTROL_REQUIREMENTS[name]
    return (low + high) / 2.0


def _controls(band=BAND_A, overrides=None):
    overrides = overrides or {}
    out = []
    for name in OBLIGED_CONTROLS[band]:
        if name in overrides and overrides[name] is None:
            continue
        entry = {
            "control": name,
            "measured_value": _mid(name),
            "verification_age_days": 0.0,
        }
        if name in overrides:
            entry.update(overrides[name])
        out.append(entry)
    return out


def _station(
    station_id="st-1", band=BAND_A, epa=True, packaging="shielding", controls=None
):
    return {
        "station_id": station_id,
        "epa_designated": epa,
        "transfer_packaging": packaging,
        "controls": _controls(band) if controls is None else controls,
    }


def _storage(**overrides):
    base = {
        "temperature_c": 22.0,
        "relative_humidity_pct": 45.0,
        "declared_shelf_life_days": 730.0,
        "elapsed_shelf_life_days": 120.0,
    }
    base.update(overrides)
    return base


def _residual(**overrides):
    base = {
        "charge_coulomb": 1e-10,
        "package_capacitance_farad": 1e-11,
        "margin_factor": 2.0,
    }
    base.update(overrides)
    return base


def _spec(**overrides):
    spec = {
        "item_id": "bd-sn-0001",
        "withstand_voltage_v": 150.0,
        "discharge_model": "human-body-model",
        "route": [
            _station("st-goods-in"),
            _station("st-bench"),
            _station("st-store"),
        ],
        "storage": _storage(),
        "residual": _residual(),
    }
    spec.update(overrides)
    return spec


class DischargeModelTests(unittest.TestCase):
    def test_every_model_has_a_threshold_row(self):
        for model in DISCHARGE_MODELS:
            self.assertIn(model, DEFAULT_WITHSTAND_THRESHOLDS)

    def test_model_is_trimmed_and_lowercased(self):
        self.assertEqual(
            normalize_discharge_model("  Human-Body-Model "), "human-body-model"
        )

    def test_unknown_model_rejected(self):
        with self.assertRaises(ValueError):
            normalize_discharge_model("static-vibes-model")

    def test_default_table_validates(self):
        table = validate_thresholds(DEFAULT_WITHSTAND_THRESHOLDS)
        self.assertEqual(len(table), len(DISCHARGE_MODELS))

    def test_table_missing_a_model_rejected(self):
        partial = dict(DEFAULT_WITHSTAND_THRESHOLDS)
        del partial["machine-model"]
        with self.assertRaises(ValueError):
            validate_thresholds(partial)

    def test_table_that_does_not_rise_rejected(self):
        broken = copy.deepcopy(
            {k: list(v) for k, v in DEFAULT_WITHSTAND_THRESHOLDS.items()}
        )
        broken["human-body-model"][1] = ("esd-band-b", 100.0)
        with self.assertRaises(ValueError):
            validate_thresholds(broken)

    def test_table_with_a_wrong_band_name_rejected(self):
        broken = copy.deepcopy(
            {k: list(v) for k, v in DEFAULT_WITHSTAND_THRESHOLDS.items()}
        )
        broken["machine-model"][0] = ("esd-band-z", 100.0)
        with self.assertRaises(ValueError):
            validate_thresholds(broken)


class SensitivityBandTests(unittest.TestCase):
    def test_bands_run_most_sensitive_first(self):
        self.assertEqual(SENSITIVITY_BANDS[0], BAND_A)
        self.assertEqual(SENSITIVITY_BANDS[-1], ESD_NOT_SENSITIVE)
        self.assertLess(band_rank(BAND_A), band_rank(ESD_NOT_SENSITIVE))

    def test_low_withstand_voltage_is_the_most_sensitive_band(self):
        self.assertEqual(sensitivity_band(100.0, "human-body-model"), BAND_A)

    def test_same_voltage_places_differently_under_another_model(self):
        self.assertEqual(sensitivity_band(150.0, "human-body-model"), BAND_A)
        self.assertEqual(sensitivity_band(150.0, "machine-model"), "esd-band-b")

    def test_voltage_exactly_on_a_limit_falls_to_the_less_sensitive_band(self):
        self.assertEqual(sensitivity_band(250.0, "human-body-model"), "esd-band-b")

    def test_high_withstand_voltage_is_not_sensitive(self):
        self.assertEqual(
            sensitivity_band(9000.0, "human-body-model"), ESD_NOT_SENSITIVE
        )

    def test_zero_withstand_voltage_rejected(self):
        with self.assertRaises(ValueError):
            sensitivity_band(0.0, "human-body-model")

    def test_boolean_withstand_voltage_rejected(self):
        with self.assertRaises(ValueError):
            sensitivity_band(True, "human-body-model")

    def test_unknown_band_rank_rejected(self):
        with self.assertRaises(ValueError):
            band_rank("esd-band-zeta")


class ObligationTests(unittest.TestCase):
    def test_a_more_sensitive_band_owes_more_controls(self):
        self.assertGreater(
            len(obliged_controls(BAND_A)), len(obliged_controls("esd-band-c"))
        )

    def test_lead_shorting_is_owed_by_the_sensitive_bands(self):
        self.assertIn(CLIP, obliged_controls(BAND_A))
        self.assertIn(CLIP, obliged_controls("esd-band-b"))

    def test_a_not_sensitive_part_owes_no_control(self):
        self.assertEqual(obliged_controls(ESD_NOT_SENSITIVE), ())

    def test_protected_area_is_owed_by_every_sensitive_band(self):
        for band in SENSITIVITY_BANDS[:-1]:
            self.assertIn(band, EPA_REQUIRED_BANDS)
        self.assertNotIn(ESD_NOT_SENSITIVE, EPA_REQUIRED_BANDS)

    def test_shielding_and_dissipative_are_different_rungs(self):
        self.assertGreater(transfer_rank("shielding"), transfer_rank("dissipative"))
        self.assertEqual(TRANSFER_PACKAGING_LADDER[0], "unprotected")

    def test_sensitive_bands_oblige_shielding_outright(self):
        self.assertEqual(MINIMUM_TRANSFER_PACKAGING[BAND_A], "shielding")
        self.assertEqual(MINIMUM_TRANSFER_PACKAGING["esd-band-b"], "shielding")

    def test_unknown_packaging_rejected(self):
        with self.assertRaises(ValueError):
            normalize_transfer_packaging("a jiffy bag")


class ControlGradingTests(unittest.TestCase):
    def test_control_in_band_and_freshly_verified_is_compliant(self):
        graded = grade_control(
            STRAP, {"measured_value": _mid(STRAP), "verification_age_days": 0.5}
        )
        self.assertEqual(graded["status"], CONTROL_COMPLIANT)
        self.assertIsNone(graded["finding"])

    def test_control_nobody_offered_is_graded_absent_not_skipped(self):
        graded = grade_control(STRAP, None)
        self.assertEqual(graded["status"], CONTROL_ABSENT)
        self.assertIsNotNone(graded["finding"])

    def test_control_outside_its_own_band_is_not_a_control(self):
        graded = grade_control(
            STRAP, {"measured_value": 1.0, "verification_age_days": 0.0}
        )
        self.assertEqual(graded["status"], CONTROL_OUT_OF_BAND)

    def test_in_band_but_stale_verification_is_a_finding(self):
        graded = grade_control(
            STRAP, {"measured_value": _mid(STRAP), "verification_age_days": 330.0}
        )
        self.assertEqual(graded["status"], CONTROL_VERIFICATION_STALE)
        self.assertTrue(graded["in_band"])
        self.assertFalse(graded["verification_current"])

    def test_measurement_exactly_on_its_interval_still_stands(self):
        _low, _high, _unit, max_age = CONTROL_REQUIREMENTS[STRAP]
        graded = grade_control(
            STRAP, {"measured_value": _mid(STRAP), "verification_age_days": max_age}
        )
        self.assertEqual(graded["status"], CONTROL_COMPLIANT)

    def test_measurement_exactly_on_a_band_limit_is_in_band(self):
        low, _high, _unit, _age = CONTROL_REQUIREMENTS[CLIP]
        graded = grade_control(
            CLIP, {"measured_value": low, "verification_age_days": 0.0}
        )
        self.assertTrue(graded["in_band"])

    def test_shorting_clip_measuring_kilohms_is_not_a_short(self):
        graded = grade_control(
            CLIP, {"measured_value": 4700.0, "verification_age_days": 0.0}
        )
        self.assertEqual(graded["status"], CONTROL_OUT_OF_BAND)

    def test_negative_verification_age_rejected(self):
        with self.assertRaises(ValueError):
            grade_control(
                STRAP, {"measured_value": _mid(STRAP), "verification_age_days": -1.0}
            )

    def test_unknown_control_rejected(self):
        with self.assertRaises(ValueError):
            grade_control("vibe-check", None)

    def test_control_missing_a_key_rejected(self):
        with self.assertRaises(ValueError):
            grade_control(STRAP, {"measured_value": _mid(STRAP)})


class StationGradingTests(unittest.TestCase):
    def test_fully_controlled_station_is_compliant(self):
        result = grade_station(_station(), BAND_A)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_station_outside_a_protected_area_is_deficient(self):
        result = grade_station(_station(epa=False), BAND_A)
        self.assertFalse(result["epa_ok"])
        self.assertFalse(result["compliant"])

    def test_four_of_five_controls_is_not_a_compliant_station(self):
        station = _station(controls=_controls(overrides={CLIP: None}))
        result = grade_station(station, BAND_A)
        self.assertFalse(result["compliant"])
        statuses = [c["status"] for c in result["controls"]]
        self.assertIn(CONTROL_ABSENT, statuses)

    def test_dissipative_arrival_is_refused_where_shielding_is_owed(self):
        result = grade_station(_station(packaging="dissipative"), BAND_A)
        self.assertFalse(result["transfer_ok"])
        self.assertFalse(result["compliant"])

    def test_dissipative_arrival_is_enough_for_the_mild_band(self):
        station = _station(band="esd-band-c", packaging="dissipative")
        result = grade_station(station, "esd-band-c")
        self.assertTrue(result["compliant"])

    def test_control_offered_twice_rejected(self):
        controls = _controls()
        controls.append(dict(controls[0]))
        with self.assertRaises(ValueError):
            grade_station(_station(controls=controls), BAND_A)

    def test_non_boolean_protected_area_flag_rejected(self):
        station = _station()
        station["epa_designated"] = "mostly"
        with self.assertRaises(ValueError):
            grade_station(station, BAND_A)

    def test_station_missing_a_key_rejected(self):
        station = _station()
        del station["transfer_packaging"]
        with self.assertRaises(ValueError):
            grade_station(station, BAND_A)

    def test_unrecognized_offered_control_rejected(self):
        controls = _controls()
        controls.append(
            {"control": "lucky-rabbit-foot", "measured_value": 1.0, "verification_age_days": 0.0}
        )
        with self.assertRaises(ValueError):
            grade_station(_station(controls=controls), BAND_A)


class RouteTests(unittest.TestCase):
    def test_all_compliant_stations_make_a_compliant_route(self):
        route = grade_route([_station("st-1"), _station("st-2")], BAND_A)
        self.assertTrue(route["compliant"])
        self.assertIsNone(route["governing_station_id"])

    def test_one_weak_station_governs_the_whole_route(self):
        route = grade_route(
            [_station("st-1"), _station("st-2", epa=False), _station("st-3")], BAND_A
        )
        self.assertFalse(route["compliant"])
        self.assertEqual(route["governing_station_id"], "st-2")
        self.assertEqual(route["compliant_station_count"], 2)

    def test_first_exposure_is_the_earliest_deficient_station(self):
        route = grade_route(
            [
                _station("st-1", packaging="unprotected"),
                _station("st-2", epa=False),
            ],
            BAND_A,
        )
        self.assertEqual(route["first_exposure_index"], 0)

    def test_repeated_station_rejected(self):
        with self.assertRaises(ValueError):
            grade_route([_station("st-1"), _station("st-1")], BAND_A)

    def test_empty_route_rejected(self):
        with self.assertRaises(ValueError):
            grade_route([], BAND_A)


class StorageTests(unittest.TestCase):
    def test_store_inside_both_envelopes_is_compliant(self):
        self.assertTrue(grade_storage(_storage())["compliant"])

    def test_store_below_the_humidity_floor_is_the_esd_finding(self):
        result = grade_storage(_storage(relative_humidity_pct=12.0))
        self.assertFalse(result["compliant"])
        self.assertIn("floor", result["findings"][0])

    def test_store_above_the_humidity_ceiling_is_also_a_finding(self):
        result = grade_storage(_storage(relative_humidity_pct=85.0))
        self.assertFalse(result["compliant"])

    def test_humidity_band_is_two_sided(self):
        self.assertLess(STORAGE_HUMIDITY_BAND[0], STORAGE_HUMIDITY_BAND[1])
        self.assertLess(STORAGE_TEMPERATURE_BAND[0], STORAGE_TEMPERATURE_BAND[1])

    def test_reading_exactly_on_the_humidity_floor_is_accepted(self):
        result = grade_storage(
            _storage(relative_humidity_pct=STORAGE_HUMIDITY_BAND[0])
        )
        self.assertTrue(result["compliant"])

    def test_store_below_its_temperature_floor_is_a_finding(self):
        result = grade_storage(_storage(temperature_c=4.0))
        self.assertFalse(result["compliant"])

    def test_spent_shelf_life_is_a_finding(self):
        result = grade_storage(
            _storage(declared_shelf_life_days=730.0, elapsed_shelf_life_days=900.0)
        )
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(
            result["shelf_life_spent_fraction"], 900.0 / 730.0, places=9
        )

    def test_shelf_life_exactly_spent_is_accepted(self):
        result = grade_storage(
            _storage(declared_shelf_life_days=730.0, elapsed_shelf_life_days=730.0)
        )
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["shelf_life_spent_fraction"], 1.0, places=9)

    def test_humidity_outside_zero_to_hundred_rejected(self):
        with self.assertRaises(ValueError):
            grade_storage(_storage(relative_humidity_pct=140.0))

    def test_negative_elapsed_shelf_life_rejected(self):
        with self.assertRaises(ValueError):
            grade_storage(_storage(elapsed_shelf_life_days=-5.0))


class ResidualChargeTests(unittest.TestCase):
    def test_charge_becomes_a_voltage_across_the_package(self):
        self.assertAlmostEqual(
            residual_voltage_from_charge(1e-9, 1e-11), 100.0, places=9
        )

    def test_a_smaller_package_turns_the_same_charge_into_more_volts(self):
        big = residual_voltage_from_charge(1e-9, 2e-11)
        small = residual_voltage_from_charge(1e-9, 1e-11)
        self.assertAlmostEqual(small, 2.0 * big, places=9)

    def test_zero_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            residual_voltage_from_charge(1e-9, 0.0)

    def test_negative_charge_rejected(self):
        with self.assertRaises(ValueError):
            residual_voltage_from_charge(-1e-9, 1e-11)

    def test_margin_is_applied_before_the_comparison(self):
        result = grade_residual_charge(_residual(charge_coulomb=1e-9), 150.0)
        self.assertAlmostEqual(result["delivered_voltage_v"], 100.0, places=9)
        self.assertAlmostEqual(result["stress_voltage_v"], 200.0, places=9)
        self.assertFalse(result["compliant"])

    def test_a_part_clearing_only_without_the_margin_does_not_clear(self):
        without_margin = grade_residual_charge(
            _residual(charge_coulomb=1e-9, margin_factor=1.0), 150.0
        )
        self.assertTrue(without_margin["compliant"])
        with_margin = grade_residual_charge(_residual(charge_coulomb=1e-9), 150.0)
        self.assertFalse(with_margin["compliant"])

    def test_stress_exactly_on_the_withstand_voltage_clears(self):
        result = grade_residual_charge(_residual(charge_coulomb=1e-9), 200.0)
        self.assertAlmostEqual(result["stress_voltage_v"], 200.0, places=9)
        self.assertTrue(result["compliant"])

    def test_margin_below_one_rejected(self):
        with self.assertRaises(ValueError):
            grade_residual_charge(_residual(margin_factor=0.5), 150.0)

    def test_residual_missing_a_key_rejected(self):
        residual = _residual()
        del residual["package_capacitance_farad"]
        with self.assertRaises(ValueError):
            grade_residual_charge(residual, 150.0)


class RegimeTests(unittest.TestCase):
    def test_clean_regime_is_compliant(self):
        result = evaluate_handling_regime(_spec())
        self.assertEqual(result["verdict"], REGIME_COMPLIANT)
        self.assertEqual(result["sensitivity_band"], BAND_A)

    def test_one_unshielded_transfer_breaks_the_whole_regime(self):
        spec = _spec(
            route=[
                _station("st-goods-in"),
                _station("st-bench", packaging="antistatic-only"),
                _station("st-store"),
            ]
        )
        result = evaluate_handling_regime(spec)
        self.assertEqual(result["verdict"], REGIME_DEFICIENT)
        self.assertEqual(result["route"]["governing_station_id"], "st-bench")

    def test_a_dry_store_alone_holds_the_regime(self):
        result = evaluate_handling_regime(
            _spec(storage=_storage(relative_humidity_pct=8.0))
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(result["route"]["compliant"])

    def test_a_less_sensitive_part_owes_a_smaller_control_set(self):
        spec = _spec(
            withstand_voltage_v=3000.0,
            route=[_station("st-1", band="esd-band-c", packaging="dissipative")],
        )
        result = evaluate_handling_regime(spec)
        self.assertEqual(result["sensitivity_band"], "esd-band-c")
        self.assertTrue(result["compliant"])

    def test_findings_from_every_arm_are_reported_together(self):
        spec = _spec(
            route=[_station("st-1", epa=False)],
            storage=_storage(relative_humidity_pct=8.0),
            residual=_residual(charge_coulomb=1e-8),
        )
        result = evaluate_handling_regime(spec)
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_tolerance_is_named_and_small(self):
        self.assertLess(BAND_TOLERANCE, 1e-6)

    def test_spec_missing_a_key_rejected(self):
        spec = _spec()
        del spec["storage"]
        with self.assertRaises(ValueError):
            evaluate_handling_regime(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_handling_regime("we use a wrist strap")


if __name__ == "__main__":
    unittest.main()
