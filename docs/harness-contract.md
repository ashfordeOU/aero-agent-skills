# Aero Agent Skills harness contract

Status as of 2026-09-19: rewritten against the live Makefile and the live gate output on branch r4-correction. The milestone record that used to open this file is preserved below, collapsed, because every figure in it is as-of its own date and none of them is the live figure.

<details>
<summary><b>Milestone record, 2026-08-31 to 2026-09-13 (historical; superseded figures, kept because they record what was true on each date)</b></summary>

Status: contract landed 2026-09-02. Harness REAL on skill 1
(avionics/do178c/planning), and the 09-04 milestone landed early 2026-08-31.

P6 (2026-09-13): gate 8 `portability` added, taking `make validate` to
8/8. math.pow, 10**x and math.log10 are not correctly rounded, so which
side of the last bit a result lands on differs between libm
implementations. A contract test that asserts a STRICT inequality at that
boundary passes on the macOS build host and fails on the Linux CI runner,
and the local battery cannot see it because it runs on the build host.
Measured: e20-launch-system-emc-compatibility asserted
`assertLess(raw, 10.0)` on 20*log10() of a field built from 10**(-db/20);
locally a few ULP under ten, on the runner exactly ten. Four consecutive
public commits went red on that one line. Gate 8 instruments
assertLess/assertGreater/assertLessEqual/assertGreaterEqual across every
shipped contract test and fails on any comparison within 1e-12 relative of
its bound. The fix is always to assert the behaviour rather than the
rounding direction (assertAlmostEqual at the boundary), never to widen the
engineering limit.

P5.2 (2026-08-31): Wave 2 fan-out build to sixty-nine verified
skills in twelve installable domain packs (81 SKILL.md under gate 1:
12 routers + 69 leaves). Fourteen new leaves across seven families:
avionics +3 (far-cs25/special-conditions,
flight-management/vertical-navigation, do254/configuration-management),
gnc-autonomy +3 (control/root-locus-design,
optimal-control/lqr-design, navigation/navigation-frames opening the
navigation pack), manufacturing-quality +1
(as9102/delta-fai), space-systems +2 (ecss/software-verification,
subsystems/communication-link-budget), structures +3
(fem/modal-analysis, composites/failure-criteria,
damage-tolerance/residual-strength), propulsion +2
(rocket/nozzle-design, turbofan/bypass-ratio-trade). No standards-map
changes (sixteen entries, ten gated). Gate 3 runs sixty-nine contract
tests; gate 5 runs 154 active corpus tasks (the 126 prior plus
twenty-eight domain tasks sc1/sc2, vn1/vn2, rl1/rl2, lqr1/lqr2,
nf1/nf2, df1/df2, dcm1/dcm2, sv1/sv2, ma1/ma2, fc1/fc2, res1/res2,
lb1/lb2, nz1/nz2, bpr1/bpr2). Owner: Ops Manager, Wave 2 build.
P5.2 (2026-08-31): Wave 3 fan-out build to eighty-three verified
skills in twelve installable domain packs (95 SKILL.md under gate 1:
12 routers + 83 leaves). Fourteen new leaves across nine families:
flight-mechanics +2 (performance/climb-performance,
performance/turn-performance), cross-cutting +2
(documentation/engineering-margins,
numerics/convergence-verification), vehicle-design +2
(sizing/ws-tw-trade, cost-estimation/parametric-cost),
flight-test-operations +2 (envelope/v-speeds,
performance/accelerate-stop-distance), aerodynamics +2
(high-speed/normal-shock, drag-polars/drag-polar),
manufacturing-quality +1 (ndt/ndt-method-selection), propulsion +1
(axial-compressor/axial-compressor-stage), gnc-autonomy +1
(guidance/proportional-navigation), space-systems +1
(orbit-mechanics/sun-synchronous-inclination). No standards-map
changes (sixteen entries, ten gated). Gate 3 runs eighty-three
contract tests; gate 5 runs 182 active corpus tasks (the 154 prior
plus twenty-eight domain tasks roc1/roc2, em1/em2, wt1/wt2, ns1/ns2,
turn1/turn2, vsp1/vsp2, pc1/pc2, pn1/pn2, ss1/ss2, dp1/dp2, nd1/nd2,
acst1/acst2, asd1/asd2, cv1/cv2). Owner: Ops Manager, Wave 3 build.
P5.1 (2026-08-31): Wave 5 library expansion to fifty-five verified
skills in twelve installable domain packs (67 SKILL.md under gate 1:
12 routers + 55 leaves). Twelve new leaves: propulsion +3
(gas-turbine-cycle, turbofan-cycle, rocket-sizing), flight-mechanics
+3 (breguet-range, takeoff-performance, longitudinal-stability),
flight-test-operations +2 (envelope-expansion,
stall-speed-determination), avionics +1 (lightning-protection),
aerodynamics +1 (cfd-turbulence-modeling), space-systems +1
(sun-pointing), structures +1 (crack-growth). No standards-map
changes (sixteen entries, ten gated). Gate 3 runs fifty-five contract
tests; gate 5 runs 126 active corpus tasks (the 102 prior plus
twenty-four domain tasks cg1/cg2, gt1/gt2, tf1/tf2, rs1/rs2, br1/br2,
tp1/tp2, lon1/lon2, ee1/ee2, vs1/vs2, lig1/lig2, tbm1/tbm2,
spt1/spt2). Owner: Ops Manager, Wave 5 build.
P2.1 (2026-08-31): twenty-seven published skills; gate 3 runs twenty-seven contract
tests, gate 5 runs sixty-six corpus tasks (fifty-eight domain tasks +
eight adversarial cross-pair tasks added across the P2.1 and P3.5 reworks).
P3.6 (2026-08-31): domain-pack restructure: the twenty-seven skills are
organized into nine installable domain packs (avionics,
space-systems, systems-engineering-safety, manufacturing-quality,
cross-cutting, aerodynamics, gnc-autonomy, structures, vehicle-design)
per the 12-discipline taxonomy; every pack carries a router
SKILL.md (52 SKILL.md under gate 1: 9 routers + 43 leaves); every
SKILL.md carries top-level `domain` and `pack` frontmatter
(enforced by scripts/pack_inventory.py, listed via `make packs`);
corpus tasks and future pins use pack paths. Owner: Ops Manager, Phase 0 build.
P3.5 (2026-08-31): library expansion to twenty-seven verified skills
in nine installable domain packs (52 SKILL.md under gate 1: 9 routers
+ 43 leaves). Fifteen new leaves across four new packs (aerodynamics,
gnc-autonomy, structures, vehicle-design) and the existing packs
(avionics +3, space-systems +2, systems-engineering-safety +2,
manufacturing-quality +1). standards-map.yaml extended with do-330,
do-160, as9102, mmpsd, naca-tr-824 (fourteen entries). Gate 3 runs
twenty-seven contract tests; gate 5 runs the expanded Hit@1 corpus
(sixty-six active tasks: domain tasks for every leaf, the t1/t2/t4
pins promoted, t3 still pinned to manufacturing-quality/as9100/quality,
plus adversarial cross-pair tasks xp1-xp8). pack_inventory.py now
validates router pack-vs-folder and domain-vs-taxonomy; gate 4 scans
README.md/STANDARDS.md/NOTICE alongside skills/ and docs/. Owner: Ops Manager, P3.5 build.
P3.7 (2026-08-31): Wave 4 library expansion to forty-three verified
skills in nine installable domain packs (52 SKILL.md under gate 1: 9
routers + 43 leaves). Sixteen new leaves across all nine packs:
avionics +3 (airworthiness-liaison, requirements-capture,
flight-planning), space-systems +2 (thermal-design,
attitude-control-sizing), systems-engineering-safety +2 (validation,
common-cause-analysis), aerodynamics +2 (airfoil-selection,
cfd-convergence), gnc-autonomy +1 (rendezvous-phasing), structures +2
(laminate-stiffness, miner-damage), vehicle-design +2 (tow-estimation,
inertia-estimation), manufacturing-quality +1 (counterfeit-prevention),
cross-cutting +1 (isa-atmosphere). No standards-map changes (fourteen
entries, nine gated). Gate 3 runs forty-three contract tests; gate 5
runs 102 active corpus tasks (sixty-six prior plus thirty-two domain
tasks al1/al2, rc1/rc2, fp1/fp2, td1/td2, ac1/ac2, va1/va2, cc1/cc2,
as1/as2, cfc1/cfc2, rp1/rp2, ls1/ls2, md1/md2, to1/to2, mi1/mi2,
cp1/cp2, isa1/isa2 plus adversarial xp9-xp12). Owner: Ops Manager,
Wave 4 build.
P5.2 (2026-08-31): Wave 5 fan-out build to one hundred twelve
verified skills in twelve installable domain packs (124 SKILL.md
under gate 1: 12 routers + 112 leaves). Twelve new leaves across
five families: propulsion +3 (axial-compressor/compressor-map,
gas-turbine-cycle/regenerative-cycle, rocket/propellant-selection),
cross-cutting +3 (sep2640/skill-evaluation,
documentation/engineering-report, units-atmos/unit-conversion),
flight-test-operations +2 (flutter/ground-vibration-testing,
planning/flight-test-instrumentation), manufacturing-quality +2
(as9100/calibration-control, ndt/ultrasonic-inspection),
systems-engineering-safety +2 (mbse/sysml-modeling,
arp4761a/particular-risk-analysis). No standards-map changes
(sixteen entries, ten gated). Gate 3 runs one hundred twelve
contract tests; gate 5 runs 240 active corpus tasks (the 216 prior
plus twenty-four domain tasks cmap1/cmap2, rgc1/rgc2, rps1/rps2,
ske1/ske2, er1/er2, uc1/uc2, gvt1/gvt2, fti1/fti2, cal1/cal2,
ui1/ui2, sys1/sys2, pra1/pra2). Owner: Ops Manager, Wave 5 build.
Sources: internal design briefs (router design; domain taxonomy;
legal/export-control compliance flags).

</details>

## Read this first

`make validate` and `make attest` are the offline batteries this repository ships.
This document is the contract they answer to: which gates run, what a green from
each one proves, what it does not prove, and how much of the corpus it actually
reached.

Three rules govern this document.

1. **A figure that can be computed is never typed.** Every count below is printed
   next to the command that produces it. `python3 tools/figure_audit.py --list`
   prints the register (`ops/automation/numbers.yaml`) beside the live value of
   every denominator; `python3 tools/figure_audit.py` fails any publishable
   document whose typed figure disagrees with the tree.
2. **Coverage is stated with its complement.** "N checked" is half a sentence.
   The other half is "M not checked, and why".
3. **A check that could not run reports UNCHECKED, never PASS.** An unchecked
   family is not a clean family, and nothing in this document may let the two
   read alike.

Every measurement quoted here was taken on 2026-09-19 on branch `r4-correction`
and is shown with the command that produced it. Re-run the command; do not trust
the transcript.

### What this document said before 2026-09-19, and what is true

| Published claim | What is true |
|---|---|
| A gate table with five rows; prose elsewhere in the file describing a gate 8 and a gate 9 | `make validate` runs the nine targets listed below and `make attest` three more. The table now lists every one of them. |
| A definition of done naming a five-gate battery on one skill | Definition of done is the whole battery green on every skill in the tree. See "Definition of done". |
| A gate 5 pass criterion of 154 tasks | The gate asserts 6,308 cases reaching all 3,189 leaves. It read one file and reached under a third of them until 2026-09-19; gate 13 now refuses a build in which any leaf has no case. Counts and commands in "Gate 5" below. |
| Gate 4 described as an RTCA/SAE/IAQG grep, with ECSS named as text that "must not trip the gate" | Gate 4 is family-aware. ECSS is the one family whose source documents are indexed, and ECSS prose in this repo IS compared against them; a long shared run fails the gate whether or not it carries a citation. |
| "Gated standards never appear verbatim anywhere in this repository - the no-verbatim gate enforces it" (also in README.md and docs/FAQ.md) | The gate compares body text for one family out of fourteen. For the other thirteen it checks publisher boilerplate only, or reports UNCHECKED. The no-verbatim rule is a policy the corpus follows; it is mechanically enforced only where an index exists. |

## What `make validate` runs

The roster is the prerequisite list of the `validate` target in the Makefile.
That line is the only authority; this table follows it in order.

```
$ grep -m1 '^validate:' Makefile
validate: lint-spec desc-lint pytest-contract no-verbatim hit1 independence release-law portability corpus-naming no-inference slug-uniqueness router-coverage-structure router-coverage-complete hermeticity evidence-contract export-bundle
$ grep -m1 '^validate:' Makefile | cut -d: -f2 | wc -w | tr -d ' '
16
```

| Gate | `make` target | Runner | A green means |
|---|---|---|---|
| 1 spec lint | `lint-spec` | `scripts/gate-spec-lint.sh` -> `scripts/spec_lint.py` | every SKILL.md in the tree conforms to the agentskills.io frontmatter contract and its compliance flags agree with `standards-map.yaml` |
| 2 description lint | `desc-lint` | `scripts/gate-desc-lint.sh` -> `scripts/desc_lint.py` | every description carries an action clause, an explicit "Use when", at least two triggers, and 50-150 words |
| 3 behaviour contracts | `pytest-contract` | `scripts/gate-pytest-contract.sh` | every shipped `scripts/test_*.py` imports stdlib only and passes under a driver the gate owns (the module's own `__main__` block never runs, so a test cannot report its own verdict) |
| 4 no-verbatim | `no-verbatim` | `tools/verbatim_gate.py` + `scripts/verbatim_table_scan.py` | no publisher boilerplate anywhere scanned, no objective-table block, and no long run of ECSS source text |
| 5 Hit@1 corpus | `hit1` | `scripts/gate-hit1-corpus.sh` -> `scripts/router_eval.py` | every case in `eval/` - the assembled corpus AND every per-leaf `hit1-<slug>.yaml` fragment - resolves top-1 to its expected skill through the deterministic offline router |
| 6 verifier independence | `independence` | `scripts/gate-verify-independence.sh` -> `scripts/verify-independence.py` | no claims-ledger row or evidence bundle has the same agent generating and verifying an artifact |
| 7 release law | `release-law` | `scripts/release-manager.py --check` | the version in the shipped manifests matches the release band the leaf count puts us in |
| 8 portability | `portability` | `scripts/portability_check.py` | no contract test asserts a strict inequality within 1e-12 relative of its bound, so no test depends on which side of the last bit a libm result lands |
| 9 corpus-fragment naming | `corpus-naming` | `scripts/corpus_naming_check.py --strict` | no leaf is covered by eval fragments filed under more than one spelling |
| 10 no-inference | `no-inference` | `scripts/gate_no_inference.py` | nothing on a verdict path calls a model; a claim@1 stays a computation |
| 11 slug uniqueness | `slug-uniqueness` | `tools/check_slug_uniqueness.py` | the flat fragment and install namespace is collision-free, so no leaf can overwrite another |
| 12 router coverage, structure | `router-coverage-structure` | `tools/router_coverage.py --structure-only` | `eval/hit1-corpus.yaml` has the shape gate 5 assumes: document root keys, four keys per case, unique ids |
| 13 router coverage, complete | `router-coverage-complete` | `tools/router_coverage.py --no-score --max-uncovered 0` | every leaf skill is named by at least one case, so no leaf ships that the router was never asked about |
| 14 hermeticity | `hermeticity` | `tools/determinism/hermeticity.py` | the generated artefacts carry no embedded timestamp, absolute path, hostname, build id or locale-dependent number -- a pipeline can be bit-identical on one machine and still be non-hermetic |
| 15 evidence contract | `evidence-contract` | `tools/evidence/tests/` (56 tests) | the evidence record's digest does not move with key order or float representation, floats are refused, and a regrade issues a successor rather than mutating a record |
| 16 export bundle | `export-bundle` | `tools/export/test_export_bundle.py` (26 tests) | the exported reference case set and its tokenizer behave as the shipped router expects |

`make validate` prints one summary line. That line is a summary of the targets
above and of nothing else: it is not evidence that the corpus is complete, and
the per-gate coverage sections below state what each target left untouched.

## What `make attest` runs

```
$ grep -m1 '^attest:' Makefile
attest: number-snapshot-offline brief-audit content-policy-sweep figure-audit gated-set-check stale-number-guard
```

| Target | Runner | A green means |
|---|---|---|
| number snapshot (offline) | `ops/automation/number-snapshot.sh --offline` | the recorded state snapshot regenerates from the tree at rest, with no network |
| brief audit | `ops/automation/brief-audit.sh` -> `ops/automation/number_audit.py` | every MARKET figure in the publishable documents resolves against the register in `ops/automation/numbers.yaml` |
| content-policy sweep | `ops/automation/content-policy-sweep.sh` | no compliance claim, certification claim, control marking, part number or military-platform parameter appears in publishable content |
| corpus figure audit | `tools/figure_audit.py` | every typed corpus figure in the publishable documents agrees with the tree it describes |
| gated-set check | `ops/automation/gated-set-check.sh` | no document states a gated-standards or map-coverage count that disagrees with `standards-map.yaml` |
| stale-number guard | `ops/automation/stale-number-guard.sh` | no live document still carries a retired count claim; a line marked a planning target is exempt, and the exemption does not leak past its own line |

## Checks that run, but not from `make validate`

| Check | How it is run | Why it is not in `validate` |
|---|---|---|
| visuals freshness | `make visuals-check`, run by `.github/workflows/attest.yml` | regenerates the charts and the README generator blocks and fails on any diff; it needs the generator, not the gate battery |
| npm package battery | `make package-test` | replays the whole Hit@1 corpus through the JavaScript router port and exercises the installer, MCP stdio and CLI; it needs Node |
| per-skill completeness | `make completeness` | reports as-needed gaps; blocking only with `--strict` |
| value delta | `make value-delta`, `make value-delta-all` | samples the with-skill versus without-skill contract delta |
| negative controls | `make negative-controls`, and `.github/workflows/attest.yml` | proves each gate of `validate` and `attest` still returns RED on an artifact built to fail it. It is NOT a prerequisite of `validate` or `attest` because it invokes `make <gate>` in subprocesses. The workflow step fails rather than skipping when the suite is absent, so it can no longer pass by grading nothing |
| public-safety audit | `ops/automation/publish-public.sh`, i.e. `make publish-public` | blocks a publish on absolute local paths and other leaks, and it grades the EXPORT rather than this tree. Note what that script replays inside the export: `make validate`, `make brief-audit`, `make content-policy-sweep`, `make visuals-check`, `make package-test` - the offline number snapshot is not among them |

## The release layer: is what we built what is published?

`make validate` and `make attest` are offline and deterministic by contract.
Neither can answer the one question a consumer actually cares about — is the
PUBLIC repo current? — because answering it needs the network.

That gap had a cost. On 2026-09-19 the public repo sat 18 hours behind dev with every dev
gate green, a drift of more than six release bands. Three faults had each aborted
the hourly publish; each wrote a line to a log and exited. Nothing graded
the shipping path, so nothing reported it.

| Check | How it is run | A green means |
|---|---|---|
| publish health | `make publish-health`, and every hourly publish | the public repo's own `docs/metrics.json` is within one release band of dev's, and the newest public tag is reported beside it |

Its exit codes are the part that matters:

```
0  verified: public content is current within tolerance
1  verified STALE: public is behind — the publish pipe is broken
2  COULD NOT VERIFY (no gh, no network, API refused)
```

**2 is not a pass.** A check that cannot run must not report success — the
same rule the negative-control battery follows, and the reason this check
exists at all. Its own detector suite
(`ops/automation/test_publish_health.py`) asserts that, and asserts that the
real 2026-09-19 drift is caught.

## Checks present in the tree and wired to nothing

As of 2026-09-19 these exist and run, but no `make` target and no workflow
invokes them. Presence is not enforcement, and this list exists so that nobody
reads the tree and assumes otherwise.

| Path | What it would check |
|---|---|
| `tools/determinism/perturb.py` | that a gate result does not move with the environment. Real and passing (39/39 runs byte-identical), but it re-runs the generators 40 times (~130s), so it has its own target rather than a place in `validate` |
| `tools/mutation/mutation_score.py` | whether the contract tests would catch a deliberately broken logic module. A SAMPLED score, not a pass/fail verdict: it cannot gate until somebody sets the bar it has to clear. `make mutation-score` |
| `scripts/leaf-audit.py`, `scripts/leaf-implementability-audit.py` | leaf content audits |

When one of these is wired, its row belongs in the roster table above and its
coverage statement in the section below, in the same commit.

## Gate detail, each with its complement

### Gate 1: spec lint

Checks per SKILL.md, against the open agentskills.io specification and the
compliance flags of the legal brief:

- file present at `skills/<path>/SKILL.md`, YAML frontmatter parses;
- `name` required, 64 characters or fewer, lowercase, numbers and hyphens,
  matching the parent directory;
- `description` required, 1024 characters or fewer; `compatibility` 500 or fewer
  when present; body under 500 lines;
- references one level deep, relative paths only;
- `license` equal to `Apache-2.0`;
- `compliance` one of `none | ITAR-GATED | EAR-GATED | STANDARDS-REF`;
- `standards` non-empty, every entry resolvable in `standards-map.yaml` by id or
  by name;
- `gated` consistent with the map: a standard the map marks `gated: true` must be
  listed reference-only in the skill, or the skill itself must be `gated: true`;
- `metadata.version` and `metadata.author` present.

Scope: every SKILL.md in the tree. The run of 2026-09-19 linted 3,201 SKILL.md files, which is every family
router plus every leaf (`find skills -name SKILL.md | wc -l`).

A green does not mean the skill is correct, useful, or that its standards
citations are the right ones. It means the file is well formed and its
declarations agree with the map.

### Gate 2: description lint

The description is what the router reads, so it is linted as an interface:
action clause, an explicit "Use when ...", a `Trigger` keyword with at least two
trigger keywords, 50-150 words. Same scope as gate 1: 3,033 descriptions on 2026-09-19.

A green does not mean the description routes well. Gate 5 is the only check that
tests routing, and it reaches a minority of leaves (below).

### Gate 3: behaviour contracts

Every leaf ships a stdlib-only `scripts/test_*.py` beside the logic module it
exercises, and the gate runs all of them offline. The gate imports each test
module under a private name, so the module's own `if __name__ == "__main__"`
block is dead code: a module cannot decide its own verdict by calling
`unittest.main(exit=False)` or `sys.exit(0)`. The verdict is computed by the
driver from the `unittest.TestResult`.

Scope on 2026-09-19: 3,189 test files
(`find skills -mindepth 5 -maxdepth 5 -name 'test_*.py' | wc -l`) across the
3,189 leaves (`find skills -mindepth 4 -maxdepth 4 -name SKILL.md | wc -l`).
Every leaf ships a real contract test. The file count runs two above the leaf
count for a reason a reader should have rather than infer: two leaves have
slugs that begin with `test-`
(`space-systems/ecss/test-analysis-correlation` and
`space-systems/ecss/test-philosophy-and-model-strategy`), so their LOGIC
modules are named `test_..._logic.py` and the discovery glob collects them as
contract tests. They assert nothing, and gate 3 fails them for exactly that
("no non-skipped test executed"). `make validate` is red on this tree today on
those two files and nothing else in gate 3. The defect is in the leaf slug and
the discovery glob; the verdict is correct and must not be relaxed.

A green does not mean the engineering is right. It means the shipped logic
module behaves as its own contract test says it should. The test and the module
are authored together, so a shared misconception passes; that is what
`tools/mutation/mutation_score.py` is for, and it is not wired.

### Gate 4: no-verbatim

The rule the gate serves has not changed: name plus paraphrase plus short
attributed quotes plus a link, never an objective table, appendix text or a
multi-line verbatim block. What has changed is the honesty of the enforcement.

Three parts:

1. **Markers.** Publisher boilerplate, licence and DRM lines and store URLs
   that only appear in a file if a page of a standard was pasted into it.
   Available for every publisher that stamps its documents. A marker check says
   nothing about body text, so a family with markers and no source text is
   reported markers-only, never covered.
2. **Source text.** Where a family's source documents were available at index
   build time, `tools/build_verbatim_index.py` distils them into one-way shingle
   fingerprints under `tools/verbatim-index/`, and the gate compares every
   scanned file against them. Any run of at least 32 identical words shares at
   least one fingerprint. One shared fingerprint is a WARN (on this corpus those
   are lists of defined terms, the vocabulary of the field); two or more mean a
   run of roughly fifty words and FAIL. `--min-fingerprints 1` makes every match
   fail.
3. **Coverage.** Every standards family present in the corpus is listed with the
   number of leaf-to-standard citations it carries and the check it received.

Scanned surfaces: `skills/`, `docs/`, and `README.md`, `STANDARDS.md`, `NOTICE`
at the root. Objective-table blocks are a separate runner
(`scripts/verbatim_table_scan.py`).

Coverage as the gate itself reported it on 2026-09-19 (`make no-verbatim`; the
"citations" column is the gate's own leaf count per family, and a leaf citing
several standards appears in several rows):

| Family | Publisher | Leaf citations | Check performed |
|---|---|---:|---|
| ecss | ECSS / ESA | 2,445 | source text + markers, against 144 source documents |
| faa | FAA (14 CFR) | 261 | UNCHECKED: US Government work: the source carries no copyright or licence boilerplate to match |
| easa | EASA | 149 | markers only |
| sae | SAE International | 120 | markers only |
| nasa | NACA / NASA | 94 | UNCHECKED: US Government work: the source carries no copyright or licence boilerplate to match |
| rtca | RTCA / EUROCAE | 50 | markers only |
| iaqg | IAQG (published by SAE) | 47 | markers only |
| aia | AIA (sold via Accuris/Techstreet) | 7 | markers only |
| mcp | MCP working group (open spec) | 6 | UNCHECKED: open specification, published without licence boilerplate to match |
| arinc | ARINC / AEEC (published by SAE ITC) | 5 | markers only |
| asme | ASME | 4 | markers only |
| dod | US DoD (MIL-STD) | 4 | UNCHECKED: US Government work: the source carries no copyright or licence boilerplate to match |
| ata | ATA / A4A | 1 | markers only |
| usgov | US Government (DDTC / BIS) | 1 | UNCHECKED: US Government work: the source carries no copyright or licence boilerplate to match |

The gate closes with a one-line COVERAGE summary of that same table. It is not
quoted here, and the omission is deliberate: `tools/figure_audit.py` reads the
parenthetical subset counts in that line ("(leaves 2445)") as corpus claims and
fails any document that quotes it. Reproduce the line with `make no-verbatim`.
The 2026-09-19 run scanned 9,115 files.

Read the table as: one family out of fourteen has its body text compared against
the real documents. That family is ECSS, and it covers 2,445 of the 3,021
leaves. Eight families, 383 further citations, get the marker check only, which
can catch a pasted page and cannot catch a retyped paragraph. Five families,
366 further citations, get neither and are reported UNCHECKED; 365 distinct
leaves carry at least one such citation. Three citations on one leaf
(`skills/avionics/do178c/planning/SKILL.md`, which spells its standards
`ARP4754A`, `ARP4761A` and `DO-178C`) resolve against no id in
`standards-map.yaml` at all and are reported UNMAPPED; gate 1 accepts them
because it resolves by id or by name, and gate 4 resolves by id only.

Five one-fingerprint WARNs stand on the ECSS side, each a short run of defined
terms; they are listed by path in the gate output and are under the two
fingerprints needed to fail.

A green from gate 4 therefore means: nothing pasted from a publisher that stamps
its documents, no objective-table block, and no long run of ECSS prose. It does
not mean the other thirteen families are free of verbatim text. Nobody has
checked. `make no-verbatim` accepts `--strict`, which turns every UNCHECKED
family into a failure; no `make` target passes it today.

### Gate 5: Hit@1 corpus

`eval/` holds queries with an expected skill each, resolved by the flat+tags
router (`scripts/router_eval.py`: token overlap over tags, name, description and
body with a tag boost; deterministic, offline). Pass means top-1 equals
`expected_skill` for every case in the directory.

Until 2026-09-19 the gate read one file, `eval/hit1-corpus.yaml`, and the 2,277
per-leaf fragments beside it were graded by nothing. That is the change: the
gate now executes the whole directory.

Scope, measured 2026-09-19 (the corpus grows during a build wave, so re-run
these rather than trusting the transcript):

```
$ grep -c '^  - id:' eval/hit1-corpus.yaml
1754
$ find eval -maxdepth 1 -name 'hit1-*.yaml' ! -name 'hit1-corpus.yaml' | wc -l
2277
$ find skills -mindepth 4 -maxdepth 4 -name SKILL.md | wc -l
3189
$ make hit1 | tail -1
PASS gate5-hit1: 6308/6308 tasks Hit@1 (deterministic offline router)
$ python3 tools/router_coverage.py --no-score | grep 'named by an executed case'
  named by an executed case                  3189  (100.00%)
```

The gate asserts every case in the directory: 6,308 of them, naming all 3,189
leaf skills. Before the flip it asserted 1,754 cases reaching 938 of them, so
the remaining 2,251 shipped with nothing ever asking the router about them.

A green from gate 5 still says only that the router picks correctly for the
queries that exist. What changed is the complement: there is no longer a leaf
with no query. Gate 13 is what keeps it that way -- gate 5 scores the cases it
finds and is silent about a leaf that brought none.

Two properties of the evidence that a green does NOT cover, both measured by
`tools/router_robustness.py` and neither gating anything today:

- the tokenizer keeps hyphens inside a token, so a user typing "bearing
  stress" never matches the tag `bearing-stress`. Re-scored with hyphens
  stripped from the query, Hit@1 is 6,086 of 6,308 (96.48%).
- 222 cases win by 0.5 or less. None now win by 0.0: a tie is broken on
  ascending skill path, which is not merit, and all 94 such cases were
  repaired rather than left to the alphabet.

Two further facts about the corpus, both measured the same day, both outside
this gate's control:

- `eval/` holds 2,277 router fragments with 4,554 cases between them, covering
  2,277 distinct leaves, and the assembled corpus holds 1,754 cases naming 938.
  The two sets overlap; together they name all 3,189. Gate 5 now runs both, so
  the assembly step no longer decides what is graded.
- No case shares more than six consecutive tokens with the leaf it expects
  (`tools/case_independence.py`). A case that recites its leaf cannot fail, and
  381 of them did before the repair; the gate 5 figure means less without this
  one beside it.
- The corpus header still describes a sixty-six-task P3.5 state and reconciles a
  Phase-0 baseline of five canonical queries. It is a historical note and should
  be read as one.

### Gate 6: verifier independence

The rule: the agent or process that VERIFIES an artifact must be independent of
the one that GENERATED it. The gate inspects the artifact kinds that carry both
roles as metadata - claims-ledger tables and evidence bundles - and fails on a
missing role, a generator equal to the verifier, a self-reference, or a verifier
naming the same model family as the generator. The run of 2026-09-19 checked 27 records.

A green does not mean every leaf was independently verified. It means no record
that exists claims otherwise. Leaves outside the ledger and the bundles are not
in scope for this gate and are not counted by it.

### Gate 7: release law

Every hundred new leaves is one minor version bump. The gate compares the leaf
count against the version declared in the shipped manifests and reports the
release band, so the fast lanes cannot drift silently. It also reports whether
the band's tag exists on the public repository.

A green means the declared versions match the band. It is a numbering check, not
a check that anything was released.

### Gate 8: portability

`math.pow`, `10**x` and `math.log10` are not correctly rounded, so which side of
the last bit a result lands on differs between libm implementations. A test that
asserts a STRICT inequality at that boundary passes on the macOS build host and
fails on the Linux CI runner, and a local battery cannot see it because it runs
on the build host. Measured 2026-09-13: one leaf asserted `assertLess(raw, 10.0)`
on `20*log10()` of a field built from `10**(-db/20)`; locally a few ULP under
ten, on the runner exactly ten, and four consecutive public commits went red on
that one line.

The gate instruments `assertLess`, `assertGreater`, `assertLessEqual` and
`assertGreaterEqual` across every shipped contract test and fails on any
comparison within 1e-12 relative of its bound. The fix is always to assert the
behaviour rather than the rounding direction (`assertAlmostEqual` at the
boundary), never to widen the engineering limit.

### Gate 9: corpus-fragment naming

`leaf-create-gate.sh` resolves corpus coverage with
`ls eval/hit1-*"$LEAF_NAME"*.yaml`, a glob wildcarded on both sides, so every
invented prefix satisfies it. Fourteen concurrent builders once filed the same
corpus under `hit1-e2008-*`, `hit1-w0913-e2008-*` and `hit1-wave-e2008-*`, and no
gate went red. The root cause was upstream: the builders were told to use "your
own scratch dir" without being given one.

The gate does not mandate a filename, which would break the legacy
`hit1-wave1-*` and `hit1-wave2-*` fragments that predate the slug convention. It
fails when a SINGLE leaf is covered by fragments under MORE THAN ONE spelling,
which is the defect itself and cannot be produced by legacy naming. A fragment
maps to the LONGEST leaf slug contained in its filename, so a shorter slug that
is a substring of a longer one does not steal the mapping. Canonical name for
anything new: `eval/hit1-<slug>.yaml`.

The gate states its own denominator, and on 2026-09-19 it reported:

```
WARN corpus-naming: 1372 of 3189 leaves (43.0%) have no corpus fragment, so this gate says nothing about them. Coverage is leaf-create-gate.sh's contract, not this gate's; --strict here rejects only a ZERO denominator.
WARN corpus-naming: 2 fragment(s) name no known leaf and graded nothing; each is either an aggregate file or an orphan left by a rename.
PASS corpus-naming: 1817 of 3189 leaf/leaves graded, one spelling each (1819 fragment(s), 2 unattributable)
```

## Determinism rules

- No network. Every gate runs locally on stdlib or pinned preinstalled tools
  (python3, PyYAML for the register readers, stdlib unittest).
- Fixed inputs, stable ordering (sorted finds), exit-code based.
- A gate with nothing to check reports that state; it does not print PASS over an
  empty denominator. Gate 9 prints EMPTY on a zero denominator and fails under
  `--strict`; gate 4 prints UNCHECKED per family and fails those families under
  `--strict`.
- No gate prints (STUB).

## What "verified" means in this repository

A skill is verified when the battery above passes on the commit that ships it.
Stated in full, that means:

- its SKILL.md is well formed and its declarations agree with the standards map
  (gates 1 and 2);
- its shipped contract test passes offline under a driver it cannot influence
  (gate 3);
- nothing in it matches a publisher marker or an objective-table block, and
  nothing in it shares a long run with an indexed ECSS document (gate 4);
- the router resolves every query that names it to it (gate 5), and at least
  one query names it (gate 13) - as of 2026-09-19 that holds for all 3,189
  leaves, where it previously held for 938;
- the repository-level invariants hold: independent verification records,
  version band, numeric portability, one corpus spelling per leaf, no model on
  a verdict path, a collision-free slug namespace and a well-formed corpus
  (gates 6 to 12).

It does not mean certification, approval, airworthiness, or that a
domain expert has reviewed the engineering. It does not mean the library is free
of verbatim standards text; it means no check that was run found any, and for
thirteen of the fourteen publisher families no check capable of finding body-text
reuse has been run at all.

## Numbers in this document

| Figure | Generator |
|---|---|
| gates in `make validate` | `grep -m1 '^validate:' Makefile \| cut -d: -f2 \| wc -w` |
| gates in `make attest` | `grep -m1 '^attest:' Makefile \| cut -d: -f2 \| wc -w` |
| leaves | `find skills -mindepth 4 -maxdepth 4 -name SKILL.md \| wc -l` |
| SKILL.md files (leaves + routers) | `find skills -name SKILL.md \| wc -l` |
| contract test files | `find skills -mindepth 5 -maxdepth 5 -name 'test_*.py' \| wc -l` |
| corpus tasks | `grep -c '^  - id:' eval/hit1-corpus.yaml` |
| cases gate 5 executes | `make hit1 \| tail -1` |
| leaves named by an executed case | `python3 tools/router_coverage.py --no-score` |
| leaves with no case anywhere | `make router-coverage-complete` |
| router fragments | `find eval -maxdepth 1 -name 'hit1-*.yaml' ! -name 'hit1-corpus.yaml' \| wc -l` |
| gate 4 coverage, per family | `make no-verbatim` (the COVERAGE line) |
| gate 9 coverage | `python3 scripts/corpus_naming_check.py` |

Seven of those are registered denominators in `ops/automation/numbers.yaml`:
`validate_gates`, `attest_gates`, `leaves`, `skill_md_files`, `test_files`,
`corpus_tasks` and `router_fragments`. `python3 tools/figure_audit.py --list`
prints each beside its live value, and `python3 tools/figure_audit.py` fails
this document when a typed figure drifts from the tree.

Three are NOT registered, and nothing grades them: the count of leaves the
corpus asserts, the gate 4 per-family coverage, and the gate 9 denominator.
They are transcribed here from the gate output on the date given, by a script
rather than by hand, and they will go stale silently. Registering them is owed
work, immediately below.

## Wiring still owed

Recorded here because this document is where a reader looks for the gap, not
because this document can close it. None of these are edits to this file.

1. Register in `ops/automation/numbers.yaml`: the gate 4 coverage figures
   (source-checked, markers-only, unchecked, unmapped), the gate 9 denominator,
   and the number of leaves the Hit@1 corpus asserts - so the three
   transcriptions above are graded rather than trusted. The last one is the
   single most load-bearing uncounted figure in the repository: it is the
   difference between "router-asserted" and "shipped".
2. Wire `tools/figure_audit.py` into a `make` target and into CI, so a typed
   figure cannot drift between publishes.
3. Wire the checkers listed under "present in the tree and wired to nothing", or
   record why each one stays manual. `tools/negative_controls/` is the urgent
   one: it is the only thing in the tree that would prove a gate can still
   return red, and the CI step that was supposed to do that job points at a
   file this tree does not contain.
4. Add `no-verbatim-strict` (the gate already accepts `--strict`) so the
   unchecked families can be made blocking the day an index exists for them.
5. Run `make visuals`. `scripts/gen_visuals.py` now derives the gate ratio from
   the Makefile's own prerequisite lists, but the blocks committed in README.md
   and the charts in docs/ predate that and predate the current corpus, so they
   still show the old battery. `make visuals-check` lists every stale artifact;
   this is a regeneration, not an edit, and it belongs to whoever owns the
   generator.
6. Generate the README "Verify" table from `collect_gates()` as well. It is
   written by hand today, so wiring a tenth gate leaves it one row short and no
   check notices; the generator already reads the roster for the badge and for
   the gate chart.

## Definition of done

`make validate` and `make attest` exit 0 on a clean checkout with no network
access, on every skill in the tree, with every gate's coverage statement printed
and no family, leaf or figure silently skipped. A gate that cannot check
something says so in its own output, and that statement is reproduced in this
document with its complement.
