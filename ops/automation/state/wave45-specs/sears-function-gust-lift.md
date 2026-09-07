# Wave-45 leaf spec: sears-function-gust-lift (aerodynamics, aeroelasticity pack)

- Path: skills/aerodynamics/aeroelasticity/sears-function-gust-lift/
- Pack: aeroelasticity (4 leaves present at prep:
  added-mass-coefficients-potential-flow, aeroelastic-gust-response,
  divergence-speed, flutter-speed-prediction; sears-function-gust-lift is
  the wave-45 aeroelasticity addition). Claim fences (quoted from the
  sibling frontmatter and bodies at prep; no sibling produces or fences
  the frequency-domain sinusoidal-gust lift response of the rigid thin
  section):
  - aeroelastic-gust-response (this pack) is the time-domain
    flexible-section discrete-gust sibling: its description reads "Use
    when you must compute the dynamic aeroelastic response of a flexible
    two-degree-of-freedom typical wing section to a discrete gust with
    indicial unsteady aerodynamics: run the Wagner and Kussner lag-state
    lift model in the time domain, produce the plunge and pitch response
    histories for a one-minus-cosine gust, and report the dynamic
    magnification factor of the peak lift over the quasi-steady value".
    Its Domain quick reference documents "apparent-mass and full
    Theodorsen noncirculatory terms are neglected at this level" and
    pairs the model with flutter-speed-prediction as "the same
    typical-section machinery, a different question (stability there,
    forced response here)". Fresh probe: its SKILL.md, logic and contract
    test contain zero occurrences of frequency, harmonic, sinusoidal or
    Sears (real greps below), so frequency-domain gust response is
    neither produced nor fenced there; the quasi-steady peak lift it
    documents, L_qs = 2*pi*rho*V*b*w_g, is exactly the amplitude this
    leaf's gain is normalized against.
  - flutter-speed-prediction (this pack) is the V-g stability owner and
    the source of the Theodorsen-function conventions this leaf reuses:
    its description and Domain quick reference state "the complex
    lift-deficiency function C(k) = H1^(2)(k)/(H1^(2)(k) + i H0^(2)(k))
    built from Bessel J and Y series (Abramowitz and Stegun 9.1.10 to
    9.1.11), evaluated at harmonic motion with the reduced frequency
    k = omega*b/V. Limits: C = 1 in steady flow (k = 0) and C = 1/2 at
    high reduced frequency", and it warns "Quasi-steady aerodynamics
    (C = 1) is known to give erroneous pitch damping and is not used
    here". Its problem is the damping-crossing stability search of the
    two-DOF section (V-g method, artificial damping g, frequency
    coalescence, FAR 25.629 clearance margin), not a forced gust
    response; this leaf evaluates the same published C(k) form inside the
    Sears function and produces no stability content.
  - added-mass-coefficients-potential-flow (this pack) owns the
    added-mass coefficient catalog of accelerating bodies: "an
    accelerating body must drag a surrounding mass of fluid with it, and
    that fluid inertia is a real load", and notes the gust and flutter
    siblings "both document neglecting apparent-mass terms at their
    level". This leaf is a RIGID airfoil with no acceleration degree of
    freedom and no added-mass coefficient catalog; the noncirculatory
    content of the gust response is carried inside the total Sears
    function S(k), never estimated as a separate coefficient.
  - divergence-speed (this pack) is the static torsional instability
    leaf of the same typical section, no gust content.
  - wave-drag-area-rule (aerodynamics/high-speed) owns the transonic
    area rule and the Sears-Haack minimum-drag body: "size the
    Sears-Haack minimum-drag body for a given length and volume,
    evaluate its zero-lift wave drag" with the body radius
    r(x) = r_max*(4*(x/L)*(1 - x/L))^(3/4). The bare token sears in the
    whole skills/ tree resolves ONLY to that leaf, its scripts and its
    router row (real grep below); the sears-function token of this leaf
    is disjoint from the sears-haack body token.
  - structures/loads/gust-maneuver-loads (structures family) owns the
    rigid-aircraft discrete-gust certification load-factor method
    (description: "compute aircraft structural loads from gust and
    maneuver conditions per FAR 25.341 and FAR 25.337: discrete 1-cosine
    gust load factor n = 1 + (rho0*V_e*a*K_g*U_de)/(2*W/S), gust
    alleviation factor K_g = 0.88*mu_g/(5.3 + mu_g) ..."), an
    inertia-weighted vehicle load factor, and
    structures/loads/random-vibration-analysis owns the PSD
    transmissibility machinery that is the home of continuous-turbulence
    (Dryden, von Karman) spectral gust content. This leaf is the section
    aerodynamics transfer function S(k): no vehicle inertia, no load
    factor, no PSD content.
  Whole-tree greps at prep (real runs for this spec):
  "sears-function|sears function|sinusoidal-gust|gust-transfer-function"
  = 0 hits in skills/ (grep exit 1) and 0 corpus tasks;
  "harmonic gust|frequency-domain" = 0 hits in the aerodynamics family
  (the only tree hits are cross-cutting numerics DSP/control leaves and
  the structures random-vibration leaves, all signal-processing uses of
  the phrase, no gust content); "kussner|wagner|indicial" resolves inside
  aerodynamics only to aeroelastic-gust-response and
  added-mass-coefficients-potential-flow; "sears" = only
  wave-drag-area-rule (SKILL.md, scripts, router row). Corpus:
  "sears" matches exactly 2 tasks, both the Sears-Haack-body tasks
  (wd1/wd2, expected_skill wave-drag-area-rule); sears-function and
  sinusoidal-gust appear in no eval/hit1-corpus.yaml task.
- Standards id: far-25 + cs-25 (reference-only, both present in
  standards-map.yaml, lines 16 and 27, matching the aeroelasticity pack
  convention of aeroelastic-gust-response and flutter-speed-prediction).
  Ledger Standard: far-25, cs-25.
- Family: aerodynamics

## Claim

Produce the frequency-domain unsteady lift response of a rigid thin
airfoil in incompressible flow to a convected sinusoidal vertical gust
(the Sears problem, Sears 1941, JAS 8(3); Bisplinghoff, Ashley and
Halfman, Aeroelasticity, unsteady incompressible gust chapter; Fung, An
Introduction to the Theory of Aeroelasticity): evaluate the complex
Sears function S(k) from the Bessel J0, J1, Y0, Y1 series (Abramowitz
and Stegun 9.1.10 to 9.1.11 forms, the same published series family the
flutter sibling documents for C(k)) with the Theodorsen lift-deficiency
function C(k), the gust gain |S(k)| (the unsteady gust-load amplitude
ratio to the quasi-steady reference L_qs = 2*pi*rho*V*b*w_g), the phase
lag of the gust load behind the convected gust, and the unsteady
gust-load amplitude itself, plus the k to 0 quasi-steady limit |S| = 1,
the monotone gain roll-off with reduced frequency k = omega*b/V, and the
half-amplitude reduced frequency where |S(k)| = 0.5. Produces the
complex sears function, the gain and phase-lag tables versus reduced
frequency, and the gust-load amplitudes that gate sinusoidal-gust load
estimates, unsteady thin-airfoil response checks and aeroelasticity
coursework. Does NOT do: the time-domain dynamic response of a flexible
typical section to a discrete one-minus-cosine gust with the Wagner and
Kussner indicial lag-state model and the dynamic magnification factor
(aeroelastic-gust-response, whose file contains no frequency, harmonic,
sinusoidal or Sears content, real grep); the V-g flutter speed search,
damping crossing and frequency coalescence of the same typical section
(flutter-speed-prediction, which owns the C(k) stability machinery this
leaf only evaluates inside S(k)); static divergence (divergence-speed);
added-mass coefficient estimation of accelerating bodies
(added-mass-coefficients-potential-flow); the Sears-Haack body, area
rule or transonic wave drag (wave-drag-area-rule, the owner of the bare
sears token); the rigid-aircraft discrete-gust certification load factor
or the V-n gust lines (structures/loads/gust-maneuver-loads);
continuous-turbulence PSD gust loads from Dryden or von Karman spectra
(structures/loads/random-vibration-analysis is the PSD machinery home);
airfoil motion degrees of freedom, structural flexibility or mass
properties (rigid airfoil, no structure). Scope: single-frequency
frozen sinusoidal gust, incompressible thin-airfoil theory, small gust
amplitudes (linear), two-dimensional section per unit span, reduced
frequency k >= 0. Deterministic, pure stdlib (math only), no RNG, no
gamma-gas constant (the theory is incompressible and gamma-free).

## Model (implement exactly)

Pure stdlib, math only, deterministic, no RNG. Module constants:
EULER_GAMMA = 0.57721566490153286060651209 (Euler-Mascheroni constant of
the Y-series logarithm terms), SERIES_TERMS_MAX = 300 (safety cap of the
Bessel series loops), SERIES_TOL = 1e-18 (relative term tolerance that
stops each Bessel series), BISECT_LO = 0.1 and BISECT_HI = 2.0 (default
bracket of the half-amplitude bisection). Conventions, pinned: time
dependence e^{+i*omega*t}, physical quantities are the real part; gust
vertical velocity field w_g(x, t) = w_g_amp*Re{e^{i*(omega*t - k*x/b)}}
with x measured downstream from the LEADING EDGE, so the gust front
crosses the leading edge at t = 0; reduced frequency k = omega*b/V =
2*pi*f*b/V with semi-chord b = c/2; lift per unit span
L(t) = Re{L_hat*e^{i*omega*t}} with the complex amplitude
L_hat = 2*pi*rho*V*b*w_g_amp*S(k); phase lag phi(k) = -arg S(k) in
radians, the time by which the lift peak lags the gust peak at the
leading edge. The classical mid-chord-referenced form (gust front at the
mid-chord at t = 0, the BAH p. 287 printed form) is the exact algebraic
identity S_mid(k) = S(k)*e^{+i*k} = C(k)*(J0(k) - i*J1(k)) + i*J1(k)
with |S_mid| = |S|: the module pins the leading-edge reference (the
convention whose phase lag grows monotonically from 0) and S(0) = 1
exactly in either reference.

Defining relations (pin these exactly; every function derives from them):
- Bessel series (A&S 9.1.10 and the 9.1.11-form Y series, the same
  family the flutter sibling cites for C(k)): J0(x) = sum_m (-1)^m
  (x/2)^(2m)/(m!)^2, J1(x) = (x/2) sum_m (-1)^m (x/2)^(2m)/(m!(m+1)!),
  Y0(x) = (2/pi)*[(ln(x/2) + gamma)*J0(x) + sum_{m>=1} (-1)^(m+1)
  H_m*(x/2)^(2m)/(m!)^2], Y1(x) = (2/pi)*[(ln(x/2) + gamma)*J1(x) -
  1/x] - (1/pi)*sum_{m>=0} (-1)^m (H_m + H_{m+1})*(x/2)^(2m+1)/
  (m!(m+1)!) with H_m the harmonic numbers (H_0 = 0). Each series runs
  until its term magnitude falls below SERIES_TOL times the running sum.
- Hankel functions of the second kind: H0^(2)(k) = J0(k) - i*Y0(k),
  H1^(2)(k) = J1(k) - i*Y1(k).
- Theodorsen function: C(k) = H1^(2)(k)/(H1^(2)(k) + i*H0^(2)(k)), with
  C = 1 exactly at k = 0 and C -> 1/2 at high reduced frequency (the
  flutter sibling's documented limits).
- Sears function (leading-edge reference): S(k) = [C(k)*(J0(k) -
  i*J1(k)) + i*J1(k)]*e^(-i*k); S(0) = 1 + 0i exactly.
- Closed-form gain identity (exact, from the Bessel Wronskian
  J1*Y0 - J0*Y1 = 2/(pi*k)): |S(k)| = (2/(pi*k))/|H1^(2)(k) +
  i*H0^(2)(k)| for k > 0.
- Gust-load amplitudes per unit span (N/m): quasi-steady reference
  L_qs = 2*pi*rho*V*b*w_g_amp; unsteady amplitude L_hat = L_qs*|S(k)| =
  2*pi*rho*V*b*w_g_amp*|S(k)|.

Functions (implement with exactly these signatures; pure math only):
- bessel_j0(x) -> float, bessel_j1(x) -> float, bessel_y0(x) -> float,
  bessel_y1(x) -> float: the A&S series above. ValueError if x <= 0.0 or
  not finite.
- theodorsen_c(k) -> complex: C(k) by the Hankel ratio. k = 0.0 returns
  exactly 1.0 + 0.0j. ValueError if k < 0.0 or not finite.
- sears_function(k) -> complex: S(k) = [C(k)*(J0(k) - i*J1(k)) +
  i*J1(k)]*e^(-i*k). k = 0.0 returns exactly 1.0 + 0.0j. ValueError if
  k < 0.0 or not finite.
- sears_gain(k) -> float: |S(k)|, the unsteady-load ratio to the
  quasi-steady reference. ValueErrors as sears_function.
- sears_phase_lag(k) -> float: phi(k) = -arg S(k) in radians, the value
  of atan2(-S(k).imag, S(k).real) in (-pi, pi]. ValueErrors as
  sears_function.
- reduced_frequency(freq_hz, v, b) -> float: k = 2*pi*freq_hz*b/v.
  ValueError if any input is non-positive or not finite.
- quasi_steady_gust_lift(rho, v, b, w_g_amp) -> float: L_qs =
  2*pi*rho*v*b*w_g_amp. ValueError if rho, v or b is non-positive or not
  finite, or w_g_amp is negative or not finite (zero amplitude is
  allowed).
- unsteady_gust_load(rho, v, b, w_g_amp, k) -> float:
  L_qs*|S(k)|. ValueErrors as quasi_steady_gust_lift plus k < 0.0.
- half_gain_reduced_frequency(k_lo = BISECT_LO, k_hi = BISECT_HI) ->
  float: deterministic bisection (120 iterations) on |S(k)| = 0.5 over
  [k_lo, k_hi], which brackets 0.5 because the gain is monotone
  decreasing. ValueError if the bracket is reversed or 0.5 is not
  bracketed (sears_gain(k_lo) <= 0.5 or sears_gain(k_hi) >= 0.5).

Identities to test (closed form, deterministic; all values REAL anchor
outputs of /tmp/w45spec/anchor_sears_function_gust_lift.py, stdlib math,
exit 0):
- Bessel constants: at x = 0.5: J0 = 0.938469807240813,
  J1 = 0.2422684576748739, Y0 = -0.4445187335067066,
  Y1 = -1.471472392670243; at x = 1.0: J0 = 0.7651976865579666,
  J1 = 0.4400505857449336, Y0 = 0.088256964215677,
  Y1 = -0.7812128213002887; at x = 2.0: J0 = 0.2238907791412356,
  J1 = 0.5767248077568736, Y0 = 0.5103756726497453,
  Y1 = -0.1070324315409374; worst absolute error of the series against
  the published constants is 9.44e-16.
- Theodorsen function: C(0) = 1 + 0i exactly; C(0.5) =
  0.597936064250132 - 0.1507095031626353i with |C| = 0.6166367579657139;
  C(1.0) = 0.5394348710777939 - 0.1002729028641078i with |C| =
  0.5486753458863547; C(2.0) = 0.5129548124291317 -
  0.05769128342167992i with |C| = 0.5161888450722721 (|C| falls toward
  the flutter sibling's documented high-k limit 1/2).
- Sears function: S(0) = 1 + 0i exactly with gain 1 and zero phase lag;
  S(0.1) = 0.800817849647392 - 0.244649056217272i, gain
  0.8373543986997829, lag 0.2964940866019039 rad (16.98785981287542
  deg); S(0.25) = 0.6026337749688766 - 0.3027386944162097i, gain
  0.6744020935836941, lag 0.4655332845434467 rad (26.67309242720233
  deg); S(0.5) = 0.4392999993899336 - 0.2901613576384412i, gain
  0.5264770678107253, lag 0.5837270902719581 rad (33.44509866003521
  deg); S(1.0) = 0.3051596787128952 - 0.2421600879532278i, gain
  0.3895689126581746, lag 0.6707968790189207 rad (38.43383007833184
  deg); S(2.0) = 0.2097218163963314 - 0.1856916381211891i, gain
  0.2801153775512997, lag 0.7247005314150557 rad (41.52228186097062
  deg).
- Closed-form gain identity: |S(k)| = (2/(pi*k))/|H1^(2)(k) +
  i*H0^(2)(k)| over the whole sweep k in [0.1, 2.0], REAL anchor max
  residual 2.22e-16 (the Bessel Wronskian makes the mid-chord form
  S_mid = C*(J0 - i*J1) + i*J1 = i*(2/(pi*k))/(H1^(2) + i*H0^(2)) an
  exact algebraic identity, so gain and phase are one theory).
- Quasi-steady limit and monotonicity: |S(0)| = 1 exactly (the
  quasi-steady limit consistent with L_qs = 2*pi*rho*V*b*w_g, the
  reference the aeroelastic-gust-response sibling documents for its
  discrete-gust model); the gain is monotone decreasing and the phase
  lag monotone increasing over the 0.1 to 2.0 sweep (anchor True, True);
  the half-amplitude reduced frequency is k_half = 0.5672427076304547
  with |S(k_half)| = 0.5000000000000001, inside the [0.1, 2.0] sweep.
- Sibling cross-validation: the module's C(0.5) = 0.597936064250132 -
  0.1507095031626353i and C(1.0) = 0.5394348710777939 -
  0.1002729028641078i reproduce the classic published Theodorsen values
  (C(0.5) ~ 0.598 - 0.151i, C(1) ~ 0.539 - 0.100i in the standard
  tables, the family the flutter sibling's own Bessel machinery is
  built on), so the two leaves agree where their C(k) evaluations touch.
- ValueErrors across the module: bessel_j0(0.0), bessel_j1(-1.0),
  bessel_y0(0.0), bessel_y1(0.0), theodorsen_c(-0.5),
  sears_function(-0.5), sears_function(float("nan")),
  quasi_steady_gust_lift(0.0, 80.0, 1.0, 5.0) and
  quasi_steady_gust_lift(1.225, 80.0, 1.0, -5.0),
  unsteady_gust_load(1.225, 80.0, 1.0, 5.0, -0.5),
  reduced_frequency(0.0, 80.0, 1.0), half_gain_reduced_frequency(2.0,
  0.1) (reversed bracket). All 12 anchor cases raise (anchor True).
- Determinism: two identical full sweeps return identical bits (anchor
  True); S(0) exact; no imports beyond math; no RNG; no gas-gamma
  constant anywhere.

## Worked example

Representative point: rigid thin section of chord c = 2 m (semi-chord
b = 1 m) at V = 80 m/s in standard sea-level air rho = 1.225 kg/m^3,
encountering a sinusoidal vertical gust of amplitude w_g_amp = 5 m/s at
reduced frequency k = 0.5 (gust frequency f = k*V/(2*pi*b) =
6.366197723675814 Hz, gust wavelength lambda = V/f =
12.56637061435917 m = 6.283185307179586 chord lengths). All values
below are REAL outputs of the prep anchor
/tmp/w45spec/anchor_sears_function_gust_lift.py (stdlib math,
deterministic, exit 0; identical under /usr/bin/python3 3.9.6 and
~/.pyenv/versions/3.13.12/bin/python3).

- Quasi-steady reference: L_qs = 2*pi*rho*V*b*w_g_amp =
  3078.760800517998 N/m, the amplitude the same gust would produce at
  k = 0 (the rigid quasi-steady value the aeroelastic-gust-response
  sibling documents as L_qs = 2*pi*rho*V*b*w_g).
- Complex Sears function at k = 0.5: S(0.5) =
  0.4392999993899336 - 0.2901613576384412i (leading-edge gust
  reference). Gust gain |S(0.5)| = 0.5264770678107253, so the
  unsteady gust load retains 52.65 percent of the quasi-steady
  amplitude at this reduced frequency.
- Phase lag: phi(0.5) = 0.5837270902719581 rad = 33.44509866003521 deg:
  the lift peak follows the gust peak at the leading edge by
  phi/omega = 0.014593 s (omega = k*V/b = 40 rad/s at the worked
  point).
- Unsteady gust-load amplitude: L_hat = L_qs*|S(0.5)| =
  1620.896958747317 N/m per unit span (the amplitude a rigid-section
  sinusoidal-gust load estimate would carry into a structural check).
- Half-amplitude reduced frequency: |S(k)| = 0.5 at k_half =
  0.5672427076304547 (within the corpus query's 0.1 to 2.0 sweep; the
  gain has fallen from 1 at k = 0 to 0.5265 at k = 0.5), where L_hat =
  1539.380400258999 N/m = 0.5000000000000001*L_qs exactly.
- Read-off: the gain table |S(0.1)| = 0.8373543986997829,
  |S(0.5)| = 0.5264770678107253, |S(1.0)| = 0.3895689126581746,
  |S(2.0)| = 0.2801153775512997 shows the monotone roll-off; even a
  gust a full 6.28 chords long (k = 0.5) loads the rigid section at
  about half the quasi-steady amplitude, and the phase lag grows from
  0 to 41.52 deg across the sweep, the signature of the convected-gust
  response the flexible-section time-domain sibling does not produce.
Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of /tmp/w45spec/
anchor_sears_function_gust_lift.py (stdlib math, deterministic, exit 0).

## Validation list (contract test must include)

- Bessel constants: at x = 0.5, 1.0 and 2.0 each of J0, J1, Y0, Y1
  equals the published-constant digits listed under Identities within
  1e-12 absolute (REAL anchor worst error 9.44e-16).
- theodorsen_c(0.5) = 0.597936064250132 - 0.1507095031626353i within
  1e-9 on each part; theodorsen_c(1.0) = 0.5394348710777939 -
  0.1002729028641078i within 1e-9; theodorsen_c(2.0) =
  0.5129548124291317 - 0.05769128342167992i within 1e-9; |C(0.5)| =
  0.6166367579657139 within 1e-9; theodorsen_c(0.0) is exactly 1 + 0j;
  |C(2.0)| = 0.5161888450722721 within 1e-9, above the 0.5 limit.
- sears_function complex values at k = 0.1, 0.25, 0.5, 1.0, 2.0 equal
  the Identities digits within 1e-9 on each part (relative to max(1,
  |part|)); sears_gain values 0.8373543986997829 (0.1),
  0.5264770678107253 (0.5), 0.3895689126581746 (1.0),
  0.2801153775512997 (2.0) within 1e-9 absolute; sears_phase_lag values
  0.2964940866019039 (0.1), 0.5837270902719581 (0.5),
  0.6707968790189207 (1.0), 0.7247005314150557 (2.0) within 1e-9 rad;
  sears_function(0.0) is exactly 1 + 0j and sears_gain(0.0) exactly 1.0
  (the quasi-steady limit).
- Closed-form gain identity: |sears_gain(k) -
  (2/(pi*k))/|H1^(2)(k) + i*H0^(2)(k)|| < 1e-12 at every 0.1 step of
  k in [0.1, 2.0] with H1^(2), H0^(2) built in the test from the public
  bessel_j0/j1/y0/y1 functions (REAL anchor max residual 2.22e-16).
- Half-amplitude: half_gain_reduced_frequency() = 0.5672427076304547
  within 1e-9; sears_gain(0.5672427076304547) = 0.5 within 1e-9;
  sears_gain(0.5) > 0.5 > sears_gain(0.6) (bracket sanity);
  half_gain_reduced_frequency(2.0, 0.1) raises ValueError (reversed
  bracket), as does a bracket that does not straddle 0.5.
- Monotonicity: sears_gain strictly decreasing and sears_phase_lag
  strictly increasing at every 0.05 step of k in [0.1, 2.0] (anchor
  monotone True for both over the 0.1-step sweep); the k_half crossing
  therefore sits in the swept range.
- Worked example at b = 1 m, V = 80 m/s, rho = 1.225 kg/m^3,
  w_g_amp = 5 m/s, k = 0.5: quasi_steady_gust_lift =
  3078.760800517998 N/m within 1e-6 relative; unsteady_gust_load =
  1620.896958747317 N/m within 1e-6 relative; the ratio
  L_hat/L_qs equals sears_gain(0.5) within 1e-12;
  reduced_frequency(6.366197723675814, 80.0, 1.0) = 0.5 within 1e-12;
  lambda = V/f = 12.56637061435917 m = 6.283185307179586 chords;
  phase lag 0.5837270902719581 rad = 33.44509866003521 deg within
  1e-9; at k_half the unsteady load is 1539.380400258999 N/m within
  1e-6 relative and the ratio to L_qs is 0.5000000000000001 within
  1e-9.
- ValueErrors (the 12 anchor cases under Identities): zero or negative
  Bessel arguments, negative or non-finite k, negative or non-finite
  w_g_amp, non-positive rho/V/b/freq, zero frequency, reversed
  half-gain bracket; every case raises ValueError.
- Determinism: two identical full sweeps return identical bits; no
  imports beyond math; no RNG. Test passes under BOTH interpreters
  (/usr/bin/python3 3.9.6 and ~/.pyenv/versions/3.13.12/bin/python3).
  No exact-float equality on computed sums; use
  assertAlmostEqual/math.isclose everywhere. Contract test file named
  test_sears_function_gust_lift.py (underscores), unittest, offline in
  under 20 seconds.

## Corpus fragment (2 verbatim queries for
eval/hit1-wave45-sears-function-gust-lift.yaml)

Query 1 (copy verbatim):
  "evaluate the sears-function lift response of the rigid airfoil to a
  sinusoidal-gust field at reduced frequency 0.5: compute the complex
  sears-function from the Bessel series, the gust gain and phase lag,
  and the unsteady gust-load amplitude against the quasi-steady
  2 pi rho V b w_g reference"
  intent: "aerodynamics; sears-function sinusoidal-gust response of the
  rigid thin airfoil: complex sears function from the Bessel series,
  gust gain and phase lag, unsteady gust-load amplitude against the
  2 pi rho V b w_g quasi-steady reference"
  expected_skill: "aerodynamics/aeroelasticity/sears-function-gust-lift"
Query 2 (copy verbatim):
  "sweep the sears-function gain of the thin airfoil in the
  sinusoidal-gust encounter across reduced frequencies 0.1 to 2.0 and
  report the reduced frequency where the unsteady gust-load amplitude
  falls to half the quasi-steady value"
  intent: "aerodynamics; sears-function gain sweep across reduced
  frequencies 0.1 to 2.0 and the half-amplitude reduced frequency of
  the unsteady gust load"
  expected_skill: "aerodynamics/aeroelasticity/sears-function-gust-lift"
Task ids: w45-sears-function-gust-lift-1 and -2. Prep grep and probe:
"sears-function", "sears function", "sinusoidal-gust" and
"gust-transfer-function" appear in NO existing eval/hit1-corpus.yaml
task and in NO skills/ file (0 hits each, real greps, exit 1); the only
corpus "sears" matches are the two Sears-Haack-body tasks (wd1/wd2,
expected_skill wave-drag-area-rule), the only "gust" tasks route to
gust-maneuver-loads and aeroelastic-gust-response, and the corpus
"theodorsen" tasks route to flutter-speed-prediction. The queries
deliberately carry the sears-function and sinusoidal-gust hyphenated
tokens because the wave-drag-area-rule sears-haack tag and the
aeroelastic-gust-response gust tokens are live steal risks for
bare-worded queries.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the frequency-domain
gust response of a rigid thin airfoil to a convected sinusoidal vertical
gust:" and include the outputs in the Claim. First tag: sears-function.
Additional tags ONLY the receipt's gate (f) list, verbatim:
sears-function, sinusoidal-gust, unsteady-gust-load,
gust-transfer-function, reduced-frequency-gust. NEVER the bare single
words sears (collides with the sears-haack body of wave-drag-area-rule),
gust, airfoil, unsteady, and NEVER the sibling tokens
aeroelastic-gust-response, dynamic-gust-response, kussner-function,
wagner-function, indicial-aerodynamics, dynamic-magnification-factor,
typical-section-gust, unsteady-aerodynamics, gust-response-history
(aeroelastic-gust-response), flutter-speed, v-g-method, bending-torsion,
typical-section, frequency-coalescence, flutter-margin, theodorsen,
reduced-frequency (the bare word; only the compound
reduced-frequency-gust is allowed), far-25-629, aeroelasticity
(flutter-speed-prediction), divergence-speed, wave-drag, area-rule,
sears-haack, drag-divergence, cross-sectional-area
(wave-drag-area-rule), virtual-mass, apparent-mass,
acceleration-reaction-force, kinetic-energy-catalog
(added-mass-coefficients-potential-flow), discrete-gust,
gust-alleviation-factor, gust-load-factor, v-n-diagram
(gust-maneuver-loads), and never dryden-spectrum, von-karman-spectrum,
power-spectral-density (the structures loads family). 50-150 words,
<=1000 chars, no em dash, action verb present. Recommended wording
(outputs in Claim order): "Use when you must compute the frequency-domain
gust response of a rigid thin airfoil to a convected sinusoidal vertical
gust: evaluate the complex sears-function S(k) from the Bessel series
with the Theodorsen lift-deficiency function, the gust gain and the
phase lag of the gust load, and the unsteady gust-load amplitude against
the quasi-steady 2*pi*rho*V*b*w_g reference, with the |S| = 1
quasi-steady limit at zero reduced frequency, the monotone gain
roll-off, and the reduced frequency where the gust load falls to half
the quasi-steady value. Produces the complex sears function, gain and
phase tables versus reduced frequency, and the unsteady gust-load
amplitudes that gate sinusoidal-gust load estimates and unsteady
thin-airfoil coursework. Trigger: sears function, sinusoidal gust,
gust transfer function, unsteady gust load, gust reduced frequency
sweep." The sibling triggers "kussner", "wagner", "indicial",
"one-minus-cosine gust", "dynamic magnification factor", "flutter",
"v-g method", "sears-haack" and "area rule" must not appear. ZERO em
dashes in every file; never the word "classified" in prose. Standards
reference-only: far-25 and cs-25 named as the certification gust
context (the FAR 25 and CS 25 gust-load rules frame the context; the
Sears relations are standard engineering methodology, summary-only),
never reproduced verbatim.
