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
