"""Contract tests for the clause 7.1 hybrid design general-requirements logic."""

import unittest

from q6005_hybrid_design_general_requirements_logic import (
    DEFAULT_DERATING_LIMITS,
    MARGIN_TOLERANCE,
    REQUIRED_DESIGN_EVIDENCE,
    assess_clearances,
    assess_element,
    assess_elements,
    assess_hybrid_design,
    clearance_margin_mm,
    derating_limit_for,
    derating_ratio,
    junction_temperature_c,
    missing_evidence,
    thermal_margin_k,
    validate_evidence_record,
)

COMPLETE_EVIDENCE = {item: True for item in REQUIRED_DESIGN_EVIDENCE}

ELEMENTS = [
    {"reference": "R1", "family": "resistor", "applied": 0.100, "rated": 0.250},
    {"reference": "C1", "family": "capacitor", "applied": 30.0, "rated": 100.0},
    {"reference": "U1", "family": "semiconductor-die", "applied": 0.500, "rated": 1.000},
]

MINIMA = {
    "conductor-spacing-mm": 0.200,
    "wire-bond-to-adjacent-feature-mm": 0.250,
    "die-to-die-mm": 0.500,
}

DECLARED = {
    "conductor-spacing-mm": 0.300,
    "wire-bond-to-adjacent-feature-mm": 0.400,
    "die-to-die-mm": 0.800,
}


def _spec(**overrides):
    spec = {
        "evidence": dict(COMPLETE_EVIDENCE),
        "elements": [dict(e) for e in ELEMENTS],
        "base_temperature_c": 55.0,
        "dissipation_w": 1.20,
        "thermal_resistances_k_per_w": [12.0, 3.0, 2.0],
        "max_junction_temperature_c": 110.0,
        "clearances_mm": dict(DECLARED),
        "clearance_minima_mm": dict(MINIMA),
    }
    spec.update(overrides)
    return spec


class EvidenceTests(unittest.TestCase):
    def test_complete_record_has_no_gap(self):
        self.assertEqual(missing_evidence(COMPLETE_EVIDENCE), ())

    def test_absent_item_is_a_gap(self):
        record = dict(COMPLETE_EVIDENCE)
        del record["thermal-analysis"]
        self.assertIn("thermal-analysis", missing_evidence(record))

    def test_declared_but_incomplete_item_is_a_gap(self):
        record = dict(COMPLETE_EVIDENCE)
        record["worst-case-analysis"] = False
        self.assertEqual(missing_evidence(record), ("worst-case-analysis",))

    def test_gaps_follow_the_mandated_order(self):
        gaps = missing_evidence({"design-rules": True})
        self.assertEqual(gaps, tuple(i for i in REQUIRED_DESIGN_EVIDENCE if i != "design-rules"))

    def test_unknown_evidence_item_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence_record({"marketing-brochure": True})

    def test_non_boolean_evidence_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence_record({"design-rules": "yes"})

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence_record(["design-rules"])


class DeratingTests(unittest.TestCase):
    def test_ratio_is_applied_over_rated(self):
        self.assertAlmostEqual(derating_ratio(0.1, 0.25), 0.40, places=9)

    def test_zero_applied_is_allowed(self):
        self.assertAlmostEqual(derating_ratio(0.0, 0.25), 0.0, places=9)

    def test_zero_rated_rejected(self):
        with self.assertRaises(ValueError):
            derating_ratio(0.1, 0.0)

    def test_negative_applied_rejected(self):
        with self.assertRaises(ValueError):
            derating_ratio(-0.1, 0.25)

    def test_boolean_applied_rejected(self):
        with self.assertRaises(ValueError):
            derating_ratio(True, 0.25)

    def test_family_limit_read_from_the_default_table(self):
        self.assertAlmostEqual(derating_limit_for("resistor"), DEFAULT_DERATING_LIMITS["resistor"])

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            derating_limit_for("unobtainium")

    def test_element_exactly_at_its_limit_is_compliant(self):
        record = assess_element(
            {"reference": "R9", "family": "resistor", "applied": 0.125, "rated": 0.250}
        )
        self.assertAlmostEqual(record["ratio"], record["limit"], places=9)
        self.assertTrue(record["compliant"])

    def test_element_above_its_limit_is_not_compliant(self):
        record = assess_element(
            {"reference": "R9", "family": "resistor", "applied": 0.200, "rated": 0.250}
        )
        self.assertFalse(record["compliant"])

    def test_duplicate_element_reference_rejected(self):
        with self.assertRaises(ValueError):
            assess_elements([dict(ELEMENTS[0]), dict(ELEMENTS[0])])

    def test_empty_element_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_elements([])

    def test_element_missing_a_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_element({"reference": "R1", "family": "resistor", "applied": 0.1})


class ThermalTests(unittest.TestCase):
    def test_junction_temperature_stacks_the_resistances(self):
        self.assertAlmostEqual(junction_temperature_c(55.0, 1.2, [12.0, 3.0, 2.0]), 75.4, places=9)

    def test_zero_dissipation_leaves_the_base_temperature(self):
        self.assertAlmostEqual(junction_temperature_c(-20.0, 0.0, [12.0]), -20.0, places=9)

    def test_empty_resistance_stack_rejected(self):
        with self.assertRaises(ValueError):
            junction_temperature_c(55.0, 1.2, [])

    def test_negative_resistance_rejected(self):
        with self.assertRaises(ValueError):
            junction_temperature_c(55.0, 1.2, [12.0, -1.0])

    def test_margin_is_allowance_minus_junction(self):
        self.assertAlmostEqual(thermal_margin_k(75.4, 110.0), 34.6, places=9)

    def test_junction_exactly_at_the_allowance_has_zero_margin(self):
        self.assertAlmostEqual(thermal_margin_k(110.0, 110.0), 0.0, places=9)


class ClearanceTests(unittest.TestCase):
    def test_margin_is_declared_minus_minimum(self):
        self.assertAlmostEqual(clearance_margin_mm(0.300, 0.200), 0.100, places=9)

    def test_records_are_returned_in_name_order(self):
        records = assess_clearances(DECLARED, MINIMA)
        self.assertEqual([r["name"] for r in records], sorted(MINIMA))

    def test_clearance_exactly_at_its_minimum_is_compliant(self):
        records = assess_clearances({"a-mm": 0.250}, {"a-mm": 0.250})
        self.assertAlmostEqual(records[0]["margin_mm"], 0.0, places=9)
        self.assertTrue(records[0]["compliant"])

    def test_clearance_below_its_minimum_is_not_compliant(self):
        records = assess_clearances({"a-mm": 0.100}, {"a-mm": 0.250})
        self.assertFalse(records[0]["compliant"])

    def test_declared_clearance_without_a_minimum_rejected(self):
        with self.assertRaises(ValueError):
            assess_clearances({"a-mm": 0.3, "b-mm": 0.3}, {"a-mm": 0.2})

    def test_minimum_without_a_declared_value_rejected(self):
        with self.assertRaises(ValueError):
            assess_clearances({"a-mm": 0.3}, {"a-mm": 0.2, "b-mm": 0.2})


class AssessmentTests(unittest.TestCase):
    def test_sound_design_is_releasable(self):
        result = assess_hybrid_design(_spec())
        self.assertTrue(result["releasable"])
        self.assertEqual(result["findings"], [])

    def test_evidence_gap_holds_the_design(self):
        evidence = dict(COMPLETE_EVIDENCE)
        evidence["layout-drawing"] = False
        result = assess_hybrid_design(_spec(evidence=evidence))
        self.assertFalse(result["releasable"])
        self.assertIn("layout-drawing", result["evidence_gaps"])

    def test_over_derated_element_is_named(self):
        elements = [dict(e) for e in ELEMENTS]
        elements[0]["applied"] = 0.240
        result = assess_hybrid_design(_spec(elements=elements))
        self.assertEqual(result["over_derated"], ("R1",))
        self.assertFalse(result["releasable"])

    def test_thermal_overshoot_is_reported_with_the_deficit(self):
        result = assess_hybrid_design(_spec(max_junction_temperature_c=70.0))
        self.assertFalse(result["thermal_compliant"])
        self.assertAlmostEqual(result["thermal_margin_k"], -5.4, places=9)

    def test_junction_exactly_at_the_allowance_still_releases(self):
        result = assess_hybrid_design(_spec(max_junction_temperature_c=75.4))
        self.assertAlmostEqual(result["thermal_margin_k"], 0.0, places=9)
        self.assertTrue(result["thermal_compliant"])

    def test_tight_clearance_is_named(self):
        declared = dict(DECLARED)
        declared["die-to-die-mm"] = 0.400
        result = assess_hybrid_design(_spec(clearances_mm=declared))
        self.assertEqual(result["tight_clearances"], ("die-to-die-mm",))

    def test_several_shortfalls_are_all_reported(self):
        evidence = dict(COMPLETE_EVIDENCE)
        evidence["derating-analysis"] = False
        declared = dict(DECLARED)
        declared["conductor-spacing-mm"] = 0.100
        result = assess_hybrid_design(_spec(evidence=evidence, clearances_mm=declared))
        self.assertEqual(len(result["findings"]), 2)

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["dissipation_w"]
        with self.assertRaises(ValueError):
            assess_hybrid_design(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_hybrid_design(["evidence"])

    def test_tolerance_is_far_below_an_engineering_digit(self):
        self.assertLess(MARGIN_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
