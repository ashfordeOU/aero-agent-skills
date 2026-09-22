# Aero Agent Skills eval harness (Phase 0 -> REAL)
# Full gate contract: docs/harness-contract.md (16 gates; this header is
# NOT the roster — `make validate` is. Kept in sync 2026-09-19.)
# All gates REAL as of the 09-04 milestone (landed early). Deterministic, no network.
#
#   gate 1 lint-spec      agentskills.io conformance (spec_lint.py)
#   gate 2 desc-lint      description what+when+trigger (desc_lint.py)
#   gate 3 pytest-contract  per-skill DAL A-E behavior test, stdlib unittest (skill-shipped scripts/test_*.py)
#   gate 4 no-verbatim    RTCA/SAE/IAQG copyright control, skills/ + docs/
#   gate 5 hit1           Hit@1 corpus eval, deterministic offline router
#   gate 6 independence   verifier independence over the evidence records
#   gate 7 release-law    version files sit at the corpus band
#   gate 8 portability    no strict inequality within 1e-12 of its bound
#                         (pow/log10 are not correctly rounded, so a test
#                          pinned to a last-place result passes on the
#                          build host and fails on the Linux CI runner)
#   gate 9 corpus-naming  one router fragment spelling per leaf
#   gate 10 no-inference  nothing on a verdict path may call a model (claim@1)
#   gate 11 slug-uniqueness  the flat fragment/install namespace is collision-free
#   gate 12 router-coverage-structure  the corpus file's own shape
#   gate 13 router-coverage-complete   every leaf is asserted by a case
#   gate 14 hermeticity   generated artefacts carry no machine-specific trace
#   gate 15 evidence-contract  the evidence record + regrade rules hold
#   gate 16 export-bundle the exported reference case set
#   gate 17 shipped-instructions  nothing shipped says cd into an author-only dir
#   gate 18 role-bindings  every leaf a paired role binds still exists
#   gate 19 obligations   every clause item a leaf declares is anchored to a
#                         step of its procedure (docs/OBLIGATIONS.md)

.PHONY: validate lint-spec desc-lint pytest-contract no-verbatim hit1 \
        independence release-law portability corpus-naming no-inference \
        slug-uniqueness router-coverage-structure router-coverage-complete \
        hermeticity evidence-contract export-bundle shipped-instructions \
        role-bindings role-bindings-refresh \
        determinism-perturb mutation-score gated-set-check stale-number-guard \
        publish-health release-machinery visuals-control \
        no-verbatim-strict router-coverage hit1-all negative-controls figure-audit \
        attest attest-strict snapshot-live number-snapshot-offline brief-audit \
        content-policy-sweep packs visuals visuals-check obligations

validate: lint-spec desc-lint pytest-contract no-verbatim hit1 independence release-law portability corpus-naming no-inference slug-uniqueness router-coverage-structure router-coverage-complete hermeticity evidence-contract export-bundle shipped-instructions role-bindings obligations
	@echo "Aero Agent Skills validate: PASS ($(words $^)/$(words $^) REAL gates green - docs/harness-contract.md)"

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

# Gate 8: a contract test must not depend on which side of the last bit a
# libm result lands on. See scripts/portability_check.py for the incident.
portability:
	@python3 scripts/portability_check.py

# Gate 9 (2026-09-13): one corpus fragment per leaf. leaf-create-gate.sh
# resolves coverage with a glob wildcarded on BOTH sides, so every invented
# prefix satisfied it - 14 concurrent builders filed one corpus under three
# different names and no gate went red.
corpus-naming:
	@python3 scripts/corpus_naming_check.py --strict

# Gate 10 (2026-09-19, claim@1): nothing reachable from a verdict may perform
# model inference. Parses with ast; does not grep.
no-inference:
	@python3 scripts/gate_no_inference.py

# Gate 11: leaf dirs are per-standard, but eval/hit1-<slug>.yaml and the
# installer's flattened folder are each ONE flat namespace. A duplicate slug
# silently overwrites another leaf's router fragment.
slug-uniqueness:
	@python3 tools/check_slug_uniqueness.py

# Gate 12: the corpus file's own shape. A future_pins entry came apart into
# document-root keys, PyYAML accepted it, gate 5 reads only tasks:, and nothing
# went red for 44 waves.
router-coverage-structure:
	@python3 tools/router_coverage.py --structure-only

# Gate 14: a pipeline can be bit-identical on one machine and still be
# non-hermetic -- it only looks stable because the machine did not move.
# Scans the three generated artefacts for embedded timestamps, absolute
# paths, hostnames, build ids and locale-dependent formatting.
hermeticity:
	@python3 tools/determinism/hermeticity.py \
	  docs/metrics.json \
	  packages/aero-agent-skills/manifest.json \
	  packages/jetbrains-plugin/src/main/resources/catalog/catalog.json

# Gate 15: the evidence record is the paid artefact -- a verdict somebody
# else can check. Its digest must not move with key order or float
# representation, and a regrade must issue a successor, never a mutation.
evidence-contract:
	@python3 -m unittest -q tools.evidence.tests.test_record \
	  tools.evidence.tests.test_regrade tools.evidence.tests.test_frontmatter
	@python3 tools/evidence/test_ed25519.py
	@python3 tools/evidence/test_signing.py
	@python3 tools/evidence/test_licence.py
	@python3 tools/evidence/test_report.py

# Gate 16: the exported reference case set and the tokenizer that reads it.
export-bundle:
	@python3 tools/export/test_export_bundle.py

# Gate 19: a leaf may bind the lettered items of an ECSS clause it makes the
# practitioner discharge (front matter `clauses:`). A binding is refused
# unless every declared item has a row in the leaf's `## Obligations` table
# pointing at a step that exists in its numbered procedure. It proves the
# claim is ANCHORED; whether the step discharges the item is the fidelity
# audit's question (tools/fidelity/). Then the gate's own detector suites.
obligations:
	@python3 tools/obligations/obligations_gate.py
	@python3 tools/obligations/test_obligations.py
	@python3 tools/obligations/test_earm_items.py

# ---- shipped, run on demand, deliberately NOT in validate ----
# Real and passing, but it re-runs the generators 40 times (~130s) to prove
# the output does not move with the environment. Too slow to put in front of
# every commit; run it when a generator changes.
determinism-perturb:
	@python3 tools/determinism/perturb.py

# A SAMPLED mutation score over the leaf corpus, not a pass/fail verdict.
# It cannot gate until somebody sets the bar it has to clear.
mutation-score:
	@python3 tools/mutation/mutation_score.py

# Attestation gates as of 2026-09-19: both now carry detector suites
# (ops/automation/test_gated_set_check.py, test_stale_number_guard.py), so
# both can be shown to return red and both are in `make attest`. Offline,
# so they belong there rather than in the release layer.
gated-set-check:
	@bash ops/automation/gated-set-check.sh

stale-number-guard:
	@bash ops/automation/stale-number-guard.sh

# Is what we built actually what is published?
#
# NOT in validate and NOT in attest: both are offline by contract and this
# needs the network. It is the RELEASE layer's check. On 2026-09-19 the
# public repo sat 18 hours and 672 leaves behind dev with every dev gate
# green, because three faults had each aborted the publish and nothing
# graded the shipping path. Exit 2 means "could not verify" and is not a
# pass. Runs from the hourly job; run it by hand any time.
publish-health:
	@python3 ops/automation/publish-health.py

# The publish machinery's OWN tests. Nine suites existed and nothing
# ran them, which is how a SIGPIPE that only fires on a large sync sat
# undetected until the first large sync -- and then blocked the release
# for a day. Offline (they build throwaway git repos), so attest is the
# right layer, not the networked release one.
release-machinery:
	@bash ops/automation/release_machinery.sh

router-coverage-complete:
	@python3 tools/router_coverage.py --no-score --max-uncovered 0

# ---- measured, deliberately NOT gating ----
router-coverage:
	@python3 tools/router_coverage.py

# Regression ratchet over both case sets. Raise as fragments are repaired,
# never lower. Not in validate: which set gates a release is a founder call.
hit1-all:
	@python3 tools/router_coverage.py --expect-executed-hits 6308 --expect-unexecuted-hits 0

# Gate 4 with UNCHECKED families treated as failures. Red on purpose until
# sources exist for the five unchecked families.
no-verbatim-strict:
	@scripts/gate-no-verbatim.sh --strict

# Prove each gate can still return RED. MUST NOT be a prerequisite of validate
# or attest: it invokes `make <gate>` in subprocesses.
negative-controls:
	@python3 tools/negative_controls/run_negative_controls.py

figure-audit:
	@python3 tools/figure_audit.py

no-verbatim:
	@scripts/gate-no-verbatim.sh

hit1:
	@scripts/gate-hit1-corpus.sh

independence:
	@scripts/gate-verify-independence.sh

# Release convention (founder 2026-09-03: every 100 skills = one minor bump).
# Was prose + a manual tool, so the fast lanes drifted silently. Blocking.
release-law:
	@python3 scripts/release-manager.py --check

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
	@python3 scripts/gen_jetbrains_catalog.py

# Negative control for the raster freshness the lock now enforces. Runs on a
# throwaway copy: a control that edits the real lock and restores it is one
# interrupt away from leaving the tree in the state it planted.
visuals-control:
	@bash ops/automation/visuals-control.sh

visuals-check:
	@python3 scripts/gen_visuals.py --selftest
	@python3 scripts/gen_visuals.py --check
	@python3 scripts/gen_manifest.py --check
	@python3 scripts/gen_jetbrains_catalog.py --check

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
# aero-agent-skills (founder 2026-09-02: the private dev repo stays test-only, the
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
attest: number-snapshot-offline brief-audit content-policy-sweep figure-audit gated-set-check stale-number-guard release-machinery
	@ops/automation/attest-summary.sh $(words $^)

# Opt-in: make a zero brief-audit denominator BLOCK.
attest-strict:
	@BRIEF_AUDIT_STRICT=1 $(MAKE) attest

snapshot-live:
	@ops/automation/number-snapshot.sh --live

number-snapshot-offline:
	@ops/automation/number-snapshot.sh --offline

brief-audit:
	@ops/automation/brief-audit.sh

content-policy-sweep:
	@ops/automation/content-policy-sweep.sh

# Nothing that ships may tell the reader to cd into a directory only
# the author has. Four shipped files opened their run instructions with
# `cd ~/AeroSkills`, which exists on no machine including this one.
shipped-instructions:
	@python3 scripts/gate_shipped_instructions.py

# The cross-corpus invariant, from this side. A leaf renamed or retired here
# breaks a role in a corpus that versions independently, and no gate in this
# repository would have noticed. ops/contracts/role-bindings.json is the
# roles corpus's declaration, pinned so the check runs offline inside the
# publish export -- reaching for a live corpus would make this a gate that
# can pass because something was reachable.
role-bindings:
	@python3 scripts/role_bindings_contract.py

role-bindings-refresh:
	@test -n "$(ROLES)" || { echo "FAIL: ROLES=<path to aero-agent-roles> is required" >&2; exit 2; }
	@python3 scripts/role_bindings_contract.py --refresh "$(ROLES)"
