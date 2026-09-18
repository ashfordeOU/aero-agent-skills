---
name: q7080-am-records
description: "Audit a build record for the evidence an additively manufactured part has to carry years after the machine was re-tooled. Use when a build is closed out under ECSS-Q-ST-70-80C records: check every field the part class owes, separate a field nobody filled in from one filled in with nothing, work the powder blend into a virgin mass share and a reuse generation and hold both against the class limits, resolve each inspection, coupon and post-process reference against a retrievable document, and report retention alongside the verdict. Trigger: ecss, q-st-70-80-additive-manufacturing-scope, am-build-record, powder-lot-traceability, powder-reuse-generation, virgin-powder-fraction, build-parameter-record, am-record-retention."
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
  tags: [ecss, q-st-70-80-additive-manufacturing-scope, q7080-am-records, am-build-record, powder-lot-traceability, powder-reuse-generation, virgin-powder-fraction, build-parameter-record, am-record-retention]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Additive Manufacturing — Build Records (space-systems/ecss/q7080-am-records)

Use when the task is the records step of ECSS-Q-ST-70-80C -- closing
out a build so that the parameters, the powder history, the results and
the people behind them can still be retrieved long after the machine
has been re-tooled and the operator has moved on.

## Domain quick reference

- A build record is the only surviving evidence that a part was made
  the way the qualification says it was made. It answers four
  questions: what was run, what it was made of, what came out, and who
  says so. A record that answers three of the four closes nothing.
- The two failure modes are different and are treated differently. A
  field nobody filled in leaves an open record. A field filled in with
  nothing leaves a record that looks closed and is not. Neither is a
  pass, and an empty field is not a zero.
- Powder is not a single input. A load is a blend of contributions,
  each with its own lot identity, its own mass and its own count of
  builds already been through. The number the class limits is a mass
  share of virgin powder and a highest reuse generation, and both come
  out of the blend arithmetic rather than off the drum.
- The highest generation in a blend and the mass-weighted mean
  generation say different things. A small mass of heavily reused
  powder barely moves the mean and can still breach the limit, which is
  why the highest is carried separately.
- A reference is only traceability if it resolves. A record pointing at
  an inspection report, a coupon set and a post-process run that no
  retrievable document answers is a record of intent.
- Retention is part of the record, not an afterthought. The class sets
  how long the evidence is held, and a record cannot be disposed of on
  the grounds that the parts flew.

## Workflow

1. Declare the part class. The field list, the powder limits and the
   retention period all follow from it, so an uncategorized part is
   rejected rather than defaulted.
2. Sort every required field into present, blank or missing, and report
   blank and missing separately with the field named. Score the
   completeness on fields that actually carry a value.
3. Work the powder contributions into a total mass, a virgin mass
   share, a mass-weighted mean reuse generation and the highest
   generation present. Reject a blend that lists one lot twice, or a
   contribution with no lot identity.
4. Hold the virgin share and the highest generation against the class
   limits and name the breach rather than the fact of a breach.
5. Resolve every inspection, coupon, post-process and non-conformance
   reference against the document index, and list each one that answers
   to nothing.
6. Report retention alongside a verdict: complete and traceable,
   incomplete with the holes named, or complete but standing on a
   material history the class does not allow.

## Pitfalls

- Recording the powder specification instead of the lot. The
  specification says what was ordered; the lot says what was loaded,
  and the reuse history belongs to the lot alone.
- Treating a blank field as a benign default. It is read downstream as
  a value that was checked and found unremarkable, when nothing was
  checked at all, and it is the field most likely to be blank on the
  build that later matters.
- Quoting a mean reuse generation as the reuse state of the load. A few
  kilogrammes of heavily reused powder can sit under a comfortable mean
  and still be the material that built the part.
- Filing a reference without filing the document. The record then
  passes every completeness check and fails the first time somebody
  tries to retrieve the evidence, which is usually during an
  investigation.
- Closing a record on the operator alone where the class also owes an
  approver. The two are different roles and the record carries both, or
  it carries no independent confirmation that the build was reviewed.
- Disposing of a record on part delivery. Retention runs from the
  record, in years the class sets, and it outlives the hardware
  programme more often than not.

## Behavior contract (gate 3)

The field status sorting, completeness score, powder blend arithmetic,
blend limits, reference resolution, retention and the records verdict
are exercised by the gate 3 contract test:
scripts/test_q7080_am_records.py against
scripts/q7080_am_records_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7080_am_records.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
