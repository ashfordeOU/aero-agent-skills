---
name: load-event-identification
description: "Use when identify all load events a structure will experience across its full mission lifecycle — assembly, test, flight, and ground operations — so that no load case is omitted from the structural analysis. For each event, record its phase, the applicable load types (quasi-static, dynamic, thermal, pressure, acoustic, shock), and any limit or qualification factor. Verify that every mandatory phase has at least one event, that all flight mission phases (launch, ascent, on-orbit, separation) are represented, and that each event entry is complete before it enters the load schedule. Trigger: ecss, e-st-32-structures-scope, load-events, load-cases, structural-loads, mission-phases, assembly-loads, test-loads, flight-loads, ground-ops."
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
  tags: [ecss, e-st-32-structures-scope, load-events, load-cases, structural-loads, mission-phases, assembly-loads, test-loads, flight-loads, ground-ops]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Load Event Identification (space-systems/ecss/load-event-identification)

Use when the task is to enumerate every load event across the full mission lifecycle (ECSS-E-ST-32C clause 7.2.1) so that the structural analysis covers assembly, test, flight, and ground operations without omission.

## Domain quick reference

- Clause 7.2.1 requires the load event list to span four phases: **assembly** (integration steps, mate/demate, handling during build), **test** (environmental qualification, static and dynamic testing, pressure proof), **flight** (launch, ascent, on-orbit operations, separation events, re-entry or landing), and **ground operations** (transportation, storage, fuelling, launch-site handling). Every phase must contribute at least one event to the load schedule.
- Each event is described by its **phase**, a set of **load types** drawn from: quasi-static (steady-state acceleration), dynamic (random vibration, acoustic, sine), thermal (temperature gradient, delta-T), pressure (internal or external), acoustic (high-intensity sound field), and shock (pyrotechnic or mechanical impulse). An event may carry more than one load type simultaneously.
- Flight events must include at minimum: lift-off/launch, ascent (max-q or maximum dynamic pressure), on-orbit (deployment, manoeuvre, docking), and separation. Omitting any of these is a gap in the load schedule, not a conservative assumption.
- Each event carries a **limit load factor** (applied to the design limit load, DLL) and, where qualification testing is the verification method, a **qualification factor** (typically 1.25 × DLL). These factors are set by the applicable loads specification, not by this leaf; this leaf flags events where either factor is absent.

## Workflow

1. Obtain the programme loads specification and the mission timeline. List every distinct operational phase from manufacturing through end-of-life disposal or re-entry.
2. For each phase, enumerate every event that imposes a structural load. Assign each event a unique identifier, its phase label (assembly, test, flight, ground_ops), and one or more load types. Record the limit load factor and qualification factor where known; mark them as pending where not yet defined.
3. Validate each event entry: name present, phase from the allowed set, at least one valid load type, no unrecognized load type. Reject incomplete entries and request the missing data before the event enters the schedule.
4. Check phase coverage: confirm that at least one valid event exists for each of the four mandatory phases. Record any missing phase as a gap finding.
5. Check flight sub-event coverage: confirm that the flight phase entries collectively include launch, ascent, on-orbit, and separation. Record any missing flight sub-event as a gap finding.
6. Produce the consolidated load event schedule listing all valid events grouped by phase, followed by a gap report (missing phases, missing flight sub-events, incomplete entries). The schedule is not ready for stress analysis until the gap report is empty.

## Pitfalls

- Omitting assembly events on the assumption that assembly loads are small — integration tooling reactions and mate/demate forces can govern local fittings and are required by clause 7.2.1 regardless of magnitude.
- Treating test and flight as interchangeable — qualification test loads (×1.25 on DLL) are separate events from the flight limit loads they verify; both must appear in the schedule, in their own phase rows.
- Listing only the worst-case flight event (e.g., max-q) and suppressing earlier or later events — each distinct flight phase can govern different structural members, and clause 7.2.1 requires complete enumeration, not reduction to a single envelope.
- Leaving the limit load factor blank and entering the event anyway — a factor-less event will produce an unchecked analysis; the gap must be flagged and resolved before the event is accepted.

## Behavior contract (gate 3)

The event-validation, phase-coverage, flight-sub-event-coverage, and gap-reporting logic is exercised by the gate 3 contract test: scripts/test_load_event_identification.py against scripts/load_event_identification_logic.py (stdlib unittest, offline). Run:

```
python3 scripts/test_load_event_identification.py
```

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
