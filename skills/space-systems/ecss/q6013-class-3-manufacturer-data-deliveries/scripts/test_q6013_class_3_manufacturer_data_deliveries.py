"""Contract tests for the clause 6.3.11 class 3 manufacturer data deliveries.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused delivery policy,
a blank lot identity, a waiver reaching a core item or carrying no recorded
acceptance, a folder item the lot does not owe, the in-full, reduced,
unidentified, mismatched, unfranchised and absent dispositions, the credit
floor a core item owes, the provenance-weighted completeness against its
floor and the marginal band above it.
"""

import unittest

from q6013_class_3_manufacturer_data_deliveries_logic import (
    CORE_ITEMS,
    DEFAULT_DELIVERY_POLICY,
    DISPOSITION_ABSENT,
    DISPOSITION_IN_FULL,
    DISPOSITION_LOT_MISMATCH,
    DISPOSITION_REDUCED,
    DISPOSITION_UNFRANCHISED,
    DISPOSITION_UNIDENTIFIED,
    ITEM_WEIGHTS,
    PACKAGE_ACCEPTED,
    PACKAGE_ACCEPTED_WITH_ACTIONS,
    PACKAGE_REFUSED_CORE_ITEM_MISSING,
    PACKAGE_REFUSED_CORE_ITEM_UNDERCREDITED,
    PACKAGE_REFUSED_LOT_MISMATCH,
    PACKAGE_REFUSED_SHORT_OF_FLOOR,
    PACKAGE_REFUSED_UNFRANCHISED_SOURCE,
    PROVENANCE_CREDIT,
    REGISTERED_ITEMS,
    SUPPORTING_ITEMS,
    UNFRANCHISED_SOURCE,
    assess_data_package,
    dispose_item,
    item_weight,
    lot_identity,
    meets_floor,
    owed_item_set,
    provenance_credit,
    validate_delivered_items,
    validate_delivery_policy,
    weighted_completeness,
)

LOT = "LOT-4471"
DATE_CODE = "2419"
REFERENCE = "LOT-4471/2419"


def _policy(**overrides):
    policy = dict(DEFAULT_DELIVERY_POLICY)
    policy.update(overrides)
    return policy


def _record(item, provenance="manufacturer-issued", reference=REFERENCE, issue="A"):
    return {
        "item": item,
        "provenance": provenance,
        "lot_reference": reference,
        "issue": issue,
    }


def _folder(drop=(), **overrides):
    records = []
    for name in owed_item_set():
        if name in drop:
            continue
        if name in overrides:
            records.append(_record(name, **overrides[name]))
        else:
            records.append(_record(name))
    return records


def _case(**overrides):
    case = {
        "lot_identifier": LOT,
        "date_code": DATE_CODE,
        "delivered_items": _folder(),
        "waivers": {},
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_delivery_policy(DEFAULT_DELIVERY_POLICY), DEFAULT_DELIVERY_POLICY
        )

    def test_policy_missing_a_key_is_refused(self):
        policy = dict(DEFAULT_DELIVERY_POLICY)
        del policy["completeness_floor"]
        with self.assertRaises(ValueError):
            validate_delivery_policy(policy)

    def test_a_zero_completeness_floor_is_refused(self):
        with self.assertRaises(ValueError):
            validate_delivery_policy(_policy(completeness_floor=0.0))

    def test_a_band_reaching_past_a_complete_package_is_refused(self):
        with self.assertRaises(ValueError):
            validate_delivery_policy(_policy(completeness_floor=0.98, marginal_band=0.2))

    def test_a_core_floor_under_the_package_floor_is_refused(self):
        with self.assertRaises(ValueError):
            validate_delivery_policy(_policy(core_credit_floor=0.5))

    def test_a_non_mapping_policy_is_refused(self):
        with self.assertRaises(ValueError):
            validate_delivery_policy(["completeness_floor"])


class IdentityTests(unittest.TestCase):
    def test_the_identity_joins_the_lot_and_the_date_code(self):
        self.assertEqual(lot_identity(LOT, DATE_CODE)["reference"], REFERENCE)

    def test_a_blank_lot_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            lot_identity("   ", DATE_CODE)

    def test_a_blank_date_code_is_refused_where_the_policy_asks_for_one(self):
        with self.assertRaises(ValueError):
            lot_identity(LOT, "")

    def test_a_policy_may_stand_the_identity_on_the_lot_alone(self):
        identity = lot_identity(LOT, "", _policy(require_date_code=False))
        self.assertEqual(identity["reference"], "LOT-4471/no-date-code")


class RegisterTests(unittest.TestCase):
    def test_every_registered_item_carries_a_weight(self):
        self.assertEqual(set(ITEM_WEIGHTS), set(REGISTERED_ITEMS))

    def test_the_core_and_supporting_items_partition_the_register(self):
        self.assertEqual(set(CORE_ITEMS) | set(SUPPORTING_ITEMS), set(REGISTERED_ITEMS))
        self.assertFalse(set(CORE_ITEMS) & set(SUPPORTING_ITEMS))

    def test_every_registered_provenance_carries_a_credit(self):
        for name, credit in PROVENANCE_CREDIT.items():
            self.assertAlmostEqual(provenance_credit(name), credit, places=9)

    def test_an_unfranchised_source_is_not_a_credit_level(self):
        with self.assertRaises(ValueError):
            provenance_credit(UNFRANCHISED_SOURCE)

    def test_an_unregistered_provenance_is_refused(self):
        with self.assertRaises(ValueError):
            provenance_credit("a pdf someone emailed")

    def test_an_unregistered_item_has_no_weight(self):
        with self.assertRaises(ValueError):
            item_weight("a nice letter")


class OwedSetTests(unittest.TestCase):
    def test_the_owed_set_opens_with_the_core_items(self):
        self.assertEqual(owed_item_set()[: len(CORE_ITEMS)], list(CORE_ITEMS))

    def test_a_recorded_acceptance_drops_a_supporting_item(self):
        owed = owed_item_set({"material-and-substance-declaration": "PA-12"})
        self.assertNotIn("material-and-substance-declaration", owed)
        self.assertEqual(len(owed), len(REGISTERED_ITEMS) - 1)

    def test_a_core_item_cannot_be_waived(self):
        with self.assertRaises(ValueError):
            owed_item_set({"certificate-of-conformity": "PA-12"})

    def test_a_waiver_with_no_recorded_acceptance_is_refused(self):
        with self.assertRaises(ValueError):
            owed_item_set({"change-notification-subscription": "  "})

    def test_a_waiver_naming_an_unregistered_item_is_refused(self):
        with self.assertRaises(ValueError):
            owed_item_set({"a nice letter": "PA-12"})

    def test_a_non_mapping_waiver_set_is_refused(self):
        with self.assertRaises(ValueError):
            owed_item_set(["material-and-substance-declaration"])


class DeliveredRecordTests(unittest.TestCase):
    def test_a_duplicated_item_is_refused(self):
        records = _folder()
        records.append(_record("certificate-of-conformity"))
        with self.assertRaises(ValueError):
            validate_delivered_items(records, owed_item_set())

    def test_an_unregistered_delivered_item_is_refused(self):
        records = _folder()
        records.append(_record("a nice letter"))
        with self.assertRaises(ValueError):
            validate_delivered_items(records, owed_item_set())

    def test_a_record_missing_a_key_is_refused(self):
        records = _folder()
        del records[0]["issue"]
        with self.assertRaises(ValueError):
            validate_delivered_items(records, owed_item_set())

    def test_a_non_mapping_record_is_refused(self):
        with self.assertRaises(ValueError):
            validate_delivered_items(["certificate-of-conformity"], owed_item_set())

    def test_an_item_the_lot_does_not_owe_is_recorded_not_credited(self):
        owed = owed_item_set({"change-notification-subscription": "PA-12"})
        checked = validate_delivered_items(_folder(), owed)
        self.assertEqual(checked["unowed"], ["change-notification-subscription"])


class DispositionTests(unittest.TestCase):
    def setUp(self):
        self.identity = lot_identity(LOT, DATE_CODE)

    def test_a_manufacturer_issued_item_is_credited_in_full(self):
        outcome = dispose_item(_record("certificate-of-conformity"), self.identity)
        self.assertEqual(outcome["disposition"], DISPOSITION_IN_FULL)
        self.assertAlmostEqual(outcome["credit"], 1.0, places=9)

    def test_an_archived_published_datasheet_is_credited_at_a_reduced_rate(self):
        outcome = dispose_item(
            _record(
                "part-datasheet-or-specification",
                provenance="published-datasheet-archived",
            ),
            self.identity,
        )
        self.assertEqual(outcome["disposition"], DISPOSITION_REDUCED)
        self.assertAlmostEqual(outcome["credit"], 0.6, places=9)

    def test_an_unarchived_published_datasheet_credits_nothing(self):
        outcome = dispose_item(
            _record(
                "part-datasheet-or-specification",
                provenance="published-datasheet-not-archived",
            ),
            self.identity,
        )
        self.assertEqual(outcome["disposition"], DISPOSITION_ABSENT)
        self.assertAlmostEqual(outcome["credit"], 0.0, places=9)

    def test_an_item_with_no_issue_reference_is_unidentified(self):
        outcome = dispose_item(
            _record("electrical-test-summary", issue="   "), self.identity
        )
        self.assertEqual(outcome["disposition"], DISPOSITION_UNIDENTIFIED)

    def test_an_item_offered_against_another_lot_is_mismatched(self):
        outcome = dispose_item(
            _record("electrical-test-summary", reference="LOT-9999/2419"), self.identity
        )
        self.assertEqual(outcome["disposition"], DISPOSITION_LOT_MISMATCH)

    def test_an_unfranchised_record_is_disposed_not_scored(self):
        outcome = dispose_item(
            _record("certificate-of-conformity", provenance=UNFRANCHISED_SOURCE),
            self.identity,
        )
        self.assertEqual(outcome["disposition"], DISPOSITION_UNFRANCHISED)
        self.assertAlmostEqual(outcome["credit"], 0.0, places=9)

    def test_an_absent_item_disposes_as_absent(self):
        outcome = dispose_item(None, self.identity)
        self.assertEqual(outcome["disposition"], DISPOSITION_ABSENT)


class CompletenessTests(unittest.TestCase):
    def test_a_folder_delivered_in_full_scores_unity(self):
        owed = owed_item_set()
        credits = {name: 1.0 for name in owed}
        self.assertAlmostEqual(weighted_completeness(credits, owed), 1.0, places=9)

    def test_an_absent_item_lowers_the_fraction_rather_than_leaving_it(self):
        owed = owed_item_set()
        credits = {name: 1.0 for name in owed}
        credits["material-and-substance-declaration"] = 0.0
        self.assertAlmostEqual(
            weighted_completeness(credits, owed), 5.4 / 5.8, places=9
        )

    def test_a_waiver_shortens_the_owed_set_where_an_absence_does_not(self):
        waived = owed_item_set({"material-and-substance-declaration": "PA-12"})
        credits = {name: 1.0 for name in waived}
        self.assertAlmostEqual(weighted_completeness(credits, waived), 1.0, places=9)

    def test_a_credit_outside_zero_to_unity_is_refused(self):
        owed = owed_item_set()
        credits = {name: 1.0 for name in owed}
        credits["electrical-test-summary"] = 1.4
        with self.assertRaises(ValueError):
            weighted_completeness(credits, owed)

    def test_an_empty_owed_set_is_refused(self):
        with self.assertRaises(ValueError):
            weighted_completeness({}, [])

    def test_a_fraction_landing_exactly_on_its_floor_is_inside_it(self):
        self.assertTrue(meets_floor(0.75, 0.75))

    def test_a_fraction_under_its_floor_is_outside_it(self):
        self.assertFalse(meets_floor(0.7, 0.75))


class AssessmentTests(unittest.TestCase):
    def test_a_folder_delivered_in_full_meets_the_class_three_scope(self):
        result = assess_data_package(_case())
        self.assertEqual(result["verdict"], PACKAGE_ACCEPTED)
        self.assertTrue(result["accepted"])
        self.assertAlmostEqual(result["completeness"], 1.0, places=9)

    def test_an_unfranchised_record_closes_the_assessment_first(self):
        case = _case(
            delivered_items=_folder(
                **{"electrical-test-summary": {"provenance": UNFRANCHISED_SOURCE}}
            )
        )
        self.assertEqual(
            assess_data_package(case)["verdict"], PACKAGE_REFUSED_UNFRANCHISED_SOURCE
        )

    def test_a_folder_covering_another_lot_is_refused(self):
        case = _case(
            delivered_items=_folder(
                **{"certificate-of-conformity": {"reference": "LOT-9999/2419"}}
            )
        )
        self.assertEqual(
            assess_data_package(case)["verdict"], PACKAGE_REFUSED_LOT_MISMATCH
        )

    def test_an_absent_core_item_is_refused(self):
        case = _case(delivered_items=_folder(drop=("certificate-of-conformity",)))
        result = assess_data_package(case)
        self.assertEqual(result["verdict"], PACKAGE_REFUSED_CORE_ITEM_MISSING)
        self.assertEqual(
            result["dispositions"]["certificate-of-conformity"], DISPOSITION_ABSENT
        )

    def test_a_core_item_with_no_issue_reference_is_refused(self):
        case = _case(
            delivered_items=_folder(**{"certificate-of-conformity": {"issue": ""}})
        )
        self.assertEqual(
            assess_data_package(case)["verdict"], PACKAGE_REFUSED_CORE_ITEM_MISSING
        )

    def test_published_material_cannot_stand_in_for_a_core_item(self):
        case = _case(
            delivered_items=_folder(
                **{
                    "certificate-of-conformity": {
                        "provenance": "published-datasheet-archived"
                    }
                }
            )
        )
        self.assertEqual(
            assess_data_package(case)["verdict"],
            PACKAGE_REFUSED_CORE_ITEM_UNDERCREDITED,
        )

    def test_a_core_item_landing_exactly_on_the_core_credit_floor_is_accepted(self):
        case = _case(
            delivered_items=_folder(
                **{
                    "certificate-of-conformity": {
                        "provenance": "franchised-distributor-issued"
                    }
                }
            )
        )
        result = assess_data_package(case)
        self.assertEqual(result["verdict"], PACKAGE_ACCEPTED)
        self.assertAlmostEqual(result["completeness"], 5.6 / 5.8, places=9)

    def test_a_completeness_inside_the_marginal_band_is_accepted_with_actions(self):
        case = _case(
            delivered_items=_folder(
                drop=("electrical-test-summary", "moisture-sensitivity-declaration")
            )
        )
        result = assess_data_package(case)
        self.assertEqual(result["verdict"], PACKAGE_ACCEPTED_WITH_ACTIONS)
        self.assertTrue(result["accepted"])
        self.assertAlmostEqual(result["completeness"], 4.4 / 5.8, places=9)

    def test_a_completeness_under_the_floor_is_refused(self):
        case = _case(
            delivered_items=_folder(
                drop=(
                    "electrical-test-summary",
                    "moisture-sensitivity-declaration",
                    "material-and-substance-declaration",
                )
            )
        )
        result = assess_data_package(case)
        self.assertEqual(result["verdict"], PACKAGE_REFUSED_SHORT_OF_FLOOR)
        self.assertAlmostEqual(result["completeness"], 4.0 / 5.8, places=9)

    def test_a_recorded_waiver_rescues_a_folder_an_absence_would_have_weakened(self):
        dropped = ("electrical-test-summary", "moisture-sensitivity-declaration")
        waived = assess_data_package(
            _case(
                delivered_items=_folder(drop=dropped),
                waivers={name: "PA-12" for name in dropped},
            )
        )
        self.assertEqual(waived["verdict"], PACKAGE_ACCEPTED)
        self.assertAlmostEqual(waived["completeness"], 1.0, places=9)

    def test_an_unowed_item_is_reported_without_making_up_the_numbers(self):
        case = _case(waivers={"change-notification-subscription": "PA-12"})
        result = assess_data_package(case)
        self.assertEqual(result["unowed_items"], ["change-notification-subscription"])
        self.assertEqual(result["verdict"], PACKAGE_ACCEPTED)

    def test_a_case_missing_a_required_key_is_refused(self):
        case = _case()
        del case["waivers"]
        with self.assertRaises(ValueError):
            assess_data_package(case)

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_data_package(["lot_identifier"])

    def test_every_verdict_carries_at_least_one_finding(self):
        for case in (
            _case(),
            _case(delivered_items=_folder(drop=("certificate-of-conformity",))),
            _case(
                delivered_items=_folder(
                    drop=("electrical-test-summary", "moisture-sensitivity-declaration")
                )
            ),
        ):
            self.assertTrue(assess_data_package(case)["findings"])


if __name__ == "__main__":
    unittest.main()
