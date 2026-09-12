#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 6.3.2.3 protected
frequency band emissions.

Exercises scripts/e20_protected_frequency_band_emissions_logic.py
(stdlib unittest, offline). Contract: a registry band maps to exactly
one protected service and an unknown band raises; each service carries
its own limit; the emission set is the carrier, the harmonic series
with its suppression and widened bandwidth, and every complete
declared spurious product; spectral overlap and a uniform power
spectral density give the in-band power, with an emission wholly
inside a band contributing all of its power and no scaling arithmetic;
contributions sum per band; a total on the limit to within the named
tolerance is not a finding while a real exceedance is; an incomplete
spurious declaration is reported and kept out of the summation; a
sweep short of the minimum order is a finding; and the review is
compliant only when all three lists are empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_protected_frequency_band_emissions_logic as pf  # noqa: E402

# Suppression that puts the second harmonic of the VHF carrier below
# exactly on the distress-band limit of -90 dBm.
ON_LIMIT_SUPPRESSION_DB = 128.45098040014256


def _clean_transmitter():
    """An X-band downlink whose carrier and first five harmonics reach
    no protected band at all."""
    return {
        "transmitter_id": "TX-X-1",
        "fundamental_hz": 8.4e9,
        "fundamental_power_w": 10.0,
        "fundamental_bandwidth_hz": 1.0e7,
        "max_harmonic_order": 5,
    }


def _vhf_transmitter(second_harmonic_suppression_db=ON_LIMIT_SUPPRESSION_DB):
    """A VHF carrier whose second harmonic lands inside the distress
    and safety band, filtered to sit on the limit."""
    return {
        "transmitter_id": "TX-V-1",
        "fundamental_hz": 203.025e6,
        "fundamental_power_w": 7.0,
        "fundamental_bandwidth_hz": 1.0e4,
        "max_harmonic_order": 5,
        "harmonic_suppression_db": {
            2: second_harmonic_suppression_db,
            3: 120.0,
            4: 120.0,
            5: 120.0,
        },
    }


def _band(name):
    for band in pf.PROTECTED_BANDS:
        if band["name"] == name:
            return dict(band)
    raise AssertionError("fixture asked for an unknown band %r" % (name,))


class BandRegistryTest(unittest.TestCase):
    def test_hydrogen_line_band_is_radio_astronomy(self):
        self.assertEqual(
            pf.categorize_protected_band("radio_astronomy_1400_1427"),
            "radio_astronomy",
        )

    def test_twenty_three_gigahertz_band_is_passive_radiometry(self):
        self.assertEqual(
            pf.categorize_protected_band("passive_radiometry_23600_24000"),
            "passive_radiometry",
        )

    def test_beacon_band_is_distress_and_safety(self):
        self.assertEqual(
            pf.categorize_protected_band("distress_406_0_406_1"),
            "distress_and_safety",
        )

    def test_l1_band_is_navigation(self):
        self.assertEqual(
            pf.categorize_protected_band("gnss_l1_1559_1610"), "gnss_navigation"
        )

    def test_uplink_band_is_a_spacecraft_receive_band(self):
        self.assertEqual(
            pf.categorize_protected_band("spacecraft_receive_s_band_2025_2110"),
            "spacecraft_receive",
        )

    def test_unknown_band_raises(self):
        with self.assertRaises(ValueError):
            pf.categorize_protected_band("amateur_two_metre")

    def test_every_registry_band_has_a_limit(self):
        for band in pf.PROTECTED_BANDS:
            self.assertIn(
                pf.categorize_protected_band(band["name"]), pf.SERVICE_LIMIT_DBM
            )

    def test_every_registry_band_has_ordered_edges(self):
        for band in pf.PROTECTED_BANDS:
            self.assertLess(band["f_min_hz"], band["f_max_hz"])


class ServiceLimitTest(unittest.TestCase):
    def test_radio_astronomy_limit(self):
        self.assertAlmostEqual(pf.service_limit_dbm("radio_astronomy"), -80.0)

    def test_distress_band_is_the_tightest_limit(self):
        self.assertEqual(
            min(pf.SERVICE_LIMIT_DBM, key=pf.SERVICE_LIMIT_DBM.get),
            "distress_and_safety",
        )

    def test_spacecraft_receive_is_the_loosest_limit(self):
        self.assertEqual(
            max(pf.SERVICE_LIMIT_DBM, key=pf.SERVICE_LIMIT_DBM.get),
            "spacecraft_receive",
        )

    def test_unknown_service_raises(self):
        with self.assertRaises(ValueError):
            pf.service_limit_dbm("amateur_service")

    def test_limit_in_watts_round_trips_to_the_stated_limit(self):
        for service in pf.SERVICE_LIMIT_DBM:
            self.assertAlmostEqual(
                pf.watts_to_dbm(pf.service_limit_w(service)),
                pf.service_limit_dbm(service),
            )

    def test_limit_in_watts_raises_for_an_unknown_service(self):
        with self.assertRaises(ValueError):
            pf.service_limit_w("amateur_service")


class PowerConversionTest(unittest.TestCase):
    def test_one_milliwatt_is_zero_dbm(self):
        self.assertAlmostEqual(pf.watts_to_dbm(1.0e-3), 0.0)

    def test_one_watt_is_thirty_dbm(self):
        self.assertAlmostEqual(pf.watts_to_dbm(1.0), 30.0)

    def test_dbm_to_watts_inverts_watts_to_dbm(self):
        self.assertAlmostEqual(pf.dbm_to_watts(pf.watts_to_dbm(4.7e-9)), 4.7e-9)

    def test_a_large_negative_dbm_is_a_valid_power(self):
        self.assertAlmostEqual(pf.dbm_to_watts(-90.0), 1.0e-12)

    def test_zero_watts_has_no_decibel_representation(self):
        with self.assertRaises(ValueError):
            pf.watts_to_dbm(0.0)

    def test_negative_watts_raises(self):
        with self.assertRaises(ValueError):
            pf.watts_to_dbm(-1.0e-9)


class EmissionEdgesTest(unittest.TestCase):
    def test_edges_straddle_the_centre_frequency(self):
        lower, upper = pf.emission_edges(1.4e9, 2.0e6)
        self.assertAlmostEqual(lower, 1.399e9)
        self.assertAlmostEqual(upper, 1.401e9)

    def test_edge_separation_is_the_bandwidth(self):
        lower, upper = pf.emission_edges(2.2e9, 5.0e6)
        self.assertAlmostEqual(upper - lower, 5.0e6)

    def test_zero_centre_frequency_raises(self):
        with self.assertRaises(ValueError):
            pf.emission_edges(0.0, 1.0e6)

    def test_zero_bandwidth_raises(self):
        with self.assertRaises(ValueError):
            pf.emission_edges(1.4e9, 0.0)

    def test_negative_bandwidth_raises(self):
        with self.assertRaises(ValueError):
            pf.emission_edges(1.4e9, -1.0e6)

    def test_bandwidth_wider_than_the_carrier_raises(self):
        with self.assertRaises(ValueError):
            pf.emission_edges(1.0e6, 4.0e6)


class BandOverlapTest(unittest.TestCase):
    def setUp(self):
        self.band = _band("radio_astronomy_1400_1427")

    def test_emission_wholly_inside_overlaps_its_own_width(self):
        self.assertAlmostEqual(
            pf.band_overlap_hz(1.409e9, 1.411e9, self.band), 2.0e6
        )

    def test_emission_straddling_the_lower_edge(self):
        self.assertAlmostEqual(
            pf.band_overlap_hz(1.399e9, 1.401e9, self.band), 1.0e6
        )

    def test_emission_wider_than_the_band_overlaps_the_whole_band(self):
        self.assertAlmostEqual(
            pf.band_overlap_hz(1.0e9, 2.0e9, self.band), 2.7e7
        )

    def test_emission_clear_of_the_band_overlaps_nothing(self):
        self.assertAlmostEqual(
            pf.band_overlap_hz(1.30e9, 1.35e9, self.band), 0.0
        )

    def test_emission_touching_the_edge_overlaps_nothing(self):
        self.assertAlmostEqual(
            pf.band_overlap_hz(1.38e9, 1.400e9, self.band), 0.0
        )

    def test_inverted_emission_edges_raise(self):
        with self.assertRaises(ValueError):
            pf.band_overlap_hz(1.41e9, 1.40e9, self.band)

    def test_inverted_band_edges_raise(self):
        broken = dict(self.band)
        broken["f_min_hz"], broken["f_max_hz"] = (
            broken["f_max_hz"],
            broken["f_min_hz"],
        )
        with self.assertRaises(ValueError):
            pf.band_overlap_hz(1.40e9, 1.41e9, broken)


class InBandPowerTest(unittest.TestCase):
    def test_whole_emission_inside_contributes_all_its_power_exactly(self):
        self.assertAlmostEqual(
            pf.in_band_power_w(3.0e-12, 1.0e6, 1.0e6), 3.0e-12, delta=0.0
        )

    def test_half_the_bandwidth_inside_contributes_half_the_power(self):
        self.assertAlmostEqual(pf.in_band_power_w(1.0e-9, 2.0e6, 1.0e6), 5.0e-10)

    def test_a_tenth_of_the_bandwidth_contributes_a_tenth(self):
        self.assertAlmostEqual(pf.in_band_power_w(1.0e-6, 1.0e7, 1.0e6), 1.0e-7)

    def test_no_overlap_contributes_nothing(self):
        self.assertAlmostEqual(pf.in_band_power_w(1.0e-6, 1.0e6, 0.0), 0.0)

    def test_zero_power_contributes_nothing(self):
        self.assertAlmostEqual(pf.in_band_power_w(0.0, 1.0e6, 1.0e6), 0.0)

    def test_negative_power_raises(self):
        with self.assertRaises(ValueError):
            pf.in_band_power_w(-1.0e-9, 1.0e6, 1.0e5)

    def test_zero_bandwidth_raises(self):
        with self.assertRaises(ValueError):
            pf.in_band_power_w(1.0e-9, 0.0, 0.0)

    def test_negative_overlap_raises(self):
        with self.assertRaises(ValueError):
            pf.in_band_power_w(1.0e-9, 1.0e6, -1.0)

    def test_overlap_wider_than_the_emission_raises(self):
        with self.assertRaises(ValueError):
            pf.in_band_power_w(1.0e-9, 1.0e6, 2.0e6)


class HarmonicSeriesTest(unittest.TestCase):
    def test_series_starts_at_the_second_order(self):
        series = pf.harmonic_frequencies_hz(1.0e9, 5)
        self.assertEqual([order for order, _ in series], [2, 3, 4, 5])

    def test_each_harmonic_is_a_multiple_of_the_carrier(self):
        for order, frequency in pf.harmonic_frequencies_hz(2.0e8, 4):
            self.assertAlmostEqual(frequency, order * 2.0e8)

    def test_first_order_sweep_raises(self):
        with self.assertRaises(ValueError):
            pf.harmonic_frequencies_hz(1.0e9, 1)

    def test_zero_carrier_raises(self):
        with self.assertRaises(ValueError):
            pf.harmonic_frequencies_hz(0.0, 5)

    def test_default_suppression_grows_with_order(self):
        self.assertLess(
            pf.harmonic_suppression_db(2), pf.harmonic_suppression_db(4)
        )

    def test_default_suppression_at_the_second_order(self):
        self.assertAlmostEqual(
            pf.harmonic_suppression_db(2),
            pf.HARMONIC_BASE_SUPPRESSION_DB + 20.0 * math.log10(2.0),
        )

    def test_a_declared_suppression_wins(self):
        self.assertAlmostEqual(pf.harmonic_suppression_db(3, 95.0), 95.0)

    def test_negative_declared_suppression_raises(self):
        with self.assertRaises(ValueError):
            pf.harmonic_suppression_db(3, -1.0)

    def test_suppression_below_the_second_order_raises(self):
        with self.assertRaises(ValueError):
            pf.harmonic_suppression_db(1)

    def test_ten_decibels_of_suppression_is_a_tenth_of_the_power(self):
        self.assertAlmostEqual(pf.harmonic_power_w(10.0, 10.0), 1.0)

    def test_no_suppression_leaves_the_carrier_power(self):
        self.assertAlmostEqual(pf.harmonic_power_w(10.0, 0.0), 10.0)

    def test_negative_carrier_power_raises(self):
        with self.assertRaises(ValueError):
            pf.harmonic_power_w(-1.0, 40.0)

    def test_negative_suppression_raises(self):
        with self.assertRaises(ValueError):
            pf.harmonic_power_w(10.0, -1.0)


class DeclarationTest(unittest.TestCase):
    def test_complete_emission_has_nothing_missing(self):
        emission = {
            "emission_id": "spur_a",
            "center_hz": 1.41e9,
            "bandwidth_hz": 1.0e6,
            "power_w": 1.0e-12,
        }
        self.assertEqual(pf.missing_emission_fields(emission), [])

    def test_absent_field_is_reported(self):
        emission = {
            "emission_id": "spur_a",
            "center_hz": 1.41e9,
            "bandwidth_hz": 1.0e6,
        }
        self.assertEqual(pf.missing_emission_fields(emission), ["power_w"])

    def test_field_left_as_none_counts_as_absent(self):
        emission = {
            "emission_id": "spur_a",
            "center_hz": 1.41e9,
            "bandwidth_hz": 1.0e6,
            "power_w": None,
        }
        self.assertEqual(pf.missing_emission_fields(emission), ["power_w"])

    def test_empty_emission_reports_every_field(self):
        self.assertEqual(
            pf.missing_emission_fields({}), sorted(pf.REQUIRED_EMISSION_FIELDS)
        )

    def test_declaration_findings_name_the_missing_field(self):
        transmitter = _clean_transmitter()
        transmitter["spurious_emissions"] = [
            {"emission_id": "spur_a", "center_hz": 1.41e9, "bandwidth_hz": 1.0e6}
        ]
        findings = pf.declaration_findings(transmitter)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "incomplete_spurious_emission_declaration"
        )
        self.assertEqual(findings[0]["field"], "power_w")

    def test_a_complete_declaration_produces_no_finding(self):
        transmitter = _clean_transmitter()
        transmitter["spurious_emissions"] = [
            {
                "emission_id": "spur_a",
                "center_hz": 1.41e9,
                "bandwidth_hz": 1.0e6,
                "power_w": 1.0e-13,
            }
        ]
        self.assertEqual(pf.declaration_findings(transmitter), [])


class ContributionsAndTotalsTest(unittest.TestCase):
    def test_emission_clear_of_every_band_contributes_nothing(self):
        emission = {
            "emission_id": "carrier",
            "center_hz": 8.4e9,
            "bandwidth_hz": 1.0e7,
            "power_w": 10.0,
        }
        self.assertEqual(pf.emission_contributions(emission), [])

    def test_emission_can_reach_two_bands_at_once(self):
        emission = {
            "emission_id": "wide_spur",
            "center_hz": 1.610e9,
            "bandwidth_hz": 1.0e7,
            "power_w": 1.0e-6,
        }
        names = [name for name, _ in pf.emission_contributions(emission)]
        self.assertEqual(
            sorted(names), ["gnss_l1_1559_1610", "radio_astronomy_1610_1614"]
        )

    def test_contribution_scales_with_the_overlapping_fraction(self):
        emission = {
            "emission_id": "edge_spur",
            "center_hz": 1.400e9,
            "bandwidth_hz": 2.0e6,
            "power_w": 1.0e-9,
        }
        contributions = pf.emission_contributions(emission)
        self.assertEqual(len(contributions), 1)
        self.assertAlmostEqual(contributions[0][1], 5.0e-10)

    def test_totals_sum_contributions_from_several_emissions(self):
        emissions = [
            {
                "emission_id": "spur_a",
                "center_hz": 1.410e9,
                "bandwidth_hz": 1.0e6,
                "power_w": 3.0e-12,
            },
            {
                "emission_id": "spur_b",
                "center_hz": 1.415e9,
                "bandwidth_hz": 1.0e6,
                "power_w": 7.0e-12,
            },
        ]
        totals = pf.band_totals_w(emissions)
        self.assertEqual(list(totals), ["radio_astronomy_1400_1427"])
        self.assertAlmostEqual(totals["radio_astronomy_1400_1427"], 1.0e-11)

    def test_unreached_bands_are_absent_from_the_totals(self):
        self.assertEqual(pf.band_totals_w([]), {})

    def test_carrier_and_harmonics_are_all_in_the_emission_set(self):
        emissions = pf.transmitter_emissions(_clean_transmitter())
        self.assertEqual(
            [e["emission_id"] for e in emissions],
            [
                "fundamental",
                "harmonic_2",
                "harmonic_3",
                "harmonic_4",
                "harmonic_5",
            ],
        )

    def test_harmonic_bandwidth_scales_with_its_order(self):
        emissions = pf.transmitter_emissions(_clean_transmitter())
        self.assertAlmostEqual(emissions[1]["bandwidth_hz"], 2.0e7)
        self.assertAlmostEqual(emissions[4]["bandwidth_hz"], 5.0e7)

    def test_incomplete_spurious_product_is_kept_out_of_the_emission_set(self):
        transmitter = _clean_transmitter()
        transmitter["spurious_emissions"] = [
            {"emission_id": "spur_a", "center_hz": 1.41e9, "bandwidth_hz": 1.0e6}
        ]
        ids = [e["emission_id"] for e in pf.transmitter_emissions(transmitter)]
        self.assertNotIn("spur_a", ids)


class BandLimitFindingsTest(unittest.TestCase):
    def test_empty_totals_produce_no_finding(self):
        self.assertEqual(pf.band_limit_findings("TX-1", {}), [])

    def test_a_band_under_its_limit_produces_no_finding(self):
        totals = {"radio_astronomy_1400_1427": 1.0e-13}
        self.assertEqual(pf.band_limit_findings("TX-1", totals), [])

    def test_a_band_over_its_limit_is_reported(self):
        totals = {"radio_astronomy_1400_1427": 1.0e-9}
        findings = pf.band_limit_findings("TX-1", totals)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "protected_band_emission_above_limit"
        )
        self.assertEqual(findings[0]["service"], "radio_astronomy")
        self.assertAlmostEqual(findings[0]["limit_dbm"], -80.0)
        self.assertAlmostEqual(findings[0]["total_dbm"], -60.0)

    def test_findings_are_sorted_by_band_name(self):
        totals = {
            "gnss_l1_1559_1610": 1.0e-9,
            "distress_406_0_406_1": 1.0e-9,
        }
        names = [f["band"] for f in pf.band_limit_findings("TX-1", totals)]
        self.assertEqual(names, sorted(names))

    def test_a_band_with_no_power_is_skipped(self):
        self.assertEqual(
            pf.band_limit_findings("TX-1", {"radio_astronomy_1400_1427": 0.0}), []
        )

    def test_a_negative_total_raises(self):
        with self.assertRaises(ValueError):
            pf.band_limit_findings("TX-1", {"radio_astronomy_1400_1427": -1.0e-12})

    def test_an_unknown_band_raises(self):
        with self.assertRaises(ValueError):
            pf.band_limit_findings("TX-1", {"amateur_two_metre": 1.0e-12})

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            pf.band_limit_findings(
                "TX-1", {"radio_astronomy_1400_1427": 1.0e-12}, tolerance_db=-1.0
            )


class HarmonicCoverageTest(unittest.TestCase):
    def test_a_deep_enough_sweep_produces_no_finding(self):
        self.assertEqual(pf.harmonic_coverage_findings(_clean_transmitter()), [])

    def test_a_shallow_sweep_is_reported(self):
        transmitter = _clean_transmitter()
        transmitter["max_harmonic_order"] = 3
        findings = pf.harmonic_coverage_findings(transmitter)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "harmonic_sweep_below_minimum_order"
        )
        self.assertEqual(findings[0]["minimum_order"], pf.MIN_HARMONIC_ORDER)

    def test_a_custom_minimum_order_is_honoured(self):
        transmitter = _clean_transmitter()
        self.assertEqual(
            len(pf.harmonic_coverage_findings(transmitter, minimum_order=9)), 1
        )

    def test_a_minimum_order_below_two_raises(self):
        with self.assertRaises(ValueError):
            pf.harmonic_coverage_findings(_clean_transmitter(), minimum_order=1)


class TransmitterReviewTest(unittest.TestCase):
    def test_a_transmitter_reaching_no_band_is_compliant(self):
        review = pf.transmitter_emission_review(_clean_transmitter())
        self.assertTrue(pf.is_transmitter_compliant(review))
        self.assertEqual(review["declaration"], [])
        self.assertEqual(review["band_limit"], [])
        self.assertEqual(review["harmonic_coverage"], [])

    def test_a_harmonic_exactly_on_the_limit_is_compliant(self):
        # The filtered second harmonic sits on the -90 dBm distress
        # limit, but the suppression ratio puts the computed total a
        # few units in the last place over it.
        transmitter = _vhf_transmitter()
        totals = pf.band_totals_w(pf.transmitter_emissions(transmitter))
        raw_dbm = pf.watts_to_dbm(totals["distress_406_0_406_1"])
        self.assertGreater(raw_dbm, -90.0)
        review = pf.transmitter_emission_review(transmitter)
        self.assertEqual(review["band_limit"], [])
        self.assertTrue(pf.is_transmitter_compliant(review))

    def test_three_decibels_less_filtering_is_a_real_exceedance(self):
        transmitter = _vhf_transmitter(ON_LIMIT_SUPPRESSION_DB - 3.0)
        review = pf.transmitter_emission_review(transmitter)
        self.assertEqual(len(review["band_limit"]), 1)
        self.assertEqual(review["band_limit"][0]["band"], "distress_406_0_406_1")
        self.assertAlmostEqual(review["band_limit"][0]["total_dbm"], -87.0)
        self.assertFalse(pf.is_transmitter_compliant(review))

    def test_a_shallow_sweep_breaks_coverage_only(self):
        transmitter = _clean_transmitter()
        transmitter["max_harmonic_order"] = 2
        review = pf.transmitter_emission_review(transmitter)
        self.assertEqual(len(review["harmonic_coverage"]), 1)
        self.assertEqual(review["band_limit"], [])
        self.assertFalse(pf.is_transmitter_compliant(review))

    def test_an_incomplete_spurious_product_breaks_the_declaration(self):
        transmitter = _clean_transmitter()
        transmitter["spurious_emissions"] = [
            {"emission_id": "spur_a", "center_hz": 1.41e9, "bandwidth_hz": 1.0e6}
        ]
        review = pf.transmitter_emission_review(transmitter)
        self.assertEqual(len(review["declaration"]), 1)
        self.assertEqual(review["band_limit"], [])
        self.assertFalse(pf.is_transmitter_compliant(review))

    def test_two_small_products_can_sum_over_a_limit(self):
        transmitter = _clean_transmitter()
        transmitter["spurious_emissions"] = [
            {
                "emission_id": "spur_a",
                "center_hz": 1.410e9,
                "bandwidth_hz": 1.0e6,
                "power_w": 6.0e-12,
            },
            {
                "emission_id": "spur_b",
                "center_hz": 1.415e9,
                "bandwidth_hz": 1.0e6,
                "power_w": 6.0e-12,
            },
        ]
        alone = pf.band_limit_findings(
            "TX-X-1", {"radio_astronomy_1400_1427": 6.0e-12}
        )
        review = pf.transmitter_emission_review(transmitter)
        self.assertEqual(alone, [])
        self.assertEqual(len(review["band_limit"]), 1)

    def test_a_first_order_sweep_raises(self):
        transmitter = _clean_transmitter()
        transmitter["max_harmonic_order"] = 1
        with self.assertRaises(ValueError):
            pf.transmitter_emission_review(transmitter)

    def test_a_custom_band_registry_is_used(self):
        transmitter = _clean_transmitter()
        transmitter["bands"] = (
            {
                "name": "mission_receive_8400",
                "f_min_hz": 8.39e9,
                "f_max_hz": 8.41e9,
                "service": "spacecraft_receive",
            },
        )
        review = pf.transmitter_emission_review(transmitter)
        self.assertEqual(len(review["band_limit"]), 1)
        self.assertEqual(review["band_limit"][0]["band"], "mission_receive_8400")

    def test_review_does_not_mutate_input(self):
        transmitter = _vhf_transmitter()
        snapshot = {
            "harmonic_suppression_db": dict(transmitter["harmonic_suppression_db"]),
            "max_harmonic_order": transmitter["max_harmonic_order"],
        }
        pf.transmitter_emission_review(transmitter)
        self.assertEqual(
            transmitter["harmonic_suppression_db"],
            snapshot["harmonic_suppression_db"],
        )
        self.assertEqual(
            transmitter["max_harmonic_order"], snapshot["max_harmonic_order"]
        )

    def test_a_loosened_tolerance_never_hides_a_real_exceedance(self):
        transmitter = _vhf_transmitter(ON_LIMIT_SUPPRESSION_DB - 3.0)
        transmitter["tolerance_db"] = 1.0e-6
        review = pf.transmitter_emission_review(transmitter)
        self.assertEqual(len(review["band_limit"]), 1)


if __name__ == "__main__":
    unittest.main()
