---
name: e3301-control-system-gain-phase-margin
description: "Compute the closed-loop stability margins of a mechanism control system and grade them against ECSS-E-ST-33-01C clauses 4.7.8.1 and 4.7.8.2. Use when the task is finding the gain crossover and phase crossover of a tabulated open-loop response, reading the phase margin up from the half-turn lag and the gain margin as the reciprocal magnitude, repeating that across hot, cold, inertia and end-of-life friction cases, retaining the smallest of each, and grading them against the factor-of-two gain margin and thirty-degree phase margin. Trigger: ecss, e-st-33-01-mechanisms-scope, mechanism-loop-gain-margin, mechanism-loop-phase-margin, open-loop-gain-crossover, phase-crossover-frequency, worst-case-stability-margin, servo-loop-stability-grading."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-control-system-gain-phase-margin, mechanism-loop-gain-margin, mechanism-loop-phase-margin, open-loop-gain-crossover, phase-crossover-frequency, worst-case-stability-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Closed-Loop Gain and Phase Margin (space-systems/ecss/e3301-control-system-gain-phase-margin)

Use when the task is the stability-margin step of ECSS-E-ST-33-01C
clauses 4.7.8.1 and 4.7.8.2 -- showing that a mechanism's closed control
loop keeps a factor of two of gain margin and thirty degrees of phase
margin, not at nominal, but at the worst corner of everything the loop's
plant can do.

## Domain quick reference

- The two margins answer different questions about the same open-loop
  response. Gain margin asks how much more loop gain the plant could
  develop before the loop sustains oscillation; phase margin asks how
  much extra lag -- from a computation delay, a filter, or a structural
  mode -- it could absorb first. A loop can be generous in one and bare
  in the other.
- Gain margin is read at the phase crossover, where the loop's lag
  reaches a half turn, and it is the reciprocal of the magnitude there.
  Phase margin is read at the gain crossover, where the magnitude passes
  unity, and it is the phase measured up from that same half turn.
- The factor of two and six decibels are the same requirement written
  two ways; carrying both in the report saves the reader converting, and
  keeping them derived from one constant keeps them from drifting apart.
- Interpolation between tabulated points is done in log frequency,
  because a frequency response is a straight line there over a decade
  and a curve in linear frequency. Magnitude is interpolated in
  decibels for the same reason.
- A tabulated point sitting exactly on a crossing is used as it stands.
  Interpolating onto a point already in hand replaces an exact value
  with a rounded one, and that rounding is what makes a boundary case
  land differently on two machines.
- The requirement is written at the worst case, so a single nominal
  response cannot demonstrate it. Plant inertia, harmonic-drive
  friction at end of life, temperature-dependent motor constant and
  supply voltage all move the loop, and the worst gain margin and the
  worst phase margin usually come from different corners.

## Workflow

1. Validate each case's open-loop response: strictly increasing
   frequency, positive magnitude, finite phase in degrees. A response
   is an input, not a model to be extrapolated.
2. Find the gain crossover by interpolating the decibel magnitude to
   zero in log frequency, and read the phase there. A response that
   never reaches unity gain over its tabulated band is refused rather
   than extrapolated.
3. Find the phase crossover by interpolating the phase to the half turn
   in log frequency, and read the magnitude there. A response that
   never reaches the half turn is likewise refused.
4. Compute the gain margin as the reciprocal of that magnitude, in both
   linear and decibel form, and the phase margin as the crossover phase
   measured up from the half turn.
5. Repeat for every declared parameter case and retain the smallest
   gain margin and the smallest phase margin separately, breaking an
   exact tie on the case identifier so the selection is reproducible.
6. Grade both retained values against the required margins, absorbing
   representation error at the boundary with a named tolerance.
7. Report the per-case records, which case governed each margin, and the
   findings. A submission carrying only one case is itself a finding.

## Pitfalls

- Reading both margins at the same frequency. They sit at two different
  crossovers, and a loop whose crossovers are far apart will give
  nonsense if one frequency is used for both.
- Taking the worst case as the case with the worst phase margin and
  reporting its gain margin too. The two worst cases are usually
  different corners, and pairing them from one case understates the
  exposure.
- Extrapolating a response that never crosses unity gain inside its
  tabulated band. The crossover may be real, but it is outside the
  data, and inventing it puts a number on the report that nothing
  measured.
- Interpolating in linear frequency or linear magnitude. Over a decade
  that misplaces a crossover badly, and the margin read there is wrong
  by more than the margin itself.
- Demonstrating the margins at nominal only. The requirement is a
  worst-case one, and a nominal loop with six decibels of gain margin
  routinely has three at end-of-life friction.
- Widening the required margin to make an exact-equality case pass. An
  equality at the limit is a representation question, absorbed by the
  named tolerance inside the comparison; the required value stays as
  specified.

## Behavior contract (gate 3)

The response validation, decibel conversion, gain-crossover and
phase-crossover interpolation, gain-margin and phase-margin computation,
worst-case retention across parameter cases and the requirement grading
are exercised by the gate 3 contract test:
scripts/test_e3301_control_system_gain_phase_margin.py against
scripts/e3301_control_system_gain_phase_margin_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3301_control_system_gain_phase_margin.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
