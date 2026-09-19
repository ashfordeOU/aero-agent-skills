"""Contract test for the e3311 transfer devices leaf (stdlib unittest)."""

import copy
import unittest

from e3311_transfer_devices_logic import (
    DEFAULT_TRANSFER_POLICY,
    VERDICT_MET,
    VERDICT_NOT_MET,
    assess_transfer_train,
    branch_arrival_time_s,
    gap_margin,
    interface_verdict,
    segment_transit_time_s,
    segment_verdict,
    simultaneity_verdict,
    temperature_verdict,
    validate_interface,
    validate_segment,
    validate_train,
    validate_transfer_policy,
)


def segment(sid="MDF-PORT", **kw):
    record = {
        "id": sid,
        "kind": "detonation-transfer-line",
        "length_m": 1.400,
        "propagation_velocity_m_s": 7000.0,
        "core_load_g_per_m": 1.50,
        "min_propagating_core_load_g_per_m": 1.00,
        "min_bend_radius_mm": 25.0,
        "installed_bend_radius_mm": 60.0,
    }
    record.update(kw)
    return record


def interface(iid="TBI-1", **kw):
    record = {
        "id": iid,
        "through_bulkhead": False,
        "design_gap_mm": 1.00,
        "max_transfer_gap_mm": 4.00,
        "delay_s": 0.0,
    }
    record.update(kw)
    return record


def bulkhead_interface(iid="TBI-1", **kw):
    record = interface(
        iid,
        through_bulkhead=True,
        bulkhead_proof_pressure_mpa=120.0,
        peak_transfer_pressure_mpa=40.0,
        seal_retained=True,
    )
    record.update(kw)
    return record


def train(**kw):
    record = {
        "id": "SEP-TRAIN",
        "qualified_min_temperature_k": 213.0,
        "qualified_max_temperature_k": 353.0,
        "segments": [
            segment("MDF-PORT", length_m=1.400),
            segment("MDF-STBD", length_m=1.400),
        ],
        "interfaces": [bulkhead_interface("TBI-1"), interface("XFER-2")],
        "branches": [
            {"id": "PORT", "segments": ["MDF-PORT"], "interfaces": ["TBI-1"]},
            {"id": "STBD", "segments": ["MDF-STBD"], "interfaces": ["XFER-2"]},
        ],
    }
    record.update(kw)
    return copy.deepcopy(record)


def case(**kw):
    record = {
        "predicted_min_temperature_k": 233.0,
        "predicted_max_temperature_k": 333.0,
    }
    record.update(kw)
    return record


class TestPolicyValidation(unittest.TestCase):
    def test_default_policy_is_valid(self):
        self.assertIs(
            validate_transfer_policy(DEFAULT_TRANSFER_POLICY),
            DEFAULT_TRANSFER_POLICY,
        )

    def test_a_non_mapping_policy_raises(self):
        with self.assertRaises(ValueError):
            validate_transfer_policy(["min_gap_margin", 2.0])

    def test_a_gap_margin_below_unity_raises(self):
        with self.assertRaises(ValueError):
            validate_transfer_policy(
                dict(DEFAULT_TRANSFER_POLICY, min_gap_margin=0.8)
            )

    def test_a_zero_simultaneity_limit_raises(self):
        with self.assertRaises(ValueError):
            validate_transfer_policy(
                dict(DEFAULT_TRANSFER_POLICY, max_simultaneity_spread_s=0.0)
            )


class TestRecordValidation(unittest.TestCase):
    def test_a_valid_segment_normalizes(self):
        record = validate_segment(segment())
        self.assertEqual(record["kind"], "detonation-transfer-line")

    def test_an_unknown_line_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_segment(segment(kind="pyro-rope"))

    def test_a_zero_propagation_velocity_raises(self):
        with self.assertRaises(ValueError):
            validate_segment(segment(propagation_velocity_m_s=0.0))

    def test_a_bulkhead_interface_without_a_seal_declaration_raises(self):
        record = bulkhead_interface()
        del record["seal_retained"]
        with self.assertRaises(ValueError):
            validate_interface(record)

    def test_a_bulkhead_interface_without_a_peak_pressure_raises(self):
        record = bulkhead_interface()
        del record["peak_transfer_pressure_mpa"]
        with self.assertRaises(ValueError):
            validate_interface(record)

    def test_a_plain_interface_needs_no_containment_figures(self):
        record = validate_interface(interface())
        self.assertIsNone(record["peak_transfer_pressure_mpa"])

    def test_a_zero_design_gap_raises(self):
        with self.assertRaises(ValueError):
            validate_interface(interface(design_gap_mm=0.0))

    def test_duplicate_segment_ids_raise(self):
        bad = train()
        bad["segments"][1]["id"] = "MDF-PORT"
        with self.assertRaises(ValueError):
            validate_train(bad)

    def test_a_branch_on_an_unknown_segment_raises(self):
        bad = train()
        bad["branches"][0]["segments"] = ["MDF-KEEL"]
        with self.assertRaises(ValueError):
            validate_train(bad)

    def test_an_interface_on_no_branch_raises(self):
        bad = train()
        bad["branches"][1]["interfaces"] = []
        with self.assertRaises(ValueError):
            validate_train(bad)

    def test_a_train_with_no_branch_raises(self):
        bad = train()
        bad["branches"] = []
        with self.assertRaises(ValueError):
            validate_train(bad)


class TestInterfaceGate(unittest.TestCase):
    def test_gap_margin_is_the_reliable_gap_over_the_design_gap(self):
        self.assertAlmostEqual(gap_margin(interface()), 4.0, places=9)

    def test_a_margin_landing_exactly_on_the_requirement_passes(self):
        verdict = interface_verdict(
            interface(design_gap_mm=2.00, max_transfer_gap_mm=4.00)
        )
        self.assertAlmostEqual(verdict["gap_margin"], 2.0, places=9)
        self.assertTrue(verdict["compliant"])

    def test_a_wide_design_gap_fails_the_transfer_margin(self):
        verdict = interface_verdict(interface(design_gap_mm=3.50))
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("reliable transfer" in f for f in verdict["findings"]))

    def test_a_thin_bulkhead_fails_the_containment_margin(self):
        verdict = interface_verdict(
            bulkhead_interface(bulkhead_proof_pressure_mpa=50.0)
        )
        self.assertFalse(verdict["compliant"])
        self.assertAlmostEqual(verdict["pressure_margin"], 1.25, places=9)

    def test_a_breached_seal_is_reported_on_its_own(self):
        verdict = interface_verdict(bulkhead_interface(seal_retained=False))
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("breached" in f for f in verdict["findings"]))


class TestSegmentGate(unittest.TestCase):
    def test_transit_time_is_length_over_velocity(self):
        self.assertAlmostEqual(
            segment_transit_time_s(segment()), 1.400 / 7000.0, places=12
        )

    def test_a_healthy_segment_passes(self):
        self.assertTrue(segment_verdict(segment())["compliant"])

    def test_a_core_load_exactly_on_the_margin_passes(self):
        verdict = segment_verdict(
            segment(core_load_g_per_m=1.25, min_propagating_core_load_g_per_m=1.0)
        )
        self.assertAlmostEqual(verdict["core_load_margin"], 1.25, places=9)
        self.assertTrue(verdict["compliant"])

    def test_a_thin_core_load_fails(self):
        self.assertFalse(
            segment_verdict(segment(core_load_g_per_m=1.05))["compliant"]
        )

    def test_a_tight_installed_bend_fails(self):
        verdict = segment_verdict(segment(installed_bend_radius_mm=18.0))
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("radius" in f for f in verdict["findings"]))


class TestSimultaneity(unittest.TestCase):
    def test_branch_arrival_adds_transit_and_crossing_delay(self):
        checked = validate_train(train())
        arrival = branch_arrival_time_s(
            checked["branches"][0], checked["segments"], checked["interfaces"]
        )
        self.assertAlmostEqual(arrival, 1.400 / 7000.0, places=12)

    def test_matched_branches_have_no_spread(self):
        verdict = simultaneity_verdict(train())
        self.assertAlmostEqual(verdict["spread_s"], 0.0, places=12)
        self.assertTrue(verdict["compliant"])

    def test_an_unequal_branch_length_opens_a_spread(self):
        bad = train()
        bad["segments"][1]["length_m"] = 30.0
        verdict = simultaneity_verdict(bad)
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("arrives" in f for f in verdict["findings"]))

    def test_a_crossing_delay_counts_toward_the_spread(self):
        bad = train()
        bad["interfaces"][0]["delay_s"] = 0.05
        verdict = simultaneity_verdict(bad)
        self.assertAlmostEqual(verdict["spread_s"], 0.05, places=12)
        self.assertFalse(verdict["compliant"])

    def test_an_unknown_branch_reference_raises(self):
        checked = validate_train(train())
        with self.assertRaises(ValueError):
            branch_arrival_time_s(
                {"segments": ["MDF-KEEL"], "interfaces": []},
                checked["segments"],
                checked["interfaces"],
            )


class TestTemperatureGate(unittest.TestCase):
    def test_a_qualified_range_with_margin_passes(self):
        self.assertTrue(temperature_verdict(train(), case())["compliant"])

    def test_a_range_landing_exactly_on_the_requirement_passes(self):
        verdict = temperature_verdict(
            train(
                qualified_min_temperature_k=223.0,
                qualified_max_temperature_k=343.0,
            ),
            case(),
        )
        self.assertAlmostEqual(verdict["required_low_k"], 223.0, places=9)
        self.assertTrue(verdict["compliant"])

    def test_a_short_hot_qualification_fails(self):
        verdict = temperature_verdict(
            train(qualified_max_temperature_k=335.0), case()
        )
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("hot case" in f for f in verdict["findings"]))

    def test_an_inverted_predicted_range_raises(self):
        with self.assertRaises(ValueError):
            temperature_verdict(
                train(), case(predicted_min_temperature_k=400.0)
            )


class TestAssessment(unittest.TestCase):
    def test_a_sound_train_meets_the_clause(self):
        report = assess_transfer_train(train(), case())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["findings"], [])

    def test_a_failed_interface_fails_the_train(self):
        bad = train()
        bad["interfaces"][0]["seal_retained"] = False
        report = assess_transfer_train(bad, case())
        self.assertEqual(report["failed_interfaces"], ["TBI-1"])
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)

    def test_a_failed_segment_fails_the_train(self):
        bad = train()
        bad["segments"][0]["core_load_g_per_m"] = 1.02
        report = assess_transfer_train(bad, case())
        self.assertEqual(report["failed_segments"], ["MDF-PORT"])
        self.assertFalse(report["compliant"])

    def test_simultaneity_alone_can_fail_an_otherwise_sound_train(self):
        bad = train()
        bad["interfaces"][1]["delay_s"] = 0.2
        report = assess_transfer_train(bad, case())
        self.assertEqual(report["failed_segments"], [])
        self.assertEqual(report["failed_interfaces"], [])
        self.assertFalse(report["compliant"])


if __name__ == "__main__":
    unittest.main()
