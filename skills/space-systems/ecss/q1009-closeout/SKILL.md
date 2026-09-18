---
name: q1009-closeout
description: "Verify that a nonconformance has met its close-out criteria under ECSS-Q-ST-10-09C clause 5.4.2 before the report is closed. Use when an NCR is proposed for closure, when the retained record set has to be checked against the route that was taken, or when closure signatures and retention are in question: confirm the granted disposition was carried out and checked, hold closure while a condition or an agreed action is unfinished, name the records a departure route additionally owes, and compute how long the closed report has to stay available. Trigger: ecss, q-st-10-09c, ncr-closure-criteria, disposition-verification, capa-completion-check, closure-signature-roles, retained-record-set, ncr-retention-period."
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
  tags: [ecss, q-st-10-09c-nonconformance-scope, q1009-closeout, ncr-closure-criteria, disposition-verification, capa-completion-check, closure-signature-roles, retained-record-set, ncr-retention-period]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Nonconformance Control — Close-Out and Retained Records (space-systems/ecss/q1009-closeout)

Use when the task is the close-out step of ECSS-Q-ST-10-09C clause
5.4.2 — deciding whether a nonconformance report has actually met the
criteria that let it be closed, and what has to be retained once it is.

## Domain quick reference

- Closure is a verification, not a filing step. Four things are shown
  against criteria fixed in advance: the granted disposition was
  carried out and checked, the agreed actions were completed and shown
  effective, the records the report rests on exist, and the people
  entitled to close it have signed.
- Carried out and checked are two criteria, not one. An item that was
  reworked but never re-inspected against the grant has an unverified
  disposition, and closing on it puts an unproven repair into the
  as-built record.
- Conditions attached to the disposition close before the report does.
  A conditional grant whose analysis or inspection is still outstanding
  is an open item wearing a closed label.
- The record set depends on the route. Every closure holds the report
  itself, the disposition record and the verification evidence; a route
  that left a departure in the hardware additionally holds the approved
  concession and the as-built configuration update; a report that
  agreed actions holds their closure evidence.
- Signature authority follows severity. Product assurance and
  engineering sign every closure; a major nonconformance also needs the
  customer, because the customer granted the disposition in the first
  place.
- A closed report is a retained report. The set stays available for the
  period the programme declares, and the closure date fixes when that
  period ends — the next question about that hardware usually arrives
  years after the board has moved on.

## Workflow

1. Take the identifier, the granted disposition and the severity, and
   reject a case that cannot name them rather than closing on a
   partially described report.
2. Check the disposition twice: that it was carried out, and that what
   was carried out was verified against what was granted.
3. Count the conditions still attached to the grant; any open condition
   holds the closure regardless of how complete the rest looks.
4. Check the agreed actions are verified effective, and check the
   opposite direction too — a closure claiming verified actions on a
   report that agreed none is describing something that did not happen.
5. Derive the record set the route owes, compare it with what is held,
   and name what is absent rather than reporting a count.
6. Check the closure signatures against the roles the severity
   requires, naming the missing ones.
7. Compute the retention end date from the closure date and the
   declared retention period, and report any shortfall against the
   programme requirement.
8. Close only with every criterion met; otherwise report the unmet
   criteria together, so one board sitting can clear them all.

## Pitfalls

- Closing on the disposition alone. The disposition is one of four
  criteria; a report closed with its actions still running leaves the
  cause in place and the record says the case was handled.
- Treating a signature as agreement that the criteria were met rather
  than a check that they were. The verification comes first; the
  signature records that it happened.
- Filing a departure closure without the as-built configuration update.
  The hardware now differs from the drawing, and the only place that
  difference was ever going to be recorded is the configuration record.
- Counting a retention period from the date of the nonconformance
  rather than from closure. The period covers the closed record, and
  starting it early can retire the file while the hardware is still
  flying.
- Closing a major nonconformance on internal signatures because the
  customer is slow to respond. The customer granted the disposition;
  closing without them removes the only party who can confirm the grant
  was honoured.
- Clearing an open condition by noting it in the closure text. A
  condition closes with the evidence it named, not with a sentence in
  the report that closes over it.

## Behavior contract (gate 3)

The disposition verification, condition and action checks, record-set
derivation, signature roles, retention arithmetic and the closure
verdict are exercised by the gate 3 contract test:
scripts/test_q1009_closeout.py against scripts/q1009_closeout_logic.py
(stdlib unittest, offline). Run: python3 scripts/test_q1009_closeout.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
