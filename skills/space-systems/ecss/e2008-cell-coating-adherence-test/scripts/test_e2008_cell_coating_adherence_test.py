#!/usr/bin/env python3
"""Contract test for the cell coating and contact adherence check (offline).

Walks the clause procedure step by step: the surfaces a specimen has to
have had the method applied to, the refusal of a run that reached only
one of them, the removed-area fraction of each surface against the
allowance that belongs to it, the current the cell gives up where the
antireflection coating came away, the three-step removal grouping, the
specimen verdict, the lot reject allowance and the metallisation rule
that fails a run on its own. This is the gate 3 review evidence for the
leaf.
"""

import copy
import unittest

from e2008_cell_coating_adherence_test_logic import (
    ADHERENCE_SURFACES,
    ANTIREFLECTION_COATING,
    CELL_CONTACT,
    COATING_ADHERENCE_FAILED,
    COATING_ADHERENCE_NOT_EVALUATED,
    COATING_ADHERENCE_PASSED,
    COATING_ADHERENCE_VERDICTS,
    DEFAULT_COATING_ADHERENCE_POLICY,
    DIODE_CONTACT,
    INTACT,
    OVER_ALLOWANCE,
    REMOVAL_CATEGORIES,
    WITHIN_ALLOWANCE,
    categorize_removal,
    coating_current_loss_fraction,
    evaluate_cell_coating_adherence,
    evaluate_specimen,
    removed_area_fraction,
    required_surfaces,
    surface_coverage,
    surface_removal_cap,
    validate_coating_adherence_policy,
)

COATING_AREA_MM2 = 3200.0
CONTACT_AREA_MM2 = 400.0
DIODE_AREA_MM2 = 20.0


def _specimen(
    identifier,
    coating_removed=16.0,
    contact_removed=0.0,
    diode_removed=0.0,
    carries_diode=True,
):
    surfaces = {
        ANTIREFLECTION_COATING: {
            "surface_area_mm2": COATING_AREA_MM2,
            "removed_area_mm2": coating_removed,
            "coated_reflectance": 0.02,
            "bare_reflectance": 0.30,
        },
        CELL_CONTACT: {
            "surface_area_mm2": CONTACT_AREA_MM2,
            "removed_area_mm2": contact_removed,
        },
    }
    if carries_diode:
        surfaces[DIODE_CONTACT] = {
            "surface_area_mm2": DIODE_AREA_MM2,
            "removed_area_mm2": diode_removed,
        }
    return {
        "id": identifier,
        "carries_bypass_diode": carries_diode,
        "surfaces": surfaces,
    }


SOUND_SPECIMENS = [_specimen("s%02d" % index) for index in range(10)]


def _run(specimens):
    return {"lot_id": "lot-8", "specimens": copy.deepcopy(specimens)}


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_coating_adherence_policy(DEFAULT_COATING_ADHERENCE_POLICY),
            DEFAULT_COATING_ADHERENCE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_coating_adherence_policy("default")

    def test_coating_allowance_of_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_COATING_ADHERENCE_POLICY)
        broken["max_coating_removed_fraction"] = 1.0
        with self.assertRaises(ValueError):
            validate_coating_adherence_policy(broken)

    def test_negative_contact_allowance_rejected(self):
        broken = copy.deepcopy(DEFAULT_COATING_ADHERENCE_POLICY)
        broken["max_contact_removed_fraction"] = -0.01
        with self.assertRaises(ValueError):
            validate_coating_adherence_policy(broken)

    def test_reject_allowance_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_COATING_ADHERENCE_POLICY)
        broken["max_reject_fraction"] = 1.2
        with self.assertRaises(ValueError):
            validate_coating_adherence_policy(broken)

    def test_zero_specimen_floor_rejected(self):
        broken = copy.deepcopy(DEFAULT_COATING_ADHERENCE_POLICY)
        broken["min_specimens"] = 0
        with self.assertRaises(ValueError):
            validate_coating_adherence_policy(broken)


class CapTests(unittest.TestCase):
    def test_coating_carries_the_coating_allowance(self):
        self.assertAlmostEqual(
            surface_removal_cap(ANTIREFLECTION_COATING),
            float(DEFAULT_COATING_ADHERENCE_POLICY["max_coating_removed_fraction"]),
            places=12,
        )

    def test_both_metallisations_carry_the_tighter_allowance(self):
        contact = surface_removal_cap(CELL_CONTACT)
        diode = surface_removal_cap(DIODE_CONTACT)
        self.assertAlmostEqual(contact, diode, places=12)
        self.assertLess(contact, surface_removal_cap(ANTIREFLECTION_COATING))

    def test_unknown_surface_rejected(self):
        with self.assertRaises(ValueError):
            surface_removal_cap("coverglass-face")


class RemovedAreaTests(unittest.TestCase):
    def test_fraction_is_removed_over_surface(self):
        self.assertAlmostEqual(
            removed_area_fraction(16.0, COATING_AREA_MM2), 0.005, places=12
        )

    def test_nothing_removed_gives_zero(self):
        self.assertAlmostEqual(
            removed_area_fraction(0.0, COATING_AREA_MM2), 0.0, places=12
        )

    def test_removed_beyond_the_surface_rejected(self):
        with self.assertRaises(ValueError):
            removed_area_fraction(4000.0, COATING_AREA_MM2)

    def test_zero_surface_area_rejected(self):
        with self.assertRaises(ValueError):
            removed_area_fraction(1.0, 0.0)

    def test_negative_removed_area_rejected(self):
        with self.assertRaises(ValueError):
            removed_area_fraction(-1.0, COATING_AREA_MM2)


class CurrentLossTests(unittest.TestCase):
    def test_no_removal_costs_no_current(self):
        self.assertAlmostEqual(
            coating_current_loss_fraction(0.0, 0.02, 0.30), 0.0, places=12
        )

    def test_loss_scales_with_the_stripped_share(self):
        one = coating_current_loss_fraction(0.01, 0.02, 0.30)
        two = coating_current_loss_fraction(0.02, 0.02, 0.30)
        self.assertAlmostEqual(two, 2.0 * one, places=12)

    def test_loss_follows_the_reflectance_step(self):
        self.assertAlmostEqual(
            coating_current_loss_fraction(0.02, 0.02, 0.30),
            0.02 * 0.28 / 0.98,
            places=12,
        )

    def test_bare_reflectance_not_above_the_coated_one_rejected(self):
        with self.assertRaises(ValueError):
            coating_current_loss_fraction(0.02, 0.30, 0.30)

    def test_reflectance_of_one_rejected(self):
        with self.assertRaises(ValueError):
            coating_current_loss_fraction(0.02, 0.02, 1.0)

    def test_negative_stripped_share_rejected(self):
        with self.assertRaises(ValueError):
            coating_current_loss_fraction(-0.01, 0.02, 0.30)


class RemovalCategoryTests(unittest.TestCase):
    def test_nothing_removed_is_intact(self):
        self.assertEqual(categorize_removal(0.0, 0.02), INTACT)

    def test_small_removal_is_within_allowance(self):
        self.assertEqual(categorize_removal(0.005, 0.02), WITHIN_ALLOWANCE)

    def test_removal_exactly_on_the_allowance_is_within_it(self):
        cap = surface_removal_cap(ANTIREFLECTION_COATING)
        fraction = removed_area_fraction(64.0, COATING_AREA_MM2)
        self.assertAlmostEqual(fraction, cap, places=9)
        self.assertEqual(categorize_removal(fraction, cap), WITHIN_ALLOWANCE)

    def test_large_removal_is_over_allowance(self):
        self.assertEqual(categorize_removal(0.2, 0.02), OVER_ALLOWANCE)

    def test_every_category_is_reachable(self):
        seen = {
            categorize_removal(value, 0.02) for value in (0.0, 0.005, 0.2)
        }
        self.assertEqual(seen, set(REMOVAL_CATEGORIES))

    def test_negative_cap_rejected(self):
        with self.assertRaises(ValueError):
            categorize_removal(0.01, -0.02)


class CoverageTests(unittest.TestCase):
    def test_a_diode_cell_needs_all_three_surfaces(self):
        self.assertEqual(
            required_surfaces(_specimen("s1")), ADHERENCE_SURFACES
        )

    def test_a_cell_without_a_diode_needs_two(self):
        self.assertEqual(
            required_surfaces(_specimen("s2", carries_diode=False)),
            (ANTIREFLECTION_COATING, CELL_CONTACT),
        )

    def test_full_coverage_is_complete(self):
        result = surface_coverage(_specimen("s3"))
        self.assertTrue(result["complete"])
        self.assertEqual(result["findings"], [])

    def test_a_coating_only_run_is_incomplete(self):
        specimen = _specimen("s4")
        del specimen["surfaces"][CELL_CONTACT]
        del specimen["surfaces"][DIODE_CONTACT]
        result = surface_coverage(specimen)
        self.assertFalse(result["complete"])
        self.assertEqual(set(result["missing"]), {CELL_CONTACT, DIODE_CONTACT})

    def test_a_diode_surface_on_a_diodeless_cell_is_flagged(self):
        specimen = _specimen("s5", carries_diode=False)
        specimen["surfaces"][DIODE_CONTACT] = {
            "surface_area_mm2": DIODE_AREA_MM2,
            "removed_area_mm2": 0.0,
        }
        result = surface_coverage(specimen)
        self.assertFalse(result["complete"])
        self.assertEqual(result["unexpected"], (DIODE_CONTACT,))

    def test_unknown_surface_name_rejected(self):
        specimen = _specimen("s6")
        specimen["surfaces"]["coverglass-face"] = {}
        with self.assertRaises(ValueError):
            surface_coverage(specimen)


class SpecimenTests(unittest.TestCase):
    def test_sound_specimen_is_acceptable(self):
        record = evaluate_specimen(_specimen("s7"))
        self.assertTrue(record["acceptable"])
        self.assertTrue(record["evaluated"])
        self.assertEqual(record["surface_categories"][CELL_CONTACT], INTACT)

    def test_contact_removal_on_the_allowance_stays_acceptable(self):
        record = evaluate_specimen(_specimen("s8", contact_removed=2.0))
        self.assertAlmostEqual(
            record["surface_removed_fraction"][CELL_CONTACT],
            surface_removal_cap(CELL_CONTACT),
            places=9,
        )
        self.assertEqual(
            record["surface_categories"][CELL_CONTACT], WITHIN_ALLOWANCE
        )
        self.assertTrue(record["acceptable"])

    def test_lifted_metallisation_is_named(self):
        record = evaluate_specimen(_specimen("s9", contact_removed=40.0))
        self.assertEqual(record["over_allowance_surfaces"], (CELL_CONTACT,))
        self.assertFalse(record["acceptable"])
        self.assertTrue(any("past the" in note for note in record["findings"]))

    def test_coating_loss_past_the_allowance_fails_the_specimen(self):
        record = evaluate_specimen(_specimen("s10", coating_removed=320.0))
        self.assertEqual(
            record["surface_categories"][ANTIREFLECTION_COATING], OVER_ALLOWANCE
        )
        self.assertFalse(record["acceptable"])

    def test_current_loss_is_reported_with_the_specimen(self):
        record = evaluate_specimen(_specimen("s11", coating_removed=64.0))
        self.assertAlmostEqual(
            record["current_loss_fraction"], 0.02 * 0.28 / 0.98, places=12
        )
        self.assertTrue(record["current_loss_within_allowance"])

    def test_an_incomplete_specimen_is_not_evaluated(self):
        specimen = _specimen("s12")
        del specimen["surfaces"][DIODE_CONTACT]
        record = evaluate_specimen(specimen)
        self.assertFalse(record["evaluated"])
        self.assertIsNone(record["acceptable"])
        self.assertEqual(record["missing_surfaces"], (DIODE_CONTACT,))

    def test_non_mapping_specimen_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_specimen("tape applied, nothing came off")


class RunTests(unittest.TestCase):
    def test_sound_run_passes(self):
        result = evaluate_cell_coating_adherence(_run(SOUND_SPECIMENS))
        self.assertEqual(result["verdict"], COATING_ADHERENCE_PASSED)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["rejected_specimen_ids"], [])

    def test_one_coating_reject_exactly_on_the_allowance_passes(self):
        specimens = copy.deepcopy(SOUND_SPECIMENS)
        specimens[2]["surfaces"][ANTIREFLECTION_COATING][
            "removed_area_mm2"
        ] = 320.0
        result = evaluate_cell_coating_adherence(_run(specimens))
        self.assertAlmostEqual(
            result["reject_fraction"],
            float(DEFAULT_COATING_ADHERENCE_POLICY["max_reject_fraction"]),
            places=9,
        )
        self.assertEqual(result["verdict"], COATING_ADHERENCE_PASSED)
        self.assertEqual(result["rejected_specimen_ids"], ["s02"])

    def test_too_many_coating_rejects_fail_the_run(self):
        specimens = copy.deepcopy(SOUND_SPECIMENS)
        for index in range(3):
            specimens[index]["surfaces"][ANTIREFLECTION_COATING][
                "removed_area_mm2"
            ] = 320.0
        result = evaluate_cell_coating_adherence(_run(specimens))
        self.assertEqual(result["verdict"], COATING_ADHERENCE_FAILED)
        self.assertTrue(
            any("rejected share" in note for note in result["findings"])
        )

    def test_one_lifted_metallisation_fails_the_run_on_its_own(self):
        specimens = copy.deepcopy(SOUND_SPECIMENS)
        specimens[5]["surfaces"][DIODE_CONTACT]["removed_area_mm2"] = 8.0
        result = evaluate_cell_coating_adherence(_run(specimens))
        self.assertEqual(result["verdict"], COATING_ADHERENCE_FAILED)
        self.assertEqual(result["metallisation_loss_specimen_ids"], ["s05"])

    def test_a_specimen_missing_a_surface_stops_the_run(self):
        specimens = copy.deepcopy(SOUND_SPECIMENS)
        del specimens[1]["surfaces"][CELL_CONTACT]
        result = evaluate_cell_coating_adherence(_run(specimens))
        self.assertEqual(result["verdict"], COATING_ADHERENCE_NOT_EVALUATED)
        self.assertIsNone(result["compliant"])
        self.assertEqual(result["unevaluated_specimen_ids"], ["s01"])

    def test_too_few_specimens_stops_the_run(self):
        result = evaluate_cell_coating_adherence(_run(SOUND_SPECIMENS[:2]))
        self.assertEqual(result["verdict"], COATING_ADHERENCE_NOT_EVALUATED)
        self.assertTrue(
            any("under the floor" in note for note in result["findings"])
        )

    def test_mean_current_loss_is_reported(self):
        result = evaluate_cell_coating_adherence(_run(SOUND_SPECIMENS))
        expected = sum(
            record["current_loss_fraction"] for record in result["specimens"]
        ) / len(result["specimens"])
        self.assertAlmostEqual(
            result["mean_current_loss_fraction"], expected, places=12
        )

    def test_every_verdict_is_reachable(self):
        lifted = copy.deepcopy(SOUND_SPECIMENS)
        lifted[0]["surfaces"][CELL_CONTACT]["removed_area_mm2"] = 40.0
        seen = {
            evaluate_cell_coating_adherence(run)["verdict"]
            for run in (
                _run(SOUND_SPECIMENS),
                _run(lifted),
                _run(SOUND_SPECIMENS[:1]),
            )
        }
        self.assertEqual(seen, set(COATING_ADHERENCE_VERDICTS))

    def test_run_without_specimens_rejected(self):
        run = _run(SOUND_SPECIMENS)
        run["specimens"] = []
        with self.assertRaises(ValueError):
            evaluate_cell_coating_adherence(run)

    def test_non_mapping_run_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_cell_coating_adherence("ten specimens, tape method")


if __name__ == "__main__":
    unittest.main()
