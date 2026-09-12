---
name: factors-of-safety-and-scatter
description: "Use when apply structural factors of safety and scatter factors per ECSS-E-ST-32C clauses 4.5.17–4.5.18: select the appropriate ultimate and yield factor of safety by material category (metallic ductile, metallic brittle, composite, or bonded), compute the design ultimate and yield loads from the design limit load, then derive the allowable design fatigue life by dividing the analysis life by the applicable scatter factor (inspectable location: 2, uninspectable location: 4). Verify a non-negative margin of safety for both the static strength and fatigue loading paths. Trigger: ecss, e-st-32-structures-scope, factors-of-safety, scatter-factor, design-limit-load, design-ultimate-load, fatigue-life, margin-of-safety, structural-analysis."
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
  tags: [ecss, e-st-32-structures-scope, factors-of-safety, scatter-factor, design-limit-load, design-ultimate-load, fatigue-life, margin-of-safety, structural-analysis]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structural Engineering — Factors of Safety and Scatter (space-systems/ecss/factors-of-safety-and-scatter)

Use when the task is applying structural factors of safety and scatter factors
under ECSS-E-ST-32C clauses 4.5.17–4.5.18 — selecting and applying the
correct ultimate and yield factors to the design limit load, deriving design
ultimate and yield loads, and computing the allowable fatigue life from the
analysis life via the appropriate scatter factor for the inspection regime.

## Domain quick reference

- **Design Limit Load (DLL)** is the baseline structural load from which all
  design loads are derived. It already incorporates uncertainty factors from
  the loads cycle (see the limit-load-to-dll-cascade leaf). Clauses 4.5.17–4.5.18
  take DLL as input and produce design loads and allowable lives.
- **Factor of Safety (FOS)** is applied to DLL to obtain the design load for
  each failure mode. Two factors apply:
  - *Ultimate FOS*: multiplies DLL to give the Design Ultimate Load (DUL),
    used to verify that no catastrophic failure occurs. The value depends on
    material category: 1.25 for metallic ductile materials, 1.50 for metallic
    brittle materials, 1.40 for composites, 1.50 for bonded structures.
    (ECSS-E-ST-32C Rev.2 clause 4.5.17 — representative values; project
    tailoring can raise but not lower these.)
  - *Yield FOS*: multiplies DLL to give the Design Yield Load (DYL), used to
    verify that no permanent deformation occurs. The value is 1.00 for metallic
    ductile materials and 1.10 for metallic brittle, composite, and bonded
    categories.
- **Scatter factor** applies to fatigue analysis (clause 4.5.18). The analysis
  predicts a mean fatigue life; the scatter factor divides that life to derive
  the allowable design life, accounting for material variability. Locations
  accessible for in-service inspection use a scatter factor of 2; uninspectable
  locations use 4. The lower allowable life from an uninspectable location must
  be met by the design mission life.
- **Margin of Safety (MS)** is the standard structural compliance metric:
  MS = (allowable / applied) − 1. A result ≥ 0 is a pass; a negative MS is a
  finding requiring design action.

## Workflow

1. Confirm the DLL for each load case is finalised and documented before
   beginning FOS application. A DLL that is still under revision propagates
   uncertainty into every downstream design load.
2. Determine the material category of each structural element: metallic ductile,
   metallic brittle, composite, or bonded. Reject an element with no recorded
   material category; it cannot be assigned a factor of safety without one.
3. Apply the ultimate FOS for the category to the DLL to obtain the DUL. Apply
   the yield FOS to obtain the DYL. Record both derived loads against the element
   and load case.
4. Check that the element allowable (strength or stiffness limit from the
   material allowables database) is compared against DUL for ultimate checks
   and DYL for yield checks. Do not compare an ultimate allowable against a
   yield load or vice versa.
5. Compute the margin of safety for each limit state: MS = allowable / applied − 1.
   An MS below zero is a finding; flag it with the element identifier, load case,
   and limit state (ultimate or yield).
6. For each fatigue-critical location, confirm whether the location is accessible
   for inspection over the mission lifetime. Select the scatter factor accordingly
   (2 or 4) and divide the analysis fatigue life to obtain the allowable life.
7. Verify that the mission design life does not exceed the allowable fatigue life.
   If it does, the location fails the scatter-factor check; record the deficit.
8. Aggregate all MS and fatigue findings per element. An element is structurally
   compliant only when all MS ≥ 0 and the allowable fatigue life ≥ mission life.

## Pitfalls

- Applying FOS to a load that is not the DLL (e.g., applying it to the limit
  load before uncertainty factors have been incorporated) understates the design
  load and produces a non-conservative result.
- Using a single FOS for all materials regardless of category — the values differ
  materially between metallic ductile and composite structures; collapsing them
  into a single figure is non-compliant.
- Treating a scatter factor of 2 as universally applicable — it is valid only
  for inspectable locations. An uninspectable location at scatter factor 2
  instead of 4 doubles the apparent allowable life and can mask a fatigue
  finding entirely.
- Mixing ultimate allowables with yield loads or vice versa in the MS
  calculation — the compliance check must pair ultimate loads with ultimate
  allowables and yield loads with yield allowables.
- Recording MS = 0 as "passing with margin" — it is the minimum acceptable
  value, not a comfortable reserve; any uncertainty in the analysis or allowable
  can flip it negative.

## Behavior contract (gate 3)

The FOS application, scatter-factor application, and margin-of-safety logic is
exercised by the gate 3 contract test:
scripts/test_factors_of_safety_and_scatter.py against
scripts/factors_of_safety_and_scatter_logic.py (stdlib unittest, offline). Run:

```
python3 scripts/test_factors_of_safety_and_scatter.py
```

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
- Reference anchor: ECSS-E-ST-32C Rev.2 (2019) clauses 4.5.17–4.5.18.
