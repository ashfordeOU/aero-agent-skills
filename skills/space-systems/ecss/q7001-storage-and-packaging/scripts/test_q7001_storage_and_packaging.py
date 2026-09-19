"""Contract test for the storage and packaging leaf (stdlib unittest)."""

import unittest

from q7001_storage_and_packaging_logic import (
    BOUND_BY_POLICY,
    BOUND_BY_PURGE,
    BOUND_BY_RESIDUE,
    assess_storage,
    days_until_limit,
    minimum_barrier_layers,
    projected_level,
    purge_hold_days,
    reverification_interval,
    validate_packaging,
)


def item(**kw):
    record = {
        "id": "FPA-MODULE-3",
        "sensitivity": "precision-clean",
        "residue_limit": 1.0,
        "residue_at_packing": 0.2,
        "residue_accumulation_per_day": 0.001,
        "purge_required": True,
        "humidity_sensitive": False,
        "required_area_class": 8,
    }
    record.update(kw)
    return record


def packaging(**kw):
    record = {
        "barrier_layers": 3,
        "contact_materials": ["cleanroom-polyethylene-film"],
        "desiccant_present": False,
        "purge_pressure_kpa": 5.0,
        "minimum_purge_pressure_kpa": 1.0,
        "purge_decay_kpa_per_day": 0.01,
    }
    record.update(kw)
    return record


def store(**kw):
    record = {
        "planned_storage_days": 180.0,
        "policy_ceiling_days": 365.0,
        "area_class": 8,
    }
    record.update(kw)
    return record


class TestBarrierLayers(unittest.TestCase):
    def test_precision_clean_demands_three_layers(self):
        self.assertEqual(minimum_barrier_layers("precision-clean"), 3)

    def test_a_looser_sensitivity_demands_fewer_layers(self):
        self.assertLess(
            minimum_barrier_layers("general"), minimum_barrier_layers("clean")
        )

    def test_an_unknown_sensitivity_raises(self):
        with self.assertRaises(ValueError):
            minimum_barrier_layers("fairly-clean-ish")


class TestProjection(unittest.TestCase):
    def test_the_projection_is_linear_in_the_days(self):
        self.assertAlmostEqual(projected_level(0.2, 0.001, 180.0), 0.38, places=9)

    def test_no_accumulation_leaves_the_level_alone(self):
        self.assertAlmostEqual(projected_level(0.2, 0.0, 900.0), 0.2, places=12)

    def test_a_negative_accumulation_rate_raises(self):
        with self.assertRaises(ValueError):
            projected_level(0.2, -0.001, 180.0)

    def test_the_days_to_the_limit_close_the_gap_at_the_rate(self):
        self.assertAlmostEqual(days_until_limit(0.2, 0.001, 1.0), 800.0, places=6)

    def test_an_item_already_at_its_limit_has_no_days_left(self):
        self.assertAlmostEqual(days_until_limit(1.0, 0.001, 1.0), 0.0, places=9)

    def test_an_item_already_past_its_limit_cannot_be_stored(self):
        with self.assertRaises(ValueError):
            days_until_limit(1.4, 0.001, 1.0)

    def test_a_stable_item_never_reaches_its_limit(self):
        self.assertEqual(days_until_limit(0.2, 0.0, 1.0), float("inf"))


class TestPurgeHold(unittest.TestCase):
    def test_the_hold_is_the_margin_over_the_decay_rate(self):
        self.assertAlmostEqual(purge_hold_days(5.0, 1.0, 0.01), 400.0, places=6)

    def test_a_faster_decay_shortens_the_hold(self):
        self.assertLess(purge_hold_days(5.0, 1.0, 0.05), purge_hold_days(5.0, 1.0, 0.01))

    def test_a_sealed_bag_at_its_floor_has_no_hold(self):
        self.assertAlmostEqual(purge_hold_days(1.0, 1.0, 0.01), 0.0, places=9)

    def test_a_bag_sealed_below_its_floor_raises(self):
        with self.assertRaises(ValueError):
            purge_hold_days(0.5, 1.0, 0.01)

    def test_a_bag_that_does_not_leak_holds_indefinitely(self):
        self.assertEqual(purge_hold_days(5.0, 1.0, 0.0), float("inf"))


class TestInterval(unittest.TestCase):
    def test_the_policy_ceiling_binds_a_well_packaged_item(self):
        interval = reverification_interval(800.0, 400.0, 365.0)
        self.assertEqual(interval["bound_by"], BOUND_BY_POLICY)
        self.assertAlmostEqual(interval["interval_days"], 365.0, places=9)

    def test_the_purge_binds_when_it_runs_out_first(self):
        interval = reverification_interval(800.0, 120.0, 365.0)
        self.assertEqual(interval["bound_by"], BOUND_BY_PURGE)

    def test_the_residue_projection_binds_when_it_runs_out_first(self):
        interval = reverification_interval(90.0, 400.0, 365.0)
        self.assertEqual(interval["bound_by"], BOUND_BY_RESIDUE)
        self.assertEqual(interval["whole_days"], 90)

    def test_a_fractional_interval_is_reported_in_whole_days_too(self):
        interval = reverification_interval(90.6, 400.0, 365.0)
        self.assertEqual(interval["whole_days"], 90)

    def test_a_negative_purge_hold_raises(self):
        with self.assertRaises(ValueError):
            reverification_interval(800.0, -1.0, 365.0)

    def test_a_zero_policy_ceiling_raises(self):
        with self.assertRaises(ValueError):
            reverification_interval(800.0, 400.0, 0.0)


class TestPackagingValidation(unittest.TestCase):
    def test_adequate_packaging_has_no_findings(self):
        row = validate_packaging(packaging(), "precision-clean")
        self.assertEqual(row["findings"], [])
        self.assertEqual(row["required_barrier_layers"], 3)

    def test_too_few_layers_is_a_finding(self):
        row = validate_packaging(packaging(barrier_layers=1), "precision-clean")
        self.assertIn(
            "barrier-layers-below-the-minimum-for-the-sensitivity", row["findings"]
        )

    def test_a_refused_contact_material_is_named(self):
        row = validate_packaging(
            packaging(
                contact_materials=["plasticised-pvc-film", "cleanroom-polyethylene-film"]
            ),
            "precision-clean",
        )
        self.assertEqual(row["refused_materials_present"], ["plasticised-pvc-film"])
        self.assertIn(
            "packaging-material-refused-in-contact-with-flight-hardware",
            row["findings"],
        )

    def test_zero_barrier_layers_raises(self):
        with self.assertRaises(ValueError):
            validate_packaging(packaging(barrier_layers=0), "precision-clean")

    def test_packaging_with_no_contact_material_raises(self):
        with self.assertRaises(ValueError):
            validate_packaging(packaging(contact_materials=[]), "precision-clean")


class TestAssessStorage(unittest.TestCase):
    def test_a_sound_storage_configuration_is_clear(self):
        report = assess_storage(item(), packaging(), store())
        self.assertTrue(report["clear"])
        self.assertEqual(report["verdict"], "storage-configuration-acceptable")
        self.assertEqual(report["reverification"]["bound_by"], BOUND_BY_POLICY)

    def test_the_projected_level_at_the_end_is_reported(self):
        report = assess_storage(item(), packaging(), store())
        self.assertAlmostEqual(report["projected_residue_at_end"], 0.38, places=9)

    def test_a_leaky_bag_makes_the_purge_bind_the_interval(self):
        report = assess_storage(
            item(), packaging(purge_decay_kpa_per_day=0.05), store()
        )
        self.assertEqual(report["reverification"]["bound_by"], BOUND_BY_PURGE)

    def test_storage_beyond_the_interval_is_a_finding(self):
        report = assess_storage(
            item(), packaging(), store(planned_storage_days=500.0)
        )
        self.assertIn(
            "planned-storage-longer-than-the-re-verification-interval",
            report["findings"],
        )

    def test_a_projection_past_the_requirement_is_a_finding(self):
        report = assess_storage(
            item(residue_accumulation_per_day=0.01),
            packaging(),
            store(planned_storage_days=300.0, policy_ceiling_days=400.0),
        )
        self.assertIn(
            "projected-level-at-end-of-storage-exceeds-the-requirement",
            report["findings"],
        )

    def test_a_humidity_sensitive_item_without_desiccant_is_a_finding(self):
        report = assess_storage(item(humidity_sensitive=True), packaging(), store())
        self.assertIn("no-desiccant-in-a-humidity-sensitive-package", report["findings"])

    def test_a_humidity_sensitive_item_with_desiccant_is_clear(self):
        report = assess_storage(
            item(humidity_sensitive=True), packaging(desiccant_present=True), store()
        )
        self.assertTrue(report["clear"])

    def test_a_purge_required_item_with_no_purge_state_is_a_finding(self):
        bag = packaging()
        del bag["purge_pressure_kpa"]
        report = assess_storage(item(), bag, store())
        self.assertIn(
            "purge-required-but-the-bag-declares-no-purge-state", report["findings"]
        )

    def test_a_store_dirtier_than_the_item_cannot_unbag_it(self):
        report = assess_storage(item(), packaging(), store(area_class=9))
        self.assertIn(
            "store-cannot-be-used-to-unbag-the-item-it-holds", report["findings"]
        )

    def test_an_unrecorded_store_class_is_a_finding(self):
        record = store()
        del record["area_class"]
        report = assess_storage(item(), packaging(), record)
        self.assertIn("store-area-class-not-recorded", report["findings"])

    def test_an_item_already_over_its_limit_raises(self):
        with self.assertRaises(ValueError):
            assess_storage(item(residue_at_packing=2.0), packaging(), store())

    def test_a_non_mapping_store_raises(self):
        with self.assertRaises(ValueError):
            assess_storage(item(), packaging(), "the big shelf")

    def test_a_negative_planned_storage_raises(self):
        with self.assertRaises(ValueError):
            assess_storage(item(), packaging(), store(planned_storage_days=-10.0))

    def test_a_non_boolean_purge_flag_raises(self):
        with self.assertRaises(ValueError):
            assess_storage(item(purge_required="yes"), packaging(), store())


if __name__ == "__main__":
    unittest.main()
