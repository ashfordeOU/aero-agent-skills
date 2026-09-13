---
name: e2006-thruster-beam-neutralization
description: "Use when verify that the exhaust beam of an electric-propulsion thruster is neutralized by design under ECSS-E-ST-20-06C clause 11.2.2, so the space-charge potential of the platform stays low: categorize the thruster as dedicated-neutralizer, shared-neutralizer or self-neutralizing, balance emitted ion-beam-current against neutralizer-electron-current and charge-exchange-backflow, drive the residual net-emitted-current across the plasma-contact-conductance to obtain the floating-potential, check that potential and the neutralizer-coupling-voltage against their allowances, and reject a firing sequence that opens the beam before the electron-emitter has ignited. Trigger: ecss, e-st-20-electrical-scope, thruster-beam-neutralization, neutralizer-current-balance, net-emitted-current, plasma-contact-conductance, neutralizer-coupling-voltage, beam-neutralization-sequence, electric-propulsion-space-charge."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-thruster-beam-neutralization, neutralizer-current-balance, net-emitted-current, plasma-contact-conductance, neutralizer-coupling-voltage, beam-neutralization-sequence, electric-propulsion-space-charge]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging -- Thruster Beam Neutralization (space-systems/ecss/e2006-thruster-beam-neutralization)

Use when the task is the beam-neutralization requirement of
ECSS-E-ST-20-06C clause 11.2.2 -- showing that an electric-propulsion
thruster expels no net charge, so the space-charge-potential the firing
drives onto the platform stays inside the allowance the charging
analysis holds.

## Domain quick reference

- An ion thruster expels positive propellant ions. Left alone, that
  current strips positive charge from the platform and drives its
  floating-potential steeply negative until the ambient plasma
  re-balances it -- which is exactly the condition clause 11.2.2
  forbids by design. Neutralization is the design answer: an electron
  emitter (hollow-cathode neutralizer, or an integrated emitter on a
  self-neutralizing thruster) returns an electron current matched to
  the ion-beam-current.
- Three neutralization architectures appear in practice and each is
  categorized before the balance is struck: dedicated-neutralizer (one
  emitter per thruster), shared-neutralizer (one emitter serving a
  cluster, so an emitter outage removes several thrusters at once) and
  self-neutralizing (ions and electrons leave the same emitter, as on
  a field-emission or colloid device). An architecture outside that
  set is uncategorized and is rejected rather than assumed.
- The current balance is signed: net-emitted-current equals the
  ion-beam-current, minus the neutralizer-electron-current, minus the
  charge-exchange-backflow current that returns ions to the platform.
  A neutralization ratio (electron current over beam current) at or
  above unity is the electron-rich condition an operational thruster
  is flown in; below unity the beam is under-neutralized.
- The residual net-emitted-current does not float free: it is driven
  across the plasma-contact-conductance of the exposed conductive
  surfaces, and the quotient is the steady floating-potential of the
  platform. A small conductance (a well-insulated spacecraft) turns a
  modest current imbalance into a large potential, which is why the
  conductance is an input to the check and never assumed.
- Two design provisions sit alongside the balance. The
  neutralizer-coupling-voltage, the drop between emitter and ambient
  plasma, has its own allowance because a rising coupling voltage
  signals emitter degradation. And the firing sequence must ignite the
  emitter before the beam opens, with a stated lead time -- a beam
  opened first is an unneutralized beam for the duration of the lag.

## Workflow

1. Categorize the neutralization architecture of each thruster; reject
   an unrecognized architecture before any number is computed.
2. Strike the current balance: ion-beam-current minus
   neutralizer-electron-current minus charge-exchange-backflow gives
   the net-emitted-current; the electron-to-ion ratio gives the
   electron-rich verdict. A beam current that is zero or negative is
   not a firing thruster and is rejected as bad input.
3. Divide the net-emitted-current by the plasma-contact-conductance to
   obtain the signed floating-potential (positive net emission of
   positive charge drives the platform negative), then compare its
   magnitude against the allowance from the charging analysis.
4. Compare the neutralizer-coupling-voltage against its own allowance;
   a thruster with no coupling voltage on record is a finding, not a
   pass, because the provision was never evidenced.
5. Check the firing sequence: the emitter ignition instant plus the
   required lead must not fall after beam-on. Absent sequence data is
   again a finding rather than a silent pass.
6. Check the emitter inventory against the architecture: an
   architecture that needs an emitter and declares none is blocking; a
   single emitter is recorded as a single-string observation for the
   redundancy case, not as a breach of clause 11.2.2.
7. Aggregate per thruster and across the propulsion set; the set is
   neutralization-compliant only when every thruster carries an empty
   blocking-finding list.

## Pitfalls

- Reading a neutralization ratio of unity as proof and stopping there
  -- the ratio is dimensionless, while the potential the clause cares
  about comes from the residual current divided by the
  plasma-contact-conductance, so a nominally balanced pair of large
  currents can still leave an unacceptable potential.
- Dropping the charge-exchange-backflow term. Returning ions carry
  positive charge back to the platform and genuinely reduce the net
  emission; omitting them biases the computed potential and hides
  which way the imbalance actually points.
- Treating a shared-neutralizer cluster as if each thruster had its
  own emitter -- the emitter count is architecture-dependent, and a
  cluster on one emitter is a single-string case that the redundancy
  record has to state explicitly.
- Accepting a missing coupling voltage or a missing ignition sequence
  as "no violation found". Clause 11.2.2 is a design-provision
  requirement: an unevidenced provision is an open finding.
- Widening the potential allowance to absorb a case that lands a few
  representation bits over the limit. The logic already compares with
  a named closeness tolerance, so a physically compliant equality
  passes without the engineering limit being moved.

## Behavior contract (gate 3)

The architecture categorization, current balance, floating-potential,
coupling-voltage, ignition-sequence and emitter-redundancy logic is
exercised by the gate 3 contract test:
scripts/test_e2006_thruster_beam_neutralization.py against
scripts/e2006_thruster_beam_neutralization_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2006_thruster_beam_neutralization.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
