#!/usr/bin/env python3
"""Contract test for per-lot SCA qualification, clause 6.4.1 (offline)."""

import copy
import unittest

from e2008_sca_qualification_general_logic import (
    CONFIGURATION_KEYS,
    DEFAULT_LOT_QUALIFICATION_POLICY,
    LOT_CAMPAIGN_INCOMPLETE,
    LOT_COUPON_PROVENANCE_MISMATCH,
    LOT_NO_CAMPAIGN,
    LOT_QUALIFIED,
    PROCUREMENT_FULLY_QUALIFIED,
    PROCUREMENT_NOT_FULLY_QUALIFIED,
    REQUIRED_LOT_ACTIVITIES,
    assess_procurement_lot,
    assess_procurement_qualification,
    campaign_completeness,
    configuration_delta,
    heritage_admissibility,
    lot_configuration,
    required_lot_activities,
    validate_lot_qualification_policy,
)


def _campaign(lot_id, **overrides):
    campaign = {
        "coupon_lot_id": lot_id,
        "coupon_count": DEFAULT_LOT_QUALIFICATION_POLICY["min_coupons_per_lot"],
        "closed": True,
        "activities": list(REQUIRED_LOT_ACTIVITIES),
    }
    campaign.update(overrides)
    return campaign


def _lot(lot_id="lot-a", **overrides):
    lot = {
        "lot_id": lot_id,
        "supplier": "cell-supplier-one",
        "assembly_type": "triple-junction-sca",
        "process_baseline": "baseline-2026-a",
        "campaign": _campaign(lot_id),
    }
    lot.update(overrides)
    return lot


def _procurement(*lots):
    return {"lots": list(lots) or [_lot("lot-a"), _lot("lot-b")]}


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_lot_qualification_policy(DEFAULT_LOT_QUALIFICATION_POLICY),
            DEFAULT_LOT_QUALIFICATION_POLICY,
        )

    def test_default_policy_does_not_admit_heritage(self):
        self.assertFalse(
            DEFAULT_LOT_QUALIFICATION_POLICY["admit_heritage_in_place_of_campaign"]
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot_qualification_policy("qualify everything")

    def test_zero_coupon_minimum_rejected(self):
        broken = copy.deepcopy(DEFAULT_LOT_QUALIFICATION_POLICY)
        broken["min_coupons_per_lot"] = 0
        with self.assertRaises(ValueError):
            validate_lot_qualification_policy(broken)

    def test_non_boolean_heritage_switch_rejected(self):
        broken = copy.deepcopy(DEFAULT_LOT_QUALIFICATION_POLICY)
        broken["admit_heritage_in_place_of_campaign"] = "yes"
        with self.assertRaises(ValueError):
            validate_lot_qualification_policy(broken)


class ConfigurationTests(unittest.TestCase):
    def test_required_activity_set_is_returned_as_a_tuple_copy(self):
        first = required_lot_activities()
        self.assertEqual(first, REQUIRED_LOT_ACTIVITIES)
        self.assertIsInstance(first, tuple)

    def test_configuration_reads_every_identity_attribute(self):
        configuration = lot_configuration(_lot())
        self.assertEqual(sorted(configuration), sorted(CONFIGURATION_KEYS))

    def test_identical_lots_have_no_configuration_delta(self):
        self.assertEqual(configuration_delta(_lot("lot-a"), _lot("lot-b")), [])

    def test_a_changed_process_baseline_shows_in_the_delta(self):
        other = _lot("lot-b", process_baseline="baseline-2026-b")
        self.assertEqual(configuration_delta(_lot("lot-a"), other), ["process_baseline"])

    def test_a_changed_supplier_and_type_both_show_in_the_delta(self):
        other = _lot("lot-b", supplier="cell-supplier-two", assembly_type="thin-film-sca")
        self.assertEqual(
            configuration_delta(_lot("lot-a"), other),
            ["assembly_type", "supplier"],
        )

    def test_lot_missing_an_identity_attribute_rejected(self):
        lot = _lot()
        del lot["supplier"]
        with self.assertRaises(ValueError):
            lot_configuration(lot)

    def test_blank_identity_attribute_rejected(self):
        with self.assertRaises(ValueError):
            lot_configuration(_lot(supplier="  "))


class CampaignTests(unittest.TestCase):
    def test_full_campaign_is_complete(self):
        result = campaign_completeness(_campaign("lot-a"), "lot-a")
        self.assertTrue(result["complete"])
        self.assertTrue(result["coupon_provenance_matches"])
        self.assertEqual(result["findings"], [])

    def test_campaign_on_another_lots_coupons_fails_provenance(self):
        result = campaign_completeness(_campaign("lot-z"), "lot-a")
        self.assertFalse(result["coupon_provenance_matches"])
        self.assertTrue(any("drawn from lot" in f for f in result["findings"]))

    def test_campaign_missing_an_activity_is_incomplete(self):
        activities = [a for a in REQUIRED_LOT_ACTIVITIES if a != "sca-humidity-exposure"]
        result = campaign_completeness(
            _campaign("lot-a", activities=activities), "lot-a"
        )
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing_activities"], ["sca-humidity-exposure"])

    def test_campaign_on_too_few_coupons_is_incomplete(self):
        result = campaign_completeness(_campaign("lot-a", coupon_count=1), "lot-a")
        self.assertFalse(result["coupons_sufficient"])
        self.assertTrue(any("against a required" in f for f in result["findings"]))

    def test_coupon_count_exactly_on_the_minimum_is_sufficient(self):
        minimum = DEFAULT_LOT_QUALIFICATION_POLICY["min_coupons_per_lot"]
        result = campaign_completeness(_campaign("lot-a", coupon_count=minimum), "lot-a")
        self.assertEqual(result["coupon_count"], result["required_coupon_count"])
        self.assertTrue(result["coupons_sufficient"])

    def test_open_campaign_is_incomplete_under_the_default_policy(self):
        result = campaign_completeness(_campaign("lot-a", closed=False), "lot-a")
        self.assertFalse(result["complete"])
        self.assertTrue(any("still open" in f for f in result["findings"]))

    def test_a_policy_may_accept_an_open_campaign(self):
        policy = copy.deepcopy(DEFAULT_LOT_QUALIFICATION_POLICY)
        policy["require_campaign_closed"] = False
        result = campaign_completeness(_campaign("lot-a", closed=False), "lot-a", policy)
        self.assertTrue(result["complete"])

    def test_unknown_activity_rejected(self):
        activities = list(REQUIRED_LOT_ACTIVITIES) + ["sca-bake-out"]
        with self.assertRaises(ValueError):
            campaign_completeness(_campaign("lot-a", activities=activities), "lot-a")

    def test_repeated_activity_rejected(self):
        activities = list(REQUIRED_LOT_ACTIVITIES) + ["sca-thermal-cycling"]
        with self.assertRaises(ValueError):
            campaign_completeness(_campaign("lot-a", activities=activities), "lot-a")

    def test_non_mapping_campaign_rejected(self):
        with self.assertRaises(ValueError):
            campaign_completeness("closed", "lot-a")

    def test_negative_coupon_count_rejected(self):
        with self.assertRaises(ValueError):
            campaign_completeness(_campaign("lot-a", coupon_count=-2), "lot-a")


class HeritageTests(unittest.TestCase):
    def test_a_lot_with_no_claim_reports_none(self):
        result = heritage_admissibility(_lot(), {})
        self.assertFalse(result["claimed"])
        self.assertFalse(result["admitted"])

    def test_a_matching_claim_is_refused_under_the_default_policy(self):
        reference = _lot("lot-a")
        claimant = _lot("lot-b", campaign=None, heritage_lot_id="lot-a")
        result = heritage_admissibility(
            claimant, {"lot-a": reference, "lot-b": claimant}
        )
        self.assertTrue(result["configuration_matches"])
        self.assertFalse(result["admitted"])
        self.assertTrue(any("owes a" in f for f in result["findings"]))

    def test_a_matching_claim_is_admitted_under_a_permissive_policy(self):
        policy = copy.deepcopy(DEFAULT_LOT_QUALIFICATION_POLICY)
        policy["admit_heritage_in_place_of_campaign"] = True
        reference = _lot("lot-a")
        claimant = _lot("lot-b", campaign=None, heritage_lot_id="lot-a")
        result = heritage_admissibility(
            claimant, {"lot-a": reference, "lot-b": claimant}, policy
        )
        self.assertTrue(result["admitted"])

    def test_a_claim_across_a_configuration_change_is_never_admitted(self):
        policy = copy.deepcopy(DEFAULT_LOT_QUALIFICATION_POLICY)
        policy["admit_heritage_in_place_of_campaign"] = True
        reference = _lot("lot-a")
        claimant = _lot(
            "lot-b",
            campaign=None,
            heritage_lot_id="lot-a",
            process_baseline="baseline-2026-b",
        )
        result = heritage_admissibility(
            claimant, {"lot-a": reference, "lot-b": claimant}, policy
        )
        self.assertEqual(result["configuration_delta"], ["process_baseline"])
        self.assertFalse(result["admitted"])

    def test_a_claim_on_an_undeclared_lot_is_reported(self):
        claimant = _lot("lot-b", campaign=None, heritage_lot_id="lot-missing")
        result = heritage_admissibility(claimant, {"lot-b": claimant})
        self.assertFalse(result["configuration_matches"])
        self.assertTrue(
            any("which the procurement does not declare" in f for f in result["findings"])
        )

    def test_a_claim_on_itself_rejected(self):
        claimant = _lot("lot-b", campaign=None, heritage_lot_id="lot-b")
        with self.assertRaises(ValueError):
            heritage_admissibility(claimant, {"lot-b": claimant})

    def test_non_mapping_index_rejected(self):
        with self.assertRaises(ValueError):
            heritage_admissibility(_lot(), ["lot-a"])


class LotVerdictTests(unittest.TestCase):
    def test_lot_with_its_own_closed_campaign_is_qualified(self):
        record = assess_procurement_lot(_lot())
        self.assertEqual(record["verdict"], LOT_QUALIFIED)
        self.assertTrue(record["qualified"])
        self.assertEqual(record["findings"], [])

    def test_lot_with_no_campaign_is_not_qualified(self):
        record = assess_procurement_lot(_lot(campaign=None))
        self.assertEqual(record["verdict"], LOT_NO_CAMPAIGN)
        self.assertTrue(any("no qualification campaign" in f for f in record["findings"]))

    def test_provenance_mismatch_outranks_an_incomplete_activity_set(self):
        campaign = _campaign(
            "lot-z", activities=list(REQUIRED_LOT_ACTIVITIES)[:2]
        )
        record = assess_procurement_lot(_lot(campaign=campaign))
        self.assertEqual(record["verdict"], LOT_COUPON_PROVENANCE_MISMATCH)

    def test_short_activity_set_is_an_incomplete_campaign(self):
        campaign = _campaign("lot-a", activities=list(REQUIRED_LOT_ACTIVITIES)[:4])
        record = assess_procurement_lot(_lot(campaign=campaign))
        self.assertEqual(record["verdict"], LOT_CAMPAIGN_INCOMPLETE)

    def test_a_heritage_claim_does_not_qualify_a_lot_by_default(self):
        reference = _lot("lot-a")
        claimant = _lot("lot-b", campaign=None, heritage_lot_id="lot-a")
        record = assess_procurement_lot(
            claimant, {"lot-a": reference, "lot-b": claimant}
        )
        self.assertEqual(record["verdict"], LOT_NO_CAMPAIGN)
        self.assertFalse(record["qualified"])

    def test_a_permissive_policy_lets_a_matching_claim_qualify_a_lot(self):
        policy = copy.deepcopy(DEFAULT_LOT_QUALIFICATION_POLICY)
        policy["admit_heritage_in_place_of_campaign"] = True
        reference = _lot("lot-a")
        claimant = _lot("lot-b", campaign=None, heritage_lot_id="lot-a")
        record = assess_procurement_lot(
            claimant, {"lot-a": reference, "lot-b": claimant}, policy
        )
        self.assertEqual(record["verdict"], LOT_QUALIFIED)

    def test_lot_without_an_identifier_rejected(self):
        lot = _lot()
        lot["lot_id"] = ""
        with self.assertRaises(ValueError):
            assess_procurement_lot(lot)

    def test_non_mapping_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_procurement_lot("lot-a")


class ProcurementTests(unittest.TestCase):
    def test_procurement_where_every_lot_is_qualified_is_clean(self):
        result = assess_procurement_qualification(_procurement())
        self.assertEqual(result["verdict"], PROCUREMENT_FULLY_QUALIFIED)
        self.assertTrue(result["every_lot_qualified"])
        self.assertAlmostEqual(result["qualified_fraction"], 1.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_one_unqualified_lot_opens_the_procurement(self):
        result = assess_procurement_qualification(
            _procurement(_lot("lot-a"), _lot("lot-b", campaign=None))
        )
        self.assertEqual(result["verdict"], PROCUREMENT_NOT_FULLY_QUALIFIED)
        self.assertEqual(result["open_lot_ids"], ["lot-b"])
        self.assertAlmostEqual(result["qualified_fraction"], 0.5, places=9)

    def test_a_delivered_lot_nobody_declared_is_reported(self):
        case = _procurement(_lot("lot-a"))
        case["delivered_lot_ids"] = ["lot-a", "lot-ghost"]
        result = assess_procurement_qualification(case)
        self.assertEqual(result["undeclared_lot_ids"], ["lot-ghost"])
        self.assertEqual(result["verdict"], PROCUREMENT_NOT_FULLY_QUALIFIED)
        self.assertTrue(
            any(
                "declares no qualification status for it at all" in f
                for f in result["findings"]
            )
        )

    def test_a_declared_lot_that_is_not_delivered_does_not_open_the_procurement(self):
        case = _procurement(_lot("lot-a"), _lot("lot-b", campaign=None))
        case["delivered_lot_ids"] = ["lot-a"]
        result = assess_procurement_qualification(case)
        self.assertEqual(result["verdict"], PROCUREMENT_FULLY_QUALIFIED)
        self.assertEqual(result["open_lot_ids"], [])

    def test_procurement_groups_lots_by_verdict(self):
        grouped = assess_procurement_qualification(
            _procurement(
                _lot("lot-a"),
                _lot("lot-b", campaign=None),
                _lot("lot-c", campaign=_campaign("lot-z")),
            )
        )["grouped_by_verdict"]
        self.assertEqual(grouped[LOT_QUALIFIED], ["lot-a"])
        self.assertEqual(grouped[LOT_NO_CAMPAIGN], ["lot-b"])
        self.assertEqual(grouped[LOT_COUPON_PROVENANCE_MISMATCH], ["lot-c"])

    def test_procurement_collects_every_lot_finding(self):
        result = assess_procurement_qualification(
            _procurement(_lot("lot-a", campaign=_campaign("lot-a", closed=False)))
        )
        self.assertTrue(any("still open" in f for f in result["findings"]))

    def test_repeated_lot_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_procurement_qualification(_procurement(_lot("lot-a"), _lot("lot-a")))

    def test_empty_procurement_rejected(self):
        with self.assertRaises(ValueError):
            assess_procurement_qualification({"lots": []})

    def test_empty_delivered_list_rejected(self):
        case = _procurement(_lot("lot-a"))
        case["delivered_lot_ids"] = []
        with self.assertRaises(ValueError):
            assess_procurement_qualification(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_procurement_qualification([_lot()])


if __name__ == "__main__":
    unittest.main()
