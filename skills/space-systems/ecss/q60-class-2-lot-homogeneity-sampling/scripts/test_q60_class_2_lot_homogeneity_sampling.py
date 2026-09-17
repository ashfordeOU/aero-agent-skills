#!/usr/bin/env python3
"""Contract test for the class 2 radiation test sample set composition (offline)."""

import copy
import unittest

from q60_class_2_lot_homogeneity_sampling_logic import (
    BASIS_SUPPORTED_SCOPE,
    CONTROL_COUNT_SHORT,
    DEFAULT_SAMPLE_PLAN,
    IRRADIATED_COUNT_SHORT,
    RADIATION_TEST_METHODS,
    SAMPLE_SET_COMPOSED,
    SCOPE_EXCEEDS_BASIS,
    SPARE_COUNT_SHORT,
    SPECIMEN_OUTSIDE_BASIS,
    SPECIMEN_ROLES,
    TRACEABILITY_AXES,
    TRACEABILITY_BASES,
    assess_radiation_sample_set,
    coverage_fraction,
    partition_specimens,
    required_axes,
    required_sample_size,
    role_counts,
    scope_is_supported,
    specimen_mismatches,
    supported_scope,
    validate_flight_lot,
    validate_sample_plan,
    validate_specimen,
    validate_specimens,
)

FLIGHT_LOT = {
    "lot_id": "FL-2201",
    "part_number": "PN-4478",
    "manufacturer": "MFR-A",
    "die_revision": "C",
    "wafer_diffusion_lot": "WDL-77",
    "assembly_date_code": "2218",
    "package_style": "CQFP-64",
}


def _specimen(specimen_id, role="irradiated", **overrides):
    record = {"specimen_id": specimen_id, "role": role}
    for axis in TRACEABILITY_AXES:
        record[axis] = FLIGHT_LOT[axis]
    record.update(overrides)
    return record


def _set(irradiated=0, control=0, spare=0):
    specimens = []
    for index in range(irradiated):
        specimens.append(_specimen("IR-%d" % (index,), "irradiated"))
    for index in range(control):
        specimens.append(_specimen("CT-%d" % (index,), "control"))
    for index in range(spare):
        specimens.append(_specimen("SP-%d" % (index,), "spare"))
    return specimens


def _case(**overrides):
    case = {
        "flight_lot": copy.deepcopy(FLIGHT_LOT),
        "specimens": _set(irradiated=5, control=2, spare=2),
        "basis": "same-wafer-diffusion-lot",
        "method": "total-ionising-dose",
        "bias_conditions": 1,
        "declared_result_scope": "lot-specific",
    }
    case.update(overrides)
    return case


class PlanTests(unittest.TestCase):
    def test_default_plan_covers_every_method(self):
        plan = validate_sample_plan()
        self.assertEqual(sorted(plan), sorted(RADIATION_TEST_METHODS))

    def test_default_plan_is_copied_not_shared(self):
        plan = validate_sample_plan()
        plan["total-ionising-dose"]["control"] = 99
        self.assertEqual(DEFAULT_SAMPLE_PLAN["total-ionising-dose"]["control"], 2)

    def test_plan_missing_method_is_rejected(self):
        broken = {
            name: dict(entry)
            for name, entry in DEFAULT_SAMPLE_PLAN.items()
            if name != "single-event-effects"
        }
        with self.assertRaises(ValueError):
            validate_sample_plan(broken)

    def test_plan_with_zero_irradiated_is_rejected(self):
        broken = {name: dict(entry) for name, entry in DEFAULT_SAMPLE_PLAN.items()}
        broken["total-ionising-dose"]["irradiated_per_condition"] = 0
        with self.assertRaises(ValueError):
            validate_sample_plan(broken)

    def test_plan_with_non_boolean_consumption_flag_is_rejected(self):
        broken = {name: dict(entry) for name, entry in DEFAULT_SAMPLE_PLAN.items()}
        broken["total-ionising-dose"]["conditions_consume_specimens"] = 1
        with self.assertRaises(ValueError):
            validate_sample_plan(broken)


class BasisTests(unittest.TestCase):
    def test_wafer_lot_basis_tests_every_axis(self):
        self.assertEqual(required_axes("same-wafer-diffusion-lot"), TRACEABILITY_AXES)

    def test_heritage_basis_tests_fewest_axes(self):
        self.assertLess(
            len(required_axes("same-part-type-heritage")),
            len(required_axes("same-assembly-date-code")),
        )

    def test_unknown_basis_is_rejected(self):
        with self.assertRaises(ValueError):
            required_axes("same-shipping-box")

    def test_every_basis_declares_a_supported_scope(self):
        for basis in TRACEABILITY_BASES:
            self.assertIn(supported_scope(basis), BASIS_SUPPORTED_SCOPE.values())

    def test_lot_specific_claim_needs_the_wafer_lot_basis(self):
        self.assertTrue(scope_is_supported("lot-specific", "same-wafer-diffusion-lot"))
        self.assertFalse(scope_is_supported("lot-specific", "same-assembly-date-code"))

    def test_weaker_claim_on_a_stronger_basis_is_supported(self):
        self.assertTrue(
            scope_is_supported("generic-part-type", "same-wafer-diffusion-lot")
        )

    def test_unknown_scope_is_rejected(self):
        with self.assertRaises(ValueError):
            scope_is_supported("whole-programme", "same-wafer-diffusion-lot")


class ValidationTests(unittest.TestCase):
    def test_flight_lot_missing_an_axis_is_rejected(self):
        lot = copy.deepcopy(FLIGHT_LOT)
        del lot["package_style"]
        with self.assertRaises(ValueError):
            validate_flight_lot(lot)

    def test_flight_lot_with_blank_axis_is_rejected(self):
        lot = copy.deepcopy(FLIGHT_LOT)
        lot["wafer_diffusion_lot"] = "   "
        with self.assertRaises(ValueError):
            validate_flight_lot(lot)

    def test_specimen_with_unknown_role_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_specimen(_specimen("X-1", "witness"))

    def test_specimen_roles_are_the_three_declared_ones(self):
        self.assertEqual(SPECIMEN_ROLES, ("irradiated", "control", "spare"))

    def test_empty_offered_set_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_specimens([])

    def test_duplicate_specimen_id_is_rejected(self):
        specimens = _set(irradiated=2)
        specimens[1]["specimen_id"] = specimens[0]["specimen_id"]
        with self.assertRaises(ValueError):
            validate_specimens(specimens)

    def test_specimen_list_of_wrong_type_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_specimens({"specimen_id": "IR-0"})


class MismatchTests(unittest.TestCase):
    def test_matching_specimen_has_no_mismatch(self):
        self.assertEqual(
            specimen_mismatches(FLIGHT_LOT, _specimen("IR-0"), "same-wafer-diffusion-lot"),
            (),
        )

    def test_other_wafer_lot_is_a_mismatch_on_the_narrow_basis(self):
        odd = _specimen("IR-9", wafer_diffusion_lot="WDL-78")
        self.assertEqual(
            specimen_mismatches(FLIGHT_LOT, odd, "same-wafer-diffusion-lot"),
            ("wafer_diffusion_lot",),
        )

    def test_other_wafer_lot_is_invisible_on_the_date_code_basis(self):
        odd = _specimen("IR-9", wafer_diffusion_lot="WDL-78")
        self.assertEqual(
            specimen_mismatches(FLIGHT_LOT, odd, "same-assembly-date-code"), ()
        )

    def test_partition_places_an_off_lot_specimen_outside(self):
        specimens = _set(irradiated=5, control=2, spare=2)
        specimens[0]["wafer_diffusion_lot"] = "WDL-99"
        split = partition_specimens(FLIGHT_LOT, specimens, "same-wafer-diffusion-lot")
        self.assertEqual(len(split["outside_basis"]), 1)
        self.assertEqual(split["outside_basis"][0]["specimen_id"], "IR-0")
        self.assertEqual(len(split["within_basis"]), 8)


class SizingTests(unittest.TestCase):
    def test_dose_method_multiplies_on_bias_conditions(self):
        size = required_sample_size("total-ionising-dose", 3)
        self.assertEqual(size["irradiated"], 15)
        self.assertEqual(size["control"], 2)
        self.assertEqual(size["total"], 19)

    def test_event_method_does_not_multiply_on_bias_conditions(self):
        one = required_sample_size("single-event-effects", 1)
        four = required_sample_size("single-event-effects", 4)
        self.assertEqual(one["irradiated"], four["irradiated"])

    def test_zero_bias_conditions_is_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_size("total-ionising-dose", 0)

    def test_boolean_bias_conditions_is_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_size("total-ionising-dose", True)

    def test_unknown_method_is_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_size("proton-annealing", 1)

    def test_role_counts_add_up_to_the_offered_set(self):
        counts = role_counts(_set(irradiated=5, control=2, spare=2))
        self.assertEqual(counts, {"irradiated": 5, "control": 2, "spare": 2})


class CoverageTests(unittest.TestCase):
    def test_zero_requirement_is_fully_covered(self):
        self.assertAlmostEqual(coverage_fraction(0, 0), 1.0, places=9)

    def test_exact_requirement_reaches_one(self):
        self.assertAlmostEqual(coverage_fraction(5, 5), 1.0, places=9)

    def test_partial_coverage_is_the_plain_ratio(self):
        self.assertAlmostEqual(coverage_fraction(3, 4), 0.75, places=9)

    def test_surplus_does_not_exceed_one(self):
        self.assertAlmostEqual(coverage_fraction(9, 5), 1.0, places=9)

    def test_negative_availability_is_rejected(self):
        with self.assertRaises(ValueError):
            coverage_fraction(-1, 5)


class AssessmentTests(unittest.TestCase):
    def test_complete_set_is_composed(self):
        result = assess_radiation_sample_set(_case())
        self.assertEqual(result["verdict"], SAMPLE_SET_COMPOSED)
        self.assertTrue(result["composed"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["irradiated_coverage"], 1.0, places=9)

    def test_off_lot_specimen_takes_precedence_over_a_count(self):
        specimens = _set(irradiated=5, control=2, spare=2)
        specimens[0]["package_style"] = "CQFP-84"
        result = assess_radiation_sample_set(_case(specimens=specimens))
        self.assertEqual(result["verdict"], SPECIMEN_OUTSIDE_BASIS)
        self.assertFalse(result["composed"])

    def test_off_lot_specimen_does_not_count_toward_the_roles(self):
        specimens = _set(irradiated=5, control=2, spare=2)
        specimens[0]["die_revision"] = "D"
        result = assess_radiation_sample_set(_case(specimens=specimens))
        self.assertEqual(result["offered_within_basis"]["irradiated"], 4)
        self.assertEqual(result["shortfalls"]["irradiated"], 1)

    def test_overclaimed_scope_is_found(self):
        result = assess_radiation_sample_set(
            _case(basis="same-part-type-heritage", declared_result_scope="lot-specific")
        )
        self.assertEqual(result["verdict"], SCOPE_EXCEEDS_BASIS)
        self.assertEqual(result["supported_result_scope"], "generic-part-type")

    def test_scope_defaults_to_what_the_basis_supports(self):
        case = _case(basis="same-assembly-date-code")
        del case["declared_result_scope"]
        result = assess_radiation_sample_set(case)
        self.assertEqual(result["declared_result_scope"], "date-code-family")
        self.assertEqual(result["verdict"], SAMPLE_SET_COMPOSED)

    def test_short_irradiated_count_is_found(self):
        result = assess_radiation_sample_set(
            _case(specimens=_set(irradiated=3, control=2, spare=2))
        )
        self.assertEqual(result["verdict"], IRRADIATED_COUNT_SHORT)
        self.assertEqual(result["shortfalls"]["irradiated"], 2)
        self.assertAlmostEqual(result["irradiated_coverage"], 0.6, places=9)

    def test_missing_control_group_is_found(self):
        result = assess_radiation_sample_set(
            _case(specimens=_set(irradiated=5, control=0, spare=2))
        )
        self.assertEqual(result["verdict"], CONTROL_COUNT_SHORT)

    def test_short_spares_are_found_last(self):
        result = assess_radiation_sample_set(
            _case(specimens=_set(irradiated=5, control=2, spare=0))
        )
        self.assertEqual(result["verdict"], SPARE_COUNT_SHORT)

    def test_event_method_needs_no_control_group(self):
        result = assess_radiation_sample_set(
            _case(
                method="single-event-latch-up",
                bias_conditions=6,
                specimens=_set(irradiated=2, control=0, spare=1),
            )
        )
        self.assertEqual(result["verdict"], SAMPLE_SET_COMPOSED)

    def test_more_bias_conditions_raise_the_dose_requirement(self):
        result = assess_radiation_sample_set(
            _case(bias_conditions=2, specimens=_set(irradiated=5, control=2, spare=2))
        )
        self.assertEqual(result["required"]["irradiated"], 10)
        self.assertEqual(result["verdict"], IRRADIATED_COUNT_SHORT)

    def test_case_missing_a_key_is_rejected(self):
        case = _case()
        del case["method"]
        with self.assertRaises(ValueError):
            assess_radiation_sample_set(case)

    def test_case_of_wrong_type_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_radiation_sample_set(["total-ionising-dose"])

    def test_result_reports_the_requirement_it_graded_against(self):
        result = assess_radiation_sample_set(_case())
        self.assertEqual(result["required"]["total"], 9)
        self.assertEqual(result["method"], "total-ionising-dose")
        self.assertEqual(result["basis"], "same-wafer-diffusion-lot")


if __name__ == "__main__":
    unittest.main(verbosity=0)
