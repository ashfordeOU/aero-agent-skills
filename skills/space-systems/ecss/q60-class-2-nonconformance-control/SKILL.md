---
name: q60-class-2-nonconformance-control
description: "Manage the nonconformance and failure control system a programme runs over its class 2 EEE parts under ECSS-Q-ST-60C clause 5.5.2: escalate a part sitting in a safety-critical or single-point-failure function, grade each report minor, major or critical from effect, reach and safety consequence, derive the dispositions the grade allows and the signatures each earns, decide when a failure analysis is owed, impound siblings by shared date code for a lot-related mode and across every date code for a design-related one, detect a systematic recurrence, and count closure working days. Use when a class 2 part fails or repeats a failure mode. Trigger: ecss, q-st-60c, class-2-eee-nonconformance, class-2-usage-criticality-escalation, class-2-sibling-lot-impound, class-2-systematic-mode-recurrence, class-2-nonconformance-closure-deadline."
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
  tags: [ecss, q-st-60c-eee-components-scope, q-st-60c, q60-class-2-nonconformance-control, class-2-eee-part, class-2-eee-nonconformance, class-2-usage-criticality-escalation, class-2-sibling-lot-impound, class-2-systematic-mode-recurrence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 2 Nonconformance and Failure Control (space-systems/ecss/q60-class-2-nonconformance-control)

Use when the task is the nonconformance and failure control step of
ECSS-Q-ST-60C clause 5.5.2 for an EEE part procured to the intermediate
assurance class — turning one report on one lot into a graded,
dispositioned, contained and time-bounded programme-level record.

## Domain quick reference

- The procurement class is not the handling regime. A class 2 part sitting in
  a safety-critical function, or standing alone as a single point of failure,
  is worked to the harder standard; the class it was bought under says how much
  evidence came with it, not how much the failure matters.
- Grade first, decide after. The grade comes from the effect, how far the parts
  had already travelled and whether there is a safety consequence, and every
  later decision — dispositions, signatures, analysis, deadline — keys on it.
- A critical report has no use-as-is. Adding signatures does not convert an
  unacceptable disposition into an acceptable one; the only routes are back to
  the supplier or to scrap.
- Containment reach follows the mode family, not the paperwork. A lot-related
  mode reaches the sibling lots sharing the date code; a design-related mode
  reaches every date code of that part number and manufacturer; an
  assembly-induced or handling-induced mode reaches no sibling lot at all,
  because nothing was ever wrong with the parts.
- A second-source part carrying the same generic number is not a sibling. The
  manufacturer is part of the identity, and sweeping it in impounds hardware
  that was never at risk.
- One report is an escape; the same mode three times inside the rolling window
  is a property of the part. The count is taken over the window, so an old
  occurrence outside it does not keep a mode alive forever.
- The closure clock runs in working days from raising, and an unclosed report
  keeps accruing them. An open report is not a report inside its deadline.

## Workflow

1. Validate the report: the lot, part number, manufacturer and date code it
   names, the effect, the reach, and the function the part was sitting in.
2. Test whether the usage escalates the handling regime — safety-critical
   function or single point of failure — before grading anything.
3. Grade the report minor, major or critical from effect and reach, force
   critical on a safety consequence, and lift one step for an escalated usage.
4. Derive the dispositions the grade allows and the signatures the chosen one
   earns, rejecting a disposition the grade never offered.
5. Decide whether a failure analysis is owed: always above minor, always on a
   functional failure, always once the mode reads as systematic.
6. Impound the sibling lots the mode family actually reaches, matching on part
   number and manufacturer and, for a lot-related mode, on date code too.
7. Count the mode's occurrences inside the rolling window, mark it systematic
   at the threshold, and report the closure working days against the deadline
   the grade sets.

## Pitfalls

- Handling a class 2 part gently because of its class. The part's function
  decides the consequence; a single-point-failure part that drifts out of
  specification is not a minor report whatever it was bought as.
- Signing a use-as-is on a critical report. The signature chain exists to
  approve allowed dispositions, not to widen the set.
- Impounding by part number after a workmanship failure. Nothing is wrong with
  the sibling lots, and the impound freezes a build for no gain.
- Impounding only the date code after a design-related mode. The next date code
  carries the same design and the same failure.
- Counting recurrences over all time. Every mode eventually reaches three
  occurrences; only the ones inside the window say anything about the part now.
- Reading an open report as within deadline. The clock does not stop because
  nobody closed the record.

## Behavior contract (gate 3)

The usage escalation test, the grading, the allowed-disposition and approval
chains, the failure-analysis trigger, the mode-family containment reach, the
windowed recurrence count and rate, the working-day closure clock and the
assembled assessment are exercised by the gate 3 contract test:
scripts/test_q60_class_2_nonconformance_control.py against
scripts/q60_class_2_nonconformance_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_2_nonconformance_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
