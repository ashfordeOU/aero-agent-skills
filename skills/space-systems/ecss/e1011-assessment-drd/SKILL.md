---
name: e1011-assessment-drd
description: "Use when generate or validate the HFE continuous assessment process report per ECSS-E-ST-10-11C Annex C (normative DRD): confirm the report identifies assessment scope (system under review, mission phase, review gate or milestone), the assessment method applied (inspection, walkthrough, simulation, or user trial), a finding register where each entry carries an HFE criterion label, a severity level (critical, major, minor, or observation), and a recommendation, and a corrective-action register that links each finding to an owner and status. Derive the overall result: fail when any critical finding remains unresolved, conditional when a critical or major finding is in progress, pass otherwise. Flag any mandatory DRD section that is absent. Trigger: ecss, e-st-10-system-scope, hfe-assessment, drd, continuous-assessment, finding-register, corrective-action, assessment-report, hfe-drd."
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
  tags: [ecss, e-st-10-system-scope, hfe-assessment, drd, continuous-assessment, finding-register, corrective-action, assessment-report, hfe-drd]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors — HFE Assessment Process DRD (space-systems/ecss/e1011-assessment-drd)

Use when the task is to generate or validate the HFE continuous assessment
process report required by ECSS-E-ST-10-11C Annex C (normative): checking that
the report document satisfies the DRD's mandatory section list, that each
finding carries a severity level and an HFE criterion label, that every
corrective action is linked to a finding and carries an owner and status, and
that the overall result is correctly derived from the open severity profile of
the finding register.

## Domain quick reference

- ECSS-E-ST-10-11C Annex C defines a normative DRD for the HFE continuous
  assessment process report. The DRD requires the report to record the
  assessment scope, mission phase, review gate, the assessment method or
  methods applied, an HFE criteria list, a finding register, a
  corrective-action register, and an overall result. Every mandatory section
  must be present before the report can be formally accepted.
- Assessment methods recognized by the DRD are inspection (static review of
  design artefacts against HFE criteria), walkthrough (structured step-by-step
  task review with subject-matter experts), simulation (assessment via a
  prototype or representative simulator), and user trial (formal evaluation
  with representative operators).
- Each finding in the register carries an HFE criterion label (e.g.,
  display legibility, workload, anthropometry), a severity level, and a
  recommendation. Severity levels form an ordered set: critical (prevents
  safe or effective operation; immediate corrective action required), major
  (significant impact on performance or safety; action required before the
  next review gate), minor (limited impact; corrective action recommended),
  and observation (informational; no immediate action required).
- The overall result is derived from the open severity profile of the finding
  register against the corrective-action register: FAIL when any critical
  finding has no linked action or all linked actions remain open; CONDITIONAL
  when a critical finding's best action status is in-progress or accepted, or
  any major finding is open or in-progress; PASS when no critical or major
  finding has an unresolved or in-progress action.

## Workflow

1. Confirm the report contains all mandatory DRD sections: report identifier,
   report date, assessment scope, mission phase, review gate, assessment
   methods list, HFE criteria covered, findings list, and corrective-actions
   list. Record every absent section as a non-conformance before proceeding
   to content checks.
2. Validate the mission phase against the recognized project phase set
   (pre_phase_a through phase_f). An unrecognized phase token is a structural
   error; reject it before evaluating findings.
3. Validate each assessment method token against the recognized method set.
   An unrecognized method is a non-conformance; record it and continue to
   the next method.
4. Walk the finding register: for each entry confirm that the required fields
   are present (identifier, description, HFE criterion, severity, and
   recommendation) and that the severity level is one of the four recognized
   levels. A finding with a missing field or an unrecognized severity is
   flagged individually.
5. Walk the corrective-action register: for each entry confirm the required
   fields are present (finding identifier, action description, owner, and
   status) and that the status is one of the recognized values (open,
   in_progress, accepted, or closed). An action referencing a finding
   identifier not in the finding register is also flagged.
6. Derive the overall result from the open severity profile: scan for any
   critical finding whose best linked action status is "open" (FAIL); then
   scan for any critical finding with best status "in_progress" or "accepted",
   or any major finding with best status "open" or "in_progress" (CONDITIONAL);
   otherwise return PASS.
7. Aggregate all findings from steps 1 through 6; the report is DRD-compliant
   only when every issue list is empty and the overall result is PASS.

## Pitfalls

- Treating section presence as sufficient and skipping field-level checks —
  a section heading with no populated fields fails the DRD just as badly as
  an absent section.
- Deriving the overall result from the severity of findings alone without
  consulting the corrective-action register — a critical finding closed by a
  verified corrective action contributes to a PASS, not a FAIL.
- Accepting an assessment method token not in the recognized set — the DRD
  constrains the method vocabulary; an unrecognized method must be corrected
  before the report is submitted, not annotated as a local variant.
- Treating a missing overall result as implicitly PASS — the DRD requires
  an explicit overall result derived from the severity profile; its absence
  is itself a non-conformance regardless of the finding register content.

## Behavior contract (gate 3)

The mandatory-section check, mission-phase validation, assessment-method
validation, finding-record completeness, corrective-action record completeness,
overall-result derivation, and full-report validation are exercised by the
gate 3 contract test: scripts/test_e1011_assessment_drd.py against
scripts/e1011_assessment_drd_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_assessment_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
