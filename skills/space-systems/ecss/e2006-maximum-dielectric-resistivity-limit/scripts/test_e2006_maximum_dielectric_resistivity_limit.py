#!/usr/bin/env python3
"""Gate 3 contract test for e2006-maximum-dielectric-resistivity-limit."""

import unittest

from e2006_maximum_dielectric_resistivity_limit_logic import (
    CONDUCTIVE_REGIME_MAX_OHM_M,
    DISSIPATIVE_REGIME_MAX_OHM_M,
    assess_dielectric_inventory,
    bounding_charging_current_density,
    bulk_potential_drop,
    categorize_resistivity_regime,
    evaluate_dielectric,
    maximum_bulk_resistivity,
    maximum_dielectric_thickness,
    maximum_sheet_resistivity,
    net_charging_current_density,
    resistivity_margin,
    sheet_potential_drop,
    within_ceiling,
)

# Representative GEO substorm driver and a 100 um polyimide film.
J_GEO = 1.0e-6          # A/m^2
THICKNESS = 1.0e-4      # m
V_ALLOW = 100.0         # V


class RatioMixin(unittest.TestCase):
    def assertRatio(self, value, expected, places=12):
        """Compare two floats spanning many decades without a bare ==."""
        self.assertAlmostEqual(value / expected, 1.0, places=places)


class TestCurrentDensityBalance(RatioMixin):
    def test_bare_electron_flux_is_the_net_driver(self):
        net = net_charging_current_density(2.0e-6)
        self.assertRatio(net, 2.0e-6)

    def test_secondary_and_backscatter_reduce_the_driver(self):
        net = net_charging_current_density(2.0e-6, secondary_yield=0.4, backscatter_yield=0.1)
        self.assertRatio(net, 1.0e-6)

    def test_photoemission_and_ions_offset_collection(self):
        net = net_charging_current_density(
            2.0e-6, ion_flux_density_a_m2=3.0e-7, photoemission_density_a_m2=7.0e-7
        )
        self.assertRatio(net, 1.0e-6)

    def test_high_secondary_yield_flips_the_sign(self):
        net = net_charging_current_density(1.0e-6, secondary_yield=1.5)
        self.assertLess(net, 0.0)
        self.assertRatio(abs(net), 5.0e-7)

    def test_bounding_density_takes_the_magnitude(self):
        magnitude = bounding_charging_current_density(1.0e-6, secondary_yield=1.5)
        self.assertRatio(magnitude, 5.0e-7)

    def test_cancelling_environment_is_rejected(self):
        with self.assertRaises(ValueError):
            bounding_charging_current_density(1.0e-6, photoemission_density_a_m2=1.0e-6)

    def test_zero_electron_flux_is_rejected(self):
        with self.assertRaises(ValueError):
            net_charging_current_density(0.0)

    def test_negative_ion_flux_is_rejected(self):
        with self.assertRaises(ValueError):
            net_charging_current_density(1.0e-6, ion_flux_density_a_m2=-1.0e-9)

    def test_backscatter_yield_above_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            net_charging_current_density(1.0e-6, backscatter_yield=1.2)

    def test_absurd_secondary_yield_is_rejected(self):
        with self.assertRaises(ValueError):
            net_charging_current_density(1.0e-6, secondary_yield=25.0)

    def test_boolean_input_is_rejected(self):
        with self.assertRaises(ValueError):
            net_charging_current_density(True)


class TestCeilingDerivation(RatioMixin):
    def test_bulk_ceiling_matches_ohms_law_inversion(self):
        ceiling = maximum_bulk_resistivity(V_ALLOW, J_GEO, THICKNESS)
        self.assertRatio(ceiling, 1.0e12)

    def test_thicker_film_lowers_the_bulk_ceiling(self):
        thin = maximum_bulk_resistivity(V_ALLOW, J_GEO, THICKNESS)
        thick = maximum_bulk_resistivity(V_ALLOW, J_GEO, THICKNESS * 10.0)
        self.assertLess(thick, thin)
        self.assertRatio(thin / thick, 10.0)

    def test_bulk_ceiling_round_trips_through_the_potential_drop(self):
        ceiling = maximum_bulk_resistivity(V_ALLOW, J_GEO, THICKNESS)
        self.assertRatio(bulk_potential_drop(ceiling, J_GEO, THICKNESS), V_ALLOW)

    def test_sheet_ceiling_is_quadratic_in_bleed_path_length(self):
        short = maximum_sheet_resistivity(V_ALLOW, J_GEO, 0.1)
        long_path = maximum_sheet_resistivity(V_ALLOW, J_GEO, 0.2)
        self.assertRatio(short / long_path, 4.0)

    def test_sheet_ceiling_round_trips_through_the_sheet_drop(self):
        ceiling = maximum_sheet_resistivity(V_ALLOW, J_GEO, 0.5)
        self.assertRatio(sheet_potential_drop(ceiling, J_GEO, 0.5), V_ALLOW)

    def test_maximum_thickness_is_the_inverse_derivation(self):
        t_max = maximum_dielectric_thickness(1.0e12, J_GEO, V_ALLOW)
        self.assertRatio(t_max, THICKNESS)

    def test_zero_thickness_is_rejected(self):
        with self.assertRaises(ValueError):
            maximum_bulk_resistivity(V_ALLOW, J_GEO, 0.0)

    def test_negative_allowable_potential_is_rejected(self):
        with self.assertRaises(ValueError):
            maximum_bulk_resistivity(-1.0, J_GEO, THICKNESS)

    def test_zero_current_density_is_rejected(self):
        with self.assertRaises(ValueError):
            maximum_sheet_resistivity(V_ALLOW, 0.0, 0.5)

    def test_non_numeric_bleed_path_is_rejected(self):
        with self.assertRaises(ValueError):
            maximum_sheet_resistivity(V_ALLOW, J_GEO, "0.5")


class TestMarginAndRegime(RatioMixin):
    def test_margin_is_positive_below_the_ceiling(self):
        self.assertRatio(resistivity_margin(5.0e11, 1.0e12), 1.0)

    def test_margin_is_zero_at_the_ceiling(self):
        self.assertAlmostEqual(resistivity_margin(1.0e12, 1.0e12), 0.0, places=12)

    def test_margin_is_negative_above_the_ceiling(self):
        self.assertLess(resistivity_margin(2.0e12, 1.0e12), 0.0)

    def test_margin_rejects_zero_resistivity(self):
        with self.assertRaises(ValueError):
            resistivity_margin(0.0, 1.0e12)

    def test_regime_bands(self):
        self.assertEqual(categorize_resistivity_regime(1.0e2), "conductive")
        self.assertEqual(categorize_resistivity_regime(1.0e7), "static-dissipative")
        self.assertEqual(categorize_resistivity_regime(1.0e15), "insulating")

    def test_regime_band_edges_are_upper_exclusive(self):
        self.assertEqual(
            categorize_resistivity_regime(CONDUCTIVE_REGIME_MAX_OHM_M), "static-dissipative"
        )
        self.assertEqual(
            categorize_resistivity_regime(DISSIPATIVE_REGIME_MAX_OHM_M), "insulating"
        )

    def test_regime_rejects_negative_resistivity(self):
        with self.assertRaises(ValueError):
            categorize_resistivity_regime(-1.0)


class TestCeilingComparison(RatioMixin):
    def test_value_below_ceiling_passes(self):
        self.assertTrue(within_ceiling(9.0e11, 1.0e12))

    def test_value_above_ceiling_fails(self):
        self.assertFalse(within_ceiling(1.1e12, 1.0e12))

    def test_exact_boundary_passes(self):
        self.assertTrue(within_ceiling(1.0e12, 1.0e12))

    def test_representation_drift_at_the_boundary_is_absorbed(self):
        drifted = 0.1 + 0.2  # 0.30000000000000004
        self.assertGreater(drifted, 0.3)
        self.assertTrue(within_ceiling(drifted, 0.3))

    def test_drift_absorption_does_not_widen_the_engineering_limit(self):
        self.assertFalse(within_ceiling(0.3 * (1.0 + 1.0e-6), 0.3))


class TestItemEvaluation(RatioMixin):
    def base_item(self, **overrides):
        item = {
            "id": "outer-mli-layer",
            "resistivity_ohm_m": 5.0e11,
            "thickness_m": THICKNESS,
        }
        item.update(overrides)
        return item

    def test_compliant_item_reports_positive_margin(self):
        result = evaluate_dielectric(self.base_item(), J_GEO, default_allowable_potential_v=V_ALLOW)
        self.assertEqual(result["disposition"], "compliant")
        self.assertTrue(result["bulk_within_ceiling"])
        self.assertGreater(result["bulk_margin"], 0.0)
        self.assertEqual(result["findings"], [])

    def test_bare_insulator_above_ceiling_is_categorized_as_exceeding(self):
        result = evaluate_dielectric(
            self.base_item(resistivity_ohm_m=1.0e15), J_GEO, default_allowable_potential_v=V_ALLOW
        )
        self.assertEqual(result["disposition"], "ceiling-exceeded")
        self.assertEqual(result["regime"], "insulating")
        self.assertIn("no bleed path declared", result["findings"][0])

    def test_compliant_coating_mitigates_a_bulk_exceedance(self):
        result = evaluate_dielectric(
            self.base_item(
                resistivity_ohm_m=1.0e15,
                coating_sheet_resistivity_ohm_sq=1.0e7,
                bleed_path_length_m=0.2,
            ),
            J_GEO,
            default_allowable_potential_v=V_ALLOW,
        )
        self.assertEqual(result["disposition"], "mitigated-by-bleed-path")
        self.assertTrue(result["sheet_within_ceiling"])
        self.assertRatio(result["sheet_ceiling_ohm_sq"], 5.0e9)

    def test_failing_coating_leaves_the_item_exceeding(self):
        result = evaluate_dielectric(
            self.base_item(
                resistivity_ohm_m=1.0e15,
                coating_sheet_resistivity_ohm_sq=1.0e12,
                bleed_path_length_m=0.2,
            ),
            J_GEO,
            default_allowable_potential_v=V_ALLOW,
        )
        self.assertEqual(result["disposition"], "ceiling-exceeded")
        self.assertFalse(result["sheet_within_ceiling"])
        self.assertEqual(len(result["findings"]), 2)

    def test_item_level_allowable_overrides_the_default(self):
        tight = evaluate_dielectric(
            self.base_item(allowable_potential_v=10.0), J_GEO, default_allowable_potential_v=V_ALLOW
        )
        self.assertEqual(tight["disposition"], "ceiling-exceeded")
        self.assertRatio(tight["bulk_ceiling_ohm_m"], 1.0e11)

    def test_missing_allowable_is_a_finding_not_a_default(self):
        with self.assertRaises(ValueError):
            evaluate_dielectric(self.base_item(), J_GEO)

    def test_missing_required_key_is_rejected(self):
        item = self.base_item()
        del item["thickness_m"]
        with self.assertRaises(ValueError):
            evaluate_dielectric(item, J_GEO, default_allowable_potential_v=V_ALLOW)

    def test_unknown_key_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_dielectric(
                self.base_item(bogus_key=1.0), J_GEO, default_allowable_potential_v=V_ALLOW
            )

    def test_half_declared_coating_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_dielectric(
                self.base_item(coating_sheet_resistivity_ohm_sq=1.0e7),
                J_GEO,
                default_allowable_potential_v=V_ALLOW,
            )

    def test_blank_item_id_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_dielectric(
                self.base_item(id="  "), J_GEO, default_allowable_potential_v=V_ALLOW
            )

    def test_non_mapping_item_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_dielectric(["outer-mli-layer"], J_GEO, default_allowable_potential_v=V_ALLOW)

    def test_exact_ceiling_item_is_compliant(self):
        ceiling = maximum_bulk_resistivity(V_ALLOW, J_GEO, THICKNESS)
        result = evaluate_dielectric(
            self.base_item(resistivity_ohm_m=ceiling), J_GEO, default_allowable_potential_v=V_ALLOW
        )
        self.assertEqual(result["disposition"], "compliant")
        self.assertAlmostEqual(result["bulk_margin"], 0.0, places=12)


class TestInventoryAssessment(RatioMixin):
    def inventory(self):
        return [
            {"id": "radiator-paint", "resistivity_ohm_m": 1.0e9, "thickness_m": 2.0e-4},
            {"id": "outer-mli-layer", "resistivity_ohm_m": 5.0e11, "thickness_m": THICKNESS},
            {
                "id": "antenna-radome",
                "resistivity_ohm_m": 1.0e15,
                "thickness_m": 1.0e-3,
                "coating_sheet_resistivity_ohm_sq": 1.0e6,
                "bleed_path_length_m": 0.3,
            },
        ]

    def test_inventory_aggregates_dispositions(self):
        summary = assess_dielectric_inventory(
            self.inventory(), J_GEO, default_allowable_potential_v=V_ALLOW
        )
        self.assertEqual(summary["counts"]["compliant"], 2)
        self.assertEqual(summary["counts"]["mitigated-by-bleed-path"], 1)
        self.assertEqual(summary["counts"]["ceiling-exceeded"], 0)
        self.assertTrue(summary["compliant"])

    def test_inventory_identifies_the_worst_margin(self):
        summary = assess_dielectric_inventory(
            self.inventory(), J_GEO, default_allowable_potential_v=V_ALLOW
        )
        self.assertEqual(summary["worst_margin_id"], "antenna-radome")
        self.assertLess(summary["worst_margin"], 0.0)

    def test_one_uncovered_exceedance_fails_the_inventory(self):
        items = self.inventory()
        items[2].pop("coating_sheet_resistivity_ohm_sq")
        items[2].pop("bleed_path_length_m")
        summary = assess_dielectric_inventory(items, J_GEO, default_allowable_potential_v=V_ALLOW)
        self.assertFalse(summary["compliant"])
        self.assertEqual(summary["counts"]["ceiling-exceeded"], 1)

    def test_duplicate_item_id_is_rejected(self):
        items = self.inventory()
        items[1]["id"] = "radiator-paint"
        with self.assertRaises(ValueError):
            assess_dielectric_inventory(items, J_GEO, default_allowable_potential_v=V_ALLOW)

    def test_empty_inventory_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_dielectric_inventory([], J_GEO, default_allowable_potential_v=V_ALLOW)

    def test_non_sequence_inventory_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_dielectric_inventory({"id": "x"}, J_GEO, default_allowable_potential_v=V_ALLOW)


if __name__ == "__main__":
    unittest.main()
