"""Contract tests for the clause 4.15 transport, facility, handling and storage logic."""

import unittest

from e3311_transport_facilities_handling_storage_logic import (
    COMPATIBILITY_GROUPS,
    ISOLATION_GROUPS,
    assess_storage_site,
    cube_root,
    environment_verdict,
    groups_compatible,
    handling_verdict,
    licensed_limit_verdict,
    magazine_compatibility,
    net_explosive_quantity,
    normalize_group,
    quantity_distance_m,
    separation_verdict,
    transport_verdict,
    validate_non_negative,
    validate_positive,
)


def item(item_id="INI-1", group="D", neq=1.0, count=8):
    return {
        "item_id": item_id,
        "compatibility_group": group,
        "neq_kg": neq,
        "count": count,
    }


def operation(**overrides):
    base = {
        "operation_id": "OP-1",
        "bonded": True,
        "personnel_present": 2,
        "personnel_limit": 3,
        "rf_transmitter_distance_m": 40.0,
        "rf_exclusion_m": 30.0,
        "safing_device_fitted": True,
    }
    base.update(overrides)
    return base


def good_spec(**overrides):
    spec = {
        "magazine": {
            "items": [item("INI-1", "D", 1.0, 8), item("CAP-2", "S", 0.05, 20)],
            "licensed_limit_kg": 25.0,
            "k_factor": 8.0,
            "exposed_sites": [{"name": "assembly hall", "distance_m": 60.0}],
        },
        "environment": {
            "measured": {"temperature_c": 18.0, "humidity_pct": 40.0},
            "limits": {
                "temperature_min_c": -10.0,
                "temperature_max_c": 35.0,
                "humidity_max_pct": 60.0,
            },
        },
        "handling": [operation()],
        "shipments": [
            {
                "shipment_id": "SHP-7",
                "container_qualified": True,
                "safing_device_fitted": True,
                "declared_neq_kg": 8.0,
                "items": [item("INI-1", "D", 1.0, 8)],
            }
        ],
    }
    spec.update(overrides)
    return spec


class GroupTests(unittest.TestCase):
    def test_lowercase_group_normalizes(self):
        self.assertEqual(normalize_group(" d "), "D")

    def test_unknown_group_rejected(self):
        with self.assertRaises(ValueError):
            normalize_group("Q")

    def test_non_string_group_rejected(self):
        with self.assertRaises(ValueError):
            normalize_group(4)

    def test_every_isolation_group_is_a_known_group(self):
        for group in ISOLATION_GROUPS:
            self.assertIn(group, COMPATIBILITY_GROUPS)

    def test_isolation_group_shares_with_nothing_else(self):
        self.assertFalse(groups_compatible("L", "S"))
        self.assertFalse(groups_compatible("D", "A"))

    def test_isolation_group_shares_with_its_own_kind(self):
        self.assertTrue(groups_compatible("L", "L"))

    def test_group_s_mixes_with_ordinary_groups(self):
        self.assertTrue(groups_compatible("S", "B"))
        self.assertTrue(groups_compatible("D", "S"))

    def test_mixable_groups_share(self):
        self.assertTrue(groups_compatible("C", "G"))

    def test_self_only_group_does_not_mix_with_a_mixable_group(self):
        self.assertFalse(groups_compatible("B", "D"))


class NumericTests(unittest.TestCase):
    def test_validate_positive_returns_float(self):
        self.assertEqual(validate_positive("x", 2), 2.0)

    def test_validate_non_negative_accepts_zero(self):
        self.assertEqual(validate_non_negative("x", 0), 0.0)

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            validate_non_negative("x", -0.1)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", True)

    def test_cube_root_of_a_perfect_cube_is_exact(self):
        self.assertAlmostEqual(cube_root(8.0), 2.0, places=9)
        self.assertAlmostEqual(cube_root(27.0), 3.0, places=9)

    def test_cube_root_of_zero_is_zero(self):
        self.assertAlmostEqual(cube_root(0.0), 0.0, places=9)

    def test_cube_root_of_a_non_cube(self):
        self.assertAlmostEqual(cube_root(10.0) ** 3, 10.0, places=9)


class QuantityTests(unittest.TestCase):
    def test_quantity_sums_over_counts(self):
        self.assertAlmostEqual(
            net_explosive_quantity([item(neq=0.5, count=4), item(neq=1.0, count=2)]),
            4.0,
            places=9,
        )

    def test_empty_store_holds_nothing(self):
        self.assertAlmostEqual(net_explosive_quantity([]), 0.0, places=9)

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            net_explosive_quantity([item(count=-1)])

    def test_missing_field_rejected(self):
        with self.assertRaises(ValueError):
            net_explosive_quantity([{"neq_kg": 1.0}])

    def test_distance_follows_the_cube_root_law(self):
        self.assertAlmostEqual(quantity_distance_m(8.0, 8.0), 16.0, places=9)

    def test_eight_times_the_quantity_doubles_the_distance(self):
        near = quantity_distance_m(1.0, 8.0)
        far = quantity_distance_m(8.0, 8.0)
        self.assertAlmostEqual(far, 2.0 * near, places=9)

    def test_zero_k_factor_rejected(self):
        with self.assertRaises(ValueError):
            quantity_distance_m(8.0, 0.0)


class MagazineTests(unittest.TestCase):
    def test_compatible_store_is_segregated(self):
        result = magazine_compatibility([item("A1", "D"), item("A2", "S")])
        self.assertTrue(result["segregated"])
        self.assertEqual(result["conflicts"], [])

    def test_incompatible_pair_is_reported_with_both_names(self):
        result = magazine_compatibility([item("DET-1", "B"), item("CORD-2", "D")])
        self.assertFalse(result["segregated"])
        self.assertIn("DET-1", result["findings"][0])
        self.assertIn("CORD-2", result["findings"][0])

    def test_empty_magazine_rejected(self):
        with self.assertRaises(ValueError):
            magazine_compatibility([])

    def test_blank_item_id_rejected(self):
        with self.assertRaises(ValueError):
            magazine_compatibility([item(" ", "D")])


class LimitAndSeparationTests(unittest.TestCase):
    def test_quantity_exactly_on_the_licence_is_within_it(self):
        result = licensed_limit_verdict(25.0, 25.0)
        self.assertTrue(result["within_licence"])

    def test_quantity_over_the_licence_is_a_finding(self):
        result = licensed_limit_verdict(30.0, 25.0)
        self.assertFalse(result["within_licence"])

    def test_distance_exactly_on_the_requirement_is_adequate(self):
        result = separation_verdict(8.0, 8.0, 16.0, "control room")
        self.assertTrue(result["adequate"])
        self.assertAlmostEqual(result["required_m"], 16.0, places=9)

    def test_short_distance_names_the_exposed_site(self):
        result = separation_verdict(8.0, 8.0, 10.0, "control room")
        self.assertFalse(result["adequate"])
        self.assertIn("control room", result["findings"][0])

    def test_blank_site_name_rejected(self):
        with self.assertRaises(ValueError):
            separation_verdict(8.0, 8.0, 20.0, "  ")


class EnvironmentTests(unittest.TestCase):
    def test_environment_inside_the_envelope_passes(self):
        result = environment_verdict(
            {"temperature_c": 18.0, "humidity_pct": 40.0},
            {"temperature_min_c": -10.0, "temperature_max_c": 35.0, "humidity_max_pct": 60.0},
        )
        self.assertTrue(result["within_envelope"])

    def test_temperature_above_the_envelope_is_a_finding(self):
        result = environment_verdict(
            {"temperature_c": 44.0, "humidity_pct": 40.0},
            {"temperature_min_c": -10.0, "temperature_max_c": 35.0, "humidity_max_pct": 60.0},
        )
        self.assertFalse(result["within_envelope"])

    def test_humidity_above_the_envelope_is_a_finding(self):
        result = environment_verdict(
            {"temperature_c": 18.0, "humidity_pct": 80.0},
            {"temperature_min_c": -10.0, "temperature_max_c": 35.0, "humidity_max_pct": 60.0},
        )
        self.assertFalse(result["within_envelope"])

    def test_inverted_limit_range_rejected(self):
        with self.assertRaises(ValueError):
            environment_verdict(
                {"temperature_c": 18.0, "humidity_pct": 40.0},
                {"temperature_min_c": 40.0, "temperature_max_c": 10.0, "humidity_max_pct": 60.0},
            )


class HandlingTests(unittest.TestCase):
    def test_controlled_operation_passes(self):
        self.assertTrue(handling_verdict(operation())["controlled"])

    def test_unbonded_handling_point_is_a_finding(self):
        result = handling_verdict(operation(bonded=False))
        self.assertFalse(result["controlled"])
        self.assertIn("bonded", result["findings"][0])

    def test_missing_safing_device_is_a_finding(self):
        self.assertFalse(handling_verdict(operation(safing_device_fitted=False))["controlled"])

    def test_too_many_people_is_a_finding(self):
        self.assertFalse(handling_verdict(operation(personnel_present=9))["controlled"])

    def test_transmitter_inside_the_exclusion_is_a_finding(self):
        self.assertFalse(
            handling_verdict(operation(rf_transmitter_distance_m=5.0))["controlled"]
        )

    def test_transmitter_exactly_on_the_exclusion_is_acceptable(self):
        self.assertTrue(
            handling_verdict(operation(rf_transmitter_distance_m=30.0))["controlled"]
        )

    def test_missing_field_rejected(self):
        bad = operation()
        del bad["bonded"]
        with self.assertRaises(ValueError):
            handling_verdict(bad)


class TransportTests(unittest.TestCase):
    def test_clean_shipment_is_acceptable(self):
        shipment = good_spec()["shipments"][0]
        self.assertTrue(transport_verdict(shipment)["acceptable"])

    def test_declared_quantity_mismatch_is_a_finding(self):
        shipment = dict(good_spec()["shipments"][0], declared_neq_kg=2.0)
        result = transport_verdict(shipment)
        self.assertFalse(result["acceptable"])
        self.assertAlmostEqual(result["actual_neq_kg"], 8.0, places=9)

    def test_unqualified_container_is_a_finding(self):
        shipment = dict(good_spec()["shipments"][0], container_qualified=False)
        self.assertFalse(transport_verdict(shipment)["acceptable"])

    def test_incompatible_load_is_reported_as_one_load(self):
        shipment = dict(
            good_spec()["shipments"][0],
            declared_neq_kg=9.0,
            items=[item("INI-1", "D", 1.0, 8), item("DET-9", "B", 1.0, 1)],
        )
        result = transport_verdict(shipment)
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("one load" in f for f in result["findings"]))

    def test_non_mapping_shipment_rejected(self):
        with self.assertRaises(ValueError):
            transport_verdict(["SHP-7"])


class SiteTests(unittest.TestCase):
    def test_clean_site_is_controlled(self):
        result = assess_storage_site(good_spec())
        self.assertTrue(result["controlled"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["net_explosive_quantity_kg"], 9.0, places=9)

    def test_over_licence_site_is_not_controlled(self):
        spec = good_spec()
        spec["magazine"] = dict(spec["magazine"], licensed_limit_kg=1.0)
        self.assertFalse(assess_storage_site(spec)["controlled"])

    def test_close_exposed_site_is_not_controlled(self):
        spec = good_spec()
        spec["magazine"] = dict(
            spec["magazine"], exposed_sites=[{"name": "office", "distance_m": 3.0}]
        )
        self.assertFalse(assess_storage_site(spec)["controlled"])

    def test_incompatible_store_is_not_controlled(self):
        spec = good_spec()
        spec["magazine"] = dict(
            spec["magazine"],
            items=[item("INI-1", "D", 1.0, 8), item("PRI-2", "A", 0.01, 1)],
        )
        self.assertFalse(assess_storage_site(spec)["controlled"])

    def test_missing_magazine_key_rejected(self):
        spec = good_spec()
        del spec["magazine"]["k_factor"]
        with self.assertRaises(ValueError):
            assess_storage_site(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_storage_site(["magazine"])

    def test_exposed_sites_must_be_a_sequence(self):
        spec = good_spec()
        spec["magazine"] = dict(spec["magazine"], exposed_sites={"name": "office"})
        with self.assertRaises(ValueError):
            assess_storage_site(spec)


if __name__ == "__main__":
    unittest.main()
