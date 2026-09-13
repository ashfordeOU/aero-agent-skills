#!/usr/bin/env python3
"""Contract test for the critical materials interface listing leaf."""

import unittest

from e2008_critical_materials_interface_listing_logic import (
    ANODIC_INDEX_V,
    BULK_INTERFACE_ROLE,
    GALVANIC_LIMIT_V,
    INTERFACE_DATA_FIELDS,
    OUTGASSING_CVCM_LIMIT_PERCENT,
    OUTGASSING_TML_LIMIT_PERCENT,
    anodic_separation,
    assess_pmp_list,
    check_galvanic_couple,
    check_outgassing,
    evaluate_list_entry,
    interface_criticality,
    missing_entry_fields,
    required_entry_fields,
)


def adhesive_entry(**overrides):
    entry = {
        "id": "MAT-ADH-01",
        "kind": "material",
        "designation": "cell-to-coverglass adhesive",
        "supplier": "array integrator",
        "specification": "SPEC-ADH-4471",
        "material_family": "adhesive",
        "interface_role": "cell-to-coverglass",
        "mating_item": "ceria-doped coverglass",
        "interface_type": "bonded",
        "interface_environment": "vacuum-thermal-cycling",
        "qualification_reference": "QR-ADH-0211",
        "outgassing_tml_percent": 0.35,
        "outgassing_cvcm_percent": 0.02,
    }
    entry.update(overrides)
    return entry


def interconnect_entry(**overrides):
    entry = {
        "id": "PRT-ICN-02",
        "kind": "part",
        "designation": "silver-plated interconnect",
        "supplier": "cell supplier",
        "specification": "SPEC-ICN-1120",
        "part_number": "ICN-1120-A",
        "interface_role": "cell-to-interconnect",
        "mating_item": "cell front busbar",
        "interface_type": "welded",
        "interface_environment": "vacuum-thermal-cycling",
        "qualification_reference": "QR-ICN-0044",
        "metal": "silver",
        "mating_metal": "gold",
        "mating_material_family": "metal",
    }
    entry.update(overrides)
    return entry


def bulk_entry(**overrides):
    entry = {
        "id": "MAT-CFRP-03",
        "kind": "material",
        "designation": "substrate facesheet laminate",
        "supplier": "panel supplier",
        "specification": "SPEC-CFRP-0900",
        "material_family": "composite",
        "interface_role": BULK_INTERFACE_ROLE,
    }
    entry.update(overrides)
    return entry


def pmp_list():
    return [adhesive_entry(), interconnect_entry(), bulk_entry()]


class TestInterfaceCriticality(unittest.TestCase):
    def test_a_named_interface_is_critical(self):
        result = interface_criticality(adhesive_entry())
        self.assertTrue(result["critical"])
        self.assertIn("named-critical-interface", result["drivers"])

    def test_a_bulk_entry_is_not_critical(self):
        result = interface_criticality(bulk_entry())
        self.assertFalse(result["critical"])
        self.assertEqual(result["drivers"], [])

    def test_a_bonded_non_metallic_item_fires_its_own_driver(self):
        result = interface_criticality(adhesive_entry())
        self.assertIn("non-metallic-at-a-bonded-joint", result["drivers"])

    def test_an_exposed_environment_makes_a_bulk_entry_critical(self):
        entry = bulk_entry(interface_environment="atomic-oxygen")
        result = interface_criticality(entry)
        self.assertTrue(result["critical"])
        self.assertIn("exposed-surface-environment", result["drivers"])

    def test_a_dissimilar_metal_couple_fires_its_own_driver(self):
        result = interface_criticality(interconnect_entry())
        self.assertIn("dissimilar-metal-couple", result["drivers"])

    def test_a_like_metal_couple_does_not_fire_the_driver(self):
        result = interface_criticality(
            interconnect_entry(metal="silver", mating_metal="silver")
        )
        self.assertNotIn("dissimilar-metal-couple", result["drivers"])

    def test_absent_role_defaults_to_bulk(self):
        entry = bulk_entry()
        del entry["interface_role"]
        self.assertEqual(interface_criticality(entry)["interface_role"], BULK_INTERFACE_ROLE)

    def test_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            interface_criticality(bulk_entry(interface_role="cell-to-sunlight"))

    def test_unknown_environment_raises(self):
        with self.assertRaises(ValueError):
            interface_criticality(bulk_entry(interface_environment="monsoon"))

    def test_unknown_interface_type_raises(self):
        with self.assertRaises(ValueError):
            interface_criticality(adhesive_entry(interface_type="glued"))

    def test_mating_metal_without_a_metal_raises(self):
        entry = interconnect_entry()
        del entry["metal"]
        with self.assertRaises(ValueError):
            interface_criticality(entry)

    def test_unknown_metal_raises(self):
        with self.assertRaises(ValueError):
            interface_criticality(interconnect_entry(metal="unobtainium"))

    def test_entry_that_is_not_a_mapping_raises(self):
        with self.assertRaises(ValueError):
            interface_criticality("MAT-ADH-01")


class TestRequiredFields(unittest.TestCase):
    def test_a_bulk_entry_owes_only_identification_data(self):
        fields = required_entry_fields(bulk_entry())
        for field in INTERFACE_DATA_FIELDS:
            self.assertNotIn(field, fields)

    def test_a_critical_entry_owes_the_interface_data(self):
        fields = required_entry_fields(adhesive_entry())
        for field in INTERFACE_DATA_FIELDS:
            self.assertIn(field, fields)

    def test_a_bonded_non_metallic_item_owes_its_outgassing_figures(self):
        fields = required_entry_fields(adhesive_entry())
        self.assertIn("outgassing_tml_percent", fields)
        self.assertIn("outgassing_cvcm_percent", fields)

    def test_a_welded_metal_couple_owes_the_mating_family(self):
        self.assertIn("mating_material_family", required_entry_fields(interconnect_entry()))

    def test_a_part_owes_its_part_number(self):
        self.assertIn("part_number", required_entry_fields(interconnect_entry()))

    def test_a_process_owes_its_process_reference(self):
        entry = {
            "id": "PRC-WELD-04",
            "kind": "process",
            "designation": "parallel-gap resistance weld",
            "supplier": "array integrator",
            "specification": "SPEC-WLD-0301",
            "process_reference": "PR-WLD-0301",
            "interface_role": BULK_INTERFACE_ROLE,
        }
        self.assertIn("process_reference", required_entry_fields(entry))

    def test_required_fields_are_reported_once_each(self):
        fields = required_entry_fields(adhesive_entry())
        self.assertEqual(len(fields), len(set(fields)))

    def test_missing_fields_are_named(self):
        entry = adhesive_entry()
        del entry["qualification_reference"]
        self.assertIn("qualification_reference", missing_entry_fields(entry))

    def test_a_blank_field_counts_as_missing(self):
        entry = adhesive_entry(qualification_reference="   ")
        self.assertIn("qualification_reference", missing_entry_fields(entry))

    def test_a_complete_entry_is_missing_nothing(self):
        self.assertEqual(missing_entry_fields(adhesive_entry()), ())

    def test_entry_without_a_kind_raises(self):
        entry = adhesive_entry()
        del entry["kind"]
        with self.assertRaises(ValueError):
            required_entry_fields(entry)

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            required_entry_fields(adhesive_entry(kind="assembly"))


class TestOutgassing(unittest.TestCase):
    def test_a_clean_material_passes_both_limits(self):
        result = check_outgassing(0.3, 0.02)
        self.assertTrue(result["within"])

    def test_total_mass_loss_over_the_limit_is_caught(self):
        result = check_outgassing(1.4, 0.02)
        self.assertFalse(result["tml_within"])
        self.assertFalse(result["within"])

    def test_collected_volatile_fraction_over_the_limit_is_caught(self):
        result = check_outgassing(0.5, 0.25)
        self.assertFalse(result["cvcm_within"])

    def test_both_limits_met_exactly_still_pass(self):
        result = check_outgassing(
            OUTGASSING_TML_LIMIT_PERCENT, OUTGASSING_CVCM_LIMIT_PERCENT
        )
        self.assertTrue(result["within"])

    def test_a_volatile_fraction_above_the_mass_loss_raises(self):
        with self.assertRaises(ValueError):
            check_outgassing(0.05, 0.30)

    def test_negative_mass_loss_raises(self):
        with self.assertRaises(ValueError):
            check_outgassing(-0.1, 0.02)

    def test_non_numeric_figure_raises(self):
        with self.assertRaises(ValueError):
            check_outgassing("0.3", 0.02)


class TestGalvanicCouple(unittest.TestCase):
    def test_separation_is_the_anodic_index_difference(self):
        self.assertAlmostEqual(
            anodic_separation("aluminium", "copper"),
            abs(ANODIC_INDEX_V["aluminium"] - ANODIC_INDEX_V["copper"]),
            places=9,
        )

    def test_separation_is_symmetric(self):
        self.assertAlmostEqual(
            anodic_separation("gold", "aluminium"),
            anodic_separation("aluminium", "gold"),
            places=9,
        )

    def test_a_close_couple_is_within_the_allowance(self):
        self.assertTrue(check_galvanic_couple("silver", "gold")["within"])

    def test_a_couple_exactly_on_the_allowance_survives_float_representation(self):
        result = check_galvanic_couple("silver", "brass")
        self.assertAlmostEqual(result["separation_v"], GALVANIC_LIMIT_V, places=9)
        self.assertTrue(result["within"])

    def test_a_wide_couple_is_outside_the_allowance(self):
        self.assertFalse(check_galvanic_couple("aluminium", "copper")["within"])

    def test_a_tighter_allowance_may_be_imposed(self):
        self.assertFalse(
            check_galvanic_couple("silver", "brass", limit_v=0.1)["within"]
        )

    def test_unknown_metal_raises(self):
        with self.assertRaises(ValueError):
            check_galvanic_couple("gold", "vibranium")


class TestEvaluateListEntry(unittest.TestCase):
    def test_a_complete_critical_entry_is_complete(self):
        record = evaluate_list_entry(adhesive_entry())
        self.assertTrue(record["complete"])
        self.assertEqual(record["findings"], [])

    def test_a_critical_entry_without_interface_data_is_flagged(self):
        entry = adhesive_entry()
        del entry["mating_item"]
        del entry["qualification_reference"]
        record = evaluate_list_entry(entry)
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("interface-data-missing", codes)

    def test_an_outgassing_failure_is_flagged(self):
        record = evaluate_list_entry(adhesive_entry(outgassing_tml_percent=0.8, outgassing_cvcm_percent=0.25))
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("outgassing-over-limit", codes)

    def test_a_wide_galvanic_couple_is_flagged(self):
        record = evaluate_list_entry(
            interconnect_entry(metal="aluminium", mating_metal="copper")
        )
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("galvanic-couple-excessive", codes)

    def test_an_entry_that_mates_with_itself_is_flagged(self):
        record = evaluate_list_entry(
            adhesive_entry(mating_item="cell-to-coverglass adhesive")
        )
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("interface-mates-with-itself", codes)

    def test_a_bulk_entry_needs_no_interface_data(self):
        record = evaluate_list_entry(bulk_entry())
        self.assertTrue(record["complete"])
        self.assertFalse(record["criticality"]["critical"])

    def test_one_outgassing_figure_without_the_other_raises(self):
        entry = adhesive_entry()
        del entry["outgassing_cvcm_percent"]
        with self.assertRaises(ValueError):
            evaluate_list_entry(entry)

    def test_unknown_key_raises(self):
        with self.assertRaises(ValueError):
            evaluate_list_entry(adhesive_entry(shelf_life_months=12))

    def test_blank_identifier_raises(self):
        with self.assertRaises(ValueError):
            evaluate_list_entry(adhesive_entry(id="  "))

    def test_missing_identifier_raises(self):
        entry = adhesive_entry()
        del entry["id"]
        with self.assertRaises(ValueError):
            evaluate_list_entry(entry)

    def test_findings_carry_code_subject_and_detail(self):
        record = evaluate_list_entry(adhesive_entry(outgassing_tml_percent=0.8, outgassing_cvcm_percent=0.25))
        for finding in record["findings"]:
            self.assertEqual(sorted(finding.keys()), ["code", "detail", "subject"])


class TestAssessPmpList(unittest.TestCase):
    def test_a_sound_list_is_accepted(self):
        report = assess_pmp_list(pmp_list())
        self.assertTrue(report["accepted"])
        self.assertEqual(report["verdict"], "interface-data-complete")

    def test_critical_entries_are_named(self):
        report = assess_pmp_list(pmp_list())
        self.assertEqual(report["critical_count"], 2)
        self.assertIn("MAT-ADH-01", report["critical_entries"])

    def test_counts_by_kind_are_reported(self):
        report = assess_pmp_list(pmp_list())
        self.assertEqual(report["counts_by_kind"]["material"], 2)
        self.assertEqual(report["counts_by_kind"]["part"], 1)

    def test_one_incomplete_entry_rejects_the_list(self):
        entries = pmp_list()
        del entries[0]["qualification_reference"]
        report = assess_pmp_list(entries)
        self.assertFalse(report["accepted"])
        self.assertEqual(report["verdict"], "interface-data-incomplete")

    def test_complete_fraction_counts_entries_not_findings(self):
        entries = pmp_list()
        del entries[0]["qualification_reference"]
        report = assess_pmp_list(entries)
        self.assertAlmostEqual(report["complete_fraction"], 2.0 / 3.0, places=9)

    def test_duplicate_identifier_raises(self):
        entries = pmp_list()
        entries[1]["id"] = "MAT-ADH-01"
        with self.assertRaises(ValueError):
            assess_pmp_list(entries)

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            assess_pmp_list([])

    def test_string_list_raises(self):
        with self.assertRaises(ValueError):
            assess_pmp_list("MAT-ADH-01")


if __name__ == "__main__":
    unittest.main()
