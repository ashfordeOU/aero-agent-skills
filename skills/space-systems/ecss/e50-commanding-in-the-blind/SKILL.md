---
name: e50-commanding-in-the-blind
description: "Plan a telecommand session that must be uplinked with no return link under ECSS-E-ST-50C clause 5.4.7: group the command set by whether repetition is safe, so a non-idempotent or on-board-state-dependent command is caught before it goes up blind, derive the repetition count from the per-copy loss probability and the confidence the session must reach, size the repeated sequence against the uplink rate and the inter-command gap, and confirm it fits the window with the guard time held back. Use when early orbit, a safe mode, an occultation or a lost-attitude recovery leaves the ground commanding without telemetry. Trigger: ecss, e-st-50c-clause-5-4-7, commanding-in-the-blind, blind-uplink-repetition-count, telecommand-idempotency-grouping, blind-window-guard-time, no-return-link-commanding."
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
  tags: [ecss, e-st-50-communications-scope, e50-commanding-in-the-blind, e-st-50c-clause-5-4-7, commanding-in-the-blind, blind-uplink-repetition-count, telecommand-idempotency-grouping, blind-window-guard-time, no-return-link-commanding]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications -- Commanding in the Blind (space-systems/ecss/e50-commanding-in-the-blind)

Use when the task is clause 5.4.7 of ECSS-E-ST-50C: uplinking into a
window where nothing comes back. Launch and early orbit before the
downlink is established, a safe mode with the transmitter off, an
occultation, a recovery from an attitude that never points the antenna
at the ground. The session cannot be watched, so it has to be
survivable by construction.

## Domain quick reference

- Repetition is the only defence available. With no acknowledgement, the
  ground cannot retry on failure, so every copy that will ever be sent
  has to be sent inside the window. The repetition count is therefore a
  design quantity fixed before the window opens, not an operator
  reaction inside it.
- Repetition is only a defence for a command that survives it. A
  command that steps a counter, toggles a state or advances a sequence
  produces a different spacecraft each time it lands, so sending it four
  times to beat a lossy link is a hazard rather than a margin. The
  suitability grouping runs before the count is derived, because an
  unsuitable command makes the count meaningless.
- A command that branches on an on-board state is unsuitable even when
  it is idempotent. Blind means the ground does not know that state, so
  the command's own outcome is unknown, and repeating it neither
  confirms nor corrects anything.
- The count follows from the residual failure probability, not from
  habit. Accumulating the per-copy loss probability copy by copy says
  exactly how many are needed to reach the session's confidence, and it
  stays the same number on every machine because it never inverts a
  logarithm to get there.
- The window is not the usable window. Acquisition, sweep, ranging and
  the drop-out at the far edge are held back as guard time first, and
  the sequence is sized against what is left. Inter-command gaps are
  part of that size: with tens of repetitions, the gaps can outweigh the
  on-air time.

## Workflow

1. Validate the window and hold back the guard time; a guard that
   consumes the whole window is an input error, not a zero-length
   session.
2. Group the command set by blind suitability, requiring each record to
   declare idempotency and state dependence explicitly rather than
   inferring either from the command name.
3. Derive the repetition count by accumulating the residual failure
   probability until it reaches the allowed value, absorbing an exact
   landing on that value with a named tolerance instead of adding a
   copy.
4. Size the repeated sequence: total command bits times the count over
   the uplink rate, plus the inter-command gap across every slot
   boundary.
5. Compare the sized sequence with the usable window, treating an exact
   fit as a fit.
6. Report the grouping, the count, the achieved residual probability and
   the fit together, so a session that fails on suitability is not
   reported as a timing problem.

## Pitfalls

- Deriving the repetition count before grouping the commands. The count
  is only meaningful for commands that tolerate repetition, and deriving
  it first makes an unsuitable command look like a sized, planned item.
- Reading idempotency off the command name. A command called "set" can
  step a register and a command called "step" can be absolute; the
  record has to say which, and a missing flag is an input error.
- Sizing the sequence on on-air time alone. The gaps between slots scale
  with the number of commands times the repetition count, and they
  dominate the budget long before the bits do.
- Spending the whole window. Acquisition and the far-edge drop-out are
  not margin to be recovered; a sequence sized against the raw window is
  sized against time the link does not have.
- Adding one more copy when the residual probability lands on the
  allowed value. That is a representation question, handled by the
  tolerance inside the comparison; the confidence target stays as
  specified.

## Behavior contract (gate 3)

The window validation, suitability grouping, residual-probability
accumulation, repetition derivation, sequence sizing and the fit
comparison are exercised by the gate 3 contract test:
scripts/test_e50_commanding_in_the_blind.py against
scripts/e50_commanding_in_the_blind_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e50_commanding_in_the_blind.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
