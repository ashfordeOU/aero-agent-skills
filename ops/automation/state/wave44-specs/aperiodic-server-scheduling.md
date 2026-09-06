# Wave-44 leaf spec: aperiodic-server-scheduling (avionics,
# fsw pack)

- Path: skills/avionics/fsw/aperiodic-server-scheduling/
- Pack: fsw (present siblings avionics/fsw/real-time-scheduling,
  avionics/fsw/shared-resource-access-control, avionics/fsw/cfs-
  architecture, avionics/fsw/fprime-component; adjacent fences in
  avionics/ima/ima-partitioning (partition window schedule and
  inter-partition port latency) and avionics/data-bus/mil-std-1553 (bus
  response windows)). AV 46 probe receipt task-0 rank 1; wave-44 leaf
  plan item 1; 0 owners verified.
- Claim fences (quoted from the sibling frontmatter and bodies at prep;
  none owns the fixed-priority service of aperiodic or event-driven jobs
  beside a periodic task set):
  - real-time-scheduling (this pack) is the PERIODIC-ONLY fence: its
    description reads "Use when you must decide the offline schedulability
    of a periodic hard-real-time task set: compute the processor
    utilization of (C, T) tasks with implicit deadlines, apply the
    Liu-Layland utilization bound for rate-monotonic fixed-priority
    scheduling, run the exact iterative response-time analysis task by
    task, and test earliest-deadline-first feasibility with the
    full-utilization condition". Its scope note is explicit: "WCET
    estimation, jitter and blocking analysis, and arbitrary-deadline
    response-time extensions are out of scope; the model is the classic
    implicit-deadline periodic task set." Every task in that leaf is a
    (C, T) pair released strictly by its period; there is no aperiodic
    arrival, no event job, no server budget, no capacity replenishment
    and no aperiodic response bound anywhere in its model, workflow,
    worked examples (sets A, B, C, D are all periodic) or test contract.
    The gap this leaf closes: an avionics task set that ALSO services
    aperiodic or event-driven jobs (fault or health events, command
    handling, mode-change requests) cannot be admitted by the periodic
    sibling at all, because its model has no place for an event release.
  - shared-resource-access-control (this pack) is the PCP-blocking-only
    fence: its description reads "Use when you must account for
    shared-resource blocking in a fixed-priority avionics task set:
    assign each protected resource its priority ceiling from the tasks
    that lock it, compute the worst-case blocking time each task can
    suffer from lower-priority tasks under the priority ceiling protocol,
    and run the response-time analysis with the blocking term to decide
    schedulability". Its task model is the same periodic (C, T) set plus
    lock dicts; the blocking term B_i it adds to the fixed point is a
    shared-resource ceiling effect, never an event-service budget.
  - cfs-architecture (this pack) routes messages by 16-bit message ID
    over a software bus publish/subscribe model (quoted: "route messages
    by 16-bit message ID over a software bus publish/subscribe model");
    its apps run on cyclic APP_Execute schedules, and no leaf body
    computes a server budget or an aperiodic response bound.
  - fprime-component (this pack) "schedule[s] component input ports in
    rate groups" (quoted); the rate group is a cyclic dispatch layout,
    not an event server with capacity and replenishment.
  - ima-partitioning (avionics/ima, adjacent) owns the partition schedule
    level: its description reads "check partition schedule feasibility by
    summing the partition durations within the major frame and verifying
    that each partition receives its period slot, build the partition
    configuration table from frame and window data, bound sampling port
    and queuing port message latency for inter-partition communication".
    That leaf sits one level above this one (partition windows in the
    frame schedule); it never sizes a process-level server budget for
    aperiodic work inside a partition, and this leaf does not touch
    partition window or port-latency arithmetic.
  - mil-std-1553 (avionics/data-bus, adjacent) owns the bus
    command/response "response window", which real-time-scheduling
    itself notes "is a bus term, not a task response time"; nothing in
    the data-bus family services event-driven task-level work with a
    fixed-priority server budget.
  Whole-tree greps at prep (grep -c 0, grep -l empty per token): the
  tokens sporadic-server, deferrable-server, polling-server,
  server-budget and server-capacity return ZERO matches in every
  skills/*.md file and in eval/hit1-corpus.yaml and every eval/*.yaml
  fragment. The bare word aperiodic appears in the skills tree only in
  flight-test-operations/stability/dynamic-stability-flight-test, and
  only as aircraft dynamics language in one script ("the roll mode is
  aperiodic, estimate ...", "aperiodic, heavily damped, no oscillation",
  "aperiodic convergence as expected"); it carries zero scheduling
  content and no SKILL.md text. GENUINE avionics/fsw gap (probe receipt
  AV 46, verified zero-owner, GO): no leaf sizes a polling, deferrable or
  sporadic server budget for the aperiodic and event-driven jobs that the
  periodic-only real-time-scheduling model cannot admit.
- Standards id: do-178c (RTCA DO-178C, Software Considerations in Airborne
  Systems and Equipment Certification; the avionics software lifecycle
  context in which the scheduling analysis artifact is recorded),
  reference-only and present in standards-map.yaml. Ledger Standard:
  do-178c.
- Family: avionics

## Claim

Insert a fixed-priority aperiodic server (capacity C_s, period T_s, with
polling-server, deferrable-server or sporadic-server budget semantics)
into a periodic hard-real-time task set so the aperiodic and event-driven
jobs of an avionics flight software task set get a bounded worst-case
service without breaking any periodic deadline. Take the aperiodic load
as its event streams, each an (s, a) pair of worst-case execution s and
minimum inter-arrival a in the same time unit as the periodic task set,
and reduce it to the load utilization u_a = sum(s/a). Size the server
budget from that load: server utilization U_s = u_a + margin (margin is
explicit burst headroom, so stability U_s >= u_a always holds with
margin 0 allowed), capacity C_s = U_s * T_s at the chosen server period,
with U_s capped at 1. Fold the budget into the fixed-priority
response-time analysis exactly as a periodic task (C_s, T_s) at its
priority slot: the server's own response time is the fixed point of a
task of execution C_s and period T_s over the tasks above it, every
periodic task below the server gains the interference term
ceil(R_i / T_s) * C_s, and every periodic task above it is untouched.
Search the n + 1 priority slots from the highest and place the server at
the first slot where every periodic task still converges within its
implicit deadline and the server's own response stays within T_s,
reporting the insertion index, the augmented response times, the total
utilization and the feasible verdict, or the no-feasible-slot error when
no placement works. Then bound the aperiodic service: the worst-case
response of the final unit of service of an aperiodic burst of total
demand d (each job at most C_s) arriving at the worst phase is
R = ceil(d / C_s) * T_s + d - (ceil(d / C_s) - 1) * C_s, the single-job
bound is T_s + C_a, and the phase and replenishment arithmetic
distinguishes the three mechanisms: the polling server forfeits an
unused budget at any poll that finds an empty queue, so its single-job
response depends on the arrival phase and approaches T_s + C_a for an
arrival just after an empty poll; the deferrable server preserves its
budget through the period and serves immediately at every phase while
the budget is unspent; the sporadic server replenishes the consumed
budget T_s after the consumption started, and its budget never sits idle
in forfeit. Does NOT do: the plain periodic feasibility verdict of a task
set with no aperiodic jobs (avionics/fsw/real-time-scheduling owns the
utilization, bound and response-time verdicts of the periodic-only
model); priority-ceiling blocking from shared resources
(avionics/fsw/shared-resource-access-control); partition window
schedules and sampling or queuing port latencies
(avionics/ima/ima-partitioning); the software bus routing and cyclic
rate group dispatch layout (avionics/fsw/cfs-architecture,
avionics/fsw/fprime-component); bus command/response windows
(avionics/data-bus/mil-std-1553). Server
budget sizing assumes worst-case execution times as inputs, never
estimates them; aperiodic arrival behavior beyond the (s, a)
minimum-inter-arrival stream model is out of scope; the analysis is the
single-processor fixed-priority model, one time unit per task set.

## Model (implement exactly)

Pure stdlib, math.ceil only, closed form. Module constant:
MAX_RTA_ITERATIONS = 100 (the fixed-point safety cap; an iterate that
still moves after 100 passes reports divergence).

Defining relations (pin these exactly; every function below derives from
them):
- Load utilization: u_a = sum over streams of s_j / a_j, worst-case
  execution s_j over minimum inter-arrival a_j, same time unit as the
  periodic task set. An empty stream list carries zero load, u_a = 0.
- Server sizing: U_s = u_a + margin, C_s = U_s * T_s. The utilization
  must not exceed 1 and the capacity must be positive, so u_a >= 0,
  margin >= 0, u_a + margin in (0, 1]. Doubling T_s at fixed U_s doubles
  C_s and leaves U_s invariant.
- Budget as a periodic task: in the fixed-priority response-time analysis
  of a periodic task set augmented with a server budget (C_s, T_s) at
  priority slot k, task i below the server iterates
  R_i = C_i + sum over higher-priority periodic tasks j of
  ceil(R_i / T_j) * C_j + (ceil(R_i / T_s) * C_s when k <= i), and the
  server's own response iterates the same fixed point for a task of
  execution C_s and period T_s over the tasks above it. The iteration is
  monotone non-decreasing: convergence is an iterate that repeats within
  1e-12, and an iterate that exceeds the task's own period (or the 100
  pass cap) can never converge under it, so that task reports None. This
  budget-as-periodic-task insertion is the standard fixed-priority
  treatment of polling, deferrable and sporadic server budgets in the
  schedulability analysis of lower-priority tasks (Sprunt, Sha and
  Lehoczky, "Aperiodic task scheduling for hard-real-time systems", The
  Journal of Real-Time Systems 1(1), 1989, pp. 27-60, which introduces
  the sporadic server and compares the aperiodic service algorithms; the
  deferrable server mechanism is from Lehoczky, Sha and Strosnider,
  RTSS 1987. Citation verified against the publisher record at spec time;
  the mathematics above is public science, summary-only, no text
  reproduced).
- Server mechanisms (published semantics, pinned for the phase and
  replenishment arithmetic below):
  - polling: capacity exists only at the poll instants k * T_s and is
    forfeited when a poll finds an empty queue;
  - deferrable: capacity is preserved through the period and replenished
    to C_s at each period start;
  - sporadic: a consumed budget is replenished T_s after the consumption
    started, so the budget is never forfeited on idleness.
- Aperiodic worst-case response bound: a burst of total execution demand
  d (each job at most C_s) arriving at the worst phase misses the
  in-progress service window; the server delivers at most C_s per period,
  k = ceil(d / C_s) windows are needed, and the final unit of service
  completes at k * T_s + d - (k - 1) * C_s after the arrival. A single
  job of execution C_a <= C_s therefore has the bound T_s + C_a. The
  bound arithmetic is identical for all three mechanisms; the mechanisms
  differ only in which arrival phases attain it.
- Single-job phase response (queue empty, budget available): polling
  serves a job that arrives exactly at a poll instant (phase 0) in C_a
  and otherwise waits for the next poll, R = (T_s - phase) + C_a, whose
  sup over phases is T_s + C_a approached as phase tends to 0 from above
  (the missed-poll instant); deferrable and sporadic serve immediately at
  every phase while the budget is available, R = C_a (capacity
  preservation).
- Replenishment wait after a full-budget consumption [start, end]:
  polling waits for the next poll instant, ceil(end / T_s) * T_s - end;
  deferrable waits for the next period-start replenishment, the same
  ceil arithmetic (preservation only helps before the budget is spent);
  sporadic waits T_s after the consumption started, (start + T_s) - end
  = T_s - (end - start), independent of where in the period the
  consumption sat. A consumption ending exactly on a poll or period
  boundary has polling and deferrable wait 0.

Functions:
- periodic_utilization(tasks) -> float
  Sum of C/T over the periodic (C, T) task list, rate-monotonic order
  (index 0 highest priority), implicit deadlines D = T. ValueError for
  an empty list, a non-positive or boolean C or T, or a malformed entry.
- aperiodic_utilization(streams) -> float
  Load utilization sum(s/a) over the (s, a) event streams. An empty
  stream list returns 0.0; ValueError for any non-positive or boolean
  s or a, or a malformed entry.
- server_parameters(u_a, t_s, margin = 0.0) -> dict
  Returns {"period": T_s, "capacity": C_s, "utilization": U_s} with
  U_s = u_a + margin and C_s = U_s * T_s. ValueError when u_a < 0,
  margin < 0, T_s <= 0, U_s > 1, or the capacity is zero (u_a = 0 and
  margin = 0).
- polling_server_response(t_s, c_s, c_a, phase = 0.0) -> float
  Single-job response under the polling server with an empty queue and
  an available budget: C_a at phase 0.0 (the job arrives exactly at a
  poll instant), else (T_s - phase) + C_a. ValueError when T_s <= 0,
  C_s <= 0, C_a <= 0, C_a > C_s, or phase outside [0, T_s).
- deferrable_server_response(t_s, c_s, c_a, phase = 0.0) -> float
  Single-job response under the deferrable server with an unspent
  budget: C_a at every phase (capacity preservation). Same ValueErrors;
  the phase argument is validated for interface parity and does not
  change the result.
- sporadic_server_response(t_s, c_s, c_a, phase = 0.0) -> float
  Single-job response under the sporadic server with an available
  budget: C_a at every phase. Same ValueErrors.
- aperiodic_response_bound(t_s, c_s, demand) -> float
  The worst-case bound of the final unit of service of a burst of total
  demand `demand`: k = ceil(demand / C_s), returns
  k * T_s + demand - (k - 1) * C_s. ValueError when T_s <= 0, C_s <= 0
  or demand <= 0. No per-job cap here: `demand` is a burst total whose
  individual jobs are each at most C_s.
- replenishment_wait(kind, t_s, start, end) -> float
  Wait from the end of a full-budget consumption [start, end] until the
  budget is next fully available: "polling" and "deferrable" give
  ceil(end / T_s) * T_s - end, "sporadic" gives T_s - (end - start).
  ValueError for any kind outside the three strings, T_s <= 0,
  start < 0, end <= start, or a consumption longer than T_s.
- server_response_times(tasks, server, above_index) -> dict
  Response-time analysis of the periodic set with the server budget
  inserted at priority slot above_index in [0, len(tasks)]: tasks
  [0:above_index] stay above the server, the server sits between task
  above_index - 1 and task above_index, tasks [above_index:] run below
  it and gain ceil(R_i / T_s) * C_s. Returns {"above_index",
  "server_response_time" (float or None), "task_response_times" (list
  with a None entry per diverged task, or None), "feasible" (True only
  when the server response and every task response converged within the
  task periods), "total_utilization" (periodic utilization + C_s / T_s)}.
  ValueError for an empty or malformed task list, a server dict without
  positive capacity and period with capacity <= period, or above_index
  outside [0, len(tasks)].
- place_server(tasks, server) -> dict
  Scan the n + 1 priority slots from the highest (above_index 0, best
  aperiodic responsiveness) to the lowest (above_index n) and return the
  first feasible placement as {"insertion_index", "server_response_time",
  "task_response_times", "total_utilization", "feasible": True}.
  ValueError when no slot is feasible, with a message naming the number
  of priority slots tried.

Identities to test (closed form, exact):
- Utilization and sizing: periodic_utilization of set A is 0.52 exactly
  (1/5 + 2/10 + 3/25); aperiodic_utilization of streams A is 0.1 exactly
  (1/20 + 2/40); an empty stream list is 0.0; doubling every execution
  s doubles the load utilization; capacity equals utilization times
  period exactly (round trip 0.12) and server_parameters(0.1, 50, 0.02)
  doubles the capacity of server_parameters(0.1, 25, 0.02) (6.0 against
  3.0) while the utilization stays 0.12.
- Phase-zero identity: all three server responses equal C_a at phase 0.0
  (real anchor 2.000000 from each of polling, deferrable and sporadic at
  (25, 3, 2, 0.0)).
- Polling phase linearity: polling_server_response(25, 3, 2, phase)
  equals (25 - phase) + 2 at every positive phase, real anchors 14.500000
  at phase 12.5 and 3.000000 at phase 24.0; deferrable and sporadic are
  phase independent, 2.000000 at both phases (capacity preservation), so
  a mid-period arrival is served 14.5 ms sooner by the preserving
  servers; the polling worst case is the sup T_s + C_a = 27.0 approached
  as phase tends to 0 from above.
- Bound identities: aperiodic_response_bound(25, 3, 2.0) = 27.000000,
  the single-job bound T_s + C_a; the exact-multiple ladder demand 3, 6,
  9 gives 28.000000, 53.000000, 78.000000, each extra full budget of
  demand adds exactly one server period (78.0 - 53.0 = 25.0); the bound
  is monotone in demand (77.0 at demand 8 above 53.0 at demand 6) and in
  T_s (12.000000 at T_s 10 below 27.000000 at T_s 25).
- Replenishment waits: a consumption aligned to a period start
  ([0, 3], T_s 25) gives wait 22.0 for all three kinds; the sporadic
  wait is T_s - length and independent of start (22.0 on both [0, 3] and
  [17, 20]); the polling and deferrable waits on the mid-period
  consumption [17, 20] are 5.0 (next poll and period start at 25); a
  consumption ending exactly on the boundary [22, 25] has polling and
  deferrable wait 0.0 while the sporadic wait stays 22.0 (replenishment
  at 22 + 25 = 47).
- Placement identities: with the server below every task (above_index
  n) the task responses equal the plain periodic response times
  [1.000000, 3.000000, 7.000000] and the server response is 10.000000;
  as the slot moves from 0 to n the server response rises 3.0, 4.0, 7.0,
  10.0 while the periodic responses fall back to the plain baseline;
  total_utilization equals periodic utilization plus C_s / T_s (0.640000
  on set A with U_s 0.12).
- place_server returns the highest feasible slot (insertion_index 0 on
  set A, insertion_index 2 on set B) and raises ValueError when every
  slot fails (u_a + margin 0.9 on set A: no feasible insertion point in
  the 4 priority slots).
- ValueErrors across the module: periodic_utilization on an empty list,
  (0, 5), (1, 0) and a malformed entry; aperiodic_utilization on (0, 5)
  and (1, 0); server_parameters at u_a -0.1, T_s 0, margin -0.01, at
  u_a + margin above 1 and at zero capacity; polling at T_s 0, C_a above
  C_s, negative phase and phase at T_s; deferrable at C_a 0; sporadic at
  phase at T_s; aperiodic_response_bound at demand 0;
  replenishment_wait at a bad kind, negative start, end equal to start
  and a consumption longer than T_s; server_response_times on an empty
  task list, a server with capacity above period, and above_index -1 and
  len(tasks); place_server when no slot is feasible.
- Determinism; identical outputs run to run; no randomness anywhere; no
  imports beyond math.ceil; MAX_RTA_ITERATIONS fixed at 100.

## Worked example

Periodic task set A = [(1, 5), (2, 10), (3, 25)] ms in rate-monotonic
order (task 0 highest priority, implicit deadlines 5, 10, 25 ms). The
aperiodic load has two event streams, E1 (s 1.0 ms, a 20 ms: fault and
health-event processing) and E2 (s 2.0 ms, a 40 ms: command handling),
times in ms. Server period T_s = 25 ms (the slowest periodic period),
burst margin 0.02. All values below are REAL outputs of the prep anchor
/tmp/w44spec/anchor_aperiodic.py (stdlib math, closed form), run once
and quoted as printed:

- Periodic baseline: periodic_utilization(A) = 0.520000; the plain
  response times with no server are [1.000000, 3.000000, 7.000000] ms,
  every task inside its period.
- Aperiodic load and sizing:
  aperiodic_utilization([(1, 20), (2, 40)]) = 0.100000 (0.05 + 0.05), so
  the event load demands 10% of the processor;
  server_parameters(0.1, 25, 0.02) returns period 25.0, capacity
  3.000000 ms and utilization 0.120000: the server budget C_s = 3 ms
  every 25 ms covers the 0.10 load with 0.02 of headroom. The same
  margin at T_s = 50 gives capacity 6.000000 at the same utilization
  0.120000, and the capacity/period round trip is 0.120000.
- Worst-case aperiodic response bounds (T_s 25, C_s 3, job 2 ms):
  a single 2 ms job has the bound 27.000000 ms (T_s + C_a) at the worst
  arrival phase; a burst of demand 3, 6, 9 ms has the bounds 28.000000,
  53.000000, 78.000000 ms (each extra full budget of backlog adds one
  25 ms period); the 8 ms event burst from a storm of events has the
  bound 77.000000 ms; halving the server period to 10 ms cuts the
  single-job bound to 12.000000 ms.
- Phase responses of a 2 ms job (queue empty, budget available):
  polling (25, 3, 2, phase 0.0) = 2.000000, phase 12.5 = 14.500000,
  phase 24.0 = 3.000000: the polling server forfeits the budget at an
  empty poll, so an arrival just after the poll instant waits almost a
  full period, while an arrival near the next poll is served quickly.
  deferrable and sporadic return 2.000000 at every one of those phases:
  the preserved (deferrable) or non-forfeited (sporadic) budget serves
  the same arrival immediately at mid-period, 14.5 ms sooner than
  polling. The polling worst case is the sup 27.0 ms approached as the
  phase tends to 0 from above, exactly the single-job bound above.
- Replenishment waits after a full-budget consumption (T_s 25):
  consumption [0.0, 3.0]: polling 22.000000, deferrable 22.000000,
  sporadic 22.000000 (aligned to a period start, all three wait one
  period minus the 3 ms of service); consumption [17.0, 20.0]: polling
  5.000000 and deferrable 5.000000 (next poll and next period start at
  25) against sporadic 22.000000 (replenishment at 17 + 25 = 42);
  consumption [22.0, 25.0]: polling 0.000000 and deferrable 0.000000
  (ends exactly on the boundary) against sporadic 22.000000.
- Server placement on set A with the (C_s 3, T_s 25) budget: every
  priority slot is feasible, and the per-slot scan shows the structure:
  above_index 0: server R_s = 3.000000, tasks [4.000000, 7.000000,
  10.000000]; above_index 1: server R_s = 4.000000, tasks [1.000000,
  7.000000, 10.000000]; above_index 2: server R_s = 7.000000, tasks
  [1.000000, 3.000000, 10.000000]; above_index 3: server R_s =
  10.000000, tasks [1.000000, 3.000000, 7.000000]. The server response
  rises as the slot moves down while the periodic tasks recover their
  plain response times. place_server(A) returns insertion_index 0,
  server_response_time 3.000000, task_response_times [4.000000,
  7.000000, 10.000000], total_utilization 0.64, feasible True: the
  light event load (0.10) fits a 3 ms budget at the TOP of the priority
  order, giving the aperiodic queue the best possible responsiveness,
  and the periodic tasks still close at 4, 7 and 10 ms against their 5,
  10 and 25 ms deadlines.
- Heavy event load, set B: add event stream E3 (s 3.0 ms, a 12.5 ms:
  telemetry downlink request handling), so
  aperiodic_utilization(streams B) = 0.340000 and
  server_parameters(0.34, 25, 0.06) gives capacity 10.000000 at
  utilization 0.400000. The slot scan: above_index 0: server R_s =
  10.000000, tasks [None, None, 24.000000], feasible False (task 0
  would close at 1 + 10 = 11 ms against its 5 ms period, so its iterate
  crosses the deadline and reports None); above_index 1: server R_s =
  13.000000, tasks [1.000000, None, 24.000000], feasible False (task 1
  cannot survive a 10 ms preemption every 25 ms against its 10 ms
  period); above_index 2: server R_s = 18.000000, tasks [1.000000,
  3.000000, 24.000000], feasible True; above_index 3: server R_s =
  24.000000, tasks [1.000000, 3.000000, 7.000000], feasible True.
  place_server(B) returns insertion_index 2, server_response_time
  18.000000, task_response_times [1.000000, 3.000000, 24.000000],
  total_utilization 0.92, feasible True: the 10 ms budget must sit
  BELOW the 5 ms and 10 ms tasks (a budget that large preempting either
  of them blows their deadlines) and just above the 25 ms task, which
  absorbs it at 24 ms against its 25 ms deadline. Push the load to
  u_a + margin 0.9 (capacity 22.5 ms) and place_server raises ValueError:
  "no feasible insertion point for the server in the 4 priority slots",
  the no-feasible-slot verdict.
- Read-off: the leaf decides where an aperiodic event service can live
  and what the events will pay. A 10% event load rides free at the top
  of the priority order (set A, insertion index 0) with a 3 ms budget
  and worst-case single-job bound 27 ms; a 34% event load (set B) forces
  a 10 ms budget below the two fast tasks (insertion index 2) with worst
  case 77 ms for an 8 ms backlog storm, and the periodic set still
  closes at 1, 3 and 24 ms. The phase table is the mechanism
  comparison: polling pays up to a full period for an arrival that just
  missed an empty poll (14.5 ms at mid-period in the example), while
  deferrable and sporadic answer the same arrival in 2.0 ms.
Run your module and take the real outputs as assert targets; the anchors
above are real prep outputs of /tmp/w44spec/anchor_aperiodic.py (stdlib
math, closed form, exit 0, no randomness).

## Validation list (contract test must include)

- periodic_utilization([(1, 5), (2, 10), (3, 25)]) = 0.52 within 1e-9
  and its plain response times are [1.0, 3.0, 7.0] within 1e-9 each;
  empty and malformed task lists raise.
- aperiodic_utilization([(1.0, 20.0), (2.0, 40.0)]) = 0.1 within 1e-9;
  aperiodic_utilization([]) = 0.0 exactly; doubled executions double the
  load; zero or negative s or a raises.
- server_parameters(0.1, 25, 0.02): capacity 3.0 within 1e-3 (3.000000
  displayed), utilization 0.12 within 1e-9, period 25.0; capacity equals
  utilization times period within 1e-9; server_parameters(0.1, 50, 0.02)
  capacity 6.0 within 1e-3 at the same utilization; u_a -0.1, T_s 0,
  margin -0.01, u_a + margin 1.1 and zero capacity all raise.
- polling_server_response(25, 3, 2, 0.0) = 2.0 within 1e-9;
  (25, 3, 2, 12.5) = 14.5 within 1e-9; (25, 3, 2, 24.0) = 3.0 within
  1e-9; deferrable and sporadic return 2.0 within 1e-9 at phases 0.0,
  12.5 and 24.0; C_a 0, C_a above C_s, negative phase, phase at T_s and
  T_s 0 raise in every response function.
- aperiodic_response_bound(25, 3, 2.0) = 27.0 within 1e-9; demand 3.0,
  6.0, 9.0 give 28.0, 53.0, 78.0 within 1e-9; the ladder step 78.0 -
  53.0 = 25.0 within 1e-9; aperiodic_response_bound(10, 3, 2.0) = 12.0
  within 1e-9; demand 0 raises.
- replenishment_wait: ("polling", 25, 0, 3) and ("deferrable", 25, 0, 3)
  and ("sporadic", 25, 0, 3) all 22.0 within 1e-9; ("polling", 25, 17,
  20) and ("deferrable", 25, 17, 20) both 5.0 within 1e-9; ("sporadic",
  25, 17, 20) = 22.0 within 1e-9 (t_s - length, start independent);
  ("deferrable", 25, 22, 25) = 0.0 within 1e-9 against ("sporadic", 25,
  22, 25) = 22.0 within 1e-9; bad kind, start -1, end equal to start and
  a consumption longer than T_s raise.
- server_response_times on set A with the (3, 25) server: above_index 0
  server R_s 3.0 within 1e-9 and tasks [4.0, 7.0, 10.0] within 1e-9
  each; above_index 3 server R_s 10.0 within 1e-9 and tasks equal the
  plain [1.0, 3.0, 7.0] within 1e-9; total_utilization 0.64 within 1e-9;
  the server response across slots 0..3 is 3.0, 4.0, 7.0, 10.0 within
  1e-9; a diverged task yields a None entry and feasible False; empty
  task list, capacity above period and above_index -1 and len(tasks)
  raise.
- place_server on set A returns insertion_index 0 with task responses
  [4.0, 7.0, 10.0] within 1e-9; on set B (streams [(1.0, 20.0), (2.0,
  40.0), (3.0, 12.5)], margin 0.06) returns insertion_index 2 with
  server R_s 18.0 within 1e-9 and tasks [1.0, 3.0, 24.0] within 1e-9,
  total_utilization 0.92 within 1e-9; slots 0 and 1 of set B are
  infeasible with None entries; place_server with u_a + margin 0.9
  raises ValueError naming the 4 priority slots.
- ValueErrors enumerated in the identity list above all raise from every
  public function; the module is deterministic (identical outputs run to
  run), imports nothing beyond math.ceil, and MAX_RTA_ITERATIONS is 100.
- Run the deterministic contract test offline; it exits 0 with no
  network access.

## Corpus fragment (eval/hit1-wave44-aperiodic-server-scheduling.yaml)

Query 1 (copy verbatim):
  "size the aperiodic-server-scheduling server-budget from the
  aperiodic load utilization and place the sporadic-server at the
  fixed-priority slot that keeps the periodic task set feasible"
  intent: "avionics/fsw; sizing the sporadic-server capacity and period
  from the aperiodic load utilization and inserting the server budget
  into the fixed-priority response-time analysis at the highest feasible
  priority slot so the periodic tasks keep their deadlines"
  expected_skill: "avionics/fsw/aperiodic-server-scheduling"
Query 2 (copy verbatim):
  "bound the aperiodic-response-time of the event-driven jobs under the
  deferrable-server and polling-server worst-case phases with the
  capacity-loss wait and the replenishment arithmetic"
  intent: "avionics/fsw; worst-case aperiodic response bounds and
  budget-replenishment waits for the deferrable-server and polling-
  server mechanisms servicing event-driven jobs beside a fixed-priority
  periodic task set"
  expected_skill: "avionics/fsw/aperiodic-server-scheduling"
Task ids: w44-aperiodic-server-scheduling-1 and -2. Prep grep (run at
spec time): each of the tokens sporadic-server, deferrable-server,
polling-server, server-budget and server-capacity returns 0 matches in
eval/hit1-corpus.yaml and in every eval/*.yaml fragment (grep -c 0,
grep -l empty), and the skills tree carries them nowhere except this
plan (ops/automation, not router input), so the queries above are
collision-free; the sibling tasks route on periodic utilization, bound
and response-time language (real-time-scheduling), ceiling and blocking
language (shared-resource-access-control) and partition and port-latency
language (ima-partitioning), none of which carry server-budget or event
service content.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must give the aperiodic or
event-driven jobs of an avionics flight software task set a bounded
service under fixed-priority scheduling:" and include the outputs in the
Claim order (sized budget, insertion index with augmented response times
and total utilization, worst-case response bounds, no-feasible-slot
verdict). First tag: aperiodic-server-scheduling. Additional tags ONLY:
sporadic-server, deferrable-server, polling-server, server-capacity,
aperiodic-response-bound. NEVER single generic words (server, budget,
aperiodic, periodic, scheduling, priority, response, event, deadline,
feasibility) and never any sibling token below. 50-150 words, <=1000
chars, no em dash, no content-policy sweep term (the banned word from
the builder kit), action verb present. Recommended wording (135 words,
942 chars, verified):
"Use when you must give the aperiodic or event-driven jobs of an
avionics flight software task set a bounded service under fixed-priority
scheduling: reduce the event streams to their load utilization, size the
polling-server, deferrable-server or sporadic-server capacity and period
from that load with a burst margin, fold the server budget into the
fixed-priority response-time analysis as a periodic task at its priority
slot, and place it at the highest slot where every periodic task keeps
its implicit deadline and the budget completes within its period.
Produces the sized server budget, the insertion index with the augmented
response times and total utilization, the worst-case aperiodic response
bounds with the capacity-loss wait and replenishment arithmetic, and the
no-feasible-slot verdict. Trigger: aperiodic server, sporadic server,
deferrable server, polling server, server budget, event driven jobs,
aperiodic response time."

FORBIDDEN TOKENS (belong to siblings): liu-layland-bound,
rate-monotonic-scheduling, earliest-deadline-first, cpu-utilization,
fixed-priority-scheduling, response-time-analysis, wcet-estimation,
jitter, arbitrary-deadline, and any query whose only content is a
schedulability-verdict with no aperiodic service (real-time-scheduling);
priority-ceiling-protocol, priority-inheritance, worst-case-blocking,
stack-resource-policy, blocking-time-bound, schedulability-with-blocking
(shared-resource-access-control); arinc-653, major-frame,
partition-configuration-table, sampling-port, queuing-port,
inter-partition-communication, health-monitoring (ima-partitioning);
software-bus, publish-subscribe, cfe, osal, rate-group, command-opcode,
telemetry-channel (cfs-architecture, fprime-component). Never the bare
words server, budget, aperiodic, periodic, scheduling or response as
standalone tags.
