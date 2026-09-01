<p align="center">
  <img src="docs/banner.svg" alt="AeroSkills — the aerospace knowledge layer for AI agents" width="100%">
</p>

<p align="center">
  <strong>The aerospace engineering knowledge layer for AI agents.</strong><br>
  Standards-mapped skills that give a coding agent the certification process — not just the acronyms.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue" alt="Apache-2.0"></a>
  <a href="https://agentskills.io"><img src="https://img.shields.io/badge/format-agentskills.io-purple" alt="agentskills.io"></a>
  <a href="skills/"><img src="https://img.shields.io/badge/skills-259%20of%201%2C460-green" alt="skills"></a>
  <a href="STANDARDS.md"><img src="https://img.shields.io/badge/standards-20-blue" alt="standards"></a>
  <a href="https://github.com/arjun-0077/aeroskills/actions"><img src="https://img.shields.io/badge/gates-5%2F5%20REAL-green" alt="gates"></a>
  <a href="README.md"><img src="https://img.shields.io/badge/status-dev-blue" alt="status"></a>
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> ·
  <a href="#why">Why</a> ·
  <a href="#whats-inside">What's inside</a> ·
  <a href="#the-standards-map">Standards map</a> ·
  <a href="#verify">Verify</a> ·
  <a href="#roadmap">Roadmap</a> ·
  <a href="#faq">FAQ</a>
</p>

---

Ask a general-purpose AI about DO-178C and you get a Wikipedia summary: the acronyms, none of the clauses. Aerospace engineering is standards-bound and evidence-driven. A number without a validation step is useless.

**AeroSkills encodes the process** — when to use a standard, the workflow, the pitfalls, and the point where the agent must stop and let a human sign. Each skill is a `SKILL.md` on the open agentskills.io format: YAML frontmatter the router reads, a body the agent follows. Loaded on demand, no lock-in, works in any host that reads the format.

*Development status. This repository is the private development home: skills, gates, and domain packs are actively built and verified here. Public release is founder-gated; when released it ships as a clean repo through the company org (Ashforde).*

## Quick start

**One command, any agent** — the open [skills CLI](https://github.com/vercel-labs/skills) installs into 70+ agents (Claude Code, Codex, Cursor, Copilot, Gemini CLI, Cline, and more):

```bash
npx skills add arjun-0077/aeroskills            # install all skills
npx skills add arjun-0077/aeroskills --list     # browse before installing
```

Or grab one pack / one skill:

```bash
npx skills add arjun-0077/aeroskills --skill avionics/do178c/planning
```

**Or copy the folder** — skills are just files. Copy or symlink any `skills/<family>/<pack>/<leaf>/` into your agent's skills directory (`~/.claude/skills/`, `~/.codex/skills/`, …). Per-host commands: [docs/harness-integration.md](docs/harness-integration.md).

**Verify it works:**

```bash
git clone https://github.com/arjun-0077/aeroskills && cd aeroskills
make validate   # 5/5 REAL gates, deterministic, offline
```

## Why

AI agents default to the shortest path — which often means skipping the specs, the verification steps, and the "stop here, a human must sign" gates that keep aerospace software safe. AeroSkills gives agents structured workflows that encode the same discipline a certification engineer brings.

Two things separate this library from a folder of prompts:

- **The standards map.** Every skill carries standards frontmatter that resolves against `standards-map.yaml` — 20 standards (DO-178C, DO-254, ARP4754A, ARP4761A, AS9100, DO-330, DO-160G, AS9102, MMPDS, FAR-25/CS-25, FAR-33, ARINC 429, NAS 410, ASME Y14.5, ECSS, NACA TR-824, NACA TN 902, MIL-STD-1553, plus SEP-2640 as the delivery format). Referenced and summarized, never copied. No aerospace repo has this.
- **Eval gates, not promises.** `make validate` runs 5 REAL gates before anything ships. Replayable by anyone: clone, run, exit 0. "Verified" means exactly that — the gates pass on the commit you are looking at. Not certification, not approval, not airworthy.

## What's inside

**263 verified skills** (as of 2026-09-01) across **12 disciplines**, each spec-linted, behavior-tested, and router-asserted. Target: **73 packs × 20 skills = 1,460**.

| Family | Live packs | Standard spine | Example skills |
|---|---|---|---|
| **Avionics** | do178c, do254, do160, far-cs25, data-bus, flight-management | DO-178C, DO-254, DO-330, DO-160G | planning, verification, configuration-management, tool-qualification |
| **Aerodynamics** | airfoil, cfd, drag-polars, high-speed, boundary-layer, high-lift, ground-effects | NACA TR-824 | airfoil-selection, xfoil-analysis, cfd-convergence, normal-shock |
| **Systems engineering & safety** | arp4754a, arp4761a, mbse | ARP4754A, ARP4761A | dal-allocation, safety-assessment |
| **Flight mechanics** | performance, stability-control, handling-qualities | FAR-25/CS-25 | breguet-range, climb-performance, longitudinal-stability |
| **Flight test & operations** | envelope, performance, planning, flutter, stability | FAR-25/CS-25 | v-speeds, flight-test-planning, flutter-testing |
| **GNC & autonomy** | control, navigation, optimal-control, guidance, space | ARP4754A | root-locus-design, lqr-design, dymos-trajectory |
| **Space systems** | orbit-mechanics, adcs, subsystems, ecss | ECSS | orbital-decay, isa-atmosphere |
| **Structures** | fatigue, fem, composites, damage-tolerance, materials | FAR-25/CS-25 | engineering-margins |
| **Manufacturing quality** | as9100, as9102, ndt, special-processes | AS9100, AS9102 | first-article-inspection |
| **Propulsion** | rocket, turbofan, turboprop, ramjet, gas-turbine-cycle, axial-compressor, engine-airframe | FAR-33 | rocket-sizing |
| **Vehicle design** | conceptual, sizing, mass-properties, mdo, cost-estimation, structures-integration | FAR-25/CS-25 | — |
| **Cross-cutting** | sep2640, numerics, units-atmos, documentation, tolerancing | SEP-2640 | skill-delivery, engineering-report, unit-conversion |

Full catalog: the [skills/](skills/) tree — every leaf is a verified skill. Per-pack tables: [docs/catalog.md](docs/catalog.md).

## The standards map

`standards-map.yaml` is the machine-readable source of truth; [STANDARDS.md](STANDARDS.md) is the human companion. The map records family, publisher, status, applicability, and the summary-not-copy rule for every mapped standard. Gated standards (DO-178C, DO-254, ARP4754A, ARP4761A, AS9100, DO-330, DO-160G, AS9102, MMPDS) never appear verbatim anywhere in this repository — the no-verbatim gate enforces it.

## Verify

You do not need to trust the badge. Replay the gates on the commit you are looking at:

| Gate | What it checks | How to run |
|---|---|---|
| 1 spec lint | agentskills.io conformance + compliance flags | `make lint-spec` |
| 2 desc lint | description what + when + trigger | `make desc-lint` |
| 3 behavior tests | per-skill behavior contract, DAL A–E determination | `make pytest-contract` |
| 4 no-verbatim | standards text copyright control | `make no-verbatim` |
| 5 Hit@1 corpus | router selects the expected skill | `make hit1` |

```bash
make validate   # 5/5 REAL gates
make attest     # 3/3: number snapshot, brief audit, content-policy sweep
```

Verified means the full bar passes on the commit you are looking at: `make validate` 5/5 and `make attest` 3/3, every behavior contract green, router deterministic. That is what "verified" means in this repository: nothing more. It is not certification, not approval, not airworthy.

## Security

Skills are folders that can carry scripts, and agent hosts execute what they load. Review the SKILL.md and any scripts before you install, the same way you would review any code dependency. To report a vulnerability, see [SECURITY.md](SECURITY.md).

## Roadmap

- **Shipped:** 259 verified skills across 12 disciplines, all gated by `make validate` (5/5) and `make attest` (3/3).
- **Release bar (founder, 2026-08-31):** 50+ domains × 20+ verified skills = 1,000+ skills before any release. The 12-discipline tree decomposes into 73 sub-domain packs (1,460 skills at 20 each). [development/50x20-domain-tree.md](development/50x20-domain-tree.md)
- **Next:** fill the live sub-domain packs toward 20 skills each; open remaining packs on the same eval-gated pipeline.
- **Later:** reference builds; a SEP-2640-aligned MCP adapter for enterprise delivery; marketplace listings; AI Department Operator packs (role charters, budget ledgers, schedules, evidence gates).

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR: one skill per PR, every contributor certifies their submission contains no controlled data and no verbatim standards text, and every merge must pass `make validate` (5/5) and `make attest` (3/3).

## FAQ

[docs/FAQ.md](docs/FAQ.md) covers the questions buyers actually ask: license, certification status, export control, what verified means, and affiliation. Short answers: Apache-2.0, not certified, not controlled as published, verified = replayable `make validate` 5/5 plus `make attest` 3/3 on the commit you are looking at, not affiliated with RTCA, SAE, EASA, FAA, or any government.

## Compliance notice

> **Compliance notice.** AeroSkills is an open, unrestricted library of *civil aerospace engineering methodology* for AI agents, published by Ashforde OU (Estonia) under Apache-2.0. The content is educational: general engineering principles, processes, and tool-usage guidance. It is **not** ITAR/EAR-controlled technical data, and no proprietary standards text is reproduced. Standards are referenced and summarized only (see [STANDARDS.md](STANDARDS.md)). As published, without restrictions on further dissemination, this library falls within the EU dual-use "public domain" exclusion (Annex I General Technology Note, Regulation (EU) 2021/821). **Responsible use:** users are solely responsible for their own compliance. **Not affiliated with or endorsed by** RTCA, EUROCAE, SAE International, IAQG, EASA, FAA, or any government.

## Star request

If AeroSkills saves you an afternoon, star the repository. It tells us where to spend the next authoring pass.

## License

Apache-2.0. See [LICENSE](LICENSE) · [NOTICE](NOTICE) · [SECURITY.md](SECURITY.md) · [CONTRIBUTING.md](CONTRIBUTING.md) · [STANDARDS.md](STANDARDS.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
