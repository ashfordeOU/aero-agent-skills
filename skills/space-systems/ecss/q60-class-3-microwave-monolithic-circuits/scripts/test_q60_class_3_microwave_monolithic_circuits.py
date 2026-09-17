#!/usr/bin/env python3
"""Contract test for the class 3 monolithic microwave part, four phases (offline)."""

import copy
import unittest

from q60_class_3_microwave_monolithic_circuits_logic import (
    ADMISSIBLE_AT_CLASS_3,
    CHOICE_PEDIGREE_NOT_ADMISSIBLE,
    DEFAULT_CLASS3_MMIC_POLICY,
    DELIVERY_FORMS,
    DELIVERY_FORM_EVIDENCE,
    DESIGN_GAIN_MARGIN_SHORT,
    FUNCTION_GAIN_MARGIN_FLOOR_DB,
    MMIC_FUNCTIONS,
    PEDIGREE_EVIDENCE,
    PHASES,
    PURCHASE_TRACEABILITY_INCOMPLETE,
    REQUIRED_TRACEABILITY_FIELDS,
    SCREENING_PEDIGREES,
    UNKNOWN_PEDIGREE,
    USE_JUNCTION_TEMPERATURE_OVER_LIMIT,
    USE_LOAD_MISMATCH_OVERSTRESS,
    WEAKEST_CLASS_3_PEDIGREE,
    assess_class3_mmic,
    choice_findings,
    compensating_evidence,
    delivered_power_w,
    design_findings,
    dissipated_power_w,
    first_blocking_phase,
    gain_margin_db,
    junction_margin_c,
    junction_temperature_c,
    meets_floor,
    mismatch_stress_factor,
    pedigree_rank,
    phase_findings,
    purchase_findings,
    reflection_magnitude,
    use_findings,
    validate_class3_mmic_case,
    validate_class3_mmic_policy,
)

TRACEABILITY = {
    "lot_date_code": "2625",
    "lot_traceability_reference": "LOT-C3-4412",
    "procurement_specification": "PS-MMIC-014",
}

CASE = {
    "part_number": "MMIC-C3-770",
    "function": "power-amplifier",
    "screening_pedigree": "automotive-grade",
    "delivery_form": "hermetic-package",
    "available_gain_db": 26.0,
    "required_gain_db": 22.0,
    "rated_output_power_w": 10.0,
    "nominal_output_power_w": 8.0,
    "dc_input_power_w": 30.0,
    "load_vswr": 1.5,
    "baseplate_temperature_c": 40.0,
    "thermal_resistance_junction_case_c_per_w": 2.0,
    "thermal_resistance_case_baseplate_c_per_w": 1.0,
    "traceability": dict(TRACEABILITY),
}


def _case(**overrides):
    case = copy.deepcopy(CASE)
    case.update(overrides)
    return case


def _traceability(**overrides):
    record = dict(TRACEABILITY)
    record.update(overrides)
    return record


class PolicyTests(unittest.TestCase):
    def test_default_policy_is_returned_when_omitted(self):
        self.assertEqual(validate_class3_mmic_policy(), DEFAULT_CLASS3_MMIC_POLICY)

    def test_unknown_policy_key_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_class3_mmic_policy({"noise_figure_cap_db": 3})

    def test_a_stress_cap_below_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_class3_mmic_policy({"mismatch_stress_cap": 0.5})

    def test_a_non_positive_temperature_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_class3_mmic_policy({"junction_temperature_limit_c": 0})


class LadderTests(unittest.TestCase):
    def test_space_evaluated_is_the_strongest_pedigree(self):
        self.assertEqual(pedigree_rank("space-evaluated"), 1)

    def test_unknown_pedigree_is_the_weakest_rung(self):
        self.assertEqual(pedigree_rank(UNKNOWN_PEDIGREE), len(SCREENING_PEDIGREES))

    def test_an_unlisted_pedigree_is_rejected(self):
        with self.assertRaises(ValueError):
            pedigree_rank("a-good-feeling")

    def test_class_3_reaches_below_a_space_evaluated_part(self):
        self.assertGreater(
            pedigree_rank(WEAKEST_CLASS_3_PEDIGREE), pedigree_rank("space-evaluated")
        )

    def test_every_admissible_pedigree_names_its_evidence(self):
        for pedigree in SCREENING_PEDIGREES:
            if pedigree == UNKNOWN_PEDIGREE:
                continue
            self.assertIn(pedigree, PEDIGREE_EVIDENCE)

    def test_a_weaker_pedigree_never_owes_less_evidence(self):
        for index in range(len(SCREENING_PEDIGREES) - 2):
            stronger = PEDIGREE_EVIDENCE[SCREENING_PEDIGREES[index]]
            weaker = PEDIGREE_EVIDENCE[SCREENING_PEDIGREES[index + 1]]
            self.assertTrue(set(stronger).issubset(set(weaker)))

    def test_every_delivery_form_names_an_evidence_set(self):
        for form in DELIVERY_FORMS:
            self.assertIn(form, DELIVERY_FORM_EVIDENCE)

    def test_every_function_names_a_gain_margin_floor(self):
        for function in MMIC_FUNCTIONS:
            self.assertGreater(FUNCTION_GAIN_MARGIN_FLOOR_DB[function], 0.0)


class CaseValidationTests(unittest.TestCase):
    def test_a_complete_case_validates(self):
        validated = validate_class3_mmic_case(CASE)
        self.assertEqual(validated["function"], "power-amplifier")

    def test_an_unknown_function_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_class3_mmic_case(_case(function="oscillator-bank"))

    def test_an_unknown_delivery_form_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_class3_mmic_case(_case(delivery_form="paper-bag"))

    def test_a_standing_wave_ratio_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_class3_mmic_case(_case(load_vswr=0.8))

    def test_an_output_above_the_rating_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_class3_mmic_case(_case(nominal_output_power_w=14.0))

    def test_a_supply_below_the_output_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_class3_mmic_case(_case(dc_input_power_w=4.0))

    def test_a_zero_die_thermal_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_class3_mmic_case(
                _case(thermal_resistance_junction_case_c_per_w=0.0)
            )

    def test_a_zero_interface_resistance_is_allowed(self):
        validated = validate_class3_mmic_case(
            _case(thermal_resistance_case_baseplate_c_per_w=0.0)
        )
        self.assertAlmostEqual(
            validated["thermal_resistance_case_baseplate_c_per_w"], 0.0, places=9
        )

    def test_a_negative_baseplate_temperature_is_allowed(self):
        validated = validate_class3_mmic_case(_case(baseplate_temperature_c=-25.0))
        self.assertAlmostEqual(validated["baseplate_temperature_c"], -25.0, places=9)

    def test_a_traceability_field_of_wrong_type_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_class3_mmic_case(_case(traceability=_traceability(lot_date_code=2625)))

    def test_a_blank_traceability_field_reads_as_absent(self):
        validated = validate_class3_mmic_case(
            _case(traceability=_traceability(lot_date_code="   "))
        )
        self.assertIsNone(validated["traceability"]["lot_date_code"])

    def test_a_case_of_wrong_type_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_class3_mmic_case("MMIC-C3-770")


class MismatchTests(unittest.TestCase):
    def test_a_matched_load_reflects_nothing(self):
        self.assertAlmostEqual(reflection_magnitude(1.0), 0.0, places=9)

    def test_a_matched_load_puts_no_extra_stress_on_the_stage(self):
        self.assertAlmostEqual(mismatch_stress_factor(1.0), 1.0, places=9)

    def test_the_reflection_follows_the_standing_wave_ratio(self):
        self.assertAlmostEqual(reflection_magnitude(1.5), 0.2, places=9)

    def test_the_stress_factor_is_the_squared_voltage_sum(self):
        self.assertAlmostEqual(mismatch_stress_factor(1.5), 1.44, places=9)

    def test_a_reflection_below_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            reflection_magnitude(0.5)

    def test_a_matched_load_delivers_the_whole_output(self):
        self.assertAlmostEqual(delivered_power_w(8.0, 1.0), 8.0, places=9)

    def test_a_mismatched_load_delivers_less(self):
        self.assertAlmostEqual(delivered_power_w(8.0, 1.5), 8.0 * (1.0 - 0.04), places=9)

    def test_delivered_power_rejects_a_non_positive_output(self):
        with self.assertRaises(ValueError):
            delivered_power_w(0.0, 1.5)


class ThermalTests(unittest.TestCase):
    def test_the_reflected_power_comes_back_as_dissipation(self):
        self.assertAlmostEqual(
            dissipated_power_w(CASE), 30.0 - 8.0 * (1.0 - 0.04), places=9
        )

    def test_a_matched_load_dissipates_least(self):
        self.assertLess(
            dissipated_power_w(_case(load_vswr=1.0)), dissipated_power_w(CASE)
        )

    def test_the_junction_sits_above_the_baseplate_by_the_path_drop(self):
        expected = 40.0 + dissipated_power_w(CASE) * 3.0
        self.assertAlmostEqual(junction_temperature_c(CASE), expected, places=9)

    def test_the_interface_resistance_counts_as_much_as_the_die_one(self):
        hotter = junction_temperature_c(
            _case(thermal_resistance_case_baseplate_c_per_w=4.0)
        )
        self.assertGreater(hotter, junction_temperature_c(CASE))

    def test_the_margin_is_the_limit_less_the_junction(self):
        self.assertAlmostEqual(
            junction_margin_c(CASE),
            DEFAULT_CLASS3_MMIC_POLICY["junction_temperature_limit_c"]
            - junction_temperature_c(CASE),
            places=9,
        )

    def test_a_case_exactly_on_the_limit_has_a_zero_margin(self):
        limit = junction_temperature_c(CASE)
        self.assertAlmostEqual(
            junction_margin_c(CASE, {"junction_temperature_limit_c": limit}),
            0.0,
            places=9,
        )

    def test_a_value_on_its_floor_meets_it(self):
        self.assertTrue(meets_floor(0.0, 0.0))

    def test_a_value_below_its_floor_does_not_meet_it(self):
        self.assertFalse(meets_floor(-3.0, 0.0))


class PhaseTests(unittest.TestCase):
    def test_a_clean_design_phase_raises_nothing(self):
        self.assertEqual(design_findings(CASE), ())

    def test_the_gain_margin_is_the_plain_difference(self):
        self.assertAlmostEqual(gain_margin_db(CASE), 4.0, places=9)

    def test_a_margin_exactly_on_its_floor_is_accepted(self):
        case = _case(available_gain_db=25.0, required_gain_db=22.0)
        self.assertAlmostEqual(
            gain_margin_db(case), FUNCTION_GAIN_MARGIN_FLOOR_DB["power-amplifier"],
            places=9,
        )
        self.assertEqual(design_findings(case), ())

    def test_a_thin_gain_margin_is_a_design_finding(self):
        findings = design_findings(_case(required_gain_db=24.0))
        self.assertEqual(findings[0]["finding"], DESIGN_GAIN_MARGIN_SHORT)
        self.assertEqual(findings[0]["phase"], "design")

    def test_a_switch_matrix_is_held_to_less_margin_than_a_power_stage(self):
        self.assertLess(
            FUNCTION_GAIN_MARGIN_FLOOR_DB["switch-matrix"],
            FUNCTION_GAIN_MARGIN_FLOOR_DB["power-amplifier"],
        )

    def test_a_catalogue_part_is_still_a_choice_class_3_can_make(self):
        self.assertEqual(choice_findings(_case(screening_pedigree="commercial-catalogue")), ())

    def test_a_part_with_no_stated_pedigree_is_not_admissible(self):
        findings = choice_findings(_case(screening_pedigree=UNKNOWN_PEDIGREE))
        self.assertEqual(findings[0]["finding"], CHOICE_PEDIGREE_NOT_ADMISSIBLE)

    def test_a_complete_traceability_record_raises_nothing(self):
        self.assertEqual(purchase_findings(CASE), ())

    def test_a_missing_traceability_field_is_a_purchase_finding(self):
        findings = purchase_findings(
            _case(traceability=_traceability(lot_traceability_reference=None))
        )
        self.assertEqual(findings[0]["finding"], PURCHASE_TRACEABILITY_INCOMPLETE)
        self.assertIn("lot_traceability_reference", findings[0]["measured"])

    def test_every_required_traceability_field_is_checked(self):
        for field in REQUIRED_TRACEABILITY_FIELDS:
            case = _case(traceability=_traceability(**{field: None}))
            self.assertEqual(len(purchase_findings(case)), 1)

    def test_a_clean_application_raises_no_use_finding(self):
        self.assertEqual(use_findings(CASE), ())

    def test_a_badly_mismatched_load_is_a_use_finding(self):
        findings = use_findings(_case(load_vswr=6.0))
        self.assertEqual(findings[0]["finding"], USE_LOAD_MISMATCH_OVERSTRESS)

    def test_a_stress_exactly_on_the_cap_is_accepted(self):
        cap = mismatch_stress_factor(CASE["load_vswr"])
        self.assertEqual(use_findings(CASE, {"mismatch_stress_cap": cap}), ())

    def test_a_hot_baseplate_pushes_the_junction_over_the_limit(self):
        findings = use_findings(_case(baseplate_temperature_c=110.0))
        self.assertEqual(findings[0]["finding"], USE_JUNCTION_TEMPERATURE_OVER_LIMIT)

    def test_a_junction_exactly_on_the_limit_is_accepted(self):
        limit = junction_temperature_c(CASE)
        self.assertEqual(
            use_findings(CASE, {"junction_temperature_limit_c": limit}), ()
        )


class EvidenceTests(unittest.TestCase):
    def test_a_space_evaluated_hermetic_part_owes_nothing_extra(self):
        case = _case(screening_pedigree="space-evaluated")
        self.assertEqual(compensating_evidence(case), ())

    def test_a_catalogue_part_owes_the_full_evidence_set(self):
        evidence = compensating_evidence(_case(screening_pedigree="commercial-catalogue"))
        self.assertIn("upscreening-programme", evidence)
        self.assertIn("radiation-evaluation", evidence)

    def test_a_bare_die_moves_the_assembly_evidence_onto_the_builder(self):
        evidence = compensating_evidence(_case(delivery_form="bare-die"))
        self.assertIn("die-attach-qualification", evidence)

    def test_a_plastic_body_brings_moisture_control_instead(self):
        evidence = compensating_evidence(_case(delivery_form="plastic-encapsulated"))
        self.assertIn("moisture-sensitivity-control", evidence)

    def test_the_evidence_set_never_repeats_an_item(self):
        evidence = compensating_evidence(
            _case(screening_pedigree="commercial-catalogue", delivery_form="bare-die")
        )
        self.assertEqual(len(evidence), len(set(evidence)))


class AssessmentTests(unittest.TestCase):
    def test_a_clean_part_is_admissible(self):
        result = assess_class3_mmic(CASE)
        self.assertEqual(result["verdict"], ADMISSIBLE_AT_CLASS_3)
        self.assertIsNone(result["blocking_phase"])
        self.assertTrue(result["admissible"])

    def test_the_design_phase_blocks_before_the_choice_phase(self):
        result = assess_class3_mmic(
            _case(required_gain_db=24.0, screening_pedigree=UNKNOWN_PEDIGREE)
        )
        self.assertEqual(result["blocking_phase"], "design")
        self.assertEqual(result["verdict"], DESIGN_GAIN_MARGIN_SHORT)

    def test_the_choice_phase_blocks_before_the_purchase_phase(self):
        result = assess_class3_mmic(
            _case(
                screening_pedigree=UNKNOWN_PEDIGREE,
                traceability=_traceability(lot_date_code=None),
            )
        )
        self.assertEqual(result["blocking_phase"], "choice")

    def test_the_purchase_phase_blocks_before_the_use_phase(self):
        result = assess_class3_mmic(
            _case(traceability=_traceability(procurement_specification=None), load_vswr=6.0)
        )
        self.assertEqual(result["blocking_phase"], "purchase")
        self.assertEqual(result["verdict"], PURCHASE_TRACEABILITY_INCOMPLETE)

    def test_the_use_phase_is_the_last_one_to_block(self):
        result = assess_class3_mmic(_case(load_vswr=6.0))
        self.assertEqual(result["blocking_phase"], "use")

    def test_every_phase_appears_in_the_report(self):
        result = assess_class3_mmic(CASE)
        for phase in PHASES:
            self.assertIn(phase, result["phase_findings"])

    def test_the_findings_list_is_every_phase_concatenated(self):
        result = assess_class3_mmic(
            _case(required_gain_db=24.0, screening_pedigree=UNKNOWN_PEDIGREE)
        )
        total = sum(len(result["phase_findings"][phase]) for phase in PHASES)
        self.assertEqual(len(result["findings"]), total)

    def test_first_blocking_phase_is_none_on_a_clean_part(self):
        self.assertIsNone(first_blocking_phase(CASE))

    def test_the_reported_evidence_matches_the_choice(self):
        result = assess_class3_mmic(_case(screening_pedigree="commercial-catalogue"))
        self.assertEqual(
            result["compensating_evidence"],
            compensating_evidence(_case(screening_pedigree="commercial-catalogue")),
        )

    def test_the_reported_thermal_numbers_match_the_helpers(self):
        result = assess_class3_mmic(CASE)
        self.assertAlmostEqual(
            result["junction_temperature_c"], junction_temperature_c(CASE), places=9
        )
        self.assertAlmostEqual(
            result["dissipated_power_w"], dissipated_power_w(CASE), places=9
        )

    def test_a_phase_report_is_returned_even_when_the_part_is_blocked(self):
        result = assess_class3_mmic(_case(screening_pedigree=UNKNOWN_PEDIGREE))
        self.assertFalse(result["admissible"])
        self.assertEqual(result["phase_findings"]["design"], ())


if __name__ == "__main__":
    unittest.main(verbosity=0)
