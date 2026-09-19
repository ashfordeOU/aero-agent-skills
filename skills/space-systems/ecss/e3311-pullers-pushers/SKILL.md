---
name: e3311-pullers-pushers
description: "Size an explosive pin puller or pin pusher against ECSS-E-ST-33-11C clauses 4.12.3 and 4.12.4. Use when the task is turning a cartridge rating into a defensible stroke and work balance: converting chamber pressure across the bore into piston force, reducing peak pressure to a mean effective pressure over the stroke, building the resisting force from the external load and the friction a side load creates, grading delivered work against required work and delivered stroke against engagement depth plus misalignment, and bounding the surplus energy dumped into the end stop. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, explosive-pin-puller-stroke-margin, explosive-pin-pusher-work-margin, cartridge-pressure-piston-force, pin-puller-side-load-friction, actuator-end-of-stroke-kinetic-energy."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-pullers-pushers, explosive-pin-puller-stroke-margin, explosive-pin-pusher-work-margin, cartridge-pressure-piston-force, pin-puller-side-load-friction, actuator-end-of-stroke-kinetic-energy]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Pullers and Pushers (space-systems/ecss/e3311-pullers-pushers)

Use when the task is the explosive puller and pusher requirement of
ECSS-E-ST-33-11C clauses 4.12.3 and 4.12.4 -- showing that a
gas-driven piston both moves far enough and does enough work to free
or drive its load, under the side load and friction the installation
actually imposes, and that the energy left over at the end of travel
is small enough for the structure behind the stop.

## Domain quick reference

- A puller and a pusher are the same machine run in opposite
  directions: a cartridge fills a chamber, the pressure acts on a bore
  area, and the piston travels a stroke. The two duties that decide
  acceptance are therefore separate and both mandatory -- enough work
  and enough travel.
- Force follows pressure across the bore area, so it scales with the
  square of the bore diameter. Doubling the bore quadruples the force
  at the same pressure, which is why a small increase in bore recovers
  more margin than a large increase in cartridge charge.
- Peak chamber pressure is not the pressure that does the work. The gas
  expands as the piston travels, so the work integral is taken on a
  mean effective pressure, a declared fraction of the peak. Using peak
  pressure over the whole stroke overstates the delivered work by the
  whole expansion loss.
- The resisting force is rarely the external load alone. A side load
  presses the pin against its bore and the resulting friction adds
  directly to what the piston must overcome, so an actuator sized on
  the axial load alone is sized on the wrong number.
- Stroke has its own margin. The pin must clear the full engagement
  depth and then the misalignment the joint can take up, and an
  actuator whose travel merely equals the engagement depth releases
  nothing once the interface is off-nominal.
- Surplus work is not free. Whatever the piston does not spend on the
  load arrives at the end stop as kinetic energy, and that is a shock
  input to the surrounding structure, so an oversized actuator is a
  different finding rather than no finding.

## Workflow

1. Declare the device kind, the bore diameter, the peak chamber
   pressure and the mean effective pressure fraction. Reject a
   pressure fraction at or above unity, because the gas expands.
2. Convert the mean effective pressure across the bore area into piston
   force, and multiply by the available stroke to get delivered work.
3. Build the resisting force from the external load and the friction
   the declared side load produces, then multiply by the stroke the
   release actually needs to get required work.
4. Compute the required stroke as engagement depth plus the
   misalignment allowance, and grade the available stroke against it as
   a ratio, not a difference.
5. Grade delivered work against required work as a ratio against the
   policy floor for that device kind, and report the shortfall.
6. Take the surplus work as kinetic energy at the end stop, derive the
   impact velocity from the moving mass, and compare the energy with
   the shock allowance. Combine the work, stroke and end-stop verdicts
   into one result.

## Pitfalls

- Working with peak chamber pressure over the whole stroke. The gas
  expands behind a moving piston, so the work done is the mean
  effective pressure times the swept volume, and peak pressure
  overstates it by the expansion loss.
- Sizing on the axial load alone. The side load the installation
  imposes turns into friction on the pin, and that term frequently
  exceeds the axial load it was left out of.
- Grading stroke by a difference. A five millimetre surplus means
  something different on a three millimetre engagement than on a fifty
  millimetre one, and the requirement is a proportion of what the
  release actually needs.
- Sizing the stroke on engagement depth alone. The joint takes up
  misalignment before the pin starts to clear, so the travel that
  counts begins after that take-up is spent.
- Reading a large work margin as an unqualified pass. The surplus
  arrives at the end stop, and an actuator with four times the work it
  needs delivers a shock the bracket behind it may not be qualified to.
- Comparing a work or stroke ratio with its floor by bare arithmetic.
  Both are quotients of products, so a case that sits exactly on the
  floor can land a few units in the last place below it; the
  comparison absorbs that while the floor stays untouched.

## Behavior contract (gate 3)

The piston force conversion, mean effective pressure work, side-load
friction, work and stroke margins, end-stop kinetic energy and the
combined verdict are exercised by the gate 3 contract test:
scripts/test_e3311_pullers_pushers.py against
scripts/e3311_pullers_pushers_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e3311_pullers_pushers.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
