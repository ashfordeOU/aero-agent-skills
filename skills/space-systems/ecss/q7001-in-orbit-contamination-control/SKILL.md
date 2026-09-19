---
name: q7001-in-orbit-contamination-control
description: "Model the contamination a spacecraft inflicts on its own sensitive surfaces once in orbit. Use when material outgassing, thruster plume backflow, venting and released particles all reach an optic or a radiator and the mission deposition allocation has to be shown to hold. Integrates each decaying outgassing source analytically over the mission window, carries it to the surface through a view factor and a temperature-dependent sticking coefficient, adds the backflow share of the firings that can see it, converts deposited mass per area into a film thickness, keeps released particles on their own obscuration account, and names the dominant source. Trigger: ecss, q-st-70-01, in-orbit-molecular-deposition, spacecraft-outgassing-decay, thruster-plume-backflow, surface-sticking-coefficient, deposited-film-thickness, mission-deposition-allocation."
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
  tags: [ecss, q-st-70-01-cleanliness-contamination-control, q7001-in-orbit-contamination-control, in-orbit-molecular-deposition, spacecraft-outgassing-decay, thruster-plume-backflow, surface-sticking-coefficient, deposited-film-thickness, mission-deposition-allocation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Contamination Control — In Orbit (space-systems/ecss/q7001-in-orbit-contamination-control)

Use when the task is the in-orbit contamination control of ECSS-Q-ST-70-01 —
showing that what the spacecraft emits at itself over the mission stays inside
the allocation its sensitive surfaces were designed around. This leaf takes
over where the launch-site leaf stops.

## Domain quick reference

- Outgassing is a decaying source, not a rate. The specific rate falls roughly
  exponentially with a material time constant, so the mass emitted over a
  window is the analytic integral of that decay, and a mission ten time
  constants long emits barely more than one five constants long.
- Emitted is not arrived, and arrived is not retained. The view factor decides
  what reaches the surface; the sticking coefficient, which falls as the
  receiving surface warms, decides what stays. A warm surface can be inside its
  allocation only because it is warm, which is a thermal assumption the budget
  is quietly resting on.
- Thruster plume backflow is a separate source with a separate mechanism. A
  small fraction of the expelled propellant turns back into the hemisphere
  behind the nozzle, so a thruster that never points at the surface can still
  deposit on it, and the total depends on propellant mass expelled rather than
  on firing count.
- Particles and films answer different requirements. A film changes
  transmission and absorptance continuously; released particles obscure area
  and scatter. Adding a particle count into a film thickness loses both, so the
  two are budgeted on separate accounts.
- Thickness, not mass, is what an optical or thermal requirement is written
  against, and the conversion needs the deposit density — an assumed density is
  an assumption to be stated, not a constant to be hidden.
- The dominant source is the output that matters most. A budget that closes
  says nothing about what to fix if it stops closing; the ranked contributions
  say where the next kilogram of control belongs.

## Workflow

1. Validate each source: a positive outgassing area, a positive initial
   specific rate, a positive decay time constant and a view factor inside the
   unit interval.
2. Integrate the decay analytically over the mission window rather than
   stepping it, so the result does not depend on a step size.
3. Multiply by the view factor and the sticking coefficient at the receiving
   surface temperature, and divide by the receiving area, to get each source's
   deposit per unit area.
4. Add the thruster term: for every firing, the propellant mass times the
   backflow fraction times the view factor, retained by the same sticking
   coefficient.
5. Accumulate released particles into an obscuration figure on their own
   account, scaled by the fraction actually captured by the surface.
6. Convert the total deposit into a film thickness through the deposit density
   and compare it with the allocation, treating a result on the boundary as
   inside it through a named tolerance.
7. Report the per-source contributions, the totals, the margins, the dominant
   source and any finding — including a surface warm enough to retain nothing.

## Pitfalls

- Treating the outgassing rate as constant over the mission. A constant rate
  turns a source that has largely finished in a month into one that runs for
  years, and the overestimate hides the sources that actually matter.
- Budgeting emitted mass instead of retained mass. Without the view factor and
  the sticking coefficient the number is about the spacecraft, not about the
  surface, and it will be wrong by orders of magnitude in either direction.
- Assuming a thruster pointing away cannot contaminate. Backflow is what the
  term describes; the view factor to the backflow hemisphere is what decides
  it, not the thrust direction.
- Adding particle counts into the film budget. The two obscure differently and
  fail different requirements; combining them makes neither testable.
- Quoting a thickness without the density behind it. The conversion from mass
  per area is not free, and a different assumed density moves the answer
  proportionally.
- Using a strict inequality on a sum of exponentials at the allocation
  boundary. The comparison carries a named tolerance so the same budget does
  not pass on one machine and fail on another.

## Behavior contract (gate 3)

The source validation, analytic decay integral, sticking taper, per-source
deposition, thruster backflow, released-particle obscuration, thickness
conversion and the allocation comparison with its dominant-source ranking are
exercised by the gate 3 contract test:
scripts/test_q7001_in_orbit_contamination_control.py against
scripts/q7001_in_orbit_contamination_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_in_orbit_contamination_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
