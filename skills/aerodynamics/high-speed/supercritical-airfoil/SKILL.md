---
name: supercritical-airfoil
description: "Use when you must analyze or design a supercritical airfoil for high-speed flight: compute the drag-divergence Mach number from the Korn thickness-lift rule, estimate the terminating shock strength of the upper-surface supersonic pocket, quantify the wave-drag penalty above drag divergence, and size the maximum thickness ratio or cruise lift coefficient that the flat upper surface permits. Produces the drag-divergence Mach, the shock-strength reduction, the wave-drag penalty, and the aft-loading pitching moment that feed high-speed wing design. Trigger: supercritical airfoil, drag divergence Mach, aft loading, flat upper surface, wave drag, shock strength."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: aerodynamics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: high-speed
  tags: [supercritical-airfoil, drag-divergence-mach, aft-loading, flat-upper-surface, wave-drag-reduction, terminating-shock-strength, cruise-lift-coefficient]
  version: 0.1.0
  author: Aero Agent Skills
---

# Supercritical Airfoil Design and Analysis (aerodynamics/high-speed/supercritical-airfoil)

Use when the task is supercritical airfoil design and analysis: the flat
upper surface, aft loading, drag-divergence Mach, wave-drag reduction,
terminating shock strength, and the cruise lift coefficient of the
section.

## Domain quick reference

- Supercritical airfoil: a section whose nearly flat upper surface keeps
  the local Mach number barely supersonic over a long region. The weak
  supersonic pocket replaces the strong suction peak of a conventional
  section, so the terminating shock at its rear is weaker and wave drag
  at high subsonic Mach is reduced.
- Terminating shock strength: the static pressure ratio p2/p1 across the
  normal shock that closes the supersonic pocket,
  p2/p1 = 1 + 2*gamma/(gamma+1)*(M^2 - 1), evaluated at the local Mach
  just ahead of the shock (gamma = 1.4). A conventional section at
  M 0.8 accelerates the upper surface to about M 1.3, ratio about 1.81;
  the flat top of a supercritical section holds it near M 1.15, ratio
  about 1.38. Weaker shock means less wave drag and less
  shock/boundary-layer separation risk.
- Wave-drag penalty: above drag divergence, wave drag grows roughly with
  the cube of (M - M_DD). The penalty index (M - M_DD)^3 is zero at or
  below M_DD and rises steeply above it.
- Drag-divergence Mach (Korn rule of thumb): M_DD = 0.95 - t/c - C_L/10
  for a supercritical section and M_DD = 0.90 - t/c - C_L/10 for a
  conventional section, with t/c the thickness ratio and C_L the cruise
  lift coefficient. The 0.05 offset is the wave-drag-reduction benefit.
  Example: t/c 0.12 at C_L 0.5 gives M_DD 0.78 supercritical versus
  0.73 conventional.
- Thickness and lift at fixed Mach (inverse Korn): at M 0.8 and C_L 0.5
  the supercritical section still carries t/c 0.10 while the
  conventional section is limited to about 0.05; equivalently, at
  M 0.8 with t/c 0.10 the supercritical section carries C_L 0.5 while
  the conventional section has no cruise lift left. This is the classic
  "same Mach, roughly twice the thickness" trade.
- Aft loading: camber and loading concentrated near the trailing edge
  recover the lift lost by the flat upper surface, at the price of a
  more negative pitching moment about the aerodynamic center: about
  -0.12 for a typical supercritical section versus -0.06 for a
  conventional transport section. The trim drag this creates is part of
  the trade against the wave-drag saving.
- Range: the Korn rule is a high-subsonic design rule of thumb, valid
  for t/c in (0.02, 0.30), C_L in [0, 1.5), and flight Mach below 1;
  supersonic cruise is out of domain.
- Validation anchor: NACA Report 824 (public domain) supplies the
  classic section data that the design trade is compared against.

## Workflow

1. Fix the design point: cruise Mach M, target cruise lift coefficient
   C_L, and thickness ratio t/c.
2. Compute the drag-divergence Mach with drag_divergence_mach for both
   section types; keep the cruise Mach below M_DD.
3. Size the section: max_thickness_ratio at fixed Mach and C_L, or
   max_cruise_lift_coefficient at fixed Mach and t/c, for the chosen
   type.
4. When M exceeds M_DD, estimate the wave-drag penalty with
   wave_drag_penalty.
5. Assess the terminating shock strength with terminating_shock_strength
   at the local Mach ahead of the shock on the upper surface.
6. Note the aft-loading pitching moment with aft_loading_moment and
   budget the trim drag in the tail sizing.

## Pitfalls

- Reading a supercritical claim at the free-stream Mach as if the local
  upper-surface Mach were the same; the flat top keeps the local Mach
  barely supersonic, which is the whole mechanism.
- Using the conventional base (0.90) for a supercritical section or the
  reverse; the 0.05 offset is the benefit being quantified.
- Treating the Korn rule as exact; it is a design rule of thumb
  calibrated against wind-tunnel data, not a theory.
- Ignoring the aft-loading moment: the more negative C_m,ac needs a tail
  download and costs trim drag that eats part of the wave-drag saving.
- Expecting the flat upper surface to keep the lift unchanged; the flat
  top loses front loading and aft loading is what recovers the cruise
  lift coefficient.
- Applying the rules at or above M 1; the supercritical benefit is a
  high-subsonic effect and supersonic cruise is out of domain.
- Assuming the terminating shock disappears; it is weakened, not
  eliminated, and the shock/boundary-layer interaction at its foot still
  needs care.
- Confusing drag-divergence Mach with the first-sonic-point Mach; M_DD
  sits well above it, and first-sonic-point estimation belongs to the
  transonic-similarity leaf.

## Behavior contract (gate 3)

The design logic is exercised by the gate 3 contract test:
scripts/test_supercritical_airfoil.py against
scripts/supercritical_airfoil_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_supercritical_airfoil.py

## Compliance

- The Korn rule and the flat-upper-surface/aft-loading mechanism are
  standard public-domain textbook content (Anderson, Fundamentals of
  Aerodynamics; Mason, Configuration Aerodynamics; Whitcomb's NASA work
  on supercritical airfoils is US Government public-domain); paraphrase
  and computed values only, no verbatim excerpts of any standard.
- Standards reference: NACA TR 824 (classic airfoil section data,
  reference-only) per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
