# Phase Twelve - Capstone And Handoff

## Purpose

Phase Twelve closes the project with evidence rather than claims. It packages a reproducible demonstration, an architecture narrative, an evaluated scenario set, and a clear handoff describing what the harness proves and what remains intentionally out of scope.

The goal is a technically honest capstone: someone new to the repository can understand the bounded-agent design, reproduce representative runs, inspect safety and evaluation evidence, and extend the system without inheriting undocumented assumptions.

## Phase Entry Context

By this phase, the project has a bounded agent loop, typed registry and tools, durable state and memory, scoped MCP knowledge access, safety and recovery controls, independent verification, evaluation reporting, and an operational CLI workflow.

## Phase Exit Criteria

Phase Twelve is complete when:

- a representative end-to-end demonstration is reproducible from documented commands
- architecture, ownership, and trust boundaries are documented
- evaluation and baseline evidence is summarized honestly
- safety and failure behavior is demonstrated alongside successful behavior
- known limitations and non-goals are explicit
- artifact retention and cleanup guidance exists
- contributor handoff guidance exists
- final quality checks pass

## Phase Twelve Checklist

- [x] Milestone 12.1 - Capstone Demonstration
  - [x] Select representative success, escalation, safety, resume, and MCP scenarios
  - [x] Define deterministic demonstration commands
  - [x] Capture expected artifacts and outputs
  - [x] Add a demonstration smoke test or script
- [x] Milestone 12.2 - Evidence Bundle
  - [x] Summarize traces, memory, terminal results, verifier results, and eval reports
  - [x] Link artifacts to scenario IDs and run IDs
  - [x] Include baseline comparison evidence
  - [x] Include safety and failure evidence
  - [x] Define artifact retention rules
- [x] Milestone 12.3 - Architecture Narrative
  - [x] Document data flow and ownership boundaries
  - [x] Document registry, approval, idempotency, MCP, and memory contracts
  - [x] Document verifier independence
  - [x] Document deterministic versus live-model modes
  - [x] Validate diagrams and examples against implementation
- [x] Milestone 12.4 - Risk And Limitation Register
  - [x] Record unimplemented production concerns
  - [x] Record model and prompt limitations
  - [x] Record local MCP transport limitations
  - [x] Record evaluation coverage limits
  - [x] Record security and operator assumptions
- [x] Milestone 12.5 - Contributor Handoff
  - [x] Document local setup and quality commands
  - [x] Document how to add a scenario, tool, MCP capability, and verifier check
  - [x] Document migration and compatibility expectations
  - [x] Document issue triage conventions
- [x] Milestone 12.6 - Final Readiness Review
  - [x] Run complete quality suite
  - [x] Run representative demonstration from clean state
  - [x] Confirm documentation links and artifact paths
  - [x] Write final project completion note

## Capstone Principles

- Demonstrate failure handling, approval boundaries, and escalation as clearly as success paths.
- Keep claims proportional to independently verified evidence.
- Preserve local reproducibility as the default operating mode.
- Treat the capstone as a handoff document, not marketing copy.
- Keep production deployment, remote MCP hosting, and unrestricted automation explicitly outside scope unless separately implemented.

## Phase Twelve Completion Note

Implemented with `scripts/run_capstone.py`, a representative deterministic scenario set, a smoke test, and `docs/CAPSTONE-HANDOFF.md`. The handoff records artifact paths, evidence/retention expectations, ownership boundaries, known limitations, contributor extension points, and the local quality gate. The full suite and Ruff checks passed on 2026-09-08.
