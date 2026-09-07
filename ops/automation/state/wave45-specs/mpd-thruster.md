# Wave-45 leaf spec: mpd-thruster (propulsion, electric pack)

- Path: skills/propulsion/electric/mpd-thruster/
- Pack: electric (present siblings hall-thruster, gridded-ion-thruster,
  electrothermal-thruster; adjacent fences in propulsion/rocket (rocket-sizing
  owns the delta-v and propellant-mass mission loop around a single thruster
  operating point, rocket-nozzle-design owns chemical nozzle expansion); the
  wave-45 whole-family probe GO-1 at HEAD 5cc8fef3 by probe task-3).
- Claim fences (quoted from the sibling frontmatter/body at prep; none claims
  the self-field ELECTROMAGNETIC (JxB) acceleration mechanism, the pack's
  fourth slot):
  - hall-thruster (this pack, quoted in the receipt): "This leaf implements
    the standard HET performance model (Goebel and Katz style
    decomposition)... converting discharge power into thrust through an axial
    electric field in a crossed-field discharge." Crossed-field electrostatic
    acceleration slot only; its body carries the beam-current and
    utilization-factor machinery, the anode vs total efficiency split and a
    xenon/krypton trade, no electromagnetic body-force term anywhere.
  - electrothermal-thruster (this pack) Pitfalls enumerate the pack's three
    mechanisms and none is electromagnetic (receipt quote): "hall and gridded
    thrusters accelerate charged beams through crossed fields or grids, while
    this leaf only heats propellant and uses no extraction electrodes - do not
    apply the perveance or beam-current machinery here." Body (fresh
    verified): "this leaf only heats propellant, so it neither accelerates
    charged beams nor uses extraction electrode assemblies".
  - gridded-ion-thruster (this pack) frontmatter (fresh verified): "extracting
    ions from a discharge plasma and accelerating them electrostatically
    through the net voltage between the screen and accelerator grids of a
    two-grid (or three-grid) ion optics assembly". Electrostatic grid
    extraction owned; its Child-Langmuir perveance, grid transparency and
    beam-current machinery must not appear here.
  Whole-tree greps at prep (receipt gate (a), re-verified at spec prep):
  magnetoplasmadynamic | mpd.thruster | self-field | applied-field -> 0 files
  under skills/, 0 owners (plain 'mpd' matches only the MMPDS substring in
  structures/data-sources, unrelated; corpus 'magnetoplasmadynamic' 0 tasks).
  GENUINE propulsion gap (receipt task-3 GO-1): no leaf produces the steady
  self-field MPD operating point from the discharge-current-squared thrust
  law; the wave-45 closed-veins list names the electromagnetic self-field
  slot the one open electric-propulsion mechanism.
- Standards id: ecss (grep-verified at spec prep: standards-map.yaml line 94
  "  - id: ecss"; ECSS series, free ESA downloads, reference-only, cited and
  paraphrased never reproduced; the same reference id all three electric-pack
  siblings use). Ledger Standard: ecss.
- Family: propulsion

## Claim

Compute the steady operating point of a self-field magnetoplasmadynamic
(MPD) electromagnetic thruster from the discharge current and the coaxial
geometry alone: the electromagnetic thrust T = (mu0/(4 pi)) * J^2 *
ln(r_a/r_c) of the steady self-field arc (the current-squared law of Jahn,
"Physics of Electric Propulsion", McGraw-Hill 1968, reported in the Sutton
Rocket Propulsion Elements electric-propulsion chapter; no applied magnetic
field, electrode falls and ionization neglected, the ideal electromagnetic
thrust), the effective exhaust velocity v_e = T/m_dot and specific impulse
Isp = v_e/g0 from the propellant mass flow, the jet kinetic power P_j =
T^2/(2 m_dot), and the thrust-to-power ratio on the jet-power basis, closed
by a documented reference-only class band verdict (Isp 1000-4000 s and
thrust-to-power 10-40 mN/kW, published ranges for the steady self-field MPD
class) that reports the point's position in the band and NEVER enforces it.
Produces the single-point summary dict with thrust, exhaust velocity,
specific impulse, jet power, thrust-to-power and the band verdict in one
call. Does NOT do: crossed-field electrostatic acceleration or the HET
efficiency decomposition with utilization factors (hall-thruster);
electrostatic grid extraction, Child-Langmuir perveance, grid transparency,
beam-current or ion-optics machinery (gridded-ion-thruster); heating-only
electrothermal operating points with propellant enthalpy tables and
resistojet or arcjet family language (electrothermal-thruster); applied-field
MPD corrections, discharge voltage, electrode falls or arc resistance (the
model has no voltage input at all); propellant chemistry (argon is carried as
a mass-flow label only, v_e = T/m_dot is mechanism-agnostic); the delta-v and
propellant-mass mission loop (rocket-sizing); nozzle expansion, chamber
states or pressure terms (rocket-nozzle-design). The class bands are reported
reference-only and never enforced, matching the electrothermal-thruster
band-verdict pattern: an out-of-band point is not an error and the verdict
function never raises on one.

## Model (implement exactly)

Pure stdlib, math only, deterministic, no RNG. Module constants:
MU0 = 4.0*pi*1e-7 (N/A^2, exact SI vacuum permeability, float value
1.2566370614359173e-06); MU0_OVER_4PI = MU0/(4.0*pi), the 1e-7 N/A^2 law
coefficient (float value 1.0000000000000001e-07, assert with isclose, never
with exact equality); G0 = 9.80665 (m/s^2); MN_PER_KW = 1e6 (N/W to mN/kW
scale); reference-only class bands ISP_BAND_S = (1000.0, 4000.0) (s) and
TP_BAND_MN_PER_KW = (10.0, 40.0) (mN/kW), reported never enforced.

Defining relations (pin these exactly; every function derives from them):
- Self-field electromagnetic thrust: T = (mu0/(4 pi)) * J^2 * ln(r_a/r_c),
  with J the total discharge current (A) and r_a/r_c the anode-to-cathode
  radius ratio of the coaxial electrode pair (r_a > r_c required). The
  discharge current drives its own azimuthal magnetic field; the JxB body
  force on the arc is the sole acceleration mechanism. Ideal electromagnetic
  thrust: electrode falls, ionization and thermal-pressure contributions are
  neglected (recorded idealization of the anchor).
- Effective exhaust velocity (definition, not a nozzle expansion): v_e =
  T/m_dot with m_dot the total propellant mass flow.
- Specific impulse: Isp = v_e/G0.
- Jet kinetic power: P_j = T^2/(2 m_dot). Exact identity P_j = 0.5*m_dot*
  v_e^2 follows from v_e = T/m_dot and must hold in the tests.
- Thrust-to-power (jet-power basis): T/P_j = 2*m_dot/T (N/W); report mN/kW
  by scaling with MN_PER_KW.
- Band verdict: reference-only; each metric's position is 'below', 'inside'
  or 'above' against ISP_BAND_S and TP_BAND_MN_PER_KW; the verdict dict
  carries enforced: False and NEVER raises for an out-of-band point.

Functions (with ValueError rejections as listed; no imports beyond math):
- self_field_thrust(current_j, radius_ratio) -> T (N). ValueError if inputs
  non-finite, current_j < 0, or radius_ratio <= 1 (a coaxial pair needs
  r_a > r_c; ln of 1 or less is not a physical geometry). current_j = 0 is
  allowed and returns 0.0 exactly.
- exhaust_velocity(thrust, mass_flow) -> v_e (m/s) = thrust/mass_flow.
  ValueError if inputs non-finite, thrust < 0, or mass_flow <= 0.
- specific_impulse(v_e) -> Isp (s) = v_e/G0. ValueError if non-finite or
  v_e < 0.
- jet_power(thrust, mass_flow) -> P_j (W) = thrust**2/(2*mass_flow).
  ValueError if inputs non-finite, thrust < 0, or mass_flow <= 0.
- thrust_to_power(thrust, p_j) -> N/W = thrust/p_j. ValueError if inputs
  non-finite, thrust < 0, or p_j <= 0.
- mpd_band_verdict(isp, thrust_to_power_mn_per_kw) -> dict with
  isp_band_s, isp_position, thrust_to_power_band_mn_per_kw,
  thrust_to_power_position (each position in {'below', 'inside', 'above'})
  and enforced: False. ValueError only for negative or non-finite inputs;
  NEVER for an out-of-band position.
- mpd_operating_point(current_j, radius_ratio, mass_flow) -> dict with
  current_j, radius_ratio, mass_flow, thrust, exhaust_velocity,
  specific_impulse, jet_power, thrust_to_power_n_per_w,
  thrust_to_power_mn_per_kw, band_verdict (nested dict). ValueErrors
  propagate from the chained functions.

Identities to test (closed form, from the real anchor outputs):
- Current-squared scaling: T at 20 kA is exactly 4 * T at 10 kA, and T at
  5 kA is exactly T(10 kA)/4 = 5.756462732485115 N (the J^2 law; real
  anchor).
- Log-geometry scaling: T at r_a/r_c = 100 is exactly 2 * T at ratio 10 and
  T at ratio 1000 is exactly 3 * T at ratio 10 (ln doubling and tripling;
  real anchor).
- Coefficient identity: T/J^2 = 2.302585093e-7 N/A^2 = 1e-7 * ln(10) (real
  anchor 23.02585092994046 N over 1e8 A^2).
- Definition identities: v_e = T/m_dot; Isp = v_e/G0; P_j from T^2/(2 m_dot)
  equals 0.5*m_dot*v_e^2; T/P_j = 2*m_dot/T (all isclose at 1e-12, real
  anchor).
- Boundary: self_field_thrust(0, 10) = 0.0 exactly and the zero-current
  thrust is 0 at any ratio (no current, no self-field, no thrust).
- Band verdict semantics: mpd_band_verdict(23479.833510873195, 8.685889638)
  returns isp_position 'above' and thrust_to_power_position 'below' with
  enforced False (the anchor point itself); mpd_band_verdict(2000.0, 20.0)
  returns 'inside' for both; out-of-band points never raise.
- ValueErrors across the module: self_field_thrust at current -100 A, at
  radius_ratio 1.0 and at nan; exhaust_velocity at mass_flow 0 and at
  thrust -1; specific_impulse at v_e -1; jet_power at mass_flow -1e-4;
  thrust_to_power at p_j 0; mpd_band_verdict at isp -1; mpd_operating_point
  at current -1 and at mass_flow 0.
- Determinism: no imports beyond math; constants fixed; repeated runs
  byte-identical under BOTH interpreters (verified at spec prep).

## Worked example

Steady self-field MPD point at the receipt's published anchor: J = 10 kA
(10000 A), r_a/r_c = 10, m_dot = 0.1 g/s = 1.0e-4 kg/s argon. All values
below are REAL outputs of the prep anchor /tmp/w45spec/anchor_mpd_thruster.py
(stdlib math, closed form; ALL CHECKS PASS on the run).
- Thrust: T = 1e-7 * (1e4)^2 * ln(10) = 10 * ln(10) = 23.02585092994046 N,
  reproducing the receipt's 23.0 N target within 1 percent (0.11 percent
  high). The coefficient identity holds: T/J^2 = 2.302585093e-7 N/A^2.
- Exhaust velocity: v_e = T/m_dot = 230258.5092994046 m/s.
- Specific impulse: Isp = v_e/G0 = 23479.833510873195 s.
- Jet power: P_j = T^2/(2 m_dot) = 2650949.0552391997 W (about 2.651 MW);
  the identity P_j = 0.5*m_dot*v_e^2 holds exactly.
- Thrust-to-power (jet-power basis): T/P_j = 8.685889638065036e-06 N/W =
  8.685889638065037 mN/kW; the identity T/P_j = 2*m_dot/T holds exactly.
- Band verdict: isp_position 'above' the reported 1000-4000 s class band,
  thrust_to_power_position 'below' the reported 10-40 mN/kW band, enforced
  False. The anchor fixes m_dot at 0.1 g/s, so the ideal current-squared law
  implies an exhaust velocity far above the class-typical range; the verdict
  reports this position and never enforces it (reference-only, matching the
  electrothermal-thruster band-verdict pattern).
- Query-2 companion point at J = 5 kA (same ratio and mass flow): T =
  5.756462732485115 N, exactly one quarter of the 10 kA thrust by the J^2
  law; v_e = 57564.62732485115 m/s; Isp = 5869.958377718299 s; P_j =
  165684.31595244998 W; T/P_j = 3.4743558552260144e-05 N/W =
  34.74355855226015 mN/kW (INSIDE the reported 10-40 mN/kW band); verdict
  isp_position 'above', thrust_to_power_position 'inside', enforced False.
  At fixed mass flow, doubling J quadruples the thrust but quarters the
  jet-power-basis thrust-to-power (34.74355855226015 / 4 =
  8.685889638065037), the discharge-current-scaling signature of the law.

## Validation list (deterministic checks the contract test must run)

1. Module import + constants match the spec values: MU0
   1.2566370614359173e-06 and MU0_OVER_4PI within 1e-6 relative of 1e-7
   (isclose, never exact float equality: the computed constant is
   1.0000000000000001e-07), G0 9.80665, MN_PER_KW 1e6, band tuples as
   pinned.
2. Worked-example values within 1e-6 relative of the anchor outputs: thrust
   23.02585092994046 N, exhaust velocity 230258.5092994046 m/s, specific
   impulse 23479.833510873195 s, jet power 2650949.0552391997 W,
   thrust-to-power 8.685889638065037 mN/kW.
3. Receipt target: thrust at the worked point equals 23.0 N within 1 percent.
4. Scaling identities: T(20 kA) == 4*T(10 kA), T(5 kA) == T(10 kA)/4 ==
   5.756462732485115 N; T(ratio 100) == 2*T(ratio 10), T(ratio 1000) ==
   3*T(ratio 10); T/J^2 == 1e-7*ln(10) (2.302585093e-7 N/A^2).
5. Definition and jet-power identities: v_e == T/m_dot; Isp == v_e/G0;
   P_j == 0.5*m_dot*v_e^2 == T^2/(2 m_dot); T/P_j == 2*m_dot/T.
6. Boundary: self_field_thrust(0, 10) == 0.0 exactly; zero-current thrust is
   0 at any valid ratio.
7. Band verdict: at the anchor point isp_position 'above' and
   thrust_to_power_position 'below' with enforced False; at (2000 s,
   20 mN/kW) both positions 'inside'; out-of-band inputs never raise.
8. All ValueErrors listed under Identities fire.
9. Determinism: two identical runs return byte-identical outputs (verified
   at spec prep under both interpreters).
10. Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3). No exact-float equality on
    computed sums; use assertAlmostEqual/math.isclose everywhere.

## Corpus fragment (2 verbatim queries for eval/hit1-wave45-mpd-thruster.yaml)

1. "size an mpd-thruster for the 10 kA discharge current with the 10 to 1
   anode-to-cathode radius ratio: compute the self-field electromagnetic
   thrust from the current-squared thrust law and the exhaust velocity from
   the 0.1 g/s argon mass flow" (routes on mpd-thruster, self-field
   electromagnetic thrust, current-squared thrust law, anode-to-cathode
   radius ratio tokens)
2. "analyze the magnetoplasmadynamic-thruster self-field arc operating
   points: thrust from the discharge-current-squared thrust law at 5 kA and
   10 kA, jet power and specific impulse from the argon mass flow, and the
   thrust-to-power band verdict for the steady-state mpd-thruster class"
   (routes on magnetoplasmadynamic-thruster, self-field arc,
   discharge-current-squared, mpd-thruster tokens)
intent lines: "propulsion; steady self-field MPD operating point from the
discharge-current-squared electromagnetic thrust law at the anode-to-cathode
radius ratio" and "propulsion; self-field MPD thrust, jet power, specific
impulse and thrust-to-power across the 5 kA and 10 kA discharge-current
operating points with the reference-only band verdict".

## Description/tag guidance for the builder

- Description: "Use when you must compute the steady operating point of a
  magnetoplasmadynamic (self-field electromagnetic) thruster for electric
  propulsion: the electromagnetic thrust from the discharge current squared
  through the self-field thrust law T = (mu0/(4 pi)) J^2 ln(r_a/r_c) at the
  anode-to-cathode radius ratio, the exhaust velocity and specific impulse
  from the propellant mass flow, the jet kinetic power, and the
  reference-only thrust-to-power band verdict for the steady-state self-field
  MPD class. Produces the single-point MPD summary with thrust, exhaust
  velocity, specific impulse, jet power, thrust-to-power and the class
  operating-band verdict in one call, with the published bands reported and
  never enforced. Trigger: mpd thruster, magnetoplasmadynamic thruster,
  self-field electromagnetic arc, discharge current squared thrust law,
  anode to cathode radius ratio, MPD jet power, thrust-to-power band
  verdict." (<=1000 chars, <=148 words; draft at about 900 chars.)
- metadata tags (EXACTLY as the receipt gate (f) lists them):
  [mpd-thruster, magnetoplasmadynamic-thruster, self-field-thrust-law,
  electromagnetic-acceleration, discharge-current-scaling]
- FORBIDDEN tokens (sibling claims): crossed-field electrostatic
  acceleration, axial electric field in a crossed-field discharge,
  efficiency utilization factors, beam current, perveance, Child-Langmuir,
  grid transparency, ion optics, accelerator grid, extraction electrodes,
  resistojet, arcjet, heated propellant enthalpy, rocket-equation
  propellant-mass mission loop, chemical nozzle expansion. No generic
  single-word tags (no bare thruster, current, power, impulse).
- ZERO em dashes in every file; never the word that the spec-engineer
  kit's reserved-word ban names (it is a gate-scanned token, do not print
  it anywhere).
- Standards reference-only: ecss (ECSS series) named + paraphrased, never
  reproduced verbatim.
