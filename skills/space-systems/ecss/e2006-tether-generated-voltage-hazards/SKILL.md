---
name: e2006-tether-generated-voltage-hazards
description: "Use when compute the potentials a conducting tether develops while it is carried through a planetary magnetic-field, and grade the hazards those potentials create, per ECSS-E-ST-20-06C clause 10.2.1: derive the motional-electric-field from orbital-velocity and flux-density, project it along the deployed line for the end-to-end electromotive-force, split that force about the plasma-floating point, then band each exposed end against its arc-onset threshold, each insulated span against its withstand rating, and every reachable end against the ground-handling touch-potential limit. Trigger: ecss, e-st-20-electrical-scope, e2006-tether-generated-voltage-hazards, electrodynamic-tether, motional-emf, tether-end-potential, arc-onset-threshold, touch-potential-limit, plasma-floating-potential."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-tether-generated-voltage-hazards, electrodynamic-tether, motional-emf, tether-end-potential, arc-onset-threshold, plasma-floating-potential]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Design — Tether-Generated Potential Hazards (space-systems/ecss/e2006-tether-generated-voltage-hazards)

Use when the task is the hazard assessment of ECSS-E-ST-20-06C clause
10.2.1 — quantifying the potentials that a conducting tether develops
across a moving spacecraft system, and checking each place those
potentials appear against the limit that governs it.

## Domain quick reference

- A conductor carried through a magnetic-field sees an induced field
  equal to the cross product of its velocity with the flux density.
  Only the field component across the velocity contributes, so a line
  flying along the field lines sees nothing; in a typical low orbit the
  induced field runs to a couple of tenths of a volt per metre, which
  is why a kilometre-class deployed line reaches hundreds of volts
  while a metre-class one does not.
- Only the projection of that induced field along the deployed line
  integrates into an end-to-end electromotive-force. A line lying
  across the induced field develops no end-to-end force at all, and
  past ninety degrees the polarity reverses. Taking the induced field
  magnitude straight into the end-to-end figure is the single most
  common overstatement in this clause.
- The line floats where the electron current it collects balances the
  ion current it collects, and that balance point decides how the
  end-to-end force is shared between the two ends. A tether with an
  effective electron emitter at one end sits almost entirely positive
  with respect to the ambient plasma; a passive line straddles it.
  The split, not the total, is what each end has to survive.
- Three different limits then apply to three different places. An
  exposed end in contact with the plasma is bounded by its arc-onset
  threshold, which depends on the surface: bare metal goes first, a
  contactor electrode designed for the duty goes last. An insulated
  span is bounded by its dielectric withstand rating against the share
  of the force it stands off. A reachable end is bounded by the
  ground-handling touch-potential limit, which is far lower than
  either and applies on the bench, not only in flight.
- Banding matters as much as the pass or fail. A potential that has
  crossed most of the way to its arc onset without exceeding it is a
  finding with no exceedance: it is reported, it constrains the
  design, and it does not by itself fail the assessment.

## Workflow

1. Collect the flight condition: orbital velocity, ambient flux
   density, the angle between them, the deployed length, the angle
   between the deployed line and the induced field, and the expected
   floating split. Reject a non-positive velocity, flux density or
   length rather than defaulting it.
2. Compute the induced field magnitude from velocity, flux density and
   their included angle.
3. Project it along the deployed line and multiply by the deployed
   length to obtain the signed end-to-end electromotive-force. Keep the
   sign: it names which end is the collecting one.
4. Split the force about the floating point to get the potential of
   each end with respect to the ambient plasma.
5. Band each end against the arc-onset threshold of its own surface:
   inside the band, approaching it, or past it. Compare on magnitude,
   because the sign of the potential does not change the onset that
   applies. Treat an exact band edge as the compliant side by absorbing
   the representation error in the comparison, never by moving the
   threshold.
6. For each reachable end, apply the ground-handling touch-potential
   limit separately — an end can sit well inside its arc onset and
   still be unsafe to touch.
7. For each insulated span, take its share of the end-to-end force as
   the applied stress and check the withstand-to-stress ratio against
   the required insulation margin.
8. Collect every finding with the quantity that drove it, and report
   the configuration as compliant only when no end and no span is past
   its limit.

## Pitfalls

- Using the induced field magnitude as the end-to-end force without
  projecting it along the line. That converts an alignment question
  into a worst case and hides the configurations that genuinely have
  no end-to-end force.
- Splitting the force evenly by default. The floating point moves with
  the current balance, and an emitter at one end moves it almost all
  the way; an even split understates the collecting end by nearly a
  factor of two.
- Comparing a signed potential against an onset threshold. The
  negative-going end is usually the one that arcs, and a signed
  comparison silently passes it.
- Checking the arc onset and stopping. A reachable end at a hundred
  volts is compliant against a contactor electrode's onset and still
  above the touch-potential limit that governs bench handling.
- Reading an approaching-the-band result as a pass with margin. It is
  a finding: the design has consumed the margin it was given, and the
  next configuration change spends what is left.
- Widening a limit to make an exact-boundary case pass. The boundary
  case is a representation artefact of the arithmetic, not an
  engineering allowance; absorb it in the comparison.

## Behavior contract (gate 3)

The induced-field, end-to-end force, floating-split, arc-onset banding,
touch-limit and insulation-margin logic is exercised by the gate 3
contract test: scripts/test_e2006_tether_generated_voltage_hazards.py
against scripts/e2006_tether_generated_voltage_hazards_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_tether_generated_voltage_hazards.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
