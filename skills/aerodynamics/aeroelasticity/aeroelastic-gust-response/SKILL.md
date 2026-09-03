---
name: aeroelastic-gust-response
description: "Use when you must compute the dynamic aeroelastic response of a flexible two-degree-of-freedom typical wing section to a discrete gust with indicial unsteady aerodynamics: run the Wagner and Kussner lag-state lift model in the time domain, produce the plunge and pitch response histories for a one-minus-cosine gust, and report the dynamic magnification factor of the peak lift over the quasi-steady value plus the peak-load verdict against a limit. Produces response histories, the dynamic magnification factor, and load margin. Trigger: aeroelastic gust response, dynamic gust response, kussner function, wagner function, indicial aerodynamics, dynamic magnification factor, typical section gust, gust response history."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: aerodynamics
pack: aeroelasticity
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: aeroelasticity
  tags: [aeroelastic-gust-response, dynamic-gust-response, kussner-function, wagner-function, indicial-aerodynamics, dynamic-magnification-factor, typical-section-gust, unsteady-aerodynamics, gust-response-history]
  version: 0.1.0
  author: AeroSkills
---

# Aeroelastic Gust Response (aerodynamics/aeroelasticity/aeroelastic-gust-response)

Use when the task is the DYNAMIC response of a flexible two-degree-of-freedom
typical wing section to a discrete gust: the plunge and pitch time histories
driven by the unsteady (indicial) aerodynamic lift, the dynamic magnification
factor of the peak lift over the quasi-steady value, and the peak-load
verdict against a limit. This leaf is the flexible-section RESPONSE problem,
distinct from the rigid discrete-gust certification load case
(structures/loads/gust-maneuver-loads owns that load method), from the flutter speed search (flutter-speed-prediction
owns the V-g method), and from static divergence (divergence-speed). The
model pairs with flutter-speed-prediction: the same typical-section
machinery, a different question (stability there, forced response here).

## Domain quick reference

- Typical section: plunge h (positive DOWN, m), pitch theta (positive
  nose-up, rad) about an elastic axis at fraction e of the chord from the
  leading edge; per-unit-span mass m_s (kg/m), pitch inertia I_theta
  (kg m^2/m), plunge stiffness k_h (N/m), pitch stiffness k_theta
  (N m/rad), structural damping ignored. Reduced time s = 2*V*t/c with
  semi-chord b = c/2.
- Sign conventions: lift L is positive UPWARD (conventional lift) and the
  plunge equation is m_s*h_ddot + k_h*h = -L; an upward gust therefore
  accelerates the section upward, the physically correct direction. A
  section moving down (h_dot > 0) sees an upwash, so the effective angle at
  the three-quarter chord is alpha_m = theta + h_dot/V +
  (0.75 - e)*c*theta_dot/V; the +h_dot/V term is what gives the standard
  plunge damping. The nose-up moment about the elastic axis from the lift at
  the quarter-chord aerodynamic center is M_ea = -L*(0.25 - e)*c: for e <
  0.25 (elastic axis forward of the aerodynamic center, statically stable)
  an upward lift produces a restoring nose-down moment.
- Indicial (Duhamel) aerodynamics in lag-state form, incompressible thin
  airfoil: the motion angle alpha_m enters through the Wagner function
  phi_w(s) = 1 - A1*exp(-b1*s) - A2*exp(-b2*s) with the R.T. Jones
  two-term coefficients A1 = 0.165, b1 = 0.0455, A2 = 0.335, b2 = 0.3, and
  the gust angle alpha_g through the Kussner function phi_k(s) =
  1 - A1k*exp(-b1k*s) - A2k*exp(-b2k*s) with A1k = 0.5, b1k = 0.13, A2k =
  0.5, b2k = 1.0. The Kussner channel models streamwise gust penetration;
  apparent-mass and full Theodorsen noncirculatory terms are neglected at
  this level (documented assumption). phi_w(0) = 0.5 and phi_k(0) = 0: a
  step in alpha_m starts at half the quasi-steady lift, a sharp-edge gust
  starts at zero.
- Lag-state form: filtered states x1, x2 (Wagner, driven by alpha_m) and
  xk1, xk2 (Kussner, driven by alpha_g) follow x_dot = (2*V/c)*b_i*
  (alpha - x) per term, and the lift per unit span is L = 2*pi*rho*V^2*b*
  [(1 - A1 - A2)*alpha_m + A1*x1 + A2*x2 + (1 - A1k - A2k)*alpha_g +
  A1k*xk1 + A2k*xk2].
- Gust: one-minus-cosine vertical gust w_g (m/s, upward positive) with
  gradient length H (m), alpha_g(s) = (w_g/V)*(1 - cos(2*pi*s/s_g))/2 over
  0 <= s <= s_g, s_g = 2*H/c in reduced time, zero after. A sharp-edge gust
  is the short-gradient limit.
- Equations of motion (per unit span, RK4 in real time):
  m_s*h_ddot + k_h*h = -L and I_theta*theta_ddot + k_theta*theta = M_ea.
- Quasi-steady reference: L_qs = 2*pi*rho*V*b*w_g, the lift the peak gust
  angle w_g/V would produce on the rigid section. Dynamic magnification
  factor DMF = peak(|L(t)|)/L_qs over the encounter history.
- Quasi-static flexible reference: with q = (0.25 - e)*c*2*pi*rho*V^2*b/
  k_theta, the static aeroelastic peak lift is L_qs/(1 + q). For e = 0.2
  and the worked-example stiffness, q = 0.195 so L_qs_flex = 0.837*L_qs:
  a forward elastic axis gives static aeroelastic load relief, and a very
  long gust gradient approaches that ratio, not unity. Putting the elastic
  axis at the aerodynamic center (e = 0.25, q = 0) removes the relief and
  the long-gradient DMF approaches 1.0.
- Metric direction: for this flexible-section lift response the DMF rises
  monotonically with gradient length toward the quasi-static value; the
  shortest gradients give the smallest DMF because the section recoils and
  the gust is over before the structural response peaks. This is the
  opposite trend of the rigid discrete-gust load-factor method in the
  structures loads family, whose alleviation treatment belongs to that
  leaf, not here.
- FAR 25 and CS 25 gust-load rules frame the certification gust context;
  the relations above are standard engineering methodology, summary-only,
  no standard text reproduced.

## Workflow

1. Set the section: V, c, rho, m_s, I_theta, k_h, k_theta, e (elastic axis
   fraction from the leading edge, 0 to 1) in a params dict; the module
   checks every non-positive mass, inertia, stiffness, speed, chord and
   non-finite input with a ValueError. Choose k_h = m_s*(2*pi*f_h)^2 and
   k_theta = I_theta*(2*pi*f_theta)^2 for the target uncoupled plunge and
   pitch frequencies.
2. Confirm the indicial coefficients with wagner_coefficients() and
   kussner_coefficients() (module constants, R.T. Jones and classical
   two-term values).
3. Set the gust: w_g (m/s, upward positive), gradient length H (m). The
   gradient reduced time follows as s_g = 2*H/c. The gust angle at any
   reduced time s is gust_angle_time(w_g, V, s_g, s).
4. Integrate: gust_response_history(params, w_g, H, dt_real, t_max)
   returns the t, s, h, h_dot, theta, theta_dot, lift, alpha_gust and
   alpha_motion histories plus the peak absolute lift and its time. Use a
   dt small enough to resolve the pitch mode (about 5e-4 s for the worked
   example) and a t_max long enough for the structural settling, 2.5 s or
   more.
5. Reference: quasi_steady_peak_lift(rho, V, c, w_g) gives the rigid
   quasi-steady peak L_qs; dynamic_magnification_factor(peak_lift, L_qs)
   gives the DMF.
6. Check the peak load: peak_load_verdict(peak_lift, limit) returns the
   verdict PASS or FAIL and the fractional margin limit/peak - 1, negative
   when the limit is exceeded.
7. Sanity checks: a step in effective angle with no gust must start at
   about 0.5 of the quasi-steady lift (Wagner phi(0) = 0.5) and converge
   to the full value; the long-gradient DMF must approach the quasi-static
   flexible ratio; confirm with the contract test.

## Worked example

Transport-wing typical section: c = 2 m, m_s = 300 kg/m, I_theta = 40
kg m^2/m, elastic axis e = 0.2 (20 percent chord), k_h = 47374 N/m
(uncoupled plunge 2.0 Hz), k_theta = 39478 N m/rad (uncoupled pitch 5.0
Hz), V = 100 m/s, rho = 1.225 kg/m^3, gust w_g = 15 m/s, H = 25 m
(s_g = 25, gust duration 0.25 s).

- Rigid quasi-steady peak: L_qs = 2*pi*rho*V*b*w_g = 11545 N/m.
- Response: peak |L| = 6901 N/m at t = 0.135 s, inside the gust. The
  dynamic magnification factor is DMF = 6901/11545 = 0.598. The section
  recoils against the gust (upward plunge velocity subtracts from the
  incidence) so the flexible peak sits below the rigid quasi-steady value.
- Quasi-static flexible peak: L_qs/(1 + q) with q = (0.25 - 0.2)*2*
  2*pi*1.225*1e4*1/39478 = 0.195 gives 0.837*11545 = 9662 N/m. A much
  longer gradient H = 200 m gives DMF = 0.830, approaching that ratio; the
  residual difference is the penetration and structural lag. With the
  elastic axis at the aerodynamic center (e = 0.25) the same long gradient
  gives DMF = 0.987, approaching 1.0, confirming the aerodynamics alone
  tend to the quasi-steady peak.
- Short gradient H = 2 m (near sharp edge) gives DMF = 0.320: the DMF
  rises monotonically with gradient length for this flexible section,
  documented above.
- Peak-load verdict at H = 25 m: against a limit of 8 kN/m the peak
  6901 N/m PASSes with margin +15.9 percent; against 6.5 kN/m it FAILs
  with margin -5.8 percent.

## Verification

- Confirm a step in effective angle with no gust starts at 0.5 of the
  quasi-steady lift and converges to the full value within a few percent
  (test_lag_state_step_* methods assert ratios 0.5 -> 1.0 against the
  closed-form Wagner function).
- Confirm the worked-example run returns peak |L| = 6901 N/m and
  DMF = 0.598 at H = 25 m, and that the long-gradient DMF (H = 200 m) sits
  in [0.78, 0.88], the e = 0.25 variant in [0.93, 1.05], and DMF(2 m) <
  DMF(25 m) < DMF(200 m).
- Confirm peak_load_verdict returns FAIL with a negative margin when the
  limit is below the computed peak.
- Confirm ValueError rejection of non-positive V, c, rho, m_s, I_theta,
  k_h, k_theta, H, dt and t_max, negative w_g, elastic axis outside
  [0, 1], missing parameter keys and non-finite inputs.
- Run the contract test offline: python3
  scripts/test_aeroelastic_gust_response.py (35 tests, deterministic,
  under 1 s).

## Related leaves

- aerodynamics/aeroelasticity/flutter-speed-prediction: the stability
  counterpart of this leaf, V-g flutter speed of the same typical section.
- aerodynamics/aeroelasticity/divergence-speed: static divergence of a
  section whose elastic axis lies aft of the aerodynamic center.
- structures/loads/gust-maneuver-loads: the rigid discrete-gust
  certification load factor method, the other half of the gust-loads
  story.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_aeroelastic_gust_response.py

The test covers the indicial coefficient values, the Wagner step-response
limits (0.5 at s = 0, unity at large s) and Kussner sharp-edge limits
(zero at s = 0, unity at large s), the one-minus-cosine gust angle shape
and peak, the lag-state step anchor (initial lift about 0.5 of the
quasi-steady value, convergence to the full value, match to the closed
form), the fully developed lift kernel and the zero-start gust channel,
the quasi-steady peak lift formula, the dynamic magnification factor, the
peak-load verdict PASS/FAIL/margin logic, the worked-example peak and DMF,
the long-gradient bands, the monotonic DMF trend with gradient length,
quiescence with no gust, linear scaling with gust velocity, and ValueError
rejection of every non-physical input class.

## Compliance

- Standards referenced, not reproduced: the FAR 25 and CS 25 gust-load
  rules frame the certification context; the indicial aerodynamics and
  typical-section relations above are standard engineering methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
