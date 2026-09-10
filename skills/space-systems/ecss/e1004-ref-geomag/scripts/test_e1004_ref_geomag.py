#!/usr/bin/env python3
"""Offline stdlib unittest for e1004_ref_geomag_logic (gate 3 contract test)."""

import unittest

from e1004_ref_geomag_logic import (
    EARTH_RADIUS_KM,
    EPOCH_STATUS_DEFINITIVE,
    EPOCH_STATUS_PREDICTIVE,
    EPOCH_STATUS_STALE,
    NOMINAL_MAGNETOPAUSE_STANDOFF_RE,
    POSITION_INSIDE_MAGNETOPAUSE,
    POSITION_OUTSIDE_OR_AT_MAGNETOPAUSE,
    REFERENCE_DYNAMIC_PRESSURE_NPA,
    REGIME_BEYOND_NOMINAL_MAGNETOPAUSE,
    REGIME_INTERNAL_ONLY,
    REGIME_INTERNAL_PLUS_EXTERNAL,
    classify_field_model_regime,
    classify_magnetopause_position,
    field_model_source_selection,
    magnetopause_standoff_re,
    required_igrf_degree,
    select_external_model,
    validate_igrf_epoch,
)


class ClassifyFieldModelRegimeTests(unittest.TestCase):
    def test_low_altitude_is_internal_only(self):
        self.assertEqual(classify_field_model_regime(500.0), REGIME_INTERNAL_ONLY)

    def test_internal_only_upper_boundary_inclusive(self):
        altitude_at_2re = EARTH_RADIUS_KM * 1.0
        self.assertEqual(
            classify_field_model_regime(altitude_at_2re), REGIME_INTERNAL_ONLY
        )

    def test_just_above_internal_only_boundary_is_internal_plus_external(self):
        altitude_just_above_2re = EARTH_RADIUS_KM * 1.0 + 1.0
        self.assertEqual(
            classify_field_model_regime(altitude_just_above_2re),
            REGIME_INTERNAL_PLUS_EXTERNAL,
        )

    def test_external_required_upper_boundary_inclusive(self):
        altitude_at_10re = EARTH_RADIUS_KM * 9.0
        self.assertEqual(
            classify_field_model_regime(altitude_at_10re),
            REGIME_INTERNAL_PLUS_EXTERNAL,
        )

    def test_just_above_external_boundary_is_beyond_nominal_magnetopause(self):
        altitude_just_above_10re = EARTH_RADIUS_KM * 9.0 + 1.0
        self.assertEqual(
            classify_field_model_regime(altitude_just_above_10re),
            REGIME_BEYOND_NOMINAL_MAGNETOPAUSE,
        )

    def test_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            classify_field_model_regime(-1.0)


class RequiredIgrfDegreeTests(unittest.TestCase):
    def test_below_1000km_is_full_degree(self):
        self.assertEqual(required_igrf_degree(500.0), 13)

    def test_at_1000km_boundary_inclusive(self):
        self.assertEqual(required_igrf_degree(1000.0), 13)

    def test_just_above_1000km_drops_to_10(self):
        self.assertEqual(required_igrf_degree(1000.1), 10)

    def test_at_6000km_boundary_inclusive(self):
        self.assertEqual(required_igrf_degree(6000.0), 10)

    def test_just_above_6000km_drops_to_8(self):
        self.assertEqual(required_igrf_degree(6000.1), 8)

    def test_at_20000km_boundary_inclusive(self):
        self.assertEqual(required_igrf_degree(20000.0), 8)

    def test_beyond_20000km_drops_to_4(self):
        self.assertEqual(required_igrf_degree(35786.0), 4)

    def test_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            required_igrf_degree(-1.0)


class ValidateIgrfEpochTests(unittest.TestCase):
    def test_within_definitive_window(self):
        result = validate_igrf_epoch(2022, 2020)
        self.assertEqual(result["status"], EPOCH_STATUS_DEFINITIVE)
        self.assertEqual(result["years_since_generation_epoch"], 2)

    def test_at_generation_epoch_is_definitive(self):
        result = validate_igrf_epoch(2020, 2020)
        self.assertEqual(result["status"], EPOCH_STATUS_DEFINITIVE)

    def test_at_predictive_boundary(self):
        result = validate_igrf_epoch(2025, 2020)
        self.assertEqual(result["status"], EPOCH_STATUS_PREDICTIVE)

    def test_within_predictive_window(self):
        result = validate_igrf_epoch(2029, 2020)
        self.assertEqual(result["status"], EPOCH_STATUS_PREDICTIVE)

    def test_at_stale_boundary(self):
        result = validate_igrf_epoch(2030, 2020)
        self.assertEqual(result["status"], EPOCH_STATUS_STALE)

    def test_invalid_generation_epoch_not_on_cadence_raises(self):
        with self.assertRaises(ValueError):
            validate_igrf_epoch(2022, 2021)

    def test_generation_epoch_before_1900_raises(self):
        with self.assertRaises(ValueError):
            validate_igrf_epoch(1899, 1895)

    def test_epoch_year_before_generation_epoch_raises(self):
        with self.assertRaises(ValueError):
            validate_igrf_epoch(2019, 2020)


class SelectExternalModelTests(unittest.TestCase):
    def test_quiet_conditions_select_t89(self):
        self.assertEqual(select_external_model(1.0)["model"], "T89")

    def test_quiet_boundary_inclusive(self):
        self.assertEqual(select_external_model(2.0)["model"], "T89")

    def test_moderate_conditions_select_t96(self):
        self.assertEqual(select_external_model(3.0)["model"], "T96")

    def test_moderate_boundary_inclusive(self):
        self.assertEqual(select_external_model(4.0)["model"], "T96")

    def test_active_conditions_select_t01(self):
        self.assertEqual(select_external_model(5.0)["model"], "T01")

    def test_active_boundary_inclusive(self):
        self.assertEqual(select_external_model(6.0)["model"], "T01")

    def test_storm_conditions_select_t04(self):
        result = select_external_model(9.0)
        self.assertEqual(result["model"], "T04")
        self.assertIn("sym_h_index_nt", result["required_inputs"])

    def test_below_range_raises(self):
        with self.assertRaises(ValueError):
            select_external_model(-0.1)

    def test_above_range_raises(self):
        with self.assertRaises(ValueError):
            select_external_model(9.1)


class MagnetopauseTests(unittest.TestCase):
    def test_standoff_at_reference_pressure_is_nominal(self):
        self.assertEqual(
            magnetopause_standoff_re(REFERENCE_DYNAMIC_PRESSURE_NPA),
            NOMINAL_MAGNETOPAUSE_STANDOFF_RE,
        )

    def test_higher_pressure_compresses_standoff(self):
        standoff = magnetopause_standoff_re(REFERENCE_DYNAMIC_PRESSURE_NPA * 4)
        self.assertLess(standoff, NOMINAL_MAGNETOPAUSE_STANDOFF_RE)

    def test_lower_pressure_expands_standoff(self):
        standoff = magnetopause_standoff_re(REFERENCE_DYNAMIC_PRESSURE_NPA / 4)
        self.assertGreater(standoff, NOMINAL_MAGNETOPAUSE_STANDOFF_RE)

    def test_nonpositive_pressure_raises(self):
        with self.assertRaises(ValueError):
            magnetopause_standoff_re(0.0)

    def test_position_inside_magnetopause(self):
        self.assertEqual(
            classify_magnetopause_position(5.0, REFERENCE_DYNAMIC_PRESSURE_NPA),
            POSITION_INSIDE_MAGNETOPAUSE,
        )

    def test_position_at_standoff_is_outside_or_at(self):
        self.assertEqual(
            classify_magnetopause_position(
                NOMINAL_MAGNETOPAUSE_STANDOFF_RE, REFERENCE_DYNAMIC_PRESSURE_NPA
            ),
            POSITION_OUTSIDE_OR_AT_MAGNETOPAUSE,
        )

    def test_position_beyond_standoff_is_outside(self):
        self.assertEqual(
            classify_magnetopause_position(20.0, REFERENCE_DYNAMIC_PRESSURE_NPA),
            POSITION_OUTSIDE_OR_AT_MAGNETOPAUSE,
        )

    def test_nonpositive_radial_distance_raises(self):
        with self.assertRaises(ValueError):
            classify_magnetopause_position(0.0, REFERENCE_DYNAMIC_PRESSURE_NPA)


class FieldModelSourceSelectionTests(unittest.TestCase):
    def test_internal_only_regime_has_no_external_model(self):
        result = field_model_source_selection(500.0, kp_index=1.0)
        self.assertEqual(result["regime"], REGIME_INTERNAL_ONLY)
        self.assertIsNone(result["external_model"])
        self.assertIsNone(result["magnetopause_position"])
        self.assertEqual(result["igrf_degree"], 13)

    def test_internal_plus_external_regime_selects_external_model(self):
        result = field_model_source_selection(20000.0, kp_index=3.0)
        self.assertEqual(result["regime"], REGIME_INTERNAL_PLUS_EXTERNAL)
        self.assertEqual(result["external_model"]["model"], "T96")
        self.assertIsNone(result["magnetopause_position"])

    def test_beyond_nominal_magnetopause_requires_pressure(self):
        with self.assertRaises(ValueError):
            field_model_source_selection(100000.0, kp_index=1.0)

    def test_beyond_nominal_magnetopause_with_pressure_classifies_position(self):
        result = field_model_source_selection(
            100000.0, kp_index=1.0, dynamic_pressure_npa=REFERENCE_DYNAMIC_PRESSURE_NPA
        )
        self.assertEqual(result["regime"], REGIME_BEYOND_NOMINAL_MAGNETOPAUSE)
        self.assertEqual(result["external_model"]["model"], "T89")
        self.assertEqual(
            result["magnetopause_position"], POSITION_OUTSIDE_OR_AT_MAGNETOPAUSE
        )

    def test_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            field_model_source_selection(-1.0, kp_index=1.0)


if __name__ == "__main__":
    result = unittest.main(exit=False)
    if result.result.wasSuccessful():
        print("OK")
    else:
        raise SystemExit(1)
