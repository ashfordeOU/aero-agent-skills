---
name: e50-essential-telemetry-acquisition
description: "Evaluate an essential-telemetry set against ECSS-E-ST-50C clause 5.5.2: confirm the set is designated and covers every mandated health category, that each parameter stays acquirable in all declared mission phases including safe and contingency modes, that its acquisition path is independent of the nominal on-board processing chain so a processor reset cannot silence it, and that the aggregate encoded rate fits the guaranteed emergency downlink capacity. Use when scoping, reviewing or verifying an essential telemetry list, a safe-mode telemetry budget, or an emergency-link rate allocation. Trigger: ecss, e-st-50-communications-scope, essential-telemetry-acquisition, safe-mode-telemetry-availability, processor-independent-acquisition-path, emergency-downlink-rate-budget, health-category-coverage, contingency-phase-telemetry."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
clauses:
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.5.2
    items: [a, b, c, d]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications-scope, e50-essential-telemetry-acquisition, essential-telemetry-set, safe-mode-telemetry-availability, processor-independent-acquisition-path, emergency-downlink-rate-budget, health-category-coverage, contingency-phase-telemetry]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Essential Telemetry Acquisition (space-systems/ecss/e50-essential-telemetry-acquisition)

Use when the task is the essential-telemetry provision of ECSS-E-ST-50C
clause 5.5.2 — fixing which parameters make up the minimum set that lets
the ground establish spacecraft health and diagnose an anomaly, and
showing that set can actually be acquired and downlinked when everything
else on board has degraded.

## Domain quick reference

- Essential telemetry is a designated set, not a filter applied to the
  nominal housekeeping stream. It is named in the design, it is what the
  emergency mode transmits, and its membership is a decision that has to
  be justified category by category: power, thermal, attitude, the
  command link itself, and the state of the on-board computer.
- The set has to survive the conditions it exists for. A parameter that
  is only sampled in the nominal mission phase, or only when the payload
  is powered, is not essential telemetry however useful it is in cruise;
  the phase list a parameter is available in must cover every declared
  phase, safe and contingency modes included.
- Acquisition independence is the point of the clause that is easiest to
  lose. If the sample reaches the transmitter only by way of the nominal
  application processor, then a processor reset — the very event the
  ground is trying to diagnose — removes the evidence. An independent
  hardware path, or an acquisition chain in a separate processing domain,
  is what makes the parameter observable in that state.
- The set has to fit the link it will be heard on. The emergency
  downlink is the low-rate, low-gain, worst-case-pointing case, so the
  budget is the aggregate of bits-per-sample times sample rate over the
  whole set, grossed up by the frame and coding overhead of the
  transport, compared with the guaranteed emergency capacity — not with
  the nominal downlink rate.
- Sample rate is part of membership, not a separate tuning knob. Halving
  a rate to make the budget close changes what the ground can see of a
  transient; the trade is between which parameters are in the set and
  how fast each is sampled, and both sides of it belong in the same
  assessment.

## Workflow

1. Validate each candidate parameter: a name, a health category, a
   positive bits-per-sample, a positive sample rate, the set of mission
   phases it is available in, and whether its acquisition depends on the
   nominal on-board processing chain. A missing or non-positive field is
   an input error, not a default.
2. Check category coverage against the mandated health categories for
   the mission, which between them have to tell the ground how the
   vehicle as a whole is faring; report each category with no parameter
   behind it rather than reporting a single pass or fail.
3. Check phase coverage per parameter against the declared mission
   phases, and report the parameter-phase pairs that are missing.
4. Flag every parameter whose acquisition path is dependent on the
   nominal processing chain: on an on-board software application having
   to run, or on the space network being up. Those are the members that
   disappear in the condition the set exists for, and the acquisition
   should reach them by a route that waits on neither.
5. Take the set through the degraded case the clause is written for.
   For each parameter, establish that the critical monitoring point it
   is read from, and the chain that carries the sample to the
   transmitter and out to the ground, both still work when every other
   system on board has lost all but one of its redundant branches — the
   command and data management unit among them — and report each
   parameter that does not survive that condition.
6. Compute the aggregate encoded rate: the sum over the set of
   bits-per-sample times sample rate, multiplied by the transport
   overhead factor of the emergency frame and coding scheme.
7. Compare that rate with the guaranteed emergency downlink capacity,
   absorbing floating-point representation error at the boundary with a
   named tolerance rather than by inflating the capacity.
8. Confirm the membership is held as an agreed list, and that the
   agreement is in place no later than the preliminary design review:
   for each member, the rule that turns its raw sample into engineering
   units, the encoding it is carried in, and the format it is
   transmitted in.
9. Report the per-parameter rates, the aggregate, the headroom, and
   every finding: uncovered category, phase gap, dependent acquisition
   path, single-branch loss, capacity overrun.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.5.2a | 5 |
| ECSS-E-ST-50C Rev.2 5.5.2b | 8 |
| ECSS-E-ST-50C Rev.2 5.5.2c | 2 |
| ECSS-E-ST-50C Rev.2 5.5.2d | 4 |

## Pitfalls

- Treating the nominal housekeeping list as the essential set. The
  nominal list is sized for the nominal link and sampled by the nominal
  chain; both assumptions fail in the case clause 5.5.2 is written for.
- Counting a parameter as covered because it exists somewhere in the
  telemetry database. Coverage is per category and per mission phase; a
  parameter available only in the nominal phase leaves a phase gap that
  a set-level pass hides.
- Budgeting the aggregate against the nominal downlink rate. The
  emergency capacity is the one the set must fit, and it is lower by
  orders of magnitude on most missions.
- Forgetting the transport overhead. Frame headers, error-control coding
  and idle-frame insertion all consume the emergency capacity; a payload
  sum that just fits becomes an overrun once the overhead factor is
  applied.
- Widening the capacity to clear an exact-equality case. An aggregate
  landing on the capacity is a representation question, handled by the
  tolerance inside the comparison; the guaranteed capacity stays as
  specified.

## Behavior contract (gate 3)

The parameter validation, category coverage, phase coverage,
acquisition-independence screening, aggregate rate computation and
capacity comparison are exercised by the gate 3 contract test:
scripts/test_e50_essential_telemetry_acquisition.py against
scripts/e50_essential_telemetry_acquisition_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e50_essential_telemetry_acquisition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
