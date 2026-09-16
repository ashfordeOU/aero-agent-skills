---
name: e2008-vacuum-thermal-cycling-purpose
description: "Use when scoping or reviewing a solar-array vacuum cycling campaign. Determine why a photovoltaic assembly is cycled in vacuum rather than in air under ECSS-E-ST-20-08C clause 5.5.3.11.1, and whether the planned run serves that purpose: group every declared component, assembly and interface into the survival objective the run makes it demonstrate, mark the items whose failure mode only exists once the air is gone, confirm the cycled article actually carries each declared item, then check the chamber pressure, the hot and cold extremes and the cycle count bound the flight environment with their margins. Trigger: ecss, e-st-20-08c, clause-5-5-3-11-1, vacuum-thermal-cycling-purpose, solar-array-vacuum-cycling, vacuum-specific-failure-mode, cold-welding-interface-survival, chamber-vacuum-level-bound, cycled-article-item-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-vacuum-thermal-cycling-purpose, vacuum-thermal-cycling-purpose, solar-array-vacuum-cycling, vacuum-specific-failure-mode, cold-welding-interface-survival, cycled-article-item-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Vacuum Thermal-Cycling Purpose (space-systems/ecss/e2008-vacuum-thermal-cycling-purpose)

Use when the task is to state and defend why the components, the assemblies
and the interfaces of a photovoltaic assembly are cycled inside a vacuum
chamber under ECSS-E-ST-20-08C clause 5.5.3.11.1 — what survival the run is
bought to demonstrate, whether the hardware earns a vacuum environment at all,
and whether the planned run bounds the environment it stands in for.

## Domain quick reference

- The purpose is survival, and it is owed to three families at once:
  components, assemblies and the interfaces between them. An inventory that
  declares only components leaves the interface objectives unstated, and an
  interface is where most of the cycled damage accumulates.
- Each declared item turns into its own objective. A coverglass bondline, an
  interconnect, a bus-bar joint, a harness insulation, a mated connector, a
  hinge and a blanket attachment each fail differently under cycling, so each
  makes the run demonstrate something different.
- Vacuum is not chamber housekeeping, it is part of the requirement. Residual
  gas carries heat and suppresses the failure modes that only exist without
  air: adhesive outgassing, insulation embrittlement, cold welding of mated
  or moving metals, and the loss of every convective path. An inventory with
  none of those modes is honestly cycled in air, and saying so is a legitimate
  outcome of this assessment.
- An objective nobody can observe is not demonstrated. An item declared for
  the run but absent from the cycled article leaves its objective unserved
  however well the chamber performed, so article coverage is graded next to
  the chamber conditions rather than assumed.
- A run only serves the purpose when it bounds what it represents: at or below
  the pressure that still counts as vacuum, hotter and colder than the
  predicted extremes by the agreed margin, and at least the predicted cycles
  times the coverage factor. A milder run demonstrates nothing about the life
  it was bought to cover.
- A stated purpose is not a served purpose. An assembly that earns the run but
  has nothing planned is a distinct outcome from one whose planned run falls
  short, and the two carry different actions.

## Workflow

1. Validate the campaign policy first: the pressure that still counts as a
   vacuum environment, the temperature margin owed to the predicted extremes
   and the cycle coverage factor. A coverage factor below unity would let the
   run fall short by construction and is refused.
2. Group the declared inventory, rejecting an unrecognised item rather than
   ignoring it, and map each item to the objective it makes the run
   demonstrate together with the family it belongs to.
3. Mark the items whose failure mode only exists without air. At least one of
   them is what earns a vacuum run; with none, report that an ambient run
   covers the inventory and stop there.
4. Measure article coverage: name every declared item the cycled article does
   not carry, and the family each of them belongs to.
5. Check the planned run on all four counts — pressure, hot extreme, cold
   extreme, cycle count — and report each count that falls short with its
   value and the value it owed. A run landing exactly on an owed value
   complies; the comparison tolerance absorbs representation error and no
   bound moves.
6. Close on one verdict: vacuum not required, justified but nothing planned,
   planned run under bounds, or planned run bounding the flight environment,
   with the objectives the run serves attached to it.

## Pitfalls

- Justifying the run as "thermal cycling, in a vacuum chamber". That rationale
  survives no review, because it never says which failure mode needed the air
  removed, and it cannot defend the cost of the chamber.
- Declaring only components. The interfaces — mated connectors, hinges,
  bonding straps, blanket attachments — are where cold welding and
  differential motion do their damage, and an unstated interface objective is
  an undemonstrated one.
- Accepting a chamber pressure "roughly a vacuum". Around a pascal the
  residual gas still conducts heat and still suppresses cold welding, so the
  run quietly stops being the environment the clause asks for.
- Assuming the cycled article carries everything the inventory declares. A
  coupon built without the connector it was supposed to represent leaves that
  objective unserved and the finding invisible.
- Reading a shortfall in one count as a shortfall overall and stopping. Each
  of pressure, extremes and cycle count is reported with what it owed, because
  they are fixed by different people in different ways.
- Treating a value that lands exactly on an owed bound as a failure. Equality
  at a bound is a representation question, handled by the tolerance inside the
  comparison; widening the bound to pass a run is the wrong fix.

## Behavior contract (gate 3)

The policy validation, objective grouping, vacuum-specific marking, article
coverage, environment bounding and purpose verdict are exercised by the gate 3
contract test: scripts/test_e2008_vacuum_thermal_cycling_purpose.py against
scripts/e2008_vacuum_thermal_cycling_purpose_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_vacuum_thermal_cycling_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
