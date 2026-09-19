#!/usr/bin/env python3
"""Gate 3 contract test for q6005-hybrid-repair-provisions.

Offline, stdlib unittest. Exercises the assembly sequence, the per-action
repair window, the direct, lid-removal and closed routes, the re-screening
each route drags with it and the approvals a request needs, for
ECSS-Q-ST-60-05C clause 10.5 as paraphrased in the logic module. Every
quantity here is a sequence position or a boolean, so the assertions compare
exactly; no float bound is asserted from a side.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_hybrid_repair_provisions_logic import (  # noqa: E402
    ACTION_WINDOWS,
    ASSEMBLY_SEQUENCE,
    action_window_stage,
    assess_repair_request,
    repair_route,
    requires_lid_removal,
    rescreen_steps,
    stage_index,
    within_repair_window,
)


def request(action="wire-rebond", stage="wire-bonding", **overrides):
    spec = {
        "action": action,
        "assembly_stage": stage,
        "approved_repair_procedure_exists": True,
    }
    spec.update(overrides)
    return spec


class SequenceTests(unittest.TestCase):
    def test_stages_are_indexed_in_worked_order(self):
        self.assertEqual(stage_index("substrate-preparation"), 0)
        self.assertLess(stage_index("wire-bonding"), stage_index("lid-sealing"))
        self.assertEqual(stage_index("delivered"), len(ASSEMBLY_SEQUENCE) - 1)

    def test_stage_names_are_matched_case_and_separator_insensitively(self):
        self.assertEqual(stage_index("  LID SEALING "), stage_index("lid-sealing"))

    def test_unknown_stage_is_refused(self):
        with self.assertRaises(ValueError):
            stage_index("lid-polishing")

    def test_blank_or_non_string_stage_is_refused(self):
        for bad in ("", "   ", 4, None):
            with self.assertRaises(ValueError):
                stage_index(bad)

    def test_every_action_window_names_a_real_stage(self):
        for action, window in ACTION_WINDOWS.items():
            self.assertIn(window, ASSEMBLY_SEQUENCE)
            self.assertEqual(action_window_stage(action), window)

    def test_unknown_action_is_refused(self):
        with self.assertRaises(ValueError):
            action_window_stage("repaint-the-lid")


class WindowTests(unittest.TestCase):
    def test_a_rebond_before_pre_cap_is_inside_its_window(self):
        self.assertTrue(within_repair_window("wire-rebond", "wire-bonding"))
        self.assertTrue(within_repair_window("wire-rebond", "pre-cap-inspection"))

    def test_a_rebond_after_sealing_is_outside_its_window(self):
        self.assertFalse(within_repair_window("wire-rebond", "lid-sealing"))

    def test_substrate_touch_up_closes_once_elements_are_attached(self):
        self.assertTrue(
            within_repair_window("substrate-metallization-touch-up", "substrate-metallization")
        )
        self.assertFalse(
            within_repair_window("substrate-metallization-touch-up", "active-die-attach")
        )

    def test_element_replacement_stays_open_through_wire_bonding(self):
        self.assertTrue(within_repair_window("active-die-replacement", "wire-bonding"))
        self.assertFalse(within_repair_window("active-die-replacement", "pre-cap-inspection"))


class RouteTests(unittest.TestCase):
    def test_work_inside_the_window_takes_the_direct_route(self):
        self.assertEqual(repair_route("wire-rebond", "wire-bonding"), "direct")
        self.assertFalse(requires_lid_removal("wire-rebond", "wire-bonding"))

    def test_work_blocked_only_by_the_seal_takes_the_lid_removal_route(self):
        self.assertEqual(repair_route("wire-rebond", "post-seal-screening"), "lid-removal")
        self.assertTrue(requires_lid_removal("wire-rebond", "post-seal-screening"))

    def test_work_buried_under_later_assembly_is_closed_not_reopened(self):
        self.assertEqual(
            repair_route("substrate-metallization-touch-up", "active-die-attach"), "closed"
        )
        self.assertFalse(
            requires_lid_removal("substrate-metallization-touch-up", "active-die-attach")
        )

    def test_lid_removal_does_not_reopen_work_buried_before_pre_cap(self):
        # De-lidding reverts the unit to pre-cap, not to bare substrate, so an
        # action whose window closed earlier stays closed on a sealed unit.
        self.assertEqual(
            repair_route("substrate-metallization-touch-up", "delivered"), "closed"
        )
        self.assertEqual(
            repair_route("active-die-replacement", "post-seal-screening"), "closed"
        )
        self.assertFalse(requires_lid_removal("active-die-replacement", "post-seal-screening"))

    def test_external_lead_repair_stays_direct_on_a_sealed_unit(self):
        self.assertEqual(repair_route("external-lead-repair", "post-seal-screening"), "direct")
        self.assertFalse(requires_lid_removal("external-lead-repair", "post-seal-screening"))

    def test_a_delivered_unit_is_past_every_window(self):
        self.assertEqual(repair_route("external-lead-repair", "delivered"), "closed")


class RescreenTests(unittest.TestCase):
    def test_a_closed_route_drags_no_rescreen_because_there_is_no_repair(self):
        self.assertEqual(rescreen_steps("substrate-metallization-touch-up", "delivered"), ())
        self.assertEqual(rescreen_steps("active-die-replacement", "post-seal-screening"), ())

    def test_direct_work_before_pre_cap_costs_an_inspection_of_the_area(self):
        self.assertEqual(rescreen_steps("wire-rebond", "wire-bonding"), ("inspect-the-repaired-area",))

    def test_direct_work_at_pre_cap_repeats_the_pre_cap_inspection(self):
        steps = rescreen_steps("wire-rebond", "pre-cap-inspection")
        self.assertIn("repeat-pre-cap-inspection", steps)

    def test_direct_work_on_a_sealed_unit_repeats_the_seal_tests(self):
        steps = rescreen_steps("external-lead-repair", "post-seal-screening")
        self.assertIn("repeat-seal-tests", steps)
        self.assertIn("repeat-external-visual", steps)

    def test_lid_removal_repeats_the_whole_screening_sequence(self):
        steps = rescreen_steps("wire-rebond", "lid-sealing")
        self.assertIn("repeat-the-full-screening-sequence", steps)
        self.assertIn("re-seal-and-repeat-seal-tests", steps)


class AssessmentTests(unittest.TestCase):
    def test_a_rebond_in_the_window_with_a_procedure_is_permitted(self):
        result = assess_repair_request(request())
        self.assertTrue(result["permitted"])
        self.assertEqual(result["route"], "direct")
        self.assertEqual(result["blockers"], [])

    def test_a_request_without_an_approved_procedure_is_blocked(self):
        result = assess_repair_request(request(approved_repair_procedure_exists=False))
        self.assertFalse(result["permitted"])
        self.assertTrue(any("approved repair procedure" in b for b in result["blockers"]))

    def test_lid_removal_without_customer_approval_is_blocked(self):
        result = assess_repair_request(request(stage="post-seal-screening"))
        self.assertTrue(result["requires_lid_removal"])
        self.assertFalse(result["permitted"])
        self.assertTrue(any("customer approval" in b for b in result["blockers"]))

    def test_lid_removal_with_customer_approval_is_permitted_but_costly(self):
        result = assess_repair_request(
            request(stage="post-seal-screening", customer_approval_granted=True)
        )
        self.assertTrue(result["permitted"])
        self.assertIn("customer-approval-for-lid-removal", result["approvals_required"])
        self.assertIn("repeat-the-full-screening-sequence", result["rescreen"])
        self.assertTrue(any("void" in f for f in result["findings"]))

    def test_a_closed_window_cannot_be_approved_open(self):
        result = assess_repair_request(
            request(
                action="substrate-metallization-touch-up",
                stage="active-die-attach",
                customer_approval_granted=True,
            )
        )
        self.assertFalse(result["permitted"])
        self.assertTrue(any("window closed" in b for b in result["blockers"]))

    def test_delivered_hardware_needs_customer_approval(self):
        result = assess_repair_request(request(action="external-lead-repair", stage="delivered"))
        self.assertFalse(result["permitted"])
        self.assertIn(
            "customer-approval-for-work-on-delivered-hardware", result["approvals_required"]
        )

    def test_manufacturer_authorization_is_always_required(self):
        result = assess_repair_request(request())
        self.assertIn("manufacturer-quality-authorization", result["approvals_required"])

    def test_missing_required_key_is_refused(self):
        for key in ("action", "assembly_stage"):
            spec = request()
            del spec[key]
            with self.assertRaises(ValueError):
                assess_repair_request(spec)

    def test_non_boolean_flag_is_refused(self):
        with self.assertRaises(ValueError):
            assess_repair_request(request(customer_approval_granted="yes"))

    def test_a_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_repair_request(["wire-rebond", "wire-bonding"])

    def test_the_report_names_where_the_window_closes(self):
        result = assess_repair_request(request())
        self.assertEqual(result["window_closes_at"], "pre-cap-inspection")
        self.assertTrue(result["within_window"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
