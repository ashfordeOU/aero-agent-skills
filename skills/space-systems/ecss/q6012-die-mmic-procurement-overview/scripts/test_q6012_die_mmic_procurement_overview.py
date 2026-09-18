"""Contract tests for the clause 4.1 die-form MMIC procurement scope map."""

import unittest

from q6012_die_mmic_procurement_overview_logic import (
    BUILD_MODELS,
    CLAUSE_KEYS,
    DIE_FORMS,
    FOUNDRY_STANDINGS,
    QUALITY_TOKENS,
    applicable_clauses,
    assess_procurement_scope,
    clause_dependencies,
    clause_titles,
    close_under_dependencies,
    coverage_ratio,
    dependency_order,
    route_map,
    scope_findings,
    topological_order,
    validate_case,
)


def base_spec(**overrides):
    spec = {
        "form": "die",
        "foundry_standing": "qualified",
        "model": "fm",
        "quality_level": "level-2",
        "programme_floor": "level-2",
        "lot_acceptance_data": True,
        "assembled_in_house": True,
        "radiation_environment": True,
        "die_count": 40,
    }
    spec.update(overrides)
    return spec


class RegistryTests(unittest.TestCase):
    def test_registry_keys_are_unique(self):
        self.assertEqual(len(CLAUSE_KEYS), len(set(CLAUSE_KEYS)))

    def test_every_key_has_a_title(self):
        self.assertEqual(set(clause_titles()), set(CLAUSE_KEYS))

    def test_dependencies_reference_known_keys_only(self):
        graph = clause_dependencies()
        for key, deps in graph.items():
            for dep in deps:
                self.assertIn(dep, graph, "%s depends on unknown %s" % (key, dep))

    def test_registry_graph_is_acyclic(self):
        graph = clause_dependencies()
        ordered = topological_order(list(graph), graph)
        self.assertEqual(len(ordered), len(graph))

    def test_scope_clause_has_no_prerequisites(self):
        self.assertEqual(clause_dependencies()["scope-and-applicability"], ())


class ValidateCaseTests(unittest.TestCase):
    def test_normalises_tokens_to_lower_case(self):
        case = validate_case(base_spec(model="FM", form="Die"))
        self.assertEqual(case["model"], "fm")
        self.assertEqual(case["form"], "die")

    def test_optional_flags_default_to_false(self):
        spec = {
            "form": "die",
            "foundry_standing": "evaluated",
            "model": "em",
            "quality_level": "level-3",
            "programme_floor": "level-3",
        }
        case = validate_case(spec)
        self.assertFalse(case["lot_acceptance_data"])
        self.assertFalse(case["assembled_in_house"])
        self.assertEqual(case["die_count"], 1)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(["form"])

    def test_missing_required_key_rejected(self):
        spec = base_spec()
        del spec["programme_floor"]
        with self.assertRaises(ValueError):
            validate_case(spec)

    def test_unknown_key_rejected_rather_than_ignored(self):
        with self.assertRaises(ValueError):
            validate_case(base_spec(radiaton_environment=True))

    def test_unknown_token_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(base_spec(model="ftm"))

    def test_non_string_token_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(base_spec(form=1))

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(base_spec(assembled_in_house="yes"))

    def test_zero_die_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(base_spec(die_count=0))

    def test_boolean_die_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(base_spec(die_count=True))

    def test_token_tables_are_the_documented_ones(self):
        self.assertIn("packaged", DIE_FORMS)
        self.assertIn("unassessed", FOUNDRY_STANDINGS)
        self.assertEqual(BUILD_MODELS, ("em", "eqm", "fm"))
        self.assertEqual(QUALITY_TOKENS[0], "commercial")


class ApplicabilityTests(unittest.TestCase):
    def test_flight_build_routes_lot_procurement(self):
        keys = [r["key"] for r in applicable_clauses(validate_case(base_spec()))]
        self.assertIn("lot-procurement", keys)

    def test_engineering_model_does_not_route_lot_procurement(self):
        case = validate_case(base_spec(model="em", lot_acceptance_data=False))
        keys = [r["key"] for r in applicable_clauses(case)]
        self.assertNotIn("lot-procurement", keys)

    def test_offered_acceptance_data_routes_lot_acceptance_on_a_model_build(self):
        case = validate_case(base_spec(model="eqm", lot_acceptance_data=True))
        keys = [r["key"] for r in applicable_clauses(case)]
        self.assertIn("lot-acceptance", keys)

    def test_no_radiation_environment_drops_the_evaluation_area(self):
        case = validate_case(base_spec(radiation_environment=False))
        keys = [r["key"] for r in applicable_clauses(case)]
        self.assertNotIn("radiation-evaluation", keys)

    def test_supplier_attached_dies_drop_the_assembly_area(self):
        case = validate_case(base_spec(assembled_in_house=False))
        keys = [r["key"] for r in applicable_clauses(case)]
        self.assertNotIn("assembly-and-attachment", keys)

    def test_level_under_the_floor_routes_screening_on_a_model_build(self):
        case = validate_case(base_spec(model="em", quality_level="industrial",
                                       programme_floor="level-2",
                                       lot_acceptance_data=False))
        keys = [r["key"] for r in applicable_clauses(case)]
        self.assertIn("die-screening", keys)

    def test_every_record_carries_a_reason(self):
        for record in applicable_clauses(validate_case(base_spec())):
            self.assertTrue(record["reason"])

    def test_applicability_rejects_a_raw_spec(self):
        with self.assertRaises(ValueError):
            applicable_clauses(["form"])


class ClosureAndOrderTests(unittest.TestCase):
    def test_closure_pulls_in_a_missing_prerequisite(self):
        closed, pulled = close_under_dependencies(["lot-acceptance"])
        self.assertIn("lot-procurement", closed)
        self.assertIn("foundry-selection", pulled)

    def test_closure_marks_nothing_when_the_set_is_already_closed(self):
        _closed, pulled = close_under_dependencies(["scope-and-applicability"])
        self.assertEqual(pulled, [])

    def test_closure_rejects_an_unknown_key(self):
        with self.assertRaises(ValueError):
            close_under_dependencies(["die-burn-in"])

    def test_closure_rejects_a_non_collection(self):
        with self.assertRaises(ValueError):
            close_under_dependencies("lot-acceptance")

    def test_dependency_order_places_prerequisites_first(self):
        ordered = dependency_order(["lot-acceptance"])
        self.assertLess(ordered.index("foundry-selection"), ordered.index("lot-procurement"))
        self.assertLess(ordered.index("lot-procurement"), ordered.index("lot-acceptance"))

    def test_dependency_order_is_reproducible(self):
        first = dependency_order(["lot-acceptance", "die-screening"])
        second = dependency_order(["die-screening", "lot-acceptance"])
        self.assertEqual(first, second)

    def test_topological_order_refuses_a_cycle(self):
        graph = {"a": ("b",), "b": ("a",)}
        with self.assertRaises(ValueError):
            topological_order(["a", "b"], graph)

    def test_topological_order_refuses_a_node_outside_the_graph(self):
        with self.assertRaises(ValueError):
            topological_order(["a", "z"], {"a": ()})

    def test_topological_order_refuses_a_repeated_node(self):
        with self.assertRaises(ValueError):
            topological_order(["a", "a"], {"a": ()})

    def test_topological_order_refuses_a_non_mapping_graph(self):
        with self.assertRaises(ValueError):
            topological_order(["a"], [("a", ())])


class RouteMapTests(unittest.TestCase):
    def test_route_positions_are_one_based_and_dense(self):
        route = route_map(validate_case(base_spec()))
        self.assertEqual([r["position"] for r in route], list(range(1, len(route) + 1)))

    def test_route_never_places_a_clause_before_its_prerequisite(self):
        route = route_map(validate_case(base_spec()))
        position = {r["key"]: r["position"] for r in route}
        for record in route:
            for dep in record["depends_on"]:
                self.assertLess(position[dep], record["position"])

    def test_pulled_in_area_is_marked(self):
        case = validate_case(base_spec(model="em", radiation_environment=False,
                                       assembled_in_house=False,
                                       lot_acceptance_data=False,
                                       quality_level="level-3",
                                       programme_floor="level-3"))
        route = route_map(case)
        self.assertTrue(all(isinstance(r["pulled_in"], bool) for r in route))

    def test_full_flight_case_covers_the_whole_registry(self):
        route = route_map(validate_case(base_spec()))
        self.assertAlmostEqual(coverage_ratio(route), 1.0, places=9)

    def test_lean_model_case_covers_less_than_the_registry(self):
        case = validate_case(base_spec(model="em", radiation_environment=False,
                                       assembled_in_house=False,
                                       lot_acceptance_data=False,
                                       quality_level="level-3",
                                       programme_floor="level-3"))
        self.assertLess(coverage_ratio(route_map(case)), 1.0)

    def test_coverage_ratio_rejects_a_malformed_record(self):
        with self.assertRaises(ValueError):
            coverage_ratio([{"title": "no key here"}])

    def test_coverage_ratio_rejects_an_unknown_key(self):
        with self.assertRaises(ValueError):
            coverage_ratio([{"key": "die-burn-in"}])

    def test_coverage_ratio_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            coverage_ratio({"key": "scope-and-applicability"})


class FindingsAndAssessmentTests(unittest.TestCase):
    def test_clean_flight_case_has_no_findings(self):
        result = assess_procurement_scope(base_spec())
        self.assertTrue(result["clear"])
        self.assertEqual(result["findings"], [])

    def test_packaged_part_is_reported_out_of_scope(self):
        result = assess_procurement_scope(base_spec(form="packaged"))
        self.assertFalse(result["in_scope"])
        self.assertFalse(result["clear"])
        self.assertIn("packaged", result["findings"][0])

    def test_out_of_scope_route_keeps_only_the_scope_area(self):
        result = assess_procurement_scope(base_spec(form="packaged"))
        self.assertEqual([r["key"] for r in result["route"]], ["scope-and-applicability"])

    def test_unassessed_foundry_on_a_flight_build_is_flagged(self):
        findings = scope_findings(validate_case(base_spec(foundry_standing="unassessed")))
        self.assertTrue(any("unassessed foundry" in f for f in findings))

    def test_flight_build_without_acceptance_data_is_flagged(self):
        findings = scope_findings(validate_case(base_spec(lot_acceptance_data=False)))
        self.assertTrue(any("lot acceptance data" in f for f in findings))

    def test_level_below_the_floor_is_flagged(self):
        findings = scope_findings(
            validate_case(base_spec(quality_level="industrial", programme_floor="level-1"))
        )
        self.assertTrue(any("below the programme floor" in f for f in findings))

    def test_level_above_the_floor_is_not_flagged(self):
        findings = scope_findings(
            validate_case(base_spec(quality_level="level-1", programme_floor="level-3"))
        )
        self.assertEqual(findings, [])

    def test_assessment_reports_the_normalised_case(self):
        result = assess_procurement_scope(base_spec(model="EM", lot_acceptance_data=False))
        self.assertEqual(result["case"]["model"], "em")

    def test_assessment_rejects_a_bad_spec(self):
        with self.assertRaises(ValueError):
            assess_procurement_scope(base_spec(foundry_standing="preferred"))

    def test_pulled_in_keys_are_reported_separately(self):
        result = assess_procurement_scope(base_spec())
        self.assertIsInstance(result["pulled_in"], list)
        for key in result["pulled_in"]:
            self.assertIn(key, CLAUSE_KEYS)


if __name__ == "__main__":
    unittest.main()
