---
name: e2008-working-standard-verification
description: "Audit the periodic correlation that keeps a daily-use solar-array working standard tied to a primary reference, per ECSS-E-ST-20-08C clause 10.2.2.3.5: count the days since the last correlation against the agreed interval and separate approaching from passed, read each correlation as a ratio of working reading to reference reading, size the drift from the baseline and between consecutive ones, combine the budget into an expanded uncertainty and ask whether the movement is larger than the method can see, then count same-sign steps so a slow creep is caught before any single one reaches the limit. Use when traceability of a working standard to a primary reference must be shown current. Trigger: ecss, e-st-20-08c, solar-array-working-standard-correlation, working-standard-recalibration-interval, primary-reference-cell-traceability, working-standard-drift-trend, correlation-expanded-uncertainty."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-working-standard-verification, solar-array-working-standard-correlation, working-standard-recalibration-interval, primary-reference-cell-traceability, working-standard-drift-trend, correlation-expanded-uncertainty]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Array — Working Standard Verification (space-systems/ecss/e2008-working-standard-verification)

Use when the task is clause 10.2.2.3.5 of ECSS-E-ST-20-08C -- the
periodic correlation that ties the working standard used day to day
back to a primary reference at an interval agreed in advance. The
working standard is the cell that goes on the simulator every morning:
handled, cycled, re-connected and left under the lamp, and none of that
leaves a mark anybody would see.

## Domain quick reference

- The interval is agreed, not derived, so the check is arithmetic on
  days rather than a judgement about wear. What it must not collapse is
  the difference between a standard approaching its interval and one
  past it. The first is a planning item and the readings it took are
  sound; the second casts doubt over every reading taken since the
  interval ran out.
- A correlation is a ratio, not a reading. The working standard and the
  primary reference are measured under the same conditions and it is
  their ratio that carries forward, because a common shift in the source
  divides out of it and a shift in the working standard does not.
- Drift is measured against the baseline correlation, the first in the
  series, and separately between consecutive ones. A standard that
  moved once and then held is a different object from one moving a
  little at every visit, and only the pair of numbers tells them apart.
- A movement smaller than the expanded uncertainty of the correlation
  is not evidence the standard moved. It is evidence the method cannot
  resolve a move that small, which is why significance is reported
  beside the drift instead of being folded into it.
- The budget combines as a root sum of squares, which assumes the
  components are independent. A correlation whose terms share a source
  -- the same reference cell behind two lines, say -- states that in
  its own budget rather than leaning on this roll-up.
- Trend outranks any single step. Three correlations that each move a
  tenth of a percent the same way describe a standard on its way out
  even though no step is near the limit, so consecutive same-sign steps
  are counted and reported as a defect in their own right.
- The primary-reference term is required in the budget. An omitted
  component is unknown, not zero, and silently dropping it would
  shrink the expanded uncertainty and make an invisible drift look
  significant.

## Workflow

1. Normalise the correlation history oldest first, rejecting a repeated
   or out-of-order day rather than sorting it, because a history whose
   order was assumed cannot support a trend.
2. Count the days from the latest correlation to the day being assessed
   and grade them against the agreed interval, reporting within,
   approaching and passed as three separate states.
3. Form the ratio of each correlation and take the cumulative drift
   against the baseline and the step drift between consecutive pairs.
4. Validate the uncertainty budget, combine it as a root sum of squares
   and widen it by the stated coverage factor.
5. Ask whether the cumulative movement exceeds that expanded
   uncertainty, and report the answer beside the drift rather than in
   place of it.
6. Count the longest run of same-sign steps, then settle the verdict:
   any drift, uncertainty or trend defect, or a passed interval, gives
   out-of-limit; an approaching interval alone gives due; nothing gives
   traceable.

## Pitfalls

- Reading a recent correlation as a current one. A correlation done
  last week against an interval that expired last year is recent and
  late at the same time, so the elapsed days are graded against the
  agreed interval and never against a sense of how long ago it feels.
- Taking drift against a nominal value. The nominal is what the cell
  was sold as; the baseline correlation is what this laboratory
  actually measured, and a drift referred to the wrong origin carries
  the transfer error of the first visit for ever.
- Declaring a drift real because it is larger than the limit. Limit and
  uncertainty answer different questions -- one whether the standard is
  still fit, the other whether the move can be seen at all -- and a
  drift can pass the second while failing the first.
- Grading each step and never the sequence. Steps inside the limit
  every time hide a standard walking steadily away, which is the whole
  reason the same-sign run is counted.
- Leaving a component out of the budget because nobody measured it. The
  root sum of squares then returns a smaller expanded uncertainty and
  every marginal drift is promoted to significant.
- Comparing a drift or an expanded uncertainty against its bound by
  bare arithmetic. Both are built from divisions and a square root and
  can land a few units in the last place from the bound on one platform
  and exactly on it on another, so the comparison absorbs that
  representation error while the bound stays where it was.

## Behavior contract (gate 3)

The day parsing, budget validation, root-sum-of-squares combination and
coverage-factor expansion, history ordering, baseline and step drift,
same-sign run counting, elapsed-day interval grading, drift significance
and the verdict precedence are exercised by the gate 3 contract test:
scripts/test_e2008_working_standard_verification.py against
scripts/e2008_working_standard_verification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_working_standard_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
