#!/usr/bin/env python3
"""Gate: no test may assert a strict inequality that sits within a few ULP
of its bound.

Why this gate exists
--------------------
math.pow, 10**x and math.log10 are NOT correctly rounded. Which side of the
last bit a result lands on differs between libm implementations, so a value
that is a few ULP below a round number on macOS/arm64 can be exactly equal to
it on the Linux/x86-64 CI runner. A test that asserts the STRICT inequality at
that boundary passes on the build host and fails in CI - and because the local
gate battery runs on the build host, nothing catches it before publish.

Measured 2026-09-13: e20-launch-system-emc-compatibility asserted
`assertLess(raw, 10.0)` on 20*log10() of a field built from 10**(-db/20).
Locally raw was a few ULP under ten; on the runner it was exactly ten. Four
consecutive public commits went red on that single line.

What to do when this gate fires
-------------------------------
Assert the BEHAVIOUR, not the rounding direction. If the case is meant to sit
on the boundary, use assertAlmostEqual(value, bound, places=9) and keep the
assertion about what the code then does (a finding raised or absorbed). Never
widen the engineering limit to make it pass.

Measurement honesty
-------------------
The gate can only grade comparisons it actually observes, so it reports the
number of comparison assertions it MEASURED, not the number of files it
walked. A suite that could not be executed (load error, timeout, lost marker)
is a hole in the measurement, not a pass, and fails the gate.

Usage: portability_check.py [skills_dir]   (exit 1 if any near-boundary hit)
"""
import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "skills")
# 1 ULP is ~2.2e-16 relative; 1e-12 leaves four orders of head-room.
REL_TOL = 1e-12

RUNNER_SRC = r'''
import json, os, runpy, sys, unittest
HITS = []
SEEN = [0]
def _wrap(name):
    orig = getattr(unittest.TestCase, name)
    def f(self, a, b, *args, **kw):
        try:
            SEEN[0] += 1
            # Two detector artifacts, removed 2026-09-19 on the first run this
            # gate ever actually performed (it had measured zero assertions):
            #  - the `1.0` floor in scale made the rule ABSOLUTE below 1.0, so
            #    abs(residual) < 1e-12 against an exactly-zero residual was
            #    flagged as near-boundary. 192 rows across 67 files, reproduced.
            #  - an infinite operand satisfied inf <= inf * tol. 1 row.
            # Neither changes REL_TOL; both remove false positives, so the gate
            # gets STRICTER in meaning while flagging fewer rows.
            import math as _math
            if (isinstance(a, float) and isinstance(b, (int, float))
                    and _math.isfinite(a) and _math.isfinite(b)):
                gap = abs(float(a) - float(b))
                scale = max(abs(float(a)), abs(float(b)))
                if scale > 0.0 and gap <= scale * REL_TOL_PLACEHOLDER:
                    HITS.append({"test": self.id(), "assert": name,
                                 "a": repr(a), "b": repr(b), "gap": gap})
        except Exception:
            pass
        return orig(self, a, b, *args, **kw)
    setattr(unittest.TestCase, name, f)
for n in ("assertLess", "assertGreater", "assertLessEqual", "assertGreaterEqual"):
    _wrap(n)
target = sys.argv[1]
sys.path.insert(0, os.path.dirname(target))
# unittest.main() parses sys.argv. Left as [runner, target] it reads the target
# PATH as a test NAME, the loader turns it into a _FailedTest and not one test
# method runs - which measured zero of the corpus while printing a green.
sys.argv = [target]
ERR = ""
try:
    runpy.run_path(target, run_name="__main__")
except SystemExit:
    pass
except BaseException as e:
    ERR = "%s: %s" % (type(e).__name__, str(e)[:160])
sys.stderr.write("\n__ULP__" + json.dumps(
    {"hits": HITS, "seen": SEEN[0], "err": ERR}) + "\n")
'''.replace("REL_TOL_PLACEHOLDER", repr(REL_TOL))

runner = os.path.join(os.environ.get("TMPDIR", "/tmp"), "_portability_runner.py")
open(runner, "w").write(RUNNER_SRC)

tests = []
for dp, _dn, fs in os.walk(SKILLS):
    for f in fs:
        if f.startswith("test_") and f.endswith(".py"):
            tests.append(os.path.join(dp, f))
tests.sort()

def run(t):
    try:
        p = subprocess.run([sys.executable, runner, t], cwd=os.path.dirname(t),
                           capture_output=True, text=True, timeout=200)
    except subprocess.TimeoutExpired:
        return t, {"hits": [], "seen": 0, "err": "Timeout: exceeded 200s"}
    except Exception as e:
        return t, {"hits": [], "seen": 0,
                   "err": "%s: %s" % (type(e).__name__, str(e)[:160])}
    err = p.stderr or ""
    i = err.rfind("__ULP__")
    if i < 0:
        return t, {"hits": [], "seen": 0,
                   "err": "NoMarker: runner produced no result (rc=%s)" % p.returncode}
    try:
        return t, json.loads(err[i + 7:].strip())
    except Exception as e:
        return t, {"hits": [], "seen": 0,
                   "err": "BadMarker: %s" % str(e)[:160]}

hits = []
unmeasured = []
measured = 0
suites = 0
with ThreadPoolExecutor(max_workers=max(8, (os.cpu_count() or 8))) as ex:
    for t, res in ex.map(run, tests):
        rel = os.path.relpath(t, ROOT)
        measured += res.get("seen", 0)
        if res.get("err"):
            unmeasured.append((rel, res["err"]))
        else:
            suites += 1
        for h in res.get("hits", []):
            if h.get("gap", -1) >= 0:
                h["file"] = rel
                hits.append(h)

if not hits and not unmeasured:
    print("PASS portability: %d suites executed, %d inequality assertion(s) "
          "measured, none within %g of its bound (libm rounding safe)"
          % (suites, measured, REL_TOL))
    sys.exit(0)

if hits:
    print("FAIL portability: %d strict assertion(s) sit on a rounding boundary "
          "and may fail on a different libm:" % len(hits))
    for h in sorted(hits, key=lambda x: x["gap"]):
        print("  %s" % h["file"])
        print("    %s  %s(a=%s, b=%s)  gap=%.3g" %
              (h["test"], h["assert"], h["a"], h["b"], h["gap"]))
    print("\nAssert the behaviour, not the rounding direction: use "
          "assertAlmostEqual(value, bound, places=9) and keep the assertion "
          "about what the code does. Never widen the engineering limit.")

if unmeasured:
    print("\nFAIL portability: %d suite(s) could not be executed, so their "
          "assertions were NOT measured (a hole, not a pass):" % len(unmeasured))
    for rel, err in sorted(unmeasured):
        print("  %s\n    %s" % (rel, err))

print("\nmeasured %d inequality assertion(s) across %d executed suite(s)"
      % (measured, suites))
sys.exit(1)
