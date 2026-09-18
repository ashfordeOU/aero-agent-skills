---
name: e50-command-encryption
description: "Evaluate whether a spacecraft telecommand uplink carries the command protection of ECSS-E-ST-50C clause 5.4.6: group the uplink dictionary by hazard category into the commands owing authentication alone and the ones owing authentication with encryption, reduce the declared algorithm, key length and block size to an effective strength in bits, hold that against the floor the strictest protected category sets, and budget the key schedule by counting commands between rotations against the per-key usage limit. Use when a command link, a key plan or a security unit is assessed before flight. Trigger: ecss, e-st-50c-clause-5-4-6, telecommand-command-encryption, telecommand-authentication-duty, effective-key-strength-bits, telecommand-key-rotation-budget, hazardous-command-protection."
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
  tags: [ecss, e-st-50-communications-scope, e50-command-encryption, e-st-50c-clause-5-4-6, telecommand-command-encryption, telecommand-authentication-duty, effective-key-strength-bits, telecommand-key-rotation-budget, hazardous-command-protection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications -- Telecommand Command Encryption (space-systems/ecss/e50-command-encryption)

Use when the task is clause 5.4.6 of ECSS-E-ST-50C: deciding which
commands on an uplink have to be protected, and whether the protection
actually fitted is strong enough to be worth fitting. Two normative
items sit here -- one that binds the duty to the command, one that binds
the strength to the duty -- and a link can satisfy the first while
failing the second.

## Domain quick reference

- The duty follows the command, not the link. A telemetry dump request
  and a pyrotechnic arming command travel the same carrier, and only one
  of them can put the spacecraft or its operators at risk if it is
  replayed, forged or simply read by somebody watching the uplink.
- Authentication and encryption answer different questions.
  Authentication says the command came from the ground that owns the
  spacecraft; encryption says nobody else learned what it was. A
  hazardous command needs the first. A command whose content is itself
  the intelligence -- a manoeuvre, a key load, a payload tasking --
  needs both, so encryption is not a stronger grade of authentication
  but a separate duty.
- A declared key length is not the strength delivered. A two-key triple
  construction loses half its nominal length to a meet-in-the-middle
  attack, and any construction is capped by twice its block size, so a
  suite advertised at 168 bit can be sitting well under a 112 bit floor.
  The number that has to clear the floor is the reduced one.
- Key exhaustion is the failure an adequate algorithm hides. A rotation
  interval is a calendar quantity; a per-key usage limit is a count of
  protected commands. Multiplying the command rate by the interval says
  whether the schedule fits, and a busy commissioning phase can exhaust
  a key that a cruise-phase rate would never have reached.
- An uplink that protects everything is not automatically safe. If no
  command in the dictionary demands protection, the hazard
  categorization is more likely incomplete than the dictionary benign,
  and that is a finding about the analysis rather than about the link.

## Workflow

1. Validate the uplink dictionary: every command carries a name and a
   hazard category, names are unique, and an unrecognised category is an
   input error rather than a default to routine.
2. Group the dictionary by protection duty and retain the strictest
   strength floor any command in it demands.
3. Reduce the declared suite to an effective strength: scale the key
   length by the structural loss of the algorithm family, then cap the
   result at twice the block size.
4. Compare the protection actually provided against the strictest duty
   demanded, treating the duties as an ordered ladder so encryption
   satisfies an authentication-only demand and not the reverse.
5. Compare the effective strength against the retained floor.
6. Budget the key schedule: command rate times rotation interval against
   the per-key limit, absorbing an exact landing on the limit with a
   named tolerance rather than by raising the limit.
7. Report the grouping, the two verdicts and the key budget together
   with an explicit finding list, so a link that fails on one axis is
   not reported as failing on all three.

## Pitfalls

- Reporting a single pass/fail for the link. The duty check, the
  strength check and the key budget fail independently, and a fix aimed
  at the wrong one leaves the link exactly as exposed as it was.
- Reading encryption as a superset of authentication. A stream cipher
  with no integrity tag hides the command and still lets a forged one
  through, so the ladder used here orders duties, it does not merge
  them.
- Clearing the floor with the declared key length. The nominal number is
  the one on the datasheet; the reduced number is the one an attacker
  faces, and the gap between them is exactly where an under-strength
  suite passes review.
- Trusting a rotation interval on its own. An interval says how often
  keys change, not how many commands each key protected, and the two
  only agree at the command rate that was assumed when the interval was
  set.
- Treating a usage ratio that lands on unity as an overrun. That is a
  representation question, handled by the tolerance inside the
  comparison; the per-key limit stays as specified.

## Behavior contract (gate 3)

The hazard grouping, duty ladder, effective-strength reduction, block
cap, key-budget ratio and the finding list are exercised by the gate 3
contract test:
scripts/test_e50_command_encryption.py against
scripts/e50_command_encryption_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e50_command_encryption.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
