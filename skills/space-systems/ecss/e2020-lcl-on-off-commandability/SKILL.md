---
name: e2020-lcl-on-off-commandability
description: "Verify that a latching or high power current limiter accepts external commands to switch its output on and off, per clause 5.2.6.1.1 of ECSS-E-ST-20-20C. Use when an LCL or HPC channel definition has to be graded before its command interface is frozen. Confirm that both an on command and an off command exist, that each reaches the channel from an external source rather than internal logic alone, and that the declared pulse width clears the minimum the channel accepts. Then run command sequences through an off, on and latched-off state machine, including commands issued while the channel sits latched after an overcurrent, and report every command the channel would ignore. Trigger: ecss, e-st-20-20c, lcl-on-off-commandability, latching-current-limiter-command-interface, high-power-limiter-command, lcl-command-pulse-width, lcl-latched-state-command-authority, external-limiter-command-source."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-20c, e2020-lcl-on-off-commandability, lcl-on-off-commandability, latching-current-limiter-command-interface, high-power-limiter-command, lcl-command-pulse-width, lcl-latched-state-command-authority, external-limiter-command-source]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply — Limiter On/Off Commandability (space-systems/ecss/e2020-lcl-on-off-commandability)

Use when the task is clause 5.2.6.1.1 of ECSS-E-ST-20-20C: a latching current
limiter and a high power limiter each accept a command from outside the
channel to switch their output on and to switch it off. This leaf grades a
declared command interface and then demonstrates it by running the channel's
output state machine.

## Domain quick reference

- The clause is about two commands, not one switch. On and off are separate
  entries in the interface, each with its own source, pulse and authority, and
  a channel can implement one properly and the other not at all.
- External is the operative word. A channel whose off command exists only as
  an internal protective action — the limiter opening itself on overcurrent —
  has no commandability; the command has to be reachable from outside the
  channel, from the platform's command chain.
- A command is a pulse with a width, and the channel accepts it only above a
  minimum. A pulse specified below that minimum is an interface that looks
  complete on paper and drops commands in flight, which is why the width is
  graded against the channel's accepted minimum rather than assumed adequate.
- The latched state is where commandability is quietly lost. A latching
  limiter that has tripped on overcurrent sits latched off; the off command
  has to hold authority there so the channel can be secured, and the on
  command has to hold authority there so the channel can be restored. An
  interface that honours both only from the nominal states passes a careless
  review and strands the channel after its first trip.
- The two latched cases are independent and have to be run independently. A
  single sequence that issues off then on out of the latched state leaves that
  state on the first command, so the second command is no longer testing what
  it appears to test.
- The categories matter. Retriggerable and foldback limiters regulate and
  recover by themselves, so they fall outside this clause; grading one against
  it and reporting a failure is a scope error, and the result is reported as
  out of scope instead.

## Workflow

1. Normalise the limiter category and decide whether the clause applies;
   report an out-of-scope category rather than failing it.
2. Validate the interface: one entry per command name, a recognised source, a
   positive pulse width, an authority list of recognised output states, and a
   positive accepted minimum pulse.
3. Grade presence: both the on command and the off command have to exist.
4. Grade reachability: each command's source has to be external, or external
   as well as internal; internal only is a finding.
5. Grade the pulse: the declared width has to clear the accepted minimum, with
   an exact equality at the bound absorbed by a named tolerance rather than by
   moving the minimum.
6. Grade authority: the on command from the off state, the off command from
   the on state, and both from the latched state.
7. Demonstrate rather than assert. Run three sequences — the nominal on, off,
   on cycle, securing a latched channel, and restoring a latched channel —
   and record for each command whether it was honoured and why not.
8. Return the verdict with the traces, the pulse margins and every command the
   channel would ignore.

## Pitfalls

- Reading the protective trip as the off command. The limiter opening itself
  on overcurrent is a protection function; the clause asks for a command the
  outside world issues, and the two are satisfied by different hardware.
- Accepting an interface that lists a command without a source. An unsourced
  command cannot be shown to be reachable from outside, and defaulting it to
  external is how an internal-only interface passes.
- Ignoring the pulse width because the command exists. A width below the
  channel's accepted minimum makes the command unreliable in exactly the
  situations it is needed in.
- Grading the latched state with one sequence. Issuing off then on out of the
  latched state exercises the latched case once; the restore command is then
  acting from the off state and the finding disappears.
- Assuming a channel that turns on can be turned off. Authority is per command
  and per state, and an off command with no authority in the latched state
  leaves an operator no way to secure a channel that has already tripped.
- Failing a retriggerable or foldback limiter against this clause. Those
  categories recover on their own and are outside it; the honest result is an
  out-of-scope report, not a non-compliance.

## Behavior contract (gate 3)

The category and state normalisation, interface validation, pulse-margin
comparison with its bound-equality tolerance, source reachability, per-state
command authority, the output state machine, the three demonstration runs and
the verdict ladder — compliant, non-compliant, out of scope — are exercised by
the gate 3 contract test:
scripts/test_e2020_lcl_on_off_commandability.py against
scripts/e2020_lcl_on_off_commandability_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e2020_lcl_on_off_commandability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
