---
name: e2020-retrigger-default-enabled-state
description: "Determine whether a retriggerable limiter comes up with its retrigger behaviour already active, under ECSS-E-ST-20-20C clause 5.2.6.3.1. Use when a power design declares a power-up default and that declaration has to be checked against evidence: refuse an undeclared default, require every restarting event the project names rather than cold power-up alone, fail a restart that carries the pre-event state across instead of defaulting, and compare the time each restart needs to put the default in force against the moment a load can first be enabled. Trigger: ecss, e-st-20-20c-clause-5-2-6-3-1, retrigger-function-power-up-default-enabled, retrigger-enabled-after-reset, retrigger-default-state-volatility, retrigger-default-establishment-time, retrigger-default-restart-event-coverage."
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
  tags: [ecss, e-st-20-20-power-distribution-scope, e-st-20-20c-clause-5-2-6-3-1, e2020-retrigger-default-enabled-state, retrigger-function-power-up-default-enabled, retrigger-enabled-after-reset, retrigger-default-state-volatility, retrigger-default-establishment-time, retrigger-default-restart-event-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Limiters -- Retrigger Default Enabled State (space-systems/ecss/e2020-retrigger-default-enabled-state)

Use when the task is the clause 5.2.6.3.1 question of ECSS-E-ST-20-20C:
a retriggerable limiter that has just powered up has to have its
retrigger behaviour active, with nobody having commanded it.

## Domain quick reference

- A default is only a default if it is reached from every state the
  limiter could have been in beforehand. A design that comes up enabled
  because the previous state happened to be enabled has demonstrated
  nothing; the first time it is entered from a disabled limiter it comes
  up disabled.
- The default has to hold after every event that restarts the limiter,
  not only after a cold power-up. A warm reset, a watchdog reset and a
  recovery from undervoltage all leave the limiter running again, and a
  design that establishes the default on cold power-up alone has left
  the other paths to whatever configuration memory happened to hold.
- A retained state is a defect even when the retained value is the
  enabled one. The mechanism that carried it across will carry the other
  value just as willingly on the next restart, so retention is judged on
  the mechanism, not on the value it happened to hold in the test.
- The consequence of getting this wrong is quiet and long-lived. An
  operator who disabled retrigger during a fault investigation months
  earlier has, on a design with retained configuration, silently decided
  how this limiter answers today's overcurrent, and nothing in the
  telemetry of the restart says so.
- Establishing the default is not instantaneous. A controller boots,
  reads its reset defaults and only then governs the retrigger logic, so
  there is a window between the restart and the default actually being
  in force. If a load can be enabled inside that window, the first
  overcurrent meets an undefined retrigger behaviour.
- A limiter coming up with retrigger inactive is not merely
  non-compliant; it is a different component. It behaves as a plain
  latching limiter, and every fault-protection sequence written around
  the automatic retry is wrong for it.

## Workflow

1. Validate the restart policy first: which restarting events the
   project requires evidence for, how soon after a restart a load can be
   enabled, and the advisory band. An empty required-event list, or an
   advisory band above the whole window, is refused rather than used.
2. Validate every restart record: a non-blank event name, a retrigger
   state drawn from the two admissible values, a boolean retention flag
   and a non-negative time to establish the default. Duplicate event
   names and an empty record set are refused.
3. Read the declared power-up state. An absent declaration closes the
   assessment on default not declared; a declaration of inactive closes
   it on default not enabled, before any evidence is weighed.
4. Compare the covered events against the required set and name every
   restart with no evidence behind it, not the first one found. An event
   beyond the required set is not a finding.
5. Name every restart that comes up inactive and every restart that
   carries the pre-event state across, and report them together rather
   than stopping at the first.
6. Take the slowest restart, compute how long the default is in force
   before a load can first be enabled, and compare with a named
   tolerance; a margin landing exactly on zero is admissible.
7. Close on one verdict: default not declared, restart coverage
   incomplete, default not enabled, default established too late, or
   enabled by default after every restart -- with the slowest restart,
   its margin and any advisory beside it.

## Pitfalls

- Testing the default only from an already enabled limiter. That case
  cannot fail, so it is the one case that proves nothing; the evidence
  has to enter at least one restart with retrigger commanded off.
- Accepting cold power-up evidence for every restart. The reset paths
  differ in exactly what they reinitialise, which is why a watchdog
  reset is where retained configuration usually surfaces.
- Reading a retained enabled state as a pass. The value is not the
  question; the mechanism that retained it is, and it will retain the
  other value next time.
- Ignoring the establishment window. A default that is correct fifty
  milliseconds after the restart is still absent for the load enabled
  ten milliseconds after it.
- Moving the load-enable window to admit a slow boot. The window is a
  declared project value; widening it to fit the design under assessment
  turns the check into a restatement of the design.

## Behavior contract (gate 3)

The policy validation, restart-record validation, declared-default
reading, required-event coverage, the inactive-restart and
retained-state determinations, the establishment-window margin and the
advisories are exercised by the gate 3 contract test:
scripts/test_e2020_retrigger_default_enabled_state.py against
scripts/e2020_retrigger_default_enabled_state_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_retrigger_default_enabled_state.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
