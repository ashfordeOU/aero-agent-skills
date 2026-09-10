"""Deterministic logic for ECSS-E-ST-10-02C 5.2.4.3 acceptance stage.

Offline, stdlib-only module backing the e1002-acceptance skill leaf:
gating an acceptance article on flight-standard eligibility, guarding
against acceptance-test overtest of a prototype-philosophy flight
model, dispositioning the workmanship/performance test outcome, and
closing out the acceptance stage across a set of articles. Uses the
same model-philosophy vocabulary as the sibling e1002-models leaf
(prototype vs protoflight).
"""

MODEL_PHILOSOPHIES = frozenset({"prototype", "protoflight"})

STATUSES = frozenset(
    {
        "accepted",
        "blocked_not_flight_standard",
        "blocked_overtest",
        "failed_workmanship_or_performance",
    }
)


def required_test_role(philosophy: str) -> str:
    """Acceptance role implied by the project's model philosophy.

    A prototype-philosophy flight model (FM) was never itself stressed
    to qualification levels, so it still needs a dedicated acceptance
    test. A protoflight-philosophy article (PFM) already absorbed the
    qualification-amplitude campaign directly, so its acceptance
    disposition is credited from that protoflight campaign rather than
    a second, separate acceptance test.
    """
    if philosophy not in MODEL_PHILOSOPHIES:
        raise ValueError(f"unknown model philosophy: {philosophy!r}")
    if philosophy == "prototype":
        return "acceptance_test"
    return "protoflight_credit"


def check_flight_standard(article_baseline: str, qualified_baseline: str) -> bool:
    """Eligibility gate: only a flight-standard article may be accepted.

    An acceptance article must be built (parts, materials, processes,
    configuration) to the same baseline that was qualified; a
    workmanship/performance test cannot substitute for a baseline
    mismatch, which must be dispositioned as a nonconformance or
    rebuilt before acceptance can proceed.
    """
    return article_baseline == qualified_baseline


def check_acceptance_overtest(
    philosophy: str,
    applied_amplitude: float,
    qualification_amplitude: float,
) -> bool:
    """Flag an acceptance test that oversteps its qualified margin.

    A prototype-philosophy acceptance test only needs to precipitate
    workmanship defects and confirm performance; qualification margin
    on that unit was already demonstrated on the separate qualification
    model, so driving the flight article's acceptance test above the
    qualification amplitude buys nothing and risks consuming life or
    damaging the article. Protoflight is exempt: its full-amplitude
    test is not an add-on overtest, it is the qualification campaign
    performed on the article by design (see e1002-models).
    """
    if philosophy not in MODEL_PHILOSOPHIES:
        raise ValueError(f"unknown model philosophy: {philosophy!r}")
    if philosophy == "protoflight":
        return False
    return applied_amplitude > qualification_amplitude


def evaluate_test_outcome(anomaly_detected: bool, performance_within_spec: bool) -> str:
    """Workmanship/performance verdict for one acceptance test run.

    Passing requires both no workmanship anomaly and performance
    within the specified acceptance criteria; either failure routes
    the article to nonconformance handling instead of acceptance.
    """
    if anomaly_detected or not performance_within_spec:
        return "failed"
    return "passed"


def disposition_article(article: dict) -> dict:
    """Acceptance disposition for one article dict.

    Required keys: id, philosophy, article_baseline, qualified_baseline,
    applied_amplitude, qualification_amplitude, anomaly_detected,
    performance_within_spec. Checks run in gating order: flight-standard
    eligibility first (a non-flight-standard article is blocked before
    its test result is even considered), then the overtest guard, then
    the workmanship/performance outcome. Returns a new dict; does not
    mutate the input. Raises ValueError if 'id' is missing.
    """
    if "id" not in article:
        raise ValueError("article is missing an id")

    role = required_test_role(article["philosophy"])

    if not check_flight_standard(article["article_baseline"], article["qualified_baseline"]):
        return {"id": article["id"], "role": role, "status": "blocked_not_flight_standard"}

    if check_acceptance_overtest(
        article["philosophy"],
        article["applied_amplitude"],
        article["qualification_amplitude"],
    ):
        return {"id": article["id"], "role": role, "status": "blocked_overtest"}

    outcome = evaluate_test_outcome(
        article["anomaly_detected"], article["performance_within_spec"]
    )
    if outcome == "failed":
        return {
            "id": article["id"],
            "role": role,
            "status": "failed_workmanship_or_performance",
        }

    return {"id": article["id"], "role": role, "status": "accepted"}


def build_acceptance_disposition(articles: list) -> list:
    """Disposition for every article, in input order.

    Raises ValueError on a duplicate article id.
    """
    dispositions = []
    seen_ids = set()
    for article in articles:
        result = disposition_article(article)
        if result["id"] in seen_ids:
            raise ValueError(f"duplicate article id: {result['id']!r}")
        seen_ids.add(result["id"])
        dispositions.append(result)
    return dispositions


def missing_dispositions(all_article_ids: list, dispositions: list) -> list:
    """Article ids expected in the acceptance set but absent from
    dispositions, in all_article_ids order -- an acceptance stage
    closure cannot claim completeness while an intended flight article
    was never dispositioned.
    """
    dispositioned_ids = {entry["id"] for entry in dispositions}
    return [aid for aid in all_article_ids if aid not in dispositioned_ids]


def close_out_acceptance_stage(dispositions: list) -> tuple:
    """Acceptance-stage closure verdict across a set of dispositions.

    Returns (all_accepted, open_items): all_accepted is True only when
    every disposition has status 'accepted'; open_items lists the
    id/status pairs still blocking closure, in input order.
    """
    open_items = [
        {"id": entry["id"], "status": entry["status"]}
        for entry in dispositions
        if entry["status"] != "accepted"
    ]
    return (len(open_items) == 0, open_items)
