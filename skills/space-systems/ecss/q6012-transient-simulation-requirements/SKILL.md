---
name: q6012-transient-simulation-requirements
description: "Size the timestep, window and run budget of a die-form MMIC transient simulation under ECSS-Q-ST-60-12C clause 7.2.4: derive the spectral knee of the fastest switching edge, set the largest timestep that still resolves it, extend the window past the last declared event by a full settling time, convert both into a step count graded against the run budget, and check that turn-on and turn-off are both covered. Use when a switching, pulsed or bias-stepped circuit is being simulated, a run truncates before settling, or an overnight run has to be made affordable. Refuses duplicate or out-of-window events. Trigger: ecss, q-st-60-12c, mmic-transient-simulation, switching-edge-resolution, mmic-settling-window, transient-timestep-sizing, mmic-inrush-current, transient-step-budget."
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
  tags: [ecss, q-st-60-mmic-scope, q6012-transient-simulation-requirements, mmic-transient-simulation, switching-edge-resolution, mmic-settling-window, transient-timestep-sizing, transient-step-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS MMIC — Transient Simulation Requirements (space-systems/ecss/q6012-transient-simulation-requirements)

Use when the task is the transient-simulation requirement of
ECSS-Q-ST-60-12C clause 7.2.4 — deciding how a die-form MMIC's
switch-on, switch-off and other time-varying behaviour has to be set up
in the time domain so the run actually contains the behaviour the
analysis is meant to find.

## Domain quick reference

- A transient run is bounded at both ends by different physics. The
  short end is set by the fastest edge: the timestep has to split that
  edge into enough points that overshoot and ringing exist in the
  waveform at all. The long end is set by the slowest settling time
  constant: the window has to reach past the last event by a full
  settling time or the run stops while the circuit is still moving.
- The spectral content of an edge is read from its rise time, not from
  the clock or carrier frequency. A monotonic edge carries energy up to
  a knee near 0.35 over the rise time, and energy above that knee is
  what excites the parasitic resonances the run exists to expose, so the
  sample rate implied by the timestep clears the knee by a factor rather
  than merely satisfying Nyquist.
- Settling is a residual, not an event. A first-order decay never
  arrives, so the window length follows from the residual error the
  analysis has to demonstrate through the logarithm of its reciprocal —
  one percent is about 4.6 time constants, one part in a thousand about
  6.9.
- Turn-off is not the mirror of turn-on. For an inductive or charged
  load the stressing edge is the switch-off, so a run that only covers
  the switch-on has covered the easier half; both kinds are declared
  explicitly and the absence of either is a coverage finding.
- Timestep and window multiply into a step count, and that count is the
  real constraint. When it exceeds the budget the answer is local
  refinement around the edges, never a globally coarser timestep that
  quietly removes the edge detail the run was set up for.

## Workflow

1. Validate the fastest rise time, the slowest settling time constant
   and the residual error fraction; a residual at or beyond unity, or a
   non-positive time, is an input error rather than a degenerate case.
2. Derive the edge knee and the largest timestep that resolves the edge
   to at least the minimum number of points, refusing a coarser
   points-per-edge request instead of honouring it.
3. Derive the settling time from the time constant and the residual, and
   place the stop time a full settling time past the last declared
   event.
4. Where the caller declares its own window, grade that window rather
   than silently replacing it with a sufficient one; a truncating window
   is a finding the caller has to see.
5. Validate the event schedule: recognised event kinds only, distinct
   moments, nothing outside the window.
6. Convert stop time and timestep into a step count and compare it with
   the run budget.
7. Size the switching stress the run has to reproduce — peak inrush
   through the source resistance, energy stored in the load capacitance,
   and the supply slew rate the edge imposes.
8. Report every finding: an under-sampled edge, a truncating window, a
   missing turn-on or turn-off, and a step count over budget.

## Pitfalls

- Choosing the timestep from the carrier or clock period. The edge, not
  the repetition rate, sets the short end of the run; a timestep sized
  from the period can step straight over the transition.
- Satisfying Nyquist at the knee and stopping there. The edge carries
  energy above its knee, so a sample rate merely twice the knee rounds
  the corner the analysis was set up to examine.
- Ending the window at the last event. The last event is where the
  interesting part begins; the window has to carry a full settling time
  beyond it.
- Simulating only the switch-on. Turn-off is the stressing edge for an
  inductive or charged load, and a run without it is a half-covered
  clause, not a pass.
- Coarsening the timestep globally to fit the step budget. That trades
  away the edge resolution the run exists for; refine locally around the
  edges and leave the quiescent stretches coarse.
- Treating a step count over budget as a reason to shorten the window.
  The window is set by settling physics; the budget is set by the
  machine, and only one of the two is negotiable.

## Behavior contract (gate 3)

The input validation, knee and timestep derivation, settling window,
event-schedule validation, step-count budgeting, switching-stress sizing
and the full assessment are exercised by the gate 3 contract test:
scripts/test_q6012_transient_simulation_requirements.py against
scripts/q6012_transient_simulation_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6012_transient_simulation_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
