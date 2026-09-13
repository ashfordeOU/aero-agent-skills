#!/usr/bin/env python3
"""Contract test for the solar array standard objectives leaf (offline)."""

import copy
import unittest

from e2008_solar_array_standard_objectives_logic import (
    DEFAULT_ORGANISATION_WEIGHTS,
    FLOW_DOWN_TIERS,
    INCOMPLETE_VERDICT,
    OBJECTIVE_AREAS,
    ORGANISED_VERDICT,
    VERIFICATION_METHODS,
    assess_standard_objectives,
    index_requirements,
    link_defects,
    link_integrity_ratio,
    objective_coverage,
    objective_coverage_ratio,
    organisation_index,
    terminal_requirements,
    tier_rank,
    trace_to_objective,
    uncovered_objective_areas,
    unflowed_objective_areas,
    unverified_terminals,
    validate_requirement,
    validate_weights,
    verification_assignment_ratio,
)

ORGANISED_TREE = [
    {"id": "P0", "objective_area": "performance-definition", "tier": "system"},
    {
        "id": "P1",
        "objective_area": "performance-definition",
        "tier": "assembly",
        "parent": "P0",
        "verification_method": "test",
    },
    {"id": "D0", "objective_area": "design-and-interface", "tier": "system"},
    {
        "id": "D1",
        "objective_area": "design-and-interface",
        "tier": "assembly",
        "parent": "D0",
    },
    {
        "id": "D2",
        "objective_area": "design-and-interface",
        "tier": "component",
        "parent": "D1",
        "verification_method": "inspection",
    },
    {"id": "V0", "objective_area": "verification-and-test", "tier": "system"},
    {
        "id": "V1",
        "objective_area": "verification-and-test",
        "tier": "assembly",
        "parent": "V0",
        "verification_method": "analysis",
    },
    {"id": "Q0", "objective_area": "product-assurance", "tier": "system"},
    {
        "id": "Q1",
        "objective_area": "product-assurance",
        "tier": "assembly",
        "parent": "Q0",
    },
    {
        "id": "Q2",
        "objective_area": "product-assurance",
        "tier": "component",
        "parent": "Q1",
    },
    {
        "id": "Q3",
        "objective_area": "product-assurance",
        "tier": "material",
        "parent": "Q2",
        "verification_method": "inspection",
    },
    {"id": "R0", "objective_area": "documentation-and-data", "tier": "system"},
    {
        "id": "R1",
        "objective_area": "documentation-and-data",
        "tier": "assembly",
        "parent": "R0",
        "verification_method": "review-of-design",
    },
]


def _tree(**changes):
    """Deep copy of the organised tree with one record replaced or added."""
    records = copy.deepcopy(ORGANISED_TREE)
    for identifier, replacement in changes.items():
        for position, record in enumerate(records):
            if record["id"] == identifier:
                if replacement is None:
                    records.pop(position)
                else:
                    records[position] = replacement
                break
        else:
            if replacement is not None:
                records.append(replacement)
    return records


class TierTests(unittest.TestCase):
    def test_tier_rank_orders_system_above_material(self):
        self.assertLess(tier_rank("system"), tier_rank("material"))

    def test_every_declared_tier_has_a_rank(self):
        ranks = [tier_rank(tier) for tier in FLOW_DOWN_TIERS]
        self.assertEqual(ranks, sorted(ranks))

    def test_unknown_tier_rejected(self):
        with self.assertRaises(ValueError):
            tier_rank("sub-assembly")


class RequirementValidationTests(unittest.TestCase):
    def test_a_well_formed_record_is_normalised(self):
        entry = validate_requirement(
            {
                "id": "  P1 ",
                "objective_area": "performance-definition",
                "tier": "assembly",
                "parent": "P0",
                "verification_method": "test",
            }
        )
        self.assertEqual(entry["id"], "P1")
        self.assertEqual(entry["parent"], "P0")

    def test_missing_verification_method_is_kept_as_none(self):
        entry = validate_requirement(
            {"id": "P0", "objective_area": "performance-definition", "tier": "system"}
        )
        self.assertIsNone(entry["verification_method"])
        self.assertIsNone(entry["parent"])

    def test_unknown_objective_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(
                {"id": "X1", "objective_area": "marketing", "tier": "system"}
            )

    def test_unknown_verification_method_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(
                {
                    "id": "X1",
                    "objective_area": "product-assurance",
                    "tier": "system",
                    "verification_method": "opinion",
                }
            )

    def test_empty_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(
                {"id": "   ", "objective_area": "product-assurance", "tier": "system"}
            )

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement("P0")

    def test_duplicate_identifier_rejected(self):
        records = _tree()
        records.append(copy.deepcopy(records[0]))
        with self.assertRaises(ValueError):
            index_requirements(records)

    def test_empty_requirement_set_rejected(self):
        with self.assertRaises(ValueError):
            index_requirements([])


class CoverageTests(unittest.TestCase):
    def test_organised_tree_covers_every_objective_area(self):
        index = index_requirements(ORGANISED_TREE)
        self.assertEqual(uncovered_objective_areas(index), ())
        self.assertAlmostEqual(objective_coverage_ratio(index), 1.0, places=9)

    def test_every_objective_area_appears_in_the_coverage_map(self):
        coverage = objective_coverage(index_requirements(ORGANISED_TREE))
        for area in OBJECTIVE_AREAS:
            self.assertIn(area, coverage)

    def test_deepest_tier_is_reported_per_area(self):
        coverage = objective_coverage(index_requirements(ORGANISED_TREE))
        self.assertEqual(coverage["product-assurance"]["deepest_tier"], "material")
        self.assertEqual(coverage["verification-and-test"]["deepest_tier"], "assembly")

    def test_dropping_a_top_level_aim_lowers_the_coverage_ratio(self):
        index = index_requirements(_tree(R0=None, R1=None))
        self.assertIn("documentation-and-data", uncovered_objective_areas(index))
        self.assertAlmostEqual(objective_coverage_ratio(index), 0.8, places=9)

    def test_an_aim_stated_but_never_flowed_down_is_named(self):
        index = index_requirements(_tree(R1=None))
        self.assertIn("documentation-and-data", unflowed_objective_areas(index))

    def test_a_flowed_aim_is_not_reported_as_unflowed(self):
        index = index_requirements(ORGANISED_TREE)
        self.assertEqual(unflowed_objective_areas(index), ())


class LinkDefectTests(unittest.TestCase):
    def test_organised_tree_has_no_link_defect(self):
        self.assertEqual(link_defects(index_requirements(ORGANISED_TREE)), [])

    def test_missing_parent_is_reported(self):
        index = index_requirements(
            _tree(
                D2={
                    "id": "D2",
                    "objective_area": "design-and-interface",
                    "tier": "component",
                    "parent": "D9",
                    "verification_method": "inspection",
                }
            )
        )
        defects = link_defects(index)
        self.assertTrue(any(d["defect"] == "parent-not-found" for d in defects))

    def test_a_lower_tier_requirement_without_a_parent_is_reported(self):
        index = index_requirements(
            _tree(
                V1={
                    "id": "V1",
                    "objective_area": "verification-and-test",
                    "tier": "assembly",
                    "verification_method": "analysis",
                }
            )
        )
        self.assertTrue(
            any(d["defect"] == "parent-not-found" for d in link_defects(index))
        )

    def test_a_skipped_tier_is_reported(self):
        index = index_requirements(
            _tree(
                Q3={
                    "id": "Q3",
                    "objective_area": "product-assurance",
                    "tier": "material",
                    "parent": "Q1",
                    "verification_method": "inspection",
                }
            )
        )
        self.assertTrue(any(d["defect"] == "tier-skipped" for d in link_defects(index)))

    def test_a_parent_at_or_below_the_child_tier_is_reported(self):
        index = index_requirements(
            _tree(
                D1={
                    "id": "D1",
                    "objective_area": "design-and-interface",
                    "tier": "assembly",
                    "parent": "P1",
                }
            )
        )
        self.assertTrue(
            any(d["defect"] == "parent-not-above" for d in link_defects(index))
        )

    def test_a_parent_serving_another_aim_is_reported(self):
        index = index_requirements(
            _tree(
                V1={
                    "id": "V1",
                    "objective_area": "verification-and-test",
                    "tier": "assembly",
                    "parent": "P0",
                    "verification_method": "analysis",
                }
            )
        )
        self.assertTrue(
            any(d["defect"] == "cross-area-parent" for d in link_defects(index))
        )

    def test_a_system_tier_requirement_with_a_parent_is_reported(self):
        index = index_requirements(
            _tree(
                V0={
                    "id": "V0",
                    "objective_area": "verification-and-test",
                    "tier": "system",
                    "parent": "P0",
                }
            )
        )
        self.assertTrue(
            any(d["defect"] == "top-tier-with-parent" for d in link_defects(index))
        )

    def test_a_closed_parent_chain_is_reported(self):
        records = [
            {"id": "P0", "objective_area": "performance-definition", "tier": "system"},
            {
                "id": "A1",
                "objective_area": "performance-definition",
                "tier": "assembly",
                "parent": "A2",
            },
            {
                "id": "A2",
                "objective_area": "performance-definition",
                "tier": "assembly",
                "parent": "A1",
                "verification_method": "test",
            },
        ]
        defects = link_defects(index_requirements(records))
        self.assertTrue(any(d["defect"] == "parent-chain-cycle" for d in defects))

    def test_link_integrity_falls_when_a_link_breaks(self):
        clean = link_integrity_ratio(index_requirements(ORGANISED_TREE))
        broken = link_integrity_ratio(
            index_requirements(
                _tree(
                    Q3={
                        "id": "Q3",
                        "objective_area": "product-assurance",
                        "tier": "material",
                        "parent": "Q1",
                        "verification_method": "inspection",
                    }
                )
            )
        )
        self.assertAlmostEqual(clean, 1.0, places=9)
        self.assertLess(broken, 0.99)

    def test_link_defects_reject_an_empty_index(self):
        with self.assertRaises(ValueError):
            link_defects({})


class TerminalAndVerificationTests(unittest.TestCase):
    def test_terminals_are_the_records_with_no_child(self):
        index = index_requirements(ORGANISED_TREE)
        self.assertEqual(
            terminal_requirements(index), ("D2", "P1", "Q3", "R1", "V1")
        )

    def test_organised_tree_leaves_no_terminal_unverified(self):
        index = index_requirements(ORGANISED_TREE)
        self.assertEqual(unverified_terminals(index), ())
        self.assertAlmostEqual(verification_assignment_ratio(index), 1.0, places=9)

    def test_a_terminal_without_a_method_is_named(self):
        index = index_requirements(
            _tree(
                R1={
                    "id": "R1",
                    "objective_area": "documentation-and-data",
                    "tier": "assembly",
                    "parent": "R0",
                }
            )
        )
        self.assertEqual(unverified_terminals(index), ("R1",))
        self.assertAlmostEqual(verification_assignment_ratio(index), 0.8, places=9)

    def test_every_declared_method_is_accepted_on_a_terminal(self):
        for method in VERIFICATION_METHODS:
            index = index_requirements(
                _tree(
                    R1={
                        "id": "R1",
                        "objective_area": "documentation-and-data",
                        "tier": "assembly",
                        "parent": "R0",
                        "verification_method": method,
                    }
                )
            )
            self.assertEqual(unverified_terminals(index), ())


class TraceTests(unittest.TestCase):
    def test_a_material_tier_requirement_traces_to_its_aim(self):
        trace = trace_to_objective(index_requirements(ORGANISED_TREE), "Q3")
        self.assertEqual(trace["chain"], ("Q3", "Q2", "Q1", "Q0"))
        self.assertEqual(trace["top_level"], "Q0")
        self.assertEqual(trace["objective_area"], "product-assurance")
        self.assertEqual(trace["depth"], 3)

    def test_a_top_level_requirement_traces_to_itself(self):
        trace = trace_to_objective(index_requirements(ORGANISED_TREE), "P0")
        self.assertEqual(trace["chain"], ("P0",))
        self.assertEqual(trace["depth"], 0)

    def test_tracing_an_unknown_requirement_rejected(self):
        with self.assertRaises(ValueError):
            trace_to_objective(index_requirements(ORGANISED_TREE), "Z9")

    def test_tracing_through_a_missing_parent_rejected(self):
        index = index_requirements(
            _tree(
                D2={
                    "id": "D2",
                    "objective_area": "design-and-interface",
                    "tier": "component",
                    "parent": "D9",
                    "verification_method": "inspection",
                }
            )
        )
        with self.assertRaises(ValueError):
            trace_to_objective(index, "D2")


class WeightTests(unittest.TestCase):
    def test_default_weights_validate(self):
        self.assertIs(
            validate_weights(DEFAULT_ORGANISATION_WEIGHTS), DEFAULT_ORGANISATION_WEIGHTS
        )

    def test_weights_that_do_not_sum_to_one_rejected(self):
        broken = dict(DEFAULT_ORGANISATION_WEIGHTS)
        broken["link_integrity"] = 0.5
        with self.assertRaises(ValueError):
            validate_weights(broken)

    def test_negative_weight_rejected(self):
        broken = dict(DEFAULT_ORGANISATION_WEIGHTS)
        broken["link_integrity"] = -0.3
        broken["objective_coverage"] = 1.0
        with self.assertRaises(ValueError):
            validate_weights(broken)

    def test_missing_weight_rejected(self):
        broken = dict(DEFAULT_ORGANISATION_WEIGHTS)
        del broken["verification_assignment"]
        with self.assertRaises(ValueError):
            validate_weights(broken)

    def test_organisation_index_of_an_organised_tree_is_one(self):
        index = index_requirements(ORGANISED_TREE)
        self.assertAlmostEqual(organisation_index(index), 1.0, places=9)


class AssessmentTests(unittest.TestCase):
    def test_organised_tree_passes(self):
        result = assess_standard_objectives({"requirements": ORGANISED_TREE})
        self.assertEqual(result["verdict"], ORGANISED_VERDICT)
        self.assertTrue(result["organised"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["organisation_index"], 1.0, places=9)
        self.assertEqual(result["requirement_count"], len(ORGANISED_TREE))

    def test_an_uncovered_aim_fails_the_assessment(self):
        result = assess_standard_objectives({"requirements": _tree(R0=None, R1=None)})
        self.assertEqual(result["verdict"], INCOMPLETE_VERDICT)
        self.assertFalse(result["organised"])
        self.assertIn("documentation-and-data", result["uncovered_objective_areas"])
        self.assertTrue(any("owns no system-tier" in f for f in result["findings"]))

    def test_an_unflowed_aim_fails_the_assessment(self):
        result = assess_standard_objectives({"requirements": _tree(R1=None)})
        self.assertEqual(result["verdict"], INCOMPLETE_VERDICT)
        self.assertAlmostEqual(result["objective_coverage_ratio"], 1.0, places=9)
        self.assertTrue(any("never flowed" in f for f in result["findings"]))

    def test_an_unverified_terminal_fails_the_assessment(self):
        result = assess_standard_objectives(
            {
                "requirements": _tree(
                    R1={
                        "id": "R1",
                        "objective_area": "documentation-and-data",
                        "tier": "assembly",
                        "parent": "R0",
                    }
                )
            }
        )
        self.assertEqual(result["verdict"], INCOMPLETE_VERDICT)
        self.assertEqual(result["unverified_terminals"], ("R1",))
        self.assertAlmostEqual(result["organisation_index"], 0.94, places=9)

    def test_a_broken_link_is_carried_into_the_findings(self):
        result = assess_standard_objectives(
            {
                "requirements": _tree(
                    Q3={
                        "id": "Q3",
                        "objective_area": "product-assurance",
                        "tier": "material",
                        "parent": "Q1",
                        "verification_method": "inspection",
                    }
                )
            }
        )
        self.assertEqual(result["verdict"], INCOMPLETE_VERDICT)
        self.assertTrue(any("tier-skipped" in f for f in result["findings"]))

    def test_assessment_rejects_a_non_mapping_case(self):
        with self.assertRaises(ValueError):
            assess_standard_objectives(["P0"])

    def test_assessment_rejects_a_case_with_no_requirements(self):
        with self.assertRaises(ValueError):
            assess_standard_objectives({"requirements": []})

    def test_weaker_trees_never_score_above_the_organised_tree(self):
        organised = assess_standard_objectives({"requirements": ORGANISED_TREE})
        weaker = assess_standard_objectives({"requirements": _tree(R0=None, R1=None)})
        self.assertLess(weaker["organisation_index"], organised["organisation_index"])


if __name__ == "__main__":
    unittest.main()
