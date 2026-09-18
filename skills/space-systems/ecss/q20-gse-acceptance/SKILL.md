---
name: q20-gse-acceptance
description: "Evaluate the acceptance of ground support equipment under ECSS-Q-ST-20C clause 5.8.4.2: grade each acceptance result against the agreed GSE requirement it answers, keep the measured margin rather than only the verdict, refuse a reported pass whose own measurement misses the bound, insist that a safety-critical requirement be shown by test or inspection instead of argued on paper, compute acceptance coverage over the requirement set, and separate a failure carried on an approved waiver from one that stops the equipment. Use when GSE has finished its acceptance campaign and someone has to say whether it may be used. Trigger: ecss, q-st-20c-clause-5-8-4-2, gse-acceptance-test-grading, gse-acceptance-margin, gse-acceptance-coverage, gse-waivered-limitation, gse-release-for-use."
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
  tags: [ecss, q-st-20c-quality-assurance-scope, q20-gse-acceptance, gse-acceptance-test-grading, gse-acceptance-margin, gse-acceptance-coverage, gse-waivered-limitation, gse-release-for-use]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS GSE Acceptance (space-systems/ecss/q20-gse-acceptance)

Use when the task is the clause 5.8.4.2 acceptance of ground support equipment
in ECSS-Q-ST-20C: the acceptance tests and acceptance reviews have been run
against the agreed GSE requirements, and the equipment is either released for
use, released with what it cannot do written down, or held.

## Domain quick reference

- The verdict on a result and the measurement behind it are two facts, and
  they disagree more often than anyone expects. A line reading pass against a
  reading that misses its bound is the finding the review exists to catch.
- A margin is worth more than a verdict. Two requirements both pass; one
  passes by a factor and one by a whisker, and only the second tells the
  operations team what to watch.
- A value landing exactly on its bound is inside it. The bound is the bound,
  and the last few bits of a sensor conversion are a representation question,
  not an engineering one.
- Criticality decides what a method may be. Equipment that holds, lifts or
  powers flight hardware is shown behaving; analysis and review of design show
  intent, and intent does not carry a load.
- Coverage is over the requirement set, not over the results. Twelve results
  against four requirements leaves whatever was never exercised unexercised,
  and a not-run result on a requirement reopens it whatever ran earlier.
- A waiver does not turn a failure into a pass. It turns it into a limitation
  the equipment carries, and the release says so on its face.

## Workflow

1. Validate the agreed requirement set: unique identifiers, a criticality and a
   planned method from the closed vocabularies, and a bound with the side of it
   the equipment must stay on wherever the requirement is quantitative.
2. Validate the acceptance results the same way, refusing a result against a
   requirement nobody agreed and an outcome outside the vocabulary.
3. Grade each quantitative result on its own measurement, compute the margin,
   and raise the contradiction where a reported pass does not survive it.
4. Raise a failure with no approved waiver behind it, and a method the result
   used where the requirement planned another.
5. Grade method adequacy against criticality separately, since a safety-critical
   requirement closed on paper is a finding whatever the paper concluded.
6. Compute acceptance coverage, letting a not-run result reopen a requirement,
   and compare it with the required value through a named tolerance.
7. Sort waivered failures into limitations, then return released,
   released-with-limitations or not-released.

## Pitfalls

- Taking the outcome column at face value. The measurement is the evidence and
  the outcome is somebody's reading of it; the two are compared, not conflated.
- Recording a pass and discarding the margin. The equipment that passed by
  0.01 is the equipment that will fail next season, and nobody kept the number.
- Counting results instead of requirements. Three runs against one requirement
  leaves the other three untouched, and a result count hides that.
- Letting an analysis close a lifting or pressure requirement. Those are shown
  under load or under pressure, and no calculation substitutes for the sight.
- Reading a waiver as a pass. The equipment is limited, the limitation travels
  with it, and the release states it rather than burying it in the minutes.
- Accepting a coverage figure that just misses its target as close enough. The
  comparison is made through a stated tolerance or not at all.

## Behavior contract (gate 3)

The requirement and result validation, measurement grading with margins,
pass-versus-measurement contradiction, unwaivered failures, method
substitution, criticality-based method adequacy, acceptance coverage,
limitation extraction and the release verdict are exercised by the gate 3
contract test: scripts/test_q20_gse_acceptance.py against
scripts/q20_gse_acceptance_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q20_gse_acceptance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
