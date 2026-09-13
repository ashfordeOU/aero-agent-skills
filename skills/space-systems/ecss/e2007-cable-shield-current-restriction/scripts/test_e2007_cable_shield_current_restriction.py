"""Contract test for the cable-shield current-restriction leaf (stdlib unittest)."""

import unittest

from e2007_cable_shield_current_restriction_logic import (
    CURRENT_TOLERANCE_A,
    EXEMPT,
    NOT_EXEMPT,
    assess_cable,
    assess_shield_current_restriction,
    check_exempt_coaxial_constraints,
    check_incidental_current,
    check_intended_current_use,
    exemption_status,
    incidental_current_limit_a,
    measured_shield_current_a,
    predicted_shield_current_a,
    shield_current_share,
    validate_cable,
)


def cable(cid="K-1", function="low-frequency-signal",
          construction="twisted-shielded-pair", **kw):
    record = {
        "id": cid,
        "function": function,
        "construction": construction,
        "circuit_current_a": 2.0,
        "shield_resistance_ohm": 1.0,
        "return_resistance_ohm": 0.02,
    }
    record.update(kw)
    return record


def coax(cid="K-C", function="radiofrequency-feed", **kw):
    record = {
        "id": cid,
        "function": function,
        "construction": "coaxial",
        "shield_is_intended_return": True,
        "characteristic_impedance_ohm": 50.0,
        "shield_resistance_ohm": 0.05,
        "circuit_current_a": 0.1,
    }
    record.update(kw)
    return record


class TestValidateCable(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_cable(cable())
        self.assertFalse(norm["shield_is_intended_return"])
        self.assertTrue(norm["dedicated_return_conductor"])
        self.assertTrue(norm["shield_bonded_both_ends"])
        self.assertIsNone(norm["bond_strap_currents_a"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_cable(["K-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_cable(cable(""))

    def test_unknown_function_raises(self):
        with self.assertRaises(ValueError):
            validate_cable(cable("K-1", function="doorbell-feed"))

    def test_unknown_construction_raises(self):
        with self.assertRaises(ValueError):
            validate_cable(cable("K-1", construction="ribbon"))

    def test_non_boolean_return_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_cable(cable("K-1", shield_is_intended_return="yes"))

    def test_negative_circuit_current_raises(self):
        with self.assertRaises(ValueError):
            validate_cable(cable("K-1", circuit_current_a=-1.0))

    def test_zero_shield_resistance_raises(self):
        with self.assertRaises(ValueError):
            validate_cable(cable("K-1", shield_resistance_ohm=0.0))

    def test_negative_characteristic_impedance_raises(self):
        with self.assertRaises(ValueError):
            validate_cable(coax(characteristic_impedance_ohm=-50.0))

    def test_empty_strap_list_raises(self):
        with self.assertRaises(ValueError):
            validate_cable(cable("K-1", bond_strap_currents_a=[]))

    def test_negative_strap_current_raises(self):
        with self.assertRaises(ValueError):
            validate_cable(cable("K-1", bond_strap_currents_a=[-0.1]))

    def test_non_positive_return_resistance_raises(self):
        with self.assertRaises(ValueError):
            validate_cable(cable("K-1", return_resistance_ohm=0.0))


class TestExemptionStatus(unittest.TestCase):
    def test_coaxial_radiofrequency_feed_is_exempt(self):
        status, reason = exemption_status(coax())
        self.assertEqual(status, EXEMPT)
        self.assertEqual(reason, "coaxial-radiofrequency-feed")

    def test_coaxial_high_speed_link_is_exempt(self):
        status, reason = exemption_status(
            coax(function="high-speed-data", data_rate_mbps=100.0)
        )
        self.assertEqual(status, EXEMPT)
        self.assertEqual(reason, "coaxial-high-speed-data-link")

    def test_data_rate_exactly_at_the_threshold_is_exempt(self):
        status, _ = exemption_status(
            coax(function="high-speed-data", data_rate_mbps=10.0)
        )
        self.assertEqual(status, EXEMPT)

    def test_slow_data_link_is_not_exempt(self):
        status, reason = exemption_status(
            coax(function="high-speed-data", data_rate_mbps=1.0)
        )
        self.assertEqual(status, NOT_EXEMPT)
        self.assertEqual(reason, "data-rate-below-exemption-threshold")

    def test_non_coaxial_radiofrequency_run_is_not_exempt(self):
        status, reason = exemption_status(
            cable("K-1", function="radiofrequency-feed",
                  construction="single-shielded-wire")
        )
        self.assertEqual(status, NOT_EXEMPT)
        self.assertEqual(reason, "construction-is-not-coaxial")

    def test_coaxial_power_feed_is_not_exempt(self):
        status, reason = exemption_status(coax(function="power-distribution"))
        self.assertEqual(status, NOT_EXEMPT)
        self.assertEqual(reason, "function-outside-the-exemption")

    def test_overbraided_high_speed_link_is_not_exempt(self):
        status, reason = exemption_status(
            cable("K-1", function="high-speed-data",
                  construction="overbraided-bundle", data_rate_mbps=400.0)
        )
        self.assertEqual(status, NOT_EXEMPT)
        self.assertEqual(reason, "construction-is-not-coaxial")


class TestShieldCurrentShare(unittest.TestCase):
    def test_equal_resistances_split_evenly(self):
        self.assertAlmostEqual(shield_current_share(0.1, 0.1), 0.5)

    def test_high_shield_resistance_keeps_current_off_the_shield(self):
        self.assertAlmostEqual(shield_current_share(1.0, 0.02), 0.02 / 1.02)

    def test_zero_shield_resistance_raises(self):
        with self.assertRaises(ValueError):
            shield_current_share(0.0, 0.02)

    def test_negative_return_resistance_raises(self):
        with self.assertRaises(ValueError):
            shield_current_share(1.0, -0.02)

    def test_non_numeric_resistance_raises(self):
        with self.assertRaises(ValueError):
            shield_current_share("1.0", 0.02)


class TestMeasuredShieldCurrent(unittest.TestCase):
    def test_absent_measurement_returns_none(self):
        self.assertIsNone(measured_shield_current_a(cable()))

    def test_single_strap_is_returned(self):
        self.assertAlmostEqual(
            measured_shield_current_a(cable("K-1", bond_strap_currents_a=[0.04])), 0.04
        )

    def test_strap_currents_are_totalled(self):
        total = measured_shield_current_a(
            cable("K-1", bond_strap_currents_a=[0.01, 0.02, 0.03])
        )
        self.assertAlmostEqual(total, 0.06)


class TestPredictedShieldCurrent(unittest.TestCase):
    def test_missing_return_conductor_puts_all_current_on_the_shield(self):
        current = predicted_shield_current_a(
            cable("K-1", dedicated_return_conductor=False)
        )
        self.assertAlmostEqual(current, 2.0)

    def test_single_end_bond_carries_no_current(self):
        current = predicted_shield_current_a(
            cable("K-1", shield_bonded_both_ends=False)
        )
        self.assertAlmostEqual(current, 0.0)

    def test_parallel_division_is_applied(self):
        current = predicted_shield_current_a(cable())
        self.assertAlmostEqual(current, 2.0 * (0.02 / 1.02))

    def test_missing_return_resistance_raises(self):
        bad = cable()
        del bad["return_resistance_ohm"]
        with self.assertRaises(ValueError):
            predicted_shield_current_a(bad)


class TestIncidentalLimit(unittest.TestCase):
    def test_limit_is_five_percent_of_circuit_current(self):
        self.assertAlmostEqual(incidental_current_limit_a(cable()), 0.1)

    def test_limit_scales_with_circuit_current(self):
        self.assertAlmostEqual(
            incidental_current_limit_a(cable("K-1", circuit_current_a=40.0)), 2.0
        )


class TestIntendedCurrentUse(unittest.TestCase):
    def test_exempt_coaxial_run_is_clean(self):
        self.assertEqual(check_intended_current_use(coax()), [])

    def test_ordinary_cable_with_its_own_return_is_clean(self):
        self.assertEqual(check_intended_current_use(cable()), [])

    def test_shield_declared_as_return_is_flagged(self):
        findings = check_intended_current_use(
            cable("K-1", shield_is_intended_return=True)
        )
        self.assertIn(
            "shield-declared-as-intended-return-without-exemption", findings
        )

    def test_missing_return_conductor_is_flagged(self):
        findings = check_intended_current_use(
            cable("K-1", dedicated_return_conductor=False)
        )
        self.assertIn(
            "no-dedicated-return-conductor-forces-current-onto-shield", findings
        )

    def test_slow_data_link_using_its_shield_gets_both_findings(self):
        findings = check_intended_current_use(
            coax(function="high-speed-data", data_rate_mbps=1.0)
        )
        self.assertIn(
            "shield-declared-as-intended-return-without-exemption", findings
        )
        self.assertIn("data-rate-below-exemption-threshold", findings)


class TestIncidentalCurrent(unittest.TestCase):
    def test_exempt_run_reports_no_incidental_finding(self):
        findings, current = check_incidental_current(coax())
        self.assertEqual(findings, [])
        self.assertIsNone(current)

    def test_missing_return_conductor_is_left_to_the_other_check(self):
        findings, current = check_incidental_current(
            cable("K-1", dedicated_return_conductor=False)
        )
        self.assertEqual(findings, [])
        self.assertIsNone(current)

    def test_current_within_the_limit_is_clean(self):
        findings, current = check_incidental_current(cable())
        self.assertEqual(findings, [])
        self.assertLess(current, incidental_current_limit_a(cable()))

    def test_current_above_the_limit_is_flagged(self):
        findings, current = check_incidental_current(
            cable("K-1", shield_resistance_ohm=0.02, return_resistance_ohm=0.02)
        )
        self.assertIn("incidental-shield-current-above-limit", findings)
        self.assertAlmostEqual(current, 1.0)

    def test_measurement_overrides_the_prediction(self):
        findings, current = check_incidental_current(
            cable("K-1", shield_resistance_ohm=0.02, return_resistance_ohm=0.02,
                  bond_strap_currents_a=[0.01, 0.01])
        )
        self.assertEqual(findings, [])
        self.assertAlmostEqual(current, 0.02)

    def test_strap_total_exactly_on_the_limit_is_compliant(self):
        record = cable("K-1", circuit_current_a=2.4,
                       bond_strap_currents_a=[0.02, 0.10])
        findings, current = check_incidental_current(record)
        limit = incidental_current_limit_a(record)
        # The strap accumulation lands a few ULPs over a limit it in fact
        # sits exactly on; the named tolerance absorbs that.
        self.assertGreater(current, limit)
        self.assertLess(current - limit, CURRENT_TOLERANCE_A)
        self.assertEqual(findings, [])


class TestExemptCoaxialConstraints(unittest.TestCase):
    def test_non_exempt_cable_has_no_coaxial_constraints(self):
        self.assertEqual(check_exempt_coaxial_constraints(cable()), [])

    def test_well_formed_coaxial_run_is_clean(self):
        self.assertEqual(check_exempt_coaxial_constraints(coax()), [])

    def test_missing_characteristic_impedance_is_flagged(self):
        record = coax()
        del record["characteristic_impedance_ohm"]
        self.assertIn(
            "exempt-coaxial-characteristic-impedance-not-declared",
            check_exempt_coaxial_constraints(record),
        )

    def test_single_end_bonded_outer_conductor_is_flagged(self):
        findings = check_exempt_coaxial_constraints(
            coax(shield_bonded_both_ends=False)
        )
        self.assertIn("exempt-coaxial-outer-conductor-not-bonded-both-ends", findings)

    def test_resistive_outer_conductor_is_flagged(self):
        findings = check_exempt_coaxial_constraints(coax(shield_resistance_ohm=2.0))
        self.assertIn("exempt-coaxial-shield-resistance-above-limit", findings)

    def test_outer_conductor_exactly_at_the_resistance_limit_is_clean(self):
        self.assertEqual(check_exempt_coaxial_constraints(coax(shield_resistance_ohm=0.5)), [])


class TestAssessCable(unittest.TestCase):
    def test_ordinary_cable_is_compliant(self):
        result = assess_cable(cable())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["exemption"], NOT_EXEMPT)

    def test_exempt_coaxial_run_is_compliant(self):
        result = assess_cable(coax())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["exemption"], EXEMPT)
        self.assertEqual(result["exemption_reason"], "coaxial-radiofrequency-feed")

    def test_shield_return_without_exemption_fails(self):
        result = assess_cable(
            cable("K-1", shield_is_intended_return=True,
                  dedicated_return_conductor=False)
        )
        self.assertFalse(result["compliant"])
        self.assertIn(
            "shield-declared-as-intended-return-without-exemption",
            result["findings"],
        )
        self.assertIn(
            "no-dedicated-return-conductor-forces-current-onto-shield",
            result["findings"],
        )

    def test_limit_is_reported_with_the_result(self):
        result = assess_cable(cable())
        self.assertAlmostEqual(result["incidental_limit_a"], 0.1)


class TestAssessShieldCurrentRestriction(unittest.TestCase):
    def test_clean_cable_list_is_compliant(self):
        report = assess_shield_current_restriction([cable("K-1"), coax("K-2")])
        self.assertTrue(report["compliant"])
        self.assertEqual(report["exempt_ids"], ["K-2"])
        self.assertEqual(report["non_compliant_ids"], [])

    def test_violation_is_listed(self):
        report = assess_shield_current_restriction(
            [cable("K-1"), cable("K-2", shield_is_intended_return=True)]
        )
        self.assertFalse(report["compliant"])
        self.assertEqual(report["non_compliant_ids"], ["K-2"])

    def test_defective_coaxial_run_is_listed(self):
        report = assess_shield_current_restriction(
            [coax("K-1", shield_bonded_both_ends=False)]
        )
        self.assertFalse(report["compliant"])
        self.assertEqual(report["non_compliant_ids"], ["K-1"])

    def test_duplicate_cable_id_raises(self):
        with self.assertRaises(ValueError):
            assess_shield_current_restriction([cable("K-1"), cable("K-1")])

    def test_empty_cable_list_raises(self):
        with self.assertRaises(ValueError):
            assess_shield_current_restriction([])

    def test_non_list_input_raises(self):
        with self.assertRaises(ValueError):
            assess_shield_current_restriction(cable())


if __name__ == "__main__":
    unittest.main()
