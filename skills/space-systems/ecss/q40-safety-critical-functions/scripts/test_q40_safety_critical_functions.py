"""Contract tests for the clause 6.5 safety-critical function logic."""

import unittest

from q40_safety_critical_functions_logic import (
    CONTROL_AREAS,
    CRITICAL_SEVERITIES,
    REQUIRED_TOLERANCE,
    SEVERITY_ORDER,
    UNIVERSAL_CONTROL_AREAS,
    achieved_failure_tolerance,
    assess_function,
    assess_safety_critical_functions,
    independent_inhibit_count,
    is_safety_critical,
    missing_controls,
    required_controls,
    required_failure_tolerance,
    required_inhibit_count,
    validate_function,
    validate_severity,
)


def all_controls(extra=()):
    """Build a control mapping with every universal area provided."""
    controls = {area: True for area in UNIVERSAL_CONTROL_AREAS}
    for area in extra:
        controls[area] = True
    return controls


def inhibits(count, group=None):
    """Build a list of inhibits, optionally all in one common-cause group."""
    return [
        {"id": "inh-%d" % index, "common_cause_group": group}
        for index in range(1, count + 1)
    ]


def function(identifier="FN-1", severity="catastrophic", **kwargs):
    """Build a function record with sensible defaults."""
    record = {
        "id": identifier,
        "severity": severity,
        "controls": kwargs.pop("controls", all_controls()),
        "inhibits": kwargs.pop("inhibits", inhibits(3)),
    }
    record.update(kwargs)
    return record


class SeverityTests(unittest.TestCase):
    def test_severity_order_is_most_severe_first(self):
        self.assertEqual(SEVERITY_ORDER, ("catastrophic", "critical", "major", "minor"))

    def test_critical_severities_are_the_top_two(self):
        self.assertEqual(CRITICAL_SEVERITIES, ("catastrophic", "critical"))

    def test_severity_is_trimmed_and_lowered(self):
        self.assertEqual(validate_severity(" CRITICAL "), "critical")

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            validate_severity("hazardous")


class ToleranceTests(unittest.TestCase):
    def test_catastrophic_demands_two_failure_tolerance(self):
        self.assertEqual(required_failure_tolerance("catastrophic"), 2)

    def test_critical_demands_one_failure_tolerance(self):
        self.assertEqual(required_failure_tolerance("critical"), 1)

    def test_major_demands_no_failure_tolerance(self):
        self.assertEqual(required_failure_tolerance("major"), 0)

    def test_tolerance_table_covers_every_severity(self):
        self.assertEqual(sorted(REQUIRED_TOLERANCE), sorted(SEVERITY_ORDER))

    def test_inhibit_count_is_one_more_than_the_tolerance(self):
        self.assertEqual(required_inhibit_count("catastrophic"), 3)
        self.assertEqual(required_inhibit_count("critical"), 2)


class InhibitIndependenceTests(unittest.TestCase):
    def test_ungrouped_inhibits_all_count(self):
        self.assertEqual(independent_inhibit_count(inhibits(3)), 3)

    def test_inhibits_sharing_a_group_count_once(self):
        self.assertEqual(independent_inhibit_count(inhibits(3, group="bus-a")), 1)

    def test_mixed_groups_count_per_group(self):
        mixed = inhibits(2, group="bus-a") + inhibits(1)
        mixed[-1]["id"] = "inh-9"
        self.assertEqual(independent_inhibit_count(mixed), 2)

    def test_no_inhibits_gives_zero_tolerance(self):
        self.assertEqual(achieved_failure_tolerance([]), 0)

    def test_tolerance_is_one_less_than_the_independent_count(self):
        self.assertEqual(achieved_failure_tolerance(inhibits(3)), 2)

    def test_common_cause_group_collapses_the_tolerance(self):
        self.assertEqual(achieved_failure_tolerance(inhibits(3, group="bus-a")), 0)

    def test_malformed_inhibit_rejected(self):
        with self.assertRaises(ValueError):
            independent_inhibit_count([{"name": "inh-1"}])


class ValidationTests(unittest.TestCase):
    def test_valid_record_normalises_the_identifier(self):
        record = validate_function(function(identifier="  FN-7  "))
        self.assertEqual(record["id"], "FN-7")

    def test_unknown_function_key_rejected(self):
        bad = function()
        bad["owner"] = "avionics"
        with self.assertRaises(ValueError):
            validate_function(bad)

    def test_unknown_control_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_function(function(controls={"paint-colour": True}))

    def test_non_boolean_control_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_function(function(controls={"status-information": "yes"}))

    def test_duplicate_inhibit_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_function(
                function(inhibits=[{"id": "inh-1"}, {"id": "inh-1"}])
            )

    def test_blank_inhibit_group_rejected(self):
        with self.assertRaises(ValueError):
            validate_function(function(inhibits=[{"id": "inh-1", "common_cause_group": "  "}]))

    def test_non_boolean_uses_software_rejected(self):
        with self.assertRaises(ValueError):
            validate_function(function(uses_software="yes"))


class CriticalityTests(unittest.TestCase):
    def test_catastrophic_function_is_safety_critical(self):
        self.assertTrue(is_safety_critical(validate_function(function())))

    def test_major_function_is_not_safety_critical_by_severity(self):
        record = validate_function(function(severity="major", inhibits=[]))
        self.assertFalse(is_safety_critical(record))

    def test_declared_override_promotes_a_major_function(self):
        record = validate_function(
            function(severity="major", inhibits=[], safety_critical=True)
        )
        self.assertTrue(is_safety_critical(record))

    def test_declared_override_can_demote(self):
        record = validate_function(function(safety_critical=False))
        self.assertFalse(is_safety_critical(record))


class ControlAreaTests(unittest.TestCase):
    def test_areas_are_returned_in_declaration_order(self):
        record = validate_function(function(uses_software=True, uses_eee=True))
        self.assertEqual(required_controls(record), CONTROL_AREAS)

    def test_hardware_only_function_does_not_owe_the_software_area(self):
        record = validate_function(function(uses_eee=True))
        self.assertNotIn("software-safety-control", required_controls(record))

    def test_software_only_function_does_not_owe_the_eee_area(self):
        record = validate_function(function(uses_software=True))
        self.assertNotIn("eee-component-selection", required_controls(record))

    def test_non_critical_function_owes_no_control_area(self):
        record = validate_function(function(severity="minor", inhibits=[]))
        self.assertEqual(required_controls(record), ())

    def test_absent_universal_area_is_reported_missing(self):
        controls = all_controls()
        del controls["safe-shutdown"]
        record = validate_function(function(controls=controls))
        self.assertEqual(missing_controls(record), ("safe-shutdown",))

    def test_area_declared_false_counts_as_missing(self):
        controls = all_controls()
        controls["status-information"] = False
        record = validate_function(function(controls=controls))
        self.assertIn("status-information", missing_controls(record))


class AssessFunctionTests(unittest.TestCase):
    def test_compliant_function_has_no_findings(self):
        row = assess_function(function())
        self.assertEqual(row["findings"], [])
        self.assertEqual(row["achieved_failure_tolerance"], 2)
        self.assertEqual(row["required_failure_tolerance"], 2)

    def test_tolerance_shortfall_is_a_finding(self):
        row = assess_function(function(inhibits=inhibits(2)))
        self.assertTrue(any("failure tolerance" in f for f in row["findings"]))

    def test_common_cause_group_produces_a_shortfall(self):
        row = assess_function(function(inhibits=inhibits(3, group="bus-a")))
        self.assertEqual(row["independent_inhibits"], 1)
        self.assertTrue(row["findings"])

    def test_missing_software_control_is_a_finding(self):
        row = assess_function(function(uses_software=True))
        self.assertTrue(any("software-safety-control" in f for f in row["findings"]))

    def test_non_critical_function_needs_no_inhibits(self):
        row = assess_function(function(severity="minor", inhibits=[]))
        self.assertFalse(row["safety_critical"])
        self.assertEqual(row["required_inhibits"], 0)
        self.assertEqual(row["findings"], [])


class RollUpTests(unittest.TestCase):
    def test_clean_set_reports_controls_complete(self):
        result = assess_safety_critical_functions([function(), function("FN-2", "critical",
                                                                       inhibits=inhibits(2))])
        self.assertEqual(result["verdict"], "controls-complete")
        self.assertEqual(result["safety_critical_count"], 2)

    def test_open_areas_are_collected_across_functions(self):
        controls = all_controls()
        del controls["safe-shutdown"]
        result = assess_safety_critical_functions(
            [function(controls=controls), function("FN-2", "critical", uses_eee=True,
                                                   inhibits=inhibits(2))]
        )
        self.assertEqual(
            result["open_control_areas"], ["eee-component-selection", "safe-shutdown"]
        )
        self.assertEqual(result["verdict"], "controls-incomplete")

    def test_non_critical_functions_are_counted_but_not_critical(self):
        result = assess_safety_critical_functions(
            [function(), function("FN-2", "minor", inhibits=[])]
        )
        self.assertEqual(result["function_count"], 2)
        self.assertEqual(result["safety_critical_count"], 1)

    def test_duplicate_function_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_safety_critical_functions([function(), function("fn-1")])

    def test_empty_function_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_safety_critical_functions([])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            assess_safety_critical_functions({"id": "FN-1"})


if __name__ == "__main__":
    unittest.main()
