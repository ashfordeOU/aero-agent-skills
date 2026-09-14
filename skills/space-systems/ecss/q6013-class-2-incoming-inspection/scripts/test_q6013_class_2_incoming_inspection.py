"""Contract tests for the clause 5.3.7 intermediate class receiving logic.

The cases follow the dock workflow one step at a time: the inspection level
earned by the delivery history, the source-type override that outranks it, the
level-scaled sample, the accept number and the allowance a tightened level
withdraws, the three order reconciliations, the delivery documents, and the
level the next delivery will be received at. Each step is exercised on both
sides of its limit.
"""

import unittest

from q6013_class_2_incoming_inspection_logic import (
    DEFAULT_ACCEPT_NUMBER,
    REDUCED_AFTER_CLEAN,
    REQUIRED_DOCUMENTS,
    SAMPLE_CAP,
    SAMPLE_FLOOR,
    SKIP_AFTER_CLEAN,
    accept_number_for,
    assess_class_2_receipt,
    determine_level,
    missing_documents,
    next_inspection_level,
    quantity_discrepancy,
    reconcile_date_code,
    reconcile_part_number,
    sample_size,
)

FULL_DOCS = {item: True for item in REQUIRED_DOCUMENTS}


def _history(clean=0, rejected=False):
    return {"consecutive_accepted": clean, "last_delivery_rejected": rejected}


def _spec(**overrides):
    spec = {
        "delivery_id": "DN-2026-0441",
        "ordered_part_number": "LM4050AIM3-2.5",
        "received_part_number": "LM4050AIM3-2.5",
        "ordered_quantity": 400,
        "received_quantity": 400,
        "ordered_date_code": "2541",
        "received_date_code": "2541",
        "source_type": "franchised-distributor",
        "history": _history(),
        "documents": dict(FULL_DOCS),
        "visual_defects": 0,
    }
    spec.update(overrides)
    return spec


class LevelTests(unittest.TestCase):
    def test_new_supplier_is_inspected_at_normal(self):
        self.assertEqual(determine_level(_history(), "franchised-distributor")["level"], "normal")

    def test_clean_record_one_short_of_the_threshold_stays_normal(self):
        history = _history(clean=REDUCED_AFTER_CLEAN - 1)
        self.assertEqual(determine_level(history, "manufacturer")["level"], "normal")

    def test_clean_record_at_the_threshold_earns_reduced(self):
        history = _history(clean=REDUCED_AFTER_CLEAN)
        self.assertEqual(determine_level(history, "manufacturer")["level"], "reduced")

    def test_long_clean_record_earns_skip_lot(self):
        history = _history(clean=SKIP_AFTER_CLEAN)
        self.assertEqual(determine_level(history, "manufacturer")["level"], "skip-lot")

    def test_skip_lot_needs_traceability_evidenced(self):
        history = _history(clean=SKIP_AFTER_CLEAN)
        result = determine_level(history, "manufacturer", traceability_evidenced=False)
        self.assertEqual(result["level"], "reduced")
        self.assertTrue(any("traceability" in reason for reason in result["reasons"]))

    def test_a_rejection_tightens_whatever_the_record(self):
        history = _history(clean=SKIP_AFTER_CLEAN, rejected=True)
        self.assertEqual(determine_level(history, "manufacturer")["level"], "tightened")

    def test_unfranchised_source_tightens_a_spotless_record(self):
        history = _history(clean=SKIP_AFTER_CLEAN)
        result = determine_level(history, "unfranchised-broker")
        self.assertEqual(result["level"], "tightened")
        self.assertTrue(any("unfranchised" in reason for reason in result["reasons"]))

    def test_unknown_source_type_rejected(self):
        with self.assertRaises(ValueError):
            determine_level(_history(), "a-man-in-a-van")

    def test_negative_clean_count_rejected(self):
        with self.assertRaises(ValueError):
            determine_level(_history(clean=-1), "manufacturer")

    def test_non_boolean_rejection_flag_rejected(self):
        history = {"consecutive_accepted": 3, "last_delivery_rejected": "no"}
        with self.assertRaises(ValueError):
            determine_level(history, "manufacturer")


class SampleSizeTests(unittest.TestCase):
    def test_normal_sample_is_the_integer_square_root(self):
        self.assertEqual(sample_size("normal", 400), 20)

    def test_reduced_sample_is_about_half_the_normal_one(self):
        self.assertEqual(sample_size("reduced", 400), 10)

    def test_tightened_sample_is_double_the_normal_one(self):
        self.assertEqual(sample_size("tightened", 400), 40)

    def test_skip_lot_draws_no_visual_sample(self):
        self.assertEqual(sample_size("skip-lot", 400), 0)

    def test_small_lot_is_raised_to_the_floor(self):
        self.assertEqual(sample_size("reduced", 9), SAMPLE_FLOOR)

    def test_sample_never_exceeds_the_lot(self):
        self.assertEqual(sample_size("tightened", 2), 2)

    def test_large_lot_is_held_at_the_cap(self):
        self.assertEqual(sample_size("tightened", 1000000), SAMPLE_CAP)

    def test_exact_square_lot_sizes_are_reproducible(self):
        self.assertEqual(sample_size("normal", 2500), 50)
        self.assertEqual(sample_size("normal", 2499), 49)

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValueError):
            sample_size("normal", 0)

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            sample_size("occasional", 100)

    def test_cap_below_floor_rejected(self):
        with self.assertRaises(ValueError):
            sample_size("normal", 100, floor=10, cap=5)


class AcceptNumberTests(unittest.TestCase):
    def test_default_is_accept_on_zero(self):
        self.assertEqual(accept_number_for("normal"), DEFAULT_ACCEPT_NUMBER)

    def test_declared_allowance_is_honoured_at_reduced(self):
        self.assertEqual(accept_number_for("reduced", 1), 1)

    def test_tightened_withdraws_the_declared_allowance(self):
        self.assertEqual(accept_number_for("tightened", 3), 0)

    def test_negative_declared_allowance_rejected(self):
        with self.assertRaises(ValueError):
            accept_number_for("normal", -1)


class ReconciliationTests(unittest.TestCase):
    def test_case_and_spacing_differences_still_match(self):
        self.assertTrue(reconcile_part_number(" lm4050aim3-2.5 ", "LM4050AIM3-2.5")["matches"])

    def test_substituted_part_number_does_not_match(self):
        self.assertFalse(reconcile_part_number("LM4050AIM3-2.5", "LM4050AIM3-5.0")["matches"])

    def test_blank_part_number_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_part_number("", "LM4050AIM3-2.5")

    def test_unconstrained_order_matches_any_date_code(self):
        result = reconcile_date_code(None, "2607")
        self.assertTrue(result["matches"])
        self.assertFalse(result["constrained"])

    def test_stated_date_code_must_match(self):
        self.assertFalse(reconcile_date_code("2541", "2607")["matches"])

    def test_shortfall_and_overage_are_separate_numbers(self):
        short = quantity_discrepancy(400, 380)
        self.assertEqual(short["shortfall"], 20)
        self.assertEqual(short["overage"], 0)
        over = quantity_discrepancy(400, 410)
        self.assertEqual(over["shortfall"], 0)
        self.assertEqual(over["overage"], 10)

    def test_zero_received_quantity_rejected(self):
        with self.assertRaises(ValueError):
            quantity_discrepancy(400, 0)


class DocumentTests(unittest.TestCase):
    def test_full_document_set_leaves_nothing_absent(self):
        self.assertEqual(missing_documents(FULL_DOCS), [])

    def test_document_marked_not_received_is_absent(self):
        documents = dict(FULL_DOCS)
        documents["certificate-of-conformity"] = False
        self.assertEqual(missing_documents(documents), ["certificate-of-conformity"])

    def test_document_omitted_entirely_is_absent(self):
        documents = dict(FULL_DOCS)
        del documents["manufacturer-traceability"]
        self.assertEqual(missing_documents(documents), ["manufacturer-traceability"])

    def test_sequence_of_names_reads_as_all_received(self):
        self.assertEqual(missing_documents(list(REQUIRED_DOCUMENTS)), [])

    def test_non_boolean_document_value_rejected(self):
        with self.assertRaises(ValueError):
            missing_documents({"certificate-of-conformity": "following by email"})


class NextLevelTests(unittest.TestCase):
    def test_a_quarantine_tightens_the_next_delivery(self):
        self.assertEqual(next_inspection_level("reduced", False, 0), "tightened")

    def test_a_clean_accept_holds_the_level(self):
        self.assertEqual(next_inspection_level("reduced", True, 0), "reduced")

    def test_a_tolerated_defect_returns_a_reduced_level_to_normal(self):
        self.assertEqual(next_inspection_level("reduced", True, 1), "normal")

    def test_a_tolerated_defect_does_not_ease_a_tightened_level(self):
        self.assertEqual(next_inspection_level("tightened", True, 1), "tightened")

    def test_non_boolean_acceptance_rejected(self):
        with self.assertRaises(ValueError):
            next_inspection_level("normal", "yes", 0)


class DispositionTests(unittest.TestCase):
    def test_clean_delivery_goes_to_store(self):
        result = assess_class_2_receipt(_spec())
        self.assertEqual(result["disposition"], "accept-to-store")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["sample_size"], 20)

    def test_substituted_part_number_is_quarantined(self):
        result = assess_class_2_receipt(_spec(received_part_number="LM4050AIM3-5.0"))
        self.assertEqual(result["disposition"], "quarantine")
        self.assertEqual(result["next_level"], "tightened")

    def test_wrong_date_code_is_quarantined(self):
        self.assertEqual(
            assess_class_2_receipt(_spec(received_date_code="2607"))["disposition"], "quarantine"
        )

    def test_short_delivery_is_quarantined(self):
        result = assess_class_2_receipt(_spec(received_quantity=380))
        self.assertEqual(result["disposition"], "quarantine")
        self.assertEqual(result["quantity"]["shortfall"], 20)

    def test_overage_is_an_advisory_not_a_quarantine(self):
        result = assess_class_2_receipt(_spec(received_quantity=410, ordered_quantity=400))
        self.assertEqual(result["disposition"], "accept-to-store")
        self.assertTrue(any("over the ordered" in note for note in result["advisories"]))

    def test_missing_document_is_quarantined(self):
        documents = dict(FULL_DOCS)
        documents["packaging-declaration"] = False
        self.assertEqual(
            assess_class_2_receipt(_spec(documents=documents))["disposition"], "quarantine"
        )

    def test_defect_over_the_accept_number_is_quarantined(self):
        self.assertEqual(
            assess_class_2_receipt(_spec(visual_defects=1))["disposition"], "quarantine"
        )

    def test_defect_within_a_declared_allowance_is_accepted(self):
        result = assess_class_2_receipt(_spec(visual_defects=1, declared_accept_number=1))
        self.assertEqual(result["disposition"], "accept-to-store")
        self.assertEqual(result["next_level"], "normal")

    def test_broker_delivery_is_sampled_at_the_tightened_rate(self):
        result = assess_class_2_receipt(
            _spec(source_type="unfranchised-broker", history=_history(clean=SKIP_AFTER_CLEAN))
        )
        self.assertEqual(result["level"], "tightened")
        self.assertEqual(result["sample_size"], 40)

    def test_skip_lot_delivery_still_checks_identity_and_documents(self):
        documents = dict(FULL_DOCS)
        documents["certificate-of-conformity"] = False
        result = assess_class_2_receipt(
            _spec(history=_history(clean=SKIP_AFTER_CLEAN), documents=documents)
        )
        self.assertEqual(result["level"], "skip-lot")
        self.assertEqual(result["sample_size"], 0)
        self.assertEqual(result["disposition"], "quarantine")

    def test_every_finding_is_reported_together(self):
        documents = dict(FULL_DOCS)
        documents["packaging-declaration"] = False
        result = assess_class_2_receipt(
            _spec(
                received_part_number="LM4050AIM3-5.0",
                received_quantity=380,
                documents=documents,
                visual_defects=2,
            )
        )
        self.assertEqual(len(result["findings"]), 4)

    def test_more_defects_than_the_sample_inspected_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_2_receipt(_spec(visual_defects=999))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["documents"]
        with self.assertRaises(ValueError):
            assess_class_2_receipt(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_2_receipt(["not", "a", "mapping"])


if __name__ == "__main__":
    unittest.main()
