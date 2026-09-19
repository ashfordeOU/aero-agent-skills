"""Contract test for the crewed-compartment interface leaf (stdlib unittest)."""

import unittest

from q7021_manned_areas_interface_logic import (
    ACCEPTED,
    ACCEPTED_WITH_CONTAINMENT,
    COMPARTMENT_EXCEPTION_BUDGET_CM2,
    CONTAINMENT_HOUSING,
    CONTAINMENT_SEALED,
    EXEMPT_AREA_CM2,
    EXEMPT_MASS_G,
    NEEDS_ASSESSMENT,
    NOT_PROPAGATING,
    NOT_PROPAGATING_RESTRICTED,
    PROPAGATING,
    REJECTED,
    THICKNESS_TOLERANCE_MM,
    assess_compartment,
    assess_usage,
    atmosphere_covered,
    configuration_covered,
    isolates_from_the_cabin,
    oxygen_partial_pressure,
    small_quantity_exempt,
    validate_entry,
    validate_usage,
    worst_disposition,
)


def entry(**kw):
    e = {
        "material_designation": "PFX-220 polyimide film",
        "rating": NOT_PROPAGATING,
        "tested_oxygen_partial_pressure_kpa": 30.0,
        "tested_thickness_mm": 0.5,
    }
    e.update(kw)
    return e


def usage(**kw):
    u = {
        "location_id": "node-2 standoff panel",
        "compartment_oxygen_volume_pct": 21.0,
        "compartment_total_pressure_kpa": 101.3,
        "installed_thickness_mm": 0.5,
        "exposed_area_cm2": 40.0,
        "mass_g": 22.0,
        "ignitable_item_below": False,
        "containment": "none",
    }
    u.update(kw)
    return u


class TestAtmosphere(unittest.TestCase):
    def test_partial_pressure_is_the_fraction_of_the_total(self):
        self.assertAlmostEqual(oxygen_partial_pressure(21.0, 101.3), 21.273, places=9)

    def test_a_negative_oxygen_fraction_raises(self):
        with self.assertRaises(ValueError):
            oxygen_partial_pressure(-1.0, 101.3)

    def test_a_zero_total_pressure_raises(self):
        with self.assertRaises(ValueError):
            oxygen_partial_pressure(21.0, 0.0)

    def test_a_more_severe_test_covers_the_cabin(self):
        result = atmosphere_covered(validate_entry(entry()), validate_usage(usage()))
        self.assertTrue(result["covered"])

    def test_a_milder_test_does_not_cover_the_cabin(self):
        thin = validate_entry(entry(tested_oxygen_partial_pressure_kpa=14.7))
        result = atmosphere_covered(thin, validate_usage(usage()))
        self.assertFalse(result["covered"])

    def test_an_exactly_equal_atmosphere_is_covered(self):
        cabin = oxygen_partial_pressure(21.0, 101.3)
        exact = validate_entry(entry(tested_oxygen_partial_pressure_kpa=cabin))
        result = atmosphere_covered(exact, validate_usage(usage()))
        self.assertTrue(result["covered"])
        self.assertAlmostEqual(
            result["tested_kpa"], result["compartment_kpa"], places=9
        )


class TestValidation(unittest.TestCase):
    def test_an_unknown_rating_raises(self):
        with self.assertRaises(ValueError):
            validate_entry(entry(rating="probably-fine"))

    def test_a_non_mapping_entry_raises(self):
        with self.assertRaises(ValueError):
            validate_entry("PFX-220")

    def test_an_unknown_containment_raises(self):
        with self.assertRaises(ValueError):
            validate_usage(usage(containment="some-tape"))

    def test_a_zero_installed_thickness_raises(self):
        with self.assertRaises(ValueError):
            validate_usage(usage(installed_thickness_mm=0.0))

    def test_a_negative_exposed_area_raises(self):
        with self.assertRaises(ValueError):
            validate_usage(usage(exposed_area_cm2=-3.0))

    def test_a_non_boolean_geometry_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_usage(usage(ignitable_item_below="no"))

    def test_a_blank_location_raises(self):
        with self.assertRaises(ValueError):
            validate_usage(usage(location_id="   "))


class TestConfiguration(unittest.TestCase):
    def test_the_tested_thickness_covers_itself(self):
        self.assertTrue(
            configuration_covered(validate_entry(entry()), validate_usage(usage()))
        )

    def test_a_thickness_exactly_at_the_tolerance_is_still_covered(self):
        thicker = usage(installed_thickness_mm=0.5 + THICKNESS_TOLERANCE_MM)
        self.assertTrue(
            configuration_covered(validate_entry(entry()), validate_usage(thicker))
        )

    def test_a_thickness_well_outside_the_band_is_not_covered(self):
        thicker = usage(installed_thickness_mm=2.0)
        self.assertFalse(
            configuration_covered(validate_entry(entry()), validate_usage(thicker))
        )


class TestQuantity(unittest.TestCase):
    def test_a_tiny_item_is_exempt(self):
        self.assertTrue(
            small_quantity_exempt(validate_usage(usage(exposed_area_cm2=2.0, mass_g=1.0)))
        )

    def test_an_item_exactly_on_both_limits_is_exempt(self):
        limit = usage(exposed_area_cm2=EXEMPT_AREA_CM2, mass_g=EXEMPT_MASS_G)
        self.assertTrue(small_quantity_exempt(validate_usage(limit)))

    def test_a_heavy_small_item_is_not_exempt(self):
        heavy = usage(exposed_area_cm2=2.0, mass_g=EXEMPT_MASS_G + 4.0)
        self.assertFalse(small_quantity_exempt(validate_usage(heavy)))

    def test_a_sealed_enclosure_isolates_and_a_vented_housing_does_not(self):
        self.assertTrue(
            isolates_from_the_cabin(validate_usage(usage(containment=CONTAINMENT_SEALED)))
        )
        self.assertFalse(
            isolates_from_the_cabin(validate_usage(usage(containment=CONTAINMENT_HOUSING)))
        )


class TestDisposition(unittest.TestCase):
    def test_a_clean_material_in_a_covered_cabin_is_accepted(self):
        self.assertEqual(assess_usage(entry(), usage())["disposition"], ACCEPTED)

    def test_a_milder_test_sends_the_usage_to_assessment(self):
        result = assess_usage(
            entry(tested_oxygen_partial_pressure_kpa=14.7), usage()
        )
        self.assertEqual(result["disposition"], NEEDS_ASSESSMENT)
        self.assertIn("test-atmosphere-milder-than-the-compartment", result["reasons"])

    def test_an_untested_thickness_sends_the_usage_to_assessment(self):
        result = assess_usage(entry(), usage(installed_thickness_mm=2.0))
        self.assertEqual(result["disposition"], NEEDS_ASSESSMENT)
        self.assertIn("installed-thickness-outside-the-tested-band", result["reasons"])

    def test_a_propagating_material_openly_installed_is_rejected(self):
        result = assess_usage(entry(rating=PROPAGATING), usage())
        self.assertEqual(result["disposition"], REJECTED)
        self.assertIn("propagating-material-openly-installed", result["reasons"])

    def test_a_propagating_material_sealed_away_is_accepted_with_containment(self):
        result = assess_usage(
            entry(rating=PROPAGATING), usage(containment=CONTAINMENT_SEALED)
        )
        self.assertEqual(result["disposition"], ACCEPTED_WITH_CONTAINMENT)

    def test_a_tiny_propagating_item_still_needs_assessment(self):
        result = assess_usage(
            entry(rating=PROPAGATING), usage(exposed_area_cm2=2.0, mass_g=1.0)
        )
        self.assertEqual(result["disposition"], NEEDS_ASSESSMENT)
        self.assertIn(
            "propagating-material-below-the-quantity-limit", result["reasons"]
        )

    def test_a_dripping_material_above_nothing_is_accepted(self):
        result = assess_usage(entry(rating=NOT_PROPAGATING_RESTRICTED), usage())
        self.assertEqual(result["disposition"], ACCEPTED)

    def test_a_dripping_material_above_an_ignitable_item_is_rejected(self):
        result = assess_usage(
            entry(rating=NOT_PROPAGATING_RESTRICTED),
            usage(ignitable_item_below=True),
        )
        self.assertEqual(result["disposition"], REJECTED)
        self.assertIn("dripping-material-above-an-ignitable-item", result["reasons"])

    def test_containment_rescues_a_dripping_material(self):
        result = assess_usage(
            entry(rating=NOT_PROPAGATING_RESTRICTED),
            usage(ignitable_item_below=True, containment=CONTAINMENT_HOUSING),
        )
        self.assertEqual(result["disposition"], ACCEPTED_WITH_CONTAINMENT)


class TestCompartment(unittest.TestCase):
    def test_the_worst_item_governs_the_compartment(self):
        report = assess_compartment(
            [
                {"entry": entry(), "usage": usage()},
                {"entry": entry(rating=PROPAGATING), "usage": usage(location_id="rack 3")},
            ]
        )
        self.assertEqual(report["governing_disposition"], REJECTED)
        self.assertIn("rejected-installation-at-rack 3", report["findings"])

    def test_a_clean_compartment_reports_clean(self):
        report = assess_compartment([{"entry": entry(), "usage": usage()}])
        self.assertTrue(report["clean"])
        self.assertEqual(report["governing_disposition"], ACCEPTED)

    def test_accepted_items_do_not_consume_the_exception_budget(self):
        report = assess_compartment([{"entry": entry(), "usage": usage()}])
        self.assertAlmostEqual(report["exception_area_cm2"], 0.0, places=9)

    def test_accumulated_exceptions_breach_the_compartment_budget(self):
        item = {
            "entry": entry(rating=PROPAGATING),
            "usage": usage(containment=CONTAINMENT_SEALED, exposed_area_cm2=60.0),
        }
        report = assess_compartment([item, dict(item)])
        self.assertIn("exception-area-over-the-compartment-budget", report["findings"])
        self.assertGreater(
            report["exception_area_cm2"], COMPARTMENT_EXCEPTION_BUDGET_CM2
        )

    def test_an_exception_area_exactly_on_the_budget_is_not_a_finding(self):
        item = {
            "entry": entry(rating=PROPAGATING),
            "usage": usage(
                containment=CONTAINMENT_SEALED,
                exposed_area_cm2=COMPARTMENT_EXCEPTION_BUDGET_CM2,
            ),
        }
        report = assess_compartment([item])
        self.assertAlmostEqual(
            report["exception_area_cm2"],
            COMPARTMENT_EXCEPTION_BUDGET_CM2,
            places=9,
        )
        self.assertNotIn(
            "exception-area-over-the-compartment-budget", report["findings"]
        )

    def test_an_empty_compartment_raises(self):
        with self.assertRaises(ValueError):
            assess_compartment([])

    def test_a_non_list_compartment_raises(self):
        with self.assertRaises(ValueError):
            assess_compartment({"entry": entry(), "usage": usage()})

    def test_an_unknown_disposition_raises(self):
        with self.assertRaises(ValueError):
            worst_disposition([ACCEPTED, "probably-fine"])

    def test_an_empty_disposition_set_raises(self):
        with self.assertRaises(ValueError):
            worst_disposition([])

    def test_assessment_outranks_containment_in_the_roll_up(self):
        self.assertEqual(
            worst_disposition([ACCEPTED_WITH_CONTAINMENT, NEEDS_ASSESSMENT]),
            NEEDS_ASSESSMENT,
        )


if __name__ == "__main__":
    unittest.main()
