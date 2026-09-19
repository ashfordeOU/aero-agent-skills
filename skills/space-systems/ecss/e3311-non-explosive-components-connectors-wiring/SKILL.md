---
name: e3311-non-explosive-components-connectors-wiring
description: "Size and verify the connectors and firing-line wiring of an initiation subsystem against ECSS-E-ST-33-11C clauses 4.10.1 and 4.10.2. Build the loop resistance from both conductors and every contact, compute the current that actually reaches the bridgewire through the source resistance, and grade it against the all-fire current with the project margin, not against the no-fire bound. Invert the same model for the largest loop resistance and the smallest conductor cross-section that still fire. Assess the declared keying, twisting, shielding and segregation features alongside. Use when designing or reviewing an initiator harness. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, initiator-firing-line-wiring, eed-connector-anti-mismating-keying, firing-circuit-loop-resistance, all-fire-current-margin, firing-harness-segregation."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-non-explosive-components-connectors-wiring, initiator-firing-line-wiring, eed-connector-anti-mismating-keying, firing-circuit-loop-resistance, all-fire-current-margin, firing-harness-segregation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Non-Explosive Components, Connectors and Wiring (space-systems/ecss/e3311-non-explosive-components-connectors-wiring)

Use when the connectors and wiring that carry firing energy to an initiator
are being designed or reviewed under ECSS-E-ST-33-11C clauses 4.10.1 and
4.10.2 — the parts of the initiation chain that hold no energetic material
and are therefore the parts a harness engineer owns.

## Domain quick reference

- These clauses are about the boring half of the chain, which is the
  half that fails. The initiator is qualified hardware; the connector,
  the contacts and the copper between them are project design, and they
  are where a firing current goes missing.
- The bound that applies here is the all-fire current, not the no-fire
  current. No-fire is the safety case — the most energy that must not
  set the device off. All-fire is the functional case — the least that
  reliably does. They are different numbers used by different arguments,
  and swapping them inverts the conclusion.
- Resistance is a loop, not a run. Outgoing and return conductors both
  count, and a budget built on a single-conductor figure understates the
  harness by a factor of two.
- Contacts are resistance too, and they are the term that drifts. A
  connector pair is several milliohms when new and more after mating
  cycles and corrosion, so the budget carries the end-of-life contact
  figure rather than the datasheet one.
- Anti-mismating is a physical property, not a procedure. A firing
  connector that can be mated to a non-firing one will be, eventually,
  by someone tired; keying and a connector shell unique to the firing
  circuit are the controls that do not depend on attention.
- A firing line is a twisted, shielded pair bonded at both ends and
  routed away from the rest of the harness. Each of those is a coupling
  path closed, and each is cheap during design and impossible after
  integration.
- A feature not declared is absent. An initiation harness does not get
  the benefit of an assumption about what the drawing probably meant.

## Workflow

1. State the firing circuit end to end: source voltage, source
   resistance, run length, conductor cross-section, contact count and
   per-contact resistance, and the initiator bridgewire resistance.
2. Build the loop resistance from both conductors and every contact in
   the path, using the end-of-life contact figure.
3. Compute the current that actually reaches the bridgewire as a series
   divider across source, loop and bridgewire. The open-circuit source
   voltage is not what the initiator sees.
4. Grade that current against the all-fire current with the margin the
   project set, using a relative tolerance so a design sized to land on
   the margin is not decided by rounding.
5. Separate the two failure modes in the report: a line that does not
   reach the all-fire current at all is a different defect from one that
   reaches it without the required margin.
6. Where the margin is short, invert the same model: the largest loop
   resistance that works, and the smallest conductor cross-section that
   delivers it over this run with these contacts. Say plainly when no
   cross-section reaches it and the source or initiator has to change.
7. Check the declared physical features — keying, a connector unique to
   the firing circuit, twisting, shielding, shield bonding at both ends,
   segregation, contacts rated for the firing current — and treat an
   undeclared feature as absent.

## Pitfalls

- Grading the delivered current against the no-fire current. It is the
  safety bound, it is smaller, and using it makes an underfed firing
  line look compliant.
- Computing the harness as one conductor. The return path is real
  copper and doubles the term.
- Using the datasheet contact resistance. Contacts age, and a budget
  with no end-of-life allowance passes at delivery and fails after the
  fourth mate.
- Dividing the source voltage by the bridgewire resistance. The source
  resistance and the harness are in the same series loop, and ignoring
  them overstates the current by whatever they add.
- Treating anti-mismating as a procedural control. Procedures are
  executed by people at the end of a shift; keying is executed by the
  shell.
- Bonding a shield at one end only on a firing line. It is the right
  answer for a low-frequency signal cable and the wrong one here.
- Reporting margin short and stopping. The cross-section that fixes it
  is the same calculation read backwards, and a review without it just
  sends the problem around again.

## Behavior contract (gate 3)

Geometry, contact-count and margin validation, the two-conductor loop
with contact resistance, the series-divider delivered current, the
all-fire margin, the separation of a line that cannot fire from one
short of margin, the maximum-loop and minimum-cross-section inverses
each re-checked against the same model, the unreachable-margin case,
and the declared-feature screen are exercised by the gate 3 contract
test:
scripts/test_e3311_non_explosive_components_connectors_wiring.py
against
scripts/e3311_non_explosive_components_connectors_wiring_logic.py
(stdlib unittest, offline).
Run:
python3 scripts/test_e3311_non_explosive_components_connectors_wiring.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
