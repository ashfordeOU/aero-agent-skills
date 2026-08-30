# AeroSkills eval harness (Phase 0 -> REAL)
# Full 5-gate contract: docs/harness-contract.md
# All gates REAL as of the 09-04 milestone (landed early). Deterministic, no network.
#
#   gate 1 lint-spec      agentskills.io conformance (spec_lint.py)
#   gate 2 desc-lint      description what+when+trigger (desc_lint.py)
#   gate 3 pytest-contract  DAL A-E behavior test, stdlib unittest (do178c_levels.py)
#   gate 4 no-verbatim    RTCA/SAE/IAQG copyright control, skills/ + docs/
#   gate 5 hit1           Hit@1 corpus eval, deterministic offline router

.PHONY: validate lint-spec desc-lint pytest-contract no-verbatim hit1

validate: lint-spec desc-lint pytest-contract no-verbatim hit1
	@echo "AeroSkills validate: PASS (5/5 REAL gates green - docs/harness-contract.md)"

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
