# Agent contract

Canonical instructions for every agent working in this repository. Tool-specific files
(`CLAUDE.md`, `.github/copilot-instructions.md`, and similar) are generated pointers to
this file. Edit this file; never edit an adapter.

## Authority order

1. `<plan file>` — goals, scope, intended behaviour, invariants, decisions.
2. `<model file>` — validated structured requirements and tasks.
3. `.project/state.json` — execution state, blockers, history.
4. Inspected code and observed runs — implemented behaviour.
5. `.project/evidence/` — outcomes tied to exact input revisions.

Indexes, summaries, and adapters are generated views. Do not edit a generated view to
change a fact.

## Commands

| Purpose | Command |
|---|---|
| Install | `<command>` |
| Build | `<command>` |
| Test | `<command>` |
| Lint / typecheck | `<command>` |
| Validate the model | `<command>` |

Do not invent a command. If a check does not exist yet, leave it pending and say so.

## Working rules

- Take one task at a time from `docs/task/`. Work only inside its declared scope.
- Read the task bundle at `.project/bundles/<task-id>.md` before touching code.
- Keep comments minimal: only complex or non-obvious logic — the reason, invariant, or constraint.
- Preserve existing IDs. Link supersessions; never renumber or delete history.
- Never change a requirement, test, or threshold to make an implementation pass.

## Completion

A task is done only with its own acceptance criteria met, applicable checks run, original
runner output preserved, and an implementation record written. Update the execution record
first; the visible `[]` / `[!]` / `[x]` marker is regenerated from it.

## Global invariants

- `<invariant ID>` — `<statement and how work must preserve it>`

## Do not

- `<forbidden path, effect, or dependency>`
