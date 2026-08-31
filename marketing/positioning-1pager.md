# AeroSkills positioning: the aerospace knowledge layer

**Date:** 2026-08-31 · **Status:** draft-in-tree, release founder-gated
**Sources:** research/briefs/06, 09, 11; docs/harness-contract.md;
ops/automation/numbers.yaml (canonical number register)

## One line

AeroSkills is the aerospace engineering knowledge layer for AI agents:
standards-mapped skills that give a coding agent the certification
process, not just the acronyms.

## Category: knowledge layer, not the platform

AeroSkills ships as files. Each skill is a SKILL.md document on the
open agentskills.io format that any agent host can load on demand. It
does not run simulations, it does not host services, it does not route
or govern. Those are platform concerns. The library is the layer below
them. Call it the knowledge layer, never the platform.

## Buyer: the engineer

Primary buyer is the working engineer: systems, software, safety,
avionics. Someone who has asked a general-purpose AI about DO-178C and
gotten a Wikipedia summary: correct acronyms, no clauses, no workflow.
AeroSkills answers with the planning artifacts, the DAL allocation
logic, the verification steps, and the point where the agent must stop
and let a human sign.

## Wedge: the standards map

The machine-readable map (standards-map.yaml) covers DO-178C, DO-254,
ARP4754A, ARP4761A, AS9100, FAR-25, CS-25, ECSS, and SEP-2640, with a
summary-not-copy rule and a gated-standard rule enforced by a real
gate. Every skill carries standards frontmatter that resolves against
the map. No aerospace repo has this. The map is the moat; the skills
are how the map earns its keep.

## Proof: evals, not promises

make validate runs 5 REAL gates before anything ships:

1. spec lint: agentskills.io conformance + compliance flags
2. description lint: what + when + trigger, written for the router
3. behavior test: DAL/FDAL/IDAL determination per ARP4754A/ARP4761A
4. no-verbatim: copyright control over standards text
5. Hit@1: routing corpus resolves to the expected skill

Replayable by anyone: clone, run make validate, exit 0. "Verified"
in our copy means exactly this: the gates pass on the commit you are
looking at. It does not mean certified, approved, or airworthy.

## The lane is empty

The aerospace lane is unserved. Total across all attempts is about 228★.
The two live attempts: ajhcs/mbse-agents (22★) and
devideamax/aerospace-team (21★). Adjacent domains prove the play:
Anthropic-Cybersecurity-Skills (31,700★) and K-Dense Scientific Agent
Skills (39,503★) both won on framework mapping and evals, the same
two things AeroSkills ships first.

## Compliance posture

As published, this is not controlled technical data; verify before
use (brief 06 §8.3.9). The library is methodology, not designs:
general engineering principles and process guidance. It carries no
certification claims and no export-control claims. Mis-marking public
content is itself a compliance failure (brief 06 §8.3.9).

## What ships

The Phase 1 certification spine is shipped: 12 skills across DO-178C
(planning, development, verification, configuration management),
DO-254 hardware planning, ARP4754A systems planning, ARP4761A safety
assessment, AS9100 quality, FAR-25/CS-25 airworthiness, ECSS space
software, MBSE systems engineering, and SEP-2640 skill delivery.
Methodology that lives inside certified workflows, not certification
itself. Draft is in-tree; release is founder-gated.
