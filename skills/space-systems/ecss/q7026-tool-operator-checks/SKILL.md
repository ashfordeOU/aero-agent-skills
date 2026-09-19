---
name: q7026-tool-operator-checks
description: "Evaluate the operator go and no-go gauge check on a crimp tool and the logbook entry recording it under ECSS-Q-ST-70-26C, then bound the crimps made since the last good check. Use when a shift starts, or a gauge check fails and the affected production run has to be scoped. Reads the pin pair as pass, die-undersize, die-worn-open or an untrustworthy gauge set, names every missing logbook field, releases or holds the tool, and spans the quarantine back to the last passing check rather than to the shift start. Trigger: ecss, q-st-70-26, crimp-go-no-go-gauge-check, crimp-tool-logbook-entry, crimp-operator-release-check, crimp-quarantine-span, crimp-tool-hold."
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
  tags: [ecss, q-st-70-26-crimping-scope, q7026-tool-operator-checks, crimp-go-no-go-gauge-check, crimp-tool-logbook-entry, crimp-operator-release-check, crimp-quarantine-span, crimp-tool-hold]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Crimping — Operator Checks and Tool Logbooks (space-systems/ecss/q7026-tool-operator-checks)

Use when the task is the operator-facing half of the ECSS-Q-ST-70-26C
tooling clause — the go and no-go check made before a crimp tool is
used, the logbook entry that records it, and what a failed check does
to the crimps already produced.

## Domain quick reference

- The gauge check is two observations, not one. The go pin has to enter
  the closed die and the no-go pin has to be refused by it. Only the
  pair is a pass.
- Each single failure names a wear direction. A go pin refused means
  the die is closing undersize; a no-go pin accepted means it has worn
  open. They are different repairs, and folding them into one "failed"
  loses the only diagnosis available at the bench.
- Both pins reading wrong at once is not a very bad tool. It is a gauge
  set that cannot be trusted, and the next action is to change gauges,
  not to condemn the tool.
- A check that was not recorded did not happen. The entry carries the
  tool, the operator, the time, the gauge set and the crimp counter
  reading, and a missing field is named so the person holding it can
  supply it rather than the entry being rewritten from memory.
- Release is the conjunction of a passing gauge and a complete entry. A
  good check with no counter reading releases nothing, because the
  evidence that would bound a later failure does not exist.
- The counter reading is what makes a failed check actionable. The
  suspect crimps are the ones made since the last passing check, not
  since the shift began. Quarantining the whole shift scraps good work;
  quarantining from the last check when that check also failed misses
  bad work.
- With no earlier passing check anywhere in the run, the span is open
  at the bottom and has to say so.

## Workflow

1. Read the go and no-go pin pair into one verdict: pass, die
   undersize, die worn open, or an untrustworthy gauge set.
2. Name every required logbook field that is missing, and separately
   every one present but unusable — a blank operator, a timestamp that
   is not a timestamp, a negative counter.
3. Decide release as a conjunction: complete entry, passing gauge, tool
   not already on hold. Collect every reason; do not stop at the first.
4. Validate the run as a run: one tool, entries in time order, a
   counter that never goes backwards.
5. For each failing check, walk back to the nearest earlier passing
   check and take the counter difference as the suspect span.
6. With no earlier passing check, report the span as open at the bottom
   rather than measuring it from the first entry as if that were good.
7. Roll the shift up: releases, holds, every quarantine with the index
   that raised it, crimps affected, crimps produced and the fraction.

## Pitfalls

- Recording one pin result. A tool that passes the go pin and also
  swallows the no-go pin reads as a pass on half the evidence.
- Collapsing undersize and worn-open into a single failure, which sends
  the tool for the wrong repair.
- Condemning a tool on a gauge set that contradicted itself.
- Releasing on a good gauge with a half-filled logbook. The counter
  reading is the whole value of the entry.
- Quarantining back to the shift start by default, which scraps work
  that a passing check already covered.
- Quarantining back to a check that had itself failed, which leaves bad
  crimps outside the span.

## Behavior contract (gate 3)

Gauge pin reading, logbook gap naming, the release conjunction, run
validation for tool identity, time order and counter monotonicity,
quarantine spans bounded by the last passing check and the open case,
and the shift roll-up with its quarantine fraction are exercised by the
gate 3 contract test:
scripts/test_q7026_tool_operator_checks.py against
scripts/q7026_tool_operator_checks_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7026_tool_operator_checks.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
