"""Contract tests for the clause 5.1.2 detailed die-criteria logic."""

import math
import unittest

from q6012_die_selection_detailed_requirements_logic import (
    ABSOLUTE_ZERO_C,
    BOLTZMANN_EV_PER_K,
    ESD_CATEGORY_ORDER,
    MANDATORY_CRITERIA,
    MARGIN_TOLERANCE,
    arrhenius_life_hours,
    assess_detailed_requirements,
    channel_temperature_c,
    criterion_verdict,
    derated_limit,
    evaluate_bias_criteria,
    evaluate_handling_criteria,
    evaluate_reliability_criteria,
    evaluate_rf_criteria,
    evaluate_thermal_criteria,
    evidence_findings,
    kelvin,
)

DIE = {
    "gain_db": 22.0,
    "output_power_dbm": 34.0,
    "noise_figure_db": 2.4,
    "input_return_loss_db": 14.0,
    "output_return_loss_db": 12.0,
    "max_drain_voltage_v": 10.0,
    "max_drain_current_ma": 500.0,
    "thermal_resistance_c_per_w": 8.0,
    "max_channel_temperature_c": 175.0,
    "rated_life_hours": 1.0e6,
    "rated_life_temperature_c": 150.0,
    "activation_energy_ev": 1.5,
    "esd_sensitivity_category": "class-1c",
    "bond_pad_routes": ["die-attach-and-wire-bond", "hermetic-package"],
    "screening_level": "level-2",
    "lot_acceptance_reference": "LAT-2026-014",
    "process_monitor_reference": "PCM-2026-Q3",
}

DESIGN = {
    "required_gain_db": 20.0,
    "required_output_power_dbm": 33.0,
    "max_noise_figure_db": 3.0,
    "min_return_loss_db": 10.0,
    "applied_drain_voltage_v": 7.0,
    "applied_drain_current_ma": 300.0,
    "voltage_derating_factor": 0.8,
    "current_derating_factor": 0.8,
    "base_temperature_c": 70.0,
    "dissipated_power_w": 5.0,
    "channel_temperature_derating_c": 25.0,
    "required_life_hours": 131400.0,
    "line_esd_capability": "class-1a",
    "assembly_route": "die-attach-and-wire-bond",
}


def die(**overrides):
    record = dict(DIE)
    record.update(overrides)
    return record


def design(**overrides):
    record = dict(DESIGN)
    record.update(overrides)
    return record


def by_name(verdicts, name):
    for verdict in verdicts:
        if verdict["name"] == name:
            return verdict
    raise AssertionError("no verdict named %s" % name)


class TemperatureArithmeticTests(unittest.TestCase):
    def test_kelvin_conversion(self):
        self.assertAlmostEqual(kelvin(0.0), 273.15, places=9)

    def test_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            kelvin(ABSOLUTE_ZERO_C)

    def test_non_numeric_temperature_rejected(self):
        with self.assertRaises(ValueError):
            kelvin("cold")

    def test_channel_temperature_adds_the_thermal_rise(self):
        self.assertAlmostEqual(channel_temperature_c(70.0, 5.0, 8.0), 110.0, places=9)

    def test_zero_dissipation_leaves_the_base_temperature(self):
        self.assertAlmostEqual(channel_temperature_c(70.0, 0.0, 8.0), 70.0, places=9)

    def test_negative_dissipation_rejected(self):
        with self.assertRaises(ValueError):
            channel_temperature_c(70.0, -1.0, 8.0)

    def test_zero_thermal_resistance_rejected(self):
        with self.assertRaises(ValueError):
            channel_temperature_c(70.0, 5.0, 0.0)

    def test_boolean_power_rejected(self):
        with self.assertRaises(ValueError):
            channel_temperature_c(70.0, True, 8.0)


class DeratingTests(unittest.TestCase):
    def test_factor_scales_the_rating(self):
        self.assertAlmostEqual(derated_limit(10.0, 0.8), 8.0, places=9)

    def test_unity_factor_keeps_the_rating(self):
        self.assertAlmostEqual(derated_limit(10.0, 1.0), 10.0, places=9)

    def test_factor_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            derated_limit(10.0, 1.2)

    def test_zero_factor_rejected(self):
        with self.assertRaises(ValueError):
            derated_limit(10.0, 0.0)


class CriterionVerdictTests(unittest.TestCase):
    def test_max_sense_margin_is_headroom(self):
        verdict = criterion_verdict("x", 7.0, 8.0, "max")
        self.assertAlmostEqual(verdict["margin"], 1.0, places=9)
        self.assertTrue(verdict["met"])

    def test_min_sense_margin_is_excess(self):
        verdict = criterion_verdict("x", 22.0, 20.0, "min")
        self.assertAlmostEqual(verdict["margin"], 2.0, places=9)
        self.assertTrue(verdict["met"])

    def test_exact_equality_is_met(self):
        verdict = criterion_verdict("x", 8.0, 8.0, "max")
        self.assertAlmostEqual(verdict["margin"], 0.0, places=9)
        self.assertTrue(verdict["met"])

    def test_breach_is_not_met(self):
        verdict = criterion_verdict("x", 9.0, 8.0, "max")
        self.assertFalse(verdict["met"])

    def test_absent_value_is_an_evidence_gap(self):
        verdict = criterion_verdict("x", None, 8.0, "max")
        self.assertFalse(verdict["evidence"])
        self.assertFalse(verdict["met"])
        self.assertIsNone(verdict["margin"])

    def test_unknown_sense_rejected(self):
        with self.assertRaises(ValueError):
            criterion_verdict("x", 1.0, 2.0, "about")

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            criterion_verdict("  ", 1.0, 2.0, "max")

    def test_non_numeric_value_rejected(self):
        with self.assertRaises(ValueError):
            criterion_verdict("x", "seven", 8.0, "max")


class ArrheniusTests(unittest.TestCase):
    def test_life_at_the_rated_temperature_is_the_rated_life(self):
        self.assertAlmostEqual(
            arrhenius_life_hours(1.0e6, 150.0, 150.0, 1.5), 1.0e6, places=3
        )

    def test_hotter_channel_shortens_the_life(self):
        hot = arrhenius_life_hours(1.0e6, 150.0, 175.0, 1.5)
        self.assertAlmostEqual(hot / 1.0e6, math.exp(
            (1.5 / BOLTZMANN_EV_PER_K) * (1.0 / kelvin(175.0) - 1.0 / kelvin(150.0))
        ), places=9)

    def test_cooler_channel_extends_the_life(self):
        cool = arrhenius_life_hours(1.0e6, 150.0, 110.0, 1.5)
        self.assertGreater(cool / 1.0e6, 10.0)

    def test_zero_activation_energy_rejected(self):
        with self.assertRaises(ValueError):
            arrhenius_life_hours(1.0e6, 150.0, 110.0, 0.0)

    def test_non_positive_rated_life_rejected(self):
        with self.assertRaises(ValueError):
            arrhenius_life_hours(0.0, 150.0, 110.0, 1.5)


class RfCriteriaTests(unittest.TestCase):
    def test_all_five_criteria_are_returned(self):
        verdicts = evaluate_rf_criteria(DIE, DESIGN)
        self.assertEqual(len(verdicts), 5)

    def test_gain_above_requirement_is_met(self):
        verdict = by_name(evaluate_rf_criteria(DIE, DESIGN), "small-signal-gain-db")
        self.assertTrue(verdict["met"])
        self.assertAlmostEqual(verdict["margin"], 2.0, places=9)

    def test_noise_figure_is_a_maximum(self):
        verdict = by_name(evaluate_rf_criteria(DIE, DESIGN), "noise-figure-db")
        self.assertEqual(verdict["sense"], "max")
        self.assertAlmostEqual(verdict["margin"], 0.6, places=9)

    def test_return_loss_exactly_at_the_floor_is_met(self):
        verdicts = evaluate_rf_criteria(die(output_return_loss_db=10.0), DESIGN)
        verdict = by_name(verdicts, "output-return-loss-db")
        self.assertTrue(verdict["met"])
        self.assertAlmostEqual(verdict["margin"], 0.0, places=9)

    def test_short_output_power_is_not_met(self):
        verdicts = evaluate_rf_criteria(die(output_power_dbm=31.0), DESIGN)
        self.assertFalse(by_name(verdicts, "output-power-dbm")["met"])

    def test_absent_gain_is_an_evidence_gap(self):
        verdicts = evaluate_rf_criteria(die(gain_db=None), DESIGN)
        self.assertFalse(by_name(verdicts, "small-signal-gain-db")["evidence"])

    def test_missing_design_requirement_rejected(self):
        broken = design()
        del broken["max_noise_figure_db"]
        with self.assertRaises(ValueError):
            evaluate_rf_criteria(DIE, broken)


class BiasCriteriaTests(unittest.TestCase):
    def test_voltage_is_compared_with_the_derated_rating(self):
        verdict = by_name(evaluate_bias_criteria(DIE, DESIGN), "drain-voltage-v")
        self.assertAlmostEqual(verdict["limit"], 8.0, places=9)
        self.assertAlmostEqual(verdict["margin"], 1.0, places=9)

    def test_voltage_exactly_at_the_derated_rating_is_met(self):
        verdict = by_name(
            evaluate_bias_criteria(DIE, design(applied_drain_voltage_v=8.0)),
            "drain-voltage-v",
        )
        self.assertTrue(verdict["met"])
        self.assertAlmostEqual(verdict["margin"], 0.0, places=9)

    def test_voltage_above_the_derated_rating_is_not_met(self):
        verdict = by_name(
            evaluate_bias_criteria(DIE, design(applied_drain_voltage_v=9.0)),
            "drain-voltage-v",
        )
        self.assertFalse(verdict["met"])

    def test_undereated_absolute_maximum_is_never_the_limit(self):
        verdict = by_name(evaluate_bias_criteria(DIE, DESIGN), "drain-current-ma")
        self.assertAlmostEqual(verdict["limit"], 400.0, places=9)

    def test_absent_rating_is_an_evidence_gap(self):
        verdict = by_name(
            evaluate_bias_criteria(die(max_drain_voltage_v=None), DESIGN),
            "drain-voltage-v",
        )
        self.assertFalse(verdict["evidence"])

    def test_derating_factor_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_bias_criteria(DIE, design(voltage_derating_factor=1.5))


class ThermalAndLifeTests(unittest.TestCase):
    def test_channel_temperature_is_compared_with_the_derated_limit(self):
        verdict = evaluate_thermal_criteria(DIE, DESIGN)[0]
        self.assertAlmostEqual(verdict["value"], 110.0, places=9)
        self.assertAlmostEqual(verdict["limit"], 150.0, places=9)
        self.assertTrue(verdict["met"])

    def test_channel_temperature_exactly_at_the_limit_is_met(self):
        verdict = evaluate_thermal_criteria(DIE, design(dissipated_power_w=10.0))[0]
        self.assertAlmostEqual(verdict["value"], 150.0, places=9)
        self.assertAlmostEqual(verdict["margin"], 0.0, places=9)
        self.assertTrue(verdict["met"])

    def test_overheated_channel_is_not_met(self):
        verdict = evaluate_thermal_criteria(DIE, design(dissipated_power_w=12.0))[0]
        self.assertFalse(verdict["met"])

    def test_absent_thermal_resistance_is_an_evidence_gap(self):
        verdict = evaluate_thermal_criteria(die(thermal_resistance_c_per_w=None), DESIGN)[0]
        self.assertFalse(verdict["evidence"])

    def test_projected_life_uses_the_reached_channel_temperature(self):
        verdict = evaluate_reliability_criteria(DIE, DESIGN)[0]
        expected = arrhenius_life_hours(1.0e6, 150.0, 110.0, 1.5)
        self.assertAlmostEqual(verdict["value"], expected, places=6)
        self.assertTrue(verdict["met"])

    def test_hot_design_fails_the_life_criterion(self):
        verdict = evaluate_reliability_criteria(DIE, design(dissipated_power_w=14.0))[0]
        self.assertFalse(verdict["met"])

    def test_absent_activation_energy_is_an_evidence_gap(self):
        verdict = evaluate_reliability_criteria(die(activation_energy_ev=None), DESIGN)[0]
        self.assertFalse(verdict["evidence"])


class HandlingCriteriaTests(unittest.TestCase):
    def test_robust_die_passes_a_fragile_capable_line(self):
        verdict = by_name(evaluate_handling_criteria(DIE, DESIGN), "esd-sensitivity-category")
        self.assertTrue(verdict["met"])

    def test_die_at_the_line_category_is_met(self):
        verdicts = evaluate_handling_criteria(die(esd_sensitivity_category="class-1a"), DESIGN)
        verdict = by_name(verdicts, "esd-sensitivity-category")
        self.assertTrue(verdict["met"])
        self.assertAlmostEqual(verdict["margin"], 0.0, places=9)

    def test_die_more_fragile_than_the_line_is_not_met(self):
        verdicts = evaluate_handling_criteria(die(esd_sensitivity_category="class-0"), DESIGN)
        self.assertFalse(by_name(verdicts, "esd-sensitivity-category")["met"])

    def test_supported_assembly_route_is_met(self):
        verdict = by_name(evaluate_handling_criteria(DIE, DESIGN), "bond-pad-compatibility")
        self.assertTrue(verdict["met"])

    def test_unsupported_assembly_route_is_not_met(self):
        verdicts = evaluate_handling_criteria(DIE, design(assembly_route="flip-chip"))
        self.assertFalse(by_name(verdicts, "bond-pad-compatibility")["met"])

    def test_unrecognised_line_capability_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_handling_criteria(DIE, design(line_esd_capability="class-9"))

    def test_unrecognised_die_category_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_handling_criteria(die(esd_sensitivity_category="class-9"), DESIGN)

    def test_absent_bond_pad_routes_is_an_evidence_gap(self):
        verdicts = evaluate_handling_criteria(die(bond_pad_routes=None), DESIGN)
        self.assertFalse(by_name(verdicts, "bond-pad-compatibility")["evidence"])

    def test_every_category_name_is_ordered(self):
        self.assertEqual(len(ESD_CATEGORY_ORDER), 5)


class EvidenceTests(unittest.TestCase):
    def test_complete_record_has_no_gaps(self):
        self.assertEqual(evidence_findings(DIE), [])

    def test_absent_screening_level_is_a_gap(self):
        gaps = evidence_findings(die(screening_level=None))
        self.assertEqual([g["code"] for g in gaps], ["screening-level-absent"])

    def test_blank_reference_counts_as_absent(self):
        gaps = evidence_findings(die(lot_acceptance_reference="   "))
        self.assertEqual([g["code"] for g in gaps], ["lot-acceptance-reference-absent"])

    def test_non_mapping_die_rejected(self):
        with self.assertRaises(ValueError):
            evidence_findings(["gain_db"])


class AssessmentTests(unittest.TestCase):
    def test_compliant_die_is_selectable(self):
        result = assess_detailed_requirements(DIE, DESIGN)
        self.assertTrue(result["selectable"])
        self.assertEqual(result["findings"], [])

    def test_every_mandatory_criterion_is_evaluated(self):
        result = assess_detailed_requirements(DIE, DESIGN)
        names = {v["name"] for v in result["verdicts"]}
        for required in MANDATORY_CRITERIA:
            self.assertIn(required, names)

    def test_unmet_criterion_blocks_selection(self):
        result = assess_detailed_requirements(die(gain_db=18.0), DESIGN)
        self.assertFalse(result["selectable"])
        self.assertEqual([v["name"] for v in result["unmet"]], ["small-signal-gain-db"])

    def test_missing_datum_blocks_selection_separately(self):
        result = assess_detailed_requirements(die(noise_figure_db=None), DESIGN)
        self.assertFalse(result["selectable"])
        self.assertEqual([v["name"] for v in result["missing"]], ["noise-figure-db"])
        self.assertEqual(result["unmet"], [])

    def test_evidence_gap_alone_blocks_selection(self):
        result = assess_detailed_requirements(die(process_monitor_reference=None), DESIGN)
        self.assertFalse(result["selectable"])
        self.assertEqual(result["unmet"], [])
        self.assertEqual(len(result["evidence_gaps"]), 1)

    def test_findings_name_the_shortfall(self):
        result = assess_detailed_requirements(die(output_power_dbm=31.0), DESIGN)
        self.assertIn("output-power-dbm", result["findings"][0])

    def test_several_defects_are_all_reported(self):
        result = assess_detailed_requirements(
            die(gain_db=18.0, noise_figure_db=None, screening_level=None), DESIGN
        )
        self.assertEqual(len(result["findings"]), 3)

    def test_non_mapping_die_rejected(self):
        with self.assertRaises(ValueError):
            assess_detailed_requirements(["gain_db"], DESIGN)

    def test_non_mapping_design_rejected(self):
        with self.assertRaises(ValueError):
            assess_detailed_requirements(DIE, ["required_gain_db"])

    def test_missing_design_key_rejected(self):
        broken = design()
        del broken["required_life_hours"]
        with self.assertRaises(ValueError):
            assess_detailed_requirements(DIE, broken)

    def test_tolerance_is_small_enough_to_be_a_representation_guard(self):
        self.assertAlmostEqual(MARGIN_TOLERANCE, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main()
