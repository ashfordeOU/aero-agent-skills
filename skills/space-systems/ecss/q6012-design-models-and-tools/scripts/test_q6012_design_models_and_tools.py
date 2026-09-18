"""Contract tests for the clause 5.3 model, design-kit and tool acceptance."""

import unittest

from q6012_design_models_and_tools_logic import (
    COVERAGE_TOLERANCE,
    DESIGN_KIT_ACCEPTABLE,
    MODEL_CORRELATION_EXCEEDED,
    MODEL_ENVELOPE_EXCEEDED,
    MODEL_PROCESS_RELEASE_MISMATCH,
    PASSIVE_EM_VERIFICATION_MISSING,
    TOOL_NOT_VERSION_CONTROLLED,
    TOOL_VALIDATION_EVIDENCE_MISSING,
    assess_design_kit,
    assess_model,
    assess_tool,
    axis_coverage,
    envelope_coverage,
    model_acceptance_fraction,
    span_overlap,
    validate_model,
    validate_model_policy,
    validate_span,
    validate_tool,
    validate_usage_envelope,
)

USAGE = {
    "frequency_ghz": (26.0, 30.0),
    "bias_v": (0.0, 6.0),
    "temperature_c": (-30.0, 85.0),
    "process_release": "phemt-rel-4",
}

ACTIVE_MODEL = {
    "id": "fet-2x50um",
    "kind": "active-device",
    "frequency_ghz": (1.0, 40.0),
    "bias_v": (0.0, 8.0),
    "temperature_c": (-55.0, 125.0),
    "process_release": "phemt-rel-4",
    "correlation_error_pct": 3.0,
}

PASSIVE_MODEL = {
    "id": "spiral-inductor",
    "kind": "passive-structure",
    "frequency_ghz": (1.0, 40.0),
    "bias_v": (0.0, 8.0),
    "temperature_c": (-55.0, 125.0),
    "process_release": "phemt-rel-4",
    "correlation_error_pct": 2.0,
    "em_verified": True,
}

TOOL = {
    "name": "harmonic-balance-suite",
    "version": "9.2",
    "version_controlled": True,
    "validation_evidence": True,
}


def with_changes(base, **overrides):
    record = dict(base)
    record.update(overrides)
    return record


class PolicyTests(unittest.TestCase):
    def test_defaults_are_returned_when_no_policy_given(self):
        rules = validate_model_policy()
        self.assertAlmostEqual(rules["max_correlation_error_pct"], 5.0, places=9)
        self.assertFalse(rules["allow_envelope_extrapolation"])

    def test_override_is_merged_over_the_defaults(self):
        rules = validate_model_policy({"max_correlation_error_pct": 8.0})
        self.assertAlmostEqual(rules["max_correlation_error_pct"], 8.0, places=9)
        self.assertTrue(rules["require_tool_version_control"])

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_model_policy({"max_model_age_years": 3})

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_model_policy({"allow_envelope_extrapolation": "yes"})

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_model_policy({"max_correlation_error_pct": -1.0})

    def test_coverage_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_model_policy({"min_axis_coverage": 1.5})


class SpanTests(unittest.TestCase):
    def test_span_is_returned_as_floats(self):
        self.assertEqual(validate_span((2, 8), "band"), (2.0, 8.0))

    def test_negative_temperature_span_allowed(self):
        self.assertEqual(validate_span((-55, 125), "temperature_c"), (-55.0, 125.0))

    def test_inverted_span_rejected(self):
        with self.assertRaises(ValueError):
            validate_span((30.0, 26.0), "band")

    def test_non_numeric_span_rejected(self):
        with self.assertRaises(ValueError):
            validate_span(("26", 30.0), "band")

    def test_non_finite_span_rejected(self):
        with self.assertRaises(ValueError):
            validate_span((26.0, float("inf")), "band")

    def test_positive_flag_rejects_zero_frequency(self):
        with self.assertRaises(ValueError):
            validate_span((0.0, 30.0), "frequency_ghz", positive=True)

    def test_three_element_span_rejected(self):
        with self.assertRaises(ValueError):
            validate_span((1.0, 2.0, 3.0), "band")


class CoverageTests(unittest.TestCase):
    def test_disjoint_spans_do_not_overlap(self):
        self.assertAlmostEqual(span_overlap((26.0, 30.0), (40.0, 50.0)), 0.0, places=9)

    def test_partial_overlap_width(self):
        self.assertAlmostEqual(span_overlap((26.0, 30.0), (28.0, 50.0)), 2.0, places=9)

    def test_exactly_covered_axis_is_unity(self):
        self.assertAlmostEqual(axis_coverage((26.0, 30.0), (26.0, 30.0)), 1.0, places=9)

    def test_half_covered_axis(self):
        self.assertAlmostEqual(axis_coverage((26.0, 30.0), (28.0, 40.0)), 0.5, places=9)

    def test_uncovered_axis_is_zero(self):
        self.assertAlmostEqual(axis_coverage((26.0, 30.0), (40.0, 50.0)), 0.0, places=9)

    def test_single_point_usage_inside_validated_span(self):
        self.assertAlmostEqual(axis_coverage((28.0, 28.0), (26.0, 30.0)), 1.0, places=9)

    def test_single_point_usage_outside_validated_span(self):
        self.assertAlmostEqual(axis_coverage((32.0, 32.0), (26.0, 30.0)), 0.0, places=9)

    def test_worst_axis_is_named(self):
        model = with_changes(ACTIVE_MODEL, temperature_c=(-10.0, 40.0))
        coverage = envelope_coverage(model, USAGE)
        self.assertEqual(coverage["worst_axis"], "temperature_c")

    def test_volume_coverage_is_the_product_of_the_axes(self):
        model = with_changes(ACTIVE_MODEL, bias_v=(0.0, 3.0))
        coverage = envelope_coverage(model, USAGE)
        expected = coverage["frequency_ghz"] * coverage["bias_v"] * coverage["temperature_c"]
        self.assertAlmostEqual(coverage["volume_coverage"], expected, places=9)


class ValidationTests(unittest.TestCase):
    def test_usage_envelope_missing_key_rejected(self):
        envelope = dict(USAGE)
        del envelope["bias_v"]
        with self.assertRaises(ValueError):
            validate_usage_envelope(envelope)

    def test_blank_process_release_rejected(self):
        with self.assertRaises(ValueError):
            validate_usage_envelope(with_changes(USAGE, process_release="  "))

    def test_unknown_model_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_model(with_changes(ACTIVE_MODEL, kind="behavioural"))

    def test_negative_correlation_error_rejected(self):
        with self.assertRaises(ValueError):
            validate_model(with_changes(ACTIVE_MODEL, correlation_error_pct=-2.0))

    def test_non_boolean_em_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_model(with_changes(PASSIVE_MODEL, em_verified="checked"))

    def test_model_missing_key_rejected(self):
        model = dict(ACTIVE_MODEL)
        del model["process_release"]
        with self.assertRaises(ValueError):
            validate_model(model)

    def test_tool_missing_version_rejected(self):
        tool = dict(TOOL)
        del tool["version"]
        with self.assertRaises(ValueError):
            validate_tool(tool)

    def test_non_mapping_tool_rejected(self):
        with self.assertRaises(ValueError):
            validate_tool(["harmonic-balance-suite", "9.2"])


class ModelAssessmentTests(unittest.TestCase):
    def test_covering_model_is_acceptable(self):
        record = assess_model(ACTIVE_MODEL, USAGE)
        self.assertTrue(record["acceptable"])
        self.assertEqual(record["findings"], [])

    def test_model_validated_exactly_over_the_used_band_is_acceptable(self):
        model = with_changes(
            ACTIVE_MODEL,
            frequency_ghz=(26.0, 30.0),
            bias_v=(0.0, 6.0),
            temperature_c=(-30.0, 85.0),
        )
        record = assess_model(model, USAGE)
        self.assertAlmostEqual(record["coverage"]["worst_coverage"], 1.0, places=9)
        self.assertTrue(record["acceptable"])

    def test_short_envelope_is_flagged(self):
        model = with_changes(ACTIVE_MODEL, frequency_ghz=(1.0, 28.0))
        record = assess_model(model, USAGE)
        self.assertIn(MODEL_ENVELOPE_EXCEEDED, record["statuses"])

    def test_extrapolation_allowed_by_policy_drops_the_envelope_finding(self):
        model = with_changes(ACTIVE_MODEL, frequency_ghz=(1.0, 28.0))
        record = assess_model(model, USAGE, {"allow_envelope_extrapolation": True})
        self.assertNotIn(MODEL_ENVELOPE_EXCEEDED, record["statuses"])

    def test_process_release_mismatch_is_flagged(self):
        record = assess_model(with_changes(ACTIVE_MODEL, process_release="phemt-rel-3"), USAGE)
        self.assertIn(MODEL_PROCESS_RELEASE_MISMATCH, record["statuses"])

    def test_correlation_error_exactly_at_the_tolerance_is_accepted(self):
        model = with_changes(ACTIVE_MODEL, correlation_error_pct=5.0)
        record = assess_model(model, USAGE)
        self.assertAlmostEqual(record["correlation_error_pct"], 5.0, places=9)
        self.assertTrue(record["acceptable"])

    def test_correlation_error_above_the_tolerance_is_flagged(self):
        model = with_changes(ACTIVE_MODEL, correlation_error_pct=7.5)
        record = assess_model(model, USAGE)
        self.assertIn(MODEL_CORRELATION_EXCEEDED, record["statuses"])

    def test_unverified_passive_in_band_is_flagged(self):
        model = with_changes(PASSIVE_MODEL, em_verified=False)
        record = assess_model(model, USAGE)
        self.assertIn(PASSIVE_EM_VERIFICATION_MISSING, record["statuses"])

    def test_unverified_passive_at_the_threshold_frequency_is_flagged(self):
        envelope = with_changes(USAGE, frequency_ghz=(2.0, 20.0))
        model = with_changes(PASSIVE_MODEL, em_verified=False)
        record = assess_model(model, envelope)
        self.assertIn(PASSIVE_EM_VERIFICATION_MISSING, record["statuses"])

    def test_unverified_passive_well_below_the_threshold_is_accepted(self):
        envelope = with_changes(USAGE, frequency_ghz=(2.0, 6.0))
        model = with_changes(PASSIVE_MODEL, em_verified=False)
        record = assess_model(model, envelope)
        self.assertTrue(record["acceptable"])

    def test_active_model_needs_no_electromagnetic_verification(self):
        record = assess_model(with_changes(ACTIVE_MODEL, em_verified=False), USAGE)
        self.assertNotIn(PASSIVE_EM_VERIFICATION_MISSING, record["statuses"])


class ToolTests(unittest.TestCase):
    def test_controlled_tool_is_acceptable(self):
        self.assertTrue(assess_tool(TOOL)["acceptable"])

    def test_uncontrolled_tool_is_flagged(self):
        record = assess_tool(with_changes(TOOL, version_controlled=False))
        self.assertIn(TOOL_NOT_VERSION_CONTROLLED, record["statuses"])

    def test_tool_without_validation_evidence_is_flagged(self):
        record = assess_tool(with_changes(TOOL, validation_evidence=False))
        self.assertIn(TOOL_VALIDATION_EVIDENCE_MISSING, record["statuses"])

    def test_version_control_requirement_can_be_waived(self):
        record = assess_tool(
            with_changes(TOOL, version_controlled=False),
            {"require_tool_version_control": False},
        )
        self.assertTrue(record["acceptable"])


class AcceptanceFractionTests(unittest.TestCase):
    def test_all_accepted_is_unity(self):
        records = [{"acceptable": True}, {"acceptable": True}]
        self.assertAlmostEqual(model_acceptance_fraction(records), 1.0, places=9)

    def test_half_accepted(self):
        records = [{"acceptable": True}, {"acceptable": False}]
        self.assertAlmostEqual(model_acceptance_fraction(records), 0.5, places=9)

    def test_empty_record_set_rejected(self):
        with self.assertRaises(ValueError):
            model_acceptance_fraction([])

    def test_malformed_record_rejected(self):
        with self.assertRaises(ValueError):
            model_acceptance_fraction([{"id": "fet"}])


class DesignKitTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "usage_envelope": USAGE,
            "models": [ACTIVE_MODEL, PASSIVE_MODEL],
            "tools": [TOOL],
        }
        spec.update(overrides)
        return spec

    def test_clean_kit_is_acceptable(self):
        result = assess_design_kit(self._spec())
        self.assertEqual(result["verdict"], DESIGN_KIT_ACCEPTABLE)
        self.assertEqual(result["findings"], [])

    def test_acceptance_fraction_counts_the_models(self):
        spec = self._spec(
            models=[ACTIVE_MODEL, with_changes(PASSIVE_MODEL, correlation_error_pct=9.0)]
        )
        result = assess_design_kit(spec)
        self.assertAlmostEqual(result["model_acceptance_fraction"], 0.5, places=9)

    def test_release_mismatch_outranks_a_correlation_finding(self):
        spec = self._spec(
            models=[
                with_changes(ACTIVE_MODEL, correlation_error_pct=9.0),
                with_changes(PASSIVE_MODEL, process_release="phemt-rel-3"),
            ]
        )
        result = assess_design_kit(spec)
        self.assertEqual(result["verdict"], MODEL_PROCESS_RELEASE_MISMATCH)

    def test_tool_finding_reaches_the_verdict(self):
        spec = self._spec(tools=[with_changes(TOOL, version_controlled=False)])
        result = assess_design_kit(spec)
        self.assertEqual(result["verdict"], TOOL_NOT_VERSION_CONTROLLED)
        self.assertFalse(result["acceptable"])

    def test_duplicate_model_id_rejected(self):
        spec = self._spec(models=[ACTIVE_MODEL, with_changes(PASSIVE_MODEL, id="fet-2x50um")])
        with self.assertRaises(ValueError):
            assess_design_kit(spec)

    def test_empty_model_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_design_kit(self._spec(models=[]))

    def test_missing_tools_key_rejected(self):
        spec = self._spec()
        del spec["tools"]
        with self.assertRaises(ValueError):
            assess_design_kit(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_design_kit(["usage_envelope"])

    def test_findings_are_carried_through_from_every_model(self):
        spec = self._spec(
            models=[
                with_changes(ACTIVE_MODEL, process_release="phemt-rel-3"),
                with_changes(PASSIVE_MODEL, em_verified=False),
            ]
        )
        result = assess_design_kit(spec)
        self.assertEqual(len(result["findings"]), 2)

    def test_tolerance_is_small_enough_to_be_a_representation_allowance(self):
        self.assertAlmostEqual(COVERAGE_TOLERANCE, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main()
