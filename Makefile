# Aero Agent Skills eval harness (Phase 0 -> REAL)
# Full 5-gate contract: docs/harness-contract.md
# All gates REAL as of the 09-04 milestone (landed early). Deterministic, no network.
#
#   gate 1 lint-spec      agentskills.io conformance (spec_lint.py)
#   gate 2 desc-lint      description what+when+trigger (desc_lint.py)
#   gate 3 pytest-contract  per-skill DAL A-E behavior test, stdlib unittest (skill-shipped scripts/test_*.py)
#   gate 4 no-verbatim    RTCA/SAE/IAQG copyright control, skills/ + docs/
#   gate 5 hit1           Hit@1 corpus eval, deterministic offline router

.PHONY: validate lint-spec desc-lint pytest-contract no-verbatim hit1 \
        attest snapshot-live number-snapshot-offline brief-audit content-policy-sweep \
        packs visuals visuals-check

validate: lint-spec desc-lint pytest-contract no-verbatim hit1
	@echo "Aero Agent Skills validate: PASS (5/5 REAL gates green - docs/harness-contract.md)"

# Per-skill completeness standard (founder 2026-09-01): every leaf skill
# must have SKILL.md + scripts/ + contract test + no broken refs, with
# references/ + assets/ triaged as-needed. `make completeness` runs it;
# `make completeness --strict` fails on as-needed gaps.
completeness:
	@python3 scripts/skill-completeness.py

# Value-delta gate (founder 2026-08-31): every skill must prove it beats
# NOT using it. Deterministic proxy: contract-test pass (with) minus
# fact-vs-procedure baseline (without). Records land in eval/skill-eval/.
# `make value-delta` samples 10; `make value-delta-all` runs the whole tree.
value-delta:
	@python3 scripts/skill-eval.py --report --threshold 0.2

value-delta-all:
	@python3 scripts/skill-eval.py --all --report --threshold 0.2

lint-spec:
	@scripts/gate-spec-lint.sh

desc-lint:
	@scripts/gate-desc-lint.sh

pytest-contract:
	@scripts/gate-pytest-contract.sh

no-verbatim:
	@scripts/gate-no-verbatim.sh

hit1:
	@scripts/gate-hit1-corpus.sh

# Per-domain install inventory (founder directive 2026-08-31): list the
# domain packs and their leaf skills from frontmatter so an installer
# can install only the pack the user needs. Deterministic, offline.
packs:
	@python3 scripts/pack_inventory.py

# Generated visuals + README numbers (founder directive 2026-09-01): every
# number and chart in the README is computed from the tree by
# scripts/gen_visuals.py. `make visuals` regenerates; `make visuals-check`
# fails when any artifact is stale (run in CI). Deterministic, offline.
visuals:
	@python3 scripts/gen_visuals.py
	@python3 scripts/gen_manifest.py

visuals-check:
	@python3 scripts/gen_visuals.py --check
	@python3 scripts/gen_manifest.py --check

# npm package battery (founder 2026-09-02): manifest invariants, FULL Hit@1
# corpus replay through the JS router port (674/674 or fail), installer
# flatten + collision handling, MCP stdio round-trip, CLI smoke. Offline.
.PHONY: package-test
package-test:
	@node packages/aero-agent-skills/test/smoke.mjs

# GitHub About sidebar synced from docs/metrics.json (founder 2026-09-02).
# Needs network + the origin remote's token, so it is NOT an offline gate —
# run after leaf counts change so the public description never goes stale.
.PHONY: about
about:
	@bash ops/automation/update-about.sh

# Sync the dev/test tree to the public release repo, github.com/ashfordeOU/
# aero-agent-skills (founder 2026-09-02: arjun-0077 stays test-only, the
# public repo is where releases ship). Exports the allowlist, runs the
# FULL gate battery inside that export before touching git, then pushes
# through a persistent local mirror (fast-forward only, never force). A
# safe no-op when nothing on the allowlist changed. `publish-public-dry`
# stops after the gate battery — no mirror, no push. See
# ops/automation/publish-public.sh and docs/release-runbook-ashforde.md
# section 10 for the full reasoning.
.PHONY: publish-public publish-public-dry
publish-public:
	@bash ops/automation/publish-public.sh

publish-public-dry:
	@bash ops/automation/publish-public.sh --dry-run

# Attestation gates (milestone 2026-08-31): number snapshot (offline, at rest),
# brief-audit against the canonical register, content-policy sweep. All three
# deterministic, no network. `make snapshot-live` refreshes the evidence and
# runs BEFORE committing (a fresh state snapshot is part of each complete commit).
.PHONY: attest
attest: number-snapshot-offline brief-audit content-policy-sweep
	@echo "Aero Agent Skills attest: PASS (number snapshot offline + brief audit + content policy green)"

snapshot-live:
	@ops/automation/number-snapshot.sh --live

number-snapshot-offline:
	@ops/automation/number-snapshot.sh --offline

brief-audit:
	@ops/automation/brief-audit.sh

content-policy-sweep:
	@ops/automation/content-policy-sweep.sh
