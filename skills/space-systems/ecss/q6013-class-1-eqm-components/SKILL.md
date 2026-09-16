---
name: q6013-class-1-eqm-components
description: "Use when an EQM parts list, build-standard delta or qualification transfer argument is reviewed. Evaluate whether commercial components fitted to an engineering qualification model represent the flight build under clause 4.1.6 of ECSS-Q-ST-60-13C: compare each fitted part with its flight-intended counterpart attribute by attribute, weight the deviations into a representativeness index, and map every deviation onto the qualification domains whose results stop transferring, so a package substitution invalidates a mechanical result while a die-lot substitution invalidates a lifetime one. Treat a different manufacturer or part number as a different part rather than a deduction. Return a per-part category, the retest set, and one transfer verdict. Trigger: ecss, q-st-60-13c, eqm-commercial-component-representativeness, eqm-to-flight-build-standard-delta, eqm-qualification-transfer-domain, eqm-representativeness-index, eqm-retest-set."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q-st-60-13c, q6013-class-1-eqm-components, eqm-commercial-component-representativeness, eqm-to-flight-build-standard-delta, eqm-qualification-transfer-domain, eqm-representativeness-index, eqm-retest-set]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Engineering Qualification Model Components (space-systems/ecss/q6013-class-1-eqm-components)

Use when the task is clause 4.1.6 of ECSS-Q-ST-60-13C: commercial components
fitted to an engineering qualification model, and how representative of the
flight build they have to be for the qualification result to mean anything.
This leaf grades a model's parts list against the intended flight build and
returns what still transfers and what has to be repeated.

## Domain quick reference

- A qualification campaign is an argument about the flight build, run on a
  model. The argument holds only where the model was the same thing. Every
  attribute on which the fitted part differs removes a piece of the argument,
  and the piece removed is specific: it is not a general loss of confidence.
- The deviations are not interchangeable. A package substitution takes away
  the mechanical and thermal results, because the load path and the thermal
  resistance both changed. A die-lot substitution takes away the lifetime and
  radiation results, because those are lot properties and the campaign
  measured a lot that will not be flown. A screening-level substitution takes
  away the lifetime claim alone.
- A different manufacturer or a different part number is not a deduction on a
  score. The model carries a different part, the campaign qualified that other
  part, and no weighting rescues the transfer. Treating it as a small penalty
  is how a model that shares nothing but a function scores above a threshold.
- The index is useful for ranking and for the model-level picture, not as the
  sole decision. It answers "how much of the build standard is shared"; the
  domain map answers "which tests have to be repeated", which is the question
  the programme actually needs before it books a shaker.
- Quantity weighting matters at model level. A deviating part fitted once in a
  harness and a deviating part fitted in every string are the same line on a
  parts list and different exposures for the flight build.
- "The board works" is not representativeness. A model built from whatever the
  lab had can pass every functional test and still transfer nothing, because
  functional success was never the claim the campaign was making.

## Workflow

1. Validate the attribute weight set: every weighted attribute must have a
   declared qualification impact, and the weights must sum to unity.
2. Compare each fitted component with its flight-intended counterpart across
   the weighted attributes, refusing a component that simply omits one rather
   than reading the omission as a match.
3. Collect the deviating attributes per component, sorted so the record is
   reproducible.
4. Subtract the deviation weights from unity to form the representativeness
   index of the component.
5. Take the union of the qualification domains the deviations invalidate.
6. Categorize the component: representative when nothing deviates,
   non-representative when a fundamental attribute deviates or the index falls
   under the threshold, partially representative otherwise, treating an
   exactly-met threshold as met through a named tolerance.
7. Form the model index as the quantity-weighted mean, and the retest set as
   the union of the domains lost by every component that is not fully
   representative.
8. Return ranked findings and one verdict: transferable, transferable with
   retest, or not transferable.

## Pitfalls

- Scoring a different part number as a partial match. The qualification result
  was produced on another component; the index is irrelevant, and letting the
  weight decide is the failure this leaf is built to prevent.
- Reading the index as the decision. A part at a high index can still have
  taken away the exact domain the campaign was run for, and the retest set,
  not the score, is what the programme plans against.
- Treating every deviation as invalidating everything. Over-broad invalidation
  costs a full requalification where a targeted mechanical retest would have
  closed the delta, and it trains reviewers to argue the map away entirely.
- Grading only the parts that were substituted deliberately. A lot change made
  by the stockroom is the same deviation as a design change, and it is the one
  nobody writes down.
- Counting parts rather than installed quantity at model level. The exposure
  the flight build carries scales with how often the deviating part is fitted.
- Accepting functional success as evidence of representativeness. The model
  working proves the circuit, not that the qualification argument transfers.

## Behavior contract (gate 3)

The weight validation, attribute comparison, index formation, domain mapping,
fundamental-attribute rule, quantity-weighted model index, retest set and
transfer verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_eqm_components.py against
scripts/q6013_class_1_eqm_components_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q6013_class_1_eqm_components.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
