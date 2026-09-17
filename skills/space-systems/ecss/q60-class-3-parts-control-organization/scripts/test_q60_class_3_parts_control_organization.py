"""Contract tests for the clause 6.1.2.1 class 3 part control accountability logic."""

import unittest

from q60_class_3_parts_control_organization_logic import (
    BOUND_TOLERANCE,
    ESCALATION_DEPTH_CEILING,
    MANDATE_FLOOR,
    PART_CONTROL_FUNCTIONS,
    accountable_unit,
    admissible_units,
    compile_class_3_parts_control_organization,
    contested_functions,
    declared_functions,
    mandate_share,
    ordered_functions,
    organization_disposition,
    unassigned_functions,
    unit_defects,
    unit_findings,
    unit_id,
    unrecognised_functions,
)

ALL_FUNCTIONS = list(PART_CONTROL_FUNCTIONS)


def _unit(**over):
    base = {
        "unit_id": "product-assurance-office",
        "declared_in_project_organization": True,
        "accountable_role": "parts-engineer",
        "functions": list(ALL_FUNCTIONS),
        "escalation_depth": 2,
        "independent_of_design_authority": True,
    }
    base.update(over)
    return base


def _project(**over):
    base = {
        "project_id": "CLASS-3-PLATFORM-6061",
        "units": [_unit()],
    }
    base.update(over)
    return base


class FunctionOrderTests(unittest.TestCase):
    def test_functions_come_back_in_report_order(self):
        ordered = ordered_functions(["nonconformance-referral",
                                     "part-selection-approval"])
        self.assertEqual(ordered, ["part-selection-approval",
                                   "nonconformance-referral"])

    def test_function_names_compare_case_insensitively(self):
        self.assertEqual(ordered_functions(["PART-SELECTION-APPROVAL"]),
                         ["part-selection-approval"])

    def test_a_repeated_function_is_counted_once(self):
        self.assertEqual(
            ordered_functions(["part-selection-approval",
                               "part-selection-approval"]),
            ["part-selection-approval"])

    def test_an_unknown_function_is_left_out_of_the_recognised_list(self):
        self.assertEqual(ordered_functions(["tea-rota-management"]), [])

    def test_an_unknown_function_is_reported_separately(self):
        self.assertEqual(
            unrecognised_functions(_unit(functions=["tea-rota-management"])),
            ["tea-rota-management"])

    def test_a_bare_string_is_not_a_sequence_of_functions(self):
        with self.assertRaises(ValueError):
            ordered_functions("part-selection-approval")

    def test_an_empty_function_name_is_rejected(self):
        with self.assertRaises(ValueError):
            ordered_functions(["  "])

    def test_every_listed_function_is_orderable(self):
        self.assertEqual(ordered_functions(ALL_FUNCTIONS), ALL_FUNCTIONS)


class MandateTests(unittest.TestCase):
    def test_a_full_mandate_reads_one(self):
        self.assertAlmostEqual(mandate_share(_unit()), 1.0, places=9)

    def test_an_empty_mandate_reads_zero(self):
        self.assertAlmostEqual(mandate_share(_unit(functions=[])), 0.0, places=9)

    def test_a_partial_mandate_is_the_held_share(self):
        unit = _unit(functions=ALL_FUNCTIONS[:3])
        self.assertAlmostEqual(mandate_share(unit),
                               3.0 / len(PART_CONTROL_FUNCTIONS), places=9)

    def test_an_unrecognised_function_adds_no_mandate(self):
        unit = _unit(functions=ALL_FUNCTIONS + ["tea-rota-management"])
        self.assertAlmostEqual(mandate_share(unit), 1.0, places=9)

    def test_declared_functions_come_back_in_report_order(self):
        unit = _unit(functions=list(reversed(ALL_FUNCTIONS)))
        self.assertEqual(declared_functions(unit), ALL_FUNCTIONS)

    def test_the_floor_is_the_documented_size(self):
        self.assertAlmostEqual(MANDATE_FLOOR, 0.75, places=9)

    def test_the_tolerance_is_the_documented_size(self):
        self.assertAlmostEqual(BOUND_TOLERANCE, 1e-9, places=12)


class UnitDefectTests(unittest.TestCase):
    def test_a_sound_unit_carries_no_defects(self):
        self.assertEqual(unit_defects(_unit()), [])

    def test_an_undeclared_unit_is_a_defect(self):
        self.assertIn("unit-not-declared-in-organization",
                      unit_defects(_unit(declared_in_project_organization=False)))

    def test_a_missing_declaration_flag_is_a_defect(self):
        unit = _unit()
        del unit["declared_in_project_organization"]
        self.assertIn("unit-not-declared-in-organization", unit_defects(unit))

    def test_an_unnamed_accountable_role_is_a_defect(self):
        self.assertIn("accountable-role-not-named",
                      unit_defects(_unit(accountable_role="   ")))

    def test_a_unit_holding_nothing_is_a_defect(self):
        defects = unit_defects(_unit(functions=[]))
        self.assertIn("no-part-control-function-held", defects)

    def test_selection_approval_is_the_function_that_cannot_be_missing(self):
        unit = _unit(functions=[f for f in ALL_FUNCTIONS
                                if f != "part-selection-approval"])
        self.assertIn("part-selection-approval-not-held", unit_defects(unit))

    def test_an_unrecognised_function_is_a_defect(self):
        unit = _unit(functions=ALL_FUNCTIONS + ["tea-rota-management"])
        self.assertIn("function-not-recognised", unit_defects(unit))

    def test_an_unstated_escalation_depth_is_a_defect(self):
        unit = _unit()
        del unit["escalation_depth"]
        self.assertIn("escalation-depth-not-stated", unit_defects(unit))

    def test_a_boolean_is_not_an_escalation_depth(self):
        self.assertIn("escalation-depth-not-stated",
                      unit_defects(_unit(escalation_depth=True)))

    def test_a_depth_beyond_the_ceiling_is_a_defect(self):
        unit = _unit(escalation_depth=ESCALATION_DEPTH_CEILING + 1)
        self.assertIn("escalation-depth-beyond-ceiling", unit_defects(unit))

    def test_a_depth_exactly_on_the_ceiling_is_admissible(self):
        unit = _unit(escalation_depth=ESCALATION_DEPTH_CEILING)
        self.assertEqual(unit_defects(unit), [])

    def test_a_unit_inside_the_design_authority_is_a_defect(self):
        self.assertIn("not-independent-of-design-authority",
                      unit_defects(_unit(independent_of_design_authority=False)))

    def test_a_mandate_below_the_floor_is_a_defect(self):
        unit = _unit(functions=["part-selection-approval"])
        self.assertIn("mandate-below-floor", unit_defects(unit))

    def test_a_mandate_above_the_floor_is_admissible(self):
        unit = _unit(functions=ALL_FUNCTIONS[:5])
        self.assertAlmostEqual(mandate_share(unit), 5.0 / 6.0, places=9)
        self.assertEqual(unit_defects(unit), [])

    def test_a_unit_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            unit_defects("product-assurance-office")

    def test_a_unit_without_an_identifier_gets_a_placeholder(self):
        self.assertEqual(unit_id(_unit(unit_id=None)), "unnamed-unit")


class RosterTests(unittest.TestCase):
    def test_a_defective_unit_is_listed_with_its_defects(self):
        findings = unit_findings([_unit(accountable_role="")])
        self.assertEqual(findings[0]["unit"], "product-assurance-office")
        self.assertIn("accountable-role-not-named", findings[0]["defects"])

    def test_a_sound_roster_reports_no_findings(self):
        self.assertEqual(unit_findings(_project()["units"]), [])

    def test_only_admissible_units_are_returned(self):
        units = [_unit(), _unit(unit_id="design-office",
                                independent_of_design_authority=False)]
        self.assertEqual([unit_id(u) for u in admissible_units(units)],
                         ["product-assurance-office"])

    def test_an_empty_roster_is_rejected(self):
        with self.assertRaises(ValueError):
            admissible_units([])

    def test_a_roster_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            admissible_units(_unit())


class PlacementTests(unittest.TestCase):
    def test_a_full_roster_leaves_nothing_unassigned(self):
        self.assertEqual(unassigned_functions(_project()["units"]), [])

    def test_a_function_nobody_holds_is_named(self):
        unit = _unit(functions=ALL_FUNCTIONS[:-1])
        self.assertEqual(unassigned_functions([unit]), [ALL_FUNCTIONS[-1]])

    def test_an_undeclared_unit_places_nothing(self):
        unit = _unit(declared_in_project_organization=False)
        self.assertEqual(unassigned_functions([unit]), ALL_FUNCTIONS)

    def test_unassigned_functions_come_back_in_report_order(self):
        unit = _unit(functions=["nonconformance-referral"])
        missing = unassigned_functions([unit])
        indexes = [PART_CONTROL_FUNCTIONS.index(n) for n in missing]
        self.assertEqual(indexes, sorted(indexes))

    def test_one_unit_contests_nothing(self):
        self.assertEqual(contested_functions(_project()["units"]), [])

    def test_two_units_claiming_one_function_contest_it(self):
        units = [_unit(), _unit(unit_id="quality-office",
                                functions=["part-selection-approval"])]
        self.assertEqual(contested_functions(units), ["part-selection-approval"])

    def test_an_undeclared_unit_contests_nothing(self):
        units = [_unit(), _unit(unit_id="shadow-office",
                                declared_in_project_organization=False)]
        self.assertEqual(contested_functions(units), [])


class NominationTests(unittest.TestCase):
    def test_the_only_admissible_unit_is_nominated(self):
        self.assertEqual(accountable_unit(_project()["units"]),
                         "product-assurance-office")

    def test_no_admissible_unit_nominates_nobody(self):
        units = [_unit(independent_of_design_authority=False)]
        self.assertIsNone(accountable_unit(units))

    def test_the_larger_mandate_wins(self):
        units = [
            _unit(unit_id="quality-office", functions=ALL_FUNCTIONS[:5]),
            _unit(unit_id="product-assurance-office"),
        ]
        self.assertEqual(accountable_unit(units), "product-assurance-office")

    def test_an_equal_mandate_goes_to_the_shorter_escalation_path(self):
        units = [
            _unit(unit_id="quality-office", escalation_depth=3),
            _unit(unit_id="assurance-office", escalation_depth=1),
        ]
        self.assertEqual(accountable_unit(units), "assurance-office")

    def test_an_equal_path_goes_to_the_lower_identifier(self):
        units = [
            _unit(unit_id="quality-office", escalation_depth=2),
            _unit(unit_id="assurance-office", escalation_depth=2),
        ]
        self.assertEqual(accountable_unit(units), "assurance-office")

    def test_a_defective_unit_is_never_nominated(self):
        units = [
            _unit(unit_id="alpha-office", accountable_role=""),
            _unit(unit_id="zulu-office"),
        ]
        self.assertEqual(accountable_unit(units), "zulu-office")


class DispositionTests(unittest.TestCase):
    def test_a_placed_mandate_reads_as_assigned(self):
        self.assertEqual(
            organization_disposition("product-assurance-office", [], []),
            "accountability-assigned")

    def test_no_nominee_leaves_the_mandate_unassigned(self):
        self.assertEqual(organization_disposition(None, [], []),
                         "accountability-unassigned")

    def test_an_unheld_function_leaves_the_mandate_unassigned(self):
        self.assertEqual(
            organization_disposition("product-assurance-office",
                                     ["nonconformance-referral"], []),
            "accountability-unassigned")

    def test_an_unheld_function_outranks_an_overlap(self):
        self.assertEqual(
            organization_disposition("product-assurance-office",
                                     ["nonconformance-referral"],
                                     ["part-selection-approval"]),
            "accountability-unassigned")

    def test_an_overlap_reads_as_split(self):
        self.assertEqual(
            organization_disposition("product-assurance-office", [],
                                     ["part-selection-approval"]),
            "accountability-split")

    def test_the_unassigned_list_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            organization_disposition("product-assurance-office",
                                     "nonconformance-referral", [])

    def test_a_nominee_must_be_an_identifier_or_nothing(self):
        with self.assertRaises(ValueError):
            organization_disposition(7, [], [])


class CompilationTests(unittest.TestCase):
    def test_a_sound_organization_is_ready(self):
        result = compile_class_3_parts_control_organization(_project())
        self.assertTrue(result["organization_ready"])
        self.assertEqual(result["disposition"], "accountability-assigned")

    def test_the_accountable_unit_is_named(self):
        result = compile_class_3_parts_control_organization(_project())
        self.assertEqual(result["accountable_unit"], "product-assurance-office")

    def test_the_accountable_mandate_share_is_reported(self):
        result = compile_class_3_parts_control_organization(_project())
        self.assertAlmostEqual(result["accountable_mandate_share"], 1.0, places=9)

    def test_an_unplaced_function_blocks_the_organization(self):
        project = _project(units=[_unit(functions=ALL_FUNCTIONS[:5])])
        result = compile_class_3_parts_control_organization(project)
        self.assertEqual(result["unassigned_functions"], [ALL_FUNCTIONS[5]])
        self.assertFalse(result["organization_ready"])

    def test_an_overlap_is_reported_as_split(self):
        project = _project(units=[
            _unit(),
            _unit(unit_id="quality-office", functions=["part-selection-approval"]),
        ])
        result = compile_class_3_parts_control_organization(project)
        self.assertEqual(result["disposition"], "accountability-split")
        self.assertIn("part-selection-approval", result["contested_functions"])

    def test_a_defective_unit_is_reported_with_its_defects(self):
        project = _project(units=[_unit(accountable_role="")])
        result = compile_class_3_parts_control_organization(project)
        self.assertIn("accountable-role-not-named",
                      result["unit_findings"][0]["defects"])

    def test_a_roster_with_nobody_admissible_names_nobody(self):
        project = _project(units=[_unit(independent_of_design_authority=False)])
        result = compile_class_3_parts_control_organization(project)
        self.assertIsNone(result["accountable_unit"])
        self.assertIsNone(result["accountable_mandate_share"])

    def test_an_empty_roster_is_rejected(self):
        with self.assertRaises(ValueError):
            compile_class_3_parts_control_organization(_project(units=[]))

    def test_the_project_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            compile_class_3_parts_control_organization([_project()])


if __name__ == "__main__":
    unittest.main(verbosity=1)
