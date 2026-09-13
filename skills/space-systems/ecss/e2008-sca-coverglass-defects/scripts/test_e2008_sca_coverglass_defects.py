#!/usr/bin/env python3
"""Contract test for the coverglass complete-coverage screen (offline)."""

import copy
import unittest

from e2008_sca_coverglass_defects_logic import (
    ACCEPT,
    COVERAGE_DISPOSITIONS,
    COVERGLASS_EDGES,
    DEFAULT_COVERAGE_CRITERIA,
    INSPECTION_INCOMPLETE,
    REFER,
    REJECT,
    REWORK,
    assess_coverglass,
    assess_edge_chip,
    covered_area_mm2,
    edge_overhangs_mm,
    glass_is_undersized,
    inspect_assembly_coverage,
    validate_coverage_criteria,
)

CELL = {"length_mm": 40.0, "width_mm": 40.0}
GLASS = {"length_mm": 41.0, "width_mm": 41.0}
SQUARE_OVERHANGS = edge_overhangs_mm(CELL, GLASS)


def _record(chips=None, **overrides):
    record = {
        "coverglass_id": "CG-01",
        "cell": dict(CELL),
        "coverglass": dict(GLASS),
        "offset_x_mm": 0.0,
        "offset_y_mm": 0.0,
        "edge_chips": copy.deepcopy(chips) if chips else [],
    }
    record.update(overrides)
    return record


def _chip(**overrides):
    chip = {
        "id": "G1",
        "edge": "x-minus",
        "ingress_mm": 0.2,
        "length_mm": 5.0,
    }
    chip.update(overrides)
    return chip


def _assembly(records, declared=None, **overrides):
    assembly = {
        "assembly_id": "SCA-ASSY-01",
        "declared_coverglass_count": (
            declared if declared is not None else len(records)
        ),
        "coverglasses": records,
    }
    assembly.update(overrides)
    return assembly


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_coverage_criteria(DEFAULT_COVERAGE_CRITERIA),
            DEFAULT_COVERAGE_CRITERIA,
        )

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_coverage_criteria("default")

    def test_missing_minimum_overhang_rejected(self):
        broken = copy.deepcopy(DEFAULT_COVERAGE_CRITERIA)
        del broken["min_overhang_mm"]
        with self.assertRaises(ValueError):
            validate_coverage_criteria(broken)

    def test_tolerance_wider_than_the_margin_rejected(self):
        broken = copy.deepcopy(DEFAULT_COVERAGE_CRITERIA)
        broken["placement_tolerance_mm"] = 0.5
        with self.assertRaises(ValueError):
            validate_coverage_criteria(broken)

    def test_exposed_fraction_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_COVERAGE_CRITERIA)
        broken["max_exposed_area_fraction"] = 1.5
        with self.assertRaises(ValueError):
            validate_coverage_criteria(broken)

    def test_non_integer_chip_allowance_rejected(self):
        broken = copy.deepcopy(DEFAULT_COVERAGE_CRITERIA)
        broken["max_chips_per_coverglass"] = 1.5
        with self.assertRaises(ValueError):
            validate_coverage_criteria(broken)


class GeometryTests(unittest.TestCase):
    def test_a_square_placement_leaves_the_same_overhang_all_round(self):
        for edge in COVERGLASS_EDGES:
            self.assertAlmostEqual(SQUARE_OVERHANGS[edge], 0.5, places=12)

    def test_an_offset_moves_overhang_from_one_edge_to_the_other(self):
        overhangs = edge_overhangs_mm(CELL, GLASS, offset_x_mm=0.3)
        self.assertAlmostEqual(overhangs["x-plus"], 0.8, places=12)
        self.assertAlmostEqual(overhangs["x-minus"], 0.2, places=12)
        self.assertAlmostEqual(overhangs["y-plus"], 0.5, places=12)

    def test_an_offset_can_drive_an_overhang_negative(self):
        overhangs = edge_overhangs_mm(CELL, GLASS, offset_x_mm=0.8)
        self.assertAlmostEqual(overhangs["x-minus"], -0.3, places=12)

    def test_a_square_placement_covers_the_whole_cell(self):
        covered = covered_area_mm2(CELL, SQUARE_OVERHANGS)
        self.assertAlmostEqual(covered, 1600.0, places=9)

    def test_a_short_edge_takes_a_strip_off_the_covered_area(self):
        overhangs = edge_overhangs_mm(CELL, GLASS, offset_x_mm=0.8)
        self.assertAlmostEqual(covered_area_mm2(CELL, overhangs), 1588.0, places=9)

    def test_a_glass_shifted_clear_of_the_cell_covers_nothing(self):
        overhangs = edge_overhangs_mm(CELL, GLASS, offset_x_mm=45.0)
        self.assertAlmostEqual(covered_area_mm2(CELL, overhangs), 0.0, places=9)

    def test_an_exactly_sized_glass_is_not_undersized(self):
        self.assertEqual(glass_is_undersized(CELL, dict(CELL)), [])

    def test_a_glass_short_on_one_axis_is_named(self):
        self.assertEqual(
            glass_is_undersized(CELL, {"length_mm": 39.0, "width_mm": 41.0}), ["x"]
        )

    def test_a_glass_short_on_both_axes_names_both(self):
        self.assertEqual(
            glass_is_undersized(CELL, {"length_mm": 39.0, "width_mm": 39.0}),
            ["x", "y"],
        )

    def test_non_numeric_dimension_rejected(self):
        with self.assertRaises(ValueError):
            edge_overhangs_mm(CELL, {"length_mm": "41", "width_mm": 41.0})

    def test_non_numeric_offset_rejected(self):
        with self.assertRaises(ValueError):
            edge_overhangs_mm(CELL, GLASS, offset_x_mm="0.3")


class EdgeChipTests(unittest.TestCase):
    def test_a_chip_inside_the_overhang_accepts(self):
        result = assess_edge_chip(_chip(), SQUARE_OVERHANGS, GLASS)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertFalse(result["exposes_bare_cell"])
        self.assertAlmostEqual(result["remaining_overhang_mm"], 0.3, places=12)

    def test_a_chip_leaving_exactly_the_minimum_overhang_accepts(self):
        result = assess_edge_chip(_chip(ingress_mm=0.3), SQUARE_OVERHANGS, GLASS)
        self.assertAlmostEqual(
            result["remaining_overhang_mm"],
            DEFAULT_COVERAGE_CRITERIA["min_overhang_mm"],
            places=12,
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_a_chip_eating_the_margin_refers(self):
        result = assess_edge_chip(_chip(ingress_mm=0.4), SQUARE_OVERHANGS, GLASS)
        self.assertEqual(result["disposition"], REFER)
        self.assertFalse(result["exposes_bare_cell"])

    def test_a_chip_past_the_cell_edge_exposes_bare_cell(self):
        result = assess_edge_chip(_chip(ingress_mm=0.7), SQUARE_OVERHANGS, GLASS)
        self.assertEqual(result["disposition"], REWORK)
        self.assertTrue(result["exposes_bare_cell"])
        self.assertAlmostEqual(result["exposed_area_mm2"], 1.0, places=9)

    def test_a_chip_on_an_already_short_edge_only_adds_its_own_strip(self):
        overhangs = edge_overhangs_mm(CELL, GLASS, offset_x_mm=0.8)
        result = assess_edge_chip(_chip(ingress_mm=0.2), overhangs, GLASS)
        self.assertAlmostEqual(result["exposed_area_mm2"], 1.0, places=9)

    def test_a_chip_longer_than_its_glass_edge_rejected(self):
        with self.assertRaises(ValueError):
            assess_edge_chip(_chip(length_mm=60.0), SQUARE_OVERHANGS, GLASS)

    def test_an_unknown_chip_edge_rejected(self):
        with self.assertRaises(ValueError):
            assess_edge_chip(_chip(edge="north"), SQUARE_OVERHANGS, GLASS)

    def test_a_zero_ingress_chip_rejected(self):
        with self.assertRaises(ValueError):
            assess_edge_chip(_chip(ingress_mm=0.0), SQUARE_OVERHANGS, GLASS)


class CoverglassTests(unittest.TestCase):
    def test_a_square_placement_covers_the_cell_completely(self):
        result = assess_coverglass(_record())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["completely_covered"])
        self.assertAlmostEqual(result["exposed_area_mm2"], 0.0, places=9)
        self.assertAlmostEqual(result["min_overhang_mm"], 0.5, places=12)

    def test_an_overhang_exactly_on_the_minimum_still_accepts(self):
        result = assess_coverglass(_record(offset_x_mm=0.3))
        self.assertAlmostEqual(result["overhangs_mm"]["x-minus"], 0.2, places=12)
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["thin_edges"], [])

    def test_a_thin_overhang_refers_without_exposing_the_cell(self):
        result = assess_coverglass(_record(offset_x_mm=0.4))
        self.assertEqual(result["verdict"], REFER)
        self.assertTrue(result["completely_covered"])
        self.assertEqual(result["thin_edges"], ["x-minus"])

    def test_a_shortfall_inside_the_placement_tolerance_is_indeterminate(self):
        result = assess_coverglass(_record(offset_x_mm=0.52))
        self.assertEqual(result["verdict"], REFER)
        self.assertTrue(result["coverage_indeterminate"])
        self.assertFalse(result["completely_covered"])

    def test_a_misplaced_but_adequate_glass_is_reworked(self):
        result = assess_coverglass(_record(offset_x_mm=0.8))
        self.assertEqual(result["verdict"], REWORK)
        self.assertEqual(result["short_edges"], ["x-minus"])
        self.assertEqual(result["undersized_axes"], [])
        self.assertAlmostEqual(result["exposed_area_mm2"], 12.0, places=9)

    def test_a_badly_misplaced_glass_exposes_too_much_to_re_lay(self):
        result = assess_coverglass(_record(offset_x_mm=1.5))
        self.assertEqual(result["verdict"], REJECT)
        self.assertAlmostEqual(result["exposed_area_fraction"], 0.025, places=9)

    def test_an_undersized_glass_is_the_wrong_part_not_a_wrong_placement(self):
        record = _record(coverglass={"length_mm": 39.0, "width_mm": 41.0})
        result = assess_coverglass(record)
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["undersized_axes"], ["x"])
        self.assertTrue(
            any("re-lay cannot recover" in finding for finding in result["findings"])
        )

    def test_a_glass_exactly_the_size_of_the_cell_covers_but_carries_no_margin(self):
        record = _record(coverglass=dict(CELL))
        result = assess_coverglass(record)
        self.assertEqual(result["undersized_axes"], [])
        self.assertTrue(result["completely_covered"])
        self.assertEqual(result["verdict"], REFER)
        self.assertEqual(sorted(result["thin_edges"]), sorted(list(COVERGLASS_EDGES)))

    def test_a_chip_exposure_adds_to_the_coverglass_exposure(self):
        result = assess_coverglass(_record([_chip(ingress_mm=0.7)]))
        self.assertEqual(result["verdict"], REWORK)
        self.assertAlmostEqual(result["exposed_area_mm2"], 1.0, places=9)
        self.assertFalse(result["completely_covered"])

    def test_too_many_chips_escalate_even_when_each_one_passes(self):
        chips = [_chip(id="G%d" % n, edge=edge) for n, edge in enumerate(COVERGLASS_EDGES)]
        result = assess_coverglass(_record(chips))
        self.assertEqual(result["verdict"], REFER)
        self.assertTrue(any("edge chips against" in f for f in result["findings"]))

    def test_duplicate_chip_ids_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass(_record([_chip(), _chip()]))

    def test_a_blank_coverglass_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass(_record(coverglass_id="  "))

    def test_a_record_without_a_cell_rejected(self):
        record = _record()
        del record["cell"]
        with self.assertRaises(ValueError):
            assess_coverglass(record)

    def test_non_list_chips_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass(_record(edge_chips="none"))


class AssemblyTests(unittest.TestCase):
    def test_every_glass_square_gives_a_covered_assembly(self):
        records = [_record(coverglass_id="CG-%d" % n) for n in range(3)]
        result = inspect_assembly_coverage(_assembly(records))
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["every_cell_completely_covered"])
        self.assertAlmostEqual(result["bare_cell_exposed_fraction"], 0.0, places=12)

    def test_a_missing_record_leaves_the_assembly_open(self):
        records = [_record(coverglass_id="CG-%d" % n) for n in range(2)]
        result = inspect_assembly_coverage(_assembly(records, declared=5))
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)
        self.assertEqual(result["missing_record_count"], 3)
        self.assertFalse(result["every_cell_completely_covered"])

    def test_the_worst_glass_drives_the_assembly_verdict(self):
        records = [
            _record(coverglass_id="CG-0"),
            _record(coverglass_id="CG-1", offset_x_mm=0.8),
        ]
        result = inspect_assembly_coverage(_assembly(records))
        self.assertEqual(result["verdict"], REWORK)
        self.assertEqual(result["exposed_ids"], ["CG-1"])
        self.assertEqual(result["not_accepted_ids"], ["CG-1"])
        self.assertAlmostEqual(result["bare_cell_exposed_mm2"], 12.0, places=9)

    def test_more_records_than_declared_rejected(self):
        records = [_record(coverglass_id="CG-%d" % n) for n in range(3)]
        with self.assertRaises(ValueError):
            inspect_assembly_coverage(_assembly(records, declared=2))

    def test_duplicate_coverglass_ids_rejected(self):
        records = [_record(coverglass_id="CG-0") for _ in range(2)]
        with self.assertRaises(ValueError):
            inspect_assembly_coverage(_assembly(records))

    def test_non_integer_declared_count_rejected(self):
        with self.assertRaises(ValueError):
            inspect_assembly_coverage(_assembly([_record()], declared="two"))

    def test_non_mapping_assembly_rejected(self):
        with self.assertRaises(ValueError):
            inspect_assembly_coverage("SCA-ASSY-01")

    def test_every_declared_disposition_is_counted(self):
        result = inspect_assembly_coverage(_assembly([_record()]))
        self.assertEqual(
            sorted(result["disposition_counts"]), sorted(list(COVERAGE_DISPOSITIONS))
        )


if __name__ == "__main__":
    unittest.main()
