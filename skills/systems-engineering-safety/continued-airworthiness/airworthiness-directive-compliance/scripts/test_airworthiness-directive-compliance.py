"""Contract test for airworthiness-directive-compliance (wave-37).

Offline, deterministic, stdlib only. Covers the worked example from the
engineering spec (module real outputs as assert targets), applicability
and status truth tables, calendar arithmetic, the fleet review
identities, ValueError rejections of non-physical inputs, dict key
shape, and determinism.

Run: python3 scripts/test_airworthiness-directive-compliance.py
"""

import datetime
import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LOGIC_PATH = os.path.join(
    _HERE, "airworthiness-directive-compliance_logic.py"
)

_spec = importlib.util.spec_from_file_location("adic_logic", _LOGIC_PATH)
adic = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adic)

DAYS_PER_MONTH = adic.DAYS_PER_MONTH

AS_OF = datetime.date(2026, 2, 1)

AD_CYCLES = {
    "id": "AD-2024-001",
    "affected_models": ["T-100"],
    "affected_serials": [],
    "basis": "cycles",
    "value": 4000,
    "grace": 200,
    "effective_date": "2024-01-15",
}

AD_CALENDAR = {
    "id": "AD-2024-002",
    "affected_models": ["T-100"],
    "affected_serials": [],
    "basis": "calendar",
    "value": 24,
    "grace": 3,
    "effective_date": "2024-01-15",
}


def ac(model, serial, cycles, hours=0.0, last=None):
    """Build an aircraft record; last_action_date defaults to None."""
    return {
        "model": model,
        "serial": serial,
        "cycles_since_last_action": float(cycles),
        "hours_since_last_action": float(hours),
        "last_action_date": last,
    }


class TestApplicability(unittest.TestCase):
    """Truth table: model hit, serial-range hit, neither."""

    def test_model_hit_applies(self):
        self.assertTrue(adic.ad_applies(AD_CYCLES, ac("T-100", "001", 3500)))

    def test_serial_range_hit_applies(self):
        ad = dict(AD_CYCLES, affected_models=[], affected_serials=[("001", "050")])
        self.assertTrue(adic.ad_applies(ad, ac("T-100", "033", 100)))
        self.assertTrue(adic.ad_applies(ad, ac("T-200", "033", 100)))

    def test_range_boundaries_inclusive(self):
        ad = dict(AD_CYCLES, affected_models=[], affected_serials=[("001", "050")])
        self.assertTrue(adic.ad_applies(ad, ac("T-100", "001", 100)))
        self.assertTrue(adic.ad_applies(ad, ac("T-100", "050", 100)))

    def test_misses_do_not_apply(self):
        # Worked example ac4: T-200/009, model not affected.
        self.assertFalse(adic.ad_applies(AD_CYCLES, ac("T-200", "009", 9999)))
        ad = dict(AD_CYCLES, affected_models=[], affected_serials=[("001", "050")])
        self.assertFalse(adic.ad_applies(ad, ac("T-100", "051", 100)))
        self.assertFalse(adic.ad_applies(ad, ac("T-100", "000", 100)))


class TestRemainingUnits(unittest.TestCase):
    """Remaining margin in the directive's own basis."""

    def test_worked_example_ac1_remaining_500(self):
        # 4000 - 3500 cycles.
        self.assertEqual(
            adic.remaining_units(AD_CYCLES, ac("T-100", "001", 3500), AS_OF),
            500.0,
        )

    def test_worked_example_ac2_remaining_minus_200(self):
        # 4000 - 4200 cycles.
        self.assertEqual(
            adic.remaining_units(AD_CYCLES, ac("T-100", "002", 4200), AS_OF),
            -200.0,
        )

    def test_worked_example_ac3_remaining_minus_550(self):
        # 4000 - 4550 cycles.
        self.assertEqual(
            adic.remaining_units(AD_CYCLES, ac("T-100", "003", 4550), AS_OF),
            -550.0,
        )

    def test_hours_basis_uses_hours_since_last_action(self):
        ad = dict(AD_CYCLES, basis="hours", value=3000, grace=100)
        self.assertEqual(
            adic.remaining_units(ad, ac("T-100", "001", 0, hours=2750), AS_OF),
            250.0,
        )

    def test_calendar_due_anchor_2026_02_01(self):
        # Effective 2024-01-15; 748 elapsed days on 2026-02-01;
        # value_days 730.5 gives remaining -17.5.
        self.assertEqual(
            adic.remaining_units(AD_CALENDAR, ac("T-100", "001", 0), AS_OF),
            -17.5,
        )

    def test_calendar_overdue_anchor_2027_06_01(self):
        # 1233 elapsed days on 2027-06-01 gives remaining -502.5.
        self.assertEqual(
            adic.remaining_units(
                AD_CALENDAR, ac("T-100", "001", 0), datetime.date(2027, 6, 1)
            ),
            -502.5,
        )

    def test_calendar_before_effective_date_still_open_margin(self):
        # as_of before effectivity gives a positive margin above value.
        remaining = adic.remaining_units(
            AD_CALENDAR, ac("T-100", "001", 0), datetime.date(2023, 12, 1)
        )
        self.assertGreater(remaining, 730.5)

    def test_days_per_month_constant(self):
        self.assertAlmostEqual(DAYS_PER_MONTH, 30.4375)
        self.assertAlmostEqual(24 * DAYS_PER_MONTH, 730.5)
        self.assertAlmostEqual(3 * DAYS_PER_MONTH, 91.3125)


class TestComplianceStatus(unittest.TestCase):
    """Status truth table with boundary handling."""

    def test_remaining_positive_is_open(self):
        self.assertEqual(
            adic.compliance_status(AD_CYCLES, ac("T-100", "001", 3500), AS_OF),
            "open",
        )

    def test_remaining_negative_inside_grace_is_due(self):
        self.assertEqual(
            adic.compliance_status(AD_CYCLES, ac("T-100", "002", 4200), AS_OF),
            "due",
        )

    def test_remaining_below_grace_is_overdue(self):
        self.assertEqual(
            adic.compliance_status(AD_CYCLES, ac("T-100", "003", 4550), AS_OF),
            "overdue",
        )

    def test_due_boundaries_inclusive(self):
        # remaining exactly 0 is due; remaining exactly -grace is due.
        self.assertEqual(
            adic.compliance_status(AD_CYCLES, ac("T-100", "004", 4000), AS_OF),
            "due",
        )
        self.assertEqual(
            adic.compliance_status(AD_CYCLES, ac("T-100", "005", 4200), AS_OF),
            "due",
        )

    def test_just_below_minus_grace_is_overdue(self):
        ad = dict(AD_CYCLES, grace=200)
        self.assertEqual(
            adic.compliance_status(ad, ac("T-100", "006", 4200.5), AS_OF),
            "overdue",
        )

    def test_calendar_due_within_grace_days(self):
        # Remaining -17.5 inside grace_days 91.3125 on 2026-02-01.
        self.assertEqual(
            adic.compliance_status(AD_CALENDAR, ac("T-100", "001", 0), AS_OF),
            "due",
        )

    def test_calendar_overdue_beyond_grace_days(self):
        self.assertEqual(
            adic.compliance_status(
                AD_CALENDAR, ac("T-100", "001", 0), datetime.date(2027, 6, 1)
            ),
            "overdue",
        )

    def test_zero_grace_band(self):
        ad = dict(AD_CYCLES, grace=0)
        self.assertEqual(
            adic.compliance_status(ad, ac("T-100", "001", 4000), AS_OF), "due"
        )
        self.assertEqual(
            adic.compliance_status(ad, ac("T-100", "002", 4001), AS_OF), "overdue"
        )


class TestFleetReview(unittest.TestCase):
    """Worked example fleet report and identities."""

    def test_worked_example_report_counts(self):
        fleet = [
            ac("T-100", "001", 3500),   # open
            ac("T-100", "002", 4200),   # due
            ac("T-100", "003", 4550),   # overdue
            ac("T-200", "009", 9999),   # not applicable
            ac("T-100", "004", 3500),   # open, 500 cycles remaining
        ]
        report = adic.fleet_ad_review(AD_CYCLES, fleet, AS_OF)
        self.assertEqual(report["ad_id"], "AD-2024-001")
        self.assertEqual(report["basis"], "cycles")
        self.assertEqual(report["applicable"], 4)
        self.assertEqual(report["open"], 2)
        self.assertEqual(report["due"], 1)
        self.assertEqual(report["overdue"], 1)
        self.assertEqual(report["compliance_rate"], 0.5)

    def test_report_keys_exactly_as_documented(self):
        report = adic.fleet_ad_review(AD_CYCLES, [ac("T-100", "001", 3500)], AS_OF)
        self.assertEqual(
            set(report.keys()),
            {"ad_id", "basis", "applicable", "open", "due", "overdue",
             "compliance_rate"},
        )

    def test_identity_counts_sum_to_applicable(self):
        fleet = [
            ac("T-100", "001", 3500),
            ac("T-100", "002", 4200),
            ac("T-100", "003", 4550),
            ac("T-200", "009", 9999),
            ac("T-100", "004", 3500),
        ]
        report = adic.fleet_ad_review(AD_CYCLES, fleet, AS_OF)
        self.assertEqual(
            report["open"] + report["due"] + report["overdue"],
            report["applicable"],
        )
        self.assertEqual(
            report["compliance_rate"],
            report["open"] / report["applicable"],
        )

    def test_non_applicable_aircraft_never_counted(self):
        report = adic.fleet_ad_review(
            AD_CYCLES, [ac("T-200", "009", 9999), ac("T-300", "001", 1)], AS_OF
        )
        self.assertEqual(report["applicable"], 0)
        self.assertEqual(report["open"], 0)
        self.assertEqual(report["due"], 0)
        self.assertEqual(report["overdue"], 0)
        self.assertIsNone(report["compliance_rate"])

    def test_calendar_fleet_report(self):
        fleet = [ac("T-100", "001", 0), ac("T-100", "002", 0)]
        report = adic.fleet_ad_review(AD_CALENDAR, fleet, AS_OF)
        self.assertEqual(report["applicable"], 2)
        self.assertEqual(report["due"], 2)
        self.assertEqual(report["open"], 0)
        self.assertEqual(report["overdue"], 0)
        self.assertEqual(report["compliance_rate"], 0.0)

    def test_determinism_two_runs_identical(self):
        fleet = [ac("T-100", "001", 3500), ac("T-100", "002", 4200)]
        first = adic.fleet_ad_review(AD_CYCLES, fleet, AS_OF)
        second = adic.fleet_ad_review(AD_CYCLES, fleet, AS_OF)
        self.assertEqual(first, second)


class TestValueErrors(unittest.TestCase):
    """Non-physical inputs are rejected with ValueError."""

    def test_unknown_basis_raises(self):
        ad = dict(AD_CYCLES, basis="landings")
        with self.assertRaises(ValueError):
            adic.remaining_units(ad, ac("T-100", "001", 100), AS_OF)
        with self.assertRaises(ValueError):
            adic.fleet_ad_review(ad, [ac("T-100", "001", 100)], AS_OF)

    def test_non_positive_value_raises(self):
        for bad_value in (0, -400):
            ad = dict(AD_CYCLES, value=bad_value)
            with self.assertRaises(ValueError):
                adic.remaining_units(ad, ac("T-100", "001", 100), AS_OF)

    def test_negative_grace_raises(self):
        ad = dict(AD_CYCLES, grace=-1)
        with self.assertRaises(ValueError):
            adic.compliance_status(ad, ac("T-100", "001", 100), AS_OF)

    def test_empty_aircraft_list_raises(self):
        with self.assertRaises(ValueError):
            adic.fleet_ad_review(AD_CYCLES, [], AS_OF)

    def test_aircraft_missing_required_key_raises(self):
        bad = {"model": "T-100", "serial": "001"}
        with self.assertRaises(ValueError):
            adic.ad_applies(AD_CYCLES, bad)
        with self.assertRaises(ValueError):
            adic.fleet_ad_review(AD_CYCLES, [bad], AS_OF)

    def test_ad_missing_required_key_raises(self):
        ad = {"id": "AD-X", "affected_models": ["T-100"]}
        with self.assertRaises(ValueError):
            adic.ad_applies(ad, ac("T-100", "001", 100))

    def test_calendar_ad_missing_effective_date_raises(self):
        ad = {k: v for k, v in AD_CALENDAR.items() if k != "effective_date"}
        with self.assertRaises(ValueError):
            adic.remaining_units(ad, ac("T-100", "001", 0), AS_OF)

    def test_invalid_effective_date_raises(self):
        ad = dict(AD_CALENDAR, effective_date="2024-13-45")
        with self.assertRaises(ValueError):
            adic.remaining_units(ad, ac("T-100", "001", 0), AS_OF)


if __name__ == "__main__":
    unittest.main()
