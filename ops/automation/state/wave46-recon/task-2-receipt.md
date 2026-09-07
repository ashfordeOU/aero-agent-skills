# WAVE-46 AVIONICS PROBE RECEIPT (task-2, whole-family FRESH)

- Repo: the AeroSkills repo at ~/AeroSkills, git HEAD d4b4d590 (ops:
  wave-46 brief, verified via git rev-parse --short HEAD = d4b4d590).
- Scope: ENTIRE avionics family, 48 leaves, probed fresh at wave-46
  HEAD. Read-only: no git writes, no edits to skills/, eval/, docs/,
  scripts/, Makefile, standards-map.yaml, ops/automation briefs. The
  only repo write anywhere is this receipt.
- Family diff wave-45 HEAD (5cc8fef3) to wave-46 HEAD (d4b4d590),
  restricted to skills/avionics/: exactly 4 changed paths, the router
  SKILL.md update plus the landed leaf
  fsw/deadline-monotonic-scheduling (SKILL.md + logic + test). No
  ownership change for any prior decline reason.
- Repo census: 637 SKILL.md leaves on disk, all tracked at HEAD
  (git ls-files count equals find count). Corpus eval/hit1-corpus.yaml:
  1266 tasks parsed by regex; 99 target avionics leaves, 48 distinct
  avionics targets, set-identical to the 48 disk leaves (0 orphans, 0
  unserved). Every avionics leaf carries 2-3 corpus tasks.

## Verdict

1 ranked GO candidate: avionics/fsw/mixed-criticality-scheduling.
Everything else in the family declines with receipts below (heavily
saturated, as expected). Wave-45 landed deadline-monotonic-scheduling
as the fixed-priority relative-deadline sibling of real-time-scheduling;
the criticality-mode response-time analysis (two-version worst-case
execution time estimates C_LO/C_HI per task, LO-to-HI criticality mode
change, AMC-rtb bound) is the next genuinely open slot in the same fsw
response-time-analysis lineage, and it is the first seam named in the
wave-46 fresh-seam brief.

## Ranked GO candidate

### 1. avionics/fsw/mixed-criticality-scheduling (GO, rank 1)

Schedulability of an avionics flight software task set under the
two-criticality (dual-criticality) execution time model: each task
carries a low-criticality worst-case execution time estimate C_LO and a
high-criticality estimate C_HI (C_HI >= C_LO), the set is checked in
LO mode with the classic fixed-point response-time analysis over C_LO,
and in HI mode after the criticality mode change with the AMC-rtb
fixed point R_i = C_i(HI) + sum over higher-priority LO tasks of
ceil(R_i / T_j) * C_j(LO) plus sum over higher-priority HI tasks of
ceil(R_i / T_j) * C_j(HI), converged against each task's deadline.
Deterministic, offline, ceil-only fixed point, the same computation
family as real-time-scheduling, deadline-monotonic-scheduling,
shared-resource-access-control and aperiodic-server-scheduling.
DO-178C software levels A-E give the criticality semantics (the Vestal
model is DO-178B/C DAL-inspired), so do-178c is the reference-only
standards id, matching the fsw pack convention.

(a) Zero-owner grep evidence, WHOLE skills/ tree plus eval/ (fresh,
run at HEAD d4b4d590):

$ grep -rn -i -E "mixed[- ]criticality|amc-rtb|amc-max|\bvestal\b|criticality-aware|dual-criticality|hi-mode|lo-mode" skills/ eval/ --include="*.md" --include="*.yaml" | grep -v __pycache__; echo EXIT=$?
EXIT=1

$ grep -c -i -E "mixed criticality|mixed-criticality|amc-rtb|vestal" eval/hit1-corpus.yaml
0

Token scan across every skills/ SKILL.md plus eval/hit1-corpus.yaml:
mixed-criticality, overload, offset-phase, hierarchical-scheduling,
self-suspend, energy-aware and the whole display/indicator zone each
returned 0 hits anywhere (script /tmp/w46_tokscan.py). The corpus has
no task that routes on criticality-mode scheduling: the only
"criticality" corpus rows are SES/ECSS level-determination tasks
(p1 -> avionics/do178c/planning, sp1 + w17-development-assurance-levels
-> SES arp4754a leaves, ss1 -> ECSS), all level/DAL flavored, none
scheduling flavored.

(b) Nearest sibling fences (quoted, fresh):

skills/avionics/fsw/real-time-scheduling/SKILL.md lines 69-73:
"- Scope notes: WCET estimation, jitter and blocking analysis, and
  arbitrary-deadline response-time extensions are out of scope; the
  model is the classic implicit-deadline periodic task set. ARINC 653
  partition schedule windows and message bus response windows are not
  this leaf."

The wave-45 fence list (real-time-scheduling lines 190-192) routes
WCET estimation, jitter, blocking, arbitrary-deadline extensions,
ARINC 653 partition windows and bus response windows away from the
implicit-deadline leaf. None of the four scheduling leaves names a
criticality-mode or dual-execution-time model: deadline-monotonic-
scheduling stops at per-task relative deadlines and release jitter
(its line 169: "Implicit-deadline identity (D = T, J = 0): the pack
sibling's sets reproduce exactly"); shared-resource-access-control
scope note (lines 63-67) says plain feasibility belongs to
real-time-scheduling and "WCET budgets are inputs, not outputs";
aperiodic-server-scheduling intro (line 26) exists because "the
periodic-only model of the pack sibling cannot admit the event release
at all" and treats mode-change requests only as example event-driven
jobs. Criticality-mode scheduling is not claimed and not fenced by any
of the four; it is the wave-46 next sibling exactly as aperiodic-server
(wave-44) and deadline-monotonic (wave-45) were before it.

Nearest-owner fence on the level side: avionics/do178c/planning owns
DAL/software-level determination (its description trigger: "software
level determination, DAL assignment"; tags: dal, software-levels). The
new leaf must therefore stay on scheduling tokens and never claim
level-determination tokens (build-time caveat below).

(c) Standards-map id exists (grep-verified fresh):

$ grep -n "id: do-178c" standards-map.yaml
61:  - id: do-178c

do-178c is the reference-only id carried by all four fsw scheduling
siblings; the Vestal criticality model is literally DO-178B/C DAL
inspired, so the reference is the pack convention, and no DO-178C text
is reproduced.

(d) Published deterministic anchors (public science, summary-only):
- Vestal, "Preemptive Scheduling of Multi-Criticality Systems with
  Varying Degrees of Execution Time Assurance", RTSS 2007 (the
  two-version C_LO/C_HI task model).
- Baruah, Burns, Davis, "Response-Time Analysis for Mixed Criticality
  Systems", RTSS 2011 (the AMC-rtb exact bound: LO-mode analysis with
  C_LO, HI-mode analysis with the dual interference sum above).
- Burns and Davis, "Mixed Criticality Systems: A Review", 2017 update
  (model taxonomy and the AMC/AMC-max variants).
The analysis is the classic fixed point with math.ceil only, identical
in shape to the four sibling leaves' own iterations: deterministic,
offline, closed-form, no tables, no numeric integration.

(e) Two non-stealing Hit@1 corpus queries with distinctive hyphenated
tokens (proposed, for the wave-46 spec to copy verbatim; every
distinctive token below scans 0 hits in skills/ and eval/ today):
1. "run the mixed-criticality-scheduling amc-rtb-analysis on the
   flight-control task set where each task carries a dual-criticality
   execution time estimate C_LO and C_HI, and verify the
   hi-criticality-mode response time of the level-A task against its
   deadline after the criticality mode change"
2. "check the lo-criticality-mode feasibility of the two-criticality
   process set with the C_LO estimates, then recompute the
   hi-criticality-mode response times under the AMC-rtb interference
   bound when the HI tasks overrun their LO budgets"
No existing corpus task carries mixed-criticality, amc-rtb,
dual-criticality, criticality-mode or hi/lo-mode tokens (full-file
substring scan, zero hits), so there is no theft. The new tasks give
the leaf its corpus demand at build time, the wave-45
deadline-monotonic precedent (GO with zero prior corpus demand).

(f) Proposed tags, hyphenated compounds ONLY:
mixed-criticality-scheduling (first tag = leaf name),
amc-rtb-analysis, dual-criticality-execution-time,
hi-criticality-mode-rta, lo-criticality-mode-rta,
criticality-mode-change-rta. Build-time caveats (same class as the
wave-45 DM caveat): never tag or describe with the single words
criticality, dal, software-level, wcet, worst-case-execution-time
(do178c/planning owns level tokens; real-time-scheduling owns the
literal trigger phrase "worst case execution time" in its description
even though its scope fences WCET estimation out); refer to the
estimates as C_LO/C_HI execution-time estimates. At build time add one
fence line to real-time-scheduling and one router row to
skills/avionics/SKILL.md pointing criticality-mode scheduling to the
new leaf (the aperiodic-server and deadline-monotonic precedents).

## Declines table (fresh receipts, wave-46 HEAD)

| Candidate seam | Evidence | Decline reason |
|---|---|---|
| fsw EDF processor-demand / demand-bound (Baruah) | real-time-scheduling owns EDF verdicts: edf_feasible, full-utilization condition, corpus tasks w33-2 (earliest-deadline-first, cpu-utilization) | Corpus theft on earliest-deadline-first/cpu-utilization tokens; EDF feasibility math already owned by the implicit-deadline sibling |
| fsw offset/phase release RTA (Tindell offsets, phased releases) | 0 hits for release-offset/task-offset/phased-release/staggered-release across skills/ + eval/; corpus 0; wave-45 decline re-verified | No corpus demand, no hyphenated-token corpus surface, and the Audsley anchor family is now claimed inside deadline-monotonic-scheduling (audsley 6 hits there, incl. busy-window citation) |
| fsw WCET estimation leaf | real-time-scheduling description trigger owns the literal "worst case execution time" token | Token theft on the sibling's owned trigger even though estimation is fenced out of its scope; estimation is tool/analysis-method territory, not a closed-form leaf; corpus 0 |
| fsw transient overload / overload handling | 0 hits for transient-overload/permanent-overload/overload-handling anywhere; corpus 0 | No published deterministic closed-form anchor, no standards-map id tie, no corpus demand |
| fsw hierarchical / two-level (ARINC 653 style) scheduling | arinc-653 not in standards-map.yaml (only arinc-429, arinc-664, mil-std-1553 ids exist, grep-verified) | Map-blocked; ima-partitioning already owns major-frame feasibility and partition schedule arithmetic |
| fsw self-suspending / energy-aware scheduling | 0 hits both token families, corpus 0 | Research topics with no avionics certification tie, no map id, no demand |
| fsw multiprocessor / global scheduling | no map id, corpus 0 | No DO-178C-scaled single-core family anchor; out of the pack's RTA lineage |
| do178c dev-process seams (coverage, traceability, PDS, tools, MC/DC) | software-testing owns MC/DC test-case count + coverage objectives per level (rbt1/rbt2, v1 corpus tasks); verification owns structural coverage + independence; development owns requirement-to-code traceability and derived requirements; previously-developed-software owns PDS; tool-qualification owns TQL | Every process function has an owner with corpus demand; wave-45 verdict re-verified, no fresh seam |
| do178c UMS/FLS | zero user-modifiable / field-loadable tokens in skills/avionics + eval/; the only corpus ids fls1/fls2 are flight-loads-survey tasks routing to flight-test-operations/envelope/flight-loads-survey (unrelated); do178c/planning owns PSAC/SDP/planning scope | Objective-table-gated content from the standard; closed wave-44/45, no fresh counter-evidence |
| do254 hardware seams (elemental analysis, FPGA/HDL, advanced verification) | do254/verification description owns verification methods per AEH class including "review, analysis" and hardware/software integration evidence; hardware-planning owns simple-vs-complex AEH; requirements-capture and configuration-management own their domains | No unowned deterministic computation; wave-45 decline re-verified; HDL/FPGA design practice has no closed-form anchor |
| flight-management CDA / continuous-descent path | vertical-navigation owns top-of-descent distance, descent gradient, flight path angle, altitude-at-waypoint checks (description quoted in probe) | CDA geometry is the same descent-gradient trig already inside the vertical-navigation fence; corpus 0 for continuous-descent |
| flight-management path-terminator legs (IF/CF/DF/VA/VM/FA) beyond RF | radius-to-fix-leg owns RF leg + RNP AR arcs; lateral-navigation owns fly-by/fly-over, turn anticipation, intercept heading; holding-pattern-entry owns HM-style entries | ARINC 424 leg definitions have no standards-map id (map-blocked); remaining terminator legs have 0 corpus demand and sit on owned geometry tokens |
| flight-management FMS function seams (fuel prediction, alternate planning, ETA) | performance-computation owns cost index, ECON, step climb, fuel-time trade (49 token hits); rta-time-control owns arrival time control | Owned by sibling fences with corpus tasks; 0 demand for the rest |
| flight-management RNP/VNAV additions | rnp-anp-containment owns RNP/ANP containment (39 token hits); vertical-navigation owns VNAV path; radius-to-fix-leg owns RNP AR flyable arcs | All three seams owned with corpus demand |
| data-bus AFDX network-calculus worst-case latency | afdx leaf fence, lines 102-104: "Routing network timing here: AFDX jitter and latency budgets are this leaf"; its workflow already models serialization + per-switch delay latency and corpus tasks w18-arinc664-afdx-1/-2 claim jitter tolerance and end-to-end latency | Network-calculus tightening would sit inside the owned latency-budget fence; corpus demand on latency/jitter already routes to arinc664-afdx |
| data-bus ARINC 429 / 1553 additions | protocol + bus-loading leaves exist for both buses with corpus tasks (429: word format/BNR/BCD/SSM/label + loading budget; 1553: command word/RT/BC/Manchester II + minor-frame loading) | Fully owned pairs; no unowned arithmetic seam remains |
| data-bus ARINC 629 / ARINC 825 / CAN | zero hits for arinc-629/arinc-825/controller-area-network/can-bus/flexray/ttethernet/as6802 across skills/ + eval/ (exit 1) | Map-blocked: no such id in standards-map.yaml (only arinc-429, arinc-664, mil-std-1553); wave-44/45 closure re-verified |
| displays/indicators (PFD/ND/EFIS/EICAS symbology, flight director) | 0 hits for the whole token zone (attitude-indicator, efis, pfd, eicas, flight-director, symbology, glass-cockpit, head-up-display) in skills/ AND eval/hit1-corpus.yaml | Empty zone but map-blocked: no display-standard id (ARINC 661 absent) and no published deterministic closed-form anchor; far-25 instrument regulation text is qualitative. Do not open without a standards-map id |
| comms/nav receivers (VHF transceiver, receiver sensitivity) | radio-navigation-aids owns the VOR/DME/ILS receiver-side geometry (its intro: "angles that the approach receivers display against the runway centerline and the nominal glidepath... on the local tangent plane") and pairs position fixes to gnc ("with the gnc navigation leaf that owns the position fix feeding the coordinates", lines 33-34; workflow step 1: "the gnc position fix leaves provide the coordinates") | Receiver MOPS ids (VHF comm, ILS, VOR, DME, ADF families) absent from standards-map.yaml: map-blocked; receiver-level signal processing has 0 corpus demand |
| IMA extension seams (partition offset windows, ports, health) | ima-partitioning owns MAF feasibility, port latency bounds, health monitoring (45 token hits incl. arinc-653 body mentions); do297 owns architecture, module acceptance, resource budgets | arinc-653 has no standards-map id: any new IMA scheduling/port leaf is map-blocked on the reference id its content requires |
| do160 section 17/18/19/26 seams | zero claims in skills/avionics/do160 for voltage-spike, section 17/18/19/26, audio-frequency-conducted, flammability; corpus 0 | Table-gated test-condition content from the gated standard, no closed-form computation anchor; wave-44/45 closure re-verified. Note section 23 verdict logic is already claimed by lightning-protection (its description checks "the section 23 direct effects pass criteria") |
| do160 section 8 vibration seam | vibration test content owned across structures/loads/random-vibration-analysis and flight-test-operations vibration leaves; environmental-qualification is the DO-160 umbrella | Table-driven test conditions; cross-family owners exist; wave-44 closure re-verified |
| far-cs25 additions | airworthiness owns certification basis + 25.1309; special-conditions owns 25.17 scoping; quantitative severity/DAL apportionment routes to the systems-engineering-safety arp4761a family | Saturated 2-leaf pack; every quantitative seam routes cross-family to owned leaves |
| surveillance TAWS/GPWS + Mode-S/transponder | zero hits for taws/gpws/terrain-awareness/ground-proximity/egpws in skills/ + eval/ (exit 1); transponder/1090 tokens live only in ads-b-surveillance (1090ES range, owned under rtca-do-260b) and tcas-resolution-advisory (which fences: "state, not the transponder waveform, not the FMS route, not a datalink", line 38) | CLOSED, RTCA-gated: standards-map.yaml carries rtca-do-229/185/260b only; no terrain-awareness (TAWS/GPWS) MOPS id and no Mode-S transponder MOPS id (DO-181C family) exist. Wind-shear content is owned cross-family by flight-mechanics/performance/windshear-analysis. Wave-32 decline re-verified, no fresh evidence |
| surveillance 1090ES channel occupancy | adjacent to the closed Mode-S/transponder vein; no transponder MOPS id | Wave-45 decline re-verified; map-blocked |

## Closed veins (re-verified fresh at HEAD d4b4d590, receipts over lists)

- TAWS/GPWS: CLOSED. Zero token hits repo-wide, no RTCA terrain MOPS
  id in standards-map.yaml, wave-32 decline stands, no fresh evidence.
- Mode-S / transponder / 1090ES: CLOSED. tcas-resolution-advisory
  fences the transponder waveform out (line 38), ads-b owns 1090ES
  under rtca-do-260b, no Mode-S transponder MOPS id exists in the map.
- do160 sec 17/18/19/23/26: table-gated (23's verdict logic is inside
  lightning-protection's own description fence).
- ARINC 629 / ARINC 825 / CAN: map-blocked, zero hits anywhere.
- do178c UMS/FLS: objective-table-gated, zero tokens, closed wave-44.
- fsw aperiodic service, shared-resource blocking, relative-deadline
  RTA: OWNED (aperiodic-server-scheduling, shared-resource-access-
  control, deadline-monotonic-scheduling); do not reopen.
- Wind-triangle / air-data conversions / position fixing: owned
  cross-family (flight-mechanics wind-effects and performance,
  cross-cutting units, FTO position-error-calibration, gnc-autonomy
  navigation), wave-45 receipts stand, no ownership change in the
  wave-45-to-46 avionics diff.

## Method and honesty notes

- All greps and scans were read-only terminal/search_files runs at
  HEAD d4b4d590. Helper scripts live in /tmp only: /tmp/w46_avcorpus.py
  (corpus parse + avionics inventory), /tmp/w46_tokscan.py (24 token
  groups over every skills/ SKILL.md + eval/hit1-corpus.yaml),
  /tmp/w46_final.py (UMS/FLS, DAL-owner, proposed-tag collision,
  census). No repo file was modified.
- Corpus parser: 1266 of 1266 raw task rows parsed (regex on the
  two-space task indent); avionics inventory set-identical to disk,
  99 tasks over 48 distinct targets.
- Census counts: 637 SKILL.md leaves repo-wide (tracked == disk), of
  which avionics 48 across data-bus 5, do160 6, do178c 9, do254 4,
  far-cs25 2, flight-management 11, fsw 6, ima 2, surveillance 3,
  matching the brief's 48-leaf family exactly.
- The wave-46 builder kit's "625 leaves baseline" refers to the
  eval/skill-ratings.md ledger (last numbered row 625), not the 637
  SKILL.md files on disk; both numbers are reported here to avoid
  ambiguity.
- Wave-45 corpus tasks for the landed leaf exist (deadline-monotonic-
  scheduling carries 2 corpus rows), so the family corpus math
  (48 x 2 = 96 plus 3 level-A extra rows = 99) is exact.
- Mixed-criticality-scheduling is offered with the same GO profile as
  the wave-45 deadline-monotonic GO: zero prior corpus demand, real
  published deterministic anchors, standards-map id present, spec-time
  tasks supply demand, and build-time fence/row additions are required
  (real-time-scheduling fence line + avionics router row). If the
  wave-46 triage prefers no scheduling leaf this wave, the fallback is
  NO_CANDIDATES for the whole family: every other seam above declines
  with receipts regardless of the MC decision.
