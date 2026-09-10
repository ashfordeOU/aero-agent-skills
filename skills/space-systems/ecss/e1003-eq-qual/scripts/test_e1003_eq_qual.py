#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-03C clause 5.2 equipment
qualification test baseline.

Exercises scripts/e1003_eq_qual_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - family applicability
follows Table 5-1 (physical_properties/functional_performance/thermal
always applicable, the rest gated by equipment attributes); the
baseline sequence brackets environmental families with an initial and
final functional/performance check in fixed clause order; qualification
level/duration derivation (Table 5-2) applies the margin in the
requested mode and a strictly positive duration factor; a baseline is
only reported complete when every environmental/mission-specific family
has a requirement attached.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1003_eq_qual_logic as eq  # noqa: E402


BASE_EQUIPMENT = {
    "has_mechanical_loads": False,
    "is_pressurized": False,
    "has_electronics": False,
    "has_mission_specific_test": False,
}


class SelectApplicableFamiliesTest(unittest.TestCase):
    def test_baseline_families_always_present(self):
        applicable = eq.select_applicable_families(BASE_EQUIPMENT)
        self.assertEqual(
            applicable, ["physical_properties", "functional_performance", "thermal"]
        )

    def test_each_attribute_enables_its_family(self):
        equipment = dict(
            BASE_EQUIPMENT,
            has_mechanical_loads=True,
            is_pressurized=True,
            has_electronics=True,
            has_mission_specific_test=True,
        )
        applicable = eq.select_applicable_families(equipment)
        for family in ("mechanical", "pressure_integrity", "electrical", "mission_specific"):
            self.assertIn(family, applicable)

    def test_does_not_mutate_input(self):
        equipment = dict(BASE_EQUIPMENT)
        before = dict(equipment)
        eq.select_applicable_families(equipment)
        self.assertEqual(equipment, before)


class BuildBaselineSequenceTest(unittest.TestCase):
    def test_minimal_equipment_sequence(self):
        sequence = eq.build_baseline_sequence(BASE_EQUIPMENT)
        families = [step["family"] for step in sequence]
        self.assertEqual(
            families,
            [
                "physical_properties",
                "functional_performance",
                "thermal",
                "functional_performance",
            ],
        )
        self.assertEqual(sequence[1]["phase"], "initial")
        self.assertEqual(sequence[-1]["phase"], "final")

    def test_full_equipment_sequence_follows_clause_order(self):
        equipment = dict(
            BASE_EQUIPMENT,
            has_mechanical_loads=True,
            is_pressurized=True,
            has_electronics=True,
            has_mission_specific_test=True,
        )
        sequence = eq.build_baseline_sequence(equipment)
        families = [step["family"] for step in sequence]
        self.assertEqual(
            families,
            [
                "physical_properties",
                "functional_performance",
                "mechanical",
                "pressure_integrity",
                "thermal",
                "electrical",
                "functional_performance",
                "mission_specific",
            ],
        )

    def test_functional_performance_brackets_environmental_families(self):
        equipment = dict(BASE_EQUIPMENT, has_mechanical_loads=True)
        sequence = eq.build_baseline_sequence(equipment)
        initial_idx = next(
            i for i, s in enumerate(sequence) if s["family"] == "functional_performance" and s["phase"] == "initial"
        )
        final_idx = next(
            i for i, s in enumerate(sequence) if s["family"] == "functional_performance" and s["phase"] == "final"
        )
        mechanical_idx = next(i for i, s in enumerate(sequence) if s["family"] == "mechanical")
        self.assertLess(initial_idx, mechanical_idx)
        self.assertLess(mechanical_idx, final_idx)


class ComputeQualificationLevelTest(unittest.TestCase):
    def test_multiplicative_margin(self):
        self.assertAlmostEqual(eq.compute_qualification_level(10.0, 1.5), 15.0)

    def test_additive_margin(self):
        self.assertAlmostEqual(
            eq.compute_qualification_level(20.0, 10.0, mode="additive"), 30.0
        )

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            eq.compute_qualification_level(10.0, 1.5, mode="exponential")


class ComputeQualificationDurationTest(unittest.TestCase):
    def test_duration_scaled_by_factor(self):
        self.assertAlmostEqual(eq.compute_qualification_duration(4.0, 2.0), 8.0)

    def test_zero_duration_factor_raises(self):
        with self.assertRaises(ValueError):
            eq.compute_qualification_duration(4.0, 0.0)

    def test_negative_duration_factor_raises(self):
        with self.assertRaises(ValueError):
            eq.compute_qualification_duration(4.0, -1.0)


class BuildTestRequirementTest(unittest.TestCase):
    def test_requirement_fields(self):
        requirement = eq.build_test_requirement(
            "thermal",
            reference_level=60.0,
            reference_duration=24.0,
            margin=10.0,
            duration_factor=1.5,
            mode="additive",
        )
        self.assertEqual(requirement["family"], "thermal")
        self.assertAlmostEqual(requirement["qualification_level"], 70.0)
        self.assertAlmostEqual(requirement["qualification_duration"], 36.0)
        self.assertEqual(requirement["margin_mode"], "additive")


class BuildQualificationBaselineTest(unittest.TestCase):
    def test_attaches_requirement_to_configured_family(self):
        equipment = dict(BASE_EQUIPMENT, has_mechanical_loads=True)
        test_configs = {
            "mechanical": {
                "reference_level": 8.0,
                "reference_duration": 2.0,
                "margin": 1.25,
                "duration_factor": 2.0,
            },
        }
        baseline = eq.build_qualification_baseline(equipment, test_configs)
        mechanical_step = next(s for s in baseline if s["family"] == "mechanical")
        self.assertIsNotNone(mechanical_step["requirement"])
        self.assertAlmostEqual(mechanical_step["requirement"]["qualification_level"], 10.0)
        thermal_step = next(s for s in baseline if s["family"] == "thermal")
        self.assertIsNone(thermal_step["requirement"])

    def test_baseline_families_never_get_a_requirement(self):
        equipment = dict(BASE_EQUIPMENT)
        baseline = eq.build_qualification_baseline(equipment, {})
        for step in baseline:
            if step["family"] in ("physical_properties", "functional_performance"):
                self.assertIsNone(step["requirement"])

    def test_does_not_mutate_inputs(self):
        equipment = dict(BASE_EQUIPMENT, has_mechanical_loads=True)
        test_configs = {
            "mechanical": {
                "reference_level": 8.0,
                "reference_duration": 2.0,
                "margin": 1.25,
                "duration_factor": 2.0,
            },
        }
        equipment_before = dict(equipment)
        configs_before = {k: dict(v) for k, v in test_configs.items()}
        eq.build_qualification_baseline(equipment, test_configs)
        self.assertEqual(equipment, equipment_before)
        self.assertEqual(test_configs, configs_before)


class MissingRequirementsTest(unittest.TestCase):
    def test_lists_unconfigured_environmental_families_deduplicated(self):
        equipment = dict(BASE_EQUIPMENT, has_mechanical_loads=True)
        baseline = eq.build_qualification_baseline(equipment, {})
        self.assertEqual(eq.missing_requirements(baseline), ["mechanical", "thermal"])

    def test_empty_when_all_configured(self):
        equipment = dict(BASE_EQUIPMENT)
        test_configs = {
            "thermal": {
                "reference_level": 60.0,
                "reference_duration": 24.0,
                "margin": 10.0,
                "duration_factor": 1.0,
                "mode": "additive",
            },
        }
        baseline = eq.build_qualification_baseline(equipment, test_configs)
        self.assertEqual(eq.missing_requirements(baseline), [])


class BaselineCompleteTest(unittest.TestCase):
    def test_incomplete_when_a_family_has_no_requirement(self):
        equipment = dict(BASE_EQUIPMENT)
        baseline = eq.build_qualification_baseline(equipment, {})
        self.assertFalse(eq.baseline_complete(baseline))

    def test_complete_when_every_family_has_a_requirement(self):
        equipment = dict(BASE_EQUIPMENT)
        test_configs = {
            "thermal": {
                "reference_level": 60.0,
                "reference_duration": 24.0,
                "margin": 10.0,
                "duration_factor": 1.0,
                "mode": "additive",
            },
        }
        baseline = eq.build_qualification_baseline(equipment, test_configs)
        self.assertTrue(eq.baseline_complete(baseline))


if __name__ == "__main__":
    unittest.main(verbosity=2)
