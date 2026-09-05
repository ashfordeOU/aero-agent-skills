---
name: magnetic-particle-inspection
description: "Use when a task names magnetic particle testing on steel parts, magnetization current selection, field strength, particle sensitivity, magnetic indication, or residual field. Determine magnetic particle inspection (MT) parameters for ferromagnetic aerospace parts and turn particle indications into acceptance decisions: compute the magnetizing current for circular magnetization by head shot or central conductor, size the ampere-turns and coil current for longitudinal magnetization from the part L/D ratio, verify the tangential field strength against the 2400 to 4800 A/m band and the coverage overlap between shots, classify magnetic particles by median size and sensitivity, check the wet bath concentration, and disposition relevant and non-relevant indications with the residual field demagnetization check. Trigger: magnetic particle, magnetization current, circular magnetization, longitudinal magnetization, field strength, particle sensitivity, magnetic indication, residual field."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
  - id: nas-410
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: ndt
  tags: [magnetic-particle-inspection, magnetization-current, circular-magnetization, longitudinal-magnetization, field-strength, coverage-overlap, ampere-turns, encircling-coil, ld-ratio, head-shot, central-conductor, particle-sensitivity, particle-size-class, bath-concentration, magnetic-indication, acceptance-verdict, residual-field, demagnetization]
  version: 0.1.0
  author: Aero Agent Skills
---

# Magnetic Particle Inspection (manufacturing-quality/ndt/magnetic-particle-inspection)

Use when the task is executing magnetic particle inspection (MT) on a
ferromagnetic part: selecting the magnetizing current for circular and
longitudinal magnetization, verifying the field strength and coverage
overlap, classifying the magnetic particles by sensitivity, and turning
the observed indications into acceptance decisions.

## Domain quick reference

All numbers below were computed and verified by running the logic
module in scripts/.

- Head shot current (circular magnetization): I = amperes_per_inch * D,
  with D the part diameter in inches. Common practice is 300 to 800 A
  per inch of diameter. A 2.0 in shaft needs 1600 A at 800 A/in and
  600 A at 300 A/in.
- Central conductor current: the same current-per-inch rule applies to
  the conductor diameter, because the bore field is set by the
  conductor radius. A 1.0 in conductor at 800 A/in carries 800 A and
  magnetizes the bore of any part OD it threads.
- Effective diameter of a hollow part: D_eff = sqrt(OD^2 - ID^2). A
  2.0 in OD, 1.0 in ID sleeve behaves as a 1.732 in solid bar for L/D.
- Effective L/D: L/D = length / D_eff. An 8.0 in long sleeve has
  L/D = 4.62. Coil magnetization requires 2 <= L/D < 15; below 2, add
  pole pieces or stack parts; at or above 15, only the central portion
  is magnetized, so magnetize in sections or use another technique.
- Low fill factor coil: NI = 45000 / (L/D). At L/D = 4.62 the coil
  needs 9743 ampere-turns, and a 250 turn coil runs at 39 A
  (9743 / 250 = 38.97 A). At L/D = 4 the coil needs 11250 ampere-turns.
- High fill factor coil: NI = 35000 / (L/D + 2). At L/D = 4 the coil
  needs 5833 ampere-turns, far fewer than the low fill value of 11250,
  because the flux path is shorter when the part fills the coil.
- Field strength: H = NI / L for a long solenoid, in A/m. 1000
  ampere-turns over a 0.25 m coil gives 4000 A/m, inside the wet
  fluorescent band of 2400 to 4800 A/m (30 to 60 oersted). The wet
  visible band is 2400 to 3200 A/m. Verdicts: 2000 A/m is low, 4000
  A/m is adequate for fluorescent, 5000 A/m is high for fluorescent,
  and 4000 A/m is high for visible.
- Coverage: step = width * (1 - overlap), with 10 to 15 percent
  overlap common between adjacent shots. A 0.2 m magnetization zone at
  15 percent overlap advances 0.17 m per pass, so a 0.5 m shaft needs
  3 passes to cover its length.
- Particle classification: median diameter classes are extra-fine
  below 10 um, fine 10 to 20 um, medium 20 to 35 um, and coarse 35 um
  and above. Sensitivity follows size: high below 20 um, standard 20
  to 35 um, low 35 um and above. An 8 um particle is extra-fine with
  high sensitivity; a 45 um particle is coarse with low sensitivity.
- Bath concentration: wet fluorescent 0.1 to 0.4 mL of concentrate per
  100 mL of carrier, wet visible 1 to 2 mL per 100 mL. A 0.2 mL/100 mL
  fluorescent bath is within range; 1.5 mL/100 mL is within range only
  for the visible method.
- Indication class: linear when length / width >= 3. A 6.0 mm by
  1.5 mm indication has ratio 4.0 and is linear; a 4.0 mm by 2.0 mm
  indication is not.
- Acceptance: a relevant 4.0 mm indication against a 3.0 mm limit is
  rejected, a 2.0 mm indication is accepted, and a non-relevant
  indication is evaluated, never auto-rejected.
- Residual field: demagnetize when the residual field exceeds the
  limit, commonly 3 A/m. A 5 A/m residual fails the check, 2 A/m
  passes.
- Defect to direction: a longitudinal (axial) defect is detected by
  circular magnetization; a transverse (circumferential) defect by
  longitudinal magnetization. Production parts are magnetized in both
  directions, 90 degrees apart, so every defect orientation is cut by
  a field.

## Workflow

1. Confirm the part is ferromagnetic and name the defect class: a
   longitudinal (axial) defect needs circular magnetization, a
   transverse defect needs longitudinal magnetization.
2. For circular magnetization by head shot, compute the current with
   head_shot_current (300 to 800 A per inch of diameter typical). For
   a bore, use central_conductor_current on the conductor diameter.
3. For longitudinal magnetization by encircling coil, compute the
   effective diameter with effective_diameter_hollow (hollow parts),
   the L/D with effective_ld_ratio, the ampere-turns with
   coil_ampere_turns_low_fill or coil_ampere_turns_high_fill by fill
   factor, then the coil current with coil_current_from_turns.
4. Verify the field with solenoid_field_strength and
   tangential_field_verdict against the fluorescent band of 2400 to
   4800 A/m (or 2400 to 3200 A/m visible), and plan the coverage with
   coverage_step at 10 to 15 percent overlap.
5. Classify the particle with particle_size_class and
   particle_sensitivity from the median particle size, and check the
   bath with bath_concentration_check.
6. Interpret the indications: classify linear versus rounded with
   indication_linear_ratio and indication_is_linear, mark each
   indication relevant or non-relevant, and disposition with
   acceptance_verdict against the engineering acceptance limit.
7. After testing, check the residual field with
   residual_field_verdict and demagnetize when required. Record the
   results under NAS 410 qualified personnel and the qualified
   procedure.

## Pitfalls

- Confusing the two magnetization directions: a longitudinal (axial)
  defect is detected by circular magnetization, whose field circles
  the part; the encircling coil produces an axial field that detects
  transverse defects. Magnetizing in only one direction leaves every
  defect of the other orientation undetected.
- Using the part OD instead of the conductor diameter for central
  conductor magnetization: the bore field is set by the conductor
  radius, so the current-per-inch rule applies to the conductor, not
  to the part.
- Ignoring the L/D limits of coil magnetization: below L/D 2 the coil
  field is too weak and pole pieces or stacked parts are required, and
  at or above L/D 15 only the central portion is magnetized; the
  ampere-turns functions raise ValueError outside the band.
- Confusing MPI with liquid-penetrant-inspection: penetrant finds
  surface-breaking discontinuities in any material through capillary
  action and dwell time, while MPI finds surface and near-surface
  discontinuities in ferromagnetic materials only, driven by
  magnetization current and field, with no dwell time and no bleed-out
  sizing.
- Confusing MPI with eddy-current-inspection: eddy current works on
  any conductor, senses subsurface flaws through depth of penetration
  and the impedance plane, and needs no magnetizing current and no
  particle bath; MPI requires ferromagnetic material and produces
  visible particle indications.
- Treating a non-relevant indication as a reject: indications from
  threads, sharp section changes, or magnetic writing are recorded and
  evaluated; acceptance_verdict returns 'evaluate' for them, never
  'reject' or 'accept' on length alone.
- Over-magnetizing: a field above the band collects particles into
  false background indications; tangential_field_verdict flags 'high'
  and the magnetizing current must be reduced before judging
  indications.
- Forgetting the residual field check: a part that still attracts
  chips or debris after testing must be demagnetized and re-checked;
  residual_field_verdict returns 'demagnetize' above the limit.

## Behavior contract (gate 3)

The inspection math is exercised by the gate 3 contract test:
scripts/test_magnetic_particle_inspection.py against
scripts/magnetic_particle_inspection_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_magnetic_particle_inspection.py

## Compliance

- Standards referenced, not reproduced: AS9100 clause 8.5.1.3 frames
  NDT as a special process requiring controlled procedures and
  qualified personnel, and NAS 410 sets the qualification and
  certification requirements for the NDT personnel who execute
  magnetic particle inspection; the current-per-inch, ampere-turns,
  field band, coverage, and acceptance calculations above are common
  MT methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
