"""Contract tests for the clause 5.5.3/5.5.4/5.5.5.1 generic-performance logic."""

import math
import unittest

from e3102_qualification_methods_generic_performance_logic import (
    MARGIN_TOLERANCE,
    METHOD_STRENGTH,
    VERIFICATION_METHODS,
    allocate_method,
    assess_generic_performance,
    critical_flaw_depth,
    design_load,
    grade_method_allocation,
    hoop_stress,
    leak_before_burst,
    margin_of_safety,
    safe_life_demonstration,
    worst_case_load_case,
)


def requirement(**overrides):
    base = {"id": "TP-0100", "kind": "performance", "safety_critical": False}
    base.update(overrides)
    return base


LOAD_CASES = [
    {"name": "launch-quasi-static", "limit_load": 900.0},
    {"name": "random-vibration-equivalent", "limit_load": 1200.0},
    {"name": "handling", "limit_load": 300.0},
]


class MethodAllocationTests(unittest.TestCase):
    def test_performance_requirement_needs_test(self):
        self.assertEqual(allocate_method(requirement())["required_method"], "test")

    def test_leak_tightness_needs_test(self):
        out = allocate_method(requirement(kind="leak-tightness"))
        self.assertEqual(out["required_method"], "test")

    def test_safety_critical_overrides_a_dimensional_kind(self):
        out = allocate_method(requirement(kind="dimensional", safety_critical=True))
        self.assertEqual(out["required_method"], "test")

    def test_structural_with_correlated_model(self):
        out = allocate_method(
            requirement(kind="structural", correlated_test_evidence=True)
        )
        self.assertEqual(out["required_method"], "analysis-supported-by-test")

    def test_structural_without_correlation_needs_test(self):
        out = allocate_method(requirement(kind="structural"))
        self.assertEqual(out["required_method"], "test")

    def test_dimensional_needs_inspection(self):
        self.assertEqual(
            allocate_method(requirement(kind="dimensional"))["required_method"], "inspection"
        )

    def test_documentation_needs_review_of_design(self):
        self.assertEqual(
            allocate_method(requirement(kind="documentation"))["required_method"],
            "review-of-design",
        )

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            allocate_method(requirement(kind="vibes"))

    def test_missing_key_rejected(self):
        item = requirement()
        del item["safety_critical"]
        with self.assertRaises(ValueError):
            allocate_method(item)

    def test_non_boolean_criticality_rejected(self):
        with self.assertRaises(ValueError):
            allocate_method(requirement(safety_critical="yes"))

    def test_strength_ordering_is_monotone(self):
        ordered = sorted(VERIFICATION_METHODS, key=lambda m: METHOD_STRENGTH[m])
        self.assertEqual(ordered, list(VERIFICATION_METHODS))

    def test_weaker_proposal_is_a_finding(self):
        out = grade_method_allocation(requirement(proposed_method="analysis"))
        self.assertFalse(out["adequate"])
        self.assertIn("analysis", out["finding"])

    def test_matching_proposal_is_adequate(self):
        out = grade_method_allocation(requirement(proposed_method="test"))
        self.assertTrue(out["adequate"])
        self.assertIsNone(out["finding"])

    def test_stronger_proposal_is_adequate(self):
        out = grade_method_allocation(
            requirement(kind="dimensional", proposed_method="test")
        )
        self.assertTrue(out["adequate"])

    def test_unknown_proposed_method_rejected(self):
        with self.assertRaises(ValueError):
            grade_method_allocation(requirement(proposed_method="vibe-check"))


class MechanicalLoadTests(unittest.TestCase):
    def test_design_load_is_the_factored_limit_load(self):
        self.assertAlmostEqual(design_load(1000.0, 1.25), 1250.0, places=9)

    def test_design_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            design_load(1000.0, 0.9)

    def test_non_numeric_limit_load_rejected(self):
        with self.assertRaises(ValueError):
            design_load("1000", 1.25)

    def test_margin_of_safety_is_zero_at_the_allowable(self):
        self.assertAlmostEqual(margin_of_safety(1250.0, 1250.0), 0.0, places=9)

    def test_positive_margin_when_allowable_exceeds_the_load(self):
        self.assertAlmostEqual(margin_of_safety(1500.0, 1250.0), 0.2, places=9)

    def test_worst_case_is_the_highest_design_load(self):
        out = worst_case_load_case(LOAD_CASES, 1.25, 2000.0)
        self.assertEqual(out["name"], "random-vibration-equivalent")
        self.assertAlmostEqual(out["design_load"], 1500.0, places=9)

    def test_per_case_design_factor_can_govern(self):
        cases = [
            {"name": "launch-quasi-static", "limit_load": 900.0, "design_factor": 2.0},
            {"name": "random-vibration-equivalent", "limit_load": 1200.0},
        ]
        out = worst_case_load_case(cases, 1.25, 2000.0)
        self.assertEqual(out["name"], "launch-quasi-static")

    def test_exact_margin_zero_is_compliant(self):
        out = worst_case_load_case(
            [{"name": "launch-quasi-static", "limit_load": 1000.0}], 1.25, 1250.0
        )
        self.assertAlmostEqual(out["margin_of_safety"], 0.0, places=9)
        self.assertTrue(out["compliant"])

    def test_negative_margin_is_not_compliant(self):
        out = worst_case_load_case(LOAD_CASES, 1.25, 1000.0)
        self.assertFalse(out["compliant"])

    def test_empty_load_case_set_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_load_case([], 1.25, 2000.0)

    def test_malformed_load_case_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_load_case([{"name": "launch"}], 1.25, 2000.0)


class SafeLifeTests(unittest.TestCase):
    def test_demonstration_at_the_scatter_factored_life_passes(self):
        out = safe_life_demonstration(1000.0, 4.0, 4000.0)
        self.assertAlmostEqual(out["required_cycles"], 4000.0, places=9)
        self.assertAlmostEqual(out["coverage_ratio"], 1.0, places=9)
        self.assertTrue(out["compliant"])

    def test_one_cycle_short_fails(self):
        self.assertFalse(safe_life_demonstration(1000.0, 4.0, 3000.0)["compliant"])

    def test_generous_demonstration_passes(self):
        out = safe_life_demonstration(1000.0, 4.0, 8000.0)
        self.assertAlmostEqual(out["coverage_ratio"], 2.0, places=9)

    def test_scatter_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            safe_life_demonstration(1000.0, 0.5, 4000.0)

    def test_zero_service_life_rejected(self):
        with self.assertRaises(ValueError):
            safe_life_demonstration(0.0, 4.0, 4000.0)

    def test_negative_demonstrated_cycles_rejected(self):
        with self.assertRaises(ValueError):
            safe_life_demonstration(1000.0, 4.0, -10.0)


class LeakBeforeBurstTests(unittest.TestCase):
    def test_hoop_stress_is_the_thin_wall_value(self):
        self.assertAlmostEqual(hoop_stress(4.0e6, 0.006, 0.0005), 48.0e6, places=3)

    def test_thick_wall_rejected(self):
        with self.assertRaises(ValueError):
            hoop_stress(4.0e6, 0.001, 0.002)

    def test_critical_flaw_depth_matches_the_closed_form(self):
        depth = critical_flaw_depth(30.0e6, 100.0e6)
        self.assertAlmostEqual(depth, (0.3 * 0.3) / math.pi, places=12)

    def test_geometry_factor_reduces_the_depth(self):
        plain = critical_flaw_depth(30.0e6, 100.0e6, 1.0)
        shaped = critical_flaw_depth(30.0e6, 100.0e6, 2.0)
        self.assertAlmostEqual(shaped, plain / 4.0, places=12)

    def test_zero_stress_rejected(self):
        with self.assertRaises(ValueError):
            critical_flaw_depth(30.0e6, 0.0)

    def test_tough_thin_wall_leaks_before_it_bursts(self):
        out = leak_before_burst(30.0e6, 4.0e6, 0.006, 0.0005)
        self.assertTrue(out["satisfied"])
        self.assertGreater(out["depth_to_thickness_ratio"], 2.0)

    def test_brittle_boundary_bursts_first(self):
        out = leak_before_burst(1.0e6, 12.0e6, 0.020, 0.0008)
        self.assertFalse(out["satisfied"])

    def test_required_ratio_above_one_tightens_the_verdict(self):
        loose = leak_before_burst(6.0e6, 8.0e6, 0.010, 0.0010, required_ratio=1.0)
        tight = leak_before_burst(6.0e6, 8.0e6, 0.010, 0.0010, required_ratio=50.0)
        self.assertTrue(loose["satisfied"])
        self.assertFalse(tight["satisfied"])

    def test_ratio_exactly_at_the_requirement_is_satisfied(self):
        out = leak_before_burst(30.0e6, 4.0e6, 0.006, 0.0005)
        exact = leak_before_burst(
            30.0e6, 4.0e6, 0.006, 0.0005, required_ratio=out["depth_to_thickness_ratio"]
        )
        self.assertAlmostEqual(
            exact["depth_to_thickness_ratio"], exact["required_ratio"], places=9
        )
        self.assertTrue(exact["satisfied"])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "requirements": [
                requirement(id="TP-0100", proposed_method="test"),
                requirement(
                    id="TP-0200",
                    kind="structural",
                    correlated_test_evidence=True,
                    proposed_method="analysis-supported-by-test",
                ),
                requirement(id="TP-0300", kind="dimensional", proposed_method="inspection"),
            ],
            "load_cases": LOAD_CASES,
            "design_factor": 1.25,
            "allowable": 2000.0,
            "service_cycles": 1000.0,
            "scatter_factor": 4.0,
            "demonstrated_cycles": 4500.0,
            "pressure": 4.0e6,
            "inner_radius": 0.006,
            "wall_thickness": 0.0005,
            "fracture_toughness": 30.0e6,
        }
        spec.update(overrides)
        return spec

    def test_clean_case_is_compliant(self):
        out = assess_generic_performance(self._spec())
        self.assertTrue(out["compliant"])
        self.assertEqual(out["findings"], [])

    def test_weak_method_allocation_surfaces_as_a_finding(self):
        spec = self._spec()
        spec["requirements"][0]["proposed_method"] = "review-of-design"
        out = assess_generic_performance(spec)
        self.assertFalse(out["compliant"])
        self.assertTrue(any("TP-0100" in f for f in out["findings"]))

    def test_mechanical_shortfall_surfaces(self):
        out = assess_generic_performance(self._spec(allowable=1000.0))
        self.assertTrue(any("margin of safety" in f for f in out["findings"]))

    def test_fatigue_shortfall_surfaces(self):
        out = assess_generic_performance(self._spec(demonstrated_cycles=2000.0))
        self.assertTrue(any("safe-life" in f for f in out["findings"]))

    def test_leak_before_burst_shortfall_surfaces(self):
        out = assess_generic_performance(
            self._spec(fracture_toughness=1.0e6, inner_radius=0.020, wall_thickness=0.0008,
                       pressure=12.0e6)
        )
        self.assertTrue(any("leaks" in f for f in out["findings"]))

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["scatter_factor"]
        with self.assertRaises(ValueError):
            assess_generic_performance(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_generic_performance(["requirements"])

    def test_empty_requirement_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_generic_performance(self._spec(requirements=[]))

    def test_margin_tolerance_is_tight(self):
        self.assertLessEqual(MARGIN_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
