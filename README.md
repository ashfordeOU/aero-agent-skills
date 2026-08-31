# AeroSkills

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

# AeroSkills — Company Structure

AeroSkills runs as a company of departments, following the proven
Department-as-Code pattern (Veda reference implementation). Each
department is a folder with a README (what it does + how to run it),
an AGENTS.md (rules), and its own workspace.

Updated: 2026-08-30

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
2. Evidence over claims — no finding ships without receipts
3. Store-first: everything learned is filed, indexed, connected
4. Supersede-not-delete: history is the safety net
5. Each department owns its folder; cross-cutting work lands where
   it belongs and is linked
