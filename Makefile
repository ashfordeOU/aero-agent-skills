# AeroSkills eval harness spine (Phase 0)
# Full 5-gate contract: docs/harness-contract.md
# Wired today (stubs): gate 1 spec lint, gate 4 no-verbatim, gate 5 Hit@1 corpus.
# Gates 2 (description lint) and 3 (per-skill pytest contract) land real by 2026-09-04.
# Deterministic, no network calls.

.PHONY: validate lint-spec no-verbatim hit1

validate: lint-spec no-verbatim hit1
	@echo "AeroSkills validate: PASS (stub gates green; full contract docs/harness-contract.md)"

lint-spec:
	@scripts/gate-spec-lint.sh

no-verbatim:
	@scripts/gate-no-verbatim.sh

hit1:
	@scripts/gate-hit1-corpus.sh
