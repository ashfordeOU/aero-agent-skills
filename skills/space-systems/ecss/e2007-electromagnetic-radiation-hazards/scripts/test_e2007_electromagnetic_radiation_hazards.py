#!/usr/bin/env python3
"""Gate 3 contract test for e2007-electromagnetic-radiation-hazards.

Offline, deterministic, standard library only. Run:
    python3 test_e2007_electromagnetic_radiation_hazards.py
"""

import math
import unittest

from e2007_electromagnetic_radiation_hazards_logic import (
    SEVERITY_INHIBITS,
    assess_electromagnetic_radiation_hazards,
    categorize_receptor,
    check_hazard_analysis_linkage,
    derated_allowable,
    evaluate_radiation_hazard_case,
    field_strength_v_per_m,
    linear_gain,
    near_field_boundary_m,
    power_flux_density_w_per_m2,
    safe_separation_distance_m,
    wavelength_m,
)

# A compact emitter whose near-field boundary is well inside any stand-off
# distance used below (aperture 0.1 m at 2.2 GHz -> boundary 0.1468 m).
EMITTER = {
    "emitter_id": "TX-S-BAND",
    "power_w": 5.0,
    "gain_dbi": 0.0,
    "frequency_hz": 2.2e9,
    "aperture_m": 0.1,
}

# A large reflector whose near-field boundary is 76.85 m.
BIG_EMITTER = {
    "emitter_id": "TX-X-REFLECTOR",
    "power_w": 200.0,
    "gain_dbi": 40.0,
    "frequency_hz": 8.0e9,
    "aperture_m": 1.2,
}


def ordnance(**overrides):
    case = {
        "receptor_id": "EED-SEP-NUT",
        "receptor_type": "electro-explosive-device",
        "threshold": 24.436872873390443,
        "distance_m": 10.0,
        "hazard_report_id": "HR-0142",
        "severity": "catastrophic",
        "independent_inhibits": 2,
    }
    case.update(overrides)
    return case


class TestGainAndWavelength(unittest.TestCase):
    def test_isotropic_gain_is_unity(self):
        self.assertAlmostEqual(linear_gain(0.0), 1.0)

    def test_ten_decibel_gain_is_ten(self):
        self.assertAlmostEqual(linear_gain(10.0), 10.0)

    def test_twenty_decibel_gain_is_one_hundred(self):
        self.assertAlmostEqual(linear_gain(20.0), 100.0)

    def test_negative_gain_is_a_fraction(self):
        self.assertAlmostEqual(linear_gain(-3.0), 0.5011872336272722)

    def test_non_numeric_gain_raises(self):
        with self.assertRaises(ValueError):
            linear_gain("10 dBi")

    def test_wavelength_at_three_hundred_megahertz(self):
        self.assertAlmostEqual(wavelength_m(300.0e6), 0.9993081933333333)

    def test_non_positive_frequency_raises(self):
        with self.assertRaises(ValueError):
            wavelength_m(0.0)


class TestNearFieldBoundary(unittest.TestCase):
    def test_large_aperture_is_governed_by_the_radiating_term(self):
        self.assertAlmostEqual(
            near_field_boundary_m(2.0, 1.0e10), 266.85127615852167, places=6
        )

    def test_tiny_aperture_at_low_frequency_is_governed_by_the_wavelength_term(self):
        self.assertAlmostEqual(
            near_field_boundary_m(0.02, 1.0e8), 0.4771345159236942, places=9
        )

    def test_compact_emitter_boundary(self):
        self.assertAlmostEqual(
            near_field_boundary_m(0.1, 2.2e9), 0.1467682018871869, places=9
        )

    def test_non_positive_aperture_raises(self):
        with self.assertRaises(ValueError):
            near_field_boundary_m(0.0, 2.2e9)

    def test_non_positive_frequency_raises(self):
        with self.assertRaises(ValueError):
            near_field_boundary_m(0.5, -1.0)


class TestFieldAndFlux(unittest.TestCase):
    def test_known_field_strength(self):
        self.assertAlmostEqual(field_strength_v_per_m(30.0, 0.0, 10.0), 3.0)

    def test_field_scales_inversely_with_distance(self):
        near = field_strength_v_per_m(30.0, 0.0, 5.0)
        far = field_strength_v_per_m(30.0, 0.0, 10.0)
        self.assertAlmostEqual(near / far, 2.0)

    def test_gain_enters_the_field_as_a_square_root(self):
        plain = field_strength_v_per_m(30.0, 0.0, 10.0)
        boosted = field_strength_v_per_m(30.0, 10.0, 10.0)
        self.assertAlmostEqual(boosted / plain, math.sqrt(10.0))

    def test_zero_distance_raises_for_field(self):
        with self.assertRaises(ValueError):
            field_strength_v_per_m(30.0, 0.0, 0.0)

    def test_non_positive_power_raises_for_field(self):
        with self.assertRaises(ValueError):
            field_strength_v_per_m(-1.0, 0.0, 10.0)

    def test_known_power_flux_density(self):
        self.assertAlmostEqual(
            power_flux_density_w_per_m2(4.0 * math.pi, 0.0, 1.0), 1.0
        )

    def test_flux_scales_with_inverse_square(self):
        near = power_flux_density_w_per_m2(100.0, 0.0, 10.0)
        far = power_flux_density_w_per_m2(100.0, 0.0, 20.0)
        self.assertAlmostEqual(near / far, 4.0)

    def test_flux_matches_a_hand_computed_case(self):
        self.assertAlmostEqual(
            power_flux_density_w_per_m2(100.0, 20.0, 50.0), 0.3183098861837907
        )

    def test_non_positive_distance_raises_for_flux(self):
        with self.assertRaises(ValueError):
            power_flux_density_w_per_m2(100.0, 0.0, -5.0)


class TestReceptorCategorization(unittest.TestCase):
    def test_ordnance_is_a_field_family_with_the_largest_margin(self):
        record = categorize_receptor("electro-explosive-device")
        self.assertEqual(record["quantity"], "field")
        self.assertAlmostEqual(record["margin_db"], 20.0)

    def test_ground_crew_is_a_flux_family(self):
        record = categorize_receptor("ground-crew")
        self.assertEqual(record["quantity"], "flux")
        self.assertAlmostEqual(record["margin_db"], 10.0)

    def test_propellant_vapour_is_a_field_family(self):
        record = categorize_receptor("propellant-vapour")
        self.assertEqual(record["quantity"], "field")
        self.assertAlmostEqual(record["margin_db"], 6.0)

    def test_lookup_ignores_case_and_padding(self):
        record = categorize_receptor("  Ground-Crew  ")
        self.assertEqual(record["receptor_type"], "ground-crew")

    def test_unknown_receptor_type_raises(self):
        with self.assertRaises(ValueError):
            categorize_receptor("star-tracker")

    def test_non_string_receptor_type_raises(self):
        with self.assertRaises(ValueError):
            categorize_receptor(7)


class TestDerating(unittest.TestCase):
    def test_twenty_decibel_field_margin_divides_by_ten(self):
        self.assertAlmostEqual(derated_allowable(50.0, 20.0, "field"), 5.0)

    def test_ten_decibel_flux_margin_divides_by_ten(self):
        self.assertAlmostEqual(derated_allowable(50.0, 10.0, "flux"), 5.0)

    def test_six_decibel_field_margin_halves(self):
        self.assertAlmostEqual(derated_allowable(50.0, 6.0206, "field"), 25.0, places=3)

    def test_zero_margin_returns_the_threshold(self):
        self.assertAlmostEqual(derated_allowable(12.5, 0.0, "field"), 12.5)

    def test_negative_margin_raises(self):
        with self.assertRaises(ValueError):
            derated_allowable(12.5, -1.0, "field")

    def test_unknown_quantity_raises(self):
        with self.assertRaises(ValueError):
            derated_allowable(12.5, 6.0, "current")

    def test_non_positive_threshold_raises(self):
        with self.assertRaises(ValueError):
            derated_allowable(0.0, 6.0, "field")


class TestSafeSeparation(unittest.TestCase):
    def test_field_separation_reproduces_the_allowable(self):
        distance = safe_separation_distance_m(30.0, 0.0, 3.0, "field")
        self.assertAlmostEqual(distance, 10.0)

    def test_flux_separation_reproduces_the_allowable(self):
        distance = safe_separation_distance_m(4.0 * math.pi, 0.0, 1.0, "flux")
        self.assertAlmostEqual(distance, 1.0)

    def test_tighter_allowable_pushes_the_separation_out(self):
        loose = safe_separation_distance_m(30.0, 0.0, 3.0, "field")
        tight = safe_separation_distance_m(30.0, 0.0, 0.3, "field")
        self.assertAlmostEqual(tight / loose, 10.0)

    def test_unknown_quantity_raises(self):
        with self.assertRaises(ValueError):
            safe_separation_distance_m(30.0, 0.0, 3.0, "voltage")

    def test_non_positive_allowable_raises(self):
        with self.assertRaises(ValueError):
            safe_separation_distance_m(30.0, 0.0, 0.0, "field")


class TestHazardAnalysisLinkage(unittest.TestCase):
    def test_complete_linkage_has_no_findings(self):
        self.assertEqual(check_hazard_analysis_linkage(ordnance()), [])

    def test_missing_hazard_report_identifier_is_a_finding(self):
        findings = check_hazard_analysis_linkage(ordnance(hazard_report_id=""))
        self.assertEqual(len(findings), 1)
        self.assertIn("hazard-report", findings[0])

    def test_absent_hazard_report_key_is_a_finding(self):
        case = ordnance()
        del case["hazard_report_id"]
        self.assertEqual(len(check_hazard_analysis_linkage(case)), 1)

    def test_unrecognised_severity_is_a_finding(self):
        findings = check_hazard_analysis_linkage(ordnance(severity="annoying"))
        self.assertEqual(len(findings), 1)
        self.assertIn("severity", findings[0])

    def test_catastrophic_needs_two_independent_inhibits(self):
        findings = check_hazard_analysis_linkage(ordnance(independent_inhibits=1))
        self.assertEqual(len(findings), 1)
        self.assertIn("independent inhibit", findings[0])

    def test_critical_needs_two_independent_inhibits(self):
        self.assertEqual(SEVERITY_INHIBITS["critical"], 2)
        findings = check_hazard_analysis_linkage(
            ordnance(severity="critical", independent_inhibits=2)
        )
        self.assertEqual(findings, [])

    def test_major_needs_one_independent_inhibit(self):
        self.assertEqual(
            check_hazard_analysis_linkage(
                ordnance(severity="major", independent_inhibits=1)
            ),
            [],
        )

    def test_minor_needs_no_independent_inhibit(self):
        self.assertEqual(
            check_hazard_analysis_linkage(
                ordnance(severity="minor", independent_inhibits=0)
            ),
            [],
        )

    def test_non_integer_inhibit_count_raises(self):
        with self.assertRaises(ValueError):
            check_hazard_analysis_linkage(ordnance(independent_inhibits=1.5))

    def test_negative_inhibit_count_raises(self):
        with self.assertRaises(ValueError):
            check_hazard_analysis_linkage(ordnance(independent_inhibits=-1))


class TestEvaluateCase(unittest.TestCase):
    def test_compliant_ordnance_case(self):
        result = evaluate_radiation_hazard_case(EMITTER, ordnance(threshold=500.0))
        self.assertEqual(result["status"], "compliant")
        self.assertEqual(result["quantity"], "field")
        self.assertAlmostEqual(result["computed"], 1.224744871391589)
        self.assertAlmostEqual(result["allowable"], 50.0)
        self.assertAlmostEqual(result["separation_shortfall_m"], 0.0)
        self.assertEqual(result["linkage_findings"], [])

    def test_exceeded_ordnance_case_reports_the_shortfall(self):
        result = evaluate_radiation_hazard_case(EMITTER, ordnance(threshold=2.0))
        self.assertEqual(result["status"], "exceeded")
        self.assertAlmostEqual(result["allowable"], 0.2)
        self.assertAlmostEqual(result["safe_separation_m"], 61.23724356957945, places=6)
        self.assertGreater(result["separation_shortfall_m"], 51.0)
        self.assertIsNotNone(result["finding"])

    def test_exact_allowable_is_compliant_despite_float_error(self):
        # Field at 10 m from a 5 W isotropic emitter is 1.224744871391589 V/m.
        # A 2.4436872873390443 V/m threshold derated by 6 dB lands on exactly
        # that value, and the decade conversion leaves it a few ULPs low.
        result = evaluate_radiation_hazard_case(
            EMITTER,
            ordnance(threshold=2.4436872873390443, margin_db=6.0),
        )
        self.assertEqual(result["status"], "compliant")
        self.assertAlmostEqual(result["computed"], result["allowable"], places=12)

    def test_one_percent_above_the_allowable_is_exceeded(self):
        result = evaluate_radiation_hazard_case(
            EMITTER,
            ordnance(threshold=2.4193, margin_db=6.0),
        )
        self.assertEqual(result["status"], "exceeded")

    def test_ground_crew_case_uses_the_flux_quantity(self):
        receptor = {
            "receptor_id": "PAD-CREW",
            "receptor_type": "ground-crew",
            "threshold": 100.0,
            "distance_m": 10.0,
            "hazard_report_id": "HR-0201",
            "severity": "critical",
            "independent_inhibits": 2,
        }
        result = evaluate_radiation_hazard_case(EMITTER, receptor)
        self.assertEqual(result["quantity"], "flux")
        self.assertAlmostEqual(result["computed"], 0.003978873577297384, places=12)
        self.assertAlmostEqual(result["allowable"], 10.0)
        self.assertEqual(result["status"], "compliant")

    def test_receptor_inside_the_near_field_is_not_evaluated(self):
        result = evaluate_radiation_hazard_case(BIG_EMITTER, ordnance(distance_m=10.0))
        self.assertEqual(result["status"], "near-field-invalid")
        self.assertIsNone(result["computed"])
        self.assertIsNone(result["allowable"])
        self.assertAlmostEqual(result["near_field_boundary_m"], 76.85316753365423, places=6)

    def test_margin_override_is_honoured(self):
        default_case = evaluate_radiation_hazard_case(EMITTER, ordnance(threshold=100.0))
        override = evaluate_radiation_hazard_case(
            EMITTER, ordnance(threshold=100.0, margin_db=0.0)
        )
        self.assertAlmostEqual(default_case["allowable"], 10.0)
        self.assertAlmostEqual(override["allowable"], 100.0)

    def test_missing_emitter_field_raises(self):
        emitter = dict(EMITTER)
        del emitter["aperture_m"]
        with self.assertRaises(ValueError):
            evaluate_radiation_hazard_case(emitter, ordnance())

    def test_missing_receptor_field_raises(self):
        case = ordnance()
        del case["distance_m"]
        with self.assertRaises(ValueError):
            evaluate_radiation_hazard_case(EMITTER, case)

    def test_non_positive_distance_raises(self):
        with self.assertRaises(ValueError):
            evaluate_radiation_hazard_case(EMITTER, ordnance(distance_m=0.0))

    def test_unknown_receptor_type_raises(self):
        with self.assertRaises(ValueError):
            evaluate_radiation_hazard_case(
                EMITTER, ordnance(receptor_type="reaction-wheel")
            )


class TestAssessment(unittest.TestCase):
    def setUp(self):
        self.receptors = [
            ordnance(threshold=500.0),
            {
                "receptor_id": "PAD-CREW",
                "receptor_type": "ground-crew",
                "threshold": 100.0,
                "distance_m": 12.0,
                "hazard_report_id": "HR-0201",
                "severity": "critical",
                "independent_inhibits": 2,
            },
        ]

    def test_all_clear_assessment(self):
        out = assess_electromagnetic_radiation_hazards(EMITTER, self.receptors)
        self.assertTrue(out["hazard_compliant"])
        self.assertEqual(len(out["cases"]), 2)
        self.assertEqual(out["exceeded_cases"], [])
        self.assertEqual(out["linkage_gaps"], [])

    def test_linkage_gap_alone_breaks_compliance(self):
        receptors = [ordnance(threshold=500.0, hazard_report_id=""), self.receptors[1]]
        out = assess_electromagnetic_radiation_hazards(EMITTER, receptors)
        self.assertFalse(out["hazard_compliant"])
        self.assertEqual(out["exceeded_cases"], [])
        self.assertEqual(len(out["linkage_gaps"]), 1)

    def test_exceeded_case_is_listed(self):
        receptors = [ordnance(threshold=2.0), self.receptors[1]]
        out = assess_electromagnetic_radiation_hazards(EMITTER, receptors)
        self.assertFalse(out["hazard_compliant"])
        self.assertEqual(len(out["exceeded_cases"]), 1)

    def test_near_field_case_is_listed_separately(self):
        out = assess_electromagnetic_radiation_hazards(BIG_EMITTER, self.receptors)
        self.assertFalse(out["hazard_compliant"])
        self.assertEqual(len(out["near_field_invalid"]), 2)

    def test_empty_receptor_set_raises(self):
        with self.assertRaises(ValueError):
            assess_electromagnetic_radiation_hazards(EMITTER, [])

    def test_duplicate_receptor_identifier_raises(self):
        with self.assertRaises(ValueError):
            assess_electromagnetic_radiation_hazards(
                EMITTER, [ordnance(threshold=500.0), ordnance(threshold=400.0)]
            )

    def test_non_mapping_receptor_raises(self):
        with self.assertRaises(ValueError):
            assess_electromagnetic_radiation_hazards(EMITTER, ["EED-SEP-NUT"])


if __name__ == "__main__":
    unittest.main()
