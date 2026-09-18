"""Contract test for the diagnostic forward-control leaf (stdlib unittest)."""

import unittest

from e7041_managing_the_diagnostic_parameter_report_forward_logic import (
    ACCEPTED,
    FINDING_DORMANT_SELECTION,
    FINDING_RATE_OVER_BUDGET,
    FINDING_STALE_SELECTION,
    MAX_STRUCTURES_PER_APPLICATION_PROCESS,
    REASON_ALREADY_FORWARDED,
    REASON_APPLICATION_PROCESS_NOT_CONTROLLED,
    REASON_NOT_IN_CONFIGURATION,
    REASON_STRUCTURE_CAPACITY,
    REASON_STRUCTURE_NOT_DEFINED,
    REASON_SUBSUMED_BY_WILDCARD,
    REASON_WILDCARD_NOT_PARTIALLY_DELETABLE,
    REJECTED,
    add_diagnostic_selections,
    assess_diagnostic_forward_control,
    delete_diagnostic_selections,
    dormant_selections,
    empty_configuration,
    forwarded_report_rate_hz,
    grade_rate_budget,
    is_diagnostic_report_forwarded,
    normalize_configuration,
    report_configuration,
    selected_structures,
    stale_selections,
    structure_is_defined,
    structure_report_rate_hz,
    validate_definition_catalogue,
    validate_selection,
)

CONTROLLED = [10, 11]
CATALOGUE = {
    10: {
        1: {"collection_interval_s": 8.0, "collection_enabled": True},
        2: {"collection_interval_s": 8.0, "collection_enabled": True},
        3: {"collection_interval_s": 4.0, "collection_enabled": False},
    },
    11: {
        7: {"collection_interval_s": 2.0, "collection_enabled": True},
    },
}


def sel(apid=10, structure_id=1):
    return {"apid": apid, "structure_id": structure_id}


class TestCatalogue(unittest.TestCase):
    def test_structure_defined_under_its_own_application_process(self):
        self.assertTrue(structure_is_defined(CATALOGUE, 10, 2))

    def test_same_identifier_under_another_application_process_is_not_the_same(self):
        self.assertFalse(structure_is_defined(CATALOGUE, 11, 2))

    def test_catalogue_entry_must_be_a_mapping_of_definitions(self):
        with self.assertRaises(ValueError):
            validate_definition_catalogue({10: [1, 2]})

    def test_non_positive_collection_interval_raises(self):
        with self.assertRaises(ValueError):
            validate_definition_catalogue(
                {10: {1: {"collection_interval_s": 0.0}}}
            )

    def test_non_boolean_collection_enabled_raises(self):
        with self.assertRaises(ValueError):
            validate_definition_catalogue(
                {10: {1: {"collection_interval_s": 1.0, "collection_enabled": "yes"}}}
            )

    def test_empty_catalogue_raises(self):
        with self.assertRaises(ValueError):
            validate_definition_catalogue({})

    def test_selection_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_selection([10, 1])

    def test_wildcard_and_explicit_structures_together_raise(self):
        with self.assertRaises(ValueError):
            normalize_configuration({10: {"all_structures": True, "structure_ids": [1]}})


class TestRates(unittest.TestCase):
    def test_enabled_structure_rate_is_the_reciprocal_interval(self):
        self.assertAlmostEqual(
            structure_report_rate_hz(CATALOGUE, 10, 1), 0.125, places=9
        )

    def test_disabled_structure_contributes_no_rate(self):
        self.assertAlmostEqual(
            structure_report_rate_hz(CATALOGUE, 10, 3), 0.0, places=9
        )

    def test_undefined_structure_rate_raises(self):
        with self.assertRaises(ValueError):
            structure_report_rate_hz(CATALOGUE, 10, 9)

    def test_forwarded_rate_sums_the_selected_structures(self):
        config, _ = add_diagnostic_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(), sel(structure_id=2)]
        )
        self.assertAlmostEqual(
            forwarded_report_rate_hz(config, CATALOGUE), 0.25, places=9
        )

    def test_wildcard_rate_skips_the_disabled_structure(self):
        config, _ = add_diagnostic_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [{"apid": 10}]
        )
        self.assertAlmostEqual(
            forwarded_report_rate_hz(config, CATALOGUE), 0.25, places=9
        )

    def test_a_rate_exactly_on_budget_is_inside_it(self):
        config, _ = add_diagnostic_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(), sel(structure_id=2)]
        )
        grade = grade_rate_budget(config, CATALOGUE, 0.25)
        self.assertAlmostEqual(grade["forwarded_rate_hz"], grade["budget_hz"], places=9)
        self.assertTrue(grade["within_budget"])
        self.assertEqual(grade["findings"], [])

    def test_a_rate_well_over_budget_is_a_finding(self):
        config, _ = add_diagnostic_selections(
            empty_configuration(),
            CONTROLLED,
            CATALOGUE,
            [sel(), sel(structure_id=2), sel(apid=11, structure_id=7)],
        )
        grade = grade_rate_budget(config, CATALOGUE, 0.25)
        self.assertFalse(grade["within_budget"])
        self.assertEqual(grade["findings"], [FINDING_RATE_OVER_BUDGET])
        self.assertGreater(grade["forwarded_rate_hz"], grade["budget_hz"])

    def test_non_positive_budget_raises(self):
        with self.assertRaises(ValueError):
            grade_rate_budget(empty_configuration(), CATALOGUE, 0.0)


class TestAddAndDelete(unittest.TestCase):
    def test_defined_structure_is_forwarded_after_add(self):
        config, disp = add_diagnostic_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel()]
        )
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertTrue(is_diagnostic_report_forwarded(config, 10, 1))
        self.assertFalse(is_diagnostic_report_forwarded(config, 10, 2))

    def test_undefined_structure_is_rejected(self):
        config, disp = add_diagnostic_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(structure_id=9)]
        )
        self.assertEqual(disp[0]["reason"], REASON_STRUCTURE_NOT_DEFINED)
        self.assertEqual(config, {})

    def test_uncontrolled_application_process_is_rejected(self):
        _, disp = add_diagnostic_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(apid=12)]
        )
        self.assertEqual(disp[0]["reason"], REASON_APPLICATION_PROCESS_NOT_CONTROLLED)

    def test_duplicate_structure_is_rejected(self):
        _, disp = add_diagnostic_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(), sel()]
        )
        self.assertEqual(disp[1]["reason"], REASON_ALREADY_FORWARDED)

    def test_wildcard_subsumes_a_later_structure(self):
        config, disp = add_diagnostic_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [{"apid": 10}, sel()]
        )
        self.assertEqual(disp[1]["reason"], REASON_SUBSUMED_BY_WILDCARD)
        self.assertEqual(config[10]["structure_ids"], set())

    def test_one_rejected_item_does_not_abandon_the_rest(self):
        config, disp = add_diagnostic_selections(
            empty_configuration(),
            CONTROLLED,
            CATALOGUE,
            [sel(structure_id=9), sel(apid=11, structure_id=7)],
        )
        self.assertEqual(disp[0]["status"], REJECTED)
        self.assertEqual(disp[1]["status"], ACCEPTED)

    def test_structure_capacity_is_a_rejection(self):
        catalogue = {
            10: {
                n: {"collection_interval_s": 100.0}
                for n in range(0, MAX_STRUCTURES_PER_APPLICATION_PROCESS + 2)
            }
        }
        items = [
            sel(structure_id=n)
            for n in range(0, MAX_STRUCTURES_PER_APPLICATION_PROCESS + 2)
        ]
        _, disp = add_diagnostic_selections(
            empty_configuration(), CONTROLLED, catalogue, items
        )
        self.assertEqual(disp[-1]["reason"], REASON_STRUCTURE_CAPACITY)

    def test_deleting_a_structure_stops_forwarding_it(self):
        config, _ = add_diagnostic_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(), sel(structure_id=2)]
        )
        config, disp = delete_diagnostic_selections(config, [sel()])
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertFalse(is_diagnostic_report_forwarded(config, 10, 1))
        self.assertTrue(is_diagnostic_report_forwarded(config, 10, 2))

    def test_deleting_an_absent_structure_is_rejected(self):
        _, disp = delete_diagnostic_selections(empty_configuration(), [sel()])
        self.assertEqual(disp[0]["reason"], REASON_NOT_IN_CONFIGURATION)

    def test_wildcard_cannot_be_partially_deleted(self):
        config, _ = add_diagnostic_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [{"apid": 10}]
        )
        _, disp = delete_diagnostic_selections(config, [sel()])
        self.assertEqual(disp[0]["reason"], REASON_WILDCARD_NOT_PARTIALLY_DELETABLE)

    def test_items_must_be_a_list(self):
        with self.assertRaises(ValueError):
            add_diagnostic_selections(
                empty_configuration(), CONTROLLED, CATALOGUE, sel()
            )


class TestFindingsAndReport(unittest.TestCase):
    def test_dormant_selection_is_reported_not_rejected(self):
        config, disp = add_diagnostic_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(structure_id=3)]
        )
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertEqual(
            dormant_selections(config, CATALOGUE), [{"apid": 10, "structure_id": 3}]
        )

    def test_an_enabled_selection_is_not_dormant(self):
        config, _ = add_diagnostic_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel()]
        )
        self.assertEqual(dormant_selections(config, CATALOGUE), [])

    def test_a_deleted_definition_leaves_a_stale_selection(self):
        config, _ = add_diagnostic_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(structure_id=2)]
        )
        shrunk = {
            10: {1: {"collection_interval_s": 8.0}},
            11: {7: {"collection_interval_s": 2.0}},
        }
        self.assertEqual(
            stale_selections(config, shrunk), [{"apid": 10, "structure_id": 2}]
        )

    def test_selected_structures_are_intersected_with_the_catalogue(self):
        config, _ = add_diagnostic_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(), sel(structure_id=2)]
        )
        self.assertEqual(selected_structures(config, CATALOGUE, 10), [1, 2])
        self.assertEqual(selected_structures(config, CATALOGUE, 11), [])

    def test_report_is_sorted(self):
        config, _ = add_diagnostic_selections(
            empty_configuration(),
            CONTROLLED,
            CATALOGUE,
            [sel(apid=11, structure_id=7), sel(structure_id=2), sel(structure_id=1)],
        )
        report = report_configuration(config)
        self.assertEqual([e["apid"] for e in report["application_processes"]], [10, 11])
        self.assertEqual(report["application_processes"][0]["structure_ids"], [1, 2])

    def test_assessment_is_acceptable_when_nothing_is_flagged(self):
        result = assess_diagnostic_forward_control(
            empty_configuration(),
            CONTROLLED,
            CATALOGUE,
            [{"operation": "add", "items": [sel(), sel(structure_id=2)]}],
            0.25,
        )
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["rejected_total"], 0)

    def test_assessment_collects_dormant_and_over_budget_findings(self):
        result = assess_diagnostic_forward_control(
            empty_configuration(),
            CONTROLLED,
            CATALOGUE,
            [
                {
                    "operation": "add",
                    "items": [sel(), sel(structure_id=3), sel(apid=11, structure_id=7)],
                }
            ],
            0.2,
        )
        self.assertIn(FINDING_RATE_OVER_BUDGET, result["findings"])
        self.assertIn(FINDING_DORMANT_SELECTION, result["findings"])
        self.assertNotIn(FINDING_STALE_SELECTION, result["findings"])
        self.assertFalse(result["acceptable"])

    def test_unknown_operation_raises(self):
        with self.assertRaises(ValueError):
            assess_diagnostic_forward_control(
                empty_configuration(), CONTROLLED, CATALOGUE, [{"operation": "purge"}], 1.0
            )

    def test_empty_request_list_raises(self):
        with self.assertRaises(ValueError):
            assess_diagnostic_forward_control(
                empty_configuration(), CONTROLLED, CATALOGUE, [], 1.0
            )


if __name__ == "__main__":
    unittest.main()
