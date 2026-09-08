from argparse import ArgumentParser

from bounded_agent.evals import run_capstone


def main() -> None:
    parser = ArgumentParser(description="Run the deterministic capstone evidence set.")
    parser.add_argument("--eval-run-id", default="capstone-demo")
    arguments = parser.parse_args()
    summary = run_capstone(eval_run_id=arguments.eval_run_id)
    print(f"Capstone evaluation: {summary.eval_run_id}")
    print(f"Verified pass rate: {summary.metrics['verified_pass_rate']:.0%}")
    print(f"Artifacts: {summary.artifact_dir}")


if __name__ == "__main__":
    main()
