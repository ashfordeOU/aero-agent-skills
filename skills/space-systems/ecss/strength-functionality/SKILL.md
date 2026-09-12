---
name: strength-functionality
description: "Use when verify strength functionality requirements per
  ECSS-E-ST-32C clause 4.3.2 across all levels of assembly: confirm no
  yielding occurs at the Design Yield Load (DYL) and no failure at the
  Design Ultimate Load (DUL). Scale limit loads by yield and ultimate factors
  of safety, evaluate multiaxial stress states with the von Mises criterion,
  and compute margins of safety for yield and ultimate thresholds at each
  assembly level (component, subsystem, system). Flag any level where a
  margin falls below zero. Applicable to linear and nonlinear finite element
  analyses. Trigger: ecss, e-st-32-structures-scope, strength-functionality,
  margin-of-safety, design-yield-load, design-ultimate-load, von-mises,
  factors-of-safety."
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
  tags: [ecss, e-st-32-structures-scope, strength-functionality, margin-of-safety, design-yield-load, design-ultimate-load, von-mises, factors-of-safety]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Strength Functionality (space-systems/ecss/strength-functionality)

Use when the task is verifying that a structural design satisfies the
strength functionality requirements of ECSS-E-ST-32C clause 4.3.2 —
confirming no permanent deformation at the Design Yield Load and no
fracture or collapse at the Design Ultimate Load, applied at every
level of the assembly hierarchy.

## Domain quick reference

- Clause 4.3.2 establishes two load-level gates: the Design Yield Load
  (DYL) and the Design Ultimate Load (DUL). The DYL is derived from the
  limit load by applying a yield factor of safety; the DUL is derived by
  applying a higher ultimate factor of safety. Both are applied at each
  assembly level — component, subsystem, and system — not only at the top
  level.
- The no-yielding criterion at DYL requires that the equivalent stress
  at every critical location remains below the material yield strength.
  For metallic isotropic materials the multiaxial stress state is reduced
  to an equivalent scalar stress using the von Mises criterion before
  comparison against the allowable.
- The no-failure criterion at DUL requires that the equivalent stress
  remains below the material ultimate strength (or that the applied load
  remains below the section's ultimate capacity for net-section or
  fastener checks). No plastic collapse, fracture, or instability may
  occur below DUL.
- Margin of safety (MoS) is the standard reporting metric: MoS =
  (allowable / applied) − 1. A non-negative MoS is required; a negative
  MoS at either gate is a non-compliance finding regardless of the
  magnitude.
- The standard permits nonlinear analysis (material or geometric) when
  linear methods are not conservative. Nonlinear runs must still satisfy
  the same DYL and DUL thresholds and must report MoS referenced to the
  same allowables.

## Workflow

1. Identify the limit load for each load case and assembly level under
   assessment. Do not apply factors of safety to the limit load at this
   step; retain them as a separate multiplier.
2. Derive DYL and DUL by multiplying the limit load by the applicable
   yield and ultimate factors of safety respectively (per the program
   factors-of-safety document and ECSS-E-ST-32C Table 4-1 or equivalent).
3. Run the structural analysis (linear or nonlinear finite element, or
   closed-form) for each load case at both DYL and DUL. Record the peak
   equivalent stress at each critical location. For multiaxial states,
   apply the von Mises criterion to compute the equivalent scalar stress
   before comparing against the allowable.
4. Compute MoS for the yield gate: MoS_yield = (yield_strength /
   vm_stress_at_DYL) − 1. Flag any location where MoS_yield < 0.
5. Compute MoS for the ultimate gate: MoS_ultimate = (ultimate_strength /
   vm_stress_at_DUL) − 1. Flag any location where MoS_ultimate < 0.
6. Repeat steps 1–5 for every level of the assembly hierarchy that has
   been identified as a structural load path. A finding at any level is a
   non-compliance regardless of the pass/fail status at other levels.
7. Consolidate results into a strength summary table listing assembly
   level, load case, DYL, DUL, peak von Mises stress at each gate, and
   both MoS values. All entries must show MoS ≥ 0 for the design to
   satisfy clause 4.3.2.

## Pitfalls

- Applying factors of safety to the analysis input loads rather than
  deriving DYL/DUL from the limit load — factors of safety must be
  applied to the limit load, not stacked on top of an already-factored
  load, or the DUL calculation double-counts the margin.
- Checking only the system-level assembly and treating subsystem and
  component findings as bounded by the system result — clause 4.3.2
  requires independent verification at all levels; a component may fail
  its own yield criterion even when the system-level MoS is positive.
- Using maximum principal stress as the scalar for yield comparison on
  metallic ductile materials — the von Mises criterion is the appropriate
  choice for isotropic ductile metals; principal stress comparisons are
  appropriate for brittle materials where a different failure criterion
  applies.
- Reading a near-zero positive MoS as comfortable — MoS ≥ 0 is the
  binary pass criterion, but program requirements often mandate a minimum
  positive MoS (e.g. MoS ≥ 0.00) and acceptance boards may impose
  stricter limits; always verify the program-specific threshold.
- Running a linear analysis at DUL without checking whether large
  displacements or material nonlinearity change the load path — when the
  structure exhibits geometric or material softening before DUL, a linear
  analysis underestimates peak stresses and is not conservative.

## Behavior contract (gate 3)

The DYL/DUL scaling, von Mises equivalent stress, margin-of-safety, and
multi-level compliance logic is exercised by the gate 3 contract test:
scripts/test_strength_functionality.py against
scripts/strength_functionality_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_strength_functionality.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
