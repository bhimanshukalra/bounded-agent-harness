# ADR-001 - Experimental Model Containment

Status: accepted

## Context

A future model-backed decision source could change decision quality and prompt-related risk without changing registry-owned authority. It must not silently enter the deterministic local workflow.

## Decision

`ENABLE_LIVE_MODEL` remains false by default. Any model-backed source requires a separate accepted capability proposal naming scenarios, baseline threshold, verifier coverage, rollout owner, and rollback plan. Registry permissions, approval matching, idempotency, and MCP read-only boundaries remain unchanged.

## Evidence And Rollback

The deterministic capstone and full quality suite are the release gate. A safety/verifier regression, unbounded cost, or unexplained baseline regression blocks rollout. Rollback is disablement of `ENABLE_LIVE_MODEL`, retention of affected artifacts, and reproduction with deterministic mode.

Next review date: 2026-12-07.
