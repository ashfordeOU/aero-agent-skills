"""Contract tests for the ECSS-Q-ST-70-01C cleanliness verification-plan logic."""

import unittest

from q7001_cleanliness_verification_plan_logic import (
    DEFAULT_MARGIN_FACTOR,
    build_verification_plan,
    capable_methods,
    method_is_capable,
    method_matches_kind,
    plan_coverage_fraction,
    plan_requirement,
    rank_methods,
    validate_method,
    validate_requirement,
    verification_points,
)

MILESTONES = ["subassembly-clean", "integration", "pre-encapsulation", "launch-site"]

TAPE_LIFT = {
    "name": "tape-lift",
    "kinds": "particulate",
    "detection_floor": 0.02,
    "min_sample_area_m2": 0.001,
    "direct": True,
}
VACUUM = {
    "name": "vacuum-sampling",
    "kinds": "particulate",
    "detection_floor": 0.05,
    "min_sample_area_m2": 0.25,
    "direct": True,
}
FALLOUT_PLATE = {
    "name": "particle-fallout-plate",
    "kinds": "particulate",
    "detection_floor": 0.01,
    "min_sample_area_m2": 0.01,
    "direct": False,
}
RINSE_IR = {
    "name": "solvent-rinse-infrared",
    "kinds": ["molecular"],
    "detection_floor": 0.1,
    "min_sample_area_m2": 0.02,
    "direct": True,
}
BLACK_LIGHT = {
    "name": "black-light-inspection",
    "kinds": ["particulate", "molecular"],
    "detection_floor": 1.0,
    "min_sample_area_m2": 0.0001,
    "quantitative": False,
    "direct": True,
}

ALL_METHODS = [TAPE_LIFT, VACUUM, FALLOUT_PLATE, RINSE_IR, BLACK_LIGHT]


def particulate_requirement(**overrides):
    record = {
        "id": "CLN-010",
        "kind": "particulate",
        "limit": 0.10,
        "area_m2": 1.5,
        "milestones": MILESTONES,
    }
    record.update(overrides)
    return record


def molecular_requirement(**overrides):
    record = {
        "id": "CLN-020",
        "kind": "molecular",
        "limit": 1.0,
        "area_m2": 0.8,
        "milestones": MILESTONES,
    }
    record.update(overrides)
    return record


class ValidateRequirementTests(unittest.TestCase):
    def test_normalises_kind_and_defaults(self):
        record = validate_requirement(particulate_requirement(kind="Particulate"))
        self.assertEqual(record["kind"], "particulate")
        self.assertFalse(record["critical"])

    def test_final_milestone_defaults_to_the_last_one(self):
        record = validate_requirement(particulate_requirement())
        self.assertEqual(record["final_accessible_milestone"], "launch-site")

    def test_declared_final_milestone_is_kept(self):
        record = validate_requirement(
            particulate_requirement(final_accessible_milestone="integration")
        )
        self.assertEqual(record["final_accessible_milestone"], "integration")

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(particulate_requirement(kind="biological"))

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(particulate_requirement(limit=0.0))

    def test_negative_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(particulate_requirement(area_m2=-1.0))

    def test_boolean_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(particulate_requirement(limit=True))

    def test_empty_milestone_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(particulate_requirement(milestones=[]))

    def test_repeated_milestone_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(
                particulate_requirement(milestones=["integration", "integration"])
            )

    def test_final_milestone_outside_the_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(
                particulate_requirement(final_accessible_milestone="storage")
            )

    def test_missing_key_rejected(self):
        broken = particulate_requirement()
        del broken["limit"]
        with self.assertRaises(ValueError):
            validate_requirement(broken)

    def test_non_mapping_requirement_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(["CLN-010"])


class ValidateMethodTests(unittest.TestCase):
    def test_single_kind_string_is_accepted(self):
        record = validate_method(TAPE_LIFT)
        self.assertEqual(record["kinds"], ["particulate"])

    def test_qualitative_method_carries_an_infinite_floor(self):
        record = validate_method(BLACK_LIGHT)
        self.assertFalse(record["quantitative"])
        self.assertEqual(record["detection_floor"], float("inf"))

    def test_duplicate_kinds_are_collapsed(self):
        record = validate_method(
            dict(RINSE_IR, kinds=["molecular", "Molecular"])
        )
        self.assertEqual(record["kinds"], ["molecular"])

    def test_unknown_method_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_method(dict(TAPE_LIFT, kinds=["radiological"]))

    def test_non_positive_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_method(dict(TAPE_LIFT, detection_floor=0.0))

    def test_missing_min_area_rejected(self):
        broken = dict(TAPE_LIFT)
        del broken["min_sample_area_m2"]
        with self.assertRaises(ValueError):
            validate_method(broken)


class CapabilityTests(unittest.TestCase):
    def setUp(self):
        self.requirement = validate_requirement(particulate_requirement())

    def test_kind_match(self):
        self.assertTrue(method_matches_kind(validate_method(TAPE_LIFT), self.requirement))
        self.assertFalse(method_matches_kind(validate_method(RINSE_IR), self.requirement))

    def test_capable_method_accepted(self):
        self.assertTrue(method_is_capable(validate_method(TAPE_LIFT), self.requirement))

    def test_floor_above_the_margin_is_not_capable(self):
        coarse = validate_method(dict(TAPE_LIFT, detection_floor=0.09))
        self.assertFalse(method_is_capable(coarse, self.requirement))

    def test_floor_exactly_at_the_margin_is_capable(self):
        exact = validate_method(
            dict(TAPE_LIFT, detection_floor=self.requirement["limit"] / DEFAULT_MARGIN_FACTOR)
        )
        self.assertTrue(method_is_capable(exact, self.requirement))

    def test_sample_area_larger_than_the_surface_is_not_capable(self):
        small = validate_requirement(particulate_requirement(area_m2=0.05))
        self.assertFalse(method_is_capable(validate_method(VACUUM), small))

    def test_qualitative_method_is_never_capable(self):
        self.assertFalse(method_is_capable(validate_method(BLACK_LIGHT), self.requirement))

    def test_margin_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            method_is_capable(validate_method(TAPE_LIFT), self.requirement, 0.5)

    def test_capable_methods_filters_the_catalogue(self):
        names = [item["name"] for item in capable_methods(ALL_METHODS, self.requirement)]
        self.assertIn("tape-lift", names)
        self.assertNotIn("solvent-rinse-infrared", names)

    def test_empty_catalogue_rejected(self):
        with self.assertRaises(ValueError):
            capable_methods([], self.requirement)

    def test_ranking_puts_a_direct_method_before_an_indirect_one(self):
        ranked = rank_methods(ALL_METHODS, self.requirement)
        self.assertEqual(ranked[0]["name"], "tape-lift")
        self.assertEqual(ranked[-1]["name"], "particle-fallout-plate")


class VerificationPointTests(unittest.TestCase):
    def test_points_run_to_the_final_accessible_milestone(self):
        record = validate_requirement(
            particulate_requirement(final_accessible_milestone="pre-encapsulation")
        )
        self.assertEqual(
            verification_points(record),
            ["subassembly-clean", "integration", "pre-encapsulation"],
        )

    def test_points_cover_every_milestone_when_the_surface_stays_accessible(self):
        record = validate_requirement(particulate_requirement())
        self.assertEqual(len(verification_points(record)), len(MILESTONES))


class PlanRequirementTests(unittest.TestCase):
    def test_covered_requirement_reports_no_finding(self):
        entry = plan_requirement(particulate_requirement(), ALL_METHODS)
        self.assertTrue(entry["covered"])
        self.assertEqual(entry["findings"], [])
        self.assertEqual(entry["selected_method"], "tape-lift")

    def test_alternate_methods_are_listed(self):
        entry = plan_requirement(particulate_requirement(), ALL_METHODS)
        self.assertIn("particle-fallout-plate", entry["alternate_methods"])

    def test_missing_kind_is_reported(self):
        entry = plan_requirement(molecular_requirement(), [TAPE_LIFT, VACUUM])
        self.assertFalse(entry["covered"])
        self.assertIn("no method measuring molecular", entry["findings"][0])

    def test_qualitative_only_coverage_is_reported(self):
        entry = plan_requirement(molecular_requirement(), [BLACK_LIGHT])
        self.assertFalse(entry["covered"])
        self.assertIn("qualitative", entry["findings"][0])

    def test_sample_area_shortfall_is_reported(self):
        entry = plan_requirement(
            particulate_requirement(area_m2=0.05), [VACUUM]
        )
        self.assertFalse(entry["covered"])
        self.assertIn("minimum sample area", entry["findings"][0])

    def test_floor_shortfall_is_reported(self):
        entry = plan_requirement(particulate_requirement(limit=0.01), [TAPE_LIFT])
        self.assertFalse(entry["covered"])
        self.assertIn("margin factor", entry["findings"][0])

    def test_critical_surface_carried_only_indirectly_is_reported(self):
        entry = plan_requirement(
            particulate_requirement(critical=True), [FALLOUT_PLATE]
        )
        self.assertFalse(entry["covered"])
        self.assertIn("indirect witness", entry["findings"][0])

    def test_critical_surface_with_a_direct_method_is_covered(self):
        entry = plan_requirement(
            particulate_requirement(critical=True), [FALLOUT_PLATE, TAPE_LIFT]
        )
        self.assertTrue(entry["covered"])


class BuildPlanTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "requirements": [particulate_requirement(), molecular_requirement()],
            "methods": ALL_METHODS,
        }
        spec.update(overrides)
        return spec

    def test_full_coverage_plan_is_complete(self):
        plan = build_verification_plan(self._spec())
        self.assertTrue(plan["complete"])
        self.assertAlmostEqual(plan["coverage_fraction"], 1.0, places=9)
        self.assertEqual(plan["uncovered"], [])

    def test_partial_coverage_fraction(self):
        plan = build_verification_plan(self._spec(methods=[TAPE_LIFT, BLACK_LIGHT]))
        self.assertAlmostEqual(plan["coverage_fraction"], 0.5, places=9)
        self.assertEqual(plan["uncovered"], ["CLN-020"])

    def test_findings_are_aggregated_across_requirements(self):
        plan = build_verification_plan(self._spec(methods=[BLACK_LIGHT]))
        self.assertEqual(len(plan["findings"]), 2)
        self.assertFalse(plan["complete"])

    def test_tighter_margin_factor_can_remove_coverage(self):
        plan = build_verification_plan(self._spec(margin_factor=50.0))
        self.assertIn("CLN-010", plan["uncovered"])

    def test_duplicate_requirement_id_rejected(self):
        with self.assertRaises(ValueError):
            build_verification_plan(
                self._spec(requirements=[particulate_requirement(), particulate_requirement()])
            )

    def test_missing_methods_key_rejected(self):
        spec = self._spec()
        del spec["methods"]
        with self.assertRaises(ValueError):
            build_verification_plan(spec)

    def test_empty_requirement_set_rejected(self):
        with self.assertRaises(ValueError):
            build_verification_plan(self._spec(requirements=[]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            build_verification_plan(["requirements"])

    def test_coverage_fraction_rejects_an_empty_entry_list(self):
        with self.assertRaises(ValueError):
            plan_coverage_fraction([])

    def test_coverage_fraction_rejects_a_malformed_entry(self):
        with self.assertRaises(ValueError):
            plan_coverage_fraction([{"requirement_id": "CLN-010"}])


if __name__ == "__main__":
    unittest.main()
