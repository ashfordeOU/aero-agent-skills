"""Contract tests for the metallic mechanical test scope and purpose logic."""

import unittest

from q7045_applicability_and_purpose_logic import (
    DESIGN_ALLOWABLE_MINIMUM_HEATS,
    PURPOSE_MINIMUM_PIECES,
    assess_campaign,
    cell_coverage,
    expand_matrix,
    heat_coverage,
    in_scope_material,
    minimum_pieces_for_purpose,
    partition_properties,
    valid_pieces,
)


def piece(prop="tensile", orient="l", temp=20.0, heat="H1", valid=True):
    """One test-piece record assigned to a matrix cell."""
    return {
        "property": prop,
        "orientation": orient,
        "temperature_c": temp,
        "heat_id": heat,
        "valid": valid,
    }


def campaign(**overrides):
    """A lot-acceptance campaign on an aluminium plate, one cell, filled."""
    spec = {
        "material_family": "aluminium-alloy",
        "product_form": "plate",
        "requested_properties": ["tensile"],
        "purpose": "lot-acceptance",
        "orientations": ["l"],
        "temperatures_c": [20.0],
        "pieces": [piece() for _ in range(3)],
    }
    spec.update(overrides)
    return spec


class MaterialScopeTests(unittest.TestCase):
    def test_aluminium_alloy_is_in_scope(self):
        self.assertTrue(in_scope_material("aluminium-alloy")["in_scope"])

    def test_carbon_fibre_laminate_is_out_of_scope(self):
        result = in_scope_material("carbon-fibre-laminate")
        self.assertFalse(result["in_scope"])
        self.assertTrue(any("not a metallic" in r for r in result["reasons"]))

    def test_family_is_case_and_space_insensitive(self):
        self.assertTrue(in_scope_material("  Titanium-Alloy ")["in_scope"])

    def test_metal_matrix_composite_needs_a_product_form(self):
        with self.assertRaises(ValueError):
            in_scope_material("metal-matrix-composite")

    def test_metal_matrix_composite_admitted_with_a_product_form(self):
        result = in_scope_material("metal-matrix-composite", "extruded-bar")
        self.assertTrue(result["in_scope"])
        self.assertTrue(any("extruded-bar" in r for r in result["reasons"]))

    def test_unlisted_family_is_refused_not_guessed(self):
        with self.assertRaises(ValueError):
            in_scope_material("unobtainium")

    def test_non_string_family_rejected(self):
        with self.assertRaises(ValueError):
            in_scope_material(42)


class PropertyScopeTests(unittest.TestCase):
    def test_mechanical_properties_are_kept(self):
        split = partition_properties(["tensile", "fatigue"])
        self.assertEqual(split["covered"], ["fatigue", "tensile"])
        self.assertEqual(split["out_of_scope"], [])

    def test_non_mechanical_property_is_carried_out_explicitly(self):
        split = partition_properties(["tensile", "density"])
        self.assertEqual(split["covered"], ["tensile"])
        self.assertEqual(split["out_of_scope"], ["density"])

    def test_duplicate_requests_collapse(self):
        split = partition_properties(["tensile", "tensile"])
        self.assertEqual(split["covered"], ["tensile"])

    def test_unknown_property_is_refused(self):
        with self.assertRaises(ValueError):
            partition_properties(["springiness"])

    def test_empty_request_rejected(self):
        with self.assertRaises(ValueError):
            partition_properties([])


class PurposeMinimumTests(unittest.TestCase):
    def test_design_allowable_owes_the_most_pieces(self):
        self.assertEqual(
            minimum_pieces_for_purpose("design-allowable"),
            max(PURPOSE_MINIMUM_PIECES.values()),
        )

    def test_lot_acceptance_owes_fewer_than_qualification(self):
        self.assertLess(
            minimum_pieces_for_purpose("lot-acceptance"),
            minimum_pieces_for_purpose("qualification"),
        )

    def test_unknown_purpose_rejected(self):
        with self.assertRaises(ValueError):
            minimum_pieces_for_purpose("because-the-customer-asked")


class MatrixTests(unittest.TestCase):
    def test_matrix_is_the_full_cross_product(self):
        cells = expand_matrix(["tensile", "shear"], ["l", "lt"], [20.0, 150.0])
        self.assertEqual(len(cells), 8)

    def test_matrix_cells_are_unique_and_sorted(self):
        cells = expand_matrix(["tensile", "tensile"], ["l"], [20.0, 20.0])
        self.assertEqual(cells, [("tensile", "l", 20.0)])

    def test_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            expand_matrix(["tensile"], ["l"], [-300.0])

    def test_non_numeric_temperature_rejected(self):
        with self.assertRaises(ValueError):
            expand_matrix(["tensile"], ["l"], ["ambient"])

    def test_empty_orientation_list_rejected(self):
        with self.assertRaises(ValueError):
            expand_matrix(["tensile"], [], [20.0])


class ValidPieceTests(unittest.TestCase):
    def test_invalid_pieces_are_not_counted(self):
        grouped = valid_pieces([piece(), piece(valid=False)])
        self.assertEqual(len(grouped[("tensile", "l", 20.0)]), 1)

    def test_missing_valid_flag_defaults_to_valid(self):
        record = piece()
        del record["valid"]
        self.assertEqual(len(valid_pieces([record])), 1)

    def test_non_boolean_valid_flag_rejected(self):
        with self.assertRaises(ValueError):
            valid_pieces([piece(valid="yes")])

    def test_piece_missing_a_cell_key_rejected(self):
        record = piece()
        del record["orientation"]
        with self.assertRaises(ValueError):
            valid_pieces([record])

    def test_non_mapping_piece_rejected(self):
        with self.assertRaises(ValueError):
            valid_pieces(["tensile"])


class CoverageTests(unittest.TestCase):
    def test_empty_and_short_cells_are_reported_separately(self):
        cells = expand_matrix(["tensile"], ["l", "lt"], [20.0])
        coverage = cell_coverage(cells, [piece(), piece()], 3)
        self.assertEqual(coverage["short_cells"], [("tensile", "l", 20.0)])
        self.assertEqual(coverage["empty_cells"], [("tensile", "lt", 20.0)])

    def test_pieces_outside_the_declared_matrix_are_flagged(self):
        cells = expand_matrix(["tensile"], ["l"], [20.0])
        coverage = cell_coverage(cells, [piece(), piece(orient="st")], 1)
        self.assertEqual(coverage["unplanned_cells"], [("tensile", "st", 20.0)])

    def test_zero_minimum_rejected(self):
        with self.assertRaises(ValueError):
            cell_coverage(expand_matrix(["tensile"], ["l"], [20.0]), [], 0)

    def test_heat_coverage_collects_distinct_heats(self):
        heats = heat_coverage([piece(heat="A"), piece(heat="B"), piece(heat="A")])
        self.assertEqual(heats["heats"], ["a", "b"])

    def test_heat_coverage_counts_pieces_with_no_heat(self):
        record = piece()
        del record["heat_id"]
        self.assertEqual(heat_coverage([record])["pieces_without_heat"], 1)


class CampaignAssessmentTests(unittest.TestCase):
    def test_filled_lot_acceptance_campaign_is_complete(self):
        result = assess_campaign(campaign())
        self.assertEqual(result["status"], "in-scope-complete")
        self.assertTrue(result["complete"])

    def test_non_metallic_family_stops_the_assessment(self):
        result = assess_campaign(campaign(material_family="polymer"))
        self.assertEqual(result["status"], "out-of-scope")
        self.assertFalse(result["in_scope"])

    def test_only_non_mechanical_properties_leaves_the_scope(self):
        result = assess_campaign(campaign(requested_properties=["density"]))
        self.assertEqual(result["status"], "out-of-scope")

    def test_non_mechanical_request_is_reported_but_does_not_stop_a_valid_campaign(self):
        result = assess_campaign(campaign(requested_properties=["tensile", "density"]))
        self.assertTrue(result["in_scope"])
        self.assertTrue(any("outside this standard" in f for f in result["findings"]))

    def test_short_cell_makes_the_campaign_incomplete(self):
        result = assess_campaign(campaign(pieces=[piece(), piece()]))
        self.assertEqual(result["status"], "in-scope-incomplete")
        self.assertTrue(any("fewer than" in f for f in result["findings"]))

    def test_empty_cell_is_reported_as_its_own_finding(self):
        result = assess_campaign(campaign(orientations=["l", "lt"]))
        self.assertTrue(any("no valid test piece" in f for f in result["findings"]))

    def test_invalid_pieces_do_not_fill_a_cell(self):
        result = assess_campaign(
            campaign(pieces=[piece(), piece(), piece(valid=False)])
        )
        self.assertEqual(result["status"], "in-scope-incomplete")

    def test_design_allowable_from_one_heat_fails_heat_coverage(self):
        result = assess_campaign(
            campaign(purpose="design-allowable", pieces=[piece() for _ in range(9)])
        )
        self.assertTrue(any("multi-heat basis" in f for f in result["findings"]))

    def test_design_allowable_across_enough_heats_passes(self):
        heats = ["H1", "H2", "H3"]
        pieces = [piece(heat=heats[i % DESIGN_ALLOWABLE_MINIMUM_HEATS]) for i in range(9)]
        result = assess_campaign(campaign(purpose="design-allowable", pieces=pieces))
        self.assertEqual(result["status"], "in-scope-complete")

    def test_acceptance_dataset_does_not_become_a_design_allowable(self):
        pieces = [piece(heat="H%d" % (i % 3)) for i in range(3)]
        accepted = assess_campaign(campaign(pieces=pieces))
        promoted = assess_campaign(campaign(purpose="design-allowable", pieces=pieces))
        self.assertTrue(accepted["complete"])
        self.assertFalse(promoted["complete"])

    def test_missing_spec_key_rejected(self):
        spec = campaign()
        del spec["purpose"]
        with self.assertRaises(ValueError):
            assess_campaign(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_campaign(["aluminium-alloy"])

    def test_minimum_travels_with_the_result(self):
        result = assess_campaign(campaign(purpose="qualification"))
        self.assertEqual(result["minimum_pieces_per_cell"], 5)


if __name__ == "__main__":
    unittest.main()
