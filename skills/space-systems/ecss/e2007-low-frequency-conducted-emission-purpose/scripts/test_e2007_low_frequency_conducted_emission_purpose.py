"""Contract test for the low-frequency conducted-emission purpose leaf (stdlib unittest)."""

import unittest

from e2007_low_frequency_conducted_emission_purpose_logic import (
    BAND_CEILING_HZ,
    BAND_FLOOR_HZ,
    OBJECTIVE_BAND,
    OBJECTIVE_LIMIT_LINE,
    OBJECTIVE_RETURN_LEADS,
    OBJECTIVE_SENSING,
    OBJECTIVE_SUPPLY_LEADS,
    assess_low_frequency_conducted_emission_purpose,
    assess_plan,
    band_coverage_fraction,
    band_decades,
    band_spans_the_aim,
    objectives_served,
    required_band_decades,
    uninstrumented_leads,
    unserved_objectives,
    validate_plan,
)

# Independently worked reference values for the log-domain coverage of
# the 30 Hz to 100 kHz aim band (3.5228787452803374 decades wide).
FULL_BAND_DECADES = 3.5228787452803374
COVERAGE_300HZ_TO_30KHZ = 0.567717524390936
COVERAGE_300HZ_TO_200KHZ = 0.716141237804532


def plan(pid="P-1", **kw):
    record = {
        "id": pid,
        "band_start_hz": 30.0,
        "band_stop_hz": 100.0e3,
        "method": "current-probe",
        "supply_leads": ["PWR-A", "PWR-B"],
        "return_leads": ["RTN-A", "RTN-B"],
        "instrumented_leads": ["PWR-A", "PWR-B", "RTN-A", "RTN-B"],
        "limit_line_declared": True,
    }
    record.update(kw)
    return record


class TestValidatePlan(unittest.TestCase):
    def test_normalized_copy_keeps_the_leads(self):
        norm = validate_plan(plan())
        self.assertEqual(norm["supply_leads"], ["PWR-A", "PWR-B"])
        self.assertEqual(norm["return_leads"], ["RTN-A", "RTN-B"])
        self.assertTrue(norm["limit_line_declared"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_plan(["P-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_plan(plan(""))

    def test_non_positive_start_raises(self):
        with self.assertRaises(ValueError):
            validate_plan(plan("P-1", band_start_hz=0.0))

    def test_stop_below_start_raises(self):
        with self.assertRaises(ValueError):
            validate_plan(plan("P-1", band_start_hz=1.0e3, band_stop_hz=100.0))

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            validate_plan(plan("P-1", method="oscilloscope-eyeball"))

    def test_empty_supply_lead_list_raises(self):
        with self.assertRaises(ValueError):
            validate_plan(plan("P-1", supply_leads=[]))

    def test_empty_return_lead_list_raises(self):
        with self.assertRaises(ValueError):
            validate_plan(plan("P-1", return_leads=[]))

    def test_lead_named_as_both_supply_and_return_raises(self):
        with self.assertRaises(ValueError):
            validate_plan(plan("P-1", return_leads=["PWR-A"]))

    def test_duplicate_lead_in_one_list_raises(self):
        with self.assertRaises(ValueError):
            validate_plan(plan("P-1", supply_leads=["PWR-A", "PWR-A"]))

    def test_instrumenting_an_unknown_lead_raises(self):
        with self.assertRaises(ValueError):
            validate_plan(plan("P-1", instrumented_leads=["PWR-Z"]))

    def test_non_string_lead_raises(self):
        with self.assertRaises(ValueError):
            validate_plan(plan("P-1", supply_leads=[7]))

    def test_non_boolean_limit_line_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_plan(plan("P-1", limit_line_declared="yes"))


class TestBandArithmetic(unittest.TestCase):
    def test_required_band_width_in_decades(self):
        self.assertAlmostEqual(required_band_decades(), FULL_BAND_DECADES, places=9)

    def test_one_decade_band(self):
        self.assertAlmostEqual(band_decades(100.0, 1000.0), 1.0, places=9)

    def test_three_decade_band(self):
        self.assertAlmostEqual(band_decades(10.0, 10000.0), 3.0, places=9)

    def test_inverted_band_raises(self):
        with self.assertRaises(ValueError):
            band_decades(1000.0, 100.0)

    def test_non_positive_edge_raises(self):
        with self.assertRaises(ValueError):
            band_decades(0.0, 100.0)

    def test_non_numeric_edge_raises(self):
        with self.assertRaises(ValueError):
            band_decades("30 Hz", 100.0)


class TestBandCoverage(unittest.TestCase):
    def test_exact_aim_band_gives_full_coverage(self):
        self.assertAlmostEqual(band_coverage_fraction(plan()), 1.0, places=9)

    def test_wider_sweep_is_not_credited_beyond_the_aim(self):
        wide = plan("P-1", band_start_hz=1.0, band_stop_hz=1.0e6)
        self.assertAlmostEqual(band_coverage_fraction(wide), 1.0, places=9)

    def test_narrow_sweep_inside_the_band(self):
        narrow = plan("P-1", band_start_hz=300.0, band_stop_hz=30.0e3)
        self.assertAlmostEqual(
            band_coverage_fraction(narrow), COVERAGE_300HZ_TO_30KHZ, places=9
        )

    def test_sweep_overhanging_the_top_edge_is_clipped(self):
        over = plan("P-1", band_start_hz=300.0, band_stop_hz=200.0e3)
        self.assertAlmostEqual(
            band_coverage_fraction(over), COVERAGE_300HZ_TO_200KHZ, places=9
        )

    def test_sweep_entirely_above_the_band_covers_nothing(self):
        above = plan("P-1", band_start_hz=200.0e3, band_stop_hz=400.0e3)
        self.assertAlmostEqual(band_coverage_fraction(above), 0.0, places=9)

    def test_sweep_entirely_below_the_band_covers_nothing(self):
        below = plan("P-1", band_start_hz=1.0, band_stop_hz=10.0)
        self.assertAlmostEqual(band_coverage_fraction(below), 0.0, places=9)


class TestBandSpan(unittest.TestCase):
    def test_exact_edges_span_the_aim(self):
        self.assertTrue(band_spans_the_aim(plan()))

    def test_plan_written_to_the_literal_constants_spans_the_aim(self):
        edged = plan("P-1", band_start_hz=BAND_FLOOR_HZ, band_stop_hz=BAND_CEILING_HZ)
        self.assertTrue(band_spans_the_aim(edged))

    def test_sweep_starting_late_does_not_span(self):
        self.assertFalse(band_spans_the_aim(plan("P-1", band_start_hz=150.0)))

    def test_sweep_stopping_early_does_not_span(self):
        self.assertFalse(band_spans_the_aim(plan("P-1", band_stop_hz=20.0e3)))


class TestLeadCoverage(unittest.TestCase):
    def test_fully_instrumented_plan_leaves_nothing_out(self):
        missing_supply, missing_return = uninstrumented_leads(plan())
        self.assertEqual(missing_supply, [])
        self.assertEqual(missing_return, [])

    def test_supply_only_plan_names_the_missing_returns(self):
        supply_only = plan("P-1", instrumented_leads=["PWR-A", "PWR-B"])
        missing_supply, missing_return = uninstrumented_leads(supply_only)
        self.assertEqual(missing_supply, [])
        self.assertEqual(missing_return, ["RTN-A", "RTN-B"])

    def test_partial_plan_names_the_missing_supply_lead(self):
        partial = plan("P-1", instrumented_leads=["PWR-A", "RTN-A", "RTN-B"])
        missing_supply, missing_return = uninstrumented_leads(partial)
        self.assertEqual(missing_supply, ["PWR-B"])
        self.assertEqual(missing_return, [])


class TestObjectives(unittest.TestCase):
    def test_complete_plan_serves_every_objective(self):
        served = objectives_served(plan())
        self.assertTrue(all(served.values()))
        self.assertEqual(unserved_objectives(plan()), [])

    def test_missing_returns_unserve_one_objective(self):
        supply_only = plan("P-1", instrumented_leads=["PWR-A", "PWR-B"])
        served = objectives_served(supply_only)
        self.assertTrue(served[OBJECTIVE_SUPPLY_LEADS])
        self.assertFalse(served[OBJECTIVE_RETURN_LEADS])
        self.assertEqual(unserved_objectives(supply_only), [OBJECTIVE_RETURN_LEADS])

    def test_short_sweep_unserves_the_band_objective(self):
        short = plan("P-1", band_stop_hz=20.0e3)
        self.assertEqual(unserved_objectives(short), [OBJECTIVE_BAND])

    def test_absent_limit_line_unserves_its_objective(self):
        unlimited = plan("P-1", limit_line_declared=False)
        self.assertEqual(unserved_objectives(unlimited), [OBJECTIVE_LIMIT_LINE])

    def test_voltage_probe_unserves_the_sensing_objective(self):
        voltage = plan("P-1", method="voltage-probe")
        self.assertEqual(unserved_objectives(voltage), [OBJECTIVE_SENSING])

    def test_stabilisation_network_unserves_the_sensing_objective(self):
        lisn = plan("P-1", method="line-impedance-stabilisation-network")
        self.assertFalse(objectives_served(lisn)[OBJECTIVE_SENSING])

    def test_unserved_objectives_keep_a_fixed_order(self):
        bad = plan(
            "P-1",
            instrumented_leads=[],
            band_stop_hz=20.0e3,
            limit_line_declared=False,
            method="voltage-probe",
        )
        self.assertEqual(
            unserved_objectives(bad),
            [
                OBJECTIVE_SUPPLY_LEADS,
                OBJECTIVE_RETURN_LEADS,
                OBJECTIVE_BAND,
                OBJECTIVE_LIMIT_LINE,
                OBJECTIVE_SENSING,
            ],
        )


class TestAssessPlan(unittest.TestCase):
    def test_complete_plan_serves_the_aim(self):
        result = assess_plan(plan())
        self.assertTrue(result["serves_the_aim"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["band_coverage_fraction"], 1.0, places=9)

    def test_supply_only_plan_misses_the_aim(self):
        result = assess_plan(plan("P-1", instrumented_leads=["PWR-A", "PWR-B"]))
        self.assertFalse(result["serves_the_aim"])
        self.assertEqual(result["findings"], ["return-leads-without-a-sensor"])
        self.assertEqual(result["missing_return_leads"], ["RTN-A", "RTN-B"])

    def test_short_sweep_plan_misses_the_aim(self):
        result = assess_plan(plan("P-1", band_start_hz=300.0, band_stop_hz=30.0e3))
        self.assertFalse(result["serves_the_aim"])
        self.assertIn("sweep-does-not-span-the-low-frequency-band", result["findings"])
        self.assertAlmostEqual(
            result["band_coverage_fraction"], COVERAGE_300HZ_TO_30KHZ, places=9
        )

    def test_plan_without_a_limit_line_misses_the_aim(self):
        result = assess_plan(plan("P-1", limit_line_declared=False))
        self.assertIn("no-limit-line-to-compare-against", result["findings"])


class TestAssessPlanSet(unittest.TestCase):
    def test_clean_set_serves_the_aim(self):
        report = assess_low_frequency_conducted_emission_purpose(
            [plan("P-1"), plan("P-2")]
        )
        self.assertTrue(report["serves_the_aim"])
        self.assertAlmostEqual(report["mean_band_coverage_fraction"], 1.0, places=9)
        self.assertEqual(report["plans_missing_the_aim"], [])

    def test_mean_coverage_over_a_mixed_set(self):
        report = assess_low_frequency_conducted_emission_purpose(
            [plan("P-1"), plan("P-2", band_start_hz=300.0, band_stop_hz=30.0e3)]
        )
        self.assertAlmostEqual(
            report["mean_band_coverage_fraction"],
            (1.0 + COVERAGE_300HZ_TO_30KHZ) / 2.0,
            places=9,
        )
        self.assertEqual(report["plans_missing_the_aim"], ["P-2"])

    def test_duplicate_plan_id_raises(self):
        with self.assertRaises(ValueError):
            assess_low_frequency_conducted_emission_purpose([plan("P-1"), plan("P-1")])

    def test_empty_plan_list_raises(self):
        with self.assertRaises(ValueError):
            assess_low_frequency_conducted_emission_purpose([])

    def test_non_list_input_raises(self):
        with self.assertRaises(ValueError):
            assess_low_frequency_conducted_emission_purpose(plan())


if __name__ == "__main__":
    unittest.main()
