#!/usr/bin/env python3
"""Contract test for the Class 1 restricted material screen (offline).

Walks the clause workflow step by step: the finish table split into
accepted, barred-outright and mitigable, the pure-tin lead mass fraction
against its threshold including the exact-boundary case, the silver
barrier underplate, the conditional plastic encapsulation with absence
kept apart from failure, the outgassing limits at their exact bounds,
and the roll-up of the three axes into one construction verdict. This is
the gate 3 review evidence for the leaf.
"""

import copy
import unittest

from q6013_class_1_material_restrictions_logic import (
    BARRED_FINISHES,
    CONSTRUCTION_ACCEPTED,
    CONSTRUCTION_MITIGATION_REQUIRED,
    CONSTRUCTION_PROHIBITED,
    MATERIAL_ACCEPTED,
    MATERIAL_MITIGATION_REQUIRED,
    MATERIAL_PROHIBITED,
    MITIGABLE_FINISHES,
    assess_encapsulation,
    assess_finish,
    assess_outgassing,
    assess_part_construction,
    resolve_policy,
    restricted_materials,
)


def _finish(material="tin-lead", surface="part-termination", **overrides):
    record = {"material": material, "surface": surface}
    record.update(copy.deepcopy(overrides))
    return record


def _encapsulation(kind="hermetic-ceramic", **overrides):
    record = {"kind": kind}
    if kind == "plastic-encapsulated":
        record.update(
            {
                "moisture_sensitivity_level": 2,
                "bake_and_dry_pack_record": True,
                "total_ionising_dose_krad": 10.0,
            }
        )
    record.update(copy.deepcopy(overrides))
    return record


def _part(part_id="PRT-00", **overrides):
    record = {
        "part_id": part_id,
        "finishes": [_finish()],
        "encapsulation": _encapsulation(),
        "outgassing": {
            "total_mass_loss_percent": 0.35,
            "collected_volatile_percent": 0.02,
        },
    }
    record.update(copy.deepcopy(overrides))
    return record


class FinishTableTests(unittest.TestCase):
    def test_the_restricted_table_separates_barred_from_mitigable(self):
        table = restricted_materials()
        self.assertEqual(set(table["barred"]), set(BARRED_FINISHES))
        self.assertEqual(set(table["mitigable"]), set(MITIGABLE_FINISHES))
        self.assertFalse(set(table["barred"]) & set(table["mitigable"]))

    def test_an_accepted_finish_passes_without_a_finding(self):
        result = assess_finish(_finish("gold"))
        self.assertEqual(result["verdict"], MATERIAL_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_cadmium_is_barred_with_no_mitigation_offered(self):
        result = assess_finish(_finish("cadmium"))
        self.assertEqual(result["verdict"], MATERIAL_PROHIBITED)
        self.assertIsNone(result["mitigation"])
        self.assertTrue(any("no later process" in f for f in result["findings"]))

    def test_zinc_is_barred_even_with_a_declared_mitigation(self):
        result = assess_finish(
            _finish("zinc", lead_mass_fraction_percent=40.0)
        )
        self.assertEqual(result["verdict"], MATERIAL_PROHIBITED)
        self.assertFalse(result["mitigation_applied"])

    def test_an_unknown_finish_material_rejected(self):
        with self.assertRaises(ValueError):
            assess_finish(_finish("unobtainium"))

    def test_a_blank_surface_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_finish(_finish("gold", surface="   "))


class PureTinMitigationTests(unittest.TestCase):
    def test_pure_tin_without_a_declared_fraction_needs_mitigation(self):
        result = assess_finish(_finish("pure-tin"))
        self.assertEqual(result["verdict"], MATERIAL_MITIGATION_REQUIRED)
        self.assertIsNone(result["lead_mass_fraction_percent"])
        self.assertTrue(any("unevidenced" in f for f in result["findings"]))

    def test_pure_tin_above_the_threshold_is_accepted(self):
        result = assess_finish(
            _finish("pure-tin", lead_mass_fraction_percent=5.0)
        )
        self.assertEqual(result["verdict"], MATERIAL_ACCEPTED)
        self.assertTrue(result["mitigation_applied"])
        self.assertEqual(result["mitigation"], "lead-alloyed-finish")

    def test_pure_tin_exactly_on_the_threshold_is_accepted(self):
        result = assess_finish(
            _finish("pure-tin", lead_mass_fraction_percent=3.0)
        )
        self.assertAlmostEqual(
            result["lead_mass_fraction_percent"],
            resolve_policy()["min_lead_mass_fraction_percent"],
            places=9,
        )
        self.assertEqual(result["verdict"], MATERIAL_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_pure_tin_below_the_threshold_needs_mitigation(self):
        result = assess_finish(
            _finish("pure-tin", lead_mass_fraction_percent=1.0)
        )
        self.assertEqual(result["verdict"], MATERIAL_MITIGATION_REQUIRED)
        self.assertTrue(any("whisker-mitigation" in f for f in result["findings"]))

    def test_a_raised_threshold_reopens_a_previously_accepted_finish(self):
        finish = _finish("pure-tin", lead_mass_fraction_percent=3.0)
        self.assertEqual(assess_finish(finish)["verdict"], MATERIAL_ACCEPTED)
        raised = assess_finish(finish, {"min_lead_mass_fraction_percent": 4.0})
        self.assertEqual(raised["verdict"], MATERIAL_MITIGATION_REQUIRED)

    def test_a_lead_fraction_above_one_hundred_percent_rejected(self):
        with self.assertRaises(ValueError):
            assess_finish(_finish("pure-tin", lead_mass_fraction_percent=140.0))

    def test_silver_needs_a_declared_barrier_underplate(self):
        bare = assess_finish(_finish("pure-silver"))
        plated = assess_finish(_finish("pure-silver", barrier_underplate=True))
        self.assertEqual(bare["verdict"], MATERIAL_MITIGATION_REQUIRED)
        self.assertEqual(plated["verdict"], MATERIAL_ACCEPTED)
        self.assertEqual(plated["mitigation"], "nickel-barrier-underplate")


class EncapsulationTests(unittest.TestCase):
    def test_a_hermetic_package_is_accepted_with_no_conditions(self):
        result = assess_encapsulation(_encapsulation("hermetic-metal"))
        self.assertEqual(result["verdict"], MATERIAL_ACCEPTED)
        self.assertEqual(result["conditions_open"], [])

    def test_a_plastic_package_meeting_every_condition_is_accepted(self):
        result = assess_encapsulation(_encapsulation("plastic-encapsulated"))
        self.assertEqual(result["verdict"], MATERIAL_ACCEPTED)
        self.assertEqual(len(result["conditions_met"]), 3)

    def test_an_absent_condition_is_kept_apart_from_a_failed_one(self):
        record = _encapsulation("plastic-encapsulated")
        del record["moisture_sensitivity_level"]
        record["bake_and_dry_pack_record"] = False
        result = assess_encapsulation(record)
        self.assertEqual(result["conditions_absent"], ["moisture-sensitivity-level"])
        self.assertEqual(result["conditions_open"], ["bake-and-dry-pack-record"])
        self.assertEqual(result["verdict"], MATERIAL_MITIGATION_REQUIRED)

    def test_a_dose_above_the_plastic_package_limit_opens_a_condition(self):
        result = assess_encapsulation(
            _encapsulation("plastic-encapsulated", total_ionising_dose_krad=90.0)
        )
        self.assertIn("plastic-package-dose-environment", result["conditions_open"])
        self.assertEqual(result["verdict"], MATERIAL_MITIGATION_REQUIRED)

    def test_a_dose_exactly_on_the_plastic_package_limit_is_inside_it(self):
        limit = resolve_policy()["max_plastic_package_dose_krad"]
        result = assess_encapsulation(
            _encapsulation("plastic-encapsulated", total_ionising_dose_krad=limit)
        )
        self.assertAlmostEqual(limit, 30.0, places=9)
        self.assertIn("plastic-package-dose-environment", result["conditions_met"])
        self.assertEqual(result["verdict"], MATERIAL_ACCEPTED)

    def test_an_undeclared_package_construction_is_barred(self):
        result = assess_encapsulation(_encapsulation("unknown-encapsulation"))
        self.assertEqual(result["verdict"], MATERIAL_PROHIBITED)

    def test_a_moisture_level_below_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_encapsulation(
                _encapsulation("plastic-encapsulated", moisture_sensitivity_level=0)
            )


class OutgassingTests(unittest.TestCase):
    def test_low_outgassing_data_is_accepted(self):
        result = assess_outgassing(
            {"total_mass_loss_percent": 0.35, "collected_volatile_percent": 0.02}
        )
        self.assertEqual(result["verdict"], MATERIAL_ACCEPTED)
        self.assertAlmostEqual(result["mass_loss_margin_percent"], 0.65, places=9)

    def test_values_exactly_on_both_limits_are_inside_them(self):
        limits = resolve_policy()
        result = assess_outgassing(
            {
                "total_mass_loss_percent": limits["max_total_mass_loss_percent"],
                "collected_volatile_percent": limits["max_collected_volatile_percent"],
            }
        )
        self.assertAlmostEqual(result["mass_loss_margin_percent"], 0.0, places=9)
        self.assertAlmostEqual(result["volatile_margin_percent"], 0.0, places=9)
        self.assertEqual(result["verdict"], MATERIAL_ACCEPTED)

    def test_a_mass_loss_above_the_limit_is_barred(self):
        result = assess_outgassing(
            {"total_mass_loss_percent": 2.4, "collected_volatile_percent": 0.02}
        )
        self.assertEqual(result["verdict"], MATERIAL_PROHIBITED)
        self.assertTrue(any("total mass loss" in f for f in result["findings"]))

    def test_absent_outgassing_data_is_not_a_bar_but_a_gap(self):
        result = assess_outgassing({})
        self.assertEqual(result["verdict"], MATERIAL_MITIGATION_REQUIRED)
        self.assertIsNone(result["total_mass_loss_percent"])

    def test_a_negative_mass_loss_rejected(self):
        with self.assertRaises(ValueError):
            assess_outgassing(
                {
                    "total_mass_loss_percent": -0.4,
                    "collected_volatile_percent": 0.02,
                }
            )


class PolicyTests(unittest.TestCase):
    def test_defaults_resolve_to_the_declared_limits(self):
        settings = resolve_policy()
        self.assertAlmostEqual(settings["max_total_mass_loss_percent"], 1.0, places=9)
        self.assertAlmostEqual(
            settings["max_collected_volatile_percent"], 0.10, places=9
        )
        self.assertEqual(settings["max_moisture_sensitivity_level"], 3)

    def test_a_lead_threshold_above_one_hundred_percent_rejected(self):
        with self.assertRaises(ValueError):
            resolve_policy({"min_lead_mass_fraction_percent": 120.0})

    def test_a_fractional_moisture_level_limit_rejected(self):
        with self.assertRaises(ValueError):
            resolve_policy({"max_moisture_sensitivity_level": 2.5})


class ConstructionRollUpTests(unittest.TestCase):
    def test_a_clean_construction_is_accepted(self):
        result = assess_part_construction(_part())
        self.assertEqual(result["verdict"], CONSTRUCTION_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["mitigations_owed"], [])

    def test_one_barred_finish_bars_the_whole_construction(self):
        part = _part(
            finishes=[
                _finish("gold", surface="lid-plating"),
                _finish("cadmium", surface="lead-frame"),
            ]
        )
        result = assess_part_construction(part)
        self.assertEqual(result["verdict"], CONSTRUCTION_PROHIBITED)
        self.assertEqual(result["worst_axis"], MATERIAL_PROHIBITED)
        self.assertEqual(
            result["grouped_surfaces"][MATERIAL_PROHIBITED], ["lead-frame"]
        )

    def test_a_mitigable_finish_names_the_surface_that_owes_it(self):
        part = _part(
            finishes=[
                _finish("gold", surface="lid-plating"),
                _finish("pure-tin", surface="lead-frame"),
            ]
        )
        result = assess_part_construction(part)
        self.assertEqual(result["verdict"], CONSTRUCTION_MITIGATION_REQUIRED)
        self.assertEqual(result["mitigations_owed"], ["lead-frame"])

    def test_outgassing_can_bar_a_part_whose_finishes_are_clean(self):
        part = _part(
            outgassing={
                "total_mass_loss_percent": 3.0,
                "collected_volatile_percent": 0.5,
            }
        )
        result = assess_part_construction(part)
        self.assertEqual(result["verdict"], CONSTRUCTION_PROHIBITED)
        for finish in result["finishes"]:
            self.assertEqual(finish["verdict"], MATERIAL_ACCEPTED)

    def test_a_surface_declared_twice_rejected(self):
        part = _part(finishes=[_finish("gold"), _finish("nickel")])
        with self.assertRaises(ValueError):
            assess_part_construction(part)

    def test_a_part_with_no_finishes_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_construction(_part(finishes=[]))

    def test_non_mapping_part_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_construction("the lead frame looked like tin-lead")


if __name__ == "__main__":
    unittest.main()
