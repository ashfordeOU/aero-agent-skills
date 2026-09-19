"""Contract test for the radiation recovery-and-healing leaf (stdlib unittest)."""

import math
import unittest

from q7006_recovery_and_healing_effects_logic import (
    EXPOSURE_REGIMES,
    MIN_QUIET_HALF_TIMES,
    assess_recovery,
    degradation_at,
    normalize_recovery_series,
    permanent_degradation,
    recovered_fraction,
    recovery_credit_admissible,
    recovery_credit_reasons,
    recovery_half_time,
    recovery_time_constant,
    series_is_monotonic,
)

PRISTINE = 0.200
AS_IRRADIATED = 0.280


def series(values=None):
    if values is None:
        values = [(24.0, 0.255), (168.0, 0.242), (720.0, 0.240)]
    return [{"elapsed_h": h, "value": v} for h, v in values]


def record(**kw):
    item = {
        "property": "solar-absorptance",
        "direction": "increase-is-degradation",
        "pristine_value": PRISTINE,
        "as_irradiated_value": AS_IRRADIATED,
        "recovery_series": series(),
        "exposure_regime": "intermittent",
        "quiet_interval_h": 2000.0,
        "credit_claimed": True,
    }
    item.update(kw)
    return item


class TestDegradationFrame(unittest.TestCase):
    def test_a_darkened_reading_is_a_positive_degradation(self):
        self.assertAlmostEqual(
            degradation_at(PRISTINE, AS_IRRADIATED, "increase-is-degradation"),
            0.080,
            places=9,
        )

    def test_a_transmittance_loss_is_a_positive_degradation(self):
        self.assertAlmostEqual(
            degradation_at(0.90, 0.82, "decrease-is-degradation"), 0.08, places=9
        )

    def test_an_unknown_direction_raises(self):
        with self.assertRaises(ValueError):
            degradation_at(PRISTINE, AS_IRRADIATED, "darker-is-worse")

    def test_a_fully_healed_reading_has_recovered_everything(self):
        self.assertAlmostEqual(recovered_fraction(0.080, 0.0), 1.0, places=9)

    def test_an_unhealed_reading_has_recovered_nothing(self):
        self.assertAlmostEqual(recovered_fraction(0.080, 0.080), 0.0, places=9)

    def test_a_half_healed_reading_has_recovered_half(self):
        self.assertAlmostEqual(recovered_fraction(0.080, 0.040), 0.5, places=9)

    def test_recovery_of_nothing_raises(self):
        with self.assertRaises(ValueError):
            recovered_fraction(0.0, 0.0)


class TestSeries(unittest.TestCase):
    def test_a_series_is_ordered_by_elapsed_time(self):
        points = normalize_recovery_series(
            series([(720.0, 0.240), (24.0, 0.255)]),
            PRISTINE,
            "increase-is-degradation",
        )
        self.assertAlmostEqual(points[0][0], 24.0, places=9)
        self.assertAlmostEqual(points[0][1], 0.055, places=9)

    def test_two_points_at_the_same_elapsed_time_raise(self):
        with self.assertRaises(ValueError):
            normalize_recovery_series(
                series([(24.0, 0.255), (24.0, 0.250)]),
                PRISTINE,
                "increase-is-degradation",
            )

    def test_an_empty_series_raises(self):
        with self.assertRaises(ValueError):
            normalize_recovery_series([], PRISTINE, "increase-is-degradation")

    def test_a_healing_series_is_monotonic(self):
        points = normalize_recovery_series(
            series(), PRISTINE, "increase-is-degradation"
        )
        self.assertTrue(series_is_monotonic(points))

    def test_a_series_that_darkens_again_is_not_monotonic(self):
        points = normalize_recovery_series(
            series([(24.0, 0.255), (168.0, 0.265)]),
            PRISTINE,
            "increase-is-degradation",
        )
        self.assertFalse(series_is_monotonic(points))

    def test_a_one_point_series_cannot_be_checked_for_a_trend(self):
        points = normalize_recovery_series(
            series([(24.0, 0.255)]), PRISTINE, "increase-is-degradation"
        )
        with self.assertRaises(ValueError):
            series_is_monotonic(points)

    def test_the_permanent_floor_is_where_the_series_settles(self):
        points = normalize_recovery_series(
            series(), PRISTINE, "increase-is-degradation"
        )
        self.assertAlmostEqual(permanent_degradation(points), 0.040, places=9)


class TestTimeConstant(unittest.TestCase):
    def test_one_time_constant_leaves_one_over_e_of_the_recoverable_part(self):
        tau = recovery_time_constant(
            100.0, 0.040 + 0.040 / math.e, 0.080, 0.040
        )
        self.assertAlmostEqual(tau, 100.0, places=6)

    def test_the_half_time_is_the_time_constant_times_log_two(self):
        self.assertAlmostEqual(
            recovery_half_time(100.0), 100.0 * math.log(2.0), places=9
        )

    def test_a_reading_already_at_the_floor_has_no_time_constant(self):
        with self.assertRaises(ValueError):
            recovery_time_constant(100.0, 0.040, 0.080, 0.040)

    def test_a_reading_still_at_the_as_irradiated_value_has_no_time_constant(self):
        with self.assertRaises(ValueError):
            recovery_time_constant(100.0, 0.080, 0.080, 0.040)

    def test_a_zero_elapsed_time_raises(self):
        with self.assertRaises(ValueError):
            recovery_time_constant(0.0, 0.060, 0.080, 0.040)

    def test_a_zero_time_constant_has_no_half_time(self):
        with self.assertRaises(ValueError):
            recovery_half_time(0.0)


class TestCredit(unittest.TestCase):
    def test_a_continuous_exposure_is_never_credited_with_healing(self):
        reasons = recovery_credit_reasons(
            {"exposure_regime": "continuous", "quiet_interval_h": 0.0,
             "recovery_half_time_h": 10.0}
        )
        self.assertIn(
            "continuous-exposure-leaves-no-quiet-time-to-heal-in", reasons
        )

    def test_a_long_quiet_interval_earns_the_credit(self):
        self.assertTrue(
            recovery_credit_admissible(
                {"exposure_regime": "intermittent", "quiet_interval_h": 1000.0,
                 "recovery_half_time_h": 10.0}
            )
        )

    def test_a_quiet_interval_exactly_on_the_limit_earns_the_credit(self):
        self.assertTrue(
            recovery_credit_admissible(
                {
                    "exposure_regime": "intermittent",
                    "quiet_interval_h": MIN_QUIET_HALF_TIMES * 10.0,
                    "recovery_half_time_h": 10.0,
                }
            )
        )

    def test_a_short_quiet_interval_does_not_earn_the_credit(self):
        reasons = recovery_credit_reasons(
            {"exposure_regime": "intermittent", "quiet_interval_h": 5.0,
             "recovery_half_time_h": 10.0}
        )
        self.assertIn(
            "quiet-interval-too-short-against-the-recovery-half-time", reasons
        )

    def test_every_declared_regime_is_usable(self):
        for regime in EXPOSURE_REGIMES:
            recovery_credit_reasons(
                {"exposure_regime": regime, "quiet_interval_h": 1000.0,
                 "recovery_half_time_h": 10.0}
            )

    def test_an_unknown_regime_raises(self):
        with self.assertRaises(ValueError):
            recovery_credit_reasons({"exposure_regime": "occasional"})


class TestAssessment(unittest.TestCase):
    def test_a_healing_property_is_evaluated_cleanly(self):
        result = assess_recovery(record())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["evaluated"])
        self.assertAlmostEqual(result["as_irradiated_degradation"], 0.080, places=9)
        self.assertAlmostEqual(result["permanent_degradation"], 0.040, places=9)
        self.assertAlmostEqual(result["recovered_fraction"], 0.5, places=9)

    def test_a_credited_property_designs_to_the_permanent_floor(self):
        result = assess_recovery(record())
        self.assertTrue(result["credit_admissible"])
        self.assertAlmostEqual(result["design_degradation"], 0.040, places=9)

    def test_a_continuously_irradiated_property_designs_to_the_raw_value(self):
        result = assess_recovery(
            record(exposure_regime="continuous", credit_claimed=False)
        )
        self.assertFalse(result["credit_admissible"])
        self.assertAlmostEqual(result["design_degradation"], 0.080, places=9)

    def test_claiming_a_credit_the_mission_cannot_earn_is_a_finding(self):
        result = assess_recovery(record(exposure_regime="continuous"))
        self.assertIn(
            "recovery-credit-claimed-but-not-admissible", result["findings"]
        )

    def test_a_series_that_darkens_again_is_a_finding(self):
        result = assess_recovery(
            record(recovery_series=series([(24.0, 0.255), (168.0, 0.268)]))
        )
        self.assertIn(
            "recovery-series-moves-away-from-the-pristine-value", result["findings"]
        )

    def test_a_series_healing_past_the_pristine_value_is_a_finding(self):
        result = assess_recovery(
            record(recovery_series=series([(24.0, 0.210), (168.0, 0.190)]))
        )
        self.assertIn("series-recovered-past-the-pristine-value", result["findings"])

    def test_a_single_point_series_cannot_show_a_trend(self):
        result = assess_recovery(record(recovery_series=series([(24.0, 0.255)])))
        self.assertIn(
            "recovery-series-too-short-to-show-a-trend", result["findings"]
        )

    def test_a_series_taken_only_at_the_beam_stop_has_no_recovery_point(self):
        result = assess_recovery(record(recovery_series=series([(0.0, 0.280)])))
        self.assertIn(
            "recovery-series-has-no-point-after-the-exposure", result["findings"]
        )

    def test_the_derived_half_time_is_positive(self):
        result = assess_recovery(record())
        self.assertGreater(result["recovery_half_time_h"], 0.0)

    def test_a_non_boolean_credit_claim_raises(self):
        with self.assertRaises(ValueError):
            assess_recovery(record(credit_claimed="yes"))

    def test_a_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            assess_recovery(["solar-absorptance"])


if __name__ == "__main__":
    unittest.main()
