#!/usr/bin/env bash
# Gate 3 (REAL): per-skill behavior contract tests (stdlib unittest, no network).
# Contract: docs/harness-contract.md gate 3. Discovers contract tests in
# scripts/test_*.py (repo-level) and any skill-shipped skills/**/scripts/test_*.py,
# enforces stdlib-only imports (scripts/check_stdlib_imports.py), runs each test
# under a driver this gate owns. Exit 0 = all tests pass.
#
# WHY A DRIVER AND NOT `python3 <test file>`
# ------------------------------------------
# This gate used to decide with `if ! python3 "$t"`, i.e. it trusted the exit
# code produced by the very module it was grading. Any module whose __main__
# block decouples a failing assertion from a non-zero exit -- unittest.main(
# exit=False), sys.exit(0), os._exit(0), try/except around main -- printed
# "FAILED (failures=N)" and still scored PASS.
#
# The driver below closes that by construction rather than by blacklist:
#
#   1. It imports the test module under a PRIVATE module name, so the module's
#      own `if __name__ == "__main__":` block is dead code and never executes.
#      Every variant of the defect lives in that block, so no variant of it --
#      including ones nobody has written yet -- can reach the verdict.
#   2. The verdict is computed by the driver from the unittest.TestResult object
#      the driver itself owns, never from anything the module prints or returns.
#   3. The driver reports on a sentinel line stamped with a per-file random
#      nonce. The driver deletes that nonce from the environment BEFORE the
#      module under test is imported, so the module cannot read it and cannot
#      forge or duplicate the line. A missing sentinel is red, and so is more
#      than one -- which is what catches a module that kills the interpreter
#      outright (os._exit(0) leaves exit status 0 but no sentinel).
#   4. A green additionally requires at least one NON-SKIPPED test to have run,
#      which closes the neighbouring hole: a "test" file that executes cleanly
#      while asserting nothing (no TestCase, empty discovery, everything
#      skipped) used to be counted as a passing contract test.
#
# A run is green only if ALL of: driver exit 0, exactly one sentinel carrying
# this run's nonce, sentinel status=ok, and effective>=1.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"

roots=("$repo_root/scripts")
if [ -d "$repo_root/skills" ]; then
  roots+=("$repo_root/skills")
fi

# The driver is kept inline (and passed via `python3 -c`) so this gate stays a
# single self-contained file and never writes anything into the tree.
read -r -d '' gate3_driver <<'GATE3_DRIVER_PY' || true
import importlib.util
import os
import sys
import unittest

# Popped before anything from the module under test is imported: the graded
# module must not be able to read, echo or forge this run's nonce.
_NONCE = os.environ.pop("GATE3_NONCE", "")


def _die(msg, code=2):
    sys.stderr.write("gate3-driver: %s\n" % msg)
    return code


def main():
    if not _NONCE:
        return _die("GATE3_NONCE is not set in the environment")
    if len(sys.argv) != 2:
        return _die("usage: gate3-driver <test_file.py>")
    path = os.path.abspath(sys.argv[1])
    if not os.path.isfile(path):
        return _die("not a file: %s" % path)

    # Reproduce the import environment of `python3 <test file>`: the test
    # file's own directory first, and the current working directory NOT on
    # the path (python3 -c would otherwise add it and mask a missing sibling).
    sys.path = [p for p in sys.path if p not in ("", ".")]
    sys.path.insert(0, os.path.dirname(path))

    mod_name = "gate3_module_under_test"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        return _die("cannot build an import spec for %s" % path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    try:
        # BaseException, not Exception: a module-level sys.exit(0) raises
        # SystemExit and must be reported, not silently honoured.
        spec.loader.exec_module(module)
    except BaseException as exc:
        return _die("import raised %s: %s" % (type(exc).__name__, exc), 1)

    try:
        suite = unittest.TestLoader().loadTestsFromModule(module)
    except BaseException as exc:
        return _die("collection raised %s: %s" % (type(exc).__name__, exc), 1)

    try:
        result = unittest.TextTestRunner(stream=sys.stderr, verbosity=1).run(suite)
    except BaseException as exc:
        return _die("run raised %s: %s" % (type(exc).__name__, exc), 1)

    tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(getattr(result, "skipped", []))
    unexpected = len(getattr(result, "unexpectedSuccesses", []))
    effective = tests - skipped
    ok = (
        result.wasSuccessful()
        and failures == 0
        and errors == 0
        and unexpected == 0
        and effective >= 1
    )
    sys.stdout.write(
        "GATE3_VERDICT %s status=%s tests=%d failures=%d errors=%d "
        "skipped=%d unexpected=%d effective=%d\n"
        % (
            _NONCE,
            "ok" if ok else "fail",
            tests,
            failures,
            errors,
            skipped,
            unexpected,
            effective,
        )
    )
    sys.stdout.flush()
    return 0 if ok else 1


sys.exit(main())
GATE3_DRIVER_PY

fail=0
ran=0
total_tests=0
failed_files=()

while IFS= read -r -d '' t; do
  ran=$((ran + 1))
  echo "gate3: running $t"

  file_bad=0
  if ! python3 "$repo_root/scripts/check_stdlib_imports.py" "$t"; then
    fail=1
    file_bad=1
    failed_files+=("$t [stdlib-imports]")
  fi

  nonce="g3-$$-${ran}-${RANDOM}${RANDOM}${RANDOM}"
  set +e
  out="$(GATE3_NONCE="$nonce" python3 -c "$gate3_driver" "$t" 2>&1)"
  rc=$?
  set -e

  sentinels="$(printf '%s\n' "$out" | grep -c "^GATE3_VERDICT ${nonce} " || true)"
  line="$(printf '%s\n' "$out" | grep "^GATE3_VERDICT ${nonce} " | head -n 1 || true)"
  status="$(printf '%s\n' "$line" | sed -n 's/.* status=\([a-z]*\).*/\1/p')"
  n_tests="$(printf '%s\n' "$line" | sed -n 's/.* tests=\([0-9]*\).*/\1/p')"
  n_eff="$(printf '%s\n' "$line" | sed -n 's/.* effective=\([0-9]*\).*/\1/p')"

  reason=""
  if [ "$sentinels" != "1" ]; then
    reason="driver verdict absent or duplicated (sentinels=${sentinels}, exit=${rc}) -- the test module did not run to completion under the gate driver"
  elif [ -z "${n_eff:-}" ] || [ "$n_eff" -lt 1 ]; then
    reason="no non-skipped test executed (tests=${n_tests:-0}, effective=${n_eff:-0}) -- a contract test file must assert something"
  elif [ "$status" != "ok" ]; then
    counts="$(printf '%s\n' "$line" | sed -n 's/^GATE3_VERDICT [^ ]* //p')"
    reason="assertions failed -- ${counts}"
  elif [ "$rc" -ne 0 ]; then
    reason="driver exited ${rc} despite status=ok"
  fi

  if [ -n "$reason" ]; then
    fail=1
    file_bad=1
    failed_files+=("$t [${reason%%:*}]")
    printf '%s\n' "$out" >&2
    echo "gate3: FAIL $t -- $reason" >&2
  else
    total_tests=$((total_tests + n_tests))
    echo "gate3: ok $t (tests=${n_tests}, effective=${n_eff})"
  fi
done < <(find "${roots[@]}" -name 'test_*.py' -print0 2>/dev/null | sort -z)

if [ "$ran" -eq 0 ]; then
  echo "FAIL gate3-pytest-contract: no contract tests found (every skill ships skills/<path>/scripts/test_*.py)" >&2
  exit 1
fi
if [ "$fail" -ne 0 ]; then
  echo "" >&2
  echo "gate3: ${#failed_files[@]} of ${ran} contract test file(s) failed:" >&2
  for f in "${failed_files[@]}"; do
    echo "  - $f" >&2
  done
  echo "FAIL gate3-pytest-contract: one or more test runs failed" >&2
  exit 1
fi
echo "PASS gate3-pytest-contract: ${ran} contract test file(s), ${total_tests} test(s) passed (stdlib unittest, offline)"
