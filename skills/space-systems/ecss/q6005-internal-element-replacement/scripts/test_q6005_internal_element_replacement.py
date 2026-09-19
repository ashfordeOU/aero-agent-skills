#!/usr/bin/env python3
"""Gate 3 contract test for q6005-internal-element-replacement.

Offline, stdlib unittest. Exercises the repair-site validation, the
replacement and thermal-excursion allowances, the keep-out neighbourhood
search, the heat-exposure filter and the three-way disposition of
ECSS-Q-ST-60-05C clause 10.5.2 as paraphrased in the logic module. A part
placed on the nominal keep-out radius is asserted with assertAlmostEqual
rather than a strict inequality: a Euclidean distance that should land on the
radius is not guaranteed to on every platform, and a strict assertion there
would go red on one host and green on another.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_internal_element_replacement_logic import (  # noqa: E402
    ATTACH_METHODS,
    BASE_VERIFICATIONS,
    DEFAULT_KEEP_OUT_MM,
    assess_element_replacement,
    excursion_cost,
    heat_exposed_neighbours,
    neighbours_within_keep_out,
    projected_thermal_cycles,
    replacements_remaining,
    required_verifications,
    thermal_headroom,
    validate_attach_method,
    validate_elements,
    validate_site,
)


def site(**overrides):
    record = {
        "site_id": "U7",
        "attach_method": "adhesive",
        "position_mm": (0.0, 0.0),
        "prior_replacements": 0,
        "prior_thermal_cycles": 0,
        "residue_removal_confirmed": True,
    }
    record.update(overrides)
    return record


def element(element_id="C3", position=(5.0, 0.0), limit=200.0, shielded=False):
    return {
        "element_id": element_id,
        "position_mm": position,
        "temperature_limit_c": limit,
        "shielded": shielded,
    }


def repair(**overrides):
    """A clean first-time adhesive replacement with no near neighbours."""
    spec = {
        "site": site(),
        "elements": [element()],
        "replacement_part": {"from_accepted_lot": True, "site_accessible": True},
        "approved_procedure": True,
    }
    spec.update(overrides)
    return spec


class SiteValidationTests(unittest.TestCase):
    def test_site_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_site(["U7", "adhesive"])

    def test_missing_site_key_is_refused(self):
        for key in ("site_id", "attach_method", "position_mm"):
            record = site()
            del record[key]
            with self.assertRaises(ValueError):
                validate_site(record)

    def test_position_must_be_a_pair(self):
        for bad in ((1.0,), (1.0, 2.0, 3.0), "0,0", {"x": 1, "y": 2}):
            with self.assertRaises(ValueError):
                validate_site(site(position_mm=bad))

    def test_unknown_attach_method_is_refused(self):
        with self.assertRaises(ValueError):
            validate_attach_method("welded")

    def test_attach_method_is_normalised_to_lower_case(self):
        self.assertEqual(validate_attach_method("Eutectic"), "eutectic")

    def test_negative_history_is_refused_but_history_itself_is_not(self):
        with self.assertRaises(ValueError):
            validate_site(site(prior_replacements=-1))
        self.assertEqual(validate_site(site(prior_replacements=4))["prior_replacements"], 4)

    def test_boolean_history_is_not_an_integer_count(self):
        with self.assertRaises(ValueError):
            validate_site(site(prior_thermal_cycles=True))

    def test_element_records_are_validated(self):
        with self.assertRaises(ValueError):
            validate_elements({"element_id": "C3"})
        with self.assertRaises(ValueError):
            validate_elements([{"element_id": "C3", "position_mm": (1.0, 1.0)}])
        with self.assertRaises(ValueError):
            validate_elements([element(limit=-5.0)])


class AllowanceTests(unittest.TestCase):
    def test_excursion_cost_depends_on_the_attach_method(self):
        self.assertEqual(excursion_cost("adhesive"), 1)
        self.assertEqual(excursion_cost("eutectic"), 2)
        self.assertEqual(excursion_cost("solder"), 2)

    def test_replacements_remaining_never_goes_negative(self):
        self.assertEqual(replacements_remaining(site(prior_replacements=0)), 1)
        self.assertEqual(replacements_remaining(site(prior_replacements=1)), 0)
        self.assertEqual(replacements_remaining(site(prior_replacements=9)), 0)

    def test_replacement_limit_is_configurable(self):
        self.assertEqual(replacements_remaining(site(prior_replacements=1), limit=3), 2)

    def test_projected_cycles_add_the_repair_cost_to_the_history(self):
        self.assertEqual(
            projected_thermal_cycles(site(attach_method="eutectic", prior_thermal_cycles=1)), 3
        )

    def test_thermal_headroom_is_negative_once_the_allowance_is_passed(self):
        self.assertEqual(
            thermal_headroom(site(attach_method="eutectic", prior_thermal_cycles=2)), -1
        )
        self.assertEqual(thermal_headroom(site(prior_thermal_cycles=0)), 2)


class KeepOutTests(unittest.TestCase):
    def test_far_elements_are_outside_the_keep_out(self):
        self.assertEqual(neighbours_within_keep_out(site(), [element()]), [])

    def test_near_elements_are_returned_nearest_first(self):
        found = neighbours_within_keep_out(
            site(),
            [element("C1", (1.2, 0.0)), element("C2", (0.4, 0.3))],
        )
        self.assertEqual([item[0] for item in found], ["C2", "C1"])

    def test_an_element_on_the_radius_is_inside_it(self):
        found = neighbours_within_keep_out(site(), [element("C1", (0.9, 1.2))])
        self.assertEqual(len(found), 1)
        self.assertAlmostEqual(found[0][1], DEFAULT_KEEP_OUT_MM, places=9)

    def test_keep_out_radius_is_configurable(self):
        self.assertEqual(
            len(neighbours_within_keep_out(site(), [element("C1", (3.0, 4.0))], keep_out_mm=5.0)),
            1,
        )

    def test_heat_exposure_uses_the_attach_peak_not_the_distance(self):
        near_tolerant = element("C1", (0.5, 0.0), limit=500.0)
        near_fragile = element("C2", (0.5, 0.5), limit=125.0)
        exposed = heat_exposed_neighbours(site(), [near_tolerant, near_fragile])
        self.assertEqual([item["element_id"] for item in exposed], ["C2"])
        self.assertAlmostEqual(
            exposed[0]["attach_peak_c"], ATTACH_METHODS["adhesive"]["peak_c"], places=9
        )

    def test_a_shielded_neighbour_is_not_exposed(self):
        fragile = element("C2", (0.5, 0.0), limit=125.0, shielded=True)
        self.assertEqual(heat_exposed_neighbours(site(), [fragile]), [])

    def test_a_neighbour_at_exactly_the_attach_peak_is_not_exposed(self):
        at_peak = element("C2", (0.5, 0.0), limit=ATTACH_METHODS["adhesive"]["peak_c"])
        self.assertEqual(heat_exposed_neighbours(site(), [at_peak]), [])


class VerificationTests(unittest.TestCase):
    def test_base_verifications_are_always_carried(self):
        self.assertEqual(required_verifications([]), list(BASE_VERIFICATIONS))

    def test_conditions_add_verifications(self):
        verifications = required_verifications(["heat-exposed-neighbours", "second-replacement"])
        self.assertIn("visual-check-of-elements-inside-the-keep-out-radius", verifications)
        self.assertIn("substrate-metallisation-adhesion-check-at-the-site", verifications)

    def test_conditions_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            required_verifications("heat-exposed-neighbours")


class DispositionTests(unittest.TestCase):
    def test_a_clean_first_replacement_is_permitted(self):
        result = assess_element_replacement(repair())
        self.assertEqual(result["disposition"], "permitted")
        self.assertTrue(result["permitted"])
        self.assertEqual(result["blockers"], [])

    def test_missing_approved_procedure_blocks_the_repair(self):
        result = assess_element_replacement(repair(approved_procedure=False))
        self.assertEqual(result["disposition"], "not-permitted")
        self.assertTrue(any("approved repair procedure" in b for b in result["blockers"]))

    def test_an_exhausted_site_allowance_blocks_the_repair(self):
        result = assess_element_replacement(repair(site=site(prior_replacements=1)))
        self.assertFalse(result["permitted"])
        self.assertTrue(any("no attempt remains" in b for b in result["blockers"]))

    def test_thermal_allowance_overrun_blocks_the_repair(self):
        result = assess_element_replacement(
            repair(site=site(attach_method="eutectic", prior_thermal_cycles=2))
        )
        self.assertEqual(result["disposition"], "not-permitted")
        self.assertEqual(result["thermal_headroom"], -1)

    def test_a_part_outside_an_accepted_lot_blocks_the_repair(self):
        result = assess_element_replacement(
            repair(replacement_part={"from_accepted_lot": False, "site_accessible": True})
        )
        self.assertFalse(result["permitted"])

    def test_an_inaccessible_element_blocks_the_repair(self):
        result = assess_element_replacement(
            repair(replacement_part={"from_accepted_lot": True, "site_accessible": False})
        )
        self.assertTrue(any("not accessible" in b for b in result["blockers"]))

    def test_a_fragile_near_neighbour_makes_it_conditional_not_forbidden(self):
        result = assess_element_replacement(
            repair(elements=[element("C2", (0.5, 0.0), limit=125.0)])
        )
        self.assertEqual(result["disposition"], "permitted-with-conditions")
        self.assertIn("heat-exposed-neighbours", result["conditions"])
        self.assertIn(
            "visual-check-of-elements-inside-the-keep-out-radius", result["verifications"]
        )

    def test_unconfirmed_residue_removal_makes_it_conditional(self):
        result = assess_element_replacement(
            repair(site=site(residue_removal_confirmed=False))
        )
        self.assertEqual(result["disposition"], "permitted-with-conditions")
        self.assertIn("residue-unconfirmed", result["conditions"])

    def test_spec_keys_are_required(self):
        for key in ("site", "elements", "replacement_part"):
            spec = repair()
            del spec[key]
            with self.assertRaises(ValueError):
                assess_element_replacement(spec)

    def test_non_boolean_procedure_flag_is_refused(self):
        with self.assertRaises(ValueError):
            assess_element_replacement(repair(approved_procedure="yes"))

    def test_result_reports_the_attach_peak_for_the_method_used(self):
        result = assess_element_replacement(repair(site=site(attach_method="solder")))
        self.assertAlmostEqual(
            result["attach_peak_c"], ATTACH_METHODS["solder"]["peak_c"], places=9
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
