"""Contract tests for the clause 4.3.3 and 4.3.4 interface requirements logic."""

import unittest

from e31_electrical_aocs_interface_requirements_logic import (
    POWER_TOLERANCE_W,
    SPEED_OF_LIGHT_M_PER_S,
    STEFAN_BOLTZMANN_W_PER_M2K4,
    TORQUE_TOLERANCE_NM,
    assess_electrical_aocs_interfaces,
    dissipation_by_mode,
    evaluate_circuit,
    heater_circuit_current_a,
    heater_circuit_power_w,
    orbit_average_demand_w,
    peak_demand_w,
    radiator_disturbance_torque_nm,
    radiator_recoil_force_n,
    switch_current_headroom,
    total_disturbance_torque_nm,
    validate_bus_range,
    validate_positive,
)

BUS = (26.0, 29.0)


def circuit(**overrides):
    """Return a representative prime heater circuit record."""
    record = {
        "name": "propellant-line-heater-a",
        "resistance_ohm": 120.0,
        "duty_cycle": 0.35,
        "switch_rating_a": 0.5,
        "branch": "prime",
    }
    record.update(overrides)
    return record


def surface(**overrides):
    """Return a representative offset radiating surface record."""
    record = {
        "area_m2": 1.2,
        "emissivity": 0.85,
        "temperature_k": 290.0,
        "moment_arm_m": 0.9,
    }
    record.update(overrides)
    return record


class ValidationTests(unittest.TestCase):
    def test_positive_returns_float(self):
        self.assertEqual(validate_positive("x", 7), 7.0)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", False)

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", float("inf"))

    def test_bus_range_returns_pair(self):
        self.assertEqual(validate_bus_range(26, 29), (26.0, 29.0))

    def test_inverted_bus_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_bus_range(29.0, 26.0)

    def test_zero_bus_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_bus_range(0.0, 29.0)


class CircuitElectricalTests(unittest.TestCase):
    def test_power_is_voltage_squared_over_resistance(self):
        self.assertAlmostEqual(heater_circuit_power_w(100.0, 30.0), 9.0, places=12)

    def test_current_is_voltage_over_resistance(self):
        self.assertAlmostEqual(heater_circuit_current_a(100.0, 30.0), 0.3, places=12)

    def test_power_grows_as_the_square_of_bus_voltage(self):
        low = heater_circuit_power_w(120.0, 26.0)
        high = heater_circuit_power_w(120.0, 52.0)
        self.assertAlmostEqual(high / low, 4.0, places=12)

    def test_zero_resistance_rejected(self):
        with self.assertRaises(ValueError):
            heater_circuit_power_w(0.0, 28.0)

    def test_negative_voltage_rejected(self):
        with self.assertRaises(ValueError):
            heater_circuit_current_a(120.0, -28.0)


class SwitchHeadroomTests(unittest.TestCase):
    def test_headroom_is_positive_below_the_derated_rating(self):
        self.assertAlmostEqual(
            switch_current_headroom(0.2, 0.5, 0.8), (0.4 - 0.2) / 0.4, places=12
        )

    def test_headroom_is_zero_exactly_at_the_derated_rating(self):
        self.assertAlmostEqual(switch_current_headroom(0.4, 0.5, 0.8), 0.0, places=12)

    def test_headroom_is_negative_above_the_derated_rating(self):
        self.assertLess(switch_current_headroom(0.6, 0.5, 0.8), 0.0)

    def test_derating_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            switch_current_headroom(0.2, 0.5, 1.2)


class EvaluateCircuitTests(unittest.TestCase):
    def test_sizes_the_circuit_at_the_top_of_the_bus(self):
        record = evaluate_circuit(circuit(), BUS)
        self.assertAlmostEqual(
            record["power_at_max_bus_w"], 29.0 * 29.0 / 120.0, places=12
        )

    def test_min_bus_power_is_lower(self):
        record = evaluate_circuit(circuit(), BUS)
        self.assertLess(record["power_at_min_bus_w"], record["power_at_max_bus_w"])

    def test_redundant_branch_is_recorded(self):
        record = evaluate_circuit(circuit(branch="redundant"), BUS)
        self.assertEqual(record["branch"], "redundant")

    def test_unknown_branch_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_circuit(circuit(branch="spare"), BUS)

    def test_duty_cycle_above_one_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_circuit(circuit(duty_cycle=1.4), BUS)

    def test_zero_duty_cycle_allowed(self):
        record = evaluate_circuit(circuit(duty_cycle=0.0), BUS)
        self.assertAlmostEqual(record["duty_cycle"], 0.0, places=12)

    def test_missing_key_rejected(self):
        bad = circuit()
        del bad["switch_rating_a"]
        with self.assertRaises(ValueError):
            evaluate_circuit(bad, BUS)

    def test_undersized_switch_is_not_compliant(self):
        record = evaluate_circuit(circuit(switch_rating_a=0.2), BUS)
        self.assertFalse(record["switch_compliant"])


class DemandTests(unittest.TestCase):
    def _records(self):
        return [
            evaluate_circuit(circuit(), BUS),
            evaluate_circuit(
                circuit(name="propellant-line-heater-b", branch="redundant"), BUS
            ),
            evaluate_circuit(
                circuit(name="battery-heater", resistance_ohm=60.0,
                        duty_cycle=0.5, switch_rating_a=1.0), BUS
            ),
        ]

    def test_peak_skips_the_redundant_branch_by_default(self):
        records = self._records()
        expected = (29.0 * 29.0 / 120.0) + (29.0 * 29.0 / 60.0)
        self.assertAlmostEqual(peak_demand_w(records), expected, places=12)

    def test_peak_counts_both_branches_when_credible(self):
        records = self._records()
        with_both = peak_demand_w(records, both_branches_credible=True)
        without = peak_demand_w(records)
        self.assertAlmostEqual(
            with_both - without, 29.0 * 29.0 / 120.0, places=12
        )

    def test_average_is_duty_weighted(self):
        records = self._records()
        expected = (29.0 * 29.0 / 120.0) * 0.35 + (29.0 * 29.0 / 60.0) * 0.5
        self.assertAlmostEqual(orbit_average_demand_w(records), expected, places=12)

    def test_average_never_exceeds_peak(self):
        records = self._records()
        self.assertLess(orbit_average_demand_w(records), peak_demand_w(records))

    def test_empty_record_set_rejected(self):
        with self.assertRaises(ValueError):
            peak_demand_w([])

    def test_malformed_record_rejected(self):
        with self.assertRaises(ValueError):
            orbit_average_demand_w([{"name": "x"}])


class DissipationDataTests(unittest.TestCase):
    def test_every_declared_mode_is_returned(self):
        table = dissipation_by_mode(
            ["safe", "nominal"], {"safe": 120.0, "nominal": 340.0}
        )
        self.assertEqual(sorted(table), ["nominal", "safe"])

    def test_zero_dissipation_mode_allowed(self):
        table = dissipation_by_mode(["off"], {"off": 0.0})
        self.assertAlmostEqual(table["off"], 0.0, places=12)

    def test_missing_mode_is_unknown_not_zero(self):
        with self.assertRaises(ValueError):
            dissipation_by_mode(["safe", "nominal"], {"safe": 120.0})

    def test_extra_mode_in_the_map_rejected(self):
        with self.assertRaises(ValueError):
            dissipation_by_mode(["safe"], {"safe": 120.0, "science": 500.0})

    def test_empty_mode_list_rejected(self):
        with self.assertRaises(ValueError):
            dissipation_by_mode([], {})

    def test_negative_dissipation_rejected(self):
        with self.assertRaises(ValueError):
            dissipation_by_mode(["safe"], {"safe": -5.0})


class DisturbanceTorqueTests(unittest.TestCase):
    def test_recoil_force_matches_the_radiated_power_over_c(self):
        force = radiator_recoil_force_n(1.0, 1.0, 300.0)
        radiated = STEFAN_BOLTZMANN_W_PER_M2K4 * 300.0 ** 4
        self.assertAlmostEqual(force, radiated / SPEED_OF_LIGHT_M_PER_S, places=18)

    def test_force_scales_with_the_fourth_power_of_temperature(self):
        cold = radiator_recoil_force_n(1.0, 0.9, 150.0)
        hot = radiator_recoil_force_n(1.0, 0.9, 300.0)
        self.assertAlmostEqual(hot / cold, 16.0, places=9)

    def test_torque_is_force_times_moment_arm(self):
        force = radiator_recoil_force_n(1.2, 0.85, 290.0)
        torque = radiator_disturbance_torque_nm(1.2, 0.85, 290.0, 0.9)
        self.assertAlmostEqual(torque, force * 0.9, places=18)

    def test_centred_radiator_contributes_no_torque(self):
        self.assertAlmostEqual(
            radiator_disturbance_torque_nm(1.2, 0.85, 290.0, 0.0), 0.0, places=18
        )

    def test_emissivity_above_one_rejected(self):
        with self.assertRaises(ValueError):
            radiator_recoil_force_n(1.0, 1.4, 290.0)

    def test_total_sums_the_surfaces(self):
        total = total_disturbance_torque_nm([surface(), surface(moment_arm_m=0.3)])
        single = radiator_disturbance_torque_nm(1.2, 0.85, 290.0, 0.9)
        other = radiator_disturbance_torque_nm(1.2, 0.85, 290.0, 0.3)
        self.assertAlmostEqual(total, single + other, places=18)

    def test_surface_missing_a_key_rejected(self):
        bad = surface()
        del bad["emissivity"]
        with self.assertRaises(ValueError):
            total_disturbance_torque_nm([bad])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "circuits": [
                circuit(),
                circuit(name="propellant-line-heater-b", branch="redundant"),
                circuit(name="battery-heater", resistance_ohm=60.0,
                        duty_cycle=0.5, switch_rating_a=1.0),
            ],
            "bus_range": BUS,
            "peak_allocation_w": 40.0,
            "average_allocation_w": 20.0,
            "modes": ["safe", "nominal"],
            "dissipation_w_by_mode": {"safe": 120.0, "nominal": 340.0},
            "surfaces": [surface()],
            "torque_allocation_nm": 5.0e-6,
        }
        spec.update(overrides)
        return spec

    def test_nominal_case_is_compliant(self):
        result = assess_electrical_aocs_interfaces(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_peak_overrun_raises_a_finding(self):
        result = assess_electrical_aocs_interfaces(self._spec(peak_allocation_w=10.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("peak heater demand" in f for f in result["findings"]))

    def test_average_overrun_raises_a_finding(self):
        result = assess_electrical_aocs_interfaces(
            self._spec(average_allocation_w=1.0)
        )
        self.assertTrue(any("orbit-average" in f for f in result["findings"]))

    def test_torque_overrun_raises_a_finding(self):
        result = assess_electrical_aocs_interfaces(
            self._spec(torque_allocation_nm=1.0e-12)
        )
        self.assertTrue(any("disturbance torque" in f for f in result["findings"]))

    def test_both_branches_credible_raises_the_peak(self):
        base = assess_electrical_aocs_interfaces(self._spec())
        both = assess_electrical_aocs_interfaces(
            self._spec(both_branches_credible=True)
        )
        self.assertGreater(both["peak_demand_w"], base["peak_demand_w"])

    def test_undersized_switch_reaches_the_findings(self):
        spec = self._spec()
        spec["circuits"][0]["switch_rating_a"] = 0.1
        result = assess_electrical_aocs_interfaces(spec)
        self.assertTrue(any("headroom" in f for f in result["findings"]))

    def test_mode_gap_is_refused_rather_than_reported(self):
        spec = self._spec(dissipation_w_by_mode={"safe": 120.0})
        with self.assertRaises(ValueError):
            assess_electrical_aocs_interfaces(spec)

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["torque_allocation_nm"]
        with self.assertRaises(ValueError):
            assess_electrical_aocs_interfaces(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_electrical_aocs_interfaces([1, 2, 3])

    def test_malformed_bus_range_rejected(self):
        with self.assertRaises(ValueError):
            assess_electrical_aocs_interfaces(self._spec(bus_range=(28.0,)))

    def test_tolerances_are_rounding_allowances(self):
        self.assertLess(POWER_TOLERANCE_W, 1e-6)
        self.assertLess(TORQUE_TOLERANCE_NM, 1e-12)


if __name__ == "__main__":
    unittest.main()
