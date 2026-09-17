#!/usr/bin/env python3
"""Contract test for the class 3 hybrid microcircuit purchase (offline)."""

import copy
import unittest

from q60_class_3_hybrid_procurement_logic import (
    ACCEPTANCE_BURDEN_ABOVE_CAP,
    ACTIVE_ELEMENT_KINDS,
    ACTIVE_SHORTFALL_STEPS,
    COMPENSATION_STEPS_BY_DEPTH,
    DEFAULT_PURCHASE_POLICY,
    ELEMENT_KINDS,
    ELEMENT_TIER_UNBOUNDED,
    GENERIC_FAMILY_MISMATCH,
    HYBRID_CONSTRUCTIONS,
    NOMINAL_ELEMENT_TIER,
    PURCHASE_AS_SPECIFIED,
    PURCHASE_WITH_COMPENSATING_ACCEPTANCE,
    SPECIFICATION_TIERS,
    STEP_EFFORT,
    SUPPLIER_NOT_ASSESSED,
    UNBOUNDED_TIER,
    acceptance_effort,
    acceptance_plan,
    assess_hybrid_purchase,
    burden_ratio,
    compensation_steps,
    construction_profile,
    element_compensation,
    order_line_compensation,
    shortfall_depth,
    supplier_assessment,
    tier_rank,
    unbounded_elements,
    validate_element,
    validate_elements,
    validate_order_line,
    validate_purchase_policy,
)

ORDER_LINE = {
    "part_number": "HYB-C3-820",
    "construction": "thick-film",
    "cited_generic_family": "hybrid-thick-film-generic",
    "cited_tier": "manufacturer-referenced-specification",
    "supplier": "SUP-NORTH",
    "quantity": 12,
}

ELEMENTS = [
    {
        "element_id": "D1",
        "kind": "semiconductor-die",
        "specification_tier": "generic-plus-source-control-drawing",
    },
    {
        "element_id": "C1",
        "kind": "chip-capacitor",
        "specification_tier": "manufacturer-referenced-specification",
    },
    {
        "element_id": "R1",
        "kind": "chip-resistor",
        "specification_tier": "manufacturer-referenced-specification",
    },
    {
        "element_id": "S1",
        "kind": "substrate",
        "specification_tier": "manufacturer-referenced-specification",
    },
    {
        "element_id": "W1",
        "kind": "interconnect-wire",
        "specification_tier": "manufacturer-unreferenced-specification",
    },
]

REGISTER = [
    {"supplier": "SUP-NORTH", "generic_family": "hybrid-thick-film-generic"},
]

AUDITS = [
    {"supplier": "SUP-EAST", "audit_reference": "AUD-77", "age_months": 12},
]


def _line(**overrides):
    line = copy.deepcopy(ORDER_LINE)
    line.update(overrides)
    return line


def _elements(index=None, **overrides):
    elements = copy.deepcopy(ELEMENTS)
    if index is not None:
        elements[index].update(overrides)
    return elements


def _case(**overrides):
    case = {
        "order_line": _line(),
        "elements": _elements(),
        "qualification_register": copy.deepcopy(REGISTER),
        "supplier_audits": copy.deepcopy(AUDITS),
    }
    case.update(overrides)
    return case


class LadderTests(unittest.TestCase):
    def test_detail_specification_is_the_strongest_tier(self):
        self.assertEqual(tier_rank("esa-detail-specification"), 1)

    def test_undocumented_is_the_weakest_tier(self):
        self.assertEqual(tier_rank(UNBOUNDED_TIER), len(SPECIFICATION_TIERS))

    def test_unknown_tier_is_rejected(self):
        with self.assertRaises(ValueError):
            tier_rank("handshake")

    def test_a_claim_at_its_nominal_tier_has_no_shortfall(self):
        self.assertEqual(
            shortfall_depth(
                "manufacturer-referenced-specification",
                "manufacturer-referenced-specification",
            ),
            0,
        )

    def test_a_claim_above_its_nominal_tier_has_no_shortfall(self):
        self.assertEqual(
            shortfall_depth(
                "esa-detail-specification", "manufacturer-referenced-specification"
            ),
            0,
        )

    def test_shortfall_counts_the_rungs_dropped(self):
        self.assertEqual(
            shortfall_depth("undocumented", "generic-plus-source-control-drawing"), 3
        )

    def test_every_element_kind_has_a_nominal_tier(self):
        for kind in ELEMENT_KINDS:
            self.assertIn(NOMINAL_ELEMENT_TIER[kind], SPECIFICATION_TIERS)


class ConstructionTests(unittest.TestCase):
    def test_every_construction_names_a_family_and_a_nominal_tier(self):
        for construction in HYBRID_CONSTRUCTIONS:
            profile = construction_profile(construction)
            self.assertIn(profile["nominal_order_tier"], SPECIFICATION_TIERS)
            self.assertTrue(profile["generic_family"])

    def test_a_multichip_module_sits_higher_than_a_thick_film_build(self):
        self.assertLess(
            tier_rank(construction_profile("multichip-module")["nominal_order_tier"]),
            tier_rank(construction_profile("thick-film")["nominal_order_tier"]),
        )

    def test_unknown_construction_is_rejected(self):
        with self.assertRaises(ValueError):
            construction_profile("wire-wrap-board")

    def test_profile_is_a_copy(self):
        profile = construction_profile("thin-film")
        profile["generic_family"] = "changed"
        self.assertEqual(
            HYBRID_CONSTRUCTIONS["thin-film"]["generic_family"],
            "hybrid-thin-film-generic",
        )


class PolicyTests(unittest.TestCase):
    def test_default_policy_is_returned_when_omitted(self):
        self.assertEqual(validate_purchase_policy(), DEFAULT_PURCHASE_POLICY)

    def test_unknown_policy_key_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_purchase_policy({"discount_percent": 5})

    def test_negative_cap_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_purchase_policy({"acceptance_effort_cap": -4})

    def test_a_zero_cap_admits_no_purchase(self):
        with self.assertRaises(ValueError):
            burden_ratio((), {"acceptance_effort_cap": 0})


class OrderLineTests(unittest.TestCase):
    def test_complete_line_validates(self):
        record = validate_order_line(ORDER_LINE)
        self.assertEqual(record["construction"], "thick-film")

    def test_zero_quantity_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_order_line(_line(quantity=0))

    def test_blank_supplier_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_order_line(_line(supplier="   "))

    def test_a_line_at_its_nominal_tier_needs_no_acceptance(self):
        entry = order_line_compensation(ORDER_LINE)
        self.assertEqual(entry["depth"], 0)
        self.assertEqual(entry["steps"], ())

    def test_a_line_one_rung_down_pulls_the_incoming_test(self):
        entry = order_line_compensation(
            _line(cited_tier="manufacturer-unreferenced-specification")
        )
        self.assertEqual(entry["depth"], 1)
        self.assertEqual(entry["steps"], ("incoming-electrical-test",))

    def test_an_undocumented_line_is_unbounded(self):
        entry = order_line_compensation(_line(cited_tier="undocumented"))
        self.assertTrue(entry["unbounded"])


class CompensationTests(unittest.TestCase):
    def test_no_shortfall_costs_nothing(self):
        self.assertEqual(compensation_steps(0), ())

    def test_negative_depth_is_rejected(self):
        with self.assertRaises(ValueError):
            compensation_steps(-1)

    def test_each_depth_carries_the_one_below_it(self):
        for depth in (2, 3):
            shallower = set(COMPENSATION_STEPS_BY_DEPTH[depth - 1])
            self.assertTrue(shallower.issubset(set(COMPENSATION_STEPS_BY_DEPTH[depth])))

    def test_a_depth_past_the_table_clamps_to_the_deepest_rung(self):
        self.assertEqual(compensation_steps(9), COMPENSATION_STEPS_BY_DEPTH[3])

    def test_every_step_carries_an_effort(self):
        for steps in COMPENSATION_STEPS_BY_DEPTH.values():
            for step in steps:
                self.assertIn(step, STEP_EFFORT)

    def test_an_active_die_shortfall_adds_the_radiation_step(self):
        entry = element_compensation(
            {
                "element_id": "D9",
                "kind": "semiconductor-die",
                "specification_tier": "manufacturer-unreferenced-specification",
            }
        )
        self.assertEqual(entry["depth"], 2)
        for step in ACTIVE_SHORTFALL_STEPS:
            self.assertIn(step, entry["steps"])

    def test_a_passive_shortfall_does_not_add_the_radiation_step(self):
        entry = element_compensation(
            {
                "element_id": "C9",
                "kind": "chip-capacitor",
                "specification_tier": "manufacturer-unreferenced-specification",
            }
        )
        for step in ACTIVE_SHORTFALL_STEPS:
            self.assertNotIn(step, entry["steps"])

    def test_an_active_element_at_its_nominal_tier_adds_nothing(self):
        entry = element_compensation(ELEMENTS[0])
        self.assertEqual(entry["steps"], ())
        self.assertIn(entry["kind"], ACTIVE_ELEMENT_KINDS)

    def test_unknown_element_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_element(
                {"element_id": "X1", "kind": "relay", "specification_tier": "undocumented"}
            )

    def test_empty_bill_of_materials_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_elements([])

    def test_duplicate_element_id_is_rejected(self):
        elements = _elements()
        elements[1]["element_id"] = elements[0]["element_id"]
        with self.assertRaises(ValueError):
            validate_elements(elements)


class PlanTests(unittest.TestCase):
    def test_a_fully_specified_purchase_needs_no_acceptance_plan(self):
        self.assertEqual(acceptance_plan(ORDER_LINE, ELEMENTS), ())

    def test_the_plan_is_the_union_across_the_bill_of_materials(self):
        elements = _elements(1, specification_tier="manufacturer-unreferenced-specification")
        elements[0]["specification_tier"] = "manufacturer-unreferenced-specification"
        plan = acceptance_plan(ORDER_LINE, elements)
        self.assertIn("incoming-electrical-test", plan)
        self.assertIn("radiation-lot-verification", plan)

    def test_the_plan_never_repeats_a_step(self):
        elements = _elements(1, specification_tier="manufacturer-unreferenced-specification")
        elements[2]["specification_tier"] = "manufacturer-unreferenced-specification"
        plan = acceptance_plan(ORDER_LINE, elements)
        self.assertEqual(len(plan), len(set(plan)))

    def test_effort_is_the_sum_of_the_step_costs(self):
        plan = ("incoming-electrical-test", "constructional-analysis")
        self.assertEqual(acceptance_effort(plan), STEP_EFFORT["incoming-electrical-test"]
                         + STEP_EFFORT["constructional-analysis"])

    def test_an_unknown_step_is_rejected(self):
        with self.assertRaises(ValueError):
            acceptance_effort(("sniff-test",))

    def test_effort_of_an_empty_plan_is_zero(self):
        self.assertEqual(acceptance_effort(()), 0)

    def test_burden_ratio_is_effort_over_the_cap(self):
        plan = ("incoming-electrical-test", "constructional-analysis")
        expected = acceptance_effort(plan) / DEFAULT_PURCHASE_POLICY[
            "acceptance_effort_cap"
        ]
        self.assertAlmostEqual(burden_ratio(plan), expected, places=9)

    def test_burden_ratio_of_an_empty_plan_is_zero(self):
        self.assertAlmostEqual(burden_ratio(()), 0.0, places=9)


class SupplierTests(unittest.TestCase):
    def test_a_registered_supplier_is_assessed(self):
        status = supplier_assessment(
            REGISTER, AUDITS, "SUP-NORTH", "hybrid-thick-film-generic"
        )
        self.assertEqual(status["route"], "registered")
        self.assertTrue(status["assessed"])

    def test_a_register_entry_for_another_family_does_not_carry(self):
        status = supplier_assessment(
            REGISTER, AUDITS, "SUP-NORTH", "hybrid-microwave-generic"
        )
        self.assertEqual(status["route"], "unknown")

    def test_a_recent_audit_stands_in_for_a_register_entry(self):
        status = supplier_assessment(
            REGISTER, AUDITS, "SUP-EAST", "hybrid-thick-film-generic"
        )
        self.assertEqual(status["route"], "audited")
        self.assertTrue(status["assessed"])

    def test_an_audit_exactly_at_its_validity_still_stands(self):
        audits = [
            {
                "supplier": "SUP-EAST",
                "audit_reference": "AUD-78",
                "age_months": DEFAULT_PURCHASE_POLICY["audit_validity_months"],
            }
        ]
        status = supplier_assessment(
            REGISTER, audits, "SUP-EAST", "hybrid-thick-film-generic"
        )
        self.assertTrue(status["assessed"])

    def test_a_stale_audit_does_not_stand(self):
        audits = [
            {"supplier": "SUP-EAST", "audit_reference": "AUD-79", "age_months": 40}
        ]
        status = supplier_assessment(
            REGISTER, audits, "SUP-EAST", "hybrid-thick-film-generic"
        )
        self.assertFalse(status["assessed"])

    def test_an_unlisted_supplier_is_not_assessed(self):
        status = supplier_assessment(
            REGISTER, AUDITS, "SUP-WEST", "hybrid-thick-film-generic"
        )
        self.assertFalse(status["assessed"])

    def test_a_blank_audit_reference_is_rejected(self):
        audits = [{"supplier": "SUP-EAST", "audit_reference": "  ", "age_months": 3}]
        with self.assertRaises(ValueError):
            supplier_assessment(
                REGISTER, audits, "SUP-EAST", "hybrid-thick-film-generic"
            )

    def test_an_audit_entry_missing_a_key_is_rejected(self):
        with self.assertRaises(ValueError):
            supplier_assessment(
                REGISTER,
                [{"supplier": "SUP-EAST"}],
                "SUP-EAST",
                "hybrid-thick-film-generic",
            )


class AssessmentTests(unittest.TestCase):
    def test_a_fully_specified_purchase_needs_no_compensation(self):
        result = assess_hybrid_purchase(_case())
        self.assertEqual(result["verdict"], PURCHASE_AS_SPECIFIED)
        self.assertEqual(result["acceptance_plan"], ())
        self.assertTrue(result["purchasable"])

    def test_a_shortfall_turns_the_purchase_into_a_compensated_one(self):
        result = assess_hybrid_purchase(
            _case(
                elements=_elements(
                    1, specification_tier="manufacturer-unreferenced-specification"
                )
            )
        )
        self.assertEqual(result["verdict"], PURCHASE_WITH_COMPENSATING_ACCEPTANCE)
        self.assertEqual(result["deepest_shortfall"], 1)
        self.assertTrue(result["purchasable"])

    def test_an_undocumented_element_cannot_be_bought_back(self):
        result = assess_hybrid_purchase(
            _case(elements=_elements(2, specification_tier="undocumented"))
        )
        self.assertEqual(result["verdict"], ELEMENT_TIER_UNBOUNDED)
        self.assertFalse(result["purchasable"])
        self.assertEqual(result["unbounded_elements"], ("R1",))

    def test_an_unbounded_element_outranks_a_family_mismatch(self):
        result = assess_hybrid_purchase(
            _case(
                order_line=_line(cited_generic_family="hybrid-thin-film-generic"),
                elements=_elements(2, specification_tier="undocumented"),
            )
        )
        self.assertEqual(result["verdict"], ELEMENT_TIER_UNBOUNDED)

    def test_a_wrong_family_stops_an_otherwise_clean_order(self):
        result = assess_hybrid_purchase(
            _case(order_line=_line(cited_generic_family="hybrid-microwave-generic"))
        )
        self.assertEqual(result["verdict"], GENERIC_FAMILY_MISMATCH)

    def test_an_unassessed_supplier_stops_the_order(self):
        result = assess_hybrid_purchase(_case(order_line=_line(supplier="SUP-WEST")))
        self.assertEqual(result["verdict"], SUPPLIER_NOT_ASSESSED)
        self.assertFalse(result["purchasable"])

    def test_an_audited_supplier_is_accepted_at_class_3(self):
        result = assess_hybrid_purchase(_case(order_line=_line(supplier="SUP-EAST")))
        self.assertEqual(result["verdict"], PURCHASE_AS_SPECIFIED)
        self.assertEqual(result["supplier_status"]["route"], "audited")

    def test_an_acceptance_plan_over_the_cap_stops_the_order(self):
        result = assess_hybrid_purchase(
            _case(
                elements=_elements(
                    0, specification_tier="manufacturer-unreferenced-specification"
                )
            ),
            {"acceptance_effort_cap": 10},
        )
        self.assertEqual(result["verdict"], ACCEPTANCE_BURDEN_ABOVE_CAP)
        self.assertGreater(result["acceptance_effort"], 10)

    def test_the_same_plan_is_purchasable_under_the_default_cap(self):
        result = assess_hybrid_purchase(
            _case(
                elements=_elements(
                    0, specification_tier="manufacturer-unreferenced-specification"
                )
            )
        )
        self.assertEqual(result["verdict"], PURCHASE_WITH_COMPENSATING_ACCEPTANCE)
        self.assertIn("radiation-lot-verification", result["acceptance_plan"])

    def test_the_reported_burden_ratio_matches_the_plan(self):
        result = assess_hybrid_purchase(
            _case(
                elements=_elements(
                    0, specification_tier="manufacturer-unreferenced-specification"
                )
            )
        )
        self.assertAlmostEqual(
            result["burden_ratio"],
            acceptance_effort(result["acceptance_plan"])
            / DEFAULT_PURCHASE_POLICY["acceptance_effort_cap"],
            places=9,
        )

    def test_case_missing_a_key_is_rejected(self):
        case = _case()
        del case["supplier_audits"]
        with self.assertRaises(ValueError):
            assess_hybrid_purchase(case)

    def test_case_of_wrong_type_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_hybrid_purchase("HYB-C3-820")

    def test_unbounded_elements_lists_only_the_undocumented_ones(self):
        elements = _elements(3, specification_tier="undocumented")
        self.assertEqual(unbounded_elements(elements), ("S1",))


if __name__ == "__main__":
    unittest.main(verbosity=0)
