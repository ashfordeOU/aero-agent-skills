#!/usr/bin/env python3
"""Contract test for the IR contamination method selection (offline)."""

import copy
import unittest

from q7005_method_selection_logic import (
    ACCESS_CLASSES,
    ACCESS_ENCLOSED,
    ACCESS_LINE_OF_SIGHT,
    ACCESS_OPEN,
    CONTACT_METHODS,
    DEFAULT_SELECTION_POLICY,
    DEFAULT_SOLVENT_COMPATIBILITY,
    DIRECT_CONTACT_PROBE,
    DIRECT_STANDOFF,
    INDIRECT_RINSE,
    INDIRECT_WIPE,
    METHODS,
    SOLVENT_METHODS,
    access_gate,
    evaluate_candidate,
    rank_candidates,
    select_method,
    sensitivity_margin,
    solvent_gate,
    substrate_gate,
    validate_selection_policy,
)

LIMITS = {
    DIRECT_CONTACT_PROBE: 0.10,
    DIRECT_STANDOFF: 0.40,
    INDIRECT_WIPE: 0.05,
    INDIRECT_RINSE: 0.08,
}

BASE_CASE = {
    "access_class": ACCESS_OPEN,
    "solvent_tolerant": True,
    "contact_permitted": True,
    "contaminant_type": "hydrocarbon-oil",
    "solvent": "hexane",
    "required_level_ug_cm2": 1.0,
    "detection_limits_ug_cm2": LIMITS,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_selection_policy(DEFAULT_SELECTION_POLICY),
            DEFAULT_SELECTION_POLICY,
        )

    def test_a_recovery_floor_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_SELECTION_POLICY)
        broken["min_recovery_fraction"] = 1.5
        with self.assertRaises(ValueError):
            validate_selection_policy(broken)

    def test_a_fragile_margin_below_the_admissibility_floor_rejected(self):
        broken = copy.deepcopy(DEFAULT_SELECTION_POLICY)
        broken["fragile_margin"] = -1.0
        with self.assertRaises(ValueError):
            validate_selection_policy(broken)

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_selection_policy(0.6)


class AccessGateTests(unittest.TestCase):
    def test_open_access_admits_every_method(self):
        for method in METHODS:
            self.assertTrue(access_gate(method, ACCESS_OPEN)["passed"], method)

    def test_a_sight_line_alone_admits_only_the_standoff_read(self):
        self.assertTrue(access_gate(DIRECT_STANDOFF, ACCESS_LINE_OF_SIGHT)["passed"])
        self.assertFalse(access_gate(INDIRECT_WIPE, ACCESS_LINE_OF_SIGHT)["passed"])

    def test_an_enclosed_volume_admits_only_the_rinse(self):
        self.assertTrue(access_gate(INDIRECT_RINSE, ACCESS_ENCLOSED)["passed"])
        self.assertFalse(access_gate(DIRECT_STANDOFF, ACCESS_ENCLOSED)["passed"])

    def test_a_blocked_access_gate_carries_a_reason(self):
        gate = access_gate(INDIRECT_WIPE, ACCESS_ENCLOSED)
        self.assertIn("access is enclosed", gate["reason"])

    def test_every_access_class_is_known(self):
        self.assertEqual(len(set(ACCESS_CLASSES)), len(ACCESS_CLASSES))

    def test_an_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            access_gate("sniff-test", ACCESS_OPEN)

    def test_an_unknown_access_class_rejected(self):
        with self.assertRaises(ValueError):
            access_gate(DIRECT_STANDOFF, "awkward")


class SubstrateGateTests(unittest.TestCase):
    def test_a_solvent_intolerant_substrate_blocks_the_wet_methods(self):
        for method in SOLVENT_METHODS:
            self.assertFalse(
                substrate_gate(method, False, True)["passed"], method
            )

    def test_a_no_touch_surface_blocks_the_contact_methods(self):
        for method in CONTACT_METHODS:
            self.assertFalse(
                substrate_gate(method, True, False)["passed"], method
            )

    def test_the_standoff_read_survives_both_restrictions(self):
        self.assertTrue(substrate_gate(DIRECT_STANDOFF, False, False)["passed"])

    def test_a_blocked_substrate_gate_carries_a_reason(self):
        gate = substrate_gate(INDIRECT_RINSE, False, True)
        self.assertIn("does not tolerate solvent", gate["reason"])

    def test_a_non_boolean_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            substrate_gate(INDIRECT_WIPE, "maybe", True)


class SolventGateTests(unittest.TestCase):
    def test_a_dry_method_passes_the_solvent_gate_unconditionally(self):
        gate = solvent_gate(DIRECT_STANDOFF, "silicone", "isopropanol")
        self.assertTrue(gate["passed"])
        self.assertIsNone(gate["recovery_fraction"])

    def test_a_compatible_pairing_passes_and_reports_its_recovery(self):
        gate = solvent_gate(INDIRECT_WIPE, "silicone", "hexane")
        self.assertTrue(gate["passed"])
        self.assertAlmostEqual(gate["recovery_fraction"], 0.9, places=9)

    def test_an_incompatible_pairing_is_blocked(self):
        gate = solvent_gate(INDIRECT_WIPE, "silicone", "isopropanol")
        self.assertFalse(gate["passed"])
        self.assertIn("recovers only", gate["reason"])

    def test_a_recovery_exactly_on_the_floor_passes(self):
        table = {"test-residue": {"probe-solvent": DEFAULT_SELECTION_POLICY["min_recovery_fraction"]}}
        gate = solvent_gate(INDIRECT_WIPE, "test-residue", "probe-solvent", table)
        self.assertTrue(gate["passed"])

    def test_an_unknown_contaminant_type_is_refused_not_guessed(self):
        with self.assertRaises(ValueError):
            solvent_gate(INDIRECT_WIPE, "unknown-goo", "hexane")

    def test_an_unknown_solvent_is_refused_not_guessed(self):
        with self.assertRaises(ValueError):
            solvent_gate(INDIRECT_WIPE, "silicone", "water")

    def test_every_tabulated_recovery_is_a_fraction(self):
        for contaminant, table in DEFAULT_SOLVENT_COMPATIBILITY.items():
            for solvent, recovery in table.items():
                self.assertGreater(recovery, 0.0, (contaminant, solvent))
                self.assertLessEqual(recovery, 1.0, (contaminant, solvent))


class MarginTests(unittest.TestCase):
    def test_a_limit_ten_times_under_the_requirement_gives_nine(self):
        self.assertAlmostEqual(sensitivity_margin(0.1, 1.0), 9.0, places=9)

    def test_a_limit_exactly_on_the_requirement_gives_zero(self):
        self.assertAlmostEqual(sensitivity_margin(1.0, 1.0), 0.0, places=9)

    def test_a_limit_above_the_requirement_is_negative(self):
        self.assertLess(sensitivity_margin(2.0, 1.0), 0.0)

    def test_a_zero_detection_limit_rejected(self):
        with self.assertRaises(ValueError):
            sensitivity_margin(0.0, 1.0)

    def test_a_non_numeric_requirement_rejected(self):
        with self.assertRaises(ValueError):
            sensitivity_margin(0.1, "visibly clean")


class CandidateTests(unittest.TestCase):
    def test_an_unblocked_candidate_is_admissible(self):
        candidate = evaluate_candidate(INDIRECT_WIPE, BASE_CASE)
        self.assertTrue(candidate["admissible"])
        self.assertEqual(candidate["blocked_by"], ())

    def test_a_candidate_blocked_on_access_names_that_gate(self):
        candidate = evaluate_candidate(
            INDIRECT_WIPE, _case(BASE_CASE, access_class=ACCESS_ENCLOSED)
        )
        self.assertIn("access", candidate["blocked_by"])
        self.assertFalse(candidate["admissible"])

    def test_a_candidate_can_be_blocked_on_two_gates_at_once(self):
        candidate = evaluate_candidate(
            INDIRECT_WIPE,
            _case(BASE_CASE, access_class=ACCESS_ENCLOSED, solvent_tolerant=False),
        )
        self.assertEqual(len(candidate["blocked_by"]), 2)

    def test_a_candidate_failing_only_sensitivity_names_that_gate(self):
        candidate = evaluate_candidate(
            DIRECT_STANDOFF, _case(BASE_CASE, required_level_ug_cm2=0.01)
        )
        self.assertEqual(candidate["blocked_by"], ("sensitivity",))

    def test_a_margin_exactly_on_the_floor_stays_admissible(self):
        case = _case(
            BASE_CASE,
            required_level_ug_cm2=LIMITS[DIRECT_STANDOFF],
            access_class=ACCESS_LINE_OF_SIGHT,
        )
        candidate = evaluate_candidate(DIRECT_STANDOFF, case)
        self.assertTrue(candidate["admissible"])

    def test_a_thin_margin_is_admissible_and_flagged_fragile(self):
        case = _case(
            BASE_CASE,
            required_level_ug_cm2=LIMITS[DIRECT_STANDOFF],
            access_class=ACCESS_LINE_OF_SIGHT,
        )
        candidate = evaluate_candidate(DIRECT_STANDOFF, case)
        self.assertTrue(candidate["fragile"])

    def test_a_generous_margin_is_not_fragile(self):
        candidate = evaluate_candidate(INDIRECT_WIPE, BASE_CASE)
        self.assertFalse(candidate["fragile"])

    def test_a_case_with_no_limit_for_the_method_rejected(self):
        case = _case(BASE_CASE, detection_limits_ug_cm2={INDIRECT_RINSE: 0.08})
        with self.assertRaises(ValueError):
            evaluate_candidate(INDIRECT_WIPE, case)

    def test_a_non_mapping_limit_table_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_candidate(INDIRECT_WIPE, _case(BASE_CASE, detection_limits_ug_cm2=0.05))


class RankingTests(unittest.TestCase):
    def test_the_most_sensitive_admissible_method_ranks_first(self):
        ranking = rank_candidates(BASE_CASE)
        self.assertEqual(ranking["admissible"][0]["method"], INDIRECT_WIPE)

    def test_the_admissible_list_is_ordered_by_falling_margin(self):
        margins = [c["sensitivity_margin"] for c in rank_candidates(BASE_CASE)["admissible"]]
        self.assertEqual(margins, sorted(margins, reverse=True))

    def test_the_rejected_list_is_ordered_by_name(self):
        ranking = rank_candidates(
            _case(BASE_CASE, access_class=ACCESS_LINE_OF_SIGHT)
        )
        names = [c["method"] for c in ranking["rejected"]]
        self.assertEqual(names, sorted(names))

    def test_a_case_declaring_no_known_method_rejected(self):
        with self.assertRaises(ValueError):
            rank_candidates(_case(BASE_CASE, detection_limits_ug_cm2={}))


class SelectionTests(unittest.TestCase):
    def test_the_base_case_selects_a_method(self):
        result = select_method(BASE_CASE)
        self.assertTrue(result["selected"])
        self.assertEqual(result["retained"]["method"], INDIRECT_WIPE)

    def test_a_sight_line_only_configuration_falls_to_the_standoff_read(self):
        result = select_method(_case(BASE_CASE, access_class=ACCESS_LINE_OF_SIGHT))
        self.assertEqual(result["retained"]["method"], DIRECT_STANDOFF)

    def test_a_no_touch_solvent_intolerant_surface_still_has_one_method(self):
        result = select_method(
            _case(BASE_CASE, solvent_tolerant=False, contact_permitted=False)
        )
        self.assertEqual(result["retained"]["method"], DIRECT_STANDOFF)

    def test_an_enclosed_no_solvent_volume_selects_nothing(self):
        result = select_method(
            _case(BASE_CASE, access_class=ACCESS_ENCLOSED, solvent_tolerant=False)
        )
        self.assertFalse(result["selected"])
        self.assertTrue(any("no method survives" in f for f in result["findings"]))

    def test_every_rejection_appears_in_the_findings(self):
        result = select_method(_case(BASE_CASE, access_class=ACCESS_ENCLOSED))
        for candidate in result["ranking"]["rejected"]:
            self.assertTrue(
                any(candidate["method"] in f for f in result["findings"]),
                candidate["method"],
            )

    def test_a_fragile_retained_method_is_a_finding(self):
        case = _case(
            BASE_CASE,
            access_class=ACCESS_LINE_OF_SIGHT,
            required_level_ug_cm2=LIMITS[DIRECT_STANDOFF],
        )
        result = select_method(case)
        self.assertTrue(any("clears the requirement by only" in f for f in result["findings"]))

    def test_a_wet_retained_method_carries_the_recovery_duty(self):
        result = select_method(BASE_CASE)
        self.assertTrue(any("recovery fraction" in d for d in result["duties"]))

    def test_every_selection_carries_the_gate_recording_duty(self):
        result = select_method(BASE_CASE)
        self.assertTrue(any("gate that excluded" in d for d in result["duties"]))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            select_method("wipe it")


if __name__ == "__main__":
    unittest.main()
