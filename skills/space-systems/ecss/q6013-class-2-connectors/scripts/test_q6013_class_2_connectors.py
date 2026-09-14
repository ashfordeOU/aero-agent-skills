"""Contract tests for the clause 5.6.6 class 2 connector with removable contacts.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused connector policy,
a connector with no reference, arrangement or removal tool, a contact worked
past the insertion limit, a position over the loading-derated allowance, a
planned mating programme that spends the rated durability, an insert with no
spare provision, and evidence that is absent, unrecorded or carried entirely
against a heritage connector.
"""

import unittest

from q6013_class_2_connectors_logic import (
    ABSENT,
    CONNECTOR_CURRENT_DERATING_EXCEEDED,
    CONNECTOR_DURABILITY_CONSUMED,
    CONNECTOR_EVIDENCE_SHORT,
    CONNECTOR_MEETS_CLASS_TWO_SCOPE,
    CONNECTOR_NOT_IDENTIFIED,
    CONNECTOR_SPARE_PROVISION_SHORT,
    CONTACT_ARRANGEMENT_AND_KEYING_RECORD,
    CONTACT_INSERTION_LIMIT_EXCEEDED,
    CONTACT_RETENTION_FORCE_VERIFICATION,
    CRIMP_REMOVABLE_CONTACT,
    DECLARED_WITHOUT_RECORD,
    DEFAULT_CONNECTOR_POLICY,
    HELD_AGAINST_HERITAGE,
    HELD_DIRECTLY,
    INSERTION_AND_REMOVAL_TOOL_QUALIFICATION,
    INSULATION_RESISTANCE_MEASUREMENT,
    MATING_CYCLE_LOG,
    REQUIRED_EVIDENCE,
    SOLDER_CUP_REMOVABLE_CONTACT,
    TERMINATION_PROCESS_QUALIFICATION,
    absent_evidence,
    allowed_contact_current_a,
    assess_connector_application,
    contact_loading_factor,
    contact_loading_fraction,
    current_advisories,
    energised_positions,
    evidence_disposition,
    evidence_share,
    held_evidence,
    heritage_evidence,
    mating_cycle_fraction,
    over_inserted_positions,
    overloaded_positions,
    spare_contact_share,
    spare_positions,
    unrecorded_evidence,
    validate_connector_identity,
    validate_connector_policy,
    validate_contact_record,
    validate_contacts,
    validate_evidence,
    validate_evidence_record,
    weighted_evidence,
)


def _policy(**overrides):
    policy = dict(DEFAULT_CONNECTOR_POLICY)
    policy.update(overrides)
    return policy


def _contact(position, energised=False, current=0.0, insertions=1, spare=False,
             termination=CRIMP_REMOVABLE_CONTACT):
    return {
        "position": position,
        "termination": termination,
        "energised": energised,
        "current_a": current,
        "insertion_count": insertions,
        "spare": spare,
    }


def _contacts(current=1.5):
    live = [_contact("p%02d" % i, energised=True, current=current) for i in range(1, 7)]
    idle = [_contact("p07"), _contact("p08")]
    spares = [_contact("p09", insertions=0, spare=True),
              _contact("p10", insertions=0, spare=True)]
    return live + idle + spares


def _direct(subject, record="CONN-REP-3"):
    return {
        "subject": subject,
        "held_against_heritage": False,
        "record_reference": record,
        "heritage_connector_reference": "",
    }


def _heritage(subject, connector="CONN-HER-88"):
    return {
        "subject": subject,
        "held_against_heritage": True,
        "record_reference": "",
        "heritage_connector_reference": connector,
    }


def _evidence():
    return [
        _direct(CONTACT_RETENTION_FORCE_VERIFICATION, "RET-11"),
        _direct(INSERTION_AND_REMOVAL_TOOL_QUALIFICATION, "TOOLQ-02"),
        _direct(TERMINATION_PROCESS_QUALIFICATION, "CRIMPQ-05"),
        _direct(MATING_CYCLE_LOG, "MATE-LOG-19"),
        _direct(INSULATION_RESISTANCE_MEASUREMENT, "IR-07"),
        _heritage(CONTACT_ARRANGEMENT_AND_KEYING_RECORD),
    ]


def _expected_weighted():
    return (5.0 + DEFAULT_CONNECTOR_POLICY["heritage_credit"]) / len(REQUIRED_EVIDENCE)


def _case(**overrides):
    case = {
        "connector_reference": "CONN-2026-041",
        "insert_arrangement": "10-way-size-20",
        "rated_contact_current_a": 5.0,
        "rated_mating_cycles": 500.0,
        "planned_mating_cycles": 200.0,
        "removal_tool_reference": "TOOL-RM-20",
        "contacts": _contacts(),
        "evidence": _evidence(),
    }
    case.update(overrides)
    return case


def _boundary_contacts():
    live = [_contact("p%02d" % i, energised=True, current=1.5) for i in range(1, 6)]
    idle = [_contact("p06"), _contact("p07"), _contact("p08")]
    spares = [_contact("p09", insertions=0, spare=True),
              _contact("p10", insertions=0, spare=True)]
    return live + idle + spares


def _boundary_case():
    return _case(rated_contact_current_a=4.0, contacts=_boundary_contacts())


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_connector_policy(DEFAULT_CONNECTOR_POLICY),
            DEFAULT_CONNECTOR_POLICY,
        )

    def test_a_policy_allowing_no_insertion_at_all_is_refused(self):
        with self.assertRaises(ValueError):
            validate_connector_policy(_policy(max_contact_insertions=0))

    def test_a_fractional_insertion_limit_is_refused(self):
        with self.assertRaises(ValueError):
            validate_connector_policy(_policy(max_contact_insertions=2.5))

    def test_zero_current_derating_refused(self):
        with self.assertRaises(ValueError):
            validate_connector_policy(_policy(contact_current_derating_factor=0.0))

    def test_a_loading_slope_of_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_connector_policy(_policy(contact_loading_slope=1.0))

    def test_weighted_floor_above_the_share_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_connector_policy(
                _policy(min_evidence_share=0.5, min_weighted_evidence=0.9)
            )

    def test_zero_heritage_credit_refused(self):
        with self.assertRaises(ValueError):
            validate_connector_policy(_policy(heritage_credit=0.0))

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_connector_policy(["max_contact_insertions"])


class IdentityTests(unittest.TestCase):
    def test_a_good_identity_reads_back(self):
        identity = validate_connector_identity(_case())
        self.assertEqual(identity["insert_arrangement"], "10-way-size-20")
        self.assertAlmostEqual(identity["rated_contact_current_a"], 5.0, places=9)

    def test_zero_rated_contact_current_refused(self):
        with self.assertRaises(ValueError):
            validate_connector_identity(_case(rated_contact_current_a=0.0))

    def test_zero_rated_mating_cycles_refused(self):
        with self.assertRaises(ValueError):
            validate_connector_identity(_case(rated_mating_cycles=0.0))

    def test_negative_planned_matings_refused(self):
        with self.assertRaises(ValueError):
            validate_connector_identity(_case(planned_mating_cycles=-4.0))

    def test_non_string_connector_reference_refused(self):
        with self.assertRaises(ValueError):
            validate_connector_identity(_case(connector_reference=41))


class ContactValidationTests(unittest.TestCase):
    def test_a_good_contact_reads_back(self):
        record = validate_contact_record(_contact("p01", energised=True, current=1.2))
        self.assertEqual(record["termination"], CRIMP_REMOVABLE_CONTACT)
        self.assertAlmostEqual(record["current_a"], 1.2, places=9)

    def test_a_solder_cup_termination_is_recognised(self):
        record = validate_contact_record(
            _contact("p02", termination=SOLDER_CUP_REMOVABLE_CONTACT)
        )
        self.assertEqual(record["termination"], SOLDER_CUP_REMOVABLE_CONTACT)

    def test_unrecognised_termination_refused(self):
        with self.assertRaises(ValueError):
            validate_contact_record(_contact("p03", termination="twisted-together"))

    def test_a_blank_position_refused(self):
        with self.assertRaises(ValueError):
            validate_contact_record(_contact("   "))

    def test_a_position_both_spare_and_energised_refused(self):
        with self.assertRaises(ValueError):
            validate_contact_record(
                _contact("p04", energised=True, current=1.0, spare=True)
            )

    def test_an_energised_position_carrying_nothing_refused(self):
        with self.assertRaises(ValueError):
            validate_contact_record(_contact("p05", energised=True, current=0.0))

    def test_a_negative_insertion_count_refused(self):
        with self.assertRaises(ValueError):
            validate_contact_record(_contact("p06", insertions=-1))

    def test_a_fractional_insertion_count_refused(self):
        with self.assertRaises(ValueError):
            validate_contact_record(_contact("p07", insertions=1.5))

    def test_duplicate_position_refused(self):
        with self.assertRaises(ValueError):
            validate_contacts([_contact("p01"), _contact("p01")])

    def test_empty_contact_list_refused(self):
        with self.assertRaises(ValueError):
            validate_contacts([])

    def test_non_sequence_contacts_refused(self):
        with self.assertRaises(ValueError):
            validate_contacts({"position": "p01"})


class DeratingTests(unittest.TestCase):
    def test_the_loading_fraction_counts_only_energised_positions(self):
        self.assertAlmostEqual(contact_loading_fraction(_contacts()), 0.6, places=9)
        self.assertEqual(len(energised_positions(_contacts())), 6)
        self.assertEqual(spare_positions(_contacts()), ("p09", "p10"))

    def test_the_loading_factor_follows_the_slope(self):
        self.assertAlmostEqual(contact_loading_factor(_contacts()), 0.82, places=9)

    def test_the_allowance_is_the_rating_derated_twice(self):
        self.assertAlmostEqual(
            allowed_contact_current_a(_case()), 5.0 * 0.5 * 0.82, places=9
        )

    def test_a_lightly_loaded_insert_allows_more_per_contact(self):
        light = _case(contacts=_boundary_contacts())
        self.assertGreater(
            allowed_contact_current_a(light), allowed_contact_current_a(_case())
        )

    def test_no_position_is_overloaded_in_a_sound_harness(self):
        self.assertEqual(overloaded_positions(_case()), ())

    def test_an_overloaded_position_is_named(self):
        case = _case(contacts=_contacts(current=3.0))
        self.assertEqual(len(overloaded_positions(case)), 6)

    def test_a_current_landing_exactly_on_the_allowance_is_within_it(self):
        case = _boundary_case()
        policy = _policy(contact_loading_slope=0.5)
        self.assertAlmostEqual(allowed_contact_current_a(case, policy), 1.5, places=9)
        self.assertEqual(overloaded_positions(case, policy), ())

    def test_the_insertion_limit_names_the_worked_positions(self):
        self.assertEqual(over_inserted_positions(_case()), ())
        contacts = _contacts()
        contacts[2]["insertion_count"] = 4
        self.assertEqual(over_inserted_positions(_case(contacts=contacts)), ("p03",))

    def test_a_contact_landing_exactly_on_the_insertion_limit_is_kept(self):
        contacts = _contacts()
        contacts[2]["insertion_count"] = 3
        self.assertEqual(over_inserted_positions(_case(contacts=contacts)), ())

    def test_the_mating_cycle_fraction_is_the_planned_share_of_the_rating(self):
        self.assertAlmostEqual(mating_cycle_fraction(_case()), 0.4, places=9)

    def test_the_spare_share_counts_only_unused_positions(self):
        self.assertAlmostEqual(spare_contact_share(_contacts()), 0.2, places=9)

    def test_a_position_inside_the_marginal_band_raises_an_advisory(self):
        advisories = current_advisories(_boundary_case(), _policy(contact_loading_slope=0.5))
        self.assertEqual(len(advisories), 5)
        self.assertIn("marginal band", advisories[0])

    def test_a_comfortable_harness_raises_no_advisory(self):
        self.assertEqual(current_advisories(_case()), ())


class EvidenceTests(unittest.TestCase):
    def test_every_required_subject_appears_in_the_disposition(self):
        self.assertEqual(set(evidence_disposition(_evidence())), set(REQUIRED_EVIDENCE))

    def test_a_complete_build_holds_every_subject(self):
        self.assertAlmostEqual(evidence_share(_evidence()), 1.0, places=9)
        self.assertEqual(absent_evidence(_evidence()), ())
        self.assertEqual(unrecorded_evidence(_evidence()), ())
        self.assertEqual(len(held_evidence(_evidence())), len(REQUIRED_EVIDENCE))

    def test_a_heritage_claim_is_named_and_credited_below_one(self):
        self.assertEqual(
            heritage_evidence(_evidence()), (CONTACT_ARRANGEMENT_AND_KEYING_RECORD,)
        )
        disposition = evidence_disposition(_evidence())
        self.assertEqual(
            disposition[CONTACT_ARRANGEMENT_AND_KEYING_RECORD]["state"],
            HELD_AGAINST_HERITAGE,
        )
        self.assertEqual(
            disposition[CONTACT_RETENTION_FORCE_VERIFICATION]["state"], HELD_DIRECTLY
        )
        self.assertAlmostEqual(
            weighted_evidence(_evidence()), _expected_weighted(), places=9
        )

    def test_a_heritage_claim_naming_no_connector_is_unrecorded(self):
        records = _evidence()
        records[5] = _heritage(CONTACT_ARRANGEMENT_AND_KEYING_RECORD, connector=" ")
        self.assertEqual(
            unrecorded_evidence(records), (CONTACT_ARRANGEMENT_AND_KEYING_RECORD,)
        )
        self.assertEqual(
            evidence_disposition(records)[CONTACT_ARRANGEMENT_AND_KEYING_RECORD]["state"],
            DECLARED_WITHOUT_RECORD,
        )

    def test_a_subject_with_no_record_reference_is_unrecorded(self):
        records = _evidence()
        records[0] = _direct(CONTACT_RETENTION_FORCE_VERIFICATION, record="")
        self.assertEqual(
            unrecorded_evidence(records), (CONTACT_RETENTION_FORCE_VERIFICATION,)
        )

    def test_a_missing_subject_is_named_absent(self):
        records = _evidence()[:4]
        self.assertEqual(
            absent_evidence(records),
            (INSULATION_RESISTANCE_MEASUREMENT, CONTACT_ARRANGEMENT_AND_KEYING_RECORD),
        )
        self.assertEqual(
            evidence_disposition(records)[INSULATION_RESISTANCE_MEASUREMENT]["state"],
            ABSENT,
        )

    def test_a_record_that_is_both_direct_and_heritage_is_refused(self):
        entry = _heritage(MATING_CYCLE_LOG)
        entry["record_reference"] = "MATE-LOG-19"
        with self.assertRaises(ValueError):
            validate_evidence_record(entry)

    def test_unrecognised_evidence_subject_refused(self):
        with self.assertRaises(ValueError):
            validate_evidence_record(_direct("looks-fine-to-me"))

    def test_duplicate_evidence_subject_refused(self):
        with self.assertRaises(ValueError):
            validate_evidence([_direct(MATING_CYCLE_LOG), _direct(MATING_CYCLE_LOG)])

    def test_empty_evidence_list_refused(self):
        with self.assertRaises(ValueError):
            validate_evidence([])


class AssessmentTests(unittest.TestCase):
    def test_a_sound_connector_meets_the_class_scope(self):
        result = assess_connector_application(_case())
        self.assertEqual(result["verdict"], CONNECTOR_MEETS_CLASS_TWO_SCOPE)
        self.assertAlmostEqual(result["contact_loading_fraction"], 0.6, places=9)
        self.assertAlmostEqual(
            result["allowed_contact_current_a"], 5.0 * 0.5 * 0.82, places=9
        )
        self.assertAlmostEqual(result["weighted_evidence"], _expected_weighted(), places=9)

    def test_a_connector_with_no_reference_is_not_identified(self):
        result = assess_connector_application(_case(connector_reference="  "))
        self.assertEqual(result["verdict"], CONNECTOR_NOT_IDENTIFIED)
        self.assertTrue(result["findings"])

    def test_a_connector_with_no_removal_tool_is_not_identified(self):
        result = assess_connector_application(_case(removal_tool_reference=""))
        self.assertEqual(result["verdict"], CONNECTOR_NOT_IDENTIFIED)

    def test_the_removal_tool_requirement_may_be_waived_by_policy(self):
        result = assess_connector_application(
            _case(removal_tool_reference=""),
            _policy(require_removal_tool_reference=False),
        )
        self.assertEqual(result["verdict"], CONNECTOR_MEETS_CLASS_TWO_SCOPE)

    def test_a_connector_with_no_contacts_declared_is_not_identified(self):
        case = _case()
        del case["contacts"]
        result = assess_connector_application(case)
        self.assertEqual(result["verdict"], CONNECTOR_NOT_IDENTIFIED)

    def test_a_worked_contact_closes_the_assessment_on_the_insertion_limit(self):
        contacts = _contacts()
        contacts[1]["insertion_count"] = 5
        result = assess_connector_application(_case(contacts=contacts))
        self.assertEqual(result["verdict"], CONTACT_INSERTION_LIMIT_EXCEEDED)
        self.assertEqual(result["over_inserted_positions"], ("p02",))

    def test_every_overloaded_position_is_named_not_only_the_first(self):
        result = assess_connector_application(_case(contacts=_contacts(current=3.0)))
        self.assertEqual(result["verdict"], CONNECTOR_CURRENT_DERATING_EXCEEDED)
        self.assertEqual(len(result["overloaded_positions"]), 6)

    def test_a_spent_mating_life_closes_the_assessment(self):
        result = assess_connector_application(_case(planned_mating_cycles=400.0))
        self.assertEqual(result["verdict"], CONNECTOR_DURABILITY_CONSUMED)
        self.assertAlmostEqual(result["mating_cycle_fraction"], 0.8, places=9)

    def test_a_mating_plan_landing_exactly_on_the_cap_is_admissible(self):
        result = assess_connector_application(_case(planned_mating_cycles=250.0))
        self.assertAlmostEqual(result["mating_cycle_fraction"], 0.5, places=9)
        self.assertEqual(result["verdict"], CONNECTOR_MEETS_CLASS_TWO_SCOPE)

    def test_an_insert_with_no_spare_provision_closes_the_assessment(self):
        contacts = _contacts()
        contacts[8]["spare"] = False
        contacts[9]["spare"] = False
        result = assess_connector_application(_case(contacts=contacts))
        self.assertEqual(result["verdict"], CONNECTOR_SPARE_PROVISION_SHORT)
        self.assertAlmostEqual(result["spare_contact_share"], 0.0, places=9)

    def test_a_spare_share_landing_exactly_on_the_floor_is_admissible(self):
        result = assess_connector_application(
            _case(), _policy(min_spare_contact_share=0.2)
        )
        self.assertAlmostEqual(result["spare_contact_share"], 0.2, places=9)
        self.assertEqual(result["verdict"], CONNECTOR_MEETS_CLASS_TWO_SCOPE)

    def test_a_build_with_no_evidence_at_all_is_short(self):
        case = _case()
        del case["evidence"]
        result = assess_connector_application(case)
        self.assertEqual(result["verdict"], CONNECTOR_EVIDENCE_SHORT)

    def test_every_missing_subject_is_named_not_only_the_first(self):
        result = assess_connector_application(_case(evidence=_evidence()[:3]))
        self.assertEqual(result["verdict"], CONNECTOR_EVIDENCE_SHORT)
        self.assertEqual(len(result["absent_evidence"]), 3)

    def test_a_build_documented_entirely_against_heritage_fails_the_credit(self):
        records = [_heritage(subject) for subject in REQUIRED_EVIDENCE]
        result = assess_connector_application(
            _case(evidence=records), _policy(min_weighted_evidence=0.8)
        )
        self.assertEqual(result["verdict"], CONNECTOR_EVIDENCE_SHORT)
        self.assertAlmostEqual(result["evidence_share"], 1.0, places=9)
        self.assertAlmostEqual(
            result["weighted_evidence"],
            DEFAULT_CONNECTOR_POLICY["heritage_credit"],
            places=9,
        )

    def test_advisories_travel_with_a_passing_verdict(self):
        result = assess_connector_application(
            _boundary_case(), _policy(contact_loading_slope=0.5)
        )
        self.assertEqual(result["verdict"], CONNECTOR_MEETS_CLASS_TWO_SCOPE)
        self.assertEqual(len(result["advisories"]), 5)

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_connector_application(["connector_reference"])


if __name__ == "__main__":
    unittest.main()
