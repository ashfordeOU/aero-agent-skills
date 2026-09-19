---
name: e3301-latching-locking-end-stops
description: "Design the latching, locking and end-stop arrangement of a spacecraft mechanism over its full range of travel under ECSS-E-ST-33-01 clauses 4.7.5.4.3 and 4.7.5.4.4. Use when an end stop has to absorb the kinetic energy of the moving assembly plus the spring energy and drive work still delivered over the travel left at contact, a latch has to capture where the assembly actually arrives without the worst-case overshoot flying past the window, every reachable travel limit needs a stop, and the locked state needs preload above its disturbance plus an observable indication. Trigger: ecss, e-st-33-01-mechanisms, mechanism-end-stop-energy-absorption, latch-capture-window, deployment-overshoot-travel, locked-state-preload-margin, end-of-travel-status-indication."
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
  tags: [ecss, e-st-33-01-mechanisms, e3301-latching-locking-end-stops, mechanism-end-stop-energy-absorption, latch-capture-window, deployment-overshoot-travel, locked-state-preload-margin, end-of-travel-status-indication]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Latching, Locking and End Stops (space-systems/ecss/e3301-latching-locking-end-stops)

Use when the task is the end-of-travel design of ECSS-E-ST-33-01
clauses 4.7.5.4.3 and 4.7.5.4.4 -- sizing the stops that arrest a
mechanism, placing the latch that captures it, and showing that the
resulting locked state holds and can be seen to hold.

## Domain quick reference

- An end stop is sized on energy, not on a static load. Three sources
  arrive at it: the kinetic energy the moving assembly carries in, the
  stored energy a spring still releases over the travel left after
  first contact, and the work a drive keeps doing if it pushes into
  the stop over that same residual travel.
- The residual travel is what makes the last two terms real. A stop
  that compresses or a latch that slides before it seats leaves the
  spring and the motor free to keep adding energy after contact, and a
  budget that stops at the kinetic term misses them entirely.
- The arriving energy is raised by a policy factor before it is
  compared with the declared absorption capability. A declared factor
  lighter than the floor is replaced by the floor and reported rather
  than accepted.
- Every travel limit the mechanism can reach needs a stop. A limit
  argued to be unreachable is declared as such, so the argument is
  visible; silence about a limit is a gap, not an exemption.
- A latch only latches where the assembly actually arrives. The
  capture window has to contain the arrival position, and the
  worst-case overshoot must not carry the assembly past the far edge of
  that window, which is the classic way a fast deployment fails to
  catch.
- The locked state has two further duties: a locking preload above the
  disturbance it holds against, and an indication, because a locked
  state that cannot be observed cannot be reported as achieved.

## Workflow

1. Declare the mechanism: identifier, travel range, and which travel
   limits are actually reachable.
2. Enter each end stop with the travel limit it sits at, the inertia
   and approach rate at contact, the residual travel after contact, the
   spring effort and drive effort still acting over that travel, the
   declared absorption capability and any declared energy factor.
3. Build the arriving energy from its three sources, raise it by the
   applied factor, and take the energy margin against the declared
   absorption capability.
4. Check limit coverage: a reachable limit with no stop is a finding,
   and a stop with no arriving energy declared is reported rather than
   scored as infinitely capable.
5. Enter each latch with its capture window, the arrival position, the
   worst-case overshoot, the locking preload, the disturbance the lock
   holds against and whether the state is indicated.
6. Grade capture, overshoot, preload margin and indication, then report
   every failing stop, every failing latch and every uncovered travel
   limit together.

## Pitfalls

- Sizing a stop on kinetic energy alone. A deployment spring that is
  still extending at contact and a motor that is still commanded both
  keep pouring energy into the stop after it is touched.
- Taking the nominal deployment rate. Rate scatter, a low resistive
  torque and a cold spring all raise the arriving energy as the square
  of the rate, so the worst-case rate is the only one worth computing.
- Placing the capture window on the nominal arrival and forgetting
  overshoot. A fast arrival flies past the far edge, the latch does not
  catch, and the assembly rebounds into a travel range nobody analysed.
- Leaving the retract-side limit without a stop because normal
  operation never goes there. A failed command, a rebound or a ground
  handling event does, and the clause asks about reachable travel, not
  intended travel.
- Reporting a lock as achieved from a commanded position. Position
  telemetry from the drive is not an indication of the locked state;
  the state itself has to be observable.
- Comparing an energy margin or a preload margin with zero by bare
  arithmetic. Both are quotients of floats, so a stop sized exactly to
  its requirement can land either side of zero; the comparisons absorb
  that representation error and report the zero-reserve condition.

## Behavior contract (gate 3)

The three energy sources and their sum, the energy factor floor, the
absorption margin and its grouping, reachable-limit coverage, the
capture window and overshoot checks, the locking preload margin and the
indication requirement are exercised by the gate 3 contract test:
scripts/test_e3301_latching_locking_end_stops.py against
scripts/e3301_latching_locking_end_stops_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3301_latching_locking_end_stops.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
