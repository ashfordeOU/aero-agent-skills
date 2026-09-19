"""Contract test for the holding-dimensioning leaf (stdlib unittest)."""

import unittest

from e3301_holding_torque_force_dimensioning_logic import (
    MIN_CAPABILITY_RETENTION_BY_KIND,
    MIN_DISTURBANCE_UPLIFT_BY_KIND,
    SEVERITY_BY_BASIS,
    VALID_LIFE_POINTS,
    VERDICT_NEGATIVE,
    VERDICT_POSITIVE,
    VERDICT_ZERO,
    applied_holding_factors,
    assess_held_state,
    assess_holding_dimensioning,
    effective_holding_capability,
    factored_disturbing_load,
    holding_margin,
    life_coverage_findings,
    margin_verdict,
    minimum_holding_factors,
    state_needs_power,
    validate_held_state,
)

BOTH_LIFE_POINTS = list(VALID_LIFE_POINTS)


def held_state(sid="H-1", kind="latched-mechanical", **kw):
    record = {
        "id": sid,
        "kind": kind,
        "basis": "measured-on-flight-standard-hardware",
        "holding_capability": 10.0,
        "disturbing_load": 1.0,
        "power_available": True,
        "life_points": BOTH_LIFE_POINTS,
    }
    record.update(kw)
    return record


def mechanism(**kw):
    record = {
        "id": "BOOM-ROOT-HINGE",
        "units": "torque-nm",
        "required_life_points": BOTH_LIFE_POINTS,
        "held_states": [
            held_state("H-1", "latched-mechanical"),
            held_state("H-2", "brake-unpowered", holding_capability=8.0),
        ],
    }
    record.update(kw)
    return record


class TestMinimumFactors(unittest.TestCase):
    def test_positive_latch_retains_more_than_a_friction_clamp(self):
        basis = "measured-on-flight-standard-hardware"
        latch = minimum_holding_factors("latched-mechanical", basis)
        clamp = minimum_holding_factors("friction-clamp", basis)
        self.assertGreater(
            latch["capability_retention"], clamp["capability_retention"]
        )
        self.assertLess(latch["disturbance_uplift"], clamp["disturbance_uplift"])

    def test_weak_basis_bites_from_both_sides(self):
        measured = minimum_holding_factors(
            "brake-unpowered", "measured-on-flight-standard-hardware"
        )
        estimated = minimum_holding_factors(
            "brake-unpowered", "estimated-from-heritage"
        )
        severity = SEVERITY_BY_BASIS["estimated-from-heritage"]
        self.assertAlmostEqual(
            estimated["capability_retention"],
            measured["capability_retention"] / severity,
            places=9,
        )
        self.assertAlmostEqual(
            estimated["disturbance_uplift"],
            measured["disturbance_uplift"] * severity,
            places=9,
        )

    def test_flight_standard_basis_gives_the_bare_kind_values(self):
        factors = minimum_holding_factors(
            "detent-magnetic", "measured-on-flight-standard-hardware"
        )
        self.assertAlmostEqual(
            factors["capability_retention"],
            MIN_CAPABILITY_RETENTION_BY_KIND["detent-magnetic"],
            places=9,
        )
        self.assertAlmostEqual(
            factors["disturbance_uplift"],
            MIN_DISTURBANCE_UPLIFT_BY_KIND["detent-magnetic"],
            places=9,
        )

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            minimum_holding_factors("velcro", "estimated-from-heritage")

    def test_unknown_basis_raises(self):
        with self.assertRaises(ValueError):
            minimum_holding_factors("latched-mechanical", "rumour")


class TestPowerDependence(unittest.TestCase):
    def test_powered_brake_needs_power(self):
        self.assertTrue(state_needs_power("brake-powered"))

    def test_unpowered_brake_and_latch_do_not(self):
        self.assertFalse(state_needs_power("brake-unpowered"))
        self.assertFalse(state_needs_power("latched-mechanical"))

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            state_needs_power("wishes")


class TestValidateHeldState(unittest.TestCase):
    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_held_state("H-1")

    def test_zero_capability_raises(self):
        with self.assertRaises(ValueError):
            validate_held_state(held_state(holding_capability=0.0))

    def test_zero_disturbance_raises(self):
        with self.assertRaises(ValueError):
            validate_held_state(held_state(disturbing_load=0.0))

    def test_retention_above_unity_raises(self):
        with self.assertRaises(ValueError):
            validate_held_state(held_state(declared_capability_retention=1.4))

    def test_uplift_below_unity_raises(self):
        with self.assertRaises(ValueError):
            validate_held_state(held_state(declared_disturbance_uplift=0.5))

    def test_non_boolean_power_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_held_state(held_state(power_available="maybe"))

    def test_unknown_life_point_raises(self):
        with self.assertRaises(ValueError):
            validate_held_state(held_state(life_points=["some-day"]))


class TestAppliedFactors(unittest.TestCase):
    def test_absent_declarations_fall_to_the_floor(self):
        factors, findings = applied_holding_factors(held_state())
        floor = minimum_holding_factors(
            "latched-mechanical", "measured-on-flight-standard-hardware"
        )
        self.assertAlmostEqual(
            factors["capability_retention"], floor["capability_retention"], places=9
        )
        self.assertEqual(findings, [])

    def test_optimistic_retention_is_pulled_back_and_flagged(self):
        factors, findings = applied_holding_factors(
            held_state(declared_capability_retention=1.0)
        )
        self.assertAlmostEqual(factors["capability_retention"], 0.90, places=9)
        self.assertIn(
            "declared-capability-retention-above-minimum-severity", findings
        )

    def test_light_uplift_is_pulled_up_and_flagged(self):
        factors, findings = applied_holding_factors(
            held_state(declared_disturbance_uplift=1.1)
        )
        self.assertAlmostEqual(factors["disturbance_uplift"], 1.50, places=9)
        self.assertIn("declared-disturbance-uplift-below-minimum", findings)

    def test_declaration_exactly_on_the_floor_is_accepted(self):
        floor = minimum_holding_factors(
            "latched-mechanical", "measured-on-flight-standard-hardware"
        )
        _, findings = applied_holding_factors(
            held_state(
                declared_capability_retention=floor["capability_retention"],
                declared_disturbance_uplift=floor["disturbance_uplift"],
            )
        )
        self.assertEqual(findings, [])

    def test_conservative_declarations_are_kept(self):
        factors, findings = applied_holding_factors(
            held_state(
                declared_capability_retention=0.50,
                declared_disturbance_uplift=4.00,
            )
        )
        self.assertAlmostEqual(factors["capability_retention"], 0.50, places=9)
        self.assertAlmostEqual(factors["disturbance_uplift"], 4.00, places=9)
        self.assertEqual(findings, [])


class TestCapabilityAndDisturbance(unittest.TestCase):
    def test_capability_is_knocked_down(self):
        capability, findings = effective_holding_capability(held_state())
        self.assertAlmostEqual(capability, 9.0, places=9)
        self.assertEqual(findings, [])

    def test_disturbance_is_raised(self):
        self.assertAlmostEqual(factored_disturbing_load(held_state()), 1.5, places=9)

    def test_powered_brake_without_power_holds_nothing(self):
        capability, findings = effective_holding_capability(
            held_state(kind="brake-powered", power_available=False)
        )
        self.assertAlmostEqual(capability, 0.0, places=9)
        self.assertIn("powered-hold-credited-in-an-unpowered-state", findings)

    def test_margin_is_capability_over_disturbance(self):
        self.assertAlmostEqual(holding_margin(9.0, 1.5), 5.0, places=9)

    def test_equal_capability_and_disturbance_give_zero(self):
        self.assertAlmostEqual(holding_margin(1.5, 1.5), 0.0, places=9)

    def test_zero_disturbance_raises(self):
        with self.assertRaises(ValueError):
            holding_margin(9.0, 0.0)

    def test_verdict_groups_last_place_noise_as_zero(self):
        self.assertEqual(margin_verdict(1.0e-15), VERDICT_ZERO)
        self.assertEqual(margin_verdict(0.2), VERDICT_POSITIVE)
        self.assertEqual(margin_verdict(-0.2), VERDICT_NEGATIVE)


class TestAssessHeldState(unittest.TestCase):
    def test_healthy_latch_passes(self):
        result = assess_held_state(held_state())
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["holding_margin"], 5.0, places=9)

    def test_both_factors_apply_together(self):
        result = assess_held_state(held_state(holding_capability=1.5))
        self.assertAlmostEqual(result["effective_capability"], 1.35, places=9)
        self.assertAlmostEqual(result["factored_disturbance"], 1.5, places=9)
        self.assertEqual(result["verdict"], VERDICT_NEGATIVE)

    def test_unpowered_state_is_reported_as_unheld(self):
        result = assess_held_state(
            held_state(kind="brake-powered", power_available=False)
        )
        self.assertFalse(result["compliant"])
        self.assertIn("powered-hold-credited-in-an-unpowered-state", result["findings"])

    def test_missing_end_of_life_assessment_is_a_finding(self):
        result = assess_held_state(held_state(life_points=["begin-of-life"]))
        self.assertIn("not-assessed-at:end-of-life", result["findings"])

    def test_empty_required_life_points_raises(self):
        with self.assertRaises(ValueError):
            life_coverage_findings(held_state(), [])


class TestAssessMechanism(unittest.TestCase):
    def test_clean_mechanism_passes(self):
        report = assess_holding_dimensioning(mechanism())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["unheld_state_ids"], [])

    def test_governing_state_is_the_weakest_hold(self):
        report = assess_holding_dimensioning(mechanism())
        self.assertEqual(report["governing_state_id"], "H-2")

    def test_one_failing_state_fails_the_mechanism(self):
        report = assess_holding_dimensioning(
            mechanism(
                held_states=[
                    held_state("H-1"),
                    held_state("H-2", "friction-clamp", holding_capability=1.0),
                ]
            )
        )
        self.assertFalse(report["compliant"])
        self.assertEqual(report["non_compliant_state_ids"], ["H-2"])

    def test_unpowered_state_is_listed_as_unheld(self):
        report = assess_holding_dimensioning(
            mechanism(
                held_states=[
                    held_state("H-1"),
                    held_state("H-2", "brake-powered", power_available=False),
                ]
            )
        )
        self.assertEqual(report["unheld_state_ids"], ["H-2"])

    def test_duplicate_state_id_raises(self):
        with self.assertRaises(ValueError):
            assess_holding_dimensioning(
                mechanism(held_states=[held_state("H-1"), held_state("H-1")])
            )

    def test_empty_state_list_raises(self):
        with self.assertRaises(ValueError):
            assess_holding_dimensioning(mechanism(held_states=[]))

    def test_unknown_units_raise(self):
        with self.assertRaises(ValueError):
            assess_holding_dimensioning(mechanism(units="kilogram-metres"))


if __name__ == "__main__":
    unittest.main()
