"""Contract tests for the clause 5.1.2 unwanted-firing tolerance logic."""

import unittest

from e2021_unwanted_firing_failure_tolerance_logic import (
    BARRIERS,
    MARGIN_TOLERANCE_DB,
    MIN_INDEPENDENT_INHIBITS,
    assess_unwanted_firing,
    barrier_coverage,
    independent_groups,
    independent_inhibit_count,
    no_fire_margin_db,
    normalize_barrier,
    normalize_inhibits,
    resource_map,
    single_failure_scan,
    stray_energy_verdict,
    validate_positive,
)


def chain():
    return [
        {"inhibit_id": "ARM-RELAY", "barrier": "arm", "resources": ["bus-a", "cmd-a"]},
        {"inhibit_id": "SEL-SWITCH", "barrier": "select", "resources": ["bus-b", "cmd-b"]},
        {"inhibit_id": "FIRE-FET", "barrier": "fire", "resources": ["bus-b", "cmd-c"]},
    ]


def independent_chain():
    return [
        {"inhibit_id": "ARM-RELAY", "barrier": "arm", "resources": ["bus-a"]},
        {"inhibit_id": "SEL-SWITCH", "barrier": "select", "resources": ["bus-b"]},
        {"inhibit_id": "FIRE-FET", "barrier": "fire", "resources": ["bus-c"]},
    ]


def good_spec(**overrides):
    spec = {
        "inhibits": independent_chain(),
        "failures": [
            {"failure_id": "F1", "defeats_inhibits": ["ARM-RELAY"]},
            {"failure_id": "F2", "defeats_inhibits": [], "defeats_resources": ["bus-b"]},
        ],
        "no_fire_current_a": 1.0,
        "worst_case_induced_current_a": 0.05,
        "required_margin_db": 20.0,
    }
    spec.update(overrides)
    return spec


class BarrierTests(unittest.TestCase):
    def test_barrier_names_normalize(self):
        self.assertEqual(normalize_barrier(" Arm "), "arm")

    def test_unknown_barrier_rejected(self):
        with self.assertRaises(ValueError):
            normalize_barrier("safe")

    def test_non_string_barrier_rejected(self):
        with self.assertRaises(ValueError):
            normalize_barrier(3)

    def test_every_barrier_is_covered_by_the_example_chain(self):
        coverage = barrier_coverage(chain())
        self.assertTrue(coverage["complete"])
        self.assertEqual(coverage["present"], sorted(BARRIERS))

    def test_a_missing_barrier_is_reported(self):
        coverage = barrier_coverage(chain()[:2])
        self.assertFalse(coverage["complete"])
        self.assertEqual(coverage["missing"], ["fire"])


class InventoryTests(unittest.TestCase):
    def test_inventory_normalizes_and_sorts_resources(self):
        normalized = normalize_inhibits(
            [{"inhibit_id": " X ", "barrier": "arm", "resources": [" b ", "a", "a"]}]
        )
        self.assertEqual(normalized[0]["inhibit_id"], "X")
        self.assertEqual(normalized[0]["resources"], ["a", "b"])

    def test_duplicate_inhibit_id_rejected(self):
        bad = chain()
        bad[1] = dict(bad[1], inhibit_id="ARM-RELAY")
        with self.assertRaises(ValueError):
            normalize_inhibits(bad)

    def test_empty_inventory_rejected(self):
        with self.assertRaises(ValueError):
            normalize_inhibits([])

    def test_missing_field_rejected(self):
        with self.assertRaises(ValueError):
            normalize_inhibits([{"inhibit_id": "X", "barrier": "arm"}])

    def test_resource_map_lists_dependants(self):
        mapping = resource_map(chain())
        self.assertEqual(mapping["bus-b"], ["FIRE-FET", "SEL-SWITCH"])
        self.assertEqual(mapping["bus-a"], ["ARM-RELAY"])

    def test_validate_positive_rejects_zero(self):
        with self.assertRaises(ValueError):
            validate_positive("i", 0.0)

    def test_validate_positive_rejects_boolean(self):
        with self.assertRaises(ValueError):
            validate_positive("i", True)


class IndependenceTests(unittest.TestCase):
    def test_fully_independent_chain_keeps_every_inhibit(self):
        self.assertEqual(independent_inhibit_count(independent_chain()), 3)

    def test_a_shared_bus_collapses_two_inhibits_into_one(self):
        groups = independent_groups(chain())
        self.assertEqual(independent_inhibit_count(chain()), 2)
        self.assertIn(["FIRE-FET", "SEL-SWITCH"], groups)

    def test_one_bus_behind_everything_collapses_to_a_single_inhibit(self):
        shared = [
            {"inhibit_id": "A", "barrier": "arm", "resources": ["bus"]},
            {"inhibit_id": "B", "barrier": "select", "resources": ["bus"]},
            {"inhibit_id": "C", "barrier": "fire", "resources": ["bus"]},
        ]
        self.assertEqual(independent_inhibit_count(shared), 1)

    def test_collapse_is_transitive_through_a_chain_of_resources(self):
        linked = [
            {"inhibit_id": "A", "barrier": "arm", "resources": ["r1"]},
            {"inhibit_id": "B", "barrier": "select", "resources": ["r1", "r2"]},
            {"inhibit_id": "C", "barrier": "fire", "resources": ["r2"]},
        ]
        self.assertEqual(independent_inhibit_count(linked), 1)

    def test_an_inhibit_with_no_shared_resource_stands_alone(self):
        mixed = [
            {"inhibit_id": "A", "barrier": "arm", "resources": []},
            {"inhibit_id": "B", "barrier": "select", "resources": ["r1"]},
            {"inhibit_id": "C", "barrier": "fire", "resources": ["r1"]},
        ]
        self.assertEqual(independent_inhibit_count(mixed), 2)

    def test_minimum_is_two_inhibits(self):
        self.assertEqual(MIN_INDEPENDENT_INHIBITS, 2)


class SingleFailureScanTests(unittest.TestCase):
    def test_independent_chain_survives_every_single_resource_failure(self):
        scan = single_failure_scan(independent_chain())
        self.assertTrue(scan["tolerant"])
        self.assertEqual(scan["clearing_failures"], [])

    def test_a_common_bus_behind_every_inhibit_is_found(self):
        shared = [
            {"inhibit_id": "A", "barrier": "arm", "resources": ["bus"]},
            {"inhibit_id": "B", "barrier": "select", "resources": ["bus"]},
            {"inhibit_id": "C", "barrier": "fire", "resources": ["bus"]},
        ]
        scan = single_failure_scan(shared)
        self.assertFalse(scan["tolerant"])
        self.assertEqual(scan["clearing_failures"][0]["name"], "bus")

    def test_a_declared_failure_defeating_every_inhibit_is_found(self):
        scan = single_failure_scan(
            independent_chain(),
            [
                {
                    "failure_id": "FPGA-RUNAWAY",
                    "defeats_inhibits": ["ARM-RELAY", "SEL-SWITCH", "FIRE-FET"],
                }
            ],
        )
        self.assertFalse(scan["tolerant"])
        self.assertIn("FPGA-RUNAWAY", scan["findings"][0])

    def test_a_partial_failure_leaves_the_chain_tolerant(self):
        scan = single_failure_scan(
            independent_chain(),
            [{"failure_id": "F1", "defeats_inhibits": ["ARM-RELAY", "SEL-SWITCH"]}],
        )
        self.assertTrue(scan["tolerant"])

    def test_a_failure_may_be_declared_through_the_resources_it_takes_out(self):
        scan = single_failure_scan(
            chain(),
            [{"failure_id": "F2", "defeats_inhibits": ["ARM-RELAY"],
              "defeats_resources": ["bus-b"]}],
        )
        self.assertFalse(scan["tolerant"])

    def test_a_failure_naming_an_unknown_inhibit_is_rejected(self):
        with self.assertRaises(ValueError):
            single_failure_scan(
                independent_chain(),
                [{"failure_id": "F9", "defeats_inhibits": ["NO-SUCH"]}],
            )

    def test_a_failure_naming_an_unknown_resource_is_rejected(self):
        with self.assertRaises(ValueError):
            single_failure_scan(
                independent_chain(),
                [{"failure_id": "F9", "defeats_inhibits": [], "defeats_resources": ["ghost"]}],
            )

    def test_failures_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            single_failure_scan(independent_chain(), {"failure_id": "F1"})


class StrayEnergyTests(unittest.TestCase):
    def test_margin_is_twenty_decades_of_current(self):
        self.assertAlmostEqual(no_fire_margin_db(1.0, 0.1), 20.0, places=9)

    def test_a_stray_current_at_the_no_fire_level_has_no_margin(self):
        self.assertAlmostEqual(no_fire_margin_db(1.0, 1.0), 0.0, places=9)

    def test_margin_grows_as_the_stray_current_falls(self):
        self.assertGreater(no_fire_margin_db(1.0, 0.01), no_fire_margin_db(1.0, 0.1))

    def test_zero_induced_current_rejected(self):
        with self.assertRaises(ValueError):
            no_fire_margin_db(1.0, 0.0)

    def test_a_margin_exactly_on_the_requirement_is_met(self):
        verdict = stray_energy_verdict(1.0, 0.1, 20.0)
        self.assertTrue(verdict["met"])
        self.assertAlmostEqual(verdict["achieved_margin_db"], 20.0, places=9)

    def test_a_short_margin_is_a_finding(self):
        verdict = stray_energy_verdict(1.0, 0.5, 20.0)
        self.assertFalse(verdict["met"])

    def test_negative_required_margin_rejected(self):
        with self.assertRaises(ValueError):
            stray_energy_verdict(1.0, 0.1, -3.0)

    def test_tolerance_is_representation_sized(self):
        self.assertLess(MARGIN_TOLERANCE_DB, 1e-6)


class AssessmentTests(unittest.TestCase):
    def test_a_sound_chain_is_single_failure_tolerant(self):
        result = assess_unwanted_firing(good_spec())
        self.assertTrue(result["single_failure_tolerant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["independent_inhibits"], 3)

    def test_a_shared_bus_chain_is_still_tolerant_with_two_groups(self):
        result = assess_unwanted_firing(good_spec(inhibits=chain(), failures=None))
        self.assertTrue(result["single_failure_tolerant"])
        self.assertEqual(result["independent_inhibits"], 2)

    def test_a_single_common_resource_sinks_the_chain(self):
        shared = [
            {"inhibit_id": "A", "barrier": "arm", "resources": ["bus"]},
            {"inhibit_id": "B", "barrier": "select", "resources": ["bus"]},
            {"inhibit_id": "C", "barrier": "fire", "resources": ["bus"]},
        ]
        result = assess_unwanted_firing(good_spec(inhibits=shared, failures=None))
        self.assertFalse(result["single_failure_tolerant"])
        self.assertEqual(result["independent_inhibits"], 1)

    def test_a_missing_barrier_is_a_finding(self):
        result = assess_unwanted_firing(
            good_spec(inhibits=independent_chain()[:2], failures=None)
        )
        self.assertFalse(result["single_failure_tolerant"])
        self.assertTrue(any("barrier" in f for f in result["findings"]))

    def test_a_short_stray_margin_sinks_the_chain(self):
        result = assess_unwanted_firing(good_spec(worst_case_induced_current_a=0.9))
        self.assertFalse(result["single_failure_tolerant"])

    def test_a_partial_stray_block_is_rejected(self):
        spec = good_spec()
        del spec["required_margin_db"]
        with self.assertRaises(ValueError):
            assess_unwanted_firing(spec)

    def test_a_chain_without_stray_data_is_still_assessed(self):
        spec = {"inhibits": independent_chain()}
        result = assess_unwanted_firing(spec)
        self.assertIsNone(result["stray_energy"])
        self.assertTrue(result["single_failure_tolerant"])

    def test_missing_inhibits_rejected(self):
        with self.assertRaises(ValueError):
            assess_unwanted_firing({"failures": []})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_unwanted_firing(["inhibits"])


if __name__ == "__main__":
    unittest.main()
