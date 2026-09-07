---
name: deadline-monotonic-scheduling
description: "Use when you must decide the fixed-priority schedulability of an avionics flight software task set whose per-task relative deadlines are not the implicit period: order the tasks by deadline-monotonic priority assignment so the shorter deadline ranks higher, run the exact jitter-aware fixed-point response-time iteration against each task's own deadline, and cover constrained deadlines (D no greater than T) and arbitrary deadlines (D beyond T) with the busy-period job scan when a queued job can be the worst. Produces the deadline-monotonic priority order, the per-task worst-case response times against the per-task deadlines, the release-jitter recomputation when a higher-priority task carries release jitter, the feasible verdict for the whole set, and the divergence verdict when an iterate or a queued job's response crosses its deadline. Trigger: deadline monotonic scheduling, constrained deadline, arbitrary deadline, release jitter, relative deadline, shorter deadline priority."
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
  tags: [deadline-monotonic-scheduling, constrained-deadline-rta, arbitrary-deadline-rta, release-jitter-rta, dm-priority-assignment, shorter-deadline-order]
  version: 0.1.0
  author: AeroSkills
---

# Deadline-Monotonic Scheduling (avionics/fsw/deadline-monotonic-scheduling)

Use when an avionics flight software task set has per-task relative
deadlines D_i that are not the implicit D_i = T_i of the pack sibling,
so the periodic-only model cannot admit the set at all: a 40 ms-period
navigation task that must finish within 25 ms, or a 30 ms-period
recording task that tolerates a 60 ms relative deadline. This leaf
assigns priorities by deadline-monotonic order (shorter deadline,
higher priority; the fixed-priority assignment Leung and Whitehead
(1982) proved optimal for constrained deadlines), then runs the exact
jitter-aware fixed-point response-time iteration task by task against
each task's own deadline. Constrained deadlines (D <= T) need only the
converged first-job completion; arbitrary deadlines (D > T) whose
first-job completion exceeds the period additionally run the
busy-period job scan and take the worst job response as the exact
response time. Pure Python stdlib, closed form (math.ceil only),
deterministic. Pairs with avionics/fsw/real-time-scheduling for the
implicit-deadline feasibility verdicts of a set where every D = T and
with avionics/fsw/shared-resource-access-control when a shared-resource
blocking term must be added to the fixed point.

## Domain quick reference

- Task shape: each task is a dict {name, C, T, D, J} in one time unit,
  worst-case execution C, period T, relative deadline D, optional
  release jitter J (default 0.0); name is optional. Every function
  rejects, with ValueError, an empty task list, a malformed entry, a
  missing C/T/D key, a boolean or non-positive C, T or D, a boolean or
  negative J, and a non-numeric value.
- Deadline-monotonic order: tasks sorted by D ascending, stably, so the
  shorter deadline ranks higher (index 0) and equal deadlines keep
  their input order. For constrained deadlines this assignment is
  optimal among fixed priorities (Leung and Whitehead, "On the
  Complexity of Fixed-Priority Scheduling of Periodic Real-Time
  Tasks", Performance Evaluation 2(4), 1982). The analysis functions
  require the list to already be in this order and raise ValueError
  otherwise; dm_priority_order produces it.
- Busy-window completion of job q of task i (Audsley, Burns,
  Richardson and Wellings, "Applying New Scheduling Theory to Static
  Priority Pre-emptive Scheduling", Software Engineering Journal,
  1993): w_i(q) = (q + 1) * C_i + sum over higher-priority j of
  ceil((w_i(q) + J_j) / T_j) * C_j, iterated from w = (q + 1) * C_i
  until an iterate repeats within CONVERGENCE_TOL (1e-12). For q = 0
  this is the classic fixed point R_i = C_i + sum of
  ceil((R_i + J_j) / T_j) * C_j, with the Tindell and Clark (1994)
  release-jitter term in the interference count. The map is monotone
  non-decreasing.
- Convergence rule: job q of task i releases at q * T_i and completes
  at w_i(q), so its response is w_i(q) - q * T_i and it must satisfy
  w_i(q) <= q * T_i + D_i. An iterate past that per-job bound can
  never converge under the deadline, so the solve reports None; a
  solve that still moves after MAX_RTA_ITERATIONS (100) passes also
  reports None.
- Constrained deadlines (D <= T): the converged first-job completion
  w_i(0) is the exact worst-case response time, feasible iff
  w_i(0) <= D_i; successive jobs never overlap, so no job scan runs.
- Arbitrary deadlines (D > T): when w_i(0) <= T_i the first-job
  completion is again the exact response. When w_i(0) > T_i, jobs
  queue and the exact response is the maximum of w_i(q) - q * T_i over
  the busy period, scanned while w_i(q) > (q + 1) * T_i and stopped at
  the first q with w_i(q) <= (q + 1) * T_i. A job response past D_i,
  or a scan past MAX_BUSY_PERIOD_JOBS (1000), reports None.
- Release jitter: J_j of a higher-priority task delays its releases by
  up to J_j and enters only the interference counts of lower-priority
  tasks through ceil((w + J_j) / T_j); a task's own J never enters its
  own equation. Jitter can inflate lower responses by whole
  preemptions and can push a first-job completion past T_i, opening
  the queueing regime.
- Utilization: U = sum of C_i / T_i, reported for context only; it is
  not a verdict when deadlines differ from periods, but U > 1 always
  ends in None through the never-ending busy period.
- Module constants: MAX_RTA_ITERATIONS = 100, MAX_BUSY_PERIOD_JOBS =
  1000, CONVERGENCE_TOL = 1e-12. Imports math only.

## Workflow

1. Assemble the task set as {name, C, T, D, J} dicts in one time unit,
   with J and name optional; every function validates the shape and
   raises ValueError on an empty list, malformed entry, missing key,
   boolean or non-positive C/T/D, or boolean or negative J.
2. Order the priorities: dm_priority_order over the task list returns
   the deadline-monotonic priority order, shorter deadline higher
   priority with stable ties (the shorter-deadline-order assignment).
3. Compute the context utilization: utilization over the set gives
   U = sum of C/T, reported but never a verdict (deadlines differ).
4. Run the jitter-aware fixed-point response-time iteration against
   each per-task deadline: response_time on each index of the
   deadline-monotonic-ordered list converges w_i(0) against D_i; a
   constrained-deadline task needs only this first-job completion.
5. Run the arbitrary-deadline busy-period job scan: response_time on a
   task with D > T whose first-job completion exceeds T_i scans the
   queued jobs and returns the worst job response, or None on
   divergence (an iterate or a queued job's response past D_i).
6. Recompute with the release jitter zeroed: response_time on the
   jitter-free copy of the set isolates what the higher-priority
   task's release jitter costs each lower task.
7. Take the feasible verdict: dm_response_times (or feasible) over the
   ordered list reports names, per-task response times, the feasible
   verdict (every response at most its own deadline) and U.
8. Confirm with the deterministic contract test run under both
   interpreters (see Behavior contract).

## Worked example

Task set A, four avionics fsw processes in ms, already in
deadline-monotonic order (deadlines 10, 20, 25, 60 ms ascending):
flight-control (C 2.0, T 10.0, D 10.0, J 4.0), guidance (C 1.0,
T 20.0, D 20.0), navigation (C 4.0, T 40.0, D 25.0, a constrained
deadline shorter than its period) and mission-recording (C 18.0,
T 30.0, D 60.0, an arbitrary deadline beyond its period). Real module
outputs:

- dm_priority_order(A) keeps the list as given: the 25 ms-deadline
  navigation task outranks the 60 ms-deadline mission-recording task
  even though its 40 ms period is longer, the opposite of a
  period-ordered assignment.
- Full analysis: dm_response_times(A) gives responses [2.0, 3.0, 9.0,
  32.0] ms against deadlines [10, 20, 25, 60] ms, utilization 0.95,
  feasible True: every task closes inside its own deadline.
- Constrained deadline and the jitter cost: response_time(A, 2) =
  9.0 ms against D 25 ms for navigation; with J_0 = 0 the same task
  closes at 7.0 ms, so the 4 ms release jitter on flight-control costs
  navigation exactly 2.0 ms = C_0, one extra flight-control preemption
  counted by ceil((R + 4) / 10) at the converged R = 9.
- Arbitrary deadline, jittered: response_time(A, 3) = 32.0 ms against
  D 60 ms for mission-recording. Its first-job completion w(0) =
  32.0 ms exceeds T = 30 ms, so jobs queue and the busy-period scan
  runs: completions w(0..3) = 32.0, 62.0, 91.0, 114.0 ms with job
  responses 32.0, 32.0, 31.0, 24.0 ms, stopping at job 3 because
  w(3) = 114.0 <= 4 * T = 120.0 ends the busy period; the exact worst
  case is the max, 32.0 ms. Without the jitter the first-job
  completion is exactly 30.0 ms = T, so no job ever queues and the
  response is 30.0 ms: the jitter is what opens the queueing regime.
- Queued job strictly the worst (navigation C = 5 variant, still
  D 25 <= T 40): response_time(variant, 2) = 10.0 ms; the
  mission-recording completions become 33.0, 64.0, 94.0, 119.0 ms with
  responses 33.0, 34.0, 34.0, 29.0 ms, so the exact worst-case
  response is 34.0 ms, held by the queued first and second jobs,
  strictly above the first-job completion 33.0 ms: the job scan, not
  the first-job fixed point alone, gives the arbitrary-deadline
  answer.
- Ordering is the analysis: the same four tasks under period-order
  priorities (10, 20, 30, 40) close at 2.0, 3.0 and 26.0 ms for
  flight-control, guidance and mission-recording, but navigation now
  sits below mission-recording and its iterates run 25.0 then 30.0,
  crossing D 25 ms on the second pass, so navigation reports None and
  the period-ordered set is infeasible; the deadline-monotonic order
  is the difference between a feasible and an infeasible set.
- Implicit-deadline identity (D = T, J = 0): the pack sibling's sets
  reproduce exactly, [1.0, 2.0, 6.0] on [(1, 3), (1, 4), (2, 8)] and
  [1.0, 2.0, 4.0] on [(1, 5), (1, 6), (2, 10)], both feasible True,
  and [2.0, None, None] on the over-subscribed [(2, 3), (2, 5),
  (2, 7)], feasible False.
- Over-subscribed arbitrary-deadline variant (mission-recording
  C = 22.0): utilization 1.083333 > 1, and dm_response_times reports
  [2.0, 3.0, 9.0, None], feasible False: the busy period of the
  arbitrary-deadline task never ends and a queued job's response
  crosses D 60 ms, the divergence verdict.
- Single-task closed form: response_time of {(C 3, T 10, D 7)} is
  3.0 = C, feasible; {(C 3, T 10, D 2)} (C > D) reports None.
- Real ValueError messages: an empty list raises "task list must be a
  non-empty list"; a non-deadline-monotonic list raises "tasks must be
  in deadline-monotonic priority order (non-decreasing D); sort with
  dm_priority_order first"; C = 0 raises "C must be a positive number,
  got 0.0"; J = -1 raises "J must be a non-negative number, got
  -1.0"; a missing D raises "task missing key(s) D"; index 4 on the
  four-task list raises "index out of range".

## Verification

- dm_response_times(A) returns [2.0, 3.0, 9.0, 32.0], feasible True,
  utilization 0.95; each response sits at most its own deadline.
- response_time(A, 2) = 9.0 with J_0 = 4 and 7.0 with J_0 = 0, the
  2.0 ms difference equal to C_0 (release-jitter recomputation).
- The busy-period completions of mission-recording, w(0..3) = 32.0,
  62.0, 91.0, 114.0 ms, terminate with 114.0 <= 120.0; the C = 5
  variant completes at 33.0, 64.0, 94.0, 119.0 ms with worst 34.0 ms.
- dm_priority_order is stable (equal deadlines keep input order),
  returns non-decreasing D, and never mutates its input.
- ValueErrors across the module: empty list, missing key, boolean or
  non-positive C/T/D, boolean or negative J, non-numeric value,
  non-deadline-monotonic order (from response_time, dm_response_times
  and feasible), and index outside [0, len(tasks)) (from
  response_time).
- The module is deterministic (identical outputs run to run), imports
  nothing beyond math, and MAX_RTA_ITERATIONS = 100 with
  MAX_BUSY_PERIOD_JOBS = 1000.
- Run the contract test offline: python3
  scripts/test_deadline_monotonic_scheduling.py (42 tests, exits 0;
  also green under ~/.pyenv/versions/3.13.12/bin/python3).

## Related leaves

- avionics/fsw/real-time-scheduling: the implicit-deadline (D = T)
  utilization, bound and response-time feasibility verdicts; a set
  with any per-task deadline D != T routes here, because that leaf's
  model has no deadline slot and no deadline-ordered priority.
- avionics/fsw/shared-resource-access-control: the priority-ceiling
  blocking term B_i that a shared-resource task set adds to the same
  fixed point under implicit deadlines.
- avionics/fsw/aperiodic-server-scheduling: polling, deferrable and
  sporadic server budgets for aperiodic jobs beside an
  implicit-deadline periodic set.
- avionics/ima/ima-partitioning: partition window schedules and
  sampling or queuing port latencies one level above process
  deadlines.
- avionics/fsw/cfs-architecture and avionics/fsw/fprime-component:
  software bus routing and cyclic rate-group dispatch layout.
- avionics/data-bus/mil-std-1553: bus command/response windows, a bus
  term rather than a task response.

## Pitfalls

- Routing a per-task-deadline set to the implicit-deadline sibling:
  real-time-scheduling has no D != T slot, so a 40 ms-period task with
  a 25 ms deadline cannot even be represented there; the
  deadline-monotonic order and the per-task-deadline convergence are
  this leaf's job.
- Assuming period order equals deadline order: the worked set is
  feasible under deadline-monotonic priorities and infeasible under
  rate-monotonic-style period priorities (navigation's second iterate
  30.0 crosses D 25.0); order the priorities by the shorter deadline
  before running any analysis.
- Quoting the first-job completion as the arbitrary-deadline answer:
  when w(0) > T_i a queued job can be strictly the worst (34.0 ms from
  a queued job against a 33.0 ms first-job completion); only the
  busy-period job scan finds the exact worst case.
- Forgetting the release-jitter term: J_j of a higher-priority task
  inflates every lower task's interference count through
  ceil((w + J_j) / T_j), can cost whole preemptions (2.0 ms = C_0 on
  navigation) and can push a first-job completion past T_i into the
  queueing regime; but a task's own jitter never changes its own
  response.
- Reading U as the verdict: with per-task deadlines, U <= 1 is not a
  feasibility test and U > 1 is not the only infeasibility; the
  per-task convergence against each D_i decides.
- Treating a diverged task as a large response: response_time returns
  None when an iterate crosses q * T_i + D_i (it can never converge
  under the deadline) or when the scan exceeds the caps; None is the
  divergence verdict, not a number to compare against D_i.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_deadline_monotonic_scheduling.py

The test covers the task-shape ValueErrors, the deadline-monotonic
priority assignment with stable ties, the context utilization, the
jitter-aware fixed-point iteration against each per-task deadline
including the constrained-deadline first-job completions and the
implicit-deadline equivalence with the pack sibling's classic results,
the arbitrary-deadline busy-period job scan with the exact busy-period
completions and the queued-job-worst identity, the release-jitter
recomputation (2.0 ms cost, queueing-regime opening), the feasible
verdict of the whole set, the ordering-is-the-analysis contrast, the
real ValueError messages, and module discipline (determinism,
math-only imports, MAX_RTA_ITERATIONS 100 and MAX_BUSY_PERIOD_JOBS
1000). 42 tests, offline and deterministic, exits 0 under both
/usr/bin/python3 (3.9.6) and ~/.pyenv/versions/3.13.12/bin/python3.

## Compliance

- Standards referenced, not reproduced: RTCA DO-178C (Software
  Considerations in Airborne Systems and Equipment Certification)
  frames the avionics software lifecycle context in which the
  scheduling analysis artifact is recorded; the mathematics above is
  public science (Leung and Whitehead 1982; Audsley, Burns,
  Richardson and Wellings 1993; Tindell and Clark 1994), summary-only
  per standards-map.yaml. No standard text is reproduced verbatim.
- compliance: STANDARDS-REF, gated: false.
