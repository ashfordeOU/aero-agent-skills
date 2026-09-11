---
name: e1006-char-cm-trace
description: "Use when auditing configuration management traceability of requirements under ECSS-E-ST-10C §8.2.3: verify each requirement carries a unique identifier, a documented source trace linking it to an originating parent requirement, standard clause, or customer specification, and an assignment to a configuration baseline. Flag requirements with missing identifiers, empty source traces, unrecognized source types, or unassigned baselines. Identify duplicate requirement identifiers across the set. A requirement achieves CM-trace compliance only when its identity, source trace, and baseline assignment are all present and valid. Trigger: ecss, e-st-10c, e-st-10-system-scope, configuration-management, cm-trace, traceability, requirements-identity, cm-baseline."
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
  tags: [ecss, e-st-10c, e-st-10-system-scope, configuration-management, cm-trace, traceability, requirements-identity, cm-baseline]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Systems Engineering — Requirements CM Traceability (space-systems/ecss/e1006-char-cm-trace)

Use when the task is the configuration management (CM) traceability audit of
requirements under ECSS-E-ST-10C §8.2.3 — confirming that every requirement
has a unique identity, a documented source trace, and an assignment to a
configuration baseline.

## Domain quick reference

- §8.2.3 requires each requirement to be individually identifiable (a unique
  ID that persists through the project lifecycle), traceable to its origin
  (parent requirement, standard clause, or customer specification), and placed
  under CM by assignment to a named baseline.
- Source trace types recognised by this leaf: **parent-req** (derived from a
  higher-level requirement), **standard** (imposed by a standard clause),
  **customer-spec** (mandated by the customer's specification), and
  **interface-req** (imposed at a system interface boundary). Any other type
  is flagged as unrecognized.
- A configuration baseline anchors the requirement to a formal CM state. A
  requirement that has not yet been assigned to a baseline is not yet under
  CM control and is flagged regardless of how well-formed its identity and
  source trace are.
- Duplicate identifiers within a requirement set violate the uniqueness
  invariant and are flagged as a set-level finding independently of each
  individual requirement's field audit.

## Workflow

1. For each requirement record, confirm the presence and non-emptiness of
   three fields: identifier (`id`), source trace (`source_type` +
   `source_ref`), and baseline assignment (`baseline`).
2. Validate the identifier: it must be a non-empty string.
3. Validate the source trace: `source_type` must be one of the four
   recognized types; `source_ref` must be a non-empty string naming the
   specific parent requirement ID, standard clause, or specification section.
4. Validate the baseline assignment: `baseline` must be a non-empty string
   naming the CM baseline.
5. After auditing each record individually, scan the full set for duplicate
   identifiers; mark every record sharing a duplicate ID as non-compliant
   with an identity finding.
6. Aggregate: a requirement is CM-trace compliant when all three checks pass
   and its ID is unique in the set. The set is compliant when every member
   is compliant and no duplicate IDs exist.

## Pitfalls

- Treating a requirement with a well-formed ID and source trace as compliant
  when its baseline field is empty — the baseline assignment is a mandatory
  CM-control attribute, not optional metadata.
- Accepting an unrecognized source type without flagging it — an arbitrary
  string in `source_type` cannot be verified against a known origination
  category and must be rejected.
- Treating an empty source reference as satisfactory because the source type
  is present — the type category alone does not constitute a trace; the
  specific reference (requirement ID, clause number, or section) is required.
- Missing the duplicate-ID check when auditing records individually — each
  individual audit sees only one record, so the uniqueness invariant must be
  enforced at the set level after individual audits complete.

## Behavior contract (gate 3)

The identity validation, source trace checking, baseline assignment checking,
individual requirement audit, and set-level audit logic are exercised by the
gate 3 contract test: scripts/test_e1006_char_cm_trace.py against
scripts/e1006_char_cm_trace_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1006_char_cm_trace.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
