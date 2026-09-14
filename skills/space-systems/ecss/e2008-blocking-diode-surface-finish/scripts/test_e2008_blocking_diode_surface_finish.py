#!/usr/bin/env python3
"""Contract test for the blocking diode contact surface finish screen (offline)."""

import copy
import unittest

from e2008_blocking_diode_surface_finish_logic import (
    ACCEPT,
    ANODE,
    BLISTER,
    CATHODE,
    DEFAULT_FINISH_POLICY,
    EXAMINATION_INCOMPLETE,
    OXIDATION,
    PIT,
    REJECT,
    RESIDUE,
    REWORK,
    SCRATCH,
    assess_anomaly,
    assess_blocking_diode_finish,
    assess_contact_finish,
    coverage_by_kind,
    penetration_fraction,
    screen_blocking_diode_surface_finish,
    validate_finish_policy,
)


def _policy(**overrides):
    record = copy.deepcopy(DEFAULT_FINISH_POLICY)
    record.update(overrides)
    return record


def _anomaly(kind=SCRATCH, depth_um=0.5, coverage_fraction=0.01):
    return {
        "kind": kind,
        "depth_um": depth_um,
        "coverage_fraction": coverage_fraction,
    }


def _contact(polarity=ANODE, **overrides):
    record = {
        "polarity": polarity,
        "metallization_thickness_um": 5.0,
        "roughness_um": 0.40,
        "examination_magnification": 40.0,
        "anomalies": [],
    }
    record.update(overrides)
    return record


def _device(device_id="BD-001", anode=None, cathode=None):
    contacts = []
    contacts.append(anode if anode is not None else _contact(ANODE))
    if cathode is not False:
        contacts.append(cathode if cathode is not None else _contact(CATHODE))
    return {"device_id": device_id, "contacts": contacts}


def _lot(how_many, declared=None):
    return {
        "lot_id": "BDL-7",
        "declared_device_count": declared if declared is not None else how_many,
        "devices": [_device("BD-%03d" % n) for n in range(1, how_many + 1)],
    }


class PolicyValidationTests(unittest.TestCase):
    def test_the_default_policy_validates(self):
        self.assertIs(
            validate_finish_policy(DEFAULT_FINISH_POLICY), DEFAULT_FINISH_POLICY
        )

    def test_a_non_mapping_policy_is_refused(self):
        with self.assertRaises(ValueError):
            validate_finish_policy(0.8)

    def test_a_bondable_ceiling_at_the_working_ceiling_is_refused(self):
        with self.assertRaises(ValueError):
            validate_finish_policy(_policy(bondable_roughness_ceiling_um=0.80))

    def test_a_per_kind_allowance_above_the_total_is_refused(self):
        with self.assertRaises(ValueError):
            validate_finish_policy(_policy(max_anomaly_coverage_fraction=0.20))

    def test_a_coverage_allowance_above_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_finish_policy(_policy(max_total_coverage_fraction=1.4))

    def test_a_rework_margin_below_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_finish_policy(_policy(rework_margin_factor=0.5))

    def test_a_non_positive_magnification_floor_is_refused(self):
        with self.assertRaises(ValueError):
            validate_finish_policy(_policy(magnification_floor=0.0))

    def test_a_missing_penetration_allowance_is_refused(self):
        broken = _policy()
        del broken["max_penetration_fraction"]
        with self.assertRaises(ValueError):
            validate_finish_policy(broken)


class PenetrationTests(unittest.TestCase):
    def test_half_the_metallisation_reads_one_half(self):
        self.assertAlmostEqual(penetration_fraction(2.5, 5.0), 0.5, places=9)

    def test_a_depth_equal_to_the_thickness_reads_unity(self):
        self.assertAlmostEqual(penetration_fraction(5.0, 5.0), 1.0, places=9)

    def test_an_undamaged_surface_reads_zero(self):
        self.assertAlmostEqual(penetration_fraction(0.0, 5.0), 0.0, places=9)

    def test_a_negative_depth_is_refused(self):
        with self.assertRaises(ValueError):
            penetration_fraction(-0.1, 5.0)

    def test_a_zero_metallisation_thickness_is_refused(self):
        with self.assertRaises(ValueError):
            penetration_fraction(1.0, 0.0)

    def test_a_non_numeric_depth_is_refused(self):
        with self.assertRaises(ValueError):
            penetration_fraction("deep", 5.0)


class AnomalyTests(unittest.TestCase):
    def test_a_shallow_narrow_scratch_is_accepted(self):
        result = assess_anomaly(_anomaly(), 5.0)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertEqual(result["findings"], [])

    def test_a_blister_is_rejected_however_shallow(self):
        result = assess_anomaly(
            _anomaly(kind=BLISTER, depth_um=0.01, coverage_fraction=0.001), 5.0
        )
        self.assertEqual(result["disposition"], REJECT)
        self.assertFalse(result["through_to_substrate"])

    def test_a_pit_through_to_the_substrate_is_rejected(self):
        result = assess_anomaly(_anomaly(kind=PIT, depth_um=5.0), 5.0)
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(result["through_to_substrate"])

    def test_a_penetration_exactly_on_the_allowance_is_admissible(self):
        result = assess_anomaly(_anomaly(kind=PIT, depth_um=1.5), 5.0)
        self.assertAlmostEqual(result["penetration_fraction"], 0.30, places=9)
        self.assertEqual(result["disposition"], ACCEPT)

    def test_a_penetration_inside_the_rework_margin_returns_the_part(self):
        result = assess_anomaly(_anomaly(kind=PIT, depth_um=2.5), 5.0)
        self.assertEqual(result["disposition"], REWORK)

    def test_a_penetration_past_the_rework_margin_is_rejected(self):
        result = assess_anomaly(_anomaly(kind=PIT, depth_um=4.0), 5.0)
        self.assertEqual(result["disposition"], REJECT)

    def test_a_coverage_exactly_on_the_allowance_is_admissible(self):
        result = assess_anomaly(
            _anomaly(kind=OXIDATION, depth_um=0.1, coverage_fraction=0.05), 5.0
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_a_wide_shallow_film_returns_the_part_for_cleaning(self):
        result = assess_anomaly(
            _anomaly(kind=RESIDUE, depth_um=0.05, coverage_fraction=0.08), 5.0
        )
        self.assertEqual(result["disposition"], REWORK)

    def test_a_film_over_most_of_the_contact_is_rejected(self):
        result = assess_anomaly(
            _anomaly(kind=RESIDUE, depth_um=0.05, coverage_fraction=0.60), 5.0
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_an_unknown_anomaly_kind_is_refused(self):
        with self.assertRaises(ValueError):
            assess_anomaly(_anomaly(kind="smudge"), 5.0)

    def test_a_coverage_above_one_is_refused(self):
        with self.assertRaises(ValueError):
            assess_anomaly(_anomaly(coverage_fraction=1.2), 5.0)

    def test_a_non_mapping_anomaly_is_refused(self):
        with self.assertRaises(ValueError):
            assess_anomaly("scratch", 5.0)


class CoverageAccumulationTests(unittest.TestCase):
    def test_an_unmarked_contact_totals_zero(self):
        result = coverage_by_kind([], 5.0)
        self.assertAlmostEqual(result["total_coverage_fraction"], 0.0, places=9)
        self.assertEqual(result["graded"], [])

    def test_coverage_is_totalled_per_kind(self):
        result = coverage_by_kind(
            [
                _anomaly(kind=SCRATCH, coverage_fraction=0.01),
                _anomaly(kind=SCRATCH, coverage_fraction=0.02),
                _anomaly(kind=OXIDATION, depth_um=0.1, coverage_fraction=0.03),
            ],
            5.0,
        )
        self.assertAlmostEqual(result["coverage_by_kind"][SCRATCH], 0.03, places=9)
        self.assertAlmostEqual(result["coverage_by_kind"][OXIDATION], 0.03, places=9)
        self.assertAlmostEqual(result["total_coverage_fraction"], 0.06, places=9)

    def test_coverage_summing_past_the_contact_area_is_refused(self):
        with self.assertRaises(ValueError):
            coverage_by_kind(
                [
                    _anomaly(kind=OXIDATION, depth_um=0.1, coverage_fraction=0.7),
                    _anomaly(kind=RESIDUE, depth_um=0.1, coverage_fraction=0.7),
                ],
                5.0,
            )

    def test_anomalies_not_a_list_is_refused(self):
        with self.assertRaises(ValueError):
            coverage_by_kind("none", 5.0)


class ContactFinishTests(unittest.TestCase):
    def test_a_sound_contact_is_accepted(self):
        result = assess_contact_finish(_contact())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["examined"])
        self.assertEqual(result["findings"], [])

    def test_roughness_exactly_on_the_working_ceiling_is_admissible(self):
        result = assess_contact_finish(_contact(roughness_um=0.80))
        self.assertEqual(result["verdict"], ACCEPT)

    def test_roughness_between_the_ceilings_returns_the_part(self):
        result = assess_contact_finish(_contact(roughness_um=1.10))
        self.assertEqual(result["verdict"], REWORK)

    def test_roughness_exactly_on_the_bondable_ceiling_is_still_rework(self):
        result = assess_contact_finish(_contact(roughness_um=1.60))
        self.assertEqual(result["verdict"], REWORK)

    def test_roughness_past_the_bondable_ceiling_is_rejected(self):
        result = assess_contact_finish(_contact(roughness_um=2.20))
        self.assertEqual(result["verdict"], REJECT)

    def test_an_under_magnified_examination_leaves_the_contact_open(self):
        result = assess_contact_finish(_contact(examination_magnification=8.0))
        self.assertEqual(result["verdict"], EXAMINATION_INCOMPLETE)
        self.assertFalse(result["examined"])
        self.assertTrue(result["findings"])

    def test_magnification_exactly_on_the_floor_counts_as_examined(self):
        result = assess_contact_finish(_contact(examination_magnification=20.0))
        self.assertTrue(result["examined"])

    def test_many_small_anomalies_trip_the_total_coverage_allowance(self):
        contact = _contact(
            anomalies=[
                _anomaly(kind=SCRATCH, coverage_fraction=0.04),
                _anomaly(kind=OXIDATION, depth_um=0.1, coverage_fraction=0.04),
                _anomaly(kind=RESIDUE, depth_um=0.1, coverage_fraction=0.04),
            ]
        )
        result = assess_contact_finish(contact)
        self.assertEqual(result["verdict"], REWORK)
        self.assertAlmostEqual(result["total_coverage_fraction"], 0.12, places=9)

    def test_the_deepest_penetration_is_carried_on_the_record(self):
        contact = _contact(
            anomalies=[_anomaly(kind=PIT, depth_um=1.0), _anomaly(depth_um=0.25)]
        )
        result = assess_contact_finish(contact)
        self.assertAlmostEqual(
            result["deepest_penetration_fraction"], 0.20, places=9
        )

    def test_an_unknown_polarity_is_refused(self):
        with self.assertRaises(ValueError):
            assess_contact_finish(_contact(polarity="middle"))

    def test_a_missing_metallisation_thickness_is_refused(self):
        broken = _contact()
        del broken["metallization_thickness_um"]
        with self.assertRaises(ValueError):
            assess_contact_finish(broken)

    def test_a_negative_roughness_is_refused(self):
        with self.assertRaises(ValueError):
            assess_contact_finish(_contact(roughness_um=-0.2))


class DeviceSentencingTests(unittest.TestCase):
    def test_a_device_with_two_sound_contacts_is_accepted(self):
        result = assess_blocking_diode_finish(_device())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["complete"])
        self.assertEqual(result["examined_polarities"], [ANODE, CATHODE])

    def test_the_worse_contact_sentences_the_device(self):
        result = assess_blocking_diode_finish(
            _device(cathode=_contact(CATHODE, roughness_um=2.5))
        )
        self.assertEqual(result["verdict"], REJECT)

    def test_a_device_with_one_contact_examined_is_left_open(self):
        result = assess_blocking_diode_finish(_device(cathode=False))
        self.assertEqual(result["verdict"], EXAMINATION_INCOMPLETE)
        self.assertEqual(result["missing_polarities"], [CATHODE])

    def test_an_under_magnified_contact_leaves_the_device_open(self):
        result = assess_blocking_diode_finish(
            _device(cathode=_contact(CATHODE, examination_magnification=5.0))
        )
        self.assertEqual(result["verdict"], EXAMINATION_INCOMPLETE)
        self.assertEqual(result["under_magnified_polarities"], [CATHODE])

    def test_two_records_for_one_polarity_are_refused(self):
        device = _device()
        device["contacts"].append(_contact(CATHODE))
        with self.assertRaises(ValueError):
            assess_blocking_diode_finish(device)

    def test_a_device_with_no_contacts_is_refused(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_finish({"device_id": "BD-9", "contacts": []})

    def test_a_device_without_an_id_is_refused(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_finish({"device_id": "  ", "contacts": []})


class LotScreenTests(unittest.TestCase):
    def test_a_clean_lot_is_accepted(self):
        result = screen_blocking_diode_surface_finish(_lot(20))
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["complete"])
        self.assertEqual(result["examined_count"], 20)
        self.assertEqual(result["affected_count"], 0)

    def test_one_finding_in_twenty_stays_inside_the_lot_allowance(self):
        lot = _lot(20)
        lot["devices"][0]["contacts"][0]["roughness_um"] = 1.10
        result = screen_blocking_diode_surface_finish(lot)
        self.assertEqual(result["affected_count"], 1)
        self.assertEqual(result["verdict"], REWORK)

    def test_findings_past_the_rework_margin_reject_the_lot(self):
        lot = _lot(20)
        for device in lot["devices"][:6]:
            device["contacts"][0]["roughness_um"] = 1.10
        result = screen_blocking_diode_surface_finish(lot)
        self.assertEqual(result["verdict"], REJECT)

    def test_a_short_lot_is_left_open(self):
        result = screen_blocking_diode_surface_finish(_lot(8, declared=12))
        self.assertEqual(result["verdict"], EXAMINATION_INCOMPLETE)
        self.assertEqual(result["missing_count"], 4)

    def test_more_records_than_declared_is_refused(self):
        with self.assertRaises(ValueError):
            screen_blocking_diode_surface_finish(_lot(12, declared=8))

    def test_a_duplicate_device_id_is_refused(self):
        lot = _lot(3)
        lot["devices"][2]["device_id"] = "BD-001"
        with self.assertRaises(ValueError):
            screen_blocking_diode_surface_finish(lot)

    def test_a_non_integer_declared_count_is_refused(self):
        lot = _lot(3)
        lot["declared_device_count"] = "three"
        with self.assertRaises(ValueError):
            screen_blocking_diode_surface_finish(lot)

    def test_devices_not_a_list_is_refused(self):
        with self.assertRaises(ValueError):
            screen_blocking_diode_surface_finish(
                {"lot_id": "BDL-7", "declared_device_count": 3, "devices": "three"}
            )

    def test_an_open_device_keeps_the_lot_open_even_when_all_are_present(self):
        lot = _lot(6)
        lot["devices"][3]["contacts"][1]["examination_magnification"] = 4.0
        result = screen_blocking_diode_surface_finish(lot)
        self.assertEqual(result["verdict"], EXAMINATION_INCOMPLETE)
        self.assertEqual(result["open_device_ids"], ["BD-004"])

    def test_the_report_carries_the_lot_it_answered_to(self):
        result = screen_blocking_diode_surface_finish(_lot(5))
        self.assertEqual(result["lot_id"], "BDL-7")
        self.assertEqual(result["declared_device_count"], 5)
        self.assertEqual(result["counts"][ACCEPT], 5)


if __name__ == "__main__":
    unittest.main()
