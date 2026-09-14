"""Contract tests for the clause 6.6.7 class 3 high voltage and high power usage.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused application
policy, an application naming no part, an application under both thresholds,
each axis engaging on its own, a voltage utilization over the cap, a surface
path shorter than the applied voltage demands, a discharge inception too
close to the peak working voltage, a case off the end of its derating curve,
a dissipation over the derated allowance, a junction over the rating less the
class margin, and evidence that is absent, unrecorded, or carried entirely on
analyses and supplier declarations.
"""

import unittest

from q6013_class_3_high_voltage_parts_logic import (
    ABSENT,
    APPLICATION_EVIDENCE_SHORT,
    APPLICATION_NOT_DECLARED,
    BELOW_BOTH_THRESHOLDS,
    CONFORMAL_COATING_AND_VENTING_RECORD,
    DECLARED_WITHOUT_A_RECORD,
    DEFAULT_APPLICATION_POLICY,
    DISCHARGE_MARGIN_SHORT,
    HELD_AS_AN_ANALYSIS,
    HELD_AS_A_MEASUREMENT,
    HELD_AS_A_SUPPLIER_DECLARATION,
    HIGH_POWER_AXIS,
    HIGH_POWER_THERMAL_SURVEY_RECORD,
    HIGH_VOLTAGE_AXIS,
    HIGH_VOLTAGE_DIELECTRIC_WITHSTAND_RECORD,
    INSULATION_SPACING_LAYOUT_RECORD,
    INSULATION_SPACING_SHORT,
    JUNCTION_TEMPERATURE_EXCEEDED,
    MEETS_CLASS_THREE_SCOPE,
    PARTIAL_DISCHARGE_INCEPTION_RECORD,
    POWER_DERATING_EXCEEDED,
    REQUIRED_APPLICATION_EVIDENCE,
    VOLTAGE_AND_POWER_DERATING_ANALYSIS,
    VOLTAGE_DERATING_EXCEEDED,
    absent_evidence,
    allowed_dissipation_w,
    allowed_junction_temperature_c,
    analysis_evidence,
    assess_high_voltage_application,
    declaration_evidence,
    discharge_margin,
    engaged_axes,
    evidence_disposition,
    evidence_share,
    held_evidence,
    junction_temperature_c,
    measured_evidence,
    peak_working_voltage_v,
    required_creepage_mm,
    thermal_derating_factor,
    unrecorded_evidence,
    utilization_advisories,
    validate_application,
    validate_application_policy,
    validate_evidence,
    validate_evidence_record,
    voltage_utilization,
    weighted_evidence,
)


def _policy(**overrides):
    policy = dict(DEFAULT_APPLICATION_POLICY)
    policy.update(overrides)
    return policy


def _measurement(subject, reference="HV-MEAS-6"):
    return {
        "subject": subject,
        "held_as_analysis": False,
        "held_as_supplier_declaration": False,
        "record_reference": reference,
    }


def _analysis(subject, reference="HV-ANA-2"):
    return {
        "subject": subject,
        "held_as_analysis": True,
        "held_as_supplier_declaration": False,
        "record_reference": reference,
    }


def _declaration(subject, reference="HV-DEC-9"):
    return {
        "subject": subject,
        "held_as_analysis": False,
        "held_as_supplier_declaration": True,
        "record_reference": reference,
    }


def _evidence():
    return [
        _measurement(HIGH_VOLTAGE_DIELECTRIC_WITHSTAND_RECORD, "DWV-03"),
        _measurement(PARTIAL_DISCHARGE_INCEPTION_RECORD, "PDIV-11"),
        _measurement(HIGH_POWER_THERMAL_SURVEY_RECORD, "THERM-07"),
        _measurement(INSULATION_SPACING_LAYOUT_RECORD, "LAYOUT-22"),
        _analysis(VOLTAGE_AND_POWER_DERATING_ANALYSIS, "DER-14"),
        _declaration(CONFORMAL_COATING_AND_VENTING_RECORD, "COAT-DEC-5"),
    ]


def _expected_weighted():
    return (
        4.0
        + DEFAULT_APPLICATION_POLICY["analysis_credit"]
        + DEFAULT_APPLICATION_POLICY["supplier_declaration_credit"]
    ) / len(REQUIRED_APPLICATION_EVIDENCE)


def _case(**overrides):
    case = {
        "application_reference": "HVA-3-007",
        "part_reference": "PRT-600V-30W",
        "applied_voltage_v": 400.0,
        "rated_voltage_v": 600.0,
        "peak_factor": 1.1,
        "discharge_inception_voltage_v": 700.0,
        "creepage_path_mm": 2.5,
        "dissipated_power_w": 8.0,
        "rated_power_w": 30.0,
        "derating_onset_temperature_c": 25.0,
        "max_case_temperature_c": 125.0,
        "case_temperature_c": 65.0,
        "thermal_resistance_c_per_w": 3.0,
        "max_junction_temperature_c": 150.0,
        "evidence": _evidence(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_application_policy(DEFAULT_APPLICATION_POLICY),
            DEFAULT_APPLICATION_POLICY,
        )

    def test_a_zero_voltage_threshold_refused(self):
        with self.assertRaises(ValueError):
            validate_application_policy(_policy(high_voltage_threshold_v=0.0))

    def test_a_zero_power_threshold_refused(self):
        with self.assertRaises(ValueError):
            validate_application_policy(_policy(high_power_threshold_w=0.0))

    def test_a_zero_voltage_utilization_cap_refused(self):
        with self.assertRaises(ValueError):
            validate_application_policy(_policy(max_voltage_utilization=0.0))

    def test_a_zero_power_derating_factor_refused(self):
        with self.assertRaises(ValueError):
            validate_application_policy(_policy(power_derating_factor=0.0))

    def test_a_discharge_margin_below_one_refused(self):
        with self.assertRaises(ValueError):
            validate_application_policy(_policy(min_discharge_margin=0.9))

    def test_a_negative_junction_margin_refused(self):
        with self.assertRaises(ValueError):
            validate_application_policy(_policy(junction_temperature_margin_c=-5.0))

    def test_an_analysis_credit_of_one_refused(self):
        with self.assertRaises(ValueError):
            validate_application_policy(_policy(analysis_credit=1.0))

    def test_a_declaration_worth_as_much_as_an_analysis_refused(self):
        with self.assertRaises(ValueError):
            validate_application_policy(
                _policy(analysis_credit=0.6, supplier_declaration_credit=0.6)
            )

    def test_a_zero_declaration_credit_refused(self):
        with self.assertRaises(ValueError):
            validate_application_policy(_policy(supplier_declaration_credit=0.0))

    def test_weighted_floor_above_the_share_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_application_policy(
                _policy(min_evidence_share=0.4, min_weighted_evidence=0.9)
            )

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_application_policy(["high_power_threshold_w"])


class ApplicationValidationTests(unittest.TestCase):
    def test_a_good_application_reads_back(self):
        declared = validate_application(_case())
        self.assertEqual(declared["part_reference"], "PRT-600V-30W")
        self.assertAlmostEqual(declared["applied_voltage_v"], 400.0, places=9)

    def test_a_zero_applied_voltage_refused(self):
        with self.assertRaises(ValueError):
            validate_application(_case(applied_voltage_v=0.0))

    def test_a_zero_rated_voltage_refused(self):
        with self.assertRaises(ValueError):
            validate_application(_case(rated_voltage_v=0.0))

    def test_a_peak_factor_below_one_refused(self):
        with self.assertRaises(ValueError):
            validate_application(_case(peak_factor=0.8))

    def test_a_negative_dissipation_refused(self):
        with self.assertRaises(ValueError):
            validate_application(_case(dissipated_power_w=-1.0))

    def test_a_zero_thermal_resistance_refused(self):
        with self.assertRaises(ValueError):
            validate_application(_case(thermal_resistance_c_per_w=0.0))

    def test_a_derating_curve_with_no_run_refused(self):
        with self.assertRaises(ValueError):
            validate_application(
                _case(derating_onset_temperature_c=125.0, max_case_temperature_c=125.0)
            )

    def test_a_junction_rated_cooler_than_the_package_refused(self):
        with self.assertRaises(ValueError):
            validate_application(_case(max_junction_temperature_c=100.0))

    def test_a_non_string_part_reference_refused(self):
        with self.assertRaises(ValueError):
            validate_application(_case(part_reference=600))

    def test_a_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            validate_application(["applied_voltage_v"])


class ThresholdTests(unittest.TestCase):
    def test_both_axes_engage_on_the_worked_case(self):
        self.assertEqual(
            engaged_axes(_case()), (HIGH_VOLTAGE_AXIS, HIGH_POWER_AXIS)
        )

    def test_a_small_low_voltage_part_engages_neither_axis(self):
        case = _case(applied_voltage_v=12.0, dissipated_power_w=0.5)
        self.assertEqual(engaged_axes(case), ())

    def test_the_power_axis_can_engage_on_its_own(self):
        case = _case(applied_voltage_v=28.0)
        self.assertEqual(engaged_axes(case), (HIGH_POWER_AXIS,))

    def test_the_voltage_axis_can_engage_on_its_own(self):
        case = _case(dissipated_power_w=1.0)
        self.assertEqual(engaged_axes(case), (HIGH_VOLTAGE_AXIS,))

    def test_a_value_landing_exactly_on_a_threshold_engages_the_axis(self):
        case = _case(applied_voltage_v=50.0, dissipated_power_w=5.0)
        self.assertEqual(
            engaged_axes(case), (HIGH_VOLTAGE_AXIS, HIGH_POWER_AXIS)
        )


class VoltageTests(unittest.TestCase):
    def test_the_utilization_is_the_applied_over_the_rating(self):
        self.assertAlmostEqual(
            voltage_utilization(_case()), 400.0 / 600.0, places=9
        )

    def test_the_peak_working_voltage_uses_the_declared_peak_factor(self):
        self.assertAlmostEqual(peak_working_voltage_v(_case()), 440.0, places=9)

    def test_the_required_creepage_follows_the_field_limit(self):
        self.assertAlmostEqual(required_creepage_mm(_case()), 2.0, places=9)

    def test_a_looser_field_limit_asks_for_less_path(self):
        self.assertAlmostEqual(
            required_creepage_mm(_case(), _policy(creepage_field_limit_v_per_mm=400.0)),
            1.0,
            places=9,
        )

    def test_the_discharge_margin_is_taken_against_the_peak_not_the_mean(self):
        self.assertAlmostEqual(discharge_margin(_case()), 700.0 / 440.0, places=9)

    def test_a_larger_peak_factor_eats_the_discharge_margin(self):
        self.assertLess(
            discharge_margin(_case(peak_factor=1.6)), discharge_margin(_case())
        )


class PowerTests(unittest.TestCase):
    def test_a_case_below_the_onset_carries_the_full_rating(self):
        self.assertAlmostEqual(
            thermal_derating_factor(_case(case_temperature_c=10.0)), 1.0, places=9
        )

    def test_a_case_at_its_maximum_carries_nothing(self):
        self.assertAlmostEqual(
            thermal_derating_factor(_case(case_temperature_c=125.0)), 0.0, places=9
        )

    def test_a_case_above_its_maximum_is_clamped_at_nothing(self):
        self.assertAlmostEqual(
            thermal_derating_factor(_case(case_temperature_c=140.0)), 0.0, places=9
        )

    def test_the_derating_runs_linearly_between_the_two_ends(self):
        self.assertAlmostEqual(thermal_derating_factor(_case()), 0.6, places=9)

    def test_the_allowance_is_the_rating_derated_twice(self):
        self.assertAlmostEqual(
            allowed_dissipation_w(_case()), 30.0 * 0.7 * 0.6, places=9
        )

    def test_the_junction_is_the_case_plus_the_rise(self):
        self.assertAlmostEqual(junction_temperature_c(_case()), 89.0, places=9)

    def test_the_junction_cap_holds_the_class_margin_back(self):
        self.assertAlmostEqual(
            allowed_junction_temperature_c(_case()), 140.0, places=9
        )

    def test_a_larger_thermal_resistance_drives_the_junction_up(self):
        self.assertGreater(
            junction_temperature_c(_case(thermal_resistance_c_per_w=6.0)),
            junction_temperature_c(_case()),
        )


class EvidenceTests(unittest.TestCase):
    def test_every_required_subject_appears_in_the_disposition(self):
        self.assertEqual(
            set(evidence_disposition(_evidence())),
            set(REQUIRED_APPLICATION_EVIDENCE),
        )

    def test_a_complete_application_holds_every_subject(self):
        self.assertAlmostEqual(evidence_share(_evidence()), 1.0, places=9)
        self.assertEqual(absent_evidence(_evidence()), ())
        self.assertEqual(unrecorded_evidence(_evidence()), ())
        self.assertEqual(
            len(held_evidence(_evidence())), len(REQUIRED_APPLICATION_EVIDENCE)
        )

    def test_the_three_tiers_are_separated_and_credited_in_order(self):
        disposition = evidence_disposition(_evidence())
        self.assertEqual(
            disposition[HIGH_VOLTAGE_DIELECTRIC_WITHSTAND_RECORD]["state"],
            HELD_AS_A_MEASUREMENT,
        )
        self.assertEqual(
            disposition[VOLTAGE_AND_POWER_DERATING_ANALYSIS]["state"],
            HELD_AS_AN_ANALYSIS,
        )
        self.assertEqual(
            disposition[CONFORMAL_COATING_AND_VENTING_RECORD]["state"],
            HELD_AS_A_SUPPLIER_DECLARATION,
        )
        self.assertGreater(
            disposition[VOLTAGE_AND_POWER_DERATING_ANALYSIS]["credit"],
            disposition[CONFORMAL_COATING_AND_VENTING_RECORD]["credit"],
        )

    def test_each_tier_reports_its_own_subjects(self):
        self.assertEqual(len(measured_evidence(_evidence())), 4)
        self.assertEqual(
            analysis_evidence(_evidence()), (VOLTAGE_AND_POWER_DERATING_ANALYSIS,)
        )
        self.assertEqual(
            declaration_evidence(_evidence()),
            (CONFORMAL_COATING_AND_VENTING_RECORD,),
        )

    def test_the_credited_evidence_sums_the_three_tiers(self):
        self.assertAlmostEqual(
            weighted_evidence(_evidence()), _expected_weighted(), places=9
        )

    def test_a_subject_with_no_reference_is_unrecorded(self):
        records = _evidence()
        records[0] = _measurement(HIGH_VOLTAGE_DIELECTRIC_WITHSTAND_RECORD, " ")
        self.assertEqual(
            unrecorded_evidence(records),
            (HIGH_VOLTAGE_DIELECTRIC_WITHSTAND_RECORD,),
        )
        self.assertEqual(
            evidence_disposition(records)[
                HIGH_VOLTAGE_DIELECTRIC_WITHSTAND_RECORD
            ]["state"],
            DECLARED_WITHOUT_A_RECORD,
        )

    def test_a_missing_subject_is_named_absent(self):
        records = _evidence()[:4]
        self.assertEqual(
            absent_evidence(records),
            (
                VOLTAGE_AND_POWER_DERATING_ANALYSIS,
                CONFORMAL_COATING_AND_VENTING_RECORD,
            ),
        )
        self.assertEqual(
            evidence_disposition(records)[VOLTAGE_AND_POWER_DERATING_ANALYSIS][
                "state"
            ],
            ABSENT,
        )

    def test_a_record_that_is_both_analysis_and_declaration_refused(self):
        entry = _analysis(PARTIAL_DISCHARGE_INCEPTION_RECORD)
        entry["held_as_supplier_declaration"] = True
        with self.assertRaises(ValueError):
            validate_evidence_record(entry)

    def test_unrecognised_evidence_subject_refused(self):
        with self.assertRaises(ValueError):
            validate_evidence_record(_measurement("the-usual-paperwork"))

    def test_duplicate_evidence_subject_refused(self):
        with self.assertRaises(ValueError):
            validate_evidence(
                [
                    _measurement(PARTIAL_DISCHARGE_INCEPTION_RECORD),
                    _measurement(PARTIAL_DISCHARGE_INCEPTION_RECORD),
                ]
            )

    def test_empty_evidence_list_refused(self):
        with self.assertRaises(ValueError):
            validate_evidence([])


class AssessmentTests(unittest.TestCase):
    def test_a_sound_application_meets_the_class_scope(self):
        result = assess_high_voltage_application(_case())
        self.assertEqual(result["verdict"], MEETS_CLASS_THREE_SCOPE)
        self.assertEqual(
            result["engaged_axes"], (HIGH_VOLTAGE_AXIS, HIGH_POWER_AXIS)
        )
        self.assertAlmostEqual(result["required_creepage_mm"], 2.0, places=9)
        self.assertAlmostEqual(result["junction_temperature_c"], 89.0, places=9)
        self.assertAlmostEqual(
            result["weighted_evidence"], _expected_weighted(), places=9
        )

    def test_an_application_naming_no_part_is_not_declared(self):
        result = assess_high_voltage_application(_case(part_reference="  "))
        self.assertEqual(result["verdict"], APPLICATION_NOT_DECLARED)
        self.assertTrue(result["findings"])

    def test_an_application_with_no_reference_is_not_declared(self):
        result = assess_high_voltage_application(_case(application_reference=""))
        self.assertEqual(result["verdict"], APPLICATION_NOT_DECLARED)

    def test_an_application_under_both_thresholds_is_outside_the_clause(self):
        result = assess_high_voltage_application(
            _case(applied_voltage_v=12.0, dissipated_power_w=0.5)
        )
        self.assertEqual(result["verdict"], BELOW_BOTH_THRESHOLDS)
        self.assertEqual(result["engaged_axes"], ())
        self.assertIsNone(result["voltage_utilization"])

    def test_a_voltage_over_the_cap_closes_the_assessment(self):
        result = assess_high_voltage_application(_case(applied_voltage_v=500.0))
        self.assertEqual(result["verdict"], VOLTAGE_DERATING_EXCEEDED)

    def test_a_utilization_landing_exactly_on_the_cap_is_admissible(self):
        result = assess_high_voltage_application(_case(applied_voltage_v=450.0))
        self.assertAlmostEqual(result["voltage_utilization"], 0.75, places=9)
        self.assertEqual(result["verdict"], MEETS_CLASS_THREE_SCOPE)

    def test_a_short_surface_path_closes_the_assessment(self):
        result = assess_high_voltage_application(_case(creepage_path_mm=1.2))
        self.assertEqual(result["verdict"], INSULATION_SPACING_SHORT)

    def test_a_path_landing_exactly_on_the_requirement_is_admissible(self):
        result = assess_high_voltage_application(_case(creepage_path_mm=2.0))
        self.assertEqual(result["verdict"], MEETS_CLASS_THREE_SCOPE)

    def test_a_discharge_inception_too_close_to_the_peak_closes_the_assessment(self):
        result = assess_high_voltage_application(
            _case(discharge_inception_voltage_v=500.0)
        )
        self.assertEqual(result["verdict"], DISCHARGE_MARGIN_SHORT)

    def test_a_discharge_margin_landing_exactly_on_the_floor_is_admissible(self):
        result = assess_high_voltage_application(
            _case(discharge_inception_voltage_v=572.0)
        )
        self.assertAlmostEqual(result["discharge_margin"], 1.3, places=9)
        self.assertEqual(result["verdict"], MEETS_CLASS_THREE_SCOPE)

    def test_a_case_off_the_end_of_its_curve_closes_the_assessment(self):
        result = assess_high_voltage_application(_case(case_temperature_c=130.0))
        self.assertEqual(result["verdict"], POWER_DERATING_EXCEEDED)
        self.assertAlmostEqual(result["thermal_derating_factor"], 0.0, places=9)

    def test_a_dissipation_over_the_allowance_closes_the_assessment(self):
        result = assess_high_voltage_application(_case(dissipated_power_w=15.0))
        self.assertEqual(result["verdict"], POWER_DERATING_EXCEEDED)

    def test_a_dissipation_landing_exactly_on_the_allowance_is_admissible(self):
        allowed = allowed_dissipation_w(_case())
        result = assess_high_voltage_application(_case(dissipated_power_w=allowed))
        self.assertEqual(result["verdict"], MEETS_CLASS_THREE_SCOPE)

    def test_a_junction_over_the_margined_rating_closes_the_assessment(self):
        result = assess_high_voltage_application(
            _case(thermal_resistance_c_per_w=10.0, max_junction_temperature_c=140.0)
        )
        self.assertEqual(result["verdict"], JUNCTION_TEMPERATURE_EXCEEDED)
        self.assertAlmostEqual(result["junction_temperature_c"], 145.0, places=9)

    def test_a_voltage_only_application_is_not_asked_for_a_thermal_verdict(self):
        result = assess_high_voltage_application(_case(dissipated_power_w=1.0))
        self.assertEqual(result["engaged_axes"], (HIGH_VOLTAGE_AXIS,))
        self.assertIsNone(result["allowed_dissipation_w"])
        self.assertEqual(result["verdict"], MEETS_CLASS_THREE_SCOPE)

    def test_a_power_only_application_is_not_asked_for_a_creepage_path(self):
        result = assess_high_voltage_application(
            _case(applied_voltage_v=28.0, creepage_path_mm=0.05)
        )
        self.assertEqual(result["engaged_axes"], (HIGH_POWER_AXIS,))
        self.assertIsNone(result["required_creepage_mm"])
        self.assertEqual(result["verdict"], MEETS_CLASS_THREE_SCOPE)

    def test_an_application_with_no_evidence_at_all_is_short(self):
        case = _case()
        del case["evidence"]
        result = assess_high_voltage_application(case)
        self.assertEqual(result["verdict"], APPLICATION_EVIDENCE_SHORT)

    def test_every_missing_subject_is_named_not_only_the_first(self):
        result = assess_high_voltage_application(_case(evidence=_evidence()[:3]))
        self.assertEqual(result["verdict"], APPLICATION_EVIDENCE_SHORT)
        self.assertEqual(len(result["absent_evidence"]), 3)

    def test_an_application_argued_entirely_on_declarations_fails_the_credit(self):
        records = [_declaration(subject) for subject in REQUIRED_APPLICATION_EVIDENCE]
        result = assess_high_voltage_application(_case(evidence=records))
        self.assertEqual(result["verdict"], APPLICATION_EVIDENCE_SHORT)
        self.assertAlmostEqual(result["evidence_share"], 1.0, places=9)
        self.assertAlmostEqual(
            result["weighted_evidence"],
            DEFAULT_APPLICATION_POLICY["supplier_declaration_credit"],
            places=9,
        )

    def test_an_application_argued_entirely_on_analyses_clears_the_credit(self):
        records = [_analysis(subject) for subject in REQUIRED_APPLICATION_EVIDENCE]
        result = assess_high_voltage_application(_case(evidence=records))
        self.assertAlmostEqual(
            result["weighted_evidence"],
            DEFAULT_APPLICATION_POLICY["analysis_credit"],
            places=9,
        )
        self.assertEqual(result["verdict"], MEETS_CLASS_THREE_SCOPE)

    def test_a_marginal_voltage_advisory_travels_with_a_passing_verdict(self):
        result = assess_high_voltage_application(_case(applied_voltage_v=445.0))
        self.assertEqual(result["verdict"], MEETS_CLASS_THREE_SCOPE)
        self.assertEqual(len(result["advisories"]), 1)
        self.assertIn("marginal band", result["advisories"][0])

    def test_a_comfortable_application_raises_no_advisory(self):
        self.assertEqual(utilization_advisories(_case()), ())

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_high_voltage_application(["applied_voltage_v"])


if __name__ == "__main__":
    unittest.main()
