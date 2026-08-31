# AeroSkills

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Format: agentskills.io](https://img.shields.io/badge/format-agentskills.io-purple)](https://agentskills.io)
[![Skills: 12](https://img.shields.io/badge/skills-12-blue)](skills/)
[![Standards: 9](https://img.shields.io/badge/standards-9-blue)](STANDARDS.md)
[![Gates: 5/5 REAL](https://img.shields.io/badge/gates-5%2F5%20REAL-green)](docs/harness-contract.md)
[![Status: draft](https://img.shields.io/badge/status-draft-orange)](README.md)

Aerospace engineering skills for AI agents: standards-mapped,
eval-gated, Apache-2.0. The knowledge layer for engineering agents,
not the platform.

*Draft v0.2. Buyer-facing draft, in-tree only; release is
founder-gated.*

> **Compliance notice.** AeroSkills is an open, unrestricted library of
> *civil aerospace engineering methodology* for AI agents, published by
> Ashforde OU (Estonia) under Apache-2.0. The content is educational:
> general engineering principles, processes, and tool-usage guidance. It
> is **not** ITAR/EAR-controlled technical data, and no proprietary
> standards text is reproduced. Standards are referenced and
> summarized only: DO-178C, DO-254, ARP4754A, ARP4761A, and AS9100
> remain the property of their publishers (© RTCA/SAE/IAQG) and must
> be purchased from them; ECSS and FAR/CS-25 are freely available
> (public regulations or free downloads); SEP-2640 is an open
> specification from the MCP working group (see STANDARDS.md).
>
> As published, without restrictions on further dissemination, this
> library falls within the EU dual-use "public domain" exclusion (Annex I
> General Technology Note, Regulation (EU) 2021/821) and is not subject
> to EU dual-use export authorization.
>
> **Responsible use.** Users are solely responsible for their own
> compliance with export-control and sanctions laws applicable to their
> use of this material. This notice is hygiene, not the legal mechanism:
> public availability is what keeps published information decontrolled.
>
> **Not affiliated with or endorsed by** RTCA, EUROCAE, SAE International,
> IAQG, EASA, FAA, or any government.
>
> See [SECURITY.md](SECURITY.md) · [CONTRIBUTING.md](CONTRIBUTING.md) · [STANDARDS.md](STANDARDS.md)

## Table of contents

- [Why AeroSkills](#why-aeroskills)
- [What's here](#whats-here)
- [Install](#install)
- [Harness integration](#harness-integration)
- [Verify](#verify)
- [Standards map](#standards-map)
- [Security](#security)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [FAQ](#faq)

## Why AeroSkills

Ask a general-purpose AI about DO-178C and you get a Wikipedia summary:
the acronyms, none of the clauses. Aerospace engineering is
standards-bound and evidence-driven. A number without a validation
step is useless. AeroSkills encodes the process: when to use a
standard, the workflow, the pitfalls, and the point where the agent
must stop and let a human sign.

Each skill is a SKILL.md file on the open agentskills.io format: YAML
frontmatter the router reads, a body the agent follows. Loaded on
demand, no lock-in, works in any host that reads the format.

Two things separate this library from a folder of prompts:

- **Standards map.** Every skill carries standards frontmatter that
  resolves against standards-map.yaml: DO-178C, DO-254, ARP4754A,
  ARP4761A, AS9100, FAR-25, CS-25, ECSS, SEP-2640. Referenced and
  summarized, never copied.
- **Eval gates.** make validate runs 5 REAL gates before anything
  ships: spec conformance, description quality, a DAL-determination
  behavior test, a no-verbatim copyright scan, and a 28-task Hit@1
  routing corpus. Deterministic, offline, replayable. Verified means
  the gates pass on the commit you are looking at; not certification,
  not approval, not airworthy.

## What's here

Twelve verified skills, each spec-linted, behavior-tested, and
router-asserted by make validate:

| Skill | Standard | Covers |
|---|---|---|
| avionics/do178c/planning | DO-178C | software level/DAL (A-E) from failure severity; PSAC; planning-phase artifacts |
| avionics/do178c/development | DO-178C | HLR/LLR/code traceability, derived requirements |
| avionics/do178c/verification | DO-178C | review, structural coverage per level, independence |
| avionics/do178c/configuration-management | DO-178C | baselines, problem reports, release gate |
| avionics/do254/hardware-planning | DO-254 | simple vs complex AEH, PHAC scope |
| arp4754a/systems-planning | ARP4754A | FDAL/IDAL allocation, certification and system development plans |
| arp4761a/safety-assessment | ARP4761A | FHA/PSSA/SSA sequence, analysis set (FTA/FMEA/CCA) |
| as9100/quality | AS9100 | aerospace QMS clauses, audit evidence, corrective action closure |
| avionics/far-cs25/airworthiness | FAR-25/CS-25 | certification basis, means of compliance, 25.1309 applicability |
| space/ecss/software-engineering | ECSS | ECSS criticality (A-D), lifecycle gates, heritage reuse |
| mbse/systems-engineering | SysML | SysML modeling workflow, function allocation, digital-thread traceability |
| sep2640/skill-delivery | SEP-2640 | SKILL.md packaging and discovery over MCP |

Every skill ships its own behavior contract in skills/<path>/scripts/,
exercised by make validate gate 3.

## Install

Prereqs: git, make, python3 with PyYAML.

    git clone https://github.com/arjun-0077/aeroskills.git
    cd aeroskills
    make validate        # 5/5 REAL gates, offline

Then load the skills into your agent host. The install unit is the
leaf folder that contains SKILL.md, for example
skills/avionics/do178c/planning. Copy or symlink it into your host's
skills directory, then restart the session. Full per-host walkthrough:
[docs/harness-integration.md](docs/harness-integration.md).

One-command registry installs (npx skills add, gh skill install) are
listed for when the repository is public; the manual paths below work
today.

## Harness integration

| Host | Mechanism | Install target |
|---|---|---|
| Claude Code | skills directory (project or user scope) | .claude/skills/ or ~/.claude/skills/ |
| OpenAI Codex | skills directories (repo and user scope) | .agents/skills/ or ~/.agents/skills/ (legacy experimental: ~/.codex/skills/ behind a feature flag) |
| DeepSeek (via harness) | run DeepSeek as the model provider in a SKILL.md host, then use that host's method | see the host row |
| Gemini CLI | native SKILL.md support plus install/link commands | ~/.gemini/skills/ or .gemini/skills/ |
| OpenCode | skills directory, native skill tool | .opencode/skills/ (also .claude/skills/, .agents/skills/) |
| Cursor | skills directory, loads SKILL.md natively | .cursor/skills/ (also .claude/skills/, .codex/skills/, ~/.claude/skills/, ~/.codex/skills/) |
| Generic agentskills.io host | any host that reads the format | host's skills directory |
| SEP-2640 MCP | emerging skills-over-MCP adapter, skills served as resources | skill:// URIs behind directoryRead |

Example, Claude Code user scope:

    mkdir -p ~/.claude/skills
    cp -r skills/avionics/do178c/planning ~/.claude/skills/planning

Example, Gemini CLI via the native command:

    gemini skills link "$PWD/skills/avionics/do178c/planning"

Known constraint: the legacy experimental Codex loader caps skill
descriptions at 500 characters; AeroSkills descriptions run 575 to
716 characters, so that loader may skip or truncate them until
trimmed (the current Codex skills docs use the agentskills.io format).
Details and the rest of the per-host commands:
[docs/harness-integration.md](docs/harness-integration.md).

## Verify

You do not need to trust the badge. Replay the gates on the commit you
are looking at:

    make validate        # 5/5 REAL gates: spec lint, desc lint, behavior tests, no-verbatim scan, Hit@1 corpus
    make attest          # 3/3: number snapshot offline, brief audit, content-policy sweep

| Gate | What it checks | How to run |
|---|---|---|
| 1 spec lint | agentskills.io conformance + compliance flags | make lint-spec |
| 2 desc lint | description what + when + trigger | make desc-lint |
| 3 behavior tests | per-skill DAL determination contract | make pytest-contract |
| 4 no-verbatim | standards text copyright control | make no-verbatim |
| 5 Hit@1 corpus | router selects the expected skill | make hit1 |

Exit 0 means the commit passes. That is what "verified" means in this
repository: nothing more. It is not certification, not approval, not
airworthy.

## Standards map

standards-map.yaml is the machine-readable source of truth; STANDARDS.md
is the human companion. The map records family, publisher, status,
applicability, and the summary-not-copy rule for every mapped standard.
Gated standards (DO-178C, DO-254, ARP4754A, ARP4761A, AS9100) never
appear verbatim anywhere in this repository; the no-verbatim gate
enforces it.

## Security

Skills are folders that can carry scripts (skills/<path>/scripts/),
and agent hosts execute what they load. Review the SKILL.md and any
scripts before you install, the same way you would review any code
dependency. The no-verbatim gate means standards text is referenced
and summarized, never copied into the library. To report a
vulnerability, see [SECURITY.md](SECURITY.md).

## Roadmap

- Shipped: the certification spine. DO-178C planning, development,
  verification, and configuration management; DO-254 hardware
  planning; ARP4754A systems planning; ARP4761A safety assessment;
  AS9100 quality; FAR-25/CS-25 airworthiness; plus ECSS space
  software, MBSE, and SEP-2640 skill delivery. All 12 gated by
  make validate (5/5).
- Next: breadth across the 12 aerospace disciplines (aerodynamics/XFOIL,
  propulsion, structures, flight mechanics, spacecraft subsystems) on
  the same eval-gated build; reference builds; a SEP-2640-aligned MCP
  adapter for enterprise delivery; marketplace listings.
- Later: the same knowledge packaged as AI Department Operator packs:
  role charters, budget ledgers, schedules, evidence gates.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR: one skill
per PR, every contributor certifies their submission contains no
controlled data and no verbatim standards text, and every merge must
pass make validate (5/5) and make attest (3/3). Thin domains today:
space/ecss (one skill) and mbse (one skill).

## FAQ

[docs/FAQ.md](docs/FAQ.md) covers the questions buyers actually ask:
license, certification status, export control, what verified means,
and affiliation. The short answers: Apache-2.0, not certified, not
controlled as published, verified = replayable make validate 5/5, and
not affiliated with RTCA, SAE, EASA, FAA, or any government.

## Star request

If AeroSkills saves you an afternoon, star the repository. It tells us
where to spend the next authoring pass.

## License and legal

Apache-2.0. See [LICENSE](LICENSE) · [NOTICE](NOTICE) ·
[SECURITY.md](SECURITY.md) · [CONTRIBUTING.md](CONTRIBUTING.md) ·
[STANDARDS.md](STANDARDS.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## Maintainers

Repo operating structure, department inventory, and operating rules:
[docs/company-of-departments.md](docs/company-of-departments.md).
