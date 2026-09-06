---
name: rotorcraft-main-rotor-sizing
description: "Use when you must size the main rotor of a single-main-rotor rotorcraft from the takeoff weight and design ceilings: the main-rotor-disk-loading ceiling sets the disk area and radius, the rotor-thrust-coefficient follows from momentum theory at the chosen rotor tip speed, the rotor solidity closes from the ct-over-sigma hover design point, the blade area and chord follow from the blade count on constant-chord blades, and the rotor-tip-mach number checks the tip speed against the speed of sound. Produces the disk area, radius, thrust coefficient, solidity, blade area, chord and tip mach that gate a main rotor sizing pass before the power leaves consume the geometry. Sizing only: closed-form inversions from weight, no rotor power, no flight-state performance; the geometry-consuming rotorcraft leaves keep their owners. Trigger: main rotor sizing, disk loading ceiling, ct-over-sigma, rotor tip speed."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-29
    reference-only: true
gated: false
domain: flight-mechanics
pack: performance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: performance
  tags: [rotorcraft-main-rotor-sizing, main-rotor-disk-loading, rotor-thrust-coefficient, ct-over-sigma, rotor-tip-mach]
  version: 0.1.0
  author: AeroSkills
---

# Main Rotor Sizing (flight-mechanics/performance/rotorcraft-main-rotor-sizing)

Use when you must size the main rotor of a single-main-rotor rotorcraft
from the takeoff weight and the design ceilings, rather than analyze a
rotor whose geometry is already given. The weight-borne hover thrust
T = m * g0 against the chosen main-rotor-disk-loading ceiling sets the
disk area and radius, the rotor-thrust-coefficient follows from
momentum theory at the rotor tip speed, the rotor solidity closes from
the ct-over-sigma hover design point, the blade area and the constant
chord follow from the blade count on rectangular blades, and the
rotor-tip-mach number checks the tip speed against the speed of sound.
Closed-form sizing only, pure Python, stdlib only: no power term, no
inflow solve, no figure of merit, no blade-element sections, no
compressibility corrections beyond the tip Mach check. The geometry it
produces feeds the rotorcraft performance leaves that consume a given
rotor: hover power, forward flight, climb, autorotation, ground effect
and turn. Pairs with flight-mechanics/performance/rotorcraft-tail-rotor-
sizing, which applies the identical disk sizing inversion to the
anti-torque rotor with its own torque-balance inputs.

## Domain quick reference

- Weight-borne hover thrust: T = m * g0, g0 = 9.80665 m/s2, at the
  takeoff mass m.
- Disk area at the ceiling: A = T / DL_max, with DL_max the chosen
  main-rotor-disk-loading ceiling (250-500 Pa band, 350 Pa worked).
- Disk radius: R = sqrt(A / PI).
- Achieved disk loading: T / A equals DL_max exactly when the disk is
  sized with that ceiling.
- Hover thrust coefficient (momentum theory): CT = T / (rho * A *
  Vtip^2) with A = PI * R^2, Vtip the rotor tip speed (200-230 m/s
  band, 210 m/s worked), rho = 1.225 kg/m3 at sea level.
- Ceiling identity: at the sized disk CT = DL_max / (rho * Vtip^2), so
  the thrust coefficient is independent of the rotor size.
- Solidity closure: sigma = CT / (CT/sigma)_design from the ct-over-
  sigma hover design point (0.10-0.14 band, 0.12 worked); the closure
  round trip sigma * (CT/sigma)_design recovers CT.
- Blade area: A_b = sigma * A. Constant blade chord on rectangular
  blades: c = A_b / (b * R) from the blade count b; the solidity
  identity sigma = b * c * R / A recovers the input.
- Rotor tip Mach: M_tip = Vtip / a with a the speed of sound
  (340.3 m/s sea level).
- SI units throughout: N, m, m2, Pa, m/s.
- FAR-29 frames transport rotorcraft certification context; the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Fix the design point: takeoff mass m and the design ceilings, the
   main-rotor-disk-loading ceiling, the ct-over-sigma hover design
   point, the blade count and the rotor tip speed, with the weight-borne
   hover thrust T = m * G0.
2. Size the disk from the weight against the ceiling with
   disk_area_and_radius and confirm the disk sits exactly at the
   main-rotor-disk-loading ceiling (thrust over area round trip and
   PI * radius**2 recovering the area).
3. Compute the rotor-thrust-coefficient at the rotor tip speed with
   hover_thrust_coefficient and cross-check the ceiling identity
   CT = disk_loading_max / (rho * tip_speed**2).
4. Close the rotor solidity from the ct-over-sigma design point with
   solidity_closure and check the design-point round trip CT / sigma.
5. Lay out the rectangular blades with blade_area_chord, total blade
   area and constant blade chord from the blade count, verifying the
   solidity identity sigma = b * c * R / A.
6. Check the rotor-tip-mach number with tip_mach against the speed of
   sound; subcritical at sea level, so no compressibility correction
   enters the sizing.
7. Close out with the deterministic contract test
   scripts/test_rotorcraft_main_rotor_sizing.py.

## Worked example

Primary state: helicopter takeoff mass m = 4500 kg, main-rotor-disk-
loading ceiling DL_max = 350 Pa, ct-over-sigma design point 0.12,
blade count b = 4, rotor tip speed Vtip = 210 m/s, rho = 1.225 kg/m3,
speed of sound a = 340.3 m/s. Module outputs:

- Thrust: T = W = 4500 * 9.80665 = 44129.925 N (weight-borne hover
  reference).
- Disk area: A = 44129.925 / 350 = 126.0855 m2.
- Disk radius: R = sqrt(126.0855 / PI) = 6.3352 m.
- Achieved disk loading: T / A = 350.0 Pa, exactly the ceiling.
- Thrust coefficient: CT = 44129.925 / (1.225 * 126.0855 * 210^2) =
  0.006479, and the ceiling identity 350.0 / (1.225 * 210^2) gives the
  same 0.006479.
- Solidity closure: sigma = 0.006479 / 0.12 = 0.053990; the design
  point check CT / sigma = 0.1200.
- Blade area: A_b = 0.053990 * 126.0855 = 6.8073 m2.
- Blade chord: c = 6.8073 / (4 * 6.3352) = 0.2686 m, blade aspect
  ratio R / c = 23.58 (rectangular constant-chord blades); the
  solidity check b * c * R / A = 0.053990.
- Tip Mach: M_tip = 210.0 / 340.3 = 0.61710, comfortably subcritical
  at sea level, so no compressibility correction enters the sizing.

The light 350 Pa ceiling gives a large disk (about 126 m2, R = 6.34 m)
and hence a low hover thrust coefficient, so the 0.12 design point
closes at sigma about 0.054 with a 0.269 m chord. At fixed tip speed
and design point the solidity scales linearly with the ceiling,
sigma = DL_max / (rho * Vtip^2 * (CT/sigma)_design), about 0.092 at a
600 Pa ceiling.

Secondary state: m = 3000 kg, DL_max = 300 Pa, ct_over_sigma = 0.10,
b = 4, Vtip = 210 m/s: W = 29419.950 N, A = 98.0665 m2,
R = 5.5871 m, achieved disk loading 300.0 Pa, CT = 0.005553,
sigma = 0.055532 (CT / sigma = 0.1000), blade area 5.4459 m2, chord
0.2437 m, and M_tip = 0.61710 unchanged at the fixed tip speed.

## Verification

- Confirm disk_area_and_radius(44129.925, 350.0) returns (126.0855,
  6.3352) and that thrust / area equals 350.0 Pa exactly, the disk
  sized at the ceiling; PI * radius**2 recovers the area.
- Confirm hover_thrust_coefficient(44129.925, 1.225, 6.3352, 210.0)
  returns 0.006479, equal to the ceiling identity 350.0 / (1.225 *
  210^2); the value is independent of the rotor size at a fixed
  ceiling and tip speed.
- Confirm solidity_closure(0.006479, 0.12) returns 0.053990 and that
  the closure round trip sigma * 0.12 recovers the thrust coefficient
  (design-point check CT / sigma = 0.1200).
- Confirm blade_area_chord(0.053990, 126.0855, 4, 6.3352) returns
  (6.8073, 0.2686) and the solidity identity 4 * 0.2686 * 6.3352 /
  126.0855 recovers 0.053990.
- Confirm tip_mach(210.0, 340.3) returns 0.61710.
- Confirm the disk radius scales with the square root of the mass at a
  fixed ceiling (6.3352 m at 4500 kg against 5.5871 m at 3000 kg) and
  that the tip Mach is unchanged when only the mass or the ceiling
  changes at a fixed tip speed.
- Convention cross-check: disk_area_and_radius(1851.8519, 300.0)
  returns (6.1728, 1.4017), matching the rotorcraft-tail-rotor-sizing
  worked example for the shared A = T / DL_max inversion applied to its
  own anti-torque thrust; the torque-balance inputs never enter here.
- Confirm every non-positive thrust, disk loading, air density, radius,
  tip speed, thrust coefficient, ct-over-sigma design point, solidity,
  area and speed of sound, every blade count below 1 and every
  fractional blade count raises ValueError (15 rejection classes).
- No RNG anywhere: repeated runs give identical floats.
- Run the contract test offline: python3
  scripts/test_rotorcraft_main_rotor_sizing.py (35 tests,
  deterministic).

## Pitfalls

- Sizing on a radius that is already given: this leaf derives the disk
  radius from the takeoff weight and the disk-loading ceiling; the
  rotorcraft performance siblings (hover, forward flight, climb, turn)
  all consume a given radius and solidity and never size the rotor.
- Writing the ceiling with the hover sibling's token: the sizing
  ceiling is the main-rotor-disk-loading compound; rotor-disk-loading
  belongs to rotorcraft-hover-performance for a given rotor.
- Closing solidity from a rounded thrust coefficient: the closure runs
  on the module thrust coefficient of the sized rotor (0.006479 into
  0.12 gives 0.053990); round CT to fewer decimals first and the
  division drifts out of the 1e-6 window.
- Forgetting the blade count in the chord: the chord is the total blade
  area spread over b * R, so doubling the blade count halves the chord
  at a fixed solidity and disk.
- Reading the achieved disk loading as below the ceiling: A = T/DL_max
  sizes the disk at the ceiling, so the achieved T / A equals DL_max
  exactly and the CT ceiling identity holds.
- Non-positive thrust, disk loading, rho, radius, tip speed, thrust
  coefficient, design point, solidity, area or speed of sound, and
  blade counts below 1 or fractional raise ValueError; runs are
  deterministic (no RNG).

## Related leaves

- flight-mechanics/performance/rotorcraft-hover-performance: the OGE
  hover power and figure of merit for the main rotor sized here.
- flight-mechanics/performance/rotorcraft-tail-rotor-sizing: the
  identical disk sizing inversion applied to the anti-torque rotor from
  the torque balance.
- flight-mechanics/performance/rotorcraft-forward-flight-performance:
  forward flight power of the sized main rotor.
- flight-mechanics/performance/rotorcraft-vertical-climb-performance:
  climb power states of the sized main rotor.
- flight-mechanics/performance/rotorcraft-turn-performance: the turn
  closure that reuses a given hover rotor at n times the weight.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rotorcraft_main_rotor_sizing.py

The test covers the primary worked example chain (4500 kg at the 350 Pa
ceiling, 0.12 design point, 4 blades, 210 m/s) and the secondary
3000 kg / 300 Pa / 0.10 state against the spec anchors, every function
against its defining equation, the ceiling and radius round trips, the
ceiling identity of the thrust coefficient, the solidity closure round
trip, the blade solidity identity, the tip Mach invariance, the shared
inversion cross-check with the sibling worked anchor, run-to-run
determinism, and ValueError rejection of every non-physical input
class.

## Compliance

- Standards referenced, not reproduced: FAR-29 is a regulatory
  standard; the main rotor sizing relations above are standard
  engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
