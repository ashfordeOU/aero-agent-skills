---
name: q60-class-2-evaluation-general-requirements
description: "Determine whether a part proposed for Class 2 use still owes an evaluation under ECSS-Q-ST-60C clause 5.2.3.1, when no prior qualification stands behind it: read the assurance class each prior record was earned at and carry it down but never up, hold every record to the same manufacturing line, the same part variant, no notified process change, its validity window and a mission profile at least as demanding, take the strongest admissible record rather than the sum of the weak ones, withhold a tailored programme the customer never agreed to, and return the elements still outstanding. Use when heritage, agency or lower-class evidence is offered in place of a Class 2 evaluation. Trigger: ecss, q-st-60c-clause-5-2-3-1, class-2-evaluation-need, class-2-prior-qualification-gap, assurance-class-evidence-direction, class-2-tailored-evaluation-programme, class-2-evaluation-decision."
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
  tags: [ecss, q-st-60c-class-2-eee-scope, q-st-60c, q60-class-2-evaluation-general-requirements, q-st-60c-clause-5-2-3-1, class-2-evaluation-need, class-2-prior-qualification-gap, assurance-class-evidence-direction, class-2-tailored-evaluation-programme, class-2-evaluation-decision]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 2 Evaluation, General Requirements (space-systems/ecss/q60-class-2-evaluation-general-requirements)

Use when the task is clause 5.2.3.1 of ECSS-Q-ST-60C: deciding that an
evaluation has to be run on a part proposed for Class 2 use, because nothing
already in hand qualifies it for that use — and deciding how much of a
programme that evaluation is.

## Domain quick reference

- Class 2 is not Class 1 with the rules relaxed by hand. It is a different
  target, and the first question a prior record has to answer is which target
  it was earned against.
- Evidence travels one way. A record earned at the stricter class carries down
  to a Class 2 use because the article was held to more, not less. A record
  earned at a looser class never carries up, however recent, however complete,
  however convenient. This single rule is what a Class 3 commercial record
  most often walks past.
- Direction alone is not admissibility. A record still has to describe the
  article that will actually be delivered: the same manufacturing line, the
  same part variant, no process change notified since, inside its validity
  window, and taken over a mission profile at least as demanding as the one in
  front of the part now. Each rule that fails names a different repair.
- Coverage is the strongest admissible record, never the sum of the weak ones.
  Three partial arguments stay three partial arguments; adding them is how an
  unevaluated part talks its way onto a Class 2 list.
- A tailored programme is granted by the customer, not by the evidence.
  Coverage inside the tailored band with no agreement on record leaves the full
  programme standing, and the missing agreement is named rather than assumed.
- A tailored programme is never an empty one. The manufacturer assessment and
  the constructional analysis describe the line the part is built on, so no
  outside record reaches them, and any element the surviving record does not
  itself cover stays outstanding beside them.
- Novelty overrides evidence. A technology never flown takes the full
  programme whatever is on offer, because no outside record can describe an
  article that does not exist anywhere else.

## Workflow

1. Describe the use context: the technology maturity, and whether the customer
   has actually agreed to a tailored programme. An unrecognised value is an
   input error, not a default.
2. Collect every prior record offered in place of an evaluation and read the
   assurance class it was earned at before reading anything else about it.
3. Discard upward travel first. A record from a looser class is refused on
   direction, and the refusal is reported in its own right so nobody re-offers
   it with a better date.
4. Hold each surviving record to all five admissibility rules at once and keep
   the list of the ones that failed; a record that is not admissible earns
   nothing, whatever its kind.
5. Take coverage as the strongest admissible record. Never accumulate, and
   report a stack of partial arguments as a finding.
6. Apply the novelty override before reading coverage, so a first-of-kind
   technology cannot be waived by a record from elsewhere.
7. Decide: no evaluation when coverage reaches a whole programme, a tailored
   programme above the tailored bound and only with customer agreement, the
   full programme otherwise, absorbing the bound comparison with a named
   tolerance rather than by moving the bound.
8. Return the outstanding elements with the decision, so the evaluation plan
   starts from what is owed rather than from a template.

## Pitfalls

- Letting a Class 3 record carry a Class 2 part because it is the only record
  in the file. The direction rule exists precisely for the case where nothing
  better was ever produced.
- Adding weak arguments together. An agency qualification plus a commercial
  qualification plus a favourable datasheet is still not a qualification, and
  the sum is the usual route by which an unevaluated part enters a design.
- Accepting a record on the part number alone. Same number, another
  manufacturing line or another die variant is how a commercial part changes
  underneath a programme with nothing on the datasheet moving.
- Reading a mission demand ratio below one as a near miss. A record taken over
  a milder profile says nothing about the harder one; it is refused, not
  derated.
- Tailoring the programme because the coverage looked good enough. Tailoring is
  an agreement the customer signs, and its absence is a finding, not a silence.
- Waiving the manufacturer assessment or the constructional analysis inside a
  tailored programme. Those two are about the line, not the part type, so no
  outside record reaches them.
- Treating a record as covering every programme element when it names only the
  two it actually ran. The elements it never touched stay outstanding.
- Reporting only the first admissibility rule that failed. Each failure names a
  different repair and a plan needs all of them.

## Behavior contract (gate 3)

The assurance-class direction rule, admissibility rules, strongest-record
coverage, customer-agreement condition on tailoring, novelty override and
residual programme are exercised by the gate 3 contract test:
scripts/test_q60_class_2_evaluation_general_requirements.py against
scripts/q60_class_2_evaluation_general_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q60_class_2_evaluation_general_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
