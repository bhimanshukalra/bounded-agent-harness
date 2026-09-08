from typer.testing import CliRunner

from bounded_agent.cli import app
from bounded_agent.config import Settings


def test_package_imports():
    import bounded_agent

    assert bounded_agent is not None


def test_cli_help_works():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Bounded support-resolution agent harness" in result.output


def test_run_scenario_executes_and_exposes_artifacts(tmp_path, monkeypatch):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs", eval_runs_dir=tmp_path / "evals")
    monkeypatch.setattr("bounded_agent.cli.load_settings", lambda: settings)

    result = CliRunner().invoke(app, ["run-scenario", "support_001", "--run-id", "run_001"])

    assert result.exit_code == 0
    assert "Run complete: run_001" in result.output
    assert "Terminal state: needs_human_approval" in result.output
    assert (settings.runs_dir / "run_001" / "result.json").exists()


def test_run_scenario_fails_for_missing_scenario():
    result = CliRunner().invoke(app, ["run-scenario", "missing"])

    assert result.exit_code == 1
    assert "Scenario not found: missing" in result.output


def test_run_scenario_rejects_path_like_run_id(tmp_path, monkeypatch):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs", eval_runs_dir=tmp_path / "evals")
    monkeypatch.setattr("bounded_agent.cli.load_settings", lambda: settings)

    result = CliRunner().invoke(app, ["run-scenario", "support_001", "--run-id", "../escape"])

    assert result.exit_code == 1
    assert "Invalid run ID" in result.output
    assert not (tmp_path / "escape").exists()


def test_validate_scenarios_loads_all_fixtures():
    result = CliRunner().invoke(app, ["validate-scenarios"])

    assert result.exit_code == 0
    assert "Validated 10 scenario(s)." in result.output


def test_run_eval_executes_the_default_scenario_set():
    result = CliRunner().invoke(app, ["run-eval"])

    assert result.exit_code == 0
    assert "Evaluation complete: local-eval" in result.output
    assert "Verified pass rate:" in result.output


def test_demo_shows_bounded_workflow():
    result = CliRunner().invoke(app, ["demo"])

    assert result.exit_code == 0
    assert "Bounded support-resolution demo" in result.output
    assert "Scenario: support_001" in result.output
    assert "request approval before applying any refund" in result.output
    assert "reports/demo-trace.md" in result.output


def test_reset_env_resets_a_scenario(tmp_path, monkeypatch):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    monkeypatch.setattr("bounded_agent.cli.load_settings", lambda: settings)

    result = CliRunner().invoke(app, ["reset-env", "support_001", "--run-id", "reset_001"])

    assert result.exit_code == 0
    assert "Environment reset: support_001" in result.output
    assert (settings.runs_dir / "reset_001" / "state.db").exists()


def test_inspection_commands_read_persisted_artifacts(tmp_path, monkeypatch):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs", eval_runs_dir=tmp_path / "evals")
    monkeypatch.setattr("bounded_agent.cli.load_settings", lambda: settings)
    runner = CliRunner()
    assert runner.invoke(app, ["run-scenario", "support_001", "--run-id", "run_001"]).exit_code == 0

    trace = runner.invoke(app, ["show-trace", "run_001", "--event-type", "terminal_state"])
    state = runner.invoke(app, ["show-run", "run_001"])
    memory = runner.invoke(app, ["show-memory", "run_001", "--artifact", "safety"])
    terminal = runner.invoke(app, ["show-result", "run_001"])

    assert trace.exit_code == 0
    assert '"event_type": "terminal_state"' in trace.output
    assert state.exit_code == 0
    assert '"run_id": "run_001"' in state.output
    assert memory.exit_code == 0
    assert "# Safety Events" in memory.output
    assert terminal.exit_code == 0
    assert '"terminal_state": "needs_human_approval"' in terminal.output
