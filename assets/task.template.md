---
id: TASK-NNN
title: <task title>
execution_status: todo
relevance: current
depends_on: []
supersedes: []
superseded_by: null
---

# TASK-NNN — <task title>

## Traceability

| Field | Value |
|---|---|
| Requirements | `<requirement IDs and links>` |
| Acceptance criteria | `<criterion IDs>` |
| Components | `<component IDs>` |
| Decisions | `<accepted decision IDs>` |
| Baseline contracts | `<preserved artifacts or conventions affected>` |

## Objective

<Observable outcome, not an activity summary.>

## In scope

- <bounded deliverable>

## Out of scope

- <explicit exclusion or deferral>

## Inputs and dependencies

- <exact documents, interfaces, predecessor evidence, or files required>

## Technical approach

<Contracts, state transitions, algorithms, interfaces, compatibility behavior, and migration details needed to implement without rediscovering the design.>

## Files and symbols

- `<path or symbol>` — <expected change>

## Invariants and constraints

- `<invariant ID>` — <how this task must preserve it>

## Acceptance criteria and verification

- [ ] `<criterion ID>` — <observable result>; verify with `<command, test, inspection, or pending analyzer>`

## Required evidence

- <artifact path, runner output, device observation, or explicit N/A reason>

## Stop conditions

- <ambiguity, failed dependency, compatibility break, or unavailable evidence that blocks completion>

## Completion

1. Run the listed checks and preserve their original outputs.
2. Write the implementation record from `implementation.template.md` or the accepted project template.
3. Update the execution record, then regenerate the visible `[]`, `[!]`, or `[x]` marker from `task-status.md` without deleting history.
