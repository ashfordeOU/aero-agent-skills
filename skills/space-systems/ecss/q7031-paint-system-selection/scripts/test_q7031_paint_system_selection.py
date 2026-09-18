"""Contract tests for the ECSS-Q-ST-70-31C paint-system selection logic."""

import unittest

from q7031_paint_system_selection_logic import (
    PRIMER_TOPCOAT_COMPATIBILITY,
    SUBSTRATE_PRIMER_COMPATIBILITY,
    THERMAL_ROLES,
    absorptance_emittance_ratio,
    end_of_life_absorptance,
    environment_findings,
    normalize_key,
    primer_accepts_substrate,
    score_candidate,
    select_paint_system,
    thermal_role_targets,
    topcoat_accepts_primer,
)

ENVIRONMENT = {
    "equivalent_sun_hours": 4000.0,
    "atomic_oxygen_fluence": 1.0e20,
    "thermal_cycle_range_k": 160.0,
}


def candidate(**overrides):
    base = {
        "name": "white-silicate",
        "primer": "epoxy-polyamide",
        "topcoat": "inorganic-silicate",
        "alpha_bol": 0.14,
        "epsilon": 0.88,
        "uv_degradation_per_1000_esh": 0.005,
        "atomic_oxygen_rating": 1.0e21,
        "ultraviolet_rating_esh": 8000.0,
        "thermal_cycle_rating_k": 200.0,
    }
    base.update(overrides)
    return base


def requirement(**overrides):
    base = {
        "substrate": "aluminium-alloy",
        "thermal_role": "radiator-cold-surface",
        "environment": dict(ENVIRONMENT),
    }
    base.update(overrides)
    return base


class CompatibilityTests(unittest.TestCase):
    def test_primer_bonds_to_listed_substrate(self):
        self.assertTrue(primer_accepts_substrate("epoxy-polyamide", "aluminium-alloy"))

    def test_primer_rejected_on_wrong_substrate(self):
        self.assertFalse(primer_accepts_substrate("silicate", "magnesium-alloy"))

    def test_unknown_substrate_rejected(self):
        with self.assertRaises(ValueError):
            primer_accepts_substrate("epoxy-polyamide", "beryllium-billet")

    def test_topcoat_qualified_over_primer(self):
        self.assertTrue(topcoat_accepts_primer("polyurethane", "epoxy-polyamine"))

    def test_topcoat_not_qualified_over_primer(self):
        self.assertFalse(topcoat_accepts_primer("inorganic-silicate", "epoxy-polyamine"))

    def test_unknown_primer_rejected(self):
        with self.assertRaises(ValueError):
            topcoat_accepts_primer("polyurethane", "resin-of-unknown-origin")

    def test_compatibility_tables_are_populated(self):
        self.assertIn("cfrp-laminate", SUBSTRATE_PRIMER_COMPATIBILITY)
        self.assertIn("silicate", PRIMER_TOPCOAT_COMPATIBILITY)

    def test_key_normalisation_folds_case(self):
        self.assertEqual(normalize_key(" Epoxy-Polyamide ", "primer"), "epoxy-polyamide")


class OpticalTests(unittest.TestCase):
    def test_no_degradation_leaves_absorptance_alone(self):
        self.assertAlmostEqual(end_of_life_absorptance(0.2, 0.0, 9000.0), 0.2, places=9)

    def test_degradation_scales_with_dose(self):
        got = end_of_life_absorptance(0.20, 0.01, 4000.0)
        self.assertAlmostEqual(got, 0.24, places=9)

    def test_degraded_absorptance_saturates_at_unity(self):
        self.assertAlmostEqual(end_of_life_absorptance(0.9, 0.5, 9000.0), 1.0, places=9)

    def test_absorptance_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            end_of_life_absorptance(1.4, 0.0, 0.0)

    def test_negative_dose_rejected(self):
        with self.assertRaises(ValueError):
            end_of_life_absorptance(0.2, 0.01, -5.0)

    def test_ratio_is_absorptance_over_emittance(self):
        self.assertAlmostEqual(absorptance_emittance_ratio(0.22, 0.88), 0.25, places=9)

    def test_zero_emittance_rejected(self):
        with self.assertRaises(ValueError):
            absorptance_emittance_ratio(0.22, 0.0)

    def test_emittance_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            absorptance_emittance_ratio(0.22, 1.4)


class EnvironmentTests(unittest.TestCase):
    def test_rated_candidate_has_no_findings(self):
        self.assertEqual(environment_findings(candidate(), ENVIRONMENT), [])

    def test_atomic_oxygen_over_rating_reported(self):
        got = environment_findings(candidate(atomic_oxygen_rating=1.0e19), ENVIRONMENT)
        self.assertIn("atomic-oxygen-fluence-over-rating", got)

    def test_ultraviolet_over_rating_reported(self):
        got = environment_findings(candidate(ultraviolet_rating_esh=1000.0), ENVIRONMENT)
        self.assertIn("ultraviolet-dose-over-rating", got)

    def test_thermal_cycle_over_rating_reported(self):
        got = environment_findings(candidate(thermal_cycle_rating_k=100.0), ENVIRONMENT)
        self.assertIn("thermal-cycle-range-over-rating", got)

    def test_demand_exactly_at_rating_is_not_a_finding(self):
        got = environment_findings(
            candidate(thermal_cycle_rating_k=ENVIRONMENT["thermal_cycle_range_k"]),
            ENVIRONMENT,
        )
        self.assertNotIn("thermal-cycle-range-over-rating", got)

    def test_absent_rating_is_not_graded(self):
        spec = candidate()
        del spec["atomic_oxygen_rating"]
        self.assertNotIn(
            "atomic-oxygen-fluence-over-rating", environment_findings(spec, ENVIRONMENT)
        )


class ThermalRoleTests(unittest.TestCase):
    def test_role_targets_returned(self):
        alpha, ratio = thermal_role_targets("radiator-cold-surface")
        self.assertAlmostEqual(alpha, THERMAL_ROLES["radiator-cold-surface"][0])
        self.assertAlmostEqual(ratio, THERMAL_ROLES["radiator-cold-surface"][1])

    def test_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            thermal_role_targets("mystery-surface")

    def test_every_role_has_two_targets(self):
        for targets in THERMAL_ROLES.values():
            self.assertEqual(len(targets), 2)


class ScoringTests(unittest.TestCase):
    def test_candidate_scored_on_end_of_life_values(self):
        rec = score_candidate(candidate(), requirement())
        self.assertAlmostEqual(rec["alpha_eol"], 0.16, places=9)
        self.assertFalse(rec["rejected"])

    def test_incompatible_primer_is_rejected_with_a_reason(self):
        rec = score_candidate(
            candidate(primer="silicate", topcoat="silicone"),
            requirement(substrate="magnesium-alloy"),
        )
        self.assertTrue(rec["rejected"])
        self.assertIn("primer-not-compatible-with-substrate", rec["reasons"])

    def test_unqualified_topcoat_is_rejected_with_a_reason(self):
        rec = score_candidate(
            candidate(primer="epoxy-polyamine", topcoat="inorganic-silicate"),
            requirement(),
        )
        self.assertIn("topcoat-not-qualified-over-primer", rec["reasons"])

    def test_missing_candidate_key_rejected(self):
        spec = candidate()
        del spec["epsilon"]
        with self.assertRaises(ValueError):
            score_candidate(spec, requirement())

    def test_missing_requirement_key_rejected(self):
        req = requirement()
        del req["thermal_role"]
        with self.assertRaises(ValueError):
            score_candidate(candidate(), req)


class SelectionTests(unittest.TestCase):
    def test_closest_to_the_role_is_selected(self):
        black = candidate(name="black-polyurethane", topcoat="polyurethane",
                          alpha_bol=0.95, epsilon=0.90)
        out = select_paint_system([black, candidate()], requirement())
        self.assertEqual(out["selected"], "white-silicate")

    def test_black_wins_for_an_absorber_role(self):
        black = candidate(name="black-polyurethane", topcoat="polyurethane",
                          alpha_bol=0.92, epsilon=0.88, uv_degradation_per_1000_esh=0.0)
        out = select_paint_system(
            [candidate(), black], requirement(thermal_role="solar-absorber-warm-surface")
        )
        self.assertEqual(out["selected"], "black-polyurethane")

    def test_rejected_candidates_never_rank(self):
        bad = candidate(name="unrated-white", ultraviolet_rating_esh=100.0)
        out = select_paint_system([bad, candidate()], requirement())
        self.assertEqual([r["name"] for r in out["ranked"]], ["white-silicate"])
        self.assertEqual(out["rejected"][0]["name"], "unrated-white")

    def test_all_rejected_selects_nothing(self):
        bad = candidate(name="unrated-white", ultraviolet_rating_esh=100.0)
        out = select_paint_system([bad], requirement())
        self.assertIsNone(out["selected"])

    def test_exact_tie_broken_on_the_name(self):
        twin = candidate(name="alpha-twin")
        other = candidate(name="zulu-twin")
        out = select_paint_system([other, twin], requirement())
        self.assertEqual(out["selected"], "alpha-twin")

    def test_duplicate_candidate_names_rejected(self):
        with self.assertRaises(ValueError):
            select_paint_system([candidate(), candidate()], requirement())

    def test_empty_candidate_list_rejected(self):
        with self.assertRaises(ValueError):
            select_paint_system([], requirement())


if __name__ == "__main__":
    unittest.main()
