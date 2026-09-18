"""Contract test for the harness high-voltage leaf (stdlib unittest)."""

import unittest

from q2030_hv_logic import (
    AIR_BREAKDOWN_V_PER_MM,
    CONTAMINATION_CONTROLLED,
    CONTAMINATION_HEAVY,
    CONTAMINATION_LIGHT,
    HIGH_VOLTAGE_THRESHOLD_V,
    MATERIAL_GROUP_I,
    MATERIAL_GROUP_II,
    MATERIAL_GROUP_III,
    MAX_PROOF_LEAKAGE_UA,
    MIN_CLEARANCE_MM,
    MIN_CREEPAGE_MM,
    MIN_PROOF_DWELL_S,
    PASCHEN_BAND_HIGH_MBAR,
    PASCHEN_BAND_LOW_MBAR,
    REGIME_AMBIENT_AIR,
    REGIME_PASCHEN_MINIMUM_BAND,
    REGIME_VACUUM,
    SEA_LEVEL_PRESSURE_MBAR,
    VACUUM_SURFACE_FLASHOVER_V_PER_MM,
    assess_hv_application,
    assess_hv_feature,
    breakdown_gradient_v_per_mm,
    distance_findings,
    high_voltage_applies,
    medium_findings,
    pressure_regime,
    proof_test_findings,
    proof_voltage_v,
    required_clearance_mm,
    required_creepage_mm,
    validate_feature,
)


def feature(fid="HV-1", **kw):
    record = {
        "id": fid,
        "working_voltage_v": 1000.0,
        "pressure_mbar": SEA_LEVEL_PRESSURE_MBAR,
        "material_group": MATERIAL_GROUP_II,
        "contamination_category": CONTAMINATION_LIGHT,
        "encapsulated": False,
        "measured_clearance_mm": 5.0,
        "measured_creepage_mm": 8.0,
        "proof_test": {"applied_v": 2500.0, "dwell_s": 60.0, "leakage_ua": 5.0},
    }
    record.update(kw)
    return record


class TestValidateFeature(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_feature(
            {"id": "HV-1", "working_voltage_v": 500.0, "pressure_mbar": 1000.0}
        )
        self.assertEqual(norm["material_group"], MATERIAL_GROUP_II)
        self.assertEqual(norm["contamination_category"], CONTAMINATION_LIGHT)
        self.assertFalse(norm["encapsulated"])
        self.assertIsNone(norm["proof_test"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_feature(["HV-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_feature(feature(""))

    def test_zero_working_voltage_raises(self):
        with self.assertRaises(ValueError):
            validate_feature(feature(working_voltage_v=0.0))

    def test_zero_pressure_raises(self):
        with self.assertRaises(ValueError):
            validate_feature(feature(pressure_mbar=0.0))

    def test_unknown_material_group_raises(self):
        with self.assertRaises(ValueError):
            validate_feature(feature(material_group="group-iv"))

    def test_unknown_contamination_category_raises(self):
        with self.assertRaises(ValueError):
            validate_feature(feature(contamination_category="filthy"))

    def test_non_boolean_encapsulation_raises(self):
        with self.assertRaises(ValueError):
            validate_feature(feature(encapsulated="yes"))

    def test_non_mapping_proof_test_raises(self):
        with self.assertRaises(ValueError):
            validate_feature(feature(proof_test=[2500.0]))


class TestApplicability(unittest.TestCase):
    def test_low_voltage_does_not_trigger_the_provisions(self):
        self.assertFalse(high_voltage_applies(HIGH_VOLTAGE_THRESHOLD_V))

    def test_above_the_threshold_the_provisions_apply(self):
        self.assertTrue(high_voltage_applies(HIGH_VOLTAGE_THRESHOLD_V + 1.0))

    def test_low_voltage_feature_is_reported_as_not_applicable(self):
        result = assess_hv_feature(feature(working_voltage_v=48.0, proof_test=None))
        self.assertFalse(result["applicable"])
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["proof_voltage_v"])


class TestPressureRegime(unittest.TestCase):
    def test_sea_level_is_ambient_air(self):
        self.assertEqual(pressure_regime(SEA_LEVEL_PRESSURE_MBAR), REGIME_AMBIENT_AIR)

    def test_hard_vacuum_is_the_vacuum_regime(self):
        self.assertEqual(pressure_regime(1.0e-6), REGIME_VACUUM)

    def test_the_band_itself_is_the_paschen_minimum(self):
        self.assertEqual(pressure_regime(1.0), REGIME_PASCHEN_MINIMUM_BAND)

    def test_band_edges_belong_to_the_band(self):
        self.assertEqual(
            pressure_regime(PASCHEN_BAND_HIGH_MBAR), REGIME_PASCHEN_MINIMUM_BAND
        )
        self.assertEqual(
            pressure_regime(PASCHEN_BAND_LOW_MBAR), REGIME_PASCHEN_MINIMUM_BAND
        )

    def test_non_positive_pressure_raises(self):
        with self.assertRaises(ValueError):
            pressure_regime(0.0)

    def test_air_gradient_falls_with_pressure(self):
        full = breakdown_gradient_v_per_mm(SEA_LEVEL_PRESSURE_MBAR)
        self.assertAlmostEqual(full, AIR_BREAKDOWN_V_PER_MM, places=9)
        half = breakdown_gradient_v_per_mm(SEA_LEVEL_PRESSURE_MBAR / 2.0)
        self.assertAlmostEqual(half, AIR_BREAKDOWN_V_PER_MM / 2.0, places=9)

    def test_vacuum_gradient_is_the_surface_flashover_value(self):
        self.assertAlmostEqual(
            breakdown_gradient_v_per_mm(1.0e-6), VACUUM_SURFACE_FLASHOVER_V_PER_MM, places=9
        )

    def test_gradient_inside_the_band_raises(self):
        with self.assertRaises(ValueError):
            breakdown_gradient_v_per_mm(1.0)


class TestClearanceAndCreepage(unittest.TestCase):
    def test_clearance_scales_with_voltage_and_safety_factor(self):
        self.assertAlmostEqual(
            required_clearance_mm(1500.0, SEA_LEVEL_PRESSURE_MBAR), 1.0, places=9
        )

    def test_clearance_is_floored_for_a_modest_voltage(self):
        self.assertAlmostEqual(
            required_clearance_mm(200.0, SEA_LEVEL_PRESSURE_MBAR), MIN_CLEARANCE_MM, places=9
        )

    def test_clearance_grows_as_pressure_falls_in_the_air_regime(self):
        high = required_clearance_mm(1500.0, SEA_LEVEL_PRESSURE_MBAR)
        low = required_clearance_mm(1500.0, SEA_LEVEL_PRESSURE_MBAR / 2.0)
        self.assertAlmostEqual(low, 2.0 * high, places=9)

    def test_clearance_refuses_a_non_positive_voltage(self):
        with self.assertRaises(ValueError):
            required_clearance_mm(0.0, SEA_LEVEL_PRESSURE_MBAR)

    def test_creepage_scales_with_the_material_and_contamination_table(self):
        self.assertAlmostEqual(
            required_creepage_mm(1000.0, MATERIAL_GROUP_II, CONTAMINATION_LIGHT),
            4.0,
            places=9,
        )

    def test_dirtier_environment_asks_for_more_creepage(self):
        clean = required_creepage_mm(1000.0, MATERIAL_GROUP_I, CONTAMINATION_CONTROLLED)
        dirty = required_creepage_mm(1000.0, MATERIAL_GROUP_III, CONTAMINATION_HEAVY)
        self.assertGreater(dirty, clean)

    def test_creepage_is_floored(self):
        self.assertAlmostEqual(
            required_creepage_mm(120.0, MATERIAL_GROUP_I, CONTAMINATION_CONTROLLED),
            MIN_CREEPAGE_MM,
            places=9,
        )

    def test_creepage_is_never_below_the_clearance(self):
        value = required_creepage_mm(
            1000.0, MATERIAL_GROUP_I, CONTAMINATION_CONTROLLED, clearance_mm=6.0
        )
        self.assertAlmostEqual(value, 6.0, places=9)

    def test_creepage_rejects_an_unknown_material_group(self):
        with self.assertRaises(ValueError):
            required_creepage_mm(1000.0, "group-iv", CONTAMINATION_LIGHT)

    def test_creepage_rejects_an_unknown_contamination_category(self):
        with self.assertRaises(ValueError):
            required_creepage_mm(1000.0, MATERIAL_GROUP_II, "filthy")


class TestMediumFindings(unittest.TestCase):
    def test_unencapsulated_feature_in_the_band_is_a_finding(self):
        self.assertIn(
            "unencapsulated-feature-inside-the-paschen-minimum-band",
            medium_findings(feature(pressure_mbar=1.0)),
        )

    def test_encapsulated_feature_in_the_band_is_clean(self):
        self.assertEqual(
            medium_findings(feature(pressure_mbar=1.0, encapsulated=True)), []
        )

    def test_ambient_feature_has_no_medium_finding(self):
        self.assertEqual(medium_findings(feature()), [])


class TestDistanceFindings(unittest.TestCase):
    def test_generous_as_built_distances_are_clean(self):
        self.assertEqual(distance_findings(feature()), [])

    def test_short_clearance_is_a_finding(self):
        self.assertIn(
            "as-built-clearance-below-the-sized-value",
            distance_findings(feature(measured_clearance_mm=0.1)),
        )

    def test_short_creepage_is_a_finding(self):
        self.assertIn(
            "as-built-creepage-below-the-sized-value",
            distance_findings(feature(measured_creepage_mm=0.1)),
        )

    def test_distance_exactly_on_the_sized_value_is_accepted(self):
        sized_clearance = required_clearance_mm(1000.0, SEA_LEVEL_PRESSURE_MBAR)
        sized_creepage = required_creepage_mm(
            1000.0,
            MATERIAL_GROUP_II,
            CONTAMINATION_LIGHT,
            clearance_mm=sized_clearance,
        )
        exact = feature(
            measured_clearance_mm=sized_clearance, measured_creepage_mm=sized_creepage
        )
        self.assertEqual(distance_findings(exact), [])

    def test_distances_are_not_graded_inside_the_band(self):
        self.assertEqual(
            distance_findings(
                feature(pressure_mbar=1.0, encapsulated=True, measured_clearance_mm=0.0)
            ),
            [],
        )


class TestProofTest(unittest.TestCase):
    def test_proof_voltage_is_derived_from_the_working_voltage(self):
        self.assertAlmostEqual(proof_voltage_v(1000.0), 2500.0, places=9)

    def test_proof_voltage_refuses_a_non_positive_working_voltage(self):
        with self.assertRaises(ValueError):
            proof_voltage_v(0.0)

    def test_absent_proof_test_is_a_finding(self):
        self.assertEqual(
            proof_test_findings(feature(proof_test=None)),
            ["no-high-voltage-proof-test-on-record"],
        )

    def test_low_applied_voltage_is_a_finding(self):
        low = feature(proof_test={"applied_v": 1200.0, "dwell_s": 60.0, "leakage_ua": 1.0})
        self.assertIn("proof-voltage-below-the-derived-level", proof_test_findings(low))

    def test_short_dwell_is_a_finding(self):
        brief = feature(
            proof_test={"applied_v": 2500.0, "dwell_s": 5.0, "leakage_ua": 1.0}
        )
        self.assertIn("proof-dwell-shorter-than-required", proof_test_findings(brief))

    def test_high_leakage_is_a_finding(self):
        leaky = feature(
            proof_test={
                "applied_v": 2500.0,
                "dwell_s": MIN_PROOF_DWELL_S,
                "leakage_ua": MAX_PROOF_LEAKAGE_UA * 2.0,
            }
        )
        self.assertIn("proof-leakage-current-above-the-limit", proof_test_findings(leaky))

    def test_leakage_exactly_on_the_limit_is_accepted(self):
        on_limit = feature(
            proof_test={
                "applied_v": 2500.0,
                "dwell_s": MIN_PROOF_DWELL_S,
                "leakage_ua": MAX_PROOF_LEAKAGE_UA,
            }
        )
        self.assertEqual(proof_test_findings(on_limit), [])


class TestAssessment(unittest.TestCase):
    def test_a_sound_feature_is_compliant(self):
        result = assess_hv_feature(feature())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["regime"], REGIME_AMBIENT_AIR)
        self.assertAlmostEqual(result["proof_voltage_v"], 2500.0, places=9)

    def test_a_band_feature_reports_encapsulation(self):
        report = assess_hv_application(
            [feature("HV-1"), feature("HV-2", pressure_mbar=1.0, encapsulated=True)]
        )
        self.assertEqual(report["encapsulation_required_ids"], ["HV-2"])
        self.assertTrue(report["compliant"])

    def test_duplicate_feature_id_raises(self):
        with self.assertRaises(ValueError):
            assess_hv_application([feature("HV-1"), feature("HV-1")])

    def test_empty_feature_set_raises(self):
        with self.assertRaises(ValueError):
            assess_hv_application([])

    def test_non_list_input_raises(self):
        with self.assertRaises(ValueError):
            assess_hv_application(feature())


if __name__ == "__main__":
    unittest.main()
