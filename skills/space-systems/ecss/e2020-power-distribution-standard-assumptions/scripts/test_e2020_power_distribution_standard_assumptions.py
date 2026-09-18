"""Contract tests for the clause 4.2 baseline assumption applicability check.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused marginal-band
policy, an unstated or inverted baseline, an application reporting an
impossible range, a breach on each of the four assumptions, an application
landing exactly on a bound, and the marginal-band advisories.
"""

import unittest

from e2020_power_distribution_standard_assumptions_logic import (
    ASSUMPTION_NOT_STATED,
    COLD_TEMPERATURE,
    DEFAULT_ASSUMPTION_POLICY,
    HIGH_BUS_VOLTAGE,
    HOT_TEMPERATURE,
    LOW_BUS_VOLTAGE,
    OUTSIDE_BASELINE_ENVELOPE,
    WITHIN_BASELINE_ENVELOPE,
    assess_baseline_applicability,
    breached_assumptions,
    envelope_margins,
    limiting_assumption,
    marginal_assumption_advisories,
    validate_application,
    validate_assumption_policy,
    validate_baseline_assumptions,
)


def _policy(**overrides):
    policy = dict(DEFAULT_ASSUMPTION_POLICY)
    policy.update(overrides)
    return policy


def _baseline(**overrides):
    baseline = {
        "reference": "clause 4.2 baseline, issue C",
        "qualification_min_temperature_c": -40.0,
        "qualification_max_temperature_c": 85.0,
        "bus_min_voltage_v": 26.0,
        "bus_nominal_voltage_v": 28.0,
        "bus_max_voltage_v": 29.0,
    }
    baseline.update(overrides)
    return baseline


def _application(**overrides):
    application = {
        "unit": "LCL-04",
        "min_temperature_c": -25.0,
        "max_temperature_c": 70.0,
        "min_bus_voltage_v": 26.5,
        "max_bus_voltage_v": 28.6,
    }
    application.update(overrides)
    return application


def _case(**overrides):
    case = {"baseline": _baseline(), "application": _application()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_assumption_policy(DEFAULT_ASSUMPTION_POLICY),
            DEFAULT_ASSUMPTION_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_assumption_policy("marginal_voltage_band_v")

    def test_zero_temperature_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_assumption_policy(_policy(marginal_temperature_band_k=0.0))

    def test_negative_voltage_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_assumption_policy(_policy(marginal_voltage_band_v=-1.0))


class BaselineTests(unittest.TestCase):
    def test_a_valid_baseline_reads_back(self):
        base = validate_baseline_assumptions(_baseline())
        self.assertAlmostEqual(base["bus_nominal_voltage_v"], 28.0, places=12)
        self.assertEqual(base["reference"], "clause 4.2 baseline, issue C")

    def test_inverted_qualification_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_baseline_assumptions(
                _baseline(
                    qualification_min_temperature_c=85.0,
                    qualification_max_temperature_c=-40.0,
                )
            )

    def test_collapsed_qualification_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_baseline_assumptions(
                _baseline(
                    qualification_min_temperature_c=20.0,
                    qualification_max_temperature_c=20.0,
                )
            )

    def test_inverted_bus_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_baseline_assumptions(
                _baseline(bus_min_voltage_v=29.0, bus_max_voltage_v=26.0)
            )

    def test_nominal_outside_its_own_bus_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_baseline_assumptions(_baseline(bus_nominal_voltage_v=31.0))

    def test_nominal_exactly_on_the_upper_bus_bound_admitted(self):
        base = validate_baseline_assumptions(_baseline(bus_nominal_voltage_v=29.0))
        self.assertAlmostEqual(base["bus_nominal_voltage_v"], 29.0, places=9)

    def test_non_positive_bus_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_baseline_assumptions(_baseline(bus_min_voltage_v=0.0))

    def test_non_mapping_baseline_rejected(self):
        with self.assertRaises(ValueError):
            validate_baseline_assumptions("clause 4.2")


class ApplicationTests(unittest.TestCase):
    def test_a_valid_application_reads_back(self):
        app = validate_application(_application())
        self.assertEqual(app["unit"], "LCL-04")
        self.assertAlmostEqual(app["max_temperature_c"], 70.0, places=12)

    def test_blank_unit_rejected(self):
        with self.assertRaises(ValueError):
            validate_application(_application(unit="   "))

    def test_inverted_application_temperature_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_application(
                _application(min_temperature_c=70.0, max_temperature_c=-25.0)
            )

    def test_inverted_application_bus_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_application(
                _application(min_bus_voltage_v=29.0, max_bus_voltage_v=26.0)
            )

    def test_non_finite_temperature_rejected(self):
        with self.assertRaises(ValueError):
            validate_application(_application(max_temperature_c=float("inf")))


class MarginTests(unittest.TestCase):
    def test_the_four_margins_are_signed_inside_positive(self):
        margins = envelope_margins(_baseline(), _application())
        self.assertAlmostEqual(margins[COLD_TEMPERATURE], 15.0, places=9)
        self.assertAlmostEqual(margins[HOT_TEMPERATURE], 15.0, places=9)
        self.assertAlmostEqual(margins[LOW_BUS_VOLTAGE], 0.5, places=9)
        self.assertAlmostEqual(margins[HIGH_BUS_VOLTAGE], 0.4, places=9)

    def test_a_hot_application_shows_a_negative_hot_margin(self):
        margins = envelope_margins(
            _baseline(), _application(max_temperature_c=95.0)
        )
        self.assertAlmostEqual(margins[HOT_TEMPERATURE], -10.0, places=9)
        self.assertEqual(breached_assumptions(margins), (HOT_TEMPERATURE,))

    def test_a_cold_application_breaches_the_cold_assumption(self):
        margins = envelope_margins(
            _baseline(), _application(min_temperature_c=-55.0)
        )
        self.assertEqual(breached_assumptions(margins), (COLD_TEMPERATURE,))

    def test_a_sagging_bus_breaches_the_low_voltage_assumption(self):
        margins = envelope_margins(
            _baseline(), _application(min_bus_voltage_v=24.0)
        )
        self.assertEqual(breached_assumptions(margins), (LOW_BUS_VOLTAGE,))

    def test_a_rising_bus_breaches_the_high_voltage_assumption(self):
        margins = envelope_margins(
            _baseline(), _application(max_bus_voltage_v=32.0)
        )
        self.assertEqual(breached_assumptions(margins), (HIGH_BUS_VOLTAGE,))

    def test_an_application_exactly_on_a_bound_is_inside(self):
        margins = envelope_margins(
            _baseline(), _application(max_temperature_c=85.0)
        )
        self.assertAlmostEqual(margins[HOT_TEMPERATURE], 0.0, places=9)
        self.assertEqual(breached_assumptions(margins), ())

    def test_margins_missing_a_key_are_refused(self):
        margins = envelope_margins(_baseline(), _application())
        del margins[LOW_BUS_VOLTAGE]
        with self.assertRaises(ValueError):
            breached_assumptions(margins)

    def test_the_limiting_assumption_is_reported_per_kind(self):
        limiting = limiting_assumption(
            envelope_margins(_baseline(), _application(max_temperature_c=80.0))
        )
        self.assertEqual(limiting["thermal"]["assumption"], HOT_TEMPERATURE)
        self.assertAlmostEqual(limiting["thermal"]["margin"], 5.0, places=9)
        self.assertEqual(limiting["electrical"]["assumption"], HIGH_BUS_VOLTAGE)
        self.assertEqual(limiting["electrical"]["unit"], "V")


class AdvisoryTests(unittest.TestCase):
    def test_a_thin_voltage_margin_raises_an_advisory(self):
        advisories = marginal_assumption_advisories(
            envelope_margins(_baseline(), _application())
        )
        self.assertTrue(any(HIGH_BUS_VOLTAGE in a for a in advisories))

    def test_a_breached_assumption_raises_no_advisory(self):
        advisories = marginal_assumption_advisories(
            envelope_margins(_baseline(), _application(max_bus_voltage_v=32.0))
        )
        self.assertFalse(any(HIGH_BUS_VOLTAGE in a for a in advisories))

    def test_a_wide_band_flags_every_met_assumption(self):
        advisories = marginal_assumption_advisories(
            envelope_margins(_baseline(), _application()),
            _policy(marginal_temperature_band_k=40.0, marginal_voltage_band_v=5.0),
        )
        self.assertEqual(len(advisories), 4)


class AssessmentTests(unittest.TestCase):
    def test_an_application_inside_the_envelope_closes_clean(self):
        result = assess_baseline_applicability(_case())
        self.assertEqual(result["verdict"], WITHIN_BASELINE_ENVELOPE)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["unit"], "LCL-04")

    def test_a_missing_baseline_closes_the_assessment(self):
        case = _case()
        del case["baseline"]
        result = assess_baseline_applicability(case)
        self.assertEqual(result["verdict"], ASSUMPTION_NOT_STATED)
        self.assertEqual(result["margins"], {})

    def test_a_blank_baseline_reference_closes_the_assessment(self):
        result = assess_baseline_applicability(
            _case(baseline=_baseline(reference="   "))
        )
        self.assertEqual(result["verdict"], ASSUMPTION_NOT_STATED)

    def test_a_hotter_mounting_is_a_deviation(self):
        result = assess_baseline_applicability(
            _case(application=_application(max_temperature_c=95.0))
        )
        self.assertEqual(result["verdict"], OUTSIDE_BASELINE_ENVELOPE)
        self.assertEqual(result["breached_assumptions"], (HOT_TEMPERATURE,))
        self.assertTrue(any("deviation" in f for f in result["findings"]))

    def test_two_breaches_are_both_named(self):
        result = assess_baseline_applicability(
            _case(
                application=_application(
                    max_temperature_c=95.0, max_bus_voltage_v=32.0
                )
            )
        )
        self.assertEqual(
            result["breached_assumptions"], (HOT_TEMPERATURE, HIGH_BUS_VOLTAGE)
        )
        self.assertEqual(len(result["findings"]), 2)

    def test_an_application_on_the_bound_still_closes_within(self):
        result = assess_baseline_applicability(
            _case(application=_application(max_bus_voltage_v=29.0))
        )
        self.assertAlmostEqual(result["margins"][HIGH_BUS_VOLTAGE], 0.0, places=9)
        self.assertEqual(result["verdict"], WITHIN_BASELINE_ENVELOPE)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_baseline_applicability(["baseline"])

    def test_a_missing_application_is_refused(self):
        case = _case()
        del case["application"]
        with self.assertRaises(ValueError):
            assess_baseline_applicability(case)


if __name__ == "__main__":
    unittest.main()
