#!/usr/bin/env python3
"""Gate 3 contract test: datum reference frames.

Exercises scripts/datum_reference_frames_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 (datum precedence
parsing; datum feature simulators for plane, axis, point; degrees of
freedom constrained by each datum; the precedence order changing the
constraint table; material condition modifiers MMB, LMB, RMB on datum
feature references and the resulting datum shift; the feature control
frame string; invalid inputs raise ValueError.

Anchors:
- dof_set('plane', 'z') = {tz, rx, ry}: one translation, two rotations
- dof_set('axis', 'z') = {tx, ty, rx, ry}: two translations, two rotations
- dof_set('point', 'z') = {tx, ty, tz}: three translations
- plane z + plane x + plane y frame constrains 3, then 2, then 1 DOF
  (the 3-2-1 rule), all six constrained
- swapping primary and secondary changes the per-datum DOF table
- datum_shift('rmb', 'hole', 10.0, 10.3) = 0.0
- datum_shift('mmb', 'hole', 10.0, 10.3) = 0.3
- datum_shift('mmb', 'pin', 10.0, 9.8) = 0.2
- datum_shift('lmb', 'hole', 10.5, 10.2) = 0.3
- feature_control_frame('position', 0.5, ('A',)) = 'position-symbol|diameter-0.5|A'
- feature_control_frame('position', 0.5, ('A', {'letter': 'B',
  'modifier': 'mmb'}, 'C'), 'mmc') = 'position-symbol|diameter-0.5-MMC|A|B-MMB|C'
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import datum_reference_frames_logic as drf  # noqa: E402

POS = "\u2316"
DIAM = "\u2300"
MMC = "\u24c2"
LMC = "\u24c1"
RFS = "\u24c8"


class DofSetTest(unittest.TestCase):
    def test_plane_normal_z(self):
        self.assertEqual(drf.dof_set("plane", "z"), frozenset(("tz", "rx", "ry")))

    def test_plane_normal_x(self):
        self.assertEqual(drf.dof_set("plane", "x"), frozenset(("tx", "ry", "rz")))

    def test_axis_along_z(self):
        self.assertEqual(
            drf.dof_set("axis", "z"), frozenset(("tx", "ty", "rx", "ry"))
        )

    def test_axis_along_y(self):
        self.assertEqual(
            drf.dof_set("axis", "y"), frozenset(("tx", "tz", "rx", "rz"))
        )

    def test_point(self):
        self.assertEqual(drf.dof_set("point", "z"), frozenset(("tx", "ty", "tz")))

    def test_invalid_feature_type_raises(self):
        with self.assertRaises(ValueError):
            drf.dof_set("slot", "z")

    def test_invalid_orientation_raises(self):
        with self.assertRaises(ValueError):
            drf.dof_set("plane", "w")


class DofLabelTest(unittest.TestCase):
    def test_translation_label(self):
        self.assertEqual(drf.dof_label("tx"), "translation x")

    def test_rotation_label(self):
        self.assertEqual(drf.dof_label("rz"), "rotation z")

    def test_unknown_dof_raises(self):
        with self.assertRaises(ValueError):
            drf.dof_label("qx")


class ParseDatumPrecedenceTest(unittest.TestCase):
    def test_letters_auto_assigned(self):
        datums = drf.parse_datum_precedence(
            {"feature_type": "plane", "orientation": "z"},
            {"feature_type": "plane", "orientation": "x"},
            {"feature_type": "plane", "orientation": "y"},
        )
        self.assertEqual([d["letter"] for d in datums], ["A", "B", "C"])

    def test_default_modifier_is_rmb(self):
        datums = drf.parse_datum_precedence(
            {"feature_type": "plane", "orientation": "z"}
        )
        self.assertEqual(datums[0]["modifier"], "rmb")

    def test_simulator_from_feature_type(self):
        datums = drf.parse_datum_precedence(
            {"feature_type": "axis", "orientation": "z"},
            {"feature_type": "point", "orientation": "z"},
        )
        self.assertEqual(datums[0]["simulator"], "axis")
        self.assertEqual(datums[1]["simulator"], "point")

    def test_custom_letter_kept(self):
        datums = drf.parse_datum_precedence(
            {"feature_type": "plane", "orientation": "z", "letter": "D"}
        )
        self.assertEqual(datums[0]["letter"], "D")

    def test_duplicate_letter_raises(self):
        with self.assertRaises(ValueError):
            drf.parse_datum_precedence(
                {"feature_type": "plane", "orientation": "z", "letter": "A"},
                {"feature_type": "plane", "orientation": "x", "letter": "A"},
            )

    def test_invalid_feature_type_raises(self):
        with self.assertRaises(ValueError):
            drf.parse_datum_precedence({"feature_type": "cone", "orientation": "z"})

    def test_lowercase_letter_raises(self):
        with self.assertRaises(ValueError):
            drf.parse_datum_precedence({"feature_type": "plane", "orientation": "z", "letter": "a"})

    def test_invalid_modifier_raises(self):
        with self.assertRaises(ValueError):
            drf.parse_datum_precedence(
                {"feature_type": "plane", "orientation": "z", "modifier": "mrb"}
            )


class DatumReferenceFrameTest(unittest.TestCase):
    def test_primary_plane_constrains_correct_dof(self):
        frame = drf.datum_reference_frame(
            {"feature_type": "plane", "orientation": "z"}
        )
        row = frame["dof_table"][0]
        self.assertEqual(row["precedence"], "primary")
        self.assertEqual(row["simulator"], "plane")
        self.assertEqual(row["dof"], ["tz", "rx", "ry"])
        self.assertEqual(row["count"], 3)
        self.assertEqual(frame["constrained"], ["tz", "rx", "ry"])
        self.assertEqual(frame["unconstrained"], ["tx", "ty", "rz"])

    def test_three_plane_frame_321_rule(self):
        frame = drf.datum_reference_frame(
            {"feature_type": "plane", "orientation": "z"},
            {"feature_type": "plane", "orientation": "x"},
            {"feature_type": "plane", "orientation": "y"},
        )
        counts = [row["count"] for row in frame["dof_table"]]
        self.assertEqual(counts, [3, 2, 1])
        self.assertEqual(frame["constrained_count"], 6)
        self.assertEqual(frame["unconstrained"], [])
        self.assertEqual(frame["dof_table"][1]["dof"], ["tx", "rz"])
        self.assertEqual(frame["dof_table"][2]["dof"], ["ty"])

    def test_axis_primary_leaves_rotation_free(self):
        frame = drf.datum_reference_frame(
            {"feature_type": "axis", "orientation": "z"},
            {"feature_type": "plane", "orientation": "x"},
            {"feature_type": "plane", "orientation": "y"},
        )
        counts = [row["count"] for row in frame["dof_table"]]
        self.assertEqual(counts, [4, 1, 0])
        self.assertEqual(frame["constrained_count"], 5)
        self.assertEqual(frame["unconstrained"], ["tz"])

    def test_precedence_order_changes_the_frame(self):
        frame_primary_z = drf.datum_reference_frame(
            {"feature_type": "plane", "orientation": "z"},
            {"feature_type": "plane", "orientation": "x"},
        )
        frame_primary_x = drf.datum_reference_frame(
            {"feature_type": "plane", "orientation": "x"},
            {"feature_type": "plane", "orientation": "z"},
        )
        self.assertEqual(frame_primary_z["dof_table"][0]["dof"], ["tz", "rx", "ry"])
        self.assertEqual(frame_primary_x["dof_table"][0]["dof"], ["tx", "ry", "rz"])
        self.assertNotEqual(
            frame_primary_z["dof_table"][1]["dof"],
            frame_primary_x["dof_table"][1]["dof"],
        )
        self.assertEqual(frame_primary_z["constrained_count"], 5)
        self.assertEqual(frame_primary_x["constrained_count"], 5)

    def test_redundant_secondary_constrains_nothing(self):
        frame = drf.datum_reference_frame(
            {"feature_type": "plane", "orientation": "z"},
            {"feature_type": "plane", "orientation": "z"},
        )
        self.assertEqual(frame["dof_table"][1]["count"], 0)
        self.assertEqual(frame["dof_table"][1]["dof"], [])
        self.assertEqual(frame["constrained_count"], 3)

    def test_point_primary_then_two_planes(self):
        frame = drf.datum_reference_frame(
            {"feature_type": "point", "orientation": "z"},
            {"feature_type": "plane", "orientation": "z"},
            {"feature_type": "plane", "orientation": "x"},
        )
        counts = [row["count"] for row in frame["dof_table"]]
        self.assertEqual(counts, [3, 2, 1])
        self.assertEqual(frame["unconstrained"], [])

    def test_primary_only_leaves_three_free(self):
        frame = drf.datum_reference_frame(
            {"feature_type": "plane", "orientation": "z"}
        )
        self.assertEqual(frame["constrained_count"], 3)
        self.assertEqual(frame["unconstrained"], ["tx", "ty", "rz"])


class DatumShiftTest(unittest.TestCase):
    def test_rmb_fixed_simulator(self):
        self.assertAlmostEqual(drf.datum_shift("rmb", "hole", 10.0, 10.3), 0.0)
        self.assertAlmostEqual(drf.datum_shift("rmb", "pin", 10.0, 9.8), 0.0)

    def test_mmb_hole_shift(self):
        self.assertAlmostEqual(drf.datum_shift("mmb", "hole", 10.0, 10.3), 0.3)

    def test_mmb_hole_at_boundary_zero(self):
        self.assertAlmostEqual(drf.datum_shift("mmb", "hole", 10.0, 10.0), 0.0)

    def test_mmb_pin_shift(self):
        self.assertAlmostEqual(drf.datum_shift("mmb", "pin", 10.0, 9.8), 0.2)

    def test_lmb_hole_shift(self):
        self.assertAlmostEqual(drf.datum_shift("lmb", "hole", 10.5, 10.2), 0.3)

    def test_lmb_pin_shift(self):
        self.assertAlmostEqual(drf.datum_shift("lmb", "pin", 9.5, 9.8), 0.3)

    def test_mmb_hole_below_boundary_raises(self):
        with self.assertRaises(ValueError):
            drf.datum_shift("mmb", "hole", 10.0, 9.9)

    def test_mmb_pin_above_boundary_raises(self):
        with self.assertRaises(ValueError):
            drf.datum_shift("mmb", "pin", 10.0, 10.1)

    def test_lmb_hole_above_boundary_raises(self):
        with self.assertRaises(ValueError):
            drf.datum_shift("lmb", "hole", 10.5, 10.6)

    def test_lmb_pin_below_boundary_raises(self):
        with self.assertRaises(ValueError):
            drf.datum_shift("lmb", "pin", 9.5, 9.4)

    def test_invalid_modifier_raises(self):
        with self.assertRaises(ValueError):
            drf.datum_shift("mmc", "hole", 10.0, 10.3)

    def test_invalid_feature_kind_raises(self):
        with self.assertRaises(ValueError):
            drf.datum_shift("mmb", "slot", 10.0, 10.3)

    def test_nonpositive_boundary_raises(self):
        with self.assertRaises(ValueError):
            drf.datum_shift("mmb", "hole", 0.0, 10.3)

    def test_nonfinite_raises(self):
        with self.assertRaises(ValueError):
            drf.datum_shift("mmb", "hole", float("nan"), 10.3)
        with self.assertRaises(ValueError):
            drf.datum_shift("mmb", "hole", 10.0, float("inf"))


class FeatureControlFrameTest(unittest.TestCase):
    def test_position_no_datums(self):
        self.assertEqual(drf.feature_control_frame("position", 0.5), POS + "|" + DIAM + "0.5")

    def test_position_single_datum(self):
        self.assertEqual(
            drf.feature_control_frame("position", 0.5, ("A",)),
            POS + "|" + DIAM + "0.5|A",
        )

    def test_position_full_frame_with_modifiers(self):
        self.assertEqual(
            drf.feature_control_frame(
                "position",
                0.5,
                ("A", {"letter": "B", "modifier": "mmb"}, "C"),
                "mmc",
            ),
            POS + "|" + DIAM + "0.5" + MMC + "|A|B" + MMC + "|C",
        )

    def test_flatness_no_diameter(self):
        self.assertEqual(drf.feature_control_frame("flatness", 0.2), "\u2313|0.2")

    def test_perpendicularity_lmb_datum(self):
        self.assertEqual(
            drf.feature_control_frame(
                "perpendicularity", 0.05, ({"letter": "A", "modifier": "lmb"},)
            ),
            "\u22a5|0.05|A" + LMC,
        )

    def test_integer_tolerance_no_trailing_zeros(self):
        self.assertEqual(
            drf.feature_control_frame("position", 10.0), POS + "|" + DIAM + "10"
        )

    def test_float_rounding_stable(self):
        self.assertEqual(
            drf.feature_control_frame("position", 0.1 + 0.2),
            POS + "|" + DIAM + "0.3",
        )

    def test_lmc_and_rfs_tolerance_modifiers(self):
        self.assertEqual(
            drf.feature_control_frame("position", 0.5, tolerance_modifier="lmc"),
            POS + "|" + DIAM + "0.5" + LMC,
        )
        self.assertEqual(
            drf.feature_control_frame("position", 0.5, tolerance_modifier="rfs"),
            POS + "|" + DIAM + "0.5" + RFS,
        )

    def test_diameter_override_off(self):
        self.assertEqual(
            drf.feature_control_frame("position", 0.5, diameter=False),
            POS + "|0.5",
        )

    def test_diameter_override_on_for_flatness(self):
        self.assertEqual(
            drf.feature_control_frame("flatness", 0.2, diameter=True),
            "\u2313|" + DIAM + "0.2",
        )

    def test_unknown_characteristic_raises(self):
        with self.assertRaises(ValueError):
            drf.feature_control_frame("wobble", 0.5)

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            drf.feature_control_frame("position", -0.5)

    def test_nonfinite_tolerance_raises(self):
        with self.assertRaises(ValueError):
            drf.feature_control_frame("position", float("nan"))

    def test_invalid_tolerance_modifier_raises(self):
        with self.assertRaises(ValueError):
            drf.feature_control_frame("position", 0.5, tolerance_modifier="mmb")

    def test_invalid_datum_ref_raises(self):
        with self.assertRaises(ValueError):
            drf.feature_control_frame("position", 0.5, ("",))
        with self.assertRaises(ValueError):
            drf.feature_control_frame(
                "position", 0.5, ({"letter": "A", "modifier": "mmc"},)
            )


class BracketScenarioTest(unittest.TestCase):
    def test_mounting_bracket_frame_and_fcf(self):
        # Bracket: datum A is the base face (plane, normal z), datum B
        # the side face (plane, normal x), datum C the locating hole
        # (axis, z, referenced at MMB). The frame constrains all six
        # DOF; the tertiary hole locates the last translation.
        frame = drf.datum_reference_frame(
            {"feature_type": "plane", "orientation": "z"},
            {"feature_type": "plane", "orientation": "x"},
            {"feature_type": "axis", "orientation": "z", "modifier": "mmb"},
        )
        self.assertEqual(frame["dof_table"][2]["dof"], ["ty"])
        self.assertEqual(frame["constrained_count"], 6)
        self.assertEqual(frame["unconstrained"], [])
        # The locating hole at MMB: actual mating size 10.2 against the
        # 10.0 MMB size gives 0.2 datum shift.
        self.assertAlmostEqual(drf.datum_shift("mmb", "hole", 10.0, 10.2), 0.2)
        # FCF for the hole pattern: position diameter 0.5 at MMC,
        # referenced to A, B, and C at MMB.
        fcf = drf.feature_control_frame(
            "position",
            0.5,
            ("A", "B", {"letter": "C", "modifier": "mmb"}),
            "mmc",
        )
        self.assertEqual(fcf, POS + "|" + DIAM + "0.5" + MMC + "|A|B|C" + MMC)


if __name__ == "__main__":
    unittest.main(verbosity=2)
