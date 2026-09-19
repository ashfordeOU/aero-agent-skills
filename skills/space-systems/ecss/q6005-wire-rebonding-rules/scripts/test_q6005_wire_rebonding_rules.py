#!/usr/bin/env python3
"""Gate 3 contract test for q6005-wire-rebonding-rules.

Offline, stdlib unittest. Exercises the bond geometry validation, the pad
attempt allowance, the accumulated footprint budget, the stacking and remnant
rules, the wire-to-pad metal caution and the per-site and overall disposition
of ECSS-Q-ST-60-05C clause 10.5.3 as paraphrased in the logic module. A pad
filled exactly by its bonds lands on a utilisation of one, so that bound is
asserted with assertAlmostEqual rather than a strict inequality that libm
could round either way between the build host and the CI runner.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_wire_rebonding_rules_logic import (  # noqa: E402
    PAD_KINDS,
    assess_bond_site,
    assess_rebonding,
    attempts_allowed,
    attempts_used,
    bond_footprint_um2,
    consumed_area_um2,
    footprint_utilisation,
    pad_area_um2,
    rebonds_remaining,
    validate_bond,
    validate_bond_site,
)

WEDGE = {"bond_type": "wedge", "width_um": 50.0, "length_um": 100.0}
BALL = {"bond_type": "ball", "diameter_um": 60.0}


def site(**overrides):
    record = {
        "site_id": "P12",
        "pad_kind": "chip-pad",
        "pad_width_um": 100.0,
        "pad_length_um": 100.0,
        "prior_bonds": [],
        "remnant_removed": True,
        "over_previous_footprint": False,
        "wire_material": "aluminium",
        "pad_metallisation": "aluminium",
    }
    record.update(overrides)
    return record


def work(**overrides):
    """One clean first rebond on an empty, remnant-free chip pad."""
    spec = {
        "sites": [{"site": site(prior_bonds=[dict(WEDGE)]), "proposed_bond": dict(WEDGE)}],
        "approved_procedure": True,
    }
    spec.update(overrides)
    return spec


class BondGeometryTests(unittest.TestCase):
    def test_bond_must_be_a_mapping_with_a_type(self):
        with self.assertRaises(ValueError):
            validate_bond(["wedge", 50, 100])
        with self.assertRaises(ValueError):
            validate_bond({"width_um": 50.0, "length_um": 100.0})

    def test_unknown_bond_type_is_refused(self):
        with self.assertRaises(ValueError):
            validate_bond({"bond_type": "stitch", "width_um": 10.0})

    def test_missing_or_non_positive_dimensions_are_refused(self):
        with self.assertRaises(ValueError):
            validate_bond({"bond_type": "ball"})
        with self.assertRaises(ValueError):
            validate_bond({"bond_type": "ball", "diameter_um": 0.0})
        with self.assertRaises(ValueError):
            validate_bond({"bond_type": "wedge", "width_um": 50.0, "length_um": -1.0})

    def test_wedge_footprint_is_the_rectangle(self):
        self.assertAlmostEqual(bond_footprint_um2(WEDGE), 5000.0, places=9)

    def test_ball_footprint_is_the_disc(self):
        self.assertAlmostEqual(bond_footprint_um2(BALL), math.pi * 30.0 * 30.0, places=9)


class SiteValidationTests(unittest.TestCase):
    def test_missing_site_key_is_refused(self):
        for key in ("site_id", "pad_kind", "pad_width_um", "pad_length_um"):
            record = site()
            del record[key]
            with self.assertRaises(ValueError):
                validate_bond_site(record)

    def test_unknown_pad_kind_is_refused(self):
        with self.assertRaises(ValueError):
            validate_bond_site(site(pad_kind="feedthrough"))

    def test_prior_bonds_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            validate_bond_site(site(prior_bonds=dict(WEDGE)))

    def test_an_over_bonded_pad_validates_rather_than_raising(self):
        record = validate_bond_site(site(prior_bonds=[dict(WEDGE), dict(WEDGE), dict(WEDGE)]))
        self.assertEqual(len(record["prior_bonds"]), 3)

    def test_pad_area_is_the_bondable_rectangle(self):
        self.assertAlmostEqual(pad_area_um2(site()), 10000.0, places=9)


class AllowanceTests(unittest.TestCase):
    def test_attempt_allowance_differs_by_pad_kind(self):
        self.assertEqual(attempts_allowed("chip-pad"), 2)
        self.assertEqual(attempts_allowed("substrate-pad"), 3)
        self.assertEqual(attempts_allowed("package-post"), 3)

    def test_unknown_pad_kind_has_no_allowance(self):
        with self.assertRaises(ValueError):
            attempts_allowed("feedthrough")

    def test_attempts_used_counts_bonds_not_successes(self):
        self.assertEqual(attempts_used(site(prior_bonds=[dict(WEDGE), dict(WEDGE)])), 2)

    def test_rebonds_remaining_never_goes_negative(self):
        self.assertEqual(rebonds_remaining(site()), 2)
        self.assertEqual(rebonds_remaining(site(prior_bonds=[dict(WEDGE)])), 1)
        self.assertEqual(
            rebonds_remaining(site(prior_bonds=[dict(WEDGE), dict(WEDGE), dict(WEDGE)])), 0
        )


class AreaBudgetTests(unittest.TestCase):
    def test_consumed_area_sums_the_prior_footprints(self):
        self.assertAlmostEqual(
            consumed_area_um2(site(prior_bonds=[dict(WEDGE), dict(WEDGE)])), 10000.0, places=9
        )

    def test_a_pad_filled_exactly_lands_on_a_utilisation_of_one(self):
        utilisation = footprint_utilisation(site(prior_bonds=[dict(WEDGE)]), dict(WEDGE))
        self.assertAlmostEqual(utilisation, 1.0, places=9)

    def test_a_pad_filled_exactly_still_accepts_the_bond(self):
        result = assess_bond_site(site(prior_bonds=[dict(WEDGE)]), dict(WEDGE))
        self.assertEqual(result["refusals"], [])
        self.assertEqual(result["disposition"], "rebond-permitted")

    def test_a_bond_that_overflows_the_pad_is_refused(self):
        oversized = {"bond_type": "wedge", "width_um": 60.0, "length_um": 100.0}
        result = assess_bond_site(site(prior_bonds=[dict(WEDGE)]), oversized)
        self.assertFalse(result["permitted"])
        self.assertTrue(any("does not fit" in r for r in result["refusals"]))


class PlacementRuleTests(unittest.TestCase):
    def test_a_spent_allowance_refuses_the_rebond(self):
        result = assess_bond_site(
            site(pad_width_um=400.0, prior_bonds=[dict(WEDGE), dict(WEDGE)]), dict(WEDGE)
        )
        self.assertFalse(result["permitted"])
        self.assertTrue(any("permitted attempts" in r for r in result["refusals"]))

    def test_an_unremoved_remnant_refuses_the_rebond(self):
        result = assess_bond_site(
            site(prior_bonds=[dict(WEDGE)], remnant_removed=False), dict(WEDGE)
        )
        self.assertTrue(any("remnant" in r for r in result["refusals"]))

    def test_stacking_is_refused_on_a_chip_pad_and_allowed_on_a_post(self):
        stacked_chip = assess_bond_site(
            site(prior_bonds=[dict(WEDGE)], over_previous_footprint=True), dict(WEDGE)
        )
        self.assertFalse(stacked_chip["permitted"])
        stacked_post = assess_bond_site(
            site(
                pad_kind="package-post",
                prior_bonds=[dict(WEDGE)],
                over_previous_footprint=True,
            ),
            dict(WEDGE),
        )
        self.assertTrue(stacked_post["permitted"])

    def test_a_first_bond_on_a_bare_pad_needs_no_remnant_removal(self):
        result = assess_bond_site(site(prior_bonds=[], remnant_removed=False), dict(WEDGE))
        self.assertEqual(result["disposition"], "rebond-permitted")

    def test_a_mixed_metal_pairing_is_a_caution_not_a_refusal(self):
        result = assess_bond_site(
            site(prior_bonds=[dict(WEDGE)], wire_material="gold", pad_metallisation="aluminium"),
            dict(WEDGE),
        )
        self.assertEqual(result["disposition"], "rebond-permitted-with-caution")
        self.assertTrue(result["permitted"])
        self.assertEqual(len(result["cautions"]), 1)

    def test_a_like_metal_pairing_raises_no_caution(self):
        result = assess_bond_site(
            site(prior_bonds=[dict(WEDGE)], wire_material="gold", pad_metallisation="gold"),
            dict(WEDGE),
        )
        self.assertEqual(result["cautions"], [])


class OverallDispositionTests(unittest.TestCase):
    def test_a_clean_single_site_rebond_is_permitted(self):
        result = assess_rebonding(work())
        self.assertEqual(result["disposition"], "permitted")
        self.assertEqual(result["refused_sites"], [])

    def test_an_unapproved_procedure_blocks_every_site(self):
        result = assess_rebonding(work(approved_procedure=False))
        self.assertEqual(result["disposition"], "not-permitted")

    def test_one_refused_site_blocks_the_whole_corrective_work(self):
        spec = work(
            sites=[
                {"site": site(prior_bonds=[dict(WEDGE)]), "proposed_bond": dict(WEDGE)},
                {
                    "site": site(
                        site_id="P13", prior_bonds=[dict(WEDGE)], remnant_removed=False
                    ),
                    "proposed_bond": dict(WEDGE),
                },
            ]
        )
        result = assess_rebonding(spec)
        self.assertEqual(result["disposition"], "not-permitted")
        self.assertEqual(result["refused_sites"], ["p13"])

    def test_a_cautioned_site_reports_but_does_not_block(self):
        spec = work(
            sites=[
                {
                    "site": site(
                        prior_bonds=[dict(WEDGE)],
                        wire_material="gold",
                        pad_metallisation="aluminium",
                    ),
                    "proposed_bond": dict(WEDGE),
                }
            ]
        )
        result = assess_rebonding(spec)
        self.assertEqual(result["disposition"], "permitted-with-caution")
        self.assertTrue(result["permitted"])
        self.assertEqual(result["cautioned_sites"], ["p12"])

    def test_empty_or_malformed_site_lists_are_refused(self):
        with self.assertRaises(ValueError):
            assess_rebonding({"sites": []})
        with self.assertRaises(ValueError):
            assess_rebonding({"sites": [{"site": site()}]})
        with self.assertRaises(ValueError):
            assess_rebonding({})

    def test_non_boolean_procedure_flag_is_refused(self):
        with self.assertRaises(ValueError):
            assess_rebonding(work(approved_procedure="yes"))

    def test_allowances_can_be_overridden_per_programme(self):
        relaxed = {
            "chip-pad": {"attempt_allowance": 4, "stacking_permitted": False},
        }
        result = assess_bond_site(
            site(pad_width_um=800.0, prior_bonds=[dict(WEDGE), dict(WEDGE)]),
            dict(WEDGE),
            allowances=relaxed,
        )
        self.assertEqual(result["attempts_allowed"], 4)
        self.assertTrue(result["permitted"])

    def test_pad_kind_table_is_the_single_source_of_the_allowance(self):
        self.assertEqual(
            sorted(PAD_KINDS), ["chip-pad", "package-post", "substrate-pad"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
