from pathlib import Path

from pydantic import ValidationError

from bounded_agent.config import Settings


def test_settings_defaults_use_project_layout():
    settings = Settings(_env_file=None)

    assert settings.project_root.name == "bounded-agent-harness"
    assert settings.data_dir == settings.project_root / "data"
    assert settings.fixtures_dir == settings.project_root / "data" / "fixtures"
    assert settings.scenarios_dir == settings.project_root / "data" / "scenarios"
    assert settings.runs_dir == settings.project_root / "data" / "runs"
    assert settings.eval_runs_dir == settings.project_root / "data" / "eval_runs"
    assert settings.prompts_dir == settings.project_root / "prompts"
    assert settings.default_max_steps == 12
    assert settings.default_max_tool_retries == 2
    assert settings.default_max_invalid_actions == 2
    assert settings.default_token_budget == 50_000
    assert settings.default_cost_budget_usd == 1.0
    assert settings.enable_live_model is False
    assert settings.enable_mcp is False


def test_settings_accept_environment_overrides(monkeypatch, tmp_path):
    project_root = tmp_path / "project"
    data_dir = tmp_path / "custom-data"
    prompts_dir = tmp_path / "custom-prompts"

    monkeypatch.setenv("PROJECT_ROOT", str(project_root))
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("PROMPTS_DIR", str(prompts_dir))
    monkeypatch.setenv("DEFAULT_MAX_STEPS", "7")
    monkeypatch.setenv("DEFAULT_MAX_TOOL_RETRIES", "3")
    monkeypatch.setenv("DEFAULT_MAX_INVALID_ACTIONS", "1")
    monkeypatch.setenv("DEFAULT_TOKEN_BUDGET", "12345")
    monkeypatch.setenv("DEFAULT_COST_BUDGET_USD", "0.5")
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    monkeypatch.setenv("MODEL_NAME", "mock-model")
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setenv("ENABLE_LIVE_MODEL", "true")
    monkeypatch.setenv("ENABLE_MCP", "true")

    settings = Settings(_env_file=None)

    assert settings.project_root == project_root
    assert settings.data_dir == data_dir
    assert settings.fixtures_dir == data_dir / "fixtures"
    assert settings.scenarios_dir == data_dir / "scenarios"
    assert settings.runs_dir == data_dir / "runs"
    assert settings.eval_runs_dir == data_dir / "eval_runs"
    assert settings.prompts_dir == prompts_dir
    assert settings.default_max_steps == 7
    assert settings.default_max_tool_retries == 3
    assert settings.default_max_invalid_actions == 1
    assert settings.default_token_budget == 12_345
    assert settings.default_cost_budget_usd == 0.5
    assert settings.model_provider == "mock"
    assert settings.model_name == "mock-model"
    assert settings.model_api_key == "test-key"
    assert settings.enable_live_model is True
    assert settings.enable_mcp is True


def test_settings_reject_invalid_budgets():
    try:
        Settings(_env_file=None, default_max_steps=0)
    except ValidationError as exc:
        assert "default_max_steps" in str(exc)
    else:
        raise AssertionError("expected default_max_steps validation to fail")


def test_settings_accept_explicit_path_values(tmp_path):
    settings = Settings(
        _env_file=None,
        project_root=tmp_path,
        fixtures_dir=Path("/tmp/fixtures"),
    )

    assert settings.fixtures_dir == Path("/tmp/fixtures")
    assert settings.scenarios_dir == tmp_path / "data" / "scenarios"
