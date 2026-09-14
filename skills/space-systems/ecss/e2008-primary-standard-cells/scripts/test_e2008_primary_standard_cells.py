"""Contract tests for the clause 10.2.1 primary standard cell assessment.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused policy, a
standard citing no recognised calibration route, a certificate that had
lapsed by the test day, a multijunction article with a junction no
standard represents, and a level set further off its temperature
corrected target than the tolerance admits.
"""

import unittest
from datetime import date

from e2008_primary_standard_cells_logic import (
    ACCEPTED_TRACEABILITY_ROUTES,
    CALIBRATION_EXPIRED,
    DEFAULT_STANDARD_CELL_POLICY,
    JUNCTION_COVERAGE_INCOMPLETE,
    LEVEL_OUT_OF_TOLERANCE,
    LEVEL_SET,
    SINGLE_JUNCTION,
    TRACEABILITY_NOT_ESTABLISHED,
    assess_primary_standard_setting,
    calibration_age_days,
    calibration_in_date,
    junction_coverage,
    level_error_fraction,
    setting_record,
    standard_cells,
    temperature_corrected_target_current_a,
    traceability_established,
    validate_standard_cell,
    validate_standard_cell_policy,
)

REFERENCE_TEMPERATURE_C = 25.0
COEFFICIENT_PER_K = 0.0004
TEST_DATE = "2026-06-01"
CALIBRATION_DATE = "2026-03-01"

CALIBRATED_A = {
    "top-junction": 0.01650,
    "middle-junction": 0.01620,
    "bottom-junction": 0.02100,
}
REQUIRED_JUNCTIONS = ("top-junction", "middle-junction", "bottom-junction")


def _policy(**overrides):
    policy = dict(DEFAULT_STANDARD_CELL_POLICY)
    policy.update(overrides)
    return policy


def _cell(base, **overrides):
    key = base.split("-")[0]
    cell = {
        "id": "std-%s" % key,
        "junction": base,
        "calibration_reference": "CAL-2026-%s" % key,
        "traceability_route": "high-altitude-aircraft",
        "calibration_date": CALIBRATION_DATE,
        "calibrated_short_circuit_current_a": CALIBRATED_A[base],
        "reference_irradiance_w_m2": 1367.0,
        "reference_temperature_c": REFERENCE_TEMPERATURE_C,
        "temperature_coefficient_per_k": COEFFICIENT_PER_K,
    }
    cell.update(overrides)
    return cell


def _cells():
    return [_cell(junction) for junction in REQUIRED_JUNCTIONS]


def _settings(temperature_c=REFERENCE_TEMPERATURE_C, scale=1.0):
    records = []
    for junction in REQUIRED_JUNCTIONS:
        target = CALIBRATED_A[junction] * (
            1.0 + COEFFICIENT_PER_K * (temperature_c - REFERENCE_TEMPERATURE_C)
        )
        records.append(
            {
                "standard_id": "std-%s" % junction.split("-")[0],
                "measured_current_a": target * scale,
                "cell_temperature_c": temperature_c,
            }
        )
    return records


def _case(**overrides):
    case = {
        "standard_cells": _cells(),
        "required_junctions": list(REQUIRED_JUNCTIONS),
        "settings": _settings(),
        "test_date": TEST_DATE,
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_standard_cell_policy(DEFAULT_STANDARD_CELL_POLICY),
            DEFAULT_STANDARD_CELL_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_standard_cell_policy("max_level_error_fraction")

    def test_a_whole_unit_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_standard_cell_policy(_policy(max_level_error_fraction=1.2))

    def test_a_zero_day_validity_rejected(self):
        with self.assertRaises(ValueError):
            validate_standard_cell_policy(_policy(max_calibration_age_days=0))

    def test_a_boolean_validity_rejected(self):
        with self.assertRaises(ValueError):
            validate_standard_cell_policy(_policy(max_calibration_age_days=True))

    def test_a_marginal_window_wider_than_the_validity_rejected(self):
        with self.assertRaises(ValueError):
            validate_standard_cell_policy(_policy(marginal_validity_days=900))

    def test_a_marginal_error_band_wider_than_the_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_standard_cell_policy(
                _policy(marginal_level_error_fraction=0.05)
            )


class StandardCellRecordTests(unittest.TestCase):
    def test_a_standard_is_read_back(self):
        checked = validate_standard_cell(_cell("top-junction"))
        self.assertEqual(checked["id"], "std-top")
        self.assertEqual(checked["junction"], "top-junction")
        self.assertEqual(checked["calibration_date"], date(2026, 3, 1))

    def test_non_mapping_standard_rejected(self):
        with self.assertRaises(ValueError):
            validate_standard_cell("std-top")

    def test_a_blank_standard_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_standard_cell(_cell("top-junction", id="  "))

    def test_a_standard_naming_no_junction_rejected(self):
        with self.assertRaises(ValueError):
            validate_standard_cell(_cell("top-junction", junction="   "))

    def test_a_malformed_calibration_date_rejected(self):
        with self.assertRaises(ValueError):
            validate_standard_cell(
                _cell("top-junction", calibration_date="01-03-2026")
            )

    def test_a_negative_calibrated_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_standard_cell(
                _cell("top-junction", calibrated_short_circuit_current_a=-0.0165)
            )

    def test_a_single_junction_standard_is_a_legitimate_record(self):
        checked = validate_standard_cell(
            _cell("top-junction", junction=SINGLE_JUNCTION)
        )
        self.assertEqual(checked["junction"], SINGLE_JUNCTION)

    def test_a_duplicate_standard_id_rejected(self):
        cells = _cells()
        cells[2]["id"] = cells[0]["id"]
        with self.assertRaises(ValueError):
            standard_cells(cells)

    def test_an_empty_standard_set_rejected(self):
        with self.assertRaises(ValueError):
            standard_cells([])


class TraceabilityTests(unittest.TestCase):
    def test_a_recognised_route_is_traceable(self):
        cells = standard_cells(_cells())
        self.assertTrue(traceability_established(cells[0]))

    def test_every_accepted_route_is_traceable(self):
        for route in ACCEPTED_TRACEABILITY_ROUTES:
            cell = standard_cells([_cell("top-junction", traceability_route=route)])[0]
            self.assertTrue(traceability_established(cell))

    def test_a_datasheet_route_is_not_traceable(self):
        cell = standard_cells(
            [_cell("top-junction", traceability_route="vendor-datasheet")]
        )[0]
        self.assertFalse(traceability_established(cell))

    def test_a_blank_certificate_reference_is_not_traceable(self):
        cell = standard_cells(
            [_cell("top-junction", calibration_reference="   ")]
        )[0]
        self.assertFalse(traceability_established(cell))


class CalibrationDateTests(unittest.TestCase):
    def test_the_age_is_counted_to_the_test_day(self):
        cell = standard_cells(_cells())[0]
        self.assertEqual(calibration_age_days(cell, TEST_DATE), 92)

    def test_a_calibration_dated_after_the_test_rejected(self):
        cell = standard_cells(_cells())[0]
        with self.assertRaises(ValueError):
            calibration_age_days(cell, "2026-01-01")

    def test_a_fresh_certificate_is_in_date(self):
        cell = standard_cells(_cells())[0]
        self.assertTrue(calibration_in_date(cell, TEST_DATE))

    def test_a_certificate_exactly_on_its_last_day_is_in_date(self):
        cell = standard_cells(_cells())[0]
        self.assertTrue(
            calibration_in_date(cell, TEST_DATE, _policy(max_calibration_age_days=92))
        )

    def test_a_certificate_one_day_past_is_out_of_date(self):
        cell = standard_cells(_cells())[0]
        self.assertFalse(
            calibration_in_date(cell, TEST_DATE, _policy(max_calibration_age_days=91))
        )


class TemperatureCorrectionTests(unittest.TestCase):
    def test_at_the_reference_temperature_the_target_is_the_certificate_value(self):
        cell = standard_cells(_cells())[0]
        self.assertAlmostEqual(
            temperature_corrected_target_current_a(cell, REFERENCE_TEMPERATURE_C),
            CALIBRATED_A["top-junction"],
            places=12,
        )

    def test_a_warmer_cell_raises_the_target(self):
        cell = standard_cells(_cells())[0]
        warm = temperature_corrected_target_current_a(cell, 45.0)
        self.assertAlmostEqual(
            warm,
            CALIBRATED_A["top-junction"] * (1.0 + COEFFICIENT_PER_K * 20.0),
            places=12,
        )

    def test_a_colder_cell_lowers_the_target(self):
        cell = standard_cells(_cells())[0]
        cold = temperature_corrected_target_current_a(cell, 5.0)
        self.assertLess(cold, CALIBRATED_A["top-junction"])

    def test_a_coefficient_that_zeroes_the_target_rejected(self):
        cell = standard_cells(
            [_cell("top-junction", temperature_coefficient_per_k=-0.5)]
        )[0]
        with self.assertRaises(ValueError):
            temperature_corrected_target_current_a(cell, 45.0)

    def test_a_level_on_target_carries_no_error(self):
        self.assertAlmostEqual(
            level_error_fraction(0.0165, 0.0165), 0.0, places=12
        )

    def test_a_level_set_low_carries_a_negative_error(self):
        self.assertAlmostEqual(
            level_error_fraction(0.099, 0.1), -0.01, places=9
        )

    def test_a_zero_target_rejected_rather_than_divided_by(self):
        with self.assertRaises(ValueError):
            level_error_fraction(0.0165, 0.0)


class JunctionCoverageTests(unittest.TestCase):
    def test_a_full_set_covers_every_junction(self):
        coverage = junction_coverage(standard_cells(_cells()), REQUIRED_JUNCTIONS)
        self.assertEqual(coverage["missing"], ())
        self.assertEqual(len(coverage["covered"]), 3)

    def test_a_single_standard_leaves_two_junctions_unset(self):
        cells = standard_cells([_cell("top-junction")])
        coverage = junction_coverage(cells, REQUIRED_JUNCTIONS)
        self.assertEqual(
            coverage["missing"], ("middle-junction", "bottom-junction")
        )

    def test_a_standard_for_no_required_junction_is_reported_unused(self):
        cells = standard_cells(_cells() + [_cell("top-junction", id="std-spare", junction="spare-junction")])
        coverage = junction_coverage(cells, REQUIRED_JUNCTIONS)
        self.assertEqual(coverage["unused"], ("spare-junction",))

    def test_an_empty_required_set_rejected(self):
        with self.assertRaises(ValueError):
            junction_coverage(standard_cells(_cells()), [])

    def test_a_junction_required_twice_rejected(self):
        with self.assertRaises(ValueError):
            junction_coverage(
                standard_cells(_cells()), ["top-junction", "top-junction"]
            )


class SettingRecordTests(unittest.TestCase):
    def test_an_on_target_setting_has_no_error(self):
        cells = standard_cells(_cells())
        record = setting_record(_settings()[0], cells)
        self.assertAlmostEqual(record["level_error_fraction"], 0.0, places=12)

    def test_the_target_follows_the_cell_temperature(self):
        cells = standard_cells(_cells())
        record = setting_record(_settings(temperature_c=45.0)[0], cells)
        self.assertGreater(record["target_current_a"], CALIBRATED_A["top-junction"])
        self.assertAlmostEqual(record["level_error_fraction"], 0.0, places=12)

    def test_setting_against_the_bare_certificate_value_leaves_the_offset(self):
        cells = standard_cells(_cells())
        record = setting_record(
            {
                "standard_id": "std-top",
                "measured_current_a": CALIBRATED_A["top-junction"],
                "cell_temperature_c": 45.0,
            },
            cells,
        )
        self.assertLess(record["level_error_fraction"], 0.0)

    def test_a_setting_citing_an_unoffered_standard_rejected(self):
        cells = standard_cells(_cells())
        with self.assertRaises(ValueError):
            setting_record(
                {
                    "standard_id": "std-absent",
                    "measured_current_a": 0.0165,
                    "cell_temperature_c": 25.0,
                },
                cells,
            )

    def test_a_negative_measured_current_rejected(self):
        cells = standard_cells(_cells())
        setting = _settings()[0]
        setting["measured_current_a"] = -0.0165
        with self.assertRaises(ValueError):
            setting_record(setting, cells)


class AssessmentTests(unittest.TestCase):
    def test_a_covered_in_date_on_target_setting_is_set(self):
        result = assess_primary_standard_setting(_case())
        self.assertEqual(result["verdict"], LEVEL_SET)
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["covered_junctions"]), 3)

    def test_an_untraceable_standard_closes_the_assessment(self):
        cells = _cells()
        cells[1]["traceability_route"] = "vendor-datasheet"
        result = assess_primary_standard_setting(_case(standard_cells=cells))
        self.assertEqual(result["verdict"], TRACEABILITY_NOT_ESTABLISHED)
        self.assertIn("std-middle", result["findings"][0])

    def test_every_untraceable_standard_is_named_not_only_the_first(self):
        cells = _cells()
        cells[0]["traceability_route"] = "vendor-datasheet"
        cells[1]["calibration_reference"] = "  "
        result = assess_primary_standard_setting(_case(standard_cells=cells))
        self.assertEqual(len(result["findings"]), 2)

    def test_a_lapsed_certificate_closes_the_assessment(self):
        cells = _cells()
        cells[2]["calibration_date"] = "2023-01-05"
        result = assess_primary_standard_setting(_case(standard_cells=cells))
        self.assertEqual(result["verdict"], CALIBRATION_EXPIRED)

    def test_a_certificate_about_to_lapse_raises_an_advisory(self):
        result = assess_primary_standard_setting(
            _case(), _policy(max_calibration_age_days=120)
        )
        self.assertEqual(result["verdict"], LEVEL_SET)
        self.assertEqual(len(result["advisories"]), 3)

    def test_a_missing_junction_closes_the_assessment(self):
        cells = _cells()[:2]
        result = assess_primary_standard_setting(
            _case(standard_cells=cells, settings=_settings()[:2])
        )
        self.assertEqual(result["verdict"], JUNCTION_COVERAGE_INCOMPLETE)
        self.assertEqual(result["missing_junctions"], ("bottom-junction",))

    def test_a_single_standard_does_not_set_a_triple_junction_article(self):
        result = assess_primary_standard_setting(
            _case(standard_cells=[_cell("top-junction")], settings=_settings()[:1])
        )
        self.assertEqual(result["verdict"], JUNCTION_COVERAGE_INCOMPLETE)
        self.assertEqual(len(result["missing_junctions"]), 2)

    def test_a_level_beyond_the_tolerance_is_out_of_tolerance(self):
        result = assess_primary_standard_setting(_case(settings=_settings(scale=1.04)))
        self.assertEqual(result["verdict"], LEVEL_OUT_OF_TOLERANCE)
        self.assertEqual(len(result["findings"]), 3)

    def test_a_level_exactly_on_the_tolerance_is_admitted(self):
        result = assess_primary_standard_setting(_case(settings=_settings(scale=1.01)))
        self.assertEqual(result["verdict"], LEVEL_SET)
        self.assertAlmostEqual(
            result["worst_level_error_fraction"], 0.01, places=9
        )

    def test_a_residual_error_inside_tolerance_raises_an_advisory(self):
        result = assess_primary_standard_setting(_case(settings=_settings(scale=1.005)))
        self.assertEqual(result["verdict"], LEVEL_SET)
        self.assertTrue(
            any("residual error" in advisory for advisory in result["advisories"])
        )

    def test_an_on_target_setting_raises_no_advisory(self):
        result = assess_primary_standard_setting(_case())
        self.assertEqual(result["advisories"], [])

    def test_the_worst_setting_travels_with_the_verdict(self):
        settings = _settings()
        settings[1]["measured_current_a"] *= 1.006
        result = assess_primary_standard_setting(_case(settings=settings))
        self.assertEqual(result["worst_setting_standard_id"], "std-middle")

    def test_a_missing_required_junction_list_rejected(self):
        case = _case()
        del case["required_junctions"]
        with self.assertRaises(ValueError):
            assess_primary_standard_setting(case)

    def test_a_missing_setting_record_rejected(self):
        case = _case()
        del case["settings"]
        with self.assertRaises(ValueError):
            assess_primary_standard_setting(case)

    def test_a_missing_test_date_rejected(self):
        case = _case()
        del case["test_date"]
        with self.assertRaises(ValueError):
            assess_primary_standard_setting(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_primary_standard_setting(["standard_cells"])


if __name__ == "__main__":
    unittest.main()
