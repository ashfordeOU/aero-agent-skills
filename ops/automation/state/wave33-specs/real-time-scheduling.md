# Wave-33 leaf spec: real-time-scheduling (avionics, fsw pack)

- Path: skills/avionics/fsw/real-time-scheduling/
- Pack: fsw. Sibling scope check: avionics/ima/ima-partitioning owns MAF
  cyclic window arithmetic only (frame load, period divisibility, window
  slots - no priority-driven/RM/EDF theory); avionics/fsw/cfs-architecture
  is publish/subscribe routing + app skeleton; avionics/fsw/fprime-
  component rate_group validates structural membership only;
  avionics/data-bus/mil-std-1553 "response time window" is bus
  command/response timing (unrelated). Family-wide grep for
  rate.monotonic|earliest.deadline|EDF|liu|layland|response.time found
  only that 1553 hit. This leaf owns the real-time scheduling
  feasibility math.
- Standards id: do-178c (reference-only; mirrors the ima-partitioning
  precedent for ARINC-653-adjacent scheduling; ARINC-653 itself is NOT
  in standards-map and is not needed - pure public mathematics, Liu &
  Layland 1973). Ledger Standard: do-178c.
- Family: avionics

## Claim

Decide the offline schedulability of a periodic hard-real-time process
or task set with implicit deadlines under rate-monotonic fixed-priority
scheduling, via the Liu-Layland sufficient utilization-bound test and
the exact iterative response-time analysis, and under earliest-deadline-
first scheduling via the full-utilization test, for avionics software
partition and process task sets. Produces the utilization, the RM bound
verdict, the exact response times with a feasibility verdict, and the
EDF feasibility verdict.

Does NOT do: MAF cyclic window arithmetic / ARINC-653 partition
scheduling windows (ima-partitioning); message bus scheduling / 1553
response windows (data-bus); rate-group structural checks
(fprime-component); WCET estimation; jitter/blocking analysis
(arbitrary-deadline response-time extensions are out of scope).

## Model (implement exactly)

Conventions: task set of (C_i, T_i) pairs: worst-case execution time C
and period T (implicit deadline D = T), all in the same time unit.
- Utilization U = sum C_i / T_i.
- Liu-Layland bound: U_rm(n) = n (2^(1/n) - 1).
- RM sufficient test: feasible if U <= U_rm(n).
- Exact RM response time (iterative): R_i = C_i + sum_{j in hp(i)}
  ceil(R_i / T_j) C_j, iterate from R_i = C_i to a fixed point; the
  task set is RM-feasible iff R_i <= T_i for all i; divergence (R_i
  growing past a large cap, e.g. 1e6 or 1000 * max T) => infeasible.
  hp(i) = higher-priority tasks (shorter period, tie-break by index
  documented).
- EDF (implicit deadlines): feasible iff U <= 1 (necessary and
  sufficient).

Functions (pure stdlib):

- utilization(tasks) -> U. tasks is a list of (C, T) tuples; ValueError
  on empty list or non-positive entries.
- liu_layland_bound(n) -> n (2^(1/n) - 1). ValueError on n < 1.
- rm_ub_feasible(tasks) -> bool (U <= U_rm(len(tasks))).
- rm_response_times(tasks) -> list of R_i (floats or ints; keep as
  float for ceil math, assert integrality), or None when divergent.
  Document the iteration cap and divergence detection.
- rm_feasible(tasks) -> bool (exact RTA verdict, R_i <= T_i all i).
- edf_feasible(tasks) -> bool (U <= 1).
- scheduling_summary(tasks) -> dict {utilization, n_tasks,
  liu_layland_bound, rm_ub_verdict, rm_exact_response_times,
  rm_exact_feasible, edf_feasible, verdict} where verdict is one of
  "RM-guaranteed-by-UB" | "RM-exact-feasible (UB inconclusive)" |
  "RM-infeasible" | "EDF-feasible-only" etc. Keep the dict keys exact
  and documented.

## Worked example

Classic sets (computed at prep, pure stdlib):
- A = [(1,3), (1,4), (2,8)]: U = 0.8333, LL bound(3) = 0.7798 => UB
  test INCONCLUSIVE (U > bound); EDF feasible (U <= 1); exact RTA
  converges R = [1, 2, 6] all <= T => RM-exact-feasible. This is the
  key demonstration that RTA beats the UB test.
- B = [(2,3), (2,5), (2,7)]: U = 1.3524 > 1 => EDF infeasible; RTA
  diverges (R_max > cap) => RM infeasible.
- C = [(1,5), (1,6), (2,10)]: U = 0.5667 <= 0.7798 => RM guaranteed by
  UB; RTA R = [1, 2, 4].
- Liu-Layland anchors: U_rm(2) = 0.828427, U_rm(3) = 0.779763,
  U_rm(4) = 0.756828.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: empty task list; C <= 0 or T <= 0.
- LL anchors: liu_layland_bound(2/3/4) within 1e-5 of the values above.
- Worked set A: rm_ub_feasible False, edf_feasible True,
  rm_response_times [1,2,6], rm_feasible True.
- Worked set B: edf_feasible False, RTA returns None / divergence
  detected, rm_feasible False.
- Worked set C: rm_ub_feasible True, rm_feasible True.
- Monotonicity: adding a task raises U; doubling C doubles that task's
  contribution.
- Determinism: identical outputs run-to-run.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave33-real-time-scheduling.yaml)

Query 1 (copy verbatim):
  "rate monotonic scheduling utilization bound feasibility test liu layland for an avionics periodic task set with implicit deadlines"
  intent: "avionics; RM Liu-Layland utilization bound schedulability of a periodic task set"
  expected_skill: "avionics/fsw/real-time-scheduling"
Query 2 (copy verbatim):
  "earliest deadline first cpu utilization schedulability test and iterative response time analysis for a hard real time process set"
  intent: "avionics; EDF full-utilization and exact RM response-time-analysis schedulability"
  expected_skill: "avionics/fsw/real-time-scheduling"
Task ids: w33-real-time-scheduling-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must decide the offline
schedulability of a periodic hard-real-time task set:" and include the
outputs in the Claim. First tag: real-time-scheduling. Additional tags
ONLY: rate-monotonic-scheduling, response-time-analysis,
liu-layland-bound, earliest-deadline-first, cpu-utilization,
fixed-priority-scheduling. NEVER single generic words (scheduling,
task, real-time, priority, deadline, process, utilization, avionics).
50-150 words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): MAF, cyclic window, partition
frame, window slot, period divisibility (ima-partitioning); response
time window in the 1553 bus sense (data-bus); rate group membership
(fprime-component); telemetry pipeline, publish subscribe
(cfs-architecture). The tokens "rate monotonic", "response time
analysis", "earliest deadline first", "Liu-Layland" are this leaf's
own.

Tags: [real-time-scheduling, rate-monotonic-scheduling,
response-time-analysis, liu-layland-bound, earliest-deadline-first,
cpu-utilization, fixed-priority-scheduling]

Sibling-citation lines for Related leaves:
avionics/ima/ima-partitioning (MAF cyclic window arithmetic; this leaf
schedules the processes inside the partitions),
avionics/fsw/cfs-architecture,
avionics/data-bus/mil-std-1553.

Ledger Standard: do-178c.
