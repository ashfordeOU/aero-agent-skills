---
name: e1011-org-env
description: "Use when you document the organisational environment for a human spaceflight or ground-intensive mission under ECSS-E-ST-10-11C §4.2.1.5: identify crew roles and their authority levels, map ground support units and interface types, record procedure types with designated approval authorities, and verify that mandatory functions — flight control, systems monitoring, crew support — are covered by at least one ground unit. Flag gaps: missing commander role, uncovered mandatory ground function, or procedure without an approval authority. Produce a complete org-env record before the human factors context-of-use analysis proceeds. Trigger: ecss, e-st-10-system-scope, e-st-10-11c, org-env, crew-organisation, ground-support, procedures, human-factors."
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
  tags: [ecss, e-st-10-system-scope, e-st-10-11c, org-env, crew-organisation, ground-support, procedures, human-factors]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS HFE — Organisational Environment (space-systems/ecss/e1011-org-env)

Use when the task is to document the organisational environment of a
human spaceflight or ground-intensive mission as required by
ECSS-E-ST-10-11C §4.2.1.5 — capturing crew structure, ground support
units, and procedures context before the context-of-use analysis can
proceed.

## Domain quick reference

- §4.2.1.5 requires the organisational environment to be captured as
  part of the human factors context of use. It covers three areas:
  crew organisation (roles, authority levels, team hierarchy),
  ground support (mission control and specialist units, their functions
  and communication interfaces to the crew), and procedures context
  (the set of procedure types in use, their approval authorities, and
  their review cadence).
- Crew roles are characterised by a title, a stated responsibility,
  and an authority level drawn from a controlled vocabulary
  (commander, crew-member, specialist, observer). At least one role
  with authority level "commander" is required; its absence leaves the
  authority chain undefined and blocks the HFE analysis.
- Ground support units are characterised by a name, a function, and
  an interface type to the crew (direct-voice, data-link, video, text,
  indirect). Three functions are mandatory: flight-control,
  systems-monitoring, and crew-support. A unit may cover more than one
  function, but each mandatory function must appear in at least one
  unit record.
- Procedure entries are characterised by a type (nominal, contingency,
  emergency, maintenance, handover), an approval authority (a named
  role or body), and a review cycle in days. A procedure without an
  approval authority cannot be traced to any organisational decision
  point and must be flagged.

## Workflow

1. Collect every crew role entry. For each, confirm the title,
   responsibility, and authority level are present and that the
   authority level is one of the valid values. Reject entries with
   unknown authority levels before they enter the record.
2. Verify that at least one crew role carries authority level
   "commander". If none does, flag the absence as a finding — do not
   attempt to infer a commander from title text.
3. Check for duplicate role titles within the crew list. Duplicates
   suggest a copy-paste error in the input; flag each one individually.
4. Collect every ground support unit. For each, confirm that unit
   name, function, and interface type are present and that the
   interface type is from the controlled set. Reject unknown interface
   types.
5. Verify that the three mandatory ground functions — flight-control,
   systems-monitoring, crew-support — are covered by at least one
   unit record. Flag each uncovered mandatory function as a separate
   finding.
6. Collect every procedure entry. For each, confirm proc_type and
   approval_authority are present, that proc_type is from the
   controlled set, and that review_cycle_days (when provided) is a
   positive number.
7. Aggregate all findings. The org-env record is complete when the
   findings list is empty. Partial records must not be passed to the
   context-of-use analysis as if they were complete.

## Pitfalls

- Treating a record with no commander role as a minor gap — the
  authority chain for all operational decisions depends on this role;
  its absence is a blocking finding, not a warning.
- Assuming that ground support is adequately captured if at least one
  unit is on record — all three mandatory functions must be explicitly
  present; the absence of flight-control or crew-support cannot be
  inferred from a generic "MCC" entry.
- Passing procedure entries with a missing approval_authority into the
  analysis — a procedure without a traceable approving authority cannot
  be linked to any organisational decision structure, which is a
  §4.2.1.5 gap.
- Accepting duplicate crew role titles without investigation — two
  entries sharing a title typically indicate either a data entry error
  or an unresolved role split that must be resolved before the
  authority chain is valid.

## Behavior contract (gate 3)

The crew-role validation, commander check, duplicate-title check,
ground-unit validation, mandatory-function coverage check, and
procedure validation logic is exercised by the gate 3 contract test:
scripts/test_e1011_org_env.py against scripts/e1011_org_env_logic.py
(stdlib unittest, offline). Run:

    python3 scripts/test_e1011_org_env.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
