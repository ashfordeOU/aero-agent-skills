"""Contract test for the flammability data-recording leaf (stdlib unittest)."""

import datetime
import unittest

from q7021_flammability_data_recording_logic import (
    BURN_LENGTH_LIMIT_MM,
    CONFIRMED,
    CONFLICT,
    COVERED,
    DUPLICATE_ENTRY,
    KEY_FIELDS,
    MIN_SPECIMENS,
    NEW_ENTRY,
    NOT_COVERED,
    NOT_PROPAGATING,
    NOT_PROPAGATING_RESTRICTED,
    PROPAGATING,
    STALE,
    SUPERSEDES,
    atmosphere_key,
    covers_use_atmosphere,
    data_set_key,
    declared_list_link,
    oxygen_partial_pressure,
    parse_test_date,
    rate_run,
    reconcile,
    record_results,
    thickness_band,
    validate_record,
    validate_specimen,
)


def specimen(**kw):
    s = {
        "burn_length_mm": 42.0,
        "self_extinguished": True,
        "drip_ignited_indicator": False,
    }
    s.update(kw)
    return s


def record(**kw):
    r = {
        "material_designation": "PFX-220 polyimide film",
        "manufacturer": "Beispiel Folien",
        "product_form": "film 0.05 mm backed",
        "processing_state": "as supplied",
        "thickness_mm": 0.5,
        "oxygen_volume_pct": 30.0,
        "total_pressure_kpa": 70.0,
        "test_report_reference": "FL-2026-0018",
        "test_date": "2026-04-03",
        "specimens": [specimen(), specimen(), specimen()],
    }
    r.update(kw)
    return r


class TestAtmosphere(unittest.TestCase):
    def test_partial_pressure_is_the_fraction_of_the_total(self):
        self.assertAlmostEqual(oxygen_partial_pressure(30.0, 70.0), 21.0, places=9)

    def test_air_at_sea_level_rounds_to_the_record_resolution(self):
        self.assertAlmostEqual(
            oxygen_partial_pressure(20.9, 101.3), 21.17, places=9
        )

    def test_an_oxygen_fraction_above_one_hundred_raises(self):
        with self.assertRaises(ValueError):
            oxygen_partial_pressure(120.0, 70.0)

    def test_a_zero_total_pressure_raises(self):
        with self.assertRaises(ValueError):
            oxygen_partial_pressure(30.0, 0.0)

    def test_a_non_numeric_pressure_raises(self):
        with self.assertRaises(ValueError):
            oxygen_partial_pressure(30.0, "70")

    def test_the_atmosphere_key_carries_partial_and_total_pressure(self):
        self.assertEqual(atmosphere_key(30.0, 70.0), (21.0, 70.0))


class TestKeyAndGeometry(unittest.TestCase):
    def test_the_key_covers_every_material_field_plus_geometry_and_atmosphere(self):
        self.assertEqual(len(data_set_key(record())), len(KEY_FIELDS) + 3)

    def test_the_key_ignores_case_and_spacing(self):
        self.assertEqual(
            data_set_key(record()),
            data_set_key(record(manufacturer="  BEISPIEL   FOLIEN ")),
        )

    def test_a_different_atmosphere_is_a_different_entry(self):
        self.assertNotEqual(
            data_set_key(record()), data_set_key(record(oxygen_volume_pct=21.0))
        )

    def test_a_different_thickness_is_a_different_entry(self):
        self.assertNotEqual(
            data_set_key(record()), data_set_key(record(thickness_mm=2.0))
        )

    def test_a_blank_material_field_raises(self):
        with self.assertRaises(ValueError):
            data_set_key(record(product_form="  "))

    def test_a_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            data_set_key("PFX-220")

    def test_thickness_is_rounded_to_the_record_resolution(self):
        self.assertAlmostEqual(thickness_band(0.5049), 0.5, places=9)

    def test_a_zero_thickness_raises(self):
        with self.assertRaises(ValueError):
            thickness_band(0.0)


class TestRating(unittest.TestCase):
    def test_a_clean_run_is_not_propagating(self):
        self.assertEqual(rate_run([specimen()] * 3)["rating"], NOT_PROPAGATING)

    def test_a_specimen_that_never_extinguished_makes_the_run_propagating(self):
        run = [specimen(), specimen(self_extinguished=False), specimen()]
        self.assertEqual(rate_run(run)["rating"], PROPAGATING)

    def test_burning_past_the_observation_limit_is_propagating(self):
        run = [
            specimen(),
            specimen(burn_length_mm=BURN_LENGTH_LIMIT_MM + 5.0),
            specimen(),
        ]
        self.assertEqual(rate_run(run)["rating"], PROPAGATING)

    def test_burning_exactly_to_the_observation_limit_is_not_propagating(self):
        run = [
            specimen(),
            specimen(burn_length_mm=BURN_LENGTH_LIMIT_MM),
            specimen(),
        ]
        result = rate_run(run)
        self.assertEqual(result["rating"], NOT_PROPAGATING)
        self.assertAlmostEqual(
            result["worst_burn_length_mm"], BURN_LENGTH_LIMIT_MM, places=9
        )

    def test_drip_ignition_restricts_rather_than_fails_the_run(self):
        run = [specimen(), specimen(drip_ignited_indicator=True), specimen()]
        self.assertEqual(rate_run(run)["rating"], NOT_PROPAGATING_RESTRICTED)

    def test_the_worst_specimen_governs_the_recorded_burn_length(self):
        run = [specimen(burn_length_mm=10.0), specimen(burn_length_mm=88.0), specimen()]
        self.assertAlmostEqual(rate_run(run)["worst_burn_length_mm"], 88.0, places=9)

    def test_too_few_specimens_raises(self):
        with self.assertRaises(ValueError):
            rate_run([specimen()] * (MIN_SPECIMENS - 1))

    def test_a_non_list_specimen_set_raises(self):
        with self.assertRaises(ValueError):
            rate_run(specimen())

    def test_a_negative_burn_length_raises(self):
        with self.assertRaises(ValueError):
            validate_specimen(specimen(burn_length_mm=-1.0))

    def test_a_non_boolean_extinction_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_specimen(specimen(self_extinguished="yes"))


class TestCoverage(unittest.TestCase):
    def test_a_more_severe_test_covers_a_milder_use(self):
        entry = validate_record(record())
        self.assertEqual(
            covers_use_atmosphere(entry, 20.9, 70.0)["verdict"], COVERED
        )

    def test_sea_level_air_is_more_severe_than_a_reduced_pressure_test(self):
        entry = validate_record(record())
        self.assertEqual(
            covers_use_atmosphere(entry, 20.9, 101.3)["verdict"], NOT_COVERED
        )

    def test_a_milder_test_does_not_cover_a_more_severe_use(self):
        entry = validate_record(record(oxygen_volume_pct=21.0, total_pressure_kpa=70.0))
        self.assertEqual(
            covers_use_atmosphere(entry, 40.0, 101.3)["verdict"], NOT_COVERED
        )

    def test_an_identical_atmosphere_is_covered(self):
        entry = validate_record(record())
        result = covers_use_atmosphere(entry, 30.0, 70.0)
        self.assertEqual(result["verdict"], COVERED)
        self.assertAlmostEqual(result["use_kpa"], result["tested_kpa"], places=9)


class TestDeclaredListLink(unittest.TestCase):
    def test_a_clean_entry_carries_no_restriction(self):
        link = declared_list_link(validate_record(record()))
        self.assertIsNone(link["restriction"])

    def test_a_dripping_entry_carries_an_installation_restriction(self):
        run = [specimen(), specimen(drip_ignited_indicator=True), specimen()]
        link = declared_list_link(validate_record(record(specimens=run)))
        self.assertEqual(
            link["restriction"], "no-ignitable-item-below-the-installed-material"
        )

    def test_a_propagating_entry_demands_a_justification(self):
        run = [specimen(self_extinguished=False)] * 3
        link = declared_list_link(validate_record(record(specimens=run)))
        self.assertEqual(
            link["restriction"], "use-requires-an-accepted-justification"
        )

    def test_the_link_names_the_source_report(self):
        link = declared_list_link(validate_record(record()))
        self.assertEqual(link["source_report"], "FL-2026-0018")


class TestReconciliation(unittest.TestCase):
    def test_nothing_recorded_makes_a_new_entry(self):
        self.assertEqual(reconcile(None, record()), NEW_ENTRY)

    def test_the_same_report_again_is_a_duplicate(self):
        self.assertEqual(reconcile(record(), record()), DUPLICATE_ENTRY)

    def test_another_report_with_the_same_result_confirms(self):
        self.assertEqual(
            reconcile(record(), record(test_report_reference="FL-2026-0044")),
            CONFIRMED,
        )

    def test_a_later_report_with_a_new_result_supersedes(self):
        later = record(
            test_report_reference="FL-2026-0090",
            test_date="2026-08-01",
            specimens=[specimen(self_extinguished=False)] * 3,
        )
        self.assertEqual(reconcile(record(), later), SUPERSEDES)

    def test_an_earlier_report_with_a_new_result_is_stale(self):
        earlier = record(
            test_report_reference="FL-2025-0002",
            test_date="2025-02-01",
            specimens=[specimen(self_extinguished=False)] * 3,
        )
        self.assertEqual(reconcile(record(), earlier), STALE)

    def test_two_results_on_the_same_date_conflict(self):
        other = record(
            test_report_reference="FL-2026-0019",
            specimens=[specimen(self_extinguished=False)] * 3,
        )
        self.assertEqual(reconcile(record(), other), CONFLICT)

    def test_reconciling_across_two_keys_raises(self):
        with self.assertRaises(ValueError):
            reconcile(record(), record(thickness_mm=2.0))


class TestRecording(unittest.TestCase):
    def test_a_first_submission_lands_in_the_data_set(self):
        report = record_results([record()])
        self.assertEqual(len(report["recorded_keys"]), 1)
        self.assertTrue(report["clean"])

    def test_an_unreportable_run_is_not_recorded(self):
        report = record_results([record(report_reportable=False)])
        self.assertEqual(report["recorded_keys"], [])
        self.assertEqual(report["actions"][0]["action"], "not-recorded")
        self.assertIn(
            "entry-offered-from-a-run-that-is-not-reportable", report["findings"]
        )

    def test_a_stale_submission_does_not_overwrite(self):
        earlier = record(
            test_report_reference="FL-2025-0002",
            test_date="2025-02-01",
            specimens=[specimen(self_extinguished=False)] * 3,
        )
        report = record_results([record(), earlier])
        key = report["recorded_keys"][0]
        self.assertEqual(report["data_set"][key]["rating"], NOT_PROPAGATING)
        self.assertIn(
            "earlier-run-offered-against-a-newer-entry", report["findings"]
        )

    def test_two_atmospheres_produce_two_entries(self):
        report = record_results([record(), record(oxygen_volume_pct=21.0)])
        self.assertEqual(len(report["recorded_keys"]), 2)

    def test_the_declared_list_links_follow_the_data_set(self):
        report = record_results([record()])
        self.assertEqual(len(report["declared_list_links"]), 1)

    def test_an_empty_submission_raises(self):
        with self.assertRaises(ValueError):
            record_results([])

    def test_a_non_list_submission_raises(self):
        with self.assertRaises(ValueError):
            record_results(record())

    def test_a_non_mapping_recorded_set_raises(self):
        with self.assertRaises(ValueError):
            record_results([record()], recorded=[record()])

    def test_an_iso_date_parses_and_a_date_passes_through(self):
        day = datetime.date(2026, 4, 3)
        self.assertEqual(parse_test_date("2026-04-03"), day)
        self.assertEqual(parse_test_date(day), day)

    def test_a_malformed_date_raises(self):
        with self.assertRaises(ValueError):
            parse_test_date("03/04/2026")


if __name__ == "__main__":
    unittest.main()
