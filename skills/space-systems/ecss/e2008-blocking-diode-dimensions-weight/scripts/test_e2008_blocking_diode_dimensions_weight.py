"""Contract tests for the clause 12.6.2 blocking diode dimensions logic."""

import unittest

from e2008_blocking_diode_dimensions_weight_logic import (
    BLOCKING_DIODE_ATTACHMENT_OUT_OF_POSITION,
    BLOCKING_DIODE_DIMENSIONS_CONFORMING,
    BLOCKING_DIODE_KEEP_OUT_EXCEEDED,
    BLOCKING_DIODE_MASS_INCONSISTENT,
    BLOCKING_DIODE_OUTLINE_OUT_OF_BAND,
    BLOCKING_DIODE_TERMINAL_GEOMETRY_INADEQUATE,
    DEFAULT_BLOCKING_DIODE_DIMENSION_POLICY,
    STATE_IN_BAND,
    STATE_OVER_BAND,
    STATE_UNDER_BAND,
    TERMINALS,
    assess_blocking_diode_dimensions,
    band_limits,
    combined_terminal_coverage,
    deviation_fraction,
    feature_state,
    footprint_area_mm2,
    implied_mass_mg,
    keep_out_envelope_mm,
    mass_deviation_fraction,
    terminal_coverage_fraction,
    terminal_current_density,
    true_position_diameter_mm,
    validate_blocking_diode_dimension_policy,
    worst_true_position_mm,
)


def _policy(**overrides):
    policy = dict(DEFAULT_BLOCKING_DIODE_DIMENSION_POLICY)
    policy.update(overrides)
    return policy


def _drawing(**overrides):
    drawing = {
        "length_mm": {"nominal": 12.0, "minus_tol": 0.15, "plus_tol": 0.15},
        "width_mm": {"nominal": 6.0, "minus_tol": 0.15, "plus_tol": 0.15},
        "thickness_mm": {"nominal": 0.30, "minus_tol": 0.03, "plus_tol": 0.03},
        "material_density_g_cm3": 2.33,
        "keep_out_length_mm": 12.8,
        "keep_out_width_mm": 6.8,
    }
    drawing.update(overrides)
    return drawing


def _measured(**overrides):
    measured = {
        "length_mm": 12.04,
        "width_mm": 5.97,
        "thickness_mm": 0.30,
        "mass_mg": 50.2,
        "terminal_pad_area_mm2": {"anode": 14.0, "cathode": 12.0},
        "interconnector_offsets_mm": [[0.03, 0.04], [0.02, -0.01]],
    }
    measured.update(overrides)
    return measured


def _case(**overrides):
    case = {
        "drawing": _drawing(),
        "measured": _measured(),
        "duty": {"string_current_a": 3.0},
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_blocking_diode_dimension_policy(
                DEFAULT_BLOCKING_DIODE_DIMENSION_POLICY
            ),
            DEFAULT_BLOCKING_DIODE_DIMENSION_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocking_diode_dimension_policy("coverage")

    def test_coverage_floor_above_full_coverage_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocking_diode_dimension_policy(
                _policy(min_terminal_coverage_fraction=1.3)
            )

    def test_zero_coverage_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocking_diode_dimension_policy(
                _policy(min_terminal_coverage_fraction=0.0)
            )

    def test_zero_current_density_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocking_diode_dimension_policy(
                _policy(max_terminal_current_density_a_per_mm2=0.0)
            )

    def test_a_mass_tolerance_admitting_any_part_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocking_diode_dimension_policy(
                _policy(max_mass_deviation_fraction=1.0)
            )

    def test_negative_true_position_zone_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocking_diode_dimension_policy(
                _policy(max_true_position_diameter_mm=-0.1)
            )


class BandTests(unittest.TestCase):
    def test_band_limits_sit_either_side_of_the_nominal(self):
        low, high = band_limits(12.0, 0.15, 0.15)
        self.assertAlmostEqual(low, 11.85, places=9)
        self.assertAlmostEqual(high, 12.15, places=9)

    def test_an_asymmetric_band_keeps_its_two_tolerances(self):
        low, high = band_limits(12.0, 0.05, 0.3)
        self.assertAlmostEqual(low, 11.95, places=9)
        self.assertAlmostEqual(high, 12.3, places=9)

    def test_a_measurement_inside_the_band_is_in_band(self):
        self.assertEqual(feature_state(12.04, 12.0, 0.15, 0.15), STATE_IN_BAND)

    def test_a_measurement_on_the_low_limit_is_in_band(self):
        self.assertEqual(feature_state(11.85, 12.0, 0.15, 0.15), STATE_IN_BAND)

    def test_a_measurement_on_the_high_limit_is_in_band(self):
        self.assertEqual(feature_state(12.15, 12.0, 0.15, 0.15), STATE_IN_BAND)

    def test_a_limit_the_subtraction_cannot_represent_is_still_in_band(self):
        # 0.30 - 0.03 does not land on 0.27 in binary; the band must not
        # reject a part that measures the limit the drawing wrote.
        self.assertEqual(feature_state(0.27, 0.30, 0.03, 0.03), STATE_IN_BAND)
        self.assertEqual(feature_state(0.33, 0.30, 0.03, 0.03), STATE_IN_BAND)

    def test_a_measurement_below_the_band_is_under_band(self):
        self.assertEqual(feature_state(11.4, 12.0, 0.15, 0.15), STATE_UNDER_BAND)

    def test_a_measurement_above_the_band_is_over_band(self):
        self.assertEqual(feature_state(12.6, 12.0, 0.15, 0.15), STATE_OVER_BAND)

    def test_a_minus_tolerance_swallowing_the_nominal_rejected(self):
        with self.assertRaises(ValueError):
            band_limits(0.30, 0.30, 0.03)

    def test_a_boolean_measurement_rejected(self):
        with self.assertRaises(ValueError):
            feature_state(True, 12.0, 0.15, 0.15)

    def test_a_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            band_limits(12.0, -0.1, 0.15)

    def test_deviation_is_signed_against_the_nominal(self):
        self.assertAlmostEqual(deviation_fraction(13.2, 12.0), 0.1, places=9)
        self.assertAlmostEqual(deviation_fraction(10.8, 12.0), -0.1, places=9)


class TerminalGeometryTests(unittest.TestCase):
    def test_footprint_is_the_product_of_the_lateral_dimensions(self):
        self.assertAlmostEqual(footprint_area_mm2(12.0, 6.0), 72.0, places=9)

    def test_coverage_is_the_pad_share_of_the_footprint(self):
        self.assertAlmostEqual(terminal_coverage_fraction(18.0, 72.0), 0.25, places=9)

    def test_a_pad_filling_the_footprint_is_full_coverage(self):
        self.assertAlmostEqual(terminal_coverage_fraction(72.0, 72.0), 1.0, places=9)

    def test_a_pad_larger_than_the_footprint_rejected(self):
        with self.assertRaises(ValueError):
            terminal_coverage_fraction(80.0, 72.0)

    def test_both_terminals_are_summed_into_one_combined_coverage(self):
        combined = combined_terminal_coverage(
            {"anode": 18.0, "cathode": 18.0}, 72.0
        )
        self.assertAlmostEqual(combined, 0.5, places=9)

    def test_two_pads_that_cannot_both_fit_are_rejected(self):
        with self.assertRaises(ValueError):
            combined_terminal_coverage({"anode": 40.0, "cathode": 40.0}, 72.0)

    def test_a_missing_terminal_pad_rejected(self):
        with self.assertRaises(ValueError):
            combined_terminal_coverage({"anode": 18.0}, 72.0)

    def test_current_density_is_the_string_current_over_the_pad(self):
        self.assertAlmostEqual(terminal_current_density(3.0, 12.0), 0.25, places=9)

    def test_a_smaller_pad_raises_the_current_density(self):
        self.assertGreater(
            terminal_current_density(3.0, 2.0), terminal_current_density(3.0, 12.0)
        )

    def test_zero_pad_area_rejected(self):
        with self.assertRaises(ValueError):
            terminal_current_density(3.0, 0.0)

    def test_negative_string_current_rejected(self):
        with self.assertRaises(ValueError):
            terminal_current_density(-3.0, 12.0)

    def test_both_terminals_are_named(self):
        self.assertEqual(sorted(TERMINALS), ["anode", "cathode"])


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
        # 0.12 on each axis is inside a 0.125 per-axis check, and still needs
        # a zone of about 0.339 mm once the axes are combined.
        self.assertGreater(true_position_diameter_mm(0.12, 0.12), 0.33)

    def test_the_worst_attachment_point_sets_the_value(self):
        worst = worst_true_position_mm([[0.01, 0.0], [0.03, 0.04], [0.0, 0.02]])
        self.assertAlmostEqual(worst, 0.1, places=9)

    def test_an_empty_offset_list_rejected(self):
        with self.assertRaises(ValueError):
            worst_true_position_mm([])

    def test_a_non_pair_offset_rejected(self):
        with self.assertRaises(ValueError):
            worst_true_position_mm([[0.01, 0.0, 0.0]])

    def test_a_non_sequence_offset_set_rejected(self):
        with self.assertRaises(ValueError):
            worst_true_position_mm("0.01,0.0")


class KeepOutEnvelopeTests(unittest.TestCase):
    def test_the_envelope_grows_the_outline_by_the_placement_zone(self):
        length, width = keep_out_envelope_mm(12.0, 6.0, 0.2)
        self.assertAlmostEqual(length, 12.2, places=9)
        self.assertAlmostEqual(width, 6.2, places=9)

    def test_a_perfectly_placed_part_needs_only_its_own_outline(self):
        length, width = keep_out_envelope_mm(12.0, 6.0, 0.0)
        self.assertAlmostEqual(length, 12.0, places=9)
        self.assertAlmostEqual(width, 6.0, places=9)

    def test_a_negative_placement_zone_rejected(self):
        with self.assertRaises(ValueError):
            keep_out_envelope_mm(12.0, 6.0, -0.1)


class MassTests(unittest.TestCase):
    def test_a_unit_density_block_weighs_its_volume(self):
        self.assertAlmostEqual(implied_mass_mg(2.0, 3.0, 4.0, 1.0), 24.0, places=9)

    def test_implied_mass_follows_the_material_density(self):
        self.assertAlmostEqual(
            implied_mass_mg(12.0, 6.0, 0.3, 2.33), 72.0 * 0.3 * 2.33, places=9
        )

    def test_mass_deviation_is_signed_against_the_implied_mass(self):
        self.assertAlmostEqual(mass_deviation_fraction(21.0, 20.0), 0.05, places=9)

    def test_a_light_part_gives_a_negative_deviation(self):
        self.assertAlmostEqual(mass_deviation_fraction(19.0, 20.0), -0.05, places=9)

    def test_zero_material_density_rejected(self):
        with self.assertRaises(ValueError):
            implied_mass_mg(12.0, 6.0, 0.3, 0.0)


class AssessmentTests(unittest.TestCase):
    def test_a_conforming_sheet_passes_with_no_findings(self):
        result = assess_blocking_diode_dimensions(_case())
        self.assertEqual(result["verdict"], BLOCKING_DIODE_DIMENSIONS_CONFORMING)
        self.assertEqual(result["findings"], [])

    def test_every_feature_state_is_reported(self):
        result = assess_blocking_diode_dimensions(_case())
        self.assertEqual(
            sorted(result["feature_states"]),
            ["length_mm", "thickness_mm", "width_mm"],
        )

    def test_a_long_diode_is_outline_out_of_band(self):
        result = assess_blocking_diode_dimensions(
            _case(measured=_measured(length_mm=12.6, mass_mg=52.5))
        )
        self.assertEqual(result["verdict"], BLOCKING_DIODE_OUTLINE_OUT_OF_BAND)
        self.assertEqual(result["feature_states"]["length_mm"], STATE_OVER_BAND)

    def test_a_thin_diode_is_named_under_band(self):
        result = assess_blocking_diode_dimensions(
            _case(measured=_measured(thickness_mm=0.24, mass_mg=40.2))
        )
        self.assertEqual(result["verdict"], BLOCKING_DIODE_OUTLINE_OUT_OF_BAND)
        self.assertEqual(result["feature_states"]["thickness_mm"], STATE_UNDER_BAND)

    def test_an_undersized_pad_is_a_terminal_geometry_problem(self):
        result = assess_blocking_diode_dimensions(
            _case(
                measured=_measured(
                    terminal_pad_area_mm2={"anode": 14.0, "cathode": 4.0}
                )
            )
        )
        self.assertEqual(
            result["verdict"], BLOCKING_DIODE_TERMINAL_GEOMETRY_INADEQUATE
        )
        self.assertFalse(result["terminal_geometry_met"])

    def test_a_generous_anode_does_not_excuse_a_starved_cathode(self):
        result = assess_blocking_diode_dimensions(
            _case(
                measured=_measured(
                    terminal_pad_area_mm2={"anode": 40.0, "cathode": 4.0}
                )
            )
        )
        self.assertEqual(
            result["verdict"], BLOCKING_DIODE_TERMINAL_GEOMETRY_INADEQUATE
        )
        self.assertGreater(
            result["terminal_coverage_fraction"]["anode"],
            result["terminal_coverage_fraction"]["cathode"],
        )

    def test_a_pad_that_cannot_carry_the_string_current_is_inadequate(self):
        result = assess_blocking_diode_dimensions(
            _case(duty={"string_current_a": 30.0})
        )
        self.assertEqual(
            result["verdict"], BLOCKING_DIODE_TERMINAL_GEOMETRY_INADEQUATE
        )
        self.assertFalse(result["terminal_geometry_met"])

    def test_both_terminals_are_reported_with_their_density(self):
        result = assess_blocking_diode_dimensions(_case())
        self.assertEqual(
            sorted(result["terminal_current_density_a_per_mm2"]),
            ["anode", "cathode"],
        )

    def test_an_attachment_outside_the_zone_is_out_of_position(self):
        result = assess_blocking_diode_dimensions(
            _case(measured=_measured(interconnector_offsets_mm=[[0.2, 0.2]]))
        )
        self.assertEqual(
            result["verdict"], BLOCKING_DIODE_ATTACHMENT_OUT_OF_POSITION
        )
        self.assertFalse(result["true_position_met"])

    def test_an_in_band_part_can_still_burst_the_keep_out(self):
        result = assess_blocking_diode_dimensions(
            _case(drawing=_drawing(keep_out_length_mm=12.1))
        )
        self.assertEqual(result["verdict"], BLOCKING_DIODE_KEEP_OUT_EXCEEDED)
        self.assertFalse(result["keep_out_envelope_met"])

    def test_the_envelope_is_grown_from_the_measured_outline(self):
        result = assess_blocking_diode_dimensions(_case())
        self.assertAlmostEqual(
            _ratio(result["keep_out_envelope_mm"][0], 12.04 + 0.1), 1.0, places=9
        )

    def test_a_mass_disagreeing_with_the_geometry_is_inconsistent(self):
        result = assess_blocking_diode_dimensions(
            _case(measured=_measured(mass_mg=80.0))
        )
        self.assertEqual(result["verdict"], BLOCKING_DIODE_MASS_INCONSISTENT)
        self.assertFalse(result["mass_consistent"])

    def test_the_implied_mass_is_derived_from_the_measured_outline(self):
        result = assess_blocking_diode_dimensions(_case())
        self.assertAlmostEqual(
            _ratio(result["implied_mass_mg"], 12.04 * 5.97 * 0.30 * 2.33),
            1.0,
            places=12,
        )

    def test_every_inadequacy_is_reported_not_only_the_first(self):
        result = assess_blocking_diode_dimensions(
            _case(
                measured=_measured(
                    length_mm=12.6,
                    terminal_pad_area_mm2={"anode": 4.0, "cathode": 4.0},
                    interconnector_offsets_mm=[[0.3, 0.3]],
                    mass_mg=90.0,
                )
            )
        )
        self.assertEqual(result["verdict"], BLOCKING_DIODE_OUTLINE_OUT_OF_BAND)
        self.assertGreaterEqual(len(result["findings"]), 5)

    def test_a_missing_drawing_block_rejected(self):
        case = _case()
        del case["drawing"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_dimensions(case)

    def test_a_missing_duty_block_rejected(self):
        case = _case()
        del case["duty"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_dimensions(case)

    def test_a_missing_measured_feature_rejected(self):
        measured = _measured()
        del measured["thickness_mm"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_dimensions(_case(measured=measured))

    def test_a_missing_drawn_band_rejected(self):
        drawing = _drawing()
        del drawing["width_mm"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_dimensions(_case(drawing=drawing))

    def test_a_missing_keep_out_reservation_rejected(self):
        drawing = _drawing()
        del drawing["keep_out_width_mm"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_dimensions(_case(drawing=drawing))

    def test_a_missing_terminal_pad_block_rejected(self):
        measured = _measured()
        del measured["terminal_pad_area_mm2"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_dimensions(_case(measured=measured))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_dimensions(["length_mm"])


if __name__ == "__main__":
    unittest.main()
