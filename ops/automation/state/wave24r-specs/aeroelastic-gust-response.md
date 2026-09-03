# Wave-24R leaf spec: aeroelastic-gust-response (aerodynamics)

- Path: skills/aerodynamics/aeroelasticity/aeroelastic-gust-response/
- Pack: aeroelasticity (existing: divergence-speed,
  flutter-speed-prediction)
- Standards ids: far-25, cs-25  (Ledger Standard: far-25, cs-25)
- Family: aerodynamics

## Claim

Dynamic aeroelastic response of a two-degree-of-freedom typical wing
section to a sharp-edge or discrete gust using indicial (Wagner and
Kussner) unsteady aerodynamics: compute the gust-induced lift and the
plunge/pitch response time history, the dynamic magnification factor of
the peak response relative to the quasi-steady value, and the peak load
verdict against a supplied limit. Produces the response history, the
magnification factor, and the peak-load margin.

Does NOT do: the FAR discrete-gust rigid load-factor method with the
gust alleviation factor and the V-n gust lines
(structures/loads/gust-maneuver-loads owns that certification load
case), flutter speed search (flutter-speed-prediction owns the V-g
method), static divergence (divergence-speed). This leaf is the DYNAMIC
(unsteady indicial) gust RESPONSE of the flexible section, not the rigid
load factor.

## Model (implement exactly)

Typical section: plunge h (positive down, m), pitch theta (rad, nose
up), elastic axis at a fraction of the chord; section mass per span m_s
(kg/m), pitch inertia I_theta (kg m^2/m? use per unit span), plunge
stiffness k_h (N/m per span... use per unit span values consistently),
pitch stiffness k_theta, structural damping ignored (assumption
documented) or small viscous terms optional (keep it undamped for the
anchors, documented).

Indicial aerodynamics (incompressible, Wagner function for the
angle-of-attack response and Kussner function for the gust penetration;
module constants for the two-term exponential approximations):
- Wagner: phi_w(s) = 1 - A1*exp(-b1*s) - A2*exp(-b2*s) with A1 = 0.165,
  b1 = 0.0455, A2 = 0.335, b2 = 0.3 (R.T. Jones approximation, s =
  reduced time = 2*V*t/c).
- Kussner: phi_k(s) = 1 - A1k*exp(-b1k*s) - A2k*exp(-b2k*s) with A1k =
  0.5, b1k = 0.13, A2k = 0.5, b2k = 1.0 (classical two-term
  approximation).
Unsteady lift (incompressible, thin airfoil, per unit span):
- L(s) = 2*pi*rho*V^2*b*[ theta_eff + ... ] implement the Duhamel form:
  L = 2*pi*rho*V*b*( V*theta + h_dot? sign conventions... ) Use the
  standard Duhamel superposition for a step change in effective angle
  of attack:
    L(s) = 2*pi*rho*V^2*b * ( alpha_eff(0)*phi_w(s) +
    integral_0^s phi_w(s-sigma) d(alpha_eff) )
  with the effective angle from the section motion and the gust:
    alpha_eff = theta + h_dot/V + alpha_g(s)  (sign conventions
    documented; h positive down reduces incidence for the usual
    convention: use alpha_eff = theta - h_dot/V + alpha_g if that is
    your documented convention - pick one and be consistent).
  Implement the Duhamel integral numerically with the exponential
  approximation via the state-space (indicial) formulation:
    x1_dot = -b1*(2V/c)*x1 + alpha_eff_dot? -- OR use the simpler
    exact-integration approach: with the two-term exponential
    approximation, augment the state with two lag states per Wagner
    term and integrate with RK4 over the gust encounter. Prefer the
    lag-state formulation (cleaner, deterministic):
      lift lag states x_w1, x_w2 with
      x_wi_dot = -b_i*(2V/c)*x_wi + alpha_eff_dot  (per term)
      L = 2*pi*rho*V^2*b*[ A0*alpha_eff + A1*x_w1 + A2*x_w2 ] with
      A0 = 1 - A1 - A2 = 0.5? NO: Wagner at s=0 is 0.5 and at infinity
      1.0, so the Jones coefficients with phi(0) = 1 - 0.165 - 0.335 =
      0.5. In the lag form L = 2*pi*rho*V^2*b*[ phi(inf)*alpha_eff -
      (A1*(alpha_eff - x_w1) + A2*(alpha_eff - x_w2)) ] = ...
      Implement the textbook lag-state form and VERIFY the limiting
      behavior: for a step alpha_eff the lift starts at half the
      quasi-steady value and approaches the full quasi-steady value;
      assert that in the tests.
Gust model: discrete one-minus-cosine gust (sharp-edge optional):
- alpha_g(s) = (w_g/V) * (1 - cos(2*pi*s/s_g))/2 for 0 <= s <= s_g,
  0 after, where w_g is the gust velocity (m/s) and s_g the gust
  gradient in reduced time (s_g = 2*V*H/c with H the gust gradient
  length, default 12.5*mean chord? use H input in m); the Kussner
  function smooths the penetration: in the lift the gust angle enters
  through the Kussner indicial response - for the simplified model use
  the Kussner lag states driven by alpha_g with the same lag-state
  machinery and A1k/A2k/b1k/b2k, and note the assumption (gust
  penetration modeled by the Kussner function rather than a streamwise
  integration).
Equations of motion (per unit span):
- m_s*h_ddot + k_h*h = -L (sign per convention)
- I_theta*theta_ddot + k_theta*theta = M_ea (pitch moment about the
  elastic axis; include the standard moment from the lift at the
  aerodynamic center offset and the pitch-damping term; keep the model
  at the level of: M_ea = L*(0.25 - e)*c? with e the elastic-axis
  fraction; document).
- Integrate with RK4 dt (reduced-time or real time, be consistent).
Outputs:
- Response history h(t), theta(t), L(t).
- Quasi-steady reference: L_qs_peak = the lift from the peak gust angle
  applied quasi-steadily.
- Dynamic magnification factor DMF = peak(|L(t)|)/L_qs_peak (or the
  peak response ratio; document which).
- Peak-load verdict: compare the peak L (or peak h) against the input
  limit.
Functions:
- wagner_coefficients(), kussner_coefficients()
- gust_angle_time(w_g, s_g, s) -> alpha_g at reduced time s
- lag_state_derivatives(...)
- gust_response_history(params, w_g, H, dt_real, t_max) -> histories
- quasi_steady_peak_lift(...)
- dynamic_magnification_factor(...)
- peak_load_verdict(peak, limit) -> (PASS/FAIL, margin)
ValueError on: V <= 0, c <= 0, non-positive stiffness/mass/inertia,
w_g < 0, H <= 0, non-finite inputs.
Anchors to verify (assert with your real outputs):
- Step response: apply a step in alpha_eff with no gust: initial lift is
  about 0.5 of the quasi-steady value and it converges to the full value
  (assert within a few percent over a long time).
- For a sharp-edge gust (large s_g effectively... use the one-minus-
  cosine with a long gradient so the response approaches the quasi-
  steady peak; DMF approaches 1.0 from below or modestly above for a
  lightly damped section; assert the DMF band you compute and report it).
- With a short gust gradient the DMF is larger than with a long gradient
  (assert monotonic trend across two gradients).
- Peak-load verdict triggers FAIL when the limit is below the computed
  peak.
Keep the worked example parameters in the SKILL body concrete (choose a
typical-section representation of a transport wing: c = 2 m? per-unit-
span values m_s = 300 kg/m, I_theta = 40 kg m^2/m? k_h, k_theta chosen
so the uncoupled plunge and pitch frequencies are ~ 2 Hz and ~ 5 Hz,
V = 100 m/s, rho = 1.225, w_g = 15 m/s, H = 25 m; report your computed
DMF and peak load).

## Corpus tasks (2 tasks, ids w24r-aeroelastic-gust-response-1/2)

Distinctive tokens: aeroelastic-gust-response, dynamic-gust-response,
kussner-function, wagner-function, indicial aerodynamics, dynamic
magnification factor, typical-section gust. FORBIDDEN (they belong to
the rigid-loads sibling): "gust alleviation factor", "one-cosine
discrete gust", "v-n diagram", "gust lines", "vb vc vd", "far 25.341".

1. "compute the dynamic aeroelastic gust response of the typical wing
   section with the Kussner and Wagner indicial functions: run the
   lag-state unsteady lift model for the one-minus-cosine gust and
   report the dynamic magnification factor of the peak lift over the
   quasi-steady value"
2. "evaluate the flexible wing section response to a sharp gust input in
   the time domain with the two-term exponential indicial
   approximations and check the peak load against the limit, reporting
   the margin"

## SKILL body notes

Pair with flutter-speed-prediction (same typical-section machinery,
different question: stability vs response), divergence-speed, and the
rigid discrete-gust loads leaf in structures. Document every convention
(h positive down, reduced time, Duhamel/lag-state equivalence, Kussner
as the penetration model). Worked example uses your concrete parameter
set with the real outputs quoted.
