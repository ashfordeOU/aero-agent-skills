"""Contract tests for the clause 6.4.3.13.2 subgroup measurement logic."""

import math
import unittest

from e2008_coverglass_conductivity_measurement_process_logic import (
    CONCENTRIC_RING,
    DEFAULT_MEASUREMENT_POLICY,
    FOUR_POINT_COLLINEAR,
    MEASUREMENT_INVALID,
    POPULATION_INCOMPLETE,
    SUBGROUP_CONDUCTIVITY_MEASURED,
    SUBGROUP_NOT_ESTABLISHED,
    article_mean_conductivity_s_per_square,
    article_site_conductivities,
    assess_coverglass_conductivity_measurement,
    environment_within_band,
    probe_current_within_band,
    sheet_resistance_concentric_ring,
    sheet_resistance_four_point,
    site_sheet_resistance,
    site_surface_conductivity,
    subgroup_population,
    surface_conductivity_s_per_square,
    validate_measurement_policy,
)

SUBGROUP = "qualification-subgroup-c"


def _policy(**overrides):
    policy = dict(DEFAULT_MEASUREMENT_POLICY)
    policy.update(overrides)
    return policy


def _sites(count, voltage_v=0.5, current_a=1.0e-9):
    return [
        {"id": "s%d" % index, "voltage_v": voltage_v, "current_a": current_a}
        for index in range(1, count + 1)
    ]


def _article(identifier, subgroup=SUBGROUP, sites=None, voltage_v=0.5, **extra):
    article = {
        "id": identifier,
        "subgroup": subgroup,
        "method": FOUR_POINT_COLLINEAR,
        "sites": _sites(5, voltage_v=voltage_v) if sites is None else sites,
    }
    article.update(extra)
    return article


def _case(**overrides):
    case = {
        "designated_subgroup": SUBGROUP,
        "environment": {"relative_humidity_percent": 35.0, "temperature_c": 22.0},
        "articles": [
            _article("cg-01", voltage_v=0.5),
            _article("cg-02", voltage_v=0.4),
            _article("cg-03", voltage_v=0.6),
        ],
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_measurement_policy(DEFAULT_MEASUREMENT_POLICY),
            DEFAULT_MEASUREMENT_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_measurement_policy("subgroup")

    def test_inverted_probe_current_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_measurement_policy(
                _policy(min_probe_current_a=1.0e-6, max_probe_current_a=1.0e-12)
            )

    def test_inverted_humidity_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_measurement_policy(
                _policy(
                    min_relative_humidity_percent=60.0,
                    max_relative_humidity_percent=20.0,
                )
            )

    def test_zero_minimum_article_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_measurement_policy(_policy(min_subgroup_articles=0))


class MethodTests(unittest.TestCase):
    def test_four_point_uses_the_collinear_geometry_factor(self):
        expected = (math.pi / math.log(2.0)) * 0.5 / 1.0e-9
        self.assertAlmostEqual(
            _ratio(sheet_resistance_four_point(0.5, 1.0e-9), expected),
            1.0,
            places=12,
        )

    def test_ring_uses_the_log_radius_ratio(self):
        expected = 2.0 * math.pi * (0.5 / 1.0e-9) / math.log(2.0)
        self.assertAlmostEqual(
            _ratio(
                sheet_resistance_concentric_ring(0.5, 1.0e-9, 0.005, 0.010),
                expected,
            ),
            1.0,
            places=12,
        )

    def test_a_two_to_one_ring_is_twice_the_four_point_factor(self):
        ring = sheet_resistance_concentric_ring(0.5, 1.0e-9, 0.005, 0.010)
        four_point = sheet_resistance_four_point(0.5, 1.0e-9)
        self.assertAlmostEqual(_ratio(ring, 2.0 * four_point), 1.0, places=12)

    def test_ring_radii_in_the_wrong_order_rejected(self):
        with self.assertRaises(ValueError):
            sheet_resistance_concentric_ring(0.5, 1.0e-9, 0.010, 0.005)

    def test_zero_drive_current_rejected(self):
        with self.assertRaises(ValueError):
            sheet_resistance_four_point(0.5, 0.0)

    def test_boolean_voltage_rejected(self):
        with self.assertRaises(ValueError):
            sheet_resistance_four_point(True, 1.0e-9)

    def test_conductivity_is_the_reciprocal_sheet_resistance(self):
        self.assertAlmostEqual(
            _ratio(surface_conductivity_s_per_square(2.0e9), 5.0e-10),
            1.0,
            places=12,
        )

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            site_sheet_resistance("two-point-clip", {"voltage_v": 0.5})

    def test_the_ring_method_dispatches_on_the_method_name(self):
        reading = {
            "voltage_v": 0.5,
            "current_a": 1.0e-9,
            "inner_radius_m": 0.005,
            "outer_radius_m": 0.010,
        }
        self.assertAlmostEqual(
            _ratio(
                site_sheet_resistance(CONCENTRIC_RING, reading),
                sheet_resistance_concentric_ring(0.5, 1.0e-9, 0.005, 0.010),
            ),
            1.0,
            places=12,
        )

    def test_a_higher_drive_voltage_reads_a_lower_conductivity(self):
        low = site_surface_conductivity(
            FOUR_POINT_COLLINEAR, {"voltage_v": 1.0, "current_a": 1.0e-9}
        )
        high = site_surface_conductivity(
            FOUR_POINT_COLLINEAR, {"voltage_v": 0.5, "current_a": 1.0e-9}
        )
        self.assertLess(low, high)

    def test_non_mapping_reading_rejected(self):
        with self.assertRaises(ValueError):
            site_sheet_resistance(FOUR_POINT_COLLINEAR, [0.5, 1.0e-9])


class ConditionTests(unittest.TestCase):
    def test_a_current_inside_the_band_is_acceptable(self):
        self.assertTrue(probe_current_within_band(1.0e-9, _policy()))

    def test_a_current_exactly_at_the_ceiling_is_acceptable(self):
        policy = _policy()
        self.assertTrue(
            probe_current_within_band(policy["max_probe_current_a"], policy)
        )

    def test_a_current_above_the_ceiling_is_not_acceptable(self):
        self.assertFalse(probe_current_within_band(1.0e-3, _policy()))

    def test_a_representative_ambient_raises_no_finding(self):
        ok, findings = environment_within_band(
            {"relative_humidity_percent": 35.0, "temperature_c": 22.0}, _policy()
        )
        self.assertTrue(ok)
        self.assertEqual(findings, ())

    def test_a_humid_ambient_is_reported(self):
        ok, findings = environment_within_band(
            {"relative_humidity_percent": 80.0, "temperature_c": 22.0}, _policy()
        )
        self.assertFalse(ok)
        self.assertEqual(len(findings), 1)

    def test_both_ambient_excursions_are_reported(self):
        ok, findings = environment_within_band(
            {"relative_humidity_percent": 80.0, "temperature_c": 40.0}, _policy()
        )
        self.assertFalse(ok)
        self.assertEqual(len(findings), 2)

    def test_missing_humidity_rejected(self):
        with self.assertRaises(ValueError):
            environment_within_band({"temperature_c": 22.0}, _policy())


class PopulationTests(unittest.TestCase):
    def test_only_the_designated_subgroup_is_measured(self):
        members, others = subgroup_population(
            [_article("cg-01"), _article("cg-09", subgroup="acceptance-subgroup-a")],
            SUBGROUP,
        )
        self.assertEqual([a["id"] for a in members], ["cg-01"])
        self.assertEqual([a["id"] for a in others], ["cg-09"])

    def test_an_article_with_no_subgroup_record_rejected(self):
        article = _article("cg-01")
        del article["subgroup"]
        with self.assertRaises(ValueError):
            subgroup_population([article], SUBGROUP)

    def test_duplicate_article_id_rejected(self):
        with self.assertRaises(ValueError):
            subgroup_population([_article("cg-01"), _article("cg-01")], SUBGROUP)

    def test_non_sequence_inventory_rejected(self):
        with self.assertRaises(ValueError):
            subgroup_population({"id": "cg-01"}, SUBGROUP)

    def test_every_site_of_an_article_is_converted(self):
        values = article_site_conductivities(_article("cg-01"))
        self.assertEqual(len(values), 5)

    def test_duplicate_site_id_rejected(self):
        article = _article("cg-01")
        article["sites"][1]["id"] = article["sites"][0]["id"]
        with self.assertRaises(ValueError):
            article_site_conductivities(article)

    def test_an_article_with_no_sites_rejected(self):
        with self.assertRaises(ValueError):
            article_site_conductivities(_article("cg-01", sites=[]))

    def test_the_article_mean_matches_its_uniform_sites(self):
        expected = 1.0 / sheet_resistance_four_point(0.5, 1.0e-9)
        self.assertAlmostEqual(
            _ratio(article_mean_conductivity_s_per_square(_article("cg-01")), expected),
            1.0,
            places=12,
        )


class MeasurementAssessmentTests(unittest.TestCase):
    def test_a_complete_valid_run_measures_the_subgroup(self):
        result = assess_coverglass_conductivity_measurement(_case())
        self.assertEqual(result["verdict"], SUBGROUP_CONDUCTIVITY_MEASURED)
        self.assertEqual(result["findings"], [])

    def test_the_measured_articles_are_named(self):
        result = assess_coverglass_conductivity_measurement(_case())
        self.assertEqual(result["measured_articles"], ("cg-01", "cg-02", "cg-03"))

    def test_the_subgroup_average_weights_each_article_once(self):
        result = assess_coverglass_conductivity_measurement(_case())
        means = result["article_means_s_per_square"]
        expected = sum(means.values()) / 3.0
        self.assertAlmostEqual(
            _ratio(result["subgroup_average_s_per_square"], expected),
            1.0,
            places=12,
        )

    def test_an_oversampled_article_does_not_carry_the_average(self):
        case = _case()
        case["articles"][0]["sites"] = _sites(40, voltage_v=0.5)
        result = assess_coverglass_conductivity_measurement(case)
        plain = assess_coverglass_conductivity_measurement(_case())
        self.assertAlmostEqual(
            _ratio(
                result["subgroup_average_s_per_square"],
                plain["subgroup_average_s_per_square"],
            ),
            1.0,
            places=12,
        )

    def test_a_blank_designation_leaves_the_subgroup_unestablished(self):
        result = assess_coverglass_conductivity_measurement(
            _case(designated_subgroup="   ")
        )
        self.assertEqual(result["verdict"], SUBGROUP_NOT_ESTABLISHED)

    def test_an_inventory_holding_no_member_leaves_it_unestablished(self):
        result = assess_coverglass_conductivity_measurement(
            _case(designated_subgroup="qualification-subgroup-z")
        )
        self.assertEqual(result["verdict"], SUBGROUP_NOT_ESTABLISHED)

    def test_non_members_are_named_and_not_measured(self):
        case = _case()
        case["articles"].append(_article("cg-77", subgroup="acceptance-subgroup-a"))
        result = assess_coverglass_conductivity_measurement(case)
        self.assertEqual(result["excluded_articles"], ("cg-77",))
        self.assertNotIn("cg-77", result["measured_articles"])

    def test_too_few_member_articles_is_an_incomplete_population(self):
        case = _case()
        case["articles"] = case["articles"][:2]
        result = assess_coverglass_conductivity_measurement(case)
        self.assertEqual(result["verdict"], POPULATION_INCOMPLETE)

    def test_an_article_short_of_sites_is_an_incomplete_population(self):
        case = _case()
        case["articles"][1]["sites"] = _sites(2)
        result = assess_coverglass_conductivity_measurement(case)
        self.assertEqual(result["verdict"], POPULATION_INCOMPLETE)
        self.assertEqual(len(result["findings"]), 1)

    def test_a_site_count_exactly_at_the_minimum_is_complete(self):
        policy = _policy(min_sites_per_article=5)
        result = assess_coverglass_conductivity_measurement(_case(), policy)
        self.assertEqual(result["verdict"], SUBGROUP_CONDUCTIVITY_MEASURED)
        self.assertEqual(result["site_count"], 15)

    def test_an_overdriven_site_invalidates_the_run(self):
        case = _case()
        case["articles"][2]["sites"][0]["current_a"] = 1.0e-3
        result = assess_coverglass_conductivity_measurement(case)
        self.assertEqual(result["verdict"], MEASUREMENT_INVALID)
        self.assertFalse(result["probe_currents_within_band"])

    def test_a_humid_ambient_invalidates_the_run(self):
        result = assess_coverglass_conductivity_measurement(
            _case(
                environment={
                    "relative_humidity_percent": 85.0,
                    "temperature_c": 22.0,
                }
            )
        )
        self.assertEqual(result["verdict"], MEASUREMENT_INVALID)
        self.assertFalse(result["environment_representative"])

    def test_the_average_is_still_reported_when_the_run_is_invalid(self):
        result = assess_coverglass_conductivity_measurement(
            _case(
                environment={
                    "relative_humidity_percent": 85.0,
                    "temperature_c": 22.0,
                }
            )
        )
        self.assertIsNotNone(result["subgroup_average_s_per_square"])

    def test_both_invalidating_conditions_are_reported(self):
        case = _case(
            environment={"relative_humidity_percent": 85.0, "temperature_c": 22.0}
        )
        case["articles"][0]["sites"][0]["current_a"] = 1.0e-3
        result = assess_coverglass_conductivity_measurement(case)
        self.assertEqual(len(result["findings"]), 2)

    def test_absent_designation_key_rejected(self):
        case = _case()
        del case["designated_subgroup"]
        with self.assertRaises(ValueError):
            assess_coverglass_conductivity_measurement(case)

    def test_missing_environment_block_rejected(self):
        case = _case()
        del case["environment"]
        with self.assertRaises(ValueError):
            assess_coverglass_conductivity_measurement(case)

    def test_missing_article_inventory_rejected(self):
        case = _case()
        del case["articles"]
        with self.assertRaises(ValueError):
            assess_coverglass_conductivity_measurement(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_conductivity_measurement(["designated_subgroup"])


if __name__ == "__main__":
    unittest.main()
