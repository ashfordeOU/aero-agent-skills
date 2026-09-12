---
name: metallic-pressure-components
description: "Use when verify metallic pressure components — valves, pumps, pressure lines, fittings, and hoses — against ECSS-E-ST-32 clause 4.5.1: categorize each component by type, check proof and burst pressure margins against the maximum expected operating pressure using the applicable pressure factors, compute hoop stress and von Mises equivalent stress for cylindrical sections, evaluate ultimate-strength margins-of-safety, and confirm fatigue safe-life by applying a scatter factor of four to the demonstrated test life. Trigger: ecss, e-st-32-structures-scope, metallic-pressure-components, pressure-lines, valves, pumps, fittings, pressure-cycle-fatigue, safe-life."
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
  tags: [ecss, e-st-32-structures-scope, metallic-pressure-components, valves, pumps, pressure-lines, fittings, hoses, pressure-cycle-fatigue, safe-life]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Metallic Pressure Components (space-systems/ecss/metallic-pressure-components)

Use when the task is verifying metallic pressure components under ECSS-E-ST-32
clause 4.5.1 — covering valves, pumps, pressure lines, fittings, and hoses —
by checking pressure margins against the maximum expected operating pressure,
computing hoop and von Mises stress for cylindrical sections, evaluating
strength margins of safety, and confirming fatigue safe life.

## Domain quick reference

- Clause 4.5.1 covers five metallic pressure component (MPC) types: valves,
  pumps, pressure lines, fittings, and hoses. Each component is categorized
  into exactly one of these types before verification begins.
- Proof pressure and burst pressure requirements are applied against the
  maximum expected operating pressure (MEOP). Lines and fittings use a burst
  factor of 1.5 × MEOP; valves, pumps, and hoses use 2.0 × MEOP. The proof
  factor is 1.1 × MEOP for all component types.
- For thin-walled cylindrical sections (radius-to-thickness ratio ≥ 10), hoop
  stress is σ_h = p·r/t and axial stress is σ_a = p·r/(2t) for closed-end
  geometry. The von Mises equivalent stress combines both for the
  ultimate-strength margin of safety: MS = F_tu / (γ × σ_vm) − 1, where γ is
  the material safety factor (default 1.25). A non-negative margin is required.
- Fatigue and safe life: the demonstrated test life (pressure cycles) is
  divided by a scatter factor of 4 to obtain the safe life. The safe life must
  cover the required mission pressure cycles. A component whose safe life falls
  short of the required cycles must be re-tested, redesigned, or declared a
  fracture-critical part and subjected to the fracture control programme.

## Workflow

1. Categorize each pressure component as valve, pump, line, fitting, or hose.
   Reject any component with an unrecognized type before it enters the pressure
   verification sequence.
2. For each component, confirm the proof pressure test value satisfies
   proof ≥ 1.1 × MEOP. Record the proof ratio; flag any component below the
   threshold.
3. Determine the applicable burst factor (1.5 for lines and fittings; 2.0 for
   valves, pumps, and hoses), then confirm burst pressure ≥ factor × MEOP.
   Flag any shortfall.
4. For cylindrical sections, verify the thin-wall criterion (r/t ≥ 10), compute
   hoop and axial stress at MEOP, derive the von Mises equivalent, and
   calculate the margin of safety against the material ultimate tensile strength
   with the applicable safety factor (default 1.25). A negative margin is a
   structural finding.
5. Retrieve the fatigue test life (pressure cycles to failure or test runout).
   Divide by the scatter factor of 4 to obtain the safe life. Confirm the safe
   life exceeds the required mission pressure cycles. Record the life margin
   factor (safe life / required cycles).
6. Aggregate findings per component: a component is verified only when no
   proof, burst, strength, or fatigue finding remains open.

## Pitfalls

- Applying the burst factor of 2.0 to lines and fittings — lines and fittings
  carry a burst factor of 1.5 under clause 4.5.1; using 2.0 overstates the
  requirement without providing additional safety margin insight.
- Using the thin-wall stress formula when r/t < 10 — the thin-wall hoop stress
  equation is not valid for thick sections; use the Lamé thick-wall formula or
  a finite-element model for sections below the r/t = 10 threshold.
- Conflating proof pressure with burst pressure — proof is a non-destructive
  structural integrity check; burst is the pressure at which the component must
  not rupture. Both must be checked independently.
- Reading a scatter factor of 4 applied to the stress amplitude rather than the
  life — clause 4.5.1 applies the scatter factor to the demonstrated life in
  cycles, not to the stress level. Misapplying it to stress incorrectly
  overstates safe life.
- Skipping the fatigue check for low-cycle components — components that see
  fewer than 1000 pressure cycles are not exempt; the scatter factor of 4 still
  applies to whatever test life was demonstrated.

## Behavior contract (gate 3)

The component-categorization, proof/burst pressure, hoop stress, margin of
safety, and fatigue safe-life logic is exercised by the gate 3 contract test:
scripts/test_metallic_pressure_components.py against
scripts/metallic_pressure_components_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_metallic_pressure_components.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
