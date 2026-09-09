---
name: continuous-turbulence-gust-loads
description: "Use when you must compute the continuous turbulence gust design loads of an airplane by the power spectral density gust method: build the von Karman or Dryden power spectral density of the vertical gust velocity from the scale of turbulence and the turbulence intensity, form the rigid-aircraft gust response transfer function, multiply into the response power spectral density, integrate to the rms load response and scale to the design limit load factor of the continuous turbulence design criterion, and report the equivalent discrete gust velocity the discrete-gust envelope analysis takes as its input. Produces turbulence PSD and response PSD ordinates, the rms load factor, the design gust loads and the discrete-gust equivalent in SI units. Trigger: continuous turbulence gust loads, von Karman spectrum, Dryden spectrum, gust response transfer function, turbulence PSD, power spectral density gust method, rms load response, continuous turbulence design."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: structures
pack: loads
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: loads
  tags: [continuous-turbulence-gust-loads, von-karman-spectrum, dryden-spectrum, turbulence-psd, gust-response-transfer-function, power-spectral-density-gust-method, rms-load-response, continuous-turbulence-design]
  version: 0.1.0
  author: AeroSkills
---

# Continuous-Turbulence Gust Loads (structures/loads/continuous-turbulence-gust-loads)

Use when the continuous-turbulence design condition of the transport
gust and turbulence loads rules must be evaluated: the von Karman or
Dryden power spectral density of the vertical gust velocity, the
rigid-aircraft heave gust-response transfer function, the response
PSD, the rms-response ratio A, the design limit incremental load
factor and the equivalent discrete-gust velocity handed to the
discrete 1-cosine envelope method. This is the spectral, continuous-
turbulence counterpart of the discrete gust and maneuver case; pair it
with structures/loads/gust-maneuver-loads for the discrete-gust and
V-n envelope side of the same certification loads set.

## Domain quick reference

- Von Karman one-sided vertical-gust velocity PSD (spatial frequency,
  Hoblit convention): Phi_vK(Omega) = sigma_w^2 (L/pi)
  (1 + (8/3)(1.339 L Omega)^2) / (1 + (1.339 L Omega)^2)^(11/6).
- Dryden one-sided vertical-gust velocity PSD, same convention:
  Phi_D(Omega) = sigma_w^2 (L/pi) (1 + 3 (L Omega)^2)
  / (1 + (L Omega)^2)^2. Both share the DC ordinate
  Phi(0) = sigma_w^2 L/pi and integrate (Parseval) to sigma_w^2; von
  Karman decays as Omega^(-5/3) rather than Dryden's Omega^(-2), so it
  carries more high-frequency energy.
- Rigid-aircraft heave gust-response transfer, quasi-steady
  aerodynamics: |H(omega)|^2 = h_inf^2 omega^2 / (omega^2 + K^2), with
  h_inf = rho V S a_lift / (2 W) the frozen-gust gain and
  K = rho V S a_lift / (2 m) the heave-follow rate (vehicle inertia
  and lift-curve slope, not an oscillator transmissibility).
- Rms-response ratio A: A^2 = (1/pi) integral_0^inf |H(V Omega)|^2
  Phi_hat(Omega) dOmega, evaluated by a fixed 16384-panel Simpson
  quadrature in ln(Omega) with analytic tails (Dryden also has an
  exact closed form, A_D^2 = h_inf^2 (3 y_c + 2) / (2 (1 + y_c)^2)).
- Design rule (linear model, continuous-turbulence design condition,
  named by name only): delta_n_limit = U_sigma A,
  n_limit = 1 + delta_n_limit, with U_sigma the limit turbulence
  intensity (true airspeed); the limit increment equals 2.5 times the
  rms response to the 0.4 U_sigma field.
- Equivalent discrete-gust velocity (hand-off): the algebraic
  inversion of the discrete 1-cosine formula,
  U_de_eq = 2 (W/S) delta_n / (rho V_e a_lift K_g), evaluated only to
  report the value the discrete-gust envelope method takes as input.

## Workflow

1. Build the turbulence PSD ordinates with von_karman_psd or
   dryden_psd (or spectrum_psd_ordinates for a grid of spatial
   frequencies) from the scale of turbulence L and sigma_w.
2. Form the rigid-aircraft gust-response parameters with
   rigid_aircraft_response_params (h_inf, K, mass) and, if needed, the
   transfer magnitude squared with gust_response_transfer_squared.
3. Integrate the response PSD to the rms-response ratio A with
   rms_response_ratio (spectrum choice "von-karman" or "dryden"), and
   inspect the response PSD ordinates with response_psd_ordinates.
4. Scale to the rms incremental load factor of a given rms field with
   rms_load_factor_response(sigma_w, a_ratio).
5. Scale to the design limit incremental load factor with
   design_incremental_load_factor(a_ratio, u_sigma) and read off
   n_limit = 1 + delta_n_limit, the continuous-turbulence design
   criterion result.
6. Report the hand-off value with equivalent_discrete_gust_velocity
   (using gust_alleviation_factor internally) for the discrete-gust
   envelope analysis to consume.
7. Run the one-shot continuous_turbulence_report for the full set of
   ordinates, ratios and load factors in a single call.

## Worked example

Typical transport at the VB-class sea-level condition (rho = 1.225
kg/m^3, V = 154.33 m/s, W/S = 4800 Pa, S = 120 m^2, cbar = 3.81 m,
a_lift = 5.7/rad, L = 762 m, U_sigma = 27.432 m/s TAS, no
alleviation):

- Rigid-aircraft response: h_inf = 0.11225096093750002 per (m/s),
  K = 1.1008058860777343 /s, reduced filter corner
  y_c = K L / V = 5.435197856484374.
- Von Karman: A_vK = 0.06000490538363879 per (m/s), response factor
  A/h_inf = 0.5345602824464799, delta_n_limit = 1.6460545644839792,
  n_limit = 2.646054564483979, U_de_eq = 19.063820591364568 m/s EAS
  (about 62.5 fps), with mu_g = 36.79718848898816 and
  k_g = 0.7692087531874008 evaluated inside the inversion.
- Dryden: A_D = 0.0527721846394613 per (m/s), n_limit =
  2.4476465690297022, U_de_eq = 16.765953612441937 m/s EAS (about 55.0
  fps). The von Karman ratio sits 13.705554912291994 percent above the
  Dryden ratio because its spectrum decays more slowly at high
  reduced frequency; both stay below the frozen bound h_inf.
- The continuous-turbulence limit condition (n = 2.65 von Karman) sits
  in the same design band as the discrete VB gust of the sibling
  method (2.4-2.7 class); the equivalent discrete-gust velocities
  (about 62.5 and 55.0 fps EAS) sit just below the 66 fps VB design
  gust, so the discrete condition marginally drives at this point and
  the continuous condition is the second envelope input.

## Verification

Deterministic checks (see the contract test): the Parseval closure of
the normalized von Karman spectrum against its analytic Beta-function
value, the exact Dryden closure and DC-ordinate identity, the Dryden
closed-form response integral against the quadrature, the response
factor small-c and large-c limits, the von-Karman-above-Dryden
ordering with both bounded by h_inf, linear scaling of the rms and
limit load factors, grid convergence of the fixed Simpson quadrature
under panel doubling, determinism of repeated report calls, and
ValueError rejection of non-physical inputs (non-positive or boolean
rho, V, W, S, a_lift, g, L, cbar, U_sigma, sigma_w, delta_n; negative
Omega; a negative or invalid A; an unknown spectrum name; an empty
Omega grid).

## Pitfalls

- Treating the response transfer as an SDOF oscillator
  transmissibility: it is the rigid-AIRCRAFT heave response built from
  vehicle inertia and lift-curve slope, not a test-input acceleration
  PSD response (that machinery belongs to
  structures/loads/random-vibration-analysis, confined to SDOF
  base-excitation equipment screening).
- Claiming the discrete 1-cosine load factor, the gust alleviation
  factor, or the V-n envelope as a product of this leaf: they appear
  here only inside the algebraic inversion that reports the
  equivalent discrete-gust velocity; the discrete method and its
  envelope belong to gust-maneuver-loads.
- Using the published rounded von Karman constant 1.339 and expecting
  the Parseval closure to equal 1.0 exactly: the closure ratio is
  0.9999890060233615 for the rounded constant, exactly 1.0 only for
  the unrounded VK_A_EXACT; assert within 1e-3 of unity, never exact
  equality.
- Mixing the spatial frequency Omega (rad/m, spectrum argument) with
  the encounter circular frequency omega = V Omega (rad/s, transfer
  function argument): rms_response_ratio and
  response_psd_ordinates handle this conversion internally, but a
  direct call to gust_response_transfer_squared needs omega in rad/s.
- Forgetting that A is independent of the turbulence intensity: A
  depends only on the aircraft and spectrum parameters; sigma_w or
  U_sigma scale the response and limit load factor linearly after A
  is computed.
- Feeding an unknown spectrum name or an empty Omega grid: only
  "von-karman" and "dryden" are accepted, and the ordinate functions
  reject an empty grid rather than returning an empty list silently.

## Behavior contract (gate 3)

The behavior contract is
scripts/test_continuous_turbulence_gust_loads.py against
scripts/continuous_turbulence_gust_loads_logic.py (stdlib unittest,
offline, deterministic). Run:

python3 scripts/test_continuous_turbulence_gust_loads.py

It asserts: the worked-example rms-response ratios, h_inf, K, y_c and
design limit load factors for both spectra within 1e-6 relative; the
equivalent discrete-gust velocity hand-off and the one-shot report key
set; the von Karman turbulence PSD and response PSD ordinates at the
default Omega grid within 1e-6 relative; the shared DC ordinate of
both spectra; the Parseval closures (von Karman within 1e-3 of unity
for the rounded constant, Dryden within 1e-6 of exact unity) checked
against their analytic values, never by exact-float equality; the
Dryden closed-form identity and its response-factor limits; the
von-Karman-above-Dryden ordering and the frozen bound; linear scaling
of the rms and limit load factors including the 2.5x quotient at the
0.4 U_sigma field; grid convergence under panel doubling and
determinism of the one-shot report; and ValueError rejection of every
non-physical input with the real message prefixes.

## Related leaves

- structures/loads/gust-maneuver-loads: owns the discrete 1-cosine
  gust load factor, the gust alleviation factor and the V-n envelope;
  this leaf's equivalent discrete-gust velocity is the reported
  hand-off value that envelope analysis takes as input.
- structures/loads/random-vibration-analysis: the SDOF base-excitation
  equipment-qualification response (transmissibility, Miles equation,
  g-rms screening), disjoint from this leaf's rigid-aircraft
  continuous-turbulence gust response.
- aerodynamics/aeroelasticity/aeroelastic-gust-response: the flexible
  typical-section time-domain response to a discrete gust
  (Wagner/Kussner indicial states), distinct from this leaf's rigid
  closed-form spectral method.
- aerodynamics/aeroelasticity/sears-function-gust-lift: the
  single-frequency Sears function gust gain and phase of a rigid
  airfoil section; this leaf is the spectral, continuous-turbulence
  implementer that leaf's Related leaves section names as the PSD
  machinery home.

## Compliance

- Standards: far-25 and cs-25, both reference-only (STANDARDS-REF),
  gated: false. The continuous-turbulence design condition of 14 CFR
  25.341(b) and CS 25.341(b) is referenced by name only, never
  reproduced; FAA AC 25.341-1 is named as method context only.
- The von Karman and Dryden spectrum relations, the heave transfer
  function and the design rule are standard published methodology
  (Hoblit, Gust Loads on Aircraft); no verbatim regulation text, no
  proprietary tables, no test data.
