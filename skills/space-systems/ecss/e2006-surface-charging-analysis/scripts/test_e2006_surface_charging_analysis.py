#!/usr/bin/env python3
"""Gate 3 contract test for the clause 6.4 surface-charging analysis."""

import math
import unittest

import e2006_surface_charging_analysis_logic as logic


SUBSTORM = {
    "electron_temperature_ev": 10000.0,
    "ambient_electron_current_density_a_m2": 1.0e-5,
}
COLD = {
    "electron_temperature_ev": 20.0,
    "ambient_electron_current_density_a_m2": 1.0e-6,
}


def blanket(**kw):
    row = {
        "id": "mli-1",
        "material": "kapton-thermal-blanket",
        "area_m2": 4.0,
        "surface_resistivity_ohm_sq": 1.0e15,
        "illumination": "eclipsed",
        "grounded": False,
    }
    row.update(kw)
    return row


def chassis(**kw):
    row = {
        "id": "bus-panel",
        "material": "bare-aluminium",
        "area_m2": 6.0,
        "surface_resistivity_ohm_sq": 1.0e-2,
        "illumination": "eclipsed",
        "grounded": True,
    }
    row.update(kw)
    return row


class NormalizeItemTests(unittest.TestCase):
    def test_happy_row_carries_material_parameters(self):
        row = logic.normalize_material_item(blanket())
        self.assertEqual(row["id"], "mli-1")
        self.assertAlmostEqual(row["delta_max"], 2.10)
        self.assertAlmostEqual(row["e_max_ev"], 150.0)

    def test_differential_limit_defaults(self):
        row = logic.normalize_material_item(blanket())
        self.assertAlmostEqual(
            row["differential_limit_v"], logic.DEFAULT_DIFFERENTIAL_LIMIT_V
        )

    def test_differential_limit_override_is_kept(self):
        row = logic.normalize_material_item(blanket(differential_limit_v=250.0))
        self.assertAlmostEqual(row["differential_limit_v"], 250.0)

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_material_item(["mli-1"])

    def test_blank_id_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_material_item(blanket(id="  "))

    def test_unknown_material_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_material_item(blanket(material="gold-foil"))

    def test_unknown_illumination_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_material_item(blanket(illumination="penumbra"))

    def test_non_boolean_grounding_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_material_item(blanket(grounded="yes"))

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_material_item(blanket(area_m2=0.0))

    def test_negative_resistivity_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_material_item(blanket(surface_resistivity_ohm_sq=-1.0))

    def test_non_finite_area_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_material_item(blanket(area_m2=float("inf")))

    def test_string_area_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_material_item(blanket(area_m2="4.0"))


class InventoryTests(unittest.TestCase):
    def test_inventory_length(self):
        inv = logic.build_external_material_inventory([blanket(), chassis()])
        self.assertEqual(len(inv), 2)

    def test_empty_inventory_rejected(self):
        with self.assertRaises(ValueError):
            logic.build_external_material_inventory([])

    def test_non_list_inventory_rejected(self):
        with self.assertRaises(ValueError):
            logic.build_external_material_inventory({"id": "mli-1"})

    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            logic.build_external_material_inventory([blanket(), blanket()])


class ConductionPathTests(unittest.TestCase):
    def test_bonded_low_resistivity_is_dissipating(self):
        row = logic.normalize_material_item(chassis())
        self.assertEqual(logic.categorize_conduction_path(row), "charge-dissipating")

    def test_bonded_at_the_resistivity_limit_is_dissipating(self):
        row = logic.normalize_material_item(
            chassis(surface_resistivity_ohm_sq=logic.DISSIPATIVE_RESISTIVITY_LIMIT_OHM_SQ)
        )
        self.assertEqual(logic.categorize_conduction_path(row), "charge-dissipating")

    def test_bonded_above_the_resistivity_limit_is_storing(self):
        row = logic.normalize_material_item(
            chassis(surface_resistivity_ohm_sq=1.0e12)
        )
        self.assertEqual(logic.categorize_conduction_path(row), "charge-storing")

    def test_unbonded_conductor_is_storing(self):
        row = logic.normalize_material_item(chassis(grounded=False))
        self.assertEqual(logic.categorize_conduction_path(row), "charge-storing")

    def test_raw_row_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_conduction_path({"id": "mli-1"})


class CoverageTests(unittest.TestCase):
    def test_exact_coverage_is_complete(self):
        inv = logic.build_external_material_inventory([blanket(), chassis()])
        cov = logic.inventory_area_coverage(inv, 10.0)
        self.assertTrue(cov["complete"])
        self.assertFalse(cov["overrun"])
        self.assertAlmostEqual(cov["covered_fraction"], 1.0)

    def test_shortfall_is_incomplete(self):
        inv = logic.build_external_material_inventory([blanket(), chassis()])
        cov = logic.inventory_area_coverage(inv, 20.0)
        self.assertFalse(cov["complete"])
        self.assertAlmostEqual(cov["covered_fraction"], 0.5)

    def test_overrun_is_flagged(self):
        inv = logic.build_external_material_inventory([blanket(), chassis()])
        cov = logic.inventory_area_coverage(inv, 8.0)
        self.assertTrue(cov["complete"])
        self.assertTrue(cov["overrun"])

    def test_representation_error_does_not_open_a_gap(self):
        inv = logic.build_external_material_inventory(
            [blanket(area_m2=0.1), chassis(area_m2=0.2)]
        )
        cov = logic.inventory_area_coverage(inv, 0.3)
        self.assertTrue(cov["complete"])
        self.assertFalse(cov["overrun"])

    def test_zero_declared_area_rejected(self):
        inv = logic.build_external_material_inventory([chassis()])
        with self.assertRaises(ValueError):
            logic.inventory_area_coverage(inv, 0.0)


class EmissionYieldTests(unittest.TestCase):
    def test_peak_energy_returns_peak_yield(self):
        params = logic.MATERIAL_KINDS["kapton-thermal-blanket"]
        value = logic.emission_yield(params, params["e_max_ev"])
        self.assertAlmostEqual(
            value, params["delta_max"] + params["backscatter"], places=2
        )

    def test_yield_falls_far_above_the_peak(self):
        params = logic.MATERIAL_KINDS["kapton-thermal-blanket"]
        hot = logic.emission_yield(params, 10000.0)
        peak = logic.emission_yield(params, params["e_max_ev"])
        self.assertLess(hot, peak)

    def test_yield_falls_far_below_the_peak(self):
        params = logic.MATERIAL_KINDS["kapton-thermal-blanket"]
        cold = logic.emission_yield(params, 5.0)
        peak = logic.emission_yield(params, params["e_max_ev"])
        self.assertLess(cold, peak)

    def test_hot_plasma_yield_is_below_unity(self):
        params = logic.MATERIAL_KINDS["kapton-thermal-blanket"]
        self.assertLess(logic.emission_yield(params, 10000.0), 1.0)

    def test_zero_energy_rejected(self):
        params = logic.MATERIAL_KINDS["bare-aluminium"]
        with self.assertRaises(ValueError):
            logic.emission_yield(params, 0.0)

    def test_negative_energy_rejected(self):
        params = logic.MATERIAL_KINDS["bare-aluminium"]
        with self.assertRaises(ValueError):
            logic.emission_yield(params, -10.0)


class EnvironmentTests(unittest.TestCase):
    def test_photoemission_scale_defaults_to_one(self):
        env = logic.normalize_environment(SUBSTORM)
        self.assertAlmostEqual(env["photoemission_scale"], 1.0)

    def test_non_mapping_environment_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_environment(10000.0)

    def test_missing_temperature_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_environment(
                {"ambient_electron_current_density_a_m2": 1.0e-5}
            )

    def test_zero_ambient_current_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_environment(
                {
                    "electron_temperature_ev": 10000.0,
                    "ambient_electron_current_density_a_m2": 0.0,
                }
            )

    def test_negative_photoemission_scale_rejected(self):
        env = dict(SUBSTORM)
        env["photoemission_scale"] = -0.1
        with self.assertRaises(ValueError):
            logic.normalize_environment(env)


class PotentialTests(unittest.TestCase):
    def test_eclipsed_dielectric_charges_negative_in_a_substorm(self):
        row = logic.normalize_material_item(blanket())
        self.assertLess(logic.equilibrium_surface_potential(row, SUBSTORM), -1000.0)

    def test_sunlit_surface_is_pinned_in_a_tenuous_plasma(self):
        row = logic.normalize_material_item(blanket(illumination="sunlit"))
        self.assertAlmostEqual(
            logic.equilibrium_surface_potential(row, COLD),
            logic.SUNLIT_PINNED_POTENTIAL_V,
        )

    def test_sunlit_surface_charges_when_the_ambient_flux_overwhelms_photoemission(self):
        row = logic.normalize_material_item(blanket(illumination="sunlit"))
        dense = dict(SUBSTORM)
        dense["ambient_electron_current_density_a_m2"] = 1.0e-3
        self.assertLess(logic.equilibrium_surface_potential(row, dense), -1000.0)

    def test_losing_photoemission_deepens_a_sunlit_surface(self):
        row = logic.normalize_material_item(blanket(illumination="sunlit"))
        dense = dict(SUBSTORM)
        dense["ambient_electron_current_density_a_m2"] = 1.0e-3
        eclipsed = dict(dense)
        eclipsed["photoemission_scale"] = 0.0
        self.assertLess(
            logic.equilibrium_surface_potential(row, eclipsed),
            logic.equilibrium_surface_potential(row, dense),
        )

    def test_emission_above_unity_pins_an_eclipsed_surface(self):
        row = logic.normalize_material_item(blanket())
        env = dict(SUBSTORM)
        env["electron_temperature_ev"] = 150.0
        self.assertAlmostEqual(logic.equilibrium_surface_potential(row, env), 0.0)

    def test_emission_above_unity_pins_a_sunlit_surface_positive(self):
        row = logic.normalize_material_item(blanket(illumination="sunlit"))
        env = dict(SUBSTORM)
        env["electron_temperature_ev"] = 150.0
        self.assertAlmostEqual(
            logic.equilibrium_surface_potential(row, env),
            logic.SUNLIT_PINNED_POTENTIAL_V,
        )

    def test_removing_sunlight_deepens_the_potential(self):
        lit = logic.normalize_material_item(blanket(illumination="sunlit"))
        dark = logic.normalize_material_item(blanket())
        self.assertLess(
            logic.equilibrium_surface_potential(dark, SUBSTORM),
            logic.equilibrium_surface_potential(lit, SUBSTORM),
        )


class BandTests(unittest.TestCase):
    def test_one_hundred_volts_is_benign(self):
        self.assertEqual(logic.categorize_potential_band(100.0), "benign")

    def test_one_thousand_volts_is_moderate(self):
        self.assertEqual(logic.categorize_potential_band(-1000.0), "moderate")

    def test_kilovolt_level_is_severe(self):
        self.assertEqual(logic.categorize_potential_band(-4000.0), "severe")

    def test_band_uses_magnitude_not_sign(self):
        self.assertEqual(logic.categorize_potential_band(250.0), "moderate")

    def test_non_numeric_potential_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_potential_band("-4000")


class FrameAndRowTests(unittest.TestCase):
    def test_frame_potential_is_area_weighted(self):
        inv = logic.build_external_material_inventory(
            [
                chassis(id="panel-a", area_m2=6.0),
                chassis(
                    id="panel-b",
                    area_m2=2.0,
                    material="indium-tin-oxide-coating",
                    surface_resistivity_ohm_sq=1.0e6,
                ),
            ]
        )
        a = logic.equilibrium_surface_potential(inv[0], SUBSTORM)
        b = logic.equilibrium_surface_potential(inv[1], SUBSTORM)
        self.assertAlmostEqual(
            logic.frame_potential(inv, SUBSTORM), (6.0 * a + 2.0 * b) / 8.0
        )

    def test_frame_potential_without_a_bonded_surface_rejected(self):
        inv = logic.build_external_material_inventory([blanket()])
        with self.assertRaises(ValueError):
            logic.frame_potential(inv, SUBSTORM)

    def test_bonded_rows_sit_at_the_frame_potential(self):
        inv = logic.build_external_material_inventory([blanket(), chassis()])
        rows = logic.surface_potential_rows(inv, SUBSTORM)
        bonded = [r for r in rows if r["conduction_path"] == "charge-dissipating"][0]
        self.assertAlmostEqual(bonded["differential_offset_v"], 0.0)
        self.assertAlmostEqual(
            bonded["surface_potential_v"], bonded["frame_potential_v"]
        )

    def test_floating_row_offset_is_isolated_minus_frame(self):
        inv = logic.build_external_material_inventory([blanket(), chassis()])
        rows = logic.surface_potential_rows(inv, SUBSTORM)
        floating = [r for r in rows if r["conduction_path"] == "charge-storing"][0]
        self.assertAlmostEqual(
            floating["differential_offset_v"],
            floating["isolated_potential_v"] - floating["frame_potential_v"],
        )


class AssessmentTests(unittest.TestCase):
    def test_offset_above_the_limit_is_a_finding(self):
        rows = [
            {
                "id": "mli-1",
                "surface_potential_v": -2000.0,
                "differential_offset_v": -900.0,
                "differential_limit_v": 500.0,
            }
        ]
        findings = logic.assess_surface_potentials(rows)
        self.assertEqual(findings[0]["kind"], "differential-offset-exceedance")

    def test_offset_exactly_at_the_limit_passes(self):
        rows = [
            {
                "id": "mli-1",
                "surface_potential_v": -2000.0,
                "differential_offset_v": -(0.1 + 0.2),
                "differential_limit_v": 0.3,
            }
        ]
        self.assertEqual(logic.assess_surface_potentials(rows), [])

    def test_absolute_limit_finding(self):
        rows = [
            {
                "id": "mli-1",
                "surface_potential_v": -6000.0,
                "differential_offset_v": 0.0,
                "differential_limit_v": 500.0,
            }
        ]
        findings = logic.assess_surface_potentials(rows, {"absolute_limit_v": 5000.0})
        self.assertEqual(findings[0]["kind"], "absolute-potential-exceedance")

    def test_absolute_limit_absent_by_default(self):
        rows = [
            {
                "id": "mli-1",
                "surface_potential_v": -6000.0,
                "differential_offset_v": 0.0,
                "differential_limit_v": 500.0,
            }
        ]
        self.assertEqual(logic.assess_surface_potentials(rows), [])

    def test_negative_absolute_limit_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_surface_potentials([], {"absolute_limit_v": -1.0})


class ReportTests(unittest.TestCase):
    def test_benign_vehicle_is_compliant(self):
        report = logic.analyze_surface_charging(
            [blanket(illumination="sunlit"), chassis(illumination="sunlit")],
            10.0,
            COLD,
        )
        self.assertTrue(report["compliant"])
        self.assertEqual(report["item_count"], 2)

    def test_substorm_vehicle_reports_an_offset_finding(self):
        report = logic.analyze_surface_charging(
            [blanket(), chassis()], 10.0, SUBSTORM
        )
        self.assertFalse(report["compliant"])
        self.assertIn(
            "differential-offset-exceedance", logic.summarize_findings(report)
        )

    def test_coverage_gap_is_reported_first(self):
        report = logic.analyze_surface_charging(
            [blanket(illumination="sunlit"), chassis(illumination="sunlit")],
            40.0,
            COLD,
        )
        self.assertEqual(report["findings"][0]["kind"], "inventory-coverage-gap")

    def test_area_overrun_is_reported(self):
        report = logic.analyze_surface_charging(
            [blanket(illumination="sunlit"), chassis(illumination="sunlit")],
            5.0,
            COLD,
        )
        kinds = logic.summarize_findings(report)
        self.assertEqual(kinds.get("inventory-area-overrun"), 1)

    def test_per_item_limit_override_changes_the_verdict(self):
        report = logic.analyze_surface_charging(
            [blanket(differential_limit_v=20000.0), chassis()], 10.0, SUBSTORM
        )
        self.assertTrue(report["compliant"])

    def test_frame_potential_is_shared_by_every_row(self):
        report = logic.analyze_surface_charging(
            [blanket(), chassis()], 10.0, SUBSTORM
        )
        for row in report["surfaces"]:
            self.assertAlmostEqual(
                row["frame_potential_v"], report["frame_potential_v"]
            )

    def test_summary_counts_every_finding(self):
        report = logic.analyze_surface_charging(
            [blanket(), chassis()], 40.0, SUBSTORM
        )
        counts = logic.summarize_findings(report)
        self.assertEqual(sum(counts.values()), len(report["findings"]))

    def test_summary_rejects_a_foreign_mapping(self):
        with self.assertRaises(ValueError):
            logic.summarize_findings({"surfaces": []})

    def test_report_is_deterministic(self):
        first = logic.analyze_surface_charging([blanket(), chassis()], 10.0, SUBSTORM)
        second = logic.analyze_surface_charging([blanket(), chassis()], 10.0, SUBSTORM)
        self.assertAlmostEqual(
            first["frame_potential_v"], second["frame_potential_v"]
        )
        self.assertEqual(len(first["findings"]), len(second["findings"]))

    def test_every_material_kind_can_be_analysed(self):
        for name in sorted(logic.MATERIAL_KINDS):
            inv = [blanket(id="sample", material=name), chassis()]
            report = logic.analyze_surface_charging(inv, 10.0, SUBSTORM)
            self.assertTrue(math.isfinite(report["frame_potential_v"]))


if __name__ == "__main__":
    unittest.main()
