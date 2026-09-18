"""Contract tests for the clause 6.6 operational safety logic."""

import unittest

from q40_operational_safety_logic import (
    CONTROL_PRECEDENCE,
    FLIGHT_PHASES,
    GROUND_PHASES,
    MAXIMUM_CONTROL_RANK,
    OPERATIONAL_PHASES,
    SEVERITY_ORDER,
    assess_operation,
    assess_operational_safety,
    control_rank,
    maximum_control_rank,
    phase_coverage,
    reaction_margin_s,
    reaction_status,
    validate_control_type,
    validate_operation,
    validate_phase,
    validate_severity,
)


def operation(identifier="OP-1", phase="handling", severity="critical",
              control_type="engineered-safety-device", **kwargs):
    """Build an operation record with sensible defaults."""
    record = {
        "id": identifier,
        "phase": phase,
        "hazard": kwargs.pop("hazard", "lifted mass over personnel"),
        "severity": severity,
        "control_type": control_type,
        "verification": kwargs.pop("verification", "proof-load certificate"),
    }
    record.update(kwargs)
    return record


def flight_operation(**kwargs):
    """Build a flight-phase constraint with a reaction-time budget."""
    defaults = {
        "identifier": "OP-F1",
        "phase": "mission-control",
        "severity": "critical",
        "control_type": "engineered-safety-device",
        "available_time_s": 120.0,
        "required_reaction_time_s": 30.0,
    }
    defaults.update(kwargs)
    identifier = defaults.pop("identifier")
    return operation(identifier, **defaults)


class PhaseTests(unittest.TestCase):
    def test_ground_and_flight_phases_do_not_overlap(self):
        self.assertEqual(set(GROUND_PHASES) & set(FLIGHT_PHASES), set())

    def test_operational_phases_are_the_union(self):
        self.assertEqual(OPERATIONAL_PHASES, GROUND_PHASES + FLIGHT_PHASES)

    def test_phase_is_trimmed_and_lowered(self):
        self.assertEqual(validate_phase("  Transport "), "transport")

    def test_unknown_phase_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase("storage")

    def test_severity_is_validated(self):
        self.assertEqual(validate_severity("MAJOR"), "major")

    def test_severity_table_covers_every_severity(self):
        self.assertEqual(sorted(MAXIMUM_CONTROL_RANK), sorted(SEVERITY_ORDER))


class PrecedenceTests(unittest.TestCase):
    def test_precedence_runs_strongest_first(self):
        self.assertEqual(CONTROL_PRECEDENCE[0], "design-elimination")
        self.assertEqual(CONTROL_PRECEDENCE[-1], "procedure-and-training")

    def test_rank_is_the_position_in_the_precedence(self):
        self.assertEqual(control_rank("design-elimination"), 0)
        self.assertEqual(control_rank("procedure-and-training"), 3)

    def test_unknown_control_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_type("checklist")

    def test_catastrophic_may_not_rest_on_a_warning_device(self):
        self.assertLess(maximum_control_rank("catastrophic"),
                        control_rank("warning-device"))

    def test_minor_may_rest_on_procedure(self):
        self.assertEqual(maximum_control_rank("minor"), control_rank("procedure-and-training"))


class ReactionMarginTests(unittest.TestCase):
    def test_margin_is_available_minus_required(self):
        self.assertAlmostEqual(reaction_margin_s(120.0, 30.0), 90.0, places=9)

    def test_positive_margin_reads_positive(self):
        self.assertEqual(reaction_status(reaction_margin_s(120.0, 30.0)), "positive")

    def test_equal_times_read_as_exhausted(self):
        margin = reaction_margin_s(45.0, 45.0)
        self.assertAlmostEqual(margin, 0.0, places=9)
        self.assertEqual(reaction_status(margin), "exhausted")

    def test_required_beyond_available_reads_negative(self):
        self.assertEqual(reaction_status(reaction_margin_s(20.0, 45.0)), "negative")

    def test_zero_available_time_rejected(self):
        with self.assertRaises(ValueError):
            reaction_margin_s(0.0, 30.0)

    def test_non_numeric_time_rejected(self):
        with self.assertRaises(ValueError):
            reaction_margin_s("120", 30.0)

    def test_non_finite_margin_rejected(self):
        with self.assertRaises(ValueError):
            reaction_status(float("inf"))


class ValidationTests(unittest.TestCase):
    def test_valid_record_normalises_tokens(self):
        record = validate_operation(operation(phase=" HANDLING "))
        self.assertEqual(record["phase"], "handling")

    def test_unknown_key_rejected(self):
        bad = operation()
        bad["crane_id"] = "C-4"
        with self.assertRaises(ValueError):
            validate_operation(bad)

    def test_blank_hazard_rejected(self):
        with self.assertRaises(ValueError):
            validate_operation(operation(hazard="   "))

    def test_blank_verification_rejected(self):
        with self.assertRaises(ValueError):
            validate_operation(operation(verification="  "))

    def test_absent_control_is_allowed_at_validation(self):
        record = validate_operation(operation(control_type=None, verification=None))
        self.assertIsNone(record["control_type"])

    def test_non_boolean_personnel_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_operation(operation(personnel_exposed="yes"))

    def test_negative_available_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_operation(operation(available_time_s=-1.0))


class GroundOperationTests(unittest.TestCase):
    def test_engineered_control_on_a_critical_hazard_is_clean(self):
        row = assess_operation(operation())
        self.assertEqual(row["findings"], [])
        self.assertEqual(row["phase_set"], "ground")

    def test_uncontrolled_hazard_is_a_finding(self):
        row = assess_operation(operation(control_type=None, verification=None))
        self.assertTrue(any("no hazard control" in f for f in row["findings"]))

    def test_procedural_control_on_a_catastrophic_hazard_is_a_finding(self):
        row = assess_operation(
            operation(severity="catastrophic", control_type="procedure-and-training")
        )
        self.assertTrue(any("weaker than the precedence" in f for f in row["findings"]))

    def test_design_elimination_satisfies_a_catastrophic_hazard(self):
        row = assess_operation(
            operation(severity="catastrophic", control_type="design-elimination")
        )
        self.assertEqual(row["findings"], [])

    def test_control_without_verification_is_a_finding(self):
        row = assess_operation(operation(verification=None))
        self.assertTrue(any("no verification" in f for f in row["findings"]))
        self.assertFalse(row["verified"])

    def test_personnel_exposed_behind_procedure_only_is_a_finding(self):
        row = assess_operation(
            operation(severity="minor", control_type="procedure-and-training",
                      personnel_exposed=True)
        )
        self.assertTrue(any("exposes personnel" in f for f in row["findings"]))

    def test_personnel_exposed_behind_an_engineered_device_is_clean(self):
        row = assess_operation(operation(personnel_exposed=True))
        self.assertEqual(row["findings"], [])

    def test_ground_task_short_of_reaction_time_is_a_finding(self):
        row = assess_operation(
            operation(available_time_s=10.0, required_reaction_time_s=30.0)
        )
        self.assertTrue(any("more reaction time" in f for f in row["findings"]))


class FlightConstraintTests(unittest.TestCase):
    def test_positive_margin_is_clean(self):
        row = assess_operation(flight_operation())
        self.assertEqual(row["findings"], [])
        self.assertEqual(row["phase_set"], "flight")
        self.assertEqual(row["reaction_status"], "positive")

    def test_missing_reaction_budget_is_a_finding(self):
        row = assess_operation(
            flight_operation(available_time_s=None, required_reaction_time_s=None)
        )
        self.assertTrue(any("no reaction-time budget" in f for f in row["findings"]))

    def test_exhausted_margin_is_a_finding_not_a_pass(self):
        row = assess_operation(
            flight_operation(available_time_s=45.0, required_reaction_time_s=45.0)
        )
        self.assertEqual(row["reaction_status"], "exhausted")
        self.assertTrue(row["findings"])

    def test_negative_margin_is_a_finding(self):
        row = assess_operation(
            flight_operation(available_time_s=20.0, required_reaction_time_s=45.0)
        )
        self.assertEqual(row["reaction_status"], "negative")
        self.assertTrue(row["findings"])

    def test_personnel_rule_does_not_apply_in_flight(self):
        row = assess_operation(
            flight_operation(severity="minor", control_type="procedure-and-training",
                             personnel_exposed=True)
        )
        self.assertEqual(row["findings"], [])


class CoverageTests(unittest.TestCase):
    def test_covered_phases_are_reported_in_declaration_order(self):
        rows = [assess_operation(operation()), assess_operation(flight_operation())]
        coverage = phase_coverage(rows)
        self.assertEqual(coverage["covered"], ("handling", "mission-control"))

    def test_required_phase_with_no_operation_is_uncovered(self):
        rows = [assess_operation(operation())]
        coverage = phase_coverage(rows, ["handling", "transport"])
        self.assertEqual(coverage["uncovered"], ("transport",))

    def test_no_required_phases_gives_no_gap(self):
        rows = [assess_operation(operation())]
        self.assertEqual(phase_coverage(rows)["uncovered"], ())

    def test_unknown_required_phase_rejected(self):
        rows = [assess_operation(operation())]
        with self.assertRaises(ValueError):
            phase_coverage(rows, ["storage"])


class AssessmentTests(unittest.TestCase):
    def test_clean_set_reports_operations_controlled(self):
        result = assess_operational_safety(
            {"operations": [operation(), flight_operation()]}
        )
        self.assertEqual(result["verdict"], "operations-controlled")
        self.assertEqual(result["ground_count"], 1)
        self.assertEqual(result["flight_count"], 1)

    def test_uncovered_required_phase_becomes_a_finding(self):
        result = assess_operational_safety(
            {"operations": [operation()], "required_phases": ["handling", "transport"]}
        )
        self.assertTrue(any("hazardous phase transport" in f for f in result["findings"]))
        self.assertEqual(result["verdict"], "operations-uncontrolled")

    def test_duplicate_operation_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_operational_safety({"operations": [operation(), operation("op-1")]})

    def test_empty_operation_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_operational_safety({"operations": []})

    def test_missing_operations_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_operational_safety({"required_phases": ["handling"]})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_operational_safety([operation()])


if __name__ == "__main__":
    unittest.main()
