"""Contract tests for the clause 5.3.8 Class 2 radiation verification logic.

The cases walk the decision one step at a time: the category the project graded
the part to, the knockdown a heritage record takes for its similarity tier, the
radiation design margin that credit produces against the declared environment,
the destructive single event veto and the one mitigation that may be credited
against it, and the route the part ends on. Boundary doses are asserted with
assertAlmostEqual against the bound and with the decision the code then takes,
never with a strict float inequality at the bound.
"""

import unittest

from q60_class_2_radiation_verification_testing_logic import (
    DEFAULT_HERITAGE_CREDIT,
    DEFAULT_REQUIRED_MARGIN,
    DESTRUCTIVE_EVENT_TYPES,
    MITIGABLE_EVENT_TYPES,
    RADIATION_CATEGORIES,
    ROUTE_PRECEDENCE,
    TIER_ORDER,
    assess_radiation_verification,
    best_heritage_record,
    credited_capability,
    heritage_factor,
    normalize_category,
    radiation_design_margin,
    single_event_verdict,
)

MISSION_DOSE = 50
MISSION_LET = 60


def _record(tier="same-family", dose=110, reference="TID-2025-004"):
    return {"tier": tier, "demonstrated_dose": dose, "reference": reference}


def _event(event_type="single-event-latch-up", onset=40):
    return {"type": event_type, "onset_let": onset}


def _spec(**overrides):
    spec = {
        "category": "dose-sensitive",
        "mission_dose": MISSION_DOSE,
        "records": [_record()],
    }
    spec.update(overrides)
    return spec


class CategoryTests(unittest.TestCase):
    def test_category_normalized(self):
        self.assertEqual(normalize_category("  Dose-Sensitive "), "dose-sensitive")

    def test_every_category_recognised(self):
        for name in RADIATION_CATEGORIES:
            self.assertEqual(normalize_category(name), name)

    def test_unknown_category_refused(self):
        with self.assertRaises(ValueError):
            normalize_category("slightly-sensitive")

    def test_non_string_category_refused(self):
        with self.assertRaises(ValueError):
            normalize_category(2)


class HeritageCreditTests(unittest.TestCase):
    def test_flight_lot_credited_whole(self):
        self.assertEqual(heritage_factor("same-lot"), 1)

    def test_distant_tier_credited_least(self):
        self.assertLess(
            heritage_factor("same-technology-node"), heritage_factor("same-family")
        )

    def test_credit_never_rises_with_distance(self):
        factors = [heritage_factor(tier) for tier in TIER_ORDER]
        self.assertEqual(factors, sorted(factors, reverse=True))

    def test_every_tier_has_a_credit(self):
        self.assertEqual(set(DEFAULT_HERITAGE_CREDIT), set(TIER_ORDER))

    def test_unknown_tier_refused(self):
        with self.assertRaises(ValueError):
            heritage_factor("same-wafer-quadrant")

    def test_credit_above_one_refused(self):
        with self.assertRaises(ValueError):
            heritage_factor("same-lot", {"same-lot": 1.2})

    def test_credited_capability_applies_the_knockdown(self):
        self.assertAlmostEqual(
            float(credited_capability(100, "same-family")), 70.0, places=9
        )

    def test_credited_capability_is_exact_not_floating(self):
        self.assertEqual(credited_capability(100, "same-family"), 70)

    def test_negative_demonstrated_dose_refused(self):
        with self.assertRaises(ValueError):
            credited_capability(-10, "same-lot")

    def test_zero_demonstrated_dose_refused(self):
        with self.assertRaises(ValueError):
            credited_capability(0, "same-lot")


class MarginTests(unittest.TestCase):
    def test_margin_is_the_dose_ratio(self):
        self.assertAlmostEqual(
            float(radiation_design_margin(75, MISSION_DOSE)), 1.5, places=9
        )

    def test_margin_is_exact_at_the_bound(self):
        self.assertEqual(radiation_design_margin(75, MISSION_DOSE), DEFAULT_REQUIRED_MARGIN)

    def test_float_dose_enters_through_its_decimal_text(self):
        self.assertEqual(radiation_design_margin(75.0, 50.0), radiation_design_margin(75, 50))

    def test_class_two_required_margin_is_one_and_a_half(self):
        self.assertEqual(DEFAULT_REQUIRED_MARGIN * 2, 3)

    def test_zero_mission_dose_refused(self):
        with self.assertRaises(ValueError):
            radiation_design_margin(75, 0)

    def test_non_numeric_dose_refused(self):
        with self.assertRaises(ValueError):
            radiation_design_margin("75 krad", MISSION_DOSE)


class BestRecordTests(unittest.TestCase):
    def test_no_records_gives_nothing(self):
        self.assertIsNone(best_heritage_record([], MISSION_DOSE))

    def test_highest_credited_dose_wins(self):
        best = best_heritage_record(
            [_record("same-technology-node", 100, "A"), _record("same-family", 110, "B")],
            MISSION_DOSE,
        )
        self.assertEqual(best["reference"], "B")

    def test_tie_breaks_towards_the_closer_tier(self):
        best = best_heritage_record(
            [_record("same-technology-node", 140, "A"), _record("same-family", 100, "B")],
            MISSION_DOSE,
        )
        self.assertEqual(best["reference"], "B")
        self.assertEqual(best["tier"], "same-family")

    def test_a_bigger_dose_at_a_worse_tier_can_still_win(self):
        best = best_heritage_record(
            [_record("same-technology-node", 200, "A"), _record("same-family", 100, "B")],
            MISSION_DOSE,
        )
        self.assertEqual(best["reference"], "A")

    def test_record_without_a_tier_refused(self):
        with self.assertRaises(ValueError):
            best_heritage_record([{"demonstrated_dose": 100}], MISSION_DOSE)

    def test_record_with_an_unknown_tier_refused(self):
        with self.assertRaises(ValueError):
            best_heritage_record([_record("same-fab", 100)], MISSION_DOSE)

    def test_non_mapping_record_refused(self):
        with self.assertRaises(ValueError):
            best_heritage_record(["TID-2025-004"], MISSION_DOSE)

    def test_non_sequence_records_refused(self):
        with self.assertRaises(ValueError):
            best_heritage_record("TID-2025-004", MISSION_DOSE)


class SingleEventTests(unittest.TestCase):
    def test_onset_above_the_requirement_raises_nothing(self):
        verdict = single_event_verdict([_event(onset=75)], MISSION_LET)
        self.assertEqual(verdict["veto"], [])
        self.assertEqual(verdict["advisory"], [])

    def test_onset_exactly_at_the_requirement_raises_nothing(self):
        verdict = single_event_verdict([_event(onset=MISSION_LET)], MISSION_LET)
        self.assertEqual(verdict["veto"], [])

    def test_destructive_event_below_the_requirement_vetoes(self):
        verdict = single_event_verdict([_event()], MISSION_LET)
        self.assertEqual(len(verdict["veto"]), 1)
        self.assertIn("single-event-latch-up", verdict["veto"][0])

    def test_verified_mitigation_credits_latch_up(self):
        verdict = single_event_verdict(
            [_event()],
            MISSION_LET,
            [{"event_type": "single-event-latch-up", "verified": True}],
        )
        self.assertEqual(verdict["veto"], [])
        self.assertIn("verified mitigation", verdict["advisory"][0])

    def test_unverified_mitigation_credits_nothing(self):
        verdict = single_event_verdict(
            [_event()],
            MISSION_LET,
            [{"event_type": "single-event-latch-up", "verified": False}],
        )
        self.assertEqual(len(verdict["veto"]), 1)

    def test_mitigation_cannot_be_credited_against_burnout(self):
        verdict = single_event_verdict(
            [_event("single-event-burnout")],
            MISSION_LET,
            [{"event_type": "single-event-burnout", "verified": True}],
        )
        self.assertEqual(len(verdict["veto"]), 1)

    def test_gate_rupture_below_the_requirement_vetoes(self):
        verdict = single_event_verdict([_event("single-event-gate-rupture")], MISSION_LET)
        self.assertEqual(len(verdict["veto"]), 1)

    def test_non_destructive_event_is_advisory_not_a_veto(self):
        verdict = single_event_verdict([_event("single-event-upset", 5)], MISSION_LET)
        self.assertEqual(verdict["veto"], [])
        self.assertIn("rate is a design question", verdict["advisory"][0])

    def test_mitigable_set_is_narrower_than_the_destructive_set(self):
        self.assertTrue(MITIGABLE_EVENT_TYPES < DESTRUCTIVE_EVENT_TYPES)

    def test_event_without_an_onset_refused(self):
        with self.assertRaises(ValueError):
            single_event_verdict([{"type": "single-event-latch-up"}], MISSION_LET)

    def test_negative_onset_refused(self):
        with self.assertRaises(ValueError):
            single_event_verdict([_event(onset=-1)], MISSION_LET)

    def test_non_boolean_verified_flag_refused(self):
        with self.assertRaises(ValueError):
            single_event_verdict(
                [_event()],
                MISSION_LET,
                [{"event_type": "single-event-latch-up", "verified": "yes"}],
            )

    def test_non_sequence_events_refused(self):
        with self.assertRaises(ValueError):
            single_event_verdict("single-event-latch-up", MISSION_LET)


class VerificationRouteTests(unittest.TestCase):
    def test_part_not_graded_sensitive_needs_no_test(self):
        result = assess_radiation_verification({"category": "not-sensitive"})
        self.assertEqual(result["route"], "no-verification-required")
        self.assertFalse(result["dose"]["checked"])

    def test_sufficient_heritage_is_accepted(self):
        result = assess_radiation_verification(_spec())
        self.assertEqual(result["route"], "accept-on-heritage")
        self.assertAlmostEqual(result["dose"]["margin"], 1.54, places=9)
        self.assertTrue(result["dose"]["margin_met"])

    def test_margin_landing_exactly_on_the_bound_is_accepted(self):
        result = assess_radiation_verification(
            _spec(records=[_record("same-lot", 75, "TID-FLIGHT")])
        )
        self.assertAlmostEqual(result["dose"]["margin"], 1.5, places=9)
        self.assertEqual(result["route"], "accept-on-heritage")

    def test_thin_family_heritage_sends_the_flight_lot_for_test(self):
        result = assess_radiation_verification(
            _spec(records=[_record("same-family", 100)])
        )
        self.assertEqual(result["route"], "irradiate-flight-lot")
        self.assertAlmostEqual(result["dose"]["margin"], 1.4, places=9)

    def test_no_record_sends_the_flight_lot_for_test(self):
        result = assess_radiation_verification(_spec(records=[]))
        self.assertEqual(result["route"], "irradiate-flight-lot")
        self.assertIsNone(result["dose"]["best_record"])

    def test_flight_lot_short_of_the_margin_rejects_the_part(self):
        result = assess_radiation_verification(
            _spec(records=[_record("same-lot", 70, "TID-FLIGHT")])
        )
        self.assertEqual(result["route"], "reject-part")
        self.assertTrue(any("no further irradiation" in f for f in result["findings"]))

    def test_diffusion_lot_credit_can_carry_the_part(self):
        result = assess_radiation_verification(
            _spec(records=[_record("same-diffusion-lot", 100)])
        )
        self.assertEqual(result["route"], "accept-on-heritage")
        self.assertAlmostEqual(result["dose"]["margin"], 1.8, places=9)

    def test_required_margin_may_be_raised_by_the_project(self):
        result = assess_radiation_verification(_spec(required_margin=2))
        self.assertEqual(result["route"], "irradiate-flight-lot")

    def test_event_sensitive_part_without_data_owes_a_test(self):
        result = assess_radiation_verification(
            {"category": "event-sensitive", "mission_let": MISSION_LET}
        )
        self.assertEqual(result["route"], "irradiate-flight-lot")

    def test_event_sensitive_part_with_adequate_onset_passes(self):
        result = assess_radiation_verification(
            {
                "category": "event-sensitive",
                "mission_let": MISSION_LET,
                "events": [_event(onset=75)],
            }
        )
        self.assertEqual(result["route"], "no-verification-required")
        self.assertTrue(result["events"]["checked"])

    def test_destructive_event_rejects_despite_a_wide_dose_margin(self):
        result = assess_radiation_verification(
            _spec(
                category="dose-and-event-sensitive",
                records=[_record("same-lot", 5000, "TID-FLIGHT")],
                mission_let=MISSION_LET,
                events=[_event()],
            )
        )
        self.assertEqual(result["route"], "reject-part")
        self.assertTrue(result["dose"]["margin_met"])

    def test_both_checks_clean_accepts_on_heritage(self):
        result = assess_radiation_verification(
            _spec(
                category="dose-and-event-sensitive",
                mission_let=MISSION_LET,
                events=[_event(onset=75)],
            )
        )
        self.assertEqual(result["route"], "accept-on-heritage")

    def test_dose_sensitive_part_without_a_mission_dose_refused(self):
        with self.assertRaises(ValueError):
            assess_radiation_verification({"category": "dose-sensitive"})

    def test_event_sensitive_part_without_a_mission_let_refused(self):
        with self.assertRaises(ValueError):
            assess_radiation_verification({"category": "event-sensitive"})

    def test_missing_category_refused(self):
        with self.assertRaises(ValueError):
            assess_radiation_verification({"mission_dose": MISSION_DOSE})

    def test_non_mapping_spec_refused(self):
        with self.assertRaises(ValueError):
            assess_radiation_verification(["category"])

    def test_route_precedence_runs_worst_first(self):
        self.assertEqual(ROUTE_PRECEDENCE[0], "reject-part")
        self.assertEqual(ROUTE_PRECEDENCE[-1], "no-verification-required")


if __name__ == "__main__":
    unittest.main()
