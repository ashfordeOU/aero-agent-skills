---
name: e2006-solar-array-arc-general-requirement
description: "Use when determine whether a photovoltaic solar-array design triggers the arc-characterization obligation of ECSS-E-ST-20-06C clause 7.2.2: categorize every exposed array surface element as conductive or dielectric, check each one against the surface-grounding provisions (bond-path resistance to structure, conductive-coating surface-resistivity, ungrounded dielectric exposed-area allowance), compute the triple-junction primary-arc inception threshold from coverglass-thickness, interconnect-gap and surface-temperature, compare it with the worst-case dielectric-to-conductor differential-potential, estimate the primary-arc count over the exposure period, and derive the characterization scope a non-conforming array must carry. Trigger: ecss, e-st-20-06c, solar-array-arcing, primary-arc-inception, triple-junction, array-surface-grounding, bond-path-resistance, arc-characterization-scope, electrostatic-discharge-onset, coverglass-interconnect-gap."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-solar-array-arc-general-requirement, e-st-20-06c, solar-array-arcing, primary-arc-inception, triple-junction, array-surface-grounding, arc-characterization-scope, electrostatic-discharge-onset]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Solar-Array Arc General Requirement (space-systems/ecss/e2006-solar-array-arc-general-requirement)

Use when the task is the clause 7.2.2 obligation of ECSS-E-ST-20-06C: an
exposed photovoltaic array that does not satisfy the surface-grounding
provisions cannot be declared acceptable on inspection alone, it has to be
supported by an arc-characterization analysis. This leaf decides whether
that obligation is triggered, and states what the analysis has to contain.

## Domain quick reference

- Clause 7.2.2 is a conditional requirement, not a design rule. It is read
  in two steps: first establish whether the array surfaces satisfy the
  surface-grounding provisions, then, only for an array that does not,
  require an arc-characterization analysis of the exposed photovoltaic
  surfaces. An array that satisfies the provisions discharges the clause by
  inspection of the grounding evidence.
- Every exposed element on the array front face is categorized once as
  conductive (interconnect, busbar, substrate facesheet, hinge fitting) or
  dielectric (coverglass, cell edge, adhesive fillet, harness insulation,
  blanket film). The provision each one has to meet depends on that
  category: a conductive element needs a bond path to structure below the
  resistance limit, a dielectric element is acceptable either because a
  conductive coating bleeds it to structure through such a bond path, or
  because its ungrounded exposed area stays inside the allowance. A
  conductive element with no bond path at all is a floating conductor and
  fails outright.
- The physical driver behind the clause is the triple junction where
  coverglass, interconnect and vacuum meet. Its primary-arc inception
  threshold rises with coverglass thickness and with the cell-to-cell gap,
  and falls as the surface cools. Inception is reached when the worst-case
  dielectric-to-conductor differential-potential, including the string bias
  seen by the conductor, reaches that threshold.
- The characterization scope is assembled from the drivers that fired.
  Grounding deficiency adds a justification item; reached inception adds a
  primary-arc rate prediction and a discharge-energy budget; a string
  voltage at or above the sustained-arc review level adds a sustained-arc
  susceptibility review, which is where this leaf hands over to the
  secondary-arc clauses.

## Workflow

1. Inventory every exposed array surface element with its exposed area and,
   where it exists, the series segments of its bond path to structure and
   its coating surface-resistivity. Reject an unrecognized element type, a
   duplicated element identifier or a non-positive exposed area before the
   assessment starts.
2. Categorize each element as conductive or dielectric and apply the
   matching grounding provision. Sum the bond-path segments rather than
   trusting a single quoted resistance, and treat a summed value that lands
   a few bits above the limit as at the limit.
3. Aggregate the per-element findings into an array-level verdict and keep
   the identifiers of the deficient elements; they are the evidence the
   analysis has to address one by one.
4. Compute the triple-junction inception threshold from coverglass
   thickness, interconnect gap and the coldest surface temperature in the
   mission profile, clamped at the model floor.
5. Compute the worst-case differential-potential between the dielectric
   surface and the adjacent conductor, including the string bias, and
   compare it with the threshold. Treat a differential that equals the
   threshold within representation error as having reached inception.
6. Where inception is reached, predict the primary-arc count over the
   exposure period from the overdrive above threshold and the exposed
   triple-junction length.
7. Assemble the characterization scope from the drivers that fired. The
   array is clause-7.2.2 compliant without analysis only when the grounding
   provisions are satisfied and inception is not reached.

## Pitfalls

- Reading the clause as a blanket requirement for every array. It fires on
  the grounding condition; an array that meets the provisions closes it on
  grounding evidence, and raising an analysis anyway buries the arrays that
  genuinely need one.
- Accepting a quoted end-to-end bond resistance instead of summing the
  series segments. A hinge, a harness run and a connector each contribute,
  and the path that matters is the one the charge actually takes.
- Treating a large coverglass area as safe because it is "only glass". An
  ungrounded dielectric beyond the area allowance is exactly the surface
  that holds the differential-potential which drives the triple junction.
- Evaluating inception at room temperature. The threshold falls on a cold
  eclipse-exit surface, so the assessment has to use the coldest case in
  the mission profile, not the qualification ambient.
- Forgetting the string bias when forming the differential-potential. The
  conductor sits at its local potential plus the string bias, and dropping
  the bias understates the differential on every string but the first.
- Declaring an at-threshold case as a pass because a summed potential
  printed a hair under the threshold. The representation error belongs in
  the comparison, never in the engineering limit.

## Behavior contract (gate 3)

The grounding-provision, inception-threshold, differential-potential,
arc-count and characterization-scope logic is exercised by the gate 3
contract test: scripts/test_e2006_solar_array_arc_general_requirement.py
against scripts/e2006_solar_array_arc_general_requirement_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_solar_array_arc_general_requirement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
