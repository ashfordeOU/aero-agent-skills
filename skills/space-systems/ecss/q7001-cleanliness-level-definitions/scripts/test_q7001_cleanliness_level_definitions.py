"""Contract tests for the cleanliness level definition logic."""

import math
import unittest

from q7001_cleanliness_level_definitions_logic import (
    DEFAULT_DISTRIBUTION_SLOPE,
    DEFAULT_REFERENCE_AREA_CM2,
    MOLECULAR_UNITS_TO_NG_PER_CM2,
    band_obscuration_percent,
    channel_allowances,
    convert_molecular,
    define_levels,
    level_obscuration_percent,
    particle_count_allowance,
    projected_area_cm2,
    scale_allowance_to_area,
    select_molecular_level,
    validate_positive,
    validate_size_channels,
)

CHANNELS = [5.0, 15.0, 25.0, 50.0, 100.0]
LADDER = [
    ("A", 100.0, "ng/cm2"),
    ("B", 1.0, "ug/cm2"),
    ("C", 10.0, "ug/cm2"),
]


def nominal_spec(**overrides):
    spec = {
        "particulate_level_um": 100.0,
        "size_channels": list(CHANNELS),
        "inspected_area_cm2": 100.0,
        "molecular_ladder": [tuple(step) for step in LADDER],
        "required_molecular_ng_per_cm2": 2000.0,
    }
    spec.update(overrides)
    return spec


class ValidationTests(unittest.TestCase):
    def test_positive_value_returns_float(self):
        self.assertEqual(validate_positive(5, "size_um"), 5.0)

    def test_zero_size_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "size_um")

    def test_boolean_size_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(True, "size_um")

    def test_single_size_channel_rejected(self):
        with self.assertRaises(ValueError):
            validate_size_channels([25.0])

    def test_non_increasing_channels_rejected(self):
        with self.assertRaises(ValueError):
            validate_size_channels([25.0, 25.0, 50.0])

    def test_channels_returned_as_floats(self):
        self.assertEqual(validate_size_channels([5, 10]), [5.0, 10.0])


class LevelCurveTests(unittest.TestCase):
    def test_allowance_at_the_level_label_is_one_particle(self):
        self.assertAlmostEqual(particle_count_allowance(100.0, 100.0), 1.0, places=9)

    def test_allowance_rises_steeply_below_the_label(self):
        coarse = particle_count_allowance(100.0, 50.0)
        fine = particle_count_allowance(100.0, 5.0)
        self.assertGreater(fine, coarse)
        self.assertGreater(coarse, 1.0)

    def test_nothing_coarser_than_the_label_is_admitted(self):
        self.assertAlmostEqual(particle_count_allowance(100.0, 150.0), 0.0)

    def test_a_coarser_level_admits_more_at_the_same_size(self):
        self.assertGreater(
            particle_count_allowance(300.0, 25.0),
            particle_count_allowance(100.0, 25.0),
        )

    def test_allowance_scales_with_the_reference_area(self):
        base = particle_count_allowance(100.0, 25.0)
        doubled = particle_count_allowance(
            100.0, 25.0, reference_area_cm2=2.0 * DEFAULT_REFERENCE_AREA_CM2
        )
        self.assertAlmostEqual(doubled / base, 2.0, places=9)

    def test_declared_slope_changes_the_curve(self):
        shallow = particle_count_allowance(100.0, 25.0, slope=0.5)
        default = particle_count_allowance(100.0, 25.0)
        self.assertNotAlmostEqual(shallow, default, places=3)
        self.assertAlmostEqual(DEFAULT_DISTRIBUTION_SLOPE, 0.926, places=9)

    def test_zero_slope_rejected(self):
        with self.assertRaises(ValueError):
            particle_count_allowance(100.0, 25.0, slope=0.0)

    def test_allowance_scales_onto_the_inspected_area(self):
        self.assertAlmostEqual(
            scale_allowance_to_area(600.0, 1000.0, 100.0), 60.0, places=9
        )

    def test_negative_count_rejected_by_area_scaling(self):
        with self.assertRaises(ValueError):
            scale_allowance_to_area(-1.0, 1000.0, 100.0)

    def test_zero_inspected_area_rejected(self):
        with self.assertRaises(ValueError):
            scale_allowance_to_area(600.0, 1000.0, 0.0)


class ObscurationTests(unittest.TestCase):
    def test_projected_area_is_the_disc_of_the_particle(self):
        expected = math.pi * (0.5 * 100.0 * 1e-4) ** 2
        self.assertAlmostEqual(projected_area_cm2(100.0), expected, places=15)

    def test_band_obscuration_is_a_percentage_of_the_reference_area(self):
        value = band_obscuration_percent(1.0, 100.0, 1000.0)
        expected = 100.0 * projected_area_cm2(100.0) / 1000.0
        self.assertAlmostEqual(value, expected, places=15)

    def test_zero_count_obscures_nothing(self):
        self.assertAlmostEqual(band_obscuration_percent(0.0, 100.0, 1000.0), 0.0)

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            band_obscuration_percent(-2.0, 100.0, 1000.0)

    def test_level_obscuration_is_positive_and_small(self):
        value = level_obscuration_percent(100.0, CHANNELS)
        self.assertGreater(value, 0.0)
        self.assertLess(value, 1.0)

    def test_a_coarser_level_obscures_more(self):
        self.assertGreater(
            level_obscuration_percent(300.0, CHANNELS + [300.0]),
            level_obscuration_percent(100.0, CHANNELS),
        )

    def test_too_few_usable_channels_rejected(self):
        with self.assertRaises(ValueError):
            level_obscuration_percent(10.0, [50.0, 100.0])


class MolecularUnitTests(unittest.TestCase):
    def test_canonical_unit_is_unchanged(self):
        self.assertAlmostEqual(convert_molecular(250.0, "ng/cm2"), 250.0, places=12)

    def test_microgram_per_square_centimetre_is_a_thousand_nanograms(self):
        self.assertAlmostEqual(convert_molecular(1.0, "ug/cm2"), 1000.0, places=9)

    def test_milligram_per_square_metre_conversion(self):
        self.assertAlmostEqual(convert_molecular(1.0, "mg/m2"), 100.0, places=9)

    def test_conversion_round_trips(self):
        canonical = convert_molecular(2.5, "ug/cm2")
        self.assertAlmostEqual(
            convert_molecular(canonical, "ng/cm2", "ug/cm2"), 2.5, places=9
        )

    def test_every_declared_unit_is_positive(self):
        for unit, factor in MOLECULAR_UNITS_TO_NG_PER_CM2.items():
            self.assertGreater(factor, 0.0, unit)

    def test_unknown_unit_rejected(self):
        with self.assertRaises(ValueError):
            convert_molecular(1.0, "grains/inch2")

    def test_negative_mass_rejected(self):
        with self.assertRaises(ValueError):
            convert_molecular(-1.0, "ng/cm2")


class MolecularLevelSelectionTests(unittest.TestCase):
    def test_coarsest_step_inside_the_limit_is_selected(self):
        step = select_molecular_level(LADDER, 2000.0)
        self.assertEqual(step["label"], "B")
        self.assertAlmostEqual(step["allowance_ng_per_cm2"], 1000.0, places=9)

    def test_step_exactly_on_the_limit_is_admissible(self):
        step = select_molecular_level(LADDER, 1000.0)
        self.assertEqual(step["label"], "B")

    def test_no_step_meets_a_very_tight_limit(self):
        self.assertIsNone(select_molecular_level(LADDER, 50.0))

    def test_duplicate_ladder_label_rejected(self):
        with self.assertRaises(ValueError):
            select_molecular_level(LADDER + [("A", 5.0, "ug/cm2")], 2000.0)

    def test_malformed_ladder_entry_rejected(self):
        with self.assertRaises(ValueError):
            select_molecular_level([("A", 100.0)], 2000.0)

    def test_empty_ladder_rejected(self):
        with self.assertRaises(ValueError):
            select_molecular_level([], 2000.0)


class DefinitionRecordTests(unittest.TestCase):
    def test_nominal_definition_is_consistent(self):
        record = define_levels(nominal_spec())
        self.assertTrue(record["consistent"])
        self.assertEqual(record["findings"], [])

    def test_particulate_record_names_its_units(self):
        record = define_levels(nominal_spec())["particulate"]
        self.assertEqual(record["label_unit"], "um")
        self.assertIn("particles per", record["count_unit"])
        self.assertAlmostEqual(record["label"], 100.0, places=9)

    def test_inspected_area_allowances_are_added(self):
        record = define_levels(nominal_spec())["particulate"]
        for channel in record["channels"]:
            self.assertIn("allowance_on_inspected_area", channel)
        first = record["channels"][0]
        self.assertAlmostEqual(
            first["allowance_on_inspected_area"],
            first["count_allowance"] / 10.0,
            places=9,
        )

    def test_channel_coarser_than_the_label_is_a_finding(self):
        record = define_levels(nominal_spec(size_channels=CHANNELS + [300.0]))
        self.assertFalse(record["consistent"])
        self.assertTrue(any("coarser than the level label" in f for f in record["findings"]))

    def test_molecular_selection_is_carried_in_the_record(self):
        molecular = define_levels(nominal_spec())["molecular"]
        self.assertEqual(molecular["label"], "B")
        self.assertEqual(molecular["unit"], "ng/cm2")

    def test_unreachable_molecular_limit_is_a_finding(self):
        record = define_levels(nominal_spec(required_molecular_ng_per_cm2=50.0))
        self.assertIsNone(record["molecular"])
        self.assertTrue(any("no molecular ladder step" in f for f in record["findings"]))

    def test_ladder_without_a_required_limit_rejected(self):
        spec = nominal_spec()
        del spec["required_molecular_ng_per_cm2"]
        with self.assertRaises(ValueError):
            define_levels(spec)

    def test_missing_particulate_level_rejected(self):
        spec = nominal_spec()
        del spec["particulate_level_um"]
        with self.assertRaises(ValueError):
            define_levels(spec)

    def test_non_mapping_specification_rejected(self):
        with self.assertRaises(ValueError):
            define_levels(["particulate_level_um"])

    def test_channel_allowances_flag_sizes_above_the_label(self):
        records = channel_allowances(50.0, CHANNELS)
        flagged = [r["size_um"] for r in records if r["above_level_label"]]
        self.assertEqual(flagged, [100.0])


if __name__ == "__main__":
    unittest.main()
