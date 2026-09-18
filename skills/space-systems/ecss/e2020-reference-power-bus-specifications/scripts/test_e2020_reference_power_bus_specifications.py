"""Contract tests for the clause 5.1 reference power bus specification.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused marginal-band
policy, a specification whose transient envelope is narrower than its
steady band, the worst-case instantaneous voltages built from steady
limits, ripple and transients, a device short on either voltage bound or
on transient duration, a device landing exactly on a bound, and the
weakest-device report.
"""

import unittest

from e2020_reference_power_bus_specifications_logic import (
    DEFAULT_BUS_POLICY,
    DEVICE_OUTSIDE_BUS_ENVELOPE,
    DEVICES_COVER_REFERENCE_BUS,
    LOWER_VOLTAGE,
    SPECIFICATION_NOT_ESTABLISHED,
    TRANSIENT_DURATION,
    UPPER_VOLTAGE,
    assess_reference_bus_compatibility,
    device_compatibilities,
    device_compatibility,
    marginal_device_advisories,
    validate_bus_policy,
    validate_bus_specification,
    validate_device_window,
    weakest_device,
    worst_case_instantaneous_voltages,
)


def _policy(**overrides):
    policy = dict(DEFAULT_BUS_POLICY)
    policy.update(overrides)
    return policy


def _specification(**overrides):
    specification = {
        "reference": "reference bus RB-28, issue A",
        "nominal_voltage_v": 28.0,
        "steady_min_voltage_v": 26.0,
        "steady_max_voltage_v": 29.0,
        "ripple_peak_to_peak_v": 0.5,
        "transient_max_voltage_v": 32.0,
        "transient_min_voltage_v": 21.0,
        "max_transient_duration_ms": 10.0,
    }
    specification.update(overrides)
    return specification


def _device(**overrides):
    device = {
        "id": "LCL-07",
        "min_operating_voltage_v": 20.0,
        "max_operating_voltage_v": 34.0,
        "max_tolerated_transient_duration_ms": 20.0,
    }
    device.update(overrides)
    return device


def _case(**overrides):
    case = {"bus_specification": _specification(), "devices": [_device()]}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_bus_policy(DEFAULT_BUS_POLICY), DEFAULT_BUS_POLICY)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_bus_policy("marginal_voltage_band_v")

    def test_zero_voltage_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_bus_policy(_policy(marginal_voltage_band_v=0.0))

    def test_negative_duration_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_bus_policy(_policy(marginal_duration_band_ms=-2.0))


class SpecificationTests(unittest.TestCase):
    def test_a_valid_specification_reads_back(self):
        spec = validate_bus_specification(_specification())
        self.assertAlmostEqual(spec["nominal_voltage_v"], 28.0, places=12)
        self.assertAlmostEqual(spec["max_transient_duration_ms"], 10.0, places=12)

    def test_inverted_steady_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_bus_specification(
                _specification(steady_min_voltage_v=29.0, steady_max_voltage_v=26.0)
            )

    def test_nominal_outside_the_steady_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_bus_specification(_specification(nominal_voltage_v=31.0))

    def test_nominal_exactly_on_the_steady_upper_limit_admitted(self):
        spec = validate_bus_specification(_specification(nominal_voltage_v=29.0))
        self.assertAlmostEqual(spec["nominal_voltage_v"], 29.0, places=9)

    def test_upper_transient_below_the_steady_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_bus_specification(_specification(transient_max_voltage_v=28.5))

    def test_lower_transient_above_the_steady_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_bus_specification(_specification(transient_min_voltage_v=27.0))

    def test_a_transient_bound_equal_to_the_steady_limit_is_admitted(self):
        spec = validate_bus_specification(
            _specification(transient_max_voltage_v=29.0, transient_min_voltage_v=26.0)
        )
        self.assertAlmostEqual(spec["transient_max_voltage_v"], 29.0, places=9)

    def test_negative_ripple_rejected(self):
        with self.assertRaises(ValueError):
            validate_bus_specification(_specification(ripple_peak_to_peak_v=-0.1))

    def test_zero_transient_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_bus_specification(_specification(max_transient_duration_ms=0.0))

    def test_non_mapping_specification_rejected(self):
        with self.assertRaises(ValueError):
            validate_bus_specification("reference bus RB-28")


class WorstCaseTests(unittest.TestCase):
    def test_the_transient_sets_the_extremes_when_it_is_wider(self):
        extremes = worst_case_instantaneous_voltages(_specification())
        self.assertAlmostEqual(
            extremes["highest_instantaneous_voltage_v"], 32.0, places=9
        )
        self.assertAlmostEqual(
            extremes["lowest_instantaneous_voltage_v"], 21.0, places=9
        )

    def test_ripple_sets_the_extremes_when_the_transient_is_tight(self):
        extremes = worst_case_instantaneous_voltages(
            _specification(
                transient_max_voltage_v=29.0,
                transient_min_voltage_v=26.0,
                ripple_peak_to_peak_v=1.0,
            )
        )
        self.assertAlmostEqual(
            extremes["highest_instantaneous_voltage_v"], 29.5, places=9
        )
        self.assertAlmostEqual(
            extremes["lowest_instantaneous_voltage_v"], 25.5, places=9
        )

    def test_half_the_ripple_is_reported(self):
        extremes = worst_case_instantaneous_voltages(_specification())
        self.assertAlmostEqual(extremes["half_ripple_v"], 0.25, places=12)


class DeviceWindowTests(unittest.TestCase):
    def test_a_valid_window_reads_back(self):
        window = validate_device_window(_device())
        self.assertEqual(window["id"], "LCL-07")
        self.assertAlmostEqual(window["max_operating_voltage_v"], 34.0, places=12)

    def test_blank_device_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_device_window(_device(id="  "))

    def test_collapsed_operating_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_device_window(
                _device(min_operating_voltage_v=28.0, max_operating_voltage_v=28.0)
            )

    def test_non_positive_tolerated_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_device_window(_device(max_tolerated_transient_duration_ms=0.0))


class CompatibilityTests(unittest.TestCase):
    def test_a_wide_device_covers_the_bus(self):
        result = device_compatibility(_device(), _specification())
        self.assertTrue(result["compatible"])
        self.assertAlmostEqual(result["upper_margin_v"], 2.0, places=9)
        self.assertAlmostEqual(result["lower_margin_v"], 1.0, places=9)
        self.assertAlmostEqual(result["duration_margin_ms"], 10.0, places=9)

    def test_a_device_short_at_the_top_is_named(self):
        result = device_compatibility(
            _device(max_operating_voltage_v=31.0), _specification()
        )
        self.assertFalse(result["compatible"])
        self.assertEqual(result["shortfalls"], (UPPER_VOLTAGE,))

    def test_a_device_short_at_the_bottom_is_named(self):
        result = device_compatibility(
            _device(min_operating_voltage_v=22.0), _specification()
        )
        self.assertEqual(result["shortfalls"], (LOWER_VOLTAGE,))

    def test_a_device_short_on_duration_is_named(self):
        result = device_compatibility(
            _device(max_tolerated_transient_duration_ms=4.0), _specification()
        )
        self.assertEqual(result["shortfalls"], (TRANSIENT_DURATION,))

    def test_voltage_margin_does_not_offset_a_duration_shortfall(self):
        result = device_compatibility(
            _device(
                max_operating_voltage_v=60.0,
                min_operating_voltage_v=5.0,
                max_tolerated_transient_duration_ms=4.0,
            ),
            _specification(),
        )
        self.assertFalse(result["compatible"])
        self.assertEqual(result["shortfalls"], (TRANSIENT_DURATION,))

    def test_a_device_exactly_on_both_bounds_is_compatible(self):
        result = device_compatibility(
            _device(
                max_operating_voltage_v=32.0,
                min_operating_voltage_v=21.0,
                max_tolerated_transient_duration_ms=10.0,
            ),
            _specification(),
        )
        self.assertAlmostEqual(result["upper_margin_v"], 0.0, places=9)
        self.assertAlmostEqual(result["lower_margin_v"], 0.0, places=9)
        self.assertAlmostEqual(result["duration_margin_ms"], 0.0, places=9)
        self.assertTrue(result["compatible"])

    def test_duplicate_device_identifier_rejected(self):
        with self.assertRaises(ValueError):
            device_compatibilities([_device(), _device()], _specification())

    def test_an_empty_device_list_rejected(self):
        with self.assertRaises(ValueError):
            device_compatibilities([], _specification())

    def test_the_weakest_device_is_the_one_with_least_room(self):
        results = device_compatibilities(
            [_device(), _device(id="LCL-08", max_operating_voltage_v=32.4)],
            _specification(),
        )
        self.assertEqual(weakest_device(results)["id"], "LCL-08")

    def test_weakest_device_refuses_an_empty_sequence(self):
        with self.assertRaises(ValueError):
            weakest_device(())


class AdvisoryTests(unittest.TestCase):
    def test_a_thin_voltage_margin_raises_an_advisory(self):
        results = device_compatibilities(
            [_device(max_operating_voltage_v=32.3)], _specification()
        )
        advisories = marginal_device_advisories(results)
        self.assertTrue(any("marginal band" in a for a in advisories))

    def test_an_incompatible_device_raises_no_advisory(self):
        results = device_compatibilities(
            [_device(max_operating_voltage_v=31.0)], _specification()
        )
        self.assertEqual(marginal_device_advisories(results), ())

    def test_a_thin_duration_margin_raises_its_own_advisory(self):
        results = device_compatibilities(
            [_device(max_tolerated_transient_duration_ms=10.5)], _specification()
        )
        advisories = marginal_device_advisories(results)
        self.assertTrue(any("transient" in a for a in advisories))


class AssessmentTests(unittest.TestCase):
    def test_a_covered_bus_closes_clean(self):
        result = assess_reference_bus_compatibility(_case())
        self.assertEqual(result["verdict"], DEVICES_COVER_REFERENCE_BUS)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["weakest_device_id"], "LCL-07")

    def test_a_missing_specification_closes_the_assessment(self):
        case = _case()
        del case["bus_specification"]
        result = assess_reference_bus_compatibility(case)
        self.assertEqual(result["verdict"], SPECIFICATION_NOT_ESTABLISHED)
        self.assertEqual(result["device_results"], ())

    def test_a_blank_bus_reference_closes_the_assessment(self):
        result = assess_reference_bus_compatibility(
            _case(bus_specification=_specification(reference="   "))
        )
        self.assertEqual(result["verdict"], SPECIFICATION_NOT_ESTABLISHED)

    def test_the_worst_case_extremes_are_reported(self):
        result = assess_reference_bus_compatibility(_case())
        self.assertAlmostEqual(
            result["highest_instantaneous_voltage_v"], 32.0, places=9
        )
        self.assertAlmostEqual(
            result["lowest_instantaneous_voltage_v"], 21.0, places=9
        )

    def test_an_incompatible_device_moves_the_verdict(self):
        result = assess_reference_bus_compatibility(
            _case(devices=[_device(), _device(id="LCL-09", min_operating_voltage_v=23.0)])
        )
        self.assertEqual(result["verdict"], DEVICE_OUTSIDE_BUS_ENVELOPE)
        self.assertEqual(result["incompatible_devices"], ("LCL-09",))
        self.assertEqual(len(result["findings"]), 1)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_reference_bus_compatibility(["bus_specification"])

    def test_a_missing_device_list_is_refused(self):
        case = _case()
        del case["devices"]
        with self.assertRaises(ValueError):
            assess_reference_bus_compatibility(case)


if __name__ == "__main__":
    unittest.main()
