#!/usr/bin/env python3
"""Contract test for the class 2 hybrid microcircuit purchase (offline)."""

import copy
import unittest

from q60_class_2_hybrid_procurement_logic import (
    CITED_ISSUE_SUPERSEDED,
    DEFAULT_ORDER_POLICY,
    ELEMENT_KINDS,
    ELEMENT_TIER_SHORT,
    GENERIC_FAMILY_MISMATCH,
    HYBRID_CONSTRUCTIONS,
    MINIMUM_ELEMENT_TIER,
    ORDER_LINE_TIER_SHORT,
    ORDER_SPECIFICATION_COMPLETE,
    SPECIFICATION_TIERS,
    SUPPLIER_QUALIFICATION_LAPSED,
    achievable_tier,
    assess_hybrid_order,
    bill_of_materials_tier,
    citation_findings,
    construction_profile,
    element_findings,
    element_tier_coverage,
    month_index,
    parse_month_code,
    supplier_qualification_status,
    tier_rank,
    validate_element,
    validate_elements,
    validate_order_line,
    validate_order_policy,
    worse_tier,
)

ORDER_LINE = {
    "part_number": "HYB-3300",
    "construction": "thick-film",
    "cited_generic_family": "hybrid-thick-film-generic",
    "cited_tier": "generic-plus-source-control-drawing",
    "cited_issue": 4,
    "current_issue": 4,
    "supplier": "SUP-NORTH",
    "order_month": "2026-05",
}

ELEMENTS = [
    {
        "element_id": "D1",
        "kind": "semiconductor-die",
        "specification_tier": "esa-detail-specification",
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
]

REGISTER = [
    {
        "supplier": "SUP-NORTH",
        "generic_family": "hybrid-thick-film-generic",
        "qualified_until_month": "2027-11",
    }
]


def _line(**overrides):
    line = copy.deepcopy(ORDER_LINE)
    line.update(overrides)
    return line


def _case(**overrides):
    case = {
        "order_line": _line(),
        "elements": copy.deepcopy(ELEMENTS),
        "qualification_register": copy.deepcopy(REGISTER),
    }
    case.update(overrides)
    return case


class TierLadderTests(unittest.TestCase):
    def test_detail_specification_is_the_strongest_tier(self):
        self.assertEqual(tier_rank("esa-detail-specification"), 1)

    def test_undocumented_is_the_weakest_tier(self):
        self.assertEqual(tier_rank("undocumented"), len(SPECIFICATION_TIERS))

    def test_unknown_tier_is_rejected(self):
        with self.assertRaises(ValueError):
            tier_rank("verbal-assurance")

    def test_worse_tier_picks_the_weaker_claim(self):
        self.assertEqual(
            worse_tier("esa-detail-specification", "undocumented"), "undocumented"
        )

    def test_worse_tier_of_equal_tiers_is_that_tier(self):
        self.assertEqual(
            worse_tier("manufacturer-referenced-specification",
                       "manufacturer-referenced-specification"),
            "manufacturer-referenced-specification",
        )

    def test_every_element_kind_has_a_tier_floor(self):
        for kind in ELEMENT_KINDS:
            self.assertIn(MINIMUM_ELEMENT_TIER[kind], SPECIFICATION_TIERS)


class ConstructionTests(unittest.TestCase):
    def test_every_construction_names_a_family_and_a_floor(self):
        for construction in HYBRID_CONSTRUCTIONS:
            profile = construction_profile(construction)
            self.assertIn(profile["weakest_order_tier"], SPECIFICATION_TIERS)
            self.assertTrue(profile["generic_family"])

    def test_multichip_module_demands_a_detail_specification(self):
        self.assertEqual(
            construction_profile("multichip-module")["weakest_order_tier"],
            "esa-detail-specification",
        )

    def test_unknown_construction_is_rejected(self):
        with self.assertRaises(ValueError):
            construction_profile("printed-wiring-board")

    def test_profile_is_a_copy(self):
        profile = construction_profile("thick-film")
        profile["generic_family"] = "changed"
        self.assertEqual(
            HYBRID_CONSTRUCTIONS["thick-film"]["generic_family"],
            "hybrid-thick-film-generic",
        )


class MonthTests(unittest.TestCase):
    def test_month_code_splits_into_year_and_month(self):
        self.assertEqual(parse_month_code("2026-05"), (2026, 5))

    def test_month_thirteen_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_month_code("2026-13")

    def test_short_year_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_month_code("26-05")

    def test_month_index_orders_across_a_year_boundary(self):
        self.assertEqual(month_index("2027-01") - month_index("2026-12"), 1)

    def test_month_index_of_the_same_code_is_equal(self):
        self.assertEqual(month_index("2026-05"), month_index("2026-05"))


class PolicyTests(unittest.TestCase):
    def test_default_policy_is_returned_when_omitted(self):
        self.assertEqual(validate_order_policy(), DEFAULT_ORDER_POLICY)

    def test_unknown_policy_key_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_order_policy({"discount": 5})

    def test_negative_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_order_policy({"qualification_margin_months": -1})


class OrderLineTests(unittest.TestCase):
    def test_complete_line_validates(self):
        record = validate_order_line(ORDER_LINE)
        self.assertEqual(record["construction"], "thick-film")

    def test_issue_ahead_of_the_current_one_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_order_line(_line(cited_issue=6, current_issue=4))

    def test_zero_issue_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_order_line(_line(cited_issue=0))

    def test_blank_supplier_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_order_line(_line(supplier="  "))

    def test_wrong_family_is_a_citation_finding(self):
        findings = citation_findings(_line(cited_generic_family="hybrid-thin-film-generic"))
        self.assertEqual(findings[0]["finding"], GENERIC_FAMILY_MISMATCH)

    def test_superseded_issue_is_a_citation_finding(self):
        findings = citation_findings(_line(cited_issue=2, current_issue=5))
        self.assertTrue(
            any(item["finding"] == CITED_ISSUE_SUPERSEDED for item in findings)
        )

    def test_weak_order_tier_is_a_citation_finding(self):
        findings = citation_findings(
            _line(cited_tier="manufacturer-unreferenced-specification")
        )
        self.assertTrue(
            any(item["finding"] == ORDER_LINE_TIER_SHORT for item in findings)
        )

    def test_clean_line_raises_no_citation_finding(self):
        self.assertEqual(citation_findings(ORDER_LINE), ())


class ElementTests(unittest.TestCase):
    def test_unknown_element_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_element(
                {"element_id": "X1", "kind": "connector", "specification_tier": "undocumented"}
            )

    def test_empty_bill_of_materials_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_elements([])

    def test_duplicate_element_id_is_rejected(self):
        elements = copy.deepcopy(ELEMENTS)
        elements[1]["element_id"] = elements[0]["element_id"]
        with self.assertRaises(ValueError):
            validate_elements(elements)

    def test_die_on_a_maker_specification_is_short(self):
        findings = element_findings(
            {
                "element_id": "D9",
                "kind": "semiconductor-die",
                "specification_tier": "manufacturer-referenced-specification",
            }
        )
        self.assertEqual(findings[0]["finding"], ELEMENT_TIER_SHORT)

    def test_capacitor_on_a_referenced_maker_specification_is_accepted(self):
        self.assertEqual(
            element_findings(
                {
                    "element_id": "C9",
                    "kind": "chip-capacitor",
                    "specification_tier": "manufacturer-referenced-specification",
                }
            ),
            (),
        )

    def test_unreferenced_maker_specification_is_short_for_a_passive(self):
        findings = element_findings(
            {
                "element_id": "C8",
                "kind": "chip-capacitor",
                "specification_tier": "manufacturer-unreferenced-specification",
            }
        )
        self.assertEqual(findings[0]["required_tier"], "manufacturer-referenced-specification")

    def test_bill_of_materials_tier_is_the_weakest_element(self):
        elements = copy.deepcopy(ELEMENTS)
        elements[2]["specification_tier"] = "undocumented"
        bom = bill_of_materials_tier(elements)
        self.assertEqual(bom["governing_tier"], "undocumented")
        self.assertEqual(bom["governing_element_id"], "R1")

    def test_coverage_is_one_when_every_element_meets_its_floor(self):
        self.assertAlmostEqual(element_tier_coverage(ELEMENTS), 1.0, places=9)

    def test_coverage_is_the_plain_share_of_compliant_elements(self):
        elements = copy.deepcopy(ELEMENTS)
        elements[0]["specification_tier"] = "undocumented"
        self.assertAlmostEqual(element_tier_coverage(elements), 0.75, places=9)


class SupplierTests(unittest.TestCase):
    def test_listed_supplier_inside_the_window_is_qualified(self):
        status = supplier_qualification_status(
            REGISTER, "SUP-NORTH", "hybrid-thick-film-generic", "2026-05"
        )
        self.assertTrue(status["qualified"])
        self.assertEqual(status["months_remaining"], 18)

    def test_supplier_absent_from_the_register_is_not_qualified(self):
        status = supplier_qualification_status(
            REGISTER, "SUP-SOUTH", "hybrid-thick-film-generic", "2026-05"
        )
        self.assertFalse(status["listed"])
        self.assertFalse(status["qualified"])

    def test_qualification_for_another_family_does_not_carry(self):
        status = supplier_qualification_status(
            REGISTER, "SUP-NORTH", "hybrid-thin-film-generic", "2026-05"
        )
        self.assertFalse(status["listed"])

    def test_order_in_the_closing_month_is_still_qualified(self):
        status = supplier_qualification_status(
            REGISTER, "SUP-NORTH", "hybrid-thick-film-generic", "2027-11"
        )
        self.assertTrue(status["qualified"])
        self.assertEqual(status["months_remaining"], 0)

    def test_order_after_the_window_is_not_qualified(self):
        status = supplier_qualification_status(
            REGISTER, "SUP-NORTH", "hybrid-thick-film-generic", "2027-12"
        )
        self.assertFalse(status["qualified"])

    def test_closing_soon_is_inside_the_margin(self):
        status = supplier_qualification_status(
            REGISTER, "SUP-NORTH", "hybrid-thick-film-generic", "2027-10"
        )
        self.assertTrue(status["inside_margin"])

    def test_register_entry_missing_a_key_is_rejected(self):
        with self.assertRaises(ValueError):
            supplier_qualification_status(
                [{"supplier": "SUP-NORTH"}],
                "SUP-NORTH",
                "hybrid-thick-film-generic",
                "2026-05",
            )


class AssessmentTests(unittest.TestCase):
    def test_clean_order_is_complete(self):
        result = assess_hybrid_order(_case())
        self.assertEqual(result["verdict"], ORDER_SPECIFICATION_COMPLETE)
        self.assertTrue(result["orderable"])
        self.assertEqual(result["findings"], [])

    def test_achievable_tier_follows_the_weakest_element(self):
        elements = copy.deepcopy(ELEMENTS)
        elements[3]["specification_tier"] = "manufacturer-unreferenced-specification"
        result = assess_hybrid_order(_case(elements=elements))
        self.assertEqual(
            result["achievable_tier"], "manufacturer-unreferenced-specification"
        )
        self.assertEqual(result["governing_element_id"], "S1")

    def test_family_mismatch_outranks_an_element_gap(self):
        elements = copy.deepcopy(ELEMENTS)
        elements[0]["specification_tier"] = "undocumented"
        result = assess_hybrid_order(
            _case(
                order_line=_line(cited_generic_family="hybrid-microwave-generic"),
                elements=elements,
            )
        )
        self.assertEqual(result["verdict"], GENERIC_FAMILY_MISMATCH)

    def test_unqualified_supplier_stops_the_order(self):
        result = assess_hybrid_order(
            _case(order_line=_line(supplier="SUP-WEST"))
        )
        self.assertEqual(result["verdict"], SUPPLIER_QUALIFICATION_LAPSED)
        self.assertFalse(result["orderable"])

    def test_element_gap_is_reported_with_its_element(self):
        elements = copy.deepcopy(ELEMENTS)
        elements[1]["specification_tier"] = "undocumented"
        result = assess_hybrid_order(_case(elements=elements))
        self.assertEqual(result["verdict"], ELEMENT_TIER_SHORT)
        self.assertEqual(result["findings"][0]["element_id"], "C1")

    def test_multichip_module_rejects_a_generic_plus_drawing_order(self):
        result = assess_hybrid_order(
            _case(
                order_line=_line(
                    construction="multichip-module",
                    cited_generic_family="hybrid-multichip-module-generic",
                ),
                qualification_register=[
                    {
                        "supplier": "SUP-NORTH",
                        "generic_family": "hybrid-multichip-module-generic",
                        "qualified_until_month": "2027-11",
                    }
                ],
            )
        )
        self.assertEqual(result["verdict"], ORDER_LINE_TIER_SHORT)

    def test_achievable_tier_never_beats_the_order_line(self):
        result = assess_hybrid_order(_case())
        self.assertGreaterEqual(
            tier_rank(result["achievable_tier"]), tier_rank(result["cited_tier"])
        )
        self.assertEqual(
            achievable_tier(result["cited_tier"], result["bill_of_materials_tier"]),
            result["achievable_tier"],
        )

    def test_case_missing_a_key_is_rejected(self):
        case = _case()
        del case["elements"]
        with self.assertRaises(ValueError):
            assess_hybrid_order(case)

    def test_case_of_wrong_type_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_hybrid_order("HYB-3300")


if __name__ == "__main__":
    unittest.main(verbosity=0)
