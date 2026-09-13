#!/usr/bin/env python3
"""Gate 3 contract test for e2007-launch-phase-receiver-overload.

Stdlib unittest, offline, deterministic.
"""

import unittest

import e2007_launch_phase_receiver_overload_logic as logic


def receiver_record(**overrides):
    rec = {
        "id": "rx-tt-and-c",
        "center_frequency_mhz": 2200.0,
        "bandwidth_mhz": 40.0,
        "gain_dbi": 0.0,
        "overload_threshold_dbm": -20.0,
        "damage_threshold_dbm": 10.0,
        "required_margin_db": 6.0,
    }
    rec.update(overrides)
    return rec


def radar_record(**overrides):
    rec = {
        "id": "range-radar",
        "frequency_mhz": 5600.0,
        "field_strength_v_per_m": 200.0,
        "phases": ["prelaunch", "liftoff", "ascent"],
    }
    rec.update(overrides)
    return rec


def pad_link_record(**overrides):
    rec = {
        "id": "pad-telemetry",
        "frequency_mhz": 2205.0,
        "field_strength_v_per_m": 0.2,
        "phases": ["prelaunch", "liftoff", "ascent"],
    }
    rec.update(overrides)
    return rec


class TestUnitConversions(unittest.TestCase):
    def test_one_milliwatt_is_zero_dbm(self):
        self.assertAlmostEqual(logic.watts_to_dbm(0.001), 0.0, places=12)

    def test_dbm_to_watts_round_trip(self):
        self.assertAlmostEqual(logic.dbm_to_watts(30.0), 1.0, places=12)
        self.assertAlmostEqual(
            logic.watts_to_dbm(logic.dbm_to_watts(-17.5)), -17.5, places=9
        )

    def test_zero_watts_has_no_dbm_value(self):
        with self.assertRaises(ValueError):
            logic.watts_to_dbm(0.0)

    def test_negative_watts_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.watts_to_dbm(-0.5)

    def test_non_numeric_level_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.dbm_to_watts("-20 dBm")

    def test_power_density_of_unit_field(self):
        self.assertAlmostEqual(
            logic.power_density_w_per_m2(1.0), 0.0026544187, places=10
        )

    def test_power_density_scales_with_field_squared(self):
        self.assertAlmostEqual(
            logic.power_density_w_per_m2(2.0),
            4.0 * logic.power_density_w_per_m2(1.0),
            places=10,
        )

    def test_zero_field_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.power_density_w_per_m2(0.0)

    def test_negative_field_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.power_density_w_per_m2(-10.0)

    def test_wavelength_at_three_hundred_megahertz(self):
        self.assertAlmostEqual(logic.wavelength_m(300.0), 0.9993081933, places=9)

    def test_zero_frequency_has_no_wavelength(self):
        with self.assertRaises(ValueError):
            logic.wavelength_m(0.0)

    def test_effective_aperture_of_isotropic_antenna(self):
        self.assertAlmostEqual(
            logic.effective_aperture_m2(300.0, 0.0), 0.0794674052, places=9
        )

    def test_effective_aperture_doubles_for_three_decibels_of_gain(self):
        base = logic.effective_aperture_m2(2200.0, 0.0)
        with_gain = logic.effective_aperture_m2(2200.0, 3.0102999566)
        self.assertAlmostEqual(with_gain / base, 2.0, places=8)

    def test_effective_aperture_rejects_negative_frequency(self):
        with self.assertRaises(ValueError):
            logic.effective_aperture_m2(-2200.0, 0.0)

    def test_effective_aperture_rejects_non_numeric_gain(self):
        with self.assertRaises(ValueError):
            logic.effective_aperture_m2(2200.0, "high")


class TestEmitterNormalization(unittest.TestCase):
    def test_emitter_happy_path(self):
        got = logic.normalize_emitter(radar_record())
        self.assertEqual(got["id"], "range-radar")
        self.assertEqual(got["phases"], ("prelaunch", "liftoff", "ascent"))

    def test_emitter_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.normalize_emitter(["range-radar"])

    def test_emitter_needs_a_non_blank_id(self):
        with self.assertRaises(ValueError):
            logic.normalize_emitter(radar_record(id="  "))

    def test_emitter_frequency_must_be_positive(self):
        with self.assertRaises(ValueError):
            logic.normalize_emitter(radar_record(frequency_mhz=0.0))

    def test_emitter_field_strength_must_be_positive(self):
        with self.assertRaises(ValueError):
            logic.normalize_emitter(radar_record(field_strength_v_per_m=-1.0))

    def test_emitter_needs_a_phase_list(self):
        with self.assertRaises(ValueError):
            logic.normalize_emitter(radar_record(phases="prelaunch"))

    def test_unrecognised_phase_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_emitter(radar_record(phases=["on-orbit"]))

    def test_emitter_with_no_phase_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_emitter(radar_record(phases=[]))

    def test_duplicate_phases_are_collapsed(self):
        got = logic.normalize_emitter(radar_record(phases=["ascent", "ascent"]))
        self.assertEqual(got["phases"], ("ascent",))


class TestReceiverNormalization(unittest.TestCase):
    def test_receiver_defaults_are_applied(self):
        got = logic.normalize_receiver(receiver_record())
        self.assertAlmostEqual(
            got["rejection_slope_db_per_octave"],
            logic.DEFAULT_REJECTION_SLOPE_DB_PER_OCTAVE,
            places=12,
        )
        self.assertAlmostEqual(
            got["max_rejection_db"], logic.DEFAULT_MAX_REJECTION_DB, places=12
        )

    def test_receiver_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.normalize_receiver("rx-1")

    def test_receiver_needs_a_non_blank_id(self):
        with self.assertRaises(ValueError):
            logic.normalize_receiver(receiver_record(id=""))

    def test_receiver_bandwidth_must_be_positive(self):
        with self.assertRaises(ValueError):
            logic.normalize_receiver(receiver_record(bandwidth_mhz=0.0))

    def test_receiver_centre_frequency_must_be_positive(self):
        with self.assertRaises(ValueError):
            logic.normalize_receiver(receiver_record(center_frequency_mhz=-2200.0))

    def test_damage_threshold_below_overload_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_receiver(
                receiver_record(overload_threshold_dbm=0.0, damage_threshold_dbm=-30.0)
            )

    def test_equal_thresholds_are_accepted(self):
        got = logic.normalize_receiver(
            receiver_record(overload_threshold_dbm=-10.0, damage_threshold_dbm=-10.0)
        )
        self.assertAlmostEqual(got["damage_threshold_dbm"], -10.0, places=12)

    def test_negative_required_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_receiver(receiver_record(required_margin_db=-3.0))

    def test_negative_rejection_slope_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_receiver(
                receiver_record(rejection_slope_db_per_octave=-20.0)
            )

    def test_negative_maximum_rejection_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_receiver(receiver_record(max_rejection_db=-60.0))

    def test_non_numeric_gain_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_receiver(receiver_record(gain_dbi=None))


class TestFairingAndSelectivity(unittest.TestCase):
    def setUp(self):
        self.rx = logic.normalize_receiver(receiver_record())

    def test_enclosed_configuration_credits_the_shielding(self):
        self.assertAlmostEqual(
            logic.fairing_attenuation_db(logic.CONFIG_ENCLOSED, 30.0), 30.0, places=12
        )

    def test_jettisoned_configuration_credits_nothing(self):
        self.assertAlmostEqual(
            logic.fairing_attenuation_db(logic.CONFIG_JETTISONED, 30.0), 0.0, places=12
        )

    def test_unknown_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.fairing_attenuation_db("fairing-half-open", 30.0)

    def test_negative_shielding_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.fairing_attenuation_db(logic.CONFIG_ENCLOSED, -10.0)

    def test_in_band_emitter_is_not_rejected(self):
        self.assertAlmostEqual(
            logic.front_end_rejection_db(2205.0, self.rx), 0.0, places=12
        )

    def test_passband_edge_is_not_rejected(self):
        self.assertAlmostEqual(
            logic.front_end_rejection_db(2220.0, self.rx), 0.0, places=12
        )

    def test_out_of_band_emitter_follows_the_slope(self):
        self.assertAlmostEqual(
            logic.front_end_rejection_db(2260.0, self.rx), 31.6992500144, places=8
        )

    def test_far_out_of_band_emitter_saturates_at_the_floor(self):
        self.assertAlmostEqual(
            logic.front_end_rejection_db(5600.0, self.rx),
            logic.DEFAULT_MAX_REJECTION_DB,
            places=12,
        )

    def test_rejection_rejects_a_non_positive_frequency(self):
        with self.assertRaises(ValueError):
            logic.front_end_rejection_db(0.0, self.rx)


class TestCoupling(unittest.TestCase):
    def setUp(self):
        self.rx = logic.normalize_receiver(receiver_record())
        self.in_band = logic.normalize_emitter(
            {
                "id": "in-band-source",
                "frequency_mhz": 2200.0,
                "field_strength_v_per_m": 10.0,
                "phases": ["ascent"],
            }
        )

    def test_coupled_level_without_a_fairing(self):
        level = logic.coupled_power_dbm(
            self.in_band, self.rx, logic.CONFIG_JETTISONED, 30.0
        )
        self.assertAlmostEqual(level, -4.0644438700, places=7)

    def test_fairing_removes_exactly_its_shielding(self):
        open_level = logic.coupled_power_dbm(
            self.in_band, self.rx, logic.CONFIG_JETTISONED, 30.0
        )
        closed_level = logic.coupled_power_dbm(
            self.in_band, self.rx, logic.CONFIG_ENCLOSED, 30.0
        )
        self.assertAlmostEqual(open_level - closed_level, 30.0, places=9)

    def test_two_equal_levels_add_three_decibels(self):
        self.assertAlmostEqual(logic.aggregate_dbm([0.0, 0.0]), 3.0102999566, places=9)

    def test_aggregate_is_dominated_by_the_strongest_contributor(self):
        total = logic.aggregate_dbm([0.0, -40.0])
        self.assertAlmostEqual(total, 0.0004342, places=6)

    def test_aggregate_rejects_an_empty_list(self):
        with self.assertRaises(ValueError):
            logic.aggregate_dbm([])

    def test_aggregate_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            logic.aggregate_dbm(-20.0)


class TestMargin(unittest.TestCase):
    def test_exactly_met_margin_passes(self):
        self.assertTrue(logic.meets_margin(6.0, 6.0))

    def test_margin_absorbs_last_place_error(self):
        required = 6.0
        achieved = required - 5e-13
        self.assertLess(achieved, required)
        self.assertTrue(logic.meets_margin(achieved, required))

    def test_real_shortfall_is_not_absorbed(self):
        self.assertFalse(logic.meets_margin(5.9, 6.0))

    def test_negative_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.meets_margin(6.0, 6.0, tolerance=-1e-9)

    def test_non_numeric_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.meets_margin("6 dB", 6.0)


class TestCaseEvaluation(unittest.TestCase):
    def setUp(self):
        self.rx = logic.normalize_receiver(receiver_record())
        self.emitters = [
            logic.normalize_emitter(radar_record()),
            logic.normalize_emitter(pad_link_record()),
            logic.normalize_emitter(
                {
                    "id": "launcher-transponder",
                    "frequency_mhz": 2250.0,
                    "field_strength_v_per_m": 5.0,
                    "phases": ["liftoff", "ascent"],
                }
            ),
        ]

    def test_emitters_in_phase_filters_the_inventory(self):
        selected = logic.emitters_in_phase(self.emitters, "prelaunch")
        self.assertEqual(len(selected), 2)
        self.assertNotIn(
            "launcher-transponder", [e["id"] for e in selected]
        )

    def test_emitters_in_phase_rejects_an_unknown_phase(self):
        with self.assertRaises(ValueError):
            logic.emitters_in_phase(self.emitters, "separation")

    def test_case_evaluation_reports_the_driving_emitter(self):
        case = logic.evaluate_receiver_case(
            self.rx, self.emitters, "ascent", logic.CONFIG_JETTISONED, 30.0
        )
        self.assertEqual(case["driving_emitter"], "launcher-transponder")
        self.assertEqual(len(case["contributions"]), 3)

    def test_jettisoned_configuration_is_the_harsher_case(self):
        enclosed = logic.evaluate_receiver_case(
            self.rx, self.emitters, "ascent", logic.CONFIG_ENCLOSED, 30.0
        )
        jettisoned = logic.evaluate_receiver_case(
            self.rx, self.emitters, "ascent", logic.CONFIG_JETTISONED, 30.0
        )
        self.assertGreater(jettisoned["port_level_dbm"], enclosed["port_level_dbm"])
        self.assertAlmostEqual(
            jettisoned["port_level_dbm"] - enclosed["port_level_dbm"], 30.0, places=9
        )

    def test_case_evaluation_rejects_a_phase_with_no_emitter(self):
        quiet = [
            logic.normalize_emitter(radar_record(phases=["ascent"])),
        ]
        with self.assertRaises(ValueError):
            logic.evaluate_receiver_case(
                self.rx, quiet, "prelaunch", logic.CONFIG_ENCLOSED, 30.0
            )

    def test_benign_environment_passes_both_margins(self):
        quiet = [logic.normalize_emitter(pad_link_record())]
        case = logic.evaluate_receiver_case(
            self.rx, quiet, "ascent", logic.CONFIG_JETTISONED, 30.0
        )
        self.assertTrue(case["overload_ok"])
        self.assertTrue(case["damage_ok"])
        self.assertGreater(case["overload_margin_db"], 6.0)


class TestCampaignAssessment(unittest.TestCase):
    def test_benign_campaign_is_demonstrated(self):
        report = logic.assess_launch_campaign(
            [receiver_record()], [pad_link_record()], 30.0
        )
        self.assertTrue(report["demonstrated"])
        self.assertEqual(report["findings"], ())
        self.assertEqual(len(report["cases"]), len(logic.REQUIRED_CASES))

    def test_every_required_pair_is_covered(self):
        report = logic.assess_launch_campaign(
            [receiver_record()], [pad_link_record()], 30.0
        )
        covered = set((c["phase"], c["configuration"]) for c in report["cases"])
        self.assertEqual(covered, set(logic.REQUIRED_CASES))

    def test_strong_in_band_source_breaks_the_overload_margin(self):
        hot = pad_link_record(field_strength_v_per_m=20.0)
        report = logic.assess_launch_campaign([receiver_record()], [hot], 30.0)
        self.assertFalse(report["demonstrated"])
        self.assertTrue(
            any(f.startswith("overload-margin-shortfall:") for f in report["findings"])
        )

    def test_damage_shortfall_is_reported_separately(self):
        hot = pad_link_record(field_strength_v_per_m=200.0)
        report = logic.assess_launch_campaign(
            [receiver_record(damage_threshold_dbm=0.0)], [hot], 30.0
        )
        self.assertTrue(
            any(f.startswith("damage-margin-shortfall:") for f in report["findings"])
        )

    def test_phase_with_no_declared_emitter_is_a_finding(self):
        report = logic.assess_launch_campaign(
            [receiver_record()], [pad_link_record(phases=["ascent"])], 30.0
        )
        self.assertFalse(report["demonstrated"])
        self.assertIn("no-emitter-environment-declared:prelaunch", report["findings"])
        self.assertIn("no-emitter-environment-declared:liftoff", report["findings"])

    def test_fairing_shielding_can_rescue_the_enclosed_phases_only(self):
        hot = pad_link_record(field_strength_v_per_m=20.0)
        report = logic.assess_launch_campaign([receiver_record()], [hot], 60.0)
        shortfalls = [
            f for f in report["findings"] if f.startswith("overload-margin-shortfall:")
        ]
        self.assertEqual(len(shortfalls), 1)
        self.assertTrue(shortfalls[0].endswith(logic.CONFIG_JETTISONED))

    def test_campaign_needs_at_least_one_receiver(self):
        with self.assertRaises(ValueError):
            logic.assess_launch_campaign([], [pad_link_record()], 30.0)

    def test_campaign_rejects_a_non_sequence_emitter_inventory(self):
        with self.assertRaises(ValueError):
            logic.assess_launch_campaign([receiver_record()], pad_link_record(), 30.0)


if __name__ == "__main__":
    unittest.main()
