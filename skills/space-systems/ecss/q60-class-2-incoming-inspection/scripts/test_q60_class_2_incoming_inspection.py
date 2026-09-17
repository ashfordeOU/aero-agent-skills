"""Contract tests for the clause 5.3.7 Class 2 arrival inspection logic.

The cases walk the bench one step at a time: reconciling the pieces that
arrived against the note and the transit damage, sizing the draw and its
acceptance numbers from the lot, grouping the defects found by severity,
reading the packaging as evidence about the pieces inside, and settling the
disposition the delivery earns. Each step is exercised on both sides of its
limit so the record shows what was judged, not only the verdict.
"""

import unittest

from q60_class_2_incoming_inspection_logic import (
    DEFAULT_SAMPLE_PLAN,
    DEFECT_SEVERITIES,
    DISPOSITION_PRECEDENCE,
    REQUIRED_ARRIVAL_DOCUMENTS,
    assess_incoming_inspection,
    documentation_findings,
    packaging_findings,
    reconcile_quantity,
    sampling_plan,
    tally_defects,
)

FULL_DOCS = list(REQUIRED_ARRIVAL_DOCUMENTS)


def _defect(severity="minor", description=None):
    record = {"severity": severity}
    if description is not None:
        record["description"] = description
    return record


def _spec(**overrides):
    spec = {
        "declared_quantity": 400,
        "counted_quantity": 400,
        "damaged_quantity": 0,
        "defects": [],
        "documents": list(FULL_DOCS),
        "packaging": {
            "static_protective_bag_intact": True,
            "shipping_seal_intact": True,
        },
    }
    spec.update(overrides)
    return spec


class SamplingPlanTests(unittest.TestCase):
    def test_small_lot_drawn_from_the_first_tier(self):
        plan = sampling_plan(12)
        self.assertEqual(plan["sample_size"], 5)
        self.assertEqual(plan["accept_major"], 0)

    def test_tier_boundary_belongs_to_the_lower_tier(self):
        self.assertEqual(sampling_plan(15)["sample_size"], 5)
        self.assertEqual(sampling_plan(16)["sample_size"], 8)

    def test_mid_lot_draws_its_own_tier(self):
        plan = sampling_plan(400)
        self.assertEqual(plan["sample_size"], 20)
        self.assertEqual(plan["accept_major"], 1)
        self.assertEqual(plan["accept_minor"], 5)

    def test_large_lot_falls_into_the_unbounded_tier(self):
        plan = sampling_plan(50000)
        self.assertEqual(plan["sample_size"], 50)
        self.assertEqual(plan["accept_major"], 3)

    def test_lot_smaller_than_its_draw_is_examined_whole(self):
        plan = sampling_plan(3)
        self.assertEqual(plan["sample_size"], 3)
        self.assertTrue(plan["whole_lot_examined"])

    def test_draw_smaller_than_the_lot_is_not_a_whole_examination(self):
        self.assertFalse(sampling_plan(400)["whole_lot_examined"])

    def test_acceptance_numbers_never_shrink_with_lot_size(self):
        sizes = [10, 40, 100, 400, 1000, 5000]
        majors = [sampling_plan(size)["accept_major"] for size in sizes]
        self.assertEqual(majors, sorted(majors))

    def test_zero_lot_refused(self):
        with self.assertRaises(ValueError):
            sampling_plan(0)

    def test_negative_lot_refused(self):
        with self.assertRaises(ValueError):
            sampling_plan(-5)

    def test_malformed_tier_refused(self):
        with self.assertRaises(ValueError):
            sampling_plan(10, [(15, 5, 0)])

    def test_plan_table_missing_a_covering_tier_refused(self):
        with self.assertRaises(ValueError):
            sampling_plan(900, [(15, 5, 0, 1)])

    def test_every_tier_is_well_formed(self):
        for tier in DEFAULT_SAMPLE_PLAN:
            self.assertEqual(len(tier), 4)


class QuantityTests(unittest.TestCase):
    def test_matching_count_has_no_findings(self):
        result = reconcile_quantity(400, 400)
        self.assertEqual(result["accepted"], 400)
        self.assertEqual(result["findings"], [])

    def test_short_delivery_is_a_finding(self):
        result = reconcile_quantity(400, 397)
        self.assertEqual(result["accepted"], 397)
        self.assertIn("were counted", result["findings"][0])

    def test_damage_leaves_the_accepted_count(self):
        result = reconcile_quantity(400, 400, 6)
        self.assertEqual(result["accepted"], 394)
        self.assertTrue(any("damaged" in item for item in result["findings"]))

    def test_damage_above_the_count_refused(self):
        with self.assertRaises(ValueError):
            reconcile_quantity(400, 10, 11)

    def test_zero_declared_refused(self):
        with self.assertRaises(ValueError):
            reconcile_quantity(0, 0)

    def test_non_integer_count_refused(self):
        with self.assertRaises(ValueError):
            reconcile_quantity(400, 400.0)


class DefectTallyTests(unittest.TestCase):
    def test_empty_draw_tallies_to_nothing(self):
        tally = tally_defects([])
        self.assertEqual(tally["total"], 0)
        self.assertEqual(tally["counts"]["major"], 0)

    def test_defects_grouped_by_severity(self):
        tally = tally_defects([_defect("major"), _defect("minor"), _defect("minor")])
        self.assertEqual(tally["counts"]["major"], 1)
        self.assertEqual(tally["counts"]["minor"], 2)
        self.assertEqual(tally["total"], 3)

    def test_description_kept_for_the_record(self):
        tally = tally_defects([_defect("critical", "cracked package body")])
        self.assertEqual(tally["detail"]["critical"], ["cracked package body"])

    def test_missing_description_falls_back_to_the_severity(self):
        tally = tally_defects([_defect("major")])
        self.assertIn("major", tally["detail"]["major"][0])

    def test_severity_is_case_insensitive(self):
        self.assertEqual(tally_defects([_defect("MAJOR")])["counts"]["major"], 1)

    def test_unknown_severity_refused(self):
        with self.assertRaises(ValueError):
            tally_defects([_defect("catastrophic")])

    def test_defect_without_a_severity_refused(self):
        with self.assertRaises(ValueError):
            tally_defects([{"description": "bent lead"}])

    def test_non_mapping_defect_refused(self):
        with self.assertRaises(ValueError):
            tally_defects(["bent lead"])

    def test_missing_defects_treated_as_none_found(self):
        self.assertEqual(tally_defects(None)["total"], 0)

    def test_three_severities_recognised(self):
        self.assertEqual(len(DEFECT_SEVERITIES), 3)


class PackagingTests(unittest.TestCase):
    def test_intact_packaging_raises_nothing(self):
        result = packaging_findings({})
        self.assertEqual(result["critical"], [])
        self.assertEqual(result["advisory"], [])

    def test_breached_bag_is_critical(self):
        result = packaging_findings({"static_protective_bag_intact": False})
        self.assertEqual(len(result["critical"]), 1)
        self.assertIn("every piece it held", result["critical"][0])

    def test_broken_seal_is_advisory(self):
        result = packaging_findings({"shipping_seal_intact": False})
        self.assertEqual(result["critical"], [])
        self.assertEqual(len(result["advisory"]), 1)

    def test_non_boolean_packaging_flag_refused(self):
        with self.assertRaises(ValueError):
            packaging_findings({"static_protective_bag_intact": "torn"})

    def test_non_mapping_packaging_refused(self):
        with self.assertRaises(ValueError):
            packaging_findings(["bag"])


class DocumentationTests(unittest.TestCase):
    def test_complete_paperwork_has_no_findings(self):
        self.assertEqual(documentation_findings(FULL_DOCS), [])

    def test_missing_document_named(self):
        held = [d for d in FULL_DOCS if d != "certificate-of-conformity"]
        self.assertEqual(documentation_findings(held), ["certificate-of-conformity"])

    def test_document_names_are_case_insensitive(self):
        self.assertEqual(documentation_findings([d.upper() for d in FULL_DOCS]), [])

    def test_empty_pack_names_every_document(self):
        self.assertEqual(len(documentation_findings([])), len(REQUIRED_ARRIVAL_DOCUMENTS))

    def test_non_sequence_pack_refused(self):
        with self.assertRaises(ValueError):
            documentation_findings("delivery-note")


class ArrivalAssessmentTests(unittest.TestCase):
    def test_clean_delivery_enters_the_bonded_store(self):
        result = assess_incoming_inspection(_spec())
        self.assertEqual(result["disposition"], "accept-to-bonded-store")
        self.assertEqual(result["accepted_quantity"], 400)
        self.assertEqual(result["blocking"], [])

    def test_one_critical_defect_quarantines_the_lot(self):
        result = assess_incoming_inspection(
            _spec(defects=[_defect("critical", "cracked package body")])
        )
        self.assertEqual(result["disposition"], "quarantine-lot")
        self.assertEqual(result["accepted_quantity"], 0)

    def test_majors_within_the_number_still_accept(self):
        result = assess_incoming_inspection(_spec(defects=[_defect("major")]))
        self.assertEqual(result["disposition"], "accept-to-bonded-store")
        self.assertTrue(any("within the acceptance number" in i for i in result["advisory"]))

    def test_majors_above_the_number_quarantine(self):
        result = assess_incoming_inspection(
            _spec(defects=[_defect("major"), _defect("major")])
        )
        self.assertEqual(result["disposition"], "quarantine-lot")

    def test_minors_above_the_number_screen_the_remainder(self):
        result = assess_incoming_inspection(_spec(defects=[_defect("minor")] * 6))
        self.assertEqual(result["disposition"], "screen-remainder")
        self.assertEqual(result["accepted_quantity"], 400)

    def test_minors_on_the_number_still_accept(self):
        result = assess_incoming_inspection(_spec(defects=[_defect("minor")] * 5))
        self.assertEqual(result["disposition"], "accept-to-bonded-store")

    def test_breached_bag_quarantines_a_defect_free_draw(self):
        result = assess_incoming_inspection(
            _spec(packaging={"static_protective_bag_intact": False})
        )
        self.assertEqual(result["disposition"], "quarantine-lot")

    def test_broken_seal_alone_does_not_quarantine(self):
        result = assess_incoming_inspection(
            _spec(packaging={"shipping_seal_intact": False})
        )
        self.assertEqual(result["disposition"], "accept-to-bonded-store")
        self.assertTrue(any("shipping seal" in item for item in result["advisory"]))

    def test_missing_paperwork_holds_the_delivery(self):
        held = [d for d in FULL_DOCS if d != "lot-traceability-record"]
        result = assess_incoming_inspection(_spec(documents=held))
        self.assertEqual(result["disposition"], "hold-for-documentation")
        self.assertEqual(result["missing_documents"], ["lot-traceability-record"])

    def test_quarantine_outranks_a_documentation_hold(self):
        result = assess_incoming_inspection(
            _spec(documents=[], defects=[_defect("critical")])
        )
        self.assertEqual(result["disposition"], "quarantine-lot")

    def test_documentation_hold_outranks_a_screen(self):
        result = assess_incoming_inspection(
            _spec(documents=[], defects=[_defect("minor")] * 6)
        )
        self.assertEqual(result["disposition"], "hold-for-documentation")

    def test_damage_shrinks_the_lot_the_plan_is_sized_on(self):
        result = assess_incoming_inspection(
            _spec(declared_quantity=20, counted_quantity=20, damaged_quantity=6)
        )
        self.assertEqual(result["quantity"]["accepted"], 14)
        self.assertEqual(result["plan"]["sample_size"], 5)

    def test_wholly_damaged_delivery_is_quarantined(self):
        result = assess_incoming_inspection(
            _spec(declared_quantity=8, counted_quantity=8, damaged_quantity=8)
        )
        self.assertEqual(result["disposition"], "quarantine-lot")
        self.assertIsNone(result["plan"])
        self.assertEqual(result["accepted_quantity"], 0)

    def test_more_defects_than_the_draw_refused(self):
        with self.assertRaises(ValueError):
            assess_incoming_inspection(
                _spec(declared_quantity=10, counted_quantity=10, defects=[_defect()] * 6)
            )

    def test_short_count_is_reported_even_on_acceptance(self):
        result = assess_incoming_inspection(_spec(counted_quantity=397))
        self.assertEqual(result["disposition"], "accept-to-bonded-store")
        self.assertTrue(any("were counted" in item for item in result["advisory"]))

    def test_missing_spec_key_refused(self):
        spec = _spec()
        del spec["counted_quantity"]
        with self.assertRaises(ValueError):
            assess_incoming_inspection(spec)

    def test_non_mapping_spec_refused(self):
        with self.assertRaises(ValueError):
            assess_incoming_inspection(["declared_quantity"])

    def test_precedence_runs_worst_first(self):
        self.assertEqual(DISPOSITION_PRECEDENCE[0], "quarantine-lot")
        self.assertEqual(DISPOSITION_PRECEDENCE[-1], "accept-to-bonded-store")


if __name__ == "__main__":
    unittest.main()
