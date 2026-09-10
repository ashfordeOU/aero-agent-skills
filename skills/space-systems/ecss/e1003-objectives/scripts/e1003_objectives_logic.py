#!/usr/bin/env python3
"""ECSS-E-ST-10-03C clause 4.5 test objectives logic (paraphrase, not
copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
clause 4.5 sets the objective of each test campaign type. Qualification
testing demonstrates, on a qualification or protoflight article, that
the design meets its requirements with margin beyond the levels and
duration expected in the mission environment, uncovering marginal
design weaknesses. Acceptance testing demonstrates the absence of
workmanship and manufacturing defects in the deliverable/flight
article at levels representative of the expected flight environment
(no added margin), for the minimum duration needed to screen
workmanship without consuming the item's operational life. Protoflight
testing is applied to a flight article that also serves the
qualification role: it combines both objectives, so the article is
tested at qualification levels but only for the reduced,
acceptance-like duration -- demonstrating margin and screening
workmanship together without excessively consuming the flight
article's life margin. This module implements the objective set, the
required level/duration derivation, and a check of a proposed test
definition against them; it does not set the numeric levels/durations
themselves (see the sibling e1003-eq-qual / e1003-eq-acceptance /
e1003-eq-protoflight leaves) or the input tolerances applied to a test
(see e1003-input-tolerances).
"""

CAMPAIGNS = ("qualification", "acceptance", "protoflight")
OBJECTIVES = ("demonstrate_margin", "workmanship_screen")
LEVELS = ("acceptance_level", "qualification_level")
DURATIONS = ("reduced", "full")

_CAMPAIGN_OBJECTIVES = {
    "qualification": frozenset({"demonstrate_margin"}),
    "acceptance": frozenset({"workmanship_screen"}),
    "protoflight": frozenset({"demonstrate_margin", "workmanship_screen"}),
}

_CAMPAIGN_LEVEL = {
    "qualification": "qualification_level",
    "acceptance": "acceptance_level",
    "protoflight": "qualification_level",
}

_CAMPAIGN_DURATION = {
    "qualification": "full",
    "acceptance": "reduced",
    "protoflight": "reduced",
}


def _check_campaign(campaign):
    if campaign not in CAMPAIGNS:
        raise ValueError("unknown test campaign: %r" % (campaign,))


def campaign_objectives(campaign):
    """Objective set assigned to a test campaign per clause 4.5:
    qualification -> demonstrate_margin only; acceptance ->
    workmanship_screen only; protoflight -> both (it combines the
    qualification and acceptance objectives on one flight article).
    Raises ValueError for an unknown campaign."""
    _check_campaign(campaign)
    return _CAMPAIGN_OBJECTIVES[campaign]


def required_test_level(campaign):
    """Test level required to meet a campaign's objectives:
    qualification and protoflight need qualification_level (margin
    above the expected environment); acceptance needs acceptance_level
    (representative of the expected environment, no added margin).
    Raises ValueError for an unknown campaign."""
    _check_campaign(campaign)
    return _CAMPAIGN_LEVEL[campaign]


def required_test_duration(campaign):
    """Duration class required to meet a campaign's objectives:
    qualification needs full duration (fully demonstrate margin);
    acceptance and protoflight need reduced duration (workmanship
    screen only, without consuming the deliverable/flight article's
    operational life). Raises ValueError for an unknown campaign."""
    _check_campaign(campaign)
    return _CAMPAIGN_DURATION[campaign]


def flight_article_at_risk(campaign):
    """True when the campaign's test article is the deliverable/flight
    article whose remaining operational life must be protected
    (acceptance, protoflight); False for qualification, which uses a
    dedicated qualification article. Raises ValueError for an unknown
    campaign."""
    _check_campaign(campaign)
    return campaign in ("acceptance", "protoflight")


def set_test_objectives(campaign):
    """Full objective-setting record for one campaign: campaign,
    objectives (sorted tuple), required level, required duration, and
    whether the test article is flight-life-at-risk. Raises ValueError
    for an unknown campaign."""
    _check_campaign(campaign)
    return {
        "campaign": campaign,
        "objectives": tuple(sorted(campaign_objectives(campaign))),
        "level": required_test_level(campaign),
        "duration": required_test_duration(campaign),
        "flight_article_at_risk": flight_article_at_risk(campaign),
    }


def evaluate_test_definition(campaign, level, duration):
    """Evaluate a proposed (level, duration) pair against the
    objectives assigned to a campaign. Returns a new dict: campaign,
    objectives, expected (level, duration), actual (level, duration),
    valid (bool), issues (tuple of strings, empty when valid). Raises
    ValueError for an unknown campaign, level, or duration."""
    _check_campaign(campaign)
    if level not in LEVELS:
        raise ValueError("unknown test level: %r" % (level,))
    if duration not in DURATIONS:
        raise ValueError("unknown test duration: %r" % (duration,))

    expected_level = required_test_level(campaign)
    expected_duration = required_test_duration(campaign)
    issues = []

    if level != expected_level:
        if campaign == "acceptance":
            issues.append(
                "acceptance test above flight levels risks damaging the "
                "deliverable/flight article without demonstrating "
                "additional margin"
            )
        else:
            issues.append(
                "%s campaign needs %s to demonstrate margin, got %s"
                % (campaign, expected_level, level)
            )

    if duration != expected_duration:
        if flight_article_at_risk(campaign) and duration == "full":
            issues.append(
                "full-duration test on a flight-life-at-risk article "
                "(%s) risks consuming operational life margin before "
                "flight" % (campaign,)
            )
        else:
            issues.append(
                "%s campaign needs %s duration to screen workmanship, "
                "got %s" % (campaign, expected_duration, duration)
            )

    return {
        "campaign": campaign,
        "objectives": tuple(sorted(campaign_objectives(campaign))),
        "expected": {"level": expected_level, "duration": expected_duration},
        "actual": {"level": level, "duration": duration},
        "valid": len(issues) == 0,
        "issues": tuple(issues),
    }


def protoflight_combines_qualification_and_acceptance():
    """True when the protoflight objective set is exactly the union of
    the qualification and acceptance objective sets -- the invariant
    that protoflight testing combines both campaigns' objectives on one
    flight article, per clause 4.5."""
    combined = campaign_objectives("qualification") | campaign_objectives("acceptance")
    return campaign_objectives("protoflight") == combined


def build_objectives_matrix(campaigns=CAMPAIGNS):
    """Objective-setting record (set_test_objectives) for each campaign
    in campaigns, in input order. Raises ValueError on a duplicate
    campaign or an unknown campaign."""
    matrix = []
    seen = set()
    for campaign in campaigns:
        _check_campaign(campaign)
        if campaign in seen:
            raise ValueError("duplicate campaign: %r" % (campaign,))
        seen.add(campaign)
        matrix.append(set_test_objectives(campaign))
    return matrix
