---
name: virtual-deadline-scheduling
description: "Use when you must decide the offline schedulability of an avionics flight software task set under the dual-criticality execution-time model scheduled by edf-vd virtual-deadline scheduling: each task carries the C_LO and C_HI execution-time estimates with C_HI at least C_LO and the implicit-deadline period T, sum the per-mode demand contributions of the LO and HI tasks, derive the common virtual-deadline factor x for the HI tasks, and check the lo-criticality-mode and the hi-criticality-mode demand conditions after the criticality mode change. Produces the per-mode demand sums, the virtual-deadline factor x, the per-HI-task virtual deadlines x*T, the lo-criticality-mode feasible verdict, the hi-criticality-mode feasible verdict, and the whole-set edf-vd feasible verdict. Trigger: edf vd scheduling, virtual deadline scheduling, virtual deadline factor, dual criticality mode change, lo criticality mode demand, hi criticality mode demand."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: do-178c
    reference-only: true
gated: false
domain: avionics
pack: fsw
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: fsw
  tags: [virtual-deadline-scheduling, edf-vd-analysis, virtual-deadline-factor, hi-criticality-mode-edf, lo-criticality-mode-edf, dual-mode-demand-check]
  version: 0.1.0
  author: AeroSkills
---

# Virtual-Deadline Scheduling (avionics/fsw/virtual-deadline-scheduling)

Use when the task is deciding the offline schedulability of an
avionics flight software task set under the dual-criticality
execution-time model scheduled by EDF-VD, the virtual-deadline
scheduling algorithm of Baruah, Bonifaci, D'Angelo, Li,
Marchetti-Spaccamela, Megow and Stougie (2012). Each task carries a
low-criticality execution-time estimate C_LO and a high-criticality
estimate C_HI, and EDF is priority-free: there is no task list order
and no deadline key, only the implicit period T. This leaf implements
the closed-form per-mode demand test, pure Python, stdlib only. It
pairs with avionics/fsw/mixed-criticality-scheduling, the
fixed-priority AMC-rtb branch of the same dual-criticality model, and
with avionics/fsw/real-time-scheduling, whose classic implicit-deadline
EDF verdict this leaf reproduces exactly on an all-LO set.

## Domain quick reference

- Task model: {name, criticality, C_LO, C_HI, T}, criticality "LO" or
  "HI", C_HI at least C_LO, one time unit, implicit deadline D = T. A
  LO task carries no high estimate, so its C_HI equals its C_LO. There
  is no priority order: any task list order is accepted.
- Per-mode demand sums: a = u_lo_lo = sum over LO tasks of C_LO / T,
  b = u_hi_lo = sum over HI tasks of C_LO / T, c = u_hi_hi = sum over
  HI tasks of C_HI / T. U_LO = a + b, U_HI = c.
- Virtual-deadline factor: x = b / (1 - a) when a HI task exists and
  a < 1 (every HI task's LO-mode deadline shortens to x * T); x = 1.0
  (no tightening) when no HI task exists; x is None when a >= 1 with
  at least one HI task, the LO tasks alone saturating the processor.
- LO-mode condition (the EDF demand density of the virtual-deadline
  LO-mode schedule): a + b / x <= 1, which at the canonical factor is
  exactly U_LO <= 1.
- HI-mode condition (the demand condition after the LO to HI
  criticality mode change, when LO jobs are dropped): c + a * x <= 1.
  The a * x term is the virtual-deadline tightening cost: a smaller x
  helps the HI-mode condition, a larger x helps the LO-mode condition.
- Verdicts: lo-criticality-mode feasible iff the LO-mode condition
  holds (False when x is None); hi-criticality-mode feasible iff the
  HI-mode condition holds, vacuously True for an all-LO set (c = 0,
  no HI task to guarantee); the whole-set edf-vd feasible verdict is
  lo feasible and hi feasible.
- Multiprocessor-form cross-check: a <= (1 - c) / (1 - c + b) holds
  iff c + a * x <= 1 holds, an equivalent restatement of the HI-mode
  condition.
- Units are one time unit throughout (ms in the worked example below).
  Module constant TOL = 1e-12 is the tolerance every comparison uses.
  The DO-178C software level scheme A-E frames which tasks need the
  higher-assurance estimate as reference-only context; no level is
  ever determined here.

## Workflow

1. Build the task list with each task's criticality, C_LO, C_HI and T;
   EDF is priority-free, so any list order is accepted.
2. Compute the per-mode demand sums (a, b, c) with utilizations(tasks),
   returning u_lo_lo, u_hi_lo, u_hi_hi, u_lo and u_hi.
3. Derive the common virtual-deadline factor with
   virtual_deadline_factor(tasks): 1.0 with no HI task, None when the
   LO tasks alone saturate the processor.
4. Get the per-HI-task virtual deadlines x * T with
   virtual_deadlines(tasks), keyed by task name ("task" when a task
   carries no name key), an empty dict for an all-LO set, None when no
   factor exists.
5. Check the lo-criticality-mode demand condition a + b / x <= 1 with
   lo_mode_feasible(tasks).
6. Check the hi-criticality-mode demand condition c + a * x <= 1 with
   hi_mode_feasible(tasks), vacuously True for an all-LO set.
7. Gather every result in one call with edf_vd_report(tasks): the
   demand sums, x, the virtual deadlines, both mode verdicts and the
   whole-set feasible verdict.
8. Get the convenience whole-set verdict alone with feasible(tasks).
   Confirm the deterministic checks, including ValueError rejection of
   non-physical inputs, with the contract test
   scripts/test_virtual_deadline_scheduling.py.

## Worked example

Task set A, three avionics fsw processes in ms, any list order (EDF is
priority-free), implicit deadlines D = T:

- flight-control: criticality HI, C_LO 1.0, C_HI 2.0, T 5.0.
- health-monitor: criticality HI, C_LO 2.0, C_HI 4.0, T 10.0.
- guidance: criticality LO, C_LO 2.0, C_HI 2.0, T 10.0 (dropped after
  the criticality mode change, so only its C_LO / T contributes to the
  per-mode sums).

edf_vd_report(SET_A) (module output): u_lo_lo 0.2 (guidance only,
2.0/10.0), u_hi_lo 0.4 (1.0/5.0 + 2.0/10.0), u_hi_hi 0.8 (2.0/5.0 +
4.0/10.0), u_lo 0.6000000000000001, u_hi 0.8. The virtual-deadline
factor x is 0.5 exactly (0.4 / (1 - 0.2)); the LO-mode density
a + b/x prints 1, so lo_feasible is True. The HI-mode demand
c + a*x is 0.90000000000000002, at most 1, so hi_feasible is True:
flight-control and health-monitor can overrun to their C_HI estimates
and still meet their real deadlines after the criticality mode
change. virtual_deadlines gives {flight-control: 2.5, health-monitor:
5.0}, i.e. 0.5 * 5.0 and 0.5 * 10.0 ms. The multiprocessor-form
cross-check (1 - c) / (1 - c + b) evaluates to 0.33333333333333326,
above a 0.2, consistent with the HI-mode condition holding. The
whole-set verdict feasible is True.

Task set B (HI-mode overload, the mode-change verdict): guidance LO
C_LO 3.0, T 10.0; flight-control HI C_LO 1.0, C_HI 3.0, T 10.0;
health-monitor HI C_LO 2.0, C_HI 6.0, T 10.0. Module output: u_lo_lo
0.3, u_hi_lo 0.30000000000000004, u_hi_hi 0.8999999999999999, u_lo
0.6000000000000001, x 0.42857142857142866 (the LO-mode density prints
1, so lo_feasible is True). The HI-mode demand c + a*x is
1.0285714285714285, strictly above 1, so hi_feasible is False and the
whole verdict is False: the HI-mode demand c = 0.9 alone is at most 1,
yet the a*x tightening term 0.1285714285714286 shows the LO tasks
leave too little early slack for the mode change. Virtual deadlines
print 4.2857142857142865 ms for both HI tasks (x * 10.0).

Task set C (LO-mode overload, the no-factor verdict): guidance LO
C_LO 8.0, T 10.0; trim LO C_LO 1.0, T 5.0; flight-control HI C_LO 1.0,
C_HI 2.0, T 10.0. Module output: u_lo_lo 1.0 (the LO tasks alone
saturate the processor), u_hi_lo 0.1, u_hi_hi 0.2, u_lo 1.1. The
factor x reports None, lo_feasible False, hi_feasible False, feasible
False, virtual_deadlines None: no common virtual-deadline factor
exists and edf-vd rejects the set.

Identity anchors (module output): the all-LO set [(1, 3), (1, 4),
(2, 8)] gives u_lo 0.8333333333333333, x 1.0, feasible True with an
empty virtual_deadlines dict; the all-LO overload [(2, 3), (2, 5),
(2, 7)] gives u_lo 1.3523809523809525, feasible False (hi_feasible
stays vacuously True); the HI-only set [(1.0, 2.0, 5.0), (2.0, 4.0,
10.0)] gives u_hi 0.8, x 0.4, feasible True; the no-overrun collapse
of set A (every C_HI equal to C_LO) gives u_lo 0.6000000000000001,
x 0.5, HI demand c + a*x 0.5 (equal to x since c = b at the collapse),
feasible True.

## Verification

- Confirm edf_vd_report(SET_A) gives u_lo_lo 0.2, u_hi_lo 0.4, u_hi_hi
  0.8, u_lo 0.6, u_hi 0.8, x 0.5, lo_feasible True, hi_feasible True,
  feasible True, virtual_deadlines {flight-control: 2.5,
  health-monitor: 5.0}, LO-mode density 1.0 and HI-mode demand 0.9.
- Confirm set B (u_lo_lo 0.3, u_hi_lo 0.3, u_hi_hi 0.9, x
  0.42857142857142866) gives lo_feasible True, hi_feasible False,
  feasible False, HI-mode demand 1.0285714285714285.
- Confirm set C (u_lo_lo 1.0) gives x None, lo_feasible False,
  hi_feasible False, feasible False, virtual_deadlines None.
- Confirm the all-LO identity against the pack sibling's classic
  results: [(1, 3), (1, 4), (2, 8)] gives u_lo 0.8333333333333333,
  x 1.0, feasible True; [(2, 3), (2, 5), (2, 7)] gives u_lo
  1.3523809523809525, feasible False.
- Confirm the multiprocessor-form equivalence on set A:
  (1 - c) / (1 - c + b) = 0.33333333333333326, above a 0.2, and holds
  iff hi_mode_feasible holds on every HI-bearing validation set.
- Confirm every non-physical input (empty list, missing key, boolean
  or non-positive C_LO/C_HI/T, C_HI below C_LO, a LO task with C_HI
  above C_LO, an unknown criticality word) raises ValueError from
  every public function.
- Run the contract test offline: python3
  scripts/test_virtual_deadline_scheduling.py (deterministic).

## Related leaves

- avionics/fsw/mixed-criticality-scheduling: the fixed-priority
  AMC-rtb branch of the same dual-criticality (C_LO, C_HI) model, over
  a deadline-monotonic priority order with a per-task fixed-point
  response-time solve; this leaf runs the priority-free EDF branch
  with a closed-form demand test instead, on the same C_LO/C_HI pair.
- avionics/fsw/real-time-scheduling: the single-execution-time
  implicit-deadline (C, T) model whose classic EDF full-utilization
  verdict this leaf reproduces exactly on an all-LO set (a <= 1); a
  task with no HI estimate belongs there, not here.
- avionics/do178c/planning: software level and DAL determination, the
  context that motivates the C_LO/C_HI split; this leaf never
  determines a level.

## Pitfalls

- Treating the LO-mode density as a real test: at the canonical factor
  a + b/x always prints 1 when a HI task exists, by construction; the
  substantive LO-mode requirement is that a factor exists at all
  (x is not None), not that the density differs from 1.
- Skipping the HI-mode check after a passing LO-mode verdict: set B
  passes the LO-mode condition (density 1) yet fails the HI-mode
  condition (c + a*x = 1.0285714285714285, above 1); both conditions
  must hold for the whole-set verdict.
- Assuming an all-LO set can fail hi_mode_feasible: an all-LO set has
  no HI task to guarantee, so hi_feasible is vacuously True even when
  a > 1 (the all-LO overload identity); the whole-set verdict still
  fails there because lo_feasible is False.
- Imposing a priority order on the task list: EDF is priority-free, so
  no deadline-monotonic or other ordering check exists here, unlike
  the fixed-priority AMC-rtb sibling.
- Mistaking this leaf for the AMC-rtb fixed-point response-time
  analysis: this leaf never iterates a per-task response time or
  charges an interference sum; it is the closed-form per-mode demand
  test of Baruah et al. 2012 (avionics/fsw/mixed-criticality-
  scheduling owns the response-time branch).
- Applying this leaf to a single-estimate (C, T) task set: a task with
  no HI estimate belongs to avionics/fsw/real-time-scheduling; this
  leaf's model requires the C_LO/C_HI pair and criticality tag on
  every task.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline, no
network, exits 0):

    python3 scripts/test_virtual_deadline_scheduling.py

The test covers the worked sets A, B and C from the spec, the all-LO
and HI-only reductions against the pack siblings' classic results, the
no-overrun collapse identity, the multiprocessor-form equivalence, the
factor discipline (0 < x <= 1 iff U_LO <= 1, x is None iff a >= 1 with
a HI task present), the HI-mode vacuous-True scope on an all-LO set,
determinism across runs, and ValueError rejection of every
non-physical input enumerated above.

## Compliance

- Standards referenced, not reproduced: DO-178C (RTCA, joint EUROCAE
  ED-12C) frames the avionics software lifecycle context in which the
  scheduling analysis artifact is recorded, per standards-map.yaml.
  The edf-vd closed-form demand test is public science (Baruah,
  Bonifaci, D'Angelo, Li, Marchetti-Spaccamela, Megow and Stougie,
  IEEE Transactions on Computers 61(8):1140-1152, 2012), summary-only;
  no standard text is reproduced and no software level or DAL is ever
  determined by this leaf.
- compliance: STANDARDS-REF, gated: false.
