---
name: e2008-grounding-resistance-test
description: "Evaluate the resistance measured at every grounding point of a photovoltaic assembly under ECSS-E-ST-20-08C clause 5.5.3.3.4: resolve the window each point is allowed to sit in, reject a reading taken to a neighbour fitting instead of the declared structural reference, screen the repeat readings for a contact moving under the probe and the test current for enough drive to break the film on a bolted joint, compensate a two-wire fixture, then separate a resistive bond from a path more conductive than the plan allows. Use when a grounding run has to be accepted, sentenced or repeated. Trigger: ecss, e-st-20-electrical-scope, grounding-point-bond-resistance, photovoltaic-assembly-grounding-plan, four-wire-bond-measurement, bond-reading-repeatability, dissipative-path-resistance-window, grounding-point-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-grounding-resistance-test, grounding-point-bond-resistance, photovoltaic-assembly-grounding-plan, four-wire-bond-measurement, bond-reading-repeatability, dissipative-path-resistance-window, grounding-point-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Grounding Resistance Test (space-systems/ecss/e2008-grounding-resistance-test)

Use when the task is the grounding resistance test of ECSS-E-ST-20-08C
clause 5.5.3.3.4 -- measuring the resistance at each grounding point of a
photovoltaic assembly back to the one structural reference the grounding plan
names, and deciding whether each point sits where the plan puts it.

## Domain quick reference

- A grounding point has a window, not a limit. A structural or electrical
  bonding point fails by being too resistive; a path that bleeds surface
  charge has a floor as well as a ceiling and fails by being too conductive,
  because a low-resistance path there turns a bleed into a fault current
  route. The verdict says which edge was crossed.
- The reference is part of the measurement. A reading taken from one grounding
  point to a convenient neighbour grades the metalwork between them, not the
  path to structure, so it is carried as not evaluated rather than as a value.
- Milliohm readings need a four-wire probe. The fixture and the contact are
  the same size as a bonding-point window, so a two-wire reading is usable
  only with a declared fixture resistance and is otherwise inconclusive.
- Bolted joints wear an oxide and contamination film. Below a stated test
  current the probe reads the film rather than the joint, and the number comes
  out plausible and wrong, so the drive level is graded alongside the value.
- Repeats are the stability evidence. A single reading cannot show the contact
  held; a spread between repeats is a contact moving under the probe, and the
  mean of a moving contact is not a measurement of the bond.
- Window edges are inclusive. A point landing exactly on its ceiling is a
  pass, so the comparison absorbs representation error rather than the window
  being widened to make the arithmetic tidy.

## Workflow

1. Validate the grounding plan: one named structural reference, a non-empty
   point list, unique point ids, and no point that is the reference itself.
2. Resolve each point's window from its category, letting a declared floor or
   ceiling override the default, and refuse an inverted window.
3. Match the readings to the plan: points never measured, points measured
   twice with no stated reason, and readings taken at points the plan does not
   list.
4. Reject outright any reading whose stated destination is not the declared
   structural reference.
5. Screen how each reading was taken: repeat count, relative spread between
   repeats, test current against the film-breaking minimum, and probe
   technique against the window it has to resolve.
6. Reduce the repeats to a mean and compensate a two-wire fixture, refusing a
   declared fixture resistance larger than the mean reading.
7. Grade the compensated value against the window -- within, above, below, or
   open -- then roll the points up into a campaign verdict and report the
   grouped verdicts, the coverage and every finding.

## Pitfalls

- Grading a bond from one reading. The contact resistance of a probe on a
  painted or anodised fitting moves while you watch it, and a single number
  records whichever moment the trigger was pulled.
- Measuring point to point because the reference is awkward to reach. Two
  well-bonded points give a low reading to each other while both sit on an
  isolated section, so the reading passes and the assembly is not grounded.
- Using a low test current because the meter allows it. The film breaks down
  above a drive level, and below it the instrument is measuring the film.
- Reading a dissipative path as pass-if-low. A charge-bleeding path with a
  near-zero resistance is a fault, not a good bond, which is why the floor is
  graded as hard as the ceiling.
- Subtracting a fixture resistance nobody measured. A guessed lead value moves
  a milliohm verdict either way, so a two-wire reading with no declared
  fixture is inconclusive rather than compensated.
- Letting unmeasured points ride on the points that passed. Grounding is
  verified only when every declared point was measured once and every one sits
  inside its window.

## Behavior contract (gate 3)

The plan and policy validation, window resolution, reference check, repeat
statistics and quality screen, fixture compensation, the four point verdicts,
the coverage accounting and the campaign roll-up are exercised by the gate 3
contract test: scripts/test_e2008_grounding_resistance_test.py against
scripts/e2008_grounding_resistance_test_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_grounding_resistance_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
