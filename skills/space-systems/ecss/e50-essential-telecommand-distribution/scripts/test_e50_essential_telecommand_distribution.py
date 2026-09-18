#!/usr/bin/env python3
"""Gate 3 contract test for e50-essential-telecommand-distribution.

stdlib unittest, offline, deterministic. Run:
    python3 test_e50_essential_telecommand_distribution.py
"""

import unittest

from e50_essential_telecommand_distribution_logic import (
    AVAILABLE_IN_ALL_MODES,
    FULLY_DISTRIBUTED,
    HARDWARE_DECODED,
    NOT_DISTRIBUTED,
    OBLIGATIONS,
    PARTIALLY_DISTRIBUTED,
    SEGREGATED,
    WITHIN_LATENCY,
    assess_distribution,
    assess_essential_command,
    check_hardware_decoded,
    check_latency,
    check_mode_availability,
    check_segregation,
    missing_modes,
    validate_essential_command,
    validate_required_modes,
    within_latency,
)

MODES = ("nominal", "safe", "survival")


def command(
    identifier="hpc-pyro-arm",
    hardware=True,
    shared=(),
    modes=MODES,
    delivery=0.5,
    specified=2.0,
):
    return {
        "id": identifier,
        "decoded_in_hardware": hardware,
        "shared_failure_points": list(shared),
        "available_modes": list(modes),
        "delivery_latency_s": delivery,
        "specified_latency_s": specified,
    }


class TestValidation(unittest.TestCase):
    def test_a_well_formed_command_is_normalized(self):
        record = validate_essential_command(command())
        self.assertEqual(record["id"], "hpc-pyro-arm")
        self.assertAlmostEqual(record["delivery_latency_s"], 0.5, places=9)

    def test_a_missing_key_is_rejected(self):
        broken = command()
        del broken["available_modes"]
        with self.assertRaises(ValueError):
            validate_essential_command(broken)

    def test_a_string_in_place_of_a_mode_list_is_rejected(self):
        broken = command()
        broken["available_modes"] = "safe"
        with self.assertRaises(ValueError):
            validate_essential_command(broken)

    def test_an_integer_standing_in_for_a_flag_is_rejected(self):
        broken = command()
        broken["decoded_in_hardware"] = 1
        with self.assertRaises(ValueError):
            validate_essential_command(broken)

    def test_a_negative_latency_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_essential_command(command(delivery=-1.0))

    def test_an_empty_required_mode_set_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_required_modes([])

    def test_a_blank_mode_name_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_required_modes(["nominal", "  "])


class TestObligations(unittest.TestCase):
    def test_a_hardware_decoded_route_satisfies_the_first_obligation(self):
        self.assertTrue(check_hardware_decoded(command()))

    def test_a_software_decoded_route_fails_the_first_obligation(self):
        self.assertFalse(check_hardware_decoded(command(hardware=False)))

    def test_a_route_with_no_shared_point_is_segregated(self):
        self.assertTrue(check_segregation(command()))

    def test_a_route_sharing_a_decoder_is_not_segregated(self):
        self.assertFalse(check_segregation(command(shared=("tc-decoder-a",))))

    def test_a_route_present_in_every_required_mode_passes(self):
        self.assertTrue(check_mode_availability(command(), MODES))

    def test_a_route_absent_in_survival_mode_fails(self):
        self.assertFalse(
            check_mode_availability(command(modes=("nominal", "safe")), MODES)
        )

    def test_the_absent_modes_are_named(self):
        self.assertEqual(
            missing_modes(command(modes=("nominal",)), MODES), ("safe", "survival")
        )

    def test_a_route_inside_its_budget_passes_the_latency_obligation(self):
        self.assertTrue(check_latency(command(delivery=0.5, specified=2.0)))

    def test_a_route_landing_exactly_on_its_budget_still_passes(self):
        self.assertTrue(within_latency(2.0, 2.0))

    def test_a_route_past_its_budget_fails(self):
        self.assertFalse(within_latency(2.5, 2.0))

    def test_extra_modes_beyond_the_required_set_do_no_harm(self):
        record = command(modes=MODES + ("commissioning",))
        self.assertTrue(check_mode_availability(record, MODES))


class TestSingleCommand(unittest.TestCase):
    def test_a_clean_command_satisfies_all_four_obligations(self):
        report = assess_essential_command(command(), MODES)
        self.assertTrue(report["distributed"])
        self.assertEqual(len(report["satisfied"]), len(OBLIGATIONS))
        self.assertEqual(report["findings"], [])

    def test_a_software_decoded_command_names_the_first_obligation(self):
        report = assess_essential_command(command(hardware=False), MODES)
        self.assertIn(HARDWARE_DECODED, report["failed"])
        self.assertTrue(any("flight software" in f for f in report["findings"]))

    def test_a_shared_failure_point_names_the_second_obligation(self):
        report = assess_essential_command(command(shared=("power-rail-a",)), MODES)
        self.assertIn(SEGREGATED, report["failed"])
        self.assertTrue(any("power-rail-a" in f for f in report["findings"]))

    def test_a_missing_mode_names_the_third_obligation(self):
        report = assess_essential_command(command(modes=("nominal",)), MODES)
        self.assertIn(AVAILABLE_IN_ALL_MODES, report["failed"])
        self.assertEqual(report["missing_modes"], ("safe", "survival"))

    def test_a_slow_route_names_the_fourth_obligation(self):
        report = assess_essential_command(command(delivery=9.0, specified=2.0), MODES)
        self.assertIn(WITHIN_LATENCY, report["failed"])

    def test_four_defects_produce_four_findings(self):
        report = assess_essential_command(
            command(
                hardware=False,
                shared=("obc-a",),
                modes=("nominal",),
                delivery=9.0,
                specified=2.0,
            ),
            MODES,
        )
        self.assertEqual(len(report["findings"]), 4)
        self.assertEqual(report["satisfied"], ())


class TestArchitecture(unittest.TestCase):
    def test_an_all_clean_architecture_is_fully_distributed(self):
        report = assess_distribution(
            [command("hpc-a"), command("hpc-b")], MODES
        )
        self.assertEqual(report["verdict"], FULLY_DISTRIBUTED)
        self.assertTrue(report["compliant"])
        self.assertAlmostEqual(report["coverage_fraction"], 1.0, places=9)

    def test_one_defective_command_makes_it_partial(self):
        report = assess_distribution(
            [command("hpc-a"), command("hpc-b", hardware=False)], MODES
        )
        self.assertEqual(report["verdict"], PARTIALLY_DISTRIBUTED)
        self.assertAlmostEqual(report["coverage_fraction"], 0.5, places=9)

    def test_an_architecture_with_no_clean_command_is_not_distributed(self):
        report = assess_distribution(
            [command("hpc-a", hardware=False), command("hpc-b", modes=("nominal",))],
            MODES,
        )
        self.assertEqual(report["verdict"], NOT_DISTRIBUTED)
        self.assertEqual(report["distributed_count"], 0)

    def test_failures_are_grouped_by_obligation(self):
        report = assess_distribution(
            [command("hpc-a", hardware=False), command("hpc-b", shared=("obc-a",))],
            MODES,
        )
        self.assertEqual(report["failures_by_obligation"][HARDWARE_DECODED], ("hpc-a",))
        self.assertEqual(report["failures_by_obligation"][SEGREGATED], ("hpc-b",))

    def test_duplicate_command_identifiers_are_rejected(self):
        with self.assertRaises(ValueError):
            assess_distribution([command("hpc-a"), command("hpc-a")], MODES)

    def test_an_empty_architecture_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_distribution([], MODES)

    def test_the_required_modes_are_carried_into_the_report(self):
        report = assess_distribution([command("hpc-a")], MODES)
        self.assertEqual(report["required_modes"], ("nominal", "safe", "survival"))


if __name__ == "__main__":
    unittest.main()
