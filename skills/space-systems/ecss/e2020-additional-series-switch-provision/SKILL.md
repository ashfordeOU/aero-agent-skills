---
name: e2020-additional-series-switch-provision
description: "Evaluate whether a second series switch really lets a power line be opened when the main switch stays on. Use when an ECSS-E-ST-20-20C clause 5.2.13.3.1 line needs its additional commandable switch justified: confirm the extra device sits in series rather than in parallel, that its command path and drive domain are separate from the main switch, that it carries the derated line current, holds off the derated bus voltage and can break the prospective fault current, add the two conduction drops against the allowable line drop, and fold a common-cause factor into the residual stuck-on probability. Refuses an unknown arrangement word, a probability outside zero to one and a derating above unity. Trigger: ecss, e-st-20-20c, additional-series-switch-provision, series-switch-command-independence, switch-stuck-on-residual-probability, switch-breaking-capacity, series-conduction-drop, common-cause-beta-factor."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-additional-series-switch-provision, series-switch-command-independence, switch-stuck-on-residual-probability, switch-breaking-capacity, series-conduction-drop, common-cause-beta-factor, line-opening-capability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power — Additional Series Switch Provision (space-systems/ecss/e2020-additional-series-switch-provision)

Use when the task is the second-switch provision of ECSS-E-ST-20-20C
clause 5.2.13.3.1 — adding a further commandable switch in series so
that a power line can still be opened when the main switch does not let
go, and showing the added device actually delivers that capability
rather than only appearing on the schematic.

## Domain quick reference

- The failure the provision exists for is a switch that stays on. Welded
  relay contacts, an output device that has failed short, a drive stage
  that never releases: the command is issued, and the line stays live.
  Nothing downstream can be de-energised, so a fault that the line is
  feeding keeps being fed.
- The extra switch has to be IN SERIES. A device in parallel with the
  main switch makes the line harder to open, not easier — it is an
  availability provision and it is the opposite of this one. Getting the
  arrangement word right is the first check, not a formality.
- A second switch on the same command path or the same drive domain as
  the main switch is defeated by the failure that defeated the first.
  Independence of the command and independence of the drive are what the
  provision is actually buying; a duplicated device on one command line
  buys mass.
- The added device now carries the full line current continuously and
  holds off the bus voltage, but the figure most often skipped is the
  BREAKING capacity. Opening a line under fault is exactly the condition
  this switch exists for, so a device that carries the line comfortably
  and cannot interrupt the prospective fault current has not met the
  clause.
- Two devices in series conduct in series, so their on-state drops add
  at the same current. The provision therefore spends line voltage, and
  the sum has to stay inside whatever drop the line is allowed.
- The residual probability that the line still cannot be opened is not
  the bare product of the two stuck-on figures. One environment, one
  production lot, one sagging drive rail defeats both at once, so a
  common-cause factor is folded in; with the factor at zero the model
  falls back to the independent product, and with it at one the second
  device buys nothing at all.
- The derating factors, the common-cause factor and the allowable
  residual are declared project policy rather than physical constants;
  the defaults in the logic module are a starting point a project
  substitutes its own values into.

## Workflow

1. Validate both devices: command path, drive domain, technology,
   continuous and voltage ratings, breaking capacity, on-state
   resistance and stuck-on probability. A device that breaks less than
   it carries is a data error and is refused rather than assessed.
2. Validate the line: load current, bus voltage, the prospective fault
   current the line can deliver, and the drop the line is allowed to
   spend. A fault current below the load current is a data error.
3. Check the arrangement word first. A parallel device is reported as
   unable to open the line, and the rest of the assessment is still run
   so the reviewer sees every reason at once.
4. Compare the command path and the drive domain of the two devices.
   Either one shared is a finding. A shared technology is an advisory:
   it does not defeat the provision by itself, but it is the signal to
   raise the common-cause factor rather than leave it at its default.
5. Derate each device's continuous and voltage ratings by the project
   factors and compare against the line current and the bus voltage;
   compare each breaking capacity against the prospective fault current.
6. Add the two on-state drops at the line current and compare the sum
   against the allowable line drop.
7. Fold the common-cause factor into the two stuck-on probabilities and
   compare the residual against the allowable, reporting the improvement
   over the main switch alone and raising an advisory when the residual
   is dominated by the shared-cause term — the case where a third device
   would buy almost nothing.

## Pitfalls

- Duplicating the switch but not its command. A second device on the
  same command path or the same drive rail fails with the first, so the
  provision reads as redundancy on the schematic and delivers none.
- Sizing the extra device on the line current alone. It has to break the
  prospective fault current, and a switch chosen to carry the load will
  often be nowhere near that figure; the fault case is the one the
  device exists for.
- Adding the device in parallel. It is an easy schematic slip and it
  inverts the intent: opening the line requires every series element to
  open, so a parallel path guarantees the line stays live.
- Multiplying the two stuck-on probabilities and stopping there. The
  bare product assumes nothing can defeat both devices at once, which is
  the assumption a shared environment, a shared lot and a shared drive
  rail all break; the residual has to carry a common-cause term.
- Forgetting the drop the provision costs. Both devices conduct all the
  time, so the line pays their summed drop continuously, and a provision
  added late can push a line that was already near its allowable drop
  over it.
- Comparing a derated rating or a summed drop by bare arithmetic. A
  derated rating is a product of a rating and a factor and the drop is a
  sum of products, so a device meant to sit exactly on the line current
  or exactly on the allowable drop can land a few units in the last
  place the wrong side of the bound; the comparison absorbs that
  representation error while the deratings stay as specified.

## Behavior contract (gate 3)

The device validation, line validation, policy validation, arrangement
check, command and drive independence, derated capability, breaking
capacity, summed series drop, common-cause residual and the full
provision evaluation are exercised by the gate 3 contract test:
scripts/test_e2020_additional_series_switch_provision.py against
scripts/e2020_additional_series_switch_provision_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2020_additional_series_switch_provision.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
