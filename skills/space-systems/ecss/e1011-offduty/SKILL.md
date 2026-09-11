---
name: e1011-offduty
description: "Use when design off-duty stations — sleep quarters, personal hygiene
  facilities, and recreation areas — aboard a crewed spacecraft per ECSS-E-ST-10-11C
  §4.7.7 HFE requirements: categorize each station as sleep, hygiene, or recreation,
  verify mandatory parameters (acoustic attenuation, lighting range, thermal envelope,
  volume, restraint, privacy) for sleep stations, verify containment and accessibility
  parameters for hygiene facilities, verify exercise volume and communication link
  availability for recreation areas, and aggregate findings per station to determine
  overall HFE compliance. Trigger: ecss, e-st-10-system-scope, e-st-10-11c,
  off-duty-stations, sleep-station, hygiene-facility, recreation, human-factors."
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
  tags: [ecss, e-st-10-system-scope, e-st-10-11c, off-duty-stations, sleep-station, hygiene-facility, recreation, human-factors]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS HFE — Off-Duty Stations (space-systems/ecss/e1011-offduty)

Use when the task is to design or verify off-duty crew accommodations aboard a
crewed spacecraft under ECSS-E-ST-10-11C §4.7.7 — covering sleep quarters,
personal hygiene facilities, and recreation areas, each with its own parameter
set that must satisfy HFE requirements before the station is considered compliant.

## Domain quick reference

- §4.7.7 groups off-duty provisions into three station types, each with distinct
  design criteria: **sleep** (privacy, acoustic isolation, lighting controllability,
  thermal comfort, physical restraint), **hygiene** (fluid containment, water
  delivery rate, physical accessibility, handholds for microgravity use), and
  **recreation** (communication link to ground, adequate exercise volume, suitable
  lighting for leisure and exercise tasks).
- Each station type is evaluated against its own parameter set; a sleep parameter
  (e.g. acoustic attenuation) is not carried over to the hygiene check and vice
  versa. Mixing parameter sets across station types produces invalid results.
- Sleep station lighting must span the full range from 0 lux (full dark for
  sleep onset) up to a task-lighting maximum; both bounds are checked separately.
  A station that cannot achieve full dark fails the sleep-lighting requirement
  even if its maximum level is within bounds.
- All three station types use a boolean presence check for critical system
  features (restraint system, privacy screen, waste containment, communication
  link). A feature present but set to False is treated the same as a missing
  feature — it must be True to pass.
- Missing parameters are tracked separately from out-of-bound findings so that
  a station with a gap in its design record is not read as compliant merely
  because no numeric violation was computed.

## Workflow

1. Identify every off-duty station in the spacecraft design record and assign
   each a station type (sleep, hygiene, or recreation). Reject any station whose
   type is not one of these three — do not guess or default; return an error and
   request clarification before continuing.
2. For each **sleep station**, collect and check: acoustic attenuation (dB),
   minimum and maximum achievable lighting (lux), minimum and maximum design
   temperature (°C), crew personal volume (m³), and boolean presence of a
   restraint system and a privacy screen. Flag each parameter that is absent or
   outside its bound.
3. For each **hygiene station**, collect and check: water flow rate (mL/min),
   boolean presence of a waste containment system, accessibility rating (1–5
   scale, minimum 3), and handhold count (minimum 2). Flag each parameter that
   is absent or outside its bound.
4. For each **recreation station**, collect and check: boolean availability of a
   communication link to ground, exercise envelope volume (m³, minimum 10),
   and lighting level (lux, minimum 300). Flag each parameter that is absent or
   outside its bound.
5. Aggregate findings and missing parameters per station. A station is
   HFE-compliant only when both lists are empty. Report the total station count,
   the compliant count, and the per-station finding lists so the design team can
   act on each gap individually.
6. If all stations in the set are compliant, report overall compliance. If any
   station fails, the set is not compliant — partial compliance is not an
   accepted outcome; every station must individually pass.

## Pitfalls

- Treating a boolean feature as compliant when its value is False because the
  key is present in the design record — the requirement is that the system is
  operational (True), not merely mentioned.
- Checking only the maximum lighting level for a sleep station and missing that
  the minimum achievable level must reach full dark (0 lux) — a station that
  cannot dim below 5 lux fails the sleep requirement regardless of its ceiling.
- Applying sleep-station acoustic or volume thresholds to a hygiene or
  recreation station — each station type has its own parameter set and bounds;
  cross-applying them produces false findings or false passes.
- Reading an empty findings list as compliant when the missing list is non-empty
  — a station with unset parameters has incomplete data, not no violations.
- Aggregating numeric parameters across station types (e.g., summing volumes
  across all three types) — each parameter is local to its station record.

## Behavior contract (gate 3)

The station-type validation, per-type parameter bounds checking, boolean
presence checks, missing-parameter tracking, and set-level aggregation logic
are exercised by the gate 3 contract test:
scripts/test_e1011_offduty.py against scripts/e1011_offduty_logic.py
(stdlib unittest, offline, deterministic). Run:
  python3 scripts/test_e1011_offduty.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
