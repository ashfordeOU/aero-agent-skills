"""Contract tests for the outgassing-screening specimen preparation logic."""

import unittest

from q7002_specimen_preparation_logic import (
    BOAT_INNER_MM,
    CONDITIONING_HOURS,
    CONDITIONING_HUMIDITY_PCT,
    CONDITIONING_TEMPERATURE_C,
    EXTRA_SPECIMENS_INHOMOGENEOUS,
    MINIMUM_SPECIMENS,
    NOMINAL_SPECIMEN_MASS_MG,
    SPECIMEN_MASS_WINDOW_MG,
    conditioning_findings,
    net_specimen_mass_mg,
    piece_fits_holder,
    piece_mass_mg,
    piece_volume_mm3,
    pieces_per_specimen,
    plan_specimens,
    specimen_count,
    specimen_mass_findings,
)

GOOD_CONDITIONING = {
    "hours": CONDITIONING_HOURS,
    "temperature_c": CONDITIONING_TEMPERATURE_C,
    "humidity_pct": CONDITIONING_HUMIDITY_PCT,
}


def base_material(**overrides):
    """A homogeneous cured film cut into 10 x 5 x 0.5 mm pieces."""
    material = {
        "form": "film",
        "density_g_cm3": 1.2,
        "piece_dimensions_mm": (10.0, 5.0, 0.5),
        "homogeneous": True,
        "achieved_conditioning": dict(GOOD_CONDITIONING),
    }
    material.update(overrides)
    return material


class GeometryTests(unittest.TestCase):
    def test_volume_is_the_product_of_the_dimensions(self):
        self.assertAlmostEqual(piece_volume_mm3((10.0, 5.0, 0.5)), 25.0, places=9)

    def test_mass_follows_volume_and_density(self):
        # 25 mm^3 = 0.025 cm^3; at 1.2 g/cm^3 that is 0.03 g = 30 mg.
        self.assertAlmostEqual(piece_mass_mg((10.0, 5.0, 0.5), 1.2), 30.0, places=9)

    def test_zero_dimension_rejected(self):
        with self.assertRaises(ValueError):
            piece_volume_mm3((10.0, 0.0, 0.5))

    def test_two_component_dimension_rejected(self):
        with self.assertRaises(ValueError):
            piece_volume_mm3((10.0, 5.0))

    def test_negative_density_rejected(self):
        with self.assertRaises(ValueError):
            piece_mass_mg((10.0, 5.0, 0.5), -1.2)

    def test_small_piece_fits_the_holder(self):
        self.assertTrue(piece_fits_holder((10.0, 5.0, 0.5)))

    def test_piece_fits_when_turned(self):
        self.assertTrue(piece_fits_holder((0.5, 28.0, 10.0)))

    def test_over_long_piece_does_not_fit(self):
        self.assertFalse(piece_fits_holder((45.0, 5.0, 0.5)))

    def test_piece_exactly_the_holder_size_fits(self):
        self.assertTrue(piece_fits_holder(BOAT_INNER_MM))


class PieceCountTests(unittest.TestCase):
    def test_exact_multiple_needs_no_extra_piece(self):
        self.assertEqual(pieces_per_specimen(200.0, 50.0), 4)

    def test_partial_piece_rounds_up(self):
        self.assertEqual(pieces_per_specimen(200.0, 30.0), 7)

    def test_one_large_piece_is_enough(self):
        self.assertEqual(pieces_per_specimen(200.0, 400.0), 1)

    def test_zero_piece_mass_rejected(self):
        with self.assertRaises(ValueError):
            pieces_per_specimen(200.0, 0.0)

    def test_non_numeric_target_rejected(self):
        with self.assertRaises(ValueError):
            pieces_per_specimen("200", 30.0)


class SpecimenCountTests(unittest.TestCase):
    def test_homogeneous_solid_takes_the_replicate_minimum(self):
        counts = specimen_count("film")
        self.assertEqual(counts["specimens"], MINIMUM_SPECIMENS)
        self.assertEqual(counts["carrier_blanks"], 0)

    def test_inhomogeneous_material_takes_extra_replicates(self):
        counts = specimen_count("film", homogeneous=False)
        self.assertEqual(counts["specimens"], MINIMUM_SPECIMENS + EXTRA_SPECIMENS_INHOMOGENEOUS)

    def test_paste_needs_a_carrier_blank_per_specimen(self):
        counts = specimen_count("paste")
        self.assertTrue(counts["carrier_required"])
        self.assertEqual(counts["carrier_blanks"], counts["specimens"])

    def test_form_match_ignores_case(self):
        self.assertTrue(specimen_count("Two-Part-Mixed")["carrier_required"])

    def test_more_specimens_than_the_minimum_are_accepted(self):
        self.assertEqual(specimen_count("film", requested=6)["specimens"], 6)

    def test_fewer_specimens_than_the_minimum_rejected(self):
        with self.assertRaises(ValueError):
            specimen_count("film", requested=MINIMUM_SPECIMENS - 1)

    def test_blank_form_rejected(self):
        with self.assertRaises(ValueError):
            specimen_count("  ")

    def test_non_boolean_homogeneity_rejected(self):
        with self.assertRaises(ValueError):
            specimen_count("film", homogeneous="yes")


class MassTests(unittest.TestCase):
    def test_net_mass_removes_the_carrier(self):
        self.assertAlmostEqual(net_specimen_mass_mg(320.0, 120.0), 200.0, places=9)

    def test_no_carrier_leaves_the_gross_unchanged(self):
        self.assertAlmostEqual(net_specimen_mass_mg(200.0), 200.0, places=9)

    def test_carrier_consuming_the_whole_gross_rejected(self):
        with self.assertRaises(ValueError):
            net_specimen_mass_mg(200.0, 200.0)

    def test_negative_carrier_rejected(self):
        with self.assertRaises(ValueError):
            net_specimen_mass_mg(200.0, -10.0)

    def test_nominal_mass_is_inside_the_window(self):
        self.assertEqual(specimen_mass_findings(NOMINAL_SPECIMEN_MASS_MG), [])

    def test_mass_exactly_on_the_lower_bound_is_inside(self):
        self.assertEqual(specimen_mass_findings(SPECIMEN_MASS_WINDOW_MG[0]), [])

    def test_mass_exactly_on_the_upper_bound_is_inside(self):
        self.assertEqual(specimen_mass_findings(SPECIMEN_MASS_WINDOW_MG[1]), [])

    def test_undersized_specimen_is_flagged(self):
        findings = specimen_mass_findings(20.0)
        self.assertTrue(any("below the" in f for f in findings))

    def test_oversized_specimen_is_flagged(self):
        findings = specimen_mass_findings(900.0)
        self.assertTrue(any("above the" in f for f in findings))


class ConditioningTests(unittest.TestCase):
    def test_nominal_conditioning_is_clean(self):
        self.assertEqual(conditioning_findings(GOOD_CONDITIONING), [])

    def test_short_conditioning_is_flagged(self):
        findings = conditioning_findings(dict(GOOD_CONDITIONING, hours=6.0))
        self.assertTrue(any("short of the" in f for f in findings))

    def test_longer_conditioning_is_not_a_finding(self):
        self.assertEqual(conditioning_findings(dict(GOOD_CONDITIONING, hours=48.0)), [])

    def test_temperature_outside_the_band_is_flagged(self):
        findings = conditioning_findings(dict(GOOD_CONDITIONING, temperature_c=31.0))
        self.assertTrue(any("temperature" in f for f in findings))

    def test_temperature_exactly_on_the_band_edge_is_clean(self):
        edge = CONDITIONING_TEMPERATURE_C + 2.0
        self.assertEqual(conditioning_findings(dict(GOOD_CONDITIONING, temperature_c=edge)), [])

    def test_humidity_outside_the_band_is_flagged(self):
        findings = conditioning_findings(dict(GOOD_CONDITIONING, humidity_pct=72.0))
        self.assertTrue(any("relative humidity" in f for f in findings))

    def test_missing_conditioning_key_rejected(self):
        achieved = dict(GOOD_CONDITIONING)
        del achieved["humidity_pct"]
        with self.assertRaises(ValueError):
            conditioning_findings(achieved)

    def test_non_numeric_conditioning_value_rejected(self):
        with self.assertRaises(ValueError):
            conditioning_findings(dict(GOOD_CONDITIONING, temperature_c="23"))


class PlanTests(unittest.TestCase):
    def test_nominal_film_plan_is_ready(self):
        plan = plan_specimens(base_material())
        self.assertTrue(plan["ready"])
        self.assertEqual(plan["findings"], [])

    def test_plan_reports_pieces_and_total_material(self):
        plan = plan_specimens(base_material())
        self.assertAlmostEqual(plan["piece_mass_mg"], 30.0, places=9)
        self.assertEqual(plan["pieces_per_specimen"], 7)
        self.assertAlmostEqual(
            plan["total_material_mg"], NOMINAL_SPECIMEN_MASS_MG * MINIMUM_SPECIMENS, places=9
        )

    def test_inhomogeneous_material_plans_extra_specimens(self):
        plan = plan_specimens(base_material(homogeneous=False))
        self.assertEqual(plan["specimens"], MINIMUM_SPECIMENS + EXTRA_SPECIMENS_INHOMOGENEOUS)

    def test_paste_without_a_declared_carrier_is_flagged(self):
        plan = plan_specimens(base_material(form="paste"))
        self.assertFalse(plan["ready"])
        self.assertTrue(any("needs a carrier" in f for f in plan["findings"]))

    def test_paste_with_a_carrier_nets_out_the_material_mass(self):
        plan = plan_specimens(base_material(form="paste", carrier_mass_mg=150.0))
        self.assertAlmostEqual(plan["net_specimen_mass_mg"], NOMINAL_SPECIMEN_MASS_MG, places=9)
        self.assertAlmostEqual(plan["gross_specimen_mass_mg"], 350.0, places=9)
        self.assertEqual(plan["carrier_blanks"], plan["specimens"])

    def test_oversized_piece_is_flagged(self):
        plan = plan_specimens(base_material(piece_dimensions_mm=(45.0, 5.0, 0.5)))
        self.assertFalse(plan["piece_fits_holder"])
        self.assertTrue(any("does not fit the sample holder" in f for f in plan["findings"]))

    def test_out_of_window_target_mass_is_flagged(self):
        plan = plan_specimens(base_material(target_specimen_mass_mg=900.0))
        self.assertFalse(plan["ready"])

    def test_failed_conditioning_reaches_the_plan_findings(self):
        plan = plan_specimens(
            base_material(achieved_conditioning=dict(GOOD_CONDITIONING, hours=2.0))
        )
        self.assertTrue(any("short of the" in f for f in plan["findings"]))

    def test_plan_without_conditioning_data_skips_that_check(self):
        material = base_material()
        del material["achieved_conditioning"]
        self.assertTrue(plan_specimens(material)["ready"])

    def test_missing_required_material_key_rejected(self):
        material = base_material()
        del material["density_g_cm3"]
        with self.assertRaises(ValueError):
            plan_specimens(material)

    def test_non_mapping_material_rejected(self):
        with self.assertRaises(ValueError):
            plan_specimens("film")


if __name__ == "__main__":
    unittest.main()
