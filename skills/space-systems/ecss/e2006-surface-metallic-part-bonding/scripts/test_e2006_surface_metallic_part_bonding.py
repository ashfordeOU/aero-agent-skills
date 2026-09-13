#!/usr/bin/env python3
"""Gate 3 contract test for e2006-surface-metallic-part-bonding."""

import unittest

from e2006_surface_metallic_part_bonding_logic import (
    BOND_CATEGORY_LIMITS_OHM,
    assess_bonding_network,
    bond_category_limit,
    build_bond_network,
    collected_current,
    effective_resistance_to_reference,
    evaluate_part_bond,
    parallel_resistance,
    quasi_static_potential,
    series_resistance,
    strap_inductance,
    transient_bond_potential,
    within_limit,
)

REFERENCE = "spacecraft-structure"
J_GEO = 1.0e-6  # A/m^2


def sample_parts():
    return [
        {"id": "primary-truss", "category": "primary-structure", "exposed_area_m2": 0.5},
        {"id": "antenna-bracket", "category": "secondary-structure", "exposed_area_m2": 0.1},
        {"id": "solar-wing-hinge", "category": "mechanism-metal", "exposed_area_m2": 0.05},
        {"id": "handrail-fitting", "category": "electrostatic-bleed", "exposed_area_m2": 0.02},
    ]


def sample_bonds():
    return [
        {"from": "primary-truss", "to": REFERENCE, "resistance_ohm": 1.0e-3},
        {"from": "antenna-bracket", "to": "primary-truss", "resistance_ohm": 5.0e-3},
        {"from": "solar-wing-hinge", "to": "antenna-bracket", "resistance_ohm": 2.0e-2},
        {"from": "handrail-fitting", "to": REFERENCE, "resistance_ohm": 0.5},
    ]


class RatioMixin(unittest.TestCase):
    def assertRatio(self, value, expected, places=12):
        self.assertAlmostEqual(value / expected, 1.0, places=places)


class TestCategoryLimits(RatioMixin):
    def test_every_category_has_a_positive_ceiling(self):
        for category, limit in BOND_CATEGORY_LIMITS_OHM.items():
            self.assertGreater(limit, 0.0, category)

    def test_bleed_ceiling_is_looser_than_primary_structure(self):
        self.assertGreater(
            bond_category_limit("electrostatic-bleed"),
            bond_category_limit("primary-structure"),
        )

    def test_unknown_category_is_rejected(self):
        with self.assertRaises(ValueError):
            bond_category_limit("chassis-bond")

    def test_non_string_category_is_rejected(self):
        with self.assertRaises(ValueError):
            bond_category_limit(2.5e-3)


class TestSeriesAndParallel(RatioMixin):
    def test_series_adds(self):
        self.assertRatio(series_resistance([1.0e-3, 2.0e-3, 5.0e-4]), 3.5e-3)

    def test_series_accepts_a_zero_joint(self):
        self.assertRatio(series_resistance([1.0e-3, 0.0]), 1.0e-3)

    def test_series_rejects_empty(self):
        with self.assertRaises(ValueError):
            series_resistance([])

    def test_series_rejects_a_negative_segment(self):
        with self.assertRaises(ValueError):
            series_resistance([1.0e-3, -1.0e-4])

    def test_two_equal_straps_halve_the_resistance(self):
        self.assertRatio(parallel_resistance([4.0e-3, 4.0e-3]), 2.0e-3)

    def test_parallel_never_exceeds_the_better_strap(self):
        combined = parallel_resistance([1.0e-3, 1.0])
        self.assertLess(combined, 1.0e-3)
        self.assertGreater(combined, 0.0)

    def test_parallel_rejects_a_zero_strap(self):
        with self.assertRaises(ValueError):
            parallel_resistance([1.0e-3, 0.0])

    def test_parallel_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            parallel_resistance(1.0e-3)


class TestStrapInductance(RatioMixin):
    def test_inductance_is_in_the_expected_decade(self):
        value = strap_inductance(0.3, 0.02)
        self.assertGreater(value, 1.0e-7)
        self.assertLess(value, 1.0e-6)

    def test_longer_strap_has_more_inductance(self):
        self.assertGreater(strap_inductance(0.6, 0.02), strap_inductance(0.3, 0.02))

    def test_wider_strap_has_less_inductance(self):
        self.assertLess(strap_inductance(0.3, 0.05), strap_inductance(0.3, 0.02))

    def test_strap_shorter_than_its_width_is_rejected(self):
        with self.assertRaises(ValueError):
            strap_inductance(0.01, 0.02)

    def test_zero_width_is_rejected(self):
        with self.assertRaises(ValueError):
            strap_inductance(0.3, 0.0)


class TestPotentials(RatioMixin):
    def test_collected_current_scales_with_area(self):
        self.assertRatio(collected_current(J_GEO, 0.5), 5.0e-7)

    def test_collected_current_rejects_zero_area(self):
        with self.assertRaises(ValueError):
            collected_current(J_GEO, 0.0)

    def test_quasi_static_potential_is_ohms_law(self):
        self.assertRatio(quasi_static_potential(5.0e-7, 1.0e-3), 5.0e-10)

    def test_quasi_static_potential_rejects_negative_current(self):
        with self.assertRaises(ValueError):
            quasi_static_potential(-1.0e-7, 1.0e-3)

    def test_transient_without_inductance_is_resistive_only(self):
        self.assertRatio(transient_bond_potential(10.0, 1.0e-8, 1.0e-3), 1.0e-2)

    def test_inductive_term_dominates_a_fast_event(self):
        inductance = strap_inductance(0.3, 0.02)
        resistive = transient_bond_potential(10.0, 1.0e-8, 1.0e-3)
        full = transient_bond_potential(10.0, 1.0e-8, 1.0e-3, inductance_h=inductance)
        self.assertGreater(full, 100.0 * resistive)

    def test_slower_rise_time_lowers_the_transient(self):
        fast = transient_bond_potential(10.0, 1.0e-8, 1.0e-3, inductance_h=2.0e-7)
        slow = transient_bond_potential(10.0, 1.0e-6, 1.0e-3, inductance_h=2.0e-7)
        self.assertGreater(fast, slow)

    def test_zero_rise_time_is_rejected(self):
        with self.assertRaises(ValueError):
            transient_bond_potential(10.0, 0.0, 1.0e-3)

    def test_negative_inductance_is_rejected(self):
        with self.assertRaises(ValueError):
            transient_bond_potential(10.0, 1.0e-8, 1.0e-3, inductance_h=-1.0e-9)


class TestLimitComparison(RatioMixin):
    def test_below_limit_passes(self):
        self.assertTrue(within_limit(1.0e-3, 2.5e-3))

    def test_above_limit_fails(self):
        self.assertFalse(within_limit(5.0e-3, 2.5e-3))

    def test_exact_limit_passes(self):
        self.assertTrue(within_limit(2.5e-3, 2.5e-3))

    def test_summed_route_drift_is_absorbed(self):
        drifted = 1.0e-3 + 1.5e-3  # sum of powers of ten, may drift a few ULPs
        self.assertTrue(within_limit(drifted, 2.5e-3))

    def test_drift_absorption_does_not_relax_the_ceiling(self):
        self.assertFalse(within_limit(2.5e-3 * (1.0 + 1.0e-6), 2.5e-3))


class TestNetworkConstruction(RatioMixin):
    def test_network_is_symmetric(self):
        network = build_bond_network(sample_parts(), sample_bonds(), REFERENCE)
        self.assertRatio(network["primary-truss"][REFERENCE], network[REFERENCE]["primary-truss"])

    def test_redundant_straps_combine_in_parallel(self):
        bonds = sample_bonds()
        bonds.append({"from": REFERENCE, "to": "primary-truss", "resistance_ohm": 1.0e-3})
        network = build_bond_network(sample_parts(), bonds, REFERENCE)
        self.assertRatio(network["primary-truss"][REFERENCE], 5.0e-4)

    def test_unknown_endpoint_is_rejected(self):
        bonds = sample_bonds()
        bonds.append({"from": "shear-panel", "to": REFERENCE, "resistance_ohm": 1.0e-3})
        with self.assertRaises(ValueError):
            build_bond_network(sample_parts(), bonds, REFERENCE)

    def test_self_looping_bond_is_rejected(self):
        bonds = sample_bonds()
        bonds.append({"from": "primary-truss", "to": "primary-truss", "resistance_ohm": 1.0e-3})
        with self.assertRaises(ValueError):
            build_bond_network(sample_parts(), bonds, REFERENCE)

    def test_duplicate_part_id_is_rejected(self):
        parts = sample_parts()
        parts[1]["id"] = "primary-truss"
        with self.assertRaises(ValueError):
            build_bond_network(parts, sample_bonds(), REFERENCE)

    def test_part_named_like_the_reference_is_rejected(self):
        parts = sample_parts()
        parts[0]["id"] = REFERENCE
        with self.assertRaises(ValueError):
            build_bond_network(parts, sample_bonds(), REFERENCE)

    def test_unknown_part_key_is_rejected(self):
        parts = sample_parts()
        parts[0]["mass_kg"] = 3.0
        with self.assertRaises(ValueError):
            build_bond_network(parts, sample_bonds(), REFERENCE)

    def test_bond_missing_resistance_is_rejected(self):
        bonds = sample_bonds()
        del bonds[0]["resistance_ohm"]
        with self.assertRaises(ValueError):
            build_bond_network(sample_parts(), bonds, REFERENCE)

    def test_negative_bond_resistance_is_rejected(self):
        bonds = sample_bonds()
        bonds[0]["resistance_ohm"] = -1.0e-3
        with self.assertRaises(ValueError):
            build_bond_network(sample_parts(), bonds, REFERENCE)

    def test_reference_absent_from_every_bond_is_rejected(self):
        bonds = [
            {"from": "antenna-bracket", "to": "primary-truss", "resistance_ohm": 5.0e-3},
            {"from": "solar-wing-hinge", "to": "antenna-bracket", "resistance_ohm": 2.0e-2},
        ]
        with self.assertRaises(ValueError):
            build_bond_network(sample_parts(), bonds, REFERENCE)

    def test_empty_parts_is_rejected(self):
        with self.assertRaises(ValueError):
            build_bond_network([], sample_bonds(), REFERENCE)


class TestRouteResolution(RatioMixin):
    def test_reference_is_its_own_datum(self):
        network = build_bond_network(sample_parts(), sample_bonds(), REFERENCE)
        best = effective_resistance_to_reference(network, REFERENCE)
        self.assertAlmostEqual(best[REFERENCE], 0.0, places=15)

    def test_route_accumulates_in_series(self):
        network = build_bond_network(sample_parts(), sample_bonds(), REFERENCE)
        best = effective_resistance_to_reference(network, REFERENCE)
        self.assertRatio(best["antenna-bracket"], 6.0e-3)
        self.assertRatio(best["solar-wing-hinge"], 2.6e-2)

    def test_lowest_resistance_route_wins(self):
        bonds = sample_bonds()
        bonds.append({"from": "solar-wing-hinge", "to": REFERENCE, "resistance_ohm": 3.0e-2})
        network = build_bond_network(sample_parts(), bonds, REFERENCE)
        best = effective_resistance_to_reference(network, REFERENCE)
        self.assertRatio(best["solar-wing-hinge"], 2.6e-2)

    def test_a_better_direct_route_replaces_the_long_one(self):
        bonds = sample_bonds()
        bonds.append({"from": "solar-wing-hinge", "to": REFERENCE, "resistance_ohm": 4.0e-3})
        network = build_bond_network(sample_parts(), bonds, REFERENCE)
        best = effective_resistance_to_reference(network, REFERENCE)
        self.assertRatio(best["solar-wing-hinge"], 4.0e-3)

    def test_part_bonded_only_to_a_floating_neighbour_is_unreachable(self):
        parts = sample_parts()
        bonds = [
            {"from": "primary-truss", "to": REFERENCE, "resistance_ohm": 1.0e-3},
            {"from": "antenna-bracket", "to": "solar-wing-hinge", "resistance_ohm": 1.0e-3},
            {"from": "handrail-fitting", "to": REFERENCE, "resistance_ohm": 0.5},
        ]
        network = build_bond_network(parts, bonds, REFERENCE)
        best = effective_resistance_to_reference(network, REFERENCE)
        self.assertIsNone(best["antenna-bracket"])
        self.assertIsNone(best["solar-wing-hinge"])

    def test_reference_outside_the_network_is_rejected(self):
        network = build_bond_network(sample_parts(), sample_bonds(), REFERENCE)
        with self.assertRaises(ValueError):
            effective_resistance_to_reference(network, "chassis-datum")

    def test_empty_network_is_rejected(self):
        with self.assertRaises(ValueError):
            effective_resistance_to_reference({}, REFERENCE)


class TestPartEvaluation(RatioMixin):
    def test_compliant_part_has_no_findings(self):
        part = {"id": "primary-truss", "category": "primary-structure", "exposed_area_m2": 0.5}
        result = evaluate_part_bond(part, 1.0e-3, current_density_a_m2=J_GEO)
        self.assertEqual(result["disposition"], "bonded-compliant")
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["within_category_limit"])

    def test_unreachable_part_is_reported_as_isolated(self):
        part = {"id": "solar-wing-hinge", "category": "mechanism-metal", "exposed_area_m2": 0.05}
        result = evaluate_part_bond(part, None, current_density_a_m2=J_GEO)
        self.assertEqual(result["disposition"], "electrically-isolated")
        self.assertFalse(result["within_category_limit"])

    def test_resistance_above_the_category_ceiling_is_non_compliant(self):
        part = {"id": "primary-truss", "category": "primary-structure", "exposed_area_m2": 0.5}
        result = evaluate_part_bond(part, 1.0e-2, current_density_a_m2=J_GEO)
        self.assertEqual(result["disposition"], "bonding-non-compliant")
        self.assertFalse(result["within_category_limit"])

    def test_same_resistance_passes_under_a_bleed_category(self):
        part = {"id": "handrail-fitting", "category": "electrostatic-bleed", "exposed_area_m2": 0.02}
        result = evaluate_part_bond(part, 1.0e-2, current_density_a_m2=J_GEO)
        self.assertEqual(result["disposition"], "bonded-compliant")

    def test_missing_area_is_incomplete_evidence_not_a_pass(self):
        part = {"id": "primary-truss", "category": "primary-structure"}
        result = evaluate_part_bond(part, 1.0e-3, current_density_a_m2=J_GEO)
        self.assertEqual(result["disposition"], "incomplete-evidence")
        self.assertIsNone(result["quasi_static_potential_v"])

    def test_transient_exceedance_is_caught_on_a_milliohm_bond(self):
        part = {"id": "primary-truss", "category": "primary-structure", "exposed_area_m2": 0.5}
        result = evaluate_part_bond(
            part,
            1.0e-3,
            current_density_a_m2=J_GEO,
            discharge={
                "peak_current_a": 10.0,
                "rise_time_s": 1.0e-8,
                "inductance_h": strap_inductance(0.3, 0.02),
            },
        )
        self.assertEqual(result["disposition"], "bonding-non-compliant")
        self.assertGreater(result["transient_potential_v"], 100.0)
        self.assertTrue(result["within_category_limit"])

    def test_short_wide_strap_passes_the_same_transient(self):
        part = {"id": "primary-truss", "category": "primary-structure", "exposed_area_m2": 0.5}
        result = evaluate_part_bond(
            part,
            1.0e-3,
            current_density_a_m2=J_GEO,
            allowable_potential_v=50.0,
            discharge={
                "peak_current_a": 10.0,
                "rise_time_s": 1.0e-6,
                "inductance_h": strap_inductance(0.05, 0.02),
            },
        )
        self.assertEqual(result["disposition"], "bonded-compliant")

    def test_unknown_discharge_key_is_rejected(self):
        part = {"id": "primary-truss", "category": "primary-structure", "exposed_area_m2": 0.5}
        with self.assertRaises(ValueError):
            evaluate_part_bond(
                part, 1.0e-3, discharge={"peak_current_a": 10.0, "fall_time_s": 1.0e-8}
            )

    def test_unknown_category_on_a_part_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_part_bond({"id": "shear-panel", "category": "chassis-bond"}, 1.0e-3)

    def test_negative_resistance_is_rejected(self):
        part = {"id": "primary-truss", "category": "primary-structure", "exposed_area_m2": 0.5}
        with self.assertRaises(ValueError):
            evaluate_part_bond(part, -1.0e-3)


class TestNetworkAssessment(RatioMixin):
    def test_healthy_network_is_compliant(self):
        summary = assess_bonding_network(
            sample_parts(), sample_bonds(), REFERENCE, current_density_a_m2=J_GEO
        )
        self.assertTrue(summary["compliant"])
        self.assertEqual(summary["counts"]["bonded-compliant"], 4)
        self.assertEqual(summary["isolated_parts"], [])

    def test_severed_route_isolates_a_whole_branch(self):
        bonds = [
            {"from": "primary-truss", "to": REFERENCE, "resistance_ohm": 1.0e-3},
            {"from": "solar-wing-hinge", "to": "antenna-bracket", "resistance_ohm": 2.0e-2},
            {"from": "handrail-fitting", "to": REFERENCE, "resistance_ohm": 0.5},
        ]
        summary = assess_bonding_network(
            sample_parts(), bonds, REFERENCE, current_density_a_m2=J_GEO
        )
        self.assertFalse(summary["compliant"])
        self.assertEqual(summary["isolated_parts"], ["antenna-bracket", "solar-wing-hinge"])
        self.assertEqual(summary["counts"]["electrically-isolated"], 2)

    def test_over_limit_branch_is_counted_as_non_compliant(self):
        bonds = sample_bonds()
        bonds[1]["resistance_ohm"] = 5.0e-2
        summary = assess_bonding_network(
            sample_parts(), bonds, REFERENCE, current_density_a_m2=J_GEO
        )
        self.assertFalse(summary["compliant"])
        self.assertEqual(summary["counts"]["bonding-non-compliant"], 2)

    def test_missing_areas_are_counted_as_incomplete_evidence(self):
        parts = sample_parts()
        for part in parts:
            part.pop("exposed_area_m2")
        summary = assess_bonding_network(parts, sample_bonds(), REFERENCE)
        self.assertFalse(summary["compliant"])
        self.assertEqual(summary["counts"]["incomplete-evidence"], 4)


if __name__ == "__main__":
    unittest.main()
