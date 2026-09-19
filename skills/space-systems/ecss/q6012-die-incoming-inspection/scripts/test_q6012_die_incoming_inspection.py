"""Contract tests for the clause 10.3 die batch incoming inspection."""

import unittest

from q6012_die_incoming_inspection_logic import (
    CHECK_KEYS,
    COMPUTED_CHECKS,
    DISPOSITIONS,
    OUTCOMES,
    SEVERITIES,
    applicable_checks,
    assess_incoming_inspection,
    check_outcomes,
    check_severities,
    check_titles,
    disposition_for,
    inspection_findings,
    quantity_reconciliation,
    validate_arrival,
    validate_results,
)


def arrival_spec(**overrides):
    spec = {
        "batch_id": "IN-2210",
        "ordered_quantity": 500,
        "packing_list_quantity": 500,
        "counted_quantity": 500,
        "arrived_sealed": True,
        "visual_sample_required": True,
        "wafer_map_supplied": True,
        "radiation_lot": False,
    }
    spec.update(overrides)
    return spec


def clean_results(spec=None, override=None):
    arrival = validate_arrival(spec or arrival_spec())
    results = {}
    for record in applicable_checks(arrival):
        if record["check"] in COMPUTED_CHECKS:
            continue
        results[record["check"]] = "pass"
    results.update(override or {})
    return results


def inspection_spec(**overrides):
    results_override = overrides.pop("results_override", None)
    spec = arrival_spec(**overrides)
    full = dict(spec)
    full["results"] = clean_results(spec, results_override)
    return full


class RegistryTests(unittest.TestCase):
    def test_check_keys_are_unique(self):
        self.assertEqual(len(CHECK_KEYS), len(set(CHECK_KEYS)))

    def test_every_check_has_a_title_and_a_severity(self):
        self.assertEqual(set(check_titles()), set(CHECK_KEYS))
        self.assertEqual(set(check_severities()), set(CHECK_KEYS))

    def test_every_severity_is_a_declared_severity(self):
        for severity in check_severities().values():
            self.assertIn(severity, SEVERITIES)

    def test_computed_checks_are_real_checks(self):
        for key in COMPUTED_CHECKS:
            self.assertIn(key, CHECK_KEYS)

    def test_outcome_and_disposition_vocabularies_are_closed(self):
        self.assertEqual(OUTCOMES, ("pass", "fail", "not-performed"))
        self.assertEqual(len(DISPOSITIONS), len(set(DISPOSITIONS)))


class ValidateArrivalTests(unittest.TestCase):
    def test_flags_default_when_absent(self):
        arrival = validate_arrival(
            {
                "batch_id": "B",
                "ordered_quantity": 10,
                "packing_list_quantity": 10,
                "counted_quantity": 10,
            }
        )
        self.assertTrue(arrival["arrived_sealed"])
        self.assertFalse(arrival["radiation_lot"])

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            validate_arrival(["batch_id"])

    def test_missing_required_key_rejected(self):
        spec = arrival_spec()
        del spec["counted_quantity"]
        with self.assertRaises(ValueError):
            validate_arrival(spec)

    def test_unknown_key_rejected_rather_than_ignored(self):
        with self.assertRaises(ValueError):
            validate_arrival(arrival_spec(arived_sealed=True))

    def test_fractional_quantity_rejected(self):
        with self.assertRaises(ValueError):
            validate_arrival(arrival_spec(counted_quantity=499.5))

    def test_negative_quantity_rejected(self):
        with self.assertRaises(ValueError):
            validate_arrival(arrival_spec(counted_quantity=-1))

    def test_zero_ordered_quantity_rejected(self):
        with self.assertRaises(ValueError):
            validate_arrival(arrival_spec(ordered_quantity=0))

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_arrival(arrival_spec(arrived_sealed="yes"))


class QuantityTests(unittest.TestCase):
    def test_all_three_agreeing_is_matched(self):
        result = quantity_reconciliation(validate_arrival(arrival_spec()))
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["packing_delta"], 0)
        self.assertEqual(result["order_delta"], 0)

    def test_count_disagreeing_with_the_packing_list_is_its_own_status(self):
        arrival = validate_arrival(arrival_spec(counted_quantity=480))
        result = quantity_reconciliation(arrival)
        self.assertEqual(result["status"], "packing-list-mismatch")
        self.assertEqual(result["packing_delta"], -20)

    def test_packing_list_agreeing_but_short_of_the_order(self):
        arrival = validate_arrival(
            arrival_spec(packing_list_quantity=450, counted_quantity=450)
        )
        result = quantity_reconciliation(arrival)
        self.assertEqual(result["status"], "short-shipped")
        self.assertEqual(result["order_delta"], -50)

    def test_over_shipment_is_reported_not_absorbed(self):
        arrival = validate_arrival(
            arrival_spec(packing_list_quantity=520, counted_quantity=520)
        )
        self.assertEqual(
            quantity_reconciliation(arrival)["status"], "over-shipped"
        )

    def test_reconciliation_rejects_an_unnormalised_record(self):
        with self.assertRaises(ValueError):
            quantity_reconciliation(
                {
                    "batch_id": "B",
                    "ordered_quantity": 10,
                    "packing_list_quantity": 10,
                    "counted_quantity": 10,
                }
            )


class ApplicabilityTests(unittest.TestCase):
    def test_sealed_arrival_pulls_in_the_seal_checks(self):
        keys = [r["check"] for r in applicable_checks(validate_arrival(arrival_spec()))]
        self.assertIn("seal-and-desiccant-condition", keys)
        self.assertIn("humidity-indicator-reading", keys)

    def test_unsealed_arrival_drops_the_seal_checks(self):
        arrival = validate_arrival(arrival_spec(arrived_sealed=False))
        keys = [r["check"] for r in applicable_checks(arrival)]
        self.assertNotIn("seal-and-desiccant-condition", keys)
        self.assertNotIn("humidity-indicator-reading", keys)

    def test_radiation_lot_pulls_in_its_identity_check(self):
        arrival = validate_arrival(arrival_spec(radiation_lot=True))
        keys = [r["check"] for r in applicable_checks(arrival)]
        self.assertIn("radiation-lot-identity", keys)

    def test_absent_wafer_map_drops_the_cross_check(self):
        arrival = validate_arrival(arrival_spec(wafer_map_supplied=False))
        keys = [r["check"] for r in applicable_checks(arrival)]
        self.assertNotIn("wafer-map-cross-check", keys)

    def test_every_applicable_check_carries_a_reason(self):
        for record in applicable_checks(validate_arrival(arrival_spec())):
            self.assertTrue(record["reason"])


class ValidateResultsTests(unittest.TestCase):
    def setUp(self):
        self.arrival = validate_arrival(arrival_spec())
        self.applicable = applicable_checks(self.arrival)

    def test_complete_result_set_is_accepted(self):
        results = validate_results(clean_results(), self.applicable)
        self.assertNotIn("quantity-reconciliation", results)

    def test_missing_outcome_for_an_applicable_check_rejected(self):
        results = clean_results()
        del results["identity-and-lot-match"]
        with self.assertRaises(ValueError):
            validate_results(results, self.applicable)

    def test_outcome_for_a_computed_check_rejected(self):
        results = clean_results()
        results["quantity-reconciliation"] = "pass"
        with self.assertRaises(ValueError):
            validate_results(results, self.applicable)

    def test_outcome_for_an_inapplicable_check_rejected(self):
        arrival = validate_arrival(arrival_spec(arrived_sealed=False))
        applicable = applicable_checks(arrival)
        results = clean_results(arrival_spec(arrived_sealed=False))
        results["humidity-indicator-reading"] = "pass"
        with self.assertRaises(ValueError):
            validate_results(results, applicable)

    def test_unknown_check_rejected(self):
        results = clean_results()
        results["taste-test"] = "pass"
        with self.assertRaises(ValueError):
            validate_results(results, self.applicable)

    def test_unknown_outcome_rejected(self):
        results = clean_results(override={"packaging-integrity": "probably-fine"})
        with self.assertRaises(ValueError):
            validate_results(results, self.applicable)

    def test_non_mapping_results_rejected(self):
        with self.assertRaises(ValueError):
            validate_results([("packaging-integrity", "pass")], self.applicable)


class OutcomeAndDispositionTests(unittest.TestCase):
    def test_quantity_outcome_is_computed_not_reported(self):
        arrival = validate_arrival(arrival_spec(counted_quantity=480))
        outcomes = check_outcomes(arrival, clean_results())
        quantity = [o for o in outcomes if o["check"] == "quantity-reconciliation"][0]
        self.assertEqual(quantity["outcome"], "fail")
        self.assertEqual(quantity["detail"], "packing-list-mismatch")

    def test_clean_arrival_is_accepted_and_released(self):
        result = assess_incoming_inspection(inspection_spec())
        self.assertEqual(result["disposition"], "accept")
        self.assertTrue(result["release_to_production"])
        self.assertEqual(result["findings"], [])

    def test_critical_failure_rejects_the_batch(self):
        result = assess_incoming_inspection(
            inspection_spec(results_override={"identity-and-lot-match": "fail"})
        )
        self.assertEqual(result["disposition"], "reject")
        self.assertFalse(result["release_to_production"])

    def test_skipped_critical_check_also_rejects(self):
        result = assess_incoming_inspection(
            inspection_spec(results_override={"visual-sample-inspection":
                                              "not-performed"})
        )
        self.assertEqual(result["disposition"], "reject")
        self.assertTrue(any("not performed" in f for f in result["findings"]))

    def test_major_failure_quarantines_the_batch(self):
        result = assess_incoming_inspection(
            inspection_spec(results_override={"seal-and-desiccant-condition": "fail"})
        )
        self.assertEqual(result["disposition"], "quarantine")

    def test_quantity_mismatch_quarantines_without_an_inspector_saying_so(self):
        result = assess_incoming_inspection(inspection_spec(counted_quantity=480))
        self.assertEqual(result["disposition"], "quarantine")
        self.assertEqual(result["quantities"]["status"], "packing-list-mismatch")

    def test_minor_failure_is_a_deviation_not_a_quarantine(self):
        result = assess_incoming_inspection(
            inspection_spec(results_override={"wafer-map-cross-check": "fail"})
        )
        self.assertEqual(result["disposition"], "accept-with-deviation")
        self.assertFalse(result["release_to_production"])

    def test_worst_severity_governs_when_several_fail(self):
        result = assess_incoming_inspection(
            inspection_spec(
                results_override={
                    "wafer-map-cross-check": "fail",
                    "seal-and-desiccant-condition": "fail",
                    "packaging-integrity": "fail",
                }
            )
        )
        self.assertEqual(result["disposition"], "reject")

    def test_findings_are_ordered_worst_severity_first(self):
        result = assess_incoming_inspection(
            inspection_spec(
                results_override={
                    "wafer-map-cross-check": "fail",
                    "packaging-integrity": "fail",
                }
            )
        )
        self.assertTrue(result["findings"][0].startswith("critical"))

    def test_pass_fraction_counts_every_applicable_check(self):
        result = assess_incoming_inspection(inspection_spec())
        self.assertAlmostEqual(result["pass_fraction"], 1.0, places=9)
        self.assertEqual(result["passed_checks"], len(result["outcomes"]))

    def test_disposition_rejects_an_empty_outcome_set(self):
        with self.assertRaises(ValueError):
            disposition_for([])

    def test_disposition_rejects_an_unknown_severity(self):
        with self.assertRaises(ValueError):
            disposition_for([{"severity": "cosmetic", "outcome": "fail"}])

    def test_findings_reject_a_non_sequence(self):
        with self.assertRaises(ValueError):
            inspection_findings({"check": "packaging-integrity"})

    def test_assessment_requires_the_results_key(self):
        with self.assertRaises(ValueError):
            assess_incoming_inspection(arrival_spec())

    def test_check_outcomes_rejects_a_missing_outcome(self):
        arrival = validate_arrival(arrival_spec())
        with self.assertRaises(ValueError):
            check_outcomes(arrival, {})


if __name__ == "__main__":
    unittest.main()
