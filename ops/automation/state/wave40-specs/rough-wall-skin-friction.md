# Wave-40 leaf spec: rough-wall-skin-friction (aerodynamics, boundary-layer pack)

- Path: skills/aerodynamics/boundary-layer/rough-wall-skin-friction/
- Pack: boundary-layer (verified present at prep with boundary-layer-
  theory, boundary-layer-separation and boundary-layer-transition).
  Closest siblings: boundary-layer-theory (smooth flat plate only; its
  frontmatter claim is "Compute laminar and turbulent boundary-layer
  thicknesses for a smooth flat plate" with the 1/7 power-law local
  friction Cf = 0.0592 / Re_x^(1/5), and roughness appears only as a
  caveat, "Treating the transition point as fixed: roughness, free-stream
  turbulence, and pressure gradient move it by orders of magnitude"; no
  roughness-height input exists in its functions),
  boundary-layer-transition (natural transition only: its body states the
  model "covers a clean two-dimensional surface (no roughness, sweep or
  suction inputs and no Tollmien-Schlichting wave-growth integration; the
  Michel criterion replaces an eN envelope)" and its Pitfalls repeat
  "this leaf covers clean two-dimensional natural transition only; the
  Michel criterion replaces an eN envelope and takes no roughness, sweep
  or suction input"),
  boundary-layer-separation (Thwaites-lambda and Stratford separation
  criteria, no friction coefficient),
  parasite-drag (drag-polars pack, smooth-surface buildup: "Cf is the
  flat-plate skin-friction coefficient, FF the form factor, Q the
  interference factor, S_wet_i the wetted area of the component" with the
  smooth-wall pair "laminar Cf = 1.328 / sqrt(Re); fully turbulent
  Cf = 0.455 / (log10(Re))^2.58"; no roughness-height term anywhere),
  flat-plate-skin-friction-heating (high-speed pack; smooth-wall friction
  feeding heating: "Local skin friction: laminar Cf = 0.664 /
  sqrt(Re_star); turbulent Cf = 0.0592 / Re_star**0.2 (1/7-power law
  form)" plus the recovery-factor and flux layer this leaf does not
  touch). Whole-tree greps at prep: "sand roughness", "fully rough",
  "rough-wall" and "roughness height" = 0 hits in skills/aerodynamics;
  roughness appears only in the caveat sentences above. GENUINE AERO gap
  (fresh probe): the turbulent flat-plate friction estimate takes no
  surface-roughness input anywhere in the tree.
- Standards id: naca-tr-824 (reference-only). Ledger Standard:
  naca-tr-824.
- Family: aerodynamics

## Claim

Estimate the turbulent skin-friction coefficient of a rough flat plate in
incompressible flow: compute the smooth-wall turbulent baseline Cf from
the local Reynolds number, the friction velocity from that baseline, and
the roughness Reynolds number k+ of the equivalent sand roughness; classify
the surface as smooth, transitional or fully-rough on the classic
roughness-Reynolds thresholds; compute the Schlichting fully-rough
correlation value for the fetch; and select the operative coefficient
without iteration, using the direct fully-rough value when the surface is
fully rough and a documented log-linear blend between the smooth value at
k+ 5 and the fully-rough value at k+ 70 when it is transitional; finally
test whether a roughness element of height k trips the boundary layer on
the critical-roughness Reynolds criterion. Produces the regime class, the
k+ value, the smooth baseline, the rough or blended coefficient, the
operative coefficient with its treatment note and the trip verdict that
gate roughness and trip-strip sizing on aerodynamic surfaces. Does NOT
do: laminar or turbulent thickness and displacement estimates or
laminar-friction correlations (boundary-layer-theory); natural transition
location prediction with the Thwaites or Michel methods
(boundary-layer-transition); separation criteria (boundary-layer-
separation); drag buildup with form and interference factors over wetted
areas (parasite-drag); heating, recovery factor or the compressible
reference-temperature method (flat-plate-skin-friction-heating).
Deterministic core only; scatter-ridden transition-onset location is out
of scope (the trip test is a threshold verdict, not an onset distance).

## Model (implement exactly)

Functions (pure stdlib, math only):
- classify_regime(k_s_plus) -> "smooth" when k+ < 5.0, "transitional"
  when 5.0 <= k+ <= 70.0, "fully-rough" when k+ > 70.0, on the module
  constants SMOOTH_K_PLUS = 5.0 and FULLY_ROUGH_K_PLUS = 70.0 (the
  classic hydraulically smooth / transitional / fully rough bands);
  ValueError if k_s_plus < 0.
- smooth_turbulent_cf(re_x) -> float 0.0592 * re_x**-0.2 (the 1/7
  power-law turbulent local friction on a smooth plate, consistent with
  the boundary-layer-theory and flat-plate-skin-friction-heating smooth
  anchors); ValueError if re_x <= 0.
- friction_velocity(u_inf, cf) -> float u_inf * sqrt(cf / 2); ValueError
  if u_inf <= 0 or cf <= 0.
- sand_roughness_reynolds(rho, u_tau, k_s, mu) -> float rho * u_tau *
  k_s / mu (the roughness Reynolds number k+); ValueError if any input is
  <= 0.
- rough_wall_cf(x, k_s) -> float (2.87 + 1.58 * log10(x / k_s))**(-2.5),
  the classical Schlichting fully-rough turbulent flat-plate correlation
  (name and paraphrase only, standard engineering methodology). Validity
  floor: the correlation is calibrated for long fetches and saturates to
  unphysical values when x / k_s is small, so x / k_s must be at least
  ROUGH_MIN_X_OVER_KS = 100.0 (module constant); ValueError if x <= 0,
  k_s <= 0 or x / k_s < 100.0.
- cf_with_roughness(re_x, x, k_s, rho, u_inf, mu) -> dict {"regime",
  "k_s_plus", "cf_smooth", "cf_rough_or_iterated", "cf_used", "note"},
  implementing the non-circular single-pass sequence: (1) cf_smooth from
  smooth_turbulent_cf, (2) u_tau from friction_velocity on cf_smooth, (3)
  k+ from sand_roughness_reynolds, (4) regime from classify_regime, (5)
  the fully-rough correlation value cf_rough = rough_wall_cf(x, k_s), (6)
  selection: smooth regime keeps cf_smooth; fully-rough regime uses
  cf_rough directly; transitional regime interpolates log-linearly in
  ln(k+), frac = (ln k+ - ln SMOOTH_K_PLUS) / (ln FULLY_ROUGH_K_PLUS -
  ln SMOOTH_K_PLUS) and cf = exp(ln cf_smooth + frac * (ln cf_rough -
  ln cf_smooth)), which is continuous and monotone in k+ and returns
  cf_smooth at k+ 5 and cf_rough at k+ 70 exactly. The blend is documented
  in the SKILL body as an engineering approximation. cf_rough_or_iterated
  holds the value the roughness treatment produces (cf_rough in the
  fully-rough regime, the blend in the transitional regime, cf_smooth in
  the smooth regime where the roughness is hydraulically inactive) and
  cf_used equals it by construction (the single-pass sequence never
  iterates); note is a fixed treatment string per regime. ValueErrors as
  in the component functions; dict keys exactly as documented.
- trip_criterion(u, k, nu, re_k_crit = 600.0) -> dict {"re_k": u * k /
  nu, "trip_expected": re_k >= re_k_crit, "re_k_crit": re_k_crit}: the
  critical-roughness Reynolds test, re_k_crit defaulting to the module
  constant TRIP_RE_K = 600.0, the classical critical value for a
  roughness element or trip wire tripping a laminar layer (paraphrase of
  the standard trip-sizing guidance; no verbatim source text); the
  comparison is inclusive at the boundary. ValueError if u <= 0, k <= 0,
  nu <= 0 or re_k_crit <= 0.
Module constants: SMOOTH_K_PLUS = 5.0, FULLY_ROUGH_K_PLUS = 70.0,
ROUGH_MIN_X_OVER_KS = 100.0, TRIP_RE_K = 600.0.

Identity to test: k+ scales linearly with k_s at fixed flow (a 10x height
gives 10x k+); the blend returns cf_smooth at k+ 5 and cf_rough at k+ 70
exactly; classify_regime boundaries sit at 5.0 and 70.0 inclusive of
transitional; smooth_turbulent_cf is monotone decreasing in re_x;
rough_wall_cf is monotone decreasing in x / k_s; trip at re_k == 600 is
expected (inclusive).

## Worked example

Standard air rho = 1.225 kg/m3, u = 60 m/s, mu = 1.81e-5 Pa s (nu =
1.47755e-5 m2/s), plate station x = 2.0 m: re_x = rho * u * x / mu =
8.12155e6, smooth baseline cf = 0.0592 * re_x**-0.2 = 2.45694e-3,
friction velocity u_tau = u * sqrt(cf / 2) = 2.10297 m/s.
- k_s = 0.3 mm: x / k_s = 6666.67, k+ = rho * u_tau * k_s / mu =
  42.6984, so the regime is transitional (5 <= k+ <= 70). The raw
  fully-rough correlation value is 4.21783e-3 and the log-linear blend
  gives cf_used = 3.81178e-3, between the smooth baseline and the fully
  rough value as expected. trip_criterion: re_k = u * k_s / nu =
  1218.23 >= 600, trip_expected True.
- k_s = 3 mm: x / k_s = 666.667, k+ = 426.984, so the regime is
  fully-rough and cf_used = cf_rough_or_iterated = rough_wall_cf =
  6.87032e-3, about 2.8 times the smooth baseline, the expected penalty
  for a heavily sanded surface at this short fetch. trip_criterion: re_k
  = 12182.3, trip_expected True. Fetch sensitivity of the same 3 mm
  roughness: at x = 6 m (x / k_s = 2000) the fully-rough value drops to
  5.37918e-3 and at x = 20 m (x / k_s = 6666.67) to 4.21783e-3, the
  correlation falling as the fetch grows.
- Smooth reference: k_s = 1e-5 m gives k+ = 1.42328 (smooth regime) and
  cf_used = cf_smooth = 2.45694e-3; a small element below trip, k = 3e-5
  m, gives re_k = 121.823 and trip_expected False.
- Regime boundary checks: k+ = 4.999 smooth, k+ = 5.0 transitional, k+ =
  70.0 transitional, k+ = 70.001 fully-rough.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds, computed by running the prep anchor
scripts /tmp/w40spec/anchor_rough_wall.py and
/tmp/w40spec/anchor_rough_wall_edges.py (prep-verified by stdlib math).

## Validation list (contract test must include)

- smooth_turbulent_cf(8.12155e6) = 2.45694e-3 within 1e-8; ValueError at
  re_x 0 and negative.
- classify_regime boundaries: 4.999 smooth, 5.0 transitional, 70.0
  transitional, 70.001 fully-rough; ValueError at negative k+.
- friction_velocity(60, 2.45694e-3) = 2.10297 within 1e-5; ValueError at
  u_inf 0 and cf 0.
- sand_roughness_reynolds on the example: k+ 42.6984 (0.3 mm) and 426.984
  (3 mm) within 1e-3; linearity identity: 10x k_s gives 10x k+.
- rough_wall_cf(2.0, 3e-3) = 6.87032e-3 within 1e-7; (2.0, 3e-4) =
  4.21783e-3 within 1e-7; x = 6 m and x = 20 m values 5.37918e-3 and
  4.21783e-3 within 1e-7.
- rough_wall_cf monotone decreasing in x / k_s; ValueError at x / k_s =
  99.9 (below the 100.0 floor), at k_s 0 and at x 0.
- cf_with_roughness(8.12155e6, 2.0, 3e-4, 1.225, 60.0, 1.81e-5): regime
  transitional, k_s_plus 42.6984, cf_smooth 2.45694e-3, cf_used
  3.81178e-3 within 1e-7.
- cf_with_roughness(8.12155e6, 2.0, 3e-3, 1.225, 60.0, 1.81e-5): regime
  fully-rough, cf_used 6.87032e-3 within 1e-7.
- cf_with_roughness smooth case k_s = 1e-5 m: regime smooth, cf_used
  equals cf_smooth; dict keys exactly regime, k_s_plus, cf_smooth,
  cf_rough_or_iterated, cf_used, note.
- Blend endpoint identities: the blend at k+ 5 equals cf_smooth and at k+
  70 equals cf_rough (within 1e-15); blend monotone between the anchors.
- trip_criterion(60.0, 3e-4, 1.47755e-5): re_k 1218.23 within 1e-3,
  trip_expected True; (60.0, 3e-5, 1.47755e-5): re_k 121.823,
  trip_expected False; inclusive boundary: re_k exactly 600 gives True.
- ValueErrors across the module: non-positive rho, u_tau, mu, u, k, nu,
  re_k_crit.
- Determinism; fixed note strings per regime.

## Corpus fragment (eval/hit1-wave40-rough-wall-skin-friction.yaml)

Query 1 (copy verbatim):
  "estimate the rough-wall-skin-friction of the plate from the sand-roughness height and decide whether the fully-rough-cf correlation applies at this fetch"
  intent: "aerodynamics; sand-roughness regime and fully-rough turbulent skin friction"
  expected_skill: "aerodynamics/boundary-layer/rough-wall-skin-friction"
Query 2 (copy verbatim):
  "check the k-plus-regime and the trip-criterion of the rough-wall-skin-friction estimate from the sand-roughness reynolds number before using the fully-rough-cf value"
  intent: "aerodynamics; roughness reynolds trip test and fully-rough friction coefficient"
  expected_skill: "aerodynamics/boundary-layer/rough-wall-skin-friction"
Task ids: w40-rough-wall-skin-friction-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must estimate the turbulent
skin-friction on a rough flat plate:" and include the outputs in the
Claim. First tag: rough-wall-skin-friction. Additional tags ONLY:
sand-roughness, fully-rough-cf, k-plus-regime, trip-criterion. NEVER
single generic words (skin, friction, roughness, drag, plate, transition,
reynolds, regime, trip). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): blasius, displacement-thickness,
momentum-thickness, shape-factor, transition-reynolds-number
(boundary-layer-theory); thwaites-integral, michel-criterion,
transition-location, natural-transition, e-n-envelope
(boundary-layer-transition); stratford-separation-criterion,
thwaites-lambda-criterion, separation-point, separation-margin
(boundary-layer-separation); form-factor, interference-factor,
wetted-area, drag-buildup, equivalent-skin-friction, zero-lift-drag
(parasite-drag); recovery-factor, adiabatic-wall-temperature,
cold-wall-heat-flux, reference-temperature-method, reynolds-analogy,
sutherland-viscosity (flat-plate-skin-friction-heating).
