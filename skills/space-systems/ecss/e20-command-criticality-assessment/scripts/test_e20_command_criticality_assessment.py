#!/usr/bin/env python3
"""Gate 3 contract test for e20-command-criticality-assessment.

stdlib unittest, offline, deterministic. Run:
    python3 test_e20_command_criticality_assessment.py
"""

import unittest

from e20_command_criticality_assessment_logic import (
    assess_command,
    assess_command_set,
    bound_redundancy_downgrade,
    categorize_command_effect,
    check_protection_measures,
    escalate_to_system_level,
    rate_equipment_criticality,
)


def command(**overrides):
    """A benign, fully protected baseline command."""
    cmd = {
        "id": "TC-0001",
        "effect": "no-effect",
        "reversible": True,
        "onboard_recovery": "none",
        "system_context": {
            "single_string_critical_function": False,
            "subsystems_affected": 1,
        },
        "protections": [],
    }
    for key, value in overrides.items():
        if key == "system_context":
            cmd["system_context"].update(value)
        else:
            cmd[key] = value
    return cmd


def redundancy(claimed=False, path_available=False, same_command_word=False):
    return {
        "claimed": claimed,
        "path_available": path_available,
        "same_command_word": same_command_word,
    }


class EffectCategorizationTests(unittest.TestCase):
    def test_canonical_effects_carry_an_ordered_severity(self):
        ranks = [categorize_command_effect(e)[1] for e in (
            "no-effect",
            "transient-nuisance",
            "degraded-performance",
            "loss-of-redundancy",
            "loss-of-function",
            "loss-of-mission",
            "loss-of-vehicle",
        )]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(ranks, [0, 1, 2, 3, 4, 5, 6])

    def test_aliases_and_spacing_normalise(self):
        self.assertEqual(categorize_command_effect("Catastrophic"), ("loss-of-vehicle", 6))
        self.assertEqual(categorize_command_effect(" function loss "), ("loss-of-function", 4))
        self.assertEqual(categorize_command_effect("degraded"), ("degraded-performance", 2))

    def test_unrecognised_effect_terms_raise(self):
        with self.assertRaises(ValueError):
            categorize_command_effect("slightly-annoying")
        with self.assertRaises(ValueError):
            categorize_command_effect("  ")
        with self.assertRaises(ValueError):
            categorize_command_effect(4)


class EquipmentRatingTests(unittest.TestCase):
    def test_benign_command_is_non_critical(self):
        result = rate_equipment_criticality(command())
        self.assertEqual(result["equipment_level"], "non-critical")
        self.assertEqual(result["severity"], 0)

    def test_irreversible_effect_raises_one_step(self):
        reversible = rate_equipment_criticality(
            command(effect="degraded-performance", reversible=True)
        )
        irreversible = rate_equipment_criticality(
            command(effect="degraded-performance", reversible=False)
        )
        self.assertEqual(reversible["equipment_level"], "mission-significant")
        self.assertEqual(irreversible["equipment_level"], "mission-critical")

    def test_autonomous_recovery_lowers_but_ground_recovery_does_not(self):
        autonomous = rate_equipment_criticality(
            command(effect="loss-of-function", onboard_recovery="autonomous")
        )
        ground = rate_equipment_criticality(
            command(effect="loss-of-function", onboard_recovery="ground")
        )
        self.assertEqual(autonomous["equipment_level"], "mission-significant")
        self.assertEqual(ground["equipment_level"], "mission-critical")
        self.assertTrue(any("ground pass" in n for n in ground["rationale"]))

    def test_level_saturates_at_the_top_of_the_scale(self):
        result = rate_equipment_criticality(
            command(effect="loss-of-vehicle", reversible=False)
        )
        self.assertEqual(result["equipment_level"], "hazardous")

    def test_malformed_commands_raise(self):
        with self.assertRaises(ValueError):
            rate_equipment_criticality(["TC-0001"])
        broken = command()
        del broken["reversible"]
        with self.assertRaises(ValueError):
            rate_equipment_criticality(broken)
        with self.assertRaises(ValueError):
            rate_equipment_criticality(command(reversible="yes"))
        with self.assertRaises(ValueError):
            rate_equipment_criticality(command(onboard_recovery="maybe"))


class SystemConfirmationTests(unittest.TestCase):
    def test_single_string_critical_function_forces_mission_critical(self):
        result = escalate_to_system_level(
            "mission-significant",
            {"single_string_critical_function": True, "subsystems_affected": 1},
        )
        self.assertEqual(result["system_level"], "mission-critical")

    def test_single_string_floor_never_lowers_a_hazardous_rating(self):
        result = escalate_to_system_level(
            "hazardous",
            {"single_string_critical_function": True, "subsystems_affected": 1},
        )
        self.assertEqual(result["system_level"], "hazardous")

    def test_multi_subsystem_propagation_raises_one_step(self):
        result = escalate_to_system_level(
            "mission-significant",
            {"single_string_critical_function": False, "subsystems_affected": 3},
        )
        self.assertEqual(result["system_level"], "mission-critical")
        self.assertTrue(any("propagates" in n for n in result["notes"]))

    def test_unchanged_rating_is_reported_as_confirmed(self):
        result = escalate_to_system_level(
            "non-critical",
            {"single_string_critical_function": False, "subsystems_affected": 1},
        )
        self.assertEqual(result["system_level"], "non-critical")
        self.assertTrue(any("confirmed" in n for n in result["notes"]))

    def test_bad_level_and_context_raise(self):
        with self.assertRaises(ValueError):
            escalate_to_system_level(
                "very-critical",
                {"single_string_critical_function": False, "subsystems_affected": 1},
            )
        with self.assertRaises(ValueError):
            escalate_to_system_level("non-critical", "no-context")
        with self.assertRaises(ValueError):
            escalate_to_system_level("non-critical", {"subsystems_affected": 1})
        with self.assertRaises(ValueError):
            escalate_to_system_level(
                "non-critical",
                {"single_string_critical_function": False, "subsystems_affected": 0},
            )
        with self.assertRaises(ValueError):
            escalate_to_system_level(
                "non-critical",
                {"single_string_critical_function": False, "subsystems_affected": True},
            )


class RedundancyDowngradeTests(unittest.TestCase):
    def test_unclaimed_downgrade_leaves_the_level_alone(self):
        result = bound_redundancy_downgrade("mission-critical", 4, redundancy())
        self.assertEqual(result["level"], "mission-critical")

    def test_downgrade_without_a_redundant_path_is_rejected(self):
        result = bound_redundancy_downgrade(
            "mission-critical", 4, redundancy(claimed=True, path_available=False)
        )
        self.assertEqual(result["level"], "mission-critical")
        self.assertIn("no redundant path", result["note"])

    def test_shared_command_word_defeats_the_downgrade(self):
        result = bound_redundancy_downgrade(
            "hazardous",
            6,
            redundancy(claimed=True, path_available=True, same_command_word=True),
        )
        self.assertEqual(result["level"], "hazardous")
        self.assertIn("same command word", result["note"])

    def test_valid_downgrade_moves_exactly_one_step(self):
        result = bound_redundancy_downgrade(
            "hazardous", 6, redundancy(claimed=True, path_available=True)
        )
        self.assertEqual(result["level"], "mission-critical")

    def test_downgrade_is_floored_for_a_loss_of_function_effect(self):
        result = bound_redundancy_downgrade(
            "mission-significant", 4, redundancy(claimed=True, path_available=True)
        )
        self.assertEqual(result["level"], "mission-significant")
        self.assertIn("floored", result["note"])

    def test_low_severity_downgrade_may_reach_non_critical(self):
        result = bound_redundancy_downgrade(
            "mission-significant", 2, redundancy(claimed=True, path_available=True)
        )
        self.assertEqual(result["level"], "non-critical")

    def test_bad_severity_and_redundancy_raise(self):
        with self.assertRaises(ValueError):
            bound_redundancy_downgrade("mission-critical", 9, redundancy())
        with self.assertRaises(ValueError):
            bound_redundancy_downgrade("mission-critical", "four", redundancy())
        with self.assertRaises(ValueError):
            bound_redundancy_downgrade("mission-critical", 4, ["claimed"])
        with self.assertRaises(ValueError):
            bound_redundancy_downgrade("mission-critical", 4, {"claimed": True})
        with self.assertRaises(ValueError):
            bound_redundancy_downgrade(
                "mission-critical",
                4,
                {"claimed": "yes", "path_available": True, "same_command_word": False},
            )


class ProtectionTests(unittest.TestCase):
    def test_hazardous_command_demands_the_full_protection_set(self):
        missing = check_protection_measures("hazardous", [])
        self.assertEqual(
            missing,
            [
                "command-verification",
                "arm-and-execute",
                "command-authentication",
                "inhibit-status-telemetry",
            ],
        )

    def test_protection_names_match_case_insensitively_and_extras_are_ignored(self):
        missing = check_protection_measures(
            "mission-critical",
            ["Command-Verification", "ARM-AND-EXECUTE", "operator-confirmation"],
        )
        self.assertEqual(missing, [])

    def test_non_critical_command_demands_nothing(self):
        self.assertEqual(check_protection_measures("non-critical", []), [])

    def test_bad_level_and_protection_list_raise(self):
        with self.assertRaises(ValueError):
            check_protection_measures("super-critical", [])
        with self.assertRaises(ValueError):
            check_protection_measures("hazardous", "arm-and-execute")
        with self.assertRaises(ValueError):
            check_protection_measures("hazardous", ["arm-and-execute", "  "])


class AssessCommandTests(unittest.TestCase):
    def test_protected_hazardous_command_is_compliant(self):
        result = assess_command(
            command(
                id="TC-0900",
                effect="loss-of-vehicle",
                reversible=False,
                protections=[
                    "command-verification",
                    "arm-and-execute",
                    "command-authentication",
                    "inhibit-status-telemetry",
                ],
            )
        )
        self.assertEqual(result["retained_level"], "hazardous")
        self.assertTrue(result["compliant"])
        self.assertEqual(result["missing_protections"], [])

    def test_system_context_escalation_is_visible_next_to_the_equipment_claim(self):
        result = assess_command(
            command(
                id="TC-0200",
                effect="degraded-performance",
                system_context={"single_string_critical_function": True},
                protections=["command-verification"],
            )
        )
        self.assertEqual(result["equipment_level"], "mission-significant")
        self.assertEqual(result["system_level"], "mission-critical")
        self.assertTrue(result["escalated"])
        self.assertEqual(result["missing_protections"], ["arm-and-execute"])
        self.assertFalse(result["compliant"])

    def test_propagation_across_subsystems_raises_the_retained_level(self):
        result = assess_command(
            command(
                id="TC-0300",
                effect="loss-of-function",
                system_context={"subsystems_affected": 2},
                protections=["command-verification", "arm-and-execute"],
            )
        )
        self.assertEqual(result["equipment_level"], "mission-critical")
        self.assertEqual(result["retained_level"], "hazardous")
        self.assertEqual(
            result["missing_protections"],
            ["command-authentication", "inhibit-status-telemetry"],
        )

    def test_missing_system_context_raises(self):
        bare = command()
        del bare["system_context"]
        with self.assertRaises(ValueError):
            assess_command(bare)


class AssessCommandSetTests(unittest.TestCase):
    def test_set_summary_counts_levels_and_lists_the_gaps(self):
        benign = command(id="TC-0001")
        escalated = command(
            id="TC-0200",
            effect="degraded-performance",
            system_context={"single_string_critical_function": True},
            protections=["command-verification", "arm-and-execute"],
        )
        unsafe = command(
            id="TC-0900",
            effect="loss-of-vehicle",
            reversible=False,
            protections=["command-verification"],
        )
        summary = assess_command_set([benign, escalated, unsafe])
        self.assertEqual(summary["assessed"], 3)
        self.assertEqual(summary["level_counts"]["non-critical"], 1)
        self.assertEqual(summary["level_counts"]["mission-critical"], 1)
        self.assertEqual(summary["level_counts"]["hazardous"], 1)
        self.assertEqual(summary["escalated"], ["TC-0200"])
        self.assertEqual(summary["non_compliant"], ["TC-0900"])
        self.assertFalse(summary["all_compliant"])

    def test_fully_protected_set_is_compliant(self):
        summary = assess_command_set([command(id="TC-0001"), command(id="TC-0002")])
        self.assertTrue(summary["all_compliant"])
        self.assertEqual(summary["escalated"], [])

    def test_set_level_errors_raise(self):
        with self.assertRaises(ValueError):
            assess_command_set(command())
        with self.assertRaises(ValueError):
            assess_command_set([])
        with self.assertRaises(ValueError):
            assess_command_set([command(), command()])


if __name__ == "__main__":
    unittest.main()
