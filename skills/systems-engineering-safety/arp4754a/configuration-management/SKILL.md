---
name: configuration-management
description: "Use when managing configuration of aircraft system requirements and design data per ARP4754A: identify configuration items (requirements, design data, verification data, analysis), create and version baselines, run change control (change request, impact analysis, minor vs major classification, approval, implementation, verification), check traceability closure (every requirement mapped to a design element and a verification method, every derived requirement sourced), and record change history. All logic is deterministic, offline stdlib. Trigger: configuration management, baseline, change control, change request, impact analysis, major change, minor change, safety critical requirement, certification data, interfaces, configuration item, change history, traceability closure."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: arp4754a
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: arp4754a
  tags: [arp4754a, configuration-management, change-control, baseline, traceability, impact-analysis, change-request, configuration-item]
  version: 0.1.0
  author: Aero Agent Skills
---

# ARP4754A Configuration Management (systems-engineering-safety/arp4754a/configuration-management)

Use when the task is configuration management of aircraft system
requirements and design data per ARP4754A: identifying what must be
placed under configuration control, freezing baselines, running change
control with impact analysis and minor/major classification, checking
traceability closure, and keeping a change history.

## Domain quick reference

- Configuration items (CIs) per ARP4754A: system requirements, design
  data (architecture, interfaces), verification data (tests, results),
  and analysis (safety analysis, trade studies). Working notes and
  minutes are not CIs.
- A baseline is a versioned snapshot of the CI set. All change activity
  is measured against the frozen baseline.
- Change control sequence: change request -> impact analysis (which
  requirements, design elements, verification methods, and analyses are
  affected) -> classification -> approval -> implementation ->
  verification. Classification is MAJOR when the change touches
  safety-relevant requirements, interfaces, or certification data;
  otherwise MINOR.
- Traceability closure: every requirement maps to at least one design
  element and one verification method; every derived requirement has a
  source.
- Every change is recorded in the change history log (change id,
  description, classification, status, date, sequential record id).

## Workflow

1. Identify the configuration items in the development data set
   (identify_configuration_items): requirements, design, verification,
   analysis. Non-CI data is excluded.
2. Create the baseline (create_baseline): pass the item list with
   versions; the snapshot is sorted and frozen under a baseline id and
   version. Baseline version "1.0" is the start of change control.
3. On a proposed change, run impact analysis (change_impact_analysis):
   give the change request (id + affected item ids) and the trace map.
   The impact set is expanded through the trace map so a touched design
   element, test, or analysis pulls in its owning requirements.
4. Classify the change (classify_change): major when the impact set is
   safety-relevant or the change flags interfaces_changed or
   certification_data_changed; otherwise minor.
5. Approve, implement, and verify the change, then record it
   (record_change) in the change history log with its classification
   and status.
6. On a change to a derived requirement, confirm the source is updated;
   re-run check_traceability_closure before releasing a new baseline.

## Worked example

Flight control system, baseline B-1 at version 1.0 contains REQ-101
(brake authority, safety critical), REQ-102 (derived from REQ-101), and
design/test/analysis items. A change request CR-001 proposes updating
REQ-101 braking limits.

- identify_configuration_items puts REQ-101, REQ-102, DES-201,
  TEST-301, AN-401 under configuration management; meeting minutes are
  excluded.
- create_baseline freezes the set as B-1 v1.0 (item_count 5).
- change_impact_analysis(CR-001, trace_map) expands REQ-101 to
  DES-201, TEST-301, AN-401 and reports safety_relevant True because
  REQ-101 is safety critical.
- classify_change returns "major". The change proceeds through
  approval, implementation, verification, and record_change appends
  record 1 to the history log.

## Verification checks

- Every requirement has a non-empty design mapping and a non-empty
  verification mapping (check_traceability_closure closed True).
- Every derived requirement has a source.
- No change affecting safety-relevant requirements, interfaces, or
  certification data is categorized as minor.
- Impact analysis lists every affected requirement, design element,
  verification method, and analysis before approval.
- Every change has a history record with classification and status.

## Pitfalls

- Placing working notes and minutes under configuration control: only
  requirements, design data, verification data and analysis are
  configuration items, and non-CI data is excluded from the baseline
  snapshot.
- Freezing a baseline from an unsorted, unversioned item set: the
  snapshot is sorted and frozen under a baseline id and version, and
  version \"1.0\" is the start of change control — change activity has
  no meaning before the baseline exists.
- Approving an impact analysis that lists only the directly touched
  item: the impact set is expanded through the trace map, so touching
  a design element, test, or analysis pulls in its owning requirements
  before classification.
- Classifying a safety-relevant change as minor: classification is
  major when the impact set is safety-relevant or the change flags
  interfaces_changed or certification_data_changed, so a minor label
  on REQ-101-class impact is a process failure, not a judgment call.
- Releasing a new baseline without re-running traceability closure: a
  change to a derived requirement must update its source, and closure
  must hold (every requirement mapped to design and verification,
  every derived requirement sourced) before release.
- Skipping the history record: every change is appended to the change
  history log with its classification and status, and a change with no
  record cannot be audited against the frozen baseline.

## Behavior contract (gate 3)

The logic is exercised by the contract test
scripts/test_configuration_management.py against
scripts/configuration_management_logic.py (stdlib unittest, offline,
deterministic). Run: python3 scripts/test_configuration_management.py
Contract asserts: a complete trace map passes closure; a requirement
missing its verification mapping fails closure; a change to a
safety-critical requirement classifies as major; invalid input raises
ValueError.

## Compliance

- Standards referenced, not reproduced: ARP4754A text is proprietary
  (SAE); this skill encodes CM process logic only (summary-only per
  standards-map.yaml).
- Revision note: ARP4754B (2023) supersedes ARP4754A; this skill keys
  to ARP4754A as the certification-baseline revision (FAA AC 20-174
  cites A); see standards-map.yaml arp4754a.revision_decision.
- compliance: STANDARDS-REF, gated: false.

## Related skills

- requirements-traceability: trace matrix closure across levels
  (complementary to the per-requirement closure check here).
- derived-requirements: source discipline for derived requirements.
- verification-planning: verification methods and data that must stay
  under configuration management.
- development-assurance-levels: safety relevance of requirements that
  drives major-change classification.
