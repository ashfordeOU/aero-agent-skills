---
name: rough-wall-skin-friction
description: "Use when you must estimate the turbulent skin-friction on a rough flat plate: it computes the smooth-wall turbulent baseline Cf from the local Reynolds number, the friction velocity and the sand-roughness reynolds number k+; classifies the k-plus-regime as smooth, transitional or fully rough; evaluates the Schlichting fully-rough-cf correlation for the fetch; and selects the operative coefficient without iteration, the direct fully-rough value or a log-linear blend. Produces the regime class, k+ value, smooth baseline, rough or blended coefficient, operative coefficient with treatment note, and the trip-criterion verdict for roughness and trip-strip sizing on aerodynamic surfaces. Trigger: rough-wall-skin-friction, sand-roughness-height, equivalent-sand-roughness, roughness-reynolds-number, k-plus-regime, fully-rough-cf, trip-criterion, trip-strip-sizing."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: boundary-layer
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: boundary-layer
  tags: [rough-wall-skin-friction, sand-roughness, fully-rough-cf, k-plus-regime, trip-criterion]
  version: 0.1.0
  author: AeroSkills
---

# Rough Wall Skin Friction (aerodynamics/boundary-layer/rough-wall-skin-friction)

Use when the task is estimating the turbulent skin-friction coefficient
of a rough flat plate in incompressible flow from the equivalent
sand-roughness height: smooth-wall turbulent baseline, friction velocity,
roughness Reynolds number k+, surface regime classification, the
fully-rough-cf correlation and a non-iterative coefficient selection with
a documented log-linear blend, plus the trip-criterion test for a
roughness element or trip strip. This leaf implements the classical
roughness band model in pure Python, stdlib only, with the module
constants from the leaf spec (SMOOTH_K_PLUS = 5.0, FULLY_ROUGH_K_PLUS =
70.0, ROUGH_MIN_X_OVER_KS = 100.0, TRIP_RE_K = 600.0). It pairs with
aerodynamics/boundary-layer/boundary-layer-theory, whose smooth-plate
correlations supply the smooth-wall baseline anchor, and with
aerodynamics/drag-polars/parasite-drag, whose buildup can consume the
rough coefficient as the component Cf.

## Domain quick reference

- Smooth-wall turbulent baseline (1/7 power law):
  cf_smooth = 0.0592 / re_x**0.2, with re_x = rho * u_inf * x / mu the
  local Reynolds number at the fetch station x. The rough surface can
  only raise friction above this baseline.
- Friction velocity: u_tau = u_inf * sqrt(cf / 2), the shear velocity
  that scales the roughness.
- Roughness Reynolds number: k+ = rho * u_tau * k_s / mu, formed on the
  equivalent sand-roughness height k_s.
- Regime bands on k+ (classic thresholds): smooth below 5.0,
  transitional from 5.0 through 70.0, fully rough above 70.0. A
  hydraulically smooth surface keeps the smooth-wall coefficient; only a
  transitional or fully-rough surface needs a roughness correction.
- Fully-rough correlation (Schlichting, long-fetch form):
  cf_rough = (2.87 + 1.58 * log10(x / k_s))**(-2.5). Calibrated for long
  fetches, so x / k_s must reach the 100.0 validity floor; the value
  falls as the fetch grows.
- Transitional blend: log-linear in ln(k+) between cf_smooth at k+ 5.0
  and cf_rough at k+ 70.0, frac = (ln k+ - ln 5.0) / (ln 70.0 - ln 5.0)
  and cf = exp(ln cf_smooth + frac * (ln cf_rough - ln cf_smooth)),
  continuous and monotone in k+. The blend is a documented engineering
  approximation across the transitional band.
- Trip test: re_k = u * k / nu for an element of height k; trip is
  expected when re_k >= 600.0, the classical critical roughness
  Reynolds value (paraphrase of standard trip-sizing guidance).
- Units are SI throughout: kg/m3, m/s, Pa s, m.
- NACA-TR-824 frames the classical boundary-layer context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Fix the flow state and the fetch station: density rho, speed u_inf,
   dynamic viscosity mu (nu = mu / rho), the station x from the leading
   edge and the sand-roughness height k_s. Form re_x = rho * u_inf * x /
   mu.
2. Compute the smooth-wall turbulent baseline with
   smooth_turbulent_cf(re_x), the 1/7 power-law local friction that the
   roughness correction departs from.
3. Convert the baseline into a friction velocity with
   friction_velocity(u_inf, cf_smooth) = u_inf * sqrt(cf / 2).
4. Form the roughness Reynolds number with
   sand_roughness_reynolds(rho, u_tau, k_s, mu) = rho * u_tau * k_s / mu.
5. Classify the surface regime with classify_regime(k_s_plus): smooth,
   transitional or fully-rough on the 5.0 and 70.0 thresholds.
6. Evaluate the fully-rough correlation for the fetch with
   rough_wall_cf(x, k_s), valid only when x / k_s >= 100.0.
7. Select the operative coefficient without iteration:
   cf_with_roughness(re_x, x, k_s, rho, u_inf, mu) chains steps 2 through
   6 and returns the dict {regime, k_s_plus, cf_smooth,
   cf_rough_or_iterated, cf_used, note}. The smooth regime keeps
   cf_smooth (roughness hydraulically inactive), the fully-rough regime
   uses cf_rough directly, and the transitional regime takes the
   log-linear blend; cf_rough_or_iterated holds whatever the roughness
   treatment produces and cf_used equals it by construction. The note is
   the fixed treatment string for the regime.
8. Run the trip test on the roughness element with trip_criterion(u_inf,
   k, nu), comparing re_k = u_inf * k / nu against the 600.0 critical
   value (inclusive). This gates roughness and trip-strip sizing on
   aerodynamic surfaces.
9. Confirm the deterministic checks with the contract test
   scripts/test_rough_wall_skin_friction.py.

## Worked example

Standard air rho = 1.225 kg/m3, u_inf = 60 m/s, mu = 1.81e-5 Pa s
(nu = 1.47755e-5 m2/s), station x = 2.0 m. re_x = rho * u_inf * x / mu =
8.12155e6, baseline cf_smooth = 0.0592 * re_x**-0.2 = 2.45694e-3 and the
friction velocity u_tau = 2.10297 m/s.

- k_s = 0.3 mm: x / k_s = 6666.67, k+ = rho * u_tau * k_s / mu = 42.6984,
  so the k-plus-regime is transitional. The fully-rough-cf correlation
  value is 4.21783e-3 and the log-linear blend gives cf_used =
  3.81178e-3, between the smooth baseline and the fully rough value.
  trip_criterion: re_k = 1218.23, above 600, trip_expected True.
- k_s = 3 mm: x / k_s = 666.67, k+ = 426.984, fully-rough, and cf_used =
  cf_rough = 6.87032e-3, about 2.8 times the smooth baseline, the
  expected penalty for a heavily sanded surface at this short fetch.
  trip_criterion: re_k = 12182.3, trip_expected True. Fetch sensitivity
  of the same 3 mm roughness: at x = 6 m (x / k_s = 2000) the
  fully-rough-cf value drops to 5.37918e-3 and at x = 20 m (x / k_s =
  6666.67) to 4.21783e-3, the correlation falling as the fetch grows.
- Smooth reference: k_s = 1e-5 m gives k+ = 1.42328 (smooth) and cf_used
  = cf_smooth = 2.45694e-3; a small element k = 3e-5 m gives re_k =
  121.823, trip_expected False.
- Regime boundary checks: k+ = 4.999 smooth, k+ = 5.0 transitional, k+ =
  70.0 transitional, k+ = 70.001 fully-rough.

## Verification

- Confirm smooth_turbulent_cf(8.12155e6) = 2.45694e-3 within 1e-8 and
  that it rejects re_x <= 0.
- Confirm classify_regime boundaries: 4.999 smooth, 5.0 transitional,
  70.0 transitional, 70.001 fully-rough, and ValueError below zero.
- Confirm friction_velocity(60.0, 2.45694e-3) = 2.10297 within 1e-5 and
  the sqrt closed form.
- Confirm sand_roughness_reynolds returns k+ 42.6984 (0.3 mm) and
  426.984 (3 mm) within 1e-3, and the linearity identity: 10x k_s gives
  10x k+.
- Confirm rough_wall_cf(2.0, 3e-3) = 6.87032e-3, (2.0, 3e-4) =
  4.21783e-3, (6.0, 3e-3) = 5.37918e-3 and (20.0, 3e-3) = 4.21783e-3
  within 1e-7, monotone in x / k_s, with ValueError below the x / k_s =
  100.0 floor and on zero inputs.
- Confirm the cf_with_roughness report dicts for the transitional,
  fully-rough and smooth cases above, with exactly the six documented
  keys and fixed per-regime note strings.
- Confirm the blend endpoints: k+ 5.0 returns cf_smooth and k+ 70.0
  returns cf_rough exactly (within 1e-15), monotone between.
- Confirm the trip verdicts: re_k 1218.23 True, 121.823 False and the
  inclusive boundary at re_k = 600.0 True.
- Confirm every non-physical input raises ValueError: non-positive re_x,
  k_s_plus, u_inf, cf, rho, u_tau, mu, x, u, k, nu and re_k_crit.
- Run the contract test offline: python3
  scripts/test_rough_wall_skin_friction.py (30 tests, deterministic).

## Related leaves

- aerodynamics/boundary-layer/boundary-layer-theory: the smooth flat
  plate thickness and friction correlations that supply the smooth-wall
  baseline anchor of step 2; it takes no roughness-height input.
- aerodynamics/boundary-layer/boundary-layer-transition: natural
  transition prediction on a clean surface, the complementary question
  to the trip test when the surface is smooth.
- aerodynamics/boundary-layer/boundary-layer-separation: Thwaites and
  Stratford separation criteria for the same boundary-layer family, no
  friction coefficient.
- aerodynamics/high-speed/flat-plate-skin-friction-heating: the
  high-speed smooth-wall friction and heating counterpart; use it when
  the flow is compressible.
- aerodynamics/drag-polars/parasite-drag: the smooth-surface drag
  buildup that can consume the rough coefficient as the component Cf in
  a full-aircraft buildup.

## Pitfalls

- Calling a surface smooth from the sand-roughness height alone: the
  regime depends on k+, not on k_s; at the worked example the 0.3 mm
  grain is transitional (k+ 42.7) while the same grain at low speed or
  short fetch can be hydraulically smooth.
- Applying the fully-rough-cf correlation at a short fetch: below x / k_s
  = 100.0 the correlation saturates to unphysical values and the module
  rejects the input.
- Reading cf_used as the converged rough value when the baseline is
  smooth: the single-pass sequence never iterates, so in the smooth
  regime cf_rough_or_iterated is simply the smooth-wall baseline with
  the roughness hydraulically inactive.
- Treating the trip test as an onset location: the trip criterion is a
  threshold verdict on re_k, not a transition-onset distance; scatter in
  the actual onset is out of scope for this deterministic core.
- Mixing the regime thresholds: the transitional band is inclusive at
  both ends, k+ 5.0 and 70.0, and the blend is anchored exactly there.
- Sizing a trip strip with the roughness Reynolds of the surface grain
  instead of the element: the trip test uses the element height k in
  u * k / nu against the 600 critical value.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rough_wall_skin_friction.py

The test covers the module constants, the step-2 smooth-wall baseline
anchor and its monotone Reynolds scaling, the step-3 friction velocity
anchor and closed form, the step-4 sand-roughness reynolds anchors and
the 10x height linearity identity, the step-5 k-plus-regime boundary
classifications, the step-6 fully-rough-cf anchors across three fetches
and the fetch-ratio floor, the step-7 transitional, fully-rough and
smooth report dicts with the exact six keys, determinism and fixed note
strings, the blend endpoint identities at k+ 5.0 and 70.0 with monotone
mid-band behavior, the step-8 trip-criterion anchors with the inclusive
600 boundary and the default critical constant, and ValueError rejection
of every non-physical input class. 30 tests, deterministic, exits 0.

## Compliance

- Standards referenced, not reproduced: NACA-TR-824 provides the
  classical boundary-layer context for the skin-friction and roughness
  correlations; the relations above are standard engineering
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
