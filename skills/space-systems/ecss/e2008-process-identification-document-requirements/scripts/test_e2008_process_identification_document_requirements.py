#!/usr/bin/env python3
"""Contract test for process identification document content, Annex F (offline)."""

import copy
import unittest

from e2008_process_identification_document_requirements_logic import (
    DEFAULT_PID_CONTENT_POLICY,
    DOCUMENT_ACCEPTABLE,
    DOCUMENT_NOT_ACCEPTABLE,
    PARAMETER_BAND_DEGENERATE,
    PARAMETER_BAND_TOO_WIDE,
    PARAMETER_UNBOUNDED,
    PARAMETER_UNBRACKETED,
    PARAMETER_USABLE,
    PROCESS_DESCRIBED,
    PROCESS_FIELDS_MISSING,
    PROCESS_PARAMETER_UNUSABLE,
    PROCESS_PARAMETERS_THIN,
    PROCESS_UNINSTRUCTED,
    REQUIRED_DOCUMENT_SECTIONS,
    REQUIRED_PROCESS_FIELDS,
    SEQUENCE_DUPLICATED,
    SEQUENCE_GAPPED,
    SEQUENCE_ORDERED,
    absent_gated_fields,
    assess_control_parameter,
    assess_process_identification_document,
    assess_process_record,
    assess_process_sequence,
    audit_document_sections,
    audit_process_fields,
    required_document_sections,
    required_process_fields,
    validate_pid_content_policy,
)

PROCESS_IDS = (
    "assembly-surface-preparation",
    "assembly-interconnector-welding",
    "assembly-coverglass-bonding",
)


def _parameter(**overrides):
    parameter = {
        "name": "weld-energy-j",
        "nominal": 10.0,
        "minimum": 9.0,
        "maximum": 11.0,
    }
    parameter.update(overrides)
    return parameter


def _process(process_id, sequence, **overrides):
    process = {
        "process_id": process_id,
        "description": "described step by step with its acceptance condition",
        "sequence": sequence,
        "facility_or_line": "assembly line two, cleanroom bay",
        "equipment": "parallel gap welder, serial recorded per shift",
        "materials_and_consumables": "silver interconnector stock, adhesive batch controlled",
        "control_parameters": [_parameter()],
        "in_process_inspection": "visual and pull sample per panel",
        "operator_qualification": "certified operator, currency re-checked yearly",
        "work_instruction_ref": "wi-0412 issue D",
    }
    process.update(overrides)
    return process


def _document(processes=None, **overrides):
    built = (
        processes
        if processes is not None
        else [_process(pid, i + 1) for i, pid in enumerate(PROCESS_IDS)]
    )
    document = {
        "document_identifier": "pid-asm-0088",
        "issue_and_date": "issue A, 2026-04-19",
        "preparing_organisation": "assembly supplier, production engineering",
        "product_applicability": "solar cell assembly build standard 3",
        "process_list": list(PROCESS_IDS),
        "process_flow_sequence": "preparation, welding, bonding",
        "change_control_statement": "changes raised and agreed before any build",
        "approval_record": "signed by production and quality",
        "processes": built,
    }
    document.update(overrides)
    return document


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_pid_content_policy(DEFAULT_PID_CONTENT_POLICY),
            DEFAULT_PID_CONTENT_POLICY,
        )

    def test_default_policy_demands_every_section(self):
        self.assertAlmostEqual(
            DEFAULT_PID_CONTENT_POLICY["min_section_fraction"], 1.0, places=9
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_pid_content_policy("write it all down")

    def test_a_zero_parameter_floor_rejected(self):
        broken = copy.deepcopy(DEFAULT_PID_CONTENT_POLICY)
        broken["min_control_parameters_per_process"] = 0
        with self.assertRaises(ValueError):
            validate_pid_content_policy(broken)

    def test_a_zero_band_ceiling_rejected(self):
        broken = copy.deepcopy(DEFAULT_PID_CONTENT_POLICY)
        broken["max_parameter_band_fraction"] = 0.0
        with self.assertRaises(ValueError):
            validate_pid_content_policy(broken)

    def test_a_non_boolean_sequence_switch_rejected(self):
        broken = copy.deepcopy(DEFAULT_PID_CONTENT_POLICY)
        broken["require_contiguous_sequence"] = "yes"
        with self.assertRaises(ValueError):
            validate_pid_content_policy(broken)


class RequiredSetTests(unittest.TestCase):
    def test_section_set_is_returned_as_a_tuple_copy(self):
        sections = required_document_sections()
        self.assertEqual(sections, REQUIRED_DOCUMENT_SECTIONS)
        self.assertIsInstance(sections, tuple)

    def test_field_set_is_returned_as_a_tuple_copy(self):
        fields = required_process_fields()
        self.assertEqual(fields, REQUIRED_PROCESS_FIELDS)
        self.assertIsInstance(fields, tuple)

    def test_field_set_carries_equipment_and_control_parameters(self):
        fields = required_process_fields()
        self.assertIn("equipment", fields)
        self.assertIn("control_parameters", fields)


class SectionAuditTests(unittest.TestCase):
    def test_a_full_document_is_missing_nothing(self):
        self.assertEqual(audit_document_sections(_document()), [])

    def test_a_dropped_section_is_named(self):
        document = _document()
        del document["change_control_statement"]
        self.assertEqual(
            audit_document_sections(document), ["change_control_statement"]
        )

    def test_a_blank_section_counts_as_absent(self):
        self.assertEqual(
            audit_document_sections(_document(approval_record="   ")),
            ["approval_record"],
        )

    def test_an_empty_process_list_counts_as_absent(self):
        self.assertEqual(
            audit_document_sections(_document(process_list=[])), ["process_list"]
        )

    def test_non_mapping_document_rejected(self):
        with self.assertRaises(ValueError):
            audit_document_sections("a document")


class ProcessFieldAuditTests(unittest.TestCase):
    def test_a_full_process_is_missing_nothing(self):
        self.assertEqual(audit_process_fields(_process(PROCESS_IDS[0], 1)), [])

    def test_a_dropped_equipment_field_is_named(self):
        process = _process(PROCESS_IDS[0], 1)
        del process["equipment"]
        self.assertEqual(audit_process_fields(process), ["equipment"])

    def test_an_empty_parameter_list_is_named(self):
        process = _process(PROCESS_IDS[0], 1, control_parameters=[])
        self.assertEqual(audit_process_fields(process), ["control_parameters"])

    def test_a_non_integer_sequence_is_named(self):
        process = _process(PROCESS_IDS[0], 1)
        process["sequence"] = "first"
        self.assertEqual(audit_process_fields(process), ["sequence"])

    def test_gated_fields_are_absent_only_when_policy_asks(self):
        process = _process(PROCESS_IDS[0], 1)
        del process["operator_qualification"]
        self.assertEqual(absent_gated_fields(process), ["operator_qualification"])
        policy = copy.deepcopy(DEFAULT_PID_CONTENT_POLICY)
        policy["require_operator_qualification"] = False
        self.assertEqual(absent_gated_fields(process, policy), [])

    def test_non_mapping_process_rejected(self):
        with self.assertRaises(ValueError):
            audit_process_fields("a process")


class ControlParameterTests(unittest.TestCase):
    def test_a_banded_parameter_is_usable(self):
        result = assess_control_parameter(_parameter())
        self.assertEqual(result["verdict"], PARAMETER_USABLE)
        self.assertTrue(result["usable"])

    def test_the_band_fraction_is_reported(self):
        result = assess_control_parameter(_parameter())
        self.assertAlmostEqual(result["band_fraction"], 0.2, places=9)

    def test_a_band_exactly_on_the_ceiling_is_accepted(self):
        result = assess_control_parameter(
            _parameter(nominal=10.0, minimum=7.5, maximum=12.5)
        )
        self.assertEqual(result["verdict"], PARAMETER_USABLE)
        self.assertAlmostEqual(result["band_fraction"], 0.5, places=9)

    def test_a_parameter_with_no_band_is_unbounded(self):
        parameter = _parameter()
        del parameter["maximum"]
        self.assertEqual(
            assess_control_parameter(parameter)["verdict"], PARAMETER_UNBOUNDED
        )

    def test_a_band_that_misses_its_nominal_is_unbracketed(self):
        result = assess_control_parameter(
            _parameter(nominal=10.0, minimum=11.0, maximum=12.0)
        )
        self.assertEqual(result["verdict"], PARAMETER_UNBRACKETED)

    def test_a_zero_width_band_is_degenerate(self):
        result = assess_control_parameter(
            _parameter(nominal=10.0, minimum=10.0, maximum=10.0)
        )
        self.assertEqual(result["verdict"], PARAMETER_BAND_DEGENERATE)

    def test_a_band_wider_than_the_ceiling_is_named(self):
        result = assess_control_parameter(
            _parameter(nominal=10.0, minimum=2.0, maximum=18.0)
        )
        self.assertEqual(result["verdict"], PARAMETER_BAND_TOO_WIDE)

    def test_a_zero_nominal_skips_the_width_test(self):
        result = assess_control_parameter(
            _parameter(name="bias-offset-v", nominal=0.0, minimum=-1.0, maximum=1.0)
        )
        self.assertIsNone(result["band_fraction"])
        self.assertEqual(result["verdict"], PARAMETER_USABLE)

    def test_a_negative_nominal_uses_its_magnitude(self):
        result = assess_control_parameter(
            _parameter(name="bake-offset-c", nominal=-20.0, minimum=-22.0, maximum=-18.0)
        )
        self.assertAlmostEqual(result["band_fraction"], 0.2, places=9)

    def test_an_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            assess_control_parameter(_parameter(minimum=12.0, maximum=8.0))

    def test_a_parameter_without_a_name_rejected(self):
        parameter = _parameter()
        del parameter["name"]
        with self.assertRaises(ValueError):
            assess_control_parameter(parameter)

    def test_non_mapping_parameter_rejected(self):
        with self.assertRaises(ValueError):
            assess_control_parameter("10 J")


class SequenceTests(unittest.TestCase):
    def test_a_contiguous_run_is_ordered(self):
        processes = [_process(pid, i + 1) for i, pid in enumerate(PROCESS_IDS)]
        result = assess_process_sequence(processes)
        self.assertEqual(result["verdict"], SEQUENCE_ORDERED)
        self.assertTrue(result["ordered"])

    def test_a_repeated_position_is_named(self):
        processes = [_process(pid, 1) for pid in PROCESS_IDS]
        result = assess_process_sequence(processes)
        self.assertEqual(result["verdict"], SEQUENCE_DUPLICATED)
        self.assertEqual(result["duplicate_positions"], [1])

    def test_a_skipped_position_is_named(self):
        processes = [
            _process(PROCESS_IDS[0], 1),
            _process(PROCESS_IDS[1], 2),
            _process(PROCESS_IDS[2], 4),
        ]
        result = assess_process_sequence(processes)
        self.assertEqual(result["verdict"], SEQUENCE_GAPPED)
        self.assertEqual(result["missing_positions"], [3])

    def test_a_position_beyond_the_run_is_named(self):
        processes = [
            _process(PROCESS_IDS[0], 1),
            _process(PROCESS_IDS[1], 2),
            _process(PROCESS_IDS[2], 9),
        ]
        result = assess_process_sequence(processes)
        self.assertEqual(result["out_of_range_positions"], [9])

    def test_a_non_integer_position_rejected(self):
        processes = [_process(PROCESS_IDS[0], 1), _process(PROCESS_IDS[1], "two")]
        with self.assertRaises(ValueError):
            assess_process_sequence(processes)

    def test_an_empty_process_sequence_rejected(self):
        with self.assertRaises(ValueError):
            assess_process_sequence([])


class ProcessRecordTests(unittest.TestCase):
    def test_a_full_process_is_described(self):
        result = assess_process_record(_process(PROCESS_IDS[0], 1))
        self.assertEqual(result["verdict"], PROCESS_DESCRIBED)
        self.assertTrue(result["described"])

    def test_a_missing_field_outranks_an_unusable_parameter(self):
        process = _process(
            PROCESS_IDS[0], 1, equipment="", control_parameters=[_parameter(minimum=11.0, maximum=12.0)]
        )
        self.assertEqual(
            assess_process_record(process)["verdict"], PROCESS_FIELDS_MISSING
        )

    def test_a_thin_parameter_set_outranks_an_unusable_parameter(self):
        policy = copy.deepcopy(DEFAULT_PID_CONTENT_POLICY)
        policy["min_control_parameters_per_process"] = 3
        process = _process(
            PROCESS_IDS[0], 1, control_parameters=[_parameter(minimum=11.0, maximum=12.0)]
        )
        self.assertEqual(
            assess_process_record(process, policy)["verdict"], PROCESS_PARAMETERS_THIN
        )

    def test_an_unusable_parameter_outranks_a_missing_instruction(self):
        process = _process(
            PROCESS_IDS[0],
            1,
            control_parameters=[_parameter(minimum=11.0, maximum=12.0)],
            work_instruction_ref="",
        )
        result = assess_process_record(process)
        self.assertEqual(result["verdict"], PROCESS_PARAMETER_UNUSABLE)
        self.assertEqual(result["unusable_parameters"], ["weld-energy-j"])

    def test_a_missing_instruction_reference_is_uninstructed(self):
        process = _process(PROCESS_IDS[0], 1, work_instruction_ref="")
        self.assertEqual(
            assess_process_record(process)["verdict"], PROCESS_UNINSTRUCTED
        )

    def test_a_relaxed_policy_admits_a_process_with_no_instruction(self):
        policy = copy.deepcopy(DEFAULT_PID_CONTENT_POLICY)
        policy["require_work_instruction_reference"] = False
        process = _process(PROCESS_IDS[0], 1, work_instruction_ref="")
        self.assertEqual(
            assess_process_record(process, policy)["verdict"], PROCESS_DESCRIBED
        )

    def test_a_process_without_an_identifier_rejected(self):
        process = _process(PROCESS_IDS[0], 1)
        del process["process_id"]
        with self.assertRaises(ValueError):
            assess_process_record(process)


class DocumentSweepTests(unittest.TestCase):
    def test_a_full_document_is_acceptable(self):
        result = assess_process_identification_document(_document())
        self.assertEqual(result["verdict"], DOCUMENT_ACCEPTABLE)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["every_section_present"])

    def test_a_full_document_carries_every_section(self):
        result = assess_process_identification_document(_document())
        self.assertAlmostEqual(result["stated_section_fraction"], 1.0, places=9)

    def test_a_missing_section_blocks_acceptance(self):
        document = _document()
        del document["change_control_statement"]
        result = assess_process_identification_document(document)
        self.assertEqual(result["verdict"], DOCUMENT_NOT_ACCEPTABLE)
        self.assertEqual(result["missing_sections"], ["change_control_statement"])

    def test_the_stated_section_fraction_is_reported(self):
        document = _document()
        del document["change_control_statement"]
        result = assess_process_identification_document(document)
        self.assertAlmostEqual(
            result["stated_section_fraction"],
            (len(REQUIRED_DOCUMENT_SECTIONS) - 1)
            / float(len(REQUIRED_DOCUMENT_SECTIONS)),
            places=9,
        )

    def test_a_listed_but_undescribed_process_is_named(self):
        document = _document(process_list=list(PROCESS_IDS) + ["assembly-final-clean"])
        result = assess_process_identification_document(document)
        self.assertEqual(result["listed_but_undescribed"], ["assembly-final-clean"])
        self.assertEqual(result["verdict"], DOCUMENT_NOT_ACCEPTABLE)

    def test_a_described_but_unlisted_process_is_named(self):
        document = _document(process_list=list(PROCESS_IDS[:2]))
        result = assess_process_identification_document(document)
        self.assertEqual(result["described_but_unlisted"], [PROCESS_IDS[2]])

    def test_a_broken_flow_blocks_acceptance(self):
        processes = [
            _process(PROCESS_IDS[0], 1),
            _process(PROCESS_IDS[1], 2),
            _process(PROCESS_IDS[2], 4),
        ]
        result = assess_process_identification_document(_document(processes))
        self.assertEqual(result["process_sequence"]["verdict"], SEQUENCE_GAPPED)
        self.assertEqual(result["verdict"], DOCUMENT_NOT_ACCEPTABLE)

    def test_a_relaxed_policy_admits_a_broken_flow(self):
        processes = [
            _process(PROCESS_IDS[0], 1),
            _process(PROCESS_IDS[1], 2),
            _process(PROCESS_IDS[2], 4),
        ]
        policy = copy.deepcopy(DEFAULT_PID_CONTENT_POLICY)
        policy["require_contiguous_sequence"] = False
        result = assess_process_identification_document(_document(processes), policy)
        self.assertEqual(result["verdict"], DOCUMENT_ACCEPTABLE)

    def test_open_processes_are_listed(self):
        processes = [_process(pid, i + 1) for i, pid in enumerate(PROCESS_IDS)]
        processes[1]["work_instruction_ref"] = ""
        result = assess_process_identification_document(_document(processes))
        self.assertEqual(result["open_process_ids"], [PROCESS_IDS[1]])

    def test_processes_are_grouped_by_verdict(self):
        processes = [_process(pid, i + 1) for i, pid in enumerate(PROCESS_IDS)]
        processes[0]["equipment"] = ""
        result = assess_process_identification_document(_document(processes))
        self.assertEqual(
            result["grouped_by_verdict"][PROCESS_FIELDS_MISSING], [PROCESS_IDS[0]]
        )

    def test_assessments_come_back_in_identifier_order(self):
        result = assess_process_identification_document(_document())
        ids = [entry["process_id"] for entry in result["process_assessments"]]
        self.assertEqual(ids, sorted(ids))

    def test_a_repeated_process_identifier_rejected(self):
        processes = [_process(PROCESS_IDS[0], 1), _process(PROCESS_IDS[0], 2)]
        with self.assertRaises(ValueError):
            assess_process_identification_document(_document(processes))

    def test_an_empty_process_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_process_identification_document(_document([]))

    def test_a_document_without_an_identifier_rejected(self):
        document = _document()
        del document["document_identifier"]
        with self.assertRaises(ValueError):
            assess_process_identification_document(document)

    def test_non_mapping_document_rejected_by_the_sweep(self):
        with self.assertRaises(ValueError):
            assess_process_identification_document([_process(PROCESS_IDS[0], 1)])

    def test_findings_name_the_document(self):
        document = _document()
        del document["change_control_statement"]
        result = assess_process_identification_document(document)
        self.assertTrue(any("pid-asm-0088" in item for item in result["findings"]))


if __name__ == "__main__":
    unittest.main()
