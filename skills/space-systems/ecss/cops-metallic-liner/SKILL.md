---
name: cops-metallic-liner
description: "Use when assess the structural response of a COPS (Composite Overwrapped Pressure Structure) with metallic liner under ECSS-E-ST-32C §4.4.3: compute the hoop strain shared between the liner and composite overwrap via the compatibility condition, determine the stress state in each component at design pressure, check the liner against yielding, verify the composite against its hoop allowable, account for ring stiffener contributions to shell stiffness, and confirm the burst pressure margin satisfies the required factor of safety. Trigger: ecss, e-st-32-structures-scope, cops, composite-overwrapped-pressure-structure, metallic-liner, stiffened-shell, liner-interaction, burst-pressure, load-sharing."
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
  tags: [ecss, e-st-32-structures-scope, cops, composite-overwrapped-pressure-structure, metallic-liner, stiffened-shell, liner-interaction, burst-pressure, load-sharing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — COPS with Metallic Liner (space-systems/ecss/cops-metallic-liner)

Use when the task is the structural verification of a Composite Overwrapped
Pressure Structure with a metallic liner under ECSS-E-ST-32C §4.4.3 —
computing the load shared between liner and composite overwrap, checking
stress margins in each component, accounting for ring stiffeners, and
confirming burst pressure compliance.

## Domain quick reference

- A COPS with metallic liner consists of a thin metallic liner overwound
  with a composite laminate (the overWrap). The liner provides leak
  tightness; the composite carries the structural hoop load. Ring stiffeners,
  when present, are smeared into the shell as an effective additional
  stiffness contribution.
- Liner and composite share the same hoop strain at their interface because
  the two layers are bonded. This compatibility condition determines how the
  internal pressure load is apportioned: hoop strain ε_h = P·r / (E_l·t_l +
  E_c·t_c), where subscripts l and c denote liner and composite respectively
  and r is the inner radius.
- The metallic liner may yield at design pressure — this is often by intent
  in a metallic-liner COPS, where the liner is sized to yield on first
  pressurisation and the composite carries the bulk of the hoop load at
  operating pressure. The assessment records whether yielding occurs and
  whether it is within the design intent.
- Burst pressure is estimated from the combined hoop capacity of liner
  (at yield stress) and composite (at allowable): P_burst = (σ_yl·t_l +
  σ_allow_c·t_c) / r. The burst margin of safety is P_burst / (P_design · FoS) − 1.
- Ring stiffeners increase the effective axial stiffness of the shell. Each
  stiffener ring is smeared as K_s = E_s·A_s / spacing [N/m], which feeds
  into stability and dynamic response checks beyond this leaf's scope.

## Workflow

1. Gather the geometry (inner radius, liner wall thickness, composite
   overwrap thickness) and material properties (liner modulus, liner yield
   stress, composite hoop modulus, composite hoop allowable). Record the
   ring stiffener cross-section area, material modulus, and spacing; set
   area to zero when no stiffeners are present.
2. Compute the common hoop strain using the compatibility condition:
   ε_h = P_design · r / (E_l·t_l + E_c·t_c). Reject inputs with non-positive
   dimensions or moduli before entering this step.
3. Compute the hoop stress in the liner (σ_l = E_l · ε_h) and in the
   composite (σ_c = E_c · ε_h) at design pressure.
4. Compare σ_l against the liner yield stress. Record whether the liner has
   yielded and the yield margin of safety. A yielded liner at design pressure
   is a finding to document; it does not automatically fail the structure if
   the burst margin is met.
5. Compare σ_c against the composite hoop allowable. A negative composite
   margin is a structural finding requiring redesign or allowable revision.
6. If ring stiffeners are present, compute the smeared axial stiffness
   K_s = E_s · A_s / spacing and record it for use in stability and dynamics
   checks.
7. Estimate burst pressure P_burst = (σ_yl·t_l + σ_allow_c·t_c) / r and
   compute the burst margin MoS = P_burst / (P_design · FoS) − 1. Flag any
   negative burst margin as a critical finding.
8. Report the compliance status: the structure meets the §4.4.3 requirements
   when the composite margin is non-negative and the burst margin is
   non-negative. Liner yielding at design pressure must be declared but does
   not block compliance when both of the above conditions are satisfied.

## Pitfalls

- Applying pressure load only to the liner or only to the composite without
  enforcing hoop-strain compatibility. The two layers must share the same
  circumferential strain at their bond line; treating them as independent
  vessels overstates the stress in the weaker layer.
- Treating liner yield at design pressure as an automatic failure. In a
  metallic-liner COPS the liner is frequently designed to yield intentionally;
  the compliance check is the burst margin, not whether the liner remains
  elastic at design pressure.
- Using the composite ultimate stress as the burst allowable without checking
  that this value includes the appropriate knockdown for open-hole,
  temperature, and moisture effects. An un-knocked-down allowable produces an
  unconservative burst pressure estimate.
- Omitting stiffener contribution when stiffeners are physically present.
  Stiffeners increase shell stiffness and alter the buckling margin; ignoring
  them understates the structure's resistance to instability but may also
  shift load in ways that matter for local stress.
- Setting the burst factor of safety below the programme-required value.
  ECSS-E-ST-32C §4.4.3 and the applicable pressure vessel safety requirements
  define the minimum burst FoS; the value must be confirmed against the
  applicable safety standard before running the margin check.

## Behavior contract (gate 3)

The hoop-strain compatibility, liner yield, composite stress, stiffener
smearing, and burst margin logic is exercised by the gate 3 contract test:
scripts/test_cops_metallic_liner.py against
scripts/cops_metallic_liner_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_cops_metallic_liner.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
