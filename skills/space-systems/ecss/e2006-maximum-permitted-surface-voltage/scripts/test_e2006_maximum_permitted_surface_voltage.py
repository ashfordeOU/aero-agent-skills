#!/usr/bin/env python3
"""Gate 3 contract test for e2006-maximum-permitted-surface-voltage."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2006_maximum_permitted_surface_voltage_logic import (  # noqa: E402
    BINDING_SOURCES,
    MARGINAL_RATIO,
    MATERIAL_CEILINGS,
    VERDICTS,
    discharge_onset_verdict,
    evaluate_surface,
    evaluate_surface_set,
    internal_field,
    material_ceilings,
    minimum_thickness_for_potential,
    permitted_surface_potential,
    potential_at_field,
    potential_margin,
    within_ceiling,
)


def good_surface(**over):
    surface = {
        "name": "polyimide-blanket-outer-face",
        "material_family": "polyimide-film",
        "thickness_m": 2.5e-5,
        "predicted_potential_v": 150.0,
        "safety_factor": 1.0,
    }
    surface.update(over)
    return surface


class TestMaterialCeilings(unittest.TestCase):
    def test_known_family_returns_three_ceilings(self):
        ceilings = material_ceilings("polyimide-film")
        self.assertIn("absolute_potential_ceiling_v", ceilings)
        self.assertIn("differential_potential_ceiling_v", ceilings)
        self.assertIn("breakdown_field_v_per_m", ceilings)

    def test_lookup_is_case_and_space_insensitive(self):
        self.assertEqual(
            material_ceilings("  Polyimide-Film "), material_ceilings("polyimide-film")
        )

    def test_returned_mapping_is_a_copy(self):
        ceilings = material_ceilings("ptfe-film")
        ceilings["breakdown_field_v_per_m"] = 1.0
        self.assertNotEqual(
            MATERIAL_CEILINGS["ptfe-film"]["breakdown_field_v_per_m"], 1.0
        )

    def test_every_family_has_positive_ceilings(self):
        for family, ceilings in MATERIAL_CEILINGS.items():
            for key, value in ceilings.items():
                self.assertGreater(value, 0.0, "%s.%s" % (family, key))

    def test_differential_ceiling_is_below_absolute_ceiling(self):
        for family, ceilings in MATERIAL_CEILINGS.items():
            self.assertLess(
                ceilings["differential_potential_ceiling_v"],
                ceilings["absolute_potential_ceiling_v"],
                family,
            )

    def test_unknown_family_raises(self):
        with self.assertRaises(ValueError):
            material_ceilings("beryllium-foil")

    def test_blank_family_raises(self):
        with self.assertRaises(ValueError):
            material_ceilings("   ")

    def test_non_string_family_raises(self):
        with self.assertRaises(ValueError):
            material_ceilings(7)


class TestFieldAndPotential(unittest.TestCase):
    def test_internal_field_is_potential_over_thickness(self):
        self.assertAlmostEqual(internal_field(250.0, 2.5e-5), 1.0e7, places=3)

    def test_potential_at_field_is_the_inverse(self):
        self.assertAlmostEqual(potential_at_field(1.0e7, 2.5e-5), 250.0, places=9)

    def test_field_and_potential_round_trip(self):
        field = internal_field(311.0, 4.0e-5)
        self.assertAlmostEqual(potential_at_field(field, 4.0e-5), 311.0, places=9)

    def test_zero_potential_gives_zero_field(self):
        self.assertAlmostEqual(internal_field(0.0, 2.5e-5), 0.0, places=9)

    def test_thinner_layer_raises_the_field(self):
        self.assertGreater(internal_field(200.0, 1.0e-5), internal_field(200.0, 2.0e-5))

    def test_zero_thickness_raises(self):
        with self.assertRaises(ValueError):
            internal_field(200.0, 0.0)

    def test_negative_potential_raises(self):
        with self.assertRaises(ValueError):
            internal_field(-200.0, 2.5e-5)

    def test_zero_field_ceiling_raises(self):
        with self.assertRaises(ValueError):
            potential_at_field(0.0, 2.5e-5)

    def test_non_numeric_thickness_raises(self):
        with self.assertRaises(ValueError):
            potential_at_field(1.0e7, "thin")


class TestMinimumThickness(unittest.TestCase):
    def test_thickness_covers_the_requested_potential(self):
        t = minimum_thickness_for_potential(500.0, 1.0e7)
        self.assertAlmostEqual(potential_at_field(1.0e7, t), 500.0, places=9)

    def test_safety_factor_thickens_the_layer(self):
        t1 = minimum_thickness_for_potential(500.0, 1.0e7, 1.0)
        t2 = minimum_thickness_for_potential(500.0, 1.0e7, 2.0)
        self.assertAlmostEqual(t2 / t1, 2.0, places=9)

    def test_zero_potential_raises(self):
        with self.assertRaises(ValueError):
            minimum_thickness_for_potential(0.0, 1.0e7)

    def test_safety_factor_below_unity_raises(self):
        with self.assertRaises(ValueError):
            minimum_thickness_for_potential(500.0, 1.0e7, 0.9)

    def test_zero_field_raises(self):
        with self.assertRaises(ValueError):
            minimum_thickness_for_potential(500.0, 0.0)


class TestPermittedPotential(unittest.TestCase):
    def test_thin_layer_is_bound_by_the_breakdown_field(self):
        result = permitted_surface_potential("polyimide-film", 2.5e-5)
        self.assertEqual(result["binding_source"], "dielectric-breakdown-field")
        self.assertAlmostEqual(result["permitted_potential_v"], 250.0, places=9)

    def test_thick_layer_is_bound_by_the_critical_potential(self):
        result = permitted_surface_potential("polyimide-film", 1.0e-4)
        self.assertEqual(result["binding_source"], "critical-differential-potential")
        self.assertAlmostEqual(result["permitted_potential_v"], 500.0, places=9)

    def test_thickening_a_potential_bound_layer_buys_no_margin(self):
        thin = permitted_surface_potential("polyimide-film", 1.0e-4)
        thicker = permitted_surface_potential("polyimide-film", 5.0e-4)
        self.assertAlmostEqual(
            thin["permitted_potential_v"], thicker["permitted_potential_v"], places=9
        )
        self.assertFalse(thicker["thickening_buys_margin"])

    def test_thickening_a_field_bound_layer_buys_margin(self):
        thin = permitted_surface_potential("polyimide-film", 1.0e-5)
        thicker = permitted_surface_potential("polyimide-film", 2.0e-5)
        self.assertGreater(
            thicker["permitted_potential_v"], thin["permitted_potential_v"]
        )
        self.assertTrue(thicker["thickening_buys_margin"])

    def test_safety_factor_divides_the_binding_ceiling(self):
        result = permitted_surface_potential("polyimide-film", 1.0e-4, 2.0)
        self.assertAlmostEqual(result["permitted_potential_v"], 250.0, places=9)

    def test_mission_override_tightens_the_ceiling(self):
        result = permitted_surface_potential("polyimide-film", 1.0e-4, 1.0, 120.0)
        self.assertAlmostEqual(result["permitted_potential_v"], 120.0, places=9)
        self.assertEqual(result["binding_source"], "mission-override")
        self.assertTrue(result["override_applied"])

    def test_mission_override_can_never_raise_the_ceiling(self):
        result = permitted_surface_potential("polyimide-film", 1.0e-4, 1.0, 5000.0)
        self.assertAlmostEqual(result["permitted_potential_v"], 500.0, places=9)
        self.assertFalse(result["override_applied"])

    def test_binding_source_is_a_declared_source(self):
        for thickness in (1.0e-5, 1.0e-4):
            result = permitted_surface_potential("polyimide-film", thickness)
            self.assertIn(result["binding_source"], BINDING_SOURCES)

    def test_families_rank_by_their_critical_potential(self):
        soft = permitted_surface_potential("conductive-black-paint", 1.0e-3)
        hard = permitted_surface_potential("fused-silica-reflector", 1.0e-3)
        self.assertGreater(hard["permitted_potential_v"], soft["permitted_potential_v"])

    def test_safety_factor_below_unity_raises(self):
        with self.assertRaises(ValueError):
            permitted_surface_potential("polyimide-film", 1.0e-4, 0.5)

    def test_zero_thickness_raises(self):
        with self.assertRaises(ValueError):
            permitted_surface_potential("polyimide-film", 0.0)

    def test_negative_override_raises(self):
        with self.assertRaises(ValueError):
            permitted_surface_potential("polyimide-film", 1.0e-4, 1.0, -10.0)

    def test_unknown_family_raises(self):
        with self.assertRaises(ValueError):
            permitted_surface_potential("mystery-laminate", 1.0e-4)


class TestCeilingComparison(unittest.TestCase):
    def test_below_ceiling_passes(self):
        self.assertTrue(within_ceiling(240.0, 250.0))

    def test_exactly_at_ceiling_passes(self):
        self.assertTrue(within_ceiling(250.0, 250.0))

    def test_above_ceiling_fails(self):
        self.assertFalse(within_ceiling(260.0, 250.0))

    def test_representation_error_at_the_ceiling_is_absorbed(self):
        # minimum_thickness_for_potential -> permitted_surface_potential round
        # trip lands a few ULPs under the requested potential for these inputs.
        thickness = minimum_thickness_for_potential(150.0, 1.0e7, 1.14)
        ceiling = permitted_surface_potential("polyimide-film", thickness, 1.14)
        permitted = ceiling["permitted_potential_v"]
        self.assertLess(permitted, 150.0)
        self.assertTrue(within_ceiling(150.0, permitted))
        self.assertAlmostEqual(permitted / 150.0, 1.0, places=12)

    def test_ceiling_is_not_widened_by_the_tolerance(self):
        self.assertFalse(within_ceiling(250.0 * 1.0001, 250.0))

    def test_non_finite_value_raises(self):
        with self.assertRaises(ValueError):
            within_ceiling(float("nan"), 250.0)


class TestMarginAndVerdict(unittest.TestCase):
    def test_margin_is_the_unused_fraction(self):
        self.assertAlmostEqual(potential_margin(250.0, 200.0), 0.2, places=12)

    def test_margin_is_negative_when_exceeded(self):
        self.assertLess(potential_margin(250.0, 300.0), 0.0)

    def test_margin_is_one_at_zero_potential(self):
        self.assertAlmostEqual(potential_margin(250.0, 0.0), 1.0, places=12)

    def test_zero_permitted_raises(self):
        with self.assertRaises(ValueError):
            potential_margin(0.0, 100.0)

    def test_negative_predicted_raises(self):
        with self.assertRaises(ValueError):
            potential_margin(250.0, -10.0)

    def test_comfortable_surface_is_compliant(self):
        self.assertEqual(discharge_onset_verdict(250.0, 100.0), "compliant")

    def test_marginal_ratio_edge_is_still_compliant(self):
        self.assertEqual(
            discharge_onset_verdict(250.0, 250.0 * MARGINAL_RATIO), "compliant"
        )

    def test_just_above_the_marginal_ratio_is_marginal(self):
        self.assertEqual(discharge_onset_verdict(250.0, 230.0), "marginal")

    def test_at_the_ceiling_is_marginal_not_onset(self):
        self.assertEqual(discharge_onset_verdict(250.0, 250.0), "marginal")

    def test_above_the_ceiling_is_discharge_onset(self):
        self.assertEqual(discharge_onset_verdict(250.0, 400.0), "discharge-onset")

    def test_verdicts_are_declared_verdicts(self):
        for predicted in (10.0, 230.0, 400.0):
            self.assertIn(discharge_onset_verdict(250.0, predicted), VERDICTS)


class TestEvaluateSurface(unittest.TestCase):
    def test_field_bound_surface_reports_its_binding_constraint(self):
        result = evaluate_surface(good_surface())
        self.assertEqual(result["binding_source"], "dielectric-breakdown-field")
        self.assertTrue(result["compliant"])

    def test_predicted_field_is_computed_from_the_thickness(self):
        result = evaluate_surface(good_surface())
        self.assertAlmostEqual(result["internal_field_v_per_m"], 6.0e6, places=1)

    def test_exceeding_surface_carries_a_potential_finding(self):
        result = evaluate_surface(good_surface(predicted_potential_v=900.0))
        self.assertFalse(result["potential_ok"])
        self.assertEqual(result["verdict"], "discharge-onset")
        self.assertTrue(any("above permitted" in f for f in result["findings"]))

    def test_exceeding_surface_also_flags_the_internal_field(self):
        result = evaluate_surface(good_surface(predicted_potential_v=900.0))
        self.assertFalse(result["field_ok"])
        self.assertEqual(len(result["findings"]), 2)

    def test_thick_surface_can_fail_on_potential_while_field_is_fine(self):
        result = evaluate_surface(
            good_surface(thickness_m=1.0e-3, predicted_potential_v=700.0)
        )
        self.assertFalse(result["potential_ok"])
        self.assertTrue(result["field_ok"])
        self.assertEqual(len(result["findings"]), 1)

    def test_mission_override_can_turn_a_pass_into_a_finding(self):
        result = evaluate_surface(good_surface(mission_override_v=100.0))
        self.assertFalse(result["potential_ok"])
        self.assertEqual(result["binding_source"], "mission-override")

    def test_safety_factor_reduces_the_margin(self):
        plain = evaluate_surface(good_surface())
        factored = evaluate_surface(good_surface(safety_factor=1.5))
        self.assertLess(factored["margin_fraction"], plain["margin_fraction"])

    def test_surface_without_predicted_potential_raises(self):
        surface = good_surface()
        del surface["predicted_potential_v"]
        with self.assertRaises(ValueError):
            evaluate_surface(surface)

    def test_surface_without_name_raises(self):
        with self.assertRaises(ValueError):
            evaluate_surface(good_surface(name=""))

    def test_surface_without_material_family_raises(self):
        surface = good_surface()
        del surface["material_family"]
        with self.assertRaises(ValueError):
            evaluate_surface(surface)

    def test_surface_without_thickness_raises(self):
        surface = good_surface()
        del surface["thickness_m"]
        with self.assertRaises(ValueError):
            evaluate_surface(surface)

    def test_non_mapping_surface_raises(self):
        with self.assertRaises(ValueError):
            evaluate_surface("blanket")


class TestEvaluateSurfaceSet(unittest.TestCase):
    def setUp(self):
        self.surfaces = [
            good_surface(),
            good_surface(
                name="coverglass-front-face",
                material_family="borosilicate-coverglass",
                thickness_m=1.0e-4,
                predicted_potential_v=300.0,
            ),
            good_surface(
                name="black-paint-panel",
                material_family="conductive-black-paint",
                thickness_m=5.0e-4,
                predicted_potential_v=900.0,
            ),
        ]

    def test_counts_split_compliant_and_onset(self):
        summary = evaluate_surface_set(self.surfaces)
        self.assertEqual(summary["surface_count"], 3)
        self.assertEqual(summary["compliant_count"], 2)
        self.assertEqual(summary["onset_count"], 1)

    def test_set_is_not_compliant_while_a_finding_is_open(self):
        summary = evaluate_surface_set(self.surfaces)
        self.assertFalse(summary["set_compliant"])
        self.assertTrue(summary["open_findings"])

    def test_worst_surface_is_the_lowest_margin(self):
        summary = evaluate_surface_set(self.surfaces)
        self.assertEqual(summary["worst_surface"], "black-paint-panel")
        self.assertLess(summary["worst_margin_fraction"], 0.0)

    def test_binding_mix_is_reported(self):
        summary = evaluate_surface_set(self.surfaces)
        self.assertEqual(sum(summary["binding_mix"].values()), 3)
        for source in summary["binding_mix"]:
            self.assertIn(source, BINDING_SOURCES)

    def test_clean_set_is_compliant(self):
        summary = evaluate_surface_set(self.surfaces[:2])
        self.assertTrue(summary["set_compliant"])
        self.assertEqual(summary["open_findings"], [])

    def test_marginal_surface_is_counted_without_a_finding(self):
        summary = evaluate_surface_set(
            [good_surface(predicted_potential_v=245.0)]
        )
        self.assertEqual(summary["marginal_count"], 1)
        self.assertTrue(summary["set_compliant"])

    def test_empty_set_raises(self):
        with self.assertRaises(ValueError):
            evaluate_surface_set([])

    def test_duplicate_surface_name_raises(self):
        with self.assertRaises(ValueError):
            evaluate_surface_set([good_surface(), good_surface()])

    def test_non_list_set_raises(self):
        with self.assertRaises(ValueError):
            evaluate_surface_set(good_surface())


if __name__ == "__main__":
    unittest.main()
