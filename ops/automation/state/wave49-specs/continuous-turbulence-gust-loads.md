# Wave-49 leaf spec: continuous-turbulence-gust-loads (structures, loads pack)

- Path: skills/structures/loads/continuous-turbulence-gust-loads/
- Pack: structures/loads (4 leaves present at this HEAD:
  gust-maneuver-loads, landing-ground-loads, random-vibration-analysis,
  shock-response-spectrum). Wave-49 probe receipt task-2 rank-2 GO
  (CONDITIONAL), the structures GO 2 of the wave-49 reduced wave
  (4-leaf pool, CEO-approved); 0 owners verified whole-tree at prep and
  re-verified at spec time: `grep -rilE "von.karman|continuous.
  turbulence|tuned.gust" skills/ --include=SKILL.md` returns ONLY
  skills/structures/fem/plate-buckling/SKILL.md (von Karman
  effective-width constant, unrelated), skills/aerodynamics/boundary-
  layer/boundary-layer-theory/SKILL.md (von Karman momentum integral,
  unrelated) and skills/aerodynamics/aeroelasticity/sears-function-gust-
  lift/SKILL.md (frequency-domain gust lift context only, single
  frequency, not spectral), so no leaf implements a continuous-turbulence
  PSD gust-loads method; the corpus scan of the same vocabulary over
  eval/hit1-corpus.yaml is 0 of 1326 task blocks at this HEAD; and the
  wave-41..48 structures recon and leaf-plan history carries no
  continuous-turbulence adjudication on the structures side (the only
  prior-wave hits are the aerodynamics-side wave-45/46 rows quoted
  below, the wave-45 sears-function spec FORBIDDEN TOKENS, and the gust
  content of the two aerodynamics/aeroelasticity leaves quoted below).
- Claim fences (quoted verbatim from the sibling frontmatter and bodies
  at this HEAD). The CONDITIONAL flag exists because the wave-45/46
  aerodynamics receipts assigned the label "PSD machinery home" to
  random-vibration-analysis, so a reviewer holding that assignment as a
  vein line may decline this GO as same-vein or order an
  extend-random-vibration-analysis; the fences below pre-empt that
  reading point by point:
  - gust-maneuver-loads frontmatter description (line 3 at this HEAD,
    verbatim; bracketed ellipsis elides the trigger-word tail): "Use
    when you must compute aircraft structural loads from gust and
    maneuver conditions per FAR 25.341 and FAR 25.337: discrete 1-cosine
    gust load factor n = 1 + (rho0*V_e*a*K_g*U_de)/(2*W/S), gust
    alleviation factor K_g = 0.88*mu_g/(5.3+mu_g) with mass ratio
    mu_g = 2*(W/S)/(rho*cbar*a*g), limit maneuvering load factor 2.5
    (normal) or 3.8 (commuter/transport) at VA with linear variation to
    0 at VD, V-n diagram construction with the corner point at VA and
    gust lines at VB/VC/VD, envelope verdicts and margin checks.
    Produces the V-n diagram, gust and maneuver load factors, and
    pass/fail envelope margins. [...]" Its body (read in full at this
    HEAD) has NO PSD spectrum content anywhere: the leaf is the DISCRETE
    1-cosine method plus the maneuver envelope; tags (line 16,
    verbatim): gust-loads, maneuver-loads, v-n-diagram, far-25-341,
    far-25-337, load-factor, envelope, discrete-gust, 1-cosine,
    gust-alleviation-factor, mass-ratio, maneuvering-speed, corner-point,
    margin-check, limit-load-factor.
  - random-vibration-analysis frontmatter description (line 3 at this
    HEAD, verbatim; bracketed ellipses elide the transmissibility and
    Miles closed forms in the middle): "Use when you must compute the
    random vibration response of a structure or equipment item to a
    base-input acceleration power spectral density:
    single-degree-of-freedom transmissibility [...] RMS response in g
    from the Miles equation [...] numerical integration of the response
    PSD over a supplied spectrum, 3-sigma peak level, and the equivalent
    static load factor n_eq = 3*sigma for equipment qualification
    screening. Produces response PSD points, g-rms and 3-sigma response
    levels, and screening load factors." Its body (lines 33-37,
    verbatim): "This is the other dynamic loads input alongside discrete
    gust and maneuver loads, feeding the same structural sizing and
    fatigue flows. The response-level model here is deliberately confined
    to SDOF random vibration response; cycle counting and cumulative
    fatigue damage of the vibration response are owned by the fatigue
    pack." The built leaf is SDOF BASE-EXCITATION equipment
    qualification; it never claims aircraft gust loads, has no
    atmospheric turbulence spectrum family, no vehicle inertia or
    lift-curve machinery and no certification framing. The "PSD machinery
    home" label names machinery, not this seam: an SDOF oscillator
    cannot express an aircraft continuous-turbulence gust design load
    (wave-48 conditional pattern, below).
  - The cross-family hand-off that created this seam (verbatim rows of
    the wave-45 and wave-46 aerodynamics receipts, as quoted in the
    wave-49 task-2 receipt): wave-45: "continuous-turbulence PSD gust
    loads (Dryden / von Karman spectra) | Family home is
    structures/loads (random-vibration-analysis and gust-maneuver-loads
    own the PSD load machinery), not aerodynamics section theory";
    wave-46 aerodynamics receipt STANDS re-verify; wave-45
    sears-function spec FORBIDDEN TOKENS: "never dryden-spectrum,
    von-karman-spectrum, power-spectral-density (the structures loads
    family)". The aerodynamics family fences the vocabulary out of
    itself and into structures/loads, but the named home leaves
    implement no such content (their descs verbatim above): the hand-off
    is unfulfilled, the same pattern the wave-48 laminate-bending-
    stiffness GO closed for the D-terms hand-off, and this leaf is where
    it lands.
  - The aerodynamics dynamic-gust identity (on disk at this HEAD),
    aeroelastic-gust-response frontmatter description (lines 25-34,
    verbatim): "Use when the task is the DYNAMIC response of a flexible
    two-degree-of-freedom typical wing section to a discrete gust: the
    plunge and pitch time histories driven by the unsteady (indicial)
    aerodynamic lift, the dynamic magnification factor of the peak lift
    over the quasi-steady value, and the peak-load verdict against a
    limit. This leaf is the flexible-section RESPONSE problem, distinct
    from the rigid discrete-gust certification load case
    (structures/loads/gust-maneuver-loads owns that load method)..."
    Its tags include kussner-function, wagner-function,
    indicial-aerodynamics, dynamic-magnification-factor: discrete
    time-domain flexible dynamics (Wagner/Kussner lag states, RK4
    histories), not a PSD design-loads method and not rigid-vehicle
    loads; disjoint from this leaf as the receipt states.
  - The frequency-domain aerodynamic sibling, sears-function-gust-lift,
    Related leaves (lines 218-220 at this HEAD, verbatim):
    "structures/loads/random-vibration-analysis: the PSD machinery home
    of continuous-turbulence spectral gust content; this leaf is
    single-frequency, not spectral." That line documents the wave-45/46
    assignment in writing; the assigned home, as built, cannot express
    the content (its own desc verbatim above). This leaf is the
    structures/loads implementer the hand-off calls for.
  - Conditional precedent: the wave-47 creep-stress-relaxation and
    wave-48 laminate-bending-stiffness GOs were both flagged CONDITIONAL
    on same-vein suspicions against siblings that could not express the
    seam, and both landed at build with the fences as pre-emption. This
    leaf is the mirror: the flagged vein (PSD response machinery)
    belongs to a sibling (random-vibration-analysis) whose built
    contract is SDOF base-excitation equipment screening and cannot
    express aircraft continuous-turbulence gust design loads.
  - Claim restriction that makes the fence hold: this leaf claims the
    atmospheric-turbulence spectral description (von Karman AND Dryden
    one-sided spectra with the published 1.339 constant and the scale
    input), the rigid-aircraft vertical (heave) gust-response transfer
    function, the response PSD, the rms-response ratio A, the
    design-limit incremental load factor by the linear-model design rule
    of the continuous-turbulence condition and the equivalent
    discrete-gust velocity report. It never offers an SDOF
    transmissibility or Miles product, never builds the discrete 1-cosine
    load factor, the gust alleviation factor or the V-n envelope as
    claimed outputs (gust-maneuver-loads owns those; this leaf evaluates
    only the algebraic inversion of its load-factor formula to report the
    equivalent discrete-gust velocity), and never produces flexible-mode
    or unsteady-aerodynamic response histories (aeroelasticity family).
- Standards id: far-25 (line 16) and cs-25 (line 27), both present in
  standards-map.yaml (grep-verified at spec time), reference-only: the
  exact pair the in-pack loads sibling gust-maneuver-loads carries at
  this HEAD; all STANDARDS-REF, gated false. The leaf is framed by the
  continuous-turbulence design condition of the FAR/CS gust and
  turbulence loads rules (14 CFR 25.341(b) and CS 25.341(b), referenced
  by name only, never reproduced; FAA AC 25.341-1 describes acceptable
  compliance methods and is named as method context only). No new id
  invented. Ledger Standard: far-25 (primary), cs-25 (secondary).
- Family: structures

## Claim

Compute the continuous-turbulence PSD gust design loads of an airplane:
given the aircraft mass and loading parameters (density rho, speed V,
weight W, wing area S, mean chord cbar, lift-curve slope a_lift) and the
turbulence environment at the flight condition (scale of turbulence L
and the design turbulence intensity, taken as the limit turbulence
intensity U_sigma in true airspeed per the continuous-turbulence design
condition, or an rms gust velocity sigma_w), form the one-sided vertical
gust velocity power spectral density Phi(Omega) = sigma_w^2 (L/pi)
(1 + (8/3)(1.339 L Omega)^2) / (1 + (1.339 L Omega)^2)^(11/6) for the
von Karman spectrum (the Dryden alternative Phi(Omega) = sigma_w^2
(L/pi) (1 + 3 (L Omega)^2) / (1 + (L Omega)^2)^2 with the same L and
sigma_w), build the gust-response transfer function of the rigid
aircraft (the vertical heave-response closed form with quasi-steady
aerodynamics: |H(omega)|^2 = h_inf^2 omega^2 / (omega^2 + K^2) with
h_inf = rho V S a_lift / (2 W) the frozen-gust incremental load factor
per unit gust velocity and K = rho V S a_lift / (2 m) the heave-follow
rate), form the response PSD |H|^2 Phi, integrate over the spatial
frequency to the rms-response ratio A (root-mean-square incremental load
factor per root-mean-square gust velocity), and scale to the design
load: the limit incremental load factor is the product of the limit
turbulence intensity U_sigma and A (both positive and negative gusts
apply), so the limit load factor is n_limit = 1 + U_sigma A; the
turbulence field convention of the design condition's non-linearity
provision frames a field of rms 0.4 U_sigma, whose linear-model response
makes the limit increment exactly 2.5 times the rms response to that
field. Produces, as the deliverables this leaf exists for: the von
Karman and Dryden turbulence PSD ordinates; the rigid-aircraft
gust-response transfer ordinates and the response PSD ordinates; the
rms-response ratio A for either spectrum (worked values in the Worked example section; von Karman sits
13.705554912291994 percent above Dryden because its spectrum decays as
Omega^(-5/3) rather than Omega^(-2)); the rms incremental load factor at any given sigma_w
(linear scaling); the design-limit incremental load factor and limit
load factor n_limit by the linear-model design rule at the given U_sigma
(worked value in the Worked example section, inside the same design
band as the discrete VB gust of the sibling method); the equivalent
discrete-gust velocity U_de_eq (m/s EAS) that the discrete-gust method
of gust-maneuver-loads would need to reproduce this leaf's limit
increment at the same condition, reported as the hand-off value that
leaf's envelope analysis takes as input; and the turbulence margin, here
the ranking of the continuous-turbulence limit increment against the
discrete condition at the same flight condition. The model is deterministic closed-form arithmetic in SI units on the
flight condition and turbulence inputs, with one fixed-grid Simpson
quadrature (analytic tails, below 1e-9 relative) for the von Karman
response integral, closed form exactly for Dryden. The certification
rules are referenced by name only, never reproduced; the design
intensity is a given input. Does NOT do: the discrete 1-cosine gust load factor, the
gust alleviation factor as a claimed product, the V-n diagram, envelope
verdicts and margin checks (gust-maneuver-loads owns the discrete method
and the envelope; this leaf's limit increment feeds that envelope only
through the reported equivalent discrete-gust velocity, evaluated by
inverting the sibling's own formula, never as an envelope product); the
SDOF base-excitation random vibration response of equipment, the
transmissibility, the Miles equation, g-rms screening and the n_eq =
3 sigma equipment qualification load factor (random-vibration-analysis
owns the SDOF response machinery under its desc "deliberately confined
to SDOF random vibration response"; this leaf's transfer is a
rigid-AIRCRAFT heave response with vehicle inertia and lift-curve slope,
not an oscillator transmissibility, and its spectrum is the atmospheric
turbulence spectrum, not a test-input acceleration PSD); the flexible
typical-section dynamic gust response, Wagner and Kussner indicial
lag-state histories, the dynamic magnification factor and peak-load
verdicts (aerodynamics/aeroelasticity/aeroelastic-gust-response); the
single-frequency Sears function gust gain and phase of a rigid airfoil
section (aerodynamics/aeroelasticity/sears-function-gust-lift); flutter,
divergence and any aeroelastic stability search; cycle counting and
cumulative fatigue damage of the gust spectrum (the fatigue pack and
load-spectrum-counting own the counting flow; this leaf reports the
design load levels those flows consume); atmospheric turbulence model
building or gust generation for simulation (no forming filters, no time
series); structural dynamics beyond the rigid-aircraft closed form
(flexible modes and unsteady-aerodynamic response functions are the
certification method's full-dynamic-analysis content, out of scope here
as in the sibling discrete leaf); and material property values or
design-value tables (properties are inputs, never looked up).
The von Karman and Dryden spectrum names, the PSD relations and the
heave transfer are standard published methodology (Hoblit, Gust Loads on
Aircraft, continuous-turbulence chapters); no tables, no test data.

## Model (implement exactly)

Pure stdlib (math only), closed form, deterministic, no RNG, no tables.
SI units throughout: rho kg/m^3, V m/s (TAS; equal to EAS at the
sea-level worked condition), W N, S m^2, cbar m, a_lift 1/rad, L m,
Omega rad/m (spatial circular frequency), sigma_w m/s, U_sigma m/s
(TAS), PSD ordinates per (m/s)^2 per (rad/m), A in 1/(m/s), load
factors dimensionless, U_de_eq in m/s EAS.

Module constants (published values only; every other fixed number is an
integration-grid parameter):
- VK_A = 1.339: the von Karman spectrum constant (published, rounded).
- VK_A_EXACT = 1.338985279065281 (computed at import from the Gamma
  closed form below, never hard-coded): the constant value for which
  the Parseval closure of the von Karman spectrum is exact.
- G_MS2 = 9.80665: standard gravity, m/s^2.
- RHO0 = 1.225: standard sea-level density, kg/m^3 (the SI reference of
  the EAS convention of the equivalent-gust report).
- L_SCALE_DEFAULT = 762.0: 2500 ft scale of turbulence in m, the
  documented default for the L input only (never applied silently).
- Integration grid: Simpson on t = ln(y), y in (0, inf), 16384 panels
  over ln(y_lo = 1e-4) to ln(y_hi = 1e10), an exact cap over (0, y_lo]
  and the analytic tails below; grid doubling changes every integral by
  less than 1e-9 relative (real anchor differences 7.54391552449773e-15
  and 1.199199970034183e-14).

Defining relations (pin these exactly; every function derives from
them):
- von Karman one-sided vertical-gust velocity PSD, spatial frequency
  (the receipt's published form, Hoblit convention):
  Phi_vK(Omega) = sigma_w^2 (L/pi) (1 + (8/3)(1.339 L Omega)^2)
                  / (1 + (1.339 L Omega)^2)^(11/6)
  With y = L Omega and the shape G_vK(y) = (1 + (8/3)(1.339 y)^2) /
  (1 + (1.339 y)^2)^(11/6), the Parseval closure is exact when the
  spectrum constant a satisfies a = J/pi with the closed-form integral
  J = integral_0^inf (1 + (8/3) x^2) / (1 + x^2)^(11/6) dx
    = (1/2) B(1/2, 4/3) + (4/3) B(3/2, 1/3),
  evaluated by Beta functions from math.lgamma; the real value is
  a_exact = J/pi = 1.338985279065281, so the published rounded 1.339
  (1.4720934718992496e-05 above a_exact) gives the closure ratio
  a_exact/1.339 = 0.9999890060233615: the Parseval integral of the
  normalized spectrum is 0.999989006 of sigma_w^2, asserted within 1e-3
  of unity (the identity is exact for the unrounded constant).
- Dryden one-sided vertical-gust velocity PSD, same convention:
  Phi_D(Omega) = sigma_w^2 (L/pi) (1 + 3 (L Omega)^2)
                 / (1 + (L Omega)^2)^2
  With y = L Omega and G_D(y) = (1 + 3 y^2) / (1 + y^2)^2, the closure
  is exact: integral_0^inf G_D(y) dy = pi (partial fractions
  3/(1+y^2) - 2/(1+y^2)^2), so integral Phi_D dOmega = sigma_w^2
  exactly (real numeric closure ratio 1.000000000000048).
- Both spectra share the DC ordinate Phi(0) = sigma_w^2 L/pi (real
  anchor 242.5521332720485 per (m/s)^2 per (rad/m) at L = 762 m,
  sigma_w = 1 m/s) and the same L and sigma_w semantics; the von Karman
  spectrum carries more energy at high reduced frequency (decay
  Omega^(-5/3) vs Omega^(-2)), which is why its response ratio sits
  above the Dryden one.
- Rigid-aircraft vertical (heave) gust response with quasi-steady
  aerodynamics: with z the aircraft vertical displacement (upward
  positive), the incremental lift from a vertical gust w_g is
  Delta L = q S a_lift (w_g - z_dot) / V, the heave equation is
  m z_ddot = Delta L, and the Laplace-domain response of the
  incremental load factor Delta n = z_ddot/g to the gust velocity is
  H(s) = h_inf s / (s + K), |H(omega)|^2 = h_inf^2 omega^2 /
  (omega^2 + K^2), with
    m     = W / g
    K     = rho V S a_lift / (2 m)          [1/s, heave-follow rate]
    h_inf = K / g = rho V S a_lift / (2 W)  [1/(m/s), frozen-gust gain]
  |H| rises from 0 at omega = 0 (the aircraft rides very long
  wavelength gusts) to the frozen value h_inf well above K; h_inf is the
  largest incremental load factor per unit gust velocity the rigid model
  can produce. This is the documented rigid-aircraft closed form of the
  gust-response transfer function; the full dynamic analysis of the
  certification method (flexible modes, unsteady aerodynamics) is out of
  scope, exactly as in the sibling discrete leaf.
- Response variance ratio: with omega = V Omega the encounter circular
  frequency, the rms-response ratio A (per (m/s) of rms gust velocity)
  is
  A^2 = integral_0^inf |H(V Omega)|^2 Phi_hat(Omega) dOmega
  where Phi_hat = Phi / sigma_w^2 is the normalized spectrum. In the
  reduced variable y = L Omega with the reduced filter corner
  y_c = K L / V,
  A^2 = (h_inf^2 / pi) integral_0^inf [y^2 / (y^2 + y_c^2)] G(y) dy.
  For the Dryden spectrum the integral is closed form exactly:
  A_D^2 = h_inf^2 B(y_c) with B(c) = (3 c + 2) / (2 (1 + c)^2), from
  the partial fractions and the standard integrals integral_0^inf
  y^2/((y^2 + c^2)(1 + y^2)) dy = (pi/2)/(1 + c) and integral_0^inf
  y^2/((y^2 + c^2)(1 + y^2)^2) dy = pi/4 - pi c (c + 2)/(4 (1 + c)^2).
  B(c) -> 1 as c -> 0+ (frozen-gust limit, A -> h_inf) and B(c) -> 0
  as c -> inf (the aircraft follows every gust), both identities of the
  closed form (real anchors 0.9999995 at c = 1e-6 and
  1.499999999998e-12 at c = 1e12). For the von Karman spectrum the
  integral is evaluated by the fixed Simpson grid with analytic tails
  (the shape decays as (8/3) 1.339^(-5/3) y^(-5/3), Dryden as 3 y^(-2);
  the tails include the leading and first filter corrections).
- rms response: sigma_delta_n = sigma_w A, exactly linear in sigma_w
  (Gaussian linear model).
- Design rule (paraphrased methodology of the continuous-turbulence
  design condition, referenced by name only, never reproduced): the
  limit load is the steady 1g load plus or minus the product of the
  limit turbulence intensity U_sigma (true airspeed, m/s) and the
  rms-response ratio A, so Delta n_limit = U_sigma A and
  n_limit = 1 + Delta n_limit; both positive and negative gusts apply.
  The turbulence field convention of the design condition frames an rms
  field of 0.4 U_sigma, whose linear-model rms response is 0.4 U_sigma A,
  making the limit increment exactly 2.5 times that rms response (real
  quotient 2.5). U_sigma is a given input at the flight condition (like
  the design gust velocity is a given input of the discrete method);
  the flight-profile alleviation factor of the design condition, when
  applied, scales U_sigma before entry and is applied by the caller;
  this leaf embeds no regulatory data profile and no regulatory text.
  The worked example takes the conservative no-alleviation convention
  (factor 1.0) at the sea-level reference intensity.
- Equivalent discrete-gust velocity (hand-off report): the algebraic
  inversion of the discrete 1-cosine load-factor formula of the sibling
  method at the single condition,
  U_de_eq = 2 (W/S) Delta n / (rho V_e a_lift K_g),  with
  K_g = 0.88 mu_g / (5.3 + mu_g),  mu_g = 2 (W/S) / (rho cbar a_lift g),
  evaluated at the sea-level condition where V_e = V and rho = rho0, so
  U_de_eq is in m/s EAS. The discrete load-factor formula, the
  alleviation factor and the V-n envelope are owned products of
  gust-maneuver-loads; here the two closed forms appear only inside the
  inversion that produces the reported hand-off value.

Functions (every public function validates its inputs identically;
ValueError, never assert; real message prefixes quoted in the Worked
example):
- von_karman_psd(omega, sigma_w, l) -> float: the von Karman PSD
  ordinate. ValueErrors: sigma_w or l not a positive number ("sigma_w
  must be a positive number, got ...", "L must be a positive number,
  got ..."), omega negative ("Omega must be a non-negative number, got
  ..."), any boolean argument.
- dryden_psd(omega, sigma_w, l) -> float: the Dryden PSD ordinate.
  Same ValueErrors.
- rigid_aircraft_response_params(rho, v, w, s, a_lift, g=G_MS2) ->
  {"h_inf": float, "k_rate": float, "mass_kg": float}: the heave
  response parameters above. ValueErrors: any of rho, V, W, S, a_lift,
  g not a positive number ("rho must be a positive number, got ...",
  "W must be a positive number, got ...").
- gust_response_transfer_squared(omega, rho, v, w, s, a_lift, g) ->
  float: |H(omega)|^2. Same ValueErrors plus omega negative.
- rms_response_ratio(spectrum, rho, v, w, s, a_lift, l, g) -> float:
  the rms-response ratio A per (m/s). ValueErrors: spectrum not
  "von-karman" or "dryden" ("spectrum must be 'von-karman' or 'dryden',
  got ..."), l not positive, the aircraft inputs invalid.
- rms_load_factor_response(sigma_w, a_ratio) -> float: sigma_w A, the
  rms incremental load factor of the given rms field. ValueErrors:
  sigma_w not positive, a_ratio not non-negative ("A must be a
  non-negative number, got ...").
- design_incremental_load_factor(a_ratio, u_sigma) -> float: U_sigma A,
  the limit incremental load factor. ValueErrors: u_sigma not positive
  ("U_sigma must be a positive number, got ..."), a_ratio invalid.
- gust_alleviation_factor(ws, cbar, a_lift, rho, g) -> float: K_g of
  the discrete method, evaluated only inside the equivalence report.
  ValueErrors: any input not positive ("cbar must be a positive number,
  got ...").
- equivalent_discrete_gust_velocity(delta_n, ws, v_eas, a_lift, cbar,
  rho, g) -> float: U_de_eq in m/s EAS by the inversion above.
  ValueErrors: delta_n not positive ("delta_n must be a positive number,
  got ..."), any input not positive.
- spectrum_psd_ordinates(spectrum, omega_grid, sigma_w, l) -> list of
  (omega, phi) pairs: the turbulence PSD ordinates at the given Omega
  grid (rad/m). ValueErrors as the PSD functions plus an empty grid
  ("omega grid must not be empty").
- response_psd_ordinates(spectrum, omega_grid, rho, v, w, s, a_lift,
  l, g) -> list of (omega, |H|^2 Phi_hat) pairs: the response PSD
  ordinates at the grid, the integrand of the A-squared integral.
  Same ValueErrors.
- continuous_turbulence_report(spectrum, rho, v, w, s, a_lift, l,
  u_sigma, cbar, g=G_MS2, omega_grid=None) -> dict: the one-shot
  report. Keys: "spectrum", "h_inf" (1/(m/s)), "k_rate" (1/s), "y_c"
  (dimensionless reduced filter corner), "a_ratio" (1/(m/s)),
  "response_factor" (A/h_inf), "rms_delta_n_at_1mps", "delta_n_limit",
  "n_limit", "u_de_eq_mps_eas" (m/s EAS), "mu_g", "k_g", "mass_kg",
  "turbulence_psd_ordinates" and "response_psd_ordinates" at the
  default Omega grid 2 pi / [1000, 500, 200, 100, 50, 25] m. Same
  ValueErrors as the component functions.

Identities to test (closed form, checkable without the builder module):
- von Karman Parseval closure: integral Phi_hat_vK dOmega =
  a_exact/1.339 = 0.9999890060233615 with the published rounded
  constant, and = 1 exactly with a_exact = 1.338985279065281; assert
  the numeric closure ratio within 1e-3 of unity and the numeric-vs-
  analytic agreement within 1e-6 (real 7.616129948928574e-14 relative).
- Dryden closure: integral Phi_hat_D dOmega = 1 exactly; assert the
  numeric closure within 1e-6 of unity (real 1.000000000000048).
- DC ordinate identity: both spectra equal sigma_w^2 L/pi at Omega = 0
  (real 242.5521332720485 at the worked L, sigma_w = 1 m/s).
- Dryden exact response integral: A_D = h_inf sqrt(B(y_c)) with
  B(c) = (3 c + 2)/(2 (1 + c)^2) equals the quadrature within 1e-9
  relative (real closed form 0.052772184639460866 vs quadrature
  0.0527721846394613, absolute difference 4.371503159461554e-16,
  relative 8.283725961560227e-15).
- Response factor limits: B(c) -> 1 as c -> 0+ and B(c) -> 0 as
  c -> inf (real anchors 0.9999995 and 1.499999999998e-12).
- Ordering and bounds: A_vK > A_Dryden (real ratio 1.13705554912292,
  von Karman 13.705554912291994 percent above) and both sit below the
  frozen bound h_inf (real A_vK = 0.06000490538363879, A_D =
  0.0527721846394613, h_inf = 0.11225096093750002).
- Linearity: rms response scales exactly with sigma_w and the limit
  increment exactly with U_sigma (real 2x-intensity case gives
  n_limit = 4.292109128967958 = 1 + 2 (n_limit - 1) at the worked
  condition, within 1e-12); the limit increment is exactly 2.5 times
  the rms response to the 0.4 U_sigma field (real quotient 2.5).
- Determinism: identical outputs run to run, identical under both
  interpreters; no randomness; no imports beyond math; grid doubling
  changes every internal integral by less than 1e-9 relative (real
  7.54391552449773e-15, 1.199199970034183e-14).

## Worked example

Typical transport at the VB-class sea-level condition, chosen to sit
alongside the discrete-gust sibling's worked case for direct comparison:
rho = 1.225 kg/m^3 (sea level, TAS = EAS), V = 154.33 m/s (300 KEAS
class), W/S = 4800 Pa on S = 120 m^2 (W = 576000 N), cbar = 3.81 m,
a_lift = 5.7/rad, g = 9.80665 m/s^2; turbulence scale L = 762 m (2500
ft) and limit turbulence intensity U_sigma = 27.432 m/s TAS (90 ft/s,
the sea-level reference intensity of the continuous-turbulence design
condition, taken with the flight-profile alleviation factor at 1.0, the
conservative no-alleviation convention; the intensity is a given input,
and applying the alleviation factor is the caller's step, never
embedded).

All values below are REAL outputs of the prep anchor
ops/automation/state/wave49-specs/anchors/anchor_continuous-turbulence-
gust-loads.py (pure stdlib, math only, exit 0, no RNG), run once and
quoted as printed, then re-verified byte-identical under python3
(3.11.16 at this machine), the ~/.pyenv/versions/3.13.12 interpreter and
/usr/bin/python3 (3.9.6). All internal identity asserts pass.

- Rigid-aircraft response parameters (identical for both spectra):
  K = 1.1008058860777343 /s, h_inf = 0.11225096093750002 per (m/s),
  reduced filter corner y_c = K L / V = 5.435197856484374. h_inf is the
  frozen-gust gain, the largest possible incremental load factor per
  unit gust velocity (a 1 m/s rms field on a frozen aircraft would give
  0.11225 g rms); the heave filter (corner at encounter frequency K,
  wavelength about 2 pi V / K ~ 880 m) removes the energy the aircraft
  follows.
- von Karman spectrum at the worked condition: A_vK =
  0.06000490538363879 per (m/s), response factor A/h_inf =
  0.5345602824464799 (the rigid response retains 53.46 percent of the
  frozen sensitivity). rms incremental load factor at sigma_w = 1 m/s:
  0.06000490538363879; at the 0.4 U_sigma field rms (10.9728 m/s, the
  field convention of the design condition's non-linearity provision):
  sigma_delta_n = 0.6584218257935917. Limit incremental load factor at
  U_sigma = 27.432 m/s TAS: Delta n_limit = 1.6460545644839792, so
  n_limit = 2.646054564483979: the continuous-turbulence limit condition
  at the sea-level reference intensity sits at n = 2.65, inside the
  same design band as the discrete VB gust of the sibling method
  (2.4-2.7 class); the limit increment is exactly 2.5 times
  the rms response to the 0.4 U_sigma field (real quotient 2.5). The
  equivalent discrete-gust velocity reported to the discrete-gust
  envelope method: U_de_eq = 19.063820591364568 m/s EAS (about
  62.5 ft/s), with the discrete-form parameters mu_g =
  36.79718848898816 and K_g = 0.7692087531874008 evaluated inside the
  inversion: a discrete gust of about 62.5 fps EAS would produce the
  same limit increment, just below the 66 fps VB design gust, so the
  discrete condition marginally drives at this point.
- von Karman turbulence PSD ordinates at sigma_w = 1 m/s (the
  normalized spectrum, per (m/s)^2 per (rad/m)) at the default Omega
  grid 2 pi / [1000, 500, 200, 100, 50, 25] m:
  Phi(0.006283185307179587) = 28.23049507989389;
  Phi(0.012566370614359173) = 9.127652940158693;
  Phi(0.031415926535897934) = 1.9968651285963208;
  Phi(0.06283185307179587) = 0.6296425301970892;
  Phi(0.12566370614359174) = 0.19837774655453844;
  Phi(0.25132741228718347) = 0.062489231858575404. The DC ordinate is
  Phi(0) = sigma_w^2 L/pi = 242.5521332720485 (identical for both
  spectra).
- von Karman response PSD ordinates |H(V Omega)|^2 Phi_hat(Omega) (the
  A-squared integrand, per 1/(m/s)^2 per (rad/m)) at the same grid:
  R(0.006283185307179587) = 0.15541916622516297;
  R(0.012566370614359173) = 0.08698574123506526;
  R(0.031415926535897934) = 0.02392760963617748;
  R(0.06283185307179587) = 0.007832728553613196;
  R(0.12566370614359174) = 0.0024915873597191056;
  R(0.25132741228718347) = 0.0007867480180908697. Its integral over all
  Omega is A_vK^2 = 0.0036005886700994434 (1/(m/s))^2 (the Dryden
  counterpart is A_D^2 = 0.0027849034716213956).
- Dryden alternative at the same condition: A_D = 0.0527721846394613
  per (m/s), response factor 0.47012679623156384; Delta n_limit =
  1.4476465690297025, n_limit = 2.4476465690297022; U_de_eq =
  16.765953612441937 m/s EAS (about 55.0 ft/s). The von Karman A sits
  13.705554912291994 percent above the Dryden A (ratio
  1.13705554912292) because the von Karman spectrum decays as
  Omega^(-5/3) rather than Omega^(-2) and therefore loads the response
  band harder; the spectra agree at Omega = 0 and both integrate to
  sigma_w^2 (Parseval), so the gap is purely spectral shape, the
  published reason the design condition names the von Karman form.
- Real ValueError messages (module output, quoted as raised): a negative
  L raises "L must be a positive number, got -1.0"; sigma_w = 0 raises
  "sigma_w must be a positive number, got 0.0"; a negative Omega raises
  "Omega must be a non-negative number, got -0.1"; rho = 0 raises
  "rho must be a positive number, got 0.0"; a negative W raises
  "W must be a positive number, got -576000.0"; a boolean rho raises
  "rho must be a positive number, got True"; an unknown spectrum raises
  "spectrum must be 'von-karman' or 'dryden', got 'kolmogorov'";
  L = 0 in the ratio raises "L must be a positive number, got 0.0";
  a negative U_sigma raises "U_sigma must be a positive number, got
  -1.0"; a negative A raises "A must be a non-negative number, got
  -0.5"; a negative sigma_w raises "sigma_w must be a positive number,
  got -1.0"; a negative cbar raises "cbar must be a positive number,
  got -3.81"; delta_n = 0 raises "delta_n must be a positive number,
  got 0.0"; an empty Omega grid raises "omega grid must not be empty".

Run your module and take the real outputs as assert targets; every
value above is a real prep output of the anchor named at the head of
this section (stdlib math, closed form, exit 0, no randomness,
identical under both interpreters).

## Validation list (contract test must include)

1. Worked example asserts within 1e-6 relative at the worked inputs
   (rho = 1.225, V = 154.33, W = 576000, S = 120, cbar = 3.81,
   a_lift = 5.7, L = 762.0, g = 9.80665): rms_response_ratio("von-
   karman", ...) gives 0.06000490538363879, the Dryden ratio gives
   0.0527721846394613, rigid_aircraft_response_params reports h_inf =
   0.11225096093750002 and K = 1.1008058860777343 with y_c =
   5.435197856484374, and design_incremental_load_factor at
   U_sigma = 27.432 gives 1.6460545644839792 with n_limit =
   2.646054564483979 (von Karman) and 1.4476465690297025 with n_limit
   = 2.4476465690297022 (Dryden).
2. The hand-off report: equivalent_discrete_gust_velocity at the
   worked condition returns U_de_eq = 19.063820591364568 m/s EAS for
   the von Karman limit increment and 16.765953612441937 for the
   Dryden, within 1e-6 relative; mu_g = 36.79718848898816 and
   k_g = 0.7692087531874008; the one-shot report key set is
   {"spectrum", "h_inf", "k_rate", "y_c", "a_ratio", "response_factor",
   "rms_delta_n_at_1mps", "delta_n_limit", "n_limit",
   "u_de_eq_mps_eas", "mu_g", "k_g", "mass_kg",
   "turbulence_psd_ordinates", "response_psd_ordinates"}.
3. Turbulence PSD ordinates within 1e-6 relative at the worked grid:
   the six von Karman ordinates of the Worked example (28.23049507989389
   down to 0.062489231858575404) and the DC ordinate 242.5521332720485
   for both spectra; the six response PSD ordinates of the Worked
   example (0.15541916622516297 down to 0.0007867480180908697).
4. Parseval closures: the integral of the normalized von Karman
   spectrum over Omega in (0, inf) equals a_exact/1.339 =
   0.9999890060233615 within 1e-3 of unity (the published 1.339 is the
   rounding of a_exact = 1.338985279065281 computed from the
   Beta-function closed form; the closure is exact for the unrounded
   constant) and the normalized Dryden integral equals 1.0 within 1e-6;
   assert the numeric quadrature against the analytic closure values
   within 1e-6 relative, never by exact-float equality.
5. Dryden exact integral identity: A_D equals h_inf times sqrt(B(y_c))
   with B(c) = (3 c + 2) / (2 (1 + c)^2) within 1e-9 relative
   (recompute the closed form in-test); the response-factor limits
   B(1e-6) within 1e-5 of 1 and B(1e12) below 1e-9 absolute.
6. Ordering and bounds: the von Karman ratio exceeds the Dryden ratio
   by the real ratio 1.13705554912292 (13.705554912291994 percent)
   within 1e-6 relative, and both sit below h_inf (the frozen bound;
   assert A < h_inf for both spectra at the worked condition). Both
   spectra share the DC ordinate sigma_w^2 L/pi (assert within 1e-9
   relative).
7. Linearity and scaling: rms_load_factor_response(1.0, A) returns A
   itself; the limit increment at 2 U_sigma is exactly twice the
   increment at U_sigma (assert within 1e-9 relative, real n_limit
   4.292109128967958 at the doubled intensity); the limit increment
   equals 2.5 times the rms response at the 0.4 U_sigma field rms
   within 1e-9 relative (real quotient 2.5).
8. Determinism: two consecutive one-shot report calls return identical
   dicts; the fixed 16384-panel Simpson grid with analytic tails
   changes every internal integral by less than 1e-9 relative when the
   panel count doubles (real 7.54391552449773e-15 and
   1.199199970034183e-14); no randomness anywhere; no imports beyond
   math; the module's only constants are the published spectrum
   constant, the standard gravity and density, the 762 m scale default
   and the fixed grid parameters.
9. ValueErrors raise from the named public function with the real
   message prefixes quoted in the Worked example: non-positive or
   boolean rho, V, W, S, a_lift, g, L, cbar, U_sigma, sigma_w, delta_n
   ("rho must be a positive number, got ...", "W must be a positive
   number, got ...", "sigma_w must be a positive number, got ...",
   "U_sigma must be a positive number, got ...", "cbar must be a
   positive number, got ...", "delta_n must be a positive number, got
   ..."), a negative Omega ("Omega must be a non-negative number, got
   ..."), a negative or invalid A ("A must be a non-negative number,
   got ..."), an unknown spectrum ("spectrum must be 'von-karman' or
   'dryden', got ...") and an empty Omega grid ("omega grid must not
   be empty").
10. No exact-float equality on computed sums; use
    assertAlmostEqual/math.isclose everywhere, with the Parseval
    closures asserted against their analytic values (the real von
    Karman residue 0.999989006 is a property of the published rounded
    1.339 constant, never an equality target at 1.0). Test passes
    under BOTH interpreters (/usr/bin/python3 and
    ~/.pyenv/versions/3.13.12/bin/python3).
11. Run the deterministic contract test offline (no network); it exits
    0. All worked-example numbers above were verified byte-identical
    under python3, the ~/.pyenv/versions/3.13.12 interpreter and
    /usr/bin/python3 before spec time.
12. Magnitude gate: the limit load factor of the worked condition
    (2.646054564483979 von Karman, 2.4476465690297022 Dryden, at the
    sea-level reference intensity with no alleviation) sits in the
    transport design-load-factor band of the discrete VB gust at the
    same condition (2.4-2.7 class), and the rms incremental load factor
    per m/s of rms gust velocity (0.06000490538363879 von Karman) sits
    in the published rigid-aircraft rms-response band; the equivalent
    discrete-gust velocities (19.063820591364568 and 16.765953612441937
    m/s EAS, about 62.5 and 55.0 fps) sit just below the 66 fps VB
    design gust, so the discrete condition marginally drives at VB-class
    sea level and the continuous condition is the second envelope input.

## Corpus fragment (eval/hit1-wave49-continuous-turbulence-gust-loads.yaml)

Query 1 (copy verbatim from the probe receipt gate (e)):
  "compute the continuous-turbulence-gust-loads of the transport
  airplane by the power-spectral-density-gust-method with the
  von-karman-spectrum of the vertical gust velocity, the
  gust-response-transfer-function and the rms-load-response, and report
  the design load factor and turbulence-psd ordinates of the
  continuous-turbulence-design criterion"
  -> top1 continuous-turbulence-gust-loads 42.5, top2 buffet-boundary-
  testing 9.0 / gust-maneuver-loads 9.0, margin 33.5 (strong)
  intent: "structures/loads; continuous-turbulence-gust-loads: the
  continuous-turbulence design loads of the transport airplane by the
  power-spectral-density gust method with the von Karman spectrum of
  the vertical gust velocity, the rigid-aircraft gust-response transfer
  function and the rms load response, reporting the design load factor
  and the turbulence PSD ordinates of the continuous-turbulence design
  criterion"
  expected_skill: "structures/loads/continuous-turbulence-gust-loads"
Query 2 (copy verbatim from the probe receipt gate (e)):
  "estimate the design gust loads of the airplane in continuous
  turbulence from the dryden-spectrum input and the
  gust-response-transfer-function: integrate the response power
  spectral density to the rms load factor, scale to the design
  turbulence intensity and report the equivalent discrete-gust velocity
  the gust-maneuver-loads envelope takes as input"
  -> top1 continuous-turbulence-gust-loads 34.0, top2
  gust-maneuver-loads 19.5, margin 14.5 (clear)
  intent: "structures/loads; continuous-turbulence-gust-loads: the
  design gust loads in continuous turbulence from the Dryden spectrum
  input and the gust-response transfer function, integrating the
  response power spectral density to the rms load factor, scaling to
  the design turbulence intensity and reporting the equivalent
  discrete-gust velocity the gust-maneuver-loads envelope analysis
  takes as its input"
  expected_skill: "structures/loads/continuous-turbulence-gust-loads"
Task ids: w49-continuous-turbulence-gust-loads-1 and -2. Prep greps
(re-run fresh at spec time): the whole-tree grep returns only the three
incidental von Karman hits (plate-buckling effective width,
boundary-layer momentum integral, sears-function single-frequency
context) and the corpus scan is 0 of 1326 blocks, so the queries are
collision-free; the discrete-gust corpus tasks route on the 1-cosine,
V-n and envelope vocabulary of gust-maneuver-loads and do not overlap
this spectral surface. Build-time fence note (wave-49 receipt gate
(f)): add routing bullets to gust-maneuver-loads' and
random-vibration-analysis' Related leaves pointing continuous-turbulence
/ spectral-gust questions at this leaf; the sears-function-gust-lift
related-leaves line naming random-vibration-analysis "the PSD machinery home of continuous-
turbulence spectral gust content" should gain this leaf as the actual
implementer of that content).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the continuous
turbulence gust design loads of an airplane by the power spectral
density gust method:" and include the outputs in the Claim order (the
von Karman and Dryden vertical gust velocity power spectral densities,
the rigid-aircraft gust-response transfer function, the response power
spectral density, the rms response ratio A, the rms load response and
the design limit load factor per the continuous-turbulence design
criterion, and the equivalent discrete gust velocity reported to the
discrete-gust envelope method), then close with the Trigger list. Never
claim the discrete 1-cosine load factor, the gust alleviation factor,
the V-n diagram or the envelope verdict as products, never claim SDOF
transmissibility or Miles-equation equipment screening, never claim
flexible-section or indicial time-domain response histories, and never
phrase the response model as an oscillator transfer function (it is the
rigid-aircraft heave response with vehicle inertia and lift-curve
slope). First tag: continuous-turbulence-gust-loads. Metadata tags
EXACTLY as the probe receipt gate (f) lists them, nothing else:
von-karman-spectrum, dryden-spectrum, turbulence-psd,
gust-response-transfer-function, power-spectral-density-gust-method,
rms-load-response, continuous-turbulence-design. 50-150 words,
<=1000 chars, no em dash, no content-policy sweep term, action verb
present. Recommended wording (142 words, 963 chars, verified at spec
time):

"Use when you must compute the continuous turbulence gust design loads
of an airplane by the power spectral density gust method: build the von
Karman or Dryden power spectral density of the vertical gust velocity
from the scale of turbulence and the turbulence intensity, form the
rigid-aircraft gust response transfer function, multiply into the
response power spectral density, integrate to the rms load response and
scale to the design limit load factor of the continuous turbulence
design criterion, and report the equivalent discrete gust velocity the
discrete-gust envelope analysis takes as its input. Produces turbulence
PSD and response PSD ordinates, the rms load factor, the design gust
loads and the discrete-gust equivalent in SI units. Trigger: continuous
turbulence gust loads, von Karman spectrum, Dryden spectrum, gust
response transfer function, turbulence PSD, power spectral density gust
method, rms load response, continuous turbulence design."

FORBIDDEN TOKENS (belong to siblings): discrete-gust, 1-cosine,
gust-alleviation-factor, v-n-diagram, envelope-verdict, margin-check,
maneuver-load-factor and any claim that computes the discrete 1-cosine
gust load factor, the alleviation factor or the V-n envelope as a
product (gust-maneuver-loads owns the discrete method and the envelope;
here the discrete load-factor formula appears only inside the algebraic
inversion that reports the equivalent discrete-gust velocity, and the
gust alleviation factor only inside that same inversion);
transmissibility, miles-equation, base-excitation, g-rms,
equivalent-static-load-factor, vibration-qualification, s-dof, sdof and
any claim that computes an SDOF oscillator response or equipment
screening level (random-vibration-analysis owns the SDOF random
vibration response machinery, "deliberately confined to SDOF random
vibration response" in its own desc); wagner-function, kussner-function,
indicial-aerodynamics, dynamic-magnification-factor, typical-section,
gust-response-history and any time-domain flexible-section response
(aeroelastic-gust-response); sears-function, sinusoidal-gust,
unsteady-gust-load, reduced-frequency-gust (sears-function-gust-lift);
flutter, divergence, stability (the aeroelasticity stability leaves);
cycle-counting, rainflow, miner, fatigue-damage (the fatigue pack and
load-spectrum-counting); buffet, flutter-testing and any aircraft
buffet content; turbulence-model, forming-filter, gust-generation,
simulation (no time-series or filter content); and the bare single words
psd, spectrum, gust, turbulence, loads, response, transfer, power,
spectral, density as standalone metadata tags (use only the hyphenated
compounds listed above). The von Karman and Dryden spectrum relations,
the heave transfer and the design rule are this leaf's own products,
fenced in the Claim above; FAR-25 and CS-25 frame the certification
context by name only and FAA AC 25.341-1 is named as method context
only, never reproduced verbatim.
