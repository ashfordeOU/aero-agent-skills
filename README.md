# AeroSkills

Aerospace engineering skills for AI agents: standards-mapped,
eval-gated, Apache-2.0. The knowledge layer for engineering agents,
not the platform.

*Draft v0.1. Buyer-facing draft, in-tree only; release is
founder-gated.*

> **Compliance notice.** AeroSkills is an open, unrestricted library of
> *civil aerospace engineering methodology* for AI agents, published by
> Ashforde OU (Estonia) under Apache-2.0. The content is educational:
> general engineering principles, processes, and tool-usage guidance. It
> is **not** ITAR/EAR-controlled technical data, and no proprietary
> standards text is reproduced. Standards (DO-178C, DO-254, ARP4754A,
> ARP4761A, AS9100, FAR/CS-25, ECSS, SEP-2640) are referenced and
> summarized only — the standards themselves remain the property of
> their publishers and must be purchased from them (see STANDARDS.md).
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
  behavior test, a no-verbatim copyright scan, and a Hit@1 routing
  corpus. Deterministic, offline, replayable.

## What's here

- skills/avionics/do178c/planning: the seed skill. Determine the
  software level (DAL A-E) from failure-condition severity, draft the
  PSAC, scope planning artifacts. Behavior-tested.

## Install

Clone, verify, then point your agent host at the skills folder:

    git clone https://github.com/arjun-0077/aeroskills.git
    cd aeroskills
    make validate        # 5/5 REAL gates, offline

Add skills/<path> to your host's skills directory (Claude Code,
Hermes, OpenClaw, Codex, or any agentskills.io host). Each SKILL.md
declares its compatibility in frontmatter.

## Standards map

standards-map.yaml is the machine-readable source of truth; STANDARDS.md
is the human companion. The map records family, publisher, status,
applicability, and the summary-not-copy rule for every mapped standard.
Gated standards (DO-178C, DO-254, ARP4754A, ARP4761A, AS9100) never
appear verbatim anywhere in this repository; the no-verbatim gate
enforces it.

## Roadmap

- Now: the certification spine. DO-178C planning is shipped; next are
  DO-178C verification, DO-254 hardware assurance, ARP4761A safety
  assessment, AS9100 quality.
- Next: breadth across the 12 aerospace disciplines, reference builds,
  a SEP-2640-aligned MCP adapter for enterprise delivery, marketplace
  listings.
- Later: the same knowledge packaged as AI Department Operator packs:
  role charters, budget ledgers, schedules, evidence gates.

## Star request

If AeroSkills saves you an afternoon, star the repository. It tells us
where to spend the next authoring pass.

## License and legal

Apache-2.0. See [LICENSE](LICENSE) · [NOTICE](NOTICE) ·
[SECURITY.md](SECURITY.md) · [CONTRIBUTING.md](CONTRIBUTING.md) ·
[STANDARDS.md](STANDARDS.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

# AeroSkills: Company Structure

AeroSkills runs as a company of departments, following the proven
Department-as-Code pattern (Veda reference implementation). Each
department is a folder with a README (what it does + how to run it),
an AGENTS.md (rules), and its own workspace.

Updated: 2026-08-31

## Department inventory

| Department | Purpose | Key outputs |
|---|---|---|
| **Research** | Market + competitor + technical research | research/notes/, research/briefs/ |
| **Development** | Product build, skills, tooling | development/src/, development/builds/ |
| **Marketing** | Positioning, content, GTM | marketing/strategy/, marketing/content/ |
| **Finance** | Costs, pricing, runway, invoices | finance/ledger/, finance/pricing/ |
| **Ops** | Infrastructure, automation, reliability | ops/runbooks/, ops/state/ |
| **Security** | Guardrails, compliance, risk | security/policy/, security/audits/ |
| **Legal** | Licensing, contracts, IP | legal/contracts/, legal/licenses/ |
| **HR (People)** | Roles, charters, hiring | people/roles/, people/onboarding/ |
| **Support** | Docs, help, user questions | support/docs/, support/faq/ |

## Department-as-Code anatomy

```
AeroSkills/
├── README.md            # this file
├── research/            # what we learn
├── development/         # what we build
├── marketing/           # how we're seen
├── finance/             # how we survive
├── ops/                 # how it runs
├── security/            # how we stay safe
├── legal/               # how we stay legal
├── people/              # who does what
├── support/             # how users get help
├── AGENTS.md            # project-wide rules
└── .git/                # one main branch, clean-at-rest
```

## Operating rules (from Veda doctrine)

1. ONE main branch; every commit complete; clean at rest
2. Evidence over claims: no finding ships without receipts
3. Store-first: everything learned is filed, indexed, connected
4. Supersede-not-delete: history is the safety net
5. Each department owns its folder; cross-cutting work lands where
   it belongs and is linked
