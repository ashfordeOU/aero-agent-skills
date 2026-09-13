#!/usr/bin/env python3
"""Contract test for the clause 5.2.5.2 enclosure-occupancy logic.

Standard library unittest only; offline and deterministic.
Run: python3 test_e2007_test_area_occupancy_limits.py
"""

import unittest

from e2007_test_area_occupancy_limits_logic import (
    KNOWN_FUNCTIONS,
    KNOWN_ROLES,
    PERSON_FOOTPRINT_M2,
    PERTURBATION_LIMIT,
    RUN_MODES,
    STRAY_ITEM,
    assess_enclosure_occupancy,
    categorize_item,
    evaluate_egress_capacity,
    evaluate_hardware,
    evaluate_personnel,
    necessary_roles,
    quiet_zone_perturbation,
)


def roster():
    return [
        {"badge": "b-01", "role": "run-conductor", "justification": "runs the step"},
        {
            "badge": "b-02",
            "role": "measurement-engineer",
            "justification": "operates the receiver",
        },
        {
            "badge": "b-03",
            "role": "safety-officer",
            "justification": "watches the drive level",
        },
    ]


def hardware():
    return [
        {
            "id": "article-1",
            "function": "article-under-verification",
            "justification": "the item being verified",
            "footprint_m2": 0.60,
        },
        {
            "id": "probe-1",
            "function": "field-probe",
            "justification": "monitors the field level",
            "footprint_m2": 0.05,
        },
        {
            "id": "rack-1",
            "function": "support-equipment",
            "justification": "feeds the article",
            "footprint_m2": 0.80,
            "inside_quiet_zone": False,
        },
    ]


def plan():
    return {
        "run_mode": "radiated-susceptibility",
        "occupants": roster(),
        "items": hardware(),
        "quiet_zone_area_m2": 40.0,
        "egress_capacity": 6,
    }


class TestNecessaryRoles(unittest.TestCase):
    def test_emission_run_needs_conductor_and_engineer(self):
        self.assertEqual(
            sorted(necessary_roles("radiated-emission")),
            ["measurement-engineer", "run-conductor"],
        )

    def test_susceptibility_run_adds_the_safety_officer(self):
        self.assertIn("safety-officer", necessary_roles("radiated-susceptibility"))

    def test_calibration_run_needs_only_the_engineer(self):
        self.assertEqual(
            sorted(necessary_roles("enclosure-calibration")), ["measurement-engineer"]
        )

    def test_in_enclosure_commanding_adds_the_operator(self):
        self.assertIn(
            "article-operator",
            necessary_roles("radiated-emission", in_enclosure_commanding=True),
        )

    def test_witnessed_run_adds_the_quality_witness(self):
        self.assertIn(
            "quality-witness", necessary_roles("radiated-emission", witnessed=True)
        )

    def test_an_observer_is_never_necessary(self):
        for mode in RUN_MODES:
            roles = necessary_roles(mode, True, True)
            self.assertNotIn("observer", roles)
            self.assertNotIn("visitor", roles)

    def test_unrecognized_run_mode_rejected(self):
        with self.assertRaises(ValueError):
            necessary_roles("thermal-vacuum-soak")

    def test_non_boolean_commanding_flag_rejected(self):
        with self.assertRaises(ValueError):
            necessary_roles("radiated-emission", in_enclosure_commanding="yes")

    def test_every_base_role_is_a_known_role(self):
        for mode in RUN_MODES:
            for role in necessary_roles(mode, True, True):
                self.assertIn(role, KNOWN_ROLES)


class TestPersonnel(unittest.TestCase):
    def test_a_minimal_essential_roster_has_no_finding(self):
        result = evaluate_personnel(roster(), "radiated-susceptibility")
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["essential"]), 3)

    def test_an_observer_is_withdrawn(self):
        people = roster() + [
            {"badge": "b-09", "role": "observer", "justification": "wants to watch"}
        ]
        result = evaluate_personnel(people, "radiated-susceptibility")
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["findings"][0]["finding"], "role-not-needed-for-run-mode")

    def test_a_needed_role_without_justification_is_withdrawn(self):
        people = roster()
        del people[1]["justification"]
        result = evaluate_personnel(people, "radiated-susceptibility")
        reasons = [item["finding"] for item in result["findings"]]
        self.assertIn("no-run-step-justification", reasons)

    def test_withdrawing_a_needed_role_also_reports_it_absent(self):
        people = roster()
        del people[1]["justification"]
        result = evaluate_personnel(people, "radiated-susceptibility")
        reasons = [item["finding"] for item in result["findings"]]
        self.assertIn("required-role-absent", reasons)

    def test_a_missing_safety_officer_is_reported(self):
        result = evaluate_personnel(roster()[:2], "radiated-susceptibility")
        self.assertEqual(
            [item["finding"] for item in result["findings"]], ["required-role-absent"]
        )

    def test_commanding_operator_is_kept_when_the_run_needs_one(self):
        people = roster() + [
            {
                "badge": "b-04",
                "role": "article-operator",
                "justification": "commands the article in place",
            }
        ]
        result = evaluate_personnel(
            people, "radiated-susceptibility", in_enclosure_commanding=True
        )
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["essential"]), 4)

    def test_duplicate_badge_rejected(self):
        people = roster()
        people[1]["badge"] = "b-01"
        with self.assertRaises(ValueError):
            evaluate_personnel(people, "radiated-susceptibility")

    def test_unrecognized_role_rejected(self):
        people = roster() + [
            {"badge": "b-05", "role": "photographer", "justification": "documents"}
        ]
        with self.assertRaises(ValueError):
            evaluate_personnel(people, "radiated-susceptibility")

    def test_roster_entry_without_a_badge_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_personnel(
                [{"role": "run-conductor", "justification": "runs"}],
                "radiated-emission",
            )

    def test_roster_that_is_not_a_list_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_personnel({"badge": "b-01"}, "radiated-emission")


class TestHardware(unittest.TestCase):
    def test_a_justified_item_keeps_its_function(self):
        self.assertEqual(categorize_item(hardware()[1]), "field-probe")

    def test_an_item_without_a_function_is_stray(self):
        self.assertEqual(
            categorize_item({"id": "toolbox-1", "footprint_m2": 0.2}), STRAY_ITEM
        )

    def test_an_item_without_justification_is_stray(self):
        item = dict(hardware()[1])
        del item["justification"]
        self.assertEqual(categorize_item(item), STRAY_ITEM)

    def test_unrecognized_item_function_rejected(self):
        with self.assertRaises(ValueError):
            categorize_item({"id": "x", "function": "spare-cable", "justification": "j"})

    def test_item_without_an_id_rejected(self):
        with self.assertRaises(ValueError):
            categorize_item({"function": "field-probe", "justification": "j"})

    def test_clean_hardware_set_has_no_finding(self):
        result = evaluate_hardware(hardware())
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["needed"]), 3)

    def test_stray_item_is_flagged_for_withdrawal(self):
        items = hardware() + [{"id": "toolbox-1", "footprint_m2": 0.2}]
        result = evaluate_hardware(items)
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["findings"][0]["finding"], "unjustified-item-present")

    def test_a_verification_run_without_its_article_is_flagged(self):
        result = evaluate_hardware(hardware()[1:])
        self.assertEqual(
            [item["finding"] for item in result["findings"]],
            ["article-under-verification-absent"],
        )

    def test_a_calibration_run_needs_no_article(self):
        result = evaluate_hardware(hardware()[1:], require_article=False)
        self.assertEqual(result["findings"], [])

    def test_duplicate_item_id_rejected(self):
        items = hardware() + [dict(hardware()[1])]
        with self.assertRaises(ValueError):
            evaluate_hardware(items)

    def test_every_known_function_is_categorizable(self):
        for function in KNOWN_FUNCTIONS:
            item = {"id": "i-1", "function": function, "justification": "needed"}
            self.assertEqual(categorize_item(item), function)


class TestPerturbation(unittest.TestCase):
    def test_an_empty_enclosure_perturbs_nothing(self):
        self.assertAlmostEqual(quiet_zone_perturbation(0, [], 40.0), 0.0)

    def test_bodies_count_at_the_standing_footprint(self):
        self.assertAlmostEqual(
            quiet_zone_perturbation(4, [], 40.0), 4 * PERSON_FOOTPRINT_M2 / 40.0
        )

    def test_items_outside_the_quiet_zone_are_skipped(self):
        inside = quiet_zone_perturbation(0, [hardware()[0]], 40.0)
        outside = quiet_zone_perturbation(0, [hardware()[2]], 40.0)
        self.assertAlmostEqual(inside, 0.6 / 40.0)
        self.assertAlmostEqual(outside, 0.0)

    def test_bodies_and_items_add_up(self):
        fraction = quiet_zone_perturbation(2, hardware(), 40.0)
        self.assertAlmostEqual(fraction, (2 * PERSON_FOOTPRINT_M2 + 0.65) / 40.0)

    def test_exact_boundary_case_survives_representation_error(self):
        items = [
            {"id": "i-1", "footprint_m2": 0.20},
            {"id": "i-2", "footprint_m2": 0.05},
        ]
        fraction = quiet_zone_perturbation(1, items, 6.0)
        self.assertGreater(fraction, PERTURBATION_LIMIT)
        run = plan()
        run["quiet_zone_area_m2"] = 6.0
        run["run_mode"] = "enclosure-calibration"
        run["occupants"] = [
            {
                "badge": "b-02",
                "role": "measurement-engineer",
                "justification": "runs the calibration",
            }
        ]
        run["items"] = [
            {
                "id": "rack-1",
                "function": "support-equipment",
                "justification": "drives the calibration antenna",
                "footprint_m2": 0.20,
            },
            {
                "id": "probe-1",
                "function": "field-probe",
                "justification": "monitors the field",
                "footprint_m2": 0.05,
            },
        ]
        result = assess_enclosure_occupancy(run)
        self.assertGreater(result["perturbation_fraction"], PERTURBATION_LIMIT)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["clear_to_run"])

    def test_a_real_over_occupancy_is_not_absorbed(self):
        fraction = quiet_zone_perturbation(6, hardware(), 12.0)
        self.assertGreater(fraction, PERTURBATION_LIMIT)

    def test_non_positive_quiet_zone_area_rejected(self):
        with self.assertRaises(ValueError):
            quiet_zone_perturbation(1, [], 0.0)

    def test_negative_footprint_rejected(self):
        with self.assertRaises(ValueError):
            quiet_zone_perturbation(1, [{"id": "i-1", "footprint_m2": -0.5}], 40.0)

    def test_non_integer_headcount_rejected(self):
        with self.assertRaises(ValueError):
            quiet_zone_perturbation(2.5, [], 40.0)


class TestEgressCapacity(unittest.TestCase):
    def test_headcount_under_capacity_passes(self):
        self.assertEqual(evaluate_egress_capacity(3, 6)["findings"], [])

    def test_headcount_exactly_at_capacity_passes(self):
        self.assertEqual(evaluate_egress_capacity(6, 6)["findings"], [])

    def test_headcount_above_capacity_is_flagged(self):
        result = evaluate_egress_capacity(7, 6)
        self.assertEqual(
            result["findings"][0]["finding"], "headcount-above-egress-capacity"
        )

    def test_zero_capacity_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_egress_capacity(1, 0)

    def test_negative_headcount_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_egress_capacity(-1, 6)


class TestOccupancyAssessment(unittest.TestCase):
    def test_a_clean_plan_is_clear_to_run(self):
        result = assess_enclosure_occupancy(plan())
        self.assertTrue(result["clear_to_run"])
        self.assertEqual(result["findings"], [])

    def test_perturbation_fraction_is_reported(self):
        result = assess_enclosure_occupancy(plan())
        self.assertAlmostEqual(
            result["perturbation_fraction"], (3 * PERSON_FOOTPRINT_M2 + 0.65) / 40.0
        )

    def test_a_crowded_enclosure_is_blocked(self):
        run = plan()
        run["quiet_zone_area_m2"] = 8.0
        result = assess_enclosure_occupancy(run)
        self.assertFalse(result["clear_to_run"])
        self.assertEqual(
            [item["finding"] for item in result["findings"]],
            ["quiet-zone-perturbation-above-allowance"],
        )

    def test_egress_capacity_is_checked_against_the_surviving_headcount(self):
        run = plan()
        run["egress_capacity"] = 2
        result = assess_enclosure_occupancy(run)
        reasons = [item["finding"] for item in result["findings"]]
        self.assertIn("headcount-above-egress-capacity", reasons)

    def test_withdrawn_visitors_do_not_count_towards_egress(self):
        run = plan()
        run["egress_capacity"] = 3
        run["occupants"] = roster() + [
            {"badge": "b-08", "role": "visitor", "justification": "touring"}
        ]
        result = assess_enclosure_occupancy(run)
        reasons = [item["finding"] for item in result["findings"]]
        self.assertNotIn("headcount-above-egress-capacity", reasons)
        self.assertEqual(result["egress"]["occupants"], 3)

    def test_stray_hardware_does_not_perturb_the_retained_quiet_zone(self):
        run = plan()
        run["items"] = hardware() + [{"id": "toolbox-1", "footprint_m2": 20.0}]
        result = assess_enclosure_occupancy(run)
        self.assertAlmostEqual(
            result["perturbation_fraction"], (3 * PERSON_FOOTPRINT_M2 + 0.65) / 40.0
        )
        self.assertEqual(
            [item["finding"] for item in result["findings"]],
            ["unjustified-item-present"],
        )

    def test_a_calibration_plan_needs_neither_article_nor_conductor(self):
        run = plan()
        run["run_mode"] = "enclosure-calibration"
        run["occupants"] = [
            {
                "badge": "b-02",
                "role": "measurement-engineer",
                "justification": "runs the calibration",
            }
        ]
        run["items"] = [hardware()[1]]
        result = assess_enclosure_occupancy(run)
        self.assertTrue(result["clear_to_run"])

    def test_findings_from_every_stage_are_aggregated(self):
        run = plan()
        run["occupants"] = roster() + [
            {"badge": "b-09", "role": "observer", "justification": "watching"}
        ]
        run["items"] = hardware() + [{"id": "toolbox-1", "footprint_m2": 0.2}]
        run["quiet_zone_area_m2"] = 8.0
        run["egress_capacity"] = 1
        result = assess_enclosure_occupancy(run)
        reasons = sorted(item["finding"] for item in result["findings"])
        self.assertEqual(
            reasons,
            [
                "headcount-above-egress-capacity",
                "quiet-zone-perturbation-above-allowance",
                "role-not-needed-for-run-mode",
                "unjustified-item-present",
            ],
        )

    def test_missing_plan_key_rejected(self):
        run = plan()
        del run["egress_capacity"]
        with self.assertRaises(ValueError):
            assess_enclosure_occupancy(run)

    def test_plan_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_enclosure_occupancy(["radiated-emission"])


if __name__ == "__main__":
    unittest.main()
