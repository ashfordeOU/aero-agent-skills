"""Contract test for the database-update-after-layout leaf (stdlib unittest)."""

import unittest

from e2040_database_update_after_layout_logic import (
    DESIGN_WIDE_KINDS,
    FINDING_DUPLICATE_DEPOSIT,
    FINDING_MISSING_DEPOSIT,
    FINDING_NO_CONFIGURATION_ID,
    FINDING_NO_DIGEST,
    FINDING_OUT_OF_PHASE_RUN,
    FINDING_SUPERSEDED_RUN,
    FINDING_UNEXPECTED_DEPOSIT,
    KIND_CONFIGURATION_BITSTREAM,
    KIND_LAYOUT_TIMING_DATA,
    KIND_PLACE_AND_ROUTE_RECORD,
    KIND_POST_LAYOUT_NETLIST,
    TECHNOLOGY_DEPENDENT_KINDS,
    assess_database_update_after_layout,
    check_deposit,
    completeness_fraction,
    is_programmable,
    owed_entries,
    validate_deposit,
    validate_device,
)


def device(kind="asic", technologies=("tech-a",), run=3, did="DEV-1"):
    return {
        "id": did,
        "kind": kind,
        "technologies": list(technologies),
        "closing_layout_run": run,
    }


def deposit(kind, technology=None, run=3, **kw):
    record = {
        "kind": kind,
        "technology": technology,
        "layout_run": run,
        "configuration_id": "CI-%s" % kind,
        "digest": "d41d8cd9",
    }
    record.update(kw)
    return record


def full_set(dev):
    return [
        deposit(kind, technology, run=dev["closing_layout_run"])
        for kind, technology in owed_entries(dev)
    ]


class TestValidateDevice(unittest.TestCase):
    def test_normalizes_a_good_record(self):
        norm = validate_device(device())
        self.assertEqual(norm["id"], "DEV-1")
        self.assertEqual(norm["technologies"], ["tech-a"])
        self.assertEqual(norm["closing_layout_run"], 3)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_device(["DEV-1"])

    def test_unknown_device_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_device(device(kind="breadboard"))

    def test_empty_technology_list_raises(self):
        with self.assertRaises(ValueError):
            validate_device(device(technologies=()))

    def test_duplicate_technology_raises(self):
        with self.assertRaises(ValueError):
            validate_device(device(technologies=("tech-a", "tech-a")))

    def test_negative_closing_run_raises(self):
        with self.assertRaises(ValueError):
            validate_device(device(run=-1))

    def test_blank_device_id_raises(self):
        with self.assertRaises(ValueError):
            validate_device(device(did="   "))


class TestOwedSet(unittest.TestCase):
    def test_asic_owes_no_bitstream(self):
        kinds = {kind for kind, _ in owed_entries(device(kind="asic"))}
        self.assertNotIn(KIND_CONFIGURATION_BITSTREAM, kinds)

    def test_fpga_owes_a_bitstream_per_technology(self):
        entries = owed_entries(device(kind="fpga", technologies=("t1", "t2")))
        bitstreams = [e for e in entries if e[0] == KIND_CONFIGURATION_BITSTREAM]
        self.assertEqual(sorted(t for _, t in bitstreams), ["t1", "t2"])

    def test_technology_dependent_kinds_scale_with_technology_count(self):
        one = owed_entries(device(technologies=("t1",)))
        two = owed_entries(device(technologies=("t1", "t2")))
        self.assertEqual(
            len(two) - len(one), len(TECHNOLOGY_DEPENDENT_KINDS)
        )

    def test_design_wide_kinds_are_owed_once(self):
        entries = owed_entries(device(technologies=("t1", "t2")))
        for kind in DESIGN_WIDE_KINDS:
            self.assertEqual([e for e in entries if e[0] == kind], [(kind, None)])

    def test_is_programmable_tracks_device_kind(self):
        self.assertTrue(is_programmable(device(kind="fpga")))
        self.assertFalse(is_programmable(device(kind="asic")))
        self.assertFalse(is_programmable(device(kind="ip-core")))


class TestValidateDeposit(unittest.TestCase):
    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_deposit(deposit("floorplan-sketch", "tech-a"), device())

    def test_technology_dependent_kind_without_technology_raises(self):
        with self.assertRaises(ValueError):
            validate_deposit(deposit(KIND_POST_LAYOUT_NETLIST), device())

    def test_undeclared_technology_raises(self):
        with self.assertRaises(ValueError):
            validate_deposit(
                deposit(KIND_POST_LAYOUT_NETLIST, "tech-z"), device()
            )

    def test_design_wide_kind_with_technology_raises(self):
        with self.assertRaises(ValueError):
            validate_deposit(
                deposit(DESIGN_WIDE_KINDS[0], "tech-a"), device()
            )

    def test_non_integer_layout_run_raises(self):
        with self.assertRaises(ValueError):
            validate_deposit(
                deposit(KIND_POST_LAYOUT_NETLIST, "tech-a", run=1.5), device()
            )

    def test_blank_digest_raises(self):
        with self.assertRaises(ValueError):
            validate_deposit(
                deposit(KIND_POST_LAYOUT_NETLIST, "tech-a", digest="  "), device()
            )


class TestCheckDeposit(unittest.TestCase):
    def test_clean_deposit_has_no_findings(self):
        self.assertEqual(
            check_deposit(deposit(KIND_POST_LAYOUT_NETLIST, "tech-a"), device()), []
        )

    def test_earlier_run_is_superseded(self):
        self.assertIn(
            FINDING_SUPERSEDED_RUN,
            check_deposit(
                deposit(KIND_POST_LAYOUT_NETLIST, "tech-a", run=2), device()
            ),
        )

    def test_later_run_is_out_of_phase(self):
        self.assertIn(
            FINDING_OUT_OF_PHASE_RUN,
            check_deposit(
                deposit(KIND_POST_LAYOUT_NETLIST, "tech-a", run=4), device()
            ),
        )

    def test_missing_configuration_id_is_a_finding(self):
        self.assertIn(
            FINDING_NO_CONFIGURATION_ID,
            check_deposit(
                deposit(KIND_LAYOUT_TIMING_DATA, "tech-a", configuration_id=None),
                device(),
            ),
        )

    def test_missing_digest_is_a_finding(self):
        self.assertIn(
            FINDING_NO_DIGEST,
            check_deposit(
                deposit(KIND_PLACE_AND_ROUTE_RECORD, "tech-a", digest=None),
                device(),
            ),
        )


class TestCompletenessFraction(unittest.TestCase):
    def test_full_set_is_exactly_one(self):
        self.assertAlmostEqual(completeness_fraction(7, 7), 1.0, places=9)

    def test_half_set(self):
        self.assertAlmostEqual(completeness_fraction(3, 6), 0.5, places=9)

    def test_zero_owed_raises(self):
        with self.assertRaises(ValueError):
            completeness_fraction(0, 0)

    def test_satisfied_above_owed_raises(self):
        with self.assertRaises(ValueError):
            completeness_fraction(8, 7)


class TestAssessment(unittest.TestCase):
    def test_complete_asic_repository_may_proceed(self):
        dev = device(kind="asic")
        report = assess_database_update_after_layout(dev, full_set(dev))
        self.assertTrue(report["may_proceed"])
        self.assertEqual(report["findings"], [])
        self.assertAlmostEqual(report["completeness"], 1.0, places=9)

    def test_missing_item_is_a_named_gap(self):
        dev = device(kind="asic")
        deposits = [
            d for d in full_set(dev) if d["kind"] != KIND_LAYOUT_TIMING_DATA
        ]
        report = assess_database_update_after_layout(dev, deposits)
        self.assertFalse(report["may_proceed"])
        self.assertIn((KIND_LAYOUT_TIMING_DATA, "tech-a"), report["gaps"])
        self.assertIn(
            ((KIND_LAYOUT_TIMING_DATA, "tech-a"), FINDING_MISSING_DEPOSIT),
            report["findings"],
        )

    def test_single_netlist_does_not_cover_two_technologies(self):
        dev = device(kind="asic", technologies=("t1", "t2"))
        deposits = [
            d
            for d in full_set(dev)
            if not (d["kind"] == KIND_POST_LAYOUT_NETLIST and d["technology"] == "t2")
        ]
        report = assess_database_update_after_layout(dev, deposits)
        self.assertIn((KIND_POST_LAYOUT_NETLIST, "t2"), report["gaps"])

    def test_duplicate_deposit_is_a_finding(self):
        dev = device(kind="asic")
        deposits = full_set(dev)
        deposits.append(deposit(KIND_POST_LAYOUT_NETLIST, "tech-a"))
        report = assess_database_update_after_layout(dev, deposits)
        self.assertIn(
            ((KIND_POST_LAYOUT_NETLIST, "tech-a"), FINDING_DUPLICATE_DEPOSIT),
            report["findings"],
        )

    def test_bitstream_for_an_asic_is_unexpected(self):
        dev = device(kind="asic")
        deposits = full_set(dev)
        deposits.append(deposit(KIND_CONFIGURATION_BITSTREAM, "tech-a"))
        report = assess_database_update_after_layout(dev, deposits)
        self.assertIn((KIND_CONFIGURATION_BITSTREAM, "tech-a"), report["unexpected"])
        self.assertIn(
            ((KIND_CONFIGURATION_BITSTREAM, "tech-a"), FINDING_UNEXPECTED_DEPOSIT),
            report["findings"],
        )

    def test_superseded_deposit_does_not_count_towards_completeness(self):
        dev = device(kind="asic")
        deposits = []
        for item in full_set(dev):
            if item["kind"] == KIND_POST_LAYOUT_NETLIST:
                item = dict(item, layout_run=1)
            deposits.append(item)
        report = assess_database_update_after_layout(dev, deposits)
        self.assertEqual(report["satisfied_count"], report["owed_count"] - 1)
        self.assertFalse(report["may_proceed"])

    def test_fpga_full_set_may_proceed(self):
        dev = device(kind="fpga", technologies=("t1", "t2"))
        report = assess_database_update_after_layout(dev, full_set(dev))
        self.assertTrue(report["may_proceed"])
        self.assertEqual(report["owed_count"], len(DESIGN_WIDE_KINDS) + 2 * 4)

    def test_non_list_deposits_raises(self):
        with self.assertRaises(ValueError):
            assess_database_update_after_layout(device(), deposit(KIND_POST_LAYOUT_NETLIST, "tech-a"))

    def test_empty_repository_reports_zero_completeness(self):
        dev = device(kind="asic")
        report = assess_database_update_after_layout(dev, [])
        self.assertAlmostEqual(report["completeness"], 0.0, places=9)
        self.assertEqual(len(report["gaps"]), report["owed_count"])


if __name__ == "__main__":
    unittest.main()
