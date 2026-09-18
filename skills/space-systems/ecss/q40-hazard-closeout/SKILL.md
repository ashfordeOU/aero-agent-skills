---
name: q40-hazard-closeout
description: "Perform hazard reporting, review and close-out under ECSS-Q-ST-40C: hold every hazard control on its own row of the safety verification tracking log, discharge a control only when its row is closed, cites evidence and has that evidence accepted, add the safety review board behind a catastrophic or critical hazard and an acceptance reference behind any declared residual risk, then emit the hazard close-out statement and the log rollup. Use when hazards are taken to a safety review for closure. Trigger: ecss, q-st-40c, ecss-hazard-close-out, safety-verification-tracking-log, svtl-annex-c, hazard-close-out-statement, residual-risk-acceptance-reference."
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
  tags: [ecss, q-st-40c-safety, q-st-40c, q40-hazard-closeout, ecss-hazard-close-out, safety-verification-tracking-log, svtl-annex-c, hazard-close-out-statement, residual-risk-acceptance-reference]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Safety — Hazard Reporting, Review and Close-Out (space-systems/ecss/q40-hazard-closeout)

Use when the task is the hazard reporting and review clause of ECSS-Q-ST-40C
together with safety-assurance verification of close-out and the safety
verification tracking log: hazards exist, controls have been verified, and the
board has to be told which hazards actually close.

Related but not the same: the ARP4761A safety-assessment closure rollup answers
the civil-certification question over an aircraft-level assessment. This leaf
is the ECSS hazard report and its SVTL row per control, with the board
endorsement and residual-risk acceptance that the ECSS route demands.

## Domain quick reference

- A hazard never closes directly. It closes because each of its controls
  closed, so the unit of evidence is the control, not the hazard, and the SVTL
  is the place the controls are held.
- A control with no SVTL row is not an open item. It is an item nobody is
  holding, and it will not appear on any list the review reads. That is worse
  than an open row and it should read differently in the findings.
- Closed, evidenced and accepted are three separate conditions. A row marked
  closed with no reference is a claim; a row citing evidence nobody accepted
  is a submission. Collapsing them into one boolean loses the reason.
- Severity adds conditions on top of the controls rather than changing them.
  A catastrophic hazard with every control closed still does not close without
  the safety review board behind it.
- A declared residual risk needs an acceptance reference by name. The mirror
  case matters too: an acceptance reference with no residual risk declared
  means the hazard report and the risk record disagree about what is left.
- The closure fraction is for tracking, not for deciding. A hazard at eighty
  percent is an open hazard; the fraction tells the board where the work is.

## Workflow

1. Validate the hazard report: identity, severity, at least one control, and a
   well-formed SVTL entry or an explicit absence for each control.
2. Build the SVTL rows for the tracked controls, keyed back to hazard and
   control, so the log can be read independently of the reports.
3. Name the untracked controls separately from the open ones.
4. Grade each control in order — no row, row not closed, closed without an
   evidence reference, evidence not accepted — stopping at the first reason so
   each control yields one finding with the reason that actually applies.
5. Add the hazard-level findings: board endorsement at catastrophic and
   critical, residual-risk acceptance where a residual risk is declared, and
   the orphan acceptance reference.
6. Compute the closure fraction over the controls for tracking.
7. Close the hazard only when there are no findings at all, and emit a
   close-out statement that says which it is and on what basis.
8. Roll the log up: SVTL status counts, untracked control count, open hazards,
   and whether any open hazard is catastrophic or critical.

## Pitfalls

- Closing a hazard because its controls were verified, without checking that
  the verification reached the log. Verified and tracked are different states.
- Treating an untracked control as an open one. Nothing will chase it, because
  nothing lists it.
- Accepting a closed SVTL row on its status alone. The status is the assertion
  and the evidence reference is what makes it checkable.
- Marking evidence accepted by the same party that produced it, so acceptance
  carries no independent judgement.
- Closing a catastrophic hazard on a full control set without the board. The
  controls are necessary and the endorsement is the other half.
- Reading the closure fraction as a disposition. It is a progress number and a
  hazard is closed or it is not.
- Leaving an acceptance reference behind after the residual risk was designed
  out, so the record still says something is being carried.

## Behavior contract (gate 3)

The hazard report validation, SVTL row construction, untracked-control
detection, the ordered control grading, hazard-level conditions for board
endorsement and residual-risk acceptance, the closure fraction, the close-out
statement and the hazard-closed / hazard-open disposition plus the
log-closed / log-open / log-blocked rollup are exercised by the gate 3 contract
test: scripts/test_q40_hazard_closeout.py against
scripts/q40_hazard_closeout_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q40_hazard_closeout.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
