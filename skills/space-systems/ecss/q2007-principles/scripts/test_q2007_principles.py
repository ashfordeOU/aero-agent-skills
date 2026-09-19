"""Contract tests for the test-centre assurance scope principles logic."""

import unittest

from q2007_principles_logic import (
    CENTRE_FUNCTIONS,
    CORE_FUNCTIONS,
    DISCIPLINES,
    OPERATIONS_LINE,
    assess_test_centre_scope,
    centre_function,
    coverage_cells,
    coverage_fraction,
    exclusion_findings,
    independence_findings,
    normalise_identifier,
    subcontract_findings,
    uncovered_cells,
    validate_declaration,
)


def _entry(function, quality=True, safety=True, **extra):
    record = {
        "function": function,
        "quality_assurance": quality,
        "safety_assurance": safety,
    }
    record.update(extra)
    return record


def _full_declaration():
    return [_entry(function) for function in CENTRE_FUNCTIONS]


def _spec(**overrides):
    spec = {
        "declaration": _full_declaration(),
        "assurance_reports_to": "centre-director",
    }
    spec.update(overrides)
    return spec


class NormaliseIdentifierTests(unittest.TestCase):
    def test_trims_and_lowercases(self):
        self.assertEqual(
            normalise_identifier(" Facility-Maintenance ", "function"),
            "facility-maintenance",
        )

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier(" ", "function")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier(9, "function")


class CentreFunctionTests(unittest.TestCase):
    def test_known_function_returned(self):
        self.assertEqual(
            centre_function("Calibration-And-Metrology"), "calibration-and-metrology"
        )

    def test_unknown_function_rejected(self):
        with self.assertRaises(ValueError):
            centre_function("staff-canteen")

    def test_every_core_function_is_a_centre_function(self):
        for function in CORE_FUNCTIONS:
            self.assertIn(function, CENTRE_FUNCTIONS)

    def test_subcontracted_services_are_in_the_organization(self):
        self.assertIn("subcontracted-test-services", CENTRE_FUNCTIONS)

    def test_both_disciplines_are_named(self):
        self.assertEqual(set(DISCIPLINES), {"quality", "safety"})


class ValidateDeclarationTests(unittest.TestCase):
    def test_full_declaration_normalised(self):
        entries = validate_declaration(_full_declaration())
        self.assertEqual(len(entries), len(CENTRE_FUNCTIONS))
        self.assertTrue(entries["facility-maintenance"]["quality"])

    def test_partial_declaration_allowed(self):
        entries = validate_declaration([_entry("facility-maintenance")])
        self.assertEqual(list(entries), ["facility-maintenance"])

    def test_duplicate_function_rejected(self):
        with self.assertRaises(ValueError):
            validate_declaration(
                [_entry("facility-maintenance"), _entry("facility-maintenance")]
            )

    def test_missing_discipline_flag_rejected(self):
        bad = {"function": "facility-maintenance", "quality_assurance": True}
        with self.assertRaises(ValueError):
            validate_declaration([bad])

    def test_missing_function_rejected(self):
        with self.assertRaises(ValueError):
            validate_declaration([{"quality_assurance": True,
                                   "safety_assurance": True}])

    def test_blank_rationale_rejected(self):
        with self.assertRaises(ValueError):
            validate_declaration(
                [_entry("facility-maintenance", safety=False,
                        exclusion_rationale="  ")]
            )

    def test_empty_declaration_rejected(self):
        with self.assertRaises(ValueError):
            validate_declaration([])

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            validate_declaration(["facility-maintenance"])


class ExclusionFindingTests(unittest.TestCase):
    def test_full_scope_is_silent(self):
        self.assertEqual(exclusion_findings(validate_declaration(
            _full_declaration())), [])

    def test_undeclared_function_reported(self):
        declaration = [_entry(f) for f in CENTRE_FUNCTIONS
                       if f != "personnel-training-and-certification"]
        findings = exclusion_findings(validate_declaration(declaration))
        self.assertEqual(len(findings), 1)
        self.assertIn("personnel-training-and-certification", findings[0])

    def test_core_function_exclusion_refused(self):
        declaration = _full_declaration()
        declaration[0] = _entry("test-facility-operations", safety=False,
                                owner="qa-manager",
                                exclusion_rationale="handled by the customer")
        findings = exclusion_findings(validate_declaration(declaration))
        self.assertTrue(any("core function" in f for f in findings))

    def test_exclusion_without_a_rationale_reported(self):
        declaration = _full_declaration()
        index = CENTRE_FUNCTIONS.index("handling-transport-and-storage")
        declaration[index] = _entry("handling-transport-and-storage", quality=False)
        findings = exclusion_findings(validate_declaration(declaration))
        self.assertTrue(any("no rationale" in f for f in findings))

    def test_exclusion_without_an_owner_reported(self):
        declaration = _full_declaration()
        index = CENTRE_FUNCTIONS.index("handling-transport-and-storage")
        declaration[index] = _entry("handling-transport-and-storage", quality=False,
                                    exclusion_rationale="carrier holds the approval")
        findings = exclusion_findings(validate_declaration(declaration))
        self.assertTrue(any("no accountable owner" in f for f in findings))

    def test_justified_and_owned_exclusion_is_accepted(self):
        declaration = _full_declaration()
        index = CENTRE_FUNCTIONS.index("handling-transport-and-storage")
        declaration[index] = _entry("handling-transport-and-storage", quality=False,
                                    owner="logistics-lead",
                                    exclusion_rationale="carrier holds the approval")
        self.assertEqual(exclusion_findings(validate_declaration(declaration)), [])

    def test_both_disciplines_named_in_one_finding(self):
        declaration = _full_declaration()
        index = CENTRE_FUNCTIONS.index("handling-transport-and-storage")
        declaration[index] = _entry("handling-transport-and-storage", quality=False,
                                    safety=False)
        findings = exclusion_findings(validate_declaration(declaration))
        self.assertEqual(len(findings), 1)
        self.assertIn("quality assurance and safety assurance", findings[0])


class SubcontractFindingTests(unittest.TestCase):
    def test_subcontract_in_scope_is_silent(self):
        self.assertEqual(
            subcontract_findings(validate_declaration(_full_declaration())), []
        )

    def test_subcontract_exclusion_reported_even_when_justified(self):
        declaration = _full_declaration()
        index = CENTRE_FUNCTIONS.index("subcontracted-test-services")
        declaration[index] = _entry("subcontracted-test-services", quality=False,
                                    owner="procurement-lead",
                                    exclusion_rationale="supplier is approved")
        self.assertEqual(
            len(subcontract_findings(validate_declaration(declaration))), 1
        )

    def test_undeclared_subcontract_leaves_this_check_silent(self):
        declaration = [_entry(f) for f in CENTRE_FUNCTIONS
                       if f != "subcontracted-test-services"]
        self.assertEqual(subcontract_findings(validate_declaration(declaration)), [])


class IndependenceFindingTests(unittest.TestCase):
    def test_independent_reporting_line_is_silent(self):
        self.assertEqual(independence_findings("centre-director"), [])

    def test_operations_reporting_line_reported(self):
        self.assertEqual(len(independence_findings("Test-Operations-Manager")), 1)

    def test_every_operations_line_entry_is_caught(self):
        for line in OPERATIONS_LINE:
            self.assertEqual(len(independence_findings(line)), 1, line)

    def test_blank_reporting_line_rejected(self):
        with self.assertRaises(ValueError):
            independence_findings("")


class CoverageTests(unittest.TestCase):
    def test_one_cell_per_function_and_discipline(self):
        cells = coverage_cells(validate_declaration(_full_declaration()))
        self.assertEqual(len(cells), len(CENTRE_FUNCTIONS) * len(DISCIPLINES))

    def test_full_declaration_scores_one(self):
        self.assertAlmostEqual(
            coverage_fraction(validate_declaration(_full_declaration())), 1.0,
            places=12,
        )

    def test_one_excluded_discipline_drops_one_cell(self):
        declaration = _full_declaration()
        index = CENTRE_FUNCTIONS.index("facility-maintenance")
        declaration[index] = _entry("facility-maintenance", safety=False)
        entries = validate_declaration(declaration)
        total = len(CENTRE_FUNCTIONS) * len(DISCIPLINES)
        self.assertAlmostEqual(
            coverage_fraction(entries), (total - 1) / float(total), places=12
        )

    def test_undeclared_function_counts_as_uncovered(self):
        declaration = [_entry(f) for f in CENTRE_FUNCTIONS
                       if f != "facility-maintenance"]
        entries = validate_declaration(declaration)
        uncovered = uncovered_cells(entries)
        self.assertEqual(len(uncovered), len(DISCIPLINES))

    def test_uncovered_cells_name_the_discipline(self):
        declaration = _full_declaration()
        index = CENTRE_FUNCTIONS.index("facility-maintenance")
        declaration[index] = _entry("facility-maintenance", safety=False)
        uncovered = uncovered_cells(validate_declaration(declaration))
        self.assertEqual(uncovered, ["facility-maintenance/safety"])


class AssessTestCentreScopeTests(unittest.TestCase):
    def test_full_scope_passes(self):
        result = assess_test_centre_scope(_spec())
        self.assertEqual(result["verdict"], "scope-covers-the-centre")
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=12)

    def test_operations_reporting_line_fails_the_scope(self):
        result = assess_test_centre_scope(_spec(assurance_reports_to="facility-manager"))
        self.assertEqual(result["verdict"], "scope-incomplete")

    def test_undeclared_function_is_listed(self):
        declaration = [_entry(f) for f in CENTRE_FUNCTIONS
                       if f != "facility-maintenance"]
        result = assess_test_centre_scope(_spec(declaration=declaration))
        self.assertEqual(result["undeclared_functions"], ["facility-maintenance"])

    def test_subcontract_exclusion_fails_the_scope(self):
        declaration = _full_declaration()
        index = CENTRE_FUNCTIONS.index("subcontracted-test-services")
        declaration[index] = _entry("subcontracted-test-services", quality=False,
                                    owner="procurement-lead",
                                    exclusion_rationale="supplier is approved")
        result = assess_test_centre_scope(_spec(declaration=declaration))
        self.assertTrue(any("stay inside" in f for f in result["findings"]))

    def test_test_execution_alone_is_not_the_scope(self):
        result = assess_test_centre_scope(
            _spec(declaration=[_entry("test-facility-operations")])
        )
        self.assertEqual(result["verdict"], "scope-incomplete")
        self.assertEqual(
            len(result["undeclared_functions"]), len(CENTRE_FUNCTIONS) - 1
        )

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["assurance_reports_to"]
        with self.assertRaises(ValueError):
            assess_test_centre_scope(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_centre_scope(["declaration"])

    def test_declared_functions_are_reported_sorted(self):
        result = assess_test_centre_scope(_spec())
        self.assertEqual(result["declared_functions"],
                         sorted(result["declared_functions"]))


if __name__ == "__main__":
    unittest.main()
