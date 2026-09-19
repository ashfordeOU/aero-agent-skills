---
name: q6005-repair-general-conditions
description: "Verify that a proposed repair on a hybrid microcircuit satisfies the general conditions of ECSS-Q-ST-60-05C clause 10.5.1: test the operator's certification for this specific action and its validity on the day of the work, count the attempts already spent at the bond site and on the element against their allowances, measure the fraction of the unit's elements that would have been repaired, confirm the record set that travels with the work, and return the permission with every failing condition named. Use when a repair has to be authorised or audited. Trigger: ecss, q-st-60-05c, hybrid-repair-operator-qualification, repair-attempt-allowance, repaired-element-fraction-limit, hybrid-repair-record-set, repair-authorization-conditions."
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
  tags: [ecss, q-st-60-05-hybrid-procurement, q6005-repair-general-conditions, hybrid-repair-operator-qualification, repair-attempt-allowance, repaired-element-fraction-limit, hybrid-repair-record-set, repair-authorization-conditions]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — General Repair Conditions (space-systems/ecss/q6005-repair-general-conditions)

Use when the task is authorising or auditing an individual repair on a hybrid
microcircuit against the general conditions of ECSS-Q-ST-60-05C clause
10.5.1 — who is allowed to do the work, how many times it may be attempted,
and what has to be written down.

## Domain quick reference

- Certification is per action and time-limited, not a general licence. An
  operator certified for wire rebonding is not thereby certified to replace an
  element, and a certification that had lapsed on the day of the work does not
  cover it retrospectively, whatever the operator's experience.
- A certification with no expiry date is not an open-ended certification. It
  is an incomplete record, and the condition it evidences — that the operator
  was current — is unverified rather than satisfied.
- Attempts are counted at two scopes, because two things wear out. A bond site
  tolerates the original bond and one rebond, after which the pad and the
  metallization beneath it have been worked too often; an element tolerates
  one repair, after which the thermal and mechanical history of its attachment
  is no longer the one that was qualified.
- Both counts come from the unit's repair history, not from the current
  operation. The attempt about to be made is the next one, so an allowance of
  two is spent by one prior rebond, and the arithmetic has to be done on the
  record rather than on what the operator remembers.
- The whole-unit limit exists because per-element allowances compose badly.
  Ten elements each repaired once, all within their own allowance, is a
  rebuilt unit; the fraction of elements touched is what makes that visible.
- The record set is the repair. An unrecorded repair cannot be distinguished
  later from a manufacturing anomaly, and the unit's history — which drives
  every allowance above — is only as good as the entries in it.

## Workflow

1. Validate the operator: a named identity, a certification covering the
   requested action, and an expiry date on or after the day of the work.
   Refuse an anonymous operator or a malformed date outright.
2. Normalise and validate the unit's prior repair history, folding case and
   separators so one element does not appear under two spellings and split its
   own count.
3. Count the repairs already made on the target element and add the one being
   proposed; compare with the per-element allowance.
4. Count the attempts already spent at the target bond site, the original bond
   included, and compare with the per-site allowance. A repair with no bond
   site spends no site attempt.
5. Measure the fraction of the unit's elements that would have been repaired
   once this one is, counting distinct elements rather than repair events, and
   compare with the whole-unit limit — treating a value exactly on the limit as
   inside it, settled by a named tolerance rather than a strict comparison.
6. Compare the records supplied with the required set, matching names
   insensitively to case and separator.
7. Return the permission with every failing condition named, plus the findings
   that matter next time: a unit on its limit, a bond site on its last
   attempt.

## Pitfalls

- Reading experience as certification. The condition is documentary: the
  certification names the action and carries a date, and an operator who could
  plainly do the work is still not authorised to do it.
- Counting the proposed attempt as if it were the first. The allowance covers
  the total, so the count to compare is the history plus one; comparing the
  history alone grants one extra attempt every time.
- Counting repair events instead of distinct elements for the whole-unit
  limit. Two repairs on one element are one element repaired, and conflating
  them either blocks a legitimate repair or hides a rebuilt unit.
- Splitting an element's history across two spellings. Two entries of one
  each, where one element was repaired twice, silently restores an allowance
  that was already spent.
- Deciding an exactly-on-the-limit fraction with a strict comparison. That
  case is common, because units are built in round numbers of elements, and a
  last-bit rounding difference must not decide whether the repair is allowed.
- Treating the record set as paperwork that can follow. The next repair's
  allowances are computed from these entries; a repair recorded later, or not
  at all, corrupts every allowance computed after it.

## Behavior contract (gate 3)

The operator qualification, the per-element and per-bond-site attempt
allowances, the repaired-element fraction, the record set and the overall
permission are exercised by the gate 3 contract test:
scripts/test_q6005_repair_general_conditions.py against
scripts/q6005_repair_general_conditions_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q6005_repair_general_conditions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
