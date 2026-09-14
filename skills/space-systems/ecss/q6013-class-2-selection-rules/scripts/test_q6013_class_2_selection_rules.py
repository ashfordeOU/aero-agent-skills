"""Contract tests for the clause 5.2.2.1 Class 2 baseline selection rule logic."""

import unittest

from q6013_class_2_selection_rules_logic import (
    BASELINE_RULES,
    CONTROLLED_PROCUREMENT_ROUTES,
    DEFAULT_RISK_CEILING,
    PROCUREMENT_ROUTES,
    RISK_TOLERANCE,
    UPRATING_CAP_K,
    VERDICTS,
    assess_class2_part_admissibility,
    evaluate_rules,
    mitigation_effective,
    residual_risk,
    temperature_shortfall,
    validate_mitigation,
    validate_temperature_case,
)

GOOD_TEMPERATURE = {
    "rated_min_c": -55.0,
    "rated_max_c": 125.0,
    "mission_min_c": -30.0,
    "mission_max_c": 85.0,
    "margin_k": 10.0,
}


def candidate(**overrides):
    """Return a candidate part meeting every baseline rule unless overridden."""
    part = {
        "reference": "U12-LDO",
        "authentic_provenance": True,
        "quality_system_certified": True,
        "procurement_route": "franchised-distributor",
        "flight_lot_homogeneous": True,
        "change_notification_agreed": True,
        "radiation_capability_declared": True,
        "temperature": dict(GOOD_TEMPERATURE),
    }
    part.update(overrides)
    return part


def mitigation(rule, measure=None, **overrides):
    """Return a mitigation record for one baseline rule."""
    record = {
        "rule": rule,
        "measure": measure if measure is not None else BASELINE_RULES[rule]["measure"],
        "reference": "PA-MIT-014",
    }
    record.update(overrides)
    return record


def hot_case(gap):
    """Return a temperature case whose hot end falls short by the given kelvin."""
    case = dict(GOOD_TEMPERATURE)
    case["rated_max_c"] = GOOD_TEMPERATURE["mission_max_c"] + GOOD_TEMPERATURE["margin_k"] - gap
    return case


class CatalogueTests(unittest.TestCase):
    def test_exactly_one_rule_is_a_hard_bar(self):
        bars = [rule for rule, spec in BASELINE_RULES.items() if not spec["mitigable"]]
        self.assertEqual(bars, ["authentic-provenance"])

    def test_every_mitigable_rule_names_its_measure(self):
        for rule, spec in BASELINE_RULES.items():
            if spec["mitigable"]:
                self.assertTrue(spec["measure"], rule)
                self.assertGreater(spec["residual"], 0.0)

    def test_hard_bar_carries_no_residual_share(self):
        self.assertAlmostEqual(BASELINE_RULES["authentic-provenance"]["residual"], 0.0, places=9)

    def test_controlled_routes_are_a_subset_of_the_declared_routes(self):
        for route in CONTROLLED_PROCUREMENT_ROUTES:
            self.assertIn(route, PROCUREMENT_ROUTES)

    def test_verdict_vocabulary_is_the_declared_one(self):
        self.assertEqual(
            VERDICTS, ("admissible", "admissible-with-mitigation", "not-admissible")
        )

    def test_tolerance_is_representation_sized(self):
        self.assertLess(RISK_TOLERANCE, 1e-6)


class TemperatureTests(unittest.TestCase):
    def test_enveloping_range_has_no_shortfall(self):
        self.assertAlmostEqual(temperature_shortfall(dict(GOOD_TEMPERATURE)), 0.0, places=9)

    def test_hot_shortfall_is_reported_in_kelvin(self):
        self.assertAlmostEqual(temperature_shortfall(hot_case(12.0)), 12.0, places=9)

    def test_cold_shortfall_is_reported_in_kelvin(self):
        case = dict(GOOD_TEMPERATURE)
        case["rated_min_c"] = GOOD_TEMPERATURE["mission_min_c"] - GOOD_TEMPERATURE["margin_k"] + 4.0
        self.assertAlmostEqual(temperature_shortfall(case), 4.0, places=9)

    def test_both_ends_short_add_up(self):
        case = hot_case(6.0)
        case["rated_min_c"] = GOOD_TEMPERATURE["mission_min_c"] - GOOD_TEMPERATURE["margin_k"] + 3.0
        self.assertAlmostEqual(temperature_shortfall(case), 9.0, places=9)

    def test_margin_is_applied_not_ignored(self):
        bare = dict(GOOD_TEMPERATURE)
        bare["rated_max_c"] = GOOD_TEMPERATURE["mission_max_c"]
        self.assertAlmostEqual(
            temperature_shortfall(bare), GOOD_TEMPERATURE["margin_k"], places=9
        )

    def test_inverted_rated_range_rejected(self):
        case = dict(GOOD_TEMPERATURE)
        case["rated_min_c"] = 200.0
        with self.assertRaises(ValueError):
            validate_temperature_case(case)

    def test_inverted_mission_range_rejected(self):
        case = dict(GOOD_TEMPERATURE)
        case["mission_max_c"] = -90.0
        with self.assertRaises(ValueError):
            validate_temperature_case(case)

    def test_negative_margin_rejected(self):
        case = dict(GOOD_TEMPERATURE)
        case["margin_k"] = -5.0
        with self.assertRaises(ValueError):
            validate_temperature_case(case)

    def test_missing_temperature_bound_rejected(self):
        case = dict(GOOD_TEMPERATURE)
        del case["rated_max_c"]
        with self.assertRaises(ValueError):
            validate_temperature_case(case)

    def test_non_numeric_bound_rejected(self):
        case = dict(GOOD_TEMPERATURE)
        case["rated_max_c"] = "125C"
        with self.assertRaises(ValueError):
            validate_temperature_case(case)


class RuleEvaluationTests(unittest.TestCase):
    def test_clean_part_meets_every_rule(self):
        outcome, shortfall = evaluate_rules(candidate())
        self.assertTrue(all(outcome.values()))
        self.assertAlmostEqual(shortfall, 0.0, places=9)

    def test_open_market_route_fails_the_procurement_rule(self):
        outcome, _ = evaluate_rules(candidate(procurement_route="open-market"))
        self.assertFalse(outcome["controlled-procurement-route"])

    def test_independent_distributor_is_not_a_controlled_route(self):
        outcome, _ = evaluate_rules(candidate(procurement_route="independent-distributor"))
        self.assertFalse(outcome["controlled-procurement-route"])

    def test_manufacturer_direct_is_a_controlled_route(self):
        outcome, _ = evaluate_rules(candidate(procurement_route="manufacturer-direct"))
        self.assertTrue(outcome["controlled-procurement-route"])

    def test_temperature_rule_fails_on_a_shortfall(self):
        outcome, shortfall = evaluate_rules(candidate(temperature=hot_case(8.0)))
        self.assertFalse(outcome["temperature-range-envelope"])
        self.assertAlmostEqual(shortfall, 8.0, places=9)

    def test_undeclared_fact_is_unknown_not_false(self):
        part = candidate()
        del part["radiation_capability_declared"]
        with self.assertRaises(ValueError):
            evaluate_rules(part)

    def test_non_boolean_fact_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_rules(candidate(flight_lot_homogeneous="probably"))

    def test_unknown_procurement_route_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_rules(candidate(procurement_route="a friend of the lab"))

    def test_blank_reference_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_rules(candidate(reference="  "))


class MitigationTests(unittest.TestCase):
    def test_recognised_measure_is_effective(self):
        self.assertTrue(
            mitigation_effective(
                "flight-lot-homogeneity", BASELINE_RULES["flight-lot-homogeneity"]["measure"]
            )
        )

    def test_wrong_measure_for_the_rule_is_not_effective(self):
        self.assertFalse(
            mitigation_effective("flight-lot-homogeneity", "manufacturer-audit-report")
        )

    def test_uprating_holds_exactly_at_the_cap(self):
        self.assertTrue(
            mitigation_effective(
                "temperature-range-envelope", "uprating-assessment", UPRATING_CAP_K
            )
        )

    def test_uprating_fails_beyond_the_cap(self):
        self.assertFalse(
            mitigation_effective(
                "temperature-range-envelope", "uprating-assessment", UPRATING_CAP_K + 0.5
            )
        )

    def test_mitigation_on_the_hard_bar_refused(self):
        with self.assertRaises(ValueError):
            validate_mitigation(mitigation("authentic-provenance", measure="a nice story"))

    def test_mitigation_on_an_unknown_rule_refused(self):
        record = mitigation("flight-lot-homogeneity")
        record["rule"] = "looks-fine-to-me"
        with self.assertRaises(ValueError):
            validate_mitigation(record)

    def test_blank_measure_refused(self):
        with self.assertRaises(ValueError):
            validate_mitigation(mitigation("flight-lot-homogeneity", measure="   "))

    def test_negative_shortfall_refused(self):
        with self.assertRaises(ValueError):
            mitigation_effective("temperature-range-envelope", "uprating-assessment", -1.0)


class ResidualRiskTests(unittest.TestCase):
    def test_no_mitigated_rule_leaves_no_risk(self):
        self.assertAlmostEqual(residual_risk([]), 0.0, places=9)

    def test_risk_is_the_sum_of_the_declared_shares(self):
        total = residual_risk(["flight-lot-homogeneity", "temperature-range-envelope"])
        self.assertAlmostEqual(total, 0.35, places=9)

    def test_duplicate_rule_rejected(self):
        with self.assertRaises(ValueError):
            residual_risk(["flight-lot-homogeneity", "flight-lot-homogeneity"])

    def test_unknown_rule_rejected(self):
        with self.assertRaises(ValueError):
            residual_risk(["good-vibes"])


class AssessmentTests(unittest.TestCase):
    def test_clean_part_is_admissible(self):
        result = assess_class2_part_admissibility({"candidate": candidate()})
        self.assertEqual(result["verdict"], "admissible")
        self.assertEqual(result["failed_rules"], ())
        self.assertEqual(result["findings"], [])

    def test_hard_bar_failure_is_never_admissible(self):
        result = assess_class2_part_admissibility(
            {"candidate": candidate(authentic_provenance=False)}
        )
        self.assertEqual(result["verdict"], "not-admissible")
        self.assertEqual(result["unmitigated_rules"], ("authentic-provenance",))

    def test_mitigated_failure_is_admissible_with_mitigation(self):
        result = assess_class2_part_admissibility(
            {
                "candidate": candidate(flight_lot_homogeneous=False),
                "mitigations": [mitigation("flight-lot-homogeneity")],
            }
        )
        self.assertEqual(result["verdict"], "admissible-with-mitigation")
        self.assertAlmostEqual(result["residual_risk"], 0.20, places=9)

    def test_failure_with_the_wrong_measure_is_not_carried(self):
        result = assess_class2_part_admissibility(
            {
                "candidate": candidate(flight_lot_homogeneous=False),
                "mitigations": [
                    mitigation("flight-lot-homogeneity", measure="periodic-construction-audit")
                ],
            }
        )
        self.assertEqual(result["verdict"], "not-admissible")

    def test_uprating_carries_a_shortfall_exactly_at_the_cap(self):
        result = assess_class2_part_admissibility(
            {
                "candidate": candidate(temperature=hot_case(UPRATING_CAP_K)),
                "mitigations": [mitigation("temperature-range-envelope")],
            }
        )
        self.assertAlmostEqual(result["temperature_shortfall_k"], UPRATING_CAP_K, places=9)
        self.assertEqual(result["verdict"], "admissible-with-mitigation")

    def test_uprating_does_not_carry_a_shortfall_past_the_cap(self):
        result = assess_class2_part_admissibility(
            {
                "candidate": candidate(temperature=hot_case(UPRATING_CAP_K + 2.0)),
                "mitigations": [mitigation("temperature-range-envelope")],
            }
        )
        self.assertEqual(result["verdict"], "not-admissible")

    def test_stacked_mitigations_breach_the_risk_ceiling(self):
        result = assess_class2_part_admissibility(
            {
                "candidate": candidate(
                    quality_system_certified=False,
                    procurement_route="open-market",
                    flight_lot_homogeneous=False,
                ),
                "mitigations": [
                    mitigation("manufacturer-quality-system"),
                    mitigation("controlled-procurement-route"),
                    mitigation("flight-lot-homogeneity"),
                ],
            }
        )
        self.assertAlmostEqual(result["residual_risk"], 0.65, places=9)
        self.assertEqual(result["verdict"], "not-admissible")

    def test_residual_risk_exactly_at_the_ceiling_is_accepted(self):
        result = assess_class2_part_admissibility(
            {
                "candidate": candidate(
                    flight_lot_homogeneous=False, temperature=hot_case(5.0)
                ),
                "mitigations": [
                    mitigation("flight-lot-homogeneity"),
                    mitigation("temperature-range-envelope"),
                ],
            }
        )
        self.assertAlmostEqual(result["residual_risk"], DEFAULT_RISK_CEILING, places=9)
        self.assertEqual(result["verdict"], "admissible-with-mitigation")

    def test_mitigation_attached_to_a_met_rule_is_reported_not_counted(self):
        result = assess_class2_part_admissibility(
            {
                "candidate": candidate(),
                "mitigations": [mitigation("flight-lot-homogeneity")],
            }
        )
        self.assertEqual(result["unused_mitigations"], ("flight-lot-homogeneity",))
        self.assertAlmostEqual(result["residual_risk"], 0.0, places=9)
        self.assertEqual(result["verdict"], "admissible")

    def test_findings_are_ordered_worst_first(self):
        result = assess_class2_part_admissibility(
            {
                "candidate": candidate(
                    flight_lot_homogeneous=False, change_notification_agreed=False
                ),
                "mitigations": [mitigation("flight-lot-homogeneity")],
            }
        )
        self.assertEqual(result["findings"][0]["severity"], 0)
        self.assertEqual(result["findings"][0]["rule"], "change-notification-agreement")

    def test_two_mitigations_on_one_rule_rejected(self):
        with self.assertRaises(ValueError):
            assess_class2_part_admissibility(
                {
                    "candidate": candidate(flight_lot_homogeneous=False),
                    "mitigations": [
                        mitigation("flight-lot-homogeneity"),
                        mitigation("flight-lot-homogeneity"),
                    ],
                }
            )

    def test_missing_candidate_rejected(self):
        with self.assertRaises(ValueError):
            assess_class2_part_admissibility({"mitigations": []})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_class2_part_admissibility(["candidate"])

    def test_risk_ceiling_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            assess_class2_part_admissibility(
                {"candidate": candidate(), "risk_ceiling": 2.0}
            )

    def test_mitigations_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            assess_class2_part_admissibility(
                {"candidate": candidate(), "mitigations": {"rule": "x"}}
            )


if __name__ == "__main__":
    unittest.main()
