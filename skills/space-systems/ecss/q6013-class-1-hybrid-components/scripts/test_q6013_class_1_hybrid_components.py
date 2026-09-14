"""Contract tests for the clause 4.6.3 class 1 hybrid procurement chain.

Every workflow step the SKILL.md sets out is exercised here, together with the
stop conditions the gate 3 contract reviews: no generic specification, a detail
specification citing the wrong parent, an element with no specification of its
own, and an element bought at a class weaker than the hybrid claims.
"""

import unittest

from q6013_class_1_hybrid_components_logic import (
    CHAIN_COMPLETE,
    DETAIL_SPECIFICATION_NOT_DERIVED,
    ELEMENT_CLASS_SHORTFALL,
    ELEMENT_KINDS,
    ELEMENT_SPECIFICATION_MISSING,
    GENERIC_SPECIFICATION_MISSING,
    PROCUREMENT_CLASSES,
    assess_hybrid_procurement,
    class_rank,
    compliant_element_share,
    detail_specification_is_derived,
    effective_hybrid_class,
    element_shortfalls,
    validate_element,
    validate_elements,
    validate_specification,
    weaker_class,
    weakest_element_class,
)

GENERIC_ID = "GS-HYB-4410"


def _generic(**overrides):
    spec = {"id": GENERIC_ID, "issue": "issue-6"}
    spec.update(overrides)
    return spec


def _detail(**overrides):
    spec = {
        "id": "DS-HYB-4410-07",
        "issue": "issue-2",
        "parent_generic_specification": GENERIC_ID,
    }
    spec.update(overrides)
    return spec


def _element(identifier, kind="die", procurement_class="class-1", spec="SCD-9001"):
    return {
        "id": identifier,
        "kind": kind,
        "procurement_class": procurement_class,
        "specification": spec,
    }


def _elements():
    return [
        _element("el-01", kind="die"),
        _element("el-02", kind="chip-resistor", spec="SCD-9002"),
        _element("el-03", kind="chip-capacitor", spec="SCD-9003"),
        _element("el-04", kind="substrate", spec="SCD-9004"),
    ]


def _case(**overrides):
    case = {
        "hybrid_class": "class-1",
        "generic_specification": _generic(),
        "detail_specification": _detail(),
        "elements": _elements(),
        "custom_type": True,
    }
    case.update(overrides)
    return case


class ClassRankTests(unittest.TestCase):
    def test_every_declared_class_ranks(self):
        self.assertEqual(
            [class_rank(name) for name in PROCUREMENT_CLASSES], [1, 2, 3]
        )

    def test_unknown_class_rejected(self):
        with self.assertRaises(ValueError):
            class_rank("class-9")

    def test_blank_class_rejected(self):
        with self.assertRaises(ValueError):
            class_rank("  ")

    def test_weaker_class_picks_the_higher_rank(self):
        self.assertEqual(weaker_class("class-1", "class-3"), "class-3")

    def test_weaker_class_of_equals_is_that_class(self):
        self.assertEqual(weaker_class("class-2", "class-2"), "class-2")


class SpecificationTests(unittest.TestCase):
    def test_specification_without_id_reads_as_absent(self):
        self.assertIsNone(validate_specification({"issue": "issue-1"}, "generic", False))

    def test_absent_required_specification_rejected(self):
        with self.assertRaises(ValueError):
            validate_specification(None, "generic_specification", required=True)

    def test_non_mapping_specification_rejected(self):
        with self.assertRaises(ValueError):
            validate_specification("GS-HYB-4410", "generic", False)

    def test_detail_citing_the_generic_is_derived(self):
        self.assertTrue(detail_specification_is_derived(_detail(), _generic()))

    def test_detail_citing_another_generic_is_not_derived(self):
        self.assertFalse(
            detail_specification_is_derived(
                _detail(parent_generic_specification="GS-HYB-0001"), _generic()
            )
        )

    def test_detail_with_no_parent_is_not_derived(self):
        detail = _detail()
        del detail["parent_generic_specification"]
        self.assertFalse(detail_specification_is_derived(detail, _generic()))

    def test_generic_without_id_rejected_by_the_derivation_check(self):
        with self.assertRaises(ValueError):
            detail_specification_is_derived(_detail(), {"issue": "issue-6"})


class ElementTests(unittest.TestCase):
    def test_every_declared_kind_validates(self):
        for kind in ELEMENT_KINDS:
            record = validate_element(_element("el-x", kind=kind))
            self.assertEqual(record["kind"], kind)

    def test_unknown_element_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_element(_element("el-01", kind="wire-bond-loop"))

    def test_element_without_id_rejected(self):
        element = _element("el-01")
        del element["id"]
        with self.assertRaises(ValueError):
            validate_element(element)

    def test_duplicate_element_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_elements([_element("el-01"), _element("el-01")])

    def test_empty_element_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_elements([])

    def test_element_without_specification_reads_as_unspecified(self):
        record = validate_element(_element("el-01", spec=""))
        self.assertIsNone(record["specification"])


class RollupTests(unittest.TestCase):
    def test_uniform_elements_show_no_shortfall(self):
        records = validate_elements(_elements())
        self.assertEqual(element_shortfalls(records, "class-1"), [])

    def test_a_weaker_element_is_a_shortfall(self):
        elements = _elements()
        elements[2]["procurement_class"] = "class-3"
        records = validate_elements(elements)
        self.assertEqual([r["id"] for r in element_shortfalls(records, "class-1")], ["el-03"])

    def test_weakest_element_class_is_the_poorest_present(self):
        elements = _elements()
        elements[1]["procurement_class"] = "class-2"
        records = validate_elements(elements)
        self.assertEqual(weakest_element_class(records), "class-2")

    def test_effective_class_follows_the_poorest_element(self):
        elements = _elements()
        elements[3]["procurement_class"] = "class-3"
        records = validate_elements(elements)
        self.assertEqual(effective_hybrid_class("class-1", records), "class-3")

    def test_effective_class_never_improves_on_the_declaration(self):
        records = validate_elements(_elements())
        self.assertEqual(effective_hybrid_class("class-2", records), "class-2")

    def test_compliant_share_of_a_uniform_set_is_one(self):
        records = validate_elements(_elements())
        self.assertAlmostEqual(compliant_element_share(records, "class-1"), 1.0, places=9)

    def test_compliant_share_falls_with_a_weaker_element(self):
        elements = _elements()
        elements[0]["procurement_class"] = "class-2"
        records = validate_elements(elements)
        self.assertAlmostEqual(compliant_element_share(records, "class-1"), 0.75, places=9)


class AssessmentTests(unittest.TestCase):
    def test_complete_chain_passes(self):
        result = assess_hybrid_procurement(_case())
        self.assertEqual(result["verdict"], CHAIN_COMPLETE)
        self.assertTrue(result["chain_complete"])
        self.assertEqual(result["findings"], [])

    def test_absent_generic_outranks_every_other_finding(self):
        elements = _elements()
        elements[0]["procurement_class"] = "class-3"
        result = assess_hybrid_procurement(
            _case(generic_specification=None, elements=elements)
        )
        self.assertEqual(result["verdict"], GENERIC_SPECIFICATION_MISSING)

    def test_element_without_specification_stops_the_chain(self):
        elements = _elements()
        elements[1]["specification"] = ""
        result = assess_hybrid_procurement(_case(elements=elements))
        self.assertEqual(result["verdict"], ELEMENT_SPECIFICATION_MISSING)
        self.assertEqual(result["elements_without_specification"], ["el-02"])

    def test_custom_hybrid_without_a_detail_specification_fails(self):
        result = assess_hybrid_procurement(_case(detail_specification=None))
        self.assertEqual(result["verdict"], DETAIL_SPECIFICATION_NOT_DERIVED)

    def test_catalogue_hybrid_may_rest_on_the_generic_alone(self):
        result = assess_hybrid_procurement(
            _case(detail_specification=None, custom_type=False)
        )
        self.assertEqual(result["verdict"], CHAIN_COMPLETE)

    def test_detail_citing_the_wrong_parent_fails(self):
        result = assess_hybrid_procurement(
            _case(detail_specification=_detail(parent_generic_specification="GS-OTHER"))
        )
        self.assertEqual(result["verdict"], DETAIL_SPECIFICATION_NOT_DERIVED)
        self.assertFalse(result["detail_is_derived"])

    def test_weaker_element_gives_the_shortfall_verdict(self):
        elements = _elements()
        elements[2]["procurement_class"] = "class-2"
        result = assess_hybrid_procurement(_case(elements=elements))
        self.assertEqual(result["verdict"], ELEMENT_CLASS_SHORTFALL)
        self.assertEqual(result["effective_hybrid_class"], "class-2")

    def test_non_boolean_custom_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_hybrid_procurement(_case(custom_type="yes"))

    def test_missing_elements_key_rejected(self):
        case = _case()
        del case["elements"]
        with self.assertRaises(ValueError):
            assess_hybrid_procurement(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_hybrid_procurement(["hybrid_class"])


if __name__ == "__main__":
    unittest.main()
