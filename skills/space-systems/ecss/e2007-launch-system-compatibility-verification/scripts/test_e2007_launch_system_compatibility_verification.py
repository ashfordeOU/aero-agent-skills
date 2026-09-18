#!/usr/bin/env python3
"""Gate 3 contract test for e2007-launch-system-compatibility-verification.

Stdlib unittest, offline, deterministic.
"""

import unittest

import e2007_launch_system_compatibility_verification_logic as logic


WINDOW = {"liftoff_s": 0.0, "separation_s": 1800.0}


def unpowered_unit(unit_id="transponder"):
    return {
        "id": unit_id,
        "phases": [{"start_s": 0.0, "end_s": 1800.0, "state": "unpowered"}],
    }


def launch_config(**overrides):
    cfg = {
        "ascent_window": {"liftoff_s": 0.0, "separation_s": 1800.0},
        "units": [
            unpowered_unit("transponder"),
            unpowered_unit("obc"),
            unpowered_unit("separation-electronics"),
        ],
    }
    cfg.update(overrides)
    return cfg


class TestPowerStateCategorization(unittest.TestCase):
    def test_canonical_state_is_returned(self):
        self.assertEqual(logic.power_state_kind("unpowered"), logic.STATE_UNPOWERED)

    def test_off_alias_resolves_to_unpowered(self):
        self.assertEqual(logic.power_state_kind("OFF"), logic.STATE_UNPOWERED)

    def test_survival_heater_alias_resolves_to_passive(self):
        self.assertEqual(logic.power_state_kind("survival-heater"), logic.STATE_PASSIVE)

    def test_beacon_alias_resolves_to_rf_transmitting(self):
        self.assertEqual(logic.power_state_kind("beacon-on"), logic.STATE_RF)

    def test_blank_state_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.power_state_kind("   ")

    def test_unknown_state_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.power_state_kind("partially-warm")

    def test_only_unpowered_permits_the_waiver(self):
        self.assertTrue(logic.state_permits_waiver("no-power"))
        self.assertFalse(logic.state_permits_waiver("thermostat-heater"))
        self.assertFalse(logic.state_permits_waiver("bus-powered"))


class TestAscentWindow(unittest.TestCase):
    def test_window_is_normalized(self):
        window = logic.normalize_ascent_window({"liftoff_s": 0, "separation_s": 60})
        self.assertAlmostEqual(window["separation_s"], 60.0, places=9)

    def test_window_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.normalize_ascent_window([0.0, 1800.0])

    def test_separation_before_liftoff_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_ascent_window({"liftoff_s": 10.0, "separation_s": 5.0})

    def test_zero_length_window_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_ascent_window({"liftoff_s": 7.0, "separation_s": 7.0})

    def test_non_numeric_liftoff_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_ascent_window({"liftoff_s": "T0", "separation_s": 60.0})


class TestIntervalAlgebra(unittest.TestCase):
    def test_interval_is_clipped_to_the_window(self):
        clipped = logic.clip_interval_to_window(-100.0, 400.0, WINDOW)
        self.assertAlmostEqual(clipped[0], 0.0, places=9)
        self.assertAlmostEqual(clipped[1], 400.0, places=9)

    def test_interval_entirely_outside_the_window_is_dropped(self):
        self.assertIsNone(logic.clip_interval_to_window(2000.0, 2400.0, WINDOW))

    def test_inverted_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.clip_interval_to_window(500.0, 100.0, WINDOW)

    def test_overlapping_intervals_merge_into_one_span(self):
        merged = logic.merge_intervals([(0.0, 100.0), (50.0, 200.0)])
        self.assertEqual(len(merged), 1)
        self.assertAlmostEqual(merged[0][1], 200.0, places=9)

    def test_abutting_intervals_merge_without_a_spurious_gap(self):
        merged = logic.merge_intervals([(0.0, 900.0), (900.0, 1800.0)])
        self.assertEqual(len(merged), 1)

    def test_disjoint_intervals_stay_separate(self):
        merged = logic.merge_intervals([(0.0, 100.0), (200.0, 300.0)])
        self.assertEqual(len(merged), 2)

    def test_malformed_interval_pair_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.merge_intervals([(0.0, 100.0, 200.0)])

    def test_gap_in_the_middle_of_the_window_is_reported(self):
        gaps = logic.uncovered_gaps([(0.0, 600.0), (1200.0, 1800.0)], WINDOW)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0][0], 600.0, places=9)
        self.assertAlmostEqual(gaps[0][1], 1200.0, places=9)

    def test_full_coverage_reports_no_gap(self):
        self.assertEqual(logic.uncovered_gaps([(0.0, 1800.0)], WINDOW), ())

    def test_trailing_gap_is_reported(self):
        gaps = logic.uncovered_gaps([(0.0, 1500.0)], WINDOW)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0][1], 1800.0, places=9)

    def test_overlaps_are_counted_once_in_the_duration(self):
        self.assertAlmostEqual(
            logic.total_duration_s([(0.0, 100.0), (50.0, 150.0)]), 150.0, places=9
        )


class TestUnitRecords(unittest.TestCase):
    def test_unit_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.normalize_unit(["transponder"], WINDOW)

    def test_unit_without_an_id_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_unit({"id": "  ", "phases": []}, WINDOW)

    def test_unit_without_phases_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_unit({"id": "obc", "phases": []}, WINDOW)

    def test_unit_whose_phases_all_fall_outside_the_window_is_rejected(self):
        unit = {
            "id": "obc",
            "phases": [{"start_s": 3000.0, "end_s": 3600.0, "state": "unpowered"}],
        }
        with self.assertRaises(ValueError):
            logic.normalize_unit(unit, WINDOW)

    def test_partial_declaration_leaves_a_coverage_gap(self):
        unit = logic.normalize_unit(
            {
                "id": "obc",
                "phases": [{"start_s": 0.0, "end_s": 900.0, "state": "unpowered"}],
            },
            WINDOW,
        )
        self.assertEqual(len(logic.unit_coverage_gaps(unit, WINDOW)), 1)

    def test_unpowered_unit_has_no_powered_interval(self):
        unit = logic.normalize_unit(unpowered_unit(), WINDOW)
        self.assertEqual(logic.unit_powered_intervals(unit), ())
        self.assertAlmostEqual(logic.unit_powered_duration_s(unit), 0.0, places=9)

    def test_heater_phase_is_counted_as_powered_time(self):
        unit = logic.normalize_unit(
            {
                "id": "battery",
                "phases": [
                    {"start_s": 0.0, "end_s": 600.0, "state": "unpowered"},
                    {"start_s": 600.0, "end_s": 900.0, "state": "survival-heater"},
                    {"start_s": 900.0, "end_s": 1800.0, "state": "unpowered"},
                ],
            },
            WINDOW,
        )
        self.assertAlmostEqual(logic.unit_powered_duration_s(unit), 300.0, places=9)
        self.assertIn(logic.STATE_PASSIVE, logic.unit_states(unit))


class TestWaiver(unittest.TestCase):
    def test_waiver_is_granted_when_every_unit_stays_unpowered(self):
        result = logic.waiver_assessment(launch_config()["units"], WINDOW)
        self.assertTrue(result["granted"])
        self.assertEqual(result["reasons"], ())

    def test_waiver_is_refused_when_one_unit_transmits(self):
        units = launch_config()["units"] + [
            {
                "id": "beacon",
                "phases": [{"start_s": 0.0, "end_s": 1800.0, "state": "beacon-on"}],
            }
        ]
        result = logic.waiver_assessment(units, WINDOW)
        self.assertFalse(result["granted"])
        self.assertIn("beacon", result["powered_units"])

    def test_waiver_is_refused_on_an_incomplete_declaration(self):
        units = [
            {
                "id": "obc",
                "phases": [{"start_s": 0.0, "end_s": 900.0, "state": "unpowered"}],
            }
        ]
        result = logic.waiver_assessment(units, WINDOW)
        self.assertFalse(result["granted"])
        self.assertIn("obc", result["uncovered_units"])

    def test_empty_unit_list_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.waiver_assessment([], WINDOW)

    def test_powered_duration_sums_across_units(self):
        units = [
            {
                "id": "a",
                "phases": [
                    {"start_s": 0.0, "end_s": 1700.0, "state": "unpowered"},
                    {"start_s": 1700.0, "end_s": 1800.0, "state": "bus-powered"},
                ],
            },
            {
                "id": "b",
                "phases": [
                    {"start_s": 0.0, "end_s": 1600.0, "state": "unpowered"},
                    {"start_s": 1600.0, "end_s": 1800.0, "state": "bus-powered"},
                ],
            },
        ]
        result = logic.waiver_assessment(units, WINDOW)
        self.assertAlmostEqual(result["powered_duration_s"], 300.0, places=9)


class TestVerificationMethods(unittest.TestCase):
    def test_unpowered_state_owes_inspection_only(self):
        self.assertEqual(
            logic.required_verification_methods(["unpowered"]), ("inspection",)
        )

    def test_transmitting_state_owes_a_test(self):
        self.assertIn("test", logic.required_verification_methods(["beacon-on"]))

    def test_passive_state_owes_analysis_and_test(self):
        methods = logic.required_verification_methods(["survival-heater"])
        self.assertEqual(methods, ("analysis", "test"))

    def test_methods_are_returned_in_canonical_order(self):
        methods = logic.required_verification_methods(
            ["bus-powered", "unpowered", "survival-heater"]
        )
        self.assertEqual(methods, ("inspection", "analysis", "test"))

    def test_method_request_must_be_a_collection(self):
        with self.assertRaises(ValueError):
            logic.required_verification_methods("unpowered")


class TestEmissionMargin(unittest.TestCase):
    def test_margin_is_the_limit_less_the_emission(self):
        self.assertAlmostEqual(
            logic.radiated_emission_margin_db(34.0, 40.0), 6.0, places=9
        )

    def test_negative_margin_when_emission_exceeds_the_limit(self):
        self.assertAlmostEqual(
            logic.radiated_emission_margin_db(46.0, 40.0), -6.0, places=9
        )

    def test_exact_equality_at_the_required_margin_passes(self):
        margin = logic.radiated_emission_margin_db(34.0, 40.0)
        self.assertAlmostEqual(margin, 6.0, places=9)
        self.assertTrue(logic.meets_required_margin_db(margin, 6.0))

    def test_margin_below_the_requirement_fails(self):
        self.assertFalse(logic.meets_required_margin_db(3.0, 6.0))

    def test_negative_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.meets_required_margin_db(6.0, 6.0, tolerance=-1.0)

    def test_non_numeric_emission_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.radiated_emission_margin_db("34 dB", 40.0)


class TestTopLevelVerification(unittest.TestCase):
    def test_unpowered_ascent_grants_the_waiver_and_closes_clean(self):
        report = logic.verify_launch_system_compatibility(launch_config())
        self.assertTrue(report["waiver_granted"])
        self.assertTrue(report["acceptable"])
        self.assertEqual(report["required_methods"], ("inspection",))
        self.assertIsNone(report["emission_margin_db"])

    def test_ascent_duration_is_reported(self):
        report = logic.verify_launch_system_compatibility(launch_config())
        self.assertAlmostEqual(report["ascent_duration_s"], 1800.0, places=9)

    def test_powered_unit_refuses_the_waiver_and_sizes_the_margin(self):
        cfg = launch_config()
        cfg["units"] = cfg["units"] + [
            {
                "id": "beacon",
                "phases": [{"start_s": 0.0, "end_s": 1800.0, "state": "beacon-on"}],
            }
        ]
        cfg["emission"] = {
            "emission_dbuv_per_m": 34.0,
            "launcher_limit_dbuv_per_m": 40.0,
            "required_margin_db": 6.0,
        }
        report = logic.verify_launch_system_compatibility(cfg)
        self.assertFalse(report["waiver_granted"])
        self.assertTrue(report["margin_ok"])
        self.assertIn("test", report["required_methods"])
        self.assertTrue(
            any(f.startswith("unit-powered-during-ascent") for f in report["findings"])
        )

    def test_margin_shortfall_is_a_finding(self):
        cfg = launch_config()
        cfg["units"] = cfg["units"] + [
            {
                "id": "beacon",
                "phases": [{"start_s": 0.0, "end_s": 1800.0, "state": "beacon-on"}],
            }
        ]
        cfg["emission"] = {
            "emission_dbuv_per_m": 39.0,
            "launcher_limit_dbuv_per_m": 40.0,
            "required_margin_db": 6.0,
        }
        report = logic.verify_launch_system_compatibility(cfg)
        self.assertIn("launcher-emission-margin-shortfall", report["findings"])
        self.assertFalse(report["acceptable"])

    def test_refused_waiver_without_an_emission_record_is_rejected(self):
        cfg = launch_config()
        cfg["units"] = cfg["units"] + [
            {
                "id": "beacon",
                "phases": [{"start_s": 0.0, "end_s": 1800.0, "state": "beacon-on"}],
            }
        ]
        with self.assertRaises(ValueError):
            logic.verify_launch_system_compatibility(cfg)

    def test_configuration_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.verify_launch_system_compatibility("ariane-6")

    def test_coverage_gap_alone_blocks_the_waiver(self):
        cfg = launch_config()
        cfg["units"] = [
            {
                "id": "obc",
                "phases": [{"start_s": 0.0, "end_s": 900.0, "state": "unpowered"}],
            }
        ]
        cfg["emission"] = {
            "emission_dbuv_per_m": 34.0,
            "launcher_limit_dbuv_per_m": 40.0,
            "required_margin_db": 6.0,
        }
        report = logic.verify_launch_system_compatibility(cfg)
        self.assertFalse(report["waiver_granted"])
        self.assertIn("ascent-coverage-incomplete:obc", report["findings"])


if __name__ == "__main__":
    unittest.main()
