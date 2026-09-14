"""Contract tests for the clause 4.6.7 high voltage and microwave part logic."""

import unittest

from q6013_class_1_high_voltage_parts_logic import (
    CORONA_MITIGATIONS,
    CORONA_PRESSURE_BAND_PA,
    DERATING_CEILINGS,
    MANDATORY_SCREENING,
    MARGIN_TOLERANCE,
    RATIO_TOLERANCE,
    REQUIRED_MULTIPACTION_MARGIN_DB,
    SERVICE_CATEGORIES,
    assess_corona_control,
    assess_high_voltage_part,
    assess_multipaction,
    assess_voltage_derating,
    missing_screening_steps,
    multipaction_margin_db,
    normalize_token,
    validate_part_identity,
    validate_service_category,
    voltage_derating_ratio,
)

HV_PART = {
    "manufacturer": "northfield components",
    "part_number": "HV-2214-K",
    "service_category": "high-voltage",
}

MW_PART = {
    "manufacturer": "northfield components",
    "part_number": "MW-8801-C",
    "service_category": "high power microwave",
}


def _hv_application(**overrides):
    application = {
        "part": dict(HV_PART),
        "applied_voltage_v": 400.0,
        "rated_voltage_v": 1000.0,
        "operates_in_vacuum": True,
        "energized_pressures_pa": [1.0e-3],
        "corona_mitigations": [],
        "screening_steps": list(MANDATORY_SCREENING["high-voltage"]),
    }
    application.update(overrides)
    return application


def _mw_application(**overrides):
    application = {
        "part": dict(MW_PART),
        "applied_voltage_v": 100.0,
        "rated_voltage_v": 400.0,
        "operates_in_vacuum": True,
        "multipaction": {
            "applied_peak_power_w": 100.0,
            "multipaction_threshold_power_w": 800.0,
        },
        "energized_pressures_pa": [1.0e-4],
        "corona_mitigations": [],
        "screening_steps": list(MANDATORY_SCREENING["high-power-microwave"]),
    }
    application.update(overrides)
    return application


class IdentityTests(unittest.TestCase):
    def test_identity_returned_stripped_and_normalized(self):
        identity = validate_part_identity(
            {"manufacturer": "  northfield  ", "part_number": "HV-2214-K",
             "service_category": "High Voltage"}
        )
        self.assertEqual(identity["manufacturer"], "northfield")
        self.assertEqual(identity["service_category"], "high-voltage")

    def test_missing_part_number_rejected(self):
        bad = dict(HV_PART)
        del bad["part_number"]
        with self.assertRaises(ValueError):
            validate_part_identity(bad)

    def test_blank_manufacturer_rejected(self):
        with self.assertRaises(ValueError):
            validate_part_identity(dict(HV_PART, manufacturer="   "))

    def test_non_mapping_part_rejected(self):
        with self.assertRaises(ValueError):
            validate_part_identity("HV-2214-K")

    def test_unknown_service_category_rejected(self):
        with self.assertRaises(ValueError):
            validate_service_category("medium-voltage")

    def test_both_service_categories_are_reachable(self):
        for category in SERVICE_CATEGORIES:
            self.assertEqual(validate_service_category(category), category)

    def test_underscored_token_normalizes_to_hyphens(self):
        self.assertEqual(normalize_token("Voltage_Conditioning"), "voltage-conditioning")


class DeratingTests(unittest.TestCase):
    def test_ratio_is_applied_over_rated(self):
        self.assertAlmostEqual(voltage_derating_ratio(400.0, 1000.0), 0.4, places=9)

    def test_zero_rated_voltage_rejected(self):
        with self.assertRaises(ValueError):
            voltage_derating_ratio(400.0, 0.0)

    def test_negative_applied_voltage_rejected(self):
        with self.assertRaises(ValueError):
            voltage_derating_ratio(-1.0, 1000.0)

    def test_non_numeric_voltage_rejected(self):
        with self.assertRaises(ValueError):
            voltage_derating_ratio("400", 1000.0)

    def test_ratio_exactly_on_the_ceiling_is_admissible(self):
        record = assess_voltage_derating(500.0, 1000.0, "high-voltage")
        self.assertAlmostEqual(record["ratio"], record["ceiling"], places=9)
        self.assertTrue(record["within_ceiling"])
        self.assertEqual(record["findings"], [])

    def test_ratio_above_the_ceiling_is_a_finding(self):
        record = assess_voltage_derating(700.0, 1000.0, "high-voltage")
        self.assertFalse(record["within_ceiling"])
        self.assertEqual(len(record["findings"]), 1)

    def test_microwave_ceiling_differs_from_the_high_voltage_one(self):
        self.assertNotEqual(
            DERATING_CEILINGS["high-voltage"],
            DERATING_CEILINGS["high-power-microwave"],
        )

    def test_tighter_declared_ceiling_is_applied(self):
        record = assess_voltage_derating(400.0, 1000.0, "high-voltage", ceiling=0.3)
        self.assertAlmostEqual(record["ceiling"], 0.3, places=9)
        self.assertFalse(record["within_ceiling"])

    def test_looser_declared_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            assess_voltage_derating(400.0, 1000.0, "high-voltage", ceiling=0.8)

    def test_declared_ceiling_equal_to_the_default_is_accepted(self):
        record = assess_voltage_derating(
            400.0, 1000.0, "high-voltage", ceiling=DERATING_CEILINGS["high-voltage"]
        )
        self.assertAlmostEqual(
            record["ceiling"], DERATING_CEILINGS["high-voltage"], places=9
        )

    def test_ratio_tolerance_is_representation_sized(self):
        self.assertLess(RATIO_TOLERANCE, 1e-6)


class MultipactionTests(unittest.TestCase):
    def test_margin_of_a_factor_of_four(self):
        self.assertAlmostEqual(
            multipaction_margin_db(100.0, 400.0), 6.020599913279624, places=9
        )

    def test_equal_powers_give_zero_margin(self):
        self.assertAlmostEqual(multipaction_margin_db(50.0, 50.0), 0.0, places=9)

    def test_zero_applied_power_rejected(self):
        with self.assertRaises(ValueError):
            multipaction_margin_db(0.0, 400.0)

    def test_negative_threshold_power_rejected(self):
        with self.assertRaises(ValueError):
            multipaction_margin_db(100.0, -400.0)

    def test_comfortable_margin_meets_the_floor(self):
        record = assess_multipaction(
            {"applied_peak_power_w": 100.0, "multipaction_threshold_power_w": 800.0}
        )
        self.assertTrue(record["meets_margin"])
        self.assertEqual(record["findings"], [])

    def test_margin_exactly_on_the_required_floor_is_admissible(self):
        margin = multipaction_margin_db(100.0, 400.0)
        record = assess_multipaction(
            {"applied_peak_power_w": 100.0, "multipaction_threshold_power_w": 400.0},
            required_margin_db=margin,
        )
        self.assertAlmostEqual(record["margin_db"], record["required_margin_db"],
                               places=9)
        self.assertTrue(record["meets_margin"])

    def test_thin_margin_is_a_finding(self):
        record = assess_multipaction(
            {"applied_peak_power_w": 100.0, "multipaction_threshold_power_w": 150.0}
        )
        self.assertFalse(record["meets_margin"])
        self.assertEqual(len(record["findings"]), 1)

    def test_missing_threshold_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_multipaction({"applied_peak_power_w": 100.0})

    def test_default_required_margin_is_used_when_none_declared(self):
        record = assess_multipaction(
            {"applied_peak_power_w": 100.0, "multipaction_threshold_power_w": 800.0}
        )
        self.assertAlmostEqual(
            record["required_margin_db"], REQUIRED_MULTIPACTION_MARGIN_DB, places=9
        )

    def test_margin_tolerance_is_representation_sized(self):
        self.assertLess(MARGIN_TOLERANCE, 1e-6)


class CoronaTests(unittest.TestCase):
    def test_vacuum_only_operation_raises_no_finding(self):
        record = assess_corona_control([1.0e-4], [])
        self.assertEqual(record["exposed_pressures_pa"], [])
        self.assertEqual(record["findings"], [])

    def test_pressure_inside_the_band_without_mitigation_is_a_finding(self):
        record = assess_corona_control([2.0e3], [])
        self.assertEqual(len(record["exposed_pressures_pa"]), 1)
        self.assertEqual(len(record["findings"]), 1)

    def test_pressure_inside_the_band_with_mitigation_is_clean(self):
        record = assess_corona_control([2.0e3], ["encapsulation"])
        self.assertEqual(record["findings"], [])
        self.assertEqual(record["mitigations"], ["encapsulation"])

    def test_band_edges_count_as_exposed(self):
        low, high = CORONA_PRESSURE_BAND_PA
        record = assess_corona_control([low, high], [])
        self.assertEqual(len(record["exposed_pressures_pa"]), 2)

    def test_sea_level_pressure_is_above_the_band(self):
        record = assess_corona_control([1.013e5], [])
        self.assertEqual(record["exposed_pressures_pa"], [])

    def test_unknown_mitigation_rejected(self):
        with self.assertRaises(ValueError):
            assess_corona_control([2.0e3], ["wrap-it-in-tape"])

    def test_repeated_mitigation_rejected(self):
        with self.assertRaises(ValueError):
            assess_corona_control([2.0e3], ["encapsulation", "encapsulation"])

    def test_non_sequence_pressures_rejected(self):
        with self.assertRaises(ValueError):
            assess_corona_control(2.0e3, [])

    def test_every_recognized_mitigation_is_accepted(self):
        for mitigation in CORONA_MITIGATIONS:
            record = assess_corona_control([2.0e3], [mitigation])
            self.assertEqual(record["findings"], [])


class ScreeningTests(unittest.TestCase):
    def test_complete_high_voltage_screening_leaves_nothing_absent(self):
        self.assertEqual(
            missing_screening_steps(
                "high-voltage", list(MANDATORY_SCREENING["high-voltage"])
            ),
            [],
        )

    def test_absent_step_is_named(self):
        absent = missing_screening_steps("high-voltage", ["construction-analysis"])
        self.assertIn("voltage-conditioning", absent)
        self.assertIn("partial-discharge-measurement", absent)

    def test_no_declared_steps_names_every_required_step(self):
        absent = missing_screening_steps("high-power-microwave", None)
        self.assertEqual(
            len(absent), len(MANDATORY_SCREENING["high-power-microwave"])
        )

    def test_repeated_screening_step_rejected(self):
        with self.assertRaises(ValueError):
            missing_screening_steps(
                "high-voltage", ["voltage-conditioning", "voltage_conditioning"]
            )

    def test_screening_sets_differ_between_categories(self):
        self.assertNotEqual(
            set(MANDATORY_SCREENING["high-voltage"]),
            set(MANDATORY_SCREENING["high-power-microwave"]),
        )


class ApplicationAssessmentTests(unittest.TestCase):
    def test_clean_high_voltage_application_is_fit(self):
        result = assess_high_voltage_part(_hv_application())
        self.assertTrue(result["fit_for_class_1_use"])
        self.assertEqual(result["findings"], [])

    def test_clean_microwave_application_is_fit(self):
        result = assess_high_voltage_part(_mw_application())
        self.assertTrue(result["fit_for_class_1_use"])
        self.assertIsNotNone(result["multipaction"])

    def test_microwave_part_without_power_margin_block_is_a_finding(self):
        result = assess_high_voltage_part(_mw_application(multipaction=None))
        self.assertFalse(result["fit_for_class_1_use"])
        self.assertTrue(any("power-margin" in f for f in result["findings"]))

    def test_high_voltage_part_needs_no_power_margin_block(self):
        result = assess_high_voltage_part(_hv_application())
        self.assertIsNone(result["multipaction"])

    def test_microwave_part_outside_vacuum_skips_the_power_margin(self):
        result = assess_high_voltage_part(
            _mw_application(operates_in_vacuum=False, multipaction=None)
        )
        self.assertIsNone(result["multipaction"])
        self.assertTrue(result["fit_for_class_1_use"])

    def test_overstressed_voltage_reaches_the_verdict(self):
        result = assess_high_voltage_part(_hv_application(applied_voltage_v=900.0))
        self.assertFalse(result["fit_for_class_1_use"])

    def test_absent_screening_reaches_the_verdict(self):
        result = assess_high_voltage_part(_hv_application(screening_steps=[]))
        self.assertEqual(
            len(result["absent_screening_steps"]),
            len(MANDATORY_SCREENING["high-voltage"]),
        )
        self.assertFalse(result["fit_for_class_1_use"])

    def test_missing_application_key_rejected(self):
        application = _hv_application()
        del application["rated_voltage_v"]
        with self.assertRaises(ValueError):
            assess_high_voltage_part(application)

    def test_non_mapping_application_rejected(self):
        with self.assertRaises(ValueError):
            assess_high_voltage_part(["part"])

    def test_non_boolean_vacuum_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_high_voltage_part(_hv_application(operates_in_vacuum="yes"))

    def test_every_finding_is_named_not_only_the_first(self):
        result = assess_high_voltage_part(
            _hv_application(
                applied_voltage_v=900.0,
                screening_steps=[],
                energized_pressures_pa=[2.0e3],
                corona_mitigations=[],
            )
        )
        self.assertGreaterEqual(len(result["findings"]), 5)


if __name__ == "__main__":
    unittest.main()
