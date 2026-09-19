"""Contract tests for the propulsion cleanliness interface reconciliation."""

import unittest

from q7001_propulsion_cleanliness_interface_logic import (
    LIMIT_TOLERANCE_UM,
    PROPULSION_SOURCE,
    SYSTEM_SOURCE,
    assess_propulsion_interface,
    governing_nvr_limit,
    governing_particle_limit,
    orifice_blockage_fraction,
    reconcile_interface,
    required_filter_rating_um,
    validate_interface,
)


def interface(**overrides):
    base = {
        "name": "thruster-valve-inlet",
        "smallest_orifice_um": 200.0,
        "installed_filter_rating_um": 25.0,
        "system_limit_um": 50.0,
        "propulsion_limit_um": 50.0,
        "system_nvr_mg_m2": 1.0,
        "propulsion_nvr_mg_m2": 1.0,
        "safety_factor": 3.0,
        "max_blockage_fraction": 0.1,
    }
    base.update(overrides)
    return base


def second_interface(**overrides):
    base = interface(
        name="latch-valve-inlet",
        smallest_orifice_um=300.0,
        installed_filter_rating_um=50.0,
    )
    base.update(overrides)
    return base


class GoverningLimitTests(unittest.TestCase):
    def test_tighter_propulsion_limit_governs(self):
        result = governing_particle_limit(50.0, 25.0)
        self.assertAlmostEqual(result["limit_um"], 25.0)
        self.assertEqual(result["source"], PROPULSION_SOURCE)

    def test_tighter_system_limit_governs(self):
        result = governing_particle_limit(10.0, 50.0)
        self.assertAlmostEqual(result["limit_um"], 10.0)
        self.assertEqual(result["source"], SYSTEM_SOURCE)

    def test_a_tie_is_credited_to_the_system_specification(self):
        result = governing_particle_limit(50.0, 50.0)
        self.assertAlmostEqual(result["limit_um"], 50.0)
        self.assertEqual(result["source"], SYSTEM_SOURCE)

    def test_a_tie_within_tolerance_is_still_a_tie(self):
        result = governing_particle_limit(50.0, 50.0 - LIMIT_TOLERANCE_UM / 2.0)
        self.assertEqual(result["source"], SYSTEM_SOURCE)

    def test_zero_system_limit_rejected(self):
        with self.assertRaises(ValueError):
            governing_particle_limit(0.0, 50.0)

    def test_negative_propulsion_limit_rejected(self):
        with self.assertRaises(ValueError):
            governing_particle_limit(50.0, -25.0)

    def test_tighter_propulsion_residue_governs(self):
        result = governing_nvr_limit(1.0, 0.5)
        self.assertAlmostEqual(result["limit_mg_m2"], 0.5)
        self.assertEqual(result["source"], PROPULSION_SOURCE)

    def test_tighter_system_residue_governs(self):
        result = governing_nvr_limit(0.2, 1.0)
        self.assertAlmostEqual(result["limit_mg_m2"], 0.2)
        self.assertEqual(result["source"], SYSTEM_SOURCE)

    def test_non_numeric_residue_rejected(self):
        with self.assertRaises(ValueError):
            governing_nvr_limit("1.0", 0.5)


class FilterAndBlockageTests(unittest.TestCase):
    def test_rating_is_the_passage_over_the_factor(self):
        self.assertAlmostEqual(
            required_filter_rating_um(300.0, 3.0), 100.0, places=12
        )

    def test_a_higher_factor_demands_a_finer_filter(self):
        loose = required_filter_rating_um(300.0, 2.0)
        tight = required_filter_rating_um(300.0, 5.0)
        self.assertGreater(loose, tight)

    def test_a_factor_below_one_is_refused(self):
        with self.assertRaises(ValueError):
            required_filter_rating_um(300.0, 0.5)

    def test_zero_passage_rejected(self):
        with self.assertRaises(ValueError):
            required_filter_rating_um(0.0, 3.0)

    def test_blockage_is_an_area_ratio(self):
        self.assertAlmostEqual(
            orifice_blockage_fraction(200.0, 50.0), 0.0625, places=12
        )

    def test_a_particle_as_wide_as_the_passage_blocks_it_entirely(self):
        self.assertAlmostEqual(orifice_blockage_fraction(200.0, 200.0), 1.0)

    def test_blockage_saturates_at_one(self):
        self.assertAlmostEqual(orifice_blockage_fraction(200.0, 600.0), 1.0)

    def test_zero_particle_rejected(self):
        with self.assertRaises(ValueError):
            orifice_blockage_fraction(200.0, 0.0)


class ValidationTests(unittest.TestCase):
    def test_defaults_are_applied(self):
        record = validate_interface(
            {
                "name": "pressurant-fill-drain",
                "smallest_orifice_um": 200.0,
                "installed_filter_rating_um": 25.0,
                "system_limit_um": 50.0,
                "propulsion_limit_um": 50.0,
                "system_nvr_mg_m2": 1.0,
                "propulsion_nvr_mg_m2": 1.0,
            }
        )
        self.assertAlmostEqual(record["safety_factor"], 3.0)
        self.assertAlmostEqual(record["max_blockage_fraction"], 0.1)

    def test_missing_key_rejected(self):
        bad = interface()
        del bad["system_nvr_mg_m2"]
        with self.assertRaises(ValueError):
            validate_interface(bad)

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_interface(interface(name="  "))

    def test_non_mapping_interface_rejected(self):
        with self.assertRaises(ValueError):
            validate_interface(["name"])

    def test_safety_factor_below_one_refused_at_reconciliation(self):
        with self.assertRaises(ValueError):
            reconcile_interface(interface(safety_factor=0.5))

    def test_blockage_allowable_above_one_refused(self):
        with self.assertRaises(ValueError):
            reconcile_interface(interface(max_blockage_fraction=1.5))


class ReconciliationTests(unittest.TestCase):
    def test_baseline_interface_is_clean(self):
        result = reconcile_interface(interface())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_governing_source_is_reported(self):
        result = reconcile_interface(interface())
        self.assertEqual(result["governing_particle_source"], SYSTEM_SOURCE)

    def test_propulsion_driven_particle_limit_is_flagged(self):
        result = reconcile_interface(interface(propulsion_limit_um=25.0))
        self.assertEqual(result["governing_particle_source"], PROPULSION_SOURCE)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("governs nothing here" in f for f in result["findings"]))

    def test_propulsion_driven_residue_limit_is_flagged(self):
        result = reconcile_interface(interface(propulsion_nvr_mg_m2=0.25))
        self.assertEqual(result["governing_nvr_source"], PROPULSION_SOURCE)
        self.assertTrue(any("residue limit" in f for f in result["findings"]))

    def test_coarse_filter_against_the_passage_is_flagged(self):
        result = reconcile_interface(interface(installed_filter_rating_um=120.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("coarser than" in f for f in result["findings"]))

    def test_filter_coarser_than_the_governing_limit_is_flagged(self):
        result = reconcile_interface(
            interface(installed_filter_rating_um=60.0, smallest_orifice_um=600.0)
        )
        self.assertTrue(
            any("larger than the governing limit" in f for f in result["findings"])
        )

    def test_filter_exactly_at_the_required_rating_is_accepted(self):
        required = required_filter_rating_um(200.0, 3.0)
        result = reconcile_interface(
            interface(
                installed_filter_rating_um=required,
                system_limit_um=required,
                propulsion_limit_um=required,
                max_blockage_fraction=0.2,
            )
        )
        self.assertAlmostEqual(
            result["installed_filter_rating_um"],
            result["required_filter_rating_um"],
            places=9,
        )
        self.assertTrue(result["compliant"])

    def test_blockage_over_the_allowable_is_flagged(self):
        result = reconcile_interface(interface(max_blockage_fraction=0.01))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("blocks" in f for f in result["findings"]))

    def test_blockage_exactly_at_the_allowable_is_accepted(self):
        probe = reconcile_interface(interface())
        result = reconcile_interface(
            interface(max_blockage_fraction=probe["blockage_fraction"])
        )
        self.assertAlmostEqual(
            result["blockage_fraction"], result["max_blockage_fraction"], places=12
        )
        self.assertTrue(result["compliant"])

    def test_a_narrower_passage_blocks_more(self):
        wide = reconcile_interface(interface(smallest_orifice_um=600.0))
        narrow = reconcile_interface(interface(smallest_orifice_um=200.0))
        self.assertGreater(narrow["blockage_fraction"], wide["blockage_fraction"])


class RollUpTests(unittest.TestCase):
    def test_baseline_system_is_compliant(self):
        result = assess_propulsion_interface(
            {"interfaces": [interface(), second_interface()]}
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_the_tightest_interface_drives_the_system(self):
        result = assess_propulsion_interface(
            {
                "interfaces": [
                    interface(),
                    second_interface(system_limit_um=15.0),
                ]
            }
        )
        self.assertAlmostEqual(result["system_particle_limit_um"], 15.0)
        self.assertEqual(result["system_particle_driver"], "latch-valve-inlet")

    def test_the_tightest_residue_interface_is_named(self):
        result = assess_propulsion_interface(
            {
                "interfaces": [
                    interface(),
                    second_interface(system_nvr_mg_m2=0.2),
                ]
            }
        )
        self.assertAlmostEqual(result["system_nvr_limit_mg_m2"], 0.2)
        self.assertEqual(result["system_nvr_driver"], "latch-valve-inlet")

    def test_propulsion_driven_interfaces_are_listed(self):
        result = assess_propulsion_interface(
            {
                "interfaces": [
                    interface(propulsion_limit_um=20.0),
                    second_interface(),
                ]
            }
        )
        self.assertEqual(
            result["propulsion_driven_interfaces"], ["thruster-valve-inlet"]
        )

    def test_findings_are_aggregated(self):
        result = assess_propulsion_interface(
            {
                "interfaces": [
                    interface(propulsion_limit_um=20.0),
                    second_interface(propulsion_nvr_mg_m2=0.1),
                ]
            }
        )
        self.assertFalse(result["compliant"])
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_duplicate_interface_names_rejected(self):
        with self.assertRaises(ValueError):
            assess_propulsion_interface({"interfaces": [interface(), interface()]})

    def test_empty_interface_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_propulsion_interface({"interfaces": []})

    def test_missing_interfaces_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_propulsion_interface({})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_propulsion_interface(["interfaces"])

    def test_every_interface_is_reported(self):
        result = assess_propulsion_interface(
            {"interfaces": [interface(), second_interface()]}
        )
        self.assertEqual(
            [entry["name"] for entry in result["interfaces"]],
            ["thruster-valve-inlet", "latch-valve-inlet"],
        )


if __name__ == "__main__":
    unittest.main()
