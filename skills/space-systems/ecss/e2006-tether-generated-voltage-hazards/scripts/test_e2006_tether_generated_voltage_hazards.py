#!/usr/bin/env python3
"""Contract test for the clause 10.2.1 tether potential-hazard logic."""

import math
import unittest

from e2006_tether_generated_voltage_hazards_logic import (
    ARC_ONSET_BY_SURFACE,
    GROUND_HANDLING_TOUCH_LIMIT_V,
    MIN_INSULATION_MARGIN,
    SEVERITY_COMPLIANT,
    SEVERITY_EXCEEDED,
    SEVERITY_MARGINAL,
    arc_onset_v,
    assess_end,
    assess_insulation_spans,
    assess_voltage_hazards,
    categorize_end_severity,
    end_potentials,
    ground_handling_exceedance,
    insulation_margin,
    motional_electric_field,
    tether_emf,
)


def config(**overrides):
    base = {
        "velocity_mps": 7500.0,
        "field_tesla": 3.0e-5,
        "velocity_field_angle_deg": 90.0,
        "deployed_length_m": 5000.0,
        "tether_alignment_deg": 0.0,
        "floating_fraction": 0.5,
        "ends": [
            {
                "role": "anode-end",
                "surface_kind": "plasma-contactor-electrode",
                "reachable_during_handling": False,
            },
            {
                "role": "cathode-end",
                "surface_kind": "plasma-contactor-electrode",
                "reachable_during_handling": False,
            },
        ],
        "insulation_spans": [],
    }
    base.update(overrides)
    return base


class TestMotionalField(unittest.TestCase):
    def test_perpendicular_case(self):
        self.assertAlmostEqual(
            motional_electric_field(7500.0, 3.0e-5, 90.0), 0.225, places=9
        )

    def test_oblique_case_reduces_field(self):
        value = motional_electric_field(7500.0, 3.0e-5, 30.0)
        self.assertAlmostEqual(value, 0.225 * 0.5, places=9)

    def test_parallel_motion_induces_nothing(self):
        self.assertAlmostEqual(motional_electric_field(7500.0, 3.0e-5, 0.0), 0.0, places=12)

    def test_antiparallel_motion_induces_nothing(self):
        self.assertAlmostEqual(
            motional_electric_field(7500.0, 3.0e-5, 180.0), 0.0, places=12
        )

    def test_zero_velocity_rejected(self):
        with self.assertRaises(ValueError):
            motional_electric_field(0.0, 3.0e-5, 90.0)

    def test_zero_field_rejected(self):
        with self.assertRaises(ValueError):
            motional_electric_field(7500.0, 0.0, 90.0)

    def test_angle_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            motional_electric_field(7500.0, 3.0e-5, 190.0)

    def test_non_numeric_velocity_rejected(self):
        with self.assertRaises(ValueError):
            motional_electric_field("7500", 3.0e-5, 90.0)

    def test_infinite_field_rejected(self):
        with self.assertRaises(ValueError):
            motional_electric_field(7500.0, float("inf"), 90.0)


class TestTetherEmf(unittest.TestCase):
    def test_aligned_line_integrates_the_whole_field(self):
        self.assertAlmostEqual(tether_emf(0.225, 5000.0, 0.0), 1125.0, places=6)

    def test_crosswise_line_develops_nothing(self):
        self.assertAlmostEqual(tether_emf(0.225, 5000.0, 90.0), 0.0, places=9)

    def test_reversed_line_reverses_polarity(self):
        self.assertAlmostEqual(tether_emf(0.225, 5000.0, 180.0), -1125.0, places=6)

    def test_sixty_degree_alignment_halves_the_force(self):
        self.assertAlmostEqual(tether_emf(0.225, 5000.0, 60.0), 562.5, places=6)

    def test_negative_field_rejected(self):
        with self.assertRaises(ValueError):
            tether_emf(-0.225, 5000.0, 0.0)

    def test_zero_length_rejected(self):
        with self.assertRaises(ValueError):
            tether_emf(0.225, 0.0, 0.0)

    def test_alignment_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            tether_emf(0.225, 5000.0, -10.0)


class TestEndPotentials(unittest.TestCase):
    def test_symmetric_float_splits_evenly(self):
        ends = end_potentials(1125.0, 0.5)
        self.assertAlmostEqual(ends["anode-end"], 562.5, places=6)
        self.assertAlmostEqual(ends["cathode-end"], -562.5, places=6)

    def test_contactor_at_the_cathode_pushes_the_line_positive(self):
        ends = end_potentials(1125.0, 0.05)
        self.assertAlmostEqual(ends["anode-end"], 1068.75, places=6)
        self.assertAlmostEqual(ends["cathode-end"], -56.25, places=6)

    def test_fully_negative_float(self):
        ends = end_potentials(1125.0, 1.0)
        self.assertAlmostEqual(ends["anode-end"], 0.0, places=9)
        self.assertAlmostEqual(ends["cathode-end"], -1125.0, places=6)

    def test_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            end_potentials(1125.0, 1.2)

    def test_negative_fraction_rejected(self):
        with self.assertRaises(ValueError):
            end_potentials(1125.0, -0.1)

    def test_non_numeric_emf_rejected(self):
        with self.assertRaises(ValueError):
            end_potentials(None, 0.5)


class TestArcOnsetAndSeverity(unittest.TestCase):
    def test_known_surface_returns_its_onset(self):
        self.assertAlmostEqual(arc_onset_v("bare-metal-in-plasma"), 100.0, places=6)

    def test_every_catalogued_onset_is_positive(self):
        for kind in ARC_ONSET_BY_SURFACE:
            self.assertGreater(arc_onset_v(kind), 0.0)

    def test_unknown_surface_rejected(self):
        with self.assertRaises(ValueError):
            arc_onset_v("painted-radiator")

    def test_low_potential_is_compliant(self):
        self.assertEqual(categorize_end_severity(-40.0, 100.0), SEVERITY_COMPLIANT)

    def test_potential_between_bands_is_marginal(self):
        self.assertEqual(categorize_end_severity(-90.0, 100.0), SEVERITY_MARGINAL)

    def test_potential_above_onset_is_exceeded(self):
        self.assertEqual(categorize_end_severity(-140.0, 100.0), SEVERITY_EXCEEDED)

    def test_sign_does_not_change_the_band(self):
        self.assertEqual(
            categorize_end_severity(140.0, 100.0),
            categorize_end_severity(-140.0, 100.0),
        )

    def test_exact_band_edge_stays_compliant_despite_float_error(self):
        # 79.7 + 0.1 + 0.2 is exactly the 80 % band edge in exact arithmetic
        # but lands a few ULPs above it in binary; the band must not move.
        edge = 79.7 + 0.1 + 0.2
        self.assertEqual(categorize_end_severity(edge, 100.0), SEVERITY_COMPLIANT)

    def test_exact_onset_is_marginal_not_exceeded(self):
        self.assertEqual(categorize_end_severity(100.0, 100.0), SEVERITY_MARGINAL)

    def test_zero_onset_rejected(self):
        with self.assertRaises(ValueError):
            categorize_end_severity(50.0, 0.0)


class TestInsulationAndTouch(unittest.TestCase):
    def test_margin_is_withstand_over_stress(self):
        self.assertAlmostEqual(insulation_margin(-250.0, 1000.0), 4.0, places=9)

    def test_unstressed_span_has_unbounded_margin(self):
        self.assertTrue(math.isinf(insulation_margin(0.0, 1000.0)))

    def test_zero_withstand_rejected(self):
        with self.assertRaises(ValueError):
            insulation_margin(100.0, 0.0)

    def test_touch_limit_respected(self):
        self.assertFalse(ground_handling_exceedance(45.0))

    def test_touch_limit_exceeded(self):
        self.assertTrue(ground_handling_exceedance(-120.0))

    def test_exact_touch_limit_is_not_an_exceedance(self):
        edge = 59.7 + 0.1 + 0.2
        self.assertFalse(ground_handling_exceedance(edge))

    def test_touch_limit_constant(self):
        self.assertAlmostEqual(GROUND_HANDLING_TOUCH_LIMIT_V, 60.0, places=9)

    def test_negative_touch_limit_rejected(self):
        with self.assertRaises(ValueError):
            ground_handling_exceedance(10.0, limit_v=-1.0)


class TestAssessEnd(unittest.TestCase):
    def test_clean_end(self):
        record = assess_end(
            {"role": "anode-end", "surface_kind": "plasma-contactor-electrode"}, 120.0
        )
        self.assertTrue(record["compliant"])
        self.assertEqual(record["findings"], [])

    def test_arcing_end_reports_the_driver(self):
        record = assess_end(
            {"role": "cathode-end", "surface_kind": "bare-metal-in-plasma"}, -562.5
        )
        self.assertFalse(record["compliant"])
        self.assertEqual(record["severity"], SEVERITY_EXCEEDED)
        self.assertTrue(any("arc onset" in f for f in record["findings"]))

    def test_marginal_end_is_reported_without_failing(self):
        record = assess_end(
            {"role": "anode-end", "surface_kind": "bare-metal-in-plasma"}, 90.0
        )
        self.assertTrue(record["compliant"])
        self.assertEqual(record["severity"], SEVERITY_MARGINAL)
        self.assertEqual(len(record["findings"]), 1)

    def test_reachable_end_adds_the_touch_finding(self):
        record = assess_end(
            {
                "role": "anode-end",
                "surface_kind": "anodized-structure",
                "reachable_during_handling": True,
            },
            150.0,
        )
        self.assertTrue(record["touch_exceeded"])
        self.assertFalse(record["compliant"])

    def test_unreachable_end_skips_the_touch_check(self):
        record = assess_end(
            {
                "role": "anode-end",
                "surface_kind": "anodized-structure",
                "reachable_during_handling": False,
            },
            150.0,
        )
        self.assertFalse(record["touch_exceeded"])

    def test_bad_role_rejected(self):
        with self.assertRaises(ValueError):
            assess_end({"role": "mid-span", "surface_kind": "bare-metal-in-plasma"}, 10.0)

    def test_non_boolean_reach_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_end(
                {
                    "role": "anode-end",
                    "surface_kind": "bare-metal-in-plasma",
                    "reachable_during_handling": "yes",
                },
                10.0,
            )

    def test_non_mapping_end_rejected(self):
        with self.assertRaises(ValueError):
            assess_end(["anode-end"], 10.0)


class TestInsulationSpans(unittest.TestCase):
    def test_span_with_ample_margin(self):
        records = assess_insulation_spans(
            [{"id": "mid-span", "length_share": 0.5, "withstand_v": 5000.0}], 1125.0
        )
        self.assertTrue(records[0]["compliant"])
        self.assertAlmostEqual(records[0]["stress_v"], 562.5, places=6)

    def test_span_below_required_margin(self):
        records = assess_insulation_spans(
            [{"id": "mid-span", "length_share": 1.0, "withstand_v": 1500.0}], 1125.0
        )
        self.assertFalse(records[0]["compliant"])
        self.assertTrue(any("below the required" in f for f in records[0]["findings"]))

    def test_exact_required_margin_passes_despite_float_error(self):
        share = (0.1 + 0.2) / 3.0
        records = assess_insulation_spans(
            [{"id": "edge-span", "length_share": share, "withstand_v": 20.0}], 100.0
        )
        self.assertTrue(records[0]["compliant"])
        self.assertAlmostEqual(records[0]["margin"], MIN_INSULATION_MARGIN, places=9)

    def test_polarity_does_not_change_the_stress(self):
        positive = assess_insulation_spans(
            [{"id": "s", "length_share": 0.4, "withstand_v": 5000.0}], 1125.0
        )
        negative = assess_insulation_spans(
            [{"id": "s", "length_share": 0.4, "withstand_v": 5000.0}], -1125.0
        )
        self.assertAlmostEqual(positive[0]["stress_v"], negative[0]["stress_v"], places=9)

    def test_share_above_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_insulation_spans(
                [{"id": "s", "length_share": 1.5, "withstand_v": 5000.0}], 1125.0
            )

    def test_zero_share_rejected(self):
        with self.assertRaises(ValueError):
            assess_insulation_spans(
                [{"id": "s", "length_share": 0.0, "withstand_v": 5000.0}], 1125.0
            )

    def test_missing_withstand_rejected(self):
        with self.assertRaises(ValueError):
            assess_insulation_spans([{"id": "s", "length_share": 0.5}], 1125.0)

    def test_empty_span_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_insulation_spans(
                [{"id": "", "length_share": 0.5, "withstand_v": 5000.0}], 1125.0
            )

    def test_non_list_spans_rejected(self):
        with self.assertRaises(ValueError):
            assess_insulation_spans({"id": "s"}, 1125.0)


class TestAssessVoltageHazards(unittest.TestCase):
    def test_nominal_electrodynamic_case(self):
        result = assess_voltage_hazards(config())
        self.assertAlmostEqual(result["induced_field_v_per_m"], 0.225, places=9)
        self.assertAlmostEqual(result["emf_v"], 1125.0, places=6)
        self.assertAlmostEqual(result["end_potentials_v"]["anode-end"], 562.5, places=6)
        self.assertFalse(result["compliant"])

    def test_bare_metal_ends_fail_on_arcing(self):
        cfg = config(
            ends=[
                {"role": "anode-end", "surface_kind": "bare-metal-in-plasma"},
                {"role": "cathode-end", "surface_kind": "bare-metal-in-plasma"},
            ]
        )
        result = assess_voltage_hazards(cfg)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 2)

    def test_short_line_stays_inside_every_limit(self):
        cfg = config(deployed_length_m=100.0)
        result = assess_voltage_hazards(cfg)
        self.assertAlmostEqual(result["emf_v"], 22.5, places=6)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_crosswise_line_has_no_force_and_no_finding(self):
        cfg = config(tether_alignment_deg=90.0)
        result = assess_voltage_hazards(cfg)
        self.assertAlmostEqual(result["emf_v"], 0.0, places=9)
        self.assertTrue(result["compliant"])

    def test_marginal_end_is_listed_separately(self):
        cfg = config(
            deployed_length_m=800.0,
            ends=[
                {"role": "anode-end", "surface_kind": "bare-metal-in-plasma"},
                {"role": "cathode-end", "surface_kind": "bare-metal-in-plasma"},
            ],
        )
        result = assess_voltage_hazards(cfg)
        self.assertAlmostEqual(result["emf_v"], 180.0, places=6)
        self.assertEqual(sorted(result["marginal_ends"]), ["anode-end", "cathode-end"])
        self.assertTrue(result["compliant"])
        self.assertEqual(len(result["findings"]), 2)

    def test_insulation_span_folds_into_the_summary(self):
        cfg = config(
            insulation_spans=[
                {"id": "outboard", "length_share": 1.0, "withstand_v": 1500.0}
            ]
        )
        result = assess_voltage_hazards(cfg)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("outboard" in f for f in result["findings"]))

    def test_missing_required_field_rejected(self):
        cfg = config()
        del cfg["deployed_length_m"]
        with self.assertRaises(ValueError):
            assess_voltage_hazards(cfg)

    def test_wrong_end_count_rejected(self):
        cfg = config(ends=[{"role": "anode-end", "surface_kind": "bare-metal-in-plasma"}])
        with self.assertRaises(ValueError):
            assess_voltage_hazards(cfg)

    def test_duplicate_end_role_rejected(self):
        cfg = config(
            ends=[
                {"role": "anode-end", "surface_kind": "bare-metal-in-plasma"},
                {"role": "anode-end", "surface_kind": "bare-metal-in-plasma"},
            ]
        )
        with self.assertRaises(ValueError):
            assess_voltage_hazards(cfg)

    def test_non_mapping_config_rejected(self):
        with self.assertRaises(ValueError):
            assess_voltage_hazards("tether")


if __name__ == "__main__":
    unittest.main()
