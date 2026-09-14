"""Contract tests for the clause 4.6.6 connector-contact and sourcing logic."""

import unittest

from q6013_class_1_connectors_logic import (
    BUNDLE_DERATING_TABLE,
    CLASS_1_CURRENT_FACTOR,
    CURRENT_TOLERANCE_A,
    NICKEL_UNDERPLATE_MIN_UM,
    THICKNESS_TOLERANCE_UM,
    allowed_contact_current_a,
    assess_connector_contacts,
    bundle_derating_factor,
    contact_size_rating_a,
    contact_sourcing,
    contact_voltage_drop_mv,
    interpolate_table,
    minimum_gold_thickness_um,
    plating_acceptance,
)


def clean_spec(**overrides):
    """A qualified-source size-20 contact set that should accept outright."""
    spec = {
        "contact_source": "contact-manufacturer-qualified",
        "contact_size": "size-20",
        "mating_cycles": 200.0,
        "gold_um": 1.40,
        "nickel_um": 2.00,
        "active_fraction": 0.50,
        "applied_current_a": 2.0,
        "contact_resistance_mohm": 4.0,
        "allowed_drop_mv": 15.0,
        "contact_lot_identifier": "CTL-7781",
    }
    spec.update(overrides)
    return spec


class ContactSizeTests(unittest.TestCase):
    def test_size_twenty_rating(self):
        self.assertAlmostEqual(contact_size_rating_a("size-20"), 7.5, places=9)

    def test_lookup_is_case_and_space_insensitive(self):
        self.assertAlmostEqual(contact_size_rating_a("  SIZE-16 "), 13.0, places=9)

    def test_larger_contact_carries_more(self):
        self.assertGreater(contact_size_rating_a("size-8"),
                           contact_size_rating_a("size-12"))

    def test_unknown_size_rejected(self):
        with self.assertRaises(ValueError):
            contact_size_rating_a("size-30")

    def test_empty_size_rejected(self):
        with self.assertRaises(ValueError):
            contact_size_rating_a("  ")


class InterpolationTests(unittest.TestCase):
    def test_tabulated_point_is_returned(self):
        self.assertAlmostEqual(minimum_gold_thickness_um(200.0), 1.27, places=9)

    def test_midpoint_is_linear(self):
        value = interpolate_table(((0.0, 0.0), (10.0, 5.0)), 4.0, name="demo")
        self.assertAlmostEqual(value, 2.0, places=9)

    def test_lower_edge_of_the_durability_table(self):
        self.assertAlmostEqual(minimum_gold_thickness_um(50.0), 0.75, places=9)

    def test_upper_edge_of_the_durability_table(self):
        self.assertAlmostEqual(minimum_gold_thickness_um(1000.0), 2.54, places=9)

    def test_below_the_table_is_refused(self):
        with self.assertRaises(ValueError):
            minimum_gold_thickness_um(10.0)

    def test_above_the_table_is_refused(self):
        with self.assertRaises(ValueError):
            minimum_gold_thickness_um(5000.0)

    def test_more_cycles_need_more_gold(self):
        self.assertGreater(minimum_gold_thickness_um(800.0),
                           minimum_gold_thickness_um(300.0))

    def test_non_monotone_table_rejected(self):
        with self.assertRaises(ValueError):
            interpolate_table(((1.0, 1.0), (1.0, 2.0)), 1.0, name="demo")

    def test_single_point_table_rejected(self):
        with self.assertRaises(ValueError):
            interpolate_table(((1.0, 1.0),), 1.0, name="demo")

    def test_malformed_point_rejected(self):
        with self.assertRaises(ValueError):
            interpolate_table(((1.0, 1.0), (2.0,)), 1.5, name="demo")

    def test_non_positive_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            minimum_gold_thickness_um(0.0)


class PlatingTests(unittest.TestCase):
    def test_thick_finish_accepts(self):
        result = plating_acceptance(1.40, 2.00, 200.0)
        self.assertTrue(result["accepted"])

    def test_gold_exactly_on_the_requirement_accepts(self):
        result = plating_acceptance(1.27, 2.00, 200.0)
        self.assertAlmostEqual(result["required_gold_um"], 1.27, places=9)
        self.assertTrue(result["gold_sufficient"])

    def test_thin_gold_is_named(self):
        result = plating_acceptance(0.90, 2.00, 200.0)
        self.assertFalse(result["gold_sufficient"])
        self.assertTrue(result["nickel_sufficient"])

    def test_nickel_exactly_on_the_minimum_accepts(self):
        result = plating_acceptance(1.40, NICKEL_UNDERPLATE_MIN_UM, 200.0)
        self.assertTrue(result["nickel_sufficient"])

    def test_thin_nickel_is_named(self):
        result = plating_acceptance(1.40, 0.50, 200.0)
        self.assertFalse(result["nickel_sufficient"])
        self.assertFalse(result["accepted"])

    def test_negative_gold_rejected(self):
        with self.assertRaises(ValueError):
            plating_acceptance(-0.1, 2.0, 200.0)

    def test_thickness_tolerance_is_tight(self):
        self.assertLessEqual(THICKNESS_TOLERANCE_UM, 1e-6)


class BundleTests(unittest.TestCase):
    def test_no_active_neighbours_gives_unity(self):
        self.assertAlmostEqual(bundle_derating_factor(0.0), 1.0, places=9)

    def test_fully_loaded_connector_halves_the_rating(self):
        self.assertAlmostEqual(bundle_derating_factor(1.0), 0.50, places=9)

    def test_factor_falls_with_the_active_fraction(self):
        previous = None
        for fraction, _ in BUNDLE_DERATING_TABLE:
            value = bundle_derating_factor(fraction)
            if previous is not None:
                self.assertLess(value, previous)
            previous = value

    def test_interpolated_fraction(self):
        self.assertAlmostEqual(bundle_derating_factor(0.375), 0.725, places=9)

    def test_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            bundle_derating_factor(1.2)

    def test_negative_fraction_rejected(self):
        with self.assertRaises(ValueError):
            bundle_derating_factor(-0.1)


class AllowedCurrentTests(unittest.TestCase):
    def test_allowed_current_combines_both_factors(self):
        expected = 7.5 * CLASS_1_CURRENT_FACTOR * 0.65
        self.assertAlmostEqual(allowed_contact_current_a("size-20", 0.5), expected,
                               places=9)

    def test_empty_connector_still_takes_the_class_factor(self):
        self.assertAlmostEqual(allowed_contact_current_a("size-20", 0.0), 3.75,
                               places=9)

    def test_bigger_contact_allows_more_current(self):
        self.assertGreater(allowed_contact_current_a("size-12", 0.5),
                           allowed_contact_current_a("size-16", 0.5))

    def test_unknown_size_rejected(self):
        with self.assertRaises(ValueError):
            allowed_contact_current_a("size-99", 0.5)


class VoltageDropTests(unittest.TestCase):
    def test_drop_is_current_times_resistance(self):
        self.assertAlmostEqual(contact_voltage_drop_mv(2.0, 4.0), 8.0, places=9)

    def test_zero_current_gives_zero_drop(self):
        self.assertAlmostEqual(contact_voltage_drop_mv(0.0, 4.0), 0.0, places=9)

    def test_negative_resistance_rejected(self):
        with self.assertRaises(ValueError):
            contact_voltage_drop_mv(2.0, -4.0)


class SourcingTests(unittest.TestCase):
    def test_qualified_contact_manufacturer_stands_alone(self):
        self.assertEqual(contact_sourcing("contact-manufacturer-qualified")["standing"],
                         "accept")

    def test_distributor_is_a_deviation(self):
        self.assertEqual(
            contact_sourcing("distributor-with-lot-traceability")["standing"],
            "deviation",
        )

    def test_open_market_is_refused(self):
        self.assertEqual(contact_sourcing("open-market")["standing"], "reject")

    def test_unknown_source_rejected(self):
        with self.assertRaises(ValueError):
            contact_sourcing("a-drawer-in-the-lab")


class AssessmentTests(unittest.TestCase):
    def test_clean_case_accepts(self):
        result = assess_connector_contacts(clean_spec())
        self.assertEqual(result["disposition"], "accept")
        self.assertEqual(result["findings"], [])

    def test_open_market_source_rejects(self):
        result = assess_connector_contacts(clean_spec(contact_source="open-market"))
        self.assertEqual(result["disposition"], "reject")

    def test_distributor_source_is_a_deviation(self):
        result = assess_connector_contacts(
            clean_spec(contact_source="distributor-with-lot-traceability")
        )
        self.assertEqual(result["disposition"], "accept-with-deviation")
        self.assertEqual(len(result["findings"]), 1)

    def test_thin_gold_rejects(self):
        result = assess_connector_contacts(clean_spec(gold_um=0.80))
        self.assertEqual(result["disposition"], "reject")
        self.assertFalse(result["plating"]["gold_sufficient"])

    def test_thin_nickel_rejects(self):
        result = assess_connector_contacts(clean_spec(nickel_um=0.60))
        self.assertEqual(result["disposition"], "reject")

    def test_overloaded_contact_rejects(self):
        result = assess_connector_contacts(clean_spec(applied_current_a=6.0))
        self.assertEqual(result["disposition"], "reject")

    def test_current_exactly_at_the_allowance_accepts(self):
        allowed = allowed_contact_current_a("size-20", 0.50)
        result = assess_connector_contacts(
            clean_spec(applied_current_a=allowed, contact_resistance_mohm=1.0,
                       allowed_drop_mv=15.0)
        )
        self.assertAlmostEqual(result["allowed_current_a"], allowed, places=9)
        self.assertEqual(result["disposition"], "accept")

    def test_excess_contact_drop_rejects(self):
        result = assess_connector_contacts(clean_spec(contact_resistance_mohm=20.0))
        self.assertEqual(result["disposition"], "reject")

    def test_missing_contact_lot_rejects(self):
        spec = clean_spec()
        del spec["contact_lot_identifier"]
        result = assess_connector_contacts(spec)
        self.assertEqual(result["disposition"], "reject")
        self.assertTrue(any("traceability" in f for f in result["findings"]))

    def test_more_active_contacts_shrink_the_allowance(self):
        light = assess_connector_contacts(clean_spec(active_fraction=0.25))
        heavy = assess_connector_contacts(clean_spec(active_fraction=1.0))
        self.assertLess(heavy["allowed_current_a"], light["allowed_current_a"])

    def test_reported_drop_matches_the_inputs(self):
        result = assess_connector_contacts(clean_spec())
        self.assertAlmostEqual(result["contact_drop_mv"], 8.0, places=9)

    def test_missing_key_rejected(self):
        spec = clean_spec()
        del spec["contact_size"]
        with self.assertRaises(ValueError):
            assess_connector_contacts(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_connector_contacts(["contact_source"])

    def test_current_tolerance_is_tight(self):
        self.assertLessEqual(CURRENT_TOLERANCE_A, 1e-6)


if __name__ == "__main__":
    unittest.main()
