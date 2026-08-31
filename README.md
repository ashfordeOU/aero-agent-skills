# AeroSkills

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Format: agentskills.io](https://img.shields.io/badge/format-agentskills.io-purple)](https://agentskills.io)
[![Skills: 43 of 1,000+ target](https://img.shields.io/badge/skills-43%20of%201000%2B%20target-blue)](skills/)
[![Standards: 14](https://img.shields.io/badge/standards-14-blue)](STANDARDS.md)
[![Gates: 5/5 REAL](https://img.shields.io/badge/gates-5%2F5%20REAL-green)](docs/harness-contract.md)
[![Status: dev](https://img.shields.io/badge/status-dev-blue)](README.md)

Aerospace engineering skills for AI agents: standards-mapped,
eval-gated, Apache-2.0. The knowledge layer for engineering agents,
not the platform.

*Development status. This repository is the private development home:
skills, gates, and domain packs are actively built and verified here.
Public release is founder-gated; when released it ships as a clean
repo through the company org (Ashforde).*

## Table of contents

- [Why AeroSkills](#why-aeroskills)
- [Compliance notice](#compliance-notice)
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
  resolves against standards-map.yaml: the 13 domain standards
  DO-178C, DO-254, ARP4754A, ARP4761A, AS9100, DO-330, DO-160G,
  AS9102, MMPDS, FAR-25, CS-25, ECSS, and NACA TR-824, plus SEP-2640
  as the delivery format (skills over MCP), separate from the domain
  list. Referenced and summarized, never copied.
- **Eval gates.** make validate runs 5 REAL gates before anything
  ships: spec conformance, description quality, a per-skill behavior
  contract test, a no-verbatim copyright scan, and a 102-task Hit@1
  routing corpus. make attest adds 3: number snapshot, brief audit,
  content policy. Deterministic, offline, replayable. Verified means
  the full bar passes on the commit you are looking at: make validate
  5/5 and make attest 3/3, every behavior contract green, router
  deterministic. Not certification, not approval, not airworthy.

## Compliance notice

> **Compliance notice.** AeroSkills is an open, unrestricted library of
> *civil aerospace engineering methodology* for AI agents, published by
> Ashforde OU (Estonia) under Apache-2.0. The content is educational:
> general engineering principles, processes, and tool-usage guidance. It
> is **not** ITAR/EAR-controlled technical data, and no proprietary
> standards text is reproduced. Standards are referenced and
> summarized only: DO-178C, DO-254, ARP4754A, ARP4761A, AS9100,
> DO-330 (© RTCA/EUROCAE), DO-160G (© RTCA/EUROCAE ED-14G),
> AS9102 (© IAQG/SAE), and MMPDS (© SAE) remain the property of
> their publishers and must be purchased from them; ECSS and
> FAR/CS-25 are freely available (public regulations or free
> downloads); SEP-2640 is an open specification from the MCP working
> group (see STANDARDS.md).
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

## What's here

Forty-three verified skills (as of 2026-08-31) in nine installable
domain packs, each spec-linted, behavior-tested, and router-asserted
by make validate:

| Pack | Skill | Standard | Covers |
|---|---|---|---|
| aerodynamics | airfoil/airfoil-selection | NACA TR-824 | Use when you must select an airfoil section for a wing design: score ca |
| aerodynamics | airfoil/xfoil-analysis | NACA TR-824 | Use when running XFOIL-style airfoil analysis for a given section: pla |
| aerodynamics | cfd/cfd-convergence | NACA TR-824 | Use when you must judge whether a computational fluid dynamics run has c |
| avionics | do160/environmental-qualification | DO-160G | Use when planning or reviewing DO-160 environmental qualification of a |
| avionics | do178c/airworthiness-liaison | DO-178C | Use when you must manage DO-178C airworthiness and certification liaison |
| avionics | do178c/configuration-management | DO-178C | Use when you must manage DO-178C software configuration: establish con |
| avionics | do178c/development | DO-178C | Use when you must develop DO-178C airborne software lifecycle data for |
| avionics | do178c/planning | DO-178C | Use when planning DO-178C software certification for airborne systems |
| avionics | do178c/tool-qualification | DO-330 | Use when assessing software tool qualification per DO-330 and DO-178C: |
| avionics | do178c/verification | DO-178C | Use when you must verify DO-178C airborne software against its require |
| avionics | do254/hardware-planning | DO-254 | Use when you must plan DO-254 design assurance for airborne electronic |
| avionics | do254/requirements-capture | DO-254 | Use when you must capture and review DO-254 hardware requirements for a c |
| avionics | do254/verification | DO-254 | Use when verifying DO-254 airborne electronic hardware: determine the |
| avionics | far-cs25/airworthiness | FAR-25/CS-25 | Use when scoping transport-category airworthiness certification: deter |
| avionics | flight-management/flight-planning | DO-178C | Use when you must build and check a flight management system flight plan: |
| cross-cutting | sep2640/skill-delivery | SEP-2640 | Use when packaging or delivering domain skills over MCP per SEP-2640: |
| cross-cutting | units-atmos/isa-atmosphere | ECSS | Use when you must apply the international standard atmosphere in aerospac |
| gnc-autonomy | control/python-control-design | ARP4754A | Use when designing and validating feedback control laws with Python co |
| gnc-autonomy | optimal-control/dymos-trajectory | ARP4754A | Use when setting up and assessing pseudospectral trajectory optimizati |
| gnc-autonomy | space/orbit-dynamics | ECSS | Use when analyzing spacecraft orbital mechanics with two-body and J2-p |
| gnc-autonomy | space/rendezvous-phasing | ECSS | Use when you must plan an orbital rendezvous phasing maneuver: compute th |
| manufacturing-quality | as9100/counterfeit-prevention | AS9100 | Use when you must plan counterfeit parts prevention for an aerospace pro |
| manufacturing-quality | as9100/quality | AS9100 | Use when scoping or preparing AS9100 aerospace quality management work |
| manufacturing-quality | as9102/first-article-inspection | AS9102 | Use when preparing or reviewing an AS9102 first article inspection (FA |
| space-systems | adcs/attitude-control-sizing | ECSS | Use when you must size the attitude control subsystem actuators for a sp |
| space-systems | ecss/software-engineering | ECSS | Use when scoping European space software work per the ECSS series: cla |
| space-systems | ecss/systems-engineering | ECSS | Use when scoping or gating European space systems engineering per ECSS |
| space-systems | subsystems/power-thermal-budget | ECSS | Use when sizing spacecraft electrical power and thermal budgets per EC |
| space-systems | subsystems/thermal-design | ECSS | Use when you must size the thermal control subsystem for a spacecraft: c |
| structures | composites/laminate-stiffness | FAR-25/CS-25 | Use when you must compute the stiffness of a composite laminate with cla |
| structures | fatigue/miner-damage | FAR-25/CS-25 | Use when you must evaluate fatigue life with cumulative damage: sum the P |
| structures | fem/calculix-linear | FAR-25 | Use when running or checking linear static finite element analysis for |
| structures | materials/mmpsd-allowables | MMPDS | Use when computing statistically based metallic material design allowa |
| systems-engineering-safety | arp4754a/requirements-traceability | ARP4754A | Use when planning or auditing requirements traceability per ARP4754A: |
| systems-engineering-safety | arp4754a/systems-planning | ARP4754A | Use when you must plan aircraft and system development per ARP4754A: a |
| systems-engineering-safety | arp4754a/validation | ARP4754A | Use when you must run requirements validation for an aircraft or system |
| systems-engineering-safety | arp4761a/common-cause-analysis | ARP4761A | Use when you must plan or review common cause analysis for a safety asse |
| systems-engineering-safety | arp4761a/fta-fmea | ARP4761A | Use when scoping or executing FTA (fault tree analysis) and FMEA (fail |
| systems-engineering-safety | arp4761a/safety-assessment | ARP4761A | Use when planning or conducting the civil-aircraft safety assessment p |
| systems-engineering-safety | mbse/systems-engineering | SysML | Use when running model-based systems engineering for an aerospace prog |
| vehicle-design | conceptual/tow-estimation | FAR-25/CS-25 | Use when you must estimate the takeoff gross weight in conceptual aircra |
| vehicle-design | mass-properties/inertia-estimation | FAR-25/CS-25 | Use when you must estimate mass properties for vehicle design: compute m |
| vehicle-design | sizing/weight-estimation | FAR-25/CS-25 | Use when performing class-I or class-II vehicle weight estimation: com |
Domain packs follow the 12-discipline taxonomy: aerodynamics,
gnc-autonomy, structures, vehicle-design, avionics, space-systems,
systems-engineering-safety, manufacturing-quality, cross-cutting.
Nine of the twelve disciplines have packs today; propulsion, flight
mechanics, and flight test land in Wave 5. Each pack has a router
SKILL.md that describes the
domain, lists its sub-skills, and tells an agent when to route to it;
every SKILL.md carries domain and pack frontmatter so routers and
installers can filter on them. Run `make packs` for the machine
readable inventory.

Every skill ships its own behavior contract in skills/<path>/scripts/,
exercised by make validate gate 3.

## Install

Prereqs: git, make, python3 with PyYAML.

    git clone https://github.com/arjun-0077/aeroskills.git
    cd aeroskills
    make validate        # 5/5 REAL gates, offline
    make packs           # list the domain packs and their skills

The library is organized into installable domain packs, so you can
install only the domain you need. A pack is the set of leaf folders
(the folders that contain SKILL.md) under skills/<pack>/. Copy or
symlink those leaf folders into your host's skills directory, then
restart the session. Full per-host walkthrough:
[docs/harness-integration.md](docs/harness-integration.md).

Example, install only the avionics pack (DO-178C software lifecycle,
DO-330 tool qualification, DO-160 environmental qualification, DO-254
hardware assurance, FAR-25/CS-25 airworthiness), Claude Code
user scope:

    mkdir -p ~/.claude/skills
    cp -r skills/avionics/do178c/planning skills/avionics/do178c/development \
          skills/avionics/do178c/verification skills/avionics/do178c/configuration-management \
          skills/avionics/do178c/tool-qualification skills/avionics/do160/environmental-qualification \
          skills/avionics/do254/hardware-planning skills/avionics/do254/verification \
          skills/avionics/far-cs25/airworthiness \
          ~/.claude/skills/

Example, install only the space-systems pack (ECSS software and
systems engineering, power and thermal budgeting):

    cp -r skills/space-systems/ecss/software-engineering \
          skills/space-systems/ecss/systems-engineering \
          skills/space-systems/subsystems/power-thermal-budget \
          ~/.claude/skills/

Install the full library the same way: copy every pack's leaf folders.
The pack entry points (skills/<pack>/SKILL.md) are router documents
for agents; hosts load the leaf folders that carry the actual skills.

One-command registry installs (npx skills add, gh skill install) are
listed for when the repository is public; the manual paths above work
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

Every host consumes flat <skill-name>/SKILL.md folders, so installing
a domain pack means copying or symlinking each of its leaf folders.
`make packs` lists every leaf in every pack.

Example, avionics pack, Claude Code user scope (same as Install):

    for d in skills/avionics/do178c/* skills/avionics/do254/* skills/avionics/far-cs25/*; do
      cp -r "$d" ~/.claude/skills/
    done

Example, single skill, Gemini CLI via the native command:

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
| 3 behavior tests | per-skill behavior contract, DAL A-E determination | make pytest-contract |
| 4 no-verbatim | standards text copyright control | make no-verbatim |
| 5 Hit@1 corpus | router selects the expected skill | make hit1 |

Verified means the full bar passes on the commit you are looking at:
make validate 5/5 (spec conformance, description quality, per-skill
behavior contract, no-verbatim copyright control, Hit@1 routing) and
make attest 3/3 (number snapshot against the canonical register,
brief audit, content-policy sweep), with the offline router
deterministic. That is what "verified" means in this
repository: nothing more. It is not certification, not approval, not
airworthy.

## Standards map

standards-map.yaml is the machine-readable source of truth; STANDARDS.md
is the human companion. The map records family, publisher, status,
applicability, and the summary-not-copy rule for every mapped standard.
Gated standards (DO-178C, DO-254, ARP4754A, ARP4761A, AS9100, DO-330,
DO-160G, AS9102, MMPDS) never appear verbatim anywhere in this
repository; the no-verbatim gate enforces it.

## Security

Skills are folders that can carry scripts (skills/<path>/scripts/),
and agent hosts execute what they load. Review the SKILL.md and any
scripts before you install, the same way you would review any code
dependency. The no-verbatim gate means standards text is referenced
and summarized, never copied into the library. To report a
vulnerability, see [SECURITY.md](SECURITY.md).

## Roadmap

- Shipped: 43 verified skills in nine installable domain packs as of
  2026-08-31. The certification spine (DO-178C planning, development,
  verification, and configuration management; DO-254 hardware
  planning; ARP4754A systems planning; ARP4761A safety assessment;
  AS9100 quality; FAR-25/CS-25 airworthiness; ECSS space software,
  MBSE, SEP-2640 skill delivery) plus Wave 4 breadth across all nine
  packs. Every skill gated by make validate (5/5) and make attest
  (3/3).
- Release bar (founder, 2026-08-31): 50+ domains x 20+ verified
  skills = 1,000+ skills, all make-validate green, before any
  release. The 12-discipline tree decomposes into 68 sub-domain packs
  (1,360 skills at 20 each): a planning target, not a shipped count.
  [development/50x20-domain-tree.md](development/50x20-domain-tree.md).
- Next: fill the nine existing packs toward 20 skills each (43 ->
  ~180), then Wave 5 opens new disciplines (propulsion, flight
  mechanics, flight test and operations) on the same eval-gated
  pipeline, then the remaining sub-domains.
- Later: reference builds; a SEP-2640-aligned MCP adapter for
  enterprise delivery; marketplace listings; the same knowledge
  packaged as AI Department Operator packs (role charters, budget
  ledgers, schedules, evidence gates).

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR: one skill
per PR, every contributor certifies their submission contains no
controlled data and no verbatim standards text, and every merge must
pass make validate (5/5) and make attest (3/3). New skills land inside
their domain pack (skills/<pack>/<standard>/<activity>/SKILL.md) and
carry domain and pack frontmatter. Smallest packs today: cross-cutting
(two skills), aerodynamics and vehicle-design (three each); every pack
grows toward 20 per the 50x20 release bar.

## FAQ

[docs/FAQ.md](docs/FAQ.md) covers the questions buyers actually ask:
license, certification status, export control, what verified means,
and affiliation. The short answers: Apache-2.0, not certified, not
controlled as published, verified = replayable make validate 5/5 plus
make attest 3/3 on the commit you are looking at, and not affiliated
with RTCA, SAE, EASA, FAA, or any government.

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
