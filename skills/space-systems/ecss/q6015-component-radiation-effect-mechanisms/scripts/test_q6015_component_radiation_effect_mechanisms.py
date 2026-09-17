"""Contract tests for the clause 4.2 radiation effect mechanism logic."""

import unittest

from q6015_component_radiation_effect_mechanisms_logic import (
    DEFAULT_LET_SCREENING_FACTOR,
    LET_TOLERANCE,
    LOW_DOSE_RATE_SENSITIVE,
    MECHANISM_FAMILIES,
    MECHANISMS,
    TECHNOLOGIES,
    TECHNOLOGY_SUSCEPTIBILITY,
    assess_component,
    credible_mechanisms,
    demanded_methods,
    destructive_subset,
    driving_quantity,
    group_by_family,
    is_destructive,
    mechanism_family,
    normalize_token,
    required_method,
    single_event_reachable,
    validate_component,
    validate_environment,
    validate_mechanism,
    validate_technology,
)

ENVIRONMENT = {
    "total_ionising_dose": 30000.0,
    "displacement_damage_dose": 1.0e10,
    "max_linear_energy_transfer": 60.0,
}


def _component(**overrides):
    component = {
        "part_number": "RC-4120-M",
        "technology": "bulk-cmos-digital",
        "onset_threshold": 15.0,
        "declared_methods": [
            "cumulative-dose-step-test",
            "heavy-ion-single-event-test",
            "heavy-ion-destructive-event-test",
        ],
    }
    component.update(overrides)
    return component


class MechanismTableTests(unittest.TestCase):
    def test_every_mechanism_declares_a_known_family(self):
        for record in MECHANISMS.values():
            self.assertIn(record["family"], MECHANISM_FAMILIES)

    def test_every_mechanism_declares_a_driver_and_a_method(self):
        for name, record in MECHANISMS.items():
            self.assertTrue(record["driver"], name)
            self.assertTrue(record["method"], name)

    def test_cumulative_mechanisms_are_not_destructive_in_one_event(self):
        for name, record in MECHANISMS.items():
            if record["family"] == "cumulative":
                self.assertFalse(record["destructive"], name)

    def test_latchup_and_burnout_are_destructive(self):
        self.assertTrue(is_destructive("single-event-latchup"))
        self.assertTrue(is_destructive("single-event-burnout"))

    def test_upset_is_not_destructive(self):
        self.assertFalse(is_destructive("single-event-upset"))

    def test_mechanism_family_is_reported(self):
        self.assertEqual(mechanism_family("displacement-damage"), "cumulative")
        self.assertEqual(mechanism_family("single-event-upset"), "single-event")

    def test_driver_and_method_are_reported(self):
        self.assertEqual(
            driving_quantity("single-event-latchup"), "linear-energy-transfer"
        )
        self.assertEqual(
            required_method("displacement-damage"), "proton-displacement-test"
        )

    def test_unknown_mechanism_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_mechanism("thermal-runaway")

    def test_normalize_token_folds_case_and_underscores(self):
        self.assertEqual(
            normalize_token("Single_Event_Upset"), "single-event-upset"
        )


class TechnologyTests(unittest.TestCase):
    def test_every_technology_lists_recognized_mechanisms(self):
        for technology, mechanisms in TECHNOLOGY_SUSCEPTIBILITY.items():
            self.assertTrue(mechanisms, technology)
            for mechanism in mechanisms:
                self.assertIn(mechanism, MECHANISMS)

    def test_silicon_on_insulator_is_not_open_to_latchup(self):
        self.assertNotIn(
            "single-event-latchup", TECHNOLOGY_SUSCEPTIBILITY["soi-cmos-digital"]
        )

    def test_bulk_cmos_is_open_to_latchup(self):
        self.assertIn(
            "single-event-latchup", TECHNOLOGY_SUSCEPTIBILITY["bulk-cmos-digital"]
        )

    def test_power_mosfet_carries_the_destructive_gate_mechanisms(self):
        mechanisms = TECHNOLOGY_SUSCEPTIBILITY["power-mosfet"]
        self.assertIn("single-event-gate-rupture", mechanisms)
        self.assertIn("single-event-burnout", mechanisms)

    def test_solar_cell_assembly_carries_no_single_event_mechanism(self):
        for mechanism in TECHNOLOGY_SUSCEPTIBILITY["solar-cell-assembly"]:
            self.assertEqual(mechanism_family(mechanism), "cumulative")

    def test_unknown_technology_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_technology("vacuum-tube")

    def test_technologies_tuple_matches_the_table(self):
        self.assertEqual(set(TECHNOLOGIES), set(TECHNOLOGY_SUSCEPTIBILITY))

    def test_low_dose_rate_technologies_are_recognized(self):
        for technology in LOW_DOSE_RATE_SENSITIVE:
            self.assertIn(technology, TECHNOLOGY_SUSCEPTIBILITY)


class GroupingTests(unittest.TestCase):
    def test_mechanisms_are_grouped_into_both_families(self):
        grouped = group_by_family(list(TECHNOLOGY_SUSCEPTIBILITY["bipolar-linear"]))
        self.assertEqual(grouped["cumulative"],
                         ["total-ionising-dose", "displacement-damage"])
        self.assertEqual(grouped["single-event"], ["single-event-transient"])

    def test_grouping_preserves_order_and_removes_repeats(self):
        grouped = group_by_family(
            ["single-event-upset", "single-event-upset", "total-ionising-dose"]
        )
        self.assertEqual(grouped["single-event"], ["single-event-upset"])
        self.assertEqual(grouped["cumulative"], ["total-ionising-dose"])

    def test_destructive_subset_keeps_only_destructive_mechanisms(self):
        subset = destructive_subset(
            list(TECHNOLOGY_SUSCEPTIBILITY["bulk-cmos-digital"])
        )
        self.assertEqual(subset, ["single-event-latchup"])

    def test_grouping_requires_a_sequence(self):
        with self.assertRaises(ValueError):
            group_by_family("single-event-upset")

    def test_destructive_subset_requires_a_sequence(self):
        with self.assertRaises(ValueError):
            destructive_subset("single-event-latchup")


class EnvironmentAndScreeningTests(unittest.TestCase):
    def test_environment_is_keyed_by_driving_quantity(self):
        levels = validate_environment(dict(ENVIRONMENT))
        self.assertAlmostEqual(levels["total-ionising-dose"], 30000.0, places=9)
        self.assertAlmostEqual(levels["linear-energy-transfer"], 60.0, places=9)

    def test_missing_environment_key_is_rejected(self):
        bad = dict(ENVIRONMENT)
        del bad["max_linear_energy_transfer"]
        with self.assertRaises(ValueError):
            validate_environment(bad)

    def test_negative_environment_level_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_environment(dict(ENVIRONMENT, total_ionising_dose=-1.0))

    def test_zero_environment_level_is_allowed(self):
        levels = validate_environment(
            dict(ENVIRONMENT, displacement_damage_dose=0.0)
        )
        self.assertAlmostEqual(levels["displacement-damage-dose"], 0.0, places=9)

    def test_onset_below_the_environment_is_reachable(self):
        self.assertTrue(single_event_reachable(15.0, 60.0))

    def test_onset_above_the_environment_is_not_reachable(self):
        self.assertFalse(single_event_reachable(90.0, 60.0))

    def test_onset_exactly_at_the_environment_maximum_is_reachable(self):
        self.assertTrue(single_event_reachable(60.0, 60.0))

    def test_screening_factor_moves_the_screened_maximum(self):
        self.assertFalse(single_event_reachable(60.0, 60.0, 0.5))
        self.assertTrue(single_event_reachable(60.0, 60.0, 2.0))

    def test_default_screening_factor_is_unity(self):
        self.assertAlmostEqual(DEFAULT_LET_SCREENING_FACTOR, 1.0, places=9)

    def test_let_tolerance_is_small_and_positive(self):
        self.assertGreater(LET_TOLERANCE, 0.0)
        self.assertLess(LET_TOLERANCE, 1e-6)

    def test_zero_onset_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            single_event_reachable(0.0, 60.0)


class CredibilityTests(unittest.TestCase):
    def test_full_environment_keeps_the_whole_technology_set(self):
        result = credible_mechanisms("bulk-cmos-digital", ENVIRONMENT, 15.0)
        self.assertEqual(
            result["credible"],
            list(TECHNOLOGY_SUSCEPTIBILITY["bulk-cmos-digital"]),
        )
        self.assertEqual(result["screened_out"], [])

    def test_hard_part_screens_out_every_single_event_mechanism(self):
        result = credible_mechanisms("bulk-cmos-digital", ENVIRONMENT, 120.0)
        self.assertEqual(result["credible"], ["total-ionising-dose"])
        self.assertEqual(len(result["screened_out"]), 4)

    def test_absent_displacement_environment_screens_that_mechanism_out(self):
        environment = dict(ENVIRONMENT, displacement_damage_dose=0.0)
        result = credible_mechanisms("optocoupler", environment, 15.0)
        self.assertNotIn("displacement-damage", result["credible"])
        self.assertIn("displacement-damage", result["screened_out"])

    def test_no_heavy_ion_environment_screens_out_all_single_events(self):
        environment = dict(ENVIRONMENT, max_linear_energy_transfer=0.0)
        result = credible_mechanisms("power-mosfet", environment, 15.0)
        self.assertEqual(result["credible"], ["total-ionising-dose"])

    def test_missing_onset_keeps_single_event_mechanisms_credible(self):
        result = credible_mechanisms("power-mosfet", ENVIRONMENT, None)
        self.assertIn("single-event-burnout", result["credible"])

    def test_demanded_methods_are_deduplicated(self):
        methods = demanded_methods(
            ["single-event-upset", "single-event-transient"]
        )
        self.assertEqual(methods, ["heavy-ion-single-event-test"])

    def test_low_dose_rate_technology_demands_an_extra_method(self):
        methods = demanded_methods(["total-ionising-dose"], "bipolar-linear")
        self.assertIn("low-dose-rate-cumulative-test", methods)

    def test_other_technologies_do_not_demand_the_extra_method(self):
        methods = demanded_methods(["total-ionising-dose"], "bulk-cmos-digital")
        self.assertNotIn("low-dose-rate-cumulative-test", methods)


class ComponentTests(unittest.TestCase):
    def test_fully_covered_component_is_acceptable(self):
        result = assess_component(_component(), ENVIRONMENT)
        self.assertTrue(result["acceptable"])
        self.assertTrue(result["coverage_complete"])
        self.assertEqual(result["destructive_mechanisms"], ["single-event-latchup"])

    def test_absent_destructive_method_is_called_out_as_such(self):
        component = _component(
            declared_methods=[
                "cumulative-dose-step-test",
                "heavy-ion-single-event-test",
            ]
        )
        result = assess_component(component, ENVIRONMENT)
        self.assertFalse(result["acceptable"])
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("destructive", result["findings"][0])

    def test_absent_non_destructive_method_is_a_plain_finding(self):
        component = _component(
            technology="soi-cmos-digital",
            declared_methods=["cumulative-dose-step-test"],
        )
        result = assess_component(component, ENVIRONMENT)
        self.assertEqual(len(result["findings"]), 1)
        self.assertNotIn("destructive", result["findings"][0])

    def test_empty_plan_names_every_demanded_method(self):
        result = assess_component(_component(declared_methods=[]), ENVIRONMENT)
        self.assertEqual(len(result["absent_methods"]), 3)
        self.assertEqual(len(result["findings"]), 3)

    def test_duplicate_declared_method_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_component(
                _component(
                    declared_methods=[
                        "cumulative-dose-step-test",
                        "cumulative-dose-step-test",
                    ]
                )
            )

    def test_component_missing_a_required_key_is_rejected(self):
        bad = _component()
        del bad["technology"]
        with self.assertRaises(ValueError):
            validate_component(bad)

    def test_non_mapping_component_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_component("RC-4120-M")

    def test_blank_part_number_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_component(_component(part_number="   "))

    def test_benign_environment_screening_everything_out_is_a_finding(self):
        environment = {
            "total_ionising_dose": 0.0,
            "displacement_damage_dose": 0.0,
            "max_linear_energy_transfer": 0.0,
        }
        result = assess_component(
            _component(declared_methods=[]), environment
        )
        self.assertEqual(result["credible_mechanisms"], [])
        self.assertFalse(result["acceptable"])

    def test_grouped_and_flat_mechanism_sets_agree(self):
        result = assess_component(_component(), ENVIRONMENT)
        flat = (result["grouped_mechanisms"]["cumulative"]
                + result["grouped_mechanisms"]["single-event"])
        self.assertEqual(sorted(flat), sorted(result["credible_mechanisms"]))


if __name__ == "__main__":
    unittest.main()
