#!/usr/bin/env python3
"""Gate: a leaf that binds clause items anchors every one to a step.

A leaf may declare, in its front matter, the lettered items of an ECSS clause
it makes a practitioner discharge (the `clauses` key; the rules for the key
itself are in obligation_binding.py and docs/OBLIGATIONS.md). A declaration on
its own is a claim nobody can check. This gate makes it checkable: every
declared item must have a row in the leaf's `## Obligations` table, and every
row must point at a step that exists in the leaf's numbered procedure.

    ## Obligations

    | Item | Step |
    |---|---|
    | ECSS-E-ST-50C Rev.2 5.6.11.8a | 3 |

The procedure is the leaf's `## Workflow` section (`## Procedure` and
`## Steps` are read the same way; exactly one may be present), and a Step is
the number of one of its top-level numbered items.

REFUSED, each with the leaf and the item named:
  * a malformed binding (anything obligation_binding.validate refuses,
    including the reserved relation `cites-clause`, and a key the stdlib
    reader will not read);
  * a declared item with no row (declared items exceed anchors);
  * a row for an item the front matter does not declare;
  * a row whose Step is not a step of the procedure;
  * a duplicate: an item declared twice, or a row given twice;
  * a malformed table or row, a second Obligations section, a procedure
    whose numbering is not 1..n (a Step must name the number a reader sees).

WHAT A GREEN DOES NOT MEAN. The gate proves each claimed item is pointed at
an instruction the practitioner performs. It does not, and cannot, judge
whether that instruction discharges the item: that is read, sampled and
blind, by the fidelity audit (tools/fidelity/). A binding is optional, so a
tree in which no leaf declares one is green, and the PASS line says how many
leaves it actually graded.

Exit 0 = every binding is anchored (or none is declared); 1 = at least one
refusal; 2 = the gate could not run. stdlib only; Python 3.9 through 3.14.
"""

import argparse
import os
import re
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import obligation_binding as binding  # noqa: E402

GATE = "obligations"
PROCEDURE_TITLES = ("workflow", "procedure", "steps")
OBLIGATIONS_TITLE = "obligations"

_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$")
_STEP_RE = re.compile(r"^(\d+)[.)][ \t]+\S")
_SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")
_ROW_ITEM_RE = re.compile(
    r"^(?P<std>\S.*?)\s+(?P<clause>\d+(?:\.\d+)*)(?P<item>(?P<ch>[a-z])(?P=ch)?)$")


class Leaf(object):
    """What the gate reads out of one SKILL.md."""

    def __init__(self, rel, text):
        self.rel = rel
        self.refusals = []          # (subject, reason)
        self.declared = []          # binding.Item
        self.bound = False
        self.unreadable = False     # a binding is present but not readable
        self.rows = []              # (label, key, step, lineno)
        self.steps = None           # list of int, or None: no procedure
        self.procedure = None       # the heading title that held it
        self.has_obligations = False
        # Procedure-shape findings count only against a leaf that anchors to
        # the procedure: an unbound leaf is not graded by this gate at all.
        self.procedure_refusals = []
        self._read(text)

    # -- front matter ----------------------------------------------------
    def _read(self, text):
        text = text.replace("\r\n", "\n")
        present, value, syntax = binding.read_leaf(text)
        self.refusals.extend(syntax)
        self.unreadable = bool(syntax)
        if present and not syntax:
            items, refused = binding.validate(value)
            self.declared = items
            self.refusals.extend(refused)
        self.bound = present
        _front, end = binding.front_matter_lines(text)
        lines = text.split("\n")
        start = (end + 1) if end is not None else 0
        self._read_body(lines[start:], start)

    # -- body ------------------------------------------------------------
    def _read_body(self, lines, offset):
        headings = []               # (index, level, title)
        fenced = False
        for i, line in enumerate(lines):
            if line.lstrip().startswith(("```", "~~~")):
                fenced = not fenced
                continue
            if fenced:
                continue
            m = _HEADING_RE.match(line)
            if m:
                headings.append((i, len(m.group(1)), m.group(2).strip()))

        def extent(k):
            i, level, _title = headings[k]
            end = len(lines)
            for j, lvl, _t in headings[k + 1:]:
                if lvl <= level:
                    end = j
                    break
            return i + 1, end

        procedures = [k for k, h in enumerate(headings)
                      if h[1] == 2 and h[2].lower() in PROCEDURE_TITLES]
        obligations = [k for k, h in enumerate(headings)
                       if h[1] == 2 and h[2].lower() == OBLIGATIONS_TITLE]

        if len(procedures) > 1:
            self.procedure_refusals.append((
                "procedure", "more than one procedure section (%s): a Step "
                "cannot say which one it counts in"
                % ", ".join("## " + headings[k][2] for k in procedures)))
        elif procedures:
            k = procedures[0]
            self.procedure = headings[k][2]
            lo, hi = extent(k)
            self.steps = self._steps(lines[lo:hi])

        if len(obligations) > 1:
            self.refusals.append((
                "## Obligations", "the section appears %d times: a leaf has "
                "one Obligations table" % len(obligations)))
        if obligations:
            self.has_obligations = True
            lo, hi = extent(obligations[0])
            self._table(lines[lo:hi], offset + lo)

    def _steps(self, lines):
        steps = []
        fenced = False
        for line in lines:
            if line.lstrip().startswith(("```", "~~~")):
                fenced = not fenced
                continue
            if fenced:
                continue
            m = _STEP_RE.match(line)
            if m:
                steps.append(int(m.group(1)))
        if steps and steps != list(range(1, len(steps) + 1)):
            self.procedure_refusals.append((
                "## " + self.procedure, "the procedure is numbered %s, not "
                "1..%d: a Step must name the number a reader sees"
                % (", ".join(str(s) for s in steps), len(steps))))
        return steps

    def _table(self, lines, offset):
        blocks, current = [], None
        fenced = False
        for i, line in enumerate(lines):
            if line.lstrip().startswith(("```", "~~~")):
                fenced = not fenced
                current = None
                continue
            if not fenced and line.strip().startswith("|"):
                if current is None:
                    current = []
                    blocks.append(current)
                current.append((offset + i + 1, line))
            else:
                current = None
        if not blocks:
            self.refusals.append((
                "## Obligations", "the section carries no | Item | Step | "
                "table"))
            return
        if len(blocks) > 1:
            self.refusals.append((
                "## Obligations", "the section carries %d tables; the anchors "
                "are one | Item | Step | table" % len(blocks)))
        table = blocks[0]

        def cells(line):
            return [c.strip() for c in line.strip().strip("|").split("|")]

        header = [c.lower() for c in cells(table[0][1])]
        if header != ["item", "step"]:
            self.refusals.append((
                "## Obligations", "the table header is | %s |, not "
                "| Item | Step |" % " | ".join(cells(table[0][1]))))
            return
        if len(table) < 2 or not all(_SEPARATOR_CELL_RE.match(c)
                                     for c in cells(table[1][1])):
            self.refusals.append((
                "## Obligations", "the table has no |---|---| separator under "
                "its header"))
            return
        for lineno, line in table[2:]:
            row = cells(line)
            shown = row[0] if row else line.strip()
            if len(row) != 2:
                self.refusals.append((
                    shown, "Obligations row at line %d has %d cells, not 2 "
                    "(| Item | Step |)" % (lineno, len(row))))
                continue
            label = row[0].strip("`").strip()
            m = _ROW_ITEM_RE.match(label)
            if m is None:
                self.refusals.append((
                    label or "(empty)", "Obligations row at line %d: the Item "
                    "is not '<standard> <clause><item>', e.g. "
                    "'ECSS-E-ST-50C Rev.2 5.6.11.8a'" % lineno))
                continue
            std_bad = binding.standard_problem(m.group("std"))
            if std_bad:
                self.refusals.append((label, "Obligations row at line %d: %s"
                                      % (lineno, std_bad)))
                continue
            step_text = row[1].strip("`").strip()
            if not re.match(r"^\d+$", step_text):
                self.refusals.append((
                    label, "Obligations row at line %d: Step %r is not the "
                    "number of one step" % (lineno, row[1])))
                continue
            key = (m.group("std"), m.group("clause"), m.group("item"))
            self.rows.append((label, key, int(step_text), lineno))


def check_leaf(rel, text):
    """Every refusal for one SKILL.md, as (subject, reason) pairs."""
    leaf = Leaf(rel, text)
    out = list(leaf.refusals)
    if leaf.bound or leaf.has_obligations:
        out.extend(leaf.procedure_refusals)
    declared = {(d.standard, d.clause, d.item): d for d in leaf.declared}

    if not leaf.bound:
        if leaf.has_obligations:
            if leaf.rows:
                for label, _key, _step, lineno in leaf.rows:
                    out.append((label, "Obligations row at line %d anchors "
                                "an item the front matter does not declare "
                                "(this leaf declares no clauses)" % lineno))
            else:
                out.append(("## Obligations", "an Obligations section on a "
                            "leaf that declares no clauses"))
        return leaf, out

    seen_rows = {}
    for label, key, step, lineno in leaf.rows:
        if key in seen_rows:
            out.append((label, "Obligations rows at lines %d and %d anchor "
                        "the same item: one row per item"
                        % (seen_rows[key], lineno)))
            continue
        seen_rows[key] = lineno
        # An unreadable binding declares nothing that can be matched; its own
        # refusal is the finding, and matching rows against it would only
        # repeat that refusal once per row.
        if key not in declared and not leaf.unreadable:
            out.append((label, "Obligations row at line %d anchors an item "
                        "the front matter does not declare" % lineno))
        if leaf.steps is None:
            out.append((label, "Step %d: the leaf has no numbered procedure "
                        "(## Workflow) to anchor to" % step))
        elif step not in leaf.steps:
            span = ("1..%d" % len(leaf.steps)) if leaf.steps else "none"
            out.append((label, "Step %d does not exist: ## %s has steps %s"
                        % (step, leaf.procedure, span)))

    for key, item in sorted(declared.items()):
        if key not in seen_rows:
            where = ("no row in ## Obligations anchors it"
                     if leaf.has_obligations
                     else "the leaf has no ## Obligations section")
            out.append((binding.item_label(*key), "declared (clauses[%d], %s) "
                        "but %s" % (item.entry, item.relation or "refused "
                                    "relation", where)))
    return leaf, out


def iter_skill_files(root):
    skills = os.path.join(root, "skills")
    for dirpath, dirnames, filenames in os.walk(skills):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        if "SKILL.md" in filenames:
            yield os.path.join(dirpath, "SKILL.md")


def run(root, paths=None, out=sys.stdout):
    """Run the gate. Returns the exit code."""
    root = os.path.abspath(root)
    if paths:
        files = [os.path.abspath(p) for p in paths]
    else:
        if not os.path.isdir(os.path.join(root, "skills")):
            print("FAIL %s: no skills/ directory under the root: nothing "
                  "was graded" % GATE, file=out)
            return 2
        files = sorted(iter_skill_files(root))
    if not files:
        print("FAIL %s: no SKILL.md found; the gate graded nothing" % GATE,
              file=out)
        return 2
    refused_leaves = 0
    refusals = 0
    bound = 0
    declared = 0
    anchored = 0
    for path in files:
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError) as exc:
            print("FAIL %s: %s: cannot read: %s" % (GATE, rel, exc), file=out)
            refusals += 1
            refused_leaves += 1
            continue
        leaf, found = check_leaf(rel, text)
        if leaf.bound:
            bound += 1
            declared += len(leaf.declared)
        if found:
            refused_leaves += 1
            refusals += len(found)
            for subject, reason in found:
                print("FAIL %s: %s: %s: %s" % (GATE, rel, subject, reason),
                      file=out)
        elif leaf.bound:
            anchored += len(leaf.declared)
    if refusals:
        print("FAIL %s: %d refusal(s) in %d of %d SKILL.md; %d declare a "
              "binding" % (GATE, refusals, refused_leaves, len(files), bound),
              file=out)
        return 1
    print("PASS %s: %d SKILL.md read; %d declare a clause binding, %d "
          "declared item(s) anchored to a procedure step; %d carry no binding "
          "(optional, and not graded here)"
          % (GATE, len(files), bound, anchored, len(files) - bound), file=out)
    return 0


def main(argv=None):
    here_root = os.path.dirname(os.path.dirname(HERE))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=here_root,
                    help="the tree to grade (default: this checkout)")
    ap.add_argument("paths", nargs="*",
                    help="grade only these SKILL.md files")
    args = ap.parse_args(argv)
    return run(args.root, args.paths)


if __name__ == "__main__":
    sys.exit(main())
