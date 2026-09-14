"""Contract tests for the clause 6.6.4 lowest-class programming-control logic."""

import unittest

from q6013_class_3_programmable_devices_logic import (
    BUDGET_TOLERANCE,
    CATEGORY_CONTROLS,
    COMMON_CONTROLS,
    DEFAULT_ENDURANCE_DERATING,
    DEVICE_CATEGORIES,
    FAMILY_CATEGORY,
    PROGRAMMING_VERDICTS,
    VERIFICATION_FLOOR,
    assess_programming_record,
    categorize_family,
    cycle_budget,
    open_controls,
    required_controls,
    validate_identifier,
    verification_coverage,
)


def otp_record(**overrides):
    """Return a clean one time programmable operation record."""
    base = {
        "reference": "PRG-OTP-1",
        "family": "antifuse-fpga",
        "controls_performed": list(
            required_controls("one-time-programmable")
        ),
        "pattern_identity": "PAT-4471-rev-B",
        "declared_checksum": "9f2ac1",
        "readback_checksum": "9F2AC1",
        "batch_size": 40,
        "verified_devices": 40,
        "cycles_used": 1,
    }
    base.update(overrides)
    return base


def flash_record(**overrides):
    """Return a clean reprogrammable non-volatile operation record."""
    base = {
        "reference": "PRG-FLH-1",
        "family": "flash-fpga",
        "controls_performed": list(
            required_controls("reprogrammable-non-volatile")
        ),
        "pattern_identity": "PAT-8802-rev-A",
        "declared_checksum": "0011ab",
        "readback_checksum": "0011ab",
        "batch_size": 20,
        "verified_devices": 20,
        "rated_cycles": 1000,
        "cycles_used": 120,
    }
    base.update(overrides)
    return base


def volatile_record(**overrides):
    """Return a clean reprogrammable volatile operation record."""
    base = {
        "reference": "PRG-SRM-1",
        "family": "sram-fpga",
        "controls_performed": list(
            required_controls("reprogrammable-volatile")
        ),
        "pattern_identity": "PAT-1200-rev-C",
        "declared_checksum": "abcd01",
        "readback_checksum": "abcd01",
        "batch_size": 8,
        "verified_devices": 2,
        "rated_cycles": 100000,
        "cycles_used": 40,
    }
    base.update(overrides)
    return base


class ValidateIdentifierTests(unittest.TestCase):
    def test_strips_surrounding_space(self):
        self.assertEqual(validate_identifier(" PRG-1 ", "reference"), "PRG-1")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("\n", "reference")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier(None, "reference")


class CategoryTests(unittest.TestCase):
    def test_antifuse_is_one_time(self):
        self.assertEqual(categorize_family("antifuse-fpga"), "one-time-programmable")

    def test_flash_is_reprogrammable_non_volatile(self):
        self.assertEqual(
            categorize_family("flash-memory"), "reprogrammable-non-volatile"
        )

    def test_sram_is_reprogrammable_volatile(self):
        self.assertEqual(categorize_family("SRAM-FPGA"), "reprogrammable-volatile")

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            categorize_family("mystery-array")

    def test_every_mapped_family_lands_in_the_published_set(self):
        self.assertTrue(
            set(FAMILY_CATEGORY.values()).issubset(set(DEVICE_CATEGORIES))
        )


class RequiredControlTests(unittest.TestCase):
    def test_common_controls_apply_to_every_category(self):
        for category in DEVICE_CATEGORIES:
            self.assertTrue(set(COMMON_CONTROLS).issubset(required_controls(category)))

    def test_category_controls_are_added(self):
        needed = required_controls("one-time-programmable")
        self.assertTrue(
            set(CATEGORY_CONTROLS["one-time-programmable"]).issubset(needed)
        )

    def test_required_set_is_sorted_and_unique(self):
        needed = required_controls("reprogrammable-non-volatile")
        self.assertEqual(list(needed), sorted(set(needed)))

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            required_controls("write-once-maybe")


class OpenControlTests(unittest.TestCase):
    def test_complete_record_leaves_nothing_open(self):
        needed = required_controls("reprogrammable-volatile")
        self.assertEqual(open_controls("reprogrammable-volatile", needed), ())

    def test_absent_control_is_named(self):
        needed = list(required_controls("one-time-programmable"))
        dropped = needed.pop()
        self.assertEqual(
            open_controls("one-time-programmable", needed), (dropped,)
        )

    def test_repeated_control_rejected(self):
        with self.assertRaises(ValueError):
            open_controls(
                "one-time-programmable",
                ["blank-verification", "blank-verification"],
            )

    def test_non_sequence_performed_set_rejected(self):
        with self.assertRaises(ValueError):
            open_controls("one-time-programmable", 12)


class VerificationCoverageTests(unittest.TestCase):
    def test_whole_batch_verified_is_unity(self):
        self.assertAlmostEqual(verification_coverage(40, 40), 1.0, places=9)

    def test_quarter_batch_verified_is_a_quarter(self):
        self.assertAlmostEqual(verification_coverage(2, 8), 0.25, places=9)

    def test_more_verified_than_built_rejected(self):
        with self.assertRaises(ValueError):
            verification_coverage(41, 40)

    def test_empty_batch_rejected(self):
        with self.assertRaises(ValueError):
            verification_coverage(0, 0)

    def test_negative_verified_count_rejected(self):
        with self.assertRaises(ValueError):
            verification_coverage(-1, 40)


class CycleBudgetTests(unittest.TestCase):
    def test_usable_cycles_are_the_derated_rating(self):
        budget = cycle_budget(1000, 0)
        self.assertAlmostEqual(budget["usable_cycles"], 500.0, places=9)

    def test_remaining_cycles_are_the_budget_less_the_spend(self):
        budget = cycle_budget(1000, 120)
        self.assertAlmostEqual(budget["remaining_cycles"], 380.0, places=9)

    def test_spend_landing_exactly_on_the_budget_counts_as_within(self):
        self.assertTrue(cycle_budget(1000, 500)["within_budget"])

    def test_spend_beyond_the_budget_is_outside(self):
        self.assertFalse(cycle_budget(1000, 501)["within_budget"])

    def test_declared_derating_overrides_the_default(self):
        budget = cycle_budget(1000, 0, 0.25)
        self.assertAlmostEqual(budget["usable_cycles"], 250.0, places=9)

    def test_zero_rating_rejected(self):
        with self.assertRaises(ValueError):
            cycle_budget(0, 0)

    def test_derating_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            cycle_budget(1000, 0, 1.5)

    def test_default_derating_is_a_fraction(self):
        self.assertLess(DEFAULT_ENDURANCE_DERATING, 1.0)


class AssessmentTests(unittest.TestCase):
    def test_clean_one_time_record_is_accepted(self):
        self.assertEqual(
            assess_programming_record(otp_record())["verdict"],
            "programming-record-accepted",
        )

    def test_clean_flash_record_is_accepted(self):
        self.assertEqual(
            assess_programming_record(flash_record())["verdict"],
            "programming-record-accepted",
        )

    def test_clean_volatile_record_is_accepted(self):
        self.assertEqual(
            assess_programming_record(volatile_record())["verdict"],
            "programming-record-accepted",
        )

    def test_missing_pattern_identity_refuses_the_record(self):
        self.assertEqual(
            assess_programming_record(otp_record(pattern_identity="  "))["verdict"],
            "refuse-unverified-pattern",
        )

    def test_readback_disagreement_refuses_the_record(self):
        self.assertEqual(
            assess_programming_record(
                otp_record(readback_checksum="deadbe")
            )["verdict"],
            "refuse-unverified-pattern",
        )

    def test_absent_readback_refuses_the_record(self):
        self.assertEqual(
            assess_programming_record(
                otp_record(readback_checksum=None)
            )["verdict"],
            "refuse-unverified-pattern",
        )

    def test_checksum_comparison_ignores_letter_case(self):
        self.assertTrue(assess_programming_record(otp_record())["checksums_agree"])

    def test_open_mandatory_control_escalates(self):
        performed = list(required_controls("one-time-programmable"))
        performed.remove("blank-verification")
        result = assess_programming_record(otp_record(controls_performed=performed))
        self.assertEqual(result["verdict"], "escalate-to-parts-control-board")

    def test_open_control_is_named_on_the_record(self):
        performed = list(required_controls("one-time-programmable"))
        performed.remove("blank-verification")
        result = assess_programming_record(otp_record(controls_performed=performed))
        self.assertEqual(result["open_controls"], ("blank-verification",))

    def test_open_advisory_control_is_accepted_with_the_control_named(self):
        performed = list(required_controls("reprogrammable-volatile"))
        performed.remove("configuration-scrub-provision")
        result = assess_programming_record(
            volatile_record(
                controls_performed=performed,
                advisory_controls=["configuration-scrub-provision"],
            )
        )
        self.assertEqual(result["verdict"], "accepted-with-open-advisory-control")

    def test_partial_verification_of_a_one_time_batch_escalates(self):
        result = assess_programming_record(otp_record(verified_devices=39))
        self.assertEqual(result["verdict"], "escalate-to-parts-control-board")

    def test_volatile_coverage_landing_on_its_floor_counts_as_met(self):
        result = assess_programming_record(
            volatile_record(batch_size=8, verified_devices=2)
        )
        self.assertTrue(result["verification_met"])

    def test_volatile_coverage_below_its_floor_escalates(self):
        result = assess_programming_record(
            volatile_record(batch_size=8, verified_devices=1)
        )
        self.assertEqual(result["verdict"], "escalate-to-parts-control-board")

    def test_exhausted_endurance_budget_escalates(self):
        result = assess_programming_record(flash_record(cycles_used=900))
        self.assertEqual(result["verdict"], "escalate-to-parts-control-board")

    def test_spend_landing_exactly_on_the_budget_stays_accepted(self):
        result = assess_programming_record(flash_record(cycles_used=500))
        self.assertEqual(result["verdict"], "programming-record-accepted")

    def test_one_time_device_programmed_twice_escalates(self):
        result = assess_programming_record(otp_record(cycles_used=2))
        self.assertEqual(result["verdict"], "escalate-to-parts-control-board")

    def test_unverified_pattern_outranks_an_open_control(self):
        performed = list(required_controls("one-time-programmable"))
        performed.remove("post-program-readback")
        result = assess_programming_record(
            otp_record(controls_performed=performed, pattern_identity="")
        )
        self.assertEqual(result["verdict"], "refuse-unverified-pattern")

    def test_findings_are_ordered_by_severity(self):
        performed = list(required_controls("one-time-programmable"))
        performed.remove("blank-verification")
        result = assess_programming_record(
            otp_record(controls_performed=performed, verified_devices=10)
        )
        severities = [item["severity"] for item in result["findings"]]
        self.assertEqual(severities, sorted(severities))

    def test_reprogrammable_record_without_a_rating_rejected(self):
        broken = flash_record()
        del broken["rated_cycles"]
        with self.assertRaises(ValueError):
            assess_programming_record(broken)

    def test_missing_batch_size_rejected(self):
        broken = otp_record()
        del broken["batch_size"]
        with self.assertRaises(ValueError):
            assess_programming_record(broken)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_programming_record(["PRG-1"])

    def test_unknown_family_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_programming_record(otp_record(family="guesswork-array"))

    def test_verdict_is_drawn_from_the_published_set(self):
        self.assertIn(
            assess_programming_record(flash_record())["verdict"],
            PROGRAMMING_VERDICTS,
        )

    def test_one_time_floor_is_the_whole_batch(self):
        self.assertAlmostEqual(
            VERIFICATION_FLOOR["one-time-programmable"], 1.0, places=9
        )

    def test_tolerance_is_representation_sized(self):
        self.assertLess(BUDGET_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
