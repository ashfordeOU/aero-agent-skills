#!/usr/bin/env python3
"""Gate 3 contract test for e2006-internal-dielectric-field-limits.

Stdlib unittest, offline, deterministic. Run:
    python3 test_e2006_internal_dielectric_field_limits.py
"""

import math
import unittest

from e2006_internal_dielectric_field_limits_logic import (
    MATERIAL_PROPERTIES,
    MIN_TEMPERATURE_C,
    allowable_field,
    assess_dielectric_item,
    assess_dielectric_set,
    categorize_insulating_material,
    coaxial_internal_field,
    derated_default_cap,
    field_within_cap,
    internal_field,
    planar_internal_field,
    summarize_assessment,
    temperature_derating_factor,
    validate_demonstration,
)

POLYIMIDE = "polyimide-film"
POLYIMIDE_CAP = MATERIAL_PROPERTIES[POLYIMIDE]["base_cap_v_per_m"]


def planar_item(item_id, potential, thickness, material=POLYIMIDE, temp=20.0, demo=None):
    item = {
        "id": item_id,
        "material": material,
        "geometry": "planar",
        "potential_v": potential,
        "thickness_m": thickness,
        "temperature_c": temp,
    }
    if demo is not None:
        item["demonstration"] = demo
    return item


def good_demo(level, material=POLYIMIDE):
    return {
        "material": material,
        "evidence_ref": "QR-2211-dielectric-breakdown",
        "temperature_min_c": -60.0,
        "temperature_max_c": 125.0,
        "demonstrated_cap_v_per_m": level,
    }


class TestCategorizeInsulatingMaterial(unittest.TestCase):
    def test_known_material_normalizes(self):
        self.assertEqual(categorize_insulating_material("  Polyimide-Film "), POLYIMIDE)

    def test_every_table_key_is_accepted(self):
        for key in MATERIAL_PROPERTIES:
            self.assertEqual(categorize_insulating_material(key), key)

    def test_uncategorized_material_raises(self):
        with self.assertRaises(ValueError):
            categorize_insulating_material("unobtanium-wrap")

    def test_blank_material_raises(self):
        with self.assertRaises(ValueError):
            categorize_insulating_material("  ")

    def test_non_string_material_raises(self):
        with self.assertRaises(ValueError):
            categorize_insulating_material(3.3)


class TestPlanarInternalField(unittest.TestCase):
    def test_uniform_field_is_potential_over_thickness(self):
        self.assertAlmostEqual(planar_internal_field(100.0, 1.0e-3), 1.0e5, places=3)

    def test_thinner_wall_raises_the_field(self):
        thick = planar_internal_field(100.0, 2.0e-3)
        thin = planar_internal_field(100.0, 1.0e-3)
        self.assertGreater(thin, thick)

    def test_zero_potential_gives_zero_field(self):
        self.assertAlmostEqual(planar_internal_field(0.0, 1.0e-3), 0.0)

    def test_integer_inputs_accepted(self):
        self.assertAlmostEqual(planar_internal_field(10, 1), 10.0)

    def test_negative_potential_raises(self):
        with self.assertRaises(ValueError):
            planar_internal_field(-5.0, 1.0e-3)

    def test_zero_thickness_raises(self):
        with self.assertRaises(ValueError):
            planar_internal_field(100.0, 0.0)

    def test_negative_thickness_raises(self):
        with self.assertRaises(ValueError):
            planar_internal_field(100.0, -1.0e-3)

    def test_non_numeric_thickness_raises(self):
        with self.assertRaises(ValueError):
            planar_internal_field(100.0, "thin")

    def test_boolean_potential_raises(self):
        with self.assertRaises(ValueError):
            planar_internal_field(True, 1.0e-3)

    def test_non_finite_potential_raises(self):
        with self.assertRaises(ValueError):
            planar_internal_field(float("nan"), 1.0e-3)


class TestCoaxialInternalField(unittest.TestCase):
    def test_matches_the_inner_radius_gradient(self):
        value = coaxial_internal_field(1000.0, 1.0e-3, 3.0e-3)
        expected = 1000.0 / (1.0e-3 * math.log(3.0))
        self.assertAlmostEqual(value, expected, places=3)

    def test_peak_exceeds_the_planar_mean_of_the_same_wall(self):
        peak = coaxial_internal_field(1000.0, 1.0e-3, 3.0e-3)
        mean = planar_internal_field(1000.0, 2.0e-3)
        self.assertGreater(peak, mean)

    def test_thinner_inner_conductor_drives_the_gradient_up(self):
        thin = coaxial_internal_field(1000.0, 0.5e-3, 3.0e-3)
        fat = coaxial_internal_field(1000.0, 1.0e-3, 3.0e-3)
        self.assertGreater(thin, fat)

    def test_zero_inner_radius_raises(self):
        with self.assertRaises(ValueError):
            coaxial_internal_field(1000.0, 0.0, 3.0e-3)

    def test_outer_not_exceeding_inner_raises(self):
        with self.assertRaises(ValueError):
            coaxial_internal_field(1000.0, 2.0e-3, 2.0e-3)

    def test_negative_potential_raises(self):
        with self.assertRaises(ValueError):
            coaxial_internal_field(-1.0, 1.0e-3, 3.0e-3)

    def test_non_numeric_outer_radius_raises(self):
        with self.assertRaises(ValueError):
            coaxial_internal_field(1000.0, 1.0e-3, None)


class TestInternalFieldDispatch(unittest.TestCase):
    def test_planar_dispatch(self):
        self.assertAlmostEqual(
            internal_field(planar_item("p1", 100.0, 1.0e-3)), 1.0e5, places=3
        )

    def test_coaxial_dispatch(self):
        item = {
            "id": "c1",
            "material": POLYIMIDE,
            "geometry": "Coaxial",
            "potential_v": 1000.0,
            "inner_radius_m": 1.0e-3,
            "outer_radius_m": 3.0e-3,
            "temperature_c": 20.0,
        }
        expected = 1000.0 / (1.0e-3 * math.log(3.0))
        self.assertAlmostEqual(internal_field(item), expected, places=3)

    def test_unknown_geometry_raises(self):
        item = planar_item("p1", 100.0, 1.0e-3)
        item["geometry"] = "toroidal"
        with self.assertRaises(ValueError):
            internal_field(item)

    def test_missing_geometry_raises(self):
        with self.assertRaises(ValueError):
            internal_field({"potential_v": 1.0, "thickness_m": 1.0})

    def test_non_mapping_item_raises(self):
        with self.assertRaises(ValueError):
            internal_field(["planar", 100.0])


class TestTemperatureDerating(unittest.TestCase):
    def test_unity_well_below_the_knee(self):
        self.assertAlmostEqual(temperature_derating_factor(POLYIMIDE, -40.0), 1.0)

    def test_unity_exactly_at_the_knee(self):
        knee = MATERIAL_PROPERTIES[POLYIMIDE]["knee_temperature_c"]
        self.assertAlmostEqual(temperature_derating_factor(POLYIMIDE, knee), 1.0)

    def test_midpoint_is_halfway_to_the_floor(self):
        props = MATERIAL_PROPERTIES[POLYIMIDE]
        mid = (props["knee_temperature_c"] + props["service_temperature_c"]) / 2.0
        expected = 1.0 - (1.0 - props["floor_factor"]) * 0.5
        self.assertAlmostEqual(temperature_derating_factor(POLYIMIDE, mid), expected)

    def test_floor_factor_at_service_temperature(self):
        props = MATERIAL_PROPERTIES[POLYIMIDE]
        self.assertAlmostEqual(
            temperature_derating_factor(POLYIMIDE, props["service_temperature_c"]),
            props["floor_factor"],
        )

    def test_factor_is_monotonic_above_the_knee(self):
        a = temperature_derating_factor(POLYIMIDE, 140.0)
        b = temperature_derating_factor(POLYIMIDE, 180.0)
        self.assertGreater(a, b)

    def test_above_service_temperature_raises(self):
        with self.assertRaises(ValueError):
            temperature_derating_factor(POLYIMIDE, 260.0)

    def test_below_data_floor_raises(self):
        with self.assertRaises(ValueError):
            temperature_derating_factor(POLYIMIDE, MIN_TEMPERATURE_C - 1.0)

    def test_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            temperature_derating_factor("unobtanium-wrap", 20.0)

    def test_non_numeric_temperature_raises(self):
        with self.assertRaises(ValueError):
            temperature_derating_factor(POLYIMIDE, "warm")


class TestDeratedDefaultCap(unittest.TestCase):
    def test_cold_item_keeps_the_base_cap(self):
        self.assertAlmostEqual(derated_default_cap(POLYIMIDE, 20.0), POLYIMIDE_CAP, places=3)

    def test_hot_item_is_derated_below_the_base_cap(self):
        self.assertLess(derated_default_cap(POLYIMIDE, 180.0), POLYIMIDE_CAP)

    def test_out_of_envelope_temperature_raises(self):
        with self.assertRaises(ValueError):
            derated_default_cap("epoxy-glass-laminate", 200.0)


class TestValidateDemonstration(unittest.TestCase):
    def test_valid_record_returns_its_level(self):
        level = validate_demonstration(
            good_demo(3.0e7), POLYIMIDE, 20.0, POLYIMIDE_CAP
        )
        self.assertAlmostEqual(level, 3.0e7, places=3)

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            validate_demonstration("QR-2211", POLYIMIDE, 20.0, POLYIMIDE_CAP)

    def test_record_for_another_material_raises(self):
        with self.assertRaises(ValueError):
            validate_demonstration(
                good_demo(3.0e7, material="ptfe-wire-insulation"),
                POLYIMIDE,
                20.0,
                POLYIMIDE_CAP,
            )

    def test_record_with_uncategorized_material_raises(self):
        record = good_demo(3.0e7)
        record["material"] = "unobtanium-wrap"
        with self.assertRaises(ValueError):
            validate_demonstration(record, POLYIMIDE, 20.0, POLYIMIDE_CAP)

    def test_missing_evidence_reference_raises(self):
        record = good_demo(3.0e7)
        del record["evidence_ref"]
        with self.assertRaises(ValueError):
            validate_demonstration(record, POLYIMIDE, 20.0, POLYIMIDE_CAP)

    def test_blank_evidence_reference_raises(self):
        record = good_demo(3.0e7)
        record["evidence_ref"] = "   "
        with self.assertRaises(ValueError):
            validate_demonstration(record, POLYIMIDE, 20.0, POLYIMIDE_CAP)

    def test_temperature_above_the_covered_band_raises(self):
        with self.assertRaises(ValueError):
            validate_demonstration(good_demo(3.0e7), POLYIMIDE, 150.0, POLYIMIDE_CAP)

    def test_temperature_below_the_covered_band_raises(self):
        with self.assertRaises(ValueError):
            validate_demonstration(good_demo(3.0e7), POLYIMIDE, -100.0, POLYIMIDE_CAP)

    def test_band_edges_are_covered(self):
        level = validate_demonstration(good_demo(3.0e7), POLYIMIDE, 125.0, POLYIMIDE_CAP)
        self.assertAlmostEqual(level, 3.0e7, places=3)

    def test_inverted_temperature_band_raises(self):
        record = good_demo(3.0e7)
        record["temperature_min_c"] = 125.0
        record["temperature_max_c"] = -60.0
        with self.assertRaises(ValueError):
            validate_demonstration(record, POLYIMIDE, 20.0, POLYIMIDE_CAP)

    def test_level_equal_to_baseline_raises(self):
        with self.assertRaises(ValueError):
            validate_demonstration(
                good_demo(POLYIMIDE_CAP), POLYIMIDE, 20.0, POLYIMIDE_CAP
            )

    def test_level_below_baseline_raises(self):
        with self.assertRaises(ValueError):
            validate_demonstration(good_demo(1.0e7), POLYIMIDE, 20.0, POLYIMIDE_CAP)

    def test_non_positive_level_raises(self):
        with self.assertRaises(ValueError):
            validate_demonstration(good_demo(0.0), POLYIMIDE, 20.0, POLYIMIDE_CAP)

    def test_non_numeric_level_raises(self):
        record = good_demo(3.0e7)
        record["demonstrated_cap_v_per_m"] = "high"
        with self.assertRaises(ValueError):
            validate_demonstration(record, POLYIMIDE, 20.0, POLYIMIDE_CAP)


class TestAllowableField(unittest.TestCase):
    def test_default_basis_without_a_record(self):
        cap, basis = allowable_field(POLYIMIDE, 20.0)
        self.assertAlmostEqual(cap, POLYIMIDE_CAP, places=3)
        self.assertEqual(basis, "derated-default")

    def test_demonstration_basis_raises_the_cap(self):
        cap, basis = allowable_field(POLYIMIDE, 20.0, good_demo(3.0e7))
        self.assertAlmostEqual(cap, 3.0e7, places=3)
        self.assertEqual(basis, "application-demonstration")

    def test_demonstration_must_clear_the_derated_baseline(self):
        with self.assertRaises(ValueError):
            allowable_field(POLYIMIDE, 20.0, good_demo(1.5e7))


class TestFieldWithinCap(unittest.TestCase):
    def test_comfortably_below_cap(self):
        self.assertTrue(field_within_cap(1.0e7, 2.0e7))

    def test_exactly_on_cap(self):
        self.assertTrue(field_within_cap(2.0e7, 2.0e7))

    def test_quotient_a_few_ulps_over_cap_is_still_compliant(self):
        field = planar_internal_field(21.0, 1.05e-06)
        self.assertGreater(field, 2.0e7)
        self.assertTrue(field_within_cap(field, 2.0e7))

    def test_genuine_exceedance_is_rejected(self):
        self.assertFalse(field_within_cap(2.1e7, 2.0e7))


class TestAssessDielectricItem(unittest.TestCase):
    def test_compliant_planar_wall(self):
        result = assess_dielectric_item(planar_item("w1", 100.0, 1.0e-3))
        self.assertTrue(result["compliant"])
        self.assertEqual(result["cap_basis"], "derated-default")
        self.assertEqual(result["findings"], [])

    def test_utilization_and_margin_are_reported(self):
        result = assess_dielectric_item(planar_item("w2", 100.0, 1.0e-5))
        self.assertAlmostEqual(result["utilization"], 0.5, places=6)
        self.assertAlmostEqual(result["margin_v_per_m"], 1.0e7, places=1)

    def test_planar_exceedance_is_flagged(self):
        result = assess_dielectric_item(planar_item("w3", 1000.0, 1.0e-5))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("exceeds" in f for f in result["findings"]))

    def test_boundary_wall_stays_compliant(self):
        result = assess_dielectric_item(planar_item("w4", 21.0, 1.05e-06))
        self.assertGreater(result["field_v_per_m"], POLYIMIDE_CAP)
        self.assertTrue(result["compliant"])

    def test_coaxial_item_uses_the_inner_gradient(self):
        item = {
            "id": "c2",
            "material": POLYIMIDE,
            "geometry": "coaxial",
            "potential_v": 5000.0,
            "inner_radius_m": 1.0e-4,
            "outer_radius_m": 5.0e-4,
            "temperature_c": 20.0,
        }
        result = assess_dielectric_item(item)
        self.assertFalse(result["compliant"])
        self.assertGreater(result["field_v_per_m"], POLYIMIDE_CAP)

    def test_temperature_derating_can_turn_a_pass_into_a_finding(self):
        cool = assess_dielectric_item(planar_item("w5", 190.0, 1.0e-5, temp=20.0))
        hot = assess_dielectric_item(planar_item("w6", 190.0, 1.0e-5, temp=190.0))
        self.assertTrue(cool["compliant"])
        self.assertFalse(hot["compliant"])
        self.assertLess(hot["cap_v_per_m"], cool["cap_v_per_m"])

    def test_valid_demonstration_lifts_the_cap(self):
        item = planar_item("w7", 250.0, 1.0e-5, demo=good_demo(3.0e7))
        result = assess_dielectric_item(item)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["cap_basis"], "application-demonstration")
        self.assertAlmostEqual(result["cap_v_per_m"], 3.0e7, places=3)

    def test_rejected_demonstration_falls_back_to_the_default(self):
        item = planar_item(
            "w8", 250.0, 1.0e-5, demo=good_demo(3.0e7, material="ptfe-wire-insulation")
        )
        result = assess_dielectric_item(item)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["cap_basis"], "derated-default")
        self.assertTrue(any("demonstration rejected" in f for f in result["findings"]))
        self.assertAlmostEqual(result["derated_default_cap_v_per_m"], POLYIMIDE_CAP, places=3)

    def test_demonstration_not_covering_the_temperature_is_rejected(self):
        item = planar_item("w9", 250.0, 1.0e-5, temp=150.0, demo=good_demo(3.0e7))
        result = assess_dielectric_item(item)
        self.assertEqual(result["cap_basis"], "derated-default")
        self.assertTrue(any("demonstration rejected" in f for f in result["findings"]))

    def test_blank_item_id_raises(self):
        with self.assertRaises(ValueError):
            assess_dielectric_item(planar_item("  ", 100.0, 1.0e-3))

    def test_non_mapping_item_raises(self):
        with self.assertRaises(ValueError):
            assess_dielectric_item("w1")

    def test_uncategorized_material_raises(self):
        with self.assertRaises(ValueError):
            assess_dielectric_item(planar_item("w1", 100.0, 1.0e-3, material="mystery-goo"))

    def test_missing_temperature_raises(self):
        item = planar_item("w1", 100.0, 1.0e-3)
        del item["temperature_c"]
        with self.assertRaises(ValueError):
            assess_dielectric_item(item)

    def test_temperature_outside_the_qualified_envelope_raises(self):
        with self.assertRaises(ValueError):
            assess_dielectric_item(planar_item("w1", 100.0, 1.0e-3, temp=260.0))


class TestAssessDielectricSet(unittest.TestCase):
    def test_all_compliant_set(self):
        report = assess_dielectric_set(
            [planar_item("w1", 100.0, 1.0e-3), planar_item("w2", 100.0, 1.0e-4)]
        )
        self.assertTrue(report["compliant"])
        self.assertEqual(report["item_count"], 2)
        self.assertEqual(report["non_compliant_items"], [])

    def test_one_bad_item_fails_the_set(self):
        report = assess_dielectric_set(
            [planar_item("w1", 100.0, 1.0e-3), planar_item("w3", 1000.0, 1.0e-5)]
        )
        self.assertFalse(report["compliant"])
        self.assertEqual(report["non_compliant_items"], ["w3"])

    def test_worst_utilization_names_the_driving_item(self):
        report = assess_dielectric_set(
            [planar_item("w1", 100.0, 1.0e-3), planar_item("w3", 1000.0, 1.0e-5)]
        )
        self.assertEqual(report["worst_item_id"], "w3")
        self.assertGreater(report["worst_utilization"], 1.0)

    def test_empty_set_raises(self):
        with self.assertRaises(ValueError):
            assess_dielectric_set([])

    def test_non_list_set_raises(self):
        with self.assertRaises(ValueError):
            assess_dielectric_set(planar_item("w1", 100.0, 1.0e-3))

    def test_duplicate_item_id_raises(self):
        with self.assertRaises(ValueError):
            assess_dielectric_set(
                [planar_item("w1", 100.0, 1.0e-3), planar_item("w1", 100.0, 1.0e-4)]
            )


class TestSummarizeAssessment(unittest.TestCase):
    def test_compliant_summary_text(self):
        report = assess_dielectric_set([planar_item("w1", 100.0, 1.0e-3)])
        text = summarize_assessment(report)
        self.assertIn("COMPLIANT", text)
        self.assertIn("w1", text)

    def test_non_compliant_summary_text(self):
        report = assess_dielectric_set([planar_item("w3", 1000.0, 1.0e-5)])
        self.assertIn("NON-COMPLIANT", summarize_assessment(report))

    def test_summary_of_non_report_raises(self):
        with self.assertRaises(ValueError):
            summarize_assessment({"compliant": True})


class TestDeterminismAndTable(unittest.TestCase):
    def test_repeated_assessment_is_identical(self):
        item = planar_item("w1", 100.0, 1.0e-3)
        self.assertEqual(assess_dielectric_item(item), assess_dielectric_item(item))

    def test_material_table_is_self_consistent(self):
        for key, props in MATERIAL_PROPERTIES.items():
            self.assertGreater(props["base_cap_v_per_m"], 0.0, key)
            self.assertTrue(math.isfinite(props["base_cap_v_per_m"]), key)
            self.assertLess(props["knee_temperature_c"], props["service_temperature_c"], key)
            self.assertGreater(props["floor_factor"], 0.0, key)
            self.assertLessEqual(props["floor_factor"], 1.0, key)


if __name__ == "__main__":
    unittest.main()
