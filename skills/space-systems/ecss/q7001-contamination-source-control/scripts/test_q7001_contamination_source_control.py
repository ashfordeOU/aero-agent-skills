"""Contract tests for the contamination source-control design logic."""

import copy
import unittest

from q7001_contamination_source_control_logic import (
    BUDGET_TOLERANCE,
    CURRENCIES,
    assess_source_control,
    control_retention_factor,
    deposited_contribution,
    dominant_sources,
    evaluate_source,
    rank_sources,
    source_emission_per_s,
    temperature_factor,
    validate_fraction,
    validate_positive,
)


def sample_sources():
    return [
        {
            "name": "harness adhesive",
            "kind": "adhesive",
            "currency": "molecular",
            "specific_rate": 2.0,
            "area_m2": 0.5,
            "view_factor": 0.1,
            "capture_fraction": 0.5,
            "duration_s": 1000.0,
            "receiver_area_m2": 2.5,
        },
        {
            "name": "gimbal grease",
            "kind": "lubricant",
            "currency": "molecular",
            "specific_rate": 1.0,
            "area_m2": 0.1,
            "view_factor": 0.2,
            "capture_fraction": 0.5,
            "duration_s": 1000.0,
            "receiver_area_m2": 2.5,
        },
        {
            "name": "blanket outer layer",
            "kind": "outgassing-surface",
            "currency": "molecular",
            "specific_rate": 0.5,
            "area_m2": 2.0,
            "view_factor": 0.02,
            "capture_fraction": 0.25,
            "duration_s": 1000.0,
            "receiver_area_m2": 2.5,
        },
        {
            "name": "hinge wear debris",
            "kind": "particulate-shedder",
            "currency": "particulate",
            "specific_rate": 1.0e-4,
            "area_m2": 0.05,
            "view_factor": 0.4,
            "capture_fraction": 1.0,
            "duration_s": 1000.0,
            "receiver_area_m2": 2.5,
        },
    ]


def sample_controls():
    return [
        {
            "name": "vacuum bake",
            "applies_to": ["adhesive", "outgassing-surface"],
            "effectiveness": 0.9,
            "verified": True,
        },
        {
            "name": "labyrinth seal",
            "applies_to": ["lubricant"],
            "effectiveness": 0.75,
            "verified": True,
        },
        {
            "name": "debris shroud",
            "applies_to": ["particulate-shedder"],
            "effectiveness": 0.5,
            "verified": True,
        },
    ]


class ValidationTests(unittest.TestCase):
    def test_positive_returns_float(self):
        self.assertAlmostEqual(validate_positive(3, "x"), 3.0, places=9)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(True, "x")

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(float("inf"), "x")

    def test_fraction_accepts_unity_by_default(self):
        self.assertAlmostEqual(validate_fraction(1.0, "f"), 1.0, places=9)

    def test_fraction_rejects_unity_when_closed(self):
        with self.assertRaises(ValueError):
            validate_fraction(1.0, "f", allow_one=False)

    def test_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_fraction(1.4, "f")


class TemperatureFactorTests(unittest.TestCase):
    def test_measurement_temperature_gives_unity(self):
        self.assertAlmostEqual(temperature_factor(300.0, 300.0, 6000.0), 1.0, places=9)

    def test_zero_activation_gives_unity_at_any_temperature(self):
        self.assertAlmostEqual(temperature_factor(400.0, 300.0, 0.0), 1.0, places=9)

    def test_hotter_source_emits_more(self):
        self.assertGreater(
            temperature_factor(340.0, 300.0, 6000.0),
            temperature_factor(310.0, 300.0, 6000.0),
        )

    def test_colder_source_emits_less_than_unity(self):
        self.assertLess(temperature_factor(280.0, 300.0, 6000.0), 1.0)

    def test_two_steps_compose_into_one(self):
        first = temperature_factor(320.0, 300.0, 6000.0)
        second = temperature_factor(340.0, 320.0, 6000.0)
        single = temperature_factor(340.0, 300.0, 6000.0)
        self.assertAlmostEqual(first * second, single, places=9)

    def test_reciprocal_step_undoes_the_factor(self):
        up = temperature_factor(340.0, 300.0, 6000.0)
        down = temperature_factor(300.0, 340.0, 6000.0)
        self.assertAlmostEqual(up * down, 1.0, places=9)

    def test_zero_temperature_rejected(self):
        with self.assertRaises(ValueError):
            temperature_factor(0.0, 300.0, 6000.0)

    def test_negative_activation_rejected(self):
        with self.assertRaises(ValueError):
            temperature_factor(300.0, 300.0, -10.0)


class EmissionTests(unittest.TestCase):
    def test_emission_is_rate_times_area(self):
        self.assertAlmostEqual(source_emission_per_s(2.0, 0.5), 1.0, places=9)

    def test_temperature_factor_scales_the_emission(self):
        self.assertAlmostEqual(source_emission_per_s(2.0, 0.5, 3.0), 3.0, places=9)

    def test_zero_specific_rate_is_allowed(self):
        self.assertAlmostEqual(source_emission_per_s(0.0, 0.5), 0.0, places=9)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            source_emission_per_s(2.0, 0.0)

    def test_deposited_contribution_spreads_over_the_receiver(self):
        self.assertAlmostEqual(
            deposited_contribution(1.0, 0.1, 0.5, 1000.0, 2.5), 20.0, places=9
        )

    def test_halving_the_view_factor_halves_the_deposit(self):
        full = deposited_contribution(1.0, 0.2, 0.5, 1000.0, 2.5)
        half = deposited_contribution(1.0, 0.1, 0.5, 1000.0, 2.5)
        self.assertAlmostEqual(half, full / 2.0, places=9)

    def test_view_factor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            deposited_contribution(1.0, 1.2, 0.5, 1000.0, 2.5)

    def test_zero_receiver_area_rejected(self):
        with self.assertRaises(ValueError):
            deposited_contribution(1.0, 0.1, 0.5, 1000.0, 0.0)


class ControlCreditTests(unittest.TestCase):
    def test_applicable_verified_control_is_credited(self):
        credit = control_retention_factor("adhesive", sample_controls())
        self.assertAlmostEqual(credit["retention"], 0.1, places=9)
        self.assertEqual(credit["credited"], ["vacuum bake"])

    def test_control_for_another_kind_is_not_credited(self):
        credit = control_retention_factor("lubricant", [sample_controls()[0]])
        self.assertAlmostEqual(credit["retention"], 1.0, places=9)
        self.assertEqual(credit["credited"], [])

    def test_two_applicable_controls_multiply(self):
        controls = sample_controls()
        controls.append(
            {
                "name": "getter plate",
                "applies_to": ["adhesive"],
                "effectiveness": 0.5,
                "verified": True,
            }
        )
        credit = control_retention_factor("adhesive", controls)
        self.assertAlmostEqual(credit["retention"], 0.05, places=9)

    def test_unverified_control_earns_no_credit_and_is_flagged(self):
        controls = sample_controls()
        controls[0]["verified"] = False
        credit = control_retention_factor("adhesive", controls)
        self.assertAlmostEqual(credit["retention"], 1.0, places=9)
        self.assertEqual(len(credit["findings"]), 1)

    def test_no_controls_leaves_the_source_uncontrolled(self):
        self.assertAlmostEqual(
            control_retention_factor("adhesive", None)["retention"], 1.0, places=9
        )

    def test_control_credited_twice_rejected(self):
        controls = sample_controls() + [sample_controls()[0]]
        with self.assertRaises(ValueError):
            control_retention_factor("adhesive", controls)

    def test_total_effectiveness_rejected(self):
        controls = [
            {
                "name": "perfect barrier",
                "applies_to": ["adhesive"],
                "effectiveness": 1.0,
                "verified": True,
            }
        ]
        with self.assertRaises(ValueError):
            control_retention_factor("adhesive", controls)

    def test_control_naming_an_unknown_kind_rejected(self):
        controls = sample_controls()
        controls[0]["applies_to"] = ["propellant"]
        with self.assertRaises(ValueError):
            control_retention_factor("adhesive", controls)

    def test_unknown_source_kind_rejected(self):
        with self.assertRaises(ValueError):
            control_retention_factor("mystery", sample_controls())

    def test_non_boolean_verified_flag_rejected(self):
        controls = sample_controls()
        controls[0]["verified"] = "yes"
        with self.assertRaises(ValueError):
            control_retention_factor("adhesive", controls)


class EvaluateSourceTests(unittest.TestCase):
    def test_uncontrolled_and_controlled_contributions(self):
        record = evaluate_source(sample_sources()[0], sample_controls())
        self.assertAlmostEqual(record["uncontrolled"], 20.0, places=9)
        self.assertAlmostEqual(record["contribution"], 2.0, places=9)

    def test_lubricant_takes_its_own_control(self):
        record = evaluate_source(sample_sources()[1], sample_controls())
        self.assertAlmostEqual(record["contribution"], 1.0, places=9)

    def test_temperature_scaling_raises_the_contribution(self):
        source = dict(
            sample_sources()[0], temperature_k=340.0, reference_k=300.0,
            activation_k=6000.0
        )
        record = evaluate_source(source, sample_controls())
        self.assertGreater(record["contribution"], 2.0)
        self.assertAlmostEqual(
            record["contribution"], 2.0 * record["temperature_factor"], places=9
        )

    def test_partial_temperature_scaling_rejected(self):
        source = dict(sample_sources()[0], temperature_k=340.0)
        with self.assertRaises(ValueError):
            evaluate_source(source, sample_controls())

    def test_unknown_currency_rejected(self):
        source = dict(sample_sources()[0], currency="thermal")
        with self.assertRaises(ValueError):
            evaluate_source(source, sample_controls())

    def test_unknown_kind_rejected(self):
        source = dict(sample_sources()[0], kind="propellant")
        with self.assertRaises(ValueError):
            evaluate_source(source, sample_controls())

    def test_missing_source_key_rejected(self):
        source = sample_sources()[0]
        del source["view_factor"]
        with self.assertRaises(ValueError):
            evaluate_source(source, sample_controls())

    def test_non_mapping_source_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_source(["adhesive"], sample_controls())


class RankingTests(unittest.TestCase):
    def _records(self):
        return [
            evaluate_source(s, sample_controls()) for s in sample_sources()[:3]
        ]

    def test_ranked_largest_first(self):
        names = [r["name"] for r in rank_sources(self._records())]
        self.assertEqual(names[0], "harness adhesive")
        self.assertEqual(names[-1], "blanket outer layer")

    def test_tie_broken_by_name(self):
        records = [
            {"name": "beta", "contribution": 1.0},
            {"name": "alpha", "contribution": 1.0},
        ]
        self.assertEqual([r["name"] for r in rank_sources(records)][0], "alpha")

    def test_empty_record_set_rejected(self):
        with self.assertRaises(ValueError):
            rank_sources([])

    def test_malformed_record_rejected(self):
        with self.assertRaises(ValueError):
            rank_sources([{"name": "alpha"}])

    def test_dominant_set_is_the_leading_contributors(self):
        self.assertEqual(
            dominant_sources(self._records(), 0.8),
            ["harness adhesive", "gimbal grease"],
        )

    def test_full_share_takes_every_source(self):
        self.assertEqual(len(dominant_sources(self._records(), 1.0)), 3)

    def test_small_share_takes_only_the_largest(self):
        self.assertEqual(dominant_sources(self._records(), 0.5), ["harness adhesive"])

    def test_all_zero_contributions_give_an_empty_dominant_set(self):
        records = [{"name": "a", "contribution": 0.0}, {"name": "b", "contribution": 0.0}]
        self.assertEqual(dominant_sources(records, 0.8), [])


class AssessSourceControlTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "sources": sample_sources(),
            "controls": sample_controls(),
            "allocations": {"molecular": 5.0, "particulate": 1.0e-3},
        }
        spec.update(overrides)
        return copy.deepcopy(spec)

    def test_controlled_design_is_compliant(self):
        result = assess_source_control(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_totals_are_kept_in_separate_currencies(self):
        result = assess_source_control(self._spec())
        self.assertAlmostEqual(result["totals"]["molecular"], 3.2, places=9)
        self.assertAlmostEqual(result["totals"]["particulate"], 4.0e-4, places=9)
        self.assertEqual(sorted(result["totals"]), sorted(CURRENCIES))

    def test_total_exactly_at_the_allocation_is_within_it(self):
        spec = self._spec()
        spec["allocations"] = {"molecular": 3.2}
        result = assess_source_control(spec)
        self.assertTrue(result["compliant"])
        self.assertLessEqual(
            result["totals"]["molecular"] - 3.2, BUDGET_TOLERANCE * 3.2
        )

    def test_molecular_overrun_is_flagged(self):
        spec = self._spec()
        spec["allocations"] = {"molecular": 1.0}
        result = assess_source_control(spec)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("molecular" in f for f in result["findings"]))

    def test_uncontrolled_dominant_source_is_flagged(self):
        spec = self._spec()
        spec["controls"] = [c for c in spec["controls"] if c["name"] != "vacuum bake"]
        result = assess_source_control(spec)
        self.assertTrue(
            any("harness adhesive" in f and "dominates" in f for f in result["findings"])
        )

    def test_unverified_control_surfaces_in_the_rolled_up_findings(self):
        spec = self._spec()
        spec["controls"][1]["verified"] = False
        result = assess_source_control(spec)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("verification basis" in f for f in result["findings"]))

    def test_ranking_is_reported(self):
        result = assess_source_control(self._spec())
        self.assertEqual(result["ranked"][0], "harness adhesive")

    def test_dominant_set_reported_per_currency(self):
        result = assess_source_control(self._spec())
        self.assertEqual(result["dominant"]["particulate"], ["hinge wear debris"])

    def test_duplicate_source_rejected(self):
        spec = self._spec()
        spec["sources"].append(spec["sources"][0])
        with self.assertRaises(ValueError):
            assess_source_control(spec)

    def test_empty_source_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_source_control(self._spec(sources=[]))

    def test_allocation_in_an_unknown_currency_rejected(self):
        spec = self._spec()
        spec["allocations"] = {"thermal": 1.0}
        with self.assertRaises(ValueError):
            assess_source_control(spec)

    def test_missing_sources_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_source_control({"controls": sample_controls()})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_source_control(["sources"])


if __name__ == "__main__":
    unittest.main()
