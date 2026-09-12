---
name: e1024-ref-data
description: "Use when define the interface reference data list for a space system
  development project under ECSS-E-ST-10-24C Annex E: identify each interface type
  (electrical, mechanical, thermal, data, RF, optical, fluid, pyrotechnic), specify
  typical parameters with measurement units and value ranges, assign a format token
  per parameter entry, verify that every record contains all required fields, and
  group entries by interface type to produce a structured reference table. Apply
  during ICD development, interface requirement capture, or compliance review of
  interface documentation. Trigger: ecss, e-st-10-system-scope, e-st-10-24c,
  interface-management, icd, interface-reference-data, parameter-list, units,
  formats, interface-types."
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
  tags: [ecss, e-st-10-system-scope, e-st-10-24c, interface-management, icd, interface-reference-data, parameter-list, units, formats]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Interface Management — Interface Reference Data (space-systems/ecss/e1024-ref-data)

Use when the task is defining the interface reference data list for a space
system project per ECSS-E-ST-10-24C Annex E (informative): determining the
canonical parameter set per interface type, assigning units and format tokens,
and verifying each parameter record is complete before aggregating into a
structured reference table used as the basis for Interface Control Documents.

## Domain quick reference

- Annex E of ECSS-E-ST-10-24C defines a reference set of typical interface
  parameters, their measurement units, acceptable formats, and value ranges,
  grouped by interface type. The annex is informative; projects may extend the
  parameter set but must maintain structural completeness.
- Eight interface types are recognised: electrical (voltage, current, power,
  impedance), mechanical (mass, dimensions, torque), thermal (temperature range,
  conductance, dissipation), data (rate, protocol, frame structure), RF
  (frequency, power, polarisation), optical (wavelength, aperture, field of
  view), fluid (pressure, flow rate), and pyrotechnic (firing current, voltage,
  timing). Each type has its own accepted unit set; a unit from one type's set
  is not valid for another type's parameters.
- Every parameter record requires five fields: interface_type, parameter_name,
  unit, format, and value_range. A record with any field blank or absent is
  incomplete and must be resolved before the reference table is considered ready
  for ICD attachment.
- Format tokens are drawn from a fixed vocabulary: float, int, enum, string,
  bool, hex, binary. Each token may be followed by a bracketed range or
  enumeration to tighten the constraint; an unrecognised token blocks downstream
  parsing.

## Workflow

1. Inventory all interfaces in the project and, for each one, identify its type
   from the canonical set of eight. Reject any unrecognised type before the
   record enters the reference table — the type drives unit and format
   validation in every subsequent step.
2. For each interface type, enumerate the parameters that must be documented.
   Use the Annex E reference set as the starting point: electrical parameters
   include bus voltage, current limit, inrush current, impedance, and power;
   mechanical parameters include mass, envelope dimensions, bolt torque, and
   fundamental frequency; thermal parameters include operating temperature range,
   maximum allowable power dissipation, and interface thermal conductance; data
   parameters include nominal data rate, protocol identifier, and frame or
   packet size; RF parameters include centre frequency, transmit power, and
   polarisation sense; optical parameters include centre wavelength, aperture
   diameter, and field of view; fluid parameters include nominal supply pressure
   and maximum flow rate; pyrotechnic parameters include no-fire current, all-fire
   current, and pulse duration.
3. For each parameter, select the measurement unit from the accepted unit set for
   that interface type. Flag any unit that does not belong to the type's set —
   the presence of a unit from another type's set typically indicates a copy
   error in the ICD row.
4. Assign a format token (float, int, enum, string, bool, hex, binary) to each
   parameter and append the value range or enumeration. Flag any token not in the
   accepted vocabulary; do not infer or substitute a non-standard token.
5. Verify that every parameter record contains all five required fields with
   non-blank values. Collect all findings before returning results; do not stop
   on the first missing field, as a batch view of incomplete records is more
   actionable than a one-at-a-time report.
6. Group validated records by interface type to produce the reference table.
   Records with unresolvable type errors are held in a separate error bucket;
   the table is not ready for ICD attachment until the error bucket is empty.

## Pitfalls

- Assigning a unit from a different interface type's accepted set (e.g. kg for
  an electrical parameter) — units are type-specific and cross-type assignment
  is a data error, not a conservative choice.
- Using a descriptive token such as "number" or "real" instead of "float" or
  "int" — the format token vocabulary is fixed; informal synonyms are not
  substitutes and will fail downstream validation.
- Leaving value_range blank and treating the record as structurally complete —
  an unset range means the constraint was never captured; the record must be
  resolved before the table can be used in an ICD.
- Treating Annex E as normative — the annex is informative; it provides a
  representative parameter set that projects extend or restrict. The validation
  logic (required fields, accepted units, accepted format tokens) applies
  regardless of whether a given parameter appears in the Annex E list.

## Behavior contract (gate 3)

The interface-type validation, unit-set checking, format-token checking,
required-field verification, and table-grouping logic are exercised by the
gate 3 contract test: scripts/test_e1024_ref_data.py against
scripts/e1024_ref_data_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1024_ref_data.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
