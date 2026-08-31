# AeroSkills 50×20 Domain Tree (founder release bar 2026-08-31)

Founder: "Not good enough for release until there are at least 20 skills
per domain and verified and tested and reliable. And 50+ domains each ready."

**Release gate: 50+ domains × 20+ verified skills = 1,000+ skills, all
make-validate green.**

This tree decomposes the 12 aerospace disciplines into **68 sub-domains**
(→ 1,360 skills at 20 each). Each sub-domain is an installable pack.

| Discipline | Sub-domains (packs) | Skills @20 |
|---|---|---|
| Aerodynamics | airfoil · cfd · high-speed · aeroelasticity · wind-tunnel · drag-polars | 120 |
| Propulsion | gas-turbine-cycle · turbomachinery · combustion · rocket · electric-propulsion · engine-airframe | 120 |
| Structures | fem · composites · fatigue · damage-tolerance · materials · thermal-structures | 120 |
| Flight mechanics | performance · stability-control · handling-qualities · flight-dynamics-sim | 80 |
| GNC / autonomy | control-design · estimation-filtering · trajectory-opt · guidance · navigation · autopilots | 120 |
| Avionics | do178c · do254 · do160 · data-bus · ima · displays · flight-management | 140 |
| Systems engineering | requirements · mbse · safety-assessment · certification · config-mgmt | 100 |
| Space systems | orbit-mechanics · mission-design · subsystems · adcs · propulsion · launch-reentry · ground-systems | 140 |
| Vehicle design | conceptual · sizing · mdo · mass-properties · cost-estimation | 100 |
| Manufacturing & quality | qms · fai · special-processes · supply-chain · additive | 100 |
| Flight test | envelope · performance-test · stability-test · instrumentation · telemetry | 100 |
| Cross-cutting | units-atmos · numerics · data-sources · documentation · compliance · project-mgmt | 120 |
| **Total** | **68 packs** | **1,360** |

## Build order (pipeline)

1. **Wave 4 (next):** fill each existing pack to 20 (avionics, space-systems,
   systems-engineering-safety, aerodynamics, gnc-autonomy, structures,
   vehicle-design, manufacturing-quality, cross-cutting) — the 9 packs grow
   from 27 → ~180.
2. **Wave 5:** new disciplines (propulsion, flight-mechanics, flight-test)
   with first packs.
3. **Waves 6+:** remaining sub-domains, using the same standards-map →
   build → eval-gate → verify pipeline; WikiSkill loop accelerates via
   usage data once any public distribution exists.

## Verification bar (every skill)

- make validate 5/5 (spec lint · desc lint · pytest contract · no-verbatim · Hit@1)
- make attest 3/3
- Per-skill behavior contract test
- Reliability: gate 3 contract tests all pass, deterministic offline router

## Status tracking

Tracked in the Veda project registry (`knowledge/_PROJECTS.md`,
`_ASSIGNMENTS.md`). CEO audits the 50×20 bar at ≥9.5 before any release.
