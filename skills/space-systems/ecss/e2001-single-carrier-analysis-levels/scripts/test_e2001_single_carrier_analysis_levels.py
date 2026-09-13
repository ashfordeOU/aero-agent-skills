#!/usr/bin/env python3
"""Gate 3 contract test -- single-carrier design-analysis-level selection.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2001_single_carrier_analysis_levels.py
"""

import unittest

from e2001_single_carrier_analysis_levels_logic import (
    LEVEL_ONE,
    LEVEL_TWO,
    LEVEL_TWO_PREREQUISITES,
    QUASI_STATIC_GAP_TO_WAVELENGTH_LIMIT,
    SPEED_OF_LIGHT_M_S,
    assess_analysis_level_selection,
    chart_band_for_material,
    frequency_gap_product_ghz_mm,
    gap_to_wavelength_ratio,
    gap_uniformity_ratio,
    is_quasi_static,
    is_within_chart_band,
    level_one_eligibility,
    missing_level_two_prerequisites,
    normalize_geometry_family,
    select_design_analysis_level,
    summarize_level_selection,
)


def baseline_case(**overrides):
    """A gap that clears every level-one applicability gate."""
    case = {
        "identifier": "output-iris",
        "geometry_family": "parallel-plate",
        "frequency_hz": 1.0e10,
        "gap_m": 5.0e-4,
        "electrode_material": "silver",
    }
    case.update(overrides)
    return case


class TestGeometryFamily(unittest.TestCase):
    def test_parallel_plate_is_chart_representable(self):
        rec = normalize_geometry_family("parallel-plate")
        self.assertTrue(rec["chart_representable"])
        self.assertEqual(rec["reduction"], "direct")

    def test_waveguide_iris_reduces_to_equivalent_gap(self):
        rec = normalize_geometry_family(" Waveguide-Iris ")
        self.assertTrue(rec["chart_representable"])
        self.assertEqual(rec["family"], "waveguide-iris")

    def test_microstrip_gap_is_not_chart_representable(self):
        self.assertFalse(normalize_geometry_family("microstrip-gap")["chart_representable"])

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            normalize_geometry_family("helical-slow-wave-line")

    def test_non_string_family_rejected(self):
        with self.assertRaises(ValueError):
            normalize_geometry_family(None)


class TestFrequencyGapProduct(unittest.TestCase):
    def test_product_in_gigahertz_millimetre(self):
        self.assertAlmostEqual(
            frequency_gap_product_ghz_mm(1.0e10, 5.0e-4), 5.0, places=12
        )

    def test_product_scales_with_separation(self):
        small = frequency_gap_product_ghz_mm(1.0e10, 5.0e-4)
        large = frequency_gap_product_ghz_mm(1.0e10, 1.0e-3)
        self.assertAlmostEqual(large / small, 2.0, places=12)

    def test_non_positive_gap_rejected(self):
        with self.assertRaises(ValueError):
            frequency_gap_product_ghz_mm(1.0e10, 0.0)

    def test_non_positive_frequency_rejected(self):
        with self.assertRaises(ValueError):
            frequency_gap_product_ghz_mm(-1.0e10, 5.0e-4)


class TestChartBands(unittest.TestCase):
    def test_silver_band_on_record(self):
        low, high = chart_band_for_material("silver")
        self.assertAlmostEqual(low, 0.1)
        self.assertAlmostEqual(high, 100.0)

    def test_lookup_is_case_and_whitespace_insensitive(self):
        self.assertEqual(chart_band_for_material("  Titanium "), (0.5, 20.0))

    def test_uncharted_surface_rejected(self):
        with self.assertRaises(ValueError):
            chart_band_for_material("carbon-fibre-skin")

    def test_inverted_custom_band_rejected(self):
        with self.assertRaises(ValueError):
            chart_band_for_material("silver", {"silver": (10.0, 2.0)})

    def test_product_inside_band(self):
        self.assertTrue(is_within_chart_band(5.0, (0.1, 100.0)))

    def test_product_below_band_is_outside(self):
        self.assertFalse(is_within_chart_band(0.05, (0.1, 100.0)))

    def test_product_above_band_is_outside(self):
        self.assertFalse(is_within_chart_band(120.0, (0.1, 100.0)))

    def test_product_exactly_at_lower_edge_is_inside(self):
        self.assertTrue(is_within_chart_band(0.1, (0.1, 100.0)))

    def test_product_at_upper_edge_absorbs_representation_error(self):
        # A gap sized to land the product exactly on the titanium upper edge.
        # The division and multiplication overshoot 20.0 by a few units in the
        # last place; the case is charted and must not read as outside.
        frequency_ghz = 67.0 / 7.0
        gap_m = (20.0 / frequency_ghz) / 1000.0
        product = frequency_gap_product_ghz_mm(frequency_ghz * 1.0e9, gap_m)
        self.assertGreater(product, 20.0)
        self.assertAlmostEqual(product, 20.0, places=9)
        self.assertTrue(is_within_chart_band(product, (0.5, 20.0)))

    def test_non_positive_product_rejected(self):
        with self.assertRaises(ValueError):
            is_within_chart_band(0.0, (0.1, 100.0))


class TestQuasiStaticGate(unittest.TestCase):
    def test_ratio_against_wavelength(self):
        # One-metre wavelength: a 0.1 m separation is a tenth of it.
        self.assertAlmostEqual(
            gap_to_wavelength_ratio(SPEED_OF_LIGHT_M_S, 0.1), 0.1, places=12
        )

    def test_small_gap_is_quasi_static(self):
        self.assertTrue(is_quasi_static(1.0e10, 5.0e-4))

    def test_electrically_large_gap_is_not_quasi_static(self):
        self.assertFalse(is_quasi_static(1.0e10, 2.0e-2))

    def test_gap_exactly_at_the_limit_is_quasi_static(self):
        wavelength = SPEED_OF_LIGHT_M_S / 1.0e10
        gap_m = QUASI_STATIC_GAP_TO_WAVELENGTH_LIMIT * wavelength
        self.assertTrue(is_quasi_static(1.0e10, gap_m))

    def test_tighter_custom_limit_rejects_the_same_gap(self):
        self.assertFalse(is_quasi_static(1.0e10, 5.0e-4, limit=0.01))

    def test_non_positive_limit_rejected(self):
        with self.assertRaises(ValueError):
            is_quasi_static(1.0e10, 5.0e-4, limit=0.0)


class TestGapUniformity(unittest.TestCase):
    def test_single_separation_is_uniform(self):
        self.assertAlmostEqual(gap_uniformity_ratio({"gap_m": 1.0e-3}), 1.0)

    def test_ratio_of_extremes(self):
        ratio = gap_uniformity_ratio({"gap_max_m": 1.2e-3, "gap_min_m": 1.0e-3})
        self.assertAlmostEqual(ratio, 1.2, places=12)

    def test_inverted_extremes_rejected(self):
        with self.assertRaises(ValueError):
            gap_uniformity_ratio({"gap_max_m": 1.0e-3, "gap_min_m": 2.0e-3})

    def test_missing_minimum_rejected(self):
        with self.assertRaises(ValueError):
            gap_uniformity_ratio({"gap_max_m": 1.0e-3})


class TestLevelOneEligibility(unittest.TestCase):
    def test_baseline_case_clears_every_gate(self):
        out = level_one_eligibility(baseline_case())
        self.assertTrue(out["eligible"])
        self.assertEqual(out["blockers"], [])
        self.assertAlmostEqual(out["frequency_gap_product_ghz_mm"], 5.0, places=12)

    def test_gap_exactly_at_the_quasi_static_limit_stays_eligible(self):
        wavelength = SPEED_OF_LIGHT_M_S / 1.0e10
        gap_m = QUASI_STATIC_GAP_TO_WAVELENGTH_LIMIT * wavelength
        out = level_one_eligibility(baseline_case(gap_m=gap_m))
        self.assertTrue(out["eligible"])

    def test_multi_carrier_case_rejected(self):
        with self.assertRaises(ValueError):
            level_one_eligibility(baseline_case(carrier_count=4))

    def test_zero_carrier_count_rejected(self):
        with self.assertRaises(ValueError):
            level_one_eligibility(baseline_case(carrier_count=0))

    def test_non_integer_carrier_count_rejected(self):
        with self.assertRaises(ValueError):
            level_one_eligibility(baseline_case(carrier_count=1.5))

    def test_uncharted_surface_is_a_blocker_not_an_exception(self):
        out = level_one_eligibility(baseline_case(electrode_material="kapton-tape"))
        self.assertFalse(out["eligible"])
        self.assertEqual(len(out["blockers"]), 1)
        self.assertIsNone(out["chart_band_ghz_mm"])

    def test_product_outside_the_charted_band_blocks_the_chart_route(self):
        out = level_one_eligibility(
            baseline_case(electrode_material="titanium", gap_m=5.0e-3)
        )
        self.assertFalse(out["eligible"])
        self.assertEqual(len(out["blockers"]), 1)

    def test_electrically_large_gap_blocks_the_chart_route(self):
        out = level_one_eligibility(
            baseline_case(electrode_material="aluminium", gap_m=9.0e-3)
        )
        self.assertFalse(out["eligible"])
        self.assertEqual(len(out["blockers"]), 1)

    def test_non_uniform_gap_blocks_the_equivalent_reduction(self):
        out = level_one_eligibility(
            baseline_case(gap_max_m=1.3e-3, gap_min_m=1.0e-3)
        )
        self.assertFalse(out["eligible"])
        self.assertAlmostEqual(out["gap_uniformity_ratio"], 1.3, places=12)

    def test_dielectric_in_the_gap_blocks_the_chart_basis(self):
        out = level_one_eligibility(baseline_case(dielectric_in_gap=True))
        self.assertFalse(out["eligible"])

    def test_static_magnetic_field_blocks_the_chart_basis(self):
        out = level_one_eligibility(baseline_case(static_magnetic_field=True))
        self.assertFalse(out["eligible"])

    def test_blockers_accumulate(self):
        out = level_one_eligibility(
            baseline_case(
                geometry_family="microstrip-gap",
                dielectric_in_gap=True,
                static_magnetic_field=True,
            )
        )
        self.assertGreaterEqual(len(out["blockers"]), 3)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            level_one_eligibility(["parallel-plate", 1.0e10])

    def test_missing_geometry_rejected(self):
        case = baseline_case()
        del case["geometry_family"]
        with self.assertRaises(ValueError):
            level_one_eligibility(case)


class TestLevelTwoPrerequisites(unittest.TestCase):
    def test_nothing_declared_leaves_every_prerequisite_open(self):
        self.assertEqual(
            missing_level_two_prerequisites({}), list(LEVEL_TWO_PREREQUISITES)
        )

    def test_full_evidence_leaves_nothing_open(self):
        case = {"level_two_evidence": list(LEVEL_TWO_PREREQUISITES)}
        self.assertEqual(missing_level_two_prerequisites(case), [])

    def test_partial_evidence_reports_the_remainder(self):
        case = {"level_two_evidence": ["electron-seeding-model"]}
        self.assertEqual(len(missing_level_two_prerequisites(case)), 3)

    def test_unrecognized_evidence_item_rejected(self):
        with self.assertRaises(ValueError):
            missing_level_two_prerequisites({"level_two_evidence": ["vendor-promise"]})

    def test_non_list_evidence_rejected(self):
        with self.assertRaises(ValueError):
            missing_level_two_prerequisites({"level_two_evidence": "all-of-it"})


class TestRouteSelection(unittest.TestCase):
    def test_eligible_case_takes_the_chart_route(self):
        out = select_design_analysis_level(baseline_case())
        self.assertEqual(out["selected_level"], LEVEL_ONE)
        self.assertFalse(out["requested_level_rejected"])

    def test_detailed_route_may_always_be_requested(self):
        out = select_design_analysis_level(
            baseline_case(requested_level=LEVEL_TWO)
        )
        self.assertEqual(out["selected_level"], LEVEL_TWO)
        self.assertTrue(out["level_one_eligible"])
        self.assertFalse(out["requested_level_rejected"])

    def test_chart_route_request_is_rejected_when_a_gate_fails(self):
        out = select_design_analysis_level(
            baseline_case(geometry_family="microstrip-gap", requested_level=LEVEL_ONE)
        )
        self.assertEqual(out["selected_level"], LEVEL_TWO)
        self.assertTrue(out["requested_level_rejected"])
        self.assertGreaterEqual(len(out["rationale"]), 2)

    def test_ineligible_case_without_a_request_routes_to_the_detailed_path(self):
        out = select_design_analysis_level(
            baseline_case(geometry_family="arbitrary-three-dimensional")
        )
        self.assertEqual(out["selected_level"], LEVEL_TWO)
        self.assertFalse(out["requested_level_rejected"])

    def test_unknown_requested_level_rejected(self):
        with self.assertRaises(ValueError):
            select_design_analysis_level(baseline_case(requested_level="level-three"))


class TestSelectionAssessment(unittest.TestCase):
    def test_chart_route_case_is_ready_without_modelling_evidence(self):
        rec = assess_analysis_level_selection(baseline_case())
        self.assertEqual(rec["selected_level"], LEVEL_ONE)
        self.assertTrue(rec["ready_to_analyse"])
        self.assertEqual(rec["findings"], [])

    def test_detailed_route_without_evidence_is_not_ready(self):
        rec = assess_analysis_level_selection(
            baseline_case(geometry_family="microstrip-gap")
        )
        self.assertEqual(rec["selected_level"], LEVEL_TWO)
        self.assertFalse(rec["ready_to_analyse"])
        self.assertEqual(len(rec["missing_prerequisites"]), 4)
        self.assertEqual(len(rec["findings"]), 4)

    def test_detailed_route_with_full_evidence_is_ready(self):
        rec = assess_analysis_level_selection(
            baseline_case(
                geometry_family="microstrip-gap",
                level_two_evidence=list(LEVEL_TWO_PREREQUISITES),
            )
        )
        self.assertTrue(rec["ready_to_analyse"])
        self.assertEqual(rec["missing_prerequisites"], [])

    def test_rejected_chart_request_is_carried_into_the_findings(self):
        rec = assess_analysis_level_selection(
            baseline_case(
                geometry_family="microstrip-gap",
                requested_level=LEVEL_ONE,
                level_two_evidence=list(LEVEL_TWO_PREREQUISITES),
            )
        )
        self.assertTrue(rec["requested_level_rejected"])
        self.assertTrue(rec["findings"])
        self.assertTrue(rec["ready_to_analyse"])


class TestUnitRollUp(unittest.TestCase):
    def _cases(self):
        return [
            baseline_case(identifier="chart-gap"),
            baseline_case(
                identifier="modelled-gap",
                geometry_family="arbitrary-three-dimensional",
                level_two_evidence=list(LEVEL_TWO_PREREQUISITES),
            ),
            baseline_case(
                identifier="open-gap", geometry_family="dielectric-loaded-gap"
            ),
        ]

    def test_roll_up_splits_the_routes(self):
        out = summarize_level_selection(self._cases())
        self.assertEqual(out["gap_count"], 3)
        self.assertEqual(out["level_one_gaps"], ["chart-gap"])
        self.assertEqual(out["level_two_gaps"], ["modelled-gap", "open-gap"])

    def test_open_prerequisite_holds_the_unit_back(self):
        out = summarize_level_selection(self._cases())
        self.assertEqual(out["gaps_not_ready"], ["open-gap"])
        self.assertFalse(out["unit_ready"])

    def test_unit_is_ready_when_every_gap_is(self):
        out = summarize_level_selection(self._cases()[:2])
        self.assertTrue(out["unit_ready"])
        self.assertEqual(out["gaps_not_ready"], [])

    def test_empty_case_list_rejected(self):
        with self.assertRaises(ValueError):
            summarize_level_selection([])

    def test_non_list_cases_rejected(self):
        with self.assertRaises(ValueError):
            summarize_level_selection(baseline_case())


if __name__ == "__main__":
    unittest.main()
