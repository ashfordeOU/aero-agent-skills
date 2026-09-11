"""
Gate-3 contract tests for e1011_eva_logic.
Stdlib unittest only; offline; deterministic.
Run: python3 test_e1011_eva.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e1011_eva_logic import (
    AbortScenario,
    ConsumablePlan,
    EvaTool,
    MobilityAssessment,
    SuitInterface,
    assess_tool,
    check_abort_timeline,
    check_suit_interface,
    compute_consumable_margin,
    evaluate_mobility,
)


class TestSuitInterface(unittest.TestCase):

    def _make_suit(self, **overrides):
        defaults = dict(
            cabin_pressure_kpa=101.3,
            suit_operating_pressure_kpa=29.6,
            life_support_duration_h=8.75,  # covers 7 h + 25%
            required_duration_h=7.0,
            suit_min_temp_c=-130.0,
            suit_max_temp_c=120.0,
            environment_min_temp_c=-100.0,
            environment_max_temp_c=100.0,
        )
        defaults.update(overrides)
        return SuitInterface(**defaults)

    def test_compatible_suit(self):
        result = check_suit_interface(self._make_suit())
        self.assertTrue(result.compatible)
        self.assertEqual(result.issues, [])

    def test_insufficient_life_support(self):
        # 6 h life support cannot cover 7 h + 25% = 8.75 h
        result = check_suit_interface(self._make_suit(life_support_duration_h=6.0))
        self.assertFalse(result.compatible)
        self.assertTrue(any("Life support" in i for i in result.issues))

    def test_environment_too_cold(self):
        result = check_suit_interface(self._make_suit(environment_min_temp_c=-150.0))
        self.assertFalse(result.compatible)
        self.assertTrue(any("thermal floor" in i for i in result.issues))

    def test_environment_too_hot(self):
        result = check_suit_interface(self._make_suit(environment_max_temp_c=135.0))
        self.assertFalse(result.compatible)
        self.assertTrue(any("thermal ceiling" in i for i in result.issues))

    def test_suit_pressure_at_cabin_raises_warning(self):
        # Suit pressure >= cabin pressure is a warning, not a blocking issue
        result = check_suit_interface(
            self._make_suit(suit_operating_pressure_kpa=101.3)
        )
        self.assertTrue(result.compatible)          # no blocking issues
        self.assertTrue(len(result.warnings) > 0)
        self.assertTrue(any("pre-breathe" in w for w in result.warnings))

    def test_invalid_cabin_pressure(self):
        with self.assertRaises(ValueError):
            check_suit_interface(self._make_suit(cabin_pressure_kpa=0.0))

    def test_invalid_required_duration(self):
        with self.assertRaises(ValueError):
            check_suit_interface(self._make_suit(required_duration_h=-1.0))

    def test_invalid_thermal_range(self):
        with self.assertRaises(ValueError):
            check_suit_interface(
                self._make_suit(suit_min_temp_c=50.0, suit_max_temp_c=10.0)
            )


class TestToolAssessment(unittest.TestCase):

    def _make_tool(self, **overrides):
        defaults = dict(
            name="wrench-7",
            max_operator_force_n=100.0,
            required_force_n=80.0,
            reach_m=0.6,
            required_reach_m=0.5,
            operation_class="one_hand",
            gloved_grip_compatible=True,
        )
        defaults.update(overrides)
        return EvaTool(**defaults)

    def test_tool_suitable(self):
        result = assess_tool(self._make_tool())
        self.assertTrue(result.suitable)
        self.assertEqual(result.issues, [])

    def test_operator_force_exceeded(self):
        result = assess_tool(self._make_tool(required_force_n=120.0))
        self.assertFalse(result.suitable)
        self.assertTrue(any("operator maximum" in i for i in result.issues))

    def test_class_limit_exceeded(self):
        # One-hand class limit is 111 N; 120 N exceeds it
        result = assess_tool(
            self._make_tool(max_operator_force_n=150.0, required_force_n=120.0)
        )
        self.assertFalse(result.suitable)
        self.assertTrue(any("class limit" in i for i in result.issues))

    def test_reach_insufficient(self):
        result = assess_tool(self._make_tool(reach_m=0.3, required_reach_m=0.5))
        self.assertFalse(result.suitable)
        self.assertTrue(any("reach" in i for i in result.issues))

    def test_glove_incompatible(self):
        result = assess_tool(self._make_tool(gloved_grip_compatible=False))
        self.assertFalse(result.suitable)
        self.assertTrue(any("glove" in i for i in result.issues))

    def test_invalid_operation_class(self):
        with self.assertRaises(ValueError):
            assess_tool(self._make_tool(operation_class="three_hand"))

    def test_two_hand_tool_within_limit(self):
        # 200 N two-hand, class limit 222 N => should pass
        result = assess_tool(
            self._make_tool(
                max_operator_force_n=210.0,
                required_force_n=200.0,
                operation_class="two_hand",
            )
        )
        self.assertTrue(result.suitable)


class TestMobilityAssessment(unittest.TestCase):

    def test_lunar_mobility_feasible(self):
        mob = MobilityAssessment(
            surface_type="lunar",
            translation_distance_m=20.0,  # 20 m / 2 m·min⁻¹ = 10 min
            allowed_time_min=15.0,
            terrain_slope_deg=10.0,
        )
        result = evaluate_mobility(mob)
        self.assertTrue(result.feasible)
        self.assertAlmostEqual(result.estimated_time_min, 10.0, places=5)

    def test_lunar_slope_exceeded(self):
        mob = MobilityAssessment(
            surface_type="lunar",
            translation_distance_m=10.0,
            allowed_time_min=30.0,
            terrain_slope_deg=25.0,  # > 20° limit
        )
        result = evaluate_mobility(mob)
        self.assertFalse(result.feasible)
        self.assertTrue(any("trafficability" in i for i in result.issues))

    def test_martian_time_exceeded(self):
        mob = MobilityAssessment(
            surface_type="martian",
            translation_distance_m=30.0,  # 30 / 1.5 = 20 min
            allowed_time_min=15.0,
        )
        result = evaluate_mobility(mob)
        self.assertFalse(result.feasible)
        self.assertTrue(any("Estimated translation" in i for i in result.issues))

    def test_invalid_surface_type(self):
        with self.assertRaises(ValueError):
            evaluate_mobility(
                MobilityAssessment(
                    surface_type="asteroid",
                    translation_distance_m=10.0,
                    allowed_time_min=5.0,
                )
            )

    def test_microgravity_slope_not_checked(self):
        # slope is N/A for microgravity (limit = 0); passing slope=30 must not flag
        mob = MobilityAssessment(
            surface_type="microgravity",
            translation_distance_m=12.0,  # 12 / 6 = 2 min
            allowed_time_min=5.0,
            terrain_slope_deg=30.0,
        )
        result = evaluate_mobility(mob)
        self.assertTrue(result.feasible)
        self.assertEqual(result.issues, [])


class TestConsumableMargin(unittest.TestCase):

    def _make_plan(self, **overrides):
        defaults = dict(
            o2_supply_kg=1.0,
            o2_consumption_rate_kg_h=0.1,   # 0.6 kg used in 6 h; 0.4 remaining > 0.25 reserve
            power_supply_wh=1000.0,
            power_consumption_w=100.0,       # 600 Wh used; 400 remaining > 250 reserve
            coolant_capacity_wh=1500.0,
            metabolic_rate_w=150.0,          # 900 Wh generated; 600 remaining > 375 reserve
            duration_h=6.0,
            required_margin_fraction=0.25,
        )
        defaults.update(overrides)
        return ConsumablePlan(**defaults)

    def test_adequate_margins(self):
        result = compute_consumable_margin(self._make_plan())
        self.assertTrue(result.adequate)
        self.assertEqual(result.issues, [])

    def test_o2_margin_insufficient(self):
        # consume 0.9 kg of 1.0 kg supply; 0.1 remaining < 0.25 reserve
        result = compute_consumable_margin(
            self._make_plan(o2_consumption_rate_kg_h=0.15)  # 0.9 kg in 6 h
        )
        self.assertFalse(result.adequate)
        self.assertTrue(any("O2" in i for i in result.issues))

    def test_power_margin_insufficient(self):
        # consume 900 Wh of 1000 Wh; 100 remaining < 250 reserve
        result = compute_consumable_margin(
            self._make_plan(power_consumption_w=150.0)
        )
        self.assertFalse(result.adequate)
        self.assertTrue(any("Power" in i for i in result.issues))

    def test_coolant_margin_insufficient(self):
        # generate 1350 Wh of 1500 Wh capacity; 150 remaining < 375 reserve
        result = compute_consumable_margin(
            self._make_plan(metabolic_rate_w=225.0)
        )
        self.assertFalse(result.adequate)
        self.assertTrue(any("Coolant" in i for i in result.issues))

    def test_invalid_margin_fraction(self):
        with self.assertRaises(ValueError):
            compute_consumable_margin(self._make_plan(required_margin_fraction=1.5))

    def test_invalid_o2_supply(self):
        with self.assertRaises(ValueError):
            compute_consumable_margin(self._make_plan(o2_supply_kg=0.0))


class TestAbortTimeline(unittest.TestCase):

    def test_abort_safe_iss(self):
        abort = AbortScenario(
            airlock_distance_m=40.0,    # 40 / 8 = 5 min
            surface_type="iss_exterior",
            abort_time_limit_min=10.0,
            consumable_remaining_h=0.5,  # 0.5 h > 5/60 h
        )
        result = check_abort_timeline(abort)
        self.assertTrue(result.safe)
        self.assertAlmostEqual(result.estimated_return_min, 5.0, places=5)

    def test_abort_return_time_exceeded(self):
        abort = AbortScenario(
            airlock_distance_m=100.0,   # 100 / 2 = 50 min > 30 min limit
            surface_type="lunar",
            abort_time_limit_min=30.0,
            consumable_remaining_h=2.0,
        )
        result = check_abort_timeline(abort)
        self.assertFalse(result.safe)
        self.assertTrue(any("safe-return limit" in i for i in result.issues))

    def test_abort_consumable_insufficient(self):
        # 60 m at 2 m/min = 30 min = 0.5 h; only 0.2 h remaining
        abort = AbortScenario(
            airlock_distance_m=60.0,
            surface_type="lunar",
            abort_time_limit_min=60.0,
            consumable_remaining_h=0.2,
        )
        result = check_abort_timeline(abort)
        self.assertFalse(result.safe)
        self.assertTrue(any("Consumable" in i for i in result.issues))

    def test_invalid_surface_type(self):
        with self.assertRaises(ValueError):
            check_abort_timeline(
                AbortScenario(
                    airlock_distance_m=10.0,
                    surface_type="europa",
                    abort_time_limit_min=20.0,
                    consumable_remaining_h=1.0,
                )
            )

    def test_zero_distance_abort(self):
        abort = AbortScenario(
            airlock_distance_m=0.0,
            surface_type="martian",
            abort_time_limit_min=5.0,
            consumable_remaining_h=0.0,
        )
        result = check_abort_timeline(abort)
        self.assertTrue(result.safe)
        self.assertAlmostEqual(result.estimated_return_min, 0.0, places=5)


if __name__ == "__main__":
    unittest.main()
