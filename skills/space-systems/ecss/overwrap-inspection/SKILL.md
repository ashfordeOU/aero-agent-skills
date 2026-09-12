---
name: overwrap-inspection
description: "Use when assess composite overwrap integrity per ECSS-E-ST-32C clause
  5.7: select the non-destructive testing method appropriate to the detected anomaly
  type and overwrap material (CFRP, GFRP, aramid), evaluate inspection coverage against
  the required threshold, categorize each defect as acceptable, monitor, or rejectable
  using established size criteria, and determine the overall inspection outcome (pass,
  conditional-pass, fail, or incomplete). Apply visual damage tolerance evaluation
  to surface anomalies before committing to invasive NDT. Trigger: ecss, e-st-32-structures-scope,
  overwrap-inspection, composite-overwrap, ndt, vdt, delamination, void."
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
  tags: [ecss, e-st-32-structures-scope, overwrap-inspection, composite-overwrap, ndt, vdt, delamination, void]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Composite Overwrap Inspection (space-systems/ecss/overwrap-inspection)

Use when the task is to assess the integrity of a composite overwrap on a
spacecraft pressure vessel or structure per ECSS-E-ST-32C clause 5.7 —
selecting the non-destructive testing (NDT) method for each detected anomaly,
applying visual damage tolerance (VDT) criteria to surface findings, and
producing an inspection verdict.

## Domain quick reference

- Clause 5.7 requires that composite overwraps on pressure vessels and
  structural elements be inspected using methods suited to the anomaly type
  and overwrap material. Accepted overwrap materials are carbon-fibre
  reinforced polymer (CFRP), glass-fibre reinforced polymer (GFRP), and
  aramid-fibre composites; the NDT method matrix is material-specific.
- Anomaly types addressed: voids (internal pores from fabrication), delaminations
  (inter-ply separations), surface scratches, fibre breakage, and inclusions
  (foreign matter entrapped during lay-up). Each type is categorized into one
  of three severity bands — acceptable (no action required), monitor (re-inspect
  at next opportunity), or rejectable (remove from service pending disposition) —
  based on a size threshold specific to that type.
- NDT methods in scope: ultrasonic testing (UT), radiography (X-ray), active
  thermography (AT), visual inspection (VI), and acoustic emission (AE). Method
  selection is driven by the combination of defect type and overwrap material;
  surface anomalies are evaluated by VDT first, before committing to volumetric
  NDT.
- Inspection coverage is a mandatory metric: the ratio of inspected area to
  total overwrap area must reach or exceed 95 % before an inspection can yield
  a pass or fail verdict; below that threshold the result is "incomplete" and
  additional coverage is required.

## Workflow

1. Identify every detected anomaly on the overwrap and record its type and
   maximum linear dimension in millimetres. Reject any anomaly whose type is
   not in the recognized set before it enters the sizing assessment; an
   unrecognized anomaly type requires disposition by the responsible structures
   engineer before proceeding.
2. For each surface anomaly (scratch, visible fibre breakage), apply visual
   damage tolerance: compare against the VDT acceptance limits for the
   overwrap material. Anomalies within VDT limits are acceptable without
   further volumetric NDT; anomalies beyond the VDT limit escalate to
   volumetric NDT in the next step.
3. For each volumetric or escalated anomaly, consult the NDT method matrix
   (defect type × overwrap material) to select the recommended method or
   methods. Document the method chosen and the rationale when deviating from
   the matrix recommendation.
4. Categorize each anomaly using the size-based thresholds for its type:
   within the acceptable limit → acceptable; between acceptable and monitor
   limits → monitor; above the monitor limit → rejectable. Aggregate the
   worst category across all anomalies on the same overwrap.
5. Compute inspection coverage as (inspected area / total overwrap area) × 100.
   If coverage is below 95 %, return an "incomplete" verdict regardless of
   anomaly findings and request additional inspection to close the gap.
6. Determine the overall inspection verdict: pass (all anomalies acceptable,
   coverage adequate), conditional-pass (worst category is monitor, coverage
   adequate), fail (any rejectable anomaly, coverage adequate), or incomplete
   (coverage below threshold). A fail requires a formal disposition record
   before the component may be used.

## Pitfalls

- Applying volumetric NDT to every finding without first screening surface
  anomalies by VDT — VDT is the first gate for surface indications and avoids
  unnecessary intrusive inspection of acceptable scratches or marks.
- Using an NDT method from outside the recommended matrix for the overwrap
  material without documented justification — method mismatch can leave
  characteristic defect types undetected in that material system.
- Treating an incomplete coverage result as a pass because no rejectable
  anomaly was found in the inspected region — uninspected area carries unknown
  risk, so a coverage shortfall is itself a non-conformance.
- Combining anomalies of different types into a single worst-size figure and
  applying a single threshold — each defect type has its own acceptance limits
  and must be assessed independently before aggregating the category verdict.
- Failing to escalate an unrecognized anomaly type to the structures engineer
  and instead applying the nearest known type's limits — limits are specific
  to each anomaly morphology and are not interchangeable.

## Behavior contract (gate 3)

The NDT method selection, defect categorization, coverage assessment, and
inspection result logic are exercised by the gate 3 contract test:
scripts/test_overwrap_inspection.py against scripts/overwrap_inspection_logic.py
(stdlib unittest, offline). Run:

    python3 scripts/test_overwrap_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
