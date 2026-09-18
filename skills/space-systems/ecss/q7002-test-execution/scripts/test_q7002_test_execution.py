"""Contract tests for the outgassing exposure execution logic.

The cases read a run log the way a reviewer does: the order the phases were
stamped in, which samples had specimen temperature, collector temperature and
chamber pressure all inside their limits at the same moment, how much soak
time that credits, which stretches did not qualify and why, and whether the
required soak was actually delivered.
"""

import unittest

from q7002_test_execution_logic import (
    DEFAULT_LIMITS,
    PHASE_ORDER,
    assess_test_execution,
    excursions,
    longest_excursion_h,
    phase_order_findings,
    qualified_dwell_h,
    sample_failures,
    sample_qualifies,
    validate_timeline,
)


def _sample(time_h, specimen=125.0, collector=25.0, pressure=1.0e-5):
    return {
        "time_h": time_h,
        "specimen_temperature_c": specimen,
        "collector_temperature_c": collector,
        "pressure_pa": pressure,
    }


def _clean_log(step=4.0, span=24.0):
    count = int(round(span / step)) + 1
    return [_sample(i * step) for i in range(count)]


def _events(**overrides):
    stamps = {
        "pump_down_start": 0.0,
        "heating_start": 1.0,
        "stabilised": 2.0,
        "soak_start": 2.0,
        "soak_end": 26.0,
        "cooldown_complete": 28.0,
    }
    stamps.update(overrides)
    return stamps


class TimelineTests(unittest.TestCase):
    def test_clean_log_validates(self):
        records = validate_timeline(_clean_log())
        self.assertEqual(len(records), 7)

    def test_single_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_timeline([_sample(0.0)])

    def test_repeated_time_stamp_rejected(self):
        with self.assertRaises(ValueError):
            validate_timeline([_sample(0.0), _sample(0.0)])

    def test_backwards_time_stamp_rejected(self):
        with self.assertRaises(ValueError):
            validate_timeline([_sample(4.0), _sample(1.0)])

    def test_missing_channel_rejected(self):
        broken = _sample(0.0)
        del broken["pressure_pa"]
        with self.assertRaises(ValueError):
            validate_timeline([broken, _sample(4.0)])

    def test_zero_pressure_rejected(self):
        with self.assertRaises(ValueError):
            validate_timeline([_sample(0.0, pressure=0.0), _sample(4.0)])


class SampleQualificationTests(unittest.TestCase):
    def test_nominal_sample_qualifies(self):
        self.assertTrue(sample_qualifies(_sample(0.0)))

    def test_band_edges_are_inclusive(self):
        low, high = DEFAULT_LIMITS["specimen_temperature_band_c"]
        self.assertTrue(sample_qualifies(_sample(0.0, specimen=low)))
        self.assertTrue(sample_qualifies(_sample(0.0, specimen=high)))

    def test_pressure_exactly_at_the_ceiling_qualifies(self):
        ceiling = DEFAULT_LIMITS["pressure_ceiling_pa"]
        self.assertTrue(sample_qualifies(_sample(0.0, pressure=ceiling)))

    def test_cold_bar_is_named(self):
        self.assertEqual(sample_failures(_sample(0.0, specimen=110.0)),
                         ["specimen-temperature"])

    def test_warm_collector_is_named(self):
        self.assertEqual(sample_failures(_sample(0.0, collector=31.0)),
                         ["collector-temperature"])

    def test_soft_vacuum_is_named(self):
        self.assertEqual(sample_failures(_sample(0.0, pressure=1.0e-2)),
                         ["chamber-pressure"])

    def test_three_failures_are_all_named(self):
        reasons = sample_failures(_sample(0.0, specimen=90.0, collector=40.0,
                                          pressure=1.0e-1))
        self.assertEqual(len(reasons), 3)

    def test_unknown_limit_key_rejected(self):
        with self.assertRaises(ValueError):
            sample_failures(_sample(0.0), {"chamber_colour": 1.0})

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            sample_failures(_sample(0.0), {"specimen_temperature_band_c": (126.0, 124.0)})


class QualifiedDwellTests(unittest.TestCase):
    def test_clean_log_credits_the_whole_span(self):
        self.assertAlmostEqual(qualified_dwell_h(_clean_log()), 24.0, places=9)

    def test_one_bad_sample_costs_both_neighbouring_intervals(self):
        log = _clean_log()
        log[3] = _sample(12.0, pressure=1.0e-2)
        self.assertAlmostEqual(qualified_dwell_h(log), 16.0, places=9)

    def test_a_bad_end_sample_costs_one_interval(self):
        log = _clean_log()
        log[-1] = _sample(24.0, specimen=100.0)
        self.assertAlmostEqual(qualified_dwell_h(log), 20.0, places=9)

    def test_two_consecutive_bad_samples_cost_three_intervals(self):
        log = _clean_log()
        log[2] = _sample(8.0, collector=40.0)
        log[3] = _sample(12.0, collector=40.0)
        self.assertAlmostEqual(qualified_dwell_h(log), 12.0, places=9)

    def test_an_all_bad_log_credits_nothing(self):
        log = [_sample(0.0, specimen=20.0), _sample(4.0, specimen=20.0)]
        self.assertAlmostEqual(qualified_dwell_h(log), 0.0, places=9)

    def test_finer_sampling_credits_the_same_span(self):
        self.assertAlmostEqual(
            qualified_dwell_h(_clean_log(step=1.0)), 24.0, places=9
        )


class ExcursionTests(unittest.TestCase):
    def test_clean_log_has_no_excursions(self):
        self.assertEqual(excursions(_clean_log()), [])

    def test_one_bad_sample_is_one_excursion(self):
        log = _clean_log()
        log[3] = _sample(12.0, pressure=1.0e-2)
        events = excursions(log)
        self.assertEqual(len(events), 1)
        self.assertAlmostEqual(events[0]["duration_h"], 0.0, places=9)
        self.assertEqual(events[0]["causes"], ["chamber-pressure"])

    def test_consecutive_bad_samples_are_one_event(self):
        log = _clean_log()
        log[2] = _sample(8.0, collector=40.0)
        log[3] = _sample(12.0, collector=40.0)
        events = excursions(log)
        self.assertEqual(len(events), 1)
        self.assertAlmostEqual(events[0]["duration_h"], 4.0, places=9)

    def test_separated_bad_samples_are_two_events(self):
        log = _clean_log()
        log[1] = _sample(4.0, specimen=100.0)
        log[5] = _sample(20.0, specimen=100.0)
        self.assertEqual(len(excursions(log)), 2)

    def test_causes_of_a_stretch_are_merged(self):
        log = _clean_log()
        log[2] = _sample(8.0, collector=40.0)
        log[3] = _sample(12.0, pressure=1.0e-2)
        events = excursions(log)
        self.assertEqual(events[0]["causes"], ["chamber-pressure", "collector-temperature"])

    def test_trailing_excursion_is_closed(self):
        log = _clean_log()
        log[-1] = _sample(24.0, specimen=100.0)
        events = excursions(log)
        self.assertEqual(len(events), 1)
        self.assertAlmostEqual(events[0]["start_h"], 24.0, places=9)

    def test_longest_excursion_of_none_is_zero(self):
        self.assertAlmostEqual(longest_excursion_h([]), 0.0)

    def test_longest_excursion_picks_the_largest(self):
        self.assertAlmostEqual(
            longest_excursion_h([{"duration_h": 1.0}, {"duration_h": 4.0}]), 4.0
        )

    def test_malformed_excursion_rejected(self):
        with self.assertRaises(ValueError):
            longest_excursion_h([{"start_h": 1.0}])


class PhaseOrderTests(unittest.TestCase):
    def test_ordered_log_is_silent(self):
        self.assertEqual(phase_order_findings(_events()), [])

    def test_all_six_phases_are_named(self):
        self.assertEqual(len(PHASE_ORDER), 6)

    def test_soak_before_stabilisation_is_flagged(self):
        notes = phase_order_findings(_events(soak_start=1.5))
        self.assertEqual(len(notes), 1)
        self.assertIn("soak_start", notes[0])

    def test_missing_stamp_is_flagged(self):
        stamps = _events()
        del stamps["cooldown_complete"]
        notes = phase_order_findings(stamps)
        self.assertIn("no stamp", notes[0])

    def test_unknown_phase_rejected(self):
        stamps = _events()
        stamps["tea_break"] = 5.0
        with self.assertRaises(ValueError):
            phase_order_findings(stamps)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            phase_order_findings(["pump_down_start"])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "samples": _clean_log(),
            "required_duration_h": 24.0,
            "events": _events(),
        }
        spec.update(overrides)
        return spec

    def test_clean_run_delivers_the_soak(self):
        result = assess_test_execution(self._spec())
        self.assertTrue(result["soak_delivered"])
        self.assertTrue(result["execution_clean"])
        self.assertEqual(result["findings"], [])

    def test_qualified_and_elapsed_are_both_reported(self):
        result = assess_test_execution(self._spec())
        self.assertAlmostEqual(result["qualified_dwell_h"], 24.0, places=9)
        self.assertAlmostEqual(result["elapsed_h"], 24.0, places=9)

    def test_exactly_the_required_duration_is_delivered(self):
        result = assess_test_execution(self._spec(required_duration_h=24.0))
        self.assertAlmostEqual(
            result["qualified_dwell_h"], result["required_duration_h"], places=9
        )
        self.assertTrue(result["soak_delivered"])

    def test_dropout_shortens_the_qualified_soak(self):
        log = _clean_log()
        log[3] = _sample(12.0, pressure=1.0e-2)
        result = assess_test_execution(self._spec(samples=log))
        self.assertFalse(result["soak_delivered"])
        self.assertAlmostEqual(result["qualified_dwell_h"], 16.0, places=9)

    def test_excursion_is_reported_beside_the_shortfall(self):
        log = _clean_log()
        log[3] = _sample(12.0, pressure=1.0e-2)
        result = assess_test_execution(self._spec(samples=log))
        self.assertEqual(len(result["excursions"]), 1)
        self.assertEqual(len(result["findings"]), 2)

    def test_elapsed_time_does_not_rescue_a_short_soak(self):
        log = _clean_log(step=4.0, span=24.0)
        log[3] = _sample(12.0, collector=40.0)
        result = assess_test_execution(self._spec(samples=log))
        self.assertAlmostEqual(result["elapsed_h"], 24.0, places=9)
        self.assertFalse(result["soak_delivered"])

    def test_out_of_order_phases_make_the_run_unclean(self):
        result = assess_test_execution(self._spec(events=_events(soak_start=1.0)))
        self.assertTrue(result["soak_delivered"])
        self.assertFalse(result["execution_clean"])

    def test_events_are_optional(self):
        spec = self._spec()
        del spec["events"]
        result = assess_test_execution(spec)
        self.assertTrue(result["execution_clean"])

    def test_longest_excursion_is_reported(self):
        log = _clean_log()
        log[2] = _sample(8.0, specimen=100.0)
        log[3] = _sample(12.0, specimen=100.0)
        result = assess_test_execution(self._spec(samples=log))
        self.assertAlmostEqual(result["longest_excursion_h"], 4.0, places=9)

    def test_tighter_limits_can_be_supplied(self):
        log = _clean_log()
        log[3] = _sample(12.0, specimen=125.8)
        loose = assess_test_execution(self._spec(samples=log))
        tight = assess_test_execution(
            self._spec(samples=log, limits={"specimen_temperature_band_c": (124.9, 125.1)})
        )
        self.assertTrue(loose["soak_delivered"])
        self.assertFalse(tight["soak_delivered"])

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["required_duration_h"]
        with self.assertRaises(ValueError):
            assess_test_execution(spec)

    def test_non_positive_required_duration_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_execution(self._spec(required_duration_h=0.0))


if __name__ == "__main__":
    unittest.main()
