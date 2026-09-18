#!/usr/bin/env python3
"""Gate 3 contract test for q6005-chip-lot-acceptance-conditions.

Offline, stdlib unittest. Exercises the sublot validation, quantity
reconciliation, traceability coverage, wafer-lot homogeneity, the delivery
documentation check and the three-way disposition of ECSS-Q-ST-60-05C clause
8.1.4 as paraphrased in the logic module. Coverage and homogeneity land
exactly on one for a clean delivery, so those bounds are asserted with
assertAlmostEqual rather than a strict inequality that libm could round either
way between build host and CI runner.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_chip_lot_acceptance_conditions_logic import (  # noqa: E402
    REQUIRED_DOCUMENTS,
    assess_lot_acceptance,
    delivered_quantity,
    homogeneity_ratio,
    missing_documents,
    reconcile_quantities,
    traceability_coverage,
    untraceable_sublots,
    validate_sublots,
    wafer_lot_breakdown,
)


def sublot(wafer="WL-4471", diffusion="DL-88", quantity=100):
    return {"wafer_lot_id": wafer, "diffusion_lot_id": diffusion, "quantity": quantity}


def delivery(**overrides):
    """A clean single-wafer-lot delivery of 100 fully traceable dice."""
    spec = {
        "sublots": [sublot()],
        "ordered_quantity": 100,
        "documents": list(REQUIRED_DOCUMENTS),
    }
    spec.update(overrides)
    return spec


class SublotValidationTests(unittest.TestCase):
    def test_empty_delivery_is_refused(self):
        with self.assertRaises(ValueError):
            validate_sublots([])

    def test_mapping_is_not_a_sequence_of_sublots(self):
        with self.assertRaises(ValueError):
            validate_sublots({"wafer_lot_id": "WL-1", "quantity": 10})

    def test_sublot_without_quantity_is_refused(self):
        with self.assertRaises(ValueError):
            validate_sublots([{"wafer_lot_id": "WL-1", "diffusion_lot_id": "DL-1"}])

    def test_non_positive_quantity_is_refused(self):
        for bad in (0, -5):
            with self.assertRaises(ValueError):
                validate_sublots([sublot(quantity=bad)])

    def test_boolean_quantity_is_refused(self):
        with self.assertRaises(ValueError):
            validate_sublots([sublot(quantity=True)])

    def test_placeholder_identity_normalises_to_untraceable_not_an_error(self):
        normalised = validate_sublots([sublot(diffusion="TBD")])
        self.assertIsNone(normalised[0]["diffusion_lot_id"])
        self.assertFalse(normalised[0]["traceable"])

    def test_non_string_identity_is_refused(self):
        with self.assertRaises(ValueError):
            validate_sublots([sublot(wafer=17)])

    def test_delivered_quantity_sums_the_sublots(self):
        self.assertEqual(delivered_quantity([sublot(quantity=60), sublot(quantity=40)]), 100)


class QuantityReconciliationTests(unittest.TestCase):
    def test_matching_delivery_raises_no_quantity_finding(self):
        result = reconcile_quantities([sublot()], 100, 100)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["quantity_matches_order"])
        self.assertFalse(result["paperwork_disagrees"])

    def test_declared_quantity_disagreeing_with_the_sublots_is_flagged(self):
        result = reconcile_quantities([sublot(quantity=90)], 100, 100)
        self.assertTrue(result["paperwork_disagrees"])
        self.assertTrue(any("delivery note" in f for f in result["findings"]))

    def test_short_delivery_is_flagged_without_a_paperwork_failure(self):
        result = reconcile_quantities([sublot(quantity=90)], 100)
        self.assertFalse(result["paperwork_disagrees"])
        self.assertTrue(any("short" in f for f in result["findings"]))

    def test_over_delivery_is_flagged(self):
        result = reconcile_quantities([sublot(quantity=120)], 100)
        self.assertTrue(any("over" in f for f in result["findings"]))

    def test_non_positive_ordered_quantity_is_refused(self):
        with self.assertRaises(ValueError):
            reconcile_quantities([sublot()], 0)


class TraceabilityTests(unittest.TestCase):
    def test_full_delivery_covers_every_die(self):
        # Coverage lands exactly on one; assert the equality, not a side of it.
        self.assertAlmostEqual(traceability_coverage([sublot()]), 1.0, places=9)

    def test_missing_diffusion_lot_removes_that_sublot_from_coverage(self):
        sublots = [sublot(quantity=75), sublot(diffusion=None, quantity=25)]
        self.assertAlmostEqual(traceability_coverage(sublots), 0.75, places=9)

    def test_coverage_is_weighted_by_quantity_not_by_sublot_count(self):
        sublots = [sublot(quantity=990), sublot(wafer=None, quantity=10)]
        self.assertAlmostEqual(traceability_coverage(sublots), 0.99, places=9)

    def test_untraceable_sublots_are_reported_by_index(self):
        sublots = [sublot(), sublot(wafer="unknown"), sublot()]
        self.assertEqual(untraceable_sublots(sublots), [1])


class HomogeneityTests(unittest.TestCase):
    def test_single_wafer_lot_delivery_is_fully_homogeneous(self):
        self.assertAlmostEqual(homogeneity_ratio([sublot()]), 1.0, places=9)

    def test_two_sublots_from_one_wafer_lot_stay_homogeneous(self):
        sublots = [sublot(quantity=40), sublot(quantity=60)]
        self.assertAlmostEqual(homogeneity_ratio(sublots), 1.0, places=9)
        self.assertEqual(len(wafer_lot_breakdown(sublots)), 1)

    def test_split_delivery_reports_the_largest_lot_fraction(self):
        sublots = [sublot(quantity=70), sublot(wafer="WL-9002", quantity=30)]
        self.assertAlmostEqual(homogeneity_ratio(sublots), 0.70, places=9)

    def test_breakdown_is_ordered_largest_lot_first(self):
        sublots = [sublot(wafer="WL-B", quantity=30), sublot(wafer="WL-A", quantity=70)]
        self.assertEqual(wafer_lot_breakdown(sublots)[0], ("WL-A", 70))


class DocumentationTests(unittest.TestCase):
    def test_complete_documentation_set_leaves_nothing_missing(self):
        self.assertEqual(missing_documents(list(REQUIRED_DOCUMENTS)), [])

    def test_document_names_are_matched_case_and_separator_insensitively(self):
        provided = [d.replace("-", " ").upper() for d in REQUIRED_DOCUMENTS]
        self.assertEqual(missing_documents(provided), [])

    def test_absent_document_is_reported(self):
        provided = [d for d in REQUIRED_DOCUMENTS if d != "esd-handling-record"]
        self.assertEqual(missing_documents(provided), ["esd-handling-record"])

    def test_blank_document_name_is_refused(self):
        with self.assertRaises(ValueError):
            missing_documents(["certificate-of-conformity", "  "])

    def test_string_is_not_a_document_list(self):
        with self.assertRaises(ValueError):
            missing_documents("certificate-of-conformity")


class DispositionTests(unittest.TestCase):
    def test_clean_delivery_is_accepted(self):
        result = assess_lot_acceptance(delivery())
        self.assertEqual(result["disposition"], "accept")
        self.assertTrue(result["accepted"])
        self.assertEqual(result["rejections"], [])
        self.assertEqual(result["reservations"], [])
        self.assertAlmostEqual(result["traceability_coverage"], 1.0, places=9)
        self.assertAlmostEqual(result["homogeneity_ratio"], 1.0, places=9)

    def test_untraceable_die_rejects_the_delivery(self):
        spec = delivery(sublots=[sublot(quantity=99), sublot(diffusion=None, quantity=1)],
                        ordered_quantity=100)
        result = assess_lot_acceptance(spec)
        self.assertEqual(result["disposition"], "reject")
        self.assertFalse(result["fully_traceable"])
        self.assertTrue(any("traceability" in r for r in result["rejections"]))

    def test_missing_document_rejects_the_delivery(self):
        spec = delivery(documents=[d for d in REQUIRED_DOCUMENTS if d != "certificate-of-conformity"])
        result = assess_lot_acceptance(spec)
        self.assertEqual(result["disposition"], "reject")
        self.assertEqual(result["missing_documents"], ["certificate-of-conformity"])

    def test_split_lot_rejects_when_multiple_lots_were_not_permitted(self):
        spec = delivery(sublots=[sublot(quantity=50), sublot(wafer="WL-9002", quantity=50)])
        result = assess_lot_acceptance(spec)
        self.assertEqual(result["disposition"], "reject")
        self.assertTrue(any("wafer lots" in r for r in result["rejections"]))

    def test_split_lot_is_a_reservation_when_multiple_lots_were_permitted(self):
        spec = delivery(
            sublots=[sublot(quantity=50), sublot(wafer="WL-9002", quantity=50)],
            multiple_wafer_lots_permitted=True,
        )
        result = assess_lot_acceptance(spec)
        self.assertEqual(result["disposition"], "accept-with-reservation")
        self.assertTrue(result["accepted"])
        self.assertAlmostEqual(result["homogeneity_ratio"], 0.5, places=9)

    def test_paperwork_disagreeing_with_the_goods_rejects(self):
        spec = delivery(sublots=[sublot(quantity=95)], declared_quantity=100,
                        ordered_quantity=100)
        result = assess_lot_acceptance(spec)
        self.assertEqual(result["disposition"], "reject")
        self.assertTrue(any("does not describe the goods" in r for r in result["rejections"]))

    def test_short_delivery_alone_is_a_reservation_not_a_rejection(self):
        spec = delivery(sublots=[sublot(quantity=95)], ordered_quantity=100)
        result = assess_lot_acceptance(spec)
        self.assertEqual(result["disposition"], "accept-with-reservation")
        self.assertTrue(any("short" in r for r in result["reservations"]))

    def test_several_conditions_failing_are_all_named(self):
        spec = delivery(
            sublots=[sublot(quantity=50), sublot(wafer=None, quantity=50)],
            documents=["certificate-of-conformity"],
        )
        result = assess_lot_acceptance(spec)
        self.assertEqual(result["disposition"], "reject")
        self.assertGreaterEqual(len(result["rejections"]), 3)

    def test_report_carries_the_lot_breakdown_and_counts(self):
        spec = delivery(
            sublots=[sublot(quantity=70), sublot(wafer="WL-9002", quantity=30)],
            multiple_wafer_lots_permitted=True,
        )
        result = assess_lot_acceptance(spec)
        self.assertEqual(result["sublot_count"], 2)
        self.assertEqual(result["delivered_quantity"], 100)
        self.assertEqual(result["wafer_lot_breakdown"][0], ("WL-4471", 70))

    def test_missing_required_key_is_refused(self):
        for key in ("sublots", "ordered_quantity", "documents"):
            spec = delivery()
            del spec[key]
            with self.assertRaises(ValueError):
                assess_lot_acceptance(spec)

    def test_non_boolean_multi_lot_permission_is_refused(self):
        with self.assertRaises(ValueError):
            assess_lot_acceptance(delivery(multiple_wafer_lots_permitted="yes"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
