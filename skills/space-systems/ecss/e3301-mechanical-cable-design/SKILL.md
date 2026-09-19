---
name: e3301-mechanical-cable-design
description: "Design a mechanism cable drive so its preload, flexure life and end fittings reach the required life under ECSS-E-ST-33-01C clause 4.7.3.4.3. Use when the task is setting a preload high enough that the returning run never goes slack under the drive force, checking the pulley-to-cable diameter ratio against the bend-ratio floor, forming the outer-strand bending stress, accumulating the flexure passes the mission demands and comparing them with the allowable bends at the tension ratio actually run, and grading a swaged or potted termination against its efficiency-derated strength. Trigger: ecss, e-st-33-01c, cable-drive-preload, cable-slack-run-tension, pulley-bend-ratio, cable-flexure-life, outer-strand-bending-stress, cable-end-fitting-efficiency, cable-drive-margin-of-safety."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-mechanical-cable-design, cable-drive-preload, pulley-bend-ratio, cable-flexure-life, outer-strand-bending-stress, cable-end-fitting-efficiency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Cable-Drive Design (space-systems/ecss/e3301-mechanical-cable-design)

Use when the task is the cable-drive design of ECSS-E-ST-33-01C clause
4.7.3.4.3 — sizing the preload, the pulley geometry, the flexure life and the
end fittings of a cable or tape drive so the drive reaches the life the
mechanism is required to deliver.

## Domain quick reference

- A cable drive is preloaded so that both runs of the loop stay in tension.
  The drive force is reacted differentially: one run gains half of it, the
  other loses half. The design constraint is therefore on the returning run,
  not on the loaded one, and it is a functional constraint — a run that
  reaches zero tension leaves the groove, loses the position reference and
  can trap a strand under the next wrap.
- The pulley-to-cable diameter ratio is the single strongest driver of cable
  life. It is a cable-level ratio, but the fibre that actually fatigues is an
  individual strand, so the bending stress is formed on the strand diameter:
  a construction with many fine strands bends far more kindly at the same
  cable diameter than one with few coarse ones.
- Flexure life is counted in bend events, not mechanism cycles. Every pulley
  the cable passes contributes, and a run that passes a pulley out and back
  contributes twice per cycle. A four-pulley layout spends life eight times
  faster than a cycle count suggests.
- Life at a given bend ratio falls off as a power of the tension ratio — the
  fraction of breaking load the tight run actually carries — so a life curve
  read at one reference tension has to be derated before it is compared with
  the mission demand.
- An end fitting develops only a fraction of the cable breaking load. A swage
  or a potted socket has a characteristic efficiency, and on a well-chosen
  cable the fitting, not the cable, is what the strength margin is set by.

## Workflow

1. Split the drive force around the preload into a tight-run and a
   returning-run tension. Report a negative returning-run value as computed
   rather than clamping it, so the slack condition is visible.
2. Form the pulley-to-cable bend ratio and compare it with the floor the
   cable construction carries; refuse a geometry where the cable is not
   smaller than the pulley.
3. Form the outer-strand bending stress from the modulus, the strand diameter
   and the pulley diameter.
4. Accumulate the bend events the mission demands from the mission cycles,
   the pulley count and the passes each pulley sees per cycle, then apply the
   life factor.
5. Read the allowable bend events off the bend-ratio life curve by log-log
   interpolation, refusing to extrapolate past the tabulated span, and derate
   them for the tension ratio the tight run actually runs at. A tension ratio
   that reaches unity is not a flexure-life case and is refused.
6. Compute the strength margin of safety twice — against the cable breaking
   load and against the efficiency-derated fitting strength — and name which
   of the two governs.
7. Report the tensions, the bend ratio and stress, the demanded and allowable
   bend events, both margins and every finding, absorbing an exact zero
   margin with a named tolerance rather than by relaxing the safety factor.

## Pitfalls

- Sizing the preload on the tight run. The tight run only gets tighter; it is
  the returning run that decides whether a preload is enough, and half the
  drive force is the number it has to beat.
- Forming the bending stress on the cable diameter. That over-states the
  stress by the strand-count ratio and turns a perfectly good construction
  into an apparent failure — or, when a bend-ratio floor is met with a coarse
  construction, hides a real one.
- Counting mechanism cycles as bend events. The pulley count and the passes
  per pulley multiply, and a layout change that adds an idler adds life
  consumption without changing a single requirement.
- Reading a flexure-life curve without derating for tension. The curve belongs
  to a reference tension ratio; a drive run at twice that ratio has a small
  fraction of the tabulated life at the same bend ratio.
- Extrapolating the life curve to cover an unusually large pulley. Past the
  tabulated span the curve shape is not known, and inventing life data is
  worse than refusing the point.
- Grading the drive against the cable breaking load alone. The termination is
  usually the weaker item, and a margin taken on the cable can be positive
  while the fitting margin is negative.

## Behavior contract (gate 3)

The run-tension split, bend-ratio and outer-strand stress geometry, bend-event
accumulation, log-log life-curve interpolation with tension derating,
termination efficiency and the two strength margins are exercised by the gate
3 contract test: scripts/test_e3301_mechanical_cable_design.py against
scripts/e3301_mechanical_cable_design_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e3301_mechanical_cable_design.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
