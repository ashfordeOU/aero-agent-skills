---
name: e20-battery-safety-management
description: "Use when manage the safety case for a spacecraft battery under ECSS-E-ST-20C clause 5.6.5.2 and the product assurance space-safety route: categorize each battery hazard by severity and likelihood, scale the control strategy it earns (independent inhibit count, containment provision, cell-to-cell propagation barrier), count only the inhibits that are genuinely independent and verifiable towards the achieved failure tolerance, compute the thermal margin between the predicted cell temperature and runaway onset, place the residual risk in an acceptance band, and refuse to close the case while a hazard lacks its product-assurance safety requirement link. Trigger: ecss, e-st-20-electrical-scope, battery-safety-case, battery-hazard-severity, independent-inhibit-chain, failure-tolerance-sizing, thermal-runaway-propagation-barrier, residual-risk-band, product-assurance-safety-link."
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
  tags: [ecss, e-st-20-electrical-scope, e20-battery-safety-management, battery-safety-case, independent-inhibit-chain, failure-tolerance-sizing, thermal-runaway-propagation-barrier, residual-risk-band]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Battery Safety Management (space-systems/ecss/e20-battery-safety-management)

Use when the task is the ECSS-E-ST-20C clause 5.6.5.2 case: battery
safety is not managed inside the electrical design alone, it is
managed under the product assurance route for space safety, and this
leaf is the bridge -- it turns a battery hazard list into sized
controls, an achieved failure tolerance, a residual risk band and a
traceable link back to the owning safety requirement.

## Domain quick reference

- The clause is a delegation, not a design rule. The electrical
  discipline owns the battery; the space-safety discipline owns the
  method by which its hazards are controlled and accepted. Every
  hazard therefore carries two things a purely electrical assessment
  would omit: a severity on the safety scale, and a reference to the
  safety requirement that owns it. A hazard with no such reference is
  an open finding even when its inhibit chain is perfect.
- Severity sizes the control strategy. Take the baseline as three
  independent inhibits for a catastrophic hazard (tolerant to two
  failures), two for a critical hazard (tolerant to one), one for a
  marginal hazard and none for a negligible one.
- Hazard family then tailors that baseline in two ways. A hazard
  controlled by containment rather than by interruption -- electrolyte
  leakage, overpressure rupture -- trades one inhibit for a containment
  provision, which is then mandatory. A hazard that can propagate from
  cell to cell -- thermal runaway, internal short circuit -- demands a
  physical propagation barrier on top of its inhibits once it reaches
  critical severity.
- Only an inhibit that is both independent of its neighbours and
  verifiable counts. A chain of three inhibits sharing one command
  path, or one that cannot be shown to be in place, delivers less
  tolerance than its length suggests. Achieved failure tolerance is
  the effective count minus one, never below zero.
- The propagation barrier is graded numerically: the margin between
  the highest predicted cell surface temperature and the runaway onset
  temperature, compared against the required margin. A barrier that is
  absent fails regardless of how large the margin is, and a margin
  exactly at the requirement passes.
- Residual risk is the product of the severity and likelihood ordinals
  on a 1..20 index, banded into acceptable, acceptable-with-review,
  undesirable and unacceptable. An unacceptable band is itself a
  finding -- controls sized correctly do not license a risk the
  programme has not accepted.

## Workflow

1. Validate the battery record (runaway onset temperature, worst-case
   predicted cell temperature, required thermal margin, presence of a
   cell-to-cell barrier, the governing space-safety standard
   reference) and reject a missing or blank safety standard link.
2. Validate each hazard: known hazard family, severity and likelihood
   on the scales, a recognized verification method, a boolean
   containment flag, and the owning safety requirement reference.
3. Size the required controls from severity plus hazard family:
   independent inhibit count, containment demand, barrier demand.
4. Evaluate the declared inhibit chain, discounting every inhibit that
   is not independent or not verifiable, and record each discount as
   its own finding rather than folding it into the count silently.
5. Where a barrier is demanded, compute the thermal margin and grade
   it against the required margin.
6. Compute the risk index and band, add a finding for an unacceptable
   band, and aggregate: the safety case closes only when no hazard
   carries an open finding.

## Pitfalls

- Counting inhibits by how many are drawn rather than by how many are
  independent. Three relays behind one command decoder are one
  inhibit, and a chain that cannot be verified in the as-flown
  configuration contributes nothing at all.
- Sizing controls from the failure's probability instead of its
  consequence. Severity sets the required tolerance; likelihood only
  enters the residual-risk band afterwards. A rare catastrophic hazard
  still earns its full inhibit count.
- Treating a containment-family hazard as under-controlled because it
  carries fewer inhibits. The trade is deliberate -- but only if the
  containment provision genuinely exists; drop the provision and the
  hazard is short of controls on both routes at once.
- Assuming a cell-to-cell barrier is sufficient because it is present.
  The barrier is graded by thermal margin; a present barrier with the
  predicted cell temperature sitting close to runaway onset does not
  meet the requirement.
- Closing the safety case on control adequacy alone while a hazard has
  no owning safety requirement. The clause delegates management of
  battery safety to the product assurance route, so an untraced hazard
  is outside that route and cannot be declared controlled.

## Behavior contract (gate 3)

Hazard and battery validation, severity and likelihood categorization,
control sizing, inhibit-chain evaluation, propagation-margin
arithmetic, risk banding and safety-case aggregation are exercised by
the gate 3 contract test: test_e20_battery_safety_management.py
against e20_battery_safety_management_logic.py (stdlib unittest,
offline, deterministic). Run:
`python3 scripts/test_e20_battery_safety_management.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
