"""Contract tests for the clause 12.6.6 planar contact adherence logic."""

import unittest

from e2008_blocking_diode_contact_adherence_logic import (
    ADHERENCE_CATEGORIES,
    ADHERENT,
    ANODE_PAD,
    BELOW_LIMIT,
    BONDED_PADS,
    CATHODE_PAD,
    DEFAULT_ADHERENCE_POLICY,
    FIXTURE_DEFICIENT,
    LIFTED,
    LOT_ACCEPTED,
    LOT_REJECTED,
    NORMAL_PULL_ANGLE_DEG,
    RUN_VERDICTS,
    SAMPLE_INSUFFICIENT,
    assess_contact_adherence_run,
    categorize_pad_adherence,
    contact_stress_n_per_mm2,
    fixture_is_conforming,
    pull_angle_deviation_deg,
    required_sample_size,
    sentence_planar_device,
    validate_adherence_policy,
)

PAD_AREA_MM2 = 2.25


def _policy(**overrides):
    policy = dict(DEFAULT_ADHERENCE_POLICY)
    policy.update(overrides)
    return policy


def _device(identifier="d1", anode=6.0, cathode=6.0):
    return {
        "id": identifier,
        "pads": {
            ANODE_PAD: {"pull_load_n": anode, "pad_area_mm2": PAD_AREA_MM2},
            CATHODE_PAD: {"pull_load_n": cathode, "pad_area_mm2": PAD_AREA_MM2},
        },
    }


def _fixture(**overrides):
    fixture = {
        "pull_angle_deg": 90.0,
        "crosshead_rate_mm_per_min": 2.0,
    }
    fixture.update(overrides)
    return fixture


def _run(**overrides):
    run = {
        "lot": {"diode_count": 200},
        "fixture": _fixture(),
        "devices": [_device("d%d" % n) for n in range(1, 21)],
    }
    run.update(overrides)
    return run


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_adherence_policy(DEFAULT_ADHERENCE_POLICY),
            DEFAULT_ADHERENCE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_adherence_policy("planar")

    def test_a_lift_off_threshold_above_the_adherence_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_adherence_policy(_policy(lift_off_stress_n_per_mm2=9.0))

    def test_an_angle_tolerance_that_allows_a_shear_rejected(self):
        with self.assertRaises(ValueError):
            validate_adherence_policy(_policy(max_pull_angle_deviation_deg=120.0))

    def test_an_inverted_crosshead_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_adherence_policy(_policy(min_crosshead_rate_mm_per_min=40.0))

    def test_a_sample_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_adherence_policy(_policy(sample_fraction=1.6))

    def test_every_verdict_pad_and_category_is_declared(self):
        self.assertEqual(len(set(RUN_VERDICTS)), 4)
        self.assertEqual(len(set(ADHERENCE_CATEGORIES)), 3)
        self.assertEqual(len(set(BONDED_PADS)), 2)


class SampleSizeTests(unittest.TestCase):
    def test_a_large_lot_owes_its_declared_share(self):
        self.assertEqual(required_sample_size(200), 20)

    def test_a_small_lot_is_held_to_the_floor_not_the_share(self):
        self.assertEqual(required_sample_size(30), 5)

    def test_a_lot_smaller_than_the_floor_owes_all_of_itself(self):
        self.assertEqual(required_sample_size(3), 3)

    def test_a_fractional_share_rounds_up_never_down(self):
        self.assertEqual(required_sample_size(155), 16)

    def test_a_zero_lot_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_size(0)

    def test_a_non_integer_lot_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_size(200.5)


class StressTests(unittest.TestCase):
    def test_stress_is_the_load_over_the_bonded_area(self):
        self.assertAlmostEqual(
            contact_stress_n_per_mm2(9.0, PAD_AREA_MM2), 4.0, places=9
        )

    def test_a_bigger_pad_holding_the_same_load_reads_lower(self):
        small = contact_stress_n_per_mm2(6.0, 1.0)
        large = contact_stress_n_per_mm2(6.0, 4.0)
        self.assertGreater(small, large)

    def test_a_zero_load_is_zero_stress(self):
        self.assertAlmostEqual(contact_stress_n_per_mm2(0.0, 2.0), 0.0, places=12)

    def test_a_zero_pad_area_rejected(self):
        with self.assertRaises(ValueError):
            contact_stress_n_per_mm2(6.0, 0.0)

    def test_a_negative_load_rejected(self):
        with self.assertRaises(ValueError):
            contact_stress_n_per_mm2(-6.0, 2.0)


class FixtureTests(unittest.TestCase):
    def test_a_normal_pull_has_no_deviation(self):
        self.assertAlmostEqual(
            pull_angle_deviation_deg(NORMAL_PULL_ANGLE_DEG), 0.0, places=12
        )

    def test_deviation_is_unsigned_either_side_of_normal(self):
        self.assertAlmostEqual(pull_angle_deviation_deg(80.0), 10.0, places=9)
        self.assertAlmostEqual(pull_angle_deviation_deg(100.0), 10.0, places=9)

    def test_an_angle_beyond_a_half_turn_rejected(self):
        with self.assertRaises(ValueError):
            pull_angle_deviation_deg(400.0)

    def test_a_square_pull_at_a_declared_rate_conforms(self):
        self.assertTrue(fixture_is_conforming(_fixture()))

    def test_a_deviation_exactly_at_the_tolerance_conforms(self):
        policy = _policy()
        tolerance = float(policy["max_pull_angle_deviation_deg"])
        fixture = _fixture(pull_angle_deg=NORMAL_PULL_ANGLE_DEG + tolerance)
        self.assertAlmostEqual(
            pull_angle_deviation_deg(fixture["pull_angle_deg"]),
            tolerance,
            places=9,
        )
        self.assertTrue(fixture_is_conforming(fixture, policy))

    def test_a_rate_exactly_on_the_lower_edge_conforms(self):
        policy = _policy()
        edge = float(policy["min_crosshead_rate_mm_per_min"])
        self.assertTrue(
            fixture_is_conforming(
                _fixture(crosshead_rate_mm_per_min=edge), policy
            )
        )

    def test_a_peeling_angle_does_not_conform(self):
        self.assertFalse(fixture_is_conforming(_fixture(pull_angle_deg=60.0)))

    def test_a_snatched_crosshead_does_not_conform(self):
        self.assertFalse(
            fixture_is_conforming(_fixture(crosshead_rate_mm_per_min=50.0))
        )

    def test_a_non_mapping_fixture_rejected(self):
        with self.assertRaises(ValueError):
            fixture_is_conforming([90.0, 2.0])


class PadGroupingTests(unittest.TestCase):
    def test_a_strong_pad_is_adherent(self):
        self.assertEqual(
            categorize_pad_adherence(9.0, PAD_AREA_MM2), ADHERENT
        )

    def test_a_pad_exactly_at_the_adherence_limit_is_adherent(self):
        policy = _policy()
        limit = float(policy["min_adherence_stress_n_per_mm2"])
        load = limit * PAD_AREA_MM2
        self.assertAlmostEqual(
            contact_stress_n_per_mm2(load, PAD_AREA_MM2), limit, places=9
        )
        self.assertEqual(
            categorize_pad_adherence(load, PAD_AREA_MM2, policy), ADHERENT
        )

    def test_a_weak_pad_is_below_limit(self):
        self.assertEqual(
            categorize_pad_adherence(2.0, PAD_AREA_MM2), BELOW_LIMIT
        )

    def test_a_pad_at_the_lift_off_threshold_has_lifted(self):
        policy = _policy()
        load = float(policy["lift_off_stress_n_per_mm2"]) * PAD_AREA_MM2
        self.assertEqual(
            categorize_pad_adherence(load, PAD_AREA_MM2, policy), LIFTED
        )

    def test_a_pad_that_came_away_at_zero_load_has_lifted(self):
        self.assertEqual(categorize_pad_adherence(0.0, PAD_AREA_MM2), LIFTED)


class DeviceSentencingTests(unittest.TestCase):
    def test_a_sound_device_is_adherent(self):
        self.assertEqual(sentence_planar_device(_device())["category"], ADHERENT)

    def test_a_device_is_sentenced_by_its_weakest_pad(self):
        self.assertEqual(
            sentence_planar_device(_device(cathode=2.0))["category"], BELOW_LIMIT
        )

    def test_a_lift_off_outranks_a_low_reading_on_the_same_device(self):
        sentence = sentence_planar_device(_device(anode=2.0, cathode=0.0))
        self.assertEqual(sentence["category"], LIFTED)

    def test_each_pad_keeps_its_own_grouping_and_stress(self):
        sentence = sentence_planar_device(_device(anode=9.0, cathode=2.0))
        self.assertEqual(sentence["pad_categories"][ANODE_PAD], ADHERENT)
        self.assertEqual(sentence["pad_categories"][CATHODE_PAD], BELOW_LIMIT)
        self.assertAlmostEqual(
            sentence["pad_stress_n_per_mm2"][ANODE_PAD], 4.0, places=9
        )

    def test_the_weakest_stress_is_reported_with_the_sentence(self):
        sentence = sentence_planar_device(_device(anode=9.0, cathode=2.0))
        self.assertAlmostEqual(
            sentence["weakest_stress_n_per_mm2"],
            min(sentence["pad_stress_n_per_mm2"].values()),
            places=12,
        )

    def test_an_unrecognised_pad_rejected(self):
        with self.assertRaises(ValueError):
            sentence_planar_device({"id": "d1", "pads": {"heat-sink-tab": {}}})

    def test_a_device_with_no_pads_rejected(self):
        with self.assertRaises(ValueError):
            sentence_planar_device({"id": "d1", "pads": {}})

    def test_a_non_mapping_device_rejected(self):
        with self.assertRaises(ValueError):
            sentence_planar_device(["d1"])


class RunAssessmentTests(unittest.TestCase):
    def test_a_sound_sample_accepts_the_lot(self):
        result = assess_contact_adherence_run(_run())
        self.assertEqual(result["verdict"], LOT_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["required_sample_devices"], 20)

    def test_an_undersized_sample_cannot_accept_the_lot(self):
        devices = [_device("d%d" % n) for n in range(1, 11)]
        result = assess_contact_adherence_run(_run(devices=devices))
        self.assertEqual(result["verdict"], SAMPLE_INSUFFICIENT)
        self.assertEqual(result["pulled_devices"], 10)

    def test_an_undersized_sample_outranks_a_lifted_pad(self):
        devices = [_device("d%d" % n) for n in range(1, 10)] + [
            _device("d10", cathode=0.0)
        ]
        result = assess_contact_adherence_run(_run(devices=devices))
        self.assertEqual(result["verdict"], SAMPLE_INSUFFICIENT)

    def test_a_sample_larger_than_the_lot_rejected(self):
        devices = [_device("d%d" % n) for n in range(1, 21)]
        with self.assertRaises(ValueError):
            assess_contact_adherence_run(
                _run(lot={"diode_count": 5}, devices=devices)
            )

    def test_a_peeling_fixture_is_a_fixture_deficiency(self):
        result = assess_contact_adherence_run(
            _run(fixture=_fixture(pull_angle_deg=60.0))
        )
        self.assertEqual(result["verdict"], FIXTURE_DEFICIENT)
        self.assertFalse(result["fixture_conforming"])

    def test_a_snatched_crosshead_is_a_fixture_deficiency(self):
        result = assess_contact_adherence_run(
            _run(fixture=_fixture(crosshead_rate_mm_per_min=50.0))
        )
        self.assertEqual(result["verdict"], FIXTURE_DEFICIENT)

    def test_a_fixture_deficiency_outranks_a_failed_reject_fraction(self):
        devices = [_device("d%d" % n) for n in range(1, 18)] + [
            _device("d18", anode=2.0),
            _device("d19", anode=2.0),
            _device("d20", anode=2.0),
        ]
        result = assess_contact_adherence_run(
            _run(fixture=_fixture(pull_angle_deg=60.0), devices=devices)
        )
        self.assertEqual(result["verdict"], FIXTURE_DEFICIENT)

    def test_one_lifted_pad_rejects_the_lot_outright(self):
        devices = [_device("d%d" % n) for n in range(1, 20)] + [
            _device("d20", cathode=0.0)
        ]
        result = assess_contact_adherence_run(_run(devices=devices))
        self.assertEqual(result["verdict"], LOT_REJECTED)
        self.assertEqual(result["lifted_devices"], 1)

    def test_a_reject_fraction_over_the_cap_rejects_the_lot(self):
        devices = [_device("d%d" % n) for n in range(1, 18)] + [
            _device("d18", anode=2.0),
            _device("d19", anode=2.0),
            _device("d20", anode=2.0),
        ]
        result = assess_contact_adherence_run(_run(devices=devices))
        self.assertEqual(result["verdict"], LOT_REJECTED)
        self.assertAlmostEqual(result["reject_fraction"], 0.15, places=12)

    def test_a_reject_fraction_exactly_at_the_cap_accepts_the_lot(self):
        policy = _policy()
        devices = [_device("d%d" % n) for n in range(1, 20)] + [
            _device("d20", anode=2.0)
        ]
        result = assess_contact_adherence_run(_run(devices=devices), policy)
        self.assertAlmostEqual(
            result["reject_fraction"], policy["max_reject_fraction"], places=9
        )
        self.assertEqual(result["verdict"], LOT_ACCEPTED)

    def test_every_device_pulled_is_sentenced(self):
        result = assess_contact_adherence_run(_run())
        self.assertEqual(len(result["sentences"]), 20)

    def test_missing_lot_block_rejected(self):
        run = _run()
        del run["lot"]
        with self.assertRaises(ValueError):
            assess_contact_adherence_run(run)

    def test_missing_fixture_block_rejected(self):
        run = _run()
        del run["fixture"]
        with self.assertRaises(ValueError):
            assess_contact_adherence_run(run)

    def test_an_empty_device_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_contact_adherence_run(_run(devices=[]))

    def test_a_non_mapping_run_rejected(self):
        with self.assertRaises(ValueError):
            assess_contact_adherence_run(["lot"])


if __name__ == "__main__":
    unittest.main()
