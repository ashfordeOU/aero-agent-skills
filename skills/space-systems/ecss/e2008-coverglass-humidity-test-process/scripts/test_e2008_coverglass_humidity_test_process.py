"""Contract tests for the clause 8.7.11.1.2 holding-arrangement logic."""

import unittest

from e2008_coverglass_humidity_test_process_logic import (
    CHAMBER_CONDITIONS_INVALID,
    DEFAULT_HOLDING_POLICY,
    EDGE_SLOT,
    EXPOSURE_INCOMPLETE,
    FLAT_TRAY,
    HOLDING_NOT_ACCEPTABLE,
    SUBGROUP_EXPOSURE_HELD,
    SUBGROUP_NOT_ESTABLISHED,
    article_holding_findings,
    assess_coverglass_humidity_holding,
    chamber_findings,
    dew_point_c,
    dew_point_margin_c,
    masked_face_fraction,
    rack_capacity,
    rack_pitch_mm,
    realised_clearance_mm,
    settled_dwell_hours,
    subgroup_population,
    support_exposes_both_faces,
    validate_holding_policy,
)

SUBGROUP = "subgroup-o"


def _policy(**overrides):
    policy = dict(DEFAULT_HOLDING_POLICY)
    policy.update(overrides)
    return policy


def _article(identifier, subgroup=SUBGROUP, **overrides):
    article = {
        "id": identifier,
        "subgroup": subgroup,
        "support": EDGE_SLOT,
        "holder_material": "ptfe",
        "holder_contact_area_mm2": 40.0,
        "face_area_mm2": 1600.0,
        "face_clearance_mm": 6.0,
        "touching_neighbour": False,
    }
    article.update(overrides)
    return article


def _chamber(**overrides):
    chamber = {
        "temperature_c": 45.0,
        "relative_humidity_percent": 90.0,
        "gauge_pressure_kpa": 0.0,
        "article_surface_temperature_c": 45.0,
        "total_chamber_hours": 30.0,
        "ramp_hours": 4.0,
    }
    chamber.update(overrides)
    return chamber


def _case(**overrides):
    case = {
        "designated_subgroup": SUBGROUP,
        "chamber": _chamber(),
        "articles": [_article("cg-01"), _article("cg-02"), _article("cg-03")],
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_holding_policy(DEFAULT_HOLDING_POLICY), DEFAULT_HOLDING_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_holding_policy("subgroup-o")

    def test_masked_fraction_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_holding_policy(_policy(max_masked_face_fraction=1.0))

    def test_inverted_humidity_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_holding_policy(
                _policy(
                    min_relative_humidity_percent=95.0,
                    max_relative_humidity_percent=85.0,
                )
            )

    def test_saturated_humidity_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_holding_policy(_policy(max_relative_humidity_percent=100.0))

    def test_empty_holder_material_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_holding_policy(_policy(holder_materials=()))


class DewPointTests(unittest.TestCase):
    def test_saturated_air_dews_at_its_own_temperature(self):
        self.assertAlmostEqual(dew_point_c(37.5, 100.0), 37.5, places=9)

    def test_dew_point_sits_below_air_temperature_when_unsaturated(self):
        self.assertLess(dew_point_c(45.0, 90.0), 45.0 - 1.0)

    def test_drier_air_dews_lower(self):
        self.assertLess(dew_point_c(45.0, 60.0), dew_point_c(45.0, 90.0) - 1.0)

    def test_zero_humidity_rejected(self):
        with self.assertRaises(ValueError):
            dew_point_c(45.0, 0.0)

    def test_supersaturated_humidity_rejected(self):
        with self.assertRaises(ValueError):
            dew_point_c(45.0, 101.0)

    def test_margin_is_surface_temperature_less_dew_point(self):
        margin = dew_point_margin_c(46.0, 45.0, 90.0)
        self.assertAlmostEqual(margin, 46.0 - dew_point_c(45.0, 90.0), places=9)

    def test_article_colder_than_dew_point_gives_a_negative_margin(self):
        self.assertLess(dew_point_margin_c(40.0, 45.0, 90.0), 0.0)


class RackGeometryTests(unittest.TestCase):
    def test_pitch_is_thickness_plus_clearance(self):
        self.assertAlmostEqual(rack_pitch_mm(0.15, 6.0), 6.15, places=9)

    def test_capacity_floors_a_partial_slot(self):
        self.assertEqual(rack_capacity(300.0, 6.15), 48)

    def test_capacity_keeps_an_exactly_filled_rack(self):
        self.assertEqual(rack_capacity(30.0, 6.0), 5)

    def test_zero_pitch_rejected(self):
        with self.assertRaises(ValueError):
            rack_capacity(300.0, 0.0)

    def test_realised_clearance_shares_the_slack_between_articles(self):
        self.assertAlmostEqual(
            realised_clearance_mm(300.0, 40, 0.15), (300.0 - 6.0) / 40.0, places=9
        )

    def test_masked_fraction_is_contact_over_face(self):
        self.assertAlmostEqual(masked_face_fraction(100.0, 1000.0), 0.1, places=9)

    def test_contact_larger_than_the_face_rejected(self):
        with self.assertRaises(ValueError):
            masked_face_fraction(1200.0, 1000.0)

    def test_untouched_face_masks_nothing(self):
        self.assertAlmostEqual(masked_face_fraction(0.0, 1000.0), 0.0, places=9)


class SupportTests(unittest.TestCase):
    def test_edge_slot_exposes_both_faces(self):
        self.assertTrue(support_exposes_both_faces(EDGE_SLOT))

    def test_flat_tray_shelves_a_face(self):
        self.assertFalse(support_exposes_both_faces(FLAT_TRAY))

    def test_unknown_support_rejected(self):
        with self.assertRaises(ValueError):
            support_exposes_both_faces("hung-on-a-string")


class DwellTests(unittest.TestCase):
    def test_ramp_comes_back_out_of_the_dwell(self):
        self.assertAlmostEqual(settled_dwell_hours(30.0, 6.0), 24.0, places=9)

    def test_ramp_longer_than_the_run_rejected(self):
        with self.assertRaises(ValueError):
            settled_dwell_hours(4.0, 6.0)

    def test_negative_ramp_rejected(self):
        with self.assertRaises(ValueError):
            settled_dwell_hours(30.0, -1.0)


class PopulationTests(unittest.TestCase):
    def test_members_and_non_members_are_kept_apart(self):
        members, others = subgroup_population(
            [_article("cg-01"), _article("cg-09", subgroup="subgroup-b")], SUBGROUP
        )
        self.assertEqual([a["id"] for a in members], ["cg-01"])
        self.assertEqual([a["id"] for a in others], ["cg-09"])

    def test_article_without_a_recorded_subgroup_rejected(self):
        article = _article("cg-01")
        del article["subgroup"]
        with self.assertRaises(ValueError):
            subgroup_population([article], SUBGROUP)

    def test_duplicate_article_id_rejected(self):
        with self.assertRaises(ValueError):
            subgroup_population([_article("cg-01"), _article("cg-01")], SUBGROUP)


class ArticleHoldingTests(unittest.TestCase):
    def test_a_well_held_article_reports_nothing(self):
        self.assertEqual(article_holding_findings(_article("cg-01")), ())

    def test_tray_support_is_reported(self):
        findings = article_holding_findings(_article("cg-01", support=FLAT_TRAY))
        self.assertEqual(len(findings), 1)
        self.assertIn("shelves a face", findings[0])

    def test_unqualified_holder_material_is_reported(self):
        findings = article_holding_findings(
            _article("cg-01", holder_material="mild-steel")
        )
        self.assertTrue(any("holder materials" in f for f in findings))

    def test_over_masked_face_is_reported(self):
        findings = article_holding_findings(
            _article("cg-01", holder_contact_area_mm2=400.0)
        )
        self.assertTrue(any("masks" in f for f in findings))

    def test_masking_exactly_on_the_limit_is_accepted(self):
        self.assertEqual(
            article_holding_findings(_article("cg-01", holder_contact_area_mm2=160.0)),
            (),
        )

    def test_tight_clearance_is_reported(self):
        findings = article_holding_findings(_article("cg-01", face_clearance_mm=1.0))
        self.assertTrue(any("circulate" in f for f in findings))

    def test_clearance_exactly_on_the_limit_is_accepted(self):
        self.assertEqual(
            article_holding_findings(_article("cg-01", face_clearance_mm=5.0)), ()
        )

    def test_touching_neighbour_is_reported(self):
        findings = article_holding_findings(
            _article("cg-01", touching_neighbour=True)
        )
        self.assertTrue(any("touches a neighbour" in f for f in findings))

    def test_non_boolean_touching_flag_rejected(self):
        with self.assertRaises(ValueError):
            article_holding_findings(_article("cg-01", touching_neighbour="no"))

    def test_every_holding_defect_is_listed_not_just_the_first(self):
        findings = article_holding_findings(
            _article(
                "cg-01",
                support=FLAT_TRAY,
                holder_material="mild-steel",
                face_clearance_mm=0.5,
                touching_neighbour=True,
            )
        )
        self.assertEqual(len(findings), 4)


class ChamberTests(unittest.TestCase):
    def test_a_nominal_chamber_reports_nothing(self):
        margin, findings = chamber_findings(_chamber())
        self.assertEqual(findings, ())
        self.assertGreater(margin, 1.0)

    def test_cold_chamber_is_reported(self):
        _margin, findings = chamber_findings(_chamber(temperature_c=25.0))
        self.assertTrue(any("chamber air" in f for f in findings))

    def test_dry_chamber_is_reported(self):
        _margin, findings = chamber_findings(
            _chamber(relative_humidity_percent=40.0)
        )
        self.assertTrue(any("relative humidity" in f for f in findings))

    def test_pressurised_chamber_is_reported(self):
        _margin, findings = chamber_findings(_chamber(gauge_pressure_kpa=20.0))
        self.assertTrue(any("ambient pressure" in f for f in findings))

    def test_a_partial_vacuum_is_reported_as_well(self):
        _margin, findings = chamber_findings(_chamber(gauge_pressure_kpa=-20.0))
        self.assertTrue(any("ambient pressure" in f for f in findings))

    def test_condensing_article_is_reported(self):
        _margin, findings = chamber_findings(
            _chamber(article_surface_temperature_c=41.0)
        )
        self.assertTrue(any("dew point" in f for f in findings))

    def test_missing_surface_temperature_rejected(self):
        chamber = _chamber()
        del chamber["article_surface_temperature_c"]
        with self.assertRaises(ValueError):
            chamber_findings(chamber)


class VerdictTests(unittest.TestCase):
    def test_a_sound_arrangement_is_held(self):
        result = assess_coverglass_humidity_holding(_case())
        self.assertEqual(result["verdict"], SUBGROUP_EXPOSURE_HELD)
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["held_articles"]), 3)

    def test_settled_dwell_is_reported_on_the_accepted_case(self):
        result = assess_coverglass_humidity_holding(_case())
        self.assertAlmostEqual(result["settled_dwell_hours"], 26.0, places=9)

    def test_blank_designation_is_not_a_population(self):
        result = assess_coverglass_humidity_holding(_case(designated_subgroup="  "))
        self.assertEqual(result["verdict"], SUBGROUP_NOT_ESTABLISHED)

    def test_no_member_article_is_not_a_population(self):
        case = _case(articles=[_article("cg-09", subgroup="subgroup-b")])
        result = assess_coverglass_humidity_holding(case)
        self.assertEqual(result["verdict"], SUBGROUP_NOT_ESTABLISHED)
        self.assertEqual(result["excluded_articles"], ("cg-09",))

    def test_a_short_subgroup_stops_the_run_at_the_population_step(self):
        case = _case(articles=[_article("cg-01"), _article("cg-02")])
        result = assess_coverglass_humidity_holding(case)
        self.assertEqual(result["verdict"], SUBGROUP_NOT_ESTABLISHED)
        self.assertIsNone(result["dew_point_margin_c"])
        self.assertIsNone(result["settled_dwell_hours"])

    def test_one_badly_held_article_fails_the_arrangement(self):
        case = _case(
            articles=[
                _article("cg-01"),
                _article("cg-02", support=FLAT_TRAY),
                _article("cg-03"),
            ]
        )
        result = assess_coverglass_humidity_holding(case)
        self.assertEqual(result["verdict"], HOLDING_NOT_ACCEPTABLE)
        self.assertTrue(any("cg-02" in f for f in result["findings"]))

    def test_the_holding_step_is_judged_before_the_chamber_step(self):
        case = _case(
            articles=[_article("cg-0%d" % n, support=FLAT_TRAY) for n in (1, 2, 3)],
            chamber=_chamber(temperature_c=20.0),
        )
        result = assess_coverglass_humidity_holding(case)
        self.assertEqual(result["verdict"], HOLDING_NOT_ACCEPTABLE)
        self.assertIsNone(result["dew_point_margin_c"])

    def test_bad_chamber_condition_fails_the_run(self):
        case = _case(chamber=_chamber(relative_humidity_percent=30.0))
        result = assess_coverglass_humidity_holding(case)
        self.assertEqual(result["verdict"], CHAMBER_CONDITIONS_INVALID)

    def test_short_settled_dwell_fails_the_run(self):
        case = _case(chamber=_chamber(total_chamber_hours=26.0, ramp_hours=4.0))
        result = assess_coverglass_humidity_holding(case)
        self.assertEqual(result["verdict"], EXPOSURE_INCOMPLETE)
        self.assertAlmostEqual(result["settled_dwell_hours"], 22.0, places=9)

    def test_a_dwell_exactly_on_the_minimum_is_held(self):
        case = _case(chamber=_chamber(total_chamber_hours=28.0, ramp_hours=4.0))
        result = assess_coverglass_humidity_holding(case)
        self.assertEqual(result["verdict"], SUBGROUP_EXPOSURE_HELD)

    def test_missing_designation_key_rejected(self):
        case = _case()
        del case["designated_subgroup"]
        with self.assertRaises(ValueError):
            assess_coverglass_humidity_holding(case)

    def test_missing_chamber_record_rejected(self):
        case = _case()
        del case["chamber"]
        with self.assertRaises(ValueError):
            assess_coverglass_humidity_holding(case)

    def test_missing_article_inventory_rejected(self):
        case = _case()
        del case["articles"]
        with self.assertRaises(ValueError):
            assess_coverglass_humidity_holding(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_humidity_holding(["designated_subgroup"])


if __name__ == "__main__":
    unittest.main()
