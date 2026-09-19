"""Contract tests for the clause 5.6.12.2 frequency band selection logic."""

import unittest

from e50_frequency_band_selection_logic import (
    ALLOCATED_PRIMARY,
    ALLOCATED_SECONDARY,
    NOT_ALLOCATED,
    PARTIALLY_OUTSIDE,
    allocation_occupancy,
    assess_band_choice,
    feasible_centre_range,
    normalize_allocation,
    normalize_request,
    occupied_band,
    rank_candidate_allocations,
    validate_bandwidth,
    validate_frequency,
    validate_region,
)

ALLOCATIONS = [
    {
        "service": "space-research-deep-space",
        "lower_hz": 8400000000.0,
        "upper_hz": 8450000000.0,
        "status": "primary",
        "regions": [1, 2, 3],
    },
    {
        "service": "space-research-deep-space",
        "lower_hz": 31800000000.0,
        "upper_hz": 32300000000.0,
        "status": "primary",
        "regions": [1, 2, 3],
    },
    {
        "service": "space-operation",
        "lower_hz": 2025000000.0,
        "upper_hz": 2110000000.0,
        "status": "secondary",
        "regions": [1],
    },
]

REQUEST = {
    "service": "space-research-deep-space",
    "centre_hz": 8425000000.0,
    "necessary_bandwidth_hz": 10000000.0,
    "region": 1,
}


class ValidationTests(unittest.TestCase):
    def test_positive_frequency_accepted(self):
        self.assertAlmostEqual(validate_frequency(2200000000), 2.2e9, places=9)

    def test_zero_frequency_rejected(self):
        with self.assertRaises(ValueError):
            validate_frequency(0)

    def test_boolean_bandwidth_rejected(self):
        with self.assertRaises(ValueError):
            validate_bandwidth(True)

    def test_non_finite_bandwidth_rejected(self):
        with self.assertRaises(ValueError):
            validate_bandwidth(float("inf"))

    def test_region_four_rejected(self):
        with self.assertRaises(ValueError):
            validate_region(4)

    def test_region_as_text_rejected(self):
        with self.assertRaises(ValueError):
            validate_region("1")


class NormalisationTests(unittest.TestCase):
    def test_allocation_width_is_derived(self):
        self.assertAlmostEqual(
            normalize_allocation(ALLOCATIONS[0])["width_hz"], 50000000.0, places=9
        )

    def test_inverted_allocation_rejected(self):
        bad = dict(ALLOCATIONS[0])
        bad["upper_hz"] = bad["lower_hz"]
        with self.assertRaises(ValueError):
            normalize_allocation(bad)

    def test_unknown_allocation_status_rejected(self):
        bad = dict(ALLOCATIONS[0])
        bad["status"] = "tertiary"
        with self.assertRaises(ValueError):
            normalize_allocation(bad)

    def test_empty_region_list_rejected(self):
        bad = dict(ALLOCATIONS[0])
        bad["regions"] = []
        with self.assertRaises(ValueError):
            normalize_allocation(bad)

    def test_request_region_defaults_to_one(self):
        request = dict(REQUEST)
        del request["region"]
        self.assertEqual(normalize_request(request)["region"], 1)

    def test_bandwidth_wider_than_twice_the_centre_rejected(self):
        bad = dict(REQUEST)
        bad["necessary_bandwidth_hz"] = 2.0 * bad["centre_hz"]
        with self.assertRaises(ValueError):
            normalize_request(bad)


class OccupiedBandTests(unittest.TestCase):
    def test_edges_straddle_the_centre(self):
        lower, upper = occupied_band(8425000000.0, 10000000.0)
        self.assertAlmostEqual(lower, 8420000000.0, places=6)
        self.assertAlmostEqual(upper, 8430000000.0, places=6)

    def test_occupancy_is_the_share_of_the_allocation(self):
        self.assertAlmostEqual(
            allocation_occupancy(ALLOCATIONS[0], 10000000.0), 0.2, places=9
        )

    def test_feasible_centre_range_is_inset_by_a_half_bandwidth(self):
        low, high = feasible_centre_range(ALLOCATIONS[0], 10000000.0)
        self.assertAlmostEqual(low, 8405000000.0, places=6)
        self.assertAlmostEqual(high, 8445000000.0, places=6)

    def test_bandwidth_filling_the_allocation_gives_a_single_centre(self):
        low, high = feasible_centre_range(ALLOCATIONS[0], 50000000.0)
        self.assertAlmostEqual(low, high, places=6)
        self.assertAlmostEqual(low, 8425000000.0, places=6)

    def test_bandwidth_wider_than_the_allocation_rejected(self):
        with self.assertRaises(ValueError):
            feasible_centre_range(ALLOCATIONS[0], 60000000.0)


class AssessBandChoiceTests(unittest.TestCase):
    def test_contained_primary_band_is_protected(self):
        result = assess_band_choice(REQUEST, ALLOCATIONS)
        self.assertEqual(result["verdict"], ALLOCATED_PRIMARY)
        self.assertTrue(result["usable"])
        self.assertTrue(result["protected"])

    def test_band_exactly_filling_the_allocation_is_contained(self):
        request = dict(REQUEST)
        request["necessary_bandwidth_hz"] = 50000000.0
        result = assess_band_choice(request, ALLOCATIONS)
        self.assertAlmostEqual(result["lower_edge_hz"], 8400000000.0, places=6)
        self.assertAlmostEqual(result["upper_edge_hz"], 8450000000.0, places=6)
        self.assertEqual(result["verdict"], ALLOCATED_PRIMARY)

    def test_occupancy_is_reported_against_the_matched_allocation(self):
        result = assess_band_choice(REQUEST, ALLOCATIONS)
        self.assertAlmostEqual(result["occupancy"], 0.2, places=9)

    def test_secondary_allocation_is_usable_but_unprotected(self):
        request = {
            "service": "space-operation",
            "centre_hz": 2050000000.0,
            "necessary_bandwidth_hz": 4000000.0,
            "region": 1,
        }
        result = assess_band_choice(request, ALLOCATIONS)
        self.assertEqual(result["verdict"], ALLOCATED_SECONDARY)
        self.assertTrue(result["usable"])
        self.assertFalse(result["protected"])

    def test_secondary_allocation_carries_an_interference_finding(self):
        request = {
            "service": "space-operation",
            "centre_hz": 2050000000.0,
            "necessary_bandwidth_hz": 4000000.0,
            "region": 1,
        }
        result = assess_band_choice(request, ALLOCATIONS)
        self.assertTrue(any("secondary" in f for f in result["findings"]))

    def test_band_spilling_past_the_edge_is_not_usable(self):
        request = dict(REQUEST)
        request["centre_hz"] = 8448000000.0
        result = assess_band_choice(request, ALLOCATIONS)
        self.assertEqual(result["verdict"], PARTIALLY_OUTSIDE)
        self.assertFalse(result["usable"])

    def test_spill_finding_quantifies_the_overshoot(self):
        request = dict(REQUEST)
        request["centre_hz"] = 8448000000.0
        result = assess_band_choice(request, ALLOCATIONS)
        self.assertTrue(any("spills" in f for f in result["findings"]))

    def test_band_with_no_allocation_for_the_service(self):
        request = dict(REQUEST)
        request["service"] = "amateur-satellite"
        result = assess_band_choice(request, ALLOCATIONS)
        self.assertEqual(result["verdict"], NOT_ALLOCATED)
        self.assertIsNone(result["allocation"])

    def test_wrong_region_makes_the_allocation_inapplicable(self):
        request = {
            "service": "space-operation",
            "centre_hz": 2050000000.0,
            "necessary_bandwidth_hz": 4000000.0,
            "region": 2,
        }
        result = assess_band_choice(request, ALLOCATIONS)
        self.assertEqual(result["verdict"], NOT_ALLOCATED)

    def test_primary_is_preferred_when_both_statuses_contain_the_band(self):
        allocations = ALLOCATIONS + [
            {
                "service": "space-research-deep-space",
                "lower_hz": 8300000000.0,
                "upper_hz": 8500000000.0,
                "status": "secondary",
                "regions": [1],
            }
        ]
        result = assess_band_choice(REQUEST, allocations)
        self.assertEqual(result["verdict"], ALLOCATED_PRIMARY)

    def test_empty_allocation_catalogue_rejected(self):
        with self.assertRaises(ValueError):
            assess_band_choice(REQUEST, [])

    def test_non_list_allocation_catalogue_rejected(self):
        with self.assertRaises(ValueError):
            assess_band_choice(REQUEST, ALLOCATIONS[0])


class RankCandidateTests(unittest.TestCase):
    def test_both_deep_space_allocations_are_offered(self):
        ranked = rank_candidate_allocations(REQUEST, ALLOCATIONS)
        self.assertEqual(len(ranked), 2)

    def test_the_roomiest_allocation_ranks_first(self):
        ranked = rank_candidate_allocations(REQUEST, ALLOCATIONS)
        self.assertAlmostEqual(ranked[0]["lower_hz"], 31800000000.0, places=6)
        self.assertAlmostEqual(ranked[0]["occupancy"], 0.02, places=9)

    def test_primary_outranks_secondary_even_when_narrower(self):
        allocations = [
            {
                "service": "space-research-deep-space",
                "lower_hz": 8400000000.0,
                "upper_hz": 8450000000.0,
                "status": "primary",
                "regions": [1],
            },
            {
                "service": "space-research-deep-space",
                "lower_hz": 25500000000.0,
                "upper_hz": 27000000000.0,
                "status": "secondary",
                "regions": [1],
            },
        ]
        ranked = rank_candidate_allocations(REQUEST, allocations)
        self.assertEqual(ranked[0]["status"], "primary")

    def test_an_allocation_narrower_than_the_link_is_not_offered(self):
        request = dict(REQUEST)
        request["necessary_bandwidth_hz"] = 400000000.0
        ranked = rank_candidate_allocations(request, ALLOCATIONS)
        self.assertEqual(len(ranked), 1)

    def test_each_candidate_carries_a_usable_centre_range(self):
        ranked = rank_candidate_allocations(REQUEST, ALLOCATIONS)
        low, high = ranked[0]["centre_range_hz"]
        request = dict(REQUEST)
        request["centre_hz"] = low
        self.assertTrue(assess_band_choice(request, ALLOCATIONS)["usable"])
        self.assertTrue(high >= low)


if __name__ == "__main__":
    unittest.main()
