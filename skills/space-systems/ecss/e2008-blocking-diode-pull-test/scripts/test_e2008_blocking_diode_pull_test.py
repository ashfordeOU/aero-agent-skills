#!/usr/bin/env python3
"""Contract test for the blocking diode interconnector pull screen (offline)."""

import copy
import math
import unittest

from e2008_blocking_diode_pull_test_logic import (
    ACCEPT,
    ANODE,
    BOND_INTERFACE,
    CATHODE,
    DEFAULT_PULL_POLICY,
    DIE_FRACTURE,
    METALLIZATION_LIFT,
    PULL_INCOMPLETE,
    REJECT,
    REVIEW,
    RIBBON_FRACTURE,
    assess_blocking_diode_pull,
    assess_contact_pull,
    bond_stress_mpa,
    interconnector_capacity_n,
    resolve_normal_force,
    screen_blocking_diode_pull,
    validate_pull_policy,
)


def _policy(**overrides):
    record = copy.deepcopy(DEFAULT_PULL_POLICY)
    record.update(overrides)
    return record


def _ribbon(**overrides):
    record = {
        "width_mm": 2.0,
        "thickness_mm": 0.05,
        "tensile_strength_mpa": 250.0,
    }
    record.update(overrides)
    return record


def _contact(polarity=ANODE, **overrides):
    record = {
        "polarity": polarity,
        "failure_mode": BOND_INTERFACE,
        "pull_force_n": 12.0,
        "pull_angle_deg": 0.0,
        "bonded_area_mm2": 1.0,
        "interconnector": _ribbon(),
    }
    record.update(overrides)
    return record


def _device(device_id="BD-001", anode=None, cathode=None):
    contacts = [anode if anode is not None else _contact(ANODE)]
    if cathode is not False:
        contacts.append(cathode if cathode is not None else _contact(CATHODE))
    return {"device_id": device_id, "contacts": contacts}


def _lot(how_many, population=None):
    return {
        "lot_id": "BDL-16",
        "lot_population": population if population is not None else how_many,
        "devices": [_device("BD-%03d" % n) for n in range(1, how_many + 1)],
    }


class PolicyValidationTests(unittest.TestCase):
    def test_the_default_policy_validates(self):
        self.assertIs(validate_pull_policy(DEFAULT_PULL_POLICY), DEFAULT_PULL_POLICY)

    def test_a_non_mapping_policy_is_refused(self):
        with self.assertRaises(ValueError):
            validate_pull_policy(4.0)

    def test_a_ninety_degree_angle_cap_is_refused(self):
        with self.assertRaises(ValueError):
            validate_pull_policy(_policy(max_pull_angle_deg=90.0))

    def test_a_negative_angle_cap_is_refused(self):
        with self.assertRaises(ValueError):
            validate_pull_policy(_policy(max_pull_angle_deg=-5.0))

    def test_a_zero_utilisation_ceiling_is_refused(self):
        with self.assertRaises(ValueError):
            validate_pull_policy(_policy(ribbon_utilisation_ceiling=0.0))

    def test_a_review_margin_below_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_pull_policy(_policy(review_margin_factor=0.8))

    def test_a_zero_sample_fraction_is_refused(self):
        with self.assertRaises(ValueError):
            validate_pull_policy(_policy(min_sample_fraction=0.0))

    def test_a_non_positive_minimum_force_is_refused(self):
        with self.assertRaises(ValueError):
            validate_pull_policy(_policy(min_pull_force_n=0.0))


class RibbonCapacityTests(unittest.TestCase):
    def test_the_capacity_is_the_cross_section_times_the_strength(self):
        self.assertAlmostEqual(interconnector_capacity_n(_ribbon()), 25.0, places=9)

    def test_a_thicker_ribbon_carries_proportionally_more(self):
        thin = interconnector_capacity_n(_ribbon(thickness_mm=0.05))
        thick = interconnector_capacity_n(_ribbon(thickness_mm=0.10))
        self.assertAlmostEqual(thick, 2.0 * thin, places=9)

    def test_a_zero_width_ribbon_is_refused(self):
        with self.assertRaises(ValueError):
            interconnector_capacity_n(_ribbon(width_mm=0.0))

    def test_a_non_mapping_interconnector_is_refused(self):
        with self.assertRaises(ValueError):
            interconnector_capacity_n("ribbon")


class GeometryTests(unittest.TestCase):
    def test_a_pull_along_the_normal_keeps_its_whole_force(self):
        self.assertAlmostEqual(resolve_normal_force(10.0, 0.0), 10.0, places=9)

    def test_a_sixty_degree_pull_puts_half_its_force_into_the_joint(self):
        self.assertAlmostEqual(resolve_normal_force(10.0, 60.0), 5.0, places=9)

    def test_a_thirty_degree_pull_matches_its_cosine(self):
        self.assertAlmostEqual(
            resolve_normal_force(10.0, 30.0),
            10.0 * math.cos(math.radians(30.0)),
            places=12,
        )

    def test_a_ninety_degree_pull_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_normal_force(10.0, 90.0)

    def test_a_negative_angle_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_normal_force(10.0, -10.0)

    def test_the_bond_stress_is_the_normal_force_over_the_bonded_area(self):
        self.assertAlmostEqual(bond_stress_mpa(12.0, 1.5), 8.0, places=9)

    def test_a_zero_bonded_area_is_refused(self):
        with self.assertRaises(ValueError):
            bond_stress_mpa(12.0, 0.0)


class ContactPullTests(unittest.TestCase):
    def test_a_sound_bond_release_is_accepted(self):
        result = assess_contact_pull(_contact())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["bond_measured"])
        self.assertAlmostEqual(result["normal_force_n"], 12.0, places=9)
        self.assertAlmostEqual(result["bond_stress_mpa"], 12.0, places=9)

    def test_a_force_exactly_on_the_minimum_is_admissible(self):
        result = assess_contact_pull(
            _contact(pull_force_n=8.0, bonded_area_mm2=1.0)
        )
        self.assertEqual(result["verdict"], ACCEPT)

    def test_a_force_inside_the_review_band_is_referred(self):
        result = assess_contact_pull(
            _contact(pull_force_n=7.0, bonded_area_mm2=1.0)
        )
        self.assertEqual(result["verdict"], REVIEW)

    def test_a_force_under_the_review_floor_is_rejected(self):
        result = assess_contact_pull(
            _contact(pull_force_n=2.0, bonded_area_mm2=1.0)
        )
        self.assertEqual(result["verdict"], REJECT)

    def test_a_large_bonded_area_can_fail_on_stress_at_a_passing_force(self):
        result = assess_contact_pull(
            _contact(pull_force_n=10.0, bonded_area_mm2=4.0)
        )
        self.assertAlmostEqual(result["bond_stress_mpa"], 2.5, places=9)
        self.assertEqual(result["verdict"], REJECT)

    def test_an_off_normal_pull_past_the_cap_leaves_the_contact_open(self):
        result = assess_contact_pull(_contact(pull_angle_deg=40.0))
        self.assertEqual(result["verdict"], PULL_INCOMPLETE)
        self.assertFalse(result["measured"])

    def test_an_angle_exactly_on_the_cap_is_still_measured(self):
        result = assess_contact_pull(_contact(pull_angle_deg=15.0))
        self.assertTrue(result["measured"])
        self.assertAlmostEqual(
            result["normal_force_n"], 12.0 * math.cos(math.radians(15.0)), places=12
        )

    def test_a_ribbon_break_above_the_requirement_proves_a_lower_bound(self):
        result = assess_contact_pull(
            _contact(failure_mode=RIBBON_FRACTURE, pull_force_n=20.0)
        )
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["measured"])
        self.assertFalse(result["bond_measured"])
        self.assertTrue(result["findings"])

    def test_a_ribbon_break_below_the_requirement_proves_nothing(self):
        result = assess_contact_pull(
            _contact(
                failure_mode=RIBBON_FRACTURE,
                pull_force_n=2.0,
                interconnector=_ribbon(tensile_strength_mpa=30.0),
            )
        )
        self.assertEqual(result["verdict"], PULL_INCOMPLETE)
        self.assertFalse(result["measured"])

    def test_a_metallisation_lift_is_rejected(self):
        result = assess_contact_pull(
            _contact(failure_mode=METALLIZATION_LIFT, pull_force_n=20.0)
        )
        self.assertEqual(result["verdict"], REJECT)

    def test_a_die_fracture_is_rejected(self):
        result = assess_contact_pull(
            _contact(failure_mode=DIE_FRACTURE, pull_force_n=20.0)
        )
        self.assertEqual(result["verdict"], REJECT)

    def test_a_bond_release_near_the_ribbon_capacity_is_flagged(self):
        result = assess_contact_pull(
            _contact(pull_force_n=22.0, bonded_area_mm2=1.0)
        )
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertAlmostEqual(result["ribbon_utilisation"], 0.88, places=9)
        self.assertTrue(result["findings"])

    def test_a_utilisation_exactly_on_the_ceiling_is_not_flagged(self):
        result = assess_contact_pull(
            _contact(pull_force_n=20.0, bonded_area_mm2=1.0)
        )
        self.assertAlmostEqual(result["ribbon_utilisation"], 0.80, places=9)
        self.assertEqual(result["findings"], [])

    def test_an_unknown_failure_mode_is_refused(self):
        with self.assertRaises(ValueError):
            assess_contact_pull(_contact(failure_mode="let-go"))

    def test_an_unknown_polarity_is_refused(self):
        with self.assertRaises(ValueError):
            assess_contact_pull(_contact(polarity="middle"))

    def test_a_missing_bonded_area_is_refused(self):
        broken = _contact()
        del broken["bonded_area_mm2"]
        with self.assertRaises(ValueError):
            assess_contact_pull(broken)


class DeviceSentencingTests(unittest.TestCase):
    def test_a_device_with_two_sound_pulls_is_accepted(self):
        result = assess_blocking_diode_pull(_device())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["complete"])
        self.assertEqual(result["pulled_polarities"], [ANODE, CATHODE])
        self.assertEqual(result["bond_measured_count"], 2)

    def test_the_weaker_contact_sentences_the_device(self):
        result = assess_blocking_diode_pull(
            _device(cathode=_contact(CATHODE, pull_force_n=2.0))
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertAlmostEqual(result["weakest_normal_force_n"], 2.0, places=9)

    def test_a_device_pulled_on_one_contact_is_left_open(self):
        result = assess_blocking_diode_pull(_device(cathode=False))
        self.assertEqual(result["verdict"], PULL_INCOMPLETE)
        self.assertEqual(result["missing_polarities"], [CATHODE])

    def test_an_unusable_pull_leaves_the_device_open(self):
        result = assess_blocking_diode_pull(
            _device(cathode=_contact(CATHODE, pull_angle_deg=50.0))
        )
        self.assertEqual(result["verdict"], PULL_INCOMPLETE)
        self.assertEqual(result["unmeasured_polarities"], [CATHODE])

    def test_two_pulls_on_one_polarity_are_refused(self):
        device = _device()
        device["contacts"].append(_contact(CATHODE))
        with self.assertRaises(ValueError):
            assess_blocking_diode_pull(device)

    def test_a_device_with_no_pulls_is_refused(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_pull({"device_id": "BD-9", "contacts": []})

    def test_a_device_without_an_id_is_refused(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_pull({"device_id": " ", "contacts": []})


class LotScreenTests(unittest.TestCase):
    def test_a_clean_lot_is_accepted(self):
        result = screen_blocking_diode_pull(_lot(20))
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["complete"])
        self.assertEqual(result["pulled_count"], 20)
        self.assertEqual(result["failing_count"], 0)

    def test_a_sample_too_thin_is_referred_to_review(self):
        result = screen_blocking_diode_pull(_lot(5, population=200))
        self.assertEqual(result["verdict"], REVIEW)
        self.assertAlmostEqual(result["sample_fraction"], 0.025, places=9)

    def test_a_sample_exactly_on_the_floor_is_accepted(self):
        result = screen_blocking_diode_pull(_lot(10, population=100))
        self.assertAlmostEqual(result["sample_fraction"], 0.10, places=9)
        self.assertEqual(result["verdict"], ACCEPT)

    def test_one_weak_device_in_twenty_rejects_the_lot(self):
        lot = _lot(20)
        lot["devices"][3]["contacts"][0]["pull_force_n"] = 2.0
        result = screen_blocking_diode_pull(lot)
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["failing_count"], 1)

    def test_the_weakest_normal_force_is_carried_on_the_report(self):
        lot = _lot(20)
        lot["devices"][7]["contacts"][1]["pull_force_n"] = 9.0
        result = screen_blocking_diode_pull(lot)
        self.assertAlmostEqual(result["weakest_normal_force_n"], 9.0, places=9)

    def test_more_pulled_devices_than_the_population_is_refused(self):
        with self.assertRaises(ValueError):
            screen_blocking_diode_pull(_lot(20, population=8))

    def test_a_duplicate_device_id_is_refused(self):
        lot = _lot(3)
        lot["devices"][2]["device_id"] = "BD-001"
        with self.assertRaises(ValueError):
            screen_blocking_diode_pull(lot)

    def test_a_non_integer_population_is_refused(self):
        lot = _lot(3)
        lot["lot_population"] = "many"
        with self.assertRaises(ValueError):
            screen_blocking_diode_pull(lot)

    def test_devices_not_a_list_is_refused(self):
        with self.assertRaises(ValueError):
            screen_blocking_diode_pull(
                {"lot_id": "BDL-16", "lot_population": 3, "devices": "three"}
            )

    def test_an_open_device_keeps_the_lot_open(self):
        lot = _lot(12)
        lot["devices"][5]["contacts"][0]["pull_angle_deg"] = 45.0
        result = screen_blocking_diode_pull(lot)
        self.assertEqual(result["verdict"], PULL_INCOMPLETE)
        self.assertEqual(result["open_device_ids"], ["BD-006"])

    def test_the_report_carries_the_lot_it_answered_to(self):
        result = screen_blocking_diode_pull(_lot(12, population=60))
        self.assertEqual(result["lot_id"], "BDL-16")
        self.assertEqual(result["lot_population"], 60)
        self.assertEqual(result["counts"][ACCEPT], 12)


if __name__ == "__main__":
    unittest.main()
