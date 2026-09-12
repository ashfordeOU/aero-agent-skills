---
name: riveted-joint-analysis
description: "Use when verify a riveted structural joint per ECSS-E-ST-32C clause 4.6.2.15: distribute applied shear and in-plane moment to individual rivets using the centroid method, compute rivet shear force and sheet bearing stress for each fastener, determine the inter-rivet buckling critical stress for the skin panel between fasteners, and evaluate crippling stress for each thin-walled outstanding flange element. Flag any rivet or panel element with a negative margin of safety before issuing a stress report. Covers single-shear and double-shear rivet patterns, inter-rivet skin buckling under compressive running load, and outstanding-flange crippling. Trigger: ecss, e-st-32-structures-scope, riveted-joint, shear-transfer, inter-rivet-buckling, crippling-analysis, rivet-pattern, fastener-margin, bearing-stress."
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
  tags: [ecss, e-st-32-structures-scope, riveted-joint, shear-transfer, inter-rivet-buckling, crippling-analysis, rivet-pattern, fastener-margin, bearing-stress]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Riveted-Joint Analysis (space-systems/ecss/riveted-joint-analysis)

Use when the task is the strength verification of a riveted structural
joint per ECSS-E-ST-32C clause 4.6.2.15 — distributing shear loads to
individual rivets, checking rivet shear and sheet bearing margins,
evaluating inter-rivet skin buckling under compressive load, and
assessing crippling of thin-walled attached elements.

## Domain quick reference

- A riveted joint transfers shear between two or more structural members
  through discrete fasteners arranged in a pattern. The applied shear
  force and any in-plane moment are distributed to individual rivets
  using the centroid method: the direct (uniform) shear component is
  split equally among all rivets, while the moment component produces a
  force on each rivet proportional to its distance from the group
  centroid and perpendicular to that radius, scaled by the polar second
  moment of the rivet group.
- Each rivet is assessed for two failure modes: (a) rivet shear — the
  resultant fastener force divided by the single-shear allowable for
  that rivet material, diameter, and grip; and (b) sheet bearing — the
  resultant force divided by rivet diameter times sheet thickness,
  compared against the sheet material bearing allowable. Both checks
  must show a non-negative margin of safety for the joint to pass.
- Under compressive running loads, the skin between adjacent rivets can
  buckle as a plate-column — termed inter-rivet buckling. The critical
  stress is proportional to Young's modulus and the square of the
  thickness-to-pitch ratio, scaled by a fixity coefficient that depends
  on how rigidly the rivet heads restrain the sheet edge. A rivet that
  allows the sheet to rotate freely has a lower fixity coefficient and a
  lower critical stress; a rivet with a large head or interference fit
  increases fixity and raises the critical stress.
- Thin-walled section elements attached to riveted joints — outstanding
  flanges, webs — are also subject to crippling: a local collapse where
  the free-edge portion of the element buckles before the overall
  section yields. The crippling stress is the smaller of the material
  compressive yield stress and an elastic plate-buckling stress that
  depends on the element width-to-thickness ratio and the free-edge
  boundary condition. Every outstanding element with a negative crippling
  margin must be redesigned before the joint passes.

## Workflow

1. Define the rivet group: record the (x, y) coordinates of each rivet
   in the fastener pattern, the rivet diameter, material shear allowable,
   sheet thickness, and sheet bearing allowable.
2. Distribute the applied shear (Vx, Vy) and in-plane moment M to each
   rivet using the centroid method. Compute the group centroid and polar
   second moment; add the direct shear component (V/n) to the moment
   component (M × r / Ip) vectorially to obtain the resultant force on
   each rivet. Reject a group with zero polar moment (all rivets
   coincident) if moment is non-zero.
3. For each rivet, compute the rivet shear margin:
      MS_shear = Fs_allow / F_resultant − 1
   and the bearing margin:
      MS_bearing = Fbr_allow / (F_resultant / (d × t)) − 1
   A margin below zero is a finding; record the rivet index and both
   margin values.
4. For each skin panel under compressive running load, determine the
   inter-rivet buckling critical stress using the plate-column formula:
      sigma_cr = c × π² × E / (12 × (1 − ν²)) × (t / p)²
   where c is the fixity coefficient, t is the sheet thickness, and p is
   the rivet pitch. Compare sigma_cr against the applied compressive
   stress; a negative margin is a finding.
5. For each outstanding flange or web element, compute the crippling
   stress as the smaller of the material compressive yield stress Fcy and
   the elastic plate buckling stress K_cr × E × (t/b)², where b is the
   free-edge width. Compare against the applied compressive stress; a
   negative crippling margin is a finding.
6. Aggregate all findings. The joint passes only when every rivet has
   non-negative shear and bearing margins, every skin panel has a
   non-negative inter-rivet buckling margin, and every section element
   has a non-negative crippling margin.

## Pitfalls

- Applying the total shear directly to the critical rivet without
  distributing the moment contribution — the rivet farthest from the
  centroid carries the highest resultant and may be the critical one
  even when all rivets share the same direct-shear component.
- Using the same fixity coefficient for all rivet types — countersunk
  rivets restrain the sheet less effectively than protruding-head
  rivets; conflating the two underestimates the inter-rivet buckling
  risk for countersunk fasteners.
- Treating a zero inter-rivet buckling check as not applicable when the
  joint is loaded in compression — the panel still has a rivet pitch and
  a skin thickness, so the check must be performed and documented even
  when the critical stress is well above the applied stress.
- Confusing bearing stress with net-section tension — bearing is the
  contact stress between the rivet shank and the sheet hole wall; it
  must be checked separately from the net-section tensile stress in the
  sheet (which is a separate sheet-strength check, not the rivet check).
- Using the full section width as the crippling width b for an element
  that is attached on both edges — b is the free-edge length; an element
  attached on both sides (e.g., a web between two caps) uses a different
  plate buckling coefficient and a different effective width, not the
  outstanding-flange formula.

## Behavior contract (gate 3)

The shear-distribution, rivet shear margin, bearing margin,
inter-rivet buckling, crippling, and full group check logic is exercised
by the gate 3 contract test:
  scripts/test_riveted_joint_analysis.py against
  scripts/riveted_joint_analysis_logic.py (stdlib unittest, offline).
Run:
  python3 scripts/test_riveted_joint_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
