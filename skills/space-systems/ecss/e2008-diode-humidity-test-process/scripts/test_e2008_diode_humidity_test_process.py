"""Contract tests for the clause 9.6.6.1.2 diode chamber loading logic."""

import math
import unittest

from e2008_diode_humidity_test_process_logic import (
    CHAMBER_LOADING_ACCEPTED,
    CHAMBER_LOADING_DEFICIENT,
    DEFAULT_DIODE_CHAMBER_POLICY,
    DIODE_SAMPLE_PLAN_DEFICIENT,
    LOADING_VERDICTS,
    SUBGROUP_UNDER_TEST,
    TERMINAL_CONDENSATION_RISK,
    assess_diode_damp_loading,
    case_dew_point_c,
    case_dew_point_margin_k,
    package_gap_mm,
    pressure_in_ambient_band,
    saturation_vapour_pressure_pa,
    subgroup_diode_count,
    tray_free_flow_fraction,
    validate_diode_chamber_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_DIODE_CHAMBER_POLICY)
    policy.update(overrides)
    return policy


def _load(**overrides):
    load = {
        "device_count": 6,
        "air_temperature_c": 60.0,
        "relative_humidity_pct": 85.0,
        "case_temperature_c": 60.0,
        "chamber_pressure_kpa": 101.3,
        "tray_area_mm2": 40000.0,
        "package_footprint_mm2": 400.0,
        "row_length_mm": 200.0,
        "package_width_mm": 20.0,
        "stabilisation_dwell_h": 4.0,
        "exposure_duration_h": 1000.0,
    }
    load.update(overrides)
    return load


def _case(**overrides):
    case = {
        "sample_plan": {"subgroup": "O", "diode_count": 6},
        "chamber_load": _load(),
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_diode_chamber_policy(DEFAULT_DIODE_CHAMBER_POLICY),
            DEFAULT_DIODE_CHAMBER_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_chamber_policy("ambient")

    def test_an_inverted_pressure_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_chamber_policy(
                _policy(min_chamber_pressure_kpa=120.0)
            )

    def test_a_free_flow_floor_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_chamber_policy(_policy(min_tray_free_flow_fraction=1.0))

    def test_zero_dew_point_margin_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_chamber_policy(_policy(min_case_dew_point_margin_k=0.0))

    def test_fractional_minimum_device_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_chamber_policy(_policy(min_subgroup_diodes=5.5))

    def test_every_verdict_is_declared(self):
        self.assertEqual(len(set(LOADING_VERDICTS)), 4)


class PsychrometryTests(unittest.TestCase):
    def test_saturation_pressure_follows_the_magnus_form(self):
        expected = 610.94 * math.exp(17.625 * 60.0 / (243.04 + 60.0))
        self.assertAlmostEqual(
            _ratio(saturation_vapour_pressure_pa(60.0), expected), 1.0, places=12
        )

    def test_saturated_air_dews_at_its_own_temperature(self):
        self.assertAlmostEqual(case_dew_point_c(60.0, 100.0), 60.0, places=9)

    def test_drier_air_dews_lower(self):
        self.assertLess(case_dew_point_c(60.0, 40.0), case_dew_point_c(60.0, 85.0))

    def test_margin_is_the_case_above_the_dew_point(self):
        dew = case_dew_point_c(60.0, 85.0)
        self.assertAlmostEqual(
            case_dew_point_margin_k(dew + 5.0, 60.0, 85.0), 5.0, places=9
        )

    def test_a_case_below_the_dew_point_gives_a_negative_margin(self):
        dew = case_dew_point_c(60.0, 85.0)
        self.assertLess(case_dew_point_margin_k(dew - 1.0, 60.0, 85.0), 0.0)

    def test_humidity_above_one_hundred_per_cent_rejected(self):
        with self.assertRaises(ValueError):
            case_dew_point_c(60.0, 130.0)

    def test_zero_humidity_rejected(self):
        with self.assertRaises(ValueError):
            case_dew_point_c(60.0, 0.0)

    def test_a_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            saturation_vapour_pressure_pa(-300.0)


class TrayGeometryTests(unittest.TestCase):
    def test_free_flow_is_the_share_of_the_tray_left_open(self):
        fraction = tray_free_flow_fraction(
            {
                "tray_area_mm2": 1000.0,
                "package_footprint_mm2": 100.0,
                "device_count": 4,
            }
        )
        self.assertAlmostEqual(fraction, 0.6, places=9)

    def test_a_fully_covered_tray_leaves_no_free_flow(self):
        fraction = tray_free_flow_fraction(
            {
                "tray_area_mm2": 400.0,
                "package_footprint_mm2": 100.0,
                "device_count": 4,
            }
        )
        self.assertAlmostEqual(fraction, 0.0, places=9)

    def test_a_load_larger_than_its_tray_rejected(self):
        with self.assertRaises(ValueError):
            tray_free_flow_fraction(
                {
                    "tray_area_mm2": 300.0,
                    "package_footprint_mm2": 100.0,
                    "device_count": 4,
                }
            )

    def test_a_non_mapping_tray_rejected(self):
        with self.assertRaises(ValueError):
            tray_free_flow_fraction([1000.0, 100.0, 4])

    def test_the_row_gap_counts_both_end_gaps(self):
        gap = package_gap_mm(
            {"row_length_mm": 100.0, "package_width_mm": 10.0, "device_count": 4}
        )
        self.assertAlmostEqual(gap, 12.0, places=9)

    def test_a_denser_row_leaves_a_smaller_gap(self):
        loose = package_gap_mm(
            {"row_length_mm": 100.0, "package_width_mm": 10.0, "device_count": 4}
        )
        tight = package_gap_mm(
            {"row_length_mm": 100.0, "package_width_mm": 10.0, "device_count": 8}
        )
        self.assertLess(tight, loose)

    def test_a_row_too_short_for_its_packages_rejected(self):
        with self.assertRaises(ValueError):
            package_gap_mm(
                {"row_length_mm": 30.0, "package_width_mm": 10.0, "device_count": 4}
            )

    def test_a_fractional_device_count_rejected(self):
        with self.assertRaises(ValueError):
            package_gap_mm(
                {"row_length_mm": 100.0, "package_width_mm": 10.0, "device_count": 4.5}
            )


class SamplePlanTests(unittest.TestCase):
    def test_the_subgroup_under_test_is_counted(self):
        self.assertEqual(
            subgroup_diode_count(
                {"subgroup": SUBGROUP_UNDER_TEST, "diode_count": 6}
            ),
            6,
        )

    def test_a_lower_case_subgroup_label_still_counts(self):
        self.assertEqual(subgroup_diode_count({"subgroup": "o", "diode_count": 6}), 6)

    def test_another_subgroup_contributes_nothing(self):
        self.assertEqual(subgroup_diode_count({"subgroup": "D", "diode_count": 6}), 0)

    def test_a_missing_subgroup_label_rejected(self):
        with self.assertRaises(ValueError):
            subgroup_diode_count({"diode_count": 6})

    def test_a_non_mapping_sample_plan_rejected(self):
        with self.assertRaises(ValueError):
            subgroup_diode_count(["O", 6])


class PressureBandTests(unittest.TestCase):
    def test_the_ambient_setpoint_sits_in_the_band(self):
        self.assertTrue(pressure_in_ambient_band(101.3, _policy()))

    def test_a_pressure_exactly_on_the_lower_edge_is_in_band(self):
        policy = _policy()
        edge = float(policy["min_chamber_pressure_kpa"])
        self.assertAlmostEqual(edge, policy["min_chamber_pressure_kpa"], places=9)
        self.assertTrue(pressure_in_ambient_band(edge, policy))

    def test_a_pressure_exactly_on_the_upper_edge_is_in_band(self):
        policy = _policy()
        edge = float(policy["max_chamber_pressure_kpa"])
        self.assertTrue(pressure_in_ambient_band(edge, policy))

    def test_a_pressurised_chamber_is_out_of_band(self):
        self.assertFalse(pressure_in_ambient_band(250.0, _policy()))

    def test_a_pumped_down_chamber_is_out_of_band(self):
        self.assertFalse(pressure_in_ambient_band(20.0, _policy()))

    def test_zero_pressure_rejected(self):
        with self.assertRaises(ValueError):
            pressure_in_ambient_band(0.0, _policy())


class LoadingAssessmentTests(unittest.TestCase):
    def test_a_nominal_loading_is_accepted(self):
        result = assess_diode_damp_loading(_case())
        self.assertEqual(result["verdict"], CHAMBER_LOADING_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_the_dew_point_and_margin_are_reported(self):
        result = assess_diode_damp_loading(_case())
        expected = case_dew_point_c(60.0, 85.0)
        self.assertAlmostEqual(
            _ratio(result["dew_point_c"], expected), 1.0, places=12
        )
        self.assertAlmostEqual(
            _ratio(result["case_dew_point_margin_k"], 60.0 - expected),
            1.0,
            places=12,
        )

    def test_a_cold_diode_case_is_a_condensation_risk(self):
        dew = case_dew_point_c(60.0, 85.0)
        result = assess_diode_damp_loading(
            _case(chamber_load=_load(case_temperature_c=dew - 2.0))
        )
        self.assertEqual(result["verdict"], TERMINAL_CONDENSATION_RISK)
        self.assertLess(result["case_dew_point_margin_k"], 0.0)

    def test_a_margin_exactly_at_the_floor_is_accepted(self):
        policy = _policy()
        dew = case_dew_point_c(60.0, 85.0)
        surface = dew + policy["min_case_dew_point_margin_k"]
        result = assess_diode_damp_loading(
            _case(chamber_load=_load(case_temperature_c=surface)), policy
        )
        self.assertAlmostEqual(
            result["case_dew_point_margin_k"],
            policy["min_case_dew_point_margin_k"],
            places=9,
        )
        self.assertEqual(result["verdict"], CHAMBER_LOADING_ACCEPTED)

    def test_condensation_outranks_a_short_sample(self):
        dew = case_dew_point_c(60.0, 85.0)
        result = assess_diode_damp_loading(
            _case(
                sample_plan={"subgroup": "O", "diode_count": 2},
                chamber_load=_load(device_count=2, case_temperature_c=dew - 2.0),
            )
        )
        self.assertEqual(result["verdict"], TERMINAL_CONDENSATION_RISK)

    def test_too_few_subgroup_diodes_is_a_plan_deficiency(self):
        result = assess_diode_damp_loading(
            _case(
                sample_plan={"subgroup": "O", "diode_count": 2},
                chamber_load=_load(device_count=2),
            )
        )
        self.assertEqual(result["verdict"], DIODE_SAMPLE_PLAN_DEFICIENT)

    def test_diodes_drawn_from_another_subgroup_do_not_fill_the_plan(self):
        result = assess_diode_damp_loading(
            _case(sample_plan={"subgroup": "D", "diode_count": 12})
        )
        self.assertEqual(result["verdict"], DIODE_SAMPLE_PLAN_DEFICIENT)
        self.assertEqual(result["subgroup_diodes"], 0)

    def test_a_sample_count_exactly_at_the_floor_is_accepted(self):
        policy = _policy()
        floor = int(policy["min_subgroup_diodes"])
        result = assess_diode_damp_loading(
            _case(
                sample_plan={"subgroup": "O", "diode_count": floor},
                chamber_load=_load(device_count=floor),
            ),
            policy,
        )
        self.assertEqual(result["verdict"], CHAMBER_LOADING_ACCEPTED)

    def test_a_tray_short_of_the_planned_devices_is_a_loading_deficiency(self):
        result = assess_diode_damp_loading(
            _case(
                sample_plan={"subgroup": "O", "diode_count": 12},
                chamber_load=_load(device_count=6),
            )
        )
        self.assertEqual(result["verdict"], CHAMBER_LOADING_DEFICIENT)
        self.assertEqual(result["loaded_devices"], 6)

    def test_a_pressurised_chamber_is_a_loading_deficiency(self):
        result = assess_diode_damp_loading(
            _case(chamber_load=_load(chamber_pressure_kpa=300.0))
        )
        self.assertEqual(result["verdict"], CHAMBER_LOADING_DEFICIENT)
        self.assertFalse(result["pressure_in_band"])

    def test_a_crowded_tray_is_a_loading_deficiency(self):
        result = assess_diode_damp_loading(
            _case(chamber_load=_load(tray_area_mm2=3000.0))
        )
        self.assertEqual(result["verdict"], CHAMBER_LOADING_DEFICIENT)
        self.assertLess(result["tray_free_flow_fraction"], 0.3)

    def test_packages_too_close_together_are_a_loading_deficiency(self):
        result = assess_diode_damp_loading(
            _case(chamber_load=_load(row_length_mm=125.0))
        )
        self.assertEqual(result["verdict"], CHAMBER_LOADING_DEFICIENT)

    def test_a_short_stabilisation_dwell_is_a_loading_deficiency(self):
        result = assess_diode_damp_loading(
            _case(chamber_load=_load(stabilisation_dwell_h=0.25))
        )
        self.assertEqual(result["verdict"], CHAMBER_LOADING_DEFICIENT)

    def test_a_truncated_exposure_is_a_loading_deficiency(self):
        result = assess_diode_damp_loading(
            _case(chamber_load=_load(exposure_duration_h=200.0))
        )
        self.assertEqual(result["verdict"], CHAMBER_LOADING_DEFICIENT)

    def test_every_loading_finding_is_reported_not_only_the_first(self):
        result = assess_diode_damp_loading(
            _case(
                chamber_load=_load(
                    chamber_pressure_kpa=300.0,
                    stabilisation_dwell_h=0.25,
                    exposure_duration_h=200.0,
                )
            )
        )
        self.assertEqual(len(result["findings"]), 3)

    def test_missing_sample_plan_rejected(self):
        case = _case()
        del case["sample_plan"]
        with self.assertRaises(ValueError):
            assess_diode_damp_loading(case)

    def test_missing_chamber_load_rejected(self):
        case = _case()
        del case["chamber_load"]
        with self.assertRaises(ValueError):
            assess_diode_damp_loading(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_damp_loading(["sample_plan"])

    def test_a_negative_exposure_duration_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_damp_loading(
                _case(chamber_load=_load(exposure_duration_h=-10.0))
            )


if __name__ == "__main__":
    unittest.main()
