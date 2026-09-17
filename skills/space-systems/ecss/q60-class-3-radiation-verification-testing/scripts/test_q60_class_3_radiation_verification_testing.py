"""Contract tests for the clause 6.3.8 Class 3 radiation verification logic.

The cases follow a sensitive Class 3 part from its irradiated sample to its
route: the technologies that owe a verification at all, the tolerance factor
the sample size earns, the lower bound a wide sample gives up, the dose-rate
derating a bipolar part carries when only fast data exists, the margin against
the mission requirement, and the destructive single event that ends the part
whatever the margin says.

Float notes: every comparison that can sit on a bound is asserted with
assertAlmostEqual, and the strict comparisons are between values that differ by
far more than representation error, so the suite reads the same on any libm.
"""

import unittest

from q60_class_3_radiation_verification_testing_logic import (
    BOUND_TOLERANCE,
    DEFAULT_ELDRS_DERATING,
    DEFAULT_REQUIRED_MARGIN,
    DESTRUCTIVE_EVENT_TYPES,
    ELDRS_SENSITIVE_CATEGORIES,
    MINIMUM_SAMPLE_SIZE,
    MITIGABLE_EVENT_TYPES,
    RADIATION_CATEGORIES,
    ROUTES,
    TOLERANCE_FACTORS,
    assess_radiation_verification,
    is_sensitive,
    lot_capability,
    margin_meets,
    normalize_category,
    radiation_design_margin,
    sample_statistics,
    single_event_verdict,
    tolerance_factor,
)

SAMPLE = (100.0, 110.0, 120.0)


def _spec(**overrides):
    spec = {
        "category": "cmos-digital",
        "mission_dose": 50.0,
        "doses": list(SAMPLE),
        "mission_let": 60.0,
    }
    spec.update(overrides)
    return spec


def _event(event_type="single-event-latch-up", onset_let=20.0):
    return {"event_type": event_type, "onset_let": onset_let}


class CategoryTests(unittest.TestCase):
    def test_every_declared_technology_normalizes(self):
        for name in RADIATION_CATEGORIES:
            self.assertEqual(normalize_category(name.upper()), name)

    def test_an_undeclared_technology_is_refused(self):
        with self.assertRaises(ValueError):
            normalize_category("magnetic-core")

    def test_an_empty_technology_is_refused(self):
        with self.assertRaises(ValueError):
            normalize_category("")

    def test_a_passive_technology_is_not_dose_sensitive(self):
        self.assertFalse(is_sensitive("passive-film"))

    def test_an_active_technology_is_dose_sensitive(self):
        self.assertTrue(is_sensitive("power-mosfet"))

    def test_every_dose_rate_sensitive_technology_is_also_dose_sensitive(self):
        for name in ELDRS_SENSITIVE_CATEGORIES:
            self.assertTrue(is_sensitive(name))


class ToleranceFactorTests(unittest.TestCase):
    def test_a_tabulated_size_returns_its_factor(self):
        self.assertAlmostEqual(tolerance_factor(10), TOLERANCE_FACTORS[10], places=9)

    def test_an_untabulated_size_is_refused_not_interpolated(self):
        with self.assertRaises(ValueError):
            tolerance_factor(4)

    def test_a_non_integer_size_is_refused(self):
        with self.assertRaises(ValueError):
            tolerance_factor(10.0)

    def test_an_empty_table_is_refused(self):
        with self.assertRaises(ValueError):
            tolerance_factor(10, {})

    def test_the_factor_falls_as_the_sample_grows(self):
        self.assertGreater(TOLERANCE_FACTORS[3], TOLERANCE_FACTORS[30])


class SampleStatisticsTests(unittest.TestCase):
    def test_the_mean_of_an_even_sample(self):
        self.assertAlmostEqual(sample_statistics(SAMPLE)["mean"], 110.0, places=9)

    def test_the_spread_of_a_known_sample(self):
        self.assertAlmostEqual(sample_statistics(SAMPLE)["spread"], 10.0, places=9)

    def test_the_lowest_measured_dose_is_carried(self):
        self.assertAlmostEqual(sample_statistics(SAMPLE)["lowest"], 100.0, places=9)

    def test_a_sample_below_the_minimum_is_refused(self):
        with self.assertRaises(ValueError):
            sample_statistics(SAMPLE[: MINIMUM_SAMPLE_SIZE - 1])

    def test_a_non_positive_dose_is_refused(self):
        with self.assertRaises(ValueError):
            sample_statistics([100.0, 0.0, 120.0])

    def test_a_non_numeric_dose_is_refused(self):
        with self.assertRaises(ValueError):
            sample_statistics([100.0, "110", 120.0])

    def test_doses_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            sample_statistics(110.0)


class LotCapabilityTests(unittest.TestCase):
    def test_the_lower_bound_takes_the_spread_off_the_mean(self):
        record = lot_capability(SAMPLE, "cmos-digital")
        self.assertAlmostEqual(record["lower_bound"], 78.5, places=6)

    def test_a_wide_sample_credits_less_than_a_tight_one(self):
        tight = lot_capability([109.0, 110.0, 111.0], "cmos-digital")
        wide = lot_capability([90.0, 110.0, 130.0], "cmos-digital")
        self.assertAlmostEqual(tight["sample"]["mean"], wide["sample"]["mean"], places=9)
        self.assertGreater(tight["capability"], wide["capability"])

    def test_fast_data_on_a_bipolar_part_halves_the_capability(self):
        slow = lot_capability(SAMPLE, "bipolar-linear", low_dose_rate_data=True)
        fast = lot_capability(SAMPLE, "bipolar-linear", low_dose_rate_data=False)
        self.assertTrue(fast["eldrs_applied"])
        self.assertAlmostEqual(
            fast["capability"], slow["capability"] / DEFAULT_ELDRS_DERATING, places=9
        )

    def test_fast_data_on_a_cmos_part_is_not_derated(self):
        record = lot_capability(SAMPLE, "cmos-digital", low_dose_rate_data=False)
        self.assertFalse(record["eldrs_applied"])
        self.assertAlmostEqual(record["capability"], record["lower_bound"], places=9)

    def test_the_derating_carries_a_finding_into_the_record(self):
        record = lot_capability(SAMPLE, "optocoupler", low_dose_rate_data=False)
        self.assertTrue(any("dose-rate sensitive" in f for f in record["findings"]))

    def test_a_derating_below_unity_is_refused(self):
        with self.assertRaises(ValueError):
            lot_capability(
                SAMPLE, "bipolar-linear", low_dose_rate_data=False, eldrs_derating=0.5
            )

    def test_a_sample_whose_spread_swallows_its_mean_credits_nothing(self):
        record = lot_capability([10.0, 110.0, 210.0], "cmos-digital")
        self.assertAlmostEqual(record["capability"], 0.0, places=9)
        self.assertTrue(record["findings"])

    def test_an_untabulated_sample_size_refuses_the_capability(self):
        with self.assertRaises(ValueError):
            lot_capability([100.0, 105.0, 110.0, 115.0], "cmos-digital")


class MarginTests(unittest.TestCase):
    def test_the_margin_is_the_capability_over_the_requirement(self):
        self.assertAlmostEqual(radiation_design_margin(75.0, 50.0), 1.5, places=9)

    def test_a_margin_exactly_on_the_bound_is_a_pass(self):
        margin = radiation_design_margin(60.0, 50.0)
        self.assertAlmostEqual(margin, DEFAULT_REQUIRED_MARGIN, places=9)
        self.assertTrue(margin_meets(margin, DEFAULT_REQUIRED_MARGIN))

    def test_a_margin_clearly_under_the_bound_fails(self):
        self.assertFalse(margin_meets(0.9, DEFAULT_REQUIRED_MARGIN))

    def test_a_zero_requirement_is_refused(self):
        with self.assertRaises(ValueError):
            radiation_design_margin(75.0, 0.0)

    def test_a_negative_capability_is_refused(self):
        with self.assertRaises(ValueError):
            radiation_design_margin(-1.0, 50.0)

    def test_the_bound_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertAlmostEqual(BOUND_TOLERANCE, 1e-9, places=12)

    def test_a_non_numeric_margin_is_refused(self):
        with self.assertRaises(ValueError):
            margin_meets("1.5")


class SingleEventTests(unittest.TestCase):
    def test_a_destructive_event_inside_the_environment_vetoes(self):
        verdict = single_event_verdict([_event()], 60.0)
        self.assertTrue(verdict["vetoed"])
        self.assertEqual(len(verdict["vetoes"]), 1)

    def test_an_onset_exactly_at_the_mission_threshold_vetoes(self):
        verdict = single_event_verdict([_event(onset_let=60.0)], 60.0)
        self.assertAlmostEqual(verdict["vetoes"][0]["onset_let"], 60.0, places=9)
        self.assertTrue(verdict["vetoed"])

    def test_an_onset_clearly_above_the_threshold_survives(self):
        verdict = single_event_verdict([_event(onset_let=95.0)], 60.0)
        self.assertFalse(verdict["vetoed"])
        self.assertEqual(len(verdict["survivors"]), 1)

    def test_a_declared_mitigation_clears_a_permitted_event(self):
        verdict = single_event_verdict(
            [_event()],
            60.0,
            mitigations=["single-event-latch-up"],
            allow_mitigation_credit=True,
        )
        self.assertFalse(verdict["vetoed"])
        self.assertEqual(len(verdict["mitigated"]), 1)

    def test_a_mitigation_the_project_does_not_permit_is_ignored(self):
        verdict = single_event_verdict(
            [_event()],
            60.0,
            mitigations=["single-event-latch-up"],
            allow_mitigation_credit=False,
        )
        self.assertTrue(verdict["vetoed"])

    def test_an_unmitigable_event_type_vetoes_even_when_declared(self):
        verdict = single_event_verdict(
            [_event("single-event-burnout")],
            60.0,
            mitigations=["single-event-burnout"],
            allow_mitigation_credit=True,
        )
        self.assertTrue(verdict["vetoed"])
        self.assertNotIn("single-event-burnout", MITIGABLE_EVENT_TYPES)

    def test_a_non_destructive_event_never_vetoes(self):
        verdict = single_event_verdict([_event("single-event-upset", 5.0)], 60.0)
        self.assertFalse(verdict["vetoed"])
        self.assertNotIn("single-event-upset", DESTRUCTIVE_EVENT_TYPES)

    def test_an_event_without_an_onset_is_refused(self):
        with self.assertRaises(ValueError):
            single_event_verdict([{"event_type": "single-event-burnout"}], 60.0)

    def test_a_zero_mission_threshold_is_refused(self):
        with self.assertRaises(ValueError):
            single_event_verdict([_event()], 0.0)

    def test_events_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            single_event_verdict(_event(), 60.0)


class RouteTests(unittest.TestCase):
    def test_a_passive_part_owes_no_verification(self):
        result = assess_radiation_verification(_spec(category="passive-ceramic"))
        self.assertFalse(result["sensitive"])
        self.assertEqual(result["route"], "accept-on-lot-data")

    def test_a_sensitive_part_with_a_good_margin_is_accepted(self):
        result = assess_radiation_verification(_spec())
        self.assertEqual(result["route"], "accept-on-lot-data")
        self.assertTrue(result["meets_margin"])

    def test_a_short_margin_sends_the_part_back_for_irradiation(self):
        result = assess_radiation_verification(_spec(mission_dose=100.0))
        self.assertEqual(result["route"], "irradiate-flight-lot")
        self.assertFalse(result["meets_margin"])

    def test_no_lot_data_sends_the_part_for_irradiation(self):
        result = assess_radiation_verification(_spec(doses=[]))
        self.assertEqual(result["route"], "irradiate-flight-lot")
        self.assertIsNone(result["capability"])

    def test_a_destructive_event_rejects_the_part_despite_a_good_margin(self):
        result = assess_radiation_verification(_spec(events=[_event()]))
        self.assertTrue(result["meets_margin"])
        self.assertEqual(result["route"], "reject")

    def test_a_destructive_event_rejects_a_part_that_has_no_data_yet(self):
        result = assess_radiation_verification(_spec(doses=[], events=[_event()]))
        self.assertEqual(result["route"], "reject")

    def test_every_route_is_one_of_the_declared_routes(self):
        self.assertIn(assess_radiation_verification(_spec())["route"], ROUTES)

    def test_a_missing_mission_dose_is_refused(self):
        spec = _spec()
        del spec["mission_dose"]
        with self.assertRaises(ValueError):
            assess_radiation_verification(spec)

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_radiation_verification(["category"])

    def test_the_derating_finding_reaches_the_part_level_record(self):
        result = assess_radiation_verification(
            _spec(category="bipolar-linear", low_dose_rate_data=False)
        )
        self.assertTrue(any("dose-rate sensitive" in f for f in result["findings"]))


if __name__ == "__main__":
    unittest.main()
