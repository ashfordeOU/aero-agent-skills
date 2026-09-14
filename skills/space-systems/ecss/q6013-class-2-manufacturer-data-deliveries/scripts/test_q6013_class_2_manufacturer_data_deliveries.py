"""Contract tests for the clause 5.3.11 class 2 manufacturer data package.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused delivery policy,
an unregistered data item, an item carrying no reference or no issue, an
item matched to another lot, an item that arrived after lot acceptance, a
summary with no retained data behind it or with retention too short, an
on-request item called off and not delivered, and a package whose credited
completeness falls under its floor.
"""

import unittest

from q6013_class_2_manufacturer_data_deliveries_logic import (
    ABSENT,
    DEFAULT_DELIVERY_POLICY,
    DELIVERED_AS_SUMMARY,
    DELIVERED_IN_FULL,
    DELIVERED_LATE,
    IDENTIFIER_INCOMPLETE,
    KNOWN_ITEMS,
    LOT_MISMATCH,
    ON_REQUEST_ITEMS,
    PACKAGE_DELIVERED_LATE,
    PACKAGE_ITEMS_SHORT,
    PACKAGE_LOT_MISMATCH,
    PACKAGE_MEETS_CLASS_TWO_SCOPE,
    PACKAGE_NOT_DELIVERED,
    REQUIRED_ITEMS,
    SUMMARY_UNSUPPORTED,
    assess_manufacturer_data_deliveries,
    delivered_share,
    dispose_items,
    item_disposition,
    items_with_disposition,
    owed_items,
    validate_delivery_policy,
    validate_item_record,
    validate_lot_identity,
    weighted_completeness,
)

LOT = {"lot_identifier": "LOT-7741", "date_code": "2508"}


def _policy(**overrides):
    policy = dict(DEFAULT_DELIVERY_POLICY)
    policy.update(overrides)
    return policy


def _item(name, **overrides):
    record = {
        "item": name,
        "document_reference": "MDD-%s" % name[:6].upper(),
        "issue": "B",
        "lot_identifier": "LOT-7741",
        "date_code": "2508",
        "delivered_before_acceptance": True,
        "summary_only": False,
        "underlying_data_retained": False,
        "retention_months": 0,
    }
    record.update(overrides)
    return record


def _summary(name, **overrides):
    record = _item(
        name, summary_only=True, underlying_data_retained=True, retention_months=144
    )
    record.update(overrides)
    return record


def _full_package(summary_count=0):
    delivered = []
    for index, name in enumerate(REQUIRED_ITEMS):
        delivered.append(_summary(name) if index < summary_count else _item(name))
    return delivered


def _case(**overrides):
    case = {"lot": dict(LOT), "delivered": _full_package()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_delivery_policy(DEFAULT_DELIVERY_POLICY), DEFAULT_DELIVERY_POLICY
        )

    def test_policy_missing_a_key_is_refused(self):
        policy = dict(DEFAULT_DELIVERY_POLICY)
        del policy["summary_credit"]
        with self.assertRaises(ValueError):
            validate_delivery_policy(policy)

    def test_a_summary_credited_in_full_is_refused(self):
        with self.assertRaises(ValueError):
            validate_delivery_policy(_policy(summary_credit=1.0))

    def test_a_completeness_floor_above_the_delivered_floor_is_refused(self):
        with self.assertRaises(ValueError):
            validate_delivery_policy(
                _policy(min_delivered_share=0.6, min_weighted_completeness=0.9)
            )

    def test_a_band_reaching_the_completeness_floor_is_refused(self):
        with self.assertRaises(ValueError):
            validate_delivery_policy(_policy(marginal_band=0.8))

    def test_a_non_mapping_policy_is_refused(self):
        with self.assertRaises(ValueError):
            validate_delivery_policy(["summary_credit"])


class IdentityAndRecordTests(unittest.TestCase):
    def test_a_lot_identity_needs_both_parts(self):
        with self.assertRaises(ValueError):
            validate_lot_identity({"lot_identifier": "LOT-7741"})

    def test_a_blank_lot_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            validate_lot_identity({"lot_identifier": "  ", "date_code": "2508"})

    def test_an_unregistered_data_item_is_refused(self):
        with self.assertRaises(ValueError):
            validate_item_record(_item("a-folder-of-paper"))

    def test_a_record_missing_a_required_key_is_refused(self):
        record = _item("certificate-of-conformity")
        del record["summary_only"]
        with self.assertRaises(ValueError):
            validate_item_record(record)

    def test_a_non_boolean_timing_declaration_is_refused(self):
        with self.assertRaises(ValueError):
            validate_item_record(
                _item("certificate-of-conformity", delivered_before_acceptance="yes")
            )

    def test_the_two_item_registers_do_not_overlap(self):
        self.assertEqual(set(REQUIRED_ITEMS) & set(ON_REQUEST_ITEMS), set())
        self.assertEqual(KNOWN_ITEMS, set(REQUIRED_ITEMS) | set(ON_REQUEST_ITEMS))


class OwedItemTests(unittest.TestCase):
    def test_every_lot_owes_the_required_items(self):
        self.assertEqual(owed_items(), list(REQUIRED_ITEMS))

    def test_an_on_request_item_joins_the_set_when_called_off(self):
        owed = owed_items(["radiation-test-data"])
        self.assertIn("radiation-test-data", owed)
        self.assertEqual(len(owed), len(REQUIRED_ITEMS) + 1)

    def test_a_required_item_cannot_be_requested(self):
        with self.assertRaises(ValueError):
            owed_items(["certificate-of-conformity"])

    def test_an_unregistered_request_is_refused(self):
        with self.assertRaises(ValueError):
            owed_items(["a-nice-letter"])

    def test_a_repeated_request_is_owed_once(self):
        owed = owed_items(["radiation-test-data", "radiation-test-data"])
        self.assertEqual(len(owed), len(REQUIRED_ITEMS) + 1)


class DispositionTests(unittest.TestCase):
    def test_a_complete_identified_matching_item_is_delivered_in_full(self):
        self.assertEqual(
            item_disposition(_item("electrical-test-data"), LOT), DELIVERED_IN_FULL
        )

    def test_an_item_with_no_issue_is_identified_incompletely(self):
        self.assertEqual(
            item_disposition(_item("electrical-test-data", issue=""), LOT),
            IDENTIFIER_INCOMPLETE,
        )

    def test_an_item_with_no_reference_is_identified_incompletely(self):
        self.assertEqual(
            item_disposition(_item("electrical-test-data", document_reference=""), LOT),
            IDENTIFIER_INCOMPLETE,
        )

    def test_an_item_carrying_another_date_code_is_matched_to_another_lot(self):
        self.assertEqual(
            item_disposition(_item("electrical-test-data", date_code="2441"), LOT),
            LOT_MISMATCH,
        )

    def test_an_item_carrying_another_lot_identifier_is_matched_to_another_lot(self):
        self.assertEqual(
            item_disposition(_item("electrical-test-data", lot_identifier="LOT-9"), LOT),
            LOT_MISMATCH,
        )

    def test_an_item_arriving_after_acceptance_is_late(self):
        self.assertEqual(
            item_disposition(
                _item("electrical-test-data", delivered_before_acceptance=False), LOT
            ),
            DELIVERED_LATE,
        )

    def test_a_supported_summary_is_credited_as_a_summary(self):
        self.assertEqual(
            item_disposition(_summary("electrical-test-data"), LOT), DELIVERED_AS_SUMMARY
        )

    def test_a_summary_with_no_retained_data_is_unsupported(self):
        self.assertEqual(
            item_disposition(
                _summary("electrical-test-data", underlying_data_retained=False), LOT
            ),
            SUMMARY_UNSUPPORTED,
        )

    def test_a_summary_whose_retention_runs_out_too_soon_is_unsupported(self):
        self.assertEqual(
            item_disposition(_summary("electrical-test-data", retention_months=24), LOT),
            SUMMARY_UNSUPPORTED,
        )

    def test_a_summary_retained_exactly_to_the_floor_is_supported(self):
        floor = DEFAULT_DELIVERY_POLICY["min_retention_months"]
        self.assertEqual(
            item_disposition(_summary("electrical-test-data", retention_months=floor), LOT),
            DELIVERED_AS_SUMMARY,
        )

    def test_an_undelivered_owed_item_is_absent(self):
        resolved = dispose_items(_full_package()[:-1], LOT)
        self.assertEqual(
            resolved["dispositions"][REQUIRED_ITEMS[-1]], ABSENT
        )

    def test_an_item_delivered_twice_is_refused(self):
        delivered = _full_package() + [_item(REQUIRED_ITEMS[0])]
        with self.assertRaises(ValueError):
            dispose_items(delivered, LOT)

    def test_an_item_delivered_but_not_owed_is_recorded_not_credited(self):
        delivered = _full_package() + [_item("radiation-test-data")]
        resolved = dispose_items(delivered, LOT)
        self.assertEqual(resolved["delivered_not_owed"], ["radiation-test-data"])
        self.assertNotIn("radiation-test-data", resolved["dispositions"])


class ShareAndCompletenessTests(unittest.TestCase):
    def test_a_full_package_scores_unity_on_both_figures(self):
        resolved = dispose_items(_full_package(), LOT)
        owed = resolved["owed"]
        self.assertAlmostEqual(
            delivered_share(resolved["dispositions"], owed), 1.0, places=9
        )
        self.assertAlmostEqual(
            weighted_completeness(resolved["dispositions"], owed), 1.0, places=9
        )

    def test_a_summary_arrives_but_is_credited_below_a_full_delivery(self):
        resolved = dispose_items(_full_package(summary_count=2), LOT)
        owed = resolved["owed"]
        self.assertAlmostEqual(
            delivered_share(resolved["dispositions"], owed), 1.0, places=9
        )
        self.assertAlmostEqual(
            weighted_completeness(resolved["dispositions"], owed),
            6.4 / 7.0,
            places=9,
        )

    def test_an_absent_item_counts_as_nothing_rather_than_dropping_out(self):
        resolved = dispose_items(_full_package()[:-1], LOT)
        owed = resolved["owed"]
        self.assertAlmostEqual(
            weighted_completeness(resolved["dispositions"], owed), 6.0 / 7.0, places=9
        )

    def test_items_with_disposition_reports_in_the_owed_order(self):
        resolved = dispose_items(_full_package(summary_count=3), LOT)
        summaries = items_with_disposition(
            resolved["dispositions"], resolved["owed"], DELIVERED_AS_SUMMARY
        )
        self.assertEqual(summaries, list(REQUIRED_ITEMS[:3]))

    def test_an_empty_owed_set_is_refused(self):
        with self.assertRaises(ValueError):
            delivered_share({}, [])


class AssessmentTests(unittest.TestCase):
    def test_a_full_package_meets_the_class_scope(self):
        result = assess_manufacturer_data_deliveries(_case())
        self.assertEqual(result["verdict"], PACKAGE_MEETS_CLASS_TWO_SCOPE)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])

    def test_an_empty_delivery_is_no_package_at_all(self):
        result = assess_manufacturer_data_deliveries(_case(delivered=[]))
        self.assertEqual(result["verdict"], PACKAGE_NOT_DELIVERED)
        self.assertEqual(len(result["absent_items"]), len(REQUIRED_ITEMS))

    def test_one_item_matched_to_another_lot_stops_the_package(self):
        delivered = _full_package()
        delivered[2] = _item(REQUIRED_ITEMS[2], date_code="2441")
        result = assess_manufacturer_data_deliveries(_case(delivered=delivered))
        self.assertEqual(result["verdict"], PACKAGE_LOT_MISMATCH)
        self.assertEqual(result["mismatched_items"], [REQUIRED_ITEMS[2]])

    def test_an_item_arriving_after_acceptance_stops_the_package(self):
        delivered = _full_package()
        delivered[1] = _item(REQUIRED_ITEMS[1], delivered_before_acceptance=False)
        result = assess_manufacturer_data_deliveries(_case(delivered=delivered))
        self.assertEqual(result["verdict"], PACKAGE_DELIVERED_LATE)

    def test_an_unidentified_item_leaves_the_package_short(self):
        delivered = _full_package()
        delivered[0] = _item(REQUIRED_ITEMS[0], issue="")
        result = assess_manufacturer_data_deliveries(_case(delivered=delivered))
        self.assertEqual(result["verdict"], PACKAGE_ITEMS_SHORT)
        self.assertEqual(result["identifier_incomplete_items"], [REQUIRED_ITEMS[0]])

    def test_too_many_summaries_leave_the_package_short(self):
        result = assess_manufacturer_data_deliveries(
            _case(delivered=_full_package(summary_count=5))
        )
        self.assertEqual(result["verdict"], PACKAGE_ITEMS_SHORT)
        self.assertAlmostEqual(result["weighted_completeness"], 5.5 / 7.0, places=9)

    def test_a_completeness_landing_on_its_floor_is_inside_it(self):
        result = assess_manufacturer_data_deliveries(
            _case(delivered=_full_package(summary_count=len(REQUIRED_ITEMS))),
            _policy(min_weighted_completeness=0.7),
        )
        self.assertAlmostEqual(result["weighted_completeness"], 0.7, places=9)
        self.assertEqual(result["verdict"], PACKAGE_MEETS_CLASS_TWO_SCOPE)

    def test_a_package_just_above_its_floor_raises_an_advisory(self):
        result = assess_manufacturer_data_deliveries(
            _case(delivered=_full_package(summary_count=4))
        )
        self.assertEqual(result["verdict"], PACKAGE_MEETS_CLASS_TWO_SCOPE)
        self.assertEqual(len(result["advisories"]), 1)

    def test_an_unsupported_summary_is_not_a_delivery(self):
        delivered = _full_package()
        delivered[3] = _summary(REQUIRED_ITEMS[3], underlying_data_retained=False)
        result = assess_manufacturer_data_deliveries(_case(delivered=delivered))
        self.assertEqual(result["verdict"], PACKAGE_ITEMS_SHORT)
        self.assertEqual(result["unsupported_summary_items"], [REQUIRED_ITEMS[3]])

    def test_an_on_request_item_called_off_and_not_delivered_is_absent(self):
        result = assess_manufacturer_data_deliveries(
            _case(requested=["radiation-test-data"])
        )
        self.assertEqual(result["verdict"], PACKAGE_ITEMS_SHORT)
        self.assertEqual(result["absent_items"], ["radiation-test-data"])

    def test_an_on_request_item_called_off_and_delivered_completes_the_package(self):
        delivered = _full_package() + [_item("radiation-test-data")]
        result = assess_manufacturer_data_deliveries(
            _case(delivered=delivered, requested=["radiation-test-data"])
        )
        self.assertEqual(result["verdict"], PACKAGE_MEETS_CLASS_TWO_SCOPE)
        self.assertEqual(result["delivered_not_owed"], [])

    def test_every_failing_item_is_named_not_only_the_first(self):
        delivered = _full_package()[:-2]
        result = assess_manufacturer_data_deliveries(_case(delivered=delivered))
        self.assertEqual(result["absent_items"], list(REQUIRED_ITEMS[-2:]))
        self.assertEqual(len(result["findings"]), 2)

    def test_a_case_missing_the_lot_is_refused(self):
        case = _case()
        del case["lot"]
        with self.assertRaises(ValueError):
            assess_manufacturer_data_deliveries(case)

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_manufacturer_data_deliveries(["lot"])


if __name__ == "__main__":
    unittest.main()
