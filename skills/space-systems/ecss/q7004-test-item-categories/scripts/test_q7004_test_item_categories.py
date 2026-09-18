#!/usr/bin/env python3
"""Contract test for the thermal test item categorization (offline)."""

import copy
import unittest

from q7004_test_item_categories_logic import (
    ASSEMBLY,
    DEFAULT_CATEGORY_POLICY,
    ITEM_CATEGORIES,
    MATERIAL,
    MECHANICAL_PART,
    PROCESS,
    categorize_item,
    group_items,
    normalize_operations,
    plan_test_items,
    result_coverage,
    specimen_definition,
    specimen_demand,
    validate_category_policy,
)

RAW_MATERIAL = {
    "id": "cfrp-laminate-lot-7",
    "distinct_part_count": 1,
    "joined_into_one_unit": False,
    "applied_operations": [],
    "has_mechanical_function": False,
}

BONDED_COUPON = {
    "id": "epoxy-bond-coupon",
    "distinct_part_count": 1,
    "joined_into_one_unit": False,
    "applied_operations": ["adhesive bonding"],
    "has_mechanical_function": False,
}

BRACKET = {
    "id": "titanium-bracket",
    "distinct_part_count": 1,
    "joined_into_one_unit": False,
    "applied_operations": [],
    "has_mechanical_function": True,
}

HINGE_UNIT = {
    "id": "deployment-hinge",
    "distinct_part_count": 4,
    "joined_into_one_unit": True,
    "applied_operations": ["fastening"],
    "has_mechanical_function": True,
}

ALL_ITEMS = [RAW_MATERIAL, BONDED_COUPON, BRACKET, HINGE_UNIT]


def _item(base, **overrides):
    item = copy.deepcopy(base)
    item.update(overrides)
    return item


class OperationNormalizationTests(unittest.TestCase):
    def test_absent_operations_normalize_to_empty(self):
        self.assertEqual(normalize_operations(None), ())

    def test_names_are_lowercased_and_stripped(self):
        self.assertEqual(normalize_operations([" Welding "]), ("welding",))

    def test_a_bare_string_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_operations("bonding")

    def test_a_duplicate_operation_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_operations(["bonding", "Bonding"])

    def test_an_empty_operation_name_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_operations(["bonding", "   "])


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_category_policy(DEFAULT_CATEGORY_POLICY), DEFAULT_CATEGORY_POLICY
        )

    def test_policy_covers_every_category(self):
        for category in ITEM_CATEGORIES:
            self.assertIn(category, DEFAULT_CATEGORY_POLICY["minimum_specimens"])
            self.assertIn(category, DEFAULT_CATEGORY_POLICY["reference_specimens"])

    def test_policy_missing_a_category_rejected(self):
        broken = copy.deepcopy(DEFAULT_CATEGORY_POLICY)
        del broken["minimum_specimens"][PROCESS]
        with self.assertRaises(ValueError):
            validate_category_policy(broken)

    def test_policy_with_a_zero_minimum_rejected(self):
        broken = copy.deepcopy(DEFAULT_CATEGORY_POLICY)
        broken["minimum_specimens"][MATERIAL] = 0
        with self.assertRaises(ValueError):
            validate_category_policy(broken)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_category_policy([3, 5, 3, 2])


class CategorizationTests(unittest.TestCase):
    def test_plain_stock_is_a_material(self):
        self.assertEqual(categorize_item(RAW_MATERIAL), MATERIAL)

    def test_a_coupon_carrying_an_operation_is_a_process_item(self):
        self.assertEqual(categorize_item(BONDED_COUPON), PROCESS)

    def test_a_single_functional_piece_is_a_mechanical_part(self):
        self.assertEqual(categorize_item(BRACKET), MECHANICAL_PART)

    def test_several_joined_pieces_are_an_assembly(self):
        self.assertEqual(categorize_item(HINGE_UNIT), ASSEMBLY)

    def test_an_assembly_outranks_the_operation_that_built_it(self):
        item = _item(HINGE_UNIT, applied_operations=["welding"])
        self.assertEqual(categorize_item(item), ASSEMBLY)

    def test_an_operation_outranks_a_mechanical_function_on_one_piece(self):
        item = _item(BRACKET, applied_operations=["conversion coating"])
        self.assertEqual(categorize_item(item), PROCESS)

    def test_loose_unjoined_pieces_are_rejected(self):
        item = _item(HINGE_UNIT, joined_into_one_unit=False)
        with self.assertRaises(ValueError):
            categorize_item(item)

    def test_a_zero_part_count_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_item(_item(RAW_MATERIAL, distinct_part_count=0))

    def test_a_non_integer_part_count_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_item(_item(RAW_MATERIAL, distinct_part_count=1.0))

    def test_a_non_boolean_mechanical_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_item(_item(BRACKET, has_mechanical_function="yes"))

    def test_a_non_mapping_item_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_item("a bracket")


class SpecimenDefinitionTests(unittest.TestCase):
    def test_every_category_has_a_specimen_form_and_a_measured_property(self):
        for category in ITEM_CATEGORIES:
            definition = specimen_definition(category)
            self.assertTrue(definition["specimen_form"])
            self.assertTrue(definition["measured_property"])

    def test_a_process_specimen_carries_the_operation(self):
        self.assertIn("operation", specimen_definition(PROCESS)["specimen_form"])

    def test_an_assembly_specimen_keeps_its_interfaces(self):
        self.assertIn("interfaces", specimen_definition(ASSEMBLY)["specimen_form"])

    def test_an_unknown_category_is_rejected(self):
        with self.assertRaises(ValueError):
            specimen_definition("subsystem")


class CoverageTests(unittest.TestCase):
    def test_an_assembly_result_does_not_reach_its_materials(self):
        excluded = result_coverage(ASSEMBLY)["does_not_cover"]
        self.assertTrue(any("constituent materials" in e for e in excluded))

    def test_a_material_result_does_not_reach_an_operation(self):
        excluded = result_coverage(MATERIAL)["does_not_cover"]
        self.assertTrue(any("operation" in e for e in excluded))

    def test_a_process_result_follows_the_tested_procedure(self):
        covered = result_coverage(PROCESS)["covers"]
        self.assertTrue(any("procedure" in c for c in covered))

    def test_a_part_result_does_not_reach_the_assembly(self):
        excluded = result_coverage(MECHANICAL_PART)["does_not_cover"]
        self.assertTrue(any("assembly" in e for e in excluded))

    def test_every_category_excludes_something(self):
        for category in ITEM_CATEGORIES:
            self.assertTrue(result_coverage(category)["does_not_cover"])


class GroupingTests(unittest.TestCase):
    def test_a_mixed_campaign_lands_one_item_in_each_category(self):
        grouped = group_items(ALL_ITEMS)
        for category in ITEM_CATEGORIES:
            self.assertEqual(len(grouped[category]), 1)

    def test_grouped_ids_are_sorted(self):
        items = [
            _item(RAW_MATERIAL, id="zinc-stock"),
            _item(RAW_MATERIAL, id="alumina-stock"),
        ]
        self.assertEqual(group_items(items)[MATERIAL], ("alumina-stock", "zinc-stock"))

    def test_every_category_key_is_present_even_when_empty(self):
        grouped = group_items([RAW_MATERIAL])
        self.assertEqual(set(grouped), set(ITEM_CATEGORIES))
        self.assertEqual(grouped[ASSEMBLY], ())

    def test_a_duplicate_item_id_is_rejected(self):
        with self.assertRaises(ValueError):
            group_items([RAW_MATERIAL, _item(BRACKET, id=RAW_MATERIAL["id"])])

    def test_an_item_without_an_id_is_rejected(self):
        item = _item(RAW_MATERIAL)
        del item["id"]
        with self.assertRaises(ValueError):
            group_items([item])

    def test_an_empty_campaign_is_rejected(self):
        with self.assertRaises(ValueError):
            group_items([])


class SpecimenDemandTests(unittest.TestCase):
    def test_a_single_material_needs_its_minimum_plus_a_reference(self):
        demand = specimen_demand(group_items([RAW_MATERIAL]))
        self.assertEqual(demand["per_category"][MATERIAL], 4)
        self.assertEqual(demand["total"], 4)

    def test_a_process_item_needs_more_specimens_than_an_assembly(self):
        process_demand = specimen_demand(group_items([BONDED_COUPON]))["total"]
        assembly_demand = specimen_demand(group_items([HINGE_UNIT]))["total"]
        self.assertGreater(process_demand, assembly_demand)

    def test_demand_scales_with_the_number_of_items_in_a_category(self):
        one = specimen_demand(group_items([RAW_MATERIAL]))["total"]
        two = specimen_demand(
            group_items([RAW_MATERIAL, _item(RAW_MATERIAL, id="second-lot")])
        )["total"]
        self.assertEqual(two, 2 * one)

    def test_total_is_the_sum_over_categories(self):
        demand = specimen_demand(group_items(ALL_ITEMS))
        self.assertEqual(demand["total"], sum(demand["per_category"].values()))

    def test_a_grouped_map_missing_a_category_is_rejected(self):
        grouped = group_items(ALL_ITEMS)
        del grouped[PROCESS]
        with self.assertRaises(ValueError):
            specimen_demand(grouped)

    def test_a_broken_policy_is_rejected(self):
        broken = copy.deepcopy(DEFAULT_CATEGORY_POLICY)
        del broken["reference_specimens"]
        with self.assertRaises(ValueError):
            specimen_demand(group_items(ALL_ITEMS), broken)


class PlanTests(unittest.TestCase):
    def test_a_mixed_campaign_lists_every_category_as_present(self):
        plan = plan_test_items(ALL_ITEMS)
        self.assertEqual(set(plan["categories_present"]), set(ITEM_CATEGORIES))

    def test_a_mixed_campaign_owes_a_per_category_report(self):
        plan = plan_test_items(ALL_ITEMS)
        self.assertTrue(any("separately" in duty for duty in plan["duties"]))

    def test_an_assembly_only_campaign_raises_the_reach_finding(self):
        plan = plan_test_items([HINGE_UNIT])
        self.assertTrue(any("does not reach" in f for f in plan["findings"]))

    def test_a_process_campaign_owes_the_procedure_record(self):
        plan = plan_test_items([BONDED_COUPON])
        self.assertTrue(any("procedure" in duty for duty in plan["duties"]))

    def test_a_material_campaign_owes_an_uncycled_reference(self):
        plan = plan_test_items([RAW_MATERIAL])
        self.assertTrue(any("uncycled reference" in duty for duty in plan["duties"]))

    def test_definitions_and_coverage_are_only_built_for_present_categories(self):
        plan = plan_test_items([RAW_MATERIAL])
        self.assertEqual(set(plan["definitions"]), {MATERIAL})
        self.assertEqual(set(plan["coverage"]), {MATERIAL})

    def test_the_plan_carries_the_specimen_demand(self):
        plan = plan_test_items(ALL_ITEMS)
        self.assertEqual(plan["specimen_demand"]["total"], 4 + 6 + 4 + 2)

    def test_the_plan_rejects_a_non_list_campaign(self):
        with self.assertRaises(ValueError):
            plan_test_items(RAW_MATERIAL)


if __name__ == "__main__":
    unittest.main()
