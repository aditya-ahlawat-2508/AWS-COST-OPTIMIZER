from services.copilot.agent import check_grounding


def test_grounded_dollar_figure_passes():
    tool_results = [{"total_cost": 212.0, "breakdown": [{"key": "AmazonEC2", "cost": 212.0}]}]
    warnings = check_grounding("Stopping this instance saves $212.00/month.", tool_results)
    assert warnings == []


def test_fabricated_dollar_figure_is_flagged():
    tool_results = [{"total_cost": 212.0}]
    warnings = check_grounding("This will save you roughly $500/month.", tool_results)
    assert any("$500" in w for w in warnings)


def test_grounded_resource_id_passes():
    tool_results = [{"resource_id": "i-0123456789abcdef0"}]
    warnings = check_grounding("Instance i-0123456789abcdef0 is idle.", tool_results)
    assert warnings == []


def test_fabricated_resource_id_is_flagged():
    tool_results = [{"resource_id": "i-0123456789abcdef0"}]
    warnings = check_grounding("Instance i-deadbeefdeadbeef0 is idle.", tool_results)
    assert any("i-deadbeefdeadbeef0" in w for w in warnings)


def test_rounding_slack_within_a_cent():
    tool_results = [{"cost": 99.995}]
    warnings = check_grounding("That's about $100.00 total.", tool_results)
    # 99.995 rounds to 100.0 for display purposes; within the tolerance.
    assert warnings == []


def test_nested_tool_results_are_walked():
    tool_results = [{"breakdown": [{"nested": {"cost": 42.5}}]}]
    warnings = check_grounding("That service costs $42.50.", tool_results)
    assert warnings == []


def test_no_dollar_or_resource_mentions_has_no_warnings():
    warnings = check_grounding("I don't have enough data to answer that yet.", [{"total_cost": 10.0}])
    assert warnings == []
