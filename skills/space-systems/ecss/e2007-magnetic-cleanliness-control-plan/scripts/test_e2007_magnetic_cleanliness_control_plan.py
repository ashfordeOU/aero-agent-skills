#!/usr/bin/env python3
"""Gate 3 contract test for e2007-magnetic-cleanliness-control-plan.

Stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_magnetic_cleanliness_control_plan.py
"""

import math
import unittest

from e2007_magnetic_cleanliness_control_plan_logic import (
    ALLOCATION_METHODS,
    REQUIRED_PLAN_SECTIONS,
    SCREENING_LEVELS,
    allocate_emission_limits,
    assess_magnetic_cleanliness_plan,
    categorize_screening_level,
    check_item_emission,
    combined_field_nt,
    dipole_field_nt,
    validate_plan_sections,
)


def item(**over):
    base = {
        "id": "star-tracker",
        "declared_moment_am2": 0.001,
        "ferromagnetic_mass_kg": 0.0,
        "contains_permanent_magnet": False,
        "carries_current_loop": False,
        "screening_status": "complete",
    }
    base.update(over)
    return base


def plan(**over):
    base = {
        "sections": list(REQUIRED_PLAN_SECTIONS),
        "system_limit_nt": 20.0,
        "reference_distance_m": 2.0,
        "allocation_method": "equal-share",
        "orientation": "axial",
        "items": [
            item(id="star-tracker", declared_moment_am2=0.001),
            item(id="reaction-wheel", declared_moment_am2=0.002,
                 ferromagnetic_mass_kg=0.2, screening_status="complete"),
            item(id="battery-module", declared_moment_am2=0.0005),
            item(id="rf-transponder", declared_moment_am2=0.0004),
        ],
    }
    base.update(over)
    return base


class TestPlanSections(unittest.TestCase):
    def test_complete_plan_has_no_missing_parts(self):
        self.assertEqual(validate_plan_sections(list(REQUIRED_PLAN_SECTIONS)), ())

    def test_missing_part_is_reported(self):
        missing = validate_plan_sections(["design-guidelines", "verification-approach"])
        self.assertIn("source-emission-limits", missing)
        self.assertIn("magnetic-screening-procedure", missing)
        self.assertIn("dipole-budget-maintenance", missing)

    def test_empty_plan_reports_every_part(self):
        self.assertEqual(len(validate_plan_sections([])), len(REQUIRED_PLAN_SECTIONS))

    def test_section_matching_is_case_insensitive(self):
        self.assertEqual(
            validate_plan_sections([s.upper() for s in REQUIRED_PLAN_SECTIONS]), ()
        )

    def test_bare_string_sections_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan_sections("design-guidelines")

    def test_non_string_section_entry_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan_sections(["design-guidelines", 4])


class TestScreeningLevel(unittest.TestCase):
    def test_permanent_magnet_needs_compensation(self):
        self.assertEqual(
            categorize_screening_level(item(contains_permanent_magnet=True)),
            "dipole-mapping-and-compensation",
        )

    def test_large_moment_needs_compensation(self):
        self.assertEqual(
            categorize_screening_level(item(declared_moment_am2=0.6)),
            "dipole-mapping-and-compensation",
        )

    def test_ferromagnetic_mass_needs_full_mapping(self):
        self.assertEqual(
            categorize_screening_level(item(ferromagnetic_mass_kg=0.5)),
            "full-dipole-mapping",
        )

    def test_moderate_moment_needs_full_mapping(self):
        self.assertEqual(
            categorize_screening_level(item(declared_moment_am2=0.06)),
            "full-dipole-mapping",
        )

    def test_current_loop_needs_powered_mapping(self):
        self.assertEqual(
            categorize_screening_level(item(carries_current_loop=True)),
            "powered-current-loop-mapping",
        )

    def test_small_moment_needs_single_axis_screening(self):
        self.assertEqual(
            categorize_screening_level(item(declared_moment_am2=0.006)),
            "single-axis-screening",
        )

    def test_quiet_item_is_exempt(self):
        self.assertEqual(categorize_screening_level(item()), "screening-exempt")

    def test_every_level_is_a_declared_level(self):
        for candidate in (
            item(contains_permanent_magnet=True),
            item(ferromagnetic_mass_kg=1.0),
            item(carries_current_loop=True),
            item(declared_moment_am2=0.006),
            item(),
        ):
            self.assertIn(categorize_screening_level(candidate), SCREENING_LEVELS)

    def test_negative_moment_rejected(self):
        with self.assertRaises(ValueError):
            categorize_screening_level(item(declared_moment_am2=-0.1))

    def test_negative_mass_rejected(self):
        with self.assertRaises(ValueError):
            categorize_screening_level(item(ferromagnetic_mass_kg=-1.0))

    def test_non_boolean_magnet_flag_rejected(self):
        with self.assertRaises(ValueError):
            categorize_screening_level(item(contains_permanent_magnet="yes"))

    def test_missing_item_key_rejected(self):
        broken = item()
        del broken["carries_current_loop"]
        with self.assertRaises(ValueError):
            categorize_screening_level(broken)


class TestDipoleField(unittest.TestCase):
    def test_axial_field_matches_hand_calculation(self):
        self.assertAlmostEqual(dipole_field_nt(0.05, 1.0, "axial"), 10.0, places=9)

    def test_equatorial_field_is_half_the_axial_field(self):
        axial = dipole_field_nt(0.05, 1.0, "axial")
        equatorial = dipole_field_nt(0.05, 1.0, "equatorial")
        self.assertAlmostEqual(equatorial, axial / 2.0, places=12)

    def test_inverse_cube_falloff(self):
        near = dipole_field_nt(0.05, 1.0, "axial")
        far = dipole_field_nt(0.05, 2.0, "axial")
        self.assertAlmostEqual(near / far, 8.0, places=9)

    def test_zero_moment_gives_zero_field(self):
        self.assertAlmostEqual(dipole_field_nt(0.0, 1.0, "axial"), 0.0, places=12)

    def test_orientation_is_case_insensitive(self):
        self.assertAlmostEqual(
            dipole_field_nt(0.05, 1.0, " Axial "), 10.0, places=9
        )

    def test_zero_distance_rejected(self):
        with self.assertRaises(ValueError):
            dipole_field_nt(0.05, 0.0, "axial")

    def test_negative_moment_rejected(self):
        with self.assertRaises(ValueError):
            dipole_field_nt(-0.05, 1.0, "axial")

    def test_unknown_orientation_rejected(self):
        with self.assertRaises(ValueError):
            dipole_field_nt(0.05, 1.0, "radial")

    def test_non_string_orientation_rejected(self):
        with self.assertRaises(ValueError):
            dipole_field_nt(0.05, 1.0, 2)


class TestAllocation(unittest.TestCase):
    def test_equal_share_divides_by_count(self):
        self.assertAlmostEqual(
            allocate_emission_limits(20.0, 4, "equal-share"), 5.0, places=12
        )

    def test_root_sum_square_divides_by_sqrt_count(self):
        self.assertAlmostEqual(
            allocate_emission_limits(30.0, 9, "root-sum-square"), 10.0, places=12
        )

    def test_root_sum_square_is_less_conservative(self):
        equal = allocate_emission_limits(30.0, 9, "equal-share")
        rss = allocate_emission_limits(30.0, 9, "root-sum-square")
        self.assertGreater(rss, equal)

    def test_single_item_gets_the_whole_limit(self):
        for method in ALLOCATION_METHODS:
            self.assertAlmostEqual(
                allocate_emission_limits(12.5, 1, method), 12.5, places=12
            )

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            allocate_emission_limits(0.0, 4, "equal-share")

    def test_zero_count_rejected(self):
        with self.assertRaises(ValueError):
            allocate_emission_limits(20.0, 0, "equal-share")

    def test_non_integer_count_rejected(self):
        with self.assertRaises(ValueError):
            allocate_emission_limits(20.0, 4.5, "equal-share")

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            allocate_emission_limits(20.0, 4, "worst-case-sum")


class TestItemEmission(unittest.TestCase):
    def test_quiet_item_is_within_limit(self):
        record = check_item_emission(item(), 5.0, 2.0, "axial")
        self.assertTrue(record["within_limit"])
        self.assertFalse(record["screening_gap"])

    def test_exactly_on_limit_item_is_within_limit(self):
        allocation = allocate_emission_limits(20.0, 3, "equal-share")
        on_limit = item(id="on-limit", declared_moment_am2=0.0576)
        record = check_item_emission(on_limit, allocation, 1.2, "axial")
        self.assertGreater(record["field_nt"], allocation)
        self.assertAlmostEqual(record["field_nt"], allocation, places=9)
        self.assertTrue(record["within_limit"])

    def test_loud_item_breaches_its_limit(self):
        record = check_item_emission(item(declared_moment_am2=1.0), 5.0, 2.0, "axial")
        self.assertFalse(record["within_limit"])

    def test_unscreened_item_reports_a_gap(self):
        record = check_item_emission(
            item(ferromagnetic_mass_kg=0.5, screening_status="none"), 5.0, 2.0, "axial"
        )
        self.assertTrue(record["screening_gap"])
        self.assertEqual(record["screening_level"], "full-dipole-mapping")

    def test_exempt_item_without_screening_is_not_a_gap(self):
        record = check_item_emission(item(screening_status="none"), 5.0, 2.0, "axial")
        self.assertFalse(record["screening_gap"])

    def test_planned_screening_counts_as_recorded(self):
        record = check_item_emission(
            item(ferromagnetic_mass_kg=0.5, screening_status="planned"), 5.0, 2.0, "axial"
        )
        self.assertFalse(record["screening_gap"])

    def test_unknown_screening_status_rejected(self):
        with self.assertRaises(ValueError):
            check_item_emission(item(screening_status="maybe"), 5.0, 2.0, "axial")

    def test_zero_allocation_rejected(self):
        with self.assertRaises(ValueError):
            check_item_emission(item(), 0.0, 2.0, "axial")


class TestCombinedField(unittest.TestCase):
    def test_root_sum_square_of_two_contributions(self):
        self.assertAlmostEqual(combined_field_nt([3.0, 4.0]), 5.0, places=12)

    def test_single_contribution_passes_through(self):
        self.assertAlmostEqual(combined_field_nt([7.5]), 7.5, places=12)

    def test_matches_math_hypot(self):
        self.assertAlmostEqual(
            combined_field_nt([1.1, 2.2, 3.3]), math.hypot(1.1, 2.2, 3.3), places=12
        )

    def test_empty_sequence_rejected(self):
        with self.assertRaises(ValueError):
            combined_field_nt([])

    def test_negative_contribution_rejected(self):
        with self.assertRaises(ValueError):
            combined_field_nt([3.0, -4.0])


class TestPlanAudit(unittest.TestCase):
    def test_clean_plan_is_compliant(self):
        out = assess_magnetic_cleanliness_plan(plan())
        self.assertTrue(out["compliant"])
        self.assertEqual(out["findings"], ())
        self.assertEqual(out["missing_sections"], ())

    def test_allocation_is_reported(self):
        out = assess_magnetic_cleanliness_plan(plan())
        self.assertAlmostEqual(out["allocated_limit_nt"], 5.0, places=12)

    def test_missing_section_is_a_finding(self):
        sections = [s for s in REQUIRED_PLAN_SECTIONS if s != "design-guidelines"]
        out = assess_magnetic_cleanliness_plan(plan(sections=sections))
        self.assertFalse(out["compliant"])
        self.assertEqual(out["missing_sections"], ("design-guidelines",))

    def test_loud_item_is_a_finding(self):
        items = plan()["items"]
        items[0] = item(id="magnetorquer", declared_moment_am2=2.0,
                        contains_permanent_magnet=True, screening_status="complete")
        out = assess_magnetic_cleanliness_plan(plan(items=items))
        self.assertFalse(out["compliant"])
        self.assertTrue(any("allocation" in f for f in out["findings"]))

    def test_unscreened_item_is_a_finding(self):
        items = plan()["items"]
        items[1] = item(id="reaction-wheel", declared_moment_am2=0.002,
                        ferromagnetic_mass_kg=0.2, screening_status="none")
        out = assess_magnetic_cleanliness_plan(plan(items=items))
        self.assertFalse(out["compliant"])
        self.assertTrue(any("magnetic-screening" in f for f in out["findings"]))

    def test_uniform_allocation_is_consistent_with_the_combined_check(self):
        items = [
            item(id="unit-%d" % i, declared_moment_am2=0.007, screening_status="complete")
            for i in range(4)
        ]
        out = assess_magnetic_cleanliness_plan(
            plan(items=items, system_limit_nt=3.0, reference_distance_m=1.0,
                 allocation_method="root-sum-square")
        )
        self.assertTrue(all(r["within_limit"] for r in out["records"]))
        self.assertTrue(out["system_within_limit"])
        self.assertTrue(out["uniform_allocation_used"])

    def test_negotiated_allocations_can_overspend_the_system_limit(self):
        items = [
            item(id="unit-%d" % i, declared_moment_am2=0.009,
                 screening_status="complete", allocated_limit_nt=2.0)
            for i in range(4)
        ]
        out = assess_magnetic_cleanliness_plan(
            plan(items=items, system_limit_nt=3.0, reference_distance_m=1.0,
                 allocation_method="root-sum-square")
        )
        self.assertTrue(all(r["within_limit"] for r in out["records"]))
        self.assertFalse(out["system_within_limit"])
        self.assertFalse(out["compliant"])
        self.assertEqual(len(out["negotiated_allocation_ids"]), 4)

    def test_negotiated_allocation_governs_that_item(self):
        items = plan()["items"]
        items[0] = item(id="star-tracker", declared_moment_am2=0.001,
                        allocated_limit_nt=0.01)
        out = assess_magnetic_cleanliness_plan(plan(items=items))
        self.assertFalse(out["records"][0]["within_limit"])
        self.assertAlmostEqual(out["records"][0]["allocated_limit_nt"], 0.01, places=12)
        self.assertFalse(out["uniform_allocation_used"])

    def test_non_positive_negotiated_allocation_rejected(self):
        items = plan()["items"]
        items[0] = item(id="star-tracker", declared_moment_am2=0.001,
                        allocated_limit_nt=0.0)
        with self.assertRaises(ValueError):
            assess_magnetic_cleanliness_plan(plan(items=items))

    def test_equatorial_orientation_halves_the_total(self):
        axial = assess_magnetic_cleanliness_plan(plan())["combined_field_nt"]
        equatorial = assess_magnetic_cleanliness_plan(plan(orientation="equatorial"))[
            "combined_field_nt"
        ]
        self.assertAlmostEqual(equatorial, axial / 2.0, places=12)

    def test_empty_item_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_magnetic_cleanliness_plan(plan(items=[]))

    def test_duplicate_item_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_magnetic_cleanliness_plan(plan(items=[item(), item()]))

    def test_blank_item_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_magnetic_cleanliness_plan(plan(items=[item(id="   ")]))

    def test_missing_plan_key_rejected(self):
        broken = plan()
        del broken["reference_distance_m"]
        with self.assertRaises(ValueError):
            assess_magnetic_cleanliness_plan(broken)

    def test_non_positive_system_limit_rejected(self):
        with self.assertRaises(ValueError):
            assess_magnetic_cleanliness_plan(plan(system_limit_nt=0.0))

    def test_repeat_audit_is_deterministic(self):
        first = assess_magnetic_cleanliness_plan(plan())
        second = assess_magnetic_cleanliness_plan(plan())
        self.assertEqual(first["findings"], second["findings"])
        self.assertAlmostEqual(
            first["combined_field_nt"], second["combined_field_nt"], places=12
        )


if __name__ == "__main__":
    unittest.main()
