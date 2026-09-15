"""Contract tests for the clause 4.3.3 Class 1 screening-regime logic.

The cases walk the workflow one step at a time: the hundred-percent coverage
rule for flight standard hardware, the per-family screen set, the approved
facility, the Arrhenius burn-in equivalence, the delta drift removals, the
percent defective arithmetic and the lot disposition. Each limit is exercised
on both sides, and every float comparison at a boundary is made with a
representation-sized tolerance so the suite reads the same on any platform.
"""

import math
import unittest

from q60_class_1_screening_requirements_logic import (
    BOLTZMANN_EV_PER_K,
    FAMILY_SCREENS,
    FLIGHT_STANDARD,
    HARDWARE_STANDARDS,
    KELVIN_OFFSET,
    SCREENING_TOLERANCE,
    acceleration_factor,
    assess_screening_regime,
    burn_in_findings,
    delta_removals,
    drift_percent,
    equivalent_burn_in_hours,
    family_screens,
    lot_disposition,
    missing_screens,
    percent_defective,
)

MICROCIRCUIT = list(FAMILY_SCREENS["microcircuit"])


def _burn_in(**overrides):
    burn_in = {
        "hours": 240.0,
        "temperature_c": 150.0,
        "reference_hours": 240.0,
        "reference_temperature_c": 150.0,
        "activation_energy_ev": 0.7,
    }
    burn_in.update(overrides)
    return burn_in


def _spec(**overrides):
    spec = {
        "hardware_standard": "flight",
        "part_family": "microcircuit",
        "lot_size": 100,
        "devices_screened": 100,
        "performed_screens": list(MICROCIRCUIT),
        "facility": {"name": "manufacturer-screening-line", "approved": True},
        "burn_in": _burn_in(),
        "monitored_devices": [
            {"device_id": "u001", "parameter": "supply-current", "before": 10.0, "after": 10.1},
            {"device_id": "u002", "parameter": "supply-current", "before": 10.0, "after": 10.2},
        ],
        "delta_limit_percent": 5.0,
        "catastrophic_failures": 1,
        "allowable_percent": 5.0,
    }
    spec.update(overrides)
    return spec


class FamilyScreenTests(unittest.TestCase):
    def test_microcircuit_family_carries_seal_and_radiography(self):
        screens = family_screens("microcircuit")
        self.assertIn("seal-fine-and-gross-leak", screens)
        self.assertIn("radiographic-inspection", screens)

    def test_non_hermetic_family_carries_no_seal_screen(self):
        screens = family_screens("non-hermetic-passive")
        self.assertNotIn("seal-fine-and-gross-leak", screens)

    def test_family_name_normalised(self):
        self.assertEqual(
            family_screens("Discrete_Semiconductor"), FAMILY_SCREENS["discrete-semiconductor"]
        )

    def test_every_family_ends_on_external_visual(self):
        for screens in FAMILY_SCREENS.values():
            self.assertEqual(screens[-1], "external-visual")

    def test_every_family_brackets_burn_in_with_electricals(self):
        for screens in FAMILY_SCREENS.values():
            self.assertLess(
                screens.index("pre-burn-in-electrical"), screens.index("burn-in")
            )
            self.assertLess(
                screens.index("burn-in"), screens.index("post-burn-in-electrical")
            )

    def test_unknown_family_refused(self):
        with self.assertRaises(ValueError):
            family_screens("potting-compound")

    def test_blank_family_refused(self):
        with self.assertRaises(ValueError):
            family_screens("   ")


class MissingScreenTests(unittest.TestCase):
    def test_complete_set_has_nothing_missing(self):
        self.assertEqual(missing_screens("microcircuit", MICROCIRCUIT), [])

    def test_dropped_screen_named(self):
        performed = [s for s in MICROCIRCUIT if s != "constant-acceleration"]
        self.assertEqual(
            missing_screens("microcircuit", performed), ["constant-acceleration"]
        )

    def test_extra_screen_is_not_a_shortfall(self):
        performed = MICROCIRCUIT + ["customer-witness-hold-point"]
        self.assertEqual(missing_screens("microcircuit", performed), [])

    def test_repeated_screen_refused(self):
        with self.assertRaises(ValueError):
            missing_screens("microcircuit", MICROCIRCUIT + ["burn-in"])

    def test_non_sequence_performed_refused(self):
        with self.assertRaises(ValueError):
            missing_screens("microcircuit", "burn-in")


class AccelerationTests(unittest.TestCase):
    def test_equal_temperatures_give_unit_acceleration(self):
        self.assertAlmostEqual(acceleration_factor(125.0, 125.0, 0.7), 1.0, places=9)

    def test_hotter_burn_in_accelerates(self):
        self.assertGreater(acceleration_factor(125.0, 150.0, 0.7), 3.0)

    def test_cooler_burn_in_decelerates(self):
        self.assertLess(acceleration_factor(125.0, 85.0, 0.7), 0.2)

    def test_factor_matches_the_arrhenius_definition(self):
        value = acceleration_factor(125.0, 150.0, 0.7)
        self.assertAlmostEqual(value, 3.338028336, places=6)

    def test_higher_activation_energy_accelerates_more(self):
        low = acceleration_factor(125.0, 150.0, 0.4)
        high = acceleration_factor(125.0, 150.0, 1.0)
        self.assertGreater(high - low, 1.0)

    def test_inverse_pair_multiplies_to_one(self):
        forward = acceleration_factor(125.0, 150.0, 0.7)
        backward = acceleration_factor(150.0, 125.0, 0.7)
        self.assertAlmostEqual(forward * backward, 1.0, places=9)

    def test_temperature_below_absolute_zero_refused(self):
        with self.assertRaises(ValueError):
            acceleration_factor(-300.0, 150.0, 0.7)

    def test_non_positive_activation_energy_refused(self):
        with self.assertRaises(ValueError):
            acceleration_factor(125.0, 150.0, 0.0)

    def test_boltzmann_constant_is_in_electronvolt_per_kelvin(self):
        self.assertAlmostEqual(BOLTZMANN_EV_PER_K * 1e5, 8.617333262, places=6)

    def test_kelvin_offset_is_the_celsius_zero(self):
        self.assertAlmostEqual(KELVIN_OFFSET, 273.15, places=9)


class EquivalentHoursTests(unittest.TestCase):
    def test_same_condition_owes_the_reference_hours(self):
        self.assertAlmostEqual(
            equivalent_burn_in_hours(240.0, 125.0, 125.0, 0.7), 240.0, places=9
        )

    def test_hotter_condition_owes_fewer_hours(self):
        self.assertLess(equivalent_burn_in_hours(1000.0, 125.0, 150.0, 0.7), 400.0)

    def test_cooler_condition_owes_more_hours(self):
        self.assertGreater(equivalent_burn_in_hours(1000.0, 125.0, 85.0, 0.7), 4000.0)

    def test_hours_times_factor_return_the_reference(self):
        owed = equivalent_burn_in_hours(1000.0, 125.0, 150.0, 0.7)
        factor = acceleration_factor(125.0, 150.0, 0.7)
        self.assertAlmostEqual(owed * factor, 1000.0, places=6)

    def test_non_positive_reference_hours_refused(self):
        with self.assertRaises(ValueError):
            equivalent_burn_in_hours(0.0, 125.0, 150.0, 0.7)


class BurnInFindingTests(unittest.TestCase):
    def test_matching_condition_raises_nothing(self):
        record = burn_in_findings(_burn_in())
        self.assertEqual(record["findings"], [])
        self.assertAlmostEqual(record["hours_owed"], 240.0, places=9)

    def test_shortfall_reported(self):
        record = burn_in_findings(_burn_in(hours=100.0))
        self.assertTrue(any("short of" in f for f in record["findings"]))

    def test_hotter_condition_lets_a_shorter_burn_in_pass(self):
        record = burn_in_findings(
            _burn_in(hours=120.0, temperature_c=175.0, reference_hours=240.0,
                     reference_temperature_c=150.0)
        )
        self.assertEqual(record["findings"], [])

    def test_exact_owed_hours_are_not_a_shortfall(self):
        owed = equivalent_burn_in_hours(240.0, 150.0, 175.0, 0.7)
        record = burn_in_findings(
            _burn_in(hours=owed, temperature_c=175.0, reference_temperature_c=150.0)
        )
        self.assertEqual(record["findings"], [])

    def test_missing_burn_in_key_refused(self):
        burn_in = _burn_in()
        del burn_in["temperature_c"]
        with self.assertRaises(ValueError):
            burn_in_findings(burn_in)

    def test_negative_hours_refused(self):
        with self.assertRaises(ValueError):
            burn_in_findings(_burn_in(hours=-1.0))


class DriftTests(unittest.TestCase):
    def test_no_change_is_zero_drift(self):
        self.assertAlmostEqual(drift_percent(10.0, 10.0), 0.0, places=9)

    def test_ten_percent_rise(self):
        self.assertAlmostEqual(drift_percent(10.0, 11.0), 10.0, places=9)

    def test_drift_is_a_magnitude(self):
        self.assertAlmostEqual(drift_percent(10.0, 9.0), 10.0, places=9)

    def test_negative_reference_uses_its_magnitude(self):
        self.assertAlmostEqual(drift_percent(-10.0, -11.0), 10.0, places=9)

    def test_zero_reference_refused(self):
        with self.assertRaises(ValueError):
            drift_percent(0.0, 1.0)

    def test_non_numeric_reading_refused(self):
        with self.assertRaises(ValueError):
            drift_percent("10", 11.0)


class DeltaRemovalTests(unittest.TestCase):
    def test_drift_inside_the_limit_is_kept(self):
        records = delta_removals(
            [{"device_id": "u1", "parameter": "icc", "before": 10.0, "after": 10.4}], 5.0
        )
        self.assertFalse(records[0]["removed"])

    def test_drift_outside_the_limit_is_removed(self):
        records = delta_removals(
            [{"device_id": "u1", "parameter": "icc", "before": 10.0, "after": 10.6}], 5.0
        )
        self.assertTrue(records[0]["removed"])

    def test_drift_exactly_on_the_limit_is_kept(self):
        records = delta_removals(
            [{"device_id": "u1", "parameter": "icc", "before": 10.0, "after": 10.5}], 5.0
        )
        self.assertAlmostEqual(records[0]["drift_percent"], 5.0, places=9)
        self.assertFalse(records[0]["removed"])

    def test_same_device_and_parameter_twice_refused(self):
        with self.assertRaises(ValueError):
            delta_removals(
                [
                    {"device_id": "u1", "parameter": "icc", "before": 10.0, "after": 10.1},
                    {"device_id": "u1", "parameter": "ICC", "before": 10.0, "after": 10.2},
                ],
                5.0,
            )

    def test_second_parameter_on_one_device_allowed(self):
        records = delta_removals(
            [
                {"device_id": "u1", "parameter": "icc", "before": 10.0, "after": 10.1},
                {"device_id": "u1", "parameter": "vol", "before": 0.4, "after": 0.41},
            ],
            5.0,
        )
        self.assertEqual(len(records), 2)

    def test_negative_limit_refused(self):
        with self.assertRaises(ValueError):
            delta_removals([], -1.0)

    def test_device_missing_a_key_refused(self):
        with self.assertRaises(ValueError):
            delta_removals([{"device_id": "u1", "before": 10.0, "after": 10.1}], 5.0)


class PercentDefectiveTests(unittest.TestCase):
    def test_no_removals_is_zero(self):
        self.assertAlmostEqual(percent_defective(100, 0), 0.0, places=9)

    def test_two_of_a_hundred(self):
        self.assertAlmostEqual(percent_defective(100, 2), 2.0, places=9)

    def test_every_device_removed_is_a_hundred(self):
        self.assertAlmostEqual(percent_defective(40, 40), 100.0, places=9)

    def test_thirds_are_representation_sized(self):
        self.assertAlmostEqual(percent_defective(300, 1), 1.0 / 3.0, places=9)

    def test_more_removals_than_entered_refused(self):
        with self.assertRaises(ValueError):
            percent_defective(10, 11)

    def test_empty_lot_refused(self):
        with self.assertRaises(ValueError):
            percent_defective(0, 0)


class LotDispositionTests(unittest.TestCase):
    def test_lot_inside_the_allowance_accepted(self):
        record = lot_disposition(100, 2, 5.0)
        self.assertEqual(record["disposition"], "lot-accepted")

    def test_lot_outside_the_allowance_rejected(self):
        record = lot_disposition(100, 6, 5.0)
        self.assertEqual(record["disposition"], "lot-rejected")

    def test_lot_exactly_on_the_allowance_accepted(self):
        record = lot_disposition(100, 5, 5.0)
        self.assertAlmostEqual(record["percent_defective"], 5.0, places=9)
        self.assertTrue(record["accepted"])

    def test_allowance_outside_the_percentage_range_refused(self):
        with self.assertRaises(ValueError):
            lot_disposition(100, 1, 140.0)


class RegimeTests(unittest.TestCase):
    def test_clean_regime_is_satisfied(self):
        verdict = assess_screening_regime(_spec())
        self.assertTrue(verdict["regime_satisfied"])
        self.assertEqual(verdict["findings"], [])

    def test_sampled_screen_on_flight_hardware_reported(self):
        verdict = assess_screening_regime(_spec(devices_screened=80))
        self.assertFalse(verdict["regime_satisfied"])
        self.assertTrue(
            any("flight standard hardware takes every device" in f for f in verdict["findings"])
        )

    def test_ground_support_hardware_may_be_sampled(self):
        verdict = assess_screening_regime(
            _spec(hardware_standard="ground-support", devices_screened=80, catastrophic_failures=0)
        )
        self.assertTrue(verdict["regime_satisfied"])

    def test_dropped_screen_reported(self):
        performed = [s for s in MICROCIRCUIT if s != "particle-impact-noise-detection"]
        verdict = assess_screening_regime(_spec(performed_screens=performed))
        self.assertIn("particle-impact-noise-detection", verdict["missing_screens"])

    def test_unapproved_facility_reported(self):
        verdict = assess_screening_regime(
            _spec(facility={"name": "third-party-house", "approved": False})
        )
        self.assertTrue(any("not an approved source" in f for f in verdict["findings"]))

    def test_delta_removal_counts_toward_percent_defective(self):
        devices = [
            {"device_id": "u001", "parameter": "supply-current", "before": 10.0, "after": 12.0},
        ]
        verdict = assess_screening_regime(
            _spec(monitored_devices=devices, catastrophic_failures=0)
        )
        self.assertEqual(verdict["delta_removed_devices"], ["u001"])
        self.assertAlmostEqual(verdict["percent_defective"], 1.0, places=9)

    def test_lot_over_the_allowance_is_rejected_as_a_lot(self):
        verdict = assess_screening_regime(_spec(catastrophic_failures=8))
        self.assertEqual(verdict["disposition"], "lot-rejected")
        self.assertTrue(any("the lot is rejected" in f for f in verdict["findings"]))

    def test_every_finding_is_carried_not_only_the_first(self):
        verdict = assess_screening_regime(
            _spec(
                devices_screened=90,
                facility={"name": "third-party-house", "approved": False},
                burn_in=_burn_in(hours=10.0),
            )
        )
        self.assertGreaterEqual(len(verdict["findings"]), 3)

    def test_unknown_hardware_standard_refused(self):
        with self.assertRaises(ValueError):
            assess_screening_regime(_spec(hardware_standard="prototype"))

    def test_more_screened_than_the_lot_refused(self):
        with self.assertRaises(ValueError):
            assess_screening_regime(_spec(devices_screened=120))

    def test_missing_required_key_refused(self):
        spec = _spec()
        del spec["burn_in"]
        with self.assertRaises(ValueError):
            assess_screening_regime(spec)

    def test_non_mapping_spec_refused(self):
        with self.assertRaises(ValueError):
            assess_screening_regime(["not", "a", "mapping"])

    def test_flight_standard_is_a_recognised_standard(self):
        self.assertIn(FLIGHT_STANDARD, HARDWARE_STANDARDS)

    def test_tolerance_is_representation_sized_only(self):
        self.assertLess(SCREENING_TOLERANCE, 1e-6)

    def test_exponential_is_available_offline(self):
        self.assertAlmostEqual(math.exp(0.0), 1.0, places=9)


if __name__ == "__main__":
    unittest.main()
