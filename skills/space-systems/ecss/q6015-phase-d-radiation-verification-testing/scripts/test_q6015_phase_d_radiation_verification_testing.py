"""Contract tests for the clause 4.4.4 flight-lot verification logic."""

import unittest

from q6015_phase_d_radiation_verification_testing_logic import (
    MILESTONE_SEQUENCE,
    PART_CATEGORIES,
    REQUIRED_SAMPLE_SIZE,
    RLAT_MANDATORY,
    assess_flight_lot,
    assess_verification_campaign,
    evaluate_lot_test,
    lot_is_covered,
    lot_verification_required,
    milestone_index,
    normalize_category,
    normalize_milestone,
    open_action_findings,
    required_sample_size,
)

HERITAGE = [{"part_reference": "RH1020", "diffusion_lot": "DL-7741"}]


def flight_lot(**overrides):
    lot = {
        "part_reference": "RH1020",
        "diffusion_lot": "DL-7741",
        "category": "radiation-sensitive",
        "test_results": [260.0] * 5,
    }
    lot.update(overrides)
    return lot


class CategoryTests(unittest.TestCase):
    def test_category_is_normalised(self):
        self.assertEqual(normalize_category("Radiation Critical"), "radiation-critical")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_category("radiation-indifferent")

    def test_empty_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_category("   ")

    def test_harder_category_demands_a_bigger_sample(self):
        self.assertGreater(
            required_sample_size("radiation-critical"),
            required_sample_size("radiation-tolerant"),
        )

    def test_every_category_has_a_sample_and_a_mandate_row(self):
        for category in PART_CATEGORIES:
            self.assertIn(category, REQUIRED_SAMPLE_SIZE)
            self.assertIn(category, RLAT_MANDATORY)


class MilestoneTests(unittest.TestCase):
    def test_milestone_is_normalised(self):
        self.assertEqual(normalize_milestone("Acceptance Review"), "acceptance-review")

    def test_milestones_are_ordered(self):
        self.assertLess(
            milestone_index("qualification-review"), milestone_index("acceptance-review")
        )

    def test_unknown_milestone_rejected(self):
        with self.assertRaises(ValueError):
            normalize_milestone("launch-rehearsal")

    def test_sequence_covers_every_index(self):
        for name in MILESTONE_SEQUENCE:
            self.assertEqual(MILESTONE_SEQUENCE[milestone_index(name)], name)


class HeritageCoverageTests(unittest.TestCase):
    def test_same_diffusion_lot_is_covered(self):
        self.assertTrue(lot_is_covered(flight_lot(), HERITAGE))

    def test_different_diffusion_lot_is_not_covered(self):
        self.assertFalse(lot_is_covered(flight_lot(diffusion_lot="DL-9002"), HERITAGE))

    def test_different_part_reference_is_not_covered(self):
        self.assertFalse(lot_is_covered(flight_lot(part_reference="RH2050"), HERITAGE))

    def test_empty_heritage_covers_nothing(self):
        self.assertFalse(lot_is_covered(flight_lot(), []))

    def test_missing_diffusion_lot_rejected(self):
        with self.assertRaises(ValueError):
            lot_is_covered({"part_reference": "RH1020"}, HERITAGE)

    def test_non_sequence_heritage_rejected(self):
        with self.assertRaises(ValueError):
            lot_is_covered(flight_lot(), HERITAGE[0])


class RequirementTests(unittest.TestCase):
    def test_hard_category_always_owes_a_test(self):
        required, reason = lot_verification_required(
            flight_lot(category="radiation-critical"), HERITAGE
        )
        self.assertTrue(required)
        self.assertIn("always", reason)

    def test_tolerant_category_with_heritage_is_exempt(self):
        required, _ = lot_verification_required(
            flight_lot(category="radiation-tolerant"), HERITAGE
        )
        self.assertFalse(required)

    def test_tolerant_category_without_heritage_owes_a_test(self):
        required, reason = lot_verification_required(
            flight_lot(category="radiation-tolerant", diffusion_lot="DL-9002"), HERITAGE
        )
        self.assertTrue(required)
        self.assertIn("no heritage", reason)


class LotTestTests(unittest.TestCase):
    def test_full_sample_with_margin_is_accepted(self):
        result = evaluate_lot_test([260.0] * 5, 100.0, 2.0, 5)
        self.assertTrue(result["accepted"])

    def test_worst_result_drives_the_margin(self):
        result = evaluate_lot_test([500.0, 500.0, 210.0, 500.0, 500.0], 100.0, 2.0, 5)
        self.assertAlmostEqual(result["worst_result"], 210.0, places=9)
        self.assertAlmostEqual(result["margin"], 2.1, places=9)

    def test_margin_exactly_on_the_requirement_is_met(self):
        result = evaluate_lot_test([200.0] * 5, 100.0, 2.0, 5)
        self.assertTrue(result["margin_met"])
        self.assertAlmostEqual(result["margin"], 2.0, places=9)

    def test_short_sample_is_rejected_even_with_margin(self):
        result = evaluate_lot_test([900.0] * 3, 100.0, 2.0, 5)
        self.assertFalse(result["accepted"])
        self.assertTrue(result["margin_met"])
        self.assertIn("below the", result["reason"])

    def test_margin_shortfall_is_reported(self):
        result = evaluate_lot_test([150.0] * 5, 100.0, 2.0, 5)
        self.assertFalse(result["accepted"])
        self.assertIn("margin", result["reason"])

    def test_empty_result_set_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_lot_test([], 100.0, 2.0, 5)

    def test_non_positive_result_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_lot_test([260.0, 0.0], 100.0, 2.0, 2)

    def test_non_integer_minimum_sample_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_lot_test([260.0] * 5, 100.0, 2.0, 5.0)


class FlightLotTests(unittest.TestCase):
    def test_accepted_lot_has_no_blocker(self):
        record = assess_flight_lot(flight_lot(), 100.0, 2.0, HERITAGE)
        self.assertTrue(record["accepted"])
        self.assertIsNone(record["blocker"])

    def test_exempt_lot_is_not_tested(self):
        record = assess_flight_lot(
            flight_lot(category="radiation-tolerant", test_results=None), 100.0, 2.0, HERITAGE
        )
        self.assertFalse(record["test_required"])
        self.assertIsNone(record["test"])
        self.assertTrue(record["accepted"])

    def test_owed_test_with_no_results_is_blocked(self):
        record = assess_flight_lot(flight_lot(test_results=None), 100.0, 2.0, HERITAGE)
        self.assertFalse(record["accepted"])
        self.assertIn("no results", record["blocker"])

    def test_undersized_sample_for_a_hard_category_is_blocked(self):
        record = assess_flight_lot(
            flight_lot(category="radiation-critical", test_results=[900.0] * 5),
            100.0,
            2.0,
            HERITAGE,
        )
        self.assertFalse(record["accepted"])

    def test_record_carries_the_normalised_identity(self):
        record = assess_flight_lot(
            flight_lot(part_reference="  RH 1020 "), 100.0, 2.0, HERITAGE
        )
        self.assertEqual(record["part_reference"], "rh-1020")

    def test_non_mapping_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_flight_lot(["RH1020"], 100.0, 2.0, HERITAGE)


class ActionClosureTests(unittest.TestCase):
    def test_closed_action_is_not_a_finding(self):
        actions = [
            {"id": "RHA-1", "due_milestone": "qualification-review", "status": "closed"}
        ]
        self.assertEqual(open_action_findings(actions, "qualification-review"), [])

    def test_open_action_due_at_the_milestone_is_a_finding(self):
        actions = [{"id": "RHA-1", "due_milestone": "qualification-review", "status": "open"}]
        self.assertEqual(len(open_action_findings(actions, "qualification-review")), 1)

    def test_in_work_action_is_still_a_finding(self):
        actions = [{"id": "RHA-1", "due_milestone": "qualification-review", "status": "in-work"}]
        self.assertIn("in-work", open_action_findings(actions, "qualification-review")[0])

    def test_later_action_is_not_yet_due(self):
        actions = [{"id": "RHA-1", "due_milestone": "acceptance-review", "status": "open"}]
        self.assertEqual(open_action_findings(actions, "qualification-review"), [])

    def test_earlier_action_is_still_due_at_a_later_milestone(self):
        actions = [{"id": "RHA-1", "due_milestone": "qualification-review", "status": "open"}]
        self.assertEqual(len(open_action_findings(actions, "acceptance-review")), 1)

    def test_unknown_status_rejected(self):
        actions = [{"id": "RHA-1", "due_milestone": "acceptance-review", "status": "nearly"}]
        with self.assertRaises(ValueError):
            open_action_findings(actions, "acceptance-review")

    def test_non_mapping_action_rejected(self):
        with self.assertRaises(ValueError):
            open_action_findings(["RHA-1"], "acceptance-review")


class CampaignTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "flight_lots": [flight_lot()],
            "heritage_lots": HERITAGE,
            "specified_level": 100.0,
            "required_margin": 2.0,
            "milestone": "qualification-review",
            "actions": [
                {"id": "RHA-1", "due_milestone": "qualification-review", "status": "closed"}
            ],
        }
        spec.update(overrides)
        return spec

    def test_clean_campaign_is_milestone_ready(self):
        result = assess_verification_campaign(self._spec())
        self.assertTrue(result["milestone_ready"])
        self.assertEqual(result["blockers"], [])

    def test_tested_and_exempt_lots_are_counted(self):
        result = assess_verification_campaign(
            self._spec(
                flight_lots=[
                    flight_lot(),
                    flight_lot(
                        part_reference="RH2050",
                        category="radiation-tolerant",
                        diffusion_lot="DL-7741",
                        test_results=None,
                    ),
                ],
                heritage_lots=HERITAGE
                + [{"part_reference": "RH2050", "diffusion_lot": "DL-7741"}],
            )
        )
        self.assertEqual(result["lots_tested"], 1)
        self.assertEqual(result["lots_exempt"], 1)

    def test_failed_lot_blocks_the_milestone(self):
        result = assess_verification_campaign(
            self._spec(flight_lots=[flight_lot(test_results=[120.0] * 5)])
        )
        self.assertFalse(result["milestone_ready"])

    def test_open_action_blocks_the_milestone(self):
        result = assess_verification_campaign(
            self._spec(
                actions=[
                    {"id": "RHA-2", "due_milestone": "qualification-review", "status": "open"}
                ]
            )
        )
        self.assertFalse(result["milestone_ready"])

    def test_lots_are_reported_in_identity_order(self):
        result = assess_verification_campaign(
            self._spec(
                flight_lots=[
                    flight_lot(part_reference="RH9000", diffusion_lot="DL-1"),
                    flight_lot(part_reference="RH1020", diffusion_lot="DL-2"),
                ]
            )
        )
        self.assertEqual(
            [item["part_reference"] for item in result["lots"]], ["rh1020", "rh9000"]
        )

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["milestone"]
        with self.assertRaises(ValueError):
            assess_verification_campaign(spec)

    def test_empty_flight_lot_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_verification_campaign(self._spec(flight_lots=[]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_verification_campaign(["flight_lots"])


if __name__ == "__main__":
    unittest.main()
