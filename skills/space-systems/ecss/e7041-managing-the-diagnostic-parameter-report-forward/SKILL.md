---
name: e7041-managing-the-diagnostic-parameter-report-forward
description: "Evaluate the diagnostic parameter report forward-control configuration of the real-time forwarding control service under ECSS-E-ST-70-41C clause 6.14.3.6. Use when the task is choosing which diagnostic parameter reports reach the ground in real time and what they cost: adding and deleting diagnostic structure identifiers per application process, refusing an identifier that application process never defined, holding an all-structures wildcard against the entries it subsumes, summing the reciprocal collection intervals of the selection into a forwarded packet rate, and grading that rate against the real-time downlink budget. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, diagnostic-forward-control, diagnostic-report-structure-selection, forwarded-diagnostic-packet-rate, real-time-downlink-rate-budget, dormant-diagnostic-selection."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-managing-the-diagnostic-parameter-report-forward, diagnostic-forward-control, diagnostic-report-structure-selection, forwarded-diagnostic-packet-rate, real-time-downlink-rate-budget, dormant-diagnostic-selection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Diagnostic Parameter Report Forward Control (space-systems/ecss/e7041-managing-the-diagnostic-parameter-report-forward)

Use when the task is the diagnostic parameter report forward-control
configuration of ECSS-E-ST-70-41C clause 6.14.3.6 -- the per-structure
selection that decides which diagnostic parameter reports the real-time
forwarding control service passes on, and the downlink load that
selection creates.

## Domain quick reference

- Diagnostic parameter reports share one report type and one message
  subtype per application process, so they are separated by the
  diagnostic structure they came from, exactly as housekeeping reports
  are. The bookkeeping is the same shape: per application process, a
  set of structure identifiers, or an all-structures wildcard.
- The arithmetic is not the same. Diagnostic structures exist to sample
  quickly while an anomaly is being chased, so their collection
  intervals are short and a handful of them can put more packets on the
  real-time path than the whole housekeeping set. Each enabled
  structure contributes the reciprocal of its collection interval, and
  the selection's rate is the sum over the structures actually defined
  and collected.
- A selection on a structure whose collection is currently disabled is
  legitimate. Arming the forwarding ahead of enabling the collection is
  ordinary operations, and the selection simply contributes nothing
  until the collection starts. It is reported as dormant so nobody
  reads the quiet downlink as a fault, and so nobody is surprised by
  the rate step when the collection is enabled.
- A structure identifier means something only inside the application
  process that defines it, and an identifier that application process
  never defined cannot be selected. A selection whose definition was
  deleted afterwards is stale: it forwards nothing now and would start
  forwarding again if the number were reused.
- The rate is a sum of reciprocals of measured intervals, so a
  selection sitting exactly on its budget can land a few units in the
  last place above it. The comparison absorbs that with a named
  tolerance far below any realisable interval; the budget itself is
  never widened.

## Workflow

1. Validate the catalogue: every structure carries a positive
   collection interval and a boolean collection state. A missing or
   non-positive interval is an input error, not a structure that
   produces nothing.
2. Validate each request item and reject an application process the
   service does not control, before any catalogue lookup.
3. Reject an identifier the catalogue does not define under that item's
   own application process.
4. Apply the add: the wildcard clears what it subsumes, an identifier
   already selected or already covered by a wildcard is rejected, and
   the sizing limits become per-item rejections.
5. Apply the delete: an application process entry takes everything
   under it, an absent identifier is rejected, and a partial delete
   inside a wildcard is refused.
6. Resolve the selection against the live catalogue, sum the reciprocal
   intervals of the enabled structures, and compare the total with the
   budget through the named tolerance.
7. Report the configuration sorted, with the rate, the margin, and the
   dormant and stale selections listed separately from the rejections.

## Pitfalls

- Counting a dormant structure in the forwarded rate. The budget then
  looks spent on traffic that does not exist, and the real step arrives
  unbudgeted when the collection is enabled.
- Sizing the diagnostic selection from the housekeeping experience. The
  intervals are shorter by design, and a selection that looks small in
  structure count can be large in packets per second.
- Comparing the rate against the budget with a strict inequality on a
  floating-point sum. A selection built to sit exactly on budget then
  fails or passes depending on the order the reciprocals were added.
- Expanding the all-structures wildcard at the moment it is set. A
  diagnostic structure defined mid-investigation would not be
  forwarded, which defeats the reason the wildcard was chosen.
- Dropping a stale selection when its definition is deleted. Reusing
  the identifier later silently restores forwarding that no operator
  requested.

## Behavior contract (gate 3)

The catalogue validation, controlled-list check, undefined-structure
refusal, wildcard subsumption, partial-delete refusal, reciprocal-rate
sum, tolerance-bounded budget comparison and the dormant and stale
selection findings are exercised by the gate 3 contract test:
scripts/test_e7041_managing_the_diagnostic_parameter_report_forward.py
against
scripts/e7041_managing_the_diagnostic_parameter_report_forward_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_managing_the_diagnostic_parameter_report_forward.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
