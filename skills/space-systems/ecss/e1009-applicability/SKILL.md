---
name: e1009-applicability
description: "Use when apply the coordinate-system definitions required by ECSS-E-ST-10C §5.3.1 across all five activity domains: mission definition, engineering, verification, operations, and data processing. For each domain, determine which reference frames must be formally defined, verify that at least the required frame families are present, and identify any domain that lacks a valid frame definition. Trigger: ecss, e-st-10-system-scope, coordinate-systems, reference-frames, applicability, mission-definition, data-processing, frame-coverage."
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
  tags: [ecss, e-st-10-system-scope, coordinate-systems, reference-frames, applicability, mission-definition, data-processing, frame-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Coordinate-Definition Applicability (space-systems/ecss/e1009-applicability)

Use when the task is to apply the coordinate-system definitions of ECSS-E-ST-10C §5.3.1
across the five activity domains — mission definition, engineering, verification, operations,
and data processing — and confirm that every domain has sufficient reference-frame coverage.

## Domain quick reference

- ECSS-E-ST-10C §5.3.1 requires that coordinate-system definitions be applied consistently
  across five distinct activity domains throughout the project lifecycle. Each domain draws
  on a specific set of frame families; a domain without the required families is a
  non-compliance finding, not a warning.
- Five required applicability domains and their minimum frame-type families:
  - **mission_definition** — inertial frame (e.g. J2000/EME2000) and an Earth-fixed frame
    (e.g. ECEF/ITRF); these anchor trajectory and coverage analysis.
  - **engineering** — spacecraft body frame and a structural/mechanical reference frame;
    these support interface control and CAD-linked alignments.
  - **verification** — body frame and an inertial frame; test measurements and analysis
    results must be expressible in both.
  - **operations** — inertial, Earth-fixed, and orbital frame (e.g. LVLH/RSW/TNW);
    commanding and telemetry interpretation require all three.
  - **data_processing** — inertial frame and at least one instrument/sensor boresight frame;
    science data reduction and geo-referencing depend on these.
- A frame definition is an entry that specifies the frame name, its family (inertial,
  earth_fixed, body, orbital, instrument, topocentric, structural), and which applicability
  domain it serves. Definitions are typically collected in a coordinate-system register
  (part of the interface control document or mission analysis baseline).

## Workflow

1. Collect the project's coordinate-system register — the list of named frames with their
   family and the domain(s) each frame serves. If no register exists, create one from the
   interface control documents, mission analysis reports, and verification test plans.
2. For each of the five required domains, identify which frames in the register are assigned
   to it. A frame with an unrecognised domain label is a data-quality error; reject it
   before proceeding.
3. Validate each frame entry: non-empty name, family drawn from the recognised set
   (inertial, earth_fixed, body, orbital, instrument, topocentric, structural), and domain
   drawn from the five required domains. Raise a finding for every validation failure.
4. Check for duplicate frame names across the register; a name collision is a configuration
   error that must be resolved before the applicability check can proceed.
5. For each domain, compare the set of frame families present against the minimum required
   for that domain. Record a finding for every missing family; a domain with no frames at
   all is an immediate non-compliance.
6. Aggregate the findings per domain. A domain is covered only when all required families
   are present and no validation errors apply to its frames. The overall assessment passes
   only when all five domains are covered and the global duplicate check is clean.
7. Report covered domains, missing domains, and each finding with its domain tag and
   severity. Hand the report to the responsible systems engineer for resolution before
   the next project review.

## Pitfalls

- Treating a domain with at least one frame of any type as "covered" — coverage requires
  the specific frame families listed for that domain, not just any frame. A body frame alone
  does not satisfy operations, which needs inertial, Earth-fixed, and orbital families.
- Sharing the same frame name across domains without resolving the collision — duplicate
  names create ambiguity in interface control documents and must be resolved to unique names
  (e.g. by appending a domain suffix) before the register is used for analysis.
- Deferring the data-processing domain to post-launch — §5.3.1 applies to the full
  lifecycle; an instrument boresight frame must be defined and registered before verification
  testing, not retrofitted during commissioning.
- Accepting a topocentric or orbital frame as a substitute for an inertial frame — each
  family serves a distinct role in the standard's hierarchy; the presence of an orbital
  frame does not fulfil the inertial-frame requirement for the operations domain.

## Behavior contract (gate 3)

The frame-validation, domain-coverage, and completeness-gate logic is exercised by the
gate 3 contract test: scripts/test_e1009_applicability.py against
scripts/e1009_applicability_logic.py (stdlib unittest, offline). Run:

    python3 scripts/test_e1009_applicability.py

## Compliance

- ECSS standards are freely downloadable from ESA; content is paraphrased per
  standards-map.yaml — no verbatim standard text is reproduced.
- compliance: STANDARDS-REF, gated: false.
