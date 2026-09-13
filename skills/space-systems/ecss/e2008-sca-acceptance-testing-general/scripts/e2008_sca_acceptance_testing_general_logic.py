#!/usr/bin/env python3
"""General provisions for solar cell assembly acceptance testing.

Anchor: ECSS-E-ST-20-08C clause 6.3.1. Acceptance tests are applied to the
cell assemblies being delivered AND to the cell assemblies used for
qualification. The procedure below is a paraphrase into implementable steps;
no standard text is reproduced.

Why the second population is the whole point
--------------------------------------------
A qualification article is easy to read as exempt: it is not being shipped,
so acceptance -- the demonstration that a delivered item is sound -- looks
like somebody else's obligation. It is the opposite. A qualification result
only means something if the article it was produced on was itself an
acceptable assembly; an unaccepted coupon that fails a thermal cycle has not
told anybody whether the process or the coupon was at fault. So the
acceptance activity set is expanded over BOTH populations, and a population
with no acceptance record at all is reported as an exemption rather than as
a run of empty articles.

    per article     which of the owed acceptance activities have a record,
                    and whether the record says the article passed, failed
                    or was never run
    per population  how much of the owed acceptance work the population
                    actually carries, and whether the population was
                    exempted wholesale
    per lot         both populations present, both covered, no article left
                    with a failed or unrun acceptance activity

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "REQUIRED_SCA_ACCEPTANCE_TESTS",
    "ARTICLE_POPULATIONS",
    "TEST_RESULTS",
    "DEFAULT_ACCEPTANCE_POLICY",
    "COVERAGE_TOLERANCE_REL",
    "ARTICLE_ACCEPTED",
    "ARTICLE_TESTS_MISSING",
    "ARTICLE_TEST_NOT_RUN",
    "ARTICLE_TEST_FAILED",
    "LOT_ACCEPTED",
    "LOT_INCOMPLETE",
    "validate_identifier",
    "validate_test_record",
    "assess_article",
    "population_summary",
    "exempted_populations",
    "assess_lot_acceptance",
]

# The acceptance activity set every solar cell assembly owes, whichever
# population it belongs to.
REQUIRED_SCA_ACCEPTANCE_TESTS = (
    "sca-visual-inspection",
    "sca-electrical-performance-measurement",
    "sca-dimensional-measurement",
    "sca-interconnector-adherence-verification",
)

# The two populations the clause reaches: the assemblies that ship, and the
# assemblies consumed by the qualification campaign.
ARTICLE_POPULATIONS = ("delivery", "qualification-allocated")

TEST_RESULTS = ("pass", "fail", "not-run")

# Per-article outcomes, ranked worst first by _ARTICLE_RANK below.
ARTICLE_ACCEPTED = "article-accepted"
ARTICLE_TESTS_MISSING = "article-acceptance-tests-missing"
ARTICLE_TEST_NOT_RUN = "article-acceptance-test-not-run"
ARTICLE_TEST_FAILED = "article-acceptance-test-failed"

LOT_ACCEPTED = "sca-lot-acceptance-complete"
LOT_INCOMPLETE = "sca-lot-acceptance-incomplete"

# An activity with no record at all is worse than one recorded as not yet run,
# and both are worse than a recorded failure: the failure is known and can be
# dispositioned, the absence cannot.
_ARTICLE_RANK = {
    ARTICLE_TESTS_MISSING: 0,
    ARTICLE_TEST_NOT_RUN: 1,
    ARTICLE_TEST_FAILED: 2,
    ARTICLE_ACCEPTED: 3,
}

DEFAULT_ACCEPTANCE_POLICY = {
    # Both populations have to appear in the lot record.
    "required_populations": ARTICLE_POPULATIONS,
    # Share of the owed acceptance activities each population has to carry.
    "min_population_coverage": 1.0,
    # A failed article keeps the lot open until it is dispositioned.
    "allow_failed_article": False,
}

# Coverage shares are ratios of counts compared against round fractions, so a
# population meant to sit exactly on its minimum can land a few units in the
# last place below it. The comparison absorbs that instead of moving the
# minimum.
COVERAGE_TOLERANCE_REL = 1e-9


def validate_identifier(value, label):
    """Return value as a trimmed, non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty identifier string" % label)
    return value.strip()


def validate_test_record(record, index=0, article_id="?"):
    """Return one validated acceptance test record of an article."""
    if not isinstance(record, dict):
        raise ValueError(
            "test record %d of article %r must be a mapping" % (index, article_id)
        )
    name = validate_identifier(
        record.get("test"), "test name of record %d on article %r" % (index, article_id)
    )
    if name not in REQUIRED_SCA_ACCEPTANCE_TESTS:
        raise ValueError(
            "article %r records %r, which is not an acceptance activity of this "
            "clause" % (article_id, name)
        )
    result = record.get("result")
    if result not in TEST_RESULTS:
        raise ValueError(
            "result of %r on article %r must be one of %r, got %r"
            % (name, article_id, TEST_RESULTS, result)
        )
    return {"test": name, "result": result}


def _policy(policy):
    """Return the effective policy, defaults filled in and validated."""
    settings = dict(DEFAULT_ACCEPTANCE_POLICY)
    if policy is None:
        return settings
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    for key, value in policy.items():
        if key not in DEFAULT_ACCEPTANCE_POLICY:
            raise ValueError("policy carries unknown key '%s'" % key)
        settings[key] = value

    populations = settings["required_populations"]
    if not isinstance(populations, (list, tuple)) or not populations:
        raise ValueError("required_populations must be a non-empty sequence")
    for population in populations:
        if population not in ARTICLE_POPULATIONS:
            raise ValueError("unknown population '%s'" % population)
    settings["required_populations"] = tuple(populations)

    coverage = settings["min_population_coverage"]
    if not isinstance(coverage, (int, float)) or isinstance(coverage, bool):
        raise ValueError("min_population_coverage must be a real number")
    coverage = float(coverage)
    if not math.isfinite(coverage) or coverage < 0.0 or coverage > 1.0:
        raise ValueError("min_population_coverage must lie in [0, 1], got %r" % coverage)
    settings["min_population_coverage"] = coverage

    if not isinstance(settings["allow_failed_article"], bool):
        raise ValueError("allow_failed_article must be a boolean")
    return settings


def assess_article(article, policy=None):
    """Grade one solar cell assembly against the acceptance activity set."""
    settings = _policy(policy)
    if not isinstance(article, dict):
        raise ValueError("article must be a mapping")
    article_id = validate_identifier(article.get("article_id"), "article_id")
    population = article.get("population")
    if population not in ARTICLE_POPULATIONS:
        raise ValueError(
            "article %r must belong to one of %r, got %r"
            % (article_id, ARTICLE_POPULATIONS, population)
        )

    raw = article.get("test_records", [])
    if not isinstance(raw, (list, tuple)):
        raise ValueError("test_records of article %r must be a sequence" % article_id)
    records = [validate_test_record(r, i, article_id) for i, r in enumerate(raw)]
    names = [r["test"] for r in records]
    if len(set(names)) != len(names):
        raise ValueError(
            "article %r records the same acceptance activity twice" % article_id
        )

    by_test = {r["test"]: r["result"] for r in records}
    missing = [t for t in REQUIRED_SCA_ACCEPTANCE_TESTS if t not in by_test]
    not_run = [t for t in REQUIRED_SCA_ACCEPTANCE_TESTS if by_test.get(t) == "not-run"]
    failed = [t for t in REQUIRED_SCA_ACCEPTANCE_TESTS if by_test.get(t) == "fail"]
    passed = [t for t in REQUIRED_SCA_ACCEPTANCE_TESTS if by_test.get(t) == "pass"]

    if missing:
        verdict = ARTICLE_TESTS_MISSING
    elif not_run:
        verdict = ARTICLE_TEST_NOT_RUN
    elif failed:
        verdict = ARTICLE_TEST_FAILED
    else:
        verdict = ARTICLE_ACCEPTED

    return {
        "article_id": article_id,
        "population": population,
        "missing_tests": missing,
        "not_run_tests": not_run,
        "failed_tests": failed,
        "passed_tests": passed,
        "activity_coverage": len(passed + failed) / len(REQUIRED_SCA_ACCEPTANCE_TESTS),
        "verdict": verdict,
        "rank": _ARTICLE_RANK[verdict],
        "acceptable": verdict == ARTICLE_ACCEPTED
        or (verdict == ARTICLE_TEST_FAILED and settings["allow_failed_article"]),
    }


def population_summary(graded, population):
    """Summarise the graded articles belonging to one population."""
    if population not in ARTICLE_POPULATIONS:
        raise ValueError("unknown population '%s'" % population)
    if not isinstance(graded, (list, tuple)):
        raise ValueError("graded must be a sequence of graded articles")
    members = [a for a in graded if a["population"] == population]
    if not members:
        return {
            "population": population,
            "article_count": 0,
            "accepted_count": 0,
            "coverage_share": 0.0,
            "activity_share": 0.0,
            "present": False,
        }
    accepted = [a for a in members if a["verdict"] == ARTICLE_ACCEPTED]
    return {
        "population": population,
        "article_count": len(members),
        "accepted_count": len(accepted),
        "coverage_share": len(accepted) / len(members),
        "activity_share": math.fsum(a["activity_coverage"] for a in members)
        / len(members),
        "present": True,
    }


def exempted_populations(graded):
    """Return the populations present in the lot with no acceptance work at all."""
    if not isinstance(graded, (list, tuple)):
        raise ValueError("graded must be a sequence of graded articles")
    exempted = []
    for population in ARTICLE_POPULATIONS:
        members = [a for a in graded if a["population"] == population]
        if not members:
            continue
        run = math.fsum(a["activity_coverage"] for a in members)
        if math.isclose(run, 0.0, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE_REL):
            exempted.append(population)
    return exempted


def assess_lot_acceptance(spec):
    """Run the full clause 6.3.1 acceptance assessment over a lot.

    spec keys: lot_id, articles, and an optional policy mapping.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("lot_id", "articles"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    lot_id = validate_identifier(spec["lot_id"], "lot_id")
    settings = _policy(spec.get("policy"))

    raw = spec["articles"]
    if not isinstance(raw, (list, tuple)) or not raw:
        raise ValueError("articles must be a non-empty sequence")
    graded = [assess_article(a, settings) for a in raw]
    ids = [a["article_id"] for a in graded]
    if len(set(ids)) != len(ids):
        raise ValueError("article identifiers must be unique, got %r" % (ids,))

    summaries = {p: population_summary(graded, p) for p in ARTICLE_POPULATIONS}
    exempted = exempted_populations(graded)
    minimum = settings["min_population_coverage"]

    findings = []
    for population in settings["required_populations"]:
        summary = summaries[population]
        if not summary["present"]:
            findings.append(
                "lot %s carries no %s assembly, so the acceptance obligation of "
                "that population is untested" % (lot_id, population)
            )
            continue
        if population in exempted:
            findings.append(
                "every %s assembly in lot %s was exempted from acceptance testing"
                % (population, lot_id)
            )
            continue
        share = summary["coverage_share"]
        if share < minimum and not math.isclose(
            share, minimum, rel_tol=COVERAGE_TOLERANCE_REL, abs_tol=0.0
        ):
            findings.append(
                "%s acceptance coverage %.3f is below the required share %.3f"
                % (population, share, minimum)
            )

    for article in sorted(graded, key=lambda a: (a["rank"], a["article_id"])):
        if article["verdict"] == ARTICLE_TESTS_MISSING:
            findings.append(
                "article %s has no record for: %s"
                % (article["article_id"], ", ".join(article["missing_tests"]))
            )
        elif article["verdict"] == ARTICLE_TEST_NOT_RUN:
            findings.append(
                "article %s still has unrun acceptance activity: %s"
                % (article["article_id"], ", ".join(article["not_run_tests"]))
            )
        elif article["verdict"] == ARTICLE_TEST_FAILED and not article["acceptable"]:
            findings.append(
                "article %s failed acceptance activity: %s"
                % (article["article_id"], ", ".join(article["failed_tests"]))
            )

    grouped = {}
    for article in graded:
        grouped.setdefault(article["verdict"], []).append(article["article_id"])
    for key in grouped:
        grouped[key].sort()

    return {
        "lot_id": lot_id,
        "articles": graded,
        "articles_by_verdict": grouped,
        "populations": summaries,
        "exempted_populations": exempted,
        "lot_coverage_share": len([a for a in graded if a["acceptable"]]) / len(graded),
        "findings": findings,
        "verdict": LOT_ACCEPTED if not findings else LOT_INCOMPLETE,
    }
