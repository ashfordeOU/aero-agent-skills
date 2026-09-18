---
name: q20-test-procedures
description: "Audit the quality-assurance control of a test procedure set under ECSS-Q-ST-20C clause 5.6.3.1: confirm each procedure carries its engineering and product-assurance approvals, signed no later than issue, that every specification requirement is exercised by a step and no step cites a requirement the specification does not hold, that the procedure quotes the specification revision actually in force rather than a stale or unreleased one, and that a revision advance is backed by an approved change record. Use when a procedure set is being released, re-released after an update, or reconciled with its TSPE and TPRO baseline. Trigger: ecss, q-st-20c-clause-5-6-3-1, qa-test-procedure-approval, test-procedure-update-control, tspe-tpro-baseline-consistency, procedure-step-requirement-coverage, procedure-revision-change-record."
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
  tags: [ecss, q-st-20-quality-assurance-scope, q20-test-procedures, qa-test-procedure-approval, test-procedure-update-control, tspe-tpro-baseline-consistency, procedure-step-requirement-coverage, procedure-revision-change-record]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Quality Assurance -- Test Procedure Control (space-systems/ecss/q20-test-procedures)

Use when the task is the test-procedure control of ECSS-Q-ST-20C clause
5.6.3.1: a set of written test procedures exists, and the question is
whether it may be released to run a test -- reviewed, approved, kept
consistent with the test specification it implements, and updated under
change control rather than edited in place.

## Domain quick reference

- A procedure is released by signature, not by existence. The
  engineering signature answers for the technical content, the product
  assurance signature answers for the control of the procedure itself,
  and a customer-witnessed test adds the customer signature. A signature
  dated after the issue date is not an approval of what issued; it is a
  retrospective note, and it is a finding.
- The procedure set is graded against the test specification as a set,
  not procedure by procedure. A single procedure may legitimately cover
  part of the requirement list; what is not allowed is a requirement in
  the specification that no procedure in the set exercises. Coverage is
  therefore computed twice -- per procedure, to show what that document
  carries, and across the set, to decide release.
- Coverage has two directions. A requirement with no step is a hole in
  the test; a step citing a requirement the specification does not hold
  is a hole in the traceability, usually a requirement deleted at the
  last specification revision and left behind in the procedure.
- Consistency with the baseline is a revision question in both
  directions. Quoting a superseded specification revision means the
  procedure implements requirements that have moved. Quoting a revision
  ahead of the one in force means the procedure implements a baseline
  nobody has released, which is the worse of the two because the test
  would run against unapproved content.
- An update is a controlled event. A revision advance needs a change
  record that names the revision it came from and the revision it goes
  to, is approved, and is approved no later than the day the new
  procedure issued. A revision mark that cannot be ordered -- neither a
  letter series nor an issue number -- defeats the whole check and is an
  input error, not a tolerable oddity.

## Workflow

1. Normalise each procedure: identifier, revision mark, the
   specification it implements and the revision it quotes, issue date,
   steps with the requirements each exercises, approval signatures with
   their dates. Reject a duplicate step identifier, a duplicate approval
   role or an unorderable revision mark before grading anything.
2. Grade approvals: the mandatory roles plus the customer role when the
   test is customer-witnessed, each present and each signed on or before
   the issue date.
3. Grade coverage per procedure in both directions, keeping the covered
   fraction as evidence rather than only the pass or fail.
4. Compare the quoted specification revision with the revision in force
   and report a stale quote and a forward quote as distinct findings.
5. Grade update control: no previous revision means first issue and no
   change record is owed; an advance demands a matching approved record
   dated no later than issue; a revision behind its predecessor is an
   error in the record itself.
6. Roll up: the set is released only when every procedure is clean and
   every specification requirement is exercised somewhere in the set;
   otherwise it is held, naming the procedures and the requirements that
   hold it.

## Pitfalls

- Accepting a set because each procedure is individually approved. A
  fully approved set can still leave a requirement untested; the set
  coverage is a separate check and it is the one that decides release.
- Treating a signature date as decoration. A product assurance signature
  dated a week after issue means the document was used before it was
  controlled, which is exactly what the clause exists to prevent.
- Reading a forward specification quote as harmless optimism. It means
  the procedure was written against content that has not been released,
  so the test would verify requirements nobody has agreed.
- Editing a procedure and reissuing it without a change record, on the
  grounds that the change was small. The size of the change is not the
  criterion; the revision advance is, and an advance with no approved
  record is uncontrolled.
- Mixing revision schemes across a baseline. A letter revision and an
  issue number cannot be ordered against each other, so the comparison
  is refused rather than guessed.

## Behavior contract (gate 3)

The procedure normalisation, revision ordering, approval grading,
two-direction coverage, baseline-consistency comparison, update-control
grading and the set release verdict are exercised by the gate 3 contract
test: scripts/test_q20_test_procedures.py against
scripts/q20_test_procedures_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q20_test_procedures.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
