---
name: e1002-tools-general
description: "Use when a verification tool (test equipment, GSE, simulator, software tool, or facility) needs to be categorized and given a qualification-status category (A/B/C/D) before it is used to generate verification evidence, consistent with ECSS-E-ST-10-02C verification tools clause 5.2.6.1. Trigger: verification tool, tool classification, tool qualification status, category A B C D, GSE, EGSE, MGSE, simulator qualification, software tool validation, test facility, E-ST-10-02, ecss, e-st-10c."
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
  tags: [ecss, e-st-10c, verification-tools, tool-qualification, qualification-status, gse]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification Tool Classification & Qualification Status (space-systems/ecss/e1002-tools-general)

Use when the task is classifying a tool used to support or generate
verification evidence under ECSS-E-ST-10-02C, and assigning it a
qualification-status category before its results are accepted into the
verification programme. The detailed qualification rules for specific
tool families (GSE, simulators, software tools, facilities) live in the
sibling leaves e1002-gse-tools, e1002-simulators, e1002-sw-tools, and
e1002-facilities; this leaf owns the general classification and
category-assignment step that precedes them.

## Domain quick reference

- ECSS-E-ST-10-02C clause 5.2.6.1 requires every tool used in
  verification (test equipment, ground support equipment, simulators,
  software tools, facilities) to be identified, categorized by type, and
  given a qualification status before its output is accepted as
  verification evidence.
- A tool that only supports the activity (handling, access, non-recorded
  observation) without generating the accepted evidence does not need a
  qualification category beyond basic serviceability.
- A tool whose output does generate the accepted evidence is qualified
  to one of four status categories (A most stringent through D least
  stringent), driven by two factors: the criticality of the requirement
  the tool's evidence supports (safety-critical, mission-critical,
  standard, or negligible), and whether an independent corroborating
  source exists for the same evidence.
- Category assignment must never be manually weakened below what the
  requirement criticality and corroboration state require; a proposed
  downgrade on a safety- or mission-critical tool is a disposition item,
  not a silent acceptance.

## Workflow

1. For each tool used anywhere in the verification programme, capture:
   a tool type (test equipment, GSE, simulator, software tool, facility,
   or other), whether its output generates the accepted verification
   evidence (as opposed to merely supporting the activity), the
   criticality of the requirement(s) it supports (safety-critical,
   mission-critical, standard, negligible), and whether an independent
   corroborating source exists for the same evidence.
2. Assign the qualification-status category by precedence: a tool that
   does not generate accepted evidence -> category D; else
   safety-critical requirement with no corroboration -> category A;
   safety-critical with corroboration, or mission-critical with no
   corroboration -> category B; mission-critical with corroboration, or
   standard criticality -> category C; negligible criticality -> D.
3. Attach the qualification actions expected for the assigned category:
   A requires full qualification with configuration control and
   traceable calibration before use; B requires documented qualification
   against defined performance requirements plus calibration
   traceability; C requires calibration or checkout against the
   manufacturer specification recorded in the tool's usage record; D
   requires only a basic serviceability check.
4. Build the tool register: one (type, category, actions) entry per
   tool id, and confirm every tool id used in the verification
   programme appears in the register -- an incomplete register leaves
   verification evidence resting on an uncategorized tool.
5. Before accepting a manually assigned category, re-check it against
   the category the criticality/corroboration rule would compute and
   flag any case where the manual category is weaker (less stringent)
   than required, for engineering disposition rather than silent
   acceptance.
6. Hand tools flagged as GSE, simulator, software tool, or facility to
   the matching sibling leaf (e1002-gse-tools, e1002-simulators,
   e1002-sw-tools, e1002-facilities) for the family-specific
   qualification detail; record the general category here regardless.

## Pitfalls

- Treating a support-only tool (handling, access) as if it generates
  verification evidence and over-qualifying it, or the reverse: treating
  an evidence-generating tool as support-only to avoid qualification.
- Assigning category C or D to a tool whose evidence is the sole support
  for a safety-critical requirement, understating the rigor clause
  5.2.6.1 calls for.
- Leaving a tool out of the register because it is informally used
  (a bench meter, a one-off script) even though its output is accepted
  as verification evidence.
- Accepting a manually requested category downgrade on a safety- or
  mission-critical tool without an engineering disposition.

## Behavior contract (gate 3)

The classification, category-assignment, register-completeness, and
downgrade-guard logic is exercised by the gate 3 contract test:
scripts/test_e1002_tools_general.py against
scripts/e1002_tools_general_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_tools_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
