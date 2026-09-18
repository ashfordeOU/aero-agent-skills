#!/usr/bin/env python3
"""Contract tests for the clause 7.3.2 architecture review item logic."""

import math
import unittest

from q6012_architecture_review_item_logic import (
    MARGIN_TOLERANCE,
    REQUIREMENT_SENSE,
    assess_architecture_review,
    cascade_gain_db,
    cascade_noise_figure_db,
    cascade_output_ip3_dbm,
    chain_performance,
    db_to_linear,
    linear_to_db,
    normalise_chain,
    requirement_margins,
    topology_coverage,
    total_dc_power_mw,
    validate_block,
)

REQUIRED_FUNCTIONS = ("low-noise-amplification", "gain-stage", "output-match")


def blocks(**patch):
    """A three-block receive chain: LNA, gain stage, matched output stage."""
    base = [
        {"name": "lna", "function": "low-noise-amplification", "gain_db": 15.0,
         "noise_figure_db": 1.5, "output_ip3_dbm": 18.0, "dc_power_mw": 60.0},
        {"name": "drv", "function": "gain-stage", "gain_db": 10.0,
         "noise_figure_db": 4.0, "output_ip3_dbm": 24.0, "dc_power_mw": 120.0},
        {"name": "out", "function": "output-match", "gain_db": -1.0,
         "noise_figure_db": 1.0, "output_ip3_dbm": 30.0, "dc_power_mw": 0.0},
    ]
    by_name = {entry["name"]: entry for entry in base}
    for name, changes in patch.items():
        by_name[name].update(changes)
    return list(by_name.values())


def spec(**kwargs):
    payload = {
        "blocks": blocks(),
        "requirements": {
            "gain_db": 20.0,
            "noise_figure_db": 3.0,
            "output_ip3_dbm": 20.0,
            "dc_power_mw": 250.0,
        },
        "required_functions": REQUIRED_FUNCTIONS,
    }
    payload.update(kwargs)
    return payload


class ConversionTests(unittest.TestCase):
    def test_zero_db_is_unity(self):
        self.assertAlmostEqual(db_to_linear(0.0), 1.0, places=9)

    def test_ten_db_is_ten(self):
        self.assertAlmostEqual(db_to_linear(10.0), 10.0, places=9)

    def test_round_trip_is_the_identity(self):
        self.assertAlmostEqual(linear_to_db(db_to_linear(7.3)), 7.3, places=9)

    def test_negative_db_is_a_loss(self):
        self.assertAlmostEqual(db_to_linear(-3.0), 10.0 ** -0.3, places=9)

    def test_non_positive_ratio_rejected(self):
        with self.assertRaises(ValueError):
            linear_to_db(0.0)

    def test_boolean_input_rejected(self):
        with self.assertRaises(ValueError):
            db_to_linear(True)

    def test_non_finite_input_rejected(self):
        with self.assertRaises(ValueError):
            db_to_linear(float("inf"))


class ValidateBlockTests(unittest.TestCase):
    def test_normalises_a_declared_block(self):
        record = validate_block(blocks()[0])
        self.assertEqual(record["name"], "lna")
        self.assertAlmostEqual(record["gain_db"], 15.0, places=9)

    def test_dc_power_defaults_to_zero(self):
        record = validate_block({"name": "pad", "function": "output-match",
                                 "gain_db": -2.0, "noise_figure_db": 2.0,
                                 "output_ip3_dbm": 40.0})
        self.assertAlmostEqual(record["dc_power_mw"], 0.0, places=9)

    def test_block_without_a_function_rejected(self):
        entry = blocks()[0]
        del entry["function"]
        with self.assertRaises(ValueError):
            validate_block(entry)

    def test_negative_noise_figure_rejected(self):
        with self.assertRaises(ValueError):
            validate_block(blocks(lna={"noise_figure_db": -0.5})[0])

    def test_negative_dc_power_rejected(self):
        with self.assertRaises(ValueError):
            validate_block(blocks(lna={"dc_power_mw": -1.0})[0])

    def test_non_mapping_block_rejected(self):
        with self.assertRaises(ValueError):
            validate_block(["lna", 15.0])

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_block(blocks(lna={"name": "  "})[0])

    def test_empty_chain_rejected(self):
        with self.assertRaises(ValueError):
            normalise_chain([])

    def test_duplicate_block_name_rejected(self):
        entries = blocks()
        entries.append(dict(entries[0]))
        with self.assertRaises(ValueError):
            normalise_chain(entries)


class CascadeTests(unittest.TestCase):
    def setUp(self):
        self.chain = normalise_chain(blocks())

    def test_gain_adds_in_decibels(self):
        self.assertAlmostEqual(cascade_gain_db(self.chain), 24.0, places=9)

    def test_single_block_gain_is_its_own(self):
        chain = normalise_chain([blocks()[0]])
        self.assertAlmostEqual(cascade_gain_db(chain), 15.0, places=9)

    def test_single_block_noise_figure_is_its_own(self):
        chain = normalise_chain([blocks()[0]])
        self.assertAlmostEqual(cascade_noise_figure_db(chain), 1.5, places=9)

    def test_noise_figure_matches_the_friis_expansion(self):
        f1 = db_to_linear(1.5)
        f2 = db_to_linear(4.0)
        f3 = db_to_linear(1.0)
        g1 = db_to_linear(15.0)
        g2 = db_to_linear(10.0)
        expected = 10.0 * math.log10(f1 + (f2 - 1.0) / g1 + (f3 - 1.0) / (g1 * g2))
        self.assertAlmostEqual(cascade_noise_figure_db(self.chain), expected, places=9)

    def test_first_stage_dominates_the_noise_figure(self):
        base = cascade_noise_figure_db(normalise_chain(blocks()))
        tail = cascade_noise_figure_db(normalise_chain(blocks(drv={"noise_figure_db": 8.0})))
        front = cascade_noise_figure_db(normalise_chain(blocks(lna={"noise_figure_db": 5.5})))
        self.assertLess(tail - base, front - base)

    def test_front_end_noise_moves_the_chain_one_for_one(self):
        raised = normalise_chain(blocks(lna={"noise_figure_db": 2.5}))
        self.assertGreater(
            cascade_noise_figure_db(raised) - cascade_noise_figure_db(self.chain), 0.5
        )

    def test_single_block_output_ip3_is_its_own(self):
        chain = normalise_chain([blocks()[1]])
        self.assertAlmostEqual(cascade_output_ip3_dbm(chain), 24.0, places=9)

    def test_output_ip3_matches_the_reciprocal_sum(self):
        g2 = db_to_linear(10.0)
        g3 = db_to_linear(-1.0)
        reciprocal = (
            1.0 / (db_to_linear(18.0) * g2 * g3)
            + 1.0 / (db_to_linear(24.0) * g3)
            + 1.0 / db_to_linear(30.0)
        )
        expected = 10.0 * math.log10(1.0 / reciprocal)
        self.assertAlmostEqual(cascade_output_ip3_dbm(self.chain), expected, places=9)

    def test_cascaded_output_ip3_never_beats_the_weakest_referred_stage(self):
        referred_first = 18.0 + 10.0 - 1.0
        self.assertLess(cascade_output_ip3_dbm(self.chain), referred_first)

    def test_two_equal_stages_lose_three_decibels(self):
        chain = normalise_chain([
            {"name": "a", "function": "gain-stage", "gain_db": 0.0,
             "noise_figure_db": 3.0, "output_ip3_dbm": 20.0},
            {"name": "b", "function": "gain-stage", "gain_db": 0.0,
             "noise_figure_db": 3.0, "output_ip3_dbm": 20.0},
        ])
        self.assertAlmostEqual(
            cascade_output_ip3_dbm(chain), 20.0 - 10.0 * math.log10(2.0), places=9
        )

    def test_dc_power_is_the_sum_of_the_blocks(self):
        self.assertAlmostEqual(total_dc_power_mw(self.chain), 180.0, places=9)

    def test_performance_carries_every_metric(self):
        performance = chain_performance(self.chain)
        self.assertEqual(set(performance), set(REQUIREMENT_SENSE))


class TopologyCoverageTests(unittest.TestCase):
    def test_full_topology_is_covered(self):
        coverage = topology_coverage(normalise_chain(blocks()), REQUIRED_FUNCTIONS)
        self.assertTrue(coverage["covered"])
        self.assertAlmostEqual(coverage["coverage_fraction"], 1.0, places=9)

    def test_absent_function_is_named(self):
        entries = [b for b in blocks() if b["function"] != "output-match"]
        coverage = topology_coverage(normalise_chain(entries), REQUIRED_FUNCTIONS)
        self.assertEqual(coverage["missing_functions"], ["output-match"])
        self.assertFalse(coverage["covered"])

    def test_coverage_fraction_counts_the_missing_functions(self):
        entries = [b for b in blocks() if b["function"] == "gain-stage"]
        coverage = topology_coverage(normalise_chain(entries), REQUIRED_FUNCTIONS)
        self.assertAlmostEqual(coverage["coverage_fraction"], 1.0 / 3.0, places=9)

    def test_block_nobody_asked_for_is_reported(self):
        entries = blocks()
        entries.append({"name": "sw", "function": "bypass-switch", "gain_db": -1.5,
                        "noise_figure_db": 1.5, "output_ip3_dbm": 45.0})
        coverage = topology_coverage(normalise_chain(entries), REQUIRED_FUNCTIONS)
        self.assertEqual(coverage["unrequested_functions"], ["bypass-switch"])
        self.assertTrue(coverage["covered"])

    def test_empty_required_function_list_rejected(self):
        with self.assertRaises(ValueError):
            topology_coverage(normalise_chain(blocks()), [])


class RequirementMarginTests(unittest.TestCase):
    def setUp(self):
        self.performance = chain_performance(normalise_chain(blocks()))

    def test_minimum_sense_margin_is_value_minus_limit(self):
        margins = requirement_margins(self.performance, {"gain_db": 20.0})
        self.assertAlmostEqual(margins["gain_db"]["margin"], 4.0, places=9)
        self.assertTrue(margins["gain_db"]["met"])

    def test_maximum_sense_margin_is_limit_minus_value(self):
        margins = requirement_margins(self.performance, {"dc_power_mw": 250.0})
        self.assertAlmostEqual(margins["dc_power_mw"]["margin"], 70.0, places=9)
        self.assertTrue(margins["dc_power_mw"]["met"])

    def test_shortfall_gives_a_negative_margin(self):
        margins = requirement_margins(self.performance, {"gain_db": 30.0})
        self.assertAlmostEqual(margins["gain_db"]["margin"], -6.0, places=9)
        self.assertFalse(margins["gain_db"]["met"])

    def test_value_exactly_on_a_minimum_limit_is_met(self):
        limit = self.performance["gain_db"]
        margins = requirement_margins(self.performance, {"gain_db": limit})
        self.assertAlmostEqual(margins["gain_db"]["margin"], 0.0, places=9)
        self.assertTrue(margins["gain_db"]["met"])

    def test_value_exactly_on_a_maximum_limit_is_met(self):
        limit = self.performance["noise_figure_db"]
        margins = requirement_margins(self.performance, {"noise_figure_db": limit})
        self.assertAlmostEqual(margins["noise_figure_db"]["margin"], 0.0, places=9)
        self.assertTrue(margins["noise_figure_db"]["met"])

    def test_unknown_requirement_metric_rejected(self):
        with self.assertRaises(ValueError):
            requirement_margins(self.performance, {"phase_noise_dbc": -100.0})

    def test_empty_requirement_set_rejected(self):
        with self.assertRaises(ValueError):
            requirement_margins(self.performance, {})

    def test_missing_performance_value_rejected(self):
        with self.assertRaises(ValueError):
            requirement_margins({"gain_db": 24.0}, {"noise_figure_db": 3.0})

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(MARGIN_TOLERANCE, 1e-6)


class AssessArchitectureReviewTests(unittest.TestCase):
    def test_compliant_architecture_is_accepted(self):
        result = assess_architecture_review(spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])

    def test_gain_shortfall_is_reported(self):
        payload = spec()
        payload["requirements"] = dict(payload["requirements"], gain_db=30.0)
        result = assess_architecture_review(payload)
        self.assertFalse(result["accepted"])
        self.assertTrue(any("gain_db" in f for f in result["findings"]))

    def test_noise_figure_overrun_is_reported(self):
        payload = spec(blocks=blocks(lna={"noise_figure_db": 4.5}))
        result = assess_architecture_review(payload)
        self.assertFalse(result["accepted"])
        self.assertTrue(any("noise_figure_db" in f for f in result["findings"]))

    def test_dc_budget_overrun_is_reported(self):
        payload = spec(blocks=blocks(drv={"dc_power_mw": 400.0}))
        result = assess_architecture_review(payload)
        self.assertFalse(result["accepted"])
        self.assertTrue(any("dc_power_mw" in f for f in result["findings"]))

    def test_missing_topology_function_is_reported(self):
        entries = [b for b in blocks() if b["function"] != "output-match"]
        result = assess_architecture_review(spec(blocks=entries))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("realises no block" in f for f in result["findings"]))

    def test_coverage_is_absent_when_no_functions_were_required(self):
        payload = spec()
        del payload["required_functions"]
        result = assess_architecture_review(payload)
        self.assertIsNone(result["coverage"])
        self.assertTrue(result["accepted"])

    def test_missing_spec_key_rejected(self):
        payload = spec()
        del payload["requirements"]
        with self.assertRaises(ValueError):
            assess_architecture_review(payload)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_architecture_review(["blocks"])

    def test_performance_is_reproduced_in_the_result(self):
        result = assess_architecture_review(spec())
        self.assertAlmostEqual(result["performance"]["gain_db"], 24.0, places=9)
        self.assertAlmostEqual(result["performance"]["dc_power_mw"], 180.0, places=9)


if __name__ == "__main__":
    unittest.main()
