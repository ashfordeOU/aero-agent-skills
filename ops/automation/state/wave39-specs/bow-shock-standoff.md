# Wave-39 leaf spec: bow-shock-standoff (aerodynamics, high-speed pack)

- Path: skills/aerodynamics/high-speed/bow-shock-standoff/
- Pack: high-speed. Closest siblings: hypersonic-flow (its logic computes
  only force coefficients: rayleigh_pitot_ratio, newtonian_cp,
  sphere_drag_coefficient, cone_axial_force_coefficient; its SKILL body
  mentions the bow shock only as a motivation sentence, no shock-layer
  geometry), oblique-shock (owns the detached-shock criterion theta >
  theta_max only, no standoff distance), aerodynamic-heating (stagnation-
  point flux with nose-radius scaling, no shock-standoff geometry),
  flat-plate-skin-friction-heating, normal-shock, prandtl-meyer. Whole-tree
  greps at prep: "billig" = 0 hits; "standoff" = 0 owning hits. GENUINE
  AERO gap (fresh probe).
- Standards id: naca-tr-824 (reference-only). Ledger Standard: naca-tr-824.
- Family: aerodynamics

## Claim

Estimate the detached bow-shock standoff distance on the stagnation
streamline ahead of a blunt nose at supersonic and hypersonic Mach number:
compute the standoff ratio Delta/R with the classical Billig form
correlations for a sphere (axisymmetric) and a circular cylinder
(two-dimensional) nose at gamma = 1.4, convert the ratio to a physical
standoff distance for a given nose radius, and report the trend checks that
the standoff decreases with Mach and that the cylinder standoff exceeds the
sphere standoff at the same Mach. Produces the standoff ratio, the standoff
distance and the sanity flags that gate blunt-body nose-radius trades and
shock-layer thickness estimates. Does NOT do: hypersonic force coefficients
or modified Newtonian pressure (hypersonic-flow); oblique-shock relations
or the attached-to-detached deflection limit (oblique-shock); normal-shock
jump relations (normal-shock); stagnation-point convective heating
(aerodynamic-heating).

## Model (implement exactly)

Correlations (classical Billig-form standoff correlations for gamma = 1.4,
validity documented for freestream Mach above about 1.5; the ratios grow
without bound as Mach approaches 1 so the leaf documents the validity
floor):
- Sphere: Delta/R = 0.143 * exp(3.24 / M^2).
- Cylinder: Delta/R = 0.386 * exp(4.67 / M^2).

Functions (pure stdlib):
- standoff_ratio(mach, body="sphere") -> float Delta/R; body is "sphere"
  or "cylinder"; ValueError if mach <= 1 (no detached bow shock), or body
  not in ("sphere", "cylinder").
- standoff_distance(mach, radius, body="sphere") -> float Delta in meters;
  ValueError if radius <= 0, mach <= 1, or bad body string.
- standoff_report(mach, radius, body="sphere") -> dict with keys ratio,
  distance, sphere_cylinder_order (bool: cylinder ratio greater than sphere
  ratio at this Mach), decreasing_with_mach (bool: ratio at mach * 1.1 is
  smaller than at mach). ValueErrors as above.
Module constants: SPHERE_COEF = 0.143, SPHERE_EXP = 3.24, CYL_COEF = 0.386,
CYL_EXP = 4.67.

Identity to test: ratio is monotone decreasing in Mach; the cylinder ratio
exceeds the sphere ratio at every Mach above 1; standoff_distance scales
linearly with radius.

## Worked example

- Sphere M = 8: Delta/R = 0.143 * exp(3.24/64) = 0.15043; R = 0.5 m gives
  Delta = 0.0752 m.
- Sphere M = 4: Delta/R = 0.17510.
- Cylinder M = 8: Delta/R = 0.41522.
- Cylinder M = 4: Delta/R = 0.51682.
- Trend: M = 4 cylinder 0.51682 > M = 4 sphere 0.17510; ratio at M = 8 is
  below ratio at M = 4 for both bodies.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds (direct evaluation of the correlation
constants).

## Validation list (contract test must include)

- standoff_ratio sphere M 8 = 0.15043 within 1e-4; sphere M 4 = 0.17510
  within 1e-4.
- standoff_ratio cylinder M 8 = 0.41522 within 1e-4; cylinder M 4 =
  0.51682 within 1e-4.
- standoff_distance with R = 0.5 m at sphere M 8 = 0.0752 m within 1e-4.
- Monotone decrease: ratio(M=6) < ratio(M=4) for both bodies.
- Cylinder ratio greater than sphere ratio at M = 4 and M = 8.
- ValueErrors: mach = 1.0, mach = 0.8, radius 0, radius negative, body
  "wedge".
- Determinism; report dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave39-bow-shock-standoff.yaml)

Query 1 (copy verbatim):
  "estimate the bow-shock-standoff ratio on the stagnation streamline for the sphere nose at mach 8 with the billig-correlation"
  intent: "aerodynamics; sphere detached bow-shock standoff distance ratio"
  expected_skill: "aerodynamics/high-speed/bow-shock-standoff"
Query 2 (copy verbatim):
  "compute the blunt-body shock-layer-thickness standoff distance for the cylinder leading edge at mach 4"
  intent: "aerodynamics; cylinder bow-shock standoff distance"
  expected_skill: "aerodynamics/high-speed/bow-shock-standoff"
Task ids: w39-bow-shock-standoff-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must estimate the detached bow-shock
standoff distance ahead of a blunt nose:" and include the outputs in the
Claim. First tag: bow-shock-standoff. Additional tags ONLY:
billig-correlation, blunt-body-shock-distance, shock-layer-thickness,
stagnation-streamline. NEVER single generic words (shock, standoff,
distance, blunt, nose, hypersonic, supersonic). 50-150 words, <=1000 chars,
no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): modified-newtonian, rayleigh-pitot,
newtonian-cp, sphere-drag, cone-axial-force (hypersonic-flow); theta-beta-m,
deflection-limit, oblique (oblique-shock); sutton-graves, radiation-
equilibrium (aerodynamic-heating); mach-number relations (normal-shock).
