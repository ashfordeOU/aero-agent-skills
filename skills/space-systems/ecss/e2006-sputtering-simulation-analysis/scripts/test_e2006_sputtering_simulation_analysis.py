#!/usr/bin/env python3
"""Gate 3 contract test for e2006-sputtering-simulation-analysis.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2006_sputtering_simulation_analysis.py
"""

from __future__ import annotations

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e2006_sputtering_simulation_analysis_logic as logic  # noqa: E402


def beam_population(**over):
    rec = {
        "population_id": "P-BEAM",
        "species": "xenon-single",
        "accel_voltage_v": 1200.0,
        "emission_angle_deg": 10.0,
        "flux_ions_m2_s": 1.0e15,
        "sample_count": 20000,
    }
    rec.update(over)
    return rec


def cex_population(**over):
    rec = {
        "population_id": "P-CEX",
        "species": "xenon-single",
        "accel_voltage_v": 30.0,
        "emission_angle_deg": 60.0,
        "flux_ions_m2_s": 4.0e15,
        "sample_count": 20000,
    }
    rec.update(over)
    return rec


def radiator_surface(**over):
    rec = {
        "surface_id": "S-RADIATOR",
        "material": "aluminium-6061",
        "normal_angle_deg": 40.0,
        "span_start_deg": 5.0,
        "span_end_deg": 80.0,
        "erosion_allowance_um": 50.0,
    }
    rec.update(over)
    return rec


class TestIonEnergy(unittest.TestCase):
    def test_single_charge_energy_equals_voltage(self):
        self.assertAlmostEqual(
            logic.ion_energy_ev("xenon-single", 1200.0), 1200.0, places=9
        )

    def test_double_charge_doubles_energy(self):
        self.assertAlmostEqual(
            logic.ion_energy_ev("xenon-double", 1200.0), 2400.0, places=9
        )

    def test_unknown_species_rejected(self):
        with self.assertRaises(ValueError):
            logic.ion_energy_ev("neon-single", 1200.0)

    def test_non_positive_voltage_rejected(self):
        with self.assertRaises(ValueError):
            logic.ion_energy_ev("xenon-single", 0.0)

    def test_non_numeric_voltage_rejected(self):
        with self.assertRaises(ValueError):
            logic.ion_energy_ev("xenon-single", "high")


class TestPopulationCategorization(unittest.TestCase):
    def test_core_beam_population(self):
        self.assertEqual(logic.categorize_ion_population(1200.0, 10.0), "primary-beam")

    def test_beam_wing_population(self):
        self.assertEqual(logic.categorize_ion_population(1200.0, 45.0), "beam-wing")

    def test_slow_ions_are_charge_exchange(self):
        self.assertEqual(logic.categorize_ion_population(20.0, 45.0), "charge-exchange")

    def test_charge_exchange_ceiling_is_inclusive(self):
        ceiling = logic.CHARGE_EXCHANGE_CEILING_EV
        self.assertEqual(logic.categorize_ion_population(ceiling, 5.0), "charge-exchange")

    def test_beam_core_half_angle_is_inclusive(self):
        half = logic.BEAM_CORE_HALF_ANGLE_DEG
        self.assertEqual(logic.categorize_ion_population(900.0, half), "primary-beam")

    def test_beyond_ninety_degrees_is_backflow(self):
        self.assertEqual(logic.categorize_ion_population(900.0, 120.0), "backflow")

    def test_every_kind_is_a_declared_kind(self):
        for energy, angle in ((1200.0, 0.0), (1200.0, 60.0), (5.0, 5.0), (5.0, 170.0)):
            self.assertIn(
                logic.categorize_ion_population(energy, angle), logic.POPULATION_KINDS
            )

    def test_negative_energy_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_ion_population(-1.0, 10.0)

    def test_angle_above_one_eighty_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_ion_population(1200.0, 190.0)


class TestGeometry(unittest.TestCase):
    def test_trajectory_inside_span_intercepts(self):
        self.assertTrue(logic.trajectory_intercepts_surface(30.0, 5.0, 80.0))

    def test_trajectory_outside_span_misses(self):
        self.assertFalse(logic.trajectory_intercepts_surface(95.0, 5.0, 80.0))

    def test_span_bounds_are_inclusive(self):
        self.assertTrue(logic.trajectory_intercepts_surface(5.0, 5.0, 80.0))
        self.assertTrue(logic.trajectory_intercepts_surface(80.0, 5.0, 80.0))

    def test_inverted_span_rejected(self):
        with self.assertRaises(ValueError):
            logic.trajectory_intercepts_surface(30.0, 80.0, 5.0)

    def test_degenerate_span_rejected(self):
        with self.assertRaises(ValueError):
            logic.trajectory_intercepts_surface(30.0, 40.0, 40.0)

    def test_impact_angle_is_offset_from_normal(self):
        self.assertAlmostEqual(logic.impact_angle_deg(60.0, 40.0), 20.0, places=9)

    def test_impact_angle_is_symmetric(self):
        self.assertAlmostEqual(
            logic.impact_angle_deg(20.0, 40.0), logic.impact_angle_deg(60.0, 40.0)
        )

    def test_impact_angle_rejects_bad_normal(self):
        with self.assertRaises(ValueError):
            logic.impact_angle_deg(60.0, -5.0)


class TestAngularEnhancement(unittest.TestCase):
    def test_normal_incidence_is_unity(self):
        self.assertAlmostEqual(logic.angular_enhancement(0.0), 1.0, places=9)

    def test_oblique_incidence_raises_yield(self):
        self.assertGreater(logic.angular_enhancement(45.0), 1.0)

    def test_grazing_incidence_collapses_to_zero(self):
        self.assertAlmostEqual(
            logic.angular_enhancement(logic.GRAZING_LIMIT_DEG), 0.0, places=12
        )

    def test_beyond_grazing_limit_is_zero(self):
        self.assertAlmostEqual(logic.angular_enhancement(89.0), 0.0, places=12)

    def test_negative_incidence_rejected(self):
        with self.assertRaises(ValueError):
            logic.angular_enhancement(-1.0)


class TestSputterYield(unittest.TestCase):
    def test_below_threshold_yield_is_zero(self):
        threshold = logic.TARGET_MATERIALS["aluminium-6061"]["threshold_ev"]
        self.assertAlmostEqual(
            logic.sputter_yield_atoms_per_ion(
                "xenon-single", "aluminium-6061", threshold - 1.0, 0.0
            ),
            0.0,
            places=12,
        )

    def test_exactly_at_threshold_yield_is_zero(self):
        threshold = logic.TARGET_MATERIALS["aluminium-6061"]["threshold_ev"]
        self.assertAlmostEqual(
            logic.sputter_yield_atoms_per_ion(
                "xenon-single", "aluminium-6061", threshold, 0.0
            ),
            0.0,
            places=12,
        )

    def test_above_threshold_yield_is_positive(self):
        self.assertGreater(
            logic.sputter_yield_atoms_per_ion(
                "xenon-single", "aluminium-6061", 1200.0, 0.0
            ),
            0.0,
        )

    def test_yield_rises_with_energy_near_threshold(self):
        low = logic.sputter_yield_atoms_per_ion(
            "xenon-single", "aluminium-6061", 200.0, 0.0
        )
        high = logic.sputter_yield_atoms_per_ion(
            "xenon-single", "aluminium-6061", 800.0, 0.0
        )
        self.assertGreater(high, low)

    def test_oblique_yield_exceeds_normal_yield(self):
        normal = logic.sputter_yield_atoms_per_ion(
            "xenon-single", "aluminium-6061", 1200.0, 0.0
        )
        oblique = logic.sputter_yield_atoms_per_ion(
            "xenon-single", "aluminium-6061", 1200.0, 50.0
        )
        self.assertGreater(oblique, normal)

    def test_high_threshold_material_erodes_less(self):
        soft = logic.sputter_yield_atoms_per_ion(
            "xenon-single", "silver-interconnect", 600.0, 0.0
        )
        hard = logic.sputter_yield_atoms_per_ion(
            "xenon-single", "molybdenum-grid", 600.0, 0.0
        )
        self.assertGreater(soft, hard)

    def test_unknown_material_rejected(self):
        with self.assertRaises(ValueError):
            logic.sputter_yield_atoms_per_ion(
                "xenon-single", "unobtainium", 1200.0, 0.0
            )

    def test_unknown_species_rejected(self):
        with self.assertRaises(ValueError):
            logic.sputter_yield_atoms_per_ion("neon-single", "aluminium-6061", 1200.0, 0.0)

    def test_negative_energy_rejected(self):
        with self.assertRaises(ValueError):
            logic.sputter_yield_atoms_per_ion(
                "xenon-single", "aluminium-6061", -10.0, 0.0
            )


class TestErosionDepth(unittest.TestCase):
    def test_depth_matches_hand_calculation(self):
        material = "aluminium-6061"
        props = logic.TARGET_MATERIALS[material]
        atom_volume = (props["mass_amu"] * logic.AMU_KG) / props["density_kg_m3"]
        expected = 0.5 * 1.0e15 * 3600.0 * atom_volume * 1.0e6
        self.assertAlmostEqual(
            logic.erosion_depth_um(material, 0.5, 1.0e15, 3600.0), expected, places=9
        )

    def test_zero_duration_gives_zero_depth(self):
        self.assertAlmostEqual(
            logic.erosion_depth_um("aluminium-6061", 0.5, 1.0e15, 0.0), 0.0, places=12
        )

    def test_zero_yield_gives_zero_depth(self):
        self.assertAlmostEqual(
            logic.erosion_depth_um("aluminium-6061", 0.0, 1.0e15, 3600.0), 0.0, places=12
        )

    def test_denser_material_erodes_more_slowly(self):
        light = logic.erosion_depth_um("aluminium-6061", 0.5, 1.0e15, 3600.0)
        heavy = logic.erosion_depth_um("molybdenum-grid", 0.5, 1.0e15, 3600.0)
        self.assertGreater(light, heavy)

    def test_negative_flux_rejected(self):
        with self.assertRaises(ValueError):
            logic.erosion_depth_um("aluminium-6061", 0.5, -1.0e15, 3600.0)

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            logic.erosion_depth_um("aluminium-6061", 0.5, 1.0e15, -1.0)

    def test_unknown_material_rejected(self):
        with self.assertRaises(ValueError):
            logic.erosion_depth_um("unobtainium", 0.5, 1.0e15, 3600.0)


class TestSimulationFidelity(unittest.TestCase):
    def test_adequate_sample_count_has_no_finding(self):
        self.assertIsNone(logic.check_simulation_fidelity(beam_population()))

    def test_thin_sample_count_raises_finding(self):
        finding = logic.check_simulation_fidelity(beam_population(sample_count=10))
        self.assertIsNotNone(finding)
        self.assertIn("below the floor", finding)

    def test_missing_sample_count_raises_finding(self):
        rec = beam_population()
        del rec["sample_count"]
        finding = logic.check_simulation_fidelity(rec)
        self.assertIsNotNone(finding)
        self.assertIn("no trajectory sample_count", finding)

    def test_sample_count_exactly_at_floor_passes(self):
        floor = logic.DEFAULT_SAMPLE_FLOOR
        self.assertIsNone(
            logic.check_simulation_fidelity(beam_population(sample_count=floor))
        )

    def test_non_positive_floor_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_simulation_fidelity(beam_population(), sample_floor=0)


class TestNormalizePopulation(unittest.TestCase):
    def test_normalized_population_carries_energy_and_kind(self):
        pop = logic.normalize_population(beam_population())
        self.assertAlmostEqual(pop["energy_ev"], 1200.0, places=9)
        self.assertEqual(pop["kind"], "primary-beam")

    def test_missing_identifier_rejected(self):
        rec = beam_population()
        del rec["population_id"]
        with self.assertRaises(ValueError):
            logic.normalize_population(rec)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_population(["P-BEAM"])

    def test_unknown_species_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_population(beam_population(species="neon-single"))

    def test_negative_flux_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_population(beam_population(flux_ions_m2_s=-1.0))


class TestSurfaceAssessment(unittest.TestCase):
    def test_intercepting_population_produces_depth(self):
        result = logic.assess_surface_erosion(
            radiator_surface(), [beam_population()], 3600.0
        )
        self.assertEqual(len(result["contributions"]), 1)
        self.assertGreater(result["total_depth_um"], 0.0)

    def test_non_intercepting_population_is_dropped(self):
        result = logic.assess_surface_erosion(
            radiator_surface(), [beam_population(emission_angle_deg=150.0)], 3600.0
        )
        self.assertEqual(result["contributions"], [])
        self.assertAlmostEqual(result["total_depth_um"], 0.0, places=12)

    def test_depth_is_the_sum_of_contributions(self):
        result = logic.assess_surface_erosion(
            radiator_surface(), [beam_population(), cex_population()], 3600.0
        )
        total = sum(c["depth_um"] for c in result["contributions"])
        self.assertAlmostEqual(result["total_depth_um"], total, places=12)

    def test_generous_allowance_is_compliant(self):
        result = logic.assess_surface_erosion(
            radiator_surface(erosion_allowance_um=1.0e6), [beam_population()], 3600.0
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_tight_allowance_flags_exceedance(self):
        result = logic.assess_surface_erosion(
            radiator_surface(erosion_allowance_um=1.0e-12),
            [beam_population()],
            3.0e7,
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("exceeds the allowance" in f for f in result["findings"]))

    def test_depth_exactly_on_the_allowance_is_compliant(self):
        base = logic.assess_surface_erosion(
            radiator_surface(), [beam_population()], 3600.0
        )
        exact = logic.assess_surface_erosion(
            radiator_surface(erosion_allowance_um=base["total_depth_um"]),
            [beam_population()],
            3600.0,
        )
        self.assertTrue(exact["compliant"])

    def test_representation_error_on_the_allowance_is_absorbed(self):
        base = logic.assess_surface_erosion(
            radiator_surface(), [beam_population(), cex_population()], 3600.0
        )
        depth = base["total_depth_um"]
        allowance = math.nextafter(depth, 0.0)
        self.assertLess(allowance, depth)
        edge = logic.assess_surface_erosion(
            radiator_surface(erosion_allowance_um=allowance),
            [beam_population(), cex_population()],
            3600.0,
        )
        self.assertTrue(edge["compliant"])

    def test_missing_allowance_with_traffic_is_a_finding(self):
        surface = radiator_surface()
        del surface["erosion_allowance_um"]
        result = logic.assess_surface_erosion(surface, [beam_population()], 3600.0)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("no erosion allowance" in f for f in result["findings"]))

    def test_missing_allowance_without_traffic_is_not_a_finding(self):
        surface = radiator_surface()
        del surface["erosion_allowance_um"]
        result = logic.assess_surface_erosion(
            surface, [beam_population(emission_angle_deg=150.0)], 3600.0
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_thin_sampling_blocks_compliance(self):
        result = logic.assess_surface_erosion(
            radiator_surface(erosion_allowance_um=1.0e6),
            [beam_population(sample_count=5)],
            3600.0,
        )
        self.assertFalse(result["compliant"])

    def test_unknown_surface_material_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_surface_erosion(
                radiator_surface(material="unobtainium"), [beam_population()], 3600.0
            )

    def test_missing_surface_identifier_rejected(self):
        surface = radiator_surface()
        del surface["surface_id"]
        with self.assertRaises(ValueError):
            logic.assess_surface_erosion(surface, [beam_population()], 3600.0)

    def test_non_mapping_surface_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_surface_erosion("S-RADIATOR", [beam_population()], 3600.0)

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_surface_erosion(radiator_surface(), [beam_population()], -1.0)


class TestCampaignAssessment(unittest.TestCase):
    def test_campaign_reports_the_worst_surface(self):
        near = radiator_surface(
            surface_id="S-NEAR", normal_angle_deg=10.0, erosion_allowance_um=1.0e6
        )
        far = radiator_surface(
            surface_id="S-FAR",
            material="molybdenum-grid",
            normal_angle_deg=10.0,
            erosion_allowance_um=1.0e6,
        )
        result = logic.assess_sputtering_campaign([near, far], [beam_population()], 3600.0)
        self.assertEqual(result["worst_surface_id"], "S-NEAR")
        self.assertTrue(result["compliant"])

    def test_campaign_aggregates_findings(self):
        tight = radiator_surface(surface_id="S-TIGHT", erosion_allowance_um=1.0e-12)
        loose = radiator_surface(surface_id="S-LOOSE", erosion_allowance_um=1.0e6)
        result = logic.assess_sputtering_campaign(
            [tight, loose], [beam_population()], 3.0e7
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("S-TIGHT" in f for f in result["findings"]))

    def test_empty_surface_list_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_sputtering_campaign([], [beam_population()], 3600.0)

    def test_empty_population_list_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_sputtering_campaign([radiator_surface()], [], 3600.0)


if __name__ == "__main__":
    unittest.main()
