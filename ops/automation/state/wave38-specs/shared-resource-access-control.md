# Wave-38 leaf spec: shared-resource-access-control (avionics, fsw pack)

- Path: skills/avionics/fsw/shared-resource-access-control/
- Pack: fsw. Closest siblings: real-time-scheduling (offline schedulability
  of periodic (C, T) tasks with implicit deadlines: RM utilization bound,
  exact iterative response-time analysis, EDF feasibility - pure computation
  with NO shared-resource blocking term; its SKILL.md scope explicitly
  disclaims "WCET estimation, jitter and blocking analysis"), cfs-
  architecture (OSAL semaphore API prose), fprime-component. Whole-tree
  grep: "priority ceiling", "priority inheritance", "priority inversion",
  "stack resource", "blocking time" = ZERO owning hits in any leaf (real-
  time-scheduling matches none of these; it has no blocking math).
  ZERO owners. GENUINE AV gap (fresh probe).
- Standards id: do-178c (reference-only; sibling pattern in the fsw pack -
  the real-time scheduling of avionics software under DO-178C context).
  Ledger Standard: do-178c.
- Family: avionics

## Claim

Compute the shared-resource access control for a fixed-priority periodic
task set that shares protected resources: assign each resource its
priority ceiling from the set of tasks that lock it, compute the worst-case
blocking time each task can suffer from lower-priority tasks under the
priority ceiling protocol, and run the response-time analysis with the
blocking term to decide schedulability. Produces the per-resource ceiling
map, the per-task worst-case blocking times, the response times with
blocking, and the schedulability verdict that gate an avionics task set
design. Does NOT do: the plain (C, T) utilization, RM-bound and RTA
without resources (real-time-scheduling); WCET estimation; OSAL API
semaphore use (cfs-architecture).

## Model (implement exactly)

Conventions: a task is a dict {name, C, T, priority} with implicit
deadline D = T (C and T in the same time unit, higher number = higher
priority). A resource lock is a dict {resource, task, cs} where cs is the
task's longest critical-section time on that resource. The priority
ceiling of a resource is the highest priority among the tasks that lock
it.

Functions (pure stdlib):
- priority_ceiling(locks) -> dict resource -> ceiling priority. ValueError
  on an empty lock list or a lock referencing an unknown task.
- resource_ceiling(locks, resource) -> int.
- worst_case_blocking(task, locks) -> float: under the priority ceiling
  protocol the task can be blocked by at most one lower-priority task's
  critical section; compute the longest cs of any lower-priority task that
  locks a resource whose ceiling is >= the task's priority (the ceiling
  rule). Documented deterministic model (paraphrased PCP bound).
- blocking_times(tasks, locks) -> dict task name -> worst-case blocking.
- response_time_with_blocking(task, tasks, locks) -> float: fixed-point
  R_i = C_i + B_i + sum over higher-priority tasks j of
  ceil(R_i / T_j) * C_j; iterate from C_i + B_i until convergence or a
  cap of 100 iterations.
- rta_with_blocking_feasibility(tasks, locks) -> dict {blocking: {...},
  response_times: {...}, feasible: bool} (feasible iff every response time
  <= its task period).
ValueErrors: C <= 0, T <= 0, C > T, cs < 0, duplicate task names.

Identity to test: a task set with no shared resources has zero blocking
and the response times match plain RTA (call with an empty lock list);
blocking times are non-negative; a highest-priority task that shares no
resource with lower-priority tasks has zero blocking.

## Worked example

Verified at prep (tasks T1 C=1 T=5 prio=3, T2 C=2 T=10 prio=2, T3 C=3
T=20 prio=1; locks: R1 ceiling 3 used by T1 cs=0.5 and T3 cs=0.6, R2
ceiling 2 used by T2 cs=0.8 and T3 cs=0.7):
- Ceilings: R1 -> 3, R2 -> 2.
- Blocking: T1 0.6 (T3's 0.6 cs on R1, ceiling 3 >= prio 3), T2 0.7
  (T3's 0.7 cs on R2, ceiling 2 >= prio 2), T3 0.0 (no lower-priority
  task).
- Response times with blocking: T1 1.6, T2 3.7, T3 7.0; all <= their
  periods -> feasible True.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds from the ceiling and fixed-point rules.

## Validation list (contract test must include)

- priority_ceiling on the anchor gives R1 3 and R2 2.
- Blocking truth table on the anchor: 0.6 / 0.7 / 0.0.
- Fixed-point response times converge to 1.6 / 3.7 / 7.0 within 1e-9.
- Empty lock list: blocking all zero; RTA equals plain RTA (T1 1.0, T2
  3.0, T3 6.0 for the anchor tasks with no locks).
- Ceiling rule boundary: a lower-priority task locking a resource whose
  ceiling is below the task priority contributes no blocking.
- ValueErrors: C <= 0, C > T, cs < 0, unknown task reference.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave38-shared-resource-access-control.yaml)

Query 1 (copy verbatim):
  "compute the priority-ceiling-protocol worst-case blocking time for an avionics task set sharing protected resources"
  intent: "avionics; priority ceiling protocol blocking bounds"
  expected_skill: "avionics/fsw/shared-resource-access-control"
Query 2 (copy verbatim):
  "run the response-time-analysis with the blocking term for fixed-priority tasks under the stack-resource-policy and decide schedulability"
  intent: "avionics; response time analysis with shared resource blocking"
  expected_skill: "avionics/fsw/shared-resource-access-control"
Task ids: w38-shared-resource-access-control-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must account for shared-resource
blocking in a fixed-priority avionics task set:" and include the outputs
in the Claim. First tag: shared-resource-access-control. Additional tags
ONLY: priority-ceiling-protocol, priority-inheritance, worst-case-blocking,
stack-resource-policy, blocking-time-bound, schedulability-with-blocking.
NEVER single generic words (resource, blocking, priority, scheduling,
task, ceiling). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): utilization, Liu and Layland,
earliest deadline first, plain response time analysis (real-time-
scheduling); WCET estimation; semaphore API, OSAL (cfs-architecture).
