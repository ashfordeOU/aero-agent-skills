#!/usr/bin/env python3
"""Contract test for the PVA test-condition and method governance (offline)."""

import copy
import unittest

from e2008_pva_test_conditions_and_methods_logic import (
    AM0_REFERENCE_IRRADIANCE_W_PER_M2,
    CONDITION_KINDS,
    CONDITION_OUT_OF_BAND,
    CONDITION_SET_INCOMPLETE,
    DEFAULT_TEST_GOVERNANCE_POLICY,
    METHOD_NOT_ADMISSIBLE,
    METHOD_SOURCES,
    NOT_GOVERNED_BY_DRAWING,
    PROGRAMME_GOVERNED,
    PROGRAMME_NOT_GOVERNED,
    TEST_GOVERNED,
    TEST_PURPOSES,
    condition_deviation,
    condition_within_band,
    document_is_governing,
    evaluate_condition,
    evaluate_test,
    evaluate_test_matrix,
    illumination_intensity_ratio,
    method_admissibility,
    missing_condition_kinds,
    tolerance_utilisation,
    validate_test_governance_policy,
)

GOVERNED_TEST = {
    "name": "reference-spectrum performance measurement",
    "purpose": "electrical-performance",
    "governing_document": "source-control-drawing",
    "method_source": "scd-named-method",
    "conditions": [
        {"kind": "temperature", "specified_value": 25.0, "tolerance": 2.0, "actual_value": 25.5},
        {
            "kind": "illumination-intensity",
            "specified_value": 1.0,
            "tolerance": 0.02,
            "measured_irradiance_w_per_m2": AM0_REFERENCE_IRRADIANCE_W_PER_M2,
        },
    ],
}

CYCLING_TEST = {
    "name": "solar-array coupon cycling",
    "purpose": "thermal-cycling",
    "governing_document": "scd-invoked-specification",
    "method_source": "scd-invoked-standard-method",
    "conditions": [
        {"kind": "temperature", "specified_value": -100.0, "tolerance": 5.0, "actual_value": -98.0},
        {"kind": "cycle-count", "specified_value": 1000.0, "tolerance": 0.0, "actual_value": 1000.0},
    ],
}


def _test(base, **overrides):
    spec = copy.deepcopy(base)
    spec.update(overrides)
    return spec


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_test_governance_policy(DEFAULT_TEST_GOVERNANCE_POLICY),
            DEFAULT_TEST_GOVERNANCE_POLICY,
        )

    def test_policy_covers_every_test_purpose(self):
        for purpose in TEST_PURPOSES:
            self.assertIn(
                purpose, DEFAULT_TEST_GOVERNANCE_POLICY["mandatory_condition_kinds"]
            )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_governance_policy("default")

    def test_policy_missing_a_purpose_rejected(self):
        broken = copy.deepcopy(DEFAULT_TEST_GOVERNANCE_POLICY)
        del broken["mandatory_condition_kinds"]["thermal-cycling"]
        with self.assertRaises(ValueError):
            validate_test_governance_policy(broken)

    def test_policy_with_unknown_condition_kind_rejected(self):
        broken = copy.deepcopy(DEFAULT_TEST_GOVERNANCE_POLICY)
        broken["mandatory_condition_kinds"]["electrical-performance"] = ["moonlight"]
        with self.assertRaises(ValueError):
            validate_test_governance_policy(broken)

    def test_policy_with_empty_method_list_rejected(self):
        broken = copy.deepcopy(DEFAULT_TEST_GOVERNANCE_POLICY)
        broken["admissible_method_sources"] = []
        with self.assertRaises(ValueError):
            validate_test_governance_policy(broken)

    def test_policy_with_unknown_governing_document_rejected(self):
        broken = copy.deepcopy(DEFAULT_TEST_GOVERNANCE_POLICY)
        broken["governing_documents"] = ["hallway-whiteboard"]
        with self.assertRaises(ValueError):
            validate_test_governance_policy(broken)


class IlluminationTests(unittest.TestCase):
    def test_reference_irradiance_is_unit_intensity(self):
        self.assertAlmostEqual(
            illumination_intensity_ratio(AM0_REFERENCE_IRRADIANCE_W_PER_M2), 1.0, places=9
        )

    def test_half_the_reference_irradiance_is_half_intensity(self):
        self.assertAlmostEqual(
            illumination_intensity_ratio(AM0_REFERENCE_IRRADIANCE_W_PER_M2 / 2.0),
            0.5,
            places=9,
        )

    def test_a_custom_reference_spectrum_is_honoured(self):
        self.assertAlmostEqual(
            illumination_intensity_ratio(1000.0, reference_irradiance_w_per_m2=2000.0),
            0.5,
            places=9,
        )

    def test_zero_irradiance_rejected(self):
        with self.assertRaises(ValueError):
            illumination_intensity_ratio(0.0)

    def test_non_numeric_irradiance_rejected(self):
        with self.assertRaises(ValueError):
            illumination_intensity_ratio("1367 W/m2")


class ConditionBandTests(unittest.TestCase):
    def test_deviation_is_signed(self):
        self.assertAlmostEqual(condition_deviation(25.0, 23.5), -1.5, places=9)

    def test_condition_inside_the_band_is_accepted(self):
        self.assertTrue(condition_within_band(25.0, 2.0, 26.0))

    def test_condition_exactly_on_the_band_is_accepted(self):
        self.assertTrue(condition_within_band(25.0, 2.0, 27.0))
        self.assertAlmostEqual(tolerance_utilisation(25.0, 2.0, 27.0), 1.0, places=9)

    def test_condition_outside_the_band_is_rejected(self):
        self.assertFalse(condition_within_band(25.0, 2.0, 28.0))

    def test_band_usage_is_a_fraction_of_the_tolerance(self):
        self.assertAlmostEqual(tolerance_utilisation(25.0, 2.0, 25.5), 0.25, places=9)

    def test_zero_tolerance_demands_the_specified_value(self):
        self.assertTrue(condition_within_band(1000.0, 0.0, 1000.0))
        self.assertAlmostEqual(tolerance_utilisation(1000.0, 0.0, 1000.0), 0.0, places=9)
        self.assertFalse(condition_within_band(1000.0, 0.0, 1001.0))
        self.assertAlmostEqual(tolerance_utilisation(1000.0, 0.0, 1001.0), 1.0, places=9)

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            condition_within_band(25.0, -2.0, 25.0)


class ConditionRecordTests(unittest.TestCase):
    def test_declared_condition_is_evaluated(self):
        record = evaluate_condition(GOVERNED_TEST["conditions"][0])
        self.assertEqual(record["kind"], "temperature")
        self.assertTrue(record["within_band"])
        self.assertAlmostEqual(record["deviation"], 0.5, places=9)
        self.assertAlmostEqual(record["tolerance_utilisation"], 0.25, places=9)

    def test_irradiance_is_converted_before_the_band_is_applied(self):
        record = evaluate_condition(GOVERNED_TEST["conditions"][1])
        self.assertAlmostEqual(record["actual_value"], 1.0, places=9)
        self.assertTrue(record["within_band"])
        self.assertTrue(any("reference spectrum" in f for f in record["findings"]))

    def test_low_irradiance_falls_out_of_the_band(self):
        record = evaluate_condition(
            {
                "kind": "illumination-intensity",
                "specified_value": 1.0,
                "tolerance": 0.02,
                "measured_irradiance_w_per_m2": 1200.0,
            }
        )
        self.assertFalse(record["within_band"])
        self.assertTrue(any("deviates" in f for f in record["findings"]))

    def test_irradiance_on_a_non_illumination_condition_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_condition(
                {
                    "kind": "temperature",
                    "specified_value": 25.0,
                    "tolerance": 2.0,
                    "measured_irradiance_w_per_m2": 1367.0,
                }
            )

    def test_both_value_and_irradiance_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_condition(
                {
                    "kind": "illumination-intensity",
                    "specified_value": 1.0,
                    "tolerance": 0.02,
                    "actual_value": 1.0,
                    "measured_irradiance_w_per_m2": 1367.0,
                }
            )

    def test_condition_without_a_value_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_condition({"kind": "pressure", "specified_value": 1.0, "tolerance": 0.1})

    def test_unknown_condition_kind_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_condition(
                {"kind": "vibe", "specified_value": 1.0, "tolerance": 0.1, "actual_value": 1.0}
            )

    def test_every_condition_kind_is_accepted(self):
        for kind in CONDITION_KINDS:
            record = evaluate_condition(
                {"kind": kind, "specified_value": 10.0, "tolerance": 1.0, "actual_value": 10.0}
            )
            self.assertTrue(record["within_band"])


class MethodTests(unittest.TestCase):
    def test_drawing_named_method_is_admissible(self):
        result = method_admissibility("scd-named-method")
        self.assertTrue(result["admissible"])
        self.assertEqual(result["findings"], [])

    def test_invoked_standard_method_is_admissible(self):
        self.assertTrue(method_admissibility("scd-invoked-standard-method")["admissible"])

    def test_approved_substitution_is_admissible_and_recorded(self):
        result = method_admissibility(
            "equivalent-method-with-approved-deviation",
            deviation_approval_reference="deviation request 22",
        )
        self.assertTrue(result["admissible"])
        self.assertTrue(any("approval" in f for f in result["findings"]))

    def test_substitution_without_an_approval_reference_rejected(self):
        with self.assertRaises(ValueError):
            method_admissibility("equivalent-method-with-approved-deviation")

    def test_unapproved_equivalent_method_is_not_admissible(self):
        result = method_admissibility("equivalent-method-without-approval")
        self.assertFalse(result["admissible"])
        self.assertTrue(any("authority of the drawing" in f for f in result["findings"]))

    def test_supplier_internal_method_is_not_admissible_by_default(self):
        self.assertFalse(method_admissibility("supplier-internal-method")["admissible"])

    def test_unknown_method_source_rejected(self):
        with self.assertRaises(ValueError):
            method_admissibility("whatever-the-lab-had")

    def test_every_method_source_returns_a_verdict(self):
        for source in METHOD_SOURCES:
            reference = "deviation request 1" if "approved" in source else None
            self.assertIn(
                "admissible", method_admissibility(source, reference)
            )


class DocumentTests(unittest.TestCase):
    def test_drawing_governs(self):
        self.assertTrue(document_is_governing("source-control-drawing"))

    def test_invoked_specification_governs(self):
        self.assertTrue(document_is_governing("scd-invoked-specification"))

    def test_supplier_procedure_does_not_govern(self):
        self.assertFalse(document_is_governing("supplier-internal-procedure"))

    def test_unknown_document_rejected(self):
        with self.assertRaises(ValueError):
            document_is_governing("an email")


class ConditionSetTests(unittest.TestCase):
    def test_complete_condition_set_has_no_gap(self):
        self.assertEqual(
            missing_condition_kinds("electrical-performance", GOVERNED_TEST["conditions"]),
            [],
        )

    def test_missing_cycle_count_is_reported(self):
        conditions = [CYCLING_TEST["conditions"][0]]
        self.assertEqual(
            missing_condition_kinds("thermal-cycling", conditions), ["cycle-count"]
        )

    def test_empty_condition_set_rejected(self):
        with self.assertRaises(ValueError):
            missing_condition_kinds("electrical-performance", [])


class TestGovernanceTests(unittest.TestCase):
    def test_governed_test_passes(self):
        result = evaluate_test(GOVERNED_TEST)
        self.assertEqual(result["verdict"], TEST_GOVERNED)
        self.assertTrue(result["governed"])
        self.assertEqual(result["governing_condition_kind"], "temperature")

    def test_cycling_test_with_an_exact_cycle_count_passes(self):
        result = evaluate_test(CYCLING_TEST)
        self.assertEqual(result["verdict"], TEST_GOVERNED)

    def test_supplier_procedure_loses_governance_before_anything_else(self):
        spec = _test(
            GOVERNED_TEST,
            governing_document="supplier-internal-procedure",
            method_source="supplier-internal-method",
        )
        result = evaluate_test(spec)
        self.assertEqual(result["verdict"], NOT_GOVERNED_BY_DRAWING)
        self.assertFalse(result["document_is_governing"])

    def test_unapproved_method_is_reported_over_a_condition_defect(self):
        spec = _test(GOVERNED_TEST, method_source="equivalent-method-without-approval")
        spec["conditions"][0]["actual_value"] = 40.0
        result = evaluate_test(spec)
        self.assertEqual(result["verdict"], METHOD_NOT_ADMISSIBLE)

    def test_missing_mandatory_condition_is_reported(self):
        spec = _test(GOVERNED_TEST, conditions=[GOVERNED_TEST["conditions"][0]])
        result = evaluate_test(spec)
        self.assertEqual(result["verdict"], CONDITION_SET_INCOMPLETE)
        self.assertEqual(result["missing_condition_kinds"], ["illumination-intensity"])

    def test_out_of_band_condition_is_reported(self):
        spec = copy.deepcopy(GOVERNED_TEST)
        spec["conditions"][0]["actual_value"] = 30.0
        result = evaluate_test(spec)
        self.assertEqual(result["verdict"], CONDITION_OUT_OF_BAND)
        self.assertEqual(result["out_of_band_conditions"], ["temperature"])

    def test_test_without_conditions_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_test(_test(GOVERNED_TEST, conditions=[]))

    def test_test_without_a_name_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_test(_test(GOVERNED_TEST, name="   "))

    def test_test_with_unknown_purpose_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_test(_test(GOVERNED_TEST, purpose="looks-nice"))

    def test_non_mapping_test_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_test("reference-spectrum performance measurement")


class MatrixTests(unittest.TestCase):
    def test_fully_governed_matrix_passes(self):
        result = evaluate_test_matrix({"tests": [GOVERNED_TEST, CYCLING_TEST]})
        self.assertEqual(result["verdict"], PROGRAMME_GOVERNED)
        self.assertAlmostEqual(result["governed_fraction"], 1.0, places=9)
        self.assertEqual(result["ungoverned_tests"], [])

    def test_one_ungoverned_test_holds_the_programme(self):
        loose = _test(
            CYCLING_TEST,
            name="supplier screening run",
            governing_document="supplier-internal-procedure",
            method_source="supplier-internal-method",
        )
        result = evaluate_test_matrix({"tests": [GOVERNED_TEST, loose]})
        self.assertEqual(result["verdict"], PROGRAMME_NOT_GOVERNED)
        self.assertEqual(result["ungoverned_tests"], ["supplier screening run"])
        self.assertAlmostEqual(result["governed_fraction"], 0.5, places=9)

    def test_matrix_groups_results_by_verdict(self):
        loose = _test(GOVERNED_TEST, name="loose run", method_source="supplier-internal-method")
        result = evaluate_test_matrix({"tests": [GOVERNED_TEST, loose]})
        self.assertEqual(result["grouped_by_verdict"][METHOD_NOT_ADMISSIBLE], ["loose run"])
        self.assertIn(TEST_GOVERNED, result["grouped_by_verdict"])

    def test_matrix_collects_every_finding(self):
        loose = _test(GOVERNED_TEST, name="loose run", method_source="supplier-internal-method")
        findings = evaluate_test_matrix({"tests": [loose]})["findings"]
        self.assertTrue(any("authority of the drawing" in f for f in findings))

    def test_empty_matrix_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_test_matrix({"tests": []})

    def test_non_mapping_matrix_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_test_matrix([GOVERNED_TEST])

    def test_a_stricter_policy_can_close_a_governed_matrix(self):
        policy = copy.deepcopy(DEFAULT_TEST_GOVERNANCE_POLICY)
        policy["governing_documents"] = ["source-control-drawing"]
        result = evaluate_test_matrix({"tests": [GOVERNED_TEST, CYCLING_TEST]}, policy)
        self.assertEqual(result["verdict"], PROGRAMME_NOT_GOVERNED)
        self.assertEqual(result["ungoverned_tests"], ["solar-array coupon cycling"])


if __name__ == "__main__":
    unittest.main()
