---
name: e3301-specific-mechanism-specification-sms
description: "Audit the specific mechanism specification register of a development against ECSS-E-ST-33-01 clause 4.2.2 and its Annex A content list. Use when a platform carries several mechanisms, each owes its own specification, and every one of those has to be agreed with the customer before the design is frozen. Maps mechanisms to specifications one to one, reports a mechanism with none and a specification stretched across two, scores Annex A content heading by heading, and accepts a customer agreement only when it is recorded, referenced, dated no earlier than the issue it agrees to and in place by the milestone. Trigger: ecss, e-st-33-01, specific-mechanism-specification, mechanism-annex-a-content-list, mechanism-customer-agreement, mechanism-specification-register, mechanism-specification-coverage."
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
  tags: [ecss, e-st-33-mechanisms-scope, e3301-specific-mechanism-specification-sms, specific-mechanism-specification, mechanism-annex-a-content-list, mechanism-customer-agreement, mechanism-specification-register, mechanism-specification-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Specific Mechanism Specification (space-systems/ecss/e3301-specific-mechanism-specification-sms)

Use when the task is clause 4.2.2 of ECSS-E-ST-33-01 — establishing a
specific mechanism specification for each individual mechanism to the
Annex A content list, and getting the customer's agreement on it before
the design that depends on it is frozen.

## Domain quick reference

- The specification is per mechanism, not per subsystem. Two mechanisms
  on the same platform have different duty cycles, different
  environments and different life requirements; one document covering
  both has to state every requirement twice or state it wrongly once.
- The Annex A list is a content list, so the specification is scored
  heading by heading. A document carrying nine of ten headings is not
  ninety percent agreed — the missing heading is the one nobody has had
  to commit to, and it is usually life, tribology or verification.
- Customer agreement is a dated act against a specific issue. An
  agreement dated before the issue it supposedly agrees to was given
  against an earlier document, so the issue in hand carries no
  agreement at all, whatever the register says.
- The agreement also has a deadline. Agreed after the design review it
  was meant to feed is a programmatic finding: the review proceeded
  without the baseline it was supposed to be reviewing against.
- A specification exists to be pointed at. An agreement with no
  reference cannot be produced when asked, so it is a malformed record
  rather than a weak one, and the register should refuse it instead of
  scoring it.
- Register coverage is the mechanism-side figure: how many mechanisms
  have exactly one complete, agreed specification. A pile of excellent
  documents covering half the mechanisms is half covered.

## Workflow

1. Validate the mechanism list and every specification: identifiers,
   issue and issue date, the covered mechanism identifiers, and the
   content headings, each of which has to be one of the Annex A set.
2. Map mechanisms to specifications. Raise three distinct findings — a
   mechanism with no specification, a mechanism with more than one, and
   a specification listing more than one mechanism — and flag a
   specification pointing at a mechanism the register does not contain.
3. Score each specification against the Annex A list, reporting the
   missing headings in list order and a completeness fraction rather
   than a bare verdict. Collapse a repeated heading so it cannot
   inflate the score.
4. Grade the customer agreement: absent, pending, dated before the
   issue, agreed after the milestone, or agreed. Refuse a record that
   claims agreement without a date or a reference.
5. Mark a specification ready only when it is complete and agreed, and
   count a mechanism as covered only when exactly one ready
   specification points at it.
6. Report per-specification records, the mapping, the coverage fraction,
   every finding, and the specifications that are not carrying any
   mechanism.

## Pitfalls

- Writing one specification for a family of mechanisms because they
  share a design. The shared design is the reason the requirements look
  similar; the duty cycles, thermal environments and lifetimes are what
  differ, and those are exactly what the specification exists to fix.
- Scoring the specification as a document rather than as a content
  list. A single pass or fail hides which heading is missing, and the
  missing heading is the interesting part of the answer.
- Accepting an agreement that predates the issue. It is a real
  agreement against a real document, just not this one, and nothing in
  the register distinguishes the two unless the dates are compared.
- Treating an agreement recorded after the review as merely late. The
  review was held against an unagreed baseline, so the findings that
  review raised may have been raised against requirements that
  afterwards changed.
- Reporting document-side completeness as programme coverage. Coverage
  is counted over mechanisms, so a mechanism nobody wrote a
  specification for contributes a zero that a document-side average
  never sees.
- Letting an unreferenced agreement through as a soft finding. If it
  cannot be produced, it cannot be audited, and a register that scores
  it is asserting something it cannot support.

## Behavior contract (gate 3)

The mechanism and specification validation, the one-to-one register
mapping, the Annex A content scoring, the customer-agreement state
machine and the coverage roll-up are exercised by the gate 3 contract
test: scripts/test_e3301_specific_mechanism_specification_sms.py
against scripts/e3301_specific_mechanism_specification_sms_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3301_specific_mechanism_specification_sms.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
