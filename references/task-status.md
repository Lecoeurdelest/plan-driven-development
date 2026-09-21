# Three-state task projection

Use exactly three markers in human-readable task indexes. Treat them as generated projections of execution records, not as a second source of truth.

| Marker | Meaning | Execution states |
|---|---|---|
| `[]` | Unfinished and not active | `todo`, `ready` |
| `[!]` | Active or requires attention | `in_progress`, `verifying`, `blocked`, `needs_revalidation` |
| `[x]` | Completed under the current completion policy | `done` |

## Rendering rules

- Render one marker per task and derive it from the detailed execution state.
- Require a concrete detail for `[!]`: current activity, pending verification, blocker, or revalidation reason.
- Render `[x]` only after the task's criteria pass under the applicable completion policy and its evidence is linked.
- Move a stale completed task to `needs_revalidation` and `[!]`; preserve its prior completion record and evidence history.
- Keep relevance separate as `current`, `superseded`, or `retired`. A task can be `[x] done` and `superseded` at the same time.
- Keep dependencies, milestones, fallbacks, evidence, and implementation links visible. The marker never replaces the detailed task specification.
- Do not confuse the task marker `[]` with the Markdown checklist syntax `- [ ]` used inside acceptance criteria.

## Status-index contract

Use a Markdown table with `Status`, `ID`, `Execution`, `Relevance`, `Detail`, and `Evidence` columns. Additional columns are allowed. Keep task IDs unique.

Run:

```bash
python3 <skill-dir>/scripts/check_project.py audit-task-status docs/task/README.md
```

The audit rejects unknown markers, marker/execution mismatches, duplicate IDs, missing attention detail, and completed tasks without evidence.

## Compatibility

Inventory an accepted project's marker semantics before changing them. Preserve the existing convention unless the user approves a migration. When migration is approved, record the mapping and update the status index, execution records, agent workflows, and validation together.
