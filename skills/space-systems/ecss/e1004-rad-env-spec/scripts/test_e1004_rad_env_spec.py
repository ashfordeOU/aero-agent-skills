import unittest

from e1004_rad_env_spec_logic import (
    REQUIRED_RES_SECTIONS,
    assess_component_entry,
    assess_orbit_segment,
    assess_res,
    required_components,
)


def _entry(model="AE9", basis="long_term_average", uncertainty="factor of 2"):
    return {"model": model, "basis": basis, "uncertainty": uncertainty}


class RequiredComponentsTests(unittest.TestCase):
    def test_leo_non_polar_baseline(self):
        self.assertEqual(
            required_components("leo"),
            {"trapped_radiation", "gcr", "neutron_albedo"},
        )

    def test_leo_polar_adds_sep(self):
        self.assertEqual(
            required_components("leo", polar=True),
            {"trapped_radiation", "gcr", "neutron_albedo", "sep"},
        )

    def test_geo_baseline(self):
        self.assertEqual(
            required_components("geo"),
            {"trapped_radiation", "gcr", "sep", "internal_charging"},
        )

    def test_geo_long_mission_adds_worst_case_proton(self):
        self.assertEqual(
            required_components("geo", mission_duration_years=7.0),
            {
                "trapped_radiation",
                "gcr",
                "sep",
                "internal_charging",
                "trapped_proton_worst_case",
            },
        )

    def test_geo_short_mission_no_worst_case_proton(self):
        components = required_components("geo", mission_duration_years=2.0)
        self.assertNotIn("trapped_proton_worst_case", components)

    def test_l2_no_trapped_or_charging(self):
        components = required_components("l2")
        self.assertEqual(components, {"gcr", "sep"})

    def test_unknown_regime_raises(self):
        with self.assertRaises(ValueError):
            required_components("cislunar")


class ComponentEntryTests(unittest.TestCase):
    def test_complete_entry_has_no_issues(self):
        self.assertEqual(assess_component_entry(_entry()), [])

    def test_missing_model(self):
        entry = _entry(model="")
        self.assertIn("missing model", assess_component_entry(entry))

    def test_missing_basis(self):
        entry = _entry(basis="unspecified")
        self.assertIn(
            "missing or invalid basis", assess_component_entry(entry)
        )

    def test_missing_uncertainty(self):
        entry = _entry(uncertainty="")
        self.assertIn(
            "missing uncertainty statement", assess_component_entry(entry)
        )

    def test_all_missing(self):
        issues = assess_component_entry({})
        self.assertEqual(len(issues), 3)


class OrbitSegmentTests(unittest.TestCase):
    def test_complete_leo_segment(self):
        segment = {
            "regime": "leo",
            "components": {
                "trapped_radiation": _entry(model="AP9"),
                "gcr": _entry(model="ISO-15390", basis="spectrum"),
                "neutron_albedo": _entry(model="QARM", basis="spectrum"),
            },
        }
        result = assess_orbit_segment(segment)
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing_components"], [])
        self.assertEqual(result["component_issues"], {})

    def test_missing_component_flagged(self):
        segment = {
            "regime": "leo",
            "components": {
                "trapped_radiation": _entry(),
                "gcr": _entry(basis="spectrum"),
            },
        }
        result = assess_orbit_segment(segment)
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing_components"], ["neutron_albedo"])

    def test_incomplete_entry_flagged(self):
        segment = {
            "regime": "leo",
            "components": {
                "trapped_radiation": _entry(uncertainty=""),
                "gcr": _entry(basis="spectrum"),
                "neutron_albedo": _entry(basis="spectrum"),
            },
        }
        result = assess_orbit_segment(segment)
        self.assertFalse(result["complete"])
        self.assertIn("trapped_radiation", result["component_issues"])
        self.assertIn(
            "missing uncertainty statement",
            result["component_issues"]["trapped_radiation"],
        )

    def test_geo_long_mission_requires_worst_case_proton(self):
        segment = {
            "regime": "geo",
            "mission_duration_years": 10,
            "components": {
                "trapped_radiation": _entry(),
                "gcr": _entry(basis="spectrum"),
                "sep": _entry(model="ESP", basis="fluence"),
                "internal_charging": _entry(model="FLUMIC", basis="worst_case"),
            },
        }
        result = assess_orbit_segment(segment)
        self.assertFalse(result["complete"])
        self.assertEqual(
            result["missing_components"], ["trapped_proton_worst_case"]
        )


class AssessResTests(unittest.TestCase):
    def _complete_leo_segment(self):
        return {
            "regime": "leo",
            "components": {
                "trapped_radiation": _entry(model="AP9"),
                "gcr": _entry(model="ISO-15390", basis="spectrum"),
                "neutron_albedo": _entry(model="QARM", basis="spectrum"),
            },
        }

    def test_complete_res(self):
        res = {
            "sections_present": list(REQUIRED_RES_SECTIONS),
            "orbit_segments": [self._complete_leo_segment()],
        }
        result = assess_res(res)
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing_sections"], [])

    def test_missing_section_blocks_completeness(self):
        sections = [
            s for s in REQUIRED_RES_SECTIONS if s != "uncertainty_discussion"
        ]
        res = {
            "sections_present": sections,
            "orbit_segments": [self._complete_leo_segment()],
        }
        result = assess_res(res)
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing_sections"], ["uncertainty_discussion"])

    def test_incomplete_segment_blocks_completeness_even_with_all_sections(self):
        res = {
            "sections_present": list(REQUIRED_RES_SECTIONS),
            "orbit_segments": [{"regime": "leo", "components": {}}],
        }
        result = assess_res(res)
        self.assertFalse(result["complete"])
        self.assertFalse(result["segment_results"][0]["complete"])

    def test_no_orbit_segments_raises(self):
        res = {"sections_present": list(REQUIRED_RES_SECTIONS), "orbit_segments": []}
        with self.assertRaises(ValueError):
            assess_res(res)


if __name__ == "__main__":
    unittest.main()
