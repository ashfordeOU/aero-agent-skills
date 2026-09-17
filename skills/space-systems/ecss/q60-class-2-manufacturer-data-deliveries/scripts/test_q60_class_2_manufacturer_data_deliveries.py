"""Contract tests for the clause 5.3.11 Class 2 data delivery logic."""

import unittest

from q60_class_2_manufacturer_data_deliveries_logic import (
    ACCEPT_THRESHOLD,
    ACTIONS_THRESHOLD,
    CATEGORY_RECORDS,
    MANDATORY_RECORDS,
    RECORD_STATUSES,
    RECORD_WEIGHTS,
    STATUS_CREDIT,
    assess_data_package,
    completeness_fraction,
    grade_package,
    grade_record,
    mandatory_gaps,
    owed_records,
    record_weight,
)

LOT = "lot-4471"
DISPATCH_DAY = 900
QUANTITY = 100


def good(**overrides):
    record = {
        "lot_code": LOT,
        "issue_day": 880,
        "quantity_covered": QUANTITY,
        "signed": True,
    }
    record.update(overrides)
    return record


class OwedRecordTests(unittest.TestCase):
    def test_passive_owes_the_short_set(self):
        self.assertEqual(len(owed_records("passive")), 3)

    def test_microcircuit_owes_more_than_a_passive(self):
        self.assertGreater(
            len(owed_records("microcircuit")), len(owed_records("passive"))
        )

    def test_certificate_is_owed_by_every_category(self):
        for category in CATEGORY_RECORDS:
            self.assertIn("certificate-of-conformity", owed_records(category))

    def test_screened_lot_adds_the_screening_data(self):
        owed = owed_records("microcircuit", {"screened_lot": True})
        self.assertIn("screening-test-data", owed)

    def test_unscreened_lot_does_not_add_it(self):
        owed = owed_records("microcircuit", {"screened_lot": False})
        self.assertNotIn("screening-test-data", owed)

    def test_radiation_lot_acceptance_adds_its_report(self):
        self.assertIn(
            "radiation-lot-acceptance-report",
            owed_records("microcircuit", {"radiation_lot_acceptance": True}),
        )

    def test_rework_adds_its_record(self):
        self.assertIn(
            "rework-and-repair-record",
            owed_records("hybrid", {"rework_performed": True}),
        )

    def test_unknown_category_refused(self):
        with self.assertRaises(ValueError):
            owed_records("subsystem")

    def test_unrecognised_lot_history_flag_refused(self):
        with self.assertRaises(ValueError):
            owed_records("passive", {"was_dropped": True})

    def test_owed_set_has_no_repeats(self):
        owed = owed_records("microcircuit", {"screened_lot": True})
        self.assertEqual(len(owed), len(set(owed)))


class WeightTests(unittest.TestCase):
    def test_certificate_outweighs_the_packing_note(self):
        self.assertGreater(
            record_weight("certificate-of-conformity"),
            record_weight("packing-and-handling-note"),
        )

    def test_weight_is_read_from_the_register(self):
        self.assertAlmostEqual(record_weight("lot-traceability-record"), 4.0, places=9)

    def test_unweighted_record_refused(self):
        with self.assertRaises(ValueError):
            record_weight("informal-email-thread")

    def test_every_owed_record_carries_a_weight(self):
        for category in CATEGORY_RECORDS:
            for name in owed_records(category):
                self.assertIn(name, RECORD_WEIGHTS)

    def test_status_credits_cover_every_status(self):
        for status in RECORD_STATUSES:
            self.assertIn(status, STATUS_CREDIT)


class RecordGradingTests(unittest.TestCase):
    def test_a_clean_record_is_delivered(self):
        self.assertEqual(grade_record(good(), LOT, DISPATCH_DAY, QUANTITY), "delivered")

    def test_a_summary_is_graded_as_a_summary(self):
        self.assertEqual(
            grade_record(good(summary_only=True), LOT, DISPATCH_DAY, QUANTITY), "summary"
        )

    def test_an_issue_day_after_dispatch_is_late(self):
        self.assertEqual(
            grade_record(good(issue_day=940), LOT, DISPATCH_DAY, QUANTITY), "late"
        )

    def test_an_issue_day_on_dispatch_is_still_delivered(self):
        self.assertEqual(
            grade_record(good(issue_day=DISPATCH_DAY), LOT, DISPATCH_DAY, QUANTITY),
            "delivered",
        )

    def test_an_unsigned_record_is_unsigned(self):
        self.assertEqual(
            grade_record(good(signed=False), LOT, DISPATCH_DAY, QUANTITY), "unsigned"
        )

    def test_a_record_covering_fewer_parts_is_short(self):
        self.assertEqual(
            grade_record(good(quantity_covered=60), LOT, DISPATCH_DAY, QUANTITY),
            "short-quantity",
        )

    def test_a_record_covering_more_parts_is_still_delivered(self):
        self.assertEqual(
            grade_record(good(quantity_covered=250), LOT, DISPATCH_DAY, QUANTITY),
            "delivered",
        )

    def test_another_lot_outranks_a_missing_signature(self):
        self.assertEqual(
            grade_record(
                good(lot_code="lot-9999", signed=False), LOT, DISPATCH_DAY, QUANTITY
            ),
            "lot-mismatch",
        )

    def test_a_missing_signature_outranks_a_short_quantity(self):
        self.assertEqual(
            grade_record(
                good(signed=False, quantity_covered=10), LOT, DISPATCH_DAY, QUANTITY
            ),
            "unsigned",
        )

    def test_a_short_quantity_outranks_a_late_issue(self):
        self.assertEqual(
            grade_record(
                good(quantity_covered=10, issue_day=940), LOT, DISPATCH_DAY, QUANTITY
            ),
            "short-quantity",
        )

    def test_a_late_issue_outranks_a_summary(self):
        self.assertEqual(
            grade_record(
                good(issue_day=940, summary_only=True), LOT, DISPATCH_DAY, QUANTITY
            ),
            "late",
        )

    def test_record_missing_a_key_refused(self):
        record = good()
        del record["signed"]
        with self.assertRaises(ValueError):
            grade_record(record, LOT, DISPATCH_DAY, QUANTITY)

    def test_non_integer_issue_day_refused(self):
        with self.assertRaises(ValueError):
            grade_record(good(issue_day="2026-09-01"), LOT, DISPATCH_DAY, QUANTITY)

    def test_zero_delivered_quantity_refused(self):
        with self.assertRaises(ValueError):
            grade_record(good(), LOT, DISPATCH_DAY, 0)


class PackageGradingTests(unittest.TestCase):
    def test_absent_record_is_graded_absent(self):
        graded = grade_package(
            owed_records("passive"), {}, LOT, DISPATCH_DAY, QUANTITY
        )
        self.assertEqual(graded["certificate-of-conformity"]["status"], "absent")

    def test_delivered_record_carries_full_credit(self):
        graded = grade_package(
            owed_records("passive"),
            {"certificate-of-conformity": good()},
            LOT,
            DISPATCH_DAY,
            QUANTITY,
        )
        self.assertAlmostEqual(
            graded["certificate-of-conformity"]["credit"], 1.0, places=9
        )

    def test_a_record_the_shipment_does_not_owe_is_refused(self):
        with self.assertRaises(ValueError):
            grade_package(
                owed_records("passive"),
                {"screening-test-data": good()},
                LOT,
                DISPATCH_DAY,
                QUANTITY,
            )

    def test_empty_owed_set_refused(self):
        with self.assertRaises(ValueError):
            grade_package((), {}, LOT, DISPATCH_DAY, QUANTITY)

    def test_full_package_is_completely_complete(self):
        owed = owed_records("passive")
        graded = grade_package(
            owed, {name: good() for name in owed}, LOT, DISPATCH_DAY, QUANTITY
        )
        self.assertAlmostEqual(completeness_fraction(graded), 1.0, places=9)

    def test_empty_package_is_zero_complete(self):
        graded = grade_package(owed_records("passive"), {}, LOT, DISPATCH_DAY, QUANTITY)
        self.assertAlmostEqual(completeness_fraction(graded), 0.0, places=9)

    def test_weighting_makes_a_heavy_gap_cost_more(self):
        owed = owed_records("passive")
        without_certificate = grade_package(
            owed,
            {
                name: good()
                for name in owed
                if name != "certificate-of-conformity"
            },
            LOT,
            DISPATCH_DAY,
            QUANTITY,
        )
        without_note = grade_package(
            owed,
            {
                name: good()
                for name in owed
                if name != "date-code-and-quantity-list"
            },
            LOT,
            DISPATCH_DAY,
            QUANTITY,
        )
        self.assertLess(
            completeness_fraction(without_certificate),
            completeness_fraction(without_note),
        )

    def test_credit_outside_the_unit_interval_refused(self):
        with self.assertRaises(ValueError):
            completeness_fraction(
                {"certificate-of-conformity": {"weight": 5.0, "credit": 1.4}}
            )

    def test_empty_grade_map_refused(self):
        with self.assertRaises(ValueError):
            completeness_fraction({})


class MandatoryGapTests(unittest.TestCase):
    def test_a_full_package_has_no_mandatory_gap(self):
        owed = owed_records("passive")
        graded = grade_package(
            owed, {name: good() for name in owed}, LOT, DISPATCH_DAY, QUANTITY
        )
        self.assertEqual(mandatory_gaps(graded), ())

    def test_a_missing_certificate_is_a_mandatory_gap(self):
        owed = owed_records("passive")
        graded = grade_package(
            owed,
            {name: good() for name in owed if name != "certificate-of-conformity"},
            LOT,
            DISPATCH_DAY,
            QUANTITY,
        )
        self.assertIn("certificate-of-conformity", mandatory_gaps(graded))

    def test_a_certificate_summary_is_still_a_mandatory_gap(self):
        owed = owed_records("passive")
        delivered = {name: good() for name in owed}
        delivered["certificate-of-conformity"] = good(summary_only=True)
        graded = grade_package(owed, delivered, LOT, DISPATCH_DAY, QUANTITY)
        self.assertIn("certificate-of-conformity", mandatory_gaps(graded))

    def test_two_records_are_mandatory(self):
        self.assertEqual(len(MANDATORY_RECORDS), 2)


class AssessmentTests(unittest.TestCase):
    def _spec(self, category="passive", missing=(), **overrides):
        history = overrides.get("lot_history")
        owed = owed_records(category, history)
        delivered = {name: good() for name in owed if name not in missing}
        spec = {
            "part_category": category,
            "lot_code": LOT,
            "dispatch_day": DISPATCH_DAY,
            "delivered_quantity": QUANTITY,
            "delivered_records": delivered,
        }
        spec.update(overrides)
        return spec

    def test_a_full_package_is_accepted(self):
        out = assess_data_package(self._spec())
        self.assertEqual(out["disposition"], "accept-into-stores")

    def test_a_full_package_is_complete(self):
        out = assess_data_package(self._spec())
        self.assertAlmostEqual(out["completeness_fraction"], 1.0, places=9)

    def test_a_full_package_meets_a_threshold_of_one(self):
        out = assess_data_package(self._spec(accept_threshold=1.0))
        self.assertEqual(out["disposition"], "accept-into-stores")

    def test_a_missing_certificate_holds_the_shipment(self):
        out = assess_data_package(
            self._spec(missing=("certificate-of-conformity",))
        )
        self.assertEqual(out["disposition"], "hold-shipment")

    def test_a_mandatory_gap_outranks_a_high_completeness(self):
        out = assess_data_package(
            self._spec(
                category="microcircuit",
                missing=("lot-traceability-record",),
                actions_threshold=0.1,
                accept_threshold=0.2,
            )
        )
        self.assertEqual(out["disposition"], "hold-shipment")

    def test_a_light_gap_earns_actions(self):
        out = assess_data_package(
            self._spec(
                category="microcircuit", missing=("packing-and-handling-note",)
            )
        )
        self.assertEqual(out["disposition"], "accept-with-actions")

    def test_a_deep_gap_holds_the_shipment(self):
        out = assess_data_package(
            self._spec(
                category="microcircuit",
                missing=("lot-acceptance-test-data", "packing-and-handling-note",
                         "date-code-and-quantity-list"),
            )
        )
        self.assertEqual(out["disposition"], "hold-shipment")

    def test_shortfalls_name_the_records_that_owe_follow_up(self):
        out = assess_data_package(
            self._spec(
                category="microcircuit", missing=("packing-and-handling-note",)
            )
        )
        self.assertIn("packing-and-handling-note", out["shortfalls"])

    def test_screened_lot_adds_its_record_to_the_assessment(self):
        out = assess_data_package(
            self._spec(category="microcircuit", lot_history={"screened_lot": True})
        )
        self.assertIn("screening-test-data", out["owed_records"])
        self.assertEqual(out["disposition"], "accept-into-stores")

    def test_actions_threshold_above_accept_refused(self):
        with self.assertRaises(ValueError):
            assess_data_package(self._spec(accept_threshold=0.5, actions_threshold=0.9))

    def test_missing_required_key_refused(self):
        spec = self._spec()
        del spec["lot_code"]
        with self.assertRaises(ValueError):
            assess_data_package(spec)

    def test_non_mapping_spec_refused(self):
        with self.assertRaises(ValueError):
            assess_data_package(["part_category"])

    def test_default_thresholds_are_ordered(self):
        self.assertLess(ACTIONS_THRESHOLD, ACCEPT_THRESHOLD)

    def test_every_disposition_carries_reasons(self):
        out = assess_data_package(self._spec(missing=("certificate-of-conformity",)))
        self.assertTrue(out["reasons"])


if __name__ == "__main__":
    unittest.main()
