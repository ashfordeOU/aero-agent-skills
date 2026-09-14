"""Contract tests for the clause 5.6.7 class 2 high voltage application.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused high voltage
policy, a refused gas model, an application naming no part, a voltage under
the high voltage threshold, a voltage derating over the cap, a creepage or
clearance shorter than the applied voltage needs, a gas breakdown margin
under its floor when the assembly is powered while the pressure falls, an
encapsulated path that waives that check, and evidence that is absent,
unrecorded or carried entirely by analysis.
"""

import math
import unittest

from q6013_class_2_high_voltage_parts_logic import (
    ABSENT,
    CREEPAGE_AND_CLEARANCE_SURVEY,
    DECLARED_WITHOUT_RECORD,
    DEFAULT_GAS_MODEL,
    DEFAULT_HV_POLICY,
    HELD_AS_ANALYSIS,
    HELD_AS_MEASURED,
    HIGH_VOLTAGE_DESIGN_REVIEW_RECORD,
    HIGH_VOLTAGE_PART_DERATING_RECORD,
    HV_APPLICATION_NOT_DECLARED,
    HV_BELOW_THRESHOLD,
    HV_CREEPAGE_OR_CLEARANCE_SHORT,
    HV_EVIDENCE_SHORT,
    HV_MEETS_CLASS_TWO_SCOPE,
    HV_PASCHEN_MARGIN_SHORT,
    HV_VOLTAGE_DERATING_EXCEEDED,
    INSULATION_MATERIAL_OUTGASSING_DATA,
    PARTIAL_DISCHARGE_INCEPTION_MEASUREMENT,
    REQUIRED_EVIDENCE,
    VENTING_AND_DEPRESSURISATION_ANALYSIS,
    absent_evidence,
    analysis_evidence,
    assess_high_voltage_application,
    derating_advisories,
    evidence_disposition,
    evidence_share,
    governing_breakdown_voltage_v,
    held_evidence,
    is_vacuum_regime,
    paschen_breakdown_voltage_v,
    paschen_margin_factor,
    paschen_minimum_pressure_gap_pa_m,
    paschen_minimum_voltage_v,
    required_clearance_mm,
    required_creepage_mm,
    unrecorded_evidence,
    validate_evidence,
    validate_evidence_record,
    validate_gas_model,
    validate_hv_application,
    validate_hv_policy,
    voltage_derating_fraction,
    weighted_evidence,
)


def _policy(**overrides):
    policy = dict(DEFAULT_HV_POLICY)
    policy.update(overrides)
    return policy


def _model(**overrides):
    model = dict(DEFAULT_GAS_MODEL)
    model.update(overrides)
    return model


def _measured(subject, record="HV-REP-6"):
    return {
        "subject": subject,
        "held_by_analysis": False,
        "record_reference": record,
        "analysis_reference": "",
    }


def _analysed(subject, analysis="HV-ANA-12"):
    return {
        "subject": subject,
        "held_by_analysis": True,
        "record_reference": "",
        "analysis_reference": analysis,
    }


def _evidence():
    return [
        _measured(HIGH_VOLTAGE_DESIGN_REVIEW_RECORD, "HVDR-01"),
        _measured(PARTIAL_DISCHARGE_INCEPTION_MEASUREMENT, "PDIV-09"),
        _measured(INSULATION_MATERIAL_OUTGASSING_DATA, "OUT-03"),
        _analysed(VENTING_AND_DEPRESSURISATION_ANALYSIS),
        _measured(HIGH_VOLTAGE_PART_DERATING_RECORD, "DER-22"),
        _measured(CREEPAGE_AND_CLEARANCE_SURVEY, "CCS-14"),
    ]


def _expected_weighted():
    return (5.0 + DEFAULT_HV_POLICY["analysis_credit"]) / len(REQUIRED_EVIDENCE)


def _case(**overrides):
    case = {
        "application_reference": "HV-APP-2026-07",
        "part_reference": "CAP-HV-4K7",
        "applied_voltage_v": 1000.0,
        "rated_voltage_v": 3000.0,
        "creepage_distance_mm": 8.0,
        "clearance_distance_mm": 4.0,
        "gap_pressure_pa": 1.0e5,
        "powered_during_depressurisation": False,
        "fully_encapsulated": False,
        "evidence": _evidence(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_hv_policy(DEFAULT_HV_POLICY), DEFAULT_HV_POLICY)

    def test_zero_voltage_derating_cap_refused(self):
        with self.assertRaises(ValueError):
            validate_hv_policy(_policy(max_voltage_derating_fraction=0.0))

    def test_a_creepage_limit_above_the_clearance_limit_refused(self):
        with self.assertRaises(ValueError):
            validate_hv_policy(
                _policy(
                    creepage_field_limit_v_per_mm=600.0,
                    clearance_field_limit_v_per_mm=500.0,
                )
            )

    def test_a_paschen_margin_floor_below_one_refused(self):
        with self.assertRaises(ValueError):
            validate_hv_policy(_policy(min_paschen_margin_factor=0.8))

    def test_weighted_floor_above_the_share_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_hv_policy(_policy(min_evidence_share=0.5, min_weighted_evidence=0.9))

    def test_zero_analysis_credit_refused(self):
        with self.assertRaises(ValueError):
            validate_hv_policy(_policy(analysis_credit=0.0))

    def test_non_boolean_encapsulation_waiver_refused(self):
        with self.assertRaises(ValueError):
            validate_hv_policy(_policy(allow_encapsulation_to_waive_paschen="maybe"))

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_hv_policy(["high_voltage_threshold_v"])


class GasModelTests(unittest.TestCase):
    def test_default_gas_model_validates(self):
        self.assertIs(validate_gas_model(DEFAULT_GAS_MODEL), DEFAULT_GAS_MODEL)

    def test_a_secondary_emission_coefficient_at_one_refused(self):
        with self.assertRaises(ValueError):
            validate_gas_model(_model(secondary_emission_coefficient=1.0))

    def test_a_negative_townsend_constant_refused(self):
        with self.assertRaises(ValueError):
            validate_gas_model(_model(townsend_b_v_per_pa_m=-1.0))

    def test_non_mapping_gas_model_refused(self):
        with self.assertRaises(ValueError):
            validate_gas_model("air")


class ApplicationValidationTests(unittest.TestCase):
    def test_a_good_application_reads_back(self):
        application = validate_hv_application(_case())
        self.assertEqual(application["part_reference"], "CAP-HV-4K7")
        self.assertAlmostEqual(application["clearance_distance_mm"], 4.0, places=9)

    def test_a_creepage_shorter_than_the_clearance_refused(self):
        with self.assertRaises(ValueError):
            validate_hv_application(
                _case(creepage_distance_mm=2.0, clearance_distance_mm=4.0)
            )

    def test_zero_applied_voltage_refused(self):
        with self.assertRaises(ValueError):
            validate_hv_application(_case(applied_voltage_v=0.0))

    def test_zero_rated_voltage_refused(self):
        with self.assertRaises(ValueError):
            validate_hv_application(_case(rated_voltage_v=0.0))

    def test_zero_gap_pressure_refused(self):
        with self.assertRaises(ValueError):
            validate_hv_application(_case(gap_pressure_pa=0.0))

    def test_non_boolean_powered_declaration_refused(self):
        with self.assertRaises(ValueError):
            validate_hv_application(_case(powered_during_depressurisation="sometimes"))

    def test_non_mapping_case_refused_by_the_application_reader(self):
        with self.assertRaises(ValueError):
            validate_hv_application(["part_reference"])


class GeometryTests(unittest.TestCase):
    def test_the_derating_is_the_applied_share_of_the_rating(self):
        self.assertAlmostEqual(voltage_derating_fraction(_case()), 1.0 / 3.0, places=9)

    def test_the_required_creepage_follows_the_field_limit(self):
        self.assertAlmostEqual(required_creepage_mm(_case()), 5.0, places=9)

    def test_the_required_clearance_follows_its_own_field_limit(self):
        self.assertAlmostEqual(required_clearance_mm(_case()), 2.0, places=9)

    def test_a_surface_path_needs_more_distance_than_an_open_gap(self):
        self.assertGreater(required_creepage_mm(_case()), required_clearance_mm(_case()))

    def test_a_derating_landing_exactly_on_the_cap_is_admissible(self):
        result = assess_high_voltage_application(_case(applied_voltage_v=1500.0))
        self.assertAlmostEqual(result["voltage_derating_fraction"], 0.5, places=9)
        self.assertEqual(result["verdict"], HV_MEETS_CLASS_TWO_SCOPE)

    def test_a_creepage_landing_exactly_on_the_requirement_is_admissible(self):
        result = assess_high_voltage_application(_case(creepage_distance_mm=5.0))
        self.assertAlmostEqual(result["required_creepage_mm"], 5.0, places=9)
        self.assertEqual(result["verdict"], HV_MEETS_CLASS_TWO_SCOPE)

    def test_a_derating_inside_the_band_raises_an_advisory(self):
        advisories = derating_advisories(_case(applied_voltage_v=1450.0))
        self.assertEqual(len(advisories), 1)
        self.assertIn("marginal band", advisories[0])

    def test_a_comfortable_derating_raises_no_advisory(self):
        self.assertEqual(derating_advisories(_case()), ())


class PaschenTests(unittest.TestCase):
    def test_the_curve_minimum_sits_where_the_relation_says_it_does(self):
        self.assertAlmostEqual(
            paschen_minimum_pressure_gap_pa_m(), 0.11151287321847, places=9
        )
        self.assertAlmostEqual(paschen_minimum_voltage_v(), 305.26649043557, places=6)

    def test_the_breakdown_voltage_at_the_operating_point_is_computed(self):
        self.assertAlmostEqual(
            paschen_breakdown_voltage_v(1.0e5, 0.004), 119215.0776471383, places=3
        )

    def test_the_minimum_is_the_least_voltage_anywhere_on_the_curve(self):
        least = paschen_minimum_voltage_v()
        for product in (0.2, 0.5, 2.0, 20.0, 400.0):
            self.assertGreater(paschen_breakdown_voltage_v(product, 1.0), least)

    def test_below_the_minimum_no_gas_breakdown_is_sustained(self):
        self.assertTrue(is_vacuum_regime(1.0e-3, 0.004))
        self.assertEqual(paschen_breakdown_voltage_v(1.0e-3, 0.004), math.inf)

    def test_a_non_positive_gap_is_refused_by_the_relation(self):
        with self.assertRaises(ValueError):
            paschen_breakdown_voltage_v(1.0e5, 0.0)

    def test_an_unpowered_ascent_is_judged_at_the_operating_pressure(self):
        self.assertAlmostEqual(
            governing_breakdown_voltage_v(_case()), 119215.0776471383, places=3
        )

    def test_a_powered_ascent_is_judged_at_the_curve_minimum(self):
        case = _case(powered_during_depressurisation=True)
        self.assertAlmostEqual(
            governing_breakdown_voltage_v(case), paschen_minimum_voltage_v(), places=9
        )

    def test_the_margin_is_the_breakdown_voltage_over_the_applied_voltage(self):
        case = _case(
            powered_during_depressurisation=True,
            applied_voltage_v=paschen_minimum_voltage_v() / 2.0,
        )
        self.assertAlmostEqual(paschen_margin_factor(case), 2.0, places=9)


class EvidenceTests(unittest.TestCase):
    def test_every_required_subject_appears_in_the_disposition(self):
        self.assertEqual(set(evidence_disposition(_evidence())), set(REQUIRED_EVIDENCE))

    def test_a_complete_application_holds_every_subject(self):
        self.assertAlmostEqual(evidence_share(_evidence()), 1.0, places=9)
        self.assertEqual(absent_evidence(_evidence()), ())
        self.assertEqual(unrecorded_evidence(_evidence()), ())
        self.assertEqual(len(held_evidence(_evidence())), len(REQUIRED_EVIDENCE))

    def test_an_analysis_is_named_and_credited_below_a_measurement(self):
        self.assertEqual(
            analysis_evidence(_evidence()), (VENTING_AND_DEPRESSURISATION_ANALYSIS,)
        )
        disposition = evidence_disposition(_evidence())
        self.assertEqual(
            disposition[VENTING_AND_DEPRESSURISATION_ANALYSIS]["state"], HELD_AS_ANALYSIS
        )
        self.assertEqual(
            disposition[PARTIAL_DISCHARGE_INCEPTION_MEASUREMENT]["state"],
            HELD_AS_MEASURED,
        )
        self.assertAlmostEqual(
            weighted_evidence(_evidence()), _expected_weighted(), places=9
        )

    def test_an_analysis_claim_naming_no_analysis_is_unrecorded(self):
        records = _evidence()
        records[3] = _analysed(VENTING_AND_DEPRESSURISATION_ANALYSIS, analysis=" ")
        self.assertEqual(
            unrecorded_evidence(records), (VENTING_AND_DEPRESSURISATION_ANALYSIS,)
        )
        self.assertEqual(
            evidence_disposition(records)[VENTING_AND_DEPRESSURISATION_ANALYSIS]["state"],
            DECLARED_WITHOUT_RECORD,
        )

    def test_a_subject_with_no_record_reference_is_unrecorded(self):
        records = _evidence()
        records[1] = _measured(PARTIAL_DISCHARGE_INCEPTION_MEASUREMENT, record="")
        self.assertEqual(
            unrecorded_evidence(records), (PARTIAL_DISCHARGE_INCEPTION_MEASUREMENT,)
        )

    def test_a_missing_subject_is_named_absent(self):
        records = _evidence()[:4]
        self.assertEqual(
            absent_evidence(records),
            (HIGH_VOLTAGE_PART_DERATING_RECORD, CREEPAGE_AND_CLEARANCE_SURVEY),
        )
        self.assertEqual(
            evidence_disposition(records)[CREEPAGE_AND_CLEARANCE_SURVEY]["state"], ABSENT
        )

    def test_a_record_that_is_both_measured_and_analysed_is_refused(self):
        entry = _analysed(INSULATION_MATERIAL_OUTGASSING_DATA)
        entry["record_reference"] = "OUT-03"
        with self.assertRaises(ValueError):
            validate_evidence_record(entry)

    def test_unrecognised_evidence_subject_refused(self):
        with self.assertRaises(ValueError):
            validate_evidence_record(_measured("looked-at-it-once"))

    def test_duplicate_evidence_subject_refused(self):
        with self.assertRaises(ValueError):
            validate_evidence(
                [
                    _measured(CREEPAGE_AND_CLEARANCE_SURVEY),
                    _measured(CREEPAGE_AND_CLEARANCE_SURVEY),
                ]
            )

    def test_empty_evidence_list_refused(self):
        with self.assertRaises(ValueError):
            validate_evidence([])


class AssessmentTests(unittest.TestCase):
    def test_a_sound_application_meets_the_class_scope(self):
        result = assess_high_voltage_application(_case())
        self.assertEqual(result["verdict"], HV_MEETS_CLASS_TWO_SCOPE)
        self.assertAlmostEqual(result["required_creepage_mm"], 5.0, places=9)
        self.assertAlmostEqual(result["weighted_evidence"], _expected_weighted(), places=9)
        self.assertFalse(result["paschen_waived_by_encapsulation"])

    def test_an_application_naming_no_part_is_not_declared(self):
        result = assess_high_voltage_application(_case(part_reference="  "))
        self.assertEqual(result["verdict"], HV_APPLICATION_NOT_DECLARED)
        self.assertTrue(result["findings"])

    def test_a_voltage_under_the_threshold_leaves_the_clause(self):
        result = assess_high_voltage_application(_case(applied_voltage_v=50.0))
        self.assertEqual(result["verdict"], HV_BELOW_THRESHOLD)
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["advisories"]), 1)

    def test_a_voltage_landing_exactly_on_the_threshold_stays_in_the_clause(self):
        result = assess_high_voltage_application(_case(applied_voltage_v=100.0))
        self.assertNotEqual(result["verdict"], HV_BELOW_THRESHOLD)

    def test_an_underrated_part_closes_the_assessment_on_the_derating(self):
        result = assess_high_voltage_application(_case(rated_voltage_v=1200.0))
        self.assertEqual(result["verdict"], HV_VOLTAGE_DERATING_EXCEEDED)

    def test_a_short_creepage_closes_the_assessment(self):
        result = assess_high_voltage_application(
            _case(creepage_distance_mm=4.0, clearance_distance_mm=4.0)
        )
        self.assertEqual(result["verdict"], HV_CREEPAGE_OR_CLEARANCE_SHORT)

    def test_both_short_distances_are_reported_not_only_the_first(self):
        result = assess_high_voltage_application(
            _case(creepage_distance_mm=1.0, clearance_distance_mm=1.0)
        )
        self.assertEqual(result["verdict"], HV_CREEPAGE_OR_CLEARANCE_SHORT)
        self.assertEqual(len(result["findings"]), 2)

    def test_a_powered_ascent_closes_the_assessment_on_the_curve_minimum(self):
        result = assess_high_voltage_application(
            _case(powered_during_depressurisation=True)
        )
        self.assertEqual(result["verdict"], HV_PASCHEN_MARGIN_SHORT)
        self.assertIn("powered while the pressure falls", result["findings"][0])

    def test_a_margin_landing_exactly_on_the_floor_is_admissible(self):
        result = assess_high_voltage_application(
            _case(
                powered_during_depressurisation=True,
                applied_voltage_v=paschen_minimum_voltage_v() / 2.0,
            )
        )
        self.assertAlmostEqual(result["paschen_margin_factor"], 2.0, places=9)
        self.assertEqual(result["verdict"], HV_MEETS_CLASS_TWO_SCOPE)

    def test_encapsulation_waives_the_gas_breakdown_check(self):
        result = assess_high_voltage_application(
            _case(powered_during_depressurisation=True, fully_encapsulated=True)
        )
        self.assertEqual(result["verdict"], HV_MEETS_CLASS_TWO_SCOPE)
        self.assertTrue(result["paschen_waived_by_encapsulation"])
        self.assertIsNone(result["paschen_margin_factor"])

    def test_the_encapsulation_waiver_may_be_withheld_by_policy(self):
        result = assess_high_voltage_application(
            _case(powered_during_depressurisation=True, fully_encapsulated=True),
            _policy(allow_encapsulation_to_waive_paschen=False),
        )
        self.assertEqual(result["verdict"], HV_PASCHEN_MARGIN_SHORT)

    def test_an_application_with_no_evidence_at_all_is_short(self):
        case = _case()
        del case["evidence"]
        result = assess_high_voltage_application(case)
        self.assertEqual(result["verdict"], HV_EVIDENCE_SHORT)

    def test_every_missing_subject_is_named_not_only_the_first(self):
        result = assess_high_voltage_application(_case(evidence=_evidence()[:3]))
        self.assertEqual(result["verdict"], HV_EVIDENCE_SHORT)
        self.assertEqual(len(result["absent_evidence"]), 3)

    def test_an_application_argued_entirely_on_paper_fails_the_credit(self):
        records = [_analysed(subject) for subject in REQUIRED_EVIDENCE]
        result = assess_high_voltage_application(
            _case(evidence=records), _policy(min_weighted_evidence=0.8)
        )
        self.assertEqual(result["verdict"], HV_EVIDENCE_SHORT)
        self.assertAlmostEqual(result["evidence_share"], 1.0, places=9)
        self.assertAlmostEqual(
            result["weighted_evidence"], DEFAULT_HV_POLICY["analysis_credit"], places=9
        )

    def test_advisories_travel_with_a_passing_verdict(self):
        result = assess_high_voltage_application(_case(applied_voltage_v=1450.0))
        self.assertEqual(result["verdict"], HV_MEETS_CLASS_TWO_SCOPE)
        self.assertEqual(len(result["advisories"]), 1)

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_high_voltage_application(["part_reference"])


if __name__ == "__main__":
    unittest.main()
