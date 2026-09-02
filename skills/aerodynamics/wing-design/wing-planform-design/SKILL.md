---
name: wing-planform-design
description: "Use when you must derive the wing-planform-design reference geometry and the spanwise loading of a straight-tapered wing from the span, the area, and the taper-ratio: compute the root-chord and the tip-chord, the mean-geometric-chord, the mean-aerodynamic-chord with its mac-span-station, and convert the leading-edge-sweep into the quarter-chord-sweep. Compute the spanwise-load-distribution with the schrenk-approximation to obtain the local-lift-coefficient at any station, and size the washout-angle so the root reaches stall before the tip, giving the stall-sequencing for a benign stall. Produces the reference chords, the sweep line, and the loading check that feed the lift-curve-slope and vortex-lattice-method leaves. Trigger: wing planform design, taper ratio, mean aerodynamic chord, MAC span station, quarter chord sweep, Schrenk approximation, spanwise load distribution, washout angle."
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
  subdomain: wing-design
  tags: [wing-planform-design, planform-geometry, taper-ratio, root-chord, tip-chord, mean-geometric-chord, mean-aerodynamic-chord, mac-span-station, quarter-chord-sweep, sweep-reference-conversion, schrenk-approximation, spanwise-load-distribution, local-lift-coefficient, washout-angle, stall-sequencing]
  version: 0.1.0
  author: Aero Agent Skills
---

# Wing Planform Design (aerodynamics/wing-design/wing-planform-design)

Use when the task is the planform geometry and spanwise loading of a
straight-tapered wing: the reference chords (root, tip, mean geometric,
mean aerodynamic), the MAC spanwise station, the sweep reference-line
conversion, the Schrenk spanwise load approximation, and the washout
sizing for a root-first stall sequence.

## Domain quick reference

- A straight-tapered (trapezoidal) wing is defined by the span b, the
  reference area S, and the taper ratio lambda = ct/cr in (0, 1]. The
  derived reference geometry is the aspect ratio AR = b^2/S, the root
  chord cr = 2S/(b(1+lambda)), the tip chord ct = lambda*cr, and the
  mean geometric chord cbar = S/b. Worked example, b = 35 m, S = 125 m^2,
  lambda = 0.3: AR = 9.8, cr = 5.4945 m, ct = 1.6484 m, cbar = 3.5714 m.
- Mean aerodynamic chord: MAC = (2/3)cr(1+lambda+lambda^2)/(1+lambda).
  For the example: MAC = 3.9166 m. The MAC is the chord of the equivalent
  rectangular wing that preserves the pitch moment behavior; it is the
  reference for the center of gravity limits and the neutral point, not
  the mean geometric chord.
- MAC spanwise station from the root: y_MAC = (b/6)(1+2lambda)/(1+lambda).
  For the example: y_MAC = 7.1795 m from the root centerline. Checks:
  rectangular wing (lambda = 1) gives y_MAC = b/4, a triangle (lambda
  toward 0) gives y_MAC = b/6.
- Local chord at span station eta = 2y/b in [0, 1]: c(eta) =
  cr(1 - (1-lambda)eta), eta = 0 at the root and eta = 1 at the tip.
  For the example at eta = 0.25: c = 4.5330 m.
- Sweep reference conversion: the chord-fraction line m (0 = leading
  edge, 0.25 = quarter chord, 0.5 = mid chord, 1 = trailing edge) obeys
  tan(Lambda_m) = tan(Lambda_LE) - 4m(1-lambda)/(AR(1+lambda)), so
  tan(Lambda_to) = tan(Lambda_from) + 4(from_ref - to_ref)(1-lambda)/(AR(1+lambda)).
  For the example with Lambda_LE = 30 deg: Lambda_c/4 = 27.5828 deg,
  Lambda_c/2 = 25.0542 deg, Lambda_TE = 19.6755 deg. A straight trailing
  edge needs tan(Lambda_LE) = 4(1-lambda)/(AR(1+lambda)), 12.3954 deg
  for the example.
- Schrenk spanwise loading approximation: the loading is the average of
  the elliptical distribution and the chord-proportional distribution,
  l(eta) = CL[2S/(pi b)sqrt(1-eta^2) + c(eta)/2], with the local
  lift coefficient cl(eta) = l(eta)/c(eta). The loading integrates to
  CL*S, so the approximation carries the exact total lift. For the
  example at CL = 0.5: cl_root = 0.4569 (eta = 0), cl = 0.4928 at
  eta = 0.25, cl = 0.5257 at eta = 0.5, and cl_tip = 0.25 (eta = 1).
  A rectangular wing at CL = 0.5 gives cl_root = 0.5683 and cl_tip =
  0.25; the tip is always lightly loaded because the chord-proportional
  term halves at the tip.
- Washout: linear twist twists the tip nose-down relative to the root,
  alpha_eff(eta) = alpha_root - washout_tip*eta. The washout needed so
  the tip reaches its clmax no earlier than the root is
  epsilon = (tip_local_cl - tip_clmax)/a with the section slope a per
  radian, clamped at zero. Worked example: tip_local_cl = 1.15,
  tip_clmax = 1.0, a = 5.0265 per radian (thin wing, AR = 8) gives
  epsilon = 1.7098 deg. Root-first stall gives a benign stall with
  lateral control retained at the tip.

## Workflow

1. Collect the planform inputs: span, reference area, taper ratio, and
   the sweep angle on one reference line (usually the quarter chord).
2. Compute the derived geometry: aspect_ratio(span, area) and
   trapezoidal_chords(span, area, taper) for the root chord, tip chord,
   and mean geometric chord; confirm the taper with taper_ratio(tip,
   root) when only the chords are known.
3. Compute the mean aerodynamic chord with mean_aerodynamic_chord(root,
   taper) and its spanwise station with mac_span_station(span, taper);
   report the MAC station for the CG limits and the neutral point
   reference.
4. Convert the sweep line with sweep_convert(sweep_deg, from_ref,
   to_ref, span, area, taper) when the leading edge or the mid chord is
   the known line; the quarter chord is the standard reference for
   aerodynamic analysis.
5. Compute the spanwise loading with schrenk_loading(span, area, taper,
   cl_wing, eta) at the stations of interest (root, the MAC station, the
   planform break, the tip) and check that the local cl at the tip stays
   below the tip clmax; the loading integrates to CL*S by construction.
6. Size the washout with washout_required(root_clmax, tip_clmax,
   root_local_cl, tip_local_cl, section_slope), using the tip clmax for
   the thinner tip section and the local cl values from step 5 at the
   design CL; apply the twist with linear_washout_angle(alpha_root_deg,
   washout_tip_deg, eta).
7. Record the reference chords, the sweep line, and the washout in the
   wing geometry definition; the lift curve slope and the detailed
   loading belong to the lift-curve-slope and vortex-lattice-method
   leaves.

## Pitfalls

- Routing geometry here: deriving the reference geometry (chords, MAC,
  sweep line, taper) and the Schrenk loading from a given planform is
  this leaf. Sizing the planform from the takeoff gross weight and the
  wing loading belongs to vehicle-design/sizing/wing-planform-sizing;
  that leaf produces the planform, this leaf analyzes it.
- Routing detailed loading there: a numerical panel solution with
  horseshoe vortices, influence coefficients, downwash, and induced
  drag belongs to vortex-lattice-method. Schrenk is the hand
  approximation for conceptual checks, not a vortex solution.
- Routing sweep effects there: the effect of sweep on the section Mach
  number and the critical Mach (simple sweep theory) belongs to
  swept-wing-aerodynamics; this leaf only converts the sweep reference
  line as geometry.
- Routing cl-alpha there: the lift curve slope corrections (aspect
  ratio, sweep, Mach) belong to lift-curve-slope; this leaf provides
  the aspect ratio and sweep line it consumes, not the slope itself.
- Routing sections there: 2D section shape, camber, and NACA naming
  belong to airfoil-geometry; this leaf treats the wing planform, not
  the section contour.
- Routing clmax increments there: flap and slat clmax increments and
  the stall speed belong to high-lift-systems; this leaf sizes the
  geometric twist for stall sequencing, it does not compute clmax.
- Confusing MAC with the mean geometric chord: the mean geometric chord
  is S/b and locates the planform area; the MAC is the moment-preserving
  reference chord and its spanwise station is y_MAC, not the centroid
  station. Using cbar in place of MAC shifts the CG limit reference.
- Forgetting the MAC station: the MAC value alone is not enough; the
  CG and neutral point limits are measured at y_MAC, which depends on
  the taper ratio through (1+2lambda)/(1+lambda).
- Sign conventions in the sweep conversion: the conversion adds
  4(from_ref - to_ref)(1-lambda)/(AR(1+lambda)); converting from the
  leading edge (0) to the quarter chord (0.25) subtracts, so the
  quarter-chord sweep is always less than the leading-edge sweep for a
  tapered wing. Reversing the sign gives a swept-forward result.
- Clamping the washout: washout_required never returns a negative
  value; a negative excess means the tip is already the lighter loaded
  station and adding wash-in would need an explicit design decision,
  not the default.

## Behavior contract (gate 3)

The reference geometry, sweep conversion, Schrenk loading, and washout
sizing are exercised by the gate 3 contract test:
scripts/test_wing_planform.py against scripts/wing_planform_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_wing_planform.py

## Compliance

- Standards referenced, not reproduced: NACA Report 824 (public domain)
  supplies the section lift data anchor for the clmax values used in the
  washout sizing; the planform formulas, the Schrenk approximation, and
  the twist sizing are common aerodynamic design knowledge, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
