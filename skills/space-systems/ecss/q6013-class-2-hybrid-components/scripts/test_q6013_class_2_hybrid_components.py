"""Contract tests for the clause 5.6.3 class 2 hybrid procurement grading.

Every workflow step the SKILL.md sets out is exercised here, together with the
stop conditions the gate 3 contract reviews: a hybrid with no procurement
specification, an element with no specification of its own, an element one
class short with and without upscreening evidence, an element two classes
short, and an upscreened share sitting exactly on its cap.
"""

import unittest

from q6013_class_2_hybrid_components_logic import (
    ADMISSIBLE_UNAIDED,
    DEFAULT_HYBRID_POLICY,
    DEFAULT_TARGET_CLASS,
    ELEMENT_KINDS,
    ELEMENT_REFUSED,
    HYBRID_ADMISSIBLE,
    HYBRID_ADMISSIBLE_AFTER_UPSCREENING,
    HYBRID_REFUSED,
    PROCUREMENT_CLASSES,
    PROCUREMENT_SPECIFICATION_MISSING,
    RECOVERABLE_BY_UPSCREENING,
    assess_hybrid_procurement,
    class_rank,
    effective_hybrid_class,
    element_disposition,
    share_within_cap,
    upscreening_declared,
    validate_element,
    validate_elements,
    validate_hybrid_policy,
)

_UPSCREENING = {"specification": "upscreen-spec-11", "lot_traceability": True}


def _element(kind, procurement_class="class-2", reference=None, upscreening=None):
    record = {
        "kind": kind,
        "procurement_class": procurement_class,
        "specification_reference": reference or ("detail-spec-%s" % kind),
    }
    if upscreening is not None:
        record["upscreening"] = upscreening
    return record


def _four(*procurement_classes, **kwargs):
    upscreen_kinds = kwargs.get("upscreen_kinds", ())
    kinds = ("die", "chip-resistor", "substrate", "package")
    out = []
    for kind, procurement_class in zip(kinds, procurement_classes):
        out.append(
            _element(
                kind,
                procurement_class,
                upscreening=dict(_UPSCREENING) if kind in upscreen_kinds else None,
            )
        )
    return out


def _case(**overrides):
    case = {
        "hybrid": {"procurement_specification": "hybrid-proc-spec-4"},
        "elements": _four("class-2", "class-2", "class-2", "class-2"),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        settings = validate_hybrid_policy(None)
        self.assertAlmostEqual(settings["max_upscreened_share"], 0.5, places=9)
        self.assertEqual(settings["max_recoverable_shortfall"], 1)

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_hybrid_policy({"max_upscreen": 0.5})

    def test_share_cap_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_hybrid_policy({"max_upscreened_share": 1.2})

    def test_negative_recoverable_shortfall_rejected(self):
        with self.assertRaises(ValueError):
            validate_hybrid_policy({"max_recoverable_shortfall": -1})


class ClassRankTests(unittest.TestCase):
    def test_ranks_descend_with_assurance(self):
        ranks = [class_rank(name) for name in PROCUREMENT_CLASSES]
        self.assertEqual(ranks, sorted(ranks))

    def test_class_one_outranks_class_two(self):
        self.assertLess(class_rank("class-1"), class_rank("class-2"))

    def test_unknown_procurement_class_rejected(self):
        with self.assertRaises(ValueError):
            class_rank("class-9")

    def test_blank_procurement_class_rejected(self):
        with self.assertRaises(ValueError):
            class_rank("  ")


class ElementRecordTests(unittest.TestCase):
    def test_every_declared_kind_validates(self):
        for kind in ELEMENT_KINDS:
            self.assertEqual(validate_element(_element(kind), "element")["kind"], kind)

    def test_unknown_element_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_element(_element("heat-spreader"), "element")

    def test_element_without_specification_reference_rejected(self):
        record = _element("die")
        record["specification_reference"] = ""
        with self.assertRaises(ValueError):
            validate_element(record, "element")

    def test_element_with_non_mapping_upscreening_rejected(self):
        record = _element("die", "class-3", upscreening=["upscreen-spec-11"])
        with self.assertRaises(ValueError):
            validate_element(record, "element")

    def test_empty_element_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_elements([])

    def test_repeated_element_against_one_specification_rejected(self):
        with self.assertRaises(ValueError):
            validate_elements([_element("die"), _element("die")])


class UpscreeningTests(unittest.TestCase):
    def test_declared_upscreening_with_traceability_counts(self):
        self.assertTrue(upscreening_declared(_element("die", "class-3", upscreening=dict(_UPSCREENING))))

    def test_upscreening_without_traceability_does_not_count(self):
        record = _element(
            "die", "class-3", upscreening={"specification": "upscreen-spec-11"}
        )
        self.assertFalse(upscreening_declared(record))

    def test_upscreening_without_a_specification_does_not_count(self):
        record = _element("die", "class-3", upscreening={"lot_traceability": True})
        self.assertFalse(upscreening_declared(record))

    def test_absent_upscreening_does_not_count(self):
        self.assertFalse(upscreening_declared(_element("die", "class-3")))


class DispositionTests(unittest.TestCase):
    def test_element_at_the_target_is_admissible_unaided(self):
        self.assertEqual(element_disposition(_element("die", "class-2")), ADMISSIBLE_UNAIDED)

    def test_element_above_the_target_is_admissible_unaided(self):
        self.assertEqual(element_disposition(_element("die", "class-1")), ADMISSIBLE_UNAIDED)

    def test_element_one_class_short_with_evidence_is_recoverable(self):
        record = _element("die", "class-3", upscreening=dict(_UPSCREENING))
        self.assertEqual(element_disposition(record), RECOVERABLE_BY_UPSCREENING)

    def test_element_one_class_short_without_evidence_is_refused(self):
        self.assertEqual(element_disposition(_element("die", "class-3")), ELEMENT_REFUSED)

    def test_element_two_classes_short_cannot_be_recovered(self):
        record = _element("die", "uncontrolled", upscreening=dict(_UPSCREENING))
        self.assertEqual(element_disposition(record), ELEMENT_REFUSED)

    def test_non_mapping_element_rejected(self):
        with self.assertRaises(ValueError):
            element_disposition(["die"])


class ShareTests(unittest.TestCase):
    def test_share_below_the_cap_is_within_it(self):
        self.assertTrue(share_within_cap(0.25, 0.5))

    def test_share_exactly_on_the_cap_is_within_it(self):
        self.assertTrue(share_within_cap(0.5, 0.5))

    def test_share_above_the_cap_is_not_within_it(self):
        self.assertFalse(share_within_cap(0.75, 0.5))

    def test_non_numeric_share_rejected(self):
        with self.assertRaises(ValueError):
            share_within_cap("0.5", 0.5)


class EffectiveClassTests(unittest.TestCase):
    def test_an_all_class_one_build_claims_class_one(self):
        elements = _four("class-1", "class-1", "class-1", "class-1")
        self.assertEqual(effective_hybrid_class(elements), "class-1")

    def test_one_class_two_element_pulls_the_build_to_class_two(self):
        elements = _four("class-1", "class-1", "class-2", "class-1")
        self.assertEqual(effective_hybrid_class(elements), DEFAULT_TARGET_CLASS)

    def test_a_recovered_element_claims_only_the_target_class(self):
        elements = _four(
            "class-1", "class-1", "class-3", "class-1", upscreen_kinds=("substrate",)
        )
        self.assertEqual(effective_hybrid_class(elements), DEFAULT_TARGET_CLASS)

    def test_a_refused_element_shows_its_own_weak_class(self):
        elements = _four("class-1", "class-1", "uncontrolled", "class-1")
        self.assertEqual(effective_hybrid_class(elements), "uncontrolled")


class AssessmentTests(unittest.TestCase):
    def test_an_all_target_class_build_is_admissible(self):
        result = assess_hybrid_procurement(_case())
        self.assertEqual(result["verdict"], HYBRID_ADMISSIBLE)
        self.assertAlmostEqual(result["unaided_share"], 1.0, places=9)
        self.assertAlmostEqual(result["upscreened_share"], 0.0, places=9)

    def test_one_upscreened_element_is_admissible_after_upscreening(self):
        result = assess_hybrid_procurement(
            _case(
                elements=_four(
                    "class-2", "class-2", "class-3", "class-2",
                    upscreen_kinds=("substrate",),
                )
            )
        )
        self.assertEqual(result["verdict"], HYBRID_ADMISSIBLE_AFTER_UPSCREENING)
        self.assertEqual(result["recovered_elements"], ("substrate",))
        self.assertAlmostEqual(result["upscreened_share"], 0.25, places=9)

    def test_an_upscreened_share_exactly_on_the_cap_is_still_admissible(self):
        result = assess_hybrid_procurement(
            _case(
                elements=_four(
                    "class-3", "class-2", "class-3", "class-2",
                    upscreen_kinds=("die", "substrate"),
                )
            )
        )
        self.assertAlmostEqual(
            result["upscreened_share"], DEFAULT_HYBRID_POLICY["max_upscreened_share"],
            places=9,
        )
        self.assertEqual(result["verdict"], HYBRID_ADMISSIBLE_AFTER_UPSCREENING)

    def test_an_upscreened_share_past_the_cap_refuses_the_hybrid(self):
        result = assess_hybrid_procurement(
            _case(
                elements=_four(
                    "class-3", "class-3", "class-3", "class-2",
                    upscreen_kinds=("die", "chip-resistor", "substrate"),
                )
            )
        )
        self.assertEqual(result["verdict"], HYBRID_REFUSED)
        self.assertAlmostEqual(result["upscreened_share"], 0.75, places=9)

    def test_an_element_short_without_evidence_refuses_the_hybrid(self):
        result = assess_hybrid_procurement(
            _case(elements=_four("class-2", "class-2", "class-3", "class-2"))
        )
        self.assertEqual(result["verdict"], HYBRID_REFUSED)
        self.assertEqual(result["refused_elements"], ("substrate",))

    def test_a_hybrid_without_a_procurement_specification_is_refused(self):
        result = assess_hybrid_procurement(_case(hybrid={"procurement_specification": ""}))
        self.assertEqual(result["verdict"], PROCUREMENT_SPECIFICATION_MISSING)
        self.assertIsNone(result["effective_class"])

    def test_findings_name_every_refused_element(self):
        result = assess_hybrid_procurement(
            _case(elements=_four("class-2", "uncontrolled", "class-2", "class-2"))
        )
        self.assertTrue(any("chip-resistor" in line for line in result["findings"]))

    def test_missing_elements_key_rejected(self):
        case = _case()
        del case["elements"]
        with self.assertRaises(ValueError):
            assess_hybrid_procurement(case)

    def test_missing_hybrid_key_rejected(self):
        case = _case()
        del case["hybrid"]
        with self.assertRaises(ValueError):
            assess_hybrid_procurement(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_hybrid_procurement(["hybrid"])

    def test_effective_rank_is_never_stronger_than_the_target_when_recovered(self):
        result = assess_hybrid_procurement(
            _case(
                elements=_four(
                    "class-1", "class-1", "class-3", "class-1",
                    upscreen_kinds=("substrate",),
                )
            )
        )
        self.assertEqual(result["effective_rank"], result["target_rank"])


if __name__ == "__main__":
    unittest.main()
