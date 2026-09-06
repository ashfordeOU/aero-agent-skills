---
name: aperiodic-server-scheduling
description: "Use when you must give the aperiodic or event-driven jobs of an avionics flight software task set a bounded service under fixed-priority scheduling: reduce the event streams to their load utilization, size the polling-server, deferrable-server or sporadic-server capacity and period from that load with a burst margin, fold the server budget into the fixed-priority response-time analysis as a periodic task at its priority slot, and place it at the highest slot where every periodic task keeps its implicit deadline and the budget completes within its period. Produces the sized server budget, the insertion index with the augmented response times and total utilization, the worst-case aperiodic response bounds with the capacity-loss wait and replenishment arithmetic, and the no-feasible-slot verdict. Trigger: aperiodic server, sporadic server, deferrable server, polling server, server budget, event driven jobs, aperiodic response time."
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
  tags: [aperiodic-server-scheduling, sporadic-server, deferrable-server, polling-server, server-capacity, aperiodic-response-bound]
  version: 0.1.0
  author: AeroSkills
---

# Aperiodic Server Scheduling (avionics/fsw/aperiodic-server-scheduling)

Use when an avionics flight software task set must also service aperiodic
or event-driven jobs (fault and health events, command handling,
mode-change requests) beside its periodic hard-real-time tasks, and the
periodic-only model of the pack sibling cannot admit the event release at
all. This leaf inserts a fixed-priority aperiodic server with capacity
C_s and period T_s, in polling-server, deferrable-server or
sporadic-server budget semantics, into the periodic (C, T) task set so
the aperiodic jobs get a bounded worst-case service without breaking any
periodic deadline. It reduces the event load to its load utilization,
sizes the budget from that load with a burst margin, folds the budget
into the fixed-priority response-time analysis exactly as a periodic task
at its priority slot, and reports the insertion index with the augmented
response times, the worst-case aperiodic response bounds and the
no-feasible-slot verdict. Pure Python stdlib, closed form (math.ceil
only), deterministic. Pairs with avionics/fsw/real-time-scheduling for
the periodic-only feasibility verdicts of a task set with no aperiodic
jobs and with avionics/fsw/shared-resource-access-control when shared
resource blocking must be added to the fixed point.

## Domain quick reference

- Event load: each aperiodic event stream is an (s, a) pair of
  worst-case execution s and minimum inter-arrival a in the same time
  unit as the periodic task set. Load utilization u_a = sum over streams
  of s_j / a_j; an empty stream list carries u_a = 0.
- Server sizing: U_s = u_a + margin, C_s = U_s * T_s, with u_a >= 0,
  margin >= 0 and u_a + margin in (0, 1]. The margin is explicit burst
  headroom, so the stability condition U_s >= u_a always holds (margin 0
  allowed). Doubling T_s at fixed U_s doubles C_s and leaves U_s
  invariant.
- Budget as a periodic task: in the fixed-priority response-time
  analysis of the augmented set, task i below the server iterates
  R_i = C_i + sum over higher-priority periodic tasks j of
  ceil(R_i / T_j) * C_j + ceil(R_i / T_s) * C_s, and the server's own
  response iterates the same fixed point for a task of execution C_s and
  period T_s over the tasks above it. The iteration is monotone
  non-decreasing; an iterate that repeats within 1e-12 has converged, and
  an iterate that exceeds the task's own period, or the 100 pass cap
  (MAX_RTA_ITERATIONS), reports None. This budget-as-periodic-task
  insertion is the standard fixed-priority treatment of polling,
  deferrable and sporadic server budgets (Sprunt, Sha and Lehoczky,
  Aperiodic task scheduling for hard-real-time systems, The Journal of
  Real-Time Systems 1(1), 1989; the deferrable server mechanism from
  Lehoczky, Sha and Strosnider, RTSS 1987; public science, summary-only).
- Server mechanisms: polling capacity exists only at the poll instants
  k * T_s and is forfeited when a poll finds an empty queue; deferrable
  capacity is preserved through the period and replenished to C_s at each
  period start; sporadic replenishes a consumed budget T_s after the
  consumption started, so its budget is never forfeited on idleness.
- Aperiodic worst-case bound: a burst of total demand d (each job at most
  C_s) needs k = ceil(d / C_s) service windows, and the final unit of
  service completes at k * T_s + d - (k - 1) * C_s after the arrival.
  A single job of execution C_a <= C_s has the bound T_s + C_a. The bound
  arithmetic is identical for all three mechanisms; they differ only in
  which arrival phases attain it.
- Single-job phase response (empty queue, budget available): polling
  serves at phase 0.0 in C_a and otherwise waits for the next poll,
  R = (T_s - phase) + C_a, sup T_s + C_a approached as phase tends to 0
  from above; deferrable and sporadic serve immediately at every phase,
  R = C_a (capacity preservation).
- Replenishment wait after a full-budget consumption [start, end]:
  polling and deferrable wait ceil(end / T_s) * T_s - end for the next
  poll or period start; sporadic waits T_s - (end - start), independent
  of where in the period the consumption sat. A consumption ending
  exactly on a boundary has polling and deferrable wait 0.
- The model is single-processor fixed-priority, one time unit per task
  set; WCETs are inputs, never estimated here.

## Workflow

1. Establish the periodic baseline feasibility check: periodic_utilization
   over the (C, T) task set and the plain response times from
   server_response_times with the budget at the bottom slot.
2. Reduce the aperiodic load: aperiodic_utilization over the (s, a)
   event streams gives u_a.
3. Size the server budget: server_parameters(u_a, T_s, margin) returns
   the period, the capacity C_s = U_s * T_s and the utilization U_s.
4. Insert the budget into the response-time analysis: server_response_times
   at each candidate priority slot above_index reports the server
   response, the task responses (None per diverged task), the feasibility
   verdict and the total utilization.
5. Place the server: place_server scans the n + 1 priority slots from the
   highest and returns the first feasible insertion index, or raises the
   no-feasible-slot verdict when no placement works.
6. Bound the aperiodic worst-case response: aperiodic_response_bound
   gives the burst bound of the final unit of service.
7. Compare the mechanisms: polling_server_response against
   deferrable_server_response and sporadic_server_response over the
   arrival phases shows the forfeit-versus-preservation trade.
8. Compute the capacity-loss wait: replenishment_wait for the polling,
   deferrable and sporadic kinds after a full-budget consumption.
9. Confirm with the deterministic contract test run under both
   interpreters (see Contract test).

## Worked example

Periodic task set A = [(1, 5), (2, 10), (3, 25)] ms in rate-monotonic
order (task 0 highest priority, implicit deadlines 5, 10, 25 ms). The
aperiodic load has two event streams, E1 (s 1.0 ms, a 20 ms: fault and
health-event processing) and E2 (s 2.0 ms, a 40 ms: command handling),
times in ms. Server period T_s = 25 ms, burst margin 0.02. Real module
outputs:

- Periodic baseline: periodic_utilization(A) = 0.52 (1/5 + 2/10 + 3/25);
  the plain response times are [1.0, 3.0, 7.0] ms, every task inside its
  period.
- Aperiodic load and sizing: aperiodic_utilization([(1, 20), (2, 40)]) =
  0.1 (0.05 + 0.05), so the event load demands 10% of the processor;
  server_parameters(0.1, 25, 0.02) returns period 25.0, capacity
  3.000000 ms and utilization 0.120000: the budget C_s = 3 ms every 25 ms
  covers the 0.10 load with 0.02 of headroom. The same margin at T_s = 50
  gives capacity 6.000000 at the same utilization 0.120000, and the
  capacity/period round trip is 0.120000.
- Worst-case aperiodic response bounds (T_s 25, C_s 3, job 2 ms): a
  single 2 ms job has the bound 27.000000 ms (T_s + C_a) at the worst
  arrival phase; a burst of demand 3, 6, 9 ms has the bounds 28.000000,
  53.000000, 78.000000 ms, each extra full budget of backlog adding one
  25 ms period; the 8 ms event burst from a storm of events has the bound
  77.000000 ms; halving the server period to 10 ms cuts the single-job
  bound to 12.000000 ms.
- Phase responses of a 2 ms job (queue empty, budget available):
  polling (25, 3, 2, phase 0.0) = 2.000000, phase 12.5 = 14.500000,
  phase 24.0 = 3.000000: the polling server forfeits the budget at an
  empty poll, so an arrival just after the poll instant waits almost a
  full period while an arrival near the next poll is served quickly.
  deferrable and sporadic return 2.000000 at every one of those phases:
  the preserved budget serves the same mid-period arrival immediately,
  14.5 ms sooner than polling. The polling worst case is the sup 27.0 ms
  approached as the phase tends to 0 from above.
- Replenishment waits after a full-budget consumption (T_s 25):
  consumption [0.0, 3.0]: polling 22.000000, deferrable 22.000000,
  sporadic 22.000000 (aligned to a period start, all three wait one
  period minus the 3 ms of service); consumption [17.0, 20.0]: polling
  5.000000 and deferrable 5.000000 (next poll and period start at 25)
  against sporadic 22.000000 (replenishment at 17 + 25 = 42);
  consumption [22.0, 25.0]: polling 0.000000 and deferrable 0.000000
  (ends exactly on the boundary) against sporadic 22.000000.
- Server placement on set A with the (C_s 3, T_s 25) budget: every slot
  is feasible; the slot scan shows the structure: above_index 0: server
  R_s = 3.000000, tasks [4.000000, 7.000000, 10.000000]; above_index 1:
  R_s = 4.000000, tasks [1.000000, 7.000000, 10.000000]; above_index 2:
  R_s = 7.000000, tasks [1.000000, 3.000000, 10.000000]; above_index 3:
  R_s = 10.000000, tasks [1.000000, 3.000000, 7.000000]. place_server(A)
  returns insertion_index 0, server_response_time 3.000000, tasks
  [4.000000, 7.000000, 10.000000], total_utilization 0.64, feasible
  True: the light event load (0.10) fits a 3 ms budget at the TOP of the
  priority order, and the periodic tasks still close at 4, 7 and 10 ms
  against their 5, 10 and 25 ms deadlines.
- Heavy event load, set B: add stream E3 (s 3.0 ms, a 12.5 ms: telemetry
  downlink request handling), so aperiodic_utilization = 0.340000 and
  server_parameters(0.34, 25, 0.06) gives capacity 10.000000 at
  utilization 0.400000. Slots 0 and 1 are infeasible (None entries: the
  10 ms budget preempting the 5 ms or 10 ms task blows its deadline);
  place_server(B) returns insertion_index 2, server_response_time
  18.000000, tasks [1.000000, 3.000000, 24.000000], total_utilization
  0.92, feasible True. Push the load to u_a + margin 0.9 (capacity
  22.5 ms) and place_server raises ValueError: "no feasible insertion
  point for the server in the 4 priority slots", the no-feasible-slot
  verdict.
- Read-off: a 10% event load rides free at the top of the priority order
  (set A, insertion index 0) with a 3 ms budget and worst-case
  single-job bound 27 ms; a 34% event load forces a 10 ms budget below
  the two fast tasks (insertion index 2) with worst case 77 ms for an
  8 ms backlog storm, and the periodic set still closes at 1, 3 and
  24 ms.

## Verification

- periodic_utilization([(1, 5), (2, 10), (3, 25)]) = 0.52; an empty task
  list, zero or boolean C or T and malformed entries raise.
- aperiodic_utilization of streams A = 0.1, of an empty list exactly
  0.0; doubling every execution s doubles the load; non-positive s or a
  raises.
- server_parameters(0.1, 25, 0.02): capacity 3.0, utilization 0.12,
  period 25.0, and capacity equals utilization times period; the T_s = 50
  sizing doubles the capacity at the same utilization; negative margin,
  zero period, utilization above 1 and zero capacity raise.
- The three response functions return C_a at phase 0.0, polling alone is
  phase dependent ((T_s - phase) + C_a), deferrable and sporadic are
  phase independent; T_s 0, C_a 0, C_a above C_s, negative phase and
  phase at T_s raise in every response function.
- aperiodic_response_bound(25, 3, 2.0) = 27.0 (T_s + C_a); the demand
  ladder 3, 6, 9 gives 28.0, 53.0, 78.0 with each step one period of
  25.0; the bound is monotone in demand and in T_s; non-positive demand,
  capacity or period raise.
- replenishment_wait returns 22.0 for all three kinds on [0, 3]; polling
  and deferrable 5.0 against sporadic 22.0 on [17, 20]; polling and
  deferrable 0.0 against sporadic 22.0 on [22, 25]; bad kind, negative
  start, end equal to start and a consumption longer than T_s raise.
- server_response_times accepts above_index in [0, len(tasks)] inclusive
  (the bottom slot reproduces the plain periodic responses; out-of-range
  indices, an empty task list and a capacity above the period raise). A
  diverged task or server reports None and the slot is infeasible.
- place_server returns the highest feasible slot (insertion_index 0 on
  set A, 2 on set B) and raises the no-feasible-slot verdict naming the
  priority slots when every slot fails.
- The module is deterministic (identical outputs run to run), imports
  nothing beyond math, and MAX_RTA_ITERATIONS is fixed at 100.
- Run the contract test offline: python3
  scripts/test_aperiodic_server_scheduling.py (37 tests, exits 0; also
  green under ~/.pyenv/versions/3.13.12/bin/python3).

## Related leaves

- avionics/fsw/real-time-scheduling: the periodic-only utilization,
  bound and response-time feasibility verdicts of a task set with no
  aperiodic jobs; the set augmented here must be checked there or here
  for its periodic baseline.
- avionics/fsw/shared-resource-access-control: the priority-ceiling
  blocking term B_i that a shared-resource task set adds to the same
  fixed point.
- avionics/fsw/cfs-architecture and avionics/fsw/fprime-component: the
  software bus routing and cyclic rate-group dispatch layouts that these
  event servers sit beside.
- avionics/ima/ima-partitioning: the partition window schedule one level
  above process-level server budgets.
- avionics/data-bus/mil-std-1553: bus command/response windows, a bus
  term rather than a task or server response.

## Pitfalls

- Treating the load utilization as the server utilization: U_s = u_a +
  margin, and the margin is the burst headroom that keeps U_s >= u_a
  stable; a zero margin server sized exactly at the stream average has no
  slack for bursty event arrivals.
- Placing the server by responsiveness alone: the top slot gives the
  best aperiodic response (set A) but a large budget at the top blows the
  fast task deadlines (set B slots 0 and 1 return None entries); the
  placement scan, not intuition, decides the insertion index.
- Quoting the phase-0 response as the polling worst case: an arrival
  just after an empty poll pays nearly a full period; the polling worst
  case is the sup T_s + C_a approached as the phase tends to 0 from
  above, attained by no single phase.
- Comparing mechanisms at one phase: polling is phase dependent
  (14.5 ms mid-period in the example) while deferrable and sporadic serve
  in C_a at every phase with an unspent budget; the difference is the
  forfeit-on-empty-poll semantics, not a speed difference in service.
- Sizing the bound from a single job: a burst of total demand d pays
  k * T_s + d - (k - 1) * C_s (77 ms for an 8 ms storm), far above the
  single-job bound T_s + C_a; bound the burst, not the average job.
- Forgetting that sporadic replenishment is start anchored: the sporadic
  wait after a consumption is T_s minus the consumption length wherever
  the consumption sat in the period, while polling and deferrable wait
  for the next boundary instant.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_aperiodic_server_scheduling.py

The test covers the periodic baseline utilization and plain response
times, the aperiodic load reduction and its doubling identity, the server
budget sizing with the capacity/period round trip and the doubled-period
identity, all three single-job phase responses with their ValueErrors,
the aperiodic worst-case response bound ladder and monotonicity, the
replenishment waits of all three kinds with the boundary cases, the
response-time analysis with the inserted budget across the slot scan
(None entries for diverged tasks), the placement verdicts on sets A and
B, the no-feasible-slot raise, and module discipline (determinism,
math-only imports, MAX_RTA_ITERATIONS 100). 37 tests, offline and
deterministic, exits 0.

## Compliance

- Standards referenced, not reproduced: RTCA DO-178C (Software
  Considerations in Airborne Systems and Equipment Certification) frames
  the avionics software lifecycle context in which the scheduling
  analysis artifact is recorded; the server mathematics above is public
  science (Sprunt, Sha and Lehoczky 1989; Lehoczky, Sha and Strosnider
  1987), summary-only per standards-map.yaml. No standard text is
  reproduced verbatim.
- compliance: STANDARDS-REF, gated: false.
