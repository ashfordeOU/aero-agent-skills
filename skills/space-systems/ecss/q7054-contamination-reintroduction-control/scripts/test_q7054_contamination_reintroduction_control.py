"""Contract tests for the recontamination control logic."""

import unittest

from q7054_contamination_reintroduction_control_logic import (
    CONTROLS_ADEQUATE,
    CONTROLS_INSUFFICIENT,
    assess_recontamination_controls,
    control_options,
    degraded_state,
    level_for_count,
    nvr_added,
    particle_count_at,
    particles_added,
    validate_case,
    validate_exposure,
)


def handling_period(**overrides):
    """Four hours open on the integration stand under unidirectional flow."""
    period = {
        "phase": "integration",
        "cleanroom_class": "iso-7",
        "hours": 4.0,
        "orientation": "upward-facing",
        "unidirectional_flow": True,
        "bagging": "unbagged",
        "gloves": "powder-free-nitrile",
    }
    period.update(overrides)
    return period


def storage_period(**overrides):
    """Five hundred hours double-bagged in a class 8 store."""
    period = {
        "phase": "storage",
        "cleanroom_class": "iso-8",
        "hours": 500.0,
        "orientation": "upward-facing",
        "unidirectional_flow": False,
        "bagging": "double-bag",
        "gloves": "powder-free-nitrile",
    }
    period.update(overrides)
    return period


def adequate_case(**overrides):
    """A level 100 surface delivered against a level 300 requirement."""
    case = {
        "achieved_particulate_level_um": 100.0,
        "achieved_nvr_mg_per_01m2": 0.050,
        "required_particulate_level_um": 300.0,
        "required_nvr_mg_per_01m2": 0.10,
        "exposure": [handling_period(), storage_period()],
    }
    case.update(overrides)
    return case


def shortfall_case(**overrides):
    """Two hundred hours stored open; the controls do not hold the state."""
    case = {
        "achieved_particulate_level_um": 100.0,
        "achieved_nvr_mg_per_01m2": 0.050,
        "required_particulate_level_um": 150.0,
        "required_nvr_mg_per_01m2": 0.10,
        "exposure": [
            storage_period(hours=200.0, bagging="unbagged"),
        ],
    }
    case.update(overrides)
    return case


class LadderTests(unittest.TestCase):
    def test_the_count_at_the_level_itself_is_one(self):
        self.assertAlmostEqual(particle_count_at(100.0, 100.0), 1.0, places=9)

    def test_count_and_level_round_trip(self):
        count = particle_count_at(200.0)
        self.assertAlmostEqual(level_for_count(count), 200.0, places=6)

    def test_a_reference_size_above_the_level_is_rejected(self):
        with self.assertRaises(ValueError):
            particle_count_at(3.0, 5.0)

    def test_a_count_below_one_cannot_be_inverted(self):
        with self.assertRaises(ValueError):
            level_for_count(0.5)


class ExposureValidationTests(unittest.TestCase):
    def test_a_complete_period_validates(self):
        self.assertEqual(validate_exposure(handling_period())["phase"], "integration")

    def test_defaults_fill_the_optional_fields(self):
        period = validate_exposure({"cleanroom_class": "iso-7", "hours": 2.0})
        self.assertEqual(period["bagging"], "unbagged")
        self.assertEqual(period["orientation"], "upward-facing")
        self.assertFalse(period["unidirectional_flow"])

    def test_an_unknown_cleanroom_class_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure(handling_period(cleanroom_class="iso-4"))

    def test_an_unknown_glove_regime_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure(handling_period(gloves="woollen-mittens"))

    def test_a_non_boolean_flow_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure(handling_period(unidirectional_flow="yes"))

    def test_zero_hours_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure(handling_period(hours=0.0))

    def test_a_non_mapping_period_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure("four hours on the stand")


class DepositionTests(unittest.TestCase):
    def test_fallout_scales_with_time(self):
        short = particles_added(handling_period(hours=2.0))
        long = particles_added(handling_period(hours=4.0))
        self.assertAlmostEqual(long, 2.0 * short, places=9)

    def test_unidirectional_flow_cuts_the_fallout(self):
        still = particles_added(handling_period(unidirectional_flow=False))
        flowing = particles_added(handling_period(unidirectional_flow=True))
        self.assertLess(flowing, still)

    def test_a_double_bag_cuts_the_fallout_hardest(self):
        open_item = particles_added(handling_period(bagging="unbagged"))
        single = particles_added(handling_period(bagging="single-bag"))
        double = particles_added(handling_period(bagging="double-bag"))
        self.assertLess(double, single)
        self.assertLess(single, open_item)

    def test_turning_the_surface_away_cuts_the_fallout(self):
        up = particles_added(handling_period(orientation="upward-facing"))
        down = particles_added(handling_period(orientation="downward-facing"))
        self.assertLess(down, up)

    def test_gloves_deposit_residue_on_open_hardware(self):
        bare = nvr_added(handling_period(gloves="bare-hands"))
        gloved = nvr_added(handling_period(gloves="cleanroom-nitrile-double"))
        self.assertLess(gloved, bare)

    def test_a_bagged_item_takes_bag_residue_not_glove_residue(self):
        bagged_bare = nvr_added(handling_period(bagging="double-bag", gloves="bare-hands"))
        bagged_clean = nvr_added(
            handling_period(bagging="double-bag", gloves="cleanroom-nitrile-double")
        )
        self.assertAlmostEqual(bagged_bare, bagged_clean, places=12)

    def test_a_worse_room_deposits_more(self):
        clean_room = particles_added(handling_period(cleanroom_class="iso-5"))
        dirty_room = particles_added(handling_period(cleanroom_class="iso-8"))
        self.assertLess(clean_room, dirty_room)


class CaseValidationTests(unittest.TestCase):
    def test_a_complete_case_validates(self):
        self.assertEqual(len(validate_case(adequate_case())["exposure"]), 2)

    def test_an_empty_exposure_profile_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(adequate_case(exposure=[]))

    def test_a_mapping_passed_as_exposure_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(adequate_case(exposure=handling_period()))

    def test_a_negative_achieved_residue_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(adequate_case(achieved_nvr_mg_per_01m2=-0.01))

    def test_a_zero_requirement_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(adequate_case(required_nvr_mg_per_01m2=0.0))


class DegradationTests(unittest.TestCase):
    def test_the_level_always_degrades_over_a_real_exposure(self):
        state = degraded_state(adequate_case())
        self.assertGreater(state["degraded_particulate_level_um"], 100.0)

    def test_residue_accumulates_on_top_of_the_achieved_value(self):
        state = degraded_state(adequate_case())
        self.assertGreater(state["degraded_nvr_mg_per_01m2"], 0.050)

    def test_a_short_protected_exposure_still_meets_the_requirement(self):
        state = degraded_state(adequate_case())
        self.assertTrue(state["particulate_requirement_met"])
        self.assertTrue(state["nvr_requirement_met"])

    def test_an_open_store_breaks_both_ladders(self):
        state = degraded_state(shortfall_case())
        self.assertFalse(state["particulate_requirement_met"])
        self.assertFalse(state["nvr_requirement_met"])


class ControlOptionTests(unittest.TestCase):
    def test_options_are_ranked_by_remaining_shortfall(self):
        shortfalls = [
            option["remaining_shortfall"] for option in control_options(shortfall_case())
        ]
        self.assertEqual(shortfalls, sorted(shortfalls))

    def test_bagging_is_the_control_that_buys_back_most(self):
        best = control_options(shortfall_case())[0]
        self.assertEqual(best["control"], "double-bag-the-hardware")

    def test_a_control_already_in_force_is_not_offered(self):
        case = adequate_case(
            exposure=[
                storage_period(
                    cleanroom_class="iso-5",
                    orientation="downward-facing",
                    unidirectional_flow=True,
                    bagging="double-bag",
                    gloves="cleanroom-nitrile-double",
                )
            ]
        )
        offered = [option["control"] for option in control_options(case)]
        self.assertEqual(offered, ["halve-the-exposure-time"])


class AssessmentTests(unittest.TestCase):
    def test_a_protected_delivery_is_adequate(self):
        result = assess_recontamination_controls(adequate_case())
        self.assertEqual(result["verdict"], CONTROLS_ADEQUATE)
        self.assertIsNone(result["best_control"])

    def test_an_open_store_is_insufficient_and_names_a_control(self):
        result = assess_recontamination_controls(shortfall_case())
        self.assertEqual(result["verdict"], CONTROLS_INSUFFICIENT)
        self.assertEqual(result["best_control"]["control"], "double-bag-the-hardware")

    def test_bare_handed_handling_is_a_finding(self):
        result = assess_recontamination_controls(
            adequate_case(exposure=[handling_period(gloves="bare-hands")])
        )
        self.assertTrue(any("sheds residue" in f for f in result["findings"]))

    def test_an_open_upward_surface_with_no_flow_is_a_finding(self):
        result = assess_recontamination_controls(
            adequate_case(
                exposure=[handling_period(cleanroom_class="iso-8", unidirectional_flow=False)]
            )
        )
        self.assertTrue(any("fallout is the dominant term" in f for f in result["findings"]))

    def test_open_exposure_hours_count_only_the_unbagged_periods(self):
        result = assess_recontamination_controls(adequate_case())
        self.assertAlmostEqual(result["open_exposure_hours"], 4.0, places=9)

    def test_the_degraded_and_achieved_states_both_travel(self):
        result = assess_recontamination_controls(adequate_case())
        self.assertAlmostEqual(result["achieved_particulate_level_um"], 100.0, places=9)
        self.assertGreater(
            result["degraded_particulate_level_um"],
            result["achieved_particulate_level_um"],
        )

    def test_both_shortfall_findings_are_named(self):
        result = assess_recontamination_controls(shortfall_case())
        self.assertTrue(any("particulate level degrades" in f for f in result["findings"]))
        self.assertTrue(any("residue rises" in f for f in result["findings"]))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_recontamination_controls([handling_period()])


if __name__ == "__main__":
    unittest.main()
