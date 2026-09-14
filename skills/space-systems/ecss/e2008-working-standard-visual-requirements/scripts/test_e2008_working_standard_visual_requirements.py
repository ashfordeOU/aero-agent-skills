#!/usr/bin/env python3
"""Contract test for the working standard visual requirements (offline)."""

import copy
import unittest

from e2008_working_standard_visual_requirements_logic import (
    ACCEPT,
    BARE_CELL_STANDARD,
    CARRIER_RULES,
    CELL_RULES,
    COVERGLASSED_STANDARD,
    COVERGLASS_RULES,
    DEFAULT_VISUAL_CRITERIA,
    ENCAPSULATED_STANDARD,
    INTERCONNECTED_STANDARD,
    JOINT_RULES,
    REFER,
    REJECT,
    RULE_FAMILIES,
    STANDARD_FIT,
    STANDARD_REFERRED,
    STANDARD_UNFIT,
    applicable_rule_families,
    assess_standard_defect,
    assess_working_standard_visual,
    defect_rule_family,
    implied_current_bias_fraction,
    validate_standard_geometry,
    validate_visual_criteria,
)

GEOMETRY = {
    "length_mm": 20.0,
    "width_mm": 20.0,
    "inactive_border_mm": 0.5,
}
ACTIVE_AREA_MM2 = 19.0 * 19.0


def _defect(**overrides):
    defect = {
        "id": "D1",
        "category": "cell-surface-nick",
        "area_mm2": 0.5,
        "contact_clearance_mm": 0.8,
    }
    defect.update(overrides)
    return defect


def _standard(defects=None, **overrides):
    standard = {
        "standard_id": "WS-001",
        "construction": COVERGLASSED_STANDARD,
        "geometry": copy.deepcopy(GEOMETRY),
        "defects": copy.deepcopy(defects) if defects else [],
    }
    standard.update(overrides)
    return standard


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_visual_criteria(DEFAULT_VISUAL_CRITERIA), DEFAULT_VISUAL_CRITERIA
        )

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_visual_criteria("default")

    def test_missing_limit_rejected(self):
        broken = dict(DEFAULT_VISUAL_CRITERIA)
        del broken["max_crack_length_fraction"]
        with self.assertRaises(ValueError):
            validate_visual_criteria(broken)

    def test_area_fraction_above_one_rejected(self):
        broken = dict(DEFAULT_VISUAL_CRITERIA, max_defect_area_fraction=1.3)
        with self.assertRaises(ValueError):
            validate_visual_criteria(broken)

    def test_review_factor_below_one_rejected(self):
        broken = dict(DEFAULT_VISUAL_CRITERIA, defect_area_review_factor=0.6)
        with self.assertRaises(ValueError):
            validate_visual_criteria(broken)

    def test_non_integer_family_count_rejected(self):
        broken = dict(DEFAULT_VISUAL_CRITERIA, max_defects_per_family=2.5)
        with self.assertRaises(ValueError):
            validate_visual_criteria(broken)

    def test_one_defect_allowed_more_than_all_defects_rejected(self):
        broken = dict(
            DEFAULT_VISUAL_CRITERIA,
            max_defect_area_fraction=0.02,
            max_cumulative_obscuration_fraction=0.005,
        )
        with self.assertRaises(ValueError):
            validate_visual_criteria(broken)

    def test_referral_band_above_the_bias_limit_rejected(self):
        broken = dict(
            DEFAULT_VISUAL_CRITERIA,
            max_cumulative_obscuration_fraction=0.05,
            max_implied_current_bias_fraction=0.01,
        )
        with self.assertRaises(ValueError):
            validate_visual_criteria(broken)


class GeometryTests(unittest.TestCase):
    def test_geometry_derives_the_active_area(self):
        resolved = validate_standard_geometry(GEOMETRY)
        self.assertAlmostEqual(resolved["active_area_mm2"], ACTIVE_AREA_MM2, places=9)
        self.assertAlmostEqual(resolved["outline_area_mm2"], 400.0, places=9)
        self.assertAlmostEqual(resolved["shortest_edge_mm"], 20.0, places=9)

    def test_border_that_leaves_no_active_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_standard_geometry(dict(GEOMETRY, inactive_border_mm=10.0))

    def test_non_positive_dimension_rejected(self):
        with self.assertRaises(ValueError):
            validate_standard_geometry(dict(GEOMETRY, width_mm=0.0))

    def test_non_mapping_geometry_rejected(self):
        with self.assertRaises(ValueError):
            validate_standard_geometry(["20", "20"])


class ApplicabilityTests(unittest.TestCase):
    def test_bare_cell_standard_reaches_only_the_cell_rules(self):
        self.assertEqual(applicable_rule_families(BARE_CELL_STANDARD), (CELL_RULES,))

    def test_coverglassed_standard_adds_the_coverglass_rules(self):
        families = applicable_rule_families(COVERGLASSED_STANDARD)
        self.assertIn(COVERGLASS_RULES, families)
        self.assertNotIn(JOINT_RULES, families)

    def test_interconnected_standard_adds_the_joint_rules(self):
        families = applicable_rule_families(INTERCONNECTED_STANDARD)
        self.assertIn(JOINT_RULES, families)
        self.assertNotIn(CARRIER_RULES, families)

    def test_encapsulated_standard_reaches_every_family(self):
        self.assertEqual(
            set(applicable_rule_families(ENCAPSULATED_STANDARD)), set(RULE_FAMILIES)
        )

    def test_unknown_construction_rejected(self):
        with self.assertRaises(ValueError):
            applicable_rule_families("reference-diode-standard")

    def test_defect_category_maps_to_its_family(self):
        self.assertEqual(defect_rule_family("coverglass-chip"), COVERGLASS_RULES)
        self.assertEqual(defect_rule_family("wiring-defect"), CARRIER_RULES)

    def test_unknown_defect_category_rejected(self):
        with self.assertRaises(ValueError):
            defect_rule_family("paint-run")


class DefectTests(unittest.TestCase):
    def test_small_defect_accepted(self):
        result = assess_standard_defect(
            _defect(), GEOMETRY, COVERGLASSED_STANDARD
        )
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertTrue(result["governed"])
        self.assertTrue(result["obscures_active_area"])

    def test_defect_exactly_on_the_area_allowance_accepted(self):
        area = ACTIVE_AREA_MM2 * DEFAULT_VISUAL_CRITERIA["max_defect_area_fraction"]
        result = assess_standard_defect(
            _defect(area_mm2=area), GEOMETRY, COVERGLASSED_STANDARD
        )
        self.assertAlmostEqual(
            result["area_fraction_of_active"],
            DEFAULT_VISUAL_CRITERIA["max_defect_area_fraction"],
            places=9,
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_defect_past_the_allowance_referred(self):
        result = assess_standard_defect(
            _defect(area_mm2=1.0), GEOMETRY, COVERGLASSED_STANDARD
        )
        self.assertEqual(result["disposition"], REFER)

    def test_defect_past_the_review_limit_rejected(self):
        result = assess_standard_defect(
            _defect(area_mm2=3.0), GEOMETRY, COVERGLASSED_STANDARD
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_defect_from_a_family_the_build_does_not_carry_is_referred(self):
        result = assess_standard_defect(
            _defect(category="coverglass-chip"), GEOMETRY, BARE_CELL_STANDARD
        )
        self.assertEqual(result["disposition"], REFER)
        self.assertFalse(result["governed"])

    def test_ungoverned_observation_is_not_counted_as_obscuration(self):
        result = assess_standard_defect(
            _defect(category="coverglass-chip", area_mm2=3.0),
            GEOMETRY,
            BARE_CELL_STANDARD,
        )
        self.assertAlmostEqual(result["obscured_area_mm2"], 0.0, places=12)
        self.assertEqual(result["disposition"], REFER)

    def test_joint_finding_does_not_obscure_collecting_area(self):
        result = assess_standard_defect(
            _defect(category="interconnect-weld-defect", area_mm2=0.4),
            GEOMETRY,
            INTERCONNECTED_STANDARD,
        )
        self.assertFalse(result["obscures_active_area"])
        self.assertAlmostEqual(result["obscured_area_mm2"], 0.0, places=12)

    def test_short_crack_accepted(self):
        result = assess_standard_defect(
            _defect(category="cell-crack", area_mm2=0.2, length_mm=0.8),
            GEOMETRY,
            COVERGLASSED_STANDARD,
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_crack_past_the_edge_share_referred(self):
        result = assess_standard_defect(
            _defect(category="cell-crack", area_mm2=0.2, length_mm=1.5),
            GEOMETRY,
            COVERGLASSED_STANDARD,
        )
        self.assertEqual(result["disposition"], REFER)

    def test_long_crack_rejected(self):
        result = assess_standard_defect(
            _defect(category="cell-crack", area_mm2=0.2, length_mm=6.0),
            GEOMETRY,
            COVERGLASSED_STANDARD,
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_crack_without_a_length_rejected(self):
        with self.assertRaises(ValueError):
            assess_standard_defect(
                _defect(category="cell-crack", area_mm2=0.2),
                GEOMETRY,
                COVERGLASSED_STANDARD,
            )

    def test_defect_inside_the_contact_clearance_rejected(self):
        result = assess_standard_defect(
            _defect(contact_clearance_mm=0.1), GEOMETRY, COVERGLASSED_STANDARD
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_clearance_exactly_on_the_minimum_accepted(self):
        result = assess_standard_defect(
            _defect(
                contact_clearance_mm=DEFAULT_VISUAL_CRITERIA[
                    "min_contact_clearance_mm"
                ]
            ),
            GEOMETRY,
            COVERGLASSED_STANDARD,
        )
        self.assertAlmostEqual(
            result["contact_clearance_mm"],
            DEFAULT_VISUAL_CRITERIA["min_contact_clearance_mm"],
            places=9,
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_defect_larger_than_the_device_rejected(self):
        with self.assertRaises(ValueError):
            assess_standard_defect(
                _defect(area_mm2=900.0), GEOMETRY, COVERGLASSED_STANDARD
            )

    def test_zero_area_defect_rejected(self):
        with self.assertRaises(ValueError):
            assess_standard_defect(
                _defect(area_mm2=0.0), GEOMETRY, COVERGLASSED_STANDARD
            )

    def test_non_mapping_defect_rejected(self):
        with self.assertRaises(ValueError):
            assess_standard_defect("a nick", GEOMETRY, COVERGLASSED_STANDARD)


class BiasTests(unittest.TestCase):
    def test_bias_is_the_obscured_share_of_the_active_area(self):
        self.assertAlmostEqual(
            implied_current_bias_fraction(3.61, 361.0), 0.01, places=9
        )

    def test_no_obscuration_implies_no_bias(self):
        self.assertAlmostEqual(implied_current_bias_fraction(0.0, 361.0), 0.0, places=12)

    def test_obscured_area_over_the_active_area_rejected(self):
        with self.assertRaises(ValueError):
            implied_current_bias_fraction(400.0, 361.0)

    def test_negative_obscured_area_rejected(self):
        with self.assertRaises(ValueError):
            implied_current_bias_fraction(-1.0, 361.0)


class RollupTests(unittest.TestCase):
    def test_clean_standard_is_fit_for_transfer(self):
        result = assess_working_standard_visual(_standard([_defect()]))
        self.assertEqual(result["verdict"], STANDARD_FIT)
        self.assertEqual(result["not_accepted_ids"], [])
        self.assertEqual(result["findings"], [])

    def test_accumulation_refers_a_device_whose_defects_all_passed(self):
        defects = [
            _defect(id="D%d" % i, area_mm2=0.7) for i in range(1, 4)
        ]
        result = assess_working_standard_visual(_standard(defects))
        for entry in result["defects"]:
            self.assertEqual(entry["disposition"], ACCEPT)
        self.assertEqual(result["verdict"], STANDARD_REFERRED)
        self.assertTrue(
            any("active face" in finding for finding in result["findings"])
        )

    def test_accumulation_past_the_bias_limit_is_unfit(self):
        defects = [
            _defect(id="C%d" % i, category="cell-surface-nick", area_mm2=0.72)
            for i in range(1, 4)
        ] + [
            _defect(id="G%d" % i, category="coverglass-chip", area_mm2=0.72)
            for i in range(1, 4)
        ]
        result = assess_working_standard_visual(_standard(defects))
        self.assertEqual(result["verdict"], STANDARD_UNFIT)
        self.assertGreater(result["implied_current_bias_fraction"], 0.01)

    def test_too_many_findings_in_one_family_refers_the_device(self):
        defects = [
            _defect(id="D%d" % i, area_mm2=0.3) for i in range(1, 5)
        ]
        result = assess_working_standard_visual(_standard(defects))
        self.assertEqual(result["findings_per_family"][CELL_RULES], 4)
        self.assertEqual(result["verdict"], STANDARD_REFERRED)

    def test_uninspected_applicable_family_refers_the_device(self):
        standard = _standard([_defect()], inspected_families=[CELL_RULES])
        result = assess_working_standard_visual(standard)
        self.assertEqual(result["uninspected_families"], [COVERGLASS_RULES])
        self.assertEqual(result["verdict"], STANDARD_REFERRED)

    def test_inspected_families_default_to_the_applicable_set(self):
        result = assess_working_standard_visual(_standard([_defect()]))
        self.assertEqual(result["uninspected_families"], [])
        self.assertEqual(
            result["inspected_families"], list(result["applicable_families"])
        )

    def test_unknown_inspected_family_rejected(self):
        standard = _standard([_defect()], inspected_families=["paint-rules"])
        with self.assertRaises(ValueError):
            assess_working_standard_visual(standard)

    def test_ungoverned_observations_are_named_in_the_rollup(self):
        standard = _standard(
            [_defect(id="X1", category="wiring-defect", area_mm2=0.2)],
            construction=BARE_CELL_STANDARD,
        )
        result = assess_working_standard_visual(standard)
        self.assertEqual(result["ungoverned_observation_ids"], ["X1"])
        self.assertEqual(result["verdict"], STANDARD_REFERRED)

    def test_worst_defect_sets_the_verdict(self):
        result = assess_working_standard_visual(
            _standard([_defect(id="A"), _defect(id="B", area_mm2=3.0)])
        )
        self.assertEqual(result["verdict"], STANDARD_UNFIT)
        self.assertEqual(result["not_accepted_ids"], ["B"])

    def test_duplicate_defect_ids_rejected(self):
        with self.assertRaises(ValueError):
            assess_working_standard_visual(
                _standard([_defect(id="D"), _defect(id="D")])
            )

    def test_standard_without_an_id_rejected(self):
        standard = _standard([_defect()])
        standard["standard_id"] = "   "
        with self.assertRaises(ValueError):
            assess_working_standard_visual(standard)

    def test_non_list_defect_collection_rejected(self):
        standard = _standard()
        standard["defects"] = _defect()
        with self.assertRaises(ValueError):
            assess_working_standard_visual(standard)

    def test_input_is_not_mutated_by_the_screen(self):
        standard = _standard([_defect(), _defect(id="D2", category="coverglass-chip")])
        before = copy.deepcopy(standard)
        assess_working_standard_visual(standard)
        self.assertEqual(standard, before)


if __name__ == "__main__":
    unittest.main()
