"""Contract tests for the clause 12.6.11.2.3 post-exposure pass criteria.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused sentencing
policy, an unreferenced or self-contradictory limit set, a device carrying
no post-anneal reading, a ceiling or floor breach, and a lot losing more
devices than the declared allowance admits.
"""

import unittest

from e2008_electron_irradiation_pass_criteria_logic import (
    BLOCKING_VOLTAGE,
    DEFAULT_PASS_POLICY,
    DRAWING_REQUIREMENT_NOT_ESTABLISHED,
    FORWARD_VOLTAGE,
    LOT_MEETS_DRAWING_LIMITS,
    LOT_REJECT_FRACTION_EXCEEDED,
    POST_ANNEAL_READING_NOT_EVIDENCED,
    REVERSE_LEAKAGE,
    anneal_recovery_fraction,
    assess_post_exposure_pass_criteria,
    ceiling_margin_fraction,
    device_verdict,
    device_verdicts,
    floor_margin_fraction,
    lot_reject_fraction,
    lot_within_reject_allowance,
    marginal_device_advisories,
    unsentenced_devices,
    validate_device_record,
    validate_drawing_limits,
    validate_pass_policy,
    validate_reading,
    weakest_device,
)

MAX_FORWARD_V = 1.000
MAX_LEAKAGE_A = 2.0e-6
MIN_BLOCKING_V = 120.0


def _policy(**overrides):
    policy = dict(DEFAULT_PASS_POLICY)
    policy.update(overrides)
    return policy


def _limits(**overrides):
    limits = {
        "drawing_reference": "SCD-4471 issue C",
        "max_forward_voltage_v": MAX_FORWARD_V,
        "max_reverse_leakage_a": MAX_LEAKAGE_A,
        "min_blocking_voltage_v": MIN_BLOCKING_V,
        "reference_junction_temperature_c": 25.0,
    }
    limits.update(overrides)
    return limits


def _reading(forward=0.880, leakage=1.1e-6, blocking=142.0):
    return {
        "forward_voltage_v": forward,
        "reverse_leakage_a": leakage,
        "blocking_voltage_v": blocking,
    }


def _devices():
    return [
        {
            "id": "bd-01",
            "pre_irradiation": _reading(0.820, 4.0e-7, 155.0),
            "post_irradiation": _reading(0.940, 1.6e-6, 138.0),
            "post_anneal": _reading(0.868, 1.0e-6, 146.0),
        },
        {
            "id": "bd-02",
            "pre_irradiation": _reading(0.826, 4.2e-7, 154.0),
            "post_irradiation": _reading(0.952, 1.7e-6, 136.0),
            "post_anneal": _reading(0.884, 1.2e-6, 143.0),
        },
        {
            "id": "bd-03",
            "post_anneal": _reading(0.871, 9.0e-7, 149.0),
        },
    ]


def _case(**overrides):
    case = {"drawing_limits": _limits(), "devices": _devices()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_pass_policy(DEFAULT_PASS_POLICY), DEFAULT_PASS_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_pass_policy("max_reject_fraction")

    def test_reject_allowance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_pass_policy(_policy(max_reject_fraction=1.2))

    def test_negative_reject_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_pass_policy(_policy(max_reject_fraction=-0.05))

    def test_a_zero_reject_allowance_is_a_legitimate_policy(self):
        self.assertIsNotNone(validate_pass_policy(_policy(max_reject_fraction=0.0)))

    def test_marginal_band_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_pass_policy(_policy(marginal_band_fraction=1.3))


class DrawingLimitTests(unittest.TestCase):
    def test_a_referenced_limit_set_validates(self):
        checked = validate_drawing_limits(_limits())
        self.assertEqual(checked["drawing_reference"], "SCD-4471 issue C")
        self.assertAlmostEqual(
            checked["max_forward_voltage_v"], MAX_FORWARD_V, places=12
        )

    def test_non_mapping_limits_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing_limits("SCD-4471")

    def test_a_non_string_drawing_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing_limits(_limits(drawing_reference=4471))

    def test_a_negative_leakage_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing_limits(_limits(max_reverse_leakage_a=-1e-6))

    def test_a_forward_ceiling_above_the_blocking_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing_limits(
                _limits(max_forward_voltage_v=200.0, min_blocking_voltage_v=120.0)
            )

    def test_a_blank_drawing_reference_survives_validation(self):
        checked = validate_drawing_limits(_limits(drawing_reference="   "))
        self.assertEqual(checked["drawing_reference"], "")

    def test_a_sub_zero_reference_junction_temperature_is_admitted(self):
        checked = validate_drawing_limits(
            _limits(reference_junction_temperature_c=-40.0)
        )
        self.assertAlmostEqual(
            checked["reference_junction_temperature_c"], -40.0, places=12
        )


class ReadingTests(unittest.TestCase):
    def test_a_reading_is_read_back(self):
        reading = validate_reading("post_anneal", _reading())
        self.assertAlmostEqual(reading["forward_voltage_v"], 0.880, places=12)

    def test_a_non_mapping_reading_rejected(self):
        with self.assertRaises(ValueError):
            validate_reading("post_anneal", 0.88)

    def test_a_boolean_characteristic_rejected(self):
        bad = _reading()
        bad["blocking_voltage_v"] = True
        with self.assertRaises(ValueError):
            validate_reading("post_anneal", bad)

    def test_a_missing_characteristic_rejected(self):
        bad = _reading()
        del bad["reverse_leakage_a"]
        with self.assertRaises(ValueError):
            validate_reading("post_anneal", bad)


class DeviceRecordTests(unittest.TestCase):
    def test_a_full_record_is_read_back(self):
        record = validate_device_record(_devices()[0])
        self.assertEqual(record["id"], "bd-01")
        self.assertIsNotNone(record["post_anneal"])
        self.assertIsNotNone(record["post_irradiation"])

    def test_a_record_with_only_a_post_anneal_reading_is_admitted(self):
        record = validate_device_record(_devices()[2])
        self.assertIsNone(record["pre_irradiation"])
        self.assertIsNotNone(record["post_anneal"])

    def test_a_blank_device_id_rejected(self):
        device = _devices()[0]
        device["id"] = "  "
        with self.assertRaises(ValueError):
            validate_device_record(device)

    def test_a_missing_post_anneal_reading_is_not_an_error_here(self):
        device = _devices()[0]
        del device["post_anneal"]
        record = validate_device_record(device)
        self.assertIsNone(record["post_anneal"])


class MarginTests(unittest.TestCase):
    def test_ceiling_margin_is_the_headroom_below_the_limit(self):
        self.assertAlmostEqual(ceiling_margin_fraction(0.9, 1.0), 0.1, places=9)

    def test_a_value_on_its_ceiling_has_zero_margin(self):
        self.assertAlmostEqual(
            ceiling_margin_fraction(MAX_FORWARD_V, MAX_FORWARD_V), 0.0, places=12
        )

    def test_a_value_over_its_ceiling_has_a_negative_margin(self):
        self.assertLess(ceiling_margin_fraction(1.2, 1.0), 0.0)

    def test_floor_margin_is_the_headroom_above_the_limit(self):
        self.assertAlmostEqual(floor_margin_fraction(132.0, 120.0), 0.1, places=9)

    def test_a_value_on_its_floor_has_zero_margin(self):
        self.assertAlmostEqual(
            floor_margin_fraction(MIN_BLOCKING_V, MIN_BLOCKING_V), 0.0, places=12
        )

    def test_a_zero_limit_rejected_rather_than_divided_by(self):
        with self.assertRaises(ValueError):
            ceiling_margin_fraction(0.9, 0.0)


class RecoveryTests(unittest.TestCase):
    def test_a_full_recovery_is_one(self):
        self.assertAlmostEqual(
            anneal_recovery_fraction(0.820, 0.940, 0.820), 1.0, places=9
        )

    def test_no_recovery_is_zero(self):
        self.assertAlmostEqual(
            anneal_recovery_fraction(0.820, 0.940, 0.940), 0.0, places=12
        )

    def test_a_half_recovery_is_a_half(self):
        self.assertAlmostEqual(
            anneal_recovery_fraction(0.820, 0.940, 0.880), 0.5, places=9
        )

    def test_continued_drift_through_the_soak_is_negative(self):
        self.assertLess(anneal_recovery_fraction(0.820, 0.940, 0.980), 0.0)

    def test_an_unmoved_characteristic_rejected(self):
        with self.assertRaises(ValueError):
            anneal_recovery_fraction(0.880, 0.880, 0.880)


class DeviceVerdictTests(unittest.TestCase):
    def test_a_comfortable_device_is_accepted(self):
        verdict = device_verdict(_devices()[0], _limits())
        self.assertTrue(verdict["sentenced"])
        self.assertTrue(verdict["accepted"])
        self.assertEqual(verdict["breaches"], ())

    def test_a_device_exactly_on_every_limit_is_accepted(self):
        verdict = device_verdict(
            {
                "id": "bd-tie",
                "post_anneal": _reading(MAX_FORWARD_V, MAX_LEAKAGE_A, MIN_BLOCKING_V),
            },
            _limits(),
        )
        self.assertTrue(verdict["accepted"])
        self.assertAlmostEqual(verdict["limiting_margin_fraction"], 0.0, places=12)

    def test_a_leakage_breach_alone_is_named(self):
        verdict = device_verdict(
            {"id": "bd-04", "post_anneal": _reading(0.880, 6.0e-6, 142.0)},
            _limits(),
        )
        self.assertFalse(verdict["accepted"])
        self.assertEqual(verdict["breaches"], (REVERSE_LEAKAGE,))

    def test_every_breach_is_named_not_only_the_first(self):
        verdict = device_verdict(
            {"id": "bd-05", "post_anneal": _reading(1.400, 9.0e-6, 60.0)},
            _limits(),
        )
        self.assertEqual(
            verdict["breaches"],
            (FORWARD_VOLTAGE, REVERSE_LEAKAGE, BLOCKING_VOLTAGE),
        )

    def test_a_device_with_no_post_anneal_reading_is_left_unsentenced(self):
        verdict = device_verdict({"id": "bd-06"}, _limits())
        self.assertFalse(verdict["sentenced"])
        self.assertFalse(verdict["accepted"])
        self.assertIsNone(verdict["limiting_margin_fraction"])

    def test_the_pre_anneal_reading_alone_does_not_sentence(self):
        verdict = device_verdict(
            {"id": "bd-07", "post_irradiation": _reading(1.400, 9.0e-6, 60.0)},
            _limits(),
        )
        self.assertFalse(verdict["sentenced"])
        self.assertEqual(verdict["breaches"], ())

    def test_the_recovery_figure_travels_with_the_verdict(self):
        verdict = device_verdict(_devices()[0], _limits())
        self.assertAlmostEqual(
            verdict["forward_recovery_fraction"], (0.940 - 0.868) / (0.940 - 0.820),
            places=9,
        )

    def test_a_device_without_a_baseline_carries_no_recovery_figure(self):
        verdict = device_verdict(_devices()[2], _limits())
        self.assertIsNone(verdict["forward_recovery_fraction"])

    def test_the_limiting_margin_is_the_smallest_of_the_three(self):
        verdict = device_verdict(_devices()[1], _limits())
        self.assertAlmostEqual(
            verdict["limiting_margin_fraction"],
            min(verdict["margins"].values()),
            places=12,
        )

    def test_a_duplicate_device_id_rejected(self):
        devices = _devices()
        devices[2]["id"] = "bd-01"
        with self.assertRaises(ValueError):
            device_verdicts(devices, _limits())

    def test_an_empty_exposed_population_rejected(self):
        with self.assertRaises(ValueError):
            device_verdicts([], _limits())


class LotTests(unittest.TestCase):
    def test_a_clean_lot_rejects_nothing(self):
        verdicts = device_verdicts(_devices(), _limits())
        self.assertAlmostEqual(lot_reject_fraction(verdicts), 0.0, places=12)

    def test_one_breaching_device_in_four_is_a_quarter(self):
        devices = _devices()
        devices.append(
            {"id": "bd-08", "post_anneal": _reading(1.400, 9.0e-6, 60.0)}
        )
        verdicts = device_verdicts(devices, _limits())
        self.assertAlmostEqual(lot_reject_fraction(verdicts), 0.25, places=12)

    def test_a_lot_exactly_on_the_allowance_is_admitted(self):
        devices = _devices()
        devices.append(
            {"id": "bd-08", "post_anneal": _reading(1.400, 9.0e-6, 60.0)}
        )
        verdicts = device_verdicts(devices, _limits())
        self.assertTrue(
            lot_within_reject_allowance(verdicts, _policy(max_reject_fraction=0.25))
        )

    def test_an_unsentenced_device_is_named(self):
        devices = _devices()
        del devices[1]["post_anneal"]
        verdicts = device_verdicts(devices, _limits())
        self.assertEqual(unsentenced_devices(verdicts), ("bd-02",))

    def test_a_lot_with_no_sentenced_device_has_no_reject_share(self):
        verdicts = device_verdicts([{"id": "bd-09"}], _limits())
        with self.assertRaises(ValueError):
            lot_reject_fraction(verdicts)

    def test_the_weakest_device_is_the_smallest_limiting_margin(self):
        verdicts = device_verdicts(_devices(), _limits())
        self.assertEqual(weakest_device(verdicts)["id"], "bd-02")

    def test_an_empty_verdict_set_rejected(self):
        with self.assertRaises(ValueError):
            weakest_device([])

    def test_a_device_just_inside_a_limit_raises_an_advisory(self):
        verdicts = device_verdicts(
            [
                {
                    "id": "bd-10",
                    "post_anneal": _reading(
                        MAX_FORWARD_V * 0.995, MAX_LEAKAGE_A * 0.5, MIN_BLOCKING_V * 1.4
                    ),
                }
            ],
            _limits(),
        )
        advisories = marginal_device_advisories(verdicts)
        self.assertEqual(len(advisories), 1)
        self.assertIn("bd-10", advisories[0])

    def test_a_comfortable_lot_raises_no_advisory(self):
        verdicts = device_verdicts(_devices(), _limits())
        self.assertEqual(marginal_device_advisories(verdicts), ())


class AssessmentTests(unittest.TestCase):
    def test_a_conforming_lot_meets_the_drawing_limits(self):
        result = assess_post_exposure_pass_criteria(_case())
        self.assertEqual(result["verdict"], LOT_MEETS_DRAWING_LIMITS)
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["accepted_devices"]), 3)

    def test_a_missing_drawing_record_closes_the_assessment(self):
        case = _case()
        del case["drawing_limits"]
        result = assess_post_exposure_pass_criteria(case)
        self.assertEqual(result["verdict"], DRAWING_REQUIREMENT_NOT_ESTABLISHED)
        self.assertTrue(result["findings"])

    def test_a_blank_drawing_reference_closes_the_assessment(self):
        result = assess_post_exposure_pass_criteria(
            _case(drawing_limits=_limits(drawing_reference="  "))
        )
        self.assertEqual(result["verdict"], DRAWING_REQUIREMENT_NOT_ESTABLISHED)

    def test_a_missing_post_anneal_reading_closes_the_assessment(self):
        devices = _devices()
        del devices[0]["post_anneal"]
        result = assess_post_exposure_pass_criteria(_case(devices=devices))
        self.assertEqual(result["verdict"], POST_ANNEAL_READING_NOT_EVIDENCED)
        self.assertIn("bd-01", result["unsentenced_devices"])

    def test_too_many_breaching_devices_exceed_the_lot_allowance(self):
        devices = _devices()
        devices[0]["post_anneal"] = _reading(1.400, 9.0e-6, 60.0)
        result = assess_post_exposure_pass_criteria(_case(devices=devices))
        self.assertEqual(result["verdict"], LOT_REJECT_FRACTION_EXCEEDED)
        self.assertIn("bd-01", result["rejected_devices"])

    def test_every_breaching_device_is_named(self):
        devices = _devices()
        devices[0]["post_anneal"] = _reading(1.400, 9.0e-6, 60.0)
        devices[1]["post_anneal"] = _reading(1.300, 8.0e-6, 70.0)
        result = assess_post_exposure_pass_criteria(_case(devices=devices))
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_the_weakest_device_travels_with_the_verdict(self):
        result = assess_post_exposure_pass_criteria(_case())
        self.assertEqual(result["weakest_device_id"], "bd-02")
        self.assertGreater(result["weakest_device_margin_fraction"], 0.0)

    def test_advisories_do_not_move_the_verdict(self):
        devices = [
            {
                "id": "bd-11",
                "post_anneal": _reading(
                    MAX_FORWARD_V * 0.996, MAX_LEAKAGE_A * 0.4, MIN_BLOCKING_V * 1.5
                ),
            }
        ]
        result = assess_post_exposure_pass_criteria(_case(devices=devices))
        self.assertEqual(result["verdict"], LOT_MEETS_DRAWING_LIMITS)
        self.assertEqual(len(result["advisories"]), 1)

    def test_the_lot_reject_fraction_is_reported(self):
        result = assess_post_exposure_pass_criteria(_case())
        self.assertAlmostEqual(result["lot_reject_fraction"], 0.0, places=12)

    def test_a_missing_device_record_rejected(self):
        case = _case()
        del case["devices"]
        with self.assertRaises(ValueError):
            assess_post_exposure_pass_criteria(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_post_exposure_pass_criteria(["drawing_limits"])


if __name__ == "__main__":
    unittest.main()
