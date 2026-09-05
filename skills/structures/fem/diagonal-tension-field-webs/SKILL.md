---
name: diagonal-tension-field-webs
description: "Use when you must analyze a plane shear web above its shear-buckling stress with the diagonal tension field idealization: compute the tension field ratio of the applied shear above the buckling stress, take the classical 45 degree tension field angle or accept the angle for a non-45 web, and compute the diagonal web tension stress, the flange and end post axial loads from the diagonal tension, the rivet shear flows on the flange and end post attachments, and the margin against buckling. Produces the post-buckled web state and the attachment loads that gate the shear web reserve check. Trigger: diagonal tension field, tension field angle, web tension stress, post-buckled shear web, tension field attachment loads, shear web reserve."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: structures
pack: fem
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: fem
  tags: [diagonal-tension-field-webs, tension-field-angle, web-tension-stress, post-buckled-shear-web, tension-field-attachment-loads]
  version: 0.1.0
  author: AeroSkills
---

# Diagonal Tension Field Webs (structures/fem/diagonal-tension-field-webs)

Analyze a plane shear web loaded above its elastic shear-buckling stress
with the classical complete-diagonal-tension idealization: the web sheds
shear into an inclined tension field and carries the excess load as pure
diagonal tension. This leaf computes the tension field ratio, the classical
45 degree tension field angle, the diagonal web tension stress, the flange
and end post axial loads pulled in by the field, the rivet shear flows on
the flange and end post attachments, and the margin against buckling, in
pure Python, stdlib only. It takes the elastic shear-buckling stress tau_cr
as an input from the plate-buckling leaf and hands the elastic load
distribution below buckling to the torsion-shear-flow leaf; this leaf owns
the post-buckled reserve that gates the shear web strength check.

## Domain quick reference

- Regime split: below tau_cr the web is elastic and carries the applied
  shear as shear stress; at tau = tau_cr the web buckles and, above it, the
  excess (tau - tau_cr) is carried by a diagonal tension field. The tension
  field ratio k = (tau - tau_cr) / tau is 0 at tau_cr and approaches 1 as
  the applied shear grows.
- Tension field angle: the classical plane-web value is ALPHA_IDEAL_DEG =
  45.0 degrees, from the Kuhn sin(2 alpha) = 1 approximation of the Wagner
  field orientation; it is constant and continuous across the whole range
  above tau_cr. A web analyzed with an inclined field takes the angle as an
  input alpha_deg instead.
- Diagonal web tension stress: sigma_d = (tau - tau_cr) * (cot(alpha) +
  tan(alpha)) in Pa above tau_cr, zero in the elastic regime. At 45 degrees
  this equals 2 * (tau - tau_cr), the uniaxial diagonal tension that
  replaces the excess shear.
- Flange axial load: P_f = (tau - tau_cr) * t * d * cot(alpha) in N, the
  diagonal-tension component pulled into the flange over the web depth d
  (d between flanges, t the web thickness, both in m).
- End post axial load: P_e = (tau - tau_cr) * t * d * tan(alpha) in N. At
  the ideal 45 degree angle the flange and end post loads are equal.
- Rivet shear flows (N/m): flange q = t * (tau_cr + (tau - tau_cr) *
  tan(alpha)) above buckling, falling back to the elastic q = tau * t below
  it; end post q = tau * t in both regimes, because the end post carries the
  full applied shear.
- Margin against buckling: tau_cr / tau, 1.0 at the buckling stress and
  below 1.0 in the post-buckled field where the web works on its
  diagonal-tension reserve.
- Units are SI throughout: Pa shear stresses, m dimensions, N loads, N/m
  shear flow, degrees for angles. The buckling stress tau_cr is always an
  input; the module hard-codes no material and no allowables.
- FAR-25 frames the airframe shear-web load context; the relations above
  are standard engineering methodology, summary-only.

## Workflow

1. Collect the web state: the applied shear stress tau (Pa), the elastic
   shear-buckling stress input tau_cr (Pa, from the plate-buckling leaf or
   the analysis input), the web depth d between flanges (m), the web
   thickness t (m), and the tension field angle alpha_deg (degrees, default
   ALPHA_IDEAL_DEG = 45.0).
2. Run the regime check with tension_field_ratio(tau, tau_cr): a ratio of
   0.0 means the web is below its buckling stress and has no
   diagonal-tension reserve to analyze.
3. Take the tension field angle with tension_field_angle(tau, tau_cr) for
   the classical 45 degree plane-web value, or pass the inclined angle
   alpha_deg directly into the stress and load functions.
4. Compute the diagonal web tension stress with web_tension_stress(tau,
   tau_cr, alpha_deg), which returns sigma_d in Pa above buckling and 0.0
   below it.
5. Compute the attachment axial loads with flange_axial_load(tau, tau_cr,
   alpha_deg, depth_m, web_thickness_m) and end_post_load(tau, tau_cr,
   alpha_deg, depth_m, web_thickness_m), giving P_f and P_e in N.
6. Compute the rivet shear flows with rivet_shear_flow(tau, tau_cr,
   alpha_deg, web_thickness_m, member) for member "flange" and member
   "end_post", giving q in N/m for each attachment.
7. Gate the reserve with margin_against_buckling(tau, tau_cr): the web is
   in the post-buckled field when the margin is below 1.0, and the reserve
   check compares the diagonal web tension stress and the attachment loads
   and flows against the allowables.
8. Confirm every result with the deterministic contract test
   scripts/test_diagonal_tension_field_webs.py (step 8 confirmation).

## Worked example

Rectangular shear web 500 mm between end posts x 300 mm depth between
flanges x 1.2 mm thick, applied shear tau = 40 MPa and buckling stress
input tau_cr = 18 MPa. Running the module functions gives:

- tension_field_ratio(40e6, 18e6) = 0.55.
- tension_field_angle(40e6, 18e6) = 45.0 degrees.
- web_tension_stress(40e6, 18e6, 45.0) = 44.0 MPa (2 * (40 - 18) MPa at 45
  degrees).
- flange_axial_load(40e6, 18e6, 45.0, 0.3, 0.0012) = 7920 N;
  end_post_load(...) = 7920 N.
- rivet_shear_flow(40e6, 18e6, 45.0, 0.0012, "flange") = 48000 N/m (48
  N/mm); same for "end_post".
- margin_against_buckling(40e6, 18e6) = 0.45.
- Applied shear force V = tau * t * d = 14400 N; buckling shear force Vcr =
  tau_cr * t * d = 6480 N; excess shear = 7920 N, which equals the flange
  axial load at the ideal angle.
- Angle sensitivity on the same web: alpha 38 degrees gives sigma_d =
  45.347 MPa, flange load 10.137 kN, end post load 6.188 kN; at alpha 45
  degrees the values are 44.0 MPa and 7.92 kN on both attachments.

## Verification

- Confirm tension_field_ratio(40e6, 18e6) = 0.55, that the ratio is 0.0 at
  tau = tau_cr and in the elastic regime, and that it approaches 1 as tau
  grows.
- Confirm tension_field_angle is 45.0 degrees from just above tau_cr to
  1e6 * tau_cr (continuity of the classical angle).
- Confirm web_tension_stress = 44.0 MPa at the worked example, 45.347 MPa
  at 38 degrees, 0.0 below tau_cr, and that the 30 and 60 degree fields
  give equal stress (cot + tan symmetry about 45 degrees).
- Confirm flange_axial_load and end_post_load = 7920 N at 45 degrees (the
  45 degree symmetry identity), 10137.1 N and 6187.8 N at 38 degrees, 0.0
  below tau_cr, and that the flange load is monotone increasing in tau
  (4320 N at 30 MPa, 15120 N at 60 MPa).
- Confirm both rivet shear flows = 48000 N/m at 45 degrees, that the flange
  flow below buckling is the elastic tau * t, and that the end post flow is
  tau * t in both regimes.
- Confirm margin_against_buckling = 0.45 at the worked example, 1.0 at tau
  = tau_cr and 0.0 at zero applied shear, and that margin * tau
  reconstructs tau_cr.
- Confirm every negative tau, zero tau_cr, angle outside (0, 90) degrees,
  non-positive depth or thickness, and any member other than flange or
  end_post raises ValueError.
- Run the contract test offline: python3
  scripts/test_diagonal_tension_field_webs.py (35 tests, deterministic).

## Related leaves

- structures/fem/torsion-shear-flow: the elastic Bredt-Batho shear-flow
  distribution and shear center below buckling; it stops where the web
  buckles and this leaf takes over above tau_cr.
- structures/fem/plate-buckling: computes the elastic shear-buckling
  stress tau_cr that this leaf takes as an input; it does not compute the
  diagonal-tension state above tau_cr.
- structures/fem/buckling-analysis: general Euler column and panel
  buckling checks of the same structure, adjacent to the post-buckled web
  reserve computed here.

## Pitfalls

- Applying the diagonal-tension reserve below tau_cr: an elastic web below
  its buckling stress carries the shear as shear stress, and every
  diagonal-tension quantity here returns 0.0; only the rivet flows keep the
  elastic tau * t value.
- Reading the flange rivet flow as tau * t above buckling: once the field
  forms the flange attachment flow is t * (tau_cr + (tau - tau_cr) *
  tan(alpha)), which equals tau * t only at 45 degrees and exceeds it for
  alpha above 45 degrees, so the elastic value is unconservative there.
- Swapping the flange and end post roles: the flange picks up the
  cot(alpha) component of the diagonal tension over the web depth, the end
  post the tan(alpha) component, and the end post rivets still carry the
  full applied shear tau * t even when the web is below buckling.
- Quoting sigma_d as a shear stress: the diagonal tension is a uniaxial
  tensile stress of magnitude 2 * (tau - tau_cr) at 45 degrees, a factor of
  two above the excess shear that formed it; check it against the tension
  allowable, not the shear allowable.
- Mixing unit systems: a thickness entered in mm against Pa stresses and m
  depths silently shifts loads and flows by decades; keep Pa, m, N and N/m
  together before quoting the reserve.
- Misreading the buckling margin direction: margin_against_buckling below
  1.0 does not mean the web fails, it means the web is in the post-buckled
  diagonal-tension regime; the reserve check then gates the diagonal
  tension stress and the attachment loads and flows against their
  allowables.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_diagonal_tension_field_webs.py

The test covers the worked 500 x 300 x 1.2 mm web contract (ratio 0.55,
sigma_d 44.0 MPa, flange and end post loads 7920 N, rivet flows 48000 N/m,
margin 0.45, V 14400 N and Vcr 6480 N with the excess shear reconstructing
the flange load), the elastic-regime zeros below tau_cr, the 45 degree
symmetry identity for loads and flows, the cot + tan angle symmetry, the 38
degree angle sensitivity anchors (45.347 MPa, 10.137 kN, 6.188 kN), the
tension field ratio approach to 1, the margin inverse relation, the flange
load monotonicity in tau, the angle continuity across the post-buckling
range, run-to-run determinism, and ValueError rejection of every
non-physical input in the validation list.

## Compliance

- FAR-25 is referenced, not reproduced: standards-map.yaml marks it gated:
  false and reference-only: true; only the summary paraphrase above is
  used, never standard text.
- compliance: STANDARDS-REF, gated: false.
