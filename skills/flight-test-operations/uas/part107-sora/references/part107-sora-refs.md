# Part 107 and SORA references

Paraphrased summary for the part107-sora skill. 14 CFR Part 107 is US
government work (public domain). EASA SORA and Regulation 2019/947 are
cited as guidance; no long excerpts are reproduced (standards-map.yaml
policy).

## FAA 14 CFR Part 107 (small UAS rule) section map

- 107.1 Applicability: small unmanned aircraft systems (sUAS) under 55
  lb (25 kg) including payload; operations outside of this are not
  conducted under Part 107.
- 107.3 Definitions: small UAS, visual line of sight (VLOS), control
  station, etc.
- 107.12 Remote pilot in command certificate: the PIC must hold a
  remote pilot certificate with a small UAS rating (or be supervised
  by such a holder).
- 107.29 Daylight operation: operations in daylight or civil twilight
  (with anti-collision lighting); the 2021 night rule allows night
  operations with lighting and training under conditions.
- 107.31 Visual line of sight aircraft operation: the PIC and visual
  observer must maintain VLOS of the small UAS at all times, unaided
  (except corrective lenses).
- 107.41 Operations in certain airspace: operations in Class B, C, D
  and E surface areas require ATC authorization (LAANC or a waiver).
- 107.51 Operating limitations for small UAS: max ground speed 100 mph
  (87 knots), max altitude 400 ft AGL (higher within 400 ft of a
  structure), no careless or reckless operation.
- 107.64 Remote pilot certificate requirements, 107.65 operating rules
  for the PIC, 107.73/107.74/107.77 certificate process.
- 14 CFR 89: Remote ID rule, compliance dates and broadcast/network
  requirements.

BVLOS: vanilla Part 107 requires VLOS (107.31). Beyond visual line of
sight operations need a waiver of 107.31 or FAA BVLOS rule approval;
the FAA BVLOS rulemaking has evolved since the 2021 BVLOS ARC report,
so current FAA guidance must be verified before relying on any route.

## EASA Regulation 2019/947 and SORA background

- Regulation (EU) 2019/947 establishes three UAS operational
  categories:
  - Open: low risk, no prior authorization, subject to sub-category
    limits (A1/A2/A3 by mass and separation from people).
  - Specific: risk beyond open limits; requires an operational
    authorization or a declaration against a standard scenario (PDRA),
    usually built on a SORA.
  - Certified: highest risk (large aircraft, operations over
    assemblies of people, transport); type certification and operator
    certification apply.
- SORA (Specific Operations Risk Assessment), JARUS SORA 2.0: the
  methodology used to build the specific category safety case:
  1. ConOps description (operational volume, flight geography).
  2. Intrinsic ground risk class (GRC) from kinetic energy and ground
     population density (Table 4 style matrix).
  3. Mitigations: strategic (M1 containment, M2 effects of failures,
     M3 situational awareness) and tactical, each with robustness
     levels (none/low/medium/high).
  4. Air risk class (ARC) from airspace class and traffic density,
     then a tactical mitigation percentage (TMPR) for the residual air
     risk.
  5. SAIL (Specific Assurance and Integrity Level) combines GRC and
     ARC and drives the required integrity/assurance of the system and
     operator.

## Simplifications in part107_sora_logic.py

- GRC table: intrinsic GRC only (JARUS SORA 2.0 style, GRC 1-9);
  mitigations are applied through robustness_level, not through the
  full SORA mitigation loop. SAIL, TMPR and ConOps fidelity are out of
  scope; the summary is a screening artifact, not a submitted SORA.
- Kinetic energy uses a characteristic cruise speed (default 20 m/s);
  real SORA uses the kinetic energy at the intended operating speed
  over the ground footprint.
- ARC mapping is by airspace class only with a single altitude
  escalation rule; real SORA also considers traffic density and
  proximity to aerodromes.
- Part 107 checks are binary gates; night-rule conditions and
  structure-proximity altitude exceptions are noted but not modeled.
