# Phase Thirteen - Governed Evolution

## Purpose

Phase Thirteen turns the completed bounded-agent harness into a sustainable platform for carefully chosen follow-on work. It establishes how new capabilities are proposed, risk-assessed, evaluated, released, and retired without weakening the contracts, safety boundaries, or reproducibility established in earlier phases.

The goal is controlled evolution: the project can grow in response to real needs while every expansion remains traceable to an owner, a threat model, an evaluation plan, and an explicit decision to accept its operational cost.

## Phase Entry Context

By this phase, the project has a documented capstone, reproducible demonstrations, safety controls, durable state, scoped MCP access, independent verification, evaluation reporting, and release-readiness guidance.

## Phase Exit Criteria

Phase Thirteen is complete when:

- a capability proposal and decision record format exists
- every proposed expansion has an owner, trust-boundary analysis, and rollback plan
- evaluation gates are defined before implementation begins
- compatibility and migration expectations are documented
- feature flags or equivalent containment controls exist for experimental capabilities
- lifecycle policies cover deprecation, artifact retention, and incident follow-up
- representative governed-change exercises demonstrate the process end to end

## Phase Thirteen Checklist

- [x] Milestone 13.1 - Capability Governance
  - [x] Define a proposal template for new tools, policies, MCP capabilities, and model modes
  - [x] Require an owner, problem statement, scope, and non-goals
  - [x] Require a decision record for accepted, deferred, and rejected proposals
  - [x] Define review roles for safety, operations, and evaluation impact
- [x] Milestone 13.2 - Change Risk Assessment
  - [x] Define trust-boundary and permission-impact questions
  - [x] Define data handling and untrusted-content questions
  - [x] Define idempotency, approval, and rollback requirements
  - [x] Classify changes by risk and required evidence
- [x] Milestone 13.3 - Evaluation Gates
  - [x] Require scenario additions before new capability implementation
  - [x] Define baseline comparison and regression thresholds
  - [x] Require independent verifier coverage where behavior affects terminal claims
  - [x] Define release-blocking safety and reliability failures
- [x] Milestone 13.4 - Compatibility And Containment
  - [x] Document versioning expectations for domain models, tools, and MCP contracts
  - [x] Define migrations for persisted run state and artifacts
  - [x] Add feature-flag or equivalent containment guidance for experiments
  - [x] Define rollback and recovery procedures for released changes
- [x] Milestone 13.5 - Lifecycle Operations
  - [x] Define deprecation policy for tools, policies, and scenario fixtures
  - [x] Define artifact retention, archival, and cleanup ownership
  - [x] Define incident review inputs from traces, memory, and verifier evidence
  - [x] Define a periodic review cadence for accepted risks and limits
- [x] Milestone 13.6 - Governed Change Exercise
  - [x] Select a small representative capability change
  - [x] Produce its proposal, risk assessment, evaluation plan, and decision record
  - [x] Implement it behind the chosen containment mechanism
  - [x] Verify release and rollback paths
  - [x] Record outcomes and process improvements

## Governance Principles

- Expand capability only when its value, ownership, and risk are concrete.
- Make evaluation and rollback part of the proposal, not cleanup work.
- Preserve explicit authority boundaries as integrations and automation grow.
- Prefer reversible experiments over implicit permanent behavior.
- Treat observed failures as inputs to policy, tests, and operating guidance.

## Phase Thirteen Completion Note

Implemented with typed `CapabilityProposal` and `DecisionRecord` records, a governance policy and templates, and ADR-001 for the contained experimental-model exercise. The existing `ENABLE_LIVE_MODEL=false` configuration boundary keeps experimental model mode disabled by default; no model-backed decision source or new runtime authority was enabled.

Release evidence requires scenario and verifier coverage before an accepted proposal can ship. The contained exercise preserves the deterministic capstone as its baseline and rolls back by keeping `ENABLE_LIVE_MODEL` disabled while preserving run and evaluation artifacts for review. The accepted containment decision is scheduled for review on 2026-12-07. Focused governance, configuration, and capstone tests plus Ruff passed on 2026-09-08; full-suite verification is recorded with this implementation.
