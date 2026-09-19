"""Contract tests for the ECSS-E-ST-33-01 clause 4.2.4.1 identification logic."""

import math
import unittest

from e3301_identification_marking_labelling_logic import (
    DEFAULT_ASPECT_RATIO,
    MARKING_METHODS,
    MAX_PENETRATION_FRACTION,
    METHOD_PREFERENCE,
    SURFACE_FINISHES,
    achievable_character_height_mm,
    assess_marking_plan,
    duplicate_identities,
    identity_string,
    method_is_permitted,
    select_marking_route,
    traceability_findings,
    validate_item,
)

# "PN-1234/SN-007" is fourteen characters; a field of 33.6 mm^2 laid out in one
# row at the default aspect then supports exactly 2.00 mm characters.
IDENTITY_CHARACTERS = 14
FIELD_FOR_TWO_MM = 33.6


def housing(**overrides):
    """Return a nominal delivered bare-metal housing."""
    item = {
        "id": "ITEM-01",
        "part_number": "PN-1234",
        "serial_number": "SN-007",
        "surface_finish": "bare-metal",
        "marking_area_mm2": FIELD_FOR_TWO_MM,
        "wall_thickness_mm": 2.0,
        "delivered": True,
    }
    item.update(overrides)
    return item


class ValidationTests(unittest.TestCase):
    def test_item_is_normalised(self):
        record = validate_item(housing(id=" ITEM-01 "))
        self.assertEqual(record["id"], "ITEM-01")
        self.assertTrue(record["delivered"])

    def test_delivered_item_without_a_serial_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(housing(serial_number=None))

    def test_undelivered_item_may_omit_the_serial(self):
        record = validate_item(housing(delivered=False, serial_number=None))
        self.assertIsNone(record["serial_number"])

    def test_unknown_surface_finish_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(housing(surface_finish="galvanised"))

    def test_zero_marking_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(housing(marking_area_mm2=0.0))

    def test_negative_wall_thickness_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(housing(wall_thickness_mm=-1.0))

    def test_non_boolean_delivered_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(housing(delivered="yes"))

    def test_missing_key_rejected(self):
        item = housing()
        del item["part_number"]
        with self.assertRaises(ValueError):
            validate_item(item)

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(["ITEM-01"])

    def test_every_listed_finish_is_accepted(self):
        for finish in SURFACE_FINISHES:
            record = validate_item(housing(surface_finish=finish))
            self.assertEqual(record["surface_finish"], finish)


class IdentityTests(unittest.TestCase):
    def test_delivered_identity_pairs_part_and_serial(self):
        self.assertEqual(identity_string(housing()), "PN-1234/SN-007")

    def test_identity_length_matches_the_fixture(self):
        self.assertEqual(len(identity_string(housing())), IDENTITY_CHARACTERS)

    def test_undelivered_identity_is_the_part_number_alone(self):
        value = identity_string(housing(delivered=False, serial_number=None))
        self.assertEqual(value, "PN-1234")


class CharacterHeightTests(unittest.TestCase):
    def test_field_sized_for_two_millimetre_characters(self):
        height = achievable_character_height_mm(FIELD_FOR_TWO_MM, IDENTITY_CHARACTERS)
        self.assertAlmostEqual(height, 2.0, places=9)

    def test_quadrupling_the_field_doubles_the_height(self):
        one = achievable_character_height_mm(FIELD_FOR_TWO_MM, IDENTITY_CHARACTERS)
        four = achievable_character_height_mm(4.0 * FIELD_FOR_TWO_MM, IDENTITY_CHARACTERS)
        self.assertAlmostEqual(four, 2.0 * one, places=9)

    def test_more_characters_shrink_the_height(self):
        short = achievable_character_height_mm(FIELD_FOR_TWO_MM, 7)
        long_identity = achievable_character_height_mm(FIELD_FOR_TWO_MM, 28)
        self.assertAlmostEqual(short, 2.0 * long_identity, places=9)

    def test_an_even_split_over_two_rows_keeps_the_height(self):
        one_row = achievable_character_height_mm(FIELD_FOR_TWO_MM, 14, rows=1)
        two_rows = achievable_character_height_mm(FIELD_FOR_TWO_MM, 14, rows=2)
        self.assertAlmostEqual(two_rows, one_row, places=9)

    def test_an_odd_split_over_two_rows_wastes_part_of_the_field(self):
        # 15 characters over two rows needs eight columns, so sixteen cells are
        # reserved and the height drops by the square root of 15/16.
        one_row = achievable_character_height_mm(FIELD_FOR_TWO_MM, 15, rows=1)
        two_rows = achievable_character_height_mm(FIELD_FOR_TWO_MM, 15, rows=2)
        self.assertAlmostEqual(two_rows / one_row, math.sqrt(15.0 / 16.0), places=9)

    def test_zero_characters_rejected(self):
        with self.assertRaises(ValueError):
            achievable_character_height_mm(FIELD_FOR_TWO_MM, 0)

    def test_non_integer_character_count_rejected(self):
        with self.assertRaises(ValueError):
            achievable_character_height_mm(FIELD_FOR_TWO_MM, 14.5)

    def test_zero_rows_rejected(self):
        with self.assertRaises(ValueError):
            achievable_character_height_mm(FIELD_FOR_TWO_MM, 14, rows=0)

    def test_default_aspect_ratio_is_point_six(self):
        self.assertAlmostEqual(DEFAULT_ASPECT_RATIO, 0.6, places=12)


class MethodPermissionTests(unittest.TestCase):
    def test_laser_suits_a_bare_metal_housing(self):
        permitted, _ = method_is_permitted("laser-engraving", housing())
        self.assertTrue(permitted)

    def test_etch_does_not_suit_an_anodized_surface(self):
        permitted, reason = method_is_permitted(
            "electrochemical-etch", housing(surface_finish="anodized"))
        self.assertFalse(permitted)
        self.assertIn("does not suit", reason)

    def test_laser_still_suits_an_anodized_surface(self):
        permitted, _ = method_is_permitted(
            "laser-engraving", housing(surface_finish="anodized"))
        self.assertTrue(permitted)

    def test_stamping_is_refused_on_a_thin_wall(self):
        permitted, reason = method_is_permitted(
            "impact-stamping", housing(wall_thickness_mm=1.0))
        self.assertFalse(permitted)
        self.assertIn("into a", reason)

    def test_laser_is_refused_on_a_very_thin_wall(self):
        permitted, _ = method_is_permitted(
            "laser-engraving", housing(wall_thickness_mm=0.4))
        self.assertFalse(permitted)

    def test_penetration_exactly_on_the_wall_allowance_is_permitted(self):
        thickness = MARKING_METHODS["laser-engraving"]["penetration_mm"] / (
            MAX_PENETRATION_FRACTION)
        self.assertAlmostEqual(thickness, 0.5, places=9)
        permitted, _ = method_is_permitted(
            "laser-engraving", housing(wall_thickness_mm=thickness))
        self.assertTrue(permitted)

    def test_penetrating_methods_are_refused_on_a_fracture_critical_item(self):
        for method in ("laser-engraving", "electrochemical-etch", "impact-stamping"):
            permitted, reason = method_is_permitted(
                method, housing(fracture_critical=True))
            self.assertFalse(permitted)
            self.assertIn("stress concentration", reason)

    def test_ink_is_permitted_on_a_fracture_critical_item(self):
        permitted, _ = method_is_permitted("ink-marking", housing(fracture_critical=True))
        self.assertTrue(permitted)

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            method_is_permitted("sand-blast-stencil", housing())


class RouteTests(unittest.TestCase):
    def test_nominal_housing_is_laser_engraved(self):
        route = select_marking_route(housing())
        self.assertEqual(route["method"], "laser-engraving")
        self.assertTrue(route["direct"])

    def test_painted_housing_falls_to_ink(self):
        route = select_marking_route(housing(surface_finish="painted"))
        self.assertEqual(route["method"], "ink-marking")

    def test_thin_walled_housing_falls_to_the_shallower_method(self):
        route = select_marking_route(housing(wall_thickness_mm=0.4))
        self.assertEqual(route["method"], "electrochemical-etch")

    def test_tiny_field_falls_back_to_an_adhesive_label(self):
        route = select_marking_route(housing(marking_area_mm2=0.5))
        self.assertEqual(route["method"], "adhesive-label")
        self.assertFalse(route["direct"])

    def test_field_exactly_at_the_laser_minimum_still_engraves(self):
        minimum = MARKING_METHODS["laser-engraving"]["min_character_height_mm"]
        area = minimum * minimum * IDENTITY_CHARACTERS * DEFAULT_ASPECT_RATIO
        route = select_marking_route(housing(marking_area_mm2=area))
        self.assertAlmostEqual(route["achievable_character_height_mm"], minimum, places=9)
        self.assertEqual(route["method"], "laser-engraving")

    def test_rejected_reasons_are_reported(self):
        route = select_marking_route(housing(surface_finish="composite"))
        self.assertTrue(route["rejected"])
        self.assertEqual(route["method"], "ink-marking")

    def test_preference_order_covers_every_known_method(self):
        self.assertEqual(set(METHOD_PREFERENCE), set(MARKING_METHODS))


class UniquenessAndTraceabilityTests(unittest.TestCase):
    def test_distinct_serials_are_unique(self):
        items = [housing(), housing(id="ITEM-02", serial_number="SN-008")]
        self.assertEqual(duplicate_identities(items), [])

    def test_repeated_identity_is_reported(self):
        items = [housing(), housing(id="ITEM-02")]
        self.assertEqual(duplicate_identities(items), ["PN-1234/SN-007"])

    def test_undelivered_items_do_not_collide(self):
        items = [
            housing(id="ITEM-01", delivered=False, serial_number=None),
            housing(id="ITEM-02", delivered=False, serial_number=None),
        ]
        self.assertEqual(duplicate_identities(items), [])

    def test_missing_parent_is_a_traceability_finding(self):
        items = [housing(id="ITEM-02", serial_number="SN-008", parent_id="ITEM-99")]
        findings = traceability_findings(items)
        self.assertTrue(any("not in the delivery" in f for f in findings))

    def test_parent_without_a_serial_is_a_traceability_finding(self):
        items = [
            housing(id="ITEM-01", delivered=False, serial_number=None),
            housing(id="ITEM-02", serial_number="SN-008", parent_id="ITEM-01"),
        ]
        findings = traceability_findings(items)
        self.assertTrue(any("carries no serial number" in f for f in findings))

    def test_self_parent_is_a_traceability_finding(self):
        items = [housing(parent_id="ITEM-01")]
        findings = traceability_findings(items)
        self.assertTrue(any("its own parent" in f for f in findings))

    def test_repeated_item_identifier_rejected(self):
        with self.assertRaises(ValueError):
            traceability_findings([housing(), housing()])

    def test_good_parent_chain_has_no_findings(self):
        items = [
            housing(id="ITEM-01"),
            housing(id="ITEM-02", serial_number="SN-008", parent_id="ITEM-01"),
        ]
        self.assertEqual(traceability_findings(items), [])


class MarkingPlanTests(unittest.TestCase):
    def test_clean_plan_is_compliant(self):
        items = [housing(), housing(id="ITEM-02", serial_number="SN-008")]
        result = assess_marking_plan(items)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["direct_fraction"], 1.0, places=9)

    def test_label_fallback_is_a_finding(self):
        items = [housing(), housing(id="ITEM-02", serial_number="SN-008",
                                    marking_area_mm2=0.5)]
        result = assess_marking_plan(items)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["direct_fraction"], 0.5, places=9)

    def test_duplicate_identity_reaches_the_plan_findings(self):
        result = assess_marking_plan([housing(), housing(id="ITEM-02")])
        self.assertTrue(any("more than one delivered item" in f
                            for f in result["findings"]))

    def test_plan_counts_every_item(self):
        items = [housing(), housing(id="ITEM-02", serial_number="SN-008")]
        self.assertEqual(assess_marking_plan(items)["item_count"], 2)

    def test_empty_plan_rejected(self):
        with self.assertRaises(ValueError):
            assess_marking_plan([])


if __name__ == "__main__":
    unittest.main()
