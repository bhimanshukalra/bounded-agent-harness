from bounded_agent.config import Settings, load_settings
from bounded_agent.evals.evaluation import EvaluationConfig, EvaluationSummary, run_evaluation

CAPSTONE_SCENARIO_IDS = ("support_002", "support_005", "support_006", "support_008")


def run_capstone(
    *,
    eval_run_id: str = "capstone-demo",
    settings: Settings | None = None,
) -> EvaluationSummary:
    """Run the deterministic evidence set used by the local capstone workflow."""
    return run_evaluation(
        EvaluationConfig(
            eval_run_id=eval_run_id,
            scenario_ids=list(CAPSTONE_SCENARIO_IDS),
        ),
        settings or load_settings(),
    )
