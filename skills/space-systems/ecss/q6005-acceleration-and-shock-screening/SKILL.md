---
name: q6005-acceleration-and-shock-screening
description: "Evaluate the acceleration and shock screening applied to a hybrid microcircuit under ECSS-Q-ST-60-05C clause 10.3.5. Use when the task is setting the constant-acceleration condition a package owes from its mass, choosing the axes the load has to act along for how the elements are mounted, sizing a half-sine shock pulse by peak and duration rather than peak alone, computing the inertial force an element puts across its bonded area, and grading the post-stress drift and loose-element evidence the screen was run to expose. Trigger: ecss, q-st-60-05c, hybrid-constant-acceleration-condition, hybrid-screening-axis-selection, hybrid-shock-pulse-waveform, hybrid-die-attach-inertial-load, hybrid-post-screen-drift-limit, hybrid-loose-element-evidence."
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
  tags: [ecss, q-st-60-05-hybrid-scope, q6005-acceleration-and-shock-screening, hybrid-constant-acceleration-condition, hybrid-screening-axis-selection, hybrid-shock-pulse-waveform, hybrid-die-attach-inertial-load, hybrid-post-screen-drift-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Screening — Acceleration and Shock Screening (space-systems/ecss/q6005-acceleration-and-shock-screening)

Use when the task is the mechanical stress screen of ECSS-Q-ST-60-05C
clause 10.3.5 — deciding what level a hybrid owes, along which axes, with
what shock pulse, and whether the run that was performed exposed the weak
attachments and loose internal elements it exists to find.

## Domain quick reference

- The level is chosen from the hardware, not from a house default.
  Constant acceleration loads every internal attachment with an inertial
  force, and that force is the mass of the element times the level. A
  heavy package therefore takes a lower condition than a light one:
  applying the same level to both applies the same number, not the same
  stress, and the heavier one is the one that gets over-stressed.
- The axes come from how the elements are mounted. The axis normal to
  the die attach plane is the one that lifts an element off its
  substrate, and it is never optional. A stacked element owes both
  senses of that axis because a stack can separate either way; a
  cantilevered or overhung element owes the lateral axes too, since the
  load that opens its attachment is not the one that opens a flat bond.
- A shock pulse is a peak and a duration together. The velocity change a
  half-sine imparts is proportional to both, so a very short pulse at a
  high peak and a long pulse at a low peak are different screens even
  when one of the two numbers matches. A pulse is accepted only inside
  a stated fraction of its nominal duration, because the programmer and
  the fixture together set the shape.
- A screen has to be survivable by compliant hardware. The inertial
  force over the bonded area is a stress and the attach medium has a
  capability; an epoxy attachment and a eutectic one do not carry the
  same number. A level whose stress exceeds the capability does not
  find weak attachments, it manufactures failures in good ones, and the
  finding belongs to the screen, not to the unit.
- The screen closes electrically. A mechanical stress with no
  measurement after it has demonstrated nothing, because the element it
  shook loose is only evidence once something looks. Drift against the
  pre-stress reading and loose-element evidence are separate findings
  and both are reported.

## Workflow

1. Validate each unit record: identifier, package and element mass,
   bonded area, attach medium, mounting style, level and axes applied,
   shock condition with its measured peak and duration, and the
   post-stress outcome. An unknown mounting style, an unknown attach
   medium, an unknown or repeated axis and a non-positive mass are
   input errors, not degenerate cases to clamp.
2. Read the condition the package mass owes and the level in g behind
   it, then compare it with the level the run actually applied.
3. Read the axes the mounting style owes, and name each axis the run
   never exercised rather than reporting a single pass or fail.
4. Bound the shock pulse: the peak against its condition, and the
   duration against the window its nominal length allows.
5. Compute the inertial force on the element, the stress that force
   puts across the bonded area, and the margin the attach medium has
   over it. A negative margin is a finding against the screen.
6. Grade what the screen returned: a missing post-stress measurement,
   drift above the limit, and loose-element evidence are each their own
   finding, absorbed at the boundary with a named tolerance rather than
   by widening the limit.
7. Aggregate the lot: report passed and failed units separately, the
   reject fraction, and whether that fraction leaves the lot itself
   acceptable or refuses the whole batch.

## Pitfalls

- Applying one house level to every package. The stress is mass times
  level, so a single level under-stresses the light parts and
  over-stresses the heavy ones, and only the second failure is visible.
- Running the normal axis and calling the screen complete. A
  cantilevered element separates under a lateral load that a normal-axis
  run never applies, and the part ships with the attachment untested.
- Matching the shock peak and ignoring the duration. The velocity change
  scales with both; a pulse half as long is half the screen at the same
  peak, and the number on the report looks identical.
- Treating a broken attachment as a found defect when the screen was
  harder than the attach medium can carry. Good hardware fails that
  run, the yield drops, and the conclusion drawn is about the parts
  instead of about the level.
- Closing the screen on a visual check. Without a repeated electrical
  measurement there is no drift to compare and a shaken-loose element
  inside a sealed cavity leaves no outward sign at all.

## Behavior contract (gate 3)

The condition selection, axis selection, shock-pulse bounding, inertial
force and attachment-stress computation, margin grading, post-stress
outcome checks and lot aggregation are exercised by the gate 3 contract
test: scripts/test_q6005_acceleration_and_shock_screening.py against
scripts/q6005_acceleration_and_shock_screening_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_acceleration_and_shock_screening.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
