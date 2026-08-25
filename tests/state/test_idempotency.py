from bounded_agent.config import Settings
from bounded_agent.state import (
    connect_database,
    get_idempotency_record,
    hash_arguments,
    record_or_replay_idempotency,
    reset_scenario_environment,
)

FIXED_TIMESTAMP = "2026-08-25T00:00:00Z"


def reset_connection(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    result = reset_scenario_environment("support_009", "support_009_run", settings)
    return connect_database(result.db_path)


def test_hash_arguments_is_deterministic_for_key_order():
    left = hash_arguments({"charge_id": "ch_009_b", "amount": 49.0})
    right = hash_arguments({"amount": 49.0, "charge_id": "ch_009_b"})

    assert left == right


def test_get_idempotency_record_returns_none_for_missing_key(tmp_path):
    connection = reset_connection(tmp_path)

    assert get_idempotency_record(connection, "missing:key") is None


def test_record_or_replay_idempotency_stores_first_result(tmp_path):
    connection = reset_connection(tmp_path)

    decision = record_or_replay_idempotency(
        connection,
        idempotency_key="refund:key:001",
        run_id="run_001",
        tool_name="apply_refund",
        target_type="charge",
        target_id="ch_009_b",
        arguments={"charge_id": "ch_009_b", "amount": 49.0},
        result={"status": "refunded", "charge_id": "ch_009_b"},
        created_at=FIXED_TIMESTAMP,
    )

    record = get_idempotency_record(connection, "refund:key:001")
    assert decision["status"] == "created"
    assert decision["result"] == {"status": "refunded", "charge_id": "ch_009_b"}
    assert record["tool_name"] == "apply_refund"
    assert record["target_id"] == "ch_009_b"
    assert record["result"] == {"status": "refunded", "charge_id": "ch_009_b"}
    assert record["created_at"] == FIXED_TIMESTAMP


def test_record_or_replay_idempotency_returns_existing_result_for_matching_retry(tmp_path):
    connection = reset_connection(tmp_path)
    first = record_or_replay_idempotency(
        connection,
        idempotency_key="refund:key:001",
        run_id="run_001",
        tool_name="apply_refund",
        target_type="charge",
        target_id="ch_009_b",
        arguments={"charge_id": "ch_009_b", "amount": 49.0},
        result={"status": "refunded", "charge_id": "ch_009_b"},
        created_at=FIXED_TIMESTAMP,
    )

    retry = record_or_replay_idempotency(
        connection,
        idempotency_key="refund:key:001",
        run_id="run_001",
        tool_name="apply_refund",
        target_type="charge",
        target_id="ch_009_b",
        arguments={"amount": 49.0, "charge_id": "ch_009_b"},
        result={"status": "different_result_should_not_replace_original"},
        created_at="2026-08-25T00:01:00Z",
    )

    stored_count = connection.execute("SELECT COUNT(*) FROM idempotency_keys").fetchone()[0]
    assert first["status"] == "created"
    assert retry["status"] == "replay"
    assert retry["result"] == {"status": "refunded", "charge_id": "ch_009_b"}
    assert stored_count == 1


def test_record_or_replay_idempotency_returns_conflict_for_different_arguments(tmp_path):
    connection = reset_connection(tmp_path)
    record_or_replay_idempotency(
        connection,
        idempotency_key="refund:key:001",
        run_id="run_001",
        tool_name="apply_refund",
        target_type="charge",
        target_id="ch_009_b",
        arguments={"charge_id": "ch_009_b", "amount": 49.0},
        result={"status": "refunded", "charge_id": "ch_009_b"},
        created_at=FIXED_TIMESTAMP,
    )

    conflict = record_or_replay_idempotency(
        connection,
        idempotency_key="refund:key:001",
        run_id="run_001",
        tool_name="apply_refund",
        target_type="charge",
        target_id="ch_009_b",
        arguments={"charge_id": "ch_009_b", "amount": 25.0},
        result={"status": "partially_refunded"},
        created_at="2026-08-25T00:01:00Z",
    )

    stored_count = connection.execute("SELECT COUNT(*) FROM idempotency_keys").fetchone()[0]
    assert conflict["status"] == "conflict"
    assert conflict["result"] is None
    assert conflict["conflict"]["idempotency_key"] == "refund:key:001"
    assert conflict["conflict"]["original_argument_hash"] != conflict["conflict"]["new_argument_hash"]
    assert stored_count == 1
