#!/usr/bin/env python3
"""Tests for tools/obligations/earm_items.py.

The export these tests read is a tiny workbook BUILT in a temporary directory
with zipfile. Its text is placeholder prose written for the test; no ESA text
exists in this repository, and none is needed to prove the reader.

stdlib only. Run with `python3 tools/obligations/test_earm_items.py`.
"""

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from xml.sax.saxutils import escape

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import earm_items  # noqa: E402

TOOL = os.path.join(HERE, "earm_items.py")

HEADER = ["ECSS Source Reference", "DOORS Project", "ECSS Req. Identifier",
          "Type", "IE PUID", "RCM Version", "ECSS Change Status",
          "Original requirement", "Text of Note of Original requirement"]

PLACEHOLDER_A = "Placeholder obligation alpha for the reader test."
PLACEHOLDER_NOTE = "Placeholder note alpha."

# (standard, locator, type, identifier, status, text, note)
ROWS = [
    ("ECSS-E-ST-50C Rev. 2", "5.3.3a", "Requirement", "FX-50_0001", "Created",
     PLACEHOLDER_A, PLACEHOLDER_NOTE),
    ("ECSS-E-ST-50C Rev. 2", "5.3.3b", "Recommendation", "FX-50_0002",
     "Unchanged", "Placeholder obligation bravo.", ""),
    ("ECSS-E-ST-50C Rev. 2", "5.3.3c", "Requirement", "FX-50_0003", "Deleted",
     "Placeholder obligation charlie.", ""),
    ("ECSS-E-ST-50C Rev. 2", "5.3.30a", "Requirement", "FX-50_0004",
     "Created", "Placeholder obligation of a different clause.", ""),
    ("ECSS-E-ST-50C Rev. 2", "5.3a", "Permission", "FX-50_0005", "Created",
     "Placeholder obligation of the parent clause.", ""),
    ("ECSS-Q-ST-20C Rev.2 Corr.1", "4.1a", "Requirement", "FX-20_0001",
     "Created", "Placeholder obligation delta.", ""),
    ("ECSS-Q-ST-20C Rev.2 Corr.1", "A.2.1<1>a", "Requirement", "FX-20_0002",
     "Created", "Placeholder annex obligation.", ""),
]


def _col(i):
    return "ABCDEFGHIJKL"[i]


def build_export(path, rows=ROWS, header=HEADER, swap_content=False,
                 rich=True):
    """Write a minimal EARM-shaped workbook.

    Sheet order mirrors the real export's quirk of a title row above the
    header, and puts an information sheet with no header FIRST so the reader
    has to find the right sheet rather than take sheet one."""
    sst = []

    def s(text):
        if text not in sst:
            sst.append(text)
        return sst.index(text)

    def sheet_xml(table, header_row=True):
        out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
               '<worksheet xmlns="http://schemas.openxmlformats.org/'
               'spreadsheetml/2006/main"><sheetData>']
        r = 1
        if header_row:
            out.append('<row r="1"><c r="J1" t="s"><v>%d</v></c></row>'
                       % s("EARM"))
            r = 2
        for values in table:
            cells = []
            for i, v in enumerate(values):
                ref = "%s%d" % (_col(i), r)
                if v == "":
                    continue
                if isinstance(v, int):
                    cells.append('<c r="%s"><v>%d</v></c>' % (ref, v))
                elif v.startswith("inline:"):
                    cells.append('<c r="%s" t="inlineStr"><is><t>%s</t></is>'
                                 '</c>' % (ref, escape(v[7:])))
                else:
                    cells.append('<c r="%s" t="s"><v>%d</v></c>'
                                 % (ref, s(v)))
            out.append('<row r="%d">%s</row>' % (r, "".join(cells)))
            r += 1
        out.append("</sheetData></worksheet>")
        return "".join(out)

    data = [header]
    for std, loc, typ, ident, status, text, note in rows:
        if swap_content:
            loc, ident = ident, loc
        data.append([std, "Fixture v1.0", loc, typ, ident, 1, status,
                     "inline:" + text if text.endswith("delta.") else text,
                     note])
    current = sheet_xml(data)
    superseded = sheet_xml([header, ["ECSS-E-ST-50C", "Fixture old", "5.3.3a",
                                     "Requirement", "FX-50_0001", 1,
                                     "Created", "Placeholder older text.",
                                     ""]])
    info = sheet_xml([["About this fixture"]], header_row=False)
    sis = []
    for text in sst:
        if rich and text == "Placeholder obligation bravo.":
            sis.append('<si><r><t>Placeholder </t></r><r><rPr><b/></rPr>'
                       '<t>obligation bravo.</t></r><rPh><t>IGNORED</t></rPh>'
                       '</si>')
        else:
            sis.append("<si><t>%s</t></si>" % escape(text))
    files = {
        "[Content_Types].xml":
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.'
            'org/package/2006/content-types"/>',
        "xl/workbook.xml":
            '<?xml version="1.0"?><workbook xmlns="http://schemas.'
            'openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://'
            'schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Information" sheetId="3" r:id="rId3"/>'
            '<sheet name="Current" sheetId="1" r:id="rId1"/>'
            '<sheet name="Superseded" sheetId="2" r:id="rId2"/></sheets>'
            '</workbook>',
        "xl/_rels/workbook.xml.rels":
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.'
            'openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="worksheet" '
            'Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="worksheet" '
            'Target="worksheets/sheet2.xml"/>'
            '<Relationship Id="rId3" Type="worksheet" '
            'Target="/xl/worksheets/sheet3.xml"/></Relationships>',
        "xl/worksheets/sheet1.xml": current,
        "xl/worksheets/sheet2.xml": superseded,
        "xl/worksheets/sheet3.xml": info,
        "xl/sharedStrings.xml":
            '<?xml version="1.0"?><sst xmlns="http://schemas.openxmlformats.'
            'org/spreadsheetml/2006/main">%s</sst>' % "".join(sis),
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, body in files.items():
            z.writestr(name, body)
    return path


class ExportCase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="earm-test-")
        self.xlsx = build_export(os.path.join(self.tmp, "fixture.xlsx"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_tool(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stderr(io.StringIO()):
            rc = earm_items.main(list(argv), out=buf)
        return rc, buf.getvalue()


class ItemsMode(ExportCase):

    def test_prints_every_item_of_the_clause_in_export_order(self):
        rc, out = self.run_tool("items", "--export", self.xlsx, "--standard",
                                "ECSS-E-ST-50C Rev.2", "--clause", "5.3.3")
        self.assertEqual(rc, 0, out)
        lines = [ln for ln in out.splitlines() if ln[:1].isdigit()]
        self.assertEqual([ln.split()[0] for ln in lines],
                         ["5.3.3a", "5.3.3b", "5.3.3c"])
        self.assertIn("5.3.3c  FX-50_0003  Requirement  Deleted", out)
        self.assertIn(PLACEHOLDER_A, out)
        self.assertIn(PLACEHOLDER_NOTE, out)
        # rich text is joined; a phonetic guide is not text
        self.assertIn("Placeholder obligation bravo.", out)
        self.assertNotIn("IGNORED", out)
        # 5.3.30a belongs to another clause, 5.3a to the parent
        self.assertNotIn("5.3.30a", out)
        self.assertNotIn("parent clause", out)
        self.assertIn("sheet 'Current'", out)

    def test_ids_prints_no_text(self):
        rc, out = self.run_tool("items", "--export", self.xlsx, "--standard",
                                "ECSS-E-ST-50C Rev.2", "--clause", "5.3.3",
                                "--ids")
        self.assertEqual(rc, 0, out)
        self.assertIn("5.3.3a  FX-50_0001  Requirement  Created", out)
        self.assertNotIn("Placeholder", out)

    def test_a_corrigendum_edition_matches_its_base_designation(self):
        rc, out = self.run_tool("items", "--export", self.xlsx, "--standard",
                                "ECSS-Q-ST-20C Rev.2", "--clause", "4.1",
                                "--ids")
        self.assertEqual(rc, 0, out)
        self.assertIn("4.1a  FX-20_0001", out)
        self.assertIn("ECSS-Q-ST-20C Rev.2 Corr.1", out)

    def test_inline_string_cells_are_read(self):
        rc, out = self.run_tool("items", "--export", self.xlsx, "--standard",
                                "ECSS-Q-ST-20C Rev.2", "--clause", "4.1")
        self.assertEqual(rc, 0, out)
        self.assertIn("Placeholder obligation delta.", out)

    def test_an_annex_clause_can_be_read(self):
        rc, out = self.run_tool("items", "--export", self.xlsx, "--standard",
                                "ECSS-Q-ST-20C Rev.2", "--clause", "A.2.1<1>",
                                "--ids")
        self.assertEqual(rc, 0, out)
        self.assertIn("A.2.1<1>a", out)

    def test_another_sheet_by_name(self):
        rc, out = self.run_tool("items", "--export", self.xlsx, "--sheet",
                                "Superseded", "--standard", "ECSS-E-ST-50C",
                                "--clause", "5.3.3")
        self.assertEqual(rc, 0, out)
        self.assertIn("Placeholder older text.", out)

    def test_no_match_says_how_the_export_spells_the_edition(self):
        rc, out = self.run_tool("items", "--export", self.xlsx, "--standard",
                                "ECSS-E-ST-50C Rev.1", "--clause", "5.3.3")
        self.assertEqual(rc, 1)
        self.assertIn("the export spells this edition: ECSS-E-ST-50C Rev. 2",
                      out)

    def test_a_bad_clause_argument_is_refused(self):
        rc, _out = self.run_tool("items", "--export", self.xlsx, "--standard",
                                 "ECSS-E-ST-50C Rev.2", "--clause", "5.3.3a")
        self.assertEqual(rc, 2)


class ItNeverWritesTextToAFile(ExportCase):

    def test_stdout_redirected_to_a_file_is_refused_and_the_file_stays_empty(self):
        target = os.path.join(self.tmp, "captured.txt")
        with open(target, "w") as fh:
            r = subprocess.run(
                [sys.executable, TOOL, "items", "--export", self.xlsx,
                 "--standard", "ECSS-E-ST-50C Rev.2", "--clause", "5.3.3"],
                stdout=fh, stderr=subprocess.PIPE, text=True)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("standard output is a file", r.stderr)
        self.assertEqual(os.path.getsize(target), 0)

    def test_ids_may_go_to_a_file_because_it_carries_no_text(self):
        target = os.path.join(self.tmp, "ids.txt")
        with open(target, "w") as fh:
            r = subprocess.run(
                [sys.executable, TOOL, "items", "--export", self.xlsx,
                 "--standard", "ECSS-E-ST-50C Rev.2", "--clause", "5.3.3",
                 "--ids"], stdout=fh, stderr=subprocess.PIPE, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(target) as fh:
            body = fh.read()
        self.assertIn("5.3.3a", body)
        self.assertNotIn("Placeholder", body)

    def test_a_run_creates_no_file_anywhere_it_can_see(self):
        cwd = tempfile.mkdtemp(prefix="earm-cwd-")
        try:
            before = sorted(os.listdir(self.tmp))
            r = subprocess.run(
                [sys.executable, TOOL, "items", "--export", self.xlsx,
                 "--standard", "ECSS-E-ST-50C Rev.2", "--clause", "5.3.3"],
                cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn(PLACEHOLDER_A, r.stdout)
            self.assertEqual(os.listdir(cwd), [])
            self.assertEqual(sorted(os.listdir(self.tmp)), before)
        finally:
            shutil.rmtree(cwd, ignore_errors=True)


class ShapeChecks(ExportCase):

    def test_no_header_row_is_exit_2(self):
        bad = build_export(os.path.join(self.tmp, "noheader.xlsx"),
                           header=["A", "B", "C", "D", "E", "F", "G", "H",
                                   "I"])
        rc, _out = self.run_tool("items", "--export", bad, "--standard",
                                 "ECSS-E-ST-50C Rev.2", "--clause", "5.3.3")
        self.assertEqual(rc, 2)

    def test_locators_in_the_wrong_column_are_refused_not_guessed(self):
        bad = build_export(os.path.join(self.tmp, "swapped.xlsx"),
                           swap_content=True)
        buf = io.StringIO()
        err = io.StringIO()
        old = sys.stderr
        sys.stderr = err
        try:
            rc = earm_items.main(["standards", "--export", bad], out=buf)
        finally:
            sys.stderr = old
        self.assertEqual(rc, 2)
        self.assertIn("will not guess", err.getvalue())

    def test_not_a_workbook_is_exit_2(self):
        junk = os.path.join(self.tmp, "junk.xlsx")
        with open(junk, "w") as fh:
            fh.write("not a zip")
        rc, _out = self.run_tool("standards", "--export", junk)
        self.assertEqual(rc, 2)


class StandardsAndCoverage(ExportCase):

    def test_standards_lists_editions_with_counts_and_no_text(self):
        rc, out = self.run_tool("standards", "--export", self.xlsx)
        self.assertEqual(rc, 0, out)
        # 5.3.3c is deleted, so the 50C edition holds 4 live items
        self.assertIn("ECSS-E-ST-50C Rev. 2\t3 clause(s)\t4 item(s)", out)
        self.assertNotIn("Placeholder", out)

    def test_coverage_screens_declared_against_exported_items(self):
        root = os.path.join(self.tmp, "tree")
        leaf = os.path.join(root, "skills", "fam", "pack", "bound-leaf")
        os.makedirs(leaf)
        with open(os.path.join(leaf, "SKILL.md"), "w") as fh:
            fh.write("---\nname: bound-leaf\nclauses:\n"
                     "  - standard: ECSS-E-ST-50C Rev.2\n"
                     "    clause: 5.3.3\n"
                     "    items: [a, z]\n"
                     "    relation: implements\n"
                     "  - standard: ECSS-Q-ST-20C Rev.2\n"
                     "    clause: \"4.1\"\n"
                     "    items: [a]\n"
                     "    relation: verifies\n"
                     "  - standard: ECSS-E-ST-99C\n"
                     "    clause: 1.2.3\n"
                     "    items: [a]\n"
                     "    relation: verifies\n"
                     "---\n\n# x\n")
        rc, out = self.run_tool("coverage", "--export", self.xlsx,
                                "--root", root)
        self.assertEqual(rc, 0, out)
        self.assertIn("skills/fam/pack/bound-leaf/SKILL.md: ECSS-E-ST-50C "
                      "Rev.2 5.3.3 declared a,z; export holds a,b; not "
                      "declared: b; not in export: z", out)
        self.assertIn("ECSS-Q-ST-20C Rev.2 4.1 declared a; export holds a; "
                      "not declared: -; not in export: -", out)
        self.assertIn("ECSS-E-ST-99C 1.2.3 declared a; edition not in this "
                      "export", out)
        self.assertIn("1 leaf/leaves declare a binding (0 with refusals); 3 "
                      "clause binding(s); 4 declared item(s), 2 of them held "
                      "by the export; 1 export item(s) under bound clauses "
                      "not declared; 1 edition(s) not in the export", out)
        self.assertNotIn("Placeholder", out)

    def test_a_refused_entry_is_reported_not_silently_dropped(self):
        root = os.path.join(self.tmp, "tree2")
        leaf = os.path.join(root, "skills", "fam", "pack", "half-bound")
        os.makedirs(leaf)
        with open(os.path.join(leaf, "SKILL.md"), "w") as fh:
            fh.write("---\nname: half-bound\nclauses:\n"
                     "  - standard: ECSS-E-ST-50C Rev.2\n"
                     "    clause: 5.3.3\n"
                     "    items: [a]\n"
                     "    relation: implements\n"
                     "  - standard: ECSS-Q-ST-20C Rev.2\n"
                     "    clause: 4.1\n"
                     "    items: [a]\n"
                     "    relation: verifies\n"
                     "---\n\n# x\n")
        rc, out = self.run_tool("coverage", "--export", self.xlsx,
                                "--root", root)
        self.assertEqual(rc, 0, out)
        self.assertIn("half-bound/SKILL.md: binding has 1 refusal(s)", out)
        self.assertIn("(1 with refusals)", out)

    def test_coverage_of_an_unbound_tree_says_it_graded_nothing(self):
        root = os.path.join(self.tmp, "empty-tree")
        os.makedirs(os.path.join(root, "skills"))
        rc, out = self.run_tool("coverage", "--export", self.xlsx,
                                "--root", root)
        self.assertEqual(rc, 0)
        self.assertIn("nothing is bound yet", out)


# The export retires an item two ways. `retired` reads both, because a
# screen that read only the change status reported a withdrawn item as an
# omission nobody could repair: the item is gone from the standard, so no
# leaf can ever declare it.
WITHDRAWN = "<<deleted>>"
STILL_LIVE = ("Placeholder obligation echo, of which one numbered "
              "sub-point was withdrawn:\n1.\tstill required;\n2.\t"
              + WITHDRAWN)

MARKER_ROWS = [
    ("ECSS-E-ST-50C Rev. 2", "5.4.1a", "Requirement", "FX-50_0011",
     "Created", "Placeholder obligation of a bound clause.", ""),
    # status untouched, text replaced by the marker
    ("ECSS-E-ST-50C Rev. 2", "5.4.1b", "Requirement", "FX-50_0012",
     "Unchanged", WITHDRAWN, ""),
    # the same, with the trailing stop the export sometimes leaves
    ("ECSS-E-ST-50C Rev. 2", "5.4.1c", "Requirement", "FX-50_0013",
     "Unchanged", "<< Deleted, covered by 5.4.1a. >>.", ""),
    # a live requirement that merely CONTAINS a marker: still an obligation
    ("ECSS-E-ST-50C Rev. 2", "5.4.1d", "Requirement", "FX-50_0014",
     "Normative Change", STILL_LIVE, ""),
]


class WithdrawnItems(ExportCase):

    def setUp(self):
        super(WithdrawnItems, self).setUp()
        self.marker_xlsx = build_export(
            os.path.join(self.tmp, "markers.xlsx"), rows=MARKER_ROWS)

    def test_retired_reads_both_spellings_and_spares_a_live_requirement(self):
        def row(status, text):
            return {"status": status, "text": text}
        self.assertTrue(earm_items.retired(row("Deleted", "anything")))
        self.assertTrue(earm_items.retired(row("Unchanged", WITHDRAWN)))
        self.assertTrue(earm_items.retired(row("Unchanged", " <<deleted>>. ")))
        self.assertTrue(earm_items.retired(row("Unchanged", "<<deleted>>-")))
        self.assertTrue(earm_items.retired(
            row("Unchanged", "<<deleted, moved to 5.4.1a>>")))
        self.assertFalse(earm_items.retired(row("Unchanged", STILL_LIVE)))
        self.assertFalse(earm_items.retired(
            row("Unchanged", "Placeholder obligation foxtrot.")))

    def test_a_withdrawn_item_is_not_counted_as_an_obligation(self):
        rc, out = self.run_tool("standards", "--export", self.marker_xlsx)
        self.assertEqual(rc, 0, out)
        # a and d are obligations; b and c are withdrawn
        self.assertIn("ECSS-E-ST-50C Rev. 2\t1 clause(s)\t2 item(s)", out)

    def test_items_still_shows_a_withdrawn_row_to_the_writer(self):
        rc, out = self.run_tool("items", "--export", self.marker_xlsx,
                                "--standard", "ECSS-E-ST-50C Rev.2",
                                "--clause", "5.4.1")
        self.assertEqual(rc, 0, out)
        self.assertIn("5.4.1b  FX-50_0012  Requirement  Unchanged", out)
        self.assertIn(WITHDRAWN, out)

    def test_a_withdrawn_item_is_not_reported_as_an_omission(self):
        root = os.path.join(self.tmp, "marker-tree")
        leaf = os.path.join(root, "skills", "fam", "pack", "bound-leaf")
        os.makedirs(leaf)
        with open(os.path.join(leaf, "SKILL.md"), "w") as fh:
            fh.write("---\nname: bound-leaf\nclauses:\n"
                     "  - standard: ECSS-E-ST-50C Rev.2\n"
                     "    clause: 5.4.1\n"
                     "    items: [a, d]\n"
                     "    relation: implements\n"
                     "---\n\n# x\n")
        rc, out = self.run_tool("coverage", "--export", self.marker_xlsx,
                                "--root", root)
        self.assertEqual(rc, 0, out)
        self.assertIn("declared a,d; export holds a,d; not declared: -; "
                      "not in export: -", out)
        self.assertIn("0 export item(s) under bound clauses not declared",
                      out)


class Normalisation(unittest.TestCase):

    def test_revision_spellings(self):
        self.assertEqual(earm_items.norm_standard("ECSS-E-ST-50C  Rev. 2"),
                         "ECSS-E-ST-50C Rev.2")
        self.assertTrue(earm_items.edition_matches("ECSS-E-ST-50C Rev.2",
                                                   "ECSS-E-ST-50C Rev. 2"))
        self.assertFalse(earm_items.edition_matches("ECSS-E-ST-50C Rev.1",
                                                    "ECSS-E-ST-50C Rev. 2"))
        self.assertFalse(earm_items.edition_matches("ECSS-E-ST-50C",
                                                    "ECSS-E-ST-50-02C"))

    def test_split_locator_respects_clause_boundaries(self):
        self.assertEqual(earm_items.split_locator("5.3.3", "5.3.3aa"), "aa")
        self.assertIsNone(earm_items.split_locator("5.3.3", "5.3.30a"))
        self.assertIsNone(earm_items.split_locator("5.3.3", "5.3.3.1a"))


if __name__ == "__main__":
    unittest.main()
