# Wave-46 leaf spec: crack-tip-plasticity-correction (structures, materials pack)

- Path: skills/structures/materials/crack-tip-plasticity-correction/
- Pack: materials (present siblings creep-rupture, fracture-toughness,
  material-selection, mmpsd-allowables, multiaxial-yield-criteria,
  ramberg-osgood; adjacent fences quoted below from the damage-tolerance
  LEFM leaves crack-growth, residual-strength and walker-forman-crack-
  growth, which are the linear-elastic consumers this correction feeds,
  and from the materials siblings that own the yield and allowable
  context). STR 61 probe receipt task-11 GO rank 2 (extension);
  wave-46 leaf-plan item 10; gates (a)-(f) verbatim in the receipt.
- Claim fences (quoted from the sibling SKILL.md files at prep,
  re-verified by fresh reads at spec time):
  - materials/fracture-toughness is the K_IC and plane-strain VALIDITY
    owner: it QUOTES the plastic-zone-derived ASTM E399 size rule but
    never computes the zone or the effective crack. Its body reads
    "Plane-strain validity (ASTM E399 test context): a valid K_IC test
    requires specimen thickness B and crack size a both >= 2.5 *
    (K_IC / sigma_ys) ** 2, with sigma_ys the 0.2 percent offset yield
    strength. Anchor: K_IC = 30 MPa sqrt(m), sigma_ys = 500 MPa gives
    2.5 * (30 / 500) ** 2 = 9 mm; thinner specimens measure a
    plane-stress or transitional toughness, not K_IC" (SKILL.md lines
    51-56). Its quick reference pins the applied-K form
    "K = Y * sigma * sqrt(pi * a)" with "Y the dimensionless geometry
    factor (1.0 for a crack in an infinite plate, 1.12 for an edge
    crack)" (lines 36-41); that K evaluation is the shared LEFM input
    this leaf reuses, exactly as walker-forman reuses the crack-growth
    form only as the input to its correction. The E399 rule arithmetic
    (factor 2.5 on (K/sigma_ys)^2) appears here only in its applied-K
    form as the small-scale-yielding verdict of the correction; the
    K_IC test-specimen validity check itself stays with
    fracture-toughness.
  - damage-tolerance/walker-forman-crack-growth declares the LEFM
    scope of the rate leaves and corrects nothing: its body reads "mode
    I through-thickness crack in a wide panel (geometry factor Y
    constant), single half-crack length a growing from a0, far-field
    tension, constant amplitude and constant R within a segment with R
    in [-1, 1) and the Walker exponent gamma in (0, 1], linear-elastic
    small-scale-yielding conditions, material constants C, m, C_F,
    gamma and K_c given (no da/dN test-data fitting). No crack-closure
    (Elber) corrections, no threshold, no spectrum cycle counting and
    no variable-amplitude sequence beyond piecewise-constant R
    segments" (lines 41-49). The wave-45 empirical decline (da/dN
    threshold and Elber crack closure) STANDS and is not reopened by
    this spec; this leaf is the deterministic Irwin/Dugdale effective-
    crack correction, a different slice that was never adjudicated.
  - Whole-tree greps at prep (real runs, receipt gate (a)): "plastic-
    zone", "dugdale", "strip-yield", "effective-crack" and "r_p"
    return zero leaf hits across skills/ (no leaf computes a plastic
    zone radius, an effective crack length or a strip-yield zone);
    j-integral, ctod, epfm, tearing modulus: zero hits. The empirical
    Elber closure slice wave-45 declined is not this content.
- Standards id: mmpsd (exists in standards-map.yaml, line 160, the
  materials-pack convention: fracture-toughness carries mmpsd
  reference-only, compliance STANDARDS-REF, gated false; the worked
  example uses the 7075-T6 yield strength 503 MPa, a published
  mmpsd-typical value, referenced not reproduced). Ledger Standard:
  mmpsd.
- Family: structures

## Claim

Compute the small-scale-yielding (plastic-zone) correction to the
linear-elastic mode I stress intensity of a cracked metallic part:
evaluate the Irwin plastic-zone radius in the two constraint states
(plane stress r_p = (1/pi)*(K/sigma_ys)^2, plane strain r_p =
(1/(3*pi))*(K/sigma_ys)^2, the plane-strain zone exactly one third of
the plane-stress zone at equal K and sigma_ys), form the single-pass
effective crack length a_eff = a + r_p with r_p evaluated from the
UNCORRECTED elastic K = Y*sigma*sqrt(pi*a), and compute the corrected
stress intensity K_eff = Y*sigma*sqrt(pi*a_eff) with the k-eff over
elastic-K ratio K_eff/K = sqrt(a_eff/a). Evaluate the Dugdale
strip-yield zone of a center crack (exact secant form rho =
a*(sec(pi*sigma/(2*sigma_0)) - 1) for the infinite-sheet center crack
with strip stress sigma_0, and the small-scale-yielding asymptote
rho_ssy = (pi/8)*(K/sigma_0)^2 whose zone coefficient sits above the
Irwin plane-stress zone by exactly pi^2/8), the Dugdale effective crack
a_eff = a + rho and its corrected stress intensity. Judge the
LEFM-validity verdict from the small-scale-yielding size rule in its
applied-K arithmetic: plane-strain LEFM results (the rate laws of
crack-growth / walker-forman and the K_IC-critical crack of
fracture-toughness / residual-strength) remain valid when the crack
size a is at least 2.5*(K/sigma_ys)^2, equivalently when the
plane-stress zone fraction r_p/a stays at or below 1/(2.5*pi) = 0.1273
(a_req = 2.5*pi*r_p_ps). Produces the plane-stress and plane-strain
plastic-zone radii, the plane-strain over plane-stress zone ratio, the
effective crack length, the corrected stress intensity K_eff with the
k-eff ratio over the elastic K, the size-rule required crack size with
the a/a_req margin and the zone-fraction ratios, the Dugdale strip-yield
zone (exact and SSY asymptote) with the exact/ssy ratio, and the
LEFM-validity verdict that gates when the elastic-K results of the LEFM
siblings need the effective-crack correction. Does NOT do: the
plane-strain fracture toughness K_IC, the ASTM E399 test-specimen
validity boolean on K_IC with thickness B, the critical crack size at
K_IC, or the fast-fracture criterion (fracture-toughness owns the K_IC
frame; this leaf uses the same 2.5*(K/sigma_ys)^2 arithmetic only as
the applied-K small-scale-yielding gate, never as a test-specimen
verdict and never on K_IC data); the Paris-law da/dN rate, the crack
growth rate projection or cycles-to-critical of an uncorrected or
corrected crack, or the Y*sigma*sqrt(pi*a) product as a delivered
result (crack-growth owns the R = 0 Paris arm; walker-forman owns the
stress-ratio and K_c-limited rates; this leaf reuses the K form only as
the input to the zone and delivers K_eff, never a rate); residual
strength, the critical crack length at K_c, fracture margins or the
fracture endpoint (residual-strength); net-section yield, plastic
collapse or limit analysis of the cracked section beyond small-scale
yielding (fem plastic-collapse-analysis vein); J-integral, CTOD,
R-curve tearing or any elastic-plastic fracture mechanics (declined
wave-45, stands); da/dN threshold and Elber crack-closure corrections
(wave-45 decline, stands); any ASTM E399 or MMPDS standard text
(reference-only, paraphrase and formula arithmetic only); test-data
fitting of any material constant. Scope: mode I crack in a wide panel,
geometry factor Y constant, remote tension sigma below yield, single
crack size a in meters, sigma and sigma_ys in MPa, K in MPa*sqrt(m),
zones and a_eff in meters; Dugdale strip-yield arm applies to the
center crack (Y = 1) with applied stress below the strip stress sigma_0.
Deterministic, pure stdlib math, single-pass classical Irwin correction
(r_p from the uncorrected K, no iteration).

## Model (implement exactly)

Pure stdlib, math only. No numpy, no scipy, no RNG, no external
processes. Module constants (pin exactly):

- COEF_IRWIN_PS = 1.0 / math.pi = 0.3183098861837907 (plane-stress zone
  coefficient; r_p = COEF_IRWIN_PS * (K/sigma_ys)^2).
- COEF_IRWIN_PE = 1.0 / (3.0 * math.pi) = 0.1061032953945969
  (plane-strain zone coefficient, exactly COEF_IRWIN_PS / 3).
- COEF_DUGDALE_SSY = math.pi / 8.0 = 0.3926990816987241 (Dugdale
  small-scale-yielding zone coefficient).
- SIZE_RULE_FACTOR = 2.5 (the E399-derived plane-strain size-rule
  factor in applied-K arithmetic, quoted as summary arithmetic only).
- RHO_OVER_RP_PS = COEF_DUGDALE_SSY / COEF_IRWIN_PS = pi^2/8 =
  1.233700550136170 exactly to roundoff (Dugdale SSY zone over Irwin
  plane-stress zone).

Defining relations (implement exactly; every function derives from
these):

- Mode I stress intensity: K = Y*sigma*sqrt(pi*a) in MPa*sqrt(m) with
  sigma in MPa and a in meters (the shared LEFM form of the fracture-
  toughness and crack-growth siblings, reused here as the zone input).
- Irwin plastic-zone radius: plane stress r_p = (1/pi)*(K/sigma_ys)^2;
  plane strain r_p = (1/(3*pi))*(K/sigma_ys)^2 = r_p_ps / 3.
- Single-pass effective crack: a_eff = a + r_p, where r_p is evaluated
  from the UNCORRECTED elastic K (the classical Irwin treatment, one
  pass, no iteration; iteration is a stated extension, not this
  contract).
- Corrected stress intensity: K_eff = Y*sigma*sqrt(pi*a_eff), so the
  k-eff ratio over the elastic K is exactly K_eff/K = sqrt(a_eff/a)
  at fixed Y*sigma (identity holds to roundoff).
- Dugdale strip-yield zone (exact, infinite-sheet center crack):
  rho = a*(sec(pi*sigma/(2*sigma_0)) - 1) with sec = 1/cos and sigma_0
  the strip (flow) stress; the model requires sigma < sigma_0, the
  zone diverges as sigma approaches sigma_0.
- Dugdale small-scale-yielding asymptote:
  rho_ssy = (pi/8)*(K/sigma_0)^2 with K = sigma*sqrt(pi*a), the exact
  zone collapses onto it as sigma/sigma_0 goes to zero; the zone
  coefficient ratio rho_ssy/r_p_ps = pi^2/8 = 1.233700550136170.
- LEFM-validity size rule (applied-K arithmetic of the plane-strain
  rule the fracture-toughness sibling quotes): valid iff
  a >= 2.5*(K/sigma_ys)^2, equivalently a_req = 2.5*pi*r_p_ps (exact
  identity), equivalently r_p_ps/a <= 1/(2.5*pi) = 0.127323954473516
  and r_p_pe/a <= 1/(7.5*pi) = 0.042441318157839.

Functions:

- stress_intensity(sigma_mpa, a_m, y) -> float: K = y*sigma*sqrt(pi*a)
  in MPa*sqrt(m). ValueError: sigma <= 0, a <= 0, y <= 0.
- irwin_plastic_zone(k_mpa_sqrtm, sigma_ys_mpa, constraint) -> float:
  r_p in meters. constraint is the string "plane-stress" or
  "plane-strain"; plane stress r_p = (1/pi)*(k/sigma_ys)^2, plane
  strain r_p = (1/(3*pi))*(k/sigma_ys)^2. ValueError: k <= 0,
  sigma_ys <= 0, constraint not one of the two strings.
- effective_crack_length(a_m, r_p_m) -> float: a_eff = a + r_p in
  meters. ValueError: a <= 0, r_p < 0.
- irwin_effective_correction(sigma_mpa, a_m, y, sigma_ys_mpa,
  constraint) -> dict: the full single-pass correction. Keys:
  "k_mpa_sqrtm" (elastic K from the uncorrected a), "r_p_m",
  "a_eff_m", "k_eff_mpa_sqrtm" (Y*sigma*sqrt(pi*a_eff)),
  "k_eff_over_k". Single pass: r_p from the elastic K, a_eff = a + r_p,
  K_eff at a_eff. ValueErrors propagate from the three building
  functions; a negative applied stress raises.
- dugdale_strip_zone(a_m, sigma_mpa, sigma_0_mpa) -> float: exact rho =
  a*(1/cos(pi*sigma/(2*sigma_0)) - 1) in meters. ValueError: a <= 0,
  sigma <= 0, sigma_0 <= 0, sigma >= sigma_0 (zone undefined at and
  beyond the full-strip yield state).
- dugdale_ssy_zone(k_mpa_sqrtm, sigma_0_mpa) -> float:
  rho_ssy = (pi/8)*(k/sigma_0)^2 in meters. ValueError: k <= 0,
  sigma_0 <= 0.
- dugdale_effective_correction(sigma_mpa, a_m, sigma_0_mpa) -> dict:
  the full Dugdale effective-crack correction for the center crack
  (Y = 1). Keys: "k_mpa_sqrtm" (sigma*sqrt(pi*a)), "rho_m" (exact
  zone), "a_eff_m" (a + rho), "k_eff_mpa_sqrtm"
  (sigma*sqrt(pi*a_eff)), "k_eff_over_k". ValueErrors propagate from
  dugdale_strip_zone and stress_intensity.
- sxy_validity(k_mpa_sqrtm, sigma_ys_mpa, a_m) -> dict: the
  small-scale-yielding (LEFM-validity) verdict. Keys: "required_a_m" =
  2.5*(k/sigma_ys)^2, "a_over_required" (a / required_a),
  "r_p_ps_over_a" (plane-stress zone fraction),
  "r_p_pe_over_a" (plane-strain zone fraction), "valid" (True iff
  a >= required_a_m). ValueError: k <= 0, sigma_ys <= 0, a <= 0.

Identities to test (closed form, deterministic; all values are REAL
outputs of the spec-prep anchor, see Worked example):

- Plane-strain over plane-stress zone: r_p_pe = r_p_ps / 3 exactly for
  equal K and sigma_ys (anchor residual 0.0 at the worked example).
- SSY limit recovery: as sigma_ys goes to infinity, r_p goes to zero,
  a_eff goes to a and K_eff goes to K; at sigma_ys = 1e9 MPa the
  k-eff over elastic-K ratio minus 1 is 2.043e-14 (anchor value,
  roundoff-level collapse onto the elastic result).
- Zone coefficient identity: rho_ssy / r_p_ps = pi^2/8 =
  1.233700550136170 exactly to roundoff (anchor residual 0.0).
- k-eff ratio identity: K_eff/K = sqrt(a_eff/a) exactly to roundoff
  for BOTH the Irwin chain (residual 0.0) and the Dugdale chain
  (residual 0.0); equivalently K_eff = y*sigma*sqrt(pi*a_eff)
  recomputed from a_eff (residual 0.0).
- Asymptote collapse: the exact Dugdale zone collapses onto the SSY
  asymptote as sigma/sigma_0 goes to zero; at sigma = 1% of sigma_0
  the exact/ssy zone ratio is 1.000102818695661 (anchor value).
- Size-rule identity: a_req = 2.5*(K/sigma_ys)^2 equals 2.5*pi*r_p_ps
  exactly to roundoff (anchor residual 0.0); the verdict flips at
  r_p_ps/a = 1/(2.5*pi).
- Divergence guard: dugdale_strip_zone grows without bound as sigma
  approaches sigma_0 from below and raises ValueError at sigma = sigma_0
  (anchor: sigma = 0.999*sigma_0 zone >> sigma = 0.9*sigma_0 zone, and
  sigma = sigma_0 raises).
- Determinism: two identical runs produce identical bits (canonical
  dump sha256 1294bcbbe76231d1932cbfdabb3aac2374c905f8014a27671314e61e35c1483a
  under both /usr/bin/python3 3.9.6 and the pyenv 3.13.12 interpreter);
  no imports beyond math; no RNG.

## Worked example

7075-T6 aluminium (sigma_ys = 503 MPa, an mmpsd-typical published
value, referenced not reproduced; the Dugdale strip carries the strip
stress sigma_0 = sigma_ys = 503 MPa in both examples below, so "90
percent of the flow stress" is sigma = 0.9*503 = 452.7 MPa). All
values below are REAL outputs of the prep anchor
/tmp/w46spec/anchor_crack_tip_plasticity.py (stdlib math, exit 0,
deterministic; identical bits under /usr/bin/python3 3.9.6 and
~/.pyenv/versions/3.13.12/bin/python3; canonical dump sha256
1294bcbbe76231d1932cbfdabb3aac2374c905f8014a27671314e61e35c1483a).

Case 1 (corpus query 1): 5 mm edge crack in 7075-T6 at 180 MPa,
Y = 1.12, a = 0.005 m, sigma = 180 MPa, sigma_ys = 503 MPa.

- Elastic K = Y*sigma*sqrt(pi*a) = 1.12*180*sqrt(pi*0.005) =
  25.266813008280486 MPa*sqrt(m).
- Plane-stress zone: r_p = (1/pi)*(25.266813008280486/503)^2 =
  8.031840764557785e-04 m (0.803184 mm). Plane-strain zone:
  2.677280254852595e-04 m (0.267728 mm), exactly one third.
- Plane-stress effective crack and correction: a_eff = 0.005 +
  8.031840764557785e-04 = 0.005803184076456 m (5.803184 mm); K_eff =
  1.12*180*sqrt(pi*0.005803184076456) = 27.220659146174018
  MPa*sqrt(m); K_eff/K = 1.077328554940950 (the elastic K under-predicts
  by 7.7 percent in plane stress).
- Plane-strain effective crack and correction: a_eff =
  0.005267728025485 m (5.267728 mm); K_eff = 25.934455611168520
  MPa*sqrt(m); K_eff/K = 1.026423696675526 (2.6 percent, the reduced
  zone of the constrained state).
- Small-scale-yielding verdict: required_a = 2.5*(K/503)^2 =
  0.006308192985184 m (6.308193 mm); a/a_req = 0.792620012060999,
  BELOW 1, so the verdict at 180 MPa is LIMIT EXCEEDED: the crack is
  5 mm against a 6.31 mm plane-strain rule size, the plane-stress zone
  fraction r_p_ps/a = 0.160636815291156 exceeds the 0.1273 bound and
  the plane-strain fraction r_p_pe/a = 0.053545605097052 exceeds the
  0.0424 bound. This is the near-limit band where the effective-crack
  correction matters most: it is exactly why the leaf exists. Zone
  sanity: 0.27 to 0.80 mm on a 5 mm crack, K_eff a few percent above K
  in the valid band (see case 1b).
- Case 1b (valid companion, same crack at sigma = 120 MPa): K =
  16.844542005520324 MPa*sqrt(m); r_p_ps = 3.569707006470125e-04 m
  (0.356971 mm); a_eff = 0.005356970700647 m (5.356971 mm); K_eff =
  17.435477292409118 MPa*sqrt(m); K_eff/K = 1.035081706982305 (3.5
  percent); required_a = 0.002803641326749 m (2.803641 mm) < a, verdict
  VALID. K_eff/K at 3.5 percent with the zone at 7.1 percent of a is
  the textbook small-correction band.

Case 2 (corpus query 2): Dugdale strip-yield on a center crack loaded
to 90 percent of the flow stress, Y = 1.0, a = 0.010 m, strip stress
sigma_0 = 503 MPa, sigma = 0.9*503 = 452.7 MPa.

- Elastic K = 452.7*sqrt(pi*0.010) = 80.238985830492709 MPa*sqrt(m).
- Exact strip-yield zone: rho = 0.010*(1/cos(pi*452.7/(2*503)) - 1) =
  5.392453221499650e-02 m (53.924532 mm), 5.392 times the half-crack:
  the strip-yield zone is huge at 90 percent of the flow stress, the
  small-scale-yielding limit is far exceeded.
- Effective crack and correction: a_eff = 0.010 + 5.392453221499650e-02
  = 0.063924532214996 m (63.924532 mm); K_eff =
  452.7*sqrt(pi*0.063924532214996) = 202.870645082888728 MPa*sqrt(m);
  K_eff/K = 2.528330125102268 (k-eff 2.53 times the elastic K).
- SSY asymptote comparison: rho_ssy = (pi/8)*(80.238985830492709/503)^2
  = 9.992974456102975e-03 m (9.992974 mm); the exact zone is
  5.396244376674391 times the asymptote, so the small-scale-yielding
  asymptote under-predicts the strip-yield zone by a factor of 5.4 at
  90 percent of the flow stress and LEFM elastic results are not valid
  here (the required size rule at this K reads a_req =
  2.5*(80.238985830492709/503)^2 = 0.06361725123519331 m against a =
  0.010 m, a/a_req = 0.157190067251255). The case demonstrates the
  exact secant Dugdale arm that the leaf must deliver beyond the SSY
  band.

Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of
/tmp/w46spec/anchor_crack_tip_plasticity.py (stdlib math, exit 0,
deterministic, canonical dump sha256
1294bcbbe76231d1932cbfdabb3aac2374c905f8014a27671314e61e35c1483a on
both interpreters).

## Validation list (contract test must include)

- stress_intensity(180.0, 0.005, 1.12) = 25.266813008280486 within 1e-9
  relative and equals 1.12*180*sqrt(pi*0.005) by construction;
  stress_intensity(452.7, 0.010, 1.0) = 80.238985830492709 within 1e-9
  relative.
- irwin_plastic_zone(25.266813008280486, 503.0, "plane-stress") =
  8.031840764557785e-04 within 1e-9 relative;
  irwin_plastic_zone(25.266813008280486, 503.0, "plane-strain") =
  2.677280254852595e-04 within 1e-9 relative and equals the
  plane-stress value / 3 to roundoff.
- effective_crack_length(0.005, 8.031840764557785e-04) =
  0.005803184076456 within 1e-9 relative.
- irwin_effective_correction(180.0, 0.005, 1.12, 503.0,
  "plane-stress"): k 25.266813008280486, r_p 8.031840764557785e-04,
  a_eff 0.005803184076456, k_eff 27.220659146174018, k_eff_over_k
  1.077328554940950, each within 1e-9 relative; the same call with
  "plane-strain": r_p 2.677280254852595e-04, a_eff 0.005267728025485,
  k_eff 25.934455611168520, k_eff_over_k 1.026423696675526; the
  k_eff_over_k of each chain equals sqrt(a_eff/a) to roundoff (single
  pass: r_p from the uncorrected elastic K, then K_eff at a_eff).
- irwin_effective_correction(120.0, 0.005, 1.12, 503.0,
  "plane-stress"): k 16.844542005520324, r_p 3.569707006470125e-04,
  a_eff 0.005356970700647, k_eff 17.435477292409118, k_eff_over_k
  1.035081706982305 within 1e-9 relative.
- dugdale_strip_zone(0.010, 452.7, 503.0) = 5.392453221499650e-02
  within 1e-9 relative; dugdale_strip_zone(0.010, 0.01*503.0, 503.0)
  = 1.000102818695661 times dugdale_ssy_zone(stress_intensity(5.03,
  0.010, 1.0), 503.0) within 1e-6 relative (asymptote collapse at 1
  percent of the flow stress); the zone at sigma = 0.999*503.0 is
  greater than the zone at sigma = 0.9*503.0 by more than 10x (zone
  grows without bound toward the full-strip yield state).
- dugdale_ssy_zone(80.238985830492709, 503.0) = 9.992974456102975e-03
  within 1e-9 relative and equals (pi/8)*(k/503)^2 by construction;
  dugdale_ssy_zone(25.266813008280486, 503.0) / (1/pi)*
  (25.266813008280486/503)^2 = 1.233700550136170 = pi^2/8 to roundoff.
- dugdale_effective_correction(452.7, 0.010, 503.0): k
  80.238985830492709, rho 5.392453221499650e-02, a_eff
  0.063924532214996, k_eff 202.870645082888728, k_eff_over_k
  2.528330125102268, each within 1e-9 relative; k_eff_over_k equals
  sqrt(a_eff/a) to roundoff.
- sxy_validity(25.266813008280486, 503.0, 0.005): required_a_m
  0.006308192985184, a_over_required 0.792620012060999, r_p_ps_over_a
  0.160636815291156, r_p_pe_over_a 0.053545605097052, valid False;
  sxy_validity(16.844542005520324, 503.0, 0.005): required_a_m
  0.002803641326749, valid True; sxy_validity(80.238985830492709,
  503.0, 0.010): required_a_m 0.06361725123519331, a_over_required
  0.157190067251255, valid False; required_a_m equals
  2.5*pi*r_p_ps to roundoff (identity, no exact float equality).
- Monotonicity and direction bounds: irwin_plastic_zone and the
  k_eff_over_k ratio are strictly increasing in K at fixed sigma_ys;
  the plane-strain zone is below the plane-stress zone for every valid
  input; k_eff_over_k of case 1b (1.035081706982305) < k_eff_over_k of
  case 1 (1.077328554940950) < k_eff_over_k of case 2
  (2.528330125102268): the correction grows with the load ratio.
- ValueErrors across the module, each raising ValueError: stress_
  intensity sigma = 0, sigma < 0, a = 0, y = 0; irwin_plastic_zone
  k = 0, sigma_ys = 0, constraint = "plane" (not one of the two
  strings); effective_crack_length a = 0, r_p < 0;
  irwin_effective_correction with a negative applied stress;
  dugdale_strip_zone sigma = sigma_0 (452.7 case at sigma_0 = 452.7),
  sigma > sigma_0 (600 vs 503), a = 0; dugdale_ssy_zone k = 0;
  sxy_validity k < 0, sigma_ys = 0, a = 0 (14 anchor cases, every one
  raises).
- Determinism: two identical runs return identical bits (canonical
  dump sha256
  1294bcbbe76231d1932cbfdabb3aac2374c905f8014a27671314e61e35c1483a on
  both runs); no imports beyond math and hashlib; no RNG.
- Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
  ~/.pyenv/versions/3.13.12/bin/python3). No exact-float equality on
  computed sums; use assertAlmostEqual/math.isclose everywhere.
  Contract test file named test_crack_tip_plasticity_correction.py
  (underscores), unittest, offline in well under 20 seconds.

## Corpus fragment (eval/hit1-wave46-crack-tip-plasticity-correction.yaml)

Query 1 (copy verbatim from the receipt gate (e)):
  "compute the irwin-plastic-zone radius and the effective-crack-length
  correction for the 5 mm edge crack in 7075-T6 at 180 MPa: the
  small-scale-yielding ratio of the plastic zone to the crack size, the
  corrected stress intensity K_eff at the effective crack and the
  LEFM-validity verdict"
  intent: "structures; Irwin plastic-zone radius (plane stress and
  plane-strain), the effective-crack-length single-pass correction
  a_eff = a + r_p, the corrected stress intensity K_eff at the
  effective crack, the plastic-zone-to-crack size ratio and the
  LEFM-validity (small-scale-yielding) verdict of a 5 mm edge crack in
  7075-T6 at 180 MPa"
  expected_skill: "structures/materials/crack-tip-plasticity-correction"
Query 2 (copy verbatim from the receipt gate (e)):
  "apply the dugdale-strip-yield model to the center crack loaded to 90
  percent of the flow stress: the strip-yield plastic-zone size, the
  effective-crack-length corrected stress intensity and the k-eff to
  elastic-K ratio when the small-scale-yielding limit is exceeded"
  intent: "structures; Dugdale strip-yield model on a center crack at
  90 percent of the flow stress: the exact secant strip-yield zone, the
  effective-crack-length corrected stress intensity and the k-eff to
  elastic-K ratio beyond the small-scale-yielding limit"
  expected_skill: "structures/materials/crack-tip-plasticity-correction"
Task ids: w46-crack-tip-plasticity-correction-1 and -2. Prep grep and
probe: the distinctive tokens irwin-plastic-zone, effective-crack-
length, dugdale-strip-yield-model, small-scale-yielding-check,
k-eff-correction and plastic-zone-radius each match ZERO existing
eval/hit1-corpus.yaml tasks (receipt gate (e), real greps over all
1266 tasks) and ZERO SKILL.md bodies (receipt gate (a)); the existing
fracture-toughness tasks route on kic, stress-intensity-factor,
critical-crack-size and plane-strain tokens, the crack-growth and
walker-forman tasks on paris-law, delta-k, equivalent-delta-k,
kc-limited and stress-ratio tokens, with no overlap into the
plastic-zone / effective-crack / strip-yield token space, so no theft
in either direction. Build-time fence note (wave precedent, receipt
gate (f)): add one routing line to fracture-toughness and one to
crack-growth pointing plastic-zone, effective-crack-length and
small-scale-yielding questions at this leaf, and add the
structures/materials/crack-tip-plasticity-correction row to the family
router (skills/structures/SKILL.md).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the crack-tip-plastic-
ity-correction for a crack in metallic structure:" and include the
outputs in the Claim order (plane-stress and plane-strain plastic-zone
radii, effective-crack-length, corrected stress intensity K_eff, the
k-eff-correction ratio, the Dugdale strip-yield zone, the
small-scale-yielding verdict). First tag: crack-tip-plasticity-
correction (the leaf name). Additional tags ONLY, the exact receipt
gate (f) set, all hyphenated compounds:
irwin-plastic-zone, effective-crack-length, dugdale-strip-yield-model,
small-scale-yielding-check, k-eff-correction, plastic-zone-radius
(frontmatter metadata.tags order: crack-tip-plasticity-correction,
irwin-plastic-zone, effective-crack-length, dugdale-strip-yield-model,
small-scale-yielding-check, k-eff-correction, plastic-zone-radius).
NEVER single generic words (plastic, plastic zone, crack, crack tip,
stress, intensity, yield, zone, correction, aluminum, metal, material,
growth, toughness, fracture, K_eff alone) and NEVER the sibling-owned
tag strings or steering tokens: fracture-toughness, kic, stress-
intensity-factor, critical-crack-size, plane-strain, fast-fracture,
damage-tolerance (fracture-toughness, which owns the K_IC and E399
plane-strain validity frame), crack-growth, paris-law, stress-intensity,
fatigue-crack, fracture-mechanics, da-dn, delta-k (crack-growth, which
owns the Paris rate arm), residual-strength, critical-crack-length,
limit-load, crack-length (residual-strength, which owns the K_c
fracture endpoint), walker-forman-crack-growth, walker-equation,
forman-equation, r-ratio-correction, equivalent-delta-k,
kc-limited-growth, stress-ratio-crack-growth (walker-forman),
mmpsd-allowables, a-basis, b-basis, k-factor (mmpsd-allowables),
multiaxial-yield-criteria, von-mises-equivalent-stress, tresca-margin
(multiaxial-yield-criteria), elber, crack-closure, da-dn-threshold,
threshold (the wave-45 empirical decline, which stands), j-integral,
ctod, tearing-modulus, epfm (declined wave-45), nor net-section yield,
plastic collapse, limit analysis as claims (fem plastic-collapse-
analysis vein). The description must not contain the strings "paris
law", "damage tolerance", "fatigue crack", "fracture toughness",
"residual strength", "critical crack", "K_IC", "K_c", "elber",
"closure", "delta-k" or "da/dN". 50-150 words, <=1000 chars, action
verb present, no em dash, no content-policy sweep term. Frontmatter
mirrors the materials siblings: name crack-tip-plasticity-correction,
license Apache-2.0, compliance STANDARDS-REF, standards id mmpsd
reference-only, gated false, domain structures, pack materials,
compatibility the standard agentskills.io line, metadata domain
structures, subdomain materials, version 0.1.0, author AeroSkills.
Recommended wording (anchor-checked, 998 chars, 128 words): "Use when
you must compute the crack-tip-plasticity-correction for a crack in
metallic structure: evaluate the Irwin plastic-zone radius in plane
stress r_p = (1/pi)*(K/sigma_ys)^2 and the reduced plane-strain zone
(1/(3*pi))*(K/sigma_ys)^2, form the effective-crack-length a_eff = a +
r_p from the uncorrected elastic K, compute the corrected stress
intensity K_eff = Y*sigma*sqrt(pi*a_eff), and judge the LEFM-validity
verdict from the zone-to-crack ratio against the 2.5*(K/sigma_ys)^2
size rule. Applies the dugdale-strip-yield model to a center crack:
the strip-yield zone rho = a*(sec(pi*sigma/(2*sigma_0)) - 1), its
small-scale-yielding asymptote (pi/8)*(K/sigma_0)^2, and the k-eff to
elastic-K ratio beyond that limit. Produces the plastic-zone radius,
effective crack length, corrected stress intensity, k-eff ratio and
validity verdict gating elastic fracture results. Trigger: plastic
zone, effective crack length, small-scale yielding, Dugdale strip
yield, Irwin zone, K_eff correction." The sibling trigger phrases
"fracture toughness", "stress intensity factor", "Paris law", "damage
tolerance", "residual strength", "critical crack length" and "K_IC"
must not appear as this leaf's trigger list.
