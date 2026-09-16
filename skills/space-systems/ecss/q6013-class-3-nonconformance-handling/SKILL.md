---
name: q6013-class-3-nonconformance-handling
description: "Use when a class 3 part fails inspection or test and the disposition must be defended. Determine what a commercial EEE nonconformance owes at the lowest assurance class under ECSS-Q-ST-60-13C clause 6.5.2: categorize the finding from its effects, mechanism and escape stage, decide whether a failure analysis is owed at all and at what depth, pick the reporting route the finding earns from an internal log up to a customer notification, refuse a use-as-is disposition that leaves an unbounded part in the build, size containment across the lot, its uninspected remainder and any sister lot, and time the response against the window the category allows. Trigger: ecss, q-st-60-13c-clause-6-5-2, class-three-commercial-eee-nonconformance, failure-analysis-owed-threshold, use-as-is-refusal-rule, nonconformance-reporting-route, lot-related-mechanism-containment."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-3-nonconformance-handling, class-three-commercial-eee-nonconformance, failure-analysis-owed-threshold, use-as-is-refusal-rule, nonconformance-reporting-route, lot-related-mechanism-containment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 3 Nonconformance Handling (space-systems/ecss/q6013-class-3-nonconformance-handling)

Use when the task is clause 6.5.2 of ECSS-Q-ST-60-13C at the lowest
assurance class: a commercial part has failed somewhere, and the finding has
to become a reported, dispositioned and contained record rather than a note
in a test log -- without pretending the programme owes the deep analysis a
higher class would have paid for.

## Domain quick reference

- At this class the failure analysis is not owed by default, and that is the
  clause working as intended rather than a gap. A minor, isolated, first
  occurrence caught at incoming verification is a scrap line and nothing
  more. The judgement worth defending is where that stops being true.
- Four separate things switch the analysis on: a category of major or above,
  a mechanism that is lot-related or still unknown, a second occurrence of
  the same mechanism, and an escape past the unit-level screens. Any one of
  them is enough, and all of the reasons that apply are reported, because
  they are what sets the depth.
- The depth is the deepest reason that applies, not the first one found. A
  major finding earns imaging; a lot-related or recurring mechanism, a
  critical category or an escape to system test earns the destructive route.
  Taking the first reason gives a shallower answer every time.
- An unknown mechanism is treated exactly like a lot-related one. It is not
  a mild case pending investigation; it is a mechanism nobody has bounded,
  and the containment cannot be smaller than the population it might reach.
- Four things close an analysis and all four are separate. The mechanism has
  to be identified, the corrective action defined, its effectivity stated by
  date code or lot, and the action verified. Every missing element is
  reported together, so fixing one does not read as closing the analysis.
- The reporting route widens rather than switches. An internal log holds a
  minor isolated finding; anything owing an analysis reaches the parts
  control board; a critical category, a safety effect, an escape to system
  test or delivered hardware reaches the customer. The narrowest route the
  finding still satisfies is the one it earns.
- Use-as-is is the disposition that keeps the part in the build, so it
  carries three independent refusals: an open analysis, a mechanism that is
  not bounded, and any safety effect. Each stands on its own and all of them
  are reported at once.
- The observed fraction is a sample statistic over the inspected quantity.
  Reading it as a lot failure rate understates a lot-related mechanism and
  overstates an isolated one, in the same direction every time.
- The uninspected remainder of the receiving lot is a population nobody
  measured. Reporting it as clear because nothing was found there turns an
  unknown into a pass, and a sister lot sharing the date code is in exactly
  the same position.

## Workflow

1. Validate the record: a non-blank identity, a recognised mechanism,
   detection stage, effect set and disposition, quantities where the failed
   count fits inside the inspected count and the inspected count inside the
   lot, and a response date at or after detection. An unknown key is refused
   rather than ignored.
2. Categorize the finding. Take the highest floor any recognised effect
   forces, then grade a lot-related or unknown mechanism up to at least
   major where it surfaced at or beyond board assembly test, keeping every
   reason.
3. Decide whether an analysis is owed at all, collecting each of the four
   reasons that applies rather than stopping at the first.
4. Derive the depth owed as the deepest of those reasons.
5. Grade the analysis performed: its depth against the depth owed, then each
   of the four closing elements, naming every one that is missing. A deeper
   analysis than the one owed is accepted.
6. Pick the reporting route by widening from the internal log through each
   condition that applies.
7. Decide whether the proposed disposition is permitted, collecting every
   refusal. Scrap always closes; a return needs the part removed; rework and
   repair need a qualified procedure and repair needs the analysis closed;
   use-as-is needs all three of its conditions.
8. Size the containment -- the whole lot plus any sister lot for a
   lot-related or unknown mechanism, the failed parts otherwise -- and
   report the uninspected remainder and the observed sample fraction
   explicitly.
9. Count working days from detection against the window the category allows,
   letting an unrecorded response keep accruing, and close on one verdict:
   disposition refused, failure analysis incomplete, response late, closed
   with lot containment, or closed.

## Pitfalls

- Reading "no analysis owed by default" as "no analysis ever". The four
  switches exist precisely because the default is thin, and a finding that
  trips one of them owes the same depth it would at a higher class.
- Taking the first reason for the depth rather than the deepest. A major
  finding with a lot-related mechanism earns the destructive route, and
  stopping at imaging leaves the disposition unsupportable whatever it found.
- Treating an unknown mechanism as a lighter case than a lot-related one. It
  is the same containment until somebody bounds it.
- Calling an analysis closed because the mechanism is understood.
  Effectivity and verification are separate elements, and without them the
  corrective action has no boundary and no evidence that it worked.
- Dispositioning use-as-is to avoid rework while the mechanism is still
  open. An unbounded mechanism cannot be limited to the parts that failed,
  however small the measured deviation looks.
- Keeping a finding in the internal log because the part was cheap. The
  route is set by the category, the effects, the escape stage and whether
  the hardware has shipped, none of which is the part price.
- Containing only the parts that failed when the lot shares the mechanism.
  The uninspected remainder is the population at risk, and a sister lot from
  the same date code is in the same position.
- Reading the observed fraction as a lot failure rate. It is a sample
  statistic over the inspected quantity and nothing else.
- Starting the response clock at the review meeting. The window runs from
  detection, so a finding that sat in a log over a weekend has already spent
  part of it before anyone opened the record.

## Behavior contract (gate 3)

The record validation, categorization with reasons, the analysis-owed
decision and the owed depth, analysis completeness across its four elements,
the widening reporting route, disposition admissibility with every refusal
collected, containment sizing across the lot and its sister lots, the
observed sample fraction, the response window and the closing verdict are
exercised by the gate 3 contract test:
scripts/test_q6013_class_3_nonconformance_handling.py against
scripts/q6013_class_3_nonconformance_handling_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_3_nonconformance_handling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
