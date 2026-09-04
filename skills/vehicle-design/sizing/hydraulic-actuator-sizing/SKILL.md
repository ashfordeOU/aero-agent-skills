---
name: hydraulic-actuator-sizing
description: "Use when you must size a hydraulic actuator: the piston area and bore diameter from the actuator load and system pressure with the pressure-margin factor and mechanical efficiency, the rod-side annulus area and retract capability, the rod diameter from Euler column buckling over the extended rod length with the design factor, the nearest preferred bore and rod diameters at or above the requirements, and the actuator mass estimate. Produces the bore and rod diameters, the annulus area, the buckling margin, the preferred-size selection and the mass estimate that close the load-to-actuator chain. Trigger: hydraulic actuator sizing, actuator bore diameter, actuator rod buckling, annulus retract check, preferred actuator sizes, actuator mass estimate."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: vehicle-design
pack: sizing
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [hydraulic-actuator-sizing, actuator-bore-diameter, actuator-rod-buckling, annulus-retract-check, preferred-actuator-sizes, actuator-mass-estimate]
  version: 0.1.0
  author: AeroSkills
---

# Hydraulic Actuator Sizing (vehicle-design/sizing/hydraulic-actuator-sizing)

Use when you must size a linear hydraulic actuator for an aircraft
control or utility load: converting the required output load and the
system pressure into the piston area and bore diameter with the
pressure-margin factor and the mechanical efficiency, checking the
rod-side annulus area for the retract direction, sizing the rod
diameter from Euler column buckling over the extended rod length with
the design factor, selecting the nearest preferred bore and rod
diameters at or above the requirements, and estimating the actuator
mass. This leaf implements the load-to-actuator chain in pure Python,
stdlib only. It pairs with vehicle-design/sizing/hydraulic-system-
sizing, which takes the piston area this leaf produces as the input
for its system-level flow demand side; the actuator load that closes
the surface side comes from vehicle-design/sizing/control-surface-
sizing, and the specific gear mechanism force and stroke belong to
vehicle-design/sizing/landing-gear-retraction-sizing. This leaf sizes
the actuator structure itself, which no other leaf owns.

## Domain quick reference

- Required piston area (extend direction): A = F_req * PRESSURE_MARGIN
  / (p * MECHANICAL_EFFICIENCY), with PRESSURE_MARGIN = 1.10 covering
  seal friction and dynamic effects on the required load and
  MECHANICAL_EFFICIENCY = 0.90 converting hydraulic to mechanical
  power, so the sizing runs on F_req * 1.1 / (p * 0.9).
- Bore diameter: D_b = sqrt(4 * A / pi), the circle formula applied
  to the required piston area.
- Annulus area: A_ann = pi/4 * (D_b^2 - D_r^2), the rod-side piston
  area that remains for the retract direction after the rod occupies
  the center of the bore.
- Retract capability: F_ret = A_ann * p * MECHANICAL_EFFICIENCY /
  PRESSURE_MARGIN. The margin load is divided back out, so F_ret
  compares directly with the required load; the actuator passes only
  when F_ret >= F_req.
- Rod column sizing (Euler): I_req = F_req * BUCKLING_FACTOR_OF_SAFETY
  * (END_FIXITY_K * L_rod)^2 / (pi^2 * MODULUS_ROD) with the factor of
  safety 2.0, pinned ends K = 1.0 and the steel modulus 205 GPa, over
  the extended rod length L_rod (the rod is a column at full
  extension); solid rod diameter D_r = (64 * I_req / pi)^0.25.
- Rod stress and margin: sigma = F_req / (pi/4 * D_r^2) must stay
  below STEEL_YIELD = 1100 MPa; the Euler critical load on the actual
  rod P_cr = pi^2 * E * I / (K * L_rod)^2 gives the buckling margin
  P_cr / F_req, which the sizing factor holds at or above 2.0.
- Preferred sizes: PREFERRED_BORES_MM = (25, 32, 40, 50, 63, 80, 100,
  125) mm and PREFERRED_RODS_MM = (12, 16, 20, 25, 32, 40, 50, 63) mm;
  select_preferred returns the first preferred size at or above the
  requirement so the selection never under-sizes.
- Mass estimate: m = ROD_DENSITY * [pi/4 * D_r^2 * L_s + 0.6 * pi/4 *
  (D_b^2 - D_r^2) * L_s] with ROD_DENSITY = 7850 kg/m3, the stroke
  L_s, and the documented 0.6 fill factor on the barrel annulus
  volume for the barrel wall, seals, gland and fittings.
- Units are SI throughout: N, Pa, m, m2, kg.
- FAR Part 25 (25.671 flight control actuation context) frames the
  certification setting; the relations above are standard engineering
  methodology, summary-only.

## Workflow

1. Fix the design point: the required actuator output load F_req (N),
   the system pressure p (Pa), the extended rod length L_rod (m) and
   the stroke L_s (m).
2. Convert the load into the required piston area with piston_area,
   which applies the 1.10 pressure margin and the 0.90 mechanical
   efficiency, then read the ideal bore with bore_diameter.
3. Select the production bore with select_preferred against
   PREFERRED_BORES_MM (at or above the ideal value).
4. Size the rod as a column with rod_buckling_diameter over the
   extended length at the factor of safety 2.0, then select the
   preferred rod with select_preferred against PREFERRED_RODS_MM.
5. Form the rod-side annulus with annulus_area(bore_pref, rod_pref)
   and check the retract direction with retract_capability: the
   annulus force at the system pressure must meet the required load.
6. Close the chain with actuator_review, which returns the piston
   area, ideal and preferred diameters, annulus area, retract
   capability, rod stress, buckling margin, mass and the pass/fail
   verdict in one dict; the annulus, stress, margin and mass use the
   preferred bore and rod, as in the worked example.
7. Confirm the deterministic checks with the contract test
   scripts/test_hydraulic_actuator_sizing.py.

## Worked example

Aileron or flap actuator: F_req = 40000 N, system pressure 207 bar
(20.7e6 Pa), extended rod length 0.35 m, stroke 0.20 m.

- Piston area: piston_area(40000, 20.7e6) = 40000 * 1.1 / (20.7e6 *
  0.9) = 2.3618e-3 m2 (23.6 cm2), matching the spec anchor 2.361e-3.
- Bore: bore_diameter gives 54.84 mm (spec anchor 54.8 mm);
  select_preferred picks 63 mm from the bore list.
- Rod buckling: rod_buckling_diameter(40000, 0.35) = 17.72 mm (spec
  anchor 17.7 mm within 1 mm); select_preferred picks 20 mm.
- Annulus: annulus_area(0.063, 0.020) = pi/4 * (0.063^2 - 0.02^2) =
  2.8031e-3 m2, within 1% of the spec anchor 2.807e-3.
- Retract capability: retract_capability(2.8031e-3, 20.7e6) = 47474 N
  (spec anchor 47530 N within 1%), above the 40000 N load, so the
  retract direction passes.
- Rod stress: 40000 / (pi/4 * 0.02^2) = 127.3 MPa, well below the
  1100 MPa rod yield.
- Buckling margin on the preferred 20 mm rod: P_cr = 129.7 kN over
  0.35 m, margin 3.24 against the factor of safety 2.0.
- Mass: actuator_mass(0.063, 0.020, 0.20) = 3.13 kg (rod 0.49 kg plus
  the 0.6-fill barrel annulus 2.64 kg), within 10% of the spec anchor.
- Review: actuator_review returns piston_area 2.3618e-3 m2, bore_mm
  54.84, annulus_area 2.8031e-3 m2, rod_buckling_mm 17.72,
  bore_pref_mm 63.0, rod_pref_mm 20.0, retract_capability_N 47474,
  rod_stress_Pa 1.2732e8, buckling_margin 3.24, mass_kg 3.13 and
  verdict "pass".
- Counter-example: the same method at 30000 N over a 0.20 m rod picks
  a 50 mm bore with a 16 mm rod whose annulus gives only 29849 N of
  retract force, below the load, so the verdict is "fail"; the annulus
  must be rebalanced or the design point revisited.

## Verification

- Confirm piston_area(40000, 20.7e6) returns 2.3618e-3 m2 and that
  bore_diameter of that area returns 54.84 mm (anchors 2.361e-3 m2
  and 54.8 mm within tolerance).
- Confirm rod_buckling_diameter(40000, 0.35) returns 17.72 mm within
  1 mm of the 17.7 mm anchor, and that doubling the rod length
  multiplies the required rod diameter by sqrt(2) (Euler length
  scaling identity) while doubling the load multiplies it by 2^0.25.
- Confirm select_preferred routes 54.84 mm to 63 mm and 17.72 mm to
  20 mm (first preferred size at or above the requirement) and keeps
  an exact 63 mm requirement on 63 mm.
- Confirm retract_capability on the anchor annulus returns 47474 N,
  above the 40000 N load, and that it scales linearly with the
  annulus area.
- Confirm actuator_review on the worked example returns verdict "pass"
  with mass 3.13 kg (spec anchor within 10%) and that the 30000 N /
  0.20 m case returns "fail" because the retract capability cannot
  cover the load.
- Confirm every non-positive load, pressure, length, stroke and area,
  every rod at or above its bore, and every requirement beyond the
  largest preferred size raises ValueError.
- Confirm the review dict keys are exactly the documented set and that
  repeated calls are deterministic.
- Run the contract test offline: python3
  scripts/test_hydraulic_actuator_sizing.py (35 tests,
  deterministic).

## Related leaves

- vehicle-design/sizing/hydraulic-system-sizing: the system-level
  partner that takes the piston area this leaf produces as the input
  for its flow demand side.
- vehicle-design/sizing/control-surface-sizing: computes the surface
  geometry and the actuator load that closes the surface side of the
  chain.
- vehicle-design/sizing/landing-gear-retraction-sizing: the gear
  mechanism force and stroke at its own linkage, a specific
  application rather than a general actuator sizing method.
- vehicle-design/sizing/spoiler-sizing: another surface that loads an
  actuator through its hinge line.

## Pitfalls

- Sizing the bore on the raw load without the margin and efficiency:
  the piston area runs on F_req * 1.1 / (p * 0.9), so omitting either
  factor under-sizes the bore (2.3618e-3 m2 against 1.932e-3 m2 on
  the raw load in the worked example).
- Forgetting the retract direction: the rod occupies the center of the
  bore, so the annulus area, not the bore area, drives retraction;
  a heavily loaded actuator at the top of a size envelope can push
  more than it can pull back, and the review verdict exists to catch
  exactly that (29849 N of retract against a 30000 N load in the
  counter-example).
- Checking the rod only in compression stress: the rod is a column at
  full extension, so the Euler check over the extended length with
  the factor of safety 2.0 governs the diameter (17.72 mm), not the
  stress which passes at any reasonable size (127.3 MPa at 20 mm).
- Treating the ideal diameter as the production size: the selection
  steps to the first preferred size at or above the requirement
  (54.84 to 63 mm, 17.72 to 20 mm), and the annulus, stress, margin
  and mass all follow from the preferred pair.
- Sizing the mass on the full barrel volume: the documented 0.6 fill
  factor on the barrel annulus volume accounts for the wall, seals,
  gland and fittings, so the raw annulus volume overstates the mass
  by 40% before density is applied.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_hydraulic_actuator_sizing.py

The test covers the worked-example contract (piston area 2.3618e-3 m2
and bore 54.84 mm within tolerance, rod buckling 17.72 mm within 1 mm,
preferred selections 63 mm and 20 mm, annulus 2.8031e-3 m2 within 1%,
retract capability 47474 N within 1% of 47530 N and above the load,
rod stress 127.3 MPa below the 1100 MPa yield, mass 3.13 kg within
10%, verdict pass), the linearity of piston area and retract
capability, the circle-formula inverse and Euler length and load
scaling identities, the at-or-above preferred selection rule and its
bounds, the annulus-too-small review failure at 30000 N, determinism
of the review dict, exact dict keys, and ValueError rejection of
non-positive load, pressure, length, stroke and area, rod at or above
the bore, and requirements beyond the largest preferred size.

## Compliance

- Standards referenced, not reproduced: far-25 (14 CFR Part 25, the
  flight control actuation context of 25.671 in which the sized
  actuator operates); the sizing relations above are standard
  engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
