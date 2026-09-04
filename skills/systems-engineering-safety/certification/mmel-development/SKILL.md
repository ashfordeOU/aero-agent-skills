---
name: mmel-development
description: "Use when you must develop the Master Minimum Equipment List (MMEL) proposal for a transport type design from the safety assessment results: screen each candidate equipment item for dispatch relief with the item inoperative, classify it as MMEL-eligible or forbidden from relief, assign the operator repair interval category (A, B, C, or D), attach the (O) operating procedure and (M) maintenance flags, and check the interaction of multiple inoperative items so no combination removes a safety function. Produces the per-item MMEL proposal rows with interval category, O/M flags, and the relief verdict gating the MMEL submission to the certification authority. Trigger: master minimum equipment list, MMEL proposal, dispatch relief, MEL relief, dispatch with inoperative equipment, interval category, repair interval, inoperative item screening."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: certification
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: certification
  tags: [mmel-development, master-minimum-equipment-list, mmel-proposal, dispatch-relief, mel-relief, dispatch-with-inoperative-equipment, interval-category, repair-interval, inoperative-item-screening]
  version: 0.1.0
  author: Aero Agent Skills
---

# Master Minimum Equipment List Development (systems-engineering-safety/certification/mmel-development)

Use when the task is developing the Master Minimum Equipment List
(MMEL) proposal for a transport type design from the safety assessment
results: deciding which equipment items may be dispatched inoperative
and under what repair interval and procedure constraints. This leaf
implements the deterministic MMEL screening rules in pure Python,
stdlib only. It consumes the severity inputs produced by the arp4761a
safety assessment leaves and frames the MMEL as certification data,
pairing with the certification/means-of-compliance leaf for the
compliance position of each MMEL item and the certification-basis leaf
for the governing regulations. The operator MEL (the individual
airline document derived from the type-level MMEL) is out of scope.

## Domain quick reference

- Eligibility screen: an item may be dispatched inoperative only when
  the failure condition with the item inoperative is major or lower.
  Hazardous or catastrophic single-string items are never eligible; a
  hazardous or catastrophic item is eligible only with dual or multi
  redundancy AND when it is not itself the mitigation
  (safety_function False), so the remaining channels alone meet the
  safety objective.
- Interval categories, typical public FAA MMEL interval policy in
  summary form (name and paraphrase only, actual approval is
  authority-specific): A = 3 days, B = 10 days, C = 120 days, D = no
  scheduled repair interval. The interval tightens as severity rises:
  catastrophic with redundancy to A, hazardous with redundancy to B,
  major single-string without crew action to A.
- Category assignment summary (interval_category): none to D; minor to
  D when the crew can compensate or the item is redundant, else C when
  the single-string item is flight-relevant (in a function group or a
  safety function); major to C when redundant, B with crew action,
  A otherwise; single-string eligible items never exceed C at minor or
  none severity.
- Convenience exemption: minor single-string items outside the
  flight function groups (passenger convenience such as cabin
  entertainment) carry D with no scheduled repair interval.
- (O) operating procedure flag: required when the crew can detect and
  compensate, the category is A or B, or the item backs a safety
  function. (M) maintenance flag: required when a maintenance task
  restores the item, the category is A, or the item is
  hazardous/catastrophic with redundancy. Placard: required when the
  item needs a crew placard or log entry, or the category is A or B.
- Interaction rule: two inoperative items in the same function group
  (GROUP_OF keywords: yaw, pitch, roll, brake, thrust,
  pressurization, nav, comms, flight-guidance) that both back a safety
  function raise the double-relief issue, and more than
  allowed_combination_max inoperative items in one group is issued.
- Verdict: PASS only when no hazardous or catastrophic single-string
  item sits in the rows, no interaction issue exists, and every
  category A or B row carries its (O) flag.
- Module constants: INTERVAL_DAYS {"A": 3, "B": 10, "C": 120,
  "D": None}, GROUP_OF group keywords, SEVERITY_ORDER and
  REDUNDANCY_VALUES thresholds.

## Workflow

1. Assemble the candidate items, one dict per equipment item with
   item_id, name, function, severity_if_inoperative (none, minor,
   major, hazardous, catastrophic), redundancy (single-string, dual,
   multi), safety_function, crew_action_available,
   maintenance_required and placard_required. Take the severities from
   the arp4761a safety assessment outputs.
2. Screen each item with eligibility: only eligible items are
   candidates for dispatch relief; hazardous or catastrophic
   single-string items and mitigation items go to the forbidden list.
3. Assign the repair interval with interval_category: A 3 days, B 10
   days, C 120 days, D no scheduled repair interval (INTERVAL_DAYS).
4. Attach the (O) operating procedure and (M) maintenance flags and
   the placard with o_m_flags(item, category).
5. Build the proposal with build_mmel_proposal, which returns the
   per-item rows (item_id, category, o_flag, m_flag, placard,
   eligible), the forbidden list with reasons, and the interaction
   issues between the eligible inoperative items.
6. Inspect the issues list: a double-relief issue means two
   inoperative items in one function group would remove a safety
   function, so the combination must be split or refused.
7. Gate the submission with proposal_verdict: PASS only when no
   interaction issue exists, no hazardous or catastrophic
   single-string item is in the rows, and every A or B row has its
   (O) flag.
8. Confirm the deterministic checks with the contract test
   scripts/test_mmel_development.py.

## Worked example

Items from the type safety assessment:

1. YD-1 yaw damper (dutch roll damping), severity hazardous,
   redundancy dual, safety_function False, crew_action_available True,
   maintenance_required True, placard_required True: eligible because
   the remaining channel meets the safety objective; interval
   category B (10 days); (O) True, (M) True, placard True.
2. FCS-1 primary flight computer (flight control), severity
   catastrophic, redundancy single-string: NOT eligible, forbidden
   with the single-string reason (no dispatch relief for a
   catastrophic single-string item).
3. ENT-1 cabin entertainment (passenger media), severity minor,
   redundancy single-string, no crew action: eligible; interval
   category D (no scheduled repair interval, passenger convenience
   outside the function groups); no (O), no (M), no placard.
4. Two inoperative brake system items that both back a safety
   function (severity major, redundancy dual, safety_function True):
   build_mmel_proposal raises the double-relief issue
   ("double-relief removes a safety function: BRK-1 and BRK-2 share
   function group brake") and proposal_verdict returns FAIL, so the
   certification submission is gated.
5. A severity of "very-bad" and an empty item list both raise
   ValueError.

## Verification

- Confirm eligibility(yd1_item) returns eligible and
  interval_category(yd1_item) returns ("B", reason); the YD-1 row is
  {category B, o_flag True, m_flag True, placard True}.
- Confirm ENT-1 maps to category D with all flags False.
- Confirm FCS-1 lands in the forbidden list with the single-string
  reason and never appears in the rows.
- Confirm the brake safety-function pair produces a double-relief
  issue and proposal_verdict FAIL.
- Confirm every non-physical input raises ValueError: unknown
  severity, unknown redundancy, missing required keys, empty or
  non-list item input, and interval_category on a non-eligible item.
- Run the contract test offline: python3
  scripts/test_mmel_development.py (35 tests, deterministic).

## Related leaves

- systems-engineering-safety/certification/means-of-compliance: the
  MMEL items are part of the certification data with their per-item
  compliance position.
- systems-engineering-safety/certification/certification-basis: the
  FAR-25 / CS-25 regulatory context for the type design.
- systems-engineering-safety/arp4761a/safety-assessment: the severity
  and redundancy inputs this leaf consumes.
- systems-engineering-safety/arp4754a/configuration-management:
  post-certification change control, out of scope here.

## Pitfalls

- Granting relief to a hazardous or catastrophic single-string item:
  FCS-1 (catastrophic, single-string) goes to the forbidden list and
  never appears in the rows - and an item that is itself the
  mitigation is forbidden even when redundant, because dispatching it
  inoperative removes the very protection the safety objective
  depends on.
- Reading redundancy alone as eligibility: a hazardous or
  catastrophic item is eligible only with dual or multi redundancy
  AND safety_function False, so the remaining channels alone must
  meet the safety objective - an item that backs a safety function
  is not relieved by the presence of a twin.
- Dispatching two inoperative items that share a function group: the
  double-relief rule fires when both back a safety function (the
  BRK-1 / BRK-2 brake case), and the proposal verdict FAILs until the
  combination is split or refused.
- Submitting rows without their (O) flags: every category A or B row
  must carry its operating procedure flag, and the verdict checks it
  alongside the interaction issues and the forbidden-item screen.
- Applying one interval to all severities: the category tightens as
  severity rises (catastrophic with redundancy to A, hazardous with
  redundancy to B, major single-string without crew action to A),
  while a minor single-string passenger-convenience item outside the
  flight function groups carries D with no scheduled repair interval.
- Treating the interval days as approval: A = 3, B = 10, C = 120 and
  D = no scheduled interval are paraphrased from public FAA MMEL
  guidance, and actual interval approval is authority-specific - the
  operator MEL derived from the type-level MMEL is out of scope here.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_mmel_development.py

The test covers the eligibility branches (single-string and
mitigation refusals, redundant non-mitigation and low-severity
acceptance), interval categories per severity and redundancy including
the cabin entertainment convenience anchor, the O/M/placard flag
triggers, the interaction group logic with the double-relief rule, the
proposal verdict branches, the interval days table, determinism, and
the ValueError rejections of non-physical inputs.

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 frame the
  type certification context; the interval policy and eligibility
  rules above are paraphrased from public FAA MMEL guidance at
  reference level (no verbatim policy text), and actual interval
  approval is authority-specific.
- compliance: STANDARDS-REF, gated: false.
