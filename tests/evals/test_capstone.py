from bounded_agent.config import Settings
from bounded_agent.domain import RunnerType
from bounded_agent.evals import CAPSTONE_SCENARIO_IDS, run_capstone


def test_capstone_runs_representative_evidence_set(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs", eval_runs_dir=tmp_path / "evals")

    summary = run_capstone(eval_run_id="capstone_001", settings=settings)

    assert CAPSTONE_SCENARIO_IDS == ("support_002", "support_005", "support_006", "support_008")
    assert len(summary.attempts) == len(CAPSTONE_SCENARIO_IDS)
    assert {attempt.runner_type for attempt in summary.attempts} == {
        RunnerType.FIXED_WORKFLOW_BASELINE
    }
    assert (summary.artifact_dir / "report.md").exists()
    assert {attempt.scenario_id for attempt in summary.attempts} == set(CAPSTONE_SCENARIO_IDS)
