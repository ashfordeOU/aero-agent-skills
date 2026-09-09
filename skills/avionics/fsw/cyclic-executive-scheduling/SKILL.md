---
name: cyclic-executive-scheduling
description: "Use when you must design and verify the offline repeating frame table of a time-triggered cyclic executive for a periodic avionics flight software task set with implicit deadlines: compute the hyperperiod as the least common multiple of the task periods, choose an admissible frame length that divides every task period and is at least every task execution time C_i, lay each frame-boundary release into the frame that starts at its release time over the hyperperiod, and confirm every per-frame execution total stays within the frame length. Produces the hyperperiod, the admissible and capacity-feasible frame lengths, the constructive cyclic frame table with per-frame loads and per-frame slack, and a FITS or no-admissible-frame verdict with the reject reason. Trigger: cyclic executive scheduling, cyclic frame table, hyperperiod, frame length selection, frame fit feasibility, time triggered frame schedule, frame boundary release."
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
  tags: [cyclic-executive-scheduling, cyclic-frame-table, frame-length-selection, hyperperiod-design, time-triggered-frame-schedule, frame-fit-feasibility, frame-boundary-release]
  version: 0.1.0
  author: AeroSkills
---

# Cyclic Executive Scheduling (avionics/fsw/cyclic-executive-scheduling)

Use when you must design and check the offline feasibility of a
repeating, time-triggered cyclic executive (frame-based) schedule for a
periodic avionics flight software task set. Each task is a dict {name,
C, T} in one integer time unit: worst-case execution time C, period T,
implicit deadline D = T. There are no priorities: the cyclic executive
is priority-free, the frame table IS the schedule, and any task list
order is accepted. This leaf implements the classic closed-form cyclic
executive arithmetic (Baker and Shaw 1989, Locke 1992, Burns and
Wellings 2009) in pure Python stdlib: the hyperperiod, the period gcd,
the admissible frame lengths, the per-frame capacity check and the
constructive frame table. It is the table-driven complement to this
pack's priority-driven feasibility leaves, pairing with
avionics/fsw/real-time-scheduling for single-estimate (C, T) priority
verdicts and avionics/ima/ima-partitioning for the ARINC 653 partition
window arithmetic one level above the task set.

## Domain quick reference

- Hyperperiod (major cycle): H = lcm over all T_i, computed by folding
  lcm(a, b) = a * b // gcd(a, b) over the task periods. The frame table
  over frames 0..H/f - 1 repeats exactly every H time units.
- Period gcd: g = gcd over all T_i. A frame length divides every task
  period iff it divides g, so the candidate frame lengths are the
  divisors of g.
- Processor utilization (necessary condition only): U = sum of C_i /
  T_i. U <= 1 is necessary for a FITS verdict but never sufficient.
- Admissible frame lengths: the ascending divisors f of g with f at
  least max C_i, the frame-fit rule that every job fits inside its own
  frame.
- Frame dispatch: task i releases H / T_i jobs per hyperperiod, at
  times 0, T_i, 2*T_i, .... The job released at time t = j*f executes
  in frame j, so frame j carries exactly one job of task i iff
  (j*f) mod T_i == 0. Frame j covers [j*f, (j+1)*f).
- Per-frame load: load(j) = sum of C_i over the tasks releasing into
  frame j. A frame length f is capacity-feasible iff max over j of
  load(j) <= f.
- Verdicts: FITS when at least one admissible frame length is
  capacity-feasible, choosing the smallest such f; no-admissible-frame
  with reject_reason "frame-fit" when no divisor of g reaches max C_i,
  or "capacity" when admissible lengths exist but every candidate
  over-subscribes some frame.
- Units are one consistent integer time unit (ms in the worked
  examples) throughout; C and T are inputs, never estimated.

## Workflow

1. Define the task set as {name, C, T} dicts, one integer time unit,
   implicit deadline D = T, no priorities and no required order.
2. Compute the hyperperiod H with hyperperiod (the lcm fold over the
   task periods) and the period gcd g with period_gcd.
3. Compute the necessary-condition utilization U with utilization.
4. Enumerate admissible frame lengths with admissible_frame_lengths,
   the ascending divisors of g that are at least max C_i (the frame-fit
   rule).
5. For each admissible frame length compute the per-frame loads with
   frame_loads and the worst frame with max_frame_load, then narrow to
   the capacity-feasible subset with feasible_frame_lengths.
6. Build the constructive frame table at the smallest feasible frame
   length with frame_table, reading each frame's jobs, load and slack.
7. Get the full verdict with cyclic_executive_report (hyperperiod,
   utilization, admissible and feasible frame lengths, verdict, reject
   reason and frame table), or the boolean shortcut with feasible.
8. Confirm the deterministic checks with the contract test
   scripts/test_cyclic_executive_scheduling.py.

## Worked example

Task set A, three avionics fsw processes in ms, implicit deadlines
D = T, no priorities: flight-control (C 3, T 25, a 40 Hz flight control
law task), guidance (C 4, T 50, a 20 Hz guidance task), health-monitor
(C 5, T 100, a 10 Hz health monitoring task).

- Set-level report: hyperperiod 100 (lcm of 25, 50, 100), period_gcd
  25, max_execution_time 5, utilization 0.25. Admissible frame lengths
  (divisors of 25 at least 5): [5, 25]. Candidate f = 5 is rejected on
  capacity, max_frame_load(SET_A, 5) = 12 > 5, because frame 0 holds
  all three co-released jobs (3 + 4 + 5 = 12); candidate f = 25 is
  accepted, max_frame_load(SET_A, 25) = 12 <= 25. feasible_frame_lengths
  [25], verdict "FITS", frame_length 25 (the smallest capacity-feasible
  admissible f), frame_count 4 (100 / 25).
- Frame table at f = 25: frame_loads [12, 3, 7, 3], frame_slacks
  [13, 22, 18, 22]. Frame 0 [0,25) ms carries flight-control, guidance
  and health-monitor, load 12, slack 13 (the capacity-tight frame).
  Frame 1 [25,50) ms carries flight-control only, load 3, slack 22.
  Frame 2 [50,75) ms carries flight-control and guidance, load 7, slack
  18. Frame 3 [75,100) ms carries flight-control only, load 3, slack
  22. The table repeats every 100 ms.
- Identity anchors: sum of frame loads 25 = sum_i C_i * H / T_i =
  3*4 + 4*2 + 5*1 = 25 = H * U = 100 * 0.25 = 25.0; 7 jobs per
  hyperperiod (4 + 2 + 1) placed as 3 + 1 + 2 + 1 across the 4 frames;
  sum of per-frame slacks 75 = 4 * 25 - 25.
- Task set B, the necessary-not-sufficient capacity path: flight-
  control C 8 T 25, guidance C 9 T 50, health-monitor C 10 T 100.
  utilization 0.6, admissible_frame_lengths [25], feasible_frame_lengths
  [], verdict "no-admissible-frame", reject_reason "capacity": U = 0.6
  is at most 1, yet frame 0 must hold all three co-released jobs,
  8 + 9 + 10 = 27 > 25, so no frame length fits.
- Task set C, the frame-fit rejection path: flight-control C 3 T 25,
  display C 8 T 40. period_gcd 5, max_execution_time 8,
  admissible_frame_lengths [], verdict "no-admissible-frame",
  reject_reason "frame-fit": every common frame length divides 5 and is
  at most 5 ms, below the display task's 8 ms execution time, even
  though the processor is only 32% loaded.
- Coprime identity: hyperperiod on T = (3, 4, 5) equals 60 = 3*4*5,
  period_gcd 1.

## Verification

- Confirm cyclic_executive_report(SET_A) returns verdict "FITS",
  frame_length 25 and max_frame_load 12, with feasible(SET_A) True.
- Confirm hyperperiod on periods (3, 4, 5) equals 60 and period_gcd
  equals 1, the coprime identity.
- Confirm the total-load identity: sum of frame_loads(SET_A, 25) equals
  sum of C_i * (H // T_i) equals H * U within tolerance.
- Confirm feasible(SET_B) is False with reject_reason "capacity" even
  though utilization 0.6 is at most 1 (necessary, not sufficient).
- Confirm feasible(SET_C) is False with reject_reason "frame-fit" when
  no divisor of the period gcd reaches max C_i.
- Confirm every non-physical input raises ValueError: an empty task
  list, a non-dict entry, a missing C or T key, a boolean or
  non-integer C or T, a non-positive T, and a frame length that does
  not divide every task period.
- Run the contract test offline: python3
  scripts/test_cyclic_executive_scheduling.py (31 tests, deterministic).

## Related leaves

- avionics/fsw/real-time-scheduling: the priority-driven feasibility
  fence for the same (C, T) task model, the RM bound, exact
  response-time analysis and EDF full-utilization verdicts this leaf
  never computes.
- avionics/fsw/deadline-monotonic-scheduling: per-task relative
  deadlines and deadline-monotonic priority assignment beyond the
  implicit D = T model here.
- avionics/ima/ima-partitioning: the ARINC 653 major-frame partition
  window arithmetic one level above this leaf's task-level frame table.
- avionics/data-bus/mil-std-1553-bus-loading: minor-frame bus command
  and response window schedules, a different timing domain.

## Pitfalls

- Treating a low utilization as proof of feasibility: set C loads the
  processor at only 32% yet has zero admissible frame lengths, because
  the frame-fit rule f >= max C_i can fail even when U is small; U <= 1
  is necessary, never sufficient, for a FITS verdict.
- Assuming the largest admissible frame length is best: set A's larger
  admissible length 25 is the only capacity-feasible one, but in
  general a larger frame coarsens the schedule without guaranteeing
  capacity feasibility; always check feasible_frame_lengths, not just
  admissible_frame_lengths.
- Forgetting that frame 0 collects every task's synchronous release:
  every task releases a job at time 0, so frame 0 is often the
  capacity-tight frame (set A load 12 of 25, set B load 27 of 25), and
  a schedule can fail purely on this one frame even when later frames
  are lightly loaded.
- Reading a capacity rejection as a frame-fit rejection: set B rejects
  with reason "capacity" (an admissible f = 25 exists but every
  candidate over-subscribes a frame) while set C rejects with reason
  "frame-fit" (no divisor of the period gcd ever reaches max C_i); the
  two reject reasons point to different fixes, shrinking C_i for
  capacity versus raising g for frame-fit.
- Routing adjacent timing domains here: WCET estimation, priority-driven
  feasibility verdicts (real-time-scheduling), per-task relative
  deadlines and release jitter (deadline-monotonic-scheduling), ARINC
  653 partition configuration tables and MAF window durations
  (ima-partitioning), and bus command or response windows
  (data-bus/mil-std-1553-bus-loading) are not this leaf's task-level
  frame table.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline, no
network, exits 0):

    python3 scripts/test_cyclic_executive_scheduling.py

The test covers the worked sets A, B and C, the coprime hyperperiod
identity on periods (3, 4, 5), the frame-fit and capacity rejection
paths, the total-load, jobs-per-hyperperiod and slack-sum identities
over one hyperperiod, the necessary-not-sufficient utilization check,
the single-task idle-frame boundary, admissible-length enumeration
bounds, run-to-run determinism, and ValueError rejection of an empty
list, a non-dict entry, a missing key, a boolean or non-integer C or T,
a non-positive T, and a frame length that does not divide every task
period.

## Compliance

- Standards referenced, not reproduced: DO-178C (avionics software
  lifecycle context in which the scheduling analysis artifact is
  recorded) is listed reference-only per standards-map.yaml; the cyclic
  executive arithmetic above is public science (Baker and Shaw 1989,
  Locke 1992, Burns and Wellings 2009), summary-only.
- ARINC 653 is not in standards-map.yaml and is not needed here: the
  task-level frame-table arithmetic is independent of the partition
  standard text, mirroring the stance in real-time-scheduling.
- compliance: STANDARDS-REF, gated: false.
