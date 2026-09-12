---
name: e20-reliable-insulation-applicability-scope
description: "Use when determine which spacecraft electrical nets the reliable-insulation provisions of ECSS-E-ST-20C clause 4.2.1.2.2 actually cover: categorize each net into its family (power distribution, ordnance, high voltage, signal, bonding), admit the always-in-scope families outright, otherwise test the net against the hazardous-energy thresholds on voltage, prospective fault power and stored energy, fold in the failure-severity rank and whether the net is a single-point path, mark a net indeterminate when its data is missing, and list in-scope nets carrying no declared reliable insulation. Trigger: ecss, e-st-20-electrical-scope, reliable-insulation-scope, critical-net-selection, hazardous-energy-threshold, ordnance-firing-line, high-voltage-net, single-point-failure-net."
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
  tags: [ecss, e-st-20-electrical-scope, e20-reliable-insulation-applicability-scope, reliable-insulation-scope, critical-net-selection, hazardous-energy-threshold, ordnance-firing-line, single-point-failure-net]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Design — Reliable Insulation, Applicability Scope (space-systems/ecss/e20-reliable-insulation-applicability-scope)

Use when the task is deciding the coverage of the reliable-insulation
provisions of ECSS-E-ST-20C clause 4.2.1.2.2 -- which critical nets
across the spacecraft electrical design must carry reliable
insulation, which are legitimately outside it, and which cannot be
decided yet because the data behind the decision is missing.

## Domain quick reference

- Scope is decided per net, not per harness or per unit. Each net is
  first placed in a family: power distribution (primary bus,
  secondary bus, battery main line, solar array string), ordnance
  (pyrotechnic firing line, deployment release line), high voltage
  (payload high-voltage line, electric propulsion line), signal
  (command net, telemetry sense line), or bonding (structure bond).
- Two groups are in scope on identity alone, with no numbers needed:
  the ordnance and high-voltage families, because an insulation
  defect there is an inadvertent initiation or an arc rather than a
  degraded function, and the primary bus and battery main line,
  because they are the only nets with the full source energy behind
  them at all times.
- Every other net earns its way in on evidence, from either of two
  independent directions. The energy direction: nominal voltage at or
  above the hazardous threshold, prospective fault power (voltage
  times available fault current) at or above its threshold, or stored
  energy at or above its threshold -- any one suffices. The
  criticality direction: a failure severity of critical or worse
  combined with the net being a single-point path, i.e. no redundant
  route carries the function if this net is lost.
- A net whose voltage, fault current, stored energy or severity is
  simply not on record is not out of scope -- it is indeterminate,
  and the indeterminate list is a finding against the design data,
  not a pass. Separately, a net decided in scope but with no reliable
  insulation declared is a coverage gap: the scope decision was made
  and then not implemented.

## Workflow

1. Categorize every net by type into its family; reject an
   unrecognised net type before it reaches a decision.
2. Admit the always-in-scope groups directly: any ordnance or
   high-voltage family net, and any primary bus or battery main line.
   Record the identity driver and move on.
3. For every remaining net, evaluate the hazardous-energy drivers:
   voltage against the voltage threshold, voltage times available
   fault current against the fault-power threshold, and stored energy
   against the stored-energy threshold. Any driver present puts the
   net in scope.
4. Evaluate the criticality direction: rank the failure severity and
   test it against the critical rank, combined with the single-point
   flag. Both together put the net in scope.
5. Where the electrical data or the severity needed for steps 3 and 4
   is absent, mark the net indeterminate rather than out of scope,
   and carry it as a data finding.
6. Across the reviewed set, list every in-scope net with no declared
   reliable insulation as a coverage gap. The scope review is
   complete only when the indeterminate list and the gap list are
   both empty.

## Pitfalls

- Deciding scope on the unit rather than the net. One connector can
  carry a firing line and a housekeeping sense line; the firing line
  is in scope and the sense line may not be, and a unit-level verdict
  loses that distinction in the direction that hurts.
- Reading a low nominal voltage as safe. A 28 V battery main line
  with a high available fault current clears the fault-power
  threshold even though it never approaches the voltage threshold --
  the drivers are independent and any one suffices.
- Treating a missing number as a zero. An absent stored-energy or
  severity entry means the assessment was not done; recording it as
  out of scope converts a data gap into a silent exemption.
- Excluding a signal net because it carries no power. A command net
  that is a single-point path to a critical function is in scope on
  the criticality direction regardless of its energy.
- Closing the review once the scope list exists. A net in scope
  without declared reliable insulation is the gap the clause is
  there to prevent, and it is visible only when the declaration is
  checked against the decision.

## Behavior contract (gate 3)

The net categorization, hazardous-energy driver, severity-rank,
per-net applicability and coverage-gap logic is exercised by the gate
3 contract test:
scripts/test_e20_reliable_insulation_applicability_scope.py against
scripts/e20_reliable_insulation_applicability_scope_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e20_reliable_insulation_applicability_scope.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
