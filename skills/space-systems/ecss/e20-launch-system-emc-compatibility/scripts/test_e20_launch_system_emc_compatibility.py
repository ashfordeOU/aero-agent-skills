#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 6.3.2.2 launch system
electromagnetic environment and compatibility.

Exercises scripts/e20_launch_system_emc_compatibility_logic.py (stdlib
unittest, offline). Contract: a campaign phase maps to exactly one
half of the campaign and an unrecognized phase raises; a source maps to
exactly one category and an electrostatic source has no radiated field
model; the free-space field follows the far-field relation and is
attenuated by the fairing only while the vehicle is encapsulated; the
far-field boundary is the larger of the aperture term and the
wavelength term, and a source inside it is reported instead of scored;
a frequency outside every tested band yields no level and is reported;
a margin on the requirement to within the named tolerance is not a
finding while a real shortfall is; and the aggregated campaign is
compatible only when every finding list is empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_launch_system_emc_compatibility_logic as lc  # noqa: E402


def _range_radar():
    """A launch-site radar 300 m away whose free-space field at the
    spacecraft is exactly 30.0 V/m, and which sits beyond its own
    far-field boundary of about 149 m."""
    return {
        "source_id": "RNG-RADAR-1",
        "source_kind": "range_tracking_radar",
        "eirp_w": 2.7e6,
        "distance_m": 300.0,
        "frequency_hz": 5.6e9,
        "aperture_m": 2.0,
    }


def _facility_radio():
    return {
        "source_id": "FAC-WLAN-1",
        "source_kind": "facility_wireless_network",
        "eirp_w": 0.1,
        "distance_m": 5.0,
        "frequency_hz": 2.45e9,
        "aperture_m": 0.1,
    }


def _launcher_telemetry():
    return {
        "source_id": "LV-TM-1",
        "source_kind": "launcher_telemetry_transmitter",
        "eirp_w": 20.0,
        "distance_m": 3.0,
        "frequency_hz": 2.2e9,
        "aperture_m": 0.05,
    }


def _tribo_source(provision="bonded conductive path to structure"):
    source = {
        "source_id": "ESD-TRIBO-1",
        "source_kind": "triboelectric_charging",
    }
    if provision is not None:
        source["dissipation_provision"] = provision
    return source


def _qualification_levels():
    return [{"f_min_hz": 1.4e7, "f_max_hz": 1.8e10, "level_v_per_m": 30.0}]


def _clean_campaign():
    """A campaign that assesses every mandatory phase and passes every
    clause 6.3.2.2 check."""
    return {
        "campaign_id": "CAMP-01",
        "fairing_shielding_db": 10.0,
        "qualification_levels": _qualification_levels(),
        "phases": [
            {"phase": "payload_processing", "sources": [_facility_radio()]},
            {"phase": "encapsulation", "sources": []},
            {"phase": "on_pad_standby", "sources": [_range_radar()]},
            {"phase": "final_countdown", "sources": [_range_radar()]},
            {"phase": "liftoff", "sources": [_launcher_telemetry()]},
            {"phase": "atmospheric_ascent", "sources": [_launcher_telemetry()]},
            {"phase": "spacecraft_separation", "sources": [_tribo_source()]},
        ],
    }


class CategorizeLaunchPhaseTest(unittest.TestCase):
    def test_payload_processing_is_prelaunch(self):
        self.assertEqual(lc.categorize_launch_phase("payload_processing"), "prelaunch")

    def test_final_countdown_is_prelaunch(self):
        self.assertEqual(lc.categorize_launch_phase("final_countdown"), "prelaunch")

    def test_liftoff_is_launch(self):
        self.assertEqual(lc.categorize_launch_phase("liftoff"), "launch")

    def test_separation_is_launch(self):
        self.assertEqual(lc.categorize_launch_phase("spacecraft_separation"), "launch")

    def test_unrecognized_phase_raises(self):
        with self.assertRaises(ValueError):
            lc.categorize_launch_phase("orbit_raising")

    def test_the_two_phase_sets_do_not_overlap(self):
        self.assertEqual(lc.PRELAUNCH_PHASES & lc.LAUNCH_PHASES, frozenset())


class CategorizeEnvironmentSourceTest(unittest.TestCase):
    def test_tracking_radar_is_ground_fixed(self):
        self.assertEqual(
            lc.categorize_environment_source("range_tracking_radar"), "ground_fixed"
        )

    def test_launcher_telemetry_is_launcher_borne(self):
        self.assertEqual(
            lc.categorize_environment_source("launcher_telemetry_transmitter"),
            "launcher_borne",
        )

    def test_handheld_radio_is_a_facility_source(self):
        self.assertEqual(
            lc.categorize_environment_source("cleanroom_handheld_radio"), "facility"
        )

    def test_triboelectric_charging_is_electrostatic(self):
        self.assertEqual(
            lc.categorize_environment_source("triboelectric_charging"), "electrostatic"
        )

    def test_unrecognized_source_raises(self):
        with self.assertRaises(ValueError):
            lc.categorize_environment_source("solar_array_string")

    def test_electrostatic_is_not_an_emitter_category(self):
        self.assertNotIn("electrostatic", lc.EMITTER_CATEGORIES)


class EncapsulationTest(unittest.TestCase):
    def test_on_pad_standby_is_encapsulated(self):
        self.assertTrue(lc.is_encapsulated("on_pad_standby"))

    def test_payload_processing_is_not_encapsulated(self):
        self.assertFalse(lc.is_encapsulated("payload_processing"))

    def test_ascent_is_still_encapsulated(self):
        self.assertTrue(lc.is_encapsulated("atmospheric_ascent"))

    def test_jettison_exposes_the_spacecraft_again(self):
        self.assertFalse(lc.is_encapsulated("fairing_jettison"))

    def test_separation_is_not_encapsulated(self):
        self.assertFalse(lc.is_encapsulated("spacecraft_separation"))

    def test_unrecognized_phase_raises(self):
        with self.assertRaises(ValueError):
            lc.is_encapsulated("orbit_raising")


class FreeSpaceFieldTest(unittest.TestCase):
    def test_known_power_and_distance(self):
        self.assertAlmostEqual(lc.free_space_field_strength(2.7e6, 300.0), 30.0)

    def test_field_falls_inversely_with_distance(self):
        near = lc.free_space_field_strength(100.0, 10.0)
        far = lc.free_space_field_strength(100.0, 20.0)
        self.assertAlmostEqual(near / far, 2.0)

    def test_zero_power_gives_zero_field(self):
        self.assertAlmostEqual(lc.free_space_field_strength(0.0, 10.0), 0.0)

    def test_negative_power_raises(self):
        with self.assertRaises(ValueError):
            lc.free_space_field_strength(-1.0, 10.0)

    def test_zero_distance_raises(self):
        with self.assertRaises(ValueError):
            lc.free_space_field_strength(100.0, 0.0)

    def test_negative_distance_raises(self):
        with self.assertRaises(ValueError):
            lc.free_space_field_strength(100.0, -5.0)


class WavelengthAndFarFieldTest(unittest.TestCase):
    def test_wavelength_of_one_metre(self):
        self.assertAlmostEqual(lc.wavelength_m(lc.SPEED_OF_LIGHT_M_PER_S), 1.0)

    def test_wavelength_halves_when_frequency_doubles(self):
        self.assertAlmostEqual(
            lc.wavelength_m(1.0e9) / lc.wavelength_m(2.0e9), 2.0
        )

    def test_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            lc.wavelength_m(0.0)

    def test_aperture_term_governs_a_large_antenna(self):
        self.assertAlmostEqual(
            lc.far_field_distance_m(lc.SPEED_OF_LIGHT_M_PER_S, 10.0), 200.0
        )

    def test_wavelength_term_governs_a_small_antenna(self):
        self.assertAlmostEqual(
            lc.far_field_distance_m(lc.SPEED_OF_LIGHT_M_PER_S, 0.1), 3.0
        )

    def test_zero_aperture_falls_back_to_the_wavelength_term(self):
        self.assertAlmostEqual(
            lc.far_field_distance_m(lc.SPEED_OF_LIGHT_M_PER_S, 0.0), 3.0
        )

    def test_negative_aperture_raises(self):
        with self.assertRaises(ValueError):
            lc.far_field_distance_m(1.0e9, -1.0)

    def test_radar_boundary_sits_below_the_declared_distance(self):
        radar = _range_radar()
        boundary = lc.far_field_distance_m(radar["frequency_hz"], radar["aperture_m"])
        self.assertLess(boundary, radar["distance_m"])


class FairingAttenuationTest(unittest.TestCase):
    def test_twenty_decibels_divides_the_field_by_ten(self):
        self.assertAlmostEqual(lc.attenuated_field(30.0, 20.0), 3.0)

    def test_zero_shielding_leaves_the_field_alone(self):
        self.assertAlmostEqual(lc.attenuated_field(30.0, 0.0), 30.0)

    def test_zero_field_stays_zero(self):
        self.assertAlmostEqual(lc.attenuated_field(0.0, 15.0), 0.0)

    def test_negative_shielding_raises(self):
        with self.assertRaises(ValueError):
            lc.attenuated_field(30.0, -3.0)

    def test_negative_field_raises(self):
        with self.assertRaises(ValueError):
            lc.attenuated_field(-1.0, 10.0)


class IncidentFieldTest(unittest.TestCase):
    def test_encapsulated_phase_applies_the_fairing_attenuation(self):
        field = lc.incident_field_at_spacecraft(
            _range_radar(), "on_pad_standby", 20.0
        )
        self.assertAlmostEqual(field, 3.0)

    def test_unencapsulated_phase_does_not_attenuate(self):
        field = lc.incident_field_at_spacecraft(
            _range_radar(), "payload_processing", 20.0
        )
        self.assertAlmostEqual(field, 30.0)

    def test_after_jettison_the_field_is_unattenuated(self):
        field = lc.incident_field_at_spacecraft(
            _range_radar(), "fairing_jettison", 20.0
        )
        self.assertAlmostEqual(field, 30.0)

    def test_electrostatic_source_has_no_field_model(self):
        with self.assertRaises(ValueError):
            lc.incident_field_at_spacecraft(_tribo_source(), "liftoff", 10.0)

    def test_unrecognized_phase_raises(self):
        with self.assertRaises(ValueError):
            lc.incident_field_at_spacecraft(_range_radar(), "orbit_raising", 10.0)


class QualificationLookupTest(unittest.TestCase):
    def test_frequency_inside_the_band_returns_its_level(self):
        self.assertAlmostEqual(
            lc.qualification_level_at(2.2e9, _qualification_levels()), 30.0
        )

    def test_frequency_on_the_lower_edge_is_covered(self):
        self.assertAlmostEqual(
            lc.qualification_level_at(1.4e7, _qualification_levels()), 30.0
        )

    def test_frequency_above_the_envelope_returns_none(self):
        self.assertIsNone(
            lc.qualification_level_at(4.0e10, _qualification_levels())
        )

    def test_first_matching_band_wins(self):
        bands = [
            {"f_min_hz": 1.0e9, "f_max_hz": 3.0e9, "level_v_per_m": 50.0},
            {"f_min_hz": 2.0e9, "f_max_hz": 4.0e9, "level_v_per_m": 20.0},
        ]
        self.assertAlmostEqual(lc.qualification_level_at(2.5e9, bands), 50.0)

    def test_inverted_band_edges_raise(self):
        bands = [{"f_min_hz": 3.0e9, "f_max_hz": 1.0e9, "level_v_per_m": 50.0}]
        with self.assertRaises(ValueError):
            lc.qualification_level_at(2.0e9, bands)

    def test_non_positive_frequency_raises(self):
        with self.assertRaises(ValueError):
            lc.qualification_level_at(0.0, _qualification_levels())

    def test_empty_envelope_returns_none(self):
        self.assertIsNone(lc.qualification_level_at(2.0e9, []))


class MarginTest(unittest.TestCase):
    def test_decade_of_separation_is_twenty_decibels(self):
        self.assertAlmostEqual(
            lc.radiated_susceptibility_margin_db(30.0, 3.0), 20.0
        )

    def test_equal_levels_give_no_separation(self):
        self.assertAlmostEqual(
            lc.radiated_susceptibility_margin_db(20.0, 20.0), 0.0
        )

    def test_field_above_the_qualified_level_is_negative(self):
        self.assertLess(lc.radiated_susceptibility_margin_db(20.0, 40.0), 0.0)

    def test_zero_qualification_level_raises(self):
        with self.assertRaises(ValueError):
            lc.radiated_susceptibility_margin_db(0.0, 3.0)

    def test_zero_incident_field_raises(self):
        with self.assertRaises(ValueError):
            lc.radiated_susceptibility_margin_db(30.0, 0.0)


class PhaseCoverageTest(unittest.TestCase):
    def test_full_campaign_leaves_nothing_missing(self):
        declared = [e["phase"] for e in _clean_campaign()["phases"]]
        self.assertEqual(lc.missing_campaign_phases(declared), [])

    def test_absent_phase_is_reported(self):
        declared = [
            e["phase"]
            for e in _clean_campaign()["phases"]
            if e["phase"] != "payload_processing"
        ]
        self.assertEqual(
            lc.missing_campaign_phases(declared), ["payload_processing"]
        )

    def test_empty_campaign_reports_every_mandatory_phase(self):
        self.assertEqual(
            lc.missing_campaign_phases([]),
            sorted(lc.MANDATORY_CAMPAIGN_PHASES),
        )

    def test_custom_mandatory_set_is_honoured(self):
        self.assertEqual(
            lc.missing_campaign_phases(["liftoff"], {"liftoff", "fairing_jettison"}),
            ["fairing_jettison"],
        )

    def test_empty_mandatory_set_raises(self):
        with self.assertRaises(ValueError):
            lc.missing_campaign_phases(["liftoff"], set())


class SourceFindingsTest(unittest.TestCase):
    def test_compliant_emitter_produces_no_finding(self):
        findings = lc.source_findings(
            "on_pad_standby", _range_radar(), _qualification_levels(), 10.0
        )
        self.assertEqual(
            [k for k, v in findings.items() if v], []
        )

    def test_near_field_source_is_reported_and_not_scored(self):
        radar = _range_radar()
        radar["distance_m"] = 50.0
        findings = lc.source_findings(
            "on_pad_standby", radar, _qualification_levels(), 10.0
        )
        self.assertEqual(len(findings["near_field"]), 1)
        self.assertEqual(
            findings["near_field"][0]["issue"], "source_inside_far_field_boundary"
        )
        self.assertEqual(findings["field_margin"], [])
        self.assertEqual(findings["frequency_coverage"], [])

    def test_untested_frequency_is_reported_and_not_scored(self):
        # A small aperture keeps the emitter beyond its far-field
        # boundary at 40 GHz, so the frequency check is what fires.
        radar = _range_radar()
        radar["frequency_hz"] = 4.0e10
        radar["aperture_m"] = 0.05
        findings = lc.source_findings(
            "on_pad_standby", radar, _qualification_levels(), 10.0
        )
        self.assertEqual(findings["near_field"], [])
        self.assertEqual(len(findings["frequency_coverage"]), 1)
        self.assertEqual(
            findings["frequency_coverage"][0]["issue"],
            "frequency_outside_tested_susceptibility_envelope",
        )
        self.assertEqual(findings["field_margin"], [])

    def test_short_margin_is_reported(self):
        findings = lc.source_findings(
            "payload_processing",
            _range_radar(),
            _qualification_levels(),
            10.0,
            required_margin_db=6.0,
        )
        self.assertEqual(len(findings["field_margin"]), 1)
        self.assertAlmostEqual(findings["field_margin"][0]["margin_db"], 0.0)

    def test_margin_on_the_requirement_is_absorbed_at_the_boundary(self):
        # The radar puts exactly 30.0 V/m on the fairing and 10 dB of
        # shielding leaves exactly a tenth of the 30.0 V/m qualified
        # level, so the separation is nominally exactly 10 dB.
        #
        # Do NOT assert which side of the last bit it lands on. The value
        # is 20*log10() of a field built from 10**(-db/20), and neither
        # pow nor log10 is correctly rounded, so the rounding direction
        # differs between libm implementations: a few ULP BELOW ten on
        # macOS/arm64 and exactly ten on the Linux/x86-64 CI runner. A
        # strict assertLess here passes locally and fails in CI.
        # What matters, and what is portable, is that the case sits ON the
        # boundary and that the tolerance absorbs it into no finding.
        radar = _range_radar()
        incident = lc.incident_field_at_spacecraft(radar, "on_pad_standby", 10.0)
        raw = lc.radiated_susceptibility_margin_db(30.0, incident)
        self.assertAlmostEqual(raw, 10.0, places=9)
        findings = lc.source_findings(
            "on_pad_standby",
            radar,
            _qualification_levels(),
            10.0,
            required_margin_db=10.0,
        )
        self.assertEqual(findings["field_margin"], [])

    def test_a_real_shortfall_survives_the_tolerance(self):
        findings = lc.source_findings(
            "on_pad_standby",
            _range_radar(),
            _qualification_levels(),
            10.0,
            required_margin_db=12.0,
        )
        self.assertEqual(len(findings["field_margin"]), 1)

    def test_electrostatic_source_with_a_provision_passes(self):
        findings = lc.source_findings(
            "liftoff", _tribo_source(), _qualification_levels(), 10.0
        )
        self.assertEqual(findings["electrostatic_control"], [])

    def test_electrostatic_source_without_a_provision_is_reported(self):
        findings = lc.source_findings(
            "liftoff", _tribo_source(provision=None), _qualification_levels(), 10.0
        )
        self.assertEqual(len(findings["electrostatic_control"]), 1)
        self.assertEqual(
            findings["electrostatic_control"][0]["issue"],
            "missing_electrostatic_dissipation_provision",
        )

    def test_empty_provision_string_is_reported(self):
        findings = lc.source_findings(
            "liftoff", _tribo_source(provision=""), _qualification_levels(), 10.0
        )
        self.assertEqual(len(findings["electrostatic_control"]), 1)

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            lc.source_findings(
                "liftoff",
                _range_radar(),
                _qualification_levels(),
                10.0,
                tolerance_db=-1.0,
            )

    def test_unrecognized_phase_raises(self):
        with self.assertRaises(ValueError):
            lc.source_findings(
                "orbit_raising", _range_radar(), _qualification_levels(), 10.0
            )


class CampaignReviewTest(unittest.TestCase):
    def test_clean_campaign_is_compatible(self):
        review = lc.launch_campaign_review(_clean_campaign())
        self.assertTrue(lc.is_campaign_compatible(review))
        for key in (
            "phase_coverage",
            "near_field",
            "frequency_coverage",
            "field_margin",
            "electrostatic_control",
        ):
            self.assertEqual(review[key], [])

    def test_dropping_a_phase_breaks_coverage_only(self):
        campaign = _clean_campaign()
        campaign["phases"] = [
            e for e in campaign["phases"] if e["phase"] != "atmospheric_ascent"
        ]
        review = lc.launch_campaign_review(campaign)
        self.assertEqual(len(review["phase_coverage"]), 1)
        self.assertEqual(review["phase_coverage"][0]["phase"], "atmospheric_ascent")
        self.assertEqual(review["field_margin"], [])
        self.assertFalse(lc.is_campaign_compatible(review))

    def test_removing_the_fairing_shielding_breaks_the_margin(self):
        campaign = _clean_campaign()
        campaign["fairing_shielding_db"] = 0.0
        review = lc.launch_campaign_review(campaign)
        self.assertEqual(len(review["field_margin"]), 2)
        self.assertEqual(review["phase_coverage"], [])

    def test_missing_dissipation_provision_is_carried_through(self):
        campaign = _clean_campaign()
        campaign["phases"][-1]["sources"] = [_tribo_source(provision=None)]
        review = lc.launch_campaign_review(campaign)
        self.assertEqual(len(review["electrostatic_control"]), 1)
        self.assertFalse(lc.is_campaign_compatible(review))

    def test_narrow_envelope_reports_every_uncovered_source(self):
        campaign = _clean_campaign()
        campaign["qualification_levels"] = [
            {"f_min_hz": 1.0e9, "f_max_hz": 3.0e9, "level_v_per_m": 30.0}
        ]
        review = lc.launch_campaign_review(campaign)
        self.assertEqual(len(review["frequency_coverage"]), 2)

    def test_raising_the_requirement_reports_every_emitter(self):
        campaign = _clean_campaign()
        campaign["required_margin_db"] = 60.0
        review = lc.launch_campaign_review(campaign)
        self.assertEqual(len(review["field_margin"]), 5)

    def test_unrecognized_phase_raises_in_review(self):
        campaign = _clean_campaign()
        campaign["phases"][0]["phase"] = "orbit_raising"
        with self.assertRaises(ValueError):
            lc.launch_campaign_review(campaign)

    def test_review_does_not_mutate_input(self):
        campaign = _clean_campaign()
        snapshot = [
            (e["phase"], [dict(s) for s in e["sources"]]) for e in campaign["phases"]
        ]
        lc.launch_campaign_review(campaign)
        rebuilt = [
            (e["phase"], [dict(s) for s in e["sources"]]) for e in campaign["phases"]
        ]
        self.assertEqual(rebuilt, snapshot)

    def test_custom_mandatory_phase_set_is_used(self):
        campaign = _clean_campaign()
        campaign["mandatory_phases"] = {"liftoff"}
        review = lc.launch_campaign_review(campaign)
        self.assertEqual(review["phase_coverage"], [])

    def test_ascent_margin_matches_the_hand_calculation(self):
        telemetry = _launcher_telemetry()
        incident = lc.incident_field_at_spacecraft(
            telemetry, "atmospheric_ascent", 10.0
        )
        expected = (
            math.sqrt(30.0 * 20.0) / 3.0 / (10.0 ** 0.5)
        )
        self.assertAlmostEqual(incident, expected)


if __name__ == "__main__":
    unittest.main()
