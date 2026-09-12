---
name: load-events-and-combined-loads
description: "Use when enumerate structural load events and define load combination rules for a space structure under ECSS-E-ST-32C clauses 4.2.5–4.2.6: categorize each load event by mission phase (ground handling, transport, launch, ascent, separation, on-orbit, re-entry, landing), identify the governing load types per event (quasi-static, dynamic, thermal, pressure, acoustic, random vibration, shock), apply combination factors to form design load cases at both limit and ultimate load levels, and flag any event missing a required load type or any load set with incomplete phase coverage. Trigger: ecss, e-st-32-structures-scope, load-events, combined-loads, load-combinations, structural-analysis, design-load-cases, mission-phases."
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
  tags: [ecss, e-st-32-structures-scope, load-events, combined-loads, load-combinations, structural-analysis, design-load-cases, mission-phases]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Load Events and Combined Loads (space-systems/ecss/load-events-and-combined-loads)

Use when the task is to enumerate every structural load event across the
mission timeline and define the rules by which concurrent loads are
combined into design load cases, following ECSS-E-ST-32C clauses 4.2.5
(load events) and 4.2.6 (combined loads and interaction rules).

## Domain quick reference

- A load event is a bounded period or occurrence during the mission at
  which the structure experiences a defined set of mechanical, thermal,
  or pressure loads. Each event is anchored to a mission phase: ground
  handling, transportation, launch, ascent, separation, on-orbit,
  re-entry, or landing. Phases outside this set are not valid load event
  anchors under ECSS-E-ST-32C clause 4.2.5.
- Each phase carries a minimum required set of load types that must be
  assessed. Launch and ascent require quasi-static, acoustic, random
  vibration, and thermal loads as a minimum; separation and landing
  require shock in addition to quasi-static loads; on-orbit requires
  quasi-static and thermal; re-entry adds pressure. Failing to include
  a required load type for a phase is a design incompleteness finding.
- A design load case is formed by selecting one or more concurrent load
  types from the same event (or from events that can overlap in time)
  and applying a combination factor to each component before summing.
  A factor of 1.0 means the load contributes at its full value; a
  factor less than 1.0 reflects a reduced probability of simultaneous
  occurrence. A factor of 0.0 means the load type is not considered in
  that case.
- Limit load is the highest load expected under the specified load event.
  Ultimate load is obtained by multiplying the limit load by the
  ultimate factor (typically 1.5 for metallic structures under
  ECSS-E-ST-32C, but the project-specific value takes precedence).
  Both levels must be evaluated for each design load case.

## Workflow

1. Inventory every expected load event across the mission timeline and
   assign each one to a mission phase. Reject any event whose phase is
   not in the ECSS-E-ST-32C set; request clarification before
   proceeding.
2. For each event, record the load types present. Check the event's
   load types against the minimum required set for its phase; list
   every missing load type as a gap to be resolved before the load set
   is considered complete.
3. Form design load cases by selecting concurrent load types within an
   event (or across overlapping events) and assigning a combination
   factor to each. Verify that every combination factor is between 0.0
   and 1.0 inclusive unless a factor greater than 1.0 is explicitly
   justified by a project-specific amplification requirement.
4. Compute the combined design load for each case: multiply each load
   component's value by its combination factor and sum the results.
   Record the computed value and the load types and factors used.
5. Scale each limit-load design case to ultimate load using the
   applicable ultimate factor. Evaluate structural margins against both
   the limit and ultimate values.
6. Check that the full set of events covers every required mission
   phase. Report any phase that is absent from the event inventory as
   a coverage gap. A load set with missing phases is not complete.
7. Identify the governing design load case as the combination that
   produces the highest design load across all cases. Flag it for
   priority attention in the structural analysis.

## Pitfalls

- Assigning more than one mission phase to a single load event — each
  event belongs to exactly one phase, and mixing phases obscures which
  minimum load-type requirements apply.
- Applying a combination factor greater than 1.0 without a written
  justification — ECSS-E-ST-32C clause 4.2.6 treats factors above 1.0
  as amplification, which requires a specific structural dynamics or
  margins rationale.
- Treating an unset combination factor as 1.0 — the correct default
  when a factor is absent is 0.0 (load type not combined), not 1.0,
  because an unchecked assumption inflates the combined load and may
  miss the true governing case.
- Skipping the ultimate-factor step on any load case — limit and
  ultimate evaluations are both mandatory; a load case that only
  records a limit value is incomplete.
- Declaring coverage complete when every individual event passes its
  load-type check but a required mission phase has no event at all —
  per-event compliance does not substitute for full-phase coverage.

## Behavior contract (gate 3)

The load event validation, load type coverage check, combination
computation, ultimate factor scaling, phase coverage check, and
governing case selection logic are exercised by the gate 3 contract
test: scripts/test_load_events_and_combined_loads.py against
scripts/load_events_and_combined_loads_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_load_events_and_combined_loads.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
