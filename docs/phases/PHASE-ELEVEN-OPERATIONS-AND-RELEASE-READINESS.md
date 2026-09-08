# Phase Eleven - Operations And Release Readiness

## Purpose

Phase Eleven makes the harness practical to operate, inspect, and demonstrate. It turns the accumulated runner, safety, verifier, and evaluation artifacts into clear CLI workflows and release-quality documentation.

The goal is not a production deployment platform. The goal is a repeatable local operating experience where a developer can run a scenario, resume it, inspect its trace and memory, verify its result, run an evaluation, and understand failures without reading implementation internals.

## Phase Entry Context

The project has bounded tools, durable run state, MCP-backed policy lookup, safety controls, independent verification, and evaluation reporting. Phase Eleven exposes those completed capabilities coherently and documents their operating boundaries.

## Phase Exit Criteria

Phase Eleven is complete when:

- the CLI supports the complete local workflow
- run, resume, trace, memory, verification, and evaluation artifacts are discoverable
- commands validate arguments and return actionable failures
- configuration is documented and reproducible
- a clean checkout can run the representative workflow
- architecture and safety boundaries are documented accurately
- release checks run consistently
- tests and lint pass

## Phase Eleven Checklist

- [x] Milestone 11.1 - CLI Workflow Inventory
  - [x] Define supported operator journeys
  - [x] Audit existing commands and artifact paths
  - [x] Define consistent command output and exit behavior
  - [x] Define read-only versus mutating command contracts
  - [x] Add CLI inventory tests
- [x] Milestone 11.2 - Run And Resume Commands
  - [x] Add or refine scenario-run command
  - [x] Add resume-by-run-ID command
  - [x] Surface terminal result and artifact paths
  - [x] Prevent accidental resume of terminal runs
  - [x] Add command tests
- [x] Milestone 11.3 - Artifact Inspection Commands
  - [x] Add trace inspection with event filtering
  - [x] Add run-state and memory inspection
  - [x] Add terminal-result inspection
  - [x] Add verifier-result inspection
  - [x] Keep inspection commands read-only
  - [x] Add inspection tests
- [x] Milestone 11.4 - Verification And Evaluation Commands
  - [x] Expose independent verification command
  - [x] Expose repeatable evaluation command
  - [x] Print concise summary metrics and artifact paths
  - [x] Return nonzero status for failed verification when requested
  - [x] Add command tests
- [x] Milestone 11.5 - Configuration And Reproducibility
  - [x] Document settings and environment variables
  - [x] Add example local configuration
  - [x] Record model, prompt, fixture, and scenario versions in artifacts
  - [x] Document deterministic and live-model modes
  - [x] Add configuration tests
- [x] Milestone 11.6 - Documentation And Architecture
  - [x] Update README quickstart
  - [x] Document architecture and ownership boundaries
  - [x] Document safety and approval limitations
  - [x] Document MCP and durable-state behavior
  - [x] Add walkthrough validation checklist
- [x] Milestone 11.7 - Release Readiness Review
  - [x] Run representative end-to-end workflow from a clean state
  - [x] Confirm artifact links and error messages
  - [x] Confirm quality checks pass
  - [x] Write Phase Eleven completion note

## Operating Principles

- Commands should expose artifacts and facts, not conceal them behind convenience abstractions.
- Inspection and verification paths remain read-only.
- Configuration must make deterministic local behavior the default.
- Human operators retain authority for approvals and consequential actions.
- Documentation must distinguish implemented behavior from planned or external-service work.

## Phase Eleven Completion Note

Implemented with deterministic run, resume, reset, inspection, verification, and evaluation commands; durable artifact discovery; example configuration; evaluation reproducibility metadata; and local operations documentation. The supported release workflow is local and deterministic: remote deployment, production integrations, and live-model automation remain deferred. The full suite and Ruff checks passed on 2026-09-08.
