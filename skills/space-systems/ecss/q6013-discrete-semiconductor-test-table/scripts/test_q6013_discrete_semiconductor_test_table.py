"""Contract tests for the Table 8-3 discrete semiconductor matrix logic.

The cases follow the workflow one step at a time: family resolution, the
per-family required groups, the signed drift of a parameter and the
direction it degrades in, the per-device verdict, matrix coverage, the
per-row count verdict and the disposition that stops a lot short of
acceptance. Each step is exercised on both sides of its limit, so a review
of the record shows what was judged and not only the verdict.
"""

import unittest

from q6013_discrete_semiconductor_test_table_logic import (
    DEVICE_FAMILIES,
    FAMILY_PARAMETERS,
    LIMIT_TOLERANCE,
    assess_discrete_semiconductor_test_table,
    drift_within_limit,
    evaluate_device,
    evaluate_parameter,
    matrix_coverage,
    normalize_family,
    relative_drift_percent,
    required_test_groups,
    row_verdict,
)


def _row(group, method="method-ref", sample_size=32, failures=0, accept_number=1):
    return {
        "group": group,
        "method": method,
        "sample_size": sample_size,
        "failures": failures,
        "accept_number": accept_number,
    }


def _full_matrix(family="diode", **per_group):
    return [_row(group, **per_group.get(group, {})) for group in required_test_groups(family)]


def _spec(family="diode", **overrides):
    spec = {"family": family, "entries": _full_matrix(family)}
    spec.update(overrides)
    return spec


class FamilyTests(unittest.TestCase):
    def test_family_name_is_normalized(self):
        self.assertEqual(normalize_family("  Transistor "), "transistor")

    def test_every_declared_family_has_a_group_set(self):
        for family in DEVICE_FAMILIES:
            self.assertGreater(len(required_test_groups(family)), 0)

    def test_optocoupler_adds_the_isolation_group(self):
        self.assertIn("isolation-voltage", required_test_groups("optocoupler"))

    def test_diode_has_no_isolation_group(self):
        self.assertNotIn("isolation-voltage", required_test_groups("diode"))

    def test_transistor_adds_its_own_group(self):
        self.assertIn("safe-operating-area-check", required_test_groups("transistor"))

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            normalize_family("thyristor")

    def test_blank_family_rejected(self):
        with self.assertRaises(ValueError):
            normalize_family("   ")

    def test_non_string_family_rejected(self):
        with self.assertRaises(ValueError):
            normalize_family(3)


class DriftTests(unittest.TestCase):
    def test_upward_drift_is_positive(self):
        self.assertAlmostEqual(relative_drift_percent(100.0, 110.0), 10.0, places=9)

    def test_downward_drift_is_negative(self):
        self.assertAlmostEqual(relative_drift_percent(100.0, 80.0), -20.0, places=9)

    def test_drift_is_referenced_to_the_magnitude_of_the_initial_reading(self):
        self.assertAlmostEqual(relative_drift_percent(-100.0, -90.0), 10.0, places=9)

    def test_zero_initial_reading_rejected(self):
        with self.assertRaises(ValueError):
            relative_drift_percent(0.0, 5.0)

    def test_both_direction_bounds_the_magnitude(self):
        self.assertTrue(drift_within_limit(100.0, 108.0, 10.0, "both"))
        self.assertFalse(drift_within_limit(100.0, 85.0, 10.0, "both"))

    def test_increase_direction_ignores_a_fall(self):
        self.assertTrue(drift_within_limit(100.0, 40.0, 10.0, "increase"))

    def test_increase_direction_catches_a_rise(self):
        self.assertFalse(drift_within_limit(100.0, 130.0, 10.0, "increase"))

    def test_decrease_direction_ignores_a_rise(self):
        self.assertTrue(drift_within_limit(100.0, 150.0, 20.0, "decrease"))

    def test_decrease_direction_catches_a_fall(self):
        self.assertFalse(drift_within_limit(100.0, 70.0, 20.0, "decrease"))

    def test_drift_exactly_on_the_limit_passes(self):
        self.assertTrue(drift_within_limit(100.0, 110.0, 10.0, "both"))

    def test_tolerance_absorbs_representation_error_at_the_limit(self):
        self.assertTrue(
            drift_within_limit(100.0, 110.0 + LIMIT_TOLERANCE / 1000.0, 10.0, "both")
        )

    def test_unknown_direction_rejected(self):
        with self.assertRaises(ValueError):
            drift_within_limit(100.0, 110.0, 10.0, "sideways")

    def test_negative_limit_rejected(self):
        with self.assertRaises(ValueError):
            drift_within_limit(100.0, 110.0, -10.0, "both")


class ParameterRecordTests(unittest.TestCase):
    def test_optocoupler_transfer_ratio_degrades_downward(self):
        record = evaluate_parameter("optocoupler", "current-transfer-ratio", 100.0, 75.0, 20.0)
        self.assertEqual(record["direction"], "decrease")
        self.assertFalse(record["within_limit"])

    def test_optocoupler_transfer_ratio_rise_is_not_a_reject(self):
        record = evaluate_parameter("optocoupler", "current-transfer-ratio", 100.0, 140.0, 20.0)
        self.assertTrue(record["within_limit"])

    def test_diode_reverse_leakage_degrades_upward(self):
        record = evaluate_parameter("diode", "reverse-leakage", 1.0, 3.0, 50.0)
        self.assertEqual(record["direction"], "increase")
        self.assertFalse(record["within_limit"])

    def test_diode_forward_voltage_is_bounded_both_ways(self):
        record = evaluate_parameter("diode", "forward-voltage", 0.70, 0.60, 5.0)
        self.assertEqual(record["direction"], "both")
        self.assertFalse(record["within_limit"])

    def test_transistor_gain_is_bounded_both_ways(self):
        record = evaluate_parameter("transistor", "forward-current-gain", 150.0, 160.0, 20.0)
        self.assertTrue(record["within_limit"])
        self.assertAlmostEqual(record["drift_percent"], 20.0 / 3.0, places=9)

    def test_parameter_outside_the_family_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_parameter("diode", "current-transfer-ratio", 100.0, 90.0, 10.0)

    def test_every_family_parameter_has_a_known_direction(self):
        for family, parameters in FAMILY_PARAMETERS.items():
            for direction in parameters.values():
                self.assertIn(direction, ("both", "increase", "decrease"))


class DeviceTests(unittest.TestCase):
    def test_clean_device_is_not_rejected(self):
        record = evaluate_device(
            "diode",
            {"forward-voltage": (0.70, 0.71), "reverse-leakage": (1.0, 1.2)},
            {"forward-voltage": 5.0, "reverse-leakage": 50.0},
        )
        self.assertFalse(record["rejected"])
        self.assertEqual(record["drifted_parameters"], [])

    def test_drifted_parameter_is_named(self):
        record = evaluate_device(
            "diode",
            {"forward-voltage": (0.70, 0.90), "reverse-leakage": (1.0, 1.1)},
            {"forward-voltage": 5.0, "reverse-leakage": 50.0},
        )
        self.assertEqual(record["drifted_parameters"], ["forward-voltage"])
        self.assertTrue(record["rejected"])

    def test_missing_limit_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_device("diode", {"forward-voltage": (0.70, 0.71)}, {})

    def test_malformed_reading_pair_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_device("diode", {"forward-voltage": (0.70,)}, {"forward-voltage": 5.0})

    def test_empty_readings_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_device("diode", {}, {"forward-voltage": 5.0})


class CoverageTests(unittest.TestCase):
    def test_full_matrix_is_complete(self):
        self.assertTrue(matrix_coverage("diode", _full_matrix("diode"))["complete"])

    def test_diode_matrix_offered_for_an_optocoupler_is_incomplete(self):
        coverage = matrix_coverage("optocoupler", _full_matrix("diode"))
        self.assertIn("isolation-voltage", coverage["missing"])
        self.assertIn("reverse-bias-stress", coverage["unrecognized"])

    def test_duplicated_group_is_named(self):
        rows = _full_matrix("diode") + [_row("burn-in", method="second-method")]
        self.assertEqual(matrix_coverage("diode", rows)["duplicated"], ["burn-in"])

    def test_empty_matrix_rejected(self):
        with self.assertRaises(ValueError):
            matrix_coverage("diode", [])

    def test_row_without_a_group_rejected(self):
        with self.assertRaises(ValueError):
            matrix_coverage("diode", [{"method": "method-ref"}])


class RowVerdictTests(unittest.TestCase):
    def test_clean_row_accepts(self):
        record = row_verdict(_row("burn-in"))
        self.assertTrue(record["accepted"])

    def test_failures_over_the_accept_number_reject(self):
        record = row_verdict(_row("life-test", failures=3, accept_number=1))
        self.assertFalse(record["accepted"])

    def test_accept_number_used_in_full_is_marginal(self):
        record = row_verdict(_row("life-test", failures=1, accept_number=1))
        self.assertTrue(record["accepted"])
        self.assertTrue(record["marginal"])

    def test_failures_larger_than_the_sample_rejected(self):
        with self.assertRaises(ValueError):
            row_verdict(_row("life-test", sample_size=10, failures=20))

    def test_accept_number_larger_than_the_sample_rejected(self):
        with self.assertRaises(ValueError):
            row_verdict(_row("life-test", sample_size=10, accept_number=20))

    def test_blank_method_reference_rejected(self):
        with self.assertRaises(ValueError):
            row_verdict(_row("life-test", method="  "))

    def test_zero_sample_rejected(self):
        with self.assertRaises(ValueError):
            row_verdict(_row("life-test", sample_size=0))


class AssessmentTests(unittest.TestCase):
    def test_complete_clean_matrix_accepts(self):
        result = assess_discrete_semiconductor_test_table(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "accept")

    def test_family_is_carried_into_the_record(self):
        result = assess_discrete_semiconductor_test_table(_spec(family="optocoupler"))
        self.assertEqual(result["family"], "optocoupler")

    def test_missing_group_holds_the_lot(self):
        rows = [r for r in _full_matrix("diode") if r["group"] != "life-test"]
        result = assess_discrete_semiconductor_test_table(_spec(entries=rows))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["disposition"], "hold")

    def test_every_rejecting_group_is_named_not_just_the_first(self):
        rows = _full_matrix(
            "diode",
            **{
                "life-test": {"failures": 4, "accept_number": 1},
                "burn-in": {"failures": 3, "accept_number": 1},
            }
        )
        result = assess_discrete_semiconductor_test_table(_spec(entries=rows))
        self.assertEqual(sorted(result["rejecting_groups"]), ["burn-in", "life-test"])

    def test_drifted_device_holds_an_otherwise_clean_matrix(self):
        result = assess_discrete_semiconductor_test_table(
            _spec(
                family="optocoupler",
                entries=_full_matrix("optocoupler"),
                devices=[{"current-transfer-ratio": (100.0, 60.0)}],
                drift_limits={"current-transfer-ratio": 20.0},
            )
        )
        self.assertEqual(result["drift_reject_count"], 1)
        self.assertFalse(result["accepted"])

    def test_clean_devices_leave_the_lot_accepted(self):
        result = assess_discrete_semiconductor_test_table(
            _spec(
                family="optocoupler",
                entries=_full_matrix("optocoupler"),
                devices=[{"current-transfer-ratio": (100.0, 95.0)}],
                drift_limits={"current-transfer-ratio": 20.0},
            )
        )
        self.assertEqual(result["drift_reject_count"], 0)
        self.assertTrue(result["accepted"])

    def test_marginal_row_is_an_advisory_not_a_finding(self):
        rows = _full_matrix("diode", **{"solderability": {"failures": 1, "accept_number": 1}})
        result = assess_discrete_semiconductor_test_table(_spec(entries=rows))
        self.assertTrue(result["accepted"])
        self.assertEqual(len(result["advisories"]), 1)

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["entries"]
        with self.assertRaises(ValueError):
            assess_discrete_semiconductor_test_table(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_discrete_semiconductor_test_table(["family"])

    def test_unknown_family_in_the_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_discrete_semiconductor_test_table(_spec(family="thyristor"))

    def test_devices_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            assess_discrete_semiconductor_test_table(_spec(devices={"forward-voltage": (1, 1)}))


if __name__ == "__main__":
    unittest.main()
