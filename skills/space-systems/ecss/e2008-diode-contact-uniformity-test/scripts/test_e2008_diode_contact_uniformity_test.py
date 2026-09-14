"""Contract tests for the clause 9.6.7 diode contact uniformity test."""

import unittest

from e2008_diode_contact_uniformity_test_logic import (
    ACCEPT,
    ANODE,
    BARE_SITE,
    CATHODE,
    DEFAULT_UNIFORMITY_CRITERIA,
    NOT_ESTABLISHED,
    REFER_FOR_REVIEW,
    REJECT,
    THICK_SITE,
    THIN_SITE,
    UNIFORM,
    ZONE_CENTRE,
    ZONE_EAST,
    ZONE_NORTH,
    ZONE_SOUTH,
    ZONE_WEST,
    assess_contact_uniformity,
    assess_diode_uniformity,
    assess_uniformity_qualification,
    categorize_thickness_site,
    mean_thickness_um,
    thickness_spread_fraction,
    validate_thickness_site,
    validate_uniformity_contact,
    validate_uniformity_criteria,
    variation_coefficient,
    worst_verdict,
    zones_without_a_reading,
)


def _criteria(**overrides):
    criteria = dict(DEFAULT_UNIFORMITY_CRITERIA)
    criteria.update(overrides)
    return criteria


def _site(zone=ZONE_CENTRE, thickness_um=6.0):
    return {"zone": zone, "thickness_um": thickness_um}


def _even_map(value=6.0):
    return [
        _site(ZONE_CENTRE, value),
        _site(ZONE_NORTH, value),
        _site(ZONE_SOUTH, value),
        _site(ZONE_EAST, value),
        _site(ZONE_WEST, value),
    ]


def _map_from(values):
    zones = (ZONE_CENTRE, ZONE_NORTH, ZONE_SOUTH, ZONE_EAST, ZONE_WEST)
    return [
        _site(zones[index % len(zones)], value) for index, value in enumerate(values)
    ]


def _anode(**overrides):
    contact = {"id": "anode-land", "polarity": ANODE, "sites": _even_map()}
    contact.update(overrides)
    return contact


def _cathode(**overrides):
    contact = {"id": "cathode-land", "polarity": CATHODE, "sites": _even_map()}
    contact.update(overrides)
    return contact


def _case(**overrides):
    case = {"id": "diode-01", "contacts": [_anode(), _cathode()]}
    case.update(overrides)
    return case


def _lot(**overrides):
    lot = {
        "id": "qual-lot-01",
        "declared_sample": 3,
        "devices": [
            _case(id="diode-01"),
            _case(id="diode-02"),
            _case(id="diode-03"),
        ],
    }
    lot.update(overrides)
    return lot


def _ratio(value, expected):
    return value / expected


class CriteriaTests(unittest.TestCase):
    def test_the_default_criteria_validate(self):
        self.assertIs(
            validate_uniformity_criteria(DEFAULT_UNIFORMITY_CRITERIA),
            DEFAULT_UNIFORMITY_CRITERIA,
        )

    def test_a_non_mapping_criteria_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_uniformity_criteria("keep it even")

    def test_a_spread_allowance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_uniformity_criteria(_criteria(max_spread_fraction=1.5))

    def test_a_thickness_band_that_closes_on_itself_rejected(self):
        with self.assertRaises(ValueError):
            validate_uniformity_criteria(
                _criteria(min_local_thickness_um=6.0, max_local_thickness_um=6.0)
            )

    def test_a_single_site_criteria_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_uniformity_criteria(_criteria(min_sites_per_contact=1))

    def test_an_unknown_required_zone_rejected(self):
        with self.assertRaises(ValueError):
            validate_uniformity_criteria(_criteria(required_zones=("corner",)))

    def test_an_empty_required_zone_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_uniformity_criteria(_criteria(required_zones=()))

    def test_a_qualification_of_no_devices_rejected(self):
        with self.assertRaises(ValueError):
            validate_uniformity_criteria(_criteria(min_qualification_devices=0))


class SiteValidationTests(unittest.TestCase):
    def test_a_site_normalises_to_zone_and_thickness(self):
        reading = validate_thickness_site(_site(ZONE_EAST, 5.5))
        self.assertEqual(reading["zone"], ZONE_EAST)
        self.assertAlmostEqual(reading["thickness_um"], 5.5, places=12)

    def test_an_unknown_zone_rejected(self):
        with self.assertRaises(ValueError):
            validate_thickness_site(_site("corner", 6.0))

    def test_a_zero_thickness_reading_rejected(self):
        with self.assertRaises(ValueError):
            validate_thickness_site(_site(ZONE_CENTRE, 0.0))

    def test_a_non_numeric_thickness_rejected(self):
        with self.assertRaises(ValueError):
            validate_thickness_site(_site(ZONE_CENTRE, "thick enough"))

    def test_a_non_mapping_site_rejected(self):
        with self.assertRaises(ValueError):
            validate_thickness_site("centre 6 um")

    def test_a_contact_with_an_empty_map_rejected(self):
        with self.assertRaises(ValueError):
            validate_uniformity_contact(_anode(sites=[]))

    def test_an_unknown_polarity_rejected(self):
        with self.assertRaises(ValueError):
            validate_uniformity_contact(_anode(polarity="middle"))

    def test_a_blank_contact_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_uniformity_contact(_anode(id="   "))


class MapStatisticTests(unittest.TestCase):
    def test_the_mean_of_an_even_map_is_the_reading_itself(self):
        self.assertAlmostEqual(mean_thickness_um(_even_map(6.0)), 6.0, places=12)

    def test_an_even_map_has_no_spread(self):
        self.assertAlmostEqual(
            thickness_spread_fraction(_even_map(6.0)), 0.0, places=12
        )

    def test_an_even_map_has_no_variation(self):
        self.assertAlmostEqual(variation_coefficient(_even_map(6.0)), 0.0, places=12)

    def test_the_spread_is_the_extremes_over_the_mean(self):
        readings = _map_from([5.4, 6.6, 6.0, 6.0, 6.0])
        self.assertAlmostEqual(mean_thickness_um(readings), 6.0, places=12)
        self.assertAlmostEqual(thickness_spread_fraction(readings), 0.20, places=9)

    def test_a_map_can_pass_the_spread_and_fail_the_variation(self):
        readings = _map_from([5.4, 6.6, 5.4, 6.6, 6.0])
        self.assertAlmostEqual(thickness_spread_fraction(readings), 0.20, places=9)
        self.assertGreater(
            variation_coefficient(readings),
            DEFAULT_UNIFORMITY_CRITERIA["max_variation_coefficient"],
        )

    def test_a_map_can_fail_the_spread_and_pass_the_variation(self):
        readings = _map_from([4.8] + [6.15] * 8)
        self.assertAlmostEqual(mean_thickness_um(readings), 6.0, places=12)
        self.assertGreater(
            thickness_spread_fraction(readings),
            DEFAULT_UNIFORMITY_CRITERIA["max_spread_fraction"],
        )
        self.assertLess(
            variation_coefficient(readings),
            DEFAULT_UNIFORMITY_CRITERIA["max_variation_coefficient"],
        )

    def test_a_non_sequence_map_rejected(self):
        with self.assertRaises(ValueError):
            thickness_spread_fraction("six microns everywhere")

    def test_an_empty_map_has_no_mean(self):
        with self.assertRaises(ValueError):
            mean_thickness_um([])


class ZoneCoverageTests(unittest.TestCase):
    def test_a_full_map_leaves_no_zone_unread(self):
        self.assertEqual(zones_without_a_reading(_even_map()), ())

    def test_an_unread_zone_is_named(self):
        readings = [
            _site(ZONE_CENTRE),
            _site(ZONE_NORTH),
            _site(ZONE_SOUTH),
            _site(ZONE_EAST),
        ]
        self.assertEqual(zones_without_a_reading(readings), (ZONE_WEST,))

    def test_a_clustered_map_satisfies_a_count_and_not_a_coverage(self):
        readings = [
            _site(ZONE_CENTRE),
            _site(ZONE_CENTRE),
            _site(ZONE_NORTH),
            _site(ZONE_SOUTH),
            _site(ZONE_EAST),
        ]
        self.assertEqual(len(readings), DEFAULT_UNIFORMITY_CRITERIA["min_sites_per_contact"])
        self.assertEqual(zones_without_a_reading(readings), (ZONE_WEST,))


class SiteGradingTests(unittest.TestCase):
    def test_a_site_on_the_mean_is_uniform(self):
        grade, reason = categorize_thickness_site(_site(ZONE_CENTRE, 6.0), 6.0)
        self.assertEqual(grade, UNIFORM)
        self.assertIn("contact mean", reason)

    def test_a_site_exactly_on_the_deviation_tolerance_is_uniform(self):
        tolerance = DEFAULT_UNIFORMITY_CRITERIA["max_spread_fraction"] / 2.0
        self.assertAlmostEqual(tolerance, 0.10, places=12)
        grade, _reason = categorize_thickness_site(_site(ZONE_NORTH, 6.6), 6.0)
        self.assertEqual(grade, UNIFORM)

    def test_a_site_under_the_tolerance_is_thin(self):
        grade, reason = categorize_thickness_site(_site(ZONE_WEST, 5.0), 6.0)
        self.assertEqual(grade, THIN_SITE)
        self.assertIn("under the contact mean", reason)

    def test_a_site_over_the_tolerance_is_thick(self):
        grade, reason = categorize_thickness_site(_site(ZONE_EAST, 7.5), 6.0)
        self.assertEqual(grade, THICK_SITE)
        self.assertIn("over the contact mean", reason)

    def test_a_site_under_the_local_floor_is_bare(self):
        grade, reason = categorize_thickness_site(_site(ZONE_SOUTH, 1.5), 1.5)
        self.assertEqual(grade, BARE_SITE)
        self.assertIn("unweldable", reason)

    def test_an_evenly_thin_map_is_uniform_and_still_bare(self):
        floor = DEFAULT_UNIFORMITY_CRITERIA["min_local_thickness_um"]
        readings = _even_map(floor / 2.0)
        self.assertAlmostEqual(thickness_spread_fraction(readings), 0.0, places=12)
        grade, _reason = categorize_thickness_site(readings[0], floor / 2.0)
        self.assertEqual(grade, BARE_SITE)

    def test_a_site_exactly_on_the_local_floor_is_uniform(self):
        floor = DEFAULT_UNIFORMITY_CRITERIA["min_local_thickness_um"]
        grade, _reason = categorize_thickness_site(_site(ZONE_CENTRE, floor), floor)
        self.assertEqual(grade, UNIFORM)

    def test_a_site_exactly_on_the_local_ceiling_is_uniform(self):
        ceiling = DEFAULT_UNIFORMITY_CRITERIA["max_local_thickness_um"]
        grade, _reason = categorize_thickness_site(_site(ZONE_CENTRE, ceiling), ceiling)
        self.assertEqual(grade, UNIFORM)

    def test_a_nodule_the_mean_absorbs_is_still_caught_by_the_ceiling(self):
        ceiling = DEFAULT_UNIFORMITY_CRITERIA["max_local_thickness_um"]
        grade, reason = categorize_thickness_site(
            _site(ZONE_NORTH, ceiling + 1.0), ceiling
        )
        self.assertEqual(grade, THICK_SITE)
        self.assertIn("local ceiling", reason)

    def test_a_zero_reference_mean_rejected(self):
        with self.assertRaises(ValueError):
            categorize_thickness_site(_site(ZONE_CENTRE, 6.0), 0.0)


class WorstVerdictTests(unittest.TestCase):
    def test_an_empty_set_accepts(self):
        self.assertEqual(worst_verdict([]), ACCEPT)

    def test_severity_beats_record_order(self):
        self.assertEqual(worst_verdict([ACCEPT, REJECT, REFER_FOR_REVIEW]), REJECT)

    def test_a_bare_site_outranks_an_unmapped_zone(self):
        self.assertEqual(worst_verdict([NOT_ESTABLISHED, REJECT]), REJECT)

    def test_an_unmapped_zone_outranks_a_review(self):
        self.assertEqual(worst_verdict([REFER_FOR_REVIEW, NOT_ESTABLISHED]), NOT_ESTABLISHED)

    def test_an_unknown_verdict_rejected(self):
        with self.assertRaises(ValueError):
            worst_verdict([ACCEPT, "looks even"])


class ContactAssessmentTests(unittest.TestCase):
    def test_an_even_fully_mapped_contact_is_accepted(self):
        result = assess_contact_uniformity(_anode())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["sites_measured"], 5)

    def test_a_contact_exactly_on_the_spread_allowance_is_accepted(self):
        result = assess_contact_uniformity(
            _anode(sites=_map_from([5.4, 6.6, 6.0, 6.0, 6.0]))
        )
        self.assertAlmostEqual(result["spread_fraction"], 0.20, places=9)
        self.assertEqual(result["verdict"], ACCEPT)

    def test_a_sloping_land_fails_the_variation_with_the_spread_intact(self):
        result = assess_contact_uniformity(
            _anode(sites=_map_from([5.4, 6.6, 5.4, 6.6, 6.0]))
        )
        self.assertEqual(result["verdict"], REFER_FOR_REVIEW)
        self.assertAlmostEqual(result["spread_fraction"], 0.20, places=9)
        self.assertTrue(any("varies by" in finding for finding in result["findings"]))

    def test_a_clustered_map_closes_the_contact_as_not_evaluated(self):
        readings = [
            _site(ZONE_CENTRE),
            _site(ZONE_CENTRE),
            _site(ZONE_NORTH),
            _site(ZONE_SOUTH),
            _site(ZONE_EAST),
        ]
        result = assess_contact_uniformity(_anode(sites=readings))
        self.assertEqual(result["verdict"], NOT_ESTABLISHED)
        self.assertEqual(result["zones_without_a_reading"], (ZONE_WEST,))

    def test_too_few_sites_close_the_contact_as_not_evaluated(self):
        criteria = _criteria(required_zones=(ZONE_CENTRE,), min_sites_per_contact=5)
        result = assess_contact_uniformity(
            _anode(sites=[_site(ZONE_CENTRE)] * 4), criteria
        )
        self.assertEqual(result["verdict"], NOT_ESTABLISHED)
        self.assertTrue(any("sites measured" in finding for finding in result["findings"]))

    def test_a_bare_site_outranks_a_missing_zone(self):
        readings = [
            _site(ZONE_CENTRE, 6.0),
            _site(ZONE_NORTH, 6.0),
            _site(ZONE_SOUTH, 6.0),
            _site(ZONE_EAST, 1.0),
        ]
        result = assess_contact_uniformity(_anode(sites=readings))
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["zones_without_a_reading"], (ZONE_WEST,))

    def test_the_extremes_are_reported_with_the_verdict(self):
        result = assess_contact_uniformity(
            _anode(sites=_map_from([5.4, 6.6, 6.0, 6.0, 6.0]))
        )
        self.assertAlmostEqual(_ratio(result["min_thickness_um"], 5.4), 1.0, places=12)
        self.assertAlmostEqual(_ratio(result["max_thickness_um"], 6.6), 1.0, places=12)

    def test_every_site_is_graded_not_only_the_failing_one(self):
        result = assess_contact_uniformity(
            _anode(sites=_map_from([5.0, 6.0, 6.0, 6.0, 7.0]))
        )
        self.assertEqual(len(result["site_grades"]), 5)
        self.assertIn((ZONE_CENTRE, THIN_SITE), result["site_grades"])


class DiodeRollupTests(unittest.TestCase):
    def test_a_diode_even_on_both_lands_is_accepted(self):
        result = assess_diode_uniformity(_case())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["contacts_assessed"], 2)
        self.assertEqual(result["polarities_without_a_map"], ())

    def test_a_diode_mapped_on_one_polarity_cannot_be_accepted(self):
        result = assess_diode_uniformity(_case(contacts=[_anode()]))
        self.assertEqual(result["verdict"], NOT_ESTABLISHED)
        self.assertEqual(result["polarities_without_a_map"], (CATHODE,))

    def test_a_missing_anode_map_is_named_too(self):
        result = assess_diode_uniformity(_case(contacts=[_cathode()]))
        self.assertEqual(result["polarities_without_a_map"], (ANODE,))

    def test_one_bad_land_governs_the_diode(self):
        result = assess_diode_uniformity(
            _case(contacts=[_anode(), _cathode(sites=_even_map(1.0))])
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["contacts_not_accepted"], ("cathode-land",))

    def test_the_thinnest_site_is_carried_up_from_either_land(self):
        result = assess_diode_uniformity(
            _case(contacts=[_anode(), _cathode(sites=_map_from([4.0, 6.5, 6.5, 6.5, 6.5]))])
        )
        self.assertAlmostEqual(_ratio(result["thinnest_site_um"], 4.0), 1.0, places=12)

    def test_a_duplicate_contact_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_uniformity(_case(contacts=[_anode(), _anode()]))

    def test_a_diode_declaring_no_contact_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_uniformity(_case(contacts=[]))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_uniformity(["diode-01"])


class QualificationRunTests(unittest.TestCase):
    def test_a_complete_run_of_even_devices_is_accepted(self):
        result = assess_uniformity_qualification(_lot())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["devices_mapped"], 3)

    def test_a_run_short_of_its_declared_sample_is_not_evaluated(self):
        result = assess_uniformity_qualification(
            _lot(devices=[_case(id="diode-01"), _case(id="diode-02")])
        )
        self.assertEqual(result["verdict"], NOT_ESTABLISHED)
        self.assertTrue(
            any("declared devices" in finding for finding in result["rollup_findings"])
        )

    def test_a_sample_under_the_qualification_floor_is_not_evaluated(self):
        result = assess_uniformity_qualification(
            _lot(declared_sample=1, devices=[_case(id="diode-01")])
        )
        self.assertEqual(result["verdict"], NOT_ESTABLISHED)

    def test_one_rejected_device_governs_the_run(self):
        result = assess_uniformity_qualification(
            _lot(
                devices=[
                    _case(id="diode-01"),
                    _case(id="diode-02"),
                    _case(
                        id="diode-03",
                        contacts=[_anode(sites=_even_map(1.0)), _cathode()],
                    ),
                ]
            )
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["devices_not_accepted"], ("diode-03",))

    def test_a_duplicate_device_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_uniformity_qualification(
                _lot(devices=[_case(id="diode-01"), _case(id="diode-01")])
            )

    def test_a_non_sequence_device_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_uniformity_qualification(_lot(devices="diode-01"))

    def test_a_negative_declared_sample_rejected(self):
        with self.assertRaises(ValueError):
            assess_uniformity_qualification(_lot(declared_sample=-1))

    def test_a_non_mapping_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_uniformity_qualification("qual-lot-01")


if __name__ == "__main__":
    unittest.main()
