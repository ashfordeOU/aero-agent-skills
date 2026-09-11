---
name: e1002-execution
description: "Use when execute verification activities against the verification plan and control document under ECSS-E-ST-10-02 clause 5.3.1: confirm every readiness condition holds before an activity starts, suspend it while any nonconformance raised against it stays open, confirm each departure from the approved procedure was authorized before execution rather than after, reconcile the as-run steps against the as-planned steps, and derive the activity's true state from its own record. Trigger: ecss, e-st-10-02c, verification-execution, readiness-review, nonconformance, deviation-approval, as-run-record, activity-state."
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
  tags: [ecss, e-st-10-02c, verification-execution, nonconformance, deviation-approval, as-run-record]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification — Execution Control (space-systems/ecss/e1002-execution)

Use when the task is to run verification activities under ECSS-E-ST-10-02
clause 5.3.1 -- against the verification plan and control document, with
nonconformances and deviations controlled while the activity is live
rather than reconciled afterwards.

## Domain quick reference

- Readiness is conjunctive, not a score. Approved procedure, available
  facility, confirmed article configuration, qualified personnel: all
  four hold or the activity does not start. Three out of four is not
  seventy-five percent ready, it is not ready.
- A nonconformance raised during execution suspends the activity until
  it is dispositioned. Suspension is a state the record implies, not a
  decision someone remembers to make.
- A nonconformance with no recorded disposition is open. The default
  runs toward stopping, because the alternative silently treats an
  unanswered question as answered.
- A departure from the approved procedure needs approval *before*
  execution continues. Approving it afterwards is the defect, not the
  departure itself: the evidence was produced outside the procedure and
  nobody agreed in advance that it would still be valid.
- The as-run record is reconciled against the as-planned steps in both
  directions -- a planned step not run, and a step run that was never
  planned. A deviation covering the step explains either one; an
  unexplained difference in either direction invalidates the evidence.
- An activity with planned steps and no as-run record at all is a single
  finding, not one per step. Nothing was recorded, and enumerating the
  plan back at the reader adds nothing.
- The state is derived from the record, never read from a status field,
  so a stale field cannot make a suspended activity look complete.
  Suspension dominates: an open nonconformance outranks unmet readiness.

## Workflow

1. Check all four readiness conditions; record each unmet one.
2. List nonconformances raised against the activity with no
   disposition; each one suspends it.
3. For each procedure deviation, confirm approval preceded execution.
4. Reconcile as-run against as-planned in both directions, treating a
   step covered by a deviation as explained.
5. Derive the activity state: suspended if anything is open, planned if
   readiness is unmet, ready if nothing has run, complete only when the
   as-run reconciles.
6. The activity's evidence enters the verification control document
   only when it completed with no findings.

## Pitfalls

- Starting on "substantially ready". The unmet condition is usually the
  one that invalidates the run -- an article in the wrong configuration
  produces perfectly good data about the wrong hardware.
- Treating a nonconformance with a blank disposition as resolved. The
  blank is the signal that nobody has decided yet.
- Accepting a deviation approved after the run as equivalent to one
  approved before. The approval is a prediction that the evidence will
  still be valid; made afterwards it is only a description.
- Reconciling as-run against as-planned in one direction. Extra steps
  nobody planned are as much a departure as planned steps skipped.
- Reading the activity's state from a stored status field, which lets a
  suspended activity report complete because nobody updated it.
- Emitting one finding per planned step when no as-run record exists at
  all, burying the single real problem in noise.

## Behavior contract (gate 3)

The readiness, open-nonconformance, deviation-approval, as-run
reconciliation and derived-state logic is exercised by the gate 3
contract test: scripts/test_e1002_execution.py against
scripts/e1002_execution_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_execution.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
