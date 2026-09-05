"""Contract test for the cargo-compartment-sizing SKILL.md workflow.

Exercises the freight cargo compartment sizing workflow end to end:
step 1 fixes the hold envelope and payload (compartment length, width,
usable height, payload mass and density), step 2 chooses the candidate
ULD from the module catalog of unit load devices, step 3 checks the ULD
cross-section through the cargo door with the rotated orientation tried,
step 4 picks the largest ULD that fits the door, step 5 lays out the ULD
positions in the compartment as a strip layout with the aisle allowance,
step 6 computes the required cargo volume from the payload, step 7 sizes
the cargo door opening with the side and top margins and the corner
radii within the fuselage, and step 8 assembles the adequacy verdict
(ULD count, volume utilization, unused length and width, door
clearance, volume adequate). Offline and deterministic, stdlib unittest
only. Run: python3 scripts/test_cargo_compartment_sizing.py
"""

import math
import unittest

from cargo_compartment_sizing_logic import (
    AISLE_ALLOWANCE_M,
    DOOR_SIDE_MARGIN_M,
    DOOR_TOP_MARGIN_M,
    ULD_CATALOG,
    cargo_volume_required,
    compartment_uld_layout,
    door_opening_geometry,
    layout_summary,
    max_uld_for_door,
    uld_fits_door,
)

# Worked example: narrowbody lower-lobe freight hold, usable length 12.0 m,
# width 2.2 m, usable height 1.70 m, payload 4000 kg at 120 kg/m3, cargo
# door 1.80 m wide x 1.68 m high.
LENGTH_M = 12.0
WIDTH_M = 2.2
HEIGHT_M = 1.70
PAYLOAD_KG = 4000.0
DENSITY_KG_M3 = 120.0
DOOR_WIDTH_M = 1.80
DOOR_HEIGHT_M = 1.68


class UldFitsDoorTests(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, the ULD cross-section check
    through the cargo door, is exercised by these tests."""

    def test_ld3_46_fits_worked_example_door_both_orientations(self):
        """LD3-46 passes the 1.80 x 1.68 m door opening as tabulated and
        with the rotated cross-section."""
        width = ULD_CATALOG["LD3-46"][1]
        height = ULD_CATALOG["LD3-46"][2]
        self.assertTrue(uld_fits_door(width, height, DOOR_WIDTH_M, DOOR_HEIGHT_M))
        self.assertTrue(uld_fits_door(height, width, DOOR_WIDTH_M, DOOR_HEIGHT_M))

    def test_ld6_and_p6p_rejected_by_worked_example_door(self):
        """LD6 and P6P-96x125 are wider than the 1.80 m opening in both
        the straight and the rotated orientation."""
        for uld_id in ("LD6", "P6P-96x125"):
            width = ULD_CATALOG[uld_id][1]
            height = ULD_CATALOG[uld_id][2]
            self.assertFalse(uld_fits_door(width, height, DOOR_WIDTH_M,
                                           DOOR_HEIGHT_M))
            self.assertFalse(uld_fits_door(height, width, DOOR_WIDTH_M,
                                           DOOR_HEIGHT_M))

    def test_orientation_swap_identity_on_large_opening(self):
        """A ULD that fits a door in one orientation also passes the
        swapped cross-section when the opening is large enough to admit
        both dimensions (spec identity)."""
        width = ULD_CATALOG["LD1"][1]
        height = ULD_CATALOG["LD1"][2]
        self.assertTrue(uld_fits_door(width, height, 1.7, 1.7))
        self.assertTrue(uld_fits_door(height, width, 1.7, 1.7))

    def test_rotated_only_fit_detected(self):
        """A cross-section that only passes the door after rotation is
        accepted by the step 3 check."""
        self.assertTrue(uld_fits_door(1.5, 1.7, 1.8, 1.6))
        self.assertFalse(uld_fits_door(1.5, 1.7, 1.8, 1.2))


class CatalogTests(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, the candidate ULD from the module
    catalog of unit load devices, is exercised by these tests."""

    def test_catalog_anchor_volumes(self):
        """LD3-46, LD1 and LD9 envelope volumes reproduce the worked
        example anchors; LD11 sits between LD3-46 and LD9."""
        def volume(uld_id):
            length, width, height = ULD_CATALOG[uld_id]
            return length * width * height

        self.assertAlmostEqual(volume("LD3-46"), 3.895769, places=5)
        self.assertAlmostEqual(volume("LD1"), 5.827817, places=5)
        self.assertAlmostEqual(volume("LD9"), 11.536493, places=5)
        self.assertGreater(volume("LD11"), 7.0)
        self.assertLess(volume("LD11"), 8.5)

    def test_pallets_use_64in_build_height(self):
        """PMC and P6P pallets carry the nominal 64 in net build height of
        1.6256 m used for volume accounting, and every catalog entry has
        positive dimensions."""
        for uld_id in ("PMC-88x125", "P6P-96x125"):
            self.assertEqual(ULD_CATALOG[uld_id][2], 1.6256)
        for dims in ULD_CATALOG.values():
            self.assertTrue(all(d > 0 for d in dims))


class MaxUldForDoorTests(unittest.TestCase):
    """Step 4 of the SKILL.md workflow, picking the largest ULD that fits
    the cargo door, is exercised by these tests."""

    def test_worked_example_returns_ld1(self):
        """max_uld_for_door(1.80, 1.68) returns LD1 as the largest catalog
        ULD whose cross-section passes the opening."""
        result = max_uld_for_door(DOOR_WIDTH_M, DOOR_HEIGHT_M)
        self.assertEqual(result[0], "LD1")
        self.assertAlmostEqual(result[1], 5.827817, places=4)

    def test_large_door_returns_p6p(self):
        """A wide door admits the P6P-96x125 pallet, the largest catalog
        envelope volume."""
        self.assertEqual(max_uld_for_door(2.5, 1.7)[0], "P6P-96x125")

    def test_no_fit_none_and_deterministic_custom_catalog(self):
        """A tiny opening yields None; a caller-supplied catalog is
        respected and a volume tie resolves to the earlier catalog key."""
        self.assertIsNone(max_uld_for_door(0.5, 0.5))
        custom = {"SMALL": (1.0, 0.8, 0.8), "BIG": (2.0, 1.5, 1.5)}
        self.assertEqual(max_uld_for_door(1.6, 1.6, catalog=custom)[0], "BIG")
        tie = {"ZB": (2.0, 1.0, 1.0), "AA": (1.0, 2.0, 1.0)}
        self.assertEqual(max_uld_for_door(2.1, 1.1, catalog=tie)[0], "AA")


class CompartmentLayoutTests(unittest.TestCase):
    """Step 5 of the SKILL.md workflow, the strip layout of ULD positions
    in the compartment, is exercised by these tests."""

    def test_worked_example_layout(self):
        """The 12.0 x 2.2 x 1.70 m hold takes 7 LD3-46 positions in one
        row of 7, and a repeat run returns identical results."""
        layout = compartment_uld_layout(LENGTH_M, WIDTH_M, HEIGHT_M, "LD3-46")
        self.assertEqual(layout["positions"], 7)
        self.assertEqual(layout["rows"], 1)
        self.assertEqual(layout["per_row"], 7)
        self.assertAlmostEqual(layout["utilized_volume_m3"], 27.270382, places=5)
        self.assertAlmostEqual(layout["compartment_volume_m3"], 44.880000, places=5)
        self.assertAlmostEqual(layout["volume_utilization"], 0.607629, places=6)
        self.assertAlmostEqual(layout["unused_length_m"], 1.065300, places=4)
        self.assertAlmostEqual(layout["unused_width_m"], 0.665840, places=4)
        self.assertEqual(layout,
                         compartment_uld_layout(LENGTH_M, WIDTH_M, HEIGHT_M,
                                                "LD3-46"))

    def test_layout_dict_keys_exact(self):
        """The layout dict carries exactly the documented keys."""
        layout = compartment_uld_layout(LENGTH_M, WIDTH_M, HEIGHT_M, "LD3-46")
        self.assertEqual(
            set(layout.keys()),
            {"uld_id", "positions", "rows", "per_row",
             "utilized_volume_m3", "compartment_volume_m3",
             "volume_utilization", "unused_length_m", "unused_width_m"},
        )

    def test_doubling_length_doubles_per_row_and_positions(self):
        """Doubling the compartment length doubles per_row and positions
        at fixed width (spec identity, lengths that are exact ULD-length
        multiples)."""
        uld_length = ULD_CATALOG["LD3-46"][0]
        base = compartment_uld_layout(8 * uld_length, WIDTH_M, HEIGHT_M,
                                      "LD3-46")
        doubled = compartment_uld_layout(16 * uld_length, WIDTH_M, HEIGHT_M,
                                         "LD3-46")
        self.assertEqual(doubled["per_row"], 2 * base["per_row"])
        self.assertEqual(doubled["positions"], 2 * base["positions"])
        self.assertEqual(doubled["rows"], base["rows"])

    def test_two_abreast_rows_with_aisle_allowance(self):
        """A hold wider than twice the ULD width plus the aisle allowance
        admits two rows across the width, and the 0.10 m aisle allowance
        only separates two-abreast rows."""
        wide = compartment_uld_layout(LENGTH_M, 3.6, HEIGHT_M, "LD3-46")
        self.assertEqual(wide["rows"], 2)
        self.assertEqual(wide["positions"], wide["per_row"] * 2)
        single = compartment_uld_layout(LENGTH_M, WIDTH_M, HEIGHT_M, "LD3-46")
        uld_width = ULD_CATALOG["LD3-46"][1]
        self.assertAlmostEqual(single["unused_width_m"], WIDTH_M - uld_width,
                               places=6)

    def test_layout_invalid_inputs_raise(self):
        """Unknown ULD ids, non-positive compartment dimensions and a ULD
        taller than the usable height all raise ValueError."""
        with self.assertRaises(ValueError):
            compartment_uld_layout(LENGTH_M, WIDTH_M, HEIGHT_M, "LD-99")
        with self.assertRaises(ValueError):
            compartment_uld_layout(0.0, WIDTH_M, HEIGHT_M, "LD3-46")
        with self.assertRaises(ValueError):
            compartment_uld_layout(LENGTH_M, -1.0, HEIGHT_M, "LD3-46")
        with self.assertRaises(ValueError):
            compartment_uld_layout(LENGTH_M, WIDTH_M, 0.0, "LD3-46")
        with self.assertRaises(ValueError):
            compartment_uld_layout(LENGTH_M, WIDTH_M, 1.50, "LD3-46")


class CargoVolumeRequiredTests(unittest.TestCase):
    """Step 6 of the SKILL.md workflow, the required cargo volume from the
    payload mass and density, is exercised by these tests."""

    def test_worked_example_required_volume(self):
        """4000 kg at 120 kg/m3 needs 33.333333 m3 of cargo volume."""
        self.assertAlmostEqual(cargo_volume_required(PAYLOAD_KG, DENSITY_KG_M3),
                               33.333333, places=5)

    def test_density_doubling_halves_required_volume(self):
        """The required volume halves when the payload density doubles
        (spec identity)."""
        base = cargo_volume_required(PAYLOAD_KG, DENSITY_KG_M3)
        dense = cargo_volume_required(PAYLOAD_KG, 2 * DENSITY_KG_M3)
        self.assertAlmostEqual(dense, base / 2.0, places=6)

    def test_zero_mass_and_invalid_density_or_mass(self):
        """Zero payload needs zero volume; non-positive density and
        negative mass raise ValueError."""
        self.assertEqual(cargo_volume_required(0.0, DENSITY_KG_M3), 0.0)
        with self.assertRaises(ValueError):
            cargo_volume_required(PAYLOAD_KG, 0.0)
        with self.assertRaises(ValueError):
            cargo_volume_required(PAYLOAD_KG, -10.0)
        with self.assertRaises(ValueError):
            cargo_volume_required(-100.0, DENSITY_KG_M3)


class DoorOpeningGeometryTests(unittest.TestCase):
    """Step 7 of the SKILL.md workflow, sizing the cargo door opening with
    the side and top margins and the corner radii within the fuselage, is
    exercised by these tests."""

    def test_worked_example_door_geometry(self):
        """LD3-46 at sill -0.75 m in the 1.975 m fuselage needs a 1.634160
        m wide and 1.675600 m high opening with both corner radii inside
        the fuselage."""
        geo = door_opening_geometry("LD3-46", -0.75, 1.975)
        self.assertAlmostEqual(geo["required_door_width_m"], 1.634160, places=4)
        self.assertAlmostEqual(geo["required_door_height_m"], 1.675600, places=4)
        self.assertAlmostEqual(geo["top_corner_radius_m"], 1.234648, places=4)
        self.assertAlmostEqual(geo["bottom_corner_radius_m"], 1.109108, places=4)
        self.assertTrue(geo["within_fuselage"])

    def test_door_size_is_uld_plus_margins(self):
        """The required door width is the ULD width plus twice the 0.05 m
        side margin, and the height is the ULD height plus the 0.05 m top
        margin."""
        geo = door_opening_geometry("LD3-46", -0.75, 1.975)
        uld_width = ULD_CATALOG["LD3-46"][1]
        uld_height = ULD_CATALOG["LD3-46"][2]
        self.assertAlmostEqual(geo["required_door_width_m"],
                               uld_width + 2 * DOOR_SIDE_MARGIN_M, places=6)
        self.assertAlmostEqual(geo["required_door_height_m"],
                               uld_height + DOOR_TOP_MARGIN_M, places=6)

    def test_corner_radius_hypot_identity(self):
        """Each corner radius is the hypotenuse from the fuselage
        centerline axis to the opening corner at the sill height."""
        geo = door_opening_geometry("LD3-46", -0.75, 1.975)
        half_width = geo["required_door_width_m"] / 2.0
        self.assertAlmostEqual(
            geo["top_corner_radius_m"],
            math.hypot(half_width, -0.75 + geo["required_door_height_m"]),
            places=6)
        self.assertAlmostEqual(geo["bottom_corner_radius_m"],
                               math.hypot(half_width, -0.75), places=6)

    def test_tight_fuselage_reports_within_fuselage_false(self):
        """A tight fuselage radius makes within_fuselage False instead of
        raising, flagging the door for rework."""
        self.assertFalse(
            door_opening_geometry("LD3-46", -0.75, 1.20)["within_fuselage"])

    def test_door_geometry_invalid_inputs_raise(self):
        """An unknown ULD id and a non-positive fuselage radius raise
        ValueError in the door geometry."""
        with self.assertRaises(ValueError):
            door_opening_geometry("LD-99", -0.75, 1.975)
        with self.assertRaises(ValueError):
            door_opening_geometry("LD3-46", -0.75, 0.0)
        with self.assertRaises(ValueError):
            door_opening_geometry("LD3-46", -0.75, -1.0)


class LayoutSummaryTests(unittest.TestCase):
    """Step 8 of the SKILL.md workflow, the adequacy verdict that gates
    the freight hold layout, is exercised by these tests."""

    def test_worked_example_verdict(self):
        """The 4000 kg payload at 120 kg/m3 needs 9 LD3-46 containers
        against 7 positions, so volume_adequate is False with a 6.062952
        m3 shortfall while the door fits."""
        verdict = layout_summary(PAYLOAD_KG, DENSITY_KG_M3, LENGTH_M,
                                 WIDTH_M, HEIGHT_M, DOOR_WIDTH_M,
                                 DOOR_HEIGHT_M, "LD3-46")
        self.assertFalse(verdict["volume_adequate"])
        self.assertEqual(verdict["needed_ulds"], 9)
        self.assertEqual(verdict["positions"], 7)
        self.assertAlmostEqual(verdict["required_volume_m3"], 33.333333, places=5)
        self.assertAlmostEqual(verdict["utilized_volume_m3"], 27.270382, places=5)
        self.assertAlmostEqual(verdict["shortfall_volume_m3"], 6.062952, places=4)
        self.assertTrue(verdict["door_fits"])
        self.assertGreater(verdict["volume_utilization"], 0.5)

    def test_dense_payload_adequate(self):
        """A denser payload needs less volume, so the same hold becomes
        volume_adequate with no shortfall."""
        verdict = layout_summary(PAYLOAD_KG, 260.0, LENGTH_M, WIDTH_M,
                                 HEIGHT_M, DOOR_WIDTH_M, DOOR_HEIGHT_M,
                                 "LD3-46")
        self.assertTrue(verdict["volume_adequate"])
        self.assertEqual(verdict["shortfall_volume_m3"], 0.0)

    def test_needed_ulds_is_ceil_of_volume_ratio(self):
        """needed_ulds is the ceiling of the required volume over the
        per-ULD envelope volume."""
        verdict = layout_summary(PAYLOAD_KG, DENSITY_KG_M3, LENGTH_M,
                                 WIDTH_M, HEIGHT_M, DOOR_WIDTH_M,
                                 DOOR_HEIGHT_M, "LD3-46")
        uld_volume = ULD_CATALOG["LD3-46"][0] * ULD_CATALOG["LD3-46"][1] \
            * ULD_CATALOG["LD3-46"][2]
        expected = int(math.ceil(verdict["required_volume_m3"] / uld_volume))
        self.assertEqual(verdict["needed_ulds"], expected)

    def test_small_door_reports_door_fits_false(self):
        """A door that blocks the ULD cross-section reports door_fits
        False in the verdict."""
        verdict = layout_summary(PAYLOAD_KG, DENSITY_KG_M3, LENGTH_M,
                                 WIDTH_M, HEIGHT_M, 1.40, 1.40, "LD3-46")
        self.assertFalse(verdict["door_fits"])

    def test_verdict_propagates_layout_errors(self):
        """Non-physical compartment, density and ULD inputs raise
        ValueError through the verdict."""
        with self.assertRaises(ValueError):
            layout_summary(PAYLOAD_KG, DENSITY_KG_M3, 0.0, WIDTH_M,
                           HEIGHT_M, DOOR_WIDTH_M, DOOR_HEIGHT_M, "LD3-46")
        with self.assertRaises(ValueError):
            layout_summary(PAYLOAD_KG, 0.0, LENGTH_M, WIDTH_M, HEIGHT_M,
                           DOOR_WIDTH_M, DOOR_HEIGHT_M, "LD3-46")
        with self.assertRaises(ValueError):
            layout_summary(PAYLOAD_KG, DENSITY_KG_M3, LENGTH_M, WIDTH_M,
                           HEIGHT_M, DOOR_WIDTH_M, DOOR_HEIGHT_M, "LD-99")

    def test_verdict_keys_complete(self):
        """The verdict dict carries the payload, volume, count and door
        keys that gate the freight hold layout."""
        verdict = layout_summary(PAYLOAD_KG, DENSITY_KG_M3, LENGTH_M,
                                 WIDTH_M, HEIGHT_M, DOOR_WIDTH_M,
                                 DOOR_HEIGHT_M, "LD3-46")
        self.assertEqual(
            set(verdict.keys()),
            {"payload_mass_kg", "payload_density_kg_m3", "required_volume_m3",
             "uld_id", "positions", "needed_ulds", "volume_adequate",
             "utilized_volume_m3", "volume_utilization",
             "shortfall_volume_m3", "door_fits"},
        )

    def test_lengthened_hold_becomes_adequate(self):
        """Lengthening the hold to 14.5 m adds a ULD row, lifting the
        utilized volume above the required volume for the worked payload."""
        verdict = layout_summary(PAYLOAD_KG, DENSITY_KG_M3, 14.5, WIDTH_M,
                                 HEIGHT_M, DOOR_WIDTH_M, DOOR_HEIGHT_M,
                                 "LD3-46")
        self.assertGreater(verdict["utilized_volume_m3"], 33.333333)
        self.assertTrue(verdict["volume_adequate"])


class ModuleConstantsTests(unittest.TestCase):
    """The module constants anchoring steps 1 to 7 of the SKILL.md
    workflow, the aisle allowance and the door margins, are fixed."""

    def test_module_constants(self):
        """The aisle allowance for two-abreast rows is 0.10 m and both
        door margins are 0.05 m."""
        self.assertEqual(AISLE_ALLOWANCE_M, 0.10)
        self.assertEqual(DOOR_SIDE_MARGIN_M, 0.05)
        self.assertEqual(DOOR_TOP_MARGIN_M, 0.05)


if __name__ == "__main__":
    unittest.main()
