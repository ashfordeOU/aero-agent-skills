"""Contract tests for the painting process and facility qualification logic.

The cases cover what a qualification is made of: the coupon set the coating
application owes, the booth environment including the dew-point margin over the
substrate, every process parameter against its qualified window, the currency
of the operators who sprayed the coupons, and the day the qualification stops
being current.
"""

import unittest

from q7031_paint_process_qualification_logic import (
    APPLICATION_COUPONS,
    BASE_COUPON_KINDS,
    COUPON_KINDS,
    DEFAULT_DEW_POINT_MARGIN_C,
    add_months,
    assess_facility_set,
    assess_process_qualification,
    coupon_coverage_findings,
    dew_point_c,
    dew_point_margin_c,
    environment_findings,
    operator_currency_findings,
    parameter_within_window,
    parse_day,
    process_parameter_findings,
    qualification_expiry_day,
    required_coupon_kinds,
)

WINDOWS = {
    "spray_pressure_bar": (2.0, 3.5),
    "gun_distance_mm": (150.0, 250.0),
    "pass_count": (2.0, 4.0),
    "flash_off_minutes": (5.0, 20.0),
    "cure_temperature_c": (20.0, 60.0),
    "cure_duration_minutes": (60.0, 240.0),
}

ENVELOPE = {
    "air_temperature_c": (18.0, 28.0),
    "relative_humidity_pct": (30.0, 65.0),
    "air_velocity_m_s": (0.3, 0.8),
    "particulate_class_limit": 8.0,
    "dew_point_margin_c": 3.0,
}


def _parameters(**overrides):
    params = {
        "spray_pressure_bar": 2.8,
        "gun_distance_mm": 200.0,
        "pass_count": 3.0,
        "flash_off_minutes": 10.0,
        "cure_temperature_c": 40.0,
        "cure_duration_minutes": 120.0,
    }
    params.update(overrides)
    return params


def _environment(**overrides):
    env = {
        "air_temperature_c": 22.0,
        "relative_humidity_pct": 45.0,
        "air_velocity_m_s": 0.5,
        "particulate_class": 7.0,
        "substrate_temperature_c": 24.0,
    }
    env.update(overrides)
    return env


def _spec(**overrides):
    spec = {
        "name": "booth-2-thermal-white",
        "application": "thermal-control",
        "coupons": {
            "adhesion": 3,
            "dry-film-thickness": 3,
            "outgassing": 3,
            "humidity-resistance": 3,
            "thermo-optical": 3,
            "thermal-cycling": 3,
        },
        "parameters": _parameters(),
        "parameter_windows": dict(WINDOWS),
        "environment": _environment(),
        "environment_envelope": dict(ENVELOPE),
        "operators": [{"id": "SPR-04", "certified_day": "2025-06-01"}],
        "operator_validity_months": 24,
        "granted_day": "2025-07-15",
        "validity_months": 36,
        "reference_day": "2026-04-10",
    }
    spec.update(overrides)
    return spec


class CalendarTests(unittest.TestCase):
    def test_whole_months_advance_the_day(self):
        self.assertEqual(add_months((2025, 7, 15), 36), (2028, 7, 15))

    def test_a_month_end_clamps_rather_than_rolling_forward(self):
        self.assertEqual(add_months((2025, 1, 31), 1), (2025, 2, 28))

    def test_a_leap_february_keeps_its_twenty_ninth(self):
        self.assertEqual(add_months((2024, 1, 31), 1), (2024, 2, 29))

    def test_a_negative_month_count_is_refused(self):
        with self.assertRaises(ValueError):
            add_months((2025, 7, 15), -1)

    def test_a_non_iso_day_is_refused(self):
        with self.assertRaises(ValueError):
            parse_day("granted_day", "15.07.2025")

    def test_expiry_follows_the_grant_day_and_validity(self):
        self.assertEqual(qualification_expiry_day("2025-07-15", 36), (2028, 7, 15))


class DewPointTests(unittest.TestCase):
    def test_saturated_air_has_its_dew_point_at_the_air_temperature(self):
        self.assertAlmostEqual(dew_point_c(22.0, 100.0), 22.0, places=9)

    def test_drier_air_has_a_lower_dew_point(self):
        self.assertLess(dew_point_c(22.0, 40.0), dew_point_c(22.0, 80.0))

    def test_margin_is_the_substrate_above_the_dew_point(self):
        margin = dew_point_margin_c(22.0, 100.0, 25.0)
        self.assertAlmostEqual(margin, 3.0, places=9)

    def test_a_substrate_on_the_dew_point_has_no_margin(self):
        self.assertAlmostEqual(dew_point_margin_c(22.0, 100.0, 22.0), 0.0, places=9)

    def test_zero_humidity_is_refused_rather_than_taken_as_dry(self):
        with self.assertRaises(ValueError):
            dew_point_c(22.0, 0.0)

    def test_a_humidity_above_saturation_is_refused(self):
        with self.assertRaises(ValueError):
            dew_point_c(22.0, 140.0)

    def test_a_temperature_outside_any_booth_is_refused(self):
        with self.assertRaises(ValueError):
            dew_point_c(150.0, 45.0)


class CouponTests(unittest.TestCase):
    def test_a_general_coating_owes_the_base_set(self):
        self.assertEqual(required_coupon_kinds("general-protective"), tuple(sorted(BASE_COUPON_KINDS)))

    def test_a_thermal_control_coating_adds_optical_and_cycling_coupons(self):
        kinds = required_coupon_kinds("thermal-control")
        self.assertIn("thermo-optical", kinds)
        self.assertIn("thermal-cycling", kinds)

    def test_a_conductive_coating_adds_a_resistivity_coupon(self):
        self.assertIn("surface-resistivity", required_coupon_kinds("electrically-conductive"))

    def test_every_catalogued_application_resolves(self):
        for application in APPLICATION_COUPONS:
            self.assertTrue(required_coupon_kinds(application))

    def test_an_unknown_application_is_refused(self):
        with self.assertRaises(ValueError):
            required_coupon_kinds("decorative-only")

    def test_a_missing_coupon_kind_is_named(self):
        coupons = {k: 3 for k in required_coupon_kinds("thermal-control") if k != "outgassing"}
        findings = coupon_coverage_findings(coupons, "thermal-control")
        self.assertIn("coupon-kind-absent:outgassing", findings)

    def test_too_few_coupons_of_a_kind_is_its_own_finding(self):
        coupons = {k: 3 for k in required_coupon_kinds("thermal-control")}
        coupons["adhesion"] = 1
        self.assertIn("coupon-count-short:adhesion", coupon_coverage_findings(coupons, "thermal-control"))

    def test_an_unknown_coupon_kind_is_refused(self):
        with self.assertRaises(ValueError):
            coupon_coverage_findings({"taste-test": 3}, "thermal-control")

    def test_every_catalogued_coupon_kind_is_accepted_as_input(self):
        coupons = {kind: 3 for kind in COUPON_KINDS}
        self.assertEqual(coupon_coverage_findings(coupons, "thermal-control"), [])


class ParameterAndEnvironmentTests(unittest.TestCase):
    def test_a_parameter_on_the_window_edge_is_inside(self):
        self.assertTrue(parameter_within_window(2.0, (2.0, 3.5), "spray_pressure_bar"))

    def test_a_parameter_clearly_outside_is_outside(self):
        self.assertFalse(parameter_within_window(6.0, (2.0, 3.5), "spray_pressure_bar"))

    def test_an_inverted_window_is_refused(self):
        with self.assertRaises(ValueError):
            parameter_within_window(2.5, (3.5, 2.0), "spray_pressure_bar")

    def test_a_conforming_parameter_set_raises_nothing(self):
        self.assertEqual(process_parameter_findings(_parameters(), WINDOWS), [])

    def test_an_unrecorded_parameter_is_a_finding_not_a_pass(self):
        params = _parameters()
        del params["flash_off_minutes"]
        self.assertIn("parameter-not-recorded:flash_off_minutes",
                      process_parameter_findings(params, WINDOWS))

    def test_a_parameter_outside_its_window_is_named(self):
        self.assertIn(
            "parameter-outside-window:cure_temperature_c",
            process_parameter_findings(_parameters(cure_temperature_c=90.0), WINDOWS),
        )

    def test_a_missing_window_is_raised_against_the_qualification(self):
        windows = dict(WINDOWS)
        del windows["gun_distance_mm"]
        self.assertIn("parameter-window-absent:gun_distance_mm",
                      process_parameter_findings(_parameters(), windows))

    def test_a_conforming_environment_raises_nothing(self):
        self.assertEqual(environment_findings(_environment(), ENVELOPE), [])

    def test_a_cold_substrate_loses_the_dew_point_margin(self):
        findings = environment_findings(_environment(substrate_temperature_c=9.0), ENVELOPE)
        self.assertIn("dew-point-margin-insufficient", findings)

    def test_a_dirty_booth_is_raised(self):
        self.assertIn("particulate-class-exceeded",
                      environment_findings(_environment(particulate_class=9.0), ENVELOPE))

    def test_an_unmeasured_substrate_temperature_leaves_the_margin_unevaluated(self):
        env = _environment()
        del env["substrate_temperature_c"]
        self.assertIn("dew-point-margin-not-evaluated", environment_findings(env, ENVELOPE))

    def test_the_default_margin_floor_is_used_when_the_envelope_omits_it(self):
        envelope = dict(ENVELOPE)
        del envelope["dew_point_margin_c"]
        margin_ok = _environment(substrate_temperature_c=24.0)
        self.assertNotIn("dew-point-margin-insufficient",
                         environment_findings(margin_ok, envelope))
        self.assertAlmostEqual(DEFAULT_DEW_POINT_MARGIN_C, 3.0, places=9)


class OperatorTests(unittest.TestCase):
    def test_a_current_operator_raises_nothing(self):
        self.assertEqual(
            operator_currency_findings([{"id": "SPR-04", "certified_day": "2025-06-01"}],
                                       "2026-04-10", 24),
            [],
        )

    def test_a_lapsed_operator_is_named(self):
        findings = operator_currency_findings(
            [{"id": "SPR-09", "certified_day": "2021-01-01"}], "2026-04-10", 24
        )
        self.assertEqual(findings, ["operator-certification-lapsed:SPR-09"])

    def test_certification_running_to_the_expiry_day_is_still_current(self):
        self.assertEqual(
            operator_currency_findings([{"id": "SPR-04", "certified_day": "2024-04-10"}],
                                       "2026-04-10", 24),
            [],
        )

    def test_an_operator_without_an_id_is_refused(self):
        with self.assertRaises(ValueError):
            operator_currency_findings([{"certified_day": "2025-06-01"}], "2026-04-10")

    def test_an_empty_operator_list_is_refused(self):
        with self.assertRaises(ValueError):
            operator_currency_findings([], "2026-04-10")


class QualificationTests(unittest.TestCase):
    def test_a_complete_qualification_is_granted(self):
        result = assess_process_qualification(_spec())
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["state"], "qualified")
        self.assertTrue(result["qualified"])

    def test_the_expiry_day_is_reported(self):
        self.assertEqual(assess_process_qualification(_spec())["expiry_day"], (2028, 7, 15))

    def test_a_missing_coupon_kind_blocks_qualification(self):
        coupons = dict(_spec()["coupons"])
        del coupons["thermo-optical"]
        result = assess_process_qualification(_spec(coupons=coupons))
        self.assertEqual(result["state"], "not-qualified")

    def test_a_short_coupon_count_is_only_a_condition(self):
        coupons = dict(_spec()["coupons"])
        coupons["adhesion"] = 1
        result = assess_process_qualification(_spec(coupons=coupons))
        self.assertEqual(result["state"], "conditionally-qualified")

    def test_a_lapsed_qualification_is_not_qualified(self):
        result = assess_process_qualification(_spec(reference_day="2030-01-01"))
        self.assertIn("qualification-expired", result["findings"])
        self.assertEqual(result["state"], "not-qualified")

    def test_a_condensing_substrate_blocks_qualification(self):
        result = assess_process_qualification(
            _spec(environment=_environment(substrate_temperature_c=5.0))
        )
        self.assertEqual(result["state"], "not-qualified")

    def test_a_spec_without_a_name_is_refused(self):
        with self.assertRaises(ValueError):
            assess_process_qualification(_spec(name="  "))

    def test_a_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_process_qualification(["booth-2"])


class FacilitySetTests(unittest.TestCase):
    def test_a_set_of_qualified_processes_passes(self):
        result = assess_facility_set([_spec(), _spec(name="booth-3-conductive",
                                                     application="electrically-conductive",
                                                     coupons={
                                                         "adhesion": 3,
                                                         "dry-film-thickness": 3,
                                                         "outgassing": 3,
                                                         "humidity-resistance": 3,
                                                         "surface-resistivity": 3,
                                                         "thermal-cycling": 3,
                                                     })])
        self.assertTrue(result["set_qualified"])

    def test_one_unqualified_process_fails_the_set(self):
        result = assess_facility_set([
            _spec(),
            _spec(name="booth-9", parameters=_parameters(spray_pressure_bar=9.0)),
        ])
        self.assertFalse(result["set_qualified"])
        self.assertEqual(result["not_qualified"], ["booth-9"])

    def test_duplicate_names_are_refused(self):
        with self.assertRaises(ValueError):
            assess_facility_set([_spec(), _spec()])

    def test_an_empty_set_is_refused(self):
        with self.assertRaises(ValueError):
            assess_facility_set([])


if __name__ == "__main__":
    unittest.main()
