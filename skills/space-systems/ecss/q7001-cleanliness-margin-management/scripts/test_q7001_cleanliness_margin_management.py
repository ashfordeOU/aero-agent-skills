#!/usr/bin/env python3
"""Contract test for cleanliness margin management (offline, stdlib only)."""

import copy
import unittest

from q7001_cleanliness_margin_management_logic import (
    CONTAMINANT_KINDS,
    HEALTHY_MARGIN_FRACTION,
    MOLECULAR,
    PARTICULATE,
    PHASE_HEALTHY,
    PHASE_OVERRUN,
    PHASE_THIN,
    VERDICT_EXCEEDED,
    VERDICT_THIN,
    VERDICT_WITHIN,
    apportionment_check,
    consumption_rate,
    contaminant_unit,
    forecast_end_of_programme,
    manage_cleanliness_margin,
    normalise_phases,
    phase_margin,
    worst_phase,
)

PHASES = [
    {"phase": "cleanroom-integration", "allocated": 20.0, "consumed": 12.0, "complete": True},
    {"phase": "environmental-test", "allocated": 20.0, "consumed": 10.0, "complete": True},
    {"phase": "storage-and-transport", "allocated": 10.0, "consumed": 0.0, "complete": False},
    {"phase": "launch-and-ascent", "allocated": 10.0, "consumed": 0.0, "complete": False},
    {"phase": "on-orbit-life", "allocated": 20.0, "consumed": 0.0, "complete": False},
]

CASE = {
    "item": "telescope-primary-mirror",
    "kind": MOLECULAR,
    "budget": 100.0,
    "reserve_fraction": 0.2,
    "phases": PHASES,
}


def _case(**overrides):
    case = copy.deepcopy(CASE)
    case.update(overrides)
    return case


def _phases(**overrides):
    rows = copy.deepcopy(PHASES)
    for row in rows:
        if row["phase"] in overrides:
            row.update(overrides[row["phase"]])
    return rows


class LedgerTests(unittest.TestCase):
    def test_molecular_ledger_is_an_areal_mass(self):
        self.assertEqual(contaminant_unit(MOLECULAR), "mg/m2")

    def test_particulate_ledger_is_an_obscuration(self):
        self.assertEqual(contaminant_unit(PARTICULATE), "percent-area-coverage")

    def test_the_two_ledgers_do_not_share_a_unit(self):
        self.assertNotEqual(contaminant_unit(MOLECULAR), contaminant_unit(PARTICULATE))

    def test_unknown_contaminant_kind_rejected(self):
        with self.assertRaises(ValueError):
            contaminant_unit("biological")

    def test_every_kind_declares_a_unit(self):
        for kind in CONTAMINANT_KINDS:
            self.assertTrue(contaminant_unit(kind))


class ApportionmentTests(unittest.TestCase):
    def test_valid_apportionment_fits_inside_the_budget(self):
        result = apportionment_check(100.0, 0.2, PHASES)
        self.assertTrue(result["valid"])
        self.assertAlmostEqual(result["reserve"], 20.0, places=9)
        self.assertAlmostEqual(result["allocatable"], 80.0, places=9)

    def test_allocations_exactly_filling_the_allocatable_still_validate(self):
        rows = _phases(**{"on-orbit-life": {"allocated": 20.0}})
        result = apportionment_check(100.0, 0.2, rows)
        self.assertTrue(result["valid"])
        self.assertAlmostEqual(result["unallocated"], 0.0, places=9)

    def test_over_subscription_is_reported_not_scaled_away(self):
        rows = _phases(**{"on-orbit-life": {"allocated": 40.0}})
        result = apportionment_check(100.0, 0.2, rows)
        self.assertFalse(result["valid"])
        self.assertAlmostEqual(result["over_subscribed_by"], 20.0, places=9)

    def test_reserve_is_not_available_for_allocation(self):
        no_reserve = apportionment_check(100.0, 0.0, PHASES)
        with_reserve = apportionment_check(100.0, 0.2, PHASES)
        self.assertAlmostEqual(
            no_reserve["allocatable"] - with_reserve["allocatable"], 20.0, places=9
        )

    def test_zero_budget_rejected(self):
        with self.assertRaises(ValueError):
            apportionment_check(0.0, 0.1, PHASES)

    def test_reserve_fraction_of_one_rejected(self):
        with self.assertRaises(ValueError):
            apportionment_check(100.0, 1.0, PHASES)

    def test_negative_reserve_fraction_rejected(self):
        with self.assertRaises(ValueError):
            apportionment_check(100.0, -0.1, PHASES)

    def test_empty_apportionment_rejected(self):
        with self.assertRaises(ValueError):
            normalise_phases([])

    def test_duplicate_phase_name_rejected(self):
        rows = copy.deepcopy(PHASES) + [copy.deepcopy(PHASES[0])]
        with self.assertRaises(ValueError):
            normalise_phases(rows)

    def test_negative_allocation_rejected(self):
        rows = _phases(**{"launch-and-ascent": {"allocated": -1.0}})
        with self.assertRaises(ValueError):
            normalise_phases(rows)

    def test_non_boolean_complete_flag_rejected(self):
        rows = _phases(**{"launch-and-ascent": {"complete": "yes"}})
        with self.assertRaises(ValueError):
            normalise_phases(rows)


class PhaseMarginTests(unittest.TestCase):
    def test_untouched_allocation_is_healthy(self):
        result = phase_margin(20.0, 0.0)
        self.assertEqual(result["status"], PHASE_HEALTHY)
        self.assertAlmostEqual(result["margin_fraction"], 1.0, places=9)

    def test_margin_is_allocation_less_consumption(self):
        self.assertAlmostEqual(phase_margin(20.0, 12.0)["margin"], 8.0, places=9)

    def test_a_phase_on_the_healthy_threshold_reads_healthy(self):
        result = phase_margin(20.0, 16.0)
        self.assertAlmostEqual(
            result["margin_fraction"], HEALTHY_MARGIN_FRACTION, places=9
        )
        self.assertEqual(result["status"], PHASE_HEALTHY)

    def test_a_phase_just_inside_the_threshold_reads_thin(self):
        self.assertEqual(phase_margin(20.0, 17.0)["status"], PHASE_THIN)

    def test_a_phase_exactly_on_its_allocation_is_not_an_overrun(self):
        result = phase_margin(20.0, 20.0)
        self.assertAlmostEqual(result["margin"], 0.0, places=9)
        self.assertEqual(result["status"], PHASE_THIN)

    def test_overspend_is_an_overrun(self):
        result = phase_margin(20.0, 25.0)
        self.assertEqual(result["status"], PHASE_OVERRUN)
        self.assertAlmostEqual(result["margin"], -5.0, places=9)

    def test_negative_consumption_rejected(self):
        with self.assertRaises(ValueError):
            phase_margin(20.0, -1.0)

    def test_boolean_consumption_rejected(self):
        with self.assertRaises(ValueError):
            phase_margin(20.0, True)


class RateAndForecastTests(unittest.TestCase):
    def test_rate_uses_completed_phases_only(self):
        result = consumption_rate(PHASES)
        self.assertEqual(result["completed_phases"], 2)
        self.assertAlmostEqual(result["rate_per_completed_phase"], 11.0, places=9)

    def test_rate_is_undefined_before_any_phase_completes(self):
        rows = _phases(
            **{
                "cleanroom-integration": {"complete": False, "consumed": 0.0},
                "environmental-test": {"complete": False, "consumed": 0.0},
            }
        )
        self.assertIsNone(consumption_rate(rows)["rate_per_completed_phase"])

    def test_spreading_the_spend_over_the_whole_plan_would_understate_the_rate(self):
        result = consumption_rate(PHASES)
        naive = result["consumed_to_date"] / len(PHASES)
        self.assertGreater(result["rate_per_completed_phase"], naive)

    def test_forecast_carries_actuals_for_completed_phases(self):
        self.assertAlmostEqual(forecast_end_of_programme(PHASES), 62.0, places=9)

    def test_forecast_carries_an_overrun_forward_when_it_exceeds_the_allocation(self):
        rows = _phases(**{"storage-and-transport": {"consumed": 18.0}})
        self.assertAlmostEqual(forecast_end_of_programme(rows), 70.0, places=9)

    def test_worst_phase_is_the_largest_overrun(self):
        rows = _phases(
            **{
                "cleanroom-integration": {"consumed": 26.0},
                "environmental-test": {"consumed": 23.0},
            }
        )
        result = worst_phase(rows)
        self.assertEqual(result["phase"], "cleanroom-integration")
        self.assertAlmostEqual(result["overrun"], 6.0, places=9)

    def test_no_overrun_names_no_phase(self):
        self.assertIsNone(worst_phase(PHASES)["phase"])


class RollupTests(unittest.TestCase):
    def test_healthy_programme_is_compliant(self):
        result = manage_cleanliness_margin(CASE)
        self.assertEqual(result["verdict"], VERDICT_WITHIN)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], ())

    def test_programme_margin_excludes_the_reserve(self):
        result = manage_cleanliness_margin(CASE)
        self.assertAlmostEqual(result["programme_margin"], 58.0, places=9)

    def test_a_thin_programme_is_still_compliant(self):
        rows = _phases(
            **{
                "cleanroom-integration": {"consumed": 20.0},
                "environmental-test": {"consumed": 20.0},
                "storage-and-transport": {"consumed": 10.0, "complete": True},
                "launch-and-ascent": {"consumed": 10.0, "complete": True},
                "on-orbit-life": {"consumed": 8.0, "complete": True},
            }
        )
        result = manage_cleanliness_margin(_case(phases=rows))
        self.assertEqual(result["verdict"], VERDICT_THIN)
        self.assertTrue(result["compliant"])

    def test_spending_past_the_allocatable_budget_fails(self):
        rows = _phases(**{"cleanroom-integration": {"consumed": 95.0}})
        result = manage_cleanliness_margin(_case(phases=rows))
        self.assertEqual(result["verdict"], VERDICT_EXCEEDED)
        self.assertFalse(result["compliant"])

    def test_a_phase_overrun_is_named_in_the_findings(self):
        rows = _phases(**{"environmental-test": {"consumed": 31.0}})
        result = manage_cleanliness_margin(_case(phases=rows))
        self.assertTrue(
            any("environmental-test" in f for f in result["findings"])
        )

    def test_over_subscribed_apportionment_fails_before_any_spend(self):
        rows = _phases(
            **{
                "on-orbit-life": {"allocated": 60.0},
                "cleanroom-integration": {"consumed": 0.0, "complete": False},
                "environmental-test": {"consumed": 0.0, "complete": False},
            }
        )
        result = manage_cleanliness_margin(_case(phases=rows))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("over-subscribed" in f for f in result["findings"]))

    def test_the_particulate_ledger_reports_its_own_unit(self):
        result = manage_cleanliness_margin(_case(kind=PARTICULATE))
        self.assertEqual(result["unit"], "percent-area-coverage")

    def test_forecast_margin_is_reported_against_the_allocatable(self):
        result = manage_cleanliness_margin(CASE)
        self.assertAlmostEqual(result["forecast_margin"], 18.0, places=9)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            manage_cleanliness_margin("telescope-primary-mirror")

    def test_missing_item_rejected(self):
        case = _case()
        del case["item"]
        with self.assertRaises(ValueError):
            manage_cleanliness_margin(case)

    def test_missing_contaminant_kind_rejected(self):
        case = _case()
        del case["kind"]
        with self.assertRaises(ValueError):
            manage_cleanliness_margin(case)


if __name__ == "__main__":
    unittest.main()
