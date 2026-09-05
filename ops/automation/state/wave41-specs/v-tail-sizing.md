# Wave-41 leaf spec: v-tail-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/v-tail-sizing/
- Pack: sizing (verified present at prep with tail-sizing, canard-sizing,
  control-surface-sizing, wing-planform-sizing and the rest of the wave-1
  sizing pack). Closest siblings and their fences:
  - tail-sizing owns the conventional separate-surface aft empennage:
    its frontmatter claim is "Covers V_h = S_h * L_h / (S_w * cbar) and
    V_v = S_v * L_v / (S_w * b), with the tail arm measured from the wing
    aerodynamic center to the tail quarter chord", its body gives the
    required-area inverse "S_h = V_h * S_w * cbar / L_h, and S_v = V_v *
    S_w * b / L_v; a longer tail arm reduces the required area, a larger
    wing reference area increases it", and the typical ranges "V_h from
    0.5 to 1.0 (transport category about 0.7), V_v from 0.04 to 0.07
    (transport category about 0.06)"; its Pitfalls show the surfaces are
    distinct ("Sizing the vertical tail with the horizontal reference
    length; the vertical tail volume coefficient uses the span, not the
    chord") and nothing in its body maps the two requirements onto a
    single canted pair of surfaces. No V-tail, vee-tail, ruddervator or
    tail-dihedral concept anywhere in the leaf.
  - canard-sizing owns the forward surface: its body states "It pairs
    with vehicle-design/sizing/tail-sizing, which owns the conventional
    aft empennage volume coefficients V_h and V_v", i.e. it explicitly
    defers the aft empennage pair to tail-sizing; no V-tail treatment.
  - control-surface-sizing owns elevator and rudder area from the pitch
    and yaw moment requirements (its corpus task w?-control-surface-sizing
    is adversarial "against tail volume coefficient and engine-out
    vocabulary"), not from the volume-coefficient equivalence.
  - openvsp-geometry (conceptual pack) is the only tree hit for the probe
    "dihedral.*tail" and it is wing planform geometry only ("define the
    wing planform from the span, the root and tip chords, the sweep, the
    dihedral and the twist"), no empennage equivalence.
  Whole-tree greps at prep: "v-tail", "ruddervator", "vee-tail",
  "butterfly-tail" and "v tail" = 0 hits in skills/vehicle-design and 0
  hits in eval/hit1-corpus.yaml. The V-tail volume-coefficient
  equivalence is a GENUINE gap: the sizing pack resolves the horizontal
  and vertical volume requirements onto separate S_h and S_v surfaces
  only, and no leaf maps them onto the canted V-tail pair with its
  ruddervators.
- Standards id: far-25 (present in standards-map.yaml; all vehicle-design
  sizing siblings carry far-25 reference-only). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Size a V-tail (butterfly or vee tail) empennage from equivalent
horizontal and vertical tail-volume requirements: convert each target
volume coefficient into the required equivalent area (S_h = V_h * S_ref *
c_bar / l_h on the mean aerodynamic chord, S_v = V_v * S_ref * b / l_v on
the span), resolve the two equivalent areas onto a single canted pair of
surfaces under the documented planform-area projection convention (total
V-tail area S_vt = sqrt(S_h^2 + S_v^2), dihedral Gamma = atan(S_v / S_h)
measured from the horizontal), split the total equally between the two
panels, derive each panel's span and chord from a per-surface aspect
ratio, size the ruddervator control area as a documented fraction of the
total V-tail area, and verify that the projected effective areas
S_vt cos(Gamma) and S_vt sin(Gamma) recover the required volume
coefficients at the given arms. Produces the required equivalent areas,
the total V-tail area, the dihedral angle in radians and degrees, the
per-surface area, span and chord, the ruddervator area, and the effective
volume-coefficient round trip with its met verdicts. Does NOT do:
conventional separate-surface horizontal and vertical tail sizing,
coefficient evaluation from given tail areas, or typical-range verdicts
(tail-sizing); canard or forward-surface sizing with trim lift share and
stall precedence (canard-sizing); elevator and rudder control area from
pitch and yaw moment requirements or hinge moments
(control-surface-sizing); wing planform geometry with sweep and twist
(openvsp-geometry). Deterministic stdlib geometry only; the projection
convention is fixed and documented below, so outputs are reproducible.

## Model (implement exactly)

Pinned convention (planform-area projection, documented method): the
total V-tail area S_vt is split equally between two panels canted up at
dihedral Gamma from the horizontal plane. The horizontal-equivalent area
entering the horizontal volume-coefficient formula is the sum of the
horizontal projections of both panels, S_h_eff = S_vt * cos(Gamma), and
the vertical-equivalent area is S_v_eff = S_vt * sin(Gamma). This is the
Raymer-style projected-area equivalence for the areas used in the volume
coefficient formulas (name and paraphrase only, common conceptual sizing
methodology; the cos^2/sin^2 loading convention is NOT used here). The
vector-sum inversion S_vt = sqrt(S_h^2 + S_v^2) and Gamma = atan(S_v /
S_h) is exact under this convention, and the equal panel split makes the
per-surface horizontal projection (S_vt / 2) * cos(Gamma) and vertical
projection (S_vt / 2) * sin(Gamma).

Functions (pure stdlib, math only), module v_tail_logic.py:
- tail_area_from_volume_coefficient(v_coef, ref_len, tail_arm, s_ref) ->
  float v_coef * s_ref * ref_len / tail_arm, the required equivalent
  tail area for one volume coefficient target; call with ref_len = c_bar
  and tail_arm = l_h for the horizontal requirement (V_h) and ref_len =
  b and tail_arm = l_v for the vertical requirement (V_v), matching the
  tail-sizing leaf inverse exactly; ValueError if any input <= 0.
- vtail_geometry(s_h_req, s_v_req, aspect_ratio =
  SURFACE_ASPECT_RATIO) -> dict {"s_vt", "gamma_rad", "gamma_deg",
  "area_per_surface", "span_per_surface", "chord_per_surface"} with
  s_vt = sqrt(s_h_req^2 + s_v_req^2), gamma_rad = atan2(s_v_req,
  s_h_req) in [0, pi/2), gamma_deg = degrees(gamma_rad),
  area_per_surface = s_vt / 2. Per-surface aspect ratio convention
  (documented in the SKILL body): one panel of area area_per_surface is
  treated as a flat surface with its own aspect ratio, so
  span_per_surface = sqrt(aspect_ratio * area_per_surface) and
  chord_per_surface = area_per_surface / span_per_surface (the mean
  chord of one panel). ValueError if s_h_req <= 0, s_v_req <= 0 or
  aspect_ratio <= 0. Dict keys exactly as documented.
- ruddervator_sizing(s_vt, control_fraction =
  RUDDERVATOR_FRACTION) -> dict {"ruddervator_area_total",
  "ruddervator_area_per_surface", "control_fraction"}: total ruddervator
  area = control_fraction * s_vt (the fraction of the total V-tail area
  given to the movable ruddervator control surfaces, a documented
  engineering default of 0.35); per-surface = total / 2 since each panel
  carries one ruddervator. No hinge-geometry output; area fraction only.
  ValueError if s_vt <= 0 or control_fraction <= 0 or control_fraction
  >= 1.
- effective_volume_check(s_vt, gamma_rad, v_h_target, v_v_target,
  s_ref, c_bar, b, l_h, l_v) -> dict {"s_h_eff", "s_v_eff", "v_h_eff",
  "v_v_eff", "v_h_met", "v_v_met"}: s_h_eff = s_vt * cos(gamma_rad),
  s_v_eff = s_vt * sin(gamma_rad), v_h_eff = s_h_eff * l_h / (s_ref *
  c_bar), v_v_eff = s_v_eff * l_v / (s_ref * b). The met flags compare
  with a documented tolerance that absorbs the cos/sin/atan2 round-trip
  error of order 1e-16: v_h_met = v_h_eff >= v_h_target - VOLUME_TOL
  and v_v_met = v_v_eff >= v_v_target - VOLUME_TOL with VOLUME_TOL =
  1e-9 (module constant); a tail sized from the same targets and arms
  therefore returns both met flags True, while a genuinely undersized
  tail fails. ValueError if any input <= 0.
Module constants: RUDDERVATOR_FRACTION = 0.35, SURFACE_ASPECT_RATIO =
4.0, VOLUME_TOL = 1e-9.

Identity to test: projection identity s_h_eff^2 + s_v_eff^2 == s_vt^2;
round trip returns the required areas and target coefficients within
1e-12; equal requirements give Gamma = 45 deg and S_vt = sqrt(2) * S_h;
longer tail arms reduce the required area (doubling the arm halves it);
met flags True for the sized geometry and False for a 10% undersized
area; all non-positive inputs raise ValueError.

## Worked example

Light aircraft: S_ref = 16 m2, c_bar = 1.5 m, b = 11 m, tail arm l_h =
l_v = 4.5 m, targets V_h = 0.7 and V_v = 0.04 (both inside the
tail-sizing typical ranges quoted above).

- Required equivalent areas: S_h = 0.7 * 16 * 1.5 / 4.5 = 3.73333 m2
  and S_v = 0.04 * 16 * 11 / 4.5 = 1.56444 m2.
- V-tail resolution: S_vt = sqrt(3.73333^2 + 1.56444^2) = 4.04787 m2,
  Gamma = atan(1.56444 / 3.73333) = 0.396818 rad = 22.7360 deg from the
  horizontal (included vee angle 45.472 deg).
- Per-surface geometry at aspect ratio 4: each panel carries
  area_per_surface = 2.02394 m2, span_per_surface = sqrt(4 * 2.02394) =
  2.84530 m, chord_per_surface = 0.711325 m.
- Ruddervators at the 0.35 fraction: ruddervator_area_total = 1.41676
  m2, per surface 0.708378 m2.
- Effective volume round trip: s_h_eff = 3.73333 m2 and s_v_eff =
  1.56444 m2 recover v_h_eff = 0.7 and v_v_eff = 0.04 within 1e-15, so
  both met flags are True under VOLUME_TOL; a 10% smaller S_vt (3.64308
  m2) at the same Gamma gives v_h_eff = 0.63 and v_v_met False.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds, computed by running the prep anchor
script /tmp/w41spec/anchor_vtail.py (prep-verified by stdlib math). Real
prep outputs: s_h 3.7333333333333325, s_v 1.5644444444444445, s_vt
4.047871563863021, gamma_rad 0.3968181439505532, gamma_deg
22.736004882581458, area_per_surface 2.0239357819315105,
span_per_surface 2.8453019396412116, chord_per_surface 0.711325484910303,
ruddervator_area_total 1.4167550473520572, ruddervator_area_per_surface
0.7083775236760286, round trip v_h_eff 0.6999999999999998 and v_v_eff
0.04.

## Validation list (contract test must include)

- tail_area_from_volume_coefficient(0.7, 1.5, 4.5, 16.0) = 3.73333
  within 1e-6; (0.04, 11.0, 4.5, 16.0) = 1.56444 within 1e-6;
  arm 9.0 m halves S_h to 1.86667 (within 1e-6); ValueErrors at v_coef
  0 and negative, ref_len 0, tail_arm 0, s_ref negative.
- vtail_geometry on the example: s_vt 4.04787, gamma_rad 0.396818,
  gamma_deg 22.7360, area_per_surface 2.02394, span_per_surface
  2.84530, chord_per_surface 0.711325 (all within 1e-4 of the real prep
  values listed above); dict keys exactly s_vt, gamma_rad, gamma_deg,
  area_per_surface, span_per_surface, chord_per_surface.
- Symmetric identity: vtail_geometry(1.0, 1.0) gives gamma_deg 45.0 and
  s_vt sqrt(2); span monotone in surface area; ValueErrors at s_h_req 0,
  s_v_req 0 and aspect_ratio 0.
- ruddervator_sizing(4.047871563863021): total 1.41676, per surface
  0.708378 within 1e-4; fraction scaling: 0.5 fraction gives half of
  s_vt... gives 0.5 * s_vt; ValueErrors at s_vt 0 and negative and at
  control_fraction 0, negative and >= 1.
- effective_volume_check round trip on the example: s_h_eff 3.73333,
  s_v_eff 1.56444 within 1e-9, v_h_eff and v_v_eff within 1e-9 of the
  targets, v_h_met True and v_v_met True (tolerance); a 10% smaller
  s_vt at the same gamma gives v_h_met False and v_v_met False; all
  non-positive inputs raise ValueError.
- Projection identity: s_h_eff^2 + s_v_eff^2 == s_vt^2 within 1e-12;
  gamma in [0, pi/2); determinism and fixed dict keys.

## Corpus fragment (eval/hit1-wave41-v-tail-sizing.yaml)

Query 1 (copy verbatim):
  "size the V-tail empennage from the equivalent horizontal and vertical tail volume requirements: the total V-tail area and dihedral angle from the volume-coefficient equivalence, the per-surface geometry at the aspect ratio, and the ruddervator control area"
  intent: "vehicle design; V-tail empennage sizing from the volume-coefficient equivalence with total V-tail area, dihedral angle, per-surface geometry and ruddervator control area"
  expected_skill: "vehicle-design/sizing/v-tail-sizing"
Query 2 (copy verbatim):
  "check the effective volume coefficients of the V-tail at the dihedral angle: do the projected horizontal and vertical equivalent areas of the canted tail meet the tail volume requirements?"
  intent: "vehicle design; effective volume coefficient check of the canted V-tail at the dihedral angle against the horizontal and vertical tail volume requirements"
  expected_skill: "vehicle-design/sizing/v-tail-sizing"
Task ids: w41-v-tail-sizing-1 and -2. Both queries are collision-free at
prep: no "v-tail", "ruddervator" or "vee-tail" token exists anywhere in
eval/hit1-corpus.yaml, and the routing vocabulary (dihedral angle,
volume-coefficient equivalence, canted surfaces, ruddervator) is absent
from the tail-sizing and canard-sizing tasks.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size a V-tail empennage from
the equivalent horizontal and vertical tail volume requirements:" and
include the outputs in the Claim (total V-tail area, dihedral angle,
per-surface geometry, ruddervator area, effective volume round trip).
First tag: v-tail-sizing. Additional tags ONLY: ruddervator,
vee-tail-empennage, tail-volume-equivalence, tail-dihedral-angle,
projected-tail-area. NEVER single generic words (tail, empennage, area,
dihedral, sizing, volume, surface, control). 50-150 words, <=1000 chars,
no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): horizontal-tail, vertical-tail,
tail-volume-coefficient, tail-arm, stabilizer-sizing, mean-aerodynamic-
chord (as a sizing output; tail-sizing and wing-planform-sizing);
canard-volume-coefficient, canard-arm, canard-area, trim-lift-share,
stall-precedence, forward-wing, nose-drops (canard-sizing);
elevator-sizing, rudder-sizing, aileron, hinge-moment, pitch-moment-
requirement, yaw-moment-requirement, roll-rate-requirement, engine-out
(control-surface-sizing); sweep-dihedral-twist, wing-planform,
parametric-geometry (openvsp-geometry).
