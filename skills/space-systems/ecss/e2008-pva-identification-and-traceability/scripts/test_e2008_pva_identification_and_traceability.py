#!/usr/bin/env python3
"""Contract test for non-cell component identification and traceability (offline)."""

import copy
import unittest

from e2008_pva_identification_and_traceability_logic import (
    COMPONENT_FORMS,
    MARKING_METHODS,
    TRACE_BROKEN,
    TRACE_RANK,
    TRACE_TO_BATCH,
    TRACE_TO_PART,
    assess_assembly_traceability,
    assess_component,
    identity_chain,
    marking_adequacy,
    recall_scope,
)

INTACT_ROUTE = [
    {"name": "goods-inward", "records_identity": True},
    {"name": "kitting", "records_identity": True},
    {"name": "layup", "records_identity": True},
    {"name": "final-inspection", "records_identity": True},
]

BROKEN_ROUTE = [
    {"name": "goods-inward", "records_identity": True},
    {"name": "kitting", "records_identity": False},
    {"name": "layup", "records_identity": True},
    {"name": "final-inspection", "records_identity": True},
]

DIODE = {
    "name": "bypass-diode",
    "component_form": "discrete-part",
    "marking_method": "permanent-part-marking",
    "lot_id": "DIO-2291",
    "steps": INTACT_ROUTE,
}

ADHESIVE = {
    "name": "cell-bonding-adhesive",
    "component_form": "bulk-consumable",
    "marking_method": "tagged-container",
    "lot_id": "ADH-7734",
    "steps": INTACT_ROUTE,
}

USAGE_RECORDS = [
    {"assembly_serial": "PVA-001", "lot_ids": ["DIO-2291", "ADH-7734"]},
    {"assembly_serial": "PVA-002", "lot_ids": ["DIO-2291", "ADH-9001"]},
    {"assembly_serial": "PVA-003", "lot_ids": ["DIO-4110", "ADH-9001"]},
]


def _component(base, **overrides):
    item = copy.deepcopy(base)
    for key, value in overrides.items():
        if value is None and key in item:
            del item[key]
        else:
            item[key] = value
    return item


class MarkingAdequacyTests(unittest.TestCase):
    def test_marked_discrete_part_resolves_to_the_part(self):
        result = marking_adequacy("discrete-part", "permanent-part-marking")
        self.assertEqual(result["identity_resolution"], "part")
        self.assertTrue(result["survives_processing"])
        self.assertEqual(result["findings"], [])

    def test_marked_continuous_stock_falls_back_to_the_reel_batch(self):
        result = marking_adequacy("continuous-stock", "permanent-part-marking")
        self.assertEqual(result["identity_resolution"], "batch")
        self.assertFalse(result["survives_processing"])
        self.assertTrue(any("sectioning" in f for f in result["findings"]))

    def test_marking_a_bulk_consumable_rejected(self):
        with self.assertRaises(ValueError):
            marking_adequacy("bulk-consumable", "permanent-part-marking")

    def test_tagged_container_on_a_discrete_part_survives(self):
        result = marking_adequacy("discrete-part", "tagged-container")
        self.assertEqual(result["identity_resolution"], "batch")
        self.assertTrue(result["survives_processing"])

    def test_tagged_container_on_a_bulk_consumable_stops_at_dispensing(self):
        result = marking_adequacy("bulk-consumable", "tagged-container")
        self.assertFalse(result["survives_processing"])
        self.assertTrue(any("dispensing" in f for f in result["findings"]))

    def test_travelling_record_only_has_no_physical_fallback(self):
        result = marking_adequacy("discrete-part", "travelling-record-only")
        self.assertEqual(result["identity_resolution"], "batch")
        self.assertTrue(any("no physical fallback" in f for f in result["findings"]))

    def test_unmarked_component_resolves_to_nothing(self):
        result = marking_adequacy("discrete-part", "unmarked")
        self.assertEqual(result["identity_resolution"], "none")

    def test_unknown_component_form_rejected(self):
        with self.assertRaises(ValueError):
            marking_adequacy("mystery-item", "tagged-container")

    def test_unknown_marking_method_rejected(self):
        with self.assertRaises(ValueError):
            marking_adequacy("discrete-part", "sharpie")

    def test_every_declared_pairing_is_handled(self):
        for form in COMPONENT_FORMS:
            for method in MARKING_METHODS:
                if form == "bulk-consumable" and method == "permanent-part-marking":
                    continue
                result = marking_adequacy(form, method)
                self.assertIn(result["identity_resolution"], ("part", "batch", "none"))


class IdentityChainTests(unittest.TestCase):
    def test_intact_route_retains_every_step(self):
        chain = identity_chain(INTACT_ROUTE)
        self.assertEqual(chain["retained_steps"], 4)
        self.assertIsNone(chain["break_step"])
        self.assertAlmostEqual(chain["retention"], 1.0, places=9)

    def test_break_is_named_at_the_first_step_that_drops_identity(self):
        chain = identity_chain(BROKEN_ROUTE)
        self.assertEqual(chain["break_step"], "kitting")
        self.assertEqual(chain["retained_steps"], 1)

    def test_steps_past_the_break_do_not_restore_the_chain(self):
        chain = identity_chain(BROKEN_ROUTE)
        self.assertAlmostEqual(chain["retention"], 0.25, places=9)

    def test_route_order_is_preserved(self):
        self.assertEqual(identity_chain(INTACT_ROUTE)["route"][0], "goods-inward")

    def test_empty_route_rejected(self):
        with self.assertRaises(ValueError):
            identity_chain([])

    def test_duplicate_step_name_rejected(self):
        route = list(INTACT_ROUTE) + [{"name": "kitting", "records_identity": True}]
        with self.assertRaises(ValueError):
            identity_chain(route)

    def test_non_boolean_identity_flag_rejected(self):
        with self.assertRaises(ValueError):
            identity_chain([{"name": "kitting", "records_identity": "yes"}])

    def test_step_without_a_name_rejected(self):
        with self.assertRaises(ValueError):
            identity_chain([{"records_identity": True}])


class ComponentAssessmentTests(unittest.TestCase):
    def test_marked_discrete_part_on_an_intact_route_traces_to_the_part(self):
        result = assess_component(DIODE)
        self.assertEqual(result["verdict"], TRACE_TO_PART)
        self.assertTrue(result["chain_intact"])

    def test_bulk_consumable_traces_only_to_its_batch(self):
        self.assertEqual(assess_component(ADHESIVE)["verdict"], TRACE_TO_BATCH)

    def test_a_dropped_step_breaks_the_trace_however_good_the_mark(self):
        result = assess_component(_component(DIODE, steps=BROKEN_ROUTE))
        self.assertEqual(result["verdict"], TRACE_BROKEN)
        self.assertTrue(any("ends at kitting" in f for f in result["findings"]))

    def test_missing_lot_identifier_breaks_the_trace(self):
        result = assess_component(_component(DIODE, lot_id=None))
        self.assertEqual(result["verdict"], TRACE_BROKEN)
        self.assertTrue(any("no lot identifier" in f for f in result["findings"]))

    def test_unmarked_component_breaks_the_trace(self):
        result = assess_component(_component(DIODE, marking_method="unmarked"))
        self.assertEqual(result["verdict"], TRACE_BROKEN)

    def test_continuous_stock_mark_demotes_to_batch(self):
        ribbon = _component(
            DIODE,
            name="interconnector-ribbon",
            component_form="continuous-stock",
            lot_id="RIB-5512",
        )
        self.assertEqual(assess_component(ribbon)["verdict"], TRACE_TO_BATCH)

    def test_blank_lot_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_component(_component(DIODE, lot_id="   "))

    def test_non_mapping_component_rejected(self):
        with self.assertRaises(ValueError):
            assess_component("bypass-diode")


class RecallScopeTests(unittest.TestCase):
    def test_suspect_lot_reaches_every_assembly_that_consumed_it(self):
        self.assertEqual(
            recall_scope("DIO-2291", USAGE_RECORDS), ["PVA-001", "PVA-002"]
        )

    def test_a_lot_used_once_reaches_one_assembly(self):
        self.assertEqual(recall_scope("ADH-7734", USAGE_RECORDS), ["PVA-001"])

    def test_an_unused_lot_reaches_nothing(self):
        self.assertEqual(recall_scope("ADH-0000", USAGE_RECORDS), [])

    def test_a_build_record_without_lots_rejected(self):
        records = list(USAGE_RECORDS) + [
            {"assembly_serial": "PVA-004", "lot_ids": []}
        ]
        with self.assertRaises(ValueError):
            recall_scope("DIO-2291", records)

    def test_a_build_record_without_a_serial_rejected(self):
        with self.assertRaises(ValueError):
            recall_scope("DIO-2291", [{"lot_ids": ["DIO-2291"]}])

    def test_blank_lot_query_rejected(self):
        with self.assertRaises(ValueError):
            recall_scope("", USAGE_RECORDS)


class AssemblyRollUpTests(unittest.TestCase):
    def test_all_traceable_components_give_a_batch_level_assembly(self):
        case = {"assembly_serial": "PVA-001", "components": [DIODE, ADHESIVE]}
        result = assess_assembly_traceability(case)
        self.assertEqual(result["verdict"], TRACE_TO_BATCH)
        self.assertEqual(result["broken_components"], [])
        self.assertAlmostEqual(result["traceable_share"], 1.0, places=9)

    def test_one_broken_component_breaks_the_assembly(self):
        case = {
            "assembly_serial": "PVA-002",
            "components": [DIODE, _component(ADHESIVE, steps=BROKEN_ROUTE)],
        }
        result = assess_assembly_traceability(case)
        self.assertEqual(result["verdict"], TRACE_BROKEN)
        self.assertEqual(result["weakest_component"], "cell-bonding-adhesive")
        self.assertAlmostEqual(result["traceable_share"], 0.5, places=9)

    def test_reachable_lots_are_reported_for_the_assembly(self):
        case = {"assembly_serial": "PVA-001", "components": [DIODE, ADHESIVE]}
        self.assertEqual(
            assess_assembly_traceability(case)["lots_reachable"],
            ["ADH-7734", "DIO-2291"],
        )

    def test_every_verdict_is_ranked(self):
        case = {"assembly_serial": "PVA-001", "components": [DIODE, ADHESIVE]}
        for assessment in assess_assembly_traceability(case)["assessments"]:
            self.assertIn(assessment["verdict"], TRACE_RANK)

    def test_duplicate_component_rejected(self):
        case = {
            "assembly_serial": "PVA-001",
            "components": [DIODE, copy.deepcopy(DIODE)],
        }
        with self.assertRaises(ValueError):
            assess_assembly_traceability(case)

    def test_empty_component_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_assembly_traceability(
                {"assembly_serial": "PVA-001", "components": []}
            )

    def test_missing_assembly_serial_rejected(self):
        with self.assertRaises(ValueError):
            assess_assembly_traceability({"components": [DIODE]})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_assembly_traceability("PVA-001")


if __name__ == "__main__":
    unittest.main()
