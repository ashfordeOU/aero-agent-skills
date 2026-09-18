"""Contract tests for the clause 5.2 foundry-and-process selection logic."""

import unittest

from q6012_foundry_process_selection_logic import (
    CATEGORY_ORDER,
    MARGIN_TOLERANCE,
    TECHNOLOGY_FREQUENCY_CONSTANT_GHZ_UM,
    VALIDATION_STATUSES,
    assess_foundry_process_selection,
    assess_process_option,
    categorize_option,
    max_usable_frequency_ghz,
    option_score,
    process_capability_index,
    process_findings,
    rank_process_options,
    supply_continuity_margin_years,
    validate_design_need,
    validate_process_option,
    validation_currency,
    weakest_capability,
)

MONITOR = {
    "saturated-current": {
        "mean": 500.0, "sigma": 10.0, "lower_limit": 440.0, "upper_limit": 560.0,
    },
    "pinch-off-voltage": {
        "mean": -1.0, "sigma": 0.05, "lower_limit": -1.3, "upper_limit": -0.7,
    },
}

OPTION = {
    "process_id": "PH15",
    "foundry_id": "FAB-ALPHA",
    "technology": "gaas-phemt",
    "validation_status": "validated",
    "validation_reference": "VAL-2025-08",
    "validation_age_months": 12.0,
    "process_change_since_validation": False,
    "gate_length_um": 0.15,
    "breakdown_voltage_v": 18.0,
    "passives": ["mim-capacitor", "nichrome-resistor", "spiral-inductor", "through-substrate-via"],
    "monitor_lots": 8,
    "monitor_statistics": MONITOR,
    "production_horizon_years": 12.0,
    "line_certification": "line-certificate-2026",
}

NEED = {
    "max_frequency_ghz": 30.0,
    "supply_voltage_v": 7.0,
    "breakdown_factor": 2.0,
    "required_passives": ["mim-capacitor", "nichrome-resistor", "spiral-inductor"],
    "programme_horizon_years": 8.0,
    "min_capability_index": 1.33,
    "min_monitor_lots": 3,
    "validation_validity_months": 36.0,
}


def option(**overrides):
    record = dict(OPTION)
    record.update(overrides)
    return record


def need(**overrides):
    record = dict(NEED)
    record.update(overrides)
    return record


def codes(findings):
    return sorted(f["code"] for f in findings)


class FrequencyCapabilityTests(unittest.TestCase):
    def test_usable_frequency_scales_inversely_with_gate_length(self):
        self.assertAlmostEqual(max_usable_frequency_ghz(0.15, "gaas-phemt"), 60.0, places=9)

    def test_longer_gate_gives_a_lower_frequency(self):
        self.assertAlmostEqual(max_usable_frequency_ghz(0.5, "gaas-phemt"), 18.0, places=9)

    def test_technology_changes_the_constant(self):
        self.assertAlmostEqual(max_usable_frequency_ghz(0.25, "gan-hemt"), 30.0, places=9)

    def test_zero_gate_length_rejected(self):
        with self.assertRaises(ValueError):
            max_usable_frequency_ghz(0.0, "gaas-phemt")

    def test_unknown_technology_rejected(self):
        with self.assertRaises(ValueError):
            max_usable_frequency_ghz(0.15, "vacuum-tube")

    def test_every_technology_constant_is_a_usable_proportionality(self):
        for name, value in TECHNOLOGY_FREQUENCY_CONSTANT_GHZ_UM.items():
            self.assertIsInstance(name, str)
            self.assertGreater(value, 1.0)


class CapabilityIndexTests(unittest.TestCase):
    def test_centred_parameter_uses_the_half_width(self):
        self.assertAlmostEqual(
            process_capability_index(500.0, 10.0, 440.0, 560.0), 2.0, places=9
        )

    def test_offset_parameter_uses_the_nearer_limit(self):
        self.assertAlmostEqual(
            process_capability_index(530.0, 10.0, 440.0, 560.0), 1.0, places=9
        )

    def test_index_of_exactly_one_and_a_third(self):
        self.assertAlmostEqual(
            process_capability_index(0.0, 1.0, -4.0, 4.0), 4.0 / 3.0, places=9
        )

    def test_zero_sigma_rejected(self):
        with self.assertRaises(ValueError):
            process_capability_index(500.0, 0.0, 440.0, 560.0)

    def test_inverted_limits_rejected(self):
        with self.assertRaises(ValueError):
            process_capability_index(500.0, 10.0, 560.0, 440.0)

    def test_weakest_parameter_is_reported_by_name(self):
        name, index = weakest_capability(MONITOR)
        self.assertEqual(name, "pinch-off-voltage")
        self.assertAlmostEqual(index, 2.0, places=9)

    def test_empty_monitor_set_rejected(self):
        with self.assertRaises(ValueError):
            weakest_capability({})

    def test_monitor_entry_missing_a_key_rejected(self):
        with self.assertRaises(ValueError):
            weakest_capability({"x": {"mean": 1.0, "sigma": 1.0, "lower_limit": 0.0}})


class ValidationCurrencyTests(unittest.TestCase):
    def test_recent_validation_is_current(self):
        self.assertTrue(validation_currency("validated", 12.0, 36.0, False)["current"])

    def test_validation_exactly_at_the_validity_window_is_current(self):
        self.assertTrue(validation_currency("validated", 36.0, 36.0, False)["current"])

    def test_stale_validation_is_not_current(self):
        result = validation_currency("validated", 48.0, 36.0, False)
        self.assertFalse(result["current"])
        self.assertEqual(result["reason"], "validation-stale")

    def test_process_change_beats_a_recent_validation(self):
        result = validation_currency("validated", 1.0, 36.0, True)
        self.assertEqual(result["reason"], "process-changed-since-validation")

    def test_unvalidated_status_is_reported_as_status(self):
        result = validation_currency("not-validated", 1.0, 36.0, False)
        self.assertEqual(result["reason"], "status-not-validated")

    def test_absent_age_on_a_validated_process_is_its_own_reason(self):
        result = validation_currency("validated", None, 36.0, False)
        self.assertEqual(result["reason"], "validation-age-absent")

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            validation_currency("probably", 1.0, 36.0, False)

    def test_non_boolean_change_flag_rejected(self):
        with self.assertRaises(ValueError):
            validation_currency("validated", 1.0, 36.0, "yes")

    def test_every_status_name_is_known(self):
        self.assertEqual(len(VALIDATION_STATUSES), 3)


class ContinuityTests(unittest.TestCase):
    def test_longer_horizon_gives_a_positive_margin(self):
        self.assertAlmostEqual(supply_continuity_margin_years(12.0, 8.0), 4.0, places=9)

    def test_equal_horizons_give_no_margin(self):
        self.assertAlmostEqual(supply_continuity_margin_years(8.0, 8.0), 0.0, places=9)

    def test_short_horizon_gives_a_negative_margin(self):
        self.assertAlmostEqual(supply_continuity_margin_years(5.0, 8.0), -3.0, places=9)

    def test_negative_production_horizon_rejected(self):
        with self.assertRaises(ValueError):
            supply_continuity_margin_years(-1.0, 8.0)


class ValidationOfInputsTests(unittest.TestCase):
    def test_option_is_normalised(self):
        record = validate_process_option(OPTION)
        self.assertEqual(record["process_id"], "PH15")
        self.assertEqual(record["foundry_id"], "FAB-ALPHA")

    def test_missing_option_key_rejected(self):
        broken = option()
        del broken["gate_length_um"]
        with self.assertRaises(ValueError):
            validate_process_option(broken)

    def test_blank_process_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_process_option(option(process_id="  "))

    def test_boolean_monitor_lots_rejected(self):
        with self.assertRaises(ValueError):
            validate_process_option(option(monitor_lots=True))

    def test_negative_monitor_lots_rejected(self):
        with self.assertRaises(ValueError):
            validate_process_option(option(monitor_lots=-1))

    def test_blank_validation_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_process_option(option(validation_reference="   "))

    def test_need_is_normalised_with_defaults(self):
        record = validate_design_need({
            "max_frequency_ghz": 30.0, "supply_voltage_v": 7.0,
            "programme_horizon_years": 8.0,
        })
        self.assertAlmostEqual(record["breakdown_factor"], 2.0, places=9)
        self.assertEqual(record["min_monitor_lots"], 3)

    def test_missing_need_key_rejected(self):
        broken = need()
        del broken["supply_voltage_v"]
        with self.assertRaises(ValueError):
            validate_design_need(broken)

    def test_non_integer_lot_threshold_rejected(self):
        with self.assertRaises(ValueError):
            validate_design_need(need(min_monitor_lots=2.5))

    def test_non_mapping_need_rejected(self):
        with self.assertRaises(ValueError):
            validate_design_need(["max_frequency_ghz"])


class FindingTests(unittest.TestCase):
    def test_clean_option_raises_nothing(self):
        self.assertEqual(process_findings(OPTION, NEED), [])

    def test_unvalidated_process_is_an_exclusion(self):
        found = process_findings(option(validation_status="not-validated"), NEED)
        self.assertEqual(codes(found), ["process-not-validated"])
        self.assertEqual(found[0]["severity"], "exclusion")

    def test_process_change_since_validation_is_an_exclusion(self):
        found = process_findings(option(process_change_since_validation=True), NEED)
        self.assertEqual(codes(found), ["process-changed-since-validation"])

    def test_open_validation_is_an_action(self):
        found = process_findings(option(validation_status="in-validation"), NEED)
        self.assertEqual(codes(found), ["validation-in-progress"])
        self.assertEqual(found[0]["severity"], "action")

    def test_stale_validation_is_an_action(self):
        found = process_findings(option(validation_age_months=48.0), NEED)
        self.assertEqual(codes(found), ["validation-stale"])

    def test_missing_validation_reference_is_an_action(self):
        found = process_findings(option(validation_reference=None), NEED)
        self.assertEqual(codes(found), ["validation-reference-absent"])

    def test_frequency_short_of_the_need_is_an_exclusion(self):
        found = process_findings(option(gate_length_um=0.5), NEED)
        self.assertEqual(codes(found), ["frequency-capability-short"])

    def test_frequency_exactly_at_the_need_is_accepted(self):
        found = process_findings(option(gate_length_um=0.3), NEED)
        self.assertEqual(found, [])

    def test_breakdown_voltage_exactly_at_the_factor_is_accepted(self):
        found = process_findings(option(breakdown_voltage_v=14.0), NEED)
        self.assertEqual(found, [])

    def test_breakdown_voltage_below_the_factor_is_an_exclusion(self):
        found = process_findings(option(breakdown_voltage_v=12.0), NEED)
        self.assertEqual(codes(found), ["breakdown-voltage-short"])

    def test_missing_passive_element_is_an_exclusion(self):
        found = process_findings(option(passives=["mim-capacitor"]), NEED)
        self.assertEqual(
            codes(found), ["passive-element-absent", "passive-element-absent"]
        )

    def test_weak_capability_index_is_an_exclusion(self):
        weak = {"gate-resistance": {
            "mean": 100.0, "sigma": 20.0, "lower_limit": 40.0, "upper_limit": 160.0,
        }}
        found = process_findings(option(monitor_statistics=weak), NEED)
        self.assertEqual(codes(found), ["capability-index-short"])

    def test_capability_exactly_at_the_threshold_is_accepted(self):
        exact = {"gate-resistance": {
            "mean": 0.0, "sigma": 1.0, "lower_limit": -3.99, "upper_limit": 3.99,
        }}
        found = process_findings(
            option(monitor_statistics=exact), need(min_capability_index=1.33)
        )
        self.assertEqual(found, [])

    def test_absent_monitor_data_is_an_action(self):
        found = process_findings(option(monitor_statistics=None), NEED)
        self.assertEqual(codes(found), ["monitor-data-absent"])

    def test_too_few_monitored_lots_is_an_action(self):
        found = process_findings(option(monitor_lots=1), NEED)
        self.assertEqual(codes(found), ["monitor-lot-count-short"])

    def test_short_production_horizon_is_an_action(self):
        found = process_findings(option(production_horizon_years=5.0), NEED)
        self.assertEqual(codes(found), ["supply-continuity-short"])

    def test_equal_horizons_raise_nothing(self):
        found = process_findings(option(production_horizon_years=8.0), NEED)
        self.assertEqual(found, [])

    def test_missing_line_certification_is_an_action(self):
        found = process_findings(option(line_certification=None), NEED)
        self.assertEqual(codes(found), ["line-certification-absent"])

    def test_several_defects_are_all_reported(self):
        found = process_findings(
            option(gate_length_um=0.5, monitor_lots=0, line_certification=None), NEED
        )
        self.assertEqual(
            codes(found),
            ["frequency-capability-short", "line-certification-absent",
             "monitor-lot-count-short"],
        )


class CategorizationAndScoreTests(unittest.TestCase):
    def test_no_findings_is_selectable(self):
        self.assertEqual(categorize_option([]), "selectable")

    def test_action_only_is_selectable_with_actions(self):
        self.assertEqual(
            categorize_option([{"code": "x", "severity": "action", "detail": ""}]),
            "selectable-with-actions",
        )

    def test_any_exclusion_dominates(self):
        self.assertEqual(
            categorize_option([
                {"code": "x", "severity": "action", "detail": ""},
                {"code": "y", "severity": "exclusion", "detail": ""},
            ]),
            "not-selectable",
        )

    def test_malformed_finding_rejected(self):
        with self.assertRaises(ValueError):
            categorize_option([{"code": "x"}])

    def test_generous_option_saturates_the_score(self):
        generous = option(
            gate_length_um=0.05, breakdown_voltage_v=100.0,
            production_horizon_years=40.0,
            monitor_statistics={"p": {
                "mean": 0.0, "sigma": 1.0, "lower_limit": -9.0, "upper_limit": 9.0,
            }},
        )
        self.assertAlmostEqual(option_score(generous, NEED), 1.0, places=9)

    def test_score_is_the_mean_of_its_four_components(self):
        expected = (
            1.0
            + 18.0 / (2.0 * 7.0 * 2.0)
            + 2.0 / (2.0 * 1.33)
            + 12.0 / (2.0 * 8.0)
        ) / 4.0
        self.assertAlmostEqual(option_score(OPTION, NEED), expected, places=9)

    def test_absent_monitor_data_costs_the_capability_component(self):
        with_data = option_score(OPTION, NEED)
        without_data = option_score(option(monitor_statistics=None), NEED)
        self.assertAlmostEqual(
            with_data - without_data, (2.0 / (2.0 * 1.33)) / 4.0, places=9
        )

    def test_marginal_option_scores_half(self):
        marginal = option(
            gate_length_um=0.3, breakdown_voltage_v=14.0, production_horizon_years=8.0,
            monitor_statistics={"p": {
                "mean": 0.0, "sigma": 1.0, "lower_limit": -3.99, "upper_limit": 3.99,
            }},
        )
        self.assertAlmostEqual(option_score(marginal, NEED), 0.5, places=6)

    def test_every_category_name_is_ordered(self):
        self.assertEqual(len(CATEGORY_ORDER), 3)


class RankingTests(unittest.TestCase):
    def test_selectable_outranks_action_and_excluded(self):
        records = [
            {"option_id": "C", "category": "not-selectable", "score": 1.0},
            {"option_id": "B", "category": "selectable-with-actions", "score": 1.0},
            {"option_id": "A", "category": "selectable", "score": 0.1},
        ]
        self.assertEqual(
            [r["option_id"] for r in rank_process_options(records)], ["A", "B", "C"]
        )

    def test_higher_score_wins_inside_a_category(self):
        records = [
            {"option_id": "LOW", "category": "selectable", "score": 0.4},
            {"option_id": "HIGH", "category": "selectable", "score": 0.9},
        ]
        self.assertEqual(
            [r["option_id"] for r in rank_process_options(records)], ["HIGH", "LOW"]
        )

    def test_tie_is_broken_by_option_id(self):
        records = [
            {"option_id": "ZZ", "category": "selectable", "score": 0.5},
            {"option_id": "AA", "category": "selectable", "score": 0.5},
        ]
        self.assertEqual(
            [r["option_id"] for r in rank_process_options(records)], ["AA", "ZZ"]
        )

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            rank_process_options([{"option_id": "A", "category": "maybe", "score": 1.0}])

    def test_missing_score_rejected(self):
        with self.assertRaises(ValueError):
            rank_process_options([{"option_id": "A", "category": "selectable"}])


class AssessmentTests(unittest.TestCase):
    def _spec(self, options=None, **overrides):
        spec = {"need": NEED, "options": options if options is not None else [OPTION]}
        spec.update(overrides)
        return spec

    def test_single_clean_option_is_recommended(self):
        result = assess_foundry_process_selection(self._spec())
        self.assertEqual(result["recommended"]["option_id"], "FAB-ALPHA/PH15")
        self.assertTrue(result["clean"])

    def test_counts_cover_every_category(self):
        result = assess_foundry_process_selection(self._spec(options=[
            OPTION,
            option(process_id="PH15B", monitor_lots=1),
            option(process_id="PH50", gate_length_um=0.5),
        ]))
        self.assertEqual(result["counts"]["selectable"], 1)
        self.assertEqual(result["counts"]["selectable-with-actions"], 1)
        self.assertEqual(result["counts"]["not-selectable"], 1)

    def test_shortlist_drops_the_excluded_option(self):
        result = assess_foundry_process_selection(self._spec(options=[
            OPTION, option(process_id="PH50", gate_length_um=0.5),
        ]))
        self.assertEqual(
            [r["option_id"] for r in result["shortlist"]], ["FAB-ALPHA/PH15"]
        )

    def test_open_actions_are_counted_on_the_shortlist(self):
        result = assess_foundry_process_selection(self._spec(options=[
            option(monitor_lots=1, line_certification=None),
        ]))
        self.assertEqual(result["open_actions"], 2)
        self.assertFalse(result["clean"])

    def test_all_excluded_gives_no_recommendation(self):
        result = assess_foundry_process_selection(self._spec(options=[
            option(gate_length_um=0.5),
        ]))
        self.assertIsNone(result["recommended"])
        self.assertFalse(result["clean"])

    def test_option_record_splits_exclusions_from_actions(self):
        record = assess_process_option(
            option(gate_length_um=0.5, line_certification=None), NEED
        )
        self.assertEqual(len(record["exclusions"]), 1)
        self.assertEqual(len(record["actions"]), 1)
        self.assertEqual(record["category"], "not-selectable")

    def test_duplicate_option_rejected(self):
        with self.assertRaises(ValueError):
            assess_foundry_process_selection(self._spec(options=[OPTION, OPTION]))

    def test_empty_option_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_foundry_process_selection(self._spec(options=[]))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["need"]
        with self.assertRaises(ValueError):
            assess_foundry_process_selection(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_foundry_process_selection(["need"])

    def test_same_process_at_two_foundries_is_two_options(self):
        result = assess_foundry_process_selection(self._spec(options=[
            OPTION, option(foundry_id="FAB-BETA"),
        ]))
        self.assertEqual(len(result["records"]), 2)

    def test_tolerance_is_small_enough_to_be_a_representation_guard(self):
        self.assertAlmostEqual(MARGIN_TOLERANCE, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main()
