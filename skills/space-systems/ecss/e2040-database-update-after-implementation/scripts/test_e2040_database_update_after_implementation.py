"""Contract test for the database-update-after-implementation leaf."""

import unittest

from e2040_database_update_after_implementation_logic import (
    BASELINE_KIND_FROZEN_TAG,
    BASELINE_KIND_MOVING_BRANCH,
    FINDING_DIGEST_MISMATCH,
    FINDING_DIGEST_UNPROVEN,
    FINDING_MISSING_DEPOSIT,
    FINDING_NOT_FROZEN,
    FINDING_NO_RUN_PARAMETERS,
    FINDING_NO_TOOLCHAIN_RECORD,
    FINDING_TWO_ACTIVE_DEPOSITS,
    FINDING_UNEXPECTED_DEPOSIT,
    KIND_FINAL_NETLIST,
    KIND_FINAL_PROGRAMMING_FILE,
    KIND_IMPLEMENTATION_REPORT,
    KIND_PRODUCTION_TEST_PROGRAM,
    STATE_RETIRED,
    assess_database_update_after_implementation,
    check_deposit,
    completeness_fraction,
    digest_findings,
    freeze_findings,
    is_loaded_implementation,
    owed_as_built_entries,
    validate_deposit,
    validate_device,
)


def device(kind="fpga", technologies=("tech-a",), did="DEV-1"):
    return {"id": did, "kind": kind, "technologies": list(technologies)}


def deposit(kind, technology="tech-a", **kw):
    record = {
        "kind": kind,
        "technology": technology,
        "baseline_label": "BL-1.0",
        "baseline_kind": BASELINE_KIND_FROZEN_TAG,
        "state": "active",
        "deposited_digest": "9f86d081",
        "read_back_digest": "9f86d081",
        "toolchain_version": "impl-tool-2024.3",
        "deterministic": True,
        "run_parameter_count": 0,
    }
    record.update(kw)
    return record


def full_set(dev):
    return [deposit(kind, technology) for kind, technology in owed_as_built_entries(dev)]


class TestValidateDevice(unittest.TestCase):
    def test_normalizes_a_good_record(self):
        self.assertEqual(validate_device(device())["technologies"], ["tech-a"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_device("DEV-1")

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_device(device(kind="protoboard"))

    def test_empty_technologies_raises(self):
        with self.assertRaises(ValueError):
            validate_device(device(technologies=()))

    def test_duplicate_technology_raises(self):
        with self.assertRaises(ValueError):
            validate_device(device(technologies=("tech-a", "tech-a")))


class TestOwedSet(unittest.TestCase):
    def test_loaded_device_owes_a_programming_file(self):
        kinds = {kind for kind, _ in owed_as_built_entries(device(kind="fpga"))}
        self.assertIn(KIND_FINAL_PROGRAMMING_FILE, kinds)

    def test_fabricated_device_does_not(self):
        kinds = {kind for kind, _ in owed_as_built_entries(device(kind="asic"))}
        self.assertNotIn(KIND_FINAL_PROGRAMMING_FILE, kinds)

    def test_entries_scale_with_technology_count(self):
        one = owed_as_built_entries(device(technologies=("t1",)))
        two = owed_as_built_entries(device(technologies=("t1", "t2")))
        self.assertEqual(len(two), 2 * len(one))

    def test_is_loaded_implementation_tracks_device_kind(self):
        self.assertTrue(is_loaded_implementation(device(kind="fpga")))
        self.assertFalse(is_loaded_implementation(device(kind="asic")))


class TestValidateDeposit(unittest.TestCase):
    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_deposit(deposit("layout-sketch"), device())

    def test_undeclared_technology_raises(self):
        with self.assertRaises(ValueError):
            validate_deposit(deposit(KIND_FINAL_NETLIST, "tech-z"), device())

    def test_blank_baseline_label_raises(self):
        with self.assertRaises(ValueError):
            validate_deposit(deposit(KIND_FINAL_NETLIST, baseline_label="  "), device())

    def test_unknown_state_raises(self):
        with self.assertRaises(ValueError):
            validate_deposit(deposit(KIND_FINAL_NETLIST, state="archived-ish"), device())

    def test_unknown_baseline_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_deposit(deposit(KIND_FINAL_NETLIST, baseline_kind="sticky-note"), device())

    def test_negative_run_parameter_count_raises(self):
        with self.assertRaises(ValueError):
            validate_deposit(deposit(KIND_FINAL_NETLIST, run_parameter_count=-1), device())

    def test_non_boolean_deterministic_raises(self):
        with self.assertRaises(ValueError):
            validate_deposit(deposit(KIND_FINAL_NETLIST, deterministic="mostly"), device())


class TestDigestFindings(unittest.TestCase):
    def test_matching_digests_are_clean(self):
        self.assertEqual(digest_findings(deposit(KIND_FINAL_PROGRAMMING_FILE), device()), [])

    def test_mismatch_is_a_finding(self):
        self.assertEqual(
            digest_findings(
                deposit(KIND_FINAL_PROGRAMMING_FILE, read_back_digest="deadbeef"),
                device(),
            ),
            [FINDING_DIGEST_MISMATCH],
        )

    def test_absent_read_back_is_unproven(self):
        self.assertEqual(
            digest_findings(
                deposit(KIND_FINAL_PROGRAMMING_FILE, read_back_digest=None), device()
            ),
            [FINDING_DIGEST_UNPROVEN],
        )

    def test_non_loaded_kind_carries_no_digest_obligation(self):
        self.assertEqual(
            digest_findings(
                deposit(KIND_IMPLEMENTATION_REPORT, deposited_digest=None,
                        read_back_digest=None),
                device(),
            ),
            [],
        )


class TestFreezeFindings(unittest.TestCase):
    def test_frozen_and_recorded_is_clean(self):
        self.assertEqual(freeze_findings(deposit(KIND_FINAL_NETLIST), device()), [])

    def test_moving_branch_is_a_finding(self):
        self.assertIn(
            FINDING_NOT_FROZEN,
            freeze_findings(
                deposit(KIND_FINAL_NETLIST, baseline_kind=BASELINE_KIND_MOVING_BRANCH),
                device(),
            ),
        )

    def test_missing_toolchain_is_a_finding(self):
        self.assertIn(
            FINDING_NO_TOOLCHAIN_RECORD,
            freeze_findings(deposit(KIND_FINAL_NETLIST, toolchain_version=None), device()),
        )

    def test_non_deterministic_without_parameters_is_a_finding(self):
        self.assertIn(
            FINDING_NO_RUN_PARAMETERS,
            freeze_findings(deposit(KIND_FINAL_NETLIST, deterministic=False), device()),
        )

    def test_non_deterministic_with_parameters_is_clean(self):
        self.assertEqual(
            freeze_findings(
                deposit(KIND_FINAL_NETLIST, deterministic=False, run_parameter_count=3),
                device(),
            ),
            [],
        )

    def test_check_deposit_combines_both_families(self):
        findings = check_deposit(
            deposit(
                KIND_FINAL_PROGRAMMING_FILE,
                read_back_digest="deadbeef",
                toolchain_version=None,
            ),
            device(),
        )
        self.assertIn(FINDING_DIGEST_MISMATCH, findings)
        self.assertIn(FINDING_NO_TOOLCHAIN_RECORD, findings)


class TestCompletenessFraction(unittest.TestCase):
    def test_full_set_is_one(self):
        self.assertAlmostEqual(completeness_fraction(4, 4), 1.0, places=9)

    def test_quarter_set(self):
        self.assertAlmostEqual(completeness_fraction(1, 4), 0.25, places=9)

    def test_zero_owed_raises(self):
        with self.assertRaises(ValueError):
            completeness_fraction(0, 0)

    def test_satisfied_above_owed_raises(self):
        with self.assertRaises(ValueError):
            completeness_fraction(5, 4)


class TestAssessment(unittest.TestCase):
    def test_complete_as_built_set_closes_the_phase(self):
        dev = device(kind="fpga")
        report = assess_database_update_after_implementation(dev, full_set(dev))
        self.assertTrue(report["phase_may_close"])
        self.assertAlmostEqual(report["completeness"], 1.0, places=9)
        self.assertTrue(report["digest_proven"][(KIND_FINAL_PROGRAMMING_FILE, "tech-a")])

    def test_missing_item_is_a_gap(self):
        dev = device(kind="fpga")
        deposits = [d for d in full_set(dev) if d["kind"] != KIND_PRODUCTION_TEST_PROGRAM]
        report = assess_database_update_after_implementation(dev, deposits)
        self.assertIn((KIND_PRODUCTION_TEST_PROGRAM, "tech-a"), report["gaps"])
        self.assertIn(
            ((KIND_PRODUCTION_TEST_PROGRAM, "tech-a"), FINDING_MISSING_DEPOSIT),
            report["findings"],
        )

    def test_digest_mismatch_blocks_the_phase(self):
        dev = device(kind="fpga")
        deposits = []
        for item in full_set(dev):
            if item["kind"] == KIND_FINAL_PROGRAMMING_FILE:
                item = dict(item, read_back_digest="deadbeef")
            deposits.append(item)
        report = assess_database_update_after_implementation(dev, deposits)
        self.assertFalse(report["phase_may_close"])
        self.assertFalse(report["digest_proven"][(KIND_FINAL_PROGRAMMING_FILE, "tech-a")])

    def test_two_active_deposits_for_one_entry_is_a_finding(self):
        dev = device(kind="asic")
        deposits = full_set(dev)
        deposits.append(deposit(KIND_FINAL_NETLIST, baseline_label="BL-1.1"))
        report = assess_database_update_after_implementation(dev, deposits)
        self.assertIn(
            ((KIND_FINAL_NETLIST, "tech-a"), FINDING_TWO_ACTIVE_DEPOSITS),
            report["findings"],
        )

    def test_retired_duplicate_is_listed_and_does_not_block(self):
        dev = device(kind="asic")
        deposits = full_set(dev)
        deposits.append(
            deposit(KIND_FINAL_NETLIST, baseline_label="BL-0.9", state=STATE_RETIRED)
        )
        report = assess_database_update_after_implementation(dev, deposits)
        self.assertTrue(report["phase_may_close"])
        self.assertIn(((KIND_FINAL_NETLIST, "tech-a"), "BL-0.9"), report["retired"])

    def test_programming_file_for_a_fabricated_device_is_unexpected(self):
        dev = device(kind="asic")
        deposits = full_set(dev)
        deposits.append(deposit(KIND_FINAL_PROGRAMMING_FILE))
        report = assess_database_update_after_implementation(dev, deposits)
        self.assertIn((KIND_FINAL_PROGRAMMING_FILE, "tech-a"), report["unexpected"])
        self.assertIn(
            ((KIND_FINAL_PROGRAMMING_FILE, "tech-a"), FINDING_UNEXPECTED_DEPOSIT),
            report["findings"],
        )

    def test_second_technology_owes_its_own_set(self):
        dev = device(kind="fpga", technologies=("t1", "t2"))
        deposits = [d for d in full_set(dev) if d["technology"] == "t1"]
        report = assess_database_update_after_implementation(dev, deposits)
        self.assertAlmostEqual(report["completeness"], 0.5, places=9)

    def test_empty_repository_reports_zero_completeness(self):
        dev = device(kind="fpga")
        report = assess_database_update_after_implementation(dev, [])
        self.assertAlmostEqual(report["completeness"], 0.0, places=9)
        self.assertEqual(len(report["gaps"]), report["owed_count"])

    def test_non_list_deposits_raises(self):
        with self.assertRaises(ValueError):
            assess_database_update_after_implementation(
                device(), deposit(KIND_FINAL_NETLIST)
            )


if __name__ == "__main__":
    unittest.main()
