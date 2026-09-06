# Wave-42 leaf spec: thin-airfoil-section-theory (aerodynamics, airfoil pack)

- Path: skills/aerodynamics/airfoil/thin-airfoil-section-theory/
- Pack: airfoil (present siblings airfoil-geometry,
  airfoil-selection, airfoil-optimization, xfoil-analysis; adjacent
  fences in aerodynamics/drag-polars/lift-curve-slope, where the
  wave-22 routing lesson lives, and aerodynamics/cfd/panel-method).
- Claim fences (quoted from the sibling frontmatter at prep, none owns
  section coefficients derived from the camber line):
  - lift-curve-slope (drag-polars pack) is the FINITE-WING slope leaf
    from GIVEN section data: its description reads "compute the
    thin-airfoil section slope a0 = 2*pi per radian, correct it for
    finite aspect ratio with the lifting-line formula a = a0 / (1 + a0
    / (pi * e * AR)), apply the simple sweep theory cosine correction,
    apply the Prandtl-Glauert Mach correction a / sqrt(1 - M^2) with a
    documented M < 0.7 limit, and predict lift coefficient from angle
    of attack with C_L = a * (alpha - alpha_zero), including an
    optional stall guard", and its body states "Camber shifts the
    zero-lift angle, it does not change the thin-airfoil slope". It
    takes alpha_zero and the section slope as INPUTS and never derives
    section data from geometry; its tag list owns thin-airfoil-theory,
    which this leaf MUST NOT reuse.
  - airfoil-geometry (this pack) is ordinate geometry only: its
    description reads "compute the 4-digit thickness distribution,
    mean camber line ordinates and slope; and derive leading-edge
    radius and section area from the public-domain NACA formulas",
    with workflow "Compute camber ordinates and slope with camber_ord
    and camber_slope". It produces ordinates, slope, radius and area;
    it never forms Glauert coefficients or section forces.
  - xfoil-analysis (this pack) and panel-method (cfd pack) are the
    numerical/viscous layers that CONSUME an analytic section result
    as their verification anchor; neither is the closed-form analytic
    section solution (prep probe note, GO-2 fence check).
  Whole-tree greps at prep (probe receipt): "glauert" hits only
  Prandtl-Glauert compressibility contexts (lift-curve-slope,
  transonic-similarity, windtunnel-data-reduction); "zero-lift angle"
  hits lift-curve-slope (as input data) and flight-mechanics
  trim-analysis; "camber line" hits airfoil-geometry only (ordinate
  geometry). No leaf computes section coefficients FROM the camber
  line. Corpus tasks 1222 and 1225 carry thin-airfoil tokens but are
  wing-slope tasks and must keep routing to lift-curve-slope.
- Standards id: naca-tr-824 (reference-only, present in
  standards-map.yaml). Ledger Standard: naca-tr-824.
- Family: aerodynamics

## Claim

Compute the analytic section aerodynamics of a thin cambered airfoil
from its camber line: decompose the camber slope dz/dx into the Glauert
sine-series coefficients A0, A1, A2 by trapezoid quadrature over the
theta transform x = (1 - cos(theta))/2, then recover the section
zero-lift angle alpha_L0, the section lift coefficient
cl = 2*pi*(alpha - alpha_L0), the quarter-chord pitching-moment
coefficient cm_c4 = (pi/4)*(A2 - A1) and the center-of-pressure
location x_cp/c = 1/4 - cm_c4/cl, for a NACA 4-digit mean line given by
its (m, p) camber parameters, a power-series polynomial camber line, or
a sampled (x, z) camber-line point list. Produces the analytic section
aerodynamics that anchor the panel and viscous section tools beneath
them, in closed form with quadrature only for the Fourier integrals.
Does NOT do: the finite-wing slope from given section data with the
lifting-line, sweep or Prandtl-Glauert corrections, or lift coefficient
from a given alpha_zero input (lift-curve-slope, which owns the
thin-airfoil-theory tag); airfoil ordinates, thickness distributions,
leading-edge radius, section area or designation decode
(airfoil-geometry); numerical panel or viscous section results for a
given coordinate set (xfoil-analysis, panel-method). The camber line
geometry is consumed as input from the airfoil-geometry formulas, not
re-derived as a deliverable. Incompressible potential flow only: no
Mach effects, no viscosity, no stall.

## Model (implement exactly)

Pure stdlib, math only. Module constant PI = math.pi. Transformation
x = (1 - cos(theta))/2 over theta in [0, pi]; the camber slope
dz/dx(theta) is integrated by the trapezoid rule on a uniform theta
grid including both endpoints with n_theta intervals.

Defining relations (pin these exactly; every function below derives
from them):
- NACA 4-digit mean line (consumed per the airfoil-geometry formulas):
  for x <= p, z = (m/p^2)*(2*p*x - x^2) and
  dz/dx = (2*m/p^2)*(p - x); for x >= p,
  z = (m/(1-p)^2)*(1 - 2*p + 2*p*x - x^2) and
  dz/dx = (2*m/(1-p)^2)*(p - x); slope zero at x = p.
- Glauert coefficients (gamma(theta) = 2*U*(A0*(1+cos)/sin +
  A1*sin(theta) + A2*sin(2*theta))):
  A0 = alpha - (1/pi)*int_0^pi dz/dx dtheta;
  A1 = (2/pi)*int_0^pi dz/dx*cos(theta) dtheta;
  A2 = (2/pi)*int_0^pi dz/dx*cos(2*theta) dtheta.
- Zero-lift angle: alpha_L0 = (1/pi)*int dz/dx*(1 - cos(theta)) dtheta,
  identically -A0(alpha = 0) - A1/2 (both routes agree to machine
  noise; the identity A0(alpha_L0) = -A1/2 holds exactly).
- Section lift: cl = 2*pi*A0 + pi*A1 = 2*pi*(alpha - alpha_L0).
- Quarter-chord moment (classical text relation, anchor-verified):
  cm_c4 = (pi/4)*(A2 - A1), equivalently cm_le + cl/4 with
  cm_le = -(pi/2)*(A0 + A1) + (pi/4)*A2. WARNING: the prep note
  carried a candidate form cm_c4 = -(pi/4)*(A1 + A2); the anchor
  REJECTS it. At the 2412 point the two readings differ by
  (pi/2)*A2 = +0.021773242156, and only (pi/4)*(A2 - A1) satisfies the
  independent consistency identity cm_c4 = cm_le + cl/4 (both paths
  give -0.053119513461 to 6.9e-17). The A1 + A2 reading coincides with
  the classical one only when A2 = 0 (parabolic mean lines), where the
  exact closed-form check cm_c4 = -pi*m is unambiguous. Implement
  (pi/4)*(A2 - A1).
- Center of pressure: x_cp/c = 1/4 - cm_c4/cl.

Functions:
- glauert_coefficients_naca4(alpha_rad, m, p, n_theta=40000)
  -> (A0, A1, A2, alpha_L0): NACA 4-digit mean-line route, slope from
  the defining relations. ValueError if m < 0 or m > 0.1 (max camber
  fraction out of the 4-digit range), p <= 0 or p >= 1, or
  n_theta not an int >= 100.
- glauert_coefficients_poly(alpha_rad, coeffs, n_theta=40000)
  -> (A0, A1, A2, alpha_L0): polynomial camber route, z(x) =
  sum(coeffs[i]*x^i) for i over the list, dz/dx = sum(i*coeffs[i]*
  x^(i-1)) for i >= 1. ValueError if coeffs is not a non-empty list or
  tuple, or n_theta invalid.
- glauert_coefficients_points(alpha_rad, xs, zs, n_theta=40000)
  -> (A0, A1, A2, alpha_L0): sampled camber route, piecewise-linear
  camber with constant slope per segment. ValueError if len(xs) !=
  len(zs) or fewer than 2 points, xs not strictly increasing, xs does
  not span exactly [0, 1], or n_theta invalid.
- lift_coefficient(alpha_rad, alpha_L0_rad) -> float: 2*pi*
  (alpha_rad - alpha_L0_rad). No range guards (thin-airfoil linear
  range; stall is out of scope).
- quarter_chord_moment(A1, A2) -> float: (pi/4)*(A2 - A1). No guards.
- center_of_pressure_over_chord(cl, cm_c4) -> float:
  1/4 - cm_c4/cl. ValueError if abs(cl) < 1e-12 (no defined cp at zero
  lift).

Identities to test (closed form, exact):
- Parabolic mean line z = 4*m*x*(1-x), max camber m at mid-chord
  (equivalently the NACA 4-digit mean line at p = 0.5): A1 = 4*m,
  A2 = 0, alpha_L0 = -2*m, cm_c4 = -pi*m, cl(alpha = 0) = 4*pi*m, all
  recovered to ~1e-12 by quadrature (the KNOWN-EXACT anchor).
- Zero camber (flat mean line): A0 = alpha, A1 = A2 = alpha_L0 =
  cm_c4 = 0, cl = 2*pi*alpha.
- alpha_L0 direct integral equals -A0(alpha = 0) - A1/2 to 1e-12, and
  A0 evaluated at alpha = alpha_L0 equals -A1/2 to 1e-12 (cl vanishes
  at the zero-lift angle).
- cl = 2*pi*A0 + pi*A1 equals 2*pi*(alpha - alpha_L0) to 1e-12.
- cm_c4 = (pi/4)*(A2 - A1) equals cm_le + cl/4 with
  cm_le = -(pi/2)*(A0 + A1) + (pi/4)*A2 to 1e-12 (rejects the
  A1 + A2 mistranscription, whose error is (pi/2)*A2).
- Quadrature convergence: A1 at n_theta = 40000 agrees with
  n_theta = 1000000 to 1e-12 (kinked 4-digit slopes converge; smooth
  mean lines reach 1e-15).
- Sample-point route: a 4001-station sample of the parabola recovers
  alpha_L0 = -2*m and A1 = 4*m to ~1e-6; a 4001-station sample of the
  2412 mean line agrees with the analytic route to ~1e-7 in alpha_L0.
- ValueErrors across the module: m = -0.01 and m = 0.2; p = 0 and
  p = 1; n_theta = 10; empty coeffs; non-monotone xs; xs not starting
  at 0; center_of_pressure_over_chord at cl = 0.

## Worked example

NACA 2412 mean line (m = 0.02, p = 0.4) at alpha = 4 deg =
0.069813170080 rad (the section whose camber line airfoil-geometry also
handles, so both leaves can be cross-checked on the same airfoil). All
values below are REAL outputs of the prep anchor
/tmp/w42spec/anchor_thin_airfoil_section_theory.py (stdlib math,
trapezoid quadrature, n_theta = 40000 default).
- glauert_coefficients_naca4(0.069813170080, 0.02, 0.4):
  A0 = 0.065320283700, A1 = 0.081495141601,
  A2 = 0.013861276465, alpha_L0 = -0.036254684420 rad =
  -2.077240404870 deg: the exact thin-airfoil zero-lift angle of the
  2412 mean line, within a few hundredths of a degree of the measured
  section value near -2 deg.
- alpha_L0 by the derived identity -A0(0) - A1/2 gives
  -0.036254684420 rad, agreeing with the direct integral to 2.1e-17;
  A0(alpha_L0) = -0.040747570801 equals -A1/2 to 2.1e-17.
- cl = 2*pi*(0.069813170080 - (-0.036254684420)) =
  0.666443984960, matching cl = 2*pi*A0 + pi*A1 to 2.2e-16. At
  alpha = 0, cl = 0.227794900467.
- cm_c4 = (pi/4)*(A2 - A1) = (pi/4)*(0.013861276465 -
  0.081495141601) = -0.053119513461, near the familiar measured 2412
  section cm0.25 of about -0.05. Independent route: cm_le + cl/4 with
  cm_le = -(pi/2)*(A0 + A1) + (pi/4)*A2 gives the same value to 6.9e-17.
  The mistranscribed -(pi/4)*(A1 + A2) = -0.074892755617 would be off
  by (pi/2)*A2 = +0.021773242156 and fails the identity: rejected by
  the anchor.
- x_cp/c = 1/4 - cm_c4/cl = 0.25 - (-0.053119513461/0.666443984960) =
  0.329705893759: the cp sits at 0.330 chord at 4 deg and moves back
  toward the quarter chord as cl grows.
- Quadrature convergence of A1 at the kinked 2412 slope: n = 1000 ->
  0.081495138139, n = 10000 -> 0.081495141553, n = 40000 and above ->
  0.081495141601; A1(40000) - A1(1000000) = 3.0e-13, so the default
  resolution is converged to all printed digits.
- KNOWN-EXACT validation on the parabolic mean line z = 4*m*x*(1-x),
  m = 0.04 (polynomial route, coeffs [0.0, 0.16, -0.16]) at 4 deg:
  exact closed forms are alpha_L0 = -2*m = -0.08 rad,
  A1 = 4*m = 0.16, A2 = 0, cm_c4 = -pi*m = -0.125663706144,
  cl = 2*pi*(alpha + 2*m) and cl(0) = 4*pi*m = 0.502654824574.
  Quadrature recovers alpha_L0 = -0.080000000000 (1.5e-16),
  A1 = 0.160000000000 (6.4e-16), A2 = 0.000000000000 (2.7e-17),
  cl(4 deg) = 0.941303909067 (1.0e-15), cm_c4 = -0.125663706144
  (4.7e-16); x_cp/c(4 deg) = 0.383499611478. The NACA 4-digit route at
  p = 0.5 reproduces the parabola exactly: A1 = 0.160000000000,
  alpha_L0 = -0.080000000000, cm_c4 = -0.125663706144.
- Flat mean line (coeffs [0.0, 0.0]): A0 = 0.069813170080 = alpha,
  A1 = A2 = alpha_L0 = cm_c4 = 0.000000000000.
- Sample-point route: the parabola sampled at 4001 stations gives
  alpha_L0 = -0.079999658257 (3.4e-7 from -2*m) and
  A1 = 0.159999318515 (6.8e-7 from 4*m); the 2412 camber sampled at
  4001 stations gives alpha_L0 = -0.036254564543 rad =
  -2.077233536425 deg and cm_c4 = -0.053119329442, within 1.2e-7 rad
  and 1.8e-7 of the analytic route.
Run your module and take the real outputs as assert targets; the
anchors above are prep-verified by running the prep anchor script
/tmp/w42spec/anchor_thin_airfoil_section_theory.py (stdlib math).

## Validation list (contract test must include)

- glauert_coefficients_naca4(0.069813170080, 0.02, 0.4): A0 =
  0.065320283700, A1 = 0.081495141601, A2 = 0.013861276465,
  alpha_L0 = -0.036254684420 within 1e-9.
- lift_coefficient(0.069813170080, -0.036254684420) = 0.666443984960
  within 1e-9; lift_coefficient(0.0, -0.036254684420) =
  0.227794900467 within 1e-9.
- quarter_chord_moment(0.081495141601, 0.013861276465) =
  -0.053119513461 within 1e-9.
- center_of_pressure_over_chord(0.666443984960, -0.053119513461) =
  0.329705893759 within 1e-9.
- Parabolic closed form, poly route at 4 deg (coeffs [0.0, 0.16,
  -0.16], m = 0.04): alpha_L0 = -0.080000000000 within 1e-9,
  A1 = 0.160000000000 within 1e-9, A2 = 0.0 within 1e-9,
  cm_c4 = -0.125663706144 within 1e-9, cl(4 deg) = 0.941303909067
  within 1e-9, cl(0) = 0.502654824574 within 1e-9 (exact forms to
  1e-12).
- NACA 4-digit route with p = 0.5, m = 0.04 reproduces the parabola:
  A1 = 0.160000000000, alpha_L0 = -0.080000000000,
  cm_c4 = -0.125663706144 within 1e-9.
- Flat mean line: A0 = alpha, A1 = A2 = alpha_L0 = cm_c4 = 0 within
  1e-12.
- Identities to 1e-12: alpha_L0 direct equals -A0(0) - A1/2;
  A0(alpha_L0) = -A1/2; cl via 2*pi*A0 + pi*A1 equals the
  alpha-based form; cm_c4 = (pi/4)*(A2 - A1) equals cm_le + cl/4 with
  cm_le = -(pi/2)*(A0 + A1) + (pi/4)*A2.
- Convergence: A1 at n_theta = 1000000 differs from n_theta = 40000 by
  3.0e-13 for the 2412 mean line.
- Points route: 4001-station parabola alpha_L0 = -0.079999658257
  within 1e-6; 4001-station 2412 mean line alpha_L0 =
  -0.036254564543 and cm_c4 = -0.053119329442 within 5e-7 of the
  analytic route.
- ValueErrors: m = -0.01 and m = 0.2; p = 0.0 and p = 1.0; n_theta =
  10; empty coeffs; non-monotone xs; xs not starting at 0.0;
  center_of_pressure_over_chord at cl = 0.0.
- Determinism; no imports beyond math; PI = math.pi.

## Corpus fragment (eval/hit1-wave42-thin-airfoil-section-theory.yaml)

Query 1 (copy verbatim):
  "compute the zero-lift-angle and the quarter-chord-pitching-moment coefficient of a NACA 2412 from its camber-line slope with the glauert-sine-series coefficients"
  intent: "aerodynamics; section zero-lift angle and quarter-chord
  pitching-moment coefficient of a cambered thin airfoil derived from
  its camber-line slope via the Glauert A0/A1/A2 sine series"
  expected_skill: "aerodynamics/airfoil/thin-airfoil-section-theory"
Query 2 (copy verbatim):
  "derive the section lift coefficient cl at a given alpha from the thin-airfoil A0 and A1 Fourier coefficients of a cambered airfoil"
  intent: "aerodynamics; section lift coefficient cl of a cambered
  thin airfoil from the thin-airfoil A0/A1 Fourier coefficients"
  expected_skill: "aerodynamics/airfoil/thin-airfoil-section-theory"
Task ids: w42-thin-airfoil-section-theory-1 and -2. Prep grep: no
existing skill body or hit1-corpus task contains the distinctive
phrases (glauert-sine-series, zero-lift-angle from a camber-line slope,
quarter-chord-pitching-moment, A0/A1 Fourier coefficients of a cambered
airfoil); the corpus tasks that carry thin-airfoil tokens (1222, 1225)
are explicitly wing-slope tasks whose wing/finite-wing tokens keep them
routing to lift-curve-slope (verify in the pre-merge routing sim), and
the lift-curve-slope leaf consumes alpha_zero as input rather than
deriving section coefficients from a camber line, so the queries above
are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open with the exact sentence "Use when you must
compute the section lift and the quarter-chord pitching moment of a
thin cambered airfoil from its camber line:" and continue with the
outputs in the Claim: the glauert-sine-series coefficients A0/A1/A2 by
trapezoid quadrature, the zero-lift-angle, cl = 2*pi*(alpha -
alpha_L0), the quarter-chord pitching-moment coefficient
cm_c4 = (pi/4)*(A2 - A1) and the center-of-pressure location, for a
NACA 4-digit mean line, a polynomial camber line or sampled camber
stations, ending with a "Trigger:" list (glauert coefficients, zero
lift angle, section pitching moment, camber line analysis, thin airfoil
section). 50-150 words, <=1000 chars, no em dash, no content-policy
sweep term (the banned word from the builder kit), action verb present
(the opening "compute" satisfies it). First tag:
thin-airfoil-section-theory. Additional tags ONLY:
glauert-sine-series, zero-lift-angle, quarter-chord-moment,
camber-line. NEVER single generic words (airfoil, theory, lift, camber,
moment, angle, slope, coefficient, section, chord, moment-coefficient).

FORBIDDEN TOKENS (belong to siblings): thin-airfoil-theory (tag and
any tag-like use, owned by lift-curve-slope per the wave-22 routing
lesson), wing, finite-wing, finite-wing-correction, lifting-line,
aspect-ratio, span-efficiency, elliptic-loading, sweep-correction,
prandtl-glauert, mach-correction, wing-lift-curve-slope,
alpha-zero-as-input, stall-guard, section-slope-as-input,
lift-coefficient-from-angle-of-attack (lift-curve-slope);
thickness-distribution, airfoil-ordinates, surface-ords,
leading-edge-radius, section-area, designation-decode,
mean-line-ordinate-generation, airfoil-coordinates,
thickness-formula (airfoil-geometry); panel-method, vortex-panel,
boundary-layer-coupling, viscous-analysis, transition-tripping,
xfoil-analysis, numerical-section-analysis (xfoil-analysis,
panel-method); compressibility, mach-number-correction, swept-wing
(high-speed siblings). The corpus queries and description must stay in
the glauert-sine-series / zero-lift-angle / quarter-chord-moment /
camber-line vocabulary only.
