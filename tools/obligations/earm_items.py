#!/usr/bin/env python3
"""Read an ESA EARM export and show a writer the items of one clause.

A binding (docs/OBLIGATIONS.md) names the lettered items of a clause that a
leaf discharges. To write one, the binder needs to see which items the clause
has. ESA's EARM export of the ECSS requirements database, one row per item,
is the authority this tool reads. It is handed in by path; nothing from it is
kept in this repository.

    earm_items.py items     --export EARM.xlsx --standard "ECSS-E-ST-50C Rev.2" --clause 5.3.3
    earm_items.py items     --export EARM.xlsx --standard ... --clause ... --ids
    earm_items.py coverage  --export EARM.xlsx [--root TREE]
    earm_items.py standards --export EARM.xlsx

items      prints each item of the clause -- locator, identifier, type,
           change status, then the item's text and note -- to the terminal
           for a writer to READ. It never writes the text to a file: it has
           no output option, and it refuses to run when standard output is
           redirected to a regular file. Paraphrase the obligation in your
           own words; the text itself must never enter this repository
           (make no-verbatim compares ECSS prose against the source).
--ids      the same rows with no text at all.
coverage   a mechanical screen over the corpus: for every leaf that declares
           a binding, the items it declares against the items the export
           holds for that clause. No text is printed. It is a screen, not a
           verdict: a declared item missing from the export is usually a
           wrong locator, and an export item nobody declared is a candidate
           omission for the fidelity audit to read.
standards  the editions the export holds, spelled the way it spells them,
           with item counts. No text.

THE COLUMNS, READ BY HEADER. The export's header row names them:
'ECSS Source Reference' (the edition), 'ECSS Req. Identifier' (the item
locator, e.g. 5.3.2a), 'IE PUID' (the database identifier), 'Type',
'ECSS Change Status', 'Original requirement' and 'Text of Note of Original
requirement'. The tool checks that the locator column really holds locators
and stops (exit 2) rather than guess when it does not.

The export writes revisions two ways ('Rev.2' and 'Rev. 2'); both match the
binding's 'Rev.2'. A retired item is shown by `items` and left out of
`coverage`, because it is no longer an obligation. The export retires an
item two ways: the change status reads 'Deleted', or the status is left
alone and the whole text is replaced by a withdrawal marker ('<<deleted>>',
sometimes saying where the obligation went). Both are read; a screen that
read only the status reported a withdrawn item as an omission nobody could
repair.

Exit 0 = done; 1 = nothing matched; 2 = could not read the export or refused
to print. stdlib only (zipfile + xml.etree); Python 3.9 through 3.14.
"""

import argparse
import os
import re
import stat
import sys
import zipfile
from collections import OrderedDict
from xml.etree import ElementTree as ET

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import obligation_binding as binding  # noqa: E402

MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
DOC_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PKG_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"

# field -> header text, as the export writes it.
HEADERS = OrderedDict([
    ("standard", "ECSS Source Reference"),
    ("locator", "ECSS Req. Identifier"),
    ("identifier", "IE PUID"),
    ("type", "Type"),
    ("status", "ECSS Change Status"),
    ("text", "Original requirement"),
    ("note", "Text of Note of Original requirement"),
])
REQUIRED = ("standard", "locator", "identifier", "type", "text", "note")
HEADER_SCAN_ROWS = 20

# A locator: clause (optionally an annex letter, optionally a <n> sub-clause
# the way data requirement annexes number them) followed by the item letters.
LOCATOR_RE = re.compile(r"^(?:[A-Z]\.)?\d+(?:\.\d+)*(?:<[\d.]+>)?[a-z]")
# The subset a binding can name: a dotted clause and an item letter.
BINDABLE_RE = re.compile(r"^(\d+(?:\.\d+)*)((?P<ch>[a-z])(?P=ch)?)$")
DELETED = "deleted"
# The export retires an item two ways, and only one of them is the change
# status. The other leaves the status alone and replaces the whole text with
# a withdrawal marker, sometimes saying where the obligation went:
# '<<deleted>>', '<< deleted >>', '<<deleted, covered by <clause>>>'. The
# marker has to stand for the ENTIRE text: a live requirement may carry one
# as a single numbered sub-point, and that requirement is still an
# obligation. Trailing punctuation the export leaves behind ('.' or '-') is
# not part of the marker.
WITHDRAWN_RE = re.compile(r"(?i)^<<\s*deleted\b.*>>$")


class ExportError(Exception):
    """The export cannot be read as the shape this tool knows."""


# ---------------------------------------------------------------------------
# reading the workbook
# ---------------------------------------------------------------------------

def _col(ref):
    m = re.match(r"^([A-Z]+)", ref or "")
    return m.group(1) if m else ""


def _text_of(el):
    """The visible text of a shared-string or inline-string element.

    Rich text is a run of <r><t>; phonetic guides (<rPh>) are not text."""
    parts = []
    for child in el:
        if child.tag == MAIN_NS + "t":
            parts.append(child.text or "")
        elif child.tag == MAIN_NS + "r":
            for t in child.iter(MAIN_NS + "t"):
                parts.append(t.text or "")
    return "".join(parts)


def _shared_strings(z):
    name = "xl/sharedStrings.xml"
    if name not in z.namelist():
        return []
    out = []
    with z.open(name) as fh:
        for _event, el in ET.iterparse(fh):
            if el.tag == MAIN_NS + "si":
                out.append(_text_of(el))
                el.clear()
    return out


def _sheet_paths(z):
    """[(sheet name, part path)] in workbook order."""
    try:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    except KeyError as exc:
        raise ExportError("not an xlsx workbook (%s missing)" % exc)
    targets = {}
    for rel in rels.iter(PKG_REL_NS + "Relationship"):
        target = rel.get("Target", "")
        if target.startswith("/"):
            target = target.lstrip("/")
        elif not target.startswith("xl/"):
            target = "xl/" + target
        targets[rel.get("Id")] = target
    out = []
    for sheet in wb.iter(MAIN_NS + "sheet"):
        rid = sheet.get(DOC_REL_NS + "id")
        if rid in targets:
            out.append((sheet.get("name", ""), targets[rid]))
    return out


def _rows(z, part, sst):
    """Yield (row number, {column letter: text}) for one worksheet part."""
    with z.open(part) as fh:
        for _event, el in ET.iterparse(fh):
            if el.tag != MAIN_NS + "row":
                continue
            cells = {}
            for c in el.findall(MAIN_NS + "c"):
                kind = c.get("t")
                v = c.find(MAIN_NS + "v")
                if kind == "s" and v is not None and v.text is not None:
                    try:
                        value = sst[int(v.text)]
                    except (ValueError, IndexError):
                        raise ExportError("row %s: shared string %r is out of "
                                          "range" % (el.get("r"), v.text))
                elif kind == "inlineStr":
                    isel = c.find(MAIN_NS + "is")
                    value = _text_of(isel) if isel is not None else ""
                elif v is not None:
                    value = v.text or ""
                else:
                    value = ""
                cells[_col(c.get("r"))] = value
            try:
                rownum = int(el.get("r", "0"))
            except ValueError:
                rownum = 0
            el.clear()
            yield rownum, cells


def _norm_header(text):
    return re.sub(r"\s+", " ", (text or "")).strip()


def _find_header(z, part, sst):
    """(header row number, {field: column letter}) or None."""
    wanted = {v: k for k, v in HEADERS.items()}
    for rownum, cells in _rows(z, part, sst):
        found = {}
        for col, value in cells.items():
            field = wanted.get(_norm_header(value))
            if field:
                found[field] = col
        if all(f in found for f in REQUIRED):
            return rownum, found
        if rownum >= HEADER_SCAN_ROWS:
            break
    return None


class Export(object):
    """One sheet of an EARM export, read by header."""

    def __init__(self, path, sheet=None):
        self.path = path
        self.name = os.path.basename(path)
        try:
            self.zip = zipfile.ZipFile(path)
        except (OSError, zipfile.BadZipFile) as exc:
            raise ExportError("cannot open %s as an xlsx workbook: %s"
                              % (self.name, exc))
        self.sst = _shared_strings(self.zip)
        sheets = _sheet_paths(self.zip)
        if sheet is not None:
            chosen = [(n, p) for n, p in sheets if n == sheet]
            if not chosen:
                raise ExportError("no sheet named %r; the workbook has: %s"
                                  % (sheet, ", ".join(n for n, _ in sheets)))
            candidates = chosen
        else:
            candidates = sheets
        self.sheet = None
        for name, part in candidates:
            found = _find_header(self.zip, part, self.sst)
            if found:
                self.sheet, self.part = name, part
                self.header_row, self.columns = found
                break
        if self.sheet is None:
            raise ExportError(
                "no sheet%s carries the EARM header row (%s)"
                % ("" if sheet is None else " %r" % sheet,
                   ", ".join("'%s'" % HEADERS[f] for f in REQUIRED)))

    def rows(self):
        """Every data row as a dict of fields, in export order."""
        shaped = total = 0
        for rownum, cells in _rows(self.zip, self.part, self.sst):
            if rownum <= self.header_row:
                continue
            row = {f: (cells.get(col, "") or "") for f, col in self.columns.items()}
            row["row"] = rownum
            if not any(row.get(f, "").strip() for f in ("standard", "locator")):
                continue
            loc = row["locator"].strip()
            if loc:
                total += 1
                if LOCATOR_RE.match(loc):
                    shaped += 1
            yield row
        # Checked over the whole sheet, after the fact, so a caller that
        # has already printed rows still ends with the refusal.
        if total and shaped < 0.9 * total:
            raise ExportError(
                "the '%s' column holds locators in only %d of %d rows: this "
                "is not the column layout this tool reads, and it will not "
                "guess which column is which" % (HEADERS["locator"], shaped,
                                                 total))


def norm_standard(text):
    """'ECSS-E-ST-50C  Rev. 2' -> 'ECSS-E-ST-50C Rev.2'."""
    text = re.sub(r"\s+", " ", (text or "")).strip()
    return re.sub(r"\b(Rev|Corr)\.\s+(\d+)", r"\1.\2", text)


def edition_matches(query, exported):
    """True when an exported edition is the one a binding names.

    Exact after normalisation, or the export adds a corrigendum to the
    edition the binding names (the corrigendum does not renumber items)."""
    q, e = norm_standard(query), norm_standard(exported)
    if q == e:
        return True
    return "Corr." not in q and re.sub(r" Corr\.\d+$", "", e) == q


def split_locator(clause, locator):
    """The item part of `locator` when it belongs to `clause`, else None."""
    locator = locator.strip()
    if not locator.startswith(clause):
        return None
    rest = locator[len(clause):]
    if rest and rest[0].islower():
        return rest
    return None


# ---------------------------------------------------------------------------
# modes
# ---------------------------------------------------------------------------

def stdout_is_a_file():
    """True when standard output is redirected to a regular file.

    A replaced stream with no descriptor (io.UnsupportedOperation is both an
    OSError and a ValueError) is not a file."""
    try:
        return stat.S_ISREG(os.fstat(sys.stdout.fileno()).st_mode)
    except (OSError, ValueError, AttributeError):
        return False


def cmd_items(export, standard, clause, ids, out):
    hits = []
    editions = set()
    for row in export.rows():
        if not edition_matches(standard, row["standard"]):
            continue
        editions.add(row["standard"].strip())
        item = split_locator(clause, row["locator"])
        if item is not None:
            hits.append((item, row))
    if not hits:
        base = norm_standard(standard).split(" ")[0]
        near = sorted({r.strip() for r in _editions(export)
                       if norm_standard(r).startswith(base)})
        print("no items for %s clause %s in %s, sheet %r%s"
              % (standard, clause, export.name, export.sheet,
                 ("; the export spells this edition: %s" % ", ".join(near))
                 if near else "; no edition with that designation"),
              file=out)
        return 1
    print("%s clause %s: %d item row(s) -- %s, sheet %r, edition as "
          "exported: %s" % (standard, clause, len(hits), export.name,
                            export.sheet, ", ".join(sorted(editions))),
          file=out)
    if not ids:
        print("READ, then paraphrase. This text must never be written into "
              "the repository.", file=out)
    if ids:
        print("", file=out)
    for item, row in hits:
        status = row.get("status", "").strip() or "-"
        if not ids:
            print("", file=out)
        print("%s  %s  %s  %s" % (row["locator"].strip(),
                                  row["identifier"].strip() or "-",
                                  row["type"].strip() or "-", status),
              file=out)
        if ids:
            continue
        for line in (row["text"] or "").strip().splitlines() or ["(no text)"]:
            print("    " + line, file=out)
        note = (row["note"] or "").strip()
        if note:
            print("    NOTE:", file=out)
            for line in note.splitlines():
                print("      " + line, file=out)
    return 0


def _editions(export):
    seen = OrderedDict()
    for row in export.rows():
        seen.setdefault(row["standard"].strip(), None)
    return list(seen)


def retired(row):
    """True when the export says this item is no longer an obligation.

    Two spellings, and a screen that reads only the first reports a retired
    item as an omission nobody can repair. The change status says 'Deleted';
    or the status is left alone and the whole text is replaced by a
    withdrawal marker. The marker has to be the entire text: a live
    requirement can carry one as a single numbered sub-point and is still an
    obligation."""
    if row.get("status", "").strip().lower() == DELETED:
        return True
    text = (row.get("text") or "").strip().rstrip(".-").strip()
    return bool(WITHDRAWN_RE.match(text))


def export_index(export):
    """{normalised edition: (as exported, {clause: {item: type}})}.

    Retired items are left out: they are no longer obligations. Locators a
    binding cannot name (annex and sub-item forms) are counted apart."""
    index = OrderedDict()
    unbindable = 0
    for row in export.rows():
        std = row["standard"].strip()
        key = norm_standard(std)
        entry = index.setdefault(key, (std, {}))
        if retired(row):
            continue
        m = BINDABLE_RE.match(row["locator"].strip())
        if m is None:
            if row["locator"].strip():
                unbindable += 1
            continue
        entry[1].setdefault(m.group(1), {})[m.group(2)] = row["type"].strip()
    return index, unbindable


def _lookup(index, standard):
    for key, (spelled, clauses) in index.items():
        if edition_matches(standard, spelled):
            return spelled, clauses
    return None, None


def bound_leaves(root):
    skills = os.path.join(root, "skills")
    for dirpath, dirnames, filenames in os.walk(skills):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        if "SKILL.md" not in filenames:
            continue
        path = os.path.join(dirpath, "SKILL.md")
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            present, value, syntax = binding.read_leaf(fh.read())
        if not present:
            continue
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        if syntax:
            yield rel, [], len(syntax)
            continue
        items, refused = binding.validate(value)
        yield rel, items, len(refused)


def cmd_coverage(export, root, out):
    index, unbindable = export_index(export)
    leaves = clauses = declared = found = omitted = unreadable = 0
    missing_editions = set()
    for rel, items, refused in sorted(bound_leaves(root)):
        leaves += 1
        if refused:
            # Screened as far as it can be read, but never silently: a
            # refused entry is not in `items`, so it would vanish from the
            # counts below without this line.
            unreadable += 1
            print("%s: binding has %d refusal(s); `make obligations` names "
                  "them, and only the well-formed items are screened here"
                  % (rel, refused), file=out)
        groups = OrderedDict()
        for it in items:
            groups.setdefault((it.standard, it.clause), []).append(it.item)
        for (std, clause), letters in groups.items():
            clauses += 1
            declared += len(letters)
            spelled, table = _lookup(index, std)
            if spelled is None:
                missing_editions.add(std)
                print("%s: %s %s declared %s; edition not in this export"
                      % (rel, std, clause, ",".join(letters)), file=out)
                continue
            held = table.get(clause, {})
            unknown = [x for x in letters if x not in held]
            undeclared = [x for x in sorted(held) if x not in letters]
            found += len(letters) - len(unknown)
            omitted += len(undeclared)
            print("%s: %s %s declared %s; export holds %s; not declared: %s; "
                  "not in export: %s"
                  % (rel, std, clause, ",".join(letters),
                     ",".join(sorted(held)) or "nothing",
                     ",".join(undeclared) or "-", ",".join(unknown) or "-"),
                  file=out)
    print("coverage (%s, sheet %r): %d leaf/leaves declare a binding "
          "(%d with refusals); %d clause binding(s); %d declared item(s), %d of "
          "them held by the export; %d export item(s) under bound clauses "
          "not declared; %d edition(s) not in the export; %d export "
          "locator(s) not in bindable form (annex or sub-item)"
          % (export.name, export.sheet, leaves, unreadable, clauses, declared,
             found, omitted, len(missing_editions), unbindable), file=out)
    if not leaves:
        print("nothing is bound yet: this screen has graded no leaf", file=out)
    return 0


def cmd_standards(export, out):
    index, _unbindable = export_index(export)
    for _key, (spelled, clauses) in index.items():
        items = sum(len(v) for v in clauses.values())
        reqs = sum(1 for v in clauses.values() for t in v.values()
                   if t.lower() == "requirement")
        print("%s\t%d clause(s)\t%d item(s)\t%d requirement(s)"
              % (spelled, len(clauses), items, reqs), file=out)
    return 0


def main(argv=None, out=None):
    out = out or sys.stdout
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="mode")
    p_items = sub.add_parser("items", help="print one clause's items")
    p_cov = sub.add_parser("coverage", help="declared vs exported items")
    p_std = sub.add_parser("standards", help="editions the export holds")
    for p in (p_items, p_cov, p_std):
        p.add_argument("--export", required=True, help="path to the EARM .xlsx")
        p.add_argument("--sheet", default=None,
                       help="sheet name (default: the first carrying the "
                            "EARM header, i.e. the current requirements)")
    p_items.add_argument("--standard", required=True,
                         help="e.g. 'ECSS-E-ST-50C Rev.2'")
    p_items.add_argument("--clause", required=True, help="e.g. 5.3.3")
    p_items.add_argument("--ids", action="store_true",
                         help="locator, identifier, type and status only")
    p_cov.add_argument("--root", default=os.path.dirname(os.path.dirname(HERE)),
                       help="the tree whose bindings to screen")
    args = ap.parse_args(argv)
    if args.mode is None:
        ap.print_help(out)
        return 2
    if args.mode == "items":
        if not binding.CLAUSE_RE.match(args.clause) and not re.match(
                r"^[A-Z](?:\.\d+)+(?:<[\d.]+>)?$", args.clause):
            print("--clause %r is not a clause number" % args.clause,
                  file=sys.stderr)
            return 2
        if not args.ids and out is sys.stdout and stdout_is_a_file():
            print("refused: standard output is a file. The item text is for a "
                  "writer to read on a terminal and paraphrase; it is never "
                  "written to a file. Use --ids for a listing with no text.",
                  file=sys.stderr)
            return 2
    try:
        export = Export(args.export, args.sheet)
        if args.mode == "items":
            return cmd_items(export, args.standard, args.clause, args.ids, out)
        if args.mode == "coverage":
            return cmd_coverage(export, args.root, out)
        return cmd_standards(export, out)
    except ExportError as exc:
        print("earm_items: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
