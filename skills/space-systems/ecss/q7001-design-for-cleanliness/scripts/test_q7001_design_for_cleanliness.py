"""Contract tests for the design-for-cleanliness provision logic."""

import copy
import unittest

from q7001_design_for_cleanliness_logic import (
    CRITERION_TOLERANCE,
    PROVISIONS,
    assess_accessibility,
    assess_design_for_cleanliness,
    assess_drainage,
    assess_material_choice,
    assess_venting,
    cleanable_fraction,
    find_undrained_features,
    required_vent_area_m2,
    validate_fraction,
    validate_positive,
    vent_time_constant_s,
)


def sample_enclosure(**overrides):
    enclosure = {
        "name": "instrument housing",
        "volume_m3": 0.5,
        "vent_area_m2": 0.002,
        "conductance_m_per_s": 100.0,
        "max_time_constant_s": 4.0,
        "filtered": True,
        "directed_away": True,
    }
    enclosure.update(overrides)
    return enclosure


def sample_features():
    return [
        {"name": "blind fastener hole", "traps_fluid": True, "drained": True},
        {"name": "honeycomb core cell", "traps_fluid": True, "drained": True},
        {"name": "external rib", "traps_fluid": False, "drained": False},
    ]


def sample_materials():
    return [
        {
            "name": "conversion coating",
            "usage": "surface finish",
            "exposed": True,
            "screened": True,
            "low_outgassing": True,
        },
        {
            "name": "dry film bush",
            "usage": "lubricant",
            "exposed": True,
            "screened": True,
            "low_outgassing": True,
        },
        {
            "name": "internal potting",
            "usage": "adhesive",
            "exposed": False,
            "screened": True,
        },
    ]


class ValidationTests(unittest.TestCase):
    def test_positive_returns_float(self):
        self.assertAlmostEqual(validate_positive(3, "x"), 3.0, places=9)

    def test_zero_rejected_by_default(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "x")

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(True, "x")

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(float("nan"), "x")

    def test_fraction_accepts_the_unit_bound(self):
        self.assertAlmostEqual(validate_fraction(1.0, "f"), 1.0, places=9)

    def test_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_fraction(1.2, "f")


class VentingTests(unittest.TestCase):
    def test_time_constant_from_volume_and_vent_area(self):
        self.assertAlmostEqual(vent_time_constant_s(0.5, 0.002, 100.0), 2.5, places=9)

    def test_doubling_the_vent_area_halves_the_time_constant(self):
        one = vent_time_constant_s(0.5, 0.002, 100.0)
        two = vent_time_constant_s(0.5, 0.004, 100.0)
        self.assertAlmostEqual(two, one / 2.0, places=9)

    def test_required_area_inverts_the_time_constant(self):
        self.assertAlmostEqual(required_vent_area_m2(0.5, 2.5, 100.0), 0.002, places=9)

    def test_zero_vent_area_rejected(self):
        with self.assertRaises(ValueError):
            vent_time_constant_s(0.5, 0.0, 100.0)

    def test_negative_volume_rejected(self):
        with self.assertRaises(ValueError):
            vent_time_constant_s(-0.5, 0.002, 100.0)

    def test_compliant_enclosure_reports_no_findings(self):
        record = assess_venting(sample_enclosure())
        self.assertTrue(record["compliant"])
        self.assertEqual(record["findings"], [])

    def test_enclosure_exactly_at_its_limit_still_meets_it(self):
        record = assess_venting(sample_enclosure(max_time_constant_s=2.5))
        self.assertTrue(record["fast_enough"])
        self.assertAlmostEqual(record["time_constant_s"], 2.5, places=9)
        self.assertAlmostEqual(record["required_vent_area_m2"], 0.002, places=9)
        self.assertLessEqual(
            abs(record["time_constant_s"] - record["max_time_constant_s"]),
            CRITERION_TOLERANCE,
        )

    def test_undersized_vent_is_flagged_with_the_area_needed(self):
        record = assess_venting(sample_enclosure(max_time_constant_s=1.0))
        self.assertFalse(record["fast_enough"])
        self.assertAlmostEqual(record["required_vent_area_m2"], 0.005, places=9)

    def test_unfiltered_vent_is_flagged(self):
        record = assess_venting(sample_enclosure(filtered=False))
        self.assertFalse(record["compliant"])
        self.assertTrue(any("unfiltered" in f for f in record["findings"]))

    def test_vent_aimed_at_a_sensitive_surface_is_flagged(self):
        record = assess_venting(sample_enclosure(directed_away=False))
        self.assertFalse(record["compliant"])
        self.assertTrue(any("redirect" in f for f in record["findings"]))

    def test_missing_enclosure_key_rejected(self):
        enclosure = sample_enclosure()
        del enclosure["volume_m3"]
        with self.assertRaises(ValueError):
            assess_venting(enclosure)

    def test_blank_enclosure_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_venting(sample_enclosure(name="  "))


class DrainageTests(unittest.TestCase):
    def test_fully_drained_design_has_no_undrained_feature(self):
        self.assertEqual(find_undrained_features(sample_features()), [])

    def test_trapped_feature_without_a_drain_is_found(self):
        features = sample_features()
        features[1]["drained"] = False
        self.assertEqual(find_undrained_features(features), ["honeycomb core cell"])

    def test_feature_that_traps_nothing_needs_no_drain(self):
        features = [{"name": "external rib", "traps_fluid": False, "drained": False}]
        self.assertEqual(find_undrained_features(features), [])

    def test_duplicate_feature_name_rejected(self):
        features = sample_features()
        features[2]["name"] = "blind fastener hole"
        with self.assertRaises(ValueError):
            find_undrained_features(features)

    def test_non_boolean_drain_flag_rejected(self):
        features = sample_features()
        features[0]["drained"] = "yes"
        with self.assertRaises(ValueError):
            find_undrained_features(features)

    def test_missing_feature_key_rejected(self):
        with self.assertRaises(ValueError):
            find_undrained_features([{"name": "pocket", "traps_fluid": True}])

    def test_drainage_record_carries_the_finding(self):
        features = sample_features()
        features[0]["drained"] = False
        record = assess_drainage(features)
        self.assertFalse(record["compliant"])
        self.assertEqual(len(record["findings"]), 1)


class AccessibilityTests(unittest.TestCase):
    def test_cleanable_fraction_is_the_area_share(self):
        self.assertAlmostEqual(cleanable_fraction(6.0, 8.0), 0.75, places=9)

    def test_fully_accessible_surface_is_unity(self):
        self.assertAlmostEqual(cleanable_fraction(8.0, 8.0), 1.0, places=9)

    def test_accessible_area_over_the_total_rejected(self):
        with self.assertRaises(ValueError):
            cleanable_fraction(9.0, 8.0)

    def test_zero_total_area_rejected(self):
        with self.assertRaises(ValueError):
            cleanable_fraction(0.0, 0.0)

    def test_design_exactly_at_the_required_fraction_meets_it(self):
        record = assess_accessibility(6.0, 8.0, 0.75)
        self.assertTrue(record["compliant"])
        self.assertAlmostEqual(
            record["cleanable_fraction"] - record["required_fraction"], 0.0, places=9
        )
        self.assertLessEqual(
            abs(record["cleanable_fraction"] - record["required_fraction"]),
            CRITERION_TOLERANCE,
        )

    def test_unreachable_surface_is_flagged(self):
        record = assess_accessibility(6.0, 8.0, 0.90)
        self.assertFalse(record["compliant"])
        self.assertEqual(len(record["findings"]), 1)


class MaterialChoiceTests(unittest.TestCase):
    def test_screened_exposed_materials_pass(self):
        record = assess_material_choice(sample_materials())
        self.assertTrue(record["compliant"])
        self.assertEqual(record["exposed"], 2)
        self.assertAlmostEqual(record["compliant_share"], 1.0, places=9)

    def test_unscreened_exposed_material_is_flagged(self):
        materials = sample_materials()
        materials[0]["screened"] = False
        record = assess_material_choice(materials)
        self.assertFalse(record["compliant"])
        self.assertAlmostEqual(record["compliant_share"], 0.5, places=9)

    def test_screened_but_high_outgassing_material_is_flagged(self):
        materials = sample_materials()
        materials[1]["low_outgassing"] = False
        materials[1]["substitute"] = "dry film alternative"
        record = assess_material_choice(materials)
        self.assertFalse(record["compliant"])
        self.assertTrue(
            any("dry film alternative" in f for f in record["findings"])
        )

    def test_unexposed_material_is_not_graded_here(self):
        materials = sample_materials()
        materials[2]["screened"] = False
        self.assertTrue(assess_material_choice(materials)["compliant"])

    def test_duplicate_material_rejected(self):
        materials = sample_materials()
        materials[2]["name"] = "conversion coating"
        with self.assertRaises(ValueError):
            assess_material_choice(materials)

    def test_no_exposed_material_rejected(self):
        materials = [dict(m, exposed=False) for m in sample_materials()]
        with self.assertRaises(ValueError):
            assess_material_choice(materials)

    def test_empty_material_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_material_choice([])

    def test_non_boolean_screened_flag_rejected(self):
        materials = sample_materials()
        materials[0]["screened"] = 1
        with self.assertRaises(ValueError):
            assess_material_choice(materials)


class DesignAssessmentTests(unittest.TestCase):
    def _spec(self):
        return copy.deepcopy(
            {
                "enclosures": [sample_enclosure()],
                "features": sample_features(),
                "materials": sample_materials(),
                "accessible_area_m2": 7.0,
                "total_area_m2": 8.0,
                "required_accessible_fraction": 0.80,
            }
        )

    def test_sound_design_meets_every_provision(self):
        result = assess_design_for_cleanliness(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(sorted(result["provisions_met"]), sorted(PROVISIONS))
        self.assertEqual(result["findings"], [])

    def test_each_provision_is_reported_separately(self):
        result = assess_design_for_cleanliness(self._spec())
        self.assertEqual(sorted(result["provisions"]), sorted(PROVISIONS))

    def test_one_failed_provision_leaves_the_others_met(self):
        spec = self._spec()
        spec["features"][0]["drained"] = False
        result = assess_design_for_cleanliness(spec)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["provisions_outstanding"], ["drainage"])

    def test_vent_and_material_failures_both_surface(self):
        spec = self._spec()
        spec["enclosures"][0]["filtered"] = False
        spec["materials"][0]["screened"] = False
        result = assess_design_for_cleanliness(spec)
        self.assertEqual(
            sorted(result["provisions_outstanding"]), ["material-choice", "venting"]
        )

    def test_inaccessible_surface_fails_the_accessibility_provision(self):
        spec = self._spec()
        spec["required_accessible_fraction"] = 0.95
        result = assess_design_for_cleanliness(spec)
        self.assertIn("accessibility", result["provisions_outstanding"])

    def test_two_enclosures_sharing_a_name_rejected(self):
        spec = self._spec()
        spec["enclosures"].append(sample_enclosure())
        with self.assertRaises(ValueError):
            assess_design_for_cleanliness(spec)

    def test_empty_enclosure_list_rejected(self):
        spec = self._spec()
        spec["enclosures"] = []
        with self.assertRaises(ValueError):
            assess_design_for_cleanliness(spec)

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["materials"]
        with self.assertRaises(ValueError):
            assess_design_for_cleanliness(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_design_for_cleanliness(["enclosures"])


if __name__ == "__main__":
    unittest.main()
