"""
Gate 3 contract tests for stress_spectrum_derivation_logic.
Run: python3 test_stress_spectrum_derivation.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from stress_spectrum_derivation_logic import (
    aggregate_spectrum,
    compute_principal_stresses,
    compute_stress,
    compute_von_mises,
    derive_stress_spectrum,
    extract_turning_points,
    find_critical_location,
    goodman_equivalent_amplitude,
    rainflow_count,
    validate_spectrum,
)


class TestComputeStress(unittest.TestCase):

    def test_basic_tension(self):
        # 1000 N over 0.001 m² => 1 MPa
        result = compute_stress(1000.0, 0.001)
        self.assertAlmostEqual(result, 1_000_000.0, places=3)

    def test_stress_with_concentration_factor(self):
        # Kt=2.5 doubles the nominal stress
        result = compute_stress(100.0, 0.01, stress_concentration=2.5)
        self.assertAlmostEqual(result, 25_000.0, places=6)

    def test_compression_load(self):
        result = compute_stress(-500.0, 0.005)
        self.assertAlmostEqual(result, -100_000.0, places=6)

    def test_invalid_zero_area(self):
        with self.assertRaises(ValueError):
            compute_stress(100.0, 0.0)

    def test_invalid_negative_area(self):
        with self.assertRaises(ValueError):
            compute_stress(100.0, -0.001)

    def test_invalid_kt_below_one(self):
        with self.assertRaises(ValueError):
            compute_stress(100.0, 0.01, stress_concentration=0.9)

    def test_kt_exactly_one_passes(self):
        result = compute_stress(200.0, 0.002, stress_concentration=1.0)
        self.assertAlmostEqual(result, 100_000.0, places=6)


class TestPrincipalStressAndVonMises(unittest.TestCase):

    def test_uniaxial_state(self):
        # sigma_x only, no shear => principal stresses are sigma_x and 0
        s1, s2 = compute_principal_stresses(50.0, 0.0, 0.0)
        self.assertAlmostEqual(max(s1, s2), 50.0, places=9)
        self.assertAlmostEqual(min(s1, s2), 0.0, places=9)

    def test_equibiaxial_no_shear(self):
        s1, s2 = compute_principal_stresses(100.0, 100.0, 0.0)
        self.assertAlmostEqual(s1, 100.0, places=9)
        self.assertAlmostEqual(s2, 100.0, places=9)

    def test_von_mises_uniaxial(self):
        vm = compute_von_mises(100.0, 0.0)
        self.assertAlmostEqual(vm, 100.0, places=9)

    def test_von_mises_equibiaxial(self):
        vm = compute_von_mises(100.0, 100.0)
        self.assertAlmostEqual(vm, 100.0, places=9)


class TestFindCriticalLocation(unittest.TestCase):

    def test_selects_highest_magnitude(self):
        locs = [
            {"id": "A", "peak_stress_Pa": 200e6},
            {"id": "B", "peak_stress_Pa": 350e6},
            {"id": "C", "peak_stress_Pa": 150e6},
        ]
        crit = find_critical_location(locs)
        self.assertEqual(crit["id"], "B")

    def test_negative_stress_highest_magnitude(self):
        locs = [
            {"id": "A", "peak_stress_Pa": 200e6},
            {"id": "B", "peak_stress_Pa": -400e6},
        ]
        crit = find_critical_location(locs)
        self.assertEqual(crit["id"], "B")

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            find_critical_location([])

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            find_critical_location([{"peak_stress_Pa": 100.0}])

    def test_missing_peak_stress_raises(self):
        with self.assertRaises(ValueError):
            find_critical_location([{"id": "A"}])


class TestExtractTurningPoints(unittest.TestCase):

    def test_monotone_increasing(self):
        pts = extract_turning_points([1.0, 2.0, 3.0, 4.0])
        self.assertEqual(pts[0], 1.0)
        self.assertEqual(pts[-1], 4.0)

    def test_single_peak(self):
        pts = extract_turning_points([0.0, 10.0, 0.0])
        self.assertIn(10.0, pts)

    def test_preserves_endpoints(self):
        history = [5.0, 3.0, 8.0, 2.0, 7.0]
        pts = extract_turning_points(history)
        self.assertEqual(pts[0], 5.0)
        self.assertEqual(pts[-1], 7.0)

    def test_short_history(self):
        pts = extract_turning_points([3.0, 7.0])
        self.assertEqual(pts, [3.0, 7.0])


class TestRainflowCount(unittest.TestCase):

    def test_single_full_cycle(self):
        # Simple 0→10→0→10→0 sequence should yield at least one cycle
        history = [0.0, 10.0, 0.0, 10.0, 0.0]
        cycles = rainflow_count(history)
        self.assertGreater(len(cycles), 0)
        amplitudes = [c[0] for c in cycles]
        self.assertTrue(any(abs(a - 5.0) < 1e-9 for a in amplitudes))

    def test_constant_history_no_cycles(self):
        cycles = rainflow_count([5.0, 5.0, 5.0])
        total_count = sum(c[2] for c in cycles)
        self.assertAlmostEqual(total_count, 0.0, places=9)

    def test_counts_are_positive(self):
        history = [0.0, 8.0, 2.0, 10.0, 4.0, 6.0, 0.0]
        cycles = rainflow_count(history)
        for amp, mean, cnt in cycles:
            self.assertGreater(cnt, 0.0)

    def test_amplitudes_non_negative(self):
        history = [0.0, 5.0, -5.0, 3.0, -3.0, 0.0]
        cycles = rainflow_count(history)
        for amp, mean, cnt in cycles:
            self.assertGreaterEqual(amp, 0.0)

    def test_too_short_returns_empty(self):
        cycles = rainflow_count([10.0])
        self.assertEqual(cycles, [])


class TestGoodmanCorrection(unittest.TestCase):

    def test_zero_mean_unchanged(self):
        eq = goodman_equivalent_amplitude(100.0, 0.0, 500.0)
        self.assertAlmostEqual(eq, 100.0, places=9)

    def test_tensile_mean_increases_equivalent(self):
        eq = goodman_equivalent_amplitude(100.0, 250.0, 500.0)
        self.assertAlmostEqual(eq, 200.0, places=9)  # 100 / (1 - 250/500) = 200

    def test_compressive_mean_decreases_equivalent(self):
        eq = goodman_equivalent_amplitude(100.0, -250.0, 500.0)
        self.assertAlmostEqual(eq, 200.0 / 3.0, places=6)  # 100 / (1 + 0.5) = 66.67

    def test_mean_equals_ultimate_raises(self):
        with self.assertRaises(ValueError):
            goodman_equivalent_amplitude(50.0, 500.0, 500.0)

    def test_mean_exceeds_ultimate_raises(self):
        with self.assertRaises(ValueError):
            goodman_equivalent_amplitude(50.0, 600.0, 500.0)

    def test_zero_ultimate_raises(self):
        with self.assertRaises(ValueError):
            goodman_equivalent_amplitude(50.0, 10.0, 0.0)


class TestAggregateSpectrum(unittest.TestCase):

    def test_sorted_descending(self):
        raw = [(2.0, 0.0, 1.0), (5.0, 0.0, 1.0), (1.0, 0.0, 1.0)]
        spec = aggregate_spectrum(raw)
        amplitudes = [t[0] for t in spec]
        self.assertEqual(amplitudes, sorted(amplitudes, reverse=True))

    def test_counts_summed(self):
        raw = [(3.0, 0.0, 0.5), (3.0, 0.0, 0.5)]
        spec = aggregate_spectrum(raw)
        self.assertEqual(len(spec), 1)
        self.assertAlmostEqual(spec[0][2], 1.0, places=9)


class TestValidateSpectrum(unittest.TestCase):

    def test_empty_spectrum_produces_finding(self):
        findings = validate_spectrum([])
        self.assertGreater(len(findings), 0)

    def test_valid_spectrum_no_findings(self):
        spec = [(100.0, 0.0, 1.0), (50.0, 10.0, 2.0)]
        findings = validate_spectrum(spec)
        self.assertEqual(findings, [])

    def test_negative_amplitude_flagged(self):
        spec = [(-10.0, 0.0, 1.0)]
        findings = validate_spectrum(spec)
        self.assertTrue(any("negative" in f.lower() for f in findings))


class TestDeriveStressSpectrum(unittest.TestCase):

    def _load_events(self):
        return [
            {"id": "L1", "load_N": 0.0},
            {"id": "L2", "load_N": 10000.0},
            {"id": "L3", "load_N": 2000.0},
            {"id": "L4", "load_N": 12000.0},
            {"id": "L5", "load_N": 4000.0},
            {"id": "L6", "load_N": 0.0},
        ]

    def test_stress_history_length(self):
        events = self._load_events()
        result = derive_stress_spectrum(events, section_area_m2=0.001)
        self.assertEqual(len(result["stress_history"]), len(events))

    def test_stress_values_scale_with_area(self):
        events = [{"id": "L1", "load_N": 1000.0}, {"id": "L2", "load_N": -1000.0}]
        r1 = derive_stress_spectrum(events, section_area_m2=0.001)
        r2 = derive_stress_spectrum(events, section_area_m2=0.002)
        s1 = r1["stress_history"][0][1]
        s2 = r2["stress_history"][0][1]
        self.assertAlmostEqual(s1 / s2, 2.0, places=9)

    def test_spectrum_contains_cycles(self):
        result = derive_stress_spectrum(self._load_events(), section_area_m2=0.001)
        self.assertGreater(len(result["spectrum"]), 0)

    def test_goodman_spectrum_present_when_ultimate_given(self):
        result = derive_stress_spectrum(
            self._load_events(),
            section_area_m2=0.001,
            ultimate_stress_Pa=500e6,
        )
        self.assertIn("goodman_spectrum", result)

    def test_goodman_spectrum_absent_without_ultimate(self):
        result = derive_stress_spectrum(self._load_events(), section_area_m2=0.001)
        self.assertNotIn("goodman_spectrum", result)

    def test_empty_events_raises(self):
        with self.assertRaises(ValueError):
            derive_stress_spectrum([], section_area_m2=0.001)

    def test_missing_load_key_raises(self):
        events = [{"id": "L1"}]
        with self.assertRaises(ValueError):
            derive_stress_spectrum(events, section_area_m2=0.001)

    def test_zero_area_raises(self):
        events = [{"id": "L1", "load_N": 1000.0}]
        with self.assertRaises(ValueError):
            derive_stress_spectrum(events, section_area_m2=0.0)

    def test_kt_applied_to_stress_history(self):
        events = [{"id": "L1", "load_N": 1000.0}, {"id": "L2", "load_N": 0.0}]
        r_no_kt = derive_stress_spectrum(events, section_area_m2=0.001, stress_concentration=1.0)
        r_kt2 = derive_stress_spectrum(events, section_area_m2=0.001, stress_concentration=2.0)
        s_no_kt = r_no_kt["stress_history"][0][1]
        s_kt2 = r_kt2["stress_history"][0][1]
        self.assertAlmostEqual(s_kt2 / s_no_kt, 2.0, places=9)

    def test_findings_returned(self):
        result = derive_stress_spectrum(self._load_events(), section_area_m2=0.001)
        self.assertIn("findings", result)
        self.assertIsInstance(result["findings"], list)


if __name__ == "__main__":
    unittest.main()
