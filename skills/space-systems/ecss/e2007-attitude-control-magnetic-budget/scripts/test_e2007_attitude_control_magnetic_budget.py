#!/usr/bin/env python3
"""Gate 3 contract test for e2007-attitude-control-magnetic-budget.

Stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_attitude_control_magnetic_budget.py
"""

import math
import unittest

from e2007_attitude_control_magnetic_budget_logic import (
    AXES,
    CONTRIBUTOR_CATEGORIES,
    DEFAULT_COVERAGE_FACTOR,
    assess_magnetic_budget,
    categorize_contributor,
    check_axis_budget,
    magnetic_disturbance_torque,
    roll_up_dipole_budget,
    torque_margin,
    validate_dipole_vector,
    vector_magnitude,
)

# A representative low-Earth-orbit field vector, in tesla.
FIELD_T = (3.0e-5, 0.0, 0.0)


def contributor(**over):
    base = {
        "id": "pcdu",
        "kind": "harness-loop",
        "vector_am2": (0.05, 0.02, -0.01),
        "uncertainty_am2": (0.005, 0.005, 0.005),
    }
    base.update(over)
    return base


def fleet():
    return [
        contributor(),
        contributor(id="reaction-wheel", kind="hard-magnetic-material",
                    vector_am2=(0.03, -0.01, 0.02),
                    uncertainty_am2=(0.004, 0.004, 0.004)),
        contributor(id="trim", kind="compensation-magnet",
                    vector_am2=(-0.06, 0.0, 0.0),
                    uncertainty_am2=(0.002, 0.0, 0.0)),
    ]


class TestValidateVector(unittest.TestCase):
    def test_three_components_pass_through(self):
        self.assertEqual(validate_dipole_vector([1, 2, 3]), (1.0, 2.0, 3.0))

    def test_tuple_and_list_agree(self):
        self.assertEqual(validate_dipole_vector((1, 2, 3)), validate_dipole_vector([1, 2, 3]))

    def test_two_components_rejected(self):
        with self.assertRaises(ValueError):
            validate_dipole_vector([1.0, 2.0])

    def test_four_components_rejected(self):
        with self.assertRaises(ValueError):
            validate_dipole_vector([1.0, 2.0, 3.0, 4.0])

    def test_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_dipole_vector("123")

    def test_non_numeric_component_rejected(self):
        with self.assertRaises(ValueError):
            validate_dipole_vector([1.0, "2", 3.0])

    def test_non_finite_component_rejected(self):
        with self.assertRaises(ValueError):
            validate_dipole_vector([1.0, float("nan"), 3.0])

    def test_negative_rejected_when_non_negative_requested(self):
        with self.assertRaises(ValueError):
            validate_dipole_vector([1.0, -2.0, 3.0], non_negative=True)

    def test_magnitude_of_three_four_zero(self):
        self.assertAlmostEqual(vector_magnitude((3.0, 4.0, 0.0)), 5.0, places=12)

    def test_magnitude_of_zero_vector(self):
        self.assertAlmostEqual(vector_magnitude((0.0, 0.0, 0.0)), 0.0, places=12)


class TestCategorizeContributor(unittest.TestCase):
    def test_permanent_category(self):
        self.assertEqual(
            categorize_contributor("hard-magnetic-material"), "permanent-magnetization"
        )

    def test_induced_category(self):
        self.assertEqual(
            categorize_contributor("soft-magnetic-material"), "induced-magnetization"
        )

    def test_current_loop_category(self):
        self.assertEqual(categorize_contributor("solar-array-loop"), "current-loop-moment")

    def test_compensation_category(self):
        self.assertEqual(categorize_contributor("trim-magnet"), "compensation-moment")

    def test_case_and_whitespace_normalised(self):
        self.assertEqual(
            categorize_contributor(" Compensation-Loop "), "compensation-moment"
        )

    def test_every_known_kind_resolves(self):
        for kind in CONTRIBUTOR_CATEGORIES:
            self.assertIn(
                categorize_contributor(kind),
                {
                    "permanent-magnetization",
                    "induced-magnetization",
                    "current-loop-moment",
                    "compensation-moment",
                },
            )

    def test_uncategorized_kind_rejected(self):
        with self.assertRaises(ValueError):
            categorize_contributor("plasma-thruster-moment")

    def test_empty_kind_rejected(self):
        with self.assertRaises(ValueError):
            categorize_contributor("  ")

    def test_non_string_kind_rejected(self):
        with self.assertRaises(ValueError):
            categorize_contributor(None)


class TestRollUp(unittest.TestCase):
    def test_signed_sum_lets_compensation_cancel(self):
        out = roll_up_dipole_budget(fleet())
        self.assertAlmostEqual(out["nominal_vector_am2"][0], 0.02, places=12)
        self.assertAlmostEqual(out["nominal_vector_am2"][1], 0.01, places=12)
        self.assertAlmostEqual(out["nominal_vector_am2"][2], 0.01, places=12)

    def test_uncertainties_combine_by_root_sum_square(self):
        out = roll_up_dipole_budget(fleet())
        expected = math.sqrt(0.005 ** 2 + 0.004 ** 2 + 0.002 ** 2)
        self.assertAlmostEqual(out["uncertainty_vector_am2"][0], expected, places=12)

    def test_uncertainties_never_cancel(self):
        pair = [
            contributor(id="a", vector_am2=(0.1, 0.0, 0.0), uncertainty_am2=(0.01, 0.0, 0.0)),
            contributor(id="b", vector_am2=(-0.1, 0.0, 0.0), uncertainty_am2=(0.01, 0.0, 0.0)),
        ]
        out = roll_up_dipole_budget(pair)
        self.assertAlmostEqual(out["nominal_vector_am2"][0], 0.0, places=12)
        self.assertGreater(out["uncertainty_vector_am2"][0], 0.0)

    def test_worst_case_adds_coverage_times_uncertainty(self):
        out = roll_up_dipole_budget(fleet(), coverage_factor=3.0)
        expected = abs(out["nominal_vector_am2"][0]) + 3.0 * out["uncertainty_vector_am2"][0]
        self.assertAlmostEqual(out["worst_case_vector_am2"][0], expected, places=12)

    def test_zero_coverage_factor_gives_nominal_magnitudes(self):
        out = roll_up_dipole_budget(fleet(), coverage_factor=0.0)
        for i in range(3):
            self.assertAlmostEqual(
                out["worst_case_vector_am2"][i], abs(out["nominal_vector_am2"][i]), places=12
            )

    def test_default_coverage_factor_is_applied(self):
        out = roll_up_dipole_budget(fleet())
        self.assertAlmostEqual(out["coverage_factor"], DEFAULT_COVERAGE_FACTOR, places=12)

    def test_category_subtotals_are_traceable(self):
        out = roll_up_dipole_budget(fleet())
        self.assertAlmostEqual(out["by_category_am2"]["compensation-moment"][0], -0.06, places=12)
        self.assertAlmostEqual(out["by_category_am2"]["current-loop-moment"][0], 0.05, places=12)
        self.assertIn("permanent-magnetization", out["by_category_am2"])

    def test_contributor_count_reported(self):
        self.assertEqual(roll_up_dipole_budget(fleet())["contributor_count"], 3)

    def test_missing_uncertainty_defaults_to_zero(self):
        entry = {"id": "bare", "kind": "current-loop", "vector_am2": (0.1, 0.0, 0.0)}
        out = roll_up_dipole_budget([entry])
        self.assertAlmostEqual(out["uncertainty_vector_am2"][0], 0.0, places=12)

    def test_empty_contributor_list_rejected(self):
        with self.assertRaises(ValueError):
            roll_up_dipole_budget([])

    def test_duplicate_contributor_id_rejected(self):
        with self.assertRaises(ValueError):
            roll_up_dipole_budget([contributor(), contributor()])

    def test_blank_contributor_id_rejected(self):
        with self.assertRaises(ValueError):
            roll_up_dipole_budget([contributor(id="  ")])

    def test_negative_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            roll_up_dipole_budget([contributor(uncertainty_am2=(-0.01, 0.0, 0.0))])

    def test_negative_coverage_factor_rejected(self):
        with self.assertRaises(ValueError):
            roll_up_dipole_budget(fleet(), coverage_factor=-1.0)

    def test_missing_contributor_key_rejected(self):
        broken = contributor()
        del broken["vector_am2"]
        with self.assertRaises(ValueError):
            roll_up_dipole_budget([broken])

    def test_non_iterable_contributors_rejected(self):
        with self.assertRaises(ValueError):
            roll_up_dipole_budget(contributor())


class TestAxisBudget(unittest.TestCase):
    def test_comfortable_budget_is_within_limit(self):
        out = check_axis_budget((0.02, 0.01, 0.01), (0.1, 0.1, 0.1), 0.2)
        self.assertTrue(out["within_limit"])

    def test_exactly_on_limit_axis_is_within_limit(self):
        # 0.1 + 0.2 lands a few ULPs above 0.3 in binary floating point; the
        # axis is physically on its allocation and must read as compliant.
        rolled = roll_up_dipole_budget(
            [
                contributor(id="a", vector_am2=(0.1, 0.0, 0.0), uncertainty_am2=(0.0, 0.0, 0.0)),
                contributor(id="b", vector_am2=(0.2, 0.0, 0.0), uncertainty_am2=(0.0, 0.0, 0.0)),
            ]
        )
        worst_x = rolled["worst_case_vector_am2"][0]
        self.assertGreater(worst_x, 0.3)
        out = check_axis_budget(rolled["worst_case_vector_am2"], (0.3, 0.1, 0.1), 0.5)
        self.assertTrue(out["axes"]["x"]["within_limit"])
        self.assertTrue(out["within_limit"])

    def test_axis_breach_is_detected(self):
        out = check_axis_budget((0.5, 0.01, 0.01), (0.1, 0.1, 0.1), 1.0)
        self.assertFalse(out["axes"]["x"]["within_limit"])
        self.assertFalse(out["within_limit"])

    def test_axes_can_pass_while_magnitude_fails(self):
        out = check_axis_budget((0.1, 0.1, 0.1), (0.1, 0.1, 0.1), 0.15)
        self.assertTrue(all(out["axes"][a]["within_limit"] for a in AXES))
        self.assertFalse(out["magnitude_within_limit"])
        self.assertFalse(out["within_limit"])

    def test_magnitude_matches_euclidean_norm(self):
        out = check_axis_budget((0.03, 0.04, 0.0), (0.1, 0.1, 0.1), 0.1)
        self.assertAlmostEqual(out["magnitude_am2"], 0.05, places=12)

    def test_driving_axis_is_the_tightest(self):
        out = check_axis_budget((0.09, 0.01, 0.01), (0.1, 0.1, 0.1), 0.5)
        self.assertEqual(out["driving_axis"], "x")

    def test_remaining_allocation_reported(self):
        out = check_axis_budget((0.04, 0.01, 0.01), (0.1, 0.1, 0.1), 0.5)
        self.assertAlmostEqual(out["axes"]["x"]["remaining_am2"], 0.06, places=12)

    def test_negative_worst_case_rejected(self):
        with self.assertRaises(ValueError):
            check_axis_budget((-0.01, 0.01, 0.01), (0.1, 0.1, 0.1), 0.5)

    def test_zero_axis_allocation_rejected(self):
        with self.assertRaises(ValueError):
            check_axis_budget((0.01, 0.01, 0.01), (0.0, 0.1, 0.1), 0.5)

    def test_zero_magnitude_allocation_rejected(self):
        with self.assertRaises(ValueError):
            check_axis_budget((0.01, 0.01, 0.01), (0.1, 0.1, 0.1), 0.0)


class TestDisturbanceTorque(unittest.TestCase):
    def test_cross_product_components(self):
        out = magnetic_disturbance_torque((0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
        self.assertAlmostEqual(out["torque_vector_nm"][0], 1.0, places=12)
        self.assertAlmostEqual(out["torque_vector_nm"][1], 0.0, places=12)
        self.assertAlmostEqual(out["torque_vector_nm"][2], 0.0, places=12)

    def test_aligned_dipole_gives_no_torque(self):
        out = magnetic_disturbance_torque((0.1, 0.0, 0.0), (3.0e-5, 0.0, 0.0))
        self.assertAlmostEqual(out["torque_magnitude_nm"], 0.0, places=15)

    def test_perpendicular_dipole_gives_full_torque(self):
        out = magnetic_disturbance_torque((0.0, 0.1, 0.0), (3.0e-5, 0.0, 0.0))
        self.assertAlmostEqual(out["torque_magnitude_nm"], 3.0e-6, places=15)

    def test_torque_is_antisymmetric(self):
        forward = magnetic_disturbance_torque((0.1, 0.2, 0.3), FIELD_T)["torque_vector_nm"]
        reverse = magnetic_disturbance_torque(FIELD_T, (0.1, 0.2, 0.3))["torque_vector_nm"]
        for i in range(3):
            self.assertAlmostEqual(forward[i], -reverse[i], places=15)

    def test_bad_field_vector_rejected(self):
        with self.assertRaises(ValueError):
            magnetic_disturbance_torque((0.1, 0.0, 0.0), (3.0e-5, 0.0))


class TestTorqueMargin(unittest.TestCase):
    def test_margin_is_the_ratio(self):
        self.assertAlmostEqual(torque_margin(1.0e-5, 2.0e-6), 5.0, places=9)

    def test_zero_disturbance_gives_infinite_margin(self):
        self.assertEqual(torque_margin(1.0e-5, 0.0), float("inf"))

    def test_zero_authority_rejected(self):
        with self.assertRaises(ValueError):
            torque_margin(0.0, 2.0e-6)

    def test_negative_disturbance_rejected(self):
        with self.assertRaises(ValueError):
            torque_margin(1.0e-5, -2.0e-6)


class TestAssessBudget(unittest.TestCase):
    def kwargs(self, **over):
        base = {
            "contributors": fleet(),
            "axis_allocations_am2": (0.1, 0.1, 0.1),
            "magnitude_allocation_am2": 0.15,
            "field_vector_t": FIELD_T,
            "control_authority_nm": 1.0e-4,
        }
        base.update(over)
        return base

    def test_healthy_budget_is_compliant(self):
        out = assess_magnetic_budget(**self.kwargs())
        self.assertTrue(out["compliant"])
        self.assertEqual(out["findings"], ())

    def test_axis_breach_produces_a_finding(self):
        out = assess_magnetic_budget(**self.kwargs(axis_allocations_am2=(0.005, 0.1, 0.1)))
        self.assertFalse(out["compliant"])
        self.assertTrue(any("x-axis" in f for f in out["findings"]))

    def test_magnitude_breach_produces_a_finding(self):
        out = assess_magnetic_budget(**self.kwargs(magnitude_allocation_am2=0.001))
        self.assertFalse(out["compliant"])
        self.assertTrue(any("magnitude allocation" in f for f in out["findings"]))

    def test_torque_breach_produces_a_finding(self):
        out = assess_magnetic_budget(**self.kwargs(control_authority_nm=1.0e-9))
        self.assertFalse(out["compliant"])
        self.assertTrue(any("magnetic-disturbance-torque" in f for f in out["findings"]))
        self.assertFalse(out["torque_within_authority"])

    def test_aligned_field_leaves_infinite_torque_margin(self):
        out = assess_magnetic_budget(
            **self.kwargs(
                contributors=[
                    contributor(id="only", vector_am2=(0.02, 0.0, 0.0),
                                uncertainty_am2=(0.0, 0.0, 0.0))
                ]
            )
        )
        self.assertEqual(out["torque_margin"], float("inf"))
        self.assertTrue(out["torque_within_authority"])

    def test_driving_axis_is_reported(self):
        out = assess_magnetic_budget(**self.kwargs(axis_allocations_am2=(0.03, 0.2, 0.2)))
        self.assertEqual(out["driving_axis"], "x")

    def test_coverage_factor_tightens_the_budget(self):
        loose = assess_magnetic_budget(**self.kwargs(coverage_factor=0.0))
        tight = assess_magnetic_budget(**self.kwargs(coverage_factor=3.0))
        self.assertGreater(
            tight["rollup"]["worst_case_magnitude_am2"],
            loose["rollup"]["worst_case_magnitude_am2"],
        )

    def test_required_torque_margin_below_parity_rejected(self):
        with self.assertRaises(ValueError):
            assess_magnetic_budget(**self.kwargs(required_torque_margin=0.5))

    def test_bad_field_vector_rejected(self):
        with self.assertRaises(ValueError):
            assess_magnetic_budget(**self.kwargs(field_vector_t=(3.0e-5, 0.0)))

    def test_repeat_assessment_is_deterministic(self):
        first = assess_magnetic_budget(**self.kwargs())
        second = assess_magnetic_budget(**self.kwargs())
        self.assertEqual(first["findings"], second["findings"])
        self.assertAlmostEqual(first["torque_margin"], second["torque_margin"], places=12)


if __name__ == "__main__":
    unittest.main()
