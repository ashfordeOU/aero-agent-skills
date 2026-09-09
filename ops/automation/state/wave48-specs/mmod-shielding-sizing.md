# Wave-48 leaf spec: mmod-shielding-sizing (space-systems, subsystems pack)

- Path: skills/space-systems/subsystems/mmod-shielding-sizing/
- Pack: space-systems/subsystems (9 leaves present at this HEAD:
  antenna-aperture-sizing, command-data-handling,
  communication-link-budget, doppler-shift, power-thermal-budget,
  propellant-tank-sizing, solar-array-sizing, spacecraft-battery-sizing,
  thermal-design; adjacent fence on the environment side:
  space-systems/mission-design/radiation-debris). Wave-48 probe receipt
  task-9 rank-1 GO (strong); 0 owners verified whole-tree at prep and
  re-verified at spec time.
- Claim fences (quoted from the sibling frontmatter and body at this
  HEAD; the environment sibling, radiation-debris, stops its debris
  tier at flux and collision probability, and its shielding is
  exclusively radiation, so the impact consequence math this leaf
  produces appears nowhere in the family):
  - radiation-debris frontmatter description (line 3): "...estimate the
    debris collision probability from the flux, cross-section, and
    mission life..." and "...size aluminum shielding against total
    ionizing dose with exponential attenuation, and estimate the debris
    collision probability from the flux, cross-section, and mission
    life." The debris tier is the probability of ANY impact; the
    shielding tier is radiation dose attenuation, never an impact
    outcome.
  - radiation-debris domain quick reference, body lines 76-79: "Debris
    flux: a Gaussian density band peaking near 850 km where the
    catalogued debris population is densest, scaled by a size power law
    (s / 1 cm)^(-2.6). At the peak the flux of particles above 1 cm is
    5e-5 per m^2 per year; at 550 km it drops by about 63 percent."
    The environment side owns the flux and the size power law.
  - radiation-debris domain quick reference, body lines 80-83:
    "Collision probability: Poisson statistics, P = 1 - exp(-flux *
    area * mission_years). For small expected collisions the
    probability is approximately the product; it grows with mission
    life and cross-section, and is exactly 0 for zero area or zero
    flux." The collision probability is impact-rate math, not the
    consequence of an impact.
  - radiation-debris domain quick reference, body lines 71-75:
    "Shielding sizing: shielding_for_dose_limit returns the minimum
    aluminum thickness meeting a dose limit, or None when even the
    maximum thickness cannot (the proton component floor sits above the
    limit). At the proton belt peak (60.8 rad/day, 1 year) a 10 krad
    limit needs about 4.5 mm of aluminum." Its shielding language is
    total-ionizing-dose attenuation; nothing about bumper, standoff,
    cratering, spall, or critical diameter.
  - radiation-debris workflow step 5, body lines 109-112: "Get the
    debris flux with debris_flux_per_m2_yr at the mission altitude,
    then the collision probability with collision_probability from the
    spacecraft cross-section and mission life; grade it with
    debris_verdict." The workflow handoff this leaf closes: the
    environment leaf produces flux and collision probability, which
    become GIVEN inputs here; the impact-to-penetration conversion is
    absent downstream.
  - radiation-debris metadata tags (frontmatter line 16):
    radiation-environment, trapped-belts, total-ionizing-dose,
    single-event-effects, seu-rate, solar-particle-events,
    orbital-debris, shielding-attenuation, collision-probability,
    mission-design. No impact, penetration, ballistic-limit, or
    whipple token anywhere in the radiation-debris body or pitfalls.
  - Whole-tree greps at spec time (probe receipt gate (a), fresh at
    this HEAD): micrometeoroid, hypervelocity, whipple, ballistic-limit
    and debris-penetration return ZERO files across every skills/
    SKILL.md (all 657) and ZERO of 1306 eval/hit1-corpus.yaml task
    blocks; the single mmod substring hit in the whole tree is
    "accommODate" inside
    vehicle-design/sizing/bleed-air-system-sizing (false positive,
    re-verified); projectile hits are confined to
    gnc-autonomy/guidance/impact-point-prediction (unguided artillery
    projectile, flat-earth range equation, unrelated regime);
    structures contact content (hertzian-contact-stress,
    contact-analysis) is mechanical contact mechanics, not
    hypervelocity impact. GENUINE space-systems gap (probe receipt
    task-9, verified zero-owner, GO rank 1 strong).
- Standards id: ecss (ECSS-E-ST-10C systems engineering general
  requirements; the family spine carried reference-only by all 52
  existing space-systems leaves; grep 'id: ecss' at standards-map.yaml
  line 94, re-verified at spec time; the published anchor, Christiansen
  et al. NASA TM-2009-214789 (JSC-64399) and the Cour-Palais cratering
  equation family it consolidates, is cited summary-only per the
  STANDARDS-REF convention). Ledger Standard: ecss.
- Family: space-systems

## Claim

Size the hypervelocity meteoroid and orbital debris (MMOD) impact
protection of a spacecraft wall with the NASA/JSC ballistic-limit
equation family: the single-wall ballistic limit through the
Cour-Palais cratering equation (the semi-infinite penetration depth
P_inf of a monolithic aluminum plate and the critical projectile
diameter dc at the perforation, detached-spall, and incipient-spall
damage thresholds k = 1.8, 2.2, 3.0), and the Whipple shield through
the Christiansen new-non-optimum ballistic limit equations (the
critical projectile diameter of a thin aluminum bumper, rear wall,
and standoff configuration across the low, intermediate, and
hypervelocity impact regimes with the 3 km/s and 7 km/s
normal-velocity transitions and the 65 degree obliquity cap, plus the
bumper and rear-wall design thicknesses of a thin aluminum Whipple
shield). The impact is converted into a no-penetration condition:
whipple_rear_wall_thickness returns the rear-wall thickness that
stops a design projectile at its design normal impact velocity (the
eq (4-22) design form, Vn >= 7 km/s, with the eq (4-21) bumper
thickness), and whipple_critical_diameter returns the ballistic limit
of a given shield so the per-impact verdict is deterministic: d >= dc
is PENETRATION, d < dc is NO_PENETRATION, with the margin d/dc. The
impact outcome is rolled over the mission:
penetration_probability(expected_penetrating_impacts) returns
P = 1 - exp(-lambda), the probability of at least one penetrating
impact over the mission from the expected number of penetrating
impacts; the debris fluence, flux, and collision-probability outputs
of the space environment assessment (radiation-debris) are GIVEN
inputs, and no environment quantity is estimated here. All equations
are the published closed forms of Christiansen et al., NASA
TM-2009-214789 (JSC-64399), equations (4-1) to (4-26), reproduced
summary-only with the handbook's units (cm, g/cm^3, km/s, ksi,
degrees) and material constants only. Does NOT do: the debris
environment: flux models, the ORDEM/MASTER-style size power law
(s / 1 cm)^(-2.6), collision probability P = 1 - exp(-flux * area *
mission_years), fluence, and every radiation quantity (trapped belt
and SPE dose, single-event upsets, total-ionizing-dose aluminum
attenuation, the ADEQUATE/MARGINAL/EXCEEDED and LOW/MODERATE/HIGH
verdict bands) (space-systems/mission-design/radiation-debris owns
the whole environment and risk-probability side; this leaf consumes
its outputs and never estimates a flux, a fluence, or the probability
of any impact); debris avoidance, collision avoidance, and station
keeping delta-v (orbital-decay and mission-delta-v-budget own the
maneuver side); mechanical contact mechanics, Hertzian stress, static
indentation, fatigue crack growth, and structural joints (structures
family); impact-point prediction and the flat-earth range equation of
unguided projectiles (gnc-autonomy/guidance/impact-point-prediction);
hypervelocity impact TEST or hydrocode analysis, shock physics,
equations of state, and spallation physics beyond the empirical
damage-threshold factors (the model is the empirical BLE family
only); stuffed Whipple, multi-shock, mesh double-bumper, honeycomb,
titanium, steel, CFRP and fiberglass single-wall variants, and the
MLI blanket modification of the handbook sections 4.1.2 to 4.1.6 and
4.3 and later (aluminum single wall and aluminum Whipple only);
Bumper-code-style Monte Carlo risk assessment over a shield geometry
(single design case and the Poisson rollup only); material property
tables and allowables (properties are inputs, never looked up or
reproduced, and no test data fitting happens anywhere). Impact angle,
velocity, projectile diameter, densities, hardness, yield stress, and
sound speed are inputs, never estimated; the equations are
deterministic closed-form arithmetic in the handbook units.
Radiation-debris-style proxies are never reproduced.

## Model (implement exactly)

Pure stdlib (math only), closed form, deterministic, no RNG, no
tables beyond the fixed published coefficients below. All thicknesses
in cm, densities in g/cm^3, velocities in km/s, yield stress in ksi,
angles in degrees, masses in g, matching NASA TM-2009-214789
(JSC-64399) exactly.

Module constants (pin these exactly):
- C_CP = 5.24 (Cour-Palais cratering coefficient, eqs 4-1 and 4-2).
- K_PERFORATION = 1.8, K_DETACHED_SPALL = 2.2, K_INCIPIENT_SPALL =
  3.0 (damage thresholds t >= k P_inf, eqs 4-3 to 4-5; the default
  damage mode is perforation).
- RHO_BRANCH = 1.5 (density-ratio branch switch, eq 4-1 vs eq 4-2).
- C_HYPER = 3.918 (Whipple hypervelocity coefficient, eq 4-23).
- C_WALL_DESIGN = 0.16 (rear-wall design coefficient, cm^2 s /
  (g^(2/3) km), eq 4-22).
- CB_NEAR = 0.25 and CB_FAR = 0.20 (bumper coefficients for S/d < 30
  and S/d >= 30, eq 4-21; SD_BRANCH = 30.0).
- V_LOW = 3.0 and V_HIGH = 7.0 (low-to-intermediate and
  intermediate-to-hypervelocity transitions in the normal velocity
  Vn = V cos(theta), km/s, aluminum on aluminum).
- THETA_CAP_DEG = 65.0 (obliquity cap, eq 4-26).

Defining relations (pin these exactly; every function derives from
them; theta is the impact angle from the target normal, capped at
65 degrees before use so Vn = V cos(theta_eff)):
- Single wall, density ratio r = rho_p / rho_t. For r < 1.5
  (eq 4-1): P_inf = 5.24 d^(19/18) BHN^(-1/4) r^(1/2)
  (V cos(theta) / C_t)^(2/3). For r >= 1.5 (eq 4-2): P_inf =
  5.24 d^(19/18) BHN^(-1/4) r^(2/3) (V cos(theta) / C_t)^(2/3).
  C_t is the speed of sound in the target, BHN the Brinell hardness.
- Single-wall damage thresholds: t >= k P_inf with k = 1.8
  (perforation), 2.2 (detached spall), 3.0 (incipient spall).
- Single-wall critical diameter (eq 4-6, the k-threshold inversion):
  dc = [ t BHN^(1/4) (rho_t / rho_p)^(1/2) / (k 5.24
  (V cos(theta) / C_t)^(2/3)) ]^(18/19) for r < 1.5; for r >= 1.5 the
  density ratio becomes (rho_t / rho_p)^(2/3), the documented
  algebraic inverse of eq 4-2 (the handbook prints eq 4-6 for the
  r < 1.5 branch; aluminum-on-aluminum sits at r = 1.0).
- Whipple bumper design (eq 4-21): tb = cb d rho_p / rho_b with
  cb = 0.25 when S/d < 30 and cb = 0.20 when S/d >= 30.
- Whipple rear-wall design (eq 4-22, valid for Vn >= 7 km/s, the
  no-penetration condition at the design projectile):
  tw = 0.16 d^(1/2) (rho_p rho_b)^(1/6) Mp^(1/3) Vn (70 / sigma)^(1/2)
  / S^(1/2), where Mp is the projectile mass in g, defaulting to the
  sphere mass (pi/6) rho_p d^3, and sigma is the rear-wall yield
  stress in ksi. Vn below 7 km/s raises ValueError (the design
  equations assume hypervelocity).
- Whipple critical diameter, three regimes of the Christiansen BLE
  (theta capped at 65 deg, eq 4-26, before the regime test):
  - Vn <= 3 km/s (eq 4-24):
    dc = [ (tw (sigma / 40)^(1/2) + tb) / (0.6 rho_p^(1/2) V^(2/3)
    (cos theta)^(5/3)) ]^(18/19). The denominator equals
    0.6 rho_p^(1/2) Vn^(2/3) cos theta algebraically (Vn = V cos
    theta); the printed V^(2/3) cos^(5/3) form is pinned.
  - 3 km/s < Vn < 7 km/s (eq 4-25): exact linear interpolation
    between the low-velocity equation at Vn = 3 km/s and the
    hypervelocity equation at Vn = 7 km/s:
    dc = dc_L3 (7 - Vn) / 4 + dc_H7 (Vn - 3) / 4, with
    dc_L3 = [ (tw (sigma / 40)^(1/2) + tb) / (0.6 rho_p^(1/2) 3^(2/3)
    cos theta) ]^(18/19) (the printed eq 4-25 denominator constant
    1.248 is the rounded 0.6 * 3^(2/3) = 1.2480502938...) and
    dc_H7 = 3.918 tw^(2/3) rho_p^(-1/3) rho_b^(-1/9) S^(1/3)
    (sigma / 70)^(1/3) 7^(-2/3) (the printed eq 4-25 constant 1.071
    is the rounded 3.918 * 7^(-2/3) = 1.0706949106...). The exact
    anchors make dc exactly continuous at both regime transitions;
    the printed rounded constants differ by at most 3e-4 relative.
  - Vn >= 7 km/s (eq 4-23):
    dc = 3.918 tw^(2/3) rho_p^(-1/3) rho_b^(-1/9) Vn^(-2/3) S^(1/3)
    (sigma / 70)^(1/3). The bumper thickness does not enter the
    hypervelocity regime: the performance equations assume the bumper
    is adequate to disrupt the projectile (documented handbook
    assumption, eq 4-20 adequacy; the module documents it and never
    over-claims for an inadequate bumper).
  - The eq (4-25) blend at Vn = 7 and the eq (4-23) evaluation at
    Vn = 7 are the same value, and the eq (4-24) evaluation at Vn = 3
    and the blend anchor dc_L3 are the same value: the regime curve is
    continuous.
- Verdict: margin = d / dc; margin >= 1 (d >= dc) is PENETRATION,
  margin < 1 is NO_PENETRATION.
- Mission rollup: penetration_probability(lambda) = 1 - exp(-lambda)
  with lambda the expected number of penetrating impacts over the
  mission (a GIVEN input assembled from the environment leaf's flux
  at and above dc, the critical area, and the mission life; none of
  that environment math is performed here).

Functions (every public function validates its inputs identically;
ValueError, never assert; booleans are rejected as non-real):
- cour_palais_penetration_depth(d, rho_p, rho_t, bhn, v, theta_deg,
  c_t) -> float: P_inf in cm, eqs (4-1)/(4-2) with the rho branch.
  ValueErrors: any non-positive input ("... must be a positive number,
  got ..."), theta outside [0, 90) ("impact angle must be in [0, 90)
  degrees, got ..."), any boolean argument.
- single_wall_critical_diameter(t, rho_p, rho_t, bhn, v, theta_deg,
  c_t, k=K_PERFORATION) -> float: dc in cm at the k damage threshold.
  Same ValueErrors plus a non-positive k.
- single_wall_required_thickness(d, rho_p, rho_t, bhn, v, theta_deg,
  c_t, k=K_PERFORATION) -> float: t = k P_inf in cm.
- sphere_mass_g(d, rho_p) -> float: (pi/6) rho_p d^3 in g.
- whipple_bumper_thickness(d, rho_p, rho_b, S) -> float: tb in cm,
  eq (4-21), cb by the S/d branch.
- whipple_rear_wall_thickness(d, rho_p, rho_b, S, sigma_ksi, v,
  theta_deg, mass_g=None) -> float: tw in cm, eq (4-22); mass_g
  defaults to sphere_mass_g. ValueError "rear-wall design thickness
  requires a normal impact velocity of at least 7 km/s, got Vn ..."
  when Vn < 7 km/s.
- whipple_critical_diameter(tb, tw, sigma_ksi, rho_p, rho_b, S, v,
  theta_deg) -> float: dc in cm, three-regime dispatch on Vn with the
  65 degree cap; internal helpers _dc_low (eq 4-24), _dc_l3 and
  _dc_h7 (blend anchors), _dc_hyper (eq 4-23).
- penetration_verdict(projectile_diameter_cm, critical_diameter_cm)
  -> (str, float): ("PENETRATION", d / dc) when d >= dc, else
  ("NO_PENETRATION", d / dc).
- whipple_penetration_verdict(d, tb, tw, sigma_ksi, rho_p, rho_b, S,
  v, theta_deg) -> dict: {"verdict", "dc", "margin"} for a Whipple
  shield.
- penetration_probability(expected_penetrating_impacts) -> float:
  1 - exp(-lambda). ValueError "... expected penetrating impacts must
  be non-negative, got ..." for negative lambda.

Identities to test (closed form, checkable without the builder
module):
- Single-wall round trip: single_wall_critical_diameter of
  single_wall_required_thickness(d, ...) equals d exactly within 1e-9
  relative (the 18/19 and 19/18 powers invert), on BOTH density
  branches (r = 1.0 aluminum-on-aluminum and r = 7.85 / 2.7 >= 1.5
  steel-on-aluminum).
- t_req = k P_inf: single_wall_required_thickness(d, ...) equals
  k times cour_palais_penetration_depth(d, ...) exactly.
- Whipple design self-consistency: dc(tw_design(d)) at Vn = 7 equals
  d times the closed-form factor 3.918 * 0.16^(2/3) * (pi/6)^(2/9) =
  1.000075994715671 within 1e-9 relative (the eq 4-22 design is the
  exact inverse of the eq 4-23 hypervelocity performance equation at
  Vn = 7 km/s for a spherical projectile), and that factor lies
  within 2e-4 of 1 (the rounding of the published 3.918).
- Regime continuity: dc is exactly continuous at Vn = 3 km/s and at
  Vn = 7 km/s (dispatch boundary equals blend anchor within 1e-12).
- Hypervelocity scaling: dc(V2) / dc(V1) = (V1 / V2)^(2/3) within
  1e-12 for V1, V2 both with Vn >= 7 at fixed theta; the hypervelocity
  regime depends on Vn only, so dc at (V = 7 / cos(45 deg), theta =
  45 deg) equals dc at (V = 7 km/s, theta = 0 deg) exactly.
- Obliquity cap: dc(theta >= 65 deg) equals dc(theta = 65 deg)
  exactly (same inputs, eq 4-26).
- Verdict semantics: margin < 1 is NO_PENETRATION, margin >= 1 is
  PENETRATION; the design case at 7 km/s returns NO_PENETRATION with
  margin 0.999924011059087 and the same shield at 10 km/s returns
  PENETRATION with margin 1.2683379012255367.
- penetration_probability(0) = 0 exactly and the value grows
  monotonically to 1 with lambda.
- Determinism: identical outputs run to run, identical under both
  interpreters; no randomness; no imports beyond math.

## Worked example

A thin-aluminum Whipple shield for the receipt query-1 design case:
stop a 1.0 cm spherical aluminum projectile (rho_p = 2.70 g/cm^3) at
7 km/s normal impact (theta = 0 deg). Rear wall Al 6061-T6 class with
yield stress sigma = 40.0 ksi, aluminum bumper (rho_b = 2.70 g/cm^3)
at standoff S = 11.43 cm (S/d = 11.43 < 30). Second case: the same
shield at the query-2 micrometeoroid-class velocity of 10 km/s.
Single-wall case: a 0.48 cm monolithic Al 6061-T6 wall (BHN = 95,
rho_t = 2.70 g/cm^3, C_t = 5.0 km/s sound speed) against a 10 km/s
aluminum projectile.

All values below are REAL outputs of the prep anchor
/tmp/w48spec/anchor_mmod_shielding.py (pure stdlib, math only,
closed form, exit 0, no RNG), run once and quoted as printed, then
re-verified byte-identical under /usr/bin/python3 3.9.6 and the
3.13.12 interpreter (~/.pyenv/versions/3.13.12/bin/python3):

- Whipple design at 7 km/s (receipt query 1):
  whipple_bumper_thickness(1.0, 2.7, 2.7, 11.43) = 0.25 cm (cb =
  0.25 because S/d = 11.43 < 30; tb = 0.25 * 1.0 * 2.7 / 2.7).
  sphere_mass_g(1.0, 2.7) = 1.413716694115407 g = (pi/6) * 2.7.
  whipple_rear_wall_thickness(1.0, 2.7, 2.7, 11.43, 40.0, 7.0, 0.0)
  = 0.684892875727985 cm: the rear wall that stops the 1 cm
  projectile at its 7 km/s design impact.
  whipple_critical_diameter of the sized shield at Vn = 7 km/s =
  1.000075994715671 cm. The design self-consistency holds:
  dc / d = 1.000075994715671 equals the closed form 3.918 *
  0.16^(2/3) * (pi/6)^(2/9) = 1.000075994715671 (the eq 4-22 sizing
  is the exact inverse of the eq 4-23 performance equation at
  Vn = 7 km/s), so the 1 cm design projectile sits 0.00007599 cm
  under the ballistic limit: verdict NO_PENETRATION with margin
  d / dc = 0.999924011059087.
- Same shield at 10 km/s (receipt query 2, Whipple part): dc =
  0.7884334285317389 cm; the hypervelocity scaling identity
  dc(10) / dc(7) = 0.7883735163105243 versus (7/10)^(2/3) =
  0.7883735163105242. The 1 cm projectile now exceeds the ballistic
  limit: verdict PENETRATION with margin d / dc =
  1.2683379012255367. A shield sized at 7 km/s does not stop the
  same projectile at 10 km/s.
- Single aluminum wall at 10 km/s (receipt query 2, single-wall
  part): cour_palais_penetration_depth(1.0, 2.7, 2.7, 95, 10, 0,
  5.0) = 2.664324077003382 cm (semi-infinite crater depth of a 1 cm
  projectile); single_wall_required_thickness(1.0, ...) =
  4.795783338606088 cm = 1.8 * P_inf exactly (perforation threshold);
  single_wall_critical_diameter(0.48, 2.7, 2.7, 95, 10, 0, 5.0) =
  0.11297781552560618 cm, so the 0.48 cm wall stops only
  sub-millimeter-class projectiles at 10 km/s (the round trip
  dc(t_req(1.0 cm)) = 1.0000000000000002 cm closes the inversion).
- Regime curve of the Case-1 shield (module output): dc at V = 2
  km/s, theta = 0 (low regime, Vn = 2) = 0.6137885577448827 cm; dc
  at V = 6.5 km/s (intermediate regime, Vn = 6.5) =
  0.9344564876830601 cm; dc at V = 7 / cos(45 deg) km/s, theta = 45
  deg (Vn = 7 boundary, hypervelocity regime depends on Vn only) =
  1.000075994715671 cm, identical to the normal-impact value at
  7 km/s; dc at theta = 70 deg equals dc at theta = 65 deg exactly
  (obliquity cap, eq 4-26): 1.0594730484880124 == 1.0594730484880124
  at V = 9 km/s.
- Mission rollup: penetration_probability(0.5) = 0.3934693402873666
  = 1 - exp(-0.5).
- Real ValueError messages (module output, quoted as raised): a
  rear-wall design at Vn = 6 km/s raises "rear-wall design thickness
  requires a normal impact velocity of at least 7 km/s, got Vn 6.0
  km/s"; theta = 90 raises "impact angle must be in [0, 90) degrees,
  got 90.0"; d = -1.0 raises "projectile diameter must be a positive
  number, got -1.0"; BHN = 0.0 raises "target hardness BHN must be a
  positive number, got 0.0"; lambda = -0.1 raises "expected
  penetrating impacts must be non-negative, got -0.1"; a boolean
  bumper thickness raises "bumper thickness must be a real number,
  got True".
- The anchor's internal asserts (regime continuity at Vn = 3 and
  Vn = 7 within 1e-12, design self-consistency within 2e-4 of 1,
  single-wall round trips on both density branches within 1e-9,
  hypervelocity scaling within 1e-12, obliquity cap exactness, the
  t_req = 1.8 P_inf identity, every ValueError, determinism) all
  pass and the anchor exits 0; stdout is byte-identical under both
  interpreters.
- Magnitude gates from the probe receipt: the query-1 design case
  yields a physically sane Whipple wall (bumper 0.25 cm, rear wall
  0.684892875727985 cm at 11.43 cm standoff, sigma 40 ksi) whose
  critical diameter at the 7 km/s design point is 1.000075994715671
  cm, a cm-scale projectile stopped at cm-scale wall thickness; the
  query-2 single-wall case yields a 0.11297781552560618 cm critical
  diameter for a 0.48 cm monolithic wall at 10 km/s, the expected
  order for unprotected single walls against hypervelocity impacts;
  dc falls with velocity in the low regime (more damaging intact
  projectile), peaks through the intermediate regime, and falls as
  Vn^(-2/3) in the hypervelocity regime.

Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of /tmp/w48spec/
anchor_mmod_shielding.py (stdlib math, closed form, exit 0, no
randomness, byte-identical under both interpreters).

## Validation list (contract test must include)

1. Worked-example asserts within 1e-6 relative:
   whipple_bumper_thickness(1.0, 2.7, 2.7, 11.43) = 0.25;
   whipple_rear_wall_thickness(1.0, 2.7, 2.7, 11.43, 40.0, 7.0, 0.0)
   = 0.684892875727985; whipple_critical_diameter(0.25,
   0.684892875727985, 40.0, 2.7, 2.7, 11.43, 7.0, 0.0) =
   1.000075994715671; sphere_mass_g(1.0, 2.7) = 1.413716694115407;
   cour_palais_penetration_depth(1.0, 2.7, 2.7, 95, 10, 0, 5.0) =
   2.664324077003382; single_wall_required_thickness(1.0, 2.7, 2.7,
   95, 10, 0, 5.0) = 4.795783338606088;
   single_wall_critical_diameter(0.48, 2.7, 2.7, 95, 10, 0, 5.0) =
   0.11297781552560618; penetration_probability(0.5) =
   0.3934693402873666.
2. Design self-consistency: whipple_critical_diameter of the sized
   Case-1 shield at Vn = 7 divided by 1.0 equals
   3.918 * 0.16^(2/3) * (pi/6)^(2/9) = 1.000075994715671 within 1e-9
   relative, and lies within 2e-4 of 1.0.
3. Single-wall round trip within 1e-9 relative on both density
   branches: single_wall_critical_diameter(
   single_wall_required_thickness(d, ...), ...) = d for
   (rho_p, rho_t) = (2.7, 2.7) and (7.85, 2.7), d = 0.3, at
   V = 10 km/s; and single_wall_required_thickness equals
   K_PERFORATION * cour_palais_penetration_depth exactly.
4. Regime continuity within 1e-9 relative: dc evaluated at
   V = 3 / cos(theta) (low regime at the Vn = 3 boundary) equals the
   intermediate blend anchor dc_L3, and dc evaluated at Vn = 7 equals
   the hypervelocity anchor dc_H7; both boundaries are continuous.
5. Hypervelocity scaling within 1e-12: dc(10 km/s) / dc(7 km/s) =
   (7/10)^(2/3) = 0.7883735163105242 for the Case-1 shield at
   theta = 0; dc at (V = 7 / cos(45 deg), theta = 45 deg) equals dc
   at (V = 7 km/s, theta = 0 deg) within 1e-12 (the hypervelocity
   regime depends on Vn only).
6. Obliquity cap: whipple_critical_diameter at theta = 70 deg equals
   the value at theta = 65 deg (1.0594730484880124 at V = 9 km/s for
   the Case-1 shield) using assertAlmostEqual; no exact-float
   equality.
7. Verdict semantics: penetration_verdict(1.0, 1.000075994715671)
   = ("NO_PENETRATION", 0.999924011059087) and
   penetration_verdict(1.0, 0.7884334285317389) = ("PENETRATION",
   1.2683379012255367); whipple_penetration_verdict returns the
   dict {"verdict", "dc", "margin"} with margin = d / dc; margin >= 1
   maps to PENETRATION, margin < 1 to NO_PENETRATION.
8. penetration_probability(0.0) = 0.0 exactly (no exp call needed
   beyond the formula) and the function increases monotonically over
   lambda in {0, 0.5, 2, 5}.
9. ValueErrors raise from the named public function with the real
   message prefixes quoted in the Worked example: rear-wall design
   below Vn = 7 km/s ("... requires a normal impact velocity of at
   least 7 km/s, got Vn ..."), theta at or above 90 or negative
   ("impact angle must be in [0, 90) degrees, got ..."), zero or
   negative thicknesses, densities, hardness, sound speed, yield
   stress, mass, and velocity ("... must be a positive number, got
   ..."), negative lambda ("expected penetrating impacts must be
   non-negative, got ..."), and any boolean argument ("... must be a
   real number, got ...").
10. Determinism: two consecutive whipple_penetration_verdict calls
    return identical dicts; no randomness anywhere; no imports beyond
    math; module constants C_CP = 5.24, K_PERFORATION = 1.8,
    K_DETACHED_SPALL = 2.2, K_INCIPIENT_SPALL = 3.0, C_HYPER = 3.918,
    C_WALL_DESIGN = 0.16, CB_NEAR = 0.25, CB_FAR = 0.20, V_LOW = 3.0,
    V_HIGH = 7.0, THETA_CAP_DEG = 65.0 fixed as above.
11. No exact-float equality on computed sums; use
    assertAlmostEqual/math.isclose everywhere. Test passes under BOTH
    interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3).
12. Run the deterministic contract test offline (no network); it
    exits 0. All worked-example numbers above were verified
    byte-identical under both interpreters before spec time.

## Corpus fragment (probe receipt gate (e), wave48-recon/task-9-receipt.md)

The two wordable Hit@1 queries of the wave-48 probe, sim-verified by
exact replication of scripts/router_eval.py (hyphen-preserving
tokens, stopword filter, tag weight 3 / name 2 / desc 1 / body 0.5,
verbatim-phrase bonus 4, tie-break path asc) over the real 657-file
index plus the in-memory candidate:

Query 1 (copy verbatim):
  "size a whipple shield for a spacecraft: rear wall thickness that
  stops a 1 cm aluminum projectile at 7 km per second hypervelocity
  impact"
  scored candidate mmod-shielding-sizing 16.0; runner-up
  space-systems/mission-design/radiation-debris 7.5; margin 8.5
  (strong).
Query 2 (copy verbatim):
  "compute the ballistic limit of a single aluminum wall and a
  whipple shield bumper for a micrometeoroid projectile at 10 km per
  second"
  scored candidate 14.5; runner-up
  aerodynamics/high-speed/regular-shock-reflection 5.0; margin 9.5
  (strong).
Zero-theft audit: with the candidate injected, all 1306 corpus tasks
still Hit@1 their expected_skill and 0 tasks route to the candidate
(w20-radiation-debris-1/2, the shared-vocabulary pair, still route
to radiation-debris). Boundary note from the receipt: a deliberately
risk-flavored phrasing ("...penetration risk over the mission life")
scores only 2.5 against radiation-debris, marking the honest seam
line: environment/risk-probability language belongs to
radiation-debris, shield-sizing language to the candidate. Prep grep
re-run fresh at spec time: each of the tokens micrometeoroid,
hypervelocity, whipple, ballistic-limit, mmod (real hits), and
debris-penetration returns ZERO matches in every skills/ SKILL.md and
in eval/hit1-corpus.yaml over all 1306 task blocks (grep exit 1),
so the queries are collision-free. Task ids follow the wave-48 close
convention (w48-mmod-shielding-sizing-1 and -2). Add one routing
bullet to radiation-debris at build time pointing whipple-shield,
ballistic-limit, and "impact protection sizing" questions at the new
leaf (wave-45 routing-line precedent), keeping flux and
collision-probability questions with radiation-debris.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size meteoroid and orbital
debris (MMOD) impact protection:" and include the outputs in the
Claim order (the Cour-Palais cratering penetration depth and the
critical projectile diameter of a single aluminum wall, the Whipple
shield bumper and rear-wall design thicknesses for the
no-penetration condition at the design projectile, the Christiansen
three-regime critical diameter with the 3 and 7 km/s normal-velocity
transitions and the 65 degree obliquity cap, the per-impact
penetration verdict, and the mission penetration probability from
the expected number of penetrating impacts), then close with the
Trigger list. Refer to the environment outputs (debris fluence,
flux, collision probability) strictly as GIVEN inputs supplied by
the space environment assessment; never claim a flux, fluence,
collision-probability, dose, or risk-band output, and never present
material properties or the empirical constants as design data (ecss
is reference-only context; NASA TM-2009-214789 is cited
summary-only). First tag: mmod-shielding-sizing. Metadata tags
EXACTLY as the probe receipt gate (f) lists them, nothing else:
mmod-protection, hypervelocity-impact, whipple-shield,
ballistic-limit, micrometeoroid-shielding, debris-penetration-risk.
All six are hyphenated and all unique tree-wide at spec time (zero
substring hits for the full hyphenated strings anywhere in skills/).
50-150 words, <=1000 chars, no em dash, no content-policy sweep
term, action verb present. Recommended wording (137 words, 986
chars, verified at spec time):

"Use when you must size meteoroid and orbital debris (MMOD) impact
protection: compute the Cour-Palais cratering penetration depth and
critical projectile diameter of a single aluminum wall, size a
Whipple shield bumper and rear wall so a design projectile at its
design impact produces no rear-wall penetration, evaluate the
Christiansen ballistic limit across low, intermediate, and
hypervelocity regimes with the 3 and 7 km/s normal-velocity
transitions and the 65 degree obliquity cap, and grade an impact as
penetration or no penetration against the critical diameter.
Produces the required rear-wall thickness for the no-penetration
condition, the ballistic-limit curve over velocity, and the mission
penetration probability from the expected number of penetrating
impacts. Debris fluence and expected-impact inputs come from the
space environment leaf; no environment model is built. Trigger:
micrometeoroid, whipple shield, hypervelocity impact, ballistic
limit, bumper sizing."

FORBIDDEN TOKENS (belong to siblings): radiation-environment,
trapped-belts, total-ionizing-dose, single-event-effects, seu-rate,
solar-particle-events, orbital-debris, shielding-attenuation,
collision-probability, mission-design and any claim that estimates a
debris flux or fluence, a size power law, the probability of any
impact, a radiation dose, or the ADEQUATE/MARGINAL/EXCEEDED and
LOW/MODERATE/HIGH verdict bands (radiation-debris owns the whole
environment and risk-probability side; here flux, fluence, and
collision probability are GIVEN inputs, never outputs, and the
description must not contain the phrase collision probability);
debris-avoidance, collision-avoidance, station-keeping, delta-v,
maneuver and any avoidance-maneuver claim (orbital-decay and
mission-delta-v-budget); hertzian, contact-stress, indentation,
fatigue, crack-growth and mechanical contact content (structures);
impact-point-prediction, flat-earth, range-equation and artillery
(gnc-autonomy); stuffed-whipple, multi-shock, honeycomb, cfrp,
titanium, mli, do160 and any non-aluminum or non-Whipple shield
variant; and the bare standalone words debris, flux, fluence,
impact, penetration, projectile, shield, bumper, wall, velocity,
spall, cratering, hardness, standoff, and risk as metadata tags (use
only the hyphenated compounds listed above). Never reproduce the
empirical coefficients or equations as design data; NASA
TM-2009-214789 and the Cour-Palais cratering family are
reference-only context.
