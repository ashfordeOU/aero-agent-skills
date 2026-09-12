#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 6.3.1.1 circuit
criticality categories.

Exercises scripts/e20_circuit_criticality_categories_logic.py (stdlib
unittest, offline). Contract: the ladder runs safety critical, mission
critical, essential, non essential and an off-ladder name raises; a
circuit's category follows from its hazard, mission-loss, redundancy
and degradation attributes, with the hazard question answered first
and a missing or non-boolean attribute raising; an aggressor is raised
to the level of the most critical victim it couples into; the margin
each category demands comes from the project ladder; a demonstrated
separation that is exactly on the limit in engineering terms passes
even when the decibel subtraction lands a few units in the last place
below it; groups are presented with the safety group first; and the
aggregate review is compliant only when the coupling, evidence and
margin lists are all empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_circuit_criticality_categories_logic as cc  # noqa: E402


def _attributes(hazard=False, ends_mission=False, redundant=False, degrades=False):
    return {
        "causes_catastrophic_hazard": hazard,
        "loss_ends_mission": ends_mission,
        "redundancy_available": redundant,
        "degrades_recoverable_performance": degrades,
    }


def _clean_inventory():
    """An inventory where every circuit meets the margin its effective
    category demands."""
    return {
        "circuits": [
            {
                "circuit_id": "PYRO-ARM-01",
                "attributes": _attributes(hazard=True),
                "demonstrated": {
                    "susceptibility_threshold_dbuv": 60.0,
                    "emission_level_dbuv": 38.0,
                },
            },
            {
                "circuit_id": "TC-DECODER-01",
                "attributes": _attributes(ends_mission=True),
                "demonstrated": {
                    "susceptibility_threshold_dbuv": 54.0,
                    "emission_level_dbuv": 40.0,
                },
            },
            {
                "circuit_id": "HTR-SW-01",
                "attributes": _attributes(degrades=True),
                "demonstrated": {
                    "susceptibility_threshold_dbuv": 33.3,
                    "emission_level_dbuv": 27.3,
                },
            },
            {
                "circuit_id": "HK-TEMP-07",
                "attributes": _attributes(),
            },
        ]
    }


class CriticalityRankTest(unittest.TestCase):
    def test_safety_group_heads_the_ladder(self):
        self.assertEqual(cc.criticality_rank("safety_critical"), 1)

    def test_mission_group_follows_the_safety_group(self):
        self.assertEqual(cc.criticality_rank("mission_critical"), 2)

    def test_non_essential_group_is_last(self):
        self.assertEqual(cc.criticality_rank("non_essential"), 4)

    def test_ladder_order_is_strictly_increasing(self):
        ranks = [cc.criticality_rank(name) for name in cc.CRITICALITY_ORDER]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(len(set(ranks)), len(ranks))

    def test_off_ladder_name_raises(self):
        with self.assertRaises(ValueError):
            cc.criticality_rank("somewhat_important")

    def test_none_category_raises(self):
        with self.assertRaises(ValueError):
            cc.criticality_rank(None)


class CategorizeCircuitTest(unittest.TestCase):
    def test_catastrophic_hazard_is_safety_critical(self):
        self.assertEqual(
            cc.categorize_circuit(_attributes(hazard=True)), "safety_critical"
        )

    def test_hazard_wins_over_every_other_attribute(self):
        attributes = _attributes(
            hazard=True, ends_mission=True, redundant=True, degrades=True
        )
        self.assertEqual(cc.categorize_circuit(attributes), "safety_critical")

    def test_unbacked_mission_loss_is_mission_critical(self):
        self.assertEqual(
            cc.categorize_circuit(_attributes(ends_mission=True)), "mission_critical"
        )

    def test_redundant_mission_loss_drops_to_essential(self):
        self.assertEqual(
            cc.categorize_circuit(_attributes(ends_mission=True, redundant=True)),
            "essential",
        )

    def test_recoverable_degradation_is_essential(self):
        self.assertEqual(cc.categorize_circuit(_attributes(degrades=True)), "essential")

    def test_benign_circuit_is_non_essential(self):
        self.assertEqual(cc.categorize_circuit(_attributes()), "non_essential")

    def test_redundancy_alone_does_not_change_a_benign_circuit(self):
        self.assertEqual(
            cc.categorize_circuit(_attributes(redundant=True)), "non_essential"
        )

    def test_missing_attribute_raises(self):
        attributes = _attributes()
        del attributes["redundancy_available"]
        with self.assertRaises(ValueError):
            cc.categorize_circuit(attributes)

    def test_non_boolean_attribute_raises(self):
        attributes = _attributes()
        attributes["loss_ends_mission"] = "yes"
        with self.assertRaises(ValueError):
            cc.categorize_circuit(attributes)

    def test_integer_attribute_raises(self):
        attributes = _attributes()
        attributes["causes_catastrophic_hazard"] = 1
        with self.assertRaises(ValueError):
            cc.categorize_circuit(attributes)

    def test_non_mapping_attributes_raises(self):
        with self.assertRaises(ValueError):
            cc.categorize_circuit(["causes_catastrophic_hazard"])


class MoreCriticalTest(unittest.TestCase):
    def test_safety_beats_mission(self):
        self.assertEqual(
            cc.more_critical("mission_critical", "safety_critical"), "safety_critical"
        )

    def test_essential_beats_non_essential(self):
        self.assertEqual(
            cc.more_critical("non_essential", "essential"), "essential"
        )

    def test_equal_categories_return_that_category(self):
        self.assertEqual(
            cc.more_critical("essential", "essential"), "essential"
        )

    def test_off_ladder_argument_raises(self):
        with self.assertRaises(ValueError):
            cc.more_critical("essential", "quite_important")


class EffectiveCategoryTest(unittest.TestCase):
    def test_no_coupling_leaves_the_category_alone(self):
        self.assertEqual(cc.effective_category("non_essential", []), "non_essential")

    def test_coupling_into_a_safety_victim_raises_the_aggressor(self):
        self.assertEqual(
            cc.effective_category("non_essential", ["safety_critical"]),
            "safety_critical",
        )

    def test_the_most_critical_victim_sets_the_level(self):
        self.assertEqual(
            cc.effective_category(
                "essential", ["non_essential", "mission_critical", "essential"]
            ),
            "mission_critical",
        )

    def test_a_less_critical_victim_never_lowers_the_aggressor(self):
        self.assertEqual(
            cc.effective_category("safety_critical", ["non_essential"]),
            "safety_critical",
        )

    def test_string_victim_list_raises(self):
        with self.assertRaises(ValueError):
            cc.effective_category("essential", "safety_critical")

    def test_off_ladder_own_category_raises(self):
        with self.assertRaises(ValueError):
            cc.effective_category("quite_important", [])

    def test_off_ladder_victim_category_raises(self):
        with self.assertRaises(ValueError):
            cc.effective_category("essential", ["quite_important"])


class RequiredMarginTest(unittest.TestCase):
    def test_safety_group_demands_the_widest_margin(self):
        self.assertAlmostEqual(
            cc.required_interference_margin_db("safety_critical"), 20.0, places=9
        )

    def test_mission_group_demands_twelve_decibels(self):
        self.assertAlmostEqual(
            cc.required_interference_margin_db("mission_critical"), 12.0, places=9
        )

    def test_essential_group_demands_six_decibels(self):
        self.assertAlmostEqual(
            cc.required_interference_margin_db("essential"), 6.0, places=9
        )

    def test_margin_demand_falls_monotonically_down_the_ladder(self):
        demands = [
            cc.required_interference_margin_db(name)
            for name in cc.CRITICALITY_ORDER
        ]
        self.assertEqual(demands, sorted(demands, reverse=True))

    def test_off_ladder_category_raises(self):
        with self.assertRaises(ValueError):
            cc.required_interference_margin_db("quite_important")


class InterferenceMarginTest(unittest.TestCase):
    def test_margin_is_threshold_less_emission(self):
        self.assertAlmostEqual(cc.interference_margin_db(54.0, 40.0), 14.0, places=9)

    def test_emission_above_the_threshold_gives_a_negative_margin(self):
        self.assertAlmostEqual(cc.interference_margin_db(30.0, 42.0), -12.0, places=9)

    def test_equal_levels_give_zero_margin(self):
        self.assertAlmostEqual(cc.interference_margin_db(41.5, 41.5), 0.0, places=9)

    def test_non_finite_threshold_raises(self):
        with self.assertRaises(ValueError):
            cc.interference_margin_db(float("nan"), 40.0)

    def test_infinite_emission_raises(self):
        with self.assertRaises(ValueError):
            cc.interference_margin_db(54.0, float("inf"))

    def test_string_level_raises(self):
        with self.assertRaises(ValueError):
            cc.interference_margin_db("54", 40.0)

    def test_boolean_level_raises(self):
        with self.assertRaises(ValueError):
            cc.interference_margin_db(True, 40.0)


class MarginSatisfiesTest(unittest.TestCase):
    def test_a_comfortable_margin_passes(self):
        self.assertTrue(cc.margin_satisfies(14.0, 12.0))

    def test_a_clear_shortfall_fails(self):
        self.assertFalse(cc.margin_satisfies(5.9, 6.0))

    def test_a_negative_margin_fails(self):
        self.assertFalse(cc.margin_satisfies(-3.0, 6.0))

    def test_an_exact_limit_case_passes(self):
        self.assertTrue(cc.margin_satisfies(6.0, 6.0))

    def test_decibel_subtraction_below_the_limit_by_representation_error_passes(self):
        demonstrated = cc.interference_margin_db(33.3, 27.3)
        self.assertLess(demonstrated, 6.0)
        self.assertTrue(cc.margin_satisfies(demonstrated, 6.0))

    def test_the_tolerance_does_not_widen_the_engineering_limit(self):
        self.assertFalse(cc.margin_satisfies(6.0 - 1e-3, 6.0))

    def test_non_finite_demonstrated_value_raises(self):
        with self.assertRaises(ValueError):
            cc.margin_satisfies(float("nan"), 6.0)

    def test_string_required_value_raises(self):
        with self.assertRaises(ValueError):
            cc.margin_satisfies(6.0, "6")


class ValidateCircuitTest(unittest.TestCase):
    def test_victims_are_deduplicated_and_sorted(self):
        record = cc.validate_circuit(
            {
                "circuit_id": "C-1",
                "attributes": _attributes(),
                "coupled_victim_ids": ["C-3", "C-2", "C-3"],
            }
        )
        self.assertEqual(record["coupled_victim_ids"], ("C-2", "C-3"))

    def test_non_mapping_circuit_raises(self):
        with self.assertRaises(ValueError):
            cc.validate_circuit(["C-1"])

    def test_empty_circuit_id_raises(self):
        with self.assertRaises(ValueError):
            cc.validate_circuit({"circuit_id": "  ", "attributes": _attributes()})

    def test_missing_attributes_raises(self):
        with self.assertRaises(ValueError):
            cc.validate_circuit({"circuit_id": "C-1"})

    def test_string_victim_list_raises(self):
        with self.assertRaises(ValueError):
            cc.validate_circuit(
                {
                    "circuit_id": "C-1",
                    "attributes": _attributes(),
                    "coupled_victim_ids": "C-2",
                }
            )

    def test_empty_victim_id_raises(self):
        with self.assertRaises(ValueError):
            cc.validate_circuit(
                {
                    "circuit_id": "C-1",
                    "attributes": _attributes(),
                    "coupled_victim_ids": [""],
                }
            )

    def test_non_mapping_demonstrated_raises(self):
        with self.assertRaises(ValueError):
            cc.validate_circuit(
                {
                    "circuit_id": "C-1",
                    "attributes": _attributes(),
                    "demonstrated": [54.0, 40.0],
                }
            )


class GroupCircuitsTest(unittest.TestCase):
    def test_every_ladder_rung_is_present(self):
        groups = cc.group_circuits(_clean_inventory()["circuits"])
        self.assertEqual(set(groups), set(cc.CRITICALITY_ORDER))

    def test_the_pyro_arm_lands_in_the_safety_group(self):
        groups = cc.group_circuits(_clean_inventory()["circuits"])
        self.assertEqual(groups["safety_critical"], ["PYRO-ARM-01"])

    def test_group_members_are_sorted(self):
        circuits = [
            {"circuit_id": "C-B", "attributes": _attributes()},
            {"circuit_id": "C-A", "attributes": _attributes()},
        ]
        self.assertEqual(
            cc.group_circuits(circuits)["non_essential"], ["C-A", "C-B"]
        )

    def test_duplicate_circuit_id_raises(self):
        circuits = _clean_inventory()["circuits"]
        circuits.append({"circuit_id": "HK-TEMP-07", "attributes": _attributes()})
        with self.assertRaises(ValueError):
            cc.group_circuits(circuits)

    def test_mapping_instead_of_a_list_raises(self):
        with self.assertRaises(ValueError):
            cc.group_circuits({"circuit_id": "C-1"})


class GroupingOrderTest(unittest.TestCase):
    def test_safety_group_is_presented_first(self):
        groups = cc.group_circuits(_clean_inventory()["circuits"])
        self.assertEqual(cc.grouping_presentation_order(groups)[0], "safety_critical")

    def test_empty_rungs_are_dropped_from_the_presentation(self):
        circuits = [{"circuit_id": "C-A", "attributes": _attributes()}]
        groups = cc.group_circuits(circuits)
        self.assertEqual(cc.grouping_presentation_order(groups), ("non_essential",))

    def test_presentation_order_follows_the_ladder(self):
        groups = cc.group_circuits(_clean_inventory()["circuits"])
        order = cc.grouping_presentation_order(groups)
        ranks = [cc.criticality_rank(name) for name in order]
        self.assertEqual(ranks, sorted(ranks))

    def test_off_ladder_group_name_raises(self):
        with self.assertRaises(ValueError):
            cc.grouping_presentation_order({"quite_important": ["C-1"]})

    def test_non_mapping_groups_raises(self):
        with self.assertRaises(ValueError):
            cc.grouping_presentation_order(["safety_critical"])


class ReviewInventoryTest(unittest.TestCase):
    def test_clean_inventory_is_compliant(self):
        review = cc.review_circuit_inventory(_clean_inventory())
        self.assertTrue(review["compliant"])
        self.assertEqual(review["margin_findings"], [])

    def test_a_heater_switch_on_the_exact_limit_is_not_a_finding(self):
        review = cc.review_circuit_inventory(_clean_inventory())
        self.assertNotIn(
            "HTR-SW-01", " ".join(review["margin_findings"])
        )

    def test_non_essential_circuit_needs_no_demonstrated_evidence(self):
        review = cc.review_circuit_inventory(_clean_inventory())
        self.assertEqual(review["evidence_findings"], [])

    def test_coupling_raises_the_effective_category(self):
        inventory = _clean_inventory()
        inventory["circuits"][3]["coupled_victim_ids"] = ["PYRO-ARM-01"]
        review = cc.review_circuit_inventory(inventory)
        self.assertEqual(review["own_categories"]["HK-TEMP-07"], "non_essential")
        self.assertEqual(review["effective_categories"]["HK-TEMP-07"], "safety_critical")

    def test_a_raised_circuit_without_evidence_is_reported(self):
        inventory = _clean_inventory()
        inventory["circuits"][3]["coupled_victim_ids"] = ["PYRO-ARM-01"]
        review = cc.review_circuit_inventory(inventory)
        self.assertEqual(len(review["evidence_findings"]), 1)
        self.assertFalse(review["compliant"])

    def test_unknown_victim_is_a_coupling_finding(self):
        inventory = _clean_inventory()
        inventory["circuits"][1]["coupled_victim_ids"] = ["C-GHOST"]
        review = cc.review_circuit_inventory(inventory)
        self.assertEqual(len(review["coupling_findings"]), 1)
        self.assertFalse(review["compliant"])

    def test_margin_shortfall_is_reported_against_the_effective_category(self):
        inventory = _clean_inventory()
        inventory["circuits"][2]["demonstrated"]["emission_level_dbuv"] = 30.0
        review = cc.review_circuit_inventory(inventory)
        self.assertEqual(len(review["margin_findings"]), 1)
        self.assertIn("HTR-SW-01", review["margin_findings"][0])

    def test_raising_a_circuit_can_turn_a_passing_margin_into_a_finding(self):
        inventory = _clean_inventory()
        inventory["circuits"][2]["coupled_victim_ids"] = ["PYRO-ARM-01"]
        review = cc.review_circuit_inventory(inventory)
        self.assertEqual(review["effective_categories"]["HTR-SW-01"], "safety_critical")
        self.assertEqual(len(review["margin_findings"]), 1)

    def test_demonstrated_mapping_missing_a_level_raises(self):
        inventory = _clean_inventory()
        del inventory["circuits"][0]["demonstrated"]["emission_level_dbuv"]
        with self.assertRaises(ValueError):
            cc.review_circuit_inventory(inventory)

    def test_non_mapping_inventory_raises(self):
        with self.assertRaises(ValueError):
            cc.review_circuit_inventory(["circuits"])

    def test_review_is_deterministic_across_repeated_calls(self):
        self.assertEqual(
            cc.review_circuit_inventory(_clean_inventory()),
            cc.review_circuit_inventory(_clean_inventory()),
        )


if __name__ == "__main__":
    unittest.main()
