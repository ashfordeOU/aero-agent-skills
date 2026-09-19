#!/usr/bin/env python3
"""Observation: the expensive half, run once, against the corpus.

An evidence record separates two things that verification usually welds
together:

  OBSERVING   measuring facts about a leaf.  Reading files, running its
              contract test, instrumenting its float comparisons.  This is
              the work.  It needs the corpus present and it costs time.

  CHECKING    deciding whether those facts pass.  A pure function of the
              stored observation and a parameter set.  It needs nothing but
              the record.

Everything in this module is the first kind.  The rule that keeps regrade
possible is that an observation must be THRESHOLD-FREE: it records what was
measured, never whether the measurement was acceptable.  "word_count": 63 can
be re-decided against any word limit forever.  "words_ok": true can be
re-decided against nothing.

Where an observation cannot be made completely threshold-free - the float
comparison gaps, where keeping every one of thousands would bloat the record
- it records the boundary of its own completeness (gap_floor, all_recorded)
so a checker can tell whether the stored evidence is sufficient for the
question being asked and return INDETERMINATE when it is not.

Durations are not observations.  A wall-clock number is not reproducible, so
it is carried in a separate telemetry block that no checker may read.
"""

import ast
import json
import os
import re
import subprocess
import sys
import time

from . import canonical, frontmatter

OBSERVER_SET_VERSION = "1.0.0"

OBSERVATION_SPECS = {
    "spec-shape": "1.0.0",
    "desc-lint": "1.0.0",
    "contract-test": "1.0.0",
    "near-boundary": "1.0.0",
    "import-surface": "1.0.0",
    "marker-scan": "1.0.0",
}

# The action-verb vocabulary is versioned because it is baked into the
# measurement: the observation records which verbs were found, not the whole
# description, so a checker that wants a DIFFERENT vocabulary cannot be
# answered from a stored observation and must say so.
ACTION_VERB_VOCABULARY_VERSION = "1.0.0"
ACTION_VERBS = (
    "allocate analyze assess audit automate build calculate calibrate classify "
    "compute configure convert coordinate create define deploy derive design "
    "determine develop document draft evaluate execute extract generate guide "
    "identify implement maintain manage map model monitor optimize perform plan "
    "prepare produce review run scope simulate size structure support synthesize "
    "test troubleshoot validate verify write estimate"
).split()

# Imports are read with ast, not with a line regex.  A regex over source
# also matches English: a docstring line beginning "from the manufacturer's
# data" reports an import of "the".  Measured on this corpus, a line regex
# invents 130 imports of "the", 29 of "a" and dozens of other prose words
# alongside the real ones.  An observation that noisy cannot support a
# verdict, and no later checker fix can clean it up.
QUOTED_RE = re.compile(r"“([^”]{1,4000})”|\"([^\"\n]{1,4000})\"")

# Copyright-boilerplate markers.  Each pattern is assembled from fragments so
# that the phrase it looks for never appears contiguously in this file: the
# shipped no-verbatim gate greps for several of these same phrases, and a
# detector that trips the detector it mirrors is a defect waiting to happen
# the day someone widens that gate's scan roots.
MARKER_SET_VERSION = "1.0.0"
MARKERS = (
    ("all-rights-reserved", r"all\s+rights\s+" + "reserved"),
    ("redistribution-bar", r"not\s+for\s+" + "redistribution"),
    ("single-user-licence", r"single[-\s]user\s+licen[sc]e"),
    ("confidentiality-banner", r"proprietary\s+and\s+" + "confidential"),
    ("licence-agreement-banner", r"electronic\s+licen[sc]e\s+" + "agreement"),
    ("rights-management-banner", r"drm[-\s]" + "protected"),
    ("licensed-to-banner", r"this\s+document\s+is\s+licensed\s+" + "to"),
    ("dated-copyright-notice", r"copyright\s*(?:©|\(c\))\s*\d{4}"),
)
_COMPILED_MARKERS = tuple((mid, re.compile(pat, re.IGNORECASE)) for mid, pat in MARKERS)
MARKER_SET_DIGEST = canonical.digest([{"id": m, "pattern": p} for m, p in MARKERS])

SENTINEL = "__AERO_EVIDENCE__"
NEAR_BOUNDARY_CAP = 64
TEST_TIMEOUT_SECONDS = 180

# Runs one contract test in its own interpreter and reports both the unittest
# outcome and every float comparison gap the test made.  One execution, two
# observations: re-running the corpus twice to answer two questions is exactly
# the cost this design exists to remove.
#
# The assert wrapping mirrors the shipped portability gate (a float first
# argument against an int-or-float bound) so that a stored near-boundary
# observation means the same thing that gate means.
_RUNNER_SOURCE = r'''
import io, json, os, runpy, sys, unittest

GAPS = []
RESULTS = []
LOAD_ERROR = [None]


def _wrap(name):
    original = getattr(unittest.TestCase, name)

    def wrapper(self, first, second, *args, **kwargs):
        try:
            if isinstance(first, float) and isinstance(second, (int, float)) \
                    and not isinstance(second, bool):
                a, b = float(first), float(second)
                if a == a and b == b and abs(a) != float("inf") and abs(b) != float("inf"):
                    scale = max(abs(a), abs(b), 1.0)
                    GAPS.append([abs(a - b) / scale, self.id(), name])
        except Exception:
            pass
        return original(self, first, second, *args, **kwargs)

    wrapper.__name__ = name
    setattr(unittest.TestCase, name, wrapper)


for _name in ("assertLess", "assertGreater", "assertLessEqual", "assertGreaterEqual"):
    _wrap(_name)


class Collector(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outcomes = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.outcomes.append([test.id(), "ok"])

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.outcomes.append([test.id(), "fail"])

    def addError(self, test, err):
        super().addError(test, err)
        self.outcomes.append([test.id(), "error"])

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.outcomes.append([test.id(), "skip"])

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.outcomes.append([test.id(), "expected-failure"])

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.outcomes.append([test.id(), "unexpected-success"])


def _runner():
    return unittest.TextTestRunner(
        stream=io.StringIO(), verbosity=0, resultclass=Collector
    )


_real_main = unittest.main


def _patched_main(*args, **kwargs):
    kwargs["exit"] = False
    kwargs["testRunner"] = _runner()
    program = _real_main(*args, **kwargs)
    RESULTS.append(program.result)
    return program


unittest.main = _patched_main

target = sys.argv[1]
# Present the target exactly as a direct run would: `python3 test_x.py`.
# Left as [runner, target], unittest.main() reads the path out of argv and
# tries to load it as a test NAME, which produces a single synthetic error
# and no real run - green-looking machinery measuring nothing.
sys.argv = [target]
sys.path.insert(0, os.path.dirname(os.path.abspath(target)))
_stdout = sys.stdout
sys.stdout = io.StringIO()
namespace = None
try:
    namespace = runpy.run_path(target, run_name="__main__")
except SystemExit:
    pass
except BaseException as exc:
    LOAD_ERROR[0] = "%s: %s" % (type(exc).__name__, str(exc)[:200])
finally:
    sys.stdout = _stdout

if not RESULTS and namespace and LOAD_ERROR[0] is None:
    # The module never called unittest.main(); load its cases directly.
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for value in namespace.values():
        if isinstance(value, type) and issubclass(value, unittest.TestCase):
            suite.addTests(loader.loadTestsFromTestCase(value))
    RESULTS.append(_runner().run(suite))

outcomes = []
tests_run = failures = errors = skipped = expected = unexpected = 0
for result in RESULTS:
    tests_run += result.testsRun
    failures += len(result.failures)
    errors += len(result.errors)
    skipped += len(result.skipped)
    expected += len(result.expectedFailures)
    unexpected += len(result.unexpectedSuccesses)
    outcomes.extend(getattr(result, "outcomes", []))

payload = {
    "load_error": LOAD_ERROR[0],
    "tests_run": tests_run,
    "failures": failures,
    "errors": errors,
    "skipped": skipped,
    "expected_failures": expected,
    "unexpected_successes": unexpected,
    "outcomes": sorted(outcomes),
    "comparisons_total": len(GAPS),
    "gaps": sorted(GAPS)[:CAP_PLACEHOLDER],
}
sys.stderr.write("\n" + "SENTINEL_PLACEHOLDER" + json.dumps(payload) + "\n")
'''


_ABSOLUTE_IN_ID = re.compile(r"(?:/[^\s:]+)+")


def _sanitise(test_id):
    """Keep issuer filesystem paths out of a test identifier.

    A loader error names the file it failed on, and that name is an absolute
    path.  A record must be handable to a third party, so the path is replaced
    rather than carried.
    """
    return _ABSOLUTE_IN_ID.sub("<path>", test_id)


def _runner_path():
    base = os.environ.get("TMPDIR") or "/tmp"
    path = os.path.join(base, "_aero_evidence_runner.py")
    source = _RUNNER_SOURCE.replace("CAP_PLACEHOLDER", str(NEAR_BOUNDARY_CAP)).replace(
        "SENTINEL_PLACEHOLDER", SENTINEL
    )
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(source)
    return path


def _leaf_python_files(root, leaf_ref):
    base = os.path.join(root, leaf_ref.replace("/", os.sep))
    found = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for name in sorted(filenames):
            if name.endswith(".py"):
                absolute = os.path.join(dirpath, name)
                found.append(os.path.relpath(absolute, base).replace(os.sep, "/"))
    return sorted(found)


def observe_spec_shape(root, leaf_ref, fm, body):
    base = os.path.join(root, leaf_ref.replace("/", os.sep))
    python_files = _leaf_python_files(root, leaf_ref)
    standards = []
    for item in fm.get("standards") or []:
        if isinstance(item, dict):
            standards.append(
                {
                    "id": str(item.get("id")),
                    "reference_only": bool(item.get("reference-only")),
                }
            )
        elif item:
            standards.append({"id": str(item), "reference_only": False})
    metadata = fm.get("metadata") if isinstance(fm.get("metadata"), dict) else {}
    refs = []
    for line_no, line in enumerate(body.split("\n"), 1):
        for match in re.finditer(r"\]\(([^)\s]+)\)", line):
            refs.append(match.group(1))
    absolute_refs = [r for r in refs if r.startswith("/")]
    return {
        "observation": "spec-shape",
        "version": OBSERVATION_SPECS["spec-shape"],
        "keys_present": sorted(str(k) for k in fm.keys()),
        "name": fm.get("name"),
        "directory_name": leaf_ref.rsplit("/", 1)[-1],
        "name_matches_directory": fm.get("name") == leaf_ref.rsplit("/", 1)[-1],
        "description_chars": len(fm.get("description") or ""),
        "body_lines": len(body.split("\n")),
        "license": fm.get("license"),
        "compliance": fm.get("compliance"),
        "gated": bool(fm.get("gated")),
        "domain": fm.get("domain"),
        "pack": fm.get("pack"),
        "standards": standards,
        "metadata_version": metadata.get("version"),
        "metadata_author_present": bool(metadata.get("author")),
        "has_scripts_dir": os.path.isdir(os.path.join(base, "scripts")),
        "logic_modules": [
            p for p in python_files if not p.rsplit("/", 1)[-1].startswith("test_")
        ],
        "test_modules": [
            p for p in python_files if p.rsplit("/", 1)[-1].startswith("test_")
        ],
        "markdown_link_count": len(refs),
        "absolute_link_count": len(absolute_refs),
    }


def observe_description(fm):
    description = fm.get("description") or ""
    words = description.split()
    lowered = description.lower()
    found = sorted({verb for verb in ACTION_VERBS if re.search(r"\b%s\b" % verb, lowered)})
    trigger = re.search(r"trigger", description, re.IGNORECASE)
    if trigger:
        tail = description[trigger.end():]
        keywords = [k.strip(" :,;.") for k in re.split(r"[,;:]", tail)]
        keyword_count = len([k for k in keywords if k])
    else:
        keyword_count = 0
    return {
        "observation": "desc-lint",
        "version": OBSERVATION_SPECS["desc-lint"],
        "word_count": len(words),
        "char_count": len(description),
        "present": bool(description),
        "action_verbs_found": found,
        "action_verb_vocabulary_version": ACTION_VERB_VOCABULARY_VERSION,
        "has_use_when_clause": bool(re.search(r"use when", description, re.IGNORECASE)),
        "has_trigger_label": bool(trigger),
        "trigger_keyword_count": keyword_count,
    }


def top_level_imports(source):
    """Root module names imported by source.  Returns (names, parse_error).

    A relative import is reported as "." - it resolves inside the leaf and is
    not a third-party dependency.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [], "SyntaxError: %s" % (str(exc)[:160],)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                names.add(".")
            elif node.module:
                names.add(node.module.split(".")[0])
    return sorted(names), None


def observe_imports(root, leaf_ref):
    base = os.path.join(root, leaf_ref.replace("/", os.sep))
    modules = []
    for relative in _leaf_python_files(root, leaf_ref):
        absolute = os.path.join(base, relative.replace("/", os.sep))
        with open(absolute, "r", encoding="utf-8") as fh:
            source = fh.read()
        names, parse_error = top_level_imports(source)
        directory = os.path.dirname(absolute)
        siblings = sorted(
            n for n in names if os.path.isfile(os.path.join(directory, n + ".py"))
        )
        modules.append(
            {
                "module": relative,
                "imports": names,
                "sibling_resolved": siblings,
                "parse_error": parse_error,
            }
        )
    return {
        "observation": "import-surface",
        "version": OBSERVATION_SPECS["import-surface"],
        "extraction": "ast",
        "modules": modules,
    }


def observe_markers(root, leaf_ref):
    base = os.path.join(root, leaf_ref.replace("/", os.sep))
    targets = []
    skill_md = os.path.join(base, "SKILL.md")
    if os.path.isfile(skill_md):
        targets.append("SKILL.md")
    references = os.path.join(base, "references")
    if os.path.isdir(references):
        for dirpath, dirnames, filenames in os.walk(references):
            dirnames[:] = sorted(dirnames)
            for name in sorted(filenames):
                if name.endswith((".md", ".txt")):
                    absolute = os.path.join(dirpath, name)
                    targets.append(os.path.relpath(absolute, base).replace(os.sep, "/"))
    counts = {marker_id: 0 for marker_id, _ in MARKERS}
    scanned = []
    longest_quote = 0
    quotes_over_40 = 0
    for relative in sorted(targets):
        absolute = os.path.join(base, relative.replace("/", os.sep))
        with open(absolute, "r", encoding="utf-8") as fh:
            text = fh.read()
        scanned.append(
            {
                "path": relative,
                "chars": len(text),
                "digest": canonical.digest_bytes(text.encode("utf-8")),
            }
        )
        for marker_id, pattern in _COMPILED_MARKERS:
            counts[marker_id] += len(pattern.findall(text))
        # Quoted spans are measured over PROSE only.  A SKILL.md description
        # is a YAML double-quoted scalar: counting its delimiters as a
        # quotation makes every leaf in the corpus look like it reproduces
        # six hundred characters of somebody else's document.
        prose = text
        if relative == "SKILL.md":
            try:
                _fm, prose = frontmatter.split(text)
            except frontmatter.FrontmatterError:
                prose = text
        for match in QUOTED_RE.finditer(prose):
            span = match.group(1) or match.group(2) or ""
            longest_quote = max(longest_quote, len(span))
            if len(span) > 40:
                quotes_over_40 += 1
    return {
        "observation": "marker-scan",
        "version": OBSERVATION_SPECS["marker-scan"],
        "marker_set_version": MARKER_SET_VERSION,
        "marker_set_digest": MARKER_SET_DIGEST,
        "marker_ids": sorted(counts),
        "marker_counts": counts,
        "files_scanned": scanned,
        "longest_quoted_span_chars": longest_quote,
        "quoted_spans_over_40_chars": quotes_over_40,
        "quote_scan_scope": "prose only; SKILL.md front matter is excluded",
    }


def run_contract_tests(root, leaf_ref, test_modules, runner=None):
    """Execute the leaf's contract tests once; return (contract, boundary, telemetry)."""
    runner = runner or _runner_path()
    base = os.path.join(root, leaf_ref.replace("/", os.sep))
    modules, gaps, telemetry = [], [], []
    comparisons_total = 0
    for relative in test_modules:
        absolute = os.path.join(base, relative.replace("/", os.sep))
        started = time.monotonic()
        try:
            completed = subprocess.run(
                [sys.executable, runner, absolute],
                capture_output=True,
                text=True,
                timeout=TEST_TIMEOUT_SECONDS,
                cwd=root,
            )
            stderr = completed.stdout + completed.stderr
            returncode = completed.returncode
        except subprocess.TimeoutExpired:
            stderr, returncode = "", -1
        elapsed_ms = int((time.monotonic() - started) * 1000)
        payload = None
        for line in stderr.splitlines():
            if line.startswith(SENTINEL):
                payload = json.loads(line[len(SENTINEL):])
        if payload is None:
            modules.append(
                {
                    "module": relative,
                    "instrumented": False,
                    "load_error": "runner produced no observation",
                    "tests_run": 0,
                    "failures": 0,
                    "errors": 1,
                    "skipped": 0,
                    "expected_failures": 0,
                    "unexpected_successes": 0,
                    "outcomes": [],
                }
            )
        else:
            modules.append(
                {
                    "module": relative,
                    "instrumented": True,
                    "load_error": payload["load_error"],
                    "tests_run": payload["tests_run"],
                    "failures": payload["failures"],
                    "errors": payload["errors"],
                    "skipped": payload["skipped"],
                    "expected_failures": payload["expected_failures"],
                    "unexpected_successes": payload["unexpected_successes"],
                    "outcomes": [
                        {"test": _sanitise(test_id), "status": status}
                        for test_id, status in payload["outcomes"]
                    ],
                }
            )
            comparisons_total += payload["comparisons_total"]
            for gap, test_id, assertion in payload["gaps"]:
                gaps.append((gap, _sanitise(test_id), assertion, relative))
        telemetry.append(
            {"module": relative, "wall_ms": elapsed_ms, "returncode": returncode}
        )

    def total(field):
        return sum(m[field] for m in modules)

    contract = {
        "observation": "contract-test",
        "version": OBSERVATION_SPECS["contract-test"],
        "runner": "stdlib-unittest",
        "modules": modules,
        "totals": {
            "modules": len(modules),
            "tests_run": total("tests_run"),
            "failures": total("failures"),
            "errors": total("errors"),
            "skipped": total("skipped"),
            "expected_failures": total("expected_failures"),
            "unexpected_successes": total("unexpected_successes"),
        },
    }

    gaps.sort(key=lambda item: (item[0], item[1], item[2]))
    kept = gaps[:NEAR_BOUNDARY_CAP]
    all_recorded = comparisons_total <= NEAR_BOUNDARY_CAP
    boundary = {
        "observation": "near-boundary",
        "version": OBSERVATION_SPECS["near-boundary"],
        "mirrors_gate": "portability",
        "comparisons_total": comparisons_total,
        "recorded_cap": NEAR_BOUNDARY_CAP,
        "all_recorded": all_recorded,
        # Every comparison with a relative gap at or below gap_floor is in the
        # list.  A checker asked about a tolerance ABOVE this floor cannot be
        # answered from the record and must say so rather than guess.
        "gap_floor": None if all_recorded else canonical.num(kept[-1][0]),
        "tightest": [
            {
                "relative_gap": canonical.num(gap),
                "test": test_id,
                "assertion": assertion,
                "module": module,
            }
            for gap, test_id, assertion, module in kept
        ],
    }
    return contract, boundary, telemetry


def observe_leaf(root, leaf_ref, runner=None):
    """Measure one leaf.  Returns (observations, telemetry)."""
    skill_path = os.path.join(root, leaf_ref.replace("/", os.sep), "SKILL.md")
    with open(skill_path, "r", encoding="utf-8") as fh:
        text = fh.read()
    fm, body = frontmatter.parse(text)
    shape = observe_spec_shape(root, leaf_ref, fm, body)
    contract, boundary, telemetry = run_contract_tests(
        root, leaf_ref, shape["test_modules"], runner=runner
    )
    observations = {
        "spec-shape": shape,
        "desc-lint": observe_description(fm),
        "contract-test": contract,
        "near-boundary": boundary,
        "import-surface": observe_imports(root, leaf_ref),
        "marker-scan": observe_markers(root, leaf_ref),
    }
    return observations, {"contract_test_runs": telemetry}
