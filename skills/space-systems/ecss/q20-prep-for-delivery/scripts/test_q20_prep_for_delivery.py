"""Contract tests for the clause 5.7.4 preparation-for-delivery logic."""

import unittest

from q20_prep_for_delivery_logic import (
    BASE_LABEL_FIELDS,
    BASE_PROTECTION_MEANS,
    STANDARD_GRAVITY,
    assess_delivery_preparation,
    cushion_stress_findings,
    cushion_thickness_mm,
    desiccant_units,
    label_findings,
    normalize_token,
    protection_findings,
    required_label_fields,
    required_protection_means,
    static_stress_kpa,
    validate_item,
)

PLAIN_ITEM = {"mass_kg": 12.0, "bearing_area_mm2": 40000.0, "fragility_g": 25.0}


def _spec(**overrides):
    item = dict(PLAIN_ITEM)
    item.update(overrides.pop("item", {}))
    validated = validate_item(item)
    spec = {
        "item": item,
        "drop_height_mm": 750.0,
        "cushion": {
            "efficiency": 0.4,
            "thickness_mm": 90.0,
            "rated_min_kpa": 1.0,
            "rated_max_kpa": 20.0,
        },
        "applied_label_fields": list(required_label_fields(validated)),
        "provided_protection": list(required_protection_means(validated)),
    }
    spec.update(overrides)
    return spec


class NormalizeTokenTests(unittest.TestCase):
    def test_separators_fold_together(self):
        self.assertEqual(normalize_token("ESD_Sensitive Symbol"), "esd-sensitive-symbol")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token(" ")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token(None)


class ValidateItemTests(unittest.TestCase):
    def test_states_default_to_false(self):
        record = validate_item(PLAIN_ITEM)
        self.assertFalse(record["esd_sensitive"])
        self.assertFalse(record["hazardous"])

    def test_missing_mass_rejected(self):
        with self.assertRaises(ValueError):
            validate_item({"bearing_area_mm2": 100.0, "fragility_g": 25.0})

    def test_zero_bearing_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_item({"mass_kg": 1.0, "bearing_area_mm2": 0.0, "fragility_g": 25.0})

    def test_non_boolean_state_rejected(self):
        item = dict(PLAIN_ITEM)
        item["esd_sensitive"] = "yes"
        with self.assertRaises(ValueError):
            validate_item(item)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(["mass_kg"])


class StaticStressTests(unittest.TestCase):
    def test_stress_is_weight_over_area(self):
        value = static_stress_kpa(12.0, 40000.0)
        self.assertAlmostEqual(value, 12.0 * STANDARD_GRAVITY / 40000.0 * 1000.0, places=9)

    def test_doubling_area_halves_the_stress(self):
        one = static_stress_kpa(10.0, 10000.0)
        two = static_stress_kpa(10.0, 20000.0)
        self.assertAlmostEqual(two * 2.0, one, places=9)

    def test_negative_mass_rejected(self):
        with self.assertRaises(ValueError):
            static_stress_kpa(-1.0, 100.0)


class CushionThicknessTests(unittest.TestCase):
    def test_thickness_from_drop_and_fragility(self):
        self.assertAlmostEqual(cushion_thickness_mm(750.0, 25.0, 0.4), 75.0, places=9)

    def test_tougher_item_needs_less_cushion(self):
        soft = cushion_thickness_mm(750.0, 15.0, 0.5)
        tough = cushion_thickness_mm(750.0, 45.0, 0.5)
        self.assertAlmostEqual(tough * 3.0, soft, places=9)

    def test_efficiency_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            cushion_thickness_mm(750.0, 25.0, 1.4)

    def test_zero_efficiency_rejected(self):
        with self.assertRaises(ValueError):
            cushion_thickness_mm(750.0, 25.0, 0.0)

    def test_zero_drop_height_rejected(self):
        with self.assertRaises(ValueError):
            cushion_thickness_mm(0.0, 25.0, 0.4)


class CushionStressWindowTests(unittest.TestCase):
    def test_inside_window_is_clean(self):
        self.assertEqual(cushion_stress_findings(5.0, 1.0, 20.0), [])

    def test_below_window_is_a_finding(self):
        self.assertEqual(len(cushion_stress_findings(0.5, 1.0, 20.0)), 1)

    def test_above_window_is_a_finding(self):
        findings = cushion_stress_findings(25.0, 1.0, 20.0)
        self.assertIn("above", findings[0])

    def test_exactly_on_the_edge_is_accepted(self):
        self.assertEqual(cushion_stress_findings(20.0, 1.0, 20.0), [])

    def test_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            cushion_stress_findings(5.0, 20.0, 1.0)


class DesiccantTests(unittest.TestCase):
    def test_units_cover_the_whole_ingress(self):
        self.assertEqual(desiccant_units(0.5, 0.2, 180.0, 6.0), 3)

    def test_partial_unit_rounds_up(self):
        self.assertEqual(desiccant_units(0.5, 0.2, 181.0, 6.0), 4)

    def test_minimum_one_unit_even_for_a_tiny_bag(self):
        self.assertEqual(desiccant_units(0.001, 0.001, 1.0, 100.0), 1)

    def test_zero_capacity_rejected(self):
        with self.assertRaises(ValueError):
            desiccant_units(0.5, 0.2, 180.0, 0.0)


class LabelTests(unittest.TestCase):
    def test_plain_item_needs_only_the_base_fields(self):
        self.assertEqual(required_label_fields(PLAIN_ITEM), list(BASE_LABEL_FIELDS))

    def test_esd_item_adds_the_symbol(self):
        item = dict(PLAIN_ITEM, esd_sensitive=True)
        self.assertIn("esd-sensitive-symbol", required_label_fields(item))

    def test_hazardous_and_pressurised_add_two_fields(self):
        item = dict(PLAIN_ITEM, hazardous=True, pressurised=True)
        fields = required_label_fields(item)
        self.assertIn("hazard-marking", fields)
        self.assertIn("pressurised-item-warning", fields)

    def test_missing_field_is_named(self):
        findings = label_findings(list(BASE_LABEL_FIELDS[:-1]), list(BASE_LABEL_FIELDS))
        self.assertEqual(len(findings), 1)
        self.assertIn("lifting-points", findings[0])

    def test_case_difference_is_not_a_gap(self):
        self.assertEqual(label_findings(["Part Number"], ["part-number"]), [])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            label_findings("part-number", ["part-number"])


class ProtectionTests(unittest.TestCase):
    def test_plain_item_needs_only_the_base_means(self):
        self.assertEqual(required_protection_means(PLAIN_ITEM), list(BASE_PROTECTION_MEANS))

    def test_esd_item_needs_bag_shunts_and_procedure(self):
        means = required_protection_means(dict(PLAIN_ITEM, esd_sensitive=True))
        for expected in ("static-shielding-bag", "connector-shunts", "grounded-handling-procedure"):
            self.assertIn(expected, means)

    def test_moisture_item_needs_barrier_desiccant_and_indicator(self):
        means = required_protection_means(dict(PLAIN_ITEM, moisture_sensitive=True))
        self.assertIn("sealed-moisture-barrier", means)
        self.assertIn("humidity-indicator", means)

    def test_missing_mean_is_named(self):
        findings = protection_findings(["outer-container"], list(BASE_PROTECTION_MEANS))
        self.assertEqual(len(findings), 2)

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            protection_findings(["outer-container"], "cushioning")


class AssessPreparationTests(unittest.TestCase):
    def test_conforming_package_is_ready(self):
        result = assess_delivery_preparation(_spec())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["ready_for_delivery"])
        self.assertAlmostEqual(result["required_cushion_thickness_mm"], 75.0, places=9)

    def test_thin_cushion_is_a_finding(self):
        spec = _spec()
        spec["cushion"]["thickness_mm"] = 60.0
        result = assess_delivery_preparation(spec)
        self.assertFalse(result["ready_for_delivery"])
        self.assertIn("cushion thickness", result["findings"][0])

    def test_cushion_exactly_at_requirement_is_accepted(self):
        spec = _spec()
        spec["cushion"]["thickness_mm"] = 75.0
        result = assess_delivery_preparation(spec)
        self.assertTrue(result["ready_for_delivery"])

    def test_esd_item_without_shunts_is_a_finding(self):
        spec = _spec(item={"esd_sensitive": True})
        spec["provided_protection"] = [
            m for m in spec["provided_protection"] if m != "connector-shunts"
        ]
        result = assess_delivery_preparation(spec)
        self.assertTrue(any("connector-shunts" in f for f in result["findings"]))

    def test_moisture_item_without_storage_data_rejected(self):
        spec = _spec(item={"moisture_sensitive": True})
        with self.assertRaises(ValueError):
            assess_delivery_preparation(spec)

    def test_moisture_item_short_on_desiccant_is_a_finding(self):
        spec = _spec(item={"moisture_sensitive": True})
        spec["storage"] = {
            "bag_area_m2": 0.5,
            "wvtr_g_per_m2_day": 0.2,
            "duration_days": 180.0,
            "unit_capacity_g": 6.0,
            "units_fitted": 1,
        }
        result = assess_delivery_preparation(spec)
        self.assertEqual(result["desiccant"]["units_required"], 3)
        self.assertTrue(any("desiccant charge" in f for f in result["findings"]))

    def test_every_finding_is_reported_not_just_the_first(self):
        spec = _spec(item={"esd_sensitive": True, "hazardous": True})
        spec["applied_label_fields"] = []
        spec["provided_protection"] = []
        result = assess_delivery_preparation(spec)
        self.assertGreaterEqual(len(result["findings"]), 12)

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["cushion"]
        with self.assertRaises(ValueError):
            assess_delivery_preparation(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_preparation(["item"])

    def test_negative_units_fitted_rejected(self):
        spec = _spec(item={"moisture_sensitive": True})
        spec["storage"] = {
            "bag_area_m2": 0.5,
            "wvtr_g_per_m2_day": 0.2,
            "duration_days": 180.0,
            "unit_capacity_g": 6.0,
            "units_fitted": -1,
        }
        with self.assertRaises(ValueError):
            assess_delivery_preparation(spec)


if __name__ == "__main__":
    unittest.main()
