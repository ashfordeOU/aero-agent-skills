#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 4.2.1.2.3 reliable
insulation design provisions.

Exercises scripts/e20_reliable_insulation_design_provisions_logic.py
(stdlib unittest, offline). Contract: an exposure hazard categorizes
into exactly one of the four families and an unrecognized hazard
raises; the provision set demanded by a hazard list is deduplicated
and the gap against the implemented provisions is reported per
provision; a line whose single-barrier breach is hazardous needs two
independent barriers and a bad barrier count raises; dielectric
withstand margin is (rated - applied) / applied against a derating
floor, with non-positive voltages and a negative floor raising; the
impact screening areal density is monotonic in diameter, density,
velocity and coefficient, non-positive inputs raise, and an uncaptured
or under-sized shield is a finding; an uncaptured or short routing
standoff is a finding; and the aggregated review is compliant only
when it carries no findings.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_reliable_insulation_design_provisions_logic as ri  # noqa: E402


class CategorizeExposureHazardTest(unittest.TestCase):
    def test_meteoroid_is_impact(self):
        self.assertEqual(ri.categorize_exposure_hazard("meteoroid"), "impact")

    def test_orbital_debris_is_impact(self):
        self.assertEqual(ri.categorize_exposure_hazard("orbital_debris"), "impact")

    def test_atomic_oxygen_is_material_degradation(self):
        self.assertEqual(
            ri.categorize_exposure_hazard("atomic_oxygen"), "material_degradation"
        )

    def test_plasma_charging_is_electrical_stress(self):
        self.assertEqual(
            ri.categorize_exposure_hazard("plasma_charging"), "electrical_stress"
        )

    def test_chafing_is_mechanical_wear(self):
        self.assertEqual(ri.categorize_exposure_hazard("chafing"), "mechanical_wear")

    def test_every_known_hazard_has_a_family_and_provisions(self):
        for hazard in ri.HAZARD_PROVISIONS:
            self.assertIn(
                ri.categorize_exposure_hazard(hazard), ri.HAZARD_FAMILIES
            )
            self.assertTrue(ri.HAZARD_PROVISIONS[hazard])

    def test_unrecognized_hazard_raises(self):
        with self.assertRaises(ValueError):
            ri.categorize_exposure_hazard("sandstorm")


class ProvisionDerivationTest(unittest.TestCase):
    def test_provisions_are_deduplicated_across_hazards(self):
        provisions = ri.required_provisions(["meteoroid", "orbital_debris"])
        self.assertEqual(provisions, ("impact_shield", "routing_behind_structure"))

    def test_provisions_union_across_families(self):
        provisions = ri.required_provisions(["atomic_oxygen", "chafing"])
        self.assertEqual(
            provisions,
            ("atomic_oxygen_resistant_jacket", "chafe_protection", "stress_relief"),
        )

    def test_no_hazards_demands_no_provisions(self):
        self.assertEqual(ri.required_provisions([]), ())

    def test_missing_provisions_reports_only_the_gap(self):
        gap = ri.missing_provisions(["meteoroid"], ["impact_shield"])
        self.assertEqual(gap, ("routing_behind_structure",))

    def test_fully_implemented_leaves_no_gap(self):
        gap = ri.missing_provisions(
            ["meteoroid"], ["impact_shield", "routing_behind_structure", "spare_clamp"]
        )
        self.assertEqual(gap, ())

    def test_required_provisions_rejects_unrecognized_hazard(self):
        with self.assertRaises(ValueError):
            ri.required_provisions(["meteoroid", "moonquake"])


class BarrierRedundancyTest(unittest.TestCase):
    def test_hazardous_single_failure_needs_two_barriers(self):
        self.assertEqual(ri.required_barrier_count(True), 2)

    def test_benign_single_failure_needs_one_barrier(self):
        self.assertEqual(ri.required_barrier_count(False), 1)

    def test_one_barrier_on_a_hazardous_line_is_flagged(self):
        found = ri.barrier_redundancy_violations("L1", 1, True)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["issue"], "insufficient_independent_insulation_barriers")
        self.assertEqual(found[0]["required_barrier_count"], 2)

    def test_two_barriers_on_a_hazardous_line_is_compliant(self):
        self.assertEqual(ri.barrier_redundancy_violations("L1", 2, True), [])

    def test_one_barrier_on_a_benign_line_is_compliant(self):
        self.assertEqual(ri.barrier_redundancy_violations("L2", 1, False), [])

    def test_non_integer_barrier_count_raises(self):
        with self.assertRaises(ValueError):
            ri.barrier_redundancy_violations("L1", 1.5, False)

    def test_boolean_barrier_count_raises(self):
        with self.assertRaises(ValueError):
            ri.barrier_redundancy_violations("L1", True, False)

    def test_zero_barrier_count_raises(self):
        with self.assertRaises(ValueError):
            ri.barrier_redundancy_violations("L1", 0, False)


class DielectricMarginTest(unittest.TestCase):
    def test_margin_is_fraction_of_applied_voltage(self):
        self.assertAlmostEqual(ri.dielectric_margin(100.0, 28.0), 72.0 / 28.0)

    def test_double_rated_gives_unit_margin(self):
        self.assertAlmostEqual(ri.dielectric_margin(56.0, 28.0), 1.0)

    def test_rated_equal_to_applied_gives_zero_margin(self):
        self.assertAlmostEqual(ri.dielectric_margin(28.0, 28.0), 0.0)

    def test_margin_at_the_floor_is_compliant(self):
        self.assertEqual(ri.dielectric_margin_violations("L1", 56.0, 28.0, 1.0), [])

    def test_margin_below_the_floor_is_flagged(self):
        found = ri.dielectric_margin_violations("L1", 40.0, 28.0, 1.0)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["issue"], "dielectric_withstand_margin_below_floor")

    def test_non_positive_rated_voltage_raises(self):
        with self.assertRaises(ValueError):
            ri.dielectric_margin(0.0, 28.0)

    def test_non_positive_applied_voltage_raises(self):
        with self.assertRaises(ValueError):
            ri.dielectric_margin(100.0, 0.0)

    def test_negative_margin_floor_raises(self):
        with self.assertRaises(ValueError):
            ri.dielectric_margin_violations("L1", 100.0, 28.0, -0.1)


class ImpactScreeningTest(unittest.TestCase):
    def test_unit_design_particle_returns_the_coefficient(self):
        # 10 mm = 1 cm, unit density, unit velocity: every term is 1.0.
        self.assertAlmostEqual(
            ri.required_shield_areal_density(10.0, 1.0, 1.0, 1.0), 1.0
        )

    def test_velocity_term_is_two_thirds_power(self):
        # 8 ** (2/3) == 4 exactly, independent of the other terms.
        self.assertAlmostEqual(
            ri.required_shield_areal_density(10.0, 1.0, 8.0, 1.0), 4.0
        )

    def test_coefficient_scales_the_requirement_linearly(self):
        one = ri.required_shield_areal_density(3.0, 2.5, 12.0, 1.0)
        two = ri.required_shield_areal_density(3.0, 2.5, 12.0, 2.0)
        self.assertAlmostEqual(two, 2.0 * one)

    def test_requirement_grows_with_particle_diameter(self):
        small = ri.required_shield_areal_density(1.0, 2.5, 12.0)
        large = ri.required_shield_areal_density(4.0, 2.5, 12.0)
        self.assertGreater(large, small)

    def test_requirement_grows_with_particle_density(self):
        light = ri.required_shield_areal_density(3.0, 1.0, 12.0)
        heavy = ri.required_shield_areal_density(3.0, 4.0, 12.0)
        self.assertGreater(heavy, light)

    def test_non_positive_diameter_raises(self):
        with self.assertRaises(ValueError):
            ri.required_shield_areal_density(0.0, 2.5, 12.0)

    def test_non_positive_density_raises(self):
        with self.assertRaises(ValueError):
            ri.required_shield_areal_density(3.0, -1.0, 12.0)

    def test_non_positive_velocity_raises(self):
        with self.assertRaises(ValueError):
            ri.required_shield_areal_density(3.0, 2.5, 0.0)

    def test_non_positive_coefficient_raises(self):
        with self.assertRaises(ValueError):
            ri.required_shield_areal_density(3.0, 2.5, 12.0, 0.0)


class ImpactProtectionViolationTest(unittest.TestCase):
    def test_adequate_shield_is_compliant(self):
        self.assertEqual(ri.impact_protection_violations("L1", 2.0, 1.5), [])

    def test_shield_exactly_at_requirement_is_compliant(self):
        self.assertEqual(ri.impact_protection_violations("L1", 1.5, 1.5), [])

    def test_under_sized_shield_is_flagged(self):
        found = ri.impact_protection_violations("L1", 0.5, 1.5)
        self.assertEqual(found[0]["issue"], "impact_shield_under_sized")

    def test_uncaptured_shield_is_flagged_not_passed(self):
        found = ri.impact_protection_violations("L1", None, 1.5)
        self.assertEqual(found[0]["issue"], "shield_areal_density_not_captured")

    def test_non_positive_requirement_raises(self):
        with self.assertRaises(ValueError):
            ri.impact_protection_violations("L1", 2.0, 0.0)

    def test_negative_provided_density_raises(self):
        with self.assertRaises(ValueError):
            ri.impact_protection_violations("L1", -0.1, 1.5)


class RoutingStandoffTest(unittest.TestCase):
    def test_standoff_above_minimum_is_compliant(self):
        self.assertEqual(ri.routing_standoff_violations("L1", 50.0, 25.0), [])

    def test_standoff_exactly_at_minimum_is_compliant(self):
        self.assertEqual(ri.routing_standoff_violations("L1", 25.0, 25.0), [])

    def test_standoff_below_minimum_is_flagged(self):
        found = ri.routing_standoff_violations("L1", 10.0, 25.0)
        self.assertEqual(found[0]["issue"], "routing_standoff_below_minimum")

    def test_uncaptured_standoff_is_flagged_not_passed(self):
        found = ri.routing_standoff_violations("L1", None, 25.0)
        self.assertEqual(found[0]["issue"], "routing_standoff_not_captured")

    def test_negative_minimum_standoff_raises(self):
        with self.assertRaises(ValueError):
            ri.routing_standoff_violations("L1", 50.0, -1.0)

    def test_negative_standoff_raises(self):
        with self.assertRaises(ValueError):
            ri.routing_standoff_violations("L1", -5.0, 25.0)


class InsulationProvisionReviewTest(unittest.TestCase):
    def _compliant_line(self):
        return {
            "line_id": "internal-28v-feed",
            "hazards": ["atomic_oxygen", "chafing"],
            "implemented_provisions": [
                "atomic_oxygen_resistant_jacket",
                "chafe_protection",
                "stress_relief",
            ],
            "barrier_count": 1,
            "single_barrier_failure_hazardous": False,
            "rated_voltage_v": 100.0,
            "applied_voltage_v": 28.0,
        }

    def test_fully_provisioned_line_is_compliant(self):
        review = ri.insulation_provision_review(self._compliant_line())
        self.assertEqual(review["findings"], [])
        self.assertTrue(ri.is_provision_compliant(review))

    def test_review_reports_the_hazard_families_present(self):
        review = ri.insulation_provision_review(self._compliant_line())
        self.assertEqual(
            review["hazard_families"], ["material_degradation", "mechanical_wear"]
        )

    def test_review_does_not_mutate_the_input_line(self):
        line = self._compliant_line()
        before = dict(line)
        ri.insulation_provision_review(line)
        self.assertEqual(line, before)

    def test_exposed_boom_line_collects_every_finding(self):
        line = {
            "line_id": "boom-hv-run",
            "hazards": ["meteoroid"],
            "implemented_provisions": ["impact_shield"],
            "barrier_count": 1,
            "single_barrier_failure_hazardous": True,
            "rated_voltage_v": 100.0,
            "applied_voltage_v": 28.0,
            "design_particle": {
                "diameter_mm": 1.0,
                "density_g_cm3": 2.5,
                "velocity_km_s": 12.0,
            },
            "shield_areal_density_g_cm2": None,
        }
        review = ri.insulation_provision_review(line)
        issues = sorted(f["issue"] for f in review["findings"])
        self.assertEqual(
            issues,
            [
                "insufficient_independent_insulation_barriers",
                "provision_not_implemented",
                "shield_areal_density_not_captured",
            ],
        )
        self.assertFalse(ri.is_provision_compliant(review))

    def test_standoff_is_only_checked_when_a_minimum_is_set(self):
        line = self._compliant_line()
        line["routing_standoff_mm"] = None
        review = ri.insulation_provision_review(line)
        self.assertEqual(review["findings"], [])

    def test_set_minimum_standoff_is_enforced(self):
        line = self._compliant_line()
        line["min_routing_standoff_mm"] = 25.0
        line["routing_standoff_mm"] = 10.0
        review = ri.insulation_provision_review(line)
        self.assertEqual(
            [f["issue"] for f in review["findings"]], ["routing_standoff_below_minimum"]
        )

    def test_impact_hazard_without_design_particle_raises(self):
        line = self._compliant_line()
        line["hazards"] = ["meteoroid"]
        line["implemented_provisions"] = ["impact_shield", "routing_behind_structure"]
        with self.assertRaises(ValueError):
            ri.insulation_provision_review(line)

    def test_unrecognized_hazard_in_review_raises(self):
        line = self._compliant_line()
        line["hazards"] = ["atomic_oxygen", "gremlins"]
        with self.assertRaises(ValueError):
            ri.insulation_provision_review(line)


if __name__ == "__main__":
    unittest.main()
