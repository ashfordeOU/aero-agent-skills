"""Contract test for the q40-02-step3-decide-act leaf (stdlib unittest)."""

import unittest

from q40_02_step3_decide_act_logic import (
    DEFAULT_ACCEPTANCE_FLOOR_INDEX,
    PRECEDENCE_ORDINAL,
    REDUCTION_PRECEDENCE,
    assess_step3_decide_act,
    credited_measures,
    effectiveness_findings,
    likelihood_band,
    precedence_findings,
    residual_probability,
    residual_severity,
    risk_index,
    validate_measure,
)


def measure(mid="RM-1", precedence="eliminate-or-minimize-by-design", **kw):
    record = {
        "id": mid,
        "precedence": precedence,
        "verified": True,
        "reduction_effectiveness": 0.9,
        "severity_steps_reduced": 0,
        "higher_orders_justified_unavailable": [],
    }
    record.update(kw)
    return record


def hazard(**kw):
    record = {
        "id": "HZ-7",
        "severity": "critical",
        "base_probability": 1.0e-2,
    }
    record.update(kw)
    return record


class TestValidateMeasure(unittest.TestCase):
    def test_normalizes_defaults(self):
        norm = validate_measure({"id": "RM-9", "precedence": "safety-device"})
        self.assertFalse(norm["verified"])
        self.assertEqual(norm["severity_steps_reduced"], 0)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_measure(["RM-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_measure(measure(""))

    def test_unknown_precedence_raises(self):
        with self.assertRaises(ValueError):
            validate_measure(measure(precedence="hope"))

    def test_effectiveness_above_one_raises(self):
        with self.assertRaises(ValueError):
            validate_measure(measure(reduction_effectiveness=1.4))

    def test_negative_severity_steps_raise(self):
        with self.assertRaises(ValueError):
            validate_measure(measure(severity_steps_reduced=-1))

    def test_non_boolean_verified_raises(self):
        with self.assertRaises(ValueError):
            validate_measure(measure(verified="yes"))

    def test_unknown_justified_order_raises(self):
        with self.assertRaises(ValueError):
            validate_measure(
                measure(higher_orders_justified_unavailable=["wishful-thinking"])
            )


class TestPrecedence(unittest.TestCase):
    def test_precedence_is_ordered_strongest_first(self):
        self.assertEqual(REDUCTION_PRECEDENCE[0], "eliminate-or-minimize-by-design")
        self.assertLess(
            PRECEDENCE_ORDINAL["safety-device"],
            PRECEDENCE_ORDINAL["procedure-or-training"],
        )

    def test_strongest_order_needs_no_justification(self):
        self.assertEqual(precedence_findings(measure()), [])

    def test_procedure_without_justification_flags_three_orders(self):
        findings = precedence_findings(measure(precedence="procedure-or-training"))
        self.assertEqual(len(findings), 3)
        self.assertIn(
            "higher-order-not-justified:eliminate-or-minimize-by-design", findings
        )

    def test_justified_orders_clear_the_finding(self):
        findings = precedence_findings(
            measure(
                precedence="procedure-or-training",
                higher_orders_justified_unavailable=list(REDUCTION_PRECEDENCE[:3]),
            )
        )
        self.assertEqual(findings, [])

    def test_partial_justification_leaves_the_remainder(self):
        findings = precedence_findings(
            measure(
                precedence="warning-device",
                higher_orders_justified_unavailable=["safety-device"],
            )
        )
        self.assertEqual(
            findings, ["higher-order-not-justified:eliminate-or-minimize-by-design"]
        )


class TestEffectiveness(unittest.TestCase):
    def test_verified_effective_measure_is_clean(self):
        self.assertEqual(effectiveness_findings(measure()), [])

    def test_unverified_measure_is_a_finding(self):
        self.assertIn(
            "measure-effectiveness-not-verified",
            effectiveness_findings(measure(verified=False)),
        )

    def test_verified_but_useless_measure_is_a_finding(self):
        self.assertIn(
            "verified-measure-reduces-nothing",
            effectiveness_findings(measure(reduction_effectiveness=0.0)),
        )

    def test_only_verified_measures_are_credited(self):
        measures = [measure("RM-1"), measure("RM-2", verified=False)]
        self.assertEqual([m["id"] for m in credited_measures(measures)], ["RM-1"])

    def test_duplicate_measure_id_raises(self):
        with self.assertRaises(ValueError):
            credited_measures([measure("RM-1"), measure("RM-1")])

    def test_non_list_measures_raise(self):
        with self.assertRaises(ValueError):
            credited_measures(measure())


class TestResidual(unittest.TestCase):
    def test_single_measure_reduces_the_probability(self):
        value = residual_probability(1.0e-2, [measure(reduction_effectiveness=0.9)])
        self.assertAlmostEqual(value, 1.0e-3, places=12)

    def test_measures_compound(self):
        measures = [
            measure("RM-1", reduction_effectiveness=0.5),
            measure("RM-2", precedence="safety-device", reduction_effectiveness=0.5,
                    higher_orders_justified_unavailable=[
                        "eliminate-or-minimize-by-design"]),
        ]
        self.assertAlmostEqual(residual_probability(1.0e-2, measures), 2.5e-3, places=12)

    def test_unverified_measure_does_not_reduce(self):
        value = residual_probability(1.0e-2, [measure(verified=False)])
        self.assertAlmostEqual(value, 1.0e-2, places=12)

    def test_reduced_probability_moves_the_band(self):
        value = residual_probability(1.0e-2, [measure(reduction_effectiveness=0.9)])
        self.assertEqual(likelihood_band(value), "occasional")

    def test_severity_step_lowers_the_category(self):
        self.assertEqual(
            residual_severity("catastrophic", [measure(severity_steps_reduced=1)]),
            "critical",
        )

    def test_severity_cannot_fall_past_the_mildest(self):
        self.assertEqual(
            residual_severity("major", [measure(severity_steps_reduced=9)]), "minor"
        )

    def test_unverified_measure_does_not_lower_severity(self):
        self.assertEqual(
            residual_severity(
                "catastrophic", [measure(verified=False, severity_steps_reduced=2)]
            ),
            "catastrophic",
        )

    def test_unknown_base_severity_raises(self):
        with self.assertRaises(ValueError):
            residual_severity("awkward", [measure()])


class TestAssessment(unittest.TestCase):
    def test_strong_verified_measure_reaches_the_floor(self):
        result = assess_step3_decide_act(
            hazard(), [measure(reduction_effectiveness=0.9999, severity_steps_reduced=1)]
        )
        self.assertGreaterEqual(
            result["residual_risk_index"], DEFAULT_ACCEPTANCE_FLOOR_INDEX
        )
        self.assertTrue(result["acceptable"])

    def test_residual_below_the_floor_is_a_finding(self):
        result = assess_step3_decide_act(
            hazard(severity="catastrophic"),
            [measure(reduction_effectiveness=0.1)],
        )
        self.assertIn(
            "residual-risk-index-below-acceptance-floor", result["findings"]
        )
        self.assertFalse(result["acceptable"])

    def test_precedence_finding_reaches_the_verdict(self):
        result = assess_step3_decide_act(
            hazard(), [measure(precedence="procedure-or-training",
                               reduction_effectiveness=0.9999,
                               severity_steps_reduced=1)]
        )
        self.assertFalse(result["acceptable"])
        self.assertTrue(
            any("higher-order-not-justified" in f for f in result["findings"])
        )

    def test_initial_index_is_reported_alongside_residual(self):
        result = assess_step3_decide_act(
            hazard(), [measure(reduction_effectiveness=0.9)]
        )
        self.assertEqual(result["initial_risk_index"], risk_index("critical", "probable"))
        self.assertGreater(
            result["residual_risk_index"], result["initial_risk_index"]
        )

    def test_residual_probability_is_reported(self):
        result = assess_step3_decide_act(
            hazard(), [measure(reduction_effectiveness=0.9)]
        )
        self.assertAlmostEqual(result["residual_probability"], 1.0e-3, places=12)

    def test_empty_measure_list_raises(self):
        with self.assertRaises(ValueError):
            assess_step3_decide_act(hazard(), [])

    def test_unknown_hazard_severity_raises(self):
        with self.assertRaises(ValueError):
            assess_step3_decide_act(hazard(severity="mild"), [measure()])

    def test_floor_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            assess_step3_decide_act(hazard(), [measure()], floor_index=99)

    def test_non_mapping_hazard_raises(self):
        with self.assertRaises(ValueError):
            assess_step3_decide_act(["HZ-7"], [measure()])


if __name__ == "__main__":
    unittest.main()
