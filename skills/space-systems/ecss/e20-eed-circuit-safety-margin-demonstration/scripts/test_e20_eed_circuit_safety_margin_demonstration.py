#!/usr/bin/env python3
"""Gate 3 contract test for the clause 6.4.2 margin demonstration leaf.

stdlib unittest, offline, deterministic. Run:
python3 test_e20_eed_circuit_safety_margin_demonstration.py
"""

import unittest

from e20_eed_circuit_safety_margin_demonstration_logic import (
    CIRCUIT_CATEGORIES,
    DEFAULT_MARGIN_LADDER,
    bridgewire_no_fire_power,
    condition_margins,
    demonstrate_circuit,
    derate_no_fire_threshold,
    evidence_is_admissible,
    governing_condition,
    mandated_conditions,
    margin_from_levels,
    margin_from_linear,
    meets_required_margin,
    missing_conditions,
    normalise_demonstration,
    required_margin_db,
    review_demonstrations,
)

FIRING_CONDITIONS = (
    "flight-transmitters-keyed",
    "launch-site-radiated-environment",
    "worst-case-harness-routing",
    "ground-support-equipment-connected",
)


def firing_record(induced=0.05, evidence="instrumented-measurement", conditions=None):
    return {
        "id": "PYRO-1",
        "category": "electro-explosive-device",
        "evidence": evidence,
        "quantity": "current",
        "no_fire_value": 1.0,
        "derating_factor": 0.5,
        "measurements": [
            {"condition": condition, "induced": induced}
            for condition in (conditions if conditions is not None else FIRING_CONDITIONS)
        ],
    }


def decibel_record(induced_db=13.3, category="electro-explosive-device"):
    return {
        "id": "PYRO-DB",
        "category": category,
        "evidence": "instrumented-measurement",
        "threshold_db": 33.3,
        "measurements": [
            {"condition": condition, "induced_db": induced_db}
            for condition in mandated_conditions(category)
        ]
        or [{"condition": "flight-transmitters-keyed", "induced_db": induced_db}],
    }


class MarginLadder(unittest.TestCase):
    def test_firing_circuit_demands_the_widest_separation(self):
        self.assertAlmostEqual(
            required_margin_db("electro-explosive-device"), 20.0, places=9
        )

    def test_safety_critical_demand_is_narrower_than_the_firing_demand(self):
        self.assertLess(
            required_margin_db("safety-critical"),
            required_margin_db("electro-explosive-device"),
        )

    def test_non_critical_circuit_demands_nothing(self):
        self.assertAlmostEqual(required_margin_db("non-critical"), 0.0, places=9)

    def test_every_category_has_a_demand(self):
        for category in CIRCUIT_CATEGORIES:
            self.assertIn(category, DEFAULT_MARGIN_LADDER)

    def test_project_ladder_overrides_the_default(self):
        ladder = dict(DEFAULT_MARGIN_LADDER)
        ladder["safety-critical"] = 10.0
        self.assertAlmostEqual(
            required_margin_db("safety-critical", ladder), 10.0, places=9
        )

    def test_unknown_category_is_rejected(self):
        with self.assertRaises(ValueError):
            required_margin_db("somewhat-critical")

    def test_ladder_missing_the_category_is_rejected(self):
        with self.assertRaises(ValueError):
            required_margin_db("safety-critical", {"non-critical": 0.0})

    def test_negative_demand_is_rejected(self):
        ladder = dict(DEFAULT_MARGIN_LADDER)
        ladder["mission-critical"] = -3.0
        with self.assertRaises(ValueError):
            required_margin_db("mission-critical", ladder)

    def test_non_mapping_ladder_is_rejected(self):
        with self.assertRaises(ValueError):
            required_margin_db("safety-critical", [6.0])


class EvidenceAdmissibility(unittest.TestCase):
    def test_firing_circuit_admits_instrumented_measurement(self):
        self.assertTrue(
            evidence_is_admissible("electro-explosive-device", "instrumented-measurement")
        )

    def test_firing_circuit_refuses_a_paper_argument(self):
        self.assertFalse(evidence_is_admissible("electro-explosive-device", "analysis"))

    def test_firing_circuit_refuses_similarity(self):
        self.assertFalse(evidence_is_admissible("electro-explosive-device", "similarity"))

    def test_safety_critical_circuit_admits_analysis(self):
        self.assertTrue(evidence_is_admissible("safety-critical", "analysis"))

    def test_non_critical_circuit_admits_similarity(self):
        self.assertTrue(evidence_is_admissible("non-critical", "similarity"))

    def test_unknown_evidence_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            evidence_is_admissible("safety-critical", "engineering-judgement")

    def test_unknown_category_for_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            evidence_is_admissible("somewhat-critical", "analysis")


class ThresholdDerivation(unittest.TestCase):
    def test_derating_halves_the_no_fire_value(self):
        self.assertAlmostEqual(derate_no_fire_threshold(1.0, 0.5), 0.5, places=9)

    def test_unity_factor_leaves_the_value_alone(self):
        self.assertAlmostEqual(derate_no_fire_threshold(0.8, 1.0), 0.8, places=9)

    def test_zero_factor_is_rejected(self):
        with self.assertRaises(ValueError):
            derate_no_fire_threshold(1.0, 0.0)

    def test_factor_above_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            derate_no_fire_threshold(1.0, 1.2)

    def test_non_positive_no_fire_value_is_rejected(self):
        with self.assertRaises(ValueError):
            derate_no_fire_threshold(0.0, 0.5)

    def test_non_numeric_no_fire_value_is_rejected(self):
        with self.assertRaises(ValueError):
            derate_no_fire_threshold("one amp", 0.5)

    def test_bridgewire_power_follows_the_square_law(self):
        self.assertAlmostEqual(bridgewire_no_fire_power(1.0, 1.05), 1.05, places=9)

    def test_doubling_the_current_quadruples_the_power(self):
        single = bridgewire_no_fire_power(0.5, 2.0)
        double = bridgewire_no_fire_power(1.0, 2.0)
        self.assertAlmostEqual(double / single, 4.0, places=9)

    def test_non_positive_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            bridgewire_no_fire_power(1.0, 0.0)


class SeparationComputation(unittest.TestCase):
    def test_current_ratio_of_ten_is_twenty_decibels(self):
        self.assertAlmostEqual(margin_from_linear(0.5, 0.05, "current"), 20.0, places=9)

    def test_power_ratio_of_ten_is_ten_decibels(self):
        self.assertAlmostEqual(margin_from_linear(1.0, 0.1, "power"), 10.0, places=9)

    def test_voltage_follows_the_field_quantity_law(self):
        self.assertAlmostEqual(margin_from_linear(10.0, 1.0, "voltage"), 20.0, places=9)

    def test_induced_level_above_the_threshold_is_a_negative_separation(self):
        self.assertLess(margin_from_linear(0.5, 5.0, "current"), 0.0)

    def test_unknown_quantity_is_rejected(self):
        with self.assertRaises(ValueError):
            margin_from_linear(1.0, 0.1, "flux")

    def test_zero_induced_level_is_rejected(self):
        with self.assertRaises(ValueError):
            margin_from_linear(1.0, 0.0, "current")

    def test_negative_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            margin_from_linear(-1.0, 0.1, "current")

    def test_decibel_levels_subtract(self):
        self.assertAlmostEqual(margin_from_levels(33.0, 13.0), 20.0, places=9)

    def test_non_numeric_decibel_level_is_rejected(self):
        with self.assertRaises(ValueError):
            margin_from_levels("33 dBm", 13.0)

    def test_boolean_level_is_rejected(self):
        with self.assertRaises(ValueError):
            margin_from_levels(True, 13.0)


class DemandComparison(unittest.TestCase):
    def test_a_decibel_difference_a_hair_under_the_demand_still_meets_it(self):
        margin = margin_from_levels(33.3, 13.3)
        self.assertLess(margin, 20.0)
        self.assertTrue(meets_required_margin(margin, 20.0))

    def test_a_genuine_shortfall_does_not_meet_the_demand(self):
        self.assertFalse(meets_required_margin(19.0, 20.0))

    def test_surplus_separation_meets_the_demand(self):
        self.assertTrue(meets_required_margin(26.0, 20.0))

    def test_negative_separation_never_meets_a_positive_demand(self):
        self.assertFalse(meets_required_margin(-4.0, 6.0))

    def test_negative_demand_is_rejected(self):
        with self.assertRaises(ValueError):
            meets_required_margin(20.0, -6.0)

    def test_non_numeric_separation_is_rejected(self):
        with self.assertRaises(ValueError):
            meets_required_margin("plenty", 20.0)


class RecordNormalisation(unittest.TestCase):
    def test_linear_record_is_derated_once(self):
        record = normalise_demonstration(firing_record())
        self.assertAlmostEqual(record["threshold"], 0.5, places=9)
        self.assertIsNone(record["threshold_db"])

    def test_decibel_record_keeps_its_scale(self):
        record = normalise_demonstration(decibel_record())
        self.assertIsNone(record["threshold"])
        self.assertAlmostEqual(record["threshold_db"], 33.3, places=9)

    def test_both_scales_at_once_is_rejected(self):
        record = firing_record()
        record["threshold_db"] = 33.3
        with self.assertRaises(ValueError):
            normalise_demonstration(record)

    def test_no_threshold_at_all_is_rejected(self):
        record = firing_record()
        del record["no_fire_value"]
        with self.assertRaises(ValueError):
            normalise_demonstration(record)

    def test_empty_circuit_id_is_rejected(self):
        record = firing_record()
        record["id"] = "  "
        with self.assertRaises(ValueError):
            normalise_demonstration(record)

    def test_unknown_category_in_a_record_is_rejected(self):
        record = firing_record()
        record["category"] = "ordnance-ish"
        with self.assertRaises(ValueError):
            normalise_demonstration(record)

    def test_unknown_evidence_in_a_record_is_rejected(self):
        record = firing_record()
        record["evidence"] = "vendor-assurance"
        with self.assertRaises(ValueError):
            normalise_demonstration(record)

    def test_unknown_quantity_in_a_record_is_rejected(self):
        record = firing_record()
        record["quantity"] = "charge"
        with self.assertRaises(ValueError):
            normalise_demonstration(record)

    def test_missing_measurement_list_is_rejected(self):
        record = firing_record()
        del record["measurements"]
        with self.assertRaises(ValueError):
            normalise_demonstration(record)

    def test_measurement_without_a_condition_is_rejected(self):
        record = firing_record()
        record["measurements"][0]["condition"] = ""
        with self.assertRaises(ValueError):
            normalise_demonstration(record)

    def test_repeated_operating_condition_is_rejected(self):
        record = firing_record()
        record["measurements"].append(dict(record["measurements"][0]))
        with self.assertRaises(ValueError):
            normalise_demonstration(record)

    def test_measurement_that_is_not_a_mapping_is_rejected(self):
        record = firing_record()
        record["measurements"].append("transmitters-keyed")
        with self.assertRaises(ValueError):
            normalise_demonstration(record)

    def test_non_positive_induced_level_is_rejected(self):
        record = firing_record()
        record["measurements"][0]["induced"] = 0.0
        with self.assertRaises(ValueError):
            normalise_demonstration(record)

    def test_non_mapping_record_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_demonstration("PYRO-1")


class ConditionHandling(unittest.TestCase):
    def test_every_mandated_condition_is_computed(self):
        record = normalise_demonstration(firing_record())
        margins = condition_margins(record)
        self.assertEqual(sorted(margins), sorted(FIRING_CONDITIONS))

    def test_a_firing_circuit_owes_four_conditions(self):
        self.assertEqual(len(mandated_conditions("electro-explosive-device")), 4)

    def test_a_non_critical_circuit_owes_no_condition(self):
        self.assertEqual(mandated_conditions("non-critical"), ())

    def test_unknown_category_has_no_condition_set(self):
        with self.assertRaises(ValueError):
            mandated_conditions("somewhat-critical")

    def test_an_unexercised_condition_is_listed(self):
        record = normalise_demonstration(
            firing_record(conditions=FIRING_CONDITIONS[:2])
        )
        self.assertEqual(
            missing_conditions(record), list(FIRING_CONDITIONS[2:])
        )

    def test_the_smallest_separation_governs(self):
        margins = {"a-condition": 24.0, "b-condition": 18.5, "c-condition": 31.0}
        condition, margin = governing_condition(margins)
        self.assertEqual(condition, "b-condition")
        self.assertAlmostEqual(margin, 18.5, places=9)

    def test_equal_separations_break_on_the_condition_name(self):
        condition, _margin = governing_condition({"b-one": 12.0, "a-one": 12.0})
        self.assertEqual(condition, "a-one")

    def test_governing_nothing_is_rejected(self):
        with self.assertRaises(ValueError):
            governing_condition({})


class CircuitDemonstration(unittest.TestCase):
    def test_a_measured_firing_circuit_with_margin_is_demonstrated(self):
        result = demonstrate_circuit(firing_record())
        self.assertTrue(result["demonstrated"])
        self.assertAlmostEqual(result["governing_margin_db"], 20.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_a_firing_circuit_on_the_exact_demand_is_demonstrated(self):
        result = demonstrate_circuit(decibel_record())
        self.assertLess(result["governing_margin_db"], 20.0)
        self.assertTrue(result["demonstrated"])

    def test_a_firing_circuit_below_the_demand_is_a_finding(self):
        result = demonstrate_circuit(decibel_record(induced_db=20.0))
        self.assertFalse(result["demonstrated"])
        self.assertIn("short of", result["findings"][0])

    def test_a_firing_circuit_argued_on_paper_is_a_finding(self):
        result = demonstrate_circuit(firing_record(evidence="analysis"))
        self.assertFalse(result["demonstrated"])
        self.assertIn("cannot be demonstrated by analysis", result["findings"][0])

    def test_the_same_paper_argument_serves_a_mission_critical_circuit(self):
        record = firing_record(evidence="analysis")
        record["category"] = "mission-critical"
        record["id"] = "SIG-4"
        result = demonstrate_circuit(record)
        self.assertTrue(result["demonstrated"])

    def test_an_unexercised_condition_is_a_finding(self):
        result = demonstrate_circuit(firing_record(conditions=FIRING_CONDITIONS[:3]))
        self.assertFalse(result["demonstrated"])
        self.assertEqual(len(result["missing_conditions"]), 1)

    def test_a_non_critical_circuit_with_no_measurement_is_not_a_finding(self):
        record = firing_record(conditions=[])
        record["category"] = "non-critical"
        record["id"] = "HK-9"
        result = demonstrate_circuit(record)
        self.assertTrue(result["demonstrated"])
        self.assertIsNone(result["governing_margin_db"])

    def test_a_safety_critical_circuit_with_no_measurement_is_a_finding(self):
        record = firing_record(conditions=[])
        record["category"] = "safety-critical"
        record["id"] = "SAFE-2"
        result = demonstrate_circuit(record)
        self.assertFalse(result["demonstrated"])

    def test_a_tailored_ladder_changes_the_verdict(self):
        ladder = dict(DEFAULT_MARGIN_LADDER)
        ladder["electro-explosive-device"] = 26.0
        result = demonstrate_circuit(firing_record(), ladder)
        self.assertFalse(result["demonstrated"])


class AggregateReview(unittest.TestCase):
    def test_a_clean_set_is_demonstrated(self):
        mission = firing_record(conditions=mandated_conditions("mission-critical"))
        mission["id"] = "SIG-4"
        mission["category"] = "mission-critical"
        review = review_demonstrations([firing_record(), mission])
        self.assertTrue(review["demonstrated"])
        self.assertEqual(review["firing_circuit_count"], 1)
        self.assertAlmostEqual(review["worst_margin_db"], 20.0, places=9)

    def test_one_short_circuit_breaks_the_set(self):
        review = review_demonstrations([firing_record(), decibel_record(induced_db=25.0)])
        self.assertFalse(review["demonstrated"])
        self.assertEqual(len(review["findings"]), 1)

    def test_findings_are_ordered_by_circuit_id(self):
        first = decibel_record(induced_db=30.0)
        first["id"] = "AAA-1"
        second = decibel_record(induced_db=30.0)
        second["id"] = "ZZZ-9"
        review = review_demonstrations([second, first])
        self.assertIn("AAA-1", review["findings"][0])
        self.assertIn("ZZZ-9", review["findings"][1])

    def test_duplicate_circuit_id_is_rejected(self):
        with self.assertRaises(ValueError):
            review_demonstrations([firing_record(), firing_record()])

    def test_an_empty_set_is_rejected(self):
        with self.assertRaises(ValueError):
            review_demonstrations([])

    def test_a_missing_set_is_rejected(self):
        with self.assertRaises(ValueError):
            review_demonstrations(None)


if __name__ == "__main__":
    unittest.main()
