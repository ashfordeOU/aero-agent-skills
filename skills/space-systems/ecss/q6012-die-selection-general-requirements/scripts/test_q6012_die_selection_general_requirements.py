"""Contract tests for the clause 5.1 baseline die-selection logic."""

import unittest

from q6012_die_selection_general_requirements_logic import (
    CATEGORY_ORDER,
    MARGIN_TOLERANCE,
    REFERENCE_TEMPERATURE_MARGIN_C,
    assess_candidate,
    assess_die_baseline_selection,
    band_coverage_fraction,
    baseline_findings,
    categorize_candidate,
    coverage_score,
    dose_headroom,
    life_headroom,
    rank_candidates,
    temperature_margins_c,
    validate_application,
    validate_candidate,
)

APPLICATION = {
    "band_ghz": (13.75, 14.5),
    "case_temperature_range_c": (-30.0, 85.0),
    "mission_tid_krad": 30.0,
    "required_life_hours": 131400.0,
    "assembly_route": "die-attach-and-wire-bond",
}

CONTROLLED = ["gaas-phemt-0p15", "gan-hemt-0p25", "sige-bicmos-0p18"]

GOOD_DIE = {
    "part_id": "MMIC-A",
    "process_id": "gaas-phemt-0p15",
    "supply_route": "foundry-direct",
    "band_ghz": (12.0, 16.0),
    "temperature_range_c": (-55.0, 125.0),
    "tid_capability_krad": 100.0,
    "rated_life_hours": 400000.0,
    "evaluation_status": "qualified",
}


def die(**overrides):
    record = dict(GOOD_DIE)
    record.update(overrides)
    return record


def codes(findings):
    return sorted(f["code"] for f in findings)


class ValidateApplicationTests(unittest.TestCase):
    def test_normalises_the_band_to_floats(self):
        app = validate_application(APPLICATION)
        self.assertEqual(app["band_ghz"], (13.75, 14.5))

    def test_missing_key_rejected(self):
        broken = dict(APPLICATION)
        del broken["mission_tid_krad"]
        with self.assertRaises(ValueError):
            validate_application(broken)

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_application(dict(APPLICATION, band_ghz=(14.5, 13.75)))

    def test_non_positive_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_application(dict(APPLICATION, band_ghz=(0.0, 14.5)))

    def test_unknown_assembly_route_rejected(self):
        with self.assertRaises(ValueError):
            validate_application(dict(APPLICATION, assembly_route="glued-on"))

    def test_zero_mission_dose_rejected(self):
        with self.assertRaises(ValueError):
            validate_application(dict(APPLICATION, mission_tid_krad=0.0))

    def test_non_mapping_application_rejected(self):
        with self.assertRaises(ValueError):
            validate_application(["band_ghz"])


class ValidateCandidateTests(unittest.TestCase):
    def test_absent_optional_data_stays_none(self):
        record = validate_candidate({
            "part_id": "X", "process_id": "p", "supply_route": "foundry-direct",
        })
        self.assertIsNone(record["band_ghz"])
        self.assertIsNone(record["tid_capability_krad"])

    def test_broker_route_defaults_to_untraceable(self):
        record = validate_candidate(die(supply_route="broker"))
        self.assertFalse(record["traceable_to_manufacturer"])

    def test_foundry_route_defaults_to_traceable(self):
        self.assertTrue(validate_candidate(GOOD_DIE)["traceable_to_manufacturer"])

    def test_blank_part_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate(die(part_id="   "))

    def test_unknown_supply_route_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate(die(supply_route="ebay"))

    def test_unknown_evaluation_status_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate(die(evaluation_status="probably-fine"))

    def test_boolean_dose_capability_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate(die(tid_capability_krad=True))

    def test_empty_assembly_route_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate(die(assembly_routes=[]))


class CoverageArithmeticTests(unittest.TestCase):
    def test_fully_enclosing_band_covers_everything(self):
        self.assertAlmostEqual(
            band_coverage_fraction((12.0, 16.0), (13.75, 14.5)), 1.0, places=9
        )

    def test_exactly_matching_band_covers_everything(self):
        self.assertAlmostEqual(
            band_coverage_fraction((13.75, 14.5), (13.75, 14.5)), 1.0, places=9
        )

    def test_half_covered_band(self):
        self.assertAlmostEqual(
            band_coverage_fraction((13.75, 14.125), (13.75, 14.5)), 0.5, places=9
        )

    def test_disjoint_band_covers_nothing(self):
        self.assertAlmostEqual(
            band_coverage_fraction((8.0, 12.0), (13.75, 14.5)), 0.0, places=9
        )

    def test_single_frequency_application_inside_die_band(self):
        self.assertAlmostEqual(
            band_coverage_fraction((12.0, 16.0), (14.0, 14.0)), 1.0, places=9
        )

    def test_single_frequency_application_outside_die_band(self):
        self.assertAlmostEqual(
            band_coverage_fraction((12.0, 13.0), (14.0, 14.0)), 0.0, places=9
        )

    def test_temperature_margins_are_signed(self):
        cold, hot = temperature_margins_c((-55.0, 125.0), (-30.0, 85.0))
        self.assertAlmostEqual(cold, 25.0, places=9)
        self.assertAlmostEqual(hot, 40.0, places=9)

    def test_temperature_margin_negative_when_die_is_narrower(self):
        cold, hot = temperature_margins_c((-20.0, 70.0), (-30.0, 85.0))
        self.assertAlmostEqual(cold, -10.0, places=9)
        self.assertAlmostEqual(hot, -15.0, places=9)

    def test_dose_headroom_is_a_ratio(self):
        self.assertAlmostEqual(dose_headroom(100.0, 30.0), 100.0 / 30.0, places=9)

    def test_life_headroom_is_a_ratio(self):
        self.assertAlmostEqual(life_headroom(400000.0, 100000.0), 4.0, places=9)

    def test_zero_dose_capability_rejected(self):
        with self.assertRaises(ValueError):
            dose_headroom(0.0, 30.0)

    def test_malformed_band_pair_rejected(self):
        with self.assertRaises(ValueError):
            band_coverage_fraction((12.0,), (13.75, 14.5))


class BaselineFindingTests(unittest.TestCase):
    def test_compliant_die_raises_nothing(self):
        self.assertEqual(baseline_findings(GOOD_DIE, APPLICATION, CONTROLLED), [])

    def test_uncontrolled_process_is_an_exclusion(self):
        found = baseline_findings(die(process_id="mystery-0p5"), APPLICATION, CONTROLLED)
        self.assertEqual(codes(found), ["process-not-controlled"])
        self.assertEqual(found[0]["severity"], "exclusion")

    def test_untraceable_broker_route_is_an_exclusion(self):
        found = baseline_findings(die(supply_route="broker"), APPLICATION, CONTROLLED)
        self.assertIn("supply-route-not-traceable", codes(found))

    def test_traceable_broker_route_is_only_an_action(self):
        found = baseline_findings(
            die(supply_route="broker", traceable_to_manufacturer=True),
            APPLICATION, CONTROLLED,
        )
        self.assertEqual(codes(found), ["supply-route-needs-verification"])
        self.assertEqual(found[0]["severity"], "action")

    def test_absent_band_is_an_action_not_an_exclusion(self):
        found = baseline_findings(die(band_ghz=None), APPLICATION, CONTROLLED)
        self.assertEqual(codes(found), ["band-data-absent"])
        self.assertEqual(found[0]["severity"], "action")

    def test_short_band_is_an_exclusion(self):
        found = baseline_findings(die(band_ghz=(13.75, 14.2)), APPLICATION, CONTROLLED)
        self.assertEqual(codes(found), ["band-not-covered"])
        self.assertEqual(found[0]["severity"], "exclusion")

    def test_exactly_covering_band_is_accepted(self):
        found = baseline_findings(die(band_ghz=(13.75, 14.5)), APPLICATION, CONTROLLED)
        self.assertEqual(found, [])

    def test_exactly_enclosing_temperature_range_is_accepted(self):
        found = baseline_findings(
            die(temperature_range_c=(-30.0, 85.0)), APPLICATION, CONTROLLED
        )
        self.assertEqual(found, [])

    def test_narrow_temperature_range_is_an_exclusion(self):
        found = baseline_findings(
            die(temperature_range_c=(-20.0, 70.0)), APPLICATION, CONTROLLED
        )
        self.assertEqual(codes(found), ["temperature-not-enclosed"])

    def test_dose_headroom_exactly_at_the_required_factor_is_accepted(self):
        found = baseline_findings(
            die(tid_capability_krad=60.0), APPLICATION, CONTROLLED, required_dose_factor=2.0
        )
        self.assertEqual(found, [])

    def test_dose_headroom_below_the_required_factor_is_an_exclusion(self):
        found = baseline_findings(
            die(tid_capability_krad=45.0), APPLICATION, CONTROLLED, required_dose_factor=2.0
        )
        self.assertEqual(codes(found), ["dose-headroom-short"])

    def test_short_rated_life_is_an_exclusion(self):
        found = baseline_findings(die(rated_life_hours=50000.0), APPLICATION, CONTROLLED)
        self.assertEqual(codes(found), ["life-headroom-short"])

    def test_unevaluated_status_owes_an_evaluation_programme(self):
        found = baseline_findings(die(evaluation_status="unevaluated"), APPLICATION, CONTROLLED)
        self.assertEqual(codes(found), ["evaluation-programme-owed"])
        self.assertEqual(found[0]["severity"], "action")

    def test_absent_evaluation_status_is_an_action(self):
        found = baseline_findings(die(evaluation_status=None), APPLICATION, CONTROLLED)
        self.assertEqual(codes(found), ["evaluation-status-absent"])

    def test_unsupported_assembly_route_is_an_exclusion(self):
        found = baseline_findings(die(assembly_routes=["flip-chip"]), APPLICATION, CONTROLLED)
        self.assertEqual(codes(found), ["assembly-route-unsupported"])

    def test_several_defects_are_all_reported(self):
        found = baseline_findings(
            die(process_id="mystery-0p5", band_ghz=None, rated_life_hours=10.0),
            APPLICATION, CONTROLLED,
        )
        self.assertEqual(
            codes(found),
            ["band-data-absent", "life-headroom-short", "process-not-controlled"],
        )

    def test_empty_controlled_process_list_rejected(self):
        with self.assertRaises(ValueError):
            baseline_findings(GOOD_DIE, APPLICATION, [])

    def test_non_positive_dose_factor_rejected(self):
        with self.assertRaises(ValueError):
            baseline_findings(GOOD_DIE, APPLICATION, CONTROLLED, required_dose_factor=0.0)


class CategorizationTests(unittest.TestCase):
    def test_no_findings_is_eligible(self):
        self.assertEqual(categorize_candidate([]), "eligible")

    def test_action_only_is_eligible_with_actions(self):
        self.assertEqual(
            categorize_candidate([{"code": "x", "severity": "action", "detail": ""}]),
            "eligible-with-actions",
        )

    def test_any_exclusion_dominates(self):
        self.assertEqual(
            categorize_candidate([
                {"code": "x", "severity": "action", "detail": ""},
                {"code": "y", "severity": "exclusion", "detail": ""},
            ]),
            "not-eligible",
        )

    def test_malformed_finding_rejected(self):
        with self.assertRaises(ValueError):
            categorize_candidate([{"code": "x"}])

    def test_every_category_name_is_ordered(self):
        self.assertEqual(len(CATEGORY_ORDER), 3)


class CoverageScoreTests(unittest.TestCase):
    def test_generous_die_scores_high(self):
        score = coverage_score(GOOD_DIE, APPLICATION)
        self.assertAlmostEqual(score, 1.0, places=9)

    def test_absent_data_contributes_nothing(self):
        score = coverage_score(
            die(band_ghz=None, tid_capability_krad=None), APPLICATION
        )
        self.assertAlmostEqual(score, 0.5, places=9)

    def test_thermal_component_saturates_at_the_reference_margin(self):
        tight = coverage_score(
            die(temperature_range_c=(-30.0 - REFERENCE_TEMPERATURE_MARGIN_C,
                                     85.0 + REFERENCE_TEMPERATURE_MARGIN_C)),
            APPLICATION,
        )
        self.assertAlmostEqual(tight, 1.0, places=9)

    def test_exactly_enclosing_range_gives_no_thermal_credit(self):
        score = coverage_score(die(temperature_range_c=(-30.0, 85.0)), APPLICATION)
        self.assertAlmostEqual(score, 0.75, places=9)

    def test_score_never_exceeds_one(self):
        score = coverage_score(die(tid_capability_krad=1.0e6), APPLICATION)
        self.assertAlmostEqual(score, 1.0, places=9)


class RankingTests(unittest.TestCase):
    def test_eligible_outranks_action_and_excluded(self):
        records = [
            {"part_id": "C", "category": "not-eligible", "coverage_score": 1.0},
            {"part_id": "B", "category": "eligible-with-actions", "coverage_score": 1.0},
            {"part_id": "A", "category": "eligible", "coverage_score": 0.1},
        ]
        self.assertEqual([r["part_id"] for r in rank_candidates(records)], ["A", "B", "C"])

    def test_higher_score_wins_inside_a_category(self):
        records = [
            {"part_id": "LOW", "category": "eligible", "coverage_score": 0.4},
            {"part_id": "HIGH", "category": "eligible", "coverage_score": 0.9},
        ]
        self.assertEqual([r["part_id"] for r in rank_candidates(records)], ["HIGH", "LOW"])

    def test_tie_is_broken_by_part_id(self):
        records = [
            {"part_id": "ZZ", "category": "eligible", "coverage_score": 0.5},
            {"part_id": "AA", "category": "eligible", "coverage_score": 0.5},
        ]
        self.assertEqual([r["part_id"] for r in rank_candidates(records)], ["AA", "ZZ"])

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            rank_candidates([{"part_id": "A", "category": "maybe", "coverage_score": 1.0}])

    def test_missing_score_rejected(self):
        with self.assertRaises(ValueError):
            rank_candidates([{"part_id": "A", "category": "eligible"}])


class AssessmentTests(unittest.TestCase):
    def _spec(self, candidates=None, **overrides):
        spec = {
            "application": APPLICATION,
            "candidates": candidates if candidates is not None else [GOOD_DIE],
            "controlled_processes": CONTROLLED,
        }
        spec.update(overrides)
        return spec

    def test_single_clean_candidate_is_recommended(self):
        result = assess_die_baseline_selection(self._spec())
        self.assertEqual(result["recommended"]["part_id"], "MMIC-A")
        self.assertTrue(result["clean"])

    def test_counts_cover_every_category(self):
        result = assess_die_baseline_selection(self._spec(candidates=[
            GOOD_DIE,
            die(part_id="MMIC-B", evaluation_status="unevaluated"),
            die(part_id="MMIC-C", process_id="unknown-process"),
        ]))
        self.assertEqual(result["counts"]["eligible"], 1)
        self.assertEqual(result["counts"]["eligible-with-actions"], 1)
        self.assertEqual(result["counts"]["not-eligible"], 1)

    def test_shortlist_drops_the_excluded_candidate(self):
        result = assess_die_baseline_selection(self._spec(candidates=[
            GOOD_DIE, die(part_id="MMIC-C", process_id="unknown-process"),
        ]))
        self.assertEqual([r["part_id"] for r in result["shortlist"]], ["MMIC-A"])

    def test_open_actions_are_counted_on_the_shortlist(self):
        result = assess_die_baseline_selection(self._spec(candidates=[
            die(part_id="MMIC-B", evaluation_status="unevaluated", band_ghz=None),
        ]))
        self.assertEqual(result["open_actions"], 2)
        self.assertFalse(result["clean"])

    def test_all_excluded_gives_no_recommendation(self):
        result = assess_die_baseline_selection(self._spec(candidates=[
            die(part_id="MMIC-C", process_id="unknown-process"),
        ]))
        self.assertIsNone(result["recommended"])
        self.assertFalse(result["clean"])

    def test_action_only_candidate_is_never_recommended(self):
        result = assess_die_baseline_selection(self._spec(candidates=[
            die(part_id="MMIC-B", evaluation_status="unevaluated"),
        ]))
        self.assertIsNone(result["recommended"])
        self.assertEqual(len(result["shortlist"]), 1)

    def test_duplicate_part_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_die_baseline_selection(self._spec(candidates=[GOOD_DIE, GOOD_DIE]))

    def test_empty_candidate_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_die_baseline_selection(self._spec(candidates=[]))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["controlled_processes"]
        with self.assertRaises(ValueError):
            assess_die_baseline_selection(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_die_baseline_selection(["application"])

    def test_dose_factor_is_carried_into_every_candidate(self):
        result = assess_die_baseline_selection(
            self._spec(required_dose_factor=4.0)
        )
        self.assertEqual(result["counts"]["not-eligible"], 1)

    def test_record_splits_exclusions_from_actions(self):
        record = assess_candidate(
            die(process_id="unknown-process", evaluation_status="unevaluated"),
            APPLICATION, CONTROLLED,
        )
        self.assertEqual(len(record["exclusions"]), 1)
        self.assertEqual(len(record["actions"]), 1)

    def test_tolerance_is_small_enough_to_be_a_representation_guard(self):
        self.assertAlmostEqual(MARGIN_TOLERANCE, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main()
