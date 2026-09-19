---
name: e3311-power-plug-receptacle-provisions
description: "Evaluate the power provisions, arm-plug receptacle and safe/arm/test plug set of an explosive subsystem against ECSS-E-ST-33-11C clauses 4.10.6 to 4.10.10. Use when the task is showing that the firing source still delivers the all-fire current once source and harness resistance have taken their share and several initiators fire in parallel, that the arm receptacle is accessible, keyed, shorting when unmated, retained and left until last, and that the safe, arm and test plugs carry distinct keying and identification colours with a mating matrix that keeps the test plug out of the arm receptacle. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, initiator-firing-power-provision, arm-plug-receptacle-provisions, safe-arm-test-plug-keying, plug-cross-mating-prevention, firing-line-voltage-drop-budget."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-power-plug-receptacle-provisions, initiator-firing-power-provision, arm-plug-receptacle-provisions, safe-arm-test-plug-keying, plug-cross-mating-prevention, firing-line-voltage-drop-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Power, Plug and Receptacle Provisions (space-systems/ecss/e3311-power-plug-receptacle-provisions)

Use when the task is the pad-side half of ECSS-E-ST-33-11C clauses
4.10.6 to 4.10.10 -- the power that reaches the bridgewires, the
receptacle the arming plug goes into, and the family of plugs that
take turns in it.

## Domain quick reference

- The three parts are independent. A firing source can be generous and
  the plug keying still allow a test plug into the arm receptacle; a
  receptacle can carry every provision and the harness still starve
  the last initiator in the string. Each is graded on its own and the
  overall verdict is the conjunction.
- Firing power is not a datasheet lookup. The bridges sit in parallel,
  so the loop resistance is the source plus the harness plus the
  bridge resistance divided by the number of initiators firing at
  once. Adding initiators raises the total current and lowers the
  current each bridge receives, which is why a design qualified on one
  device can fail on four.
- The all-fire current is what the circuit must deliver on command, so
  it is graded with a margin above it rather than as an equality. The
  margin is declared policy, not a physical constant.
- The voltage-drop fraction is a separate quantity from the current
  margin and can fail while the current passes. It answers a different
  question: how much of the source is being spent on wire rather than
  on the device, and therefore how much head-room is left when the
  harness ages or a contact resistance grows.
- The arm-receptacle provisions are a closed set: accessible, keyed,
  shorting when unmated, retained, and armed last. A silent entry
  means nobody looked, so an undeclared provision is rejected rather
  than assumed.
- Keying, identification colour and the mating matrix are three
  separate defences against the same mistake. Distinct colours let a
  technician catch a wrong plug by eye; distinct keying stops the
  wrong plug entering at all; the mating matrix is where an
  inadvertently permissive keying shows up as a test plug that fits
  the arm receptacle.

## Workflow

1. Take the all-fire current and the number of initiators that fire
   together first, because both the delivered current and the loop
   resistance depend on the count and a case that omits it cannot be
   graded.
2. Build the loop: source resistance, harness resistance, bridge
   resistance over the initiator count. Divide the source voltage by
   it for the total current, then by the count again for the current
   each bridge actually receives.
3. Grade that delivered current against the all-fire current times the
   declared margin, and treat a design sitting exactly on the
   requirement as compliant rather than failing it on representation
   error.
4. Compute the drop fraction separately -- series resistance over loop
   resistance -- and grade it against its own limit.
5. Walk the arm-receptacle provisions and name each one absent.
6. Read the plug set: reject a set missing a kind, group the keying
   codes and the identification colours to find sharing, then check
   each plug against the receptacle it is allowed into and name any
   extra target it can reach.
7. Close with the overall verdict and the list of parts that produced
   it.

## Pitfalls

- Sizing the firing source for one initiator and flying four. The
  parallel bridges pull the loop resistance down, so the source
  delivers more total current while each device gets less, and the
  string that qualified on the bench is the one that misfires.
- Grading delivered current against the no-fire current. The no-fire
  current is the level everything unintended must stay under; the
  all-fire current is the level the firing circuit has to reach, and
  swapping them turns a safety limit into a performance target.
- Reading a healthy current margin as a healthy design. A loop that
  spends a third of its voltage on wire meets the current requirement
  today and loses it to the first contact that corrodes.
- Taking an undeclared receptacle provision as satisfied. The set is
  closed, so silence is a gap in the evidence, and a receptacle that
  does not short the firing line when unmated fails in exactly the
  configuration nobody inspected.
- Treating distinct colours as sufficient separation. Colour is a
  visual aid that fails in a dark bay with a gloved technician;
  keying is the control, and the mating matrix is the evidence that
  the keying was actually assigned the way the drawing claims.
- Allowing the test plug a second mating target for convenience. Every
  extra target is a path by which a ground-support item reaches a
  flight firing line, and it is exactly the path the arm receptacle
  exists to close.
- Comparing margins by bare arithmetic. The current margin and the
  drop fraction are both ratios, so a design sized exactly onto its
  requirement can land a few units in the last place below it; the
  comparison absorbs that while the requirement stays untouched.

## Behavior contract (gate 3)

The loop-resistance and delivered-current chain, the drop-fraction
limit, the receptacle provision walk, the keying, colour and mating
matrix checks and the overall verdict are exercised by the gate 3
contract test:
scripts/test_e3311_power_plug_receptacle_provisions.py against
scripts/e3311_power_plug_receptacle_provisions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3311_power_plug_receptacle_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
