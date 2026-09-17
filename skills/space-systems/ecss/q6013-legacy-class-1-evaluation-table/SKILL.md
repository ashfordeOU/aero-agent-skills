---
name: q6013-legacy-class-1-evaluation-table
description: "Assess a legacy evaluation test list for active commercial parts bought to the highest assurance class against the ECSS-Q-ST-60-13C Table 8-9 programme: confirm every required evaluation group is declared once, decide which groups existing heritage data may be credited against, refuse credit whose report names another manufacturer, site or technology, sits below the assurance class being bought to, or has aged past its validity window, reduce the list to the residual programme, allocate the devices that programme consumes, and take each remaining group on an accept-on-zero basis. Use when a heritage active part's evaluation list has to become a release or repeat verdict. Trigger: ecss, q-st-60-13c-table-8-9, legacy-part-evaluation-test-list, heritage-evaluation-credit, evaluation-evidence-validity-window, evaluation-device-allocation, highest-assurance-class-evaluation."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-legacy-class-1-evaluation-table, legacy-part-evaluation-test-list, heritage-evaluation-credit, evaluation-evidence-validity-window, evaluation-device-allocation, highest-assurance-class-evaluation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Parts -- Legacy Evaluation Test List, Highest Assurance Class (space-systems/ecss/q6013-legacy-class-1-evaluation-table)

Use when the task is the Table 8-9 evaluation test list of ECSS-Q-ST-60-13C:
an active commercial part is being bought to the highest assurance class, it
already has evaluation standing from an earlier procurement, and the question
is which evaluation groups that standing covers and which still have to be
run before the part type is released for use.

## Domain quick reference

- Evaluation is a once-per-part-type exercise, not a per-lot one. It asks
  whether this part, from this source, in this technology, can meet the
  assurance class at all. That is why legacy standing is worth something and
  why it has conditions attached.
- A legacy credit is sound only when four things hold at once: the report
  describes the same manufacturer and the same manufacturing site, the same
  technology, an assurance class at least as demanding as the one now being
  bought to, and an age inside the validity window. Any one of the four
  failing puts the group back into the programme to be run.
- Evidence may be credited downwards but never upwards. A report raised to
  the highest class stands for a less demanding procurement; a report raised
  to a less demanding class does not stand for the highest one, because the
  sample sizes and the durations behind it were smaller.
- Some groups take no credit at all. Construction analysis and destructive
  physical analysis read the material actually delivered -- the die, the
  bond, the mould -- so a report on a different date-code answers a
  different question however recent it is.
- Evaluation consumes devices and several of its groups end them. The
  residual programme therefore has to fit the devices the evaluation lot can
  give up, and an allocation that does not fit is refused rather than
  trimmed by dropping a group.
- Residual evaluation groups accept on zero unless the list declares an
  accept number. A failure sends the part type back to a repeated
  evaluation; it is not absorbed by widening the sample.

## Workflow

1. Validate the procurement context: manufacturer, site, technology, the
   assurance class being bought to, the devices the evaluation lot can give
   up, and the validity window credits are judged against.
2. Check coverage: every required evaluation group present, each declared
   once, and any group outside the required set reported as an addition
   rather than counted towards coverage.
3. Judge each offered legacy report against the context, naming every rule
   it failed rather than the first, and report a report offered for a group
   the list never declared as orphan evidence.
4. Reduce the declared list to the residual programme: the groups no sound
   credit covers.
5. Allocate devices to the residual groups and refuse an allocation that
   asks for more than the evaluation lot holds; report the devices a sound
   credit freed.
6. Take each residual group's failures against its accept number, treating
   an absent accept number as accept-on-zero.
7. Release the part type only when coverage is complete, every offered
   credit was sound, the allocation fits and no residual group failed;
   otherwise the disposition is a repeated evaluation.

## Pitfalls

- Crediting a report from a second source or a second site because the part
  number matches. The part number is the one thing that does not change when
  a line moves; the credit rules exist for exactly that case.
- Crediting a report raised to a less demanding assurance class. The credit
  direction is one way, and reading it both ways quietly buys the highest
  class on a lower class of evidence.
- Letting a recent report stand for construction analysis or destructive
  physical analysis. Those groups read the delivered material, so recency is
  not the property that matters.
- Trimming the residual programme to make the device allocation fit. A
  programme that does not fit the lot is an input to be resolved, not a list
  to be shortened silently.
- Judging a credited group on the failure count that happens to sit in the
  list beside it. A credited group was not run in this procurement, and a
  stale failure count must not decide a release.
- Absorbing an evaluation failure by enlarging the sample. Evaluation is
  accept-on-zero unless the list says otherwise, and a failure is a repeat.

## Behavior contract (gate 3)

The context validation, evidence validation, credit decision, list coverage,
residual programme, device allocation, per-group accept-on-zero verdict and
the overall release-or-repeat disposition are exercised by the gate 3
contract test:
scripts/test_q6013_legacy_class_1_evaluation_table.py against
scripts/q6013_legacy_class_1_evaluation_table_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_legacy_class_1_evaluation_table.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
