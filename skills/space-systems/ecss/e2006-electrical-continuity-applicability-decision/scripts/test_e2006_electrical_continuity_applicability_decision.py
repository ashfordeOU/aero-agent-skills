#!/usr/bin/env python3
"""Gate 3 contract test for e2006-electrical-continuity-applicability-decision."""

import unittest

from e2006_electrical_continuity_applicability_decision_logic import (
    HIGH_VOLTAGE_ONSET_V,
    SEVERITY_BENIGN,
    SEVERITY_SEVERE,
    SMALL_ISOLATED_AREA_LIMIT_CM2,
    STORED_ENERGY_LIMIT_J,
    VERDICT_NOT_APPLICABLE,
    VERDICT_RELAXED,
    VERDICT_REQUIRED,
    VERDICT_REQUIRED_BACKING,
    VERDICT_ROUTED_BIASED,
    VERDICT_ROUTED_HIGH_VOLTAGE,
    VERDICT_WAIVED_SMALL_PART,
    assess_surface_inventory,
    decide_continuity_applicability,
    environment_severity,
    format_decision_report,
    is_high_voltage_item,
    isolated_part_waiver,
    normalize_surface,
    stored_discharge_energy,
)


def surface(**overrides):
    record = {
        "surface_id": "radiator-panel-1",
        "exposure": "external-plasma-exposed",
        "material_family": "bulk-metal-conductor",
        "orbit_regime": "geostationary-earth-orbit",
        "exposed_area_cm2": 2500.0,
        "capacitance_to_structure_f": 1.0e-9,
        "operating_potential_v": 0.0,
        "deliberately_biased": False,
        "bonded_to_structure": True,
    }
    record.update(overrides)
    return record


class NormalizeSurfaceTests(unittest.TestCase):
    def test_valid_record_is_normalized(self):
        out = normalize_surface(surface(surface_id="  panel-a  "))
        self.assertEqual(out["surface_id"], "panel-a")
        self.assertAlmostEqual(out["exposed_area_cm2"], 2500.0)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            normalize_surface(["not", "a", "mapping"])

    def test_missing_identifier_rejected(self):
        record = surface()
        del record["surface_id"]
        with self.assertRaises(ValueError):
            normalize_surface(record)

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalize_surface(surface(surface_id="   "))

    def test_unknown_exposure_rejected(self):
        with self.assertRaises(ValueError):
            normalize_surface(surface(exposure="buried-under-structure"))

    def test_unknown_material_family_rejected(self):
        with self.assertRaises(ValueError):
            normalize_surface(surface(material_family="unobtainium"))

    def test_unknown_orbit_regime_rejected(self):
        with self.assertRaises(ValueError):
            normalize_surface(surface(orbit_regime="lunar-descent"))

    def test_negative_area_rejected(self):
        with self.assertRaises(ValueError):
            normalize_surface(surface(exposed_area_cm2=-1.0))

    def test_negative_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            normalize_surface(surface(capacitance_to_structure_f=-1.0e-12))

    def test_non_finite_potential_rejected(self):
        with self.assertRaises(ValueError):
            normalize_surface(surface(operating_potential_v=float("nan")))

    def test_infinite_potential_rejected(self):
        with self.assertRaises(ValueError):
            normalize_surface(surface(operating_potential_v=float("inf")))

    def test_non_boolean_bias_flag_rejected(self):
        with self.assertRaises(ValueError):
            normalize_surface(surface(deliberately_biased="yes"))

    def test_non_boolean_bond_flag_rejected(self):
        with self.assertRaises(ValueError):
            normalize_surface(surface(bonded_to_structure=1))

    def test_non_numeric_area_rejected(self):
        with self.assertRaises(ValueError):
            normalize_surface(surface(exposed_area_cm2="large"))


class EnvironmentSeverityTests(unittest.TestCase):
    def test_geostationary_is_severe(self):
        self.assertEqual(
            environment_severity("geostationary-earth-orbit"), SEVERITY_SEVERE
        )

    def test_polar_low_earth_orbit_is_severe(self):
        self.assertEqual(
            environment_severity("sun-synchronous-low-earth-orbit"), SEVERITY_SEVERE
        )

    def test_equatorial_low_earth_orbit_is_benign(self):
        self.assertEqual(
            environment_severity("equatorial-low-earth-orbit"), SEVERITY_BENIGN
        )

    def test_unknown_regime_rejected(self):
        with self.assertRaises(ValueError):
            environment_severity("halo-orbit")


class StoredEnergyTests(unittest.TestCase):
    def test_energy_of_charged_part(self):
        self.assertAlmostEqual(
            stored_discharge_energy(1.0e-9, 1000.0), 5.0e-4, places=12
        )

    def test_zero_potential_stores_nothing(self):
        self.assertAlmostEqual(stored_discharge_energy(1.0e-9, 0.0), 0.0, places=15)

    def test_sign_of_potential_does_not_matter(self):
        self.assertAlmostEqual(
            stored_discharge_energy(2.0e-10, -500.0),
            stored_discharge_energy(2.0e-10, 500.0),
            places=15,
        )

    def test_negative_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            stored_discharge_energy(-1.0e-9, 100.0)


class HighVoltageOnsetTests(unittest.TestCase):
    def test_above_onset_is_high_voltage(self):
        self.assertTrue(is_high_voltage_item(120.0))

    def test_below_onset_is_not_high_voltage(self):
        self.assertFalse(is_high_voltage_item(28.0))

    def test_exact_onset_counts_as_high_voltage(self):
        self.assertTrue(is_high_voltage_item(HIGH_VOLTAGE_ONSET_V))

    def test_negative_potential_uses_magnitude(self):
        self.assertTrue(is_high_voltage_item(-100.0))

    def test_negative_onset_rejected(self):
        with self.assertRaises(ValueError):
            is_high_voltage_item(10.0, onset_v=-1.0)


class IsolatedPartWaiverTests(unittest.TestCase):
    def test_small_low_energy_part_is_waived(self):
        out = isolated_part_waiver(0.4, 1.0e-12, 100.0)
        self.assertTrue(out["granted"])
        self.assertEqual(out["reasons"], [])

    def test_large_area_blocks_waiver(self):
        out = isolated_part_waiver(50.0, 1.0e-12, 100.0)
        self.assertFalse(out["granted"])
        self.assertIn("exposed-area-above-small-part-limit", out["reasons"])

    def test_high_stored_energy_blocks_waiver(self):
        out = isolated_part_waiver(0.2, 1.0e-7, 5000.0)
        self.assertFalse(out["granted"])
        self.assertIn("stored-discharge-energy-above-limit", out["reasons"])

    def test_both_criteria_can_fail_together(self):
        out = isolated_part_waiver(80.0, 1.0e-6, 4000.0)
        self.assertEqual(len(out["reasons"]), 2)

    def test_area_exactly_at_limit_is_waived(self):
        out = isolated_part_waiver(SMALL_ISOLATED_AREA_LIMIT_CM2, 1.0e-13, 10.0)
        self.assertTrue(out["granted"])

    def test_energy_exactly_at_limit_is_waived(self):
        out = isolated_part_waiver(0.5, 2.0e-8, 100.0)
        self.assertAlmostEqual(out["stored_energy_j"], STORED_ENERGY_LIMIT_J, places=12)
        self.assertTrue(out["granted"])

    def test_floating_potential_dominates_when_larger(self):
        out = isolated_part_waiver(0.5, 1.0e-9, 10.0, floating_potential_v=-3000.0)
        self.assertAlmostEqual(out["worst_potential_v"], 3000.0)
        self.assertFalse(out["granted"])

    def test_non_finite_floating_potential_rejected(self):
        with self.assertRaises(ValueError):
            isolated_part_waiver(0.5, 1.0e-9, 10.0, floating_potential_v=float("inf"))

    def test_negative_area_limit_rejected(self):
        with self.assertRaises(ValueError):
            isolated_part_waiver(0.5, 1.0e-9, 10.0, area_limit_cm2=-1.0)


class DecisionDiagramTests(unittest.TestCase):
    def test_internal_item_is_out_of_scope(self):
        out = decide_continuity_applicability(surface(exposure="internal-enclosed"))
        self.assertEqual(out["verdict"], VERDICT_NOT_APPLICABLE)
        self.assertEqual(out["governing_clause"], "internal-electrostatic-discharge-rules")

    def test_biased_surface_is_routed_out(self):
        out = decide_continuity_applicability(surface(deliberately_biased=True))
        self.assertEqual(out["verdict"], VERDICT_ROUTED_BIASED)

    def test_high_voltage_surface_is_routed_out(self):
        out = decide_continuity_applicability(surface(operating_potential_v=270.0))
        self.assertEqual(out["verdict"], VERDICT_ROUTED_HIGH_VOLTAGE)

    def test_bias_node_precedes_high_voltage_node(self):
        out = decide_continuity_applicability(
            surface(deliberately_biased=True, operating_potential_v=270.0)
        )
        self.assertEqual(out["verdict"], VERDICT_ROUTED_BIASED)
        self.assertNotIn("high-voltage-surface:true", out["route"])

    def test_exposed_bonded_conductor_needs_continuity(self):
        out = decide_continuity_applicability(surface())
        self.assertEqual(out["verdict"], VERDICT_REQUIRED)
        self.assertEqual(out["findings"], [])

    def test_ungrounded_conductor_raises_a_finding(self):
        out = decide_continuity_applicability(surface(bonded_to_structure=False))
        self.assertIn("ungrounded-conductive-surface", out["findings"])

    def test_small_isolated_part_is_waived(self):
        out = decide_continuity_applicability(
            surface(
                surface_id="fastener-head-7",
                bonded_to_structure=False,
                exposed_area_cm2=0.3,
                capacitance_to_structure_f=1.0e-12,
            )
        )
        self.assertEqual(out["verdict"], VERDICT_WAIVED_SMALL_PART)
        self.assertEqual(out["findings"], [])

    def test_dielectric_outer_layer_routes_to_backing_rule(self):
        out = decide_continuity_applicability(
            surface(surface_id="mli-outer-film", material_family="dielectric-film")
        )
        self.assertEqual(out["verdict"], VERDICT_REQUIRED_BACKING)

    def test_dielectric_in_benign_environment_is_relaxed(self):
        out = decide_continuity_applicability(
            surface(
                material_family="bulk-dielectric",
                orbit_regime="equatorial-low-earth-orbit",
            )
        )
        self.assertEqual(out["verdict"], VERDICT_RELAXED)

    def test_conductor_in_benign_environment_is_relaxed(self):
        out = decide_continuity_applicability(
            surface(orbit_regime="low-inclination-low-earth-orbit")
        )
        self.assertEqual(out["verdict"], VERDICT_RELAXED)

    def test_partial_shielding_needs_justification(self):
        out = decide_continuity_applicability(
            surface(exposure="external-partially-shielded")
        )
        self.assertIn("partial-shielding-needs-justification", out["findings"])

    def test_dissipative_coating_is_treated_as_conductive(self):
        out = decide_continuity_applicability(
            surface(material_family="dissipative-coating")
        )
        self.assertEqual(out["verdict"], VERDICT_REQUIRED)

    def test_route_records_every_visited_node(self):
        out = decide_continuity_applicability(surface())
        self.assertEqual(out["route"][0], "exposure:external-plasma-exposed")
        self.assertIn("deliberately-biased:false", out["route"])
        self.assertIn("material-family:bulk-metal-conductor", out["route"])
        self.assertIn("environment:%s" % SEVERITY_SEVERE, out["route"])

    def test_anchor_clause_is_reported(self):
        out = decide_continuity_applicability(surface())
        self.assertEqual(out["anchor"], "ECSS-E-ST-20-06C 6.3.3.1")

    def test_invalid_record_propagates_value_error(self):
        with self.assertRaises(ValueError):
            decide_continuity_applicability(surface(exposure="unknown"))


class InventoryTests(unittest.TestCase):
    def test_counts_and_scope_are_aggregated(self):
        out = assess_surface_inventory(
            [
                surface(surface_id="a"),
                surface(surface_id="b", exposure="internal-enclosed"),
                surface(surface_id="c", material_family="dielectric-film"),
            ]
        )
        self.assertEqual(out["verdict_counts"][VERDICT_REQUIRED], 1)
        self.assertEqual(out["verdict_counts"][VERDICT_NOT_APPLICABLE], 1)
        self.assertEqual(out["in_scope_count"], 2)
        self.assertTrue(out["compliant"])

    def test_open_findings_make_the_inventory_non_compliant(self):
        out = assess_surface_inventory(
            [surface(surface_id="a", bonded_to_structure=False)]
        )
        self.assertFalse(out["compliant"])
        self.assertEqual(out["open_findings"][0][0], "a")

    def test_duplicate_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_surface_inventory([surface(surface_id="a"), surface(surface_id="a")])

    def test_empty_inventory_rejected(self):
        with self.assertRaises(ValueError):
            assess_surface_inventory([])

    def test_non_sequence_inventory_rejected(self):
        with self.assertRaises(ValueError):
            assess_surface_inventory({"surface_id": "a"})


class ReportTests(unittest.TestCase):
    def test_report_lists_each_surface(self):
        assessment = assess_surface_inventory(
            [surface(surface_id="a"), surface(surface_id="b", bonded_to_structure=False)]
        )
        text = format_decision_report(assessment)
        self.assertIn("a -> ", text)
        self.assertIn("finding: ungrounded-conductive-surface", text)
        self.assertIn("in-scope=2", text)

    def test_report_rejects_foreign_input(self):
        with self.assertRaises(ValueError):
            format_decision_report({"nothing": True})


if __name__ == "__main__":
    unittest.main()
