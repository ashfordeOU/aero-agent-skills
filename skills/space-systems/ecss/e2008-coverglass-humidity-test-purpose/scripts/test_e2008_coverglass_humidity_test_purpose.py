"""Contract tests for the clause 8.7.11.1.1 coated-coverglass damp storage purpose."""

import unittest

from e2008_coverglass_humidity_test_purpose_logic import (
    COATING_STABILITY_EVIDENCED,
    COMMON_OBJECTIVE,
    DEFAULT_DAMP_STORAGE_POLICY,
    EXPOSURE_INADEQUATE,
    EXPOSURE_NOT_PLANNED,
    EXPOSURE_NOT_REQUIRED,
    RECOGNISED_MECHANISMS,
    acceleration_factor,
    assess_humidity_test_purpose,
    condensation_margin_c,
    dew_point_c,
    equivalent_field_hours,
    humidity_acceleration,
    mechanism_inventory,
    storage_objectives,
    surface_stays_dry,
    thermal_acceleration,
    validate_chamber_plan,
    validate_damp_storage_policy,
)

# Hand-worked oracles for the canonical 85 C / 85 percent chamber against a
# 25 C / 60 percent store, kept here rather than re-derived from the module:
# the humidity term is (85/60) raised to 2.7 and the Arrhenius term uses
# 0.79 eV over the 25 C to 85 C interval. Their product is the factor.
HUMIDITY_TERM = 2.561
THERMAL_TERM = 172.63
CHAMBER_DEW_POINT_C = 80.97


def _policy(**overrides):
    policy = dict(DEFAULT_DAMP_STORAGE_POLICY)
    policy.update(overrides)
    return policy


def _plan(**overrides):
    plan = {
        "chamber_temperature_c": 85.0,
        "chamber_relative_humidity_percent": 85.0,
        "sample_surface_temperature_c": 85.0,
        "duration_hours": 1000.0,
    }
    plan.update(overrides)
    return plan


def _case(**overrides):
    case = {
        "coating_present": True,
        "degradation_mechanisms": [
            "antireflection-coating-hydrolysis",
            "coating-to-glass-adhesion-loss",
        ],
        "damp_storage": _plan(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_damp_storage_policy(DEFAULT_DAMP_STORAGE_POLICY),
            DEFAULT_DAMP_STORAGE_POLICY,
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_storage_policy("85/85")

    def test_a_field_humidity_above_one_hundred_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_storage_policy(
                _policy(field_relative_humidity_percent=140.0)
            )

    def test_a_zero_field_humidity_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_storage_policy(
                _policy(field_relative_humidity_percent=0.0)
            )

    def test_a_negative_humidity_exponent_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_storage_policy(_policy(humidity_exponent=-1.0))

    def test_a_zero_activation_energy_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_storage_policy(_policy(activation_energy_ev=0.0))

    def test_a_field_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_storage_policy(_policy(field_temperature_c=-300.0))


class MechanismTests(unittest.TestCase):
    def test_the_recognised_mechanisms_are_listed(self):
        self.assertIn("conductive-coating-corrosion", RECOGNISED_MECHANISMS)

    def test_a_declared_mechanism_is_grouped(self):
        self.assertEqual(
            mechanism_inventory(["conductive-coating-corrosion"]),
            ("conductive-coating-corrosion",),
        )

    def test_a_repeated_mechanism_is_counted_once(self):
        grouped = mechanism_inventory(
            ["coating-pinhole-growth", "coating-pinhole-growth"]
        )
        self.assertEqual(len(grouped), 1)

    def test_an_unknown_mechanism_rejected(self):
        with self.assertRaises(ValueError):
            mechanism_inventory(["coverglass-radiation-darkening"])

    def test_a_non_collection_mechanism_list_rejected(self):
        with self.assertRaises(ValueError):
            mechanism_inventory("coating-pinhole-growth")

    def test_each_mechanism_maps_to_what_the_storage_reveals(self):
        objectives = storage_objectives(["conductive-coating-corrosion"])
        self.assertIn("coating-sheet-resistance-drift", objectives)

    def test_the_shared_objective_is_appended_when_any_mechanism_is_present(self):
        self.assertIn(COMMON_OBJECTIVE, storage_objectives(["coating-pinhole-growth"]))

    def test_no_mechanism_yields_no_objective(self):
        self.assertEqual(storage_objectives([]), ())


class AccelerationTests(unittest.TestCase):
    def test_the_humidity_term_matches_the_hand_worked_oracle(self):
        self.assertAlmostEqual(
            humidity_acceleration(85.0, 60.0, 2.7), HUMIDITY_TERM, places=3
        )

    def test_equal_humidities_do_not_accelerate(self):
        self.assertAlmostEqual(
            humidity_acceleration(60.0, 60.0, 2.7), 1.0, places=12
        )

    def test_a_zero_exponent_removes_the_humidity_term(self):
        self.assertAlmostEqual(
            humidity_acceleration(85.0, 60.0, 0.0), 1.0, places=12
        )

    def test_the_thermal_term_matches_the_hand_worked_oracle(self):
        self.assertAlmostEqual(
            thermal_acceleration(85.0, 25.0, 0.79), THERMAL_TERM, places=1
        )

    def test_equal_temperatures_do_not_accelerate(self):
        self.assertAlmostEqual(
            thermal_acceleration(25.0, 25.0, 0.79), 1.0, places=12
        )

    def test_a_colder_chamber_decelerates(self):
        self.assertLess(thermal_acceleration(5.0, 25.0, 0.79), 0.5)

    def test_the_factor_is_the_product_of_the_two_hand_worked_terms(self):
        self.assertAlmostEqual(
            acceleration_factor(85.0, 85.0, 25.0, 60.0, 0.79, 2.7),
            HUMIDITY_TERM * THERMAL_TERM,
            places=0,
        )

    def test_a_chamber_at_the_field_condition_has_no_acceleration(self):
        self.assertAlmostEqual(
            acceleration_factor(25.0, 60.0, 25.0, 60.0, 0.79, 2.7), 1.0, places=12
        )

    def test_the_equivalent_interval_scales_with_the_chamber_hours(self):
        self.assertAlmostEqual(
            equivalent_field_hours(442.0, 1000.0), 442000.0, places=6
        )

    def test_a_zero_duration_has_no_equivalent_interval(self):
        with self.assertRaises(ValueError):
            equivalent_field_hours(442.0, 0.0)

    def test_a_negative_acceleration_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_field_hours(-3.0, 1000.0)


class CondensationTests(unittest.TestCase):
    def test_saturated_air_dews_at_its_own_temperature(self):
        self.assertAlmostEqual(dew_point_c(85.0, 100.0), 85.0, places=9)

    def test_the_chamber_dew_point_matches_the_hand_worked_oracle(self):
        self.assertAlmostEqual(dew_point_c(85.0, 85.0), CHAMBER_DEW_POINT_C, places=2)

    def test_drier_air_dews_lower(self):
        self.assertGreater(dew_point_c(85.0, 85.0) - dew_point_c(85.0, 40.0), 10.0)

    def test_a_humidity_above_one_hundred_rejected(self):
        with self.assertRaises(ValueError):
            dew_point_c(85.0, 120.0)

    def test_a_zero_humidity_rejected(self):
        with self.assertRaises(ValueError):
            dew_point_c(85.0, 0.0)

    def test_the_margin_is_the_surface_above_the_dew_point(self):
        self.assertAlmostEqual(
            condensation_margin_c(85.0, 85.0, 85.0),
            85.0 - dew_point_c(85.0, 85.0),
            places=12,
        )

    def test_a_warm_surface_stays_dry(self):
        self.assertTrue(surface_stays_dry(85.0, 85.0, 85.0, 2.0))

    def test_a_cold_surface_condenses(self):
        self.assertFalse(surface_stays_dry(85.0, 85.0, 78.0, 2.0))

    def test_a_surface_exactly_on_the_required_margin_stays_dry(self):
        surface = dew_point_c(85.0, 85.0) + 2.0
        self.assertTrue(surface_stays_dry(85.0, 85.0, surface, 2.0))

    def test_a_negative_required_margin_rejected(self):
        with self.assertRaises(ValueError):
            surface_stays_dry(85.0, 85.0, 85.0, -1.0)


class ChamberPlanTests(unittest.TestCase):
    def test_a_well_formed_plan_validates(self):
        plan = _plan()
        self.assertIs(validate_chamber_plan(plan), plan)

    def test_a_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            validate_chamber_plan("85/85 for 1000 h")

    def test_a_zero_duration_plan_rejected(self):
        with self.assertRaises(ValueError):
            validate_chamber_plan(_plan(duration_hours=0.0))

    def test_a_plan_without_a_surface_temperature_rejected(self):
        plan = _plan()
        del plan["sample_surface_temperature_c"]
        with self.assertRaises(ValueError):
            validate_chamber_plan(plan)


class PurposeTests(unittest.TestCase):
    def test_a_well_planned_exposure_evidences_stability(self):
        result = assess_humidity_test_purpose(_case())
        self.assertEqual(result["verdict"], COATING_STABILITY_EVIDENCED)
        self.assertEqual(result["findings"], [])

    def test_the_acceleration_and_equivalent_interval_are_reported(self):
        result = assess_humidity_test_purpose(_case())
        self.assertAlmostEqual(
            result["acceleration_factor"], HUMIDITY_TERM * THERMAL_TERM, places=0
        )
        self.assertAlmostEqual(
            result["equivalent_field_hours"],
            result["acceleration_factor"] * 1000.0,
            places=6,
        )

    def test_an_uncoated_coverglass_does_not_earn_the_exposure(self):
        result = assess_humidity_test_purpose(
            _case(coating_present=False, degradation_mechanisms=[])
        )
        self.assertEqual(result["verdict"], EXPOSURE_NOT_REQUIRED)
        self.assertTrue(result["advisories"])

    def test_a_coated_part_with_no_declared_mechanism_does_not_earn_it_either(self):
        result = assess_humidity_test_purpose(_case(degradation_mechanisms=[]))
        self.assertEqual(result["verdict"], EXPOSURE_NOT_REQUIRED)

    def test_a_declared_mechanism_with_no_exposure_planned_is_a_finding(self):
        result = assess_humidity_test_purpose(_case(damp_storage=None))
        self.assertEqual(result["verdict"], EXPOSURE_NOT_PLANNED)
        self.assertEqual(len(result["findings"]), 1)

    def test_a_condensing_chamber_is_inadequate(self):
        result = assess_humidity_test_purpose(
            _case(damp_storage=_plan(sample_surface_temperature_c=78.0))
        )
        self.assertEqual(result["verdict"], EXPOSURE_INADEQUATE)
        self.assertTrue(any("condenses" in note for note in result["findings"]))

    def test_a_chamber_run_too_briefly_is_inadequate(self):
        result = assess_humidity_test_purpose(
            _case(damp_storage=_plan(duration_hours=12.0))
        )
        self.assertEqual(result["verdict"], EXPOSURE_INADEQUATE)

    def test_a_duration_exactly_on_the_floor_is_not_short(self):
        result = assess_humidity_test_purpose(
            _case(damp_storage=_plan(duration_hours=96.0))
        )
        self.assertEqual(result["verdict"], COATING_STABILITY_EVIDENCED)

    def test_a_gentle_chamber_cannot_reach_the_required_field_interval(self):
        result = assess_humidity_test_purpose(
            _case(
                damp_storage=_plan(
                    chamber_temperature_c=30.0,
                    chamber_relative_humidity_percent=65.0,
                    sample_surface_temperature_c=30.0,
                    duration_hours=200.0,
                )
            )
        )
        self.assertEqual(result["verdict"], EXPOSURE_INADEQUATE)
        self.assertTrue(
            any("stands in for" in note for note in result["findings"])
        )

    def test_every_inadequacy_is_reported_not_only_the_first(self):
        result = assess_humidity_test_purpose(
            _case(
                damp_storage=_plan(
                    chamber_temperature_c=30.0,
                    chamber_relative_humidity_percent=65.0,
                    sample_surface_temperature_c=20.0,
                    duration_hours=12.0,
                )
            )
        )
        self.assertEqual(result["verdict"], EXPOSURE_INADEQUATE)
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_a_very_large_acceleration_raises_an_advisory(self):
        result = assess_humidity_test_purpose(_case())
        self.assertTrue(result["advisories"])

    def test_the_objectives_travel_with_the_verdict(self):
        result = assess_humidity_test_purpose(_case())
        self.assertIn(COMMON_OBJECTIVE, result["storage_objectives"])
        self.assertIn("coating-delamination-onset", result["storage_objectives"])

    def test_the_dew_point_travels_with_the_verdict(self):
        result = assess_humidity_test_purpose(_case())
        self.assertAlmostEqual(
            result["dew_point_c"], CHAMBER_DEW_POINT_C, places=2
        )

    def test_an_unstated_coating_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_humidity_test_purpose(_case(coating_present=None))

    def test_a_missing_mechanism_inventory_rejected(self):
        case = _case()
        del case["degradation_mechanisms"]
        with self.assertRaises(ValueError):
            assess_humidity_test_purpose(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_humidity_test_purpose(["damp_storage"])

    def test_an_unknown_mechanism_in_the_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_humidity_test_purpose(
                _case(degradation_mechanisms=["coverglass-thermal-shock"])
            )


if __name__ == "__main__":
    unittest.main()
