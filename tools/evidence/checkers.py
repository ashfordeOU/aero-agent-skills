#!/usr/bin/env python3
"""Checking: the cheap half, a pure function of a stored observation.

A checker never touches the corpus.  It is handed one observation dictionary
and one parameter dictionary and returns a verdict.  That is the whole reason
regrade is possible: fixing a checker, tightening a threshold or retiring a
rule re-decides every issued record without re-running a single test.

Five verdicts, and the last three carry most of the honesty:

  PASS           the stored evidence satisfies the rule.
  FAIL           the stored evidence violates the rule.
  INDETERMINATE  the stored evidence cannot answer the question.  The rule
                 changed in a way that needs evidence nobody collected.  This
                 is not a pass and it is not a failure; it is a work order
                 for re-observation.
  WITHDRAWN      the rule no longer exists in the checker set being applied.
                 The historical outcome stays in the record; it just stops
                 counting toward the verdict.
  NOT_APPLICABLE the rule does not apply to this subject.

Every checker declares what it needs.  If the stored observation is a version
it does not understand, or lacks a field it reads, it returns INDETERMINATE
with the missing pieces named, rather than reading a default and quietly
deciding on evidence it does not have.
"""

from . import canonical

CHECKER_SET_SPEC = "aero-evidence-checkerset/1"

PASS = "PASS"
FAIL = "FAIL"
INDETERMINATE = "INDETERMINATE"
WITHDRAWN = "WITHDRAWN"
NOT_APPLICABLE = "NOT_APPLICABLE"

# Mirrors the import allowlist the shipped gate-3 helper enforces.  It lives
# in the parameters, not the code, so widening or narrowing it is a parameter
# change that regrade can apply to already-issued records.
STDLIB_ALLOWLIST = sorted(
    """
    abc argparse asyncio base64 bisect builtins collections concurrent
    contextlib copy csv dataclasses datetime decimal enum errno faulthandler
    functools gc glob hashlib heapq inspect io itertools json logging math
    mmap multiprocessing os pathlib pickle pprint queue random re select
    shlex shutil signal socket sqlite3 stat statistics string struct subprocess
    sys tempfile textwrap threading time timeit traceback types typing unittest
    uuid weakref xml zoneinfo
    """.split()
)

MARKER_IDS = (
    "all-rights-reserved",
    "redistribution-bar",
    "single-user-licence",
    "confidentiality-banner",
    "licence-agreement-banner",
    "rights-management-banner",
    "licensed-to-banner",
    "dated-copyright-notice",
)


def outcome(verdict, reason, findings=None, needs=None):
    result = {"verdict": verdict, "reason": reason, "findings": findings or []}
    if needs:
        result["needs"] = needs
    return result


def _version_understood(stored, required):
    """Same major, and at least the required minor.patch."""
    try:
        s = [int(part) for part in str(stored).split(".")]
        r = [int(part) for part in str(required).split(".")]
    except (TypeError, ValueError):
        return False
    return s[0] == r[0] and s >= r


def _missing(observation, fields):
    return [field for field in fields if field not in observation]


class Checker:
    def __init__(self, cid, version, title, observation, observation_version, fields, params, fn):
        self.id = cid
        self.version = version
        self.title = title
        self.observation = observation
        self.observation_version = observation_version
        self.fields = fields
        self.default_params = params
        self.fn = fn

    def decide(self, observation, params):
        if observation is None:
            return outcome(
                INDETERMINATE,
                "no stored observation '%s' in this record" % self.observation,
                needs={"observation": self.observation, "reason": "absent"},
            )
        stored_version = observation.get("version")
        if not _version_understood(stored_version, self.observation_version):
            return outcome(
                INDETERMINATE,
                "observation '%s' is version %s; this checker reads %s"
                % (self.observation, stored_version, self.observation_version),
                needs={
                    "observation": self.observation,
                    "stored_version": stored_version,
                    "required_version": self.observation_version,
                },
            )
        absent = _missing(observation, self.fields)
        if absent:
            return outcome(
                INDETERMINATE,
                "observation '%s' does not record %s" % (self.observation, ", ".join(absent)),
                needs={"observation": self.observation, "fields": absent},
            )
        return self.fn(observation, params)


# --------------------------------------------------------------------------
# the checkers
# --------------------------------------------------------------------------


def _spec_shape(obs, params):
    findings = []
    for key in params["required_frontmatter_keys"]:
        if key not in obs["keys_present"]:
            findings.append({"code": "missing-key", "detail": key})
    if params["require_name_matches_directory"] and not obs["name_matches_directory"]:
        findings.append(
            {
                "code": "name-directory-mismatch",
                "detail": "%s vs %s" % (obs["name"], obs["directory_name"]),
            }
        )
    if obs["body_lines"] > params["max_body_lines"]:
        findings.append({"code": "body-too-long", "detail": str(obs["body_lines"])})
    if obs["description_chars"] > params["max_description_chars"]:
        findings.append(
            {"code": "description-too-long", "detail": str(obs["description_chars"])}
        )
    if params["allowed_licenses"] and obs["license"] not in params["allowed_licenses"]:
        findings.append({"code": "license-not-allowed", "detail": str(obs["license"])})
    if params["allowed_compliance"] and obs["compliance"] not in params["allowed_compliance"]:
        findings.append({"code": "compliance-not-allowed", "detail": str(obs["compliance"])})
    if params["require_test_module"] and not obs["test_modules"]:
        findings.append({"code": "no-contract-test-module", "detail": ""})
    if params["require_logic_module"] and not obs["logic_modules"]:
        findings.append({"code": "no-logic-module", "detail": ""})
    if obs["absolute_link_count"] > params["max_absolute_links"]:
        findings.append(
            {"code": "absolute-links", "detail": str(obs["absolute_link_count"])}
        )
    if findings:
        return outcome(FAIL, "%d shape violation(s)" % len(findings), findings)
    return outcome(PASS, "front matter and layout conform")


def _desc_lint(obs, params):
    wanted = params["action_verb_vocabulary_version"]
    if obs["action_verb_vocabulary_version"] != wanted:
        return outcome(
            INDETERMINATE,
            "description was measured against action-verb vocabulary %s; this "
            "rule needs %s, which requires re-observation"
            % (obs["action_verb_vocabulary_version"], wanted),
            needs={
                "observation": "desc-lint",
                "vocabulary_stored": obs["action_verb_vocabulary_version"],
                "vocabulary_required": wanted,
            },
        )
    findings = []
    if not obs["present"]:
        findings.append({"code": "no-description", "detail": ""})
    words = obs["word_count"]
    if words < params["min_words"] or words > params["max_words"]:
        findings.append(
            {
                "code": "word-count-out-of-range",
                "detail": "%d words, allowed %d-%d"
                % (words, params["min_words"], params["max_words"]),
            }
        )
    if params["require_action_verb"] and not obs["action_verbs_found"]:
        findings.append({"code": "no-action-verb", "detail": ""})
    if params["require_use_when"] and not obs["has_use_when_clause"]:
        findings.append({"code": "no-use-when-clause", "detail": ""})
    if params["require_trigger_label"] and not obs["has_trigger_label"]:
        findings.append({"code": "no-trigger-label", "detail": ""})
    if obs["trigger_keyword_count"] < params["min_trigger_keywords"]:
        findings.append(
            {
                "code": "too-few-trigger-keywords",
                "detail": "%d, need %d"
                % (obs["trigger_keyword_count"], params["min_trigger_keywords"]),
            }
        )
    if findings:
        return outcome(FAIL, "%d description violation(s)" % len(findings), findings)
    return outcome(PASS, "%d words, action verb, use-when and triggers present" % words)


def _contract_test(obs, params):
    totals = obs["totals"]
    findings = []
    for module in obs["modules"]:
        if module.get("load_error"):
            findings.append(
                {"code": "load-error", "detail": "%s: %s" % (module["module"], module["load_error"])}
            )
        if params["require_instrumented"] and not module.get("instrumented"):
            findings.append({"code": "not-instrumented", "detail": module["module"]})
    if totals["tests_run"] < params["min_tests"]:
        findings.append(
            {
                "code": "too-few-tests",
                "detail": "%d run, need %d" % (totals["tests_run"], params["min_tests"]),
            }
        )
    if totals["failures"] > params["max_failures"]:
        findings.append({"code": "failures", "detail": str(totals["failures"])})
    if totals["errors"] > params["max_errors"]:
        findings.append({"code": "errors", "detail": str(totals["errors"])})
    if not params["allow_skips"] and totals["skipped"]:
        findings.append({"code": "skipped-tests", "detail": str(totals["skipped"])})
    if totals["unexpected_successes"]:
        findings.append(
            {"code": "unexpected-successes", "detail": str(totals["unexpected_successes"])}
        )
    if findings:
        return outcome(FAIL, "%d contract violation(s)" % len(findings), findings)
    return outcome(
        PASS,
        "%d test(s) across %d module(s), no failure or error"
        % (totals["tests_run"], totals["modules"]),
    )


def _portability(obs, params):
    tolerance = canonical.parse_num(params["relative_tolerance"])
    floor = obs.get("gap_floor")
    if not obs["all_recorded"] and floor is not None:
        if tolerance > canonical.parse_num(floor):
            return outcome(
                INDETERMINATE,
                "tolerance %s is above the recorded gap floor %s: the record "
                "holds only the %d tightest of %d comparisons, so the number "
                "of violations at this tolerance is not knowable from it"
                % (
                    params["relative_tolerance"],
                    floor,
                    obs["recorded_cap"],
                    obs["comparisons_total"],
                ),
                needs={
                    "observation": "near-boundary",
                    "gap_floor": floor,
                    "tolerance": params["relative_tolerance"],
                },
            )
    hits = [
        entry
        for entry in obs["tightest"]
        if canonical.parse_num(entry["relative_gap"]) <= tolerance
    ]
    if hits:
        return outcome(
            FAIL,
            "%d strict comparison(s) within %s relative of the bound"
            % (len(hits), params["relative_tolerance"]),
            [
                {
                    "code": "near-boundary-comparison",
                    "detail": "%s %s gap %s"
                    % (entry["test"], entry["assertion"], entry["relative_gap"]),
                }
                for entry in hits
            ],
        )
    return outcome(
        PASS,
        "no comparison within %s relative of its bound across %d comparison(s)"
        % (params["relative_tolerance"], obs["comparisons_total"]),
    )


def _stdlib_only(obs, params):
    allowed = set(params["allowlist"])
    findings = []
    for module in obs["modules"]:
        if module.get("parse_error"):
            # An empty import list from a module that would not parse is not
            # evidence of a clean import surface.
            findings.append(
                {
                    "code": "unparsable-module",
                    "detail": "%s: %s" % (module["module"], module["parse_error"]),
                }
            )
            continue
        siblings = set(module["sibling_resolved"])
        for name in module["imports"]:
            if name in allowed or name in siblings:
                continue
            findings.append(
                {"code": "non-stdlib-import", "detail": "%s imports %s" % (module["module"], name)}
            )
    if findings:
        return outcome(FAIL, "%d non-stdlib import(s)" % len(findings), findings)
    return outcome(PASS, "%d module(s) import stdlib and siblings only" % len(obs["modules"]))


def _no_verbatim(obs, params):
    enforced = list(params["markers_enforced"])
    unknown = [m for m in enforced if m not in obs["marker_ids"]]
    if unknown:
        return outcome(
            INDETERMINATE,
            "marker(s) %s were added after this record was observed; the "
            "record holds no count for them" % ", ".join(sorted(unknown)),
            needs={"observation": "marker-scan", "markers": sorted(unknown)},
        )
    findings = []
    for marker in enforced:
        count = obs["marker_counts"].get(marker, 0)
        if count > params["max_hits_per_marker"]:
            findings.append({"code": "marker-hit", "detail": "%s x%d" % (marker, count)})
    if obs["longest_quoted_span_chars"] > params["max_quoted_span_chars"]:
        findings.append(
            {
                "code": "quoted-span-too-long",
                "detail": "%d chars" % obs["longest_quoted_span_chars"],
            }
        )
    if findings:
        return outcome(FAIL, "%d paraphrase-policy violation(s)" % len(findings), findings)
    return outcome(
        PASS,
        "%d marker(s) enforced, none present across %d scanned file(s)"
        % (len(enforced), len(obs["files_scanned"])),
    )


def _references_present(obs, params):
    # Reads a field the 1.0.0 shape observation does not record.  Kept in the
    # registry, disabled by default: it is the worked example of a rule added
    # after records were issued, and the Checker preflight returns
    # INDETERMINATE for it rather than letting it decide on absent evidence.
    if obs.get("has_references_dir"):
        return outcome(PASS, "references directory present")
    return outcome(FAIL, "no references directory")


REGISTRY = {}


def _register(checker):
    REGISTRY[checker.id] = checker
    return checker


_register(
    Checker(
        "spec-shape",
        "1.0.0",
        "front matter and leaf layout conform to the skill specification",
        "spec-shape",
        "1.0.0",
        [
            "keys_present",
            "name_matches_directory",
            "body_lines",
            "description_chars",
            "license",
            "compliance",
            "test_modules",
            "logic_modules",
            "absolute_link_count",
        ],
        {
            "required_frontmatter_keys": [
                "name",
                "description",
                "license",
                "compliance",
                "standards",
                "gated",
                "domain",
                "pack",
                "metadata",
            ],
            "require_name_matches_directory": True,
            "max_body_lines": 500,
            "max_description_chars": 1024,
            "allowed_licenses": ["Apache-2.0"],
            "allowed_compliance": ["none", "ITAR-GATED", "EAR-GATED", "STANDARDS-REF"],
            "require_test_module": True,
            "require_logic_module": True,
            "max_absolute_links": 0,
        },
        _spec_shape,
    )
)

_register(
    Checker(
        "desc-lint",
        "1.0.0",
        "the description carries what, when and trigger keywords",
        "desc-lint",
        "1.0.0",
        [
            "word_count",
            "present",
            "action_verbs_found",
            "action_verb_vocabulary_version",
            "has_use_when_clause",
            "has_trigger_label",
            "trigger_keyword_count",
        ],
        {
            "min_words": 50,
            "max_words": 150,
            "min_trigger_keywords": 2,
            "require_action_verb": True,
            "require_use_when": True,
            "require_trigger_label": True,
            "action_verb_vocabulary_version": "1.0.0",
        },
        _desc_lint,
    )
)

_register(
    Checker(
        "contract-test",
        "1.0.0",
        "the leaf's behaviour contract test passes",
        "contract-test",
        "1.0.0",
        ["totals", "modules"],
        {
            "min_tests": 1,
            "max_failures": 0,
            "max_errors": 0,
            "allow_skips": False,
            "require_instrumented": True,
        },
        _contract_test,
    )
)

_register(
    Checker(
        "portability",
        "1.0.0",
        "no strict float comparison sits on its bound",
        "near-boundary",
        "1.0.0",
        ["comparisons_total", "all_recorded", "tightest", "recorded_cap"],
        {"relative_tolerance": "1e-12"},
        _portability,
    )
)

_register(
    Checker(
        "stdlib-only",
        "1.0.0",
        "shipped modules import the standard library and their siblings only",
        "import-surface",
        "1.0.0",
        ["modules"],
        {"allowlist": STDLIB_ALLOWLIST},
        _stdlib_only,
    )
)

_register(
    Checker(
        "no-verbatim",
        "1.0.0",
        "no copyright boilerplate and no long quoted span",
        "marker-scan",
        "1.0.0",
        ["marker_ids", "marker_counts", "files_scanned", "longest_quoted_span_chars"],
        {
            "markers_enforced": list(MARKER_IDS),
            "max_hits_per_marker": 0,
            "max_quoted_span_chars": 400,
        },
        _no_verbatim,
    )
)

_register(
    Checker(
        "references-present",
        "1.0.0",
        "the leaf ships a references directory",
        "spec-shape",
        "1.0.0",
        ["has_references_dir"],
        {},
        _references_present,
    )
)

DEFAULT_ENABLED = (
    "spec-shape",
    "desc-lint",
    "contract-test",
    "portability",
    "stdlib-only",
    "no-verbatim",
)


def build_set(label="default", overrides=None):
    """Build a checker set: the ordered list of checkers and their parameters.

    overrides is the parsed contents of a checker-set file:
        {"label": "...", "checkers": {"<id>": {"enabled": bool, "params": {...}}}}
    Parameters merge key by key over the registry defaults, so a file that
    changes one threshold does not have to restate the rest.
    """
    overrides = overrides or {}
    label = overrides.get("label", label)
    requested = overrides.get("checkers", {})
    unknown = sorted(set(requested) - set(REGISTRY))
    if unknown:
        raise KeyError("unknown checker id(s): %s" % ", ".join(unknown))
    entries = []
    for cid in sorted(REGISTRY):
        checker = REGISTRY[cid]
        override = requested.get(cid, {})
        enabled = override.get("enabled", cid in DEFAULT_ENABLED)
        if not enabled:
            continue
        params = dict(checker.default_params)
        params.update(override.get("params", {}))
        entries.append(
            {
                "id": cid,
                "version": checker.version,
                "title": checker.title,
                "observation": checker.observation,
                "observation_version": checker.observation_version,
                "params": params,
                "params_digest": canonical.digest(params),
            }
        )
    return {
        "spec": CHECKER_SET_SPEC,
        "label": label,
        "checkers": entries,
        "digest": canonical.digest(
            [{"id": e["id"], "version": e["version"], "params": e["params"]} for e in entries]
        ),
    }


def apply_set(checker_set, observations):
    """Run a checker set over a bag of observations.  Returns the gate list."""
    gates = []
    for entry in checker_set["checkers"]:
        checker = REGISTRY[entry["id"]]
        observation = observations.get(entry["observation"])
        result = checker.decide(observation, entry["params"])
        gates.append(
            {
                "gate": entry["id"],
                "checker_version": entry["version"],
                "params_digest": entry["params_digest"],
                "observation": entry["observation"],
                "observation_digest": canonical.digest(observation) if observation else None,
                "outcome": result,
            }
        )
    return gates


def roll_up(gates):
    """Overall verdict from the gate outcomes."""
    counts = {}
    for gate in gates:
        verdict = gate["outcome"]["verdict"]
        counts[verdict] = counts.get(verdict, 0) + 1
    if counts.get(FAIL):
        overall = FAIL
    elif counts.get(INDETERMINATE):
        overall = INDETERMINATE
    elif counts.get(PASS):
        overall = PASS
    else:
        overall = NOT_APPLICABLE
    return {"overall": overall, "counts": counts, "gates": len(gates)}
