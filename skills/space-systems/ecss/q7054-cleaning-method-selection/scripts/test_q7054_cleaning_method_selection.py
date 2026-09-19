"""Contract tests for the ultracleaning method selection logic."""

import unittest

from q7054_cleaning_method_selection_logic import (
    METHOD_CATALOGUE,
    REJECT_INCOMPATIBLE,
    REJECT_INEFFECTIVE,
    REJECT_LEVEL,
    REJECT_RESIDUE,
    REJECT_UNREACHABLE,
    method_score,
    rank_cleaning_methods,
    screen_method,
    validate_request,
)


def base_request(**overrides):
    """Particulate on an open aluminium surface, level 50 and 0.1 mg."""
    request = {
        "contaminant": "particulate",
        "substrate": "aluminium-alloy",
        "geometry": "open-surface",
        "required_particulate_level_um": 50.0,
        "required_nvr_mg_per_01m2": 0.10,
    }
    request.update(overrides)
    return request


class RequestValidationTests(unittest.TestCase):
    def test_a_complete_request_validates(self):
        self.assertEqual(validate_request(base_request())["substrate"], "aluminium-alloy")

    def test_unknown_contaminant_rejected(self):
        with self.assertRaises(ValueError):
            validate_request(base_request(contaminant="soot"))

    def test_unknown_substrate_rejected(self):
        with self.assertRaises(ValueError):
            validate_request(base_request(substrate="beryllium"))

    def test_unknown_geometry_rejected(self):
        with self.assertRaises(ValueError):
            validate_request(base_request(geometry="weldment"))

    def test_zero_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_request(base_request(required_particulate_level_um=0.0))

    def test_negative_residue_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_request(base_request(required_nvr_mg_per_01m2=-0.1))

    def test_non_mapping_request_rejected(self):
        with self.assertRaises(ValueError):
            validate_request("particulate on aluminium")


class ScreenTests(unittest.TestCase):
    def test_a_capable_route_survives_every_screen(self):
        self.assertIsNone(
            screen_method("aqueous-detergent-ultrasonic", base_request())
        )

    def test_an_incompatible_substrate_is_the_first_reason(self):
        self.assertEqual(
            screen_method(
                "aqueous-detergent-ultrasonic", base_request(substrate="optical-glass")
            ),
            REJECT_INCOMPATIBLE,
        )

    def test_a_line_of_sight_route_cannot_reach_an_internal_passage(self):
        self.assertEqual(
            screen_method(
                "carbon-dioxide-snow", base_request(geometry="internal-passage")
            ),
            REJECT_UNREACHABLE,
        )

    def test_a_route_that_does_not_touch_the_contaminant_is_dropped(self):
        self.assertEqual(
            screen_method("plasma", base_request(contaminant="ionic-residue")),
            REJECT_INEFFECTIVE,
        )

    def test_a_route_that_cannot_hold_the_level_is_dropped(self):
        self.assertEqual(
            screen_method("precision-solvent-wipe", base_request()), REJECT_LEVEL
        )

    def test_a_route_that_cannot_hold_the_residue_allowance_is_dropped(self):
        self.assertEqual(
            screen_method(
                "carbon-dioxide-snow",
                base_request(required_particulate_level_um=200.0),
            ),
            REJECT_RESIDUE,
        )

    def test_a_capability_landing_exactly_on_the_requirement_passes(self):
        spec = METHOD_CATALOGUE["aqueous-detergent-ultrasonic"]
        request = base_request(
            required_particulate_level_um=spec["achievable_particulate_level_um"],
            required_nvr_mg_per_01m2=spec["achievable_nvr_mg_per_01m2"],
        )
        self.assertIsNone(screen_method("aqueous-detergent-ultrasonic", request))

    def test_an_unknown_method_name_rejected(self):
        with self.assertRaises(ValueError):
            screen_method("steam-jet", base_request())


class ScoreTests(unittest.TestCase):
    def test_scoring_a_screened_out_route_is_refused(self):
        with self.assertRaises(ValueError):
            method_score("precision-solvent-wipe", base_request())

    def test_a_route_with_no_margin_scores_its_removal_less_its_aggressiveness(self):
        score = method_score("aqueous-detergent-ultrasonic", base_request())
        self.assertAlmostEqual(score, 6.0 * 0.95 - 0.4 * 3, places=9)

    def test_margin_raises_the_score(self):
        tight = method_score("aqueous-detergent-ultrasonic", base_request())
        loose = method_score(
            "aqueous-detergent-ultrasonic",
            base_request(required_particulate_level_um=500.0),
        )
        self.assertGreater(loose, tight)

    def test_the_margin_credit_is_capped(self):
        capped = method_score(
            "aqueous-detergent-ultrasonic",
            base_request(
                required_particulate_level_um=50000.0,
                required_nvr_mg_per_01m2=100.0,
            ),
        )
        self.assertAlmostEqual(
            capped, 6.0 * 0.95 + 1.5 * 2.0 + 1.5 * 2.0 - 0.4 * 3, places=9
        )

    def test_a_tighter_requirement_earns_no_negative_margin(self):
        score = method_score(
            "precision-solvent-immersion",
            base_request(
                required_particulate_level_um=25.0, required_nvr_mg_per_01m2=0.05
            ),
        )
        self.assertAlmostEqual(score, 6.0 * 0.70 - 0.4 * 4, places=9)


class RankingTests(unittest.TestCase):
    def test_the_aqueous_route_leads_a_particulate_job(self):
        self.assertEqual(rank_cleaning_methods(base_request())["recommended"], "aqueous-detergent-ultrasonic")

    def test_every_catalogued_route_is_either_ranked_or_rejected(self):
        result = rank_cleaning_methods(base_request())
        self.assertEqual(
            len(result["ranked"]) + len(result["rejected"]), len(METHOD_CATALOGUE)
        )

    def test_the_ranking_is_ordered_by_descending_score(self):
        scores = [entry["score"] for entry in rank_cleaning_methods(base_request())["ranked"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_an_internal_passage_leaves_only_the_wetting_routes(self):
        result = rank_cleaning_methods(
            base_request(geometry="internal-passage", required_nvr_mg_per_01m2=1.0)
        )
        self.assertEqual(
            sorted(entry["method"] for entry in result["ranked"]),
            ["aqueous-detergent-ultrasonic", "precision-solvent-immersion"],
        )

    def test_an_ionic_job_leaves_the_dry_routes_behind(self):
        result = rank_cleaning_methods(
            base_request(contaminant="ionic-residue", required_nvr_mg_per_01m2=1.0)
        )
        rejected = {entry["method"]: entry["reason"] for entry in result["rejected"]}
        self.assertEqual(rejected.get("plasma"), REJECT_INEFFECTIVE)
        self.assertEqual(rejected.get("ultraviolet-ozone"), REJECT_INEFFECTIVE)

    def test_a_silver_coating_keeps_the_gentle_routes_only(self):
        result = rank_cleaning_methods(
            base_request(
                substrate="silver-coating",
                required_particulate_level_um=200.0,
                required_nvr_mg_per_01m2=1.0,
            )
        )
        rejected = {entry["method"]: entry["reason"] for entry in result["rejected"]}
        self.assertEqual(rejected.get("plasma"), REJECT_INCOMPATIBLE)
        self.assertEqual(rejected.get("ultraviolet-ozone"), REJECT_INCOMPATIBLE)

    def test_a_single_survivor_raises_the_no_fallback_finding(self):
        result = rank_cleaning_methods(
            base_request(
                contaminant="thin-organic-film",
                substrate="silver-coating",
                geometry="internal-passage",
                required_particulate_level_um=100.0,
                required_nvr_mg_per_01m2=0.50,
            )
        )
        self.assertEqual(len(result["ranked"]), 1)
        self.assertTrue(any("no fallback route" in f for f in result["findings"]))

    def test_an_impossible_job_recommends_nothing_and_says_why(self):
        result = rank_cleaning_methods(
            base_request(
                substrate="magnesium-alloy",
                geometry="internal-passage",
                required_particulate_level_um=25.0,
                required_nvr_mg_per_01m2=0.01,
            )
        )
        self.assertIsNone(result["recommended"])
        self.assertTrue(any("no catalogued route survives" in f for f in result["findings"]))

    def test_a_weak_leader_is_flagged_for_a_preceding_step(self):
        result = rank_cleaning_methods(
            base_request(
                contaminant="particulate",
                substrate="gold-coating",
                required_particulate_level_um=100.0,
                required_nvr_mg_per_01m2=0.01,
            )
        )
        self.assertEqual(result["recommended"], "plasma")
        self.assertTrue(any("only weakly" in f for f in result["findings"]))

    def test_the_request_travels_with_the_result(self):
        result = rank_cleaning_methods(base_request())
        self.assertEqual(result["request"]["contaminant"], "particulate")


if __name__ == "__main__":
    unittest.main()
