# Library expansion pipeline (P3.4 REWORK track 2, target P3.5)

Status: plan 2026-08-31, Ops Manager (Feasibility lens). Founder brief:
"the library is too small. the goal should be to keep expanding it."

## Goal and numbers

Current: twenty-seven verified skills, all gated by make validate (5/5 REAL:
spec lint, description lint, per-skill pytest contract, no-verbatim, Hit@1
corpus). Gate 3 runs twenty-seven contract tests; gate 5 runs sixty-six
corpus tasks (fifty-eight domain tasks plus eight adversarial cross-pair).

Target: twenty-five-plus skills by P3.5, met at P3.5. Floor is waves 1+2
below (twelve prior plus fifteen new = twenty-seven); wave 3 is stretch
(thirty-three). Every new skill ships the same contract as the existing
twenty-seven skills: SKILL.md,
behavior logic + stdlib unittest, Hit@1 corpus tasks, standards-map
resolvable frontmatter, and a green make validate on the commit.

Sources for candidates: standards-map.yaml (fourteen mapped standards),
research/briefs/05-domain-taxonomy.md section 5 (P0/P1/P2 candidates per
discipline), eval/hit1-corpus.yaml future_pins (t1-t4), and the founder
brief list (DO-178C/DO-254/ARP/ECSS/FAR/CS-25 sub-skills, XFOIL/airfoil,
GNC, astrodynamics/Orekit, structures, materials, systems engineering,
safety, quality).

## Wave 1 - pinned and founder-named, low tool dependency (eight)

| Candidate | Taxonomy ref | Corpus pin | standards-map deps | Behavior contract (gate 3) | Feasibility |
|---|---|---|---|---|---|
| aerodynamics/airfoil/xfoil-analysis | 5.1 P0 | t4 (live) | none (V&V practice) | polar sanity band: cl 0.82 +- 0.05 at 10 deg, Cd0 0.0079 +- 0.001 at Re 6M | high; XFOIL freeware (MIT Drela), CLI-scriptable; contract is pure Python |
| gnc-autonomy/space/orbit-dynamics | 5.5 P0 | none | none (ECSS/CCSDS optional) | Hohmann delta-v, vis-viva, J2 drift bands | high; poliastro MIT, Orekit Apache-2.0 |
| gnc-autonomy/control/python-control-design | 5.5 P0 | none | none | PID gain, gain/phase margin checks | high; python-control BSD-3 |
| gnc-autonomy/optimal-control/dymos-trajectory | 5.5 P0 | none | none | problem setup and convergence checks | high; dymos Apache-2.0 |
| structures/fem/calculix-linear | 5.3 P0 | none | none | margin-of-safety sign convention, unit discipline | high; CalculiX GPL-2 |
| structures/materials/mmpsd-allowables | 5.3 P0 | none | mmpsd (new) | A/B-basis statistics, K-factor checks | high; MMPDS proprietary-sold, reference-only (gated) |
| space-systems/subsystems/power-thermal-budget | 5.8 P2 (promote) | t1 (live) | ecss (existing) | EPS sizing bands, eclipse duration | high |
| vehicle-design/sizing/weight-estimation | 5.9 P1 | t2 (live) | none | class-I weight-fraction bands, CG envelope | high |

## Wave 2 - standards sub-skills, certification spine depth (seven)

| Candidate | Taxonomy ref | Corpus pin | standards-map deps | Behavior contract (gate 3) | Feasibility |
|---|---|---|---|---|---|
| systems-engineering-safety/arp4761a/fta-fmea | 5.7 P1 | none | arp4761a (existing) | analysis-set selection, cut-set sanity | high |
| systems-engineering-safety/arp4754a/requirements-traceability | 5.7 P0 | none | arp4754a (existing) | closure matrix check (SRATS to HLR to LLR to code to tests) | high |
| avionics/do178c/tool-qualification | 5.6 P1 | none | do-330 (new) | TQL criteria per tool category | high |
| avionics/do160/environmental-qualification | 5.6 P1 | none | do-160 (new) | test-matrix selection per equipment class | high |
| avionics/do254/verification | 5.6 P1 | none | do-254 (existing) | verification methods per AEH class | high |
| space-systems/ecss/systems-engineering | 5.7/5.8 | none | ecss (existing) | lifecycle gate mapping (E-ST-10C) | high |
| manufacturing-quality/as9102/first-article-inspection | 5.10 P0 | none | as9102 (new) | FAI completeness gate, delta-FAI triggers | high |

## Wave 3 - breadth, P1/P2 (six, stretch)

| Candidate | Taxonomy ref | Corpus pin | standards-map deps | Behavior contract (gate 3) | Feasibility |
|---|---|---|---|---|---|
| propulsion/cycle/gas-turbine-turbofan | 5.2 P0 | none | far-33 (new), cs-e (new) | on-design cycle sanity checks | medium; NPSS/GSP licensing, PyCycle open |
| propulsion/thermo/cea-rocket-combustion | 5.2 P0 | none | none | Isp and C* sanity bands | medium; NASA CEA open Fortran |
| flight-mechanics/perf/mission-sizing | 5.4 P0 | none | none | Breguet range/payload bands | high |
| aerodynamics/cfd/openfoam-run | 5.1 P0 | none | none | residual and convergence checks | medium; OpenFOAM GPL, heavy binary |
| cross-cutting/units/isa-atmosphere | 5.12 P0 | none | none | ISA table checks (rho 1.225 kg/m3 at sea level) | high |
| avionics/far-cs25/structures | 5.3 compliance | none | far-25, cs-25 (existing) | load-path and margin checks, 25.571 damage tolerance | high |

## Standards-map extension (required by gate 1)

Gate 1 resolves every skill frontmatter standard against
standards-map.yaml; a skill citing an unmapped standard fails lint. Map
extension is part of each skill build, not a separate step. Proposed
entries (family/status/gated are proposals to verify at authoring time):

| id | Name | Family | Publisher | Status | gated |
|---|---|---|---|---|---|
| do-330 | DO-330: Software Tool Qualification Considerations | guidance | RTCA | proprietary-sold | true |
| do-160 | DO-160G: Environmental Conditions and Test Procedures | guidance | RTCA | proprietary-sold | true |
| do-297 | DO-297: Integrated Modular Avionics Guidance | guidance | RTCA | proprietary-sold | true |
| as9102 | AS9102: Aerospace First Article Inspection | quality | IAQG/SAE | proprietary-sold | true |
| as9103 | AS9103: Variation Management of Key Characteristics | quality | IAQG/SAE | proprietary-sold | true |
| mmpsd | MMPDS: Metallic Materials Properties Development and Standardization | materials | SAE | proprietary-sold | true |
| cmh-17 | CMH-17: Composite Materials Handbook | materials | SAE | proprietary-sold | true |
| far-33 | 14 CFR Part 33: Airworthiness Standards for Aircraft Engines | regulation | FAA | public-domain | false |
| cs-e | CS-E: Certification Specifications for Engines | regulation | EASA | free-download | false |
| mil-std-810 | MIL-STD-810H: Environmental Engineering Considerations | test | US DoD | public-domain | false |

Gated standards never appear verbatim anywhere in the repo (gate 4 scans
skills/ and docs/); keep name + paraphrase + short attributed quotes +
link, matching the existing DO-178C/ARP treatment.

## Build path per skill

1. standards-map: add or extend standards-map.yaml entries the skill cites
   (family, publisher, status, gated, summary_not_copy); gate 1 resolves
   against this file.
2. Author SKILL.md at skills/<domain>/<sub>/<name>/SKILL.md per the
   agentskills.io spec and harness-contract gate 1/2: frontmatter name
   equal to the parent dir, description 50-150 words with an action
   clause, explicit "Use when", and a Trigger list with two or more
   discipline keywords; compliance flag set; gated standards listed
   reference-only.
3. Behavior contract: write skills/<path>/scripts/<logic>.py and
   test_<name>.py (stdlib unittest only, offline). Gate 3 discovers
   test_*.py automatically and check_stdlib_imports.py enforces
   stdlib-only. Every skill's contract is a deterministic check the model
   can run, mirroring the twenty-seven existing skills.
4. Corpus: add two Hit@1 tasks to eval/hit1-corpus.yaml for the new skill
   and promote future_pins t1/t2/t4 to live tasks when their skills
   publish (t3 stays pinned to manufacturing-quality/as9100/quality). Re-run
   scripts/router_eval.py to confirm deterministic top-1 with no
   collision; add an adversarial cross-pair task when a new pair is
   plausible.
5. Gates: make validate (5/5) and make attest (3/3) exit 0 on the commit;
   bash ops/automation/test/run-tests.sh exits 0 after any automation
   change.
6. Evidence: make snapshot-live before commit (fresh state snapshot is
   part of each complete commit, per Makefile and AGENTS.md).
7. Commit: complete commit on main (skill + map + corpus + evidence),
   Signed-off-by, clean at rest.

Definition of done per skill: SKILL.md conformant (gate 1) and
description-linted (gate 2), behavior test passing (gate 3), no-verbatim
clean (gate 4), corpus resolves (gate 5), committed with evidence.

## Gate count projections at the floor (twenty-seven skills)

- Gate 3: twenty-seven contract tests (all twenty-seven skills).
- Gate 5: sixty-six corpus tasks (fifty-eight domain tasks plus eight
  adversarial cross-pair tasks); t3 remains pinned to
  manufacturing-quality/as9100/quality. All must resolve top-1 with no
  collision; the deterministic offline router makes this replayable.
- make validate stays 5/5; run-tests.sh G6 re-lints the full skills tree.

## Feasibility and security notes (Ops lens)

- Every candidate contract is pure-Python stdlib, matching the existing
  pattern: no new eval-gate dependencies, deterministic, offline.
- Tool-dependent skills (XFOIL, AVL, OpenFOAM, CalculiX, CEA, dymos,
  poliastro, Orekit) document tools as references with license notes;
  never bundle binaries; no network at eval time.
- New gated standards (DO-330, DO-160, AS9102, MMPDS, CMH-17, AS9103)
  follow the summary-not-copy rule; gate 4 enforces it across skills/ and
  docs/.
- Content policy: publishable content must avoid certification-claim
  phrasing and part-number patterns; the sweep covers skills/, docs/,
  development/builds/, marketing/, README.md. Skills are methodology text
  only; no ITAR/EAR-controlled data.
- Number hygiene: brief-audit scans development/ and docs/; counts in this
  plan are spelled out and no new market numbers are introduced, so the
  audit stays clean. The attestation register is unchanged.
- Ordering: waves 1+2 first (floor twenty-seven); wave 3 is stretch. Each
  wave ends gate-green and committed; the library grows monotonically.
