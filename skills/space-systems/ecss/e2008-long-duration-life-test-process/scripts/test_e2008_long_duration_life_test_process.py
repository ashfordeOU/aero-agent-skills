"""Contract tests for the clause 6.4.3.18.2 life test approach selection."""

import unittest

from e2008_long_duration_life_test_process_logic import (
    ACCELERATED_CYCLING,
    ACCELERATED_TEMPERATURE,
    ACCEPTED_APPROACHES,
    APPROACH_NOT_ACCEPTED,
    APPROACH_NOT_FEASIBLE,
    APPROACH_SELECTED_AND_DOCUMENTED,
    DEFAULT_PROCESS_POLICY,
    DOCUMENTATION_INCOMPLETE,
    MORE_THAN_ONE_APPROACH_DECLARED,
    NO_APPROACH_DECLARED,
    QUALIFIED_HERITAGE,
    REAL_TIME,
    accepted_approaches,
    admissible_approaches,
    approach_feasibility,
    declared_approaches,
    heritage_exposure_ratio,
    laboratory_hours_for,
    missing_evidence,
    require_accepted_approach,
    required_evidence_for,
    select_and_document_life_test_approach,
    usable_window_hours,
    validate_process_policy,
    validate_service_demand,
)

SERVICE_HOURS = 131490.0
SERVICE_CYCLES = 5500.0


def _policy(**overrides):
    policy = dict(DEFAULT_PROCESS_POLICY)
    policy.update(overrides)
    return policy


def _demand(**overrides):
    demand = {
        "required_service_hours": SERVICE_HOURS,
        "required_service_cycles": SERVICE_CYCLES,
    }
    demand.update(overrides)
    return demand


def _plan(**overrides):
    plan = {
        "acceleration_factor": 24.0,
        "cycles_per_hour": 1.5,
        "reference_exposure_hours": 150000.0,
    }
    plan.update(overrides)
    return plan


def _case(**overrides):
    case = {
        "declared_approaches": [ACCELERATED_TEMPERATURE],
        "documentation_record": list(required_evidence_for(ACCELERATED_TEMPERATURE)),
        "service_demand": _demand(),
        "plan": _plan(),
        "available_window_hours": 12000.0,
    }
    case.update(overrides)
    return case


class MenuTests(unittest.TestCase):
    def test_the_menu_holds_exactly_four_approaches(self):
        self.assertEqual(len(accepted_approaches()), 4)
        self.assertEqual(len(set(ACCEPTED_APPROACHES)), 4)

    def test_every_approach_name_is_hyphenated(self):
        for name in ACCEPTED_APPROACHES:
            self.assertNotIn(" ", name)

    def test_an_approach_off_the_menu_is_refused(self):
        with self.assertRaises(ValueError):
            require_accepted_approach("bake-until-it-stops")

    def test_a_non_string_approach_is_refused(self):
        with self.assertRaises(ValueError):
            require_accepted_approach(4)

    def test_surrounding_whitespace_is_normalised(self):
        self.assertEqual(require_accepted_approach("  " + REAL_TIME + " "), REAL_TIME)


class EvidenceTests(unittest.TestCase):
    def test_every_approach_declares_its_own_evidence_set(self):
        sets = {name: required_evidence_for(name) for name in ACCEPTED_APPROACHES}
        self.assertEqual(len(set(sets.values())), 4)

    def test_accelerated_temperature_needs_the_activation_energy(self):
        self.assertIn(
            "activation-energy-justification",
            required_evidence_for(ACCELERATED_TEMPERATURE),
        )

    def test_real_time_does_not_need_an_activation_energy(self):
        self.assertNotIn(
            "activation-energy-justification", required_evidence_for(REAL_TIME)
        )

    def test_heritage_needs_the_delta_analysis(self):
        self.assertIn(
            "design-and-process-delta-analysis",
            required_evidence_for(QUALIFIED_HERITAGE),
        )

    def test_cycling_needs_the_conversion_back_to_service(self):
        self.assertIn(
            "cycle-to-service-conversion", required_evidence_for(ACCELERATED_CYCLING)
        )

    def test_a_complete_record_leaves_no_gap(self):
        self.assertEqual(
            missing_evidence(REAL_TIME, required_evidence_for(REAL_TIME)), ()
        )

    def test_a_gap_is_named(self):
        record = [
            item
            for item in required_evidence_for(ACCELERATED_TEMPERATURE)
            if item != "mechanism-ceiling-statement"
        ]
        self.assertEqual(
            missing_evidence(ACCELERATED_TEMPERATURE, record),
            ("mechanism-ceiling-statement",),
        )

    def test_a_non_sequence_record_is_refused(self):
        with self.assertRaises(ValueError):
            missing_evidence(REAL_TIME, "test-article-definition")


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_process_policy(DEFAULT_PROCESS_POLICY), DEFAULT_PROCESS_POLICY
        )

    def test_a_partial_preference_order_is_refused(self):
        with self.assertRaises(ValueError):
            validate_process_policy(_policy(preference_order=(REAL_TIME,)))

    def test_a_repeated_approach_in_the_order_is_refused(self):
        with self.assertRaises(ValueError):
            validate_process_policy(
                _policy(preference_order=(REAL_TIME, REAL_TIME))
            )

    def test_a_whole_window_margin_is_refused(self):
        with self.assertRaises(ValueError):
            validate_process_policy(_policy(schedule_margin_fraction=1.0))

    def test_a_negative_margin_is_refused(self):
        with self.assertRaises(ValueError):
            validate_process_policy(_policy(schedule_margin_fraction=-0.2))

    def test_a_heritage_ratio_below_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_process_policy(_policy(minimum_heritage_exposure_ratio=0.5))


class DemandTests(unittest.TestCase):
    def test_a_valid_demand_returns_hours_and_cycles(self):
        hours, cycles = validate_service_demand(_demand())
        self.assertAlmostEqual(hours, SERVICE_HOURS, places=9)
        self.assertAlmostEqual(cycles, SERVICE_CYCLES, places=9)

    def test_a_zero_hour_demand_is_refused(self):
        with self.assertRaises(ValueError):
            validate_service_demand(_demand(required_service_hours=0.0))

    def test_a_non_mapping_demand_is_refused(self):
        with self.assertRaises(ValueError):
            validate_service_demand([SERVICE_HOURS])


class LaboratoryHoursTests(unittest.TestCase):
    def test_real_time_costs_the_whole_service_life(self):
        self.assertAlmostEqual(
            laboratory_hours_for(REAL_TIME, _plan(), _demand()),
            SERVICE_HOURS,
            places=6,
        )

    def test_acceleration_divides_the_service_hours(self):
        self.assertAlmostEqual(
            laboratory_hours_for(ACCELERATED_TEMPERATURE, _plan(), _demand()),
            SERVICE_HOURS / 24.0,
            places=6,
        )

    def test_cycling_divides_the_cycles_by_the_rate(self):
        self.assertAlmostEqual(
            laboratory_hours_for(ACCELERATED_CYCLING, _plan(), _demand()),
            SERVICE_CYCLES / 1.5,
            places=6,
        )

    def test_an_equivalence_argument_costs_no_chamber_time(self):
        self.assertAlmostEqual(
            laboratory_hours_for(QUALIFIED_HERITAGE, _plan(), _demand()),
            0.0,
            places=9,
        )

    def test_a_factor_below_one_is_refused(self):
        with self.assertRaises(ValueError):
            laboratory_hours_for(
                ACCELERATED_TEMPERATURE, _plan(acceleration_factor=0.4), _demand()
            )

    def test_a_missing_cycle_rate_is_refused(self):
        plan = _plan()
        del plan["cycles_per_hour"]
        with self.assertRaises(ValueError):
            laboratory_hours_for(ACCELERATED_CYCLING, plan, _demand())

    def test_the_heritage_ratio_is_the_exposure_over_the_demand(self):
        self.assertAlmostEqual(
            heritage_exposure_ratio(_plan(), _demand()),
            150000.0 / SERVICE_HOURS,
            places=9,
        )


class WindowTests(unittest.TestCase):
    def test_the_margin_is_held_back_from_the_window(self):
        self.assertAlmostEqual(usable_window_hours(10000.0), 9000.0, places=6)

    def test_a_zero_margin_leaves_the_whole_window(self):
        self.assertAlmostEqual(
            usable_window_hours(10000.0, _policy(schedule_margin_fraction=0.0)),
            10000.0,
            places=6,
        )

    def test_a_zero_window_is_refused(self):
        with self.assertRaises(ValueError):
            usable_window_hours(0.0)

    def test_a_run_exactly_filling_the_usable_window_is_feasible(self):
        case = _case(available_window_hours=SERVICE_HOURS / 24.0 / 0.9)
        report = approach_feasibility(ACCELERATED_TEMPERATURE, case)
        self.assertAlmostEqual(
            report["laboratory_hours"], report["usable_window_hours"], places=6
        )
        self.assertTrue(report["feasible"])

    def test_real_time_does_not_fit_a_short_window(self):
        report = approach_feasibility(REAL_TIME, _case())
        self.assertFalse(report["feasible"])
        self.assertEqual(len(report["reasons"]), 1)

    def test_thin_heritage_exposure_is_not_feasible(self):
        case = _case(plan=_plan(reference_exposure_hours=40000.0))
        report = approach_feasibility(QUALIFIED_HERITAGE, case)
        self.assertFalse(report["feasible"])

    def test_admissible_set_follows_the_preference_order(self):
        case = _case()
        self.assertEqual(
            admissible_approaches(case),
            (ACCELERATED_TEMPERATURE, ACCELERATED_CYCLING, QUALIFIED_HERITAGE),
        )


class SelectionTests(unittest.TestCase):
    def test_no_declaration_closes_the_review(self):
        case = _case()
        del case["declared_approaches"]
        result = select_and_document_life_test_approach(case)
        self.assertEqual(result["verdict"], NO_APPROACH_DECLARED)

    def test_an_approach_off_the_menu_is_reported(self):
        result = select_and_document_life_test_approach(
            _case(declared_approaches=["run-it-until-someone-asks"])
        )
        self.assertEqual(result["verdict"], APPROACH_NOT_ACCEPTED)

    def test_two_approaches_together_are_reported(self):
        result = select_and_document_life_test_approach(
            _case(declared_approaches=[REAL_TIME, ACCELERATED_TEMPERATURE])
        )
        self.assertEqual(result["verdict"], MORE_THAN_ONE_APPROACH_DECLARED)

    def test_a_repeated_declaration_is_one_approach(self):
        result = select_and_document_life_test_approach(
            _case(
                declared_approaches=[ACCELERATED_TEMPERATURE, ACCELERATED_TEMPERATURE]
            )
        )
        self.assertEqual(result["declared_approaches"], (ACCELERATED_TEMPERATURE,))
        self.assertEqual(result["verdict"], APPROACH_SELECTED_AND_DOCUMENTED)

    def test_a_documented_feasible_approach_is_selected(self):
        result = select_and_document_life_test_approach(_case())
        self.assertEqual(result["verdict"], APPROACH_SELECTED_AND_DOCUMENTED)
        self.assertEqual(result["selected_approach"], ACCELERATED_TEMPERATURE)
        self.assertEqual(result["missing_evidence"], ())

    def test_a_thin_record_is_reported_before_feasibility(self):
        result = select_and_document_life_test_approach(
            _case(documentation_record=["test-article-definition"])
        )
        self.assertEqual(result["verdict"], DOCUMENTATION_INCOMPLETE)
        self.assertIn("mechanism-ceiling-statement", result["missing_evidence"])

    def test_a_documented_but_unrunnable_approach_is_reported(self):
        result = select_and_document_life_test_approach(
            _case(
                declared_approaches=[REAL_TIME],
                documentation_record=list(required_evidence_for(REAL_TIME)),
            )
        )
        self.assertEqual(result["verdict"], APPROACH_NOT_FEASIBLE)
        self.assertTrue(result["findings"])

    def test_other_runnable_approaches_are_advised(self):
        result = select_and_document_life_test_approach(_case())
        self.assertEqual(len(result["advisories"]), 2)

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            select_and_document_life_test_approach([REAL_TIME])

    def test_a_non_sequence_declaration_is_refused(self):
        with self.assertRaises(ValueError):
            declared_approaches(_case(declared_approaches=REAL_TIME))


if __name__ == "__main__":
    unittest.main()
