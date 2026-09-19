#!/usr/bin/env python3
"""Gate 3 contract test for q6005-adhesive-compound-bonding-repair.

Offline, stdlib unittest. Exercises the compound validation, the storage and
working life arithmetic, the bond-line computation, the interpolated cure
schedule, the neighbourhood temperature check and the three-way disposition
of ECSS-Q-ST-60-05C clause 10.5.4 as paraphrased in the logic module. A
nominal joint lands exactly on a bond-line bound and a nominal cure lands
exactly on a completion of one, so those bounds are asserted with
assertAlmostEqual rather than strict inequalities that could round either way
between the build host and the CI runner.
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_adhesive_compound_bonding_repair_logic import (  # noqa: E402
    DEFAULT_BOND_LINE_UM,
    SHELF_LIFE_CAUTION_DAYS,
    assess_adhesive_repair,
    bond_line_thickness_um,
    cure_completion_ratio,
    elements_exceeded_by_cure,
    parse_date,
    required_cure_minutes,
    shelf_life_days_remaining,
    validate_compound,
    working_life_remaining_minutes,
)

USE_DAY = "2026-09-18"


def compound(**overrides):
    record = {
        "compound_id": "EA-9394",
        "storage_life_expiry": "2027-03-01",
        "working_life_minutes": 90.0,
        "electrically_conductive": False,
        "approved_for_programme": True,
    }
    record.update(overrides)
    return record


def repair(**overrides):
    """A nominal reattachment: in-date compound, 50 um bond line, full cure."""
    spec = {
        "compound": compound(),
        "use_date": USE_DAY,
        "minutes_since_mix": 20.0,
        "dispensed_volume_mm3": 1.0,
        "footprint_mm2": 20.0,
        "cure_temperature_c": 125.0,
        "cure_minutes": 60.0,
        "elements": [{"element_id": "R4", "temperature_limit_c": 200.0}],
        "site_cleaned": True,
        "isolation_required": False,
    }
    spec.update(overrides)
    return spec


class CompoundValidationTests(unittest.TestCase):
    def test_compound_must_be_a_mapping_with_its_keys(self):
        with self.assertRaises(ValueError):
            validate_compound("EA-9394")
        for key in ("compound_id", "storage_life_expiry", "working_life_minutes"):
            record = compound()
            del record[key]
            with self.assertRaises(ValueError):
                validate_compound(record)

    def test_non_boolean_flags_are_refused(self):
        with self.assertRaises(ValueError):
            validate_compound(compound(approved_for_programme="yes"))
        with self.assertRaises(ValueError):
            validate_compound(compound(electrically_conductive=1))

    def test_a_malformed_expiry_is_refused(self):
        with self.assertRaises(ValueError):
            validate_compound(compound(storage_life_expiry="01/03/2027"))

    def test_a_date_object_is_accepted_as_well_as_a_string(self):
        parsed = parse_date(datetime.date(2027, 3, 1), "expiry")
        self.assertEqual(parsed, datetime.date(2027, 3, 1))

    def test_non_positive_working_life_is_refused(self):
        with self.assertRaises(ValueError):
            validate_compound(compound(working_life_minutes=0.0))


class LifeArithmeticTests(unittest.TestCase):
    def test_shelf_life_counts_days_to_the_storage_life_date(self):
        self.assertEqual(shelf_life_days_remaining(compound(), "2027-02-27"), 2)

    def test_use_on_the_last_good_day_leaves_zero_days(self):
        self.assertEqual(shelf_life_days_remaining(compound(), "2027-03-01"), 0)

    def test_use_after_the_storage_life_date_is_negative(self):
        self.assertEqual(shelf_life_days_remaining(compound(), "2027-03-05"), -4)

    def test_working_life_remaining_goes_negative_once_spent(self):
        self.assertAlmostEqual(working_life_remaining_minutes(compound(), 30.0), 60.0, places=9)
        self.assertAlmostEqual(working_life_remaining_minutes(compound(), 100.0), -10.0, places=9)

    def test_negative_elapsed_mix_time_is_refused(self):
        with self.assertRaises(ValueError):
            working_life_remaining_minutes(compound(), -5.0)


class BondLineTests(unittest.TestCase):
    def test_bond_line_is_the_volume_spread_over_the_footprint(self):
        self.assertAlmostEqual(bond_line_thickness_um(1.0, 20.0), 50.0, places=9)

    def test_a_joint_on_the_thin_bound_is_inside_the_window(self):
        thickness = bond_line_thickness_um(0.5, 20.0)
        self.assertAlmostEqual(thickness, DEFAULT_BOND_LINE_UM[0], places=9)
        result = assess_adhesive_repair(repair(dispensed_volume_mm3=0.5))
        self.assertEqual(result["disposition"], "permitted")

    def test_a_starved_joint_is_refused(self):
        result = assess_adhesive_repair(repair(dispensed_volume_mm3=0.2))
        self.assertFalse(result["permitted"])
        self.assertTrue(any("bond line" in b for b in result["blockers"]))

    def test_a_flooded_joint_is_refused(self):
        result = assess_adhesive_repair(repair(dispensed_volume_mm3=4.0))
        self.assertTrue(any("bond line" in b for b in result["blockers"]))

    def test_non_positive_geometry_is_refused(self):
        with self.assertRaises(ValueError):
            bond_line_thickness_um(0.0, 20.0)
        with self.assertRaises(ValueError):
            bond_line_thickness_um(1.0, -20.0)


class CureScheduleTests(unittest.TestCase):
    def test_a_tabulated_temperature_returns_its_own_dwell(self):
        self.assertAlmostEqual(required_cure_minutes(125.0), 60.0, places=9)
        self.assertAlmostEqual(required_cure_minutes(80.0), 240.0, places=9)

    def test_between_two_points_the_dwell_is_interpolated(self):
        self.assertAlmostEqual(required_cure_minutes(90.0), 180.0, places=9)

    def test_above_the_hottest_point_the_hottest_dwell_is_held(self):
        self.assertAlmostEqual(required_cure_minutes(200.0), 30.0, places=9)

    def test_below_the_coolest_point_the_schedule_does_not_apply(self):
        with self.assertRaises(ValueError):
            required_cure_minutes(60.0)

    def test_a_one_point_schedule_is_refused(self):
        with self.assertRaises(ValueError):
            required_cure_minutes(125.0, schedule=((125.0, 60.0),))

    def test_a_just_complete_cure_lands_on_one(self):
        self.assertAlmostEqual(cure_completion_ratio(125.0, 60.0), 1.0, places=9)

    def test_a_just_complete_cure_is_accepted_not_refused(self):
        result = assess_adhesive_repair(repair(cure_minutes=60.0))
        self.assertEqual(result["blockers"], [])

    def test_an_under_cure_is_refused(self):
        result = assess_adhesive_repair(repair(cure_minutes=45.0))
        self.assertFalse(result["permitted"])
        self.assertTrue(any("cure is" in b for b in result["blockers"]))


class NeighbourhoodTests(unittest.TestCase):
    def test_a_tolerant_neighbour_is_not_exposed(self):
        self.assertEqual(
            elements_exceeded_by_cure(125.0, [{"element_id": "R4", "temperature_limit_c": 200.0}]),
            [],
        )

    def test_a_neighbour_at_exactly_the_cure_temperature_is_not_exposed(self):
        self.assertEqual(
            elements_exceeded_by_cure(125.0, [{"element_id": "R4", "temperature_limit_c": 125.0}]),
            [],
        )

    def test_a_fragile_neighbour_is_exposed_and_blocks_the_repair(self):
        exposed = elements_exceeded_by_cure(
            125.0, [{"element_id": "D2", "temperature_limit_c": 100.0}]
        )
        self.assertEqual([e["element_id"] for e in exposed], ["D2"])
        result = assess_adhesive_repair(
            repair(elements=[{"element_id": "D2", "temperature_limit_c": 100.0}])
        )
        self.assertFalse(result["permitted"])

    def test_malformed_element_records_are_refused(self):
        with self.assertRaises(ValueError):
            elements_exceeded_by_cure(125.0, {"element_id": "D2"})
        with self.assertRaises(ValueError):
            elements_exceeded_by_cure(125.0, [{"element_id": "D2"}])


class DispositionTests(unittest.TestCase):
    def test_a_nominal_reattachment_is_permitted(self):
        result = assess_adhesive_repair(repair())
        self.assertEqual(result["disposition"], "permitted")
        self.assertTrue(result["permitted"])

    def test_an_unapproved_compound_blocks_the_repair(self):
        result = assess_adhesive_repair(repair(compound=compound(approved_for_programme=False)))
        self.assertEqual(result["disposition"], "not-permitted")

    def test_an_expired_compound_blocks_the_repair(self):
        result = assess_adhesive_repair(
            repair(compound=compound(storage_life_expiry="2026-09-01"))
        )
        self.assertTrue(any("storage life" in b for b in result["blockers"]))

    def test_a_compound_close_to_expiry_is_a_condition_not_a_block(self):
        near = (
            datetime.date.fromisoformat(USE_DAY)
            + datetime.timedelta(days=SHELF_LIFE_CAUTION_DAYS - 1)
        ).isoformat()
        result = assess_adhesive_repair(repair(compound=compound(storage_life_expiry=near)))
        self.assertEqual(result["disposition"], "permitted-with-conditions")
        self.assertTrue(result["permitted"])

    def test_a_compound_past_its_working_life_blocks_the_repair(self):
        result = assess_adhesive_repair(repair(minutes_since_mix=120.0))
        self.assertTrue(any("working life" in b for b in result["blockers"]))

    def test_an_uncleaned_site_blocks_the_repair(self):
        result = assess_adhesive_repair(repair(site_cleaned=False))
        self.assertTrue(any("not removed" in b for b in result["blockers"]))

    def test_a_conductive_compound_on_an_isolated_joint_blocks_the_repair(self):
        result = assess_adhesive_repair(
            repair(
                compound=compound(electrically_conductive=True),
                isolation_required=True,
            )
        )
        self.assertTrue(any("isolation" in b for b in result["blockers"]))

    def test_a_conductive_compound_is_fine_where_isolation_is_not_needed(self):
        result = assess_adhesive_repair(
            repair(compound=compound(electrically_conductive=True))
        )
        self.assertEqual(result["disposition"], "permitted")

    def test_spec_keys_are_required(self):
        for key in ("compound", "use_date", "cure_minutes", "footprint_mm2"):
            spec = repair()
            del spec[key]
            with self.assertRaises(ValueError):
                assess_adhesive_repair(spec)

    def test_an_inverted_bond_line_window_is_refused(self):
        with self.assertRaises(ValueError):
            assess_adhesive_repair(repair(bond_line_window_um=(125.0, 25.0)))

    def test_non_boolean_site_flags_are_refused(self):
        with self.assertRaises(ValueError):
            assess_adhesive_repair(repair(site_cleaned="yes"))
        with self.assertRaises(ValueError):
            assess_adhesive_repair(repair(isolation_required="no"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
