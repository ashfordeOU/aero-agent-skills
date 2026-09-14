#!/usr/bin/env python3
"""Contract test for the coverglass acceptance test sequence (offline).

Walks the clause workflow step by step: the sequence record validation
and the invented or repeated steps it refuses, the activity coverage
kept apart from the order, the inversion count reduced to a conformance
fraction, the precedence pairs that hold whatever else moves, the
floors a float lands exactly on, the ranked population verdict, and the
roll-up over the delivered and the qualification populations into one
campaign verdict. This is the gate 3 review evidence for the leaf.
"""

import unittest

from e2008_coverglass_acceptance_test_sequence_logic import (
    BASELINE_SEQUENCE,
    CAMPAIGN_CONFORMING,
    CAMPAIGN_NOT_CONFORMING,
    SEQUENCE_ABSENT,
    SEQUENCE_CONFORMING,
    SEQUENCE_INCOMPLETE,
    SEQUENCE_PRECEDENCE_BROKEN,
    SEQUENCE_REORDERED,
    activity_coverage,
    assess_acceptance_sequence,
    assess_population_sequence,
    order_inversions,
    precedence_violations,
    resolve_sequence_policy,
    validate_sequence_record,
)

DRAW = BASELINE_SEQUENCE[0]
DIMENSIONAL = BASELINE_SEQUENCE[1]
VISUAL = BASELINE_SEQUENCE[2]
OPTICAL = BASELINE_SEQUENCE[3]
CONDUCTIVITY = BASELINE_SEQUENCE[4]
EXPOSURE = BASELINE_SEQUENCE[5]
POST_VISUAL = BASELINE_SEQUENCE[6]

SWAPPED = [DRAW, DIMENSIONAL, VISUAL, CONDUCTIVITY, OPTICAL, EXPOSURE, POST_VISUAL]
EXPOSURE_EARLY = [
    DRAW,
    DIMENSIONAL,
    EXPOSURE,
    VISUAL,
    OPTICAL,
    CONDUCTIVITY,
    POST_VISUAL,
]


def _entry(population="delivery", steps=None):
    if steps is None:
        steps = list(BASELINE_SEQUENCE)
    return {"population": population, "steps": list(steps)}


def _case(*entries, **overrides):
    case = {"campaign_id": "CG-CAMP-8", "sequences": list(entries)}
    case.update(overrides)
    return case


class SequenceValidationTests(unittest.TestCase):
    def test_a_sound_sequence_validates(self):
        record = validate_sequence_record(_entry())
        self.assertEqual(record["population"], "delivery")
        self.assertEqual(len(record["steps"]), len(BASELINE_SEQUENCE))

    def test_an_unknown_population_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence_record(_entry(population="spares"))

    def test_an_invented_step_is_refused_rather_than_counted(self):
        with self.assertRaises(ValueError):
            validate_sequence_record(
                _entry(steps=[DRAW, "coverglass-launch-rehearsal"])
            )

    def test_a_repeated_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence_record(_entry(steps=[DRAW, DIMENSIONAL, DRAW]))

    def test_a_non_sequence_step_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence_record(
                {"population": "delivery", "steps": "draw then inspect"}
            )

    def test_an_empty_step_label_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence_record(_entry(steps=[DRAW, "   "]))


class CoverageTests(unittest.TestCase):
    def test_the_baseline_reaches_every_activity(self):
        coverage = activity_coverage(list(BASELINE_SEQUENCE))
        self.assertEqual(coverage["missing"], [])
        self.assertAlmostEqual(coverage["coverage"], 1.0, places=9)

    def test_an_omitted_activity_is_named(self):
        coverage = activity_coverage([s for s in BASELINE_SEQUENCE if s != OPTICAL])
        self.assertEqual(coverage["missing"], [OPTICAL])

    def test_coverage_landing_exactly_on_a_relaxed_floor_is_carried(self):
        steps = list(BASELINE_SEQUENCE[:6])
        result = assess_population_sequence(
            _entry(steps=steps), {"min_activity_coverage": 6.0 / 7.0}
        )
        self.assertAlmostEqual(result["coverage"]["coverage"], 6.0 / 7.0, places=9)
        self.assertTrue(result["meets_coverage"])
        self.assertEqual(result["verdict"], SEQUENCE_CONFORMING)


class OrderTests(unittest.TestCase):
    def test_the_baseline_order_inverts_nothing(self):
        order = order_inversions(list(BASELINE_SEQUENCE))
        self.assertEqual(order["inversions"], 0)
        self.assertEqual(order["pairs"], 21)
        self.assertAlmostEqual(order["conformance"], 1.0, places=9)

    def test_one_adjacent_swap_counts_one_inverted_pair(self):
        order = order_inversions(SWAPPED)
        self.assertEqual(order["inversions"], 1)
        self.assertEqual(order["inverted_pairs"], [(CONDUCTIVITY, OPTICAL)])

    def test_a_fully_reversed_order_inverts_every_pair(self):
        order = order_inversions(list(reversed(BASELINE_SEQUENCE)))
        self.assertEqual(order["inversions"], order["pairs"])
        self.assertAlmostEqual(order["conformance"], 0.0, places=9)

    def test_conformance_landing_exactly_on_the_floor_is_carried(self):
        result = assess_population_sequence(
            _entry(steps=SWAPPED), {"min_order_conformance": 20.0 / 21.0}
        )
        self.assertAlmostEqual(result["order"]["conformance"], 20.0 / 21.0, places=9)
        self.assertTrue(result["meets_order"])
        self.assertEqual(result["verdict"], SEQUENCE_CONFORMING)

    def test_a_shorter_run_is_graded_on_its_own_pair_count(self):
        order = order_inversions([DRAW, DIMENSIONAL, VISUAL])
        self.assertEqual(order["pairs"], 3)
        self.assertAlmostEqual(order["conformance"], 1.0, places=9)


class PrecedenceTests(unittest.TestCase):
    def test_the_baseline_breaks_no_declared_pair(self):
        self.assertEqual(precedence_violations(list(BASELINE_SEQUENCE)), [])

    def test_an_exposure_pulled_ahead_breaks_its_pairs(self):
        broken = precedence_violations(EXPOSURE_EARLY)
        self.assertIn((VISUAL, EXPOSURE), broken)
        self.assertIn((OPTICAL, EXPOSURE), broken)

    def test_a_pair_with_one_member_absent_is_not_a_break(self):
        broken = precedence_violations([DRAW, DIMENSIONAL, EXPOSURE, POST_VISUAL])
        self.assertEqual(broken, [])

    def test_policy_can_carry_a_precedence_break(self):
        result = assess_population_sequence(
            _entry(steps=EXPOSURE_EARLY),
            {"carry_precedence_break": True, "min_order_conformance": 0.5},
        )
        self.assertEqual(result["verdict"], SEQUENCE_CONFORMING)
        self.assertTrue(result["precedence_broken"])


class PolicyTests(unittest.TestCase):
    def test_defaults_resolve(self):
        settings = resolve_sequence_policy()
        self.assertAlmostEqual(settings["min_order_conformance"], 1.0, places=12)
        self.assertFalse(settings["carry_precedence_break"])

    def test_a_conformance_floor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            resolve_sequence_policy({"min_order_conformance": 1.5})

    def test_a_non_boolean_precedence_position_rejected(self):
        with self.assertRaises(ValueError):
            resolve_sequence_policy({"carry_precedence_break": "sometimes"})


class PopulationVerdictTests(unittest.TestCase):
    def test_the_baseline_order_conforms(self):
        result = assess_population_sequence(_entry())
        self.assertEqual(result["verdict"], SEQUENCE_CONFORMING)
        self.assertEqual(result["findings"], [])

    def test_an_undeclared_order_ranks_worst(self):
        result = assess_population_sequence(_entry(steps=[]))
        self.assertEqual(result["verdict"], SEQUENCE_ABSENT)
        self.assertTrue(any("not been sequenced" in f for f in result["findings"]))

    def test_an_incomplete_order_outranks_a_broken_precedence(self):
        steps = [s for s in EXPOSURE_EARLY if s != CONDUCTIVITY]
        result = assess_population_sequence(_entry(steps=steps))
        self.assertEqual(result["verdict"], SEQUENCE_INCOMPLETE)

    def test_a_broken_precedence_outranks_a_plain_reordering(self):
        result = assess_population_sequence(_entry(steps=EXPOSURE_EARLY))
        self.assertEqual(result["verdict"], SEQUENCE_PRECEDENCE_BROKEN)

    def test_a_drifted_order_with_no_broken_pair_is_only_reordered(self):
        result = assess_population_sequence(_entry(steps=SWAPPED))
        self.assertEqual(result["verdict"], SEQUENCE_REORDERED)
        self.assertTrue(result["findings"])


class CampaignRollUpTests(unittest.TestCase):
    def test_both_populations_conforming_closes_the_campaign(self):
        result = assess_acceptance_sequence(
            _case(_entry("delivery"), _entry("qualification"))
        )
        self.assertEqual(result["verdict"], CAMPAIGN_CONFORMING)
        self.assertEqual(result["findings"], [])

    def test_a_missing_qualification_order_blocks_a_clean_delivery_order(self):
        result = assess_acceptance_sequence(_case(_entry("delivery")))
        self.assertEqual(result["verdict"], CAMPAIGN_NOT_CONFORMING)
        self.assertEqual(result["missing_populations"], ["qualification"])

    def test_the_weakest_population_is_named_by_rank(self):
        result = assess_acceptance_sequence(
            _case(_entry("delivery"), _entry("qualification", steps=[]))
        )
        self.assertEqual(result["weakest_population"], "qualification")
        self.assertIn(SEQUENCE_ABSENT, result["grouped_populations"])
        self.assertIn(SEQUENCE_CONFORMING, result["grouped_populations"])

    def test_a_reordered_qualification_run_blocks_the_campaign(self):
        result = assess_acceptance_sequence(
            _case(_entry("delivery"), _entry("qualification", steps=SWAPPED))
        )
        self.assertEqual(result["verdict"], CAMPAIGN_NOT_CONFORMING)
        self.assertEqual(
            result["grouped_populations"][SEQUENCE_REORDERED], ["qualification"]
        )

    def test_one_population_declaring_two_orders_rejected(self):
        with self.assertRaises(ValueError):
            assess_acceptance_sequence(_case(_entry("delivery"), _entry("delivery")))

    def test_an_empty_campaign_rejected(self):
        with self.assertRaises(ValueError):
            assess_acceptance_sequence({"campaign_id": "CG-CAMP-8", "sequences": []})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_acceptance_sequence("the delivered pieces went through in order")


if __name__ == "__main__":
    unittest.main()
