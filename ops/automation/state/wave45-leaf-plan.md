# Wave-45 leaf plan (ops manager, 12 probe receipts: 9 primary + 3 extension)

RECEIPTS OVER LISTS: all 15 planned leaves come from FRESH whole-family probe
receipts at HEAD 5cc8fef3 (zero-owner greps + sibling fence reads + standards
id grep + corpus demand checks), NOT a candidate list. Primary probe batch
deleg_5e0653e2 (5 agents: avionics, flight-mechanics, systems-engineering-
safety, propulsion, manufacturing-quality) + deleg_b57a8f5d (4 agents:
flight-test-operations, gnc-autonomy, space-systems, aerodynamics) completed
2026-09-07 ~10:50 CEST, receipts in wave45-recon/task-{0..8}-receipt.md.
Extension probe batch deleg_8afbc3ee (3 agents: vehicle-design, structures,
cross-cutting) dispatched per the brief decision rule: the primary pool of 12
carried 3 conditional items (vmcl spec-triage vs wave-44 no-Vmcl note,
mangler LOW confidence, ionospheric pool-conditional), so the viable pool sat
below ~12 at spec-time risk; extension restored it to 15. Extension receipts
in wave45-recon/task-{9,10,11}-receipt.md (vehicle-design NO_CANDIDATES with
receipts, structures +2, cross-cutting +1).

## Planned leaves (15), smallest-family order, probe receipts cited

1. avionics/fsw/deadline-monotonic-scheduling
   (AV 47; probe task-0 rank 1: fixed-priority schedulability with per-task
   relative deadlines D_i != T_i: deadline-monotonic priority order (shorter
   deadline higher priority), exact iterative response-time analysis R_i <=
   D_i for constrained (D <= T) and arbitrary (D > T) deadlines, optional
   release-jitter term in the fixed-point iteration; real-time-scheduling is
   the classic implicit-deadline periodic model and fences "arbitrary-deadline
   response-time extensions" out (quoted, lines 69-73/190-192);
   shared-resource-access-control is PCP blocking only; aperiodic-server-
   scheduling requires implicit deadlines; Leung-Whitehead 1982 DM optimality,
   Audsley-Burns-Richardson-Wellings 1993 RTA, Tindell-Clark 1994 jitter;
   do-178c ref-only (fsw convention); spec caveat: prune generic
   schedulability/fixed-priority/response-time tags, add fence line to
   real-time-scheduling)
2. propulsion/electric/mpd-thruster
   (PROP 48; probe task-3 GO-1: self-field magnetoplasmadynamic steady
   operating point: T = (mu0/(4 pi))*J^2*ln(r_a/r_c) current-squared thrust
   law, exhaust velocity and Isp from mass flow, jet power P_j = T^2/(2 m_dot),
   documented reference-only thrust-to-power band verdict; hall-thruster is
   crossed-field electrostatic (quoted), electrothermal-thruster heats
   propellant only (quoted), gridded-ion electrostatic grids; Jahn 1968,
   Sutton electric-propulsion chapter; ecss; corpus queries carry mpd-thruster/
   magnetoplasmadynamic-thruster/self-field tokens)
3. propulsion/rocket/hydrazine-monopropellant-thruster
   (PROP 48; probe task-3 GO-2: catalytic decomposition energy balance
   N2H4 -> (4/3)NH3 + (1/3)N2 exothermic with endothermic ammonia dissociation
   at documented dissociation-fraction input, chamber temperature, isentropic
   nozzle expansion to exhaust velocity and vacuum Isp, decomposition-T and
   impulse bands reference-only; cold-gas-thruster scopes inert gas and defers
   hydrazine (quoted), rocket-engine-cycle is feed system only (quoted),
   electrothermal-thruster is electric heat only; Sutton monopropellant
   section, NASA hydrazine monographs; ecss; tokens
   hydrazine-monopropellant-thruster/catalytic-decomposition/ammonia-
   dissociation)
4. flight-test-operations/envelope/vmcl-determination
   (FTO 48; probe task-5 GO-1: approach-and-landing minimum control speed
   per FAR/CS 25.149(f) summary-only: asymmetric yawing moment from the
   critical-engine cut in the landing config with go-around thrust, rudder-
   authority and 150 lbf pedal-force limited speeds, bank-5-deg and
   20-degree-heading run classification, VMCL-2 second-cut leg 25.149(g) for
   3+ engines; vmc-determination owns the AIR takeoff-config leg only (body
   verified: zero approach/landing/VMCL content), vmcg-determination the
   GROUND leg, vmu 25.107 rotation; wave-44 "do NOT also build Vmcl" was scope
   discipline (one VMC leaf in that wave), not a dead-end - no rationale on
   the record, no fence in any sibling body; far-25 + cs-25. SPEC-TIME TRIAGE:
   reuse the shared yaw-balance closed-form core from vmc/vmcg-determination,
   do not duplicate; tokens vmcl-determination/landing-minimum-control-speed/
   go-around-thrust/critical-engine-cut, NEVER bare minimum-control-speed/vmc
   (FTO-3762 steal lesson))
5. gnc-autonomy/optimal-control/loop-transfer-recovery
   (GNC 52; probe task-6 GO-1: output-side LQG loop-transfer recovery by
   inflating the filter noise weight Q = Q0 + q^2*B*B^T and re-solving the
   filter ARE per q until the recovered loop matches the full-state target
   loop; lqg-design Pitfalls: "shaping the loop gain toward full-state
   recovery is not implemented in this leaf" (quoted); Doyle-Stein 1981,
   Maciejowski ch 5; arp4754a; sim-verified Hit@1 both queries, 0 theft)
6. gnc-autonomy/control/l1-adaptive-control
   (GNC 52; probe task-6 GO-2: L1 adaptive control for a first-order plant:
   state predictor x_hat_dot = a_m x_hat + b(u + sigma_hat), projection-based
   adaptation, low-pass filter C(s) = omega_c/(s + omega_c) on the adaptive
   signal; adaptive-control owns first-order MRAC only (quoted), no L1
   anywhere; Cao-Hovakimyan 2010; arp4754a; sim-verified Hit@1 both queries)
7. gnc-autonomy/estimation-filtering/cramer-rao-lower-bound
   (GNC 52; probe task-6 GO-3: Fisher information I(theta) =
   -E[d^2 ln p/d theta^2] and CRLB var >= 1/I, vector form I^-1, DC-level-in-
   WGN equality var >= sigma^2/N; zero-owner tree-wide (only cramer hit is
   Cramer's rule in torsion-shear-flow), UKF owns NEES post-hoc metric not the
   pre-data bound (quoted); Kay 1993 ch 3, Van Trees 1968; arp4754a;
   sim-verified Hit@1 both queries)
8. gnc-autonomy/navigation/ionospheric-delay-correction
   (GNC 52; probe task-6 GO-4 CONDITIONAL: Klobuchar broadcast delay model:
   pierce-point geomagnetic latitude, amplitude/period polynomials from alpha/
   beta coefficients, vertical delay 5e-9 + sum A_n phi_m^n, obliquity factor;
   gnss-carrier-smoothing owns the divergence CHECK not the delay model
   (quoted), gnss-pseudorange-positioning works on given pseudoranges;
   Klobuchar 1987, IS-GPS-200; rtca-do-229. Include ONLY if the plan pool
   needs a 4th gnc leaf at spec time - pool is 15, so this may drop)
9. aerodynamics/aeroelasticity/sears-function-gust-lift
   (AERO 53; probe task-8 GO-1 HIGH: frequency-domain unsteady thin-airfoil
   response to a convected sinusoidal gust: complex Sears function S(k) from
   Bessel J0/J1/Y0/Y1, gain and phase lag vs reduced frequency, unsteady gust
   load vs the 2*pi*rho*V*b*w_g quasi-steady reference, k->0 and large-k
   limits; aeroelastic-gust-response is TIME-DOMAIN indicial discrete gust,
   "apparent-mass and full Theodorsen noncirculatory terms are neglected"
   (quoted), zero frequency/harmonic/sinusoidal content; Sears 1941, BAH
   Aeroelasticity, Fung; far-25 + cs-25; tags sears-function/sinusoidal-gust/
   gust-load-amplitude, never bare sears (sears-haack collision))
10. aerodynamics/boundary-layer/squire-young-profile-drag
    (AERO 53; probe task-8 GO-2 HIGH: profile drag from TE momentum thickness:
    c_d,p = 2*(theta_TE/c)*(U_TE/U_inf)^((H_TE+5)/2), zero-PG reduction to
    Blasius 1.328/sqrt(Re_c); boundary-layer-transition stops at Michel onset,
    boundary-layer-separation stops at separation flag, parasite-drag is
    whole-aircraft CD0 buildup (all quoted), none map TE momentum state to
    drag; Squire-Young 1938 ARC R&M 1838, Schlichting pp 158-162, Coder-
    Maughmer 2015; naca-tr-824; tags squire-young-formula/profile-drag-
    coefficient/trailing-edge-momentum-thickness)
11. aerodynamics/boundary-layer/laminar-far-wake
    (AERO 53; probe task-8 GO-3 MED: 2-D laminar far wake similarity:
    Goldstein 1933 small-defect Gaussian profile, centerline defect x^-1/2,
    half-width x^1/2, wake-momentum-integral drag D = rho*U_inf*integral u1 dy;
    wave-43 reserve item laminar-far-wake-free-shear never built (prior
    GO-quality signal); zero-owner wake tokens (only windtunnel wake-blockage);
    Schlichting wakes chapter, White Viscous Fluid Flow; naca-tr-824; tags
    laminar-far-wake/far-wake-velocity-defect/wake-momentum-integral)
12. aerodynamics/boundary-layer/mangler-axisymmetric-transform
    (AERO 53; probe task-8 GO-4 LOW: Mangler transform of steady laminar BL
    on an axisymmetric body to an equivalent 2-D flow, sharp-cone closed-form
    ratios delta_cone = sqrt(3)*delta_plate, tau_w,cone = sqrt(3)*tau_w,plate
    at equal running length; flat-plate-skin-friction-heating owns the 2-D
    plate station, stagnation-flow-boundary-layer owns the low-speed stagnation
    point (quoted); Schlichting bodies-of-revolution chapter, White Mangler
    section; naca-tr-824. SPEC-TIME TRIAGE: LOW confidence - the wave-42
    van-Driest adjudication shows Cf-producing neighbors fence to
    flat-plate-skin-friction-heating; a boundary sentence consuming sibling Cf
    machinery and outputting only the transform ratios mitigates. Drop if spec
    time shows function dup.)
13. structures/fem/inelastic-column-buckling
    (STRUCT 59; extension probe task-10 GO-1: yield-anchored Johnson parabola
    Euler-Johnson column-strength curve: lambda = K*L/r, transition
    lambda_t = sqrt(2*pi^2*E/F_cy), Johnson arm F_col = F_cy*(1 -
    F_cy*lambda^2/(4*pi^2*E)) below, Euler arm above, P_col = F_col*A, margin,
    regime classification; buckling-analysis computes only the elastic Euler
    arm and hands off "fall back to a Johnson parabola or test data" (quoted,
    lines 119-122), crippling-analysis anchors on LOCAL crippling stress of
    formed sheet "never on the solid-section yield" (quoted); Bruhn column
    chapter, Niu, Timoshenko-Gere, Roark; far-25 + cs-25; tags inelastic-
    column-buckling/johnson-parabola/column-strength-curve/intermediate-
    slenderness)
14. structures/damage-tolerance/walker-forman-crack-growth
    (STRUCT 59; extension probe task-10 GO-2: stress-ratio-affected da/dN:
    Walker equivalent range dK_bar = dK/(1-R)^(1-gamma) and rate
    da/dN = C*(dK_bar)^m; Forman da/dN = C*(dK)^m/((1-R)*K_c - dK) with
    terminal acceleration as K peak approaches K_c; crack-growth is strictly
    Paris constant-amplitude zero R-ratio (quoted), goodman-diagram is S-N
    infinite-life mean stress (quoted, different domain); Walker 1970 ASTM STP
    462, Forman 1967 ASME JBE; far-25 + cs-25 (25.571 frame); tags walker-
    forman-crack-growth/walker-equation/forman-equation/r-ratio-correction/
    kc-limited-growth; add fence line to crack-growth)
15. cross-cutting/numerics/fir-bandpass-bandstop-filter-design
    (CC 55; extension probe task-11 GO-1: linear-phase FIR highpass/bandpass/
    bandstop from the windowed-sinc lowpass prototype: highpass by spectral
    inversion h_hp[n] = delta[n-M] - h_lp[n], bandpass by cosine translation
    h_bp[n] = 2*h_lp[n]*cos(w0*(n-M)), bandstop by inversion of the translated
    bandpass, window weights, unity DC gain, cosine-sum magnitude dB, group
    delay (N-1)/2, direct-form convolution; the filter 2x2 grid's FIR HP/BP/BS
    cell is EMPTY (IIR LP/HP = digital-filter-design, IIR BP/BS =
    bandpass-bandstop-filter-design, FIR LP = fir-filter-design whose logic
    hardwires design_lowpass only, all quoted); Oppenheim-Schafer 8.4,
    Proakis-Manolakis ch 10, Hamming; naca-tr-824 numerics convention; tags
    fir-highpass/bandpass/bandstop-filter-design/spectral-inversion-method/
    frequency-translation-method)

Family spread: avionics +1 (47 -> 48), propulsion +2 (48 -> 50),
flight-test-operations +1 (48 -> 49), gnc-autonomy +4 (52 -> 56),
aerodynamics +4 (53 -> 57), structures +2 (59 -> 61), cross-cutting +1
(55 -> 56). Total 611 -> 626 leaves; SKILL.md 623 -> 638; corpus 1238 -> 1268
(2N = 30); ledger 611 -> 626 rows (612-626).

## Spec-time triage gates (run per leaf before spec dispatch)
- vmcl-determination: reuse the vmc/vmcg shared closed-form core; confirm no
  sibling claims the landing-config leg (verified at plan time: vmc-
  determination body has zero approach/landing/VMCL content). If genuine
  overlap judged, DECLINE and rely on the pool buffer (14 remain).
- mangler-axisymmetric-transform: LOW. If spec time shows function dup with
  flat-plate-skin-friction-heating (Cf-producing fence), DECLINE and rely on
  the buffer.
- ionospheric-delay-correction: CONDITIONAL on pool. Pool is 15; likely
  DROP at spec time to keep the gnc contribution at 3.
- aero GO-1..4 and gnc GO-1..3 and propulsion GO-1..2 and structures GO-1..2
  and avionics GO-1 and FTO GO-1 and cross-cutting GO-1: no known triage risk;
  standard spec discipline applies (anchors FIRST with REAL outputs, desc
  <=1000 chars / <=148 words, no exact-float equality asserts, no generic
  single-word tags, forbidden tokens from the receipt).

## Reserve pool (swap in if a planned leaf fails at spec/build)
- Pool of 15 is above the ~12 viability line even after dropping mangler +
  ionospheric (13). No extension re-probe needed. vehicle-design 55 stays
  closed (NO_CANDIDATES receipt task-9 with per-seam corpus counts);
  flight-mechanics/SES/MQ/space stay closed (NO_CANDIDATES receipts task-1/
  2/4/7).
- Any leaf that survives spec triage but misses a build round queues to
  08:00 UTC 2026-09-08 (never after ~19:30 UTC).

## Declined / closed this wave (probe receipts, honest)
- flight-mechanics 47: NO_CANDIDATES (task-1: all 7 brief-example seams owned
  with quoted fences; 20 declines incl. drift-down map-blocked no far-121 id,
  balked-landing in oei-climb-gradient, propeller-endurance in breguet-
  endurance, hover-ceiling split across FM + FTO owners; wave-43 H-V and
  envelope-limits stays confirmed).
- systems-engineering-safety 47: NO_CANDIDATES (task-2: all six ARP4761A
  process functions present; 16 declines; reliability-prediction-parts-count
  stays CLOSED - no MIL-HDBK-217/Telcordia id).
- manufacturing-quality 48: NO_CANDIDATES (task-4: 26 declines; CMM seam
  standards-map-blocked; only methodically-real near-miss destructive/nested
  GRR declined on design-judgment + zero demand).
- space-systems 52: NO_CANDIDATES (task-7: 18 declines; CCSDS 131.0-B
  map-blocked; slew/coverage/rendezvous cross-owned; frozen-orbit + SGP4
  demand-zero).
- vehicle-design 55: NO_CANDIDATES (task-9 extension: 9 wave-44 declines
  re-verified + 15 fresh declines, all with per-seam corpus counts of 0;
  corpus frozen at 1238 so no demand counter-evidence can exist).
- avionics 47: only deadline-monotonic-scheduling GO; TAWS/GPWS + Mode-S stay
  CLOSED (RTCA-gated); do160 sec 17/18/19/23/26 table-gated; ARINC 629/825/
  CAN map-blocked; UMS/FLS objective-table-gated.
- propulsion: scramjet CLOSED DEFINITIVELY; 12 declines incl. standing
  wave-39/43 set + fresh ramjet-combustor/external-compression-inlet/
  bell-nozzle-contour/ducted-fan compositions.
- FTO: vmcl is the last 25.149 leg; after it the VMC vein closes; 10
  performance/envelope declines.
- gnc: tdoa-positioning CLOSED (acoustic-emission-inspection claims generic
  hyperbolic iterated-LS, quoted); time-differenced-carrier-phase declined
  (doppler sibling steals Hit@1); 10 other declines.
- aerodynamics: 4 GO; 25 declines incl. all standing wave-41/43 closures;
  theodorsen-standalone function-dup; e-N not closed form; colburn analogy
  dup; supersonic-linearized-theory now OWNED by wave-44 ackeret leaf.
- structures: 2 GO; 15 declines; wave-43/44 reserves used and not reopened.
- cross-cutting: 1 GO (fir-band cells); wave-44 13-decline set re-verified +
  16 fresh declines.

## Standards ids (all verified present in standards-map.yaml at prep)
do-178c, ecss, far-25, cs-25, arp4754a, rtca-do-229, naca-tr-824.
(7 ids, all grep-verified 1 hit each at prep. far-33 NOT used this wave.)

## Prep commit scope
state/wave45-leaf-plan.md (this file) + state/wave45-recon/ (12 receipt .md
files task-0..task-11 + extract-probes.py helper). Specs land in
state/wave45-specs/ from spec-engineer agents (CAP <=4 concurrent, compact
write-NOW prompts, anchor script FIRST) and are committed incrementally per
batch (wave-44 crash-safety precedent).
