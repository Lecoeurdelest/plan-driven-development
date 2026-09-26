# Cross-platform agent contract

One canonical instruction set under `.agent/`. Every tool-specific file is a generated thin adapter that points at it. Never maintain two writable copies of the same instruction.

## Canonical layout

| Path | Role | Authority |
|---|---|---|
| `.agent/AGENTS.md` | The single instruction set: build/test commands, conventions, authority order, task workflow, completion gates | Authored |
| `.agent/rules/*.md` | Scoped rules too specific for the main file; one concern per file | Authored |
| `.agent/context/*.md` | Durable background an agent must not rediscover: architecture map, contracts, domain glossary | Authored or generated from the model |
| `.agent/index.json` | Machine-readable map of the document graph and the adapter set | Generated |
| `.agent/adapters/*.md` | Optional adapter bodies when a host needs more than a pointer | Generated |

`.agent/` carries instructions. Execution state stays in `.project/`. Human-readable specifications stay in `docs/`. An agent contract never becomes a second place to record task status.

## Adapter matrix

Verify each host against its current official documentation before relying on a row; these behaviours change.

| Host | File it reads | Adapter strategy |
|---|---|---|
| Codex CLI | `AGENTS.md` (repository root) | Root `AGENTS.md` is a generated adapter pointing to `.agent/AGENTS.md` |
| Claude Code, Cowork | `CLAUDE.md`, falling back to `AGENTS.md` when absent | Generate `CLAUDE.md`; do not rely on the fallback when a root `AGENTS.md` also exists |
| Cursor | `.cursor/rules/*.mdc`; also reads `AGENTS.md` | Generate `.cursor/rules/00-agent-contract.mdc`; use `.mdc` only for glob-scoped rules other hosts cannot express |
| GitHub Copilot | `.github/copilot-instructions.md`; also reads `AGENTS.md` | Generate `.github/copilot-instructions.md` |
| Gemini CLI | `GEMINI.md`, configurable | Prefer configuring `context.fileName` to `AGENTS.md`; generate `GEMINI.md` only when configuration is unavailable |

Generate an adapter only for hosts the project actually uses. An unused adapter is drift waiting to happen.

## Adapter form

An adapter is a pointer, not a copy. Keep it under roughly twenty lines: what the canonical file is, the instruction to read it, and nothing a reader would be tempted to edit in place.

Wrap generated content in managed-region markers so regeneration never destroys human additions outside them:

```
<!-- pdd:generated:begin id=<adapter-id> source=.agent/AGENTS.md -->
...generated pointer...
<!-- pdd:generated:end id=<adapter-id> -->
```

Symlinking an adapter to `.agent/AGENTS.md` is acceptable where the whole team is on a POSIX filesystem and the repository is never consumed as an archive. Default to real files: symlinks survive neither Windows checkouts without developer mode nor most zip or tarball exports.

Record every adapter in `.agent/index.json` and in the generated manifest with its source hash, so a hand-edited adapter is detected as drift rather than silently diverging.

## Preservation

An existing instruction file is an accepted baseline artifact. Inventory it before replacing it: classify it `preserve`, `enhance`, `supersede`, or `remove` under [preservation.md](preservation.md). Turning an authored `CLAUDE.md` into a generated adapter is a `supersede` and needs explicit approval, because it moves where a human edits.

When approved, migrate rather than delete: move the file's real content into `.agent/AGENTS.md` (or a `.agent/rules/` file), leave the adapter pointing at it, and record the replacement. Never discard project-specific instruction content because a template had no slot for it.

## Audit

```bash
python3 <skill-dir>/scripts/check_project.py audit-agent-contract --root .
```

The audit checks that the canonical file exists, that `.agent/index.json` is well-formed, that every declared adapter exists, and that no adapter has diverged from the source it was generated from. It cannot judge whether the instructions are correct, whether a host still reads the file the matrix claims, or whether a semantic change was approved.
