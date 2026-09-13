"""Contract tests for the clause 6.4.3.13.3 coverglass conductivity criterion."""

import unittest

from e2008_coverglass_conductivity_criteria_logic import (
    AVERAGE_BELOW_DRAWING_VALUE,
    AVERAGE_MEETS_DRAWING_VALUE,
    DEFAULT_ACCEPTANCE_POLICY,
    PER_ARTICLE,
    PER_SITE,
    REQUIREMENT_NOT_ESTABLISHED,
    article_mean_conductivity_s_per_square,
    article_means,
    article_site_values,
    assess_coverglass_conductivity_criteria,
    average_surface_conductivity_s_per_square,
    dead_site_advisories,
    margin_fraction,
    meets_drawing_value,
    validate_acceptance_policy,
    validate_drawing_requirement,
)

REQUIRED = 1.0e-9


def _policy(**overrides):
    policy = dict(DEFAULT_ACCEPTANCE_POLICY)
    policy.update(overrides)
    return policy


def _articles():
    return [
        {"id": "cg-01", "site_conductivities_s_per_square": [1.2e-9, 1.2e-9, 1.2e-9]},
        {"id": "cg-02", "site_conductivities_s_per_square": [1.1e-9, 1.1e-9]},
        {"id": "cg-03", "site_conductivities_s_per_square": [1.3e-9]},
    ]


def _case(**overrides):
    case = {
        "drawing_requirement": {
            "drawing_reference": "CAD-4711 issue C",
            "required_surface_conductivity_s_per_square": REQUIRED,
        },
        "articles": _articles(),
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_acceptance_policy(DEFAULT_ACCEPTANCE_POLICY),
            DEFAULT_ACCEPTANCE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceptance_policy("per-article")

    def test_site_floor_above_the_drawing_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceptance_policy(_policy(site_floor_fraction=1.5))

    def test_zero_site_floor_fraction_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceptance_policy(_policy(site_floor_fraction=0.0))

    def test_unknown_weighting_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceptance_policy(_policy(weighting="per-panel"))


class RequirementTests(unittest.TestCase):
    def test_a_referenced_requirement_validates(self):
        reference, value = validate_drawing_requirement(
            {
                "drawing_reference": "CAD-4711 issue C",
                "required_surface_conductivity_s_per_square": REQUIRED,
            }
        )
        self.assertEqual(reference, "CAD-4711 issue C")
        self.assertAlmostEqual(_ratio(value, REQUIRED), 1.0, places=12)

    def test_a_non_mapping_requirement_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing_requirement("CAD-4711")

    def test_a_negative_required_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing_requirement(
                {
                    "drawing_reference": "CAD-4711 issue C",
                    "required_surface_conductivity_s_per_square": -1.0e-9,
                }
            )

    def test_a_non_string_drawing_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing_requirement(
                {
                    "drawing_reference": 4711,
                    "required_surface_conductivity_s_per_square": REQUIRED,
                }
            )


class AverageTests(unittest.TestCase):
    def test_site_values_are_returned_with_the_article_id(self):
        identifier, values = article_site_values(_articles()[0])
        self.assertEqual(identifier, "cg-01")
        self.assertEqual(len(values), 3)

    def test_an_article_with_no_site_rejected(self):
        with self.assertRaises(ValueError):
            article_site_values(
                {"id": "cg-04", "site_conductivities_s_per_square": []}
            )

    def test_a_negative_site_conductivity_rejected(self):
        with self.assertRaises(ValueError):
            article_site_values(
                {"id": "cg-04", "site_conductivities_s_per_square": [-1.0e-9]}
            )

    def test_the_article_mean_is_the_mean_of_its_sites(self):
        self.assertAlmostEqual(
            _ratio(
                article_mean_conductivity_s_per_square(_articles()[1]), 1.1e-9
            ),
            1.0,
            places=12,
        )

    def test_duplicate_article_id_rejected(self):
        articles = _articles()
        articles[1]["id"] = "cg-01"
        with self.assertRaises(ValueError):
            article_means(articles)

    def test_an_empty_article_record_rejected(self):
        with self.assertRaises(ValueError):
            article_means([])

    def test_the_per_article_average_weights_each_coverglass_once(self):
        self.assertAlmostEqual(
            _ratio(
                average_surface_conductivity_s_per_square(_articles(), PER_ARTICLE),
                1.2e-9,
            ),
            1.0,
            places=12,
        )

    def test_the_per_site_average_differs_from_the_per_article_one(self):
        per_site = average_surface_conductivity_s_per_square(_articles(), PER_SITE)
        per_article = average_surface_conductivity_s_per_square(
            _articles(), PER_ARTICLE
        )
        self.assertAlmostEqual(_ratio(per_site, 7.1e-9 / 6.0), 1.0, places=12)
        self.assertLess(per_site, per_article)

    def test_an_unknown_weighting_rejected_by_the_average(self):
        with self.assertRaises(ValueError):
            average_surface_conductivity_s_per_square(_articles(), "per-panel")


class ComparisonTests(unittest.TestCase):
    def test_margin_is_the_fractional_excess_over_the_drawing_value(self):
        self.assertAlmostEqual(margin_fraction(1.2e-9, REQUIRED), 0.2, places=9)

    def test_a_short_average_gives_a_negative_margin(self):
        self.assertAlmostEqual(margin_fraction(8.0e-10, REQUIRED), -0.2, places=9)

    def test_an_average_above_the_drawing_value_meets_it(self):
        self.assertTrue(meets_drawing_value(1.2e-9, REQUIRED))

    def test_an_average_exactly_at_the_drawing_value_meets_it(self):
        self.assertAlmostEqual(_ratio(REQUIRED, REQUIRED), 1.0, places=12)
        self.assertTrue(meets_drawing_value(REQUIRED, REQUIRED))

    def test_an_average_below_the_drawing_value_does_not_meet_it(self):
        self.assertFalse(meets_drawing_value(8.0e-10, REQUIRED))

    def test_a_zero_average_rejected(self):
        with self.assertRaises(ValueError):
            meets_drawing_value(0.0, REQUIRED)


class AdvisoryTests(unittest.TestCase):
    def test_a_healthy_record_raises_no_advisory(self):
        self.assertEqual(dead_site_advisories(_articles(), REQUIRED, _policy()), ())

    def test_a_dead_site_is_named(self):
        articles = _articles()
        articles[0]["site_conductivities_s_per_square"][1] = 5.0e-12
        advisories = dead_site_advisories(articles, REQUIRED, _policy())
        self.assertEqual(len(advisories), 1)
        self.assertIn("cg-01", advisories[0])

    def test_a_site_exactly_at_the_floor_is_not_dead(self):
        articles = _articles()
        articles[0]["site_conductivities_s_per_square"][1] = REQUIRED * 0.1
        self.assertEqual(dead_site_advisories(articles, REQUIRED, _policy()), ())

    def test_every_dead_site_is_named_not_only_the_first(self):
        articles = _articles()
        articles[0]["site_conductivities_s_per_square"][0] = 5.0e-12
        articles[1]["site_conductivities_s_per_square"][0] = 4.0e-12
        advisories = dead_site_advisories(articles, REQUIRED, _policy())
        self.assertEqual(len(advisories), 2)


class CriteriaAssessmentTests(unittest.TestCase):
    def test_an_average_above_the_drawing_value_is_admissible(self):
        result = assess_coverglass_conductivity_criteria(_case())
        self.assertEqual(result["verdict"], AVERAGE_MEETS_DRAWING_VALUE)
        self.assertEqual(result["findings"], [])

    def test_the_average_and_margin_are_reported(self):
        result = assess_coverglass_conductivity_criteria(_case())
        self.assertAlmostEqual(
            _ratio(result["average_surface_conductivity_s_per_square"], 1.2e-9),
            1.0,
            places=12,
        )
        self.assertAlmostEqual(result["margin_fraction"], 0.2, places=9)

    def test_the_drawing_reference_travels_with_the_verdict(self):
        result = assess_coverglass_conductivity_criteria(_case())
        self.assertEqual(result["drawing_reference"], "CAD-4711 issue C")

    def test_a_short_average_fails_against_the_drawing_value(self):
        case = _case()
        case["drawing_requirement"][
            "required_surface_conductivity_s_per_square"
        ] = 2.0e-9
        result = assess_coverglass_conductivity_criteria(case)
        self.assertEqual(result["verdict"], AVERAGE_BELOW_DRAWING_VALUE)
        self.assertEqual(len(result["findings"]), 1)

    def test_an_average_exactly_at_the_drawing_value_is_admissible(self):
        case = _case()
        case["drawing_requirement"][
            "required_surface_conductivity_s_per_square"
        ] = 1.2e-9
        result = assess_coverglass_conductivity_criteria(case)
        self.assertAlmostEqual(
            _ratio(
                result["average_surface_conductivity_s_per_square"],
                case["drawing_requirement"][
                    "required_surface_conductivity_s_per_square"
                ],
            ),
            1.0,
            places=12,
        )
        self.assertEqual(result["verdict"], AVERAGE_MEETS_DRAWING_VALUE)

    def test_no_drawing_requirement_leaves_the_criterion_unestablished(self):
        case = _case()
        del case["drawing_requirement"]
        result = assess_coverglass_conductivity_criteria(case)
        self.assertEqual(result["verdict"], REQUIREMENT_NOT_ESTABLISHED)
        self.assertIsNone(result["average_surface_conductivity_s_per_square"])

    def test_a_blank_drawing_reference_leaves_it_unestablished(self):
        case = _case()
        case["drawing_requirement"]["drawing_reference"] = "   "
        result = assess_coverglass_conductivity_criteria(case)
        self.assertEqual(result["verdict"], REQUIREMENT_NOT_ESTABLISHED)

    def test_a_dead_site_is_advised_without_moving_a_passing_verdict(self):
        case = _case()
        case["articles"][0]["site_conductivities_s_per_square"][1] = 5.0e-12
        result = assess_coverglass_conductivity_criteria(case)
        self.assertEqual(result["verdict"], AVERAGE_MEETS_DRAWING_VALUE)
        self.assertEqual(len(result["advisories"]), 1)

    def test_the_worst_and_best_sites_are_reported(self):
        result = assess_coverglass_conductivity_criteria(_case())
        self.assertAlmostEqual(
            _ratio(result["worst_site_s_per_square"], 1.1e-9), 1.0, places=12
        )
        self.assertAlmostEqual(
            _ratio(result["best_site_s_per_square"], 1.3e-9), 1.0, places=12
        )

    def test_the_site_spread_ratio_is_reported(self):
        result = assess_coverglass_conductivity_criteria(_case())
        self.assertAlmostEqual(
            _ratio(result["site_spread_ratio"], 1.3 / 1.1), 1.0, places=12
        )

    def test_the_per_site_weighting_changes_the_average(self):
        result = assess_coverglass_conductivity_criteria(
            _case(), _policy(weighting=PER_SITE)
        )
        self.assertAlmostEqual(
            _ratio(
                result["average_surface_conductivity_s_per_square"], 7.1e-9 / 6.0
            ),
            1.0,
            places=12,
        )

    def test_the_per_article_means_are_reported(self):
        result = assess_coverglass_conductivity_criteria(_case())
        self.assertEqual(
            sorted(result["article_means_s_per_square"]),
            ["cg-01", "cg-02", "cg-03"],
        )

    def test_missing_article_record_rejected(self):
        case = _case()
        del case["articles"]
        with self.assertRaises(ValueError):
            assess_coverglass_conductivity_criteria(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_conductivity_criteria(["drawing_requirement"])

    def test_an_empty_measured_population_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_conductivity_criteria(_case(articles=[]))


if __name__ == "__main__":
    unittest.main()
