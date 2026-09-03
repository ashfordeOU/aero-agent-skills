"""Contract test for the equivalent-level-of-safety logic module.

stdlib unittest, offline and deterministic (34 methods). Asserts the worked
example anchors from the wave-26 leaf spec against real module outputs:
the 25.1309 catastrophic margin 5.0 with coverage 2/3 going CONDITIONAL
then PASS when monitoring is added, the 3e-9 margin FAIL, the qualitative
25.671 PASS, table lookups, margin math, margin in dB, compensation rules
per measure type, coverage math, the override path and ValueError
rejections.

Run: python3 scripts/test_equivalent_level_of_safety.py
"""

import math
import unittest

from equivalent_level_of_safety_logic import (
    EXPECTED_MEASURES,
    INTENT_TABLE,
    PROBABILITY_TARGETS,
    compensation_coverage,
    elos_verdict,
    finding_summary,
    intent_for,
    margin_db,
    measure_type,
    safety_margin,
)

WORKED_MEASURES = ["redundant-lane-monitoring", "flight-crew-procedure"]
WORKED_MEASURES_FULL = WORKED_MEASURES + ["failure-monitoring"]
QUAL_CONTROL_MEASURES = ["redundant-actuation", "jam-detection-monitoring"]


class IntentTableTests(unittest.TestCase):
    """Regulation intent table lookups and the override path."""

    def test_intent_1309_quantitative_targets_keyed_by_severity(self):
        intent = intent_for("25.1309", "catastrophic")
        self.assertTrue(intent["quantitative"])
        self.assertEqual(intent["target_prob"], 1e-9)
        self.assertEqual(intent_for("25.1309", "hazardous")["target_prob"], 1e-7)
        self.assertEqual(intent_for("25.1309", "major")["target_prob"], 1e-5)

    def test_intent_231309_shares_target_table_shape(self):
        intent = intent_for("23.1309", "catastrophic")
        self.assertTrue(intent["quantitative"])
        self.assertEqual(intent["target_prob"], 1e-9)
        self.assertEqual(PROBABILITY_TARGETS["catastrophic"], 1e-9)

    def test_intent_671_and_683_qualitative_hazardous(self):
        for paragraph in ("25.671", "25.683"):
            intent = intent_for(paragraph, "hazardous")
            self.assertFalse(intent["quantitative"])
            self.assertIsNone(intent["target_prob"])
            self.assertEqual(intent["intent_severity"], "hazardous")

    def test_intent_unknown_paragraph_without_overrides_raises(self):
        with self.assertRaises(ValueError):
            intent_for("25.1301", "major")

    def test_intent_override_path_for_unknown_paragraph(self):
        intent = intent_for(
            "25.1301", "minor",
            intent_severity_override="major",
            intent_description_override="wiring separation keeps a fire "
            "from reaching the flight deck",
        )
        self.assertFalse(intent["quantitative"])
        self.assertEqual(intent["intent_severity"], "major")
        self.assertIn("wiring separation", intent["intent_text"])
        defaulted = intent_for(
            "25.1301", "minor",
            intent_description_override="maintenance access must not "
            "degrade a protected zone",
        )
        self.assertEqual(defaulted["intent_severity"], "major")

    def test_intent_unknown_severity_and_targetless_severity_raise(self):
        with self.assertRaises(ValueError):
            intent_for("25.1309", "very-bad")
        with self.assertRaises(ValueError):
            intent_for("25.1309", "minor")  # no probability target for minor

    def test_intent_table_constants_shape(self):
        self.assertIn("25.1309", INTENT_TABLE)
        self.assertIn("25.671", INTENT_TABLE)
        self.assertEqual(EXPECTED_MEASURES[("catastrophic", True)], 3)
        self.assertEqual(EXPECTED_MEASURES[("hazardous", False)], 1)


class MarginMathTests(unittest.TestCase):
    """Safety margin ratio, decibel conversion and rejections."""

    def test_safety_margin_anchor_25_1309_exact(self):
        self.assertEqual(safety_margin(1e-9, 2e-10), 5.0)
        self.assertEqual(safety_margin(1e-9, 1e-9), 1.0)

    def test_safety_margin_below_target_is_one_third(self):
        self.assertAlmostEqual(safety_margin(1e-9, 3e-9), 1.0 / 3.0, places=9)

    def test_safety_margin_nonpositive_raises(self):
        for target, achieved in ((1e-9, 0.0), (1e-9, -1e-10),
                                 (0.0, 1e-10), (-1e-9, 1e-10)):
            with self.assertRaises(ValueError):
                safety_margin(target, achieved)

    def test_safety_margin_nonfinite_raises(self):
        with self.assertRaises(ValueError):
            safety_margin(float("nan"), 1e-10)
        with self.assertRaises(ValueError):
            safety_margin(1e-9, float("inf"))

    def test_margin_db_anchor_and_decade(self):
        value = margin_db(1e-9, 2e-10)
        self.assertAlmostEqual(value, 10.0 * math.log10(5.0), places=9)
        self.assertAlmostEqual(value, 6.9897, places=3)
        self.assertAlmostEqual(margin_db(1e-9, 1e-11), 20.0, places=9)

    def test_margin_db_round_trip_identity(self):
        decibels = margin_db(1e-9, 2e-10)
        self.assertAlmostEqual(10.0 ** (decibels / 10.0),
                               safety_margin(1e-9, 2e-10), places=9)


class MeasureClassificationTests(unittest.TestCase):
    """Measure name to type classification with documented precedence."""

    def test_redundancy_precedence_over_monitoring(self):
        # First keyword match wins: redundant-lane-monitoring is redundancy.
        self.assertEqual(measure_type("redundant-lane-monitoring"), "redundancy")
        self.assertEqual(measure_type("redundant-actuation"), "redundancy")

    def test_monitoring_names_classify_as_monitoring(self):
        self.assertEqual(measure_type("failure-monitoring"), "monitoring")
        self.assertEqual(measure_type("jam-detection-monitoring"), "monitoring")

    def test_canonical_measure_names_and_unrecognized(self):
        self.assertEqual(measure_type("redundancy"), "redundancy")
        self.assertEqual(measure_type("monitoring"), "monitoring")
        self.assertEqual(measure_type("operating limitation"), "operating-limitation")
        self.assertEqual(measure_type("flight crew procedure"), "flight-crew-procedure")
        self.assertEqual(measure_type("maintenance action"), "maintenance-action")
        self.assertEqual(measure_type("inspection interval"), "inspection-interval")
        self.assertIsNone(measure_type("design change"))
        self.assertIsNone(measure_type(""))


class CompensationRuleTests(unittest.TestCase):
    """Per measure type acceptance rules from MEASURE_RULES."""

    def test_redundancy_accepted_for_catastrophic_quantitative(self):
        coverage, accepted, _gaps = compensation_coverage(
            ["redundant-actuation"], "25.1309", "catastrophic")
        self.assertIn("redundancy", accepted)
        self.assertAlmostEqual(coverage, 1.0 / 3.0, places=6)

    def test_monitoring_requires_redundancy_or_limitation(self):
        _c, accepted, gaps = compensation_coverage(
            ["failure-monitoring"], "25.1309", "catastrophic")
        self.assertNotIn("monitoring", accepted)
        self.assertIn("monitoring", gaps)
        _c, accepted, _g = compensation_coverage(
            ["redundant-actuation", "failure-monitoring"], "25.1309",
            "catastrophic")
        self.assertIn("monitoring", accepted)

    def test_operating_limitation_requires_crew_qualitative_only(self):
        _c, accepted, _g = compensation_coverage(
            ["operating-limitation"], "25.671", "hazardous")
        self.assertNotIn("operating-limitation", accepted)
        _c, accepted, _g = compensation_coverage(
            ["operating-limitation", "flight-crew-procedure"], "25.671",
            "hazardous")
        self.assertIn("operating-limitation", accepted)

    def test_crew_procedure_requires_redundancy(self):
        # Worked example anchor: paired with redundancy it is accepted.
        _c, accepted, _g = compensation_coverage(
            ["flight-crew-procedure"], "25.1309", "catastrophic")
        self.assertNotIn("flight-crew-procedure", accepted)
        _c, accepted, _g = compensation_coverage(
            WORKED_MEASURES, "25.1309", "catastrophic")
        self.assertIn("flight-crew-procedure", accepted)

    def test_maintenance_restore_and_inspection_fatigue_rules(self):
        _c, accepted, _g = compensation_coverage(
            ["maintenance action"], "25.1309", "catastrophic")
        self.assertNotIn("maintenance-action", accepted)
        _c, accepted, _g = compensation_coverage(
            ["maintenance-restore-before-next-flight"], "25.1309",
            "catastrophic")
        self.assertIn("maintenance-action", accepted)
        _c, accepted, _g = compensation_coverage(
            ["inspection-interval"], "25.1309", "catastrophic")
        self.assertNotIn("inspection-interval", accepted)
        _c, accepted, _g = compensation_coverage(
            ["inspection-interval"], "25.571", "hazardous",
            intent_description_override="damage tolerance inspections "
            "keep crack growth within limits")
        self.assertIn("inspection-interval", accepted)


class WorkedExampleTests(unittest.TestCase):
    """The worked example anchors from the leaf spec, verbatim inputs."""

    def test_workdexample1_conditional_anchor(self):
        verdict = elos_verdict("25.1309", "catastrophic", 2e-10, WORKED_MEASURES)
        for key in ("margin", "margin_db", "coverage", "verdict", "reasons",
                    "accepted", "gaps"):
            self.assertIn(key, verdict)
        self.assertEqual(verdict["margin"], 5.0)
        self.assertAlmostEqual(verdict["coverage"], 2.0 / 3.0, places=6)
        self.assertEqual(verdict["gaps"], ["monitoring"])
        self.assertEqual(verdict["accepted"],
                         ["redundancy", "flight-crew-procedure"])
        self.assertEqual(verdict["verdict"], "CONDITIONAL")
        self.assertTrue(any("monitoring" in reason
                            for reason in verdict["reasons"]))

    def test_workdexample1_add_monitoring_passes(self):
        verdict = elos_verdict("25.1309", "catastrophic", 2e-10,
                               WORKED_MEASURES_FULL)
        self.assertEqual(verdict["coverage"], 1.0)
        self.assertEqual(verdict["verdict"], "PASS")

    def test_workdexample2_margin_below_target_fails(self):
        verdict = elos_verdict("25.1309", "catastrophic", 3e-9,
                               WORKED_MEASURES_FULL)
        self.assertAlmostEqual(verdict["margin"], 1.0 / 3.0, places=6)
        self.assertEqual(verdict["verdict"], "FAIL")
        self.assertTrue(any("margin" in reason
                            for reason in verdict["reasons"]))

    def test_workdexample3_qualitative_control_system_passes(self):
        verdict = elos_verdict("25.671", "hazardous", None,
                               QUAL_CONTROL_MEASURES)
        self.assertEqual(verdict["coverage"], 1.0)
        self.assertEqual(verdict["verdict"], "PASS")
        self.assertIsNone(verdict["margin"])
        self.assertIsNone(verdict["margin_db"])


class VerdictBranchTests(unittest.TestCase):
    """PASS, CONDITIONAL and FAIL branch behavior."""

    def test_quantitative_major_item_can_pass(self):
        verdict = elos_verdict("25.1309", "major", 1e-6,
                               ["redundant-lane-monitoring", "failure-monitoring"])
        self.assertAlmostEqual(verdict["margin"], 10.0, places=6)
        self.assertEqual(verdict["verdict"], "PASS")

    def test_quantitative_hazardous_conditional_when_measure_missing(self):
        verdict = elos_verdict("25.1309", "hazardous", 1e-8,
                               ["redundant-actuation"])
        self.assertAlmostEqual(verdict["margin"], 10.0, places=6)
        self.assertEqual(verdict["verdict"], "CONDITIONAL")
        self.assertIn("monitoring", verdict["gaps"])

    def test_empty_measures_fail_quantitative_and_qualitative(self):
        quant = elos_verdict("25.1309", "catastrophic", 2e-10, [])
        self.assertEqual(quant["coverage"], 0.0)
        self.assertEqual(quant["verdict"], "FAIL")
        qual = elos_verdict("25.671", "hazardous", None, [])
        self.assertEqual(qual["coverage"], 0.0)
        self.assertEqual(qual["verdict"], "FAIL")

    def test_coverage_capped_at_one(self):
        coverage, accepted, gaps = compensation_coverage(
            QUAL_CONTROL_MEASURES + ["operating-limitation",
                                     "flight-crew-procedure"],
            "25.671", "hazardous")
        self.assertEqual(coverage, 1.0)
        self.assertEqual(len(accepted), 4)
        self.assertEqual(gaps, [])

    def test_qualitative_primary_safety_gap_is_conditional(self):
        # Coverage 1.0 from extra measures but the canonical monitoring
        # measure is missing, a primary safety function gap: no PASS.
        verdict = elos_verdict("25.671", "catastrophic", None,
                               ["redundant-actuation", "operating-limitation",
                                "flight-crew-procedure"])
        self.assertEqual(verdict["coverage"], 1.0)
        self.assertEqual(verdict["verdict"], "CONDITIONAL")
        self.assertIn("monitoring", verdict["gaps"])
        self.assertTrue(any("primary safety function" in reason
                            for reason in verdict["reasons"]))

    def test_catastrophic_quantitative_fails_on_margin_regardless(self):
        verdict = elos_verdict("25.1309", "catastrophic", 5e-9,
                               WORKED_MEASURES_FULL)
        self.assertAlmostEqual(verdict["coverage"], 1.0, places=6)
        self.assertEqual(verdict["verdict"], "FAIL")


class ValueErrorAndSummaryTests(unittest.TestCase):
    """Non-physical input rejection and the finding summary."""

    def test_verdict_nonphysical_inputs_raise(self):
        with self.assertRaises(ValueError):
            elos_verdict("25.1309", "very-bad", 2e-10, WORKED_MEASURES)
        with self.assertRaises(ValueError):
            elos_verdict("25.1309", "catastrophic", 0.0, WORKED_MEASURES)
        with self.assertRaises(ValueError):
            elos_verdict("25.1309", "catastrophic", -1e-10, WORKED_MEASURES)
        with self.assertRaises(ValueError):
            elos_verdict("25.1309", "catastrophic", float("nan"),
                         WORKED_MEASURES)
        with self.assertRaises(ValueError):
            elos_verdict("25.1309", "catastrophic", None, WORKED_MEASURES)

    def test_finding_summary_quantitative_pass_anchor(self):
        verdict = elos_verdict("25.1309", "catastrophic", 2e-10,
                               WORKED_MEASURES_FULL)
        item = {"paragraph": "25.1309", "severity": "catastrophic"}
        summary = finding_summary(item, verdict)
        self.assertIn("25.1309", summary)
        self.assertIn("5.0", summary)
        self.assertIn("coverage 1.0", summary)
        self.assertIn("verdict PASS (finding recommended)", summary)

    def test_finding_summary_qualitative_anchor(self):
        verdict = elos_verdict("25.671", "hazardous", None,
                               QUAL_CONTROL_MEASURES)
        item = {"paragraph": "25.671", "severity": "hazardous"}
        summary = finding_summary(item, verdict)
        self.assertIn("25.671", summary)
        self.assertIn("qualitative rule, no numeric margin", summary)
        self.assertIn("finding recommended", summary)


if __name__ == "__main__":
    unittest.main()
