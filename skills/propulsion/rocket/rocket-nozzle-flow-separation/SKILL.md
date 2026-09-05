---
name: rocket-nozzle-flow-separation
description: "Use when you must predict flow separation in an overexpanded rocket nozzle: apply the separation-pressure-ratio criterion (wall static pressure falling to K_SEP times ambient, K_SEP 0.4) to decide whether the wall flow separates, find the separation-station area ratio from the isentropic area-Mach relation at the separation pressure, estimate the separation altitude where the nozzle un-separates, and compute the separated-thrust loss and the side-load flag. Produces the separation verdict, separation-station area ratio, separation altitude, corrected thrust and side-load flag. Trigger: rocket-nozzle-flow-separation, separation-pressure-ratio, summerfield-criterion, overexpanded-nozzle, separation-altitude, separated-thrust-loss, side-load-regime."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: propulsion
pack: rocket
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: rocket
  tags: [rocket-nozzle-flow-separation, separation-pressure-ratio, summerfield-criterion, overexpanded-nozzle, separation-altitude, separated-thrust-loss, side-load-regime]
  version: 0.1.0
  author: AeroSkills
---

# Rocket Nozzle Flow Separation (propulsion/rocket/rocket-nozzle-flow-separation)

Use when you must predict wall flow separation inside an overexpanded
rocket nozzle operating below its design altitude. This leaf applies the
separation-pressure-ratio criterion (Summerfield class) to decide whether
the nozzle wall flow separates, locates the separation station on the
divergent section through the isentropic area-Mach relation, finds the
altitude at which the nozzle un-separates as the ambient pressure falls,
and reports the separated-thrust correction and the side-load regime flag
that gate off-design nozzle operation. Pure Python, stdlib only. It pairs
with propulsion/rocket/nozzle-design, which owns the ideal attached-flow
sizing envelope from the chamber conditions, and with
propulsion/rocket/combustion-chamber-design for the chamber-side
performance that feeds the nozzle.

## Domain quick reference

- Separation criterion: wall separation occurs when the local wall static
  pressure falls to p_sep = K_SEP * pa with K_SEP = 0.4 (sea-level anchor,
  documented model constant), pa the ambient pressure in Pa.
- Separation Mach number: M_sep = sqrt(((pc/p_sep)**((gamma-1)/gamma) - 1)
  * 2/(gamma-1)), from the chamber pressure pc and the separation pressure.
- Separation station: A_sep/At from the isentropic area-Mach relation at
  M_sep; the flow separates when the exit area ratio Ae_At exceeds
  A_sep/At, and stays attached when Ae_At <= A_sep/At.
- Area-Mach relation: A/A* = (1/M) * ((2/(gamma+1)) * (1 + (gamma-1)/2 *
  M**2))**((gamma+1)/(2*(gamma-1))); at M = 1 the ratio is exactly 1 (the
  throat), and the supersonic branch is monotonic.
- Separation altitude: the altitude where the ISA ambient pressure equals
  the design exit pressure pe_design (bisection over 0 to 20000 m, 100
  iterations), the un-separation altitude for a nozzle designed for
  pe_design; results clamp to the bracket ends.
- ISA pressure: p(h) = 101325 * (1 - 0.0065*h/288.15)**5.2561 below
  11000 m and the isothermal form above, with module data R = 287.0 and
  G0 = 9.80665; the troposphere base is 101325 Pa at 0 m.
- Side-load regime: separated flow with the nozzle overexpanded (design
  exit pressure pe_design below the ambient pressure pa) is where
  asymmetric separation side loads occur.
- Model notes: the corrected thrust in separated_thrust_loss evaluates the
  momentum and the pressure term at the separation station and neglects
  the pressure term beyond it, so the loss is measured against the
  design-point reference m_dot * v_exit at perfect expansion (exit
  pressure matched to ambient); when pe_design is omitted the side-load
  flag follows the separation verdict because reaching p_sep below the
  ambient pressure already means the nozzle runs overexpanded.
- Units are SI throughout: pressures in Pa, temperature in K, areas in
  m^2, flow rate in kg/s, thrust in N, altitude in m.
- ECSS frames the launch-vehicle propulsion context; the relations above
  are standard engineering methodology, summary-only.

## Workflow

1. Fix the operating point: chamber pressure pc, ambient pressure pa,
   specific heat ratio gamma, exit-to-throat area ratio Ae_At, and the
   design exit pressure pe_design. Use GAMMA_DEFAULT 1.2 for hot
   combustion products when gamma is unknown.
2. Get the separation pressure with separation_pressure_ratio(pa): the
   wall static pressure that triggers separation at this ambient pressure.
3. Compute the separation Mach number with separation_mach(pc, p_sep,
   gamma) and the station area ratio with
   separation_station_area_ratio(pc, pa, gamma).
4. Judge the nozzle with separated_verdict(Ae_At, A_sep_At): True means
   the exit lies downstream of the separation station and the flow
   separates at this ambient pressure.
5. Find the un-separation altitude with separation_altitude(pe_design),
   where the ISA ambient pressure equals the design exit pressure, and
   read the ambient pressure at any flight altitude with isa_pressure.
6. Size the thrust impact with separated_thrust_loss(pc, Tc, At, pa,
   gamma, Ae_At): chamber temperature Tc and throat area At scale the
   choked flow; the dict carries the design-point thrust, the corrected
   thrust, the loss and the relative loss.
7. Flag the side-load regime with side_load_flag(separated, pc, pa,
   pe_design): True only when the flow separates while the nozzle runs
   overexpanded at that ambient pressure.
8. Confirm the deterministic checks with the contract test
   scripts/test_rocket_nozzle_flow_separation.py.

## Worked example

pc = 10 MPa, pa = 101325 Pa (sea level), gamma = 1.2, Ae_At = 40,
pe_design = 40 kPa; the thrust-loss scale uses Tc = 3500 K and
At = 0.1 m^2:

- Separation pressure: p_sep = 0.4 * 101325 = 40530 Pa.
- Separation Mach number: M_sep = 3.8787 (3.8787 within 1e-3 of the spec
  anchor at pc/p_sep = 246.7).
- Separation station area ratio: A_sep/At = 23.797 (module output
  23.79742), so the sea-level station sits well upstream of the Ae_At = 40
  exit.
- Verdict: separated_verdict(40, 23.797) is True, the nozzle wall flow
  separates at sea level; a nozzle with Ae_At = 20 stays attached.
- Separation altitude: separation_altitude(40000) = 7185 m (module
  7185.16 m, within 1 percent of 7185 m); isa_pressure(9000) = 30741 Pa
  and isa_pressure(10000) = 26435 Pa bracket the flight corridor.
- Un-separation: at 7185 m the ambient pressure has fallen to the 40 kPa
  design exit pressure and the verdict flips to attached flow.
- Side-load flag: side_load_flag(True, 1e7, 101325, 40000) is True at sea
  level, the separated and overexpanded regime; an un-separated nozzle
  never flags.
- Thrust impact: the design-point thrust is 1.8008 MN and the corrected
  (separation-capped) thrust is 1.5965 MN, a loss of 204.2 kN, 11.34
  percent of the design point. A mild nozzle with Ae_At = 10 stays
  attached and shows zero loss.

## Verification

- Confirm separation_station_area_ratio(1e7, 101325, 1.2) returns
  23.79742, within the spec bound of 23.797, and that the station area
  ratio grows as the ambient pressure falls (higher altitude, less
  separation).
- Confirm separated_verdict(40, 23.797) is True and that a nozzle whose
  Ae_At stays at or below the separation station area ratio is attached.
- Confirm area_ratio_from_mach(1.0, gamma) equals 1.0 for gamma 1.2 and
  1.4, and that separation_altitude(40000) lands within 1 percent of
  7185 m with an ISA pressure round trip back to 40000 Pa.
- Confirm the separated case reports a design-point thrust above the
  corrected thrust with a positive loss, and the attached case reports
  equal thrusts with zero loss.
- Confirm every non-physical input raises ValueError: pc <= 0, pa <= 0,
  gamma <= 1, Ae_At <= 1, pe_design <= 0, negative altitude, negative
  Mach, and a separation pressure at or above the chamber pressure.
- Run the contract test offline: python3
  scripts/test_rocket_nozzle_flow_separation.py (35 tests, deterministic,
  under a second).

## Related leaves

- propulsion/rocket/nozzle-design: the ideal attached-flow nozzle sizing
  envelope from the chamber conditions; this leaf adds the off-design
  separation correction that nozzle-design does not model.
- propulsion/rocket/combustion-chamber-design: chamber-side performance
  that supplies the chamber pressure and temperature inputs used here.
- propulsion/rocket/thrust-vector-control: actuated thrust deflection,
  whose side loads interact with the separated flow regime flagged here.

## Pitfalls

- Reading the separation pressure as an exit pressure: p_sep = K_SEP * pa
  (40530 Pa at sea level) locates a station inside the divergent section;
  the wall flow separates there, so A_sep/At (23.8) is well below the
  Ae_At = 40 exit in the separated case.
- Inverting the verdict: separated means Ae_At exceeds A_sep/At, the exit
  farther downstream than the separation station; an equal or smaller exit
  area ratio keeps the flow attached, and the exact-equal boundary is
  attached.
- Treating the separation altitude as a direct root of the A_sep_At =
  Ae_At crossing: separation_altitude returns the altitude where the ISA
  pressure equals the design exit pressure (bisection over 0 to 20000 m,
  clamped at the ends), the design-point un-separation marker; the verdict
  flips somewhere at or below it on the ascent.
- Confusing the side-load regime with plain separation: side loads need
  separation AND an overexpanded state (pe_design < pa); a separated
  nozzle running at or above its design point does not flag.
- Comparing the corrected thrust against the attached-flow estimate:
  dropping the exit-side pressure deficit of an overexpanded nozzle would
  raise the estimate above the corrected value, which inverts the loss;
  the correction is measured against the design-point reference m_dot *
  v_exit, where the pressure term vanishes.
- Forgetting the flow scale: separated_thrust_loss needs the chamber
  temperature Tc and the throat area At to size the choked flow; without
  them only the area-ratio statements of the criterion are available.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rocket_nozzle_flow_separation.py

The test must pass with exit 0 and covers the worked-example anchors
(p_sep = 40530 Pa, M_sep = 3.8787 within 1e-3, A_sep/At = 23.797,
separation_altitude(40000) near 7185 m within 1 percent, ISA pressures at
9000, 10000 and 11000 m), the area-Mach identity at M = 1 for gamma 1.2
and 1.4, the verdict truth table including the exact-equal boundary, the
growth of the separation station as the ambient pressure falls, the
verdict flip at the separation altitude, the side-load flag across
separated, un-separated and design-above-ambient states, the separated
thrust correction (design point above corrected with a positive loss) and
the attached zero-loss case, the ISA round trip, bracket clamping,
determinism, and ValueError rejection of every non-physical input listed
in the spec.

## Contract test

Run the contract test from the repo root:

    python3 skills/propulsion/rocket/rocket-nozzle-flow-separation/scripts/test_rocket_nozzle_flow_separation.py

Stdlib unittest only, deterministic, offline, 35 test methods, exit 0 in
about a second. The test imports the sibling logic module
rocket_nozzle_flow_separation_logic from its own scripts directory, so no
install or path configuration is needed.

## Compliance

- Standards referenced, not reproduced: ECSS frames the launch-vehicle
  propulsion context; the Summerfield-class separation criterion, the
  isentropic relations and the ISA standard atmosphere above are standard
  engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
