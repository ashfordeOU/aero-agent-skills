#!/usr/bin/env python3
"""Gate 3 contract test for e2001-permitted-detection-methods.

Offline, deterministic, stdlib unittest. Exercises the clause 7.2
catalogue logic: name resolution, facility-capability prerequisites,
item blocking-conditions, drive-mode gating, suite selection and the
latency-budget boundary.
"""

import unittest

from e2001_permitted_detection_methods_logic import (
    CATALOGUE,
    COVERAGE_SCOPES,
    blocking_conditions,
    canonical_technique,
    evaluate_technique,
    format_suite_report,
    normalize_drive_mode,
    permitted_catalogue,
    select_detection_suite,
    technique_record,
    techniques_by_coverage,
    unmet_prerequisites,
)

FULL_FACILITY = (
    "nulling-bridge",
    "phase-stable-reference",
    "harmonic-receiver",
    "harmonic-transparent-output",
    "spectrum-receiver",
    "low-residual-intermodulation-chain",
    "low-phase-noise-source",
    "biased-probe",
    "probe-feedthrough",
    "photodetector",
    "darkened-chamber",
    "fast-vacuum-gauge",
    "vented-region",
    "temperature-sensor",
)

CANDIDATES = (
    "forward-reflected-nulling",
    "harmonic-rise",
    "intermodulation-rise",
    "close-to-carrier-noise-rise",
    "electron-probe-current",
    "optical-emission",
    "gas-pressure-rise",
    "calorimetric-thermal-rise",
)


class TestNameResolution(unittest.TestCase):
    def test_canonical_names_resolve_to_themselves(self):
        for key in CATALOGUE:
            self.assertEqual(canonical_technique(key), key)

    def test_aliases_resolve(self):
        self.assertEqual(canonical_technique("nulling"), "forward-reflected-nulling")
        self.assertEqual(canonical_technique("Harmonics"), "harmonic-rise")
        self.assertEqual(
            canonical_technique("third-order-intermodulation"), "intermodulation-rise"
        )
        self.assertEqual(canonical_technique(" electron-probe "), "electron-probe-current")
        self.assertEqual(canonical_technique("pressure-rise"), "gas-pressure-rise")

    def test_unknown_technique_raises(self):
        with self.assertRaises(ValueError):
            canonical_technique("listening-carefully")

    def test_blank_technique_raises(self):
        with self.assertRaises(ValueError):
            canonical_technique("  ")

    def test_non_string_technique_raises(self):
        with self.assertRaises(ValueError):
            canonical_technique(42)

    def test_record_is_a_copy(self):
        record = technique_record("nulling")
        record["latency_ms"] = 999.0
        self.assertAlmostEqual(CATALOGUE["forward-reflected-nulling"]["latency_ms"], 0.05)


class TestCoveragePartition(unittest.TestCase):
    def test_global_scope_listing(self):
        names = techniques_by_coverage("global-coverage")
        self.assertIn("forward-reflected-nulling", names)
        self.assertIn("harmonic-rise", names)
        self.assertNotIn("electron-probe-current", names)

    def test_local_scope_listing(self):
        names = techniques_by_coverage("local-coverage")
        self.assertIn("optical-emission", names)
        self.assertIn("gas-pressure-rise", names)
        self.assertNotIn("harmonic-rise", names)

    def test_every_catalogue_entry_has_a_known_scope(self):
        for entry in CATALOGUE.values():
            self.assertIn(entry["coverage"], COVERAGE_SCOPES)

    def test_unknown_scope_raises(self):
        with self.assertRaises(ValueError):
            techniques_by_coverage("chamber-coverage")


class TestDriveMode(unittest.TestCase):
    def test_single_carrier_aliases(self):
        self.assertEqual(normalize_drive_mode("single-carrier"), "single-carrier-drive")
        self.assertEqual(
            normalize_drive_mode("Single-Carrier-Drive"), "single-carrier-drive"
        )

    def test_multi_carrier_aliases(self):
        self.assertEqual(normalize_drive_mode("multicarrier"), "multi-carrier-drive")
        self.assertEqual(normalize_drive_mode("multi-carrier"), "multi-carrier-drive")

    def test_unknown_drive_mode_raises(self):
        with self.assertRaises(ValueError):
            normalize_drive_mode("pulsed-ish")


class TestPrerequisitesAndBlockers(unittest.TestCase):
    def test_no_unmet_prerequisite_with_full_facility(self):
        self.assertEqual(unmet_prerequisites("optical-emission", FULL_FACILITY), [])

    def test_missing_capability_is_named(self):
        facility = [c for c in FULL_FACILITY if c != "darkened-chamber"]
        self.assertEqual(
            unmet_prerequisites("optical-emission", facility), ["darkened-chamber"]
        )

    def test_empty_facility_lists_every_need(self):
        self.assertEqual(
            unmet_prerequisites("forward-reflected-nulling", []),
            ["nulling-bridge", "phase-stable-reference"],
        )

    def test_facility_capabilities_must_be_iterable_tokens(self):
        with self.assertRaises(ValueError):
            unmet_prerequisites("optical-emission", "photodetector")

    def test_blank_capability_token_raises(self):
        with self.assertRaises(ValueError):
            unmet_prerequisites("optical-emission", ["photodetector", " "])

    def test_isolator_blocks_nulling(self):
        self.assertEqual(
            blocking_conditions("nulling", ["isolator-masks-reflection"]),
            ["isolator-masks-reflection"],
        )

    def test_output_filter_blocks_harmonic_rise(self):
        self.assertEqual(
            blocking_conditions("harmonic-rise", ["output-filter-attenuates-harmonics"]),
            ["output-filter-attenuates-harmonics"],
        )

    def test_sealed_region_blocks_probe_and_pressure(self):
        self.assertEqual(
            blocking_conditions("electron-probe-current", ["sealed-region"]),
            ["sealed-region"],
        )
        self.assertEqual(
            blocking_conditions("gas-pressure-rise", ["sealed-region"]),
            ["sealed-region"],
        )

    def test_unrelated_condition_does_not_block(self):
        self.assertEqual(blocking_conditions("harmonic-rise", ["sealed-region"]), [])


class TestTechniqueEvaluation(unittest.TestCase):
    def test_permitted_technique_has_no_reasons(self):
        result = evaluate_technique(
            "electron-probe-current", FULL_FACILITY, [], "single-carrier"
        )
        self.assertTrue(result["permitted"])
        self.assertEqual(result["reasons"], [])
        self.assertEqual(result["coverage"], "local-coverage")

    def test_intermodulation_is_rejected_under_single_carrier(self):
        result = evaluate_technique(
            "intermodulation-rise", FULL_FACILITY, [], "single-carrier"
        )
        self.assertFalse(result["permitted"])
        self.assertIn("observable absent under single-carrier-drive", result["reasons"])

    def test_intermodulation_is_permitted_under_multi_carrier(self):
        result = evaluate_technique(
            "intermodulation-rise", FULL_FACILITY, [], "multi-carrier"
        )
        self.assertTrue(result["permitted"])

    def test_blocked_and_unmet_reasons_accumulate(self):
        facility = [c for c in FULL_FACILITY if c != "nulling-bridge"]
        result = evaluate_technique(
            "forward-reflected-nulling",
            facility,
            ["isolator-masks-reflection"],
            "multi-carrier",
        )
        self.assertEqual(len(result["reasons"]), 2)

    def test_catalogue_ordering_is_by_latency(self):
        evaluated = permitted_catalogue(
            CANDIDATES, FULL_FACILITY, [], "multi-carrier"
        )
        latencies = [item["latency_ms"] for item in evaluated]
        self.assertEqual(latencies, sorted(latencies))

    def test_empty_candidate_list_raises(self):
        with self.assertRaises(ValueError):
            permitted_catalogue([], FULL_FACILITY, [], "multi-carrier")

    def test_duplicate_candidate_raises(self):
        with self.assertRaises(ValueError):
            permitted_catalogue(
                ["nulling", "forward-reflected-nulling"],
                FULL_FACILITY,
                [],
                "multi-carrier",
            )


class TestSuiteSelection(unittest.TestCase):
    def test_full_facility_yields_a_permitted_suite(self):
        report = select_detection_suite(
            CANDIDATES, FULL_FACILITY, [], "multi-carrier", 1.0
        )
        self.assertTrue(report["permitted"])
        self.assertEqual(
            report["selection"]["global-coverage"], "forward-reflected-nulling"
        )
        self.assertEqual(
            report["selection"]["local-coverage"], "electron-probe-current"
        )

    def test_on_budget_suite_is_permitted(self):
        report = select_detection_suite(
            CANDIDATES, FULL_FACILITY, [], "multi-carrier", 0.07
        )
        self.assertTrue(report["permitted"], report["findings"])
        self.assertAlmostEqual(report["total_latency_ms"], 0.07)

    def test_exact_latency_budget_boundary_absorbs_summation_error(self):
        # With nulling and harmonic-rise blocked under single-carrier
        # drive the suite is close-to-carrier-noise-rise (0.4 ms) plus
        # electron-probe-current (0.02 ms). That sum is 0.42 only to
        # within a ULP - it evaluates a hair ABOVE 0.42 in binary
        # floating point - yet the suite is physically on budget, so it
        # must pass without the budget being inflated.
        raw_sum = 0.4 + 0.02
        self.assertGreater(raw_sum, 0.42)
        report = select_detection_suite(
            CANDIDATES,
            FULL_FACILITY,
            ["isolator-masks-reflection", "output-filter-attenuates-harmonics"],
            "single-carrier",
            0.42,
        )
        self.assertEqual(
            report["selection"]["global-coverage"], "close-to-carrier-noise-rise"
        )
        self.assertEqual(report["selection"]["local-coverage"], "electron-probe-current")
        self.assertAlmostEqual(report["total_latency_ms"], 0.42)
        self.assertTrue(report["permitted"], report["findings"])

    def test_budget_one_step_below_the_boundary_still_fails(self):
        report = select_detection_suite(
            CANDIDATES,
            FULL_FACILITY,
            ["isolator-masks-reflection", "output-filter-attenuates-harmonics"],
            "single-carrier",
            0.41,
        )
        self.assertFalse(report["permitted"])
        self.assertTrue(
            any("latency-budget" in f for f in report["findings"]), report["findings"]
        )

    def test_budget_below_the_suite_is_a_finding(self):
        report = select_detection_suite(
            CANDIDATES, FULL_FACILITY, [], "multi-carrier", 0.01
        )
        self.assertFalse(report["permitted"])
        self.assertTrue(
            any("latency-budget" in f for f in report["findings"]), report["findings"]
        )

    def test_sealed_windowless_item_loses_local_coverage(self):
        report = select_detection_suite(
            CANDIDATES,
            FULL_FACILITY,
            ["sealed-region", "no-optical-view"],
            "multi-carrier",
            10.0,
        )
        self.assertIn(
            "no permitted primary technique for local-coverage", report["findings"]
        )

    def test_corroborating_technique_never_fills_a_scope(self):
        report = select_detection_suite(
            ["calorimetric-thermal-rise", "forward-reflected-nulling"],
            FULL_FACILITY,
            [],
            "single-carrier",
            10.0,
        )
        self.assertEqual(report["corroborating"], ["calorimetric-thermal-rise"])
        self.assertIn(
            "no permitted primary technique for local-coverage", report["findings"]
        )

    def test_isolator_pushes_global_coverage_to_the_next_technique(self):
        report = select_detection_suite(
            CANDIDATES,
            FULL_FACILITY,
            ["isolator-masks-reflection"],
            "multi-carrier",
            10.0,
        )
        self.assertEqual(report["selection"]["global-coverage"], "harmonic-rise")
        self.assertTrue(report["permitted"], report["findings"])

    def test_rejected_entries_carry_their_reasons(self):
        report = select_detection_suite(
            CANDIDATES, FULL_FACILITY, [], "single-carrier", 10.0
        )
        rejected = {item["technique"]: item["reasons"] for item in report["rejected"]}
        self.assertIn("intermodulation-rise", rejected)
        self.assertTrue(rejected["intermodulation-rise"])

    def test_zero_budget_raises(self):
        with self.assertRaises(ValueError):
            select_detection_suite(CANDIDATES, FULL_FACILITY, [], "multi-carrier", 0.0)

    def test_non_numeric_budget_raises(self):
        with self.assertRaises(ValueError):
            select_detection_suite(CANDIDATES, FULL_FACILITY, [], "multi-carrier", "1 ms")

    def test_boolean_budget_raises(self):
        with self.assertRaises(ValueError):
            select_detection_suite(CANDIDATES, FULL_FACILITY, [], "multi-carrier", True)

    def test_unknown_drive_mode_propagates(self):
        with self.assertRaises(ValueError):
            select_detection_suite(CANDIDATES, FULL_FACILITY, [], "swept", 10.0)

    def test_report_text_is_deterministic(self):
        first = format_suite_report(
            select_detection_suite(CANDIDATES, FULL_FACILITY, [], "multi-carrier", 1.0)
        )
        second = format_suite_report(
            select_detection_suite(CANDIDATES, FULL_FACILITY, [], "multi-carrier", 1.0)
        )
        self.assertEqual(first, second)
        self.assertIn("PERMITTED", first)

    def test_report_text_lists_findings(self):
        text = format_suite_report(
            select_detection_suite(
                CANDIDATES, FULL_FACILITY, ["sealed-region", "no-optical-view"],
                "multi-carrier", 10.0,
            )
        )
        self.assertIn("NOT PERMITTED", text)
        self.assertIn("FINDING:", text)


if __name__ == "__main__":
    unittest.main()
