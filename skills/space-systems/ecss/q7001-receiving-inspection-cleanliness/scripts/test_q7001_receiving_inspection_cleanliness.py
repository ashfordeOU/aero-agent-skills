"""Contract test for the goods-receipt cleanliness leaf (stdlib unittest)."""

import unittest

from q7001_receiving_inspection_cleanliness_logic import (
    ACCEPT,
    ACCEPT_AFTER_REVERIFICATION,
    INDICATOR_ABSENT,
    INDICATOR_TRIPPED,
    NONCONFORMANCE,
    QUARANTINE_PENDING_MEASUREMENT,
    RECLEAN_AND_REVERIFY,
    assess_measurement,
    assess_packaging,
    assess_receipt,
    assess_transport,
    consumed_fraction,
    escalate,
    validate_measurement,
    within_limit,
)


def measurement(**kw):
    record = {
        "limit": 1.0,
        "measured": 0.4,
        "method": "solvent rinse and gravimetric residue",
    }
    record.update(kw)
    return record


def packaging(**kw):
    record = {
        "outer_bag_intact": True,
        "inner_bag_intact": True,
        "seal_intact": True,
        "indicator_state": "intact",
    }
    record.update(kw)
    return record


def transport(**kw):
    record = {
        "max_shock_g": 2.0,
        "max_humidity_pct": 40.0,
        "days_since_verified_cleaning": 30.0,
    }
    record.update(kw)
    return record


def item(**kw):
    record = {
        "id": "SA-HINGE-014",
        "required_area_class": 8,
        "transport_limits": {
            "max_shock_g": 5.0,
            "max_humidity_pct": 60.0,
            "shelf_life_days": 365.0,
        },
    }
    record.update(kw)
    return record


def receipt(**kw):
    record = {
        "measurements": {"residue": measurement()},
        "packaging": packaging(),
        "transport": transport(),
        "inspection_area_class": 8,
    }
    record.update(kw)
    return record


class TestLimitArithmetic(unittest.TestCase):
    def test_a_measurement_under_its_limit_is_within_it(self):
        self.assertTrue(within_limit(0.4, 1.0))

    def test_a_measurement_equal_to_its_limit_is_within_it(self):
        self.assertTrue(within_limit(1.0, 1.0))

    def test_a_measurement_reassembled_from_thirds_is_still_within_it(self):
        value = 1.0 / 3.0 + 1.0 / 3.0 + 1.0 / 3.0
        self.assertTrue(within_limit(value, 1.0))

    def test_a_measurement_over_its_limit_is_not_within_it(self):
        self.assertFalse(within_limit(1.4, 1.0))

    def test_the_consumed_fraction_of_a_limit_is_reported(self):
        self.assertAlmostEqual(consumed_fraction(0.4, 1.0), 0.4, places=12)

    def test_a_negative_measurement_raises(self):
        with self.assertRaises(ValueError):
            consumed_fraction(-0.1, 1.0)

    def test_a_zero_limit_raises(self):
        with self.assertRaises(ValueError):
            consumed_fraction(0.4, 0.0)


class TestEscalation(unittest.TestCase):
    def test_a_worse_disposition_wins(self):
        self.assertEqual(escalate(ACCEPT, RECLEAN_AND_REVERIFY), RECLEAN_AND_REVERIFY)

    def test_a_milder_disposition_does_not_displace_a_worse_one(self):
        self.assertEqual(escalate(NONCONFORMANCE, ACCEPT), NONCONFORMANCE)

    def test_an_unknown_disposition_raises(self):
        with self.assertRaises(ValueError):
            escalate(ACCEPT, "have a word with the supplier")


class TestMeasurementAssessment(unittest.TestCase):
    def test_a_measurement_inside_its_limit_accepts(self):
        row = assess_measurement("residue", measurement(), 5.0)
        self.assertEqual(row["disposition"], ACCEPT)
        self.assertTrue(row["within_limit"])

    def test_a_measurement_with_no_method_is_quarantined(self):
        row = assess_measurement("residue", measurement(method=None), 5.0)
        self.assertEqual(row["disposition"], QUARANTINE_PENDING_MEASUREMENT)
        self.assertIn("residue-reported-with-no-method-named", row["findings"])

    def test_an_unmeasured_item_is_quarantined(self):
        row = assess_measurement("residue", measurement(measured=None), 5.0)
        self.assertEqual(row["disposition"], QUARANTINE_PENDING_MEASUREMENT)
        self.assertIsNone(row["consumed_fraction"])

    def test_a_modest_exceedance_goes_to_recleaning(self):
        row = assess_measurement("residue", measurement(measured=2.0), 5.0)
        self.assertEqual(row["disposition"], RECLEAN_AND_REVERIFY)

    def test_an_exceedance_exactly_at_the_recleaning_ceiling_still_recleans(self):
        row = assess_measurement("residue", measurement(measured=5.0), 5.0)
        self.assertEqual(row["disposition"], RECLEAN_AND_REVERIFY)

    def test_an_exceedance_past_the_recleaning_ceiling_is_a_nonconformance(self):
        row = assess_measurement("residue", measurement(measured=40.0), 5.0)
        self.assertEqual(row["disposition"], NONCONFORMANCE)
        self.assertIn("residue-beyond-what-recleaning-recovers", row["findings"])

    def test_a_non_mapping_measurement_raises(self):
        with self.assertRaises(ValueError):
            validate_measurement("residue", 0.4)


class TestPackagingAssessment(unittest.TestCase):
    def test_intact_packaging_accepts(self):
        row = assess_packaging(packaging())
        self.assertEqual(row["disposition"], ACCEPT)
        self.assertEqual(row["findings"], [])

    def test_a_breached_outer_bag_calls_for_re_verification(self):
        row = assess_packaging(packaging(outer_bag_intact=False))
        self.assertEqual(row["disposition"], ACCEPT_AFTER_REVERIFICATION)

    def test_a_breached_inner_bag_calls_for_recleaning(self):
        row = assess_packaging(packaging(inner_bag_intact=False))
        self.assertEqual(row["disposition"], RECLEAN_AND_REVERIFY)

    def test_a_tripped_indicator_calls_for_recleaning(self):
        row = assess_packaging(packaging(indicator_state=INDICATOR_TRIPPED))
        self.assertIn("contamination-indicator-tripped", row["findings"])

    def test_an_absent_indicator_is_a_finding_of_its_own(self):
        row = assess_packaging(packaging(indicator_state=INDICATOR_ABSENT))
        self.assertIn("no-contamination-indicator-in-the-package", row["findings"])

    def test_a_lost_purge_pressure_calls_for_recleaning(self):
        row = assess_packaging(
            packaging(purge_pressure_kpa=0.5, minimum_purge_pressure_kpa=2.0)
        )
        self.assertIn("purge-pressure-lost-in-transit", row["findings"])
        self.assertEqual(row["disposition"], RECLEAN_AND_REVERIFY)

    def test_a_required_purge_with_no_reading_is_a_finding(self):
        row = assess_packaging(packaging(minimum_purge_pressure_kpa=2.0))
        self.assertIn("purge-required-but-no-pressure-recorded", row["findings"])

    def test_a_purge_exactly_at_its_floor_is_accepted(self):
        row = assess_packaging(
            packaging(purge_pressure_kpa=2.0, minimum_purge_pressure_kpa=2.0)
        )
        self.assertEqual(row["findings"], [])

    def test_an_unknown_indicator_state_raises(self):
        with self.assertRaises(ValueError):
            assess_packaging(packaging(indicator_state="probably-fine"))

    def test_a_non_boolean_seal_flag_raises(self):
        with self.assertRaises(ValueError):
            assess_packaging(packaging(seal_intact="yes"))


class TestTransportAssessment(unittest.TestCase):
    def test_a_quiet_transport_accepts(self):
        row = assess_transport(transport(), item()["transport_limits"])
        self.assertEqual(row["findings"], [])

    def test_a_shock_above_the_limit_is_a_finding(self):
        row = assess_transport(
            transport(max_shock_g=12.0), item()["transport_limits"]
        )
        self.assertIn("transport-shock-above-what-the-item-allows", row["findings"])

    def test_humidity_above_the_limit_is_a_finding(self):
        row = assess_transport(
            transport(max_humidity_pct=85.0), item()["transport_limits"]
        )
        self.assertIn("transport-humidity-above-what-the-item-allows", row["findings"])

    def test_a_certificate_past_its_shelf_life_is_a_finding(self):
        row = assess_transport(
            transport(days_since_verified_cleaning=400.0), item()["transport_limits"]
        )
        self.assertIn(
            "cleanliness-certificate-older-than-the-shelf-life", row["findings"]
        )

    def test_a_shock_exactly_at_the_limit_passes(self):
        row = assess_transport(transport(max_shock_g=5.0), item()["transport_limits"])
        self.assertEqual(row["findings"], [])


class TestReceipt(unittest.TestCase):
    def test_a_clean_receipt_is_accepted_as_is(self):
        report = assess_receipt(item(), receipt())
        self.assertTrue(report["accepted_as_is"])
        self.assertEqual(report["disposition"], ACCEPT)
        self.assertTrue(report["clear"])

    def test_the_worst_measurement_is_named(self):
        report = assess_receipt(
            item(),
            receipt(
                measurements={
                    "residue": measurement(measured=0.2),
                    "obscuration": measurement(limit=2.0, measured=1.8),
                }
            ),
        )
        self.assertEqual(report["worst_measurement"], "obscuration")
        self.assertAlmostEqual(report["worst_consumed_fraction"], 0.9, places=9)

    def test_a_dirty_inspection_area_calls_for_recleaning(self):
        report = assess_receipt(item(), receipt(inspection_area_class=9))
        self.assertIn(
            "receipt-opened-in-an-area-dirtier-than-the-item-needs",
            report["findings"],
        )
        self.assertEqual(report["disposition"], RECLEAN_AND_REVERIFY)

    def test_a_cleaner_inspection_area_is_fine(self):
        report = assess_receipt(item(), receipt(inspection_area_class=6))
        self.assertTrue(report["clear"])

    def test_an_unrecorded_inspection_area_is_a_finding(self):
        record = receipt()
        del record["inspection_area_class"]
        report = assess_receipt(item(), record)
        self.assertIn("inspection-area-class-not-recorded", report["findings"])

    def test_the_worst_input_drives_the_disposition(self):
        report = assess_receipt(
            item(),
            receipt(
                measurements={"residue": measurement(measured=40.0)},
                packaging=packaging(outer_bag_intact=False),
            ),
        )
        self.assertEqual(report["disposition"], NONCONFORMANCE)

    def test_a_clean_measurement_does_not_clear_a_breached_inner_bag(self):
        report = assess_receipt(
            item(), receipt(packaging=packaging(inner_bag_intact=False))
        )
        self.assertFalse(report["accepted_as_is"])
        self.assertEqual(report["disposition"], RECLEAN_AND_REVERIFY)

    def test_a_receipt_with_no_measurements_raises(self):
        with self.assertRaises(ValueError):
            assess_receipt(item(), receipt(measurements={}))

    def test_a_non_mapping_item_raises(self):
        with self.assertRaises(ValueError):
            assess_receipt("SA-HINGE-014", receipt())

    def test_a_non_integer_inspection_area_class_raises(self):
        with self.assertRaises(ValueError):
            assess_receipt(item(), receipt(inspection_area_class=7.5))


if __name__ == "__main__":
    unittest.main()
