"""Contract tests for the clause 8.2.1 device configuration system logic."""

import unittest

from q6003_device_configuration_system_implementation_logic import (
    ARTEFACT_FIELDS,
    BASELINE_FIELDS,
    COVERAGE_TOLERANCE,
    REGENERATING_ARTEFACT_KINDS,
    RETENTION_STATES,
    TOOL_AVAILABILITY,
    UNPINNED_VERSION_TOKENS,
    artefact_retrievability,
    assess_device_configuration_system,
    baseline_completeness,
    evaluate_baseline,
    regeneration_coverage,
    tool_reproducibility,
    validate_baseline_id,
)

SOURCE = "A-SRC-01"
RECORD = "A-PROC-01"
TOOL = "T-SYNTH-01"


def artefact(**overrides):
    """Return one retrievable stored artefact with optional overrides."""
    base = {
        "artefact_id": SOURCE,
        "kind": "design-source",
        "retention_state": "retained",
        "integrity_value": "b7f1c2d4",
    }
    base.update(overrides)
    return base


def process_record(**overrides):
    """Return one retrievable process record artefact."""
    return artefact(artefact_id=RECORD, kind="process-record", **overrides)


def tool(**overrides):
    """Return one reproducible production tool with optional overrides."""
    base = {"tool_id": TOOL, "version": "9.4.2", "availability": "available"}
    base.update(overrides)
    return base


def baseline(**overrides):
    """Return one regenerable released baseline with optional overrides."""
    base = {
        "baseline_id": "BL-2026-A",
        "device_id": "ASIC-4410",
        "units_built": 40,
        "artefact_refs": [SOURCE, RECORD],
        "tool_refs": [TOOL],
    }
    base.update(overrides)
    return base


def index(*entries):
    key = "artefact_id" if "artefact_id" in entries[0] else "tool_id"
    return {entry[key]: entry for entry in entries}


class BaselineIdTests(unittest.TestCase):
    def test_identifier_is_stripped(self):
        self.assertEqual(validate_baseline_id("  BL-2026-A "), "BL-2026-A")

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_baseline_id("   ")

    def test_non_string_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_baseline_id(2026)


class ArtefactRetrievabilityTests(unittest.TestCase):
    def test_retained_artefact_with_integrity_is_retrievable(self):
        retrievable, reason = artefact_retrievability(artefact())
        self.assertTrue(retrievable)
        self.assertIsNone(reason)

    def test_offline_archive_still_counts_as_retrievable(self):
        retrievable, _ = artefact_retrievability(
            artefact(retention_state="archived-offline")
        )
        self.assertTrue(retrievable)

    def test_overwritten_in_place_is_its_own_reason(self):
        retrievable, reason = artefact_retrievability(
            artefact(retention_state="superseded-in-place")
        )
        self.assertFalse(retrievable)
        self.assertEqual(reason, "artefact-overwritten-in-place")

    def test_purged_artefact_is_not_retained(self):
        retrievable, reason = artefact_retrievability(
            artefact(retention_state="purged")
        )
        self.assertFalse(retrievable)
        self.assertEqual(reason, "artefact-not-retained")

    def test_missing_integrity_value_blocks_retrievability(self):
        retrievable, reason = artefact_retrievability(artefact(integrity_value="  "))
        self.assertFalse(retrievable)
        self.assertEqual(reason, "artefact-integrity-unrecorded")

    def test_retention_state_lookup_is_case_insensitive(self):
        retrievable, _ = artefact_retrievability(artefact(retention_state="RETAINED"))
        self.assertTrue(retrievable)

    def test_unknown_retention_state_rejected(self):
        with self.assertRaises(ValueError):
            artefact_retrievability(artefact(retention_state="somewhere-in-a-drawer"))

    def test_every_known_retention_state_answers_a_boolean(self):
        for state in RETENTION_STATES:
            retrievable, _ = artefact_retrievability(artefact(retention_state=state))
            self.assertIsInstance(retrievable, bool)

    def test_non_mapping_artefact_rejected(self):
        with self.assertRaises(ValueError):
            artefact_retrievability(SOURCE)

    def test_every_named_artefact_field_is_checked(self):
        self.assertIn("integrity_value", ARTEFACT_FIELDS)
        for field in ("artefact_id", "kind", "retention_state"):
            broken = artefact()
            del broken[field]
            with self.assertRaises(ValueError):
                artefact_retrievability(broken)


class ToolReproducibilityTests(unittest.TestCase):
    def test_available_pinned_tool_is_reproducible(self):
        reproducible, reason = tool_reproducibility(tool())
        self.assertTrue(reproducible)
        self.assertIsNone(reason)

    def test_archived_executable_still_counts(self):
        reproducible, _ = tool_reproducibility(
            tool(availability="archived-executable")
        )
        self.assertTrue(reproducible)

    def test_withdrawn_tool_cannot_be_run(self):
        reproducible, reason = tool_reproducibility(tool(availability="withdrawn"))
        self.assertFalse(reproducible)
        self.assertEqual(reason, "tool-withdrawn")

    def test_floating_version_pins_nothing(self):
        for token in UNPINNED_VERSION_TOKENS:
            reproducible, reason = tool_reproducibility(tool(version=token))
            self.assertFalse(reproducible)
            self.assertEqual(reason, "tool-version-unpinned")

    def test_blank_version_pins_nothing(self):
        reproducible, reason = tool_reproducibility(tool(version="   "))
        self.assertFalse(reproducible)
        self.assertEqual(reason, "tool-version-unpinned")

    def test_withdrawal_outranks_a_pinned_version(self):
        reproducible, reason = tool_reproducibility(
            tool(version="9.4.2", availability="withdrawn")
        )
        self.assertFalse(reproducible)
        self.assertEqual(reason, "tool-withdrawn")

    def test_unknown_availability_rejected(self):
        with self.assertRaises(ValueError):
            tool_reproducibility(tool(availability="probably-somewhere"))

    def test_every_known_availability_answers_a_boolean(self):
        for value in TOOL_AVAILABILITY:
            reproducible, _ = tool_reproducibility(tool(availability=value))
            self.assertIsInstance(reproducible, bool)

    def test_non_mapping_tool_rejected(self):
        with self.assertRaises(ValueError):
            tool_reproducibility(TOOL)


class BaselineCompletenessTests(unittest.TestCase):
    def test_complete_baseline_scores_one(self):
        missing, fraction = baseline_completeness(baseline())
        self.assertEqual(missing, ())
        self.assertAlmostEqual(fraction, 1.0, places=9)

    def test_missing_tool_refs_reported(self):
        incomplete = baseline()
        del incomplete["tool_refs"]
        missing, fraction = baseline_completeness(incomplete)
        self.assertIn("tool_refs", missing)
        self.assertAlmostEqual(
            fraction, (len(BASELINE_FIELDS) - 1) / len(BASELINE_FIELDS), places=9
        )

    def test_empty_artefact_ref_list_counts_as_missing(self):
        missing, _ = baseline_completeness(baseline(artefact_refs=[]))
        self.assertIn("artefact_refs", missing)

    def test_blank_device_id_counts_as_missing(self):
        missing, _ = baseline_completeness(baseline(device_id="  "))
        self.assertIn("device_id", missing)

    def test_non_mapping_baseline_rejected(self):
        with self.assertRaises(ValueError):
            baseline_completeness("BL-2026-A")


class EvaluateBaselineTests(unittest.TestCase):
    def setUp(self):
        self.artefacts = index(artefact(), process_record())
        self.tools = index(tool())

    def test_clean_baseline_is_regenerable(self):
        record = evaluate_baseline(baseline(), self.artefacts, self.tools)
        self.assertEqual(record["disposition"], "regenerable")
        self.assertTrue(record["regenerable"])

    def test_incomplete_baseline_is_not_graded_further(self):
        record = evaluate_baseline(
            baseline(units_built=None), self.artefacts, self.tools
        )
        self.assertEqual(record["disposition"], "record-incomplete")
        self.assertEqual(record["units_built"], 0)

    def test_unresolved_artefact_reference_is_reported(self):
        record = evaluate_baseline(
            baseline(artefact_refs=[SOURCE, "A-GHOST"]), self.artefacts, self.tools
        )
        self.assertEqual(record["disposition"], "artefact-reference-unresolved")
        self.assertEqual(record["blocking_reference"], "A-GHOST")

    def test_unresolved_tool_reference_is_reported(self):
        record = evaluate_baseline(
            baseline(tool_refs=["T-GHOST"]), self.artefacts, self.tools
        )
        self.assertEqual(record["disposition"], "tool-reference-unresolved")
        self.assertEqual(record["blocking_reference"], "T-GHOST")

    def test_overwritten_artefact_blocks_the_baseline(self):
        artefacts = index(
            artefact(retention_state="superseded-in-place"), process_record()
        )
        record = evaluate_baseline(baseline(), artefacts, self.tools)
        self.assertEqual(record["disposition"], "artefact-overwritten-in-place")
        self.assertEqual(record["blocking_reference"], SOURCE)

    def test_unpinned_tool_blocks_the_baseline(self):
        record = evaluate_baseline(
            baseline(), self.artefacts, index(tool(version="latest"))
        )
        self.assertEqual(record["disposition"], "tool-version-unpinned")
        self.assertEqual(record["blocking_reference"], TOOL)

    def test_records_alone_cannot_regenerate_a_device(self):
        artefacts = index(process_record())
        record = evaluate_baseline(
            baseline(artefact_refs=[RECORD]), artefacts, self.tools
        )
        self.assertEqual(record["disposition"], "regenerating-artefact-absent")

    def test_a_mask_set_also_regenerates(self):
        artefacts = index(artefact(kind="mask-set"), process_record())
        record = evaluate_baseline(baseline(), artefacts, self.tools)
        self.assertEqual(record["disposition"], "regenerable")
        self.assertIn("mask-set", REGENERATING_ARTEFACT_KINDS)

    def test_artefact_defect_is_reported_before_a_tool_defect(self):
        artefacts = index(artefact(retention_state="purged"), process_record())
        record = evaluate_baseline(
            baseline(), artefacts, index(tool(availability="withdrawn"))
        )
        self.assertEqual(record["disposition"], "artefact-not-retained")

    def test_non_mapping_artefact_index_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_baseline(baseline(), [artefact()], self.tools)

    def test_non_positive_units_built_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_baseline(baseline(units_built=0), self.artefacts, self.tools)


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.artefacts = index(artefact(), process_record())
        self.tools = index(tool())

    def test_coverage_is_weighted_by_units_built(self):
        good = evaluate_baseline(baseline(), self.artefacts, self.tools)
        bad = evaluate_baseline(
            baseline(baseline_id="BL-2026-B", units_built=10, tool_refs=["T-GHOST"]),
            self.artefacts,
            self.tools,
        )
        self.assertAlmostEqual(regeneration_coverage([good, bad]), 0.8, places=9)

    def test_coverage_is_one_when_every_baseline_regenerates(self):
        good = evaluate_baseline(baseline(), self.artefacts, self.tools)
        self.assertAlmostEqual(regeneration_coverage([good]), 1.0, places=9)

    def test_empty_record_set_rejected(self):
        with self.assertRaises(ValueError):
            regeneration_coverage([])

    def test_record_without_a_disposition_rejected(self):
        with self.assertRaises(ValueError):
            regeneration_coverage([{"units_built": 4}])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "baselines": [baseline()],
            "artefacts": [artefact(), process_record()],
            "tools": [tool()],
        }
        spec.update(overrides)
        return spec

    def test_clean_system_is_conformant(self):
        result = assess_device_configuration_system(self._spec())
        self.assertEqual(result["verdict"], "conformant")
        self.assertTrue(result["conformant"])
        self.assertEqual(result["findings"], [])

    def test_one_unreproducible_baseline_makes_the_system_non_conformant(self):
        result = assess_device_configuration_system(
            self._spec(tools=[tool(version="current")])
        )
        self.assertEqual(result["verdict"], "non-conformant")
        self.assertEqual(result["findings"][0]["disposition"], "tool-version-unpinned")

    def test_findings_are_ranked_worst_first(self):
        result = assess_device_configuration_system(
            self._spec(
                baselines=[
                    baseline(baseline_id="BL-A", tool_refs=["T-GHOST"]),
                    baseline(baseline_id="BL-B", device_id=None),
                ]
            )
        )
        severities = [entry["severity"] for entry in result["findings"]]
        self.assertEqual(severities, sorted(severities))
        self.assertEqual(result["findings"][0]["disposition"], "record-incomplete")

    def test_coverage_weights_a_small_engineering_baseline_lightly(self):
        result = assess_device_configuration_system(
            self._spec(
                baselines=[
                    baseline(),
                    baseline(
                        baseline_id="BL-EM", units_built=10, artefact_refs=[RECORD]
                    ),
                ]
            )
        )
        self.assertAlmostEqual(result["regeneration_coverage"], 0.8, places=9)
        self.assertEqual(result["verdict"], "non-conformant")

    def test_exactly_met_coverage_still_holds_on_findings(self):
        result = assess_device_configuration_system(
            self._spec(
                baselines=[
                    baseline(),
                    baseline(
                        baseline_id="BL-EM", units_built=10, artefact_refs=[RECORD]
                    ),
                ],
                required_coverage=0.8,
            )
        )
        self.assertAlmostEqual(result["regeneration_coverage"], 0.8, places=9)
        self.assertEqual(result["verdict"], "non-conformant")

    def test_all_incomplete_set_reports_rather_than_raises(self):
        result = assess_device_configuration_system(
            self._spec(baselines=[baseline(units_built=None)])
        )
        self.assertAlmostEqual(result["regeneration_coverage"], 0.0, places=9)
        self.assertEqual(result["verdict"], "non-conformant")

    def test_duplicate_artefact_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_device_configuration_system(
                self._spec(artefacts=[artefact(), artefact(), process_record()])
            )

    def test_duplicate_tool_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_device_configuration_system(self._spec(tools=[tool(), tool()]))

    def test_baseline_released_twice_rejected(self):
        with self.assertRaises(ValueError):
            assess_device_configuration_system(
                self._spec(baselines=[baseline(), baseline()])
            )

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)

    def test_missing_tools_key_rejected(self):
        spec = self._spec()
        del spec["tools"]
        with self.assertRaises(ValueError):
            assess_device_configuration_system(spec)

    def test_empty_baseline_sequence_rejected(self):
        with self.assertRaises(ValueError):
            assess_device_configuration_system(self._spec(baselines=[]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_device_configuration_system(["baselines"])

    def test_out_of_range_required_coverage_rejected(self):
        with self.assertRaises(ValueError):
            assess_device_configuration_system(self._spec(required_coverage=1.3))

    def test_boolean_required_coverage_rejected(self):
        with self.assertRaises(ValueError):
            assess_device_configuration_system(self._spec(required_coverage=True))


if __name__ == "__main__":
    unittest.main()
