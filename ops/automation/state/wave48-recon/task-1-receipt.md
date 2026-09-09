# WAVE-48 AVIONICS PROBE RECEIPT (task-1, whole-family FRESH)

- Repo: the AeroSkills repo at ~/AeroSkills. Probe HEAD: 92d84a48
  ("ops: stage wave-48 brief (planning only — daylight dispatch 10:00
  CEST)"), verified via git log --oneline -1. Working tree clean before
  and after; the only untracked paths are this receipt and the wave-48
  runner's task-0 receipt under ops/automation/state/wave48-recon/.
- Scope: ENTIRE avionics family, 50 leaves, probed FRESH at wave-48
  HEAD. Read-only probe: no git writes, no edits to skills/, eval/,
  standards-map.yaml, scripts/, docs/, Makefile, or any ops/automation
  brief. One write only: this receipt.
- Family delta since the wave-47 avionics receipt (HEAD a4ae6d1e): the
  wave-47 ranked GO avionics/fsw/virtual-deadline-scheduling LANDED
  (SKILL.md + scripts/ present on disk) with its router rows, its
  real-time-scheduling fence additions, and 2 corpus tasks. fsw is now
  8 leaves. Every wave-46/47 decline was re-verified FRESH this session
  with new grep batteries; none of the landings changed any decline
  reason below.
- Census (fresh find at HEAD): data-bus 5, do160 6, do178c 9, do254 4,
  far-cs25 2, flight-management 11, fsw 8, ima 2, surveillance 3 = 50
  leaves; avionics router table rows = 50 = leaves (parity).
- Corpus eval/hit1-corpus.yaml: 1306 task blocks parsed (1306/1306);
  103 avionics rows over 50 distinct avionics targets, set-identical to
  the 50 disk leaves (0 orphans, 0 unserved). Repo census: 645 leaves +
  12 routers = 657 SKILL.md; 30 standards ids in standards-map.yaml.

## Verdict

1 ranked GO candidate: avionics/fsw/cyclic-executive-scheduling
(time-triggered, frame-based cyclic executive design/feasibility — the
wave-48 brief's named fsw scheduling seam). Everything else in the
family declines with receipts below. Rate-monotonic scheduling is NOT a
candidate: real-time-scheduling already owns it (re-verified fresh, full
quote below). ARINC-653 partitioning is NOT a candidate: ima-partitioning
owns partition-window MAF feasibility and no arinc-653 id exists in
standards-map.yaml. The cyclic executive slot is the genuinely open
fsw scheduling paradigm: every landed fsw scheduling leaf answers
PRIORITY-DRIVEN feasibility (RM bound/RTA/EDF, deadline-monotonic,
AMC-rtb fixed priority, EDF-VD); none constructs or checks the
TABLE-DRIVEN time-triggered frame schedule of a periodic task set. Its
identity — hyperperiod = lcm(T_i), frame length f dividing every task
period, per-task frame fit C_i <= f, per-frame capacity over the
repeating frame table — is closed-form integer arithmetic (lcm/gcd/
divisibility/sums), deterministic offline, and claimed by no sibling.

### 1. avionics/fsw/cyclic-executive-scheduling (GO, rank 1)

Offline design and feasibility of a repeating cyclic executive (frame-
based, time-triggered) schedule for a periodic avionics flight-software
task set (C_i, T_i) with implicit deadlines D_i = T_i: compute the
hyperperiod H = lcm(T_i) (the major cycle over which the frame table
repeats); select an admissible frame length f that divides every task
period (releases land on frame boundaries) and is at least every task's
execution time (each job fits inside its own frame, C_i <= f); lay the
jobs into the frames of the hyperperiod; verify per-frame capacity (no
frame's total execution exceeds f); and return the frame table with a
FITS or no-admissible-frame verdict plus per-frame slack. Deterministic,
offline, closed-form integer arithmetic, constructive (it produces the
frame table, not just a verdict) — the table-driven complement to the
pack's six priority-driven feasibility leaves. DO-178C is the
reference-only standards id, the fsw pack convention; the scheduling
math is standard-independent public science (same stance real-time-
scheduling already takes on ARINC 653, its lines 218-220).

(a) Zero-owner grep evidence, WHOLE skills/ tree plus eval/ (fresh at
HEAD 92d84a48 this session):

$ grep -rn -i -E "cyclic[- ]executive|frame[- ]based[- ]schedul|hyperperiod|frame[- ]length|time[- ]triggered|master[- ]schedule|dispatch[- ]table" skills/ eval/ --include="*.md" --include="*.yaml" | grep -v __pycache__
EXIT=1  (no cyclic-executive, hyperperiod, frame-length, time-triggered,
master-schedule or dispatch-table hit anywhere)

Corpus substring scan of all 1306 tasks: cyclic-executive 0, hyperperiod
0, frame-table 0, major-cycle 0, time-triggered 0, frame-length 0 —
zero prior corpus demand and zero theft surface, the same GO profile as
the wave-45/46/47 landings. The only near-token hits in skills/ are
other contexts, none a task-level frame table: gnc-autonomy gain-
scheduling owns the tag "schedule-table" (control-gain breakpoints);
avionics/ima/ima-partitioning owns "major frame (MAF)" partition
windows; data-bus mil-std-1553-bus-loading and flight-test-operations
pcm leaves use "minor frame" for bus/telemetry schedules. The single
"cyclic" hits in the fsw pack are the words "major-frame cyclic window"
(real-time-scheduling, handing that arithmetic to ima-partitioning) and
"cyclic rate-group dispatch layout" (deadline-monotonic-scheduling and
aperiodic-server-scheduling Related-leaves prose describing the
cfs/fprime frameworks they sit beside) — none claims a frame table.

(b) Nearest sibling fences (quoted FRESH, verbatim this session). The
fixed-priority/EDF owner hands cyclic window arithmetic away to the
partition level and fences its own scope to priority-driven feasibility:

skills/avionics/fsw/real-time-scheduling/SKILL.md lines 32-35: "It
schedules the processes and partitions inside an ARINC 653 style
avionics software partition layout, pairing with
avionics/ima/ima-partitioning, which owns the major-frame cyclic window
arithmetic that surrounds this leaf's process set."

same leaf, lines 69-73 (scope notes): "WCET estimation, jitter and
blocking analysis, and arbitrary-deadline response-time extensions are
out of scope; the model is the classic implicit-deadline periodic task
set. ARINC 653 partition schedule windows and message bus response
windows are not this leaf."

same leaf, lines 189-193 (pitfall): "Routing adjacent timing domains
here: WCET estimation, jitter and blocking analysis, arbitrary-deadline
extensions, ARINC 653 partition schedule windows (ima/ima-partitioning),
and bus response windows (data-bus/mil-std-1553) are not this leaf's
classic implicit-deadline periodic model." — no line in real-time-
scheduling claims or fences a cyclic-executive frame table; the leaf
answers only RM-bound/RTA/EDF verdicts for (C, T) sets.

The partition owner's model is window durations, not task frame-fit:

skills/avionics/ima/ima-partitioning/SKILL.md lines 37-39: "A partition
configuration table assigns each partition a window duration d and a
period p inside a repeating major frame (MAF) of duration M; the MAF
must be a common multiple of every period so the cyclic schedule
repeats evenly (period divides the MAF)." Its feasibility is the sum of
d x (M / p) partition windows against the MAF plus per-window slot
checks and IPC port latencies — ARINC 653 application partitions one
level above process sets, not the (C_i, T_i) task frame table.

The fixed-priority siblings fence only their own models and name the
dispatch frameworks, not a frame-table owner:

skills/avionics/fsw/deadline-monotonic-scheduling/SKILL.md lines
225-228 (Related leaves): "avionics/fsw/cfs-architecture and
avionics/fsw/fprime-component: software bus routing and cyclic rate-
group dispatch layout."

skills/avionics/fsw/aperiodic-server-scheduling/SKILL.md lines 233-236
(Related leaves): "...the software bus routing and cyclic rate-group
dispatch layouts that these event servers sit beside."

The avionics router has no cyclic/frame-table/hyperperiod row:
$ grep -n -i -E "cyclic|hyperperiod|frame-table" skills/avionics/SKILL.md
EXIT=1 (50 router rows == 50 leaves; scheduling rows cover rate
monotonic/response time/earliest deadline first -> real-time-scheduling,
deadline-monotonic -> deadline-monotonic-scheduling, AMC -> mixed-
criticality-scheduling, EDF-VD virtual deadlines -> virtual-deadline-
scheduling; no row names a time-triggered frame table). The seam is
unrouted and unowned; build-time additions follow the wave-45/46/47
precedent (fence line in real-time-scheduling, router row, corpus
tasks).

(c) Standards-map id exists (grep-verified fresh):

$ grep -n "id: do-178c" standards-map.yaml
61:  - id: do-178c

do-178c is the reference-only id carried by all fsw scheduling
siblings; the cyclic executive math (frames, hyperperiod, frame-fit)
needs no gated standard text, exactly as real-time-scheduling states
(lines 218-220): "ARINC 653 is not in standards-map.yaml and is not
needed: the process-level scheduling theory is independent of the
partition standard text."

(d) Published deterministic anchors (public science, summary-only,
web-verifiable this session):
- Baker and Shaw, "The Cyclic Executive Model and Ada", Real-Time
  Systems 1(1):7-25, 1989: the formal frame model — periodic tasks
  released at frame boundaries, frame repetition over the hyperperiod,
  per-frame capacity, the classic closed-form constraints used above.
- Locke, "Software Architecture for Hard Real-Time Applications:
  Cyclic Executives vs. Fixed Priority Executives", Real-Time Systems
  4(1):37-53, 1992: the canonical avionics comparison of table-driven
  cyclic schedules with priority-driven executives.
- Burns and Wellings, "Real-Time Systems and Programming Languages"
  (4th ed., 2009), cyclic executive chapter: the design rules — the
  frame length must divide every task period, every task's worst-case
  execution time must fit within a frame, no frame may be
  over-subscribed, and the schedule repeats over the least common
  multiple of the periods.
Deterministic offline integer computation (lcm/gcd/divisibility and
sums), no tables, no empirical data, no numeric integration — the same
computational honesty bar as the pack's fixed-point leaves.

(e) Two wordable Hit@1 corpus queries, sim-verified this session by
replicating scripts/router_eval.py EXACTLY (hyphen-preserving token
regex, same stopword set, tag 3 / name 2 / desc 1 / body 0.5,
verbatim-phrase bonus 4, tie-break path asc) over the real 657-SKILL.md
index plus the hypothetical candidate (candidate = name, description,
7-tag set as proposed above):

1. "run the cyclic-executive-scheduling analysis on the periodic flight
   control software task set and lay out the repeating cyclic frame
   table: compute the hyperperiod as the least common multiple of the
   task periods, choose a frame length that divides every task period,
   verify each task worst-case execution time fits inside its own
   frame, and confirm every per-frame execution total stays within the
   frame length"
   HIT1 = candidate 36.0; runner-up avionics/fsw/aperiodic-server-
   scheduling 23.0; margin 13.0.
2. "design the cyclic-executive-scheduling frame table for the periodic
   avionics tasks: compute the hyperperiod as the least common multiple
   of the periods, pick the frame length dividing every period, and
   check the frame-fit feasibility of the repeating frame table frame
   by frame"
   HIT1 = candidate 22.0; runner-up avionics/ima/ima-partitioning 12.5;
   margin 9.5.

ZERO-THEFT audit over all 1306 corpus tasks with the candidate in the
index: 0 tasks reroute to the candidate, 0 tasks change top-1 at all,
0 existing tasks score within 0.01 of their own top-1 on the candidate
(fragility 0). Corpus tasks must never reuse the owned phrases "earliest
deadline first", "cpu utilization", "liu layland bound",
"rate monotonic" (real-time-scheduling), "deadline monotonic" (DMS),
"major frame"/"MAF"/"partition window" (ima-partitioning), "rate group"
(fprime-component), "minor frame schedule" (mil-std-1553-bus-loading)
or "schedule table"/"breakpoint" (gnc gain-scheduling); refer to the
repeat period as "hyperperiod" and to the artifact as the "cyclic frame
table".

(f) Proposed tags, hyphenated compounds ONLY:
cyclic-executive-scheduling (first tag = leaf name), cyclic-frame-table,
frame-length-selection, hyperperiod-design, time-triggered-frame-
schedule, frame-fit-feasibility, frame-boundary-release. Build-time
caveats: never tag or trigger with the owned tokens listed in (e);
the leaf stays on table-driven scheduling tokens and never claims the
priority-driven verdicts (RM bound, RTA, EDF U<=1, AMC-rtb, EDF-VD x
factor) owned by the six scheduling siblings.

## Declines table (fresh receipts at HEAD 92d84a48)

| Candidate seam | Fresh evidence this session | Decline reason |
|---|---|---|
| fsw rate-monotonic scheduling (Liu-Layland bound) | real-time-scheduling description (line 3): "apply the Liu-Layland utilization bound for rate-monotonic fixed-priority scheduling, run the exact iterative response-time analysis task by task"; tags rate-monotonic-scheduling, liu-layland-bound; router row line 86 + routing prose line ~152; corpus task line 4293 routes on "rate monotonic scheduling utilization bound feasibility test liu layland" | OWNED: the wave-48 brief names RM as a realistic seam only if not already owned — it is fully owned with corpus demand; no seam |
| fsw ARINC-653 partitioning / partition-window scheduling | ima-partitioning owns MAF partition schedule feasibility, window slots, port latencies, health monitoring (description + corpus tasks 2869-2870); standards-map.yaml carries NO arinc-653 id (only arinc-429/664/mil-std-1553, lines 204/215/237; 30 ids total) | Owned + map-blocked; wave-46/47 decline re-verified |
| fsw EDF processor-demand / demand-bound (single-estimate) | real-time-scheduling owns the EDF verdict (edf_feasible, "U <= 1 ... complete EDF test", lines 61-63, 94-95); router routes "earliest deadline first" to it | Wave-46/47 decline re-verified; single-estimate EDF stays with the implicit-deadline sibling |
| fsw AMC-max / further AMC bound variants | 0 hits for amc-max tree-wide (re-run this session, EXIT=1) | One-equation variant inside the landed mixed-criticality leaf's own model |
| fsw offset/phase-release RTA, WCET estimation, transient overload, hierarchical scheduling, self-suspend/energy-aware, multiprocessor scheduling | release-offset/phased-release/staggered-release 0 hits; transient-overload/overload-handling 0 hits; self-suspend/energy-aware 0 hits; the only "multiprocessor" hits are virtual-deadline-scheduling's EDF-VD "multiprocessor-form" speedup cross-check (lines 62/116/166/227), not a multiprocessor leaf | All wave-46/47 declines stand: zero corpus demand, no deterministic anchor, no map id, token theft on "worst case execution time" (real-time-scheduling trigger), Audsley family claimed inside deadline-monotonic-scheduling |
| do178c dev-process seams (coverage, traceability, PDS, tools, MC/DC, UMS/FLS) | software-testing owns MC/DC case counts; verification owns structural coverage/independence; development owns traceability; previously-developed-software owns PDS; tool-qualification owns TQL/DO-330; UMS/FLS tokens 0 (table-gated) | Every process function owned with corpus demand; wave-46/47 verdicts re-verified |
| do254 hardware seams (elemental analysis, FPGA/HDL, verification ratios, tool qualification) | hardware-planning owns simple-vs-complex AEH + PHAC; verification owns method selection, A/B 0.98 vs C/D 0.95 ratios, hw/sw integration; requirements-capture owns derived-vs-allocated; configuration-management owns change class/ECR/HCI; "hardware tool" 0 hits | No unowned deterministic computation; hardware DO-330 tool twin would steal do178c/tool-qualification tokens; wave-46/47 declines re-verified |
| data-bus ARINC-429 / MIL-STD-1553 additions | protocol + bus-loading pairs own both buses (429: word/BNR/BCD/SSM/label + word-rate budget; 1553: command word/RT/BC + minor-frame loading) with corpus tasks | Fully owned pairs; no unowned arithmetic seam |
| data-bus AFDX network calculus / frame packing | arinc664-afdx owns BAG/VL bandwidth/jitter/latency/frame transmission time; corpus claims jitter tolerance and end-to-end latency | Tightening sits inside the owned AFDX latency fence; wave-46/47 decline re-verified |
| data-bus ARINC 629 / ARINC 825 / CAN / TTEthernet | 0 hits for all (re-run this session); standards-map.yaml carries only arinc-429/664/mil-std-1553 | Map-blocked; wave-44/45/46/47 closure re-verified |
| flight-management seams (great-circle/rhumb, CDA/VNAV, holding wind, RF/terminator legs, radio horizon, position fix, ECON/RTA) | lateral-navigation, rhumb-line-leg, flight-planning, vertical-navigation, holding-pattern-entry, radius-to-fix-leg, rnp-anp-containment, performance-computation, rta-time-control, radio-navigation-aids own every seam with corpus demand; ads-b-surveillance owns 1090ES line-of-sight range cross-pack | Fully owned; wave-45/46/47 declines re-verified |
| surveillance TAWS/GPWS + Mode-S/transponder/1090ES | 0 hits for taws/gpws/egpws/terrain-awareness/ground-proximity (re-run this session, EXIT=1); map has no terrain or Mode-S MOPS id (rtca-do-229/185/260b only); tcas-resolution-advisory fences "not the transponder waveform" (line 38) | CLOSED, RTCA-gated: standing declines; per wave-48 brief do NOT re-propose |
| surveillance weather-radar received-power/detection range | 0 owner hits in avionics (re-run this session); airborne-weather-radar description owns the reflectivity/rainfall operating-point trigger and never fences detection range out | Conditional decline stands: a twin would route-fragment the owned weather-radar trigger; reopen only after airborne-weather-radar fences received-power/detection-range out explicitly |
| IMA extension seams (partition offsets, ports, health, task-in-partition scheduling) | ima-partitioning owns MAF/ports/health; do297 owns module acceptance/resource budgets; no arinc-653 id in standards-map.yaml | Map-blocked; task-level scheduling inside a partition is exactly this receipt's cyclic-executive GO (time-triggered frame table), not a new IMA leaf |
| do160 section seams | environmental-qualification is the section-mapping umbrella; section 23 inside lightning-protection; section 8 cross-family owned | Table-gated test conditions, no closed-form anchor; wave-44/45/46/47 closure re-verified |
| far-cs25 additions | airworthiness owns basis + 25.1309 + MoC; special-conditions owns 25.17; quantitative apportionment routes cross-family to SES arp4761a | Saturated 2-leaf pack; wave-46/47 decline re-verified |
| displays/indicators (PFD/ND/EFIS/EICAS/flight director/ARINC 661) | 0 hits for the whole display token zone in skills/ + eval/ (re-run this session) | Map-blocked (no display MOPS/ARINC 661 id) and no deterministic closed-form anchor; wave-46 decline re-verified |

## Closed veins (re-verified fresh at HEAD 92d84a48)

- TAWS/GPWS / terrain awareness: CLOSED. Zero token hits repo-wide, no
  RTCA terrain MOPS id in standards-map.yaml; standing decline.
- Mode-S / transponder / 1090ES channel occupancy: CLOSED.
  tcas-resolution-advisory fences the transponder waveform out,
  ads-b owns 1090ES under rtca-do-260b, no Mode-S transponder MOPS id
  in the map. Do not reopen (wave-48 brief).
- do160 table-gated sections: closed wave-44/45/46/47.
- ARINC 629 / ARINC 825 / CAN / TTEthernet: map-blocked, zero hits.
- do178c UMS/FLS: objective-table-gated, zero tokens.
- Display symbology zone (PFD/ND/EFIS/EICAS, flight director): map-
  blocked, zero hits, no anchor — closed unless a display-standard id
  enters standards-map.yaml.
- fsw priority-driven scheduling slots: OWNED and do not reopen —
  real-time-scheduling (RM bound, exact RTA, EDF U<=1),
  deadline-monotonic-scheduling (constrained/arbitrary deadline RTA,
  jitter), mixed-criticality-scheduling (AMC-rtb),
  virtual-deadline-scheduling (EDF-VD), aperiodic-server-scheduling,
  shared-resource-access-control.
- Weather-radar detection-range: conditional (see declines), not closed.

## Standards-map check

30 ids (`grep '^  - id:' standards-map.yaml` = 30). do-178c line 61
(candidate's reference-only id, pack convention). Data-bus ids present:
arinc-429 line 204, arinc-664 line 215, mil-std-1553 line 237. Absent
and therefore blocking: arinc-653, arinc-629, arinc-825, can,
DO-181/transponder MOPS, terrain-awareness MOPS, ARINC 661/display
MOPS. No new id proposed; the GO uses only the existing do-178c
reference-only convention.

## Method and honesty notes

- All greps, scans and sims were read-only terminal runs at HEAD
  92d84a48; helper scripts lived in /tmp only (/tmp/w48_sim2.py,
  /tmp/w48_alts.py); no repo file modified; this receipt is the only
  avionics write. git status --porcelain before and after shows only
  the untracked wave48-recon/ receipts.
- Corpus parser recovered 1306/1306 task blocks (id, query, intent,
  expected_skill); avionics inventory set-identical to disk: 103 rows
  over 50 distinct targets, 0 orphans, 0 unserved (every leaf carries
  exactly 2 rows; the level-A extra rows sit on do178c planning/
  development/configuration-management).
- The Hit@1 sim imported the scoring model from scripts/router_eval.py
  verbatim (STOP set, TOKEN_RE, weights 3/2/1/0.5, +4 phrase bonus,
  (-score, path-asc) sort) and ran it over the real 657-SKILL.md index
  plus one in-memory candidate; margins 13.0 and 9.5; zero-theft audit
  over all 1306 corpus tasks: 0 reroutes, 0 fragility.
- One boundary honesty note: ima-partitioning's MAF sum and the cyclic
  frame-fit check share the "repeating schedule, sum vs frame" shape at
  different abstraction levels (partition windows vs task jobs); the
  GO stands on the task-level identity — hyperperiod lcm, frame-length
  divisibility f | T_i, per-job frame fit C_i <= f, per-frame capacity
  with constructive table output — which no leaf claims, plus the
  zero-owner token evidence and the 9.5+ Hit@1 margins.
- Fallback: if wave-48 triage prefers no new fsw leaf this wave, the
  family verdict is NO_CANDIDATES — every other seam above declines
  with receipts regardless of the cyclic-executive decision.
