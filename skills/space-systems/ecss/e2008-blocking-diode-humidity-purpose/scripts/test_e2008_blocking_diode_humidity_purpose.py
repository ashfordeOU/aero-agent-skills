"""Contract tests for the clause 12.6.4.1.1 blocking diode damp storage logic."""

import copy
import unittest

from e2008_blocking_diode_humidity_purpose_logic import (
    DAMP_STORAGE_CONDITIONS_UNSOUND,
    DAMP_STORAGE_MONITORING_BLIND,
    DAMP_STORAGE_MONITORING_UNDER_BIASED,
    DAMP_STORAGE_NOT_PLANNED,
    DAMP_STORAGE_NOT_REQUIRED,
    DAMP_STORAGE_PURPOSE_SERVED,
    DAMP_STORAGE_SHELF_LIFE_SHORTFALL,
    DEFAULT_DAMP_STORAGE_POLICY,
    DUTY_REVERSE_BLOCKING,
    FAMILY_COATING,
    FAMILY_CONTACT,
    FAMILY_FUNCTION,
    MECHANISM_FAMILIES,
    MOISTURE_MECHANISMS,
    SHARED_OBJECTIVE,
    acceleration_factor,
    assess_blocking_diode_damp_storage_purpose,
    bias_coverage_fraction,
    bias_read_mechanisms,
    equivalent_storage_months,
    exposure_objectives,
    group_mechanisms,
    humidity_acceleration,
    mechanism_parameters,
    mechanism_record,
    monitoring_gaps,
    thermal_acceleration,
    threatened_duties,
    validate_damp_storage_policy,
)

# Independently stated reference values for the nominal chamber:
# 45 C and 85 percent relative humidity over a 22 C, 50 percent store.
_HUMIDITY_TERM = 4.101986
_THERMAL_TERM = 9.444857
_FACTOR = 38.742667
_MONTHS = 53.072146

_ALL_MECHANISMS = sorted(MOISTURE_MECHANISMS)
_ALL_PARAMETERS = [
    "attachment_pull_strength_n",
    "coating_visual_state",
    "forward_voltage_v",
    "reverse_leakage_a",
    "series_resistance_ohm",
]


def _policy(**overrides):
    policy = copy.deepcopy(DEFAULT_DAMP_STORAGE_POLICY)
    policy.update(overrides)
    return policy


def _exposure(**overrides):
    exposure = {
        "planned": True,
        "soak_hours": 1000.0,
        "chamber_temperature_c": 45.0,
        "chamber_humidity_percent": 85.0,
    }
    exposure.update(overrides)
    return exposure


def _storage(**overrides):
    storage = {"temperature_c": 22.0, "humidity_percent": 50.0}
    storage.update(overrides)
    return storage


def _monitoring(**overrides):
    monitoring = {"parameters": list(_ALL_PARAMETERS), "bias_v": 45.0}
    monitoring.update(overrides)
    return monitoring


def _case(**overrides):
    case = {
        "mechanisms": list(_ALL_MECHANISMS),
        "exposure": _exposure(),
        "storage": _storage(),
        "monitoring": _monitoring(),
        "duty": {"reverse_bias_v": 50.0},
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_damp_storage_policy(DEFAULT_DAMP_STORAGE_POLICY),
            DEFAULT_DAMP_STORAGE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_storage_policy("damp")

    def test_a_fitted_ceiling_at_the_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_storage_policy(
                _policy(min_acceleration_factor=2.0, max_fitted_acceleration_factor=2.0)
            )

    def test_a_fitted_ceiling_below_the_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_storage_policy(
                _policy(min_acceleration_factor=8.0, max_fitted_acceleration_factor=4.0)
            )

    def test_a_zero_storage_requirement_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_storage_policy(_policy(required_storage_months=0.0))

    def test_a_saturated_humidity_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_storage_policy(_policy(max_chamber_humidity_percent=100.0))

    def test_a_bias_floor_above_the_duty_bias_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_storage_policy(_policy(min_monitoring_bias_fraction=1.4))

    def test_a_zero_activation_energy_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_storage_policy(_policy(activation_energy_ev=0.0))


class MechanismCatalogueTests(unittest.TestCase):
    def test_every_mechanism_sits_in_a_known_family(self):
        for name in _ALL_MECHANISMS:
            self.assertIn(mechanism_record(name)["family"], MECHANISM_FAMILIES)

    def test_every_mechanism_carries_a_parameter_and_a_duty(self):
        for name in _ALL_MECHANISMS:
            record = mechanism_record(name)
            self.assertTrue(record["parameter"])
            self.assertTrue(record["threatened_duty"])

    def test_an_unknown_mechanism_rejected(self):
        with self.assertRaises(ValueError):
            mechanism_record("tin-whisker-growth")

    def test_a_record_is_a_copy_the_caller_cannot_corrupt(self):
        record = mechanism_record("protective-coating-crazing")
        record["family"] = FAMILY_FUNCTION
        self.assertEqual(
            mechanism_record("protective-coating-crazing")["family"], FAMILY_COATING
        )

    def test_grouping_puts_each_mechanism_in_its_family(self):
        grouped = group_mechanisms(_ALL_MECHANISMS)
        self.assertEqual(len(grouped[FAMILY_FUNCTION]), 2)
        self.assertEqual(len(grouped[FAMILY_CONTACT]), 2)
        self.assertEqual(len(grouped[FAMILY_COATING]), 2)

    def test_grouping_refuses_an_unrecognised_mechanism(self):
        with self.assertRaises(ValueError):
            group_mechanisms(["junction-passivation-ingress", "tin-whisker-growth"])

    def test_a_repeated_mechanism_is_listed_once(self):
        grouped = group_mechanisms(
            ["protective-coating-crazing", "protective-coating-crazing"]
        )
        self.assertEqual(grouped[FAMILY_COATING], ["protective-coating-crazing"])

    def test_a_non_sequence_mechanism_list_rejected(self):
        with self.assertRaises(ValueError):
            group_mechanisms("junction-passivation-ingress")

    def test_the_parameter_set_is_deduplicated_and_sorted(self):
        self.assertEqual(mechanism_parameters(_ALL_MECHANISMS), _ALL_PARAMETERS)

    def test_the_passivation_mechanism_threatens_the_blocking_duty(self):
        self.assertEqual(
            threatened_duties(["junction-passivation-ingress"]),
            [DUTY_REVERSE_BLOCKING],
        )

    def test_one_objective_per_family_plus_the_shared_one(self):
        objectives = exposure_objectives(_ALL_MECHANISMS)
        self.assertEqual(len(objectives), 4)
        self.assertEqual(objectives[-1], SHARED_OBJECTIVE)

    def test_a_single_family_gives_two_objectives(self):
        objectives = exposure_objectives(["contact-metallisation-corrosion"])
        self.assertEqual(len(objectives), 2)

    def test_no_mechanism_gives_no_objective(self):
        self.assertEqual(exposure_objectives([]), [])

    def test_only_the_passivation_mechanism_needs_the_duty_bias(self):
        self.assertEqual(
            bias_read_mechanisms(_ALL_MECHANISMS), ["junction-passivation-ingress"]
        )

    def test_a_contact_only_plan_needs_no_duty_bias(self):
        self.assertEqual(bias_read_mechanisms(["contact-metallisation-corrosion"]), [])


class MonitoringCoverageTests(unittest.TestCase):
    def test_a_complete_plan_leaves_no_gap(self):
        self.assertEqual(monitoring_gaps(_ALL_MECHANISMS, _ALL_PARAMETERS), [])

    def test_a_dropped_reading_shows_as_a_gap(self):
        planned = [p for p in _ALL_PARAMETERS if p != "coating_visual_state"]
        self.assertEqual(
            monitoring_gaps(_ALL_MECHANISMS, planned), ["coating_visual_state"]
        )

    def test_two_coating_mechanisms_share_one_reading(self):
        gaps = monitoring_gaps(
            ["protective-coating-crazing", "protective-coating-delamination"], []
        )
        self.assertEqual(gaps, ["coating_visual_state"])

    def test_gaps_come_back_sorted(self):
        gaps = monitoring_gaps(_ALL_MECHANISMS, ["coating_visual_state"])
        self.assertEqual(gaps, sorted(gaps))

    def test_a_non_sequence_monitoring_list_rejected(self):
        with self.assertRaises(ValueError):
            monitoring_gaps(_ALL_MECHANISMS, "reverse_leakage_a")


class BiasCoverageTests(unittest.TestCase):
    def test_coverage_is_the_share_of_the_duty_bias_applied(self):
        self.assertAlmostEqual(bias_coverage_fraction(40.0, 50.0), 0.8, places=9)

    def test_reading_at_the_duty_bias_is_full_coverage(self):
        self.assertAlmostEqual(bias_coverage_fraction(50.0, 50.0), 1.0, places=9)

    def test_a_bias_above_the_duty_bias_rejected(self):
        with self.assertRaises(ValueError):
            bias_coverage_fraction(70.0, 50.0)

    def test_a_zero_monitoring_bias_rejected(self):
        with self.assertRaises(ValueError):
            bias_coverage_fraction(0.0, 50.0)


class AccelerationTests(unittest.TestCase):
    def test_a_chamber_at_the_store_humidity_buys_nothing(self):
        self.assertAlmostEqual(humidity_acceleration(50.0, 50.0, 2.66), 1.0, places=12)

    def test_the_nominal_humidity_term_is_reproduced(self):
        self.assertAlmostEqual(
            humidity_acceleration(85.0, 50.0, 2.66), _HUMIDITY_TERM, places=6
        )

    def test_a_damper_chamber_buys_more(self):
        self.assertGreater(
            humidity_acceleration(85.0, 50.0, 2.66),
            humidity_acceleration(60.0, 50.0, 2.66),
        )

    def test_a_chamber_at_the_store_temperature_buys_nothing(self):
        self.assertAlmostEqual(thermal_acceleration(22.0, 22.0, 0.79), 1.0, places=12)

    def test_the_nominal_thermal_term_is_reproduced(self):
        self.assertAlmostEqual(
            thermal_acceleration(45.0, 22.0, 0.79), _THERMAL_TERM, places=6
        )

    def test_a_hotter_chamber_buys_more(self):
        self.assertGreater(
            thermal_acceleration(45.0, 22.0, 0.79),
            thermal_acceleration(30.0, 22.0, 0.79),
        )

    def test_a_humidity_at_saturation_rejected(self):
        with self.assertRaises(ValueError):
            humidity_acceleration(100.0, 50.0, 2.66)

    def test_a_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            thermal_acceleration(-300.0, 22.0, 0.79)

    def test_the_whole_factor_matches_the_stated_reference(self):
        factor = acceleration_factor(_exposure(), _storage())
        self.assertAlmostEqual(factor, _FACTOR, places=6)

    def test_a_non_mapping_exposure_rejected(self):
        with self.assertRaises(ValueError):
            acceleration_factor("45 C", _storage())

    def test_a_month_of_store_is_reproduced_by_an_unaccelerated_soak(self):
        self.assertAlmostEqual(equivalent_storage_months(730.0, 1.0), 1.0, places=9)

    def test_months_scale_with_the_soak_and_the_factor(self):
        self.assertAlmostEqual(equivalent_storage_months(1460.0, 2.0), 4.0, places=9)

    def test_a_zero_soak_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_storage_months(0.0, 10.0)


class AssessmentTests(unittest.TestCase):
    def test_a_sound_plan_serves_its_purpose(self):
        result = assess_blocking_diode_damp_storage_purpose(_case())
        self.assertEqual(result["verdict"], DAMP_STORAGE_PURPOSE_SERVED)
        self.assertEqual(result["findings"], [])

    def test_no_declared_mechanism_makes_the_exposure_unnecessary(self):
        result = assess_blocking_diode_damp_storage_purpose(_case(mechanisms=[]))
        self.assertEqual(result["verdict"], DAMP_STORAGE_NOT_REQUIRED)
        self.assertEqual(result["objectives"], [])

    def test_declared_mechanisms_with_no_exposure_are_unplanned(self):
        result = assess_blocking_diode_damp_storage_purpose(
            _case(exposure=_exposure(planned=False))
        )
        self.assertEqual(result["verdict"], DAMP_STORAGE_NOT_PLANNED)

    def test_a_condensing_chamber_is_unsound(self):
        result = assess_blocking_diode_damp_storage_purpose(
            _case(exposure=_exposure(chamber_humidity_percent=96.0))
        )
        self.assertEqual(result["verdict"], DAMP_STORAGE_CONDITIONS_UNSOUND)
        self.assertFalse(result["conditions_sound"])

    def test_a_factor_beyond_the_fitted_range_is_unsound(self):
        result = assess_blocking_diode_damp_storage_purpose(
            _case(
                exposure=_exposure(
                    chamber_temperature_c=70.0, chamber_humidity_percent=90.0
                )
            )
        )
        self.assertEqual(result["verdict"], DAMP_STORAGE_CONDITIONS_UNSOUND)
        self.assertGreater(result["acceleration_factor"], 60.0)

    def test_a_chamber_barely_above_the_store_is_unsound(self):
        result = assess_blocking_diode_damp_storage_purpose(
            _case(
                exposure=_exposure(
                    chamber_temperature_c=25.0, chamber_humidity_percent=55.0
                )
            )
        )
        self.assertEqual(result["verdict"], DAMP_STORAGE_CONDITIONS_UNSOUND)
        self.assertLess(result["acceleration_factor"], 2.0)

    def test_a_mechanism_with_no_reading_leaves_the_soak_blind(self):
        planned = [p for p in _ALL_PARAMETERS if p != "coating_visual_state"]
        result = assess_blocking_diode_damp_storage_purpose(
            _case(monitoring=_monitoring(parameters=planned))
        )
        self.assertEqual(result["verdict"], DAMP_STORAGE_MONITORING_BLIND)
        self.assertEqual(result["monitoring_gaps"], ["coating_visual_state"])

    def test_a_leakage_read_far_below_the_duty_bias_is_under_biased(self):
        result = assess_blocking_diode_damp_storage_purpose(
            _case(monitoring=_monitoring(bias_v=20.0))
        )
        self.assertEqual(result["verdict"], DAMP_STORAGE_MONITORING_UNDER_BIASED)
        self.assertFalse(result["bias_adequate"])

    def test_the_bias_is_not_judged_when_nothing_is_read_through_it(self):
        result = assess_blocking_diode_damp_storage_purpose(
            _case(
                mechanisms=["contact-metallisation-corrosion"],
                monitoring={"parameters": ["series_resistance_ohm"]},
            )
        )
        self.assertEqual(result["verdict"], DAMP_STORAGE_PURPOSE_SERVED)
        self.assertIsNone(result["bias_coverage_fraction"])

    def test_a_short_soak_falls_short_of_the_storage_life(self):
        result = assess_blocking_diode_damp_storage_purpose(
            _case(exposure=_exposure(soak_hours=200.0))
        )
        self.assertEqual(result["verdict"], DAMP_STORAGE_SHELF_LIFE_SHORTFALL)
        self.assertFalse(result["shelf_life_met"])

    def test_unsound_conditions_outrank_a_blind_monitoring_plan(self):
        planned = [p for p in _ALL_PARAMETERS if p != "coating_visual_state"]
        result = assess_blocking_diode_damp_storage_purpose(
            _case(
                exposure=_exposure(chamber_humidity_percent=96.0),
                monitoring=_monitoring(parameters=planned),
            )
        )
        self.assertEqual(result["verdict"], DAMP_STORAGE_CONDITIONS_UNSOUND)
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_the_factor_and_the_months_are_reported_whatever_the_verdict(self):
        result = assess_blocking_diode_damp_storage_purpose(
            _case(exposure=_exposure(soak_hours=200.0))
        )
        self.assertAlmostEqual(result["acceleration_factor"], _FACTOR, places=6)
        self.assertGreater(result["equivalent_storage_months"], 0.0)

    def test_the_nominal_months_match_the_stated_reference(self):
        result = assess_blocking_diode_damp_storage_purpose(_case())
        self.assertAlmostEqual(result["equivalent_storage_months"], _MONTHS, places=6)

    def test_every_family_present_is_reported(self):
        result = assess_blocking_diode_damp_storage_purpose(_case())
        self.assertEqual(sorted(result["mechanism_families"]), sorted(MECHANISM_FAMILIES))

    def test_a_missing_exposure_block_rejected(self):
        case = _case()
        del case["exposure"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_damp_storage_purpose(case)

    def test_a_missing_monitoring_block_rejected(self):
        case = _case()
        del case["monitoring"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_damp_storage_purpose(case)

    def test_a_missing_storage_block_rejected(self):
        case = _case()
        del case["storage"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_damp_storage_purpose(case)

    def test_a_missing_duty_block_rejected(self):
        case = _case()
        del case["duty"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_damp_storage_purpose(case)

    def test_a_missing_mechanisms_list_rejected(self):
        case = _case()
        del case["mechanisms"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_damp_storage_purpose(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_damp_storage_purpose(["damp"])


if __name__ == "__main__":
    unittest.main()
