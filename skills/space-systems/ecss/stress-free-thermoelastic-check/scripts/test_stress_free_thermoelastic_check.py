"""
Gate 3 contract tests for stress_free_thermoelastic_check_logic.

Run: python3 test_stress_free_thermoelastic_check.py
Expected output: OK (all tests pass, no network, no external dependencies).
"""

import unittest

from stress_free_thermoelastic_check_logic import (
    CheckStatus,
    ElementData,
    NodeDisplacement,
    check_element_stress,
    check_temperature_uniformity,
    check_displacement_residual,
    compute_stress_tolerance,
    run_thermoelastic_check,
)

# Representative material: aluminium-alloy-like
E_AL = 70.0e9      # Young's modulus [Pa]
ALPHA_AL = 23.0e-6 # CTE [1/°C]
DT = 100.0         # temperature change [°C]
FRACTION = 1e-6


def _al_element(eid, sx=0.0, sy=0.0, sz=0.0, dt=DT):
    return ElementData(
        element_id=eid,
        youngs_modulus=E_AL,
        cte=ALPHA_AL,
        delta_T=dt,
        stress_xx=sx,
        stress_yy=sy,
        stress_zz=sz,
    )


class TestComputeStressTolerance(unittest.TestCase):

    def test_nominal_tolerance(self):
        # E * alpha * |DT| * fraction = 70e9 * 23e-6 * 100 * 1e-6 = 161 Pa
        tol = compute_stress_tolerance(E_AL, ALPHA_AL, DT, FRACTION)
        self.assertAlmostEqual(tol, 70e9 * 23e-6 * 100 * 1e-6, places=3)

    def test_zero_delta_T_returns_floor(self):
        # When DT=0 tolerance falls back to fraction * E
        tol = compute_stress_tolerance(E_AL, ALPHA_AL, 0.0, FRACTION)
        self.assertAlmostEqual(tol, FRACTION * E_AL, places=3)

    def test_negative_cte_raises(self):
        with self.assertRaises(ValueError):
            compute_stress_tolerance(E_AL, -1e-6, DT, FRACTION)

    def test_zero_modulus_raises(self):
        with self.assertRaises(ValueError):
            compute_stress_tolerance(0.0, ALPHA_AL, DT, FRACTION)

    def test_negative_modulus_raises(self):
        with self.assertRaises(ValueError):
            compute_stress_tolerance(-E_AL, ALPHA_AL, DT, FRACTION)

    def test_zero_fraction_raises(self):
        with self.assertRaises(ValueError):
            compute_stress_tolerance(E_AL, ALPHA_AL, DT, 0.0)


class TestCheckElementStress(unittest.TestCase):

    def test_zero_stress_passes(self):
        elem = _al_element(1, sx=0.0, sy=0.0, sz=0.0)
        result = check_element_stress(elem, FRACTION)
        self.assertEqual(result.status, CheckStatus.PASS)
        self.assertEqual(result.element_id, 1)

    def test_small_stress_passes(self):
        # 1 Pa is well below the ~161 Pa tolerance for aluminium at DT=100
        elem = _al_element(2, sx=1.0, sy=0.5, sz=0.2)
        result = check_element_stress(elem, FRACTION)
        self.assertEqual(result.status, CheckStatus.PASS)
        self.assertLessEqual(result.ratio, 1.0)

    def test_high_stress_fails(self):
        # 1e6 Pa (1 MPa) far exceeds the ~161 Pa tolerance
        elem = _al_element(3, sx=1.0e6, sy=0.0, sz=0.0)
        result = check_element_stress(elem, FRACTION)
        self.assertEqual(result.status, CheckStatus.FAIL)
        self.assertGreater(result.ratio, 1.0)

    def test_stress_exactly_at_tolerance_passes(self):
        tol = compute_stress_tolerance(E_AL, ALPHA_AL, DT, FRACTION)
        elem = _al_element(4, sx=tol, sy=0.0, sz=0.0)
        result = check_element_stress(elem, FRACTION)
        self.assertEqual(result.status, CheckStatus.PASS)
        self.assertAlmostEqual(result.ratio, 1.0, places=9)

    def test_stress_just_above_tolerance_fails(self):
        tol = compute_stress_tolerance(E_AL, ALPHA_AL, DT, FRACTION)
        elem = _al_element(5, sx=tol * 1.001, sy=0.0, sz=0.0)
        result = check_element_stress(elem, FRACTION)
        self.assertEqual(result.status, CheckStatus.FAIL)

    def test_invalid_modulus_raises(self):
        elem = _al_element(6)
        elem.youngs_modulus = 0.0
        with self.assertRaises(ValueError):
            check_element_stress(elem, FRACTION)

    def test_negative_cte_raises(self):
        elem = _al_element(7)
        elem.cte = -1e-6
        with self.assertRaises(ValueError):
            check_element_stress(elem, FRACTION)


class TestCheckTemperatureUniformity(unittest.TestCase):

    def test_uniform_temperatures_pass(self):
        temps = {1: 120.0, 2: 120.0, 3: 120.001, 4: 119.999}
        result = check_temperature_uniformity(temps, tolerance=0.01)
        self.assertEqual(result.status, CheckStatus.PASS)
        self.assertTrue(result.uniform)

    def test_non_uniform_temperatures_fail(self):
        temps = {1: 100.0, 2: 150.0, 3: 120.0}
        result = check_temperature_uniformity(temps, tolerance=0.01)
        self.assertEqual(result.status, CheckStatus.FAIL)
        self.assertFalse(result.uniform)
        self.assertAlmostEqual(result.spread, 50.0)

    def test_single_element_passes(self):
        temps = {1: 100.0}
        result = check_temperature_uniformity(temps, tolerance=0.01)
        self.assertEqual(result.status, CheckStatus.PASS)
        self.assertEqual(result.spread, 0.0)

    def test_empty_map_raises(self):
        with self.assertRaises(ValueError):
            check_temperature_uniformity({}, tolerance=0.01)

    def test_spread_exactly_at_tolerance_passes(self):
        temps = {1: 100.0, 2: 100.01}
        result = check_temperature_uniformity(temps, tolerance=0.01)
        self.assertEqual(result.status, CheckStatus.PASS)


class TestCheckDisplacementResidual(unittest.TestCase):

    def test_zero_residual_passes(self):
        node = NodeDisplacement(1, 1e-4, 2e-4, 3e-4,
                                expected_dx=1e-4, expected_dy=2e-4, expected_dz=3e-4)
        result = check_displacement_residual(node, tolerance=1e-6)
        self.assertEqual(result.status, CheckStatus.PASS)
        self.assertAlmostEqual(result.residual, 0.0)

    def test_small_residual_passes(self):
        node = NodeDisplacement(2, 1e-4 + 1e-9, 2e-4, 3e-4,
                                expected_dx=1e-4, expected_dy=2e-4, expected_dz=3e-4)
        result = check_displacement_residual(node, tolerance=1e-6)
        self.assertEqual(result.status, CheckStatus.PASS)

    def test_large_residual_fails(self):
        node = NodeDisplacement(3, 1e-4 + 1e-3, 2e-4, 3e-4,
                                expected_dx=1e-4, expected_dy=2e-4, expected_dz=3e-4)
        result = check_displacement_residual(node, tolerance=1e-6)
        self.assertEqual(result.status, CheckStatus.FAIL)
        self.assertGreater(result.residual, 1e-6)

    def test_residual_exactly_at_tolerance_passes(self):
        tol = 1e-6
        node = NodeDisplacement(4, tol, 0.0, 0.0,
                                expected_dx=0.0, expected_dy=0.0, expected_dz=0.0)
        result = check_displacement_residual(node, tolerance=tol)
        self.assertEqual(result.status, CheckStatus.PASS)


class TestRunThermoelasticCheck(unittest.TestCase):

    def _make_passing_inputs(self):
        elements = [_al_element(i, sx=0.0, sy=0.0, sz=0.0) for i in range(1, 4)]
        nodes = [
            NodeDisplacement(i, i * 1e-4, 0.0, 0.0,
                             expected_dx=i * 1e-4)
            for i in range(1, 4)
        ]
        temps = {1: 100.0, 2: 100.002, 3: 100.005}
        return elements, nodes, temps

    def test_full_check_passes_on_good_model(self):
        elements, nodes, temps = self._make_passing_inputs()
        summary = run_thermoelastic_check(
            elements, nodes, temps,
            stress_fraction=FRACTION,
            displacement_tolerance=1e-6,
            temperature_tolerance=0.01,
        )
        self.assertEqual(summary.overall, CheckStatus.PASS)
        self.assertEqual(summary.n_elements_failed, 0)
        self.assertEqual(summary.n_nodes_failed, 0)

    def test_full_check_fails_on_high_element_stress(self):
        elements = [
            _al_element(1, sx=0.0),
            _al_element(2, sx=5.0e6),   # 5 MPa — far above tolerance
            _al_element(3, sx=0.0),
        ]
        nodes = [
            NodeDisplacement(1, 1e-4, 0.0, 0.0, expected_dx=1e-4),
        ]
        temps = {1: 100.0, 2: 100.0, 3: 100.0}
        summary = run_thermoelastic_check(
            elements, nodes, temps,
            stress_fraction=FRACTION,
        )
        self.assertEqual(summary.overall, CheckStatus.FAIL)
        self.assertEqual(summary.n_elements_failed, 1)
        self.assertEqual(summary.failed_elements[0].element_id, 2)

    def test_full_check_fails_on_non_uniform_temperature(self):
        elements = [_al_element(1, sx=0.0)]
        nodes = [NodeDisplacement(1, 1e-4, 0.0, 0.0, expected_dx=1e-4)]
        temps = {1: 100.0, 2: 200.0}   # 100 °C spread — fails uniformity
        summary = run_thermoelastic_check(
            elements, nodes, temps,
            temperature_tolerance=0.01,
        )
        self.assertEqual(summary.overall, CheckStatus.FAIL)
        self.assertEqual(summary.temperature_result.status, CheckStatus.FAIL)

    def test_full_check_fails_on_bad_displacement(self):
        elements = [_al_element(1, sx=0.0)]
        nodes = [
            NodeDisplacement(1, 1e-4 + 1e-3, 0.0, 0.0, expected_dx=1e-4)
        ]
        temps = {1: 100.0}
        summary = run_thermoelastic_check(
            elements, nodes, temps,
            displacement_tolerance=1e-6,
        )
        self.assertEqual(summary.overall, CheckStatus.FAIL)
        self.assertEqual(summary.n_nodes_failed, 1)

    def test_empty_elements_raises(self):
        nodes = [NodeDisplacement(1, 0.0, 0.0, 0.0)]
        with self.assertRaises(ValueError):
            run_thermoelastic_check([], nodes, {1: 100.0})

    def test_empty_nodes_raises(self):
        elements = [_al_element(1)]
        with self.assertRaises(ValueError):
            run_thermoelastic_check(elements, [], {1: 100.0})

    def test_summary_counts_are_correct(self):
        elements, nodes, temps = self._make_passing_inputs()
        summary = run_thermoelastic_check(elements, nodes, temps)
        self.assertEqual(summary.n_elements_checked, 3)
        self.assertEqual(summary.n_nodes_checked, 3)


if __name__ == "__main__":
    unittest.main()
