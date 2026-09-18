---
name: e50-command-authentication
description: "Evaluate whether a telecommand may be acted on under the command authentication obligation of ECSS-E-ST-50C clause 5.4.5: decide from policy whether this command needs authentication at all, check the key is still valid at this command counter, separate a replayed counter and one too far ahead to trust from a genuine advance, then compare the carried tag with the derived one in constant time and report which of those steps refused the command. Use when an uplink must resist replay, spoofing or an expired key. Trigger: ecss, e-st-50c-communications-scope, telecommand-authentication, command-replay-protection, uplink-authentication-tag, command-counter-window, authentication-key-validity, spoofed-telecommand-refusal."
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
  tags: [ecss, e-st-50c-communications-scope, e50-command-authentication, telecommand-authentication, command-replay-protection, uplink-authentication-tag, command-counter-window, authentication-key-validity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Command Authentication (space-systems/ecss/e50-command-authentication)

Use when the task is the single obligation of ECSS-E-ST-50C clause 5.4.5 —
that where command authentication is required, a command is acted on only
when it is shown to come from an authorized source — and the question is what
the receiving end must check before it acts.

## Domain quick reference

- A matching tag is necessary and not sufficient. A tag copied from a
  command sent an hour ago matches perfectly, which is why the counter is
  part of what is authenticated and part of what is checked.
- The counter check has two sides and only one is obvious. A counter at
  or below the last accepted one is a replay; a counter far above it is
  an attempt to push the receiver's state somewhere it cannot be brought
  back from, and a window is what keeps a lost command from locking the
  link out.
- Key validity is not the same question as tag correctness. A retired key
  still produces tags that verify against itself, so the validity range
  has to be tested before the tag, or a compromised old key stays useful
  forever.
- The tag has to cover everything that must not change: the key in use,
  the counter, and the command content. A tag over the content alone can
  be lifted onto a different counter, and a tag over the counter alone
  can be lifted onto a different command.
- Comparison is a side channel unless it is written not to be. An
  early-exit comparison reveals how many leading octets were right, which
  is enough to recover a tag one octet at a time.
- Authentication that is not required is not a reason to refuse. A
  command outside the protected set that arrives with a tag is still a
  valid command, and the tag is recorded rather than held against it.

## Workflow

1. Resolve policy first: is this command one that may only be acted on
   when authenticated. That answer decides what an absent tag means.
2. With no tag presented, refuse a protected command and accept an
   ordinary one, saying which rule applied.
3. Resolve the key named by the command. An unresolvable key is its own
   refusal reason, distinct from a tag that did not match.
4. Test the key's validity range against the command counter before
   touching the tag, so a retired key cannot authenticate anything.
5. Grade the counter against the last accepted one and the window:
   replay, too far ahead, or a genuine advance.
6. Derive the tag over the key identity, the counter and the command
   content, compare it with the carried one in constant time, and return
   the outcome with the counter state the receiver should keep.

## Pitfalls

- Checking the tag and nothing else. The tag proves the command was once
  authorized; only the counter proves it was authorized now.
- Comparing tags with an ordinary equality test. It stops at the first
  differing octet, and the timing difference turns a search over the
  whole tag into a search over one octet at a time.
- Leaving the key validity range untested because the tag verified. It
  verified against the key presented, which is exactly what a retired or
  leaked key does.
- Accepting any counter above the last one. A single command with an
  enormous counter advances the receiver's state past every legitimate
  command the ground still has queued.
- Authenticating the payload without the counter, or the counter without
  the payload. Either leaves a tag that can be lifted onto a command it
  was never issued for.
- Refusing a command because it carried a tag it did not need. The
  protected set says which commands must be authenticated, not which
  commands may be.

## Behavior contract (gate 3)

The octet and key validation, tag width limits, key validity range, counter
freshness with its window, tag derivation over key identity, counter and
content, the constant-time comparison and the ordered accept-or-refuse
decision are exercised by the gate 3 contract test:
scripts/test_e50_command_authentication.py against
scripts/e50_command_authentication_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e50_command_authentication.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
