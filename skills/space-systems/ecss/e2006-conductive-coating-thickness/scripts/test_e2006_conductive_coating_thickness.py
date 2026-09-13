#!/usr/bin/env python3
"""Contract tests for the clause 6.3.3.5 conductive-coating thickness leaf."""

import math
import unittest

from e2006_conductive_coating_thickness_logic import (
    ALLOWABLE_SHEET_RESISTANCE_OHM_SQ,
    COATING_REGISTER,
    DEFAULT_EROSION_UNCERTAINTY_FACTOR,
    atomic_oxygen_recession_nm,
    coating_properties,
    end_of_life_thickness_nm,
    evaluate_conductive_coating,
    linear_recession_nm,
    mechanism_recession_nm,
    required_end_of_life_thickness_nm,
    sheet_resistance_ohm_sq,
    sputter_recession_nm,
    thickness_for_sheet_resistance_nm,
    total_recession_nm,
)


def linear_mechanism(rate=10.0, kind="particulate-abrasion"):
    return {"type": kind, "rate_nm_per_year": rate}


def oxygen_mechanism(fluence=3.0e21, yield_=1.0e-27):
    return {
        "type": "atomic-oxygen",
        "fluence_atoms_per_cm2": fluence,
        "erosion_yield_cm3_per_atom": yield_,
    }


def sputter_mechanism(flux=1.0e9, yield_=0.1, duration=1.5e8, volume=1.66e-23):
    return {
        "type": "ion-sputtering",
        "ion_flux_per_cm2_s": flux,
        "sputter_yield_atoms_per_ion": yield_,
        "duration_s": duration,
        "atomic_volume_cm3": volume,
    }


class CoatingRegisterTests(unittest.TestCase):
    def test_known_coating_resolves(self):
        out = coating_properties("indium-tin-oxide")
        self.assertAlmostEqual(out["continuity_floor_nm"], 20.0)
        self.assertAlmostEqual(out["bulk_resistivity_ohm_m"], 5.0e-6)

    def test_lookup_is_case_and_space_insensitive(self):
        out = coating_properties("  Gold-Flash ")
        self.assertEqual(out["material"], "gold-flash")

    def test_every_register_entry_is_complete(self):
        for name in COATING_REGISTER:
            out = coating_properties(name)
            self.assertGreater(out["bulk_resistivity_ohm_m"], 0.0)
            self.assertGreater(out["continuity_floor_nm"], 0.0)

    def test_unknown_coating_rejected(self):
        with self.assertRaises(ValueError):
            coating_properties("anodised-titanium")

    def test_blank_coating_name_rejected(self):
        with self.assertRaises(ValueError):
            coating_properties("   ")

    def test_non_string_coating_name_rejected(self):
        with self.assertRaises(ValueError):
            coating_properties(None)


class AtomicOxygenTests(unittest.TestCase):
    def test_recession_depth_value(self):
        out = atomic_oxygen_recession_nm(3.0e21, 1.0e-27)
        self.assertAlmostEqual(out, 30.0, places=9)

    def test_zero_fluence_removes_nothing(self):
        self.assertAlmostEqual(atomic_oxygen_recession_nm(0.0, 3.0e-25), 0.0)

    def test_negative_fluence_rejected(self):
        with self.assertRaises(ValueError):
            atomic_oxygen_recession_nm(-1.0e20, 3.0e-25)

    def test_zero_yield_rejected(self):
        with self.assertRaises(ValueError):
            atomic_oxygen_recession_nm(3.0e21, 0.0)

    def test_non_numeric_fluence_rejected(self):
        with self.assertRaises(ValueError):
            atomic_oxygen_recession_nm("3e21", 3.0e-25)


class SputterTests(unittest.TestCase):
    def test_recession_depth_value(self):
        out = sputter_recession_nm(1.0e9, 0.1, 1.5e8, 1.66e-23)
        self.assertAlmostEqual(out, 2.49, places=6)

    def test_zero_duration_removes_nothing(self):
        self.assertAlmostEqual(sputter_recession_nm(1.0e9, 0.1, 0.0, 1.66e-23), 0.0)

    def test_zero_yield_removes_nothing(self):
        self.assertAlmostEqual(sputter_recession_nm(1.0e9, 0.0, 1.5e8, 1.66e-23), 0.0)

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            sputter_recession_nm(1.0e9, 0.1, -1.0, 1.66e-23)

    def test_zero_atomic_volume_rejected(self):
        with self.assertRaises(ValueError):
            sputter_recession_nm(1.0e9, 0.1, 1.5e8, 0.0)

    def test_infinite_flux_rejected(self):
        with self.assertRaises(ValueError):
            sputter_recession_nm(math.inf, 0.1, 1.5e8, 1.66e-23)


class LinearRecessionTests(unittest.TestCase):
    def test_rate_times_years(self):
        self.assertAlmostEqual(linear_recession_nm(12.0, 7.5), 90.0)

    def test_zero_years_removes_nothing(self):
        self.assertAlmostEqual(linear_recession_nm(12.0, 0.0), 0.0)

    def test_negative_rate_rejected(self):
        with self.assertRaises(ValueError):
            linear_recession_nm(-1.0, 5.0)

    def test_negative_years_rejected(self):
        with self.assertRaises(ValueError):
            linear_recession_nm(1.0, -5.0)


class MechanismDispatchTests(unittest.TestCase):
    def test_oxygen_mechanism_dispatches(self):
        self.assertAlmostEqual(
            mechanism_recession_nm(oxygen_mechanism(), 5.0), 30.0, places=9
        )

    def test_sputter_mechanism_dispatches(self):
        self.assertAlmostEqual(
            mechanism_recession_nm(sputter_mechanism(), 5.0), 2.49, places=6
        )

    def test_abrasion_mechanism_dispatches(self):
        self.assertAlmostEqual(
            mechanism_recession_nm(linear_mechanism(rate=4.0), 5.0), 20.0
        )

    def test_handling_wear_mechanism_dispatches(self):
        out = mechanism_recession_nm(
            linear_mechanism(rate=2.0, kind="handling-wear"), 3.0
        )
        self.assertAlmostEqual(out, 6.0)

    def test_unknown_mechanism_rejected(self):
        with self.assertRaises(ValueError):
            mechanism_recession_nm({"type": "micrometeoroid"}, 5.0)

    def test_non_mapping_mechanism_rejected(self):
        with self.assertRaises(ValueError):
            mechanism_recession_nm("atomic-oxygen", 5.0)

    def test_oxygen_mechanism_missing_field_rejected(self):
        record = oxygen_mechanism()
        del record["fluence_atoms_per_cm2"]
        with self.assertRaises(ValueError):
            mechanism_recession_nm(record, 5.0)


class TotalRecessionTests(unittest.TestCase):
    def test_mechanisms_accumulate(self):
        out = total_recession_nm(
            [linear_mechanism(rate=4.0), oxygen_mechanism()], 5.0, uncertainty_factor=1.0
        )
        self.assertAlmostEqual(out["nominal_nm"], 50.0, places=9)
        self.assertAlmostEqual(out["budgeted_nm"], 50.0, places=9)

    def test_uncertainty_factor_scales_the_budget(self):
        out = total_recession_nm([linear_mechanism(rate=4.0)], 5.0, uncertainty_factor=2.0)
        self.assertAlmostEqual(out["budgeted_nm"], 40.0)

    def test_default_factor_applies_when_absent(self):
        out = total_recession_nm([linear_mechanism(rate=4.0)], 5.0)
        self.assertAlmostEqual(
            out["uncertainty_factor"], DEFAULT_EROSION_UNCERTAINTY_FACTOR
        )
        self.assertAlmostEqual(out["budgeted_nm"], 20.0 * DEFAULT_EROSION_UNCERTAINTY_FACTOR)

    def test_empty_mechanism_list_removes_nothing(self):
        out = total_recession_nm([], 5.0)
        self.assertAlmostEqual(out["budgeted_nm"], 0.0)
        self.assertEqual(out["per_mechanism"], [])

    def test_per_mechanism_breakdown_is_reported(self):
        out = total_recession_nm(
            [linear_mechanism(rate=4.0), sputter_mechanism()], 5.0, uncertainty_factor=1.0
        )
        self.assertEqual(
            [item["type"] for item in out["per_mechanism"]],
            ["particulate-abrasion", "ion-sputtering"],
        )

    def test_factor_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            total_recession_nm([linear_mechanism()], 5.0, uncertainty_factor=0.9)

    def test_mechanism_list_must_be_a_list(self):
        with self.assertRaises(ValueError):
            total_recession_nm({"type": "handling-wear"}, 5.0)


class EndOfLifeThicknessTests(unittest.TestCase):
    def test_surviving_thickness_value(self):
        self.assertAlmostEqual(end_of_life_thickness_nm(120.0, 45.0), 75.0)

    def test_full_loss_floors_at_zero(self):
        self.assertAlmostEqual(end_of_life_thickness_nm(40.0, 90.0), 0.0)

    def test_zero_as_deposited_rejected(self):
        with self.assertRaises(ValueError):
            end_of_life_thickness_nm(0.0, 10.0)

    def test_negative_recession_rejected(self):
        with self.assertRaises(ValueError):
            end_of_life_thickness_nm(100.0, -1.0)


class SheetResistanceTests(unittest.TestCase):
    def test_sheet_resistance_value(self):
        out = sheet_resistance_ohm_sq(5.0e-6, 100.0)
        self.assertAlmostEqual(out, 50.0, places=9)

    def test_thinner_layer_raises_sheet_resistance(self):
        thick = sheet_resistance_ohm_sq(5.0e-6, 200.0)
        thin = sheet_resistance_ohm_sq(5.0e-6, 50.0)
        self.assertGreater(thin, thick)

    def test_thickness_for_a_ceiling_round_trips(self):
        needed = thickness_for_sheet_resistance_nm(5.0e-2, 1.0e5)
        self.assertAlmostEqual(needed, 500.0, places=6)
        self.assertAlmostEqual(sheet_resistance_ohm_sq(5.0e-2, needed), 1.0e5, places=3)

    def test_zero_thickness_has_no_sheet_resistance(self):
        with self.assertRaises(ValueError):
            sheet_resistance_ohm_sq(5.0e-6, 0.0)

    def test_zero_resistivity_rejected(self):
        with self.assertRaises(ValueError):
            sheet_resistance_ohm_sq(0.0, 100.0)

    def test_zero_allowable_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            thickness_for_sheet_resistance_nm(5.0e-6, 0.0)


class RequiredThicknessTests(unittest.TestCase):
    def test_continuity_floor_governs_a_good_conductor(self):
        props = coating_properties("indium-tin-oxide")
        out = required_end_of_life_thickness_nm(props, ALLOWABLE_SHEET_RESISTANCE_OHM_SQ)
        self.assertAlmostEqual(out, 20.0)

    def test_sheet_resistance_governs_a_resistive_coating(self):
        props = coating_properties("germanium-on-polyimide")
        out = required_end_of_life_thickness_nm(props, 1.0e5)
        self.assertAlmostEqual(out, 500.0, places=6)

    def test_tighter_ceiling_raises_the_requirement(self):
        props = coating_properties("germanium-on-polyimide")
        loose = required_end_of_life_thickness_nm(props, 1.0e5)
        tight = required_end_of_life_thickness_nm(props, 1.0e4)
        self.assertGreater(tight, loose)


class EvaluationTests(unittest.TestCase):
    def build(self, **overrides):
        record = {
            "surface": "solar-array-front-face",
            "material": "indium-tin-oxide",
            "as_deposited_nm": 150.0,
            "mission_years": 5.0,
            "uncertainty_factor": 1.0,
            "mechanisms": [linear_mechanism(rate=10.0)],
        }
        record.update(overrides)
        return record

    def test_healthy_coating_is_compliant(self):
        out = evaluate_conductive_coating(self.build())
        self.assertTrue(out["compliant"])
        self.assertAlmostEqual(out["end_of_life_thickness_nm"], 100.0)

    def test_reported_sheet_resistance_matches_the_surviving_layer(self):
        out = evaluate_conductive_coating(self.build())
        self.assertAlmostEqual(
            out["end_of_life_sheet_resistance_ohm_sq"], 50.0, places=9
        )

    def test_required_as_deposited_is_reported(self):
        out = evaluate_conductive_coating(self.build())
        self.assertAlmostEqual(out["required_as_deposited_nm"], 70.0)
        self.assertAlmostEqual(out["thickness_margin_nm"], 80.0)

    def test_thickness_exactly_on_the_continuity_floor_passes(self):
        out = evaluate_conductive_coating(self.build(as_deposited_nm=70.0))
        self.assertAlmostEqual(out["end_of_life_thickness_nm"], 20.0)
        self.assertTrue(out["continuity_ok"])
        self.assertTrue(out["compliant"])

    def test_boundary_case_with_representation_drift_passes(self):
        out = evaluate_conductive_coating(
            self.build(
                as_deposited_nm=33.05,
                mission_years=15.0,
                mechanisms=[linear_mechanism(rate=0.87)],
            )
        )
        self.assertLess(out["end_of_life_thickness_nm"], 20.0)
        self.assertTrue(out["continuity_ok"])
        self.assertTrue(out["compliant"])

    def test_thickness_a_nanometre_short_fails(self):
        out = evaluate_conductive_coating(self.build(as_deposited_nm=69.0))
        self.assertFalse(out["continuity_ok"])
        self.assertFalse(out["compliant"])

    def test_fully_eroded_coating_fails_both_checks(self):
        out = evaluate_conductive_coating(
            self.build(as_deposited_nm=30.0, mechanisms=[linear_mechanism(rate=20.0)])
        )
        self.assertAlmostEqual(out["end_of_life_thickness_nm"], 0.0)
        self.assertFalse(out["sheet_resistance_ok"])
        self.assertEqual(len(out["findings"]), 3)

    def test_default_uncertainty_factor_can_consume_the_margin(self):
        healthy = evaluate_conductive_coating(self.build(as_deposited_nm=90.0))
        self.assertTrue(healthy["compliant"])
        stressed = evaluate_conductive_coating(
            self.build(as_deposited_nm=90.0, uncertainty_factor=None)
        )
        self.assertGreater(
            stressed["recession"]["budgeted_nm"], healthy["recession"]["budgeted_nm"]
        )

    def test_sheet_resistance_ceiling_can_govern(self):
        out = evaluate_conductive_coating(
            self.build(
                material="germanium-on-polyimide",
                as_deposited_nm=300.0,
                allowable_sheet_resistance_ohm_sq=1.0e5,
                mechanisms=[linear_mechanism(rate=0.0)],
            )
        )
        self.assertTrue(out["continuity_ok"])
        self.assertFalse(out["sheet_resistance_ok"])

    def test_multiple_mechanisms_accumulate_in_the_verdict(self):
        out = evaluate_conductive_coating(
            self.build(
                as_deposited_nm=90.0,
                mechanisms=[linear_mechanism(rate=10.0), oxygen_mechanism()],
            )
        )
        self.assertAlmostEqual(out["recession"]["budgeted_nm"], 80.0, places=9)
        self.assertAlmostEqual(out["end_of_life_thickness_nm"], 10.0, places=9)
        self.assertFalse(out["compliant"])

    def test_surface_name_is_required(self):
        record = self.build()
        del record["surface"]
        with self.assertRaises(ValueError):
            evaluate_conductive_coating(record)

    def test_spec_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            evaluate_conductive_coating(["solar-array-front-face"])

    def test_unknown_material_rejected_by_the_evaluation(self):
        with self.assertRaises(ValueError):
            evaluate_conductive_coating(self.build(material="anodised-titanium"))

    def test_negative_mission_duration_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_conductive_coating(self.build(mission_years=-1.0))

    def test_zero_as_deposited_rejected_by_the_evaluation(self):
        with self.assertRaises(ValueError):
            evaluate_conductive_coating(self.build(as_deposited_nm=0.0))

    def test_negative_allowable_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_conductive_coating(
                self.build(allowable_sheet_resistance_ohm_sq=-1.0)
            )

    def test_evaluation_is_deterministic(self):
        self.assertEqual(
            evaluate_conductive_coating(self.build()),
            evaluate_conductive_coating(self.build()),
        )


if __name__ == "__main__":
    unittest.main()
