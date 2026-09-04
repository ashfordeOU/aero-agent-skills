"""Contract test for attribute_control_charts_logic (p, np, c, u charts).

Offline, deterministic, stdlib unittest. Run from the leaf scripts dir:

    python3 scripts/test_attribute_control_charts.py

Covers the wave-35 attribute-control-charts spec: worked-example
magnitude bounds for the p, np, c and u fixtures, flagged subgroup
indices, the np = n * p limit identity, the equal-area u reduction to
constant c-chart style limits, LCL floor at zero, all-conforming and
benign in-control fixtures, below-LCL flagging when LCL is positive,
ValueError rejection of non-physical inputs, dict key contract,
verdict helper, and determinism.
"""

import unittest

from attribute_control_charts_logic import (
    SIGMA_FACTOR,
    attribute_verdict,
    c_chart,
    np_chart,
    p_chart,
    u_chart,
)

# p/np fixture: 20 subgroups of n = 200, total nonconforming 90,
# subgroup index 12 carrying 14.
P_COUNTS = [4] * 20
P_COUNTS[12] = 14
P_N = 200

# c fixture: 25 units, total defects 83, unit index 12 carrying 11.
C_COUNTS = [3] * 25
C_COUNTS[12] = 11

# u fixture: 9 subgroups, counts over variable areas.
U_COUNTS = [2, 5, 3, 4, 1, 6, 2, 3, 9]
U_AREAS = [1.0, 1.5, 1.0, 2.0, 1.0, 1.5, 1.0, 1.0, 1.0]


class TestPChart(unittest.TestCase):
    def test_p_worked_example_center_and_sigma(self):
        result = p_chart(P_COUNTS, P_N)
        self.assertAlmostEqual(result["pbar"], 0.0225, delta=1e-9)
        self.assertAlmostEqual(result["sigma_p"], 0.01049, delta=1e-4)

    def test_p_worked_example_limits(self):
        result = p_chart(P_COUNTS, P_N)
        self.assertAlmostEqual(result["UCL"], 0.0540, delta=1e-4)
        self.assertEqual(result["LCL"], 0.0)

    def test_p_worked_example_flag_and_verdict(self):
        result = p_chart(P_COUNTS, P_N)
        self.assertEqual(result["flagged_subgroups"], [12])
        self.assertEqual(result["verdict"], "out-of-control")

    def test_p_all_conforming_in_control(self):
        result = p_chart([0] * 20, 200)
        self.assertEqual(result["pbar"], 0.0)
        self.assertEqual(result["sigma_p"], 0.0)
        self.assertEqual(result["UCL"], 0.0)
        self.assertEqual(result["LCL"], 0.0)
        self.assertEqual(result["flagged_subgroups"], [])
        self.assertEqual(result["verdict"], "in-control")

    def test_p_lcl_floor_exact_zero_small_pbar(self):
        result = p_chart([0] * 24 + [1], 100)
        self.assertEqual(result["LCL"], 0.0)

    def test_p_flags_below_positive_lcl(self):
        result = p_chart([10, 10, 10, 10, 6], 10)
        self.assertGreater(result["LCL"], 0.0)
        self.assertEqual(result["flagged_subgroups"], [4])
        self.assertEqual(result["verdict"], "out-of-control")

    def test_p_empty_counts_raises(self):
        with self.assertRaises(ValueError):
            p_chart([], 200)

    def test_p_nonpositive_sample_size_raises(self):
        with self.assertRaises(ValueError):
            p_chart([1, 2], 0)
        with self.assertRaises(ValueError):
            p_chart([1, 2], -10)

    def test_p_negative_count_raises(self):
        with self.assertRaises(ValueError):
            p_chart([2, -1, 3], 200)

    def test_p_count_above_sample_size_raises(self):
        with self.assertRaises(ValueError):
            p_chart([2, 201, 3], 200)


class TestNpChart(unittest.TestCase):
    def test_np_worked_example_center_and_limits(self):
        result = np_chart(P_COUNTS, P_N)
        self.assertEqual(result["npbar"], 4.5)
        self.assertAlmostEqual(result["UCL"], 10.79, delta=1e-2)
        self.assertEqual(result["LCL"], 0.0)

    def test_np_limits_equal_n_times_p_limits(self):
        p_result = p_chart(P_COUNTS, P_N)
        np_result = np_chart(P_COUNTS, P_N)
        self.assertEqual(np_result["UCL"], P_N * p_result["UCL"])
        self.assertEqual(np_result["LCL"], P_N * p_result["LCL"])
        # Also exact when the p-chart LCL is positive (no floor).
        counts = [10, 10, 10, 10, 6]
        self.assertGreater(p_chart(counts, 10)["LCL"], 0.0)
        self.assertEqual(np_chart(counts, 10)["UCL"],
                         10 * p_chart(counts, 10)["UCL"])
        self.assertEqual(np_chart(counts, 10)["LCL"],
                         10 * p_chart(counts, 10)["LCL"])

    def test_np_flagging_matches_p_fraction_flagging(self):
        np_result = np_chart(P_COUNTS, P_N)
        self.assertEqual(np_result["flagged_subgroups"],
                         p_chart(P_COUNTS, P_N)["flagged_subgroups"])
        self.assertEqual(np_result["flagged_subgroups"], [12])
        self.assertEqual(np_result["verdict"], "out-of-control")

    def test_np_all_conforming_in_control(self):
        result = np_chart([0] * 20, 200)
        self.assertEqual(result["npbar"], 0.0)
        self.assertEqual(result["UCL"], 0.0)
        self.assertEqual(result["LCL"], 0.0)
        self.assertEqual(result["verdict"], "in-control")

    def test_np_validation_raises(self):
        with self.assertRaises(ValueError):
            np_chart([], 200)
        with self.assertRaises(ValueError):
            np_chart([1, 2], 0)
        with self.assertRaises(ValueError):
            np_chart([1, -2], 200)
        with self.assertRaises(ValueError):
            np_chart([1, 2, 250], 200)


class TestCChart(unittest.TestCase):
    def test_c_worked_example_center(self):
        result = c_chart(C_COUNTS)
        self.assertAlmostEqual(result["cbar"], 3.32, delta=1e-12)

    def test_c_worked_example_limits_flag_verdict(self):
        result = c_chart(C_COUNTS)
        self.assertAlmostEqual(result["UCL"], 8.786, delta=1e-3)
        self.assertEqual(result["LCL"], 0.0)
        self.assertEqual(result["flagged_subgroups"], [12])
        self.assertEqual(result["verdict"], "out-of-control")

    def test_c_zero_fixture_in_control(self):
        result = c_chart([0] * 25)
        self.assertEqual(result["cbar"], 0.0)
        self.assertEqual(result["sigma_c"], 0.0)
        self.assertEqual(result["UCL"], 0.0)
        self.assertEqual(result["LCL"], 0.0)
        self.assertEqual(result["flagged_subgroups"], [])
        self.assertEqual(result["verdict"], "in-control")

    def test_c_single_defect_flags_when_ucl_below_one(self):
        result = c_chart([0] * 24 + [1])
        self.assertAlmostEqual(result["cbar"], 0.04, delta=1e-12)
        self.assertAlmostEqual(result["UCL"], 0.64, delta=1e-9)
        self.assertLess(result["UCL"], 1.0)
        self.assertEqual(result["flagged_subgroups"], [24])
        self.assertEqual(result["verdict"], "out-of-control")

    def test_c_validation_raises(self):
        with self.assertRaises(ValueError):
            c_chart([])
        with self.assertRaises(ValueError):
            c_chart([3, -1, 2])


class TestUChart(unittest.TestCase):
    def test_u_worked_example_ubar(self):
        result = u_chart(U_COUNTS, U_AREAS)
        self.assertAlmostEqual(result["ubar"], 3.1818, delta=1e-4)

    def test_u_worked_example_variable_limits(self):
        result = u_chart(U_COUNTS, U_AREAS)
        self.assertAlmostEqual(result["UCLs"][5], 7.5511, delta=1e-4)
        self.assertAlmostEqual(result["UCLs"][8], 8.5331, delta=1e-4)
        self.assertEqual(set(result["LCLs"]), {0.0})

    def test_u_worked_example_only_flag_is_index_8(self):
        result = u_chart(U_COUNTS, U_AREAS)
        self.assertEqual(result["flagged_subgroups"], [8])
        self.assertEqual(result["verdict"], "out-of-control")

    def test_u_benign_variable_area_in_control(self):
        result = u_chart([1, 2, 1], [2.0, 3.0, 2.0])
        self.assertEqual(result["flagged_subgroups"], [])
        self.assertEqual(result["verdict"], "in-control")

    def test_u_equal_areas_reduce_to_constant_c_style_limits(self):
        result = u_chart(C_COUNTS, [1.0] * 25)
        c_result = c_chart(C_COUNTS)
        self.assertEqual(len(set(result["UCLs"])), 1)
        self.assertEqual(len(set(result["LCLs"])), 1)
        self.assertAlmostEqual(result["ubar"], c_result["cbar"], delta=1e-12)
        self.assertEqual(result["UCLs"][0], c_result["UCL"])
        self.assertEqual(result["LCLs"][0], c_result["LCL"])

    def test_u_invalid_shapes_raise(self):
        with self.assertRaises(ValueError):
            u_chart([], [1.0])
        with self.assertRaises(ValueError):
            u_chart([1, 2, 3], [1.0, 1.0])

    def test_u_invalid_values_raise(self):
        with self.assertRaises(ValueError):
            u_chart([1, -2, 3], [1.0, 1.0, 1.0])
        with self.assertRaises(ValueError):
            u_chart([1, 2], [1.0, 0.0])
        with self.assertRaises(ValueError):
            u_chart([1, 2], [1.0, -1.0])


class TestSharedContract(unittest.TestCase):
    def test_attribute_verdict_helper(self):
        self.assertEqual(attribute_verdict(False), "in-control")
        self.assertEqual(attribute_verdict([]), "in-control")
        self.assertEqual(attribute_verdict(True), "out-of-control")
        self.assertEqual(attribute_verdict([3]), "out-of-control")

    def test_sigma_factor_is_three(self):
        self.assertEqual(SIGMA_FACTOR, 3.0)

    def test_dict_keys_exact_contract(self):
        self.assertEqual(
            set(p_chart(P_COUNTS, P_N).keys()),
            {"pbar", "sigma_p", "UCL", "LCL", "flagged_subgroups",
             "verdict"})
        self.assertEqual(
            set(np_chart(P_COUNTS, P_N).keys()),
            {"npbar", "UCL", "LCL", "flagged_subgroups", "verdict"})
        self.assertEqual(
            set(c_chart(C_COUNTS).keys()),
            {"cbar", "sigma_c", "UCL", "LCL", "flagged_subgroups",
             "verdict"})
        self.assertEqual(
            set(u_chart(U_COUNTS, U_AREAS).keys()),
            {"ubar", "UCLs", "LCLs", "flagged_subgroups", "verdict"})

    def test_determinism_identical_outputs(self):
        self.assertEqual(p_chart(P_COUNTS, P_N), p_chart(P_COUNTS, P_N))
        self.assertEqual(np_chart(P_COUNTS, P_N), np_chart(P_COUNTS, P_N))
        self.assertEqual(c_chart(C_COUNTS), c_chart(C_COUNTS))
        self.assertEqual(u_chart(U_COUNTS, U_AREAS),
                         u_chart(U_COUNTS, U_AREAS))


if __name__ == "__main__":
    unittest.main()
