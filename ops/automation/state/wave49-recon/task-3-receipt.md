# WAVE-49 AVIONICS PROBE RECEIPT (task-3, whole-family FRESH)

- Repo: the AeroSkills repo (probe working copy at ~/AeroSkills, same
  tree as the company-ops mirror). Probe HEAD: 9c2b3fe4
  ("ops: stage wave-49 brief (655 baseline, daylight gate 11:45 UTC)"),
  verified via git log --oneline -1. Working tree clean before and
  after the probe; the only untracked path is ops/automation/state/
  wave49-recon/ (this receipt + the wave-49 runner's task receipts).
- Scope: ENTIRE avionics family, 51 leaves, probed FRESH at wave-49
  HEAD. Read-only probe: no git writes, no edits to skills/, eval/,
  standards-map.yaml, scripts/, docs/, Makefile or any ops/automation
  brief. One write only: this receipt.
- Family delta since the wave-48 avionics receipt (HEAD 92d84a48,
  ops/automation/state/wave48-recon/task-1-receipt.md, read in full
  first): the single wave-48 GO avionics/fsw/cyclic-executive-scheduling
  LANDED (SKILL.md + scripts/ present on disk) with its router rows,
  its real-time-scheduling/ima fence interactions, and its 2 corpus
  tasks (w48-cyclic-executive-scheduling-1/-2). fsw is now 9 leaves,
  avionics is 51. Every wave-46/47/48 decline in the family was
  re-verified FRESH this session with new grep batteries; no landing
  changed any decline reason below.
- Census (fresh at HEAD): data-bus 5, do160 6, do178c 9, do254 4,
  far-cs25 2, flight-management 11, fsw 9, ima 2, surveillance 3 = 51
  leaves; avionics router table rows = 51 = leaves (parity).
- Corpus eval/hit1-corpus.yaml: 1326 task blocks parsed (1326/1326);
  105 avionics rows over 51 distinct avionics targets, set-identical to
  the 51 disk leaves (0 orphans, 0 unserved; every leaf carries exactly
  2 rows except the do178c level-A extras on planning/development/
  configuration-management at 3 each). Repo census: 655 leaves + 12
  routers = 667 SKILL.md; 30 standards ids in standards-map.yaml.

## Verdict

NO_CANDIDATES. The wave-49 brief names the seams that remain after the
cyclic-executive landing — rate-monotonic, priority-inversion handling,
ARINC-653 scheduling, partitioning, time/space partitioning — plus a
do254/data-bus re-check. Probed FRESH, every one is either fully OWNED
with corpus demand or map-blocked / anchor-less, and the newly landed
cyclic-executive leaf's own fences route every adjacent timing domain
to an existing owner rather than opening a slot. All wave-48 declines
stand with fresh evidence below. TAWS/GPWS/Mode-S remain CLOSED
(standing, zero tokens re-verified) and were not re-proposed.

### Seam receipts (fresh evidence at HEAD 9c2b3fe4)

| Candidate seam | Fresh evidence this session | Decline reason |
|---|---|---|
| fsw rate-monotonic scheduling (Liu-Layland bound) | real-time-scheduling description (line 3, quoted fresh): "apply the Liu-Layland utilization bound for rate-monotonic fixed-priority scheduling, run the exact iterative response-time analysis task by task"; tags rate-monotonic-scheduling, liu-layland-bound; router row line 86 + routing prose line 153; corpus task w33-real-time-scheduling-1 (intent "RM Liu-Layland utilization bound schedulability of a periodic task set") | OWNED with corpus demand; wave-48 decline re-verified fresh |
| fsw priority-inversion handling (protocol-level) | shared-resource-access-control owns the whole handling zone: description trigger list "priority ceiling protocol, priority inheritance, stack resource policy, worst case blocking, blocking time bound, schedulability with blocking" (line 3); tags priority-ceiling-protocol, priority-inheritance, stack-resource-policy (line 16); the PCP ceiling-rule at-most-once blocking model, per-resource ceiling map and RTA-with-blocking fixed point (lines 44-62); router row line 93 + routing prose line 171; corpus w38-shared-resource-access-control-1/-2 (2 rows, "priority ceiling protocol blocking bounds", "response time analysis with shared resource blocking") | OWNED; PIP/ICPP/SRP protocol variants sit inside this leaf's claimed trigger zone and would steal its tokens — same one-variant-inside-owner decline as wave-48 AMC-max; no seam |
| fsw ARINC-653 scheduling / partitioning | ima-partitioning owns ARINC 653 partition-schedule feasibility: description + tags arinc-653/partition/major-frame/maf + corpus w19-ima-partitioning-1/-2 (MAF feasibility, sampling port latency); do297 owns platform partition allocation with CPU/memory/I/O budgets, resource contention and integrity levels (description line 3, corpus w20-do297-1). Task-level scheduling INSIDE partitions is already split between the priority-driven owner (real-time-scheduling line 32: "schedules the processes and partitions inside an ARINC 653 style avionics software partition layout") and the landed time-triggered owner (cyclic-executive-scheduling lines 34-37) | Owned + map-blocked: no arinc-653 id in standards-map.yaml (30 ids re-verified; ima-partitioning compliance lines 133-134: "the ARINC 653 text is proprietary ... not yet in standards-map.yaml"; real-time-scheduling lines 218-220: "ARINC 653 is not in standards-map.yaml and is not needed"); wave-48 decline re-verified |
| fsw/ima partitioning (MAF partition-window) | ima-partitioning owns MAF sum feasibility, partition configuration table, per-partition windows, ports, health monitoring scoping (description, tags, lines 34-35 "applications run isolated from one another in partitions, each with its own memory space") | Owned with corpus demand; wave-48 decline re-verified |
| time/space partitioning (ARINC 653 partitioning-integrity concepts) | Whole-tree token scan time-partition/space-partition/temporal-partition/spatial-partition: ZERO hits in skills/ + eval/ (EXIT=1); 0 corpus rows. Deterministic anchors that exist are already owned: MAF window arithmetic (ima-partitioning), CPU/memory/I/O budget fits and integrity levels (do297 lines 51-57), robust partitioning noted as a DO-178C topic (ima-partitioning line 136) | Map-blocked + no unowned closed-form anchor: the concept substance is ARINC 653 / DO-297 standard text and neither id exists in standards-map.yaml (30 ids; no arinc-653, no do-297); zero corpus demand; any leaf would duplicate the isolation sentence already in ima-partitioning (lines 34-35) and do297 budget checks |
| do254 seams (elemental analysis, FPGA/HDL, verification ratios, hardware tool qualification) | Whole-tree scan elemental-analysis/asic/hdl/hardware-tool: ZERO relevant hits (the only "annex" matches are ARP4761A Annex L in systems-engineering-safety/markov-analysis and FAR 36 / ICAO Annex 16 in flight-test-operations — unrelated); hardware-planning owns simple-vs-complex AEH incl. its FPGA pitfall (line 54); corpus rows 351/563 (FPGA module planning, derived requirements) route to do254 hardware-planning + requirements-capture | No unowned deterministic computation; wave-48 decline re-verified fresh; family delta since wave-48 touches only fsw, do254 pack unchanged (4 leaves) |
| data-bus seams | 429 protocol + bus-loading pair and 1553 protocol + bus-loading pair and arinc664-afdx all owned with 2 corpus rows each (inventory above); ARINC 629 / ARINC 825 / TTEthernet: ZERO tree-wide hits (EXIT=1), 0 corpus rows | Fully owned pairs; other buses map-blocked (no arinc-629/825 ids; 30 ids re-verified); wave-48 decline re-verified |
| surveillance TAWS/GPWS/terrain + Mode-S/transponder | taws/gpws/egpws/terrain-awareness/ground-proximity: ZERO tree-wide hits (EXIT=1); no terrain or Mode-S MOPS id in the map (rtca-do-229/185/260b only) | CLOSED standing per wave-48 brief — re-verified zero, NOT re-proposed |
| surveillance weather-radar received-power / detection-range | airborne-weather-radar description still owns only the reflectivity/rainfall/tilt operating-point trigger; no explicit fence excluding received-power or detection-range was added (fence grep: no hits) | CONDITIONAL decline stands unchanged: a twin would route-fragment the owned weather-radar trigger; reopen only if that leaf fences received-power/detection-range out — not a GO this wave |
| fsw remaining slots (offset/phased-release RTA, WCET estimation, transient overload, hierarchical, self-suspend/energy-aware, multiprocessor) | Fresh whole-tree scan: release-offset/phased-release/staggered-release/transient-overload/overload-handling/hierarchical-scheduling/self-suspend/energy-aware: ZERO hits; the only "multiprocessor" hits are virtual-deadline-scheduling's EDF-VD "multiprocessor-form" speedup cross-check (lines 62/116/166/227), not a multiprocessor leaf; WCET estimation is explicitly fenced OUT by real-time-scheduling (lines 69-70) and shared-resource-access-control (line 64 "WCET budgets are inputs, not outputs") yet remains anchor-less measurement territory | All wave-46/47/48 declines stand: zero corpus demand, no closed-form anchor, token theft on owned triggers; wave-48 receipts re-verified |
| do178c / do160 / far-cs25 / flight-management / display-zone | No family change since wave-48 outside fsw; every process function, table-gated section and flight-management leg owned with corpus demand; display tokens zero, no display/ARINC 661 id in the 30-id map | Wave-48 declines stand unchanged |

### Closed veins (re-verified fresh at HEAD 9c2b3fe4)

- TAWS/GPWS / terrain awareness: CLOSED. Zero token hits repo-wide, no
  terrain MOPS id in standards-map.yaml. Do not reopen (standing).
- Mode-S / transponder / 1090ES channel occupancy: CLOSED. Zero token
  hits; tcas-resolution-advisory fences the transponder waveform out,
  ads-b owns 1090ES under rtca-do-260b, no transponder MOPS id. Do not
  reopen (standing).
- ARINC 629 / ARINC 825 / CAN / TTEthernet: map-blocked, zero hits.
- do160 table-gated sections, do178c UMS/FLS, display symbology zone:
  closed wave-44..48, unchanged, map id count still 30.
- fsw priority-driven scheduling slots OWNED and do not reopen:
  real-time-scheduling (RM bound, exact RTA, EDF U<=1),
  deadline-monotonic-scheduling, mixed-criticality-scheduling (AMC-rtb),
  virtual-deadline-scheduling (EDF-VD), aperiodic-server-scheduling,
  shared-resource-access-control (PCP blocking), cyclic-executive-
  scheduling (time-triggered frame table, landed wave-48). The landed
  leaf's pitfalls (cyclic-executive-scheduling lines 184-190) route
  WCET estimation, priority-driven verdicts, per-task relative deadlines
  and release jitter, ARINC 653 partition configuration tables / MAF
  windows and bus command windows to existing owners — it fences
  nothing new open.

## Standards-map check

30 ids (`grep '^  - id:' standards-map.yaml` = 30, unchanged). Absent
and therefore blocking for any candidate that would key on them:
arinc-653, arinc-629, arinc-825, do-297, terrain-awareness MOPS,
transponder/Mode-S MOPS, display/ARINC 661 MOPS. The avionics IMA and
fsw leaves key to do-178c reference-only (ima-partitioning compliance
lines 133-137 explains the ARINC-653-absent keying convention). No new
id proposed; no GO this wave.

## Method and honesty notes

- All greps, scans and inventory runs were read-only at HEAD 9c2b3fe4;
  the helper parser lived in /tmp only (/tmp/w49_avionics_inventory.py);
  no repo file modified; this receipt is the only avionics write. git
  status --porcelain shows only the untracked wave49-recon/ receipts.
- Corpus parser recovered 1326/1326 task blocks (id, query, intent,
  expected_skill); avionics inventory set-identical to disk: 105 rows
  over 51 distinct targets, 0 orphans, 0 unserved.
- Zero-theft / Hit@1 simulation was not required: with NO_CANDIDATES no
  hypothetical leaf enters the index. Corpus zone scans nevertheless
  confirm zero prior demand on the two token-empty seams (time/space
  partitioning 0 rows, data-bus-other 0 rows) and owned demand on every
  named scheduling seam (RM 1 row, blocking 2 rows, partition 3 rows,
  cyclic 2 rows).
- Boundary honesty note: "priority-inversion handling" is the seam
  whose ownership is least obvious at a glance — shared-resource-access-
  control's MODEL is the priority ceiling protocol (ceiling map,
  at-most-once blocking, RTA with blocking term) while its triggers and
  tags also claim priority-inheritance and stack-resource-policy. The
  decline stands on the description/tag/router/corpus ownership plus the
  family's variant-inside-owner precedent; a PIP-only leaf would score
  on w38-shared-resource-access-control-1 ("priority-ceiling-protocol
  worst-case blocking time") and fragment its trigger zone.
- Fallback: none needed; the family verdict is NO_CANDIDATES with every
  named seam declined above regardless of triage preference.
