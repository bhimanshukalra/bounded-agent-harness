from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    project_root: Path = Field(default_factory=default_project_root)
    data_dir: Path | None = None
    fixtures_dir: Path | None = None
    scenarios_dir: Path | None = None
    runs_dir: Path | None = None
    eval_runs_dir: Path | None = None
    prompts_dir: Path | None = None

    default_max_steps: int = Field(default=12, ge=1)
    default_max_tool_retries: int = Field(default=2, ge=0)
    default_max_invalid_actions: int = Field(default=2, ge=0)
    default_token_budget: int = Field(default=50_000, ge=1)
    default_cost_budget_usd: float = Field(default=1.0, ge=0)

    model_provider: str | None = None
    model_name: str | None = None
    model_api_key: str | None = None
    enable_live_model: bool = False
    enable_mcp: bool = False

    @model_validator(mode="after")
    def populate_default_paths(self) -> "Settings":
        root = self.project_root
        data_dir = self.data_dir or root / "data"

        self.data_dir = data_dir
        self.fixtures_dir = self.fixtures_dir or data_dir / "fixtures"
        self.scenarios_dir = self.scenarios_dir or data_dir / "scenarios"
        self.runs_dir = self.runs_dir or data_dir / "runs"
        self.eval_runs_dir = self.eval_runs_dir or data_dir / "eval_runs"
        self.prompts_dir = self.prompts_dir or root / "prompts"
        return self


def load_settings() -> Settings:
    return Settings()
