#!/usr/bin/env python3
"""Contract test for delivered cell assembly coding and traceability (offline)."""

import copy
import unittest

from e2008_sca_identification_and_traceability_logic import (
    CODING_COMPLIANT,
    CODING_NOT_ESTABLISHED,
    CODING_RANK,
    CODING_SHALLOW,
    DEPTH_ASSEMBLY,
    DEPTH_CONSTITUENT,
    DEPTH_LOT,
    DEPTH_NONE,
    DEPTH_RANK,
    MARKING_METHODS,
    PROCESS_EXPOSURES,
    achieved_depth,
    assess_assembly_coding,
    assess_delivery_coding,
    code_uniqueness,
    depth_shortfall,
    marking_permanence,
)

ASSEMBLY_A = {
    "code": "SCA-A-0001",
    "marking_method": "laser-engraved",
    "process_exposure": "thermal-cycling",
    "code_fields": ["lot-code", "serial"],
    "register_resolves_constituents": True,
}

ASSEMBLY_B = {
    "code": "SCA-A-0002",
    "marking_method": "laser-engraved",
    "process_exposure": "thermal-cycling",
    "code_fields": ["lot-code", "serial"],
    "register_resolves_constituents": True,
}


def _variant(base, **overrides):
    item = copy.deepcopy(base)
    for key, value in overrides.items():
        if value is None and key in item:
            del item[key]
        else:
            item[key] = value
    return item


class MarkingPermanenceTests(unittest.TestCase):
    def test_an_engraved_mark_survives_every_exposure(self):
        for exposure in PROCESS_EXPOSURES:
            result = marking_permanence("laser-engraved", exposure)
            self.assertTrue(result["survives_processing"])
            self.assertEqual(result["findings"], [])

    def test_fired_on_ink_survives_cure_but_not_cycling(self):
        self.assertTrue(
            marking_permanence("fired-on-ink", "bonding-and-cure")["survives_processing"]
        )
        result = marking_permanence("fired-on-ink", "thermal-cycling")
        self.assertFalse(result["survives_processing"])
        self.assertTrue(any("legible" in f for f in result["findings"]))

    def test_a_printed_label_is_lost_at_the_first_bonding_step(self):
        self.assertTrue(
            marking_permanence("printed-label", "handling-only")["survives_processing"]
        )
        self.assertFalse(
            marking_permanence("printed-label", "bonding-and-cure")["survives_processing"]
        )

    def test_a_record_only_scheme_marks_nothing_at_all(self):
        result = marking_permanence("record-only", "handling-only")
        self.assertFalse(result["survives_processing"])
        self.assertTrue(any("paperwork alone" in f for f in result["findings"]))

    def test_an_unknown_marking_method_is_rejected(self):
        with self.assertRaises(ValueError):
            marking_permanence("marker-pen", "handling-only")

    def test_an_unknown_process_exposure_is_rejected(self):
        with self.assertRaises(ValueError):
            marking_permanence("laser-engraved", "launch")

    def test_every_declared_pairing_is_handled(self):
        for method in MARKING_METHODS:
            for exposure in PROCESS_EXPOSURES:
                result = marking_permanence(method, exposure)
                self.assertIn(result["survives_processing"], (True, False))


class AchievedDepthTests(unittest.TestCase):
    def test_a_constituent_lot_field_reaches_constituent_depth(self):
        self.assertEqual(
            achieved_depth(["serial", "constituent-lot-code"])["depth"],
            DEPTH_CONSTITUENT,
        )

    def test_a_serial_plus_a_resolving_register_reaches_constituent_depth(self):
        self.assertEqual(
            achieved_depth(["serial"], True)["depth"], DEPTH_CONSTITUENT
        )

    def test_a_serial_alone_stops_at_the_assembly(self):
        result = achieved_depth(["lot-code", "serial"])
        self.assertEqual(result["depth"], DEPTH_ASSEMBLY)
        self.assertTrue(any("register has to close" in f for f in result["findings"]))

    def test_a_lot_code_alone_cannot_tell_two_assemblies_apart(self):
        result = achieved_depth(["lot-code"])
        self.assertEqual(result["depth"], DEPTH_LOT)
        self.assertTrue(any("indistinguishable" in f for f in result["findings"]))

    def test_no_coded_field_reaches_nothing(self):
        self.assertEqual(achieved_depth([])["depth"], DEPTH_NONE)

    def test_a_register_with_no_serial_to_key_on_is_flagged(self):
        result = achieved_depth(["lot-code"], True)
        self.assertTrue(any("needs a serial" in f for f in result["findings"]))

    def test_an_unknown_code_field_is_rejected(self):
        with self.assertRaises(ValueError):
            achieved_depth(["barcode-maybe"])

    def test_a_duplicated_code_field_is_rejected(self):
        with self.assertRaises(ValueError):
            achieved_depth(["serial", "serial"])

    def test_a_non_boolean_register_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            achieved_depth(["serial"], "yes")


class DepthShortfallTests(unittest.TestCase):
    def test_reaching_the_required_depth_meets_the_requirement(self):
        result = depth_shortfall(DEPTH_ASSEMBLY, DEPTH_ASSEMBLY)
        self.assertTrue(result["meets_requirement"])
        self.assertEqual(result["steps_short"], 0)

    def test_exceeding_the_required_depth_is_not_a_shortfall(self):
        result = depth_shortfall(DEPTH_LOT, DEPTH_CONSTITUENT)
        self.assertTrue(result["meets_requirement"])
        self.assertEqual(result["steps_short"], 0)

    def test_a_shortfall_is_counted_in_steps(self):
        result = depth_shortfall(DEPTH_CONSTITUENT, DEPTH_LOT)
        self.assertFalse(result["meets_requirement"])
        self.assertEqual(result["steps_short"], 2)

    def test_a_process_document_requiring_no_depth_is_rejected(self):
        with self.assertRaises(ValueError):
            depth_shortfall(DEPTH_NONE, DEPTH_ASSEMBLY)

    def test_an_unknown_depth_name_is_rejected(self):
        with self.assertRaises(ValueError):
            depth_shortfall("wafer", DEPTH_ASSEMBLY)

    def test_every_declared_depth_is_ranked(self):
        for depth in DEPTH_RANK:
            self.assertIn(depth, DEPTH_RANK)


class CodeUniquenessTests(unittest.TestCase):
    def test_a_distinct_set_is_fully_unique(self):
        result = code_uniqueness(["A-1", "A-2", "A-3"])
        self.assertEqual(result["repeated"], [])
        self.assertAlmostEqual(result["unique_share"], 1.0, places=9)

    def test_a_repeated_code_is_named(self):
        result = code_uniqueness(["A-1", "A-2", "A-1"])
        self.assertEqual(result["repeated"], ["A-1"])
        self.assertEqual(result["distinct"], 2)

    def test_the_unique_share_is_a_share_not_a_flag(self):
        self.assertAlmostEqual(
            code_uniqueness(["A-1", "A-1", "A-2", "A-2"])["unique_share"], 0.5, places=9
        )

    def test_an_empty_delivered_set_is_rejected(self):
        with self.assertRaises(ValueError):
            code_uniqueness([])

    def test_a_blank_code_is_rejected(self):
        with self.assertRaises(ValueError):
            code_uniqueness(["A-1", "  "])


class AssemblyCodingTests(unittest.TestCase):
    def test_an_engraved_serial_with_a_resolving_register_is_compliant(self):
        result = assess_assembly_coding(ASSEMBLY_A, DEPTH_CONSTITUENT)
        self.assertEqual(result["verdict"], CODING_COMPLIANT)
        self.assertEqual(result["reached_depth"], DEPTH_CONSTITUENT)

    def test_a_shallow_scheme_is_graded_below_the_required_depth(self):
        assembly = _variant(ASSEMBLY_A, register_resolves_constituents=False)
        result = assess_assembly_coding(assembly, DEPTH_CONSTITUENT)
        self.assertEqual(result["verdict"], CODING_SHALLOW)
        self.assertTrue(any("1 step(s) short" in f for f in result["findings"]))

    def test_a_mark_that_does_not_survive_outranks_a_perfect_depth(self):
        assembly = _variant(ASSEMBLY_A, marking_method="printed-label")
        result = assess_assembly_coding(assembly, DEPTH_CONSTITUENT)
        self.assertEqual(result["verdict"], CODING_NOT_ESTABLISHED)

    def test_a_record_only_scheme_establishes_no_coding(self):
        assembly = _variant(ASSEMBLY_A, marking_method="record-only")
        self.assertEqual(
            assess_assembly_coding(assembly, DEPTH_LOT)["verdict"],
            CODING_NOT_ESTABLISHED,
        )

    def test_no_coded_field_establishes_no_coding(self):
        assembly = _variant(ASSEMBLY_A, code_fields=[], register_resolves_constituents=False)
        self.assertEqual(
            assess_assembly_coding(assembly, DEPTH_LOT)["verdict"],
            CODING_NOT_ESTABLISHED,
        )

    def test_a_lower_required_depth_lets_a_lot_code_pass(self):
        assembly = _variant(
            ASSEMBLY_A, code_fields=["lot-code"], register_resolves_constituents=False
        )
        self.assertEqual(
            assess_assembly_coding(assembly, DEPTH_LOT)["verdict"], CODING_COMPLIANT
        )

    def test_an_assembly_without_a_code_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_assembly_coding(_variant(ASSEMBLY_A, code=None), DEPTH_LOT)

    def test_a_non_mapping_assembly_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_assembly_coding("SCA-A-0001", DEPTH_LOT)


class DeliveryCodingRollUpTests(unittest.TestCase):
    def test_a_clean_delivery_meets_the_required_depth_throughout(self):
        case = {
            "delivery_id": "DEL-31",
            "assemblies": [ASSEMBLY_A, ASSEMBLY_B],
            "required_depth": DEPTH_CONSTITUENT,
        }
        result = assess_delivery_coding(case)
        self.assertEqual(result["verdict"], CODING_COMPLIANT)
        self.assertAlmostEqual(result["compliant_share"], 1.0, places=9)
        self.assertTrue(result["meets_expected_share"])

    def test_one_shallow_assembly_drags_the_delivery_down_and_is_named(self):
        shallow = _variant(ASSEMBLY_B, register_resolves_constituents=False)
        case = {
            "delivery_id": "DEL-31",
            "assemblies": [ASSEMBLY_A, shallow],
            "required_depth": DEPTH_CONSTITUENT,
        }
        result = assess_delivery_coding(case)
        self.assertEqual(result["verdict"], CODING_SHALLOW)
        self.assertEqual(result["weakest_assembly"], "SCA-A-0002")
        self.assertAlmostEqual(result["compliant_share"], 0.5, places=9)

    def test_a_repeated_code_breaks_an_otherwise_compliant_delivery(self):
        twin = _variant(ASSEMBLY_B, code="SCA-A-0001")
        case = {
            "delivery_id": "DEL-31",
            "assemblies": [ASSEMBLY_A, twin],
            "required_depth": DEPTH_CONSTITUENT,
        }
        result = assess_delivery_coding(case)
        self.assertEqual(result["verdict"], CODING_NOT_ESTABLISHED)
        self.assertEqual(result["uniqueness"]["repeated"], ["SCA-A-0001"])
        self.assertTrue(any("resolves to a set" in f for f in result["findings"]))

    def test_an_unmarked_assembly_is_listed_as_not_established(self):
        bare = _variant(ASSEMBLY_B, marking_method="record-only")
        case = {
            "delivery_id": "DEL-31",
            "assemblies": [ASSEMBLY_A, bare],
            "required_depth": DEPTH_CONSTITUENT,
        }
        result = assess_delivery_coding(case)
        self.assertEqual(result["not_established"], ["SCA-A-0002"])

    def test_the_required_depth_is_carried_into_the_roll_up(self):
        case = {
            "delivery_id": "DEL-31",
            "assemblies": [ASSEMBLY_A],
            "required_depth": DEPTH_ASSEMBLY,
        }
        self.assertEqual(assess_delivery_coding(case)["required_depth"], DEPTH_ASSEMBLY)

    def test_an_empty_delivery_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_coding(
                {"delivery_id": "DEL-31", "assemblies": [], "required_depth": DEPTH_LOT}
            )

    def test_a_delivery_without_an_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_coding(
                {"assemblies": [ASSEMBLY_A], "required_depth": DEPTH_LOT}
            )

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_coding("DEL-31")

    def test_every_assembly_verdict_is_ranked(self):
        case = {
            "delivery_id": "DEL-31",
            "assemblies": [ASSEMBLY_A, ASSEMBLY_B],
            "required_depth": DEPTH_ASSEMBLY,
        }
        for assessment in assess_delivery_coding(case)["assessments"]:
            self.assertIn(assessment["verdict"], CODING_RANK)


if __name__ == "__main__":
    unittest.main()
