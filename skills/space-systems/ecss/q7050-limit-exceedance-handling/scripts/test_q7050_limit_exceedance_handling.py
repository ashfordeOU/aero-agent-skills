"""Contract tests for the cleanliness limit exceedance handling logic."""

import unittest

from q7050_limit_exceedance_handling_logic import (
    CLOSURE_ITEMS,
    DISPOSITIONS,
    SENSITIVITY_WEIGHTS,
    SEVERITIES,
    assess_exceedance,
    closure_completeness,
    deposition_number_per_m2,
    exceedance_ratio,
    grade_reverification,
    is_exceedance,
    required_consecutive_reverifications,
    select_disposition,
    sensitivity_weight,
    severity_category,
)


def full_closure():
    return {item: "recorded" for item in CLOSURE_ITEMS}


def spec(**overrides):
    base = {
        "measured": 150.0,
        "limit": 100.0,
        "sensitivity": "standard",
        "cleanable": True,
        "reverifiable": True,
        "exposure": {
            "concentration_per_m3": 1.0e6,
            "deposition_velocity_m_s": 0.001,
            "exposure_hours": 1.0,
        },
        "reverification_results": [60.0],
        "closure_package": full_closure(),
    }
    base.update(overrides)
    return base


class RatioTests(unittest.TestCase):
    def test_ratio_is_a_multiple_of_the_limit(self):
        self.assertAlmostEqual(exceedance_ratio(150.0, 100.0), 1.5, places=12)

    def test_result_under_the_limit_gives_a_ratio_below_one(self):
        self.assertAlmostEqual(exceedance_ratio(40.0, 100.0), 0.4, places=12)

    def test_result_exactly_on_the_limit_is_not_an_exceedance(self):
        self.assertFalse(is_exceedance(100.0, 100.0))

    def test_result_above_the_limit_is_an_exceedance(self):
        self.assertTrue(is_exceedance(100.5, 100.0))

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            exceedance_ratio(150.0, 0.0)

    def test_negative_measurement_rejected(self):
        with self.assertRaises(ValueError):
            exceedance_ratio(-1.0, 100.0)

    def test_boolean_measurement_rejected(self):
        with self.assertRaises(ValueError):
            exceedance_ratio(True, 100.0)


class SensitivityTests(unittest.TestCase):
    def test_standard_sensitivity_is_unity(self):
        self.assertAlmostEqual(sensitivity_weight("standard"), 1.0, places=12)

    def test_critical_sensitivity_weighs_most(self):
        self.assertGreater(
            sensitivity_weight("critical"), sensitivity_weight("sensitive")
        )

    def test_tolerant_sensitivity_weighs_least(self):
        self.assertAlmostEqual(
            sensitivity_weight("tolerant"), min(SENSITIVITY_WEIGHTS.values()),
            places=12,
        )

    def test_unknown_sensitivity_rejected(self):
        with self.assertRaises(ValueError):
            sensitivity_weight("fragile")


class SeverityTests(unittest.TestCase):
    def test_no_exceedance_is_severity_none(self):
        result = severity_category(80.0, 100.0)
        self.assertEqual(result["severity"], "none")

    def test_small_exceedance_is_minor(self):
        self.assertEqual(severity_category(150.0, 100.0)["severity"], "minor")

    def test_weighted_ratio_exactly_at_the_minor_ceiling_stays_minor(self):
        result = severity_category(200.0, 100.0, "standard")
        self.assertAlmostEqual(result["weighted_ratio"], 2.0, places=9)
        self.assertEqual(result["severity"], "minor")

    def test_mid_exceedance_is_major(self):
        self.assertEqual(severity_category(500.0, 100.0)["severity"], "major")

    def test_weighted_ratio_exactly_at_the_major_ceiling_stays_major(self):
        result = severity_category(1000.0, 100.0, "standard")
        self.assertAlmostEqual(result["weighted_ratio"], 10.0, places=9)
        self.assertEqual(result["severity"], "major")

    def test_large_exceedance_is_critical(self):
        self.assertEqual(severity_category(2000.0, 100.0)["severity"], "critical")

    def test_sensitive_hardware_raises_the_severity_at_the_same_ratio(self):
        plain = severity_category(150.0, 100.0, "standard")["severity"]
        sharp = severity_category(150.0, 100.0, "critical")["severity"]
        self.assertEqual(plain, "minor")
        self.assertEqual(sharp, "major")

    def test_tolerant_hardware_lowers_the_severity_at_the_same_ratio(self):
        self.assertEqual(
            severity_category(300.0, 100.0, "tolerant")["severity"], "minor"
        )

    def test_severity_is_from_the_declared_set(self):
        self.assertIn(severity_category(150.0, 100.0)["severity"], SEVERITIES)


class DepositionTests(unittest.TestCase):
    def test_deposition_is_concentration_times_velocity_times_time(self):
        self.assertAlmostEqual(
            deposition_number_per_m2(1.0e6, 0.001, 1.0) / 3.6e6, 1.0, places=9
        )

    def test_deposition_scales_with_exposure(self):
        one = deposition_number_per_m2(1.0e6, 0.001, 1.0)
        ten = deposition_number_per_m2(1.0e6, 0.001, 10.0)
        self.assertAlmostEqual(ten, one * 10.0, places=6)

    def test_zero_exposure_deposits_nothing(self):
        self.assertAlmostEqual(
            deposition_number_per_m2(1.0e6, 0.001, 0.0), 0.0, places=12
        )

    def test_zero_velocity_rejected(self):
        with self.assertRaises(ValueError):
            deposition_number_per_m2(1.0e6, 0.0, 1.0)

    def test_negative_exposure_rejected(self):
        with self.assertRaises(ValueError):
            deposition_number_per_m2(1.0e6, 0.001, -1.0)


class DispositionTests(unittest.TestCase):
    def test_no_severity_is_accepted_as_is(self):
        self.assertEqual(select_disposition("none"), "accept-as-is")

    def test_minor_cleanable_is_cleaned_and_reverified(self):
        self.assertEqual(select_disposition("minor"), "clean-and-reverify")

    def test_minor_uncleanable_goes_to_engineering(self):
        self.assertEqual(
            select_disposition("minor", cleanable=False), "engineering-assessment"
        )

    def test_major_cleanable_is_cleaned_and_reverified(self):
        self.assertEqual(select_disposition("major"), "clean-and-reverify")

    def test_critical_cleanable_still_goes_to_engineering(self):
        self.assertEqual(select_disposition("critical"), "engineering-assessment")

    def test_critical_uncleanable_is_rejected(self):
        self.assertEqual(select_disposition("critical", cleanable=False), "reject")

    def test_unverifiable_major_is_rejected(self):
        self.assertEqual(
            select_disposition("major", reverifiable=False), "reject"
        )

    def test_unverifiable_minor_goes_to_engineering(self):
        self.assertEqual(
            select_disposition("minor", reverifiable=False), "engineering-assessment"
        )

    def test_disposition_is_from_the_declared_set(self):
        self.assertIn(select_disposition("major"), DISPOSITIONS)

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            select_disposition("catastrophic")

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            select_disposition("minor", cleanable="yes")


class ReverificationTests(unittest.TestCase):
    def test_each_severity_owes_a_run(self):
        self.assertEqual(required_consecutive_reverifications("none"), 0)
        self.assertEqual(required_consecutive_reverifications("minor"), 1)
        self.assertEqual(required_consecutive_reverifications("major"), 2)
        self.assertEqual(required_consecutive_reverifications("critical"), 3)

    def test_trailing_run_stops_at_the_last_exceedance(self):
        result = grade_reverification([50.0, 150.0, 40.0, 30.0], 100.0, 2)
        self.assertEqual(result["trailing_conforming_run"], 2)
        self.assertTrue(result["satisfied"])

    def test_a_short_run_is_not_satisfied(self):
        result = grade_reverification([150.0, 40.0], 100.0, 2)
        self.assertEqual(result["trailing_conforming_run"], 1)
        self.assertFalse(result["satisfied"])

    def test_no_results_satisfies_a_zero_requirement(self):
        self.assertTrue(grade_reverification([], 100.0, 0)["satisfied"])

    def test_a_result_exactly_on_the_limit_keeps_the_run(self):
        result = grade_reverification([100.0, 90.0], 100.0, 2)
        self.assertEqual(result["trailing_conforming_run"], 2)

    def test_negative_reverification_result_rejected(self):
        with self.assertRaises(ValueError):
            grade_reverification([-1.0], 100.0, 1)

    def test_non_sequence_results_rejected(self):
        with self.assertRaises(ValueError):
            grade_reverification("40", 100.0, 1)


class ClosureTests(unittest.TestCase):
    def test_full_package_is_complete(self):
        result = closure_completeness(full_closure())
        self.assertTrue(result["complete"])
        self.assertAlmostEqual(result["fraction_complete"], 1.0, places=12)

    def test_missing_items_are_named(self):
        package = full_closure()
        del package["root_cause"]
        result = closure_completeness(package)
        self.assertEqual(result["missing"], ["root_cause"])
        self.assertFalse(result["complete"])

    def test_an_empty_string_does_not_count_as_present(self):
        package = full_closure()
        package["corrective_action"] = ""
        self.assertIn("corrective_action", closure_completeness(package)["missing"])

    def test_fraction_reflects_the_items_present(self):
        result = closure_completeness({"impact_assessment": "done"})
        self.assertAlmostEqual(
            result["fraction_complete"], 1.0 / len(CLOSURE_ITEMS), places=12
        )

    def test_non_mapping_package_rejected(self):
        with self.assertRaises(ValueError):
            closure_completeness(["impact_assessment"])


class AssessmentTests(unittest.TestCase):
    def test_complete_minor_exceedance_closes(self):
        result = assess_exceedance(spec())
        self.assertEqual(result["severity"]["severity"], "minor")
        self.assertEqual(result["disposition"], "clean-and-reverify")
        self.assertTrue(result["closed"])
        self.assertEqual(result["findings"], [])

    def test_conforming_result_closes_with_no_action(self):
        result = assess_exceedance(spec(measured=80.0))
        self.assertEqual(result["disposition"], "accept-as-is")
        self.assertTrue(result["closed"])

    def test_short_reverification_run_blocks_closure(self):
        result = assess_exceedance(spec(measured=500.0))
        self.assertEqual(result["severity"]["severity"], "major")
        self.assertFalse(result["closed"])
        self.assertTrue(any("consecutive conforming" in f for f in result["findings"]))

    def test_missing_closure_items_block_closure(self):
        package = full_closure()
        del package["approval"]
        result = assess_exceedance(spec(closure_package=package))
        self.assertFalse(result["closed"])
        self.assertTrue(any("closure package" in f for f in result["findings"]))

    def test_missing_exposure_data_is_a_finding(self):
        payload = spec()
        del payload["exposure"]
        result = assess_exceedance(payload)
        self.assertIsNone(result["deposited_per_m2"])
        self.assertTrue(any("no exposure data" in f for f in result["findings"]))

    def test_deposited_quantity_is_reported(self):
        result = assess_exceedance(spec())
        self.assertAlmostEqual(result["deposited_per_m2"] / 3.6e6, 1.0, places=9)

    def test_uncleanable_critical_case_is_rejected(self):
        result = assess_exceedance(spec(measured=5000.0, cleanable=False))
        self.assertEqual(result["disposition"], "reject")
        self.assertFalse(result["closed"])

    def test_sensitivity_drives_the_disposition(self):
        plain = assess_exceedance(spec())
        sharp = assess_exceedance(spec(sensitivity="critical"))
        self.assertEqual(plain["severity"]["severity"], "minor")
        self.assertEqual(sharp["severity"]["severity"], "major")

    def test_missing_key_rejected(self):
        payload = spec()
        del payload["limit"]
        with self.assertRaises(ValueError):
            assess_exceedance(payload)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_exceedance(["measured"])

    def test_malformed_exposure_rejected(self):
        with self.assertRaises(ValueError):
            assess_exceedance(spec(exposure={"exposure_hours": 1.0}))


if __name__ == "__main__":
    unittest.main()
