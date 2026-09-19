#!/usr/bin/env python3
"""Contract tests for the test-centre organization of clause 5.3.1.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a chart never
drawn, a unit reporting to a parent the chart does not hold, a reporting
cycle, a chart with two roots, a required quality or safety function no
unit holds, a function held twice over, an assurance unit reporting up
through the test-operations line, a declared interface naming an unheld
unit, and a required interface nobody declared.
"""

import unittest

from q2007_organization_logic import (
    FUNCTION_CONFIGURATION,
    FUNCTION_METROLOGY,
    FUNCTION_MISSING,
    FUNCTION_QUALITY_ASSURANCE,
    FUNCTION_SAFETY_ASSURANCE,
    FUNCTION_TEST_OPERATIONS,
    INDEPENDENCE_COMPROMISED,
    INTERFACE_GAPS,
    ORGANIZATION_DEFINED,
    ORGANIZATION_UNDEFINED,
    REQUIRED_FUNCTIONS,
    STRUCTURE_INVALID,
    assess_organization,
    cyclic_units,
    dangling_interfaces,
    independence_defects,
    interface_gaps,
    orphan_units,
    reporting_chain,
    root_units,
    shared_functions,
    structure_defects,
    unassigned_functions,
    units_holding,
    validate_interface,
    validate_organization,
    validate_unit,
)


def _unit(unit_id, reports_to, functions=None):
    return {"unit_id": unit_id, "reports_to": reports_to, "functions": list(functions or [])}


def _units():
    return [
        _unit("centre-head", None),
        _unit("quality-and-safety", "centre-head",
              [FUNCTION_QUALITY_ASSURANCE, FUNCTION_SAFETY_ASSURANCE]),
        _unit("test-operations", "centre-head", [FUNCTION_TEST_OPERATIONS]),
        _unit("configuration-office", "centre-head", [FUNCTION_CONFIGURATION]),
        _unit("metrology-lab", "centre-head", [FUNCTION_METROLOGY]),
    ]


def _interfaces():
    return [
        ("quality-and-safety", "test-operations"),
        ("metrology-lab", "test-operations"),
    ]


def _organization(**overrides):
    record = {
        "defined": True,
        "units": _units(),
        "interfaces": _interfaces(),
    }
    record.update(overrides)
    return record


def _case(**overrides):
    case = {"organization": _organization()}
    case.update(overrides)
    return case


class UnitValidation(unittest.TestCase):
    def test_unit_missing_field_refused(self):
        bad = _unit("metrology-lab", "centre-head")
        del bad["functions"]
        with self.assertRaises(ValueError):
            validate_unit(bad)

    def test_unit_reporting_to_itself_refused(self):
        with self.assertRaises(ValueError):
            validate_unit(_unit("centre-head", "centre-head"))

    def test_unrecognised_function_refused(self):
        with self.assertRaises(ValueError):
            validate_unit(_unit("catering", "centre-head", ["canteen-function"]))

    def test_duplicate_function_in_one_unit_refused(self):
        with self.assertRaises(ValueError):
            validate_unit(
                _unit("qa", "centre-head",
                      [FUNCTION_QUALITY_ASSURANCE, FUNCTION_QUALITY_ASSURANCE])
            )

    def test_duplicate_unit_id_refused(self):
        units = _units() + [_unit("metrology-lab", "centre-head", [FUNCTION_METROLOGY])]
        with self.assertRaises(ValueError):
            validate_organization(_organization(units=units))

    def test_self_interface_refused(self):
        with self.assertRaises(ValueError):
            validate_interface(("test-operations", "test-operations"))

    def test_interface_that_is_not_a_pair_refused(self):
        with self.assertRaises(ValueError):
            validate_interface(("test-operations",))

    def test_duplicate_interface_refused(self):
        interfaces = _interfaces() + [("test-operations", "quality-and-safety")]
        with self.assertRaises(ValueError):
            validate_organization(_organization(interfaces=interfaces))

    def test_non_mapping_organization_refused(self):
        with self.assertRaises(ValueError):
            validate_organization(["defined"])


class Structure(unittest.TestCase):
    def test_a_well_formed_chart_has_one_root(self):
        self.assertEqual(root_units(_organization()), ["centre-head"])

    def test_a_well_formed_chart_has_no_structural_defect(self):
        self.assertEqual(structure_defects(_organization()), [])

    def test_an_orphan_unit_is_named(self):
        units = _units() + [_unit("shipping", "logistics-division")]
        self.assertEqual(orphan_units(_organization(units=units)), ["shipping"])

    def test_a_reporting_cycle_is_named(self):
        units = [
            _unit("alpha", "beta"),
            _unit("beta", "alpha"),
        ]
        self.assertEqual(sorted(cyclic_units(_organization(units=units))), ["alpha", "beta"])

    def test_two_roots_are_a_structural_defect(self):
        units = _units() + [_unit("second-head", None)]
        defects = structure_defects(_organization(units=units))
        self.assertEqual(len(defects), 1)
        self.assertIn("2 roots", defects[0])

    def test_a_chart_with_no_root_is_a_structural_defect(self):
        units = [_unit("alpha", "beta"), _unit("beta", "alpha")]
        self.assertTrue(structure_defects(_organization(units=units)))

    def test_reporting_chain_reaches_the_root(self):
        self.assertEqual(
            reporting_chain(_organization(), "metrology-lab"), ["metrology-lab", "centre-head"]
        )

    def test_reporting_chain_on_an_unheld_unit_is_refused(self):
        with self.assertRaises(ValueError):
            reporting_chain(_organization(), "shipping")

    def test_reporting_chain_through_a_cycle_is_refused(self):
        units = [_unit("alpha", "beta"), _unit("beta", "alpha")]
        with self.assertRaises(ValueError):
            reporting_chain(_organization(units=units), "alpha")


class Functions(unittest.TestCase):
    def test_every_required_function_is_held(self):
        self.assertEqual(unassigned_functions(_organization()), [])

    def test_a_dropped_function_is_named(self):
        units = [u for u in _units() if u["unit_id"] != "metrology-lab"]
        self.assertEqual(unassigned_functions(_organization(units=units)), [FUNCTION_METROLOGY])

    def test_units_holding_returns_every_holder(self):
        units = _units() + [
            _unit("site-safety", "centre-head", [FUNCTION_SAFETY_ASSURANCE])
        ]
        self.assertEqual(
            units_holding(_organization(units=units), FUNCTION_SAFETY_ASSURANCE),
            ["quality-and-safety", "site-safety"],
        )

    def test_a_shared_function_is_reported(self):
        units = _units() + [
            _unit("site-safety", "centre-head", [FUNCTION_SAFETY_ASSURANCE])
        ]
        shared = shared_functions(_organization(units=units))
        self.assertEqual(shared[0][0], FUNCTION_SAFETY_ASSURANCE)

    def test_units_holding_refuses_an_unrecognised_function(self):
        with self.assertRaises(ValueError):
            units_holding(_organization(), "canteen-function")

    def test_a_unit_named_for_a_function_it_does_not_hold_does_not_count(self):
        units = [
            _unit("centre-head", None),
            _unit("quality-assurance-department", "centre-head", []),
            _unit("test-operations", "centre-head", [FUNCTION_TEST_OPERATIONS]),
        ]
        self.assertIn(
            FUNCTION_QUALITY_ASSURANCE,
            unassigned_functions(_organization(units=units), REQUIRED_FUNCTIONS),
        )


class Independence(unittest.TestCase):
    def test_assurance_under_the_centre_head_is_independent(self):
        self.assertEqual(independence_defects(_organization()), [])

    def test_assurance_reporting_into_operations_is_a_defect(self):
        units = _units()
        for unit in units:
            if unit["unit_id"] == "quality-and-safety":
                unit["reports_to"] = "test-operations"
        defects = independence_defects(_organization(units=units))
        self.assertEqual(len(defects), 2)
        self.assertEqual(defects[0][2], "test-operations")

    def test_assurance_two_levels_under_operations_is_still_a_defect(self):
        units = _units() + [
            _unit("test-floor", "test-operations"),
        ]
        for unit in units:
            if unit["unit_id"] == "quality-and-safety":
                unit["reports_to"] = "test-floor"
        defects = independence_defects(_organization(units=units))
        self.assertTrue(defects)
        self.assertEqual(defects[0][2], "test-operations")

    def test_operations_reporting_under_assurance_is_not_a_defect(self):
        units = _units()
        for unit in units:
            if unit["unit_id"] == "test-operations":
                unit["reports_to"] = "quality-and-safety"
        self.assertEqual(independence_defects(_organization(units=units)), [])


class Interfaces(unittest.TestCase):
    def test_a_complete_interface_set_has_no_gap(self):
        self.assertEqual(interface_gaps(_organization()), [])

    def test_a_missing_required_interface_is_named(self):
        interfaces = [("quality-and-safety", "test-operations")]
        gaps = interface_gaps(_organization(interfaces=interfaces))
        self.assertEqual(gaps, [(FUNCTION_METROLOGY, FUNCTION_TEST_OPERATIONS)])

    def test_two_functions_in_one_unit_need_no_declared_interface(self):
        units = [
            _unit("centre-head", None),
            _unit("quality-and-safety", "centre-head",
                  [FUNCTION_QUALITY_ASSURANCE, FUNCTION_SAFETY_ASSURANCE]),
            _unit("test-operations", "centre-head",
                  [FUNCTION_TEST_OPERATIONS, FUNCTION_METROLOGY]),
            _unit("configuration-office", "centre-head", [FUNCTION_CONFIGURATION]),
        ]
        interfaces = [("quality-and-safety", "test-operations")]
        self.assertEqual(interface_gaps(_organization(units=units, interfaces=interfaces)), [])

    def test_a_dangling_interface_is_named(self):
        interfaces = _interfaces() + [("quality-and-safety", "shipping")]
        self.assertEqual(
            dangling_interfaces(_organization(interfaces=interfaces)),
            [("quality-and-safety", "shipping")],
        )

    def test_a_required_pair_whose_function_is_unheld_is_not_a_gap(self):
        units = [u for u in _units() if u["unit_id"] != "metrology-lab"]
        interfaces = [("quality-and-safety", "test-operations")]
        self.assertEqual(interface_gaps(_organization(units=units, interfaces=interfaces)), [])


class Verdicts(unittest.TestCase):
    def test_a_complete_chart_is_defined(self):
        result = assess_organization(_case())
        self.assertEqual(result["verdict"], ORGANIZATION_DEFINED)
        self.assertEqual(result["findings"], [])

    def test_a_chart_never_drawn_short_circuits(self):
        result = assess_organization(_case(organization=_organization(defined=False)))
        self.assertEqual(result["verdict"], ORGANIZATION_UNDEFINED)

    def test_a_chart_with_no_units_is_undefined(self):
        result = assess_organization(_case(organization=_organization(units=[])))
        self.assertEqual(result["verdict"], ORGANIZATION_UNDEFINED)

    def test_a_structural_defect_outranks_a_missing_function(self):
        units = [_unit("alpha", "beta"), _unit("beta", "alpha")]
        result = assess_organization(_case(organization=_organization(units=units)))
        self.assertEqual(result["verdict"], STRUCTURE_INVALID)

    def test_a_missing_function_outranks_an_independence_defect(self):
        units = [
            _unit("centre-head", None),
            _unit("quality-and-safety", "test-operations",
                  [FUNCTION_QUALITY_ASSURANCE, FUNCTION_SAFETY_ASSURANCE]),
            _unit("test-operations", "centre-head", [FUNCTION_TEST_OPERATIONS]),
            _unit("configuration-office", "centre-head", [FUNCTION_CONFIGURATION]),
        ]
        result = assess_organization(_case(organization=_organization(units=units)))
        self.assertEqual(result["verdict"], FUNCTION_MISSING)

    def test_an_independence_defect_outranks_an_interface_gap(self):
        units = _units()
        for unit in units:
            if unit["unit_id"] == "quality-and-safety":
                unit["reports_to"] = "test-operations"
        organization = _organization(units=units, interfaces=[])
        result = assess_organization(_case(organization=organization))
        self.assertEqual(result["verdict"], INDEPENDENCE_COMPROMISED)

    def test_an_interface_gap_is_the_last_verdict_before_pass(self):
        result = assess_organization(_case(organization=_organization(interfaces=[])))
        self.assertEqual(result["verdict"], INTERFACE_GAPS)
        self.assertEqual(len(result["interface_gaps"]), 3)

    def test_a_shared_function_is_an_advisory_not_a_verdict(self):
        units = _units() + [
            _unit("site-safety", "centre-head", [FUNCTION_SAFETY_ASSURANCE])
        ]
        result = assess_organization(_case(organization=_organization(units=units)))
        self.assertEqual(result["verdict"], ORGANIZATION_DEFINED)
        self.assertEqual(len(result["advisories"]), 1)

    def test_an_unrecognised_required_function_override_is_refused(self):
        with self.assertRaises(ValueError):
            assess_organization(_case(required_functions=["canteen-function"]))

    def test_a_case_without_an_organization_is_refused(self):
        with self.assertRaises(ValueError):
            assess_organization({"required_functions": REQUIRED_FUNCTIONS})

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_organization(("organization",))


if __name__ == "__main__":
    unittest.main()
