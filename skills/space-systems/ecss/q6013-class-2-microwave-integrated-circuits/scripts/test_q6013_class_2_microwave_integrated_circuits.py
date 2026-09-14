"""Contract tests for the clause 5.6.5 class 2 microwave integrated circuit.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused application
policy, a refused Arrhenius reference, a part with no technology or no
package form, a channel margin under its floor, an RF drive over the
derating cap, a median life under the mission need, a non-hermetic package
with no moisture barrier, and an evaluation whose evidence is absent,
unrecorded or carried entirely by similarity.
"""

import unittest

from q6013_class_2_microwave_integrated_circuits_logic import (
    ABSENT,
    BARE_DIE_IN_SEALED_MODULE,
    BOND_INTEGRITY_EVALUATION,
    DECLARED_WITHOUT_RECORD,
    DEFAULT_LIFE_MODEL,
    DEFAULT_MMIC_POLICY,
    DIE_VISUAL_INSPECTION,
    GAAS_PHEMT,
    HELD_BY_SIMILARITY,
    HELD_DIRECTLY,
    MMIC_CHANNEL_MARGIN_SHORT,
    MMIC_EVIDENCE_SHORT,
    MMIC_MEDIAN_LIFE_SHORT,
    MMIC_MEETS_CLASS_TWO_SCOPE,
    MMIC_MOISTURE_BARRIER_MISSING,
    MMIC_NOT_IDENTIFIED,
    MMIC_RF_DRIVE_EXCEEDED,
    MOISTURE_PROTECTION_EVIDENCE,
    NON_HERMETIC_PACKAGE,
    REQUIRED_EVIDENCE,
    RF_PERFORMANCE_SCREENING,
    SINGLE_EVENT_EFFECT_EVALUATION,
    WAFER_LOT_PROCESS_MONITOR_DATA,
    absent_evidence,
    assess_mmic_application,
    channel_margin_c,
    channel_temperature_c,
    evidence_disposition,
    evidence_share,
    governing_channel_ceiling_c,
    held_evidence,
    median_life_years,
    rf_drive_fraction,
    similarity_evidence,
    thermal_advisories,
    unrecorded_evidence,
    validate_evidence,
    validate_evidence_record,
    validate_life_model,
    validate_mmic_part,
    validate_mmic_policy,
    weighted_evidence,
)


def _policy(**overrides):
    policy = dict(DEFAULT_MMIC_POLICY)
    policy.update(overrides)
    return policy


def _model(**overrides):
    model = dict(DEFAULT_LIFE_MODEL)
    model.update(overrides)
    return model


def _direct(subject, record="EVAL-REP-7"):
    return {
        "subject": subject,
        "held_by_similarity": False,
        "record_reference": record,
        "similar_part_reference": "",
    }


def _by_similarity(subject, sibling="MMIC-SIB-02"):
    return {
        "subject": subject,
        "held_by_similarity": True,
        "record_reference": "",
        "similar_part_reference": sibling,
    }


def _evidence():
    return [
        _direct(WAFER_LOT_PROCESS_MONITOR_DATA, "PCM-2026-11"),
        _direct(RF_PERFORMANCE_SCREENING, "RF-SCR-04"),
        _direct(DIE_VISUAL_INSPECTION, "DVI-04"),
        _direct(BOND_INTEGRITY_EVALUATION, "BOND-04"),
        _direct(MOISTURE_PROTECTION_EVIDENCE, "SEAL-04"),
        _by_similarity(SINGLE_EVENT_EFFECT_EVALUATION),
    ]


def _expected_weighted():
    return (5.0 + DEFAULT_MMIC_POLICY["similarity_credit"]) / len(REQUIRED_EVIDENCE)


def _case(**overrides):
    case = {
        "part_reference": "MMIC-2026-118",
        "technology": GAAS_PHEMT,
        "package_form": BARE_DIE_IN_SEALED_MODULE,
        "baseplate_temperature_c": 60.0,
        "dissipated_power_w": 2.0,
        "thermal_resistance_c_per_w": 17.5,
        "rated_channel_temperature_c": 150.0,
        "applied_rf_power_w": 1.2,
        "rated_rf_power_w": 2.0,
        "moisture_barrier_declared": False,
        "mission_duration_years": 15.0,
        "evidence": _evidence(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_mmic_policy(DEFAULT_MMIC_POLICY), DEFAULT_MMIC_POLICY)

    def test_margin_floor_at_or_above_the_ceiling_refused(self):
        with self.assertRaises(ValueError):
            validate_mmic_policy(
                _policy(max_channel_temperature_c=125.0, min_channel_margin_c=125.0)
            )

    def test_zero_rf_drive_cap_refused(self):
        with self.assertRaises(ValueError):
            validate_mmic_policy(_policy(max_rf_drive_fraction=0.0))

    def test_weighted_floor_above_the_share_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_mmic_policy(
                _policy(min_evidence_share=0.5, min_weighted_evidence=0.9)
            )

    def test_zero_similarity_credit_refused(self):
        with self.assertRaises(ValueError):
            validate_mmic_policy(_policy(similarity_credit=0.0))

    def test_non_boolean_moisture_requirement_refused(self):
        with self.assertRaises(ValueError):
            validate_mmic_policy(
                _policy(require_moisture_barrier_for_non_hermetic="probably")
            )

    def test_non_positive_median_life_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_mmic_policy(_policy(min_median_life_years=0.0))

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_mmic_policy(["max_channel_temperature_c"])


class LifeModelTests(unittest.TestCase):
    def test_default_life_model_validates(self):
        self.assertIs(validate_life_model(DEFAULT_LIFE_MODEL), DEFAULT_LIFE_MODEL)

    def test_non_positive_activation_energy_refused(self):
        with self.assertRaises(ValueError):
            validate_life_model(_model(activation_energy_ev=0.0))

    def test_non_mapping_life_model_refused(self):
        with self.assertRaises(ValueError):
            validate_life_model("1.5 eV")


class PartValidationTests(unittest.TestCase):
    def test_a_good_part_reads_back(self):
        part = validate_mmic_part(_case())
        self.assertEqual(part["technology"], GAAS_PHEMT)
        self.assertAlmostEqual(part["thermal_resistance_c_per_w"], 17.5, places=9)

    def test_unrecognised_technology_refused(self):
        with self.assertRaises(ValueError):
            validate_mmic_part(_case(technology="unobtainium-hemt"))

    def test_unrecognised_package_form_refused(self):
        with self.assertRaises(ValueError):
            validate_mmic_part(_case(package_form="shrinkwrap"))

    def test_zero_rated_rf_power_refused(self):
        with self.assertRaises(ValueError):
            validate_mmic_part(_case(rated_rf_power_w=0.0))

    def test_negative_dissipation_refused(self):
        with self.assertRaises(ValueError):
            validate_mmic_part(_case(dissipated_power_w=-1.0))

    def test_baseplate_below_absolute_zero_refused(self):
        with self.assertRaises(ValueError):
            validate_mmic_part(_case(baseplate_temperature_c=-400.0))

    def test_non_boolean_moisture_barrier_refused(self):
        with self.assertRaises(ValueError):
            validate_mmic_part(_case(moisture_barrier_declared="potted"))

    def test_non_mapping_case_refused_by_the_part_reader(self):
        with self.assertRaises(ValueError):
            validate_mmic_part(["part_reference"])


class ThermalTests(unittest.TestCase):
    def test_the_channel_sits_above_the_baseplate_by_the_thermal_path(self):
        self.assertAlmostEqual(channel_temperature_c(_case()), 95.0, places=9)

    def test_the_governing_ceiling_is_the_lower_of_the_two(self):
        self.assertAlmostEqual(
            governing_channel_ceiling_c(_case()), 125.0, places=9
        )
        self.assertAlmostEqual(
            governing_channel_ceiling_c(_case(rated_channel_temperature_c=110.0)),
            110.0,
            places=9,
        )

    def test_the_margin_is_taken_against_the_governing_ceiling(self):
        self.assertAlmostEqual(channel_margin_c(_case()), 30.0, places=9)

    def test_a_margin_landing_exactly_on_the_floor_still_clears_it(self):
        result = assess_mmic_application(_case(), _policy(min_channel_margin_c=30.0))
        self.assertAlmostEqual(result["channel_margin_c"], 30.0, places=9)
        self.assertEqual(result["verdict"], MMIC_MEETS_CLASS_TWO_SCOPE)

    def test_the_rf_drive_is_read_as_a_fraction_of_the_rated_drive(self):
        self.assertAlmostEqual(rf_drive_fraction(_case()), 0.6, places=9)

    def test_a_drive_landing_exactly_on_the_cap_still_clears_it(self):
        case = _case(applied_rf_power_w=1.4)
        self.assertAlmostEqual(rf_drive_fraction(case), 0.7, places=9)
        self.assertEqual(
            assess_mmic_application(case)["verdict"], MMIC_MEETS_CLASS_TWO_SCOPE
        )

    def test_a_channel_at_the_reference_returns_the_reference_life(self):
        case = _case(
            baseplate_temperature_c=125.0,
            dissipated_power_w=0.0,
            thermal_resistance_c_per_w=10.0,
        )
        self.assertAlmostEqual(median_life_years(case), 20.0, places=9)

    def test_a_hotter_channel_shortens_the_median_life(self):
        cool = median_life_years(_case())
        hot = median_life_years(_case(baseplate_temperature_c=110.0))
        self.assertLess(hot, cool)

    def test_a_margin_inside_the_band_raises_an_advisory(self):
        advisories = thermal_advisories(_case(), _policy(min_channel_margin_c=27.0))
        self.assertEqual(len(advisories), 1)
        self.assertIn("marginal band", advisories[0])

    def test_a_comfortable_margin_raises_no_advisory(self):
        self.assertEqual(thermal_advisories(_case()), ())


class EvidenceTests(unittest.TestCase):
    def test_every_required_subject_appears_in_the_disposition(self):
        self.assertEqual(set(evidence_disposition(_evidence())), set(REQUIRED_EVIDENCE))

    def test_a_complete_evaluation_holds_every_subject(self):
        self.assertAlmostEqual(evidence_share(_evidence()), 1.0, places=9)
        self.assertEqual(absent_evidence(_evidence()), ())
        self.assertEqual(unrecorded_evidence(_evidence()), ())
        self.assertEqual(len(held_evidence(_evidence())), len(REQUIRED_EVIDENCE))

    def test_a_similarity_claim_is_named_and_credited_below_one(self):
        self.assertEqual(
            similarity_evidence(_evidence()), (SINGLE_EVENT_EFFECT_EVALUATION,)
        )
        disposition = evidence_disposition(_evidence())
        self.assertEqual(
            disposition[SINGLE_EVENT_EFFECT_EVALUATION]["state"], HELD_BY_SIMILARITY
        )
        self.assertEqual(
            disposition[WAFER_LOT_PROCESS_MONITOR_DATA]["state"], HELD_DIRECTLY
        )
        self.assertAlmostEqual(
            weighted_evidence(_evidence()), _expected_weighted(), places=9
        )

    def test_a_similarity_claim_naming_no_sibling_is_unrecorded(self):
        records = _evidence()
        records[5] = _by_similarity(SINGLE_EVENT_EFFECT_EVALUATION, sibling="  ")
        self.assertEqual(
            unrecorded_evidence(records), (SINGLE_EVENT_EFFECT_EVALUATION,)
        )
        self.assertEqual(
            evidence_disposition(records)[SINGLE_EVENT_EFFECT_EVALUATION]["state"],
            DECLARED_WITHOUT_RECORD,
        )

    def test_a_subject_with_no_record_reference_is_unrecorded(self):
        records = _evidence()
        records[1] = _direct(RF_PERFORMANCE_SCREENING, record="")
        self.assertEqual(unrecorded_evidence(records), (RF_PERFORMANCE_SCREENING,))

    def test_a_missing_subject_is_named_absent(self):
        records = _evidence()[:4]
        self.assertEqual(
            absent_evidence(records),
            (MOISTURE_PROTECTION_EVIDENCE, SINGLE_EVENT_EFFECT_EVALUATION),
        )
        self.assertEqual(
            evidence_disposition(records)[MOISTURE_PROTECTION_EVIDENCE]["state"], ABSENT
        )

    def test_a_record_that_is_both_direct_and_by_similarity_is_refused(self):
        entry = _by_similarity(DIE_VISUAL_INSPECTION)
        entry["record_reference"] = "DVI-04"
        with self.assertRaises(ValueError):
            validate_evidence_record(entry)

    def test_unrecognised_evidence_subject_refused(self):
        with self.assertRaises(ValueError):
            validate_evidence_record(_direct("vibes-review"))

    def test_duplicate_evidence_subject_refused(self):
        with self.assertRaises(ValueError):
            validate_evidence(
                [_direct(DIE_VISUAL_INSPECTION), _direct(DIE_VISUAL_INSPECTION)]
            )

    def test_empty_evidence_list_refused(self):
        with self.assertRaises(ValueError):
            validate_evidence([])


class AssessmentTests(unittest.TestCase):
    def test_a_sound_application_meets_the_class_scope(self):
        result = assess_mmic_application(_case())
        self.assertEqual(result["verdict"], MMIC_MEETS_CLASS_TWO_SCOPE)
        self.assertAlmostEqual(result["channel_temperature_c"], 95.0, places=9)
        self.assertAlmostEqual(result["evidence_share"], 1.0, places=9)
        self.assertAlmostEqual(
            result["weighted_evidence"], _expected_weighted(), places=9
        )

    def test_a_part_with_no_reference_is_not_identified(self):
        result = assess_mmic_application(_case(part_reference="   "))
        self.assertEqual(result["verdict"], MMIC_NOT_IDENTIFIED)
        self.assertTrue(result["findings"])

    def test_a_part_with_no_package_form_is_not_identified(self):
        result = assess_mmic_application(_case(package_form=""))
        self.assertEqual(result["verdict"], MMIC_NOT_IDENTIFIED)

    def test_a_hot_channel_closes_the_assessment_on_the_margin(self):
        result = assess_mmic_application(_case(baseplate_temperature_c=88.0))
        self.assertEqual(result["verdict"], MMIC_CHANNEL_MARGIN_SHORT)
        self.assertAlmostEqual(result["channel_margin_c"], 2.0, places=9)

    def test_an_overdriven_part_closes_the_assessment_on_the_derating(self):
        result = assess_mmic_application(_case(applied_rf_power_w=1.9))
        self.assertEqual(result["verdict"], MMIC_RF_DRIVE_EXCEEDED)
        self.assertAlmostEqual(result["rf_drive_fraction"], 0.95, places=9)

    def test_a_short_median_life_closes_the_assessment(self):
        result = assess_mmic_application(
            _case(
                baseplate_temperature_c=100.0,
                thermal_resistance_c_per_w=25.0,
                rated_channel_temperature_c=200.0,
            ),
            _policy(max_channel_temperature_c=200.0),
        )
        self.assertEqual(result["verdict"], MMIC_MEDIAN_LIFE_SHORT)
        self.assertLess(result["median_life_years"], 15.0)

    def test_the_mission_duration_can_raise_the_life_requirement(self):
        short = assess_mmic_application(
            _case(
                baseplate_temperature_c=100.0,
                thermal_resistance_c_per_w=20.0,
                rated_channel_temperature_c=200.0,
                mission_duration_years=40.0,
            ),
            _policy(max_channel_temperature_c=200.0, min_median_life_years=1.0),
        )
        self.assertEqual(short["verdict"], MMIC_MEDIAN_LIFE_SHORT)

    def test_a_non_hermetic_part_without_a_barrier_is_refused(self):
        result = assess_mmic_application(_case(package_form=NON_HERMETIC_PACKAGE))
        self.assertEqual(result["verdict"], MMIC_MOISTURE_BARRIER_MISSING)

    def test_a_non_hermetic_part_with_a_barrier_is_admissible(self):
        result = assess_mmic_application(
            _case(package_form=NON_HERMETIC_PACKAGE, moisture_barrier_declared=True)
        )
        self.assertEqual(result["verdict"], MMIC_MEETS_CLASS_TWO_SCOPE)

    def test_the_moisture_requirement_may_be_waived_by_policy(self):
        result = assess_mmic_application(
            _case(package_form=NON_HERMETIC_PACKAGE),
            _policy(require_moisture_barrier_for_non_hermetic=False),
        )
        self.assertEqual(result["verdict"], MMIC_MEETS_CLASS_TWO_SCOPE)

    def test_an_evaluation_with_no_evidence_at_all_is_short(self):
        case = _case()
        del case["evidence"]
        result = assess_mmic_application(case)
        self.assertEqual(result["verdict"], MMIC_EVIDENCE_SHORT)

    def test_every_missing_subject_is_named_not_only_the_first(self):
        result = assess_mmic_application(_case(evidence=_evidence()[:3]))
        self.assertEqual(result["verdict"], MMIC_EVIDENCE_SHORT)
        self.assertEqual(len(result["absent_evidence"]), 3)

    def test_an_evaluation_carried_entirely_by_similarity_fails_the_credit(self):
        records = [_by_similarity(subject) for subject in REQUIRED_EVIDENCE]
        result = assess_mmic_application(
            _case(evidence=records), _policy(min_weighted_evidence=0.8)
        )
        self.assertEqual(result["verdict"], MMIC_EVIDENCE_SHORT)
        self.assertAlmostEqual(result["evidence_share"], 1.0, places=9)
        self.assertAlmostEqual(
            result["weighted_evidence"],
            DEFAULT_MMIC_POLICY["similarity_credit"],
            places=9,
        )

    def test_advisories_travel_with_a_passing_verdict(self):
        result = assess_mmic_application(_case(), _policy(min_channel_margin_c=28.0))
        self.assertEqual(result["verdict"], MMIC_MEETS_CLASS_TWO_SCOPE)
        self.assertEqual(len(result["advisories"]), 1)

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_mmic_application(["part_reference"])


if __name__ == "__main__":
    unittest.main()
