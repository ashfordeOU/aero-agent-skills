"""Contract test for the actuator-electronics-telemetry-interfaces leaf."""

import unittest

from e2021_actuator_electronics_telemetry_interfaces_logic import (
    ACQUISITION_PATHS,
    CHAIN_NOMINAL,
    CHAIN_REDUNDANT,
    ELECTRONICS_CHAINS,
    FINDING_PARAMETER_ABSENT,
    FINDING_PATH_LOSS_BLINDS_CHAIN,
    FINDING_SINGLE_PATH_CHANNEL,
    FINDING_UNBUFFERED_FANOUT,
    PATH_NOMINAL,
    PATH_REDUNDANT,
    REQUIRED_PARAMETERS,
    absent_channels,
    assess_telemetry_interfaces,
    blinded_chains_after_path_loss,
    channel_key,
    dual_path_channels,
    observability_coverage,
    observable_after_path_loss,
    required_channels,
    single_path_channels,
    telemetry_findings,
    unbuffered_fanouts,
    validate_channel,
    validate_housekeeping,
)


def channel(parameter, chain, paths=None, **kw):
    record = {
        "parameter": parameter,
        "source_chain": chain,
        "acquisition_paths": list(paths if paths is not None else ACQUISITION_PATHS),
        "buffered": True,
    }
    record.update(kw)
    return record


def full_routing():
    return [
        channel(parameter, chain)
        for chain in ELECTRONICS_CHAINS
        for parameter in REQUIRED_PARAMETERS
    ]


def home_only_routing():
    home = {CHAIN_NOMINAL: PATH_NOMINAL, CHAIN_REDUNDANT: PATH_REDUNDANT}
    return [
        channel(parameter, chain, [home[chain]])
        for chain in ELECTRONICS_CHAINS
        for parameter in REQUIRED_PARAMETERS
    ]


class TestValidateChannel(unittest.TestCase):
    def test_buffered_defaults_to_true(self):
        record = channel("arm-status", CHAIN_NOMINAL)
        del record["buffered"]
        self.assertTrue(validate_channel(record)["buffered"])

    def test_paths_are_returned_in_canonical_order(self):
        record = channel("arm-status", CHAIN_NOMINAL, [PATH_REDUNDANT, PATH_NOMINAL])
        self.assertEqual(validate_channel(record)["acquisition_paths"], ACQUISITION_PATHS)

    def test_path_count_is_derived(self):
        self.assertEqual(
            validate_channel(channel("arm-status", CHAIN_NOMINAL, [PATH_NOMINAL]))["path_count"],
            1,
        )

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_channel(["arm-status"])

    def test_blank_parameter_raises(self):
        with self.assertRaises(ValueError):
            validate_channel(channel("  ", CHAIN_NOMINAL))

    def test_unknown_source_chain_raises(self):
        with self.assertRaises(ValueError):
            validate_channel(channel("arm-status", "third-electronics"))

    def test_empty_path_list_raises(self):
        with self.assertRaises(ValueError):
            validate_channel(channel("arm-status", CHAIN_NOMINAL, []))

    def test_non_sequence_path_list_raises(self):
        with self.assertRaises(ValueError):
            validate_channel(channel("arm-status", CHAIN_NOMINAL, PATH_NOMINAL))

    def test_unknown_path_raises(self):
        with self.assertRaises(ValueError):
            validate_channel(channel("arm-status", CHAIN_NOMINAL, ["ground-line"]))

    def test_repeated_path_raises(self):
        with self.assertRaises(ValueError):
            validate_channel(
                channel("arm-status", CHAIN_NOMINAL, [PATH_NOMINAL, PATH_NOMINAL])
            )

    def test_non_boolean_buffered_raises(self):
        with self.assertRaises(ValueError):
            validate_channel(channel("arm-status", CHAIN_NOMINAL, buffered="yes"))


class TestValidateHousekeeping(unittest.TestCase):
    def test_full_routing_normalizes(self):
        self.assertEqual(len(validate_housekeeping(full_routing())), 8)

    def test_empty_set_raises(self):
        with self.assertRaises(ValueError):
            validate_housekeeping([])

    def test_non_sequence_raises(self):
        with self.assertRaises(ValueError):
            validate_housekeeping(channel("arm-status", CHAIN_NOMINAL))

    def test_duplicate_channel_raises(self):
        routing = full_routing()
        routing.append(channel("arm-status", CHAIN_NOMINAL))
        with self.assertRaises(ValueError):
            validate_housekeeping(routing)

    def test_same_parameter_from_the_other_chain_is_not_a_duplicate(self):
        routing = [
            channel("arm-status", CHAIN_NOMINAL),
            channel("arm-status", CHAIN_REDUNDANT),
        ]
        self.assertEqual(len(validate_housekeeping(routing)), 2)


class TestCoverage(unittest.TestCase):
    def test_eight_channels_are_required(self):
        self.assertEqual(len(required_channels()), 8)

    def test_full_routing_is_complete(self):
        self.assertEqual(absent_channels(full_routing()), ())
        self.assertAlmostEqual(observability_coverage(full_routing()), 1.0, places=9)

    def test_missing_parameter_is_named_with_its_chain(self):
        routing = [
            c
            for c in full_routing()
            if not (c["parameter"] == "fire-status" and c["source_chain"] == CHAIN_REDUNDANT)
        ]
        self.assertEqual(absent_channels(routing), ((CHAIN_REDUNDANT, "fire-status"),))

    def test_home_only_routing_has_zero_dual_path_coverage(self):
        self.assertAlmostEqual(observability_coverage(home_only_routing()), 0.0, places=9)
        self.assertEqual(dual_path_channels(home_only_routing()), ())

    def test_partial_dual_path_routing_scores_a_fraction(self):
        routing = home_only_routing()
        routing[0]["acquisition_paths"] = list(ACQUISITION_PATHS)
        routing[1]["acquisition_paths"] = list(ACQUISITION_PATHS)
        self.assertAlmostEqual(observability_coverage(routing), 0.25, places=9)


class TestRouting(unittest.TestCase):
    def test_full_routing_has_no_single_path_channel(self):
        self.assertEqual(single_path_channels(full_routing()), ())

    def test_home_only_routing_is_all_single_path(self):
        self.assertEqual(len(single_path_channels(home_only_routing())), 8)

    def test_unbuffered_fanout_is_reported(self):
        routing = full_routing()
        routing[0]["buffered"] = False
        self.assertEqual(
            unbuffered_fanouts(routing), ((channel_key(validate_channel(routing[0]))),)
        )

    def test_unbuffered_single_path_channel_is_not_a_fanout_finding(self):
        routing = home_only_routing()
        routing[0]["buffered"] = False
        self.assertEqual(unbuffered_fanouts(routing), ())


class TestPathLoss(unittest.TestCase):
    def test_full_routing_survives_either_loss(self):
        for lost in ACQUISITION_PATHS:
            self.assertEqual(len(observable_after_path_loss(full_routing(), lost)), 8)
            self.assertEqual(blinded_chains_after_path_loss(full_routing(), lost), ())

    def test_home_only_routing_blinds_the_matching_chain(self):
        self.assertEqual(
            blinded_chains_after_path_loss(home_only_routing(), PATH_NOMINAL),
            (CHAIN_NOMINAL,),
        )
        self.assertEqual(
            blinded_chains_after_path_loss(home_only_routing(), PATH_REDUNDANT),
            (CHAIN_REDUNDANT,),
        )

    def test_home_only_routing_keeps_half_the_channels(self):
        self.assertEqual(
            len(observable_after_path_loss(home_only_routing(), PATH_NOMINAL)), 4
        )

    def test_unknown_lost_path_raises(self):
        with self.assertRaises(ValueError):
            observable_after_path_loss(full_routing(), "ground-line")


class TestFindings(unittest.TestCase):
    def test_full_routing_has_no_findings(self):
        self.assertEqual(telemetry_findings(full_routing()), [])

    def test_absent_parameter_raises_its_code(self):
        routing = [c for c in full_routing() if c["parameter"] != "firing-current-monitor"]
        codes = [f["code"] for f in telemetry_findings(routing)]
        self.assertIn(FINDING_PARAMETER_ABSENT, codes)

    def test_single_path_channel_raises_its_code(self):
        routing = full_routing()
        routing[0]["acquisition_paths"] = [PATH_NOMINAL]
        codes = [f["code"] for f in telemetry_findings(routing)]
        self.assertIn(FINDING_SINGLE_PATH_CHANNEL, codes)

    def test_unbuffered_fanout_raises_its_code(self):
        routing = full_routing()
        routing[3]["buffered"] = False
        codes = [f["code"] for f in telemetry_findings(routing)]
        self.assertIn(FINDING_UNBUFFERED_FANOUT, codes)

    def test_blinded_chain_raises_its_code(self):
        codes = [f["code"] for f in telemetry_findings(home_only_routing())]
        self.assertIn(FINDING_PATH_LOSS_BLINDS_CHAIN, codes)

    def test_findings_are_sorted_by_code_then_subject(self):
        routing = home_only_routing()
        routing[0]["buffered"] = False
        keys = [(f["code"], f["subject"]) for f in telemetry_findings(routing)]
        self.assertEqual(keys, sorted(keys))


class TestAssessment(unittest.TestCase):
    def test_full_routing_is_compliant(self):
        report = assess_telemetry_interfaces(full_routing())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["declared_channel_count"], 8)
        self.assertEqual(report["required_channel_count"], 8)
        self.assertAlmostEqual(report["observability_coverage"], 1.0, places=9)

    def test_home_only_routing_is_not_compliant(self):
        report = assess_telemetry_interfaces(home_only_routing())
        self.assertFalse(report["compliant"])
        self.assertEqual(report["blinded_chains"][PATH_NOMINAL], (CHAIN_NOMINAL,))
        self.assertIn(FINDING_SINGLE_PATH_CHANNEL, report["finding_codes"])
        self.assertIn(FINDING_PATH_LOSS_BLINDS_CHAIN, report["finding_codes"])

    def test_report_lists_the_observable_set_per_loss(self):
        report = assess_telemetry_interfaces(full_routing())
        for lost in ACQUISITION_PATHS:
            self.assertEqual(len(report["observable_after_loss"][lost]), 8)

    def test_missing_monitor_blocks_compliance(self):
        routing = [c for c in full_routing() if c["parameter"] != "firing-current-monitor"]
        report = assess_telemetry_interfaces(routing)
        self.assertFalse(report["compliant"])
        self.assertEqual(len(report["absent_channels"]), 2)
        self.assertAlmostEqual(report["observability_coverage"], 0.75, places=9)


if __name__ == "__main__":
    unittest.main()
