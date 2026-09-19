"""Contract tests for the clause 10.2.4 wafer acceptance measurement decision."""

import unittest

from q6012_wafer_acceptance_measurements_logic import (
    DEFAULT_MINIMUM_SITES,
    DEFAULT_SITE_FRACTION,
    PARAMETER_KEYS,
    SIDEDNESS,
    assess_wafer_acceptance,
    median,
    parameter_sidedness,
    parameter_summary,
    parameter_titles,
    parameter_units,
    rejecting_parameters,
    site_verdict,
    validate_limits,
    validate_sites,
    wafer_summary,
    worst_margin,
)

LIMITS = {
    "pinch-off-voltage": {"lower": -2.0, "upper": -1.0},
    "saturated-drain-current": {"lower": 500.0},
    "gate-leakage-current": {"upper": 1.0},
}


def site_row(name, pinch=-1.5, idss=600.0, leak=0.2):
    return {
        "site": name,
        "values": {
            "pinch-off-voltage": pinch,
            "saturated-drain-current": idss,
            "gate-leakage-current": leak,
        },
    }


def ten_sites(overrides=None):
    rows = [site_row("S%02d" % i) for i in range(1, 11)]
    for index, values in (overrides or {}).items():
        rows[index] = site_row("S%02d" % (index + 1), **values)
    return rows


def base_spec(**overrides):
    spec = {
        "wafer_id": "W-3391",
        "limits": dict(LIMITS),
        "sites": ten_sites(),
    }
    spec.update(overrides)
    return spec


class RegistryTests(unittest.TestCase):
    def test_parameter_keys_are_unique(self):
        self.assertEqual(len(PARAMETER_KEYS), len(set(PARAMETER_KEYS)))

    def test_every_parameter_has_title_unit_and_sidedness(self):
        self.assertEqual(set(parameter_titles()), set(PARAMETER_KEYS))
        self.assertEqual(set(parameter_units()), set(PARAMETER_KEYS))
        self.assertEqual(set(parameter_sidedness()), set(PARAMETER_KEYS))

    def test_every_sidedness_is_a_declared_token(self):
        for side in parameter_sidedness().values():
            self.assertIn(side, SIDEDNESS)

    def test_defaults_are_sane(self):
        self.assertTrue(0.0 < DEFAULT_SITE_FRACTION <= 1.0)
        self.assertGreaterEqual(DEFAULT_MINIMUM_SITES, 1)


class ValidateLimitsTests(unittest.TestCase):
    def test_two_sided_parameter_keeps_both_bounds(self):
        limits = validate_limits({"sheet-resistance": {"lower": 100.0, "upper": 200.0}})
        self.assertEqual(limits["sheet-resistance"]["sidedness"], "two-sided")

    def test_minimum_parameter_given_an_upper_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_limits({"saturated-drain-current": {"lower": 1.0, "upper": 9.0}})

    def test_maximum_parameter_missing_its_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_limits({"gate-leakage-current": {}})

    def test_unknown_parameter_rejected(self):
        with self.assertRaises(ValueError):
            validate_limits({"noise-figure": {"upper": 2.0}})

    def test_inverted_two_sided_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_limits({"sheet-resistance": {"lower": 200.0, "upper": 100.0}})

    def test_unknown_bound_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_limits({"gate-leakage-current": {"max": 1.0}})

    def test_empty_limit_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_limits({})


class ValidateSitesTests(unittest.TestCase):
    def test_valid_site_set_is_normalised(self):
        limits = validate_limits(dict(LIMITS))
        sites = validate_sites(ten_sites(), limits)
        self.assertEqual(len(sites), 10)
        self.assertEqual(sites[0]["site"], "S01")

    def test_duplicate_site_rejected(self):
        limits = validate_limits(dict(LIMITS))
        rows = ten_sites()
        rows[1]["site"] = rows[0]["site"]
        with self.assertRaises(ValueError):
            validate_sites(rows, limits)

    def test_site_missing_a_limited_parameter_rejected(self):
        limits = validate_limits(dict(LIMITS))
        rows = ten_sites()
        del rows[3]["values"]["gate-leakage-current"]
        with self.assertRaises(ValueError):
            validate_sites(rows, limits)

    def test_site_measuring_an_unbounded_parameter_rejected(self):
        limits = validate_limits(dict(LIMITS))
        rows = ten_sites()
        rows[2]["values"]["sheet-resistance"] = 150.0
        with self.assertRaises(ValueError):
            validate_sites(rows, limits)

    def test_too_few_sites_rejected(self):
        limits = validate_limits(dict(LIMITS))
        with self.assertRaises(ValueError):
            validate_sites(ten_sites()[:2], limits)

    def test_non_numeric_reading_rejected(self):
        limits = validate_limits(dict(LIMITS))
        rows = ten_sites()
        rows[0]["values"]["saturated-drain-current"] = "600"
        with self.assertRaises(ValueError):
            validate_sites(rows, limits)

    def test_boolean_minimum_sites_rejected(self):
        limits = validate_limits(dict(LIMITS))
        with self.assertRaises(ValueError):
            validate_sites(ten_sites(), limits, minimum_sites=True)


class SiteVerdictTests(unittest.TestCase):
    def setUp(self):
        self.limits = validate_limits(dict(LIMITS))

    def test_interior_reading_is_within(self):
        self.assertEqual(site_verdict(-1.5, self.limits["pinch-off-voltage"]), "within")

    def test_reading_on_the_lower_limit_is_inside_and_named(self):
        self.assertEqual(
            site_verdict(-2.0, self.limits["pinch-off-voltage"]), "on-lower-limit"
        )

    def test_reading_on_the_upper_limit_is_inside_and_named(self):
        self.assertEqual(
            site_verdict(1.0, self.limits["gate-leakage-current"]), "on-upper-limit"
        )

    def test_reading_under_a_minimum_is_rejected(self):
        self.assertEqual(
            site_verdict(400.0, self.limits["saturated-drain-current"]),
            "below-minimum",
        )

    def test_reading_over_a_maximum_is_rejected(self):
        self.assertEqual(
            site_verdict(2.5, self.limits["gate-leakage-current"]), "above-maximum"
        )

    def test_verdict_rejects_a_raw_bound_mapping(self):
        with self.assertRaises(ValueError):
            site_verdict(1.0, {"upper": 2.0})


class StatisticsTests(unittest.TestCase):
    def test_median_of_an_odd_sample(self):
        self.assertAlmostEqual(median([3.0, 1.0, 2.0]), 2.0, places=9)

    def test_median_of_an_even_sample_is_the_mid_average(self):
        self.assertAlmostEqual(median([1.0, 2.0, 3.0, 4.0]), 2.5, places=9)

    def test_median_of_an_empty_sample_rejected(self):
        with self.assertRaises(ValueError):
            median([])

    def test_median_of_a_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            median({"a": 1.0})

    def test_worst_margin_is_positive_inside_the_band(self):
        limits = validate_limits(dict(LIMITS))
        self.assertAlmostEqual(
            worst_margin([600.0, 700.0], limits["saturated-drain-current"]),
            100.0,
            places=9,
        )

    def test_worst_margin_is_zero_on_the_bound(self):
        limits = validate_limits(dict(LIMITS))
        self.assertAlmostEqual(
            worst_margin([500.0, 700.0], limits["saturated-drain-current"]),
            0.0,
            places=9,
        )

    def test_worst_margin_is_negative_outside_the_band(self):
        limits = validate_limits(dict(LIMITS))
        self.assertAlmostEqual(
            worst_margin([450.0], limits["saturated-drain-current"]), -50.0, places=9
        )

    def test_worst_margin_rejects_an_empty_sample(self):
        limits = validate_limits(dict(LIMITS))
        with self.assertRaises(ValueError):
            worst_margin([], limits["saturated-drain-current"])


class ParameterSummaryTests(unittest.TestCase):
    def setUp(self):
        self.limits = validate_limits(dict(LIMITS))
        self.sites = validate_sites(ten_sites(), self.limits)

    def test_clean_parameter_has_every_site_within(self):
        summary = parameter_summary("gate-leakage-current", self.sites, self.limits)
        self.assertEqual(summary["within_sites"], 10)
        self.assertAlmostEqual(summary["within_fraction"], 1.0, places=9)
        self.assertEqual(summary["outlier_sites"], [])

    def test_one_bad_site_is_named(self):
        sites = validate_sites(ten_sites({3: {"leak": 5.0}}), self.limits)
        summary = parameter_summary("gate-leakage-current", sites, self.limits)
        self.assertEqual(summary["outlier_sites"], ["S04"])
        self.assertAlmostEqual(summary["within_fraction"], 0.9, places=9)

    def test_summary_orders_parameters_by_the_registry(self):
        keys = [s["parameter"] for s in wafer_summary(self.sites, self.limits)]
        self.assertEqual(
            keys,
            [k for k in PARAMETER_KEYS if k in self.limits],
        )

    def test_summary_rejects_an_unbounded_parameter(self):
        with self.assertRaises(ValueError):
            parameter_summary("sheet-resistance", self.sites, self.limits)


class WaferDecisionTests(unittest.TestCase):
    def test_clean_wafer_is_accepted(self):
        result = assess_wafer_acceptance(base_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["verdict"], "accept")
        self.assertEqual(result["rejecting_parameters"], [])

    def test_site_fraction_exactly_at_the_requirement_is_accepted(self):
        spec = base_spec(sites=ten_sites({3: {"leak": 5.0}}))
        result = assess_wafer_acceptance(spec)
        leak = [p for p in result["parameters"]
                if p["parameter"] == "gate-leakage-current"][0]
        self.assertAlmostEqual(leak["within_fraction"], 0.9, places=9)
        self.assertAlmostEqual(result["required_site_fraction"], 0.9, places=9)
        self.assertTrue(result["accepted"])

    def test_one_site_past_the_requirement_rejects_the_wafer(self):
        spec = base_spec(sites=ten_sites({3: {"leak": 5.0}, 4: {"leak": 6.0}}))
        result = assess_wafer_acceptance(spec)
        self.assertFalse(result["accepted"])
        self.assertEqual(
            [d["parameter"] for d in result["rejecting_parameters"]],
            ["gate-leakage-current"],
        )

    def test_a_shifted_median_rejects_even_with_a_high_site_fraction(self):
        rows = ten_sites()
        for row in rows:
            row["values"]["saturated-drain-current"] = 480.0
        result = assess_wafer_acceptance(base_spec(sites=rows))
        self.assertFalse(result["accepted"])
        drivers = result["rejecting_parameters"][0]
        self.assertEqual(drivers["parameter"], "saturated-drain-current")
        self.assertTrue(any("median" in r for r in drivers["reasons"]))

    def test_overall_within_fraction_spans_every_reading(self):
        result = assess_wafer_acceptance(base_spec())
        self.assertAlmostEqual(result["overall_within_fraction"], 1.0, places=9)

    def test_tighter_required_fraction_rejects_what_the_default_accepts(self):
        spec = base_spec(sites=ten_sites({3: {"leak": 5.0}}))
        self.assertTrue(assess_wafer_acceptance(spec)["accepted"])
        spec["required_site_fraction"] = 1.0
        self.assertFalse(assess_wafer_acceptance(spec)["accepted"])

    def test_unknown_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_wafer_acceptance(base_spec(waffer_id="W-1"))

    def test_missing_spec_key_rejected(self):
        spec = base_spec()
        del spec["limits"]
        with self.assertRaises(ValueError):
            assess_wafer_acceptance(spec)

    def test_out_of_range_required_fraction_rejected(self):
        with self.assertRaises(ValueError):
            assess_wafer_acceptance(base_spec(required_site_fraction=1.4))

    def test_empty_wafer_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_wafer_acceptance(base_spec(wafer_id="   "))

    def test_rejecting_parameters_refuses_a_bad_required_fraction(self):
        summaries = wafer_summary(
            validate_sites(ten_sites(), validate_limits(dict(LIMITS))),
            validate_limits(dict(LIMITS)),
        )
        with self.assertRaises(ValueError):
            rejecting_parameters(summaries, 0.0)

    def test_rejecting_parameters_refuses_a_malformed_summary(self):
        with self.assertRaises(ValueError):
            rejecting_parameters([{"title": "no parameter key"}])


if __name__ == "__main__":
    unittest.main()
