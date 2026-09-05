# Wave-38 leaf spec: rocket-nozzle-flow-separation (propulsion, rocket pack)

- Path: skills/propulsion/rocket/rocket-nozzle-flow-separation/
- Pack: rocket. Closest siblings: nozzle-design (ideal-thrust nozzle design
  from chamber conditions: exit Mach for a target area ratio, choked mass
  flow, exit velocity and static pressure, ideal thrust with the pressure
  term, and the expansion verdict against the ambient pressure - ideal
  envelope only, zero separation regime math), combustion-chamber-design
  (chamber C* and ideal Cf), thrust-chamber-cooling (heat transfer),
  thrust-vector-control (gimbal). Whole-tree grep: "flow separation",
  "Summerfield", "separation pressure ratio", "overexpanded" (as a
  separation regime; nozzle-design uses "overexpanded" only as the ideal
  expansion verdict Pe < Pa) = ZERO owners of the separation-correction
  function in skills/. GENUINE PROP gap (fresh probe).
- Standards id: ecss (reference-only; matches the rocket/nozzle-design
  sibling convention - ECSS frames launch vehicle propulsion). Ledger
  Standard: ecss.
- Family: propulsion

## Claim

Predict flow separation inside an overexpanded rocket nozzle operating
below its design altitude: apply the separation pressure-ratio criterion
to decide whether the nozzle wall flow separates, find the separation
station area ratio by the isentropic area-Mach relation at the separation
pressure, estimate the altitude at which the nozzle un-separates as
ambient pressure falls, and compute the separated thrust correction and
the side-load flag for the off-design regime. Produces the separation
verdict, the separation station area ratio, the separation altitude, the
corrected thrust, and the side-load flag that gate off-design nozzle
operation. Does NOT do: ideal nozzle design and expansion verdict
(nozzle-design); chamber C* and ideal Cf (combustion-chamber-design);
nozzle wall heat transfer (thrust-chamber-cooling).

## Model (implement exactly)

Conventions: SI units. Chamber pressure pc (Pa), ambient pressure pa (Pa),
specific heat ratio gamma, nozzle exit-to-throat area ratio Ae_At
(dimensionless) and the design exit pressure pe_design (Pa) are inputs.
Summerfield-class separation criterion (paraphrased closed form): wall
separation occurs when the local wall static pressure falls to
p_sep = K_SEP * pa with K_SEP = 0.4 (sea-level anchor, documented model
constant). The separation station is found by the isentropic area-Mach
relation at p_sep: M_sep from pc/p_sep, then A_sep/At from the area-Mach
relation. If Ae_At <= A_sep_At the nozzle is not separated at that ambient
pressure (attached flow).

Module constants: K_SEP = 0.4, GAMMA_DEFAULT = 1.2, R = 287.0,
G0 = 9.80665, and an ISA pressure table as module data for the altitude
calculation (sea level 101325 Pa, standard lapse; implement the closed
form p(h) = 101325 * (1 - 0.0065*h/288.15)**5.2561 below 11000 m and the
isothermal form above, standard atmosphere).

Functions (pure stdlib):
- separation_pressure_ratio(pa, k_sep=0.4) -> float p_sep.
- separation_mach(pc, p_sep, gamma) -> float: sqrt(( (pc/p_sep)**((gamma-
  1)/gamma) - 1) * 2/(gamma-1)).
- area_ratio_from_mach(M, gamma) -> float:
  (1/M) * ((2/(gamma+1)) * (1 + (gamma-1)/2 * M**2))**((gamma+1)/(2*(gamma-1))).
- separation_station_area_ratio(pc, pa, gamma) -> float: the area ratio at
  the separation pressure.
- separated_verdict(Ae_At, A_sep_At) -> bool: True (separated) if
  Ae_At > A_sep_At else False.
- isa_pressure(h_m) -> float.
- separation_altitude(pe_design) -> float: altitude where isa_pressure
  equals pe_design (bisection over [0, 20000] m, 100 iterations), the
  un-separation altitude for a nozzle designed for pe_design.
- separated_thrust_loss(...) -> dict: thrust with the pressure term
  evaluated at the separation station rather than the exit for the
  separated case (documented model: the pressure term beyond the
  separation station is neglected); include the ideal thrust and the
  corrected thrust.
- side_load_flag(separated, pc, pa) -> bool: True when separated and the
  nozzle is overexpanded (pe_design < pa), the regime where asymmetric
  separation side loads occur.
ValueErrors: pc <= 0, pa <= 0, gamma <= 1, Ae_At <= 1, pe_design <= 0.

Identity to test: area_ratio_from_mach at M = 1 is 1.0; separation area
ratio grows as pa falls (higher altitude, less separation); a nozzle with
Ae_At below the separation station area ratio is attached; at the
separation altitude the flow un-separates (verdict flips).

## Worked example

Verified at prep: pc = 10 MPa, pa = 101325 Pa (sea level), gamma = 1.2,
Ae_At = 40, pe_design = 40 kPa:
- p_sep = 40530 Pa (0.4 * 101325).
- M_sep = 3.8787; A_sep/At = 23.797.
- separated_verdict(40, 23.797) True (nozzle is separated at sea level).
- separation_altitude(40000) = 7185 m (un-separation altitude).
- isa_pressure at 9000 m = 30741 Pa; at 10000 m = 26435 Pa.
- side_load_flag True at sea level (separated and pe_design < pa).
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds from the closed-form isentropic relations
and the ISA closed form.

## Validation list (contract test must include)

- area_ratio_from_mach(1.0, gamma) == 1.0 for gamma 1.2 and 1.4.
- Mach at pc/p_sep = 246.7 and gamma 1.2 is 3.8787 within 1e-3.
- separation_verdict truth table across area ratios.
- isa_pressure at 0 m is 101325; at 11000 m near 22632 Pa (standard);
  separation_altitude(40000) near 7185 m within 1 percent.
- The un-separated case (Ae_At <= A_sep_At) gives attached flow and no
  side-load flag.
- Ideal thrust exceeds corrected (separated) thrust in the separated case.
- ValueErrors for non-physical inputs.
- Determinism.

## Corpus fragment (eval/hit1-wave38-rocket-nozzle-flow-separation.yaml)

Query 1 (copy verbatim):
  "check the overexpanded rocket nozzle for flow separation with the separation-pressure-ratio criterion and find the separation-station area ratio"
  intent: "propulsion; rocket nozzle flow separation criterion and station"
  expected_skill: "propulsion/rocket/rocket-nozzle-flow-separation"
Query 2 (copy verbatim):
  "estimate the rocket-nozzle separation altitude and the separated-thrust loss for an overexpanded nozzle at sea level"
  intent: "propulsion; nozzle separation altitude and thrust correction"
  expected_skill: "propulsion/rocket/rocket-nozzle-flow-separation"
Task ids: w38-rocket-nozzle-flow-separation-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must predict flow separation in an
overexpanded rocket nozzle:" and include the outputs in the Claim. First
tag: rocket-nozzle-flow-separation. Additional tags ONLY: separation-
pressure-ratio, summerfield-criterion, overexpanded-nozzle, separation-
altitude, separated-thrust-loss, side-load-regime. NEVER single generic
words (nozzle, separation, flow, thrust, pressure, expansion). 50-150
words, <=1000 chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): area ratio design, exit Mach, mass
flow, ideal thrust (nozzle-design); chamber pressure to C* (combustion-
chamber-design); throat heat flux, cooling (thrust-chamber-cooling); gimbal
(thrust-vector-control). The single word "nozzle" belongs to nozzle-design:
embed only the hyphenated leaf tokens in queries.
