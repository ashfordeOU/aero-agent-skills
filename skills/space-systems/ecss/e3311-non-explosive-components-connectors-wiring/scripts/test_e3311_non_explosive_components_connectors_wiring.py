"""Contract tests for the clause 4.10.1-4.10.2 connector and wiring logic."""

import unittest

from e3311_non_explosive_components_connectors_wiring_logic import (
    ACCEPTED,
    COPPER_RESISTIVITY_OHM_M,
    MARGIN_SHORT,
    REJECTED,
    REQUIRED_FEATURES,
    all_fire_margin,
    assess_firing_line,
    conductor_resistance_ohm,
    delivered_current_a,
    loop_resistance_ohm,
    maximum_loop_resistance_ohm,
    minimum_conductor_area_mm2,
    missing_features,
    validate_contact_count,
    validate_non_negative,
    validate_positive,
    voltage_drop_v,
)

LENGTH = 5.0
AREA = 0.5
SOURCE_V = 28.0
SOURCE_R = 0.5
BRIDGE_R = 1.05
ALL_FIRE = 3.5


def features(**overrides):
    declared = {name: True for name in REQUIRED_FEATURES}
    declared.update(overrides)
    return declared


class ValidationTests(unittest.TestCase):
    def test_zero_rejected_where_positive_required(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0)

    def test_negative_rejected_where_non_negative_required(self):
        with self.assertRaises(ValueError):
            validate_non_negative(-1e-9)

    def test_zero_accepted_where_non_negative_required(self):
        self.assertAlmostEqual(validate_non_negative(0), 0.0, places=9)

    def test_boolean_rejected_as_a_number(self):
        with self.assertRaises(ValueError):
            validate_positive(True)

    def test_text_rejected_as_a_number(self):
        with self.assertRaises(ValueError):
            validate_positive("0.5")

    def test_infinite_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(float("inf"))

    def test_float_contact_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_count(2.0)

    def test_negative_contact_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_count(-1)

    def test_zero_contacts_accepted(self):
        self.assertEqual(validate_contact_count(0), 0)


class ResistanceTests(unittest.TestCase):
    def test_conductor_resistance_from_geometry(self):
        expected = COPPER_RESISTIVITY_OHM_M * LENGTH / (AREA * 1e-6)
        self.assertAlmostEqual(
            conductor_resistance_ohm(LENGTH, AREA), expected, places=9
        )

    def test_resistance_scales_with_length(self):
        self.assertAlmostEqual(
            conductor_resistance_ohm(2.0 * LENGTH, AREA),
            2.0 * conductor_resistance_ohm(LENGTH, AREA),
            places=9,
        )

    def test_resistance_falls_with_area(self):
        self.assertAlmostEqual(
            conductor_resistance_ohm(LENGTH, 2.0 * AREA),
            0.5 * conductor_resistance_ohm(LENGTH, AREA),
            places=9,
        )

    def test_loop_counts_both_conductors(self):
        self.assertAlmostEqual(
            loop_resistance_ohm(LENGTH, AREA, contacts=0),
            2.0 * conductor_resistance_ohm(LENGTH, AREA),
            places=9,
        )

    def test_contacts_add_to_the_loop(self):
        bare = loop_resistance_ohm(LENGTH, AREA, contacts=0)
        with_contacts = loop_resistance_ohm(
            LENGTH, AREA, contacts=4, contact_resistance_ohm=0.01
        )
        self.assertAlmostEqual(with_contacts - bare, 0.04, places=9)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            conductor_resistance_ohm(LENGTH, 0.0)

    def test_zero_length_rejected(self):
        with self.assertRaises(ValueError):
            conductor_resistance_ohm(0.0, AREA)


class CurrentTests(unittest.TestCase):
    def test_delivered_current_is_the_series_divider(self):
        self.assertAlmostEqual(
            delivered_current_a(10.0, 0.5, 0.5, 1.0), 5.0, places=9
        )

    def test_a_larger_loop_delivers_less(self):
        self.assertLess(
            delivered_current_a(SOURCE_V, SOURCE_R, 5.0, BRIDGE_R),
            delivered_current_a(SOURCE_V, SOURCE_R, 0.5, BRIDGE_R),
        )

    def test_zero_bridgewire_rejected(self):
        with self.assertRaises(ValueError):
            delivered_current_a(SOURCE_V, SOURCE_R, 0.5, 0.0)

    def test_voltage_drop_follows_ohms_law(self):
        self.assertAlmostEqual(voltage_drop_v(2.0, 1.5), 3.0, places=9)

    def test_no_current_drops_no_voltage(self):
        self.assertAlmostEqual(voltage_drop_v(0.0, 1.5), 0.0, places=9)

    def test_margin_at_the_all_fire_current_is_one(self):
        self.assertAlmostEqual(all_fire_margin(ALL_FIRE, ALL_FIRE), 1.0, places=9)

    def test_margin_scales_with_delivered_current(self):
        self.assertAlmostEqual(all_fire_margin(7.0, ALL_FIRE), 2.0, places=9)

    def test_zero_all_fire_current_rejected(self):
        with self.assertRaises(ValueError):
            all_fire_margin(5.0, 0.0)


class SizingTests(unittest.TestCase):
    def test_maximum_loop_resistance_delivers_exactly_the_margin(self):
        allowed = maximum_loop_resistance_ohm(28.0, 0.5, 1.0, 3.5, margin=1.5)
        delivered = delivered_current_a(28.0, 0.5, allowed, 1.0)
        self.assertAlmostEqual(delivered, 1.5 * 3.5, places=9)

    def test_an_impossible_margin_admits_no_loop(self):
        self.assertIsNone(
            maximum_loop_resistance_ohm(5.0, 0.5, 1.0, 10.0, margin=1.5)
        )

    def test_minimum_area_delivers_the_margin(self):
        area = minimum_conductor_area_mm2(
            LENGTH, 28.0, 0.5, 1.0, 3.5, margin=1.5, contacts=0
        )
        loop = loop_resistance_ohm(LENGTH, area, contacts=0)
        delivered = delivered_current_a(28.0, 0.5, loop, 1.0)
        self.assertAlmostEqual(delivered, 1.5 * 3.5, places=9)

    def test_a_longer_run_needs_more_copper(self):
        short = minimum_conductor_area_mm2(2.0, 28.0, 0.5, 1.0, 3.5, contacts=0)
        long = minimum_conductor_area_mm2(8.0, 28.0, 0.5, 1.0, 3.5, contacts=0)
        self.assertGreater(long, short)

    def test_contacts_spending_the_budget_admit_no_area(self):
        self.assertIsNone(
            minimum_conductor_area_mm2(
                LENGTH, 28.0, 0.5, 1.0, 3.5, contacts=200, contact_resistance_ohm=0.1
            )
        )

    def test_an_impossible_margin_admits_no_area(self):
        self.assertIsNone(
            minimum_conductor_area_mm2(LENGTH, 5.0, 0.5, 1.0, 10.0, margin=1.5)
        )


class FeatureTests(unittest.TestCase):
    def test_a_full_declaration_misses_nothing(self):
        self.assertEqual(missing_features(features()), [])

    def test_each_feature_is_detected_when_dropped(self):
        for name in REQUIRED_FEATURES:
            self.assertIn(name, missing_features(features(**{name: False})))

    def test_an_undeclared_feature_counts_as_absent(self):
        declared = features()
        del declared["keyed_against_mismating"]
        self.assertIn("keyed_against_mismating", missing_features(declared))

    def test_a_non_boolean_declaration_rejected(self):
        with self.assertRaises(ValueError):
            missing_features(features(twisted_pair="yes"))

    def test_a_non_mapping_declaration_rejected(self):
        with self.assertRaises(ValueError):
            missing_features(["twisted_pair"])


class AssessTests(unittest.TestCase):
    def test_a_sound_firing_line_is_accepted(self):
        result = assess_firing_line(
            LENGTH, AREA, SOURCE_V, SOURCE_R, BRIDGE_R, ALL_FIRE, features()
        )
        self.assertEqual(result["verdict"], ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_a_line_exactly_on_its_margin_is_accepted(self):
        allowed = maximum_loop_resistance_ohm(28.0, 0.5, 1.0, 3.5, margin=1.5)
        area = minimum_conductor_area_mm2(
            LENGTH, 28.0, 0.5, 1.0, 3.5, margin=1.5, contacts=0
        )
        result = assess_firing_line(
            LENGTH, area, 28.0, 0.5, 1.0, 3.5, features(), margin=1.5, contacts=0
        )
        self.assertAlmostEqual(result["loop_resistance_ohm"], allowed, places=9)
        self.assertAlmostEqual(result["all_fire_margin"], 1.5, places=9)
        self.assertEqual(result["verdict"], ACCEPTED)

    def test_a_thin_conductor_is_margin_short(self):
        result = assess_firing_line(
            LENGTH, 0.032, SOURCE_V, SOURCE_R, BRIDGE_R, ALL_FIRE, features()
        )
        self.assertEqual(result["verdict"], MARGIN_SHORT)
        self.assertTrue(any("required margin" in f for f in result["findings"]))

    def test_a_margin_short_line_is_told_the_cross_section(self):
        result = assess_firing_line(
            LENGTH, 0.032, SOURCE_V, SOURCE_R, BRIDGE_R, ALL_FIRE, features()
        )
        self.assertTrue(any("reaches the margin" in f for f in result["findings"]))

    def test_the_named_cross_section_actually_reaches_the_margin(self):
        result = assess_firing_line(
            LENGTH, 0.032, SOURCE_V, SOURCE_R, BRIDGE_R, ALL_FIRE, features()
        )
        fixed = assess_firing_line(
            LENGTH,
            result["minimum_conductor_area_mm2"],
            SOURCE_V,
            SOURCE_R,
            BRIDGE_R,
            ALL_FIRE,
            features(),
        )
        self.assertEqual(fixed["verdict"], ACCEPTED)

    def test_a_line_that_cannot_fire_at_all_is_rejected(self):
        result = assess_firing_line(
            LENGTH, 0.0005, SOURCE_V, SOURCE_R, BRIDGE_R, ALL_FIRE, features()
        )
        self.assertEqual(result["verdict"], REJECTED)
        self.assertTrue(
            any("not reached at all" in f for f in result["findings"])
        )

    def test_an_unreachable_margin_says_the_circuit_has_to_change(self):
        result = assess_firing_line(
            LENGTH, AREA, 5.0, 0.5, 1.0, 10.0, features(), margin=1.5
        )
        self.assertTrue(
            any("firing circuit itself has to change" in f for f in result["findings"])
        )

    def test_an_unkeyed_connector_is_rejected_even_when_it_fires(self):
        result = assess_firing_line(
            LENGTH,
            AREA,
            SOURCE_V,
            SOURCE_R,
            BRIDGE_R,
            ALL_FIRE,
            features(keyed_against_mismating=False),
        )
        self.assertEqual(result["verdict"], REJECTED)
        self.assertIn("keyed_against_mismating", result["missing_features"])

    def test_an_unsegregated_run_is_reported(self):
        result = assess_firing_line(
            LENGTH,
            AREA,
            SOURCE_V,
            SOURCE_R,
            BRIDGE_R,
            ALL_FIRE,
            features(segregated_from_other_harness=False),
        )
        self.assertTrue(
            any("segregated_from_other_harness" in f for f in result["findings"])
        )

    def test_harness_voltage_drop_is_carried_in_the_result(self):
        result = assess_firing_line(
            LENGTH, AREA, SOURCE_V, SOURCE_R, BRIDGE_R, ALL_FIRE, features()
        )
        self.assertAlmostEqual(
            result["harness_voltage_drop_v"],
            result["delivered_current_a"] * result["loop_resistance_ohm"],
            places=9,
        )

    def test_contact_resistance_moves_the_verdict(self):
        clean = assess_firing_line(
            LENGTH, 0.1, SOURCE_V, SOURCE_R, BRIDGE_R, ALL_FIRE, features(),
            contacts=4, contact_resistance_ohm=0.0,
        )
        dirty = assess_firing_line(
            LENGTH, 0.1, SOURCE_V, SOURCE_R, BRIDGE_R, ALL_FIRE, features(),
            contacts=4, contact_resistance_ohm=0.5,
        )
        self.assertGreater(clean["all_fire_margin"], dirty["all_fire_margin"])

    def test_bad_margin_rejected(self):
        with self.assertRaises(ValueError):
            assess_firing_line(
                LENGTH, AREA, SOURCE_V, SOURCE_R, BRIDGE_R, ALL_FIRE, features(),
                margin=0.0,
            )

    def test_bad_feature_declaration_rejected(self):
        with self.assertRaises(ValueError):
            assess_firing_line(
                LENGTH, AREA, SOURCE_V, SOURCE_R, BRIDGE_R, ALL_FIRE, "all good"
            )


if __name__ == "__main__":
    unittest.main()
