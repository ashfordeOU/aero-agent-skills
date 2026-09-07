# Wave-45 leaf spec: deadline-monotonic-scheduling (avionics, fsw pack)

- Path: skills/avionics/fsw/deadline-monotonic-scheduling/
- Pack: fsw (present siblings avionics/fsw/real-time-scheduling,
  avionics/fsw/shared-resource-access-control, avionics/fsw/aperiodic-
  server-scheduling, avionics/fsw/cfs-architecture, avionics/fsw/
  fprime-component; adjacent fences avionics/ima/ima-partitioning
  (partition window schedules and port latency) and avionics/data-bus/
  mil-std-1553 (bus command/response windows) own no task-level deadline
  arithmetic). AV 45 probe receipt task-0 rank 1 GO; 0 owners verified
  whole-tree.
- Claim fences (quoted from the sibling frontmatter and bodies at prep,
  re-verified at spec time; the nearest owners fence out per-task
  deadline analysis, which is the exact gap this leaf closes):
  - real-time-scheduling (this pack) is the IMPLICIT-DEADLINE fence:
    its frontmatter description reads "Use when you must decide the
    offline schedulability of a periodic hard-real-time task set: compute
    the processor utilization of (C, T) tasks with implicit deadlines,
    apply the Liu-Layland utilization bound for rate-monotonic
    fixed-priority scheduling, run the exact iterative response-time
    analysis task by task, and test earliest-deadline-first feasibility
    with the full-utilization condition". Every task in that leaf is a
    (C, T) pair with D = T and RM priority by period. Its scope note is
    explicit (lines 69-73): "WCET estimation, jitter and blocking
    analysis, and arbitrary-deadline response-time extensions are out of
    scope; the model is the classic implicit-deadline periodic task
    set." and its pitfalls routing repeats it (lines 190-192): "Routing
    adjacent timing domains here: WCET estimation, jitter and blocking
    analysis, arbitrary-deadline extensions, ARINC 653 partition
    schedule windows (ima/ima-partitioning), and bus response windows
    (data-bus/mil-std-1553) are not this leaf's classic implicit-
    deadline periodic model." There is no per-task D, no D != T
    machinery, no release jitter and no deadline-ordered priority
    anywhere in its model, workflow, worked examples (sets A, B, C, D
    are all implicit-deadline) or test contract. The gap this leaf
    closes: a task set whose 40 ms task must finish within 25 ms, or
    whose 30 ms task tolerates a 60 ms relative deadline, cannot be
    admitted by the sibling at all, because its model has no per-task
    deadline slot and no deadline-based priority order.
  - shared-resource-access-control (this pack) is the PCP-BLOCKING-
    ONLY fence: its frontmatter description reads "Use when you must
    account for shared-resource blocking in a fixed-priority avionics
    task set: assign each protected resource its priority ceiling from
    the tasks that lock it, compute the worst-case blocking time each
    task can suffer from lower-priority tasks under the priority ceiling
    protocol, and run the response-time analysis with the blocking term
    to decide schedulability". Its task model is dicts "with implicit
    deadline D = T" (body line 27), and its scope note (lines 63-64)
    routes plain feasibility away: "plain feasibility mathematics
    without the blocking term belongs to avionics/fsw/real-time-
    scheduling; WCET budgets are inputs, not outputs". The blocking
    term B_i it adds to the fixed point is a shared-resource ceiling
    effect; no deadline other than D = T exists in its model.
  - aperiodic-server-scheduling (this pack, wave 44) is the SERVER
    fence: its frontmatter description requires "every periodic task
    keeps its implicit deadline and the budget completes within its
    period"; its server budget (C_s, T_s) is inserted beside an
    implicit-deadline periodic set, and it carries no per-task deadline
    or release-jitter term.
  - Whole-tree greps at prep (probe receipt gate (a), grep -c 0 / empty
    per token across skills/ and eval/): the tokens deadline[- ]monotonic,
    constrained[- ]deadline, audsley, release[- ]jitter and
    activation[- ]jitter return ZERO matches anywhere in the skills tree
    or in eval/hit1-corpus.yaml and every eval/*.yaml fragment; the
    token arbitrary[- ]deadline has exactly 1 hit, which is the
    real-time-scheduling fence line quoted above (a fence, not an
    owner). The corpus scan for deadline-monotonic, constrained-deadline,
    shorter-deadline, relative-deadline, release-jitter, per-task-
    deadline and jitter-extended finds zero tasks. GENUINE
    avionics/fsw gap (probe receipt task-0, verified zero-owner, GO
    rank 1): no leaf owns the D_i != T_i response-time analysis that the
    periodic-only sibling explicitly fences out.
- Standards id: do-178c (RTCA DO-178C, Software Considerations in
  Airborne Systems and Equipment Certification; the avionics software
  lifecycle context in which the scheduling analysis artifact is
  recorded), reference-only and present in standards-map.yaml (grep
  'id: do-178c' at line 61, re-verified at spec time). Ledger Standard:
  do-178c.
- Family: avionics

## Claim

Decide the offline fixed-priority schedulability of an avionics flight
software task set whose per-task relative deadlines D_i are not the
implicit D_i = T_i of the pack sibling. Each task is a dict
{name, C, T, D, J} in one time unit with worst-case execution C,
period T, relative deadline D and optional release jitter J (default
0). Assign priorities by deadline-monotonic order: shorter deadline,
higher priority, equal deadlines broken by input order, the
fixed-priority assignment that Leung and Whitehead (1982) proved
optimal for constrained deadlines. Then run the exact jitter-aware
fixed-point response-time iteration task by task, converged against
each task's own deadline: R_i = C_i + sum over higher-priority j of
ceil((R_i + J_j) / T_j) * C_j, the classic fixed point with the Tindell
and Clark (1994) release-jitter term in the interference count. A
converged response at most D_i admits the task under deadline-monotonic
priorities. Cover the full deadline range: constrained deadlines
(D <= T) need only the first-job fixed point, whose convergence is
exact and sufficient; arbitrary deadlines (D > T) additionally run the
Audsley, Burns, Richardson and Wellings (1993) busy-period job scan
when the first-job completion exceeds T_i and later jobs queue, taking
the worst response w_i(q) - q * T_i over the busy period as the exact
response time. The iteration is monotone non-decreasing, so an iterate
that crosses its per-job bound (q * T_i + D_i for job q) can never
converge under the deadline and the task reports None (divergence);
the same None reports a busy period that never ends (an
over-subscribed set). Produces the deadline-monotonic priority order,
the per-task worst-case response times against the per-task deadlines,
the release-jitter recomputation when a higher-priority task carries
activation jitter, and the feasible verdict for the whole set. Does NOT
do: the plain implicit-deadline feasibility verdicts of a periodic set
(utilization, Liu-Layland bound, RM and EDF verdicts, classic RTA with
D = T, avionics/fsw/real-time-scheduling owns those); priority-ceiling
or priority-inheritance blocking terms in the fixed point
(avionics/fsw/shared-resource-access-control); polling, deferrable or
sporadic server budgets for aperiodic jobs, and the budget insertion
and aperiodic response bounds
(avionics/fsw/aperiodic-server-scheduling); partition window schedules
and sampling or queuing port latencies (avionics/ima/ima-partitioning);
software bus routing and cyclic rate group dispatch layout
(avionics/fsw/cfs-architecture, avionics/fsw/fprime-component); bus
command/response windows (avionics/data-bus/mil-std-1553). Priority
assignment is the simple deadline-monotonic order, not a search over
assignments; offsets and phased (non-synchronous) releases are out of
scope; WCET budgets C_i are inputs, never estimated; the model is the
single-processor fixed-priority preemptive schedule, one time unit per
task set, all tasks released at the common critical instant.

## Model (implement exactly)

Pure stdlib, math.ceil only, closed form. Module constants:
MAX_RTA_ITERATIONS = 100 (the per-completion fixed-point safety cap; a
solve that still moves after 100 passes reports divergence),
MAX_BUSY_PERIOD_JOBS = 1000 (the cap on the arbitrary-deadline
busy-period job scan), CONVERGENCE_TOL = 1e-12 (an iterate that repeats
within this tolerance has converged).

Task dict shape (validated identically by every function): {name, C,
T, D, J}, name optional, J optional and defaulting to 0.0, all values
in one time unit. Every function rejects, with ValueError, an empty
task list, a malformed entry, a missing C/T/D key, a boolean or
non-positive C, T or D, a boolean or negative J, and a non-numeric
value.

Defining relations (pin these exactly; every function derives from
them):
- Deadline-monotonic priority order: the tasks sorted by D ascending,
  stable, so shorter deadline means higher priority (list index 0) and
  equal deadlines keep their input order. The analysis functions
  require the list to already be in this order (non-decreasing D) and
  raise ValueError otherwise; dm_priority_order produces it. For a
  constrained-deadline set this assignment is optimal among fixed
  priorities (Leung and Whitehead, "On the Complexity of Fixed-Priority
  Scheduling of Periodic Real-Time Tasks", Performance Evaluation 2(4),
  1982).
- Busy-window completion of job q of task i (Audsley, Burns,
  Richardson and Wellings, "Applying New Scheduling Theory to Static
  Priority Pre-emptive Scheduling", Software Engineering Journal, 1993,
  response-time analysis with convergence rules; the q-job busy-period
  form is the standard arbitrary-deadline extension of Lehoczky's busy
  period):
  w_i(q) = (q + 1) * C_i + sum over j in hp(i) of
  ceil((w_i(q) + J_j) / T_j) * C_j, where hp(i) is the set of
  higher-priority tasks (lower list indices) and J_j is the release
  jitter of task j (Tindell and Clark, 1994, jitter term in the fixed
  point). For q = 0 this is exactly the pinned classic fixed point
  R_i = C_i + sum over j in hp(i) of ceil((R_i + J_j) / T_j) * C_j.
  The map is monotone non-decreasing in w, and the solve iterates
  w <- (q + 1) * C_i + sum ... from w = (q + 1) * C_i until an iterate
  repeats within CONVERGENCE_TOL.
- Convergence rule (Audsley et al. 1993): job q of task i is released
  at q * T_i and completes at w_i(q), so its response is
  w_i(q) - q * T_i and it must satisfy w_i(q) <= q * T_i + D_i. The
  sequence of iterates is monotone non-decreasing, so an iterate past
  that per-job bound can never converge under the deadline: the solve
  reports None. A solve that hits MAX_RTA_ITERATIONS without repeating
  also reports None. This is the sibling leaves' per-period
  divergence rule with the per-task deadline in place of the period.
- Constrained deadlines (D_i <= T_i): the converged first-job
  completion w_i(0) is the exact worst-case response time: every later
  job completes before its successor is released (w_i(0) <= D_i <= T_i
  implies the busy periods of successive jobs do not overlap), so no
  job scan is needed. Feasible iff w_i(0) <= D_i.
- Arbitrary deadlines (D_i > T_i): when the first-job completion
  w_i(0) <= T_i the busy periods of successive jobs do not overlap and
  w_i(0) is again the exact worst-case response. When w_i(0) > T_i,
  job q + 1 is released while job q is still queued and later jobs can
  be the worst: the exact response time is the maximum of
  w_i(q) - q * T_i over the busy period, scanned q = 1, 2, ... while
  w_i(q) > (q + 1) * T_i (job q still running at the next release) and
  stopped at the first q with w_i(q) <= (q + 1) * T_i (the busy period
  ended; later jobs repeat the pattern). A job response past D_i, or a
  scan past MAX_BUSY_PERIOD_JOBS (the busy period of an
  over-subscribed set never ends), reports None.
- Release jitter: J_j of a higher-priority task delays its releases by
  up to J_j and enters only the interference counts of lower-priority
  tasks through ceil((w + J_j) / T_j). A task's own J_i does not enter
  its own equation: its response and its deadline are both measured
  from its actual (jittered) release, matching the pinned iteration
  whose jitter terms range over j in hp(i) only. Release jitter can
  therefore inflate lower-priority responses by whole preemptions and
  can push a first-job completion past T_i, opening the queueing
  regime, but it never changes the jittered task's own response.
- Utilization: U = sum of C_i / T_i, reported for context; it is not a
  verdict (deadlines differ from periods), but U > 1 always ends in
  None through the never-ending busy period.

Functions:
- utilization(tasks) -> float
  Sum of C / T over the task list (any order). ValueErrors of the task
  shape above.
- dm_priority_order(tasks) -> list of task dicts
  The tasks with J defaulted, stably sorted by D ascending (shorter
  deadline higher priority; equal deadlines keep input order). Returns
  copies with all five keys present. ValueErrors of the task shape
  above.
- response_time(tasks, index) -> float or None
  Exact worst-case response time of task `index` of a
  deadline-monotonic-ordered list, in the same time unit: the converged
  first-job completion for constrained deadlines (D <= T), and for
  arbitrary deadlines (D > T) the first-job completion when it stays
  within T_i or the maximum job response over the busy-period scan
  when jobs queue. None when the first-job completion or any queued
  job response crosses D_i, when a solve fails to converge within
  MAX_RTA_ITERATIONS, or when the busy-period scan exceeds
  MAX_BUSY_PERIOD_JOBS. ValueError when the list is empty or malformed,
  when the deadlines are not in non-decreasing (deadline-monotonic)
  order, or when index is outside [0, len(tasks)).
- dm_response_times(tasks) -> dict
  Returns {"names", "response_times" (one float or None per task, in
  priority order), "feasible" (True only when every response converged
  and is at most its own deadline), "utilization"}.
  ValueErrors of the task shape and of a non-deadline-monotonic order.
- feasible(tasks) -> bool
  Convenience: dm_response_times(tasks)["feasible"]. Same ValueErrors.

Identities to test (closed form, exact; checkable without the builder
module):
- Single task: response_time([{C, T, D}], 0) = C exactly, feasible iff
  C <= D; C > D reports None (the first iterate itself crosses D).
- Implicit-deadline equivalence: when every D_i = T_i and every J_i =
  0, deadline-monotonic order coincides with rate-monotonic order and
  this leaf's responses are exactly the pack sibling's classic
  response-time results on the same sets: real anchors [1.0, 2.0, 6.0]
  on [(1, 3), (1, 4), (2, 8)], [1.0, 2.0, 4.0] on [(1, 5), (1, 6),
  (2, 10)], and [2.0, None, None] on the over-subscribed [(2, 3),
  (2, 5), (2, 7)] whose second iterate crosses its period.
- Ordering is the analysis: two tasks whose period order and deadline
  order disagree (a 40 ms-period task with D 25 against a 30 ms-period
  task with D 60) are feasible in deadline order and infeasible in
  period order, exact anchors 9.0 vs None below.
- Constrained-deadline admission: a converged response at most D_i is
  the exact test; response equals the classic fixed point R_i = C_i +
  sum over hp of ceil((R_i + J_j) / T_j) * C_j converged from below.
- Release-jitter inflation: raising J_0 of the highest-priority task
  from 0 to 4 ms raises a lower task's response by exactly C_0 * k
  when the count ceil((R + J_0) / T_0) gains k releases at the
  converged R; real anchor 2.0 ms (one extra preemption, k = 1) and
  2.0 ms (the queueing-regime opening) below.
- Arbitrary-deadline worst-job identity: when w_i(0) <= T_i the
  response is w_i(0); when w_i(0) > T_i the response is the maximum of
  w_i(q) - q * T_i over the busy period, and a queued job can be
  strictly the worst (real anchor 34.0 > first-job 33.0 below); the
  scan stops at the first q with w_i(q) <= (q + 1) * T_i.
- Utilization adds: U = 0.95 on the worked set A (2/10 + 1/20 + 4/40 +
  18/30); an over-subscribed variant (U 1.083333 > 1) reports None for
  the arbitrary-deadline task through the never-ending busy period.
- ValueErrors across the module: empty list, non-DM order, index out of
  range, missing D key, C = 0, J negative, boolean and non-numeric
  values.
- Determinism; identical outputs run to run; no randomness anywhere;
  no imports beyond math.ceil; MAX_RTA_ITERATIONS fixed at 100 and
  MAX_BUSY_PERIOD_JOBS at 1000.

## Worked example

Task set A, four avionics fsw processes in ms, deadline-monotonic order
already (deadlines 10, 20, 25, 60 ms ascending):
- flight-control: C 2.0, T 10.0, D 10.0, J 4.0 (the highest-priority
  task carries the 4 ms release jitter; its own response is untouched
  by its jitter, its releases inflate every lower task);
- guidance: C 1.0, T 20.0, D 20.0 (implicit deadline);
- navigation: C 4.0, T 40.0, D 25.0 (constrained deadline 25 ms
  shorter than its 40 ms period, the query-1 headline parameter);
- mission-recording: C 18.0, T 30.0, D 60.0 (arbitrary relative
  deadline 60 ms beyond its 30 ms period, the query-2 headline
  parameter).

All values below are REAL outputs of the prep anchor
/tmp/w45spec/anchor_deadline_monotonic_scheduling.py (pure stdlib,
math.ceil only, closed form, exit 0, no RNG), run once and quoted as
printed:

- Deadline-monotonic order and its contrast with period order:
  dm_priority_order(A) keeps the list as given (D ascending 10, 20, 25,
  60), while the periods ascend 10, 20, 30, 40: the navigation task
  (T 40) outranks the mission-recording task (T 30) because its 25 ms
  deadline is shorter, the opposite of a period-ordered assignment.
- Full DM analysis with jitter: dm_response_times(A) returns responses
  [2.000000, 3.000000, 9.000000, 32.000000] ms against deadlines
  [10, 20, 25, 60] ms, utilization 0.950000, feasible True: every task
  closes inside its own deadline.
- Constrained-deadline task and the jitter cost: response_time(A, 2) =
  9.000000 ms against D 25 ms for navigation; with J_0 set to 0 the
  same task closes at 7.000000 ms, so the 4 ms release jitter on
  flight-control costs navigation exactly 2.000000 ms, one extra
  flight-control preemption (C_0 = 2.0) counted by the jitter term
  ceil((R + 4) / 10) at the converged R = 9.
- Arbitrary-deadline task, jittered: response_time(A, 3) = 32.000000
  ms against D 60 ms for mission-recording, and the first-job
  completion w(0) = 32.000000 ms exceeds T = 30 ms, so the queueing
  regime is entered and the busy-period scan runs: completions
  w(0..3) = 32.000000, 62.000000, 91.000000, 114.000000 ms with job
  responses 32.000000, 32.000000, 31.000000, 24.000000 ms, stopping at
  job 3 because w(3) = 114.000000 <= 4 * T = 120.000000 ends the busy
  period; the exact worst-case response is the max 32.000000 ms.
  Without the jitter (J_0 = 0) the first-job completion is exactly
  30.000000 ms, at its period, so no job ever queues and the response
  is 30.000000 ms: the 4 ms jitter on the highest-priority task is what
  pushes mission-recording into the queueing regime, and the
  recomputation with and without it is the release-jitter identity of
  the query-2 scenario.
- Queued job strictly the worst (navigation C = 5 variant, still D 25
  <= T 40): response_time(variant, 2) = 10.000000 ms; the
  mission-recording busy-period completions become 33.000000,
  64.000000, 94.000000, 119.000000 ms with responses 33.000000,
  34.000000, 34.000000, 29.000000 ms, so the worst-case response is
  34.000000 ms, held by the queued first and second jobs, strictly
  above the first-job completion 33.000000 ms: the exact
  arbitrary-deadline answer requires the job scan, not the first-job
  fixed point alone.
- Ordering is the analysis (RM-order diagnostic on set A, priorities
  by period 10, 20, 30, 40 instead of by deadline): flight-control
  2.000000, guidance 3.000000, mission-recording 26.000000 ms all
  converge, but navigation now sits below mission-recording and its
  iterates run 25.000000 then 30.000000, which crosses D 25 ms on the
  second pass, so navigation reports None and the period-ordered set
  is infeasible. The same four tasks in deadline order close at
  [2.0, 3.0, 9.0, 32.0] ms; the deadline-monotonic assignment is the
  difference between a feasible and an infeasible avionics set.
- Implicit-deadline identity (D = T, J = 0 everywhere): the pack
  sibling's worked sets reproduce its published results exactly,
  [1.000000, 2.000000, 6.000000] on [(1, 3), (1, 4), (2, 8)] and
  [1.000000, 2.000000, 4.000000] on [(1, 5), (1, 6), (2, 10)], both
  feasible True, and [2.000000, None, None] on the over-subscribed
  [(2, 3), (2, 5), (2, 7)], feasible False.
- Over-subscribed arbitrary-deadline variant (mission-recording C =
  22.0): utilization 1.083333 > 1, and dm_response_times reports
  [2.000000, 3.000000, 9.000000, None], feasible False: the busy
  period of the arbitrary-deadline task never ends and a queued job's
  response crosses D 60 ms, the None verdict.
- Single-task closed form: response_time of {(3, 10, D 7)} is
  3.000000 = C, feasible; {(3, 10, D 2)} (C > D) reports None.
- ValueErrors with real messages: an empty list raises "task list must
  be a non-empty list"; a list not in deadline-monotonic order raises
  "tasks must be in deadline-monotonic priority order (non-decreasing
  D); sort with dm_priority_order first"; C = 0 raises "C must be a
  positive number, got 0.0"; J = -1 raises "J must be a non-negative
  number, got -1.0"; a missing D raises "task missing key(s) D"; index
  4 on a 4-task list raises "index out of range".

Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of
/tmp/w45spec/anchor_deadline_monotonic_scheduling.py (stdlib math,
closed form, exit 0, no randomness).

## Validation list (contract test must include)

1. Worked set A asserts within 1e-6 relative: dm_response_times(A)
   gives response_times [2.0, 3.0, 9.0, 32.0] (each within 1e-6
   relative of the anchor), feasible True, utilization 0.95 within
   1e-9; each response sits at most its own deadline [10, 20, 25, 60].
2. Constrained-deadline identity: response_time(A, 2) = 9.0 within
   1e-9 with J_0 = 4 and = 7.0 within 1e-9 with J_0 = 0, and the
   difference 9.0 - 7.0 = 2.0 within 1e-9 equals C_0 (one extra
   preemption from the jitter term ceil((R + 4) / 10) at the converged
   R).
3. Arbitrary-deadline scan of set A: response_time(A, 3) = 32.0 within
   1e-9; the busy-period completions w(0..3) = 32.0, 62.0, 91.0, 114.0
   each within 1e-9 with job responses 32.0, 32.0, 31.0, 24.0, and
   114.0 <= 120.0 terminates the scan; the no-jitter variant closes at
   30.0 within 1e-9 (w(0) = T, no queueing).
4. Queued-job-worst variant (navigation C = 5): response_time(variant,
   2) = 10.0 within 1e-9; mission-recording completions 33.0, 64.0,
   94.0, 119.0 within 1e-9 each with responses 33.0, 34.0, 34.0, 29.0,
   max 34.0 within 1e-9, strictly above the first-job 33.0.
5. Ordering identity: dm_response_times on A reordered by period
   (flight-control, guidance, mission-recording, navigation) reports
   None for navigation (its second iterate 30.0 crosses D 25.0) and
   feasible False, where the deadline-monotonic order of the same tasks
   is feasible with navigation at 9.0 within 1e-9.
6. Implicit-deadline equivalence (D = T, J = 0): [1.0, 2.0, 6.0] on
   [(1, 3), (1, 4), (2, 8)], [1.0, 2.0, 4.0] on [(1, 5), (1, 6),
   (2, 10)], both feasible True, each within 1e-9; [(2, 3), (2, 5),
   (2, 7)] gives [2.0, None, None], feasible False.
7. Single-task closed forms: response_time([{C 3, T 10, D 7}], 0) =
   3.0 within 1e-9 with feasible True; the C > D shape
   [{C 3, T 10, D 2}] reports None; doubling C doubles the single-task
   response only when it stays within D (R = C exactly either way).
8. Over-subscribed set: the C 22 variant reports utilization
   1.0833333333333333 (1.083333 within 1e-5), responses [2.0, 3.0,
   9.0, None] and feasible False; the busy-period job scan terminates
   through a queued job response past D 60, not through an infinite
   loop (MAX_BUSY_PERIOD_JOBS = 1000 cap exercised only on divergence).
9. dm_priority_order stability: equal deadlines keep input order
   (stable sort); the returned order is non-decreasing in D; the
   function never mutates its input tasks.
10. All ValueErrors enumerated in the identity list raise from the
    named public function: empty list, missing key, boolean or
    non-positive C/T/D, negative or boolean J, non-numeric value,
    non-deadline-monotonic order (from response_time,
    dm_response_times and feasible), and index outside
    [0, len(tasks)) (from response_time).
11. Determinism: identical outputs run to run; no randomness anywhere;
    no imports beyond math.ceil; module constants MAX_RTA_ITERATIONS =
    100 and MAX_BUSY_PERIOD_JOBS = 1000. No exact-float equality on
    computed sums; use assertAlmostEqual/math.isclose everywhere.
12. Run the deterministic contract test offline (no network); it
    exits 0. Test passes under BOTH interpreters
    (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3).

## Corpus fragment (eval/hit1-wave45-deadline-monotonic-scheduling.yaml)

Query 1 (copy verbatim):
  "check the deadline-monotonic-scheduling feasibility of the avionics
  process set where the 40 ms task carries a constrained-deadline of 25
  ms shorter than its period: order the priorities by the shorter
  deadline and run the fixed-priority response-time iteration against
  each per-task deadline"
  intent: "avionics/fsw; deadline-monotonic priority assignment by
  shorter relative deadline and the fixed-priority response-time
  iteration converged against each per-task deadline, for a 40 ms
  process whose constrained deadline of 25 ms is shorter than its
  period"
  expected_skill: "avionics/fsw/deadline-monotonic-scheduling"
Query 2 (copy verbatim):
  "test the arbitrary-deadline response time of the process whose 60 ms
  relative deadline exceeds its 30 ms period under deadline-monotonic
  priority assignment, then recompute the worst-case response with a 4
  ms release-jitter on the highest priority task"
  intent: "avionics/fsw; arbitrary-deadline (D > T) response-time
  analysis under deadline-monotonic priority assignment, including the
  busy-period job scan, and the release-jitter recomputation of the
  worst-case response when the highest-priority task carries 4 ms
  release jitter"
  expected_skill: "avionics/fsw/deadline-monotonic-scheduling"
Task ids: w45-deadline-monotonic-scheduling-1 and -2. Prep grep (run
at spec time by the probe): each of the tokens deadline-monotonic,
constrained-deadline, arbitrary-deadline, release-jitter,
shorter-deadline, relative-deadline, per-task-deadline and
jitter-extended returns ZERO matches in eval/hit1-corpus.yaml and in
every eval/*.yaml fragment, and the skills tree carries them nowhere
except the real-time-scheduling fence lines quoted above, so the
queries are collision-free; the sibling tasks route on periodic
utilization, bound and implicit-deadline response language
(real-time-scheduling), ceiling and blocking language
(shared-resource-access-control) and server-budget and event-service
language (aperiodic-server-scheduling), none of which carry per-task
deadline or release-jitter content. Add a fence line to
real-time-scheduling at build time pointing arbitrary-deadline
extensions and per-task deadline analysis here (aperiodic-server-
scheduling precedent).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must decide the fixed-priority
schedulability of an avionics flight software task set whose per-task
relative deadlines are not the implicit period:" and include the
outputs in the Claim order (deadline-monotonic priority order,
per-task worst-case response times against the per-task deadlines,
release-jitter recomputation, feasible verdict, divergence verdict).
First tag: deadline-monotonic-scheduling. Additional tags EXACTLY as
the probe receipt gate (f) lists them, nothing else:
constrained-deadline-rta, arbitrary-deadline-rta, release-jitter-rta,
dm-priority-assignment, shorter-deadline-order. NEVER single generic
words (deadline, jitter, response, priority, scheduling, feasibility,
task, analysis, utilization) and never any sibling token below. 50-150
words, <=1000 chars, no em dash, no content-policy sweep term (the
banned word from the builder kit), action verb present. Recommended
wording (138 words, 991 chars, verified at spec time):
"Use when you must decide the fixed-priority schedulability of an
avionics flight software task set whose per-task relative deadlines are
not the implicit period: order the tasks by deadline-monotonic priority
assignment so the shorter deadline ranks higher, run the exact
jitter-aware fixed-point response-time iteration against each task's
own deadline, and cover constrained deadlines (D no greater than T) and
arbitrary deadlines (D beyond T) with the busy-period job scan when a
queued job can be the worst. Produces the deadline-monotonic priority
order, the per-task worst-case response times against the per-task
deadlines, the release-jitter recomputation when a higher-priority task
carries release jitter, the feasible verdict for the whole set, and the
divergence verdict when an iterate or a queued job's response crosses
its deadline. Trigger: deadline monotonic scheduling, constrained
deadline, arbitrary deadline, release jitter, relative deadline,
shorter deadline priority."

FORBIDDEN TOKENS (belong to siblings): liu-layland-bound,
rate-monotonic-scheduling, earliest-deadline-first, cpu-utilization,
fixed-priority-scheduling, response-time-analysis, wcet-estimation and
any query whose only content is an implicit-deadline schedulability
verdict with no per-task deadline or release jitter (real-time-
scheduling); priority-ceiling-protocol, priority-inheritance,
worst-case-blocking, stack-resource-policy, blocking-time-bound,
schedulability-with-blocking (shared-resource-access-control);
sporadic-server, deferrable-server, polling-server, server-capacity,
aperiodic-response-bound, server-budget (aperiodic-server-scheduling);
arinc-653, major-frame, partition-configuration-table, sampling-port,
queuing-port, inter-partition-communication, health-monitoring
(ima-partitioning); software-bus, publish-subscribe, cfe, osal,
rate-group, command-opcode, telemetry-channel (cfs-architecture,
fprime-component). Never the bare words deadline, jitter, response,
priority, scheduling, feasibility, task, analysis or utilization as
standalone tags.
