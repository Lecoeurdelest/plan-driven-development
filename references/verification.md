# Logic verification and evidence

## Contracts and program analysis

Extract obligations independently of code: entities, inputs, preconditions, exact predicates/units, time windows, state transitions, required outputs, forbidden effects, exceptions, retries, and idempotency. Preserve source references and unresolved ambiguities. Deriving both code and expected behavior from the same implementation can conceal the same defect twice.

Use NLP/semantic retrieval to map domain terms to candidate symbols. Similarity supports discovery, not correctness. Keep mappings in a sidecar file rather than adding inline comments everywhere.

Use language-aware AST parsing, symbol/type resolution where available, call graphs, control-flow graphs, and data-flow or taint analysis. Check callees and error paths. Compare guards, ordering, effects, units, and transitions. Similar graph shapes can mean opposite behavior; equivalent refactorings may have different shapes.

Bounded symbolic checks can help supported predicates. Retain assumptions, bounds, and counterexamples. Unmodeled dynamic calls, reflection, concurrency, external libraries, unsupported syntax, or timeouts are limitations. No finding under incomplete analysis is not proof of absence.

Record analyzer-adapter capabilities. Python's `ast` supplies syntax, not complete control/data flow. Tools such as CodeQL may supply deeper models for supported environments. Consult current official documentation when selecting/installing tools. Never describe a parser or regex as a full logic verifier.

## Behavioral checks

Select boundary/negative cases, property tests, model-based state transitions, integration checks, and device observations according to the requirement. Define expectations from the plan. Branch coverage measures exercised outcomes rather than correctness.

Targeted mutation tests can expose tests that miss changed operators, removed guards, or reversed transitions. Report surviving, unexecuted, invalid, and equivalent mutants accurately; do not impose a universal mutation score.

Example: "offline more than 20% of the window" needs cases at and around the boundary. An invariant forbidding entitlement reads on a free relay path needs dependency/flow evidence; a passing paid-user test is insufficient. Do not copy these product examples into unrelated projects.

## Complexity and comments

Suggested per-function budgets: cyclomatic complexity 10, cognitive complexity 15, nesting depth 3. These are configurable policies, not universal testing standards. Pin language/analyzer definitions. Report unsupported metrics; separate generated/vendor code using explicit scope.

Use complexity to trigger refactoring review. Explain only necessary complex algorithms, invariants, subtle domain behavior, timing, or concurrency. Low structural scores may still hide complex logic. Do not demand comments on ordinary functions, use comment-density targets, or clear complexity violations merely by adding comments. Record justified exceptions with scope, reason, and revalidation conditions.

Avoid comment-sensitive maintainability indexes as primary gates. Prefer meaningful behavior checks over implementation-mirroring tests or coverage padding.

## Confidence

Separate semantic similarity, evidence completeness, and alignment confidence. Confidence is per criterion/requirement and bounded by declared scope. Require finite values in `[0,1]`; use `null` when unavailable.

Never use invented weights or LLM self-ratings as correctness probabilities. Calibration needs independently reviewed correct/incorrect pairs, realistic defects, equivalent refactorings, project-separated holdout evaluation, reliability assessment, and measured false-pass rates with uncertainty. It must apply to current languages, requirement types, evaluator versions, and scope. Repeated model agreement alone is not independent evidence.

Provisional automatic thresholds are standard 0.95 and critical 0.99. These are policy targets until validation supports them. Without applicable calibration, report qualitative findings and null confidence; automatic completion remains inconclusive. An explicitly authorized policy amendment remains a policy change, not measured success.

Decide per required criterion, without averaging:
- **Fail:** confirmed violation, failed mandatory check, or failed required test.
- **Inconclusive:** insufficient score; ambiguity; incomplete, stale, missing, unsupported, untrusted, or uncalibrated evidence.
- **Pass:** every criterion/check passes with current applicable calibration, sufficient confidence, and complete required evidence.

A hard failure overrides a high score. Scope pass to the selected task; never imply the entire product is correct. Block completion/dependents while permitting repair and unrelated work.

## Evidence shape

The bundled metadata gate reads:
- `schema_version: 1`, `task_id`, `spec_hash` (SHA-256 of exact model bytes), `source_hash` (SHA-256 of the runner's complete input snapshot).
- `calibration`: `status: validated`, nonempty `id`, `artifact`, `evaluator_version`, `applicable: true`, only after verifying these claims.
- `criteria`: one record per selected task criterion: `id`, `status`, `confidence`, `analysis_complete`, `checks`.
- Each check: `method`, `status`, `artifacts`. Include every method required by the model. Statuses: pass, fail, inconclusive, not_run.

Also retain source locations, obligation mappings, analyzer/model/prompt versions, limitations, test IDs, commands, environment, results, counterexamples, artifact digests, and time of execution. Keep original runner outputs including failures. Never edit test artifacts to manufacture success.

The helper cannot authenticate artifacts or calibration. Inspect referenced records and verify their provenance and scope. Compute the current snapshot independently of the report, including relevant code, dependencies, tests, config, and uncommitted edits. A commit SHA does not describe a dirty tree.

## Primary references

These support techniques, not the proposed thresholds. Recheck official guidance when version behavior matters.
- [Complexity metrics](https://docs.sonarsource.com/sonarqube-server/user-guide/code-metrics/metrics-definition)
- [CodeQL data flow](https://codeql.github.com/docs/writing-codeql-queries/about-data-flow-analysis/)
- [CodeQL Python control flow](https://codeql.github.com/docs/codeql-language-guides/analyzing-control-flow-in-python/)
- [Python AST](https://docs.python.org/3/library/ast.html)
- [Branch coverage](https://coverage.readthedocs.io/en/latest/branch.html)
- [Stateful tests](https://hypothesis.readthedocs.io/en/latest/stateful.html)
- [Mutation outcomes](https://stryker-mutator.io/docs/mutation-testing-elements/mutant-states-and-metrics/)
- [Calibration research](https://proceedings.mlr.press/v70/guo17a.html)
- [Radon metrics](https://radon.readthedocs.io/en/latest/intro.html)
