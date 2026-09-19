# Router evidence, exported so someone else can re-execute it

The router claim in this repository is a self-run number: our harness, our
cases, our score. That is the weakest tier of evidence there is, however many
cases it contains. This directory exists so the claim stops depending on our
harness. Everything needed to reproduce the published Hit@1 figure is here in
a plain format, with a runner short enough to read in one sitting, and a
manifest that makes it obvious if a later run used different evidence.

Nothing in this directory needs installing, and nothing reaches the network.
The dependency list is `python3` (3.8 or newer) and this repository's
`skills/` tree.

## The claim, stated precisely

> For each of the 1,754 cases in `cases/hit1-gated-cases.jsonl`, the
> deterministic offline router — scoring every one of the 3,033 indexed
> skills against the case's query and taking the single highest-ranked
> result — returns exactly the skill path the case names.
>
> Measured: **1,754 / 1,754 = 100.00% Hit@1.**

Five things that claim does *not* say, and that a reader should hold us to:

1. **No model is involved.** The router is token overlap with fixed weights.
   Rerun it a thousand times and nothing moves. "100%" here means "the
   arithmetic lands where we say it lands", not "an agent chose well".
2. **We wrote the cases.** They were authored alongside the skills they
   point at, so their wording is closer to the skill text than a stranger's
   wording would be. This measures whether the index is internally
   discriminating; it does not measure real user queries.
3. **It covers 938 of the 3,021 leaf skills** (31%). The other 2,083 leaves
   have no case in the gated set. See "Coverage" below.
4. **It is a top-1 test over a closed set.** Every case's answer is in the
   index; there is no "no skill applies" case and no abstention.
5. **A second case set in this directory fails 444 times.** It is shipped
   here on purpose; see "The two case sets".

## Files

| File | What it is |
| --- | --- |
| `cases/hit1-gated-cases.jsonl` | The 1,754 cases the repository's own gate executes. One JSON object per line. |
| `cases/hit1-ungated-cases.jsonl` | 3,300 further cases that exist in `eval/` but that no gate executes. |
| `manifest.json` | Counts, content hashes, router parameters and the recorded result for each case set. |
| `run_hit1.py` | The reference runner. Reads a case set, routes every case, prints Hit@1. |
| `reference_router.py` | The router itself: index, scoring, ranking. Under 200 lines. |
| `case_set.py` | The case-record format and the two hash definitions. |
| `yaml_subset.py` | A small YAML reader, so the bundle needs no PyYAML. |
| `export_cases.py` | Regenerates the case sets and the manifest from `eval/`. |
| `test_export_bundle.py` | 26 unittest cases over the reader, the scoring and the hashes. |

Every record in a case set has the same fields:

```json
{"case_id": "d1", "expected_skill": "avionics/do178c/development", "gated": true,
 "intent": "DO-178C development; requirement-to-code traceability",
 "query": "trace high-level requirements to low-level requirements and source code for a DO-178C flight control software item",
 "source": "eval/hit1-corpus.yaml", "uid": "corpus:d1"}
```

`uid` is unique within the file; `case_id` alone is not unique across the
ungated set, because the per-leaf fragment files reuse short ids. `intent` is
commentary — the runner never reads it — and is included so a reviewer can
judge whether a case is fair rather than take our word for it.

## Run it

From this directory:

```
python3 run_hit1.py
```

Expected output (the hashes are the ones in `manifest.json`; the timings are
whatever your machine does):

```
Aero Agent Skills - router evidence, reference runner
-----------------------------------------------------
case set       : hit1-gated-cases.jsonl  (manifest: gated)
cases          : 1754
sha256 file   : <64 hex>  [manifest: MATCH]
sha256 cases  : <64 hex>  [manifest: MATCH]
skills root    : ../../skills
skills indexed : 3033
sha256 index  : <64 hex>  [manifest: MATCH]
router         : tags x3.0  name x2.0  description x1.0  body x0.5  phrase +4.0
stop words     : 48 (sha256 <64 hex>)
timing         : index 1.1s, route 12.4s

Hit@1          : 1754 / 1754 = 100.00%
RESULT         : PASS
```

Exit status is 0 only when every case hits **and** all three hashes match
what the manifest recorded. A reproduced number over changed evidence is not
a reproduction, so the runner fails that case loudly rather than printing a
green line.

Useful flags:

```
python3 run_hit1.py --verbose                         # one line per case
python3 run_hit1.py --cases cases/hit1-ungated-cases.jsonl --expect 2856
python3 run_hit1.py --json report.json                # machine-readable
python3 run_hit1.py --skills /path/to/skills          # index another tree
```

## What the hashes mean

`manifest.json` records three digests, and the runner recomputes all three:

- **`sha256_file`** — the bytes of the case file. Detects any edit at all,
  including reformatting.
- **`sha256_cases`** — a canonical digest over `(uid, query, expected_skill)`
  for every case, sorted by uid. This is the assertion content: it survives
  reformatting and reordering, and changes the moment a query or an expected
  answer changes. This is the hash to quote when someone asks "did you run
  the same cases?".
- **`skill_index.sha256`** — covers the path, name, description, tags and a
  hash of the body of all 3,033 indexed skills, in path order. The router
  reads nothing else, so two runs printing this digest scored the same
  corpus. It changes whenever any skill's front matter or body changes, which
  is intended: the Hit@1 figure belongs to a specific index, not to the
  repository in general.

## The two case sets

Enumerating `eval/` rather than trusting any document, there are two
populations, and they are not the same size or the same quality of evidence.

| | Gated set | Ungated set |
| --- | --- | --- |
| Cases | **1,754** | **3,300** |
| Source files | 1 (`eval/hit1-corpus.yaml`) | 1,650 (`eval/hit1-*.yaml`) |
| Executed by `make hit1` | yes | **no** |
| Distinct expected skills | 938 | 1,650 |
| Hit@1 measured here | **1,754 / 1,754 = 100.00%** | **2,856 / 3,300 = 86.55%** |

`make hit1` runs `scripts/gate-hit1-corpus.sh`, which passes exactly one file
— `eval/hit1-corpus.yaml` — to `scripts/router_eval.py`. That script is the
only thing in the repository that executes a router case, and the corpus is
the only file it is ever handed: by the gate, and by the npm package
battery. The 1,650 per-leaf fragment files sitting beside it in `eval/` are
read only for their names and counts (gate 9's naming check, the metrics
generators). Their cases have never been run. Only 50 of the 3,300 fragment
queries also appear in the gated corpus.

Run over the same index, 444 of those 3,300 unexecuted cases do not resolve
to the skill they name: 442 in `space-systems`, 1 in `aerodynamics`, 1 in
`flight-test-operations`, spread over 371 distinct leaf skills, of which 73
miss on both of their cases. They are near-neighbour collisions — one
narrowly scoped leaf out-scoring another in the same standard family.

That is why both sets ship here. Publishing only the set that passes, while
1,650 files of authored-but-never-executed cases sit in the same directory,
would be choosing the evidence after seeing the result.

## Coverage

Measured against the 3,021 leaf skills in `skills/`:

- 938 leaves (31.0%) have at least one case in the gated set;
- 2,562 leaves (84.8%) have at least one case in either set;
- **459 leaves (15.2%) have no router case at all**, gated or not.

## Where the other numbers come from

The repository quotes several different Hit@1 case counts. They are snapshots
of one counter taken at different times, not different measurements:

- **1,754** — `docs/metrics.json` (`corpus_tasks`), the README badge and the
  npm manifest. This is the live count and it is correct: it is what the gate
  executes today, and it is what this bundle exports.
- **986**, **674**, **154**, **66** — appear in `docs/`, in a Makefile
  comment and in `docs/harness-contract.md`. All are stale values of the same
  counter and none matches the tree.

Only the first is a live figure. A reviewer should treat any Hit@1 count in
prose as stale unless it matches `manifest.json`.

## Taking this to Inspect or Harbor

The bundle is shaped so that handing it to an external runner is small and
obvious. Do not vendor either runner into this repository, and check its
licence before you do anything else.

**Inspect** (UK AI Safety Institute) evaluates a *dataset* with a *solver*
and a *scorer*. The adaptation is one file, outside this repository, and it
does not modify the bundle:

1. Read `cases/hit1-gated-cases.jsonl` with Inspect's JSON-lines dataset
   reader, mapping `query` to the sample input, `expected_skill` to the
   target and `uid` to the sample id.
2. Write a solver that calls this bundle's router and puts the result in the
   completion — the whole body is
   `state.output.completion = SkillIndex.from_tree("skills").top1(input)[1]`,
   with the index built once at module import.
3. Score with Inspect's exact-match scorer. No model is needed; the solver
   never calls one.

The number Inspect prints must be 1,754/1,754. If it is not, the disagreement
is between Inspect's dataset reading and ours, and the case file is the thing
to inspect first.

**Harbor** (the runner used for Terminal-Bench) executes a task in a
container and checks its exit status. The adaptation is not one task per
case — that would be 1,754 containers for an evaluation that takes twenty
seconds — but one task whose command is `python3 run_hit1.py` and whose
verification is that exit status. The bundle needs no changes for this: it
installs nothing, downloads nothing, and already fails non-zero when either
the Hit@1 figure or a hash does not match.

Either way, the thing to hand a third party is this directory plus `skills/`.

## Checking the bundle itself

```
python3 -m unittest discover -s tools/export -p "test_*.py"
```

26 tests, well under a second, all on small synthetic fixtures: the YAML
reader's folding and tag shapes, the scoring arithmetic term by term, the
tie-break, and the two hashes — including that the content digest ignores a
commentary edit and moves when an expected answer changes. unittest writes
its summary to stderr, so capture both streams if you script it.

## How this bundle was produced, and how to regenerate it

```
python3 export_cases.py           # rewrite both case sets and manifest.json
python3 export_cases.py --check   # fail if either is stale; writes nothing
```

`export_cases.py` reads `eval/hit1-corpus.yaml` and every `eval/hit1-*.yaml`
fragment, writes the two case sets, replays both through the reference router
and records counts, hashes and results in `manifest.json`. Run it after any
change under `eval/` or `skills/`; otherwise the recorded index hash goes
stale and `run_hit1.py` will (correctly) refuse to report a pass.

Two equivalences were checked when the bundle was first generated, because
both are places where a quiet difference would produce a confidently wrong
number:

- **The YAML reader.** `yaml_subset.py` was compared with PyYAML's
  `safe_load` over all 3,033 `SKILL.md` front matters (name, description,
  tags and the body text) and all 1,651 files in `eval/` (5,054 tasks: id,
  query, intent, expected skill). Zero differences.
- **The router.** `reference_router.py` was compared with the repository's
  `scripts/router_eval.py` case by case over the whole gated corpus — the
  winning skill and its score, not just the totals. Identical for all 1,754
  cases, against a frozen copy of `skills/` so that neither run could be
  scoring a different tree.

The reference runner pre-tokenizes each skill once instead of re-tokenizing
it for every case. That is the only difference between the two
implementations: same token sets, same weights, same tie-break, same result,
about forty times faster.
