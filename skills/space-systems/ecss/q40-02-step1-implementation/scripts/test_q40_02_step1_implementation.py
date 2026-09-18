"""Contract test for the q40-02-step1-implementation leaf (stdlib unittest)."""

import unittest

from q40_02_step1_implementation_logic import (
    DEPTH_ORDINAL,
    assess_step1_implementation,
    depth_finding,
    required_depth,
    required_disciplines,
    required_scope_elements,
    required_techniques,
    validate_plan,
    validate_project_type,
)


def project(**kw):
    record = {
        "name": "smallsat-demo",
        "segments": ["launch", "orbital"],
        "crewed": False,
        "recovered": False,
        "third_party_exposure": False,
    }
    record.update(kw)
    return record


def plan_for(proj, **kw):
    record = {
        "declared_depth": required_depth(proj),
        "scope_elements": required_scope_elements(proj),
        "techniques": required_techniques(proj),
        "team_disciplines": required_disciplines(proj),
    }
    record.update(kw)
    return record


class TestValidateProjectType(unittest.TestCase):
    def test_normalizes_a_minimal_project(self):
        norm = validate_project_type({"name": "gse-rig", "segments": ["ground"]})
        self.assertFalse(norm["crewed"])
        self.assertFalse(norm["recovered"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_project_type("smallsat")

    def test_missing_name_raises(self):
        with self.assertRaises(ValueError):
            validate_project_type({"segments": ["orbital"]})

    def test_empty_segments_raises(self):
        with self.assertRaises(ValueError):
            validate_project_type(project(segments=[]))

    def test_unknown_segment_raises(self):
        with self.assertRaises(ValueError):
            validate_project_type(project(segments=["suborbital-hop"]))

    def test_crewed_ground_only_raises(self):
        with self.assertRaises(ValueError):
            validate_project_type(project(segments=["ground"], crewed=True))

    def test_recovered_without_reentry_raises(self):
        with self.assertRaises(ValueError):
            validate_project_type(project(recovered=True))

    def test_non_boolean_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_project_type(project(third_party_exposure="maybe"))


class TestRequiredDepth(unittest.TestCase):
    def test_ground_only_project_is_baseline(self):
        self.assertEqual(
            required_depth(project(segments=["ground"])), "baseline"
        )

    def test_launch_segment_raises_depth_to_enhanced(self):
        self.assertEqual(required_depth(project()), "enhanced")

    def test_third_party_exposure_raises_depth_to_enhanced(self):
        self.assertEqual(
            required_depth(project(segments=["ground"], third_party_exposure=True)),
            "enhanced",
        )

    def test_crew_forces_the_deepest_level(self):
        self.assertEqual(
            required_depth(project(segments=["orbital"], crewed=True)),
            "crewed-safety-critical",
        )

    def test_depth_ordinals_are_ordered(self):
        self.assertLess(DEPTH_ORDINAL["baseline"], DEPTH_ORDINAL["enhanced"])
        self.assertLess(
            DEPTH_ORDINAL["enhanced"], DEPTH_ORDINAL["crewed-safety-critical"]
        )


class TestDerivedSets(unittest.TestCase):
    def test_baseline_scope_is_always_present(self):
        scope = required_scope_elements(project(segments=["ground"]))
        self.assertIn("flight-hardware-items", scope)
        self.assertIn("ground-support-equipment", scope)

    def test_launch_segment_adds_range_exposure_scope(self):
        self.assertIn("range-third-party-exposure", required_scope_elements(project()))

    def test_crew_adds_escape_provisions_scope(self):
        scope = required_scope_elements(project(segments=["orbital"], crewed=True))
        self.assertIn("crew-emergency-and-escape-provisions", scope)

    def test_recovery_adds_post_flight_safing_scope(self):
        scope = required_scope_elements(
            project(segments=["launch", "orbital", "re-entry"], recovered=True)
        )
        self.assertIn("post-flight-safing-operations", scope)

    def test_crew_adds_error_analysis_technique(self):
        techniques = required_techniques(project(segments=["orbital"], crewed=True))
        self.assertIn("crew-task-and-error-analysis", techniques)
        self.assertIn("failure-tolerance-demonstration", techniques)

    def test_third_party_adds_its_own_technique(self):
        self.assertIn(
            "third-party-risk-assessment",
            required_techniques(project(third_party_exposure=True)),
        )

    def test_crew_adds_human_factors_discipline(self):
        disciplines = required_disciplines(project(segments=["orbital"], crewed=True))
        self.assertIn("human-factors", disciplines)
        self.assertIn("life-support-engineering", disciplines)

    def test_reentry_adds_thermal_protection_discipline(self):
        disciplines = required_disciplines(
            project(segments=["launch", "orbital", "re-entry"])
        )
        self.assertIn("thermal-protection-engineering", disciplines)

    def test_derived_sets_are_sorted_and_unique(self):
        techniques = required_techniques(project(segments=["ground", "launch"]))
        self.assertEqual(techniques, sorted(set(techniques)))


class TestPlanValidation(unittest.TestCase):
    def test_unknown_depth_raises(self):
        with self.assertRaises(ValueError):
            validate_plan({"declared_depth": "thorough"})

    def test_non_mapping_plan_raises(self):
        with self.assertRaises(ValueError):
            validate_plan(["baseline"])

    def test_non_sequence_techniques_raises(self):
        with self.assertRaises(ValueError):
            validate_plan({"declared_depth": "baseline", "techniques": "all-of-them"})


class TestAssessment(unittest.TestCase):
    def test_matching_plan_is_complete(self):
        proj = project()
        result = assess_step1_implementation(proj, plan_for(proj))
        self.assertTrue(result["complete"])
        self.assertEqual(result["findings"], [])

    def test_shallow_depth_is_a_finding(self):
        proj = project(segments=["orbital"], crewed=True)
        plan = plan_for(proj, declared_depth="enhanced")
        self.assertEqual(
            depth_finding(proj, plan),
            "declared-depth-below-required-crewed-safety-critical",
        )

    def test_deeper_than_required_is_not_a_finding(self):
        proj = project(segments=["ground"])
        plan = plan_for(proj, declared_depth="crewed-safety-critical")
        self.assertIsNone(depth_finding(proj, plan))

    def test_missing_technique_is_a_finding(self):
        proj = project(segments=["orbital"], crewed=True)
        reduced = [
            t for t in required_techniques(proj) if t != "crew-task-and-error-analysis"
        ]
        result = assess_step1_implementation(proj, plan_for(proj, techniques=reduced))
        self.assertIn(
            "technique-not-planned:crew-task-and-error-analysis", result["findings"]
        )
        self.assertFalse(result["complete"])

    def test_missing_discipline_is_a_finding(self):
        proj = project()
        reduced = [d for d in required_disciplines(proj) if d != "system-engineering"]
        result = assess_step1_implementation(
            proj, plan_for(proj, team_disciplines=reduced)
        )
        self.assertIn("discipline-not-planned:system-engineering", result["findings"])

    def test_extra_declaration_is_listed_not_a_finding(self):
        proj = project()
        plan = plan_for(
            proj, techniques=required_techniques(proj) + ["bow-tie-diagramming"]
        )
        result = assess_step1_implementation(proj, plan)
        technique_gap = [g for g in result["gaps"] if g["label"] == "technique"][0]
        self.assertEqual(
            technique_gap["declared_outside_requirement"], ["bow-tie-diagramming"]
        )
        self.assertTrue(result["complete"])

    def test_empty_plan_reports_every_derived_item(self):
        proj = project(segments=["orbital"], crewed=True)
        plan = plan_for(
            proj,
            declared_depth="baseline",
            scope_elements=[],
            techniques=[],
            team_disciplines=[],
        )
        result = assess_step1_implementation(proj, plan)
        expected = (
            1
            + len(required_scope_elements(proj))
            + len(required_techniques(proj))
            + len(required_disciplines(proj))
        )
        self.assertEqual(len(result["findings"]), expected)

    def test_assessment_reports_both_depths(self):
        proj = project()
        result = assess_step1_implementation(proj, plan_for(proj))
        self.assertEqual(result["required_depth"], "enhanced")
        self.assertEqual(result["declared_depth"], "enhanced")


if __name__ == "__main__":
    unittest.main()
