"""Contract tests for the clause 6.4.3.3.2 electrical parameter test logic."""

import math
import unittest

from e2008_sca_electrical_parameter_test_process_logic import (
    CONDITIONS_NOT_CONTROLLED,
    DEFAULT_SWEEP_POLICY,
    ELECTRICAL_PARAMETERS_RECORDED,
    SWEEP_INCOMPLETE,
    SWEEP_UNDER_SAMPLED,
    assess_electrical_parameter_test,
    current_is_non_increasing,
    fill_factor,
    interpolate_current_at_voltage,
    interpolate_voltage_at_current,
    irradiance_deviation_fraction,
    irradiance_within_tolerance,
    knee_point_count,
    max_voltage_step_v,
    maximum_power_point,
    normalise_sweep,
    open_circuit_voltage_v,
    short_circuit_current_a,
    sweep_point_count,
    sweep_reaches_open_circuit,
    sweep_reaches_short_circuit,
    temperature_deviation_k,
    temperature_within_tolerance,
    validate_sweep_policy,
)

ISC_A = 0.5
VOC_V = 2.7
SHAPE_V = 0.12


def _current_at(voltage):
    """A smooth falling characteristic: full current at 0 V, zero at Voc."""
    top = 1.0 - math.exp(-VOC_V / SHAPE_V)
    return ISC_A * (1.0 - math.exp((voltage - VOC_V) / SHAPE_V)) / top


def _sweep(count=41):
    step = VOC_V / (count - 1)
    return [(index * step, _current_at(index * step)) for index in range(count)]


def _policy(**overrides):
    policy = dict(DEFAULT_SWEEP_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "sweep_points": _sweep(),
        "irradiance_w_m2": 1367.0,
        "cell_temperature_c": 28.0,
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_sweep_policy(DEFAULT_SWEEP_POLICY), DEFAULT_SWEEP_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep_policy("reference")

    def test_zero_reference_irradiance_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep_policy(_policy(reference_irradiance_w_m2=0.0))

    def test_negative_temperature_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep_policy(_policy(temperature_tolerance_k=-2.0))

    def test_a_two_point_sampling_floor_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep_policy(_policy(min_sweep_points=2))


class SweepRecordTests(unittest.TestCase):
    def test_a_recorded_sweep_keeps_every_point(self):
        self.assertEqual(sweep_point_count(_sweep(41)), 41)

    def test_points_are_ordered_by_voltage(self):
        shuffled = list(reversed(_sweep(9)))
        ordered = normalise_sweep(shuffled)
        self.assertEqual(list(ordered), sorted(ordered, key=lambda pair: pair[0]))

    def test_a_repeated_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_sweep([(0.0, 0.5), (0.0, 0.4), (1.0, 0.3)])

    def test_a_two_point_record_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_sweep([(0.0, 0.5), (2.7, 0.0)])

    def test_a_malformed_point_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_sweep([(0.0, 0.5), (1.0,), (2.0, 0.1)])

    def test_a_non_finite_current_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_sweep([(0.0, float("inf")), (1.0, 0.4), (2.0, 0.1)])

    def test_the_largest_voltage_step_is_reported(self):
        sweep = [(0.0, 0.5), (0.5, 0.45), (2.0, 0.2), (2.7, 0.0)]
        self.assertAlmostEqual(max_voltage_step_v(sweep), 1.5, places=9)

    def test_a_falling_characteristic_is_non_increasing(self):
        self.assertTrue(current_is_non_increasing(_sweep()))

    def test_a_rising_segment_breaks_the_characteristic(self):
        sweep = [(0.0, 0.5), (1.0, 0.52), (2.0, 0.3), (2.7, 0.0)]
        self.assertFalse(current_is_non_increasing(sweep))


class CrossingTests(unittest.TestCase):
    def test_the_short_circuit_crossing_is_present(self):
        self.assertTrue(sweep_reaches_short_circuit(_sweep()))

    def test_a_sweep_started_above_zero_volts_misses_short_circuit(self):
        self.assertFalse(sweep_reaches_short_circuit(_sweep()[5:]))

    def test_the_open_circuit_crossing_is_present(self):
        self.assertTrue(sweep_reaches_open_circuit(_sweep()))

    def test_a_truncated_sweep_misses_open_circuit(self):
        self.assertFalse(sweep_reaches_open_circuit(_sweep()[:-6]))

    def test_short_circuit_current_is_the_zero_voltage_current(self):
        self.assertAlmostEqual(
            _ratio(short_circuit_current_a(_sweep()), ISC_A), 1.0, places=9
        )

    def test_open_circuit_voltage_is_the_zero_current_voltage(self):
        self.assertAlmostEqual(
            _ratio(open_circuit_voltage_v(_sweep()), VOC_V), 1.0, places=9
        )

    def test_a_current_outside_the_recorded_span_is_rejected(self):
        with self.assertRaises(ValueError):
            interpolate_voltage_at_current(_sweep(), 10.0)

    def test_a_voltage_outside_the_recorded_span_is_rejected(self):
        with self.assertRaises(ValueError):
            interpolate_current_at_voltage(_sweep(), 12.0)

    def test_interpolation_lands_between_the_bracketing_points(self):
        sweep = [(0.0, 0.5), (1.0, 0.4), (2.0, 0.2), (2.7, 0.0)]
        self.assertAlmostEqual(
            interpolate_current_at_voltage(sweep, 0.5), 0.45, places=9
        )

    def test_short_circuit_is_refused_when_the_sweep_never_reaches_it(self):
        with self.assertRaises(ValueError):
            short_circuit_current_a(_sweep()[5:])


class DerivedParameterTests(unittest.TestCase):
    def test_the_peak_power_point_maximises_the_product(self):
        voltage, current, power = maximum_power_point(_sweep())
        self.assertAlmostEqual(_ratio(power, voltage * current), 1.0, places=12)

    def test_the_peak_power_point_sits_below_open_circuit(self):
        voltage, _, _ = maximum_power_point(_sweep())
        self.assertLess(voltage, VOC_V)

    def test_no_recorded_point_beats_the_peak_power(self):
        _, _, power = maximum_power_point(_sweep())
        for voltage, current in _sweep():
            self.assertTrue(voltage * current <= power or
                            math.isclose(voltage * current, power, rel_tol=1e-9))

    def test_fill_factor_is_the_power_over_the_isc_voc_product(self):
        self.assertAlmostEqual(
            _ratio(fill_factor(1.0, 0.5, 2.7), 1.0 / 1.35), 1.0, places=12
        )

    def test_fill_factor_of_this_characteristic_is_physical(self):
        _, _, power = maximum_power_point(_sweep())
        factor = fill_factor(power, ISC_A, VOC_V)
        self.assertGreater(factor, 0.5)
        self.assertLess(factor, 1.0)

    def test_fill_factor_rejects_a_zero_open_circuit_voltage(self):
        with self.assertRaises(ValueError):
            fill_factor(1.0, 0.5, 0.0)

    def test_knee_points_are_counted_inside_the_window(self):
        voltage, _, _ = maximum_power_point(_sweep())
        self.assertGreaterEqual(knee_point_count(_sweep(), voltage), 5)

    def test_a_sparse_sweep_puts_few_points_in_the_knee(self):
        voltage, _, _ = maximum_power_point(_sweep(9))
        self.assertLess(knee_point_count(_sweep(9), voltage), 5)


class ConditionTests(unittest.TestCase):
    def test_the_reference_level_shows_no_deviation(self):
        self.assertAlmostEqual(irradiance_deviation_fraction(1367.0), 0.0, places=12)

    def test_an_irradiance_exactly_at_the_tolerance_is_in_band(self):
        edge = 1367.0 * 1.02
        self.assertAlmostEqual(
            abs(irradiance_deviation_fraction(edge)), 0.02, places=9
        )
        self.assertTrue(irradiance_within_tolerance(edge))

    def test_an_irradiance_well_beyond_the_tolerance_is_out_of_band(self):
        self.assertFalse(irradiance_within_tolerance(1200.0))

    def test_a_zero_irradiance_is_rejected(self):
        with self.assertRaises(ValueError):
            irradiance_deviation_fraction(0.0)

    def test_the_control_point_shows_no_temperature_deviation(self):
        self.assertAlmostEqual(temperature_deviation_k(28.0), 0.0, places=12)

    def test_a_temperature_exactly_at_the_band_edge_is_in_band(self):
        self.assertAlmostEqual(abs(temperature_deviation_k(30.0)), 2.0, places=9)
        self.assertTrue(temperature_within_tolerance(30.0))

    def test_a_temperature_well_outside_the_band_is_out_of_band(self):
        self.assertFalse(temperature_within_tolerance(45.0))

    def test_a_non_finite_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            temperature_deviation_k(float("nan"))


class AssessmentTests(unittest.TestCase):
    def test_a_controlled_dense_run_records_the_parameters(self):
        result = assess_electrical_parameter_test(_case())
        self.assertEqual(result["verdict"], ELECTRICAL_PARAMETERS_RECORDED)
        self.assertEqual(result["findings"], [])

    def test_the_derived_parameters_are_reported(self):
        result = assess_electrical_parameter_test(_case())
        self.assertAlmostEqual(
            _ratio(result["short_circuit_current_a"], ISC_A), 1.0, places=9
        )
        self.assertAlmostEqual(
            _ratio(result["open_circuit_voltage_v"], VOC_V), 1.0, places=9
        )
        self.assertGreater(result["fill_factor"], 0.5)

    def test_a_drifted_illumination_is_a_condition_finding(self):
        result = assess_electrical_parameter_test(_case(irradiance_w_m2=1200.0))
        self.assertEqual(result["verdict"], CONDITIONS_NOT_CONTROLLED)
        self.assertFalse(result["irradiance_in_band"])

    def test_a_drifted_cell_temperature_is_a_condition_finding(self):
        result = assess_electrical_parameter_test(_case(cell_temperature_c=45.0))
        self.assertEqual(result["verdict"], CONDITIONS_NOT_CONTROLLED)
        self.assertFalse(result["temperature_in_band"])

    def test_both_condition_findings_are_reported_not_only_the_first(self):
        result = assess_electrical_parameter_test(
            _case(irradiance_w_m2=1200.0, cell_temperature_c=45.0)
        )
        self.assertEqual(len(result["findings"]), 2)

    def test_a_sparse_recording_is_under_sampled(self):
        result = assess_electrical_parameter_test(_case(sweep_points=_sweep(9)))
        self.assertEqual(result["verdict"], SWEEP_UNDER_SAMPLED)
        self.assertTrue(result["findings"])

    def test_a_sweep_that_misses_short_circuit_is_incomplete(self):
        result = assess_electrical_parameter_test(_case(sweep_points=_sweep()[5:]))
        self.assertEqual(result["verdict"], SWEEP_INCOMPLETE)
        self.assertIsNone(result["short_circuit_current_a"])

    def test_a_sweep_that_misses_open_circuit_is_incomplete(self):
        result = assess_electrical_parameter_test(_case(sweep_points=_sweep()[:-6]))
        self.assertEqual(result["verdict"], SWEEP_INCOMPLETE)
        self.assertIsNone(result["open_circuit_voltage_v"])

    def test_a_condition_failure_outranks_a_sampling_failure(self):
        result = assess_electrical_parameter_test(
            _case(sweep_points=_sweep(9), irradiance_w_m2=1200.0)
        )
        self.assertEqual(result["verdict"], CONDITIONS_NOT_CONTROLLED)
        self.assertGreater(len(result["findings"]), 1)

    def test_a_rising_current_is_reported_as_a_sampling_finding(self):
        sweep = _sweep()
        sweep[10] = (sweep[10][0], sweep[9][1] + 0.01)
        result = assess_electrical_parameter_test(_case(sweep_points=sweep))
        self.assertEqual(result["verdict"], SWEEP_UNDER_SAMPLED)
        self.assertFalse(result["current_non_increasing"])

    def test_absent_sweep_points_are_rejected(self):
        case = _case()
        del case["sweep_points"]
        with self.assertRaises(ValueError):
            assess_electrical_parameter_test(case)

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_electrical_parameter_test(["sweep_points"])

    def test_a_missing_cell_temperature_is_rejected(self):
        case = _case()
        del case["cell_temperature_c"]
        with self.assertRaises(ValueError):
            assess_electrical_parameter_test(case)


if __name__ == "__main__":
    unittest.main()
