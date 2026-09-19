#!/usr/bin/env python3
"""Contract test for the mechanism mission-environment definition (offline)."""

import copy
import unittest

from e3301_mission_environments_definition_logic import (
    DEFAULT_ENVIRONMENT_POLICY,
    ENVIRONMENT_CATEGORIES,
    assess_environment_definition,
    decibel_to_amplitude_factor,
    envelope_environments,
    qualification_levels,
    undeclared_categories,
    validate_environment_policy,
    validate_phase,
)


def phase(
    name,
    duration_h=100.0,
    min_temperature_c=-20.0,
    max_temperature_c=50.0,
    random_vibration_grms=5.0,
    shock_srs_peak_g=200.0,
    radiation_dose_krad=1.0,
    actuation_cycles=10,
):
    return {
        "name": name,
        "duration_h": duration_h,
        "min_temperature_c": min_temperature_c,
        "max_temperature_c": max_temperature_c,
        "random_vibration_grms": random_vibration_grms,
        "shock_srs_peak_g": shock_srs_peak_g,
        "radiation_dose_krad": radiation_dose_krad,
        "actuation_cycles": actuation_cycles,
    }


PHASES = [
    phase("ground-storage", duration_h=4000.0, min_temperature_c=5.0,
          max_temperature_c=35.0, random_vibration_grms=0.5,
          shock_srs_peak_g=10.0, radiation_dose_krad=0.0, actuation_cycles=20),
    phase("launch", duration_h=0.2, min_temperature_c=-10.0,
          max_temperature_c=60.0, random_vibration_grms=12.0,
          shock_srs_peak_g=2000.0, radiation_dose_krad=0.0, actuation_cycles=0),
    phase("on-orbit", duration_h=87600.0, min_temperature_c=-70.0,
          max_temperature_c=95.0, random_vibration_grms=0.1,
          shock_srs_peak_g=150.0, radiation_dose_krad=30.0,
          actuation_cycles=4980),
]

CAPABILITY = {
    "min_temperature_c": -95.0,
    "max_temperature_c": 110.0,
    "random_vibration_grms": 20.0,
    "shock_srs_peak_g": 3000.0,
    "radiation_dose_krad": 100.0,
    "actuation_cycles": 25000.0,
}

GOOD_CASE = {"phases": PHASES, "declared_capability": CAPABILITY}


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_environment_policy(DEFAULT_ENVIRONMENT_POLICY),
            DEFAULT_ENVIRONMENT_POLICY,
        )

    def test_all_five_categories_are_named(self):
        self.assertEqual(len(ENVIRONMENT_CATEGORIES), 5)
        self.assertIn("life-cycles", ENVIRONMENT_CATEGORIES)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_environment_policy("default")

    def test_factor_below_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_ENVIRONMENT_POLICY)
        broken["life_test_factor"] = 0.5
        with self.assertRaises(ValueError):
            validate_environment_policy(broken)

    def test_negative_thermal_margin_rejected(self):
        broken = copy.deepcopy(DEFAULT_ENVIRONMENT_POLICY)
        broken["thermal_qualification_margin_k"] = -5.0
        with self.assertRaises(ValueError):
            validate_environment_policy(broken)

    def test_unknown_required_category_rejected(self):
        broken = copy.deepcopy(DEFAULT_ENVIRONMENT_POLICY)
        broken["required_categories"] = ["acoustic"]
        with self.assertRaises(ValueError):
            validate_environment_policy(broken)


class CoverageTests(unittest.TestCase):
    def test_a_complete_phase_has_no_gaps(self):
        self.assertEqual(undeclared_categories(phase("orbit")), [])

    def test_a_missing_radiation_entry_is_a_gap_not_a_zero(self):
        incomplete = phase("orbit")
        del incomplete["radiation_dose_krad"]
        self.assertEqual(undeclared_categories(incomplete), ["radiation"])

    def test_a_missing_thermal_bound_reports_the_thermal_category_once(self):
        incomplete = phase("orbit")
        del incomplete["min_temperature_c"]
        del incomplete["max_temperature_c"]
        self.assertEqual(undeclared_categories(incomplete), ["thermal"])

    def test_several_gaps_are_all_reported(self):
        incomplete = phase("orbit")
        del incomplete["shock_srs_peak_g"]
        del incomplete["actuation_cycles"]
        self.assertEqual(
            set(undeclared_categories(incomplete)), {"shock", "life-cycles"}
        )

    def test_non_mapping_phase_rejected(self):
        with self.assertRaises(ValueError):
            undeclared_categories("launch")


class PhaseValidationTests(unittest.TestCase):
    def test_a_complete_phase_normalises(self):
        record = validate_phase(phase("launch"))
        self.assertEqual(record["name"], "launch")
        self.assertEqual(record["actuation_cycles"], 10)

    def test_a_phase_with_a_gap_is_refused(self):
        incomplete = phase("launch")
        del incomplete["radiation_dose_krad"]
        with self.assertRaises(ValueError):
            validate_phase(incomplete)

    def test_blank_phase_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase(phase("  "))

    def test_inverted_temperature_bounds_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase(phase("launch", min_temperature_c=50.0,
                                 max_temperature_c=-20.0))

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase(phase("launch", duration_h=-1.0))

    def test_negative_vibration_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase(phase("launch", random_vibration_grms=-1.0))

    def test_non_integer_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase(phase("launch", actuation_cycles=10.5))


class EnvelopeTests(unittest.TestCase):
    def test_envelope_takes_the_coldest_cold(self):
        self.assertAlmostEqual(
            envelope_environments(PHASES)["min_temperature_c"], -70.0, places=9
        )

    def test_envelope_takes_the_hottest_hot(self):
        self.assertAlmostEqual(
            envelope_environments(PHASES)["max_temperature_c"], 95.0, places=9
        )

    def test_envelope_takes_the_worst_vibration_level(self):
        self.assertAlmostEqual(
            envelope_environments(PHASES)["max_random_vibration_grms"], 12.0, places=9
        )

    def test_dose_and_cycles_accumulate_rather_than_envelope(self):
        envelope = envelope_environments(PHASES)
        self.assertAlmostEqual(envelope["total_radiation_dose_krad"], 30.0, places=9)
        self.assertEqual(envelope["total_actuation_cycles"], 5000)

    def test_envelope_names_the_driving_phase_for_each_extreme(self):
        driving = envelope_environments(PHASES)["driving_phases"]
        self.assertEqual(driving["cold"], "on-orbit")
        self.assertEqual(driving["vibration"], "launch")
        self.assertEqual(driving["shock"], "launch")

    def test_envelope_refuses_a_phase_with_a_gap(self):
        incomplete = phase("late-addition")
        del incomplete["radiation_dose_krad"]
        with self.assertRaises(ValueError):
            envelope_environments(PHASES + [incomplete])

    def test_duplicate_phase_name_rejected(self):
        with self.assertRaises(ValueError):
            envelope_environments([phase("launch"), phase("launch")])

    def test_empty_phase_list_rejected(self):
        with self.assertRaises(ValueError):
            envelope_environments([])


class QualificationLevelTests(unittest.TestCase):
    def test_three_decibel_is_about_a_factor_of_one_point_four(self):
        self.assertAlmostEqual(decibel_to_amplitude_factor(3.0), 1.41253754, places=7)

    def test_zero_decibel_leaves_the_level_alone(self):
        self.assertAlmostEqual(decibel_to_amplitude_factor(0.0), 1.0, places=12)

    def test_thermal_margin_widens_both_ends(self):
        levels = qualification_levels(envelope_environments(PHASES))
        self.assertAlmostEqual(levels["qualification_min_temperature_c"], -80.0,
                               places=9)
        self.assertAlmostEqual(levels["qualification_max_temperature_c"], 105.0,
                               places=9)

    def test_vibration_level_is_raised_by_the_decibel_margin(self):
        levels = qualification_levels(envelope_environments(PHASES))
        self.assertAlmostEqual(
            levels["qualification_random_vibration_grms"], 16.9504505, places=6
        )

    def test_dose_carries_the_radiation_design_margin(self):
        levels = qualification_levels(envelope_environments(PHASES))
        self.assertAlmostEqual(levels["design_radiation_dose_krad"], 60.0, places=9)

    def test_life_cycles_carry_the_life_factor(self):
        levels = qualification_levels(envelope_environments(PHASES))
        self.assertEqual(levels["life_test_cycles"], 20000)

    def test_shock_carries_the_shock_factor(self):
        levels = qualification_levels(envelope_environments(PHASES))
        self.assertAlmostEqual(levels["qualification_shock_srs_peak_g"], 2800.0,
                               places=9)

    def test_incomplete_envelope_rejected(self):
        envelope = envelope_environments(PHASES)
        del envelope["max_shock_srs_peak_g"]
        with self.assertRaises(ValueError):
            qualification_levels(envelope)

    def test_non_mapping_envelope_rejected(self):
        with self.assertRaises(ValueError):
            qualification_levels("worst case")


class AssessmentTests(unittest.TestCase):
    def test_good_case_is_covered(self):
        result = assess_environment_definition(GOOD_CASE)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["verdict"], "environments-covered")
        self.assertEqual(result["shortfalls"], [])

    def test_a_gap_stops_the_assessment_before_the_envelope(self):
        incomplete = phase("late-addition")
        del incomplete["radiation_dose_krad"]
        result = assess_environment_definition(
            {"phases": PHASES + [incomplete], "declared_capability": CAPABILITY}
        )
        self.assertFalse(result["definition_complete"])
        self.assertEqual(result["verdict"], "environment-definition-incomplete")
        self.assertIn("late-addition", result["undeclared"])

    def test_a_capability_below_a_qualification_level_is_a_shortfall(self):
        capability = dict(CAPABILITY, random_vibration_grms=10.0)
        result = assess_environment_definition(
            {"phases": PHASES, "declared_capability": capability}
        )
        self.assertFalse(result["compliant"])
        self.assertIn("random_vibration_grms", result["shortfalls"])

    def test_a_capability_exactly_on_the_level_is_accepted(self):
        levels = qualification_levels(envelope_environments(PHASES))
        capability = dict(
            CAPABILITY,
            random_vibration_grms=levels["qualification_random_vibration_grms"],
            shock_srs_peak_g=levels["qualification_shock_srs_peak_g"],
        )
        result = assess_environment_definition(
            {"phases": PHASES, "declared_capability": capability}
        )
        self.assertTrue(result["compliant"])

    def test_a_warm_cold_capability_is_a_shortfall(self):
        capability = dict(CAPABILITY, min_temperature_c=-40.0)
        result = assess_environment_definition(
            {"phases": PHASES, "declared_capability": capability}
        )
        self.assertIn("min_temperature_c", result["shortfalls"])

    def test_an_unstated_capability_field_is_a_shortfall(self):
        capability = dict(CAPABILITY)
        del capability["actuation_cycles"]
        result = assess_environment_definition(
            {"phases": PHASES, "declared_capability": capability}
        )
        self.assertIn("actuation_cycles", result["shortfalls"])
        self.assertTrue(any("does not state" in f for f in result["findings"]))

    def test_without_a_capability_the_envelope_still_closes(self):
        result = assess_environment_definition({"phases": PHASES})
        self.assertTrue(result["definition_complete"])
        self.assertIsNone(result["compliant"])
        self.assertEqual(result["verdict"], "capability-not-evaluated")

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_environment_definition("phases")

    def test_empty_phase_list_in_a_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_environment_definition({"phases": []})

    def test_non_mapping_capability_rejected(self):
        with self.assertRaises(ValueError):
            assess_environment_definition(
                {"phases": PHASES, "declared_capability": "plenty"}
            )


if __name__ == "__main__":
    unittest.main()
