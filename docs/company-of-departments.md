# AeroSkills: Company Structure

AeroSkills runs as a company of departments, following the proven
Department-as-Code pattern (Veda reference implementation). Each
department is a folder with a README (what it does + how to run it)
and its own workspace.

Updated: 2026-08-31

## Department inventory

| Department | Purpose | Key outputs |
|---|---|---|
| **Research** | Market + competitor + technical research | briefs, market analysis, peer audits |
| **Development** | Product build, skills, tooling | skills/, eval/, scripts/ |
| **Marketing** | Positioning, content, GTM | positioning-1pager.md, release-notes |
| **Finance** | Costs, pricing, runway, invoices | internal ledgers, pricing notes |
| **Ops** | Infrastructure, automation, reliability | gate scripts, number register |
| **Security** | Guardrails, compliance, risk | audits, policy notes |
| **Legal** | Licensing, contracts, IP | LICENSE, NOTICE, compliance |
| **HR (People)** | Roles, charters, hiring | role charters, onboarding |
| **Support** | Docs, help, user questions | FAQ, glossary, help content |

## Department-as-Code anatomy

The public repository is the product tree only: skills, scripts,
eval corpus, standards map, public docs, and the gate machinery that
proves the product (ops/automation). Internal department workspaces
(research/, development/, finance/, people/, support/, security/audits/)
are kept out of the public package.

```
AeroSkills/              # public tree
├── README.md            # public landing page
├── skills/              # the library (27 skills, 9 packs)
├── scripts/             # gate + eval machinery
├── eval/                # Hit@1 corpus
├── standards-map.yaml   # machine-readable standards map
├── docs/                # public docs (FAQ, glossary, contract)
├── marketing/           # positioning, release notes
├── ops/automation/      # attestation gates (scripts, register)
└── .github/             # CI workflow
```

## Operating rules (from Veda doctrine)

1. ONE main branch; every commit complete; clean at rest
2. Evidence over claims: no finding ships without receipts
3. Store-first: everything learned is filed, indexed, connected
4. Supersede-not-delete: history is the safety net
5. Each department owns its folder; cross-cutting work lands where
   it belongs and is linked
