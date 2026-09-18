---
name: e5053-function
description: "Audit the function subclause of a SpaceWire service primitive against ECSS-E-ST-50-53 clause 5.2.2.1. Use when a protocol service definition needs its per-primitive purpose statements graded before baseline: confirm every declared primitive carries a function statement, measure the informative content it adds beyond the primitive name, catch a statement that only restates that name, detect parameter, generation-timing or receiver-side detail that belongs in the neighbouring subclauses, flag normative wording smuggled into an informative statement, and report two primitives sharing one statement. Trigger: ecss, e-st-50-53, service-primitive-function-subclause, primitive-purpose-statement, spacewire-service-definition, subclause-content-leakage, primitive-name-restatement, informative-statement-audit."
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
  tags: [ecss, e-st-50-spacewire-scope, e5053-function, service-primitive-function-subclause, primitive-purpose-statement, spacewire-service-definition, subclause-content-leakage, primitive-name-restatement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire Service Primitive — Function Subclause (space-systems/ecss/e5053-function)

Use when the task is the function subclause of ECSS-E-ST-50-53 clause
5.2.2.1 — the one statement that says what a service primitive is for,
written once per primitive and read by every implementer before they
reach the parameter list, the generation conditions or the receipt
behaviour.

## Domain quick reference

- A service primitive is specified by a fixed set of subclauses:
  function, semantics, when generated, effect on receipt, additional
  comments. Clause 5.2.2.1 owns the first of them. Its job is to state
  the primitive's purpose, not to describe how it is carried, when it
  fires or what the peer does with it.
- The test that separates a usable function statement from a placeholder
  is informative content. A primitive named for a data transfer whose
  function statement says it transfers data has added nothing an
  implementer did not already have from the name; the statement has to
  carry tokens the name does not.
- Content leakage between subclauses is the recurring defect. Parameter
  names, octet counts, types and encodings belong to semantics; triggers,
  timer expiries and originating events belong to when generated; state
  changes at the peer belong to effect on receipt. A function statement
  that carries them duplicates text that will drift out of step the first
  time one of the two copies is edited.
- The function subclause is informative in tone and normative in status
  only through the requirements that reference it. Normative verbs inside
  it create a second, unnumbered requirement that no compliance matrix
  will ever pick up.
- Two primitives sharing a single function statement means one of them is
  undescribed. It is a set-level defect and cannot be seen by reading one
  primitive at a time, which is why the audit runs over the whole service
  definition rather than per entry.

## Workflow

1. Validate the service definition: a non-empty sequence of primitive
   records, each with a primitive name; duplicate names are a malformed
   specification, not a finding to be reported and carried forward.
2. For each primitive, resolve its function statement. A missing key, an
   explicit null or a statement that normalises to nothing are the same
   defect — the subclause is absent.
3. Normalise whitespace, then tokenise both the primitive name and the
   statement so the comparison is not defeated by separators, case or the
   dotted request/indication suffix.
4. Subtract the name tokens and the closed stopword set from the
   statement tokens; what remains is the informative content. Below the
   declared floor the statement is a restatement of the name.
5. Scan the statement for terms owned by the neighbouring subclauses and
   group each hit under the subclause it belongs to, so the finding tells
   the author where to move the sentence rather than only that it is
   wrong.
6. Scan for normative wording and for a statement that runs past the
   sentence budget; a multi-sentence function subclause is usually two
   subclauses that have been merged.
7. Compare normalised statements across the whole set and report every
   group of primitives sharing one, then report the per-primitive results
   with the compliant count against the total.

## Pitfalls

- Accepting a statement because it is present. Presence is the cheapest
  of the checks; a one-line echo of the primitive name passes it and
  still leaves the primitive undescribed.
- Comparing raw strings when looking for duplicates. Case, trailing
  punctuation and doubled spaces hide a duplicate that normalisation
  exposes immediately.
- Moving a parameter list into the function statement to keep the
  semantics subclause short. That inverts the subclause structure and
  the duplicate drifts as soon as a parameter is added.
- Reporting content leakage without naming the owning subclause. The
  author needs the destination; an unattributed finding gets closed by
  deleting the sentence rather than relocating it.
- Treating a duplicate primitive name as a finding. A service definition
  that names one primitive twice is not partially compliant, it is
  unreadable, and the audit has to refuse it.

## Behavior contract (gate 3)

The record validation, name and statement tokenisation, informative
content measurement, restatement decision, subclause leakage grouping,
normative wording scan and set-level duplicate detection are exercised by
the gate 3 contract test:
scripts/test_e5053_function.py against scripts/e5053_function_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e5053_function.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
