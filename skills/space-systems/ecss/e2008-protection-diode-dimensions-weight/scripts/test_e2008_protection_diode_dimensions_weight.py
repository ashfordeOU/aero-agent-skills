"""Contract tests for the clause 9.6.3 protection diode dimensions logic."""

import unittest

from e2008_protection_diode_dimensions_weight_logic import (
    DEFAULT_DIMENSION_POLICY,
    DIODE_ATTACHMENT_OUT_OF_POSITION,
    DIODE_CONTACT_GEOMETRY_INADEQUATE,
    DIODE_DIMENSIONS_CONFORMING,
    DIODE_MASS_INCONSISTENT,
    DIODE_OUTLINE_OUT_OF_BAND,
    STATE_IN_BAND,
    STATE_OVER_BAND,
    STATE_UNDER_BAND,
    assess_protection_diode_dimensions,
    band_limits,
    contact_coverage_fraction,
    contact_current_density,
    deviation_fraction,
    feature_state,
    footprint_area_mm2,
    implied_mass_mg,
    mass_deviation_fraction,
    true_position_diameter_mm,
    validate_dimension_policy,
    worst_true_position_mm,
)


def _policy(**overrides):
    policy = dict(DEFAULT_DIMENSION_POLICY)
    policy.update(overrides)
    return policy


def _drawing(**overrides):
    drawing = {
        "length_mm": {"nominal": 9.0, "minus_tol": 0.1, "plus_tol": 0.1},
        "width_mm": {"nominal": 7.0, "minus_tol": 0.1, "plus_tol": 0.1},
        "thickness_mm": {"nominal": 0.18, "minus_tol": 0.02, "plus_tol": 0.02},
        "material_density_g_cm3": 2.33,
    }
    drawing.update(overrides)
    return drawing


def _measured(**overrides):
    measured = {
        "length_mm": 9.02,
        "width_mm": 6.98,
        "thickness_mm": 0.18,
        "mass_mg": 26.4,
        "contact_pad_area_mm2": 12.0,
        "interconnector_offsets_mm": [[0.02, 0.01], [0.03, -0.02]],
    }
    measured.update(overrides)
    return measured


def _case(**overrides):
    case = {
        "drawing": _drawing(),
        "measured": _measured(),
        "duty": {"string_current_a": 2.5},
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_dimension_policy(DEFAULT_DIMENSION_POLICY),
            DEFAULT_DIMENSION_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_dimension_policy("coverage")

    def test_coverage_floor_above_full_coverage_rejected(self):
        with self.assertRaises(ValueError):
            validate_dimension_policy(_policy(min_contact_coverage_fraction=1.4))

    def test_zero_current_density_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_dimension_policy(
                _policy(max_contact_current_density_a_per_mm2=0.0)
            )

    def test_a_mass_tolerance_admitting_any_part_rejected(self):
        with self.assertRaises(ValueError):
            validate_dimension_policy(_policy(max_mass_deviation_fraction=1.0))

    def test_negative_true_position_zone_rejected(self):
        with self.assertRaises(ValueError):
            validate_dimension_policy(_policy(max_true_position_diameter_mm=-0.1))


class BandTests(unittest.TestCase):
    def test_band_limits_sit_either_side_of_the_nominal(self):
        low, high = band_limits(9.0, 0.1, 0.1)
        self.assertAlmostEqual(low, 8.9, places=9)
        self.assertAlmostEqual(high, 9.1, places=9)

    def test_an_asymmetric_band_keeps_its_two_tolerances(self):
        low, high = band_limits(9.0, 0.05, 0.2)
        self.assertAlmostEqual(low, 8.95, places=9)
        self.assertAlmostEqual(high, 9.2, places=9)

    def test_a_measurement_inside_the_band_is_in_band(self):
        self.assertEqual(feature_state(9.02, 9.0, 0.1, 0.1), STATE_IN_BAND)

    def test_a_measurement_on_the_low_limit_is_in_band(self):
        self.assertEqual(feature_state(8.9, 9.0, 0.1, 0.1), STATE_IN_BAND)

    def test_a_measurement_on_the_high_limit_is_in_band(self):
        self.assertEqual(feature_state(9.1, 9.0, 0.1, 0.1), STATE_IN_BAND)

    def test_a_limit_the_subtraction_cannot_represent_is_still_in_band(self):
        # 0.18 - 0.02 does not land on 0.16 in binary; the band must not
        # reject a part that measures the limit the drawing wrote.
        self.assertEqual(feature_state(0.16, 0.18, 0.02, 0.02), STATE_IN_BAND)

    def test_a_measurement_below_the_band_is_under_band(self):
        self.assertEqual(feature_state(8.5, 9.0, 0.1, 0.1), STATE_UNDER_BAND)

    def test_a_measurement_above_the_band_is_over_band(self):
        self.assertEqual(feature_state(9.4, 9.0, 0.1, 0.1), STATE_OVER_BAND)

    def test_a_minus_tolerance_swallowing_the_nominal_rejected(self):
        with self.assertRaises(ValueError):
            band_limits(0.18, 0.18, 0.02)

    def test_a_boolean_measurement_rejected(self):
        with self.assertRaises(ValueError):
            feature_state(True, 9.0, 0.1, 0.1)

    def test_deviation_is_signed_against_the_nominal(self):
        self.assertAlmostEqual(deviation_fraction(9.9, 9.0), 0.1, places=9)
        self.assertAlmostEqual(deviation_fraction(8.1, 9.0), -0.1, places=9)


class ContactGeometryTests(unittest.TestCase):
    def test_footprint_is_the_product_of_the_lateral_dimensions(self):
        self.assertAlmostEqual(footprint_area_mm2(9.0, 7.0), 63.0, places=9)

    def test_coverage_is_the_pad_share_of_the_footprint(self):
        self.assertAlmostEqual(contact_coverage_fraction(12.6, 63.0), 0.2, places=9)

    def test_a_pad_filling_the_footprint_is_full_coverage(self):
        self.assertAlmostEqual(contact_coverage_fraction(63.0, 63.0), 1.0, places=9)

    def test_a_pad_larger_than_the_footprint_rejected(self):
        with self.assertRaises(ValueError):
            contact_coverage_fraction(70.0, 63.0)

    def test_current_density_is_the_current_over_the_pad(self):
        self.assertAlmostEqual(contact_current_density(2.5, 12.5), 0.2, places=9)

    def test_a_smaller_pad_raises_the_current_density(self):
        self.assertGreater(
            contact_current_density(2.5, 2.0), contact_current_density(2.5, 12.5)
        )

    def test_zero_pad_area_rejected(self):
        with self.assertRaises(ValueError):
            contact_current_density(2.5, 0.0)

    def test_negative_string_current_rejected(self):
        with self.assertRaises(ValueError):
            contact_current_density(-2.5, 12.5)


class TruePositionTests(unittest.TestCase):
    def test_the_zone_is_twice_the_radial_offset(self):
        self.assertAlmostEqual(true_position_diameter_mm(0.03, 0.04), 0.1, places=9)

    def test_a_point_on_nominal_needs_no_zone(self):
        self.assertAlmostEqual(true_position_diameter_mm(0.0, 0.0), 0.0, places=12)

    def test_the_sign_of_an_offset_does_not_change_the_zone(self):
        self.assertAlmostEqual(
            _ratio(
                true_position_diameter_mm(-0.03, -0.04),
                true_position_diameter_mm(0.03, 0.04),
            ),
            1.0,
            places=12,
        )

    def test_two_in_band_axes_can_still_need_a_larger_zone(self):
        # 0.09 on each axis is inside a 0.1 per-axis check, and still needs
        # a zone of 0.254 mm once the axes are combined.
        self.assertGreater(true_position_diameter_mm(0.09, 0.09), 0.25)

    def test_the_worst_attachment_point_sets_the_value(self):
        worst = worst_true_position_mm([[0.01, 0.0], [0.03, 0.04], [0.0, 0.02]])
        self.assertAlmostEqual(worst, 0.1, places=9)

    def test_an_empty_offset_list_rejected(self):
        with self.assertRaises(ValueError):
            worst_true_position_mm([])

    def test_a_non_pair_offset_rejected(self):
        with self.assertRaises(ValueError):
            worst_true_position_mm([[0.01, 0.0, 0.0]])


class MassTests(unittest.TestCase):
    def test_a_unit_density_block_weighs_its_volume(self):
        self.assertAlmostEqual(implied_mass_mg(2.0, 3.0, 4.0, 1.0), 24.0, places=9)

    def test_implied_mass_follows_the_material_density(self):
        self.assertAlmostEqual(
            implied_mass_mg(9.0, 7.0, 0.2, 2.33), 63.0 * 0.2 * 2.33, places=9
        )

    def test_mass_deviation_is_signed_against_the_implied_mass(self):
        self.assertAlmostEqual(mass_deviation_fraction(21.0, 20.0), 0.05, places=9)

    def test_a_light_part_gives_a_negative_deviation(self):
        self.assertAlmostEqual(mass_deviation_fraction(19.0, 20.0), -0.05, places=9)

    def test_zero_material_density_rejected(self):
        with self.assertRaises(ValueError):
            implied_mass_mg(9.0, 7.0, 0.2, 0.0)


class AssessmentTests(unittest.TestCase):
    def test_a_conforming_sheet_passes_with_no_findings(self):
        result = assess_protection_diode_dimensions(_case())
        self.assertEqual(result["verdict"], DIODE_DIMENSIONS_CONFORMING)
        self.assertEqual(result["findings"], [])

    def test_every_feature_state_is_reported(self):
        result = assess_protection_diode_dimensions(_case())
        self.assertEqual(
            sorted(result["feature_states"]), ["length_mm", "thickness_mm", "width_mm"]
        )

    def test_a_long_diode_is_outline_out_of_band(self):
        result = assess_protection_diode_dimensions(
            _case(measured=_measured(length_mm=9.4))
        )
        self.assertEqual(result["verdict"], DIODE_OUTLINE_OUT_OF_BAND)
        self.assertEqual(result["feature_states"]["length_mm"], STATE_OVER_BAND)

    def test_a_thin_diode_is_named_under_band(self):
        result = assess_protection_diode_dimensions(
            _case(measured=_measured(thickness_mm=0.14, mass_mg=20.5))
        )
        self.assertEqual(result["verdict"], DIODE_OUTLINE_OUT_OF_BAND)
        self.assertEqual(result["feature_states"]["thickness_mm"], STATE_UNDER_BAND)

    def test_an_undersized_pad_is_a_contact_geometry_problem(self):
        result = assess_protection_diode_dimensions(
            _case(measured=_measured(contact_pad_area_mm2=4.0))
        )
        self.assertEqual(result["verdict"], DIODE_CONTACT_GEOMETRY_INADEQUATE)
        self.assertFalse(result["contact_coverage_met"])

    def test_a_pad_that_cannot_carry_the_string_current_is_inadequate(self):
        result = assess_protection_diode_dimensions(
            _case(
                measured=_measured(contact_pad_area_mm2=10.0),
                duty={"string_current_a": 40.0},
            )
        )
        self.assertEqual(result["verdict"], DIODE_CONTACT_GEOMETRY_INADEQUATE)
        self.assertFalse(result["contact_current_density_met"])

    def test_an_attachment_outside_the_zone_is_out_of_position(self):
        result = assess_protection_diode_dimensions(
            _case(measured=_measured(interconnector_offsets_mm=[[0.2, 0.2]]))
        )
        self.assertEqual(result["verdict"], DIODE_ATTACHMENT_OUT_OF_POSITION)
        self.assertFalse(result["true_position_met"])

    def test_a_mass_disagreeing_with_the_geometry_is_inconsistent(self):
        result = assess_protection_diode_dimensions(
            _case(measured=_measured(mass_mg=40.0))
        )
        self.assertEqual(result["verdict"], DIODE_MASS_INCONSISTENT)
        self.assertFalse(result["mass_consistent"])

    def test_the_implied_mass_is_derived_from_the_measured_outline(self):
        result = assess_protection_diode_dimensions(_case())
        self.assertAlmostEqual(
            _ratio(result["implied_mass_mg"], 9.02 * 6.98 * 0.18 * 2.33),
            1.0,
            places=12,
        )

    def test_every_inadequacy_is_reported_not_only_the_first(self):
        result = assess_protection_diode_dimensions(
            _case(
                measured=_measured(
                    length_mm=9.4,
                    contact_pad_area_mm2=4.0,
                    interconnector_offsets_mm=[[0.2, 0.2]],
                    mass_mg=40.0,
                )
            )
        )
        self.assertEqual(result["verdict"], DIODE_OUTLINE_OUT_OF_BAND)
        self.assertGreaterEqual(len(result["findings"]), 4)

    def test_a_missing_drawing_block_rejected(self):
        case = _case()
        del case["drawing"]
        with self.assertRaises(ValueError):
            assess_protection_diode_dimensions(case)

    def test_a_missing_duty_block_rejected(self):
        case = _case()
        del case["duty"]
        with self.assertRaises(ValueError):
            assess_protection_diode_dimensions(case)

    def test_a_missing_measured_feature_rejected(self):
        measured = _measured()
        del measured["thickness_mm"]
        with self.assertRaises(ValueError):
            assess_protection_diode_dimensions(_case(measured=measured))

    def test_a_missing_drawn_band_rejected(self):
        drawing = _drawing()
        del drawing["width_mm"]
        with self.assertRaises(ValueError):
            assess_protection_diode_dimensions(_case(drawing=drawing))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_protection_diode_dimensions(["length_mm"])


if __name__ == "__main__":
    unittest.main()
