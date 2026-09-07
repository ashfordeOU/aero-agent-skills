# WAVE-45 AVIONICS PROBE RECEIPT (task-0, whole-family FRESH)

- Repo: the local AeroSkills repo at git HEAD 5cc8fef3 (verified via git rev-parse).
- Scope: ENTIRE avionics family, 47 leaves, probed fresh. Read-only except this receipt file.
- Corpus baseline: eval/hit1-corpus.yaml, 1238 tasks, 1022 parsed by regex in this probe; avionics task targets 47/47 set-identical to disk leaves (0 orphans, 0 unserved, verified by script /tmp/w45_orphans.py).
- Standards map: 30 ids in standards-map.yaml (grep '^  - id:' = 30), all candidate ids grep-verified below.

## Verdict

1 ranked GO candidate: avionics/fsw/deadline-monotonic-scheduling (arbitrary and constrained relative-deadline fixed-priority analysis, the RTA extension the whole fsw scheduling family explicitly fences out). It is the wave-44-style next sibling of real-time-scheduling, exactly as aperiodic-server-scheduling was. Everything else in the family declines with receipts below. Avionics at 47 remains thin but is not saturated: this one seam is genuinely open with a real published anchor, an existing standards-map id (do-178c), and no owner anywhere in the tree.

## Ranked GO candidate

### 1. avionics/fsw/deadline-monotonic-scheduling (GO, rank 1)

Fixed-priority schedulability of task sets whose per-task relative deadlines D_i are NOT the implicit D_i = T_i: deadline-monotonic priority ordering (shorter deadline, higher priority), exact iterative response-time analysis converged against each task's own deadline R_i <= D_i for constrained (D <= T) and arbitrary (D > T) deadlines, plus the optional release-jitter term in the response-time iteration. Deterministic, offline, iterative fixed point with ceil arithmetic only, the same family as the sibling leaves.

(a) Zero-owner grep evidence, WHOLE skills/ tree plus eval/:

```
$ grep -rn -i -E "deadline[- ]monotonic|constrained[- ]deadline|audsley" skills/ eval/ | grep -v __pycache__; echo EXIT=$?
EXIT=1
```

```
$ grep -rn -i -E "release[- ]jitter|activation[- ]jitter|jitter[- ]aware" skills/ eval/ | grep -v __pycache__; echo EXIT=$?
EXIT=1
```

Per-token SKILL.md counts across the whole tree (script /tmp/w45_final_evidence.py):
- deadline[- ]monotonic: 0 hits
- constrained[- ]deadline: 0 hits
- audsley: 0 hits
- release[- ]jitter: 0 hits
- activation[- ]jitter: 0 hits
- arbitrary[- ]deadline: 1 hit, ONLY in the sibling fence quoted below (real-time-scheduling says it is out of its scope, so it is a fence, not an owner).
Corpus eval/hit1-corpus.yaml token scan for deadline-monotonic, constrained-deadline, shorter-deadline, relative-deadline, release-jitter, per-task-deadline, jitter-extended: zero tasks (empty scan result). Whole-repo scan for relative deadline / deadline-based priority / priority by deadline: only ima_partitioning_logic.py line 16, which is partition window duration vs period slot inside the IMA schedule script, not task-level deadline analysis, and ima-partitioning is fenced to partition window and port latency arithmetic by its own description and by real-time-scheduling line 71.

(b) Nearest sibling fence (quoted): skills/avionics/fsw/real-time-scheduling/SKILL.md lines 69-73:

"- Scope notes: WCET estimation, jitter and blocking analysis, and
  arbitrary-deadline response-time extensions are out of scope; the
  model is the classic implicit-deadline periodic task set. ARINC 653
  partition schedule windows and message bus response windows are not
  this leaf."

and the same leaf, lines 190-192:

"- Routing adjacent timing domains here: WCET estimation, jitter and
  blocking analysis, arbitrary-deadline extensions, ARINC 653
  partition schedule windows (ima/ima-partitioning), and bus response
  windows (data-bus/mil-std-1553) are not this leaf's classic
  implicit-deadline periodic model."

Supporting sibling fences:
- shared-resource-access-control (line 27 and 40): "with implicit deadline D = T" for its task model; its scope note (line 63-64) says plain feasibility without blocking belongs to real-time-scheduling, i.e. it is PCP blocking only, no deadline extensions.
- aperiodic-server-scheduling (line 3): its server model requires "every periodic task keeps its implicit deadline and the budget completes within its period"; no D != T machinery.
- real-time-scheduling pairs with ima-partitioning only for partition window arithmetic; ima-partitioning is not a task-deadline owner.

(c) Standards-map id exists (grep-verified):

```
$ grep -n "id: do-178c" standards-map.yaml
61:  - id: do-178c
```

do-178c is the established fsw pack reference-only id (real-time-scheduling, shared-resource-access-control and aperiodic-server-scheduling all carry it reference-only).

(d) Published closed-form / deterministic computation anchor:
- Deadline-monotonic priority assignment optimality for constrained deadlines: Leung and Whitehead, "On the Complexity of Fixed-Priority Scheduling of Periodic Real-Time Tasks", Performance Evaluation 2(4), 1982.
- Response-time analysis with arbitrary (not implicit) deadlines and release jitter: Audsley, Burns, Richardson and Wellings, "Applying New Scheduling Theory to Static Priority Pre-emptive Scheduling", Software Engineering Journal, 1993 (DM ordering, R_i <= D_i convergence rules); Tindell and Clark 1994 treatment of release jitter in the fixed-point response time iteration.
- The iteration itself is the classic fixed point R_i = C_i + sum over higher priority j of ceil((R_i + J_j) / T_j) * C_j, checked against D_i, identical in shape to the sibling leaves' own fixed point, hence deterministic, offline, closed-form with ceil only, no numeric integration, no tables.
- Public science, summary-only; DO-178C text is not reproduced (gated false, reference-only), matching the fsw pack convention.

(e) 2 wordable Hit@1 corpus queries carrying distinctive hyphenated tokens that route to this leaf without stealing existing corpus tasks (existing tasks w33-1/w33-2 carry rate-monotonic-scheduling, liu-layland, earliest-deadline-first, cpu-utilization, and route to real-time-scheduling; w44 aperiodic tasks carry sporadic-server/deferrable-server tokens; none carry deadline-monotonic or constrained-deadline or release-jitter, so no theft):
1. "check the deadline-monotonic-scheduling feasibility of the avionics process set where the 40 ms task carries a constrained-deadline of 25 ms shorter than its period: order the priorities by the shorter deadline and run the fixed-priority response-time iteration against each per-task deadline"
2. "test the arbitrary-deadline response time of the process whose 60 ms relative deadline exceeds its 30 ms period under deadline-monotonic priority assignment, then recompute the worst-case response with a 4 ms release-jitter on the highest priority task"

(f) No generic single-word tag overlap: proposed tags are hyphenated compounds only, deadline-monotonic-scheduling, constrained-deadline-rta, arbitrary-deadline-rta, release-jitter-rta, dm-priority-assignment, shorter-deadline-order. The wave-44 spec caveat applies unchanged: prune generic schedulability/fixed-priority/response-time-analysis single tags, since real-time-scheduling already owns response-time-analysis, liu-layland-bound, earliest-deadline-first, cpu-utilization, fixed-priority-scheduling; and add a fence line to real-time-scheduling at build time (aperiodic-server-scheduling precedent).

Family spread note: this keeps avionics at 47 -> 48 after landing, matching the wave-44 pattern where avionics contributed exactly one leaf.

## Declines table

| Candidate seam | One-line reason |
|---|---|
| fsw EDF processor-demand / demand-bound criterion (Baruah) | EDF side collides with real-time-scheduling corpus tasks w33-2 (earliest-deadline-first + cpu-utilization tokens) and with the rank-1 GO tag space; wave convention is one scheduling leaf per wave |
| fsw offset-based / phased release RTA | 0 corpus demand, no hyphenated-token corpus surface, audsley offsets not demanded anywhere in eval corpus |
| flight-management wind triangle / wind-corrected track | Cross-family owned: flight-mechanics/performance/wind-effects claims headwind, crosswind, wind correction angle, crab angle, groundspeed (corpus tasks we1, we2) |
| flight-management great-circle destination / forward geodesic waypoint | flight-planning and lateral-navigation jointly own the great-circle leg seam (fp1, w25 tasks); corpus 0 demand for forward-geodesic, theft risk on shared waypoint/great-circle tokens |
| flight-management position fix (DME/DME, VOR/DME) | radio-navigation-aids fence routes position fixing to gnc position fix leaves (its line 34 and 68); gnc-autonomy owns pseudorange and bearing-only localization corpus tasks |
| data-bus ARINC 429 / 1553 / AFDX additions | All protocol and loading leaves exist (429, 429-bus-loading, 1553, 1553-bus-loading, afdx); ARINC 629/825/CAN remain standards-map-blocked (wave-44 closure, no new id added) |
| do160 section 17 voltage spike + section 8 vibration | Wave-44 closure stood: table-driven test condition content, no closed-form computation anchor |
| do160 section 18/19/23/26 style test setup seams | Table-gated test conditions (audio susceptibility, induced signal, flammability), no deterministic closed-form computation, do-160 content gated |
| do178c UMS/FLS objective-table-gated seams | Wave-44 closure: objective tables from the standard, table-gated, no closed-form anchor |
| do178c MC/DC or coverage-objective counting | software-testing owns mc-dc test-case-count, coverage-objectives per level and requirements-based test case generation (rbt1/rbt2, v1 corpus tasks) |
| do254 elemental-analysis / verification-method seams | do254 verification owns verification methods per AEH class; hardware-planning owns simple vs complex AEH; no unowned deterministic computation |
| surveillance TAWS/GPWS + Mode-S + transponder | Closed baseline, RTCA-gated, no standards-map id (rtca-do-229/185/260b are GPS/TCAS/ADS-B MOPS, none covers TAWS or Mode-S); no fresh evidence, do not reopen |
| surveillance 1090ES channel occupancy / transponder reply-rate budget | Adjacent to the closed Mode-S/transponder vein, no standards-map id for transponder MOPS, 0 corpus demand |
| ima partition window / port latency / health monitor seams | ima-partitioning owns MAF feasibility, port latency bounds and health monitoring; do297 owns resource budget and module acceptance; ARINC 653 not in standards-map.yaml |
| far-cs25 deterministic seams | airworthiness and special-conditions leaves cover certification basis, 25.1309 and 25.17 scoping; quantitative 25.1309 apportionment routes to systems-engineering-safety arp4761a family (owned) |
| air-data computation (Mach/CAS/TAS/density altitude) | Cross-cutting units-atmos isa-atmosphere, airspeed-conversion, density-altitude plus FTO position-error-calibration own the conversion family (isa1/isa2, uc1/uc2 corpus tasks); cross-cutting family is default CLOSED for this wave |

## Closed veins list

- TAWS/GPWS: CLOSED (RTCA-gated, no standards-map id; wave-32 decline re-verified, no fresh evidence)
- Mode-S / transponder / 1090ES channel-loading: CLOSED (same RTCA-gated reason)
- do160 sec-17 voltage spike and sec-8 vibration: CLOSED wave-44
- ARINC 629 / ARINC 825 / CAN data-bus seams: map-blocked (no standards-map ids)
- do178c UMS/FLS objective-table seams: CLOSED wave-44
- fsw aperiodic/event-job service: OWNED as of wave-44 (aperiodic-server-scheduling); do not reopen
- wind-triangle math: cross-family owned (flight-mechanics/performance/wind-effects)
- great-circle flight-planning and LNAV leg geometry: OWNED (flight-planning, lateral-navigation, radius-to-fix-leg, dme-arc-leg, rhumb-line-leg, holding-pattern-entry)
- position fixing: routes to gnc-autonomy navigation (radio-navigation-aids fence, quoted)

## Method note

All greps and scans above were read-only terminal/search_files runs. Helper scripts written to /tmp (w45_avtasks.py, w45_corpustok.py, w45_tokengroups.py, w45_greptok.py, w45_orphans.py, w45_final_evidence.py). No repo file was modified. Corpus parser counted 1022 of 1238 tasks (multiline-query tasks fall outside the regex window); the avionics inventory it did parse is set-identical to disk, and all token-demand scans used raw substring search on the full file text so the count gap does not affect the conclusions.
