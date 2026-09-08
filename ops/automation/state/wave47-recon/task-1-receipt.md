# WAVE-47 AVIONICS PROBE RECEIPT (task-1, whole-family FRESH)

- Repo: the AeroSkills repo at ~/AeroSkills. Probe HEAD: a4ae6d1e
  ("Wave-47: close-out must auto-update products-state (FIX)"),
  verified via git rev-parse. The briefed hash a544f421 is the wave-47
  brief commit itself; HEAD is a544f421 plus one ops close-out FIX, and
  `git diff --name-only a544f421 HEAD` touches only
  ops/automation/wave47-brief.md — no skills/ path, so the family is
  identical at both hashes and this probe is valid for the briefed
  baseline.
- Scope: ENTIRE avionics family, 49 leaves, probed FRESH at wave-47
  HEAD. Read-only: no git writes, no edits to skills/, eval/, docs/,
  scripts/, Makefile, standards-map.yaml, or ops/automation briefs.
  The only repo write is this receipt.
- Family delta since the wave-46 avionics receipt (HEAD d4b4d590):
  exactly 4 paths under skills/avionics/ — the router SKILL.md plus the
  landed leaf fsw/mixed-criticality-scheduling (SKILL.md + logic +
  contract test). Nothing else changed; wave-46 declines on unchanged
  packs stand and are re-cited below. Fresh probe work concentrated on
  the seams the landing created (fsw dual-criticality scheduling
  lineage) plus fresh whole-family token batteries across all nine
  packs.
- Repo census: 647 SKILL.md tracked == 647 on disk (635 leaves + 12
  routers per the wave-47 brief ledger). Corpus eval/hit1-corpus.yaml:
  1286 expected_skill rows parsed; 101 avionics rows over 49 distinct
  avionics targets, set-identical to the 49 disk leaves (0 orphans, 0
  unserved). Pack counts (fresh find): data-bus 5, do160 6, do178c 9,
  do254 4, far-cs25 2, flight-management 11, fsw 7, ima 2,
  surveillance 3 = 49.

## Verdict

1 ranked GO candidate: avionics/fsw/virtual-deadline-scheduling
(EDF-VD dual-criticality schedulability). Everything else in the family
declines with receipts below. Wave-46 landed mixed-criticality-scheduling
(the AMC-rtb fixed-point analysis over the Vestal C_LO/C_HI model) as the
fixed-priority branch of the dual-criticality scheduling lineage. Its own
model fence ("the task list IS the fixed-priority order") leaves the EDF
branch of the SAME dual-criticality model unowned: real-time-scheduling
owns EDF feasibility only for the single-execution-time implicit-deadline
set, and the router sends criticality questions only to the AMC leaf.
EDF-VD (earliest-deadline-first with virtual deadlines, Baruah et al.) is
the canonical published algorithm for that unowned corner: HI tasks
receive a shortened virtual deadline x*T and the set is checked in both
modes. It is the next sibling of the wave-46 landing exactly as
deadline-monotonic (wave-45) and mixed-criticality (wave-46) were before
it. TAWS/GPWS and Mode-S remain CLOSED (re-verified below).

### 1. avionics/fsw/virtual-deadline-scheduling (GO, rank 1)

Offline schedulability of an avionics flight-software task set under the
dual-criticality (two-criticality) execution-time model scheduled by
EDF-VD: each task carries a LO estimate C_LO and a HI estimate C_HI
(C_HI >= C_LO) with implicit deadline T; every HI task is assigned the
virtual deadline x*T for a common factor 0 < x <= 1; LO mode is the plain
EDF schedule over all jobs (feasible when the LO-mode demand fits,
equivalently U_LO <= 1 for implicit deadlines); after the
criticality-mode change the scheduler keeps only HI jobs at their real
deadlines; the set is feasible when a virtual-deadline factor x exists
under which both the LO-mode and HI-mode demand conditions hold.
Deterministic, offline, closed-form (virtual-deadline scaling plus
per-mode demand/utilization conditions, math only), the EDF sister of the
landed AMC-rtb leaf. DO-178C software levels A-E supply the criticality
semantics reference-only (never determined), the fsw pack convention.

(a) Zero-owner grep evidence, WHOLE skills/ tree plus eval/ (fresh, run
at HEAD a4ae6d1e this session):

$ grep -rn -i -E "edf-vd|virtual[- ]deadline" skills/ eval/ --include="*.md" --include="*.yaml" | grep -v __pycache__; echo EXIT=$?
EXIT=1

$ grep -rn -i -E "amc-max|amc max|adaptive[- ]mixed[- ]criticality" skills/ eval/ --include="*.md" --include="*.yaml" | grep -v __pycache__; echo EXIT=$?
EXIT=1

The only bare-word "virtual" hits in the whole tree are GD&T "virtual
condition" (cross-cutting/tolerancing/position-tolerance-calc) and AFDX
"virtual link" tokens — unrelated; "virtual deadline" never appears
anywhere. eval/hit1-corpus.yaml carries no edf-vd, virtual-deadline or
dual-criticality-EDF task (zero-hit substring scan over all 1286 rows),
so there is no theft and no prior corpus demand — the same GO profile as
the wave-45 deadline-monotonic and wave-46 mixed-criticality landings,
whose corpus demand was supplied at build time.

(b) Nearest sibling fences (quoted, fresh). The dual-criticality vein
owner that LANDED in wave-46 fences itself to fixed-priority:

skills/avionics/fsw/mixed-criticality-scheduling/SKILL.md lines 43-45:
"Priority order: the task list IS the fixed-priority order, index 0 the
highest priority, deadlines non-decreasing (deadline-monotonic order)."

and line 180 (Related leaves): "this leaf stays on the implicit-deadline
(D = T) sets." Its pitfall (lines 209-212) sends single-estimate sets to
real-time-scheduling. Nothing in the landed leaf claims the EDF branch of
the dual-criticality model.

The single-estimate EDF owner fences itself to the implicit-deadline
one-estimate model, and its EDF verdict is defined only there:

skills/avionics/fsw/real-time-scheduling/SKILL.md lines 61-62: "EDF
feasibility (implicit deadlines): U <= 1 is necessary and sufficient,
because EDF is optimal among all scheduling algorithms on a single
processor." Scope notes (lines 69-73): "WCET estimation, jitter and
blocking analysis, and arbitrary-deadline response-time extensions are
out of scope; the model is the classic implicit-deadline periodic task
set. ARINC 653 partition schedule windows and message bus response
windows are not this leaf."

The family router (skills/avionics/SKILL.md line 172) routes
"single-execution-time implicit-deadline feasibility" to real-time-
scheduling and criticality-mode questions to mixed-criticality-scheduling
only; line 151 routes plain EDF feasibility ("earliest deadline first")
to real-time-scheduling. No leaf and no router row claims a
dual-criticality EDF / virtual-deadline analysis; the seam is unrouted
and unowned. Build-time additions required (wave-45/46 precedent): one
scope fence line in real-time-scheduling, one related-leaf line in
mixed-criticality-scheduling, plus one avionics router row pointing
dual-criticality EDF questions to the new leaf.

(c) Standards-map id exists (grep-verified fresh):

$ grep -n "id: do-178c" standards-map.yaml
61:  - id: do-178c

do-178c is the reference-only id carried by all six fsw scheduling
siblings; the Vestal/EDF-VD criticality models are DO-178B/C DAL
inspired, so the reference is pack convention and no DO-178C text is
reproduced. Level determination stays with do178c/planning (its
description owns "determine the software level or DAL (A-E) from
failure-condition severity"; MC leaf pitfall lines 206-208 say the same).

(d) Published deterministic anchors (public science, web-verified this
session):
- Baruah, Bonifaci, D'Angelo, Li, Marchetti-Spaccamela, Megow, Stougie,
  "Scheduling Real-Time Mixed-Criticality Jobs", IEEE Transactions on
  Computers 61(8):1140-1152, 2012: the EDF-VD algorithm, virtual-deadline
  assignment x*T for HI tasks, the dual-mode schedule, and the
  speedup-factor / utilization-bound analyses (Semantic Scholar/ACM
  records confirm EDF-VD with "metrics such as processor speedup factor
  and utilization bounds"; the 4/3 processor-speedup factor for the
  dual-criticality case is the textbook magnitude).
- Ekberg and Yi, "Bounding and shaping the demand of generalized
  mixed-criticality sporadic task systems", Real-Time Systems 50(1):
  48-86, 2014 (journal of the RTSS 2012 paper): the exact demand-bound
  schedulability test for generalized dual-criticality EDF-VD, the
  deterministic offline test the leaf implements in the general case.
- Burns and Davis, "Mixed Criticality Systems: A Review" (2016/2017):
  the EDF-VD model summary used as the leaf's domain reference.
Magnitudes are verifiable against the published worked analyses; same
computation family (ceil/floor-free demand conditions and fixed points)
as the pack's other schedulability leaves.

(e) Two non-stealing Hit@1 corpus queries with distinctive hyphenated
tokens (proposed, for the spec to copy verbatim; every distinctive token
scans 0 hits in skills/ and eval/ today):
1. "run the edf-vd virtual-deadline-scheduling analysis on the
   dual-criticality flight-control task set with C_LO and C_HI execution
   time estimates: assign each HI task its virtual deadline factor x and
   verify the lo-criticality-mode and hi-criticality-mode feasibility of
   the set after the criticality mode change"
2. "check the virtual-deadline-factor schedulability of the
   two-criticality process set under edf-vd: compute the per-task
   virtual deadlines x*T for the HI tasks and confirm both the LO-mode
   and the HI-mode demand conditions hold for the chosen factor"
No existing corpus task carries edf-vd or virtual-deadline tokens
(zero-hit substring scan), so there is no theft; the new tasks give the
leaf its corpus demand at build time. Corpus tasks must never reuse the
real-time-scheduling owned phrases "earliest deadline first", "cpu
utilization" or "worst case execution time".

(f) Proposed tags, hyphenated compounds ONLY:
virtual-deadline-scheduling (first tag = leaf name), edf-vd-analysis,
virtual-deadline-factor, hi-criticality-mode-edf, lo-criticality-mode-edf,
dual-mode-demand-check. Build-time caveats (same class as the wave-46 MC
caveats): never tag, trigger or describe with the owned phrases "earliest
deadline first", "cpu utilization" or "worst case execution time"
(real-time-scheduling owns all three in its description and tags); never
claim the single-estimate full-utilization EDF verdict (that is
real-time-scheduling's edf_feasible); refer to the algorithm as edf-vd /
virtual-deadline scheduling throughout, and to the estimates as C_LO/C_HI
execution-time estimates. If wave-47 triage reads the wave-46 plain-EDF
decline (processor-demand in the SINGLE-estimate model) as covering the
dual-criticality EDF algorithm too, the fallback for this family is
NO_CANDIDATES: every other seam below declines with receipts regardless
of the EDF-VD decision.

## Declines table (fresh receipts at wave-47 HEAD a4ae6d1e)

| Candidate seam | Evidence | Decline reason |
|---|---|---|
| fsw AMC-max / further AMC bound variants | 0 hits for amc-max/adaptive-mixed-criticality tree-wide (EXIT=1, re-run this session) | AMC-max is a one-equation variant inside the landed leaf's own model, not a distinct deterministic workload; would duplicate the wave-46 leaf |
| fsw EDF processor-demand / demand-bound (single-estimate) | real-time-scheduling owns the EDF verdict: "edf_feasible(tasks) reports whether U <= 1, which for implicit-deadline sets is a complete EDF test" (lines 94-95); corpus task owns "earliest deadline first cpu utilization" wording; router line 151 | Wave-46 decline re-verified; single-estimate EDF feasibility math stays with the implicit-deadline sibling |
| fsw offset/phase-release RTA, WCET estimation, transient overload, hierarchical/ARINC-653-style, self-suspend/energy-aware, multiprocessor scheduling | Re-run zero-hit batteries this session: release-offset/phased-release/staggered-release/task-offset 0; transient-overload/overload-handling 0; self-suspend/energy-aware 0; hierarchical-scheduling 0; WCET trigger phrase owned by real-time-scheduling description; arinc-653 has 0 hits in standards-map.yaml | All wave-46 declines stand; the only fsw change since is the MC landing, which alters none of these reasons |
| do178c dev-process seams (coverage, traceability, PDS, tools, MC/DC, UMS/FLS) | software-testing owns MC/DC case counts; verification owns structural coverage and independence; development owns traceability; previously-developed-software owns PDS; tool-qualification owns TQL-1..5 ("tool qualification, DO-330, TQL, tool criteria, qualification level" in description, re-read this session); planning owns PSAC/levels | Every do178c process function has an owner with corpus demand; wave-46 verdict re-verified, no fresh seam |
| do254 hardware tool qualification (DO-330 for hardware tools) | 0 hits for "hardware tool" tree-wide (re-run this session); do178c/tool-qualification owns the generic TQL/DO-330/tool-criteria triggers and is the router's tool-qualification row | Adjacent-token theft: a hardware-tool twin must trigger on the same owned tokens, and the software leaf does not fence hardware tools out with distinct wording; no textbook/paper equations (DO-330 criteria table). Do not open without the software leaf fencing hardware tools out first |
| do254 hardware seams (elemental analysis, FPGA/HDL practice, AEH level assignment, verification ratios) | hardware-planning owns simple-vs-complex AEH and PHAC ("Complex AEH (programmable logic, processors...) follows the full design assurance process", re-read this session); verification owns method selection and the A/B 0.98 vs C/D 0.95 ratios; requirements-capture owns derived-vs-allocated | No unowned deterministic computation; AEH level (A-D) derives from system safety assessment (cross-family SES arp4754a/arp4761a ownership); wave-46 decline re-verified |
| data-bus ARINC 429 / MIL-STD-1553 additions | protocol + bus-loading leaves exist for both buses with corpus tasks (429: word/BNR/BCD/SSM + word-rate budget; 1553: command word/RT/BC + minor-frame loading) | Fully owned pairs; no unowned arithmetic seam remains |
| data-bus AFDX additions (network calculus, frame packing, dimensioning) | afdx leaf owns BAG selection, VL bandwidth, link budget, jitter, latency, frame transmission time; corpus tasks claim jitter tolerance and end-to-end latency | Network-calculus/frame-packing tightening sits inside the owned AFDX latency/jitter fence; wave-46 decline re-verified |
| data-bus ARINC 629 / ARINC 825 / CAN / TTEthernet | 0 hits tree-wide for all of them (re-run this session); standards-map.yaml carries only arinc-429, arinc-664, mil-std-1553 ids (lines 204/215/237) | Map-blocked; wave-44/45/46 closure re-verified |
| flight-management great-circle / orthodrome / haversine geometry | lateral-navigation owns great-circle track angle/distance; rhumb-line-leg owns the rhumb-vs-great-circle delta; flight-planning owns great-circle leg distances | Fully owned across three siblings with corpus demand |
| flight-management radio horizon / reception range | ads-b-surveillance owns 1090 MHz extended squitter radio line-of-sight range d = RANGE_COEFF * (sqrt(h1) + sqrt(h2)) | Radio line-of-sight range formula owned cross-pack under rtca-do-260b; a VHF/UHF horizon twin would steal that token |
| flight-management holding wind / outbound timing | holding-pattern-entry owns outbound leg timing and 1-in-60 wind-corrected outbound heading (tags holding-wind-correction, outbound-leg-timing) | Owned with corpus demand |
| flight-management procedure turn / base turn / course reversal | 0 hits for procedure-turn/base-turn/course-reversal in skills/ + eval/ (re-run this session) | No corpus demand and no standards-map id for ARINC 424 or TERPS/PANS-OPS procedure design (map-blocked) |
| flight-management CDA / RNP-VNAV / FMS-function seams | 0 hits for continuous-descent/cda (re-run this session); vertical-navigation owns TOD/descent-gradient/FPA; rnp-anp-containment owns RNP/ANP; radius-to-fix-leg owns RF/RNP-AR arcs; performance-computation owns cost index/ECON/step-climb | All seams owned with corpus demand; wave-46 declines re-verified |
| surveillance TAWS/GPWS + Mode-S/transponder | 0 hits for taws/gpws/terrain-awareness/egpws/ground-proximity tree-wide (re-run this session, EXIT clean); standards-map.yaml carries rtca-do-229/185/260b only — no terrain-awareness MOPS, no DO-181 Mode-S family; tcas-resolution-advisory fences "state, not the transponder waveform, not the FMS route, not a datalink" (line 38); the 7 "transponder/mode-s" token hits are modal-analysis "mode-shape" and a Markov "mode-switched" corpus row (unrelated) | CLOSED, RTCA-gated: wave-32 decline re-verified, no fresh evidence; wind-shear content owned cross-family by flight-mechanics |
| surveillance weather-radar received-power / detection-range (radar equation) | 0 owner hits for radar-range-equation/detection-range/radar-cross-section in avionics (the only 2 hits are space-systems link-budget leaves, doppler-shift and antenna-aperture-sizing, unrelated); airborne-weather-radar's description owns the "airborne weather radar ... reflectivity factor, rainfall rate, marshall palmer, echo level, ground clutter" operating-point trigger and never fences detection range out with its own wording | Conditional decline: no sibling fence-out quote exists, so a new leaf would route-fragment the existing weather-radar trigger tokens (Hit@1 fragility); zero corpus demand. Reopen only if airborne-weather-radar first fences received-power/detection-range out explicitly |
| IMA extension seams (partition offsets, ports, health) | ima-partitioning owns ARINC 653 partition schedule feasibility, MAF summation, port latency bounds, health monitoring; do297 owns module acceptance/resource budgets; arinc-653 has 0 hits in standards-map.yaml (re-verified this session) | arinc-653 has no standards-map id: any new IMA leaf is map-blocked on the reference its content requires; wave-46 decline re-verified |
| do160 section seams (17/18/19/26 and beyond 8/23) | environmental-qualification is the section-mapping umbrella; section 23 verdict logic is inside lightning-protection's description; section 8 vibration content owned cross-family; voltage-spike/flammability/audio-frequency-conducted tokens all resolve to fuel-tank flammability in SES/vehicle-design (cross-family, unrelated to do160) | Table-gated test conditions from the gated standard, no closed-form computation anchor; wave-44/45/46 closure re-verified |
| far-cs25 additions | airworthiness owns certification basis + 25.1309 scope + means of compliance; special-conditions owns 25.17 scoping; quantitative severity/DAL apportionment routes cross-family to SES arp4761a leaves | Saturated 2-leaf pack; every quantitative seam routes cross-family to owned leaves; wave-46 decline re-verified |

## Closed veins (re-verified fresh at HEAD a4ae6d1e, receipts over lists)

- TAWS/GPWS: CLOSED. Zero token hits repo-wide, no RTCA terrain MOPS id
  in standards-map.yaml, wave-32 decline stands, no fresh evidence.
- Mode-S / transponder / 1090ES channel occupancy: CLOSED.
  tcas-resolution-advisory fences the transponder waveform out (line 38),
  ads-b owns 1090ES under rtca-do-260b, no Mode-S transponder MOPS id
  exists in the map.
- do160 table-gated sections (incl. 17/18/19/23/26): closed wave-44/45/46.
- ARINC 629 / ARINC 825 / CAN / TTEthernet: map-blocked, zero hits.
- do178c UMS/FLS: objective-table-gated, zero tokens, closed wave-44.
- fsw aperiodic service, shared-resource blocking (PIP/PCP/SRP),
  relative-deadline RTA (constrained/arbitrary-deadline tokens all live
  inside deadline-monotonic-scheduling, re-verified this session),
  criticality-mode RTA: OWNED (aperiodic-server-scheduling,
  shared-resource-access-control, deadline-monotonic-scheduling,
  mixed-criticality-scheduling); do not reopen.
- Wind-triangle / air-data conversions / position fixing: owned
  cross-family (flight-mechanics wind-effects and performance,
  cross-cutting units, FTO position-error-calibration, gnc-autonomy
  navigation); wave-45/46 receipts stand, no ownership change in the
  wave-46-to-47 avionics diff (MC leaf only).

## Method and honesty notes

- All greps and scans were read-only terminal/search_files runs at HEAD
  a4ae6d1e this session; no repo file was modified and no helper script
  artifacts were left in the repo. This receipt is the only write.
- Corpus parser: 1286 of 1286 expected_skill rows parsed; avionics
  inventory set-identical to disk, 101 rows over 49 distinct targets
  (every leaf carries 2 rows; the 3 level-A extra rows sit on do178c
  planning/development/configuration-management).
- Census counts: 647 SKILL.md repo-wide (tracked == disk, 635 leaves +
  12 routers), of which avionics 49 across data-bus 5, do160 6, do178c
  9, do254 4, far-cs25 2, flight-management 11, fsw 7, ima 2,
  surveillance 3, matching the brief exactly. Avionics router table rows
  == 49 == leaves (parity).
- One early token battery in this session used backslash-escaped
  alternation (\|) under grep -E, which matches a literal pipe; those
  runs were discarded and every battery re-run with correct ERE before
  any conclusion was drawn.
- EDF-VD is offered with the same GO profile as the wave-45
  deadline-monotonic and wave-46 mixed-criticality GOs: zero prior
  corpus demand, real published deterministic anchors with verifiable
  magnitudes (Baruah et al. IEEE ToC 2012 web-verified this session),
  standards-map id present, spec-time tasks supply demand, and build-time
  fence/row additions are required (real-time-scheduling fence line,
  mixed-criticality related-leaf line, avionics router row). If wave-47
  triage prefers no scheduling leaf this wave, the fallback is
  NO_CANDIDATES for the whole family: every other seam above declines
  with receipts regardless of the EDF-VD decision.
