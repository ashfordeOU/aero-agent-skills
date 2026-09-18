"""Contract tests for the clause 5.2.16.1.1 spurious state change immunity logic."""

import unittest

from e2020_spurious_state_change_immunity_logic import (
    COMMAND_DOUBLE_LATCH,
    CONDUCTED_EM_TRANSIENT,
    DEFAULT_IMMUNITY_POLICY,
    DEVICE_FLIP_CREDIBLE,
    DEVICE_IMMUNE,
    DEVICE_MARGIN_INSUFFICIENT,
    DEVICE_NO_PROVISION,
    DEVICE_NOT_ASSESSED,
    DEVICE_SELF_CORRECTED,
    ELECTROSTATIC_DISCHARGE,
    INPUT_TRANSIENT_FILTER,
    OUTCOME_FLIP_CREDIBLE,
    OUTCOME_FLIP_SELF_CORRECTED,
    OUTCOME_IMMUNE,
    OUTCOME_MARGIN_INSUFFICIENT,
    OUTCOME_NO_PROVISION,
    OUTCOME_NOT_ASSESSED,
    PERIODIC_STATE_REFRESH,
    PERTURBATION_CLASSES,
    POWER_BUS_TRANSIENT,
    RADIATED_EM_FIELD,
    SHIELDED_STATE_HARNESS,
    SINGLE_EVENT_UPSET,
    TRIPLE_MODULAR_REDUNDANT_STATE,
    UPSET_HARDENED_LATCH,
    assess_perturbation_class,
    assess_state_immunity,
    categorize_immunity_provision,
    categorize_perturbation_class,
    immunity_margin_ratio,
    level_margin_db,
    preventing_provisions,
    provisions_covering,
    restores_within_window,
    restoring_provisions,
    validate_immunity_policy,
    worst_outcome,
)


def _policy(**overrides):
    policy = dict(DEFAULT_IMMUNITY_POLICY)
    policy.update(overrides)
    return policy


def _perturbations(**overrides):
    declared = {
        CONDUCTED_EM_TRANSIENT: {
            "environment_level": 50.0,
            "immunity_level": 200.0,
            "provisions": [INPUT_TRANSIENT_FILTER, COMMAND_DOUBLE_LATCH],
        },
        RADIATED_EM_FIELD: {
            "environment_level": 20.0,
            "immunity_level": 60.0,
            "provisions": [SHIELDED_STATE_HARNESS],
        },
        ELECTROSTATIC_DISCHARGE: {
            "environment_level": 2000.0,
            "immunity_level": 8000.0,
            "provisions": [COMMAND_DOUBLE_LATCH, SHIELDED_STATE_HARNESS],
        },
        SINGLE_EVENT_UPSET: {
            "environment_level": 2.0,
            "immunity_level": 10.0,
            "provisions": [UPSET_HARDENED_LATCH],
        },
        POWER_BUS_TRANSIENT: {
            "environment_level": 25.0,
            "immunity_level": 100.0,
            "provisions": [INPUT_TRANSIENT_FILTER],
        },
    }
    declared.update(overrides)
    return declared


def _device(**overrides):
    device = {
        "state_refresh_period_s": 0.5,
        "tolerable_outage_s": 2.0,
        "perturbations": _perturbations(),
    }
    device.update(overrides)
    return device


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_immunity_policy(DEFAULT_IMMUNITY_POLICY),
            DEFAULT_IMMUNITY_POLICY,
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            assess_state_immunity(_device(), "immune")

    def test_a_margin_floor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_state_immunity(_device(), _policy(min_margin_ratio=0.5))

    def test_a_zero_refresh_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            assess_state_immunity(_device(), _policy(max_state_refresh_period_s=0.0))

    def test_a_non_boolean_assessment_requirement_rejected(self):
        with self.assertRaises(ValueError):
            assess_state_immunity(
                _device(), _policy(require_every_class_assessed="yes")
            )


class VocabularyTests(unittest.TestCase):
    def test_every_known_class_round_trips(self):
        for name in PERTURBATION_CLASSES:
            self.assertEqual(categorize_perturbation_class(name), name)

    def test_an_unrecognised_class_rejected(self):
        with self.assertRaises(ValueError):
            categorize_perturbation_class("solar-wind-mood")

    def test_an_empty_class_rejected(self):
        with self.assertRaises(ValueError):
            categorize_perturbation_class("   ")

    def test_a_known_provision_round_trips(self):
        self.assertEqual(
            categorize_immunity_provision(" shielded-state-harness "),
            SHIELDED_STATE_HARNESS,
        )

    def test_an_unrecognised_provision_rejected(self):
        with self.assertRaises(ValueError):
            categorize_immunity_provision("thicker-paint")


class CoverageTests(unittest.TestCase):
    def test_a_shielded_harness_answers_a_radiated_field_only(self):
        self.assertEqual(
            provisions_covering(RADIATED_EM_FIELD, [SHIELDED_STATE_HARNESS]),
            (SHIELDED_STATE_HARNESS,),
        )
        self.assertEqual(
            provisions_covering(CONDUCTED_EM_TRANSIENT, [SHIELDED_STATE_HARNESS]),
            (),
        )

    def test_an_upset_hardened_latch_answers_only_the_upset_class(self):
        self.assertEqual(
            provisions_covering(SINGLE_EVENT_UPSET, [UPSET_HARDENED_LATCH]),
            (UPSET_HARDENED_LATCH,),
        )
        self.assertEqual(
            provisions_covering(POWER_BUS_TRANSIENT, [UPSET_HARDENED_LATCH]), ()
        )

    def test_a_redundant_state_answers_an_upset_and_a_radiated_field(self):
        self.assertIn(
            TRIPLE_MODULAR_REDUNDANT_STATE,
            provisions_covering(
                SINGLE_EVENT_UPSET, [TRIPLE_MODULAR_REDUNDANT_STATE]
            ),
        )

    def test_a_refresh_covers_every_class_but_only_by_restoring(self):
        for name in PERTURBATION_CLASSES:
            self.assertEqual(
                provisions_covering(name, [PERIODIC_STATE_REFRESH]),
                (PERIODIC_STATE_REFRESH,),
            )
            self.assertEqual(preventing_provisions(name, [PERIODIC_STATE_REFRESH]), ())
            self.assertEqual(
                restoring_provisions(name, [PERIODIC_STATE_REFRESH]),
                (PERIODIC_STATE_REFRESH,),
            )

    def test_preventing_and_restoring_provisions_stay_apart(self):
        provisions = [INPUT_TRANSIENT_FILTER, PERIODIC_STATE_REFRESH]
        self.assertEqual(
            preventing_provisions(CONDUCTED_EM_TRANSIENT, provisions),
            (INPUT_TRANSIENT_FILTER,),
        )
        self.assertEqual(
            restoring_provisions(CONDUCTED_EM_TRANSIENT, provisions),
            (PERIODIC_STATE_REFRESH,),
        )

    def test_a_provision_declared_twice_rejected(self):
        with self.assertRaises(ValueError):
            provisions_covering(
                RADIATED_EM_FIELD, [SHIELDED_STATE_HARNESS, SHIELDED_STATE_HARNESS]
            )

    def test_a_non_sequence_provision_set_rejected(self):
        with self.assertRaises(ValueError):
            provisions_covering(RADIATED_EM_FIELD, SHIELDED_STATE_HARNESS)


class MarginTests(unittest.TestCase):
    def test_margin_is_immunity_over_environment(self):
        self.assertAlmostEqual(immunity_margin_ratio(200.0, 50.0), 4.0, places=9)

    def test_equal_levels_give_unity_and_no_decibels(self):
        ratio = immunity_margin_ratio(50.0, 50.0)
        self.assertAlmostEqual(ratio, 1.0, places=9)
        self.assertAlmostEqual(level_margin_db(ratio), 0.0, places=9)

    def test_a_doubling_is_about_six_decibels(self):
        self.assertAlmostEqual(level_margin_db(2.0), 6.0206, places=4)

    def test_a_zero_environment_rejected(self):
        with self.assertRaises(ValueError):
            immunity_margin_ratio(200.0, 0.0)

    def test_a_negative_immunity_rejected(self):
        with self.assertRaises(ValueError):
            immunity_margin_ratio(-200.0, 50.0)

    def test_a_non_positive_ratio_has_no_decibel_value(self):
        with self.assertRaises(ValueError):
            level_margin_db(0.0)


class WindowTests(unittest.TestCase):
    def test_a_prompt_refresh_restores_in_time(self):
        self.assertTrue(restores_within_window(0.5, 2.0, DEFAULT_IMMUNITY_POLICY))

    def test_a_refresh_longer_than_the_tolerable_outage_does_not(self):
        self.assertFalse(
            restores_within_window(
                0.9, 0.4, _policy(max_state_refresh_period_s=5.0)
            )
        )

    def test_a_refresh_longer_than_the_policy_ceiling_does_not(self):
        self.assertFalse(restores_within_window(4.0, 30.0, DEFAULT_IMMUNITY_POLICY))

    def test_a_refresh_exactly_on_the_ceiling_restores_in_time(self):
        self.assertTrue(restores_within_window(1.0, 2.0, DEFAULT_IMMUNITY_POLICY))

    def test_a_zero_refresh_period_rejected(self):
        with self.assertRaises(ValueError):
            restores_within_window(0.0, 2.0, DEFAULT_IMMUNITY_POLICY)


class ClassAssessmentTests(unittest.TestCase):
    def test_a_covered_class_with_margin_is_immune(self):
        record = assess_perturbation_class(RADIATED_EM_FIELD, _device())
        self.assertEqual(record["outcome"], OUTCOME_IMMUNE)
        self.assertAlmostEqual(record["margin_ratio"], 3.0, places=9)

    def test_a_margin_exactly_on_the_floor_is_immune(self):
        device = _device(
            perturbations=_perturbations(
                **{
                    RADIATED_EM_FIELD: {
                        "environment_level": 50.0,
                        "immunity_level": 100.0,
                        "provisions": [SHIELDED_STATE_HARNESS],
                    }
                }
            )
        )
        record = assess_perturbation_class(RADIATED_EM_FIELD, device)
        self.assertAlmostEqual(
            record["margin_ratio"],
            float(DEFAULT_IMMUNITY_POLICY["min_margin_ratio"]),
            places=9,
        )
        self.assertEqual(record["outcome"], OUTCOME_IMMUNE)

    def test_a_margin_below_the_floor_but_above_unity_is_insufficient(self):
        device = _device(
            perturbations=_perturbations(
                **{
                    RADIATED_EM_FIELD: {
                        "environment_level": 50.0,
                        "immunity_level": 60.0,
                        "provisions": [SHIELDED_STATE_HARNESS],
                    }
                }
            )
        )
        record = assess_perturbation_class(RADIATED_EM_FIELD, device)
        self.assertEqual(record["outcome"], OUTCOME_MARGIN_INSUFFICIENT)

    def test_an_environment_above_the_immunity_is_a_credible_flip(self):
        device = _device(
            perturbations=_perturbations(
                **{
                    CONDUCTED_EM_TRANSIENT: {
                        "environment_level": 50.0,
                        "immunity_level": 20.0,
                        "provisions": [INPUT_TRANSIENT_FILTER],
                    }
                }
            )
        )
        record = assess_perturbation_class(CONDUCTED_EM_TRANSIENT, device)
        self.assertEqual(record["outcome"], OUTCOME_FLIP_CREDIBLE)

    def test_a_refresh_inside_the_outage_turns_a_flip_self_correcting(self):
        device = _device(
            perturbations=_perturbations(
                **{
                    CONDUCTED_EM_TRANSIENT: {
                        "environment_level": 50.0,
                        "immunity_level": 20.0,
                        "provisions": [INPUT_TRANSIENT_FILTER, PERIODIC_STATE_REFRESH],
                    }
                }
            )
        )
        record = assess_perturbation_class(CONDUCTED_EM_TRANSIENT, device)
        self.assertEqual(record["outcome"], OUTCOME_FLIP_SELF_CORRECTED)
        self.assertTrue(record["restores_in_time"])

    def test_a_refresh_outside_the_outage_leaves_the_flip_credible(self):
        device = _device(
            state_refresh_period_s=0.9,
            tolerable_outage_s=0.2,
            perturbations=_perturbations(
                **{
                    CONDUCTED_EM_TRANSIENT: {
                        "environment_level": 50.0,
                        "immunity_level": 20.0,
                        "provisions": [PERIODIC_STATE_REFRESH],
                    }
                }
            ),
        )
        record = assess_perturbation_class(CONDUCTED_EM_TRANSIENT, device)
        self.assertEqual(record["outcome"], OUTCOME_FLIP_CREDIBLE)
        self.assertFalse(record["restores_in_time"])

    def test_a_level_with_no_covering_provision_is_an_assertion(self):
        device = _device(
            perturbations=_perturbations(
                **{
                    POWER_BUS_TRANSIENT: {
                        "environment_level": 25.0,
                        "immunity_level": 400.0,
                        "provisions": [UPSET_HARDENED_LATCH],
                    }
                }
            )
        )
        record = assess_perturbation_class(POWER_BUS_TRANSIENT, device)
        self.assertEqual(record["outcome"], OUTCOME_NO_PROVISION)

    def test_an_undeclared_class_is_not_assessed(self):
        declared = _perturbations()
        del declared[SINGLE_EVENT_UPSET]
        record = assess_perturbation_class(
            SINGLE_EVENT_UPSET, _device(perturbations=declared)
        )
        self.assertEqual(record["outcome"], OUTCOME_NOT_ASSESSED)
        self.assertIsNone(record["margin_ratio"])

    def test_a_malformed_class_detail_rejected(self):
        device = _device(perturbations=_perturbations(**{RADIATED_EM_FIELD: 60.0}))
        with self.assertRaises(ValueError):
            assess_perturbation_class(RADIATED_EM_FIELD, device)


class WorstOutcomeTests(unittest.TestCase):
    def test_the_worst_outcome_is_the_one_reported(self):
        records = [
            {"outcome": OUTCOME_IMMUNE},
            {"outcome": OUTCOME_MARGIN_INSUFFICIENT},
            {"outcome": OUTCOME_IMMUNE},
        ]
        self.assertEqual(worst_outcome(records), OUTCOME_MARGIN_INSUFFICIENT)

    def test_an_unassessed_class_outranks_a_credible_flip(self):
        records = [{"outcome": OUTCOME_FLIP_CREDIBLE}, {"outcome": OUTCOME_NOT_ASSESSED}]
        self.assertEqual(worst_outcome(records), OUTCOME_NOT_ASSESSED)

    def test_an_unrecognised_outcome_rejected(self):
        with self.assertRaises(ValueError):
            worst_outcome([{"outcome": "vibes-ok"}])

    def test_an_empty_record_set_rejected(self):
        with self.assertRaises(ValueError):
            worst_outcome([])


class DeviceAssessmentTests(unittest.TestCase):
    def test_a_fully_covered_device_is_demonstrated(self):
        result = assess_state_immunity(_device())
        self.assertEqual(result["verdict"], DEVICE_IMMUNE)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["unassessed_classes"], [])

    def test_an_unassessed_class_outranks_everything_else(self):
        declared = _perturbations()
        del declared[ELECTROSTATIC_DISCHARGE]
        declared[RADIATED_EM_FIELD] = {
            "environment_level": 50.0,
            "immunity_level": 20.0,
            "provisions": [SHIELDED_STATE_HARNESS],
        }
        result = assess_state_immunity(_device(perturbations=declared))
        self.assertEqual(result["verdict"], DEVICE_NOT_ASSESSED)
        self.assertEqual(result["unassessed_classes"], [ELECTROSTATIC_DISCHARGE])

    def test_the_assessment_requirement_can_be_waived(self):
        declared = _perturbations()
        del declared[ELECTROSTATIC_DISCHARGE]
        result = assess_state_immunity(
            _device(perturbations=declared),
            _policy(require_every_class_assessed=False),
        )
        self.assertEqual(result["verdict"], DEVICE_IMMUNE)
        self.assertEqual(result["unassessed_classes"], [ELECTROSTATIC_DISCHARGE])

    def test_a_credible_flip_is_the_device_verdict(self):
        declared = _perturbations(
            **{
                POWER_BUS_TRANSIENT: {
                    "environment_level": 80.0,
                    "immunity_level": 25.0,
                    "provisions": [INPUT_TRANSIENT_FILTER],
                }
            }
        )
        result = assess_state_immunity(_device(perturbations=declared))
        self.assertEqual(result["verdict"], DEVICE_FLIP_CREDIBLE)

    def test_a_self_corrected_flip_sits_below_a_credible_one(self):
        declared = _perturbations(
            **{
                POWER_BUS_TRANSIENT: {
                    "environment_level": 80.0,
                    "immunity_level": 25.0,
                    "provisions": [INPUT_TRANSIENT_FILTER, PERIODIC_STATE_REFRESH],
                }
            }
        )
        result = assess_state_immunity(_device(perturbations=declared))
        self.assertEqual(result["verdict"], DEVICE_SELF_CORRECTED)

    def test_a_missing_provision_is_reported(self):
        declared = _perturbations(
            **{
                POWER_BUS_TRANSIENT: {
                    "environment_level": 25.0,
                    "immunity_level": 400.0,
                    "provisions": [],
                }
            }
        )
        result = assess_state_immunity(_device(perturbations=declared))
        self.assertEqual(result["verdict"], DEVICE_NO_PROVISION)

    def test_a_thin_margin_is_reported_as_insufficient(self):
        declared = _perturbations(
            **{
                POWER_BUS_TRANSIENT: {
                    "environment_level": 25.0,
                    "immunity_level": 30.0,
                    "provisions": [INPUT_TRANSIENT_FILTER],
                }
            }
        )
        result = assess_state_immunity(_device(perturbations=declared))
        self.assertEqual(result["verdict"], DEVICE_MARGIN_INSUFFICIENT)

    def test_an_unrecognised_declared_class_rejected(self):
        declared = _perturbations()
        declared["cosmic-vibes"] = {"environment_level": 1.0, "immunity_level": 2.0}
        with self.assertRaises(ValueError):
            assess_state_immunity(_device(perturbations=declared))

    def test_an_empty_perturbation_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_state_immunity(_device(perturbations={}))

    def test_a_non_mapping_device_rejected(self):
        with self.assertRaises(ValueError):
            assess_state_immunity(["latch"])

    def test_every_class_is_assessed_exactly_once(self):
        result = assess_state_immunity(_device())
        assessed = [record["class"] for record in result["classes"]]
        self.assertEqual(assessed, list(PERTURBATION_CLASSES))

    def test_every_finding_is_a_readable_sentence(self):
        declared = _perturbations(
            **{
                POWER_BUS_TRANSIENT: {
                    "environment_level": 80.0,
                    "immunity_level": 25.0,
                    "provisions": [INPUT_TRANSIENT_FILTER],
                }
            }
        )
        result = assess_state_immunity(_device(perturbations=declared))
        self.assertTrue(result["findings"])
        for note in result["findings"]:
            self.assertIsInstance(note, str)
            self.assertGreater(len(note), 20)


if __name__ == "__main__":
    unittest.main()
