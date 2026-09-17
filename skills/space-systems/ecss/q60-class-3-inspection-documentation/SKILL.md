---
name: q60-class-3-inspection-documentation
description: "Audit whether a Class 3 parts programme recorded its inspection and control outcomes reconstructably under ECSS-Q-ST-60C clause 6.7: name every performed activity carrying no record, refuse a recording authority outside the accepted list and a supplier self-declaration nobody countersigned, reject a record whose presented count fails to reconcile with its accepted, rejected and deferred counts, demand a nonconformance reference behind every rejection and a closure behind every deferral, refuse a retention period that expires before the mission does, measure outcome coverage against its floor, and raise a low acceptance yield as an advisory rather than a defect. Use when a Class 3 parts programme has to show what its inspections found. Trigger: ecss, q-st-60c, q60-class-3-inspection-documentation, q60-c3-outcome-record-reconciliation, q60-c3-self-declaration-countersignature, q60-c3-record-retention-window."
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
  tags: [ecss, q-st-60c-eee-component-procurement, q-st-60c, q60-class-3-inspection-documentation, q60-c3-outcome-record-reconciliation, q60-c3-self-declaration-countersignature, q60-c3-record-retention-window, q60-c3-outcome-coverage-floor, q60-c3-acceptance-yield-advisory]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 3 — Inspection and Control Documentation (space-systems/ecss/q60-class-3-inspection-documentation)

Use when the task is clause 6.7 of ECSS-Q-ST-60C: the inspection and control
activities of a Class 3 parts programme have been carried out, and the
question is whether what was written down can reconstruct their outcomes.

## Domain quick reference

- The clause does not ask whether the inspections happened. It asks whether,
  years later and with nobody from the original team in the room, the outcome
  of each one can be rebuilt from the paper. Those are different questions and
  a programme can pass the first and fail the second.
- An outcome record is a claim about a specific population of parts. Without a
  traceable lot identity it describes some parts somewhere, which is the same
  as describing none.
- Class 3 widens who may write the record: a supplier may record its own
  outcome. That widening has one condition attached — the authority that
  grades its own work owes a countersignature, because a self-declaration
  nobody else signed records an opinion rather than an outcome.
- The four counts are one statement, not four. Everything presented was
  accepted, rejected or deferred, so a record whose presented count does not
  reconcile with the other three has lost parts somewhere between the bench
  and the page.
- A rejection and a deferral each owe a pointer onward. A rejected quantity
  with no nonconformance reference ends the trail at the worst moment, and a
  deferred quantity with no closure is a decision that was never taken rather
  than one taken late.
- Retention is part of the record, not an archiving detail. A record kept for
  three years cannot answer a question asked in the seventh, so the period
  stated has to outlive the mission it covers with margin on top.
- Coverage counts activities, not records. An activity covered by one
  defect-free record is covered; a second clean record for the same activity
  adds nothing, and ten defective ones cover nothing.
- A low acceptance yield is an advisory, never a defect. The programme
  rejecting a great deal is a real outcome, honestly recorded, and a rule that
  penalised it would reward writing it down less honestly.

## Workflow

1. Validate the case: the performed activities, the submitted records and the
   mission duration the retention window is priced from.
2. Put the performed activities into audit order and group the records under
   the activity each one covers.
3. Name every performed activity that carries no record at all.
4. Test each record for a traceable lot identity, an accepted recording
   authority with a countersignature where the authority is the supplier
   itself, an evidence reference, four counts that reconcile, a nonconformance
   reference behind every rejection, no deferral left open, and a retention
   period that reaches past the mission.
5. Measure outcome coverage as the share of performed activities covered by at
   least one defect-free record, and judge it against its floor.
6. Take the programme acceptance yield and raise an advisory when it sits
   below the advisory floor.
7. Return one disposition: outcomes recorded when coverage reaches its floor
   and every activity carries a record; outcomes not reconstructable when no
   activity carries a usable record; outcomes partially recorded otherwise.

## Pitfalls

- Counting records instead of activities. Five clean records for one activity
  and nothing for the other four reads as excellent paperwork and covers a
  fifth of the programme.
- Reading a signature as an authority. Somebody signed the sheet is not the
  same as somebody empowered to take the outcome signed it, and at Class 3 the
  supplier signing its own sheet is exactly the case the countersignature
  exists for.
- Accepting the three outcome counts without the presented count. The
  reconciliation is the only check that the record covers the whole lot rather
  than the part of it somebody remembered.
- Treating a deferral as a neutral state. It is a decision not yet taken, and
  a programme that closes with deferrals open has recorded questions rather
  than outcomes.
- Pricing retention against the record date rather than the mission. The
  record has to survive to the last review that could need it, and that review
  sits after the mission ends, not after the inspection.
- Grading a low acceptance yield as a documentation defect. It is an outcome,
  and a rule that punishes recording it teaches the programme to record
  something else.
- Comparing a coverage figure with its floor by bare arithmetic. Coverage is a
  quotient of small counts, so a programme landing exactly on its floor can
  read a few units in the last place below it.

## Behavior contract (gate 3)

The policy merge, activity ordering, record grouping, unrecorded activities,
the per-record defect set including the self-declaration countersignature and
the retention window, the quantity reconciliation residual, reconciled
activities, outcome coverage and its floor, the acceptance yield advisory and
the three-way recording disposition are exercised by the gate 3 contract test:
scripts/test_q60_class_3_inspection_documentation.py against
scripts/q60_class_3_inspection_documentation_logic.py (stdlib unittest,
offline).
Run: python3 scripts/test_q60_class_3_inspection_documentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
