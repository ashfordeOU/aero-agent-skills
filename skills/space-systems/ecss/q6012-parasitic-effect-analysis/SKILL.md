---
name: q6012-parasitic-effect-analysis
description: "Analyze the parasitic inductance, capacitance and coupling a physical layout adds to a die-form MMIC under ECSS-Q-ST-60-12C clause 7.2.3: size bond-wire and on-die track inductance from geometry, form the coupling capacitance between adjacent conductors, convert both into reactances at the top of the operating band, locate each net's self-resonance, and grade series reactance, insertion phase error and conductor isolation against their budgets. Use when a layout or bond-plan has changed, a wire length or loop height is in question, or measured response departs from the schematic-level simulation. Refuses stubby geometry outside the thin-wire expression. Trigger: ecss, q-st-60-12c, mmic-layout-parasitics, bond-wire-inductance, mmic-coupling-capacitance, mmic-self-resonant-frequency, mmic-conductor-isolation, parasitic-reactance-budget, mmic-insertion-phase-error."
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
  tags: [ecss, q-st-60-mmic-scope, q6012-parasitic-effect-analysis, mmic-layout-parasitics, bond-wire-inductance, mmic-coupling-capacitance, mmic-self-resonant-frequency, mmic-conductor-isolation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS MMIC — Layout Parasitic Effect Analysis (space-systems/ecss/q6012-parasitic-effect-analysis)

Use when the task is the parasitic-effect analysis of ECSS-Q-ST-60-12C
clause 7.2.3 — accounting for the inductance, capacitance and coupling
that the physical realisation of a die-form MMIC adds to the circuit the
schematic describes, and deciding whether those parasitics have to be
carried into the simulated model.

## Domain quick reference

- The schematic is not the circuit. Every bond wire, every on-die track
  and every pair of conductors that face each other adds a series
  inductance, a shunt capacitance or a coupling path that was never
  drawn. At microwave frequencies these are not second-order: a
  millimetre of bond wire is of order a nanohenry, which is some tens of
  ohms of reactance in the upper Ku band.
- The reactance, not the inductance, is what the circuit sees. A
  parasitic is graded by its reactance relative to the reference
  impedance of the net it sits in, evaluated at the *highest* frequency
  the part is used at, because a parasitic that is negligible at band
  centre need not be at the top of the band.
- Every net has a self-resonance formed by its own inductance and its
  capacitance to ground. Above that frequency a nominally series
  inductance behaves as an open circuit and a nominally shunt
  capacitance as a short, so the element in the model stops representing
  the element on the die. The resonance is therefore kept a declared
  factor above the top operating frequency, not merely outside the band.
- Coupling between conductors is a divider, not a fixed number of dB.
  The aggressor drives the victim through the coupling reactance into
  the terminations the victim sees, so isolation improves as that
  reactance rises and degrades as the conductors are brought together or
  run alongside each other for longer.
- The thin-wire and flat-conductor inductance expressions are long-wire
  approximations. A stubby wire or a short, wide track is outside their
  range of validity, and the honest response is an extracted value from
  a field solver rather than a formula evaluated out of range.

## Workflow

1. Validate the interconnect geometry: wire lengths, radii and loop
   factors, track lengths, widths and thicknesses, conductor separations
   and the relative permittivity of the medium between them. A
   non-positive dimension is an input error, not a degenerate case.
2. Size the series inductance of every net from its geometry, refusing
   any net whose length-to-cross-section ratio puts it outside the
   validity range of the expression.
3. Form the coupling capacitance of every declared conductor pair from
   the facing area and the separation.
4. Convert inductances and coupling capacitances into reactances at the
   top operating frequency, and derive each net's self-resonance from
   its own inductance and its capacitance to ground.
5. Grade the series reactance against the reference impedance, the
   insertion phase error against its budget, the self-resonance against
   the floor set by the declared margin factor, and the pair isolation
   against the required value.
6. Name the net that dominates each finding, so the layout change has an
   address rather than a global instruction to tighten everything.
7. Report a layout with no declared conductor pairs as an unverified
   isolation budget, not as a pass; coupling that was never assessed is
   not coupling that was shown to be absent.

## Pitfalls

- Grading parasitics at band centre. The series reactance rises linearly
  with frequency and the isolation falls with it, so an assessment that
  is not carried out at the top of the operating band understates both.
- Treating inductance as the figure of merit. Two nets with the same
  inductance sitting in different reference impedances have different
  consequences; the reactance ratio is what the budget is written
  against.
- Checking that the self-resonance is merely outside the band. Component
  behaviour is already distorted well below resonance, which is why the
  floor is a declared multiple of the top frequency rather than the top
  frequency itself.
- Reporting a clean result from a layout in which no conductor pairs
  were declared. An empty coupling list produces no isolation finding
  for the same reason an empty test list produces no failures.
- Evaluating the thin-wire expression on a stubby wire to avoid running
  a field solver. That returns a number with no validity behind it; the
  ratio floor exists so the refusal is explicit.
- Widening a budget so an exact-equality case passes. An equality at the
  limit is a floating-point representation question, handled by the
  tolerance inside the comparison, and the budget stays as specified.

## Behavior contract (gate 3)

The geometry validation, bond-wire and track inductance expressions,
coupling capacitance, reactance conversion, self-resonance, phase-error
and isolation grading, and the full assessment are exercised by the gate
3 contract test:
scripts/test_q6012_parasitic_effect_analysis.py against
scripts/q6012_parasitic_effect_analysis_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6012_parasitic_effect_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
