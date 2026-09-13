"""Contract test for the ECSS-E-ST-20-01C clause 4.4.1 type-grouping leaf.

Offline, deterministic, stdlib unittest. Run: python3 test_e2001_equipment_type_categorisation.py
"""

import unittest

from e2001_equipment_type_categorisation_logic import (
    BASE_MARGIN_DB,
    GEOMETRY_TIERS,
    GROUP_NAMES,
    HERITAGE_ADDERS_DB,
    MARGIN_TOLERANCE_DB,
    SURFACE_TIERS,
    assess_item,
    categorize_inventory,
    categorize_item,
    geometry_tier,
    group_name,
    heritage_adder_db,
    margin_meets_policy,
    normalize_item,
    required_margin_db,
    rollup_assembly,
    surface_tier,
)


def item(**overrides):
    """A tier-1 recurrent component that each test perturbs as it needs."""
    base = {
        "id": "wg-load-01",
        "kind": "component",
        "geometry_family": "uniform-waveguide",
        "surface_state": "flight-surface-measured",
        "heritage": "recurrent-qualified",
    }
    base.update(overrides)
    return base


class GeometryTierTests(unittest.TestCase):
    def test_every_known_family_has_a_tier_between_one_and_four(self):
        for family in GEOMETRY_TIERS:
            self.assertIn(geometry_tier(family), (1, 2, 3, 4))

    def test_uniform_waveguide_is_the_best_known_gap(self):
        self.assertEqual(geometry_tier("uniform-waveguide"), 1)

    def test_dielectric_loading_is_the_worst_known_gap(self):
        self.assertEqual(geometry_tier("dielectric-loaded"), 4)

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            geometry_tier("ridged-horn-thing")


class SurfaceTierTests(unittest.TestCase):
    def test_every_known_surface_state_has_a_tier(self):
        for state in SURFACE_TIERS:
            self.assertIn(surface_tier(state), (1, 2, 4))

    def test_measured_flight_surface_is_tier_one(self):
        self.assertEqual(surface_tier("flight-surface-measured"), 1)

    def test_unknown_surface_state_rejected(self):
        with self.assertRaises(ValueError):
            surface_tier("probably-silver")


class HeritageTests(unittest.TestCase):
    def test_recurrent_qualified_adds_nothing(self):
        self.assertAlmostEqual(heritage_adder_db("recurrent-qualified"), 0.0)

    def test_new_design_adds_the_most(self):
        self.assertAlmostEqual(
            heritage_adder_db("new-design"), max(HERITAGE_ADDERS_DB.values())
        )

    def test_unknown_heritage_rejected(self):
        with self.assertRaises(ValueError):
            heritage_adder_db("flight-proven-ish")


class GroupNameTests(unittest.TestCase):
    def test_each_tier_has_a_distinct_label(self):
        labels = {group_name(tier) for tier in (1, 2, 3, 4)}
        self.assertEqual(len(labels), 4)

    def test_tier_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            group_name(5)

    def test_non_integer_tier_rejected(self):
        with self.assertRaises(ValueError):
            group_name("1")


class NormalizeItemTests(unittest.TestCase):
    def test_defaults_are_component_new_design_and_no_constituents(self):
        record = normalize_item(
            {
                "id": "x-01",
                "geometry_family": "coaxial-line",
                "surface_state": "flight-surface-measured",
            }
        )
        self.assertEqual(record["kind"], "component")
        self.assertEqual(record["heritage"], "new-design")
        self.assertEqual(record["constituents"], [])
        self.assertIsNone(record["declared_group"])
        self.assertIsNone(record["declared_margin_db"])

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            normalize_item(["x-01"])

    def test_missing_id_rejected(self):
        with self.assertRaises(ValueError):
            normalize_item(
                {
                    "geometry_family": "coaxial-line",
                    "surface_state": "flight-surface-measured",
                }
            )

    def test_blank_id_rejected(self):
        with self.assertRaises(ValueError):
            normalize_item(item(id="   "))

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalize_item(item(kind="subsystem"))

    def test_missing_geometry_rejected(self):
        raw = item()
        del raw["geometry_family"]
        with self.assertRaises(ValueError):
            normalize_item(raw)

    def test_missing_surface_state_rejected(self):
        raw = item()
        del raw["surface_state"]
        with self.assertRaises(ValueError):
            normalize_item(raw)

    def test_unknown_heritage_rejected(self):
        with self.assertRaises(ValueError):
            normalize_item(item(heritage="heritage-ish"))

    def test_component_cannot_declare_constituents(self):
        with self.assertRaises(ValueError):
            normalize_item(item(constituents=["wg-load-01"]))

    def test_constituents_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            normalize_item(item(kind="equipment", constituents="wg-load-01"))

    def test_blank_constituent_reference_rejected(self):
        with self.assertRaises(ValueError):
            normalize_item(item(kind="equipment", constituents=[""]))

    def test_unknown_declared_group_rejected(self):
        with self.assertRaises(ValueError):
            normalize_item(item(declared_group="group-9-whatever"))

    def test_negative_declared_margin_rejected(self):
        with self.assertRaises(ValueError):
            normalize_item(item(declared_margin_db=-1.0))

    def test_non_numeric_declared_margin_rejected(self):
        with self.assertRaises(ValueError):
            normalize_item(item(declared_margin_db="6 dB"))

    def test_non_finite_declared_margin_rejected(self):
        with self.assertRaises(ValueError):
            normalize_item(item(declared_margin_db=float("inf")))


class CategorizeItemTests(unittest.TestCase):
    def test_uniform_gap_and_measured_surface_is_group_one(self):
        record = categorize_item(item())
        self.assertEqual(record["tier"], 1)
        self.assertEqual(record["group"], GROUP_NAMES[1])

    def test_printed_line_moves_the_item_to_group_two(self):
        record = categorize_item(item(geometry_family="planar-printed"))
        self.assertEqual(record["tier"], 2)
        self.assertEqual(record["governing_property"], "gap-geometry")

    def test_coupon_surface_data_moves_a_uniform_gap_to_group_two(self):
        record = categorize_item(item(surface_state="process-coupon-sample"))
        self.assertEqual(record["tier"], 2)
        self.assertEqual(record["governing_property"], "surface-knowledge")

    def test_unknown_surface_dominates_a_perfect_geometry(self):
        record = categorize_item(item(surface_state="unknown-surface"))
        self.assertEqual(record["tier"], 4)
        self.assertEqual(record["governing_property"], "surface-knowledge")

    def test_dielectric_loading_dominates_a_measured_surface(self):
        record = categorize_item(item(geometry_family="dielectric-loaded"))
        self.assertEqual(record["tier"], 4)
        self.assertEqual(record["governing_property"], "gap-geometry")

    def test_multi_cavity_assembly_with_coupon_data_is_group_three(self):
        record = categorize_item(
            item(
                geometry_family="non-uniform-assembly",
                surface_state="process-coupon-sample",
            )
        )
        self.assertEqual(record["tier"], 3)

    def test_the_worse_of_two_tiers_wins_and_is_never_averaged(self):
        record = categorize_item(
            item(geometry_family="radiating-aperture", surface_state="unknown-surface")
        )
        self.assertEqual(record["tier"], 4)


class RequiredMarginTests(unittest.TestCase):
    def test_best_group_recurrent_build_takes_the_base_value(self):
        self.assertAlmostEqual(
            required_margin_db(1, "recurrent-qualified"), BASE_MARGIN_DB[1]
        )

    def test_new_design_adds_two_decibels(self):
        self.assertAlmostEqual(
            required_margin_db(3, "new-design"), BASE_MARGIN_DB[3] + 2.0
        )

    def test_modified_recurrent_adds_one_decibel(self):
        self.assertAlmostEqual(
            required_margin_db(4, "modified-recurrent"), BASE_MARGIN_DB[4] + 1.0
        )

    def test_margin_rises_monotonically_with_the_tier(self):
        values = [required_margin_db(tier, "new-design") for tier in (1, 2, 3, 4)]
        self.assertEqual(values, sorted(values))
        self.assertLess(values[0], values[3])

    def test_unknown_tier_rejected(self):
        with self.assertRaises(ValueError):
            required_margin_db(0, "new-design")


class MarginPolicyTests(unittest.TestCase):
    def test_declared_value_equal_to_policy_passes(self):
        self.assertTrue(margin_meets_policy(6.0, 6.0))

    def test_representation_error_is_absorbed(self):
        policy = required_margin_db(2, "modified-recurrent")
        self.assertTrue(margin_meets_policy(policy - MARGIN_TOLERANCE_DB / 2.0, policy))

    def test_real_shortfall_still_fails(self):
        self.assertFalse(margin_meets_policy(5.5, 6.0))

    def test_non_numeric_declared_value_rejected(self):
        with self.assertRaises(ValueError):
            margin_meets_policy(None, 6.0)

    def test_non_finite_policy_value_rejected(self):
        with self.assertRaises(ValueError):
            margin_meets_policy(6.0, float("nan"))


class AssessItemTests(unittest.TestCase):
    def test_clean_item_has_no_findings(self):
        record = assess_item(item(declared_group=GROUP_NAMES[1], declared_margin_db=3.0))
        self.assertEqual(record["findings"], [])
        self.assertAlmostEqual(record["required_margin_db"], 3.0)

    def test_understated_group_is_flagged(self):
        record = assess_item(
            item(geometry_family="dielectric-loaded", declared_group=GROUP_NAMES[1])
        )
        self.assertIn("group-understated", record["findings"])

    def test_overstated_group_is_flagged_too(self):
        record = assess_item(item(declared_group=GROUP_NAMES[4]))
        self.assertIn("group-overstated", record["findings"])

    def test_margin_below_the_type_group_policy_is_flagged(self):
        record = assess_item(
            item(
                geometry_family="non-uniform-assembly",
                heritage="new-design",
                declared_margin_db=3.0,
            )
        )
        self.assertIn("margin-below-type-group-policy", record["findings"])

    def test_margin_exactly_on_policy_is_not_flagged(self):
        record = assess_item(
            item(geometry_family="non-uniform-assembly", heritage="new-design",
                 declared_margin_db=BASE_MARGIN_DB[3] + 2.0)
        )
        self.assertEqual(record["findings"], [])

    def test_both_defects_are_reported_together(self):
        record = assess_item(
            item(
                surface_state="unknown-surface",
                declared_group=GROUP_NAMES[2],
                declared_margin_db=1.0,
            )
        )
        self.assertEqual(len(record["findings"]), 2)

    def test_required_margin_is_attached_to_the_record(self):
        record = assess_item(item(heritage="new-design"))
        self.assertAlmostEqual(record["required_margin_db"], BASE_MARGIN_DB[1] + 2.0)


class RollupTests(unittest.TestCase):
    def setUp(self):
        self.components = {
            "wg-load-01": assess_item(item(id="wg-load-01")),
            "diel-window-01": assess_item(
                item(id="diel-window-01", geometry_family="dielectric-loaded")
            ),
        }

    def test_assembly_inherits_the_worst_constituent(self):
        rolled = rollup_assembly(
            item(id="asm-01", kind="equipment", constituents=["wg-load-01", "diel-window-01"]),
            self.components,
        )
        self.assertEqual(rolled["tier"], 4)
        self.assertEqual(rolled["governing_item_id"], "diel-window-01")

    def test_assembly_keeps_its_own_group_when_it_is_the_worst(self):
        rolled = rollup_assembly(
            item(
                id="asm-02",
                kind="equipment",
                geometry_family="non-uniform-assembly",
                constituents=["wg-load-01"],
            ),
            self.components,
        )
        self.assertEqual(rolled["tier"], 3)
        self.assertEqual(rolled["governing_item_id"], "asm-02")

    def test_rolled_margin_matches_the_governing_tier(self):
        rolled = rollup_assembly(
            item(id="asm-03", kind="equipment", constituents=["diel-window-01"]),
            self.components,
        )
        self.assertAlmostEqual(rolled["required_margin_db"], BASE_MARGIN_DB[4])

    def test_missing_constituent_rejected(self):
        with self.assertRaises(ValueError):
            rollup_assembly(
                item(id="asm-04", kind="equipment", constituents=["ghost-01"]),
                self.components,
            )

    def test_component_cannot_be_rolled_up(self):
        with self.assertRaises(ValueError):
            rollup_assembly(item(id="wg-load-02"), self.components)

    def test_components_argument_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            rollup_assembly(
                item(id="asm-05", kind="equipment", constituents=[]),
                [self.components],
            )


class InventoryTests(unittest.TestCase):
    def inventory(self):
        return [
            item(id="wg-load-01"),
            item(id="diel-window-01", geometry_family="dielectric-loaded"),
            item(id="asm-01", kind="equipment", constituents=["wg-load-01", "diel-window-01"]),
        ]

    def test_every_item_is_categorized(self):
        report = categorize_inventory(self.inventory())
        self.assertEqual(len(report["records"]), 3)

    def test_group_counts_are_reported(self):
        report = categorize_inventory(self.inventory())
        self.assertEqual(report["group_counts"][GROUP_NAMES[1]], 1)
        self.assertEqual(report["group_counts"][GROUP_NAMES[4]], 2)

    def test_worst_case_margin_comes_from_the_dielectric_part(self):
        report = categorize_inventory(self.inventory())
        self.assertAlmostEqual(report["worst_case_margin_db"], BASE_MARGIN_DB[4])

    def test_clean_inventory_is_consistent(self):
        report = categorize_inventory(self.inventory())
        self.assertTrue(report["consistent"])
        self.assertEqual(report["findings"], [])

    def test_declared_group_defect_makes_the_inventory_inconsistent(self):
        items = self.inventory()
        items[1] = item(
            id="diel-window-01",
            geometry_family="dielectric-loaded",
            declared_group=GROUP_NAMES[2],
        )
        report = categorize_inventory(items)
        self.assertFalse(report["consistent"])
        self.assertEqual(
            report["findings"], [{"id": "diel-window-01", "finding": "group-understated"}]
        )

    def test_duplicate_identifier_rejected(self):
        with self.assertRaises(ValueError):
            categorize_inventory([item(id="wg-load-01"), item(id="wg-load-01")])

    def test_empty_inventory_rejected(self):
        with self.assertRaises(ValueError):
            categorize_inventory([])

    def test_non_sequence_inventory_rejected(self):
        with self.assertRaises(ValueError):
            categorize_inventory(item())


if __name__ == "__main__":
    unittest.main()
