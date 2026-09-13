#!/usr/bin/env python3
"""Contract tests for the clause 6.3.3.6 restricted-dielectric leaf."""

import math
import unittest

from e2006_restricted_dielectric_materials_logic import (
    DISCHARGE_ONSET_V,
    NEGLIGIBLE_AREA_M2,
    RESTRICTED_BULK_RESISTIVITY_OHM_M,
    RESTRICTED_REGISTER,
    RESTRICTED_SURFACE_RESISTIVITY_OHM_SQ,
    differential_potential_v,
    evaluate_external_dielectrics,
    evaluate_item,
    is_restricted_dielectric,
    normalize_item,
    registered_restriction,
    restriction_reasons,
    validate_charging_waiver,
    waiver_findings,
    within_discharge_onset,
)


def item(name="thermal-blanket-outer-layer", material="uncoated-polyimide-film",
         **overrides):
    record = {"name": name, "material": material, "exposure": "external",
              "exposed_area_m2": 0.8}
    record.update(overrides)
    return record


def waiver(**overrides):
    record = {
        "dimensionality": "three-dimensional",
        "items_modelled": ["thermal-blanket-outer-layer"],
        "environment_case": "geostationary-substorm",
        "environment_bounds_worst_case": True,
        "eclipse_entry_covered": True,
        "surface_potential_v": -250.0,
        "structure_potential_v": 0.0,
    }
    record.update(overrides)
    return record


class RegisterTests(unittest.TestCase):
    def test_registered_family_resolves(self):
        out = registered_restriction("uncoated-polyimide-film")
        self.assertIsNotNone(out)
        self.assertAlmostEqual(out["bulk_resistivity_ohm_m"], 1.0e16)

    def test_lookup_is_case_and_space_insensitive(self):
        self.assertIsNotNone(registered_restriction("  PolyTetraFluoroEthylene-Sheet "))

    def test_unregistered_family_returns_nothing(self):
        self.assertIsNone(registered_restriction("conductive-black-paint"))

    def test_every_register_entry_is_above_the_bulk_threshold(self):
        for name in RESTRICTED_REGISTER:
            entry = registered_restriction(name)
            self.assertGreater(
                entry["bulk_resistivity_ohm_m"], RESTRICTED_BULK_RESISTIVITY_OHM_M
            )

    def test_blank_material_rejected(self):
        with self.assertRaises(ValueError):
            registered_restriction("  ")

    def test_non_string_material_rejected(self):
        with self.assertRaises(ValueError):
            registered_restriction(17)


class NormalizeItemTests(unittest.TestCase):
    def test_registered_material_inherits_register_resistivities(self):
        out = normalize_item(item())
        self.assertTrue(out["registered"])
        self.assertAlmostEqual(out["bulk_resistivity_ohm_m"], 1.0e16)

    def test_measured_values_override_the_register(self):
        out = normalize_item(item(bulk_resistivity_ohm_m=1.0e9))
        self.assertAlmostEqual(out["bulk_resistivity_ohm_m"], 1.0e9)

    def test_exposure_defaults_to_external(self):
        out = normalize_item(
            {"name": "cover-glass", "material": "uncoated-fused-silica-cover",
             "exposed_area_m2": 0.2}
        )
        self.assertEqual(out["exposure"], "external")

    def test_unregistered_material_defaults_to_zero_resistivity(self):
        out = normalize_item(item(material="conductive-black-paint"))
        self.assertFalse(out["registered"])
        self.assertAlmostEqual(out["bulk_resistivity_ohm_m"], 0.0)

    def test_missing_name_rejected(self):
        record = item()
        del record["name"]
        with self.assertRaises(ValueError):
            normalize_item(record)

    def test_missing_material_rejected(self):
        record = item()
        del record["material"]
        with self.assertRaises(ValueError):
            normalize_item(record)

    def test_unknown_exposure_rejected(self):
        with self.assertRaises(ValueError):
            normalize_item(item(exposure="buried"))

    def test_internal_item_with_exposed_area_rejected(self):
        with self.assertRaises(ValueError):
            normalize_item(item(exposure="internal", exposed_area_m2=0.5))

    def test_negative_area_rejected(self):
        with self.assertRaises(ValueError):
            normalize_item(item(exposed_area_m2=-0.1))

    def test_non_numeric_area_rejected(self):
        with self.assertRaises(ValueError):
            normalize_item(item(exposed_area_m2="0.8"))

    def test_infinite_resistivity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_item(item(surface_resistivity_ohm_sq=math.inf))

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            normalize_item("thermal-blanket-outer-layer")


class RestrictionTests(unittest.TestCase):
    def test_registered_external_material_is_restricted(self):
        self.assertTrue(is_restricted_dielectric(item()))

    def test_internal_item_is_not_restricted_by_this_clause(self):
        self.assertFalse(
            is_restricted_dielectric(
                item(exposure="internal", exposed_area_m2=0.0)
            )
        )

    def test_negligible_exposed_area_is_exempt(self):
        self.assertFalse(
            is_restricted_dielectric(item(exposed_area_m2=NEGLIGIBLE_AREA_M2))
        )

    def test_area_just_above_the_exemption_is_restricted(self):
        self.assertTrue(
            is_restricted_dielectric(item(exposed_area_m2=NEGLIGIBLE_AREA_M2 * 1.01))
        )

    def test_unregistered_but_insulating_material_is_restricted(self):
        reasons = restriction_reasons(
            normalize_item(
                item(
                    material="proprietary-polymer-film",
                    bulk_resistivity_ohm_m=RESTRICTED_BULK_RESISTIVITY_OHM_M * 10.0,
                )
            )
        )
        self.assertEqual(len(reasons), 1)
        self.assertIn("bulk resistivity", reasons[0])

    def test_surface_resistivity_alone_can_restrict(self):
        reasons = restriction_reasons(
            normalize_item(
                item(
                    material="proprietary-polymer-film",
                    surface_resistivity_ohm_sq=RESTRICTED_SURFACE_RESISTIVITY_OHM_SQ
                    * 10.0,
                )
            )
        )
        self.assertEqual(len(reasons), 1)
        self.assertIn("surface resistivity", reasons[0])

    def test_material_exactly_at_the_bulk_threshold_is_not_restricted(self):
        reasons = restriction_reasons(
            normalize_item(
                item(
                    material="proprietary-polymer-film",
                    bulk_resistivity_ohm_m=RESTRICTED_BULK_RESISTIVITY_OHM_M,
                )
            )
        )
        self.assertEqual(reasons, [])

    def test_conductive_unregistered_material_is_not_restricted(self):
        self.assertFalse(
            is_restricted_dielectric(
                item(material="conductive-black-paint",
                     bulk_resistivity_ohm_m=1.0e-1,
                     surface_resistivity_ohm_sq=1.0e5)
            )
        )

    def test_registered_material_reports_every_reason(self):
        reasons = restriction_reasons(normalize_item(item()))
        self.assertEqual(len(reasons), 3)


class PotentialTests(unittest.TestCase):
    def test_difference_is_a_magnitude(self):
        self.assertAlmostEqual(differential_potential_v(-250.0, 0.0), 250.0)

    def test_structure_bias_is_taken_into_account(self):
        self.assertAlmostEqual(differential_potential_v(-250.0, -100.0), 150.0)

    def test_non_finite_potential_rejected(self):
        with self.assertRaises(ValueError):
            differential_potential_v(math.nan, 0.0)

    def test_non_numeric_potential_rejected(self):
        with self.assertRaises(ValueError):
            differential_potential_v("-250", 0.0)

    def test_below_onset_is_within(self):
        self.assertTrue(within_discharge_onset(399.0))

    def test_exactly_at_onset_is_within(self):
        self.assertTrue(within_discharge_onset(DISCHARGE_ONSET_V))

    def test_onset_boundary_with_representation_drift_is_within(self):
        drifted = differential_potential_v(-1660.57, -2060.57)
        self.assertAlmostEqual(drifted, DISCHARGE_ONSET_V)
        self.assertGreater(drifted, DISCHARGE_ONSET_V)
        self.assertTrue(within_discharge_onset(drifted))

    def test_above_onset_is_not_within(self):
        self.assertFalse(within_discharge_onset(400.5))

    def test_project_onset_can_be_tightened(self):
        self.assertFalse(within_discharge_onset(250.0, onset_v=200.0))

    def test_zero_onset_rejected(self):
        with self.assertRaises(ValueError):
            within_discharge_onset(100.0, onset_v=0.0)

    def test_negative_differential_rejected(self):
        with self.assertRaises(ValueError):
            within_discharge_onset(-10.0)


class WaiverValidationTests(unittest.TestCase):
    def test_valid_waiver_is_normalized(self):
        out = validate_charging_waiver(waiver())
        self.assertAlmostEqual(out["differential_potential_v"], 250.0)
        self.assertAlmostEqual(out["discharge_onset_v"], DISCHARGE_ONSET_V)

    def test_structure_potential_defaults_to_zero(self):
        record = waiver()
        del record["structure_potential_v"]
        out = validate_charging_waiver(record)
        self.assertAlmostEqual(out["structure_potential_v"], 0.0)

    def test_project_onset_is_carried_through(self):
        out = validate_charging_waiver(waiver(discharge_onset_v=200.0))
        self.assertAlmostEqual(out["discharge_onset_v"], 200.0)

    def test_unknown_dimensionality_rejected(self):
        with self.assertRaises(ValueError):
            validate_charging_waiver(waiver(dimensionality="axisymmetric"))

    def test_missing_environment_case_rejected(self):
        record = waiver()
        del record["environment_case"]
        with self.assertRaises(ValueError):
            validate_charging_waiver(record)

    def test_non_boolean_envelope_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_charging_waiver(waiver(environment_bounds_worst_case="yes"))

    def test_missing_eclipse_flag_rejected(self):
        record = waiver()
        del record["eclipse_entry_covered"]
        with self.assertRaises(ValueError):
            validate_charging_waiver(record)

    def test_modelled_items_must_be_a_list(self):
        with self.assertRaises(ValueError):
            validate_charging_waiver(waiver(items_modelled="blanket"))

    def test_modelled_item_entries_must_be_names(self):
        with self.assertRaises(ValueError):
            validate_charging_waiver(waiver(items_modelled=[None]))

    def test_missing_surface_potential_rejected(self):
        record = waiver()
        del record["surface_potential_v"]
        with self.assertRaises(ValueError):
            validate_charging_waiver(record)

    def test_non_mapping_waiver_rejected(self):
        with self.assertRaises(ValueError):
            validate_charging_waiver("three-dimensional")


class WaiverFindingTests(unittest.TestCase):
    def setUp(self):
        self.normalized_item = normalize_item(item())

    def test_absent_waiver_is_a_finding(self):
        out = waiver_findings(None, self.normalized_item)
        self.assertEqual(len(out), 1)

    def test_complete_waiver_leaves_no_finding(self):
        out = waiver_findings(validate_charging_waiver(waiver()), self.normalized_item)
        self.assertEqual(out, [])

    def test_two_dimensional_reduction_is_a_finding(self):
        out = waiver_findings(
            validate_charging_waiver(waiver(dimensionality="two-dimensional")),
            self.normalized_item,
        )
        self.assertTrue(any("reduction" in entry for entry in out))

    def test_item_outside_the_modelled_geometry_is_a_finding(self):
        out = waiver_findings(
            validate_charging_waiver(waiver(items_modelled=["antenna-radome"])),
            self.normalized_item,
        )
        self.assertTrue(any("modelled geometry" in entry for entry in out))

    def test_environment_shortfall_is_a_finding(self):
        out = waiver_findings(
            validate_charging_waiver(waiver(environment_bounds_worst_case=False)),
            self.normalized_item,
        )
        self.assertTrue(any("worst case" in entry for entry in out))

    def test_missing_eclipse_coverage_is_a_finding(self):
        out = waiver_findings(
            validate_charging_waiver(waiver(eclipse_entry_covered=False)),
            self.normalized_item,
        )
        self.assertTrue(any("eclipse-entry" in entry for entry in out))

    def test_potential_above_onset_is_a_finding(self):
        out = waiver_findings(
            validate_charging_waiver(waiver(surface_potential_v=-1500.0)),
            self.normalized_item,
        )
        self.assertTrue(any("discharge-onset" in entry for entry in out))

    def test_potential_exactly_on_onset_is_accepted(self):
        out = waiver_findings(
            validate_charging_waiver(
                waiver(surface_potential_v=-1660.57, structure_potential_v=-2060.57)
            ),
            self.normalized_item,
        )
        self.assertEqual(out, [])

    def test_several_shortfalls_are_reported_together(self):
        out = waiver_findings(
            validate_charging_waiver(
                waiver(
                    dimensionality="one-dimensional",
                    eclipse_entry_covered=False,
                    surface_potential_v=-1500.0,
                )
            ),
            self.normalized_item,
        )
        self.assertEqual(len(out), 3)


class ItemEvaluationTests(unittest.TestCase):
    def test_restricted_item_with_a_sound_waiver_is_permitted(self):
        out = evaluate_item(item(), waiver())
        self.assertTrue(out["restricted"])
        self.assertTrue(out["permitted"])

    def test_restricted_item_without_a_waiver_is_barred(self):
        out = evaluate_item(item())
        self.assertTrue(out["restricted"])
        self.assertFalse(out["permitted"])

    def test_unrestricted_item_needs_no_waiver(self):
        out = evaluate_item(
            item(material="conductive-black-paint",
                 bulk_resistivity_ohm_m=1.0e-1,
                 surface_resistivity_ohm_sq=1.0e5)
        )
        self.assertFalse(out["restricted"])
        self.assertTrue(out["permitted"])
        self.assertEqual(out["findings"], [])

    def test_internal_item_needs_no_waiver(self):
        out = evaluate_item(item(exposure="internal", exposed_area_m2=0.0))
        self.assertTrue(out["permitted"])

    def test_restriction_reasons_are_reported(self):
        out = evaluate_item(item())
        self.assertEqual(len(out["restriction_reasons"]), 3)

    def test_invalid_waiver_is_rejected_not_ignored(self):
        with self.assertRaises(ValueError):
            evaluate_item(item(), waiver(dimensionality="axisymmetric"))


class InventoryTests(unittest.TestCase):
    def build(self):
        blanket = item()
        blanket["waiver"] = waiver()
        cover = item(
            name="cover-glass", material="uncoated-fused-silica-cover",
            exposed_area_m2=1.2
        )
        cover["waiver"] = waiver(
            items_modelled=["cover-glass"], surface_potential_v=-320.0
        )
        paint = item(
            name="radiator-paint", material="conductive-black-paint",
            bulk_resistivity_ohm_m=1.0e-1, surface_resistivity_ohm_sq=1.0e5
        )
        return [blanket, cover, paint]

    def test_compliant_inventory_reports_no_barred_item(self):
        out = evaluate_external_dielectrics(self.build())
        self.assertTrue(out["compliant"])
        self.assertEqual(out["restricted_count"], 2)
        self.assertEqual(out["barred_items"], [])

    def test_missing_waiver_bars_one_item(self):
        inventory = self.build()
        del inventory[1]["waiver"]
        out = evaluate_external_dielectrics(inventory)
        self.assertFalse(out["compliant"])
        self.assertEqual(out["barred_items"], ["cover-glass"])

    def test_findings_are_aggregated(self):
        inventory = self.build()
        inventory[0]["waiver"] = waiver(dimensionality="two-dimensional")
        del inventory[1]["waiver"]
        out = evaluate_external_dielectrics(inventory)
        self.assertEqual(len(out["barred_items"]), 2)
        self.assertGreaterEqual(len(out["findings"]), 2)

    def test_inventory_must_be_a_list(self):
        with self.assertRaises(ValueError):
            evaluate_external_dielectrics(self.build()[0])

    def test_empty_inventory_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_external_dielectrics([])

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_external_dielectrics(["thermal-blanket-outer-layer"])

    def test_duplicate_item_names_rejected(self):
        inventory = self.build()
        inventory[2]["name"] = "cover-glass"
        with self.assertRaises(ValueError):
            evaluate_external_dielectrics(inventory)

    def test_inventory_evaluation_is_deterministic(self):
        self.assertEqual(
            evaluate_external_dielectrics(self.build()),
            evaluate_external_dielectrics(self.build()),
        )


if __name__ == "__main__":
    unittest.main()
