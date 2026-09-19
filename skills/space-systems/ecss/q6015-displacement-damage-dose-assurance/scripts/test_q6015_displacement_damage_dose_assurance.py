"""Contract test for the displacement damage dose assurance leaf."""

import unittest

from q6015_displacement_damage_dose_assurance_logic import (
    FINDING_CAPABILITY_BELOW_DOSE,
    FINDING_MARGIN_SHORTFALL,
    FINDING_RAYS_TOO_FEW,
    FINDING_SAMPLING_NOISY,
    FINDING_TEST_REQUIRED,
    MAX_RELATIVE_STANDARD_ERROR,
    METHOD_MONTE_CARLO,
    METHOD_SECTOR,
    MINIMUM_DDD_DESIGN_MARGIN,
    MINIMUM_RAY_COUNT,
    achieved_displacement_margin,
    assess_displacement_damage_dose,
    assess_part,
    ddd_at_shielding,
    displacement_test_required,
    margin_meets_minimum,
    monte_carlo_findings,
    monte_carlo_ray_trace_ddd,
    sector_ray_trace_ddd,
    validate_ddd_depth_curve,
    validate_part,
    validate_sectors,
)

CURVE = [(1.0, 4.0e9), (2.0, 2.0e9), (4.0, 1.0e9), (8.0, 5.0e8)]

EVEN_SECTORS = [
    {"solid_angle_fraction": 0.5, "thickness_mm": 2.0},
    {"solid_angle_fraction": 0.5, "thickness_mm": 2.0},
]

UNEVEN_SECTORS = [
    {"solid_angle_fraction": 0.25, "thickness_mm": 1.0},
    {"solid_angle_fraction": 0.75, "thickness_mm": 4.0},
]


def flat_rays(count, thickness=2.0):
    return [thickness] * count


def sector_part(pid="U1", **kw):
    record = {
        "id": pid,
        "family": "cmos-logic",
        "method": METHOD_SECTOR,
        "capability_mev_per_g": 1.0e10,
        "sectors": EVEN_SECTORS,
    }
    record.update(kw)
    return record


def mc_part(pid="M1", **kw):
    record = {
        "id": pid,
        "family": "cmos-logic",
        "method": METHOD_MONTE_CARLO,
        "capability_mev_per_g": 1.0e10,
        "ray_thicknesses_mm": flat_rays(MINIMUM_RAY_COUNT),
    }
    record.update(kw)
    return record


class TestCurveValidation(unittest.TestCase):
    def test_valid_curve_normalizes(self):
        points = validate_ddd_depth_curve(CURVE)
        self.assertEqual(len(points), 4)

    def test_rising_dose_with_shielding_raises(self):
        with self.assertRaises(ValueError):
            validate_ddd_depth_curve([(1.0, 1.0e9), (2.0, 2.0e9)])

    def test_repeated_thickness_raises(self):
        with self.assertRaises(ValueError):
            validate_ddd_depth_curve([(1.0, 2.0e9), (1.0, 1.0e9)])

    def test_short_curve_raises(self):
        with self.assertRaises(ValueError):
            validate_ddd_depth_curve([(1.0, 2.0e9)])


class TestDddAtShielding(unittest.TestCase):
    def test_tabulated_point_returns_its_dose(self):
        self.assertAlmostEqual(
            ddd_at_shielding(CURVE, 4.0) / 1.0e9, 1.0, places=9
        )

    def test_interpolated_value_sits_between_neighbours(self):
        value = ddd_at_shielding(CURVE, 3.0)
        self.assertLess(value, 2.0e9)
        self.assertGreater(value, 1.0e9)

    def test_shielding_outside_span_is_refused(self):
        with self.assertRaises(ValueError):
            ddd_at_shielding(CURVE, 0.2)

    def test_negative_shielding_raises(self):
        with self.assertRaises(ValueError):
            ddd_at_shielding(CURVE, -1.0)


class TestSectorRayTrace(unittest.TestCase):
    def test_sectors_must_close_the_sphere(self):
        with self.assertRaises(ValueError):
            validate_sectors(
                [
                    {"solid_angle_fraction": 0.25, "thickness_mm": 1.0},
                    {"solid_angle_fraction": 0.25, "thickness_mm": 2.0},
                ]
            )

    def test_zero_fraction_sector_raises(self):
        with self.assertRaises(ValueError):
            validate_sectors(
                [
                    {"solid_angle_fraction": 0.0, "thickness_mm": 1.0},
                    {"solid_angle_fraction": 1.0, "thickness_mm": 2.0},
                ]
            )

    def test_empty_sector_set_raises(self):
        with self.assertRaises(ValueError):
            validate_sectors([])

    def test_uniform_sectors_give_the_single_thickness_dose(self):
        value = sector_ray_trace_ddd(CURVE, EVEN_SECTORS)
        self.assertAlmostEqual(value / 1.0e9, 2.0, places=9)

    def test_thin_sector_dominates_the_weighted_dose(self):
        value = sector_ray_trace_ddd(CURVE, UNEVEN_SECTORS)
        expected = 0.25 * 4.0e9 + 0.75 * 1.0e9
        self.assertAlmostEqual(value / 1.0e9, expected / 1.0e9, places=9)


class TestMonteCarloRayTrace(unittest.TestCase):
    def test_identical_rays_have_zero_standard_error(self):
        sampling = monte_carlo_ray_trace_ddd(CURVE, flat_rays(60))
        self.assertEqual(sampling["ray_count"], 60)
        self.assertAlmostEqual(sampling["relative_standard_error"], 0.0, places=12)

    def test_mean_of_identical_rays_is_that_ray_dose(self):
        sampling = monte_carlo_ray_trace_ddd(CURVE, flat_rays(60, 4.0))
        self.assertAlmostEqual(sampling["mean_ddd_mev_per_g"] / 1.0e9, 1.0, places=9)

    def test_single_ray_raises(self):
        with self.assertRaises(ValueError):
            monte_carlo_ray_trace_ddd(CURVE, [2.0])

    def test_too_few_rays_is_a_finding(self):
        sampling = monte_carlo_ray_trace_ddd(CURVE, flat_rays(10))
        self.assertIn(FINDING_RAYS_TOO_FEW, monte_carlo_findings(sampling))

    def test_wide_spread_is_a_sampling_finding(self):
        rays = [1.0, 8.0] * 40
        sampling = monte_carlo_ray_trace_ddd(CURVE, rays)
        self.assertGreater(
            sampling["relative_standard_error"], MAX_RELATIVE_STANDARD_ERROR
        )
        self.assertIn(FINDING_SAMPLING_NOISY, monte_carlo_findings(sampling))

    def test_well_sampled_trace_has_no_finding(self):
        sampling = monte_carlo_ray_trace_ddd(CURVE, flat_rays(MINIMUM_RAY_COUNT))
        self.assertEqual(monte_carlo_findings(sampling), [])

    def test_sampling_findings_reject_a_bad_record(self):
        with self.assertRaises(ValueError):
            monte_carlo_findings({"ray_count": 1, "relative_standard_error": 0.0})


class TestMarginRules(unittest.TestCase):
    def test_achieved_margin_is_capability_over_dose(self):
        self.assertAlmostEqual(
            achieved_displacement_margin(4.0e9, 2.0e9), 2.0, places=9
        )

    def test_margin_exactly_at_minimum_is_met(self):
        self.assertTrue(margin_meets_minimum(MINIMUM_DDD_DESIGN_MARGIN))

    def test_margin_below_minimum_is_not_met(self):
        self.assertFalse(margin_meets_minimum(1.5))

    def test_zero_dose_raises(self):
        with self.assertRaises(ValueError):
            achieved_displacement_margin(4.0e9, 0.0)


class TestFamilyTestRule(unittest.TestCase):
    def test_optocoupler_owes_a_displacement_test(self):
        self.assertTrue(displacement_test_required("optocoupler"))

    def test_cmos_logic_does_not(self):
        self.assertFalse(displacement_test_required("cmos-logic"))

    def test_empty_family_raises(self):
        with self.assertRaises(ValueError):
            displacement_test_required("")


class TestPartValidation(unittest.TestCase):
    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            validate_part(sector_part("U1", method="hand-waving"))

    def test_sector_part_without_sectors_raises(self):
        record = sector_part("U1")
        del record["sectors"]
        with self.assertRaises(ValueError):
            validate_part(record)

    def test_monte_carlo_part_without_rays_raises(self):
        record = mc_part("M1")
        del record["ray_thicknesses_mm"]
        with self.assertRaises(ValueError):
            validate_part(record)

    def test_blank_test_reference_raises(self):
        with self.assertRaises(ValueError):
            validate_part(sector_part("U1", test_reference="  "))

    def test_non_mapping_part_raises(self):
        with self.assertRaises(ValueError):
            validate_part("U1")


class TestAssessPart(unittest.TestCase):
    def test_comfortable_sector_part_is_compliant(self):
        result = assess_part(sector_part(), CURVE)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["achieved_margin"], 5.0, places=9)

    def test_part_exactly_at_minimum_margin_is_compliant(self):
        result = assess_part(sector_part("U2", capability_mev_per_g=4.0e9), CURVE)
        self.assertAlmostEqual(result["achieved_margin"], 2.0, places=9)
        self.assertTrue(result["compliant"])

    def test_margin_shortfall_is_reported(self):
        result = assess_part(sector_part("U3", capability_mev_per_g=3.0e9), CURVE)
        self.assertIn(FINDING_MARGIN_SHORTFALL, result["findings"])

    def test_capability_below_dose_is_reported(self):
        result = assess_part(sector_part("U4", capability_mev_per_g=1.0e9), CURVE)
        self.assertIn(FINDING_CAPABILITY_BELOW_DOSE, result["findings"])

    def test_sensitive_family_without_test_reference_is_a_finding(self):
        result = assess_part(sector_part("U5", family="optocoupler"), CURVE)
        self.assertIn(FINDING_TEST_REQUIRED, result["findings"])
        self.assertFalse(result["compliant"])

    def test_sensitive_family_with_test_reference_passes(self):
        result = assess_part(
            sector_part("U6", family="optocoupler", test_reference="DDR-014"), CURVE
        )
        self.assertTrue(result["compliant"])

    def test_undersampled_monte_carlo_part_carries_its_finding(self):
        result = assess_part(
            mc_part("M2", ray_thicknesses_mm=flat_rays(10)), CURVE
        )
        self.assertIn(FINDING_RAYS_TOO_FEW, result["findings"])
        self.assertFalse(result["compliant"])

    def test_well_sampled_monte_carlo_part_is_compliant(self):
        result = assess_part(mc_part(), CURVE)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["sampling"]["ray_count"], MINIMUM_RAY_COUNT)


class TestAssessment(unittest.TestCase):
    def test_tightest_part_drives_the_verdict(self):
        report = assess_displacement_damage_dose(
            [sector_part("U1"), sector_part("U2", capability_mev_per_g=3.0e9)], CURVE
        )
        self.assertEqual(report["tightest_part_id"], "U2")
        self.assertFalse(report["compliant"])

    def test_test_required_ids_are_collected(self):
        report = assess_displacement_damage_dose(
            [sector_part("U1"), sector_part("U2", family="solar-cell")], CURVE
        )
        self.assertEqual(report["test_required_ids"], ["U2"])

    def test_duplicate_part_id_raises(self):
        with self.assertRaises(ValueError):
            assess_displacement_damage_dose(
                [sector_part("U1"), sector_part("U1")], CURVE
            )

    def test_empty_parts_list_raises(self):
        with self.assertRaises(ValueError):
            assess_displacement_damage_dose([], CURVE)

    def test_non_list_parts_raises(self):
        with self.assertRaises(ValueError):
            assess_displacement_damage_dose(sector_part(), CURVE)


if __name__ == "__main__":
    unittest.main()
