#!/usr/bin/env python3
"""Contract test for the power-lead susceptibility setup leaf."""

import unittest

from e2007_power_lead_susceptibility_setup_logic import (
    BOND_RESISTANCE_LIMIT_OHM,
    INJECTION_WINDOW_M,
    LEAD_HEIGHT_NOMINAL_M,
    LEAD_RUN_NOMINAL_M,
    MONITOR_OFFSET_MAX_M,
    SIGNAL_LEAD_SEPARATION_MIN_M,
    assess_bench_setup,
    check_bond_resistance,
    check_injection_position,
    check_lead_height,
    check_lead_run,
    check_monitor_position,
    check_signal_lead_separation,
    normalize_lead,
)


def high_lead(**overrides):
    lead = {
        "id": "PWR-HI",
        "polarity": "high",
        "stabilization_network": True,
        "run_length_m": 2.0,
        "height_m": 0.05,
        "injected": True,
        "injection_offset_m": 0.12,
        "monitor_offset_m": 0.14,
        "signal_lead_separation_m": 0.10,
    }
    lead.update(overrides)
    return lead


def return_lead(**overrides):
    lead = {
        "id": "PWR-RTN",
        "polarity": "return",
        "stabilization_network": True,
        "run_length_m": 2.0,
        "height_m": 0.05,
    }
    lead.update(overrides)
    return lead


def setup(**overrides):
    bench = {
        "leads": [high_lead(), return_lead()],
        "bond_resistance_ohm": 1.0e-3,
        "ground_plane": True,
    }
    bench.update(overrides)
    return bench


def codes(report):
    return [finding["code"] for finding in report["findings"]]


class TestLeadRun(unittest.TestCase):
    def test_nominal_run_conforms(self):
        check = check_lead_run(LEAD_RUN_NOMINAL_M)
        self.assertTrue(check["within"])
        self.assertAlmostEqual(check["deviation_m"], 0.0, places=12)

    def test_run_on_the_allowance_still_conforms(self):
        check = check_lead_run(2.2)
        self.assertAlmostEqual(check["deviation_m"], 0.2, places=9)
        self.assertAlmostEqual(check["allowed_m"], 0.2, places=9)
        self.assertTrue(check["within"])

    def test_run_well_past_the_allowance_fails(self):
        self.assertFalse(check_lead_run(3.0)["within"])

    def test_short_run_fails_the_same_way(self):
        self.assertFalse(check_lead_run(1.0)["within"])

    def test_zero_run_raises(self):
        with self.assertRaises(ValueError):
            check_lead_run(0.0)

    def test_tolerance_fraction_of_one_raises(self):
        with self.assertRaises(ValueError):
            check_lead_run(2.0, tolerance_fraction=1.0)


class TestLeadHeight(unittest.TestCase):
    def test_nominal_height_conforms(self):
        self.assertTrue(check_lead_height(LEAD_HEIGHT_NOMINAL_M)["within"])

    def test_height_on_the_allowance_still_conforms(self):
        check = check_lead_height(0.06)
        self.assertAlmostEqual(check["deviation_m"], 0.01, places=9)
        self.assertTrue(check["within"])

    def test_height_well_past_the_allowance_fails(self):
        self.assertFalse(check_lead_height(0.12)["within"])

    def test_non_numeric_height_raises(self):
        with self.assertRaises(ValueError):
            check_lead_height("50 mm")


class TestInjectionPosition(unittest.TestCase):
    def test_a_mid_window_offset_conforms(self):
        check = check_injection_position(0.12)
        self.assertTrue(check["within"])
        self.assertFalse(check["too_near"])
        self.assertFalse(check["too_far"])

    def test_the_near_edge_of_the_window_conforms(self):
        check = check_injection_position(INJECTION_WINDOW_M[0])
        self.assertTrue(check["within"])

    def test_the_far_edge_of_the_window_conforms(self):
        check = check_injection_position(INJECTION_WINDOW_M[1])
        self.assertTrue(check["within"])

    def test_an_offset_below_the_window_is_too_near(self):
        check = check_injection_position(0.01)
        self.assertTrue(check["too_near"])
        self.assertFalse(check["within"])

    def test_an_offset_above_the_window_is_too_far(self):
        check = check_injection_position(0.60)
        self.assertTrue(check["too_far"])
        self.assertFalse(check["within"])

    def test_a_window_that_does_not_widen_raises(self):
        with self.assertRaises(ValueError):
            check_injection_position(0.12, window_m=(0.20, 0.05))

    def test_a_window_that_is_not_a_pair_raises(self):
        with self.assertRaises(ValueError):
            check_injection_position(0.12, window_m=0.20)


class TestMonitorPosition(unittest.TestCase):
    def test_a_close_monitor_conforms(self):
        self.assertTrue(check_monitor_position(0.12, 0.14)["within"])

    def test_a_monitor_on_the_allowance_conforms(self):
        check = check_monitor_position(0.10, 0.15)
        self.assertAlmostEqual(check["separation_m"], MONITOR_OFFSET_MAX_M, places=9)
        self.assertTrue(check["within"])

    def test_a_monitor_well_past_the_allowance_fails(self):
        self.assertFalse(check_monitor_position(0.10, 0.60)["within"])

    def test_a_monitor_on_the_near_side_is_measured_the_same_way(self):
        check = check_monitor_position(0.15, 0.12)
        self.assertAlmostEqual(check["separation_m"], 0.03, places=9)
        self.assertTrue(check["within"])


class TestBondAndSeparation(unittest.TestCase):
    def test_a_low_bond_conforms(self):
        check = check_bond_resistance(1.0e-3)
        self.assertTrue(check["within"])
        self.assertAlmostEqual(check["milliohm"], 1.0, places=9)

    def test_a_bond_on_the_limit_conforms(self):
        self.assertTrue(check_bond_resistance(BOND_RESISTANCE_LIMIT_OHM)["within"])

    def test_a_bond_well_over_the_limit_fails(self):
        self.assertFalse(check_bond_resistance(0.1)["within"])

    def test_a_negative_bond_raises(self):
        with self.assertRaises(ValueError):
            check_bond_resistance(-1.0e-3)

    def test_separation_on_the_minimum_conforms(self):
        self.assertTrue(
            check_signal_lead_separation(SIGNAL_LEAD_SEPARATION_MIN_M)["within"]
        )

    def test_separation_well_below_the_minimum_fails(self):
        self.assertFalse(check_signal_lead_separation(0.005)["within"])


class TestNormalizeLead(unittest.TestCase):
    def test_a_good_injected_lead_normalizes(self):
        lead = normalize_lead(high_lead())
        self.assertEqual(lead["id"], "PWR-HI")
        self.assertTrue(lead["injected"])
        self.assertAlmostEqual(lead["injection_offset_m"], 0.12, places=9)

    def test_a_non_injected_lead_carries_no_offsets(self):
        lead = normalize_lead(return_lead())
        self.assertFalse(lead["injected"])
        self.assertIsNone(lead["injection_offset_m"])
        self.assertIsNone(lead["monitor_offset_m"])

    def test_an_unknown_key_raises(self):
        lead = return_lead()
        lead["shield"] = "braid"
        with self.assertRaises(ValueError):
            normalize_lead(lead)

    def test_a_missing_key_raises(self):
        lead = return_lead()
        del lead["height_m"]
        with self.assertRaises(ValueError):
            normalize_lead(lead)

    def test_an_unknown_polarity_raises(self):
        with self.assertRaises(ValueError):
            normalize_lead(return_lead(polarity="chassis"))

    def test_a_blank_identifier_raises(self):
        with self.assertRaises(ValueError):
            normalize_lead(return_lead(id=""))

    def test_an_injected_lead_without_an_offset_raises(self):
        lead = high_lead()
        del lead["injection_offset_m"]
        with self.assertRaises(ValueError):
            normalize_lead(lead)

    def test_an_offset_on_a_non_injected_lead_raises(self):
        lead = return_lead(injection_offset_m=0.12)
        with self.assertRaises(ValueError):
            normalize_lead(lead)

    def test_a_non_boolean_injected_flag_raises(self):
        with self.assertRaises(ValueError):
            normalize_lead(return_lead(injected="yes"))

    def test_a_non_mapping_lead_raises(self):
        with self.assertRaises(ValueError):
            normalize_lead("PWR-HI")


class TestAssessBenchSetup(unittest.TestCase):
    def test_a_good_arrangement_is_fit(self):
        report = assess_bench_setup(setup())
        self.assertTrue(report["fit"])
        self.assertEqual(report["verdict"], "setup-fit")
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["injected_lead_count"], 1)
        self.assertAlmostEqual(report["conforming_fraction"], 1.0, places=12)

    def test_a_lead_without_a_stabilization_network_is_reported(self):
        bench = setup(leads=[high_lead(), return_lead(stabilization_network=False)])
        self.assertIn("stabilization-network-missing", codes(assess_bench_setup(bench)))

    def test_a_long_run_is_reported(self):
        bench = setup(leads=[high_lead(run_length_m=4.0), return_lead()])
        self.assertIn("lead-run-out-of-tolerance", codes(assess_bench_setup(bench)))

    def test_a_high_lead_above_the_plane_is_reported(self):
        bench = setup(leads=[high_lead(), return_lead(height_m=0.30)])
        self.assertIn("lead-height-out-of-tolerance", codes(assess_bench_setup(bench)))

    def test_an_injection_outside_the_window_is_reported(self):
        bench = setup(leads=[high_lead(injection_offset_m=0.80), return_lead()])
        self.assertIn(
            "injection-position-outside-window", codes(assess_bench_setup(bench))
        )

    def test_a_distant_monitor_is_reported(self):
        bench = setup(leads=[high_lead(monitor_offset_m=0.90), return_lead()])
        self.assertIn("monitor-too-far-from-injection", codes(assess_bench_setup(bench)))

    def test_a_signal_lead_run_too_close_is_reported(self):
        bench = setup(leads=[high_lead(signal_lead_separation_m=0.005), return_lead()])
        self.assertIn("signal-lead-too-close", codes(assess_bench_setup(bench)))

    def test_no_injected_lead_is_reported(self):
        bench = setup(
            leads=[
                high_lead(
                    injected=False,
                    injection_offset_m=None,
                    monitor_offset_m=None,
                ),
                return_lead(),
            ]
        )
        bench["leads"][0].pop("injection_offset_m")
        bench["leads"][0].pop("monitor_offset_m")
        self.assertIn("no-lead-injected", codes(assess_bench_setup(bench)))

    def test_two_injected_leads_are_reported(self):
        bench = setup(
            leads=[
                high_lead(),
                return_lead(injected=True, injection_offset_m=0.12),
            ]
        )
        report = assess_bench_setup(bench)
        self.assertIn("several-leads-injected", codes(report))
        self.assertIn("return-lead-injected", codes(report))

    def test_a_missing_ground_plane_is_reported(self):
        self.assertIn("ground-plane-missing", codes(assess_bench_setup(setup(ground_plane=False))))

    def test_an_unmeasured_bond_is_reported(self):
        bench = setup()
        del bench["bond_resistance_ohm"]
        self.assertIn("bond-resistance-undeclared", codes(assess_bench_setup(bench)))

    def test_a_high_bond_is_reported(self):
        self.assertIn(
            "bond-resistance-high", codes(assess_bench_setup(setup(bond_resistance_ohm=0.2)))
        )

    def test_a_single_lead_raises(self):
        with self.assertRaises(ValueError):
            assess_bench_setup(setup(leads=[high_lead()]))

    def test_two_high_leads_raise(self):
        with self.assertRaises(ValueError):
            assess_bench_setup(
                setup(leads=[high_lead(), high_lead(id="PWR-HI-2", injected=False)])
            )

    def test_a_duplicate_lead_identifier_raises(self):
        with self.assertRaises(ValueError):
            assess_bench_setup(setup(leads=[high_lead(), return_lead(id="PWR-HI")]))

    def test_an_unknown_setup_key_raises(self):
        bench = setup()
        bench["chamber"] = "anechoic"
        with self.assertRaises(ValueError):
            assess_bench_setup(bench)

    def test_a_string_lead_list_raises(self):
        with self.assertRaises(ValueError):
            assess_bench_setup(setup(leads="PWR-HI"))

    def test_a_non_mapping_setup_raises(self):
        with self.assertRaises(ValueError):
            assess_bench_setup("bench")

    def test_findings_carry_code_subject_and_detail(self):
        bench = setup(bond_resistance_ohm=0.2)
        for finding in assess_bench_setup(bench)["findings"]:
            self.assertEqual(sorted(finding.keys()), ["code", "detail", "subject"])


if __name__ == "__main__":
    unittest.main()
