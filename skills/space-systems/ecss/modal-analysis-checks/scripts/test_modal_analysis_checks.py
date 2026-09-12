"""
Offline deterministic unit tests for modal_analysis_checks_logic.py.
Run: python3 test_modal_analysis_checks.py
Expected output: OK
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from modal_analysis_checks_logic import (
    Mode,
    FrequencyRequirement,
    ModalCheckConfig,
    identify_rigid_body_modes,
    identify_elastic_modes,
    check_rigid_body_mode_count,
    check_rigid_body_frequencies,
    compute_cumulative_effective_mass_fractions,
    check_effective_mass_fraction,
    check_minimum_frequency,
    run_all_checks,
    summarize,
)


def _rb_mode(n: int, freq: float = 0.001) -> Mode:
    """Helper: a near-zero frequency rigid-body mode with negligible effective mass."""
    return Mode(
        mode_number=n,
        frequency_hz=freq,
        eff_mass_x=0.0, eff_mass_y=0.0, eff_mass_z=0.0,
        eff_mass_rx=0.0, eff_mass_ry=0.0, eff_mass_rz=0.0,
    )


def _elastic_mode(n: int, freq: float, mx: float = 0.0, my: float = 0.0,
                  mz: float = 0.0, mrx: float = 0.0, mry: float = 0.0,
                  mrz: float = 0.0) -> Mode:
    return Mode(
        mode_number=n, frequency_hz=freq,
        eff_mass_x=mx, eff_mass_y=my, eff_mass_z=mz,
        eff_mass_rx=mrx, eff_mass_ry=mry, eff_mass_rz=mrz,
    )


def _six_rb_modes() -> list:
    return [_rb_mode(i + 1) for i in range(6)]


TOTAL_MASS = 100.0
THRESHOLD_HZ = 0.01
EMF_THRESHOLD = 0.90


class TestIdentifyModes(unittest.TestCase):

    def test_identify_rigid_body_modes_returns_low_freq(self):
        modes = _six_rb_modes() + [_elastic_mode(7, 10.0)]
        rb = identify_rigid_body_modes(modes, THRESHOLD_HZ)
        self.assertEqual(len(rb), 6)
        for m in rb:
            self.assertLess(m.frequency_hz, THRESHOLD_HZ)

    def test_identify_elastic_modes_returns_high_freq(self):
        modes = _six_rb_modes() + [_elastic_mode(7, 10.0), _elastic_mode(8, 25.0)]
        elastic = identify_elastic_modes(modes, THRESHOLD_HZ)
        self.assertEqual(len(elastic), 2)
        for m in elastic:
            self.assertGreaterEqual(m.frequency_hz, THRESHOLD_HZ)

    def test_invalid_threshold_raises(self):
        with self.assertRaises(ValueError):
            identify_rigid_body_modes([], -1.0)
        with self.assertRaises(ValueError):
            identify_elastic_modes([], 0.0)


class TestRigidBodyCount(unittest.TestCase):

    def test_exactly_six_rigid_body_modes_passes(self):
        modes = _six_rb_modes() + [_elastic_mode(7, 15.0)]
        result = check_rigid_body_mode_count(modes, THRESHOLD_HZ)
        self.assertTrue(result.passed)
        self.assertEqual(result.value, 6.0)

    def test_fewer_than_six_fails(self):
        modes = [_rb_mode(i + 1) for i in range(4)] + [_elastic_mode(5, 10.0)]
        result = check_rigid_body_mode_count(modes, THRESHOLD_HZ)
        self.assertFalse(result.passed)

    def test_more_than_six_fails(self):
        modes = [_rb_mode(i + 1) for i in range(7)] + [_elastic_mode(8, 10.0)]
        result = check_rigid_body_mode_count(modes, THRESHOLD_HZ)
        self.assertFalse(result.passed)

    def test_custom_expected_count(self):
        modes = [_rb_mode(i + 1) for i in range(3)] + [_elastic_mode(4, 5.0)]
        result = check_rigid_body_mode_count(modes, THRESHOLD_HZ, expected_count=3)
        self.assertTrue(result.passed)


class TestRigidBodyFrequencies(unittest.TestCase):

    def test_all_rb_frequencies_below_threshold(self):
        modes = _six_rb_modes() + [_elastic_mode(7, 12.0)]
        results = check_rigid_body_frequencies(modes, THRESHOLD_HZ)
        self.assertEqual(len(results), 6)
        for r in results:
            self.assertTrue(r.passed)

    def test_no_rigid_body_modes_returns_empty(self):
        modes = [_elastic_mode(1, 5.0), _elastic_mode(2, 12.0)]
        results = check_rigid_body_frequencies(modes, THRESHOLD_HZ)
        self.assertEqual(len(results), 0)


class TestCumulativeEffectiveMassFraction(unittest.TestCase):

    def setUp(self):
        self.modes = _six_rb_modes() + [
            _elastic_mode(7,  10.0, mx=50.0, my=0.0,  mz=30.0),
            _elastic_mode(8,  20.0, mx=30.0, my=60.0, mz=10.0),
            _elastic_mode(9,  35.0, mx=15.0, my=30.0, mz=50.0),
            _elastic_mode(10, 50.0, mx=5.0,  my=10.0, mz=10.0),
        ]

    def test_fractions_are_monotonically_non_decreasing(self):
        fractions = compute_cumulative_effective_mass_fractions(
            self.modes, 'x', TOTAL_MASS
        )
        values = [f for _, f in fractions]
        for i in range(1, len(values)):
            self.assertGreaterEqual(values[i], values[i - 1])

    def test_final_fraction_matches_sum(self):
        fractions = compute_cumulative_effective_mass_fractions(
            self.modes, 'x', TOTAL_MASS
        )
        _, final = fractions[-1]
        expected = (50.0 + 30.0 + 15.0 + 5.0) / TOTAL_MASS
        self.assertAlmostEqual(final, expected, places=10)

    def test_invalid_axis_raises(self):
        with self.assertRaises(ValueError):
            compute_cumulative_effective_mass_fractions(self.modes, 'w', TOTAL_MASS)

    def test_zero_total_mass_raises(self):
        with self.assertRaises(ValueError):
            compute_cumulative_effective_mass_fractions(self.modes, 'x', 0.0)


class TestEffectiveMassFractionCheck(unittest.TestCase):

    def _modes_with_full_x_mass(self):
        rb = _six_rb_modes()
        elastic = [
            _elastic_mode(7, 10.0, mx=60.0),
            _elastic_mode(8, 20.0, mx=35.0),
        ]
        return rb + elastic

    def test_fraction_above_threshold_passes(self):
        modes = self._modes_with_full_x_mass()
        result = check_effective_mass_fraction(modes, 'x', TOTAL_MASS, EMF_THRESHOLD)
        self.assertTrue(result.passed)
        self.assertAlmostEqual(result.value, 0.95)

    def test_fraction_below_threshold_fails(self):
        rb = _six_rb_modes()
        elastic = [_elastic_mode(7, 10.0, mx=50.0)]  # 50 % only
        modes = rb + elastic
        result = check_effective_mass_fraction(modes, 'x', TOTAL_MASS, EMF_THRESHOLD)
        self.assertFalse(result.passed)
        self.assertAlmostEqual(result.value, 0.50)

    def test_exactly_at_threshold_passes(self):
        rb = _six_rb_modes()
        elastic = [_elastic_mode(7, 10.0, mx=90.0)]
        modes = rb + elastic
        result = check_effective_mass_fraction(modes, 'x', TOTAL_MASS, EMF_THRESHOLD)
        self.assertTrue(result.passed)


class TestMinimumFrequencyCheck(unittest.TestCase):

    def test_first_elastic_above_minimum_passes(self):
        modes = _six_rb_modes() + [_elastic_mode(7, 20.0), _elastic_mode(8, 35.0)]
        req = FrequencyRequirement(label='lateral', min_hz=15.0)
        result = check_minimum_frequency(modes, req, THRESHOLD_HZ)
        self.assertTrue(result.passed)
        self.assertAlmostEqual(result.value, 20.0)

    def test_first_elastic_below_minimum_fails(self):
        modes = _six_rb_modes() + [_elastic_mode(7, 8.0), _elastic_mode(8, 25.0)]
        req = FrequencyRequirement(label='axial', min_hz=10.0)
        result = check_minimum_frequency(modes, req, THRESHOLD_HZ)
        self.assertFalse(result.passed)
        self.assertAlmostEqual(result.value, 8.0)

    def test_no_elastic_modes_fails(self):
        modes = _six_rb_modes()
        req = FrequencyRequirement(label='lateral', min_hz=5.0)
        result = check_minimum_frequency(modes, req, THRESHOLD_HZ)
        self.assertFalse(result.passed)
        self.assertIsNone(result.value)


class TestRunAllChecks(unittest.TestCase):

    def _build_compliant_set(self):
        rb = _six_rb_modes()
        elastic = [
            _elastic_mode(7,  15.0, mx=45.0, my=45.0, mz=45.0),
            _elastic_mode(8,  30.0, mx=30.0, my=30.0, mz=30.0),
            _elastic_mode(9,  50.0, mx=20.0, my=20.0, mz=20.0),
        ]
        return rb + elastic

    def test_compliant_model_all_pass(self):
        modes = self._build_compliant_set()
        config = ModalCheckConfig(
            total_mass=TOTAL_MASS,
            rigid_body_freq_threshold_hz=THRESHOLD_HZ,
            effective_mass_fraction_threshold=0.90,
            frequency_requirements=[
                FrequencyRequirement(label='lateral', min_hz=10.0),
            ],
        )
        results = run_all_checks(modes, config)
        all_passed, failures = summarize(results)
        self.assertTrue(all_passed, msg=f"Unexpected failures: {failures}")

    def test_wrong_rb_count_causes_failure(self):
        modes = [_rb_mode(i + 1) for i in range(4)] + [
            _elastic_mode(5, 15.0, mx=50.0, my=50.0, mz=50.0),
            _elastic_mode(6, 30.0, mx=45.0, my=45.0, mz=45.0),
        ]
        config = ModalCheckConfig(
            total_mass=TOTAL_MASS,
            rigid_body_freq_threshold_hz=THRESHOLD_HZ,
            effective_mass_fraction_threshold=0.90,
        )
        results = run_all_checks(modes, config)
        all_passed, failures = summarize(results)
        self.assertFalse(all_passed)
        self.assertTrue(any('rigid_body_count' in f for f in failures))

    def test_empty_modes_raises(self):
        config = ModalCheckConfig(total_mass=TOTAL_MASS)
        with self.assertRaises(ValueError):
            run_all_checks([], config)

    def test_zero_total_mass_raises(self):
        modes = _six_rb_modes() + [_elastic_mode(7, 10.0)]
        config = ModalCheckConfig(total_mass=0.0)
        with self.assertRaises(ValueError):
            run_all_checks(modes, config)

    def test_frequency_requirement_failure_reported(self):
        rb = _six_rb_modes()
        elastic = [
            _elastic_mode(7, 3.0, mx=50.0, my=50.0, mz=50.0),
            _elastic_mode(8, 6.0, mx=45.0, my=45.0, mz=45.0),
        ]
        modes = rb + elastic
        config = ModalCheckConfig(
            total_mass=TOTAL_MASS,
            rigid_body_freq_threshold_hz=THRESHOLD_HZ,
            effective_mass_fraction_threshold=0.90,
            frequency_requirements=[
                FrequencyRequirement(label='axial', min_hz=5.0),
            ],
        )
        results = run_all_checks(modes, config)
        all_passed, failures = summarize(results)
        self.assertFalse(all_passed)
        self.assertTrue(any('frequency_requirements' in f for f in failures))

    def test_low_effective_mass_fraction_reported(self):
        rb = _six_rb_modes()
        elastic = [_elastic_mode(7, 15.0, mx=20.0, my=20.0, mz=20.0)]
        modes = rb + elastic
        config = ModalCheckConfig(
            total_mass=TOTAL_MASS,
            rigid_body_freq_threshold_hz=THRESHOLD_HZ,
            effective_mass_fraction_threshold=0.90,
        )
        results = run_all_checks(modes, config)
        all_passed, failures = summarize(results)
        self.assertFalse(all_passed)
        fraction_failures = [f for f in failures if 'effective_mass_fraction' in f]
        self.assertGreater(len(fraction_failures), 0)


class TestSummarize(unittest.TestCase):

    def test_all_passed_returns_true_empty_list(self):
        from modal_analysis_checks_logic import CheckResult
        results = {'check_a': [CheckResult(passed=True, message='ok')]}
        ok, failures = summarize(results)
        self.assertTrue(ok)
        self.assertEqual(failures, [])

    def test_one_failure_returns_false(self):
        from modal_analysis_checks_logic import CheckResult
        results = {
            'check_a': [CheckResult(passed=True, message='ok')],
            'check_b': [CheckResult(passed=False, message='fail detail')],
        }
        ok, failures = summarize(results)
        self.assertFalse(ok)
        self.assertEqual(len(failures), 1)
        self.assertIn('check_b', failures[0])


if __name__ == "__main__":
    unittest.main()
