#!/usr/bin/env python3
"""Gate 3 contract test for e2007-power-lead-susceptibility-purpose.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_power_lead_susceptibility_purpose.py
"""

import unittest

from e2007_power_lead_susceptibility_purpose_logic import (
    RESPONSE_DEGRADED,
    RESPONSE_MALFUNCTION,
    RESPONSE_TOLERANT,
    SUPPLY_LEAD_KINDS,
    assess_power_lead_susceptibility_purpose,
    at_least,
    at_most,
    categorize_response,
    deviation_ratio,
    functions_without_coverage,
    injections_on_non_supply_leads,
    is_supply_lead,
    leads_without_injection,
    non_supply_leads,
    supply_leads,
    undeclared_injection_targets,
    under_driven_injections,
    undisturbed_sub_bands,
    validate_injection,
    validate_injections,
    validate_lead,
    validate_leads,
    validate_observation,
    validate_observations,
)

BAND_START = 30.0
BAND_STOP = 150.0e6
DECLARED_LEVEL = 100.0


def lead(lead_id="pwr-a", kind="primary-power", voltage=28.0, current=3.0):
    return {
        "lead_id": lead_id,
        "kind": kind,
        "nominal_voltage_v": voltage,
        "nominal_current_a": current,
    }


def lead_set():
    return [
        lead("pwr-a", "primary-power"),
        lead("pwr-rtn", "power-return", voltage=0.0),
        lead("tm-1", "signal", voltage=5.0, current=0.01),
    ]


def injection(
    lead_id="pwr-a",
    start=BAND_START,
    stop=BAND_STOP,
    level=DECLARED_LEVEL,
    waveform="sinusoidal",
):
    return {
        "lead_id": lead_id,
        "waveform": waveform,
        "start_hz": start,
        "stop_hz": stop,
        "level_dbuv": level,
    }


def injection_plan():
    return [injection("pwr-a"), injection("pwr-rtn")]


def observation(
    function_id="bus-voltage",
    lead_id="pwr-a",
    deviation=0.4,
    allowed=1.0,
    recovering=True,
):
    return {
        "function_id": function_id,
        "lead_id": lead_id,
        "deviation": deviation,
        "allowed_deviation": allowed,
        "self_recovering": recovering,
    }


def observation_set():
    return [observation("bus-voltage"), observation("telemetry-frame", deviation=0.1)]


class TestLeadValidation(unittest.TestCase):
    def test_lead_is_normalized(self):
        record = validate_lead(lead())
        self.assertEqual(record["kind"], "primary-power")

    def test_unknown_lead_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_lead(lead(kind="mystery"))

    def test_negative_current_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_lead(lead(current=-1.0))

    def test_boolean_voltage_is_not_a_number(self):
        record = lead()
        record["nominal_voltage_v"] = True
        with self.assertRaises(ValueError):
            validate_lead(record)

    def test_empty_lead_set_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_leads([])

    def test_leads_sort_by_identifier(self):
        ordered = validate_leads(list(reversed(lead_set())))
        self.assertEqual(ordered[0]["lead_id"], "pwr-a")


class TestScope(unittest.TestCase):
    def test_every_supply_kind_is_in_scope(self):
        for kind in SUPPLY_LEAD_KINDS:
            self.assertTrue(is_supply_lead(lead(kind=kind)))

    def test_a_signal_lead_is_out_of_scope(self):
        self.assertFalse(is_supply_lead(lead(kind="signal")))

    def test_supply_leads_exclude_the_signal_lead(self):
        names = [entry["lead_id"] for entry in supply_leads(lead_set())]
        self.assertEqual(names, ["pwr-a", "pwr-rtn"])

    def test_non_supply_leads_names_the_signal_lead(self):
        names = [entry["lead_id"] for entry in non_supply_leads(lead_set())]
        self.assertEqual(names, ["tm-1"])


class TestInjectionValidation(unittest.TestCase):
    def test_injection_is_normalized(self):
        record = validate_injection(injection())
        self.assertAlmostEqual(record["level_dbuv"], DECLARED_LEVEL, places=9)

    def test_inverted_injection_band_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_injection(injection(start=BAND_STOP, stop=BAND_START))

    def test_unknown_waveform_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_injection(injection(waveform="chirp"))

    def test_empty_injection_plan_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_injections([])

    def test_injections_sort_by_lead_then_frequency(self):
        ordered = validate_injections(list(reversed(injection_plan())))
        self.assertEqual(ordered[0]["lead_id"], "pwr-a")


class TestPlanCoverage(unittest.TestCase):
    def test_a_full_plan_leaves_no_supply_lead_undisturbed(self):
        self.assertEqual(leads_without_injection(lead_set(), injection_plan()), [])

    def test_a_missing_return_injection_is_named(self):
        missing = leads_without_injection(lead_set(), [injection("pwr-a")])
        self.assertEqual(missing, ["pwr-rtn"])

    def test_injection_on_a_signal_lead_is_out_of_scope(self):
        stray = injections_on_non_supply_leads(
            lead_set(), injection_plan() + [injection("tm-1")]
        )
        self.assertEqual(len(stray), 1)
        self.assertEqual(stray[0]["lead_id"], "tm-1")

    def test_an_undeclared_target_is_named(self):
        targets = undeclared_injection_targets(
            lead_set(), injection_plan() + [injection("pwr-b")]
        )
        self.assertEqual(targets, ["pwr-b"])

    def test_touching_injection_spans_leave_no_undisturbed_sub_band(self):
        plan = [
            injection("pwr-a", BAND_START, 1.0e6),
            injection("pwr-a", 1.0e6, BAND_STOP),
        ]
        self.assertEqual(
            undisturbed_sub_bands(plan, "pwr-a", BAND_START, BAND_STOP), []
        )

    def test_a_hole_between_injection_spans_is_exposed(self):
        plan = [
            injection("pwr-a", BAND_START, 1.0e6),
            injection("pwr-a", 2.0e6, BAND_STOP),
        ]
        gaps = undisturbed_sub_bands(plan, "pwr-a", BAND_START, BAND_STOP)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0]["span_hz"], 1.0e6, places=3)

    def test_a_lead_with_no_injection_is_undisturbed_across_the_whole_band(self):
        gaps = undisturbed_sub_bands(injection_plan(), "pwr-c", BAND_START, BAND_STOP)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0]["span_hz"], BAND_STOP - BAND_START, places=3)

    def test_an_inverted_declared_band_is_rejected(self):
        with self.assertRaises(ValueError):
            undisturbed_sub_bands(injection_plan(), "pwr-a", BAND_STOP, BAND_START)

    def test_an_injection_at_the_declared_level_is_not_under_driven(self):
        self.assertEqual(under_driven_injections(injection_plan(), DECLARED_LEVEL), [])

    def test_an_injection_below_the_declared_level_is_under_driven(self):
        weak = under_driven_injections([injection(level=88.0)], DECLARED_LEVEL)
        self.assertEqual(len(weak), 1)


class TestObservations(unittest.TestCase):
    def test_observation_is_normalized(self):
        record = validate_observation(observation())
        self.assertAlmostEqual(record["allowed_deviation"], 1.0, places=9)

    def test_a_zero_allowance_makes_the_aim_undecidable_and_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_observation(observation(allowed=0.0))

    def test_a_negative_deviation_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_observation(observation(deviation=-0.1))

    def test_a_non_boolean_recovery_flag_is_rejected(self):
        record = observation()
        record["self_recovering"] = "yes"
        with self.assertRaises(ValueError):
            validate_observation(record)

    def test_empty_observation_set_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_observations([])

    def test_deviation_ratio_is_deviation_over_allowance(self):
        self.assertAlmostEqual(
            deviation_ratio(observation(deviation=0.5, allowed=2.0)), 0.25, places=9
        )

    def test_a_deviation_inside_the_allowance_is_tolerant(self):
        self.assertEqual(categorize_response(observation()), RESPONSE_TOLERANT)

    def test_a_deviation_exactly_on_the_allowance_is_tolerant(self):
        self.assertEqual(
            categorize_response(observation(deviation=1.0, allowed=1.0)),
            RESPONSE_TOLERANT,
        )

    def test_a_recovering_excursion_is_degraded(self):
        self.assertEqual(
            categorize_response(observation(deviation=1.5, recovering=True)),
            RESPONSE_DEGRADED,
        )

    def test_a_non_recovering_excursion_is_a_malfunction(self):
        self.assertEqual(
            categorize_response(observation(deviation=1.5, recovering=False)),
            RESPONSE_MALFUNCTION,
        )

    def test_a_function_watched_only_on_an_undisturbed_lead_is_uncovered(self):
        watched = [observation("bus-voltage", lead_id="tm-1")]
        self.assertEqual(
            functions_without_coverage(watched, lead_set(), injection_plan()),
            ["bus-voltage"],
        )

    def test_a_function_watched_on_a_driven_supply_lead_is_covered(self):
        self.assertEqual(
            functions_without_coverage(observation_set(), lead_set(), injection_plan()),
            [],
        )


class TestBoundHelpers(unittest.TestCase):
    def test_at_least_absorbs_representation_error(self):
        self.assertTrue(at_least(0.1 + 0.2, 0.3))

    def test_at_most_absorbs_representation_error(self):
        self.assertTrue(at_most(0.3, 0.1 + 0.2))


class TestAssessment(unittest.TestCase):
    def test_a_sound_plan_can_demonstrate_the_aim(self):
        report = assess_power_lead_susceptibility_purpose(
            lead_set(),
            injection_plan(),
            observation_set(),
            BAND_START,
            BAND_STOP,
            DECLARED_LEVEL,
        )
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], "aim-demonstrable")
        self.assertEqual(report["in_scope_leads"], ["pwr-a", "pwr-rtn"])

    def test_an_undisturbed_return_lead_breaks_the_aim(self):
        report = assess_power_lead_susceptibility_purpose(
            lead_set(),
            [injection("pwr-a")],
            observation_set(),
            BAND_START,
            BAND_STOP,
            DECLARED_LEVEL,
        )
        self.assertEqual(report["verdict"], "aim-not-demonstrable")
        self.assertTrue(
            any("no disturbance is injected" in m for m in report["findings"])
        )

    def test_an_undisturbed_lead_is_reported_once_not_twice(self):
        report = assess_power_lead_susceptibility_purpose(
            lead_set(),
            [injection("pwr-a")],
            observation_set(),
            BAND_START,
            BAND_STOP,
            DECLARED_LEVEL,
        )
        matching = [m for m in report["findings"] if "pwr-rtn" in m]
        self.assertEqual(len(matching), 1)

    def test_an_under_driven_injection_breaks_the_aim(self):
        plan = [injection("pwr-a", level=80.0), injection("pwr-rtn")]
        report = assess_power_lead_susceptibility_purpose(
            lead_set(),
            plan,
            observation_set(),
            BAND_START,
            BAND_STOP,
            DECLARED_LEVEL,
        )
        self.assertTrue(any("under the" in m for m in report["findings"]))

    def test_a_non_recovering_function_breaks_the_aim(self):
        watched = [observation("bus-voltage", deviation=3.0, recovering=False)]
        report = assess_power_lead_susceptibility_purpose(
            lead_set(),
            injection_plan(),
            watched,
            BAND_START,
            BAND_STOP,
            DECLARED_LEVEL,
        )
        self.assertTrue(any("does not recover" in m for m in report["findings"]))
        self.assertEqual(report["verdict"], "aim-not-demonstrable")

    def test_a_recovering_function_is_a_limitation_not_a_finding(self):
        watched = [observation("bus-voltage", deviation=1.4, recovering=True)]
        report = assess_power_lead_susceptibility_purpose(
            lead_set(),
            injection_plan(),
            watched,
            BAND_START,
            BAND_STOP,
            DECLARED_LEVEL,
        )
        self.assertEqual(report["findings"], [])
        self.assertTrue(any("but recovers" in m for m in report["limitations"]))
        self.assertEqual(report["verdict"], "aim-demonstrable")

    def test_a_signal_lead_injection_is_a_limitation_not_a_finding(self):
        plan = injection_plan() + [injection("tm-1")]
        report = assess_power_lead_susceptibility_purpose(
            lead_set(),
            plan,
            observation_set(),
            BAND_START,
            BAND_STOP,
            DECLARED_LEVEL,
        )
        self.assertEqual(report["findings"], [])
        self.assertTrue(any("outside the aim" in m for m in report["limitations"]))

    def test_report_carries_a_ratio_per_response(self):
        report = assess_power_lead_susceptibility_purpose(
            lead_set(),
            injection_plan(),
            observation_set(),
            BAND_START,
            BAND_STOP,
            DECLARED_LEVEL,
        )
        self.assertEqual(len(report["responses"]), 2)
        self.assertAlmostEqual(report["responses"][0]["ratio"], 0.4, places=9)

    def test_assessment_propagates_an_empty_plan(self):
        with self.assertRaises(ValueError):
            assess_power_lead_susceptibility_purpose(
                lead_set(), [], observation_set(), BAND_START, BAND_STOP, DECLARED_LEVEL
            )


if __name__ == "__main__":
    unittest.main()
