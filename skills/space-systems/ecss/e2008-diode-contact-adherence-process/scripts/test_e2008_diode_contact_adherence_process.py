"""Contract tests for the clause 9.6.6.2.2 diode adherence run logic."""

import unittest

from e2008_diode_contact_adherence_process_logic import (
    ADHERENCE_CATEGORIES,
    ADHERENT,
    ANODE_TERMINAL,
    ATTACHMENT_SITES,
    BELOW_LIMIT,
    CATHODE_TERMINAL,
    CONDITIONING_DEFICIENT,
    DEFAULT_DIODE_LOADING_POLICY,
    DETACHED,
    DIE_ATTACH,
    LOT_FAILED,
    LOT_NOT_EVALUATED,
    LOT_PASSED,
    RUN_VERDICTS,
    assess_diode_adherence_run,
    categorize_pull_result,
    chamber_pressure_in_band,
    load_completeness,
    sentence_device,
    tray_packing_fraction,
    validate_diode_loading_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_DIODE_LOADING_POLICY)
    policy.update(overrides)
    return policy


def _device(identifier="d1", anode=3.0, cathode=3.0, die=4.0):
    return {
        "id": identifier,
        "sites": {
            ANODE_TERMINAL: anode,
            CATHODE_TERMINAL: cathode,
            DIE_ATTACH: die,
        },
    }


def _chamber(**overrides):
    chamber = {
        "loaded_diode_count": 20,
        "pressure_kpa": 101.3,
        "soak_dwell_h": 24.0,
        "terminal_clearance_mm": 3.0,
        "tray_area_mm2": 40000.0,
        "package_footprint_mm2": 400.0,
    }
    chamber.update(overrides)
    return chamber


def _run(**overrides):
    run = {
        "population": {"diode_count": 20},
        "chamber": _chamber(),
        "devices": [_device("d%d" % n) for n in range(1, 21)],
    }
    run.update(overrides)
    return run


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_diode_loading_policy(DEFAULT_DIODE_LOADING_POLICY),
            DEFAULT_DIODE_LOADING_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_loading_policy("ambient")

    def test_an_inverted_pressure_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_loading_policy(_policy(min_chamber_pressure_kpa=120.0))

    def test_a_detachment_threshold_above_the_pull_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_loading_policy(_policy(detached_load_n=5.0))

    def test_a_packing_cap_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_loading_policy(_policy(max_tray_packing_fraction=1.5))

    def test_every_verdict_and_category_is_declared(self):
        self.assertEqual(len(set(RUN_VERDICTS)), 4)
        self.assertEqual(len(set(ADHERENCE_CATEGORIES)), 3)
        self.assertEqual(len(set(ATTACHMENT_SITES)), 3)


class LoadCompletenessTests(unittest.TestCase):
    def test_a_whole_population_is_complete(self):
        self.assertAlmostEqual(load_completeness(20, 20), 1.0, places=12)

    def test_a_partial_load_reports_its_share(self):
        self.assertAlmostEqual(load_completeness(15, 20), 0.75, places=12)

    def test_more_devices_than_the_population_rejected(self):
        with self.assertRaises(ValueError):
            load_completeness(25, 20)

    def test_a_zero_population_rejected(self):
        with self.assertRaises(ValueError):
            load_completeness(0, 20)


class TrayTests(unittest.TestCase):
    def test_packing_is_the_share_of_the_tray_covered(self):
        fraction = tray_packing_fraction(
            {
                "tray_area_mm2": 1000.0,
                "package_footprint_mm2": 100.0,
                "device_count": 4,
            }
        )
        self.assertAlmostEqual(fraction, 0.4, places=9)

    def test_a_fully_covered_tray_packs_to_one(self):
        fraction = tray_packing_fraction(
            {
                "tray_area_mm2": 400.0,
                "package_footprint_mm2": 100.0,
                "device_count": 4,
            }
        )
        self.assertAlmostEqual(fraction, 1.0, places=9)

    def test_a_load_larger_than_its_tray_rejected(self):
        with self.assertRaises(ValueError):
            tray_packing_fraction(
                {
                    "tray_area_mm2": 300.0,
                    "package_footprint_mm2": 100.0,
                    "device_count": 4,
                }
            )

    def test_a_non_mapping_tray_rejected(self):
        with self.assertRaises(ValueError):
            tray_packing_fraction([1000.0, 100.0, 4])


class PressureBandTests(unittest.TestCase):
    def test_the_ambient_setpoint_sits_in_the_band(self):
        self.assertTrue(chamber_pressure_in_band(101.3, _policy()))

    def test_a_pressure_exactly_on_the_lower_edge_is_in_band(self):
        policy = _policy()
        edge = float(policy["min_chamber_pressure_kpa"])
        self.assertAlmostEqual(edge, policy["min_chamber_pressure_kpa"], places=9)
        self.assertTrue(chamber_pressure_in_band(edge, policy))

    def test_a_pressure_exactly_on_the_upper_edge_is_in_band(self):
        policy = _policy()
        self.assertTrue(
            chamber_pressure_in_band(
                float(policy["max_chamber_pressure_kpa"]), policy
            )
        )

    def test_a_pumped_down_chamber_is_out_of_band(self):
        self.assertFalse(chamber_pressure_in_band(20.0, _policy()))

    def test_zero_pressure_rejected(self):
        with self.assertRaises(ValueError):
            chamber_pressure_in_band(0.0, _policy())


class PullGroupingTests(unittest.TestCase):
    def test_a_strong_reading_is_adherent(self):
        self.assertEqual(categorize_pull_result(5.0, _policy()), ADHERENT)

    def test_a_reading_exactly_at_the_pull_limit_is_adherent(self):
        policy = _policy()
        limit = float(policy["min_pull_load_n"])
        self.assertAlmostEqual(limit, policy["min_pull_load_n"], places=9)
        self.assertEqual(categorize_pull_result(limit, policy), ADHERENT)

    def test_a_weak_reading_is_below_limit(self):
        self.assertEqual(categorize_pull_result(1.0, _policy()), BELOW_LIMIT)

    def test_a_reading_at_the_detachment_threshold_is_detached(self):
        policy = _policy()
        threshold = float(policy["detached_load_n"])
        self.assertEqual(categorize_pull_result(threshold, policy), DETACHED)

    def test_a_zero_reading_is_detached(self):
        self.assertEqual(categorize_pull_result(0.0, _policy()), DETACHED)

    def test_a_negative_reading_rejected(self):
        with self.assertRaises(ValueError):
            categorize_pull_result(-1.0, _policy())


class DeviceSentencingTests(unittest.TestCase):
    def test_a_sound_device_is_adherent(self):
        self.assertEqual(sentence_device(_device())["category"], ADHERENT)

    def test_a_device_is_sentenced_by_its_weakest_site(self):
        self.assertEqual(
            sentence_device(_device(cathode=1.0))["category"], BELOW_LIMIT
        )

    def test_detachment_outranks_a_low_reading_on_the_same_device(self):
        sentence = sentence_device(_device(cathode=1.0, die=0.0))
        self.assertEqual(sentence["category"], DETACHED)

    def test_each_site_keeps_its_own_grouping(self):
        sentence = sentence_device(_device(anode=5.0, cathode=1.0, die=0.0))
        self.assertEqual(sentence["site_categories"][ANODE_TERMINAL], ADHERENT)
        self.assertEqual(sentence["site_categories"][CATHODE_TERMINAL], BELOW_LIMIT)
        self.assertEqual(sentence["site_categories"][DIE_ATTACH], DETACHED)

    def test_a_device_with_no_sites_rejected(self):
        with self.assertRaises(ValueError):
            sentence_device({"id": "d1", "sites": {}})

    def test_an_unrecognised_site_rejected(self):
        with self.assertRaises(ValueError):
            sentence_device({"id": "d1", "sites": {"heat-sink-tab": 3.0}})

    def test_a_non_mapping_device_rejected(self):
        with self.assertRaises(ValueError):
            sentence_device(["d1"])


class RunAssessmentTests(unittest.TestCase):
    def test_a_complete_sound_run_passes_the_lot(self):
        result = assess_diode_adherence_run(_run())
        self.assertEqual(result["verdict"], LOT_PASSED)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["load_completeness"], 1.0, places=12)

    def test_a_partial_load_cannot_sentence_the_lot(self):
        result = assess_diode_adherence_run(
            _run(chamber=_chamber(loaded_diode_count=15))
        )
        self.assertEqual(result["verdict"], LOT_NOT_EVALUATED)
        self.assertAlmostEqual(result["load_completeness"], 0.75, places=12)

    def test_a_partial_load_outranks_a_detached_device(self):
        devices = [_device("d%d" % n) for n in range(1, 20)] + [
            _device("d20", die=0.0)
        ]
        result = assess_diode_adherence_run(
            _run(chamber=_chamber(loaded_diode_count=15), devices=devices)
        )
        self.assertEqual(result["verdict"], LOT_NOT_EVALUATED)

    def test_a_chamber_out_of_band_is_a_conditioning_deficiency(self):
        result = assess_diode_adherence_run(
            _run(chamber=_chamber(pressure_kpa=40.0))
        )
        self.assertEqual(result["verdict"], CONDITIONING_DEFICIENT)
        self.assertFalse(result["pressure_in_band"])

    def test_a_crowded_tray_is_a_conditioning_deficiency(self):
        result = assess_diode_adherence_run(
            _run(chamber=_chamber(tray_area_mm2=9000.0))
        )
        self.assertEqual(result["verdict"], CONDITIONING_DEFICIENT)
        self.assertGreater(result["tray_packing_fraction"], 0.7)

    def test_a_short_dwell_is_a_conditioning_deficiency(self):
        result = assess_diode_adherence_run(
            _run(chamber=_chamber(soak_dwell_h=2.0))
        )
        self.assertEqual(result["verdict"], CONDITIONING_DEFICIENT)

    def test_terminals_too_close_are_a_conditioning_deficiency(self):
        result = assess_diode_adherence_run(
            _run(chamber=_chamber(terminal_clearance_mm=0.5))
        )
        self.assertEqual(result["verdict"], CONDITIONING_DEFICIENT)

    def test_a_dwell_exactly_at_the_floor_is_accepted(self):
        policy = _policy()
        floor = float(policy["min_soak_dwell_h"])
        result = assess_diode_adherence_run(
            _run(chamber=_chamber(soak_dwell_h=floor)), policy
        )
        self.assertEqual(result["verdict"], LOT_PASSED)

    def test_conditioning_outranks_a_failed_reject_fraction(self):
        devices = [_device("d%d" % n) for n in range(1, 18)] + [
            _device("d18", anode=1.0),
            _device("d19", anode=1.0),
            _device("d20", anode=1.0),
        ]
        result = assess_diode_adherence_run(
            _run(chamber=_chamber(pressure_kpa=40.0), devices=devices)
        )
        self.assertEqual(result["verdict"], CONDITIONING_DEFICIENT)

    def test_one_detached_device_fails_the_lot_outright(self):
        devices = [_device("d%d" % n) for n in range(1, 20)] + [
            _device("d20", die=0.0)
        ]
        result = assess_diode_adherence_run(_run(devices=devices))
        self.assertEqual(result["verdict"], LOT_FAILED)
        self.assertEqual(result["detached_devices"], 1)

    def test_a_reject_fraction_over_the_cap_fails_the_lot(self):
        devices = [_device("d%d" % n) for n in range(1, 18)] + [
            _device("d18", anode=1.0),
            _device("d19", anode=1.0),
            _device("d20", anode=1.0),
        ]
        result = assess_diode_adherence_run(_run(devices=devices))
        self.assertEqual(result["verdict"], LOT_FAILED)
        self.assertAlmostEqual(result["reject_fraction"], 0.15, places=12)

    def test_a_reject_fraction_exactly_at_the_cap_passes(self):
        policy = _policy(max_reject_fraction=0.05)
        devices = [_device("d%d" % n) for n in range(1, 20)] + [
            _device("d20", anode=1.0)
        ]
        result = assess_diode_adherence_run(_run(devices=devices), policy)
        self.assertAlmostEqual(
            result["reject_fraction"], policy["max_reject_fraction"], places=9
        )
        self.assertEqual(result["verdict"], LOT_PASSED)

    def test_every_device_is_sentenced(self):
        result = assess_diode_adherence_run(_run())
        self.assertEqual(len(result["sentences"]), 20)

    def test_missing_population_block_rejected(self):
        run = _run()
        del run["population"]
        with self.assertRaises(ValueError):
            assess_diode_adherence_run(run)

    def test_missing_chamber_block_rejected(self):
        run = _run()
        del run["chamber"]
        with self.assertRaises(ValueError):
            assess_diode_adherence_run(run)

    def test_an_empty_device_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_adherence_run(_run(devices=[]))

    def test_non_mapping_run_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_adherence_run(["population"])

    def test_a_negative_soak_dwell_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_adherence_run(_run(chamber=_chamber(soak_dwell_h=-1.0)))


if __name__ == "__main__":
    unittest.main()
