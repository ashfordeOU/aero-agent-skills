#!/usr/bin/env python3
"""Gate 3 contract test for e20-reliable-insulation-underlying-assumptions.

stdlib unittest, offline, deterministic. Run:
python3 test_e20_reliable_insulation_underlying_assumptions.py
"""

import copy
import unittest

from e20_reliable_insulation_underlying_assumptions_logic import (
    CORONA_BAND_PA,
    MIN_WITHSTAND_FACTOR,
    REQUIRED_ASSUMPTIONS,
    assumption_findings,
    assumptions_hold,
    categorize_layer,
    environment_findings,
    layer_set_admissible,
    layers_independent,
    reliable_insulation_assumptions_review,
    withstand_margin,
)


def _basic():
    return {
        "layer_type": "basic_insulation",
        "part_id": "SLV-PTFE-01",
        "material": "ptfe",
        "process": "extruded_sleeve",
        "withstand_v": 1500.0,
    }


def _supplementary():
    return {
        "layer_type": "supplementary_insulation",
        "part_id": "POT-EPX-02",
        "material": "epoxy",
        "process": "vacuum_potting",
        "withstand_v": 1800.0,
    }


def _case():
    return {
        "layers": [_basic(), _supplementary()],
        "applied_stress_v": 600.0,
        "applied": {"voltage_v": 600.0, "temperature_c": 40.0, "pressure_pa": 1.0e-5},
        "qualified": {
            "max_voltage_v": 1000.0,
            "min_temperature_c": -40.0,
            "max_temperature_c": 85.0,
            "corona_band_qualified": False,
        },
        "conductive_bypass": False,
    }


class TestLayerCategorization(unittest.TestCase):
    def test_each_declared_type_maps_to_a_role(self):
        self.assertEqual(categorize_layer("basic_insulation"), "basic")
        self.assertEqual(
            categorize_layer("supplementary_insulation"), "supplementary"
        )
        self.assertEqual(categorize_layer("reinforced_insulation"), "reinforced")
        self.assertEqual(categorize_layer("functional_insulation"), "functional")

    def test_unrecognized_layer_type_raises(self):
        with self.assertRaises(ValueError):
            categorize_layer("conformal_coating")

    def test_unhashable_layer_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_layer({"type": "basic_insulation"})


class TestLayerSetAdmissibility(unittest.TestCase):
    def test_basic_plus_supplementary_is_admissible(self):
        result = layer_set_admissible([_basic(), _supplementary()])
        self.assertTrue(result["admissible"])
        self.assertEqual(result["shape"], "basic_plus_supplementary")

    def test_qualified_reinforced_layer_alone_is_admissible(self):
        result = layer_set_admissible(
            [
                {
                    "layer_type": "reinforced_insulation",
                    "qualified_full_stress": True,
                }
            ]
        )
        self.assertTrue(result["admissible"])
        self.assertEqual(result["shape"], "reinforced_single_layer")

    def test_unqualified_reinforced_layer_is_rejected(self):
        result = layer_set_admissible(
            [{"layer_type": "reinforced_insulation", "qualified_full_stress": False}]
        )
        self.assertFalse(result["admissible"])
        self.assertEqual(
            result["reason"], "reinforced_layer_not_qualified_to_full_stress"
        )

    def test_functional_layer_does_not_complete_the_set(self):
        result = layer_set_admissible(
            [_basic(), {"layer_type": "functional_insulation"}]
        )
        self.assertFalse(result["admissible"])

    def test_single_basic_layer_is_inadmissible(self):
        self.assertFalse(layer_set_admissible([_basic()])["admissible"])

    def test_empty_layer_set_raises(self):
        with self.assertRaises(ValueError):
            layer_set_admissible([])

    def test_layer_without_type_key_raises(self):
        with self.assertRaises(ValueError):
            layer_set_admissible([{"part_id": "X"}])


class TestIndependence(unittest.TestCase):
    def test_distinct_part_material_and_process_is_independent(self):
        result = layers_independent(_basic(), _supplementary())
        self.assertTrue(result["independent"])
        self.assertEqual(result["common_cause"], [])

    def test_shared_part_is_fatal_even_with_other_differences(self):
        a = _basic()
        b = _supplementary()
        b["part_id"] = a["part_id"]
        result = layers_independent(a, b)
        self.assertFalse(result["independent"])
        self.assertIn("shared_part", result["common_cause"])

    def test_shared_material_alone_still_leaves_process_diversity(self):
        a = _basic()
        b = _supplementary()
        b["material"] = a["material"]
        result = layers_independent(a, b)
        self.assertTrue(result["independent"])
        self.assertEqual(result["common_cause"], ["shared_material"])

    def test_shared_material_and_process_defeats_independence(self):
        a = _basic()
        b = _supplementary()
        b["material"] = a["material"]
        b["process"] = a["process"]
        result = layers_independent(a, b)
        self.assertFalse(result["independent"])
        self.assertEqual(
            result["common_cause"], ["shared_material", "shared_process"]
        )

    def test_missing_independence_key_raises(self):
        a = _basic()
        del a["process"]
        with self.assertRaises(ValueError):
            layers_independent(a, _supplementary())


class TestWithstandMargin(unittest.TestCase):
    def test_margin_is_the_survivor_ratio(self):
        result = withstand_margin(1500.0, 500.0)
        self.assertAlmostEqual(result["margin"], 3.0)
        self.assertTrue(result["adequate"])

    def test_margin_exactly_at_the_required_factor_is_adequate(self):
        result = withstand_margin(1200.0, 600.0)
        self.assertAlmostEqual(result["margin"], MIN_WITHSTAND_FACTOR)
        self.assertTrue(result["adequate"])

    def test_margin_below_the_factor_is_inadequate(self):
        result = withstand_margin(1100.0, 600.0)
        self.assertFalse(result["adequate"])
        self.assertAlmostEqual(result["margin"], 1100.0 / 600.0)

    def test_non_positive_inputs_raise(self):
        with self.assertRaises(ValueError):
            withstand_margin(0.0, 600.0)
        with self.assertRaises(ValueError):
            withstand_margin(1500.0, -1.0)

    def test_required_factor_below_unity_raises(self):
        with self.assertRaises(ValueError):
            withstand_margin(1500.0, 600.0, required_factor=0.5)


class TestEnvironmentEnvelope(unittest.TestCase):
    def test_covered_environment_reports_nothing(self):
        case = _case()
        self.assertEqual(
            environment_findings(case["applied"], case["qualified"]), []
        )

    def test_voltage_above_ceiling_is_flagged(self):
        case = _case()
        case["applied"]["voltage_v"] = 1200.0
        self.assertIn(
            "applied_voltage_above_qualified_ceiling",
            environment_findings(case["applied"], case["qualified"]),
        )

    def test_temperature_outside_range_is_flagged_both_ways(self):
        case = _case()
        case["applied"]["temperature_c"] = -60.0
        self.assertIn(
            "applied_temperature_outside_qualified_range",
            environment_findings(case["applied"], case["qualified"]),
        )
        case["applied"]["temperature_c"] = 95.0
        self.assertIn(
            "applied_temperature_outside_qualified_range",
            environment_findings(case["applied"], case["qualified"]),
        )

    def test_corona_band_without_qualification_is_flagged(self):
        case = _case()
        case["applied"]["pressure_pa"] = 100.0
        self.assertIn(
            "low_pressure_corona_band_not_qualified",
            environment_findings(case["applied"], case["qualified"]),
        )

    def test_corona_band_edges_are_inside_the_band(self):
        case = _case()
        low, high = CORONA_BAND_PA
        for pressure in (low, high):
            case["applied"]["pressure_pa"] = pressure
            self.assertIn(
                "low_pressure_corona_band_not_qualified",
                environment_findings(case["applied"], case["qualified"]),
            )

    def test_corona_band_with_qualification_is_clean(self):
        case = _case()
        case["applied"]["pressure_pa"] = 100.0
        case["qualified"]["corona_band_qualified"] = True
        self.assertEqual(
            environment_findings(case["applied"], case["qualified"]), []
        )

    def test_missing_or_invalid_environment_data_raises(self):
        case = _case()
        broken = dict(case["applied"])
        del broken["pressure_pa"]
        with self.assertRaises(ValueError):
            environment_findings(broken, case["qualified"])
        negative = dict(case["applied"])
        negative["voltage_v"] = -1.0
        with self.assertRaises(ValueError):
            environment_findings(negative, case["qualified"])
        negative_p = dict(case["applied"])
        negative_p["pressure_pa"] = -1.0
        with self.assertRaises(ValueError):
            environment_findings(negative_p, case["qualified"])

    def test_inverted_qualified_range_raises(self):
        case = _case()
        case["qualified"]["min_temperature_c"] = 120.0
        with self.assertRaises(ValueError):
            environment_findings(case["applied"], case["qualified"])

    def test_missing_envelope_key_raises(self):
        case = _case()
        broken = dict(case["qualified"])
        del broken["corona_band_qualified"]
        with self.assertRaises(ValueError):
            environment_findings(case["applied"], broken)


class TestAssumptionReview(unittest.TestCase):
    def test_sound_case_holds_on_every_assumption(self):
        review = reliable_insulation_assumptions_review(_case())
        self.assertTrue(assumptions_hold(review))
        self.assertEqual(sorted(review.keys()), sorted(REQUIRED_ASSUMPTIONS))

    def test_common_cause_is_reported_under_its_assumption(self):
        case = _case()
        case["layers"][1]["material"] = case["layers"][0]["material"]
        case["layers"][1]["process"] = case["layers"][0]["process"]
        review = reliable_insulation_assumptions_review(case)
        self.assertEqual(len(review["independent_layers"]), 1)
        self.assertFalse(assumptions_hold(review))

    def test_thin_survivor_is_reported_per_layer(self):
        case = _case()
        case["applied_stress_v"] = 1000.0
        findings = assumption_findings(case)
        margin_findings = [
            f for f in findings if f["assumption"] == "surviving_layer_withstand"
        ]
        self.assertEqual(len(margin_findings), 2)
        self.assertAlmostEqual(margin_findings[0]["margin"], 1.5)

    def test_conductive_bypass_is_its_own_finding(self):
        case = _case()
        case["conductive_bypass"] = True
        review = reliable_insulation_assumptions_review(case)
        self.assertEqual(len(review["no_conductive_bypass"]), 1)
        self.assertFalse(assumptions_hold(review))

    def test_review_does_not_mutate_the_case(self):
        case = _case()
        snapshot = copy.deepcopy(case)
        reliable_insulation_assumptions_review(case)
        self.assertEqual(case, snapshot)


if __name__ == "__main__":
    unittest.main()
