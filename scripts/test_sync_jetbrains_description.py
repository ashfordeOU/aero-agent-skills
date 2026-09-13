#!/usr/bin/env python3
"""Offline tests for the JetBrains storefront description sync."""
import importlib.util
import json
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "syncdesc", os.path.join(HERE, "sync_jetbrains_description.py"))
sd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sd)

GRADLE_SNIPPET = """        description = \"\"\"
            <p><b>Aero Agent Skills</b> - the aerospace knowledge layer.</p>
            <ul>
                <li><b>330+ verified skills</b> across aerodynamics, avionics, flight mechanics,
                    GNC/autonomy, propulsion, structures, space systems, and vehicle design</li>
                <li><b>Skill catalog browser</b> - search any skill in the IDE</li>
            </ul>
        \"\"\".trimIndent()
"""


def catalog(count, families):
    skills = []
    for i in range(count):
        skills.append({"name": "n%d" % i, "family": families[i % len(families)]})
    return {"count": count, "skills": skills}


def write_catalog(obj):
    fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(obj, fh)
    fh.close()
    return fh.name


class Describe(unittest.TestCase):
    def test_counts_and_families(self):
        p = write_catalog(catalog(12, ["aerodynamics", "avionics", "space-systems"]))
        count, prose = sd.describe(p)
        self.assertEqual(count, 12)
        self.assertIn("space systems", prose)

    def test_families_are_alphabetical(self):
        p = write_catalog(catalog(6, ["space-systems", "aerodynamics", "propulsion"]))
        _, prose = sd.describe(p)
        self.assertTrue(prose.startswith("aerodynamics"))

    def test_uppercase_label_sorts_case_insensitively(self):
        """Plain sorted() puts GNC/autonomy ahead of aerodynamics on ASCII."""
        p = write_catalog(catalog(6, ["gnc-autonomy", "aerodynamics", "avionics"]))
        _, prose = sd.describe(p)
        self.assertTrue(prose.startswith("aerodynamics"), prose)
        self.assertIn("GNC/autonomy", prose)

    def test_gnc_label_is_mapped(self):
        p = write_catalog(catalog(3, ["gnc-autonomy"]))
        _, prose = sd.describe(p)
        self.assertEqual(prose, "GNC/autonomy")

    def test_cross_cutting_keeps_its_hyphen(self):
        p = write_catalog(catalog(2, ["cross-cutting"]))
        _, prose = sd.describe(p)
        self.assertEqual(prose, "cross-cutting")

    def test_safety_label_is_mapped(self):
        p = write_catalog(catalog(2, ["systems-engineering-safety"]))
        _, prose = sd.describe(p)
        self.assertEqual(prose, "systems engineering and safety")

    def test_two_families_use_and(self):
        p = write_catalog(catalog(2, ["avionics", "propulsion"]))
        _, prose = sd.describe(p)
        self.assertEqual(prose, "avionics, and propulsion")

    def test_zero_count_refused(self):
        p = write_catalog({"count": 0, "skills": []})
        with self.assertRaises(ValueError):
            sd.describe(p)

    def test_missing_count_refused(self):
        p = write_catalog({"skills": [{"family": "avionics"}]})
        with self.assertRaises(ValueError):
            sd.describe(p)

    def test_count_disagreeing_with_entries_refused(self):
        """The exact failure this guards: a stale count beside a fresh skill list."""
        p = write_catalog({"count": 330, "skills": [{"name": "a", "family": "avionics"}]})
        with self.assertRaises(ValueError):
            sd.describe(p)

    def test_no_families_refused(self):
        p = write_catalog({"count": 1, "skills": [{"name": "a"}]})
        with self.assertRaises(ValueError):
            sd.describe(p)

    def test_render_has_thousands_separator(self):
        self.assertIn("1,439 verified skills", sd.render(1439, "avionics"))

    def test_render_is_one_line(self):
        self.assertNotIn("\n", sd.render(1439, "avionics, and propulsion"))


class Rewrite(unittest.TestCase):
    def test_bullet_is_replaced_across_wrapped_lines(self):
        out = sd.BULLET_RE.sub(sd.render(1439, "avionics, and propulsion"),
                               GRADLE_SNIPPET, count=1)
        self.assertIn("1,439 verified skills", out)
        self.assertNotIn("330+", out)

    def test_sibling_bullet_survives(self):
        out = sd.BULLET_RE.sub(sd.render(1439, "avionics"), GRADLE_SNIPPET, count=1)
        self.assertIn("<b>Skill catalog browser</b>", out)

    def test_rewrite_is_idempotent(self):
        once = sd.BULLET_RE.sub(sd.render(1439, "avionics"), GRADLE_SNIPPET, count=1)
        twice = sd.BULLET_RE.sub(sd.render(1439, "avionics"), once, count=1)
        self.assertEqual(once, twice)

    def test_regex_does_not_swallow_the_whole_list(self):
        out = sd.BULLET_RE.sub("X", GRADLE_SNIPPET, count=1)
        self.assertIn("</ul>", out)
        self.assertEqual(out.count("<li>"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
