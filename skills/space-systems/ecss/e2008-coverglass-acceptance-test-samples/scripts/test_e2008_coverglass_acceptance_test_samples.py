#!/usr/bin/env python3
"""Contract test for coverglass acceptance test samples (offline).

Walks the clause workflow step by step: the lot record validation and
the pooled, over-drawn and repeated draws it refuses, the sample floor
of forty pieces, the short lot that can only close on an exhaustive
draw, the proportional spread measured against the lot's own strata,
the convenience draw taken off one carrier, the tolerance boundary a
float lands on, and the roll-up into one shipment verdict. This is the
gate 3 review evidence for the leaf.
"""

import copy
import unittest

from e2008_coverglass_acceptance_test_samples_logic import (
    DRAW_ABSENT,
    DRAW_CLUSTERED,
    DRAW_SHORT,
    DRAW_SOUND,
    SHIPMENT_ACCEPTED,
    SHIPMENT_NOT_ACCEPTED,
    assess_lot_sample,
    assess_shipment_sampling,
    resolve_sampling_policy,
    sample_size_assessment,
    stratum_spread,
    validate_lot_record,
)


def _draw(prefix, spec):
    pieces = []
    index = 0
    for stratum in sorted(spec):
        for _ in range(spec[stratum]):
            pieces.append(
                {"piece_id": "%s-P%03d" % (prefix, index), "stratum": stratum}
            )
            index += 1
    return pieces


def _lot(lot_id="LOT-1", strata=None, spec=None):
    strata = dict(strata or {"tray-a": 50, "tray-b": 50})
    spec = dict(spec if spec is not None else {"tray-a": 20, "tray-b": 20})
    return {"lot_id": lot_id, "strata": strata, "draw": _draw(lot_id, spec)}


def _shipment(*lots):
    return {"shipment_id": "SHP-8", "lots": list(lots) or [_lot()]}


class LotRecordValidationTests(unittest.TestCase):
    def test_a_sound_lot_validates_and_sums_its_strata(self):
        record = validate_lot_record(_lot())
        self.assertEqual(record["lot_size"], 100)
        self.assertEqual(len(record["draw"]), 40)

    def test_a_declared_lot_size_disagreeing_with_the_strata_rejected(self):
        lot = _lot()
        lot["lot_size"] = 99
        with self.assertRaises(ValueError):
            validate_lot_record(lot)

    def test_a_pooled_draw_is_refused_rather_than_scored(self):
        lot = _lot()
        lot["draw"][0]["from_lot"] = "LOT-2"
        with self.assertRaises(ValueError):
            validate_lot_record(lot)

    def test_a_piece_naming_an_undeclared_stratum_rejected(self):
        lot = _lot()
        lot["draw"][0]["stratum"] = "tray-z"
        with self.assertRaises(ValueError):
            validate_lot_record(lot)

    def test_a_repeated_piece_rejected(self):
        lot = _lot()
        lot["draw"].append(copy.deepcopy(lot["draw"][0]))
        with self.assertRaises(ValueError):
            validate_lot_record(lot)

    def test_a_draw_larger_than_the_lot_rejected(self):
        lot = _lot(strata={"tray-a": 10, "tray-b": 10}, spec={"tray-a": 10, "tray-b": 10})
        lot["strata"] = {"tray-a": 5, "tray-b": 5}
        with self.assertRaises(ValueError):
            validate_lot_record(lot)

    def test_a_lot_with_no_strata_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot_record({"lot_id": "LOT-1", "strata": {}, "draw": []})

    def test_a_non_whole_stratum_size_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot_record(
                {"lot_id": "LOT-1", "strata": {"tray-a": 12.5}, "draw": []}
            )

    def test_an_empty_lot_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot_record(_lot(lot_id="   "))


class SampleSizeTests(unittest.TestCase):
    def test_a_draw_exactly_on_the_floor_meets_it(self):
        result = sample_size_assessment(_lot())
        self.assertEqual(result["drawn"], 40)
        self.assertTrue(result["meets_floor"])
        self.assertAlmostEqual(result["draw_fraction"], 0.40, places=9)
        self.assertEqual(result["findings"], [])

    def test_a_draw_one_piece_under_the_floor_is_short(self):
        lot = _lot(spec={"tray-a": 20, "tray-b": 19})
        result = sample_size_assessment(lot)
        self.assertFalse(result["meets_floor"])
        self.assertTrue(result["findings"])

    def test_an_undrawn_lot_is_absent_not_thin(self):
        lot = _lot(spec={})
        result = sample_size_assessment(lot)
        self.assertEqual(result["drawn"], 0)
        self.assertTrue(any("not been sampled" in f for f in result["findings"]))

    def test_a_short_lot_closes_only_on_an_exhaustive_draw(self):
        lot = _lot(
            strata={"tray-a": 10, "tray-b": 10}, spec={"tray-a": 10, "tray-b": 10}
        )
        result = sample_size_assessment(lot)
        self.assertTrue(result["short_lot"])
        self.assertTrue(result["exhaustive"])
        self.assertTrue(result["meets_floor"])
        self.assertAlmostEqual(result["draw_fraction"], 1.0, places=9)

    def test_a_short_lot_drawn_partly_still_fails(self):
        lot = _lot(strata={"tray-a": 10, "tray-b": 10}, spec={"tray-a": 10})
        result = sample_size_assessment(lot)
        self.assertFalse(result["meets_floor"])

    def test_policy_can_refuse_the_exhaustive_substitute(self):
        lot = _lot(
            strata={"tray-a": 10, "tray-b": 10}, spec={"tray-a": 10, "tray-b": 10}
        )
        result = sample_size_assessment(
            lot, {"accept_exhaustive_short_lot": False}
        )
        self.assertFalse(result["meets_floor"])
        self.assertTrue(any("substitute" in f for f in result["findings"]))


class StratumSpreadTests(unittest.TestCase):
    def test_a_proportional_draw_deviates_by_nothing(self):
        result = stratum_spread(_lot())
        self.assertAlmostEqual(result["worst_deviation"], 0.0, places=9)
        self.assertTrue(result["proportional"])
        self.assertTrue(result["meets_coverage"])

    def test_an_uneven_lot_is_graded_on_its_own_composition(self):
        lot = _lot(
            strata={"tray-a": 80, "tray-b": 20}, spec={"tray-a": 32, "tray-b": 8}
        )
        result = stratum_spread(lot)
        self.assertAlmostEqual(result["worst_deviation"], 0.0, places=9)
        self.assertTrue(result["proportional"])

    def test_a_deviation_landing_exactly_on_the_tolerance_is_carried(self):
        lot = _lot(spec={"tray-a": 26, "tray-b": 14})
        result = stratum_spread(lot)
        self.assertAlmostEqual(result["worst_deviation"], 0.15, places=9)
        self.assertTrue(result["proportional"])

    def test_a_convenience_draw_off_one_carrier_is_reported(self):
        lot = _lot(spec={"tray-a": 40})
        result = stratum_spread(lot)
        self.assertEqual(result["missed"], ["tray-b"])
        self.assertFalse(result["proportional"])
        self.assertTrue(any("convenience draw" in f for f in result["findings"]))

    def test_a_missed_stratum_is_named_even_when_policy_relaxes_coverage(self):
        lot = _lot(
            strata={"tray-a": 48, "tray-b": 48, "tray-c": 4},
            spec={"tray-a": 20, "tray-b": 20},
        )
        result = stratum_spread(lot, {"min_stratum_coverage": 0.6666666666666666})
        self.assertAlmostEqual(result["coverage"], 2.0 / 3.0, places=9)
        self.assertTrue(result["meets_coverage"])
        self.assertTrue(result["proportional"])
        self.assertEqual(result["missed"], ["tray-c"])
        self.assertTrue(result["findings"])


class PolicyTests(unittest.TestCase):
    def test_defaults_resolve(self):
        settings = resolve_sampling_policy()
        self.assertEqual(settings["min_sample_size"], 40)
        self.assertAlmostEqual(settings["max_stratum_deviation"], 0.15, places=12)

    def test_a_zero_sample_floor_rejected(self):
        with self.assertRaises(ValueError):
            resolve_sampling_policy({"min_sample_size": 0})

    def test_a_tolerance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            resolve_sampling_policy({"max_stratum_deviation": 1.5})

    def test_a_non_boolean_short_lot_position_rejected(self):
        with self.assertRaises(ValueError):
            resolve_sampling_policy({"accept_exhaustive_short_lot": "sometimes"})


class LotVerdictTests(unittest.TestCase):
    def test_a_sound_lot_carries_no_findings(self):
        result = assess_lot_sample(_lot())
        self.assertEqual(result["verdict"], DRAW_SOUND)
        self.assertEqual(result["findings"], [])

    def test_an_undrawn_lot_ranks_worst(self):
        result = assess_lot_sample(_lot(spec={}))
        self.assertEqual(result["verdict"], DRAW_ABSENT)

    def test_a_short_draw_outranks_a_clustered_one(self):
        result = assess_lot_sample(_lot(spec={"tray-a": 20}))
        self.assertEqual(result["verdict"], DRAW_SHORT)

    def test_a_large_draw_off_one_carrier_is_still_not_random(self):
        result = assess_lot_sample(_lot(spec={"tray-a": 45}))
        self.assertEqual(result["verdict"], DRAW_CLUSTERED)
        self.assertTrue(result["size"]["meets_floor"])


class ShipmentRollUpTests(unittest.TestCase):
    def test_a_sound_shipment_is_accepted(self):
        result = assess_shipment_sampling(_shipment(_lot("LOT-1"), _lot("LOT-2")))
        self.assertEqual(result["verdict"], SHIPMENT_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["shipment_fraction"], 0.40, places=9)

    def test_one_clustered_lot_blocks_the_shipment(self):
        case = _shipment(_lot("LOT-1"), _lot("LOT-2", spec={"tray-a": 45}))
        result = assess_shipment_sampling(case)
        self.assertEqual(result["verdict"], SHIPMENT_NOT_ACCEPTED)
        self.assertIn(DRAW_CLUSTERED, result["grouped_lots"])

    def test_the_weakest_lot_is_named_by_rank(self):
        case = _shipment(
            _lot("LOT-1"),
            _lot("LOT-2", spec={"tray-a": 45}),
            _lot("LOT-3", spec={}),
        )
        result = assess_shipment_sampling(case)
        self.assertEqual(result["weakest_lot"], "LOT-3")
        self.assertIn(DRAW_ABSENT, result["grouped_lots"])
        self.assertIn(DRAW_SOUND, result["grouped_lots"])

    def test_lots_are_grouped_by_verdict(self):
        case = _shipment(_lot("LOT-1"), _lot("LOT-2"))
        result = assess_shipment_sampling(case)
        self.assertEqual(result["grouped_lots"][DRAW_SOUND], ["LOT-1", "LOT-2"])

    def test_a_lot_listed_twice_rejected(self):
        case = _shipment(_lot("LOT-1"), _lot("LOT-1"))
        with self.assertRaises(ValueError):
            assess_shipment_sampling(case)

    def test_an_empty_shipment_rejected(self):
        with self.assertRaises(ValueError):
            assess_shipment_sampling({"shipment_id": "SHP-8", "lots": []})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_shipment_sampling("forty pieces were taken off the top tray")


if __name__ == "__main__":
    unittest.main()
