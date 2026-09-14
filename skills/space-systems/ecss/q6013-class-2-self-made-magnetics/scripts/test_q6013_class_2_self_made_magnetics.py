"""Contract tests for the clause 5.6.8 class 2 supplier-built magnetics.

Every workflow step the SKILL.md sets out is exercised here, together with the
stop conditions the gate 3 contract reviews: a refused screening policy, a
build standard carrying no issue, an unreleased supplier process, a winding
above the density ceiling, a core worked past hot-case saturation, an
insulation margin and a withstand ratio judged at their bounds, a per-unit
screening step never run, a sample step never run, and a sample short of the
units the lot size owes.
"""

import unittest

from q6013_class_2_self_made_magnetics_logic import (
    BUILD_BASIS_NOT_ESTABLISHED,
    DEFAULT_SCREENING_POLICY,
    DESIGN_MARGIN_NOT_DEMONSTRATED,
    DIELECTRIC_WITHSTAND_MEASUREMENT,
    ENCAPSULATION_SECTIONING,
    FULL_SCREENING_STEPS,
    INDUCTANCE_AND_TURNS_RATIO_CHECK,
    INSULATION_RESISTANCE_MEASUREMENT,
    MAGNETIC_MEETS_CLASS_TWO,
    RECOGNISED_SCREENING_STEPS,
    SAMPLE_SCREENING_STEPS,
    SCREENING_COVERAGE_SHORTFALL,
    VISUAL_AND_WORKMANSHIP_INSPECTION,
    WINDING_RESISTANCE_MEASUREMENT,
    WOUND_ASSEMBLY_THERMAL_CYCLING,
    absent_full_screening_steps,
    absent_sample_screening_steps,
    assess_supplier_built_magnetic,
    build_basis_findings,
    flux_utilization,
    insulation_margin_k,
    overloaded_windings,
    required_sample_units,
    sample_shortfall_units,
    screening_coverage,
    validate_build_lot,
    validate_part_identity,
    validate_screening_policy,
    validate_screening_record,
    validate_winding,
    validate_windings,
    winding_current_density,
    withstand_ratio,
)


def _policy(**overrides):
    policy = dict(DEFAULT_SCREENING_POLICY)
    policy.update(overrides)
    return policy


def _part(**overrides):
    part = {
        "designation": "TR-4471 flyback transformer",
        "supplier": "wound-magnetics-subcontractor",
        "build_standard": "MAG-DRW-4471",
        "build_standard_issue": "C",
        "supplier_process_released": True,
        "acceptance_data_delivered": True,
    }
    part.update(overrides)
    return part


def _lot(**overrides):
    lot = {"id": "LOT-4471-02", "lot_size": 40, "delivered_units": 40}
    lot.update(overrides)
    return lot


def _winding(name, **overrides):
    winding = {
        "name": name,
        "turns": 68,
        "conductor_area_mm2": 0.5,
        "rms_current_a": 1.4,
    }
    winding.update(overrides)
    return winding


def _windings():
    return [
        _winding("primary"),
        _winding("secondary", turns=24, conductor_area_mm2=0.8, rms_current_a=3.6),
        _winding("bias", turns=9, conductor_area_mm2=0.2, rms_current_a=0.15),
    ]


def _case(**overrides):
    case = {
        "part": _part(),
        "lot": _lot(),
        "windings": _windings(),
        "peak_flux_mt": 180.0,
        "hot_case_saturation_flux_mt": 300.0,
        "insulation_rating_c": 155.0,
        "hot_spot_c": 118.0,
        "demonstrated_withstand_v": 1500.0,
        "working_voltage_v": 420.0,
        "screening_steps": list(RECOGNISED_SCREENING_STEPS),
        "sample_units_screened": 4,
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_screening_policy(DEFAULT_SCREENING_POLICY),
            DEFAULT_SCREENING_POLICY,
        )

    def test_sample_fraction_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_screening_policy(_policy(sample_fraction=1.6))

    def test_fractional_minimum_sample_refused(self):
        with self.assertRaises(ValueError):
            validate_screening_policy(_policy(min_sample_units=2.5))

    def test_loosened_flux_ceiling_refused(self):
        with self.assertRaises(ValueError):
            validate_screening_policy(_policy(max_flux_utilization=0.95))

    def test_tightened_flux_ceiling_accepted(self):
        self.assertIsNotNone(validate_screening_policy(_policy(max_flux_utilization=0.6)))

    def test_withstand_ratio_below_one_refused(self):
        with self.assertRaises(ValueError):
            validate_screening_policy(_policy(min_withstand_ratio=0.9))

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_screening_policy(["sample_fraction"])


class IdentityTests(unittest.TestCase):
    def test_a_good_part_reads_back_its_build_standard(self):
        record = validate_part_identity(_part())
        self.assertEqual(record["build_standard_issue"], "C")
        self.assertEqual(build_basis_findings(_part()), ())

    def test_blank_supplier_refused(self):
        with self.assertRaises(ValueError):
            validate_part_identity(_part(supplier="   "))

    def test_missing_build_standard_issue_is_a_finding(self):
        findings = build_basis_findings(_part(build_standard_issue=""))
        self.assertEqual(len(findings), 1)
        self.assertIn("issue", findings[0])

    def test_unreleased_process_and_absent_data_both_named(self):
        findings = build_basis_findings(
            _part(supplier_process_released=False, acceptance_data_delivered=False)
        )
        self.assertEqual(len(findings), 2)

    def test_non_boolean_release_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_part_identity(_part(supplier_process_released="mostly"))


class LotAndSampleTests(unittest.TestCase):
    def test_a_good_lot_reads_back_its_counts(self):
        record = validate_build_lot(_lot())
        self.assertEqual(record["lot_size"], 40)

    def test_delivery_larger_than_the_lot_refused(self):
        with self.assertRaises(ValueError):
            validate_build_lot(_lot(delivered_units=41))

    def test_sample_follows_the_lot_size_through_the_fraction(self):
        self.assertEqual(required_sample_units(_lot(lot_size=40, delivered_units=40)), 4)

    def test_a_small_lot_is_floored_at_the_minimum_sample(self):
        self.assertEqual(required_sample_units(_lot(lot_size=5, delivered_units=5)), 2)

    def test_the_sample_never_exceeds_the_lot(self):
        self.assertEqual(required_sample_units(_lot(lot_size=1, delivered_units=1)), 1)

    def test_a_lot_on_an_exact_fraction_boundary_is_not_rounded_up(self):
        self.assertEqual(required_sample_units(_lot(lot_size=30, delivered_units=30)), 3)

    def test_a_met_sample_has_no_shortfall(self):
        self.assertEqual(sample_shortfall_units(_lot(), 4), 0)

    def test_a_thin_sample_reports_the_missing_units(self):
        self.assertEqual(sample_shortfall_units(_lot(), 1), 3)

    def test_screening_more_units_than_were_delivered_refused(self):
        with self.assertRaises(ValueError):
            sample_shortfall_units(_lot(delivered_units=6), 9)


class DesignBasisTests(unittest.TestCase):
    def test_current_density_is_current_over_conductor_area(self):
        self.assertAlmostEqual(
            winding_current_density(_winding("primary")), 2.8, places=9
        )

    def test_a_winding_exactly_on_the_ceiling_passes(self):
        winding = _winding("primary", conductor_area_mm2=1.0, rms_current_a=6.0)
        self.assertEqual(overloaded_windings([winding]), ())

    def test_a_winding_past_the_ceiling_is_named(self):
        winding = _winding("hot", conductor_area_mm2=0.25, rms_current_a=3.0)
        self.assertEqual(overloaded_windings([winding]), ("hot",))

    def test_zero_conductor_area_refused(self):
        with self.assertRaises(ValueError):
            validate_winding(_winding("primary", conductor_area_mm2=0.0))

    def test_a_winding_declared_twice_refused(self):
        with self.assertRaises(ValueError):
            validate_windings([_winding("primary"), _winding("primary")])

    def test_an_empty_winding_set_refused(self):
        with self.assertRaises(ValueError):
            validate_windings([])

    def test_flux_utilization_is_read_at_the_hot_case(self):
        self.assertAlmostEqual(flux_utilization(240.0, 300.0), 0.8, places=9)

    def test_zero_saturation_flux_refused(self):
        with self.assertRaises(ValueError):
            flux_utilization(180.0, 0.0)

    def test_insulation_margin_is_rating_less_hot_spot(self):
        self.assertAlmostEqual(insulation_margin_k(155.0, 145.0), 10.0, places=9)

    def test_withstand_ratio_is_demonstrated_over_working(self):
        self.assertAlmostEqual(withstand_ratio(840.0, 420.0), 2.0, places=9)

    def test_zero_working_voltage_refused(self):
        with self.assertRaises(ValueError):
            withstand_ratio(1500.0, 0.0)


class ScreeningRecordTests(unittest.TestCase):
    def test_the_two_screening_sets_do_not_overlap(self):
        self.assertEqual(
            set(FULL_SCREENING_STEPS) & set(SAMPLE_SCREENING_STEPS), set()
        )

    def test_an_unrecognised_step_refused(self):
        with self.assertRaises(ValueError):
            validate_screening_record(["magnetic-vibes-check"])

    def test_a_step_declared_twice_refused(self):
        with self.assertRaises(ValueError):
            validate_screening_record(
                [VISUAL_AND_WORKMANSHIP_INSPECTION, VISUAL_AND_WORKMANSHIP_INSPECTION]
            )

    def test_a_full_set_covers_every_step(self):
        self.assertAlmostEqual(
            screening_coverage(RECOGNISED_SCREENING_STEPS), 1.0, places=9
        )
        self.assertEqual(absent_full_screening_steps(RECOGNISED_SCREENING_STEPS), ())
        self.assertEqual(absent_sample_screening_steps(RECOGNISED_SCREENING_STEPS), ())

    def test_per_unit_and_sample_gaps_are_reported_apart(self):
        declared = [
            step
            for step in RECOGNISED_SCREENING_STEPS
            if step not in (INSULATION_RESISTANCE_MEASUREMENT, ENCAPSULATION_SECTIONING)
        ]
        self.assertEqual(
            absent_full_screening_steps(declared), (INSULATION_RESISTANCE_MEASUREMENT,)
        )
        self.assertEqual(
            absent_sample_screening_steps(declared), (ENCAPSULATION_SECTIONING,)
        )


class AssessmentTests(unittest.TestCase):
    def test_a_sound_delivery_meets_the_class(self):
        result = assess_supplier_built_magnetic(_case())
        self.assertEqual(result["verdict"], MAGNETIC_MEETS_CLASS_TWO)
        self.assertEqual(result["sample_shortfall_units"], 0)
        self.assertAlmostEqual(result["flux_utilization"], 0.6, places=9)

    def test_an_absent_part_has_no_build_basis(self):
        case = _case()
        del case["part"]
        result = assess_supplier_built_magnetic(case)
        self.assertEqual(result["verdict"], BUILD_BASIS_NOT_ESTABLISHED)
        self.assertTrue(result["findings"])

    def test_an_unreleased_process_closes_before_any_measurement(self):
        result = assess_supplier_built_magnetic(
            _case(part=_part(supplier_process_released=False))
        )
        self.assertEqual(result["verdict"], BUILD_BASIS_NOT_ESTABLISHED)
        self.assertIsNone(result["flux_utilization"])

    def test_a_saturated_core_fails_on_design_margin(self):
        result = assess_supplier_built_magnetic(_case(peak_flux_mt=282.0))
        self.assertEqual(result["verdict"], DESIGN_MARGIN_NOT_DEMONSTRATED)

    def test_a_core_exactly_on_the_utilization_ceiling_passes(self):
        result = assess_supplier_built_magnetic(_case(peak_flux_mt=240.0))
        self.assertEqual(result["verdict"], MAGNETIC_MEETS_CLASS_TWO)
        self.assertAlmostEqual(result["flux_utilization"], 0.8, places=9)

    def test_a_thermal_and_a_withstand_finding_are_both_kept(self):
        result = assess_supplier_built_magnetic(
            _case(hot_spot_c=152.0, demonstrated_withstand_v=600.0)
        )
        self.assertEqual(result["verdict"], DESIGN_MARGIN_NOT_DEMONSTRATED)
        self.assertEqual(len(result["findings"]), 2)

    def test_an_overloaded_winding_is_named_in_the_result(self):
        windings = _windings()
        windings[1]["rms_current_a"] = 9.6
        result = assess_supplier_built_magnetic(_case(windings=windings))
        self.assertEqual(result["verdict"], DESIGN_MARGIN_NOT_DEMONSTRATED)
        self.assertEqual(result["overloaded_windings"], ("secondary",))

    def test_a_missing_per_unit_step_is_a_coverage_shortfall(self):
        declared = [
            step
            for step in RECOGNISED_SCREENING_STEPS
            if step != DIELECTRIC_WITHSTAND_MEASUREMENT
        ]
        result = assess_supplier_built_magnetic(_case(screening_steps=declared))
        self.assertEqual(result["verdict"], SCREENING_COVERAGE_SHORTFALL)
        self.assertEqual(
            result["absent_full_screening_steps"], (DIELECTRIC_WITHSTAND_MEASUREMENT,)
        )

    def test_every_absent_step_is_named_not_only_the_first(self):
        declared = [VISUAL_AND_WORKMANSHIP_INSPECTION, WINDING_RESISTANCE_MEASUREMENT]
        result = assess_supplier_built_magnetic(_case(screening_steps=declared))
        self.assertEqual(result["verdict"], SCREENING_COVERAGE_SHORTFALL)
        self.assertEqual(len(result["absent_full_screening_steps"]), 2)
        self.assertEqual(len(result["absent_sample_screening_steps"]), 3)

    def test_a_thin_sample_closes_the_assessment(self):
        result = assess_supplier_built_magnetic(_case(sample_units_screened=1))
        self.assertEqual(result["verdict"], SCREENING_COVERAGE_SHORTFALL)
        self.assertEqual(result["sample_shortfall_units"], 3)

    def test_a_part_delivery_travels_as_an_advisory_not_a_finding(self):
        result = assess_supplier_built_magnetic(
            _case(lot=_lot(lot_size=40, delivered_units=12))
        )
        self.assertEqual(result["verdict"], MAGNETIC_MEETS_CLASS_TWO)
        self.assertEqual(len(result["advisories"]), 1)
        self.assertIn("LOT-4471-02", result["advisories"][0])

    def test_the_sample_step_names_survive_into_the_result(self):
        declared = [
            step
            for step in RECOGNISED_SCREENING_STEPS
            if step
            not in (INDUCTANCE_AND_TURNS_RATIO_CHECK, WOUND_ASSEMBLY_THERMAL_CYCLING)
        ]
        result = assess_supplier_built_magnetic(_case(screening_steps=declared))
        self.assertEqual(
            result["absent_sample_screening_steps"],
            (INDUCTANCE_AND_TURNS_RATIO_CHECK, WOUND_ASSEMBLY_THERMAL_CYCLING),
        )

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_supplier_built_magnetic(["part"])


if __name__ == "__main__":
    unittest.main()
