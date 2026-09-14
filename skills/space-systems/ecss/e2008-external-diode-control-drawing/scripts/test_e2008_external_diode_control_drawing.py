#!/usr/bin/env python3
"""Contract test for the external protection diode control drawing, Annex E (offline)."""

import copy
import unittest

from e2008_external_diode_control_drawing_logic import (
    BLOCKING_ADEQUATE,
    BLOCKING_INVERTED,
    BLOCKING_MARGIN_THIN,
    DEFAULT_DIODE_SCD_POLICY,
    DERATING_EXCEEDED,
    DERATING_MET,
    DIODE_SCD_NOT_RELEASABLE,
    DIODE_SCD_RELEASABLE,
    ESD_CATEGORIES,
    REQUIRED_DIODE_SCD_CONTENT,
    THERMAL_MARGIN_EXCEEDED,
    THERMAL_MARGIN_MET,
    assess_external_diode_scd,
    assess_forward_current_derating,
    assess_junction_thermal_margin,
    assess_reverse_blocking,
    audit_diode_scd_content,
    categorize_esd_sensitivity,
    esd_categories,
    junction_temperature,
    required_diode_scd_content,
    validate_diode_scd_policy,
)


def _reverse(**overrides):
    entry = {
        "reverse_breakdown_v": 200.0,
        "reverse_working_v": 80.0,
        "reverse_leakage_a": 1.0e-6,
    }
    entry.update(overrides)
    return entry


def _current(**overrides):
    entry = {
        "rated_forward_a": 3.0,
        "applied_forward_a": 1.2,
        "derating_factor": 0.5,
    }
    entry.update(overrides)
    return entry


def _forward(**overrides):
    entry = {"forward_drop_v": 0.5, "forward_current_a": 2.0}
    entry.update(overrides)
    return entry


def _thermal(**overrides):
    entry = {
        "junction_to_case_k_per_w": 20.0,
        "case_temperature_c": 70.0,
        "rated_junction_max_c": 125.0,
    }
    entry.update(overrides)
    return entry


def _content(**overrides):
    content = {
        "drawing_identifier": "scd-dio-0207",
        "issue_and_date": "issue B, 2026-05-02",
        "component_description": "external protection diode for a solar array string",
        "diode_construction": "silicon die, hermetic package, welded terminals",
        "forward_characteristics": _forward(),
        "reverse_characteristics": _reverse(),
        "current_rating": _current(),
        "thermal_characteristics": _thermal(),
        "terminal_and_mounting": "welded interconnect tabs, bonded to the substrate",
        "esd_sensitivity": "class-1b",
        "radiation_requirement": "leakage budget held after the mission fluence",
        "marking_and_traceability": "lot and date code on the package body",
        "packaging_and_handling": "electrostatic-safe trays, dry storage",
        "screening_and_acceptance": "lot screening, burn-in and electrical acceptance",
        "approved_source": "named die source and package house on the approved list",
    }
    content.update(overrides)
    return content


def _drawing(content=None, **overrides):
    drawing = {
        "drawing_id": "scd-dio-0207",
        "content": content if content is not None else _content(),
    }
    drawing.update(overrides)
    return drawing


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_diode_scd_policy(DEFAULT_DIODE_SCD_POLICY),
            DEFAULT_DIODE_SCD_POLICY,
        )

    def test_default_policy_demands_every_heading(self):
        self.assertAlmostEqual(
            DEFAULT_DIODE_SCD_POLICY["min_content_fraction"], 1.0, places=9
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_scd_policy("block everything")

    def test_a_blocking_margin_below_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_DIODE_SCD_POLICY)
        broken["min_reverse_blocking_margin"] = 0.5
        with self.assertRaises(ValueError):
            validate_diode_scd_policy(broken)

    def test_a_negative_temperature_margin_rejected(self):
        broken = copy.deepcopy(DEFAULT_DIODE_SCD_POLICY)
        broken["junction_temperature_margin_k"] = -5.0
        with self.assertRaises(ValueError):
            validate_diode_scd_policy(broken)

    def test_a_non_boolean_esd_switch_rejected(self):
        broken = copy.deepcopy(DEFAULT_DIODE_SCD_POLICY)
        broken["require_esd_category"] = "yes"
        with self.assertRaises(ValueError):
            validate_diode_scd_policy(broken)


class RequiredContentTests(unittest.TestCase):
    def test_content_set_is_returned_as_a_tuple_copy(self):
        headings = required_diode_scd_content()
        self.assertEqual(headings, REQUIRED_DIODE_SCD_CONTENT)
        self.assertIsInstance(headings, tuple)

    def test_content_set_carries_thermal_and_screening(self):
        headings = required_diode_scd_content()
        self.assertIn("thermal_characteristics", headings)
        self.assertIn("screening_and_acceptance", headings)

    def test_esd_categories_are_returned_as_a_tuple_copy(self):
        categories = esd_categories()
        self.assertEqual(categories, ESD_CATEGORIES)
        self.assertIsInstance(categories, tuple)


class ContentAuditTests(unittest.TestCase):
    def test_a_full_drawing_is_missing_nothing(self):
        self.assertEqual(audit_diode_scd_content(_drawing()), [])

    def test_a_dropped_heading_is_named(self):
        content = _content()
        del content["radiation_requirement"]
        self.assertEqual(
            audit_diode_scd_content(_drawing(content)), ["radiation_requirement"]
        )

    def test_a_blank_heading_counts_as_absent(self):
        self.assertEqual(
            audit_diode_scd_content(_drawing(_content(esd_sensitivity="  "))),
            ["esd_sensitivity"],
        )

    def test_an_empty_thermal_mapping_counts_as_absent(self):
        self.assertEqual(
            audit_diode_scd_content(_drawing(_content(thermal_characteristics={}))),
            ["thermal_characteristics"],
        )

    def test_non_mapping_drawing_rejected(self):
        with self.assertRaises(ValueError):
            audit_diode_scd_content("a drawing")

    def test_non_mapping_content_rejected(self):
        with self.assertRaises(ValueError):
            audit_diode_scd_content({"drawing_id": "scd-dio-0207", "content": 7})


class ReverseBlockingTests(unittest.TestCase):
    def test_a_well_blocked_diode_is_adequate(self):
        result = assess_reverse_blocking(_reverse())
        self.assertEqual(result["verdict"], BLOCKING_ADEQUATE)
        self.assertTrue(result["adequate"])

    def test_the_blocking_margin_is_reported(self):
        result = assess_reverse_blocking(_reverse())
        self.assertAlmostEqual(result["blocking_margin"], 2.5, places=9)

    def test_a_margin_exactly_on_the_floor_is_accepted(self):
        result = assess_reverse_blocking(
            _reverse(reverse_breakdown_v=200.0, reverse_working_v=100.0)
        )
        self.assertEqual(result["verdict"], BLOCKING_ADEQUATE)
        self.assertAlmostEqual(result["blocking_margin"], 2.0, places=9)

    def test_a_thin_margin_is_named(self):
        result = assess_reverse_blocking(
            _reverse(reverse_breakdown_v=100.0, reverse_working_v=80.0)
        )
        self.assertEqual(result["verdict"], BLOCKING_MARGIN_THIN)

    def test_a_working_voltage_above_the_breakdown_is_inverted(self):
        result = assess_reverse_blocking(
            _reverse(reverse_breakdown_v=60.0, reverse_working_v=80.0)
        )
        self.assertEqual(result["verdict"], BLOCKING_INVERTED)

    def test_a_working_voltage_equal_to_the_breakdown_is_inverted(self):
        result = assess_reverse_blocking(
            _reverse(reverse_breakdown_v=80.0, reverse_working_v=80.0)
        )
        self.assertEqual(result["verdict"], BLOCKING_INVERTED)

    def test_a_negative_leakage_rejected(self):
        with self.assertRaises(ValueError):
            assess_reverse_blocking(_reverse(reverse_leakage_a=-1.0e-6))

    def test_non_mapping_reverse_entry_rejected(self):
        with self.assertRaises(ValueError):
            assess_reverse_blocking("200 V")


class DeratingTests(unittest.TestCase):
    def test_a_derated_current_is_met(self):
        result = assess_forward_current_derating(_current())
        self.assertEqual(result["verdict"], DERATING_MET)
        self.assertTrue(result["met"])

    def test_the_derated_allowance_is_reported(self):
        result = assess_forward_current_derating(_current())
        self.assertAlmostEqual(result["derated_allowance_a"], 1.5, places=9)

    def test_a_current_exactly_on_the_allowance_is_met(self):
        result = assess_forward_current_derating(_current(applied_forward_a=1.5))
        self.assertEqual(result["verdict"], DERATING_MET)
        self.assertAlmostEqual(result["utilisation"], 1.0, places=9)

    def test_a_current_above_the_allowance_is_exceeded(self):
        result = assess_forward_current_derating(_current(applied_forward_a=2.4))
        self.assertEqual(result["verdict"], DERATING_EXCEEDED)

    def test_a_zero_derating_factor_rejected(self):
        with self.assertRaises(ValueError):
            assess_forward_current_derating(_current(derating_factor=0.0))

    def test_a_derating_factor_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            assess_forward_current_derating(_current(derating_factor=1.4))

    def test_a_negative_applied_current_rejected(self):
        with self.assertRaises(ValueError):
            assess_forward_current_derating(_current(applied_forward_a=-0.1))

    def test_non_mapping_current_entry_rejected(self):
        with self.assertRaises(ValueError):
            assess_forward_current_derating("3 A")


class JunctionThermalTests(unittest.TestCase):
    def test_the_dissipation_is_the_drop_times_the_current(self):
        result = junction_temperature(_forward(), _thermal())
        self.assertAlmostEqual(result["dissipation_w"], 1.0, places=9)

    def test_the_junction_temperature_follows_the_thermal_path(self):
        result = junction_temperature(_forward(), _thermal())
        self.assertAlmostEqual(result["junction_temperature_c"], 90.0, places=9)

    def test_a_cool_diode_holds_its_margin(self):
        result = assess_junction_thermal_margin(_forward(), _thermal())
        self.assertEqual(result["verdict"], THERMAL_MARGIN_MET)
        self.assertAlmostEqual(result["headroom_k"], 25.0, places=9)

    def test_a_junction_exactly_on_the_limit_is_accepted(self):
        thermal = _thermal(junction_to_case_k_per_w=30.0, case_temperature_c=85.0)
        result = assess_junction_thermal_margin(_forward(), thermal)
        self.assertEqual(result["verdict"], THERMAL_MARGIN_MET)
        self.assertAlmostEqual(result["junction_temperature_c"], 115.0, places=9)

    def test_a_hot_junction_is_named(self):
        thermal = _thermal(case_temperature_c=110.0)
        result = assess_junction_thermal_margin(_forward(), thermal)
        self.assertEqual(result["verdict"], THERMAL_MARGIN_EXCEEDED)

    def test_a_zero_current_dissipates_nothing(self):
        result = junction_temperature(_forward(forward_current_a=0.0), _thermal())
        self.assertAlmostEqual(result["temperature_rise_k"], 0.0, places=9)

    def test_a_negative_thermal_resistance_rejected(self):
        with self.assertRaises(ValueError):
            junction_temperature(
                _forward(), _thermal(junction_to_case_k_per_w=-2.0)
            )

    def test_a_non_positive_forward_drop_rejected(self):
        with self.assertRaises(ValueError):
            junction_temperature(_forward(forward_drop_v=0.0), _thermal())

    def test_non_mapping_thermal_entry_rejected(self):
        with self.assertRaises(ValueError):
            junction_temperature(_forward(), "125 C")


class EsdCategoryTests(unittest.TestCase):
    def test_a_stated_category_reads_back(self):
        self.assertEqual(categorize_esd_sensitivity("class-1b"), "class-1b")

    def test_a_category_is_read_case_insensitively(self):
        self.assertEqual(categorize_esd_sensitivity("CLASS-2"), "class-2")

    def test_an_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            categorize_esd_sensitivity("quite-sensitive")

    def test_a_blank_category_rejected(self):
        with self.assertRaises(ValueError):
            categorize_esd_sensitivity("   ")


class DrawingSweepTests(unittest.TestCase):
    def test_a_full_drawing_is_releasable(self):
        result = assess_external_diode_scd(_drawing())
        self.assertEqual(result["verdict"], DIODE_SCD_RELEASABLE)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["every_heading_stated"])

    def test_a_full_drawing_states_every_heading(self):
        result = assess_external_diode_scd(_drawing())
        self.assertAlmostEqual(result["stated_content_fraction"], 1.0, places=9)

    def test_a_missing_heading_blocks_release(self):
        content = _content()
        del content["approved_source"]
        result = assess_external_diode_scd(_drawing(content))
        self.assertEqual(result["verdict"], DIODE_SCD_NOT_RELEASABLE)
        self.assertEqual(result["missing_content"], ["approved_source"])

    def test_the_stated_content_fraction_is_reported(self):
        content = _content()
        del content["approved_source"]
        result = assess_external_diode_scd(_drawing(content))
        self.assertAlmostEqual(
            result["stated_content_fraction"],
            (len(REQUIRED_DIODE_SCD_CONTENT) - 1)
            / float(len(REQUIRED_DIODE_SCD_CONTENT)),
            places=9,
        )

    def test_a_thin_blocking_margin_blocks_release(self):
        content = _content(
            reverse_characteristics=_reverse(
                reverse_breakdown_v=100.0, reverse_working_v=80.0
            )
        )
        result = assess_external_diode_scd(_drawing(content))
        self.assertEqual(result["verdict"], DIODE_SCD_NOT_RELEASABLE)
        self.assertEqual(result["reverse_blocking"]["verdict"], BLOCKING_MARGIN_THIN)

    def test_an_exceeded_derating_blocks_release(self):
        content = _content(current_rating=_current(applied_forward_a=2.4))
        result = assess_external_diode_scd(_drawing(content))
        self.assertEqual(
            result["forward_current_derating"]["verdict"], DERATING_EXCEEDED
        )

    def test_a_hot_junction_blocks_release(self):
        content = _content(thermal_characteristics=_thermal(case_temperature_c=110.0))
        result = assess_external_diode_scd(_drawing(content))
        self.assertEqual(
            result["junction_thermal_margin"]["verdict"], THERMAL_MARGIN_EXCEEDED
        )

    def test_the_esd_category_is_carried_through(self):
        result = assess_external_diode_scd(_drawing())
        self.assertEqual(result["esd_category"], "class-1b")

    def test_a_missing_thermal_heading_leaves_no_thermal_assessment(self):
        content = _content()
        del content["thermal_characteristics"]
        result = assess_external_diode_scd(_drawing(content))
        self.assertIsNone(result["junction_thermal_margin"])

    def test_findings_name_the_drawing(self):
        content = _content(current_rating=_current(applied_forward_a=2.4))
        result = assess_external_diode_scd(_drawing(content))
        self.assertTrue(any("scd-dio-0207" in item for item in result["findings"]))

    def test_a_drawing_without_an_identifier_rejected(self):
        drawing = _drawing()
        del drawing["drawing_id"]
        with self.assertRaises(ValueError):
            assess_external_diode_scd(drawing)

    def test_an_empty_content_mapping_rejected(self):
        with self.assertRaises(ValueError):
            assess_external_diode_scd({"drawing_id": "scd-dio-0207", "content": {}})

    def test_non_mapping_drawing_rejected_by_the_sweep(self):
        with self.assertRaises(ValueError):
            assess_external_diode_scd([_content()])

    def test_the_esd_category_is_skipped_when_policy_drops_it(self):
        policy = copy.deepcopy(DEFAULT_DIODE_SCD_POLICY)
        policy["require_esd_category"] = False
        result = assess_external_diode_scd(_drawing(), policy)
        self.assertIsNone(result["esd_category"])


if __name__ == "__main__":
    unittest.main()
