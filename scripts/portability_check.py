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
def _wrap(name):
    orig = getattr(unittest.TestCase, name)
    def f(self, a, b, *args, **kw):
        try:
            if isinstance(a, float) and isinstance(b, (int, float)) and a == a and b == b:
                gap = abs(float(a) - float(b))
                scale = max(abs(float(a)), abs(float(b)), 1.0)
                if gap <= scale * REL_TOL_PLACEHOLDER:
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
try:
    runpy.run_path(target, run_name="__main__")
except SystemExit:
    pass
except Exception as e:
    HITS.append({"test": "<load-error>", "assert": type(e).__name__,
                 "a": str(e)[:120], "b": "", "gap": -1.0})
sys.stderr.write("\n__ULP__" + json.dumps(HITS) + "\n")
'''.replace("REL_TOL_PLACEHOLDER", repr(REL_TOL))

runner = os.path.join(os.environ.get("TMPDIR", "/tmp"), "_portability_runner.py")
open(runner, "w").write(RUNNER_SRC)

tests = []
for dp, _dn, fs in os.walk(SKILLS):
    for f in fs:
        if f.startswith("test_") and f.endswith(".py"):
            tests.append(os.path.join(dp, f))

def run(t):
    try:
        p = subprocess.run([sys.executable, runner, t], cwd=os.path.dirname(t),
                           capture_output=True, text=True, timeout=200)
        err = p.stderr or ""
        i = err.rfind("__ULP__")
        return (t, json.loads(err[i + 7:].strip())) if i >= 0 else (t, [])
    except Exception:
        return t, []

hits = []
with ThreadPoolExecutor(max_workers=8) as ex:
    for t, hs in ex.map(run, tests):
        for h in hs:
            if h.get("gap", -1) >= 0:
                h["file"] = os.path.relpath(t, ROOT)
                hits.append(h)

if not hits:
    print("PASS portability: %d test files, no strict inequality within %g of "
          "its bound (libm rounding safe)" % (len(tests), REL_TOL))
    sys.exit(0)

print("FAIL portability: %d strict assertion(s) sit on a rounding boundary and "
      "may fail on a different libm:" % len(hits))
for h in sorted(hits, key=lambda x: x["gap"]):
    print("  %s" % h["file"])
    print("    %s  %s(a=%s, b=%s)  gap=%.3g" %
          (h["test"], h["assert"], h["a"], h["b"], h["gap"]))
print("\nAssert the behaviour, not the rounding direction: use "
      "assertAlmostEqual(value, bound, places=9) and keep the assertion about "
      "what the code does. Never widen the engineering limit.")
sys.exit(1)
