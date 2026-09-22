# Negative controls — proving each gate can return RED

A gate nobody has ever watched fail is not a gate. It is a decoration that
reports PASS forever, and the longer it does so the more weight the estate
puts on it. This directory holds one **negative control** per gate: the
smallest mutation of a copy of the tree that the gate is supposed to reject,
plus the assertion that it does reject it.

```
python3 tools/negative_controls/run_negative_controls.py            # all gates
python3 tools/negative_controls/run_negative_controls.py --list     # gate set + mutations
python3 tools/negative_controls/run_negative_controls.py --only hit1 --verbose
python3 tools/negative_controls/run_negative_controls.py --keep     # keep the fixtures
```

Exit code is 0 only when **every** gate proved red-capable. Runtime is about
20 seconds. Nothing runs against the working tree, and nothing touches the
network.

## What a control has to show

Three conditions, all required:

1. **The baseline is green.** The fixture passes the gate before the
   mutation. A red baseline means the mutant's red cannot be attributed to
   anything.
2. **The mutant is red.** The gate exits non-zero.
3. **The red names the planted defect.** The output has to match the
   control's signature regex. A gate that exits non-zero because the
   mutation broke its parser has not detected anything — it crashed near the
   defect. Without this condition a control degrades into "something went
   wrong", which is how a gate keeps its reputation while losing its teeth.

## Three outcomes, not two

| state | what happened | what it is a finding about |
|---|---|---|
| `RED-CAPABLE` | all three conditions held | nothing — the gate works |
| `NOT PROVED` | the control ran; the gate stayed green, or went red without naming the defect | **the gate**: it is blind to the defect it exists for |
| `VOID` | the control could not run at all — the baseline was already red, or the mutation could not be applied | **the suite**: it says nothing whatever about that gate |

Only `RED-CAPABLE` counts towards the headline, and every state is listed
separately. This distinction is not cosmetic. Until 2026-09-19 both failure
modes printed the same `DID NOT FAIL — INVESTIGATE`, so a run in which one
control had never executed — its fixture was missing a helper the gate
needed, and baseline and mutant failed identically — was read as a gate
finding. The headline of that run was "11 of 12 gates proved red-capable"
when the honest reading was ten proved, one blind, one never exercised.

A `VOID` prints the first few failing lines of its own baseline, because a
`VOID` is a repair job for this directory rather than a report about a gate.

## The gate set

Read out of the `Makefile` at run time rather than hard-coded, so a gate
added to `validate` or `attest` without a control is reported instead of
being silently skipped:

| gate | ran by | mutation applied to the copy |
|---|---|---|
| lint-spec | validate | leaf `SKILL.md` frontmatter `name` no longer equals its parent directory |
| desc-lint | validate | the description's explicit "Use when" clause reworded away (word count unchanged) |
| pytest-contract | validate | the leaf logic module's first public function stubbed to return `None` |
| no-verbatim | validate | a proprietary-source marker line planted in a leaf `SKILL.md` |
| hit1 | validate | one corpus task's `expected_skill` repointed at a different leaf |
| independence | validate | a claims-ledger row's verifier set to its own generator |
| release-law | validate | `docs/metrics.json` leaf count pushed over the next 100-skill band |
| portability | validate | a *passing* `assertLess` planted 1e-13 from its bound inside a contract test |
| corpus-naming | validate | one leaf's corpus fragment duplicated under a second spelling |
| number-snapshot-offline | attest | the register's tracked star figure drifted away from the recorded snapshot |
| brief-audit | attest | a published figure under `docs/` drifted away from the canonical register |
| content-policy-sweep | attest | an export-compliance claim planted in a leaf `SKILL.md` |
| obligations | validate | six controls, one per defect class: the fixture's ECSS leaf is given a correct clause binding (two items, each anchored to a real step) and then one of: a declared item with no `## Obligations` row; a row for an undeclared item; a row pointing at a step that does not exist; a standard without its issue letter; an item declared twice; the reserved relation `cites-clause`. Each signature names the leaf and the item |

The table above is not the whole roster; `--list` prints every control the
suite runs, read from `controls.py`.

### A gate may carry several controls

A gate that claims to catch several defect classes gets one control per
class, each on its own mutant and its own line of output (`obligations #1`
to `obligations #6`). Until 2026-09-22 the controls were indexed by gate in a
plain dict, so a second control for the same gate silently replaced the
first: gate 4's publisher-marker control never ran once its source-text
control was added. Both run now. The headline counts gates and controls
separately, and a gate is RED-CAPABLE only when every one of its controls is.

The obligations controls carry a diagnosis: when one fails, the same leaf is
given the correct binding alone, so a gate that refuses correct bindings is
told apart from a gate that is blind to the planted defect. Each of the six
was also shown to go `NOT PROVED` when its own check was removed from a copy
of the gate (with the gate's detector suites taken out of that copy's recipe,
since they catch the removal first and would make the baseline red).

Marker strings the gates hunt for are assembled from fragments inside
`controls.py`, so this directory never itself carries one.

## Last measured result

**2026-09-22, with gate 19 (`obligations`) added: 26 of 26 gates
RED-CAPABLE across 32 controls, nothing `NOT PROVED`, nothing `VOID`, runner
exit 0.** Eighteen gates by fixture mutation (the obligations gate by six
controls, gate 4 by two, now that both of its controls run) and eight by
their own detector suites.

Earlier:

**2026-09-19, working tree `r4-correction`: 12 of 12 RED-CAPABLE, nothing
`NOT PROVED`, nothing `VOID`, runner exit 0.**

Two of those twelve changed state that day and neither was a tuning of a
mutation:

* **`no-verbatim`** was `VOID`, not merely unproven. Gate 4 had been
  rewritten to exec `tools/verbatim_gate.py`, and the fixture's copy list
  was never updated, so the baseline died with
  `can't open file .../tools/verbatim_gate.py` and the mutant died the same
  way. The fixture now declares and carries that gate's helpers; the
  mutation is unchanged, and the gate catches it.
* **`portability`** had been a standing finding here: `make portability`
  ran every contract test through `runpy` with `sys.argv` left as
  `[runner, target]`, so `unittest.main()` read the target path as a test
  name, the loader made it a `_FailedTest`, and no assertion under the
  instrumentation ever executed — 3,021 of 3,023 contract tests aborted
  that way while the gate printed PASS. It was repaired in `scripts/`,
  which this directory does not own, during the same correction block. The
  in-method control now catches the planted assertion. The diagnosis probe
  and its note stay in `controls.py` so a regression names its own cause
  again.

Measurements go stale. Re-run the suite rather than quoting this figure.

### Known gap: gate 4's source-text half has no negative control

`no-verbatim` is proved red-capable by a **publisher marker** planted in a
leaf. Its other half — the shingle comparison against
`tools/verbatim-index/` — now *executes* on the baseline, and returns clean,
but nothing here proves it can return dirty. A true positive would need a
run of real ECSS source text, and the repo carries only one-way fingerprints
of those documents, by design. So gate 4 is proved red-capable for markers
and unproved for source text. That is a gap in this suite, stated here
rather than hidden behind the gate's single `RED-CAPABLE` line; closing it
belongs with whoever holds the source documents that built the index.

## The fixture

`fixture.py` builds a pruned copy of the tree in a temporary directory: the
gate scripts, `standards-map.yaml`, `docs/`, `research/`, `ops/automation/`,
the claims ledger, the release version files, the helpers each gate runs,
and **four** real leaf skills with their real corpus fragments. Four leaves
instead of 3,021 is the difference between a 14-second suite and a
several-minute one.

The fourth leaf is an ECSS one, and it is there for a reason worth stating:
the other three map to SAE, EASA, FAA and NASA, families gate 4 can only
check with publisher markers. On a three-leaf fixture the gate's coverage
line read `leaves fully source-checked=0 of 3` — the source-text half of
the gate, the half the 2026-09-19 rewrite exists for and the half that
covers most of the corpus, never ran at all. With the ECSS leaf the
baseline reports `source-checked=1 (leaves 1)` against a 144-document
index.

Every gate entry point and helper is hashed against the working tree after
the copy. If any of them differ the build aborts, because a control that
grades a paraphrase of a gate grades nothing. A gate source the tree has and
the fixture does not also aborts the build — that is the exact shape of the
`no-verbatim` failure above, and it used to surface as a red baseline
instead of an error.

### What a gate needs is declared, and the declaration is audited

`GATE_DEPENDENCIES` in `fixture.py` records, per gate, what that gate needs
beyond the blanket copies. Gate 4's three entries are there because the gate
execs them, not because it mentions them.

A declaration nobody checks is just a longer version of the list that was
already wrong, so `audit_gate_dependencies()` re-derives each gate's
dependency closure independently: it reads the target's recipe out of the
`Makefile`, follows every script that recipe **executes** (and every script
those execute, and every sibling module they import), and collects every
repo path each of them names. Anything in that closure the fixture does not
carry aborts the build with the gate and the path printed. A run states what
it audited:

```
3 declared gate dependencies copied (tools/verbatim-index, tools/verbatim_gate.py,
tools/verbatim_shingle.py); 42 statically-reachable paths audited across 12 gates,
none missing
```

The audit reads code, not prose: whole-line comments and docstrings are
stripped first, and a script that is merely *named* is required to exist but
is never followed. Both rules are load-bearing —
`scripts/corpus_naming_check.py` explains `leaf-create-gate.sh` in its
docstring and never runs it, and following that sentence dragged two paths
into the requirements that no gate ever reads.

Its blind spots, stated rather than discovered later: a path composed at run
time is invisible to it (`scripts/verify-independence.py` walks the tree for
claims ledgers, and `ops/automation/content-policy-sweep.sh` builds its scan
roots from bare directory names), so the hand-written declaration remains the
contract and the audit is the net under it.

Five deliberate departures from a byte-for-byte copy, each one load-bearing:

1. **Four leaves, not all of them.** Removing competitors can only make the
   router's job easier, so a corpus task that was top-1 in the full tree is
   still top-1 here.
2. **The Hit@1 corpus is assembled from those four leaves' own fragments.**
   Copying the full corpus would bring 1,754 tasks pointing at leaves this
   fixture does not carry.
3. **The three release version files are set to the band
   `docs/metrics.json` implies**, using the same logic `release-manager.py
   --sync` uses. The working tree itself is *not* currently aligned — the
   release-law gate is red on it today — and an already-red baseline proves
   nothing about the mutation.
4. **One extra page is added under `docs/`** carrying a figure copied from
   the number register at build time. Without a resolvable figure the
   brief-audit gate walks its scan roots, finds nothing to check and prints
   PASS: a green that graded nothing. The mutant drifts that figure.
5. **Each pack router's sub-skill table is pruned to the leaves the fixture
   carries.** Gate 1 resolves cross-references as of 2026-09-19; a router
   copied whole indexes every leaf in its pack, so the pack routers
   reported 342 unresolved references (measured on the three-leaf fixture)
   — departure 1 read back as a gate finding — and `lint-spec` went
   `VOID`. Only table rows are dropped. A
   leaf reference anywhere else aborts the build, because rewriting a
   sentence to keep a baseline green is how a fixture starts lying about
   the tree it stands in.

A stub `gh` is placed first on `PATH` for every gate run, so the one gate
that shells out to it (`release-law`, for a report-only parity note) fails
closed instead of reaching GitHub. The suite is offline by construction.

## Adding a control

Add a `Control` to `CONTROLS` in `controls.py` with the make target, a
one-clause description of the mutation, a signature regex that only the
planted defect can produce, and a mutation function. Mutation helpers raise
`MutationError` when they find nothing to change — a mutation that silently
does nothing would manufacture a "this gate cannot fail" finding, which is
worse than no control at all.

If the gate runs anything the fixture does not already carry, add it to
`GATE_DEPENDENCIES` under the gate's own name. The build will tell you if
you forget something it can see, but it cannot see a path the gate composes
at run time.

Keep mutations minimal and keep signatures specific. If a gate only goes red
for a mutation much larger than the defect class it claims to cover, that is
a finding: report it, do not enlarge the mutation until the light turns red.
The same rule governs a `VOID`: repair the fixture so the control can run,
never soften the mutation so the failure reads better.
