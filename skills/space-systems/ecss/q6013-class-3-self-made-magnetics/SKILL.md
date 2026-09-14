---
name: q6013-class-3-self-made-magnetics
description: "Assess whether an in-house wound magnetic component and its delivered batch carry the build basis, the thermal margin and the screening the lowest assurance class of ECSS-Q-ST-60-13C clause 6.6.8 asks for: refuse a drawing with no issue, an unreleased winding procedure, an uncertified operator or a missing first article record, solve the copper-loss heat balance in closed form for the hot spot and report a winding whose solution does not settle as its own outcome, hold the hot spot under the insulation rating less a held-back margin, name every delivered unit whose measured turns ratio falls outside the band, and size the sample-drawn screening from the batch. Use when an in-house magnetic batch has to be accepted. Trigger: ecss, q-st-60-13c-clause-6-6-8, in-house-wound-magnetic-build-basis, winding-copper-loss-heat-balance, winding-thermal-stability-margin, magnetic-batch-sample-sizing, magnetic-per-unit-screening-coverage, measured-turns-ratio-tolerance."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c-clause-6-6-8, q6013-class-3-self-made-magnetics, in-house-wound-magnetic-build-basis, winding-copper-loss-heat-balance, winding-thermal-stability-margin, magnetic-batch-sample-sizing, magnetic-per-unit-screening-coverage, measured-turns-ratio-tolerance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 3 In-House Magnetics (space-systems/ecss/q6013-class-3-self-made-magnetics)

Use when the task is the self-made magnetics provision of ECSS-Q-ST-60-13C
clause 6.6.8 at the lowest assurance class: a transformer, inductor or
choke the project wound on its own bench rather than bought as a
catalogue item, the basis that has to stand behind the batch it came
from, and the screening that batch receives before any unit is fitted.

## Domain quick reference

- An in-house magnetic has a builder and no manufacturer. There is no
  datasheet to derate against and no qualification to lean on, so the
  drawing, its issue, the released winding procedure and the certified
  operator are the entire build basis. A batch that cannot name all four
  is a batch nobody can wind again the same way.
- The issue is not paperwork. Two batches wound to the same drawing
  number months apart are the same part only if the drawing did not move
  between them, and the issue is the only thing that says so.
- On an in-house winding the operator is the process. Layer tension,
  start and finish dressing and interleave placement live in the hands
  that wound it, and a certification record is what says those hands
  were assessed.
- The thermal check is a solved balance, not an evaluated formula.
  Copper resistance rises with temperature, the loss rises with the
  resistance, and the temperature rises with the loss. Written out that
  is one linear equation in the hot spot, it has a closed solution, and
  solving it is the difference between a hot spot and a room-temperature
  guess.
- The same expression carries its own stability test. As the copper loss
  coefficient approaches the thermal conductance the denominator closes
  on zero, and a component past that point does not run hot, it runs
  away. That is a distinct outcome and deserves a distinct word rather
  than a very large temperature.
- The hot spot is judged against the insulation rating less a margin the
  class holds back, not against the rating itself. Insulation life falls
  off long before the rating is reached, and the margin is what buys the
  mission the years it needs.
- A turns ratio inside tolerance on average is not a turns ratio inside
  tolerance. The measurement is per unit, and every unit outside the
  band is named, because one transformer wearing the same part number
  and a different ratio is a fault waiting for the integration where it
  is fitted.
- Screening splits in two, and the split is the point. Per-unit steps
  are owed by every delivered unit because they catch the defect that
  kills one piece: a nicked enamel, a mis-terminated winding, a varnish
  void. Sample steps characterise the batch instead. Reading a sample
  step as batch coverage, and running a per-unit step on a sample, are
  the same error in opposite directions.
- A sample is a count, not a gesture. It follows the batch through a
  declared fraction, is floored so a small batch is not screened by one
  piece, and can never exceed the batch itself.

## Workflow

1. Validate the magnetic policy first: the copper temperature
   coefficient and its reference temperature, the stability floor, the
   insulation margin, the turns ratio tolerance, the sample fraction and
   its floor, and the two build-basis flags. A stability floor below
   one, a zero tolerance or fraction, or a coefficient that is not a
   conductor coefficient is refused rather than used.
2. Validate the build basis and report every reason the batch cannot be
   repeated rather than the first: no designation, no drawing, a drawing
   with no issue, an unreleased procedure, an uncertified operator, no
   first article record. Any of those closes the assessment on build
   basis not established, before a single number is computed.
3. Validate every winding: a named identifier, whole positive turns, a
   positive resistance at the reference temperature and a non-negative
   current. Sum the copper loss coefficient across them.
4. Take the stability margin as the thermal conductance over the rate at
   which the copper loss chases its own temperature. A margin at or
   under one closes the assessment on a solution that does not settle;
   a margin under the floor closes it on the margin itself.
5. Solve the balance for the hot spot and compare it with the insulation
   rating less the class margin, with a tolerance that absorbs
   representation error so a value landing on the allowance is
   admissible.
6. Read the design turns ratio, cross-checking it against the declared
   turns where the component has exactly two windings, then name every
   delivered unit whose measured ratio sits outside the band.
7. Validate the batch and the delivery, refusing a delivery larger than
   the batch it came from, size the sample-drawn screening from the
   batch size, and report each per-unit step some unit never ran and
   each sample step run on too few units, separately and in full.
8. Report the designation, the batch and delivery, the copper loss
   coefficient, the stability margin, the hot spot and its allowance,
   the design ratio, the out-of-tolerance units, the required sample and
   both screening gap lists, and close on one verdict: build basis not
   established, thermal solution does not settle, thermal stability
   margin short, hot spot over the insulation rating, measured turns
   ratio out of tolerance, screening coverage short, or magnetic meets
   class three scope.

## Pitfalls

- Computing the winding loss at room temperature. The resistance that
  sets the loss is the resistance at the temperature the loss produced,
  and the cold figure understates a hot winding every time.
- Reading a very large hot spot as a thermal problem to be cooled. Past
  the stability point there is no steady temperature to cool towards;
  the fix is less copper loss or a better heat path, not a colder
  baseplate.
- Judging the hot spot against the insulation rating itself. The rating
  is where the insulation fails quickly, and the margin is the part of
  it the mission actually spends.
- Accepting a drawing number as a build standard. Without the issue the
  batch is traceable to a document rather than to a build, and the next
  batch to the same number will look identical on paper.
- Averaging the measured turns ratios across the delivery. The average
  is not the unit that is wrong, and the unit that is wrong is the one
  that gets fitted.
- Counting a sample step as batch coverage. A withstand test on three
  units says the build is sound; it does not say the insulation on unit
  nineteen is intact, and only the per-unit steps do.
- Screening one piece because the batch is small. The sample is derived
  from the batch size and floored, because a single piece characterises
  the piece and nothing else.

## Behavior contract (gate 3)

The policy validation, the build basis findings, the winding validation,
the copper loss coefficient, the thermal stability margin and its
unbounded case, the closed-form hot spot, the margined insulation
allowance, the design ratio cross-check, the per-unit ratio deviations
and out-of-tolerance list, the batch and delivery validation, the sample
sizing with its floor and cap, the per-unit and sample screening gaps,
the copper-dominated advisory and the acceptance verdict are exercised
by the gate 3 contract test:
scripts/test_q6013_class_3_self_made_magnetics.py against
scripts/q6013_class_3_self_made_magnetics_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q6013_class_3_self_made_magnetics.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
