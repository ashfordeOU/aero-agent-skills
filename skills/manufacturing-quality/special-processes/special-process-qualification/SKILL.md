---
name: special-process-qualification
description: "Use when a special process must be qualified rather than inspected, when a process change triggers requalification, or when preparing for NADCAP accreditation or AS9100 production control. Assess special process qualification in aerospace manufacturing: determine whether a welding, heat treatment, NDT, surface finishing, or composites process stays qualified under a proposed change by classifying the change type (parameter, equipment, personnel, time interval) against the qualified envelope and the process qualification record, and build or validate the record checklist of parameters with ranges, variables, qualification date, and validity. Trigger: special process, qualification, requalification, process qualification record, NADCAP, heat treat, welding, process control."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
  - id: nas-410
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: special-processes
  tags: [special, process, qualification, requalification, pqr, nadcap, welding, heat, treatment, ndt, surface, finishing, composites, process-control]
  version: 0.1.0
  author: Aero Agent Skills
---

# Special Process Qualification (manufacturing-quality/special-processes/special-process-qualification)

Use when the task is deciding whether a special process in aerospace
manufacturing may keep running: welding, heat treatment,
non-destructive testing (NDT), surface finishing, and composites
processing are qualified rather than inspected, so control moves to
the process parameters, equipment, personnel, and validity interval
recorded in the process qualification record (PQR). Any change outside
that envelope is a requalification trigger.

## Domain quick reference

- Special processes: welding, heat treatment, NDT, surface finishing,
  composites processing.
- Why qualified, not inspected: the product result cannot be fully
  verified by inspection alone (verification may be destructive,
  cost-prohibitive, or sample-based), so the qualification pins the
  process itself: parameters with ranges, variables, equipment,
  personnel, and validity.
- Process qualification record (PQR): process id, parameters with
  qualified ranges, process variables, qualification date, validity.
  Module contract: REQUIRED_FIELDS and build_record_checklist().
- Change types and verdicts (assess_change()): parameter in-range
  stays qualified, parameter out-of-range is requalify-required;
  equipment change is requalify-required; personnel change is
  requalify-required; time-interval past validity is
  requalify-required.
- Requalification triggers: parameter change outside the qualified
  range, equipment change, personnel change, interval expiry.
- Range check (range_status()): lo <= value <= hi is in-range,
  boundaries inclusive; an out-of-range parameter folds into
  requalify-required.
- NADCAP context: NADCAP is the PRI-run accreditation program that
  audits special processes against industry specifications; it is an
  external attestation of a facility, not a substitute for the
  organization's own PQR and requalification control.
- AS9100 production control link: special process control is part of
  production control; NDT personnel qualification follows NAS 410
  level certification practice (training, experience, examination),
  summarized here, not reproduced.

## Workflow

1. Identify the special process and its process qualification record:
   process id, parameters with qualified ranges, variables,
   qualification date, and validity.
2. Classify the proposed change type: parameter, equipment, personnel,
   or time-interval.
3. For a parameter change, compare the proposed value against the
   qualified range with range_status(value, qualified_range); an
   out-of-range verdict is a requalification trigger.
4. Call assess_change(change_type, value=..., qualified_range=...,
   elapsed_days=..., validity_days=...) for the qualification verdict:
   qualified or requalify-required.
5. When requalification is required, re-qualify (re-run the process,
   capture results, update the record) and rebuild the PQR with
   build_record_checklist(process_id, parameters, variables,
   qualification_date, validity); validate_record() flags any missing
   field.
6. Validate inputs first: an unknown change type, a missing or
   malformed qualified range, non-numeric values or days, and
   malformed record fields raise ValueError instead of returning a
   silent verdict.

## Pitfalls

- Confusion with ndt-method-selection: choosing an NDT method
  (ultrasonic vs eddy current vs penetrant) is not qualifying the NDT
  process. Method selection picks the technique for a defect class;
  special process qualification governs whether the chosen process may
  run and what change re-triggers control. NDT method selection feeds
  inspection planning; NDT as a special process is itself qualified.
- Confusion with ultrasonic-inspection: performing and evaluating a UT
  inspection is the ultrasonic-inspection leaf. A UT process change
  (probe, frequency, scan plan, couplant) is an equipment or parameter
  change here and triggers requalification of the NDT special process.
- Confusion with nonconformance-control: a nonconforming part is
  dispositioned (repair, rework, scrap); a process change is
  requalified. Finding a nonconformance does not re-qualify the
  process, and requalification is not a disposition.
- Confusion with statistical-process-control: SPC monitors variation
  of a running process against statistical control limits. Control
  limits are not qualification limits: inside SPC limits does not mean
  inside the qualified parameter range, and SPC does not replace
  requalification on equipment or personnel change.
- Confusion with supplier-control: supplier control governs external
  providers and their approval. NADCAP accreditation is an external
  attestation, but the organization that runs the process still owns
  the PQR and requalification decision; sending a special process to a
  supplier transfers the run, not the obligation.
- Interval expiry vs repeat run: the same parameter value inside the
  validity interval stays qualified; the same run after interval
  expiry is requalify-required. Expiry is checked against the
  qualification date, not against the last run.
- Personnel change breadth: any change in qualified personnel is a
  trigger, including an NDT operator level change under NAS 410
  certification, even when parameters and equipment are untouched.
- Boundary reading: the qualified range is inclusive at both ends; a
  value exactly on the bound is in-range, and only a value strictly
  outside is a trigger.

## Behavior contract (gate 3)

The qualification decision model is exercised by the gate 3 contract
test: scripts/test_special_process_qualification_logic.py against
scripts/special_process_qualification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_special_process_qualification_logic.py

## Compliance

- Standards referenced, not reproduced: AS9100 clause 8.5.1.3 frames
  special process control within production control; NAS 410 frames
  NDT personnel qualification. Both are summarized context only,
  summary-not-copy per standards-map.yaml.
- NADCAP is an accreditation program, not a standards-map entry;
  described contextually, no proprietary text reproduced.
- compliance: STANDARDS-REF, gated: false.
