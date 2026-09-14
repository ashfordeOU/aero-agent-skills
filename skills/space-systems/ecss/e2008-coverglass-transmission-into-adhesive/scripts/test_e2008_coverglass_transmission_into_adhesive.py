"""Contract tests for the clause 8.7.9 coverglass transmission-into-adhesive reduction."""

import unittest

from e2008_coverglass_transmission_into_adhesive_logic import (
    AVERAGE_BELOW_REQUIREMENT,
    AVERAGE_MEETS_REQUIREMENT,
    BACKING_NOT_QUALIFIED,
    BAND_NOT_COVERED,
    BASELINE_NOT_REFERENCED,
    BOND_NOT_VOID_FREE,
    DEFAULT_STACK_POLICY,
    GAIN_NOT_PHYSICAL,
    RECOGNISED_BACKINGS,
    SAMPLING_TOO_COARSE,
    assess_transmission_into_adhesive,
    backing_corrected_scan,
    backing_is_qualified,
    band_average_transmittance,
    covers_band,
    expected_interface_gain,
    gain_is_physical,
    interpolate_transmittance,
    max_sample_interval_nm,
    meets_requirement,
    normal_incidence_reflectance,
    observed_interface_gain,
    scan_span_nm,
    validate_backing_piece,
    validate_scan,
    validate_stack_policy,
)

BAND_START = 350.0
BAND_END = 1800.0

# Fresnel figures for the default index set, computed by hand from
# n_glass = 1.47, n_adhesive = 1.41, n_air = 1.00 and held here as an
# independent oracle rather than re-derived from the module.
REAR_AIR_REFLECTANCE = 0.036207772623711
REAR_ADHESIVE_REFLECTANCE = 0.000434027777778
FRESNEL_GAIN = 1.037117693865741


def _policy(**overrides):
    policy = dict(DEFAULT_STACK_POLICY)
    policy.update(overrides)
    return policy


def _flat_scan(value=0.97, step=10.0):
    points = []
    wavelength = BAND_START
    while wavelength <= BAND_END + 1e-9:
        points.append((wavelength, value))
        wavelength += step
    return points


def _ramp_scan():
    """Rises linearly from 0.10 at 350 nm to 0.98 at 1800 nm."""
    points = []
    wavelength = BAND_START
    while wavelength <= BAND_END + 1e-9:
        fraction = (wavelength - BAND_START) / (BAND_END - BAND_START)
        points.append((wavelength, 0.10 + 0.88 * fraction))
        wavelength += 10.0
    return points


def _backing(**overrides):
    piece = {
        "material": "uncoated-coverglass-backing-piece",
        "coated": False,
        "thickness_mm": 0.150,
        "bond_void_fraction": 0.002,
    }
    piece.update(overrides)
    return piece


def _case(**overrides):
    case = {
        "backing": _backing(),
        "stack_scan": _flat_scan(0.97),
        "backing_reference_scan": _flat_scan(1.0),
        "baseline_reference": "SPEC-CAL-2026-114",
        "required_minimum_transmittance": 0.94,
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_stack_policy(DEFAULT_STACK_POLICY), DEFAULT_STACK_POLICY)

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_stack_policy("350-1800")

    def test_an_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_stack_policy(_policy(band_start_nm=1800.0, band_end_nm=350.0))

    def test_an_interval_wider_than_the_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_stack_policy(_policy(max_sample_interval_nm=5000.0))

    def test_a_refractive_index_below_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_stack_policy(_policy(refractive_index_adhesive=0.8))

    def test_a_coverglass_index_at_the_ambient_index_rejected(self):
        with self.assertRaises(ValueError):
            validate_stack_policy(_policy(refractive_index_coverglass=1.0))

    def test_a_void_fraction_limit_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_stack_policy(_policy(max_bond_void_fraction=1.0))


class FresnelTests(unittest.TestCase):
    def test_the_rear_air_interface_reflectance_matches_the_oracle(self):
        self.assertAlmostEqual(
            normal_incidence_reflectance(1.47, 1.0),
            REAR_AIR_REFLECTANCE,
            places=12,
        )

    def test_the_rear_adhesive_interface_reflectance_matches_the_oracle(self):
        self.assertAlmostEqual(
            normal_incidence_reflectance(1.47, 1.41),
            REAR_ADHESIVE_REFLECTANCE,
            places=12,
        )

    def test_matched_media_reflect_nothing(self):
        self.assertAlmostEqual(
            normal_incidence_reflectance(1.47, 1.47), 0.0, places=12
        )

    def test_the_interface_gain_matches_the_oracle(self):
        self.assertAlmostEqual(
            expected_interface_gain(1.47, 1.41, 1.0), FRESNEL_GAIN, places=12
        )

    def test_an_index_matched_adhesive_gains_the_whole_rear_reflection(self):
        gain = expected_interface_gain(1.47, 1.47, 1.0)
        self.assertAlmostEqual(gain, 1.0 / (1.0 - REAR_AIR_REFLECTANCE), places=12)

    def test_a_coverglass_index_at_the_ambient_index_has_no_gain_to_give(self):
        with self.assertRaises(ValueError):
            expected_interface_gain(1.0, 1.41, 1.0)

    def test_a_negative_index_rejected(self):
        with self.assertRaises(ValueError):
            normal_incidence_reflectance(-1.47, 1.0)


class BackingTests(unittest.TestCase):
    def test_a_well_formed_backing_validates(self):
        piece = _backing()
        self.assertIs(validate_backing_piece(piece), piece)

    def test_the_recognised_backings_are_listed(self):
        self.assertIn("fused-silica-backing-piece", RECOGNISED_BACKINGS)

    def test_an_unknown_backing_material_rejected(self):
        with self.assertRaises(ValueError):
            validate_backing_piece(_backing(material="anodised-aluminium-plate"))

    def test_an_unstated_coating_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_backing_piece(_backing(coated=None))

    def test_a_zero_thickness_backing_rejected(self):
        with self.assertRaises(ValueError):
            validate_backing_piece(_backing(thickness_mm=0.0))

    def test_a_void_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_backing_piece(_backing(bond_void_fraction=1.4))

    def test_an_uncoated_index_close_backing_qualifies(self):
        self.assertTrue(backing_is_qualified(_backing(), 1.41))

    def test_a_coated_backing_does_not_qualify(self):
        self.assertFalse(backing_is_qualified(_backing(coated=True), 1.41))

    def test_a_backing_far_from_the_adhesive_index_does_not_qualify(self):
        self.assertFalse(backing_is_qualified(_backing(), 1.00))


class ScanValidationTests(unittest.TestCase):
    def test_a_well_formed_scan_validates(self):
        self.assertEqual(len(validate_scan(_flat_scan())), 146)

    def test_mapping_points_are_accepted(self):
        points = validate_scan(
            [
                {"wavelength_nm": 400.0, "transmittance": 0.96},
                {"wavelength_nm": 500.0, "transmittance": 0.97},
            ]
        )
        self.assertAlmostEqual(points[1][1], 0.97, places=12)

    def test_a_single_point_scan_rejected(self):
        with self.assertRaises(ValueError):
            validate_scan([(400.0, 0.97)])

    def test_a_descending_scan_rejected(self):
        with self.assertRaises(ValueError):
            validate_scan([(500.0, 0.97), (400.0, 0.97)])

    def test_a_transmittance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_scan([(400.0, 1.2), (500.0, 0.97)])

    def test_the_scan_span_is_its_first_and_last_wavelength(self):
        first, last = scan_span_nm(_flat_scan())
        self.assertAlmostEqual(first, BAND_START, places=9)
        self.assertAlmostEqual(last, BAND_END, places=9)

    def test_a_scan_landing_exactly_on_the_edges_covers_the_band(self):
        self.assertTrue(covers_band([(BAND_START, 0.9), (BAND_END, 0.9)], BAND_START, BAND_END))

    def test_a_scan_stopping_short_does_not_cover_the_band(self):
        self.assertFalse(covers_band([(400.0, 0.9), (1500.0, 0.9)], BAND_START, BAND_END))

    def test_the_widest_sample_gap_is_reported(self):
        scan = [(BAND_START, 0.9), (500.0, 0.9), (BAND_END, 0.9)]
        self.assertAlmostEqual(max_sample_interval_nm(scan), 1300.0, places=9)

    def test_a_midpoint_interpolates_linearly(self):
        scan = [(400.0, 0.20), (600.0, 0.80)]
        self.assertAlmostEqual(interpolate_transmittance(scan, 500.0), 0.50, places=12)

    def test_a_wavelength_outside_the_scan_rejected(self):
        with self.assertRaises(ValueError):
            interpolate_transmittance([(400.0, 0.2), (600.0, 0.8)], 900.0)


class BandAverageTests(unittest.TestCase):
    def test_a_flat_scan_averages_to_its_own_level(self):
        self.assertAlmostEqual(
            band_average_transmittance(_flat_scan(0.97), BAND_START, BAND_END),
            0.97,
            places=12,
        )

    def test_a_linear_ramp_averages_to_its_midpoint(self):
        self.assertAlmostEqual(
            band_average_transmittance(_ramp_scan(), BAND_START, BAND_END),
            0.54,
            places=9,
        )

    def test_a_band_wider_than_the_scan_rejected(self):
        with self.assertRaises(ValueError):
            band_average_transmittance(_flat_scan(), 300.0, BAND_END)

    def test_a_sub_band_average_uses_interpolated_edges(self):
        scan = [(400.0, 0.0), (600.0, 1.0)]
        self.assertAlmostEqual(
            band_average_transmittance(scan, 450.0, 550.0), 0.50, places=12
        )


class BackingCorrectionTests(unittest.TestCase):
    def test_a_lossless_backing_leaves_the_stack_scan_alone(self):
        corrected = backing_corrected_scan(_flat_scan(0.90), _flat_scan(1.0))
        self.assertAlmostEqual(corrected[0][1], 0.90, places=12)

    def test_a_lossy_backing_is_divided_out(self):
        corrected = backing_corrected_scan(_flat_scan(0.90), _flat_scan(0.95))
        self.assertAlmostEqual(corrected[0][1], 0.90 / 0.95, places=12)

    def test_a_stack_equal_to_its_own_reference_corrects_to_unity(self):
        corrected = backing_corrected_scan(_flat_scan(0.93), _flat_scan(0.93))
        self.assertAlmostEqual(corrected[5][1], 1.0, places=12)

    def test_a_stack_brighter_than_its_reference_rejected(self):
        with self.assertRaises(ValueError):
            backing_corrected_scan(_flat_scan(0.95), _flat_scan(0.80))

    def test_a_reference_short_of_the_stack_scan_rejected(self):
        with self.assertRaises(ValueError):
            backing_corrected_scan(
                _flat_scan(0.90), [(500.0, 1.0), (900.0, 1.0)]
            )

    def test_an_opaque_reference_rejected(self):
        with self.assertRaises(ValueError):
            backing_corrected_scan(
                [(400.0, 0.0), (600.0, 0.0)], [(400.0, 0.0), (600.0, 0.0)]
            )


class GainTests(unittest.TestCase):
    def test_the_observed_gain_is_the_ratio_of_the_two_band_figures(self):
        self.assertAlmostEqual(
            observed_interface_gain(0.97, 0.9352843999647), FRESNEL_GAIN, places=9
        )

    def test_an_into_air_average_of_zero_rejected(self):
        with self.assertRaises(ValueError):
            observed_interface_gain(0.97, 0.0)

    def test_an_into_adhesive_average_above_one_rejected(self):
        with self.assertRaises(ValueError):
            observed_interface_gain(1.4, 0.93)

    def test_a_gain_exactly_on_the_tolerance_edge_is_admissible(self):
        self.assertTrue(gain_is_physical(FRESNEL_GAIN + 0.02, FRESNEL_GAIN, 0.02))

    def test_a_gain_well_outside_the_tolerance_is_not_physical(self):
        self.assertFalse(gain_is_physical(1.40, FRESNEL_GAIN, 0.02))

    def test_a_zero_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            gain_is_physical(FRESNEL_GAIN, FRESNEL_GAIN, 0.0)


class RequirementTests(unittest.TestCase):
    def test_an_average_above_the_requirement_meets_it(self):
        self.assertTrue(meets_requirement(0.97, 0.94))

    def test_an_average_exactly_on_the_requirement_meets_it(self):
        self.assertTrue(meets_requirement(0.94, 0.94))

    def test_an_average_below_the_requirement_does_not_meet_it(self):
        self.assertFalse(meets_requirement(0.92, 0.94))

    def test_a_requirement_of_zero_rejected(self):
        with self.assertRaises(ValueError):
            meets_requirement(0.97, 0.0)


class AssessmentTests(unittest.TestCase):
    def test_a_good_stack_scan_meets_the_requirement(self):
        result = assess_transmission_into_adhesive(_case())
        self.assertEqual(result["verdict"], AVERAGE_MEETS_REQUIREMENT)
        self.assertEqual(result["findings"], [])

    def test_the_corrected_average_and_margin_are_reported(self):
        result = assess_transmission_into_adhesive(_case())
        self.assertAlmostEqual(result["band_average_transmittance"], 0.97, places=12)
        self.assertAlmostEqual(result["margin"], 0.03, places=9)

    def test_the_backing_loss_is_divided_out_of_the_reported_figure(self):
        result = assess_transmission_into_adhesive(
            _case(stack_scan=_flat_scan(0.90), backing_reference_scan=_flat_scan(0.95))
        )
        self.assertAlmostEqual(result["stack_band_average"], 0.90, places=12)
        self.assertAlmostEqual(
            result["band_average_transmittance"], 0.90 / 0.95, places=12
        )

    def test_a_coated_backing_stops_the_reduction(self):
        result = assess_transmission_into_adhesive(
            _case(backing=_backing(coated=True))
        )
        self.assertEqual(result["verdict"], BACKING_NOT_QUALIFIED)
        self.assertIsNone(result["band_average_transmittance"])

    def test_a_voided_bond_stops_the_reduction(self):
        result = assess_transmission_into_adhesive(
            _case(backing=_backing(bond_void_fraction=0.20))
        )
        self.assertEqual(result["verdict"], BOND_NOT_VOID_FREE)

    def test_a_void_fraction_exactly_on_the_limit_passes(self):
        result = assess_transmission_into_adhesive(
            _case(backing=_backing(bond_void_fraction=0.01))
        )
        self.assertEqual(result["verdict"], AVERAGE_MEETS_REQUIREMENT)

    def test_a_missing_baseline_reference_stops_the_reduction(self):
        result = assess_transmission_into_adhesive(_case(baseline_reference=""))
        self.assertEqual(result["verdict"], BASELINE_NOT_REFERENCED)

    def test_a_scan_short_of_the_band_stops_the_reduction(self):
        result = assess_transmission_into_adhesive(
            _case(stack_scan=[(500.0, 0.97), (1500.0, 0.97)])
        )
        self.assertEqual(result["verdict"], BAND_NOT_COVERED)

    def test_a_coarse_scan_stops_the_reduction(self):
        result = assess_transmission_into_adhesive(
            _case(stack_scan=[(BAND_START, 0.97), (BAND_END, 0.97)])
        )
        self.assertEqual(result["verdict"], SAMPLING_TOO_COARSE)
        self.assertAlmostEqual(result["max_sample_interval_nm"], 1450.0, places=9)

    def test_a_sample_gap_exactly_on_the_interval_is_not_too_coarse(self):
        result = assess_transmission_into_adhesive(_case(stack_scan=_flat_scan(0.97, 10.0)))
        self.assertAlmostEqual(result["max_sample_interval_nm"], 10.0, places=9)
        self.assertEqual(result["verdict"], AVERAGE_MEETS_REQUIREMENT)

    def test_a_plausible_gain_over_the_into_air_figure_passes(self):
        result = assess_transmission_into_adhesive(
            _case(into_air_band_average=0.9352843999647)
        )
        self.assertEqual(result["verdict"], AVERAGE_MEETS_REQUIREMENT)
        self.assertAlmostEqual(
            result["observed_interface_gain"], FRESNEL_GAIN, places=9
        )

    def test_an_impossible_gain_over_the_into_air_figure_is_caught(self):
        result = assess_transmission_into_adhesive(
            _case(into_air_band_average=0.60)
        )
        self.assertEqual(result["verdict"], GAIN_NOT_PHYSICAL)
        self.assertEqual(len(result["findings"]), 1)

    def test_no_gain_check_is_invented_without_an_into_air_figure(self):
        result = assess_transmission_into_adhesive(_case())
        self.assertIsNone(result["observed_interface_gain"])
        self.assertTrue(result["advisories"])

    def test_a_missing_backing_reference_scan_raises_an_advisory(self):
        case = _case()
        del case["backing_reference_scan"]
        result = assess_transmission_into_adhesive(case)
        self.assertTrue(
            any("backing reference scan" in note for note in result["advisories"])
        )

    def test_a_short_average_fails_against_the_requirement(self):
        result = assess_transmission_into_adhesive(
            _case(stack_scan=_flat_scan(0.90), required_minimum_transmittance=0.94)
        )
        self.assertEqual(result["verdict"], AVERAGE_BELOW_REQUIREMENT)

    def test_no_declared_minimum_reports_the_average_with_an_advisory(self):
        case = _case()
        del case["required_minimum_transmittance"]
        result = assess_transmission_into_adhesive(case)
        self.assertIsNone(result["required_minimum"])
        self.assertTrue(result["advisories"])

    def test_the_expected_fresnel_gain_travels_with_the_verdict(self):
        result = assess_transmission_into_adhesive(_case())
        self.assertAlmostEqual(
            result["expected_interface_gain"], FRESNEL_GAIN, places=12
        )

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_transmission_into_adhesive(["stack_scan"])

    def test_a_missing_backing_block_rejected(self):
        case = _case()
        del case["backing"]
        with self.assertRaises(ValueError):
            assess_transmission_into_adhesive(case)

    def test_a_missing_stack_scan_rejected(self):
        case = _case()
        del case["stack_scan"]
        with self.assertRaises(ValueError):
            assess_transmission_into_adhesive(case)


if __name__ == "__main__":
    unittest.main()
