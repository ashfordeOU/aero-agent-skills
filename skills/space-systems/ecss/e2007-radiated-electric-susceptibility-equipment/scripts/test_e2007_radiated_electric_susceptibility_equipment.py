#!/usr/bin/env python3
"""Gate 3 contract test for e2007-radiated-electric-susceptibility-equipment.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_radiated_electric_susceptibility_equipment.py
"""

import unittest

from e2007_radiated_electric_susceptibility_equipment_logic import (
    NOT_READY,
    READY,
    ROLE_AMPLIFIER,
    ROLE_ANTENNA,
    ROLE_GENERATOR,
    ROLE_PROBE,
    absent_roles,
    assess_radiated_electric_susceptibility_equipment,
    band_coverage_findings,
    calibration_findings,
    collect_instrument_set,
    delivered_power_dbm,
    dbm_to_watts,
    power_margin_db,
    probe_findings,
    required_forward_power_w,
    span_intersection,
    validate_instrument,
    watts_to_dbm,
)

BAND = (1.0e8, 1.0e9)

# Independent values for a 20 V/m exposure raised at one metre by a 6 dBi
# antenna: P = (E d)^2 / (30 G), written out rather than recomputed here.
REQUIRED_W = 3.3491819086794403
REQUIRED_DBM = 35.249387366083


def gen(**over):
    item = {
        "role": ROLE_GENERATOR,
        "identifier": "sig-gen-1",
        "span_low_hz": 9.0e3,
        "span_high_hz": 2.0e10,
        "calibration_valid_days": 400.0,
        "output_dbm": 0.0,
    }
    item.update(over)
    return item


def amp(**over):
    item = {
        "role": ROLE_AMPLIFIER,
        "identifier": "amp-200w",
        "span_low_hz": 1.0e7,
        "span_high_hz": 2.0e9,
        "calibration_valid_days": 400.0,
        "gain_db": 50.0,
        "rated_output_dbm": 53.0,
    }
    item.update(over)
    return item


def ant(**over):
    item = {
        "role": ROLE_ANTENNA,
        "identifier": "horn-a",
        "span_low_hz": 8.0e7,
        "span_high_hz": 1.0e9,
        "calibration_valid_days": 400.0,
        "gain_dbi": 6.0,
    }
    item.update(over)
    return item


def probe(**over):
    item = {
        "role": ROLE_PROBE,
        "identifier": "probe-iso-1",
        "span_low_hz": 1.0e7,
        "span_high_hz": 1.8e10,
        "calibration_valid_days": 400.0,
        "range_min_v_m": 1.0,
        "range_max_v_m": 200.0,
        "is_isotropic": True,
    }
    item.update(over)
    return item


def chain(**over):
    items = {
        ROLE_GENERATOR: gen(),
        ROLE_AMPLIFIER: amp(),
        ROLE_ANTENNA: ant(),
        ROLE_PROBE: probe(),
    }
    items.update(over)
    return [items[role] for role in items if items[role] is not None]


def requirement(**over):
    record = {
        "band_hz": BAND,
        "field_required_v_m": 20.0,
        "separation_m": 1.0,
        "campaign_days": 120.0,
        "cable_loss_db": 1.0,
    }
    record.update(over)
    return record


class TestInstrumentValidation(unittest.TestCase):
    def test_a_good_item_normalizes(self):
        item = validate_instrument(ant())
        self.assertEqual(item["role"], ROLE_ANTENNA)
        self.assertAlmostEqual(item["gain_dbi"], 6.0, places=9)

    def test_an_unrecognized_role_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_instrument(ant(role="turntable"))

    def test_an_empty_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_instrument(ant(identifier="   "))

    def test_an_inverted_span_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_instrument(ant(span_low_hz=1.0e9, span_high_hz=8.0e7))

    def test_a_negative_calibration_validity_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_instrument(amp(calibration_valid_days=-1.0))

    def test_an_antenna_without_its_gain_is_rejected(self):
        item = ant()
        del item["gain_dbi"]
        with self.assertRaises(ValueError):
            validate_instrument(item)

    def test_a_probe_with_a_non_boolean_isotropy_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_instrument(probe(is_isotropic="yes"))

    def test_a_probe_with_an_inverted_range_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_instrument(probe(range_min_v_m=200.0, range_max_v_m=1.0))


class TestInstrumentSet(unittest.TestCase):
    def test_a_full_set_indexes_by_role(self):
        by_role = collect_instrument_set(chain())
        self.assertEqual(sorted(by_role), sorted([
            ROLE_AMPLIFIER, ROLE_ANTENNA, ROLE_GENERATOR, ROLE_PROBE
        ]))

    def test_a_role_declared_twice_is_rejected(self):
        with self.assertRaises(ValueError):
            collect_instrument_set(chain() + [amp(identifier="amp-spare")])

    def test_an_absent_role_is_named(self):
        by_role = collect_instrument_set(chain(**{ROLE_AMPLIFIER: None}))
        self.assertEqual(absent_roles(by_role), [ROLE_AMPLIFIER])

    def test_an_empty_set_is_rejected(self):
        with self.assertRaises(ValueError):
            collect_instrument_set([])


class TestSpanIntersection(unittest.TestCase):
    def test_the_intersection_is_bounded_by_the_narrowest_item(self):
        intersection = span_intersection(collect_instrument_set(chain()))
        self.assertEqual(intersection["low_bounded_role"], ROLE_ANTENNA)
        self.assertEqual(intersection["high_bounded_role"], ROLE_ANTENNA)
        self.assertAlmostEqual(intersection["high_hz"], 1.0e9, places=3)

    def test_spans_that_do_not_overlap_are_refused(self):
        by_role = collect_instrument_set(
            chain(**{ROLE_ANTENNA: ant(span_low_hz=4.0e10, span_high_hz=5.0e10)})
        )
        with self.assertRaises(ValueError):
            span_intersection(by_role)

    def test_a_chain_spanning_the_band_has_no_coverage_finding(self):
        intersection = span_intersection(collect_instrument_set(chain()))
        self.assertEqual(band_coverage_findings(intersection, BAND), [])

    def test_a_chain_short_at_the_top_names_the_item_bounding_it(self):
        by_role = collect_instrument_set(
            chain(**{ROLE_ANTENNA: ant(span_high_hz=5.0e8)})
        )
        findings = band_coverage_findings(span_intersection(by_role), BAND)
        self.assertEqual(len(findings), 1)
        self.assertIn("horn-a", findings[0])

    def test_an_inverted_band_is_rejected(self):
        intersection = span_intersection(collect_instrument_set(chain()))
        with self.assertRaises(ValueError):
            band_coverage_findings(intersection, (1.0e9, 1.0e8))


class TestPower(unittest.TestCase):
    def test_required_power_matches_the_independent_value(self):
        power = required_forward_power_w(20.0, 1.0, 6.0)
        self.assertAlmostEqual(power / REQUIRED_W, 1.0, places=9)

    def test_a_higher_gain_antenna_needs_less_power(self):
        low_gain = required_forward_power_w(20.0, 1.0, 0.0)
        high_gain = required_forward_power_w(20.0, 1.0, 10.0)
        self.assertLess(high_gain, low_gain / 5.0)

    def test_power_grows_with_the_square_of_the_separation(self):
        near = required_forward_power_w(20.0, 1.0, 6.0)
        far = required_forward_power_w(20.0, 2.0, 6.0)
        self.assertAlmostEqual(far / near, 4.0, places=9)

    def test_a_zero_separation_is_rejected(self):
        with self.assertRaises(ValueError):
            required_forward_power_w(20.0, 0.0, 6.0)

    def test_one_milliwatt_is_the_zero_of_the_dbm_scale(self):
        self.assertAlmostEqual(watts_to_dbm(1.0e-3), 0.0, places=9)

    def test_the_dbm_scale_round_trips(self):
        self.assertAlmostEqual(dbm_to_watts(watts_to_dbm(REQUIRED_W)) / REQUIRED_W, 1.0, places=9)

    def test_delivered_power_is_the_drive_less_the_feed_loss(self):
        delivered = delivered_power_dbm(gen(), amp(), 1.0)
        self.assertAlmostEqual(delivered["delivered_dbm"], 49.0, places=9)
        self.assertFalse(delivered["amplifier_saturated"])

    def test_drive_past_the_rating_is_capped_and_flagged(self):
        delivered = delivered_power_dbm(gen(output_dbm=10.0), amp(), 0.0)
        self.assertAlmostEqual(delivered["delivered_dbm"], 53.0, places=9)
        self.assertTrue(delivered["amplifier_saturated"])

    def test_a_negative_feed_loss_is_rejected(self):
        with self.assertRaises(ValueError):
            delivered_power_dbm(gen(), amp(), -1.0)

    def test_the_margin_is_delivered_less_required(self):
        self.assertAlmostEqual(power_margin_db(49.0, REQUIRED_DBM), 49.0 - REQUIRED_DBM, places=9)


class TestProbeAndCalibration(unittest.TestCase):
    def test_an_isotropic_probe_covering_the_field_has_no_finding(self):
        self.assertEqual(probe_findings(validate_instrument(probe()), 20.0), [])

    def test_a_directional_probe_is_reported(self):
        findings = probe_findings(validate_instrument(probe(is_isotropic=False)), 20.0)
        self.assertTrue(any("not isotropic" in f for f in findings))

    def test_a_probe_that_cannot_read_the_required_field_is_reported(self):
        findings = probe_findings(
            validate_instrument(probe(range_max_v_m=10.0)), 20.0
        )
        self.assertTrue(any("under the" in f for f in findings))

    def test_a_probe_whose_floor_sits_above_the_requirement_is_reported(self):
        findings = probe_findings(
            validate_instrument(probe(range_min_v_m=50.0, range_max_v_m=500.0)), 20.0
        )
        self.assertTrue(any("reads from" in f for f in findings))

    def test_calibration_covering_the_campaign_has_no_finding(self):
        by_role = collect_instrument_set(chain())
        self.assertEqual(calibration_findings(by_role, 120.0), [])

    def test_calibration_lapsing_inside_the_campaign_is_reported(self):
        by_role = collect_instrument_set(chain(**{ROLE_AMPLIFIER: amp(calibration_valid_days=30.0)}))
        findings = calibration_findings(by_role, 120.0)
        self.assertEqual(len(findings), 1)
        self.assertIn("amp-200w", findings[0])

    def test_calibration_reaching_the_last_day_of_the_campaign_is_accepted(self):
        by_role = collect_instrument_set(chain(**{ROLE_ANTENNA: ant(calibration_valid_days=120.0)}))
        self.assertEqual(calibration_findings(by_role, 120.0), [])


class TestFullAssessment(unittest.TestCase):
    def test_a_complete_chain_is_ready(self):
        report = assess_radiated_electric_susceptibility_equipment(
            chain(), requirement()
        )
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], READY)

    def test_a_missing_amplifier_stops_the_assessment(self):
        report = assess_radiated_electric_susceptibility_equipment(
            chain(**{ROLE_AMPLIFIER: None}), requirement()
        )
        self.assertEqual(report["absent_roles"], [ROLE_AMPLIFIER])
        self.assertIsNone(report["span_intersection"])
        self.assertEqual(report["verdict"], NOT_READY)

    def test_an_underpowered_chain_is_a_finding(self):
        report = assess_radiated_electric_susceptibility_equipment(
            chain(**{ROLE_AMPLIFIER: amp(gain_db=20.0, rated_output_dbm=25.0)}),
            requirement(),
        )
        self.assertTrue(any("shortfall" in f for f in report["findings"]))
        self.assertEqual(report["verdict"], NOT_READY)

    def test_a_chain_meeting_the_need_exactly_is_a_limitation_not_a_finding(self):
        report = assess_radiated_electric_susceptibility_equipment(
            chain(**{ROLE_AMPLIFIER: amp(gain_db=REQUIRED_DBM, rated_output_dbm=60.0)}),
            requirement(cable_loss_db=0.0),
        )
        self.assertAlmostEqual(report["power_margin_db"], 0.0, places=9)
        self.assertEqual(report["findings"], [])
        self.assertTrue(any("exactly" in m for m in report["limitations"]))
        self.assertEqual(report["verdict"], READY)

    def test_a_band_shortfall_fails_the_chain(self):
        report = assess_radiated_electric_susceptibility_equipment(
            chain(**{ROLE_ANTENNA: ant(span_high_hz=5.0e8)}), requirement()
        )
        self.assertTrue(any("band edge" in f for f in report["findings"]))
        self.assertEqual(report["verdict"], NOT_READY)

    def test_a_probe_that_cannot_read_the_exposure_fails_the_chain(self):
        report = assess_radiated_electric_susceptibility_equipment(
            chain(**{ROLE_PROBE: probe(range_max_v_m=10.0)}), requirement()
        )
        self.assertEqual(report["verdict"], NOT_READY)

    def test_a_lapsing_calibration_fails_the_chain(self):
        report = assess_radiated_electric_susceptibility_equipment(
            chain(**{ROLE_GENERATOR: gen(calibration_valid_days=10.0)}), requirement()
        )
        self.assertTrue(any("day campaign" in f for f in report["findings"]))

    def test_a_saturated_amplifier_is_a_limitation(self):
        report = assess_radiated_electric_susceptibility_equipment(
            chain(**{ROLE_GENERATOR: gen(output_dbm=10.0)}), requirement()
        )
        self.assertTrue(any("capped" in m for m in report["limitations"]))
        self.assertEqual(report["verdict"], READY)

    def test_a_requirement_missing_the_separation_is_rejected(self):
        record = requirement()
        del record["separation_m"]
        with self.assertRaises(ValueError):
            assess_radiated_electric_susceptibility_equipment(chain(), record)

    def test_the_report_carries_the_power_it_graded_against(self):
        report = assess_radiated_electric_susceptibility_equipment(
            chain(), requirement()
        )
        self.assertAlmostEqual(
            report["required_power"]["dbm"] / REQUIRED_DBM, 1.0, places=9
        )


if __name__ == "__main__":
    unittest.main()
