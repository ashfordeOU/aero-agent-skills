"""Contract tests for the paint stripping and re-painting logic.

The cases take one part through a strip: whether the method may be pointed at
that substrate at all, what the cumulative loss leaves of the wall the drawing
keeps, how many further strips the part will carry, whether the stripped
surface lands in the roughness window the new primer needs, and whether the
primer and topcoat going back on are compatible with the substrate and with
each other.
"""

import unittest

from q7031_stripping_and_repainting_logic import (
    PRIMER_FAMILIES,
    STRIP_METHODS,
    SUBSTRATES,
    assess_strip_and_repaint,
    assess_strip_campaign,
    cumulative_material_loss_um,
    method_permitted_for_substrate,
    remaining_wall_margin_um,
    repaint_system_findings,
    roughness_within_window,
    strip_cycles_remaining,
    validate_method,
    validate_substrate,
)


def _job(**overrides):
    job = {
        "name": "bracket-7742",
        "substrate": "aluminium-alloy",
        "method": "plastic-media-blast",
        "approved_procedure": True,
        "cycles": 1,
        "loss_per_cycle_um": 5.0,
        "prior_loss_um": 0.0,
        "nominal_thickness_um": 2000.0,
        "minimum_thickness_um": 1900.0,
        "roughness_ra_um": 2.5,
        "roughness_window_um": (1.5, 4.0),
        "primer": "epoxy-primer",
        "topcoat": "polyurethane-topcoat",
        "residual_coating_removed": True,
    }
    job.update(overrides)
    return job


class MethodMatrixTests(unittest.TestCase):
    def test_every_substrate_and_method_pair_has_a_standing(self):
        for substrate in SUBSTRATES:
            for method in STRIP_METHODS:
                self.assertIn(
                    method_permitted_for_substrate(method, substrate),
                    ("permitted", "conditional", "prohibited"),
                )

    def test_alkaline_chemistry_is_prohibited_on_aluminium(self):
        self.assertEqual(
            method_permitted_for_substrate("chemical-alkaline", "aluminium-alloy"), "prohibited"
        )

    def test_abrasive_blast_is_prohibited_on_a_carbon_composite(self):
        self.assertEqual(
            method_permitted_for_substrate("abrasive-blast", "cfrp"), "prohibited"
        )

    def test_plastic_media_on_a_composite_is_conditional_not_free(self):
        self.assertEqual(
            method_permitted_for_substrate("plastic-media-blast", "cfrp"), "conditional"
        )

    def test_case_is_not_significant_in_a_substrate_name(self):
        self.assertEqual(validate_substrate("Aluminium-Alloy"), "aluminium-alloy")

    def test_an_unknown_method_is_refused(self):
        with self.assertRaises(ValueError):
            validate_method("wire-brush-and-hope")

    def test_an_unknown_substrate_is_refused(self):
        with self.assertRaises(ValueError):
            validate_substrate("unobtainium")


class WallBudgetTests(unittest.TestCase):
    def test_loss_is_cycles_times_the_per_cycle_loss(self):
        self.assertAlmostEqual(cumulative_material_loss_um(3, 5.0), 15.0, places=9)

    def test_earlier_strips_are_carried_into_the_loss(self):
        self.assertAlmostEqual(cumulative_material_loss_um(2, 5.0, 20.0), 30.0, places=9)

    def test_a_zero_cycle_strip_is_refused(self):
        with self.assertRaises(ValueError):
            cumulative_material_loss_um(0, 5.0)

    def test_a_boolean_cycle_count_is_refused(self):
        with self.assertRaises(ValueError):
            cumulative_material_loss_um(True, 5.0)

    def test_margin_is_what_is_left_above_the_minimum_wall(self):
        self.assertAlmostEqual(remaining_wall_margin_um(2000.0, 1900.0, 30.0), 70.0, places=9)

    def test_a_loss_that_lands_exactly_on_the_minimum_leaves_no_margin(self):
        margin = remaining_wall_margin_um(2000.0, 1900.0, 100.0)
        self.assertAlmostEqual(margin, 0.0, places=9)

    def test_a_minimum_above_the_nominal_is_refused(self):
        with self.assertRaises(ValueError):
            remaining_wall_margin_um(1900.0, 2000.0, 0.0)

    def test_further_cycles_are_whole_strips_only(self):
        self.assertEqual(strip_cycles_remaining(23.0, 5.0), 4)

    def test_a_margin_of_exactly_three_cycles_credits_three(self):
        self.assertEqual(strip_cycles_remaining(15.0, 5.0), 3)

    def test_a_consumed_margin_credits_no_further_cycles(self):
        self.assertEqual(strip_cycles_remaining(0.0, 5.0), 0)

    def test_a_non_positive_per_cycle_loss_is_refused(self):
        with self.assertRaises(ValueError):
            strip_cycles_remaining(20.0, 0.0)


class SurfaceAndSystemTests(unittest.TestCase):
    def test_a_roughness_inside_the_window_passes(self):
        self.assertTrue(roughness_within_window(2.5, (1.5, 4.0)))

    def test_both_window_edges_are_inside(self):
        self.assertTrue(roughness_within_window(1.5, (1.5, 4.0)))
        self.assertTrue(roughness_within_window(4.0, (1.5, 4.0)))

    def test_a_surface_polished_below_the_window_fails(self):
        self.assertFalse(roughness_within_window(0.2, (1.5, 4.0)))

    def test_an_inverted_window_is_refused(self):
        with self.assertRaises(ValueError):
            roughness_within_window(2.5, (4.0, 1.5))

    def test_a_compatible_system_raises_nothing(self):
        self.assertEqual(
            repaint_system_findings("epoxy-primer", "polyurethane-topcoat", "aluminium-alloy"), []
        )

    def test_a_primer_that_does_not_bond_to_the_substrate_is_raised(self):
        self.assertIn(
            "primer-substrate-incompatible",
            repaint_system_findings("silicate-primer", "inorganic-black-topcoat", "cfrp"),
        )

    def test_a_topcoat_the_primer_will_not_carry_is_raised(self):
        self.assertIn(
            "topcoat-primer-incompatible",
            repaint_system_findings("epoxy-primer", "inorganic-white-topcoat", "aluminium-alloy"),
        )

    def test_every_primer_family_lists_substrates_and_topcoats(self):
        for family in PRIMER_FAMILIES.values():
            self.assertTrue(family["substrates"])
            self.assertTrue(family["topcoats"])

    def test_an_unknown_primer_family_is_refused(self):
        with self.assertRaises(ValueError):
            repaint_system_findings("house-paint", "polyurethane-topcoat", "aluminium-alloy")


class JobDispositionTests(unittest.TestCase):
    def test_a_compliant_job_is_approved(self):
        result = assess_strip_and_repaint(_job())
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["disposition"], "strip-and-repaint-approved")
        self.assertTrue(result["approved"])

    def test_a_prohibited_method_is_refused(self):
        result = assess_strip_and_repaint(_job(method="chemical-alkaline"))
        self.assertIn("method-prohibited-on-substrate", result["findings"])
        self.assertEqual(result["disposition"], "refused")

    def test_a_conditional_method_without_a_procedure_leaves_conditions_open(self):
        result = assess_strip_and_repaint(
            _job(method="abrasive-blast", approved_procedure=False)
        )
        self.assertIn("conditional-method-without-approved-procedure", result["findings"])
        self.assertEqual(result["disposition"], "conditions-outstanding")

    def test_a_strip_that_eats_the_wall_is_refused(self):
        result = assess_strip_and_repaint(_job(prior_loss_um=200.0))
        self.assertIn("wall-margin-consumed", result["findings"])
        self.assertEqual(result["disposition"], "refused")

    def test_further_cycles_are_reported_from_the_remaining_margin(self):
        result = assess_strip_and_repaint(_job(loss_per_cycle_um=5.0, prior_loss_um=0.0))
        self.assertAlmostEqual(result["wall_margin_um"], 95.0, places=9)
        self.assertEqual(result["further_cycles_available"], 19)

    def test_an_unverified_surface_is_a_finding_not_a_pass(self):
        result = assess_strip_and_repaint(_job(roughness_window_um=None))
        self.assertIn("surface-roughness-not-verified", result["findings"])

    def test_unconfirmed_residual_removal_is_raised(self):
        result = assess_strip_and_repaint(_job(residual_coating_removed=False))
        self.assertIn("residual-coating-not-confirmed-removed", result["findings"])

    def test_a_job_without_a_name_is_refused(self):
        with self.assertRaises(ValueError):
            assess_strip_and_repaint(_job(name=""))

    def test_a_non_mapping_job_is_refused(self):
        with self.assertRaises(ValueError):
            assess_strip_and_repaint("bracket-7742")


class CampaignTests(unittest.TestCase):
    def test_a_campaign_of_compliant_jobs_is_approved(self):
        campaign = assess_strip_campaign([_job(), _job(name="bracket-7743")])
        self.assertTrue(campaign["campaign_approved"])
        self.assertEqual(campaign["refused_jobs"], [])

    def test_one_refused_job_fails_the_campaign(self):
        campaign = assess_strip_campaign([
            _job(),
            _job(name="panel-cfrp-01", substrate="cfrp", method="abrasive-blast"),
        ])
        self.assertFalse(campaign["campaign_approved"])
        self.assertEqual(campaign["refused_jobs"], ["panel-cfrp-01"])

    def test_duplicate_job_names_are_refused(self):
        with self.assertRaises(ValueError):
            assess_strip_campaign([_job(), _job()])

    def test_an_empty_campaign_is_refused(self):
        with self.assertRaises(ValueError):
            assess_strip_campaign([])


if __name__ == "__main__":
    unittest.main()
