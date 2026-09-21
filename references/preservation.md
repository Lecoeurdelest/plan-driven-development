# Preservation and compatible evolution

Use this workflow when the user identifies an existing repository, earlier project, template, or documentation system as accepted. Preserve transferable mechanics without copying product-specific content.

## Establish the baseline

Record the exact source and revision inspected. Inventory:

- document layers, paths, naming, and navigation maps;
- stable requirement, invariant, decision, task, and evidence IDs;
- authority order and which files are authored versus generated;
- visible status and dependency views;
- task specification fields and completion commands;
- implementation records, machine evidence, deviations, known gaps, invariant checks, and changed-file lists;
- task-to-implementation-to-evidence relationships;
- supersession history and which parts survive a replacement;
- agent rules, context, workflows, and thin adapters.

Do not reduce an accepted baseline to the smallest common schema. The common model is an index and validation surface; it does not erase richer project-specific fields or human-readable artifacts.

## Classify every structural change

| Disposition | Meaning | Approval |
|---|---|---|
| `preserve` | Keep path, role, and semantics | Default |
| `enhance` | Keep the accepted contract and add compatible detail or automation | Default when requested work needs it |
| `supersede` | Replace semantics while retaining history, rationale, surviving parts, and links | Explicit user approval required |
| `remove` | Delete the artifact or convention without a replacement | Explicit user approval required |

An instruction to improve, modernize, initialize, or migrate does not authorize `supersede` or `remove`. Record approval in the model and name replacements for superseded artifacts.

## Preserve rich task documentation

When the baseline separates human-readable layers, retain them:

1. A navigable documentation index or architecture map.
2. Functional and non-functional requirement files explaining intent and acceptance.
3. A visible task index with stable IDs, dependencies, milestones, fallbacks, current relevance, and the accepted status-marker convention. For new defaults, use the three-marker projection in [task-status.md](task-status.md).
4. One detailed task specification per task with objective, scope, exclusions, requirement links, files or symbols, acceptance criteria, implementation notes, and completion checks.
5. Technical documents for architecture, contracts, data, interfaces, and risky behavior.
6. One implementation record per completed task with what was built, criterion results, evidence, deviations, known gaps, invariant checks, and changed files.
7. Original machine evidence stored separately from prose.

New machine-readable state and generated bundles should feed these views. They must not replace them with a status-only list or a short roadmap.

Treat a marker-system change as a semantic change. Preserve an accepted project's existing symbols unless the user approves migration. During an approved migration, map execution and relevance separately instead of collapsing completed-but-superseded work into one symbol.

## Keep state dimensions distinct

Execution and relevance answer different questions:

- execution: `todo`, `ready`, `in_progress`, `verifying`, `done`, or `blocked`;
- relevance: `current`, `superseded`, or `retired`.

A completed task may later become superseded. Keep its completion record and evidence, link its replacement, and record which contracts or components survive. Never rewrite the task as though it was never implemented.

## Reconcile instead of replacing

Before writing:

1. Diff the proposed output contract against the baseline.
2. Produce a preservation map with one row per protected artifact or convention.
3. Resolve unapproved `supersede` and `remove` rows before generation.
4. Generate additive artifacts and update existing indexes in their established locations.
5. Run structural validation and `audit-preservation`.
6. Check semantic drift manually: stale counts, broken links, status contradictions, orphaned implementation records, missing evidence, obsolete technical notes, and authority conflicts.

Fix detected drift inside the preserved structure. Do not use drift as justification to discard the structure.
