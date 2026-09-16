---
name: q60-class-1-evaluation-general-requirements
description: "Use when heritage, agency or commercial evidence is offered in place of a Class 1 qualification. Determine whether a candidate part needs a Class 1 evaluation and how much of one, when no qualification against an approved space specification stands behind it under ECSS-Q-ST-60C clause 4.2.3.1: weigh each prior-evidence claim by kind, test it for the same manufacturing line, the same part variant, no notified process change, validity and environment severity, take the strongest admissible claim rather than the sum of the weak ones, force the full programme for new or programme-specific technology, and return the outstanding programme elements with one decision. Trigger: ecss, q-st-60c, class-1-evaluation-need, prior-qualification-gap, evaluation-evidence-transferability, reduced-evaluation-programme, class-1-evaluation-decision."
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
  tags: [ecss, q-st-60-eee-scope, q-st-60c, q60-class-1-evaluation-general-requirements, class-1-evaluation-need, prior-qualification-gap, evaluation-evidence-transferability, reduced-evaluation-programme, class-1-evaluation-decision]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 1 Evaluation, General Requirements (space-systems/ecss/q60-class-1-evaluation-general-requirements)

Use when the task is clause 4.2.3.1 of ECSS-Q-ST-60C: deciding that an
evaluation has to be run on a candidate part before it can be used at the
highest assurance class, because nothing already in hand qualifies it for that
use — and deciding how much of a programme that evaluation is.

## Domain quick reference

- The question is not whether a part is good. It is whether the evidence in
  hand describes the article that will actually be delivered. Everything else
  follows from that.
- Each piece of prior evidence has a kind, and the kind fixes the most it
  could ever be worth. A qualification against an approved space specification
  could stand alone. An agency qualification or an evaluation of the same part
  from the same line reaches a reduced programme. Flight heritage, a
  commercial qualification and a datasheet declaration never do.
- Worth is only reachable when the evidence transfers: same manufacturing
  line, same part variant, no process change notified since, inside its
  validity period, and taken in an environment at least as severe as the one
  the part now faces. Each rule that fails names a different repair — another
  line is recoverable by an audit, a notified process change is not.
- Confidence in the prior qualification is the strongest admissible claim, not
  the sum of the weak ones. Three partial arguments stay three partial
  arguments; adding them is how a commercial part talks its way into a Class 1
  design.
- Novelty overrides evidence. A technology never flown before, and a part
  family whose construction is built for one programme, both take the full
  programme whatever is on offer, because no outside record can describe an
  article that does not exist anywhere else.
- A reduced programme is never an empty one. The manufacturer assessment and
  the constructional analysis are tied to the line the part is built on, so
  they stay outstanding even when the rest of the campaign is carried.

## Workflow

1. Describe the candidate part: its technology maturity and its part family.
   An unrecognised value is an input error, not a default.
2. Collect every piece of prior evidence offered in place of an evaluation and
   read its kind to get the credit ceiling.
3. Test each item against all five transfer rules at once and keep the list of
   the ones that failed; an item that does not transfer earns nothing,
   whatever its kind.
4. Take the qualification confidence as the strongest admissible credit. Never
   accumulate, and report a stack of partial arguments as a finding.
5. Apply the novelty override before reading the confidence, so a
   programme-specific family cannot be waived by a record from elsewhere.
6. Decide: no evaluation when the confidence reaches a full qualification, a
   reduced programme above the reduced threshold, the full programme below it,
   absorbing the threshold comparison with a named tolerance rather than by
   moving the threshold.
7. Return the outstanding programme elements with the decision, so the
   evaluation plan starts from what is owed rather than from a template.

## Pitfalls

- Adding weak arguments together. Heritage plus a commercial qualification
  plus a favourable datasheet is still no qualification, and the sum is the
  usual route by which an unevaluated part enters a design.
- Accepting a record on the part number alone. Same number, another
  manufacturing line or another die variant is how a commercial part changes
  underneath a programme with nothing on the datasheet moving.
- Reading an environment severity ratio below one as a near miss. Evidence
  taken in a milder environment says nothing about the harder one; it is
  refused, not derated.
- Treating an old but otherwise perfect record as good forever. The validity
  period exists because the process behind the record drifts.
- Waiving the manufacturer assessment or the constructional analysis inside a
  reduced programme. Those two are about the line, not the part type, so no
  outside evidence reaches them.
- Letting a favourable qualification record suppress the novelty rule on a
  programme-specific device. The record cannot be about that device.
- Reporting only the first transfer rule that failed. Each failure names a
  different repair and a plan needs all of them.

## Behavior contract (gate 3)

The evidence credit ceilings, transfer rules, strongest-claim confidence,
novelty override, threshold decision and outstanding programme are exercised
by the gate 3 contract test:
scripts/test_q60_class_1_evaluation_general_requirements.py against
scripts/q60_class_1_evaluation_general_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q60_class_1_evaluation_general_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
