"""Contract tests for the clause 5.6.14.5 isochronous requirement-set logic."""

import unittest

from e50_isochronous_requirements_logic import (
    COMPLETE,
    INCOMPLETE,
    INCONSISTENT,
    REQUIRED_FIELDS,
    assess_isochronous_requirements,
    consistency_findings,
    link_utilisation,
    max_permissible_jitter_s,
    minimum_link_rate_bps,
    missing_requirements,
    required_clock_stability_ppm,
    required_playout_buffer_bits,
    serialisation_time_s,
    validate_requirements,
)

GOOD = {
    "period_s": 0.125,
    "jitter_bound_s": 0.03125,
    "latency_bound_s": 0.0625,
    "payload_bits": 8192.0,
    "link_rate_bps": 1048576.0,
    "service_duration_s": 3600.0,
}


def spec(**overrides):
    merged = dict(GOOD)
    merged.update(overrides)
    return merged


class ValidationTests(unittest.TestCase):
    def test_good_set_validates(self):
        self.assertAlmostEqual(validate_requirements(GOOD)["period_s"], 0.125, places=9)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirements([("period_s", 0.125)])

    def test_zero_period_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirements(spec(period_s=0.0))

    def test_negative_jitter_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirements(spec(jitter_bound_s=-0.001))

    def test_boolean_payload_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirements(spec(payload_bits=True))

    def test_text_link_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirements(spec(link_rate_bps="1048576"))

    def test_infinite_latency_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirements(spec(latency_bound_s=float("inf")))

    def test_zero_jitter_is_a_legal_requirement(self):
        self.assertAlmostEqual(
            validate_requirements(spec(jitter_bound_s=0))["jitter_bound_s"], 0.0, places=9
        )


class CompletenessTests(unittest.TestCase):
    def test_full_set_is_missing_nothing(self):
        self.assertEqual(missing_requirements(GOOD), [])

    def test_absent_figure_is_named_not_defaulted(self):
        partial = dict(GOOD)
        del partial["latency_bound_s"]
        self.assertEqual(missing_requirements(partial), ["latency_bound_s"])

    def test_every_required_field_is_checked(self):
        self.assertEqual(sorted(missing_requirements({})), sorted(REQUIRED_FIELDS))

    def test_service_duration_is_optional(self):
        partial = dict(GOOD)
        del partial["service_duration_s"]
        self.assertEqual(missing_requirements(partial), [])


class DerivationTests(unittest.TestCase):
    def test_serialisation_time_from_payload_and_rate(self):
        self.assertAlmostEqual(serialisation_time_s(8192.0, 1048576.0), 0.0078125, places=9)

    def test_minimum_link_rate_from_payload_and_period(self):
        self.assertAlmostEqual(minimum_link_rate_bps(8192.0, 0.125), 65536.0, places=9)

    def test_utilisation_is_the_duty_of_the_period(self):
        self.assertAlmostEqual(link_utilisation(8192.0, 1048576.0, 0.125), 0.0625, places=9)

    def test_jitter_ceiling_is_half_the_period(self):
        self.assertAlmostEqual(max_permissible_jitter_s(0.125), 0.0625, places=9)

    def test_playout_buffer_grows_with_the_jitter_bound(self):
        self.assertAlmostEqual(
            required_playout_buffer_bits(8192.0, 0.03125, 0.125), 10240.0, places=9
        )

    def test_zero_jitter_needs_only_one_payload_of_buffer(self):
        self.assertAlmostEqual(
            required_playout_buffer_bits(8192.0, 0.0, 0.125), 8192.0, places=9
        )

    def test_clock_stability_follows_the_service_duration(self):
        self.assertAlmostEqual(
            required_clock_stability_ppm(0.036, 3600.0), 10.0, places=9
        )

    def test_clock_stability_is_undefined_without_a_duration(self):
        self.assertIsNone(required_clock_stability_ppm(0.03125, None))


class ConsistencyTests(unittest.TestCase):
    def test_good_set_has_no_conflicts(self):
        self.assertEqual(consistency_findings(GOOD), [])

    def test_jitter_exactly_at_half_the_period_is_permitted(self):
        self.assertEqual(consistency_findings(spec(jitter_bound_s=0.0625)), [])

    def test_jitter_beyond_half_the_period_breaks_slot_ordering(self):
        findings = consistency_findings(spec(jitter_bound_s=0.09375))
        self.assertTrue(any("swap slots" in f for f in findings))

    def test_latency_below_the_jitter_it_permits_is_a_conflict(self):
        findings = consistency_findings(spec(latency_bound_s=0.015625))
        self.assertTrue(any("below the" in f and "jitter it permits" in f for f in findings))

    def test_latency_exactly_equal_to_the_jitter_is_permitted(self):
        self.assertEqual(consistency_findings(spec(latency_bound_s=0.03125)), [])

    def test_link_too_slow_for_one_payload_per_period(self):
        findings = consistency_findings(spec(link_rate_bps=32768.0))
        self.assertTrue(any("bit/s is needed" in f for f in findings))

    def test_serialisation_alone_can_break_the_latency_budget(self):
        findings = consistency_findings(spec(link_rate_bps=65536.0, latency_bound_s=0.03125))
        self.assertTrue(any("before any propagation" in f for f in findings))


class AssessTests(unittest.TestCase):
    def test_good_set_is_complete_and_satisfiable(self):
        result = assess_isochronous_requirements(GOOD)
        self.assertEqual(result["verdict"], COMPLETE)
        self.assertTrue(result["satisfiable"])

    def test_good_set_reports_no_findings(self):
        self.assertEqual(assess_isochronous_requirements(GOOD)["findings"], [])

    def test_absent_figure_makes_the_set_incomplete(self):
        partial = dict(GOOD)
        del partial["period_s"]
        result = assess_isochronous_requirements(partial)
        self.assertEqual(result["verdict"], INCOMPLETE)
        self.assertFalse(result["satisfiable"])

    def test_incomplete_set_names_the_absent_figure(self):
        partial = dict(GOOD)
        del partial["period_s"]
        findings = assess_isochronous_requirements(partial)["findings"]
        self.assertTrue(any("does not state period_s" in f for f in findings))

    def test_conflicting_set_is_graded_inconsistent(self):
        result = assess_isochronous_requirements(spec(jitter_bound_s=0.09375))
        self.assertEqual(result["verdict"], INCONSISTENT)
        self.assertFalse(result["satisfiable"])

    def test_derived_figures_are_carried_for_a_good_set(self):
        derived = assess_isochronous_requirements(GOOD)["derived"]
        self.assertAlmostEqual(derived["minimum_link_rate_bps"], 65536.0, places=9)
        self.assertAlmostEqual(derived["required_playout_buffer_bits"], 10240.0, places=9)

    def test_derived_figures_stay_none_when_their_inputs_are_absent(self):
        partial = dict(GOOD)
        del partial["payload_bits"]
        derived = assess_isochronous_requirements(partial)["derived"]
        self.assertIsNone(derived["serialisation_time_s"])
        self.assertIsNone(derived["required_playout_buffer_bits"])

    def test_a_partial_set_still_derives_what_it_can(self):
        partial = dict(GOOD)
        del partial["payload_bits"]
        derived = assess_isochronous_requirements(partial)["derived"]
        self.assertAlmostEqual(derived["max_permissible_jitter_s"], 0.0625, places=9)

    def test_stated_minimum_link_rate_actually_resolves_the_conflict(self):
        slow = spec(link_rate_bps=32768.0)
        needed = assess_isochronous_requirements(slow)["derived"]["minimum_link_rate_bps"]
        fixed = assess_isochronous_requirements(spec(link_rate_bps=needed))
        self.assertTrue(
            all("bit/s is needed" not in f for f in fixed["findings"])
        )

    def test_missing_and_conflicting_are_reported_together(self):
        broken = spec(jitter_bound_s=0.09375)
        del broken["latency_bound_s"]
        findings = assess_isochronous_requirements(broken)["findings"]
        self.assertTrue(any("does not state" in f for f in findings))
        self.assertTrue(any("swap slots" in f for f in findings))

    def test_bad_value_still_raises_from_assess(self):
        with self.assertRaises(ValueError):
            assess_isochronous_requirements(spec(period_s=-1.0))


if __name__ == "__main__":
    unittest.main()
