---
name: q6013-class-2-eqm-components
description: "Assess whether commercial parts fitted to an engineering qualification model still carry the flight build at the intermediate assurance class under ECSS-Q-ST-60-13C clause 5.1.6: turn every build-standard deviation into a per-domain transfer-credit loss, restore credit only where a deviation acceptance record names a justification and a delta test covering that domain, and refuse restoration on a manufacturer or part-number change because the model then carries a different part. Reports an undocumented deviation even where credit clears the floor, and returns per-domain credit, the delta-test retest set and one transfer verdict. Use when an intermediate-class model parts list or build-standard delta is reviewed. Trigger: ecss, q-st-60-13c-clause-5-1-6, class-two-eqm-commercial-part-representativeness, eqm-flight-build-standard-delta-class-two, eqm-delta-qualification-credit, eqm-deviation-acceptance-record, eqm-domain-transfer-credit-floor, eqm-delta-test-retest-set."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-eqm-components, class-two-eqm-commercial-part-representativeness, eqm-flight-build-standard-delta-class-two, eqm-delta-qualification-credit, eqm-deviation-acceptance-record, eqm-domain-transfer-credit-floor, eqm-delta-test-retest-set]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Qualification Model Parts (space-systems/ecss/q6013-class-2-eqm-components)

Use when the task is clause 5.1.6 of ECSS-Q-ST-60-13C at the intermediate
assurance class: commercial parts have been fitted to an engineering
qualification model, and the question is how much of the qualification
argument still reaches the flight build. This leaf grades the model's
parts list against the intended flight build and returns what transfers,
what transfers only on a delta argument, and what has to be repeated.

## Domain quick reference

- A qualification campaign is an argument about the flight build, run on
  a model. The argument holds where the model was the same thing. At the
  intermediate class the loss is graded rather than absolute: a
  deviation removes a declared share of the domains it touches, not the
  whole campaign, so a package change costs the mechanical domain
  outright and the thermal domain in part.
- The grading is what separates this class from the highest one. There,
  a deviation removes the argument and the only route back is to repeat
  the test. Here a recorded deviation acceptance -- a justification plus
  a named delta test -- restores part of the lost credit, at a declared
  credit factor, for the domains that delta test actually covers.
- Restoration is bounded by what the delta test reached. An acceptance
  that names the mechanical domain leaves the thermal loss standing. A
  record that claims a domain the deviation never touched is not
  generous, it is wrong, and it is refused rather than credited.
- A different manufacturer or a different part number is outside the
  scheme entirely. The model carries a different part, the campaign
  qualified that other part, and no delta test and no credit factor
  turns it back into the one that will fly. Treating it as a large
  deduction is how a model sharing nothing but a function clears a
  floor.
- The floor is a per-domain question, not a single score. A part can sit
  comfortably above the floor on four domains and be the reason the
  radiation campaign has to be rerun, and it is the short domain, not
  the average, that the programme plans against.
- A deviation with no acceptance record is a finding even when the
  credit still clears the floor. It is the lot change the stockroom made
  and nobody wrote down, and it is the one that surfaces at the delta
  review with no justification attached to it.
- Installed quantity weights the model picture. A deviating part fitted
  once in a harness and the same part fitted in every string are one
  line on a parts list and two different exposures for the flight build.

## Workflow

1. Compare each fitted part with its flight-intended counterpart across
   the catalogued build-standard attributes, refusing a part that simply
   omits one rather than reading the omission as a match.
2. Validate every deviation acceptance record: it must name an attribute
   that actually deviates, carry a justification and a delta test, and
   claim only domains the deviation removes. Refuse a record placed on
   the manufacturer or the part number.
3. For each qualification domain, compound the losses of the deviations
   touching it, scaling a loss down by the credit factor where an
   acceptance covers that attribute and that domain.
4. Compare each domain credit with the declared floor, treating an
   exactly-met floor as met through a named tolerance rather than by
   moving the floor.
5. Categorize the part: representative when nothing deviates,
   non-representative when a fundamental attribute deviates or a domain
   falls under the floor, delta-credited otherwise.
6. List the deviations carrying no acceptance record, per part, whatever
   the credit.
7. Form the model picture as the quantity-weighted per-domain credit,
   and the retest set as the union of the short domains at part level
   and at model level.
8. Return ranked findings and one verdict: transferable, transferable
   with delta tests, or not transferable.

## Pitfalls

- Reading the intermediate class as the highest class with softer
  numbers. The mechanism is different: credit is restored by a recorded
  delta argument, and a leaf that only lowers a threshold reproduces
  neither the restoration nor the record it depends on.
- Crediting a deviation from the acceptance record alone. The record
  restores credit only for the domains its delta test covered; carrying
  it across every domain the attribute touches is how a thermal loss
  disappears behind a mechanical test.
- Scoring a different part number as a deep deduction. The campaign ran
  on another component, no credit factor applies, and letting a weight
  decide is the failure this leaf exists to prevent.
- Averaging the domains into one number. The average hides the single
  short domain, and the short domain is the test the programme has to
  book.
- Passing a deviation that nobody recorded because the arithmetic still
  clears the floor. The credit is not the only output; an undocumented
  deviation is a finding in its own right.
- Counting parts rather than installed quantity at model level. The
  exposure the flight build carries scales with how often the deviating
  part is fitted.
- Accepting functional success on the model as representativeness. The
  model working proves the circuit, not that the campaign transfers.

## Behavior contract (gate 3)

The build-standard comparison, acceptance-record validation, per-domain
credit compounding, floor comparison, categorization, undocumented
deviation list, quantity-weighted model credit, retest set and transfer
verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_2_eqm_components.py against
scripts/q6013_class_2_eqm_components_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_2_eqm_components.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
