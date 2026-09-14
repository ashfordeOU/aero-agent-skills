"""Contract tests for the clause 12.6.10 temperature extreme exposure run.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused exposure policy,
a soak that stops inside the service extreme, a soak driven past the
package storage rating, a dwell or ramp outside its limit, a programme that
covers only one end of service, a sample below its floor, and a device that
came back outside its drift limits.
"""

import unittest

from e2008_blocking_diode_temperature_robustness_logic import (
    COLD,
    DEFAULT_EXPOSURE_POLICY,
    EXPOSED_DEVICES_DEGRADED,
    EXPOSURE_PLAN_INVALID,
    EXPOSURE_SAMPLE_BELOW_FLOOR,
    HOT,
    ROBUSTNESS_DEMONSTRATED,
    SERVICE_EXTREME_NOT_COVERED,
    assess_temperature_extreme_robustness,
    dwell_sufficient,
    extremes_covered,
    forward_drift_fraction,
    grade_device,
    leakage_growth_ratio,
    missing_extremes,
    ramp_within_limit,
    required_soak_temperature_c,
    soak_margin_c,
    soak_reaches_extreme,
    soak_within_package_rating,
    survivor_fraction,
    validate_exposure,
    validate_exposure_policy,
    validate_package_rating,
    validate_service_range,
)

SERVICE_RANGE = {"min_c": -95.0, "max_c": 80.0}
PACKAGE_RATING = {"min_c": -135.0, "max_c": 130.0}


def _policy(**overrides):
    policy = dict(DEFAULT_EXPOSURE_POLICY)
    policy.update(overrides)
    return policy


def _exposures(**overrides):
    plan = {
        "cold": {
            "extreme": COLD,
            "soak_temperature_c": -110.0,
            "dwell_hours": 4.0,
            "ramp_rate_c_per_min": 2.0,
        },
        "hot": {
            "extreme": HOT,
            "soak_temperature_c": 95.0,
            "dwell_hours": 4.0,
            "ramp_rate_c_per_min": 2.0,
        },
    }
    plan.update(overrides)
    return [plan["cold"], plan["hot"]]


def _device(identifier, after_v=0.71, after_ua=0.09):
    return {
        "id": identifier,
        "forward_voltage_before_v": 0.70,
        "forward_voltage_after_v": after_v,
        "reverse_leakage_before_ua": 0.05,
        "reverse_leakage_after_ua": after_ua,
    }


def _devices(count=6):
    return [_device("bd-%02d" % index) for index in range(1, count + 1)]


def _case(**overrides):
    case = {
        "service_range_c": dict(SERVICE_RANGE),
        "package_rating_c": dict(PACKAGE_RATING),
        "exposures": _exposures(),
        "devices": _devices(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_exposure_policy(DEFAULT_EXPOSURE_POLICY), DEFAULT_EXPOSURE_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure_policy("min_dwell_hours")

    def test_negative_soak_margin_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure_policy(_policy(required_hot_margin_c=-5.0))

    def test_leakage_growth_ratio_below_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure_policy(_policy(max_leakage_growth_ratio=0.5))

    def test_survivor_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure_policy(_policy(required_survivor_fraction=1.2))

    def test_whole_forward_drift_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure_policy(_policy(max_forward_drift_fraction=1.0))


class RangeTests(unittest.TestCase):
    def test_service_range_is_read_back(self):
        low, high = validate_service_range(SERVICE_RANGE)
        self.assertAlmostEqual(low, -95.0, places=9)
        self.assertAlmostEqual(high, 80.0, places=9)

    def test_inverted_service_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_service_range({"min_c": 80.0, "max_c": -95.0})

    def test_inverted_package_rating_rejected(self):
        with self.assertRaises(ValueError):
            validate_package_rating({"min_c": 130.0, "max_c": -135.0})


class SoakTests(unittest.TestCase):
    def test_required_hot_soak_sits_past_the_service_ceiling(self):
        self.assertAlmostEqual(
            required_soak_temperature_c(HOT, SERVICE_RANGE), 90.0, places=9
        )

    def test_required_cold_soak_sits_past_the_service_floor(self):
        self.assertAlmostEqual(
            required_soak_temperature_c(COLD, SERVICE_RANGE), -105.0, places=9
        )

    def test_unknown_extreme_rejected(self):
        with self.assertRaises(ValueError):
            required_soak_temperature_c("warm", SERVICE_RANGE)

    def test_achieved_margin_measured_at_both_ends(self):
        self.assertAlmostEqual(soak_margin_c(HOT, 95.0, SERVICE_RANGE), 15.0, places=9)
        self.assertAlmostEqual(
            soak_margin_c(COLD, -110.0, SERVICE_RANGE), 15.0, places=9
        )

    def test_soak_exactly_at_the_required_margin_admitted(self):
        self.assertTrue(soak_reaches_extreme(HOT, 90.0, SERVICE_RANGE))
        self.assertTrue(soak_reaches_extreme(COLD, -105.0, SERVICE_RANGE))

    def test_soak_inside_the_service_extreme_refused(self):
        self.assertFalse(soak_reaches_extreme(HOT, 82.0, SERVICE_RANGE))

    def test_soak_past_the_package_rating_refused(self):
        self.assertFalse(soak_within_package_rating(HOT, 140.0, PACKAGE_RATING))
        self.assertTrue(soak_within_package_rating(HOT, 130.0, PACKAGE_RATING))


class ExposureTests(unittest.TestCase):
    def test_exposure_is_read_back(self):
        extreme, soak, dwell, ramp = validate_exposure(_exposures()[0])
        self.assertEqual(extreme, COLD)
        self.assertAlmostEqual(soak, -110.0, places=9)
        self.assertAlmostEqual(dwell, 4.0, places=9)
        self.assertAlmostEqual(ramp, 2.0, places=9)

    def test_unknown_extreme_label_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure(
                {
                    "extreme": "tepid",
                    "soak_temperature_c": 95.0,
                    "dwell_hours": 4.0,
                    "ramp_rate_c_per_min": 2.0,
                }
            )

    def test_zero_dwell_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure(
                {
                    "extreme": HOT,
                    "soak_temperature_c": 95.0,
                    "dwell_hours": 0.0,
                    "ramp_rate_c_per_min": 2.0,
                }
            )

    def test_dwell_exactly_at_the_floor_admitted(self):
        self.assertTrue(dwell_sufficient(2.0))
        self.assertFalse(dwell_sufficient(1.5))

    def test_ramp_exactly_at_the_ceiling_admitted(self):
        self.assertTrue(ramp_within_limit(5.0))
        self.assertFalse(ramp_within_limit(9.0))


class CoverageTests(unittest.TestCase):
    def test_both_extremes_covered_by_the_nominal_plan(self):
        self.assertEqual(extremes_covered(_exposures()), [COLD, HOT])
        self.assertEqual(missing_extremes(_exposures()), [])

    def test_hot_only_plan_leaves_the_cold_end_uncovered(self):
        self.assertEqual(missing_extremes([_exposures()[1]]), [COLD])

    def test_empty_plan_rejected(self):
        with self.assertRaises(ValueError):
            extremes_covered([])


class DeviceTests(unittest.TestCase):
    def test_forward_drift_is_a_share_of_the_pre_exposure_drop(self):
        self.assertAlmostEqual(forward_drift_fraction(0.70, 0.77), 0.1, places=9)

    def test_leakage_growth_is_a_ratio(self):
        self.assertAlmostEqual(leakage_growth_ratio(0.05, 0.15), 3.0, places=9)

    def test_intact_device_is_graded_intact(self):
        graded = grade_device(_device("bd-01"))
        self.assertTrue(graded["intact"])
        self.assertEqual(graded["reasons"], [])

    def test_drifted_device_is_graded_degraded(self):
        graded = grade_device(_device("bd-02", after_v=0.80))
        self.assertFalse(graded["intact"])
        self.assertTrue(graded["reasons"])

    def test_leaky_device_is_graded_degraded(self):
        graded = grade_device(_device("bd-03", after_ua=0.40))
        self.assertFalse(graded["intact"])

    def test_survivor_share_counts_intact_devices(self):
        graded = [
            grade_device(_device("bd-01")),
            grade_device(_device("bd-02", after_v=0.80)),
        ]
        self.assertAlmostEqual(survivor_fraction(graded), 0.5, places=9)


class RunTests(unittest.TestCase):
    def test_nominal_programme_demonstrates_robustness(self):
        result = assess_temperature_extreme_robustness(_case())
        self.assertEqual(result["verdict"], ROBUSTNESS_DEMONSTRATED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["device_count"], 6)
        self.assertAlmostEqual(result["survivor_fraction"], 1.0, places=9)

    def test_shallow_hot_soak_invalidates_the_plan(self):
        exposures = _exposures(
            hot={
                "extreme": HOT,
                "soak_temperature_c": 82.0,
                "dwell_hours": 4.0,
                "ramp_rate_c_per_min": 2.0,
            }
        )
        result = assess_temperature_extreme_robustness(_case(exposures=exposures))
        self.assertEqual(result["verdict"], EXPOSURE_PLAN_INVALID)

    def test_soak_past_the_storage_rating_invalidates_the_plan(self):
        exposures = _exposures(
            hot={
                "extreme": HOT,
                "soak_temperature_c": 150.0,
                "dwell_hours": 4.0,
                "ramp_rate_c_per_min": 2.0,
            }
        )
        result = assess_temperature_extreme_robustness(_case(exposures=exposures))
        self.assertEqual(result["verdict"], EXPOSURE_PLAN_INVALID)

    def test_short_dwell_invalidates_the_plan(self):
        exposures = _exposures(
            cold={
                "extreme": COLD,
                "soak_temperature_c": -110.0,
                "dwell_hours": 0.5,
                "ramp_rate_c_per_min": 2.0,
            }
        )
        result = assess_temperature_extreme_robustness(_case(exposures=exposures))
        self.assertEqual(result["verdict"], EXPOSURE_PLAN_INVALID)

    def test_fast_ramp_invalidates_the_plan(self):
        exposures = _exposures(
            cold={
                "extreme": COLD,
                "soak_temperature_c": -110.0,
                "dwell_hours": 4.0,
                "ramp_rate_c_per_min": 20.0,
            }
        )
        result = assess_temperature_extreme_robustness(_case(exposures=exposures))
        self.assertEqual(result["verdict"], EXPOSURE_PLAN_INVALID)

    def test_hot_only_programme_leaves_an_extreme_uncovered(self):
        result = assess_temperature_extreme_robustness(
            _case(exposures=[_exposures()[1]])
        )
        self.assertEqual(result["verdict"], SERVICE_EXTREME_NOT_COVERED)
        self.assertEqual(result["missing_extremes"], [COLD])

    def test_sample_below_the_floor_is_reported(self):
        result = assess_temperature_extreme_robustness(_case(devices=_devices(3)))
        self.assertEqual(result["verdict"], EXPOSURE_SAMPLE_BELOW_FLOOR)

    def test_one_degraded_device_fails_the_programme(self):
        devices = _devices()
        devices[2] = _device("bd-03", after_ua=0.50)
        result = assess_temperature_extreme_robustness(_case(devices=devices))
        self.assertEqual(result["verdict"], EXPOSED_DEVICES_DEGRADED)
        self.assertTrue(result["findings"])

    def test_duplicate_device_identifier_rejected(self):
        devices = _devices()
        devices[1]["id"] = devices[0]["id"]
        with self.assertRaises(ValueError):
            assess_temperature_extreme_robustness(_case(devices=devices))

    def test_case_without_a_service_range_rejected(self):
        case = _case()
        del case["service_range_c"]
        with self.assertRaises(ValueError):
            assess_temperature_extreme_robustness(case)


if __name__ == "__main__":
    unittest.main()
