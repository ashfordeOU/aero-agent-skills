"""Contract tests for the clause 6.6.8 class 3 in-house magnetic component.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused magnetic policy,
a drawing with no issue, an unreleased winding procedure, an uncertified
operator, a missing first article record, a heat balance that does not
settle, a stability margin under the floor, a hot spot over the insulation
rating less the class margin, a delivered unit whose measured turns ratio
sits outside the band, a per-unit screening step some unit never ran, and a
sample-drawn step run on fewer units than the batch size demands.
"""

import math
import unittest

from q6013_class_3_self_made_magnetics_logic import (
    BUILD_BASIS_NOT_ESTABLISHED,
    DEFAULT_MAGNETIC_POLICY,
    HOT_SPOT_OVER_INSULATION_RATING,
    IMPREGNATION_AND_VARNISH_VERIFICATION,
    MAGNETIC_DIELECTRIC_WITHSTAND_TEST,
    MAGNETIC_THERMAL_CYCLE_CONDITIONING,
    MEETS_CLASS_THREE_SCOPE,
    PER_UNIT_SCREENING_STEPS,
    RECOGNISED_SCREENING_STEPS,
    SAMPLE_SCREENING_STEPS,
    SCREENING_COVERAGE_SHORT,
    THERMAL_STABILITY_MARGIN_SHORT,
    TURNS_RATIO_OUT_OF_TOLERANCE,
    VISUAL_AND_WORKMANSHIP_INSPECTION,
    WINDING_CONTINUITY_AND_TURNS_RATIO_CHECK,
    WINDING_INSULATION_RESISTANCE_MEASUREMENT,
    WINDING_THERMAL_SOLUTION_DOES_NOT_SETTLE,
    allowed_hot_spot_c,
    assess_in_house_magnetic,
    build_basis_findings,
    copper_loss_coefficient_w,
    declared_turns_ratio,
    hot_spot_advisories,
    out_of_tolerance_units,
    per_unit_screening_gaps,
    required_sample_units,
    sample_screening_gaps,
    step_coverage,
    thermal_solution_settles,
    thermal_stability_margin,
    turns_ratio_deviation,
    validate_batch,
    validate_build_basis,
    validate_magnetic_policy,
    validate_thermal_case,
    validate_unit,
    validate_units,
    validate_winding,
    validate_windings,
    winding_hot_spot_c,
)

EXPECTED_COEFFICIENT_W = 2.32
EXPECTED_STABILITY_MARGIN = 27.41949635869088
EXPECTED_HOT_SPOT_C = 53.7093951239277


def _policy(**overrides):
    policy = dict(DEFAULT_MAGNETIC_POLICY)
    policy.update(overrides)
    return policy


def _winding(identifier, turns, resistance, current):
    return {
        "identifier": identifier,
        "turns": turns,
        "resistance_at_reference_ohm": resistance,
        "current_a": current,
    }


def _windings():
    return [
        _winding("W-PRI", 100, 0.5, 1.2),
        _winding("W-SEC", 25, 0.1, 4.0),
    ]


def _unit(serial, ratio=4.0, steps=None):
    return {
        "serial": serial,
        "measured_turns_ratio": ratio,
        "steps_run": tuple(PER_UNIT_SCREENING_STEPS) if steps is None else tuple(steps),
    }


def _units(count=24, sampled=3):
    units = []
    for index in range(1, count + 1):
        steps = list(PER_UNIT_SCREENING_STEPS)
        if index <= sampled:
            steps.extend(SAMPLE_SCREENING_STEPS)
        units.append(_unit("SN-%03d" % index, steps=steps))
    return units


def _case(**overrides):
    case = {
        "designation": "T1-FLYBACK-TRANSFORMER",
        "in_house_drawing": "DRW-MAG-4412",
        "drawing_issue": "C",
        "winding_procedure_released": True,
        "operator_certified": True,
        "first_article_record": "FAI-MAG-09",
        "windings": _windings(),
        "design_turns_ratio": 4.0,
        "baseplate_temperature_c": 40.0,
        "thermal_conductance_w_per_k": 0.25,
        "core_loss_w": 0.8,
        "insulation_temperature_rating_c": 130.0,
        "batch_reference": "MAG-B-2026-03",
        "batch_size": 24,
        "units": _units(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_magnetic_policy(DEFAULT_MAGNETIC_POLICY), DEFAULT_MAGNETIC_POLICY
        )

    def test_a_zero_copper_coefficient_refused(self):
        with self.assertRaises(ValueError):
            validate_magnetic_policy(
                _policy(copper_temperature_coefficient_per_k=0.0)
            )

    def test_a_copper_coefficient_of_one_refused(self):
        with self.assertRaises(ValueError):
            validate_magnetic_policy(
                _policy(copper_temperature_coefficient_per_k=1.0)
            )

    def test_a_stability_floor_below_one_refused(self):
        with self.assertRaises(ValueError):
            validate_magnetic_policy(_policy(min_thermal_stability_margin=0.5))

    def test_a_negative_insulation_margin_refused(self):
        with self.assertRaises(ValueError):
            validate_magnetic_policy(_policy(insulation_margin_c=-5.0))

    def test_a_zero_turns_ratio_tolerance_refused(self):
        with self.assertRaises(ValueError):
            validate_magnetic_policy(_policy(turns_ratio_tolerance=0.0))

    def test_a_zero_sample_fraction_refused(self):
        with self.assertRaises(ValueError):
            validate_magnetic_policy(_policy(sample_fraction=0.0))

    def test_a_sample_fraction_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_magnetic_policy(_policy(sample_fraction=1.4))

    def test_a_zero_minimum_sample_refused(self):
        with self.assertRaises(ValueError):
            validate_magnetic_policy(_policy(min_sample_units=0))

    def test_a_non_boolean_procedure_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_magnetic_policy(_policy(require_released_procedure="yes"))

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_magnetic_policy(["sample_fraction"])


class BuildBasisTests(unittest.TestCase):
    def test_a_good_basis_reads_back(self):
        basis = validate_build_basis(_case())
        self.assertEqual(basis["in_house_drawing"], "DRW-MAG-4412")
        self.assertTrue(basis["operator_certified"])

    def test_a_sound_basis_draws_no_finding(self):
        self.assertEqual(build_basis_findings(_case()), ())

    def test_a_drawing_with_no_issue_is_named(self):
        findings = build_basis_findings(_case(drawing_issue="  "))
        self.assertEqual(len(findings), 1)
        self.assertIn("DRW-MAG-4412", findings[0])

    def test_no_drawing_at_all_is_reported_once_not_twice(self):
        findings = build_basis_findings(_case(in_house_drawing="", drawing_issue=""))
        self.assertEqual(len(findings), 1)

    def test_an_unreleased_procedure_is_named(self):
        self.assertEqual(
            len(build_basis_findings(_case(winding_procedure_released=False))), 1
        )

    def test_a_project_may_waive_the_released_procedure(self):
        self.assertEqual(
            build_basis_findings(
                _case(winding_procedure_released=False),
                _policy(require_released_procedure=False),
            ),
            (),
        )

    def test_an_uncertified_operator_is_named(self):
        self.assertEqual(
            len(build_basis_findings(_case(operator_certified=False))), 1
        )

    def test_a_missing_first_article_record_is_named(self):
        self.assertEqual(
            len(build_basis_findings(_case(first_article_record=""))), 1
        )

    def test_every_basis_reason_is_reported_not_only_the_first(self):
        findings = build_basis_findings(
            _case(
                designation="",
                in_house_drawing="",
                winding_procedure_released=False,
                operator_certified=False,
                first_article_record="",
            )
        )
        self.assertEqual(len(findings), 5)

    def test_a_non_boolean_operator_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_build_basis(_case(operator_certified="signed"))


class WindingValidationTests(unittest.TestCase):
    def test_a_good_winding_reads_back(self):
        record = validate_winding(_winding("W-PRI", 100, 0.5, 1.2))
        self.assertEqual(record["turns"], 100)
        self.assertAlmostEqual(record["current_a"], 1.2, places=9)

    def test_a_blank_winding_identifier_refused(self):
        with self.assertRaises(ValueError):
            validate_winding(_winding("  ", 100, 0.5, 1.2))

    def test_zero_turns_refused(self):
        with self.assertRaises(ValueError):
            validate_winding(_winding("W-PRI", 0, 0.5, 1.2))

    def test_a_fractional_turn_count_refused(self):
        with self.assertRaises(ValueError):
            validate_winding(_winding("W-PRI", 12.5, 0.5, 1.2))

    def test_zero_resistance_refused(self):
        with self.assertRaises(ValueError):
            validate_winding(_winding("W-PRI", 100, 0.0, 1.2))

    def test_a_negative_current_refused(self):
        with self.assertRaises(ValueError):
            validate_winding(_winding("W-PRI", 100, 0.5, -1.0))

    def test_duplicate_winding_refused(self):
        with self.assertRaises(ValueError):
            validate_windings([_winding("W-PRI", 100, 0.5, 1.2)] * 2)

    def test_an_empty_winding_set_refused(self):
        with self.assertRaises(ValueError):
            validate_windings([])

    def test_a_non_sequence_winding_set_refused(self):
        with self.assertRaises(ValueError):
            validate_windings({"identifier": "W-PRI"})


class ThermalTests(unittest.TestCase):
    def test_the_thermal_inputs_read_back(self):
        thermal = validate_thermal_case(_case())
        self.assertAlmostEqual(thermal["thermal_conductance_w_per_k"], 0.25, places=9)

    def test_a_zero_thermal_conductance_refused(self):
        with self.assertRaises(ValueError):
            validate_thermal_case(_case(thermal_conductance_w_per_k=0.0))

    def test_a_negative_core_loss_refused(self):
        with self.assertRaises(ValueError):
            validate_thermal_case(_case(core_loss_w=-0.2))

    def test_the_copper_coefficient_sums_every_winding(self):
        self.assertAlmostEqual(
            copper_loss_coefficient_w(_case()), EXPECTED_COEFFICIENT_W, places=9
        )

    def test_the_stability_margin_is_the_conductance_over_the_loss_slope(self):
        self.assertAlmostEqual(
            thermal_stability_margin(_case()), EXPECTED_STABILITY_MARGIN, places=9
        )

    def test_an_unenergised_winding_set_has_an_unbounded_margin(self):
        windings = [
            _winding("W-PRI", 100, 0.5, 0.0),
            _winding("W-SEC", 25, 0.1, 0.0),
        ]
        self.assertTrue(math.isinf(thermal_stability_margin(_case(windings=windings))))

    def test_the_heat_balance_settles_for_a_sound_component(self):
        self.assertTrue(thermal_solution_settles(_case()))

    def test_the_hot_spot_solves_the_balance_rather_than_reading_it_cold(self):
        hot = winding_hot_spot_c(_case())
        self.assertAlmostEqual(hot, EXPECTED_HOT_SPOT_C, places=6)
        self.assertGreater(hot, _case()["baseplate_temperature_c"])

    def test_a_weaker_heat_path_settles_the_winding_hotter(self):
        self.assertGreater(
            winding_hot_spot_c(_case(thermal_conductance_w_per_k=0.12)),
            winding_hot_spot_c(_case()),
        )

    def test_a_component_that_cannot_shed_its_copper_loss_does_not_settle(self):
        case = _case(thermal_conductance_w_per_k=0.005)
        self.assertFalse(thermal_solution_settles(case))
        with self.assertRaises(ValueError):
            winding_hot_spot_c(case)

    def test_the_allowed_hot_spot_holds_the_class_margin_back(self):
        self.assertAlmostEqual(allowed_hot_spot_c(_case()), 120.0, places=9)

    def test_a_copper_dominated_component_raises_an_advisory(self):
        advisories = hot_spot_advisories(_case())
        self.assertEqual(len(advisories), 1)
        self.assertIn("copper", advisories[0])

    def test_a_core_dominated_component_raises_no_advisory(self):
        self.assertEqual(hot_spot_advisories(_case(core_loss_w=6.0)), ())


class TurnsRatioTests(unittest.TestCase):
    def test_the_declared_ratio_reads_back_when_it_matches_the_turns(self):
        self.assertAlmostEqual(declared_turns_ratio(_case()), 4.0, places=9)

    def test_a_ratio_disagreeing_with_the_turns_is_refused(self):
        with self.assertRaises(ValueError):
            declared_turns_ratio(_case(design_turns_ratio=3.0))

    def test_a_zero_design_ratio_refused(self):
        with self.assertRaises(ValueError):
            declared_turns_ratio(_case(design_turns_ratio=0.0))

    def test_a_three_winding_component_is_not_cross_checked_on_turns(self):
        windings = _windings() + [_winding("W-AUX", 10, 0.2, 0.3)]
        self.assertAlmostEqual(
            declared_turns_ratio(_case(windings=windings, design_turns_ratio=4.0)),
            4.0,
            places=9,
        )

    def test_the_deviation_is_taken_relative_to_the_design_ratio(self):
        self.assertAlmostEqual(
            turns_ratio_deviation(_unit("SN-001", ratio=4.08), _case()),
            0.02,
            places=9,
        )

    def test_a_deviation_landing_exactly_on_the_tolerance_is_admissible(self):
        units = _units()
        units[0]["measured_turns_ratio"] = 4.08
        self.assertEqual(out_of_tolerance_units(_case(units=units)), ())

    def test_every_unit_outside_the_band_is_named(self):
        units = _units()
        units[1]["measured_turns_ratio"] = 4.5
        units[4]["measured_turns_ratio"] = 3.6
        self.assertEqual(
            out_of_tolerance_units(_case(units=units)), ("SN-002", "SN-005")
        )


class ScreeningTests(unittest.TestCase):
    def test_the_batch_reads_back(self):
        batch = validate_batch(_case())
        self.assertEqual(batch["batch_size"], 24)

    def test_a_zero_batch_size_refused(self):
        with self.assertRaises(ValueError):
            validate_batch(_case(batch_size=0))

    def test_a_delivery_larger_than_its_batch_refused(self):
        with self.assertRaises(ValueError):
            validate_units(_case(batch_size=10))

    def test_a_duplicate_unit_serial_refused(self):
        with self.assertRaises(ValueError):
            validate_units(_case(units=[_unit("SN-001"), _unit("SN-001")]))

    def test_an_empty_delivery_refused(self):
        with self.assertRaises(ValueError):
            validate_units(_case(units=[]))

    def test_a_blank_unit_serial_refused(self):
        with self.assertRaises(ValueError):
            validate_unit(_unit("   "))

    def test_an_unrecognised_screening_step_refused(self):
        with self.assertRaises(ValueError):
            validate_unit(_unit("SN-001", steps=["had-a-look-at-it"]))

    def test_a_repeated_screening_step_on_one_unit_refused(self):
        with self.assertRaises(ValueError):
            validate_unit(
                _unit(
                    "SN-001",
                    steps=[
                        VISUAL_AND_WORKMANSHIP_INSPECTION,
                        VISUAL_AND_WORKMANSHIP_INSPECTION,
                    ],
                )
            )

    def test_the_sample_follows_the_batch_size_through_the_fraction(self):
        self.assertEqual(required_sample_units(_case(batch_size=100)), 10)

    def test_a_small_batch_is_floored_rather_than_screened_by_one_piece(self):
        self.assertEqual(required_sample_units(_case(batch_size=8)), 3)

    def test_the_sample_never_exceeds_the_batch_it_is_drawn_from(self):
        self.assertEqual(required_sample_units(_case(batch_size=2)), 2)

    def test_a_batch_landing_on_a_whole_sample_is_not_rounded_up(self):
        self.assertEqual(required_sample_units(_case(batch_size=30)), 3)

    def test_the_coverage_counts_every_recognised_step(self):
        coverage = step_coverage(_case())
        self.assertEqual(set(coverage), set(RECOGNISED_SCREENING_STEPS))
        self.assertEqual(coverage[VISUAL_AND_WORKMANSHIP_INSPECTION], 24)
        self.assertEqual(coverage[MAGNETIC_DIELECTRIC_WITHSTAND_TEST], 3)

    def test_a_sound_batch_has_no_screening_gap(self):
        self.assertEqual(per_unit_screening_gaps(_case()), ())
        self.assertEqual(sample_screening_gaps(_case()), ())

    def test_a_per_unit_step_missed_on_one_unit_is_a_gap(self):
        units = _units()
        units[7]["steps_run"] = (
            VISUAL_AND_WORKMANSHIP_INSPECTION,
            WINDING_CONTINUITY_AND_TURNS_RATIO_CHECK,
        )
        gaps = per_unit_screening_gaps(_case(units=units))
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["step"], WINDING_INSULATION_RESISTANCE_MEASUREMENT)
        self.assertEqual(gaps[0]["covered"], 23)
        self.assertEqual(gaps[0]["required"], 24)

    def test_a_sample_step_run_on_too_few_units_is_a_gap(self):
        gaps = sample_screening_gaps(_case(units=_units(sampled=1)))
        self.assertEqual(len(gaps), 3)
        self.assertEqual(gaps[0]["covered"], 1)
        self.assertEqual(gaps[0]["required"], 3)

    def test_a_larger_batch_asks_for_a_larger_sample_from_the_same_units(self):
        case = _case(batch_size=100, units=_units(count=100, sampled=4))
        gaps = sample_screening_gaps(case)
        self.assertEqual(len(gaps), 3)
        self.assertEqual(gaps[0]["required"], 10)


class AssessmentTests(unittest.TestCase):
    def test_a_sound_batch_meets_the_class_scope(self):
        result = assess_in_house_magnetic(_case())
        self.assertEqual(result["verdict"], MEETS_CLASS_THREE_SCOPE)
        self.assertEqual(result["batch_reference"], "MAG-B-2026-03")
        self.assertEqual(result["delivered_units"], 24)
        self.assertEqual(result["required_sample_units"], 3)
        self.assertAlmostEqual(
            result["winding_hot_spot_c"], EXPECTED_HOT_SPOT_C, places=6
        )
        self.assertAlmostEqual(result["allowed_hot_spot_c"], 120.0, places=9)

    def test_the_copper_advisory_travels_with_a_passing_verdict(self):
        result = assess_in_house_magnetic(_case())
        self.assertEqual(len(result["advisories"]), 1)

    def test_a_basis_gap_closes_the_assessment_before_anything_is_computed(self):
        result = assess_in_house_magnetic(_case(drawing_issue=""))
        self.assertEqual(result["verdict"], BUILD_BASIS_NOT_ESTABLISHED)
        self.assertIsNone(result["winding_hot_spot_c"])

    def test_a_runaway_winding_closes_the_assessment_on_its_own_outcome(self):
        result = assess_in_house_magnetic(_case(thermal_conductance_w_per_k=0.005))
        self.assertEqual(result["verdict"], WINDING_THERMAL_SOLUTION_DOES_NOT_SETTLE)
        self.assertIsNone(result["winding_hot_spot_c"])

    def test_a_thin_stability_margin_closes_the_assessment(self):
        result = assess_in_house_magnetic(_case(thermal_conductance_w_per_k=0.015))
        self.assertEqual(result["verdict"], THERMAL_STABILITY_MARGIN_SHORT)

    def test_a_stability_margin_landing_exactly_on_the_floor_is_admissible(self):
        floor = 2.0
        conductance = floor * DEFAULT_MAGNETIC_POLICY[
            "copper_temperature_coefficient_per_k"
        ] * copper_loss_coefficient_w(_case())
        result = assess_in_house_magnetic(
            _case(
                thermal_conductance_w_per_k=conductance,
                insulation_temperature_rating_c=2000.0,
            )
        )
        self.assertAlmostEqual(result["thermal_stability_margin"], floor, places=9)
        self.assertEqual(result["verdict"], MEETS_CLASS_THREE_SCOPE)

    def test_a_hot_spot_over_the_insulation_rating_closes_the_assessment(self):
        result = assess_in_house_magnetic(
            _case(insulation_temperature_rating_c=55.0)
        )
        self.assertEqual(result["verdict"], HOT_SPOT_OVER_INSULATION_RATING)

    def test_a_hot_spot_landing_exactly_on_the_allowance_is_admissible(self):
        rating = EXPECTED_HOT_SPOT_C + DEFAULT_MAGNETIC_POLICY["insulation_margin_c"]
        result = assess_in_house_magnetic(
            _case(insulation_temperature_rating_c=rating)
        )
        self.assertEqual(result["verdict"], MEETS_CLASS_THREE_SCOPE)

    def test_an_out_of_tolerance_unit_closes_the_assessment(self):
        units = _units()
        units[3]["measured_turns_ratio"] = 4.4
        result = assess_in_house_magnetic(_case(units=units))
        self.assertEqual(result["verdict"], TURNS_RATIO_OUT_OF_TOLERANCE)
        self.assertEqual(result["out_of_tolerance_units"], ("SN-004",))

    def test_every_out_of_tolerance_unit_is_named_not_only_the_first(self):
        units = _units()
        units[3]["measured_turns_ratio"] = 4.4
        units[9]["measured_turns_ratio"] = 3.5
        result = assess_in_house_magnetic(_case(units=units))
        self.assertEqual(len(result["findings"]), 2)

    def test_a_per_unit_screening_gap_closes_the_assessment(self):
        units = _units()
        units[2]["steps_run"] = tuple(SAMPLE_SCREENING_STEPS)
        result = assess_in_house_magnetic(_case(units=units))
        self.assertEqual(result["verdict"], SCREENING_COVERAGE_SHORT)
        self.assertEqual(len(result["per_unit_screening_gaps"]), 3)

    def test_a_sample_screening_gap_closes_the_assessment(self):
        result = assess_in_house_magnetic(_case(units=_units(sampled=2)))
        self.assertEqual(result["verdict"], SCREENING_COVERAGE_SHORT)
        self.assertEqual(len(result["sample_screening_gaps"]), 3)

    def test_both_screening_shortfalls_are_reported_together(self):
        units = _units(sampled=1)
        units[5]["steps_run"] = (VISUAL_AND_WORKMANSHIP_INSPECTION,)
        result = assess_in_house_magnetic(_case(units=units))
        self.assertEqual(result["verdict"], SCREENING_COVERAGE_SHORT)
        self.assertEqual(len(result["per_unit_screening_gaps"]), 2)
        self.assertEqual(len(result["sample_screening_gaps"]), 3)

    def test_a_sample_step_may_be_spread_across_different_units(self):
        units = _units(sampled=0)
        units[0]["steps_run"] = tuple(units[0]["steps_run"]) + (
            MAGNETIC_DIELECTRIC_WITHSTAND_TEST,
            MAGNETIC_THERMAL_CYCLE_CONDITIONING,
            IMPREGNATION_AND_VARNISH_VERIFICATION,
        )
        units[6]["steps_run"] = tuple(units[6]["steps_run"]) + tuple(
            SAMPLE_SCREENING_STEPS
        )
        units[15]["steps_run"] = tuple(units[15]["steps_run"]) + tuple(
            SAMPLE_SCREENING_STEPS
        )
        result = assess_in_house_magnetic(_case(units=units))
        self.assertEqual(result["verdict"], MEETS_CLASS_THREE_SCOPE)

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_in_house_magnetic(["designation"])


if __name__ == "__main__":
    unittest.main()
