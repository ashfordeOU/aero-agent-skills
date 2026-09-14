#!/usr/bin/env python3
"""Contract test for the cell equivalent network leaf (offline)."""

import copy
import math
import unittest

from e2008_equivalent_network_calculation_logic import (
    MAX_CLOSURE_RESIDUAL_FRACTION,
    MAX_CONTACT_RESISTANCE_SHARE,
    MAX_READOUT_DEVIATION_FRACTION,
    MAX_UNSTATED_NETWORK_SPREAD,
    NETWORK_DERIVED,
    NETWORK_NOT_DERIVED,
    capacitive_phase_deg,
    closure_residual_fraction,
    contact_corrected_resistance_ohm,
    contact_resistance_share,
    derive_equivalent_network,
    dissipation_factor,
    missing_evidence,
    network_spread_fraction,
    parallel_capacitance_f,
    parallel_network_impedance,
    parallel_resistance_ohm,
    quality_factor,
    readout_deviation_fraction,
    series_capacitance_f,
    series_components,
)

TEST_FREQUENCY_HZ = 1000.0
MEASURED_MAGNITUDE_OHM = 400.0
MEASURED_PHASE_DEG = -87.0
LOSS_ANGLE_DEG = 90.0 + MEASURED_PHASE_DEG

BASE_CASE = {
    "impedance_magnitude_ohm": MEASURED_MAGNITUDE_OHM,
    "phase_deg": MEASURED_PHASE_DEG,
    "test_frequency_hz": TEST_FREQUENCY_HZ,
    "contact_resistance_ohm": 5.0,
    "instrument_parallel_capacitance_f": 3.98e-7,
}


def _case(**overrides):
    case = copy.deepcopy(BASE_CASE)
    case.update(overrides)
    return case


def _finding_matching(result, fragment):
    return [f for f in result["findings"] if fragment in f]


class PhaseValidationTests(unittest.TestCase):
    def test_a_lagging_phase_is_accepted_unchanged(self):
        self.assertAlmostEqual(capacitive_phase_deg(-87.0), -87.0, places=12)

    def test_a_purely_resistive_phase_is_refused(self):
        with self.assertRaises(ValueError):
            capacitive_phase_deg(0.0)

    def test_an_inductive_phase_is_refused(self):
        with self.assertRaises(ValueError):
            capacitive_phase_deg(5.0)

    def test_a_lossless_quarter_turn_is_refused(self):
        with self.assertRaises(ValueError):
            capacitive_phase_deg(-90.0)

    def test_a_phase_beyond_a_quarter_turn_is_refused(self):
        with self.assertRaises(ValueError):
            capacitive_phase_deg(-95.0)

    def test_a_phase_that_is_not_a_number_is_refused(self):
        with self.assertRaises(ValueError):
            capacitive_phase_deg("lagging")


class SeriesResolutionTests(unittest.TestCase):
    def test_the_series_pair_reproduces_the_measured_magnitude(self):
        r, x = series_components(MEASURED_MAGNITUDE_OHM, MEASURED_PHASE_DEG)
        self.assertAlmostEqual(math.hypot(r, x), MEASURED_MAGNITUDE_OHM, places=9)
        self.assertLess(x, 0.0)
        self.assertGreater(r, 0.0)

    def test_a_non_positive_magnitude_is_refused(self):
        with self.assertRaises(ValueError):
            series_components(0.0, MEASURED_PHASE_DEG)

    def test_the_series_capacitance_inverts_the_reactance(self):
        r, x = series_components(MEASURED_MAGNITUDE_OHM, MEASURED_PHASE_DEG)
        expected = 1.0 / (2.0 * math.pi * TEST_FREQUENCY_HZ * abs(x))
        self.assertAlmostEqual(
            series_capacitance_f(x, TEST_FREQUENCY_HZ) / expected, 1.0, places=12
        )

    def test_a_positive_reactance_has_no_series_capacitance(self):
        with self.assertRaises(ValueError):
            series_capacitance_f(10.0, TEST_FREQUENCY_HZ)

    def test_the_dissipation_factor_is_the_tangent_of_the_loss_angle(self):
        r, x = series_components(MEASURED_MAGNITUDE_OHM, MEASURED_PHASE_DEG)
        self.assertAlmostEqual(
            dissipation_factor(r, x),
            math.tan(math.radians(LOSS_ANGLE_DEG)),
            places=12,
        )

    def test_the_dissipation_factor_refuses_a_positive_reactance(self):
        with self.assertRaises(ValueError):
            dissipation_factor(20.0, 10.0)

    def test_the_quality_factor_is_the_reciprocal_of_the_loss(self):
        self.assertAlmostEqual(quality_factor(0.05), 20.0, places=12)

    def test_a_zero_loss_has_no_quality_factor(self):
        with self.assertRaises(ValueError):
            quality_factor(0.0)


class ParallelFormTests(unittest.TestCase):
    def test_the_parallel_resistance_rises_with_the_square_of_the_quality(self):
        self.assertAlmostEqual(
            parallel_resistance_ohm(20.0, 10.0), 20.0 * 101.0, places=9
        )

    def test_the_parallel_capacitance_is_the_series_one_divided_down(self):
        self.assertAlmostEqual(
            parallel_capacitance_f(1.0e-9, 0.1), 1.0e-9 / 1.01, places=21
        )

    def test_the_parallel_capacitance_never_exceeds_the_series_one(self):
        self.assertLess(parallel_capacitance_f(1.0e-9, 0.2), 1.0e-9)

    def test_a_lossless_pair_leaves_the_capacitance_alone(self):
        self.assertAlmostEqual(
            parallel_capacitance_f(1.0e-9, 0.0), 1.0e-9, places=21
        )

    def test_the_spread_is_the_relative_gap_between_the_two_forms(self):
        self.assertAlmostEqual(
            network_spread_fraction(1.0e-9, 0.99e-9), 0.01, places=12
        )

    def test_a_zero_series_capacitance_has_no_spread(self):
        with self.assertRaises(ValueError):
            network_spread_fraction(0.0, 1.0e-9)


class ContactCorrectionTests(unittest.TestCase):
    def test_the_harness_term_is_subtracted_from_the_series_resistance(self):
        self.assertAlmostEqual(
            contact_corrected_resistance_ohm(20.0, 5.0), 15.0, places=12
        )

    def test_a_harness_equal_to_the_measurement_is_refused(self):
        with self.assertRaises(ValueError):
            contact_corrected_resistance_ohm(20.0, 20.0)

    def test_a_harness_above_the_measurement_is_refused(self):
        with self.assertRaises(ValueError):
            contact_corrected_resistance_ohm(20.0, 25.0)

    def test_a_negative_harness_term_is_refused(self):
        with self.assertRaises(ValueError):
            contact_corrected_resistance_ohm(20.0, -1.0)

    def test_the_harness_share_is_reported_as_a_fraction(self):
        self.assertAlmostEqual(contact_resistance_share(20.0, 5.0), 0.25, places=12)


class ClosureTests(unittest.TestCase):
    def test_the_parallel_pair_rebuilds_the_measurement_it_came_from(self):
        result = derive_equivalent_network(_case())
        magnitude, phase = parallel_network_impedance(
            result["parallel_capacitance_f"],
            result["parallel_resistance_ohm"],
            TEST_FREQUENCY_HZ,
        )
        self.assertAlmostEqual(magnitude, MEASURED_MAGNITUDE_OHM, places=9)
        self.assertAlmostEqual(phase, MEASURED_PHASE_DEG, places=9)

    def test_an_identical_rebuild_leaves_no_residual(self):
        self.assertAlmostEqual(
            closure_residual_fraction(400.0, 400.0), 0.0, places=12
        )

    def test_a_zero_measured_magnitude_is_refused(self):
        with self.assertRaises(ValueError):
            closure_residual_fraction(0.0, 400.0)

    def test_the_readout_deviation_is_relative_to_the_derived_value(self):
        self.assertAlmostEqual(
            readout_deviation_fraction(1.0e-9, 1.02e-9), 0.02, places=12
        )

    def test_a_zero_declared_readout_is_refused(self):
        with self.assertRaises(ValueError):
            readout_deviation_fraction(1.0e-9, 0.0)


class DerivationTests(unittest.TestCase):
    def test_a_low_loss_measurement_derives_cleanly(self):
        result = derive_equivalent_network(_case())
        self.assertTrue(result["derived"])
        self.assertEqual(result["verdict"], NETWORK_DERIVED)
        self.assertEqual(result["findings"], [])

    def test_both_network_forms_are_reported_and_the_parallel_is_smaller(self):
        result = derive_equivalent_network(_case())
        self.assertLess(
            result["parallel_capacitance_f"], result["series_capacitance_f"]
        )
        self.assertGreater(
            result["parallel_resistance_ohm"], result["series_resistance_ohm"]
        )

    def test_the_derivation_closes_on_itself_to_representation_error(self):
        result = derive_equivalent_network(_case())
        self.assertAlmostEqual(result["closure_residual_fraction"], 0.0, places=12)
        self.assertLess(
            result["closure_residual_fraction"], MAX_CLOSURE_RESIDUAL_FRACTION
        )

    def test_the_harness_is_removed_from_the_reported_cell_resistance(self):
        result = derive_equivalent_network(_case())
        self.assertAlmostEqual(
            result["cell_series_resistance_ohm"],
            result["series_resistance_ohm"] - 5.0,
            places=12,
        )

    def test_a_spread_exactly_on_the_limit_is_not_a_finding(self):
        d = math.sqrt(
            MAX_UNSTATED_NETWORK_SPREAD / (1.0 - MAX_UNSTATED_NETWORK_SPREAD)
        )
        phase = -(90.0 - math.degrees(math.atan(d)))
        case = _case(phase_deg=phase)
        del case["instrument_parallel_capacitance_f"]
        result = derive_equivalent_network(case)
        self.assertAlmostEqual(
            result["network_spread_fraction"],
            MAX_UNSTATED_NETWORK_SPREAD,
            places=9,
        )
        self.assertEqual(_finding_matching(result, "differ by"), [])
        self.assertTrue(result["derived"])

    def test_a_lossy_cell_forces_the_network_form_to_be_named(self):
        result = derive_equivalent_network(_case(phase_deg=-80.0))
        self.assertFalse(result["derived"])
        self.assertEqual(result["verdict"], NETWORK_NOT_DERIVED)
        self.assertTrue(_finding_matching(result, "differ by"))
        self.assertGreater(
            result["network_spread_fraction"], MAX_UNSTATED_NETWORK_SPREAD
        )

    def test_a_dominating_harness_is_a_finding(self):
        result = derive_equivalent_network(_case(contact_resistance_ohm=15.0))
        self.assertTrue(_finding_matching(result, "harness contributes"))
        self.assertGreater(
            result["contact_resistance_share"], MAX_CONTACT_RESISTANCE_SHARE
        )

    def test_a_harness_term_above_the_measurement_stops_the_derivation(self):
        with self.assertRaises(ValueError):
            derive_equivalent_network(_case(contact_resistance_ohm=100.0))

    def test_an_instrument_readout_that_disagrees_is_a_finding(self):
        result = derive_equivalent_network(
            _case(instrument_parallel_capacitance_f=4.2e-7)
        )
        self.assertTrue(_finding_matching(result, "instrument parallel readout"))
        self.assertGreater(
            result["readout_deviation_fraction"], MAX_READOUT_DEVIATION_FRACTION
        )

    def test_no_instrument_readout_leaves_the_deviation_unreported(self):
        case = _case()
        del case["instrument_parallel_capacitance_f"]
        result = derive_equivalent_network(case)
        self.assertIsNone(result["readout_deviation_fraction"])
        self.assertTrue(result["derived"])

    def test_an_absent_harness_term_defaults_to_nothing_removed(self):
        case = _case()
        del case["contact_resistance_ohm"]
        result = derive_equivalent_network(case)
        self.assertAlmostEqual(result["contact_resistance_share"], 0.0, places=12)
        self.assertAlmostEqual(
            result["cell_series_resistance_ohm"],
            result["series_resistance_ohm"],
            places=12,
        )

    def test_missing_evidence_names_the_absent_input(self):
        case = _case()
        del case["phase_deg"]
        self.assertEqual(missing_evidence(case), ("phase_deg",))

    def test_absent_evidence_stops_the_derivation(self):
        case = _case()
        del case["test_frequency_hz"]
        with self.assertRaises(ValueError):
            derive_equivalent_network(case)

    def test_an_inductive_measurement_stops_the_derivation(self):
        with self.assertRaises(ValueError):
            derive_equivalent_network(_case(phase_deg=12.0))

    def test_a_case_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            derive_equivalent_network("400 ohm")

    def test_the_verdict_string_tracks_the_derived_flag(self):
        good = derive_equivalent_network(_case())
        bad = derive_equivalent_network(_case(phase_deg=-80.0))
        self.assertEqual(good["verdict"], NETWORK_DERIVED)
        self.assertEqual(bad["verdict"], NETWORK_NOT_DERIVED)


if __name__ == "__main__":
    unittest.main()
