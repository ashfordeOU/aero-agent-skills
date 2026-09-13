---
name: e2006-deliberately-biased-surface-potentials
description: "Use when determine how a deliberately biased external surface disturbs the electrostatic potential around the vehicle under ECSS-E-ST-20-06C clause 6.5: inventory every commanded-bias element, a high-voltage-array string end, an electric-propulsion grid, a plasma-contactor, a biased-plasma-probe or a tether-anode, with its bias-offset and its exposed conductive area, evaluate the plasma current each element exchanges at a trial frame potential, solve the vehicle floating-condition by bisection for the shifted frame-potential, size the Child-law sheath-extent around each element, and report snapover-onset, arc-inception, frame-sputtering and sheath-encroachment findings. Trigger: ecss, e-st-20-06c, biased-surface-potential, vehicle-floating-potential-shift, plasma-sheath-extent, snapover-onset-threshold, high-voltage-array-bias, electric-propulsion-bias-coupling, sheath-encroachment-clearance."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-deliberately-biased-surface-potentials, e-st-20-06c, biased-surface-potential, vehicle-floating-potential-shift, plasma-sheath-extent, snapover-onset-threshold, high-voltage-array-bias, electric-propulsion-bias-coupling]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Deliberately Biased Surface Potentials (space-systems/ecss/e2006-deliberately-biased-surface-potentials)

Use when the task is the clause 6.5 provision of ECSS-E-ST-20-06C: a
surface held at a commanded offset from structure exchanges current
with the ambient plasma at its own potential, so it moves the whole
vehicle and builds a potential structure around it. This leaf solves
the shifted frame-potential, sizes the sheath each biased element
projects, and reports where that disturbance crosses an onset
threshold or reaches a sensitive item.

## Domain quick reference

- A deliberately biased surface is an exposed conductor whose
  potential is set by the design, not by the plasma: a
  high-voltage-array string end, an electric-propulsion grid or
  neutraliser, a plasma-contactor, a biased-plasma-probe, a
  tether-anode, a driven antenna element. Bias is defined against
  structure; what the plasma sees is the sum of that bias and the
  frame-potential, which is why no element can be judged on its
  commanded voltage alone.
- Only exposed conductive area couples. An element sealed under
  insulation carries its bias without exchanging current, so it
  disturbs nothing until the insulation is defeated. Exposed area is
  the lever in this whole analysis: the frame shift is set by the
  ratio of exposed biased area to exposed structure area, not by the
  bias magnitude on its own.
- The vehicle floats where the summed current vanishes. A surface
  positive with respect to the plasma collects electrons through a
  linearly growing sheath and repels ions exponentially; a negative
  surface does the mirror image. Because the electron term is the
  mobile one, a large positively biased exposed area pulls the frame
  strongly negative, which is how a high-voltage-array drives its own
  structure to a potential that then sputters every other surface.
- The sheath is the reach of the disturbance. Its scale is the ambient
  Debye length, and its extent grows as the three-quarter power of the
  potential ratio, so a hundredfold bias reaches roughly thirty Debye
  lengths out. A plasma instrument, a tether, an antenna or a
  deployable inside that reach is measuring the vehicle, not the
  ambient plasma.
- Two onset thresholds bound each element against the plasma, not
  against structure: a positive threshold where electron snapover
  spreads collection across the surrounding dielectric, and a negative
  threshold where arcing initiates at the conductor-to-dielectric
  junction. A third, on the frame itself, bounds ion sputtering of the
  outer surfaces.

## Workflow

1. Normalise each biased element: an identifier, a known biased
   function, a non-zero bias against structure, an exposed conductive
   area, an explicit insulation flag and, where a sensitive item sits
   nearby, its clearance. Reject a zero bias as not a biased surface,
   a negative area, a duplicate identifier and a sign-inverted onset
   threshold before the analysis starts.
2. Capture the ambient plasma: electron and ion temperature, electron
   density, and the electron and ion current densities at zero
   potential. The density fixes the Debye length that scales every
   sheath in the report.
3. Evaluate the plasma current onto each exposed area at a trial
   frame-potential, taking the attracted species through its linear
   sheath growth and the repelled species through its exponential
   barrier. The two branches agree at zero potential; a discontinuity
   there means the convention slipped.
4. Solve the floating condition by bisection over the frame-potential,
   summing the structure and every exposed element. A vehicle with no
   exposed conductive area has no floating condition, and a balance
   that never changes sign inside the bracket is an input error, not
   a zero result.
5. Re-evaluate each element at the solved frame, size its sheath from
   the potential it presents to the plasma, and compare that reach
   against the clearance of the nearest sensitive item.
6. Report the frame shift against the same vehicle with its bias
   elements insulated, then the findings: snapover-onset, arc-inception,
   frame-sputtering and sheath-encroachment. The configuration is
   acceptable only when that list is empty.

## Pitfalls

- Judging an element on its commanded bias. The plasma sees bias plus
  frame; a positively biased string end on a vehicle driven to a large
  negative frame can sit near zero, while its neighbour at a small
  negative bias is the one that arcs.
- Counting the whole biased conductor instead of its exposed area.
  Insulated bias is inert, and treating a sealed high-voltage harness
  as exposed manufactures a frame shift that does not exist.
- Scaling the frame shift with the bias voltage alone. The driver is
  the exposed-area ratio between the biased elements and the
  structure; doubling the exposed area moves the frame far more than
  doubling the bias.
- Sizing the sheath from the Debye length alone. The reach scales as
  the three-quarter power of the potential ratio, so a sheath computed
  at the ambient scale can understate the encroachment on a plasma
  instrument by more than an order of magnitude.
- Widening an onset threshold so a boundary case passes. A potential
  that lands a few units in the last place beyond a threshold is the
  same physical value as the threshold and the comparison absorbs it;
  a potential genuinely beyond it is a finding.

## Behavior contract (gate 3)

The element validation, plasma-current branches, floating-condition
bisection, Debye length, Child-law sheath extent, clearance margin and
onset assessment are exercised by the gate 3 contract test:
scripts/test_e2006_deliberately_biased_surface_potentials.py against
scripts/e2006_deliberately_biased_surface_potentials_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_deliberately_biased_surface_potentials.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
