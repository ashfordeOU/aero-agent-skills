---
name: e2007-electromagnetic-effects-verification-report
description: "Use when assess or audit the electromagnetic-effects verification-report anchored at ECSS-E-ST-20-07C clause 5.1.3: correct each indicated receiver reading with its antenna-factor and cable-loss terms, compute the emission-margin against the applicable limit and against the margin demanded by the function-criticality, reject a recorded outcome that contradicts its own measured margin, require an evidence-reference of the document family matching the verification-method, hold every failure or deviation to a nonconformance with a recorded disposition, trace every reported entry back to a planned activity, and decide whether the compatibility campaign is closed. Trigger: ecss, e-st-20-07c, electromagnetic-effects-verification-report, emc-campaign-closure, emission-margin-db, measured-level-correction, evidence-reference-traceability, nonconformance-disposition, function-criticality-margin."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-07c, e2007-electromagnetic-effects-verification-report, emc-campaign-closure, emission-margin-db, measured-level-correction, evidence-reference-traceability, nonconformance-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Electromagnetic Effects Verification Report (space-systems/ecss/e2007-electromagnetic-effects-verification-report)

Use when the task is the reporting document of ECSS-E-ST-20-07C clause
5.1.3 -- the record that captures the analyses, the measured results and
the outcome of each activity of the electromagnetic compatibility
verification campaign, and from which campaign closure is declared.

## Domain quick reference

- The report is the results record answering the verification-plan: one
  entry per planned activity, each carrying the requirement it closes,
  the verification-method used, the recorded outcome, the reference to
  the evidence document, the date, and -- for a measured activity -- the
  levels behind the outcome. A plan activity with no entry leaves the
  campaign open regardless of how good the reported entries look.
- A measured outcome is never the raw receiver reading. The indicated
  level is corrected by the terms of the measurement chain: the
  antenna-factor and cable-loss raise the corrected level, pre-amplifier
  gain lowers it. The emission-margin is the applicable limit minus that
  corrected level.
- The margin the corrected level must keep depends on the criticality of
  the function served: a standard function needs the level at or below
  the limit, a mission-critical function a few decibels of margin, a
  safety-critical function more. The report states the criticality, not
  only the number, otherwise the outcome cannot be judged.
- A recorded outcome and its own measured margin must agree. A pass
  recorded against a margin below the required one, or a failure
  recorded against an adequate margin, is a reporting defect and is
  caught before any engineering interpretation begins.
- Evidence references carry the document family of the method used: a
  measured activity points at a test-report, a modelled one at an
  analysis-note, a build-state one at an inspection or review record.
  A reference in the wrong family means the outcome is unsupported.
- A failure or a pass-with-deviation must raise a nonconformance and
  that nonconformance must carry a disposition (accept-as-is, repair,
  rework, waiver, or a passed retest). An undispositioned nonconformance
  is an open item; a failure with no nonconformance at all is a gap in
  the record.
- Campaign closure needs both an empty findings list and no open
  outcome: a deviation dispositioned by waiver may close, an outstanding
  failure or an unexecuted activity may not.

## Workflow

1. Normalize every report entry: activity pointer, requirement pointer,
   verification-method, outcome state, evidence-reference, date, and the
   optional measured block and nonconformance block. Reject a malformed
   entry (absent key, unknown method or outcome, unparseable date,
   non-numeric level, nonconformance without an identifier) up front.
2. For each measured block, apply the measurement-chain corrections to
   the indicated reading, compute the margin against the applicable
   limit, and derive the measured verdict from the margin required by
   the declared criticality.
3. Compare the recorded outcome against that measured verdict and raise
   a finding on any contradiction, in either direction.
4. Check the evidence-reference against the document family implied by
   the method; a blank reference, a bare prefix, or a reference from
   another family is a finding. An unexecuted activity is exempt from
   the evidence check but is itself reported as not executed.
5. Require a measured block behind any outcome closed by measurement;
   a modelled or build-state outcome needs none.
6. For every failure or deviation, confirm a nonconformance with a
   disposition on record.
7. Trace the entry set against the planned activity set: list planned
   activities with no entry, and entries for activities never planned.
8. Summarize the outcome counts, then declare closure only when no
   finding remains and no outcome is still open.

## Pitfalls

- Reading the indicated receiver level as the measured level and
  reporting a margin that never included the antenna-factor and the
  cable-loss -- the correction terms are part of the result, not an
  accounting detail.
- Judging every margin against zero because the limit was met, when the
  function served is mission-critical or safety-critical and owes
  additional margin; the criticality belongs in the entry.
- Treating a pass-with-deviation as a pass because the outcome word
  starts the same way: the deviation must be carried by a
  nonconformance with a disposition before it can close anything.
- Declaring the campaign closed on the strength of the reported entries
  while planned activities sit unreported -- completeness is measured
  against the plan, never against the report's own contents.
- Rounding an exactly-met margin away: a corrected level built from a
  sum of decibel terms can land a few units in the last place below the
  required margin purely through binary representation. Absorb that in
  the comparison; never relax the required margin itself.

## Behavior contract (gate 3)

The level-correction, margin, outcome-consistency, evidence-reference,
nonconformance-closure, traceability and campaign-closure logic is
exercised by the gate 3 contract test:
scripts/test_e2007_electromagnetic_effects_verification_report.py
against
scripts/e2007_electromagnetic_effects_verification_report_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2007_electromagnetic_effects_verification_report.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
