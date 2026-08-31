# AeroSkills Eval Harness Contract (Phase 0)

Status: contract landed 2026-09-02. Harness REAL on skill 1
(avionics/do178c/planning), and the 09-04 milestone landed early 2026-08-31.
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
Sources: internal design briefs (router design; domain taxonomy;
legal/export-control compliance flags).

## Purpose

A deterministic, offline gate suite that proves a skill is shippable: agentskills.io
conformant, router-usable, legally clean, and behavior-tested. `make validate` must
exit 0 before any skill is committed as shippable.

## Commitments

- 2026-09-02: standards-map.yaml + this contract in repo. DONE.
- 2026-09-04: harness green on skill 1: all 5 gates exit 0. DONE (landed early 2026-08-31).

## Determinism rules

- No network calls. All gates run locally with stdlib or pinned preinstalled tools
  (python3, PyYAML, stdlib unittest).
- Fixed inputs (corpus, grep patterns); stable ordering (sorted finds); exit-code based.
- A gate with nothing to check reports that state and exits 0.
- No gate prints (STUB): stubs were the Phase 0 spine; all five are REAL.

## Gates

| # | Gate | Checks | Pass criteria | Status |
|---|------|--------|---------------|--------|
| 1 | Spec lint (agentskills.io conformance + compliance flags) | frontmatter, naming, description, body limits, compliance flags | every SKILL.md: name <=64 chars kebab-case matching parent dir; description <=1024 chars; compatibility <=500 chars; body <500 lines; references one level deep, relative paths only; license == Apache-2.0; compliance in {none, ITAR-GATED, EAR-GATED, STANDARDS-REF}; standards non-empty, each resolvable in standards-map.yaml; gated bool consistent with standards-map (gated standards must be reference-only or skill gated:true); metadata.version + metadata.author present. Every pack has a router SKILL.md at skills/<pack>/SKILL.md whose name equals the pack folder. Every SKILL.md carries top-level domain and pack frontmatter (pack membership, enforced by scripts/pack_inventory.py, not by this gate) | REAL |
| 2 | Description lint (what+when+trigger) | description written for the orchestrator (brief 03 section 4) | description contains action/what clause, explicit "Use when ...", 'Trigger' keyword with >=2 trigger keywords; 50-150 words | REAL |
| 3 | Per-skill pytest contract (DAL A-E determination) | skill behavior test per ARP4754A/ARP4761A | skill 1 test: failure-condition severity maps to correct DAL/FDAL/IDAL and DO-178C level; coverage depth A=MC/DC, B=decision, C=statement, D/E=none; all tests pass; stdlib-only imports | REAL |
| 4 | No-verbatim RTCA/SAE/IAQG grep | copyright control (brief 06 section 5.2) | zero verbatim-text markers AND zero objective-table blocks across skills/ and docs/ | REAL |
| 5 | Hit@1 corpus | router selection quality (brief 03 section 5) | 154/154 corpus tasks resolve to expected skill as top-1 (deterministic offline router) | REAL |

## Gate detail

### Gate 1: Spec lint (agentskills.io conformance)

Checks per SKILL.md, per the open agentskills.io specification and brief 03 section 3,
plus the compliance flags of brief 06 section 8.3.5:
- File present at skills/<path>/SKILL.md.
- YAML frontmatter parses.
- `name` required, <=64 chars, lowercase/numbers/hyphens, matches parent directory name.
- `description` required, <=1024 chars.
- `compatibility` <=500 chars when present.
- Body <500 lines (<~5K tokens).
- References one level deep from SKILL.md; relative paths only.
- `license` must equal `Apache-2.0`.
- `compliance` must be one of `none | ITAR-GATED | EAR-GATED | STANDARDS-REF`.
- `standards` non-empty list; every entry (string or `{id, reference-only}`
  mapping) must resolve against standards-map.yaml (by id or name).
- `gated` boolean consistent with the map: a standard whose map entry is
  `gated: true` must be listed `reference-only` in the skill, or the skill
  must be `gated: true`.
- `metadata.version` and `metadata.author` present.

Runner: scripts/gate-spec-lint.sh -> scripts/spec_lint.py per file.

### Gate 2: Description lint (what+when+trigger)

Checks that the description field is written for the orchestrator, not the human
(brief 03 section 4: descriptions are the router; this single field dominates selection
quality). Pass criteria:
- Contains an action/what clause (action verb: determine/draft/scope/run/...).
- Contains a when-to-use clause (explicit "Use when ...").
- Contains 'Trigger' keyword followed by >=2 trigger keywords for the skill's discipline.
- 50-150 words.

Runner: scripts/gate-desc-lint.sh -> scripts/desc_lint.py per file.

### Gate 3: Per-skill pytest contract (DAL A-E determination)

Each skill ships a behavior test that exercises the skill's core logic.
Skill 1 (avionics/do178c/planning) ships a DAL determination test per
ARP4754A/ARP4761A: given a failure-condition severity classification
(Catastrophic/Hazardous/Major/Minor/No safety effect), the test asserts the
correct DAL, FDAL/IDAL, and DO-178C software level, including coverage-depth
implications (A=MC/DC, B=decision, C=statement, D=none, E=none). Tested
logic and its test live with the skill:
skills/avionics/do178c/planning/scripts/do178c_levels.py and
scripts/test_do178c_levels.py (stdlib unittest, offline), the P2.1 rework
moved skill 1's contract in-tree so all twenty-seven skills are
self-contained (superseded the repo-root scripts/ copy); P3.5 extends the
same in-tree
contract pattern to all twenty-seven skills. Every skill ships its behavior
contract as skills/<path>/scripts/test_*.py alongside a sibling logic
module. P2.1 ships eleven more across the
certification spine: development (traceability closure per DAL), verification
(coverage depth + independence), configuration-management (baselines/change
control/release gate), systems-planning (FDAL/IDAL + planning artifacts),
hardware-planning (DO-254 AEH simple/complex classification),
safety-assessment (ARP4761A FHA/PSSA/SSA phases + analysis set), quality
(AS9100 clause scope + audit evidence + corrective-action closure),
airworthiness (FAR-25/CS-25 basis, 25.1309 applicability, means of
compliance), space software-engineering (ECSS criticality categories +
lifecycle gates + heritage reuse), systems-engineering (MBSE stages +
allocation + traceability closure), and skill-delivery (SEP-2640 package
conformance + skill URIs + server readiness). All are discovered and run
the same way.

Runner: scripts/gate-pytest-contract.sh.

### Gate 4: No-verbatim RTCA/SAE/IAQG grep (copyright control)

Scans published content (skills/ and docs/) for verbatim-text markers from
proprietary standards: RTCA/SAE/IAQG copyright boilerplate, DRM/license-restriction
lines, watermark fragments from pirated copies, and objective-table blocks
(DO-178C/DO-254 style 'Table A-1' / 'A-1.1' runs). Zero matches required. The rule
it enforces (brief 06 section 5.2): name + paraphrase + short attributed quotes
(<100 words) + links only; never reproduce objective tables, appendix text, or
multi-line verbatim blocks. Public-domain standards (FAR-25) and attribution-licensed
text (CS-25, ECSS) are quotable with citation and must not trip the gate.

Runner: scripts/gate-no-verbatim.sh (markers) + scripts/verbatim_table_scan.py (blocks).

### Gate 5: Hit@1 corpus

Fixed corpus of active tasks (eval/hit1-corpus.yaml), resolved by the
flat+tags router (brief 03 section 5 layer 2 stage 1: token overlap over
tags/name/description/body with tag boost; deterministic, offline). Pass =
top-1 == expected_skill for all tasks (66 as of the P3.5 rework: 58
domain tasks + 8 adversarial cross-pair tasks, xp1-xp8, whose wording
plausibly routes to 2+ domains and must resolve deterministically with no
collision).

Phase 0 pinned the active tasks to skill 1 (avionics/do178c/planning).
P2.1 promotes tasks for every published skill; P3.5 expands the corpus:
it now carries sixty-six active tasks across the twenty-seven skills
(domain tasks for every leaf, the t1/t2/t4 pins promoted, t3 still
pinned to manufacturing-quality/as9100/quality, plus adversarial
cross-pair tasks xp1-xp8). P3.6 (2026-08-31) updates
the expected paths to the domain-pack layout (e.g.
systems-engineering-safety/arp4754a/systems-planning) and the future pins
to pack-scheme names; the Phase-0 baseline is reconciled 5/5 in the corpus
header (4 live tasks + 1 future_pin; XFOIL NACA 0012 promoted to live
at P3.5). The brief-03 canonical queries (CubeSat battery,
weight-and-balance, XFOIL NACA 0012) are promoted to live tasks at P3.5;
engine overhaul (t3) stays a future_pin until an MRO/maintenance skill
publishes.

Runner: scripts/gate-hit1-corpus.sh -> scripts/router_eval.py.

## Wiring

Makefile target `validate` runs all five REAL gates and must exit 0:

    make validate

Makefile target `packs` lists the domain-pack inventory for per-domain
install (reads domain/pack frontmatter; deterministic, offline):

    make packs

Wired and REAL: gate 1 (spec lint), gate 2 (description lint), gate 3 (pytest
contract), gate 4 (no-verbatim), gate 5 (Hit@1 corpus).

## Definition of done

`make validate` exits 0 on a clean checkout with no network access, on skill 1
(avionics/do178c/planning) and every subsequent skill.
