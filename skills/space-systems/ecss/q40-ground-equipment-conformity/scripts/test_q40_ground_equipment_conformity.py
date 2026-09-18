"""Contract test for the q40-ground-equipment-conformity leaf (unittest)."""

import unittest

from q40_ground_equipment_conformity_logic import (
    PRESSURE_VOLUME_THRESHOLD_BAR_LITRE,
    applicable_instruments,
    assess_conformity,
    assess_equipment_set,
    ce_marking_required,
    declaration_blockers,
    notified_body_required,
    pressure_volume_product,
    validate_item,
)


def item(iid="GSE-1", **kw):
    record = {
        "id": iid,
        "contains_electronics": True,
        "ac_supply_v": 230.0,
        "responsible_entity": "the supplying organisation",
        "technical_file_ref": "TF-1",
        "harmonised_standards": ["the applied electrical safety standard"],
    }
    record.update(kw)
    return record


class TestValidateItem(unittest.TestCase):
    def test_a_complete_item_normalises(self):
        norm = validate_item(item())
        self.assertEqual(norm["id"], "GSE-1")
        self.assertAlmostEqual(norm["ac_supply_v"], 230.0, places=9)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_item("GSE-1")

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_item(item(""))

    def test_a_negative_pressure_raises(self):
        with self.assertRaises(ValueError):
            validate_item(item(design_pressure_bar=-2.0))

    def test_a_non_numeric_volume_raises(self):
        with self.assertRaises(ValueError):
            validate_item(item(volume_litre="ten litres"))

    def test_a_boolean_voltage_raises(self):
        with self.assertRaises(ValueError):
            validate_item(item(ac_supply_v=True))

    def test_an_unknown_explosive_zone_raises(self):
        with self.assertRaises(ValueError):
            validate_item(item(explosive_atmosphere_zone="zone-9"))

    def test_a_non_boolean_machinery_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_item(item(powered_moving_assembly="yes"))

    def test_non_sequence_standards_raise(self):
        with self.assertRaises(ValueError):
            validate_item(item(harmonised_standards="one standard"))

    def test_the_explosive_zone_defaults_to_none(self):
        self.assertEqual(validate_item(item())["explosive_atmosphere_zone"], "none")


class TestApplicableInstruments(unittest.TestCase):
    def test_a_mains_electronics_enclosure_picks_up_two_instruments(self):
        found = applicable_instruments(item())
        self.assertIn("low-voltage", found)
        self.assertIn("electromagnetic-compatibility", found)

    def test_a_powered_moving_assembly_is_machinery(self):
        self.assertIn("machinery",
                      applicable_instruments(item(powered_moving_assembly=True)))

    def test_a_lifting_accessory_is_named_in_its_own_right(self):
        self.assertIn("lifting-accessory",
                      applicable_instruments(item(lifting_accessory=True)))

    def test_an_explosive_atmosphere_zone_adds_its_instrument(self):
        self.assertIn("equipment-for-explosive-atmospheres",
                      applicable_instruments(item(explosive_atmosphere_zone="zone-2")))

    def test_an_extra_low_voltage_supply_is_outside_the_band(self):
        found = applicable_instruments(item(ac_supply_v=24.0, contains_electronics=False))
        self.assertNotIn("low-voltage", found)

    def test_a_dc_supply_inside_its_band_is_low_voltage(self):
        found = applicable_instruments(item(ac_supply_v=0.0, dc_supply_v=110.0))
        self.assertIn("low-voltage", found)

    def test_a_dc_supply_below_its_band_is_not_low_voltage(self):
        found = applicable_instruments(item(ac_supply_v=0.0, dc_supply_v=48.0,
                                            contains_electronics=False))
        self.assertEqual(found, [])


class TestPressureRoute(unittest.TestCase):
    def test_the_pressure_volume_product_is_the_plain_product(self):
        value = pressure_volume_product(item(design_pressure_bar=8.0, volume_litre=20.0))
        self.assertAlmostEqual(value, 160.0, places=9)

    def test_a_product_above_the_threshold_is_pressure_equipment(self):
        found = applicable_instruments(item(design_pressure_bar=8.0, volume_litre=20.0))
        self.assertIn("pressure-equipment", found)

    def test_a_product_exactly_on_the_threshold_falls_to_sound_practice(self):
        record = item(design_pressure_bar=5.0, volume_litre=10.0)
        self.assertAlmostEqual(pressure_volume_product(record),
                               PRESSURE_VOLUME_THRESHOLD_BAR_LITRE, places=9)
        found = applicable_instruments(record)
        self.assertIn("sound-engineering-practice", found)
        self.assertNotIn("pressure-equipment", found)

    def test_a_pressure_exactly_on_the_lower_bound_is_not_pressure_equipment(self):
        found = applicable_instruments(item(design_pressure_bar=0.5, volume_litre=500.0))
        self.assertNotIn("pressure-equipment", found)
        self.assertNotIn("sound-engineering-practice", found)

    def test_a_vessel_just_over_the_pressure_bound_enters_the_screen(self):
        found = applicable_instruments(item(design_pressure_bar=2.0, volume_litre=5.0))
        self.assertIn("sound-engineering-practice", found)


class TestRouteAndMarking(unittest.TestCase):
    def test_a_self_declarable_item_needs_no_notified_body(self):
        self.assertFalse(notified_body_required(item()))

    def test_pressure_equipment_needs_a_notified_body(self):
        self.assertTrue(notified_body_required(
            item(design_pressure_bar=8.0, volume_litre=20.0)))

    def test_annex_iv_machinery_needs_a_notified_body(self):
        self.assertTrue(notified_body_required(item(annex_iv_machinery=True)))

    def test_a_zone_one_item_needs_a_notified_body(self):
        self.assertTrue(notified_body_required(item(explosive_atmosphere_zone="zone-1")))

    def test_a_zone_two_item_may_be_self_declared(self):
        self.assertFalse(notified_body_required(item(explosive_atmosphere_zone="zone-2")))

    def test_an_item_under_an_instrument_carries_the_mark(self):
        self.assertTrue(ce_marking_required(item()))

    def test_sound_engineering_practice_alone_carries_no_mark(self):
        record = item(design_pressure_bar=2.0, volume_litre=5.0,
                      ac_supply_v=0.0, contains_electronics=False)
        self.assertFalse(ce_marking_required(record))

    def test_an_item_under_nothing_carries_no_mark(self):
        self.assertFalse(ce_marking_required(
            item(ac_supply_v=0.0, contains_electronics=False)))


class TestDeclaration(unittest.TestCase):
    def test_a_complete_item_is_declarable(self):
        report = assess_conformity(item())
        self.assertEqual(report["disposition"], "declaration-issuable")
        self.assertEqual(report["blockers"], [])
        self.assertEqual(report["conformity_route"], "manufacturer-self-assessment")

    def test_a_missing_responsible_entity_blocks_the_declaration(self):
        blockers = declaration_blockers(item(responsible_entity=None))
        self.assertTrue(any("responsible entity" in b for b in blockers))

    def test_a_missing_technical_file_blocks_the_declaration(self):
        blockers = declaration_blockers(item(technical_file_ref=None))
        self.assertTrue(any("technical file" in b for b in blockers))

    def test_a_notified_body_route_without_a_certificate_is_blocked(self):
        blockers = declaration_blockers(item(design_pressure_bar=8.0, volume_litre=20.0))
        self.assertTrue(any("notified body" in b for b in blockers))

    def test_a_notified_body_route_with_a_certificate_is_declarable(self):
        report = assess_conformity(item(design_pressure_bar=8.0, volume_litre=20.0,
                                        notified_body_certificate_ref="NB-1234-01"))
        self.assertTrue(report["declaration_issuable"])
        self.assertEqual(report["conformity_route"], "notified-body-assessment")

    def test_a_self_declared_route_needs_its_standards_listed(self):
        blockers = declaration_blockers(item(harmonised_standards=[]))
        self.assertTrue(any("standards applied" in b for b in blockers))

    def test_sound_practice_only_has_no_declaration_to_issue(self):
        report = assess_conformity(item(design_pressure_bar=2.0, volume_litre=5.0,
                                        ac_supply_v=0.0, contains_electronics=False))
        self.assertEqual(report["conformity_route"], "sound-engineering-practice")
        self.assertFalse(report["declaration_issuable"])

    def test_an_item_under_nothing_declares_nothing(self):
        report = assess_conformity(item(ac_supply_v=0.0, contains_electronics=False))
        self.assertEqual(report["conformity_route"], "no-route-identified")
        self.assertTrue(any("nothing is being declared" in b for b in report["blockers"]))


class TestEquipmentSet(unittest.TestCase):
    def test_a_clean_set_is_declarable(self):
        rollup = assess_equipment_set([item("GSE-1"), item("GSE-2")])
        self.assertEqual(rollup["disposition"], "set-declarable")
        self.assertAlmostEqual(rollup["issuable_ratio"], 1.0, places=9)

    def test_a_blocked_item_blocks_the_set(self):
        rollup = assess_equipment_set([item("GSE-1"),
                                       item("GSE-2", technical_file_ref=None)])
        self.assertEqual(rollup["disposition"], "set-blocked")
        self.assertEqual(rollup["blocked_ids"], ["GSE-2"])
        self.assertAlmostEqual(rollup["issuable_ratio"], 0.5, places=9)

    def test_third_party_items_are_listed_separately(self):
        rollup = assess_equipment_set([item("GSE-1"),
                                       item("GSE-2", design_pressure_bar=8.0,
                                            volume_litre=20.0,
                                            notified_body_certificate_ref="NB-1")])
        self.assertEqual(rollup["notified_body_ids"], ["GSE-2"])

    def test_duplicate_item_ids_raise(self):
        with self.assertRaises(ValueError):
            assess_equipment_set([item("GSE-1"), item("GSE-1")])

    def test_an_empty_set_raises(self):
        with self.assertRaises(ValueError):
            assess_equipment_set([])


if __name__ == "__main__":
    unittest.main()
