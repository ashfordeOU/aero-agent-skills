---
name: ground-effect
description: "Use when you must estimate the ground effect on a wing operating near the ground: compute the induced drag reduction factor and the induced drag ratio from the height to span ratio, apply the image vortex correction to the downwash and the effective aspect ratio, and estimate the lift increase and lift curve slope change in ground effect for takeoff and landing analysis. Produces the ground effect factor, the corrected induced drag, and the lift curve slope that feed low altitude performance estimates. Trigger: ground effect, induced drag reduction, image vortex, height to span ratio, ground cushion, takeoff lift."
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
  subdomain: ground-effects
  tags: [ground-effect, induced-drag, image-vortex, height-to-span, cushion]
  version: 0.1.0
  author: AeroSkills
---

# Ground Effect (aerodynamics/ground-effects/ground-effect)

Use when the task is wing aerodynamics in ground effect: induced
drag reduction near the ground, the image vortex method, and the
takeoff and landing consequences.

## Domain quick reference

- Ground effect onset is roughly h / b < 1.5, where h is the height
  of the wing reference line above the ground and b the span; the
  effect strengthens as h / b shrinks.
- Image vortex method: the ground plane is replaced by a mirror
  image of the wing vortex system, reflected across the ground and
  with circulation reversed. The image system lies 2 * h below the
  real system and enforces zero normal flow at the ground. Its
  upwash at the real wing cancels part of the downwash.
- Induced drag reduction factor (image vortex result, elliptic
  loading): sigma = 1 / (1 + 16 * (h / b)^2). The induced drag in
  ground effect is C_Di,g = C_Di,inf * (1 - sigma), and the ratio
  to free-air value is 16 * (h / b)^2 / (1 + 16 * (h / b)^2).
  Example: h / b = 0.5 gives sigma = 0.2 (20 percent drag cut),
  h / b = 0.25 gives sigma = 0.5.
- The induced angle of attack falls by the same factor (1 - sigma),
  which raises the effective aspect ratio to AR / (1 - sigma) and
  the lift curve slope toward the 2D value a_inf.
- Lift at fixed angle of attack grows in ground effect; the
  lift-curve slope follows
  a_g = a_inf / (1 + a_inf * (1 - sigma) / (pi * AR)).
- Takeoff: reduced induced drag shortens the ground roll and eases
  initial climb; the wing lifts off at a lower angle of attack for
  a given speed. Landing: the ground cushion reduces sink rate and
  extends the flare, which pilots call float.
- The wing-in-ground-effect craft class exploits h / b below about
  0.5 for cruise economy.

## Workflow

1. Collect h, b, AR, C_L, and the flight condition.
2. Compute the height to span ratio h / b.
3. Compute sigma with ground_effect_factor and the drag ratio with
   induced_drag_ratio.
4. Apply the ratio to the free-air induced drag with induced_drag.
5. Correct the effective aspect ratio and the lift curve slope for
   the takeoff or landing estimate.
6. Flag the h / b band: below about 0.25 the reduction saturates,
   and the 2D limit applies.

## Pitfalls

- Measuring h from the ground to the wrong wing reference; use the
  quarter-chord line or the wing aerodynamic center consistently.
- Using the span instead of the height to span ratio; the formulas
  are functions of h / b only in the image method.
- Forgetting the (1 - sigma) factor on the induced angle of attack
  when recomputing lift, which double counts the drag cut.
- Treating sigma as the drag ratio; sigma is the reduction, the
  ratio is 1 - sigma.
- Extrapolating the linear image method into h / b below about 0.1
  where viscous and pressure effects dominate.
- Ignoring the float on landing: the reduced sink rate extends the
  flare and can push the touchdown point down the runway.
- Assuming the lift gain persists at the stall; ground effect does
  not raise C_L,max by the same factor as the linear lift.
- Applying ground effect corrections to the cruise condition; they
  are negligible above about 1.5 spans.

## Behavior contract (gate 3)

The ground effect factor, drag ratio, image vortex offset, and
lift curve slope logic is exercised by the gate 3 contract test:
scripts/test_ground_effect.py against
scripts/ground_effect_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_ground_effect.py

## Compliance

- NACA Report 824 anchors the classic section data used for the
  free-air baseline; summary values only, per standards-map.yaml.
- The image vortex and ground effect formulas are common
  aerodynamic methodology, not reproduced text.
- compliance: STANDARDS-REF, gated: false.
