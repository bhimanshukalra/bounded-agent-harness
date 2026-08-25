import pytest

from bounded_agent.config import Settings
from bounded_agent.state import (
    SUPPORTED_FAILURE_TYPES,
    connect_database,
    consume_injected_failure,
    insert_injected_failure,
    list_injected_failures,
    next_matching_failure,
    reset_scenario_environment,
)


def reset_connection(tmp_path, scenario_id: str):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    result = reset_scenario_environment(scenario_id, f"{scenario_id}_run", settings)
    return connect_database(result.db_path)


def test_supported_failure_types_cover_phase_three_requirements():
    assert SUPPORTED_FAILURE_TYPES == {
        "timeout",
        "transient_error",
        "transient_error_after_side_effect",
        "not_found",
        "permission_denied",
        "conflict",
    }


def test_list_injected_failures_returns_scenario_failures(tmp_path):
    connection = reset_connection(tmp_path, "support_006")

    failures = list_injected_failures(connection, scenario_id="support_006")

    assert failures == [
        {
            "failure_id": "support_006:failure:1",
            "scenario_id": "support_006",
            "tool_name": "fetch_order",
            "failure_type": "timeout",
            "remaining_count": 1,
            "target": {},
            "payload": {},
        }
    ]


def test_consume_injected_failure_decrements_once_then_exhausts(tmp_path):
    connection = reset_connection(tmp_path, "support_006")

    first = consume_injected_failure(
        connection,
        scenario_id="support_006",
        tool_name="fetch_order",
    )
    second = consume_injected_failure(
        connection,
        scenario_id="support_006",
        tool_name="fetch_order",
    )
    stored = list_injected_failures(connection, scenario_id="support_006")

    assert first["failure_type"] == "timeout"
    assert first["remaining_count"] == 0
    assert second is None
    assert stored[0]["remaining_count"] == 0


def test_support_009_consumes_transient_error_after_side_effect(tmp_path):
    connection = reset_connection(tmp_path, "support_009")

    failure = consume_injected_failure(
        connection,
        scenario_id="support_009",
        tool_name="apply_refund",
    )

    assert failure["failure_type"] == "transient_error_after_side_effect"
    assert failure["remaining_count"] == 0


def test_insert_injected_failure_supports_target_matching(tmp_path):
    connection = reset_connection(tmp_path, "support_001")
    insert_injected_failure(
        connection,
        failure_id="support_001:failure:targeted",
        scenario_id="support_001",
        tool_name="fetch_order",
        failure_type="not_found",
        target={"order_id": "o_001"},
        payload={"message": "forced miss"},
    )

    mismatch = next_matching_failure(
        connection,
        scenario_id="support_001",
        tool_name="fetch_order",
        target={"order_id": "o_002"},
    )
    match = consume_injected_failure(
        connection,
        scenario_id="support_001",
        tool_name="fetch_order",
        target={"order_id": "o_001"},
    )

    assert mismatch is None
    assert match["failure_type"] == "not_found"
    assert match["payload"] == {"message": "forced miss"}


def test_insert_injected_failure_rejects_unsupported_type(tmp_path):
    connection = reset_connection(tmp_path, "support_001")

    with pytest.raises(ValueError, match="unsupported injected failure type"):
        insert_injected_failure(
            connection,
            failure_id="support_001:failure:bad",
            scenario_id="support_001",
            tool_name="fetch_order",
            failure_type="unknown_failure",
        )


def test_list_injected_failures_can_filter_by_tool_name(tmp_path):
    connection = reset_connection(tmp_path, "support_001")
    insert_injected_failure(
        connection,
        failure_id="support_001:failure:order",
        scenario_id="support_001",
        tool_name="fetch_order",
        failure_type="timeout",
    )
    insert_injected_failure(
        connection,
        failure_id="support_001:failure:refund",
        scenario_id="support_001",
        tool_name="apply_refund",
        failure_type="conflict",
    )

    failures = list_injected_failures(
        connection,
        scenario_id="support_001",
        tool_name="apply_refund",
    )

    assert [failure["failure_id"] for failure in failures] == ["support_001:failure:refund"]
