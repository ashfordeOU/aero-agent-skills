"""Contract tests for the clause 5.6.12.1 space link media logic."""

import unittest

from e50_space_link_media_logic import (
    MEDIUM_MARGINAL,
    MEDIUM_SUITABLE,
    MEDIUM_UNSUITABLE,
    assess_link_medium,
    assess_media_plan,
    normalize_link,
    normalize_medium,
    rank_media_for_link,
    validate_fraction,
    validate_positive,
)

MEDIA = [
    {
        "name": "x-band-rf",
        "max_rate_bps": 200000000.0,
        "max_range_m": 4.0e11,
        "availability": 0.99,
    },
    {
        "name": "ka-band-rf",
        "max_rate_bps": 1000000000.0,
        "max_range_m": 6.0e10,
        "availability": 0.95,
    },
    {
        "name": "optical-downlink",
        "max_rate_bps": 10000000000.0,
        "max_range_m": 4.0e8,
        "availability": 0.70,
        "interoperable": False,
    },
]

LINKS = [
    {
        "name": "science-downlink",
        "medium": "x-band-rf",
        "required_rate_bps": 50000000.0,
        "required_range_m": 1.0e11,
        "required_availability": 0.98,
    },
    {
        "name": "housekeeping-downlink",
        "medium": "x-band-rf",
        "required_rate_bps": 100000.0,
        "required_range_m": 1.0e11,
        "required_availability": 0.98,
    },
]


class ValidationTests(unittest.TestCase):
    def test_positive_magnitude_accepted(self):
        self.assertAlmostEqual(validate_positive(2500), 2500.0, places=9)

    def test_zero_magnitude_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(0)

    def test_boolean_magnitude_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(True)

    def test_non_finite_magnitude_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(float("nan"))

    def test_fraction_at_one_accepted(self):
        self.assertAlmostEqual(validate_fraction(1.0), 1.0, places=9)

    def test_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_fraction(1.0001)


class NormalisationTests(unittest.TestCase):
    def test_medium_defaults_to_interoperable(self):
        self.assertTrue(normalize_medium(MEDIA[0])["interoperable"])

    def test_medium_without_availability_rejected(self):
        with self.assertRaises(ValueError):
            normalize_medium({"name": "s-band-rf", "max_rate_bps": 1.0, "max_range_m": 1.0})

    def test_medium_with_text_flag_rejected(self):
        bad = dict(MEDIA[0])
        bad["interoperable"] = "yes"
        with self.assertRaises(ValueError):
            normalize_medium(bad)

    def test_link_availability_defaults_to_zero(self):
        link = normalize_link(
            {
                "name": "beacon",
                "medium": "x-band-rf",
                "required_rate_bps": 100.0,
                "required_range_m": 1.0e9,
            }
        )
        self.assertAlmostEqual(link["required_availability"], 0.0, places=9)

    def test_link_without_a_medium_rejected(self):
        with self.assertRaises(ValueError):
            normalize_link(
                {"name": "beacon", "required_rate_bps": 1.0, "required_range_m": 1.0}
            )

    def test_link_with_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            normalize_link(
                {
                    "name": "   ",
                    "medium": "x-band-rf",
                    "required_rate_bps": 1.0,
                    "required_range_m": 1.0,
                }
            )


class AssessLinkMediumTests(unittest.TestCase):
    def test_rate_utilisation_is_reported(self):
        result = assess_link_medium(LINKS[0], MEDIA[0])
        self.assertAlmostEqual(result["rate_utilisation"], 0.25, places=9)

    def test_range_utilisation_is_reported(self):
        result = assess_link_medium(LINKS[0], MEDIA[0])
        self.assertAlmostEqual(result["range_utilisation"], 0.25, places=9)

    def test_comfortable_link_is_suitable(self):
        result = assess_link_medium(LINKS[0], MEDIA[0])
        self.assertEqual(result["verdict"], MEDIUM_SUITABLE)
        self.assertEqual(result["breaches"], [])

    def test_link_exactly_on_the_envelope_is_not_unsuitable(self):
        link = dict(LINKS[0])
        link["required_rate_bps"] = 200000000.0
        result = assess_link_medium(link, MEDIA[0])
        self.assertAlmostEqual(result["rate_utilisation"], 1.0, places=9)
        self.assertEqual(result["verdict"], MEDIUM_MARGINAL)

    def test_link_just_inside_the_envelope_is_marginal(self):
        link = dict(LINKS[0])
        link["required_rate_bps"] = 190000000.0
        result = assess_link_medium(link, MEDIA[0])
        self.assertEqual(result["verdict"], MEDIUM_MARGINAL)

    def test_rate_beyond_the_envelope_is_unsuitable(self):
        link = dict(LINKS[0])
        link["required_rate_bps"] = 300000000.0
        result = assess_link_medium(link, MEDIA[0])
        self.assertEqual(result["verdict"], MEDIUM_UNSUITABLE)
        self.assertTrue(any("rate" in item for item in result["breaches"]))

    def test_range_beyond_the_envelope_is_unsuitable(self):
        link = dict(LINKS[0])
        link["medium"] = "ka-band-rf"
        result = assess_link_medium(link, MEDIA[1])
        self.assertEqual(result["verdict"], MEDIUM_UNSUITABLE)
        self.assertTrue(any("range" in item for item in result["breaches"]))

    def test_availability_shortfall_makes_a_fast_medium_unsuitable(self):
        link = dict(LINKS[0])
        link["medium"] = "optical-downlink"
        link["required_range_m"] = 3.0e8
        result = assess_link_medium(link, MEDIA[2])
        self.assertEqual(result["verdict"], MEDIUM_UNSUITABLE)
        self.assertAlmostEqual(result["availability_shortfall"], 0.28, places=9)

    def test_availability_met_exactly_is_not_a_breach(self):
        link = dict(LINKS[0])
        link["required_availability"] = 0.99
        result = assess_link_medium(link, MEDIA[0])
        self.assertAlmostEqual(result["availability_shortfall"], 0.0, places=9)
        self.assertEqual(result["verdict"], MEDIUM_SUITABLE)

    def test_marginal_threshold_is_configurable(self):
        link = dict(LINKS[0])
        link["required_rate_bps"] = 50000000.0
        result = assess_link_medium(link, MEDIA[0], marginal_utilisation=0.2)
        self.assertEqual(result["verdict"], MEDIUM_MARGINAL)


class RankMediaTests(unittest.TestCase):
    def test_only_capable_media_are_offered(self):
        ranked = rank_media_for_link(LINKS[0], MEDIA)
        self.assertEqual([item["medium"] for item in ranked], ["x-band-rf"])

    def test_ranking_is_by_headroom(self):
        link = {
            "name": "short-range-dump",
            "medium": "x-band-rf",
            "required_rate_bps": 50000000.0,
            "required_range_m": 3.0e8,
            "required_availability": 0.60,
        }
        ranked = rank_media_for_link(link, MEDIA)
        self.assertEqual(len(ranked), 3)
        self.assertEqual(ranked[0]["medium"], "ka-band-rf")
        self.assertEqual(ranked[-1]["medium"], "optical-downlink")
        self.assertTrue(
            ranked[0]["worst_utilisation"] <= ranked[-1]["worst_utilisation"]
        )

    def test_no_capable_medium_returns_an_empty_list(self):
        link = {
            "name": "impossible",
            "medium": "x-band-rf",
            "required_rate_bps": 5.0e10,
            "required_range_m": 1.0e13,
        }
        self.assertEqual(rank_media_for_link(link, MEDIA), [])

    def test_duplicate_medium_name_rejected(self):
        with self.assertRaises(ValueError):
            rank_media_for_link(LINKS[0], MEDIA + [MEDIA[0]])


class MediaPlanTests(unittest.TestCase):
    def test_a_sound_plan_is_compliant(self):
        result = assess_media_plan(LINKS, MEDIA[:1])
        self.assertTrue(result["compliant"])
        self.assertEqual(result["unsuitable_links"], [])

    def test_undeclared_medium_is_caught(self):
        links = LINKS + [
            {
                "name": "experimental-dump",
                "medium": "terahertz-rf",
                "required_rate_bps": 1000.0,
                "required_range_m": 1.0e8,
            }
        ]
        result = assess_media_plan(links, MEDIA)
        self.assertEqual(result["undeclared_media_links"], ["experimental-dump"])
        self.assertFalse(result["compliant"])

    def test_non_interoperable_medium_is_caught(self):
        links = [
            {
                "name": "optical-dump",
                "medium": "optical-downlink",
                "required_rate_bps": 1000000.0,
                "required_range_m": 3.0e8,
                "required_availability": 0.50,
            }
        ]
        result = assess_media_plan(links, MEDIA)
        self.assertEqual(result["non_interoperable_links"], ["optical-dump"])
        self.assertFalse(result["compliant"])

    def test_unused_declared_medium_is_reported_without_failing(self):
        result = assess_media_plan(LINKS, MEDIA[:2])
        self.assertEqual(result["unused_media"], ["ka-band-rf"])
        self.assertTrue(result["compliant"])

    def test_duplicate_link_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_media_plan(LINKS + [LINKS[0]], MEDIA)

    def test_empty_link_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_media_plan([], MEDIA)

    def test_empty_media_catalogue_rejected(self):
        with self.assertRaises(ValueError):
            assess_media_plan(LINKS, [])

    def test_findings_name_every_failing_link(self):
        links = LINKS + [
            {
                "name": "overreach",
                "medium": "ka-band-rf",
                "required_rate_bps": 1000.0,
                "required_range_m": 1.0e11,
            }
        ]
        result = assess_media_plan(links, MEDIA)
        self.assertIn("overreach", result["unsuitable_links"])
        self.assertTrue(any("cannot carry" in f for f in result["findings"]))


if __name__ == "__main__":
    unittest.main()
