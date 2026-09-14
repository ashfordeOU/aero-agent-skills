"""Contract tests for the clause 9.2 pure tin whisker risk logic."""

import unittest

from q6013_pure_tin_finish_risk_analysis_logic import (
    ARC_SUSTAINING_CURRENT_A,
    ARC_SUSTAINING_REQUIRED_MARGIN,
    ARC_SUSTAINING_VOLTAGE_V,
    BASE_GROWTH_UM_PER_YEAR,
    BASE_REQUIRED_BRIDGING_MARGIN,
    CONFORMAL_COATING_FACTOR,
    CONTROLLABLE_RATIO_FLOOR,
    FINISH_FACTORS,
    MARGIN_TOLERANCE,
    PURE_TIN_LEAD_THRESHOLD_PERCENT,
    RISK_CATEGORIES,
    SUBSTRATE_FACTORS,
    THICK_PLATING_UM,
    THIN_PLATING_UM,
    UNDERPLATE_FACTORS,
    arc_can_be_sustained,
    assess_pure_tin_risk,
    bounding_whisker_length,
    bridging_margin,
    is_pure_tin,
    normalize_token,
    plating_thickness_factor,
    required_bridging_margin,
    required_controls,
    risk_category,
    validate_circuit,
    validate_finish,
)


def _finish(**overrides):
    finish = {
        "finish_type": "bright-tin",
        "lead_mass_percent": 0.0,
        "plating_thickness_um": 5.0,
        "underplate": "none",
        "substrate": "copper",
    }
    finish.update(overrides)
    return finish


def _circuit(**overrides):
    circuit = {
        "min_conductor_spacing_um": 200.0,
        "operating_voltage_v": 3.3,
        "available_current_a": 0.1,
    }
    circuit.update(overrides)
    return circuit


def _part(**overrides):
    part = {
        "part_number": "RC-3310-SN",
        "finish": _finish(),
        "circuit": _circuit(),
        "mission_years": 5.0,
        "conformal_coated": False,
    }
    part.update(overrides)
    return part


class PureTinThresholdTests(unittest.TestCase):
    def test_lead_free_finish_is_pure_tin(self):
        self.assertTrue(is_pure_tin(0.0))

    def test_finish_just_below_the_threshold_is_pure_tin(self):
        self.assertTrue(is_pure_tin(2.9))

    def test_finish_on_the_threshold_is_not_pure_tin(self):
        self.assertFalse(is_pure_tin(PURE_TIN_LEAD_THRESHOLD_PERCENT))

    def test_leaded_finish_is_not_pure_tin(self):
        self.assertFalse(is_pure_tin(37.0))

    def test_negative_lead_content_rejected(self):
        with self.assertRaises(ValueError):
            is_pure_tin(-1.0)

    def test_lead_content_above_one_hundred_rejected(self):
        with self.assertRaises(ValueError):
            is_pure_tin(140.0)

    def test_non_numeric_lead_content_rejected(self):
        with self.assertRaises(ValueError):
            is_pure_tin("none")


class FinishValidationTests(unittest.TestCase):
    def test_finish_returned_validated(self):
        entry = validate_finish(_finish())
        self.assertEqual(entry["finish_type"], "bright-tin")
        self.assertTrue(entry["pure_tin"])

    def test_token_normalization_is_hyphenated_lower_case(self):
        self.assertEqual(normalize_token("Matte_Tin"), "matte-tin")

    def test_every_finish_type_validates(self):
        for token in FINISH_FACTORS:
            entry = validate_finish(_finish(finish_type=token))
            self.assertEqual(entry["finish_type"], token)

    def test_every_underplate_validates(self):
        for token in UNDERPLATE_FACTORS:
            entry = validate_finish(_finish(underplate=token))
            self.assertEqual(entry["underplate"], token)

    def test_every_substrate_validates(self):
        for token in SUBSTRATE_FACTORS:
            entry = validate_finish(_finish(substrate=token))
            self.assertEqual(entry["substrate"], token)

    def test_unknown_finish_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_finish(_finish(finish_type="gold-leaf"))

    def test_unknown_substrate_rejected(self):
        with self.assertRaises(ValueError):
            validate_finish(_finish(substrate="unobtainium"))

    def test_missing_underplate_key_rejected(self):
        bad = _finish()
        del bad["underplate"]
        with self.assertRaises(ValueError):
            validate_finish(bad)

    def test_zero_plating_thickness_rejected(self):
        with self.assertRaises(ValueError):
            validate_finish(_finish(plating_thickness_um=0.0))

    def test_non_mapping_finish_rejected(self):
        with self.assertRaises(ValueError):
            validate_finish("bright-tin")

    def test_bright_tin_is_the_reference_finish_factor(self):
        self.assertAlmostEqual(FINISH_FACTORS["bright-tin"], 1.0, places=9)

    def test_matte_tin_is_gentler_than_bright_tin(self):
        self.assertLess(FINISH_FACTORS["matte-tin"], FINISH_FACTORS["bright-tin"])

    def test_brass_is_the_worst_substrate(self):
        self.assertAlmostEqual(
            SUBSTRATE_FACTORS["brass"], max(SUBSTRATE_FACTORS.values()), places=9
        )


class CircuitValidationTests(unittest.TestCase):
    def test_circuit_returned_validated(self):
        entry = validate_circuit(_circuit())
        self.assertAlmostEqual(entry["min_conductor_spacing_um"], 200.0, places=9)

    def test_zero_spacing_rejected(self):
        with self.assertRaises(ValueError):
            validate_circuit(_circuit(min_conductor_spacing_um=0.0))

    def test_negative_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_circuit(_circuit(operating_voltage_v=-1.0))

    def test_zero_voltage_accepted(self):
        entry = validate_circuit(_circuit(operating_voltage_v=0.0))
        self.assertAlmostEqual(entry["operating_voltage_v"], 0.0, places=9)

    def test_missing_current_key_rejected(self):
        bad = _circuit()
        del bad["available_current_a"]
        with self.assertRaises(ValueError):
            validate_circuit(bad)

    def test_non_mapping_circuit_rejected(self):
        with self.assertRaises(ValueError):
            validate_circuit([200.0, 3.3, 0.1])


class ThicknessFactorTests(unittest.TestCase):
    def test_thin_plating_raises_the_bound(self):
        self.assertAlmostEqual(plating_thickness_factor(1.0), 1.4, places=9)

    def test_plating_on_the_thin_boundary_leaves_the_thin_band(self):
        self.assertAlmostEqual(
            plating_thickness_factor(THIN_PLATING_UM), 1.0, places=9
        )

    def test_mid_band_plating_is_neutral(self):
        self.assertAlmostEqual(plating_thickness_factor(5.0), 1.0, places=9)

    def test_plating_on_the_thick_boundary_enters_the_thick_band(self):
        self.assertAlmostEqual(
            plating_thickness_factor(THICK_PLATING_UM), 0.7, places=9
        )

    def test_thick_plating_lowers_the_bound(self):
        self.assertAlmostEqual(plating_thickness_factor(25.0), 0.7, places=9)

    def test_negative_thickness_rejected(self):
        with self.assertRaises(ValueError):
            plating_thickness_factor(-3.0)


class ArcTests(unittest.TestCase):
    def test_low_voltage_low_current_cannot_sustain_an_arc(self):
        self.assertFalse(arc_can_be_sustained(3.3, 0.1))

    def test_both_thresholds_met_can_sustain_an_arc(self):
        self.assertTrue(
            arc_can_be_sustained(ARC_SUSTAINING_VOLTAGE_V, ARC_SUSTAINING_CURRENT_A)
        )

    def test_voltage_alone_cannot_sustain_an_arc(self):
        self.assertFalse(arc_can_be_sustained(28.0, 0.05))

    def test_current_alone_cannot_sustain_an_arc(self):
        self.assertFalse(arc_can_be_sustained(3.3, 5.0))

    def test_arc_capable_circuit_doubles_the_required_margin(self):
        self.assertAlmostEqual(
            required_bridging_margin(28.0, 1.0),
            ARC_SUSTAINING_REQUIRED_MARGIN,
            places=9,
        )

    def test_benign_circuit_uses_the_base_required_margin(self):
        self.assertAlmostEqual(
            required_bridging_margin(3.3, 0.1),
            BASE_REQUIRED_BRIDGING_MARGIN,
            places=9,
        )


class BoundingLengthTests(unittest.TestCase):
    def test_reference_case_is_the_base_rate_over_the_mission(self):
        length = bounding_whisker_length(_finish(), 5.0)
        self.assertAlmostEqual(length, BASE_GROWTH_UM_PER_YEAR * 5.0, places=9)

    def test_nickel_underplate_lowers_the_bound(self):
        plain = bounding_whisker_length(_finish(), 5.0)
        barriered = bounding_whisker_length(_finish(underplate="nickel"), 5.0)
        self.assertAlmostEqual(barriered, plain * 0.3, places=9)

    def test_brass_substrate_raises_the_bound(self):
        length = bounding_whisker_length(_finish(substrate="brass"), 5.0)
        self.assertAlmostEqual(length, 300.0, places=9)

    def test_thin_plating_over_brass_is_the_worst_case(self):
        length = bounding_whisker_length(
            _finish(substrate="brass", plating_thickness_um=1.0), 5.0
        )
        self.assertAlmostEqual(length, 420.0, places=9)

    def test_conformal_coating_applies_its_factor(self):
        bare = bounding_whisker_length(_finish(), 5.0, False)
        coated = bounding_whisker_length(_finish(), 5.0, True)
        self.assertAlmostEqual(coated, bare * CONFORMAL_COATING_FACTOR, places=9)

    def test_bound_scales_with_the_mission(self):
        short = bounding_whisker_length(_finish(), 2.0)
        long = bounding_whisker_length(_finish(), 4.0)
        self.assertAlmostEqual(long, short * 2.0, places=9)

    def test_zero_mission_years_rejected(self):
        with self.assertRaises(ValueError):
            bounding_whisker_length(_finish(), 0.0)

    def test_non_boolean_coating_flag_rejected(self):
        with self.assertRaises(ValueError):
            bounding_whisker_length(_finish(), 5.0, "yes")


class MarginTests(unittest.TestCase):
    def test_margin_is_spacing_over_the_bound(self):
        self.assertAlmostEqual(bridging_margin(400.0, 200.0), 2.0, places=9)

    def test_zero_bound_rejected(self):
        with self.assertRaises(ValueError):
            bridging_margin(400.0, 0.0)

    def test_zero_spacing_rejected(self):
        with self.assertRaises(ValueError):
            bridging_margin(0.0, 200.0)

    def test_margin_exactly_on_the_requirement_is_acceptable(self):
        self.assertEqual(risk_category(1.0, 1.0), "acceptable")

    def test_margin_above_the_requirement_is_acceptable(self):
        self.assertEqual(risk_category(3.0, 1.0), "acceptable")

    def test_margin_below_the_requirement_needs_controls(self):
        self.assertEqual(risk_category(0.5, 1.0), "controls-required")

    def test_margin_exactly_on_the_control_floor_still_takes_controls(self):
        self.assertEqual(
            risk_category(CONTROLLABLE_RATIO_FLOOR, 1.0), "controls-required"
        )

    def test_margin_below_the_control_floor_is_not_acceptable(self):
        self.assertEqual(risk_category(0.1, 1.0), "not-acceptable")

    def test_doubled_requirement_moves_the_boundary(self):
        self.assertEqual(risk_category(1.0, 2.0), "controls-required")
        self.assertEqual(risk_category(2.0, 2.0), "acceptable")

    def test_every_category_returned_is_a_recognized_category(self):
        for margin in (0.05, 0.25, 0.5, 1.0, 4.0):
            self.assertIn(risk_category(margin, 1.0), RISK_CATEGORIES)

    def test_margin_tolerance_is_representation_sized(self):
        self.assertLess(MARGIN_TOLERANCE, 1e-6)


class ControlTests(unittest.TestCase):
    def test_leaded_finish_takes_no_controls(self):
        finish = validate_finish(_finish(lead_mass_percent=37.0))
        self.assertEqual(required_controls(finish, "acceptable", False, False), [])

    def test_pure_tin_always_reaches_the_declared_component_list(self):
        finish = validate_finish(_finish(finish_type="reflowed-tin",
                                         underplate="nickel"))
        controls = required_controls(finish, "acceptable", False, False)
        self.assertEqual(controls, ["pure-tin-entry-in-declared-component-list"])

    def test_bright_tin_takes_a_refinish_control(self):
        finish = validate_finish(_finish())
        controls = required_controls(finish, "acceptable", False, False)
        self.assertIn("matte-or-reflowed-tin-refinish", controls)

    def test_bare_substrate_takes_a_barrier_underplate_control(self):
        finish = validate_finish(_finish())
        controls = required_controls(finish, "acceptable", False, False)
        self.assertIn("nickel-underplate-barrier", controls)

    def test_controls_required_adds_coating_and_spacing(self):
        finish = validate_finish(_finish())
        controls = required_controls(finish, "controls-required", False, False)
        self.assertIn("conformal-coating-over-the-termination", controls)
        self.assertIn("increase-minimum-conductor-spacing", controls)

    def test_an_already_coated_assembly_is_not_told_to_coat_again(self):
        finish = validate_finish(_finish())
        controls = required_controls(finish, "controls-required", False, True)
        self.assertNotIn("conformal-coating-over-the-termination", controls)

    def test_arc_capable_circuit_takes_a_current_limit_control(self):
        finish = validate_finish(_finish())
        controls = required_controls(finish, "acceptable", True, False)
        self.assertIn(
            "series-impedance-or-current-limit-against-sustained-arc", controls
        )

    def test_not_acceptable_takes_the_rework_control(self):
        finish = validate_finish(_finish())
        controls = required_controls(finish, "not-acceptable", False, False)
        self.assertIn(
            "hot-solder-dip-or-re-tin-with-a-lead-bearing-alloy", controls
        )


class AssessmentTests(unittest.TestCase):
    def test_leaded_finish_is_outside_the_provision(self):
        result = assess_pure_tin_risk(
            _part(finish=_finish(lead_mass_percent=37.0))
        )
        self.assertFalse(result["pure_tin"])
        self.assertEqual(result["risk_category"], "not-applicable")
        self.assertEqual(result["controls"], [])
        self.assertTrue(result["acceptable_as_built"])

    def test_margin_exactly_on_the_requirement_is_acceptable_as_built(self):
        result = assess_pure_tin_risk(_part())
        self.assertAlmostEqual(result["bounding_whisker_length_um"], 200.0, places=9)
        self.assertAlmostEqual(result["bridging_margin"], 1.0, places=9)
        self.assertEqual(result["risk_category"], "acceptable")
        self.assertTrue(result["acceptable_as_built"])

    def test_generous_spacing_stays_acceptable(self):
        result = assess_pure_tin_risk(
            _part(circuit=_circuit(min_conductor_spacing_um=1000.0))
        )
        self.assertEqual(result["risk_category"], "acceptable")
        self.assertAlmostEqual(result["margin_ratio"], 5.0, places=9)

    def test_arc_capable_circuit_halves_the_ratio(self):
        result = assess_pure_tin_risk(
            _part(
                circuit=_circuit(operating_voltage_v=28.0, available_current_a=1.0)
            )
        )
        self.assertTrue(result["arc_can_be_sustained"])
        self.assertAlmostEqual(result["margin_required"], 2.0, places=9)
        self.assertAlmostEqual(result["margin_ratio"], 0.5, places=9)
        self.assertEqual(result["risk_category"], "controls-required")

    def test_tight_spacing_is_not_acceptable(self):
        result = assess_pure_tin_risk(
            _part(circuit=_circuit(min_conductor_spacing_um=40.0))
        )
        self.assertAlmostEqual(result["margin_ratio"], 0.2, places=9)
        self.assertEqual(result["risk_category"], "not-acceptable")
        self.assertFalse(result["acceptable_as_built"])

    def test_spacing_exactly_on_the_control_floor_takes_controls(self):
        result = assess_pure_tin_risk(
            _part(circuit=_circuit(min_conductor_spacing_um=50.0))
        )
        self.assertAlmostEqual(result["margin_ratio"], 0.25, places=9)
        self.assertEqual(result["risk_category"], "controls-required")

    def test_coating_recovers_a_marginal_design(self):
        bare = assess_pure_tin_risk(
            _part(circuit=_circuit(min_conductor_spacing_um=100.0))
        )
        coated = assess_pure_tin_risk(
            _part(
                circuit=_circuit(min_conductor_spacing_um=100.0),
                conformal_coated=True,
            )
        )
        self.assertEqual(bare["risk_category"], "controls-required")
        self.assertEqual(coated["risk_category"], "acceptable")

    def test_nickel_barrier_removes_the_barrier_finding(self):
        result = assess_pure_tin_risk(
            _part(finish=_finish(underplate="nickel", finish_type="matte-tin"))
        )
        self.assertFalse(any("barrier underplate" in f for f in result["findings"]))

    def test_bare_brass_bright_tin_raises_several_findings(self):
        result = assess_pure_tin_risk(
            _part(
                finish=_finish(substrate="brass", plating_thickness_um=1.0),
                circuit=_circuit(
                    min_conductor_spacing_um=60.0,
                    operating_voltage_v=28.0,
                    available_current_a=2.0,
                ),
            )
        )
        self.assertEqual(result["risk_category"], "not-acceptable")
        self.assertGreaterEqual(len(result["findings"]), 4)

    def test_missing_part_key_rejected(self):
        part = _part()
        del part["circuit"]
        with self.assertRaises(ValueError):
            assess_pure_tin_risk(part)

    def test_blank_part_number_rejected(self):
        with self.assertRaises(ValueError):
            assess_pure_tin_risk(_part(part_number="   "))

    def test_non_mapping_part_rejected(self):
        with self.assertRaises(ValueError):
            assess_pure_tin_risk(["RC-3310-SN"])

    def test_zero_mission_rejected(self):
        with self.assertRaises(ValueError):
            assess_pure_tin_risk(_part(mission_years=0.0))

    def test_coating_flag_defaults_to_false(self):
        part = _part()
        del part["conformal_coated"]
        result = assess_pure_tin_risk(part)
        self.assertFalse(result["conformal_coated"])


if __name__ == "__main__":
    unittest.main()
