#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 6.3.7.3 attitude-control-
driven magnetic cleanliness.

Exercises scripts/e20_attitude_control_magnetic_cleanliness_logic.py
(stdlib unittest, offline). Contract: the centred-dipole field falls
with the cube of the orbit radius and doubles from the equator to the
pole; the circular orbit period follows the three-halves power of the
semi-major axis; the disturbance torque is the residual moment times
the field times the alignment factor, and inverting it gives the
allowable residual dipole moment; every contributor kind maps to
exactly one variation family and an unrecognized kind raises; the
allowance splits into shares that must sum to the whole, with the sum
tested against representation error; a long-term contributor compounds
to end of life and an undeclared drift rate is a record finding; a
family sum sitting exactly on its allocation is compliant; the momentum
accumulated over one orbit is checked against the desaturation
capacity, with a missing capacity reported rather than assumed; and the
aggregated review is compliant only when every list is empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_attitude_control_magnetic_cleanliness_logic as mc  # noqa: E402


def _clean_spacecraft():
    """A low-orbit spacecraft that satisfies every clause 6.3.7.3
    check."""
    return {
        "spacecraft_id": "SC-LEO-01",
        "altitude_km": 700.0,
        "magnetic_latitude_deg": 0.0,
        "torque_allowance_nm": 5.0e-6,
        "alignment_factor": 1.0,
        "mission_years": 5.0,
        "momentum_capacity_nms": 0.05,
        "contributors": [
            {
                "contributor_id": "MAG-01",
                "kind": "permanent_magnet",
                "moment_am2": 0.05,
            },
            {
                "contributor_id": "BRK-01",
                "kind": "ferromagnetic_bracket",
                "moment_am2": 0.03,
            },
            {
                "contributor_id": "HTR-01",
                "kind": "heater_switching_loop",
                "moment_am2": 0.02,
            },
            {
                "contributor_id": "MTQ-01",
                "kind": "magnetorquer_duty_cycle",
                "moment_am2": 0.01,
            },
            {
                "contributor_id": "SA-01",
                "kind": "solar_array_current_degradation",
                "moment_am2": 0.01,
                "drift_fraction_per_year": 0.02,
            },
        ],
    }


class GeomagneticFieldTest(unittest.TestCase):
    def test_equatorial_surface_value_matches_the_model_constant(self):
        self.assertAlmostEqual(
            mc.geomagnetic_field_t(0.0, 0.0),
            mc.EQUATORIAL_SURFACE_FIELD_T,
            places=12,
        )

    def test_pole_is_twice_the_equator_at_the_same_radius(self):
        self.assertAlmostEqual(
            mc.geomagnetic_field_t(0.0, 90.0)
            / mc.geomagnetic_field_t(0.0, 0.0),
            2.0,
            places=9,
        )

    def test_southern_pole_matches_the_northern_pole(self):
        self.assertAlmostEqual(
            mc.geomagnetic_field_t(500.0, -90.0),
            mc.geomagnetic_field_t(500.0, 90.0),
            places=12,
        )

    def test_field_falls_with_the_cube_of_the_orbit_radius(self):
        altitude_km = 6371.0
        expected = mc.EQUATORIAL_SURFACE_FIELD_T / 8.0
        self.assertAlmostEqual(
            mc.geomagnetic_field_t(altitude_km, 0.0), expected, places=12
        )

    def test_low_orbit_field_far_exceeds_geostationary(self):
        self.assertGreater(
            mc.geomagnetic_field_t(700.0, 0.0),
            50.0 * mc.geomagnetic_field_t(35786.0, 0.0),
        )

    def test_field_is_strictly_decreasing_with_altitude(self):
        values = [mc.geomagnetic_field_t(h, 0.0) for h in (0.0, 400.0, 800.0)]
        for higher, lower in zip(values, values[1:]):
            self.assertGreater(higher, lower)

    def test_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            mc.geomagnetic_field_t(-1.0, 0.0)

    def test_latitude_beyond_the_pole_raises(self):
        with self.assertRaises(ValueError):
            mc.geomagnetic_field_t(700.0, 90.1)

    def test_latitude_below_the_south_pole_raises(self):
        with self.assertRaises(ValueError):
            mc.geomagnetic_field_t(700.0, -90.1)


class OrbitPeriodTest(unittest.TestCase):
    def test_surface_period_is_about_eighty_four_minutes(self):
        self.assertAlmostEqual(
            mc.orbit_period_s(0.0) / 60.0, 84.4, delta=0.5
        )

    def test_seven_hundred_kilometre_period_is_about_ninety_nine_minutes(self):
        self.assertAlmostEqual(
            mc.orbit_period_s(700.0) / 60.0, 98.6, delta=0.5
        )

    def test_period_follows_the_three_halves_power_of_the_radius(self):
        low = mc.orbit_period_s(0.0)
        high = mc.orbit_period_s(mc.EARTH_RADIUS_KM)
        self.assertAlmostEqual(high / low, 2.0 ** 1.5, places=9)

    def test_period_increases_with_altitude(self):
        self.assertGreater(mc.orbit_period_s(800.0), mc.orbit_period_s(400.0))

    def test_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            mc.orbit_period_s(-10.0)


class MagneticDisturbanceTorqueTest(unittest.TestCase):
    def test_torque_is_moment_times_field(self):
        self.assertAlmostEqual(
            mc.magnetic_disturbance_torque_nm(0.2, 2.0e-5), 4.0e-6, places=15
        )

    def test_alignment_factor_scales_the_torque(self):
        self.assertAlmostEqual(
            mc.magnetic_disturbance_torque_nm(0.2, 2.0e-5, 0.5),
            2.0e-6,
            places=15,
        )

    def test_moment_parallel_to_the_field_produces_no_torque(self):
        self.assertAlmostEqual(
            mc.magnetic_disturbance_torque_nm(0.2, 2.0e-5, 0.0),
            0.0,
            places=18,
        )

    def test_zero_moment_produces_no_torque(self):
        self.assertAlmostEqual(
            mc.magnetic_disturbance_torque_nm(0.0, 2.0e-5), 0.0, places=18
        )

    def test_negative_moment_raises(self):
        with self.assertRaises(ValueError):
            mc.magnetic_disturbance_torque_nm(-0.1, 2.0e-5)

    def test_non_positive_field_raises(self):
        with self.assertRaises(ValueError):
            mc.magnetic_disturbance_torque_nm(0.1, 0.0)

    def test_alignment_factor_above_one_raises(self):
        with self.assertRaises(ValueError):
            mc.magnetic_disturbance_torque_nm(0.1, 2.0e-5, 1.5)


class AllowableResidualDipoleTest(unittest.TestCase):
    def test_allowance_inverts_the_torque_relation(self):
        field_t = 2.0e-5
        allowable = mc.allowable_residual_dipole_am2(4.0e-6, field_t)
        self.assertAlmostEqual(
            mc.magnetic_disturbance_torque_nm(allowable, field_t),
            4.0e-6,
            places=15,
        )

    def test_alignment_factor_relaxes_the_allowance(self):
        loose = mc.allowable_residual_dipole_am2(4.0e-6, 2.0e-5, 0.5)
        tight = mc.allowable_residual_dipole_am2(4.0e-6, 2.0e-5, 1.0)
        self.assertAlmostEqual(loose, 2.0 * tight, places=12)

    def test_low_orbit_allowance_is_tighter_than_geostationary(self):
        low = mc.allowable_residual_dipole_am2(
            5.0e-6, mc.geomagnetic_field_t(700.0, 0.0)
        )
        high = mc.allowable_residual_dipole_am2(
            5.0e-6, mc.geomagnetic_field_t(35786.0, 0.0)
        )
        self.assertLess(low, high)

    def test_zero_torque_allowance_raises(self):
        with self.assertRaises(ValueError):
            mc.allowable_residual_dipole_am2(0.0, 2.0e-5)

    def test_non_positive_field_raises(self):
        with self.assertRaises(ValueError):
            mc.allowable_residual_dipole_am2(4.0e-6, -1.0)

    def test_zero_alignment_factor_raises(self):
        with self.assertRaises(ValueError):
            mc.allowable_residual_dipole_am2(4.0e-6, 2.0e-5, 0.0)


class CategorizeMomentContributorTest(unittest.TestCase):
    def test_permanent_magnet_is_steady(self):
        self.assertEqual(
            mc.categorize_moment_contributor("permanent_magnet"), "steady"
        )

    def test_heater_switching_loop_is_transient(self):
        self.assertEqual(
            mc.categorize_moment_contributor("heater_switching_loop"),
            "transient",
        )

    def test_magnetorquer_duty_cycle_is_transient(self):
        self.assertEqual(
            mc.categorize_moment_contributor("magnetorquer_duty_cycle"),
            "transient",
        )

    def test_battery_current_drift_is_long_term(self):
        self.assertEqual(
            mc.categorize_moment_contributor("battery_current_drift"),
            "long_term",
        )

    def test_every_contributor_kind_lands_in_a_known_family(self):
        for kind in mc.MOMENT_CATEGORY_BY_CONTRIBUTOR_KIND:
            self.assertIn(
                mc.categorize_moment_contributor(kind), mc.MOMENT_CATEGORIES
            )

    def test_unknown_contributor_kind_raises(self):
        with self.assertRaises(ValueError):
            mc.categorize_moment_contributor("sunlight")

    def test_none_contributor_kind_raises(self):
        with self.assertRaises(ValueError):
            mc.categorize_moment_contributor(None)


class AllocateDipoleBudgetTest(unittest.TestCase):
    def test_default_split_covers_the_whole_allowance(self):
        allocations = mc.allocate_dipole_budget(1.0)
        self.assertAlmostEqual(sum(allocations.values()), 1.0, places=9)

    def test_default_split_gives_the_steady_family_the_largest_share(self):
        allocations = mc.allocate_dipole_budget(1.0)
        self.assertGreater(allocations["steady"], allocations["transient"])
        self.assertGreater(allocations["transient"], allocations["long_term"])

    def test_allocation_scales_with_the_allowance(self):
        small = mc.allocate_dipole_budget(0.5)
        large = mc.allocate_dipole_budget(1.0)
        for category in mc.MOMENT_CATEGORIES:
            self.assertAlmostEqual(
                large[category], 2.0 * small[category], places=12
            )

    def test_representation_error_in_the_fraction_sum_is_absorbed(self):
        # 0.1 + 0.2 + 0.7 is a few units in the last place above one.
        allocations = mc.allocate_dipole_budget(
            2.0, {"steady": 0.1, "transient": 0.2, "long_term": 0.7}
        )
        self.assertAlmostEqual(allocations["long_term"], 1.4, places=12)

    def test_a_family_may_be_allocated_nothing(self):
        allocations = mc.allocate_dipole_budget(
            1.0, {"steady": 1.0, "transient": 0.0, "long_term": 0.0}
        )
        self.assertAlmostEqual(allocations["transient"], 0.0, places=12)

    def test_over_allocated_fractions_raise(self):
        with self.assertRaises(ValueError):
            mc.allocate_dipole_budget(
                1.0, {"steady": 0.6, "transient": 0.3, "long_term": 0.3}
            )

    def test_missing_family_raises(self):
        with self.assertRaises(ValueError):
            mc.allocate_dipole_budget(1.0, {"steady": 0.6, "transient": 0.4})

    def test_unknown_family_raises(self):
        with self.assertRaises(ValueError):
            mc.allocate_dipole_budget(
                1.0,
                {
                    "steady": 0.5,
                    "transient": 0.3,
                    "long_term": 0.1,
                    "seasonal": 0.1,
                },
            )

    def test_negative_fraction_raises(self):
        with self.assertRaises(ValueError):
            mc.allocate_dipole_budget(
                1.0, {"steady": 1.2, "transient": -0.2, "long_term": 0.0}
            )

    def test_non_positive_allowance_raises(self):
        with self.assertRaises(ValueError):
            mc.allocate_dipole_budget(0.0)


class EndOfLifeMomentTest(unittest.TestCase):
    def test_zero_drift_leaves_the_moment_unchanged(self):
        self.assertAlmostEqual(
            mc.end_of_life_moment_am2(0.05, 0.0, 7.0), 0.05, places=12
        )

    def test_positive_drift_compounds_over_the_mission(self):
        self.assertAlmostEqual(
            mc.end_of_life_moment_am2(0.01, 0.02, 5.0),
            0.01 * (1.02 ** 5),
            places=15,
        )

    def test_negative_drift_shrinks_the_moment(self):
        self.assertLess(mc.end_of_life_moment_am2(0.05, -0.1, 3.0), 0.05)

    def test_zero_mission_duration_is_the_delivered_value(self):
        self.assertAlmostEqual(
            mc.end_of_life_moment_am2(0.05, 0.2, 0.0), 0.05, places=12
        )

    def test_negative_initial_moment_raises(self):
        with self.assertRaises(ValueError):
            mc.end_of_life_moment_am2(-0.01, 0.02, 5.0)

    def test_drift_at_minus_one_raises(self):
        with self.assertRaises(ValueError):
            mc.end_of_life_moment_am2(0.01, -1.0, 5.0)

    def test_negative_mission_duration_raises(self):
        with self.assertRaises(ValueError):
            mc.end_of_life_moment_am2(0.01, 0.02, -1.0)


class MomentumAccumulationTest(unittest.TestCase):
    def test_momentum_is_torque_times_duration(self):
        self.assertAlmostEqual(
            mc.momentum_accumulation_nms(2.0e-6, 5000.0), 0.01, places=12
        )

    def test_zero_duration_accumulates_nothing(self):
        self.assertAlmostEqual(
            mc.momentum_accumulation_nms(2.0e-6, 0.0), 0.0, places=15
        )

    def test_negative_torque_raises(self):
        with self.assertRaises(ValueError):
            mc.momentum_accumulation_nms(-1.0e-6, 100.0)

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            mc.momentum_accumulation_nms(1.0e-6, -100.0)


class CategoryMomentSumsTest(unittest.TestCase):
    def test_families_are_summed_separately(self):
        sums = mc.category_moment_sums(
            _clean_spacecraft()["contributors"], 0.0
        )
        self.assertAlmostEqual(sums["steady"], 0.08, places=12)
        self.assertAlmostEqual(sums["transient"], 0.03, places=12)
        self.assertAlmostEqual(sums["long_term"], 0.01, places=12)

    def test_long_term_family_is_grown_to_end_of_life(self):
        sums = mc.category_moment_sums(
            _clean_spacecraft()["contributors"], 5.0
        )
        self.assertAlmostEqual(
            sums["long_term"], 0.01 * (1.02 ** 5), places=15
        )

    def test_steady_family_is_not_grown_by_the_mission_duration(self):
        sums = mc.category_moment_sums(
            _clean_spacecraft()["contributors"], 20.0
        )
        self.assertAlmostEqual(sums["steady"], 0.08, places=12)

    def test_empty_inventory_gives_zero_in_every_family(self):
        sums = mc.category_moment_sums([], 5.0)
        self.assertEqual(sorted(sums.keys()), ["long_term", "steady", "transient"])
        for value in sums.values():
            self.assertAlmostEqual(value, 0.0, places=15)

    def test_undeclared_drift_is_treated_as_no_growth(self):
        contributors = [
            {
                "contributor_id": "BAT-01",
                "kind": "battery_current_drift",
                "moment_am2": 0.02,
            }
        ]
        sums = mc.category_moment_sums(contributors, 10.0)
        self.assertAlmostEqual(sums["long_term"], 0.02, places=12)

    def test_missing_moment_raises(self):
        with self.assertRaises(ValueError):
            mc.category_moment_sums(
                [{"contributor_id": "X", "kind": "permanent_magnet"}], 1.0
            )

    def test_negative_moment_raises(self):
        with self.assertRaises(ValueError):
            mc.category_moment_sums(
                [
                    {
                        "contributor_id": "X",
                        "kind": "permanent_magnet",
                        "moment_am2": -0.1,
                    }
                ],
                1.0,
            )


class BudgetFindingsTest(unittest.TestCase):
    def test_family_inside_its_allocation_is_clean(self):
        sums = {"steady": 0.05, "transient": 0.01, "long_term": 0.0}
        allocations = {"steady": 0.1, "transient": 0.05, "long_term": 0.02}
        self.assertEqual(mc.budget_findings("SC", sums, allocations), [])

    def test_family_exactly_on_its_allocation_is_compliant(self):
        sums = {"steady": 0.1, "transient": 0.0, "long_term": 0.0}
        allocations = {"steady": 0.1, "transient": 0.05, "long_term": 0.02}
        self.assertEqual(mc.budget_findings("SC", sums, allocations), [])

    def test_representation_error_on_the_allocation_is_absorbed(self):
        sums = {"steady": 0.1 + 0.2, "transient": 0.0, "long_term": 0.0}
        allocations = {"steady": 0.3, "transient": 0.05, "long_term": 0.02}
        self.assertEqual(mc.budget_findings("SC", sums, allocations), [])

    def test_family_over_its_allocation_is_a_finding(self):
        sums = {"steady": 0.2, "transient": 0.0, "long_term": 0.0}
        allocations = {"steady": 0.1, "transient": 0.05, "long_term": 0.02}
        findings = mc.budget_findings("SC", sums, allocations)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["family"], "steady")
        self.assertEqual(
            findings[0]["issue"], "family_moment_exceeds_allocation"
        )

    def test_each_over_budget_family_yields_its_own_finding(self):
        sums = {"steady": 0.2, "transient": 0.2, "long_term": 0.2}
        allocations = {"steady": 0.1, "transient": 0.05, "long_term": 0.02}
        self.assertEqual(len(mc.budget_findings("SC", sums, allocations)), 3)

    def test_missing_family_in_the_sums_raises(self):
        with self.assertRaises(ValueError):
            mc.budget_findings(
                "SC",
                {"steady": 0.1},
                {"steady": 0.1, "transient": 0.05, "long_term": 0.02},
            )


class MomentumFindingsTest(unittest.TestCase):
    def test_momentum_inside_the_capacity_is_clean(self):
        self.assertEqual(
            mc.momentum_findings("SC", 0.1, 2.0e-5, 1.0, 5000.0, 0.05), []
        )

    def test_momentum_exactly_on_the_capacity_is_compliant(self):
        # 0.1 A.m2 in 2e-5 T over 5000 s accumulates exactly 0.01 N.m.s.
        self.assertEqual(
            mc.momentum_findings("SC", 0.1, 2.0e-5, 1.0, 5000.0, 0.01), []
        )

    def test_momentum_above_the_capacity_is_a_finding(self):
        findings = mc.momentum_findings(
            "SC", 0.5, 2.0e-5, 1.0, 5000.0, 0.01
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"],
            "orbit_momentum_exceeds_desaturation_capacity",
        )
        self.assertAlmostEqual(findings[0]["accumulated_nms"], 0.05, places=12)

    def test_missing_capacity_is_reported_not_assumed(self):
        findings = mc.momentum_findings("SC", 0.1, 2.0e-5, 1.0, 5000.0, None)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "desaturation_capacity_not_on_record"
        )

    def test_non_positive_capacity_raises(self):
        with self.assertRaises(ValueError):
            mc.momentum_findings("SC", 0.1, 2.0e-5, 1.0, 5000.0, 0.0)

    def test_negative_period_raises(self):
        with self.assertRaises(ValueError):
            mc.momentum_findings("SC", 0.1, 2.0e-5, 1.0, -1.0, 0.05)


class DriftRecordFindingsTest(unittest.TestCase):
    def test_declared_drift_leaves_no_finding(self):
        self.assertEqual(
            mc.drift_record_findings(
                "SC", _clean_spacecraft()["contributors"]
            ),
            [],
        )

    def test_undeclared_drift_on_a_long_term_contributor_is_a_finding(self):
        contributors = [
            {
                "contributor_id": "BAT-01",
                "kind": "battery_current_drift",
                "moment_am2": 0.02,
            }
        ]
        findings = mc.drift_record_findings("SC", contributors)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "long_term_drift_rate_not_on_record"
        )
        self.assertEqual(findings[0]["contributor"], "BAT-01")

    def test_steady_contributor_needs_no_drift_rate(self):
        contributors = [
            {
                "contributor_id": "MAG-01",
                "kind": "permanent_magnet",
                "moment_am2": 0.05,
            }
        ]
        self.assertEqual(mc.drift_record_findings("SC", contributors), [])

    def test_unknown_kind_raises_through_the_record_check(self):
        with self.assertRaises(ValueError):
            mc.drift_record_findings("SC", [{"kind": "aurora"}])


class CleanlinessReviewTest(unittest.TestCase):
    def test_clean_spacecraft_has_no_findings_anywhere(self):
        review = mc.cleanliness_review(_clean_spacecraft())
        self.assertEqual(review["budget"], [])
        self.assertEqual(review["momentum"], [])
        self.assertEqual(review["record"], [])
        self.assertTrue(mc.is_cleanliness_compliant(review))

    def test_review_returns_the_three_expected_finding_lists(self):
        review = mc.cleanliness_review(_clean_spacecraft())
        self.assertEqual(
            sorted(review.keys()), ["budget", "momentum", "record"]
        )

    def test_oversized_permanent_magnet_breaks_the_steady_family(self):
        spacecraft = _clean_spacecraft()
        spacecraft["contributors"][0]["moment_am2"] = 0.5
        review = mc.cleanliness_review(spacecraft)
        families = [f["family"] for f in review["budget"]]
        self.assertIn("steady", families)
        self.assertFalse(mc.is_cleanliness_compliant(review))

    def test_the_same_design_fails_in_a_lower_orbit(self):
        spacecraft = _clean_spacecraft()
        spacecraft["altitude_km"] = 300.0
        spacecraft["contributors"][0]["moment_am2"] = 0.13
        review = mc.cleanliness_review(spacecraft)
        self.assertTrue(review["budget"])

    def test_long_mission_drift_can_break_the_long_term_family(self):
        spacecraft = _clean_spacecraft()
        spacecraft["mission_years"] = 25.0
        spacecraft["contributors"][4]["drift_fraction_per_year"] = 0.08
        review = mc.cleanliness_review(spacecraft)
        families = [f["family"] for f in review["budget"]]
        self.assertIn("long_term", families)

    def test_undeclared_drift_rate_surfaces_in_the_record_list(self):
        spacecraft = _clean_spacecraft()
        del spacecraft["contributors"][4]["drift_fraction_per_year"]
        review = mc.cleanliness_review(spacecraft)
        self.assertEqual(len(review["record"]), 1)
        self.assertFalse(mc.is_cleanliness_compliant(review))

    def test_missing_desaturation_capacity_surfaces_in_the_momentum_list(self):
        spacecraft = _clean_spacecraft()
        del spacecraft["momentum_capacity_nms"]
        review = mc.cleanliness_review(spacecraft)
        self.assertEqual(
            review["momentum"][0]["issue"],
            "desaturation_capacity_not_on_record",
        )

    def test_tight_desaturation_capacity_is_a_momentum_finding(self):
        spacecraft = _clean_spacecraft()
        spacecraft["momentum_capacity_nms"] = 1.0e-4
        review = mc.cleanliness_review(spacecraft)
        self.assertEqual(
            review["momentum"][0]["issue"],
            "orbit_momentum_exceeds_desaturation_capacity",
        )

    def test_alignment_factor_defaults_to_the_worst_case(self):
        spacecraft = _clean_spacecraft()
        del spacecraft["alignment_factor"]
        worst_case = mc.cleanliness_review(spacecraft)
        spacecraft["alignment_factor"] = 1.0
        self.assertEqual(worst_case, mc.cleanliness_review(spacecraft))

    def test_review_does_not_mutate_the_input_spacecraft(self):
        spacecraft = _clean_spacecraft()
        snapshot = repr(spacecraft)
        mc.cleanliness_review(spacecraft)
        self.assertEqual(repr(spacecraft), snapshot)

    def test_unrecognized_contributor_kind_raises_through_the_review(self):
        spacecraft = _clean_spacecraft()
        spacecraft["contributors"][0]["kind"] = "moonlight"
        with self.assertRaises(ValueError):
            mc.cleanliness_review(spacecraft)

    def test_over_allocated_fractions_raise_through_the_review(self):
        spacecraft = _clean_spacecraft()
        spacecraft["allocation_fractions"] = {
            "steady": 0.9,
            "transient": 0.5,
            "long_term": 0.1,
        }
        with self.assertRaises(ValueError):
            mc.cleanliness_review(spacecraft)

    def test_compliance_helper_rejects_any_non_empty_list(self):
        self.assertFalse(
            mc.is_cleanliness_compliant(
                {"budget": [], "momentum": [], "record": [{"issue": "x"}]}
            )
        )

    def test_boundary_tolerance_is_small_and_positive(self):
        self.assertGreater(mc.BOUNDARY_REL_TOL, 0.0)
        self.assertLess(mc.BOUNDARY_REL_TOL, 1e-6)
        self.assertTrue(math.isfinite(mc.BOUNDARY_REL_TOL))


if __name__ == "__main__":
    unittest.main()
