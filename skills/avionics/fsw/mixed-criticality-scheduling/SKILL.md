---
name: mixed-criticality-scheduling
description: "Use when you must decide the offline schedulability of an avionics flight software task set under the dual-criticality execution-time model: each task carries the C_LO and C_HI execution-time estimates with C_HI at least C_LO, run the lo-criticality-mode fixed-point response-time iteration over the C_LO estimates for every task, then run the hi-criticality-mode amc-rtb fixed point after the criticality-mode change, with higher-priority LO tasks charged at C_LO and higher-priority HI tasks charged at C_HI in the interference sum. Produces the per-task lo-mode response times and the LO-mode feasible verdict, the hi-mode response times of the HI tasks under the AMC-rtb bound with the HI-mode feasible verdict, the overall mixed-criticality feasible verdict, and the divergence verdict when an iterate crosses a deadline. Trigger: mixed criticality scheduling, amc rtb analysis, dual criticality execution time, lo mode feasibility, hi mode response time, criticality mode change."
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
  tags: [mixed-criticality-scheduling, amc-rtb-analysis, dual-criticality-execution-time, hi-criticality-mode-rta, lo-criticality-mode-rta, criticality-mode-change-rta]
  version: 0.1.0
  author: AeroSkills
---

# Mixed-Criticality Scheduling (avionics/fsw/mixed-criticality-scheduling)

Use when the task is deciding the offline schedulability of an
avionics flight software task set under the dual-criticality
execution-time model: each task carries a low-criticality execution
time estimate C_LO and a high-criticality estimate C_HI, and the
schedule must be verified twice, once in the lo-criticality mode over
the C_LO estimates and once again in the hi-criticality mode after the
criticality-mode change, when a HI task overruns its LO budget. This
leaf implements the AMC-rtb fixed point of Baruah, Burns and Davis
over the Vestal dual-criticality task model, pure Python, stdlib only.
It pairs with avionics/fsw/real-time-scheduling for the single-estimate
periodic (C, T) model this leaf extends, and with
avionics/do178c/planning for the software level context that motivates
the two execution-time estimates (reference-only here, never
determined by this leaf).

## Domain quick reference

- Task model: {name, criticality, C_LO, C_HI, T, D}, criticality "LO"
  or "HI", C_HI at least C_LO, D no greater than T, one time unit. A
  LO task carries no high estimate, so its C_HI equals its C_LO.
- Priority order: the task list IS the fixed-priority order, index 0
  the highest priority, deadlines non-decreasing (deadline-monotonic
  order). Higher-priority set hp(i) = {j : j < i}.
- LO-mode response time (classic fixed-point RTA over the C_LO
  estimates): R_i(LO) = C_i(LO) + sum over j in hp(i) of
  ceil(R_i(LO) / T_j) * C_j(LO), iterated from R = C_i(LO) to a fixed
  point. Feasible iff the converged value is at most D_i.
- HI-mode response time (AMC-rtb bound, HI tasks only, after the
  criticality-mode change): R_i(HI) = C_i(HI) + sum over j in hp(i)
  with criticality LO of ceil(R_i(HI) / T_j) * C_j(LO) + sum over j in
  hp(i) with criticality HI of ceil(R_i(HI) / T_j) * C_j(HI), iterated
  from R = C_i(HI) to a fixed point. Higher-priority LO tasks are
  charged their LO estimate (their jobs are dropped only after the
  mode change); higher-priority HI tasks are charged their HI estimate
  (overrun possible). Feasible iff the converged value is at most D_i.
- Divergence rule: both maps are monotone non-decreasing in R, so an
  iterate strictly past D_i can never converge to a feasible value:
  the solve reports None. A solve that has not converged after
  MAX_RTA_ITERATIONS passes also reports None.
- Mode verdicts: LO feasible iff every task's LO-mode solve converges;
  HI feasible iff every HI task's HI-mode solve converges (an all-LO
  set has an empty HI guarantee list and a vacuously true HI verdict);
  the whole-set verdict is LO feasible and HI feasible.
- Utilization context (reported, never a verdict): U_LO = sum over all
  tasks of C_LO / T, U_HI = sum over HI tasks of C_HI / T.
- Units are one time unit throughout (ms in the worked example below).
  DO-178C frames the software-level context that motivates the
  dual-estimate model as reference-only; no level is ever determined
  here.

## Workflow

1. Build the task list in deadline-monotonic priority order (index 0
   the highest priority, D non-decreasing) with each task's
   criticality, C_LO, C_HI, T and D.
2. Run the lo-criticality-mode fixed-point response-time iteration
   over the C_LO estimates for every task with lo_response_times (or
   lo_response_time for a single task).
3. Run the hi-criticality-mode AMC-rtb fixed point for the
   HI-criticality tasks after the criticality-mode change with
   hi_response_times (or hi_response_time for a single task).
4. hi_response_time and hi_response_times guarantee HI tasks only: a
   HI-mode call on a LO-criticality index raises ValueError.
5. Inspect the AMC-rtb interference sum on any HI task: higher-priority
   LO tasks are charged at C_LO, higher-priority HI tasks are charged
   at C_HI, both arms live in the one equation.
6. Get the whole-set verdict with feasible(tasks): LO feasible and HI
   feasible.
7. Read the utilization context (U_LO, U_HI) from the response-time
   dicts as reported context, never as a verdict on its own.
8. Confirm the deterministic checks, including ValueError rejection of
   non-physical inputs, with the contract test
   scripts/test_mixed_criticality_scheduling.py.

## Worked example

Task set A, three avionics fsw processes in ms, in deadline-monotonic
priority order (deadlines 10, 20, 50 ms ascending, each equal to its
period):

- flight-control: criticality HI, C_LO 1.0, C_HI 3.0, T 10.0, D 10.0
  (the HI task whose overrun past its 1 ms LO budget forces the
  criticality-mode change).
- guidance: criticality LO, C_LO 3.0, C_HI 3.0, T 20.0, D 20.0 (a LO
  task, dropped after the mode change, higher priority than
  health-monitor so it feeds the AMC-rtb LO interference arm).
- health-monitor: criticality HI, C_LO 4.0, C_HI 10.0, T 50.0, D 50.0
  (the bottom HI task whose HI-mode equation carries both arms).

LO-mode responses (module output): lo_response_times(SET_A) gives
response_times [1.0, 4.0, 8.0] ms against deadlines [10, 20, 50] ms,
feasible True, utilization 0.33. flight-control converges at its own
C_LO 1.0 (no higher-priority load); guidance visits 3.0 then 4.0
(4 = 3 + ceil(4/10) * 1.0); health-monitor visits 4.0 then 8.0
(8 = 4 + ceil(8/10) * 1.0 + ceil(8/20) * 3.0).

HI-mode responses after the criticality-mode change (module output):
hi_response_times(SET_A) covers the HI tasks only, names
[flight-control, health-monitor], response_times [3.0, 19.0] ms,
feasible True, utilization 0.5 (3/10 + 10/50). flight-control
converges at its own C_HI 3.0; health-monitor's fixed point
R = 10.0 + ceil(R/10) * 3.0 + ceil(R/20) * 3.0 visits 10.0, 16.0 and
converges at 19.0 (10 + ceil(19/10) * 3 + ceil(19/20) * 3 = 10 + 6 + 3
= 19), the higher-priority HI flight-control task charged at its C_HI
3.0 and the higher-priority LO guidance task charged at its C_LO 3.0
in the same equation.

Mode monotonicity: flight-control 3.0 is at least its LO response 1.0,
and health-monitor 19.0 is at least its LO response 8.0, the cost of
the C_HI overruns. feasible(SET_A) is True.

No-overrun collapse: with every C_HI set equal to C_LO (flight-control
C_HI 1.0, health-monitor C_HI 4.0), hi_response_times gives
[1.0, 8.0], each HI response exactly its LO response.

Task set B (HI overload, the divergence verdict): flight-control HI
C_LO 1.0, C_HI 6.0; guidance LO C_LO 3.0, C_HI 3.0; health-monitor HI
C_LO 4.0, C_HI 30.0, same periods and deadlines as set A. LO mode is
unchanged and feasible ([1.0, 4.0, 8.0]). In HI mode flight-control
converges at 6.0, but health-monitor's first AMC-rtb pass gives
30 + ceil(30/10) * 6 + ceil(30/20) * 3 = 54.0, strictly past its D 50
ms, so the solve reports None: hi_response_times(SET_B) gives
[6.0, None], feasible False, utilization 1.2, and feasible(SET_B) is
False.

## Verification

- Confirm lo_response_times(SET_A) gives response_times
  [1.0, 4.0, 8.0], feasible True, utilization 0.33, and
  hi_response_times(SET_A) gives names [flight-control,
  health-monitor], response_times [3.0, 19.0], feasible True,
  utilization 0.5.
- Confirm the plug-back identity at the converged health-monitor HI
  response: 19.0 = 10.0 + ceil(19/10) * 3.0 + ceil(19/20) * 3.0.
- Confirm hi_response_time on a LO-criticality index raises
  ValueError ("task 1 is LO-criticality; HI-mode analysis guarantees
  HI tasks only") and that an all-LO set returns an empty HI
  guarantee list with feasible True.
- Confirm set B diverges in HI mode (health-monitor reports None on
  its first AMC-rtb pass past D 50) while its LO mode stays feasible.
- Confirm every non-physical input (empty list, missing key, boolean
  or non-positive C_LO/C_HI/T/D, C_HI below C_LO, a LO task with
  C_HI above C_LO, D above T, a non-deadline-monotonic order, an
  out-of-range index, a HI-mode call on a LO index) raises ValueError.
- Run the contract test offline: python3
  scripts/test_mixed_criticality_scheduling.py (35 tests,
  deterministic).

## Related leaves

- avionics/fsw/real-time-scheduling: the single-execution-time
  implicit-deadline (C, T) model this leaf extends with a second,
  high-criticality execution-time estimate and a mode change; the
  LO-mode phase reproduces its classic response-time results exactly
  on the same values.
- avionics/fsw/deadline-monotonic-scheduling: per-task deadlines
  D not equal to T with release jitter, for a single execution-time
  estimate; this leaf stays on the implicit-deadline (D = T) sets.
- avionics/fsw/shared-resource-access-control: the blocking-term
  extension of the single-estimate model; this leaf carries no
  blocking term.
- avionics/do178c/planning: software level and DAL determination, the
  context that motivates the C_LO/C_HI split; this leaf never
  determines a level.

## Pitfalls

- Reusing the LO-mode response for the HI verdict: the HI-mode
  response is a separate AMC-rtb fixed point, never the LO-mode value;
  in the worked example health-monitor's LO response is 8.0 but its HI
  response is 19.0, the cost of the criticality-mode change.
- Charging a higher-priority LO task at its C_HI in the HI-mode
  interference sum: a LO task never carries a C_HI different from its
  C_LO, and is charged at C_LO in the AMC-rtb equation, because LO
  jobs are dropped only after the mode change, not before.
- Including a LO task in the HI-mode guarantee list: hi_response_times
  reports HI tasks only; guidance (LO) never appears in the HI names
  or response times even though it interferes with health-monitor's
  HI response.
- Treating an out-of-deadline iterate as still converging: the moment
  an iterate crosses the task's own deadline the solve reports None
  immediately (set B, health-monitor's first pass at 54.0 past D 50),
  it is not run further to see if it might return.
- Mistaking this leaf for a level-determination tool: C_LO and C_HI
  are execution-time estimates, not a software level or DAL; level
  determination stays with avionics/do178c/planning.
- Applying this leaf to a single-estimate (C, T) task set: a task with
  no HI estimate belongs to avionics/fsw/real-time-scheduling; this
  leaf's model requires the C_LO/C_HI pair and criticality tag on
  every task.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_mixed_criticality_scheduling.py

The test covers the worked set A LO-mode and HI-mode response times
and utilization, the AMC-rtb two-arm interference structure and its
plug-back identity, the HI-mode guarantee scope (LO index rejection,
all-LO empty guarantee list), mode monotonicity and the no-overrun
collapse identity, the set B HI-overload divergence, the single-task
closed forms, the all-LO identity against the pack sibling's classic
results, the LO-mode overload divergence pattern, determinism across
runs, and ValueError rejection of every non-physical input enumerated
above.

## Compliance

- Standards referenced, not reproduced: DO-178C (RTCA, joint EUROCAE
  ED-12C) frames the avionics software lifecycle context in which the
  scheduling analysis artifact is recorded, per standards-map.yaml.
  The AMC-rtb response-time bound is public science (Baruah, Burns and
  Davis, RTSS 2011, over the Vestal dual-criticality task model, RTSS
  2007), summary-only; no standard text is reproduced and no software
  level or DAL is ever determined by this leaf.
- compliance: STANDARDS-REF, gated: false.
