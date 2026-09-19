---
name: e7041-obcp-engine
description: "Evaluate whether an on-board control procedure engine can take another procedure under ECSS-E-ST-70-41C clause 6.18.2.3, where the engine is a bounded execution environment and not an unlimited interpreter. Use when the task is validating an engine capability declaration and then admitting or refusing a load or a start against the supported procedure language and version, the code and data footprint versus the engine store, the concurrently loaded and concurrently running limits, and the per-cycle step budget the already running set consumes, then reporting engine utilisation with a named reason for every refusal. Trigger: ecss, e-st-70-41c, obcp-engine-capability, obcp-load-admission, obcp-concurrency-limit, obcp-step-budget-per-cycle, obcp-engine-store-footprint, obcp-engine-utilisation."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-obcp-engine, obcp-engine-capability, obcp-load-admission, obcp-concurrency-limit, obcp-step-budget-per-cycle, obcp-engine-utilisation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — OBCP Engine (space-systems/ecss/e7041-obcp-engine)

Use when the task is the on-board control procedure engine of
ECSS-E-ST-70-41C clause 6.18.2.3 -- the bounded thing that actually runs
procedures, and whose declared limits decide which of them can be
resident and which of them can run at the same time.

## Domain quick reference

- The engine is a declared capability, not an assumption. It states the
  procedure languages and language versions it interprets, how many
  procedures it can hold loaded, how many it can run concurrently, the
  store available for procedure code and data, and the execution steps
  it can afford per cycle. Every admission decision is against that
  declaration, so an undeclared engine cannot be reasoned about at all.
- Loaded and running are different resources with different limits. A
  procedure occupies engine store from the moment it is loaded, whether
  or not it ever runs, and it consumes step budget only while running.
  Conflating the two either refuses procedures that would have fitted or
  admits a running set the engine cannot step.
- Language version is part of the language. An engine that interprets a
  procedure language at one version does not automatically interpret a
  later one, and a procedure built against the newer version is refused
  for a reason worth printing rather than loaded and left to fail at its
  first unrecognised construct.
- The step budget is per cycle and shared. Admitting a procedure whose
  per-cycle step demand exceeds what the running set leaves free does
  not slow the engine down gracefully; it overruns the cycle, which is
  a real-time failure of everything the engine hosts, not just of the
  newcomer.
- A stopped engine admits nothing. Loading into an engine that is not
  running looks harmless and leaves an operator believing a procedure is
  ready, so the engine state is checked before any resource is.

## Workflow

1. Validate the engine declaration: identifier, state, non-negative
   limits for concurrently loaded and concurrently running procedures,
   a positive store size, a positive per-cycle step budget, and at
   least one supported language at a stated version.
2. Validate each procedure: identifier, language, language version,
   non-negative code and data footprint, and a positive per-cycle step
   demand.
3. Compute what the engine currently holds: the store consumed by the
   loaded set and the step budget consumed by the running set.
4. Decide a load: refuse a stopped engine, an unsupported language, an
   unsupported version of a supported language, a procedure already
   loaded, a loaded count already at its limit, or a footprint past the
   free store, and name which one applies.
5. Decide a start: refuse a procedure that is not loaded, one already
   running, a running count already at its limit, and a per-cycle step
   demand past what the running set leaves free.
6. Apply a sequence of admission requests in order, because each
   accepted one changes the free store, the counts and the free step
   budget the next request is graded against.
7. Report utilisation as four fractions -- loaded, running, store and
   step budget -- so a refusal can be read against which resource ran
   out.

## Pitfalls

- Treating the loaded limit as the running limit. They are separate
  declarations, and the running one is usually the smaller.
- Grading admissions independently of order. Each acceptance moves the
  free resources, so a set that fits in one order does not in another.
- Ignoring the language version. A version mismatch fails later, deeper,
  and with a worse error than a refusal at load.
- Loading into a stopped engine. Nothing complains, and the procedure is
  not ready.
- Reporting utilisation as one number. Four resources bind
  independently, and a single figure hides which one refused the
  procedure.

## Behavior contract (gate 3)

The engine and procedure validation, store and step-budget accounting,
load and start admission with named refusal reasons, order-sensitive
sequencing and the four-fraction utilisation report are exercised by the
gate 3 contract test: scripts/test_e7041_obcp_engine.py against
scripts/e7041_obcp_engine_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e7041_obcp_engine.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
