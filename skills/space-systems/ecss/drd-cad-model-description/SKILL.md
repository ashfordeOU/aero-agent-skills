---
name: drd-cad-model-description
description: "Use when validate a CAD model and drawing description document (CADMDD) for structural design delivery under ECSS-E-ST-32C Annex A: confirm the model format is an accepted exchange or native type, verify the coordinate system definition (origin, axes, handedness), check assembly tree completeness and component identification, validate drawing title block required fields, assess mass property completeness (mass, centre of gravity, inertia tensor), confirm interface definitions carry type and mating-component, and determine the overall delivery maturity and configuration status against release criteria. Trigger: ecss, e-st-32-structures-scope, cad-model, drawing-description, cadmdd, mass-properties, coordinate-system, model-delivery."
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
  tags: [ecss, e-st-32-structures-scope, cad-model, drawing-description, cadmdd, mass-properties, coordinate-system, model-delivery]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — CAD Model and Drawing Description (space-systems/ecss/drd-cad-model-description)

Use when the task is to validate a CAD Model and Drawing Description Document
(CADMDD) for structural design delivery per ECSS-E-ST-32C Annex A — checking
that every mandatory content element is present, correctly formed, and
consistent before the document is released into configuration control.

## Domain quick reference

- Annex A of ECSS-E-ST-32C defines the required content of the CADMDD: the
  model format declaration, coordinate system definition, assembly tree, drawing
  title block, mass properties record, and interface definitions.  Each element
  must be present and internally consistent for the delivery to be accepted.
- Accepted model formats are either neutral exchange formats (STEP AP214, STEP
  AP242, IGES) or identified native CAD formats (CATIA V5, CATIA V6,
  Siemens NX, Creo, SolidWorks).  A format not on this list is not a
  recognised delivery medium and must be rejected before further checks proceed.
- The coordinate system definition must state the origin, the positive X and Y
  axis directions, and the handedness (right-handed is the structural standard).
  An axis definition without handedness is ambiguous and cannot be accepted.
- The assembly tree lists every component by ID and description.  A component
  entry without an ID, or with an ID that duplicates another entry in the same
  delivery, is a structural integrity finding.
- The drawing title block must carry at minimum: document number, title,
  revision identifier, release date, originator, and approval authority.  A
  missing approval authority means the drawing has not been formally authorised.
- Mass properties (mass, centre of gravity in X/Y/Z, diagonal inertia tensor
  terms Ixx/Iyy/Izz) must all be present and non-negative.  A negative mass or
  a missing inertia term is an invalid record.
- Interface definitions must each carry an interface ID, an interface type
  (mechanical, thermal, electrical, optical, or fluid), and the mating component
  identifier.  An interface entry missing any of these three fields is incomplete.
- Model maturity must be declared as one of four recognised levels: preliminary,
  development, released, or superseded.  An undeclared or unrecognised maturity
  code means the configuration status cannot be determined.

## Workflow

1. Confirm the model format string matches an accepted exchange or native format;
   reject and stop if it does not.
2. Check the coordinate system record for the required fields (origin, x_axis,
   y_axis, handedness) and for a valid handedness value; collect any missing or
   invalid fields as findings.
3. Walk the model tree component list; flag any component without an id field and
   any component whose id duplicates an earlier entry.
4. Validate the drawing title block against the required field set; flag every
   missing field.
5. Check the mass properties record: verify all seven numeric fields are present
   and that mass_kg, ixx_kg_m2, iyy_kg_m2, and izz_kg_m2 are non-negative (the
   centre-of-gravity coordinates may be negative); flag each missing field or
   invalid value.
6. Validate the maturity level against the four recognised codes; flag an
   unrecognised or absent value.
7. For each interface definition, verify that interface_id, interface_type, and
   mating_component are all present and that interface_type is one of the five
   valid types; flag each incomplete or invalid entry.
8. Aggregate all findings by category; the CADMDD delivery is compliant only
   when every category list is empty.

## Pitfalls

- Accepting a proprietary format not on the recognised list because it opens
  correctly on the current workstation — format acceptability is a delivery
  contract requirement, not a tool capability check.
- Treating a coordinate system entry as valid when handedness is absent — a
  right-hand/left-hand ambiguity propagates silently into every subsequent
  load-path and interface geometry calculation.
- Skipping the assembly tree duplicate-ID check when the tree is generated
  automatically by the CAD tool — tools can and do produce duplicate IDs on
  copy-paste or library reuse, and a duplicate is a configuration control
  failure.
- Reading a missing approval authority as a formatting gap rather than a
  compliance finding — an unapproved drawing must not enter configuration
  control regardless of its technical content.
- Accepting a mass properties record where the inertia diagonal is omitted
  because only mass and CoG were requested by the customer — Annex A requires
  the full tensor diagonal; partial records are incomplete.

## Behavior contract (gate 3)

The format validation, coordinate system check, model tree check, title block
check, mass property check, maturity level check, interface definition check,
and aggregate compliance logic are exercised by the gate 3 contract test:
scripts/test_drd_cad_model_description.py against
scripts/drd_cad_model_description_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_drd_cad_model_description.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
