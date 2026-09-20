# Project model and lifecycle

## Common model

Use one YAML/JSON object. Preserve extra project-specific fields. Keep execution status out of this specification.

| Field | Required common shape |
|---|---|
| `schema_version` | Integer `1` |
| `project` | Stable `id`, `plan_file` |
| `components` | Objects with `id`, `title` |
| `decisions` | Objects with `id`, `title`, `status`: proposed, accepted, rejected, superseded |
| `requirements` | Objects with `id`, `title`, `risk`: standard or critical, `source` (file/section), nonempty `acceptance` |
| Each acceptance criterion | Globally unique `id`, explicit `statement`, nonempty `verification` method-name list |
| `tasks` | `id`, `title`, lists `requirement_ids`, `component_ids`, `decision_ids`, `depends_on`, `acceptance_ids` |
| `verification` | `thresholds` for standard/critical, `calibration_required_for_auto_advance: true`, optional complexity/comment policies |
| `preservation` | Optional compatibility baseline with `baselines`, `artifacts`, `conventions`, `status_dimensions`, and `approval_required_for` |

Each task needs at least one requirement and criterion. Criterion references must belong to its requirements. Methods can be `static_flow`, `behavioral_test`, `device_observation`, `manual_review`, or `document_check`; require only applicable methods. Use the bundled automatic logic gate for code-behavior claims. Document/manual tasks follow their own applicable completion policy; manual evidence does not manufacture automated alignment confidence.

Add objectives, API/data contracts, invariant scopes, ownership, risks, release gates, non-goals, task inputs/outputs, test commands, estimates, explicit deferrals, and supersessions as needed. An unmapped requirement is a planning gap unless explicitly deferred or a non-implementation obligation.

Preserve proposed versus accepted decisions. A fallback is conditional, not a second primary stack. Do not silently promote an assumption because a template needs a value.

## Preservation model

Add `preservation` whenever an existing project, previous accepted project, or user-selected template constrains the output. Read [preservation.md](preservation.md) before populating it.

- `baselines`: nonempty objects with stable `id`, `source`, and inspected `revision`.
- `artifacts`: protected objects with stable `id`, repository-relative `path` or glob, `role`, and `disposition`: `preserve`, `enhance`, `supersede`, or `remove`.
- A `supersede` or `remove` artifact requires a nonempty `approval` reference. A superseded artifact also requires nonempty `replacement_ids`.
- `conventions`: nonempty, unique statements describing protected relationships or workflows that cannot be captured by paths alone.
- `status_dimensions`: include `execution` and `relevance` so completed-but-superseded work remains representable.
- `approval_required_for`: include `remove`, `semantic_change`, and `authority_change`.

The model may index an accepted human-readable specification instead of replacing it. Mark generated ownership in the manifest and keep only one independently writable authority for each fact.

## Outputs

Reuse an existing layout and preserve its accepted artifact relationships. New projects may use:
- `plan.md`: maintained intent, optional generated progress region.
- `project.yaml`: validated structured view with sources.
- `.project/state.json`: lifecycle, blockers, history.
- `.project/generated-manifest.json`: managed outputs/regions, versions, hashes.
- `.project/bundles/<task-id>.md`: exact task context.
- `.project/evidence/<task-id>/<run-id>/`: reports and original artifacts.
- `.agent/AGENTS.md`, `.agent/rules/`, `.agent/context/`, `.agent/index.json`: shared agent contract and map.
- Root/tool instruction files: thin adapters to shared instructions.
- `docs/requirements/`, `docs/task/`, `docs/technical/`, `docs/implement/`: readable specifications and implementation records.

When an accepted baseline uses a navigable documentation index, visible task/status table, one task specification per ID, technical notes, and one implementation record per completed task, retain that contract. If a new project has no templates, adapt the bundled task and implementation templates. Generate detailed technical prose when the plan supplies concrete content or a task needs it. Avoid speculative placeholder documents. Never generate completed implementation logs or passing evidence for future code.

## Task execution

A task specification or bundle contains ID; current model/source snapshot; objective; exclusions; requirement and acceptance IDs; dependencies and state; decisions; exact inputs, outputs, files, or symbols; global invariants; relevant contracts; output scope; verification commands or pending analyzer needs; required evidence; stop conditions.

A ready task has sufficient inputs, satisfied dependencies, accepted required decisions, and observable criteria. Execution can be `todo -> ready -> in_progress -> verifying -> done`, with `blocked` and `needs_revalidation` retaining reasons and history. Track relevance separately as `current`, `superseded`, or `retired`; `done` and `superseded` can both be true for the same historical task.

Keep readiness in execution records. The bundled gate evaluates task evidence and decision prerequisites; it does not load dependency completion state. Check predecessor completion/current evidence before starting or advancing dependent tasks.

## Updating

1. Diff intent against the prior accepted model; diff code/dependencies against prior evidence.
2. Classify intent, implementation, state, generated-content, and compatibility changes. Preserve IDs, historical records, accepted artifact contracts, and linked replacements.
3. Compute impact across requirements, components, interface consumers, call/data dependencies, tasks, and tests. Use conservative invalidation for unresolved dependencies.
4. Reconcile model/output diffs. Preserve human edits, manual annotations, code, decisions, and execution history.
5. Refresh bundles and mark affected evidence stale. Reuse evidence only when all relevant inputs and policy remain unchanged.
6. Perform requested work and applicable verification, then render progress from observed state.

Keep plan revisions in version control where a project repository exists. Render from a validated model with pinned templates rather than repeating LLM extraction on each render. Stable outputs should not vary with timestamps/random IDs.

## Completion policy

Maintain one definition of done. Require each task's own criteria, applicable checks, current evidence, and disposition of deviations. Full notes apply to critical or contract-changing work; routine work needs a concise record with evidence and gaps. Distinguish implemented, verified, integrated, and released when relevant.

Scaffold build/smoke checks may pass while product requirements remain pending. Do not deadlock initialization on verification of future application behavior.
