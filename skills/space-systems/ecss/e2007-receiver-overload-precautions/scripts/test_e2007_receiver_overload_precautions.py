#!/usr/bin/env python3
"""Gate 3 contract test for e2007-receiver-overload-precautions.

Stdlib unittest only, offline, deterministic.
"""

import unittest

from e2007_receiver_overload_precautions_logic import (
    DB_EPS,
    assess_chain,
    assess_overload_precautions,
    attenuation_insertion_check,
    chain_levels_dbm,
    dbm_to_dbuv,
    dbuv_to_dbm,
    evaluate_stage_overload,
    measurement_headroom_db,
    recommend_precautions,
    required_input_attenuation_db,
    stage_gain_db,
    transducer_output_dbuv,
    worst_overload_excess_db,
)


def nominal_chain():
    return [
        {
            "name": "biconical-antenna",
            "kind": "transducer",
            "compression_point_dbm": 10.0,
            "damage_threshold_dbm": 20.0,
        },
        {"name": "coax-run", "kind": "cable", "loss_db": 3.0},
        {
            "name": "low-noise-preamplifier",
            "kind": "preamplifier",
            "gain_db": 30.0,
            "compression_point_dbm": -20.0,
            "damage_threshold_dbm": 0.0,
        },
        {"name": "step-pad", "kind": "attenuator", "loss_db": 10.0},
        {
            "name": "emi-receiver",
            "kind": "receiver",
            "compression_point_dbm": -10.0,
            "damage_threshold_dbm": 10.0,
        },
    ]


def nominal_config(quantity_level_dbuv=80.0):
    return {
        "quantity_level_dbuv": quantity_level_dbuv,
        "transducer_factor_db": 12.0,
        "chain": nominal_chain(),
        "attenuator_step_db": 10.0,
        "available_attenuation_db": 40.0,
        "limit_referred_dbm": -40.0,
        "noise_floor_dbm": -90.0,
        "min_headroom_db": 6.0,
        "insertion_check": {
            "indicated_before_dbuv": 68.0,
            "indicated_after_dbuv": 58.0,
            "inserted_attenuation_db": 10.0,
            "tolerance_db": 1.0,
        },
    }


class TestLevelConversion(unittest.TestCase):
    def test_dbuv_to_dbm_fifty_ohm_offset(self):
        self.assertAlmostEqual(dbuv_to_dbm(107.0), 0.0103, places=3)

    def test_dbm_to_dbuv_round_trip(self):
        self.assertAlmostEqual(dbm_to_dbuv(dbuv_to_dbm(74.0)), 74.0, places=9)

    def test_dbuv_to_dbm_scales_with_impedance(self):
        self.assertAlmostEqual(
            dbuv_to_dbm(100.0, 100.0) - dbuv_to_dbm(100.0, 50.0), -3.0103, places=4
        )

    def test_dbuv_to_dbm_rejects_non_positive_impedance(self):
        with self.assertRaises(ValueError):
            dbuv_to_dbm(60.0, 0.0)

    def test_dbm_to_dbuv_rejects_negative_impedance(self):
        with self.assertRaises(ValueError):
            dbm_to_dbuv(-30.0, -50.0)

    def test_dbuv_to_dbm_rejects_non_numeric_level(self):
        with self.assertRaises(ValueError):
            dbuv_to_dbm("60")

    def test_dbuv_to_dbm_rejects_infinite_level(self):
        with self.assertRaises(ValueError):
            dbuv_to_dbm(float("inf"))


class TestTransducerReferral(unittest.TestCase):
    def test_transducer_output_subtracts_factor(self):
        self.assertAlmostEqual(transducer_output_dbuv(80.0, 12.0), 68.0, places=9)

    def test_transducer_output_handles_negative_factor(self):
        self.assertAlmostEqual(transducer_output_dbuv(80.0, -4.5), 84.5, places=9)

    def test_transducer_output_rejects_nan_factor(self):
        with self.assertRaises(ValueError):
            transducer_output_dbuv(80.0, float("nan"))


class TestStageGain(unittest.TestCase):
    def test_preamplifier_gain_is_positive(self):
        stage = {"name": "lna", "kind": "preamplifier", "gain_db": 30.0}
        self.assertAlmostEqual(stage_gain_db(stage), 30.0, places=9)

    def test_passive_stage_gain_is_negative(self):
        stage = {"name": "pad", "kind": "attenuator", "loss_db": 10.0}
        self.assertAlmostEqual(stage_gain_db(stage), -10.0, places=9)

    def test_transducer_stage_is_unity(self):
        stage = {"name": "probe", "kind": "transducer"}
        self.assertAlmostEqual(stage_gain_db(stage), 0.0, places=9)

    def test_receiver_stage_is_unity(self):
        stage = {"name": "analyser", "kind": "receiver"}
        self.assertAlmostEqual(stage_gain_db(stage), 0.0, places=9)

    def test_unrecognized_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            stage_gain_db({"name": "mystery-box", "kind": "mixer"})

    def test_stage_without_name_is_rejected(self):
        with self.assertRaises(ValueError):
            stage_gain_db({"kind": "cable", "loss_db": 1.0})

    def test_stage_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            stage_gain_db(["cable", 1.0])

    def test_non_positive_preamplifier_gain_is_rejected(self):
        with self.assertRaises(ValueError):
            stage_gain_db({"name": "lna", "kind": "preamplifier", "gain_db": 0.0})

    def test_negative_passive_loss_is_rejected(self):
        with self.assertRaises(ValueError):
            stage_gain_db({"name": "pad", "kind": "attenuator", "loss_db": -3.0})

    def test_damage_threshold_below_compression_is_rejected(self):
        with self.assertRaises(ValueError):
            stage_gain_db(
                {
                    "name": "rx",
                    "kind": "receiver",
                    "compression_point_dbm": -10.0,
                    "damage_threshold_dbm": -20.0,
                }
            )


class TestChainPropagation(unittest.TestCase):
    def test_levels_accumulate_gain_and_loss(self):
        records = chain_levels_dbm(-40.0, nominal_chain())
        self.assertEqual(len(records), 5)
        self.assertAlmostEqual(records[0]["input_dbm"], -40.0, places=9)
        self.assertAlmostEqual(records[1]["input_dbm"], -40.0, places=9)
        self.assertAlmostEqual(records[2]["input_dbm"], -43.0, places=9)
        self.assertAlmostEqual(records[3]["input_dbm"], -13.0, places=9)
        self.assertAlmostEqual(records[4]["input_dbm"], -23.0, places=9)

    def test_empty_chain_is_rejected(self):
        with self.assertRaises(ValueError):
            chain_levels_dbm(-40.0, [])

    def test_duplicate_stage_names_are_rejected(self):
        chain = nominal_chain()
        chain[1]["name"] = chain[0]["name"]
        with self.assertRaises(ValueError):
            chain_levels_dbm(-40.0, chain)

    def test_chain_must_start_at_the_transducer(self):
        with self.assertRaises(ValueError):
            chain_levels_dbm(-40.0, nominal_chain()[1:])

    def test_chain_must_end_at_the_receiver(self):
        with self.assertRaises(ValueError):
            chain_levels_dbm(-40.0, nominal_chain()[:-1])

    def test_interior_receiver_stage_is_rejected(self):
        chain = nominal_chain()
        chain[2] = {"name": "spare-receiver", "kind": "receiver"}
        with self.assertRaises(ValueError):
            chain_levels_dbm(-40.0, chain)

    def test_non_numeric_source_level_is_rejected(self):
        with self.assertRaises(ValueError):
            chain_levels_dbm(None, nominal_chain())


class TestStageOverloadEvaluation(unittest.TestCase):
    def test_stage_inside_its_window_is_linear(self):
        stage = {"name": "rx", "kind": "receiver", "compression_point_dbm": -10.0}
        result = evaluate_stage_overload(stage, -30.0)
        self.assertEqual(result["status"], "linear")
        self.assertAlmostEqual(result["compression_margin_db"], 20.0, places=9)

    def test_representation_error_at_the_compression_point_stays_linear(self):
        stage = {"name": "rx", "kind": "receiver", "compression_point_dbm": 0.3}
        result = evaluate_stage_overload(stage, 0.1 + 0.2)
        self.assertGreater(0.1 + 0.2, 0.3)
        self.assertEqual(result["status"], "linear")

    def test_stage_above_compression_is_overloaded(self):
        stage = {
            "name": "rx",
            "kind": "receiver",
            "compression_point_dbm": -10.0,
            "damage_threshold_dbm": 10.0,
        }
        self.assertEqual(evaluate_stage_overload(stage, -5.0)["status"], "overload")

    def test_stage_above_damage_threshold_is_damage_risk(self):
        stage = {
            "name": "rx",
            "kind": "receiver",
            "compression_point_dbm": -10.0,
            "damage_threshold_dbm": 10.0,
        }
        self.assertEqual(evaluate_stage_overload(stage, 15.0)["status"], "damage-risk")

    def test_active_stage_without_a_declared_window_is_uncategorized(self):
        stage = {"name": "rx", "kind": "receiver"}
        self.assertEqual(evaluate_stage_overload(stage, -5.0)["status"], "uncategorized")

    def test_passive_stage_needs_no_declared_window(self):
        stage = {"name": "coax", "kind": "cable", "loss_db": 2.0}
        self.assertEqual(evaluate_stage_overload(stage, -5.0)["status"], "linear")

    def test_damage_margin_is_reported(self):
        stage = {"name": "rx", "kind": "receiver", "damage_threshold_dbm": 10.0}
        self.assertAlmostEqual(
            evaluate_stage_overload(stage, 4.0)["damage_margin_db"], 6.0, places=9
        )

    def test_non_numeric_input_level_is_rejected(self):
        stage = {"name": "rx", "kind": "receiver", "compression_point_dbm": -10.0}
        with self.assertRaises(ValueError):
            evaluate_stage_overload(stage, "-10")


class TestChainAssessment(unittest.TestCase):
    def test_quiet_chain_is_entirely_linear(self):
        evaluations = assess_chain(-39.0, nominal_chain())
        self.assertTrue(all(e["status"] == "linear" for e in evaluations))

    def test_loud_chain_overloads_preamplifier_and_receiver(self):
        evaluations = assess_chain(1.0, nominal_chain())
        by_name = {e["name"]: e for e in evaluations}
        self.assertEqual(by_name["low-noise-preamplifier"]["status"], "overload")
        self.assertEqual(by_name["emi-receiver"]["status"], "damage-risk")

    def test_chain_boundary_sum_is_absorbed(self):
        chain = [
            {"name": "probe", "kind": "transducer", "compression_point_dbm": 30.0},
            {
                "name": "lna",
                "kind": "preamplifier",
                "gain_db": 0.2,
                "compression_point_dbm": 30.0,
            },
            {"name": "rx", "kind": "receiver", "compression_point_dbm": 0.3},
        ]
        evaluations = assess_chain(0.1, chain)
        self.assertEqual(evaluations[-1]["status"], "linear")


class TestOverloadExcess(unittest.TestCase):
    def test_excess_is_zero_for_a_linear_chain(self):
        evaluations = assess_chain(-39.0, nominal_chain())
        self.assertAlmostEqual(worst_overload_excess_db(evaluations), 0.0, places=9)

    def test_excess_tracks_the_worst_stage(self):
        evaluations = assess_chain(1.0, nominal_chain())
        self.assertAlmostEqual(worst_overload_excess_db(evaluations), 28.0, places=9)

    def test_empty_evaluation_set_is_rejected(self):
        with self.assertRaises(ValueError):
            worst_overload_excess_db([])


class TestAttenuationPlanning(unittest.TestCase):
    def test_linear_chain_needs_no_attenuation(self):
        evaluations = assess_chain(-39.0, nominal_chain())
        plan = required_input_attenuation_db(evaluations, 10.0, 40.0)
        self.assertEqual(plan["steps"], 0)
        self.assertAlmostEqual(plan["required_attenuation_db"], 0.0, places=9)
        self.assertTrue(plan["feasible"])

    def test_excess_rounds_up_to_a_whole_step(self):
        evaluations = assess_chain(1.0, nominal_chain())
        plan = required_input_attenuation_db(evaluations, 10.0, 40.0)
        self.assertEqual(plan["steps"], 3)
        self.assertAlmostEqual(plan["required_attenuation_db"], 30.0, places=9)
        self.assertTrue(plan["feasible"])

    def test_plan_is_infeasible_beyond_the_available_range(self):
        evaluations = assess_chain(1.0, nominal_chain())
        plan = required_input_attenuation_db(evaluations, 10.0, 20.0)
        self.assertFalse(plan["feasible"])

    def test_exactly_available_attenuation_stays_feasible(self):
        evaluations = assess_chain(1.0, nominal_chain())
        plan = required_input_attenuation_db(evaluations, 10.0, 30.0)
        self.assertTrue(plan["feasible"])

    def test_saturated_transducer_cannot_be_fixed_downstream(self):
        evaluations = assess_chain(15.0, nominal_chain())
        plan = required_input_attenuation_db(evaluations, 10.0, 60.0)
        self.assertTrue(plan["transducer_saturated"])
        self.assertFalse(plan["feasible"])

    def test_non_positive_step_is_rejected(self):
        evaluations = assess_chain(1.0, nominal_chain())
        with self.assertRaises(ValueError):
            required_input_attenuation_db(evaluations, 0.0, 40.0)

    def test_negative_available_attenuation_is_rejected(self):
        evaluations = assess_chain(1.0, nominal_chain())
        with self.assertRaises(ValueError):
            required_input_attenuation_db(evaluations, 10.0, -1.0)


class TestPrecautionRecommendation(unittest.TestCase):
    def test_linear_chain_proceeds(self):
        evaluations = assess_chain(-39.0, nominal_chain())
        plan = required_input_attenuation_db(evaluations, 10.0, 40.0)
        self.assertEqual(recommend_precautions(evaluations, plan), ["proceed-with-measurement"])

    def test_overloaded_chain_calls_for_input_attenuation(self):
        evaluations = assess_chain(-15.0, nominal_chain())
        plan = required_input_attenuation_db(evaluations, 10.0, 40.0)
        self.assertIn("insert-input-attenuation", recommend_precautions(evaluations, plan))

    def test_damage_risk_is_the_first_action(self):
        evaluations = assess_chain(1.0, nominal_chain())
        plan = required_input_attenuation_db(evaluations, 10.0, 40.0)
        self.assertEqual(
            recommend_precautions(evaluations, plan)[0], "stop-and-protect-receiver-input"
        )

    def test_saturated_transducer_calls_for_less_coupling(self):
        evaluations = assess_chain(15.0, nominal_chain())
        plan = required_input_attenuation_db(evaluations, 10.0, 60.0)
        self.assertIn("reduce-transducer-coupling", recommend_precautions(evaluations, plan))

    def test_infeasible_plan_calls_for_a_wider_attenuator_range(self):
        evaluations = assess_chain(-15.0, nominal_chain())
        plan = required_input_attenuation_db(evaluations, 10.0, 1.0)
        self.assertIn("extend-attenuator-range", recommend_precautions(evaluations, plan))

    def test_plan_must_be_a_mapping(self):
        evaluations = assess_chain(-15.0, nominal_chain())
        with self.assertRaises(ValueError):
            recommend_precautions(evaluations, 30.0)


class TestMeasurementHeadroom(unittest.TestCase):
    def test_ample_headroom_is_sufficient(self):
        result = measurement_headroom_db(-40.0, -90.0, 6.0, 10.0)
        self.assertAlmostEqual(result["headroom_db"], 40.0, places=9)
        self.assertTrue(result["sufficient"])

    def test_added_attenuation_erodes_headroom(self):
        result = measurement_headroom_db(-40.0, -50.0, 6.0, 8.0)
        self.assertAlmostEqual(result["headroom_db"], 2.0, places=9)
        self.assertFalse(result["sufficient"])

    def test_representation_error_at_the_headroom_boundary_is_absorbed(self):
        result = measurement_headroom_db(0.3, 0.0, 0.1 + 0.2, 0.0)
        self.assertGreater(0.1 + 0.2, 0.3)
        self.assertTrue(result["sufficient"])

    def test_negative_required_headroom_is_rejected(self):
        with self.assertRaises(ValueError):
            measurement_headroom_db(-40.0, -90.0, -1.0, 0.0)

    def test_negative_added_attenuation_is_rejected(self):
        with self.assertRaises(ValueError):
            measurement_headroom_db(-40.0, -90.0, 6.0, -5.0)

    def test_non_numeric_noise_floor_is_rejected(self):
        with self.assertRaises(ValueError):
            measurement_headroom_db(-40.0, "-90", 6.0, 0.0)


class TestInsertionCheck(unittest.TestCase):
    def test_pad_reproduced_within_tolerance_is_linear(self):
        result = attenuation_insertion_check(68.0, 58.2, 10.0, 0.5)
        self.assertAlmostEqual(result["deviation_db"], -0.2, places=9)
        self.assertTrue(result["linear"])
        self.assertEqual(result["verdict"], "linear")

    def test_representation_error_at_the_tolerance_boundary_is_absorbed(self):
        result = attenuation_insertion_check(1.0, 0.0, 0.7, 0.3)
        self.assertGreater(1.0 - 0.7, 0.3)
        self.assertTrue(result["linear"])

    def test_shortfall_beyond_tolerance_signals_compression(self):
        result = attenuation_insertion_check(68.0, 62.0, 10.0, 1.0)
        self.assertFalse(result["linear"])
        self.assertEqual(result["verdict"], "compressed-before-insertion")

    def test_non_positive_inserted_pad_is_rejected(self):
        with self.assertRaises(ValueError):
            attenuation_insertion_check(68.0, 58.0, 0.0, 1.0)

    def test_non_positive_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            attenuation_insertion_check(68.0, 58.0, 10.0, 0.0)

    def test_non_numeric_indicated_level_is_rejected(self):
        with self.assertRaises(ValueError):
            attenuation_insertion_check("68", 58.0, 10.0, 1.0)


class TestEndToEndAssessment(unittest.TestCase):
    def test_quiet_setup_is_compliant(self):
        report = assess_overload_precautions(nominal_config())
        self.assertAlmostEqual(report["terminal_level_dbuv"], 68.0, places=9)
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["compliant"])
        self.assertEqual(report["actions"], ["proceed-with-measurement"])

    def test_loud_setup_reports_overload_findings(self):
        report = assess_overload_precautions(nominal_config(120.0))
        self.assertFalse(report["compliant"])
        self.assertTrue(
            any("above compression point" in f for f in report["findings"])
        )
        self.assertTrue(any("damage threshold" in f for f in report["findings"]))

    def test_missing_insertion_check_is_itself_a_finding(self):
        config = nominal_config()
        del config["insertion_check"]
        report = assess_overload_precautions(config)
        self.assertIn("no attenuation insertion check on record", report["findings"])
        self.assertFalse(report["compliant"])

    def test_failed_insertion_check_is_reported(self):
        config = nominal_config()
        config["insertion_check"]["indicated_after_dbuv"] = 64.0
        report = assess_overload_precautions(config)
        self.assertTrue(
            any("insertion check" in f for f in report["findings"])
        )

    def test_missing_required_key_is_rejected(self):
        config = nominal_config()
        del config["chain"]
        with self.assertRaises(ValueError):
            assess_overload_precautions(config)

    def test_config_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_overload_precautions([("chain", [])])

    def test_named_tolerance_is_far_below_any_engineering_limit(self):
        self.assertLess(DB_EPS, 1e-6)


if __name__ == "__main__":
    unittest.main()
