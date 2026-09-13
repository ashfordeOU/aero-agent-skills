#!/usr/bin/env python3
"""Gate 3 contract test for e2007-antenna-port-spurious-emissions.

Offline, deterministic, standard library only. Run:
    python3 test_e2007_antenna_port_spurious_emissions.py
"""

import unittest

from e2007_antenna_port_spurious_emissions_logic import (
    DEFAULT_REQUIRED_MARGIN_DB,
    assess_antenna_port_spurious_emissions,
    compatibility_margin_db,
    coupled_level_dbm,
    evaluate_antenna_pair,
    harmonic_frequencies,
    mask_coverage_gaps,
    mask_limit_dbm,
    normalize_emission_mask,
    required_isolation_db,
    worst_limit_in_band_dbm,
)

MHZ = 1.0e6


def seg(low_mhz, high_mhz, limit):
    return {
        "f_low_hz": low_mhz * MHZ,
        "f_high_hz": high_mhz * MHZ,
        "limit_dbm": limit,
    }


class TestNormalizeEmissionMask(unittest.TestCase):
    def test_sorts_segments_by_lower_edge(self):
        mask = normalize_emission_mask(
            [seg(2200, 2400, -70.0), seg(1500, 1600, -60.0)]
        )
        self.assertEqual(len(mask), 2)
        self.assertAlmostEqual(mask[0]["f_low_hz"], 1500 * MHZ)
        self.assertAlmostEqual(mask[1]["f_low_hz"], 2200 * MHZ)

    def test_abutting_segments_are_accepted(self):
        mask = normalize_emission_mask(
            [seg(1000, 1500, -60.0), seg(1500, 2000, -75.0)]
        )
        self.assertEqual(len(mask), 2)
        self.assertAlmostEqual(mask[1]["limit_dbm"], -75.0)

    def test_empty_mask_raises(self):
        with self.assertRaises(ValueError):
            normalize_emission_mask([])

    def test_none_mask_raises(self):
        with self.assertRaises(ValueError):
            normalize_emission_mask(None)

    def test_missing_field_raises(self):
        with self.assertRaises(ValueError):
            normalize_emission_mask([{"f_low_hz": 1.0e9, "f_high_hz": 2.0e9}])

    def test_non_mapping_segment_raises(self):
        with self.assertRaises(ValueError):
            normalize_emission_mask([(1.0e9, 2.0e9, -60.0)])

    def test_non_positive_lower_edge_raises(self):
        with self.assertRaises(ValueError):
            normalize_emission_mask([seg(0.0, 1500, -60.0)])

    def test_inverted_segment_raises(self):
        with self.assertRaises(ValueError):
            normalize_emission_mask([seg(2000, 1000, -60.0)])

    def test_overlapping_segments_raise(self):
        with self.assertRaises(ValueError):
            normalize_emission_mask(
                [seg(1000, 1600, -60.0), seg(1500, 2000, -75.0)]
            )

    def test_non_numeric_limit_raises(self):
        with self.assertRaises(ValueError):
            normalize_emission_mask(
                [{"f_low_hz": 1.0e9, "f_high_hz": 2.0e9, "limit_dbm": "low"}]
            )


class TestMaskLimit(unittest.TestCase):
    def setUp(self):
        self.mask = normalize_emission_mask(
            [seg(1000, 1500, -60.0), seg(2000, 2500, -80.0)]
        )

    def test_limit_inside_segment(self):
        self.assertAlmostEqual(mask_limit_dbm(self.mask, 1200 * MHZ), -60.0)

    def test_limit_in_second_segment(self):
        self.assertAlmostEqual(mask_limit_dbm(self.mask, 2400 * MHZ), -80.0)

    def test_uncovered_frequency_returns_none(self):
        self.assertIsNone(mask_limit_dbm(self.mask, 1750 * MHZ))

    def test_segment_edges_are_inclusive(self):
        self.assertAlmostEqual(mask_limit_dbm(self.mask, 1000 * MHZ), -60.0)
        self.assertAlmostEqual(mask_limit_dbm(self.mask, 1500 * MHZ), -60.0)

    def test_non_positive_frequency_raises(self):
        with self.assertRaises(ValueError):
            mask_limit_dbm(self.mask, 0.0)

    def test_non_numeric_frequency_raises(self):
        with self.assertRaises(ValueError):
            mask_limit_dbm(self.mask, "1 GHz")


class TestCoverageGaps(unittest.TestCase):
    def test_fully_covered_band_has_no_gap(self):
        mask = normalize_emission_mask(
            [seg(800, 1900, -60.0), seg(1900, 2100, -70.0)]
        )
        self.assertEqual(mask_coverage_gaps(mask, 1000 * MHZ, 2000 * MHZ), [])

    def test_interior_gap_is_reported(self):
        mask = normalize_emission_mask(
            [seg(500, 1200, -60.0), seg(1800, 2500, -70.0)]
        )
        gaps = mask_coverage_gaps(mask, 1000 * MHZ, 2000 * MHZ)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0][0], 1200 * MHZ)
        self.assertAlmostEqual(gaps[0][1], 1800 * MHZ)

    def test_gap_at_upper_end_is_reported(self):
        mask = normalize_emission_mask([seg(1000, 1500, -60.0)])
        gaps = mask_coverage_gaps(mask, 1000 * MHZ, 2000 * MHZ)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0][0], 1500 * MHZ)
        self.assertAlmostEqual(gaps[0][1], 2000 * MHZ)

    def test_mask_entirely_outside_band_leaves_whole_band_undeclared(self):
        mask = normalize_emission_mask([seg(3000, 4000, -60.0)])
        gaps = mask_coverage_gaps(mask, 1000 * MHZ, 2000 * MHZ)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0][0], 1000 * MHZ)
        self.assertAlmostEqual(gaps[0][1], 2000 * MHZ)

    def test_inverted_band_raises(self):
        mask = normalize_emission_mask([seg(1000, 1500, -60.0)])
        with self.assertRaises(ValueError):
            mask_coverage_gaps(mask, 2000 * MHZ, 1000 * MHZ)

    def test_non_positive_band_raises(self):
        mask = normalize_emission_mask([seg(1000, 1500, -60.0)])
        with self.assertRaises(ValueError):
            mask_coverage_gaps(mask, 0.0, 1000 * MHZ)


class TestWorstLimitInBand(unittest.TestCase):
    def test_takes_the_highest_overlapping_limit(self):
        mask = normalize_emission_mask(
            [seg(500, 1500, -60.0), seg(1500, 2500, -85.0)]
        )
        worst = worst_limit_in_band_dbm(mask, 1000 * MHZ, 2000 * MHZ)
        self.assertAlmostEqual(worst, -60.0)

    def test_band_inside_one_segment(self):
        mask = normalize_emission_mask([seg(500, 2500, -72.5)])
        self.assertAlmostEqual(
            worst_limit_in_band_dbm(mask, 1000 * MHZ, 2000 * MHZ), -72.5
        )

    def test_no_overlapping_segment_raises(self):
        mask = normalize_emission_mask([seg(3000, 4000, -60.0)])
        with self.assertRaises(ValueError):
            worst_limit_in_band_dbm(mask, 1000 * MHZ, 2000 * MHZ)

    def test_inverted_band_raises(self):
        mask = normalize_emission_mask([seg(500, 2500, -72.5)])
        with self.assertRaises(ValueError):
            worst_limit_in_band_dbm(mask, 2000 * MHZ, 1000 * MHZ)


class TestHarmonics(unittest.TestCase):
    def test_orders_and_frequencies(self):
        harmonics = harmonic_frequencies(1000 * MHZ, 4)
        self.assertEqual([h[0] for h in harmonics], [2, 3, 4])
        self.assertAlmostEqual(harmonics[0][1], 2000 * MHZ)
        self.assertAlmostEqual(harmonics[2][1], 4000 * MHZ)

    def test_order_below_two_raises(self):
        with self.assertRaises(ValueError):
            harmonic_frequencies(1000 * MHZ, 1)

    def test_non_integer_order_raises(self):
        with self.assertRaises(ValueError):
            harmonic_frequencies(1000 * MHZ, 3.5)

    def test_non_positive_carrier_raises(self):
        with self.assertRaises(ValueError):
            harmonic_frequencies(0.0, 3)


class TestCouplingArithmetic(unittest.TestCase):
    def test_coupled_level_subtracts_isolation(self):
        self.assertAlmostEqual(coupled_level_dbm(-60.0, 45.0), -105.0)

    def test_negative_isolation_raises(self):
        with self.assertRaises(ValueError):
            coupled_level_dbm(-60.0, -1.0)

    def test_zero_isolation_is_allowed(self):
        self.assertAlmostEqual(coupled_level_dbm(-60.0, 0.0), -60.0)

    def test_margin_is_threshold_less_coupled_level(self):
        self.assertAlmostEqual(compatibility_margin_db(-105.0, -99.0), 6.0)

    def test_required_isolation_arithmetic(self):
        self.assertAlmostEqual(required_isolation_db(-60.0, -110.0, 6.0), 56.0)

    def test_required_isolation_rejects_negative_margin(self):
        with self.assertRaises(ValueError):
            required_isolation_db(-60.0, -110.0, -1.0)


class TestEvaluateAntennaPair(unittest.TestCase):
    def setUp(self):
        self.emitter = {
            "port_id": "TX-S-BAND",
            "carrier_hz": 2200 * MHZ,
            "mask": normalize_emission_mask(
                [seg(1000, 1800, -65.0), seg(1800, 2600, -80.0)]
            ),
        }
        self.victim = {
            "port_id": "RX-GNSS",
            "band_low_hz": 1560 * MHZ,
            "band_high_hz": 1590 * MHZ,
            "susceptibility_dbm": -110.0,
        }

    def test_compliant_pair(self):
        result = evaluate_antenna_pair(self.emitter, self.victim, 60.0, 6.0)
        self.assertEqual(result["status"], "compliant")
        self.assertAlmostEqual(result["limit_dbm"], -65.0)
        self.assertAlmostEqual(result["coupled_dbm"], -125.0)
        self.assertAlmostEqual(result["margin_db"], 15.0)
        self.assertIsNone(result["finding"])
        self.assertAlmostEqual(result["isolation_shortfall_db"], 0.0)

    def test_exceeded_pair_reports_required_isolation(self):
        result = evaluate_antenna_pair(self.emitter, self.victim, 30.0, 6.0)
        self.assertEqual(result["status"], "exceeded")
        self.assertAlmostEqual(result["margin_db"], -15.0)
        self.assertAlmostEqual(result["required_isolation_db"], 51.0)
        self.assertAlmostEqual(result["isolation_shortfall_db"], 21.0)
        self.assertIsNotNone(result["finding"])

    def test_uncovered_passband_is_undeclared_not_compliant(self):
        emitter = dict(self.emitter)
        emitter["mask"] = normalize_emission_mask([seg(2000, 2600, -80.0)])
        result = evaluate_antenna_pair(emitter, self.victim, 90.0, 6.0)
        self.assertEqual(result["status"], "undeclared")
        self.assertIsNone(result["margin_db"])
        self.assertEqual(len(result["coverage_gaps_hz"]), 1)

    def test_exact_required_margin_is_compliant_despite_float_error(self):
        emitter = dict(self.emitter)
        emitter["mask"] = normalize_emission_mask([seg(1500, 1600, -55.3)])
        victim = dict(self.victim)
        victim["susceptibility_dbm"] = -99.7
        result = evaluate_antenna_pair(emitter, victim, 50.4, 6.0)
        self.assertEqual(result["status"], "compliant")
        self.assertAlmostEqual(result["margin_db"], 6.0, places=9)

    def test_one_decibel_below_requirement_fails(self):
        emitter = dict(self.emitter)
        emitter["mask"] = normalize_emission_mask([seg(1500, 1600, -55.3)])
        victim = dict(self.victim)
        victim["susceptibility_dbm"] = -99.7
        result = evaluate_antenna_pair(emitter, victim, 49.4, 6.0)
        self.assertEqual(result["status"], "exceeded")

    def test_negative_required_margin_raises(self):
        with self.assertRaises(ValueError):
            evaluate_antenna_pair(self.emitter, self.victim, 60.0, -3.0)

    def test_negative_isolation_raises(self):
        with self.assertRaises(ValueError):
            evaluate_antenna_pair(self.emitter, self.victim, -5.0, 6.0)

    def test_missing_victim_field_raises(self):
        victim = dict(self.victim)
        del victim["susceptibility_dbm"]
        with self.assertRaises(ValueError):
            evaluate_antenna_pair(self.emitter, victim, 60.0, 6.0)

    def test_missing_emitter_field_raises(self):
        emitter = dict(self.emitter)
        del emitter["carrier_hz"]
        with self.assertRaises(ValueError):
            evaluate_antenna_pair(emitter, self.victim, 60.0, 6.0)

    def test_inverted_victim_band_raises(self):
        victim = dict(self.victim)
        victim["band_high_hz"] = 1000 * MHZ
        with self.assertRaises(ValueError):
            evaluate_antenna_pair(self.emitter, victim, 60.0, 6.0)


class TestAssessment(unittest.TestCase):
    def setUp(self):
        self.emitters = [
            {
                "port_id": "TX-X-BAND",
                "carrier_hz": 8000 * MHZ,
                "mask_segments": [seg(1000, 2600, -80.0), seg(2600, 9000, -75.0)],
            }
        ]
        self.victims = [
            {
                "port_id": "RX-GNSS",
                "band_low_hz": 1560 * MHZ,
                "band_high_hz": 1590 * MHZ,
                "susceptibility_dbm": -110.0,
            },
            {
                "port_id": "RX-TTC",
                "band_low_hz": 2025 * MHZ,
                "band_high_hz": 2110 * MHZ,
                "susceptibility_dbm": -105.0,
            },
        ]
        self.isolation = {
            ("TX-X-BAND", "RX-GNSS"): 45.0,
            ("TX-X-BAND", "RX-TTC"): 40.0,
        }

    def test_raw_mask_segments_are_normalised(self):
        out = assess_antenna_port_spurious_emissions(
            self.emitters, self.victims, self.isolation
        )
        self.assertEqual(len(out["pairs"]), 2)
        self.assertTrue(out["compatible"])
        self.assertAlmostEqual(
            out["required_margin_db"], DEFAULT_REQUIRED_MARGIN_DB
        )

    def test_weak_isolation_produces_an_exceeded_pair(self):
        isolation = dict(self.isolation)
        isolation[("TX-X-BAND", "RX-GNSS")] = 10.0
        out = assess_antenna_port_spurious_emissions(
            self.emitters, self.victims, isolation
        )
        self.assertFalse(out["compatible"])
        self.assertEqual(len(out["exceeded_pairs"]), 1)
        self.assertEqual(out["exceeded_pairs"][0]["victim_port"], "RX-GNSS")

    def test_uncovered_victim_band_becomes_an_undeclared_pair(self):
        emitters = [
            {
                "port_id": "TX-X-BAND",
                "carrier_hz": 8000 * MHZ,
                "mask_segments": [seg(2600, 9000, -75.0)],
            }
        ]
        out = assess_antenna_port_spurious_emissions(
            emitters, self.victims, self.isolation
        )
        self.assertFalse(out["compatible"])
        self.assertEqual(len(out["undeclared_pairs"]), 2)

    def test_harmonic_in_victim_band_without_declared_limit_is_flagged(self):
        emitters = [
            {
                "port_id": "TX-L-BAND",
                "carrier_hz": 1035 * MHZ,
                "mask_segments": [seg(1000, 1500, -80.0), seg(2000, 2200, -80.0)],
            }
        ]
        victims = [
            {
                "port_id": "RX-TTC",
                "band_low_hz": 2025 * MHZ,
                "band_high_hz": 2110 * MHZ,
                "susceptibility_dbm": -105.0,
            },
            {
                "port_id": "RX-WIDE",
                "band_low_hz": 3000 * MHZ,
                "band_high_hz": 3200 * MHZ,
                "susceptibility_dbm": -105.0,
            },
        ]
        isolation = {
            ("TX-L-BAND", "RX-TTC"): 70.0,
            ("TX-L-BAND", "RX-WIDE"): 70.0,
        }
        out = assess_antenna_port_spurious_emissions(
            emitters, victims, isolation, 6.0, 3
        )
        orders = [f["order"] for f in out["harmonic_findings"]]
        self.assertIn(3, orders)
        self.assertFalse(out["compatible"])

    def test_covered_harmonic_raises_no_harmonic_finding(self):
        out = assess_antenna_port_spurious_emissions(
            self.emitters, self.victims, self.isolation, 6.0, 3
        )
        self.assertEqual(out["harmonic_findings"], [])

    def test_missing_isolation_entry_raises(self):
        isolation = {("TX-X-BAND", "RX-GNSS"): 45.0}
        with self.assertRaises(ValueError):
            assess_antenna_port_spurious_emissions(
                self.emitters, self.victims, isolation
            )

    def test_duplicate_emitter_port_raises(self):
        emitters = self.emitters + [dict(self.emitters[0])]
        with self.assertRaises(ValueError):
            assess_antenna_port_spurious_emissions(
                emitters, self.victims, self.isolation
            )

    def test_duplicate_victim_port_raises(self):
        victims = self.victims + [dict(self.victims[0])]
        isolation = dict(self.isolation)
        with self.assertRaises(ValueError):
            assess_antenna_port_spurious_emissions(
                self.emitters, victims, isolation
            )

    def test_empty_emitter_set_raises(self):
        with self.assertRaises(ValueError):
            assess_antenna_port_spurious_emissions([], self.victims, self.isolation)

    def test_empty_victim_set_raises(self):
        with self.assertRaises(ValueError):
            assess_antenna_port_spurious_emissions(self.emitters, [], self.isolation)

    def test_isolation_map_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_antenna_port_spurious_emissions(
                self.emitters, self.victims, [("TX-X-BAND", "RX-GNSS", 45.0)]
            )

    def test_non_positive_carrier_in_assessment_raises(self):
        emitters = [dict(self.emitters[0])]
        emitters[0]["carrier_hz"] = 0.0
        with self.assertRaises(ValueError):
            assess_antenna_port_spurious_emissions(
                emitters, self.victims, self.isolation
            )


if __name__ == "__main__":
    unittest.main()
