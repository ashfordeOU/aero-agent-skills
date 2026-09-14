"""Contract tests for the clause 7.5.12 bare-cell contact pull test."""

import math
import unittest

from e2008_bare_cell_pull_test_logic import (
    MAX_OFF_NORMAL_DEG,
    MIN_SAMPLE_CELLS,
    SITES,
    STRENGTH_TOLERANCE,
    assess_bare_cell_pull_test,
    bond_strength_mpa,
    conditioning_findings,
    evaluate_cell,
    evaluate_site,
    lot_statistics,
    normal_pull_force_n,
    sample_findings,
    sequence_findings,
    validate_conditioning,
)

AREAS = {"front-contact": 1.5, "rear-contact": 2.0}
MINIMUM_MPA = 2.0

GOOD_SEQUENCE = [
    {"step": "thermal cycling", "kind": "environmental"},
    {"step": "humidity soak", "kind": "environmental"},
    {"step": "contact pull", "kind": "mechanical"},
]
PULL_FIRST_SEQUENCE = [
    {"step": "contact pull", "kind": "mechanical"},
    {"step": "thermal cycling", "kind": "environmental"},
]


def site(name, force, angle=0.0):
    return {"site": name, "force_n": force, "off_normal_deg": angle}


def cell_record(name, front=6.0, rear=8.0, front_angle=0.0, rear_angle=0.0):
    return {
        "cell": name,
        "sites": [
            site("front-contact", front, front_angle),
            site("rear-contact", rear, rear_angle),
        ],
    }


class ConditioningTests(unittest.TestCase):
    def test_conditioning_is_returned_as_count_and_float(self):
        self.assertEqual(validate_conditioning(50, 96), (50, 96.0))

    def test_fractional_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_conditioning(50.5, 96.0)

    def test_boolean_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_conditioning(True, 96.0)

    def test_negative_soak_rejected(self):
        with self.assertRaises(ValueError):
            validate_conditioning(50, -1.0)

    def test_met_conditioning_gives_no_finding(self):
        self.assertEqual(conditioning_findings((50, 96.0), (50, 96.0)), [])

    def test_short_cycle_count_is_a_finding(self):
        findings = conditioning_findings((20, 96.0), (50, 96.0))
        self.assertEqual(len(findings), 1)
        self.assertIn("thermal cycles", findings[0])

    def test_short_soak_is_a_finding(self):
        findings = conditioning_findings((50, 24.0), (50, 96.0))
        self.assertEqual(len(findings), 1)
        self.assertIn("soaked", findings[0])

    def test_both_shortfalls_are_reported_separately(self):
        self.assertEqual(len(conditioning_findings((1, 1.0), (50, 96.0))), 2)


class SequenceTests(unittest.TestCase):
    def test_conditioning_before_the_pull_gives_no_finding(self):
        self.assertEqual(sequence_findings(GOOD_SEQUENCE), [])

    def test_pull_before_any_conditioning_is_a_finding(self):
        findings = sequence_findings(PULL_FIRST_SEQUENCE)
        self.assertTrue(any("as-built" in item for item in findings))

    def test_conditioning_after_the_pull_is_a_finding(self):
        findings = sequence_findings(PULL_FIRST_SEQUENCE)
        self.assertTrue(any("after the pull" in item for item in findings))

    def test_run_without_a_pull_is_a_finding(self):
        findings = sequence_findings(
            [{"step": "thermal cycling", "kind": "environmental"}]
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("no mechanical pull", findings[0])

    def test_empty_sequence_rejected(self):
        with self.assertRaises(ValueError):
            sequence_findings([])

    def test_unknown_step_kind_rejected(self):
        with self.assertRaises(ValueError):
            sequence_findings([{"step": "soak", "kind": "chemical"}])

    def test_step_without_a_kind_rejected(self):
        with self.assertRaises(ValueError):
            sequence_findings([{"step": "soak"}])


class ForceAndStrengthTests(unittest.TestCase):
    def test_normal_pull_at_zero_degrees_is_the_whole_force(self):
        self.assertAlmostEqual(normal_pull_force_n(6.0, 0.0), 6.0, places=9)

    def test_normal_pull_at_sixty_degrees_is_half_the_force(self):
        self.assertAlmostEqual(normal_pull_force_n(6.0, 60.0), 3.0, places=9)

    def test_normal_pull_falls_as_the_angle_grows(self):
        self.assertLess(
            normal_pull_force_n(6.0, 45.0), normal_pull_force_n(6.0, 10.0)
        )

    def test_pull_at_ninety_degrees_rejected(self):
        with self.assertRaises(ValueError):
            normal_pull_force_n(6.0, 90.0)

    def test_negative_angle_rejected(self):
        with self.assertRaises(ValueError):
            normal_pull_force_n(6.0, -5.0)

    def test_zero_force_rejected(self):
        with self.assertRaises(ValueError):
            normal_pull_force_n(0.0, 0.0)

    def test_strength_is_force_over_area(self):
        self.assertAlmostEqual(bond_strength_mpa(6.0, 1.5), 4.0, places=9)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            bond_strength_mpa(6.0, 0.0)

    def test_default_off_normal_allowance(self):
        self.assertAlmostEqual(MAX_OFF_NORMAL_DEG, 5.0, places=9)

    def test_strength_tolerance_is_small(self):
        self.assertAlmostEqual(STRENGTH_TOLERANCE, 1e-9, places=12)


class SiteTests(unittest.TestCase):
    def test_strong_site_gives_no_finding(self):
        result = evaluate_site(site("front-contact", 6.0), AREAS, MINIMUM_MPA)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["site_conformant"])
        self.assertAlmostEqual(result["strength_mpa"], 4.0, places=9)

    def test_strength_exactly_on_the_minimum_is_conformant(self):
        result = evaluate_site(site("front-contact", 3.0), AREAS, MINIMUM_MPA)
        self.assertAlmostEqual(result["strength_mpa"], MINIMUM_MPA, places=9)
        self.assertEqual(result["findings"], [])

    def test_weak_site_is_a_finding(self):
        result = evaluate_site(site("rear-contact", 2.0), AREAS, MINIMUM_MPA)
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("under", result["findings"][0])

    def test_angle_exactly_on_the_allowance_is_conformant(self):
        result = evaluate_site(
            site("front-contact", 6.0, MAX_OFF_NORMAL_DEG), AREAS, MINIMUM_MPA
        )
        self.assertEqual(result["findings"], [])

    def test_angle_over_the_allowance_is_a_finding(self):
        result = evaluate_site(
            site("front-contact", 6.0, 30.0), AREAS, MINIMUM_MPA
        )
        self.assertTrue(any("off normal" in item for item in result["findings"]))

    def test_off_normal_pull_lowers_the_reported_strength(self):
        upright = evaluate_site(site("front-contact", 6.0), AREAS, MINIMUM_MPA)
        tilted = evaluate_site(
            site("front-contact", 6.0, 60.0), AREAS, MINIMUM_MPA
        )
        self.assertAlmostEqual(
            tilted["strength_mpa"], upright["strength_mpa"] / 2.0, places=9
        )

    def test_unknown_site_name_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_site(site("edge-contact", 6.0), AREAS, MINIMUM_MPA)

    def test_site_without_a_declared_area_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_site(
                site("rear-contact", 6.0), {"front-contact": 1.5}, MINIMUM_MPA
            )

    def test_reading_without_a_force_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_site(
                {"site": "front-contact", "off_normal_deg": 0.0},
                AREAS,
                MINIMUM_MPA,
            )

    def test_two_sites_are_named(self):
        self.assertEqual(SITES, ("front-contact", "rear-contact"))


class CellTests(unittest.TestCase):
    def test_sound_cell_has_no_finding(self):
        result = evaluate_cell(cell_record("c-01"), AREAS, MINIMUM_MPA)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["cell_conformant"])

    def test_weakest_site_is_the_lower_strength(self):
        result = evaluate_cell(
            cell_record("c-02", front=6.0, rear=5.0), AREAS, MINIMUM_MPA
        )
        self.assertEqual(result["weakest_site"], "rear-contact")
        self.assertAlmostEqual(result["weakest_strength_mpa"], 2.5, places=9)

    def test_missing_rear_site_is_a_finding(self):
        record = {"cell": "c-03", "sites": [site("front-contact", 6.0)]}
        result = evaluate_cell(record, AREAS, MINIMUM_MPA)
        self.assertTrue(any("rear-contact" in item for item in result["findings"]))

    def test_repeated_site_rejected(self):
        record = {
            "cell": "c-04",
            "sites": [site("front-contact", 6.0), site("front-contact", 5.0)],
        }
        with self.assertRaises(ValueError):
            evaluate_cell(record, AREAS, MINIMUM_MPA)

    def test_cell_without_readings_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_cell({"cell": "c-05", "sites": []}, AREAS, MINIMUM_MPA)

    def test_unnamed_cell_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_cell({"cell": "  ", "sites": [site("front-contact", 6.0)]},
                          AREAS, MINIMUM_MPA)


class LotStatisticsTests(unittest.TestCase):
    def test_mean_of_a_lot(self):
        stats = lot_statistics([2.0, 4.0, 6.0])
        self.assertAlmostEqual(stats["mean_mpa"], 4.0, places=9)

    def test_spread_of_a_lot(self):
        stats = lot_statistics([2.0, 4.0, 6.0])
        self.assertAlmostEqual(stats["spread_mpa"], math.sqrt(4.0), places=9)

    def test_single_value_lot_has_no_spread(self):
        stats = lot_statistics([3.0])
        self.assertAlmostEqual(stats["spread_mpa"], 0.0, places=9)

    def test_lowest_and_highest_are_reported(self):
        stats = lot_statistics([2.0, 4.0, 6.0])
        self.assertAlmostEqual(stats["lowest_mpa"], 2.0, places=9)
        self.assertAlmostEqual(stats["highest_mpa"], 6.0, places=9)
        self.assertEqual(stats["count"], 3)

    def test_empty_lot_rejected(self):
        with self.assertRaises(ValueError):
            lot_statistics([])


class SampleTests(unittest.TestCase):
    def test_full_sample_gives_no_finding(self):
        self.assertEqual(
            sample_findings(["a", "b", "c"], ["a", "b", "c"]), []
        )

    def test_unpulled_planned_cell_is_a_finding(self):
        findings = sample_findings(["a", "b", "c"], ["a", "b"])
        self.assertTrue(any("never pulled" in item for item in findings))

    def test_unplanned_cell_is_a_finding(self):
        findings = sample_findings(["a", "b", "c"], ["a", "b", "c", "z"])
        self.assertTrue(any("not on the plan" in item for item in findings))

    def test_repeated_cell_is_a_finding(self):
        findings = sample_findings(["a", "b", "c"], ["a", "b", "c", "a"])
        self.assertTrue(any("ambiguous" in item for item in findings))

    def test_sample_under_the_floor_is_a_finding(self):
        findings = sample_findings(["a", "b"], ["a", "b"])
        self.assertTrue(any("a lot spread needs" in item for item in findings))

    def test_default_minimum_sample(self):
        self.assertEqual(MIN_SAMPLE_CELLS, 3)

    def test_empty_plan_rejected(self):
        with self.assertRaises(ValueError):
            sample_findings([], ["a"])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "planned_cells": ["c-01", "c-02", "c-03"],
            "cell_records": [
                cell_record("c-01"),
                cell_record("c-02", front=7.5, rear=9.0),
                cell_record("c-03", front=6.0, rear=10.0),
            ],
            "contact_areas_mm2": dict(AREAS),
            "minimum_strength_mpa": MINIMUM_MPA,
            "conditioning_received": (50, 96.0),
            "conditioning_required": (50, 96.0),
            "run_sequence": list(GOOD_SEQUENCE),
        }
        spec.update(overrides)
        return spec

    def test_conformant_lot_has_no_finding(self):
        result = assess_bare_cell_pull_test(self._spec())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["lot_conformant"])

    def test_every_cell_is_reported(self):
        result = assess_bare_cell_pull_test(self._spec())
        self.assertEqual(len(result["cells"]), 3)
        self.assertEqual(result["pulled_count"], 3)
        self.assertEqual(result["planned_count"], 3)

    def test_lot_statistics_are_reported(self):
        result = assess_bare_cell_pull_test(self._spec())
        self.assertEqual(result["statistics"]["count"], 3)
        self.assertAlmostEqual(result["statistics"]["lowest_mpa"], 4.0, places=9)

    def test_short_conditioning_fails_the_lot(self):
        result = assess_bare_cell_pull_test(
            self._spec(conditioning_received=(10, 96.0))
        )
        self.assertFalse(result["lot_conformant"])

    def test_pull_before_conditioning_fails_the_lot(self):
        result = assess_bare_cell_pull_test(
            self._spec(run_sequence=list(PULL_FIRST_SEQUENCE))
        )
        self.assertFalse(result["lot_conformant"])

    def test_weak_contact_fails_the_lot(self):
        spec = self._spec()
        spec["cell_records"][1]["sites"][0]["force_n"] = 1.0
        result = assess_bare_cell_pull_test(spec)
        self.assertFalse(result["lot_conformant"])
        self.assertTrue(any("c-02" in item for item in result["findings"]))

    def test_unpulled_planned_cell_fails_the_lot(self):
        spec = self._spec()
        spec["cell_records"] = spec["cell_records"][:2]
        result = assess_bare_cell_pull_test(spec)
        self.assertFalse(result["lot_conformant"])

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["contact_areas_mm2"]
        with self.assertRaises(ValueError):
            assess_bare_cell_pull_test(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_pull_test(["planned_cells"])

    def test_malformed_conditioning_pair_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_pull_test(self._spec(conditioning_received=(50,)))

    def test_empty_cell_records_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_pull_test(self._spec(cell_records=[]))


if __name__ == "__main__":
    unittest.main()
