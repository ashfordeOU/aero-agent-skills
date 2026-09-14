---
name: q6013-class-1-evaluation-testing
description: "Evaluate whether an evaluation test campaign qualifies a commercial part type for flight under ECSS-Q-ST-60-13C clause 4.2.3.4: refuse a campaign whose part type carries no manufacturer, part number and date-code identity, treat an unexecuted mandatory block as a coverage shortfall rather than a clean block, hold every block to its sample-size floor and its admissible failure count, require the declared lot diversity, and accumulate endurance device-hours against the required floor under a named tolerance. Use when evaluation results have to become a part-type qualification verdict. Trigger: ecss, q-st-60-13c-clause-4-2-3-4, commercial-part-evaluation-campaign, part-type-flight-qualification, evaluation-block-coverage, evaluation-sample-size-floor, evaluation-lot-diversity, endurance-device-hours-floor."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-evaluation-testing, q-st-60-13c-clause-4-2-3-4, commercial-part-evaluation-campaign, part-type-flight-qualification, evaluation-block-coverage, evaluation-sample-size-floor, evaluation-lot-diversity, endurance-device-hours-floor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 1 Commercial Parts — Evaluation Testing (space-systems/ecss/q6013-class-1-evaluation-testing)

Use when the task is the evaluation test campaign of ECSS-Q-ST-60-13C clause
4.2.3.4 — the campaign a commercial electrical, electronic and
electromechanical part type has to survive before that part type may be put
forward for flight at the highest assurance level.

## Domain quick reference

- The subject of an evaluation is a part type, not a delivery. The verdict is
  a statement about a manufacturer, a part number and the construction behind
  them, so the campaign is anchored to a traceable identity: manufacturer,
  part number, and the date-code or wafer-lot set the samples came from. An
  evaluation with no such identity qualifies nothing, because there is no way
  to say what a later purchase has to match.
- A campaign is a set of blocks, not a single test: construction analysis to
  see what the part actually is, electrical characterization over the intended
  range, environmental stress, an endurance run, and a radiation block. A
  block that was never executed is a coverage shortfall; it is not a block
  that passed with no failures.
- Each block carries two independent acceptance quantities: how many samples
  entered it, and how many failures it admits. A block can meet the sample
  floor and still fail on failures, or run clean and still fail on sample
  count, so both are reported per block rather than folded into one verdict.
- Sample-size floors are not uniform across blocks. A destructive construction
  analysis runs on a handful of devices while a characterization or endurance
  block runs on a full sample, so a block may carry its own floor that
  overrides the campaign default.
- Lot diversity is what turns a result about samples into a result about the
  part type. Drawing every sample from one date code measures one good lot and
  says little about the process spread behind the part number.
- Endurance evidence accumulates as device-hours, the product of the sample
  count and the run duration summed over the endurance-bearing blocks. Because
  that is a product of a count and a duration, an exactly-met floor can land a
  few units in the last place low, which is a representation question and is
  absorbed by a named tolerance.

## Workflow

1. Validate the part-type identity: manufacturer, part number and a non-empty
   date-code set. A blank field is an input error, not a field to default.
2. Validate every declared block: its normalized name, sample count, failure
   count, admissible failures, run duration and any block-specific sample
   floor. Reject a block reporting more failures than samples, and reject a
   block declared twice.
3. Compare the executed set against the mandatory block set and record each
   absent block as its own finding.
4. Assess each executed block against its applied sample floor and its
   admissible failure count, keeping both findings when both apply.
5. Count the distinct lots behind the sample set and compare with the declared
   minimum lot count.
6. Accumulate device-hours across the endurance-bearing blocks and compare
   with the required floor, absorbing floating-point representation error at
   the boundary with a named tolerance rather than by lowering the floor.
7. Report the per-block records, the absent blocks, the lot count, the
   accumulated device-hours and a qualification verdict carrying every
   finding, not only the first.

## Pitfalls

- Reading an absent block as a clean block. A campaign that never ran the
  radiation block has zero radiation failures; that is a coverage shortfall
  and has to be named as one before any verdict is formed.
- Folding sample count and failure count into a single pass mark. They fail
  for different reasons and are repaired differently — one needs more devices,
  the other needs a failure investigation — so each is reported separately.
- Applying one sample floor to every block. A destructive block and an
  endurance block do not carry the same floor, and forcing the campaign
  default onto a block that declares its own either over-tests or under-tests
  it.
- Drawing every sample from a single date code. The campaign then describes
  one lot, and a later purchase from a different lot inherits a qualification
  that was never evidenced for it.
- Lowering the required device-hour floor to absorb an exactly-met case. An
  equality at the limit is a representation question, handled by the tolerance
  inside the comparison; the required value stays as declared.
- Stopping at the first finding. The campaign owner needs the whole shortfall
  list to plan one repeat round rather than discovering the next shortfall
  after the next round.

## Behavior contract (gate 3)

The part-type identity validation, block validation, mandatory-block coverage,
per-block sample and failure verdicts, lot-diversity count, device-hour
accumulation and the overall qualification verdict are exercised by the gate 3
contract test: scripts/test_q6013_class_1_evaluation_testing.py against
scripts/q6013_class_1_evaluation_testing_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_1_evaluation_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
