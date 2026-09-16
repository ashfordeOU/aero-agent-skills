---
name: q6013-class-2-nonconformance-handling
description: "Use when a part fails inspection, board test or system test and the disposition must be defended. Determine the control and failure analysis a commercial EEE nonconformance owes at the intermediate assurance class under ECSS-Q-ST-60-13C clause 5.5.2: categorize the finding from its effects, its mechanism and the stage it escaped to, decide whether an analysis is owed and at what depth, grade the analysis performed against an identified mechanism, a corrective action, a stated effectivity and a verification, refuse a disposition that leaves an unbounded part in the build, size containment across the lot, its uninspected remainder and any sister lot, and time the response. Trigger: ecss, q-st-60-13c-clause-5-5-2, class-two-commercial-eee-nonconformance, commercial-eee-failure-analysis-depth, use-as-is-refusal-rule, lot-related-mechanism-containment, nonconformance-response-window, observed-sample-failure-fraction."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-nonconformance-handling, class-two-commercial-eee-nonconformance, commercial-eee-failure-analysis-depth, use-as-is-refusal-rule, lot-related-mechanism-containment, nonconformance-response-window, observed-sample-failure-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Nonconformance Handling (space-systems/ecss/q6013-class-2-nonconformance-handling)

Use when the task is clause 5.5.2 of ECSS-Q-ST-60-13C at the intermediate
assurance class: a commercial part has failed somewhere, and the finding has
to become an analysed, dispositioned and contained record rather than a note
in a test log.

## Domain quick reference

- At this class the failure analysis is the product. A commercial part
  carries no qualification history to fall back on, so the only thing that
  bounds the risk to the parts that failed is an understood mechanism, and
  the analysis is what produces it.
- The analysis has a depth, and the depth is owed rather than chosen. A
  visual and electrical look answers a minor isolated finding; imaging
  answers a major one or an escape past the part-level screens; the deepest
  destructive route answers a lot-related mechanism, a recurrence, or a
  finding that reached system test.
- Four things close an analysis and all four are separate. The mechanism has
  to be identified, the corrective action defined, its effectivity stated by
  date code or lot, and the action verified. An analysis short of two of them
  does not become closed by fixing one, which is why every missing element is
  reported together.
- The stage a finding surfaced at is read twice. It grades a lot-related
  mechanism up to major on the escape alone, and it deepens the analysis
  owed, because a defect the screens did not catch is a defect the screens
  cannot be trusted to have caught elsewhere.
- Use-as-is is the disposition that keeps the part in the build, so it is the
  one with three separate refusals: an open analysis, a mechanism that is not
  isolated, and any safety effect. Each refusal stands on its own and all of
  them are reported.
- A lot-related mechanism contains a population nobody measured. The
  uninspected remainder of the receiving lot, and any sister lot sharing the
  date code, are exactly the parts the containment exists for, and reporting
  them as zero because nothing was found there turns an unknown into a pass.
- The observed failure fraction is a sample statistic over the inspected
  quantity. Reading it as a lot failure rate understates a lot-related
  mechanism and overstates an isolated one, in the same direction every time.

## Workflow

1. Validate the record: a non-blank nonconformance identity, a recognised
   mechanism, detection stage and disposition, quantities where the failed
   count fits inside the inspected count and the inspected count inside the
   lot, and an analysis start at or after detection.
2. Categorize the finding. Collect every recognised effect and keep the
   reasons so the category can be defended; grade a lot-related mechanism up
   to major where it surfaced at or beyond board assembly test.
3. Decide whether an analysis is owed at all: on a major category, on a
   lot-related or not-yet-known mechanism, on a recurrence count at or above
   its threshold, or on a finding that reached system test.
4. Derive the depth owed, taking the deepest of the reasons that apply rather
   than the first one found.
5. Grade the analysis performed: its depth against the depth owed, then the
   identified mechanism, the defined corrective action, the stated effectivity
   and the verification, naming every element that is missing. A deeper
   analysis than the one owed is accepted.
6. Decide whether the proposed disposition is permitted. Scrap always closes;
   a return needs the part physically removed; rework and repair need a
   qualified procedure, and repair needs the analysis closed; use-as-is needs
   a closed analysis, an isolated mechanism and no safety effect.
7. Size the containment. A lot-related mechanism reaches the whole receiving
   lot plus any declared sister lot and reports the uninspected remainder
   explicitly; an isolated mechanism reaches the parts that failed. Report
   the observed fraction over the inspected sample.
8. Time the analysis start against the window the category allows, absorbing
   the deadline itself with a named tolerance, and close on one verdict:
   disposition refused, failure analysis incomplete, response late, closed
   with lot containment, or closed.

## Pitfalls

- Choosing the analysis depth from what the laboratory can do this week. The
  depth is set by the category, the mechanism, the recurrence and the escape
  stage, and a shallower analysis leaves the disposition unsupportable
  whatever it found.
- Calling an analysis closed because the mechanism is understood. Effectivity
  and verification are separate elements, and without them the corrective
  action has no boundary and no evidence that it worked.
- Dispositioning use-as-is to avoid rework while the mechanism is still open.
  An unknown mechanism cannot be bounded to the parts that failed, so the
  disposition is not supportable however small the measured deviation looks.
- Containing only the parts that failed when the lot shares the mechanism.
  The uninspected remainder is the population at risk, and a sister lot from
  the same date code is in the same position.
- Reading the observed fraction as a lot failure rate. It is a sample
  statistic over the inspected quantity and nothing else.
- Starting the response clock at the review meeting. The window runs from
  detection, so a finding that sat in a log over a weekend has already spent
  it before anyone opened the record.
- Returning a part to its supplier while it is still installed. The return
  becomes a disposition only once the part is removed and the assembly has
  its own repair route.

## Behavior contract (gate 3)

The record validation, categorization with reasons, analysis-owed decision,
owed depth derivation, analysis completeness, disposition admissibility with
every refusal collected, containment sizing across the lot and its sister
lots, the observed sample fraction, the response window and the closing
verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_2_nonconformance_handling.py against
scripts/q6013_class_2_nonconformance_handling_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_nonconformance_handling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
