---
name: plan-driven-development
description: Initialize software projects from detailed plans and continuously align requirements, architecture, tasks, code, and verification evidence. Use for plan-based scaffolding, plan updates, task context bundles, or requirement-to-code verification using NLP and AST-derived flow analysis. Preserve minimal comments and evidence-based completion gates; do not apply the full workflow to unrelated small edits.
---

# Plan-Driven Development

Turn the user's maintained plan into bounded, traceable work. Keep intent, implementation facts, and verification results distinct. Adapt existing repository conventions.

## Select the workflow

- **Initialize:** extract a structured model, resolve prerequisites, and generate the requested skeleton and task documents from the supplied plan.
- **Update:** reconcile explicit plan changes and current implementation with prior versions; preserve history and refresh affected artifacts.
- **Implement:** compile a self-contained task bundle, perform the work, verify affected criteria, and record the outcome.
- **Verify:** map requirements to symbols and behavior, inspect evidence, and determine whether the scoped task can advance.

Read [references/project-model.md](references/project-model.md) for the model, artifacts, and lifecycle. Read [references/verification.md](references/verification.md) for logic analysis, comments, complexity, scoring, and evidence. Use [assets/project.example.json](assets/project.example.json) as a small worked model and [assets/evidence.example.json](assets/evidence.example.json) as a pending report. Do not copy example-specific product choices into unrelated projects.

## Preserve working preferences

- Use English for engineering artifacts; derive product languages and stack choices from the plan.
- Preserve existing requirement, invariant, decision, and task IDs; link supersessions rather than renumbering.
- Keep comments minimal. Explain only complex or non-obvious logic remaining after refactoring: the reason, invariant, or constraint.
- Bound tasks with explicit acceptance criteria, dependencies, inputs, outputs, exclusions, and evidence. Use five estimated hours as a provisional splitting guideline when no project rule exists; document exceptions rather than inventing estimates.
- Give interface/schema changes explicit tasks and compatibility or migration plans. Avoid treating every file as frozen.
- Keep relevant global invariants and project fallback gates visible in task context.

## Assign one authority per fact

| Fact | Authority |
|---|---|
| Goals, scope, intended behavior, invariants, decisions | Maintained plan and accepted amendments |
| Structured requirement/task definitions | Validated model compiled from that intent |
| Task state, blockers, completion history | Execution records |
| Implemented behavior | Inspected code and observed execution |
| Outcomes and calibrated confidence | Evidence tied to exact input revisions |
| Maps, indexes, summaries, agent adapters | Generated views of the authorities above |

Default to `project.yaml`; JSON is also supported. Do not maintain two independently writable specifications. Keep execution state separately under `.project/`. A generated progress region in the plan may reflect state without rewriting intent.

## Initialize and maintain

1. Read the supplied plan, applicable `AGENTS.md`, existing task/architecture conventions, and relevant working-tree changes. Do not assume mentioned external files are accessible.
2. Extract requirements, components, contracts, decisions, risks, gates, tasks, and criteria with source file/section references. Mark inferred and unresolved information. Translate prose into explicit logic obligations independently of current code.
3. Validate IDs, references, dependency cycles, acceptance coverage, and scope. Use authorized defaults and ordinary implementation judgment. Block only work depending on a genuinely unresolved choice.
4. Generate or update appropriate artifacts: shared `.agent/` instructions and thin tool adapters; architecture/API contracts; requirements; tasks; bundles; evidence locations; selected stack scaffold and real CI configuration when requested. Verify commands exist; keep unimplemented checks pending.
5. Record generated-file ownership, managed regions, template versions, and input/output hashes. Reconcile edited generated regions; preserve human sections, source code, state, and historical evidence.
6. On plan, code, dependency, analyzer, or policy changes, calculate affected dependencies and consumers. Mark dependent evidence stale and tasks needing revalidation. If impact is uncertain, invalidate conservatively.
7. Regenerate indexes and progress summaries from records. Never silently change requirements, tests, or thresholds to make implementation pass.

Build task bundles with objectives, exclusions, requirement/criterion IDs, exact inputs, global invariants, relevant contracts, dependency state, authorized decisions, verification needs, evidence outputs, and the current snapshot. Avoid requiring agents to rediscover the document graph.

## Verify before advancement

Follow `references/verification.md`: use NLP for contracts and mappings, AST-derived control/data flow for behavior, and independently defined behavioral evidence. Similarity or a model's self-rating is insufficient.

Use `pass`, `fail`, or `inconclusive`. Confirmed violations fail. Missing, stale, unsupported, or uncalibrated required evidence is inconclusive. Only pass permits automatic completion and dependent-task advancement. Diagnosis, repair, and unrelated work may continue.

Never invent calibrated confidence. Represent unavailable scores as `null` with a reason. Calibration must apply to the actual language, requirement kind, evaluator versions, and scope. Keep manual decisions distinct from automated confidence. Record an explicitly authorized completion-policy change as a policy change, not as measured success.

Use concise completion records for routine work and full implementation notes for critical invariants, contracts, trust boundaries, or release gates. Include deviations and gaps. Preserve machine-generated results from actual runs, including failures.

Apply calibrated logic gates to tasks making code-behavior claims. For documentation, configuration, and scaffold work, use the applicable structural, build, or manual criteria without claiming domain-logic verification. Do not block a documentation update on a nonexistent behavioral calibration model.

## Bundled helper

```bash
python3 <skill-dir>/scripts/check_project.py validate project.yaml
python3 <skill-dir>/scripts/check_project.py gate project.yaml .project/evidence/T-007.json --task T-007 --source-hash <current-source-snapshot-sha256>
```

The helper validates structure and report metadata. Its gate is for automatic logic-verification decisions, not ordinary manual/document completion. It does not interpret prose, analyze ASTs, run tests, establish calibration, or authenticate artifacts. Inspect real runner outputs before trusting reports. The current source hash must come from the runner's complete input manifest, including uncommitted files and transitive dependencies; a commit ID alone is insufficient for a dirty tree.

Exit codes: `0` valid/pass, `1` invalid/fail, `2` inconclusive/unusable input. YAML needs PyYAML; JSON uses the standard library. Report unavailable analyzers instead of claiming success.

## Scope and delivery

Maintain alignment during requested work and task/plan updates. The skill does not create a background service or scheduled task. Configure ongoing automation only when requested. Skill installation does not authorize deployments, publication, purchases, or messages to others.

Report what changed, what was actually checked, which tasks can advance, and specific remaining blockers. Do not claim universal program correctness.
