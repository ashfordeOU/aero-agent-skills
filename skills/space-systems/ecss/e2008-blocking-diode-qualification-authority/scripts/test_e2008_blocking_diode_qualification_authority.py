#!/usr/bin/env python3
"""Contract test for blocking diode qualification authority, clause 12.5.1 (offline)."""

import copy
import unittest

from e2008_blocking_diode_qualification_authority_logic import (
    ACCEPTED_AUTHORITIES,
    ACCEPTED_CONSTRUCTIONS,
    DEFAULT_GRANT_POLICY,
    GRANTING_AUTHORITY,
    LOT_AUTHORITY_INVALID,
    LOT_CONSTRUCTION_OUT_OF_SCOPE,
    LOT_GRANT_WITHDRAWN,
    LOT_HOLDER_MISMATCH,
    LOT_NO_GRANT,
    LOT_QUALIFIED,
    LOT_SCOPE_MISMATCH,
    LOT_SUBCONTRACTED_STEP_UNCOVERED,
    PROCESS_IDENTITY_KEYS,
    PROGRAMME_FULLY_QUALIFIED,
    PROGRAMME_NOT_FULLY_QUALIFIED,
    QUALIFIED_CONSTRUCTION,
    assess_blocking_diode_qualification_authority,
    assess_lot_qualification,
    construction_in_clause_scope,
    find_grant,
    grant_issuing_authority,
    grant_state,
    grants_for_type,
    identity_delta,
    process_identity,
    subcontracted_step_coverage,
    validate_grant_policy,
    worst_lot_verdict,
)

IDENTITY = {
    "process_owner": "diode-works-one",
    "production_site": "site-north",
    "diode_construction": "planar",
    "process_baseline": "pb-rev-c",
}


def _lot(lot_id="lot-1", **overrides):
    lot = {
        "lot_id": lot_id,
        "diode_type": "bd-type-alpha",
        "subcontracted_steps": [],
    }
    lot.update(IDENTITY)
    lot.update(overrides)
    return lot


def _grant(**overrides):
    grant = {
        "grant_id": "qg-bd-alpha-1",
        "diode_type": "bd-type-alpha",
        "granted_to": "diode-works-one",
        "issued_by": "customer",
        "state": "issued",
        "permitted_subcontractors": [],
        "scope": dict(IDENTITY),
    }
    grant.update(overrides)
    return grant


def _programme(lots=None, register=None, **overrides):
    programme = {
        "programme_id": "prog-blocking-diode-one",
        "grant_register": register if register is not None else [_grant()],
        "lots": lots if lots is not None else [_lot()],
    }
    programme.update(overrides)
    return programme


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_grant_policy(DEFAULT_GRANT_POLICY), DEFAULT_GRANT_POLICY
        )

    def test_default_policy_refuses_a_supplier_self_declaration(self):
        self.assertFalse(DEFAULT_GRANT_POLICY["admit_supplier_self_declaration"])

    def test_default_policy_requires_the_grant_holder_to_be_the_process_owner(self):
        self.assertTrue(DEFAULT_GRANT_POLICY["require_holder_match"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_grant_policy("the customer decides")

    def test_non_boolean_holder_switch_rejected(self):
        broken = copy.deepcopy(DEFAULT_GRANT_POLICY)
        broken["require_holder_match"] = "yes"
        with self.assertRaises(ValueError):
            validate_grant_policy(broken)

    def test_out_of_range_lot_fraction_rejected(self):
        broken = copy.deepcopy(DEFAULT_GRANT_POLICY)
        broken["min_qualified_lot_fraction"] = 1.5
        with self.assertRaises(ValueError):
            validate_grant_policy(broken)

    def test_the_customer_is_the_granting_authority(self):
        self.assertEqual(GRANTING_AUTHORITY, "customer")
        self.assertIn(GRANTING_AUTHORITY, ACCEPTED_AUTHORITIES)


class IdentityTests(unittest.TestCase):
    def test_a_full_lot_reads_back_every_identity_key(self):
        read = process_identity(_lot())
        self.assertEqual(sorted(read), sorted(PROCESS_IDENTITY_KEYS))

    def test_a_lot_missing_the_process_owner_rejected(self):
        lot = _lot()
        del lot["process_owner"]
        with self.assertRaises(ValueError):
            process_identity(lot)

    def test_an_unknown_construction_rejected(self):
        with self.assertRaises(ValueError):
            process_identity(_lot(diode_construction="hybrid"))

    def test_construction_is_read_case_insensitively(self):
        self.assertEqual(
            process_identity(_lot(diode_construction="PLANAR"))["diode_construction"],
            "planar",
        )

    def test_a_matching_scope_has_no_identity_delta(self):
        self.assertEqual(identity_delta(_lot(), _grant()["scope"]), [])

    def test_a_moved_site_shows_in_the_identity_delta(self):
        self.assertEqual(
            identity_delta(_lot(production_site="site-south"), _grant()["scope"]),
            ["production_site"],
        )

    def test_the_planar_lot_is_in_clause_scope(self):
        read = construction_in_clause_scope(_lot())
        self.assertTrue(read["in_scope"])
        self.assertEqual(read["diode_construction"], QUALIFIED_CONSTRUCTION)

    def test_a_mesa_lot_is_outside_clause_scope(self):
        self.assertFalse(
            construction_in_clause_scope(_lot(diode_construction="mesa"))["in_scope"]
        )

    def test_mesa_and_planar_are_both_recognised_constructions(self):
        self.assertEqual(sorted(ACCEPTED_CONSTRUCTIONS), ["mesa", "planar"])


class RegisterTests(unittest.TestCase):
    def test_a_grant_is_found_for_its_own_holder(self):
        found = find_grant([_grant()], "bd-type-alpha", "diode-works-one")
        self.assertEqual(found["grant_id"], "qg-bd-alpha-1")

    def test_no_grant_is_found_for_another_company(self):
        self.assertIsNone(
            find_grant([_grant()], "bd-type-alpha", "diode-works-two")
        )

    def test_two_companies_may_each_hold_a_grant_for_one_type(self):
        register = [_grant(), _grant(grant_id="qg-2", granted_to="diode-works-two")]
        self.assertEqual(len(grants_for_type(register, "bd-type-alpha")), 2)

    def test_two_grants_to_the_same_company_are_a_register_defect(self):
        register = [_grant(), _grant(grant_id="qg-duplicate")]
        with self.assertRaises(ValueError):
            grants_for_type(register, "bd-type-alpha")

    def test_a_non_sequence_register_rejected(self):
        with self.assertRaises(ValueError):
            grants_for_type({"grant": _grant()}, "bd-type-alpha")

    def test_a_grant_without_a_holder_rejected(self):
        grant = _grant()
        del grant["granted_to"]
        with self.assertRaises(ValueError):
            grants_for_type([grant], "bd-type-alpha")


class AuthorityTests(unittest.TestCase):
    def test_a_customer_grant_is_valid(self):
        self.assertTrue(grant_issuing_authority(_grant())["valid"])

    def test_a_supplier_self_declaration_is_not_a_grant(self):
        self.assertFalse(
            grant_issuing_authority(_grant(issued_by="supplier"))["valid"]
        )

    def test_a_laboratory_report_is_not_a_grant(self):
        self.assertFalse(
            grant_issuing_authority(
                _grant(issued_by="third-party-laboratory")
            )["valid"]
        )

    def test_an_unknown_issuing_party_rejected(self):
        with self.assertRaises(ValueError):
            grant_issuing_authority(_grant(issued_by="the-project-office"))

    def test_a_live_grant_is_not_withdrawn(self):
        self.assertFalse(grant_state(_grant())["withdrawn"])

    def test_a_withdrawn_grant_reads_as_withdrawn(self):
        self.assertTrue(grant_state(_grant(state="withdrawn"))["withdrawn"])

    def test_an_unknown_grant_state_rejected(self):
        with self.assertRaises(ValueError):
            grant_state(_grant(state="pending"))


class SubcontractTests(unittest.TestCase):
    def test_a_lot_with_no_handed_out_steps_is_covered(self):
        self.assertTrue(subcontracted_step_coverage(_lot(), _grant())["covered"])

    def test_a_step_kept_in_house_is_covered(self):
        lot = _lot(
            subcontracted_steps=[
                {"step": "passivation", "performed_by": "diode-works-one"}
            ]
        )
        self.assertTrue(subcontracted_step_coverage(lot, _grant())["covered"])

    def test_a_named_subcontractor_is_covered(self):
        lot = _lot(
            subcontracted_steps=[
                {"step": "passivation", "performed_by": "coating-house-two"}
            ]
        )
        grant = _grant(permitted_subcontractors=["coating-house-two"])
        self.assertTrue(subcontracted_step_coverage(lot, grant)["covered"])

    def test_an_unnamed_subcontractor_is_uncovered(self):
        lot = _lot(
            subcontracted_steps=[
                {"step": "passivation", "performed_by": "coating-house-nine"}
            ]
        )
        read = subcontracted_step_coverage(lot, _grant())
        self.assertFalse(read["covered"])
        self.assertEqual(read["uncovered_steps"][0]["step"], "passivation")

    def test_a_repeated_subcontracted_step_rejected(self):
        lot = _lot(
            subcontracted_steps=[
                {"step": "passivation", "performed_by": "coating-house-two"},
                {"step": "passivation", "performed_by": "coating-house-two"},
            ]
        )
        with self.assertRaises(ValueError):
            subcontracted_step_coverage(lot, _grant())

    def test_a_non_sequence_step_list_rejected(self):
        with self.assertRaises(ValueError):
            subcontracted_step_coverage(_lot(subcontracted_steps="none"), _grant())


class LotVerdictTests(unittest.TestCase):
    def test_a_clean_lot_is_qualified(self):
        result = assess_lot_qualification(_lot(), [_grant()])
        self.assertEqual(result["verdict"], LOT_QUALIFIED)
        self.assertTrue(result["qualified"])
        self.assertEqual(result["findings"], [])

    def test_a_mesa_lot_falls_outside_the_clause(self):
        result = assess_lot_qualification(
            _lot(diode_construction="mesa"), [_grant()]
        )
        self.assertEqual(result["verdict"], LOT_CONSTRUCTION_OUT_OF_SCOPE)

    def test_a_type_nobody_granted_blocks_the_lot(self):
        result = assess_lot_qualification(_lot(diode_type="bd-type-beta"), [_grant()])
        self.assertEqual(result["verdict"], LOT_NO_GRANT)

    def test_a_type_granted_to_another_company_blocks_the_lot(self):
        result = assess_lot_qualification(
            _lot(process_owner="diode-works-two"), [_grant()]
        )
        self.assertEqual(result["verdict"], LOT_HOLDER_MISMATCH)
        self.assertEqual(result["other_holders"], ["diode-works-one"])

    def test_the_holder_mismatch_finding_names_who_does_hold_the_grant(self):
        result = assess_lot_qualification(
            _lot(process_owner="diode-works-two"), [_grant()]
        )
        self.assertTrue(any("diode-works-one" in f for f in result["findings"]))

    def test_a_supplier_issued_grant_blocks_the_lot(self):
        result = assess_lot_qualification(_lot(), [_grant(issued_by="supplier")])
        self.assertEqual(result["verdict"], LOT_AUTHORITY_INVALID)

    def test_a_moved_site_blocks_the_lot(self):
        result = assess_lot_qualification(
            _lot(production_site="site-south"), [_grant()]
        )
        self.assertEqual(result["verdict"], LOT_SCOPE_MISMATCH)

    def test_a_drifted_process_baseline_blocks_the_lot(self):
        result = assess_lot_qualification(
            _lot(process_baseline="pb-rev-d"), [_grant()]
        )
        self.assertEqual(result["verdict"], LOT_SCOPE_MISMATCH)

    def test_an_uncovered_subcontracted_step_blocks_the_lot(self):
        lot = _lot(
            subcontracted_steps=[
                {"step": "wafer-thinning", "performed_by": "grinding-house-nine"}
            ]
        )
        result = assess_lot_qualification(lot, [_grant()])
        self.assertEqual(result["verdict"], LOT_SUBCONTRACTED_STEP_UNCOVERED)

    def test_a_withdrawn_grant_blocks_the_lot(self):
        result = assess_lot_qualification(_lot(), [_grant(state="withdrawn")])
        self.assertEqual(result["verdict"], LOT_GRANT_WITHDRAWN)

    def test_a_relaxed_policy_lets_a_mesa_lot_through(self):
        relaxed = copy.deepcopy(DEFAULT_GRANT_POLICY)
        relaxed["require_planar_construction"] = False
        result = assess_lot_qualification(
            _lot(diode_construction="mesa"),
            [_grant(scope=dict(IDENTITY, diode_construction="mesa"))],
            relaxed,
        )
        self.assertEqual(result["verdict"], LOT_QUALIFIED)

    def test_a_lot_without_an_identifier_rejected(self):
        lot = _lot()
        del lot["lot_id"]
        with self.assertRaises(ValueError):
            assess_lot_qualification(lot, [_grant()])

    def test_a_grant_without_a_scope_mapping_rejected(self):
        grant = _grant()
        del grant["scope"]
        with self.assertRaises(ValueError):
            assess_lot_qualification(_lot(), [grant])


class RankTests(unittest.TestCase):
    def test_construction_outranks_every_other_arm(self):
        self.assertEqual(
            worst_lot_verdict(
                [LOT_QUALIFIED, LOT_GRANT_WITHDRAWN, LOT_CONSTRUCTION_OUT_OF_SCOPE]
            ),
            LOT_CONSTRUCTION_OUT_OF_SCOPE,
        )

    def test_a_missing_grant_outranks_a_holder_mismatch(self):
        self.assertEqual(
            worst_lot_verdict([LOT_HOLDER_MISMATCH, LOT_NO_GRANT]), LOT_NO_GRANT
        )

    def test_a_holder_mismatch_outranks_a_withdrawal(self):
        self.assertEqual(
            worst_lot_verdict([LOT_GRANT_WITHDRAWN, LOT_HOLDER_MISMATCH]),
            LOT_HOLDER_MISMATCH,
        )

    def test_all_clean_lots_rank_as_qualified(self):
        self.assertEqual(worst_lot_verdict([LOT_QUALIFIED]), LOT_QUALIFIED)

    def test_an_unknown_verdict_rejected(self):
        with self.assertRaises(ValueError):
            worst_lot_verdict(["lot-probably-fine"])

    def test_an_empty_verdict_set_rejected(self):
        with self.assertRaises(ValueError):
            worst_lot_verdict([])


class ProgrammeTests(unittest.TestCase):
    def test_a_clean_programme_is_fully_qualified(self):
        result = assess_blocking_diode_qualification_authority(_programme())
        self.assertEqual(result["verdict"], PROGRAMME_FULLY_QUALIFIED)
        self.assertTrue(result["every_lot_qualified"])

    def test_the_qualified_share_of_a_clean_programme_is_one(self):
        result = assess_blocking_diode_qualification_authority(_programme())
        self.assertAlmostEqual(result["qualified_lot_fraction"], 1.0, places=9)

    def test_one_blocked_lot_in_four_scores_three_quarters(self):
        lots = [
            _lot("lot-1"),
            _lot("lot-2"),
            _lot("lot-3"),
            _lot("lot-4", process_owner="diode-works-two"),
        ]
        result = assess_blocking_diode_qualification_authority(_programme(lots))
        self.assertAlmostEqual(result["qualified_lot_fraction"], 0.75, places=9)
        self.assertEqual(result["verdict"], PROGRAMME_NOT_FULLY_QUALIFIED)

    def test_the_programme_names_the_blocked_lots(self):
        lots = [_lot("lot-1"), _lot("lot-2", diode_type="bd-type-beta")]
        result = assess_blocking_diode_qualification_authority(_programme(lots))
        self.assertEqual(result["blocked_lot_ids"], ["lot-2"])

    def test_the_programme_names_the_ungranted_diode_types(self):
        lots = [_lot("lot-1", diode_type="bd-type-beta")]
        result = assess_blocking_diode_qualification_authority(_programme(lots))
        self.assertEqual(result["ungranted_diode_types"], ["bd-type-beta"])

    def test_the_programme_names_the_companies_holding_no_grant(self):
        lots = [_lot("lot-1", process_owner="diode-works-two")]
        result = assess_blocking_diode_qualification_authority(_programme(lots))
        self.assertEqual(result["unqualified_process_owners"], ["diode-works-two"])

    def test_the_programme_groups_the_lots_by_verdict(self):
        lots = [_lot("lot-1"), _lot("lot-2", diode_construction="mesa")]
        result = assess_blocking_diode_qualification_authority(_programme(lots))
        self.assertEqual(
            result["grouped_by_verdict"][LOT_CONSTRUCTION_OUT_OF_SCOPE], ["lot-2"]
        )

    def test_the_programme_reports_the_arm_to_close_first(self):
        lots = [_lot("lot-1", state="issued"), _lot("lot-2", diode_type="bd-type-beta")]
        result = assess_blocking_diode_qualification_authority(_programme(lots))
        self.assertEqual(result["worst_verdict"], LOT_NO_GRANT)

    def test_a_repeated_lot_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_qualification_authority(
                _programme([_lot("lot-1"), _lot("lot-1")])
            )

    def test_an_empty_lot_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_qualification_authority(_programme([]))

    def test_a_programme_without_an_identifier_rejected(self):
        programme = _programme()
        del programme["programme_id"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_qualification_authority(programme)

    def test_non_mapping_programme_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_qualification_authority([_lot()])

    def test_an_empty_register_blocks_every_lot(self):
        result = assess_blocking_diode_qualification_authority(_programme(register=[]))
        self.assertEqual(result["verdict"], PROGRAMME_NOT_FULLY_QUALIFIED)
        self.assertEqual(result["blocked_lot_ids"], ["lot-1"])

    def test_a_relaxed_share_accepts_a_partly_qualified_programme(self):
        relaxed = copy.deepcopy(DEFAULT_GRANT_POLICY)
        relaxed["min_qualified_lot_fraction"] = 0.5
        lots = [_lot("lot-1"), _lot("lot-2", diode_type="bd-type-beta")]
        result = assess_blocking_diode_qualification_authority(
            _programme(lots), relaxed
        )
        self.assertAlmostEqual(result["qualified_lot_fraction"], 0.5, places=9)
        self.assertEqual(result["required_lot_fraction"], 0.5)

    def test_the_programme_carries_every_lot_finding(self):
        lots = [_lot("lot-2", diode_type="bd-type-gamma")]
        result = assess_blocking_diode_qualification_authority(_programme(lots))
        self.assertTrue(any("bd-type-gamma" in f for f in result["findings"]))


if __name__ == "__main__":
    unittest.main()
