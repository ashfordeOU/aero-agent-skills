---
name: shared-resource-access-control
description: "Use when you must account for shared-resource blocking in a fixed-priority avionics task set: assign each protected resource its priority ceiling from the tasks that lock it, compute the worst-case blocking time each task can suffer from lower-priority tasks under the priority ceiling protocol, and run the response-time analysis with the blocking term to decide schedulability. Produces the per-resource ceiling map, the per-task worst-case blocking times, the response times with blocking, and the schedulability verdict that gate an avionics task set design. Trigger: shared resource access control, priority ceiling protocol, priority inheritance, stack resource policy, worst case blocking, blocking time bound, schedulability with blocking."
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
  tags: [shared-resource-access-control, priority-ceiling-protocol, priority-inheritance, worst-case-blocking, stack-resource-policy, blocking-time-bound, schedulability-with-blocking]
  version: 0.1.0
  author: AeroSkills
---

# Shared-Resource Access Control (avionics/fsw/shared-resource-access-control)

Use when the fixed-priority periodic tasks of an avionics flight
software set share protected resources (buffers, registers, data
stores) and the schedulability analysis must include the blocking that
shared access can cause. Each task is a {name, C, T, priority} dict
with implicit deadline D = T; each lock is a {resource, task, cs}
dict. This leaf implements the priority ceiling protocol model in pure
Python stdlib: the ceiling of every resource, the worst-case blocking
each task can suffer from lower-priority tasks under the ceiling rule,
and the response-time analysis with the blocking term, ending in a
schedulability verdict. It pairs with avionics/fsw/real-time-scheduling
for the plain (C, T) feasibility of the same task set without shared
resources, and with avionics/fsw/cfs-architecture for the flight
software application context around the task set.

## Domain quick reference

- Task model: a task is a dict {name, C, T, priority} with implicit
  deadline D = T, C and T in one time unit; higher number means higher
  priority. A lock is a dict {resource, task, cs} where cs is the
  task's longest critical-section time on that resource, in the same
  time unit as C.
- Priority ceiling of a resource: the highest priority among the tasks
  that lock it. R1 locked by tasks of priority 3 and 1 has ceiling 3.
- Ceiling rule (paraphrased PCP bound): a task can be blocked by at
  most one lower-priority task's critical section, and only on a
  resource whose ceiling is at least the task's own priority. So the
  worst-case blocking of task i is the longest cs of any single
  lower-priority task over the resources whose ceiling clears
  priority_i; everything else contributes nothing.
- Response time with blocking (fixed point): R_i = C_i + B_i +
  sum over higher-priority tasks j of ceil(R_i / T_j) * C_j, iterated
  from C_i + B_i until the value stops changing, capped at 100
  iterations (MAX_RTA_ITERATIONS). The iteration is monotone
  non-decreasing, so on an overloaded set the capped value grows far
  past the period and the set reports infeasible.
- Feasibility: every converged response time must be at most its task
  period (within 1e-9 relative slack).
- Empty lock list identity: with no shared resources every blocking
  time is zero and the fixed point above is exactly the classic
  response-time analysis of the same task set.
- Scope notes: plain feasibility mathematics without the blocking term
  belongs to avionics/fsw/real-time-scheduling; WCET budgets are
  inputs, not outputs; this leaf does not model message or bus
  response windows.

## Workflow

1. Collect the task set and the lock set: tasks as a dict {name:
   {C, T, priority}} or a list of task dicts, locks as a list of
   {resource, task, cs} dicts, all in one time unit. Every C and T
   must be positive with C <= T, every cs non-negative, task names
   unique, and every lock must name a real task.
2. Assign ceilings first: priority_ceiling(tasks, locks) returns the
   per-resource ceiling map; resource_ceiling(tasks, locks, resource)
   gives one resource. A ceiling is only defined for resources that
   some task locks, so an empty lock list raises ValueError here.
3. Compute the per-task blocking: blocking_times(tasks, locks) applies
   the ceiling rule to every task, or worst_case_blocking(task, tasks,
   locks) for a single task. Expect the lowest-priority task to come
   out with zero blocking: nothing below it exists to block it.
4. Run the response time of a single task with
   response_time_with_blocking(task, tasks, locks): the fixed point
   starts at C + B and adds the higher-priority load.
5. Decide schedulability in one call:
   rta_with_blocking_feasibility(tasks, locks) returns the dict with
   keys blocking, response_times and feasible, where feasible is True
   iff every response time is at most its period.
6. Cross-check the resource-free baseline: the same call with an empty
   lock list must give zero blocking and the plain response-time
   values, the identity that separates the blocking effect from the
   preemption load.
7. Record the ceiling map, blocking times, response times and verdict
   in the scheduling analysis artifact of the certification package;
   re-run the contract test after any change to the task or lock set.

## Worked example

Anchor set: T1 {C 1, T 5, priority 3}, T2 {C 2, T 10, priority 2},
T3 {C 3, T 20, priority 1}; locks R1 used by T1 (cs 0.5) and T3
(cs 0.6), R2 used by T2 (cs 0.8) and T3 (cs 0.7), times in ms.

- Ceilings: priority_ceiling returns R1 -> 3 (max of priorities 3 and
  1) and R2 -> 2 (max of priorities 2 and 1); resource_ceiling agrees
  per resource.
- Blocking (module output): T1 0.6, T2 0.7, T3 0.0. T1 is blocked by
  T3's 0.6 ms section on R1 (ceiling 3 clears priority 3); T3's 0.7
  and T2's 0.8 on R2 do not qualify because ceiling 2 is below T1's
  priority 3. T2 is blocked by T3's 0.7 on R2 (ceiling 2 clears
  priority 2). T3 has no lower-priority task, so 0.0.
- Response times with blocking (module output): T1 1.6 = 1 + 0.6,
  T2 3.7 = 2 + 0.7 + 1 preemption from T1, T3 7.0 = 3 + 2 + 2
  preemptions from T1 and T2. Every value is at most its period, so
  rta_with_blocking_feasibility returns feasible True.
- Empty lock list (module output): blocking all zero and the response
  times collapse to the plain analysis T1 1.0, T2 3.0, T3 7.0. Note
  the T3 fixed point visits 3, then 6, and converges at 7.0 in both
  runs: with zero blocking the with-resource and resource-free
  analyses are the same computation, and the identity holds on the
  converged value.

## Verification

- Confirm priority_ceiling on the anchor returns R1 3 and R2 2, and
  that resource_ceiling matches per resource.
- Confirm the blocking truth table: worst_case_blocking gives T1 0.6,
  T2 0.7, T3 0.0, and blocking_times agrees.
- Confirm the fixed-point response times converge to T1 1.6, T2 3.7,
  T3 7.0 within 1e-9, all within their periods, feasible True.
- Confirm the empty-lock identity: blocking all zero, response times
  equal the plain analysis (T1 1.0, T2 3.0, T3 7.0).
- Confirm the ceiling-rule boundary: a lower-priority task locking a
  resource whose ceiling sits below the task's priority contributes no
  blocking, and equal-priority tasks neither preempt nor block.
- Confirm that adding the blocking term never shrinks a response time
  and can flip a feasible set infeasible.
- Confirm ValueError rejection of C <= 0, T <= 0, C > T, cs < 0,
  duplicate task names, unknown task references, an empty task set,
  and an empty lock list for the ceiling functions.
- Run the deterministic contract test offline: python3
  scripts/test_shared_resource_access_control.py (35 tests).

## Related leaves

- avionics/fsw/real-time-scheduling: the plain (C, T) feasibility of
  the same periodic task set with no shared-resource blocking term;
  run it on the resource-free baseline of this leaf's model.
- avionics/fsw/cfs-architecture: the flight software application
  layout and inter-application messaging context that carries the task
  and resource sets this leaf analyzes.
- avionics/fsw/fprime-component: the component-based flight software
  architecture whose ports and queues become protected resources in a
  task set model.

## Pitfalls

- Reading a ceiling as a per-task quantity: the ceiling attaches to
  the resource and equals the highest priority among every task that
  locks it, so a resource used by a high-priority task keeps a high
  ceiling even when a low-priority task is its only other user.
- Summing every lower-priority critical section: under the priority
  ceiling protocol the task is blocked by at most one lower-priority
  section, so blocking is a max over qualifying sections, not a sum -
  adding T2's 0.8 and T3's sections together overstates T1's blocking
  (0.6, not 1.5+).
- Applying the ceiling rule to the wrong resources: only sections on
  resources whose ceiling is at least the task's priority count, which
  is why T3's 0.7 on R2 (ceiling 2) never blocks T1 (priority 3)
  despite T3 being lower priority.
- Dropping the blocking term from the fixed point: the iteration must
  start from C + B and add B on every pass, so the response time with
  blocking never dips below the resource-free value (T1 1.6 against
  1.0).
- Reporting a first iterate as the converged response time: T3's plain
  analysis visits 3, then 6, then converges at 7.0, and stopping at
  the first crossing understates the response time and can hide a
  deadline miss.
- Mixing priority direction or time units: higher number is higher
  priority here (the opposite of the rate-monotonic convention in the
  sibling leaf), and C, T and cs must share one time unit or every
  ceil term corrupts the fixed point.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline, no
network, exits 0):

    python3 scripts/test_shared_resource_access_control.py

The test covers the anchor ceilings R1 3 / R2 2, the blocking truth
table 0.6 / 0.7 / 0.0 with the ceiling-rule boundary and the
equal-priority case, the fixed-point response times 1.6 / 3.7 / 7.0
within 1e-9, the empty-lock identity against the plain analysis, the
blocking-monotonicity property, blocking-driven infeasibility, the
exact result-dict keys, single-task closed forms, ValueError rejection
of every non-physical input (C <= 0, T <= 0, C > T, cs < 0, duplicate
task names, unknown task and resource references, empty task set,
empty lock list for the ceiling functions, malformed and boolean
entries), and run-to-run determinism.

## Compliance

- Standards referenced, not reproduced: DO-178C (avionics software
  lifecycle, including the scheduling and resource-sharing analysis of
  the software task set) is listed reference-only per standards-map
  yaml; the ceiling and blocking mathematics above is standard public
  real-time systems methodology, summary-only.
- The inter-application messaging interfaces of the flight software
  context belong to avionics/fsw/cfs-architecture, not to this leaf.
- compliance: STANDARDS-REF, gated: false.
