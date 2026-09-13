"""Contract tests for the clause 6.2 process identification document logic."""

import copy
import unittest

from e2008_sca_process_identification_document_logic import (
    DOCUMENT_ACCEPTED,
    DOCUMENT_INCOMPLETE,
    PARAMETER_BAND_EXCLUDES_NOMINAL,
    PARAMETER_BAND_TOO_WIDE,
    PARAMETER_CONTROLLED,
    PROCESS_DOCUMENT_MISSING,
    PROCESS_ENTRY_ACCEPTED,
    PROCESS_EVIDENCE_MISSING,
    PROCESS_PARAMETER_DEFECT,
    PROCESS_PARAMETERS_MISSING,
    REQUIRED_SCA_PROCESSES,
    assess_control_parameter,
    assess_process_entry,
    assess_process_identification_document,
    document_precedes_campaign,
    process_coverage,
    validate_control_parameter,
    validate_identifier,
    validate_iso_date,
    validate_real,
)

# A welding parameter set a supplier would realistically write down: peak
# current, weld time and electrode force, each with a band around nominal.
WELD_PARAMETERS = [
    {"parameter": "weld-peak-current-a", "nominal": 250.0, "lower": 240.0,
     "upper": 260.0, "units": "A"},
    {"parameter": "weld-pulse-duration-ms", "nominal": 12.0, "lower": 11.4,
     "upper": 12.6, "units": "ms"},
    {"parameter": "electrode-force-n", "nominal": 40.0, "lower": 38.0,
     "upper": 42.0, "units": "N"},
]

GENERIC_PARAMETERS = [
    {"parameter": "bath-temperature-c", "nominal": 60.0, "lower": 57.0,
     "upper": 63.0, "units": "degC"},
]


def _entry(process, **overrides):
    criticality = REQUIRED_SCA_PROCESSES[process]
    entry = {
        "process": process,
        "controlling_document": "PCD-%s" % process,
        "control_parameters": copy.deepcopy(
            WELD_PARAMETERS if "welding" in process else GENERIC_PARAMETERS
        ),
    }
    if criticality == "qualification-critical":
        entry["qualification_evidence"] = "QR-%s-001" % process
    entry.update(overrides)
    return entry


def _spec(**overrides):
    spec = {
        "document_id": "SCA-PID-4471 rev B",
        "issue_date": "2026-02-10",
        "campaign_start_date": "2026-03-01",
        "processes": [_entry(p) for p in sorted(REQUIRED_SCA_PROCESSES)],
    }
    spec.update(overrides)
    return spec


def _replace(spec, process, **overrides):
    """Return spec with one declared process entry overridden."""
    out = copy.deepcopy(spec)
    for index, entry in enumerate(out["processes"]):
        if entry["process"] == process:
            entry.update(overrides)
            out["processes"][index] = entry
    return out


class ValidationHelperTests(unittest.TestCase):
    def test_identifier_is_trimmed(self):
        self.assertEqual(validate_identifier("  PCD-12  ", "doc"), "PCD-12")

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("   ", "doc")

    def test_non_string_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier(12, "doc")

    def test_boolean_rejected_as_a_real_number(self):
        with self.assertRaises(ValueError):
            validate_real(True, "nominal")

    def test_infinite_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_real(float("inf"), "nominal")

    def test_iso_date_parses(self):
        self.assertEqual(validate_iso_date("2026-03-01", "d").day, 1)

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            validate_iso_date("01-03-2026", "d")


class ControlParameterTests(unittest.TestCase):
    def test_valid_parameter_is_normalised(self):
        row = validate_control_parameter(WELD_PARAMETERS[0])
        self.assertEqual(row["parameter"], "weld-peak-current-a")
        self.assertAlmostEqual(row["upper"], 260.0, places=9)

    def test_missing_band_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_parameter({"parameter": "p", "nominal": 1.0, "lower": 0.5})

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_parameter(
                {"parameter": "p", "nominal": 1.0, "lower": 2.0, "upper": 0.5}
            )

    def test_non_mapping_parameter_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_parameter(["weld-peak-current-a"])

    def test_narrow_band_is_controlled(self):
        row = assess_control_parameter(WELD_PARAMETERS[0])
        self.assertEqual(row["verdict"], PARAMETER_CONTROLLED)
        self.assertAlmostEqual(row["relative_band"], 0.08, places=9)

    def test_band_exactly_on_the_policy_limit_is_controlled(self):
        row = assess_control_parameter(
            {"parameter": "p", "nominal": 100.0, "lower": 90.0, "upper": 110.0}
        )
        self.assertAlmostEqual(row["relative_band"], 0.20, places=9)
        self.assertEqual(row["verdict"], PARAMETER_CONTROLLED)

    def test_band_wider_than_the_policy_limit_controls_nothing(self):
        row = assess_control_parameter(
            {"parameter": "p", "nominal": 100.0, "lower": 70.0, "upper": 130.0}
        )
        self.assertEqual(row["verdict"], PARAMETER_BAND_TOO_WIDE)

    def test_band_that_does_not_bracket_the_nominal_is_a_defect(self):
        row = assess_control_parameter(
            {"parameter": "p", "nominal": 100.0, "lower": 101.0, "upper": 104.0}
        )
        self.assertEqual(row["verdict"], PARAMETER_BAND_EXCLUDES_NOMINAL)
        self.assertFalse(row["brackets_nominal"])

    def test_nominal_sitting_on_a_band_edge_still_brackets(self):
        row = assess_control_parameter(
            {"parameter": "p", "nominal": 100.0, "lower": 100.0, "upper": 110.0}
        )
        self.assertTrue(row["brackets_nominal"])

    def test_zero_nominal_has_no_relative_band(self):
        row = assess_control_parameter(
            {"parameter": "p", "nominal": 0.0, "lower": -1.0, "upper": 1.0}
        )
        self.assertIsNone(row["relative_band"])
        self.assertEqual(row["verdict"], PARAMETER_CONTROLLED)

    def test_band_limit_is_read_from_policy(self):
        row = assess_control_parameter(
            {"parameter": "p", "nominal": 100.0, "lower": 95.0, "upper": 105.0},
            {"max_relative_band": 0.05},
        )
        self.assertEqual(row["verdict"], PARAMETER_BAND_TOO_WIDE)


class ProcessEntryTests(unittest.TestCase):
    def test_complete_critical_entry_is_accepted(self):
        row = assess_process_entry(_entry("sca-cell-interconnector-welding"))
        self.assertEqual(row["verdict"], PROCESS_ENTRY_ACCEPTED)
        self.assertEqual(row["criticality"], "qualification-critical")

    def test_unknown_process_is_refused_not_carried(self):
        with self.assertRaises(ValueError):
            entry = _entry("sca-coverglass-bonding")
            entry["process"] = "sca-cell-painting"
            assess_process_entry(entry)

    def test_entry_without_a_controlling_document_is_ranked_worst(self):
        row = assess_process_entry(
            _entry("sca-coverglass-bonding", controlling_document=None)
        )
        self.assertEqual(row["verdict"], PROCESS_DOCUMENT_MISSING)
        self.assertEqual(row["rank"], 0)

    def test_entry_with_no_parameters_holds_nothing(self):
        row = assess_process_entry(
            _entry("sca-bus-bar-attachment", control_parameters=[])
        )
        self.assertEqual(row["verdict"], PROCESS_PARAMETERS_MISSING)

    def test_uncontrolled_parameter_names_the_offender(self):
        bad = copy.deepcopy(WELD_PARAMETERS)
        bad[1]["upper"] = 30.0
        row = assess_process_entry(
            _entry("sca-cell-interconnector-welding", control_parameters=bad)
        )
        self.assertEqual(row["verdict"], PROCESS_PARAMETER_DEFECT)
        self.assertIn("weld-pulse-duration-ms", row["defective_parameters"])

    def test_critical_process_without_evidence_is_flagged(self):
        row = assess_process_entry(
            _entry("sca-bypass-diode-attachment", qualification_evidence=None)
        )
        self.assertEqual(row["verdict"], PROCESS_EVIDENCE_MISSING)

    def test_control_only_process_closes_without_evidence(self):
        row = assess_process_entry(_entry("sca-cleaning-and-handling"))
        self.assertEqual(row["verdict"], PROCESS_ENTRY_ACCEPTED)
        self.assertFalse(row["evidence_required"])

    def test_policy_can_demand_evidence_from_every_process(self):
        row = assess_process_entry(
            _entry("sca-cleaning-and-handling"),
            {"require_evidence_for_control_only": True},
        )
        self.assertEqual(row["verdict"], PROCESS_EVIDENCE_MISSING)

    def test_duplicate_parameter_names_rejected(self):
        duplicated = copy.deepcopy(WELD_PARAMETERS) + [copy.deepcopy(WELD_PARAMETERS[0])]
        with self.assertRaises(ValueError):
            assess_process_entry(
                _entry("sca-cell-interconnector-welding", control_parameters=duplicated)
            )

    def test_missing_document_outranks_a_parameter_defect(self):
        bad = copy.deepcopy(GENERIC_PARAMETERS)
        bad[0]["upper"] = 500.0
        row = assess_process_entry(
            _entry(
                "sca-bus-bar-attachment",
                controlling_document=None,
                control_parameters=bad,
            )
        )
        self.assertEqual(row["verdict"], PROCESS_DOCUMENT_MISSING)


class CoverageTests(unittest.TestCase):
    def test_full_declaration_covers_the_required_set(self):
        entries = [{"process": p} for p in REQUIRED_SCA_PROCESSES]
        coverage = process_coverage(entries)
        self.assertAlmostEqual(coverage["coverage_share"], 1.0, places=9)
        self.assertEqual(coverage["undeclared_processes"], [])

    def test_undeclared_process_is_named(self):
        entries = [
            {"process": p} for p in REQUIRED_SCA_PROCESSES if p != "sca-coverglass-bonding"
        ]
        coverage = process_coverage(entries)
        self.assertEqual(coverage["undeclared_processes"], ["sca-coverglass-bonding"])
        self.assertLess(coverage["coverage_share"], 1.0)

    def test_entry_without_a_process_key_rejected(self):
        with self.assertRaises(ValueError):
            process_coverage([{"controlling_document": "PCD-1"}])


class CapturePrecedenceTests(unittest.TestCase):
    def test_document_issued_before_the_campaign(self):
        self.assertTrue(document_precedes_campaign("2026-02-10", "2026-03-01"))

    def test_document_issued_on_the_campaign_start_date(self):
        self.assertTrue(document_precedes_campaign("2026-03-01", "2026-03-01"))

    def test_document_issued_after_the_campaign_started(self):
        self.assertFalse(document_precedes_campaign("2026-03-02", "2026-03-01"))


class DocumentAssessmentTests(unittest.TestCase):
    def test_clean_document_is_accepted(self):
        result = assess_process_identification_document(_spec())
        self.assertEqual(result["verdict"], DOCUMENT_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["accepted_share"], 1.0, places=9)

    def test_undeclared_process_fails_the_document(self):
        spec = _spec()
        spec["processes"] = [
            e for e in spec["processes"] if e["process"] != "sca-coverglass-bonding"
        ]
        result = assess_process_identification_document(spec)
        self.assertEqual(result["verdict"], DOCUMENT_INCOMPLETE)
        self.assertFalse(result["coverage_met"])
        self.assertTrue(
            any("sca-coverglass-bonding" in f for f in result["findings"])
        )

    def test_missing_evidence_reaches_the_findings(self):
        spec = _replace(_spec(), "sca-cell-to-substrate-bonding", qualification_evidence=None)
        result = assess_process_identification_document(spec)
        self.assertEqual(result["verdict"], DOCUMENT_INCOMPLETE)
        self.assertIn(
            "sca-cell-to-substrate-bonding",
            result["entries_by_verdict"][PROCESS_EVIDENCE_MISSING],
        )

    def test_late_issue_is_a_finding_of_its_own(self):
        result = assess_process_identification_document(
            _spec(issue_date="2026-03-15")
        )
        self.assertFalse(result["issued_before_campaign"])
        self.assertTrue(any("issued after" in f for f in result["findings"]))

    def test_entries_are_grouped_by_verdict(self):
        spec = _replace(_spec(), "sca-bus-bar-attachment", controlling_document=None)
        result = assess_process_identification_document(spec)
        grouped = result["entries_by_verdict"]
        self.assertEqual(grouped[PROCESS_DOCUMENT_MISSING], ["sca-bus-bar-attachment"])
        self.assertEqual(len(grouped[PROCESS_ENTRY_ACCEPTED]), 6)

    def test_accepted_share_drops_with_a_defective_entry(self):
        spec = _replace(_spec(), "sca-bus-bar-attachment", controlling_document=None)
        result = assess_process_identification_document(spec)
        self.assertAlmostEqual(result["accepted_share"], 6.0 / 7.0, places=9)

    def test_duplicate_process_entries_rejected(self):
        spec = _spec()
        spec["processes"] = spec["processes"] + [_entry("sca-coverglass-bonding")]
        with self.assertRaises(ValueError):
            assess_process_identification_document(spec)

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["campaign_start_date"]
        with self.assertRaises(ValueError):
            assess_process_identification_document(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_process_identification_document(["SCA-PID-4471"])

    def test_empty_process_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_process_identification_document(_spec(processes=[]))

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_process_identification_document(_spec(policy={"max_band": 0.1}))

    def test_coverage_policy_below_one_accepts_a_partial_document(self):
        spec = _spec(policy={"min_process_coverage": 0.5})
        spec["processes"] = [
            e for e in spec["processes"] if e["process"] != "sca-cleaning-and-handling"
        ]
        result = assess_process_identification_document(spec)
        self.assertTrue(result["coverage_met"])
        self.assertEqual(result["verdict"], DOCUMENT_INCOMPLETE)

    def test_document_id_is_trimmed_in_the_report(self):
        result = assess_process_identification_document(
            _spec(document_id="  SCA-PID-4471 rev B  ")
        )
        self.assertEqual(result["document_id"], "SCA-PID-4471 rev B")


if __name__ == "__main__":
    unittest.main()
