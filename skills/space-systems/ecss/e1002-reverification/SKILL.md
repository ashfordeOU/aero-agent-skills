---
name: e1002-reverification
description: "Use when determine whether a previously verified hardware item
  or software configuration requires re-verification following a design change,
  extended storage period, re-flight of previously flown hardware, or an
  observed anomaly. Apply ECSS-E-ST-10C §5.4.3 to categorize the triggering
  event, derive the minimum re-verification scope, enumerate the required
  activities (inspection, functional test, delta qualification, similarity
  assessment, structural and thermal analysis, anomaly investigation,
  documentation review), check which activities are documented, and confirm the
  item re-enters the verified database only after all required activities are
  closed or formally waived. Trigger: ecss, e-st-10-system-scope,
  re-verification, design-change, anomaly, re-flight, storage,
  verification-scope, delta-qualification."
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
  tags: [ecss, e-st-10-system-scope, re-verification, design-change, anomaly, re-flight, storage, verification-scope, delta-qualification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification — Re-verification Trigger and Scope (space-systems/ecss/e1002-reverification)

Use when the task is to determine whether a previously accepted verification
baseline must be reopened under ECSS-E-ST-10C §5.4.3 — categorizing the
event that triggers the re-assessment, scoping the minimum set of
re-verification activities, and confirming closure before the item re-enters
the verified product tree.

## Domain quick reference

- Section 5.4.3 identifies four event classes that mandate a formal
  re-verification assessment: design changes to the item or its interfaces;
  storage beyond the qualified duration or under non-standard conditions;
  re-flight of hardware that was previously flown; and anomalies observed
  during testing, storage, or in-service operation.
- Each event class maps to a minimum scope level:
  - Minor design change → delta scope (inspection, delta qualification,
    functional test, documentation review).
  - Major design change → full scope (all original verification disciplines:
    inspection, structural analysis, thermal analysis, functional test,
    environmental test, documentation review).
  - Storage within the qualified limit → inspection only (inspection and
    documentation review).
  - Storage beyond the qualified limit → limited scope (inspection, functional
    test, documentation review).
  - Re-flight → delta-with-similarity scope (inspection, similarity
    assessment, functional test, documentation review).
  - Any anomaly (in test, operation, or storage) → anomaly scope (anomaly
    investigation, inspection, functional test, documentation review).
- A formal waiver accepted by the responsible authority may reduce the scope
  below the minimum; a waived reduction is a finding of type
  "scope_reduced_by_waiver" rather than an open compliance gap.
- The item must not re-enter the verified product tree until all required
  activities are closed or waived.

## Workflow

1. Identify every event that has occurred since the last accepted verification
   baseline (design changes, storage conditions and durations, flight history,
   any anomaly reports). List each as a separate re-verification trigger.
2. For each trigger, apply the trigger-categorization table (design_change,
   storage, re_flight, anomaly) and derive the scope level. Reject an
   unrecognized event type before it enters the assessment.
3. For triggers with the same item, take the union of the required activity
   sets so that the most demanding scope governs — do not assess triggers
   in isolation when they apply to the same item.
4. Cross-reference the derived required activities against the documented
   re-verification records. Produce a gap list of activities that are required
   but not yet on record.
5. For each gap, determine whether a formal scope-reduction waiver exists and
   is accepted. Gaps without a waiver are open findings of type
   "incomplete_reverification_scope"; gaps covered by a waiver are recorded
   as "scope_reduced_by_waiver".
6. Mark the item's re-verification as complete only when the gap list is empty
   or every gap is waiver-covered. Feed the outcome into the verification
   control closeout record.

## Pitfalls

- Treating a minor design change as requiring only inspection when delta
  qualification is also mandatory — the delta scope always includes a
  qualification step for the affected parameter, not just a look-see.
- Merging multiple triggers and taking only the largest single scope instead
  of the union — if both a minor change (delta) and an anomaly (anomaly
  scope) apply to the same item, the required set is the union of both, not
  either one alone.
- Accepting "no test anomaly observed" as a substitute for the anomaly
  investigation activity — the investigation is required even if the anomaly
  appears benign; its absence is an open finding.
- Closing re-verification before the documentation review is complete —
  "documentation_review" is a required activity in every scope level and
  cannot be satisfied by verbal confirmation alone.
- Treating a waiver as auto-granted — a scope-reduction waiver must be
  formally accepted by the responsible authority; an internal team decision
  does not count and leaves an open "incomplete_reverification_scope" finding.

## Behavior contract (gate 3)

The trigger categorization, scope derivation, required-activity enumeration,
coverage checking, and compliant-or-not assessment logic is exercised by the
gate 3 contract test: scripts/test_e1002_reverification.py against
scripts/e1002_reverification_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_reverification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
