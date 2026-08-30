from typer.testing import CliRunner

from bounded_agent.cli import app


def test_package_imports():
    import bounded_agent

    assert bounded_agent is not None


def test_cli_help_works():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Bounded support-resolution agent harness" in result.output


def test_run_scenario_validates_existing_scenario():
    result = CliRunner().invoke(app, ["run-scenario", "support_001"])

    assert result.exit_code == 0
    assert "Scenario validated: support_001" in result.output
    assert "run-scenario is not implemented yet" in result.output


def test_run_scenario_fails_for_missing_scenario():
    result = CliRunner().invoke(app, ["run-scenario", "missing"])

    assert result.exit_code == 1
    assert "Scenario not found: missing" in result.output


def test_validate_scenarios_loads_all_fixtures():
    result = CliRunner().invoke(app, ["validate-scenarios"])

    assert result.exit_code == 0
    assert "Validated 10 scenario(s)." in result.output


def test_run_eval_placeholder_validates_scenario_directory():
    result = CliRunner().invoke(app, ["run-eval"])

    assert result.exit_code == 0
    assert "Validated 10 scenario(s)." in result.output
    assert "run-eval is not implemented yet" in result.output


def test_demo_shows_bounded_workflow():
    result = CliRunner().invoke(app, ["demo"])

    assert result.exit_code == 0
    assert "Bounded support-resolution demo" in result.output
    assert "Scenario: support_001" in result.output
    assert "request approval before applying any refund" in result.output
    assert "reports/demo-trace.md" in result.output


def test_reset_env_placeholder():
    result = CliRunner().invoke(app, ["reset-env"])

    assert result.exit_code == 0
    assert "reset-env is not implemented yet" in result.output


def test_show_trace_placeholder_accepts_run_id():
    result = CliRunner().invoke(app, ["show-trace", "run_001"])

    assert result.exit_code == 0
    assert "Run ID accepted: run_001" in result.output
    assert "show-trace is not implemented yet" in result.output
