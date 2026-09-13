#!/usr/bin/env python3
"""Contract test for cell assembly visible defect departures (offline)."""

import copy
import unittest

from e2008_sca_visual_inspection_deviations_logic import (
    ACCEPT_AS_IS,
    AGREEMENT_STATES,
    DEFAULT_DEVIATION_POLICY,
    EVIDENCE_KINDS,
    PACKAGE_OPEN,
    PACKAGE_USABLE,
    PENDING,
    REFER,
    REJECT,
    REWORK,
    assess_deviation_package,
    assess_deviation_request,
    validate_deviation_policy,
)

BASE_REQUEST = {
    "deviation_id": "DEV-01",
    "criterion_id": "coverglass-chip-length",
    "criterion_limit": 0.20,
    "requested_limit": 0.24,
    "performance_debit": 0.001,
    "evidence": "test",
    "customer_agreement": "granted",
}


def _request(**overrides):
    request = copy.deepcopy(BASE_REQUEST)
    request.update(overrides)
    return request


def _package(requests=None, **overrides):
    package = {
        "assembly_id": "SCA-001",
        "deviations": requests if requests is not None else [_request()],
    }
    package.update(overrides)
    return package


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_deviation_policy(DEFAULT_DEVIATION_POLICY),
            DEFAULT_DEVIATION_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_deviation_policy("default")

    def test_unity_exceedance_ratio_rejected(self):
        broken = copy.deepcopy(DEFAULT_DEVIATION_POLICY)
        broken["max_exceedance_ratio"] = 1.0
        with self.assertRaises(ValueError):
            validate_deviation_policy(broken)

    def test_cumulative_allowance_below_the_single_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_DEVIATION_POLICY)
        broken["max_cumulative_performance_debit"] = 0.001
        with self.assertRaises(ValueError):
            validate_deviation_policy(broken)

    def test_unscored_evidence_kind_rejected(self):
        broken = copy.deepcopy(DEFAULT_DEVIATION_POLICY)
        del broken["evidence_strength"]["analysis"]
        with self.assertRaises(ValueError):
            validate_deviation_policy(broken)

    def test_debit_allowance_outside_the_unit_range_rejected(self):
        broken = copy.deepcopy(DEFAULT_DEVIATION_POLICY)
        broken["max_single_performance_debit"] = 1.4
        with self.assertRaises(ValueError):
            validate_deviation_policy(broken)

    def test_every_declared_evidence_kind_and_agreement_state_is_known(self):
        self.assertEqual(len(EVIDENCE_KINDS), 4)
        self.assertEqual(len(AGREEMENT_STATES), 4)


class SingleRequestTests(unittest.TestCase):
    def test_a_harmless_agreed_departure_is_usable_as_is(self):
        result = assess_deviation_request(_request())
        self.assertEqual(result["disposition"], ACCEPT_AS_IS)
        self.assertTrue(result["carried"])
        self.assertAlmostEqual(result["exceedance_ratio"], 1.2, places=9)

    def test_a_non_deviable_criterion_is_refused_on_presence(self):
        result = assess_deviation_request(_request(criterion_id="cracked-cell"))
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(
            any("no allowance at all" in reason for reason in result["reasons"])
        )

    def test_a_non_deviable_criterion_is_refused_before_the_numbers_matter(self):
        result = assess_deviation_request(
            _request(
                criterion_id="open-interconnector",
                requested_limit=0.201,
                performance_debit=0.0,
            )
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_an_exceedance_exactly_on_the_ratio_limit_survives(self):
        criterion = BASE_REQUEST["criterion_limit"]
        ratio = DEFAULT_DEVIATION_POLICY["max_exceedance_ratio"]
        result = assess_deviation_request(
            _request(requested_limit=criterion * ratio)
        )
        self.assertAlmostEqual(result["exceedance_ratio"], ratio, places=9)
        self.assertEqual(result["disposition"], ACCEPT_AS_IS)

    def test_an_exceedance_past_the_ratio_limit_is_a_different_article(self):
        result = assess_deviation_request(_request(requested_limit=0.60))
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(
            any("different article" in reason for reason in result["reasons"])
        )

    def test_a_debit_exactly_on_the_single_allowance_survives(self):
        allowance = DEFAULT_DEVIATION_POLICY["max_single_performance_debit"]
        result = assess_deviation_request(_request(performance_debit=allowance))
        self.assertAlmostEqual(result["performance_debit"], allowance, places=9)
        self.assertEqual(result["disposition"], ACCEPT_AS_IS)

    def test_a_costly_departure_is_refused_however_strong_the_evidence(self):
        result = assess_deviation_request(
            _request(performance_debit=0.04, evidence="test")
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_a_weak_case_goes_to_review_rather_than_to_the_customer(self):
        result = assess_deviation_request(
            _request(evidence="similarity-heritage")
        )
        self.assertEqual(result["disposition"], REFER)
        self.assertFalse(result["carried"])

    def test_evidence_exactly_on_the_strength_floor_is_accepted(self):
        policy = copy.deepcopy(DEFAULT_DEVIATION_POLICY)
        policy["min_evidence_strength"] = policy["evidence_strength"]["analysis"]
        result = assess_deviation_request(_request(evidence="analysis"), policy)
        self.assertEqual(result["disposition"], ACCEPT_AS_IS)

    def test_an_unrequested_agreement_leaves_the_departure_pending(self):
        result = assess_deviation_request(
            _request(customer_agreement="not-requested")
        )
        self.assertEqual(result["disposition"], PENDING)
        self.assertTrue(result["carried"])

    def test_a_requested_but_unanswered_agreement_is_still_pending(self):
        result = assess_deviation_request(_request(customer_agreement="requested"))
        self.assertEqual(result["disposition"], PENDING)

    def test_a_refused_agreement_sends_a_sound_case_to_rework(self):
        result = assess_deviation_request(_request(customer_agreement="refused"))
        self.assertEqual(result["disposition"], REWORK)
        self.assertFalse(result["carried"])

    def test_a_request_inside_the_criterion_is_not_a_departure(self):
        with self.assertRaises(ValueError):
            assess_deviation_request(_request(requested_limit=0.15))

    def test_a_request_exactly_at_the_criterion_is_not_a_departure(self):
        with self.assertRaises(ValueError):
            assess_deviation_request(_request(requested_limit=0.20))

    def test_unknown_evidence_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_deviation_request(_request(evidence="engineering-judgement"))

    def test_unknown_agreement_state_rejected(self):
        with self.assertRaises(ValueError):
            assess_deviation_request(_request(customer_agreement="verbal"))

    def test_negative_performance_debit_rejected(self):
        with self.assertRaises(ValueError):
            assess_deviation_request(_request(performance_debit=-0.01))

    def test_blank_deviation_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_deviation_request(_request(deviation_id="  "))

    def test_zero_criterion_limit_rejected(self):
        with self.assertRaises(ValueError):
            assess_deviation_request(_request(criterion_limit=0.0))


class PackageTests(unittest.TestCase):
    def test_a_package_of_agreed_harmless_departures_is_usable(self):
        result = assess_deviation_package(_package())
        self.assertEqual(result["verdict"], PACKAGE_USABLE)
        self.assertTrue(result["usable_as_is"])
        self.assertEqual(result["accept_as_is_ids"], ["DEV-01"])

    def test_an_assembly_with_no_departures_is_usable(self):
        result = assess_deviation_package(_package([]))
        self.assertEqual(result["verdict"], PACKAGE_USABLE)
        self.assertAlmostEqual(result["cumulative_performance_debit"], 0.0, places=12)

    def test_one_pending_departure_holds_the_whole_assembly(self):
        requests = [
            _request(deviation_id="DEV-01"),
            _request(deviation_id="DEV-02", customer_agreement="requested"),
        ]
        result = assess_deviation_package(_package(requests))
        self.assertEqual(result["verdict"], PACKAGE_OPEN)
        self.assertEqual(result["awaiting_agreement_ids"], ["DEV-02"])
        self.assertEqual(result["agreement_outstanding_count"], 1)

    def test_individually_small_debits_add_past_the_package_allowance(self):
        requests = [
            _request(deviation_id="DEV-0%d" % n, performance_debit=0.004)
            for n in range(1, 4)
        ]
        result = assess_deviation_package(_package(requests))
        self.assertTrue(result["cumulative_allowance_breached"])
        self.assertAlmostEqual(
            result["cumulative_performance_debit"], 0.012, places=9
        )
        self.assertEqual(len(result["review_ids"]), 3)
        self.assertEqual(result["accept_as_is_ids"], [])

    def test_a_cumulative_debit_exactly_on_the_allowance_does_not_breach(self):
        allowance = DEFAULT_DEVIATION_POLICY["max_cumulative_performance_debit"]
        requests = [
            _request(deviation_id="DEV-01", performance_debit=allowance / 2.0),
            _request(deviation_id="DEV-02", performance_debit=allowance / 2.0),
        ]
        result = assess_deviation_package(_package(requests))
        self.assertAlmostEqual(
            result["cumulative_performance_debit"], allowance, places=12
        )
        self.assertFalse(result["cumulative_allowance_breached"])
        self.assertEqual(result["verdict"], PACKAGE_USABLE)

    def test_a_rejected_departure_does_not_add_to_the_carried_debit(self):
        requests = [
            _request(deviation_id="DEV-01", performance_debit=0.004),
            _request(
                deviation_id="DEV-02",
                criterion_id="cracked-cell",
                performance_debit=0.9,
            ),
        ]
        result = assess_deviation_package(_package(requests))
        self.assertAlmostEqual(
            result["cumulative_performance_debit"], 0.004, places=9
        )
        self.assertEqual(result["rejected_ids"], ["DEV-02"])

    def test_a_refused_agreement_does_not_add_to_the_carried_debit(self):
        requests = [
            _request(deviation_id="DEV-01", performance_debit=0.004),
            _request(
                deviation_id="DEV-02",
                performance_debit=0.005,
                customer_agreement="refused",
            ),
        ]
        result = assess_deviation_package(_package(requests))
        self.assertAlmostEqual(
            result["cumulative_performance_debit"], 0.004, places=9
        )
        self.assertEqual(result["rework_ids"], ["DEV-02"])

    def test_the_worst_departure_drives_the_package(self):
        requests = [
            _request(deviation_id="DEV-01"),
            _request(deviation_id="DEV-02", customer_agreement="refused"),
            _request(deviation_id="DEV-03", criterion_id="cracked-cell"),
        ]
        result = assess_deviation_package(_package(requests))
        self.assertEqual(result["worst_disposition"], REJECT)
        self.assertFalse(result["usable_as_is"])

    def test_disposition_counts_add_up_to_the_package(self):
        requests = [
            _request(deviation_id="DEV-01"),
            _request(deviation_id="DEV-02", customer_agreement="requested"),
        ]
        result = assess_deviation_package(_package(requests))
        self.assertEqual(sum(result["disposition_counts"].values()), 2)

    def test_duplicate_deviation_ids_rejected(self):
        requests = [_request(), _request(customer_agreement="requested")]
        with self.assertRaises(ValueError):
            assess_deviation_package(_package(requests))

    def test_non_list_deviations_rejected(self):
        with self.assertRaises(ValueError):
            assess_deviation_package(_package("DEV-01"))

    def test_non_mapping_package_rejected(self):
        with self.assertRaises(ValueError):
            assess_deviation_package("SCA-001")

    def test_blank_assembly_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_deviation_package(_package(assembly_id=" "))


if __name__ == "__main__":
    unittest.main()
