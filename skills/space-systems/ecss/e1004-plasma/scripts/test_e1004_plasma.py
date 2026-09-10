import unittest

from e1004_plasma_logic import (
    applicable_regions,
    assess_orbit_segment,
    assess_plasma_environment,
    assess_region_entry,
)


def _entry(
    model="AE-8-plasma",
    electron_density=1.0,
    electron_temperature=1.0,
    ion_density=1.0,
    ion_temperature=1.0,
    basis="worst_case",
):
    return {
        "model": model,
        "electron_density": electron_density,
        "electron_temperature": electron_temperature,
        "ion_density": ion_density,
        "ion_temperature": ion_temperature,
        "basis": basis,
    }


class ApplicableRegionsTests(unittest.TestCase):
    def test_leo_non_polar_baseline(self):
        self.assertEqual(applicable_regions("leo"), {"ionosphere"})

    def test_leo_polar_adds_auroral(self):
        self.assertEqual(
            applicable_regions("leo", polar=True),
            {"ionosphere", "auroral"},
        )

    def test_geo_baseline(self):
        self.assertEqual(
            applicable_regions("geo"),
            {"plasmasphere", "outer_magnetosphere"},
        )

    def test_gto_adds_magnetosheath(self):
        self.assertEqual(
            applicable_regions("gto"),
            {"plasmasphere", "outer_magnetosphere", "magnetosheath"},
        )

    def test_l2_regions(self):
        self.assertEqual(
            applicable_regions("l2"), {"magnetotail_l2", "solar_wind"}
        )

    def test_interplanetary_solar_wind_only(self):
        self.assertEqual(applicable_regions("interplanetary"), {"solar_wind"})

    def test_planetary_regime(self):
        self.assertEqual(applicable_regions("planetary"), {"planetary"})

    def test_plasma_sources_adds_induced_to_any_regime(self):
        self.assertEqual(
            applicable_regions("leo", has_plasma_sources=True),
            {"ionosphere", "induced"},
        )

    def test_unknown_regime_raises(self):
        with self.assertRaises(ValueError):
            applicable_regions("cislunar")


class RegionEntryTests(unittest.TestCase):
    def test_complete_entry_has_no_issues(self):
        self.assertEqual(assess_region_entry(_entry()), [])

    def test_missing_model(self):
        entry = _entry(model="")
        self.assertIn("missing model", assess_region_entry(entry))

    def test_missing_electron_density(self):
        entry = _entry(electron_density=None)
        self.assertIn(
            "missing or invalid electron_density", assess_region_entry(entry)
        )

    def test_zero_ion_temperature_invalid(self):
        entry = _entry(ion_temperature=0)
        self.assertIn(
            "missing or invalid ion_temperature", assess_region_entry(entry)
        )

    def test_all_missing(self):
        issues = assess_region_entry({})
        self.assertEqual(len(issues), 5)

    def test_outer_magnetosphere_average_basis_flagged(self):
        entry = _entry(basis="long_term_average")
        issues = assess_region_entry(entry, region="outer_magnetosphere")
        self.assertTrue(
            any("worst-case" in issue for issue in issues)
        )

    def test_outer_magnetosphere_worst_case_basis_clean(self):
        entry = _entry(basis="worst_case")
        self.assertEqual(
            assess_region_entry(entry, region="outer_magnetosphere"), []
        )

    def test_non_worst_case_region_average_basis_not_flagged(self):
        entry = _entry(basis="long_term_average")
        self.assertEqual(assess_region_entry(entry, region="ionosphere"), [])


class OrbitSegmentTests(unittest.TestCase):
    def test_complete_leo_segment(self):
        segment = {
            "regime": "leo",
            "regions": {"ionosphere": _entry()},
        }
        result = assess_orbit_segment(segment)
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing_regions"], [])
        self.assertEqual(result["region_issues"], {})

    def test_missing_region_flagged(self):
        segment = {
            "regime": "geo",
            "regions": {"plasmasphere": _entry()},
        }
        result = assess_orbit_segment(segment)
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing_regions"], ["outer_magnetosphere"])

    def test_incomplete_entry_flagged(self):
        segment = {
            "regime": "leo",
            "regions": {"ionosphere": _entry(ion_density=0)},
        }
        result = assess_orbit_segment(segment)
        self.assertFalse(result["complete"])
        self.assertIn("ionosphere", result["region_issues"])
        self.assertIn(
            "missing or invalid ion_density",
            result["region_issues"]["ionosphere"],
        )

    def test_polar_leo_requires_auroral(self):
        segment = {
            "regime": "leo",
            "polar": True,
            "regions": {"ionosphere": _entry()},
        }
        result = assess_orbit_segment(segment)
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing_regions"], ["auroral"])

    def test_plasma_source_requires_induced(self):
        segment = {
            "regime": "interplanetary",
            "has_plasma_sources": True,
            "regions": {"solar_wind": _entry()},
        }
        result = assess_orbit_segment(segment)
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing_regions"], ["induced"])

    def test_geo_average_basis_for_outer_magnetosphere_incomplete(self):
        segment = {
            "regime": "geo",
            "regions": {
                "plasmasphere": _entry(),
                "outer_magnetosphere": _entry(basis="long_term_average"),
            },
        }
        result = assess_orbit_segment(segment)
        self.assertFalse(result["complete"])
        self.assertIn("outer_magnetosphere", result["region_issues"])


class AssessPlasmaEnvironmentTests(unittest.TestCase):
    def _complete_leo_segment(self):
        return {"regime": "leo", "regions": {"ionosphere": _entry()}}

    def _complete_geo_segment(self):
        return {
            "regime": "geo",
            "regions": {
                "plasmasphere": _entry(),
                "outer_magnetosphere": _entry(basis="worst_case"),
            },
        }

    def test_all_complete_segments(self):
        result = assess_plasma_environment(
            [self._complete_leo_segment(), self._complete_geo_segment()]
        )
        self.assertTrue(result["complete"])
        self.assertEqual(len(result["segment_results"]), 2)

    def test_one_incomplete_segment_blocks_completeness(self):
        incomplete = {"regime": "geo", "regions": {}}
        result = assess_plasma_environment(
            [self._complete_leo_segment(), incomplete]
        )
        self.assertFalse(result["complete"])

    def test_no_segments_raises(self):
        with self.assertRaises(ValueError):
            assess_plasma_environment([])


if __name__ == "__main__":
    unittest.main()
