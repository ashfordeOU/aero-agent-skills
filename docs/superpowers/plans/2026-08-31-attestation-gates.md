# Attestation Gates + Number Hygiene — Implementation Plan (2026-08-31)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans.
> Steps use checkbox (`- [ ]`) syntax.

**Goal:** Ship number-snapshot.sh, numbers.yaml, brief-audit.sh, content-policy-sweep.sh,
`make attest`, TDD tests (TEST.md), CI wiring — all green at rest — and reconcile every
stale quoted number in repo docs to the canonical register.

**Architecture:** numbers.yaml = canonical register (tracked live repos + derived claims +
all quoted repos). number-snapshot.sh = live GitHub API check (offline mode for at-rest
determinism). brief-audit.sh = deterministic doc-vs-register scanner (python3 engine,
bash wrapper). content-policy-sweep.sh = red-flag grep per brief 06 §8.3.6/§8.3.9.
Makefile `attest` target + CI workflow. TDD: negative fixtures first, then green at rest.

**Tech Stack:** bash, python3 (stdlib + PyYAML), gh CLI (authed arjun-0077), make.

**Spec:** docs/superpowers/specs/2026-08-31-attestation-gates-design.md

## Global Constraints
- ONE main branch; every commit complete; clean at rest; commit subject ≤50 chars.
- Deterministic scripts: no LLM, no silent network fallback; API failure → exit 1 + message.
- Never touch research/briefs/06 policy semantics; the sweep scans publishable content
  (README, marketing/, docs/, development/builds/, skills/, support/), not research/.
- Canonical tracked values (baseline 2026-08-31): K-Dense 39,111; cyber 31,700;
  devideamax 21; ajhcs 22; derived largest=22; total aerospace≈228.
- gh is authed as arjun-0077; repo stays private.

---

### Task 1: Canonical register ops/automation/numbers.yaml

**Files:** Create `ops/automation/numbers.yaml`
**Interfaces:** Produces register consumed by snapshot/audit/sweep tests.

- [ ] **Step 1: Write the register** with `tracked`, `derived`, `repos` sections,
  values from live API run 2026-08-31 (already fetched): see design doc.
- [ ] **Step 2: Verify parse** `python3 -c "import yaml;yaml.safe_load(open('ops/automation/numbers.yaml'))"` exit 0.
- [ ] **Step 3: Commit** `git add ops/automation/numbers.yaml && git commit -m "ops: canonical number register"`

### Task 2: number-snapshot.sh (TDD)

**Files:** Create `ops/automation/test/fixture-tracked-wrong.yaml` (expected 100),
`ops/automation/number-snapshot.sh`
**Interfaces:** Consumes numbers.yaml tracked/derived; produces snapshot JSON in
ops/automation/state/; exit 0/1.

- [ ] **Step 1 (RED):** Run `NUMBERS_YAML=ops/automation/test/fixture-tracked-wrong.yaml ops/automation/number-snapshot.sh --live` → expect exit 1 (live 39k vs expected 100) with diff. (Script does not exist yet → run via `bash` after minimal stub? TDD: write the assertion as a test script first.)
- [ ] **Step 2 (GREEN):** Implement snapshot (gh api, tolerance check, snapshot JSON, --offline).
- [ ] **Step 3:** Offline RED: run with no snapshot → exit 1 clear message; then run live once → offline exit 0.
- [ ] **Step 4:** Live real run → exit 0, snapshot file created.
- [ ] **Step 5: Commit** with TEST.md entry.

### Task 3: brief-audit.sh (TDD)

**Files:** Create `ops/automation/test/fixture-brief-stale.md` (contains "38.0k★"),
`ops/automation/number_audit.py`, `ops/automation/brief-audit.sh`
**Interfaces:** Consumes numbers.yaml + doc roots; exit 0/1 with diffs.

- [ ] **Step 1 (RED):** `ops/automation/brief-audit.sh ops/automation/test/fixture-brief-stale.md` → exit 1 (K-Dense 38.0k vs 39,111).
- [ ] **Step 2 (GREEN):** Implement engine + wrapper.
- [ ] **Step 3:** Reconcile docs (briefs 01, 09, 00-CEO-REPORT md+html, joint/CEO reports,
  visual report, marketing note, briefs 04/10/11) to canonical 39,111 / 31,700 / 21 / 22 /
  22-largest / 228 with "live as of 2026-08-31" notes. Fix hashicorp 804→855, LunCoSim 97→105,
  3.2k forks→3.7k, 31k/31.2k→31.7k etc.
- [ ] **Step 4 (GREEN at rest):** Full scan → exit 0.
- [ ] **Step 5: Commit** (docs + engine + wrapper together, complete unit).

### Task 4: content-policy-sweep.sh (TDD)

**Files:** Create `ops/automation/test/fixture-policy-bad.md` (contains a banned compliance claim),
`ops/automation/content-policy-sweep.sh`
**Interfaces:** Scans publishable roots; exit 0/1 listing file:line.

- [ ] **Step 1 (RED):** sweep fixture → exit 1 listing the line.
- [ ] **Step 2 (GREEN):** Implement patterns per brief 06 §8.3.6/§8.3.9 + task list.
- [ ] **Step 3 (GREEN at rest):** Full publishable scan → exit 0 (README banner allowed).
- [ ] **Step 4: Commit** with TEST.md entry.

### Task 5: Makefile + CI + TEST.md

**Files:** Modify `Makefile`; Create `.github/workflows/attest.yml`,
`ops/automation/TEST.md`
- [ ] **Step 1:** Add `.PHONY: attest` + `attest: number-snapshot brief-audit content-policy-sweep`
  (number-snapshot runs `--offline`; a `snapshot-live` target runs the live check).
- [ ] **Step 2:** CI workflow runs `make validate && make attest` on push/PR.
- [ ] **Step 3:** Write TEST.md: negative fixture commands + observed exit codes + at-rest green.
- [ ] **Step 4:** `make validate` (exit 0) + `make attest` (exit 0) fresh; clean tree.
- [ ] **Step 5: Commit.**

### Task 6: Verify + ship

- [ ] **Step 1:** `git status --short` empty; `make validate; echo $?` = 0; `make attest; echo $?` = 0.
- [ ] **Step 2:** `git log --oneline -6`; capture commit sha(s); push to origin main.
- [ ] **Step 3:** Post milestone summary to group topic 160 (3-15 lines, evidence: exit codes + sha).
- [ ] **Step 4:** Write one lesson to profile memory.
