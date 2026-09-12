---
name: thermal-and-dimensional-stability-functionality
description: "Use when evaluate thermal-environment tolerance and dimensional stability of a spacecraft structure per ECSS-E-ST-32 clauses 4.3.7 and 4.3.13: categorize each structural component by its temperature exposure regime (operating, survival, qualification), compute thermal stresses from coefficient-of-thermal-expansion mismatch and temperature differential, compare computed stresses against material allowables, and verify dimensional changes over short-term (orbital transient), medium-term (mission phase), and long-term (mission lifetime) time horizons remain within specified tolerances. Flag any component where thermal stress exceeds the allowable or where dimensional change exceeds the stability requirement for its time horizon. Trigger: ecss, e-st-32-structures-scope, thermal-stability, dimensional-stability, thermal-stress, cte-mismatch, temperature-range, orbital-thermal-cycling, structural-allowables."
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
  tags: [ecss, e-st-32-structures-scope, thermal-stability, dimensional-stability, thermal-stress, cte-mismatch, orbital-thermal-cycling, structural-allowables]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Thermal and Dimensional Stability Functionality (space-systems/ecss/thermal-and-dimensional-stability-functionality)

Use when the task is evaluating a spacecraft structure's ability to
tolerate its thermal environment (ECSS-E-ST-32 clause 4.3.7) and to
maintain dimensional stability over short-, medium-, and long-term time
horizons (clause 4.3.13). Both requirements drive design decisions
simultaneously: the same temperature delta that induces thermal stress
also drives the dimensional change that must stay within pointing or
interface tolerances.

## Domain quick reference

- Clause 4.3.7 requires that every structural component survive the
  full temperature range it will experience — from the cold-soak
  extreme to the hot-case peak — without failure or permanent
  deformation. A qualification envelope must bracket the operating
  range by the applicable temperature margin (typically ±5 °C minimum
  for qualification above operating). Each component is categorized by
  its exposure regime: operating (routine duty cycle), survival
  (off-nominal or non-operational), and qualification (test envelope).
  The thermal stress at the governing temperature differential must
  remain below the material allowable stress at that temperature.

- Clause 4.3.13 requires demonstrating that structure-level dimensional
  changes over three time horizons remain within specified tolerances:
  short-term (orbital period transients — rapid day/night cycling that
  produces repeatable elastic dimensional excursions), medium-term
  (mission-phase changes spanning days to weeks — dominated by
  moisture release, thermal settling, and deployment kinematics), and
  long-term (full mission lifetime — driven by cumulative effects of
  thermal fatigue, creep, radiation-induced property shifts, and
  outgassing). A dimensional change is assessed against the tolerance
  assigned to that time horizon; each horizon carries its own
  requirement and must be checked independently.

- Thermal stress at a bonded or constrained interface is a function of
  the coefficient of thermal expansion (CTE) mismatch between joined
  materials, the temperature differential from the assembly reference
  temperature to the extreme case, the elastic modulus of the
  constraining member, and the degree of constraint (fully constrained
  = 1.0; partial constraint is a fraction between 0 and 1). Free
  thermal expansion (constraint = 0) produces zero stress regardless
  of CTE or delta-T.

- Dimensional change from CTE is computed as alpha × delta_T × L,
  where alpha is the effective CTE of the structural path, delta_T is
  the temperature excursion from the reference condition, and L is the
  length of the structural path. For the short-term horizon, delta_T
  is the orbital peak-to-trough swing; for medium-term, it is the
  phase-to-phase differential; for long-term, the full mission envelope
  plus the contribution of irreversible effects (estimated as a
  separate dimensional drift budget).

## Workflow

1. Inventory every structural component and joint, and categorize each
   one into its exposure regime (operating, survival, qualification).
   Reject any component with an unrecognized regime before it enters
   the assessment.

2. Confirm that the qualification temperature envelope brackets the
   operating range by at least the required qualification margin on
   both the hot and cold sides. Flag any component where the
   qualification limit is tighter than operating-plus-margin.

3. For each constrained component or bonded joint, compute the thermal
   stress: sigma = E × CTE_effective × delta_T × constraint_factor.
   Use the temperature differential from the stress-free reference
   temperature to the governing extreme (hot or cold, whichever
   produces the larger stress for the material and geometry). Compare
   sigma against the material allowable at that temperature; compute
   the margin of safety and flag any negative margin.

4. For each structural dimensional path, compute the CTE-driven
   dimensional change for each time horizon using the delta_T
   appropriate to that horizon. Add any irreversible drift budget for
   the medium- and long-term horizons. Compare the total dimensional
   change against the tolerance for that horizon; flag any exceedance.

5. Check that every flagged item has a disposition: a design change, a
   tolerance relaxation with authority, or a verified-acceptable
   justification. A component with an unresolved flag is not
   compliant.

6. Aggregate findings per component and per time horizon; the structure
   meets the thermal and dimensional stability functionality
   requirements only when all thermal-stress margins are non-negative
   and all dimensional checks pass for all three horizons.

## Pitfalls

- Applying the full qualification temperature swing as the delta_T for
  thermal stress when the actual stress-free assembly temperature is
  mid-range — the stress-free reference is not always ambient; use the
  cure or bonding temperature for adhesive joints, and the room-
  temperature assembly reference for mechanical joints unless otherwise
  defined.

- Treating a zero-constraint factor as zero stress and skipping the
  dimensional check — free thermal expansion produces no stress but
  still produces dimensional change; the two checks are independent.

- Using the same delta_T for all three dimensional stability horizons —
  the short-term horizon uses the orbital thermal swing (typically
  tens of degrees), while the long-term horizon uses the full mission
  envelope including extreme cases, which can be two to three times
  larger.

- Omitting the irreversible drift contribution from the medium- and
  long-term dimensional budgets — CTE-driven reversible change is
  recoverable between orbits, but outgassing shrinkage, radiation creep,
  and moisture release are permanent and accumulate over the mission.

- Reading a missing tolerance as a pass — an unspecified dimensional
  tolerance for a horizon means the requirement has not been captured,
  which is a finding, not an acceptance.

## Behavior contract (gate 3)

The qualification-envelope check, thermal-stress computation and
comparison, dimensional-change computation for all three time horizons,
and constraint/irreversible-drift logic are exercised by the gate 3
contract test:
scripts/test_thermal_and_dimensional_stability_functionality.py
against
scripts/thermal_and_dimensional_stability_functionality_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_thermal_and_dimensional_stability_functionality.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
