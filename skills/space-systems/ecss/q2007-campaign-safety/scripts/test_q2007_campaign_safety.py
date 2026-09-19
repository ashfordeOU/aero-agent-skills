"""Contract tests for the clause 5.9.4 test-campaign safety logic."""

import unittest

from q2007_campaign_safety_logic import (
    CONTROLLED_LOCATIONS,
    DESIGN_INPUTS,
    HAZARD_FAMILIES,
    assess_campaign_safety,
    family_rule,
    identify_hazards,
    is_hazardous,
    location_findings,
    normalise_identifier,
    reconcile_questionnaire,
    safety_design_inputs,
    validate_declaration,
    validate_questionnaire,
)


def entry(ref, family, value, kind="item", location="test-hall"):
    return {"id": ref, "family": family, "value": value, "kind": kind, "location": location}


def topic(name, answer="yes", detail="handled by the customer safety officer"):
    return {"topic": name, "answer": answer, "detail": detail}


class NormaliseTests(unittest.TestCase):
    def test_trims_and_lowercases(self):
        self.assertEqual(normalise_identifier("  Pyrotechnic ", "x"), "pyrotechnic")

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier("   ", "x")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier(7, "x")


class FamilyRuleTests(unittest.TestCase):
    def test_known_family_returns_metric_threshold_unit(self):
        self.assertEqual(family_rule("lifting"), ("mass_kg", 25.0, "kg"))

    def test_inert_family_has_no_threshold(self):
        self.assertIsNone(family_rule("inert")[1])

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            family_rule("space-magic")

    def test_every_family_has_design_inputs_entry(self):
        self.assertEqual(sorted(HAZARD_FAMILIES), sorted(DESIGN_INPUTS))


class ThresholdTests(unittest.TestCase):
    def test_any_declared_pyrotechnic_is_hazardous(self):
        self.assertTrue(is_hazardous("pyrotechnic", 1.0))

    def test_tiny_propellant_mass_is_still_hazardous(self):
        self.assertTrue(is_hazardous("propellant", 0.001))

    def test_below_threshold_lift_is_not_hazardous(self):
        self.assertFalse(is_hazardous("lifting", 12.0))

    def test_value_exactly_on_the_threshold_is_hazardous(self):
        metric, threshold, unit = family_rule("high-voltage")
        self.assertEqual(metric, "voltage_v")
        self.assertEqual(unit, "V")
        self.assertTrue(is_hazardous("high-voltage", threshold))

    def test_inert_family_never_hazardous(self):
        self.assertFalse(is_hazardous("inert", 1000.0))

    def test_zero_value_rejected(self):
        with self.assertRaises(ValueError):
            is_hazardous("lifting", 0.0)

    def test_boolean_value_rejected(self):
        with self.assertRaises(ValueError):
            is_hazardous("lifting", True)


class DeclarationTests(unittest.TestCase):
    def test_entries_keyed_by_identifier(self):
        entries = validate_declaration([entry("pv-1", "pressurised-system", 200.0)])
        self.assertIn("pv-1", entries)
        self.assertTrue(entries["pv-1"]["hazardous"])

    def test_duplicate_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_declaration([
                entry("pv-1", "pressurised-system", 200.0),
                entry("PV-1", "lifting", 900.0),
            ])

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_declaration([entry("a", "lifting", 900.0, kind="activity")])

    def test_empty_declaration_rejected(self):
        with self.assertRaises(ValueError):
            validate_declaration([])

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            validate_declaration(["pv-1"])

    def test_missing_location_is_allowed(self):
        entries = validate_declaration([entry("a", "lifting", 900.0, location=None)])
        self.assertIsNone(entries["a"]["location"])


class GroupingTests(unittest.TestCase):
    def test_hazardous_and_below_threshold_are_separated(self):
        entries = validate_declaration([
            entry("a", "lifting", 900.0),
            entry("b", "lifting", 4.0),
        ])
        grouped = identify_hazards(entries)
        self.assertEqual(grouped["hazardous"]["lifting"], ["a"])
        self.assertEqual(grouped["below_threshold"]["lifting"], ["b"])

    def test_empty_mapping_rejected(self):
        with self.assertRaises(ValueError):
            identify_hazards({})


class QuestionnaireTests(unittest.TestCase):
    def test_normalises_topic_and_answer(self):
        topics = validate_questionnaire([{"topic": " Laser ", "answer": "YES", "detail": "d"}])
        self.assertEqual(topics["laser"]["answer"], "yes")

    def test_blank_detail_becomes_none(self):
        topics = validate_questionnaire([topic("laser", detail="   ")])
        self.assertIsNone(topics["laser"]["detail"])

    def test_unknown_topic_rejected(self):
        with self.assertRaises(ValueError):
            validate_questionnaire([topic("space-magic")])

    def test_duplicate_topic_rejected(self):
        with self.assertRaises(ValueError):
            validate_questionnaire([topic("laser"), topic("laser")])

    def test_unknown_answer_rejected(self):
        with self.assertRaises(ValueError):
            validate_questionnaire([topic("laser", answer="maybe")])

    def test_absent_response_is_an_empty_mapping(self):
        self.assertEqual(validate_questionnaire(None), {})


class ReconciliationTests(unittest.TestCase):
    def test_hazard_without_a_topic_blocks(self):
        findings = reconcile_questionnaire(["laser"], {})
        self.assertEqual(findings[0]["code"], "questionnaire-topic-missing")

    def test_topic_answering_no_contradicts_the_declaration(self):
        q = validate_questionnaire([topic("laser", answer="no", detail=None)])
        findings = reconcile_questionnaire(["laser"], q)
        self.assertEqual(findings[0]["code"], "questionnaire-contradicts-declaration")

    def test_yes_without_detail_blocks(self):
        q = validate_questionnaire([topic("laser", detail=None)])
        findings = reconcile_questionnaire(["laser"], q)
        self.assertEqual(findings[0]["code"], "questionnaire-detail-missing")

    def test_topic_confirmed_but_never_declared_blocks(self):
        q = validate_questionnaire([topic("propellant")])
        findings = reconcile_questionnaire([], q)
        self.assertEqual(
            findings[0]["code"], "declaration-missing-for-questionnaire-topic"
        )

    def test_matched_hazard_and_topic_produce_no_finding(self):
        q = validate_questionnaire([topic("laser")])
        self.assertEqual(reconcile_questionnaire(["laser"], q), [])

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_questionnaire(["space-magic"], {})


class LocationTests(unittest.TestCase):
    def test_hazardous_entry_outside_a_controlled_area_blocks(self):
        entries = validate_declaration([entry("a", "propellant", 5.0, location="car-park")])
        findings = location_findings(entries)
        self.assertEqual(findings[0]["code"], "hazardous-entry-outside-controlled-area")
        self.assertEqual(findings[0]["severity"], "blocking")

    def test_undeclared_location_is_advisory_only(self):
        entries = validate_declaration([entry("a", "propellant", 5.0, location=None)])
        findings = location_findings(entries)
        self.assertEqual(findings[0]["severity"], "advisory")

    def test_below_threshold_entry_is_not_location_graded(self):
        entries = validate_declaration([entry("a", "lifting", 2.0, location="car-park")])
        self.assertEqual(location_findings(entries), [])

    def test_every_controlled_location_is_accepted(self):
        for place in CONTROLLED_LOCATIONS:
            entries = validate_declaration([entry("a", "propellant", 5.0, location=place)])
            self.assertEqual(location_findings(entries), [])


class DesignInputTests(unittest.TestCase):
    def test_inputs_are_the_sorted_union(self):
        inputs = safety_design_inputs(["laser", "cryogenic"])
        self.assertEqual(list(inputs), sorted(set(inputs)))
        self.assertIn("hazardous-operation-procedure", inputs)

    def test_no_hazard_family_owes_nothing(self):
        self.assertEqual(safety_design_inputs([]), ())

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            safety_design_inputs(["space-magic"])


class AssessmentTests(unittest.TestCase):
    def test_clean_campaign_is_ready_with_safety_actions(self):
        result = assess_campaign_safety({
            "declaration": [
                entry("pv-1", "pressurised-system", 250.0),
                entry("lift-1", "lifting", 800.0, kind="operation"),
                entry("box-1", "inert", 3.0),
            ],
            "questionnaire": [topic("pressurised-system"), topic("lifting")],
        })
        self.assertEqual(result["decision"], "ready-with-safety-actions")
        self.assertEqual(result["hazard_families"], ["lifting", "pressurised-system"])
        self.assertEqual(result["hazardous_operations"], ["lift-1"])

    def test_campaign_without_any_hazard_is_ready(self):
        result = assess_campaign_safety({
            "declaration": [entry("box-1", "inert", 3.0)],
            "questionnaire": [],
        })
        self.assertEqual(result["decision"], "ready")
        self.assertEqual(result["design_inputs"], ())

    def test_missing_questionnaire_topic_blocks_the_campaign(self):
        result = assess_campaign_safety({
            "declaration": [entry("pv-1", "pressurised-system", 250.0)],
            "questionnaire": [],
        })
        self.assertEqual(result["decision"], "blocked")
        self.assertEqual(len(result["blocking_findings"]), 1)

    def test_hazardous_fraction_counts_entries_not_families(self):
        result = assess_campaign_safety({
            "declaration": [
                entry("pv-1", "pressurised-system", 250.0),
                entry("box-1", "inert", 3.0),
                entry("box-2", "inert", 3.0),
                entry("box-3", "inert", 3.0),
            ],
            "questionnaire": [topic("pressurised-system")],
        })
        self.assertAlmostEqual(result["hazardous_fraction"], 0.25, places=9)

    def test_advisory_location_finding_does_not_block(self):
        result = assess_campaign_safety({
            "declaration": [entry("pv-1", "pressurised-system", 250.0, location=None)],
            "questionnaire": [topic("pressurised-system")],
        })
        self.assertEqual(result["decision"], "ready-with-safety-actions")
        self.assertEqual(len(result["findings"]), 1)

    def test_design_inputs_follow_the_confirmed_families(self):
        result = assess_campaign_safety({
            "declaration": [entry("py-1", "pyrotechnic", 4.0, location="hazardous-storage")],
            "questionnaire": [topic("pyrotechnic")],
        })
        self.assertIn("electro-explosive-device-handling-controls", result["design_inputs"])

    def test_missing_declaration_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_campaign_safety({"questionnaire": []})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_campaign_safety(["declaration"])


if __name__ == "__main__":
    unittest.main(verbosity=0)
