"""Contract tests for the mechanical data delivery into the 70-71C data set."""

import unittest

from q7045_data_to_70_71c_logic import (
    MIN_ENTRIES_PER_GROUP,
    STRESS_FACTORS_TO_MPA,
    TEMPERATURE_BUCKET_K,
    build_dataset,
    convert_strain,
    convert_stress_to_mpa,
    convert_temperature_to_kelvin,
    dataset_key,
    normalise_entry,
    stress_units,
    temperature_bucket,
)


def _entry(**overrides):
    entry = {
        "material_designation": "Ti-6Al-4V",
        "product_form": "bar",
        "heat": "h1",
        "condition": "annealed",
        "orientation": "L",
        "property": "tensile_strength",
        "value": 900.0,
        "unit": "MPa",
        "temperature": 20.0,
        "temperature_unit": "C",
    }
    entry.update(overrides)
    return entry


class StressConversionTests(unittest.TestCase):
    def test_mpa_is_the_identity(self):
        self.assertAlmostEqual(convert_stress_to_mpa(900.0, "MPa"), 900.0, places=9)

    def test_newton_per_square_millimetre_equals_mpa(self):
        self.assertAlmostEqual(convert_stress_to_mpa(900.0, "N/mm2"), 900.0, places=9)

    def test_gigapascal_scales_by_a_thousand(self):
        self.assertAlmostEqual(convert_stress_to_mpa(0.9, "GPa"), 900.0, places=9)

    def test_ksi_uses_the_tabulated_factor(self):
        self.assertAlmostEqual(
            convert_stress_to_mpa(100.0, "ksi"), 100.0 * STRESS_FACTORS_TO_MPA["ksi"],
            places=9,
        )

    def test_psi_is_a_thousandth_of_ksi(self):
        self.assertAlmostEqual(
            convert_stress_to_mpa(1000.0, "psi"), convert_stress_to_mpa(1.0, "ksi"),
            places=9,
        )

    def test_unknown_stress_unit_rejected(self):
        with self.assertRaises(ValueError):
            convert_stress_to_mpa(900.0, "kgf/mm2")

    def test_non_positive_stress_rejected(self):
        with self.assertRaises(ValueError):
            convert_stress_to_mpa(0.0, "MPa")

    def test_stress_units_are_sorted(self):
        self.assertEqual(stress_units(), sorted(stress_units()))


class StrainConversionTests(unittest.TestCase):
    def test_percent_becomes_a_ratio(self):
        self.assertAlmostEqual(convert_strain(12.0, "%"), 0.12, places=12)

    def test_dimensionless_is_the_identity(self):
        self.assertAlmostEqual(convert_strain(0.12, "-"), 0.12, places=12)

    def test_zero_strain_is_accepted(self):
        self.assertAlmostEqual(convert_strain(0.0, "%"), 0.0, places=12)

    def test_negative_strain_rejected(self):
        with self.assertRaises(ValueError):
            convert_strain(-1.0, "%")

    def test_unknown_strain_unit_rejected(self):
        with self.assertRaises(ValueError):
            convert_strain(12.0, "microstrain")


class TemperatureTests(unittest.TestCase):
    def test_kelvin_is_the_identity(self):
        self.assertAlmostEqual(convert_temperature_to_kelvin(293.15, "K"), 293.15, places=9)

    def test_celsius_offsets_by_absolute_zero(self):
        self.assertAlmostEqual(convert_temperature_to_kelvin(20.0, "C"), 293.15, places=9)

    def test_fahrenheit_freezing_point(self):
        self.assertAlmostEqual(convert_temperature_to_kelvin(32.0, "F"), 273.15, places=9)

    def test_fahrenheit_and_celsius_agree_at_minus_forty(self):
        self.assertAlmostEqual(
            convert_temperature_to_kelvin(-40.0, "F"),
            convert_temperature_to_kelvin(-40.0, "C"),
            places=9,
        )

    def test_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            convert_temperature_to_kelvin(-300.0, "C")

    def test_unknown_temperature_unit_rejected(self):
        with self.assertRaises(ValueError):
            convert_temperature_to_kelvin(20.0, "rankine")

    def test_nearby_temperatures_share_a_bucket(self):
        self.assertEqual(
            temperature_bucket(293.15), temperature_bucket(293.15 + TEMPERATURE_BUCKET_K / 4.0)
        )

    def test_distant_temperatures_split_buckets(self):
        self.assertNotEqual(
            temperature_bucket(293.15), temperature_bucket(293.15 + 4.0 * TEMPERATURE_BUCKET_K)
        )

    def test_non_positive_bucket_input_rejected(self):
        with self.assertRaises(ValueError):
            temperature_bucket(0.0)


class NormalisationTests(unittest.TestCase):
    def test_entry_lands_in_data_set_units(self):
        normalised = normalise_entry(_entry(value=130.0, unit="ksi"))
        self.assertEqual(normalised["unit"], "mpa")
        self.assertAlmostEqual(
            normalised["value"], 130.0 * STRESS_FACTORS_TO_MPA["ksi"], places=9
        )

    def test_strain_property_normalises_as_a_ratio(self):
        normalised = normalise_entry(_entry(property="elongation", value=12.0, unit="%"))
        self.assertEqual(normalised["kind"], "strain")
        self.assertAlmostEqual(normalised["value"], 0.12, places=12)

    def test_tokens_are_case_folded(self):
        self.assertEqual(normalise_entry(_entry())["orientation"], "l")

    def test_missing_mandatory_field_rejected(self):
        entry = _entry()
        del entry["heat"]
        with self.assertRaises(ValueError):
            normalise_entry(entry)

    def test_unknown_property_rejected(self):
        with self.assertRaises(ValueError):
            normalise_entry(_entry(property="creep_rate"))

    def test_unknown_orientation_rejected(self):
        with self.assertRaises(ValueError):
            normalise_entry(_entry(orientation="radial"))

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            normalise_entry(["material_designation"])

    def test_key_drops_the_heat_but_keeps_the_condition(self):
        key = dataset_key(normalise_entry(_entry()))
        self.assertNotIn("h1", key)
        self.assertIn("annealed", key)


class DatasetTests(unittest.TestCase):
    def _batch(self):
        return [
            _entry(heat="h1", value=900.0, unit="MPa"),
            _entry(heat="h2", value=130.0, unit="ksi"),
            _entry(heat="h3", value=0.91, unit="GPa"),
        ]

    def test_equivalent_entries_land_in_one_group(self):
        result = build_dataset(self._batch())
        self.assertEqual(result["group_count"], 1)
        self.assertEqual(result["groups"][0]["entries"], 3)

    def test_group_lists_its_distinct_heats(self):
        result = build_dataset(self._batch())
        self.assertEqual(result["groups"][0]["heats"], ["h1", "h2", "h3"])

    def test_a_different_condition_splits_the_group(self):
        batch = self._batch() + [_entry(heat="h4", condition="solution-treated")]
        self.assertEqual(build_dataset(batch)["group_count"], 2)

    def test_a_different_orientation_splits_the_group(self):
        batch = self._batch() + [_entry(heat="h4", orientation="ST")]
        self.assertEqual(build_dataset(batch)["group_count"], 2)

    def test_a_far_temperature_splits_the_group(self):
        batch = self._batch() + [_entry(heat="h4", temperature=200.0)]
        self.assertEqual(build_dataset(batch)["group_count"], 2)

    def test_a_nearby_temperature_does_not_split_the_group(self):
        batch = self._batch() + [_entry(heat="h4", temperature=20.5)]
        self.assertEqual(build_dataset(batch)["group_count"], 1)

    def test_undersized_group_is_present_but_not_usable(self):
        result = build_dataset([_entry()])
        self.assertEqual(result["group_count"], 1)
        self.assertFalse(result["groups"][0]["usable"])
        self.assertFalse(result["deliverable"])

    def test_full_group_is_deliverable(self):
        result = build_dataset(self._batch())
        self.assertTrue(result["deliverable"])
        self.assertEqual(result["findings"], [])

    def test_bad_entry_is_rejected_with_a_reason_not_raised(self):
        batch = self._batch() + [_entry(heat="h4", unit="kgf/mm2")]
        result = build_dataset(batch)
        self.assertEqual(len(result["rejected"]), 1)
        self.assertIn("kgf/mm2", result["rejected"][0]["reason"])

    def test_rejection_does_not_remove_the_good_entries(self):
        batch = self._batch() + [_entry(heat="h4", unit="kgf/mm2")]
        result = build_dataset(batch)
        self.assertEqual(len(result["accepted"]), 3)
        self.assertFalse(result["deliverable"])

    def test_group_mean_is_taken_after_conversion(self):
        result = build_dataset([_entry(value=0.9, unit="GPa"), _entry(heat="h2", value=900.0)])
        self.assertAlmostEqual(result["groups"][0]["mean_value"], 900.0, places=9)

    def test_empty_batch_is_not_deliverable(self):
        result = build_dataset([])
        self.assertEqual(result["group_count"], 0)
        self.assertFalse(result["deliverable"])

    def test_min_entries_default_matches_the_constant(self):
        batch = [_entry(heat="h%d" % i) for i in range(MIN_ENTRIES_PER_GROUP)]
        self.assertTrue(build_dataset(batch)["groups"][0]["usable"])

    def test_zero_min_entries_rejected(self):
        with self.assertRaises(ValueError):
            build_dataset(self._batch(), min_entries=0)

    def test_non_sequence_batch_rejected(self):
        with self.assertRaises(ValueError):
            build_dataset("entries")


if __name__ == "__main__":
    unittest.main()
