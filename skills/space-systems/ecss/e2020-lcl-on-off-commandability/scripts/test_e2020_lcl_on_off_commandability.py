"""Contract tests for the clause 5.2.6.1.1 limiter on/off commandability logic."""

import unittest

from e2020_lcl_on_off_commandability_logic import (
    COMMANDABLE_CATEGORIES,
    COMMAND_NAMES,
    OUTPUT_STATES,
    PULSE_TOLERANCE_MS,
    apply_command,
    assess_commandability,
    command_admissible,
    next_state,
    normalise_category,
    normalise_command_name,
    normalise_state,
    pulse_margin_ms,
    run_sequence,
    validate_interface,
)

ALL_STATES = ["off", "on", "latched-off"]

# A channel that honours both commands from every output state, with a pulse
# comfortably above the 10 ms the channel accepts.
BASE = {
    "category": "latching",
    "min_pulse_width_ms": 10.0,
    "commands": [
        {
            "name": "on",
            "source": "external",
            "pulse_width_ms": 20.0,
            "authority": list(ALL_STATES),
        },
        {
            "name": "off",
            "source": "external",
            "pulse_width_ms": 20.0,
            "authority": list(ALL_STATES),
        },
    ],
}


def spec(**overrides):
    merged = {
        "category": BASE["category"],
        "min_pulse_width_ms": BASE["min_pulse_width_ms"],
        "commands": [dict(c, authority=list(c["authority"])) for c in BASE["commands"]],
    }
    merged.update(overrides)
    return merged


def with_command(name, **changes):
    commands = []
    for command in BASE["commands"]:
        entry = dict(command, authority=list(command["authority"]))
        if entry["name"] == name:
            entry.update(changes)
        commands.append(entry)
    return spec(commands=commands)


class NormalisationTests(unittest.TestCase):
    def test_category_aliases_are_folded(self):
        self.assertEqual(normalise_category("LCL"), "latching")
        self.assertEqual(normalise_category(" hpc "), "high-power")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            normalise_category("relay")

    def test_state_aliases_are_folded(self):
        self.assertEqual(normalise_state("tripped"), "latched-off")
        self.assertEqual(normalise_state("Latched"), "latched-off")

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            normalise_state("standby")

    def test_unknown_command_rejected(self):
        with self.assertRaises(ValueError):
            normalise_command_name("reset")

    def test_non_string_command_rejected(self):
        with self.assertRaises(ValueError):
            normalise_command_name(1)

    def test_command_and_state_vocabularies_are_fixed(self):
        self.assertEqual(COMMAND_NAMES, ("on", "off"))
        self.assertEqual(OUTPUT_STATES, ("off", "on", "latched-off"))
        self.assertEqual(COMMANDABLE_CATEGORIES, ("latching", "high-power"))


class InterfaceValidationTests(unittest.TestCase):
    def test_valid_interface_is_indexed_by_command_name(self):
        interface = validate_interface(spec())
        self.assertEqual(sorted(interface["commands"]), ["off", "on"])

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            validate_interface(["latching"])

    def test_missing_minimum_pulse_rejected(self):
        broken = spec()
        del broken["min_pulse_width_ms"]
        with self.assertRaises(ValueError):
            validate_interface(broken)

    def test_zero_minimum_pulse_rejected(self):
        with self.assertRaises(ValueError):
            validate_interface(spec(min_pulse_width_ms=0.0))

    def test_duplicate_command_rejected(self):
        duplicated = spec()
        duplicated["commands"].append(dict(duplicated["commands"][0]))
        with self.assertRaises(ValueError):
            validate_interface(duplicated)

    def test_unknown_source_rejected(self):
        with self.assertRaises(ValueError):
            validate_interface(with_command("on", source="telepathy"))

    def test_negative_pulse_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_interface(with_command("on", pulse_width_ms=-5.0))

    def test_boolean_pulse_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_interface(with_command("on", pulse_width_ms=True))

    def test_authority_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            validate_interface(with_command("off", authority="on"))

    def test_authority_state_is_normalised_and_deduplicated(self):
        interface = validate_interface(
            with_command("off", authority=["on", "tripped", "latched-off"])
        )
        self.assertEqual(interface["commands"]["off"]["authority"], ["on", "latched-off"])


class CommandMechanicsTests(unittest.TestCase):
    def test_pulse_margin_is_width_less_minimum(self):
        interface = validate_interface(spec())
        self.assertAlmostEqual(pulse_margin_ms(interface, "on"), 10.0, places=9)

    def test_pulse_exactly_on_the_minimum_is_accepted(self):
        interface = validate_interface(with_command("on", pulse_width_ms=10.0))
        self.assertAlmostEqual(pulse_margin_ms(interface, "on"), 0.0, places=9)
        accepted, _ = command_admissible(interface, "on", "off")
        self.assertTrue(accepted)

    def test_pulse_below_the_minimum_is_refused_with_a_reason(self):
        interface = validate_interface(with_command("on", pulse_width_ms=4.0))
        accepted, reason = command_admissible(interface, "on", "off")
        self.assertFalse(accepted)
        self.assertIn("below", reason)

    def test_internally_sourced_command_is_refused(self):
        interface = validate_interface(with_command("off", source="internal"))
        accepted, reason = command_admissible(interface, "off", "on")
        self.assertFalse(accepted)
        self.assertIn("internal", reason)

    def test_command_without_authority_in_the_state_is_refused(self):
        interface = validate_interface(with_command("off", authority=["on"]))
        accepted, reason = command_admissible(interface, "off", "latched-off")
        self.assertFalse(accepted)
        self.assertIn("authority", reason)

    def test_undeclared_command_is_refused(self):
        interface = validate_interface(spec(commands=[BASE["commands"][0]]))
        accepted, reason = command_admissible(interface, "off", "on")
        self.assertFalse(accepted)
        self.assertIn("not implemented", reason)

    def test_next_state_follows_the_command_not_the_current_state(self):
        self.assertEqual(next_state("latched-off", "on"), "on")
        self.assertEqual(next_state("on", "off"), "off")

    def test_refused_command_leaves_the_state_untouched(self):
        interface = validate_interface(with_command("on", source="internal"))
        after, record = apply_command(interface, "off", "on")
        self.assertEqual(after, "off")
        self.assertFalse(record["accepted"])

    def test_sequence_returns_one_record_per_command(self):
        interface = validate_interface(spec())
        final, trace = run_sequence(interface, "off", ["on", "off", "on"])
        self.assertEqual(final, "on")
        self.assertEqual(len(trace), 3)
        self.assertTrue(all(record["accepted"] for record in trace))

    def test_sequence_rejects_a_non_sequence_command_list(self):
        interface = validate_interface(spec())
        with self.assertRaises(ValueError):
            run_sequence(interface, "off", "on")


class AssessmentTests(unittest.TestCase):
    def test_fully_commandable_channel_is_compliant(self):
        result = assess_commandability(spec())
        self.assertEqual(result["verdict"], "compliant")
        self.assertTrue(result["commandable"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["ignored_commands"], [])

    def test_high_power_category_is_graded_the_same_way(self):
        result = assess_commandability(spec(category="high-power"))
        self.assertEqual(result["verdict"], "compliant")

    def test_missing_off_command_fails(self):
        result = assess_commandability(spec(commands=[BASE["commands"][0]]))
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertTrue(any("no off command" in f for f in result["findings"]))

    def test_internally_sourced_on_command_fails(self):
        result = assess_commandability(with_command("on", source="internal"))
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertTrue(any("outside the channel" in f for f in result["findings"]))

    def test_source_both_is_accepted_as_externally_reachable(self):
        result = assess_commandability(with_command("on", source="both"))
        self.assertEqual(result["verdict"], "compliant")

    def test_short_pulse_fails_and_names_the_minimum(self):
        result = assess_commandability(with_command("off", pulse_width_ms=2.0))
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertTrue(any("does not clear" in f for f in result["findings"]))

    def test_pulse_on_the_minimum_still_passes(self):
        result = assess_commandability(
            with_command("on", pulse_width_ms=10.0)
        )
        self.assertAlmostEqual(result["pulse_margins_ms"]["on"], 0.0, places=9)
        self.assertEqual(result["verdict"], "compliant")

    def test_channel_that_ignores_off_while_latched_fails(self):
        result = assess_commandability(with_command("off", authority=["on"]))
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertTrue(any("latched" in f for f in result["findings"]))
        self.assertEqual(result["latched_secure_final_state"], "latched-off")

    def test_channel_that_cannot_be_turned_on_again_after_a_trip_fails(self):
        result = assess_commandability(with_command("on", authority=["off", "on"]))
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertEqual(result["latched_restore_final_state"], "latched-off")
        self.assertEqual(result["latched_secure_final_state"], "off")

    def test_on_command_without_authority_from_off_fails(self):
        result = assess_commandability(
            with_command("on", authority=["on", "latched-off"])
        )
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertTrue(any("from the off state" in f for f in result["findings"]))

    def test_retriggerable_category_is_reported_out_of_scope(self):
        result = assess_commandability(spec(category="retriggerable"))
        self.assertEqual(result["verdict"], "out-of-scope")
        self.assertFalse(result["in_scope"])

    def test_traces_demonstrate_the_verdict(self):
        result = assess_commandability(spec())
        self.assertEqual(result["nominal_final_state"], "on")
        self.assertEqual(result["latched_secure_final_state"], "off")
        self.assertEqual(result["latched_restore_final_state"], "on")
        self.assertEqual(len(result["nominal_trace"]), 3)
        self.assertEqual(len(result["latched_secure_trace"]), 1)
        self.assertEqual(len(result["latched_restore_trace"]), 1)

    def test_securing_and_restoring_are_graded_from_the_latched_state_each(self):
        result = assess_commandability(with_command("on", authority=["off", "on"]))
        self.assertEqual(
            result["latched_restore_trace"][0]["state_before"], "latched-off"
        )
        self.assertFalse(result["latched_restore_trace"][0]["accepted"])

    def test_ignored_commands_are_listed(self):
        result = assess_commandability(with_command("off", authority=["on"]))
        self.assertIn("off", result["ignored_commands"])

    def test_pulse_tolerance_is_representation_sized(self):
        self.assertLess(PULSE_TOLERANCE_MS, 1e-6)


if __name__ == "__main__":
    unittest.main()
