"""Contract test for the wire and terminal control leaf (stdlib unittest)."""

import unittest

from q7026_wire_and_terminal_control_logic import (
    BRUSH_FINDING,
    CONDUCTOR_OUT_OF_RANGE,
    EXPOSED_FINDING,
    MAX_EXPOSED_CONDUCTOR_MM,
    QUALIFIED,
    STRIP_IN_WINDOW,
    STRIP_LONG,
    STRIP_SHORT,
    STRIP_TOLERANCE_MM,
    TERMINAL_NOT_LISTED,
    assess_item,
    assess_lot,
    assess_strip,
    brush_free,
    build_qualified_list,
    combination_verdict,
    exposed_conductor,
    strip_length_window,
    validate_item,
    validate_qualified_entry,
)


def qualified_entry(**kw):
    e = {
        "terminal_part_number": "ESA-M39029-58-360",
        "conductor_csa_min_mm2": 0.20,
        "conductor_csa_max_mm2": 0.60,
        "barrel_length_mm": 3.2,
        "insulation_support_gap_mm": 0.5,
    }
    e.update(kw)
    return e


def item(**kw):
    i = {
        "item_id": "W12-P3-7",
        "terminal_part_number": "ESA-M39029-58-360",
        "conductor_csa_mm2": 0.38,
        "measured_strip_length_mm": 3.7,
        "strand_count": 19,
        "strands_in_barrel": 19,
    }
    i.update(kw)
    return i


def index():
    return build_qualified_list([qualified_entry()])


class TestQualifiedList(unittest.TestCase):
    def test_the_list_indexes_by_terminal(self):
        self.assertIn("ESA-M39029-58-360", index())

    def test_the_part_number_folds_case(self):
        built = build_qualified_list(
            [qualified_entry(terminal_part_number="esa-m39029-58-360")]
        )
        self.assertIn("ESA-M39029-58-360", built)

    def test_a_duplicate_terminal_raises(self):
        with self.assertRaises(ValueError):
            build_qualified_list([qualified_entry(), qualified_entry()])

    def test_an_inverted_range_raises(self):
        with self.assertRaises(ValueError):
            validate_qualified_entry(
                qualified_entry(conductor_csa_min_mm2=0.6, conductor_csa_max_mm2=0.2)
            )

    def test_a_zero_barrel_length_raises(self):
        with self.assertRaises(ValueError):
            validate_qualified_entry(qualified_entry(barrel_length_mm=0.0))

    def test_an_empty_list_raises(self):
        with self.assertRaises(ValueError):
            build_qualified_list([])

    def test_a_non_mapping_entry_raises(self):
        with self.assertRaises(ValueError):
            validate_qualified_entry("ESA-M39029-58-360")


class TestCombination(unittest.TestCase):
    def test_a_listed_pairing_inside_the_range_is_qualified(self):
        self.assertEqual(combination_verdict(index(), item())["verdict"], QUALIFIED)

    def test_an_unlisted_terminal_is_not_qualified(self):
        result = combination_verdict(index(), item(terminal_part_number="XX-999"))
        self.assertEqual(result["verdict"], TERMINAL_NOT_LISTED)
        self.assertIsNone(result["entry"])

    def test_a_conductor_below_the_range_is_refused(self):
        self.assertEqual(
            combination_verdict(index(), item(conductor_csa_mm2=0.10))["verdict"],
            CONDUCTOR_OUT_OF_RANGE,
        )

    def test_a_conductor_above_the_range_is_refused(self):
        self.assertEqual(
            combination_verdict(index(), item(conductor_csa_mm2=0.95))["verdict"],
            CONDUCTOR_OUT_OF_RANGE,
        )

    def test_a_conductor_exactly_on_the_low_bound_is_qualified(self):
        self.assertEqual(
            combination_verdict(index(), item(conductor_csa_mm2=0.20))["verdict"],
            QUALIFIED,
        )

    def test_a_conductor_exactly_on_the_high_bound_is_qualified(self):
        self.assertEqual(
            combination_verdict(index(), item(conductor_csa_mm2=0.60))["verdict"],
            QUALIFIED,
        )


class TestStripWindow(unittest.TestCase):
    def test_the_nominal_is_barrel_plus_stand_off(self):
        window = strip_length_window(3.2, 0.5)
        self.assertAlmostEqual(window["nominal_mm"], 3.7, places=9)

    def test_the_window_is_symmetric_about_the_nominal(self):
        window = strip_length_window(3.2, 0.5)
        self.assertAlmostEqual(
            window["maximum_mm"] - window["nominal_mm"], STRIP_TOLERANCE_MM, places=9
        )
        self.assertAlmostEqual(
            window["nominal_mm"] - window["minimum_mm"], STRIP_TOLERANCE_MM, places=9
        )

    def test_a_zero_tolerance_raises(self):
        with self.assertRaises(ValueError):
            strip_length_window(3.2, 0.5, tolerance_mm=0.0)

    def test_a_zero_barrel_raises(self):
        with self.assertRaises(ValueError):
            strip_length_window(0.0, 0.5)

    def test_a_nominal_cut_is_in_window(self):
        window = strip_length_window(3.2, 0.5)
        self.assertEqual(assess_strip(window["nominal_mm"], window), STRIP_IN_WINDOW)

    def test_a_cut_exactly_on_the_lower_bound_is_in_window(self):
        window = strip_length_window(3.2, 0.5)
        self.assertEqual(assess_strip(window["minimum_mm"], window), STRIP_IN_WINDOW)

    def test_a_cut_exactly_on_the_upper_bound_is_in_window(self):
        window = strip_length_window(3.2, 0.5)
        self.assertEqual(assess_strip(window["maximum_mm"], window), STRIP_IN_WINDOW)

    def test_an_under_cut_strip_is_short(self):
        window = strip_length_window(3.2, 0.5)
        self.assertEqual(
            assess_strip(window["minimum_mm"] - 0.5, window), STRIP_SHORT
        )

    def test_an_over_cut_strip_is_long(self):
        window = strip_length_window(3.2, 0.5)
        self.assertEqual(assess_strip(window["maximum_mm"] + 0.5, window), STRIP_LONG)

    def test_a_non_mapping_window_raises(self):
        with self.assertRaises(ValueError):
            assess_strip(3.7, (3.3, 4.1))


class TestExposedConductor(unittest.TestCase):
    def test_exposure_is_the_strip_past_the_barrel(self):
        self.assertAlmostEqual(exposed_conductor(3.7, 3.2), 0.5, places=9)

    def test_a_strip_inside_the_barrel_exposes_nothing(self):
        self.assertAlmostEqual(exposed_conductor(3.0, 3.2), 0.0, places=9)

    def test_exposure_exactly_at_the_limit_is_not_a_finding(self):
        entry = qualified_entry(insulation_support_gap_mm=MAX_EXPOSED_CONDUCTOR_MM)
        built = build_qualified_list([entry])
        strip = entry["barrel_length_mm"] + MAX_EXPOSED_CONDUCTOR_MM
        result = assess_item(built, item(measured_strip_length_mm=strip))
        self.assertAlmostEqual(
            result["exposed_conductor_mm"], MAX_EXPOSED_CONDUCTOR_MM, places=9
        )
        self.assertNotIn(EXPOSED_FINDING, result["findings"])

    def test_a_negative_strip_length_raises(self):
        with self.assertRaises(ValueError):
            exposed_conductor(-1.0, 3.2)


class TestBrush(unittest.TestCase):
    def test_all_strands_in_the_barrel_is_brush_free(self):
        self.assertTrue(brush_free(item()))

    def test_one_strand_outside_is_a_brush(self):
        self.assertFalse(brush_free(item(strands_in_barrel=18)))

    def test_more_strands_in_the_barrel_than_exist_raises(self):
        with self.assertRaises(ValueError):
            validate_item(item(strand_count=19, strands_in_barrel=20))

    def test_a_non_integer_strand_count_raises(self):
        with self.assertRaises(ValueError):
            validate_item(item(strand_count=19.0))

    def test_a_blank_item_id_raises(self):
        with self.assertRaises(ValueError):
            validate_item(item(item_id="  "))


class TestItemAssessment(unittest.TestCase):
    def test_a_sound_item_is_acceptable(self):
        result = assess_item(index(), item())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["strip_verdict"], STRIP_IN_WINDOW)

    def test_an_unlisted_terminal_stops_before_the_strip_check(self):
        result = assess_item(index(), item(terminal_part_number="XX-999"))
        self.assertIsNone(result["strip_verdict"])
        self.assertIn(TERMINAL_NOT_LISTED, result["findings"])

    def test_a_short_strip_is_reported(self):
        result = assess_item(index(), item(measured_strip_length_mm=2.0))
        self.assertIn(STRIP_SHORT, result["findings"])

    def test_a_long_strip_also_reports_bare_conductor(self):
        result = assess_item(index(), item(measured_strip_length_mm=6.0))
        self.assertIn(STRIP_LONG, result["findings"])
        self.assertIn(EXPOSED_FINDING, result["findings"])

    def test_a_brush_is_reported_on_an_otherwise_good_item(self):
        result = assess_item(index(), item(strands_in_barrel=17))
        self.assertIn(BRUSH_FINDING, result["findings"])
        self.assertFalse(result["acceptable"])


class TestLot(unittest.TestCase):
    def test_a_clean_lot_reports_clean(self):
        report = assess_lot([qualified_entry()], [item(), item(item_id="W12-P3-8")])
        self.assertTrue(report["clean"])
        self.assertEqual(len(report["accepted"]), 2)

    def test_a_bad_item_is_rejected_and_named(self):
        report = assess_lot(
            [qualified_entry()],
            [item(), item(item_id="BAD1", measured_strip_length_mm=6.0)],
        )
        self.assertIn("BAD1", report["rejected"])
        self.assertTrue(any(f.startswith("BAD1: ") for f in report["findings"]))

    def test_an_empty_lot_raises(self):
        with self.assertRaises(ValueError):
            assess_lot([qualified_entry()], [])

    def test_a_non_list_lot_raises(self):
        with self.assertRaises(ValueError):
            assess_lot([qualified_entry()], item())


if __name__ == "__main__":
    unittest.main()
