"""Contract tests for the clause 6.6.6 class 3 connector selection and sourcing.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused selection policy,
a harness with no reference or no candidate family, a candidate short of
current, short of spare positions or standing on no specification at all,
a contact lot from an unidentified source, an alternative lot with no
interchangeability record, a contact supply that cannot fill the insert, a
sourcing mix below the manufacturer floor, and evidence that is absent,
unrecorded or carried entirely on supplier declarations.
"""

import unittest

from q6013_class_3_connectors_logic import (
    ABSENT,
    CIRCULAR_BAYONET_COUPLING,
    CONNECTOR_LOT_TRACEABILITY_RECORD,
    CONNECTOR_MANUFACTURER_SOURCE,
    CONNECTOR_OUTGASSING_SCREENING_RECORD,
    CONNECTOR_SPECIFICATION_REFERENCE,
    CONTACT_PLATING_AND_BASE_METAL_RECORD,
    CONTACT_SOURCING_CREDIT_SHORT,
    CONTACT_SOURCING_NOT_ESTABLISHED,
    CONTACT_SUPPLY_SHORT,
    CONTACT_TERMINATION_TOOL_REFERENCE,
    DECLARED_WITHOUT_A_RECORD,
    DEFAULT_SELECTION_POLICY,
    HELD_AS_A_PROJECT_RECORD,
    HELD_AS_A_SUPPLIER_DECLARATION,
    INTERCHANGEABLE_ALTERNATIVE_SOURCE,
    MANUFACTURER_CATALOGUE_ONLY,
    NO_ADMISSIBLE_CANDIDATE,
    NO_SPECIFICATION_HELD,
    QUALIFIED_TO_A_RECOGNISED_SPECIFICATION,
    RECTANGULAR_MICRO_D,
    RECTANGULAR_NANO_D,
    REQUIRED_SELECTION_EVIDENCE,
    SELECTION_EVIDENCE_SHORT,
    SELECTION_MEETS_CLASS_THREE_SCOPE,
    SELECTION_NOT_DECLARED,
    UNIDENTIFIED_SOURCE,
    absent_evidence,
    admissible_candidates,
    allowed_contact_current_a,
    assess_connector_selection,
    candidate_findings,
    candidate_score,
    current_headroom,
    declaration_evidence,
    evidence_disposition,
    evidence_share,
    headroom_advisories,
    held_evidence,
    manufacturer_sourced_share,
    position_loading_factor,
    position_loading_fraction,
    rank_candidates,
    selected_candidate,
    sourced_contact_count,
    sourcing_credit,
    spare_position_share,
    unidentified_source_lots,
    unrecorded_evidence,
    unsupported_alternative_lots,
    validate_candidate,
    validate_candidates,
    validate_circuit_demand,
    validate_contact_lot,
    validate_contact_lots,
    validate_evidence,
    validate_evidence_record,
    validate_selection_policy,
    weighted_evidence,
)


def _policy(**overrides):
    policy = dict(DEFAULT_SELECTION_POLICY)
    policy.update(overrides)
    return policy


def _candidate(reference, family=RECTANGULAR_MICRO_D,
               standing=QUALIFIED_TO_A_RECOGNISED_SPECIFICATION,
               positions=15, rated=3.0):
    return {
        "reference": reference,
        "family": family,
        "standing": standing,
        "insert_positions": positions,
        "rated_contact_current_a": rated,
    }


def _candidates():
    return [
        _candidate("CON-A"),
        _candidate(
            "CON-B",
            family=CIRCULAR_BAYONET_COUPLING,
            standing=MANUFACTURER_CATALOGUE_ONLY,
            positions=19,
            rated=2.0,
        ),
        _candidate(
            "CON-C",
            family=RECTANGULAR_NANO_D,
            positions=13,
            rated=1.0,
        ),
    ]


def _lot(reference, source=CONNECTOR_MANUFACTURER_SOURCE, count=10, record=""):
    return {
        "lot_reference": reference,
        "source": source,
        "contact_count": count,
        "interchangeability_record": record,
    }


def _lots():
    return [
        _lot("LOT-M-1", count=10),
        _lot(
            "LOT-A-2",
            source=INTERCHANGEABLE_ALTERNATIVE_SOURCE,
            count=5,
            record="ICD-77",
        ),
    ]


def _record(subject, reference="SEL-REC-4"):
    return {
        "subject": subject,
        "held_as_supplier_declaration": False,
        "record_reference": reference,
        "supplier_reference": "",
    }


def _declaration(subject, supplier="SUP-DEC-19"):
    return {
        "subject": subject,
        "held_as_supplier_declaration": True,
        "record_reference": "",
        "supplier_reference": supplier,
    }


def _evidence():
    return [
        _record(CONNECTOR_SPECIFICATION_REFERENCE, "SPEC-08"),
        _record(CONTACT_PLATING_AND_BASE_METAL_RECORD, "PLATE-12"),
        _record(CONTACT_TERMINATION_TOOL_REFERENCE, "CRIMP-TOOL-3"),
        _record(CONNECTOR_LOT_TRACEABILITY_RECORD, "TRACE-41"),
        _declaration(CONNECTOR_OUTGASSING_SCREENING_RECORD),
    ]


def _expected_weighted():
    return (
        4.0 + DEFAULT_SELECTION_POLICY["supplier_declaration_credit"]
    ) / len(REQUIRED_SELECTION_EVIDENCE)


def _case(**overrides):
    case = {
        "harness_reference": "HRN-3-014",
        "circuit_count": 12,
        "max_circuit_current_a": 1.0,
        "candidates": _candidates(),
        "contact_lots": _lots(),
        "evidence": _evidence(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_selection_policy(DEFAULT_SELECTION_POLICY),
            DEFAULT_SELECTION_POLICY,
        )

    def test_zero_current_derating_refused(self):
        with self.assertRaises(ValueError):
            validate_selection_policy(_policy(contact_current_derating_factor=0.0))

    def test_a_loading_slope_of_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_selection_policy(_policy(contact_loading_slope=1.0))

    def test_a_spare_share_of_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_selection_policy(_policy(min_spare_position_share=1.0))

    def test_an_alternative_credit_of_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_selection_policy(_policy(alternative_source_credit=1.0))

    def test_zero_alternative_credit_refused(self):
        with self.assertRaises(ValueError):
            validate_selection_policy(_policy(alternative_source_credit=0.0))

    def test_a_declaration_credit_of_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_selection_policy(_policy(supplier_declaration_credit=1.0))

    def test_weighted_floor_above_the_share_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_selection_policy(
                _policy(min_evidence_share=0.4, min_weighted_evidence=0.9)
            )

    def test_a_non_boolean_catalogue_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_selection_policy(_policy(accept_catalogue_only_family="yes"))

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_selection_policy(["contact_loading_slope"])


class DemandTests(unittest.TestCase):
    def test_a_good_demand_reads_back(self):
        demand = validate_circuit_demand(_case())
        self.assertEqual(demand["circuit_count"], 12)
        self.assertAlmostEqual(demand["max_circuit_current_a"], 1.0, places=9)

    def test_a_zero_circuit_count_refused(self):
        with self.assertRaises(ValueError):
            validate_circuit_demand(_case(circuit_count=0))

    def test_a_fractional_circuit_count_refused(self):
        with self.assertRaises(ValueError):
            validate_circuit_demand(_case(circuit_count=4.5))

    def test_a_zero_circuit_current_refused(self):
        with self.assertRaises(ValueError):
            validate_circuit_demand(_case(max_circuit_current_a=0.0))

    def test_a_non_string_harness_reference_refused(self):
        with self.assertRaises(ValueError):
            validate_circuit_demand(_case(harness_reference=14))


class CandidateValidationTests(unittest.TestCase):
    def test_a_good_candidate_reads_back(self):
        record = validate_candidate(_candidate("CON-A"))
        self.assertEqual(record["family"], RECTANGULAR_MICRO_D)
        self.assertEqual(record["insert_positions"], 15)

    def test_unrecognised_family_refused(self):
        with self.assertRaises(ValueError):
            validate_candidate(_candidate("CON-X", family="whatever-was-in-the-bin"))

    def test_unrecognised_standing_refused(self):
        with self.assertRaises(ValueError):
            validate_candidate(_candidate("CON-X", standing="looks-fine"))

    def test_a_blank_candidate_reference_refused(self):
        with self.assertRaises(ValueError):
            validate_candidate(_candidate("   "))

    def test_zero_insert_positions_refused(self):
        with self.assertRaises(ValueError):
            validate_candidate(_candidate("CON-X", positions=0))

    def test_zero_rated_contact_current_refused(self):
        with self.assertRaises(ValueError):
            validate_candidate(_candidate("CON-X", rated=0.0))

    def test_duplicate_candidate_refused(self):
        with self.assertRaises(ValueError):
            validate_candidates([_candidate("CON-A"), _candidate("CON-A")])

    def test_empty_candidate_list_refused(self):
        with self.assertRaises(ValueError):
            validate_candidates([])

    def test_non_sequence_candidates_refused(self):
        with self.assertRaises(ValueError):
            validate_candidates({"reference": "CON-A"})


class DeratingTests(unittest.TestCase):
    def test_the_loading_fraction_is_the_circuit_share_of_the_insert(self):
        self.assertAlmostEqual(
            position_loading_fraction(_candidate("CON-A"), _case()), 0.8, places=9
        )

    def test_the_loading_factor_follows_the_slope(self):
        self.assertAlmostEqual(
            position_loading_factor(_candidate("CON-A"), _case()), 0.8, places=9
        )

    def test_the_allowance_is_the_rating_derated_twice(self):
        self.assertAlmostEqual(
            allowed_contact_current_a(_candidate("CON-A"), _case()),
            3.0 * 0.6 * 0.8,
            places=9,
        )

    def test_a_roomier_insert_allows_more_per_contact_for_the_same_rating(self):
        tight = allowed_contact_current_a(_candidate("CON-A", positions=13), _case())
        roomy = allowed_contact_current_a(_candidate("CON-A", positions=30), _case())
        self.assertGreater(roomy, tight)

    def test_the_headroom_is_the_allowance_over_the_worst_circuit(self):
        self.assertAlmostEqual(
            current_headroom(_candidate("CON-A"), _case()), 1.44, places=9
        )

    def test_the_spare_share_counts_positions_left_after_every_circuit(self):
        self.assertAlmostEqual(
            spare_position_share(_candidate("CON-A"), _case()), 0.2, places=9
        )

    def test_an_insert_smaller_than_the_wire_list_returns_a_negative_spare(self):
        self.assertLess(
            spare_position_share(_candidate("CON-X", positions=10), _case()), 0.0
        )

    def test_the_loading_fraction_is_capped_at_a_full_insert(self):
        self.assertAlmostEqual(
            position_loading_fraction(_candidate("CON-X", positions=10), _case()),
            1.0,
            places=9,
        )


class CandidateFindingTests(unittest.TestCase):
    def test_a_sound_candidate_draws_no_finding(self):
        self.assertEqual(candidate_findings(_candidate("CON-A"), _case()), ())

    def test_a_candidate_on_no_specification_is_refused(self):
        findings = candidate_findings(
            _candidate("CON-X", standing=NO_SPECIFICATION_HELD), _case()
        )
        self.assertEqual(len(findings), 1)

    def test_a_catalogue_family_is_admissible_at_this_class_by_default(self):
        self.assertEqual(
            candidate_findings(
                _candidate(
                    "CON-B",
                    standing=MANUFACTURER_CATALOGUE_ONLY,
                    positions=19,
                    rated=2.0,
                ),
                _case(),
            ),
            (),
        )

    def test_a_project_may_declare_a_catalogue_family_insufficient(self):
        findings = candidate_findings(
            _candidate(
                "CON-B",
                standing=MANUFACTURER_CATALOGUE_ONLY,
                positions=19,
                rated=2.0,
            ),
            _case(),
            _policy(accept_catalogue_only_family=False),
        )
        self.assertEqual(len(findings), 1)

    def test_a_candidate_short_of_current_and_of_positions_reports_both(self):
        findings = candidate_findings(
            _candidate("CON-C", positions=13, rated=1.0), _case()
        )
        self.assertEqual(len(findings), 2)

    def test_a_headroom_landing_exactly_on_one_is_admissible(self):
        candidate = _candidate("CON-E", positions=15, rated=1.0)
        case = _case(max_circuit_current_a=0.48)
        self.assertAlmostEqual(current_headroom(candidate, case), 1.0, places=9)
        self.assertEqual(candidate_findings(candidate, case), ())

    def test_a_spare_share_landing_exactly_on_the_floor_is_admissible(self):
        candidate = _candidate("CON-F", positions=20, rated=3.0)
        case = _case(circuit_count=18)
        self.assertAlmostEqual(spare_position_share(candidate, case), 0.1, places=9)
        self.assertEqual(candidate_findings(candidate, case), ())


class RankingTests(unittest.TestCase):
    def test_only_admissible_candidates_are_ranked(self):
        self.assertEqual(
            tuple(r["reference"] for r in admissible_candidates(_case())),
            ("CON-A", "CON-B"),
        )

    def test_the_qualified_roomier_family_ranks_first(self):
        self.assertEqual(
            tuple(r["reference"] for r in rank_candidates(_case())),
            ("CON-A", "CON-B"),
        )

    def test_the_selection_picks_the_top_of_the_ranking(self):
        self.assertEqual(selected_candidate(_case())["reference"], "CON-A")

    def test_the_score_rewards_a_recognised_specification(self):
        qualified = candidate_score(_candidate("CON-A"), _case())
        catalogue = candidate_score(
            _candidate("CON-A2", standing=MANUFACTURER_CATALOGUE_ONLY), _case()
        )
        self.assertGreater(qualified, catalogue)

    def test_a_tie_is_broken_on_the_reference_so_the_ranking_is_repeatable(self):
        case = _case(
            candidates=[_candidate("CON-Z"), _candidate("CON-A"), _candidate("CON-M")]
        )
        self.assertEqual(
            tuple(r["reference"] for r in rank_candidates(case)),
            ("CON-A", "CON-M", "CON-Z"),
        )

    def test_no_admissible_candidate_selects_nothing(self):
        case = _case(candidates=[_candidate("CON-C", positions=13, rated=1.0)])
        self.assertIsNone(selected_candidate(case))

    def test_a_candidate_just_over_the_demand_raises_an_advisory(self):
        case = _case(
            candidates=[_candidate("CON-E", positions=15, rated=1.0)],
            max_circuit_current_a=0.44,
        )
        advisories = headroom_advisories(case)
        self.assertEqual(len(advisories), 1)
        self.assertIn("marginal band", advisories[0])

    def test_a_comfortable_selection_raises_no_advisory(self):
        self.assertEqual(
            headroom_advisories(_case(candidates=[_candidate("CON-A")])), ()
        )

    def test_a_tight_admissible_family_is_named_alongside_a_comfortable_one(self):
        advisories = headroom_advisories(_case())
        self.assertEqual(len(advisories), 1)
        self.assertIn("CON-B", advisories[0])


class SourcingTests(unittest.TestCase):
    def test_a_good_lot_reads_back(self):
        record = validate_contact_lot(_lot("LOT-M-1"))
        self.assertEqual(record["source"], CONNECTOR_MANUFACTURER_SOURCE)
        self.assertEqual(record["contact_count"], 10)

    def test_unrecognised_source_refused(self):
        with self.assertRaises(ValueError):
            validate_contact_lot(_lot("LOT-X", source="the-drawer"))

    def test_a_blank_lot_reference_refused(self):
        with self.assertRaises(ValueError):
            validate_contact_lot(_lot("  "))

    def test_a_zero_contact_count_refused(self):
        with self.assertRaises(ValueError):
            validate_contact_lot(_lot("LOT-X", count=0))

    def test_a_manufacturer_lot_citing_interchangeability_refused(self):
        with self.assertRaises(ValueError):
            validate_contact_lot(_lot("LOT-X", record="ICD-77"))

    def test_duplicate_lot_refused(self):
        with self.assertRaises(ValueError):
            validate_contact_lots([_lot("LOT-M-1"), _lot("LOT-M-1")])

    def test_empty_lot_list_refused(self):
        with self.assertRaises(ValueError):
            validate_contact_lots([])

    def test_the_sourced_count_adds_every_lot(self):
        self.assertEqual(sourced_contact_count(_lots()), 15)

    def test_the_manufacturer_share_is_taken_over_contacts_not_lots(self):
        self.assertAlmostEqual(manufacturer_sourced_share(_lots()), 10.0 / 15.0,
                               places=9)

    def test_an_alternative_lot_with_a_record_is_credited_below_a_manufacturer_lot(self):
        self.assertAlmostEqual(
            sourcing_credit(_lots()),
            (10.0 + 5.0 * DEFAULT_SELECTION_POLICY["alternative_source_credit"]) / 15.0,
            places=9,
        )

    def test_an_alternative_lot_with_no_record_is_named(self):
        lots = _lots()
        lots[1]["interchangeability_record"] = " "
        self.assertEqual(unsupported_alternative_lots(lots), ("LOT-A-2",))

    def test_an_unidentified_lot_is_named(self):
        lots = _lots() + [_lot("LOT-U-3", source=UNIDENTIFIED_SOURCE, count=4)]
        self.assertEqual(unidentified_source_lots(lots), ("LOT-U-3",))
        self.assertAlmostEqual(sourcing_credit(lots), 13.0 / 19.0, places=9)


class EvidenceTests(unittest.TestCase):
    def test_every_required_subject_appears_in_the_disposition(self):
        self.assertEqual(
            set(evidence_disposition(_evidence())), set(REQUIRED_SELECTION_EVIDENCE)
        )

    def test_a_complete_selection_holds_every_subject(self):
        self.assertAlmostEqual(evidence_share(_evidence()), 1.0, places=9)
        self.assertEqual(absent_evidence(_evidence()), ())
        self.assertEqual(unrecorded_evidence(_evidence()), ())
        self.assertEqual(
            len(held_evidence(_evidence())), len(REQUIRED_SELECTION_EVIDENCE)
        )

    def test_a_supplier_declaration_is_named_and_credited_below_one(self):
        self.assertEqual(
            declaration_evidence(_evidence()),
            (CONNECTOR_OUTGASSING_SCREENING_RECORD,),
        )
        disposition = evidence_disposition(_evidence())
        self.assertEqual(
            disposition[CONNECTOR_OUTGASSING_SCREENING_RECORD]["state"],
            HELD_AS_A_SUPPLIER_DECLARATION,
        )
        self.assertEqual(
            disposition[CONNECTOR_SPECIFICATION_REFERENCE]["state"],
            HELD_AS_A_PROJECT_RECORD,
        )
        self.assertAlmostEqual(
            weighted_evidence(_evidence()), _expected_weighted(), places=9
        )

    def test_a_declaration_naming_no_supplier_is_unrecorded(self):
        records = _evidence()
        records[4] = _declaration(CONNECTOR_OUTGASSING_SCREENING_RECORD, supplier=" ")
        self.assertEqual(
            unrecorded_evidence(records), (CONNECTOR_OUTGASSING_SCREENING_RECORD,)
        )
        self.assertEqual(
            evidence_disposition(records)[CONNECTOR_OUTGASSING_SCREENING_RECORD][
                "state"
            ],
            DECLARED_WITHOUT_A_RECORD,
        )

    def test_a_subject_with_no_record_reference_is_unrecorded(self):
        records = _evidence()
        records[0] = _record(CONNECTOR_SPECIFICATION_REFERENCE, reference="")
        self.assertEqual(
            unrecorded_evidence(records), (CONNECTOR_SPECIFICATION_REFERENCE,)
        )

    def test_a_missing_subject_is_named_absent(self):
        records = _evidence()[:3]
        self.assertEqual(
            absent_evidence(records),
            (CONNECTOR_LOT_TRACEABILITY_RECORD, CONNECTOR_OUTGASSING_SCREENING_RECORD),
        )
        self.assertEqual(
            evidence_disposition(records)[CONNECTOR_LOT_TRACEABILITY_RECORD]["state"],
            ABSENT,
        )

    def test_a_record_that_is_both_project_and_supplier_held_is_refused(self):
        entry = _declaration(CONNECTOR_LOT_TRACEABILITY_RECORD)
        entry["record_reference"] = "TRACE-41"
        with self.assertRaises(ValueError):
            validate_evidence_record(entry)

    def test_unrecognised_evidence_subject_refused(self):
        with self.assertRaises(ValueError):
            validate_evidence_record(_record("the-usual-paperwork"))

    def test_duplicate_evidence_subject_refused(self):
        with self.assertRaises(ValueError):
            validate_evidence(
                [
                    _record(CONNECTOR_SPECIFICATION_REFERENCE),
                    _record(CONNECTOR_SPECIFICATION_REFERENCE),
                ]
            )

    def test_empty_evidence_list_refused(self):
        with self.assertRaises(ValueError):
            validate_evidence([])


class AssessmentTests(unittest.TestCase):
    def test_a_sound_selection_meets_the_class_scope(self):
        result = assess_connector_selection(_case())
        self.assertEqual(result["verdict"], SELECTION_MEETS_CLASS_THREE_SCOPE)
        self.assertEqual(result["selected_connector"], "CON-A")
        self.assertEqual(result["selected_family"], RECTANGULAR_MICRO_D)
        self.assertAlmostEqual(result["current_headroom"], 1.44, places=9)
        self.assertAlmostEqual(result["spare_position_share"], 0.2, places=9)
        self.assertAlmostEqual(
            result["weighted_evidence"], _expected_weighted(), places=9
        )

    def test_the_rejected_candidate_is_named_on_a_passing_verdict(self):
        result = assess_connector_selection(_case())
        self.assertEqual(result["rejected_candidates"], ("CON-C",))

    def test_a_harness_with_no_reference_is_not_declared(self):
        result = assess_connector_selection(_case(harness_reference="  "))
        self.assertEqual(result["verdict"], SELECTION_NOT_DECLARED)
        self.assertTrue(result["findings"])

    def test_a_harness_with_no_candidates_declared_is_not_declared(self):
        case = _case()
        del case["candidates"]
        result = assess_connector_selection(case)
        self.assertEqual(result["verdict"], SELECTION_NOT_DECLARED)

    def test_every_reason_is_reported_when_no_candidate_is_admissible(self):
        case = _case(
            candidates=[
                _candidate("CON-C", positions=13, rated=1.0),
                _candidate("CON-D", standing=NO_SPECIFICATION_HELD),
            ]
        )
        result = assess_connector_selection(case)
        self.assertEqual(result["verdict"], NO_ADMISSIBLE_CANDIDATE)
        self.assertEqual(len(result["findings"]), 3)

    def test_a_harness_with_no_contact_lots_has_no_sourcing(self):
        case = _case()
        del case["contact_lots"]
        result = assess_connector_selection(case)
        self.assertEqual(result["verdict"], CONTACT_SOURCING_NOT_ESTABLISHED)

    def test_an_unidentified_lot_closes_the_assessment_on_sourcing(self):
        lots = _lots() + [_lot("LOT-U-3", source=UNIDENTIFIED_SOURCE, count=4)]
        result = assess_connector_selection(_case(contact_lots=lots))
        self.assertEqual(result["verdict"], CONTACT_SOURCING_NOT_ESTABLISHED)
        self.assertEqual(result["unidentified_source_lots"], ("LOT-U-3",))

    def test_an_alternative_lot_with_no_record_closes_the_assessment(self):
        lots = _lots()
        lots[1]["interchangeability_record"] = ""
        result = assess_connector_selection(_case(contact_lots=lots))
        self.assertEqual(result["verdict"], CONTACT_SOURCING_NOT_ESTABLISHED)
        self.assertEqual(result["unsupported_alternative_lots"], ("LOT-A-2",))

    def test_a_supply_smaller_than_the_wire_list_closes_the_assessment(self):
        result = assess_connector_selection(
            _case(contact_lots=[_lot("LOT-M-1", count=8)])
        )
        self.assertEqual(result["verdict"], CONTACT_SUPPLY_SHORT)
        self.assertEqual(result["sourced_contact_count"], 8)

    def test_a_supply_landing_exactly_on_the_wire_list_is_admissible(self):
        result = assess_connector_selection(
            _case(contact_lots=[_lot("LOT-M-1", count=12)])
        )
        self.assertEqual(result["verdict"], SELECTION_MEETS_CLASS_THREE_SCOPE)

    def test_a_mostly_alternative_sourced_harness_is_credit_short(self):
        lots = [
            _lot("LOT-M-1", count=3),
            _lot(
                "LOT-A-2",
                source=INTERCHANGEABLE_ALTERNATIVE_SOURCE,
                count=12,
                record="ICD-77",
            ),
        ]
        result = assess_connector_selection(_case(contact_lots=lots))
        self.assertEqual(result["verdict"], CONTACT_SOURCING_CREDIT_SHORT)
        self.assertAlmostEqual(
            result["manufacturer_sourced_share"], 3.0 / 15.0, places=9
        )

    def test_a_manufacturer_share_landing_exactly_on_the_floor_is_admissible(self):
        lots = [
            _lot("LOT-M-1", count=9),
            _lot(
                "LOT-A-2",
                source=INTERCHANGEABLE_ALTERNATIVE_SOURCE,
                count=9,
                record="ICD-77",
            ),
        ]
        result = assess_connector_selection(_case(contact_lots=lots))
        self.assertAlmostEqual(result["manufacturer_sourced_share"], 0.5, places=9)
        self.assertAlmostEqual(result["sourcing_credit"], 0.8, places=9)
        self.assertEqual(result["verdict"], SELECTION_MEETS_CLASS_THREE_SCOPE)

    def test_a_selection_with_no_evidence_at_all_is_short(self):
        case = _case()
        del case["evidence"]
        result = assess_connector_selection(case)
        self.assertEqual(result["verdict"], SELECTION_EVIDENCE_SHORT)

    def test_every_missing_subject_is_named_not_only_the_first(self):
        result = assess_connector_selection(_case(evidence=_evidence()[:2]))
        self.assertEqual(result["verdict"], SELECTION_EVIDENCE_SHORT)
        self.assertEqual(len(result["absent_evidence"]), 3)

    def test_a_selection_documented_entirely_on_declarations_fails_the_credit(self):
        records = [_declaration(subject) for subject in REQUIRED_SELECTION_EVIDENCE]
        result = assess_connector_selection(
            _case(evidence=records), _policy(min_weighted_evidence=0.8)
        )
        self.assertEqual(result["verdict"], SELECTION_EVIDENCE_SHORT)
        self.assertAlmostEqual(result["evidence_share"], 1.0, places=9)
        self.assertAlmostEqual(
            result["weighted_evidence"],
            DEFAULT_SELECTION_POLICY["supplier_declaration_credit"],
            places=9,
        )

    def test_an_evidence_share_landing_exactly_on_the_floor_is_admissible(self):
        result = assess_connector_selection(
            _case(evidence=_evidence()[:4]), _policy(min_weighted_evidence=0.8)
        )
        self.assertAlmostEqual(result["evidence_share"], 0.8, places=9)
        self.assertAlmostEqual(result["weighted_evidence"], 0.8, places=9)
        self.assertEqual(result["verdict"], SELECTION_MEETS_CLASS_THREE_SCOPE)

    def test_advisories_travel_with_a_passing_verdict(self):
        case = _case(
            candidates=[_candidate("CON-E", positions=15, rated=1.0)],
            max_circuit_current_a=0.44,
        )
        result = assess_connector_selection(case)
        self.assertEqual(result["verdict"], SELECTION_MEETS_CLASS_THREE_SCOPE)
        self.assertEqual(len(result["advisories"]), 1)

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_connector_selection(["harness_reference"])


if __name__ == "__main__":
    unittest.main()
