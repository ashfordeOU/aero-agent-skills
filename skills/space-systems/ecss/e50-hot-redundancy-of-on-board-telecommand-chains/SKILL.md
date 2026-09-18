---
name: e50-hot-redundancy-of-on-board-telecommand-chains
description: "Assess whether a spacecraft's on-board telecommand receiving chains hold the hot redundancy of ECSS-E-ST-50C clause 5.4.9: validate each chain end to end across the antenna, receiver, demodulator and decoder roles, decide which chains are receptive right now rather than after a command, intersect the element sets of those hot chains to expose anything common to all of them, and report how many element failures would sever command authority. Use when a receiving architecture, a cross-strap map or a safe-mode recovery path is reviewed. Trigger: ecss, e-st-50c-clause-5-4-9, telecommand-chain-hot-redundancy, on-board-receiving-chain-completeness, command-authority-severing-depth, telecommand-chain-common-element, commanded-activation-receiver-finding."
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
  tags: [ecss, e-st-50-communications-scope, e50-hot-redundancy-of-on-board-telecommand-chains, e-st-50c-clause-5-4-9, telecommand-chain-hot-redundancy, on-board-receiving-chain-completeness, command-authority-severing-depth, telecommand-chain-common-element, commanded-activation-receiver-finding]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications -- Hot Redundancy of On-Board Telecommand Chains (space-systems/ecss/e50-hot-redundancy-of-on-board-telecommand-chains)

Use when the task is clause 5.4.9 of ECSS-E-ST-50C: establishing that
the path an uplinked command takes from antenna to decoder output exists
in more than one copy, and that every copy is already listening. The
failure this guards against is circular -- a spacecraft that has lost
command authority cannot be commanded to restore it.

## Domain quick reference

- Redundancy that has to be switched on is not redundancy for this
  function. A cold spare receiver is a spare for a receiver failure; it
  is nothing at all for a loss of command authority, because the switch
  command has no path to reach it. Hot means powered, enabled and
  already receptive with no ground action.
- A chain is only a chain end to end. Antenna, receiver, demodulator and
  decoder each have to be present; a path with a healthy antenna and no
  decoder terminates in nothing, and counting it toward the hot total
  overstates the architecture by a whole chain.
- Chain count is the wrong number on its own. Two chains sharing one
  antenna, one diplexer or one power converter are severed by a single
  element failure, so the quantity that means something is the number of
  element failures it takes to sever command authority -- one when any
  element is common to every hot chain, otherwise the hot chain count.
- The common element is found by intersecting identifiers, not by
  comparing roles. Two chains both have a receiver; whether they have
  the same receiver is what decides the outcome, and only the identifier
  says so.
- A chain excluded from the hot set should be reported with its reason.
  Unpowered, disabled, incomplete and command-activated are four
  different design conversations, and collapsing them into a single hot
  count loses the one thing the reviewer needs.

## Workflow

1. Validate every chain: a name, a non-empty element list, explicit
   powered and enabled flags, and an activation mode stated as always-on
   or commanded rather than inferred.
2. Validate every element: a known role and a non-empty identifier, with
   two elements in the same role inside one chain refused as a modelling
   error.
3. Mark each chain complete or name the roles it is missing.
4. Decide hotness: powered, enabled, complete and always-on. All four,
   because any one of them failing makes the chain unavailable at the
   moment command authority is lost.
5. Intersect the element identifiers of the hot chains and report every
   identifier common to all of them.
6. Compute the severing depth: zero with no hot chain, one when a common
   element exists, otherwise the hot chain count.
7. Compare the hot count against the required minimum and report the
   verdict with a finding per excluded chain and a finding per common
   element.

## Pitfalls

- Counting a cold spare toward the hot total. It restores a receiver
  after a receiver failure and restores nothing after a loss of command
  authority; the two cases are not interchangeable.
- Judging redundancy by chain count. Two chains through one antenna are
  one failure from silence, and only the element intersection exposes
  that.
- Comparing roles instead of identifiers when looking for the common
  element. Every chain has a receiver; the question is whether it is the
  same unit.
- Accepting a partial chain because its elements are healthy. A missing
  decoder is not a degraded chain, it is an absent one, and it must not
  be carried into the hot count.
- Reporting a single hot count with the reasons discarded. Unpowered,
  disabled, incomplete and command-activated lead to four different
  fixes, and the finding list keeps them apart.

## Behavior contract (gate 3)

The chain and element validation, completeness check, hotness rule,
element intersection, severing-depth computation and the per-chain
finding list are exercised by the gate 3 contract test:
scripts/test_e50_hot_redundancy_of_on_board_telecommand_chains.py
against
scripts/e50_hot_redundancy_of_on_board_telecommand_chains_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e50_hot_redundancy_of_on_board_telecommand_chains.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
