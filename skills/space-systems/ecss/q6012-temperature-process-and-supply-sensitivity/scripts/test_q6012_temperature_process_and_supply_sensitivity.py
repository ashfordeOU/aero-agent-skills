#!/usr/bin/env python3
"""Contract test for the MMIC temperature/process/supply spread (offline)."""

import copy
import math
import unittest

from q6012_temperature_process_and_supply_sensitivity_logic import (
    AXES,
    HYBRID_METHOD,
    RSS_METHOD,
    WORST_CASE_METHOD,
    axis_basis_is_statistical,
    axis_contribution,
    combine_contributions,
    corner_matrix,
    evaluate_sensitivity,
    performance_window,
    process_excursions_sigma,
    rank_contributors,
    select_combination_method,
    supply_excursions_v,
    temperature_excursions_k,
)

# Small-signal gain of a driver stage, in decibel, with the three
# sensitivities a foundry design kit would report.
GAIN_CASE = {
    "nominal_value": 18.0,
    "sensitivities": {
        "temperature": -0.012,   # dB per kelvin
        "process": 0.9,          # dB per sigma of the foundry parameter
        "supply": 0.4,           # dB per volt of rail
    },
    "bases": {
        "temperature": "measured-over-temperature",
        "process": "multi-lot-statistics",
        "supply": "specified-tolerance",
    },
    "t_min_c": -40.0,
    "t_max_c": 85.0,
    "t_reference_c": 25.0,
    "v_min_v": 4.75,
    "v_max_v": 5.25,
    "v_nominal_v": 5.0,
    "process_sigma": 0.2,
    "coverage_sigma": 3.0,
    "spec_min": 15.0,
    "spec_max": 21.0,
}

WEAK_CASE = {
    "nominal_value": 18.0,
    "sensitivities": {"temperature": -0.05, "process": 1.4, "supply": 1.2},
    "bases": {
        "temperature": "room-temperature-only",
        "process": "foundry-nominal-only",
        "supply": "unbounded-rail",
    },
    "t_min_c": -55.0,
    "t_max_c": 125.0,
    "t_reference_c": 25.0,
    "v_min_v": 4.5,
    "v_max_v": 5.5,
    "v_nominal_v": 5.0,
    "process_sigma": 0.3,
    "spec_min": 15.0,
    "spec_max": 21.0,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class AxisBasisTests(unittest.TestCase):
    def test_temperature_is_never_statistical(self):
        for basis in ("measured-over-temperature", "model-extrapolated",
                      "room-temperature-only"):
            self.assertFalse(axis_basis_is_statistical("temperature", basis))

    def test_multi_lot_process_data_is_statistical(self):
        self.assertTrue(axis_basis_is_statistical("process", "multi-lot-statistics"))

    def test_single_lot_process_data_is_a_bound(self):
        self.assertFalse(axis_basis_is_statistical("process", "single-lot-statistics"))

    def test_specified_rail_tolerance_is_a_bound(self):
        self.assertFalse(axis_basis_is_statistical("supply", "specified-tolerance"))

    def test_measured_regulation_is_statistical(self):
        self.assertTrue(axis_basis_is_statistical("supply", "regulated-measured"))

    def test_unknown_axis_rejected(self):
        with self.assertRaises(ValueError):
            axis_basis_is_statistical("humidity", "specified-tolerance")

    def test_unknown_basis_rejected(self):
        with self.assertRaises(ValueError):
            axis_basis_is_statistical("process", "vendor-claim")


class ExcursionTests(unittest.TestCase):
    def test_temperature_excursions_straddle_the_reference(self):
        low, high = temperature_excursions_k(-40.0, 85.0, 25.0)
        self.assertAlmostEqual(low, -65.0, places=9)
        self.assertAlmostEqual(high, 60.0, places=9)

    def test_empty_temperature_envelope_rejected(self):
        with self.assertRaises(ValueError):
            temperature_excursions_k(85.0, 85.0, 85.0)

    def test_reference_outside_the_envelope_rejected(self):
        with self.assertRaises(ValueError):
            temperature_excursions_k(-40.0, 85.0, 125.0)

    def test_supply_excursions_straddle_the_nominal_rail(self):
        low, high = supply_excursions_v(4.75, 5.25, 5.0)
        self.assertAlmostEqual(low, -0.25, places=9)
        self.assertAlmostEqual(high, 0.25, places=9)

    def test_negative_rail_rejected(self):
        with self.assertRaises(ValueError):
            supply_excursions_v(-4.75, 5.25, 5.0)

    def test_nominal_rail_outside_the_band_rejected(self):
        with self.assertRaises(ValueError):
            supply_excursions_v(4.75, 5.25, 6.0)

    def test_process_excursions_are_symmetric_in_sigma(self):
        low, high = process_excursions_sigma(0.2, 3.0)
        self.assertAlmostEqual(low, -0.6, places=9)
        self.assertAlmostEqual(high, 0.6, places=9)

    def test_zero_process_sigma_gives_no_excursion(self):
        self.assertEqual(process_excursions_sigma(0.0), (0.0, 0.0))

    def test_negative_process_sigma_rejected(self):
        with self.assertRaises(ValueError):
            process_excursions_sigma(-0.2)

    def test_zero_coverage_sigma_rejected(self):
        with self.assertRaises(ValueError):
            process_excursions_sigma(0.2, 0.0)


class ContributionTests(unittest.TestCase):
    def test_positive_sensitivity_keeps_the_excursion_order(self):
        self.assertEqual(axis_contribution(0.4, (-0.25, 0.25)), (-0.1, 0.1))

    def test_negative_sensitivity_flips_the_excursion_order(self):
        low, high = axis_contribution(-0.012, (-65.0, 60.0))
        self.assertAlmostEqual(low, -0.72, places=9)
        self.assertAlmostEqual(high, 0.78, places=9)

    def test_zero_sensitivity_contributes_nothing(self):
        self.assertEqual(axis_contribution(0.0, (-65.0, 60.0)), (0.0, 0.0))

    def test_inverted_excursion_pair_rejected(self):
        with self.assertRaises(ValueError):
            axis_contribution(0.4, (0.25, -0.25))

    def test_non_numeric_sensitivity_rejected(self):
        with self.assertRaises(ValueError):
            axis_contribution("0.4 dB/V", (-0.25, 0.25))

    def test_malformed_excursion_rejected(self):
        with self.assertRaises(ValueError):
            axis_contribution(0.4, (-0.25,))


class CombinationMethodTests(unittest.TestCase):
    def test_all_bounds_give_the_worst_case_method(self):
        bases = {
            "temperature": "measured-over-temperature",
            "process": "single-lot-statistics",
            "supply": "specified-tolerance",
        }
        self.assertEqual(select_combination_method(bases), WORST_CASE_METHOD)

    def test_a_statistical_axis_gives_the_hybrid_method(self):
        self.assertEqual(select_combination_method(GAIN_CASE["bases"]), HYBRID_METHOD)

    def test_temperature_blocks_a_pure_root_sum_square(self):
        bases = {
            "temperature": "measured-over-temperature",
            "process": "multi-lot-statistics",
            "supply": "regulated-measured",
        }
        self.assertEqual(select_combination_method(bases), HYBRID_METHOD)

    def test_missing_axis_in_bases_rejected(self):
        bases = dict(GAIN_CASE["bases"])
        del bases["supply"]
        with self.assertRaises(ValueError):
            select_combination_method(bases)

    def test_non_mapping_bases_rejected(self):
        with self.assertRaises(ValueError):
            select_combination_method("all measured")


class CombineTests(unittest.TestCase):
    def _contributions(self):
        return {
            "temperature": {"pair": (-1.0, 1.0), "statistical": False},
            "process": {"pair": (-3.0, 3.0), "statistical": True},
            "supply": {"pair": (-4.0, 4.0), "statistical": True},
        }

    def test_worst_case_adds_every_contribution_arithmetically(self):
        low, high = combine_contributions(self._contributions(), WORST_CASE_METHOD)
        self.assertAlmostEqual(low, -8.0, places=9)
        self.assertAlmostEqual(high, 8.0, places=9)

    def test_hybrid_root_sum_squares_only_the_distributions(self):
        low, high = combine_contributions(self._contributions(), HYBRID_METHOD)
        # 1 deterministic + sqrt(9 + 16) = 1 + 5
        self.assertAlmostEqual(low, -6.0, places=9)
        self.assertAlmostEqual(high, 6.0, places=9)

    def test_hybrid_is_never_wider_than_the_worst_case(self):
        wc = combine_contributions(self._contributions(), WORST_CASE_METHOD)
        hy = combine_contributions(self._contributions(), HYBRID_METHOD)
        self.assertGreaterEqual(hy[0], wc[0])
        self.assertGreaterEqual(wc[1], hy[1])

    def test_root_sum_square_refused_while_a_bound_is_present(self):
        with self.assertRaises(ValueError):
            combine_contributions(self._contributions(), RSS_METHOD)

    def test_root_sum_square_allowed_when_every_axis_is_a_distribution(self):
        contributions = self._contributions()
        contributions["temperature"]["statistical"] = True
        low, high = combine_contributions(contributions, RSS_METHOD)
        self.assertAlmostEqual(high, math.sqrt(1.0 + 9.0 + 16.0), places=9)
        self.assertAlmostEqual(low, -math.sqrt(1.0 + 9.0 + 16.0), places=9)

    def test_missing_statistical_flag_rejected(self):
        contributions = self._contributions()
        del contributions["process"]["statistical"]
        with self.assertRaises(ValueError):
            combine_contributions(contributions, HYBRID_METHOD)

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            combine_contributions(self._contributions(), "eyeball")

    def test_empty_contributions_rejected(self):
        with self.assertRaises(ValueError):
            combine_contributions({}, WORST_CASE_METHOD)


class WindowAndRankingTests(unittest.TestCase):
    def test_window_offsets_the_nominal(self):
        self.assertEqual(performance_window(18.0, -2.0, 1.5), (16.0, 19.5))

    def test_inverted_spread_rejected(self):
        with self.assertRaises(ValueError):
            performance_window(18.0, 1.5, -2.0)

    def test_ranking_puts_the_widest_axis_first(self):
        ranked = rank_contributors(
            {
                "temperature": {"pair": (-1.0, 1.0)},
                "process": {"pair": (-3.0, 3.0)},
                "supply": {"pair": (-0.5, 0.5)},
            }
        )
        self.assertEqual(ranked[0]["axis"], "process")
        self.assertEqual(ranked[-1]["axis"], "supply")

    def test_ranking_shares_sum_to_one(self):
        ranked = rank_contributors(
            {
                "temperature": {"pair": (-1.0, 1.0)},
                "process": {"pair": (-3.0, 3.0)},
                "supply": {"pair": (-0.5, 0.5)},
            }
        )
        self.assertAlmostEqual(sum(r["share"] for r in ranked), 1.0, places=9)

    def test_ranking_of_a_flat_design_gives_zero_shares(self):
        ranked = rank_contributors({a: {"pair": (0.0, 0.0)} for a in AXES})
        self.assertTrue(all(r["share"] == 0.0 for r in ranked))

    def test_ranking_rejects_a_malformed_contribution(self):
        with self.assertRaises(ValueError):
            rank_contributors({"process": {"pair": 3.0}})


class CornerMatrixTests(unittest.TestCase):
    def test_monotone_response_uses_the_reduced_corner_set(self):
        corners = corner_matrix(True)
        self.assertEqual(len(corners), 9)
        self.assertIn(
            {"temperature": "cold", "process": "slow", "supply": "low"}, corners
        )

    def test_non_monotone_response_uses_the_full_grid(self):
        self.assertEqual(len(corner_matrix(False)), 27)

    def test_every_corner_names_all_three_axes(self):
        for corner in corner_matrix(False):
            self.assertEqual(set(corner), set(AXES))

    def test_non_boolean_monotone_flag_rejected(self):
        with self.assertRaises(ValueError):
            corner_matrix("yes")


class EvaluateTests(unittest.TestCase):
    def test_nominal_case_is_within_specification(self):
        result = evaluate_sensitivity(GAIN_CASE)
        self.assertEqual(result["verdict"], "spread-within-specification")
        self.assertTrue(result["compliant"])
        self.assertEqual(result["combination_method"], HYBRID_METHOD)

    def test_nominal_case_window_matches_the_hand_calculation(self):
        result = evaluate_sensitivity(GAIN_CASE)
        # temperature: -0.012 dB/K over -65..+60 K, carried deterministically
        # supply: 0.4 dB/V over +-0.25 V, a specified band, also deterministic
        # process: 0.9 dB/sigma over +-0.6 sigma, the only distribution
        self.assertAlmostEqual(result["contributions"]["temperature"][0], -0.72, places=9)
        self.assertAlmostEqual(result["contributions"]["temperature"][1], 0.78, places=9)
        self.assertAlmostEqual(result["contributions"]["process"][0], -0.54, places=9)
        self.assertAlmostEqual(result["contributions"]["supply"][0], -0.1, places=9)
        self.assertAlmostEqual(result["window_high"], 18.0 + 0.78 + 0.1 + 0.54, places=9)
        self.assertAlmostEqual(result["window_low"], 18.0 - 0.72 - 0.1 - 0.54, places=9)

    def test_temperature_is_the_dominant_axis_of_the_nominal_case(self):
        result = evaluate_sensitivity(GAIN_CASE)
        # 125 K of envelope at -0.012 dB/K is a 1.50 dB swing; the 3-sigma
        # process spread is 1.08 dB and the rail band only 0.20 dB.
        self.assertEqual(result["dominant_axis"], "temperature")
        self.assertAlmostEqual(result["ranked_contributors"][0]["swing"], 1.5, places=9)

    def test_a_steeper_process_slope_takes_over_as_dominant(self):
        case = _case(
            GAIN_CASE,
            sensitivities={"temperature": -0.012, "process": 3.0, "supply": 0.4},
        )
        self.assertEqual(evaluate_sensitivity(case)["dominant_axis"], "process")

    def test_weak_bases_raise_three_data_findings(self):
        result = evaluate_sensitivity(WEAK_CASE)
        self.assertTrue(any("foundry nominal" in f for f in result["findings"]))
        self.assertTrue(any("regulation band" in f for f in result["findings"]))
        self.assertTrue(any("room temperature" in f for f in result["findings"]))

    def test_weak_bases_force_the_worst_case_method(self):
        self.assertEqual(
            evaluate_sensitivity(WEAK_CASE)["combination_method"], WORST_CASE_METHOD
        )

    def test_weak_case_leaves_the_specification(self):
        result = evaluate_sensitivity(WEAK_CASE)
        self.assertEqual(result["verdict"], "spread-exceeds-specification")
        self.assertFalse(result["compliant"])

    def test_a_window_exactly_on_the_specification_edge_is_compliant(self):
        # sensitivities chosen so the high excursion lands on the spec edge
        case = _case(
            GAIN_CASE,
            bases={
                "temperature": "measured-over-temperature",
                "process": "single-lot-statistics",
                "supply": "specified-tolerance",
            },
            sensitivities={"temperature": 0.0, "process": 0.0, "supply": 4.0},
            spec_max=19.0,
            spec_min=17.0,
        )
        result = evaluate_sensitivity(case)
        self.assertAlmostEqual(result["window_high"], 19.0, places=9)
        self.assertAlmostEqual(result["high_margin"], 0.0, places=9)
        self.assertTrue(result["compliant"])

    def test_case_without_a_specification_is_not_graded(self):
        case = _case(GAIN_CASE)
        del case["spec_min"]
        del case["spec_max"]
        result = evaluate_sensitivity(case)
        self.assertEqual(result["verdict"], "spread-not-graded")
        self.assertIsNone(result["compliant"])
        self.assertTrue(any("not yet graded" in f for f in result["findings"]))

    def test_total_spread_matches_the_window_width(self):
        result = evaluate_sensitivity(GAIN_CASE)
        self.assertAlmostEqual(
            result["total_spread"], result["window_high"] - result["window_low"], places=9
        )

    def test_non_monotone_case_carries_the_full_corner_grid(self):
        result = evaluate_sensitivity(_case(GAIN_CASE, monotone_sensitivities=False))
        self.assertEqual(len(result["corner_matrix"]), 27)

    def test_case_missing_an_axis_sensitivity_rejected(self):
        case = _case(GAIN_CASE)
        del case["sensitivities"]["supply"]
        with self.assertRaises(ValueError):
            evaluate_sensitivity(case)

    def test_case_with_an_inverted_specification_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_sensitivity(_case(GAIN_CASE, spec_min=21.0, spec_max=15.0))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_sensitivity("18 dB over temperature")

    def test_case_without_a_nominal_value_rejected(self):
        case = _case(GAIN_CASE)
        del case["nominal_value"]
        with self.assertRaises(ValueError):
            evaluate_sensitivity(case)

    def test_wider_envelope_never_narrows_the_spread(self):
        narrow = evaluate_sensitivity(GAIN_CASE)["total_spread"]
        wide = evaluate_sensitivity(
            _case(GAIN_CASE, t_min_c=-55.0, t_max_c=125.0)
        )["total_spread"]
        self.assertGreater(wide, narrow)


if __name__ == "__main__":
    unittest.main()
