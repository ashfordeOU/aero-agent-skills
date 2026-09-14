#!/usr/bin/env python3
"""Contract test for coverglass qualification authority, clause 8.6.1 (offline)."""

import copy
import unittest

from e2008_coverglass_qualification_authority_logic import (
    ACCEPTED_AUTHORITIES,
    COVERGLASS_CONFIGURATION_KEYS,
    DEFAULT_AUTHORITY_POLICY,
    GRANTING_AUTHORITY,
    PROGRAMME_FULLY_AUTHORISED,
    PROGRAMME_NOT_FULLY_AUTHORISED,
    SUPPLY_AUTHORISED,
    SUPPLY_AUTHORITY_INVALID,
    SUPPLY_GRANT_EXPIRED,
    SUPPLY_GRANT_NOT_YET_IN_FORCE,
    SUPPLY_GRANT_WITHDRAWN,
    SUPPLY_NO_GRANT,
    SUPPLY_SCOPE_MISMATCH,
    assess_coverglass_supply_programme,
    assess_supply_authorisation,
    configuration_delta,
    coverglass_configuration,
    find_grant,
    grant_issuing_authority,
    grant_validity_window,
    validate_authority_policy,
    worst_supply_verdict,
)

CONFIG = {
    "coverglass_material": "cerium-doped-borosilicate",
    "supplier": "optics-house-one",
    "coating_configuration": "ar-coated-conductive",
    "thickness_class": "100-micrometre",
}


def _shipment(shipment_id="ship-1", **overrides):
    shipment = {
        "shipment_id": shipment_id,
        "coverglass_type": "cg-type-alpha",
        "supply_date": "2026-06-15",
    }
    shipment.update(CONFIG)
    shipment.update(overrides)
    return shipment


def _grant(**overrides):
    grant = {
        "grant_id": "qg-alpha-1",
        "coverglass_type": "cg-type-alpha",
        "issued_by": "customer",
        "issued_on": "2026-01-20",
        "valid_until": "2029-01-20",
        "state": "issued",
        "scope": dict(CONFIG),
    }
    grant.update(overrides)
    return grant


def _programme(shipments=None, register=None, **overrides):
    programme = {
        "programme_id": "prog-array-one",
        "grant_register": register if register is not None else [_grant()],
        "shipments": shipments if shipments is not None else [_shipment()],
    }
    programme.update(overrides)
    return programme


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_authority_policy(DEFAULT_AUTHORITY_POLICY),
            DEFAULT_AUTHORITY_POLICY,
        )

    def test_default_policy_refuses_a_supplier_self_declaration(self):
        self.assertFalse(DEFAULT_AUTHORITY_POLICY["admit_supplier_self_declaration"])

    def test_default_policy_refuses_a_retroactive_grant(self):
        self.assertFalse(DEFAULT_AUTHORITY_POLICY["admit_retroactive_grant"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_authority_policy("customer decides")

    def test_non_boolean_scope_switch_rejected(self):
        broken = copy.deepcopy(DEFAULT_AUTHORITY_POLICY)
        broken["require_scope_match"] = "yes"
        with self.assertRaises(ValueError):
            validate_authority_policy(broken)

    def test_out_of_range_shipment_fraction_rejected(self):
        broken = copy.deepcopy(DEFAULT_AUTHORITY_POLICY)
        broken["min_authorised_shipment_fraction"] = 2.0
        with self.assertRaises(ValueError):
            validate_authority_policy(broken)

    def test_the_customer_is_the_granting_authority(self):
        self.assertEqual(GRANTING_AUTHORITY, "customer")
        self.assertIn(GRANTING_AUTHORITY, ACCEPTED_AUTHORITIES)


class ConfigurationTests(unittest.TestCase):
    def test_a_full_article_reads_back_every_key(self):
        read = coverglass_configuration(_shipment())
        self.assertEqual(sorted(read), sorted(COVERGLASS_CONFIGURATION_KEYS))

    def test_an_article_missing_an_attribute_rejected(self):
        shipment = _shipment()
        del shipment["coating_configuration"]
        with self.assertRaises(ValueError):
            coverglass_configuration(shipment)

    def test_a_matching_scope_has_no_delta(self):
        self.assertEqual(configuration_delta(_shipment(), _grant()["scope"]), [])

    def test_a_changed_coating_is_named_in_the_delta(self):
        scope = dict(CONFIG)
        scope["coating_configuration"] = "ar-coated-non-conductive"
        self.assertEqual(
            configuration_delta(_shipment(), scope), ["coating_configuration"]
        )

    def test_two_changed_attributes_are_both_named(self):
        scope = dict(CONFIG)
        scope["supplier"] = "optics-house-two"
        scope["thickness_class"] = "150-micrometre"
        self.assertEqual(
            configuration_delta(_shipment(), scope),
            ["supplier", "thickness_class"],
        )

    def test_non_mapping_article_rejected(self):
        with self.assertRaises(ValueError):
            coverglass_configuration("cg-type-alpha")


class AuthorityTests(unittest.TestCase):
    def test_a_customer_grant_is_valid(self):
        self.assertTrue(grant_issuing_authority(_grant())["valid"])

    def test_a_supplier_grant_is_not_valid_by_default(self):
        result = grant_issuing_authority(_grant(issued_by="supplier"))
        self.assertFalse(result["valid"])
        self.assertEqual(result["issued_by"], "supplier")

    def test_a_supplier_grant_stands_when_the_policy_admits_it(self):
        policy = copy.deepcopy(DEFAULT_AUTHORITY_POLICY)
        policy["admit_supplier_self_declaration"] = True
        self.assertTrue(
            grant_issuing_authority(_grant(issued_by="supplier"), policy)["valid"]
        )

    def test_a_laboratory_grant_is_not_valid_while_a_customer_grant_is_required(self):
        result = grant_issuing_authority(
            _grant(issued_by="third-party-laboratory")
        )
        self.assertFalse(result["valid"])

    def test_an_unknown_issuing_party_rejected(self):
        with self.assertRaises(ValueError):
            grant_issuing_authority(_grant(issued_by="the-project-manager"))

    def test_a_grant_with_no_issuer_rejected(self):
        grant = _grant()
        del grant["issued_by"]
        with self.assertRaises(ValueError):
            grant_issuing_authority(grant)


class ValidityWindowTests(unittest.TestCase):
    def test_a_grant_issued_before_supply_is_in_force(self):
        window = grant_validity_window(_grant(), "2026-06-15")
        self.assertTrue(window["in_force"])
        self.assertTrue(window["in_force_from"])

    def test_a_grant_issued_on_the_supply_date_is_in_force(self):
        window = grant_validity_window(_grant(issued_on="2026-06-15"), "2026-06-15")
        self.assertTrue(window["in_force_from"])
        self.assertEqual(window["days_before_supply"], 0)

    def test_a_grant_issued_after_supply_is_not_yet_in_force(self):
        window = grant_validity_window(_grant(issued_on="2026-08-01"), "2026-06-15")
        self.assertFalse(window["in_force_from"])
        self.assertLess(window["days_before_supply"], 0)

    def test_a_retroactive_grant_stands_when_the_policy_admits_it(self):
        policy = copy.deepcopy(DEFAULT_AUTHORITY_POLICY)
        policy["admit_retroactive_grant"] = True
        window = grant_validity_window(
            _grant(issued_on="2026-08-01"), "2026-06-15", policy
        )
        self.assertTrue(window["in_force_from"])

    def test_a_grant_expiring_before_supply_has_run_out(self):
        window = grant_validity_window(_grant(valid_until="2026-03-01"), "2026-06-15")
        self.assertFalse(window["not_expired"])

    def test_a_grant_expiring_on_the_supply_date_is_still_in_force(self):
        window = grant_validity_window(_grant(valid_until="2026-06-15"), "2026-06-15")
        self.assertTrue(window["not_expired"])
        self.assertTrue(window["in_force"])

    def test_an_open_ended_grant_never_expires(self):
        window = grant_validity_window(_grant(valid_until=None), "2039-06-15")
        self.assertTrue(window["not_expired"])
        self.assertIsNone(window["valid_until"])

    def test_expiry_is_ignored_when_the_policy_stops_enforcing_it(self):
        policy = copy.deepcopy(DEFAULT_AUTHORITY_POLICY)
        policy["enforce_validity_end"] = False
        window = grant_validity_window(
            _grant(valid_until="2026-03-01"), "2026-06-15", policy
        )
        self.assertTrue(window["not_expired"])

    def test_a_withdrawn_grant_is_not_in_force(self):
        window = grant_validity_window(_grant(state="withdrawn"), "2026-06-15")
        self.assertTrue(window["withdrawn"])
        self.assertFalse(window["in_force"])

    def test_a_grant_with_no_state_reads_as_issued(self):
        grant = _grant()
        del grant["state"]
        self.assertEqual(grant_validity_window(grant, "2026-06-15")["state"], "issued")

    def test_an_unknown_grant_state_rejected(self):
        with self.assertRaises(ValueError):
            grant_validity_window(_grant(state="pencilled-in"), "2026-06-15")

    def test_an_expiry_before_the_issue_date_rejected(self):
        with self.assertRaises(ValueError):
            grant_validity_window(
                _grant(issued_on="2026-05-01", valid_until="2026-04-01"),
                "2026-06-15",
            )

    def test_a_malformed_supply_date_rejected(self):
        with self.assertRaises(ValueError):
            grant_validity_window(_grant(), "15 June 2026")

    def test_the_days_of_lead_time_are_reported(self):
        window = grant_validity_window(_grant(issued_on="2026-06-05"), "2026-06-15")
        self.assertEqual(window["days_before_supply"], 10)


class RegisterTests(unittest.TestCase):
    def test_a_grant_on_record_is_found(self):
        self.assertEqual(
            find_grant([_grant()], "cg-type-alpha")["grant_id"], "qg-alpha-1"
        )

    def test_an_unknown_type_finds_nothing(self):
        self.assertIsNone(find_grant([_grant()], "cg-type-beta"))

    def test_two_grants_for_one_type_rejected(self):
        register = [_grant(), _grant(grant_id="qg-alpha-2")]
        with self.assertRaises(ValueError):
            find_grant(register, "cg-type-alpha")

    def test_a_non_sequence_register_rejected(self):
        with self.assertRaises(ValueError):
            find_grant("qg-alpha-1", "cg-type-alpha")


class ShipmentVerdictTests(unittest.TestCase):
    def test_a_covered_shipment_is_authorised(self):
        result = assess_supply_authorisation(_shipment(), [_grant()])
        self.assertEqual(result["verdict"], SUPPLY_AUTHORISED)
        self.assertTrue(result["authorised"])

    def test_a_shipment_with_no_grant_is_blocked(self):
        result = assess_supply_authorisation(
            _shipment(coverglass_type="cg-type-beta"), [_grant()]
        )
        self.assertEqual(result["verdict"], SUPPLY_NO_GRANT)
        self.assertIsNone(result["grant_id"])

    def test_no_grant_outranks_every_other_arm(self):
        result = assess_supply_authorisation(
            _shipment(coverglass_type="cg-type-beta"), []
        )
        self.assertEqual(result["verdict"], SUPPLY_NO_GRANT)

    def test_a_supplier_grant_outranks_a_scope_mismatch(self):
        scope = dict(CONFIG)
        scope["supplier"] = "optics-house-two"
        grant = _grant(issued_by="supplier", scope=scope)
        result = assess_supply_authorisation(_shipment(), [grant])
        self.assertEqual(result["verdict"], SUPPLY_AUTHORITY_INVALID)

    def test_a_scope_mismatch_outranks_a_withdrawal(self):
        scope = dict(CONFIG)
        scope["thickness_class"] = "150-micrometre"
        grant = _grant(scope=scope, state="withdrawn")
        result = assess_supply_authorisation(_shipment(), [grant])
        self.assertEqual(result["verdict"], SUPPLY_SCOPE_MISMATCH)
        self.assertEqual(result["scope_delta"], ["thickness_class"])

    def test_a_withdrawal_outranks_a_retroactive_grant(self):
        grant = _grant(state="withdrawn", issued_on="2026-08-01")
        result = assess_supply_authorisation(_shipment(), [grant])
        self.assertEqual(result["verdict"], SUPPLY_GRANT_WITHDRAWN)

    def test_a_retroactive_grant_outranks_an_expired_one(self):
        grant = _grant(issued_on="2026-08-01", valid_until="2026-08-30")
        result = assess_supply_authorisation(_shipment(), [grant])
        self.assertEqual(result["verdict"], SUPPLY_GRANT_NOT_YET_IN_FORCE)

    def test_an_expired_grant_blocks_the_shipment(self):
        grant = _grant(valid_until="2026-03-01")
        result = assess_supply_authorisation(_shipment(), [grant])
        self.assertEqual(result["verdict"], SUPPLY_GRANT_EXPIRED)

    def test_a_scope_mismatch_stands_when_the_policy_drops_the_match(self):
        scope = dict(CONFIG)
        scope["thickness_class"] = "150-micrometre"
        policy = copy.deepcopy(DEFAULT_AUTHORITY_POLICY)
        policy["require_scope_match"] = False
        result = assess_supply_authorisation(_shipment(), [_grant(scope=scope)], policy)
        self.assertEqual(result["verdict"], SUPPLY_AUTHORISED)

    def test_a_grant_with_no_scope_rejected(self):
        grant = _grant()
        del grant["scope"]
        with self.assertRaises(ValueError):
            assess_supply_authorisation(_shipment(), [grant])

    def test_a_shipment_without_an_identifier_rejected(self):
        shipment = _shipment()
        del shipment["shipment_id"]
        with self.assertRaises(ValueError):
            assess_supply_authorisation(shipment, [_grant()])

    def test_findings_name_the_grant(self):
        result = assess_supply_authorisation(
            _shipment(), [_grant(issued_by="supplier")]
        )
        self.assertTrue(any("qg-alpha-1" in f for f in result["findings"]))


class WorstVerdictTests(unittest.TestCase):
    def test_the_most_serious_arm_wins(self):
        self.assertEqual(
            worst_supply_verdict([SUPPLY_GRANT_EXPIRED, SUPPLY_NO_GRANT]),
            SUPPLY_NO_GRANT,
        )

    def test_a_clean_set_reports_authorised(self):
        self.assertEqual(
            worst_supply_verdict([SUPPLY_AUTHORISED, SUPPLY_AUTHORISED]),
            SUPPLY_AUTHORISED,
        )

    def test_an_unknown_verdict_rejected(self):
        with self.assertRaises(ValueError):
            worst_supply_verdict(["supply-probably-fine"])

    def test_an_empty_verdict_set_rejected(self):
        with self.assertRaises(ValueError):
            worst_supply_verdict([])


class ProgrammeTests(unittest.TestCase):
    def test_a_clean_programme_is_fully_authorised(self):
        result = assess_coverglass_supply_programme(_programme())
        self.assertEqual(result["verdict"], PROGRAMME_FULLY_AUTHORISED)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["every_shipment_authorised"])

    def test_one_ungranted_type_blocks_the_programme(self):
        shipments = [
            _shipment(),
            _shipment("ship-2", coverglass_type="cg-type-beta"),
        ]
        result = assess_coverglass_supply_programme(_programme(shipments))
        self.assertEqual(result["verdict"], PROGRAMME_NOT_FULLY_AUTHORISED)
        self.assertEqual(result["ungranted_coverglass_types"], ["cg-type-beta"])

    def test_the_authorised_share_is_reported(self):
        shipments = [
            _shipment(),
            _shipment("ship-2", coverglass_type="cg-type-beta"),
        ]
        result = assess_coverglass_supply_programme(_programme(shipments))
        self.assertAlmostEqual(
            result["authorised_shipment_fraction"], 1.0 / 2.0, places=9
        )

    def test_a_clean_programme_authorises_every_shipment(self):
        result = assess_coverglass_supply_programme(_programme())
        self.assertAlmostEqual(result["authorised_shipment_fraction"], 1.0, places=9)

    def test_blocked_shipments_are_listed(self):
        shipments = [
            _shipment(),
            _shipment("ship-2", supply_date="2025-01-01"),
        ]
        result = assess_coverglass_supply_programme(_programme(shipments))
        self.assertEqual(result["blocked_shipment_ids"], ["ship-2"])

    def test_shipments_are_grouped_by_verdict(self):
        shipments = [
            _shipment(),
            _shipment("ship-2", supply_date="2025-01-01"),
        ]
        result = assess_coverglass_supply_programme(_programme(shipments))
        self.assertEqual(
            result["grouped_by_verdict"][SUPPLY_GRANT_NOT_YET_IN_FORCE], ["ship-2"]
        )

    def test_the_worst_verdict_is_reported(self):
        shipments = [
            _shipment(),
            _shipment("ship-2", coverglass_type="cg-type-beta"),
            _shipment("ship-3", supply_date="2025-01-01"),
        ]
        result = assess_coverglass_supply_programme(_programme(shipments))
        self.assertEqual(result["worst_verdict"], SUPPLY_NO_GRANT)

    def test_assessments_come_back_in_identifier_order(self):
        shipments = [
            _shipment("ship-9"),
            _shipment("ship-2"),
        ]
        result = assess_coverglass_supply_programme(_programme(shipments))
        ids = [entry["shipment_id"] for entry in result["shipment_assessments"]]
        self.assertEqual(ids, sorted(ids))

    def test_a_repeated_shipment_identifier_rejected(self):
        shipments = [_shipment("ship-1"), _shipment("ship-1")]
        with self.assertRaises(ValueError):
            assess_coverglass_supply_programme(_programme(shipments))

    def test_an_empty_shipment_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_supply_programme(_programme([]))

    def test_a_non_sequence_register_rejected(self):
        programme = _programme()
        programme["grant_register"] = "qg-alpha-1"
        with self.assertRaises(ValueError):
            assess_coverglass_supply_programme(programme)

    def test_a_programme_without_an_identifier_rejected(self):
        programme = _programme()
        del programme["programme_id"]
        with self.assertRaises(ValueError):
            assess_coverglass_supply_programme(programme)

    def test_non_mapping_programme_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_supply_programme([_shipment()])

    def test_the_programme_carries_every_shipment_finding(self):
        shipments = [_shipment("ship-2", coverglass_type="cg-type-beta")]
        result = assess_coverglass_supply_programme(_programme(shipments))
        self.assertTrue(any("cg-type-beta" in f for f in result["findings"]))

    def test_an_empty_register_blocks_every_shipment(self):
        result = assess_coverglass_supply_programme(_programme(register=[]))
        self.assertEqual(result["verdict"], PROGRAMME_NOT_FULLY_AUTHORISED)
        self.assertEqual(result["blocked_shipment_ids"], ["ship-1"])


if __name__ == "__main__":
    unittest.main()
