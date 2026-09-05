# Wave-40 leaf spec: diagonal-tension-field-webs (structures, fem pack)

- Path: skills/structures/fem/diagonal-tension-field-webs/
- Pack: fem. Closest siblings: torsion-shear-flow (elastic Bredt /
  shear-flow distribution and shear center in the elastic regime; its
  body hands the post-buckling load-carry limit to the buckling
  leaves), plate-buckling (elastic shear buckling stress tau_cr and
  compression effective width; it does not compute the diagonal
  tension state above tau_cr), buckling-analysis (general Euler column
  and panel buckling). The post-buckled diagonal-tension reserve of a
  plane shear web is unowned: whole-tree greps at prep for "diagonal
  tension", "tension field", "Wagner" = 0 hits in skills/structures/.
  GENUINE STRUCT gap (fresh probe, conf 0.8): torsion-shear-flow is
  elastic-only and plate-buckling stops at tau_cr.
- Standards id: far-25 (reference-only; structures fem pack
  convention). Ledger Standard: far-25.
- Family: structures

## Claim

Analyze a plane shear web above its shear-buckling stress with the
classical complete-diagonal-tension idealization: compute the tension
field ratio of the applied shear above the buckling stress, take the
tension field angle (the classical plane-web value 45 degrees from the
Kuhn sin(2 alpha) = 1 approximation, with the angle accepted as an
input for a non-45 web), and compute the diagonal web tension stress,
the flange and end-post axial loads from the diagonal tension, the
rivet shear flows on the flange and end-post attachments, and the
margin against buckling. Produces the post-buckled web state and the
attachment loads that gate the shear web reserve check. Does NOT do:
elastic shear-flow distribution and shear center below buckling
(torsion-shear-flow); the elastic shear-buckling stress itself
(plate-buckling owns tau_cr, which this leaf takes as an input);
general panel or column buckling (buckling-analysis).

## Model (implement exactly)

Functions (pure stdlib; SI: shear stresses in Pa, dimensions in m,
loads in N, shear flow in N/m, angles in degrees; module constant
ALPHA_IDEAL_DEG = 45.0):
- tension_field_ratio(tau, tau_cr) -> float
  k = (tau - tau_cr) / tau when tau > tau_cr, else 0.0 (elastic
  regime below buckling); ValueError if tau < 0 or tau_cr <= 0.
- tension_field_angle(tau, tau_cr) -> float
  the classical plane-web angle ALPHA_IDEAL_DEG (Kuhn sin(2 alpha) =
  1 approximation), constant and continuous across the whole range
  above tau_cr; ValueErrors as above.
- web_tension_stress(tau, tau_cr, alpha_deg) -> float
  sigma_d = (tau - tau_cr) * (cot(alpha) + tan(alpha)) when tau >
  tau_cr, else 0.0; at 45 degrees this equals 2 (tau - tau_cr);
  ValueError if tau < 0, tau_cr <= 0, or alpha_deg outside (0, 90).
- flange_axial_load(tau, tau_cr, alpha_deg, depth_m,
  web_thickness_m) -> float
  P_f = (tau - tau_cr) * t * d * cot(alpha) when tau > tau_cr, else
  0.0 (the diagonal-tension component pulled into the flange over the
  web depth); ValueError if depth_m <= 0 or web_thickness_m <= 0 or
  the shear/alpha errors above.
- end_post_load(tau, tau_cr, alpha_deg, depth_m, web_thickness_m) ->
  float P_e = (tau - tau_cr) * t * d * tan(alpha) when tau > tau_cr,
  else 0.0; ValueErrors as flange_axial_load.
- rivet_shear_flow(tau, tau_cr, alpha_deg, web_thickness_m,
  member) -> float
  for member "flange": q = t * (tau_cr + (tau - tau_cr) * tan(alpha))
  when tau > tau_cr, else q = tau * t; for member "end_post":
  q = tau * t in both regimes (the end post carries the full applied
  shear); ValueError if member not in ("flange", "end_post"), tau <
  0, web_thickness_m <= 0, tau_cr <= 0 or alpha outside (0, 90).
- margin_against_buckling(tau, tau_cr) -> float
  tau_cr / tau when tau > 0, else 0.0; ValueError if tau < 0 or
  tau_cr <= 0.
Module constants: ALPHA_IDEAL_DEG = 45.0.

Identity to test: at alpha = 45 the web tension stress equals
2 (tau - tau_cr) and the flange and end-post loads are equal; the
flange and end-post rivet flows are equal at 45 degrees; below tau_cr
the web stress, flange load and end-post load are all zero and the
rivet flow is the elastic tau * t; the tension field ratio is 0 at
tau = tau_cr and approaches 1 as tau grows; the flange load is
monotone increasing in tau; margin_against_buckling at tau = tau_cr
is 1.0.

## Worked example

Rectangular shear web 500 mm (between end posts) x 300 mm (depth
between flanges) x 1.2 mm, applied shear tau = 40 MPa and buckling
stress input tau_cr = 18 MPa:
- tension_field_ratio = 0.55.
- tension_field_angle = 45 degrees.
- web_tension_stress = 44.0 MPa (2 (40 - 18) at 45 degrees).
- flange_axial_load = 7920 N; end_post_load = 7920 N.
- rivet_shear_flow flange = 48000 N/m (48 N/mm); end_post = 48000 N/m
  (48 N/mm).
- margin_against_buckling = 0.45.
- Applied shear force V = tau t d = 14400 N; buckling shear force Vcr
  = 6480 N; excess shear = 7920 N.
- Angle sensitivity (same web): alpha 38 deg gives sigma_d 45.347 MPa,
  flange 10.137 kN, post 6.188 kN; alpha 45 deg gives 44.0 MPa and
  7.92 kN each.
Run your module and take the real outputs as assert targets; the
anchors above are prep-verified bounds, computed by running the prep
anchor script /tmp/w40spec/anchors_diagtension.py (prep-verified by
stdlib math).

## Validation list (contract test must include)

- tension_field_ratio(40e6, 18e6) = 0.55 exactly within 1e-9;
  ratio(18e6, 18e6) = 0.0; ratio(10e6, 18e6) = 0.0 (elastic);
  ValueErrors at negative tau and tau_cr 0.
- tension_field_angle(40e6, 18e6) = 45.0 and angle(1.01 * tau_cr) =
  45.0 and angle(1e6 * tau_cr) = 45.0 (continuity).
- web_tension_stress(40e6, 18e6, 45.0) = 44.0 MPa within 1e-3;
  at 38 deg = 45.347 MPa within 1e-3; below tau_cr returns 0.0;
  ValueError at alpha 0, 90, negative.
- flange_axial_load(40e6, 18e6, 45.0, 0.3, 0.0012) = 7920.0 within
  0.01; end_post_load same; at 38 deg flange 10137.1 and end post
  6187.8 within 1.0; ValueErrors at depth 0 and negative thickness.
- rivet_shear_flow(40e6, 18e6, 45.0, 0.0012, "flange") = 48000 within
  0.01; end_post 48000; below tau_cr flange = tau * t; ValueError at
  member "web".
- margin_against_buckling(40e6, 18e6) = 0.45; (18e6, 18e6) = 1.0;
  (0, 18e6) = 0.0.
- Monotonicity: flange load at 30 MPa = 4320 N, at 60 MPa = 15120 N.
- Determinism; repeated calls identical; 45-degree symmetry identity
  flange == end_post at alpha 45.

## Corpus fragment (eval/hit1-wave40-diagonal-tension-field-webs.yaml)

Query 1 (copy verbatim):
  "compute the diagonal-tension-field-webs post-buckled state of the shear web with the tension-field-angle and the web-tension-stress above the shear-buckling stress"
  intent: "structures; diagonal tension field post-buckled shear web analysis"
  expected_skill: "structures/fem/diagonal-tension-field-webs"
Query 2 (copy verbatim):
  "find the flange-axial-load and the end-post-load plus the rivet-shear-flow on the attachments of the tension-field web carrying shear above the buckling stress"
  intent: "structures; tension field attachment loads and rivet shear flows"
  expected_skill: "structures/fem/diagonal-tension-field-webs"
Task ids: w40-diagonal-tension-field-webs-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must analyze a plane shear web
above its shear-buckling stress with the diagonal tension field
idealization:" and include the outputs in the Claim. First tag:
diagonal-tension-field-webs. Additional tags ONLY:
tension-field-angle, web-tension-stress, post-buckled-shear-web,
tension-field-attachment-loads. NEVER single generic words (shear,
web, tension, buckling, stress, load, rivet, flow). 50-150 words,
<=1000 chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): bredt, shear-center, shear-flow-
distribution, multi-cell (torsion-shear-flow); shear-buckling-stress,
effective-width, von-karman (plate-buckling); euler-column, johnson,
slenderness (buckling-analysis).
