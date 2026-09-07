# Project Walkthrough Checklist

This checklist is designed for a slow, complete read-through of the project. Use it as a progress tracker while you go file by file.

For each file, answer these questions before checking it off:

1. What role does this file play?
2. What data types, functions, constants, or documents does it define?
3. What depends on it?
4. What tests or fixtures explain its intended behavior?
5. What would break if this changed?

## Pass 0: Project Shell

- [ ] `.env.example` - expected environment variable template.
- [ ] `.gitignore` - files and folders intentionally excluded from version control.
- [ ] `.python-version` - Python runtime version pin.
- [ ] `README.md` - project entry point.
- [ ] `pyproject.toml` - package metadata, dependencies, scripts, test config, lint config, and build settings.
- [ ] `uv.lock` - locked dependency graph; skim for dependency provenance rather than reading line by line.

## Pass 1: Product And Design Docs

- [ ] `docs/BOUNDED-TOOL-USING-AGENT-LOOP-ENGINEERING.md` - engineering concept for the bounded tool-using loop.
- [ ] `docs/PHASED-IMPLEMENTATION-PLAN.md` - overall implementation sequence.
- [ ] `docs/phases/PHASE-ZERO-PRODUCT-SHAPE.md` - initial product framing.
- [ ] `docs/phases/PHASE-ONE-CONTRACTS-AND-POLICIES.md` - contracts and policy layer.
- [ ] `docs/phases/PHASE-TWO-REPOSITORY-SCAFFOLD-AND-CORE-MODELS.md` - repository and model foundation.
- [ ] `docs/phases/PHASE-THREE-MOCK-ENVIRONMENT.md` - mock environment design.
- [ ] `docs/phases/PHASE-FOUR-TOOL-REGISTRY-AND-SCOPED-TOOLS.md` - tool registry and scoped tool design.

## Pass 2: Prompts

- [ ] `prompts/agent.md` - primary agent behavior prompt.
- [ ] `prompts/compaction.md` - context compaction prompt.
- [ ] `prompts/judge.md` - judge prompt.
- [ ] `prompts/safety_policy.md` - safety policy prompt.
- [ ] `prompts/verifier.md` - verifier prompt.

## Pass 3: Data Fixtures And Scenarios

- [ ] `data/fixtures/policies.json` - mock support policy data.
- [ ] `data/fixtures/support_seed.json` - seed support environment data.
- [ ] `data/scenarios/support_001.json` - support evaluation scenario 001.
- [ ] `data/scenarios/support_002.json` - support evaluation scenario 002.
- [ ] `data/scenarios/support_003.json` - support evaluation scenario 003.
- [ ] `data/scenarios/support_004.json` - support evaluation scenario 004.
- [ ] `data/scenarios/support_005.json` - support evaluation scenario 005.
- [ ] `data/scenarios/support_006.json` - support evaluation scenario 006.
- [ ] `data/scenarios/support_007.json` - support evaluation scenario 007.
- [ ] `data/scenarios/support_008.json` - support evaluation scenario 008.
- [ ] `data/scenarios/support_009.json` - support evaluation scenario 009.
- [ ] `data/scenarios/support_010.json` - support evaluation scenario 010.
- [ ] `data/eval_runs/.gitkeep` - placeholder for future eval run outputs.
- [ ] `data/runs/.gitkeep` - placeholder for future runtime outputs.

## Pass 4: Core Package, Config, And Domain

- [ ] `src/bounded_agent/__init__.py` - package initializer.
- [ ] `src/bounded_agent/config.py` - application settings and configuration loading.
- [ ] `src/bounded_agent/domain/__init__.py` - domain package initializer.
- [ ] `src/bounded_agent/domain/enums.py` - core enum definitions.
- [ ] `src/bounded_agent/domain/models.py` - core Pydantic domain models.

Pair these with:

- [ ] `tests/test_config.py` - tests for config behavior.
- [ ] `tests/domain/.gitkeep` - placeholder marker for the domain test folder.
- [ ] `tests/domain/test_enums.py` - tests for domain enums.
- [ ] `tests/domain/test_models.py` - tests for domain models.
- [ ] `tests/domain/test_scenarios.py` - tests for scenario data and domain compatibility.

## Pass 5: State Layer

- [ ] `src/bounded_agent/state/__init__.py` - state package initializer.
- [ ] `src/bounded_agent/state/audit.py` - audit record behavior.
- [ ] `src/bounded_agent/state/failures.py` - injected failure state support.
- [ ] `src/bounded_agent/state/fixtures.py` - fixture loading helpers.
- [ ] `src/bounded_agent/state/idempotency.py` - idempotency tracking behavior.
- [ ] `src/bounded_agent/state/inspection.py` - state inspection helpers.
- [ ] `src/bounded_agent/state/reset.py` - state reset behavior.
- [ ] `src/bounded_agent/state/schema.py` - state schema definitions.

Pair these with:

- [ ] `tests/state/test_audit.py` - audit tests.
- [ ] `tests/state/test_failures.py` - failure state tests.
- [ ] `tests/state/test_fixture_loader.py` - fixture loader tests.
- [ ] `tests/state/test_fixtures.py` - fixture behavior tests.
- [ ] `tests/state/test_idempotency.py` - idempotency tests.
- [ ] `tests/state/test_inspection.py` - state inspection tests.
- [ ] `tests/state/test_reset.py` - state reset tests.
- [ ] `tests/state/test_schema.py` - state schema tests.

## Pass 6: Tool System

- [ ] `src/bounded_agent/tools/__init__.py` - tools package initializer.
- [ ] `src/bounded_agent/tools/approval_tools.py` - approval-related tools.
- [ ] `src/bounded_agent/tools/execution.py` - tool execution behavior.
- [ ] `src/bounded_agent/tools/failure_handling.py` - tool failure handling behavior.
- [ ] `src/bounded_agent/tools/models.py` - tool-related models.
- [ ] `src/bounded_agent/tools/policy_tools.py` - policy lookup tools.
- [ ] `src/bounded_agent/tools/read_tools.py` - read-only support tools.
- [ ] `src/bounded_agent/tools/registry.py` - tool registration and discovery.
- [ ] `src/bounded_agent/tools/schemas.py` - tool schema generation or definitions.
- [ ] `src/bounded_agent/tools/write_tools.py` - mutating support tools.

Pair these with:

- [ ] `tests/tools/.gitkeep` - placeholder marker for the tools test folder.
- [ ] `tests/tools/test_approval_tools.py` - approval tool tests.
- [ ] `tests/tools/test_execution.py` - tool execution tests.
- [ ] `tests/tools/test_injected_failure_integration.py` - injected failure integration tests.
- [ ] `tests/tools/test_mutating_tool_idempotency.py` - idempotency tests for mutating tools.
- [ ] `tests/tools/test_policy_tools.py` - policy tool tests.
- [ ] `tests/tools/test_read_tools.py` - read tool tests.
- [ ] `tests/tools/test_registry.py` - tool registry tests.
- [ ] `tests/tools/test_schemas.py` - tool schema tests.
- [ ] `tests/tools/test_tool_models.py` - tool model tests.
- [ ] `tests/tools/test_write_tools.py` - write tool tests.

## Pass 7: Loop, CLI, Evals, And Future Modules

- [ ] `src/bounded_agent/loop/__init__.py` - loop package initializer.
- [ ] `src/bounded_agent/loop/actions.py` - loop action definitions.
- [ ] `src/bounded_agent/cli.py` - command-line interface.
- [ ] `src/bounded_agent/evals/__init__.py` - evals package initializer.
- [ ] `src/bounded_agent/evals/scenarios.py` - scenario loading for evals.
- [ ] `src/bounded_agent/mcp_server/__init__.py` - MCP server package placeholder.
- [ ] `src/bounded_agent/safety/__init__.py` - safety package placeholder.
- [ ] `src/bounded_agent/tracing/__init__.py` - tracing package placeholder.

Pair these with:

- [ ] `tests/cli/test_cli.py` - CLI tests.
- [ ] `tests/loop/test_actions.py` - loop action tests.
- [ ] `tests/evals/.gitkeep` - placeholder marker for future eval tests.
- [ ] `tests/safety/.gitkeep` - placeholder marker for future safety tests.

## Pass 8: Placeholder And Output Folders

- [ ] `reports/.gitkeep` - placeholder for report outputs.
- [ ] `reports/experiments/.gitkeep` - placeholder for experiment reports.
- [ ] `scripts/.gitkeep` - placeholder for future scripts.

## Pass 9: Generated Or Local-Only Folders

These are part of the local working tree shape, but they are not source files to study line by line.

- [ ] `.git/` - Git repository internals.
- [ ] `.venv/` - local virtual environment and installed packages.
- [ ] `.pytest_cache/` - pytest cache.
- [ ] `.ruff_cache/` - Ruff cache.
- [ ] `__pycache__/` - generated Python bytecode cache.
- [ ] `src/bounded_agent/**/__pycache__/` - generated Python bytecode caches inside source folders.
- [ ] `tests/**/__pycache__/` - generated Python bytecode caches inside test folders.

## Suggested Cadence

- [ ] Day 1 - Project shell, docs, and prompts.
- [ ] Day 2 - Data fixtures and scenarios.
- [ ] Day 3 - Config and domain models.
- [ ] Day 4 - State layer.
- [ ] Day 5 - Tool models, schemas, registry, and execution.
- [ ] Day 6 - Concrete tools: read, write, policy, approval, and failure handling.
- [ ] Day 7 - Loop, CLI, evals, and placeholder modules.
- [ ] Day 8 - Full test suite review, matching every test back to the source file it protects.
