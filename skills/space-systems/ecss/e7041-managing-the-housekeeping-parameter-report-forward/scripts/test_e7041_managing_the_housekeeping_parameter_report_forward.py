"""Contract test for the housekeeping forward-control leaf (stdlib unittest)."""

import unittest

from e7041_managing_the_housekeeping_parameter_report_forward_logic import (
    ACCEPTED,
    MAX_STRUCTURES_PER_APPLICATION_PROCESS,
    REASON_ALREADY_FORWARDED,
    REASON_APPLICATION_PROCESS_NOT_CONTROLLED,
    REASON_NOT_IN_CONFIGURATION,
    REASON_STRUCTURE_CAPACITY,
    REASON_STRUCTURE_NOT_DEFINED,
    REASON_SUBSUMED_BY_WILDCARD,
    REASON_WILDCARD_NOT_PARTIALLY_DELETABLE,
    REJECTED,
    add_housekeeping_selections,
    assess_housekeeping_forward_control,
    delete_housekeeping_selections,
    empty_configuration,
    forwarded_structures,
    is_housekeeping_report_forwarded,
    normalize_configuration,
    report_configuration,
    stale_selections,
    structure_is_defined,
    validate_definition_catalogue,
    validate_selection,
)

CONTROLLED = [10, 11]
CATALOGUE = {10: [1, 2, 3], 11: [1, 7]}


def sel(apid=10, structure_id=1):
    return {"apid": apid, "structure_id": structure_id}


class TestCatalogue(unittest.TestCase):
    def test_structure_defined_under_its_own_application_process(self):
        self.assertTrue(structure_is_defined(CATALOGUE, 10, 2))

    def test_same_identifier_under_another_application_process_is_not_the_same(self):
        self.assertFalse(structure_is_defined(CATALOGUE, 11, 2))

    def test_unknown_application_process_defines_nothing(self):
        self.assertFalse(structure_is_defined(CATALOGUE, 12, 1))

    def test_empty_catalogue_raises(self):
        with self.assertRaises(ValueError):
            validate_definition_catalogue({})

    def test_catalogue_entry_must_be_a_collection(self):
        with self.assertRaises(ValueError):
            validate_definition_catalogue({10: 3})

    def test_structure_identifier_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            validate_definition_catalogue({10: [256]})


class TestValidation(unittest.TestCase):
    def test_wildcard_selection_has_no_structure_identifier(self):
        self.assertIsNone(validate_selection({"apid": 10})["structure_id"])

    def test_selection_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_selection([10, 1])

    def test_boolean_application_process_raises(self):
        with self.assertRaises(ValueError):
            validate_selection({"apid": True, "structure_id": 1})

    def test_wildcard_with_explicit_structures_raises(self):
        bad = {10: {"all_structures": True, "structure_ids": [1]}}
        with self.assertRaises(ValueError):
            normalize_configuration(bad)

    def test_normalize_returns_an_independent_copy(self):
        source = {10: {"structure_ids": [1]}}
        copy = normalize_configuration(source)
        copy[10]["structure_ids"].add(2)
        self.assertEqual(source[10]["structure_ids"], [1])


class TestAdd(unittest.TestCase):
    def test_defined_structure_is_forwarded_after_add(self):
        config, disp = add_housekeeping_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel()]
        )
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertTrue(is_housekeeping_report_forwarded(config, 10, 1))
        self.assertFalse(is_housekeeping_report_forwarded(config, 10, 2))

    def test_undefined_structure_is_rejected(self):
        config, disp = add_housekeeping_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(structure_id=9)]
        )
        self.assertEqual(disp[0]["reason"], REASON_STRUCTURE_NOT_DEFINED)
        self.assertEqual(config, {})

    def test_structure_defined_under_another_application_process_is_rejected(self):
        _, disp = add_housekeeping_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(apid=11, structure_id=2)]
        )
        self.assertEqual(disp[0]["reason"], REASON_STRUCTURE_NOT_DEFINED)

    def test_uncontrolled_application_process_is_rejected(self):
        _, disp = add_housekeeping_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(apid=12)]
        )
        self.assertEqual(disp[0]["reason"], REASON_APPLICATION_PROCESS_NOT_CONTROLLED)

    def test_duplicate_structure_is_rejected(self):
        _, disp = add_housekeeping_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(), sel()]
        )
        self.assertEqual(disp[1]["reason"], REASON_ALREADY_FORWARDED)

    def test_wildcard_clears_and_subsumes_explicit_structures(self):
        config, _ = add_housekeeping_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel()]
        )
        config, disp = add_housekeeping_selections(
            config, CONTROLLED, CATALOGUE, [{"apid": 10}, sel(structure_id=2)]
        )
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertEqual(disp[1]["reason"], REASON_SUBSUMED_BY_WILDCARD)
        self.assertEqual(config[10]["structure_ids"], set())
        self.assertTrue(is_housekeeping_report_forwarded(config, 10, 3))

    def test_one_rejected_item_does_not_abandon_the_rest(self):
        config, disp = add_housekeeping_selections(
            empty_configuration(),
            CONTROLLED,
            CATALOGUE,
            [sel(structure_id=9), sel(apid=11, structure_id=7)],
        )
        self.assertEqual(disp[0]["status"], REJECTED)
        self.assertEqual(disp[1]["status"], ACCEPTED)
        self.assertTrue(is_housekeeping_report_forwarded(config, 11, 7))

    def test_structure_capacity_is_a_rejection(self):
        catalogue = {10: list(range(0, MAX_STRUCTURES_PER_APPLICATION_PROCESS + 2))}
        items = [
            sel(structure_id=n)
            for n in range(0, MAX_STRUCTURES_PER_APPLICATION_PROCESS + 2)
        ]
        _, disp = add_housekeeping_selections(
            empty_configuration(), CONTROLLED, catalogue, items
        )
        self.assertEqual(disp[-1]["reason"], REASON_STRUCTURE_CAPACITY)

    def test_items_must_be_a_list(self):
        with self.assertRaises(ValueError):
            add_housekeeping_selections(
                empty_configuration(), CONTROLLED, CATALOGUE, sel()
            )

    def test_empty_controlled_set_raises(self):
        with self.assertRaises(ValueError):
            add_housekeeping_selections(
                empty_configuration(), [], CATALOGUE, [sel()]
            )


class TestDelete(unittest.TestCase):
    def test_deleting_a_structure_stops_forwarding_it(self):
        config, _ = add_housekeeping_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(), sel(structure_id=2)]
        )
        config, disp = delete_housekeeping_selections(config, [sel()])
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertFalse(is_housekeeping_report_forwarded(config, 10, 1))
        self.assertTrue(is_housekeeping_report_forwarded(config, 10, 2))

    def test_deleting_the_application_process_removes_every_structure(self):
        config, _ = add_housekeeping_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(), sel(structure_id=2)]
        )
        config, disp = delete_housekeeping_selections(config, [{"apid": 10}])
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertEqual(config, {})

    def test_deleting_an_absent_structure_is_rejected(self):
        _, disp = delete_housekeeping_selections(empty_configuration(), [sel()])
        self.assertEqual(disp[0]["reason"], REASON_NOT_IN_CONFIGURATION)

    def test_wildcard_cannot_be_partially_deleted(self):
        config, _ = add_housekeeping_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [{"apid": 10}]
        )
        _, disp = delete_housekeeping_selections(config, [sel()])
        self.assertEqual(disp[0]["reason"], REASON_WILDCARD_NOT_PARTIALLY_DELETABLE)


class TestReportAndAssessment(unittest.TestCase):
    def test_wildcard_expands_against_the_live_catalogue(self):
        config, _ = add_housekeeping_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [{"apid": 10}]
        )
        self.assertEqual(forwarded_structures(config, CATALOGUE, 10), [1, 2, 3])
        grown = {10: [1, 2, 3, 4], 11: [1, 7]}
        self.assertEqual(forwarded_structures(config, grown, 10), [1, 2, 3, 4])

    def test_unconfigured_application_process_forwards_nothing(self):
        self.assertEqual(forwarded_structures(empty_configuration(), CATALOGUE, 10), [])

    def test_a_deleted_definition_leaves_a_stale_selection(self):
        config, _ = add_housekeeping_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(structure_id=3)]
        )
        shrunk = {10: [1, 2], 11: [1, 7]}
        self.assertEqual(
            stale_selections(config, shrunk), [{"apid": 10, "structure_id": 3}]
        )

    def test_a_wildcard_never_goes_stale(self):
        config, _ = add_housekeeping_selections(
            empty_configuration(), CONTROLLED, CATALOGUE, [{"apid": 10}]
        )
        self.assertEqual(stale_selections(config, {10: [], 11: [1]}), [])

    def test_report_is_sorted(self):
        config, _ = add_housekeeping_selections(
            empty_configuration(),
            CONTROLLED,
            CATALOGUE,
            [sel(apid=11, structure_id=7), sel(structure_id=3), sel(structure_id=1)],
        )
        report = report_configuration(config)
        self.assertEqual([e["apid"] for e in report["application_processes"]], [10, 11])
        self.assertEqual(report["application_processes"][0]["structure_ids"], [1, 3])

    def test_assessment_is_clean_when_nothing_was_rejected(self):
        result = assess_housekeeping_forward_control(
            empty_configuration(),
            CONTROLLED,
            CATALOGUE,
            [{"operation": "add", "items": [sel(), sel(structure_id=2)]}],
        )
        self.assertTrue(result["clean"])
        self.assertEqual(result["rejected_total"], 0)

    def test_assessment_counts_rejections_across_requests(self):
        result = assess_housekeeping_forward_control(
            empty_configuration(),
            CONTROLLED,
            CATALOGUE,
            [
                {"operation": "add", "items": [sel(), sel(structure_id=9)]},
                {"operation": "delete", "items": [sel(structure_id=2)]},
            ],
        )
        self.assertEqual(result["rejected_total"], 2)
        self.assertFalse(result["clean"])

    def test_unknown_operation_raises(self):
        with self.assertRaises(ValueError):
            assess_housekeeping_forward_control(
                empty_configuration(), CONTROLLED, CATALOGUE, [{"operation": "flush"}]
            )

    def test_empty_request_list_raises(self):
        with self.assertRaises(ValueError):
            assess_housekeeping_forward_control(
                empty_configuration(), CONTROLLED, CATALOGUE, []
            )


if __name__ == "__main__":
    unittest.main()
