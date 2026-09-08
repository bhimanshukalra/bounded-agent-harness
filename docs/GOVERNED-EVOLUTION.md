# Governed Evolution

## Proposal Gate

Every new tool, policy capability, MCP surface, model mode, or change to terminal claims starts with a capability proposal and an associated decision record. Use the typed `CapabilityProposal` and `DecisionRecord` contracts in `src/bounded_agent/governance.py`; the templates below mirror their required content.

Review roles are: capability owner, safety reviewer, operations reviewer, and evaluation reviewer. A proposal cannot move to accepted until each impact is explicit and the release gate is reproducible.

## Risk Classification

| Risk | Required evidence |
| --- | --- |
| Low | Scenario test, verifier check when terminal evidence changes, and rollback note. |
| Moderate | Low-risk evidence plus baseline comparison and operations review. |
| High | Moderate-risk evidence plus explicit containment flag, approval/idempotency analysis, safety review, and a demonstrated rollback. |

Treat untrusted-content handling, permissions, approval matching, idempotency, persisted state, and MCP provenance as trust-boundary changes. A regression in any required safety or verifier check blocks release.

## Evaluation And Release Gate

Before implementation, name the scenarios to add or amend, the baseline threshold, the independent verifier check, and the expected terminal-state evidence. Release is blocked by failed safety checks, failed verifier checks, unmatched approval behavior, duplicate mutation evidence, or a regression below the accepted baseline threshold.

## Compatibility And Containment

Domain models, tool schemas, MCP contracts, and persisted run artifacts are versioned contracts. Add optional fields before requiring them, retain readers for supported historical artifacts, and otherwise reject incompatible artifacts with a clear migration message. A migration must include a fixture, a rollback plan, and a verification run.

Experimental behavior must be disabled by default and contained behind a named configuration flag. `ENABLE_LIVE_MODEL` is the current containment boundary for any future model-backed decision source; enabling it does not grant new tool permissions, bypass approvals, or change registry ownership. Rollback means disabling the flag, preserving artifacts, and rerunning the deterministic evaluation set.

## Lifecycle And Review

Deprecate tools, policies, and scenarios with a replacement, owner, removal date, and compatibility note. Generated artifacts remain local by default; retain a copied evidence bundle only for a release review or incident. Incident review inputs are the terminal result, trace, memory, verifier report, fixture/scenario hashes, and reproduction command.

Review accepted risks, deferred proposals, and active containment flags every 90 days or immediately after a safety incident.

## Templates

### Capability Proposal

```text
Proposal ID:
Title:
Owner:
Problem statement:
Scope:
Non-goals:
Risk level:
Trust-boundary impact:
Untrusted-content impact:
Approval and idempotency impact:
Scenarios and baseline threshold:
Verifier coverage:
Containment flag:
Rollback plan:
```

### Decision Record

```text
Proposal ID:
Status: accepted | deferred | rejected
Decision owner:
Rationale:
Accepted risks:
Release gate:
Rollback trigger:
Next review date:
```

## Governed Change Exercise

`ADR-001` records the current experimental model-mode boundary. It is deliberately accepted only as disabled-by-default containment guidance: there is no model-backed decision source in the release workflow, no authority expansion, and rollback is immediate by retaining `ENABLE_LIVE_MODEL=false`.

The exercise is verified by the deterministic capstone evaluation and the existing approval, safety, verifier, and evaluation suites. This demonstrates the proposal-to-evidence-to-rollback path without introducing a new operational capability.
