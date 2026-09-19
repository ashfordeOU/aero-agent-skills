"""Contract tests for the clause 12.6.11.1.1 ionising irradiation exposure.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused exposure policy,
a facility outside the two admitted, an unstated bias condition, a dose
rate or beam energy outside its window, a sample plane too uneven for one
dose to describe it, and segments that accumulate away from the target.
"""

import unittest

from e2008_ionising_irradiation_test_process_logic import (
    ACCUMULATED_DOSE_OFF_TARGET,
    BEAM_CONDITIONS_INVALID,
    BIAS_CONDITION_NOT_STATED,
    DEFAULT_IRRADIATION_POLICY,
    DOSE_UNIFORMITY_OUT_OF_BAND,
    ELECTRON,
    EXPOSURE_ACCEPTED,
    FACILITY_NOT_ADMITTED,
    GAMMA,
    REVERSE_BIASED,
    accumulated_dose_gy,
    beam_energy_within_window,
    beam_on_hours,
    bias_condition_stated,
    dose_deviation_fraction,
    dose_rate_window,
    dose_rate_within_window,
    dose_within_tolerance,
    facility_admitted,
    mean_rate_gy_per_h,
    nominal_exposure_hours,
    normalise_facility,
    run_ionising_irradiation_exposure,
    segment_dose_gy,
    uniformity_spread_fraction,
    uniformity_within_allowance,
    validate_irradiation_policy,
    validate_segment,
)

TARGET_DOSE_GY = 1000.0


def _policy(**overrides):
    policy = dict(DEFAULT_IRRADIATION_POLICY)
    policy.update(overrides)
    return policy


def _segments(rate=10.0, hours=50.0, count=2):
    return [{"rate_gy_per_h": rate, "duration_hours": hours} for _ in range(count)]


def _monitors():
    return [0.98, 1.00, 1.02]


def _gamma_case(**overrides):
    case = {
        "facility": GAMMA,
        "bias_condition": REVERSE_BIASED,
        "target_dose_gy": TARGET_DOSE_GY,
        "segments": _segments(),
        "monitor_readings_gy": _monitors(),
    }
    case.update(overrides)
    return case


def _electron_case(**overrides):
    case = _gamma_case(
        facility=ELECTRON,
        beam_energy_mev=1.0,
        segments=_segments(rate=100.0, hours=5.0, count=2),
    )
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_irradiation_policy(DEFAULT_IRRADIATION_POLICY),
            DEFAULT_IRRADIATION_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_irradiation_policy("gamma_min_rate_gy_per_h")

    def test_inverted_gamma_rate_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_irradiation_policy(
                _policy(gamma_min_rate_gy_per_h=40.0, gamma_max_rate_gy_per_h=36.0)
            )

    def test_whole_uniformity_spread_rejected(self):
        with self.assertRaises(ValueError):
            validate_irradiation_policy(_policy(max_uniformity_spread_fraction=1.0))

    def test_whole_dose_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_irradiation_policy(_policy(dose_tolerance_fraction=1.0))


class FacilityTests(unittest.TestCase):
    def test_both_admitted_facilities_recognised(self):
        self.assertTrue(facility_admitted(GAMMA))
        self.assertTrue(facility_admitted(ELECTRON))

    def test_a_third_facility_is_not_admitted(self):
        self.assertFalse(facility_admitted("proton-cyclotron"))

    def test_facility_label_case_is_absorbed(self):
        self.assertEqual(normalise_facility("Cobalt-Gamma-Source"), GAMMA)

    def test_unknown_facility_refused_on_normalisation(self):
        with self.assertRaises(ValueError):
            normalise_facility("heavy-ion-beam")


class BiasTests(unittest.TestCase):
    def test_stated_bias_condition_recognised(self):
        self.assertTrue(bias_condition_stated(REVERSE_BIASED))
        self.assertTrue(bias_condition_stated("Unbiased"))

    def test_absent_or_unknown_bias_is_not_stated(self):
        self.assertFalse(bias_condition_stated(None))
        self.assertFalse(bias_condition_stated("whatever the rig settled at"))


class RateWindowTests(unittest.TestCase):
    def test_gamma_window_is_the_slow_one(self):
        low, high = dose_rate_window(GAMMA)
        self.assertAlmostEqual(low, 0.36, places=9)
        self.assertAlmostEqual(high, 36.0, places=9)

    def test_electron_window_sits_above_the_gamma_window(self):
        _gamma_low, gamma_high = dose_rate_window(GAMMA)
        electron_low, electron_high = dose_rate_window(ELECTRON)
        # The two windows abut exactly by construction: the policy table
        # gives the electron floor the same value as the gamma ceiling,
        # with no arithmetic between them. Assert that exact equality --
        # not a near-boundary inequality -- plus the real separation of
        # the two ceilings.
        self.assertEqual(electron_low, gamma_high)
        self.assertGreater(electron_high, gamma_high)

    def test_rate_exactly_at_the_window_edge_admitted(self):
        self.assertTrue(dose_rate_within_window(GAMMA, 0.36))
        self.assertTrue(dose_rate_within_window(GAMMA, 36.0))

    def test_rate_below_the_gamma_floor_refused(self):
        self.assertFalse(dose_rate_within_window(GAMMA, 0.01))

    def test_beam_energy_window_bounds_both_ways(self):
        self.assertTrue(beam_energy_within_window(1.0))
        self.assertFalse(beam_energy_within_window(40.0))
        self.assertFalse(beam_energy_within_window(0.1))


class DoseTests(unittest.TestCase):
    def test_segment_dose_is_rate_held_for_a_duration(self):
        self.assertAlmostEqual(segment_dose_gy(10.0, 50.0), 500.0, places=9)

    def test_segments_accumulate_to_the_total(self):
        self.assertAlmostEqual(accumulated_dose_gy(_segments()), 1000.0, places=9)

    def test_beam_on_hours_counts_only_the_segments(self):
        self.assertAlmostEqual(beam_on_hours(_segments()), 100.0, places=9)

    def test_mean_rate_is_dose_over_beam_on_time(self):
        mixed = [
            {"rate_gy_per_h": 10.0, "duration_hours": 50.0},
            {"rate_gy_per_h": 20.0, "duration_hours": 50.0},
        ]
        self.assertAlmostEqual(mean_rate_gy_per_h(mixed), 15.0, places=9)

    def test_nominal_hours_is_target_over_rate(self):
        self.assertAlmostEqual(
            nominal_exposure_hours(TARGET_DOSE_GY, 10.0), 100.0, places=9
        )

    def test_deviation_is_a_share_of_the_target(self):
        self.assertAlmostEqual(
            dose_deviation_fraction(900.0, TARGET_DOSE_GY), 0.1, places=9
        )

    def test_dose_exactly_at_the_tolerance_edge_admitted(self):
        self.assertTrue(dose_within_tolerance(1100.0, TARGET_DOSE_GY))
        self.assertFalse(dose_within_tolerance(700.0, TARGET_DOSE_GY))

    def test_segment_with_no_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_segment({"rate_gy_per_h": 10.0, "duration_hours": 0.0})

    def test_empty_segment_list_rejected(self):
        with self.assertRaises(ValueError):
            accumulated_dose_gy([])


class UniformityTests(unittest.TestCase):
    def test_spread_is_the_range_over_the_mean(self):
        self.assertAlmostEqual(uniformity_spread_fraction(_monitors()), 0.04, places=9)

    def test_single_monitor_rejected(self):
        with self.assertRaises(ValueError):
            uniformity_spread_fraction([1.0])

    def test_spread_exactly_at_the_allowance_admitted(self):
        self.assertTrue(uniformity_within_allowance([0.95, 1.05]))

    def test_uneven_plane_refused(self):
        self.assertFalse(uniformity_within_allowance([0.70, 1.30]))


class RunTests(unittest.TestCase):
    def test_nominal_gamma_exposure_accepted(self):
        result = run_ionising_irradiation_exposure(_gamma_case())
        self.assertEqual(result["verdict"], EXPOSURE_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["facility"], GAMMA)
        self.assertAlmostEqual(result["accumulated_dose_gy"], 1000.0, places=9)
        self.assertAlmostEqual(result["beam_on_hours"], 100.0, places=9)

    def test_nominal_electron_exposure_accepted(self):
        result = run_ionising_irradiation_exposure(_electron_case())
        self.assertEqual(result["verdict"], EXPOSURE_ACCEPTED)
        self.assertAlmostEqual(result["accumulated_dose_gy"], 1000.0, places=9)
        self.assertLess(result["beam_on_hours"], 20.0)

    def test_third_facility_is_outside_this_process(self):
        result = run_ionising_irradiation_exposure(
            _gamma_case(facility="proton-cyclotron")
        )
        self.assertEqual(result["verdict"], FACILITY_NOT_ADMITTED)

    def test_unstated_bias_closes_the_run(self):
        case = _gamma_case()
        del case["bias_condition"]
        result = run_ionising_irradiation_exposure(case)
        self.assertEqual(result["verdict"], BIAS_CONDITION_NOT_STATED)

    def test_gamma_run_below_the_rate_floor_reports_beam_conditions(self):
        result = run_ionising_irradiation_exposure(
            _gamma_case(segments=_segments(rate=0.05, hours=10000.0, count=2))
        )
        self.assertEqual(result["verdict"], BEAM_CONDITIONS_INVALID)

    def test_accelerator_run_without_a_beam_energy_reports_beam_conditions(self):
        case = _electron_case()
        del case["beam_energy_mev"]
        result = run_ionising_irradiation_exposure(case)
        self.assertEqual(result["verdict"], BEAM_CONDITIONS_INVALID)

    def test_accelerator_run_above_the_energy_window_reports_beam_conditions(self):
        result = run_ionising_irradiation_exposure(_electron_case(beam_energy_mev=40.0))
        self.assertEqual(result["verdict"], BEAM_CONDITIONS_INVALID)

    def test_uneven_sample_plane_closes_the_run(self):
        result = run_ionising_irradiation_exposure(
            _gamma_case(monitor_readings_gy=[0.70, 1.00, 1.30])
        )
        self.assertEqual(result["verdict"], DOSE_UNIFORMITY_OUT_OF_BAND)

    def test_under_dosed_run_is_off_target(self):
        result = run_ionising_irradiation_exposure(
            _gamma_case(segments=_segments(rate=10.0, hours=30.0, count=2))
        )
        self.assertEqual(result["verdict"], ACCUMULATED_DOSE_OFF_TARGET)
        self.assertTrue(result["findings"])

    def test_case_without_monitor_readings_rejected(self):
        case = _gamma_case()
        del case["monitor_readings_gy"]
        with self.assertRaises(ValueError):
            run_ionising_irradiation_exposure(case)

    def test_case_without_a_facility_rejected(self):
        case = _gamma_case()
        del case["facility"]
        with self.assertRaises(ValueError):
            run_ionising_irradiation_exposure(case)


if __name__ == "__main__":
    unittest.main()
