---
name: e3301-grounding-bonding
description: "Verify that every mechanism on a spacecraft is bonded to structure as ECSS-E-ST-33-01C clause 4.7.7.4 requires. Use when the task is grading a bonding schedule: computing each strap's length-to-width ratio against the geometry limit that keeps it a conductor rather than a choke, deriving its end-to-end DC resistance from foil geometry, material resistivity and the joint resistance at both ends, comparing that against the ten-milliohm bond limit, combining parallel bonds, and confirming no mechanism in the inventory is left unbonded and no strap is attributed to one that does not exist. Trigger: ecss, e-st-33-01-mechanisms-scope, mechanism-bonding-strap-aspect-ratio, mechanism-bond-dc-resistance, bonding-schedule-coverage, bond-joint-resistance, parallel-bond-path, mechanism-structure-grounding."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-grounding-bonding, mechanism-bonding-strap-aspect-ratio, mechanism-bond-dc-resistance, bonding-schedule-coverage, bond-joint-resistance, mechanism-structure-grounding]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Grounding and Bonding to Structure (space-systems/ecss/e3301-grounding-bonding)

Use when the task is the mechanism bonding step of ECSS-E-ST-33-01C
clause 4.7.7.4 -- showing that every mechanism on the vehicle has a
low-impedance path to the structure it is mounted on, and that the
straps providing it are the right shape as well as the right
resistance.

## Domain quick reference

- The bond has two jobs and the requirement has two numbers because of
  it. The DC resistance limit keeps fault current and charge off the
  mechanism's chassis; the length-to-width geometry limit keeps the
  strap's inductance low enough to stay a bond at the frequencies a
  drive produces. A strap can pass one and fail the other.
- The geometry limit is about inductance, not resistance. A long thin
  strap can measure a fraction of a milliohm at DC and still present
  ohms of reactance at the commutation harmonics of a stepper drive,
  which is exactly where the bond is needed.
- A bond's resistance is mostly not in the foil. For a short braid the
  bulk term is tens of microhms while each end joint contributes
  hundreds, so a resistance model that ignores the joints understates
  the path by an order of magnitude and a design graded on it passes on
  paper.
- Joint resistance is a surface question: finish, contact pressure,
  paint keep-out and corrosion control drive it. That is why a bond is
  measured on the built article rather than inferred from geometry, and
  why a measured value, when it exists, replaces the model rather than
  averaging with it.
- Two bonds in parallel lower the path resistance and give redundancy,
  but only when they are genuinely separate paths to the same
  structure. Two straps landing on one bracket share that bracket's
  joint and are one bond with two tails.
- Coverage is part of the requirement. A schedule that grades the straps
  it lists says nothing about a mechanism nobody wrote a strap for, so
  the inventory and the schedule are reconciled in both directions.

## Workflow

1. Validate each strap record: identifier, the mechanism it bonds,
   length, width, thickness, material, and the per-end joint resistance.
   An unrecognised material is an input error, because its resistivity
   is what the model rests on.
2. Compute the length-to-width ratio and grade it against the geometry
   limit. The limit is a strict one, so a strap sitting exactly on it
   within the named tolerance does not meet it.
3. Compute the end-to-end DC resistance as the foil bulk resistance plus
   both joint resistances; when a measured value is supplied, use it
   instead of the model.
4. Grade that resistance against the bond limit, again strictly.
5. Combine genuinely parallel bonds through their conductances when a
   mechanism carries more than one path to the same structure.
6. Reconcile the bonding schedule with the mechanism inventory in both
   directions: a mechanism with no strap, and a strap naming a
   mechanism that is not in the inventory, are both findings.
7. Report per-strap records, the per-mechanism bond map and the
   aggregated findings; the schedule is compliant only when the finding
   list is empty.

## Pitfalls

- Grading only the DC resistance. A braid that measures well at DC and
  runs long and narrow is the classic bond that passes the test and
  fails in flight, because the interference it was fitted to control
  lives above DC.
- Modelling the strap as foil alone. The joints usually dominate, so a
  geometry-only resistance is optimistic by an order of magnitude on a
  short braid.
- Averaging a measured resistance with a modelled one. The measurement
  is the evidence; the model is what you use when there is none.
- Counting two straps to the same bracket as redundant paths. They share
  the bracket joint, which is the part most likely to degrade, so the
  redundancy is nominal.
- Grading the straps in the schedule and calling the schedule complete.
  The mechanism nobody wrote a strap for produces no record to grade and
  disappears from the report unless coverage is checked explicitly.
- Relaxing a strict limit to absorb a value sitting exactly on it. The
  representation error is handled by the named tolerance inside the
  comparison, and a value at the limit does not meet a strict one.

## Behavior contract (gate 3)

The strap validation, aspect-ratio grading, bulk and joint resistance
model, measured-value override, parallel-bond combination and
schedule-versus-inventory coverage reconciliation are exercised by the
gate 3 contract test: scripts/test_e3301_grounding_bonding.py against
scripts/e3301_grounding_bonding_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e3301_grounding_bonding.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
