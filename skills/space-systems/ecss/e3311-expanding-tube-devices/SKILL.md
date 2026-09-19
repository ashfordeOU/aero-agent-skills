---
name: e3311-expanding-tube-devices
description: "Derive the admissible design windows for an expanding-tube contained separation device and grade an installed one against ECSS-E-ST-33-11C clause 4.11.8. Use when the task is sizing or accepting a flattened-tube separation joint: bounding core load below by the swell needed to fracture the notched ligament and above by what the tube can contain without rupturing, bounding ligament thickness below by the flight load it carries and above by what the delivered force will sever, reporting a window that closes to nothing, and grading containment margin, contained-debris evidence and dual-end severance timing. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, expanding-tube-separation-device, contained-separation-joint, expanding-tube-core-load-window, separation-ligament-thickness-window, expanding-tube-containment-margin, dual-end-severance-timing."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-expanding-tube-devices, expanding-tube-separation-device, contained-separation-joint, expanding-tube-core-load-window, separation-ligament-thickness-window, expanding-tube-containment-margin, dual-end-severance-timing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Expanding Tube Devices (space-systems/ecss/e3311-expanding-tube-devices)

Use when the task is the contained-separation screen of
ECSS-E-ST-33-11C clause 4.11.8 -- a flattened metal tube with an
explosive core behind a notched separation plane, which swells to
part the joint and, unlike every other explosive separation device,
must not open itself.

## Domain quick reference

- Containment is not one requirement among several; it is what the
  device is for. A joint that separates perfectly and splits its tube
  has released fragments into a vehicle that chose this device
  specifically to avoid them.
- That turns the sizing into two windows rather than two minima. Core
  load has to be large enough to swell the tube far enough to
  fracture the ligament, and small enough that the pressure stays
  well under what the tube can hold.
- The ligament is bounded from both sides too, and by requirements
  from different disciplines: structures sets the floor, because the
  notched plane carries flight load right up to the moment it fires,
  and the delivered force sets the ceiling.
- Either window can close. When the structural floor rises above the
  severance ceiling there is no thickness that works, and that is a
  different finding from a thickness sitting slightly outside a
  window -- it says the concept does not close, not that a dimension
  needs tuning.
- The two windows are coupled through core load. Raising the load to
  widen the ligament window pushes the core load toward its own
  containment ceiling, which is why both are computed rather than
  checked one at a time.
- A long joint is fired from both ends, so the last place to part is
  where the two detonations meet, and that point moves toward
  whichever end fired late. The severance time is the run to that
  meeting point, not the run along the whole joint.
- Contained-debris verification is recorded evidence, not an
  inference from the containment margin. A comfortable margin with no
  test behind it leaves the device's defining property unproven.

## Workflow

1. Normalize the assembly, rejecting a non-positive core load,
   coefficient or joint dimension and a debris declaration that is
   not a boolean, because an unrecorded verification is not a pass.
2. Build the core-load window: the lower bound from the required
   stroke and the margin over the expansion coefficient, the upper
   bound from the tube burst pressure over the pressure coefficient
   and the containment margin.
3. Build the ligament window: the lower bound from limit load and the
   structural margin over ligament strength, the upper bound from the
   delivered force over the severance coefficient and its margin.
4. Report an empty window as an empty window before grading anything
   against it, and only then check the installed core load and
   ligament thickness against their bounds.
5. Grade the containment margin directly from the internal pressure
   the installed core load raises, and check the contained-debris
   verification separately.
6. Find the meeting point of the two end initiations, clamping it to
   the joint when one end is late enough that the other runs the
   whole length, take the severance time from it and grade it.

## Pitfalls

- Sizing the core load upward until the joint reliably parts. That
  search walks straight at the containment ceiling, and the device
  that always separates is the one that ruptures its tube.
- Treating the ligament as a manufacturing detail. It is a structural
  member until the instant it fires, and thinning it to guarantee
  severance removes flight-load capability that was being counted on.
- Checking the two windows independently. They share the core load,
  so a change made to open one closes the other.
- Reading an out-of-window dimension and an empty window as the same
  finding. The first is a tuning problem; the second says no
  dimension exists and the concept has to change.
- Timing the joint along its full length when it is fired from both
  ends, or timing it to the centre when one end fires late. The
  meeting point moves, and it is the only point whose arrival matters.
- Comparing a value with a window bound by bare arithmetic. Each
  bound is a quotient of two products, so a design landing exactly on
  one can sit a few units in the last place outside it; the
  comparison absorbs that while the bound stays untouched.

## Behavior contract (gate 3)

The assembly normalization, the stroke, pressure and force response
model, the two-sided core-load and ligament windows including the
empty-window case, the containment margin, the contained-debris
check, the dual-end meeting point with its clamping and the severance
timing gate, plus the per-device and set verdicts, are exercised by
the gate 3 contract test:
scripts/test_e3311_expanding_tube_devices.py against
scripts/e3311_expanding_tube_devices_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e3311_expanding_tube_devices.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
