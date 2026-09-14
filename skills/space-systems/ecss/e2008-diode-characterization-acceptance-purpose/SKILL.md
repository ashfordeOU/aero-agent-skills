---
name: e2008-diode-characterization-acceptance-purpose
description: "Determine why a photovoltaic assembly protection diode has its electrical performance characterised during acceptance under ECSS-E-ST-20-08C clause 9.4.5.2.1: map each declared protection role to the quantity the characterisation feeds, derive the forward dissipation the worst-case section current puts into the substrate and the parasitic leakage loss the whole fitted population carries for the mission, take the sample coverage the acceptance lot actually reaches against the declared floor, and separate a characterisation nobody planned from one planned too thin to sentence a lot. Use when an acceptance programme has to justify, size or defend protection diode characterisation. Trigger: ecss, e-st-20-08c-clause-9-4-5-2-1, protection-diode-acceptance-characterisation-purpose, protection-diode-forward-dissipation-budget, protection-diode-parasitic-leakage-loss, acceptance-lot-diode-sample-coverage, protection-diode-role-objective-map."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-diode-characterization-acceptance-purpose, protection-diode-acceptance-characterisation-purpose, protection-diode-forward-dissipation-budget, protection-diode-parasitic-leakage-loss, acceptance-lot-diode-sample-coverage, protection-diode-role-objective-map]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Protection Diode Characterisation Purpose (space-systems/ecss/e2008-diode-characterization-acceptance-purpose)

Use when the task is to state and defend why the electrical performance
of a protection diode is characterised during the acceptance activity
of ECSS-E-ST-20-08C clause 9.4.5.2.1 -- which fitted role makes the
measurement necessary, what the resulting numbers are spent on, and
whether the planned characterisation reaches enough of the population
to stand as acceptance evidence.

## Domain quick reference

- A protection diode is fitted for a fault the assembly may never see.
  No acceptance activity stages that fault, so the only evidence the
  part will act on the day is its electrical behaviour measured on the
  ground, before the assembly is closed out.
- Three consumers want the number and each wants a different part of
  it. The forward branch gives the drop the diode adds while carrying
  its section and the heat that drop puts into the substrate. The
  reverse branch gives the leakage it passes while it is meant to be
  blocking. The curve itself gives a per-part signature a later
  degradation claim can be measured against.
- The forward drop is not a datasheet detail, it is a thermal input.
  Drop times section current is watts into a substrate that has only
  radiation to lose them with, and a part chosen on price can put a
  local hot spot under a cell stack.
- Leakage is small per part and never small per array. A microamp at
  string voltage is nothing; the same microamp across every diode on a
  large wing, for every sunlit minute of the mission, is a loss the
  power budget has to carry and nobody ever measures in flight.
- Coverage is what separates a number from acceptance evidence. One
  diode out of four hundred characterises one diode. The sample floor
  is what the lot verdict rests on, and it is a declared policy figure,
  not a physical constant.
- A characterisation nobody planned and one planned too thin are
  distinct outcomes with distinct fixes, and reporting them as a single
  failure hides which one the programme actually has.
- A role that is not declared is not a role. An absent inventory is
  refused rather than read as an empty one, because silence about the
  diodes on an assembly is the condition the clause exists to stop.

## Workflow

1. Validate the characterisation policy first: sample floor, forward
   dissipation budget and parasitic-loss allowance. A floor of nought
   is refused rather than used, because it accepts a lot nobody
   measured.
2. Group the declared protection roles, rejecting an unrecognised one
   rather than ignoring it, and map each to the quantity the
   characterisation feeds it. Append the shared per-part record
   whenever any role is present.
3. Derive the forward dissipation from the expected drop and the
   worst-case section current, and the parasitic loss from the string
   reverse voltage, the expected leakage and the whole fitted
   population. Both are reported whatever the verdict, because they are
   what the numbers were wanted for.
4. Decide whether the characterisation is required at all: at least one
   declared protection role. With none, no part of the assembly depends
   on how the diode behaves electrically.
5. When it is required, take the coverage the planned characterisation
   reaches against the fitted population and hold it against the floor.
   Coverage landing exactly on the floor earns the sample; the
   comparison tolerance absorbs representation error and the floor does
   not move.
6. Only once the sample can sentence the lot, hold the dissipation
   against its budget and the leakage share against its allowance,
   reporting both breaches when both are present rather than the first.
7. Close on one verdict: characterisation not required, characterisation
   not planned, characterisation undersampled, loss budget exceeded, or
   characterisation justified.

## Pitfalls

- Treating the forward drop as a catalogue figure. It is a thermal
  input, and the watts it puts into the substrate are the reason the
  acceptance measurement is taken on the flight part rather than read
  off a datasheet.
- Dismissing leakage because it is microamps. The array carries the
  product of that leakage, the string voltage and every fitted diode,
  for the whole mission, and no flight telemetry will ever separate it
  from anything else.
- Reporting an undersampled characterisation as an unplanned one. The
  first needs more parts on the bench, the second needs a test that
  does not exist yet, and a programme cannot schedule the fix it was
  not told about.
- Counting a sample larger than the lot it was drawn from. That is a
  bookkeeping error being read as full coverage, so it is refused at
  the input rather than reported as a pass.
- Sentencing the loss budgets from a sample too thin to sentence
  anything. Coverage is checked first because a breach found in one
  diode out of four hundred says nothing about the other ones.
- Letting an absent role inventory stand for an empty one. A silent
  assembly is not an assembly without protection diodes; it is one
  nobody has described yet.

## Behavior contract (gate 3)

The policy validation, role inventory and objective mapping, forward
dissipation, parasitic reverse loss and its share of array output,
sample coverage, the budget comparisons at their exact bounds, and the
purpose verdict are exercised by the gate 3 contract test:
scripts/test_e2008_diode_characterization_acceptance_purpose.py against
scripts/e2008_diode_characterization_acceptance_purpose_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2008_diode_characterization_acceptance_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
