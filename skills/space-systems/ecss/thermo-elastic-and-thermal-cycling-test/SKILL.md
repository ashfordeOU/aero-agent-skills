---
name: thermo-elastic-and-thermal-cycling-test
description: "Use when validate a spacecraft structure's thermo-elastic distortion and thermal-cycling test compliance under ECSS E-ST-32 clauses 4.6.3.14–4.6.3.15: check the temperature profile hot and cold soak limits, ramp rate, and soak duration; compute thermal strain and thermo-elastic distortion from the coefficient of thermal expansion and applied temperature delta; compare measured distortion against the design allowable; determine the required number of thermal cycles from design life and qualification factor; confirm the actual cycle count meets the requirement; and aggregate all findings into a PASS or FAIL verdict. Trigger: ecss, e-st-32-structures-scope, thermo-elastic-distortion, thermal-cycling, temperature-profile, coefficient-of-thermal-expansion, structural-test, thermal-strain."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-32-structures-scope, thermo-elastic-distortion, thermal-cycling, temperature-profile, coefficient-of-thermal-expansion, structural-test, thermal-strain]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Thermo-elastic and Thermal-cycling Tests (space-systems/ecss/thermo-elastic-and-thermal-cycling-test)

Use when the task is to validate a spacecraft structure against the thermo-elastic
and thermal-cycling test requirements of ECSS E-ST-32 clauses 4.6.3.14–4.6.3.15:
validate the applied temperature profile, compute thermo-elastic distortion from
the coefficient of thermal expansion and temperature delta, compare the result
against the design allowable, and verify the thermal-cycling campaign satisfies
the required cycle count and soak conditions.

## Domain quick reference

- **Thermo-elastic test (clause 4.6.3.14):** Verifies that dimensional change
  caused by a temperature gradient (thermo-elastic distortion) does not exceed
  the design allowable. The core relation is: distortion = CTE × ΔT × L, where
  CTE is the material coefficient of thermal expansion (1/K), ΔT is the hot
  minus cold temperature delta (K), and L is the characteristic structural
  length (m). The measured or predicted distortion is compared against the
  allowable from the structural or interface control record.
- **Thermal-cycling test (clause 4.6.3.15):** Verifies structural integrity
  through repeated excursions between hot and cold soak conditions. The required
  number of cycles is derived by applying a qualification factor to the design
  life cycle count, with a floor of three cycles regardless of design life.
  Each cycle must include a full temperature soak at both the hot and cold
  extremes — partial cycles do not count toward the tally.
- **Temperature profile parameters:** hot soak limit (T_max, K), cold soak
  limit (T_min, K), ramp rate (K/min), and minimum soak duration (min). The
  profile must satisfy T_min < T_max, a positive ramp rate within the
  material limit, and a soak duration sufficient for thermal equilibration.
- **Test type categorization:** each campaign is categorized as thermo-elastic,
  thermal-cycling, or both before any quantitative check is performed.
  An unrecognized test type is rejected before it enters the assessment.

## Workflow

1. Categorize the test campaign: identify whether the objective is thermo-elastic
   distortion verification, thermal-cycling endurance, or both. Record the
   categorized type before proceeding.
2. Validate the thermal profile: confirm T_min < T_max, that the ramp rate is
   positive and does not exceed the material or joint limit captured in the
   design record, and that the soak duration at each extreme is positive and
   meets the minimum required for thermal equilibration.
3. For a thermo-elastic test: compute thermal strain (CTE × ΔT), then
   thermo-elastic distortion (thermal strain × characteristic structural length).
   Compare the computed distortion against the allowable from the structural or
   interface control record. Flag any exceedance as a finding.
4. For a thermal-cycling test: compute the required cycle count as
   max(3, qualification_factor × design_life_cycles). Confirm the actual
   executed cycle count meets or exceeds the requirement. Flag a shortfall.
5. Confirm soak duration at both hot and cold extremes meets the minimum
   required per the test procedure. Flag any soak shortfall.
6. Verify the ramp rate does not exceed the material or adhesive limit.
   Flag any violation.
7. Aggregate all findings; the test campaign is compliant only when the
   findings list is empty. Record the overall PASS or FAIL verdict.

## Pitfalls

- Counting a cycle that did not reach full hot and cold soak as a complete
  cycle — partial cycles must not enter the cycle tally until both extremes
  have been held for the required soak duration.
- Using the qualification factor only on thermal-cycling life and not on
  on-orbit day/night cycle count when the two are mixed — state the
  convention and apply it consistently in both the requirement and the record.
- Conflating the structural distortion allowable with a dimensional stability
  budget margin from the optical or alignment subsystem — use the allowable
  that is anchored to the structural or ICD requirement, not the tighter
  optical budget unless specifically directed.
- Omitting the CTE contribution of a second material at a dissimilar-material
  joint — relative thermo-elastic distortion at an interface depends on the
  CTE of both joined materials; applying only the stiffer material's CTE
  understates the interface motion.
- Reading a ramp-rate check as optional — joints and adhesives have explicit
  ramp-rate limits; exceeding them during the test invalidates the result
  even if the cycle count and soak conditions are met.

## Behavior contract (gate 3)

The test-type categorization, thermal-profile validation, thermal-strain and
distortion computation, deformation allowable check, required-cycle-count
derivation, cycle-count sufficiency check, soak-duration validation,
ramp-rate check, and result aggregation logic are exercised by the gate 3
contract test: scripts/test_thermo_elastic_and_thermal_cycling_test.py
against scripts/thermo_elastic_and_thermal_cycling_test_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_thermo_elastic_and_thermal_cycling_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
