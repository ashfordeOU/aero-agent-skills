#!/usr/bin/env python3
"""Contract test for the coated coverglass source control drawing, Annex D (offline)."""

import copy
import unittest

from e2008_coverglass_source_control_drawing_logic import (
    DEFAULT_SCD_POLICY,
    DIMENSION_BAND_TOO_WIDE,
    DIMENSION_UNBRACKETED,
    DIMENSION_UNTOLERANCED,
    DIMENSION_USABLE,
    REQUIRED_SCD_CONTENT,
    SCD_NOT_RELEASABLE,
    SCD_RELEASABLE,
    STACK_FUNCTION_MISSING,
    STACK_THIN,
    STACK_USABLE,
    WINDOW_INVERTED,
    WINDOW_TOO_NARROW,
    WINDOW_TRANSMITTANCE_IMPOSSIBLE,
    WINDOW_USABLE,
    assess_coating_stack,
    assess_coverglass_scd,
    assess_dimensional_entry,
    assess_optical_window,
    audit_scd_content,
    dimensional_content,
    required_scd_content,
    validate_scd_policy,
)


def _stack():
    return [
        {"function": "antireflection", "face": "front"},
        {"function": "ultraviolet-reject", "face": "front"},
    ]


def _window(**overrides):
    entry = {"cut_on_nm": 350.0, "cut_off_nm": 1800.0, "min_transmittance": 0.92}
    entry.update(overrides)
    return entry


def _content(**overrides):
    content = {
        "drawing_identifier": "scd-cg-0041",
        "issue_and_date": "issue C, 2026-06-14",
        "component_description": "coated cerium-doped coverglass for a solar cell assembly",
        "substrate_material": "cerium-doped borosilicate, radiation stabilised",
        "thickness": {"coverglass_thickness_mm": {"nominal": 0.100, "minimum": 0.095, "maximum": 0.105}},
        "planar_dimensions": {
            "coverglass_length_mm": {"nominal": 40.0, "minimum": 39.8, "maximum": 40.2},
            "coverglass_width_mm": {"nominal": 30.0, "minimum": 29.85, "maximum": 30.15},
        },
        "coating_stack": _stack(),
        "optical_window": _window(),
        "solar_absorptance": "0.08 maximum over the stated window",
        "thermal_emittance": "0.85 minimum, normal hemispherical",
        "radiation_requirement": "no transmittance loss beyond the stated budget after the mission fluence",
        "surface_quality_requirement": "scratch and dig limits per the assembly inspection baseline",
        "marking_and_traceability": "lot code etched on the carrier, not on the optical face",
        "packaging_and_handling": "cleanroom trays, electrostatic-safe, humidity controlled",
        "acceptance_inspection": "sampling plan, optical and dimensional checks per lot",
        "approved_source": "named coating house and substrate supplier, both on the approved list",
    }
    content.update(overrides)
    return content


def _drawing(content=None, **overrides):
    drawing = {
        "drawing_id": "scd-cg-0041",
        "content": content if content is not None else _content(),
    }
    drawing.update(overrides)
    return drawing


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_scd_policy(DEFAULT_SCD_POLICY), DEFAULT_SCD_POLICY)

    def test_default_policy_demands_every_heading(self):
        self.assertAlmostEqual(DEFAULT_SCD_POLICY["min_content_fraction"], 1.0, places=9)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_scd_policy("draw everything")

    def test_out_of_range_band_fraction_rejected(self):
        broken = copy.deepcopy(DEFAULT_SCD_POLICY)
        broken["max_thickness_band_fraction"] = 1.4
        with self.assertRaises(ValueError):
            validate_scd_policy(broken)

    def test_zero_coating_layer_floor_rejected(self):
        broken = copy.deepcopy(DEFAULT_SCD_POLICY)
        broken["min_coating_layers"] = 0
        with self.assertRaises(ValueError):
            validate_scd_policy(broken)

    def test_non_boolean_conductive_switch_rejected(self):
        broken = copy.deepcopy(DEFAULT_SCD_POLICY)
        broken["require_conductive_coating"] = "yes"
        with self.assertRaises(ValueError):
            validate_scd_policy(broken)


class RequiredContentTests(unittest.TestCase):
    def test_content_set_is_returned_as_a_tuple_copy(self):
        headings = required_scd_content()
        self.assertEqual(headings, REQUIRED_SCD_CONTENT)
        self.assertIsInstance(headings, tuple)

    def test_content_set_carries_the_optical_window_and_the_source(self):
        headings = required_scd_content()
        self.assertIn("optical_window", headings)
        self.assertIn("approved_source", headings)

    def test_dimensional_headings_are_a_subset_of_the_content_set(self):
        self.assertTrue(set(dimensional_content()) <= set(required_scd_content()))


class ContentAuditTests(unittest.TestCase):
    def test_a_full_drawing_is_missing_nothing(self):
        self.assertEqual(audit_scd_content(_drawing()), [])

    def test_a_dropped_heading_is_named(self):
        content = _content()
        del content["radiation_requirement"]
        self.assertEqual(audit_scd_content(_drawing(content)), ["radiation_requirement"])

    def test_an_empty_string_heading_counts_as_absent(self):
        self.assertEqual(
            audit_scd_content(_drawing(_content(marking_and_traceability="   "))),
            ["marking_and_traceability"],
        )

    def test_an_empty_coating_stack_counts_as_absent(self):
        self.assertEqual(
            audit_scd_content(_drawing(_content(coating_stack=[]))), ["coating_stack"]
        )

    def test_non_mapping_drawing_rejected(self):
        with self.assertRaises(ValueError):
            audit_scd_content("a drawing")

    def test_non_mapping_content_rejected(self):
        with self.assertRaises(ValueError):
            audit_scd_content({"drawing_id": "scd-cg-0041", "content": "everything"})


class DimensionTests(unittest.TestCase):
    def test_a_banded_dimension_is_usable(self):
        result = assess_dimensional_entry(
            "coverglass_thickness_mm",
            {"nominal": 0.100, "minimum": 0.095, "maximum": 0.105},
            0.10,
        )
        self.assertEqual(result["verdict"], DIMENSION_USABLE)
        self.assertTrue(result["brackets_nominal"])

    def test_band_fraction_is_reported(self):
        result = assess_dimensional_entry(
            "coverglass_thickness_mm",
            {"nominal": 0.100, "minimum": 0.095, "maximum": 0.105},
            0.10,
        )
        self.assertAlmostEqual(result["band_fraction"], 0.1, places=9)

    def test_a_band_exactly_on_the_limit_is_accepted(self):
        result = assess_dimensional_entry(
            "coverglass_thickness_mm",
            {"nominal": 1.0, "minimum": 0.95, "maximum": 1.05},
            0.10,
        )
        self.assertEqual(result["verdict"], DIMENSION_USABLE)

    def test_a_dimension_with_no_band_is_untoleranced(self):
        result = assess_dimensional_entry(
            "coverglass_thickness_mm", {"nominal": 0.100}, 0.10
        )
        self.assertEqual(result["verdict"], DIMENSION_UNTOLERANCED)
        self.assertIsNone(result["band_width"])

    def test_a_band_that_misses_its_nominal_is_unbracketed(self):
        result = assess_dimensional_entry(
            "coverglass_thickness_mm",
            {"nominal": 0.100, "minimum": 0.102, "maximum": 0.104},
            0.10,
        )
        self.assertEqual(result["verdict"], DIMENSION_UNBRACKETED)

    def test_a_band_wider_than_the_limit_is_named(self):
        result = assess_dimensional_entry(
            "coverglass_thickness_mm",
            {"nominal": 0.100, "minimum": 0.080, "maximum": 0.130},
            0.10,
        )
        self.assertEqual(result["verdict"], DIMENSION_BAND_TOO_WIDE)

    def test_an_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            assess_dimensional_entry(
                "coverglass_thickness_mm",
                {"nominal": 0.100, "minimum": 0.120, "maximum": 0.090},
                0.10,
            )

    def test_a_non_positive_nominal_rejected(self):
        with self.assertRaises(ValueError):
            assess_dimensional_entry("coverglass_thickness_mm", {"nominal": 0.0}, 0.10)

    def test_non_mapping_dimension_rejected(self):
        with self.assertRaises(ValueError):
            assess_dimensional_entry("coverglass_thickness_mm", "0.1 mm", 0.10)


class OpticalWindowTests(unittest.TestCase):
    def test_a_stated_window_is_usable(self):
        result = assess_optical_window(_window())
        self.assertEqual(result["verdict"], WINDOW_USABLE)
        self.assertTrue(result["wide_enough"])

    def test_window_width_is_reported(self):
        result = assess_optical_window(_window())
        self.assertAlmostEqual(result["window_width_nm"], 1450.0, places=9)

    def test_a_window_running_backwards_is_inverted(self):
        result = assess_optical_window(_window(cut_on_nm=1800.0, cut_off_nm=350.0))
        self.assertEqual(result["verdict"], WINDOW_INVERTED)

    def test_a_window_of_zero_width_is_inverted(self):
        result = assess_optical_window(_window(cut_on_nm=900.0, cut_off_nm=900.0))
        self.assertEqual(result["verdict"], WINDOW_INVERTED)

    def test_a_window_narrower_than_the_floor_is_named(self):
        result = assess_optical_window(_window(cut_on_nm=800.0, cut_off_nm=850.0))
        self.assertEqual(result["verdict"], WINDOW_TOO_NARROW)

    def test_a_window_exactly_on_the_width_floor_is_accepted(self):
        result = assess_optical_window(_window(cut_on_nm=800.0, cut_off_nm=900.0))
        self.assertEqual(result["verdict"], WINDOW_USABLE)
        self.assertAlmostEqual(result["window_width_nm"], 100.0, places=9)

    def test_a_zero_transmittance_is_impossible(self):
        result = assess_optical_window(_window(min_transmittance=0.0))
        self.assertEqual(result["verdict"], WINDOW_TRANSMITTANCE_IMPOSSIBLE)

    def test_a_transmittance_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            assess_optical_window(_window(min_transmittance=1.4))

    def test_a_window_without_a_transmittance_rejected(self):
        entry = _window()
        del entry["min_transmittance"]
        with self.assertRaises(ValueError):
            assess_optical_window(entry)


class CoatingStackTests(unittest.TestCase):
    def test_a_two_layer_stack_is_usable(self):
        result = assess_coating_stack(_stack())
        self.assertEqual(result["verdict"], STACK_USABLE)
        self.assertEqual(result["layer_count"], 2)

    def test_a_stack_without_an_antireflection_layer_is_named(self):
        layers = [
            {"function": "ultraviolet-reject", "face": "front"},
            {"function": "conductive", "face": "front"},
        ]
        result = assess_coating_stack(layers)
        self.assertEqual(result["verdict"], STACK_FUNCTION_MISSING)
        self.assertEqual(result["absent_functions"], ["antireflection"])

    def test_a_conductive_layer_can_be_demanded_by_policy(self):
        policy = copy.deepcopy(DEFAULT_SCD_POLICY)
        policy["require_conductive_coating"] = True
        result = assess_coating_stack(_stack(), policy)
        self.assertEqual(result["absent_functions"], ["conductive"])

    def test_a_stack_thinner_than_the_policy_floor_is_named(self):
        layers = [
            {"function": "antireflection", "face": "front"},
            {"function": "ultraviolet-reject", "face": "front"},
        ]
        policy = copy.deepcopy(DEFAULT_SCD_POLICY)
        policy["min_coating_layers"] = 3
        self.assertEqual(assess_coating_stack(layers, policy)["verdict"], STACK_THIN)

    def test_an_unknown_face_rejected(self):
        with self.assertRaises(ValueError):
            assess_coating_stack([{"function": "antireflection", "face": "sideways"}])

    def test_an_empty_stack_rejected(self):
        with self.assertRaises(ValueError):
            assess_coating_stack([])

    def test_a_layer_without_a_function_rejected(self):
        with self.assertRaises(ValueError):
            assess_coating_stack([{"face": "front"}])


class DrawingSweepTests(unittest.TestCase):
    def test_a_full_drawing_is_releasable(self):
        result = assess_coverglass_scd(_drawing())
        self.assertEqual(result["verdict"], SCD_RELEASABLE)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["every_heading_stated"])

    def test_a_full_drawing_states_every_heading(self):
        result = assess_coverglass_scd(_drawing())
        self.assertAlmostEqual(result["stated_content_fraction"], 1.0, places=9)

    def test_a_missing_heading_blocks_release(self):
        content = _content()
        del content["approved_source"]
        result = assess_coverglass_scd(_drawing(content))
        self.assertEqual(result["verdict"], SCD_NOT_RELEASABLE)
        self.assertEqual(result["missing_content"], ["approved_source"])

    def test_the_stated_content_fraction_is_reported(self):
        content = _content()
        del content["approved_source"]
        result = assess_coverglass_scd(_drawing(content))
        self.assertAlmostEqual(
            result["stated_content_fraction"],
            (len(REQUIRED_SCD_CONTENT) - 1) / float(len(REQUIRED_SCD_CONTENT)),
            places=9,
        )

    def test_an_untoleranced_planar_dimension_blocks_release(self):
        content = _content(
            planar_dimensions={"coverglass_length_mm": {"nominal": 40.0}}
        )
        result = assess_coverglass_scd(_drawing(content))
        self.assertEqual(result["verdict"], SCD_NOT_RELEASABLE)
        self.assertEqual(result["unusable_dimensions"], ["coverglass_length_mm"])

    def test_a_single_dimension_mapping_is_accepted(self):
        content = _content(
            thickness={"nominal": 0.100, "minimum": 0.095, "maximum": 0.105}
        )
        result = assess_coverglass_scd(_drawing(content))
        self.assertIn("thickness", result["dimension_assessments"])

    def test_an_inverted_window_blocks_release(self):
        content = _content(optical_window=_window(cut_on_nm=1800.0, cut_off_nm=350.0))
        result = assess_coverglass_scd(_drawing(content))
        self.assertEqual(result["verdict"], SCD_NOT_RELEASABLE)
        self.assertEqual(result["optical_window"]["verdict"], WINDOW_INVERTED)

    def test_a_stack_without_the_ultraviolet_layer_blocks_release(self):
        content = _content(
            coating_stack=[{"function": "antireflection", "face": "front"}]
        )
        result = assess_coverglass_scd(_drawing(content))
        self.assertEqual(result["verdict"], SCD_NOT_RELEASABLE)
        self.assertEqual(result["coating_stack"]["verdict"], STACK_FUNCTION_MISSING)

    def test_a_missing_window_heading_leaves_no_window_assessment(self):
        content = _content()
        del content["optical_window"]
        result = assess_coverglass_scd(_drawing(content))
        self.assertIsNone(result["optical_window"])

    def test_findings_name_the_drawing(self):
        content = _content()
        del content["approved_source"]
        result = assess_coverglass_scd(_drawing(content))
        self.assertTrue(any("scd-cg-0041" in item for item in result["findings"]))

    def test_a_drawing_without_an_identifier_rejected(self):
        drawing = _drawing()
        del drawing["drawing_id"]
        with self.assertRaises(ValueError):
            assess_coverglass_scd(drawing)

    def test_an_empty_content_mapping_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_scd({"drawing_id": "scd-cg-0041", "content": {}})

    def test_non_mapping_drawing_rejected_by_the_sweep(self):
        with self.assertRaises(ValueError):
            assess_coverglass_scd([_content()])

    def test_a_relaxed_content_share_admits_a_thin_drawing(self):
        content = _content()
        del content["packaging_and_handling"]
        policy = copy.deepcopy(DEFAULT_SCD_POLICY)
        policy["min_content_fraction"] = 0.5
        result = assess_coverglass_scd(_drawing(content), policy)
        self.assertEqual(result["verdict"], SCD_NOT_RELEASABLE)
        self.assertNotIn(
            "against a required share", " ".join(result["findings"])
        )


if __name__ == "__main__":
    unittest.main()
