#!/usr/bin/env python3
"""Contract test for substrate integrity acceptance criteria (offline).

This is the gate 3 behaviour contract: every workflow step of the leaf
(drawing validation, threshold lookup, margin computation in both
directions of merit, per-indication disposition, cumulative totals and
the coupon verdict) is exercised here, including the refusals that stop a
coupon being graded on a limit nobody declared.
"""

import copy
import unittest

from e2008_substrate_integrity_pass_fail_criteria_logic import (
    ACCEPT,
    ACCEPT_ON_LIMIT,
    DIRECTIONS,
    INDICATION_KINDS,
    REJECT,
    SUBSTRATE_ACCEPT,
    SUBSTRATE_REJECT,
    SUBSTRATE_UNDETERMINED,
    UNDECLARED,
    assess_substrate_integrity,
    cumulative_check,
    disposition_indication,
    margin_fraction,
    threshold_for,
    validate_acd,
)

ACD = {
    "drawing_id": "ACD-PVA-SUB-001",
    "revision": "C",
    "thresholds": {
        "facesheet-crack": {"limit": 5.0, "units": "mm", "direction": "max"},
        "facesheet-core-disbond": {"limit": 25.0, "units": "mm2", "direction": "max"},
        "core-crush": {"limit": 0.4, "units": "mm", "direction": "max"},
        "residual-bond-strength": {"limit": 1.2, "units": "MPa", "direction": "min"},
    },
    "cumulative_thresholds": {
        "facesheet-core-disbond": {"limit": 60.0, "units": "mm2", "direction": "max"},
    },
}

DISBOND = {
    "indication_id": "I1",
    "kind": "facesheet-core-disbond",
    "value": 20.0,
    "units": "mm2",
}


def _acd(**overrides):
    drawing = copy.deepcopy(ACD)
    drawing.update(overrides)
    return drawing


def _indication(**overrides):
    indication = dict(DISBOND)
    indication.update(overrides)
    return indication


def _inspection(**overrides):
    inspection = {
        "coupon_id": "K1",
        "acd_revision": "C",
        "survey_complete": True,
        "indications": [_indication()],
    }
    inspection.update(overrides)
    return inspection


class DrawingValidationTests(unittest.TestCase):
    def test_reference_drawing_validates(self):
        checked = validate_acd(ACD)
        self.assertEqual(checked["revision"], "C")
        self.assertIn("facesheet-core-disbond", checked["thresholds"])

    def test_drawing_without_a_revision_rejected(self):
        broken = _acd()
        del broken["revision"]
        with self.assertRaises(ValueError):
            validate_acd(broken)

    def test_drawing_declaring_no_thresholds_rejected(self):
        with self.assertRaises(ValueError):
            validate_acd(_acd(thresholds={}))

    def test_threshold_for_an_unknown_kind_rejected(self):
        broken = _acd()
        broken["thresholds"]["paint-blister"] = {
            "limit": 1.0,
            "units": "mm",
            "direction": "max",
        }
        with self.assertRaises(ValueError):
            validate_acd(broken)

    def test_zero_limit_rejected(self):
        broken = _acd()
        broken["thresholds"]["core-crush"]["limit"] = 0.0
        with self.assertRaises(ValueError):
            validate_acd(broken)

    def test_unknown_direction_of_merit_rejected(self):
        broken = _acd()
        broken["thresholds"]["core-crush"]["direction"] = "around"
        with self.assertRaises(ValueError):
            validate_acd(broken)

    def test_cumulative_floor_rejected(self):
        broken = _acd()
        broken["cumulative_thresholds"]["facesheet-core-disbond"]["direction"] = "min"
        with self.assertRaises(ValueError):
            validate_acd(broken)

    def test_non_mapping_drawing_rejected(self):
        with self.assertRaises(ValueError):
            validate_acd("ACD-PVA-SUB-001 rev C")

    def test_both_directions_of_merit_are_declarable(self):
        declared = {
            entry["direction"] for entry in validate_acd(ACD)["thresholds"].values()
        }
        self.assertEqual(declared, set(DIRECTIONS))


class ThresholdLookupTests(unittest.TestCase):
    def test_declared_kind_returns_its_threshold(self):
        entry = threshold_for(ACD, "facesheet-crack")
        self.assertAlmostEqual(entry["limit"], 5.0, places=9)
        self.assertEqual(entry["direction"], "max")

    def test_undeclared_kind_returns_nothing_rather_than_a_default(self):
        self.assertIsNone(threshold_for(ACD, "insert-pullout"))

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            threshold_for(ACD, "paint-blister")


class MarginTests(unittest.TestCase):
    def test_ceiling_margin_is_a_fraction_of_the_limit(self):
        self.assertAlmostEqual(margin_fraction(20.0, 25.0, "max"), 0.2, places=9)

    def test_floor_margin_is_a_fraction_of_the_limit(self):
        self.assertAlmostEqual(margin_fraction(1.5, 1.2, "min"), 0.25, places=9)

    def test_value_on_a_ceiling_has_no_margin(self):
        self.assertAlmostEqual(margin_fraction(25.0, 25.0, "max"), 0.0, places=9)

    def test_value_on_a_floor_has_no_margin(self):
        self.assertAlmostEqual(margin_fraction(1.2, 1.2, "min"), 0.0, places=9)

    def test_value_past_a_ceiling_reports_a_negative_margin(self):
        self.assertAlmostEqual(margin_fraction(30.0, 25.0, "max"), -0.2, places=9)

    def test_non_positive_limit_rejected(self):
        with self.assertRaises(ValueError):
            margin_fraction(1.0, 0.0, "max")

    def test_non_numeric_value_rejected(self):
        with self.assertRaises(ValueError):
            margin_fraction("twenty", 25.0, "max")


class DispositionTests(unittest.TestCase):
    def test_indication_inside_its_ceiling_accepts(self):
        result = disposition_indication(_indication(), ACD)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertAlmostEqual(result["margin_fraction"], 0.2, places=9)

    def test_indication_past_its_ceiling_rejects(self):
        result = disposition_indication(_indication(value=30.0), ACD)
        self.assertEqual(result["disposition"], REJECT)

    def test_indication_exactly_on_its_ceiling_is_reported_on_limit(self):
        result = disposition_indication(_indication(value=25.0), ACD)
        self.assertEqual(result["disposition"], ACCEPT_ON_LIMIT)
        self.assertAlmostEqual(result["margin_fraction"], 0.0, places=9)

    def test_measurement_above_a_floor_accepts(self):
        result = disposition_indication(
            _indication(kind="residual-bond-strength", value=1.5, units="MPa"), ACD
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_measurement_below_a_floor_rejects_rather_than_passing(self):
        result = disposition_indication(
            _indication(kind="residual-bond-strength", value=0.9, units="MPa"), ACD
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_measurement_exactly_on_a_floor_is_reported_on_limit(self):
        result = disposition_indication(
            _indication(kind="residual-bond-strength", value=1.2, units="MPa"), ACD
        )
        self.assertEqual(result["disposition"], ACCEPT_ON_LIMIT)

    def test_kind_the_drawing_never_declared_is_undetermined_not_passed(self):
        result = disposition_indication(
            _indication(kind="insert-pullout", value=3.0, units="mm"), ACD
        )
        self.assertEqual(result["disposition"], UNDECLARED)
        self.assertIsNone(result["limit"])

    def test_units_disagreeing_with_the_drawing_rejected(self):
        with self.assertRaises(ValueError):
            disposition_indication(_indication(units="mm"), ACD)

    def test_negative_measurement_rejected(self):
        with self.assertRaises(ValueError):
            disposition_indication(_indication(value=-2.0), ACD)

    def test_missing_indication_identifier_rejected(self):
        indication = _indication()
        del indication["indication_id"]
        with self.assertRaises(ValueError):
            disposition_indication(indication, ACD)


class CumulativeTests(unittest.TestCase):
    def test_totals_past_the_ceiling_reject_though_each_passed(self):
        graded = [
            disposition_indication(_indication(indication_id="I1", value=20.0), ACD),
            disposition_indication(_indication(indication_id="I2", value=20.0), ACD),
            disposition_indication(_indication(indication_id="I3", value=25.0), ACD),
        ]
        results = cumulative_check(graded, ACD)
        self.assertEqual(results[0]["disposition"], REJECT)
        self.assertAlmostEqual(results[0]["total"], 65.0, places=9)

    def test_total_exactly_on_the_ceiling_is_reported_on_limit(self):
        graded = [
            disposition_indication(_indication(indication_id="I%d" % n, value=20.0), ACD)
            for n in range(1, 4)
        ]
        results = cumulative_check(graded, ACD)
        self.assertEqual(results[0]["disposition"], ACCEPT_ON_LIMIT)

    def test_kind_without_a_cumulative_ceiling_is_not_totalled(self):
        graded = [
            disposition_indication(
                _indication(indication_id="I1", kind="facesheet-crack", value=3.0, units="mm"),
                ACD,
            )
        ]
        self.assertEqual(cumulative_check(graded, ACD), [])

    def test_floor_kinds_are_never_totalled(self):
        drawing = _acd()
        drawing["cumulative_thresholds"]["residual-bond-strength"] = {
            "limit": 10.0,
            "units": "MPa",
            "direction": "max",
        }
        graded = [
            disposition_indication(
                _indication(
                    indication_id="I1",
                    kind="residual-bond-strength",
                    value=1.5,
                    units="MPa",
                ),
                drawing,
            )
        ]
        self.assertEqual(cumulative_check(graded, drawing), [])

    def test_non_list_input_rejected(self):
        with self.assertRaises(ValueError):
            cumulative_check({"kind": "core-crush"}, ACD)


class CouponVerdictTests(unittest.TestCase):
    def test_clear_coupon_accepts(self):
        result = assess_substrate_integrity(_inspection(), ACD)
        self.assertEqual(result["verdict"], SUBSTRATE_ACCEPT)

    def test_one_oversize_indication_rejects_the_coupon(self):
        result = assess_substrate_integrity(
            _inspection(indications=[_indication(value=40.0)]), ACD
        )
        self.assertEqual(result["verdict"], SUBSTRATE_REJECT)

    def test_undeclared_criteria_leave_the_coupon_undetermined(self):
        result = assess_substrate_integrity(
            _inspection(
                indications=[
                    _indication(),
                    _indication(
                        indication_id="I2",
                        kind="insert-pullout",
                        value=2.0,
                        units="mm",
                    ),
                ]
            ),
            ACD,
        )
        self.assertEqual(result["verdict"], SUBSTRATE_UNDETERMINED)
        self.assertEqual(result["undeclared_kinds"], ["insert-pullout"])

    def test_undeclared_criteria_outrank_a_rejection(self):
        result = assess_substrate_integrity(
            _inspection(
                indications=[
                    _indication(value=40.0),
                    _indication(
                        indication_id="I2",
                        kind="insert-pullout",
                        value=2.0,
                        units="mm",
                    ),
                ]
            ),
            ACD,
        )
        self.assertEqual(result["verdict"], SUBSTRATE_UNDETERMINED)

    def test_cumulative_ceiling_rejects_a_coupon_of_passing_indications(self):
        result = assess_substrate_integrity(
            _inspection(
                indications=[
                    _indication(indication_id="I1", value=22.0),
                    _indication(indication_id="I2", value=22.0),
                    _indication(indication_id="I3", value=22.0),
                ]
            ),
            ACD,
        )
        self.assertEqual(result["verdict"], SUBSTRATE_REJECT)
        self.assertTrue(any("cumulative" in note for note in result["findings"]))

    def test_incomplete_survey_leaves_the_coupon_undetermined(self):
        result = assess_substrate_integrity(_inspection(survey_complete=False), ACD)
        self.assertEqual(result["verdict"], SUBSTRATE_UNDETERMINED)

    def test_stale_drawing_revision_refused(self):
        with self.assertRaises(ValueError):
            assess_substrate_integrity(_inspection(acd_revision="D"), ACD)

    def test_empty_complete_survey_accepts_and_says_why(self):
        result = assess_substrate_integrity(_inspection(indications=[]), ACD)
        self.assertEqual(result["verdict"], SUBSTRATE_ACCEPT)
        self.assertTrue(any("no indications" in note for note in result["findings"]))

    def test_on_limit_indication_accepts_but_is_flagged(self):
        result = assess_substrate_integrity(
            _inspection(indications=[_indication(value=25.0)]), ACD
        )
        self.assertEqual(result["verdict"], SUBSTRATE_ACCEPT)
        self.assertTrue(any("no margin left" in note for note in result["findings"]))

    def test_duplicate_indication_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_substrate_integrity(
                _inspection(indications=[_indication(), _indication()]), ACD
            )

    def test_non_boolean_survey_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_substrate_integrity(_inspection(survey_complete="yes"), ACD)

    def test_every_declared_kind_is_a_known_indication_kind(self):
        for kind in validate_acd(ACD)["thresholds"]:
            self.assertIn(kind, INDICATION_KINDS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
