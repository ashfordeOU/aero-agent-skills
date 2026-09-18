"""Contract tests for the masking, overspray and edge-coverage logic."""

import math
import unittest

from q7031_masking_and_edge_control_logic import (
    CHARACTERISTIC_EDGE_RADIUS_MM,
    CRITICALITY_SAFETY_FACTORS,
    MARGIN_TOLERANCE_MM,
    SHARP_EDGE_RETENTION,
    assess_edge,
    assess_masking_plan,
    assess_zone,
    criticality_safety_factor,
    edge_dry_thickness_um,
    edge_retention_factor,
    overspray_halo_mm,
    required_mask_margin_mm,
    stripe_coats_required,
    validate_fraction,
    validate_positive,
)

HALO = overspray_halo_mm(200.0, 60.0)


def zone(**overrides):
    base = {"name": "connector-face", "criticality": "bonding-electrical",
            "declared_mask_margin_mm": 400.0}
    base.update(overrides)
    return base


class ValidatorTests(unittest.TestCase):
    def test_positive_returns_float(self):
        self.assertEqual(validate_positive(3, "x"), 3.0)

    def test_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "x")

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(True, "x")

    def test_fraction_zero_accepted(self):
        self.assertEqual(validate_fraction(0.0, "f"), 0.0)

    def test_fraction_negative_rejected(self):
        with self.assertRaises(ValueError):
            validate_fraction(-0.1, "f")


class CriticalityTests(unittest.TestCase):
    def test_optical_earns_the_widest_clearance(self):
        widest = max(CRITICALITY_SAFETY_FACTORS.values())
        self.assertAlmostEqual(criticality_safety_factor("optical"), widest, places=12)

    def test_general_is_the_bare_halo(self):
        self.assertAlmostEqual(criticality_safety_factor("general"), 1.0, places=12)

    def test_lookup_is_case_insensitive(self):
        self.assertAlmostEqual(
            criticality_safety_factor("Sealing"),
            criticality_safety_factor("sealing"),
            places=12,
        )

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            criticality_safety_factor("nice-to-have")

    def test_non_string_category_rejected(self):
        with self.assertRaises(ValueError):
            criticality_safety_factor(2)


class OversprayTests(unittest.TestCase):
    def test_halo_is_the_pattern_half_width(self):
        self.assertAlmostEqual(
            overspray_halo_mm(200.0, 60.0), 200.0 * math.tan(math.radians(30.0)), places=9
        )

    def test_drift_inflates_the_halo(self):
        plain = overspray_halo_mm(200.0, 60.0)
        drifted = overspray_halo_mm(200.0, 60.0, 0.5)
        self.assertAlmostEqual(drifted, plain * 1.5, places=9)

    def test_standing_further_off_widens_the_halo(self):
        near = overspray_halo_mm(150.0, 60.0)
        far = overspray_halo_mm(300.0, 60.0)
        self.assertAlmostEqual(far, near * 2.0, places=9)

    def test_zero_distance_rejected(self):
        with self.assertRaises(ValueError):
            overspray_halo_mm(0.0, 60.0)

    def test_degenerate_fan_angle_rejected(self):
        with self.assertRaises(ValueError):
            overspray_halo_mm(200.0, 0.0)

    def test_straight_fan_angle_rejected(self):
        with self.assertRaises(ValueError):
            overspray_halo_mm(200.0, 180.0)

    def test_required_margin_scales_with_criticality(self):
        self.assertAlmostEqual(
            required_mask_margin_mm(100.0, "optical"), 300.0, places=12
        )


class ZoneTests(unittest.TestCase):
    def test_generous_mask_is_adequate(self):
        self.assertTrue(assess_zone(zone(declared_mask_margin_mm=1000.0), HALO)["adequate"])

    def test_mask_exactly_on_the_requirement_is_adequate(self):
        required = required_mask_margin_mm(HALO, "bonding-electrical")
        record = assess_zone(zone(declared_mask_margin_mm=required), HALO)
        self.assertTrue(record["adequate"])
        self.assertAlmostEqual(record["shortfall_mm"], 0.0, places=9)

    def test_short_mask_is_a_finding(self):
        record = assess_zone(zone(declared_mask_margin_mm=10.0), HALO)
        self.assertFalse(record["adequate"])
        self.assertEqual(len(record["findings"]), 1)

    def test_shortfall_is_reported(self):
        record = assess_zone(zone(declared_mask_margin_mm=10.0), HALO)
        required = required_mask_margin_mm(HALO, "bonding-electrical")
        self.assertAlmostEqual(record["shortfall_mm"], required - 10.0, places=9)

    def test_optical_zone_needs_more_than_a_general_one(self):
        optical = assess_zone(zone(criticality="optical"), HALO)
        general = assess_zone(zone(criticality="general"), HALO)
        self.assertAlmostEqual(
            optical["required_margin_mm"], general["required_margin_mm"] * 3.0, places=9
        )

    def test_missing_zone_key_rejected(self):
        broken = zone()
        del broken["criticality"]
        with self.assertRaises(ValueError):
            assess_zone(broken, HALO)

    def test_negative_declared_margin_rejected(self):
        with self.assertRaises(ValueError):
            assess_zone(zone(declared_mask_margin_mm=-1.0), HALO)


class EdgeTests(unittest.TestCase):
    def test_sharp_edge_holds_the_floor_fraction(self):
        self.assertAlmostEqual(edge_retention_factor(0.0), SHARP_EDGE_RETENTION, places=12)

    def test_characteristic_radius_recovers_half_the_shortfall(self):
        expected = SHARP_EDGE_RETENTION + (1.0 - SHARP_EDGE_RETENTION) * 0.5
        self.assertAlmostEqual(
            edge_retention_factor(CHARACTERISTIC_EDGE_RADIUS_MM), expected, places=12
        )

    def test_retention_rises_with_radius(self):
        self.assertTrue(edge_retention_factor(0.1) < edge_retention_factor(2.0) - 1e-3)

    def test_retention_never_reaches_the_flat_value(self):
        self.assertTrue(edge_retention_factor(1000.0) < 1.0)

    def test_negative_radius_rejected(self):
        with self.assertRaises(ValueError):
            edge_retention_factor(-0.1)

    def test_edge_thickness_is_nominal_times_retention(self):
        self.assertAlmostEqual(
            edge_dry_thickness_um(40.0, 0.5), 40.0 * edge_retention_factor(0.5), places=12
        )

    def test_no_stripe_coat_when_the_edge_already_makes_the_minimum(self):
        self.assertEqual(stripe_coats_required(40.0, 2.0, 20.0), 0)

    def test_sharp_edge_needs_stripe_coats(self):
        self.assertTrue(stripe_coats_required(30.0, 0.0, 20.0) >= 2)

    def test_stripe_count_closes_the_deficit(self):
        nominal, radius, minimum = 30.0, 0.0, 20.0
        n = stripe_coats_required(nominal, radius, minimum)
        per_coat = edge_dry_thickness_um(nominal, radius)
        self.assertTrue((n + 1) * per_coat >= minimum - MARGIN_TOLERANCE_MM)

    def test_edge_exactly_on_the_minimum_needs_no_stripe(self):
        nominal = 40.0
        minimum = edge_dry_thickness_um(nominal, 0.5)
        self.assertEqual(stripe_coats_required(nominal, 0.5, minimum), 0)

    def test_edge_record_is_covered_when_retention_suffices(self):
        record = assess_edge({"name": "rib-edge", "edge_radius_mm": 3.0}, 40.0, 20.0)
        self.assertTrue(record["covered"])

    def test_edge_record_raises_a_finding_when_it_does_not(self):
        record = assess_edge({"name": "knife-edge", "edge_radius_mm": 0.0}, 30.0, 25.0)
        self.assertFalse(record["covered"])
        self.assertEqual(len(record["findings"]), 1)

    def test_missing_edge_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_edge({"name": "rib-edge"}, 40.0, 20.0)


class MaskingPlanTests(unittest.TestCase):
    def test_contained_plan(self):
        result = assess_masking_plan(
            {
                "gun_distance_mm": 200.0,
                "fan_angle_deg": 60.0,
                "zones": [zone(declared_mask_margin_mm=1000.0)],
            }
        )
        self.assertTrue(result["contained"])
        self.assertEqual(result["findings"], [])

    def test_short_mask_breaks_containment(self):
        result = assess_masking_plan(
            {
                "gun_distance_mm": 200.0,
                "fan_angle_deg": 60.0,
                "zones": [zone(declared_mask_margin_mm=5.0)],
            }
        )
        self.assertFalse(result["contained"])

    def test_halo_is_reported(self):
        result = assess_masking_plan(
            {"gun_distance_mm": 200.0, "fan_angle_deg": 60.0, "zones": [zone()]}
        )
        self.assertAlmostEqual(result["overspray_halo_mm"], HALO, places=12)

    def test_duplicate_zone_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_masking_plan(
                {
                    "gun_distance_mm": 200.0,
                    "fan_angle_deg": 60.0,
                    "zones": [zone(), zone()],
                }
            )

    def test_edges_need_the_thickness_context(self):
        with self.assertRaises(ValueError):
            assess_masking_plan(
                {
                    "gun_distance_mm": 200.0,
                    "fan_angle_deg": 60.0,
                    "zones": [zone(declared_mask_margin_mm=1000.0)],
                    "edges": [{"name": "knife-edge", "edge_radius_mm": 0.0}],
                }
            )

    def test_edge_findings_join_the_plan_findings(self):
        result = assess_masking_plan(
            {
                "gun_distance_mm": 200.0,
                "fan_angle_deg": 60.0,
                "zones": [zone(declared_mask_margin_mm=1000.0)],
                "edges": [{"name": "knife-edge", "edge_radius_mm": 0.0}],
                "nominal_dft_um": 30.0,
                "min_edge_dft_um": 25.0,
            }
        )
        self.assertFalse(result["contained"])
        self.assertEqual(len(result["edges"]), 1)

    def test_empty_zone_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_masking_plan(
                {"gun_distance_mm": 200.0, "fan_angle_deg": 60.0, "zones": []}
            )

    def test_missing_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_masking_plan({"gun_distance_mm": 200.0, "zones": [zone()]})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_masking_plan([zone()])


if __name__ == "__main__":
    unittest.main(verbosity=1)
