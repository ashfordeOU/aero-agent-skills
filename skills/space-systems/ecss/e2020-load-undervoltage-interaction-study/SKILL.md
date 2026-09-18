---
name: e2020-load-undervoltage-interaction-study
description: "Analyze whether a load carrying its own undervoltage protection drives its supplying limiter into a repetitive overload cycle. Use when clause 5.3.5.1.1 of ECSS-E-ST-20-20C is studied: take the branch limit value and trip-off delay, the load inrush and the voltage the branch holds in limitation, decide whether the load-side protection trips and then releases, and accumulate the limiter timer across windows under its declared retention to find whether the branch ever latches off, on which cycle, and what thermal duty the pass element carries meanwhile. Trigger: ecss, e-st-20-20c-clause-5-3-5-1-1, load-side-undervoltage-protection, repetitive-overload-cycle, limiter-trip-off-delay-accumulation, load-restart-oscillation, limitation-window-duty, undervoltage-recovery-hysteresis, pass-element-cycle-energy."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-20-20-power-supply-interface-scope, e2020-load-undervoltage-interaction-study, load-side-undervoltage-protection, repetitive-overload-cycle, limiter-trip-off-delay-accumulation, load-restart-oscillation, limitation-window-duty, undervoltage-recovery-hysteresis, pass-element-cycle-energy]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply Interfaces -- Load Undervoltage Interaction Study (space-systems/ecss/e2020-load-undervoltage-interaction-study)

Use when the task is clause 5.3.5.1.1 of ECSS-E-ST-20-20C -- a user
equipment carries its own undervoltage protection, and the study is
whether that protection, sitting on the load side of a limited branch,
can set up an overload pattern that repeats instead of resolving.

## Domain quick reference

- The loop nobody drew closes like this. The load energises and demands
  more than its branch limit. The limiter holds the current at the limit
  value and the branch output collapses towards whatever the load pulls
  at that current. The load's own undervoltage protection reads the
  collapse as a failed supply and switches the load off. The demand
  disappears, the branch recovers to nominal, the protection releases,
  the load energises again -- and the same event repeats.
- The pattern survives because the limiter is denied its one exit. A
  latching limiter latches only after the branch has stayed in
  limitation for the whole trip-off delay, and the load-side protection
  removes the demand long before that. Each limitation window is shorter
  than the delay, so the branch never reaches the condition that would
  end the sequence and annunciate the failure.
- What decides whether it terminates is the limiter's timer between
  windows. A timer that resets fully never accumulates past one window,
  and the cycle runs for as long as the bus is powered. A timer that
  retains part of its count creeps upward towards a ceiling set by the
  window and the retention, and latches only if that ceiling reaches the
  delay. A true integrator latches after a predictable number of cycles.
- Two harmless-looking cases sit either side of the interaction. A load
  whose protection trips above the held voltage never drops out at all,
  so the limiter runs its full delay and the failure shows once. A load
  whose release threshold sits above the recovered bus never comes back,
  so the branch stays healthy and the load stays dead.
- The cost while the pattern runs is thermal, not electrical. The pass
  element stands off nearly the whole bus at the limit value for every
  window, and repeats it at the cycle rate, which is a duty no
  single-event pulse rating covers.

## Workflow

1. Validate the branch and the load, including the ordering of the
   undervoltage trip and release thresholds; an inverted hysteresis is
   an input error, not a fast cycle.
2. Decide whether the load provokes limitation at all by comparing its
   inrush with the branch limit.
3. Compute the output voltage the branch holds during limitation from
   the limited current and the effective load resistance, capped at the
   bus, and decide whether the load-side protection reads it as an
   undervoltage.
4. Compare the protection's detection delay with the trip-off delay. A
   detection slower than the delay means the branch latches first and
   there is no cycle to study.
5. Check the protection releases on the recovered bus; if it does not,
   the load simply stays off.
6. Form the cycle period from the detection and release delays and the
   limitation duty inside it.
7. Accumulate the limiter timer across windows under the declared
   retention, take the ceiling it converges on, and report the cycle the
   branch latches on, or that it never does.
8. Close with the findings a designer acts on: an unannunciated endless
   cycle, a load that never starts, and the energy the pass element
   absorbs per cycle.

## Pitfalls

- Reading the repetitive cycle as a load fault. Both halves are behaving
  exactly as specified; the defect is that the two protections were
  sized against each other by nobody.
- Assuming the branch will eventually latch and end it. A limiter whose
  timer resets between windows accumulates nothing, and the sequence has
  no terminating condition at all.
- Taking the steady-state ceiling as the answer on its own. A ceiling
  above the trip-off delay says the branch latches, but not on which
  cycle, and the number of cycles is what the thermal duty is counted
  over.
- Sizing the load-side protection detection delay downward to be safe. A
  faster detection makes each limitation window shorter, which makes the
  cycle more persistent, not less.
- Judging the pass element by one limitation window. The window repeats
  at the cycle rate, so the relevant quantity is the energy per cycle
  against the duty, not the single-pulse rating.
- Comparing a held voltage or an accumulated time against a threshold by
  bare arithmetic. Both are products of floats that can land a few units
  in the last place either side of a threshold written in another unit,
  so each comparison absorbs that error while the threshold itself is
  never moved.

## Behavior contract (gate 3)

The branch and load validation, limitation entry, held output voltage,
undervoltage trip and release decisions, cycle period and duty, timer
accumulation, steady-state ceiling, latch-off cycle, pass-element cycle
energy and the interaction categories are exercised by the gate 3
contract test:
scripts/test_e2020_load_undervoltage_interaction_study.py against
scripts/e2020_load_undervoltage_interaction_study_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_load_undervoltage_interaction_study.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
