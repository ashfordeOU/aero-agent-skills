"""Contract test for the ECSS-E-ST-20C 7.2.2.3.6 support-scattering leaf.

Offline, deterministic, stdlib unittest only.
"""

import math
import unittest

from e20_antenna_support_structure_scattering_logic import (
    FLOOR_LEVEL_DBC,
    aperture_area_m2,
    assess_support_structure_scattering,
    blockage_fraction,
    blockage_gain_loss_db,
    categorize_scattering_mechanism,
    depolarised_split_dbc,
    scattered_side_lobe_level_dbc,
    spherical_wave_magnification,
    strut_projected_area_m2,
)


def base_config(**overrides):
    cfg = {
        "aperture_diameter_m": 2.4,
        "angular_spread_factor": 40.0,
        "strut_tilt_to_e_field_deg": 30.0,
        "allowable_gain_loss_db": 0.5,
        "allowable_side_lobe_level_dbc": -25.0,
        "allowable_cross_polar_level_dbc": -30.0,
        "supports": [
            {
                "id": "strut-set",
                "field_region": "collimated-aperture-field",
                "width_m": 0.02,
                "length_m": 0.9,
                "count": 4,
                "tilt_deg": 0.0,
            }
        ],
    }
    cfg.update(overrides)
    return cfg


class MechanismCategorisation(unittest.TestCase):
    def test_collimated_field_gives_plane_wave_scattering(self):
        self.assertEqual(
            categorize_scattering_mechanism("collimated-aperture-field"),
            "plane-wave-scattering",
        )

    def test_feed_wave_gives_spherical_wave_scattering(self):
        self.assertEqual(
            categorize_scattering_mechanism("feed-spherical-wave"),
            "spherical-wave-scattering",
        )

    def test_rim_gives_edge_diffraction(self):
        self.assertEqual(
            categorize_scattering_mechanism("reflector-rim"), "edge-diffraction"
        )

    def test_shadowed_volume_has_no_scattering_path(self):
        self.assertEqual(
            categorize_scattering_mechanism("  Outside-Illuminated-Volume  "),
            "no-scattering-path",
        )

    def test_uncategorized_field_region_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_scattering_mechanism("somewhere-else")

    def test_non_string_field_region_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_scattering_mechanism(7)


class ApertureAndProjection(unittest.TestCase):
    def test_aperture_area_of_two_metre_dish(self):
        self.assertAlmostEqual(aperture_area_m2(2.0), math.pi, places=9)

    def test_aperture_area_rejects_zero_diameter(self):
        with self.assertRaises(ValueError):
            aperture_area_m2(0.0)

    def test_aperture_area_rejects_non_numeric(self):
        with self.assertRaises(ValueError):
            aperture_area_m2("wide")

    def test_untilted_strut_projects_its_full_face(self):
        self.assertAlmostEqual(
            strut_projected_area_m2(0.02, 1.0, count=4), 0.08, places=12
        )

    def test_sixty_degree_tilt_halves_the_shadow(self):
        self.assertAlmostEqual(
            strut_projected_area_m2(0.02, 1.0, count=1, tilt_deg=60.0), 0.01, places=12
        )

    def test_normal_strut_casts_no_shadow(self):
        self.assertAlmostEqual(
            strut_projected_area_m2(0.02, 1.0, count=1, tilt_deg=90.0), 0.0, places=12
        )

    def test_tilt_beyond_ninety_is_rejected(self):
        with self.assertRaises(ValueError):
            strut_projected_area_m2(0.02, 1.0, tilt_deg=95.0)

    def test_negative_tilt_is_rejected(self):
        with self.assertRaises(ValueError):
            strut_projected_area_m2(0.02, 1.0, tilt_deg=-1.0)

    def test_zero_count_is_rejected(self):
        with self.assertRaises(ValueError):
            strut_projected_area_m2(0.02, 1.0, count=0)

    def test_boolean_count_is_rejected(self):
        with self.assertRaises(ValueError):
            strut_projected_area_m2(0.02, 1.0, count=True)

    def test_negative_width_is_rejected(self):
        with self.assertRaises(ValueError):
            strut_projected_area_m2(-0.02, 1.0)


class SphericalWaveMagnification(unittest.TestCase):
    def test_magnification_is_the_distance_ratio(self):
        self.assertAlmostEqual(spherical_wave_magnification(0.3, 1.2), 4.0, places=12)

    def test_strut_at_the_reflector_has_unit_magnification(self):
        self.assertAlmostEqual(spherical_wave_magnification(1.2, 1.2), 1.0, places=12)

    def test_reflector_closer_than_strut_is_rejected(self):
        with self.assertRaises(ValueError):
            spherical_wave_magnification(1.2, 0.3)

    def test_zero_strut_distance_is_rejected(self):
        with self.assertRaises(ValueError):
            spherical_wave_magnification(0.0, 1.2)


class BlockageMetrics(unittest.TestCase):
    def test_fraction_is_the_area_ratio(self):
        self.assertAlmostEqual(blockage_fraction(0.25, 5.0), 0.05, places=12)

    def test_zero_blocked_area_is_allowed(self):
        self.assertAlmostEqual(blockage_fraction(0.0, 5.0), 0.0, places=12)

    def test_full_blockage_is_rejected(self):
        with self.assertRaises(ValueError):
            blockage_fraction(5.0, 5.0)

    def test_negative_blocked_area_is_rejected(self):
        with self.assertRaises(ValueError):
            blockage_fraction(-0.1, 5.0)

    def test_ten_percent_blockage_loses_about_zero_point_nine_db(self):
        self.assertAlmostEqual(blockage_gain_loss_db(0.1), 0.91514984, places=6)

    def test_no_blockage_loses_no_gain(self):
        self.assertAlmostEqual(blockage_gain_loss_db(0.0), 0.0, places=12)

    def test_gain_loss_rejects_unit_fraction(self):
        with self.assertRaises(ValueError):
            blockage_gain_loss_db(1.0)

    def test_gain_loss_rejects_negative_fraction(self):
        with self.assertRaises(ValueError):
            blockage_gain_loss_db(-0.01)


class ScatteredLobeLevel(unittest.TestCase):
    def test_level_matches_the_intensity_ratio(self):
        expected = 10.0 * math.log10(0.02 / (0.98 * 50.0))
        self.assertAlmostEqual(
            scattered_side_lobe_level_dbc(0.02, 50.0), expected, places=9
        )

    def test_wider_spread_pushes_the_lobe_down(self):
        tight = scattered_side_lobe_level_dbc(0.02, 10.0)
        wide = scattered_side_lobe_level_dbc(0.02, 100.0)
        self.assertLess(wide, tight)

    def test_spread_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            scattered_side_lobe_level_dbc(0.02, 0.5)

    def test_zero_fraction_is_rejected(self):
        with self.assertRaises(ValueError):
            scattered_side_lobe_level_dbc(0.0, 10.0)


class Depolarisation(unittest.TestCase):
    def test_aligned_strut_has_no_cross_polar_term(self):
        split = depolarised_split_dbc(-30.0, 0.0)
        self.assertAlmostEqual(split["co_polar_dbc"], -30.0, places=9)
        self.assertAlmostEqual(split["cross_polar_dbc"], FLOOR_LEVEL_DBC, places=9)

    def test_forty_five_degrees_splits_the_power_evenly(self):
        split = depolarised_split_dbc(-30.0, 45.0)
        self.assertAlmostEqual(split["co_polar_dbc"], -33.0102999566, places=6)
        self.assertAlmostEqual(split["cross_polar_dbc"], -33.0102999566, places=6)

    def test_orthogonal_strut_radiates_only_cross_polar(self):
        split = depolarised_split_dbc(-30.0, 90.0)
        self.assertAlmostEqual(split["cross_polar_dbc"], -30.0, places=9)
        self.assertAlmostEqual(split["co_polar_dbc"], FLOOR_LEVEL_DBC, places=9)

    def test_tilt_outside_the_quadrant_is_rejected(self):
        with self.assertRaises(ValueError):
            depolarised_split_dbc(-30.0, 120.0)

    def test_infinite_level_is_rejected(self):
        with self.assertRaises(ValueError):
            depolarised_split_dbc(float("inf"), 30.0)


class Assessment(unittest.TestCase):
    def test_small_struts_are_compliant(self):
        result = assess_support_structure_scattering(base_config())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["blocked_area_m2"], 0.072, places=12)
        self.assertEqual(result["per_support"][0]["mechanism"], "plane-wave-scattering")

    def test_fat_struts_break_the_gain_budget(self):
        cfg = base_config()
        cfg["supports"][0]["width_m"] = 0.25
        result = assess_support_structure_scattering(cfg)
        self.assertIn("blockage-gain-loss-exceeds-allowable", result["findings"])
        self.assertFalse(result["compliant"])

    def test_gain_loss_exactly_at_the_allowable_is_compliant(self):
        cfg = base_config()
        result = assess_support_structure_scattering(cfg)
        cfg["allowable_gain_loss_db"] = result["gain_loss_db"]
        tight = assess_support_structure_scattering(cfg)
        self.assertNotIn("blockage-gain-loss-exceeds-allowable", tight["findings"])

    def test_side_lobe_exactly_at_the_allowable_is_compliant(self):
        cfg = base_config()
        result = assess_support_structure_scattering(cfg)
        cfg["allowable_side_lobe_level_dbc"] = result["co_polar_level_dbc"]
        cfg["allowable_cross_polar_level_dbc"] = result["cross_polar_level_dbc"]
        tight = assess_support_structure_scattering(cfg)
        self.assertEqual(tight["findings"], [])

    def test_missing_gain_allowable_is_itself_a_finding(self):
        cfg = base_config()
        del cfg["allowable_gain_loss_db"]
        result = assess_support_structure_scattering(cfg)
        self.assertIn("no-allowable-gain-loss-on-record", result["findings"])

    def test_missing_side_lobe_allowable_is_itself_a_finding(self):
        cfg = base_config()
        del cfg["allowable_side_lobe_level_dbc"]
        result = assess_support_structure_scattering(cfg)
        self.assertIn("no-allowable-side-lobe-level-on-record", result["findings"])

    def test_feed_region_strut_is_magnified_onto_the_aperture(self):
        cfg = base_config()
        cfg["supports"] = [
            {
                "id": "tripod-leg",
                "field_region": "feed-spherical-wave",
                "width_m": 0.01,
                "length_m": 0.2,
                "count": 3,
                "tilt_deg": 0.0,
                "strut_distance_m": 0.25,
                "reflector_distance_m": 0.75,
            }
        ]
        result = assess_support_structure_scattering(cfg)
        self.assertAlmostEqual(result["blocked_area_m2"], 0.054, places=12)

    def test_feed_region_strut_without_distances_is_rejected(self):
        cfg = base_config()
        cfg["supports"] = [
            {
                "id": "tripod-leg",
                "field_region": "feed-spherical-wave",
                "width_m": 0.01,
                "length_m": 0.2,
                "count": 3,
            }
        ]
        with self.assertRaises(ValueError):
            assess_support_structure_scattering(cfg)

    def test_support_outside_the_illuminated_volume_blocks_nothing(self):
        cfg = base_config()
        cfg["supports"].append(
            {
                "id": "stowed-bracket",
                "field_region": "outside-illuminated-volume",
                "width_m": 0.5,
                "length_m": 0.5,
            }
        )
        result = assess_support_structure_scattering(cfg)
        self.assertAlmostEqual(result["blocked_area_m2"], 0.072, places=12)
        self.assertTrue(result["compliant"])

    def test_rim_fitting_needs_a_declared_edge_level(self):
        cfg = base_config()
        cfg["supports"].append({"id": "rim-clip", "field_region": "reflector-rim"})
        with self.assertRaises(ValueError):
            assess_support_structure_scattering(cfg)

    def test_loud_rim_diffraction_is_flagged(self):
        cfg = base_config()
        cfg["supports"].append(
            {
                "id": "rim-clip",
                "field_region": "reflector-rim",
                "edge_diffraction_level_dbc": -12.0,
            }
        )
        result = assess_support_structure_scattering(cfg)
        self.assertIn("edge-diffraction-exceeds-allowable", result["findings"])

    def test_quiet_rim_diffraction_passes(self):
        cfg = base_config()
        cfg["supports"].append(
            {
                "id": "rim-clip",
                "field_region": "reflector-rim",
                "edge_diffraction_level_dbc": -40.0,
            }
        )
        result = assess_support_structure_scattering(cfg)
        self.assertTrue(result["compliant"])

    def test_duplicate_support_id_is_rejected(self):
        cfg = base_config()
        cfg["supports"].append(dict(cfg["supports"][0]))
        with self.assertRaises(ValueError):
            assess_support_structure_scattering(cfg)

    def test_support_without_an_id_is_rejected(self):
        cfg = base_config()
        cfg["supports"][0].pop("id")
        with self.assertRaises(ValueError):
            assess_support_structure_scattering(cfg)

    def test_empty_support_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_support_structure_scattering(base_config(supports=[]))

    def test_non_mapping_config_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_support_structure_scattering(["strut"])

    def test_tilted_struts_raise_the_cross_polar_lobe(self):
        upright = assess_support_structure_scattering(
            base_config(strut_tilt_to_e_field_deg=5.0)
        )
        slanted = assess_support_structure_scattering(
            base_config(strut_tilt_to_e_field_deg=45.0)
        )
        self.assertGreater(
            slanted["cross_polar_level_dbc"], upright["cross_polar_level_dbc"]
        )


if __name__ == "__main__":
    unittest.main()
