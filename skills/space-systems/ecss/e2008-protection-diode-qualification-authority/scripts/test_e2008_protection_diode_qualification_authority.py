#!/usr/bin/env python3
"""Contract test for protection diode qualification authority, clause 9.5.1 (offline)."""

import copy
import unittest

from e2008_protection_diode_qualification_authority_logic import (
    ADMISSIBLE_ISSUING_PARTIES,
    CONFIGURATION_KEYS,
    DEFAULT_DIODE_AUTHORITY_POLICY,
    DIODE_KINDS,
    PROGRAMME_AUTHORISED,
    PROGRAMME_NOT_AUTHORISED,
    SUPPLY_AUTHORISED,
    SUPPLY_GRANT_EXPIRED,
    SUPPLY_GRANT_POSTDATED,
    SUPPLY_GRANT_WITHDRAWN,
    SUPPLY_ISSUER_INADMISSIBLE,
    SUPPLY_NO_GRANT,
    SUPPLY_SCOPE_MISS,
    assess_diode_qualification_authority,
    assess_diode_supply,
    diode_kinds,
    grant_key,
    grant_scope_delta,
    grant_validity,
    issuing_authority,
    lookup_grant,
    normalise_diode_kind,
    supply_configuration,
    validate_diode_authority_policy,
    worst_arm,
)


def _grant(kind="external", grant_id=None, **overrides):
    grant = {
        "grant_id": grant_id or ("grant-%s" % kind),
        "producer": "producer-alpha",
        "diode_kind": kind,
        "diode_type": "pdx-40",
        "process_baseline": "baseline-2026a",
        "issued_by": "customer",
        "issued_on": "2026-01-15",
        "withdrawn": False,
        "valid_until": "2027-01-15",
    }
    grant.update(overrides)
    return grant


def _supply(kind="external", supply_id=None, **overrides):
    supply = {
        "supply_id": supply_id or ("sup-%s" % kind),
        "producer": "producer-alpha",
        "diode_kind": kind,
        "diode_type": "pdx-40",
        "process_baseline": "baseline-2026a",
        "supply_date": "2026-06-01",
    }
    supply.update(overrides)
    return supply


def _register():
    return [_grant("external"), _grant("integral")]


def _case(supplies=None, register=None):
    return {
        "grant_register": register if register is not None else _register(),
        "supplies": supplies
        if supplies is not None
        else [_supply("external"), _supply("integral")],
    }


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_diode_authority_policy(DEFAULT_DIODE_AUTHORITY_POLICY),
            DEFAULT_DIODE_AUTHORITY_POLICY,
        )

    def test_default_policy_refuses_a_supplier_self_grant(self):
        self.assertFalse(DEFAULT_DIODE_AUTHORITY_POLICY["admit_supplier_self_grant"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_authority_policy("the customer decides")

    def test_out_of_range_supply_fraction_rejected(self):
        broken = copy.deepcopy(DEFAULT_DIODE_AUTHORITY_POLICY)
        broken["min_authorised_supply_fraction"] = -0.2
        with self.assertRaises(ValueError):
            validate_diode_authority_policy(broken)

    def test_non_boolean_producer_switch_rejected(self):
        broken = copy.deepcopy(DEFAULT_DIODE_AUTHORITY_POLICY)
        broken["require_producer_match"] = "always"
        with self.assertRaises(ValueError):
            validate_diode_authority_policy(broken)

    def test_only_the_customer_is_admissible_by_default(self):
        self.assertEqual(ADMISSIBLE_ISSUING_PARTIES, ("customer",))


class DiodeKindTests(unittest.TestCase):
    def test_both_kinds_are_offered(self):
        self.assertEqual(diode_kinds(), DIODE_KINDS)
        self.assertIn("integral", diode_kinds())

    def test_a_kind_reads_back_lowercased(self):
        self.assertEqual(normalise_diode_kind("External"), "external")

    def test_an_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalise_diode_kind("bypass")

    def test_an_empty_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalise_diode_kind("")

    def test_the_register_key_pairs_producer_with_kind(self):
        self.assertEqual(
            grant_key("Producer-Alpha", "Integral"), "producer-alpha::integral"
        )

    def test_the_two_kinds_of_one_producer_get_different_keys(self):
        self.assertNotEqual(
            grant_key("producer-alpha", "external"),
            grant_key("producer-alpha", "integral"),
        )


class ConfigurationTests(unittest.TestCase):
    def test_every_configuration_key_is_read(self):
        configuration = supply_configuration(_supply())
        self.assertEqual(sorted(configuration), sorted(CONFIGURATION_KEYS))

    def test_a_supply_missing_the_process_baseline_rejected(self):
        supply = _supply()
        del supply["process_baseline"]
        with self.assertRaises(ValueError):
            supply_configuration(supply)

    def test_non_mapping_supply_rejected(self):
        with self.assertRaises(ValueError):
            supply_configuration("producer-alpha")

    def test_a_matching_grant_reaches_every_attribute(self):
        delta = grant_scope_delta(_supply(), _grant())
        self.assertTrue(delta["in_scope"])
        self.assertEqual(delta["attributes_out_of_scope"], [])

    def test_a_second_source_is_out_of_scope(self):
        delta = grant_scope_delta(_supply(producer="producer-beta"), _grant())
        self.assertFalse(delta["in_scope"])
        self.assertEqual(delta["attributes_out_of_scope"], ["producer"])

    def test_an_integral_diode_is_outside_an_external_grant(self):
        delta = grant_scope_delta(_supply("integral"), _grant("external"))
        self.assertIn("diode_kind", delta["attributes_out_of_scope"])

    def test_a_changed_process_baseline_is_named(self):
        delta = grant_scope_delta(
            _supply(process_baseline="baseline-2027b"), _grant()
        )
        self.assertEqual(delta["attributes_out_of_scope"], ["process_baseline"])

    def test_the_producer_check_can_be_relaxed_by_policy(self):
        policy = copy.deepcopy(DEFAULT_DIODE_AUTHORITY_POLICY)
        policy["require_producer_match"] = False
        delta = grant_scope_delta(
            _supply(producer="producer-beta"), _grant(), policy
        )
        self.assertTrue(delta["in_scope"])


class IssuingAuthorityTests(unittest.TestCase):
    def test_a_customer_grant_is_admissible(self):
        self.assertTrue(issuing_authority(_grant())["admissible"])

    def test_a_supplier_grant_is_not_admissible(self):
        result = issuing_authority(_grant(issued_by="supplier"))
        self.assertFalse(result["admissible"])
        self.assertTrue(result["self_granted"])

    def test_a_producer_grant_is_not_admissible(self):
        self.assertFalse(issuing_authority(_grant(issued_by="producer"))["admissible"])

    def test_a_laboratory_report_is_not_a_grant(self):
        result = issuing_authority(_grant(issued_by="test-laboratory"))
        self.assertFalse(result["admissible"])
        self.assertFalse(result["self_granted"])

    def test_a_supplier_grant_stands_when_policy_admits_it(self):
        policy = copy.deepcopy(DEFAULT_DIODE_AUTHORITY_POLICY)
        policy["admit_supplier_self_grant"] = True
        self.assertTrue(
            issuing_authority(_grant(issued_by="supplier"), policy)["admissible"]
        )

    def test_an_unknown_issuing_party_rejected(self):
        with self.assertRaises(ValueError):
            issuing_authority(_grant(issued_by="the-internet"))


class ValidityTests(unittest.TestCase):
    def test_a_grant_in_force_reads_back_in_force(self):
        validity = grant_validity(_grant(), "2026-06-01")
        self.assertTrue(validity["in_force"])

    def test_a_grant_issued_after_the_supply_is_postdated(self):
        validity = grant_validity(_grant(issued_on="2026-08-01"), "2026-06-01")
        self.assertTrue(validity["postdated"])
        self.assertFalse(validity["in_force"])

    def test_a_grant_that_ran_out_is_expired(self):
        validity = grant_validity(_grant(valid_until="2026-03-01"), "2026-06-01")
        self.assertTrue(validity["expired"])

    def test_a_withdrawn_grant_is_not_in_force(self):
        validity = grant_validity(_grant(withdrawn=True), "2026-06-01")
        self.assertTrue(validity["withdrawn"])
        self.assertFalse(validity["in_force"])

    def test_a_grant_with_no_end_date_never_expires(self):
        validity = grant_validity(_grant(valid_until=None), "2030-06-01")
        self.assertIsNone(validity["valid_until"])
        self.assertFalse(validity["expired"])

    def test_a_grant_expiring_before_it_was_issued_rejected(self):
        with self.assertRaises(ValueError):
            grant_validity(_grant(valid_until="2025-01-01"), "2026-06-01")

    def test_a_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            grant_validity(_grant(issued_on="last spring"), "2026-06-01")

    def test_a_non_boolean_withdrawal_rejected(self):
        with self.assertRaises(ValueError):
            grant_validity(_grant(withdrawn="yes"), "2026-06-01")


class RegisterTests(unittest.TestCase):
    def test_a_grant_is_found_for_each_kind(self):
        self.assertIsNotNone(lookup_grant(_register(), "producer-alpha", "integral"))

    def test_an_unfiled_producer_returns_nothing(self):
        self.assertIsNone(lookup_grant(_register(), "producer-beta", "external"))

    def test_duplicate_grants_for_one_key_rejected(self):
        register = _register() + [_grant("external", grant_id="grant-duplicate")]
        with self.assertRaises(ValueError):
            lookup_grant(register, "producer-alpha", "external")

    def test_non_sequence_register_rejected(self):
        with self.assertRaises(ValueError):
            lookup_grant("a register", "producer-alpha", "external")


class SupplyVerdictTests(unittest.TestCase):
    def test_a_granted_supply_is_authorised(self):
        result = assess_diode_supply(_supply(), _register())
        self.assertEqual(result["verdict"], SUPPLY_AUTHORISED)
        self.assertTrue(result["authorised"])

    def test_a_supply_with_no_grant_is_named(self):
        result = assess_diode_supply(_supply(producer="producer-beta"), _register())
        self.assertEqual(result["verdict"], SUPPLY_NO_GRANT)
        self.assertIsNone(result["grant_id"])

    def test_an_inadmissible_issuer_outranks_a_scope_miss(self):
        register = [
            _grant("external", issued_by="supplier", process_baseline="baseline-x")
        ]
        result = assess_diode_supply(_supply(), register)
        self.assertEqual(result["verdict"], SUPPLY_ISSUER_INADMISSIBLE)

    def test_a_scope_miss_outranks_a_withdrawal(self):
        register = [
            _grant("external", process_baseline="baseline-x", withdrawn=True)
        ]
        result = assess_diode_supply(_supply(), register)
        self.assertEqual(result["verdict"], SUPPLY_SCOPE_MISS)

    def test_a_withdrawal_outranks_a_postdated_grant(self):
        register = [_grant("external", withdrawn=True, issued_on="2026-08-01")]
        result = assess_diode_supply(_supply(), register)
        self.assertEqual(result["verdict"], SUPPLY_GRANT_WITHDRAWN)

    def test_a_postdated_grant_outranks_an_expired_one(self):
        register = [
            _grant("external", issued_on="2026-08-01", valid_until="2026-09-01")
        ]
        result = assess_diode_supply(_supply(supply_date="2026-06-01"), register)
        self.assertEqual(result["verdict"], SUPPLY_GRANT_POSTDATED)

    def test_an_expired_grant_blocks_the_supply(self):
        register = [_grant("external", valid_until="2026-03-01")]
        result = assess_diode_supply(_supply(), register)
        self.assertEqual(result["verdict"], SUPPLY_GRANT_EXPIRED)

    def test_an_integral_supply_against_an_external_only_register(self):
        register = [_grant("external")]
        result = assess_diode_supply(_supply("integral"), register)
        self.assertEqual(result["verdict"], SUPPLY_NO_GRANT)

    def test_a_supply_without_an_identifier_rejected(self):
        supply = _supply()
        del supply["supply_id"]
        with self.assertRaises(ValueError):
            assess_diode_supply(supply, _register())

    def test_findings_name_the_supply(self):
        result = assess_diode_supply(_supply(producer="producer-beta"), _register())
        self.assertTrue(any("sup-external" in f for f in result["findings"]))


class WorstArmTests(unittest.TestCase):
    def test_no_grant_outranks_everything(self):
        self.assertEqual(
            worst_arm([SUPPLY_GRANT_EXPIRED, SUPPLY_NO_GRANT, SUPPLY_SCOPE_MISS]),
            SUPPLY_NO_GRANT,
        )

    def test_a_clean_set_has_no_arm_to_close(self):
        self.assertIsNone(worst_arm([SUPPLY_AUTHORISED, SUPPLY_AUTHORISED]))

    def test_non_sequence_verdicts_rejected(self):
        with self.assertRaises(ValueError):
            worst_arm(None)


class ProgrammeTests(unittest.TestCase):
    def test_a_fully_granted_programme_is_authorised(self):
        result = assess_diode_qualification_authority(_case())
        self.assertEqual(result["verdict"], PROGRAMME_AUTHORISED)
        self.assertEqual(result["findings"], [])
        self.assertIsNone(result["close_first"])

    def test_one_blocked_supply_blocks_the_programme(self):
        supplies = [_supply("external"), _supply("integral", producer="producer-beta")]
        result = assess_diode_qualification_authority(_case(supplies))
        self.assertEqual(result["verdict"], PROGRAMME_NOT_AUTHORISED)
        self.assertEqual(result["blocked_supply_ids"], ["sup-integral"])

    def test_the_ungranted_producer_kind_is_named(self):
        supplies = [_supply("integral", producer="producer-beta")]
        result = assess_diode_qualification_authority(_case(supplies))
        self.assertEqual(
            result["ungranted_producer_kinds"], ["producer-beta::integral"]
        )

    def test_the_authorised_share_is_reported(self):
        supplies = [_supply("external"), _supply("integral", producer="producer-beta")]
        result = assess_diode_qualification_authority(_case(supplies))
        self.assertAlmostEqual(result["authorised_supply_fraction"], 0.5, places=9)

    def test_a_clean_programme_reports_a_full_share(self):
        result = assess_diode_qualification_authority(_case())
        self.assertAlmostEqual(result["authorised_supply_fraction"], 1.0, places=9)

    def test_the_arm_to_close_first_is_named(self):
        supplies = [
            _supply("external", supply_id="sup-1", producer="producer-beta"),
            _supply("integral", supply_id="sup-2", process_baseline="baseline-x"),
        ]
        result = assess_diode_qualification_authority(_case(supplies))
        self.assertEqual(result["close_first"], SUPPLY_NO_GRANT)

    def test_supplies_are_grouped_by_verdict(self):
        supplies = [_supply("external"), _supply("integral", producer="producer-beta")]
        result = assess_diode_qualification_authority(_case(supplies))
        self.assertEqual(
            result["grouped_by_verdict"][SUPPLY_NO_GRANT], ["sup-integral"]
        )

    def test_one_type_shipping_twice_is_judged_per_supply(self):
        supplies = [
            _supply("external", supply_id="sup-1", supply_date="2026-06-01"),
            _supply("external", supply_id="sup-2", supply_date="2027-06-01"),
        ]
        result = assess_diode_qualification_authority(_case(supplies))
        self.assertEqual(result["blocked_supply_ids"], ["sup-2"])

    def test_assessments_come_back_in_identifier_order(self):
        result = assess_diode_qualification_authority(_case())
        ids = [entry["supply_id"] for entry in result["supply_assessments"]]
        self.assertEqual(ids, sorted(ids))

    def test_repeated_supply_identifier_rejected(self):
        supplies = [
            _supply("external", supply_id="sup-1"),
            _supply("integral", supply_id="sup-1"),
        ]
        with self.assertRaises(ValueError):
            assess_diode_qualification_authority(_case(supplies))

    def test_empty_supply_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_qualification_authority(_case([]))

    def test_a_case_without_a_register_rejected(self):
        case = _case()
        del case["grant_register"]
        with self.assertRaises(ValueError):
            assess_diode_qualification_authority(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_qualification_authority([_supply()])

    def test_an_empty_register_leaves_every_supply_ungranted(self):
        result = assess_diode_qualification_authority(_case(register=[]))
        self.assertEqual(len(result["ungranted_producer_kinds"]), 2)


if __name__ == "__main__":
    unittest.main()
