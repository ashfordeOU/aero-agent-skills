"""Contract tests for the clause 9.6.9 diode contact surface finish test."""

import unittest

from e2008_diode_surface_finish_test_logic import (
    ACCEPT,
    ANODE,
    BLISTER,
    CATHODE,
    DEFAULT_SURFACE_FINISH_CRITERIA,
    NODULE,
    NOT_ESTABLISHED,
    OXIDATION,
    PITTING,
    REFER_FOR_REVIEW,
    REJECT,
    RESIDUE,
    assess_contact_finish,
    assess_diode_surface_finish,
    categorize_finish_anomaly,
    categorize_roughness,
    examination_is_adequate,
    examination_shortfalls,
    total_anomaly_coverage,
    validate_finish_anomaly,
    validate_finish_contact,
    validate_finish_examination,
    validate_surface_finish_criteria,
    worst_disposition,
)


def _criteria(**overrides):
    criteria = dict(DEFAULT_SURFACE_FINISH_CRITERIA)
    criteria.update(overrides)
    return criteria


def _examination(**overrides):
    examination = {
        "magnification_x": 20.0,
        "examined_fraction": 1.0,
        "roughness_ra_um": 0.8,
    }
    examination.update(overrides)
    return examination


def _pit(depth_fraction=0.1, coverage_fraction=0.01):
    return {
        "kind": PITTING,
        "depth_fraction": depth_fraction,
        "coverage_fraction": coverage_fraction,
    }


def _nodule(depth_fraction=0.2, coverage_fraction=0.01):
    return {
        "kind": NODULE,
        "depth_fraction": depth_fraction,
        "coverage_fraction": coverage_fraction,
    }


def _oxidation(coverage_fraction=0.05):
    return {"kind": OXIDATION, "coverage_fraction": coverage_fraction}


def _residue(coverage_fraction=0.01):
    return {"kind": RESIDUE, "coverage_fraction": coverage_fraction}


def _blister(coverage_fraction=0.0001):
    return {"kind": BLISTER, "coverage_fraction": coverage_fraction}


def _anode(**overrides):
    contact = {
        "id": "anode-land",
        "polarity": ANODE,
        "examination": _examination(),
        "anomalies": [],
    }
    contact.update(overrides)
    return contact


def _cathode(**overrides):
    contact = {
        "id": "cathode-land",
        "polarity": CATHODE,
        "examination": _examination(),
        "anomalies": [],
    }
    contact.update(overrides)
    return contact


def _case(**overrides):
    case = {"id": "diode-01", "contacts": [_anode(), _cathode()]}
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class CriteriaTests(unittest.TestCase):
    def test_the_default_criteria_validate(self):
        self.assertIs(
            validate_surface_finish_criteria(DEFAULT_SURFACE_FINISH_CRITERIA),
            DEFAULT_SURFACE_FINISH_CRITERIA,
        )

    def test_a_non_mapping_criteria_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface_finish_criteria("bright and even")

    def test_two_roughness_ceilings_on_top_of_each_other_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface_finish_criteria(
                _criteria(max_roughness_ra_um=1.6, max_weldable_roughness_ra_um=1.6)
            )

    def test_a_weldable_ceiling_below_the_working_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface_finish_criteria(
                _criteria(max_weldable_roughness_ra_um=1.0)
            )

    def test_a_coverage_allowance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface_finish_criteria(
                _criteria(max_oxidation_coverage_fraction=1.3)
            )

    def test_a_zero_magnification_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface_finish_criteria(_criteria(min_magnification_x=0.0))

    def test_a_missing_allowance_rejected(self):
        criteria = _criteria()
        del criteria["max_residue_coverage_fraction"]
        with self.assertRaises(ValueError):
            validate_surface_finish_criteria(criteria)


class ExaminationTests(unittest.TestCase):
    def test_an_examination_normalises(self):
        record = validate_finish_examination(_examination())
        self.assertAlmostEqual(record["magnification_x"], 20.0, places=12)
        self.assertAlmostEqual(record["examined_fraction"], 1.0, places=12)

    def test_a_non_mapping_examination_rejected(self):
        with self.assertRaises(ValueError):
            validate_finish_examination(None)

    def test_a_zero_magnification_rejected(self):
        with self.assertRaises(ValueError):
            validate_finish_examination(_examination(magnification_x=0.0))

    def test_an_examined_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_finish_examination(_examination(examined_fraction=1.2))

    def test_a_zero_roughness_rejected(self):
        with self.assertRaises(ValueError):
            validate_finish_examination(_examination(roughness_ra_um=0.0))

    def test_a_full_examination_carries_no_shortfall(self):
        self.assertEqual(examination_shortfalls(_examination()), ())
        self.assertTrue(examination_is_adequate(_examination()))

    def test_looking_below_the_magnification_floor_is_a_shortfall(self):
        shortfalls = examination_shortfalls(_examination(magnification_x=4.0))
        self.assertEqual(len(shortfalls), 1)
        self.assertIn("magnification", shortfalls[0])

    def test_an_examination_exactly_on_the_magnification_floor_is_adequate(self):
        floor = DEFAULT_SURFACE_FINISH_CRITERIA["min_magnification_x"]
        self.assertTrue(examination_is_adequate(_examination(magnification_x=floor)))

    def test_covering_part_of_the_land_is_a_shortfall(self):
        shortfalls = examination_shortfalls(_examination(examined_fraction=0.5))
        self.assertEqual(len(shortfalls), 1)
        self.assertIn("describes", shortfalls[0])

    def test_an_examination_exactly_on_the_coverage_floor_is_adequate(self):
        floor = DEFAULT_SURFACE_FINISH_CRITERIA["min_examined_fraction"]
        self.assertTrue(examination_is_adequate(_examination(examined_fraction=floor)))

    def test_both_shortfalls_are_reported_not_only_the_first(self):
        shortfalls = examination_shortfalls(
            _examination(magnification_x=4.0, examined_fraction=0.5)
        )
        self.assertEqual(len(shortfalls), 2)


class RoughnessTests(unittest.TestCase):
    def test_a_smooth_surface_is_accepted(self):
        disposition, reason = categorize_roughness(0.8)
        self.assertEqual(disposition, ACCEPT)
        self.assertIn("qualified for", reason)

    def test_a_surface_exactly_on_the_working_ceiling_is_accepted(self):
        ceiling = DEFAULT_SURFACE_FINISH_CRITERIA["max_roughness_ra_um"]
        disposition, _reason = categorize_roughness(ceiling)
        self.assertEqual(disposition, ACCEPT)

    def test_a_surface_between_the_two_ceilings_goes_to_review(self):
        disposition, reason = categorize_roughness(2.0)
        self.assertEqual(disposition, REFER_FOR_REVIEW)
        self.assertIn("the process has moved", reason)

    def test_a_surface_exactly_on_the_weldable_ceiling_goes_to_review(self):
        ceiling = DEFAULT_SURFACE_FINISH_CRITERIA["max_weldable_roughness_ra_um"]
        disposition, _reason = categorize_roughness(ceiling)
        self.assertEqual(disposition, REFER_FOR_REVIEW)

    def test_a_surface_past_the_weldable_ceiling_is_rejected(self):
        disposition, reason = categorize_roughness(5.0)
        self.assertEqual(disposition, REJECT)
        self.assertIn("asperity peaks", reason)

    def test_a_negative_roughness_rejected(self):
        with self.assertRaises(ValueError):
            categorize_roughness(-0.4)


class AnomalyValidationTests(unittest.TestCase):
    def test_an_unknown_anomaly_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_finish_anomaly({"kind": "haze", "coverage_fraction": 0.01})

    def test_a_coverage_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_finish_anomaly(_oxidation(coverage_fraction=1.4))

    def test_a_zero_coverage_rejected(self):
        with self.assertRaises(ValueError):
            validate_finish_anomaly(_oxidation(coverage_fraction=0.0))

    def test_a_pit_without_a_depth_rejected(self):
        with self.assertRaises(ValueError):
            validate_finish_anomaly({"kind": PITTING, "coverage_fraction": 0.01})

    def test_a_nodule_without_a_height_rejected(self):
        with self.assertRaises(ValueError):
            validate_finish_anomaly({"kind": NODULE, "coverage_fraction": 0.01})

    def test_oxidation_needs_no_depth(self):
        self.assertIsNone(validate_finish_anomaly(_oxidation())["depth_fraction"])

    def test_a_non_mapping_anomaly_rejected(self):
        with self.assertRaises(ValueError):
            validate_finish_anomaly("a bit of haze")


class AnomalyDispositionTests(unittest.TestCase):
    def test_a_blister_rejects_at_any_coverage(self):
        disposition, reason = categorize_finish_anomaly(_blister(0.0001))
        self.assertEqual(disposition, REJECT)
        self.assertIn("adhesion", reason)

    def test_a_blister_is_not_a_coverage_question(self):
        small, _reason = categorize_finish_anomaly(_blister(0.0001))
        large, _reason2 = categorize_finish_anomaly(_blister(0.4))
        self.assertEqual(small, REJECT)
        self.assertEqual(large, REJECT)

    def test_a_pit_through_the_deposit_is_rejected(self):
        disposition, reason = categorize_finish_anomaly(_pit(depth_fraction=0.8))
        self.assertEqual(disposition, REJECT)
        self.assertIn("was protecting", reason)

    def test_a_pit_depth_governs_before_its_coverage_does(self):
        disposition, _reason = categorize_finish_anomaly(
            _pit(depth_fraction=0.9, coverage_fraction=0.001)
        )
        self.assertEqual(disposition, REJECT)

    def test_a_pit_exactly_on_the_depth_allowance_falls_to_its_coverage(self):
        depth = DEFAULT_SURFACE_FINISH_CRITERIA["max_pit_depth_fraction"]
        disposition, _reason = categorize_finish_anomaly(
            _pit(depth_fraction=depth, coverage_fraction=0.01)
        )
        self.assertEqual(disposition, ACCEPT)

    def test_a_shallow_but_spread_pit_goes_to_review(self):
        disposition, reason = categorize_finish_anomaly(
            _pit(depth_fraction=0.1, coverage_fraction=0.2)
        )
        self.assertEqual(disposition, REFER_FOR_REVIEW)
        self.assertIn("shallow pitting", reason)

    def test_a_pit_inside_both_allowances_is_accepted(self):
        disposition, _reason = categorize_finish_anomaly(_pit())
        self.assertEqual(disposition, ACCEPT)

    def test_oxidation_past_its_coverage_allowance_goes_to_review(self):
        disposition, reason = categorize_finish_anomaly(_oxidation(0.4))
        self.assertEqual(disposition, REFER_FOR_REVIEW)
        self.assertIn("starves it", reason)

    def test_oxidation_exactly_on_its_allowance_is_accepted(self):
        allowance = DEFAULT_SURFACE_FINISH_CRITERIA["max_oxidation_coverage_fraction"]
        disposition, _reason = categorize_finish_anomaly(_oxidation(allowance))
        self.assertEqual(disposition, ACCEPT)

    def test_residue_past_its_allowance_goes_to_review(self):
        disposition, reason = categorize_finish_anomaly(_residue(0.05))
        self.assertEqual(disposition, REFER_FOR_REVIEW)
        self.assertIn("weld would be made through it", reason)

    def test_residue_inside_its_allowance_is_accepted(self):
        disposition, _reason = categorize_finish_anomaly(_residue(0.01))
        self.assertEqual(disposition, ACCEPT)

    def test_a_tall_nodule_goes_to_review(self):
        disposition, reason = categorize_finish_anomaly(_nodule(depth_fraction=0.8))
        self.assertEqual(disposition, REFER_FOR_REVIEW)
        self.assertIn("holds the weld head off", reason)

    def test_a_nodule_exactly_on_its_height_allowance_is_accepted(self):
        allowance = DEFAULT_SURFACE_FINISH_CRITERIA["max_nodule_height_fraction"]
        disposition, _reason = categorize_finish_anomaly(
            _nodule(depth_fraction=allowance)
        )
        self.assertEqual(disposition, ACCEPT)

    def test_residue_and_oxidation_carry_different_allowances(self):
        oxidised, _r1 = categorize_finish_anomaly(_oxidation(0.03))
        soiled, _r2 = categorize_finish_anomaly(_residue(0.03))
        self.assertEqual(oxidised, ACCEPT)
        self.assertEqual(soiled, REFER_FOR_REVIEW)


class CoverageTotalTests(unittest.TestCase):
    def test_coverage_is_summed_rather_than_unioned(self):
        total = total_anomaly_coverage([_oxidation(0.05), _oxidation(0.05)])
        self.assertAlmostEqual(total, 0.10, places=9)

    def test_an_empty_record_covers_nothing(self):
        self.assertAlmostEqual(total_anomaly_coverage([]), 0.0, places=12)

    def test_a_non_sequence_anomaly_record_rejected(self):
        with self.assertRaises(ValueError):
            total_anomaly_coverage("a bit of oxidation")


class WorstDispositionTests(unittest.TestCase):
    def test_an_empty_set_accepts(self):
        self.assertEqual(worst_disposition([]), ACCEPT)

    def test_severity_beats_record_order(self):
        self.assertEqual(worst_disposition([ACCEPT, REJECT, REFER_FOR_REVIEW]), REJECT)

    def test_a_blister_outranks_an_inadequate_examination(self):
        self.assertEqual(worst_disposition([NOT_ESTABLISHED, REJECT]), REJECT)

    def test_an_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            worst_disposition([ACCEPT, "looks bright"])


class ContactFinishTests(unittest.TestCase):
    def test_a_clean_contact_surface_is_accepted(self):
        result = assess_contact_finish(_anode())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertIsNone(result["governing_attribute"])
        self.assertTrue(result["examination_adequate"])
        self.assertEqual(result["findings"], [])

    def test_an_examination_below_the_magnification_floor_is_not_established(self):
        result = assess_contact_finish(
            _anode(examination=_examination(magnification_x=4.0))
        )
        self.assertEqual(result["verdict"], NOT_ESTABLISHED)
        self.assertEqual(result["governing_attribute"], "examination")
        self.assertFalse(result["examination_adequate"])

    def test_a_blister_rejects_the_contact_and_governs_it(self):
        result = assess_contact_finish(_anode(anomalies=[_blister()]))
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["governing_attribute"], BLISTER)

    def test_roughness_past_the_weldable_ceiling_governs_the_contact(self):
        result = assess_contact_finish(
            _anode(examination=_examination(roughness_ra_um=5.0))
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["governing_attribute"], "roughness")

    def test_a_land_whose_every_anomaly_passed_can_still_be_reviewed(self):
        anomalies = [_oxidation(0.09), _oxidation(0.09), _oxidation(0.09)]
        result = assess_contact_finish(_anode(anomalies=anomalies))
        self.assertEqual(
            [grade for _kind, grade in result["anomaly_grades"]], [ACCEPT] * 3
        )
        self.assertEqual(result["verdict"], REFER_FOR_REVIEW)
        self.assertEqual(result["governing_attribute"], "accumulated-coverage")

    def test_a_land_exactly_on_the_total_coverage_allowance_is_accepted(self):
        result = assess_contact_finish(
            _anode(anomalies=[_oxidation(0.1), _oxidation(0.1)])
        )
        self.assertAlmostEqual(
            result["total_anomaly_coverage_fraction"],
            DEFAULT_SURFACE_FINISH_CRITERIA["max_total_anomaly_coverage_fraction"],
            places=9,
        )
        self.assertEqual(result["verdict"], ACCEPT)

    def test_a_blister_outranks_an_inadequate_examination_on_the_contact(self):
        result = assess_contact_finish(
            _anode(
                examination=_examination(magnification_x=4.0),
                anomalies=[_blister()],
            )
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["governing_attribute"], BLISTER)

    def test_every_anomaly_is_graded_not_only_the_failing_one(self):
        result = assess_contact_finish(
            _anode(anomalies=[_oxidation(0.01), _residue(0.05), _pit()])
        )
        self.assertEqual(result["anomalies_recorded"], 3)
        self.assertEqual(len(result["anomaly_grades"]), 3)
        self.assertIn((RESIDUE, REFER_FOR_REVIEW), result["anomaly_grades"])

    def test_every_finding_is_reported_not_the_first(self):
        result = assess_contact_finish(
            _anode(
                examination=_examination(magnification_x=4.0, examined_fraction=0.5),
                anomalies=[_residue(0.05)],
            )
        )
        self.assertEqual(len(result["findings"]), 3)

    def test_a_blank_contact_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_finish_contact(_anode(id="   "))

    def test_an_unknown_polarity_rejected(self):
        with self.assertRaises(ValueError):
            validate_finish_contact(_anode(polarity="middle"))

    def test_a_contact_with_no_examination_rejected(self):
        with self.assertRaises(ValueError):
            validate_finish_contact(_anode(examination=None))

    def test_a_non_sequence_anomaly_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_finish_contact(_anode(anomalies="a bit of haze"))


class DiodeRollupTests(unittest.TestCase):
    def test_a_diode_clean_on_both_surfaces_is_accepted(self):
        result = assess_diode_surface_finish(_case())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["contacts_examined"], 2)
        self.assertEqual(result["polarities_without_an_examination"], ())
        self.assertEqual(result["governing_attributes"], ())

    def test_a_diode_examined_on_one_polarity_cannot_be_accepted(self):
        result = assess_diode_surface_finish(_case(contacts=[_anode()]))
        self.assertEqual(result["verdict"], NOT_ESTABLISHED)
        self.assertEqual(result["polarities_without_an_examination"], (CATHODE,))

    def test_a_missing_anode_examination_is_named_too(self):
        result = assess_diode_surface_finish(_case(contacts=[_cathode()]))
        self.assertEqual(result["polarities_without_an_examination"], (ANODE,))

    def test_one_blistered_surface_governs_the_diode(self):
        result = assess_diode_surface_finish(
            _case(contacts=[_anode(), _cathode(anomalies=[_blister()])])
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["contacts_not_accepted"], ("cathode-land",))
        self.assertEqual(result["governing_attributes"], (BLISTER,))

    def test_the_roughest_surface_is_carried_up(self):
        result = assess_diode_surface_finish(
            _case(
                contacts=[
                    _anode(),
                    _cathode(examination=_examination(roughness_ra_um=2.0)),
                ]
            )
        )
        self.assertAlmostEqual(_ratio(result["roughest_contact_ra_um"], 2.0), 1.0,
                               places=12)

    def test_a_duplicate_contact_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_surface_finish(_case(contacts=[_anode(), _anode()]))

    def test_a_diode_declaring_no_contact_surface_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_surface_finish(_case(contacts=[]))

    def test_a_non_sequence_contact_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_surface_finish(_case(contacts="anode-land"))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_surface_finish(["diode-01"])


if __name__ == "__main__":
    unittest.main()
