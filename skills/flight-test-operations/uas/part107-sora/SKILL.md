---
name: part107-sora
description: "Use when assessing the operational risk of a small UAS (drone) operation: check FAA Part 107 applicability (weight under 55 lb, visual line of sight, daylight, below 400 ft AGL, airspace class, remote pilot certificate), classify the operation under EASA SORA into open, specific or certified from kinetic energy and population density, compute the ground risk class (GRC), the air risk class (ARC) from airspace type, apply SORA robustness levels and containment, evaluate BVLOS waiver considerations, and produce an operational safety case summary. Trigger: part 107 applicability, part107 sora, sora operational category, ground risk class, air risk class, arc, grc, robustness level, containment, bvlos waiver, drone risk assessment, uas risk, remote pilot certificate, 400 ft agl, visual line of sight."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-107
    reference-only: true
gated: false
domain: flight-test-operations
pack: uas
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: uas
  tags: [uas, part-107, part107, sora, ground-risk-class, air-risk-class, bvlos, drone-ops, kinetic-energy, population-density, robustness, containment, waiver, remote-pilot-certificate, visual-line-of-sight, airspace, grc, arc, open, specific, certified, safety-case, drone, risk-assessment, applicability]
  version: 0.1.0
  author: Aero Agent Skills
---

# Part 107 and SORA UAS Risk Assessment (flight-test-operations/uas/part107-sora)

Use when a small UAS (drone) operation must be screened for FAA 14 CFR
Part 107 applicability and categorized for risk under the EASA SORA
(Specific Operations Risk Assessment) methodology, ending in an
operational safety case summary. The logic module
scripts/part107_sora_logic.py implements the checks; the contract test
scripts/test_part107_sora.py pins the correct answers. See
references/part107-sora-refs.md for the regulatory background and the
simplifications made.

## Domain quick reference

### Part 107 applicability (FAA 14 CFR Part 107, small UAS rule)

| Check | Limit | Basis |
|---|---|---|
| Takeoff weight | <= 55 lb (25 kg) | 107.3 definition of small UAS |
| Visual line of sight | VLOS maintained by pilot or observer | 107.31 |
| Time of day | Daylight or civil twilight (unless night rule met) | 107.29 |
| Altitude | <= 400 ft AGL (higher near structures under conditions) | 107.51 |
| Airspace | Class G uncontrolled free; B/C/D/E need authorization (LAANC or waiver) | 107.41 |
| Pilot | Remote pilot certificate (or direct supervision by one) | 107.12, 107.64 |

All checks must pass for the operation to be flown under Part 107. Any
failed check lists the waiver or approval needed in waivers_required.
Operations over 55 lb are outside Part 107 entirely (different
certification path).

### SORA operational categories from kinetic energy and population density

Kinetic energy: KE = 0.5 * mass_kg * speed_mps^2 (characteristic cruise
speed, default 20 m/s). Ground risk class (GRC) comes from the intrinsic
GRC table below. Category mapping (simplified, per
sora_operational_category):

| Condition | Category |
|---|---|
| GRC <= 3 and mass <= 25 kg | open |
| GRC 4-6 | specific (SORA + operational authorization / PDRA) |
| mass > 25 kg or GRC >= 7 | certified (type certification territory) |

### Intrinsic GRC table (JARUS SORA 2.0 style, simplified)

Rows: kinetic energy in joules. Columns: population density in people
per square km. Value: intrinsic GRC (1-9).

| KE (J) | < 1 | 1-25 | 25-100 | 100-250 | > 250 |
|---|---|---|---|---|---|
| < 7 | 1 | 1 | 1 | 1 | 1 |
| 7-34 | 1 | 2 | 3 | 4 | 5 |
| 34-108 | 2 | 3 | 4 | 5 | 6 |
| 108-700 | 3 | 4 | 5 | 6 | 7 |
| 700-2400 | 4 | 5 | 6 | 7 | 8 |
| > 2400 | 5 | 6 | 7 | 8 | 9 |

### Air risk class (ARC) from airspace type

| Airspace | ARC |
|---|---|
| Class B (busiest controlled) | d |
| Class C, D | c |
| Class E | b |
| Class G (uncontrolled, <= 400 ft AGL) | a |

Operating above 400 ft AGL escalates the ARC one level (manned traffic
density grows with altitude).

### SORA robustness levels and containment

Robustness of mitigations: none, low, medium, high. GRC reduction credit
is 0, 1, 2, 3 respectively; final GRC is floored at 1. Claiming any
mitigation credit requires operational containment (geofencing plus
contingency procedures); that is what makes the reduction credible.
High robustness means containment with automatic activation and
fail-safe behavior.

### BVLOS waiver considerations

BVLOS (beyond visual line of sight) is not permitted under vanilla Part
107. The operator needs a 14 CFR 107.31 waiver or FAA BVLOS rule
approval (verify current FAA guidance), plus: observer or approved
detect-and-avoid capability, remote ID compliance (14 CFR 89), airspace
authorization for the whole BVLOS volume, lost link and contingency
procedures, route weather and visibility minima, airframe reliability
evidence, and crew training.

## Workflow

1. Screen with part107_applicable(weight_lb, vlos, daylight,
   altitude_agl_ft, airspace_class, remote_pilot_cert,
   airspace_authorization). All checks must pass for Part 107 flight.
2. Estimate mass in kg (55 lb = 25 kg) and characteristic speed; call
   kinetic_energy(mass_kg, speed_mps) for KE.
3. Call ground_risk_class(ke_j, population_density) for the intrinsic
   GRC from the table.
4. Call sora_operational_category(mass_kg, population_density,
   speed_mps) to get the EASA category (open, specific, certified).
5. Call arc_from_airspace(airspace_type, altitude_agl_ft) for the ARC.
6. Choose the robustness of planned mitigations and call
   robustness_level(grc, mitigation) for the final GRC and the
   containment requirement.
7. If BVLOS is planned, call bvlos_waiver_considerations(vlos=False)
   and carry the considerations into the safety case.
8. Call ops_summary(...) to assemble the operational safety case
   summary block.

## Worked example

2 kg (4.4 lb) multirotor, 20 m/s, over sparsely populated farmland
(density 0.5 people/km2), Class G, 200 ft AGL, VLOS, daylight, remote
pilot certificate held.

- part107_applicable(4.4) -> applicable True, no waivers.
- KE = 0.5 * 2 * 20^2 = 400 J.
- ground_risk_class(400, 0.5) -> GRC 3 (row 108-700 J, column < 1).
- sora_operational_category(2.0, 0.5) -> category open, GRC 3.
- arc_from_airspace("g", 200) -> ARC-a.
- robustness_level(3, "none") -> final GRC 3, no containment required.
- ops_summary -> summary shows APPLICABLE, OPEN, GRC 3, ARC-a.

25 kg UAS, 20 m/s, over a dense city (500 people/km2), Class C.

- KE = 0.5 * 25 * 20^2 = 5000 J.
- ground_risk_class(5000, 500) -> GRC 9 (row > 2400 J, column > 250).
- sora_operational_category(25.0, 500.0) -> category certified, GRC 9
  (the 25 kg mass sits exactly on the open ceiling and the GRC forces
  the specific/certified boundary upward).
- arc_from_airspace("c") -> ARC-c.
- robustness_level(9, "high") -> final GRC 6, containment required.
- The operation needs Part 107.41 authorization (LAANC or waiver) and,
  realistically, a certified aircraft path.

## Pitfalls

- Screening an over-55-lb aircraft with the Part 107 applicability
  check: those operations are outside Part 107 entirely and take a
  different certification path; within the rule, any failed check lists
  the waiver or approval needed in waivers_required.
- Computing kinetic energy on the wrong basis: KE = 0.5 * mass_kg *
  speed_mps^2 uses the characteristic cruise speed (default 20 m/s),
  and the 25 kg ceiling equals 55 lb.
- Reading the GRC from the kinetic energy alone: the intrinsic GRC
  table is kinetic energy by population density, so 5000 J over a
  dense city reads GRC 9 while the same energy over < 1 person/km2
  reads GRC 5.
- Assuming mitigation credit is free: robustness credit (0/1/2/3 for
  none/low/medium/high) requires operational containment (geofencing
  plus contingency procedures), high robustness means automatic
  activation with fail-safe behavior, and the final GRC floors at 1.
- Flying BVLOS under vanilla Part 107: it is not permitted; BVLOS needs
  a 14 CFR 107.31 waiver or FAA BVLOS rule approval plus the
  observer/DAA, remote ID, airspace authorization, lost-link, and
  crew-training considerations.
- Treating 25 kg as safely inside the open category: the mass sits
  exactly on the open ceiling, so the GRC decides - 5000 J over a city
  lands certified with GRC 9, not open.

## Behavior contract (gate 3)

The behavior contract is scripts/test_part107_sora.py against
scripts/part107_sora_logic.py (stdlib unittest, offline, deterministic).
Run:

python3 scripts/test_part107_sora.py

It asserts: 2 kg over sparse population -> open category with low GRC 3;
25 kg over a city -> specific/certified boundary with high GRC 9;
weight over 55 lb fails Part 107 applicability; GRC table spot values;
ARC mapping and altitude escalation; robustness reductions and the
containment requirement; BVLOS waiver flag; and every invalid input
raises ValueError.

## References

- references/part107-sora-refs.md: 14 CFR Part 107 section map, EASA
  Regulation 2019/947 and SORA 2.0 background, simplification notes.
- scripts/part107_sora_logic.py: the logic module (pure Python, stdlib
  only).
- scripts/test_part107_sora.py: the behavior contract test.

## Related skills

- flight-test-operations/planning/flight-test-safety: flight test
  safety planning for manned aircraft; pairs with the UAS risk screen
  when a UAS supports flight test instrumentation.
- flight-test-operations/planning/flight-test-planning: overall test
  planning context into which the UAS safety case feeds.

## Compliance

- 14 CFR Part 107 is US government work (public domain); summarized
  with citations only, per standards-map.yaml policy.
- EASA SORA and Regulation 2019/947 referenced as guidance; paraphrased
  summary only in references/part107-sora-refs.md.
- compliance: STANDARDS-REF, gated: false.
