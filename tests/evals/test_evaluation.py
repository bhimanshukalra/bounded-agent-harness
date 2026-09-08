import json

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from bounded_agent.cli import app
from bounded_agent.config import Settings
from bounded_agent.domain import RunnerType
from bounded_agent.evals import EvaluationConfig, run_evaluation


def test_evaluation_runs_supported_fixed_workflow_and_persists_reports(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs", eval_runs_dir=tmp_path / "evals")

    summary = run_evaluation(
        EvaluationConfig(eval_run_id="eval_001", scenario_ids=["support_001"]),
        settings,
    )

    assert len(summary.attempts) == 1
    assert {attempt.runner_type for attempt in summary.attempts} == {
        RunnerType.FIXED_WORKFLOW_BASELINE,
    }
    assert all(attempt.verifier_passed for attempt in summary.attempts)
    assert summary.metrics["attempt_count"] == 1.0
    assert summary.metrics["verified_pass_rate"] == 1.0
    assert summary.metrics["fixed_workflow_baseline_verified_pass_rate"] == 1.0
    assert summary.reproducibility["execution_mode"] == "deterministic"
    assert summary.reproducibility["requested_live_model"] is False
    assert summary.reproducibility["fixture_sha256"]
    assert len((summary.artifact_dir / "attempts.jsonl").read_text().splitlines()) == 1
    assert json.loads((summary.artifact_dir / "summary.json").read_text())["eval_run_id"] == "eval_001"
    assert "Verified pass rate: 100%" in (summary.artifact_dir / "report.md").read_text()
    assert "## Runner Comparison" in (summary.artifact_dir / "report.md").read_text()


def test_evaluation_rejects_unimplemented_runner_types():
    with pytest.raises(ValidationError, match="does not implement"):
        EvaluationConfig(
            eval_run_id="eval_unsupported",
            scenario_ids=["support_001"],
            runner_types=[RunnerType.AGENT_LOOP],
        )


def test_run_eval_cli_reports_summary(tmp_path, monkeypatch):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs", eval_runs_dir=tmp_path / "evals")
    monkeypatch.setattr("bounded_agent.cli.load_settings", lambda: settings)

    result = CliRunner().invoke(
        app,
        ["run-eval", "--eval-run-id", "eval_cli", "--runners", "fixed_workflow_baseline"],
    )

    assert result.exit_code == 0
    assert "Evaluation complete: eval_cli" in result.output
    assert "Verified pass rate: 100%" in result.output
