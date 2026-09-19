---
name: q7054-contamination-reintroduction-control
description: "Assess whether the controls around cleaned hardware hold the state it left the process in, under ECSS-Q-ST-70-54C: take the cleanroom class, the unidirectional flow, the surface orientation, the glove regime and the bagging over each handling, storage and transport period, estimate the particles that fall out and the residue that transfers, degrade the achieved level by them, grade the result against the requirement, and name the single control that buys back most of any shortfall. Use when hardware has to survive handling, storage or transport after precision cleaning. Trigger: ecss, q-st-70-54c, recontamination-control, cleanroom-particle-fallout, double-bagging-cleanliness, unidirectional-flow-protection, glove-regime-residue."
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
  tags: [ecss, q-st-70-54c-ultracleaning-of-flight-hardware, q-st-70-54c, q7054-contamination-reintroduction-control, recontamination-control, cleanroom-particle-fallout, double-bagging-cleanliness, unidirectional-flow-protection, glove-regime-residue]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Ultracleaning — Contamination Reintroduction Control (space-systems/ecss/q7054-contamination-reintroduction-control)

Use when the task is the recontamination part of the process clause of
ECSS-Q-ST-70-54C: showing that what the cleaning achieved is still there when
the hardware is handed over, after everything the handling, storage and
transport put back.

## Domain quick reference

- Cleanliness is a state, not a property. It starts degrading the moment the
  process ends, so the number that matters is the state at delivery, which is
  the state at the end of cleaning minus the whole exposure history.
- Recontamination is predictable, not mysterious. Particles fall out of the
  air at a rate set by the room, reduced by unidirectional flow, by turning
  the surface away from the fallout, and above all by a bag; residue transfers
  from whatever touches the hardware.
- Particle counts add, levels do not. Two surfaces at the same level do not
  make a level twice as coarse; the arithmetic runs on counts, so the added
  fallout is added to the count the surface already carried and only the sum
  is inverted back to a level.
- A bag is worth more than a room. Two orders of magnitude of fallout
  reduction from a double bag beats a one-class room upgrade, costs almost
  nothing, and keeps working during the transport where there is no room at
  all.
- Gloves reach open hardware only. An unbagged item takes residue from the
  handler at a rate set by the glove regime; once bagged, it takes a far
  smaller rate from the bag film itself, over a far longer time, and the two
  terms are not interchangeable.
- Time is the multiplier on everything. A short open operation in a poor room
  can cost less than a long protected storage, so an exposure profile with no
  hours in it cannot be assessed at all.
- The useful output is not a verdict but a control. Once the shortfall is
  known, recomputing the exposure with one control changed at a time says
  which single change recovers it, and that is what a programme can act on.

## Workflow

1. State the achieved state at the end of cleaning — the level and the residue
   the process delivered — and the requirement the hardware owes at handover.
2. Describe the exposure as periods, each with its room class, hours, surface
   orientation, unidirectional flow, bagging and glove regime. Reject a period
   with no hours rather than treating it as instantaneous.
3. For each period compute the particles deposited from the room rate scaled
   by orientation, flow and bagging, and the residue deposited from the glove
   regime where the item is open or from the bag film where it is not.
4. Convert the achieved level to a particle count at the reference size, add
   the fallout from every period, and invert the sum back to the degraded
   level. Add the residue terms to the achieved residue directly.
5. Grade both degraded values against the requirement, treating an exact
   landing on a limit as met.
6. Raise the findings the profile implies: open hardware under a shedding
   glove regime, an upward-facing open surface with no flow in a poor room,
   and each ladder that fails with its before and after numbers.
7. Recompute the whole exposure with one control changed at a time — a tighter
   room, added flow, a double bag, a better glove regime, half the time, a
   turned surface — skip any control already in force, and rank by the
   shortfall that remains. Report the leader as the control to act on.

## Pitfalls

- Averaging or maximising levels instead of adding counts. The ladder is
  logarithmic, so combining contributions at the level is arithmetically
  wrong; the addition happens on counts and the inversion happens once.
- Assessing the room and forgetting the clock. A class figure is a rate, so
  the same room is harmless for a ten-minute operation and ruinous for a
  two-week storage, and a profile quoted without hours says nothing.
- Treating a bag as packaging rather than as a control. The bag is usually the
  largest single term in the whole profile, and the decision to leave hardware
  open on a bench between operations is a cleanliness decision, not a
  convenience.
- Charging glove residue to bagged hardware, or bag residue to open hardware.
  The two transfer paths are mutually exclusive per period, and mixing them
  either doubles the residue or hides it entirely.
- Reporting the shortfall without a control. A statement that the hardware
  arrives out of specification is not actionable; the recomputation with one
  control changed at a time is what turns it into a decision.
- Assuming a later cleaning step recovers it. Reclean is often impossible once
  the item is integrated, so fallout accumulated after the last accessible
  cleaning point is permanent for that build.

## Behavior contract (gate 3)

The exposure validation, fallout and residue deposition per period, the
count-domain addition and level inversion, requirement grading with an
exact-landing tolerance, the handling and flow findings, and the
one-control-at-a-time recomputation with its ranking are exercised by the
gate 3 contract test:
scripts/test_q7054_contamination_reintroduction_control.py against
scripts/q7054_contamination_reintroduction_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7054_contamination_reintroduction_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
