"""Contract tests for the clause 6.5.1 solar cell assembly failure criteria."""

import unittest

from e2008_sca_failure_criteria_logic import (
    ASSEMBLY_ACCEPTED,
    ASSEMBLY_FAILED,
    DEFAULT_FAILURE_POLICY,
    DEFECT_CRITERION,
    INSULATION_CRITERION,
    MAX_POWER_CRITERION,
    OPEN_CIRCUIT_VOLTAGE_CRITERION,
    SHORT_CIRCUIT_CURRENT_CRITERION,
    SUBGROUP_ACCEPTED,
    SUBGROUP_REJECTED,
    assess_cell_assembly,
    assess_subgroup,
    categorize_observations,
    disqualifying_criteria,
    insulation_resistance_holds,
    relative_loss_fraction,
    validate_failure_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_FAILURE_POLICY)
    policy.update(overrides)
    return policy


def _record(identifier="sca-01", **overrides):
    record = {
        "id": identifier,
        "before": {"pmax_w": 1.200, "isc_a": 0.5000, "voc_v": 2.600},
        "after": {"pmax_w": 1.194, "isc_a": 0.4990, "voc_v": 2.598},
        "insulation_resistance_ohm": 5.0e8,
        "observations": ["edge-chip-within-allowance"],
    }
    record.update(overrides)
    return record


def _degraded(identifier, key, after_value):
    record = _record(identifier)
    record["after"] = dict(record["after"])
    record["after"][key] = after_value
    return record


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_failure_policy(DEFAULT_FAILURE_POLICY), DEFAULT_FAILURE_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_policy("allowance")

    def test_a_loss_limit_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_policy(_policy(max_power_loss_fraction=1.5))

    def test_a_negative_loss_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_policy(
                _policy(max_short_circuit_current_loss_fraction=-0.01)
            )

    def test_a_zero_insulation_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_policy(_policy(min_insulation_resistance_ohm=0.0))

    def test_a_fractional_subgroup_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_policy(_policy(allowed_failed_assemblies=1.5))

    def test_a_negative_subgroup_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_policy(_policy(allowed_failed_assemblies=-1))


class LossTests(unittest.TestCase):
    def test_an_unchanged_value_loses_nothing(self):
        self.assertAlmostEqual(relative_loss_fraction(1.2, 1.2), 0.0, places=12)

    def test_the_loss_is_relative_to_the_pre_test_value(self):
        self.assertAlmostEqual(relative_loss_fraction(1.0, 0.98), 0.02, places=12)

    def test_a_gain_reads_as_a_negative_loss(self):
        self.assertLess(relative_loss_fraction(1.0, 1.05), 0.0)

    def test_a_dead_assembly_loses_everything(self):
        self.assertAlmostEqual(relative_loss_fraction(1.2, 0.0), 1.0, places=12)

    def test_a_zero_pre_test_value_rejected(self):
        with self.assertRaises(ValueError):
            relative_loss_fraction(0.0, 0.0)

    def test_a_negative_post_test_value_rejected(self):
        with self.assertRaises(ValueError):
            relative_loss_fraction(1.2, -0.1)

    def test_a_boolean_measurement_rejected(self):
        with self.assertRaises(ValueError):
            relative_loss_fraction(True, 0.5)


class InsulationTests(unittest.TestCase):
    def test_a_resistance_above_the_floor_holds(self):
        self.assertTrue(insulation_resistance_holds(5.0e8, _policy()))

    def test_a_resistance_exactly_at_the_floor_holds(self):
        policy = _policy()
        self.assertTrue(
            insulation_resistance_holds(policy["min_insulation_resistance_ohm"], policy)
        )

    def test_a_resistance_below_the_floor_does_not_hold(self):
        self.assertFalse(insulation_resistance_holds(1.0e6, _policy()))

    def test_a_zero_resistance_rejected(self):
        with self.assertRaises(ValueError):
            insulation_resistance_holds(0.0, _policy())


class ObservationTests(unittest.TestCase):
    def test_an_acceptable_observation_is_grouped_as_acceptable(self):
        disqualifying, acceptable = categorize_observations(
            ["edge-chip-within-allowance"]
        )
        self.assertEqual(disqualifying, ())
        self.assertEqual(acceptable, ("edge-chip-within-allowance",))

    def test_a_disqualifying_defect_is_grouped_as_disqualifying(self):
        disqualifying, acceptable = categorize_observations(["interconnect-rupture"])
        self.assertEqual(disqualifying, ("interconnect-rupture",))
        self.assertEqual(acceptable, ())

    def test_a_mixed_list_is_split_both_ways(self):
        disqualifying, acceptable = categorize_observations(
            ["coverglass-surface-mark", "cell-fracture-crossing-the-junction"]
        )
        self.assertEqual(disqualifying, ("cell-fracture-crossing-the-junction",))
        self.assertEqual(acceptable, ("coverglass-surface-mark",))

    def test_a_repeated_observation_is_grouped_once(self):
        disqualifying, _acceptable = categorize_observations(
            ["coverglass-loss", "coverglass-loss"]
        )
        self.assertEqual(disqualifying, ("coverglass-loss",))

    def test_an_unrecognised_observation_rejected(self):
        with self.assertRaises(ValueError):
            categorize_observations(["slightly-odd-looking"])

    def test_a_non_collection_observation_list_rejected(self):
        with self.assertRaises(ValueError):
            categorize_observations("coverglass-loss")

    def test_each_defect_maps_to_a_criterion(self):
        self.assertEqual(
            disqualifying_criteria(["bus-bar-detachment"]), ("bus-bar-detachment",)
        )

    def test_an_acceptable_observation_maps_to_no_criterion(self):
        self.assertEqual(disqualifying_criteria(["handling-witness-mark"]), ())


class AssemblyTests(unittest.TestCase):
    def test_a_sound_assembly_is_accepted(self):
        result = assess_cell_assembly(_record())
        self.assertEqual(result["verdict"], ASSEMBLY_ACCEPTED)
        self.assertFalse(result["failed"])
        self.assertEqual(result["criteria_met"], ())

    def test_the_three_electrical_losses_are_reported_separately(self):
        result = assess_cell_assembly(_record())
        self.assertAlmostEqual(result["power_loss_fraction"], 0.005, places=9)
        self.assertAlmostEqual(
            result["short_circuit_current_loss_fraction"], 0.002, places=9
        )
        self.assertAlmostEqual(
            result["open_circuit_voltage_loss_fraction"], 0.2 / 260.0, places=9
        )

    def test_a_power_loss_exactly_at_the_limit_is_accepted(self):
        record = _degraded("sca-02", "pmax_w", 1.176)
        result = assess_cell_assembly(record)
        self.assertAlmostEqual(
            result["power_loss_fraction"],
            DEFAULT_FAILURE_POLICY["max_power_loss_fraction"],
            places=9,
        )
        self.assertFalse(result["failed"])

    def test_a_power_loss_beyond_the_limit_fails(self):
        result = assess_cell_assembly(_degraded("sca-03", "pmax_w", 1.05))
        self.assertEqual(result["verdict"], ASSEMBLY_FAILED)
        self.assertIn(MAX_POWER_CRITERION, result["criteria_met"])

    def test_a_current_loss_beyond_the_limit_fails(self):
        result = assess_cell_assembly(_degraded("sca-04", "isc_a", 0.45))
        self.assertIn(SHORT_CIRCUIT_CURRENT_CRITERION, result["criteria_met"])

    def test_a_voltage_loss_beyond_the_limit_fails(self):
        result = assess_cell_assembly(_degraded("sca-05", "voc_v", 2.40))
        self.assertIn(OPEN_CIRCUIT_VOLTAGE_CRITERION, result["criteria_met"])

    def test_a_current_loss_does_not_raise_the_voltage_criterion(self):
        result = assess_cell_assembly(_degraded("sca-06", "isc_a", 0.45))
        self.assertNotIn(OPEN_CIRCUIT_VOLTAGE_CRITERION, result["criteria_met"])

    def test_a_low_insulation_resistance_fails(self):
        result = assess_cell_assembly(
            _record("sca-07", insulation_resistance_ohm=1.0e5)
        )
        self.assertEqual(result["verdict"], ASSEMBLY_FAILED)
        self.assertIn(INSULATION_CRITERION, result["criteria_met"])

    def test_a_disqualifying_defect_fails_a_clean_reading(self):
        result = assess_cell_assembly(
            _record("sca-08", observations=["cell-to-substrate-debonding"])
        )
        self.assertEqual(result["verdict"], ASSEMBLY_FAILED)
        self.assertEqual(result["criteria_met"], (DEFECT_CRITERION,))

    def test_an_acceptable_observation_does_not_fail_the_assembly(self):
        result = assess_cell_assembly(
            _record("sca-09", observations=["coverglass-surface-mark"])
        )
        self.assertEqual(result["verdict"], ASSEMBLY_ACCEPTED)

    def test_every_criterion_met_is_listed_not_only_the_first(self):
        record = _degraded("sca-10", "pmax_w", 1.00)
        record["after"]["isc_a"] = 0.40
        record["insulation_resistance_ohm"] = 1.0e4
        record["observations"] = ["interconnect-rupture"]
        result = assess_cell_assembly(record)
        self.assertEqual(len(result["criteria_met"]), 4)

    def test_an_empty_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell_assembly(_record("   "))

    def test_absent_observations_key_rejected(self):
        record = _record()
        del record["observations"]
        with self.assertRaises(ValueError):
            assess_cell_assembly(record)

    def test_a_missing_after_block_rejected(self):
        record = _record()
        del record["after"]
        with self.assertRaises(ValueError):
            assess_cell_assembly(record)

    def test_a_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell_assembly(["sca-01"])


class SubgroupTests(unittest.TestCase):
    def test_a_subgroup_of_sound_assemblies_is_accepted(self):
        result = assess_subgroup([_record("sca-01"), _record("sca-02")])
        self.assertEqual(result["verdict"], SUBGROUP_ACCEPTED)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(result["findings"], [])

    def test_one_failure_rejects_a_zero_allowance_subgroup(self):
        result = assess_subgroup(
            [_record("sca-01"), _degraded("sca-02", "pmax_w", 1.05)]
        )
        self.assertEqual(result["verdict"], SUBGROUP_REJECTED)
        self.assertEqual(result["failed_ids"], ("sca-02",))

    def test_one_failure_inside_an_allowance_is_accepted(self):
        result = assess_subgroup(
            [_record("sca-01"), _degraded("sca-02", "pmax_w", 1.05)],
            _policy(allowed_failed_assemblies=1),
        )
        self.assertEqual(result["verdict"], SUBGROUP_ACCEPTED)
        self.assertEqual(result["failed_count"], 1)

    def test_a_failure_count_exactly_at_the_allowance_is_accepted(self):
        policy = _policy(allowed_failed_assemblies=2)
        result = assess_subgroup(
            [
                _record("sca-01"),
                _degraded("sca-02", "pmax_w", 1.05),
                _degraded("sca-03", "isc_a", 0.40),
            ],
            policy,
        )
        self.assertEqual(result["failed_count"], policy["allowed_failed_assemblies"])
        self.assertEqual(result["verdict"], SUBGROUP_ACCEPTED)

    def test_one_failure_past_the_allowance_is_rejected(self):
        result = assess_subgroup(
            [
                _record("sca-01"),
                _degraded("sca-02", "pmax_w", 1.05),
                _degraded("sca-03", "isc_a", 0.40),
            ],
            _policy(allowed_failed_assemblies=1),
        )
        self.assertEqual(result["verdict"], SUBGROUP_REJECTED)
        self.assertEqual(result["failed_count"], 2)

    def test_each_failed_assembly_names_its_criteria_in_the_findings(self):
        result = assess_subgroup(
            [_record("sca-01"), _degraded("sca-02", "pmax_w", 1.05)]
        )
        self.assertTrue(any("sca-02" in finding for finding in result["findings"]))

    def test_every_assembly_is_returned_with_its_own_verdict(self):
        result = assess_subgroup([_record("sca-01"), _record("sca-02")])
        self.assertEqual(result["assembly_count"], 2)
        self.assertEqual(
            [outcome["verdict"] for outcome in result["assemblies"]],
            [ASSEMBLY_ACCEPTED, ASSEMBLY_ACCEPTED],
        )

    def test_a_repeated_assembly_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_subgroup([_record("sca-01"), _record("sca-01")])

    def test_an_empty_subgroup_rejected(self):
        with self.assertRaises(ValueError):
            assess_subgroup([])

    def test_a_non_sequence_subgroup_rejected(self):
        with self.assertRaises(ValueError):
            assess_subgroup(_record())


if __name__ == "__main__":
    unittest.main()
