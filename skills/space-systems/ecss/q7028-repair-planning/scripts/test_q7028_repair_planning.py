"""Contract tests for the board repair planning logic."""

import datetime
import unittest

from q7028_repair_planning_logic import (
    BOARD_MAX_PROCESS_TEMPERATURE_C,
    MAX_REWORK_CYCLES,
    material_findings,
    methods_for,
    parse_date,
    plan_repair,
    rework_cycle_findings,
    risk_band,
    risk_score,
    select_method,
)

PLANNED_DATE = "2026-10-01"


def good_material(**overrides):
    material = {
        "name": "no-clean-flux",
        "expiry_date": "2027-03-01",
        "process_temperature_c": 235.0,
    }
    material.update(overrides)
    return material


def base_request(**overrides):
    """A small track break on an accessible multilayer, level 3 function."""
    request = {
        "damage_category": "conductor-repair",
        "damage_extent_fraction": 0.10,
        "board_type": "multilayer",
        "planned_date": PLANNED_DATE,
        "criticality": 3,
        "accessibility": "open",
        "thermal_exposure": "none",
        "materials": [good_material()],
        "prior_rework_cycles": 0,
        "planned_rework_cycles": 1,
    }
    request.update(overrides)
    return request


class DateTests(unittest.TestCase):
    def test_iso_string_parses(self):
        self.assertEqual(parse_date("2026-10-01"), datetime.date(2026, 10, 1))

    def test_date_object_passes_through(self):
        day = datetime.date(2026, 10, 1)
        self.assertEqual(parse_date(day), day)

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("01/10/2026")

    def test_non_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date(20261001)


class MethodSelectionTests(unittest.TestCase):
    def test_catalogue_exists_for_a_known_category(self):
        self.assertTrue(methods_for("land-repair"))

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            methods_for("firmware-repair")

    def test_small_track_damage_takes_the_least_invasive_method(self):
        self.assertEqual(
            select_method("conductor-repair", 0.10)["method"],
            "conductor-lap-solder-splice",
        )

    def test_extent_exactly_on_a_method_limit_still_covers(self):
        self.assertEqual(
            select_method("conductor-repair", 0.15)["method"],
            "conductor-lap-solder-splice",
        )

    def test_larger_damage_escalates_to_the_next_method(self):
        self.assertEqual(
            select_method("conductor-repair", 0.40)["method"], "conductor-jumper-wire"
        )

    def test_damage_beyond_every_method_selects_nothing(self):
        selection = select_method("base-material-repair", 0.85)
        self.assertIsNone(selection["method"])
        self.assertIn("no catalogued method", selection["finding"])

    def test_a_preferred_method_inside_its_limit_is_honoured(self):
        self.assertEqual(
            select_method("land-repair", 0.20, preferred="land-rebond-in-place")["method"],
            "land-rebond-in-place",
        )

    def test_a_preferred_method_past_its_limit_is_refused(self):
        selection = select_method("land-repair", 0.60, preferred="land-rebond-in-place")
        self.assertIsNone(selection["method"])
        self.assertIn("covers damage up to", selection["finding"])

    def test_a_preferred_method_outside_the_catalogue_rejected(self):
        with self.assertRaises(ValueError):
            select_method("land-repair", 0.10, preferred="weld-it")

    def test_extent_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            select_method("land-repair", 1.5)


class MaterialTests(unittest.TestCase):
    def test_an_in_date_material_at_a_safe_temperature_is_clean(self):
        self.assertEqual(
            material_findings([good_material()], PLANNED_DATE, "multilayer"), []
        )

    def test_a_material_expiring_on_the_planned_date_is_still_usable(self):
        self.assertEqual(
            material_findings(
                [good_material(expiry_date=PLANNED_DATE)], PLANNED_DATE, "multilayer"
            ),
            [],
        )

    def test_an_expired_material_is_flagged(self):
        findings = material_findings(
            [good_material(expiry_date="2026-08-01")], PLANNED_DATE, "multilayer"
        )
        self.assertTrue(any("expires on" in f for f in findings))

    def test_a_temperature_on_the_board_ceiling_is_accepted(self):
        ceiling = BOARD_MAX_PROCESS_TEMPERATURE_C["multilayer"]
        self.assertEqual(
            material_findings(
                [good_material(process_temperature_c=ceiling)], PLANNED_DATE, "multilayer"
            ),
            [],
        )

    def test_a_temperature_above_the_board_ceiling_is_flagged(self):
        findings = material_findings(
            [good_material(process_temperature_c=255.0)], PLANNED_DATE, "flexible"
        )
        self.assertTrue(any("above the" in f for f in findings))

    def test_the_same_material_may_pass_on_one_board_and_fail_on_another(self):
        material = [good_material(process_temperature_c=240.0)]
        self.assertEqual(material_findings(material, PLANNED_DATE, "multilayer"), [])
        self.assertTrue(material_findings(material, PLANNED_DATE, "rigid-flex"))

    def test_missing_material_key_rejected(self):
        material = good_material()
        del material["expiry_date"]
        with self.assertRaises(ValueError):
            material_findings([material], PLANNED_DATE, "multilayer")

    def test_unknown_board_type_rejected(self):
        with self.assertRaises(ValueError):
            material_findings([good_material()], PLANNED_DATE, "ceramic")


class ReworkCycleTests(unittest.TestCase):
    def test_a_first_repair_is_clean(self):
        self.assertEqual(rework_cycle_findings(0, 1), [])

    def test_reaching_the_budget_exactly_is_clean(self):
        self.assertEqual(rework_cycle_findings(MAX_REWORK_CYCLES - 1, 1), [])

    def test_passing_the_budget_is_flagged(self):
        self.assertTrue(rework_cycle_findings(MAX_REWORK_CYCLES, 1))

    def test_zero_planned_cycles_rejected(self):
        with self.assertRaises(ValueError):
            rework_cycle_findings(0, 0)

    def test_negative_prior_cycles_rejected(self):
        with self.assertRaises(ValueError):
            rework_cycle_findings(-1, 1)


class RiskTests(unittest.TestCase):
    def test_an_open_low_criticality_repair_scores_one(self):
        self.assertAlmostEqual(risk_score(4, "open", "none"), 1.0, places=9)

    def test_drivers_multiply(self):
        self.assertAlmostEqual(
            risk_score(1, "under-component", "repeated-reflow"), 3.0 * 2.2 * 1.8, places=9
        )

    def test_a_score_on_the_low_bound_stays_low(self):
        self.assertEqual(risk_band(2.0), "low")

    def test_a_score_on_the_medium_bound_stays_medium(self):
        self.assertEqual(risk_band(5.0), "medium")

    def test_a_score_above_the_medium_bound_is_high(self):
        self.assertEqual(risk_band(5.5), "high")

    def test_unknown_accessibility_rejected(self):
        with self.assertRaises(ValueError):
            risk_score(3, "somewhere", "none")

    def test_unknown_thermal_exposure_rejected(self):
        with self.assertRaises(ValueError):
            risk_score(3, "open", "oven")

    def test_non_positive_score_rejected(self):
        with self.assertRaises(ValueError):
            risk_band(0.0)


class PlanTests(unittest.TestCase):
    def test_a_nominal_plan_is_ready(self):
        plan = plan_repair(base_request())
        self.assertTrue(plan["ready"])
        self.assertEqual(plan["method"], "conductor-lap-solder-splice")

    def test_a_high_risk_plan_calls_for_a_coupon(self):
        plan = plan_repair(
            base_request(
                criticality=1, accessibility="under-component", thermal_exposure="repeated-reflow"
            )
        )
        self.assertTrue(plan["trial_coupon_required"])
        self.assertEqual(plan["risk_band"], "high")

    def test_an_expired_consumable_reaches_the_plan_findings(self):
        plan = plan_repair(
            base_request(materials=[good_material(expiry_date="2026-01-01")])
        )
        self.assertFalse(plan["ready"])

    def test_a_spent_location_reaches_the_plan_findings(self):
        plan = plan_repair(base_request(prior_rework_cycles=MAX_REWORK_CYCLES))
        self.assertTrue(any("thermal excursions" in f for f in plan["findings"]))

    def test_damage_beyond_the_catalogue_leaves_no_method(self):
        plan = plan_repair(
            base_request(damage_category="base-material-repair", damage_extent_fraction=0.95)
        )
        self.assertIsNone(plan["method"])
        self.assertFalse(plan["ready"])

    def test_the_plan_reports_the_date_it_was_built_for(self):
        self.assertEqual(plan_repair(base_request())["planned_date"], PLANNED_DATE)

    def test_missing_request_key_rejected(self):
        request = base_request()
        del request["board_type"]
        with self.assertRaises(ValueError):
            plan_repair(request)

    def test_non_mapping_request_rejected(self):
        with self.assertRaises(ValueError):
            plan_repair("conductor-repair")


if __name__ == "__main__":
    unittest.main()
