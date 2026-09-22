# Clause obligations: binding a leaf to the items it discharges

A leaf that cites a clause says what it is about. It does not say how much of
the clause it covers, and until now nothing in this repository recorded that.
A leaf could cite a clause, render half of it faithfully, and pass every gate
here.

The fidelity audit measured what that costs. Leaf-to-clause fidelity was
**39.2%** under the strict reading, and omission, not error, was the main
failure: most leaves that missed a clause missed it by leaving obligations
out, not by misstating them. In the 49 renderings first judged `partial`,
readers counted the obligations each cited clause imposes and how many the
leaf addresses: **83 of 191, or 43.5%**. Method, controls and limits are in
[`tools/fidelity/README.md`](../tools/fidelity/README.md); the 39.2% is in
[`tools/fidelity/results/run-seed20260921-n100.json`](../tools/fidelity/results/run-seed20260921-n100.json).
The 83-of-191 count comes from the same run of 2026-09-21. It is not yet in
that result file, so the figure here is a transcription, and this sentence
says so.

The binding described here is the repair. It moves the unit of claim from the
clause to its lettered items, and it makes every claimed item point at an
instruction the practitioner carries out.

## The binding

A leaf may declare, in its front matter, the items of a clause it makes the
practitioner discharge:

```yaml
clauses:
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.6.11.8
    items: [a, b]
    relation: implements
```

| Key | What it holds | Refused when |
|---|---|---|
| `standard` | the edition: an ECSS designation with its issue letter, and its revision when it has one (`ECSS-E-ST-50C Rev.2`, `ECSS-E-ST-70-41C`, `ECSS-Q-ST-20C Rev.2 Corr.1`) | the issue letter is missing, or the revision is written with a space (`Rev. 2`) |
| `clause` | the dotted clause number (`5.6.11.8`) | it carries the item letter, or YAML read it as a number (see below) |
| `items` | the item letters, inline: `[a, b]`. After `z`, ECSS doubles the letter: `aa`, `bb` | the list is empty, or holds anything but an item letter |
| `relation` | `implements` or `verifies` | anything else; `cites-clause` is reserved and refused |

- **`implements`**: the leaf makes the practitioner *do* the item.
- **`verifies`**: the leaf makes the practitioner *check* that the item was met.

`cites-clause` is reserved and refused because a binding is a claim about
obligations, and a claim that carries none is the defect this key exists to
remove. A leaf that is only about a clause says so in its prose, as it
always has.

Two rules come from YAML rather than from ECSS. An unquoted `clause: 5.10` is
the number 5.1 to a YAML reader, and `clause: 5` is an integer, so a clause
with fewer than two dots is written quoted (`clause: "5.10"`). The lost digit
cannot be recovered afterwards, so the binding is refused instead of repaired.
An item written `no`, `on`, `yes` or `off` reads as a boolean, and is refused
for the same reason.

Each item is declared once. If a leaf both does an item and checks it,
declare it with the relation of the step that anchors it.

The key is optional. A leaf with no binding is graded exactly as before.

## The anchor

A leaf that declares clauses carries an `## Obligations` section: one table,
`| Item | Step |`, with one row for every declared item. Step is the number
of a step in the leaf's numbered procedure, which in this corpus is the
`## Workflow` section (`## Procedure` and `## Steps` are read the same way;
a leaf may have only one of them). The steps must be numbered 1 to n in
order, so the number in a row is the number a reader sees.

A worked example, front matter and anchor together:

```markdown
---
name: e50-example-leaf
description: "..."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
clauses:
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.6.11.8
    items: [a, b]
    relation: implements
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.6.11.9
    items: [a]
    relation: verifies
metadata:
  version: 0.1.0
  author: Aero Agent Skills
---

## Workflow

1. ...
2. ...
3. ...
4. ...

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.6.11.8a | 2 |
| ECSS-E-ST-50C Rev.2 5.6.11.8b | 3 |
| ECSS-E-ST-50C Rev.2 5.6.11.9a | 4 |
```

The locators in this example show the shape only. They are not a claim about
what those items require.

## What `make obligations` refuses

The gate (`tools/obligations/obligations_gate.py`, in `make validate`) reads
every SKILL.md and refuses, naming the leaf and the item each time:

1. a malformed binding: any key, value or shape the table above refuses,
   including the reserved relation, a `clauses` key nested under another key,
   declared twice, or written inline, and a trailing comment on a binding
   line (the repository's front-matter readers disagree about a trailing
   comment, so a comment in a binding goes on its own line);
2. a declared item with no row: the leaf claims more than it anchors;
3. a row for an item the front matter does not declare;
4. a row whose Step does not exist in the procedure, or a bound leaf with no
   numbered procedure at all;
5. a duplicate: an item declared twice, or two rows for one item;
6. a malformed table: a header other than `| Item | Step |`, a row that is
   not `<standard> <clause><item>` and one step number, a second table, or a
   second `## Obligations` section.

Gate 1 (`scripts/spec_lint.py`) checks the `clauses` key with the same rule
module (`tools/obligations/obligation_binding.py`), so the two gates cannot
disagree about what a well-formed binding is. The gate's own tests
(`tools/obligations/test_obligations.py`) also read each accepted shape with
PyYAML and with the other two front-matter readers in this tree, and fail if
any of them reads it differently.

A negative control plants each of the defects above in a copy of the tree
and requires the gate to name it: `make negative-controls`, or
`python3 tools/negative_controls/run_negative_controls.py --only obligations`.

## What a green means, and what it does not

A green means every item a leaf claims is **anchored**: it points at an
instruction the practitioner performs, in a step that exists.

It does not mean the step discharges the item. A row can point at the right
step and the step can still render the item wrongly or in part. No mechanical
check can settle that. It is settled by reading, which is what the fidelity
audit does: sampled, blind, with planted mismatches the readers are not told
about, and a run that reports nothing when the readers miss them.

It does not mean a leaf that binds nothing is complete, and it says nothing
about items no leaf has claimed. The PASS line states how many leaves
declared a binding and how many did not.

It is not a compliance statement. A binding records what a leaf asks of the
practitioner; whether a project meets a standard is decided by that
project's own verification, not by this corpus.

## How it is measured

Two numbers, reported side by side and never summed:

- **Obligations addressed.** For each clause a leaf cites, the share of that
  clause's items the leaf addresses, judged by reading. The denominator is
  every item the clause holds, bound or not, so an omission lowers it. The
  baseline is 43.5% (83 of 191), from the fidelity run of 2026-09-21. That
  baseline was read over a selected population — the renderings already judged
  partial — so a wave that reads a whole edition reports its own before figure
  and compares against that, not against the 43.5%.
- **Claim precision.** Of the items leaves *declare*, the share the reading
  finds actually addressed at the anchored step. It has no baseline, because
  until now nothing was declared.

A binding can raise the first without earning it only by claiming items the
leaf does not address, and that is exactly what the second catches. Summing
them would let one hide the other.

Between readings there is a mechanical screen, not a verdict:
`tools/obligations/earm_items.py coverage` compares, for every bound leaf,
the items it declares with the items ESA's export holds for that clause. A
declared item the export does not hold is usually a wrong locator. An item
the export holds and no leaf declares is a candidate omission for the next
reading.

## Writing a binding

The authority for which items a clause has is ESA's EARM: the export of the
ECSS requirements database, one row per item, with current and superseded
editions on separate sheets. It is handed to the tool by path and never kept
here.

```
python3 tools/obligations/earm_items.py items --export <EARM.xlsx> \
    --standard "ECSS-E-ST-50C Rev.2" --clause 5.6.11.8
python3 tools/obligations/earm_items.py items --export <EARM.xlsx> \
    --standard "ECSS-E-ST-50C Rev.2" --clause 5.6.11.8 --ids
python3 tools/obligations/earm_items.py coverage --export <EARM.xlsx>
python3 tools/obligations/earm_items.py standards --export <EARM.xlsx>
```

`items` prints each item's locator, identifier, type and change status, then
its text, to the terminal, for the writer to read. It never writes the text
to a file: it has no output option, and it refuses to run when standard
output is redirected to one. `--ids` prints the same rows with no text.

Then:

1. Read the items. Decide which ones the leaf makes the practitioner do or
   check.
2. Write or repair the procedure step that does it, **in your own words**.
   Paraphrase the obligation, never the wording: do not add an obligation the
   item does not impose, and do not weaken one it does. No ECSS text enters
   this repository; `make no-verbatim` compares ECSS prose against the
   source documents.
3. Declare the items in `clauses:` and add one `## Obligations` row per item.
4. Run `make obligations`, then the coverage screen.

A retired item is shown by `items` and left out of `coverage`: it is no
longer an obligation. The export retires an item two ways, and the screen
reads both. Either the change status is `Deleted`, or the status is left
untouched and the whole text is replaced by a withdrawal marker
(`<<deleted>>`, sometimes saying where the obligation went). The marker has
to stand for the entire text: a live requirement can carry one as a single
numbered sub-point, and that requirement still binds. Until 2026-09-22 the
screen read only the change status, so it reported a withdrawn item as an
omission that no leaf could ever repair — the item is gone from the
standard. One item of wave 1's scope was in that state, which is why the
screen and the wave's denominator disagreed by one before this was fixed.

Annex requirements (locators such as `A.2.1<1>a`) and sub-items (`a.1`) have
no form in this binding; the coverage screen counts them apart rather than
dropping them silently.

## The published schedule

This is a commitment, published before the work, so that a slip is visible.

The corpus holds 1,365 citations from a leaf to a clause, across 44 ECSS
editions, in 1,264 of its leaves. Those figures are the planning count taken
for this schedule on 2026-09-22. The citation reader of the fidelity audit
(`tools/fidelity/fidelity_audit.py`) uses a different rule and finds 1,378 on
the same day's tree. The two answer different questions and neither replaces
the other: each wave's scope is re-counted from the tree when the wave opens,
and published with it.

- **Wave 1, 2026-09-22:** ECSS-E-ST-50C Rev.2.
- **Then one wave a week**, about 150 citations each, largest editions first,
  finishing by **2026-12-01**.
- **Each wave is re-measured before the next starts**: the obligations
  addressed and the claim precision for the leaves it bound, by the fidelity
  audit's method.
- **A missed week is published as missed**, here, dated, in the log below.
  The schedule is not re-based quietly.

The order, largest first, with the planning count for each edition:

| Order | Edition | Leaves | Citations |
|---|---|---|---|
| 1 | ECSS-E-ST-50C Rev.2 | 70 | |
| 2 | ECSS-E-ST-70-41C | 111 | |
| 3 | ECSS-E-ST-20-08C Rev.2 | 109 | |
| 4 | ECSS-E-ST-20-07C Rev.2 | 99 | |
| 5 | ECSS-E-ST-32C Rev.1 | 91 | 119 |
| 6 | ECSS-E-ST-10C Rev.1 | 64 | |
| 7 onward | the remaining editions, largest first | | |

The planning count orders the editions by the leaves that cite them, and
states a separate citation count only for ECSS-E-ST-32C Rev.1. Cells it did
not state are left blank rather than filled in.

### Wave log

| Wave | Opened | Scope | Closed | Obligations addressed | Claim precision |
|---|---|---|---|---|---|
| 1 | 2026-09-22 | ECSS-E-ST-50C Rev.2 | 2026-09-22 | 61.6% → 100.0% (53/86 → 86/86) | 100.0% (86/86) |

Wave 1 bound every leaf that cites this edition — 70 of them — to 86 items
across 70 clauses, and was read blind: 150 cases over five sheets, the
before and after version of each leaf never on the same sheet, the
`clauses` block and the `## Obligations` table stripped from every case so a
reader could not see which version was in front of them or what the leaf
claimed. Ten planted controls paired an after-version procedure with a
clause of the same edition it does not serve; all 23 of their items were
graded not addressed, so the run is reportable under its own floor of 0.80.
Obligations addressed went from **53 of 86 (61.6%, 95% CI 51.1–71.2%)**
before to **86 of 86 (100.0%, 95% CI 95.7–100%)** after, counting `partial`
as a miss. Nothing was unjudgeable.
Counts, intervals, method and limits:
[`tools/obligations/results/wave-1-ECSS-E-ST-50CRev2.json`](../tools/obligations/results/wave-1-ECSS-E-ST-50CRev2.json).

Two things this row does not say. The 61.6% is **not** a measured improvement
on the 43.5% baseline above: that figure was read over the renderings already
judged partial, across every edition, and this one over all 70 of one
edition's leaves, worst and best together. Different populations; the before
figure here is wave 1's own baseline and the comparison to make. And claim
precision did not bind this wave: every leaf declared every live item of the
clause it cites, so its denominator is the same 86 items as the after rate
and the two numbers are arithmetically identical. It is reported as a check
with no room to differ, not as a second confirmation. The readers were
language-model readers, not ECSS-qualified engineers; this is a
self-measurement with a demonstrated instrument, not an independent audit.

One more thing the row does not say: seven of the 70 were reworded after the
reading and before this commit — one step of `e50-security`, whose wording
had captured two router cases belonging to other leaves, and phrase-level
rewording in six more to remove five-word runs they shared with the source
item text. Each keeps the same obligation at the same anchored step, and
none was re-read. The after rate is therefore reported on the texts as read,
not on the texts as committed.
