#!/usr/bin/env python3
"""Contract test for the Class 3 radiation hardness selection (offline)."""

import copy
import unittest

from q60_class_3_radiation_hardness_selection_logic import (
    CAPABILITY_DATA_SOURCES,
    DESTRUCTIVE_LET_MARGIN,
    DESTRUCTIVE_MECHANISMS,
    EVIDENCE_ABSENT,
    LOT_TEST_TRIGGER_DOSE_KRAD,
    LOW_DOSE_RATE_DERATE,
    MARGIN_ADEQUATE,
    MARGIN_ON_LIMIT,
    MARGIN_SHORT,
    RADIATION_ADEQUATE,
    RADIATION_DESIGN_MARGIN,
    RADIATION_EVIDENCE_INCOMPLETE,
    RADIATION_INADEQUATE,
    RADIATION_MITIGATION_REQUIRED,
    SINGLE_EVENT_MECHANISMS,
    effective_dose_capability,
    evaluate_radiation_selection,
    grade_single_event,
    grade_total_dose,
    mission_accumulated_dose,
    mission_duration_years,
    radiation_design_margin,
    required_capability,
    validate_mission_phases,
)

PHASES = [
    {"name": "transfer", "years": 0.5, "annual_dose_krad": 4.0},
    {"name": "operations", "years": 3.0, "annual_dose_krad": 2.0},
]

BASE = {
    "part_reference": "class-3-sram-controller",
    "technology": "cmos-bulk",
    "capability_data_source": "manufacturer-datasheet",
    "characterisation_dose_rate": "high-dose-rate",
    "rated_dose_krad": 30.0,
    "shielding_factor": 1.0,
    "mission_phases": PHASES,
    "environment_let": 40.0,
    "single_event_data": [
        {"mechanism": "single-event-latch-up", "let_threshold": 80.0},
        {"mechanism": "single-event-burnout", "let_threshold": 80.0},
        {"mechanism": "single-event-gate-rupture", "let_threshold": 80.0},
        {"mechanism": "single-event-upset", "let_threshold": 60.0},
    ],
}


def _case(**overrides):
    case = copy.deepcopy(BASE)
    case.update(overrides)
    return case


class MissionProfileTests(unittest.TestCase):
    def test_lifetime_is_the_sum_of_the_phases(self):
        self.assertAlmostEqual(mission_duration_years(PHASES), 3.5, places=9)

    def test_dose_accumulates_phase_by_phase(self):
        self.assertAlmostEqual(mission_accumulated_dose(PHASES), 8.0, places=9)

    def test_local_shielding_scales_what_arrives(self):
        self.assertAlmostEqual(mission_accumulated_dose(PHASES, 0.5), 4.0, places=9)

    def test_a_shielding_factor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            mission_accumulated_dose(PHASES, 1.4)

    def test_a_zero_shielding_factor_rejected(self):
        with self.assertRaises(ValueError):
            mission_accumulated_dose(PHASES, 0.0)

    def test_an_empty_mission_rejected(self):
        with self.assertRaises(ValueError):
            validate_mission_phases([])

    def test_a_phase_declared_twice_rejected(self):
        with self.assertRaises(ValueError):
            validate_mission_phases(
                [PHASES[0], {"name": "transfer", "years": 1.0, "annual_dose_krad": 1.0}]
            )

    def test_a_phase_of_zero_years_rejected(self):
        with self.assertRaises(ValueError):
            validate_mission_phases(
                [{"name": "coast", "years": 0.0, "annual_dose_krad": 1.0}]
            )

    def test_a_negative_annual_dose_rejected(self):
        with self.assertRaises(ValueError):
            validate_mission_phases(
                [{"name": "coast", "years": 1.0, "annual_dose_krad": -1.0}]
            )


class MarginTests(unittest.TestCase):
    def test_every_data_source_carries_a_margin(self):
        self.assertEqual(set(RADIATION_DESIGN_MARGIN), set(CAPABILITY_DATA_SOURCES))

    def test_the_margin_rises_as_the_evidence_weakens(self):
        margins = [RADIATION_DESIGN_MARGIN[s] for s in CAPABILITY_DATA_SOURCES]
        self.assertEqual(margins, sorted(margins))

    def test_a_lot_test_carries_the_smallest_margin(self):
        self.assertAlmostEqual(radiation_design_margin("lot-specific-test"), 1.5, places=9)

    def test_an_unknown_data_source_rejected(self):
        with self.assertRaises(ValueError):
            radiation_design_margin("engineering-judgement")

    def test_the_requirement_is_the_environment_times_the_margin(self):
        self.assertAlmostEqual(required_capability(8.0, 3.0), 24.0, places=9)

    def test_a_zero_margin_factor_rejected(self):
        with self.assertRaises(ValueError):
            required_capability(8.0, 0.0)


class RateSensitivityTests(unittest.TestCase):
    def test_a_bipolar_part_tested_fast_is_cut(self):
        self.assertAlmostEqual(
            effective_dose_capability(30.0, "bipolar-linear", "high-dose-rate"),
            30.0 * LOW_DOSE_RATE_DERATE,
            places=9,
        )

    def test_a_bipolar_part_tested_slow_keeps_its_rating(self):
        self.assertAlmostEqual(
            effective_dose_capability(30.0, "bipolar-linear", "low-dose-rate"),
            30.0,
            places=9,
        )

    def test_a_cmos_part_is_not_cut(self):
        self.assertAlmostEqual(
            effective_dose_capability(30.0, "cmos-bulk", "high-dose-rate"),
            30.0,
            places=9,
        )

    def test_an_unknown_technology_rejected(self):
        with self.assertRaises(ValueError):
            effective_dose_capability(30.0, "vacuum-tube", "high-dose-rate")

    def test_an_unknown_dose_rate_basis_rejected(self):
        with self.assertRaises(ValueError):
            effective_dose_capability(30.0, "cmos-bulk", "medium-dose-rate")


class TotalDoseTests(unittest.TestCase):
    def test_a_comfortable_part_grades_adequate(self):
        graded = grade_total_dose(BASE)
        self.assertEqual(graded["grade"], MARGIN_ADEQUATE)
        self.assertAlmostEqual(graded["required_dose_krad"], 24.0, places=9)

    def test_a_part_sized_exactly_to_its_requirement_is_on_the_limit(self):
        graded = grade_total_dose(_case(rated_dose_krad=24.0))
        self.assertEqual(graded["grade"], MARGIN_ON_LIMIT)
        self.assertAlmostEqual(graded["margin_ratio"], 1.0, places=9)

    def test_a_rate_sensitive_part_can_fall_short_after_the_cut(self):
        graded = grade_total_dose(_case(technology="bipolar-linear"))
        self.assertTrue(graded["rate_sensitivity_applied"])
        self.assertEqual(graded["grade"], MARGIN_SHORT)

    def test_a_datasheet_claim_past_the_trigger_dose_owes_a_lot_test(self):
        phases = [{"name": "operations", "years": 7.0, "annual_dose_krad": 2.0}]
        graded = grade_total_dose(_case(mission_phases=phases))
        self.assertTrue(graded["lot_evidence_owed"])
        self.assertEqual(graded["grade"], EVIDENCE_ABSENT)

    def test_a_dose_landing_exactly_on_the_trigger_owes_nothing_extra(self):
        phases = [{"name": "operations", "years": 5.0, "annual_dose_krad": 2.0}]
        graded = grade_total_dose(_case(mission_phases=phases))
        self.assertAlmostEqual(
            graded["accumulated_dose_krad"], LOT_TEST_TRIGGER_DOSE_KRAD, places=9
        )
        self.assertFalse(graded["lot_evidence_owed"])

    def test_a_lot_test_past_the_trigger_dose_owes_nothing(self):
        phases = [{"name": "operations", "years": 7.0, "annual_dose_krad": 2.0}]
        graded = grade_total_dose(
            _case(
                mission_phases=phases,
                capability_data_source="lot-specific-test",
                rated_dose_krad=40.0,
            )
        )
        self.assertFalse(graded["lot_evidence_owed"])
        self.assertEqual(graded["grade"], MARGIN_ADEQUATE)

    def test_a_missing_rated_dose_rejected(self):
        case = _case()
        del case["rated_dose_krad"]
        with self.assertRaises(ValueError):
            grade_total_dose(case)


class SingleEventTests(unittest.TestCase):
    def test_destructive_mechanisms_are_a_subset_of_the_mechanism_list(self):
        self.assertTrue(DESTRUCTIVE_MECHANISMS.issubset(set(SINGLE_EVENT_MECHANISMS)))

    def test_a_destructive_mechanism_carries_the_larger_margin(self):
        graded = grade_single_event(
            {"mechanism": "single-event-burnout", "let_threshold": 80.0}, 40.0
        )
        self.assertAlmostEqual(
            graded["required_let"], 40.0 * DESTRUCTIVE_LET_MARGIN, places=9
        )

    def test_a_threshold_sitting_exactly_on_the_requirement_is_on_the_limit(self):
        graded = grade_single_event(
            {"mechanism": "single-event-burnout", "let_threshold": 40.0 * DESTRUCTIVE_LET_MARGIN},
            40.0,
        )
        self.assertEqual(graded["grade"], MARGIN_ON_LIMIT)

    def test_an_undeclared_threshold_is_absent_evidence_not_immunity(self):
        graded = grade_single_event({"mechanism": "single-event-latch-up"}, 40.0)
        self.assertEqual(graded["grade"], EVIDENCE_ABSENT)
        self.assertIsNone(graded["margin_ratio"])

    def test_latch_up_can_be_argued_away_by_limiting_and_cycling(self):
        graded = grade_single_event(
            {
                "mechanism": "single-event-latch-up",
                "let_threshold": 10.0,
                "mitigation": "supply-current-limiting-and-cycle",
            },
            40.0,
        )
        self.assertEqual(graded["grade"], MARGIN_SHORT)
        self.assertTrue(graded["mitigated"])

    def test_burnout_cannot_be_argued_away_at_application_level(self):
        graded = grade_single_event(
            {
                "mechanism": "single-event-burnout",
                "let_threshold": 10.0,
                "mitigation": "supply-current-limiting-and-cycle",
            },
            40.0,
        )
        self.assertFalse(graded["mitigated"])

    def test_a_recoverable_upset_is_closed_by_error_correction(self):
        graded = grade_single_event(
            {
                "mechanism": "single-event-upset",
                "let_threshold": 10.0,
                "mitigation": "error-detection-and-correction",
            },
            40.0,
        )
        self.assertTrue(graded["mitigated"])

    def test_an_unmitigated_upset_stays_short(self):
        graded = grade_single_event(
            {"mechanism": "single-event-upset", "let_threshold": 10.0}, 40.0
        )
        self.assertEqual(graded["grade"], MARGIN_SHORT)
        self.assertFalse(graded["mitigated"])

    def test_an_unknown_mechanism_rejected(self):
        with self.assertRaises(ValueError):
            grade_single_event({"mechanism": "single-event-annoyance"}, 40.0)

    def test_an_unknown_mitigation_rejected(self):
        with self.assertRaises(ValueError):
            grade_single_event(
                {
                    "mechanism": "single-event-upset",
                    "let_threshold": 10.0,
                    "mitigation": "crossed-fingers",
                },
                40.0,
            )

    def test_a_zero_environment_let_rejected(self):
        with self.assertRaises(ValueError):
            grade_single_event(
                {"mechanism": "single-event-upset", "let_threshold": 10.0}, 0.0
            )


class SelectionTests(unittest.TestCase):
    def test_a_covered_part_is_adequate(self):
        result = evaluate_radiation_selection(BASE)
        self.assertEqual(result["disposition"], RADIATION_ADEQUATE)
        self.assertTrue(result["acceptable"])

    def test_the_binding_mechanism_is_the_tightest_margin(self):
        result = evaluate_radiation_selection(BASE)
        self.assertEqual(result["binding_mechanism"], "total-ionising-dose")

    def test_an_undeclared_destructive_mechanism_is_owed_evidence(self):
        case = _case(
            single_event_data=[
                {"mechanism": "single-event-latch-up", "let_threshold": 80.0}
            ]
        )
        result = evaluate_radiation_selection(case)
        self.assertEqual(
            result["uncovered_destructive_mechanisms"],
            ["single-event-burnout", "single-event-gate-rupture"],
        )
        self.assertEqual(result["disposition"], RADIATION_EVIDENCE_INCOMPLETE)

    def test_a_dose_shortfall_makes_the_selection_inadequate(self):
        result = evaluate_radiation_selection(_case(rated_dose_krad=4.0))
        self.assertEqual(result["disposition"], RADIATION_INADEQUATE)
        self.assertFalse(result["acceptable"])

    def test_a_rate_sensitive_part_that_still_passes_carries_a_mitigation(self):
        result = evaluate_radiation_selection(
            _case(technology="bipolar-linear", rated_dose_krad=60.0)
        )
        self.assertEqual(result["disposition"], RADIATION_MITIGATION_REQUIRED)
        self.assertTrue(result["required_mitigations"])

    def test_a_mitigated_upset_does_not_block_the_part(self):
        case = _case()
        case["single_event_data"][3] = {
            "mechanism": "single-event-upset",
            "let_threshold": 10.0,
            "mitigation": "triple-modular-redundancy",
        }
        result = evaluate_radiation_selection(case)
        self.assertEqual(result["disposition"], RADIATION_MITIGATION_REQUIRED)
        self.assertTrue(result["acceptable"])

    def test_an_unmitigated_burnout_shortfall_blocks_the_part(self):
        case = _case()
        case["single_event_data"][1] = {
            "mechanism": "single-event-burnout",
            "let_threshold": 10.0,
        }
        result = evaluate_radiation_selection(case)
        self.assertEqual(result["disposition"], RADIATION_INADEQUATE)

    def test_a_mechanism_declared_twice_rejected(self):
        case = _case()
        case["single_event_data"].append(
            {"mechanism": "single-event-latch-up", "let_threshold": 90.0}
        )
        with self.assertRaises(ValueError):
            evaluate_radiation_selection(case)

    def test_a_missing_part_reference_rejected(self):
        case = _case()
        del case["part_reference"]
        with self.assertRaises(ValueError):
            evaluate_radiation_selection(case)

    def test_a_missing_environment_let_rejected(self):
        case = _case()
        del case["environment_let"]
        with self.assertRaises(ValueError):
            evaluate_radiation_selection(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_radiation_selection(["sram"])

    def test_the_declared_lifetime_is_reported_with_the_result(self):
        result = evaluate_radiation_selection(BASE)
        self.assertAlmostEqual(result["mission_years"], 3.5, places=9)


if __name__ == "__main__":
    unittest.main(verbosity=0)
