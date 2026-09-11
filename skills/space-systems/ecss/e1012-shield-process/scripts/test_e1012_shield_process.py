"""
Gate-3 contract tests for e1012-shield-process logic.
Covers method selection, attenuation, predicted-dose computation, adequacy
checking with the radiation design margin, full-process orchestration and
result summarisation.
stdlib unittest only — offline, deterministic.
Run: python3 test_e1012_shield_process.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_shield_process_logic import (
    CalculationMethod,
    EffectType,
    GeometryComplexity,
    RadiationRequirement,
    ShieldConfig,
    attenuation_factor,
    check_adequacy,
    compute_predicted_dose,
    run_shielding_process,
    select_method,
    summarize_results,
)


def cfg(component_id="comp_a", primary=5.0, secondary=0.0, material="aluminium"):
    return ShieldConfig(
        component_id=component_id,
        primary_thickness_mm=primary,
        secondary_thickness_mm=secondary,
        material=material,
    )


class TestMethodSelection(unittest.TestCase):

    def test_heavy_ion_always_uses_let_spectrum(self):
        for geometry in GeometryComplexity:
            self.assertEqual(
                select_method(EffectType.SEE_HEAVY_ION, geometry),
                CalculationMethod.LET_SPECTRUM,
            )

    def test_displacement_damage_complex_uses_monte_carlo(self):
        self.assertEqual(
            select_method(EffectType.DD, GeometryComplexity.COMPLEX),
            CalculationMethod.MONTE_CARLO,
        )

    def test_displacement_damage_simple_uses_niel_weighted(self):
        self.assertEqual(
            select_method(EffectType.DD, GeometryComplexity.SIMPLE),
            CalculationMethod.NIEL_WEIGHTED,
        )

    def test_displacement_damage_moderate_uses_niel_weighted(self):
        self.assertEqual(
            select_method(EffectType.DD, GeometryComplexity.MODERATE),
            CalculationMethod.NIEL_WEIGHTED,
        )

    def test_tid_geometry_matrix(self):
        self.assertEqual(
            select_method(EffectType.TID, GeometryComplexity.SIMPLE),
            CalculationMethod.SLAB_APPROX,
        )
        self.assertEqual(
            select_method(EffectType.TID, GeometryComplexity.MODERATE),
            CalculationMethod.SECTOR_ANALYSIS,
        )
        self.assertEqual(
            select_method(EffectType.TID, GeometryComplexity.COMPLEX),
            CalculationMethod.MONTE_CARLO,
        )

    def test_proton_see_shares_the_tid_geometry_matrix(self):
        for geometry in GeometryComplexity:
            self.assertEqual(
                select_method(EffectType.SEE_PROTON, geometry),
                select_method(EffectType.TID, geometry),
            )


class TestShieldConfig(unittest.TestCase):

    def test_total_thickness_sums_primary_and_secondary(self):
        self.assertAlmostEqual(cfg(primary=2.5, secondary=1.5).total_thickness_mm, 4.0)

    def test_zero_thicknesses_allowed(self):
        self.assertEqual(cfg(primary=0.0, secondary=0.0).total_thickness_mm, 0.0)

    def test_empty_component_id_raises(self):
        with self.assertRaises(ValueError):
            cfg(component_id="")

    def test_negative_primary_raises(self):
        with self.assertRaises(ValueError):
            cfg(primary=-1.0)

    def test_negative_secondary_raises(self):
        with self.assertRaises(ValueError):
            cfg(secondary=-0.5)

    def test_empty_material_raises(self):
        with self.assertRaises(ValueError):
            cfg(material="")


class TestRadiationRequirement(unittest.TestCase):

    def test_design_limit_divides_by_margin(self):
        req = RadiationRequirement("comp_a", EffectType.TID, 100.0, 2.0)
        self.assertAlmostEqual(req.design_limit, 50.0)

    def test_margin_of_one_leaves_limit_unchanged(self):
        req = RadiationRequirement("comp_a", EffectType.TID, 100.0, 1.0)
        self.assertAlmostEqual(req.design_limit, 100.0)

    def test_empty_component_id_raises(self):
        with self.assertRaises(ValueError):
            RadiationRequirement("", EffectType.TID, 100.0, 2.0)

    def test_zero_limit_raises(self):
        with self.assertRaises(ValueError):
            RadiationRequirement("comp_a", EffectType.TID, 0.0, 2.0)

    def test_negative_limit_raises(self):
        with self.assertRaises(ValueError):
            RadiationRequirement("comp_a", EffectType.TID, -10.0, 2.0)

    def test_margin_below_one_raises(self):
        with self.assertRaises(ValueError):
            RadiationRequirement("comp_a", EffectType.TID, 100.0, 0.5)


class TestAttenuationFactor(unittest.TestCase):

    def test_zero_thickness_is_unity(self):
        self.assertAlmostEqual(attenuation_factor("aluminium", 0.0), 1.0)

    def test_one_half_value_layer_halves(self):
        # HVL(aluminium) = 5.0 mm → exp(-ln2 × 5/5) = 0.5
        self.assertAlmostEqual(attenuation_factor("aluminium", 5.0), 0.5, places=12)

    def test_material_hvls_all_halve_at_their_own_hvl(self):
        for material, hvl in (
            ("aluminium", 5.0),
            ("tantalum", 1.5),
            ("polyethylene", 12.0),
            ("titanium", 4.0),
            ("steel", 3.5),
        ):
            self.assertAlmostEqual(
                attenuation_factor(material, hvl), 0.5, places=12
            )

    def test_two_hvl_quarters(self):
        self.assertAlmostEqual(attenuation_factor("aluminium", 10.0), 0.25, places=12)

    def test_factor_decreases_monotonically(self):
        factors = [attenuation_factor("aluminium", t) for t in (0, 2, 5, 10, 20)]
        self.assertEqual(factors, sorted(factors, reverse=True))
        for earlier, later in zip(factors, factors[1:]):
            self.assertGreater(earlier, later)

    def test_material_lookup_is_case_insensitive(self):
        self.assertAlmostEqual(
            attenuation_factor("Aluminium", 5.0),
            attenuation_factor("aluminium", 5.0),
        )

    def test_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            attenuation_factor("unobtainium", 5.0)

    def test_negative_thickness_raises(self):
        with self.assertRaises(ValueError):
            attenuation_factor("aluminium", -1.0)


class TestPredictedDose(unittest.TestCase):

    def test_negative_unshielded_dose_raises(self):
        with self.assertRaises(ValueError):
            compute_predicted_dose(-1.0, cfg(), EffectType.TID)

    def test_aluminium_shield_halves_the_dose(self):
        # 100 units behind 5 mm Al (1 HVL) → 50 units
        self.assertAlmostEqual(
            compute_predicted_dose(100.0, cfg(primary=5.0), EffectType.TID),
            50.0,
            places=9,
        )

    def test_primary_and_secondary_combine(self):
        # 2.5 mm primary + 2.5 mm secondary = 5 mm total = 1 HVL → 0.5
        predicted = compute_predicted_dose(
            100.0, cfg(primary=2.5, secondary=2.5), EffectType.TID
        )
        self.assertAlmostEqual(predicted, 50.0, places=9)

    def test_zero_shielding_returns_unshielded(self):
        self.assertAlmostEqual(
            compute_predicted_dose(100.0, cfg(primary=0.0), EffectType.TID), 100.0
        )

    def test_heavy_ion_dose_is_not_attenuated(self):
        # Bulk shielding does not materially reduce the LET spectrum.
        predicted = compute_predicted_dose(
            100.0, cfg(primary=20.0, secondary=10.0), EffectType.SEE_HEAVY_ION
        )
        self.assertAlmostEqual(predicted, 100.0, places=12)

    def test_displacement_damage_uses_the_attenuation_model(self):
        predicted = compute_predicted_dose(
            1.0e12, cfg(primary=5.0), EffectType.DD
        )
        self.assertAlmostEqual(predicted, 0.5e12, places=3)


class TestAdequacyCheck(unittest.TestCase):

    def test_pass_below_design_limit(self):
        req = RadiationRequirement("comp_a", EffectType.TID, 200.0, 2.0)
        ok, notes = check_adequacy(50.0, req)  # design limit = 100
        self.assertTrue(ok)
        self.assertEqual(notes, [])

    def test_boundary_equality_passes(self):
        req = RadiationRequirement("comp_a", EffectType.TID, 100.0, 2.0)
        ok, notes = check_adequacy(50.0, req)  # exactly at design limit
        self.assertTrue(ok)
        self.assertEqual(notes, [])

    def test_fail_above_design_limit_reports_notes(self):
        req = RadiationRequirement("comp_a", EffectType.TID, 100.0, 2.0)
        ok, notes = check_adequacy(60.0, req)
        self.assertFalse(ok)
        self.assertTrue(notes)
        self.assertIn("exceeds", notes[0])

    def test_margin_applied_before_comparison(self):
        # limit 100 with RDM 2 → effective limit 50; 60 must fail even
        # though it is below the raw limit of 100.
        req = RadiationRequirement("comp_a", EffectType.TID, 100.0, 2.0)
        ok, _ = check_adequacy(60.0, req)
        self.assertFalse(ok)

    def test_margin_of_one_compares_against_raw_limit(self):
        req = RadiationRequirement("comp_a", EffectType.TID, 100.0, 1.0)
        self.assertTrue(check_adequacy(100.0, req)[0])
        self.assertFalse(check_adequacy(100.001, req)[0])


class TestRunShieldingProcess(unittest.TestCase):

    def _doses(self):
        return {
            ("comp_a", EffectType.TID): 100.0,
            ("comp_a", EffectType.SEE_HEAVY_ION): 100.0,
        }

    def test_one_result_per_requirement(self):
        reqs = [
            RadiationRequirement("comp_a", EffectType.TID, 200.0, 2.0),
            RadiationRequirement("comp_a", EffectType.SEE_HEAVY_ION, 200.0, 2.0),
        ]
        results = run_shielding_process(
            self._doses(), {"comp_a": cfg()}, reqs
        )
        self.assertEqual(len(results), 2)

    def test_result_fields_are_populated(self):
        reqs = [RadiationRequirement("comp_a", EffectType.TID, 200.0, 2.0)]
        result = run_shielding_process(
            self._doses(), {"comp_a": cfg(primary=5.0, secondary=1.0)}, reqs
        )[0]
        self.assertEqual(result.component_id, "comp_a")
        self.assertEqual(result.effect_type, EffectType.TID)
        self.assertAlmostEqual(result.primary_contribution_mm, 5.0)
        self.assertAlmostEqual(result.secondary_contribution_mm, 1.0)
        self.assertAlmostEqual(result.limit, 200.0)
        self.assertAlmostEqual(result.margin_factor, 2.0)
        # primary 5 mm + secondary 1 mm = 6 mm Al → factor exp(-ln2 × 6/5)
        expected = 100.0 * attenuation_factor("aluminium", 6.0)
        self.assertAlmostEqual(result.predicted_dose, expected, places=9)

    def test_geometry_parameter_drives_method(self):
        reqs = [RadiationRequirement("comp_a", EffectType.TID, 200.0, 2.0)]
        result = run_shielding_process(
            self._doses(),
            {"comp_a": cfg()},
            reqs,
            geometry=GeometryComplexity.SIMPLE,
        )[0]
        self.assertEqual(result.method, CalculationMethod.SLAB_APPROX)

    def test_default_geometry_is_moderate(self):
        reqs = [RadiationRequirement("comp_a", EffectType.TID, 200.0, 2.0)]
        result = run_shielding_process(self._doses(), {"comp_a": cfg()}, reqs)[0]
        self.assertEqual(result.method, CalculationMethod.SECTOR_ANALYSIS)

    def test_adequacy_flag_matches_standalone_check(self):
        reqs = [RadiationRequirement("comp_a", EffectType.TID, 80.0, 2.0)]
        result = run_shielding_process(self._doses(), {"comp_a": cfg()}, reqs)[0]
        expected_ok, _ = check_adequacy(result.predicted_dose, reqs[0])
        self.assertEqual(result.shielding_adequate, expected_ok)
        self.assertFalse(result.shielding_adequate)  # 50 > 40 → fail
        self.assertTrue(result.notes)

    def test_missing_shield_config_raises(self):
        reqs = [RadiationRequirement("comp_z", EffectType.TID, 200.0, 2.0)]
        with self.assertRaises(ValueError):
            run_shielding_process(self._doses(), {"comp_a": cfg()}, reqs)

    def test_missing_unshielded_dose_raises(self):
        reqs = [RadiationRequirement("comp_a", EffectType.DD, 200.0, 2.0)]
        with self.assertRaises(ValueError):
            run_shielding_process(self._doses(), {"comp_a": cfg()}, reqs)

    def test_empty_requirements_returns_empty_list(self):
        self.assertEqual(
            run_shielding_process(self._doses(), {"comp_a": cfg()}, []), []
        )


class TestSummarizeResults(unittest.TestCase):

    def _mixed_results(self):
        reqs = [
            RadiationRequirement("comp_a", EffectType.TID, 200.0, 2.0),   # passes
            RadiationRequirement("comp_a", EffectType.TID, 80.0, 2.0),    # fails
        ]
        return run_shielding_process(
            {("comp_a", EffectType.TID): 100.0}, {"comp_a": cfg()}, reqs
        )

    def test_counts_split_pass_and_fail(self):
        summary = summarize_results(self._mixed_results())
        self.assertEqual(summary["total_checks"], 2)
        self.assertEqual(summary["passed"], 1)
        self.assertEqual(summary["failed"], 1)

    def test_failure_detail_fields(self):
        summary = summarize_results(self._mixed_results())
        self.assertEqual(len(summary["failures"]), 1)
        failure = summary["failures"][0]
        self.assertEqual(failure["component"], "comp_a")
        self.assertEqual(failure["effect"], EffectType.TID.value)
        self.assertIn("predicted", failure)
        self.assertIn("limit", failure)
        self.assertTrue(failure["notes"])

    def test_all_pass_summary(self):
        reqs = [RadiationRequirement("comp_a", EffectType.TID, 200.0, 2.0)]
        summary = summarize_results(
            run_shielding_process(
                {("comp_a", EffectType.TID): 100.0}, {"comp_a": cfg()}, reqs
            )
        )
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["failures"], [])

    def test_empty_results_summary_is_zeroed(self):
        summary = summarize_results([])
        self.assertEqual(summary["total_checks"], 0)
        self.assertEqual(summary["passed"], 0)
        self.assertEqual(summary["failed"], 0)


if __name__ == "__main__":
    unittest.main()
