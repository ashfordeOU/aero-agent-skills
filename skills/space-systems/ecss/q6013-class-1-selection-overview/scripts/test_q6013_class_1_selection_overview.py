#!/usr/bin/env python3
"""Contract test for the Class 1 commercial selection duty framing (offline).

Walks the clause workflow step by step: the component record
validation, the duty set an assurance category owes, the split between
per-component and per-programme scope, the four record states kept
apart, the misfiled programme duty, the coverage share against the
declared minimum, the disposition policy, and the roll-up into one
selection verdict. This is the gate 3 review evidence for the leaf.
"""

import copy
import unittest

from q6013_class_1_selection_overview_logic import (
    COMPONENT_NOT_READY,
    COMPONENT_READY,
    DUTY_HELD,
    DUTY_NO_RECORD,
    DUTY_OPEN,
    DUTY_REJECTED,
    PER_COMPONENT_DUTIES,
    PROGRAMME_DUTIES,
    RECORD_HELD,
    RECORD_OPEN,
    RECORD_REJECTED,
    SELECTION_NOT_READY,
    SELECTION_READY,
    assess_component_duties,
    assess_programme_duties,
    assess_selection_readiness,
    duties_owed,
    duty_owner,
    resolve_policy,
    validate_component,
)


def _component(component_id, assurance_class="class-1", **overrides):
    record = {
        "component_id": component_id,
        "assurance_class": assurance_class,
        "duty_records": {
            duty: RECORD_HELD
            for duty in duties_owed(assurance_class, "per-component")
        },
    }
    record.update(copy.deepcopy(overrides))
    return record


def _programme(assurance_class="class-1"):
    return {
        duty: RECORD_HELD
        for duty in duties_owed(assurance_class, "per-programme")
    }


def _case(count=4):
    return {
        "selection_id": "SEL-4213",
        "components": [_component("CMP-%02d" % index) for index in range(count)],
        "programme_records": _programme(),
    }


class RecordValidationTests(unittest.TestCase):
    def test_a_sound_component_validates(self):
        record = validate_component(_component("CMP-00"))
        self.assertEqual(record["assurance_class"], "class-1")
        self.assertEqual(len(record["duty_records"]), len(PER_COMPONENT_DUTIES))

    def test_an_unknown_assurance_category_rejected(self):
        with self.assertRaises(ValueError):
            validate_component(_component("CMP-00", assurance_class="class-9"))

    def test_a_duty_outside_the_selection_set_rejected(self):
        component = _component("CMP-00")
        component["duty_records"]["launch-campaign-rehearsal"] = RECORD_HELD
        with self.assertRaises(ValueError):
            validate_component(component)

    def test_an_unknown_record_state_rejected(self):
        component = _component("CMP-00")
        component["duty_records"]["commercial-usage-justification"] = "probably-fine"
        with self.assertRaises(ValueError):
            validate_component(component)

    def test_a_blank_component_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_component(_component("   "))


class DutyScopeTests(unittest.TestCase):
    def test_class_one_owes_every_duty(self):
        owed = set(duties_owed("class-1", "per-component"))
        owed |= set(duties_owed("class-1", "per-programme"))
        self.assertEqual(owed, set(PER_COMPONENT_DUTIES) | set(PROGRAMME_DUTIES))

    def test_a_lower_category_owes_fewer_duties(self):
        self.assertLess(
            len(duties_owed("class-3", "per-component")),
            len(duties_owed("class-1", "per-component")),
        )

    def test_an_unknown_scope_rejected(self):
        with self.assertRaises(ValueError):
            duties_owed("class-1", "per-subsystem")

    def test_every_duty_names_an_owner_role(self):
        for duty in PER_COMPONENT_DUTIES + PROGRAMME_DUTIES:
            self.assertTrue(duty_owner(duty))

    def test_an_unknown_duty_has_no_owner(self):
        with self.assertRaises(ValueError):
            duty_owner("component-colour-preference")


class ComponentDutyTests(unittest.TestCase):
    def test_a_fully_held_component_is_ready(self):
        result = assess_component_duties(_component("CMP-00"))
        self.assertEqual(result["verdict"], DUTY_HELD)
        self.assertEqual(result["readiness"], COMPONENT_READY)
        self.assertAlmostEqual(result["duty_coverage"], 1.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_an_absent_record_outranks_a_rejection(self):
        component = _component("CMP-00")
        component["duty_records"]["radiation-suitability-assessment"] = RECORD_REJECTED
        del component["duty_records"]["component-evaluation-plan"]
        result = assess_component_duties(component)
        self.assertEqual(result["verdict"], DUTY_NO_RECORD)
        self.assertEqual(result["readiness"], COMPONENT_NOT_READY)

    def test_a_rejection_outranks_an_open_duty(self):
        component = _component("CMP-00")
        component["duty_records"]["component-evaluation-plan"] = RECORD_OPEN
        component["duty_records"]["franchised-procurement-route"] = RECORD_REJECTED
        result = assess_component_duties(component)
        self.assertEqual(result["verdict"], DUTY_REJECTED)

    def test_an_open_duty_can_be_carried_by_declared_policy(self):
        component = _component("CMP-00")
        component["duty_records"]["component-evaluation-plan"] = RECORD_OPEN
        strict = assess_component_duties(component)
        carried = assess_component_duties(
            component, {"carry_dispositioned_open": True}
        )
        self.assertEqual(strict["readiness"], COMPONENT_NOT_READY)
        self.assertEqual(carried["readiness"], COMPONENT_READY)
        self.assertEqual(carried["verdict"], DUTY_OPEN)

    def test_a_programme_duty_filed_against_a_part_is_a_finding(self):
        component = _component("CMP-00")
        component["duty_records"]["customer-agreement-record"] = RECORD_HELD
        result = assess_component_duties(component)
        self.assertEqual(
            result["misfiled_programme_duties"], ["customer-agreement-record"]
        )
        self.assertTrue(
            any("owed once per programme" in f for f in result["findings"])
        )

    def test_a_missing_duty_names_its_owner_in_the_finding(self):
        component = _component("CMP-00")
        del component["duty_records"]["radiation-suitability-assessment"]
        result = assess_component_duties(component)
        self.assertTrue(
            any("product-assurance" in f for f in result["findings"])
        )
        self.assertAlmostEqual(result["duty_coverage"], 0.8, places=9)

    def test_a_lower_category_part_is_not_graded_on_the_evaluation_plan(self):
        component = _component("CMP-00", assurance_class="class-2")
        result = assess_component_duties(component)
        self.assertNotIn("component-evaluation-plan", result["owed"])
        self.assertEqual(result["verdict"], DUTY_HELD)


class ProgrammeDutyTests(unittest.TestCase):
    def test_a_held_programme_record_set_passes(self):
        result = assess_programme_duties(_programme(), "class-1")
        self.assertEqual(result["verdict"], DUTY_HELD)
        self.assertAlmostEqual(result["duty_coverage"], 1.0, places=9)

    def test_an_empty_programme_record_set_is_absence_not_failure(self):
        result = assess_programme_duties({}, "class-1")
        self.assertEqual(result["verdict"], DUTY_NO_RECORD)
        self.assertEqual(len(result["missing"]), len(PROGRAMME_DUTIES))

    def test_a_per_component_duty_filed_at_programme_scope_rejected(self):
        with self.assertRaises(ValueError):
            assess_programme_duties(
                {"commercial-usage-justification": RECORD_HELD}, "class-1"
            )


class PolicyTests(unittest.TestCase):
    def test_defaults_resolve_to_full_coverage(self):
        settings = resolve_policy()
        self.assertAlmostEqual(settings["min_duty_coverage"], 1.0, places=9)
        self.assertFalse(settings["carry_dispositioned_open"])

    def test_a_coverage_minimum_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            resolve_policy({"min_duty_coverage": 1.4})

    def test_a_non_boolean_disposition_flag_rejected(self):
        with self.assertRaises(ValueError):
            resolve_policy({"carry_dispositioned_open": "yes"})


class SelectionRollUpTests(unittest.TestCase):
    def test_a_complete_selection_is_ready(self):
        result = assess_selection_readiness(_case())
        self.assertEqual(result["verdict"], SELECTION_READY)
        self.assertAlmostEqual(result["duty_coverage"], 1.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_an_open_programme_duty_alone_stops_the_selection(self):
        case = _case()
        case["programme_records"]["customer-agreement-record"] = RECORD_OPEN
        result = assess_selection_readiness(case)
        self.assertEqual(result["verdict"], SELECTION_NOT_READY)
        self.assertEqual(result["programme"]["verdict"], DUTY_OPEN)
        for assessment in result["components"]:
            self.assertEqual(assessment["verdict"], DUTY_HELD)

    def test_the_programme_duty_is_counted_once_not_once_per_part(self):
        small = assess_selection_readiness(_case(count=2))
        large = assess_selection_readiness(_case(count=8))
        self.assertEqual(len(small["programme"]["owed"]), len(PROGRAMME_DUTIES))
        self.assertEqual(len(large["programme"]["owed"]), len(PROGRAMME_DUTIES))
        self.assertAlmostEqual(large["duty_coverage"], 1.0, places=9)

    def test_the_weakest_component_is_the_one_with_no_record(self):
        case = _case()
        case["components"][1]["duty_records"][
            "commercial-usage-justification"
        ] = RECORD_OPEN
        del case["components"][3]["duty_records"]["commercial-usage-justification"]
        result = assess_selection_readiness(case)
        self.assertEqual(result["weakest_component"], "CMP-03")
        self.assertIn(DUTY_OPEN, result["grouped_components"])
        self.assertIn(DUTY_NO_RECORD, result["grouped_components"])

    def test_a_relaxed_coverage_minimum_is_met_exactly_at_the_bound(self):
        case = _case(count=2)
        del case["components"][0]["duty_records"]["component-evaluation-plan"]
        owed = 2 * len(PER_COMPONENT_DUTIES) + len(PROGRAMME_DUTIES)
        bound = (owed - 1) / owed
        case["policy"] = {"min_duty_coverage": bound}
        result = assess_selection_readiness(case)
        self.assertAlmostEqual(result["duty_coverage"], bound, places=9)
        self.assertTrue(result["meets_duty_coverage"])

    def test_a_component_listed_twice_rejected(self):
        case = _case()
        case["components"].append(copy.deepcopy(case["components"][0]))
        with self.assertRaises(ValueError):
            assess_selection_readiness(case)

    def test_an_empty_selection_rejected(self):
        with self.assertRaises(ValueError):
            assess_selection_readiness(
                {"selection_id": "SEL-4213", "components": []}
            )

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_selection_readiness("every part was agreed with the customer")


if __name__ == "__main__":
    unittest.main()
