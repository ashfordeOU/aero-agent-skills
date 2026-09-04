# Wave-37 leaf spec: hydraulic-actuator-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/hydraulic-actuator-sizing/
- Pack: sizing. Closest siblings: hydraulic-system-sizing (system level:
  actuator FLOW from a piston area INPUT, pump flow, accumulator,
  reservoir - it does not size the actuator structure), control-surface-
  sizing (sizes the surface and computes the HINGE MOMENT handed to the
  actuator - does not size the actuator), landing-gear-retraction-sizing
  (computes the gear retraction actuator FORCE and stroke at its own
  mechanism - not a general actuator sizing method), spoiler-sizing and
  others (surface geometry). Whole-tree grep: no leaf computes actuator
  bore diameter, rod diameter, or rod buckling for a hydraulic actuator.
  ZERO owners of the actuator-sizing function. GENUINE VD gap (fresh
  probe; wave-36 VD probe did not cover it).
- Standards id: far-25 (reference-only; flight control actuation
  context, 25.671). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Size a linear hydraulic actuator for an aircraft control or utility
load: convert the required output load and system pressure into the
piston area and bore diameter with the pressure-margin factor and the
mechanical efficiency, check the annulus (rod-side) area for the
retract direction, size the rod diameter from Euler column buckling
over the extended length with the design factor, select the nearest
standard bore and rod diameters from a compact preferred list, and
compute the actuator mass estimate. Produces the bore and rod
diameters, the annulus area, the buckling margin, the preferred-size
selection, and the mass estimate that close the load-to-actuator chain.
Does NOT do: hydraulic system pump/accumulator/reservoir sizing
(hydraulic-system-sizing); control surface geometry and hinge moment
(control-surface-sizing); landing gear retraction mechanism kinematics
(landing-gear-retraction-sizing).

## Model (implement exactly)

Module constants:
- PRESSURE_MARGIN = 1.10 (design margin on the required load)
- MECHANICAL_EFFICIENCY = 0.90 (typical actuator efficiency,
  documented model constant)
- BUCKLING_FACTOR_OF_SAFETY = 2.0, END_FIXITY_K = 1.0 (pinned)
- MODULUS_ROD = 205e9 (Pa, steel rod)
- ROD_DENSITY = 7850.0 (kg/m3), STEEL_YIELD = 1100e6 (Pa, for the
  rod stress check)
- PREFERRED_BORES_MM = (25.0, 32.0, 40.0, 50.0, 63.0, 80.0, 100.0,
  125.0)
- PREFERRED_RODS_MM = (12.0, 16.0, 20.0, 25.0, 32.0, 40.0, 50.0, 63.0)

Functions (pure stdlib):
- piston_area(load_N, pressure_Pa) -> m2 = load_N * PRESSURE_MARGIN /
  (pressure_Pa * MECHANICAL_EFFICIENCY). ValueErrors: load <= 0,
  pressure <= 0.
- bore_diameter(area_m2) -> m = sqrt(4 * area / pi).
- annulus_area(bore_m, rod_m) -> m2 = pi/4 * (bore**2 - rod**2).
- retract_capability(annulus_area_m2, pressure_Pa) -> N =
  annulus_area * pressure_Pa * MECHANICAL_EFFICIENCY / PRESSURE_MARGIN.
- rod_buckling_diameter(load_N, rod_length_m) -> m: Euler required
  inertia I = load_N * BUCKLING_FACTOR_OF_SAFETY * (END_FIXITY_K *
  rod_length_m)**2 / (pi**2 * MODULUS_ROD); D = (64 * I / pi) ** 0.25.
  ValueErrors: load <= 0, length <= 0.
- select_preferred(value_m, preferred_mm) -> float mm: nearest
  preferred diameter at or above the value.
- actuator_mass(bore_m, rod_m, stroke_m) -> kg: rod volume
  pi/4*rod_m**2*stroke_m plus barrel volume pi/4*(bore_m**2 -
  rod_m**2)*stroke_m * 0.6 (documented fill factor), times ROD_DENSITY.
- actuator_review(load_N, pressure_Pa, rod_length_m, stroke_m) -> dict
  {piston_area, bore_mm, annulus_area, rod_buckling_mm, bore_pref_mm,
  rod_pref_mm, retract_capability_N, rod_stress_Pa,
  buckling_margin, mass_kg, verdict: "pass" if retract capability >=
  load and rod_stress <= STEEL_YIELD else "fail"}.
  rod_stress = load / (pi/4 * rod_pref**2).

Identity to test: bore diameter from area is exact inverse of the circle
formula; doubling the rod length raises required rod diameter (Euler);
retract capability scales with the annulus area.

## Worked example

Load 40000 N, system pressure 207 bar (20.7e6 Pa), rod length 0.35 m,
stroke 0.20 m. Run your module and take the real outputs as assert
targets; bounds independently verified at prep:
- piston_area = 40000*1.1/(20.7e6*0.9) = 2.361e-3 m2 (23.6 cm2); bore =
  54.8 mm -> preferred 63 mm.
- rod_buckling_diameter = 17.7 mm (Euler, FOS 2) -> preferred 20 mm.
- With bore 63 mm, rod 20 mm: annulus area = pi/4*(0.063**2-0.02**2)
  = 2.807e-3 m2; retract capability = 2.807e-3*20.7e6*0.9/1.1 =
  47530 N >= 40000 -> pass.
- rod stress = 40000/(pi/4*0.02**2) = 127.3 MPa < 1100 MPa.
- mass = 3.13 kg by the model formula (rod 0.49 kg + 0.6-fill annulus
  2.64 kg) within 10%.

## Validation list (contract test must include)

- ValueError: load <= 0, pressure <= 0, length <= 0, stroke <= 0.
- Piston area and bore anchors (2.361e-3 m2, 54.8 mm) within tolerance;
  rod buckling 17.7 mm within 1 mm.
- Preferred selection: at-or-above nearest (54.8 -> 63; 17.7 -> 20).
- Retract-direction capability check passes at the anchor and fails
  when the rod is oversized (annulus too small) for the load.
- Identity: bore from area round-trips; Euler length scaling increases
  diameter.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave37-hydraulic-actuator-sizing.yaml)

Query 1 (copy verbatim):
  "size the hydraulic-actuator-sizing bore and piston area from the actuator load and system pressure with the margin"
  intent: "vehicle-design; hydraulic actuator bore sizing"
  expected_skill: "vehicle-design/sizing/hydraulic-actuator-sizing"
Query 2 (copy verbatim):
  "check the hydraulic-actuator-sizing rod buckling diameter and retract capability for the extended actuator"
  intent: "vehicle-design; actuator rod buckling and retract check"
  expected_skill: "vehicle-design/sizing/hydraulic-actuator-sizing"
Task ids: w37-hydraulic-actuator-sizing-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size a hydraulic actuator:" and
include the outputs in the Claim. First tag: hydraulic-actuator-sizing.
Additional tags ONLY: actuator-bore-diameter, actuator-rod-buckling,
annulus-retract-check, preferred-actuator-sizes, actuator-mass-estimate.
NEVER single generic words (actuator, hydraulic, bore, rod, load,
pressure). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): pump flow, accumulator,
reservoir (hydraulic-system-sizing); hinge moment, control surface area
(control-surface-sizing); retraction actuator force, four-bar linkage
(landing-gear-retraction-sizing).
