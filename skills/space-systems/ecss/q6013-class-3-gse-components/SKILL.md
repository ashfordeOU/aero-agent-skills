---
name: q6013-class-3-gse-components
description: "Determine which controls a commercial part inside ground support equipment still earns at the lowest assurance class of ECSS-Q-ST-60-13C clause 6.1.5: treat identification as owed by every part, add an isolation, calibration, verification, operator-safety or spares control only where a declared exposure triggers it, credit an asserted control at nothing and a waiver only where the element may be waived at all and the justification is on record, weight the credited elements into a per-part coverage, and return the control tier, the governing part and one rack verdict. Use when a ground rack parts list is graded at the lowest class. Trigger: ecss, q-st-60-13c-clause-6-1-5, class-three-gse-part-control-tier, gse-exposure-triggered-control-set, gse-control-waiver-justification, gse-control-coverage-floor, class-three-ground-rack-verdict."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-3-gse-components, class-three-gse-part-control-tier, gse-exposure-triggered-control-set, gse-control-waiver-justification, gse-control-coverage-floor, class-three-ground-rack-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Class 3 Ground Support Equipment Components (space-systems/ecss/q6013-class-3-gse-components)

Use when the task is clause 6.1.5 of ECSS-Q-ST-60-13C at the lowest assurance
class: commercial parts fitted inside ground support equipment, and what
control each one still owes once the programme has chosen the lightest class
available to it. This leaf builds the control set part by part from declared
exposures and returns what is discharged and what is open.

## Domain quick reference

- The lowest class is a reduction in the default, not a removal of the floor.
  Every part in the rack still owes identification, because a rack whose
  contents are unknown cannot be repaired, cannot be audited and cannot be
  reproduced when the same test has to be run a year later.
- Each further control is pulled in by one specific exposure. Interface
  isolation arrives because the part is wired to flight hardware. A
  calibration record arrives because the part's reading is quoted in
  acceptance evidence. An operator safety barrier arrives because the supply
  is above the potential a person can safely touch. None of them arrive
  because the rack as a whole feels important.
- An asserted control is worth nothing. "We do check that" and a cited
  procedure number are the same sentence in a review and different states in
  the record, and only the second one survives the question "show me".
- A waiver is a route, not a shortcut. It earns credit only where the element
  is waivable at this class and the justification is written down. Two
  elements are not waivable at any class: a part wired to flight hardware and
  a part at a hazardous potential both keep their control whatever the
  programme decided about assurance.
- Coverage ranks parts; it does not decide them. A rack can sit above the
  declared floor and still hold one part whose interface isolation was never
  discharged, and that one part is what the clause exists for.
- Lead time is a control input, not a logistics footnote. A part that takes
  months to replace has stopped being a shelf item, and the rack owes a spares
  holding because a failure now costs the campaign its schedule.

## Workflow

1. Validate each declared part: connection flag, data role, supply potential
   and replacement lead time, refusing an undeclared role rather than reading
   the omission as "none".
2. Build the owed control set from those exposures, starting from
   identification and adding one element per triggered exposure.
3. Read the declared control record, refusing an entry that claims evidence
   without citing a reference, and note any element declared that no exposure
   asked for.
4. Credit an evidenced element; credit a waived element only where it is
   waivable and carries a written justification; credit nothing else.
5. Weight the credited elements against the owed elements to form the part
   coverage.
6. Categorize the part as catalogue, recorded or open on what remains
   outstanding.
7. Take the quantity-weighted rack coverage, compare it with the declared
   floor through a named tolerance rather than by moving the floor, and keep
   the lowest-coverage part as the governing case with a tie broken on the
   identifier.
8. Return ranked findings and one verdict: accept or escalate.

## Pitfalls

- Reading the lowest class as "no control". The class reduces what is applied
  by default; it does not delete identification, and it does not reach the
  parts that touch flight hardware or mains potential at all.
- Applying the full control set to the whole rack. Blanket application costs
  the programme the budget the class was chosen to save, and it trains the
  bench to argue the whole register away rather than the one line that does
  not apply.
- Crediting an asserted control. The difference between an assertion and an
  evidenced control is the only thing a later audit can see.
- Waiving an element the class never made waivable. A recorded justification
  does not make an isolation barrier or a safety barrier optional, and letting
  it is how a ground fault reaches a spacecraft.
- Deciding on the coverage number. The fraction is for ranking; the
  outstanding element list is what the rack has to close.
- Ignoring replacement lead time because the part is cheap. Cost and
  availability are different axes, and the schedule risk lives on the second.

## Behavior contract (gate 3)

The exposure validation, owed-control derivation, evidence and waiver
crediting, coverage weighting, tier categorization, governing-part selection
and rack verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_3_gse_components.py against
scripts/q6013_class_3_gse_components_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q6013_class_3_gse_components.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
