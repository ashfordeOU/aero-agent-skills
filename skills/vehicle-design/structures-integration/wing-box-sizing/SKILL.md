---
name: wing-box-sizing
description: "Use when you must perform wing box sizing at the conceptual level: compute the root bending moment from the load factor, weight, and span with the elliptical lift distribution, scale the limit moment to ultimate with the 1.5 factor of safety, size the spar cap area from the bending moment and the allowable stress, and size the spar web thickness from the shear flow. Produces the root bending moment, ultimate moment, spar cap area, web thickness, and a box sized verdict that gate the wing structure integration. Trigger: wing box sizing, root bending moment, spar cap, shear flow, ultimate load, factor of safety, allowable stress."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: vehicle-design
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: structures-integration
  tags: [wing-box-sizing, wing-box, root-bending-moment, spar-cap, spar-web, shear-flow, box-beam, ultimate-load, factor-of-safety, allowable-stress]
  version: 0.1.0
  author: Aero Agent Skills
---
# Wing Box Sizing (vehicle-design/structures-integration/wing-box-sizing)

Use when the task is sizing the wing box structure at the conceptual
level: root bending moment from the load factor, weight, and span,
ultimate moment from the factor of safety, spar cap area, and spar web
thickness from the shear flow.

## Domain quick reference

- Root bending moment from the elliptical spanwise lift distribution:
  M = (2/(3*pi)) * n * W * b, with n the design load factor, W the
  design weight in newtons, and b the span in meters; result in N m.
  A uniform distribution gives M = n * W * b / 4. The elliptical
  constant 2/(3*pi) is about 0.2122; the uniform constant is 0.25.
- Root shear force per half-wing: V = n * W / 2.
- FAR-25.303 context: the factor of safety between limit and ultimate
  loads is 1.5, so M_ultimate = 1.5 * M_limit.
- Spar cap area from the box-beam bending relation M = sigma * A * h:
  A = M / (sigma * h), with h the box depth between cap centroids and
  sigma the allowable stress in pascals; the result is the area per
  cap (upper and lower caps each take the full couple).
- Spar web shear flow: q = V / (n_webs * h), and web thickness
  t = q / tau with tau the allowable shear stress.
- Worked example: n = 2.5, W = 600000 N, b = 30 m gives a root bending
  moment of about 9.55 MN m (elliptical) and an ultimate moment of
  about 14.32 MN m; with sigma = 400 MPa and h = 0.6 m the spar cap
  area is about 0.0597 m^2; with tau = 240 MPa and two webs the web
  thickness is about 2.6 mm.

## Workflow

1. Collect the design maneuvering load factor, the design weight, the
   span, the box depth, and the allowable stress and shear.
2. Compute the root bending moment with wing_root_bending_moment
   (elliptical distribution by default).
3. Scale the limit moment to ultimate with ultimate_moment.
4. Size the spar cap with spar_cap_area and the web with
   web_shear_flow followed by web_thickness.
5. Compare the required values against the available cap area and web
   thickness with wing_box_verdict, and gate the structure integration
   on the verdict.

## Pitfalls

- Using the limit moment for the cap sizing: the caps must carry the
  ultimate moment, the limit moment times the 1.5 factor of safety.
- Mixing the distribution models: elliptical gives about 0.2122 times
  n*W*b, uniform gives 0.25 times n*W*b; state which model the load
  case uses.
- Confusing the box depth with the airfoil thickness: h is the distance
  between the spar cap centroids, not the maximum airfoil thickness.
- Sizing the web with the full root shear: the shear splits over the
  web count, and web_shear_flow divides by the number of webs.
- A single undersized item fails the box: the verdict requires both the
  spar cap area and the web thickness to fit the available values.
- Zero or negative inputs raise ValueError instead of returning a
  nonsense area or thickness.

## Behavior contract (gate 3)

The sizing logic is exercised by the gate 3 contract test:
scripts/test_wing_box_sizing.py against
scripts/wing_box_sizing_logic.py (stdlib unittest, offline). Run:

python3 scripts/test_wing_box_sizing.py

## Compliance

- FAR-25 is US government work (public domain) and CS-25 is a free
  EASA download; standards referenced, not reproduced, per
  standards-map.yaml. Wing box sizing methodology (box-beam
  idealization, elliptical loading) is common conceptual design
  practice.
- compliance: STANDARDS-REF, gated: false.
