---
name: q2007-documentation
description: "Manage the documentation, records and data control a space test centre owes under ECSS-Q-ST-20-07 clause 5.2.1, and say whether the control in place holds. Use when a test centre's document register, record retention or test-data handling is being audited: refuse control never established, name the issues circulating with no approval behind them, catch a superseded or withdrawn issue still on the floor and a document circulating at two live issues at once, take record retention against the centre floor and against each record's own period before disposal, and test every test-data set for integrity evidence, a backup and a traceability pointer that resolves. Trigger: ecss, q-st-20-07-clause-5-2-1, test-centre-document-issue-control, test-centre-records-retention-period, test-centre-test-data-integrity-evidence, test-centre-test-data-traceability."
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
  tags: [ecss, q-st-20-07-test-centre-quality-and-safety-scope, q2007-documentation, q-st-20-07-clause-5-2-1, test-centre-document-issue-control, test-centre-document-approval-state, test-centre-records-retention-period, test-centre-test-data-integrity-evidence, test-centre-test-data-traceability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test-Centre Quality and Safety — Documentation, Records and Data (space-systems/ecss/q2007-documentation)

Use when the task is clause 5.2.1 of ECSS-Q-ST-20-07: the test centre
controls the documents its people work to, the records it has to keep
afterwards, and the test data both of those rest on.

## Domain quick reference

- Circulation is where document control succeeds or fails. An issue in
  circulation is the issue the floor works to, so a draft on the floor,
  or an issue with no approval day behind it, is the live defect. The
  same draft sitting uncirculated is a document being written, not a
  control failure.
- A superseded or withdrawn issue is not an approval defect. It was
  approved once; the fault is that a stale issue is still reachable
  beside its replacement, which is a separate and slightly softer
  finding than work being done to something nobody signed.
- Two approved issues of one document in circulation at the same time is
  its own defect. Neither issue is unapproved and neither is superseded,
  yet two readers following the register correctly will do different
  things.
- Retention has two independent tests. A record whose declared period is
  under the centre floor will be destroyed early by a rule nobody has
  run yet; a record already disposed of before its own period elapsed is
  gone. Both are counted; only the second has already lost something.
- Test data carries two duties a paper record does not: its integrity
  has to be demonstrable, and it has to point at the record it belongs
  to. A pointer at a record the centre does not hold is worse than no
  pointer, because it reads as traceability on a register scan.
- Years are the human unit and days are the arithmetic unit. The
  conversion runs through one named factor so the same disposal date
  grades the same way on every host.

## Workflow

1. Validate the control policy first: the retention floor in years, the
   document review interval in days, and whether integrity evidence,
   backups and traceability are demanded. An unrecognised policy key is
   refused rather than ignored.
2. Validate the register: recognised document states and record
   categories, issues numbered from one, no issue approved after it was
   issued, no record disposed of before it was created, nothing
   registered twice, and no day after the assessment day.
3. Name the circulating issues with no approval behind them.
4. Name the superseded and withdrawn issues still circulating, and the
   documents circulating at more than one approved issue.
5. Take the retention shortfalls against the centre floor and the
   premature disposals against each record's own period, converting
   years to days through the named factor and comparing with a tolerance
   rather than a bare inequality.
6. Take the test-data gaps: integrity evidence, backup, and a
   traceability pointer that resolves to a record the centre holds.
7. Carry the circulating issues past their review age as advisories.
8. Close on one verdict in order: control absent, document approval
   broken, issue control broken, records retention broken, test data
   control broken, or documentation and records controlled. Report the
   named issues, records and datasets alongside it.

## Pitfalls

- Reading a superseded issue as an unapproved one. Both are on the floor
  and only one of them was never signed; merging them hides which
  control actually failed and sends the corrective action to the wrong
  place.
- Counting an uncirculated draft as a finding. Nobody is working to it,
  and a register full of drafts under revision is a centre doing its
  job.
- Grading retention on the policy statement alone. The floor catches the
  records that will be destroyed early; only each record's own period
  and disposal day catches the ones already destroyed.
- Accepting a traceability pointer without resolving it. A dangling
  pointer passes a presence check and fails the only question that
  matters, which is whether the data can be placed against a test.
- Widening the retention floor so an exact-equality case passes. An
  equality at the limit is a representation question, handled by the
  tolerance inside the comparison; the declared floor stays as it is.

## Behavior contract (gate 3)

The policy validation, document, record and dataset validation, the
approval gaps, the stale issues in circulation, the issue collisions,
the retention shortfalls and premature disposals, the test-data control
gaps, the review-age advisories and the ordered verdict are exercised by
the gate 3 contract test: scripts/test_q2007_documentation.py against
scripts/q2007_documentation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2007_documentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
