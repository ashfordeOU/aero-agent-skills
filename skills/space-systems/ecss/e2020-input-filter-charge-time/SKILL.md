---
name: e2020-input-filter-charge-time
description: "Compute whether the input filter of a protected load finishes charging inside the charging window it is allowed while its feeding limiter holds the current. Use when an ECSS-E-ST-20-20C clause 5.3.2.3.1 load design has to show the filter energises in time: total the filter stage capacitances the bus actually sees, take the load draw during charging off the held limiting current, charge that total at what is left, and compare against the allowed window with the project margin applied. Refuses a load draw that leaves no net charging current, and reports the largest filter the window would still carry. Trigger: ecss, e-st-20-20c, load-input-filter-charge-time, filter-stage-capacitance, limitation-charging-window, net-charging-current, held-limiting-current, filter-charge-time-margin."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-input-filter-charge-time, filter-stage-capacitance, limitation-charging-window, net-charging-current, held-limiting-current, filter-charge-time-margin, load-input-filter-energisation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power — Load Input Filter Charge Time (space-systems/ecss/e2020-input-filter-charge-time)

Use when the task is the input filter charging demonstration of
ECSS-E-ST-20-20C clause 5.3.2.3.1 — showing that the capacitive filter
at a protected load's input is fully charged before the charging window
allowed during limitation runs out.

## Domain quick reference

- Energising a load input filter is a limitation event by construction.
  The protective switch feeding the unit cannot supply the inrush a
  discharged capacitance demands, so it holds its output to a limiting
  current and stays there while the filter charges. It only tolerates
  that state for a bounded window before it opens.
- While the switch is limiting, its output is a current source, so the
  filter charges linearly and the time is C*V/I. The relevant I is the
  HELD limiting current, at the lower edge of whatever band the unit is
  allowed to limit in, because a compliant switch may hold anywhere in
  that band and the slowest charge is the binding case.
- The capacitance is every stage in parallel, not the first stage alone.
  A filter is usually a common-mode stage, a differential stage and a
  bulk hold-up capacitor; the bus sees all of them, and the bulk stage
  is normally the one that dominates the total.
- The unit draws its own current while the filter is charging, and only
  the REMAINDER of the held current reaches the capacitance. Charging at
  the full held current is the common defect: it under-reports the time,
  and on a unit whose housekeeping draw is a real fraction of the held
  current it under-reports it badly.
- A unit whose draw during charging reaches or exceeds the held limiting
  current never charges at all. There is no charge time to report: the
  input voltage does not rise, the window expires and the switch opens.
  That is a distinct outcome from a filter that charges too slowly, and
  the repair is different, so it is reported as its own verdict.
- Inverting the charge time at the margin gives the largest total filter
  the window would carry. That is the figure a designer needs when the
  check fails, because it says how much capacitance has to come out.
- The charge margin and the utilisation advisory ceiling are declared
  project policy rather than physical constants; the defaults in the
  logic module are a starting point a project substitutes its own values
  into.

## Workflow

1. Validate the filter: unique stage names and a positive capacitance
   per stage. An empty stage list is refused rather than treated as a
   filter of zero capacitance that charges instantly.
2. Validate the charging conditions: bus voltage, held limiting current,
   the unit's own draw during charging and the allowed window. A draw of
   zero is accepted; a negative one is not.
3. Total the stage capacitances the bus sees in parallel, and report
   each stage's share so a reviewer can see which stage dominates.
4. Take the unit's draw during charging off the held limiting current to
   get the net current that actually reaches the capacitance.
5. If that net current is zero or negative, stop and report that the
   filter never charges. Do not divide by it.
6. Otherwise charge the total capacitance at the net current, apply the
   project margin, and compare against the allowed window. Report the
   slack in seconds and the share of the window consumed.
7. Report the largest total capacitance the window would still carry, and
   raise an advisory when a passing filter already consumes most of the
   window.

## Pitfalls

- Charging at the full held limiting current. The unit's own draw during
  charging comes off first, and only the remainder reaches the
  capacitance; ignoring it under-reports the charge time.
- Totalling only the bulk capacitor, or only the first filter stage. The
  bus sees every stage in parallel, and a check run on part of the
  filter passes a unit that will not start.
- Dividing by a net charging current that is zero or negative. A unit
  drawing at or above the held current is a real and reportable design
  state, not an arithmetic accident, and it needs its own verdict
  because shedding capacitance will not repair it.
- Charging at the middle or the upper edge of the limiting band. A
  compliant switch may hold anywhere in its band, so the binding case is
  the lowest current it may hold, and a midpoint calculation reports a
  charge a compliant unit will not deliver.
- Comparing the charge time with the window by bare arithmetic. A charge
  time is built by division and the margin by multiplication, so a
  filter meant to sit exactly on the window can land a few units in the
  last place the wrong side of it; the comparison absorbs that
  representation error while the window and the margin stay as
  specified.

## Behavior contract (gate 3)

The policy validation, filter and condition validation, capacitance
totalling, net charging current, charge time, supportable-capacitance
inversion and the full clause assessment are exercised by the gate 3
contract test: scripts/test_e2020_input_filter_charge_time.py against
scripts/e2020_input_filter_charge_time_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_input_filter_charge_time.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
