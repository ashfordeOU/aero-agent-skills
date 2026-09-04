---
name: real-time-scheduling
description: "Use when you must decide the offline schedulability of a periodic hard-real-time task set: compute the processor utilization of (C, T) tasks with implicit deadlines, apply the Liu-Layland utilization bound for rate-monotonic fixed-priority scheduling, run the exact iterative response-time analysis task by task, and test earliest-deadline-first feasibility with the full-utilization condition. Produces the utilization, the RM bound verdict, the exact response times with an RM feasibility verdict, the EDF feasibility verdict, and an overall scheduling verdict for avionics process and partition task sets. Trigger: rate monotonic scheduling, response time analysis, liu layland bound, earliest deadline first, cpu utilization, fixed priority scheduling, schedulability, worst case execution time."
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
  tags: [real-time-scheduling, rate-monotonic-scheduling, response-time-analysis, liu-layland-bound, earliest-deadline-first, cpu-utilization, fixed-priority-scheduling]
  version: 0.1.0
  author: AeroSkills
---

# Real-Time Scheduling (avionics/fsw/real-time-scheduling)

Use when you must decide whether a periodic hard-real-time task set can
meet every deadline on a single processor, before it ever runs. Each
task is a (C, T) pair: worst-case execution time C and period T, with
the implicit deadline D = T, all in one time unit. This leaf implements
the standard public feasibility mathematics (Liu and Layland 1973 plus
exact iterative response-time analysis) in pure Python stdlib: the
processor utilization, the Liu-Layland sufficient bound for
rate-monotonic fixed-priority scheduling, exact per-task response times
with an RM verdict, and the earliest-deadline-first full-utilization
verdict. It schedules the processes and partitions inside an ARINC 653
style avionics software partition layout, pairing with
avionics/ima/ima-partitioning, which owns the major-frame cyclic window
arithmetic that surrounds this leaf's process set.

## Domain quick reference

- Task set convention: n tasks, each (C_i, T_i) with implicit deadline
  D_i = T_i, all in the same time unit. Shorter period means higher
  priority under RM; equal periods are broken by list index (the
  earlier task in the list is higher priority).
- Utilization: U = sum_i C_i / T_i. This is the fraction of the
  processor the task set demands in the long run.
- Liu-Layland bound: U_rm(n) = n (2^(1/n) - 1). Anchor values:
  U_rm(2) = 0.828427, U_rm(3) = 0.779763, U_rm(4) = 0.756828, and
  U_rm(1) = 1. The bound decreases toward ln 2 ~ 0.693 as n grows.
- RM sufficient test: if U <= U_rm(n) the set is feasible under RM. The
  bound is sufficient, not necessary: a set with U above the bound may
  still be RM-feasible, which is exactly when the exact analysis earns
  its keep.
- Exact RM response time of task i (fixed-point iteration):
  R_i = C_i + sum_{j in hp(i)} ceil(R_i / T_j) * C_j, iterated from
  R_i = C_i until the value stops changing, where hp(i) is the set of
  higher-priority tasks. RM is feasible iff every converged R_i <= T_i.
- Divergence handling: the response-time sequence is monotone
  non-decreasing, so when an iterate grows past the task period, or
  past the cap 1000 * max(T) of the set, it can never converge to a
  schedulable value and the analysis reports divergence. A diverging or
  deadline-crossing task makes the whole set RM-infeasible.
- EDF feasibility (implicit deadlines): U <= 1 is necessary and
  sufficient, because EDF is optimal among all scheduling algorithms on
  a single processor.
- Scheduling verdicts: "RM-guaranteed-by-UB" when the bound test
  passes; "RM-exact-feasible (UB inconclusive)" when the bound test
  fails but exact response-time analysis converges within every period;
  "EDF-feasible-only" when RM exact analysis fails but EDF can schedule
  the U <= 1 set; "RM-infeasible" otherwise.
- Scope notes: WCET estimation, jitter and blocking analysis, and
  arbitrary-deadline response-time extensions are out of scope; the
  model is the classic implicit-deadline periodic task set. ARINC 653
  partition schedule windows and message bus response windows are not
  this leaf.

## Workflow

1. Collect the task set as a list of (C, T) pairs in one time unit,
   worst-case execution time and period each, implicit deadline
   D = T. Every C and T must be positive; an empty list, a
   non-positive value, or a malformed entry raises ValueError from
   every function.
2. Compute the processor demand: utilization(tasks) returns U. If
   U > 1 the processor is oversubscribed: no single-processor
   scheduling algorithm can work, and EDF feasibility will fail.
3. Run the cheap sufficient test first: rm_ub_feasible(tasks) applies
   the Liu-Layland bound U <= U_rm(n). A True verdict closes the case
   (RM is guaranteed). A False verdict is inconclusive, not a failure.
4. When the bound is inconclusive, run the exact analysis:
   rm_response_times(tasks) returns the converged R_i list, or None
   when the iteration diverges (an iterate exceeded its period or the
   1000 * max(T) cap), and rm_feasible(tasks) gives the exact RM
   verdict. This is where rate-monotonic analysis beats the
   utilization bound: a set that fails step 3 can still pass here.
5. Check the EDF alternative: edf_feasible(tasks) reports whether U
   <= 1, which for implicit-deadline sets is a complete EDF test.
6. Run scheduling_summary(tasks) once to gather every result: keys
   utilization, n_tasks, liu_layland_bound, rm_ub_verdict,
   rm_exact_response_times, rm_exact_feasible, edf_feasible, and a
   single verdict string.
7. Record the verdict and the response times in the scheduling
   analysis artifact for the certification package; re-run the
   contract test after any change to the task set.

## Worked example

Spec task set A, [(1, 3), (1, 4), (2, 8)] (times in ms):

- Utilization: U = 1/3 + 1/4 + 2/8 = 0.8333333333333333.
- Liu-Layland bound for 3 tasks: 0.7797631496846196, so U > bound and
  rm_ub_feasible returns False: the bound test is inconclusive.
- Exact response-time analysis converges:
  rm_response_times(A) = [1.0, 2.0, 6.0] ms, all within their periods
  (3, 4, 8 ms), so rm_feasible returns True.
- EDF: U = 0.8333 <= 1, so edf_feasible returns True.
- scheduling_summary(A)["verdict"] is
  "RM-exact-feasible (UB inconclusive)": the key demonstration that
  response-time analysis proves schedulability where the Liu-Layland
  bound stays silent.

Set B, [(2, 3), (2, 5), (2, 7)]: U = 1.3523809523809525 > 1, so
edf_feasible is False, rm_response_times returns None (the second task
response time crosses its period and the iteration diverges), and the
verdict is "RM-infeasible".

Set C, [(1, 5), (1, 6), (2, 10)]: U = 0.5666666666666667 <= 0.7798, so
rm_ub_feasible is True and the verdict is "RM-guaranteed-by-UB"; the
exact analysis confirms with response times [1.0, 2.0, 4.0].

## Verification

- Confirm the Liu-Layland anchors: liu_layland_bound(2) = 0.828427,
  liu_layland_bound(3) = 0.779763, liu_layland_bound(4) = 0.756828
  (each within 1e-5).
- Confirm worked set A gives U 0.8333, rm_ub_feasible False (bound
  inconclusive), rm_response_times [1.0, 2.0, 6.0] with rm_feasible
  True, edf_feasible True, verdict "RM-exact-feasible (UB
  inconclusive)".
- Confirm worked set B gives U 1.3524 > 1, edf_feasible False, RTA
  divergence (None), rm_feasible False.
- Confirm worked set C gives U 0.5667, rm_ub_feasible True, response
  times [1.0, 2.0, 4.0], verdict "RM-guaranteed-by-UB".
- Confirm adding a task raises U and doubling a task's C doubles that
  task's utilization contribution.
- Confirm an empty task list, C <= 0, T <= 0, malformed or
  non-numeric entries, and a fractional task count raise ValueError
  from every public function.
- Confirm identical outputs run to run (no randomness anywhere).
- Run the deterministic contract test offline: python3
  scripts/test_real_time_scheduling.py (35 tests).

## Related leaves

- avionics/ima/ima-partitioning: ARINC 653 major-frame cyclic window
  arithmetic; this leaf schedules the periodic process sets that run
  inside those partition windows.
- avionics/fsw/cfs-architecture: flight software application
  routing; its periodic applications carry the C and T budgets this
  leaf checks.
- avionics/data-bus/mil-std-1553: bus command/response protocol
  timing; its response-window concept is a bus term, not a task
  response time.

## Contract test

Run the deterministic contract test (stdlib unittest, offline, no
network, exits 0):

    python3 scripts/test_real_time_scheduling.py

The test covers the Liu-Layland anchors U_rm(2/3/4), the three worked
task sets A, B and C from the spec plus an EDF-feasible-only set D,
exact response times with integrality for integer input, divergence
detection returning None, single-task closed forms (R = C, feasible iff
C <= T), utilization monotonicity and doubling, the EDF unit-utilization
boundary, the exact convenience-dict keys, ValueError rejection of
empty, non-positive and malformed task lists, and run-to-run
determinism.

## Compliance

- Standards referenced, not reproduced: DO-178C (avionics software
  lifecycle, including scheduling analysis of the software partition
  task sets) is listed reference-only per standards-map.yaml; the
  feasibility mathematics above is pure public science (Liu and
  Layland, 1973), summary-only.
- ARINC 653 is not in standards-map.yaml and is not needed: the
  process-level scheduling theory is independent of the partition
  standard text.
- compliance: STANDARDS-REF, gated: false.
